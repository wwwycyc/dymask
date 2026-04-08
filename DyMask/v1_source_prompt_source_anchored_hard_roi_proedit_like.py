from __future__ import annotations

import torch

from .proedit_like_feature_mix import (
    ProEditLikeFeatureMixConfig,
    ProEditLikeFeatureMixController,
)
from .proedit_like_latent_shift import (
    ProEditLikeLatentShiftConfig,
    apply_proedit_like_latent_shift,
)
from .schemas import MaterializedSample
from .v1_source_prompt_source_anchored_hard_roi import V1SourcePromptSourceAnchoredHardRoiEditor


class V1SourcePromptSourceAnchoredHardRoiProEditLikeEditor(
    V1SourcePromptSourceAnchoredHardRoiEditor
):
    def __init__(
        self,
        pipe,
        config,
        feature_mix_config: ProEditLikeFeatureMixConfig,
        latent_shift_config: ProEditLikeLatentShiftConfig,
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
        self.latent_shift_config = latent_shift_config
        self.feature_mixer = ProEditLikeFeatureMixController(config=feature_mix_config)
        self.feature_mixer.register(self.pipe.unet)
        self._current_roi_mask: torch.Tensor | None = None
        self._current_method_name: str = "full_dynamic_mask"

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_hard_roi_proedit_like_v1",
                "mechanism_detail": (
                    "ProEdit-inspired localized editing with ROI-only latent refresh and "
                    "ROI-conditioned decoder feature routing that relaxes source hold inside ROI "
                    "while preserving source features outside ROI"
                ),
                "proedit_like_feature_mix": {
                    "start_ratio": self.feature_mix_config.start_ratio,
                    "end_ratio": self.feature_mix_config.end_ratio,
                    "inside_target_relax_strength": self.feature_mix_config.inside_target_relax_strength,
                    "outside_source_strength": self.feature_mix_config.outside_source_strength,
                    "up_block_indices": list(self.feature_mix_config.up_block_indices),
                    "resnet_indices": list(self.feature_mix_config.resnet_indices),
                },
                "proedit_like_latent_shift": {
                    "strength": self.latent_shift_config.strength,
                    "formula": "z_T = (1-lambda*roi) * z_T^src + (lambda*roi) * noise",
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
        if roi_mask is None or method_name == "target_only" or not self._uses_diffedit_roi_cap(method_name):
            return latents
        return apply_proedit_like_latent_shift(
            latents=latents,
            roi_mask=roi_mask,
            config=self.latent_shift_config,
        )

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
