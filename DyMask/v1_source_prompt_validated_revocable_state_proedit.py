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
from .v1_source_prompt_validated_revocable_state import V1SourcePromptValidatedRevocableStateEditor


class V1SourcePromptValidatedRevocableStateProEditEditor(
    V1SourcePromptValidatedRevocableStateEditor
):
    def __init__(
        self,
        pipe,
        config,
        feature_mix_config: ProEditLikeFeatureMixConfig,
        latent_shift_config: ProEditLikeLatentShiftConfig,
        support_rho: float = 0.85,
        support_decay_mu: float = 0.80,
        support_decay_lambda: float = 0.10,
        support_lambda: float = 0.50,
        support_kappa: float = 8.0,
        support_alpha: float = 8.0,
        support_delta: float = 0.35,
        inversion_backend=None,
    ) -> None:
        super().__init__(
            pipe,
            config,
            support_rho=support_rho,
            support_decay_mu=support_decay_mu,
            support_decay_lambda=support_decay_lambda,
            support_lambda=support_lambda,
            support_kappa=support_kappa,
            support_alpha=support_alpha,
            support_delta=support_delta,
            inversion_backend=inversion_backend,
        )
        self.feature_mix_config = feature_mix_config
        self.latent_shift_config = latent_shift_config
        self.feature_mixer = ProEditLikeFeatureMixController(config=feature_mix_config)
        self.feature_mixer.register(self.pipe.unet)
        self._current_roi_mask = None
        self._current_method_name = "full_dynamic_mask"

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_validated_revocable_state_proedit_v1",
                "mechanism_detail": (
                    "source-prompt editing with validated revocable support state, ProEdit-style self-attention KV mix, "
                    "and localized latent shift"
                ),
                "proedit_like_kv_mix": {
                    "start_ratio": self.feature_mix_config.start_ratio,
                    "end_ratio": self.feature_mix_config.end_ratio,
                    "inside_target_relax_strength": self.feature_mix_config.inside_target_relax_strength,
                    "outside_source_strength": self.feature_mix_config.outside_source_strength,
                    "up_block_indices": list(self.feature_mix_config.up_block_indices),
                    "resnet_indices": list(self.feature_mix_config.resnet_indices),
                },
                "proedit_like_latent_shift": {
                    "strength": self.latent_shift_config.strength,
                },
            }
        )
        return payload

    def _probe_method_batch_memory(
        self,
        samples,
        inversions,
        target_conditions,
        method_name,
    ) -> None:
        original_register = self.ntip2p.ptp_utils.register_attention_control
        self.feature_mixer.set_attention_controller(self.attention_store)
        self.feature_mixer.register(self.pipe.unet)
        self.ntip2p.ptp_utils.register_attention_control = lambda model, controller: None
        try:
            return super()._probe_method_batch_memory(samples, inversions, target_conditions, method_name)
        finally:
            self.ntip2p.ptp_utils.register_attention_control = original_register
            self.feature_mixer.set_attention_controller(None)
            self.feature_mixer.register(self.pipe.unet)

    def _run_method_batch(
        self,
        samples,
        method_name,
        inversions,
        target_conditions,
    ):
        original_register = self.ntip2p.ptp_utils.register_attention_control
        self.feature_mixer.set_attention_controller(self.attention_store)
        self.feature_mixer.register(self.pipe.unet)
        self.ntip2p.ptp_utils.register_attention_control = lambda model, controller: None
        try:
            return super()._run_method_batch(samples, method_name, inversions, target_conditions)
        finally:
            self.ntip2p.ptp_utils.register_attention_control = original_register
            self.feature_mixer.set_attention_controller(None)
            self.feature_mixer.register(self.pipe.unet)

    def _initialize_support_states(self, evidence):
        self._current_roi_mask = evidence
        return super()._initialize_support_states(evidence)

    def _update_support_states(self, previous_state, previous_low_evidence_state, evidence):
        self._current_roi_mask = evidence
        return super()._update_support_states(previous_state, previous_low_evidence_state, evidence)

    def _effective_mask_from_state(self, support_state):
        effective_mask = super()._effective_mask_from_state(support_state)
        self._current_roi_mask = effective_mask
        return effective_mask

    def _prepare_source_attention_pass(self, step_idx: int, total_steps: int) -> None:
        self.attention_store.reset()
        self.feature_mixer.begin_source_pass(step_idx=step_idx, total_steps=total_steps)

    def _prepare_target_attention_pass(self, step_idx: int, total_steps: int) -> None:
        self.attention_store.reset()
        self.feature_mixer.begin_target_pass(
            step_idx=step_idx,
            total_steps=total_steps,
            roi_mask=self._current_roi_mask,
            enabled=(self._current_roi_mask is not None and self._uses_support_state(self._current_method_name)),
        )

    @staticmethod
    def _uses_support_state(method_name: str) -> bool:
        if method_name == "target_only":
            return False
        return not str(method_name).startswith("global_blend")

    def _finalize_method_result(self, sample, method_name, edited_image, aux_history, trace_rows, inversion):
        result = super()._finalize_method_result(sample, method_name, edited_image, aux_history, trace_rows, inversion)
        return result

    def close(self) -> None:
        self.feature_mixer.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass
