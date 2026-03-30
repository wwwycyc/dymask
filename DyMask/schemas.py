from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import torch


@dataclass
class EditDatasetRecord:
    row_index: int
    original_prompt: str
    edit_prompt: str
    edited_prompt: str
    original_image_bytes: bytes
    edited_image_bytes: bytes | None = None
    original_image_path: str | None = None
    edited_image_path: str | None = None
    record_id: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class SampleCoreInput:
    source_image_path: Path
    target_prompt: str
    target_token_hints: tuple[str, ...] = ()


@dataclass
class SampleMetadata:
    source_prompt: str | None = None
    edit_prompt: str | None = None
    blended_word: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)
    gt_mask: np.ndarray | None = None

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "source_prompt": self.source_prompt,
            "edit_prompt": self.edit_prompt,
            "blended_word": self.blended_word,
            "extras": self.extras,
            "has_gt_mask": self.gt_mask is not None,
        }


@dataclass
class MaterializedSample:
    sample_id: str
    row_index: int
    core_input: SampleCoreInput
    target_image_path: Path | None
    sample_dir: Path
    metadata: SampleMetadata = field(default_factory=SampleMetadata)

    @property
    def source_image_path(self) -> Path:
        return self.core_input.source_image_path

    @property
    def target_prompt(self) -> str:
        return self.core_input.target_prompt

    @property
    def target_token_hints(self) -> tuple[str, ...]:
        return self.core_input.target_token_hints

    @property
    def source_prompt(self) -> str:
        return self.metadata.source_prompt or ""

    @property
    def edit_prompt(self) -> str:
        return self.metadata.edit_prompt or ""

    @property
    def blended_word(self) -> str | None:
        return self.metadata.blended_word

    @property
    def extras(self) -> dict[str, Any]:
        return self.metadata.extras

    @property
    def gt_mask(self) -> np.ndarray | None:
        return self.metadata.gt_mask


@dataclass
class SampleManifestEntry:
    sample_id: str
    row_index: int
    source_prompt: str
    edit_prompt: str
    target_prompt: str
    source_image_path: str
    target_image_path: str | None
    record_id: str | None = None


@dataclass
class TextCondition:
    prompt: str
    embeddings: torch.Tensor
    input_ids: torch.Tensor
    token_mask: torch.Tensor


@dataclass
class InversionOutput:
    zt_src: torch.Tensor
    src_latents: list[torch.Tensor]
    reconstruction_image: np.ndarray
    null_embeddings: list[torch.Tensor] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MethodResult:
    method_name: str
    edited_image: np.ndarray
    edited_image_path: Path
    mask_summary_path: Path | None
    aux_summary_path: Path | None
    delta_trace_path: Path | None
    diagnostics_csv_path: Path | None
    diagnostics_json_path: Path | None
    debug_json_path: Path
    metrics: dict[str, float | None] = field(default_factory=dict)
