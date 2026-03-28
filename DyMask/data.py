from __future__ import annotations

import random
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq

from .schemas import EditDatasetRecord, MaterializedSample, SampleManifestEntry
from .utils import decode_image_bytes, prepare_image, save_csv_records, save_image, save_json


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
            sample_payload = {
                "sample_id": sample_id,
                "row_index": record.row_index,
                "record_id": record.record_id,
                "source_prompt": record.original_prompt,
                "edit_prompt": record.edit_prompt,
                "target_prompt": record.edited_prompt,
                "original_image_path": record.original_image_path,
                "edited_image_path": record.edited_image_path,
                "source_image_path": str(source_path),
                "target_reference_path": target_reference_path,
                "extras": record.extras,
            }
            save_json(meta_path, sample_payload)

            materialized_sample = MaterializedSample(
                sample_id=sample_id,
                row_index=record.row_index,
                source_prompt=record.original_prompt,
                edit_prompt=record.edit_prompt,
                target_prompt=record.edited_prompt,
                source_image_path=source_path,
                target_image_path=target_path if target_reference_path else None,
                sample_dir=sample_dir,
                extras=record.extras,
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
