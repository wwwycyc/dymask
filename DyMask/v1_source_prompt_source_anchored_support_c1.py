from __future__ import annotations

import torch

from .schemas import MaterializedSample
from .v1_source_prompt_source_anchored_support import V1SourcePromptSourceAnchoredSupportEditor


class V1SourcePromptSourceAnchoredSupportC1Editor(V1SourcePromptSourceAnchoredSupportEditor):
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
        self.support_soft_roi_blend = self._validate_unit_interval(
            support_soft_roi_blend,
            "support_soft_roi_blend",
        )

    def _support_memory_roi(self, roi_mask: torch.Tensor | None) -> torch.Tensor | None:
        if roi_mask is None:
            return None
        soft_roi_mask = self._resolve_soft_roi_mask(roi_mask)
        if soft_roi_mask is None:
            return roi_mask
        return torch.lerp(roi_mask, soft_roi_mask, self.support_soft_roi_blend).clamp(0.0, 1.0)

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_support_c1_soft_memory_v1",
                "roi_mask_policy": "adaptive support with soft-aware support memory and unchanged adaptive anchoring",
                "support_memory_policy": {
                    "soft_roi_blend": self.support_soft_roi_blend,
                    "formula": "phi_t = dynamic_mask * lerp(roi_hard, roi_soft, beta)",
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
        support_memory_roi = self._support_memory_roi(roi_mask)
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
        support_memory_roi = self._support_memory_roi(roi_mask)
        if support_memory_roi is None:
            return aux_tensor
        aux_tensor["support_memory_roi"] = support_memory_roi
        aux_tensor["support_memory_soft_blend"] = torch.full_like(roi_mask, self.support_soft_roi_blend)
        return aux_tensor
