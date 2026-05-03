from __future__ import annotations

import torch

from DyMaskRefactor.schemas import MaterializedSample
from DyMaskRefactor.v1_source_prompt_temporal_support import V1SourcePromptTemporalSupportEditor

from DyMaskRefactor.support_line.masking import SupportMaskingMixin
from DyMaskRefactor.support_line.roi import SupportRoiMixin
from DyMaskRefactor.support_line.schedules import validate_unit_interval


class RefactorSupportBaselineEditor(SupportMaskingMixin, SupportRoiMixin, V1SourcePromptTemporalSupportEditor):
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
        self.soft_roi_start_weight = validate_unit_interval(soft_roi_start_weight, "soft_roi_start_weight")
        self.soft_roi_end_weight = validate_unit_interval(soft_roi_end_weight, "soft_roi_end_weight")
        self.anchor_hardness_start = validate_unit_interval(anchor_hardness_start, "anchor_hardness_start")
        self.anchor_hardness_end = validate_unit_interval(anchor_hardness_end, "anchor_hardness_end")
        if self.soft_roi_end_weight > self.soft_roi_start_weight:
            raise ValueError("soft_roi_end_weight must be <= soft_roi_start_weight")
        if self.anchor_hardness_end < self.anchor_hardness_start:
            raise ValueError("anchor_hardness_end must be >= anchor_hardness_start")
        self._current_soft_roi_mask: torch.Tensor | None = None

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_support_adaptive_v1",
                "roi_mask_policy": "temporal support blended with soft DiffEdit ROI using a front-loose, back-tight schedule",
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
