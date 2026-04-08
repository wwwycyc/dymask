from __future__ import annotations

from dataclasses import dataclass

import torch


def _normalize_tensor_map(tensor: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
    min_value = tensor.amin(dim=(-2, -1), keepdim=True)
    max_value = tensor.amax(dim=(-2, -1), keepdim=True)
    return (tensor - min_value) / (max_value - min_value).clamp(min=eps)


@dataclass(frozen=True)
class PreservationFieldV2Config:
    transform_gate_power: float = 1.0


def build_source_consistency_field_v2(latent_drift: torch.Tensor) -> torch.Tensor:
    return torch.clamp(1.0 - latent_drift, 0.0, 1.0)


def build_preservation_field_v2(
    latent_drift: torch.Tensor,
    transformation_field: torch.Tensor,
    config: PreservationFieldV2Config,
) -> torch.Tensor:
    source_consistency = build_source_consistency_field_v2(latent_drift)
    transform_gate = torch.clamp(1.0 - transformation_field, 0.0, 1.0)
    gate_power = float(config.transform_gate_power)
    if gate_power != 1.0:
        transform_gate = torch.pow(transform_gate, gate_power)
    preservation = source_consistency * transform_gate
    return torch.clamp(_normalize_tensor_map(preservation), 0.0, 1.0)
