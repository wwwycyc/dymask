from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import lpips
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from skimage.metrics import peak_signal_noise_ratio, structural_similarity
from torchvision import transforms
from torchvision.transforms import Resize
from transformers import AutoProcessor, CLIPConfig, CLIPModel

from .config import MetricConfig, RuntimeConfig
from .utils import image_to_numpy


class DinoVitExtractor:
    BLOCK_KEY = "block"
    ATTN_KEY = "attn"
    PATCH_IMD_KEY = "patch_imd"
    QKV_KEY = "qkv"
    KEY_LIST = (BLOCK_KEY, ATTN_KEY, PATCH_IMD_KEY, QKV_KEY)

    def __init__(self, model_name: str, device: str) -> None:
        try:
            self.model = torch.hub.load("facebookresearch/dino:main", model_name, trust_repo=True).to(device)
        except TypeError:
            self.model = torch.hub.load("facebookresearch/dino:main", model_name).to(device)
        self.model.eval()
        self.model_name = model_name
        self.device = device
        self.hook_handlers: list[Any] = []
        self.layers_dict: dict[str, list[int]] = {}
        self.outputs_dict: dict[str, list[torch.Tensor]] = {}
        self._init_hooks_data()

    def _init_hooks_data(self) -> None:
        layer_ids = list(range(12))
        self.layers_dict[self.BLOCK_KEY] = layer_ids.copy()
        self.layers_dict[self.ATTN_KEY] = layer_ids.copy()
        self.layers_dict[self.QKV_KEY] = layer_ids.copy()
        self.layers_dict[self.PATCH_IMD_KEY] = layer_ids.copy()
        for key in self.KEY_LIST:
            self.outputs_dict[key] = []

    def _register_hooks(self) -> None:
        for block_idx, block in enumerate(self.model.blocks):
            if block_idx in self.layers_dict[self.BLOCK_KEY]:
                self.hook_handlers.append(block.register_forward_hook(self._get_block_hook()))
            if block_idx in self.layers_dict[self.ATTN_KEY]:
                self.hook_handlers.append(block.attn.attn_drop.register_forward_hook(self._get_attn_hook()))
            if block_idx in self.layers_dict[self.QKV_KEY]:
                self.hook_handlers.append(block.attn.qkv.register_forward_hook(self._get_qkv_hook()))
            if block_idx in self.layers_dict[self.PATCH_IMD_KEY]:
                self.hook_handlers.append(block.attn.register_forward_hook(self._get_patch_imd_hook()))

    def _clear_hooks(self) -> None:
        for handler in self.hook_handlers:
            handler.remove()
        self.hook_handlers = []

    def _get_block_hook(self):
        def _hook(_model, _inp, output):
            self.outputs_dict[self.BLOCK_KEY].append(output)

        return _hook

    def _get_attn_hook(self):
        def _hook(_model, _inp, output):
            self.outputs_dict[self.ATTN_KEY].append(output)

        return _hook

    def _get_qkv_hook(self):
        def _hook(_model, _inp, output):
            self.outputs_dict[self.QKV_KEY].append(output)

        return _hook

    def _get_patch_imd_hook(self):
        def _hook(_model, _inp, output):
            self.outputs_dict[self.PATCH_IMD_KEY].append(output[0])

        return _hook

    def get_feature_from_input(self, input_img: torch.Tensor) -> list[torch.Tensor]:
        self._register_hooks()
        self.model(input_img)
        feature = self.outputs_dict[self.BLOCK_KEY]
        self._clear_hooks()
        self._init_hooks_data()
        return feature

    def get_qkv_feature_from_input(self, input_img: torch.Tensor) -> list[torch.Tensor]:
        self._register_hooks()
        self.model(input_img)
        feature = self.outputs_dict[self.QKV_KEY]
        self._clear_hooks()
        self._init_hooks_data()
        return feature

    def get_patch_num(self, input_img_shape: tuple[int, ...]) -> int:
        _, _, h, w = input_img_shape
        patch_size = 8 if "8" in self.model_name else 16
        return 1 + (h // patch_size) * (w // patch_size)

    def get_head_num(self) -> int:
        return 6 if "s" in self.model_name else 12

    def get_embedding_dim(self) -> int:
        return 384 if "s" in self.model_name else 768

    def get_keys_from_qkv(self, qkv: torch.Tensor, input_img_shape: tuple[int, ...]) -> torch.Tensor:
        patch_num = self.get_patch_num(input_img_shape)
        head_num = self.get_head_num()
        embedding_dim = self.get_embedding_dim()
        return qkv.reshape(patch_num, 3, head_num, embedding_dim // head_num).permute(1, 2, 0, 3)[1]

    def get_keys_from_input(self, input_img: torch.Tensor, layer_num: int) -> torch.Tensor:
        qkv_features = self.get_qkv_feature_from_input(input_img)[layer_num]
        return self.get_keys_from_qkv(qkv_features, tuple(input_img.shape))

    def get_keys_self_sim_from_input(self, input_img: torch.Tensor, layer_num: int) -> torch.Tensor:
        keys = self.get_keys_from_input(input_img, layer_num=layer_num)
        h, t, d = keys.shape
        concatenated_keys = keys.transpose(0, 1).reshape(t, h * d)
        return self.attn_cosine_sim(concatenated_keys[None, None, ...])

    @staticmethod
    def attn_cosine_sim(x: torch.Tensor, eps: float = 1e-8) -> torch.Tensor:
        x = x[0]
        norm = x.norm(dim=2, keepdim=True)
        factor = torch.clamp(norm @ norm.permute(0, 2, 1), min=eps)
        return (x @ x.permute(0, 2, 1)) / factor


class DinoStructureDistanceCalculator(torch.nn.Module):
    def __init__(self, model_name: str, patch_size: int, device: str) -> None:
        super().__init__()
        self.device = device
        self.extractor = DinoVitExtractor(model_name=model_name, device=device)
        imagenet_norm = transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225))
        self.global_transform = transforms.Compose(
            [
                Resize(patch_size, max_size=480),
                imagenet_norm,
            ]
        )

    def calculate_global_ssim_loss(self, inputs: torch.Tensor, outputs: torch.Tensor) -> torch.Tensor:
        loss = torch.tensor(0.0, device=self.device)
        for a, b in zip(inputs, outputs):
            a = self.global_transform(a)
            b = self.global_transform(b)
            with torch.no_grad():
                target_keys_self_sim = self.extractor.get_keys_self_sim_from_input(a.unsqueeze(0), layer_num=11)
            keys_self_sim = self.extractor.get_keys_self_sim_from_input(b.unsqueeze(0), layer_num=11)
            loss = loss + F.mse_loss(keys_self_sim, target_keys_self_sim)
        return loss


class MetricRunner:
    def __init__(self, runtime: RuntimeConfig, metric_config: MetricConfig) -> None:
        self.runtime = runtime
        self.metric_config = metric_config
        if str(runtime.device).startswith("cuda") and torch.cuda.is_available():
            self.device = runtime.device
        else:
            self.device = "cpu"
        self._lpips_model = None
        self._lpips_spatial_model = None
        self._clip_model = None
        self._clip_processor = None
        self._structure_distance_model = None

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

    def _lazy_structure_distance(self):
        if self._structure_distance_model is not None:
            return self._structure_distance_model
        os.environ.setdefault("TORCH_HOME", str(Path(__file__).resolve().parents[1] / ".cache" / "torch"))
        self._structure_distance_model = DinoStructureDistanceCalculator(
            model_name=self.metric_config.dino_model_name,
            patch_size=self.metric_config.dino_global_patch_size,
            device=self.device,
        ).eval()
        return self._structure_distance_model

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
        tensor = torch.from_numpy(image.astype(np.float32))
        tensor = tensor.permute(2, 0, 1).unsqueeze(0)
        return tensor * 2.0 - 1.0

    @staticmethod
    def _normalize_prompt_text(text: str) -> str:
        return " ".join(str(text).strip().split())

    @staticmethod
    def _broadcast_mask(mask: np.ndarray | None, image: np.ndarray) -> np.ndarray | None:
        if mask is None:
            return None
        mask_arr = np.asarray(mask, dtype=np.float32)
        if mask_arr.ndim == 2:
            mask_arr = mask_arr[:, :, None]
        if mask_arr.shape[:2] != image.shape[:2]:
            raise ValueError("Mask shape must match image spatial dimensions.")
        return mask_arr

    def _apply_mask(self, image: np.ndarray, mask: np.ndarray | None) -> np.ndarray:
        image_arr = image_to_numpy(image).astype(np.float32)
        mask_arr = self._broadcast_mask(mask, image_arr)
        if mask_arr is None:
            return image_arr
        return image_arr * mask_arr

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

    def compute_clip_similarity(self, image: np.ndarray, text: str, mask: np.ndarray | None = None) -> float | None:
        if not self.metric_config.enable_clipscore:
            return None
        normalized_text = self._normalize_prompt_text(text)
        if not normalized_text:
            return None
        masked = np.uint8(np.clip(self._apply_mask(image_to_numpy(image), mask), 0.0, 255.0))
        cosine = self._clip_image_text_cosine(masked, normalized_text)
        return float(max(100.0 * cosine, 0.0))

    def compute_psnr(self, reference: np.ndarray, prediction: np.ndarray, mask_ref: np.ndarray | None = None, mask_pred: np.ndarray | None = None) -> float:
        ref = self._apply_mask(reference, mask_ref) / 255.0
        pred = self._apply_mask(prediction, mask_pred) / 255.0
        return float(peak_signal_noise_ratio(ref, pred, data_range=1.0))

    def compute_lpips(
        self,
        reference: np.ndarray,
        prediction: np.ndarray,
        mask_ref: np.ndarray | None = None,
        mask_pred: np.ndarray | None = None,
    ) -> float | None:
        if not self.metric_config.enable_lpips:
            return None
        model = self._lazy_lpips()
        ref = self._apply_mask(reference, mask_ref) / 255.0
        pred = self._apply_mask(prediction, mask_pred) / 255.0
        ref_tensor = self._to_lpips_tensor(ref).to(self.device)
        pred_tensor = self._to_lpips_tensor(pred).to(self.device)
        with torch.no_grad():
            return float(model(pred_tensor, ref_tensor).item())

    def compute_mse(
        self,
        reference: np.ndarray,
        prediction: np.ndarray,
        mask_ref: np.ndarray | None = None,
        mask_pred: np.ndarray | None = None,
    ) -> float:
        ref = self._apply_mask(reference, mask_ref) / 255.0
        pred = self._apply_mask(prediction, mask_pred) / 255.0
        return float(np.mean((pred - ref) ** 2))

    def compute_ssim(
        self,
        reference: np.ndarray,
        prediction: np.ndarray,
        mask_ref: np.ndarray | None = None,
        mask_pred: np.ndarray | None = None,
    ) -> float:
        ref = self._apply_mask(reference, mask_ref) / 255.0
        pred = self._apply_mask(prediction, mask_pred) / 255.0
        return float(structural_similarity(ref, pred, data_range=1.0, channel_axis=2))

    def compute_structure_distance(
        self,
        reference: np.ndarray,
        prediction: np.ndarray,
        mask_ref: np.ndarray | None = None,
        mask_pred: np.ndarray | None = None,
    ) -> float | None:
        if not self.metric_config.enable_structure_distance:
            return None
        model = self._lazy_structure_distance()
        ref = self._apply_mask(reference, mask_ref)
        pred = self._apply_mask(prediction, mask_pred)
        ref_tensor = torch.from_numpy(np.transpose(ref, axes=(2, 0, 1))).unsqueeze(0).to(self.device)
        pred_tensor = torch.from_numpy(np.transpose(pred, axes=(2, 0, 1))).unsqueeze(0).to(self.device)
        with torch.no_grad():
            score = model.calculate_global_ssim_loss(ref_tensor, pred_tensor)
        return float(score.detach().cpu().item())

    def compute_locality_ratio(
        self,
        source_image: np.ndarray,
        edited_image: np.ndarray,
        mask: np.ndarray,
    ) -> float | None:
        if not self.metric_config.enable_lpips:
            return None
        model = self._lazy_lpips_spatial()
        source = self._apply_mask(source_image, None) / 255.0
        edited = self._apply_mask(edited_image, None) / 255.0
        source_tensor = self._to_lpips_tensor(source).to(self.device)
        edited_tensor = self._to_lpips_tensor(edited).to(self.device)
        with torch.no_grad():
            spatial = model(source_tensor, edited_tensor)
        delta = spatial.squeeze()
        if delta.ndim == 0:
            return None
        mask_tensor = torch.from_numpy(mask.astype(np.float32)).to(self.device)
        if mask_tensor.ndim == 2 and tuple(mask_tensor.shape) != tuple(delta.shape[-2:]):
            mask_tensor = F.interpolate(mask_tensor.unsqueeze(0).unsqueeze(0), size=delta.shape[-2:], mode="nearest").squeeze()
        change_in = float((delta * mask_tensor).sum().item())
        change_out = float((delta * (1.0 - mask_tensor)).sum().item())
        denom = change_in + change_out
        if denom < 1e-8:
            return None
        return float(change_in / denom)

    def evaluate_case(
        self,
        source_image: np.ndarray,
        reconstruction_image: np.ndarray,
        edited_image: np.ndarray,
        source_text: str | None = None,
        target_text: str | None = None,
        reference_edited: np.ndarray | None = None,
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

        metrics["clip_similarity_source_image"] = None
        metrics["clip_similarity_target_image"] = None
        metrics["clip_similarity_target_image_edit_part"] = None
        if self.metric_config.enable_clipscore:
            try:
                if source_text:
                    metrics["clip_similarity_source_image"] = self.compute_clip_similarity(source_image, source_text)
                if target_text:
                    metrics["clip_similarity_target_image"] = self.compute_clip_similarity(edited_image, target_text)
                    if gt_mask is not None:
                        metrics["clip_similarity_target_image_edit_part"] = self.compute_clip_similarity(
                            edited_image,
                            target_text,
                            mask=gt_mask,
                        )
            except Exception as exc:
                metrics["clip_similarity_source_image"] = None
                metrics["clip_similarity_target_image"] = None
                metrics["clip_similarity_target_image_edit_part"] = None
                metrics["clip_similarity_error"] = str(exc)

        metrics["psnr"] = None
        metrics["lpips"] = None
        metrics["mse"] = None
        metrics["ssim"] = None
        metrics["structure_distance"] = None
        if self.metric_config.enable_psnr:
            metrics["psnr"] = self.compute_psnr(source_image, edited_image)
            metrics["mse"] = self.compute_mse(source_image, edited_image)
            metrics["ssim"] = self.compute_ssim(source_image, edited_image)
        if self.metric_config.enable_lpips:
            try:
                metrics["lpips"] = self.compute_lpips(source_image, edited_image)
            except Exception as exc:
                metrics["lpips"] = None
                metrics["lpips_error"] = str(exc)
        if self.metric_config.enable_structure_distance:
            try:
                metrics["structure_distance"] = self.compute_structure_distance(source_image, edited_image)
            except Exception as exc:
                metrics["structure_distance"] = None
                metrics["structure_distance_error"] = str(exc)

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

        metrics["psnr_unedit_part"] = None
        metrics["lpips_unedit_part"] = None
        metrics["mse_unedit_part"] = None
        metrics["ssim_unedit_part"] = None
        metrics["structure_distance_unedit_part"] = None
        metrics["locality_ratio"] = None
        if gt_mask is not None:
            unedit_mask = 1.0 - gt_mask.astype(np.float32)
            if self.metric_config.enable_psnr:
                metrics["psnr_unedit_part"] = self.compute_psnr(source_image, edited_image, mask_ref=unedit_mask, mask_pred=unedit_mask)
                metrics["mse_unedit_part"] = self.compute_mse(source_image, edited_image, mask_ref=unedit_mask, mask_pred=unedit_mask)
                metrics["ssim_unedit_part"] = self.compute_ssim(source_image, edited_image, mask_ref=unedit_mask, mask_pred=unedit_mask)
            if self.metric_config.enable_lpips:
                try:
                    metrics["lpips_unedit_part"] = self.compute_lpips(
                        source_image,
                        edited_image,
                        mask_ref=unedit_mask,
                        mask_pred=unedit_mask,
                    )
                except Exception as exc:
                    metrics["lpips_unedit_part"] = None
                    metrics["lpips_unedit_part_error"] = str(exc)
            if self.metric_config.enable_structure_distance:
                try:
                    metrics["structure_distance_unedit_part"] = self.compute_structure_distance(
                        source_image,
                        edited_image,
                        mask_ref=unedit_mask,
                        mask_pred=unedit_mask,
                    )
                except Exception as exc:
                    metrics["structure_distance_unedit_part"] = None
                    metrics["structure_distance_unedit_part_error"] = str(exc)
            if self.metric_config.enable_lpips:
                try:
                    metrics["locality_ratio"] = self.compute_locality_ratio(source_image, edited_image, gt_mask.astype(np.float32))
                except Exception as exc:
                    metrics["locality_ratio"] = None
                    metrics["locality_ratio_error"] = str(exc)

        metrics["clip_similarity"] = metrics["clip_similarity_target_image"]
        metrics["clip_score"] = metrics["clip_similarity_target_image"]
        metrics["clip_similarity_edit_part"] = metrics["clip_similarity_target_image_edit_part"]
        metrics["clip_score_edit_part"] = metrics["clip_similarity_target_image_edit_part"]
        metrics["edit_source_psnr"] = metrics["psnr"]
        metrics["edit_source_lpips"] = metrics["lpips"]
        metrics["outside_mse"] = metrics["mse_unedit_part"]
        metrics["outside_psnr"] = metrics["psnr_unedit_part"]
        metrics["outside_ssim"] = metrics["ssim_unedit_part"]
        metrics["outside_lpips"] = metrics["lpips_unedit_part"]
        return metrics

    def summarize(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not rows:
            return []
        import pandas as pd
        from pandas.api.types import is_numeric_dtype

        frame = pd.DataFrame(rows)
        frame = frame.replace([np.inf, -np.inf], np.nan)
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
