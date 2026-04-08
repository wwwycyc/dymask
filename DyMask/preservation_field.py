from __future__ import annotations

from dataclasses import dataclass

import torch


@dataclass(frozen=True)
class PreservationFieldConfig:
    latent_weight: float = 1.0


def build_source_consistency_field(latent_drift: torch.Tensor) -> torch.Tensor:
    return torch.clamp(1.0 - latent_drift, 0.0, 1.0)


def build_preservation_field(
    latent_drift: torch.Tensor,
    config: PreservationFieldConfig,
) -> torch.Tensor:
    if float(config.latent_weight) <= 0.0:
        return torch.zeros_like(latent_drift)
    return torch.clamp(float(config.latent_weight) * latent_drift, 0.0, 1.0)
