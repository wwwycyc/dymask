from __future__ import annotations

import json
import shutil
from pathlib import Path

from DyMaskRefactor.schemas import MaterializedSample, SampleCoreInput, SampleManifestEntry, SampleMetadata
from DyMaskRefactor.utils import save_json


def materialize_from_sample_json(sample_json_path: Path, output_dir: Path) -> tuple[list[MaterializedSample], list[SampleManifestEntry]]:
    payload = json.loads(sample_json_path.read_text(encoding="utf-8"))
    sample_id = payload["sample_id"]
    sample_dir = output_dir / sample_id
    sample_dir.mkdir(parents=True, exist_ok=True)

    core_payload = payload.get("core_input") or {}
    metadata_payload = payload.get("metadata") or {}
    source_image_value = core_payload.get("source_image_path") or payload["source_image_path"]
    target_prompt_value = core_payload.get("target_prompt") or payload["target_prompt"]
    target_token_hints = core_payload.get("target_token_hints") or payload.get("target_token_hints") or []

    source_source_path = Path(source_image_value)
    target_source = payload.get("target_reference_path")
    target_source_path = Path(target_source) if target_source else None
    source_path = sample_dir / "source.png"
    target_path = sample_dir / "target_reference.png"
    shutil.copy2(source_source_path, source_path)
    rewritten_target_reference_path = None
    if target_source_path and target_source_path.exists():
        shutil.copy2(target_source_path, target_path)
        rewritten_target_reference_path = str(target_path)

    rewritten_payload = dict(payload)
    rewritten_payload["core_input"] = {
        "source_image_path": str(source_path),
        "target_prompt": target_prompt_value,
        "target_token_hints": list(target_token_hints),
    }
    rewritten_payload["metadata"] = {
        "source_prompt": metadata_payload.get("source_prompt", payload.get("source_prompt")),
        "edit_prompt": metadata_payload.get("edit_prompt", payload.get("edit_prompt")),
        "blended_word": metadata_payload.get("blended_word", payload.get("blended_word")),
        "extras": metadata_payload.get("extras", payload.get("extras") or {}),
        "has_gt_mask": metadata_payload.get("has_gt_mask", False),
    }
    rewritten_payload["target_reference_path"] = rewritten_target_reference_path
    save_json(sample_dir / "sample.json", rewritten_payload)

    materialized_sample = MaterializedSample(
        sample_id=sample_id,
        row_index=int(payload["row_index"]),
        core_input=SampleCoreInput(
            source_image_path=source_path,
            target_prompt=target_prompt_value,
            target_token_hints=tuple(str(term).strip() for term in target_token_hints if str(term).strip()),
        ),
        target_image_path=target_path if rewritten_target_reference_path else None,
        sample_dir=sample_dir,
        metadata=SampleMetadata(
            source_prompt=metadata_payload.get("source_prompt", payload.get("source_prompt")),
            edit_prompt=metadata_payload.get("edit_prompt", payload.get("edit_prompt")),
            blended_word=metadata_payload.get("blended_word", payload.get("blended_word")),
            extras=metadata_payload.get("extras", payload.get("extras") or {}),
            gt_mask=None,
        ),
    )
    manifest_entry = SampleManifestEntry(
        sample_id=sample_id,
        row_index=int(payload["row_index"]),
        source_prompt=materialized_sample.source_prompt,
        edit_prompt=materialized_sample.edit_prompt,
        target_prompt=materialized_sample.target_prompt,
        source_image_path=str(source_path),
        target_image_path=rewritten_target_reference_path,
        record_id=payload.get("record_id"),
    )
    return [materialized_sample], [manifest_entry]
