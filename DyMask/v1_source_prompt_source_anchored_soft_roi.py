from __future__ import annotations

import numpy as np
import torch

from .schemas import MaterializedSample
from .v1_source_prompt_source_anchored_hard_roi import V1SourcePromptSourceAnchoredHardRoiEditor


class V1SourcePromptSourceAnchoredSoftRoiEditor(V1SourcePromptSourceAnchoredHardRoiEditor):
    def __init__(
        self,
        pipe,
        config,
        diffedit_config=None,
        inversion_backend=None,
    ) -> None:
        super().__init__(
            pipe,
            config,
            diffedit_config=diffedit_config,
            inversion_backend=inversion_backend,
        )
        self._current_soft_roi_mask: torch.Tensor | None = None

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_soft_roi_v1",
                "roi_mask_policy": "soft DiffEdit ROI for update with hard outside-roi source anchoring",
                "support_update": "M_t = roi_mask_soft",
                "background_anchor_formula": "z_{t-1} = roi_mask_hard * z_{t-1}^{edit} + (1-roi_mask_hard) * z_{t-1}^{src}",
            }
        )
        return payload

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

    def _compose_effective_mask(
        self,
        method_name: str,
        dynamic_mask,
        roi_mask,
        step_idx: int,
        total_steps: int,
    ):
        if not self._uses_diffedit_roi_cap(method_name) or roi_mask is None:
            return dynamic_mask
        if self._current_soft_roi_mask is None:
            return roi_mask
        if self._current_soft_roi_mask.shape != roi_mask.shape:
            raise ValueError(
                f"soft roi mask shape mismatch: expected {tuple(roi_mask.shape)}, got {tuple(self._current_soft_roi_mask.shape)}"
            )
        return self._current_soft_roi_mask
