from __future__ import annotations

import torch

from .schemas import MaterializedSample
from .v1_source_prompt_source_anchored_support import V1SourcePromptSourceAnchoredSupportEditor


class V1SourcePromptSourceAnchoredSupportC4OnlyEditor(V1SourcePromptSourceAnchoredSupportEditor):
    def __init__(
        self,
        pipe,
        config,
        support_rho: float = 0.85,
        soft_roi_start_weight: float = 0.75,
        soft_roi_end_weight: float = 0.10,
        anchor_hardness_start: float = 0.35,
        anchor_hardness_end: float = 1.0,
        support_floor_start_ratio: float = 0.45,
        support_floor_full_ratio: float = 0.80,
        support_floor_max: float = 0.20,
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
            diffedit_config=diffedit_config,
            inversion_backend=inversion_backend,
        )
        self.support_floor_start_ratio = self._validate_unit_interval(
            support_floor_start_ratio,
            "support_floor_start_ratio",
        )
        self.support_floor_full_ratio = self._validate_unit_interval(
            support_floor_full_ratio,
            "support_floor_full_ratio",
        )
        self.support_floor_max = self._validate_unit_interval(
            support_floor_max,
            "support_floor_max",
        )
        if self.support_floor_full_ratio < self.support_floor_start_ratio:
            raise ValueError("support_floor_full_ratio must be >= support_floor_start_ratio")

    def _support_floor_gate(self, step_idx: int, total_steps: int) -> float:
        progress = self._schedule_progress(step_idx, total_steps)
        if progress <= self.support_floor_start_ratio:
            return 0.0
        if progress >= self.support_floor_full_ratio:
            return 1.0
        span = max(self.support_floor_full_ratio - self.support_floor_start_ratio, 1e-6)
        local_progress = (progress - self.support_floor_start_ratio) / span
        return self._cosine_schedule(0.0, 1.0, local_progress)

    def _scheduled_support_floor_strength(self, step_idx: int, total_steps: int) -> float:
        return self.support_floor_max * self._support_floor_gate(step_idx, total_steps)

    def _support_floor_mask(
        self,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor | None:
        if roi_mask is None:
            return None
        support_floor_roi = self._resolve_soft_roi_mask(roi_mask)
        if support_floor_roi is None:
            return None
        strength = self._scheduled_support_floor_strength(step_idx, total_steps)
        return (strength * support_floor_roi).clamp(0.0, 1.0)

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_support_c4_only_late_roi_floor_v1",
                "roi_mask_policy": "baseline adaptive support with an additional late soft-roi floor so weak support does not collapse into near-zero edit drive",
                "support_floor_policy": {
                    "start_ratio": self.support_floor_start_ratio,
                    "full_ratio": self.support_floor_full_ratio,
                    "max_strength": self.support_floor_max,
                    "formula": "F_t = alpha_t * roi_soft, alpha_t is a late cosine gate",
                },
            }
        )
        return payload

    def _effective_mask_from_support_state(
        self,
        method_name: str,
        support_state: torch.Tensor,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor:
        effective_mask = super()._effective_mask_from_support_state(
            method_name=method_name,
            support_state=support_state,
            roi_mask=roi_mask,
            step_idx=step_idx,
            total_steps=total_steps,
        )
        if roi_mask is None or method_name == "target_only" or not self._uses_diffedit_roi_cap(method_name):
            return effective_mask
        support_floor_mask = self._support_floor_mask(roi_mask, step_idx, total_steps)
        if support_floor_mask is None:
            return effective_mask
        return torch.maximum(effective_mask, support_floor_mask).clamp(0.0, 1.0)

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
        support_floor_mask = self._support_floor_mask(roi_mask, step_idx, total_steps)
        if support_floor_mask is None:
            return aux_tensor
        aux_tensor["support_floor_mask"] = support_floor_mask
        aux_tensor["support_floor_gate"] = torch.full_like(roi_mask, self._support_floor_gate(step_idx, total_steps))
        aux_tensor["support_floor_strength"] = torch.full_like(
            roi_mask,
            self._scheduled_support_floor_strength(step_idx, total_steps),
        )
        return aux_tensor
