from __future__ import annotations

import math
from pathlib import Path

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
        inversion.init_prompt(prompt)
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
    def _write_debug_payload(
        method_dir: Path,
        method_name: str,
        aux_history: list[dict[str, np.ndarray]],
        inversion: InversionOutput,
        trace_rows: list[dict[str, float | int]],
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
            trace_rows.append(
                {
                    "step_idx": step_idx,
                    "timestep": timestep_value,
                    "delta": delta,
                }
            )
            attention_map = aggregate_step_cross_attention(
                self.attention_store,
                target_condition.token_mask,
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
        debug_json_path = self._write_debug_payload(method_dir, method_name, aux_history, inversion, trace_rows)
        clear_cuda_memory()

        return MethodResult(
            method_name=method_name,
            edited_image=edited_image,
            edited_image_path=edited_path,
            mask_summary_path=mask_summary_path,
            aux_summary_path=aux_summary_path,
            delta_trace_path=delta_trace_path,
            debug_json_path=debug_json_path,
        )

    def run_sample(self, sample: MaterializedSample) -> tuple[InversionOutput, list[MethodResult]]:
        source_image = self._load_sample_image(sample.source_image_path)
        inversion = self.inversion_backend.invert(source_image, sample.source_prompt)
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
