from __future__ import annotations

from .schemas import MaterializedSample
from .v1_source_prompt_temporal_support import V1SourcePromptTemporalSupportEditor

import torch


class V1SourcePromptSourceAnchoredSupportEditor(V1SourcePromptTemporalSupportEditor):
    def __init__(
        self,
        pipe,
        config,
        support_rho: float = 0.85,
        diffedit_config=None,
        inversion_backend=None,
    ) -> None:
        super().__init__(
            pipe,
            config,
            support_rho=support_rho,
            diffedit_config=diffedit_config,
            inversion_backend=inversion_backend,
        )

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_support_v1",
                "roi_mask_policy": "hard roi times dynamic evidence with temporal support and outside-roi source anchoring",
                "background_anchor_policy": "after each scheduler step, outside-roi latent is hard-anchored to the next source latent",
                "background_anchor_formula": "z_{t-1} = roi * z_{t-1}^{edit} + (1-roi) * z_{t-1}^{src}",
            }
        )
        return payload

    def _post_scheduler_step_latents(
        self,
        method_name: str,
        prev_latents: torch.Tensor,
        roi_mask: torch.Tensor | None,
        source_latents: list[torch.Tensor],
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor:
        if roi_mask is None or method_name == "target_only" or not self._uses_diffedit_roi_cap(method_name):
            return prev_latents
        if not source_latents:
            return prev_latents

        next_source_idx = min(step_idx + 1, len(source_latents) - 1)
        source_anchor = source_latents[next_source_idx]
        if source_anchor.shape != prev_latents.shape:
            raise ValueError(
                f"source anchor shape mismatch: expected {tuple(prev_latents.shape)}, got {tuple(source_anchor.shape)}"
            )
        return roi_mask * prev_latents + (1.0 - roi_mask) * source_anchor
