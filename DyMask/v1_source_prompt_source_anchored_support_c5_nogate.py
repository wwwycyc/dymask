from __future__ import annotations

import torch

from .schemas import MaterializedSample
from .v1_source_prompt_source_anchored_support_c5 import V1SourcePromptSourceAnchoredSupportC5Editor


class V1SourcePromptSourceAnchoredSupportC5NoGateEditor(V1SourcePromptSourceAnchoredSupportC5Editor):
    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_support_c5_nogate_local_anchor_v1",
                "roi_mask_policy": (
                    "baseline adaptive temporal support plus local anchor relaxation without confidence gating; "
                    "soft roi alone controls where anchor relaxation can happen"
                ),
                "background_anchor_policy": (
                    "after each scheduler step, use baseline adaptive anchor mask and relax it uniformly inside soft roi only"
                ),
                "background_anchor_relaxation": {
                    "start_strength": self.anchor_relax_start_strength,
                    "end_strength": self.anchor_relax_end_strength,
                    "formula": "R_t = alpha_t * roi_soft; A'_t = lerp(A_t, 1, R_t)",
                },
                "ablation": "remove confidence gating while keeping local soft-roi anchor relaxation",
            }
        )
        return payload

    def _confidence_anchor_components(
        self,
        aux_tensor: dict[str, torch.Tensor] | None,
        roi_mask: torch.Tensor | None,
    ) -> dict[str, torch.Tensor] | None:
        if roi_mask is None:
            return None
        soft_roi_mask = self._resolve_soft_roi_mask(roi_mask)
        if soft_roi_mask is None:
            return None
        soft_roi_mask = soft_roi_mask.clamp(0.0, 1.0)
        ones = torch.ones_like(soft_roi_mask)
        return {
            "soft_roi_mask": soft_roi_mask,
            "evidence": ones,
            "consistency": ones,
            "confidence": soft_roi_mask,
        }
