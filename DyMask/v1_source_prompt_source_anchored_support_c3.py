from __future__ import annotations

import torch

from .schemas import MaterializedSample
from .v1_source_prompt_source_anchored_support_c2 import V1SourcePromptSourceAnchoredSupportC2Editor


class V1SourcePromptSourceAnchoredSupportC3Editor(V1SourcePromptSourceAnchoredSupportC2Editor):
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
        support_soft_enable_start_ratio: float = 0.25,
        support_soft_enable_full_ratio: float = 0.60,
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
            anchor_enable_start_ratio=anchor_enable_start_ratio,
            anchor_enable_full_ratio=anchor_enable_full_ratio,
            diffedit_config=diffedit_config,
            inversion_backend=inversion_backend,
        )
        self.support_soft_enable_start_ratio = self._validate_unit_interval(
            support_soft_enable_start_ratio,
            "support_soft_enable_start_ratio",
        )
        self.support_soft_enable_full_ratio = self._validate_unit_interval(
            support_soft_enable_full_ratio,
            "support_soft_enable_full_ratio",
        )
        if self.support_soft_enable_full_ratio < self.support_soft_enable_start_ratio:
            raise ValueError("support_soft_enable_full_ratio must be >= support_soft_enable_start_ratio")

    def _support_soft_enable_gate(self, step_idx: int, total_steps: int) -> float:
        progress = self._schedule_progress(step_idx, total_steps)
        if progress <= self.support_soft_enable_start_ratio:
            return 0.0
        if progress >= self.support_soft_enable_full_ratio:
            return 1.0
        span = max(self.support_soft_enable_full_ratio - self.support_soft_enable_start_ratio, 1e-6)
        local_progress = (progress - self.support_soft_enable_start_ratio) / span
        return self._cosine_schedule(0.0, 1.0, local_progress)

    def _scheduled_support_soft_roi_blend(self, step_idx: int, total_steps: int) -> float:
        return self.support_soft_roi_blend * self._support_soft_enable_gate(step_idx, total_steps)

    def _scheduled_support_memory_roi(
        self,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor | None:
        if roi_mask is None:
            return None
        soft_roi_mask = self._resolve_soft_roi_mask(roi_mask)
        if soft_roi_mask is None:
            return roi_mask
        scheduled_blend = self._scheduled_support_soft_roi_blend(step_idx, total_steps)
        return torch.lerp(roi_mask, soft_roi_mask, scheduled_blend).clamp(0.0, 1.0)

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_support_c3_delayed_anchor_delayed_soft_support_v1",
                "roi_mask_policy": "adaptive support with delayed source anchoring and delayed soft-aware support memory",
                "support_memory_policy": {
                    "soft_roi_blend": self.support_soft_roi_blend,
                    "enable_start_ratio": self.support_soft_enable_start_ratio,
                    "enable_full_ratio": self.support_soft_enable_full_ratio,
                    "formula": "phi_t = dynamic_mask * lerp(roi_hard, roi_soft, beta * q_t), q_t = delayed cosine gate",
                },
            }
        )
        return payload

    def _compose_effective_mask_from_aux(
        self,
        method_name: str,
        dynamic_mask: torch.Tensor,
        aux_tensor: dict[str, torch.Tensor],
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor:
        if roi_mask is None or method_name == "target_only" or not self._uses_diffedit_roi_cap(method_name):
            return super()._compose_effective_mask_from_aux(
                method_name,
                dynamic_mask,
                aux_tensor,
                roi_mask,
                step_idx,
                total_steps,
            )
        support_memory_roi = self._scheduled_support_memory_roi(roi_mask, step_idx, total_steps)
        if support_memory_roi is None:
            return dynamic_mask
        return (support_memory_roi * dynamic_mask).clamp(0.0, 1.0)

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
        support_memory_roi = self._scheduled_support_memory_roi(roi_mask, step_idx, total_steps)
        if support_memory_roi is None:
            return aux_tensor
        support_soft_enable_gate = self._support_soft_enable_gate(step_idx, total_steps)
        scheduled_blend = self._scheduled_support_soft_roi_blend(step_idx, total_steps)
        aux_tensor["support_memory_roi"] = support_memory_roi
        aux_tensor["support_memory_soft_blend"] = torch.full_like(roi_mask, scheduled_blend)
        aux_tensor["support_soft_enable_gate"] = torch.full_like(roi_mask, support_soft_enable_gate)
        return aux_tensor
