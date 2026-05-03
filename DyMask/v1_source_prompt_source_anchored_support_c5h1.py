from __future__ import annotations

import torch

from .schemas import MaterializedSample
from .v1_source_prompt_source_anchored_support_c5h0 import V1SourcePromptSourceAnchoredSupportC5H0Editor


class V1SourcePromptSourceAnchoredSupportC5H1Editor(V1SourcePromptSourceAnchoredSupportC5H0Editor):
    def __init__(
        self,
        pipe,
        config,
        support_rho: float = 0.85,
        soft_roi_start_weight: float = 0.75,
        soft_roi_end_weight: float = 0.10,
        anchor_hardness_start: float = 0.35,
        anchor_hardness_end: float = 1.0,
        anchor_relax_start_strength: float = 0.35,
        anchor_relax_end_strength: float = 0.05,
        soft_boundary_start_weight: float = 0.18,
        soft_boundary_end_weight: float = 0.04,
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
            anchor_relax_start_strength=anchor_relax_start_strength,
            anchor_relax_end_strength=anchor_relax_end_strength,
            diffedit_config=diffedit_config,
            inversion_backend=inversion_backend,
        )
        self.soft_boundary_start_weight = self._validate_unit_interval(
            soft_boundary_start_weight,
            "soft_boundary_start_weight",
        )
        self.soft_boundary_end_weight = self._validate_unit_interval(
            soft_boundary_end_weight,
            "soft_boundary_end_weight",
        )
        if self.soft_boundary_end_weight > self.soft_boundary_start_weight:
            raise ValueError("soft_boundary_end_weight must be <= soft_boundary_start_weight")

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_support_c5h1_hard_core_soft_boundary_v1",
                "roi_mask_policy": (
                    "temporal support stays hard-core, while a thin soft boundary is added only outside the hard roi"
                ),
                "soft_roi_schedule": {
                    "start_weight": self.soft_boundary_start_weight,
                    "end_weight": self.soft_boundary_end_weight,
                    "formula": "M_t = clamp(S_t + b_t * boundary_soft, 0, 1), b_t follows cosine decay",
                },
                "background_anchor_policy": (
                    "after each scheduler step, start from hard roi and add only a thin soft boundary before "
                    "confidence-gated anchor relaxation"
                ),
                "background_anchor_schedule": {
                    "start_hardness": 1.0 - self.soft_boundary_start_weight,
                    "end_hardness": 1.0 - self.soft_boundary_end_weight,
                    "formula": "A_t = clamp(roi_hard + b_t * boundary_soft, 0, 1)",
                },
                "background_anchor_relaxation": {
                    "start_strength": self.anchor_relax_start_strength,
                    "end_strength": self.anchor_relax_end_strength,
                    "formula": (
                        "boundary_soft = relu(roi_soft - roi_hard); "
                        "A_t = clamp(roi_hard + b_t * boundary_soft, 0, 1); "
                        "R_t = alpha_t * A_t * sqrt(discrepancy * dynamic_mask) * (1 - |mask - dynamic_mask|); "
                        "A'_t = lerp(A_t, 1, R_t)"
                    ),
                },
            }
        )
        return payload

    def _soft_roi_weight(self, step_idx: int, total_steps: int) -> float:
        return self._boundary_weight(step_idx, total_steps)

    def _anchor_hardness(self, step_idx: int, total_steps: int) -> float:
        return 1.0 - self._boundary_weight(step_idx, total_steps)

    def _boundary_weight(self, step_idx: int, total_steps: int) -> float:
        return self._cosine_schedule(
            self.soft_boundary_start_weight,
            self.soft_boundary_end_weight,
            self._schedule_progress(step_idx, total_steps),
        )

    def _soft_boundary_mask(self, roi_mask: torch.Tensor | None) -> torch.Tensor | None:
        if roi_mask is None:
            return None
        soft_roi_mask = self._resolve_soft_roi_mask(roi_mask)
        if soft_roi_mask is None:
            return None
        return (soft_roi_mask.clamp(0.0, 1.0) - roi_mask.clamp(0.0, 1.0)).clamp(0.0, 1.0)

    def _boundary_augmented_roi_mask(
        self,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor | None:
        if roi_mask is None:
            return None
        boundary_mask = self._soft_boundary_mask(roi_mask)
        if boundary_mask is None:
            return roi_mask.clamp(0.0, 1.0)
        return (roi_mask.clamp(0.0, 1.0) + self._boundary_weight(step_idx, total_steps) * boundary_mask).clamp(0.0, 1.0)

    def _effective_mask_from_support_state(
        self,
        method_name: str,
        support_state: torch.Tensor,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor:
        effective_mask = support_state
        if roi_mask is not None and method_name != "target_only" and self._uses_diffedit_roi_cap(method_name):
            boundary_mask = self._soft_boundary_mask(roi_mask)
            if boundary_mask is not None:
                effective_mask = (effective_mask + self._boundary_weight(step_idx, total_steps) * boundary_mask).clamp(
                    0.0,
                    1.0,
                )
        if (
            roi_mask is not None
            and method_name != "target_only"
            and self._uses_diffedit_roi_cap(method_name)
            and self._latest_anchor_confidence_context is not None
        ):
            self._cache_anchor_context(
                self._latest_anchor_confidence_context,
                support_state=support_state,
                effective_mask=effective_mask,
                roi_mask=roi_mask,
            )
        return effective_mask

    def _adaptive_anchor_mask(
        self,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor | None:
        return self._boundary_augmented_roi_mask(roi_mask, step_idx, total_steps)

    def _confidence_anchor_roi_mask(
        self,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor | None:
        return self._boundary_augmented_roi_mask(roi_mask, step_idx, total_steps)

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
        boundary_mask = self._soft_boundary_mask(roi_mask)
        if boundary_mask is None:
            return aux_tensor
        aux_tensor["soft_boundary_mask"] = boundary_mask
        aux_tensor["soft_boundary_weight"] = torch.full_like(roi_mask, self._boundary_weight(step_idx, total_steps))
        aux_tensor["soft_boundary_augmented_roi"] = self._boundary_augmented_roi_mask(roi_mask, step_idx, total_steps)
        return aux_tensor
