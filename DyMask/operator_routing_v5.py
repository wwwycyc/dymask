from __future__ import annotations

from dataclasses import dataclass

import torch

from .operator_routing_v2 import build_soft_role_priors, build_stabilize_eps


def _normalize_tensor_map(tensor: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
    min_value = tensor.amin(dim=(-2, -1), keepdim=True)
    max_value = tensor.amax(dim=(-2, -1), keepdim=True)
    return (tensor - min_value) / (max_value - min_value).clamp(min=eps)


def _normalize_tensor_map_with_mask(
    tensor: torch.Tensor,
    mask: torch.Tensor,
    eps: float = 1e-6,
) -> torch.Tensor:
    if tensor.shape != mask.shape:
        raise ValueError(
            f"masked normalization expects matching shapes, got {tuple(tensor.shape)} and {tuple(mask.shape)}"
        )

    normalized = torch.zeros_like(tensor)
    batch_size = int(tensor.shape[0])
    for batch_idx in range(batch_size):
        values = tensor[batch_idx]
        support = mask[batch_idx] > 0.0
        if bool(support.any().item()):
            selected = values[support]
            min_value = selected.min()
            max_value = selected.max()
            normalized[batch_idx] = (values - min_value) / (max_value - min_value).clamp(min=eps)
        else:
            normalized[batch_idx] = _normalize_tensor_map(values.unsqueeze(0), eps=eps).squeeze(0)
    return torch.clamp(normalized, 0.0, 1.0)


@dataclass(frozen=True)
class OperatorRoutingV5Config:
    interiority_bias: float = 1.0
    boundary_rewrite_bias: float = 1.0
    boundary_stabilize_bias: float = 1.0
    relative_update_power: float = 1.0
    trajectory_consistency_power: float = 1.0


def build_relative_update_demand_field_v5(
    eps_src: torch.Tensor,
    eps_tar: torch.Tensor,
    roi_mask: torch.Tensor,
) -> torch.Tensor:
    residual = (eps_tar - eps_src).abs().mean(dim=1, keepdim=True)
    reference_scale = 0.5 * (
        eps_src.abs().mean(dim=1, keepdim=True) + eps_tar.abs().mean(dim=1, keepdim=True)
    )
    relative_residual = residual / reference_scale.clamp(min=1e-6)
    return _normalize_tensor_map_with_mask(relative_residual, roi_mask)


def build_operator_routing_v5_state(
    transformation_field: torch.Tensor,
    latent_drift: torch.Tensor,
    roi_mask: torch.Tensor,
    config: OperatorRoutingV5Config,
) -> dict[str, torch.Tensor]:
    priors = build_soft_role_priors(roi_mask)
    roi = priors["roi"]
    interiority = priors["interiority"]
    transform = torch.clamp(transformation_field, 0.0, 1.0)
    drift = _normalize_tensor_map_with_mask(torch.clamp(latent_drift, 0.0, 1.0), roi)
    trajectory_consistency = torch.clamp(1.0 - drift, 0.0, 1.0) * roi
    core_rewrite = roi * transform * (1.0 + float(config.interiority_bias) * interiority)
    return {
        **priors,
        "transformation_field": transform,
        "trajectory_consistency": trajectory_consistency,
        "core_rewrite_field": torch.clamp(core_rewrite, 0.0, 1.0),
    }


def apply_operator_routing_v5_eps(
    eps_src: torch.Tensor,
    eps_tar: torch.Tensor,
    routing_state: dict[str, torch.Tensor],
    config: OperatorRoutingV5Config,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    roi = routing_state["roi"]
    boundaryness = routing_state["boundaryness"]
    transform = routing_state["transformation_field"]
    trajectory_consistency = routing_state["trajectory_consistency"]
    core_rewrite = routing_state["core_rewrite_field"]

    relative_update = build_relative_update_demand_field_v5(
        eps_src=eps_src,
        eps_tar=eps_tar,
        roi_mask=roi,
    )
    update_power = float(config.relative_update_power)
    consistency_power = float(config.trajectory_consistency_power)
    if update_power != 1.0:
        relative_update = torch.pow(relative_update, update_power)
    if consistency_power != 1.0:
        trajectory_consistency = torch.pow(trajectory_consistency, consistency_power)

    boundary_rewrite = (
        roi
        * boundaryness
        * torch.sqrt(torch.clamp(transform * relative_update, 0.0, 1.0))
        * float(config.boundary_rewrite_bias)
    )
    boundary_stabilize = (
        roi
        * boundaryness
        * torch.sqrt(torch.clamp(trajectory_consistency * (1.0 - relative_update), 0.0, 1.0))
        * float(config.boundary_stabilize_bias)
    )

    rewrite_raw = torch.clamp(core_rewrite + boundary_rewrite, 0.0, None)
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
        source_consistency=trajectory_consistency,
    )
    inside_eps = rewrite_weight * eps_tar + stabilize_weight * stabilize_eps
    eps = (1.0 - roi) * eps_src + roi * inside_eps
    aux = {
        **routing_state,
        "relative_update_demand": relative_update,
        "boundary_rewrite_field": torch.clamp(boundary_rewrite, 0.0, 1.0),
        "boundary_stabilize_field": torch.clamp(boundary_stabilize, 0.0, 1.0),
        "rewrite_weight": rewrite_weight,
        "stabilize_weight": stabilize_weight,
    }
    return eps, aux
