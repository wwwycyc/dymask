from __future__ import annotations

from dataclasses import dataclass

import torch


def _normalize_tensor_map(tensor: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
    min_value = tensor.amin(dim=(-2, -1), keepdim=True)
    max_value = tensor.amax(dim=(-2, -1), keepdim=True)
    return (tensor - min_value) / (max_value - min_value).clamp(min=eps)


@dataclass(frozen=True)
class TransformationFieldV2Config:
    discrepancy_weight: float = 1.0
    attention_weight: float = 1.0


def build_transformation_field_v2(
    discrepancy: torch.Tensor,
    attention: torch.Tensor,
    config: TransformationFieldV2Config,
) -> torch.Tensor:
    weight_sum = float(config.discrepancy_weight + config.attention_weight)
    if weight_sum <= 0.0:
        raise ValueError("transformation field requires a positive total weight")
    field = (
        float(config.discrepancy_weight) * discrepancy
        + float(config.attention_weight) * attention
    ) / weight_sum
    return torch.clamp(_normalize_tensor_map(field), 0.0, 1.0)
