from __future__ import annotations

from dataclasses import dataclass

import torch


@dataclass(frozen=True)
class BoundaryStabilizationFieldV8Config:
    eps: float = 1e-6


def build_boundary_stabilization_field_v8(
    boundaryness: torch.Tensor,
    transformation_field: torch.Tensor,
    source_consistency: torch.Tensor,
    config: BoundaryStabilizationFieldV8Config,
) -> torch.Tensor:
    boundary_term = torch.clamp(boundaryness, 0.0, 1.0)
    transform_term = torch.clamp(transformation_field, 0.0, 1.0)
    consistency_term = torch.clamp(source_consistency, 0.0, 1.0)
    joint_tension = (transform_term * consistency_term) / (
        transform_term + consistency_term + float(config.eps)
    )
    field = boundary_term * joint_tension
    return torch.clamp(torch.nan_to_num(field, nan=0.0, posinf=1.0, neginf=0.0), 0.0, 1.0)
