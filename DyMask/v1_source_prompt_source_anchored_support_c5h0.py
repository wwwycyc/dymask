from __future__ import annotations

import torch

from .schemas import MaterializedSample
from .v1_source_prompt_source_anchored_support import V1SourcePromptSourceAnchoredSupportEditor
from .v1_source_prompt_source_anchored_support_c5 import V1SourcePromptSourceAnchoredSupportC5Editor
from .v1_source_prompt_temporal_support import V1SourcePromptTemporalSupportEditor


class V1SourcePromptSourceAnchoredSupportC5H0Editor(V1SourcePromptSourceAnchoredSupportC5Editor):
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
        return 0.0

    def _anchor_hardness(self, step_idx: int, total_steps: int) -> float:
        return 1.0

    def _confidence_anchor_roi_mask(
        self,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor | None:
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
        effective_mask = V1SourcePromptTemporalSupportEditor._effective_mask_from_support_state(
            self,
            method_name=method_name,
            support_state=support_state,
            roi_mask=roi_mask,
            step_idx=step_idx,
            total_steps=total_steps,
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
        components = dict(components)
        components["base_anchor_mask"] = base_anchor_mask
        components["relax_mask"] = relax_mask
        components["relaxed_anchor_mask"] = relaxed_anchor_mask
        components["relax_strength"] = torch.full_like(base_anchor_mask, relax_strength)
        return relaxed_anchor_mask, components

    def _finalize_step_aux_tensor(
        self,
        method_name: str,
        aux_tensor: dict[str, torch.Tensor],
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> dict[str, torch.Tensor]:
        aux_tensor = V1SourcePromptSourceAnchoredSupportEditor._finalize_step_aux_tensor(
            self,
            method_name,
            aux_tensor,
            roi_mask,
            step_idx,
            total_steps,
        )
        if roi_mask is None or method_name == "target_only" or not self._uses_diffedit_roi_cap(method_name):
            return aux_tensor
        aux_tensor["hard_roi_mask"] = roi_mask.clamp(0.0, 1.0)
        _anchor_mask, components = self._relaxed_anchor_mask(
            roi_mask=roi_mask,
            step_idx=step_idx,
            total_steps=total_steps,
            aux_tensor=aux_tensor,
        )
        if components is None:
            return aux_tensor
        aux_tensor["confidence_anchor_roi_mask"] = components["confidence_roi_mask"]
        aux_tensor["confidence_anchor_evidence"] = components["evidence"]
        aux_tensor["confidence_anchor_consistency"] = components["consistency"]
        aux_tensor["confidence_anchor_confidence"] = components["confidence"]
        aux_tensor["confidence_anchor_relax_mask"] = components["relax_mask"]
        aux_tensor["confidence_anchor_mask"] = components["relaxed_anchor_mask"]
        aux_tensor["confidence_anchor_strength"] = components["relax_strength"]
        return aux_tensor
