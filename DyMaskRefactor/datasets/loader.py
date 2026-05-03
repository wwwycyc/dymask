from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from DyMaskRefactor.data import MagicBrushParquetDataset, PIEBenchDataset
from DyMaskRefactor.sample_io import materialize_from_sample_json
from DyMaskRefactor.schemas import MaterializedSample, SampleManifestEntry

from DyMaskRefactor.config import ExperimentConfig


@dataclass
class LoadedSamples:
    samples: list[MaterializedSample]
    manifest: list[SampleManifestEntry]


def _resolve_indices(dataset, sample_count: int, sample_seed: int, row_indices: list[int] | None) -> list[int]:
    if row_indices:
        return [int(index) for index in row_indices]
    return dataset.sample_indices(sample_count, sample_seed)


def load_materialized_samples(
    config: ExperimentConfig,
    *,
    output_dir: Path,
    sample_json: str | None = None,
    row_indices: list[int] | None = None,
) -> LoadedSamples:
    if sample_json:
        samples, manifest = materialize_from_sample_json(Path(sample_json), output_dir)
        return LoadedSamples(samples=samples, manifest=manifest)

    if config.sampling.piebench_path is not None:
        dataset = PIEBenchDataset(config.sampling.piebench_path)
    else:
        dataset = MagicBrushParquetDataset(config.sampling.parquet_path)

    indices = _resolve_indices(dataset, config.sampling.sample_count, config.sampling.sample_seed, row_indices)
    records = dataset.load_records(indices)
    samples, manifest = dataset.materialize_samples(records, output_dir, config.runtime.image_size)
    return LoadedSamples(samples=samples, manifest=manifest)


def write_manifest(output_dir: Path, manifest_name: str, manifest: list[SampleManifestEntry]) -> None:
    MagicBrushParquetDataset.write_manifest(output_dir, manifest_name, manifest)
