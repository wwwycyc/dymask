from __future__ import annotations

from dataclasses import asdict, dataclass

import torch
import torch.nn.functional as F


FIELD_SOURCES = (
    "dynamic_mask",
    "complement_dynamic_mask",
    "discrepancy",
    "attention",
    "latent_drift",
    "hybrid",
)


@dataclass
class RoiEditGainFieldConfig:
    enabled: bool = True
    source: str = "dynamic_mask"
    start_ratio: float = 0.25
    end_ratio: float = 0.85
    threshold: float = 0.50
    temperature: float = 8.0
    smoothing_kernel: int = 1
    min_scale: float = 1.0
    max_scale: float = 1.35
    discrepancy_weight: float = 1.0
    attention_weight: float = 0.5
    latent_drift_weight: float = -0.5

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class RoiEditGainFieldBuilder:
    """Build an ROI-local positive edit-gain field for inference-time ablations."""

    def __init__(self, config: RoiEditGainFieldConfig) -> None:
        self.config = config
        self._validate_source(config.source)

    @staticmethod
    def _validate_source(source: str) -> None:
        if source not in FIELD_SOURCES:
            raise ValueError(f"Unsupported field source: {source!r}")

    @staticmethod
    def _step_window_active(start_ratio: float, end_ratio: float, step_idx: int, total_steps: int) -> bool:
        total_steps = max(1, int(total_steps))
        start_step = int(float(start_ratio) * total_steps)
        end_step = int(float(end_ratio) * total_steps)
        return start_step <= int(step_idx) < max(start_step + 1, end_step)

    @staticmethod
    def _smooth_map(source_map: torch.Tensor, kernel_size: int) -> torch.Tensor:
        kernel = max(1, int(kernel_size))
        if kernel <= 1:
            return source_map
        if kernel % 2 == 0:
            kernel += 1
        padding = kernel // 2
        return F.avg_pool2d(source_map, kernel_size=kernel, stride=1, padding=padding)

    @staticmethod
    def _resolve_hybrid_source(
        discrepancy: torch.Tensor,
        attention: torch.Tensor,
        latent_drift: torch.Tensor,
        discrepancy_weight: float,
        attention_weight: float,
        latent_drift_weight: float,
    ) -> torch.Tensor:
        normalizer = abs(float(discrepancy_weight)) + abs(float(attention_weight)) + abs(float(latent_drift_weight))
        if normalizer <= 1e-6:
            return torch.zeros_like(discrepancy)
        raw = (
            float(discrepancy_weight) * discrepancy
            + float(attention_weight) * attention
            + float(latent_drift_weight) * latent_drift
        ) / normalizer
        return torch.clamp(0.5 * (raw + 1.0), min=0.0, max=1.0)

    def _resolve_source_map(
        self,
        source: str,
        dynamic_mask: torch.Tensor,
        discrepancy: torch.Tensor,
        attention: torch.Tensor,
        latent_drift: torch.Tensor,
        discrepancy_weight: float,
        attention_weight: float,
        latent_drift_weight: float,
    ) -> torch.Tensor:
        if source == "dynamic_mask":
            return torch.clamp(dynamic_mask, min=0.0, max=1.0)
        if source == "complement_dynamic_mask":
            return torch.clamp(1.0 - dynamic_mask, min=0.0, max=1.0)
        if source == "discrepancy":
            return torch.clamp(discrepancy, min=0.0, max=1.0)
        if source == "attention":
            return torch.clamp(attention, min=0.0, max=1.0)
        if source == "latent_drift":
            return torch.clamp(latent_drift, min=0.0, max=1.0)
        return self._resolve_hybrid_source(
            discrepancy=discrepancy,
            attention=attention,
            latent_drift=latent_drift,
            discrepancy_weight=discrepancy_weight,
            attention_weight=attention_weight,
            latent_drift_weight=latent_drift_weight,
        )

    def build(
        self,
        dynamic_mask: torch.Tensor,
        discrepancy: torch.Tensor,
        attention: torch.Tensor,
        latent_drift: torch.Tensor,
        step_idx: int,
        total_steps: int,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        config = self.config
        basis = self._resolve_source_map(
            source=config.source,
            dynamic_mask=dynamic_mask,
            discrepancy=discrepancy,
            attention=attention,
            latent_drift=latent_drift,
            discrepancy_weight=config.discrepancy_weight,
            attention_weight=config.attention_weight,
            latent_drift_weight=config.latent_drift_weight,
        )
        basis = self._smooth_map(basis, config.smoothing_kernel)
        if not config.enabled or not self._step_window_active(config.start_ratio, config.end_ratio, step_idx, total_steps):
            return basis, torch.ones_like(dynamic_mask)

        activated = torch.sigmoid((basis - float(config.threshold)) * float(config.temperature))
        gain = float(config.min_scale) + (float(config.max_scale) - float(config.min_scale)) * activated
        return basis, gain.to(device=dynamic_mask.device, dtype=dynamic_mask.dtype)
