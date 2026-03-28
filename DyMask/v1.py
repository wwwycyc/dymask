from __future__ import annotations

import json
import math
from pathlib import Path
import re

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

from .adapters import clear_cuda_memory, configure_ntip2p_module, load_ntip2p_module
from .config import ExperimentConfig, MaskConfig, RuntimeConfig
from .schemas import InversionOutput, MaterializedSample, MethodResult, TextCondition
from .utils import mask_to_rgb, save_csv_records, save_image, save_json, summarize_step_maps


def _normalize_tensor_map(tensor: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
    min_value = tensor.amin(dim=(-2, -1), keepdim=True)
    max_value = tensor.amax(dim=(-2, -1), keepdim=True)
    return (tensor - min_value) / (max_value - min_value).clamp(min=eps)


class PromptEncoder:
    def __init__(self, pipe) -> None:
        self.pipe = pipe
        self.cache: dict[str, TextCondition] = {}

    @torch.no_grad()
    def encode(self, prompt: str) -> TextCondition:
        if prompt in self.cache:
            return self.cache[prompt]

        tokenizer = self.pipe.tokenizer
        text_input = tokenizer(
            [prompt],
            padding="max_length",
            max_length=tokenizer.model_max_length,
            truncation=True,
            return_tensors="pt",
        )
        input_ids = text_input.input_ids.to(self.pipe.device)
        embeddings = self.pipe.text_encoder(input_ids)[0]
        token_mask = input_ids != tokenizer.pad_token_id
        if token_mask.shape[-1] > 0:
            token_mask[:, 0] = False
        if tokenizer.eos_token_id is not None:
            token_mask = token_mask & (input_ids != tokenizer.eos_token_id)
        condition = TextCondition(
            prompt=prompt,
            embeddings=embeddings.detach(),
            input_ids=input_ids.detach(),
            token_mask=token_mask.detach(),
        )
        self.cache[prompt] = condition
        return condition


def strip_prompt_markup(prompt: str) -> str:
    return prompt.replace("[", "").replace("]", "")


class DDIMInversionBackend:
    def __init__(self, pipe, runtime: RuntimeConfig) -> None:
        self.pipe = pipe
        self.runtime = runtime
        self.ntip2p = load_ntip2p_module()
        configure_ntip2p_module(self.ntip2p, pipe, runtime)

    @torch.no_grad()
    def invert(self, source_image: np.ndarray, prompt: str) -> InversionOutput:
        self.ntip2p.ptp_utils.register_attention_control(self.pipe, None)
        inversion = self.ntip2p.NullInversion(self.pipe)
        inversion.init_prompt(strip_prompt_markup(prompt))
        reconstruction_image, ddim_latents = inversion.ddim_inversion(source_image)
        src_latents = [latent.detach().clone() for latent in reversed(ddim_latents[1:])]
        return InversionOutput(
            zt_src=ddim_latents[-1].detach().clone(),
            src_latents=src_latents,
            reconstruction_image=reconstruction_image,
            null_embeddings=None,
            metadata={
                "backend": "ddim",
                "num_ddim_steps": self.runtime.num_ddim_steps,
            },
        )


class EmptyPromptSourcePredictor:
    def __init__(self, pipe, prompt_encoder: PromptEncoder) -> None:
        self.pipe = pipe
        self.condition = prompt_encoder.encode("")

    @torch.no_grad()
    def predict(self, latents: torch.Tensor, timestep: torch.Tensor) -> torch.Tensor:
        return self.pipe.unet(latents, timestep, encoder_hidden_states=self.condition.embeddings).sample


class TargetPromptPredictor:
    def __init__(self, pipe, prompt_encoder: PromptEncoder, guidance_scale: float) -> None:
        self.pipe = pipe
        self.guidance_scale = guidance_scale
        self.uncond_condition = prompt_encoder.encode("")

    @torch.no_grad()
    def predict(self, latents: torch.Tensor, timestep: torch.Tensor, target_condition: TextCondition) -> tuple[torch.Tensor, dict[str, float]]:
        latents_input = torch.cat([latents, latents], dim=0)
        context = torch.cat([self.uncond_condition.embeddings, target_condition.embeddings], dim=0)
        noise = self.pipe.unet(latents_input, timestep, encoder_hidden_states=context).sample
        noise_uncond, noise_cond = noise.chunk(2, dim=0)
        delta = (noise_cond - noise_uncond).abs().mean().item()
        guided_noise = noise_uncond + self.guidance_scale * (noise_cond - noise_uncond)
        return guided_noise, {"delta": float(delta)}


def aggregate_step_cross_attention(attention_store, token_mask: torch.Tensor, target_hw: tuple[int, int], locations: tuple[str, ...]) -> torch.Tensor:
    averaged = attention_store.get_average_attention()
    maps: list[torch.Tensor] = []
    device = token_mask.device
    token_mask = token_mask[0].to(device=device, dtype=torch.float32)
    if token_mask.sum() <= 0:
        token_mask = torch.ones_like(token_mask)
    for location in locations:
        for item in averaged.get(f"{location}_cross", []):
            pixel_count = item.shape[1]
            resolution = int(math.sqrt(pixel_count))
            if resolution * resolution != pixel_count:
                continue
            reshaped = item.reshape(1, -1, resolution, resolution, item.shape[-1])[0]
            token_weights = token_mask.to(reshaped.device).view(1, 1, 1, -1)
            token_map = (reshaped * token_weights).sum(dim=-1) / token_weights.sum().clamp(min=1.0)
            pooled = token_map.mean(dim=0, keepdim=True)
            pooled = F.interpolate(
                pooled.unsqueeze(0),
                size=target_hw,
                mode="bilinear",
                align_corners=False,
            ).squeeze(0)
            maps.append(pooled)
    if not maps:
        return torch.zeros((1, *target_hw), device=device, dtype=torch.float32)
    return torch.stack(maps, dim=0).mean(dim=0).to(device=device, dtype=torch.float32)


class DynamicMaskBuilder:
    def __init__(self, mask_config: MaskConfig, variant: str) -> None:
        self.mask_config = mask_config
        self.variant = variant
        self._static_mask: torch.Tensor | None = None

    def reset(self) -> None:
        self._static_mask = None

    def build(
        self,
        eps_src: torch.Tensor,
        eps_tar: torch.Tensor,
        latents: torch.Tensor,
        source_latent: torch.Tensor,
        attention_map: torch.Tensor,
    ) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
        if self.variant.startswith("global_blend"):
            blend_alpha = self.mask_config.global_blend_alpha
            if "_" in self.variant:
                suffix = self.variant.rsplit("_", 1)[-1]
                try:
                    blend_alpha = float(suffix)
                except ValueError:
                    blend_alpha = self.mask_config.global_blend_alpha
            mask = torch.full_like(eps_src[:, :1], blend_alpha)
            return mask, {"mask": mask}

        discrepancy = torch.abs(eps_tar - eps_src).mean(dim=1, keepdim=True)
        discrepancy = _normalize_tensor_map(discrepancy)

        if attention_map.ndim == 3:
            attention_map = attention_map.unsqueeze(0)
        attention_map = attention_map.to(device=eps_src.device, dtype=eps_src.dtype)
        attention_map = _normalize_tensor_map(attention_map)

        latent_drift = torch.abs(latents - source_latent).mean(dim=1, keepdim=True)
        latent_drift = _normalize_tensor_map(latent_drift)

        if self.variant == "discrepancy_only":
            raw_mask = discrepancy
        elif self.variant == "discrepancy_attention":
            raw_mask = (
                self.mask_config.discrepancy_weight * discrepancy
                + self.mask_config.attention_weight * attention_map
            )
        else:
            raw_mask = (
                self.mask_config.discrepancy_weight * discrepancy
                + self.mask_config.attention_weight * attention_map
                + self.mask_config.latent_weight * latent_drift
            )

        if self.mask_config.smoothing_kernel > 1:
            kernel = self.mask_config.smoothing_kernel
            padding = kernel // 2
            raw_mask = F.avg_pool2d(raw_mask, kernel_size=kernel, stride=1, padding=padding)

        mask = torch.sigmoid((raw_mask - self.mask_config.threshold) * self.mask_config.temperature)
        mask = torch.clamp(mask, min=self.mask_config.min_value, max=self.mask_config.max_value)
        mask = mask.to(device=eps_src.device, dtype=eps_src.dtype)

        if self.mask_config.mode == "static":
            if self._static_mask is None:
                self._static_mask = mask.detach().clone()
            mask = self._static_mask

        aux = {
            "discrepancy": discrepancy,
            "attention": attention_map,
            "latent_drift": latent_drift,
            "mask": mask,
        }
        return mask, aux


class V1Editor:
    def __init__(self, pipe, config: ExperimentConfig) -> None:
        self.pipe = pipe
        self.config = config
        self.ntip2p = load_ntip2p_module()
        configure_ntip2p_module(self.ntip2p, pipe, config.runtime)
        self.prompt_encoder = PromptEncoder(pipe)
        self.inversion_backend = DDIMInversionBackend(pipe, config.runtime)
        self.source_predictor = EmptyPromptSourcePredictor(pipe, self.prompt_encoder)
        self.target_predictor = TargetPromptPredictor(pipe, self.prompt_encoder, config.runtime.guidance_scale)
        self.attention_store = self.ntip2p.AttentionStore()
        self.ntip2p.ptp_utils.register_attention_control(self.pipe, self.attention_store)

    def _extract_focus_terms(self, sample: MaterializedSample) -> list[str]:
        terms: list[str] = []
        bracket_terms = re.findall(r"\[([^\]]+)\]", sample.target_prompt)
        terms.extend(term.strip() for term in bracket_terms if term.strip())

        extras = sample.extras or {}
        blended_words = extras.get("blended_words")
        if blended_words:
            try:
                entries = json.loads(blended_words)
                for entry in entries:
                    if not isinstance(entry, str):
                        continue
                    parts = [part.strip() for part in entry.split(",")]
                    if len(parts) == 2 and parts[1] and parts[1] != parts[0]:
                        terms.append(parts[1])
            except Exception:
                pass

        if not terms:
            try:
                edit_payload = json.loads(sample.edit_prompt)
                if isinstance(edit_payload, dict):
                    for key in edit_payload.keys():
                        if key and isinstance(key, str):
                            terms.append(key.strip("[] "))
            except Exception:
                pass

        if not terms:
            source_words = set(strip_prompt_markup(sample.source_prompt).split())
            target_words = strip_prompt_markup(sample.target_prompt).split()
            terms.extend([word for word in target_words if word not in source_words])

        deduped: list[str] = []
        for term in terms:
            clean = term.strip()
            if clean and clean not in deduped:
                deduped.append(clean)
        return deduped

    def _build_focus_token_mask(self, target_condition: TextCondition, focus_terms: list[str]) -> torch.Tensor:
        tokenizer = self.pipe.tokenizer
        prompt_variants = [target_condition.prompt, strip_prompt_markup(target_condition.prompt)]
        focus_mask = torch.zeros_like(target_condition.token_mask, dtype=torch.bool)

        for term in focus_terms:
            term_variants = [term, term.strip("[] "), f"[{term.strip('[] ')}]"]
            split_terms = [piece for piece in term.replace("[", "").replace("]", "").split() if piece]
            term_variants.extend(split_terms)
            found_any = False
            for prompt in prompt_variants:
                for variant in term_variants:
                    inds = self.ntip2p.ptp_utils.get_word_inds(prompt, variant, tokenizer)
                    if len(inds) > 0:
                        focus_mask[:, torch.as_tensor(inds, device=focus_mask.device)] = True
                        found_any = True
                if found_any:
                    break

        if not focus_mask.any():
            return target_condition.token_mask
        return focus_mask

    def _set_timesteps(self) -> None:
        try:
            self.pipe.scheduler.set_timesteps(self.config.runtime.num_ddim_steps, device=self.pipe.device)
        except TypeError:
            self.pipe.scheduler.set_timesteps(self.config.runtime.num_ddim_steps)

    @torch.no_grad()
    def _decode_latents(self, latents: torch.Tensor) -> np.ndarray:
        scaled = latents / 0.18215
        image = self.pipe.vae.decode(scaled).sample
        image = (image / 2 + 0.5).clamp(0, 1)
        image = image.cpu().permute(0, 2, 3, 1).numpy()[0]
        return np.clip(image * 255.0, 0, 255).astype(np.uint8)

    @staticmethod
    def _load_sample_image(path: Path) -> np.ndarray:
        return np.asarray(Image.open(path).convert("RGB")).copy()

    @staticmethod
    def _save_aux_outputs(aux_history: list[dict[str, np.ndarray]], method_dir: Path) -> Path | None:
        if not aux_history:
            return None
        images = []
        for key in ("discrepancy", "attention", "latent_drift", "mask"):
            if any(key not in step for step in aux_history):
                continue
            summary = summarize_step_maps([step[key] for step in aux_history])
            if summary is not None:
                images.append(summary)
        if not images:
            return None
        merged = np.concatenate(images, axis=0)
        aux_path = method_dir / "aux_summary.png"
        save_image(aux_path, merged)
        return aux_path

    def _save_selected_step_outputs(self, aux_history: list[dict[str, np.ndarray]], method_dir: Path) -> Path | None:
        if not aux_history:
            return None
        step_count = min(self.config.mask.selected_step_count, len(aux_history))
        if step_count <= 0:
            return None
        indices = np.linspace(0, len(aux_history) - 1, num=step_count, dtype=int).tolist()
        selected_dir = method_dir / "selected_steps"
        selected_dir.mkdir(parents=True, exist_ok=True)
        mapping: dict[str, dict[str, str]] = {}
        for index in indices:
            step_payload = aux_history[index]
            label = f"step_{index:02d}"
            mapping[label] = {}
            for key, value in step_payload.items():
                path = selected_dir / f"{label}_{key}.png"
                save_image(path, mask_to_rgb(value))
                mapping[label][key] = str(path)
        manifest_path = selected_dir / "selected_steps.json"
        save_json(manifest_path, mapping)
        return manifest_path

    @staticmethod
    def _write_delta_trace(method_dir: Path, trace_rows: list[dict[str, float | int]]) -> Path | None:
        if not trace_rows:
            return None
        csv_path = method_dir / "delta_trace.csv"
        json_path = method_dir / "delta_trace.json"
        save_csv_records(csv_path, trace_rows)
        save_json(json_path, {"trace": trace_rows})
        return csv_path

    @staticmethod
    def _compute_map_stats(map_array: np.ndarray) -> dict[str, float]:
        flat = map_array.astype(np.float32).reshape(-1)
        if flat.size == 0:
            return {
                "mean": 0.0,
                "std": 0.0,
                "min": 0.0,
                "max": 0.0,
                "p05": 0.0,
                "p10": 0.0,
                "p50": 0.0,
                "p90": 0.0,
                "p95": 0.0,
                "top10_mean": 0.0,
                "bottom10_mean": 0.0,
                "top_bottom_gap": 0.0,
                "gt_0_5_ratio": 0.0,
                "entropy": 0.0,
            }

        p05, p10, p50, p90, p95 = np.quantile(flat, [0.05, 0.10, 0.50, 0.90, 0.95]).tolist()
        top_values = flat[flat >= p90]
        bottom_values = flat[flat <= p10]
        top10_mean = float(top_values.mean()) if top_values.size > 0 else float(flat.mean())
        bottom10_mean = float(bottom_values.mean()) if bottom_values.size > 0 else float(flat.mean())

        entropy_values = flat
        if float(flat.min()) < 0.0 or float(flat.max()) > 1.0:
            min_value = float(flat.min())
            max_value = float(flat.max())
            scale = max(max_value - min_value, 1e-6)
            entropy_values = (flat - min_value) / scale
        histogram, _ = np.histogram(np.clip(entropy_values, 0.0, 1.0), bins=20, range=(0.0, 1.0))
        histogram = histogram.astype(np.float64)
        probabilities = histogram[histogram > 0] / max(float(histogram.sum()), 1.0)
        entropy = float(-(probabilities * np.log2(probabilities)).sum()) if probabilities.size > 0 else 0.0

        return {
            "mean": float(flat.mean()),
            "std": float(flat.std()),
            "min": float(flat.min()),
            "max": float(flat.max()),
            "p05": float(p05),
            "p10": float(p10),
            "p50": float(p50),
            "p90": float(p90),
            "p95": float(p95),
            "top10_mean": top10_mean,
            "bottom10_mean": bottom10_mean,
            "top_bottom_gap": float(top10_mean - bottom10_mean),
            "gt_0_5_ratio": float((flat > 0.5).mean()),
            "entropy": entropy,
        }

    @classmethod
    def _write_step_diagnostics(
        cls,
        method_dir: Path,
        method_name: str,
        aux_history: list[dict[str, np.ndarray]],
        trace_rows: list[dict[str, float | int]],
    ) -> tuple[Path | None, Path | None, dict[str, object]]:
        if not aux_history:
            return None, None, {}

        diagnostic_rows: list[dict[str, float | int]] = []
        keys = sorted({key for step in aux_history for key in step.keys()})
        for step_index, step_payload in enumerate(aux_history):
            row: dict[str, float | int] = dict(trace_rows[step_index]) if step_index < len(trace_rows) else {"step_idx": step_index}
            for key in keys:
                if key not in step_payload:
                    continue
                stats = cls._compute_map_stats(step_payload[key])
                for stat_name, stat_value in stats.items():
                    row[f"{key}_{stat_name}"] = stat_value
            diagnostic_rows.append(row)

        summary: dict[str, object] = {}
        for key in keys:
            key_rows = [row for row in diagnostic_rows if f"{key}_mean" in row]
            if not key_rows:
                continue
            summary[key] = {
                "step_count": len(key_rows),
                "mean_of_mean": float(np.mean([float(row[f"{key}_mean"]) for row in key_rows])),
                "mean_of_std": float(np.mean([float(row[f"{key}_std"]) for row in key_rows])),
                "mean_top_bottom_gap": float(np.mean([float(row[f"{key}_top_bottom_gap"]) for row in key_rows])),
                "mean_active_ratio": float(np.mean([float(row[f"{key}_gt_0_5_ratio"]) for row in key_rows])),
                "mean_entropy": float(np.mean([float(row[f"{key}_entropy"]) for row in key_rows])),
                "min_value": float(np.min([float(row[f"{key}_min"]) for row in key_rows])),
                "max_value": float(np.max([float(row[f"{key}_max"]) for row in key_rows])),
            }

        mask_summary = summary.get("mask")
        if isinstance(mask_summary, dict):
            mean_std = float(mask_summary["mean_of_std"])
            top_bottom_gap = float(mask_summary["mean_top_bottom_gap"])
            mask_summary["heuristic_soft_global_like"] = mean_std < 0.05 and top_bottom_gap < 0.25

        csv_path = method_dir / "step_diagnostics.csv"
        json_path = method_dir / "step_diagnostics.json"
        save_csv_records(csv_path, diagnostic_rows)
        save_json(
            json_path,
            {
                "method_name": method_name,
                "step_count": len(diagnostic_rows),
                "steps": diagnostic_rows,
                "summary": summary,
            },
        )
        return csv_path, json_path, summary

    @staticmethod
    def _write_debug_payload(
        method_dir: Path,
        method_name: str,
        aux_history: list[dict[str, np.ndarray]],
        inversion: InversionOutput,
        trace_rows: list[dict[str, float | int]],
        diagnostics_summary: dict[str, object] | None = None,
    ) -> Path:
        deltas = [float(row["delta"]) for row in trace_rows if "delta" in row]
        payload = {
            "method_name": method_name,
            "inversion": inversion.metadata,
            "num_steps": len(aux_history),
            "mask_mean_per_step": [float(step["mask"].mean()) for step in aux_history],
            "mask_std_per_step": [float(step["mask"].std()) for step in aux_history],
            "delta_mean_per_step": deltas,
            "delta_mean": float(np.mean(deltas)) if deltas else None,
            "delta_max": float(np.max(deltas)) if deltas else None,
            "delta_min": float(np.min(deltas)) if deltas else None,
            "diagnostics_summary": diagnostics_summary or {},
        }
        debug_path = method_dir / "debug.json"
        save_json(debug_path, payload)
        return debug_path

    def _run_single_method(
        self,
        sample: MaterializedSample,
        method_name: str,
        inversion: InversionOutput,
        target_condition: TextCondition,
    ) -> MethodResult:
        self._set_timesteps()
        latents = inversion.zt_src.detach().clone().to(self.pipe.device, dtype=self.pipe.unet.dtype)
        source_latents = [
            latent.to(self.pipe.device, dtype=self.pipe.unet.dtype)
            for latent in inversion.src_latents
        ]
        builder = DynamicMaskBuilder(self.config.mask, method_name)
        builder.reset()
        focus_terms = self._extract_focus_terms(sample)
        focus_mask = self._build_focus_token_mask(target_condition, focus_terms)

        aux_history: list[dict[str, np.ndarray]] = []
        mask_history: list[np.ndarray] = []
        trace_rows: list[dict[str, float | int]] = []
        method_dir = sample.sample_dir / method_name
        method_dir.mkdir(parents=True, exist_ok=True)

        for step_idx, timestep in enumerate(self.pipe.scheduler.timesteps):
            source_latent = source_latents[step_idx]
            self.attention_store.reset()
            eps_src = self.source_predictor.predict(latents, timestep)
            self.attention_store.reset()
            eps_tar, target_stats = self.target_predictor.predict(latents, timestep, target_condition)
            timestep_value = int(timestep.item()) if hasattr(timestep, "item") else int(timestep)
            delta = float(target_stats["delta"])
            print(f"[{sample.sample_id}][{method_name}] {step_idx} {timestep_value} {delta:.6f}")
            attention_map = aggregate_step_cross_attention(
                self.attention_store,
                focus_mask,
                target_hw=(latents.shape[-2], latents.shape[-1]),
                locations=self.config.mask.attention_locations,
            )

            if method_name == "target_only":
                mask = torch.ones_like(eps_src[:, :1])
                aux_tensor = {"mask": mask}
                eps = eps_tar
            else:
                mask, aux_tensor = builder.build(eps_src, eps_tar, latents, source_latent, attention_map)
                eps = eps_src + mask * (eps_tar - eps_src)

            src_tar_gap = float(torch.abs(eps_tar - eps_src).mean().item())
            applied_gap = float(torch.abs(eps - eps_src).mean().item())
            blend_strength = applied_gap / src_tar_gap if src_tar_gap > 1e-8 else 0.0
            trace_rows.append(
                {
                    "step_idx": step_idx,
                    "timestep": timestep_value,
                    "delta": delta,
                    "src_tar_gap": src_tar_gap,
                    "applied_gap": applied_gap,
                    "blend_strength": float(blend_strength),
                }
            )

            scheduler_output = self.pipe.scheduler.step(eps, timestep, latents)
            latents = scheduler_output.prev_sample

            aux_numpy = {
                key: value.detach().float().cpu().numpy()[0, 0]
                for key, value in aux_tensor.items()
            }
            if "mask" not in aux_numpy:
                aux_numpy["mask"] = mask.detach().float().cpu().numpy()[0, 0]
            aux_history.append(aux_numpy)
            mask_history.append(aux_numpy["mask"])

        edited_image = self._decode_latents(latents)
        edited_path = method_dir / "edited.png"
        save_image(edited_path, edited_image)

        mask_summary_path = None
        mask_summary = summarize_step_maps(mask_history)
        if mask_summary is not None:
            mask_summary_path = method_dir / "mask_summary.png"
            save_image(mask_summary_path, mask_summary)

        aux_summary_path = self._save_aux_outputs(aux_history, method_dir)
        self._save_selected_step_outputs(aux_history, method_dir)
        delta_trace_path = self._write_delta_trace(method_dir, trace_rows)
        diagnostics_csv_path, diagnostics_json_path, diagnostics_summary = self._write_step_diagnostics(
            method_dir,
            method_name,
            aux_history,
            trace_rows,
        )
        debug_json_path = self._write_debug_payload(
            method_dir,
            method_name,
            aux_history,
            inversion,
            trace_rows,
            diagnostics_summary=diagnostics_summary,
        )
        debug_payload = json.loads(debug_json_path.read_text(encoding="utf-8"))
        debug_payload["focus_terms"] = focus_terms
        save_json(debug_json_path, debug_payload)
        clear_cuda_memory()

        return MethodResult(
            method_name=method_name,
            edited_image=edited_image,
            edited_image_path=edited_path,
            mask_summary_path=mask_summary_path,
            aux_summary_path=aux_summary_path,
            delta_trace_path=delta_trace_path,
            diagnostics_csv_path=diagnostics_csv_path,
            diagnostics_json_path=diagnostics_json_path,
            debug_json_path=debug_json_path,
        )

    def visualize_attention_only(self, sample: MaterializedSample, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        self._set_timesteps()

        source_image = self._load_sample_image(sample.source_image_path)
        inversion = self.inversion_backend.invert(source_image, sample.source_prompt)
        self.ntip2p.ptp_utils.register_attention_control(self.pipe, self.attention_store)
        target_condition = self.prompt_encoder.encode(sample.target_prompt)
        focus_terms = self._extract_focus_terms(sample)
        focus_mask = self._build_focus_token_mask(target_condition, focus_terms)

        latents = inversion.zt_src.detach().clone().to(self.pipe.device, dtype=self.pipe.unet.dtype)
        attention_history: list[np.ndarray] = []
        trace_rows: list[dict[str, float | int]] = []

        for step_idx, timestep in enumerate(self.pipe.scheduler.timesteps):
            self.attention_store.reset()
            eps_tar, target_stats = self.target_predictor.predict(latents, timestep, target_condition)
            timestep_value = int(timestep.item()) if hasattr(timestep, "item") else int(timestep)
            delta = float(target_stats["delta"])
            print(f"[attention_only][{sample.sample_id}] {step_idx} {timestep_value} {delta:.6f}")
            attention_map = aggregate_step_cross_attention(
                self.attention_store,
                focus_mask,
                target_hw=(latents.shape[-2], latents.shape[-1]),
                locations=self.config.mask.attention_locations,
            )
            attention_np = attention_map.detach().float().cpu().numpy()[0]
            attention_history.append(attention_np)
            trace_rows.append({"step_idx": step_idx, "timestep": timestep_value, "delta": delta})
            latents = self.pipe.scheduler.step(eps_tar, timestep, latents).prev_sample

        selected_dir = output_dir / "selected_steps"
        selected_dir.mkdir(parents=True, exist_ok=True)
        step_count = min(self.config.mask.selected_step_count, len(attention_history))
        indices = np.linspace(0, len(attention_history) - 1, num=step_count, dtype=int).tolist()
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
        save_json(
            output_dir / "attention_debug.json",
            {
                "sample_id": sample.sample_id,
                "source_prompt": sample.source_prompt,
                "target_prompt": sample.target_prompt,
                "focus_terms": focus_terms,
                "selected_steps": manifest,
                "delta_trace_path": str(output_dir / "delta_trace.csv"),
            },
        )
        return overview_path

    def run_sample(self, sample: MaterializedSample) -> tuple[InversionOutput, list[MethodResult]]:
        source_image = self._load_sample_image(sample.source_image_path)
        inversion = self.inversion_backend.invert(source_image, sample.source_prompt)
        self.ntip2p.ptp_utils.register_attention_control(self.pipe, self.attention_store)
        save_image(sample.sample_dir / "source_reconstruction.png", inversion.reconstruction_image)
        save_json(sample.sample_dir / "inversion.json", inversion.metadata)
        if self.config.save_inversion_tensors:
            torch.save(inversion.zt_src.detach().cpu(), sample.sample_dir / "zt_src.pt")
            torch.save([latent.detach().cpu() for latent in inversion.src_latents], sample.sample_dir / "src_latents.pt")

        target_condition = self.prompt_encoder.encode(sample.target_prompt)
        method_results = [
            self._run_single_method(sample, method_name, inversion, target_condition)
            for method_name in self.config.methods
        ]
        return inversion, method_results
