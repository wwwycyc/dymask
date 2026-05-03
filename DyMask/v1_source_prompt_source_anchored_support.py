from __future__ import annotations

import math

import numpy as np
import torch

from .schemas import MaterializedSample
from .v1_source_prompt_temporal_support import V1SourcePromptTemporalSupportEditor


class V1SourcePromptSourceAnchoredSupportEditor(V1SourcePromptTemporalSupportEditor):
    def __init__(
        self,
        pipe,
        config,
        support_rho: float = 0.85,
        soft_roi_start_weight: float = 0.75,
        soft_roi_end_weight: float = 0.10,
        anchor_hardness_start: float = 0.35,
        anchor_hardness_end: float = 1.0,
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
        self.soft_roi_start_weight = self._validate_unit_interval(soft_roi_start_weight, "soft_roi_start_weight")
        self.soft_roi_end_weight = self._validate_unit_interval(soft_roi_end_weight, "soft_roi_end_weight")
        self.anchor_hardness_start = self._validate_unit_interval(anchor_hardness_start, "anchor_hardness_start")
        self.anchor_hardness_end = self._validate_unit_interval(anchor_hardness_end, "anchor_hardness_end")
        if self.soft_roi_end_weight > self.soft_roi_start_weight:
            raise ValueError("soft_roi_end_weight must be <= soft_roi_start_weight")
        if self.anchor_hardness_end < self.anchor_hardness_start:
            raise ValueError("anchor_hardness_end must be >= anchor_hardness_start")
        self._current_soft_roi_mask: torch.Tensor | None = None

    @staticmethod
    def _validate_unit_interval(value: float, name: str) -> float:
        scalar = float(value)
        if not 0.0 <= scalar <= 1.0:
            raise ValueError(f"{name} must be in [0, 1], got {scalar}")
        return scalar

    @staticmethod
    def _schedule_progress(step_idx: int, total_steps: int) -> float:
        if total_steps <= 1:
            return 1.0
        return max(0.0, min(float(step_idx) / float(total_steps - 1), 1.0))

    @staticmethod
    def _cosine_schedule(start: float, end: float, progress: float) -> float:
        eased = 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(progress, 1.0)))
        return start + (end - start) * eased

    def _soft_roi_weight(self, step_idx: int, total_steps: int) -> float:
        return self._cosine_schedule(
            self.soft_roi_start_weight,
            self.soft_roi_end_weight,
            self._schedule_progress(step_idx, total_steps),
        )

    def _anchor_hardness(self, step_idx: int, total_steps: int) -> float:
        return self._cosine_schedule(
            self.anchor_hardness_start,
            self.anchor_hardness_end,
            self._schedule_progress(step_idx, total_steps),
        )

    def _resolve_soft_roi_mask(self, roi_mask: torch.Tensor | None) -> torch.Tensor | None:
        if roi_mask is None or self._current_soft_roi_mask is None:
            return roi_mask
        if self._current_soft_roi_mask.shape != roi_mask.shape:
            raise ValueError(
                f"soft roi mask shape mismatch: expected {tuple(roi_mask.shape)}, got {tuple(self._current_soft_roi_mask.shape)}"
            )
        return self._current_soft_roi_mask

    def _adaptive_anchor_mask(
        self,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor | None:
        if roi_mask is None:
            return None
        soft_roi_mask = self._resolve_soft_roi_mask(roi_mask)
        if soft_roi_mask is None:
            return roi_mask
        hardness = self._anchor_hardness(step_idx, total_steps)
        return torch.lerp(soft_roi_mask, roi_mask, hardness).clamp(0.0, 1.0)

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_support_adaptive_v1",
                "roi_mask_policy": "temporal support blended with soft DiffEdit ROI using a front-loose, back-tight schedule",
                "soft_roi_source": "pre-binarization DiffEdit semantic guidance map",
                "hard_roi_source": "soft roi thresholded at 0.5",
                "soft_roi_schedule": {
                    "start_weight": self.soft_roi_start_weight,
                    "end_weight": self.soft_roi_end_weight,
                    "formula": "M_t = (1-w_t) * S_t + w_t * roi_soft, w_t follows cosine decay",
                },
                "background_anchor_policy": "after each scheduler step, outside-roi latent is source-anchored with a soft-to-hard ROI schedule",
                "background_anchor_schedule": {
                    "start_hardness": self.anchor_hardness_start,
                    "end_hardness": self.anchor_hardness_end,
                    "formula": "A_t = lerp(roi_soft, roi_hard, h_t), h_t follows cosine growth",
                },
                "background_anchor_formula": "z_{t-1} = A_t * z_{t-1}^{edit} + (1-A_t) * z_{t-1}^{src}",
            }
        )
        return payload

    @torch.no_grad()
    def _generate_diffedit_roi_batch(self, samples: list[MaterializedSample]) -> torch.Tensor:
        soft_masks = self._generate_diffedit_soft_mask_batch(samples)
        self._current_soft_roi_mask = (
            torch.from_numpy(soft_masks).unsqueeze(1).to(self.pipe.device, dtype=self.pipe.unet.dtype)
        )
        hard_masks = (soft_masks > 0.5).astype(np.float32)
        return torch.from_numpy(hard_masks).unsqueeze(1).to(self.pipe.device, dtype=self.pipe.unet.dtype)

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
        soft_roi_mask = self._resolve_soft_roi_mask(roi_mask)
        if soft_roi_mask is None:
            return support_state
        soft_roi_weight = self._soft_roi_weight(step_idx, total_steps)
        return torch.lerp(support_state, soft_roi_mask, soft_roi_weight).clamp(0.0, 1.0)

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

        anchor_mask = self._adaptive_anchor_mask(roi_mask, step_idx, total_steps)
        if anchor_mask is None:
            return prev_latents
        next_source_idx = min(step_idx + 1, len(source_latents) - 1)
        source_anchor = source_latents[next_source_idx]
        if source_anchor.shape != prev_latents.shape:
            raise ValueError(
                f"source anchor shape mismatch: expected {tuple(prev_latents.shape)}, got {tuple(source_anchor.shape)}"
            )
        return anchor_mask * prev_latents + (1.0 - anchor_mask) * source_anchor

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
        anchor_mask = self._adaptive_anchor_mask(roi_mask, step_idx, total_steps)
        if soft_roi_mask is None or anchor_mask is None:
            return aux_tensor
        aux_tensor["soft_roi_mask"] = soft_roi_mask
        aux_tensor["adaptive_anchor_mask"] = anchor_mask
        aux_tensor["soft_roi_blend"] = torch.full_like(roi_mask, self._soft_roi_weight(step_idx, total_steps))
        aux_tensor["anchor_hardness"] = torch.full_like(roi_mask, self._anchor_hardness(step_idx, total_steps))
        return aux_tensor
