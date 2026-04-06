from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import lpips
import numpy as np
import torch
from PIL import Image
from skimage.metrics import peak_signal_noise_ratio, structural_similarity
from transformers import AutoProcessor, CLIPConfig, CLIPModel

from .config import MetricConfig, RuntimeConfig
from .utils import image_to_numpy


class MetricRunner:
    def __init__(self, runtime: RuntimeConfig, metric_config: MetricConfig) -> None:
        self.runtime = runtime
        self.metric_config = metric_config
        self.device = "cpu"
        self._lpips_model = None
        self._lpips_spatial_model = None
        self._clip_model = None
        self._clip_processor = None

    def _lazy_lpips(self):
        if self._lpips_model is not None:
            return self._lpips_model
        self._lpips_model = lpips.LPIPS(net=self.metric_config.lpips_net).to(self.device).eval()
        return self._lpips_model

    def _lazy_lpips_spatial(self):
        if self._lpips_spatial_model is not None:
            return self._lpips_spatial_model
        self._lpips_spatial_model = lpips.LPIPS(net=self.metric_config.lpips_net, spatial=True).to(self.device).eval()
        return self._lpips_spatial_model

    def _lazy_clip(self):
        if self._clip_model is not None and self._clip_processor is not None:
            return self._clip_model, self._clip_processor
        processor_source = self.runtime.clip_model_id
        model_source = self.runtime.clip_model_id
        clip_config = None
        if self.metric_config.clip_local_files_only:
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
            processor_path, model_path = self._resolve_local_clip_sources(self.runtime.clip_model_id)
            processor_source = str(processor_path)
            model_source = str(model_path)
            clip_config = CLIPConfig.from_pretrained(processor_source, local_files_only=True)
        self._clip_processor = AutoProcessor.from_pretrained(
            processor_source,
            local_files_only=self.metric_config.clip_local_files_only,
            use_fast=False,
        )
        self._clip_model = CLIPModel.from_pretrained(
            model_source,
            config=clip_config,
            local_files_only=self.metric_config.clip_local_files_only,
        ).to(self.device).eval()
        return self._clip_model, self._clip_processor

    @staticmethod
    def _resolve_local_clip_sources(model_id: str) -> tuple[Path, Path]:
        cache_candidates = []
        hf_home = os.environ.get("HF_HOME")
        if hf_home:
            cache_candidates.append(Path(hf_home) / "hub")
        cache_candidates.append(Path.home() / ".cache" / "huggingface" / "hub")
        user_profile = os.environ.get("USERPROFILE")
        if user_profile:
            cache_candidates.append(Path(user_profile) / ".cache" / "huggingface" / "hub")

        snapshots_dir = None
        for cache_root in cache_candidates:
            model_dir = cache_root / f"models--{model_id.replace('/', '--')}"
            candidate = model_dir / "snapshots"
            if candidate.exists():
                snapshots_dir = candidate
                break
        if snapshots_dir is None:
            raise FileNotFoundError(f"Local Hugging Face snapshot not found for model: {model_id}")
        snapshots = sorted(path for path in snapshots_dir.iterdir() if path.is_dir())
        if not snapshots:
            raise FileNotFoundError(f"No local snapshots found for model: {model_id}")
        preferred_files = ("config.json", "preprocessor_config.json", "tokenizer_config.json")
        processor_snapshot = None
        safetensor_snapshot = None
        for snapshot in snapshots:
            if processor_snapshot is None and all((snapshot / name).exists() for name in preferred_files):
                processor_snapshot = snapshot
            if safetensor_snapshot is None and (snapshot / "model.safetensors").exists():
                safetensor_snapshot = snapshot
        if processor_snapshot is None:
            processor_snapshot = snapshots[0]
        if safetensor_snapshot is None:
            safetensor_snapshot = processor_snapshot
        return processor_snapshot, safetensor_snapshot

    @staticmethod
    def _to_lpips_tensor(image: np.ndarray) -> torch.Tensor:
        tensor = torch.from_numpy(image.astype(np.float32) / 255.0)
        tensor = tensor.permute(2, 0, 1).unsqueeze(0)
        return tensor * 2.0 - 1.0

    @staticmethod
    def _normalize_prompt_text(text: str) -> str:
        return " ".join(str(text).strip().split())

    def _clipscore_text(self, text: str) -> str:
        normalized = self._normalize_prompt_text(text)
        if not normalized:
            return normalized
        prefix = self._normalize_prompt_text(self.metric_config.clipscore_text_prefix)
        if not prefix:
            return normalized
        if normalized.lower().startswith(prefix.lower()):
            return normalized
        return f"{prefix} {normalized}"

    @staticmethod
    def _crop_to_mask_bbox(image: np.ndarray, mask: np.ndarray) -> np.ndarray | None:
        mask_bool = mask.astype(bool)
        if not np.any(mask_bool):
            return None
        ys, xs = np.nonzero(mask_bool)
        y0, y1 = int(ys.min()), int(ys.max()) + 1
        x0, x1 = int(xs.min()), int(xs.max()) + 1
        return image_to_numpy(image)[y0:y1, x0:x1]

    @staticmethod
    def _outside_mask(mask: np.ndarray) -> np.ndarray:
        return (mask <= 0).astype(np.float32)

    @staticmethod
    def _resize_mask_for_spatial_map(mask: np.ndarray, spatial_shape: tuple[int, int], device: str) -> torch.Tensor:
        import torch.nn.functional as F

        mask_tensor = torch.from_numpy(mask.astype(np.float32)).to(device).unsqueeze(0).unsqueeze(0)
        if tuple(mask_tensor.shape[-2:]) != tuple(spatial_shape):
            mask_tensor = F.interpolate(mask_tensor, size=spatial_shape, mode="nearest")
        return mask_tensor.squeeze(0).squeeze(0)

    def _compute_spatial_lpips_delta(self, reference: np.ndarray, prediction: np.ndarray) -> torch.Tensor:
        model = self._lazy_lpips_spatial()
        reference_tensor = self._to_lpips_tensor(image_to_numpy(reference)).to(self.device)
        prediction_tensor = self._to_lpips_tensor(image_to_numpy(prediction)).to(self.device)
        with torch.no_grad():
            return model(reference_tensor, prediction_tensor)

    def _clip_image_text_cosine(self, image: np.ndarray, text: str) -> float:
        model, processor = self._lazy_clip()
        clip_inputs = processor(
            text=[text],
            images=[Image.fromarray(image_to_numpy(image))],
            return_tensors="pt",
            padding=True,
        )
        clip_inputs = {key: value.to(self.device) for key, value in clip_inputs.items()}
        with torch.no_grad():
            outputs = model(**clip_inputs)
            image_embeds = outputs.image_embeds / outputs.image_embeds.norm(dim=-1, keepdim=True)
            text_embeds = outputs.text_embeds / outputs.text_embeds.norm(dim=-1, keepdim=True)
        return float((image_embeds * text_embeds).sum(dim=-1).item())

    def compute_psnr(self, reference: np.ndarray, prediction: np.ndarray) -> float:
        reference = image_to_numpy(reference)
        prediction = image_to_numpy(prediction)
        return float(peak_signal_noise_ratio(reference, prediction, data_range=255))

    def compute_lpips(self, reference: np.ndarray, prediction: np.ndarray) -> float | None:
        if not self.metric_config.enable_lpips:
            return None
        model = self._lazy_lpips()
        reference_tensor = self._to_lpips_tensor(image_to_numpy(reference)).to(self.device)
        prediction_tensor = self._to_lpips_tensor(image_to_numpy(prediction)).to(self.device)
        with torch.no_grad():
            return float(model(reference_tensor, prediction_tensor).item())

    def compute_clip_similarity(self, image: np.ndarray, text: str) -> float | None:
        if not self.metric_config.enable_clipscore:
            return None
        normalized_text = self._normalize_prompt_text(text)
        if not normalized_text:
            return None
        return self._clip_image_text_cosine(image_to_numpy(image), normalized_text)

    def compute_clipscore(self, image: np.ndarray, text: str) -> float | None:
        if not self.metric_config.enable_clipscore:
            return None
        clipscore_text = self._clipscore_text(text)
        if not clipscore_text:
            return None
        cosine = self._clip_image_text_cosine(image_to_numpy(image), clipscore_text)
        return float(2.5 * max(cosine, 0.0))

    def compute_clipscore_edit_part(self, image: np.ndarray, text: str, mask: np.ndarray) -> float | None:
        cropped = self._crop_to_mask_bbox(image_to_numpy(image), mask)
        if cropped is None:
            return None
        return self.compute_clipscore(cropped, text)

    def compute_clip_similarity_edit_part(self, image: np.ndarray, text: str, mask: np.ndarray) -> float | None:
        cropped = self._crop_to_mask_bbox(image_to_numpy(image), mask)
        if cropped is None:
            return None
        return self.compute_clip_similarity(cropped, text)

    def compute_mse_masked(self, reference: np.ndarray, prediction: np.ndarray, mask: np.ndarray) -> float | None:
        ref = image_to_numpy(reference).astype(np.float32)
        pred = image_to_numpy(prediction).astype(np.float32)
        outside = self._outside_mask(mask)
        valid_pixels = float(outside.sum())
        if valid_pixels < 1e-8:
            return None
        squared_error = ((ref - pred) ** 2) * outside[:, :, None]
        return float(squared_error.sum() / (valid_pixels * ref.shape[2]))

    def compute_psnr_masked(self, reference: np.ndarray, prediction: np.ndarray, mask: np.ndarray) -> float | None:
        mse = self.compute_mse_masked(reference, prediction, mask)
        if mse is None:
            return None
        if mse < 1e-10:
            return 100.0
        return float(10.0 * np.log10((255.0 ** 2) / mse))

    def compute_ssim_masked(self, reference: np.ndarray, prediction: np.ndarray, mask: np.ndarray) -> float | None:
        ref = image_to_numpy(reference)
        pred = image_to_numpy(prediction)
        outside = self._outside_mask(mask)
        if float(outside.sum()) < 1e-8:
            return None
        _, ssim_map = structural_similarity(ref, pred, data_range=255, channel_axis=2, full=True)
        if ssim_map.ndim == 3:
            ssim_map = ssim_map.mean(axis=2)
        return float((ssim_map.astype(np.float32) * outside).sum() / outside.sum())

    def compute_lpips_masked(
        self,
        reference: np.ndarray,
        prediction: np.ndarray,
        mask: np.ndarray,
        spatial_delta: torch.Tensor | None = None,
    ) -> float | None:
        if not self.metric_config.enable_lpips:
            return None
        delta = spatial_delta if spatial_delta is not None else self._compute_spatial_lpips_delta(reference, prediction)
        outside = self._resize_mask_for_spatial_map(self._outside_mask(mask), tuple(delta.shape[-2:]), self.device)
        denom = float(outside.sum().item())
        if denom < 1e-8:
            return None
        return float((delta.squeeze() * outside).sum().item() / denom)

    def compute_locality_ratio(
        self,
        source_image: np.ndarray,
        edited_image: np.ndarray,
        mask: np.ndarray,
        spatial_delta: torch.Tensor | None = None,
    ) -> float | None:
        if not self.metric_config.enable_lpips:
            return None
        delta = spatial_delta if spatial_delta is not None else self._compute_spatial_lpips_delta(source_image, edited_image)
        mask_t = self._resize_mask_for_spatial_map(mask.astype(np.float32), tuple(delta.shape[-2:]), self.device)
        change_in = float((delta.squeeze() * mask_t).sum().item())
        change_out = float((delta.squeeze() * (1.0 - mask_t)).sum().item())
        denom = change_in + change_out
        if denom < 1e-8:
            return None
        return float(change_in / denom)

    def evaluate_case(
        self,
        source_image: np.ndarray,
        reconstruction_image: np.ndarray,
        edited_image: np.ndarray,
        target_text: str,
        reference_edited: np.ndarray | None,
        gt_mask: np.ndarray | None = None,
    ) -> dict[str, float | None]:
        metrics: dict[str, float | None] = {}
        if self.metric_config.enable_psnr:
            metrics["source_recon_psnr"] = self.compute_psnr(source_image, reconstruction_image)
        if self.metric_config.enable_lpips:
            try:
                metrics["source_recon_lpips"] = self.compute_lpips(source_image, reconstruction_image)
            except Exception as exc:
                metrics["source_recon_lpips"] = None
                metrics["source_recon_lpips_error"] = str(exc)
        if self.metric_config.enable_clipscore:
            try:
                metrics["clip_similarity"] = self.compute_clip_similarity(edited_image, target_text)
                metrics["clip_score"] = self.compute_clipscore(edited_image, target_text)
            except Exception as exc:
                metrics["clip_similarity"] = None
                metrics["clip_score"] = None
                metrics["clip_score_error"] = str(exc)

        if self.metric_config.enable_psnr:
            metrics["edit_source_psnr"] = self.compute_psnr(source_image, edited_image)
        if self.metric_config.enable_lpips:
            try:
                metrics["edit_source_lpips"] = self.compute_lpips(source_image, edited_image)
            except Exception as exc:
                metrics["edit_source_lpips"] = None
                metrics["edit_source_lpips_error"] = str(exc)

        metrics["edit_reference_mode"] = "target_reference" if reference_edited is not None else "missing"
        metrics["edit_ref_psnr"] = None
        metrics["edit_ref_lpips"] = None
        if reference_edited is not None and self.metric_config.enable_psnr:
            metrics["edit_ref_psnr"] = self.compute_psnr(reference_edited, edited_image)
        if reference_edited is not None and self.metric_config.enable_lpips:
            try:
                metrics["edit_ref_lpips"] = self.compute_lpips(reference_edited, edited_image)
            except Exception as exc:
                metrics["edit_ref_lpips"] = None
                metrics["edit_ref_lpips_error"] = str(exc)

        metrics["outside_mse"] = None
        metrics["outside_psnr"] = None
        metrics["outside_ssim"] = None
        metrics["outside_lpips"] = None
        metrics["locality_ratio"] = None
        metrics["clip_score_edit_part"] = None
        metrics["clip_similarity_edit_part"] = None
        if gt_mask is not None:
            if self.metric_config.enable_clipscore:
                try:
                    metrics["clip_score_edit_part"] = self.compute_clipscore_edit_part(edited_image, target_text, gt_mask)
                    metrics["clip_similarity_edit_part"] = self.compute_clip_similarity_edit_part(edited_image, target_text, gt_mask)
                except Exception as exc:
                    metrics["clip_score_edit_part"] = None
                    metrics["clip_similarity_edit_part"] = None
                    metrics["clip_score_edit_part_error"] = str(exc)

            metrics["outside_mse"] = self.compute_mse_masked(source_image, edited_image, gt_mask)
            if self.metric_config.enable_psnr:
                metrics["outside_psnr"] = self.compute_psnr_masked(source_image, edited_image, gt_mask)
                metrics["outside_ssim"] = self.compute_ssim_masked(source_image, edited_image, gt_mask)
            if self.metric_config.enable_lpips:
                spatial_delta = None
                try:
                    spatial_delta = self._compute_spatial_lpips_delta(source_image, edited_image)
                    metrics["outside_lpips"] = self.compute_lpips_masked(
                        source_image,
                        edited_image,
                        gt_mask,
                        spatial_delta=spatial_delta,
                    )
                except Exception as exc:
                    metrics["outside_lpips"] = None
                    metrics["outside_lpips_error"] = str(exc)
                try:
                    if spatial_delta is None:
                        spatial_delta = self._compute_spatial_lpips_delta(source_image, edited_image)
                    metrics["locality_ratio"] = self.compute_locality_ratio(
                        source_image,
                        edited_image,
                        gt_mask,
                        spatial_delta=spatial_delta,
                    )
                except Exception as exc:
                    metrics["locality_ratio"] = None
                    metrics["locality_ratio_error"] = str(exc)
        return metrics

    def summarize(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not rows:
            return []
        import pandas as pd
        from pandas.api.types import is_numeric_dtype

        frame = pd.DataFrame(rows)
        numeric_columns = [
            column
            for column in frame.columns
            if column not in {"sample_id", "method_name", "source_prompt", "target_prompt", "edit_prompt"}
            and not column.endswith("_path")
            and is_numeric_dtype(frame[column])
        ]
        summaries: list[dict[str, Any]] = []
        grouped = frame.groupby("method_name", dropna=False)
        for method_name, group in grouped:
            summary: dict[str, Any] = {"method_name": method_name, "sample_count": int(len(group))}
            for column in numeric_columns:
                if group[column].notna().any():
                    summary[f"{column}_mean"] = float(group[column].mean())
                    summary[f"{column}_std"] = float(group[column].std(ddof=0))
                else:
                    summary[f"{column}_mean"] = None
                    summary[f"{column}_std"] = None
            summaries.append(summary)
        return summaries
