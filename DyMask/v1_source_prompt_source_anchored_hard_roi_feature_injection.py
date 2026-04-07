from __future__ import annotations

from .schemas import MaterializedSample
from .source_feature_injection import (
    SourceDecoderFeatureInjectionConfig,
    SourceDecoderFeatureInjectionController,
)
from .v1_source_prompt_source_anchored_hard_roi import V1SourcePromptSourceAnchoredHardRoiEditor


class V1SourcePromptSourceAnchoredHardRoiFeatureInjectionEditor(
    V1SourcePromptSourceAnchoredHardRoiEditor
):
    def __init__(
        self,
        pipe,
        config,
        injection_config: SourceDecoderFeatureInjectionConfig,
        diffedit_config=None,
        inversion_backend=None,
    ) -> None:
        super().__init__(
            pipe,
            config,
            diffedit_config=diffedit_config,
            inversion_backend=inversion_backend,
        )
        self.injection_config = injection_config
        self.feature_injector = SourceDecoderFeatureInjectionController(config=injection_config)
        self.feature_injector.register(self.pipe.unet)

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_hard_roi_feature_injection_v1",
                "decoder_feature_injection": {
                    "start_ratio": self.injection_config.start_ratio,
                    "end_ratio": self.injection_config.end_ratio,
                    "strength": self.injection_config.strength,
                    "up_block_indices": list(self.injection_config.up_block_indices),
                    "resnet_indices": list(self.injection_config.resnet_indices),
                },
                "mechanism_detail": "cache source decoder features on source pass and inject them into target decoder resnet outputs on selected steps",
            }
        )
        return payload

    def _prepare_source_attention_pass(self, step_idx: int, total_steps: int) -> None:
        super()._prepare_source_attention_pass(step_idx=step_idx, total_steps=total_steps)
        self.feature_injector.begin_source_pass(step_idx=step_idx, total_steps=total_steps)

    def _prepare_target_attention_pass(self, step_idx: int, total_steps: int) -> None:
        super()._prepare_target_attention_pass(step_idx=step_idx, total_steps=total_steps)
        self.feature_injector.begin_target_pass(step_idx=step_idx, total_steps=total_steps)
