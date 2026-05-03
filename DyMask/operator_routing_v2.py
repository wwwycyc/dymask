from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.nn.functional as F


def _normalize_tensor_map(tensor: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
    min_value = tensor.amin(dim=(-2, -1), keepdim=True)
    max_value = tensor.amax(dim=(-2, -1), keepdim=True)
    return (tensor - min_value) / (max_value - min_value).clamp(min=eps)


def _erode_mask(mask: torch.Tensor, kernel_size: int = 3) -> torch.Tensor:
    padding = kernel_size // 2
    eroded = 1.0 - F.max_pool2d(1.0 - mask, kernel_size=kernel_size, stride=1, padding=padding)
    return torch.clamp(eroded, 0.0, 1.0)


@dataclass(frozen=True)
class OperatorRoutingV2Config:
    interiority_bias: float = 1.0
    boundary_bias: float = 1.0
    use_stabilize_operator: bool = True


def build_soft_role_priors(roi_mask: torch.Tensor) -> dict[str, torch.Tensor]:
    roi = (roi_mask > 0.5).to(dtype=roi_mask.dtype, device=roi_mask.device)
    current = roi
    shell_depth = torch.zeros_like(roi)
    step = 0
    max_steps = max(int(roi.shape[-2]), int(roi.shape[-1]))

    while step < max_steps and bool((current > 0.0).any().item()):
        eroded = _erode_mask(current, kernel_size=3)
        shell = torch.clamp(current - eroded, 0.0, 1.0)
        shell_depth = shell_depth + shell * float(step)
        current = eroded
        step += 1

    max_depth = shell_depth.amax(dim=(-2, -1), keepdim=True)
    interiority = torch.where(
        max_depth > 0.0,
        shell_depth / max_depth.clamp(min=1.0),
        torch.zeros_like(shell_depth),
    )
    interiority = interiority * roi
    boundaryness = torch.where(roi > 0.0, 1.0 - interiority, torch.zeros_like(roi))
    return {
        "roi": roi,
        "interiority": torch.clamp(_normalize_tensor_map(interiority), 0.0, 1.0) * roi,
        "boundaryness": torch.clamp(boundaryness, 0.0, 1.0),
        "outside": torch.clamp(1.0 - roi, 0.0, 1.0),
    }


def build_operator_routing_v2_weights(
    transformation_field: torch.Tensor,
    source_consistency: torch.Tensor,
    preservation_field: torch.Tensor,
    roi_mask: torch.Tensor,
    config: OperatorRoutingV2Config,
) -> dict[str, torch.Tensor]:
    priors = build_soft_role_priors(roi_mask)
    roi = priors["roi"]
    interiority = priors["interiority"]
    boundaryness = priors["boundaryness"]

    transform = torch.clamp(transformation_field, 0.0, 1.0)
    consistency = torch.clamp(source_consistency, 0.0, 1.0)
    preserve_demand = torch.clamp(preservation_field, 0.0, 1.0)

    rewrite_raw = roi * transform * (
        1.0 + float(config.interiority_bias) * interiority + (1.0 - consistency)
    )
    if config.use_stabilize_operator:
        stabilize_raw = roi * torch.sqrt(torch.clamp(transform * consistency, 0.0, 1.0)) * (
            1.0 + float(config.boundary_bias) * boundaryness
        )
    else:
        stabilize_raw = torch.zeros_like(roi)
    preserve_raw = roi * preserve_demand * (
        1.0 + float(config.boundary_bias) * boundaryness
    )

    total = rewrite_raw + stabilize_raw + preserve_raw
    safe_total = total.clamp(min=1e-8)
    rewrite_weight = torch.where(roi > 0.0, rewrite_raw / safe_total, torch.zeros_like(roi))
    stabilize_weight = torch.where(roi > 0.0, stabilize_raw / safe_total, torch.zeros_like(roi))
    preserve_weight = torch.where(roi > 0.0, preserve_raw / safe_total, torch.zeros_like(roi))

    zero_total = (total <= 1e-8) & (roi > 0.0)
    preserve_weight = torch.where(zero_total, torch.ones_like(preserve_weight), preserve_weight)
    rewrite_weight = torch.where(zero_total, torch.zeros_like(rewrite_weight), rewrite_weight)
    stabilize_weight = torch.where(zero_total, torch.zeros_like(stabilize_weight), stabilize_weight)

    return {
        **priors,
        "transformation_field": transform,
        "source_consistency": consistency,
        "preservation_field": preserve_demand,
        "rewrite_weight": rewrite_weight,
        "stabilize_weight": stabilize_weight,
        "preserve_weight": preserve_weight,
    }


def build_stabilize_eps(
    eps_src: torch.Tensor,
    eps_tar: torch.Tensor,
    transformation_field: torch.Tensor,
    source_consistency: torch.Tensor,
) -> torch.Tensor:
    transform = torch.clamp(transformation_field, 0.0, 1.0)
    consistency = torch.clamp(source_consistency, 0.0, 1.0)
    blend = transform / (transform + consistency + 1e-8)
    return eps_src + blend * (eps_tar - eps_src)


def apply_operator_routing_v2_eps(
    eps_src: torch.Tensor,
    eps_tar: torch.Tensor,
    routing_weights: dict[str, torch.Tensor],
) -> torch.Tensor:
    roi = routing_weights["roi"]
    rewrite_weight = routing_weights["rewrite_weight"]
    stabilize_weight = routing_weights["stabilize_weight"]
    preserve_weight = routing_weights["preserve_weight"]

    stabilize_eps = build_stabilize_eps(
        eps_src=eps_src,
        eps_tar=eps_tar,
        transformation_field=routing_weights["transformation_field"],
        source_consistency=routing_weights["source_consistency"],
    )
    inside_eps = (
        rewrite_weight * eps_tar
        + stabilize_weight * stabilize_eps
        + preserve_weight * eps_src
    )
    return (1.0 - roi) * eps_src + roi * inside_eps
