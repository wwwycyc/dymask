from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch

from .adapters import clear_cuda_memory
from .config import ExperimentConfig
from .schemas import InversionOutput, MaterializedSample, MethodResult, TextCondition
from .utils import mask_to_rgb, save_csv_records, save_image, save_json, summarize_step_maps
from .v1 import (
    DDIMInversionBackend as BaseDDIMInversionBackend,
    DynamicMaskBuilder,
    V1Editor as BaseV1Editor,
    _select_step_indices,
    aggregate_step_cross_attention,
)


class SourcePromptDDIMInversionBackend(BaseDDIMInversionBackend):
    @torch.no_grad()
    def invert(self, source_image: np.ndarray, source_prompt: str | None = None) -> InversionOutput:
        prompt = (source_prompt or "").strip()
        self.ntip2p.ptp_utils.register_attention_control(self.pipe, None)
        inversion = self.ntip2p.NullInversion(self.pipe)
        inversion.init_prompt(prompt)
        reconstruction_image, ddim_latents = inversion.ddim_inversion(source_image)
        src_latents = [latent.detach().clone() for latent in reversed(ddim_latents[1:])]
        inversion_timesteps = [
            int(timestep.item()) if hasattr(timestep, "item") else int(timestep)
            for timestep in self.pipe.scheduler.timesteps
        ]
        return InversionOutput(
            zt_src=ddim_latents[-1].detach().clone(),
            src_latents=src_latents,
            reconstruction_image=reconstruction_image,
            null_embeddings=None,
            metadata={
                "backend": "ddim",
                "source_prompt": prompt,
                "source_prompt_used_for_inversion": bool(prompt),
                "inversion_prompt_mode": "source_prompt" if prompt else "empty",
                "num_inversion_steps": self.runtime.num_inversion_steps,
                "inversion_timesteps": inversion_timesteps,
            },
        )


class PromptConditionSourcePredictor:
    def __init__(self, pipe) -> None:
        self.pipe = pipe

    @torch.no_grad()
    def predict(
        self,
        latents: torch.Tensor,
        timestep: torch.Tensor,
        source_embeddings: torch.Tensor,
    ) -> torch.Tensor:
        batch_size = latents.shape[0]
        if source_embeddings.shape[0] != batch_size:
            raise ValueError(f"source_embeddings batch mismatch: expected {batch_size}, got {source_embeddings.shape[0]}")
        return self.pipe.unet(latents, timestep, encoder_hidden_states=source_embeddings).sample


class V1SourcePromptEditor(BaseV1Editor):
    def __init__(self, pipe, config: ExperimentConfig, inversion_backend=None) -> None:
        if inversion_backend is None:
            inversion_backend = SourcePromptDDIMInversionBackend(pipe, config.runtime)
        super().__init__(pipe, config, inversion_backend=inversion_backend)
        self.source_predictor = PromptConditionSourcePredictor(pipe)

    def _encode_source_conditions(self, samples: list[MaterializedSample]) -> list[TextCondition]:
        return [self.prompt_encoder.encode(sample.source_prompt) for sample in samples]

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        prompt = (sample.source_prompt or "").strip()
        return {
            "reference_prompt": prompt,
            "reference_prompt_mode": "source_prompt" if prompt else "empty",
            "source_prompt_used_for_reference_branch": bool(prompt),
            "attention_prompt_mode": "target_prompt",
        }

    def _finalize_method_result(
        self,
        sample: MaterializedSample,
        method_name: str,
        edited_image: np.ndarray,
        aux_history: list[dict[str, np.ndarray]],
        trace_rows: list[dict[str, float | int]],
        inversion: InversionOutput,
    ) -> MethodResult:
        result = super()._finalize_method_result(
            sample=sample,
            method_name=method_name,
            edited_image=edited_image,
            aux_history=aux_history,
            trace_rows=trace_rows,
            inversion=inversion,
        )
        debug_payload = json.loads(result.debug_json_path.read_text(encoding="utf-8"))
        debug_payload.update(self._reference_prompt_metadata(sample))
        save_json(result.debug_json_path, debug_payload)
        return result

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
        source_latents = torch.cat(
            [
                self._resample_source_latents(
                    [latent.to(self.pipe.device, dtype=self.pipe.unet.dtype) for latent in inversion.src_latents],
                    len(self.pipe.scheduler.timesteps),
                )[0]
                for inversion in inversions
            ],
            dim=0,
        )
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
                mask, _aux_tensor = builder.build(eps_src, target_noise, latents, source_latents, attention_map)
                eps = eps_src + mask * (eps_tar - eps_src)
            probe_latents = self.pipe.scheduler.step(eps, timestep, latents).prev_sample
            _ = self._decode_latents_batch(probe_latents)
        finally:
            self.attention_store.reset()
            clear_cuda_memory()

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

        aux_histories: list[list[dict[str, np.ndarray]]] = [[] for _ in range(batch_size)]
        trace_histories: list[list[dict[str, float | int]]] = [[] for _ in range(batch_size)]

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
                mask = torch.ones_like(eps_src[:, :1])
                aux_tensor["mask"] = mask
                eps = eps_tar
            else:
                mask, aux_tensor = builder.build(eps_src, target_noise, latents, source_latent, attention_map)
                eps = eps_src + mask * (eps_tar - eps_src)

            delta_values = target_stats.get("delta_per_sample", [])
            mean_delta = float(np.mean(delta_values)) if delta_values else float(target_stats["delta"])
            sample_ids = ",".join(sample.sample_id for sample in samples)
            print(f"[{method_name}][batch={batch_size}][{sample_ids}] {step_idx} {timestep_value} {mean_delta:.6f}")

            discrepancy_gap = torch.abs(target_noise - eps_src).flatten(1).mean(dim=1)
            src_tar_gap = torch.abs(eps_tar - eps_src).flatten(1).mean(dim=1)
            applied_gap = torch.abs(eps - eps_src).flatten(1).mean(dim=1)
            blend_strength = torch.where(src_tar_gap > 1e-8, applied_gap / src_tar_gap, torch.zeros_like(applied_gap))

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
                    }
                )
                aux_numpy = {
                    key: value[sample_idx, 0].detach().float().cpu().numpy()
                    for key, value in aux_tensor.items()
                }
                if "mask" not in aux_numpy:
                    aux_numpy["mask"] = mask[sample_idx, 0].detach().float().cpu().numpy()
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

    def visualize_attention_only(self, sample: MaterializedSample, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        self._set_timesteps()

        source_image = self._load_sample_image(sample.source_image_path)
        try:
            inversion = self.inversion_backend.invert(source_image, source_prompt=sample.source_prompt)
        except TypeError:
            inversion = self.inversion_backend.invert(source_image)
        self.ntip2p.ptp_utils.register_attention_control(self.pipe, self.attention_store)
        target_condition = self.prompt_encoder.encode(sample.target_prompt)
        focus_terms = self._extract_focus_terms(sample)
        focus_mask = self._build_focus_token_mask(target_condition, focus_terms)

        latents = inversion.zt_src.detach().clone().to(self.pipe.device, dtype=self.pipe.unet.dtype)
        attention_history: list[np.ndarray] = []
        trace_rows: list[dict[str, float | int]] = []

        for step_idx, timestep in enumerate(self.pipe.scheduler.timesteps):
            self.attention_store.reset()
            eps_tar, _, _, target_stats = self.target_predictor.predict(latents, timestep, target_condition.embeddings)
            timestep_value = int(timestep.item()) if hasattr(timestep, "item") else int(timestep)
            delta = float(target_stats["delta"])
            print(f"[attention_only][{sample.sample_id}] {step_idx} {timestep_value} {delta:.6f}")
            attention_map = aggregate_step_cross_attention(
                self.attention_store,
                focus_mask,
                target_hw=(latents.shape[-2], latents.shape[-1]),
                locations=self.config.mask.attention_locations,
            )
            attention_np = attention_map.detach().float().cpu().numpy()[0, 0]
            attention_history.append(attention_np)
            trace_rows.append({"step_idx": step_idx, "timestep": timestep_value, "delta": delta})
            latents = self.pipe.scheduler.step(eps_tar, timestep, latents).prev_sample

        selected_dir = output_dir / "selected_steps"
        selected_dir.mkdir(parents=True, exist_ok=True)
        indices = _select_step_indices(
            len(attention_history),
            self.config.mask.selected_step_count,
            self.config.mask.selected_step_stride,
        )
        manifest: dict[str, str] = {}
        for index in indices:
            label = f"step_{index:02d}"
            path = selected_dir / f"{label}_attention.png"
            save_image(path, mask_to_rgb(attention_history[index]))
            manifest[label] = str(path)

        overview = summarize_step_maps(attention_history)
        overview_path = output_dir / "attention_overview.png"
        if overview is not None:
            save_image(overview_path, overview)

        save_csv_records(output_dir / "delta_trace.csv", trace_rows)
        debug_payload = {
            "sample_id": sample.sample_id,
            "source_prompt": sample.source_prompt,
            "target_prompt": sample.target_prompt,
            "focus_terms": focus_terms,
            "selected_steps": manifest,
            "delta_trace_path": str(output_dir / "delta_trace.csv"),
        }
        debug_payload.update(self._reference_prompt_metadata(sample))
        save_json(output_dir / "attention_debug.json", debug_payload)
        return overview_path
