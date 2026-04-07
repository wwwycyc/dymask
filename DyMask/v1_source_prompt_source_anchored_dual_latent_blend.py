from __future__ import annotations

from .schemas import MaterializedSample
from .v1_source_prompt_temporal_support import V1SourcePromptTemporalSupportEditor

import torch


class V1SourcePromptSourceAnchoredDualLatentBlendEditor(V1SourcePromptTemporalSupportEditor):
    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_dual_latent_blend_v1",
                "roi_mask_policy": "hard roi times dynamic evidence with temporal support and dual-branch latent recomposition",
                "inside_blend_formula": "z_{t-1}^{in} = m_t * z_{t-1}^{tar} + (roi-m_t) * z_{t-1}^{src-pred}",
                "outside_anchor_formula": "z_{t-1}^{out} = (1-roi) * z_{t-1}^{src}",
                "step_update": "z_{t-1} = z_{t-1}^{in} + z_{t-1}^{out}",
            }
        )
        return payload

    def _step_latents_from_mask(
        self,
        method_name: str,
        latents: torch.Tensor,
        timestep: torch.Tensor,
        eps_src: torch.Tensor,
        eps_tar: torch.Tensor,
        effective_mask: torch.Tensor,
        roi_mask: torch.Tensor | None,
        source_latents: list[torch.Tensor],
        step_idx: int,
        total_steps: int,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        eps = eps_src + effective_mask * (eps_tar - eps_src)
        if roi_mask is None or method_name == "target_only" or not self._uses_diffedit_roi_cap(method_name):
            prev_latents = self.pipe.scheduler.step(eps, timestep, latents).prev_sample
            return eps, prev_latents

        prev_src = self.pipe.scheduler.step(eps_src, timestep, latents).prev_sample
        prev_tar = self.pipe.scheduler.step(eps_tar, timestep, latents).prev_sample
        next_source_idx = min(step_idx + 1, len(source_latents) - 1)
        source_anchor = source_latents[next_source_idx]
        if source_anchor.shape != prev_src.shape:
            raise ValueError(
                f"source anchor shape mismatch: expected {tuple(prev_src.shape)}, got {tuple(source_anchor.shape)}"
            )

        inside_src_weight = torch.clamp(roi_mask - effective_mask, 0.0, 1.0)
        prev_latents = (
            effective_mask * prev_tar
            + inside_src_weight * prev_src
            + (1.0 - roi_mask) * source_anchor
        )
        return eps, prev_latents
