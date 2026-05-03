from __future__ import annotations

from pathlib import Path

import torch

from . import vision_transformer as vits


AVAILABLE_DINO_MODELS = (
    "dino_vits16",
    "dino_vits8",
    "dino_vitb16",
    "dino_vitb8",
)


def _build_backbone(model_name: str) -> torch.nn.Module:
    if model_name == "dino_vits16":
        return vits.vit_small(patch_size=16, num_classes=0)
    if model_name == "dino_vits8":
        return vits.vit_small(patch_size=8, num_classes=0)
    if model_name == "dino_vitb16":
        return vits.vit_base(patch_size=16, num_classes=0)
    if model_name == "dino_vitb8":
        return vits.vit_base(patch_size=8, num_classes=0)
    raise ValueError(f"Unsupported DINO model: {model_name}. Expected one of {AVAILABLE_DINO_MODELS}.")


def _extract_state_dict(payload) -> dict[str, torch.Tensor]:
    if isinstance(payload, dict):
        for key in ("state_dict", "teacher", "student", "model"):
            nested = payload.get(key)
            if isinstance(nested, dict):
                payload = nested
                break
    if not isinstance(payload, dict):
        raise TypeError("Unsupported DINO checkpoint format.")

    state_dict: dict[str, torch.Tensor] = {}
    for key, value in payload.items():
        if not isinstance(value, torch.Tensor):
            continue
        name = str(key)
        for prefix in ("module.", "backbone.", "model."):
            if name.startswith(prefix):
                name = name[len(prefix):]
        state_dict[name] = value
    if not state_dict:
        raise ValueError("No tensor weights found in DINO checkpoint.")
    return state_dict


def build_dino_model(model_name: str, weights_path: str | None = None) -> torch.nn.Module:
    model = _build_backbone(model_name)
    if weights_path:
        try:
            checkpoint = torch.load(Path(weights_path).expanduser(), map_location="cpu", weights_only=True)
        except TypeError:
            checkpoint = torch.load(Path(weights_path).expanduser(), map_location="cpu")
        model.load_state_dict(_extract_state_dict(checkpoint), strict=True)
    return model
