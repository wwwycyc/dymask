from __future__ import annotations

import torch

from .schemas import MaterializedSample
from .v1_source_prompt_source_anchored_support_c5 import V1SourcePromptSourceAnchoredSupportC5Editor


class V1SourcePromptSourceAnchoredSupportC5BEditor(V1SourcePromptSourceAnchoredSupportC5Editor):
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
        mask_boundary_soft_scale: float = 1.0,
        anchor_boundary_soft_scale: float = 1.0,
        confidence_boundary_soft_scale: float = 1.0,
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
        self.mask_boundary_soft_scale = self._validate_unit_interval(
            mask_boundary_soft_scale,
            "mask_boundary_soft_scale",
        )
        self.anchor_boundary_soft_scale = self._validate_unit_interval(
            anchor_boundary_soft_scale,
            "anchor_boundary_soft_scale",
        )
        self.confidence_boundary_soft_scale = self._validate_unit_interval(
            confidence_boundary_soft_scale,
            "confidence_boundary_soft_scale",
        )

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_support_c5b_split_roi_roles_v1",
                "roi_mask_policy": (
                    "hard roi controls interior support writes and interior edit permission; "
                    "true soft roi contributes only a dynamic boundary tail outside the hard roi"
                ),
                "support_memory_policy": {
                    "formula": "S_t = rho * S_{t-1} + (1-rho) * (roi_hard * dynamic_mask)",
                },
                "effective_mask_policy": {
                    "mask_boundary_soft_scale": self.mask_boundary_soft_scale,
                    "formula": (
                        "M_t = roi_hard * S_t + beta_m * w_t * roi_soft * (1-roi_hard) * dynamic_mask"
                    ),
                },
                "background_anchor_policy": (
                    "inside hard roi keep edited latents fully; outside hard roi only retain a scheduled soft tail"
                ),
                "background_anchor_schedule": {
                    "anchor_boundary_soft_scale": self.anchor_boundary_soft_scale,
                    "formula": "A_t = roi_hard + beta_a * (1-h_t) * roi_soft * (1-roi_hard)",
                },
                "background_anchor_relaxation": {
                    "confidence_boundary_soft_scale": self.confidence_boundary_soft_scale,
                    "formula": (
                        "G_t = roi_hard + beta_c * roi_soft * (1-roi_hard); "
                        "R_t = alpha_t * G_t * sqrt(discrepancy * dynamic_mask) * (1 - |mask - dynamic_mask|)"
                    ),
                },
            }
        )
        return payload

    def _soft_boundary_tail(self, roi_mask: torch.Tensor | None) -> torch.Tensor | None:
        if roi_mask is None:
            return None
        soft_roi_mask = self._resolve_soft_roi_mask(roi_mask)
        if soft_roi_mask is None:
            return None
        boundary_tail = (1.0 - roi_mask).clamp(0.0, 1.0)
        return (soft_roi_mask.clamp(0.0, 1.0) * boundary_tail).clamp(0.0, 1.0)

    def _adaptive_anchor_mask(
        self,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor | None:
        if roi_mask is None:
            return None
        boundary_tail = self._soft_boundary_tail(roi_mask)
        if boundary_tail is None:
            return roi_mask
        boundary_scale = (1.0 - self._anchor_hardness(step_idx, total_steps)) * self.anchor_boundary_soft_scale
        boundary_keep = (boundary_scale * boundary_tail).clamp(0.0, 1.0)
        return (roi_mask + boundary_keep).clamp(0.0, 1.0)

    def _effective_mask_from_support_state(
        self,
        method_name: str,
        support_state: torch.Tensor,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor:
        if roi_mask is None or method_name == "target_only" or not self._uses_diffedit_roi_cap(method_name):
            return support_state

        hard_interior = (roi_mask * support_state).clamp(0.0, 1.0)
        boundary_tail = self._soft_boundary_tail(roi_mask)
        if boundary_tail is None:
            return hard_interior

        dynamic_mask = None
        if self._latest_anchor_confidence_context is not None:
            dynamic_mask = self._clamp_unit_tensor(self._latest_anchor_confidence_context.get("dynamic_mask"))
        boundary_component = boundary_tail if dynamic_mask is None else (boundary_tail * dynamic_mask).clamp(0.0, 1.0)
        boundary_scale = self.mask_boundary_soft_scale * self._soft_roi_weight(step_idx, total_steps)
        return (hard_interior + boundary_scale * boundary_component).clamp(0.0, 1.0)

    def _confidence_anchor_components(
        self,
        aux_tensor: dict[str, torch.Tensor] | None,
        roi_mask: torch.Tensor | None,
    ) -> dict[str, torch.Tensor] | None:
        if aux_tensor is None or roi_mask is None:
            return None
        soft_roi_mask = self._resolve_soft_roi_mask(roi_mask)
        discrepancy = self._clamp_unit_tensor(aux_tensor.get("discrepancy"))
        dynamic_mask = self._clamp_unit_tensor(aux_tensor.get("dynamic_mask"))
        effective_mask = self._clamp_unit_tensor(aux_tensor.get("mask"))
        if soft_roi_mask is None or discrepancy is None or dynamic_mask is None or effective_mask is None:
            return None

        soft_roi_mask = soft_roi_mask.clamp(0.0, 1.0)
        boundary_tail = self._soft_boundary_tail(roi_mask)
        spatial_gate = roi_mask.clamp(0.0, 1.0)
        if boundary_tail is not None:
            spatial_gate = (spatial_gate + self.confidence_boundary_soft_scale * boundary_tail).clamp(0.0, 1.0)

        evidence = torch.sqrt((discrepancy * dynamic_mask).clamp(0.0, 1.0))
        consistency = (1.0 - torch.abs(effective_mask - dynamic_mask)).clamp(0.0, 1.0)
        confidence = (spatial_gate * evidence * consistency).clamp(0.0, 1.0)
        return {
            "soft_roi_mask": soft_roi_mask,
            "soft_boundary_tail": boundary_tail if boundary_tail is not None else torch.zeros_like(roi_mask),
            "spatial_gate": spatial_gate,
            "evidence": evidence,
            "consistency": consistency,
            "confidence": confidence,
        }

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

        boundary_tail = self._soft_boundary_tail(roi_mask)
        if boundary_tail is not None:
            aux_tensor["roi_soft_boundary"] = boundary_tail
        aux_tensor["mask_boundary_soft_scale"] = torch.full_like(roi_mask, self.mask_boundary_soft_scale)
        aux_tensor["anchor_boundary_soft_scale"] = torch.full_like(roi_mask, self.anchor_boundary_soft_scale)
        aux_tensor["confidence_boundary_soft_scale"] = torch.full_like(roi_mask, self.confidence_boundary_soft_scale)

        _anchor_mask, components = self._relaxed_anchor_mask(
            roi_mask=roi_mask,
            step_idx=step_idx,
            total_steps=total_steps,
            aux_tensor=aux_tensor,
        )
        if components is None:
            return aux_tensor
        aux_tensor["confidence_anchor_spatial_gate"] = components["spatial_gate"]
        aux_tensor["confidence_anchor_soft_boundary"] = components["soft_boundary_tail"]
        return aux_tensor
