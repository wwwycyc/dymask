from __future__ import annotations

from pathlib import Path

import torch
import torch.nn.functional as F

from .adapters import clear_cuda_memory
from .config import ExperimentConfig
from .schemas import InversionOutput, MaterializedSample, MethodResult, TextCondition
from .v1 import DynamicMaskBuilder, _normalize_tensor_map, aggregate_step_cross_attention
from .v1_source_prompt import V1SourcePromptEditor


class V1SourcePromptStagewiseEditor(V1SourcePromptEditor):
    def __init__(
        self,
        pipe,
        config: ExperimentConfig,
        static_mask_steps: int = 5,
        stage_split_ratio: float = 0.5,
        inversion_backend=None,
    ) -> None:
        super().__init__(pipe, config, inversion_backend=inversion_backend)
        self.static_mask_steps = max(1, int(static_mask_steps))
        self.stage_split_ratio = float(stage_split_ratio)

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_stagewise_static_roi_v1",
                "static_mask_steps": self.static_mask_steps,
                "stage_split_ratio": self.stage_split_ratio,
            }
        )
        return payload

    @staticmethod
    def _uses_stagewise_static_roi(method_name: str) -> bool:
        return method_name not in {"target_only"} and not method_name.startswith("global_blend")

    def _stage_split_step(self, total_steps: int) -> int:
        if total_steps <= 1:
            return 1
        raw_value = int(total_steps * self.stage_split_ratio)
        return max(1, min(raw_value, total_steps - 1))

    def _mask_from_raw_discrepancy(self, discrepancy: torch.Tensor) -> torch.Tensor:
        raw_mask = discrepancy
        if self.config.mask.smoothing_kernel > 1:
            kernel = self.config.mask.smoothing_kernel
            padding = kernel // 2
            raw_mask = F.avg_pool2d(raw_mask, kernel_size=kernel, stride=1, padding=padding)
        mask = torch.sigmoid((raw_mask - self.config.mask.threshold) * self.config.mask.temperature)
        mask = torch.clamp(mask, min=self.config.mask.min_value, max=self.config.mask.max_value)
        return mask

    @torch.no_grad()
    def _build_static_roi(
        self,
        source_latents: list[torch.Tensor],
        source_embeddings: torch.Tensor,
        target_embeddings: torch.Tensor,
    ) -> torch.Tensor:
        total_steps = len(self.pipe.scheduler.timesteps)
        early_count = max(1, min(self.static_mask_steps, total_steps))
        discrepancy_maps: list[torch.Tensor] = []

        for step_idx in range(early_count):
            timestep = self.pipe.scheduler.timesteps[step_idx]
            source_latent = source_latents[step_idx]
            self.attention_store.reset()
            eps_src = self.source_predictor.predict(source_latent, timestep, source_embeddings)
            self.attention_store.reset()
            _eps_tar, target_noise, _noise_uncond, _target_stats = self.target_predictor.predict(
                source_latent,
                timestep,
                target_embeddings,
            )
            discrepancy = torch.abs(target_noise - eps_src).mean(dim=1, keepdim=True)
            discrepancy_maps.append(_normalize_tensor_map(discrepancy))

        static_discrepancy = torch.stack(discrepancy_maps, dim=0).mean(dim=0)
        static_mask = self._mask_from_raw_discrepancy(static_discrepancy)
        self.attention_store.reset()
        return static_mask.detach()

    def _compose_effective_mask(
        self,
        method_name: str,
        dynamic_mask: torch.Tensor,
        static_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor:
        if not self._uses_stagewise_static_roi(method_name) or static_mask is None:
            return dynamic_mask
        if step_idx < self._stage_split_step(total_steps):
            return static_mask
        return static_mask * dynamic_mask

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
        static_mask = self._build_static_roi(source_latents, source_embeddings, target_embeddings)
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
                eps = eps_tar
            else:
                dynamic_mask, _aux_tensor = builder.build(
                    eps_src,
                    target_noise,
                    latents,
                    source_latents[0],
                    attention_map,
                    step_idx=0,
                    total_steps=total_steps,
                )
                effective_mask = self._compose_effective_mask(method_name, dynamic_mask, static_mask, 0, total_steps)
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

        aux_histories: list[list[dict[str, object]]] = [[] for _ in range(batch_size)]
        trace_histories: list[list[dict[str, float | int | str]]] = [[] for _ in range(batch_size)]
        total_steps = len(self.pipe.scheduler.timesteps)
        static_mask = self._build_static_roi(source_latents, source_embeddings, target_embeddings)
        split_step = self._stage_split_step(total_steps)

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
                dynamic_mask = torch.ones_like(eps_src[:, :1])
                effective_mask = dynamic_mask
                aux_tensor["dynamic_mask"] = dynamic_mask
                aux_tensor["static_mask"] = torch.ones_like(dynamic_mask)
                aux_tensor["mask"] = effective_mask
                eps = eps_tar
            else:
                dynamic_mask, aux_tensor = builder.build(
                    eps_src,
                    target_noise,
                    latents,
                    source_latent,
                    attention_map,
                    step_idx=step_idx,
                    total_steps=total_steps,
                )
                effective_mask = self._compose_effective_mask(
                    method_name,
                    dynamic_mask,
                    static_mask,
                    step_idx,
                    total_steps,
                )
                aux_tensor["dynamic_mask"] = dynamic_mask
                aux_tensor["static_mask"] = static_mask
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

            stage_phase = "early_static" if step_idx < split_step else "late_refine"
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
                        "stage_phase": stage_phase,
                        "static_mask_mean": float(static_mask[sample_idx].mean().item()),
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
