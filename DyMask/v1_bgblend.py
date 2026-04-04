from __future__ import annotations

import numpy as np
import torch

from .adapters import clear_cuda_memory
from .schemas import InversionOutput, MaterializedSample, MethodResult, TextCondition
from .v1 import DynamicMaskBuilder, V1Editor as BaseV1Editor, aggregate_step_cross_attention


class V1BackgroundBlendEditor(BaseV1Editor):
    """V1 editor variant that restores source latents on the background after each denoise step."""

    def _blend_with_source_background(
        self,
        edited_latents: torch.Tensor,
        source_latent: torch.Tensor,
        mask: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        edit_mask = mask.to(device=edited_latents.device, dtype=edited_latents.dtype)
        background_mask = 1.0 - edit_mask
        blended_latents = edit_mask * edited_latents + background_mask * source_latent
        return blended_latents, background_mask

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
        timestep = self.pipe.scheduler.timesteps[0]
        total_steps = len(self.pipe.scheduler.timesteps)
        try:
            source_latent = source_latents[0]
            self.attention_store.reset()
            eps_src = self.source_predictor.predict(latents, timestep)
            self.attention_store.reset()
            eps_tar, target_noise, _noise_uncond, _target_stats = self.target_predictor.predict(latents, timestep, target_embeddings)
            attention_map = aggregate_step_cross_attention(
                self.attention_store,
                focus_masks,
                target_hw=(latents.shape[-2], latents.shape[-1]),
                locations=self.config.mask.attention_locations,
            )
            if method_name == "target_only":
                mask = torch.ones_like(eps_src[:, :1])
                eps = eps_tar
            else:
                mask, _aux_tensor = builder.build(
                    eps_src,
                    target_noise,
                    latents,
                    source_latent,
                    attention_map,
                    step_idx=0,
                    total_steps=total_steps,
                )
                eps = eps_src + mask * (eps_tar - eps_src)
            probe_latents = self.pipe.scheduler.step(eps, timestep, latents).prev_sample
            if method_name != "target_only":
                next_source_latent = source_latents[min(1, total_steps - 1)]
                probe_latents, _background_mask = self._blend_with_source_background(probe_latents, next_source_latent, mask)
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

        aux_histories: list[list[dict[str, np.ndarray]]] = [[] for _ in range(batch_size)]
        trace_histories: list[list[dict[str, float | int]]] = [[] for _ in range(batch_size)]
        total_steps = len(self.pipe.scheduler.timesteps)

        for step_idx, timestep in enumerate(self.pipe.scheduler.timesteps):
            source_latent = source_latents[step_idx]
            self.attention_store.reset()
            eps_src = self.source_predictor.predict(latents, timestep)
            self.attention_store.reset()
            eps_tar, target_noise, _noise_uncond, target_stats = self.target_predictor.predict(latents, timestep, target_embeddings)
            timestep_value = int(timestep.item()) if hasattr(timestep, "item") else int(timestep)
            attention_map = aggregate_step_cross_attention(
                self.attention_store,
                focus_masks,
                target_hw=(latents.shape[-2], latents.shape[-1]),
                locations=self.config.mask.attention_locations,
            )

            if method_name == "target_only":
                aux_tensor = builder._compute_aux_maps(eps_src, target_noise, latents, source_latent, attention_map)
                mask = torch.ones_like(eps_src[:, :1])
                background_mask = torch.zeros_like(mask)
                aux_tensor["mask"] = mask
                aux_tensor["background_mask"] = background_mask
                eps = eps_tar
            else:
                mask, aux_tensor = builder.build(
                    eps_src,
                    target_noise,
                    latents,
                    source_latent,
                    attention_map,
                    step_idx=step_idx,
                    total_steps=total_steps,
                )
                background_mask = 1.0 - mask
                aux_tensor["background_mask"] = background_mask
                eps = eps_src + mask * (eps_tar - eps_src)

            delta_values = target_stats.get("delta_per_sample", [])
            mean_delta = float(np.mean(delta_values)) if delta_values else float(target_stats["delta"])
            sample_ids = ",".join(sample.sample_id for sample in samples)
            print(f"[{method_name}][batch={batch_size}][{sample_ids}] {step_idx} {timestep_value} {mean_delta:.6f}")

            discrepancy_gap = torch.abs(target_noise - eps_src).flatten(1).mean(dim=1)
            src_tar_gap = torch.abs(eps_tar - eps_src).flatten(1).mean(dim=1)
            applied_gap = torch.abs(eps - eps_src).flatten(1).mean(dim=1)
            blend_strength = torch.where(src_tar_gap > 1e-8, applied_gap / src_tar_gap, torch.zeros_like(applied_gap))
            gamma_t = builder.latent_weight_for_step(step_idx=step_idx, total_steps=total_steps)

            scheduler_output = self.pipe.scheduler.step(eps, timestep, latents)
            next_latents = scheduler_output.prev_sample
            if method_name == "target_only":
                background_restore = torch.zeros(batch_size, device=next_latents.device, dtype=next_latents.dtype)
                latents = next_latents
            else:
                # The inversion trajectory does not expose an explicit x0 latent, so the
                # last denoise step reuses the final available source latent as fallback.
                next_source_latent = source_latents[min(step_idx + 1, total_steps - 1)]
                blended_latents, background_mask = self._blend_with_source_background(next_latents, next_source_latent, mask)
                background_restore = torch.abs(blended_latents - next_latents).flatten(1).mean(dim=1)
                latents = blended_latents

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
                        "background_ratio": float(background_mask[sample_idx].mean().item()),
                        "background_restore": float(background_restore[sample_idx].item()),
                    }
                )
                aux_numpy = {
                    key: value[sample_idx, 0].detach().float().cpu().numpy()
                    for key, value in aux_tensor.items()
                }
                if "mask" not in aux_numpy:
                    aux_numpy["mask"] = mask[sample_idx, 0].detach().float().cpu().numpy()
                if "background_mask" not in aux_numpy:
                    aux_numpy["background_mask"] = background_mask[sample_idx, 0].detach().float().cpu().numpy()
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
