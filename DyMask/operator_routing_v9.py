from __future__ import annotations

from dataclasses import dataclass

import torch

from .boundary_stabilization_field_v8 import (
    BoundaryStabilizationFieldV8Config,
    build_boundary_stabilization_field_v8,
)
from .operator_routing_v2 import build_soft_role_priors, build_stabilize_eps


@dataclass(frozen=True)
class OperatorRoutingV9Config:
    boundary_field: BoundaryStabilizationFieldV8Config = BoundaryStabilizationFieldV8Config()
    core_rewrite_max_gain: float = 0.75


def _safe_unit_interval(tensor: torch.Tensor) -> torch.Tensor:
    return torch.clamp(torch.nan_to_num(tensor, nan=0.0, posinf=1.0, neginf=0.0), 0.0, 1.0)


def build_operator_routing_v9_state(
    transformation_field: torch.Tensor,
    source_consistency: torch.Tensor,
    roi_mask: torch.Tensor,
    config: OperatorRoutingV9Config,
) -> dict[str, torch.Tensor]:
    priors = build_soft_role_priors(roi_mask)
    roi = priors["roi"]
    interiority = _safe_unit_interval(priors["interiority"]) * roi
    boundaryness = _safe_unit_interval(priors["boundaryness"]) * roi
    transform = _safe_unit_interval(transformation_field) * roi
    consistency = _safe_unit_interval(source_consistency) * roi

    stabilize_field = build_boundary_stabilization_field_v8(
        boundaryness=boundaryness,
        transformation_field=transform,
        source_consistency=consistency,
        config=config.boundary_field,
    ) * roi
    core_rewrite_gain = float(config.core_rewrite_max_gain) * interiority * transform
    core_rewrite_gain = torch.clamp(core_rewrite_gain, 0.0, float(config.core_rewrite_max_gain)) * roi
    rewrite_field = torch.clamp(roi + core_rewrite_gain - stabilize_field, 0.0, 1.0)

    return {
        **priors,
        "roi": roi,
        "interiority": interiority,
        "boundaryness": boundaryness,
        "transformation_field": transform,
        "source_consistency": consistency,
        "boundary_stabilize_field": stabilize_field,
        "core_rewrite_gain_field": core_rewrite_gain,
        "rewrite_field": rewrite_field,
    }


def apply_operator_routing_v9_eps(
    eps_src: torch.Tensor,
    eps_tar: torch.Tensor,
    routing_state: dict[str, torch.Tensor],
) -> torch.Tensor:
    roi = routing_state["roi"]
    core_rewrite_gain = routing_state["core_rewrite_gain_field"]
    stabilize_field = routing_state["boundary_stabilize_field"]

    boosted_rewrite_eps = eps_tar + core_rewrite_gain * (eps_tar - eps_src)
    stabilize_eps = build_stabilize_eps(
        eps_src=eps_src,
        eps_tar=eps_tar,
        transformation_field=routing_state["transformation_field"],
        source_consistency=routing_state["source_consistency"],
    )
    inside_eps = boosted_rewrite_eps + stabilize_field * (stabilize_eps - boosted_rewrite_eps)
    eps = (1.0 - roi) * eps_src + roi * inside_eps
    return torch.nan_to_num(eps, nan=0.0, posinf=0.0, neginf=0.0)
