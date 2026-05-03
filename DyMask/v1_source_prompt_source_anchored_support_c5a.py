from __future__ import annotations

import torch

from .schemas import MaterializedSample
from .v1_source_prompt_source_anchored_support_c5 import V1SourcePromptSourceAnchoredSupportC5Editor


class V1SourcePromptSourceAnchoredSupportC5AEditor(V1SourcePromptSourceAnchoredSupportC5Editor):
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
        support_boundary_soft_scale: float = 0.35,
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
        self.support_boundary_soft_scale = self._validate_unit_interval(
            support_boundary_soft_scale,
            'support_boundary_soft_scale',
        )

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                'variant': 'source_prompt_source_anchored_support_c5a_boundary_soft_write_v1',
                'roi_mask_policy': (
                    'C5 confidence-gated local anchor relaxation plus boundary-only soft support writes; '
                    'support memory can grow slightly into the soft roi fringe without weakening hard-roi interior'
                ),
                'support_memory_policy': {
                    'support_boundary_soft_scale': self.support_boundary_soft_scale,
                    'formula': 'phi_t = dynamic_mask * (roi_hard + beta * roi_soft * (1 - roi_hard))',
                },
            }
        )
        return payload

    def _support_write_roi(self, roi_mask: torch.Tensor | None) -> torch.Tensor | None:
        if roi_mask is None:
            return None
        soft_roi_mask = self._resolve_soft_roi_mask(roi_mask)
        if soft_roi_mask is None:
            return roi_mask
        boundary_tail = (1.0 - roi_mask).clamp(0.0, 1.0)
        soft_boundary = (self.support_boundary_soft_scale * soft_roi_mask * boundary_tail).clamp(0.0, 1.0)
        return (roi_mask + soft_boundary).clamp(0.0, 1.0)

    def _compose_effective_mask_from_aux(
        self,
        method_name: str,
        dynamic_mask: torch.Tensor,
        aux_tensor: dict[str, torch.Tensor],
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor:
        if roi_mask is None or method_name == 'target_only' or not self._uses_diffedit_roi_cap(method_name):
            return super()._compose_effective_mask_from_aux(
                method_name,
                dynamic_mask,
                aux_tensor,
                roi_mask,
                step_idx,
                total_steps,
            )
        support_write_roi = self._support_write_roi(roi_mask)
        support_evidence = dynamic_mask if support_write_roi is None else (support_write_roi * dynamic_mask).clamp(0.0, 1.0)
        self._cache_anchor_context(
            aux_tensor,
            dynamic_mask=dynamic_mask,
            roi_mask=roi_mask,
        )
        return support_evidence

    def _finalize_step_aux_tensor(
        self,
        method_name: str,
        aux_tensor: dict[str, torch.Tensor],
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> dict[str, torch.Tensor]:
        aux_tensor = super()._finalize_step_aux_tensor(method_name, aux_tensor, roi_mask, step_idx, total_steps)
        if roi_mask is None or method_name == 'target_only' or not self._uses_diffedit_roi_cap(method_name):
            return aux_tensor
        support_write_roi = self._support_write_roi(roi_mask)
        if support_write_roi is None:
            return aux_tensor
        aux_tensor['support_write_roi'] = support_write_roi
        aux_tensor['support_write_soft_tail'] = (support_write_roi - roi_mask).clamp(0.0, 1.0)
        aux_tensor['support_boundary_soft_scale'] = torch.full_like(roi_mask, self.support_boundary_soft_scale)
        return aux_tensor
