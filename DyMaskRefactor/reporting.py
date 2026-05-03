from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from DyMaskRefactor.overviews import (
    build_run_overview,
    build_sample_overview,
    resolve_overview_methods,
    write_overview_method_metric_tables,
)
from DyMaskRefactor.utils import save_csv_records


def collect_case_rows(run_samples, batch_results, metric_service, variant_name: str) -> list[dict]:
    case_rows: list[dict] = []
    for sample in run_samples:
        inversion, method_results = batch_results[sample.sample_id]
        source_image = np.asarray(Image.open(sample.source_image_path).convert("RGB"))
        target_reference = None
        if sample.target_image_path is not None and Path(sample.target_image_path).exists():
            target_reference = np.asarray(Image.open(sample.target_image_path).convert("RGB"))

        phase0_row = {
            "sample_id": sample.sample_id,
            "method_name": "phase0_reconstruction",
            "source_prompt": sample.source_prompt,
            "edit_prompt": sample.edit_prompt,
            "target_prompt": sample.target_prompt,
            "source_reconstruction_path": str(sample.sample_dir / "source_reconstruction.png"),
        }
        if metric_service is not None:
            phase0_row["source_recon_psnr"] = metric_service.compute_psnr(source_image, inversion.reconstruction_image)
            try:
                phase0_row["source_recon_lpips"] = metric_service.compute_lpips(source_image, inversion.reconstruction_image)
            except Exception as exc:  # pragma: no cover - best effort logging
                phase0_row["source_recon_lpips"] = None
                phase0_row["source_recon_lpips_error"] = str(exc)
        case_rows.append(phase0_row)

        for result in method_results:
            row = {
                "sample_id": sample.sample_id,
                "method_name": result.method_name,
                "source_prompt": sample.source_prompt,
                "edit_prompt": sample.edit_prompt,
                "target_prompt": sample.target_prompt,
                "edited_image_path": str(result.edited_image_path),
                "mask_summary_path": str(result.mask_summary_path),
                "aux_summary_path": str(result.aux_summary_path),
                "delta_trace_path": str(result.delta_trace_path),
                "diagnostics_csv_path": str(result.diagnostics_csv_path),
                "diagnostics_json_path": str(result.diagnostics_json_path),
                "debug_json_path": str(result.debug_json_path),
                "variant": variant_name,
            }
            if metric_service is not None:
                metrics_row = metric_service.evaluate_case(
                    source_image=source_image,
                    reconstruction_image=inversion.reconstruction_image,
                    edited_image=result.edited_image,
                    source_text=sample.source_prompt,
                    target_text=sample.target_prompt,
                    reference_edited=target_reference,
                    gt_mask=sample.gt_mask,
                )
                row.update(metrics_row)
            case_rows.append(row)
    return case_rows


def write_run_reports(run_dir: Path, run_samples, batch_results, case_rows: list[dict], metric_service, methods: tuple[str, ...], image_size: int) -> None:
    save_csv_records(run_dir / "metrics_case_level.csv", case_rows)
    overview_methods = resolve_overview_methods(methods)
    if metric_service is not None:
        save_csv_records(run_dir / "metrics_summary.csv", metric_service.summarize(case_rows))
        write_overview_method_metric_tables(run_dir, case_rows, overview_methods)
    for sample in run_samples:
        _inversion, method_results = batch_results[sample.sample_id]
        build_sample_overview(sample, method_results, image_size, overview_methods)
    build_run_overview(run_dir, run_samples)
