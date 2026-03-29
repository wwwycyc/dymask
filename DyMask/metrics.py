from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import lpips
import numpy as np
import torch
from PIL import Image
from skimage.metrics import peak_signal_noise_ratio
from transformers import AutoProcessor, CLIPConfig, CLIPModel

from .config import MetricConfig, RuntimeConfig
from .utils import image_to_numpy


class MetricRunner:
    def __init__(self, runtime: RuntimeConfig, metric_config: MetricConfig) -> None:
        self.runtime = runtime
        self.metric_config = metric_config
        self.device = "cpu"
        self._lpips_model = None
        self._clip_model = None
        self._clip_processor = None

    def _lazy_lpips(self):
        if self._lpips_model is not None:
            return self._lpips_model
        self._lpips_model = lpips.LPIPS(net=self.metric_config.lpips_net).to(self.device).eval()
        return self._lpips_model

    def _lazy_lpips_spatial(self):
        if not hasattr(self, '_lpips_spatial_model') or self._lpips_spatial_model is None:
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

    def compute_clipscore(self, image: np.ndarray, text: str) -> float | None:
        if not self.metric_config.enable_clipscore:
            return None
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

    def compute_psnr_masked(self, reference: np.ndarray, prediction: np.ndarray, mask: np.ndarray) -> float:
        """PSNR computed only on outside-mask (non-edit) region. mask: H×W uint8, 1=edit region."""
        ref = image_to_numpy(reference).astype(np.float32)
        pred = image_to_numpy(prediction).astype(np.float32)
        outside = (1 - mask.astype(np.float32))  # 1 where NOT edited
        # zero out edit region in both
        ref_m = ref * outside[:, :, None]
        pred_m = pred * outside[:, :, None]
        mse = np.mean((ref_m - pred_m) ** 2)
        if mse < 1e-10:
            return 100.0
        return float(10.0 * np.log10((255.0 ** 2) / mse))

    def compute_lpips_masked(self, reference: np.ndarray, prediction: np.ndarray, mask: np.ndarray) -> float | None:
        """LPIPS computed only on outside-mask region. mask: H×W uint8, 1=edit region."""
        if not self.metric_config.enable_lpips:
            return None
        model = self._lazy_lpips()
        ref_t = self._to_lpips_tensor(image_to_numpy(reference)).to(self.device)
        pred_t = self._to_lpips_tensor(image_to_numpy(prediction)).to(self.device)
        outside = torch.from_numpy((1 - mask.astype(np.float32))).to(self.device).unsqueeze(0).unsqueeze(0)
        ref_t = ref_t * outside
        pred_t = pred_t * outside
        with torch.no_grad():
            return float(model(ref_t, pred_t).item())

    def compute_locality_ratio(self, source_image: np.ndarray, edited_image: np.ndarray, mask: np.ndarray) -> float | None:
        """Locality ratio: Change_in / (Change_in + Change_out) using LPIPS spatial map."""
        if not self.metric_config.enable_lpips:
            return None
        import torch.nn.functional as F
        model = self._lazy_lpips_spatial()
        src_t = self._to_lpips_tensor(image_to_numpy(source_image)).to(self.device)
        edit_t = self._to_lpips_tensor(image_to_numpy(edited_image)).to(self.device)
        with torch.no_grad():
            delta = model(src_t, edit_t)  # [1, 1, H, W]
        mask_t = torch.from_numpy(mask.astype(np.float32)).to(self.device)  # [H, W]
        if delta.shape[-2:] != mask_t.shape:
            mask_t_4d = mask_t.unsqueeze(0).unsqueeze(0)
            mask_t_4d = F.interpolate(mask_t_4d, size=delta.shape[-2:], mode='nearest')
            mask_t = mask_t_4d.squeeze(0).squeeze(0)
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
                metrics["clip_score"] = self.compute_clipscore(edited_image, target_text)
            except Exception as exc:
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

        # Masked metrics (PIE-Bench gt_mask)
        metrics["outside_psnr"] = None
        metrics["outside_lpips"] = None
        metrics["locality_ratio"] = None
        if gt_mask is not None:
            if self.metric_config.enable_psnr:
                metrics["outside_psnr"] = self.compute_psnr_masked(source_image, edited_image, gt_mask)
            if self.metric_config.enable_lpips:
                try:
                    metrics["outside_lpips"] = self.compute_lpips_masked(source_image, edited_image, gt_mask)
                except Exception as exc:
                    metrics["outside_lpips"] = None
                    metrics["outside_lpips_error"] = str(exc)
                try:
                    metrics["locality_ratio"] = self.compute_locality_ratio(source_image, edited_image, gt_mask)
                except Exception as exc:
                    metrics["locality_ratio"] = None
                    metrics["locality_ratio_error"] = str(exc)
        elif self.metric_config.enable_psnr:
            # fallback: whole-image (existing behavior already captured in edit_source_psnr/lpips)
            metrics["outside_psnr"] = metrics.get("edit_source_psnr")
            metrics["outside_lpips"] = metrics.get("edit_source_lpips")
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
