from __future__ import annotations

import torch

from .schemas import MaterializedSample
from .v1_source_prompt_source_anchored_support_c5c import V1SourcePromptSourceAnchoredSupportC5CEditor


class V1SourcePromptSourceAnchoredSupportC5DEditor(V1SourcePromptSourceAnchoredSupportC5CEditor):
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
        adaptive_target_p90: float = 0.75,
        adaptive_trigger_p90: float = 0.55,
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
            control_soft_roi_quantile=control_soft_roi_quantile,
            control_soft_roi_gamma=control_soft_roi_gamma,
            diffedit_config=diffedit_config,
            inversion_backend=inversion_backend,
        )
        self.adaptive_target_p90 = self._validate_unit_interval(adaptive_target_p90, "adaptive_target_p90")
        self.adaptive_trigger_p90 = self._validate_unit_interval(adaptive_trigger_p90, "adaptive_trigger_p90")
        if self.adaptive_trigger_p90 >= self.adaptive_target_p90:
            raise ValueError("adaptive_trigger_p90 must be < adaptive_target_p90")

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_support_c5d_adaptive_control_soft_roi_v1",
                "adaptive_control_soft_roi": {
                    "target_p90": self.adaptive_target_p90,
                    "trigger_p90": self.adaptive_trigger_p90,
                    "formula": (
                        "boost_strength = clamp((target_p90 - q90) / (target_p90 - trigger_p90), 0, 1); "
                        "roi_soft_control = lerp(roi_soft, roi_soft_rescaled, boost_strength)"
                    ),
                },
                "mechanism_note": (
                    "Only rescue flat or sparse soft-roi cases. When the true soft-roi high quantile is already strong, "
                    "keep the corrected C5 behavior. When it is weak, partially blend toward the rescaled control map."
                ),
            }
        )
        return payload

    def _control_soft_roi_mask(self, roi_mask: torch.Tensor | None) -> torch.Tensor | None:
        soft_roi_mask = self._resolve_soft_roi_mask(roi_mask)
        if soft_roi_mask is None:
            return roi_mask
        boosted_control = super()._control_soft_roi_mask(roi_mask)
        if boosted_control is None:
            return soft_roi_mask
        flat = soft_roi_mask.flatten(start_dim=2).to(dtype=torch.float32)
        q90 = torch.quantile(flat, self.control_soft_roi_quantile, dim=-1, keepdim=True)
        q90 = q90.view(soft_roi_mask.shape[0], 1, 1, 1).to(dtype=soft_roi_mask.dtype)
        denom = max(self.adaptive_target_p90 - self.adaptive_trigger_p90, 1e-6)
        boost_strength = ((self.adaptive_target_p90 - q90) / denom).clamp(0.0, 1.0)
        control_soft_roi = torch.lerp(soft_roi_mask, boosted_control, boost_strength).clamp(0.0, 1.0)
        if roi_mask is not None:
            control_soft_roi = torch.maximum(control_soft_roi, roi_mask)
        return control_soft_roi

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
        soft_roi_mask = self._resolve_soft_roi_mask(roi_mask)
        if soft_roi_mask is None:
            return aux_tensor
        flat = soft_roi_mask.flatten(start_dim=2).to(dtype=torch.float32)
        q90 = torch.quantile(flat, self.control_soft_roi_quantile, dim=-1, keepdim=True)
        q90 = q90.view(soft_roi_mask.shape[0], 1, 1, 1).to(dtype=soft_roi_mask.dtype)
        denom = max(self.adaptive_target_p90 - self.adaptive_trigger_p90, 1e-6)
        boost_strength = ((self.adaptive_target_p90 - q90) / denom).clamp(0.0, 1.0)
        aux_tensor["adaptive_control_soft_roi_q90"] = q90.expand_as(soft_roi_mask)
        aux_tensor["adaptive_control_soft_roi_strength"] = boost_strength.expand_as(soft_roi_mask)
        aux_tensor["adaptive_control_soft_roi_target_p90"] = torch.full_like(soft_roi_mask, self.adaptive_target_p90)
        aux_tensor["adaptive_control_soft_roi_trigger_p90"] = torch.full_like(soft_roi_mask, self.adaptive_trigger_p90)
        return aux_tensor
