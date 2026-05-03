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
CHANNEL_SOURCES = (
    "residual_abs",
    "target_noise_abs",
)


@dataclass
class AdaptiveRoiResidualGainConfig:
    enabled: bool = True
    enable_spatial_gain: bool = True
    enable_channel_gain: bool = True
    enable_temporal_basis: bool = False
    basis_rho: float = 0.85
    enable_temporal_channel: bool = False
    channel_rho: float = 0.85
    enable_core_shell: bool = False
    core_erosion_kernel: int = 3
    shell_scale: float = 1.0
    source: str = "hybrid"
    start_ratio: float = 0.20
    end_ratio: float = 0.90
    temporal_power: float = 1.5
    threshold: float = 0.45
    temperature: float = 8.0
    smoothing_kernel: int = 3
    min_scale: float = 1.0
    max_scale: float = 1.45
    discrepancy_weight: float = 1.0
    attention_weight: float = 0.75
    latent_drift_weight: float = -0.25
    channel_source: str = "residual_abs"
    channel_strength: float = 0.20
    channel_temperature: float = 6.0

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class AdaptiveRoiResidualGainBuilder:
    def __init__(self, config: AdaptiveRoiResidualGainConfig) -> None:
        self.config = config
        self._validate_source(config.source)
        self._validate_channel_source(config.channel_source)

    @staticmethod
    def _validate_source(source: str) -> None:
        if source not in FIELD_SOURCES:
            raise ValueError(f"Unsupported field source: {source!r}")

    @staticmethod
    def _validate_channel_source(source: str) -> None:
        if source not in CHANNEL_SOURCES:
            raise ValueError(f"Unsupported channel source: {source!r}")

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
            discrepancy_weight=self.config.discrepancy_weight,
            attention_weight=self.config.attention_weight,
            latent_drift_weight=self.config.latent_drift_weight,
        )

    @staticmethod
    def _update_running_state(
        previous_state: torch.Tensor | None,
        current_value: torch.Tensor,
        rho: float,
    ) -> torch.Tensor:
        if previous_state is None or previous_state.shape != current_value.shape:
            return current_value
        return float(rho) * previous_state + (1.0 - float(rho)) * current_value

    def _temporal_gate(self, step_idx: int, total_steps: int) -> float:
        total_steps = max(1, int(total_steps))
        step_position = float(step_idx) / max(1, total_steps - 1)
        start_ratio = float(self.config.start_ratio)
        end_ratio = float(self.config.end_ratio)
        if not self.config.enabled or step_position < start_ratio or step_position > end_ratio:
            return 0.0
        span = max(1e-6, end_ratio - start_ratio)
        progress = (step_position - start_ratio) / span
        progress = min(max(progress, 0.0), 1.0)
        return float(progress ** float(self.config.temporal_power))

    @staticmethod
    def _erode_mask(mask: torch.Tensor, kernel_size: int) -> torch.Tensor:
        kernel = max(1, int(kernel_size))
        if kernel <= 1:
            return torch.clamp(mask, min=0.0, max=1.0)
        if kernel % 2 == 0:
            kernel += 1
        inverted = 1.0 - torch.clamp(mask, min=0.0, max=1.0)
        eroded = 1.0 - F.max_pool2d(inverted, kernel_size=kernel, stride=1, padding=kernel // 2)
        return torch.clamp(eroded, min=0.0, max=1.0)

    def split_core_shell(self, roi_mask: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        roi_mask = torch.clamp(roi_mask, min=0.0, max=1.0)
        if not self.config.enable_core_shell:
            return roi_mask, torch.zeros_like(roi_mask)

        core_mask = self._erode_mask(roi_mask, self.config.core_erosion_kernel)
        shell_mask = torch.clamp(roi_mask - core_mask, min=0.0, max=1.0)
        empty_core = core_mask.flatten(1).sum(dim=1) <= 1e-6
        if empty_core.any():
            selector = empty_core[:, None, None, None]
            core_mask = torch.where(selector, roi_mask, core_mask)
            shell_mask = torch.where(selector, torch.zeros_like(shell_mask), shell_mask)
        return core_mask, shell_mask

    @staticmethod
    def _masked_channel_mean(values: torch.Tensor, roi_mask: torch.Tensor) -> torch.Tensor:
        weights = roi_mask.expand_as(values)
        numerator = (values * weights).flatten(2).sum(dim=-1)
        denominator = weights.flatten(2).sum(dim=-1).clamp(min=1e-6)
        return numerator / denominator

    def _build_channel_descriptor(
        self,
        residual: torch.Tensor,
        target_noise: torch.Tensor,
        roi_mask: torch.Tensor,
        previous_channel_state: torch.Tensor | None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        if self.config.channel_source == "target_noise_abs":
            channel_source = target_noise.abs()
        else:
            channel_source = residual.abs()

        pooled = self._masked_channel_mean(channel_source, roi_mask)
        if self.config.enable_temporal_channel:
            channel_state = self._update_running_state(previous_channel_state, pooled, self.config.channel_rho)
        else:
            channel_state = pooled
        return pooled, channel_state

    def _build_channel_gain_from_state(
        self,
        channel_state: torch.Tensor,
        temporal_gate: float,
        residual: torch.Tensor,
    ) -> torch.Tensor:
        if float(self.config.channel_strength) <= 0.0 or temporal_gate <= 0.0:
            return torch.ones_like(residual[:, :, :1, :1])

        channel_min = channel_state.amin(dim=1, keepdim=True)
        channel_max = channel_state.amax(dim=1, keepdim=True)
        normalized = (channel_state - channel_min) / (channel_max - channel_min).clamp(min=1e-6)
        channel_gate = torch.sigmoid((normalized - 0.5) * float(self.config.channel_temperature))
        return 1.0 + temporal_gate * float(self.config.channel_strength) * channel_gate[:, :, None, None]

    def build(
        self,
        dynamic_mask: torch.Tensor,
        discrepancy: torch.Tensor,
        attention: torch.Tensor,
        latent_drift: torch.Tensor,
        residual: torch.Tensor,
        target_noise: torch.Tensor,
        roi_mask: torch.Tensor,
        step_idx: int,
        total_steps: int,
        previous_basis_state: torch.Tensor | None = None,
        previous_channel_state: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        basis = self._resolve_source_map(
            source=self.config.source,
            dynamic_mask=dynamic_mask,
            discrepancy=discrepancy,
            attention=attention,
            latent_drift=latent_drift,
        )
        basis = self._smooth_map(basis, self.config.smoothing_kernel)
        if self.config.enable_temporal_basis:
            basis_state = self._update_running_state(previous_basis_state, basis, self.config.basis_rho)
        else:
            basis_state = basis

        _channel_descriptor, channel_state = self._build_channel_descriptor(
            residual=residual,
            target_noise=target_noise,
            roi_mask=roi_mask,
            previous_channel_state=previous_channel_state,
        )

        temporal_gate = self._temporal_gate(step_idx=step_idx, total_steps=total_steps)
        if temporal_gate <= 0.0:
            spatial_gain = torch.full_like(dynamic_mask, float(self.config.min_scale))
            channel_gain = torch.ones_like(residual[:, :, :1, :1])
            return basis, basis_state, spatial_gain, channel_gain, channel_state

        activated = torch.sigmoid((basis_state - float(self.config.threshold)) * float(self.config.temperature))
        if self.config.enable_spatial_gain:
            spatial_gain = float(self.config.min_scale) + temporal_gate * (float(self.config.max_scale) - float(self.config.min_scale)) * activated
        else:
            spatial_gain = torch.full_like(dynamic_mask, float(self.config.min_scale))

        if self.config.enable_channel_gain:
            channel_gain = self._build_channel_gain_from_state(
                channel_state=channel_state,
                temporal_gate=temporal_gate,
                residual=residual,
            ).to(device=residual.device, dtype=residual.dtype)
        else:
            channel_gain = torch.ones_like(residual[:, :, :1, :1])

        return basis, basis_state, spatial_gain.to(device=dynamic_mask.device, dtype=dynamic_mask.dtype), channel_gain, channel_state
