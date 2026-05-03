from __future__ import annotations

import json
import random
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

from .schemas import EditDatasetRecord, MaterializedSample, SampleCoreInput, SampleManifestEntry, SampleMetadata
from .utils import decode_image_bytes, decode_piebench_rle, prepare_image, save_csv_records, save_image, save_json


class MagicBrushParquetDataset:
    LEGACY_COLUMNS = [
        "original_prompt",
        "original_image",
        "edit_prompt",
        "edited_prompt",
        "edited_image",
    ]
    V1_COLUMNS = [
        "image",
        "id",
        "source_prompt",
        "target_prompt",
        "edit_action",
        "aspect_mapping",
        "blended_words",
        "mask",
    ]

    def __init__(self, parquet_path: Path) -> None:
        self.parquet_path = Path(parquet_path)
        if not self.parquet_path.exists():
            raise FileNotFoundError(f"Parquet dataset not found: {self.parquet_path}")
        self.parquet_file = pq.ParquetFile(self.parquet_path)
        if self.parquet_file.metadata.num_rows > 0:
            self.column_names = self.parquet_file.read_row_group(0).column_names
        else:
            self.column_names = self.parquet_file.schema.names
        self.dataset_format = self._detect_format()
        self._row_group_offsets = self._build_row_group_offsets()

    def _detect_format(self) -> str:
        columns = set(self.column_names)
        if set(self.LEGACY_COLUMNS).issubset(columns):
            return "legacy_edit_pair"
        if set(self.V1_COLUMNS).issubset(columns):
            return "single_image_prompt_edit"
        raise ValueError(f"Unsupported parquet schema columns: {self.column_names}")

    def _build_row_group_offsets(self) -> list[int]:
        offsets = [0]
        total = 0
        for group_index in range(self.parquet_file.num_row_groups):
            total += self.parquet_file.metadata.row_group(group_index).num_rows
            offsets.append(total)
        return offsets

    @property
    def num_rows(self) -> int:
        return self.parquet_file.metadata.num_rows

    def inspect_schema(self) -> dict[str, str | int]:
        return {
            "parquet_path": str(self.parquet_path),
            "num_rows": self.num_rows,
            "num_row_groups": self.parquet_file.num_row_groups,
            "column_names": ", ".join(self.column_names),
            "dataset_format": self.dataset_format,
            "schema": str(self.parquet_file.schema),
        }

    def sample_indices(self, sample_count: int, seed: int) -> list[int]:
        sample_count = min(sample_count, self.num_rows)
        generator = random.Random(seed)
        return sorted(generator.sample(range(self.num_rows), sample_count))

    def _resolve_row_group(self, row_index: int) -> tuple[int, int]:
        for group_index in range(self.parquet_file.num_row_groups):
            start = self._row_group_offsets[group_index]
            end = self._row_group_offsets[group_index + 1]
            if start <= row_index < end:
                return group_index, row_index - start
        raise IndexError(f"Row index out of range: {row_index}")

    def load_records(self, indices: list[int]) -> list[EditDatasetRecord]:
        by_group: dict[int, list[tuple[int, int]]] = defaultdict(list)
        for row_index in indices:
            group_index, local_index = self._resolve_row_group(row_index)
            by_group[group_index].append((row_index, local_index))

        records: list[EditDatasetRecord] = []
        for group_index, members in by_group.items():
            columns = self.LEGACY_COLUMNS if self.dataset_format == "legacy_edit_pair" else self.V1_COLUMNS
            table = self.parquet_file.read_row_group(group_index, columns=columns)
            rows = table.to_pylist()
            for row_index, local_index in members:
                row = rows[local_index]
                if self.dataset_format == "legacy_edit_pair":
                    original_image = row["original_image"] or {}
                    edited_image = row["edited_image"] or {}
                    record = EditDatasetRecord(
                        row_index=row_index,
                        original_prompt=row.get("original_prompt") or "",
                        edit_prompt=row.get("edit_prompt") or "",
                        edited_prompt=row.get("edited_prompt") or "",
                        original_image_bytes=original_image.get("bytes") or b"",
                        edited_image_bytes=edited_image.get("bytes") or b"",
                        original_image_path=original_image.get("path"),
                        edited_image_path=edited_image.get("path"),
                    )
                else:
                    source_image = row["image"] or {}
                    record = EditDatasetRecord(
                        row_index=row_index,
                        original_prompt=row.get("source_prompt") or "",
                        edit_prompt=row.get("edit_action") or "",
                        edited_prompt=row.get("target_prompt") or "",
                        original_image_bytes=source_image.get("bytes") or b"",
                        edited_image_bytes=None,
                        original_image_path=source_image.get("path"),
                        edited_image_path=None,
                        record_id=row.get("id"),
                        extras={
                            "dataset_format": self.dataset_format,
                            "aspect_mapping": row.get("aspect_mapping"),
                            "blended_words": row.get("blended_words"),
                            "mask": row.get("mask"),
                        },
                    )
                records.append(record)
        return sorted(records, key=lambda item: item.row_index)

    def materialize_samples(
        self,
        records: list[EditDatasetRecord],
        output_dir: Path,
        image_size: int,
    ) -> tuple[list[MaterializedSample], list[SampleManifestEntry]]:
        output_dir.mkdir(parents=True, exist_ok=True)
        materialized: list[MaterializedSample] = []
        manifest: list[SampleManifestEntry] = []
        for offset, record in enumerate(records):
            sample_id = f"sample_{offset:03d}_row_{record.row_index:06d}"
            sample_dir = output_dir / sample_id
            sample_dir.mkdir(parents=True, exist_ok=True)

            source_image = prepare_image(decode_image_bytes(record.original_image_bytes), image_size)
            source_path = sample_dir / "source.png"
            target_path = sample_dir / "target_reference.png"
            meta_path = sample_dir / "sample.json"

            save_image(source_path, source_image)
            target_reference_path: str | None = None
            if record.edited_image_bytes:
                target_image = prepare_image(decode_image_bytes(record.edited_image_bytes), image_size)
                save_image(target_path, target_image)
                target_reference_path = str(target_path)
            core_payload = {
                "source_image_path": str(source_path),
                "target_prompt": record.edited_prompt,
                "target_token_hints": [],
            }
            metadata_payload = {
                "source_prompt": record.original_prompt,
                "edit_prompt": record.edit_prompt,
                "blended_word": None,
                "extras": record.extras,
                "has_gt_mask": False,
            }
            sample_payload = {
                "sample_id": sample_id,
                "row_index": record.row_index,
                "record_id": record.record_id,
                "core_input": core_payload,
                "metadata": metadata_payload,
                "original_image_path": record.original_image_path,
                "edited_image_path": record.edited_image_path,
                "target_reference_path": target_reference_path,
            }
            save_json(meta_path, sample_payload)

            materialized_sample = MaterializedSample(
                sample_id=sample_id,
                row_index=record.row_index,
                core_input=SampleCoreInput(
                    source_image_path=source_path,
                    target_prompt=record.edited_prompt,
                    target_token_hints=(),
                ),
                target_image_path=target_path if target_reference_path else None,
                sample_dir=sample_dir,
                metadata=SampleMetadata(
                    source_prompt=record.original_prompt,
                    edit_prompt=record.edit_prompt,
                    blended_word=None,
                    extras=record.extras,
                    gt_mask=None,
                ),
            )
            manifest_entry = SampleManifestEntry(
                sample_id=sample_id,
                row_index=record.row_index,
                source_prompt=record.original_prompt,
                edit_prompt=record.edit_prompt,
                target_prompt=record.edited_prompt,
                source_image_path=str(source_path),
                target_image_path=target_reference_path,
                record_id=record.record_id,
            )
            materialized.append(materialized_sample)
            manifest.append(manifest_entry)
        return materialized, manifest

    @staticmethod
    def write_manifest(output_dir: Path, manifest_name: str, manifest: list[SampleManifestEntry]) -> None:
        json_path = output_dir / f"{manifest_name}.json"
        csv_path = output_dir / f"{manifest_name}.csv"
        rows = [entry.__dict__ for entry in manifest]
        save_json(json_path, {"samples": rows})
        save_csv_records(csv_path, rows)


class PIEBenchDataset:
    """Loader for PIE-Bench dataset (JSON mapping file + external jpg images)."""

    def __init__(self, pie_bench_dir: Path) -> None:
        self.pie_bench_dir = Path(pie_bench_dir)
        mapping_path = self.pie_bench_dir / "mapping_file.json"
        if not mapping_path.exists():
            raise FileNotFoundError(f"PIE-Bench mapping_file.json not found: {mapping_path}")
        with open(mapping_path, encoding="utf-8") as f:
            self._data: dict[str, dict] = json.load(f)
        self._keys: list[str] = sorted(self._data.keys())

    def __len__(self) -> int:
        return len(self._keys)

    def sample_indices(self, count: int, seed: int) -> list[int]:
        rng = random.Random(seed)
        indices = list(range(len(self._keys)))
        rng.shuffle(indices)
        return indices[:count]

    def load_records(self, indices: list[int]) -> list["PIEBenchRecord"]:
        records = []
        for idx in indices:
            key = self._keys[idx]
            entry = self._data[key]
            image_full_path = self.pie_bench_dir / "annotation_images" / entry["image_path"]
            editing_prompt_raw = entry["editing_prompt"]
            target_prompt = editing_prompt_raw.replace("[", "").replace("]", "")
            target_token_hints = tuple(
                term.strip()
                for term in re.findall(r"\[([^\]]+)\]", editing_prompt_raw)
                if term.strip()
            )
            blended_word = entry.get("blended_word", "").split()[0] if entry.get("blended_word") else ""
            rle = entry.get("mask", [])
            gt_mask = decode_piebench_rle(rle) if rle else None
            records.append(PIEBenchRecord(
                row_index=idx,
                key=key,
                image_path=image_full_path,
                original_prompt=entry["original_prompt"],
                target_prompt=target_prompt,
                editing_instruction=entry.get("editing_instruction", ""),
                editing_type_id=entry.get("editing_type_id", ""),
                blended_word=blended_word,
                target_token_hints=target_token_hints,
                gt_mask=gt_mask,
            ))
        return records

    def materialize_samples(
        self,
        records: list["PIEBenchRecord"],
        output_dir: Path,
        image_size: int,
    ) -> tuple[list[MaterializedSample], list[SampleManifestEntry]]:
        output_dir.mkdir(parents=True, exist_ok=True)
        materialized: list[MaterializedSample] = []
        manifest: list[SampleManifestEntry] = []
        for offset, record in enumerate(records):
            sample_id = f"sample_{offset:03d}_pie_{record.key}"
            sample_dir = output_dir / sample_id
            sample_dir.mkdir(parents=True, exist_ok=True)

            from PIL import Image as PILImage
            pil_img = PILImage.open(record.image_path).convert("RGB")
            source_arr = prepare_image(pil_img, image_size)
            source_path = sample_dir / "source.png"
            save_image(source_path, source_arr)

            core_payload = {
                "source_image_path": str(source_path),
                "target_prompt": record.target_prompt,
                "target_token_hints": list(record.target_token_hints),
            }
            metadata_payload = {
                "source_prompt": record.original_prompt,
                "edit_prompt": record.editing_instruction,
                "blended_word": record.blended_word,
                "extras": {
                    "dataset_format": "piebench",
                    "editing_type_id": record.editing_type_id,
                },
                "has_gt_mask": record.gt_mask is not None,
            }
            meta = {
                "sample_id": sample_id,
                "row_index": record.row_index,
                "key": record.key,
                "core_input": core_payload,
                "metadata": metadata_payload,
                "target_reference_path": None,
            }
            save_json(sample_dir / "sample.json", meta)

            materialized_sample = MaterializedSample(
                sample_id=sample_id,
                row_index=record.row_index,
                core_input=SampleCoreInput(
                    source_image_path=source_path,
                    target_prompt=record.target_prompt,
                    target_token_hints=record.target_token_hints,
                ),
                target_image_path=None,
                sample_dir=sample_dir,
                metadata=SampleMetadata(
                    source_prompt=record.original_prompt,
                    edit_prompt=record.editing_instruction,
                    blended_word=record.blended_word or None,
                    extras={
                        "dataset_format": "piebench",
                        "editing_type_id": record.editing_type_id,
                    },
                    gt_mask=record.gt_mask,
                ),
            )
            manifest_entry = SampleManifestEntry(
                sample_id=sample_id,
                row_index=record.row_index,
                source_prompt=record.original_prompt,
                edit_prompt=record.editing_instruction,
                target_prompt=record.target_prompt,
                source_image_path=str(source_path),
                target_image_path=None,
                record_id=record.key,
            )
            materialized.append(materialized_sample)
            manifest.append(manifest_entry)
        return materialized, manifest


from dataclasses import dataclass, field as dc_field

@dataclass
class PIEBenchRecord:
    row_index: int
    key: str
    image_path: Path
    original_prompt: str
    target_prompt: str
    editing_instruction: str
    editing_type_id: str
    blended_word: str
    target_token_hints: tuple[str, ...] = dc_field(default_factory=tuple)
    gt_mask: np.ndarray | None = None
