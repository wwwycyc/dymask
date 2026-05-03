from __future__ import annotations

import numpy as np
import torch

from .adapters import clear_cuda_memory
from .roi_edit_gain import RoiEditGainFieldBuilder, RoiEditGainFieldConfig
from .schemas import InversionOutput, MaterializedSample, MethodResult, TextCondition
from .source_feature_injection import (
    SourceDecoderFeatureInjectionConfig,
    SourceDecoderFeatureInjectionController,
)
from .v1 import DynamicMaskBuilder, aggregate_step_cross_attention
from .v1_source_prompt_source_anchored_hard_roi import V1SourcePromptSourceAnchoredHardRoiEditor


class V1SourcePromptSourceAnchoredHardRoiFeatureInjectionRoiGainEditor(
    V1SourcePromptSourceAnchoredHardRoiEditor
):
    def __init__(
        self,
        pipe,
        config,
        injection_config: SourceDecoderFeatureInjectionConfig,
        gain_config: RoiEditGainFieldConfig,
        enable_feature_injection: bool = True,
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
        self.gain_config = gain_config
        self.enable_feature_injection = bool(enable_feature_injection)
        self.feature_injector = None
        if self.enable_feature_injection:
            self.feature_injector = SourceDecoderFeatureInjectionController(config=injection_config)
            self.feature_injector.register(self.pipe.unet)
        self.gain_builder = RoiEditGainFieldBuilder(config=gain_config)

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_hard_roi_feature_injection_roi_gain_v2",
                "mechanism_detail": (
                    "keep hard ROI support and outside-roi source anchoring fixed, then combine optional "
                    "source-decoder feature injection with an ROI-local positive edit-gain field"
                ),
                "feature_injection_enabled": self.enable_feature_injection,
                "decoder_feature_injection": {
                    "start_ratio": self.injection_config.start_ratio,
                    "end_ratio": self.injection_config.end_ratio,
                    "strength": self.injection_config.strength,
                    "up_block_indices": list(self.injection_config.up_block_indices),
                    "resnet_indices": list(self.injection_config.resnet_indices),
                },
                "roi_edit_gain_field": self.gain_config.to_dict(),
            }
        )
        return payload

    @staticmethod
    def _masked_mean(values: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        numerator = (values * mask).flatten(1).sum(dim=1)
        denominator = mask.flatten(1).sum(dim=1).clamp(min=1e-6)
        return numerator / denominator

    def _prepare_source_attention_pass(self, step_idx: int, total_steps: int) -> None:
        super()._prepare_source_attention_pass(step_idx=step_idx, total_steps=total_steps)
        if self.feature_injector is not None:
            self.feature_injector.begin_source_pass(step_idx=step_idx, total_steps=total_steps)

    def _prepare_target_attention_pass(self, step_idx: int, total_steps: int) -> None:
        super()._prepare_target_attention_pass(step_idx=step_idx, total_steps=total_steps)
        if self.feature_injector is not None:
            self.feature_injector.begin_target_pass(step_idx=step_idx, total_steps=total_steps)

    def _build_gain_maps(
        self,
        dynamic_mask: torch.Tensor,
        aux_tensor: dict[str, torch.Tensor],
        roi_mask: torch.Tensor,
        step_idx: int,
        total_steps: int,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        discrepancy = aux_tensor["discrepancy"]
        attention = aux_tensor["attention"]
        latent_drift = aux_tensor["latent_drift"]
        gain_basis, gain_field = self.gain_builder.build(
            dynamic_mask=dynamic_mask,
            discrepancy=discrepancy,
            attention=attention,
            latent_drift=latent_drift,
            step_idx=step_idx,
            total_steps=total_steps,
        )
        edit_field = roi_mask * gain_field
        return gain_basis, gain_field, edit_field

    @torch.no_grad()
    def _probe_method_batch_memory(
        self,
        samples: list[MaterializedSample],
        inversions: list[InversionOutput],
        target_conditions: list[TextCondition],
        method_name: str,
    ) -> None:
        if method_name == "target_only" or not self._uses_diffedit_roi_cap(method_name):
            super()._probe_method_batch_memory(samples, inversions, target_conditions, method_name)
            return
        if not samples:
            return

        self._set_timesteps()
        roi_mask = self._generate_diffedit_roi_batch(samples)
        self.ntip2p.ptp_utils.register_attention_control(self.pipe, self.attention_store)
        latents = torch.cat(
            [inversion.zt_src.detach().clone().to(self.pipe.device, dtype=self.pipe.unet.dtype) for inversion in inversions],
            dim=0,
        )
        source_latent_sequences = [
            self._resample_source_latents(
                [latent.to(self.pipe.device, dtype=self.pipe.unet.dtype) for latent in inversion.src_latents],
                len(self.pipe.scheduler.timesteps),
            )
            for inversion in inversions
        ]
        source_latents = [
            torch.cat([sequence[step_idx] for sequence in source_latent_sequences], dim=0)
            for step_idx in range(len(self.pipe.scheduler.timesteps))
        ]
        builder = DynamicMaskBuilder(self.config.mask, method_name)
        builder.reset()
        focus_masks = torch.cat(
            [
                self._build_focus_token_mask(condition, self._extract_focus_terms(sample)).to(self.pipe.device)
                for sample, condition in zip(samples, target_conditions)
            ],
            dim=0,
        )
        target_embeddings = torch.cat(
            [condition.embeddings.to(self.pipe.device, dtype=self.pipe.unet.dtype) for condition in target_conditions],
            dim=0,
        )
        source_conditions = self._encode_source_conditions(samples)
        source_embeddings = torch.cat(
            [condition.embeddings.to(self.pipe.device, dtype=self.pipe.unet.dtype) for condition in source_conditions],
            dim=0,
        )
        timestep = self.pipe.scheduler.timesteps[0]
        total_steps = len(self.pipe.scheduler.timesteps)
        try:
            self._prepare_source_attention_pass(step_idx=0, total_steps=total_steps)
            eps_src = self.source_predictor.predict(latents, timestep, source_embeddings)
            self._prepare_target_attention_pass(step_idx=0, total_steps=total_steps)
            eps_tar, target_noise, _noise_uncond, _target_stats = self.target_predictor.predict(
                latents,
                timestep,
                target_embeddings,
            )
            attention_map = aggregate_step_cross_attention(
                self.attention_store,
                focus_masks,
                target_hw=(latents.shape[-2], latents.shape[-1]),
                locations=self.config.mask.attention_locations,
            )
            dynamic_mask, aux_tensor = builder.build(
                eps_src,
                target_noise,
                latents,
                source_latents[0],
                attention_map,
                step_idx=0,
                total_steps=total_steps,
            )
            _gain_basis, _gain_field, edit_field = self._build_gain_maps(
                dynamic_mask=dynamic_mask,
                aux_tensor=aux_tensor,
                roi_mask=roi_mask,
                step_idx=0,
                total_steps=total_steps,
            )
            eps = eps_src + edit_field * (eps_tar - eps_src)
            prev_latents = self.pipe.scheduler.step(eps, timestep, latents).prev_sample
            prev_latents = self._post_scheduler_step_latents(
                method_name=method_name,
                prev_latents=prev_latents,
                roi_mask=roi_mask,
                source_latents=source_latents,
                step_idx=0,
                total_steps=total_steps,
            )
            _ = self._decode_latents_batch(prev_latents)
        finally:
            self.attention_store.reset()
            clear_cuda_memory()

    @torch.no_grad()
    def _run_method_batch(
        self,
        samples: list[MaterializedSample],
        method_name: str,
        inversions: list[InversionOutput],
        target_conditions: list[TextCondition],
    ) -> list[MethodResult]:
        if method_name == "target_only" or not self._uses_diffedit_roi_cap(method_name):
            return super()._run_method_batch(samples, method_name, inversions, target_conditions)

        self._set_timesteps()
        roi_mask = self._generate_diffedit_roi_batch(samples)
        self.ntip2p.ptp_utils.register_attention_control(self.pipe, self.attention_store)

        batch_size = len(samples)
        latents = torch.cat(
            [inversion.zt_src.detach().clone().to(self.pipe.device, dtype=self.pipe.unet.dtype) for inversion in inversions],
            dim=0,
        )
        source_latent_sequences = [
            self._resample_source_latents(
                [latent.to(self.pipe.device, dtype=self.pipe.unet.dtype) for latent in inversion.src_latents],
                len(self.pipe.scheduler.timesteps),
            )
            for inversion in inversions
        ]
        source_latents = [
            torch.cat([sequence[step_idx] for sequence in source_latent_sequences], dim=0)
            for step_idx in range(len(self.pipe.scheduler.timesteps))
        ]
        builder = DynamicMaskBuilder(self.config.mask, method_name)
        builder.reset()

        focus_masks = torch.cat(
            [
                self._build_focus_token_mask(condition, self._extract_focus_terms(sample)).to(self.pipe.device)
                for sample, condition in zip(samples, target_conditions)
            ],
            dim=0,
        )
        target_embeddings = torch.cat(
            [condition.embeddings.to(self.pipe.device, dtype=self.pipe.unet.dtype) for condition in target_conditions],
            dim=0,
        )
        source_conditions = self._encode_source_conditions(samples)
        source_embeddings = torch.cat(
            [condition.embeddings.to(self.pipe.device, dtype=self.pipe.unet.dtype) for condition in source_conditions],
            dim=0,
        )

        aux_histories: list[list[dict[str, np.ndarray]]] = [[] for _ in range(batch_size)]
        trace_histories: list[list[dict[str, float | int | str]]] = [[] for _ in range(batch_size)]
        total_steps = len(self.pipe.scheduler.timesteps)

        for step_idx, timestep in enumerate(self.pipe.scheduler.timesteps):
            source_latent = source_latents[step_idx]
            self._prepare_source_attention_pass(step_idx=step_idx, total_steps=total_steps)
            eps_src = self.source_predictor.predict(latents, timestep, source_embeddings)
            self._prepare_target_attention_pass(step_idx=step_idx, total_steps=total_steps)
            eps_tar, target_noise, _noise_uncond, target_stats = self.target_predictor.predict(
                latents,
                timestep,
                target_embeddings,
            )
            timestep_value = int(timestep.item()) if hasattr(timestep, "item") else int(timestep)
            attention_map = aggregate_step_cross_attention(
                self.attention_store,
                focus_masks,
                target_hw=(latents.shape[-2], latents.shape[-1]),
                locations=self.config.mask.attention_locations,
            )

            dynamic_mask, aux_tensor = builder.build(
                eps_src,
                target_noise,
                latents,
                source_latent,
                attention_map,
                step_idx=step_idx,
                total_steps=total_steps,
            )
            gain_basis, gain_field, edit_field = self._build_gain_maps(
                dynamic_mask=dynamic_mask,
                aux_tensor=aux_tensor,
                roi_mask=roi_mask,
                step_idx=step_idx,
                total_steps=total_steps,
            )
            aux_tensor["dynamic_mask"] = dynamic_mask
            aux_tensor["roi_mask"] = roi_mask
            aux_tensor["gain_basis"] = roi_mask * gain_basis
            aux_tensor["gain_field"] = roi_mask * gain_field
            aux_tensor["mask"] = edit_field
            eps = eps_src + edit_field * (eps_tar - eps_src)

            delta_values = target_stats.get("delta_per_sample", [])
            mean_delta = float(sum(delta_values) / len(delta_values)) if delta_values else float(target_stats["delta"])
            sample_ids = ",".join(sample.sample_id for sample in samples)
            print(f"[{method_name}][batch={batch_size}][{sample_ids}] {step_idx} {timestep_value} {mean_delta:.6f}")

            discrepancy_gap = torch.abs(target_noise - eps_src).flatten(1).mean(dim=1)
            src_tar_gap = torch.abs(eps_tar - eps_src).flatten(1).mean(dim=1)
            applied_gap = torch.abs(eps - eps_src).flatten(1).mean(dim=1)
            blend_strength = torch.where(src_tar_gap > 1e-8, applied_gap / src_tar_gap, torch.zeros_like(applied_gap))
            gamma_t = builder.latent_weight_for_step(step_idx=step_idx, total_steps=total_steps)

            prev_latents = self.pipe.scheduler.step(eps, timestep, latents).prev_sample
            latents = self._post_scheduler_step_latents(
                method_name=method_name,
                prev_latents=prev_latents,
                roi_mask=roi_mask,
                source_latents=source_latents,
                step_idx=step_idx,
                total_steps=total_steps,
            )

            dynamic_mask_roi_mean = self._masked_mean(dynamic_mask, roi_mask)
            gain_basis_roi_mean = self._masked_mean(gain_basis, roi_mask)
            gain_field_roi_mean = self._masked_mean(gain_field, roi_mask)

            for sample_idx in range(batch_size):
                delta = float(delta_values[sample_idx]) if sample_idx < len(delta_values) else float(target_stats["delta"])
                trace_histories[sample_idx].append(
                    {
                        "step_idx": step_idx,
                        "timestep": timestep_value,
                        "delta": delta,
                        "discrepancy_gap": float(discrepancy_gap[sample_idx].item()),
                        "src_tar_gap": float(src_tar_gap[sample_idx].item()),
                        "applied_gap": float(applied_gap[sample_idx].item()),
                        "blend_strength": float(blend_strength[sample_idx].item()),
                        "gamma_t": gamma_t,
                        "roi_mask_mean": float(roi_mask[sample_idx].mean().item()),
                        "dynamic_mask_roi_mean": float(dynamic_mask_roi_mean[sample_idx].item()),
                        "gain_basis_roi_mean": float(gain_basis_roi_mean[sample_idx].item()),
                        "gain_field_roi_mean": float(gain_field_roi_mean[sample_idx].item()),
                    }
                )
                aux_numpy = {
                    key: value[sample_idx, 0].detach().float().cpu().numpy()
                    for key, value in aux_tensor.items()
                    if isinstance(value, torch.Tensor)
                }
                aux_histories[sample_idx].append(aux_numpy)

        edited_images = self._decode_latents_batch(latents)
        results: list[MethodResult] = []
        for sample_idx, sample in enumerate(samples):
            results.append(
                self._finalize_method_result(
                    sample=sample,
                    method_name=method_name,
                    edited_image=edited_images[sample_idx],
                    aux_history=aux_histories[sample_idx],
                    trace_rows=trace_histories[sample_idx],
                    inversion=inversions[sample_idx],
                )
            )

        if self.config.runtime.clear_cuda_cache_between_methods:
            clear_cuda_memory()
        return results
