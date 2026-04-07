from __future__ import annotations

from dataclasses import dataclass

import torch


@dataclass
class SourceDecoderFeatureInjectionConfig:
    start_ratio: float = 0.25
    end_ratio: float = 0.75
    strength: float = 0.5
    up_block_indices: tuple[int, ...] = (2, 3)
    resnet_indices: tuple[int, ...] = (0, 1, 2)


class SourceDecoderFeatureInjectionController:
    def __init__(self, config: SourceDecoderFeatureInjectionConfig) -> None:
        self.config = config
        self._handles: list[torch.utils.hooks.RemovableHandle] = []
        self.reset()

    def reset(self) -> None:
        self.current_pass = "idle"
        self.current_step_idx = 0
        self.total_steps = 1
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
        self.source_cache = {}

    def begin_target_pass(self, step_idx: int, total_steps: int) -> None:
        self.current_pass = "target"
        self.current_step_idx = int(step_idx)
        self.total_steps = max(1, int(total_steps))

    def _injection_enabled(self) -> bool:
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

            if self.current_pass != "target" or not self._injection_enabled():
                return output

            source_feature = self.source_cache.get(module_name)
            if source_feature is None:
                return output
            source_feature = source_feature.to(device=output.device, dtype=output.dtype)
            if source_feature.shape != output.shape:
                return output
            strength = float(self.config.strength)
            return (1.0 - strength) * output + strength * source_feature

        return hook
