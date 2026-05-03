from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.nn.functional as F

from .operator_routing_v2 import build_soft_role_priors, build_stabilize_eps


@dataclass(frozen=True)
class OperatorRoutingV4Config:
    interiority_bias: float = 1.0
    boundary_rewrite_bias: float = 1.0
    boundary_stabilize_bias: float = 1.0


def build_source_target_agreement_field_v4(
    eps_src: torch.Tensor,
    eps_tar: torch.Tensor,
) -> torch.Tensor:
    agreement = F.cosine_similarity(eps_src, eps_tar, dim=1, eps=1e-8).unsqueeze(1)
    return torch.clamp((agreement + 1.0) * 0.5, 0.0, 1.0)


def build_operator_routing_v4_state(
    transformation_field: torch.Tensor,
    roi_mask: torch.Tensor,
    config: OperatorRoutingV4Config,
) -> dict[str, torch.Tensor]:
    priors = build_soft_role_priors(roi_mask)
    roi = priors["roi"]
    interiority = priors["interiority"]
    boundaryness = priors["boundaryness"]
    transform = torch.clamp(transformation_field, 0.0, 1.0)

    core_field = roi * transform * (
        1.0 + float(config.interiority_bias) * interiority
    )
    return {
        **priors,
        "transformation_field": transform,
        "core_field": torch.clamp(core_field, 0.0, 1.0),
    }


def apply_operator_routing_v4_eps(
    eps_src: torch.Tensor,
    eps_tar: torch.Tensor,
    routing_state: dict[str, torch.Tensor],
    config: OperatorRoutingV4Config,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    roi = routing_state["roi"]
    boundaryness = routing_state["boundaryness"]
    core_field = routing_state["core_field"]
    transform = routing_state["transformation_field"]
    agreement = build_source_target_agreement_field_v4(eps_src=eps_src, eps_tar=eps_tar)

    boundary_rewrite = roi * boundaryness * transform * (1.0 - agreement) * float(config.boundary_rewrite_bias)
    boundary_stabilize = roi * boundaryness * agreement * float(config.boundary_stabilize_bias)
    rewrite_raw = torch.clamp(core_field + boundary_rewrite, 0.0, None)
    stabilize_raw = torch.clamp(boundary_stabilize, 0.0, None)
    total = rewrite_raw + stabilize_raw
    safe_total = total.clamp(min=1e-8)
    rewrite_weight = torch.where(roi > 0.0, rewrite_raw / safe_total, torch.zeros_like(roi))
    stabilize_weight = torch.where(roi > 0.0, stabilize_raw / safe_total, torch.zeros_like(roi))
    zero_total = (total <= 1e-8) & (roi > 0.0)
    rewrite_weight = torch.where(zero_total, torch.ones_like(rewrite_weight), rewrite_weight)
    stabilize_weight = torch.where(zero_total, torch.zeros_like(stabilize_weight), stabilize_weight)

    stabilize_eps = build_stabilize_eps(
        eps_src=eps_src,
        eps_tar=eps_tar,
        transformation_field=transform,
        source_consistency=agreement,
    )
    inside_eps = rewrite_weight * eps_tar + stabilize_weight * stabilize_eps
    eps = (1.0 - roi) * eps_src + roi * inside_eps
    aux = {
        **routing_state,
        "source_target_agreement": agreement,
        "boundary_rewrite_field": torch.clamp(boundary_rewrite, 0.0, 1.0),
        "boundary_stabilize_field": torch.clamp(boundary_stabilize, 0.0, 1.0),
        "rewrite_weight": rewrite_weight,
        "stabilize_weight": stabilize_weight,
    }
    return eps, aux
