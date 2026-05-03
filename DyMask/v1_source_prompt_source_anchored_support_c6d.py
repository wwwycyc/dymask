from __future__ import annotations

import torch

from .schemas import MaterializedSample
from .v1_source_prompt_source_anchored_support_c6c import V1SourcePromptSourceAnchoredSupportC6CEditor


class V1SourcePromptSourceAnchoredSupportC6DEditor(V1SourcePromptSourceAnchoredSupportC6CEditor):
    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_support_c6d_dynamic_gap_recovery_v1",
                "background_anchor_policy": (
                    "same as C6c, but the late support-gap recovery branch is further gated by the live "
                    "dynamic mask, so stale support memory cannot reopen regions where current edit evidence "
                    "has already disappeared"
                ),
                "background_anchor_relaxation": {
                    **payload.get("background_anchor_relaxation", {}),
                    "roi_trust_formula": (
                        "roi_trust_base = relu(support_state - mask) * dynamic_mask; "
                        "roi_trust = sqrt(roi_trust_base)"
                    ),
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
        if support_state is None or dynamic_mask is None:
            return torch.zeros_like(effective_mask)
        support_gap = (support_state - effective_mask).clamp(0.0, 1.0)
        return (support_gap * dynamic_mask).clamp(0.0, 1.0)
