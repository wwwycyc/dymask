from __future__ import annotations

from .adapters import clear_cuda_memory
from .schemas import InversionOutput, MaterializedSample, MethodResult, TextCondition
from .v1 import DynamicMaskBuilder, aggregate_step_cross_attention
from .v1_source_prompt_hard_roi_locked import V1SourcePromptHardRoiLockedEditor

import numpy as np
import torch


class V1SourcePromptValidatedSupportEditor(V1SourcePromptHardRoiLockedEditor):
    def __init__(
        self,
        pipe,
        config,
        support_rho: float = 0.85,
        support_lambda: float = 0.5,
        support_kappa: float = 8.0,
        support_alpha: float = 8.0,
        support_delta: float = 0.35,
        diffedit_config=None,
        inversion_backend=None,
    ) -> None:
        super().__init__(
            pipe,
            config,
            diffedit_config=diffedit_config,
            inversion_backend=inversion_backend,
        )
        self.support_rho = float(support_rho)
        self.support_lambda = float(support_lambda)
        self.support_kappa = float(support_kappa)
        self.support_alpha = float(support_alpha)
        self.support_delta = float(support_delta)

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_validated_support_v1",
                "roi_mask_policy": "validated discrepancy accumulation with roi-aware support probability",
                "support_rho": self.support_rho,
                "support_lambda": self.support_lambda,
                "support_kappa": self.support_kappa,
                "support_alpha": self.support_alpha,
                "support_delta": self.support_delta,
                "support_update": (
                    "S_t = rho * S_{t-1} + (1-rho) * (Norm(D_t) * Pi_t), "
                    "M_t = sigmoid(alpha * (S_t - delta))"
                ),
                "support_probability": "Pi_t = sigmoid(kappa * (g_t - h_t))",
            }
        )
        return payload

    def _update_support_state(
        self,
        previous_state: torch.Tensor | None,
        evidence: torch.Tensor,
    ) -> torch.Tensor:
        if previous_state is None:
            return evidence
        return self.support_rho * previous_state + (1.0 - self.support_rho) * evidence

    def _support_consistent_map(
        self,
        method_name: str,
        attention: torch.Tensor,
        roi_mask: torch.Tensor,
    ) -> torch.Tensor:
        if method_name in {"discrepancy_attention", "full_dynamic_mask"}:
            return torch.clamp(self.support_lambda * attention + (1.0 - self.support_lambda) * roi_mask, 0.0, 1.0)
        return roi_mask

    def _support_inconsistent_map(
        self,
        method_name: str,
        attention: torch.Tensor,
        roi_mask: torch.Tensor,
    ) -> torch.Tensor:
        if method_name in {"discrepancy_attention", "full_dynamic_mask"}:
            return (1.0 - roi_mask) * (1.0 - attention)
        return 1.0 - roi_mask

    def _validated_components(
        self,
        method_name: str,
        aux_tensor: dict[str, torch.Tensor],
        roi_mask: torch.Tensor | None,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        discrepancy = aux_tensor["discrepancy"]
        attention = aux_tensor["attention"]
        roi_support = roi_mask if roi_mask is not None else torch.ones_like(discrepancy)
        support_consistent = self._support_consistent_map(method_name, attention, roi_support)
        support_inconsistent = self._support_inconsistent_map(method_name, attention, roi_support)
        support_probability = torch.sigmoid(self.support_kappa * (support_consistent - support_inconsistent))
        support_evidence = discrepancy * support_probability
        return support_consistent, support_inconsistent, support_probability, support_evidence

    def _effective_mask_from_state(self, support_state: torch.Tensor) -> torch.Tensor:
        return torch.sigmoid(self.support_alpha * (support_state - self.support_delta))

    @torch.no_grad()
    def _probe_method_batch_memory(
        self,
        samples: list[MaterializedSample],
        inversions: list[InversionOutput],
        target_conditions: list[TextCondition],
        method_name: str,
    ) -> None:
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
            self.attention_store.reset()
            eps_src = self.source_predictor.predict(latents, timestep, source_embeddings)
            self.attention_store.reset()
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
            if method_name == "target_only":
                effective_mask = torch.ones_like(eps_src[:, :1])
                eps = eps_tar
            else:
                _dynamic_mask, aux_tensor = builder.build(
                    eps_src,
                    target_noise,
                    latents,
                    source_latents[0],
                    attention_map,
                    step_idx=0,
                    total_steps=total_steps,
                )
                _support_consistent, _support_inconsistent, _support_probability, support_evidence = self._validated_components(
                    method_name,
                    aux_tensor,
                    roi_mask,
                )
                support_state = self._update_support_state(None, support_evidence)
                effective_mask = self._effective_mask_from_state(support_state)
                eps = eps_src + effective_mask * (eps_tar - eps_src)
            probe_latents = self.pipe.scheduler.step(eps, timestep, latents).prev_sample
            _ = self._decode_latents_batch(probe_latents)
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
        support_state: torch.Tensor | None = None

        for step_idx, timestep in enumerate(self.pipe.scheduler.timesteps):
            source_latent = source_latents[step_idx]
            self.attention_store.reset()
            eps_src = self.source_predictor.predict(latents, timestep, source_embeddings)
            self.attention_store.reset()
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

            if method_name == "target_only":
                aux_tensor = builder._compute_aux_maps(eps_src, target_noise, latents, source_latent, attention_map)
                support_consistent = torch.ones_like(eps_src[:, :1])
                support_inconsistent = torch.zeros_like(eps_src[:, :1])
                support_probability = torch.ones_like(eps_src[:, :1])
                support_evidence = torch.ones_like(eps_src[:, :1])
                support_state = support_evidence if support_state is None else support_evidence
                effective_mask = support_probability
                aux_tensor["roi_mask"] = roi_mask
                aux_tensor["support_consistent"] = support_consistent
                aux_tensor["support_inconsistent"] = support_inconsistent
                aux_tensor["support_probability"] = support_probability
                aux_tensor["support_evidence"] = support_evidence
                aux_tensor["support_state"] = support_state
                aux_tensor["mask"] = effective_mask
                eps = eps_tar
            else:
                _dynamic_mask, aux_tensor = builder.build(
                    eps_src,
                    target_noise,
                    latents,
                    source_latent,
                    attention_map,
                    step_idx=step_idx,
                    total_steps=total_steps,
                )
                support_consistent, support_inconsistent, support_probability, support_evidence = self._validated_components(
                    method_name,
                    aux_tensor,
                    roi_mask,
                )
                support_state = self._update_support_state(support_state, support_evidence)
                effective_mask = self._effective_mask_from_state(support_state)
                aux_tensor["roi_mask"] = roi_mask
                aux_tensor["support_consistent"] = support_consistent
                aux_tensor["support_inconsistent"] = support_inconsistent
                aux_tensor["support_probability"] = support_probability
                aux_tensor["support_evidence"] = support_evidence
                aux_tensor["support_state"] = support_state
                aux_tensor["mask"] = effective_mask
                eps = eps_src + effective_mask * (eps_tar - eps_src)

            delta_values = target_stats.get("delta_per_sample", [])
            mean_delta = float(sum(delta_values) / len(delta_values)) if delta_values else float(target_stats["delta"])
            sample_ids = ",".join(sample.sample_id for sample in samples)
            print(f"[{method_name}][batch={batch_size}][{sample_ids}] {step_idx} {timestep_value} {mean_delta:.6f}")

            discrepancy_gap = torch.abs(target_noise - eps_src).flatten(1).mean(dim=1)
            src_tar_gap = torch.abs(eps_tar - eps_src).flatten(1).mean(dim=1)
            applied_gap = torch.abs(eps - eps_src).flatten(1).mean(dim=1)
            blend_strength = torch.where(src_tar_gap > 1e-8, applied_gap / src_tar_gap, torch.zeros_like(applied_gap))
            gamma_t = builder.latent_weight_for_step(step_idx=step_idx, total_steps=total_steps)

            scheduler_output = self.pipe.scheduler.step(eps, timestep, latents)
            latents = scheduler_output.prev_sample

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
                        "support_probability_mean": float(support_probability[sample_idx].mean().item()),
                        "support_evidence_mean": float(support_evidence[sample_idx].mean().item()),
                        "support_state_mean": float(support_state[sample_idx].mean().item()),
                        "roi_mask_mean": float(roi_mask[sample_idx].mean().item()),
                    }
                )
                aux_numpy = {
                    key: value[sample_idx, 0].detach().float().cpu().numpy()
                    for key, value in aux_tensor.items()
                    if isinstance(value, torch.Tensor)
                }
                if "mask" not in aux_numpy:
                    aux_numpy["mask"] = effective_mask[sample_idx, 0].detach().float().cpu().numpy()
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
