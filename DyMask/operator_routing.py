from __future__ import annotations

from dataclasses import dataclass, field

import torch
import torch.nn.functional as F


def _normalize_kernel_size(kernel_size: int) -> int:
    kernel = max(1, int(kernel_size))
    if kernel % 2 == 0:
        kernel += 1
    return kernel


@dataclass(frozen=True)
class RegionRoleConfig:
    core_kernel_size: int = 5
    use_boundary_band: bool = True


@dataclass(frozen=True)
class OperatorRoutingConfig:
    role: RegionRoleConfig = field(default_factory=RegionRoleConfig)
    rewrite_boundary_scale: float = 0.5
    stabilize_scale: float = 1.0
    preserve_scale: float = 1.0
    use_stabilize_operator: bool = True
    frequency_kernel_size: int = 5
    stabilize_low_source_weight: float = 0.35
    stabilize_high_source_weight: float = 0.75


def _erode_mask(mask: torch.Tensor, kernel_size: int) -> torch.Tensor:
    kernel = _normalize_kernel_size(kernel_size)
    if kernel <= 1:
        return torch.clamp(mask, 0.0, 1.0)
    padding = kernel // 2
    eroded = 1.0 - F.max_pool2d(1.0 - mask, kernel_size=kernel, stride=1, padding=padding)
    return torch.clamp(eroded, 0.0, 1.0)


def build_region_role_masks(
    roi_mask: torch.Tensor,
    config: RegionRoleConfig,
) -> dict[str, torch.Tensor]:
    roi = torch.clamp(roi_mask, 0.0, 1.0)
    if not config.use_boundary_band:
        core = roi
        boundary = torch.zeros_like(roi)
    else:
        core = _erode_mask(roi, config.core_kernel_size) * roi
        boundary = torch.clamp(roi - core, 0.0, 1.0)
    return {
        "roi": roi,
        "core": core,
        "boundary": boundary,
        "outside": torch.clamp(1.0 - roi, 0.0, 1.0),
    }


def build_operator_routing_weights(
    transformation_field: torch.Tensor,
    source_consistency: torch.Tensor,
    roi_mask: torch.Tensor,
    config: OperatorRoutingConfig,
) -> dict[str, torch.Tensor]:
    roles = build_region_role_masks(roi_mask, config.role)
    roi = roles["roi"]
    core = roles["core"]
    boundary = roles["boundary"]
    transform = torch.clamp(transformation_field, 0.0, 1.0)
    consistency = torch.clamp(source_consistency, 0.0, 1.0)

    rewrite_raw = core * transform
    rewrite_raw = rewrite_raw + float(config.rewrite_boundary_scale) * boundary * transform * (1.0 - consistency)

    if config.use_stabilize_operator:
        stabilize_raw = float(config.stabilize_scale) * boundary * torch.sqrt(
            torch.clamp(transform * consistency, 0.0, 1.0)
        )
    else:
        stabilize_raw = torch.zeros_like(roi)

    preserve_raw = float(config.preserve_scale) * roi * consistency * (1.0 - transform)
    total = rewrite_raw + stabilize_raw + preserve_raw + 1e-8

    rewrite_weight = torch.where(roi > 0.0, rewrite_raw / total, torch.zeros_like(roi))
    stabilize_weight = torch.where(roi > 0.0, stabilize_raw / total, torch.zeros_like(roi))
    preserve_weight = torch.where(roi > 0.0, preserve_raw / total, torch.zeros_like(roi))

    return {
        **roles,
        "transformation_field": transform,
        "source_consistency": consistency,
        "rewrite_weight": rewrite_weight,
        "stabilize_weight": stabilize_weight,
        "preserve_weight": preserve_weight,
    }


def split_latent_frequency(latents: torch.Tensor, kernel_size: int) -> tuple[torch.Tensor, torch.Tensor]:
    kernel = _normalize_kernel_size(kernel_size)
    if kernel <= 1:
        low = latents
    else:
        padding = kernel // 2
        low = F.avg_pool2d(latents, kernel_size=kernel, stride=1, padding=padding)
    high = latents - low
    return low, high


def build_stabilize_latents(
    edited_latents: torch.Tensor,
    source_latents: torch.Tensor,
    config: OperatorRoutingConfig,
) -> torch.Tensor:
    edited_low, edited_high = split_latent_frequency(edited_latents, config.frequency_kernel_size)
    source_low, source_high = split_latent_frequency(source_latents, config.frequency_kernel_size)
    low_source_weight = float(config.stabilize_low_source_weight)
    high_source_weight = float(config.stabilize_high_source_weight)
    stabilized_low = (1.0 - low_source_weight) * edited_low + low_source_weight * source_low
    stabilized_high = (1.0 - high_source_weight) * edited_high + high_source_weight * source_high
    return stabilized_low + stabilized_high


def apply_operator_routing(
    edited_latents: torch.Tensor,
    source_latents: torch.Tensor,
    routing_weights: dict[str, torch.Tensor],
    config: OperatorRoutingConfig,
) -> torch.Tensor:
    roi = routing_weights["roi"]
    rewrite_weight = routing_weights["rewrite_weight"]
    stabilize_weight = routing_weights["stabilize_weight"]
    preserve_weight = routing_weights["preserve_weight"]

    rewrite_latents = edited_latents
    stabilize_latents = build_stabilize_latents(edited_latents, source_latents, config)
    preserve_latents = source_latents

    inside = (
        rewrite_weight * rewrite_latents
        + stabilize_weight * stabilize_latents
        + preserve_weight * preserve_latents
    )
    return roi * inside + (1.0 - roi) * source_latents
