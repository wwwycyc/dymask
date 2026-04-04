from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from DyMask.data import PIEBenchDataset
from DyMask.config import MetricConfig, RuntimeConfig
from DyMask.metrics import MetricRunner
from DyMask.run_v1 import resolve_overview_methods, write_overview_method_metric_tables
from DyMask.utils import save_csv_records, save_json


def load_image(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"))


def load_config_payload(run_dir: Path) -> dict:
    payload = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    if "runtime" in payload and "metrics" in payload:
        return payload
    experiment = payload.get("experiment")
    if isinstance(experiment, dict) and "runtime" in experiment and "metrics" in experiment:
        return experiment
    raise KeyError(f"Unsupported config.json schema in {run_dir}")


def build_runtime_and_metrics(run_dir: Path) -> tuple[dict, RuntimeConfig, MetricConfig]:
    payload = load_config_payload(run_dir)
    runtime = RuntimeConfig(**payload["runtime"])
    metrics = MetricConfig(**payload["metrics"])
    return payload, runtime, metrics


def parse_sample_payload(payload: dict) -> dict[str, object]:
    core_input = payload.get("core_input") or {}
    metadata = payload.get("metadata") or {}
    return {
        "sample_id": payload["sample_id"],
        "target_prompt": core_input.get("target_prompt", payload.get("target_prompt", "")),
        "source_prompt": metadata.get("source_prompt", payload.get("source_prompt", "")),
        "edit_prompt": metadata.get("edit_prompt", payload.get("edit_prompt", "")),
        "target_reference_path": payload.get("target_reference_path"),
        "row_index": payload.get("row_index"),
        "key": payload.get("key"),
        "has_gt_mask": metadata.get("has_gt_mask", False),
    }


def maybe_build_piebench_dataset(config_payload: dict) -> PIEBenchDataset | None:
    sampling = config_payload.get("sampling") or {}
    piebench_path = sampling.get("piebench_path")
    if not piebench_path:
        return None
    dataset = PIEBenchDataset(Path(piebench_path))
    return dataset


def resolve_gt_mask(sample_meta: dict[str, object], piebench_dataset: PIEBenchDataset | None) -> np.ndarray | None:
    if piebench_dataset is None or not bool(sample_meta.get("has_gt_mask")):
        return None
    row_index = sample_meta.get("row_index")
    if isinstance(row_index, int):
        record = piebench_dataset.load_records([row_index])[0]
        return record.gt_mask
    key = sample_meta.get("key")
    if isinstance(key, str) and key in piebench_dataset._data:
        keys = piebench_dataset._keys
        record = piebench_dataset.load_records([keys.index(key)])[0]
        return record.gt_mask
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill metrics for an existing run directory.")
    parser.add_argument("run_dir", help="Run directory under runs/dymask_v1.")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        raise FileNotFoundError(f"Run directory not found: {run_dir}")

    config_payload, runtime, metrics = build_runtime_and_metrics(run_dir)
    metric_runner = MetricRunner(runtime, metrics)
    piebench_dataset = maybe_build_piebench_dataset(config_payload)
    methods = tuple(config_payload.get("methods") or ())
    variant_payload = {}
    variant_path = run_dir / "variant.json"
    if variant_path.exists():
        variant_payload = json.loads(variant_path.read_text(encoding="utf-8"))
    variant_name = variant_payload.get("variant_name")
    rows: list[dict] = []

    samples_dir = run_dir / "samples"
    for sample_dir in sorted(path for path in samples_dir.iterdir() if path.is_dir()):
        sample_meta = parse_sample_payload(json.loads((sample_dir / "sample.json").read_text(encoding="utf-8")))
        source_image = load_image(sample_dir / "source.png")
        reconstruction_image = load_image(sample_dir / "source_reconstruction.png")
        target_reference_path = sample_meta["target_reference_path"]
        target_reference = load_image(Path(target_reference_path)) if target_reference_path else None
        gt_mask = resolve_gt_mask(sample_meta, piebench_dataset)

        phase0_row = {
            "sample_id": sample_meta["sample_id"],
            "method_name": "phase0_reconstruction",
            "source_prompt": sample_meta["source_prompt"],
            "edit_prompt": sample_meta["edit_prompt"],
            "target_prompt": sample_meta["target_prompt"],
            "variant": variant_name,
            "reconstruction_path": str(sample_dir / "source_reconstruction.png"),
            "source_recon_psnr": metric_runner.compute_psnr(source_image, reconstruction_image),
        }
        try:
            phase0_row["source_recon_lpips"] = metric_runner.compute_lpips(source_image, reconstruction_image)
        except Exception as exc:
            phase0_row["source_recon_lpips"] = None
            phase0_row["source_recon_lpips_error"] = str(exc)
        rows.append(phase0_row)

        method_dirs = sorted(path for path in sample_dir.iterdir() if path.is_dir())
        for method_dir in method_dirs:
            edited_path = method_dir / "edited.png"
            if not edited_path.exists():
                continue
            edited_image = load_image(edited_path)
            metrics_row = metric_runner.evaluate_case(
                source_image=source_image,
                reconstruction_image=reconstruction_image,
                edited_image=edited_image,
                target_text=sample_meta["target_prompt"],
                reference_edited=target_reference,
                gt_mask=gt_mask,
            )
            row = {
                "sample_id": sample_meta["sample_id"],
                "method_name": method_dir.name,
                "source_prompt": sample_meta["source_prompt"],
                "edit_prompt": sample_meta["edit_prompt"],
                "target_prompt": sample_meta["target_prompt"],
                "variant": variant_name,
                **metrics_row,
                "edited_image_path": str(edited_path),
                "mask_summary_path": str(method_dir / "mask_summary.png") if (method_dir / "mask_summary.png").exists() else None,
                "aux_summary_path": str(method_dir / "aux_summary.png") if (method_dir / "aux_summary.png").exists() else None,
                "delta_trace_path": str(method_dir / "delta_trace.csv") if (method_dir / "delta_trace.csv").exists() else None,
                "diagnostics_csv_path": str(method_dir / "step_diagnostics.csv") if (method_dir / "step_diagnostics.csv").exists() else None,
                "diagnostics_json_path": str(method_dir / "step_diagnostics.json") if (method_dir / "step_diagnostics.json").exists() else None,
                "debug_json_path": str(method_dir / "debug.json") if (method_dir / "debug.json").exists() else None,
            }
            rows.append(row)

    save_csv_records(run_dir / "metrics_case_level.csv", rows)
    summary_rows = metric_runner.summarize(rows)
    save_csv_records(run_dir / "metrics_summary.csv", summary_rows)
    save_json(run_dir / "metrics_summary.json", {"summary": summary_rows})
    if methods:
        overview_methods = resolve_overview_methods(methods)
        write_overview_method_metric_tables(run_dir, rows, overview_methods)
    print(run_dir / "metrics_summary.csv")


if __name__ == "__main__":
    main()
