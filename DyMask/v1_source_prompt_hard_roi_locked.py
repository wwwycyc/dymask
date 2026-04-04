from __future__ import annotations

from .schemas import MaterializedSample
from .v1_source_prompt_diffedit_roi import V1SourcePromptDiffEditRoiEditor


class V1SourcePromptHardRoiLockedEditor(V1SourcePromptDiffEditRoiEditor):
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
            stage_split_ratio=0.0,
            diffedit_config=diffedit_config,
            inversion_backend=inversion_backend,
        )

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_hard_roi_locked_v1",
                "roi_mask_policy": "always hard roi times dynamic mask",
            }
        )
        payload.pop("stage_split_ratio", None)
        return payload

    def _stage_split_step(self, total_steps: int) -> int:
        return 0

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
        return roi_mask * dynamic_mask
