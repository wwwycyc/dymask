from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from DyMask.config import MetricConfig, RuntimeConfig
from DyMask.metrics import MetricRunner
from DyMask.utils import save_csv_records, save_json


def load_image(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"))


def build_runtime_and_metrics(run_dir: Path) -> tuple[RuntimeConfig, MetricConfig]:
    payload = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    runtime = RuntimeConfig(**payload["runtime"])
    metrics = MetricConfig(**payload["metrics"])
    return runtime, metrics


def parse_sample_payload(payload: dict) -> dict[str, object]:
    core_input = payload.get("core_input") or {}
    metadata = payload.get("metadata") or {}
    return {
        "sample_id": payload["sample_id"],
        "target_prompt": core_input.get("target_prompt", payload.get("target_prompt", "")),
        "source_prompt": metadata.get("source_prompt", payload.get("source_prompt", "")),
        "edit_prompt": metadata.get("edit_prompt", payload.get("edit_prompt", "")),
        "target_reference_path": payload.get("target_reference_path"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill metrics for an existing run directory.")
    parser.add_argument("run_dir", help="Run directory under runs/dymask_v1.")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        raise FileNotFoundError(f"Run directory not found: {run_dir}")

    runtime, metrics = build_runtime_and_metrics(run_dir)
    metric_runner = MetricRunner(runtime, metrics)
    rows: list[dict] = []

    samples_dir = run_dir / "samples"
    for sample_dir in sorted(path for path in samples_dir.iterdir() if path.is_dir()):
        sample_meta = parse_sample_payload(json.loads((sample_dir / "sample.json").read_text(encoding="utf-8")))
        source_image = load_image(sample_dir / "source.png")
        reconstruction_image = load_image(sample_dir / "source_reconstruction.png")
        target_reference_path = sample_meta["target_reference_path"]
        target_reference = load_image(Path(target_reference_path)) if target_reference_path else None

        phase0_row = {
            "sample_id": sample_meta["sample_id"],
            "method_name": "phase0_reconstruction",
            "source_prompt": sample_meta["source_prompt"],
            "edit_prompt": sample_meta["edit_prompt"],
            "target_prompt": sample_meta["target_prompt"],
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
            )
            row = {
                "sample_id": sample_meta["sample_id"],
                "method_name": method_dir.name,
                "source_prompt": sample_meta["source_prompt"],
                "edit_prompt": sample_meta["edit_prompt"],
                "target_prompt": sample_meta["target_prompt"],
                **metrics_row,
                "edited_image_path": str(edited_path),
                "mask_summary_path": str(method_dir / "mask_summary.png") if (method_dir / "mask_summary.png").exists() else None,
                "aux_summary_path": str(method_dir / "aux_summary.png") if (method_dir / "aux_summary.png").exists() else None,
                "delta_trace_path": str(method_dir / "delta_trace.csv") if (method_dir / "delta_trace.csv").exists() else None,
                "debug_json_path": str(method_dir / "debug.json") if (method_dir / "debug.json").exists() else None,
            }
            rows.append(row)

    save_csv_records(run_dir / "metrics_case_level.csv", rows)
    summary_rows = metric_runner.summarize(rows)
    save_csv_records(run_dir / "metrics_summary.csv", summary_rows)
    save_json(run_dir / "metrics_summary.json", {"summary": summary_rows})
    print(run_dir / "metrics_summary.csv")


if __name__ == "__main__":
    main()
