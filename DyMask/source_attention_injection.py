from __future__ import annotations

from dataclasses import dataclass

import torch


@dataclass
class SourceSelfAttentionInjectionConfig:
    start_ratio: float = 0.30
    end_ratio: float = 1.0
    strength: float = 1.0
    locations: tuple[str, ...] = ("up",)
    max_store_resolution: int = 32


class SourceSelfAttentionInjectionStore:
    def __init__(
        self,
        config: SourceSelfAttentionInjectionConfig,
        low_resource: bool = False,
    ) -> None:
        self.config = config
        self.low_resource = bool(low_resource)
        self.num_att_layers = -1
        self.reset()

    @staticmethod
    def get_empty_store() -> dict[str, list[torch.Tensor]]:
        return {
            "down_cross": [],
            "mid_cross": [],
            "up_cross": [],
            "down_self": [],
            "mid_self": [],
            "up_self": [],
        }

    def reset(self) -> None:
        self.cur_step = 0
        self.cur_att_layer = 0
        self.current_pass = "idle"
        self.current_step_idx = 0
        self.total_steps = 1
        self.step_store = self.get_empty_store()
        self.attention_store = {}
        self.source_step_store = self.get_empty_store()
        self.source_cache = self.get_empty_store()
        self.source_indices = {
            "down_self": 0,
            "mid_self": 0,
            "up_self": 0,
        }

    def _reset_target_history(self) -> None:
        self.cur_step = 0
        self.cur_att_layer = 0
        self.step_store = self.get_empty_store()
        self.attention_store = {}
        self.source_indices = {
            "down_self": 0,
            "mid_self": 0,
            "up_self": 0,
        }

    def begin_source_pass(self, step_idx: int, total_steps: int) -> None:
        self.current_pass = "source"
        self.current_step_idx = int(step_idx)
        self.total_steps = max(1, int(total_steps))
        self.cur_att_layer = 0
        self.source_step_store = self.get_empty_store()
        self.source_indices = {
            "down_self": 0,
            "mid_self": 0,
            "up_self": 0,
        }

    def begin_target_pass(self, step_idx: int, total_steps: int) -> None:
        self.current_pass = "target"
        self.current_step_idx = int(step_idx)
        self.total_steps = max(1, int(total_steps))
        self._reset_target_history()

    def step_callback(self, x_t: torch.Tensor) -> torch.Tensor:
        return x_t

    def _store_enabled(self, attn: torch.Tensor) -> bool:
        return attn.shape[1] <= self.config.max_store_resolution ** 2

    def _inject_enabled(self, place_in_unet: str) -> bool:
        start_step = int(self.config.start_ratio * self.total_steps)
        end_step = int(self.config.end_ratio * self.total_steps)
        return (
            place_in_unet in self.config.locations
            and start_step <= self.current_step_idx < max(start_step + 1, end_step)
        )

    def _forward_impl(self, attn: torch.Tensor, is_cross: bool, place_in_unet: str) -> torch.Tensor:
        key = f"{place_in_unet}_{'cross' if is_cross else 'self'}"

        if self.current_pass == "source":
            if not is_cross and self._store_enabled(attn) and place_in_unet in self.config.locations:
                self.source_step_store[key].append(attn.detach().clone())
            return attn

        if self.current_pass == "target":
            if not is_cross and self._inject_enabled(place_in_unet):
                source_key = f"{place_in_unet}_self"
                source_maps = self.source_cache.get(source_key, [])
                source_index = self.source_indices[source_key]
                if source_index < len(source_maps):
                    source_attn = source_maps[source_index].to(device=attn.device, dtype=attn.dtype)
                    if source_attn.shape == attn.shape:
                        strength = float(self.config.strength)
                        attn = (1.0 - strength) * attn + strength * source_attn
                self.source_indices[source_key] += 1
            if self._store_enabled(attn):
                self.step_store[key].append(attn)
            return attn

        return attn

    def __call__(self, attn: torch.Tensor, is_cross: bool, place_in_unet: str) -> torch.Tensor:
        if self.current_pass == "target" and not self.low_resource:
            half = attn.shape[0] // 2
            attn[half:] = self._forward_impl(attn[half:], is_cross, place_in_unet)
        else:
            attn = self._forward_impl(attn, is_cross, place_in_unet)

        self.cur_att_layer += 1
        if self.cur_att_layer == self.num_att_layers:
            self.cur_att_layer = 0
            self.cur_step += 1
            self.between_steps()
        return attn

    def between_steps(self) -> None:
        if self.current_pass == "source":
            self.source_cache = {
                key: [item.detach().clone() for item in value]
                for key, value in self.source_step_store.items()
            }
            self.source_step_store = self.get_empty_store()
            return

        if self.current_pass != "target":
            return

        if len(self.attention_store) == 0:
            self.attention_store = self.step_store
        else:
            for key in self.attention_store:
                for index in range(len(self.attention_store[key])):
                    self.attention_store[key][index] += self.step_store[key][index]
        self.step_store = self.get_empty_store()

    def get_average_attention(self) -> dict[str, list[torch.Tensor]]:
        if self.cur_step <= 0:
            return self.get_empty_store()
        return {
            key: [item / self.cur_step for item in self.attention_store.get(key, [])]
            for key in self.get_empty_store()
        }
