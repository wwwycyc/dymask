from __future__ import annotations

from dataclasses import dataclass

import torch

from .boundary_stabilization_field_v3 import (
    BoundaryStabilizationFieldV3Config,
    build_boundary_stabilization_field_v3,
)
from .operator_routing_v2 import build_stabilize_eps


@dataclass(frozen=True)
class OperatorRoutingV3Config:
    boundary_stabilization: BoundaryStabilizationFieldV3Config = BoundaryStabilizationFieldV3Config()


def build_operator_routing_v3_state(
    transformation_field: torch.Tensor,
    source_consistency: torch.Tensor,
    roi_mask: torch.Tensor,
    config: OperatorRoutingV3Config,
) -> dict[str, torch.Tensor]:
    state = build_boundary_stabilization_field_v3(
        roi_mask=roi_mask,
        transformation_field=transformation_field,
        source_consistency=source_consistency,
        config=config.boundary_stabilization,
    )
    roi = state["roi"]
    stabilize_weight = state["boundary_stabilize_field"]
    rewrite_weight = torch.clamp(roi - stabilize_weight, 0.0, 1.0)
    return {
        **state,
        "transformation_field": torch.clamp(transformation_field, 0.0, 1.0),
        "source_consistency": torch.clamp(source_consistency, 0.0, 1.0),
        "rewrite_weight": rewrite_weight,
        "stabilize_weight": stabilize_weight,
    }


def apply_operator_routing_v3_eps(
    eps_src: torch.Tensor,
    eps_tar: torch.Tensor,
    routing_state: dict[str, torch.Tensor],
) -> torch.Tensor:
    roi = routing_state["roi"]
    rewrite_weight = routing_state["rewrite_weight"]
    stabilize_weight = routing_state["stabilize_weight"]
    stabilize_eps = build_stabilize_eps(
        eps_src=eps_src,
        eps_tar=eps_tar,
        transformation_field=routing_state["transformation_field"],
        source_consistency=routing_state["source_consistency"],
    )
    inside_eps = rewrite_weight * eps_tar + stabilize_weight * stabilize_eps
    return (1.0 - roi) * eps_src + roi * inside_eps
