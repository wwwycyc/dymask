from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch
from diffusers import DDIMInverseScheduler, DDIMScheduler, StableDiffusionDiffEditPipeline
from PIL import Image

from .adapters import clear_cuda_memory
from .config import ExperimentConfig, RuntimeConfig
from .diffedit import DiffEditConfig
from .schemas import InversionOutput, MaterializedSample, MethodResult, TextCondition
from .utils import mask_to_rgb, save_csv_records, save_image, save_json
from .v1 import DynamicMaskBuilder, V1Editor as BaseV1Editor, aggregate_step_cross_attention
from .v1_source_prompt import V1SourcePromptEditor


class V1SourcePromptDiffEditRoiEditor(V1SourcePromptEditor):
    def __init__(
        self,
        pipe,
        config: ExperimentConfig,
        stage_split_ratio: float = 0.5,
        diffedit_config: DiffEditConfig | None = None,
        inversion_backend=None,
    ) -> None:
        default_attn_processors = dict(pipe.unet.attn_processors)
        super().__init__(pipe, config, inversion_backend=inversion_backend)
        self.stage_split_ratio = float(stage_split_ratio)
        self.diffedit_config = diffedit_config or DiffEditConfig()
        self._default_attn_processors = default_attn_processors
        self.diffedit_pipe = self._build_shared_diffedit_pipeline(pipe, config.runtime)

    @staticmethod
    def _build_shared_diffedit_pipeline(pipe, runtime: RuntimeConfig) -> StableDiffusionDiffEditPipeline:
        scheduler = DDIMScheduler.from_config(pipe.scheduler.config, clip_sample=False, set_alpha_to_one=False)
        inverse_scheduler = DDIMInverseScheduler.from_config(
            scheduler.config,
            clip_sample=False,
            set_alpha_to_one=False,
        )
        diffedit_pipe = StableDiffusionDiffEditPipeline(
            vae=pipe.vae,
            text_encoder=pipe.text_encoder,
            tokenizer=pipe.tokenizer,
            unet=pipe.unet,
            scheduler=scheduler,
            safety_checker=None,
            feature_extractor=None,
            inverse_scheduler=inverse_scheduler,
            requires_safety_checker=False,
        )
        execution_device = getattr(pipe, "_execution_device", pipe.device)
        diffedit_pipe = diffedit_pipe.to(execution_device)
        if runtime.attention_slicing:
            diffedit_pipe.enable_attention_slicing()
        if runtime.vae_slicing:
            try:
                diffedit_pipe.vae.enable_slicing()
            except AttributeError:
                pass
        try:
            diffedit_pipe.set_progress_bar_config(disable=True)
        except Exception:
            pass
        return diffedit_pipe

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_diffedit_roi_upperbound_v1",
                "stage_split_ratio": self.stage_split_ratio,
                "roi_source": "diffedit_generate_mask",
                "roi_mask_policy": "early hard roi, late hard roi times dynamic mask",
                "diffedit_config": self.diffedit_config.to_dict(),
            }
        )
        return payload

    @staticmethod
    def _uses_diffedit_roi_cap(method_name: str) -> bool:
        return method_name not in {"target_only"} and not method_name.startswith("global_blend")

    def _stage_split_step(self, total_steps: int) -> int:
        if total_steps <= 1:
            return 1
        raw_value = int(total_steps * self.stage_split_ratio)
        return max(1, min(raw_value, total_steps - 1))

    def _restore_default_attention_processors(self) -> None:
        self.pipe.unet.set_attn_processor(dict(self._default_attn_processors))

    @staticmethod
    def _normalize_mask_batch(mask_output) -> list[np.ndarray]:
        if isinstance(mask_output, np.ndarray):
            if mask_output.ndim == 2:
                return [np.asarray(mask_output, dtype=np.float32)]
            if mask_output.ndim == 3:
                return [np.asarray(mask_output[index], dtype=np.float32) for index in range(mask_output.shape[0])]
        if isinstance(mask_output, list):
            normalized: list[np.ndarray] = []
            for item in mask_output:
                if isinstance(item, Image.Image):
                    normalized.append(np.asarray(item.convert("L"), dtype=np.float32) / 255.0)
                else:
                    normalized.append(np.asarray(item, dtype=np.float32))
            return normalized
        raise ValueError(f"Unexpected DiffEdit mask output type: {type(mask_output)}")

    @staticmethod
    def _load_sample_pil(path: Path) -> Image.Image:
        return Image.open(path).convert("RGB")

    @staticmethod
    def _harden_roi_masks(mask_batch: list[np.ndarray]) -> np.ndarray:
        return np.stack([(np.asarray(mask, dtype=np.float32) > 0.5).astype(np.float32) for mask in mask_batch], axis=0)

    @torch.no_grad()
    def _generate_diffedit_roi_batch(self, samples: list[MaterializedSample]) -> torch.Tensor:
        self._restore_default_attention_processors()
        source_pils = [self._load_sample_pil(sample.source_image_path) for sample in samples]
        mask_output = self.diffedit_pipe.generate_mask(
            image=source_pils,
            source_prompt=[sample.source_prompt for sample in samples],
            target_prompt=[sample.target_prompt for sample in samples],
            num_maps_per_mask=self.diffedit_config.num_maps_per_mask,
            mask_encode_strength=self.diffedit_config.mask_encode_strength,
            mask_thresholding_ratio=self.diffedit_config.mask_thresholding_ratio,
            num_inference_steps=self.config.runtime.num_edit_steps,
            guidance_scale=self.config.runtime.guidance_scale,
            output_type="np",
        )
        mask_batch = self._normalize_mask_batch(mask_output)
        roi_masks = self._harden_roi_masks(mask_batch)
        return torch.from_numpy(roi_masks).unsqueeze(1).to(self.pipe.device, dtype=self.pipe.unet.dtype)

    def _compose_effective_mask(
        self,
        method_name: str,
        dynamic_mask: torch.Tensor,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor:
        if not self._uses_diffedit_roi_cap(method_name) or roi_mask is None:
            return dynamic_mask
        if step_idx < self._stage_split_step(total_steps):
            return roi_mask
        return roi_mask * dynamic_mask

    def _save_roi_mask_analysis(
        self,
        sample: MaterializedSample,
        method_name: str,
        roi_mask: np.ndarray | None,
    ) -> tuple[Path | None, Path | None, dict[str, object]]:
        if roi_mask is None:
            return None, None, {}

        method_dir = sample.sample_dir / method_name
        roi_mask_path = method_dir / "diffedit_roi_mask.png"
        save_image(roi_mask_path, mask_to_rgb(roi_mask))

        summary: dict[str, object] = {}
        roi_alignment_path: Path | None = None
        if sample.gt_mask is not None:
            gt_mask = BaseV1Editor._resize_gt_mask_to_shape(sample.gt_mask, roi_mask.shape[:2])
            row = {"map_key": "diffedit_roi"}
            row.update(BaseV1Editor._compute_gt_alignment_stats(roi_mask.astype(np.float32), gt_mask))
            roi_alignment_path = method_dir / "diffedit_roi_alignment.json"
            save_csv_records(method_dir / "diffedit_roi_alignment.csv", [row])
            summary = {key: value for key, value in row.items() if key != "map_key"}
            save_json(
                roi_alignment_path,
                {
                    "summary": summary,
                    "rows": [row],
                },
            )

        return roi_mask_path, roi_alignment_path, summary

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
        roi_mask = aux_history[0].get("roi_mask") if aux_history else None
        roi_mask_path, roi_alignment_path, roi_alignment_summary = self._save_roi_mask_analysis(
            sample,
            method_name,
            roi_mask.astype(np.float32) if isinstance(roi_mask, np.ndarray) else None,
        )
        debug_payload["diffedit_roi"] = {
            "mask_path": str(roi_mask_path) if roi_mask_path else None,
            "alignment_json_path": str(roi_alignment_path) if roi_alignment_path else None,
            "alignment_summary": roi_alignment_summary,
        }
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
                effective_mask = self._compose_effective_mask(method_name, dynamic_mask, roi_mask, 0, total_steps)
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
                aux_tensor["roi_mask"] = roi_mask
                aux_tensor["static_mask"] = roi_mask
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
                    roi_mask,
                    step_idx,
                    total_steps,
                )
                aux_tensor["dynamic_mask"] = dynamic_mask
                aux_tensor["roi_mask"] = roi_mask
                aux_tensor["static_mask"] = roi_mask
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

            stage_phase = "early_roi_lock" if step_idx < split_step else "late_roi_refine"
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
