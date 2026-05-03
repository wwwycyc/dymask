from __future__ import annotations

from dataclasses import dataclass

import torch


@dataclass(frozen=True)
class TransformationFieldConfig:
    discrepancy_weight: float = 1.0
    attention_weight: float = 1.0


def build_transformation_field(
    discrepancy: torch.Tensor,
    attention: torch.Tensor,
    config: TransformationFieldConfig,
) -> torch.Tensor:
    weight_sum = float(config.discrepancy_weight + config.attention_weight)
    if weight_sum <= 0.0:
        raise ValueError("transformation field requires a positive total weight")
    field = (
        float(config.discrepancy_weight) * discrepancy
        + float(config.attention_weight) * attention
    ) / weight_sum
    return torch.clamp(field, 0.0, 1.0)
