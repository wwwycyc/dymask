from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import torch
import torch.nn.functional as F


@dataclass
class ProEditLikeFeatureMixConfig:
    start_ratio: float = 0.20
    end_ratio: float = 0.80
    inside_target_relax_strength: float = 0.05
    outside_source_strength: float = 0.15
    up_block_indices: tuple[int, ...] = (2, 3)
    resnet_indices: tuple[int, ...] = (0, 1, 2)


class ProEditLikeKVAttnProcessor:
    def __init__(self, controller: "ProEditLikeFeatureMixController", module_name: str, place_in_unet: str) -> None:
        self.controller = controller
        self.module_name = module_name
        self.place_in_unet = place_in_unet

    def __call__(
        self,
        attn,
        hidden_states: torch.Tensor,
        encoder_hidden_states: torch.Tensor | None = None,
        attention_mask: torch.Tensor | None = None,
        temb: torch.Tensor | None = None,
        *args,
        **kwargs,
    ) -> torch.Tensor:
        residual = hidden_states
        if attn.spatial_norm is not None:
            hidden_states = attn.spatial_norm(hidden_states, temb)

        input_ndim = hidden_states.ndim
        spatial_shape: tuple[int, int] | None = None
        if input_ndim == 4:
            batch_size, channel, height, width = hidden_states.shape
            spatial_shape = (height, width)
            hidden_states = hidden_states.view(batch_size, channel, height * width).transpose(1, 2)

        batch_size, sequence_length, _ = (
            hidden_states.shape if encoder_hidden_states is None else encoder_hidden_states.shape
        )

        if attention_mask is not None:
            attention_mask = attn.prepare_attention_mask(attention_mask, sequence_length, batch_size)
            attention_mask = attention_mask.view(batch_size, attn.heads, -1, attention_mask.shape[-1])

        if attn.group_norm is not None:
            hidden_states = attn.group_norm(hidden_states.transpose(1, 2)).transpose(1, 2)

        query = attn.to_q(hidden_states)
        is_cross = encoder_hidden_states is not None
        if encoder_hidden_states is None:
            encoder_hidden_states = hidden_states
        elif attn.norm_cross:
            encoder_hidden_states = attn.norm_encoder_hidden_states(encoder_hidden_states)

        key = attn.to_k(encoder_hidden_states)
        value = attn.to_v(encoder_hidden_states)

        inner_dim = key.shape[-1]
        head_dim = inner_dim // attn.heads
        query = query.view(batch_size, -1, attn.heads, head_dim).transpose(1, 2)
        key = key.view(batch_size, -1, attn.heads, head_dim).transpose(1, 2)
        value = value.view(batch_size, -1, attn.heads, head_dim).transpose(1, 2)

        if attn.norm_q is not None:
            query = attn.norm_q(query)
        if attn.norm_k is not None:
            key = attn.norm_k(key)

        key, value = self.controller.mix_kv(
            module_name=self.module_name,
            key=key,
            value=value,
            is_cross=is_cross,
            spatial_shape=spatial_shape,
        )

        hidden_states = self.controller.attend(
            query=query,
            key=key,
            value=value,
            attention_mask=attention_mask,
            is_cross=is_cross,
            place_in_unet=self.place_in_unet,
        )

        hidden_states = hidden_states.transpose(1, 2).reshape(batch_size, -1, attn.heads * head_dim)
        hidden_states = hidden_states.to(query.dtype)
        hidden_states = attn.to_out[0](hidden_states)
        hidden_states = attn.to_out[1](hidden_states)

        if input_ndim == 4:
            hidden_states = hidden_states.transpose(-1, -2).reshape(batch_size, channel, spatial_shape[0], spatial_shape[1])

        if attn.residual_connection:
            hidden_states = hidden_states + residual

        hidden_states = hidden_states / attn.rescale_output_factor
        return hidden_states


class ProEditLikeFeatureMixController:
    def __init__(self, config: ProEditLikeFeatureMixConfig) -> None:
        self.config = config
        self._default_attn_processors: dict[str, object] = {}
        self._registered_unet = None
        self.attention_controller = None
        self.reset()

    def reset(self) -> None:
        self.current_pass = "idle"
        self.current_step_idx = 0
        self.total_steps = 1
        self.current_roi_mask: torch.Tensor | None = None
        self.current_edit_modes: list[str] = []
        self.enabled = False
        self.source_cache: dict[str, tuple[torch.Tensor, torch.Tensor]] = {}

    def close(self) -> None:
        if self._registered_unet is not None and self._default_attn_processors:
            self._registered_unet.set_attn_processor(dict(self._default_attn_processors))
        self._registered_unet = None
        self._default_attn_processors = {}
        self.attention_controller = None
        self.reset()

    def set_attention_controller(self, controller) -> None:
        self.attention_controller = controller
        if controller is not None and hasattr(controller, 'num_att_layers'):
            controller.num_att_layers = len(self._default_attn_processors) if self._default_attn_processors else 0

    def register(self, unet) -> None:
        self.close()
        self._registered_unet = unet
        self._default_attn_processors = dict(unet.attn_processors)
        replacement = {}
        for name in self._default_attn_processors:
            replacement[name] = ProEditLikeKVAttnProcessor(
                controller=self,
                module_name=name,
                place_in_unet=self._resolve_place(name),
            )
        unet.set_attn_processor(replacement)
        if self.attention_controller is not None and hasattr(self.attention_controller, 'num_att_layers'):
            self.attention_controller.num_att_layers = len(replacement)

    def set_batch_edit_modes(self, edit_modes: Iterable[str]) -> None:
        self.current_edit_modes = [str(mode) for mode in edit_modes]

    def begin_source_pass(self, step_idx: int, total_steps: int) -> None:
        self.current_pass = "source"
        self.current_step_idx = int(step_idx)
        self.total_steps = max(1, int(total_steps))
        self.current_roi_mask = None
        self.enabled = True
        self.source_cache = {}

    def begin_target_pass(
        self,
        step_idx: int,
        total_steps: int,
        roi_mask: torch.Tensor | None,
        enabled: bool,
    ) -> None:
        self.current_pass = "target"
        self.current_step_idx = int(step_idx)
        self.total_steps = max(1, int(total_steps))
        self.current_roi_mask = roi_mask
        self.enabled = bool(enabled)

    def _resolve_place(self, module_name: str) -> str:
        if module_name.startswith('down_blocks.'):
            return 'down'
        if module_name.startswith('mid_block.'):
            return 'mid'
        return 'up'

    def _should_mix_kv(self, module_name: str) -> bool:
        if '.attn1.processor' not in module_name:
            return False
        parts = module_name.split('.')
        if len(parts) < 4 or parts[0] != 'up_blocks' or parts[2] != 'attentions':
            return False
        try:
            block_idx = int(parts[1])
            attn_idx = int(parts[3])
        except ValueError:
            return False
        return block_idx in self.config.up_block_indices and attn_idx in self.config.resnet_indices

    def _mix_enabled(self) -> bool:
        start_step = int(self.config.start_ratio * self.total_steps)
        end_step = int(self.config.end_ratio * self.total_steps)
        return start_step <= self.current_step_idx < max(start_step + 1, end_step)

    def _resolve_spatial_shape(self, spatial_shape: tuple[int, int] | None, token_count: int) -> tuple[int, int] | None:
        if spatial_shape is not None:
            return spatial_shape
        side = int(token_count ** 0.5)
        if side * side == token_count:
            return side, side
        return None

    def _inside_source_strength(self, edit_mode: str) -> float:
        outside = float(self.config.outside_source_strength)
        relax = float(self.config.inside_target_relax_strength)
        if edit_mode == 'add':
            return 0.0
        if edit_mode == 'style':
            return outside
        return max(0.0, outside - relax)

    def _build_source_mix_alpha(
        self,
        batch_size: int,
        token_count: int,
        spatial_shape: tuple[int, int] | None,
        *,
        device: torch.device,
        dtype: torch.dtype,
    ) -> torch.Tensor | None:
        roi_mask = self.current_roi_mask
        if roi_mask is None:
            return None
        spatial_shape = self._resolve_spatial_shape(spatial_shape, token_count)
        if spatial_shape is None:
            return None

        roi_mask = roi_mask.to(device=device, dtype=dtype)
        if roi_mask.shape[0] != batch_size:
            return None
        resized_roi = F.interpolate(roi_mask, size=spatial_shape, mode='nearest')
        roi_tokens = resized_roi.flatten(2).transpose(1, 2)

        alpha = torch.empty((batch_size, token_count), device=device, dtype=dtype)
        outside = float(self.config.outside_source_strength)
        for sample_idx in range(batch_size):
            edit_mode = self.current_edit_modes[sample_idx] if sample_idx < len(self.current_edit_modes) else 'change'
            inside = self._inside_source_strength(edit_mode)
            roi_values = roi_tokens[sample_idx, :, 0]
            alpha[sample_idx] = outside * (1.0 - roi_values) + inside * roi_values
        return alpha[:, None, :, None]

    def mix_kv(
        self,
        module_name: str,
        key: torch.Tensor,
        value: torch.Tensor,
        is_cross: bool,
        spatial_shape: tuple[int, int] | None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        if is_cross or not self._should_mix_kv(module_name):
            return key, value

        if self.current_pass == 'source':
            self.source_cache[module_name] = (key.detach().clone(), value.detach().clone())
            return key, value

        if self.current_pass != 'target' or not self.enabled or not self._mix_enabled():
            return key, value

        cached = self.source_cache.get(module_name)
        if cached is None:
            return key, value
        source_key, source_value = cached
        if key.shape[0] % 2 != 0 or source_key.shape[0] * 2 != key.shape[0]:
            return key, value

        batch_size = source_key.shape[0]
        key_uncond, key_cond = key[:batch_size], key[batch_size:]
        value_uncond, value_cond = value[:batch_size], value[batch_size:]
        if key_cond.shape != source_key.shape or value_cond.shape != source_value.shape:
            return key, value

        alpha = self._build_source_mix_alpha(
            batch_size=batch_size,
            token_count=key_cond.shape[2],
            spatial_shape=spatial_shape,
            device=key.device,
            dtype=key.dtype,
        )
        if alpha is None:
            return key, value

        source_key = source_key.to(device=key.device, dtype=key.dtype)
        source_value = source_value.to(device=value.device, dtype=value.dtype)
        mixed_key_cond = (1.0 - alpha) * key_cond + alpha * source_key
        mixed_value_cond = (1.0 - alpha) * value_cond + alpha * source_value
        key = torch.cat([key_uncond, mixed_key_cond], dim=0)
        value = torch.cat([value_uncond, mixed_value_cond], dim=0)
        return key, value

    def attend(
        self,
        *,
        query: torch.Tensor,
        key: torch.Tensor,
        value: torch.Tensor,
        attention_mask: torch.Tensor | None,
        is_cross: bool,
        place_in_unet: str,
    ) -> torch.Tensor:
        if self.attention_controller is None:
            return F.scaled_dot_product_attention(
                query,
                key,
                value,
                attn_mask=attention_mask,
                dropout_p=0.0,
                is_causal=False,
            )

        scale = query.shape[-1] ** -0.5
        attn_scores = torch.matmul(query, key.transpose(-1, -2)) * scale
        if attention_mask is not None:
            attn_scores = attn_scores + attention_mask
        attention_probs = attn_scores.softmax(dim=-1)
        attention_probs = self.attention_controller(attention_probs, is_cross, place_in_unet)
        return torch.matmul(attention_probs, value)
