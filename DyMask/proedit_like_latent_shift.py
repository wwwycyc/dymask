from __future__ import annotations

from dataclasses import dataclass

import torch


@dataclass
class ProEditLikeLatentShiftConfig:
    strength: float = 0.20


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

    refreshed_noise = torch.randn_like(latents)
    shift_mask = torch.clamp(strength * roi_mask.to(device=latents.device, dtype=latents.dtype), 0.0, 1.0)
    return (1.0 - shift_mask) * latents + shift_mask * refreshed_noise
