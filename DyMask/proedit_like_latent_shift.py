from __future__ import annotations

from dataclasses import dataclass

import torch


@dataclass
class ProEditLikeLatentShiftConfig:
    strength: float = 0.20
    min_std: float = 1e-4


def _masked_mean_std(
    tensor: torch.Tensor,
    mask: torch.Tensor,
    min_std: float,
) -> tuple[torch.Tensor, torch.Tensor]:
    weight = mask.sum(dim=(-2, -1), keepdim=True).clamp(min=1.0)
    mean = (tensor * mask).sum(dim=(-2, -1), keepdim=True) / weight
    variance = (((tensor - mean) * mask) ** 2).sum(dim=(-2, -1), keepdim=True) / weight
    std = variance.clamp(min=min_std**2).sqrt()
    return mean, std


def apply_proedit_like_latent_shift(
    latents: torch.Tensor,
    roi_mask: torch.Tensor | None,
    config: ProEditLikeLatentShiftConfig,
) -> torch.Tensor:
    if roi_mask is None:
        return latents
    strength = float(config.strength)
    if strength <= 0.0:
        return latents

    roi_mask = roi_mask.to(device=latents.device, dtype=latents.dtype)
    if roi_mask.shape[0] != latents.shape[0]:
        return latents

    region_mask = torch.clamp(roi_mask, 0.0, 1.0)
    if float(region_mask.max().item()) <= 0.0:
        return latents

    noise = torch.randn_like(latents)
    latent_mean, latent_std = _masked_mean_std(latents, region_mask, float(config.min_std))
    noise_mean, noise_std = _masked_mean_std(noise, region_mask, float(config.min_std))
    matched_noise = ((noise - noise_mean) / noise_std) * latent_std + latent_mean
    shift_mask = torch.clamp(strength * region_mask, 0.0, 1.0)
    return (1.0 - shift_mask) * latents + shift_mask * matched_noise
