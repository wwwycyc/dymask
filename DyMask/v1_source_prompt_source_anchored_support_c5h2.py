from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from .schemas import MaterializedSample
from .v1_source_prompt_source_anchored_support_c5h0 import V1SourcePromptSourceAnchoredSupportC5H0Editor


class V1SourcePromptSourceAnchoredSupportC5H2Editor(V1SourcePromptSourceAnchoredSupportC5H0Editor):
    def __init__(
        self,
        pipe,
        config,
        support_rho: float = 0.85,
        anchor_relax_start_strength: float = 0.35,
        anchor_relax_end_strength: float = 0.05,
        core_read_start_weight: float = 0.45,
        core_read_end_weight: float = 0.08,
        boundary_read_start_weight: float = 0.20,
        boundary_read_end_weight: float = 0.04,
        boundary_anchor_start_weight: float = 0.18,
        boundary_anchor_end_weight: float = 0.04,
        boundary_confidence_weight: float = 0.30,
        roi_core_quantile: float = 0.80,
        roi_core_peak_ratio: float = 0.60,
        roi_core_threshold_min: float = 0.15,
        roi_core_threshold_max: float = 0.50,
        roi_core_min_active_ratio: float = 0.05,
        roi_core_active_floor: float = 0.05,
        roi_seed_offset: int = 0,
        roi_cache_root: str = "runs/diffedit_roi_cache/source_prompt_c5h2",
        diffedit_config=None,
        inversion_backend=None,
    ) -> None:
        super().__init__(
            pipe,
            config,
            support_rho=support_rho,
            anchor_relax_start_strength=anchor_relax_start_strength,
            anchor_relax_end_strength=anchor_relax_end_strength,
            diffedit_config=diffedit_config,
            inversion_backend=inversion_backend,
        )
        self.core_read_start_weight = self._validate_unit_interval(
            core_read_start_weight,
            "core_read_start_weight",
        )
        self.core_read_end_weight = self._validate_unit_interval(
            core_read_end_weight,
            "core_read_end_weight",
        )
        self.boundary_read_start_weight = self._validate_unit_interval(
            boundary_read_start_weight,
            "boundary_read_start_weight",
        )
        self.boundary_read_end_weight = self._validate_unit_interval(
            boundary_read_end_weight,
            "boundary_read_end_weight",
        )
        self.boundary_anchor_start_weight = self._validate_unit_interval(
            boundary_anchor_start_weight,
            "boundary_anchor_start_weight",
        )
        self.boundary_anchor_end_weight = self._validate_unit_interval(
            boundary_anchor_end_weight,
            "boundary_anchor_end_weight",
        )
        self.boundary_confidence_weight = self._validate_unit_interval(
            boundary_confidence_weight,
            "boundary_confidence_weight",
        )
        self.roi_core_quantile = self._validate_unit_interval(roi_core_quantile, "roi_core_quantile")
        self.roi_core_peak_ratio = self._validate_unit_interval(roi_core_peak_ratio, "roi_core_peak_ratio")
        self.roi_core_threshold_min = self._validate_unit_interval(
            roi_core_threshold_min,
            "roi_core_threshold_min",
        )
        self.roi_core_threshold_max = self._validate_unit_interval(
            roi_core_threshold_max,
            "roi_core_threshold_max",
        )
        self.roi_core_min_active_ratio = self._validate_unit_interval(
            roi_core_min_active_ratio,
            "roi_core_min_active_ratio",
        )
        self.roi_core_active_floor = self._validate_unit_interval(
            roi_core_active_floor,
            "roi_core_active_floor",
        )
        if self.core_read_end_weight > self.core_read_start_weight:
            raise ValueError("core_read_end_weight must be <= core_read_start_weight")
        if self.boundary_read_end_weight > self.boundary_read_start_weight:
            raise ValueError("boundary_read_end_weight must be <= boundary_read_start_weight")
        if self.boundary_anchor_end_weight > self.boundary_anchor_start_weight:
            raise ValueError("boundary_anchor_end_weight must be <= boundary_anchor_start_weight")
        if self.roi_core_threshold_max < self.roi_core_threshold_min:
            raise ValueError("roi_core_threshold_max must be >= roi_core_threshold_min")
        self.roi_seed_offset = int(roi_seed_offset)
        self.roi_cache_root = Path(roi_cache_root)
        self._roi_cache_signature = self._build_roi_cache_signature()
        self._current_roi_core_mask: torch.Tensor | None = None
        self._current_roi_boundary_mask: torch.Tensor | None = None
        self._current_legacy_hard_roi_mask: torch.Tensor | None = None
        self._current_roi_core_threshold: torch.Tensor | None = None

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_support_c5h2_deterministic_core_boundary_v1",
                "roi_mask_policy": (
                    "DiffEdit soft roi is generated deterministically per sample; temporal support writes to an "
                    "adaptive hard core, while readout and anchor use only a normalized soft boundary residual"
                ),
                "roi_generation": {
                    "deterministic": True,
                    "cache_root": str(self.roi_cache_root),
                    "seed_offset": self.roi_seed_offset,
                    "soft_roi_source": "cached per-sample DiffEdit semantic guidance map",
                },
                "roi_core_policy": {
                    "formula": (
                        "tau = clamp(max(q_active, peak_ratio * peak), tau_min, tau_max); "
                        "roi_core = 1[roi_soft >= tau]; if core is too small, lower tau to cover a minimum "
                        "active fraction"
                    ),
                    "quantile": self.roi_core_quantile,
                    "peak_ratio": self.roi_core_peak_ratio,
                    "threshold_min": self.roi_core_threshold_min,
                    "threshold_max": self.roi_core_threshold_max,
                    "min_active_ratio": self.roi_core_min_active_ratio,
                    "active_floor": self.roi_core_active_floor,
                },
                "soft_boundary_policy": {
                    "formula": "roi_boundary = normalize(relu(roi_soft * (1 - roi_core)))",
                    "readout": {
                        "start_weight": self.boundary_read_start_weight,
                        "end_weight": self.boundary_read_end_weight,
                    },
                    "anchor": {
                        "start_weight": self.boundary_anchor_start_weight,
                        "end_weight": self.boundary_anchor_end_weight,
                    },
                    "confidence_weight": self.boundary_confidence_weight,
                },
                "adaptive_mask": {
                    "formula": (
                        "M_t = clamp(lerp(S_t, roi_core, c_t) + b_t * roi_boundary, 0, 1), "
                        "where c_t and b_t follow cosine decay"
                    ),
                    "core_read_start_weight": self.core_read_start_weight,
                    "core_read_end_weight": self.core_read_end_weight,
                },
                "background_anchor_policy": {
                    "formula": (
                        "A_t = clamp(roi_core + a_t * roi_boundary, 0, 1); "
                        "R_t = alpha_t * (roi_core + beta * roi_boundary) * sqrt(discrepancy * dynamic_mask) * "
                        "(1 - |mask - dynamic_mask|); "
                        "A'_t = lerp(A_t, 1, R_t)"
                    ),
                    "boundary_anchor_start_weight": self.boundary_anchor_start_weight,
                    "boundary_anchor_end_weight": self.boundary_anchor_end_weight,
                    "boundary_confidence_weight": self.boundary_confidence_weight,
                },
            }
        )
        return payload

    def _core_read_weight(self, step_idx: int, total_steps: int) -> float:
        return self._cosine_schedule(
            self.core_read_start_weight,
            self.core_read_end_weight,
            self._schedule_progress(step_idx, total_steps),
        )

    def _boundary_read_weight(self, step_idx: int, total_steps: int) -> float:
        return self._cosine_schedule(
            self.boundary_read_start_weight,
            self.boundary_read_end_weight,
            self._schedule_progress(step_idx, total_steps),
        )

    def _boundary_anchor_weight(self, step_idx: int, total_steps: int) -> float:
        return self._cosine_schedule(
            self.boundary_anchor_start_weight,
            self.boundary_anchor_end_weight,
            self._schedule_progress(step_idx, total_steps),
        )

    def _build_roi_cache_signature(self) -> str:
        payload = {
            "model_id": self.config.runtime.model_id,
            "image_size": int(self.config.runtime.image_size),
            "num_edit_steps": int(self.config.runtime.num_edit_steps),
            "diffedit": self.diffedit_config.to_dict() if self.diffedit_config is not None else {},
        }
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:16]

    @staticmethod
    def _sample_cache_key(sample: MaterializedSample) -> str:
        payload = {
            "row_index": int(sample.row_index),
            "source_prompt": sample.source_prompt,
            "target_prompt": sample.target_prompt,
            "source_image": sample.source_image_path.name,
        }
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:16]

    def _stable_seed_for_sample(self, sample: MaterializedSample) -> int:
        payload = {
            "row_index": int(sample.row_index),
            "source_prompt": sample.source_prompt,
            "target_prompt": sample.target_prompt,
            "seed_offset": self.roi_seed_offset,
        }
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
        return int(hashlib.sha256(raw).hexdigest()[:8], 16)

    def _roi_cache_dir_for_sample(self, sample: MaterializedSample) -> Path:
        return self.roi_cache_root / self._roi_cache_signature / f"row_{sample.row_index:06d}_{self._sample_cache_key(sample)}"

    @staticmethod
    def _rng_devices_for_pipe_device(device: object) -> list[int]:
        device_obj = torch.device(str(device))
        if device_obj.type != "cuda":
            return []
        index = device_obj.index
        if index is None:
            index = torch.cuda.current_device()
        return [int(index)]

    def _compute_seeded_soft_roi(self, sample: MaterializedSample) -> np.ndarray:
        seed = self._stable_seed_for_sample(sample)
        execution_device = getattr(self.diffedit_pipe, "_execution_device", self.pipe.device)
        with torch.random.fork_rng(devices=self._rng_devices_for_pipe_device(execution_device), enabled=True):
            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(seed)
            soft_mask = super()._generate_diffedit_soft_mask_batch([sample])[0]
        return np.asarray(soft_mask, dtype=np.float32)

    def _load_or_compute_soft_roi(self, sample: MaterializedSample) -> np.ndarray:
        cache_dir = self._roi_cache_dir_for_sample(sample)
        soft_path = cache_dir / "soft_roi.npy"
        if soft_path.exists():
            try:
                cached = np.load(soft_path)
                if cached.ndim == 2:
                    return np.asarray(cached, dtype=np.float32)
            except Exception:
                pass

        soft_mask = self._compute_seeded_soft_roi(sample)
        cache_dir.mkdir(parents=True, exist_ok=True)
        np.save(soft_path, soft_mask.astype(np.float32))
        meta_path = cache_dir / "meta.json"
        meta_path.write_text(
            json.dumps(
                {
                    "row_index": int(sample.row_index),
                    "sample_id": sample.sample_id,
                    "seed": int(self._stable_seed_for_sample(sample)),
                    "cache_signature": self._roi_cache_signature,
                },
                indent=2,
                ensure_ascii=True,
            ),
            encoding="utf-8",
        )
        return soft_mask

    @staticmethod
    def _normalize_boundary(boundary: np.ndarray) -> np.ndarray:
        boundary = np.asarray(boundary, dtype=np.float32)
        peak = float(boundary.max()) if boundary.size else 0.0
        if peak <= 1e-6:
            return np.zeros_like(boundary, dtype=np.float32)
        return (boundary / peak).astype(np.float32)

    def _build_core_boundary_from_soft(self, soft_mask: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
        soft_mask = np.clip(np.asarray(soft_mask, dtype=np.float32), 0.0, 1.0)
        peak = float(soft_mask.max()) if soft_mask.size else 0.0
        if peak <= 1e-6:
            return np.zeros_like(soft_mask, dtype=np.float32), np.zeros_like(soft_mask, dtype=np.float32), 1.0

        active_floor = min(self.roi_core_active_floor, peak)
        active_values = soft_mask[soft_mask >= active_floor]
        if active_values.size == 0:
            active_values = soft_mask[soft_mask > 1e-6]
        if active_values.size == 0:
            return np.zeros_like(soft_mask, dtype=np.float32), np.zeros_like(soft_mask, dtype=np.float32), 1.0

        q_active = float(np.quantile(active_values, self.roi_core_quantile))
        tau = max(
            self.roi_core_threshold_min,
            min(peak, self.roi_core_peak_ratio * peak),
            q_active,
        )
        tau = min(self.roi_core_threshold_max, peak, tau)
        core_mask = (soft_mask >= (tau - 1e-6)).astype(np.float32)

        min_core_pixels = max(1, int(round(active_values.size * self.roi_core_min_active_ratio)))
        current_core_pixels = int(core_mask.sum())
        if current_core_pixels < min_core_pixels:
            sorted_active = np.sort(active_values)
            kth_index = max(0, sorted_active.size - min_core_pixels)
            tau = min(tau, float(sorted_active[kth_index]))
            core_mask = (soft_mask >= (tau - 1e-6)).astype(np.float32)

        boundary_mask = self._normalize_boundary(soft_mask * (1.0 - core_mask))
        return core_mask.astype(np.float32), boundary_mask.astype(np.float32), float(tau)

    def _resolve_roi_core_mask(self, roi_mask: torch.Tensor | None) -> torch.Tensor | None:
        if roi_mask is None or self._current_roi_core_mask is None:
            return roi_mask
        if self._current_roi_core_mask.shape != roi_mask.shape:
            raise ValueError(
                f"roi core mask shape mismatch: expected {tuple(roi_mask.shape)}, got {tuple(self._current_roi_core_mask.shape)}"
            )
        return self._current_roi_core_mask

    def _resolve_roi_boundary_mask(self, roi_mask: torch.Tensor | None) -> torch.Tensor | None:
        if roi_mask is None or self._current_roi_boundary_mask is None:
            return None
        if self._current_roi_boundary_mask.shape != roi_mask.shape:
            raise ValueError(
                "roi boundary mask shape mismatch: "
                f"expected {tuple(roi_mask.shape)}, got {tuple(self._current_roi_boundary_mask.shape)}"
            )
        return self._current_roi_boundary_mask

    @torch.no_grad()
    def _generate_diffedit_roi_batch(self, samples: list[MaterializedSample]) -> torch.Tensor:
        if not samples:
            self._current_soft_roi_mask = None
            self._current_roi_core_mask = None
            self._current_roi_boundary_mask = None
            self._current_legacy_hard_roi_mask = None
            self._current_roi_core_threshold = None
            return torch.zeros((0, 1, 0, 0), device=self.pipe.device, dtype=self.pipe.unet.dtype)

        soft_masks = [self._load_or_compute_soft_roi(sample) for sample in samples]
        core_masks: list[np.ndarray] = []
        boundary_masks: list[np.ndarray] = []
        thresholds: list[float] = []
        for soft_mask in soft_masks:
            core_mask, boundary_mask, tau = self._build_core_boundary_from_soft(soft_mask)
            core_masks.append(core_mask)
            boundary_masks.append(boundary_mask)
            thresholds.append(tau)

        soft_mask_array = np.stack(soft_masks, axis=0).astype(np.float32)
        core_mask_array = np.stack(core_masks, axis=0).astype(np.float32)
        boundary_mask_array = np.stack(boundary_masks, axis=0).astype(np.float32)
        legacy_hard_array = (soft_mask_array > 0.5).astype(np.float32)
        threshold_array = np.asarray(thresholds, dtype=np.float32).reshape(-1, 1, 1, 1)

        device = self.pipe.device
        dtype = self.pipe.unet.dtype
        self._current_soft_roi_mask = torch.from_numpy(soft_mask_array).unsqueeze(1).to(device, dtype=dtype)
        self._current_roi_core_mask = torch.from_numpy(core_mask_array).unsqueeze(1).to(device, dtype=dtype)
        self._current_roi_boundary_mask = torch.from_numpy(boundary_mask_array).unsqueeze(1).to(device, dtype=dtype)
        self._current_legacy_hard_roi_mask = torch.from_numpy(legacy_hard_array).unsqueeze(1).to(device, dtype=dtype)
        self._current_roi_core_threshold = torch.from_numpy(threshold_array).to(device, dtype=dtype)
        return self._current_roi_core_mask

    def _effective_mask_from_support_state(
        self,
        method_name: str,
        support_state: torch.Tensor,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor:
        effective_mask = support_state
        if roi_mask is not None and method_name != "target_only" and self._uses_diffedit_roi_cap(method_name):
            core_mask = self._resolve_roi_core_mask(roi_mask)
            boundary_mask = self._resolve_roi_boundary_mask(roi_mask)
            if core_mask is not None:
                effective_mask = torch.lerp(
                    support_state,
                    core_mask.clamp(0.0, 1.0),
                    self._core_read_weight(step_idx, total_steps),
                )
            if boundary_mask is not None:
                effective_mask = (
                    effective_mask + self._boundary_read_weight(step_idx, total_steps) * boundary_mask.clamp(0.0, 1.0)
                ).clamp(0.0, 1.0)
        if (
            roi_mask is not None
            and method_name != "target_only"
            and self._uses_diffedit_roi_cap(method_name)
            and self._latest_anchor_confidence_context is not None
        ):
            self._cache_anchor_context(
                self._latest_anchor_confidence_context,
                support_state=support_state,
                effective_mask=effective_mask,
                roi_mask=roi_mask,
            )
        return effective_mask

    def _adaptive_anchor_mask(
        self,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor | None:
        if roi_mask is None:
            return None
        core_mask = self._resolve_roi_core_mask(roi_mask)
        boundary_mask = self._resolve_roi_boundary_mask(roi_mask)
        if core_mask is None:
            return roi_mask.clamp(0.0, 1.0)
        anchor_mask = core_mask.clamp(0.0, 1.0)
        if boundary_mask is not None:
            anchor_mask = (
                anchor_mask + self._boundary_anchor_weight(step_idx, total_steps) * boundary_mask.clamp(0.0, 1.0)
            ).clamp(0.0, 1.0)
        return anchor_mask

    def _confidence_anchor_roi_mask(
        self,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor | None:
        if roi_mask is None:
            return None
        core_mask = self._resolve_roi_core_mask(roi_mask)
        boundary_mask = self._resolve_roi_boundary_mask(roi_mask)
        if core_mask is None:
            return roi_mask.clamp(0.0, 1.0)
        confidence_roi_mask = core_mask.clamp(0.0, 1.0)
        if boundary_mask is not None and self.boundary_confidence_weight > 0.0:
            confidence_roi_mask = (
                confidence_roi_mask + self.boundary_confidence_weight * boundary_mask.clamp(0.0, 1.0)
            ).clamp(0.0, 1.0)
        return confidence_roi_mask

    def _finalize_step_aux_tensor(
        self,
        method_name: str,
        aux_tensor: dict[str, torch.Tensor],
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> dict[str, torch.Tensor]:
        aux_tensor = super()._finalize_step_aux_tensor(method_name, aux_tensor, roi_mask, step_idx, total_steps)
        if roi_mask is None or method_name == "target_only" or not self._uses_diffedit_roi_cap(method_name):
            return aux_tensor
        core_mask = self._resolve_roi_core_mask(roi_mask)
        boundary_mask = self._resolve_roi_boundary_mask(roi_mask)
        if core_mask is not None:
            aux_tensor["roi_core_mask"] = core_mask
            aux_tensor["hard_roi_mask"] = core_mask
        if self._current_soft_roi_mask is not None:
            aux_tensor["soft_roi_mask"] = self._current_soft_roi_mask
        if boundary_mask is not None:
            aux_tensor["roi_boundary_mask"] = boundary_mask
        if self._current_legacy_hard_roi_mask is not None:
            aux_tensor["legacy_hard_roi_mask"] = self._current_legacy_hard_roi_mask
        if self._current_roi_core_threshold is not None:
            aux_tensor["roi_core_threshold"] = self._current_roi_core_threshold.expand_as(roi_mask)
        aux_tensor["core_read_weight"] = torch.full_like(roi_mask, self._core_read_weight(step_idx, total_steps))
        aux_tensor["boundary_read_weight"] = torch.full_like(roi_mask, self._boundary_read_weight(step_idx, total_steps))
        aux_tensor["boundary_anchor_weight"] = torch.full_like(
            roi_mask,
            self._boundary_anchor_weight(step_idx, total_steps),
        )
        aux_tensor["boundary_confidence_weight"] = torch.full_like(roi_mask, self.boundary_confidence_weight)
        return aux_tensor
