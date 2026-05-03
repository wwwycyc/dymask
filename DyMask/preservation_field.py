from __future__ import annotations

from dataclasses import dataclass

import torch


@dataclass(frozen=True)
class PreservationFieldConfig:
    latent_weight: float = 1.0
    use_transform_gate: bool = False
    transform_gate_power: float = 1.0


def build_source_consistency_field(latent_drift: torch.Tensor) -> torch.Tensor:
    return torch.clamp(1.0 - latent_drift, 0.0, 1.0)


def build_preservation_field(
    latent_drift: torch.Tensor,
    config: PreservationFieldConfig,
    transformation_field: torch.Tensor | None = None,
) -> torch.Tensor:
    if float(config.latent_weight) <= 0.0:
        return torch.zeros_like(latent_drift)
    preservation = torch.clamp(float(config.latent_weight) * latent_drift, 0.0, 1.0)
    if config.use_transform_gate and transformation_field is not None:
        transform_gate = torch.clamp(1.0 - transformation_field, 0.0, 1.0)
        gate_power = float(config.transform_gate_power)
        if gate_power != 1.0:
            transform_gate = torch.pow(transform_gate, gate_power)
        preservation = preservation * transform_gate
    return torch.clamp(preservation, 0.0, 1.0)
