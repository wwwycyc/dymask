from __future__ import annotations

import torch

from .schemas import MaterializedSample
from .v1_source_prompt_source_anchored_support_c1 import V1SourcePromptSourceAnchoredSupportC1Editor


class V1SourcePromptSourceAnchoredSupportC2Editor(V1SourcePromptSourceAnchoredSupportC1Editor):
    def __init__(
        self,
        pipe,
        config,
        support_rho: float = 0.85,
        soft_roi_start_weight: float = 0.75,
        soft_roi_end_weight: float = 0.10,
        anchor_hardness_start: float = 0.35,
        anchor_hardness_end: float = 1.0,
        support_soft_roi_blend: float = 0.50,
        anchor_enable_start_ratio: float = 0.20,
        anchor_enable_full_ratio: float = 0.50,
        diffedit_config=None,
        inversion_backend=None,
    ) -> None:
        super().__init__(
            pipe,
            config,
            support_rho=support_rho,
            soft_roi_start_weight=soft_roi_start_weight,
            soft_roi_end_weight=soft_roi_end_weight,
            anchor_hardness_start=anchor_hardness_start,
            anchor_hardness_end=anchor_hardness_end,
            support_soft_roi_blend=support_soft_roi_blend,
            diffedit_config=diffedit_config,
            inversion_backend=inversion_backend,
        )
        self.anchor_enable_start_ratio = self._validate_unit_interval(
            anchor_enable_start_ratio,
            "anchor_enable_start_ratio",
        )
        self.anchor_enable_full_ratio = self._validate_unit_interval(
            anchor_enable_full_ratio,
            "anchor_enable_full_ratio",
        )
        if self.anchor_enable_full_ratio < self.anchor_enable_start_ratio:
            raise ValueError("anchor_enable_full_ratio must be >= anchor_enable_start_ratio")

    def _anchor_enable_gate(self, step_idx: int, total_steps: int) -> float:
        progress = self._schedule_progress(step_idx, total_steps)
        if progress <= self.anchor_enable_start_ratio:
            return 0.0
        if progress >= self.anchor_enable_full_ratio:
            return 1.0
        span = max(self.anchor_enable_full_ratio - self.anchor_enable_start_ratio, 1e-6)
        local_progress = (progress - self.anchor_enable_start_ratio) / span
        return self._cosine_schedule(0.0, 1.0, local_progress)

    def _delayed_anchor_mask(
        self,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor | None:
        base_anchor_mask = self._adaptive_anchor_mask(roi_mask, step_idx, total_steps)
        if base_anchor_mask is None:
            return None
        anchor_enable_gate = self._anchor_enable_gate(step_idx, total_steps)
        return torch.lerp(torch.ones_like(base_anchor_mask), base_anchor_mask, anchor_enable_gate).clamp(0.0, 1.0)

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_support_c2_delayed_anchor_v1",
                "background_anchor_policy": "after each scheduler step, source anchoring is delayed early and then smoothly enabled before the original adaptive roi-hardness schedule takes over",
                "background_anchor_enable_schedule": {
                    "start_ratio": self.anchor_enable_start_ratio,
                    "full_ratio": self.anchor_enable_full_ratio,
                    "formula": "g_t = 0 before start, cosine-ramp to 1 by full; A'_t = lerp(1, A_t, g_t)",
                },
            }
        )
        return payload

    def _post_scheduler_step_latents(
        self,
        method_name: str,
        prev_latents: torch.Tensor,
        roi_mask: torch.Tensor | None,
        source_latents: list[torch.Tensor],
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor:
        if roi_mask is None or method_name == "target_only" or not self._uses_diffedit_roi_cap(method_name):
            return prev_latents
        if not source_latents:
            return prev_latents

        anchor_mask = self._delayed_anchor_mask(roi_mask, step_idx, total_steps)
        if anchor_mask is None:
            return prev_latents
        next_source_idx = min(step_idx + 1, len(source_latents) - 1)
        source_anchor = source_latents[next_source_idx]
        if source_anchor.shape != prev_latents.shape:
            raise ValueError(
                f"source anchor shape mismatch: expected {tuple(prev_latents.shape)}, got {tuple(source_anchor.shape)}"
            )
        return anchor_mask * prev_latents + (1.0 - anchor_mask) * source_anchor

    def _finalize_step_aux_tensor(
        self,
        method_name: str,
        aux_tensor: dict[str, torch.Tensor],
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> dict[str, torch.Tensor]:
        aux_tensor = super()._finalize_step_aux_tensor(method_name, aux_tensor, roi_mask, step_idx, total_steps)
        if roi_mask is None or method_name == "target_only" or not self._uses_diffedit_roi_cap(method_name):
            return aux_tensor
        delayed_anchor_mask = self._delayed_anchor_mask(roi_mask, step_idx, total_steps)
        if delayed_anchor_mask is None:
            return aux_tensor
        aux_tensor["anchor_enable_gate"] = torch.full_like(roi_mask, self._anchor_enable_gate(step_idx, total_steps))
        aux_tensor["delayed_anchor_mask"] = delayed_anchor_mask
        return aux_tensor
