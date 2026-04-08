from __future__ import annotations

from dataclasses import dataclass

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


class ProEditLikeFeatureMixController:
    def __init__(self, config: ProEditLikeFeatureMixConfig) -> None:
        self.config = config
        self._handles: list[torch.utils.hooks.RemovableHandle] = []
        self.reset()

    def reset(self) -> None:
        self.current_pass = "idle"
        self.current_step_idx = 0
        self.total_steps = 1
        self.current_roi_mask: torch.Tensor | None = None
        self.enabled = False
        self.source_cache: dict[str, torch.Tensor] = {}

    def close(self) -> None:
        for handle in self._handles:
            handle.remove()
        self._handles.clear()
        self.reset()

    def register(self, unet) -> None:
        self.close()
        modules = dict(unet.named_modules())
        for block_idx in self.config.up_block_indices:
            for resnet_idx in self.config.resnet_indices:
                module_name = f"up_blocks.{int(block_idx)}.resnets.{int(resnet_idx)}"
                module = modules.get(module_name)
                if module is None:
                    continue
                self._handles.append(module.register_forward_hook(self._build_hook(module_name)))

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

    def _mix_enabled(self) -> bool:
        start_step = int(self.config.start_ratio * self.total_steps)
        end_step = int(self.config.end_ratio * self.total_steps)
        return start_step <= self.current_step_idx < max(start_step + 1, end_step)

    def _build_hook(self, module_name: str):
        def hook(_module, _inputs, output):
            if not isinstance(output, torch.Tensor):
                return output

            if self.current_pass == "source":
                self.source_cache[module_name] = output.detach().clone()
                return output

            if self.current_pass != "target" or not self.enabled or not self._mix_enabled():
                return output

            source_feature = self.source_cache.get(module_name)
            roi_mask = self.current_roi_mask
            if source_feature is None or roi_mask is None:
                return output

            source_feature = source_feature.to(device=output.device, dtype=output.dtype)
            resized_roi = F.interpolate(
                roi_mask.to(device=output.device, dtype=output.dtype),
                size=output.shape[-2:],
                mode="nearest",
            )

            if output.shape[0] == source_feature.shape[0]:
                alpha = (
                    -float(self.config.inside_target_relax_strength) * resized_roi
                    + float(self.config.outside_source_strength) * (1.0 - resized_roi)
                )
                return output + alpha * (source_feature - output)

            if output.shape[0] == 2 * source_feature.shape[0]:
                batch_size = source_feature.shape[0]
                if resized_roi.shape[0] != batch_size:
                    return output
                zeros_roi = torch.zeros_like(resized_roi)
                alpha = torch.cat(
                    [
                        zeros_roi,
                        -float(self.config.inside_target_relax_strength) * resized_roi
                        + float(self.config.outside_source_strength) * (1.0 - resized_roi),
                    ],
                    dim=0,
                )
                source_feature_full = torch.cat([output[:batch_size], source_feature], dim=0)
                return output + alpha * (source_feature_full - output)

            return output

        return hook
