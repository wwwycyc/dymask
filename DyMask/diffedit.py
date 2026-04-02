from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
from diffusers import DDIMInverseScheduler, DDIMScheduler, StableDiffusionDiffEditPipeline
from PIL import Image

from .adapters import clear_cuda_memory
from .config import ExperimentConfig, RuntimeConfig
from .schemas import InversionOutput, MaterializedSample, MethodResult
from .utils import compose_labeled_overview, mask_to_rgb, save_csv_records, save_image, save_json
from .v1 import V1Editor as BaseV1Editor


@dataclass
class DiffEditConfig:
    num_maps_per_mask: int = 10
    mask_encode_strength: float = 0.5
    mask_thresholding_ratio: float = 3.0
    inpaint_strength: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_diffedit_pipeline(runtime: RuntimeConfig) -> StableDiffusionDiffEditPipeline:
    device = runtime.device if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device.startswith("cuda") and runtime.dtype == "float16" else torch.float32
    if device.startswith("cuda"):
        torch.backends.cuda.matmul.allow_tf32 = runtime.enable_tf32
        torch.backends.cudnn.allow_tf32 = runtime.enable_tf32
        if hasattr(torch, "set_float32_matmul_precision"):
            torch.set_float32_matmul_precision("high" if runtime.enable_tf32 else "highest")

    pipe_kwargs = {
        "torch_dtype": dtype,
        "safety_checker": None,
        "feature_extractor": None,
        "local_files_only": runtime.local_files_only,
        "requires_safety_checker": False,
    }
    try:
        pipe = StableDiffusionDiffEditPipeline.from_pretrained(runtime.model_id, **pipe_kwargs)
    except TypeError:
        pipe_kwargs.pop("requires_safety_checker", None)
        pipe = StableDiffusionDiffEditPipeline.from_pretrained(runtime.model_id, **pipe_kwargs)

    pipe.scheduler = DDIMScheduler.from_config(pipe.scheduler.config, clip_sample=False, set_alpha_to_one=False)
    pipe.inverse_scheduler = DDIMInverseScheduler.from_config(
        pipe.scheduler.config,
        clip_sample=False,
        set_alpha_to_one=False,
    )

    if runtime.enable_cpu_offload and torch.cuda.is_available():
        pipe.enable_model_cpu_offload()
    else:
        pipe = pipe.to(device)
    if runtime.channels_last and device.startswith("cuda"):
        pipe.unet.to(memory_format=torch.channels_last)
        try:
            pipe.vae.to(memory_format=torch.channels_last)
        except Exception:
            pass
    if runtime.attention_slicing:
        pipe.enable_attention_slicing()
    if runtime.vae_slicing:
        try:
            pipe.vae.enable_slicing()
        except AttributeError:
            pass
    if runtime.enable_xformers:
        try:
            pipe.enable_xformers_memory_efficient_attention()
        except Exception:
            pass
    return pipe


class DiffEditEditor:
    def __init__(
        self,
        pipe: StableDiffusionDiffEditPipeline,
        config: ExperimentConfig,
        diffedit_config: DiffEditConfig,
        inversion_backend,
    ) -> None:
        self.pipe = pipe
        self.config = config
        self.diffedit_config = diffedit_config
        self.inversion_backend = inversion_backend

    @property
    def device(self):
        return getattr(self.pipe, "_execution_device", self.pipe.device)

    @staticmethod
    def _is_cuda_oom_error(exc: BaseException) -> bool:
        if isinstance(exc, torch.cuda.OutOfMemoryError):
            return True
        message = str(exc).lower()
        return "cuda" in message and "out of memory" in message

    @staticmethod
    def _next_batch_size(current: int, minimum: int) -> int:
        if current <= minimum:
            return minimum
        next_batch = max(minimum, (current + 1) // 2)
        if next_batch >= current:
            next_batch = current - 1
        return max(minimum, next_batch)

    @staticmethod
    def _load_sample_image(path: Path) -> np.ndarray:
        return np.asarray(Image.open(path).convert("RGB")).copy()

    @staticmethod
    def _load_sample_pil(path: Path) -> Image.Image:
        return Image.open(path).convert("RGB")

    def _get_edit_timesteps(self) -> torch.Tensor:
        try:
            self.pipe.scheduler.set_timesteps(self.config.runtime.num_edit_steps, device=self.device)
        except TypeError:
            self.pipe.scheduler.set_timesteps(self.config.runtime.num_edit_steps)
        timesteps, _ = self.pipe.get_timesteps(
            self.config.runtime.num_edit_steps,
            self.diffedit_config.inpaint_strength,
            self.device,
        )
        return timesteps

    def _prepare_image_latents(self, inversion: InversionOutput, timestep_count: int) -> torch.Tensor:
        source_latents = BaseV1Editor._resample_source_latents(
            [latent.detach().clone().to(self.device, dtype=self.pipe.unet.dtype) for latent in inversion.src_latents],
            timestep_count,
        )
        return torch.stack(source_latents, dim=1)

    def _prepare_image_latents_batch(self, inversions: list[InversionOutput], timestep_count: int) -> torch.Tensor:
        return torch.cat(
            [self._prepare_image_latents(inversion, timestep_count) for inversion in inversions],
            dim=0,
        )

    @staticmethod
    def _mask_stats(mask: np.ndarray) -> dict[str, float]:
        flat = mask.astype(np.float32).reshape(-1)
        return {
            "mean": float(flat.mean()) if flat.size else 0.0,
            "std": float(flat.std()) if flat.size else 0.0,
            "active_ratio": float((flat > 0.5).mean()) if flat.size else 0.0,
            "min": float(flat.min()) if flat.size else 0.0,
            "max": float(flat.max()) if flat.size else 0.0,
        }

    def _save_mask_outputs(self, method_dir: Path, mask_latent: np.ndarray, image_size: tuple[int, int]) -> tuple[Path, Path]:
        latent_mask_path = method_dir / "mask_latent.png"
        resized_mask_path = method_dir / "mask.png"
        save_image(latent_mask_path, mask_to_rgb(mask_latent))
        resized = Image.fromarray((np.clip(mask_latent, 0.0, 1.0) * 255.0).astype(np.uint8)).resize(
            image_size,
            Image.Resampling.NEAREST,
        )
        resized_mask = (np.asarray(resized) > 127).astype(np.float32)
        save_image(resized_mask_path, mask_to_rgb(resized_mask))
        return latent_mask_path, resized_mask_path

    def _save_aux_summary(
        self,
        sample: MaterializedSample,
        method_dir: Path,
        source_image: np.ndarray,
        reconstruction_image: np.ndarray,
        edited_image: np.ndarray,
        resized_mask_rgb: np.ndarray,
    ) -> Path:
        items: list[tuple[str, np.ndarray]] = [
            ("source", source_image),
            ("reconstruction", reconstruction_image),
            ("mask", resized_mask_rgb),
            ("edited", edited_image),
        ]
        if sample.target_image_path is not None and Path(sample.target_image_path).exists():
            items.append(("target reference", np.asarray(Image.open(sample.target_image_path).convert("RGB"))))
        overview = compose_labeled_overview(
            items,
            columns=min(3, len(items)),
            tile_size=(self.config.runtime.image_size, self.config.runtime.image_size),
            title=sample.sample_id,
        )
        aux_summary_path = method_dir / "aux_summary.png"
        save_image(aux_summary_path, overview)
        return aux_summary_path

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
    def _normalize_image_batch(images) -> list[np.ndarray]:
        if isinstance(images, list):
            return [np.asarray(image.convert("RGB") if isinstance(image, Image.Image) else image).copy() for image in images]
        if isinstance(images, np.ndarray):
            if images.ndim == 3:
                return [np.asarray(images).copy()]
            if images.ndim == 4:
                return [np.asarray(images[index]).copy() for index in range(images.shape[0])]
        raise ValueError(f"Unexpected DiffEdit image output type: {type(images)}")

    def _finalize_diffedit_result(
        self,
        sample: MaterializedSample,
        inversion: InversionOutput,
        mask_latent: np.ndarray,
        edited_image: np.ndarray,
        source_image: np.ndarray,
        source_size: tuple[int, int],
    ) -> MethodResult:
        method_name = "diffedit"
        method_dir = sample.sample_dir / method_name
        method_dir.mkdir(parents=True, exist_ok=True)
        if mask_latent.ndim != 2:
            raise ValueError(f"Unexpected DiffEdit mask shape: {mask_latent.shape}")

        edited_path = method_dir / "edited.png"
        save_image(edited_path, edited_image)

        latent_mask_path, resized_mask_path = self._save_mask_outputs(method_dir, mask_latent, source_size)
        resized_mask = np.asarray(Image.open(resized_mask_path).convert("RGB"))
        aux_summary_path = self._save_aux_summary(
            sample,
            method_dir,
            source_image,
            inversion.reconstruction_image,
            edited_image,
            resized_mask,
        )

        mask_stats = self._mask_stats(mask_latent)
        diagnostics_row = {
            "mask_latent_mean": mask_stats["mean"],
            "mask_latent_std": mask_stats["std"],
            "mask_latent_active_ratio": mask_stats["active_ratio"],
            "mask_latent_min": mask_stats["min"],
            "mask_latent_max": mask_stats["max"],
        }
        diagnostics_csv_path = method_dir / "mask_diagnostics.csv"
        diagnostics_json_path = method_dir / "mask_diagnostics.json"
        save_csv_records(diagnostics_csv_path, [diagnostics_row])
        save_json(
            diagnostics_json_path,
            {
                "method_name": method_name,
                "mask_stats": diagnostics_row,
                "mask_latent_path": str(latent_mask_path),
                "mask_path": str(resized_mask_path),
            },
        )

        debug_json_path = method_dir / "debug.json"
        save_json(
            debug_json_path,
            {
                "method_name": method_name,
                "source_prompt": sample.source_prompt,
                "target_prompt": sample.target_prompt,
                "edit_prompt": sample.edit_prompt,
                "inversion": inversion.metadata,
                "runtime": {
                    "num_inversion_steps": self.config.runtime.num_inversion_steps,
                    "num_edit_steps": self.config.runtime.num_edit_steps,
                    "guidance_scale": self.config.runtime.guidance_scale,
                },
                "diffedit": self.diffedit_config.to_dict(),
                "source_prompt_used_for_inversion": bool(inversion.metadata.get("source_prompt_used_for_inversion")),
                "mask_generation": {
                    "source_prompt": sample.source_prompt,
                    "target_prompt": sample.target_prompt,
                },
                "paths": {
                    "edited_image_path": str(edited_path),
                    "mask_latent_path": str(latent_mask_path),
                    "mask_path": str(resized_mask_path),
                    "aux_summary_path": str(aux_summary_path),
                    "diagnostics_csv_path": str(diagnostics_csv_path),
                    "diagnostics_json_path": str(diagnostics_json_path),
                },
            },
        )

        return MethodResult(
            method_name=method_name,
            edited_image=edited_image,
            edited_image_path=edited_path,
            mask_summary_path=resized_mask_path,
            aux_summary_path=aux_summary_path,
            delta_trace_path=None,
            diagnostics_csv_path=diagnostics_csv_path,
            diagnostics_json_path=diagnostics_json_path,
            debug_json_path=debug_json_path,
        )

    def _run_diffedit_batch(
        self,
        samples: list[MaterializedSample],
        inversions: list[InversionOutput],
    ) -> list[MethodResult]:
        source_images = [self._load_sample_image(sample.source_image_path) for sample in samples]
        source_pils = [self._load_sample_pil(sample.source_image_path) for sample in samples]
        mask_output = self.pipe.generate_mask(
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
        masks = self._normalize_mask_batch(mask_output)
        if len(masks) != len(samples):
            raise ValueError(f"DiffEdit mask batch size mismatch: expected {len(samples)}, got {len(masks)}")

        timesteps = self._get_edit_timesteps()
        image_latents = self._prepare_image_latents_batch(inversions, len(timesteps))
        edited_output = self.pipe(
            prompt=[sample.target_prompt for sample in samples],
            mask_image=np.stack(masks, axis=0),
            image_latents=image_latents,
            inpaint_strength=self.diffedit_config.inpaint_strength,
            num_inference_steps=self.config.runtime.num_edit_steps,
            guidance_scale=self.config.runtime.guidance_scale,
            output_type="pil",
        )
        edited_images = self._normalize_image_batch(edited_output.images)
        if len(edited_images) != len(samples):
            raise ValueError(f"DiffEdit image batch size mismatch: expected {len(samples)}, got {len(edited_images)}")

        results: list[MethodResult] = []
        for sample, inversion, mask_latent, edited_image, source_image, source_pil in zip(
            samples,
            inversions,
            masks,
            edited_images,
            source_images,
            source_pils,
        ):
            results.append(
                self._finalize_diffedit_result(
                    sample=sample,
                    inversion=inversion,
                    mask_latent=mask_latent,
                    edited_image=edited_image,
                    source_image=source_image,
                    source_size=source_pil.size,
                )
            )
        return results

    def run_samples(self, samples: list[MaterializedSample]) -> dict[str, tuple[InversionOutput, list[MethodResult]]]:
        if not samples:
            return {}

        prepared: list[tuple[MaterializedSample, InversionOutput]] = []
        for sample in samples:
            source_image = self._load_sample_image(sample.source_image_path)
            try:
                inversion = self.inversion_backend.invert(source_image, source_prompt=sample.source_prompt)
            except TypeError:
                inversion = self.inversion_backend.invert(source_image)

            save_image(sample.sample_dir / "source_reconstruction.png", inversion.reconstruction_image)
            save_json(sample.sample_dir / "inversion.json", inversion.metadata)
            if self.config.save_inversion_tensors:
                torch.save(inversion.zt_src.detach().cpu(), sample.sample_dir / "zt_src.pt")
                torch.save([latent.detach().cpu() for latent in inversion.src_latents], sample.sample_dir / "src_latents.pt")
            prepared.append((sample, inversion))

        results: dict[str, tuple[InversionOutput, list[MethodResult]]] = {
            sample.sample_id: (inversion, [])
            for sample, inversion in prepared
        }
        batch_size = max(1, int(self.config.runtime.sample_batch_size))
        min_batch_size = max(1, min(int(self.config.runtime.min_sample_batch_size), batch_size))
        auto_batch_fallback = bool(self.config.runtime.auto_batch_fallback) and batch_size > min_batch_size
        active_batch_size = batch_size
        start = 0
        while start < len(prepared):
            current_batch_size = min(active_batch_size, len(prepared) - start)
            batch = prepared[start:start + current_batch_size]
            batch_samples = [sample for sample, _inversion in batch]
            batch_inversions = [inversion for _sample, inversion in batch]
            try:
                batch_method_results = self._run_diffedit_batch(batch_samples, batch_inversions)
            except RuntimeError as exc:
                if not auto_batch_fallback or not self._is_cuda_oom_error(exc) or current_batch_size <= min_batch_size:
                    raise
                next_batch_size = self._next_batch_size(current_batch_size, min_batch_size)
                failed_ids = ",".join(sample.sample_id for sample in batch_samples)
                print(
                    f"[auto-batch-fallback][diffedit] CUDA OOM at batch={current_batch_size} "
                    f"for {failed_ids}; retrying with batch={next_batch_size}"
                )
                active_batch_size = next_batch_size
                clear_cuda_memory()
                continue
            for sample, inversion, method_result in zip(batch_samples, batch_inversions, batch_method_results):
                results[sample.sample_id] = (inversion, [method_result])
            start += current_batch_size
            if self.config.runtime.clear_cuda_cache_between_methods:
                clear_cuda_memory()
        return results
