from __future__ import annotations

import math

from .adapters import clear_cuda_memory
from .schemas import InversionOutput, MaterializedSample, MethodResult, TextCondition
from .v1 import DynamicMaskBuilder, _normalize_tensor_map, aggregate_step_cross_attention
from .v1_source_prompt_hard_roi_locked import V1SourcePromptHardRoiLockedEditor

import numpy as np
import torch
import torch.nn.functional as F


class V1SourcePromptGraphRefinedAttentionEditor(V1SourcePromptHardRoiLockedEditor):
    def __init__(
        self,
        pipe,
        config,
        support_rho: float = 0.85,
        attention_graph_beta: float = 0.60,
        attention_graph_steps: int = 2,
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
        self.attention_graph_beta = float(attention_graph_beta)
        self.attention_graph_steps = int(attention_graph_steps)

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_graph_refined_attention_v1",
                "roi_mask_policy": "always hard roi times dynamic evidence with temporal support accumulation",
                "support_rho": self.support_rho,
                "attention_refinement": "self-attention-guided graph smoothing of target cross-attention",
                "attention_graph_beta": self.attention_graph_beta,
                "attention_graph_steps": self.attention_graph_steps,
                "support_update": "S_t = rho * S_{t-1} + (1-rho) * phi_t, S_0 = phi_0",
                "support_evidence": "phi_t = roi_mask * dynamic_mask",
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

    def _post_scheduler_step_latents(
        self,
        method_name: str,
        prev_latents: torch.Tensor,
        roi_mask: torch.Tensor | None,
        source_latents: list[torch.Tensor],
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor:
        return prev_latents

    def _aggregate_step_self_attention_affinity(
        self,
        batch_size: int,
        locations: tuple[str, ...],
    ) -> tuple[torch.Tensor | None, int | None]:
        averaged = self.attention_store.get_average_attention()
        affinity_by_resolution: dict[int, list[torch.Tensor]] = {}
        for location in locations:
            for item in averaged.get(f"{location}_self", []):
                if item.ndim != 3 or item.shape[0] % batch_size != 0:
                    continue
                query_pixels = int(item.shape[1])
                key_pixels = int(item.shape[2])
                if query_pixels != key_pixels:
                    continue
                resolution = int(math.sqrt(query_pixels))
                if resolution * resolution != query_pixels:
                    continue
                reshaped = item.reshape(batch_size, -1, query_pixels, key_pixels)
                pooled = reshaped.mean(dim=1)
                affinity_by_resolution.setdefault(resolution, []).append(pooled)

        if not affinity_by_resolution:
            return None, None

        resolution = max(affinity_by_resolution.keys())
        affinity = torch.stack(affinity_by_resolution[resolution], dim=0).mean(dim=0)
        affinity = 0.5 * (affinity + affinity.transpose(1, 2))
        affinity = torch.clamp(affinity, min=0.0)
        affinity = affinity / affinity.sum(dim=-1, keepdim=True).clamp(min=1e-6)
        return affinity, resolution

    def _refine_attention_map(
        self,
        attention_map: torch.Tensor,
        batch_size: int,
        locations: tuple[str, ...],
    ) -> tuple[torch.Tensor, torch.Tensor | None, torch.Tensor | None]:
        if attention_map.ndim != 4 or self.attention_graph_steps <= 0:
            return attention_map, None, None

        affinity, resolution = self._aggregate_step_self_attention_affinity(batch_size, locations)
        if affinity is None or resolution is None:
            return attention_map, None, None

        raw_attention = attention_map
        affinity = affinity.to(device=raw_attention.device, dtype=raw_attention.dtype)
        coarse_attention = F.interpolate(
            raw_attention,
            size=(resolution, resolution),
            mode="bilinear",
            align_corners=False,
        )
        base = coarse_attention.flatten(2).transpose(1, 2)
        refined = base
        graph_support = torch.bmm(affinity, base)
        beta = max(0.0, min(1.0, self.attention_graph_beta))
        for _ in range(self.attention_graph_steps):
            refined = (1.0 - beta) * base + beta * torch.bmm(affinity, refined)
        refined_attention = refined.transpose(1, 2).reshape(batch_size, 1, resolution, resolution)
        refined_attention = F.interpolate(
            refined_attention,
            size=raw_attention.shape[-2:],
            mode="bilinear",
            align_corners=False,
        )
        refined_attention = _normalize_tensor_map(refined_attention)
        graph_support_map = graph_support.transpose(1, 2).reshape(batch_size, 1, resolution, resolution)
        graph_support_map = F.interpolate(
            graph_support_map,
            size=raw_attention.shape[-2:],
            mode="bilinear",
            align_corners=False,
        )
        graph_support_map = _normalize_tensor_map(graph_support_map)
        return refined_attention, raw_attention, graph_support_map

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
            raw_attention_map = aggregate_step_cross_attention(
                self.attention_store,
                focus_masks,
                target_hw=(latents.shape[-2], latents.shape[-1]),
                locations=self.config.mask.attention_locations,
            )
            attention_map, _attention_raw, _attention_graph = self._refine_attention_map(
                raw_attention_map,
                batch_size=len(samples),
                locations=self.config.mask.attention_locations,
            )
            if method_name == "target_only":
                effective_mask = torch.ones_like(eps_src[:, :1])
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
                support_evidence = self._compose_effective_mask(
                    method_name,
                    dynamic_mask,
                    roi_mask,
                    step_idx=0,
                    total_steps=total_steps,
                )
                effective_mask = self._update_support_state(None, support_evidence)
                eps = eps_src + effective_mask * (eps_tar - eps_src)
            probe_latents = self.pipe.scheduler.step(eps, timestep, latents).prev_sample
            probe_latents = self._post_scheduler_step_latents(
                method_name=method_name,
                prev_latents=probe_latents,
                roi_mask=roi_mask,
                source_latents=source_latents,
                step_idx=0,
                total_steps=total_steps,
            )
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
            raw_attention_map = aggregate_step_cross_attention(
                self.attention_store,
                focus_masks,
                target_hw=(latents.shape[-2], latents.shape[-1]),
                locations=self.config.mask.attention_locations,
            )
            attention_map, attention_raw, attention_graph = self._refine_attention_map(
                raw_attention_map,
                batch_size=batch_size,
                locations=self.config.mask.attention_locations,
            )

            if method_name == "target_only":
                aux_tensor = builder._compute_aux_maps(eps_src, target_noise, latents, source_latent, attention_map)
                dynamic_mask = torch.ones_like(eps_src[:, :1])
                support_evidence = dynamic_mask
                support_state = dynamic_mask if support_state is None else dynamic_mask
                effective_mask = support_state
                if attention_raw is not None:
                    aux_tensor["attention_raw"] = attention_raw
                if attention_graph is not None:
                    aux_tensor["attention_graph"] = attention_graph
                aux_tensor["dynamic_mask"] = dynamic_mask
                aux_tensor["roi_mask"] = roi_mask
                aux_tensor["support_evidence"] = support_evidence
                aux_tensor["support_state"] = support_state
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
                if attention_raw is not None:
                    aux_tensor["attention_raw"] = attention_raw
                if attention_graph is not None:
                    aux_tensor["attention_graph"] = attention_graph
                support_evidence = self._compose_effective_mask(
                    method_name,
                    dynamic_mask,
                    roi_mask,
                    step_idx,
                    total_steps,
                )
                support_state = self._update_support_state(support_state, support_evidence)
                effective_mask = support_state
                aux_tensor["dynamic_mask"] = dynamic_mask
                aux_tensor["roi_mask"] = roi_mask
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
            attention_refine_delta = (
                torch.abs(attention_map - raw_attention_map).flatten(1).mean(dim=1)
                if attention_raw is not None
                else torch.zeros(batch_size, device=latents.device, dtype=latents.dtype)
            )

            scheduler_output = self.pipe.scheduler.step(eps, timestep, latents)
            latents = self._post_scheduler_step_latents(
                method_name=method_name,
                prev_latents=scheduler_output.prev_sample,
                roi_mask=roi_mask,
                source_latents=source_latents,
                step_idx=step_idx,
                total_steps=total_steps,
            )

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
                        "attention_refine_delta_mean": float(attention_refine_delta[sample_idx].item()),
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
