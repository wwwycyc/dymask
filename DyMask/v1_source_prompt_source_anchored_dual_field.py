from __future__ import annotations

from .preservation_field import (
    PreservationFieldConfig,
    build_preservation_field,
    build_source_consistency_field,
)
from .schemas import MaterializedSample
from .transformation_field import TransformationFieldConfig, build_transformation_field
from .v1_source_prompt_source_anchored_hard_roi import V1SourcePromptSourceAnchoredHardRoiEditor

import torch


class V1SourcePromptSourceAnchoredDualFieldEditor(V1SourcePromptSourceAnchoredHardRoiEditor):
    def __init__(
        self,
        pipe,
        config,
        dual_field_mode: str = "full",
        transform_discrepancy_weight: float = 1.0,
        transform_attention_weight: float = 1.0,
        preservation_latent_weight: float = 1.0,
        diffedit_config=None,
        inversion_backend=None,
    ) -> None:
        super().__init__(
            pipe,
            config,
            diffedit_config=diffedit_config,
            inversion_backend=inversion_backend,
        )
        if dual_field_mode not in {"full", "transform_only", "preservation_only"}:
            raise ValueError(f"unsupported dual_field_mode: {dual_field_mode}")
        self.dual_field_mode = dual_field_mode
        self.transform_config = TransformationFieldConfig(
            discrepancy_weight=float(transform_discrepancy_weight),
            attention_weight=float(transform_attention_weight),
        )
        self.preservation_config = PreservationFieldConfig(
            latent_weight=float(preservation_latent_weight),
        )

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_dual_field_v1",
                "roi_mask_policy": "hard roi support with outside-roi source anchoring and roi-internal dual-field execution",
                "dual_field_mode": self.dual_field_mode,
                "transformation_formula": "T_t = (w_d * D_t + w_a * A_t) / (w_d + w_a)",
                "preservation_formula": "P_t = clamp(w_c * C_t, 0, 1)",
                "effective_mask_formula": {
                    "full": "M_t = roi_mask * T_t * (1 - P_t)",
                    "transform_only": "M_t = roi_mask * T_t",
                    "preservation_only": "M_t = roi_mask * (1 - P_t)",
                }[self.dual_field_mode],
                "transform_discrepancy_weight": self.transform_config.discrepancy_weight,
                "transform_attention_weight": self.transform_config.attention_weight,
                "preservation_latent_weight": self.preservation_config.latent_weight,
            }
        )
        return payload

    def _update_support_state(
        self,
        previous_state: torch.Tensor | None,
        evidence: torch.Tensor,
    ) -> torch.Tensor:
        return evidence

    def _transformation_field_for_method(
        self,
        method_name: str,
        aux_tensor: dict[str, torch.Tensor],
    ) -> torch.Tensor:
        attention_weight = self.transform_config.attention_weight
        if method_name not in {"discrepancy_attention", "full_dynamic_mask"}:
            attention_weight = 0.0
        config = TransformationFieldConfig(
            discrepancy_weight=self.transform_config.discrepancy_weight,
            attention_weight=attention_weight,
        )
        return build_transformation_field(
            discrepancy=aux_tensor["discrepancy"],
            attention=aux_tensor["attention"],
            config=config,
        )

    def _compose_effective_mask_from_aux(
        self,
        method_name: str,
        dynamic_mask: torch.Tensor,
        aux_tensor: dict[str, torch.Tensor],
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor:
        if method_name == "target_only" or roi_mask is None or not self._uses_diffedit_roi_cap(method_name):
            return dynamic_mask

        transformation_field = self._transformation_field_for_method(method_name, aux_tensor)
        preservation_field = build_preservation_field(
            latent_drift=aux_tensor["latent_drift"],
            config=self.preservation_config,
        )
        source_consistency = build_source_consistency_field(aux_tensor["latent_drift"])

        if self.dual_field_mode == "transform_only":
            effective_mask = roi_mask * transformation_field
        elif self.dual_field_mode == "preservation_only":
            effective_mask = roi_mask * (1.0 - preservation_field)
        else:
            effective_mask = roi_mask * transformation_field * (1.0 - preservation_field)

        effective_mask = torch.clamp(effective_mask, 0.0, 1.0).to(
            device=dynamic_mask.device,
            dtype=dynamic_mask.dtype,
        )
        aux_tensor["transformation_field"] = transformation_field
        aux_tensor["preservation_field"] = preservation_field
        aux_tensor["source_consistency"] = source_consistency
        aux_tensor["dual_field_mask"] = effective_mask
        return effective_mask
