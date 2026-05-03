from __future__ import annotations

import numpy as np
import torch

from DyMaskRefactor.schemas import MaterializedSample

from DyMaskRefactor.support_line.schedules import cosine_schedule, schedule_progress


class SupportRoiMixin:
    def _soft_roi_weight(self, step_idx: int, total_steps: int) -> float:
        return cosine_schedule(
            self.soft_roi_start_weight,
            self.soft_roi_end_weight,
            schedule_progress(step_idx, total_steps),
        )

    def _anchor_hardness(self, step_idx: int, total_steps: int) -> float:
        return cosine_schedule(
            self.anchor_hardness_start,
            self.anchor_hardness_end,
            schedule_progress(step_idx, total_steps),
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

    @torch.no_grad()
    def _generate_diffedit_roi_batch(self, samples: list[MaterializedSample]) -> torch.Tensor:
        self._restore_default_attention_processors()
        source_pils = [self._load_sample_pil(sample.source_image_path) for sample in samples]
        mask_output = self.diffedit_pipe.generate_mask(
            image=source_pils,
            source_prompt=[sample.source_prompt for sample in samples],
            target_prompt=[sample.target_prompt for sample in samples],
            num_maps_per_mask=self.diffedit_config.num_maps_per_mask,
            mask_encode_strength=self.diffedit_config.mask_encode_strength,
            mask_thresholding_ratio=self.diffedit_config.mask_thresholding_ratio,
            num_inference_steps=self.config.runtime.num_edit_steps,
            guidance_scale=self.config.runtime.guidance_scale,
            output_type="np",
        )
        mask_batch = self._normalize_mask_batch(mask_output)
        soft_masks = np.stack([np.clip(np.asarray(mask, dtype=np.float32), 0.0, 1.0) for mask in mask_batch], axis=0)
        self._current_soft_roi_mask = (
            torch.from_numpy(soft_masks).unsqueeze(1).to(self.pipe.device, dtype=self.pipe.unet.dtype)
        )
        hard_masks = self._harden_roi_masks(mask_batch)
        return torch.from_numpy(hard_masks).unsqueeze(1).to(self.pipe.device, dtype=self.pipe.unet.dtype)
