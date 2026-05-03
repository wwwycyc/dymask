from __future__ import annotations

import torch

from .conflict_gated_feature_mix import (
    ConflictGatedFeatureMixConfig,
    ConflictGatedFeatureMixController,
)
from .schemas import MaterializedSample
from .v1_source_prompt_source_anchored_hard_roi import V1SourcePromptSourceAnchoredHardRoiEditor


class V1SourcePromptSourceAnchoredHardRoiConflictGatedMixEditor(
    V1SourcePromptSourceAnchoredHardRoiEditor
):
    def __init__(
        self,
        pipe,
        config,
        feature_mix_config: ConflictGatedFeatureMixConfig,
        diffedit_config=None,
        inversion_backend=None,
    ) -> None:
        super().__init__(
            pipe,
            config,
            diffedit_config=diffedit_config,
            inversion_backend=inversion_backend,
        )
        self.feature_mix_config = feature_mix_config
        self.feature_mixer = ConflictGatedFeatureMixController(config=feature_mix_config)
        self.feature_mixer.register(self.pipe.unet)
        self._current_roi_mask: torch.Tensor | None = None
        self._current_method_name: str = "full_dynamic_mask"

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_hard_roi_conflict_gated_mix_v1",
                "mechanism_detail": (
                    "Hard ROI support with outside-roi source anchoring and decoder feature routing "
                    "that preserves source outside ROI while amplifying target rewrite inside ROI "
                    "only where source-target feature conflict is high"
                ),
                "conflict_gated_feature_mix": {
                    "start_ratio": self.feature_mix_config.start_ratio,
                    "end_ratio": self.feature_mix_config.end_ratio,
                    "inside_rewrite_gain_strength": self.feature_mix_config.inside_rewrite_gain_strength,
                    "outside_source_strength": self.feature_mix_config.outside_source_strength,
                    "up_block_indices": list(self.feature_mix_config.up_block_indices),
                    "resnet_indices": list(self.feature_mix_config.resnet_indices),
                    "inside_gain_formula": (
                        "inside_gain = lambda_in * roi * normalized_mean_abs(F_tar - F_src)"
                    ),
                },
            }
        )
        return payload

    def _initialize_edit_latents(
        self,
        method_name: str,
        latents: torch.Tensor,
        roi_mask: torch.Tensor | None,
        source_latents: list[torch.Tensor],
        total_steps: int,
    ) -> torch.Tensor:
        del source_latents, total_steps
        self._current_method_name = method_name
        self._current_roi_mask = roi_mask
        return latents

    def _prepare_source_attention_pass(self, step_idx: int, total_steps: int) -> None:
        super()._prepare_source_attention_pass(step_idx=step_idx, total_steps=total_steps)
        self.feature_mixer.begin_source_pass(step_idx=step_idx, total_steps=total_steps)

    def _prepare_target_attention_pass(self, step_idx: int, total_steps: int) -> None:
        super()._prepare_target_attention_pass(step_idx=step_idx, total_steps=total_steps)
        self.feature_mixer.begin_target_pass(
            step_idx=step_idx,
            total_steps=total_steps,
            roi_mask=self._current_roi_mask,
            enabled=(
                self._current_roi_mask is not None
                and self._current_method_name != "target_only"
                and self._uses_diffedit_roi_cap(self._current_method_name)
            ),
        )

    def close(self) -> None:
        self.feature_mixer.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass
