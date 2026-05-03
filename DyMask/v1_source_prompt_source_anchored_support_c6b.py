from __future__ import annotations

import torch

from .schemas import MaterializedSample
from .v1_source_prompt_source_anchored_support_c6 import V1SourcePromptSourceAnchoredSupportC6Editor


class V1SourcePromptSourceAnchoredSupportC6BEditor(V1SourcePromptSourceAnchoredSupportC6Editor):
    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_support_c6b_confidence_roi_agreement_v1",
                "background_anchor_policy": (
                    "same as C6, but the late roi-trust fallback is tightened to regions where support state "
                    "and effective mask both agree, to avoid broad-roi over-relaxation"
                ),
                "background_anchor_relaxation": {
                    **payload.get("background_anchor_relaxation", {}),
                    "roi_trust_formula": "roi_trust_base = support_state * mask; roi_trust = sqrt(roi_trust_base)",
                },
            }
        )
        return payload

    def _roi_trust_base(
        self,
        support_state: torch.Tensor | None,
        effective_mask: torch.Tensor,
        dynamic_mask: torch.Tensor | None,
    ) -> torch.Tensor:
        _ = dynamic_mask
        if support_state is None:
            return effective_mask
        return (support_state * effective_mask).clamp(0.0, 1.0)
