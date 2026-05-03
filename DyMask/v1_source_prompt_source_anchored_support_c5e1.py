from __future__ import annotations

import torch

from .schemas import MaterializedSample
from .v1_source_prompt_source_anchored_support_c5 import V1SourcePromptSourceAnchoredSupportC5Editor


class V1SourcePromptSourceAnchoredSupportC5E1Editor(V1SourcePromptSourceAnchoredSupportC5Editor):
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
        confidence_deficit_rescue_strength: float = 0.30,
        confidence_deficit_gap_power: float = 1.0,
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
        self.confidence_deficit_rescue_strength = self._validate_unit_interval(
            confidence_deficit_rescue_strength,
            "confidence_deficit_rescue_strength",
        )
        self.confidence_deficit_gap_power = self._validate_positive(
            confidence_deficit_gap_power,
            "confidence_deficit_gap_power",
        )

    @staticmethod
    def _validate_positive(value: float, name: str) -> float:
        scalar = float(value)
        if scalar <= 0.0:
            raise ValueError(f"{name} must be > 0, got {scalar}")
        return scalar

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_support_c5e1_deficit_confidence_rescue_v1",
                "mechanism_note": (
                    "Keep true-soft C5 readout and baseline adaptive anchor schedule unchanged. "
                    "Only add a local confidence rescue where the instantaneous dynamic mask wants more edit "
                    "than the effective mask currently permits."
                ),
                "background_anchor_relaxation_rescue": {
                    "deficit_rescue_strength": self.confidence_deficit_rescue_strength,
                    "deficit_gap_power": self.confidence_deficit_gap_power,
                    "formula": (
                        "gap = relu(dynamic_mask - mask); rescue = roi_soft * sqrt(discrepancy * dynamic_mask) * gap^p; "
                        "confidence' = clamp(confidence + lambda * rescue, 0, 1)"
                    ),
                },
            }
        )
        return payload

    def _confidence_anchor_components(
        self,
        aux_tensor: dict[str, torch.Tensor] | None,
        roi_mask: torch.Tensor | None,
    ) -> dict[str, torch.Tensor] | None:
        components = super()._confidence_anchor_components(aux_tensor, roi_mask)
        if components is None or aux_tensor is None:
            return components

        dynamic_mask = self._clamp_unit_tensor(aux_tensor.get("dynamic_mask"))
        effective_mask = self._clamp_unit_tensor(aux_tensor.get("mask"))
        if dynamic_mask is None or effective_mask is None:
            return components

        deficit_gap = (dynamic_mask - effective_mask).clamp(0.0, 1.0)
        if self.confidence_deficit_gap_power != 1.0:
            deficit_gap = deficit_gap.pow(self.confidence_deficit_gap_power)

        rescue = (components["soft_roi_mask"] * components["evidence"] * deficit_gap).clamp(0.0, 1.0)
        base_confidence = components["confidence"]
        rescued_confidence = (
            base_confidence + self.confidence_deficit_rescue_strength * rescue
        ).clamp(0.0, 1.0)

        updated = dict(components)
        updated["base_confidence"] = base_confidence
        updated["deficit_gap"] = deficit_gap
        updated["deficit_rescue"] = rescue
        updated["rescued_confidence"] = rescued_confidence
        updated["confidence"] = rescued_confidence
        updated["deficit_rescue_strength"] = torch.full_like(base_confidence, self.confidence_deficit_rescue_strength)
        updated["deficit_gap_power"] = torch.full_like(base_confidence, self.confidence_deficit_gap_power)
        return updated

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

        components = self._confidence_anchor_components(aux_tensor, roi_mask)
        if components is None:
            return aux_tensor

        aux_tensor["confidence_anchor_base_confidence"] = components["base_confidence"]
        aux_tensor["confidence_anchor_deficit_gap"] = components["deficit_gap"]
        aux_tensor["confidence_anchor_deficit_rescue"] = components["deficit_rescue"]
        aux_tensor["confidence_anchor_rescued_confidence"] = components["rescued_confidence"]
        aux_tensor["confidence_anchor_deficit_rescue_strength"] = components["deficit_rescue_strength"]
        aux_tensor["confidence_anchor_deficit_gap_power"] = components["deficit_gap_power"]
        return aux_tensor
