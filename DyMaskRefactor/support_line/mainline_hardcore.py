from __future__ import annotations

import torch

from DyMaskRefactor.schemas import MaterializedSample

from DyMaskRefactor.support_line.schedules import cosine_schedule, schedule_progress, validate_unit_interval
from DyMaskRefactor.support_line.variants_confidence import RefactorSupportC5Editor


class RefactorSupportC5H0Editor(RefactorSupportC5Editor):
    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_support_c5h0_hard_core_v1",
                "roi_mask_policy": (
                    "temporal support writes and readout stay on hard roi only; "
                    "soft roi is retained only as diagnostic reference"
                ),
                "soft_roi_schedule": {
                    "start_weight": 0.0,
                    "end_weight": 0.0,
                    "formula": "disabled; M_t = S_t",
                },
                "background_anchor_policy": (
                    "after each scheduler step, use hard roi as the anchor base and relax it only where "
                    "hard roi, discrepancy, and dynamic support agree"
                ),
                "background_anchor_schedule": {
                    "start_hardness": 1.0,
                    "end_hardness": 1.0,
                    "formula": "A_t = roi_hard",
                },
                "background_anchor_relaxation": {
                    "start_strength": self.anchor_relax_start_strength,
                    "end_strength": self.anchor_relax_end_strength,
                    "formula": (
                        "R_t = alpha_t * roi_hard * sqrt(discrepancy * dynamic_mask) * "
                        "(1 - |mask - dynamic_mask|); A'_t = lerp(roi_hard, 1, R_t)"
                    ),
                },
            }
        )
        return payload

    def _soft_roi_weight(self, step_idx: int, total_steps: int) -> float:
        _ = step_idx
        _ = total_steps
        return 0.0

    def _anchor_hardness(self, step_idx: int, total_steps: int) -> float:
        _ = step_idx
        _ = total_steps
        return 1.0

    def _confidence_anchor_roi_mask(
        self,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor | None:
        _ = step_idx
        _ = total_steps
        if roi_mask is None:
            return None
        return roi_mask.clamp(0.0, 1.0)

    def _confidence_anchor_components(
        self,
        aux_tensor: dict[str, torch.Tensor] | None,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> dict[str, torch.Tensor] | None:
        if aux_tensor is None or roi_mask is None:
            return None
        confidence_roi_mask = self._confidence_anchor_roi_mask(roi_mask, step_idx, total_steps)
        discrepancy = self._clamp_unit_tensor(aux_tensor.get("discrepancy"))
        dynamic_mask = self._clamp_unit_tensor(aux_tensor.get("dynamic_mask"))
        effective_mask = self._clamp_unit_tensor(aux_tensor.get("mask"))
        if confidence_roi_mask is None or discrepancy is None or dynamic_mask is None or effective_mask is None:
            return None
        confidence_roi_mask = confidence_roi_mask.clamp(0.0, 1.0)
        evidence = torch.sqrt((discrepancy * dynamic_mask).clamp(0.0, 1.0))
        consistency = (1.0 - torch.abs(effective_mask - dynamic_mask)).clamp(0.0, 1.0)
        confidence = (confidence_roi_mask * evidence * consistency).clamp(0.0, 1.0)
        return {
            "confidence_roi_mask": confidence_roi_mask,
            "evidence": evidence,
            "consistency": consistency,
            "confidence": confidence,
        }

    def _effective_mask_from_support_state(
        self,
        method_name: str,
        support_state: torch.Tensor,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor:
        _ = step_idx
        _ = total_steps
        effective_mask = support_state
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
        _ = step_idx
        _ = total_steps
        if roi_mask is None:
            return None
        return roi_mask.clamp(0.0, 1.0)

    def _relaxed_anchor_mask(
        self,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
        aux_tensor: dict[str, torch.Tensor] | None,
    ) -> tuple[torch.Tensor | None, dict[str, torch.Tensor] | None]:
        base_anchor_mask = self._adaptive_anchor_mask(roi_mask, step_idx, total_steps)
        if base_anchor_mask is None:
            return None, None
        components = self._confidence_anchor_components(aux_tensor, roi_mask, step_idx, total_steps)
        if components is None:
            return base_anchor_mask, None
        relax_strength = self._anchor_relax_strength(step_idx, total_steps)
        relax_mask = (relax_strength * components["confidence"]).clamp(0.0, 1.0)
        relaxed_anchor_mask = torch.lerp(base_anchor_mask, torch.ones_like(base_anchor_mask), relax_mask).clamp(0.0, 1.0)
        enriched = dict(components)
        enriched["base_anchor_mask"] = base_anchor_mask
        enriched["relax_mask"] = relax_mask
        enriched["relaxed_anchor_mask"] = relaxed_anchor_mask
        enriched["relax_strength"] = torch.full_like(base_anchor_mask, relax_strength)
        return relaxed_anchor_mask, enriched

    def _anchor_mask(
        self,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor | None:
        anchor_mask, _components = self._relaxed_anchor_mask(
            roi_mask=roi_mask,
            step_idx=step_idx,
            total_steps=total_steps,
            aux_tensor=self._latest_anchor_confidence_context,
        )
        return anchor_mask

    def _extra_step_aux_tensors(
        self,
        method_name: str,
        aux_tensor: dict[str, torch.Tensor],
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> dict[str, torch.Tensor]:
        if roi_mask is None or method_name == "target_only" or not self._uses_diffedit_roi_cap(method_name):
            return {}
        _anchor_mask, components = self._relaxed_anchor_mask(
            roi_mask=roi_mask,
            step_idx=step_idx,
            total_steps=total_steps,
            aux_tensor=aux_tensor,
        )
        if components is None:
            return {"hard_roi_mask": roi_mask.clamp(0.0, 1.0)}
        return {
            "hard_roi_mask": roi_mask.clamp(0.0, 1.0),
            "confidence_anchor_roi_mask": components["confidence_roi_mask"],
            "confidence_anchor_evidence": components["evidence"],
            "confidence_anchor_consistency": components["consistency"],
            "confidence_anchor_confidence": components["confidence"],
            "confidence_anchor_relax_mask": components["relax_mask"],
            "confidence_anchor_mask": components["relaxed_anchor_mask"],
            "confidence_anchor_strength": components["relax_strength"],
        }

class RefactorSupportC5H1Editor(RefactorSupportC5H0Editor):
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
        self.soft_boundary_start_weight = validate_unit_interval(
            soft_boundary_start_weight,
            "soft_boundary_start_weight",
        )
        self.soft_boundary_end_weight = validate_unit_interval(
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

    def _boundary_weight(self, step_idx: int, total_steps: int) -> float:
        return cosine_schedule(
            self.soft_boundary_start_weight,
            self.soft_boundary_end_weight,
            schedule_progress(step_idx, total_steps),
        )

    def _soft_roi_weight(self, step_idx: int, total_steps: int) -> float:
        return self._boundary_weight(step_idx, total_steps)

    def _anchor_hardness(self, step_idx: int, total_steps: int) -> float:
        return 1.0 - self._boundary_weight(step_idx, total_steps)

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

    def _extra_step_aux_tensors(
        self,
        method_name: str,
        aux_tensor: dict[str, torch.Tensor],
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> dict[str, torch.Tensor]:
        tensors = super()._extra_step_aux_tensors(method_name, aux_tensor, roi_mask, step_idx, total_steps)
        if roi_mask is None or method_name == "target_only" or not self._uses_diffedit_roi_cap(method_name):
            return tensors
        boundary_mask = self._soft_boundary_mask(roi_mask)
        if boundary_mask is None:
            return tensors
        tensors["soft_boundary_mask"] = boundary_mask
        tensors["soft_boundary_weight"] = torch.full_like(roi_mask, self._boundary_weight(step_idx, total_steps))
        tensors["soft_boundary_augmented_roi"] = self._boundary_augmented_roi_mask(roi_mask, step_idx, total_steps)
        return tensors

__all__ = [
    "RefactorSupportC5H0Editor",
    "RefactorSupportC5H1Editor",
]
