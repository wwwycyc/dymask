from __future__ import annotations

from .schemas import MaterializedSample
from .source_attention_injection import (
    SourceSelfAttentionInjectionConfig,
    SourceSelfAttentionInjectionStore,
)
from .v1_source_prompt_source_anchored_hard_roi import V1SourcePromptSourceAnchoredHardRoiEditor


class V1SourcePromptSourceAnchoredHardRoiSelfAttentionInjectionEditor(
    V1SourcePromptSourceAnchoredHardRoiEditor
):
    def __init__(
        self,
        pipe,
        config,
        injection_config: SourceSelfAttentionInjectionConfig,
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
        self.attention_store = SourceSelfAttentionInjectionStore(
            config=injection_config,
            low_resource=False,
        )
        self.ntip2p.ptp_utils.register_attention_control(self.pipe, self.attention_store)

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_hard_roi_self_attention_injection_v1",
                "self_attention_injection": {
                    "start_ratio": self.injection_config.start_ratio,
                    "end_ratio": self.injection_config.end_ratio,
                    "strength": self.injection_config.strength,
                    "locations": list(self.injection_config.locations),
                },
                "mechanism_detail": "cache source self-attention on source pass and inject it into target self-attention on selected decoder steps",
            }
        )
        return payload

    def _prepare_source_attention_pass(self, step_idx: int, total_steps: int) -> None:
        self.attention_store.begin_source_pass(step_idx=step_idx, total_steps=total_steps)

    def _prepare_target_attention_pass(self, step_idx: int, total_steps: int) -> None:
        self.attention_store.begin_target_pass(step_idx=step_idx, total_steps=total_steps)
