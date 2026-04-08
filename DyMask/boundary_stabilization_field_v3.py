from __future__ import annotations

from dataclasses import dataclass

import torch

from .operator_routing_v2 import build_soft_role_priors


@dataclass(frozen=True)
class BoundaryStabilizationFieldV3Config:
    transform_gate_power: float = 1.0


def build_boundary_stabilization_field_v3(
    roi_mask: torch.Tensor,
    transformation_field: torch.Tensor,
    source_consistency: torch.Tensor,
    config: BoundaryStabilizationFieldV3Config,
) -> dict[str, torch.Tensor]:
    priors = build_soft_role_priors(roi_mask)
    roi = priors["roi"]
    boundaryness = priors["boundaryness"]
    transform_gate = torch.clamp(1.0 - transformation_field, 0.0, 1.0)
    gate_power = float(config.transform_gate_power)
    if gate_power != 1.0:
        transform_gate = torch.pow(transform_gate, gate_power)
    boundary_stabilize = roi * boundaryness * torch.clamp(source_consistency, 0.0, 1.0) * transform_gate
    return {
        **priors,
        "boundary_stabilize_field": torch.clamp(boundary_stabilize, 0.0, 1.0),
    }
