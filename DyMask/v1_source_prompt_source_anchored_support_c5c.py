from __future__ import annotations

import torch

from .schemas import MaterializedSample
from .v1_source_prompt_source_anchored_support_c5 import V1SourcePromptSourceAnchoredSupportC5Editor


class V1SourcePromptSourceAnchoredSupportC5CEditor(V1SourcePromptSourceAnchoredSupportC5Editor):
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
        control_soft_roi_quantile: float = 0.90,
        control_soft_roi_gamma: float = 1.0,
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
        self.control_soft_roi_quantile = self._validate_open_unit_interval(
            control_soft_roi_quantile,
            "control_soft_roi_quantile",
        )
        self.control_soft_roi_gamma = self._validate_positive(
            control_soft_roi_gamma,
            "control_soft_roi_gamma",
        )

    @staticmethod
    def _validate_open_unit_interval(value: float, name: str) -> float:
        scalar = float(value)
        if not 0.0 < scalar < 1.0:
            raise ValueError(f"{name} must be in (0, 1), got {scalar}")
        return scalar

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
                "variant": "source_prompt_source_anchored_support_c5c_control_soft_roi_v1",
                "control_soft_roi": {
                    "quantile": self.control_soft_roi_quantile,
                    "gamma": self.control_soft_roi_gamma,
                    "formula": (
                        "roi_soft_control = max(roi_hard, clamp((roi_soft / q)^gamma, 0, 1)), "
                        "where q is the per-sample high quantile of true roi_soft"
                    ),
                },
                "mechanism_note": (
                    "Keep true soft DiffEdit ROI for geometry and diagnostics, but rescale its amplitude "
                    "before using it in mask readout, anchor scheduling, and confidence gating."
                ),
            }
        )
        return payload

    def _control_soft_roi_mask(self, roi_mask: torch.Tensor | None) -> torch.Tensor | None:
        soft_roi_mask = self._resolve_soft_roi_mask(roi_mask)
        if soft_roi_mask is None:
            return roi_mask
        flat = soft_roi_mask.flatten(start_dim=2)
        flat_float = flat.to(dtype=torch.float32)
        quantile = torch.quantile(flat_float, self.control_soft_roi_quantile, dim=-1, keepdim=True)
        quantile = quantile.to(dtype=soft_roi_mask.dtype).view(soft_roi_mask.shape[0], 1, 1, 1).clamp(min=1e-6)
        control_soft_roi = (soft_roi_mask / quantile).clamp(0.0, 1.0)
        if self.control_soft_roi_gamma != 1.0:
            control_soft_roi = control_soft_roi.pow(self.control_soft_roi_gamma)
        if roi_mask is not None:
            control_soft_roi = torch.maximum(control_soft_roi, roi_mask)
        return control_soft_roi.clamp(0.0, 1.0)

    def _adaptive_anchor_mask(
        self,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor | None:
        if roi_mask is None:
            return None
        control_soft_roi = self._control_soft_roi_mask(roi_mask)
        if control_soft_roi is None:
            return roi_mask
        hardness = self._anchor_hardness(step_idx, total_steps)
        return torch.lerp(control_soft_roi, roi_mask, hardness).clamp(0.0, 1.0)

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
        control_soft_roi = self._control_soft_roi_mask(roi_mask)
        if control_soft_roi is None:
            return support_state
        soft_roi_weight = self._soft_roi_weight(step_idx, total_steps)
        effective_mask = torch.lerp(support_state, control_soft_roi, soft_roi_weight).clamp(0.0, 1.0)
        if self._latest_anchor_confidence_context is not None:
            self._cache_anchor_context(
                self._latest_anchor_confidence_context,
                support_state=support_state,
                effective_mask=effective_mask,
                roi_mask=roi_mask,
            )
        return effective_mask

    def _confidence_anchor_components(
        self,
        aux_tensor: dict[str, torch.Tensor] | None,
        roi_mask: torch.Tensor | None,
    ) -> dict[str, torch.Tensor] | None:
        if aux_tensor is None or roi_mask is None:
            return None
        soft_roi_mask = self._resolve_soft_roi_mask(roi_mask)
        control_soft_roi = self._control_soft_roi_mask(roi_mask)
        discrepancy = self._clamp_unit_tensor(aux_tensor.get("discrepancy"))
        dynamic_mask = self._clamp_unit_tensor(aux_tensor.get("dynamic_mask"))
        effective_mask = self._clamp_unit_tensor(aux_tensor.get("mask"))
        if (
            soft_roi_mask is None
            or control_soft_roi is None
            or discrepancy is None
            or dynamic_mask is None
            or effective_mask is None
        ):
            return None
        soft_roi_mask = soft_roi_mask.clamp(0.0, 1.0)
        control_soft_roi = control_soft_roi.clamp(0.0, 1.0)
        evidence = torch.sqrt((discrepancy * dynamic_mask).clamp(0.0, 1.0))
        consistency = (1.0 - torch.abs(effective_mask - dynamic_mask)).clamp(0.0, 1.0)
        confidence = (control_soft_roi * evidence * consistency).clamp(0.0, 1.0)
        return {
            "soft_roi_mask": soft_roi_mask,
            "control_soft_roi_mask": control_soft_roi,
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
        control_soft_roi = self._control_soft_roi_mask(roi_mask)
        if control_soft_roi is not None:
            aux_tensor["control_soft_roi_mask"] = control_soft_roi
            aux_tensor["control_soft_roi_quantile"] = torch.full_like(roi_mask, self.control_soft_roi_quantile)
            aux_tensor["control_soft_roi_gamma"] = torch.full_like(roi_mask, self.control_soft_roi_gamma)
        return aux_tensor
