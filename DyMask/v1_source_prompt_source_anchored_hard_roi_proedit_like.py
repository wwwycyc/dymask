from __future__ import annotations

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
        self._current_roi_mask = None
        self._current_method_name = "full_dynamic_mask"

    def _infer_edit_mode(self, sample: MaterializedSample) -> str:
        prompt = (sample.edit_prompt or "").lower()
        if any(token in prompt for token in ("remove", "erase", "delete", "without")):
            return "remove"
        if any(token in prompt for token in ("add ", " insert", "append", "put ", "with ")) and not any(
            token in prompt for token in ("change", "replace")
        ):
            return "add"
        if any(token in prompt for token in ("style", "effect", "pixel art", "digital art", "cartoon", "painting")):
            return "style"
        return "change"

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_hard_roi_proedit_like_v2",
                "mechanism_detail": (
                    "ProEdit-inspired localized editing with ROI-aware self-attention KV mixing and "
                    "localized latent refresh, layered on top of hard ROI source anchoring"
                ),
                "proedit_like_kv_mix": {
                    "start_ratio": self.feature_mix_config.start_ratio,
                    "end_ratio": self.feature_mix_config.end_ratio,
                    "inside_target_relax_strength": self.feature_mix_config.inside_target_relax_strength,
                    "outside_source_strength": self.feature_mix_config.outside_source_strength,
                    "up_block_indices": list(self.feature_mix_config.up_block_indices),
                    "resnet_indices": list(self.feature_mix_config.resnet_indices),
                    "formula": "K,V <- (1-alpha) * target + alpha * source, with alpha weaker inside ROI than outside ROI",
                },
                "proedit_like_latent_shift": {
                    "strength": self.latent_shift_config.strength,
                    "formula": "z_T <- (1-lambda*roi) * z_T + (lambda*roi) * matched_noise(z_T)",
                },
            }
        )
        return payload

    def _run_method_batch(self, samples, method_name, inversions, target_conditions):
        register_attention_control = self.ntip2p.ptp_utils.register_attention_control
        self.feature_mixer.set_batch_edit_modes(self._infer_edit_mode(sample) for sample in samples)
        self.feature_mixer.set_attention_controller(self.attention_store)
        self.feature_mixer.register(self.pipe.unet)
        self.ntip2p.ptp_utils.register_attention_control = lambda model, controller: None
        try:
            return super()._run_method_batch(samples, method_name, inversions, target_conditions)
        finally:
            self.ntip2p.ptp_utils.register_attention_control = register_attention_control
            self.feature_mixer.set_attention_controller(None)
            self.feature_mixer.register(self.pipe.unet)

    def _initialize_edit_latents(
        self,
        method_name: str,
        latents,
        roi_mask,
        source_latents,
        total_steps: int,
    ):
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
