from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from DyMaskRefactor.schemas import MaterializedSample
from DyMaskRefactor.utils import compose_labeled_overview, save_csv_records, save_image, save_json


METHOD_DISPLAY_NAMES = {
    "target_only": "target-only",
    "global_blend": "global blend",
    "discrepancy_only": "D_t",
    "discrepancy_attention": "D_t + A_t",
    "discrepancy_latent": "D_t - C_t",
    "full_dynamic_mask": "Full",
}


def canonical_method_name(method_name: str) -> str:
    return "global_blend" if method_name.startswith("global_blend") else method_name


def display_method_name(method_name: str) -> str:
    return METHOD_DISPLAY_NAMES.get(canonical_method_name(method_name), method_name)


def resolve_overview_methods(method_names: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    resolved: list[str] = []
    for method_name in method_names:
        canonical_name = canonical_method_name(str(method_name))
        if canonical_name not in METHOD_DISPLAY_NAMES:
            continue
        if canonical_name in resolved:
            continue
        resolved.append(canonical_name)
    return tuple(resolved)


def build_sample_overview(
    sample: MaterializedSample,
    method_results: list,
    image_size: int,
    overview_methods: tuple[str, ...],
) -> Path | None:
    result_by_method = {
        canonical_method_name(result.method_name): result
        for result in method_results
    }
    active_methods = tuple(method for method in overview_methods if method in result_by_method)
    if not active_methods:
        return None

    items: list[tuple[str, np.ndarray]] = [
        ("source", np.asarray(Image.open(sample.source_image_path).convert("RGB"))),
    ]
    for method_name in active_methods:
        result = result_by_method[method_name]
        items.append((display_method_name(method_name), np.asarray(Image.open(result.edited_image_path).convert("RGB"))))

    full_result = result_by_method.get("full_dynamic_mask")
    if full_result is None:
        return None
    if full_result.aux_summary_path is None or not Path(full_result.aux_summary_path).exists():
        return None
    items.append(("mask overview", np.asarray(Image.open(full_result.aux_summary_path).convert("RGB"))))

    overview = compose_labeled_overview(
        items,
        columns=4,
        tile_size=(image_size, image_size),
        title=sample.sample_id,
    )
    overview_path = sample.sample_dir / "overview.png"
    save_image(overview_path, overview)
    return overview_path


def build_run_overview(run_dir: Path, samples: list[MaterializedSample]) -> Path | None:
    items: list[tuple[str, np.ndarray]] = []
    for sample in samples:
        overview_path = sample.sample_dir / "overview.png"
        if not overview_path.exists():
            continue
        items.append((sample.sample_id, np.asarray(Image.open(overview_path).convert("RGB"))))
    if not items:
        return None

    columns = 2 if len(items) <= 4 else 4
    overview = compose_labeled_overview(
        items,
        columns=columns,
        tile_size=(960, 560),
        title=run_dir.name,
    )
    overview_path = run_dir / "overview_all_samples.png"
    save_image(overview_path, overview)
    return overview_path


def _metric_mean(values: list[float | None]) -> float | None:
    numeric = [float(value) for value in values if value is not None and np.isfinite(float(value))]
    if not numeric:
        return None
    return float(np.mean(numeric))


def _metric_std(values: list[float | None]) -> float | None:
    numeric = [float(value) for value in values if value is not None and np.isfinite(float(value))]
    if not numeric:
        return None
    return float(np.std(numeric, ddof=0))


def write_overview_method_metric_tables(
    run_dir: Path,
    case_rows: list[dict],
    overview_methods: tuple[str, ...],
) -> tuple[Path, Path]:
    ordered_methods = list(overview_methods)
    filtered_rows: list[dict[str, object]] = []

    for row in case_rows:
        method_name = row.get("method_name")
        if not isinstance(method_name, str):
            continue
        canonical_name = canonical_method_name(method_name)
        if canonical_name not in ordered_methods:
            continue
        filtered_rows.append(
            {
                "sample_id": row.get("sample_id"),
                "method_name": display_method_name(canonical_name),
                "edit_reference_mode": row.get("edit_reference_mode"),
                "clip_similarity_source_image": row.get("clip_similarity_source_image"),
                "clip_similarity_target_image": row.get("clip_similarity_target_image"),
                "clip_similarity_target_image_edit_part": row.get("clip_similarity_target_image_edit_part"),
                "psnr": row.get("psnr"),
                "lpips": row.get("lpips"),
                "mse": row.get("mse"),
                "ssim": row.get("ssim"),
                "structure_distance": row.get("structure_distance"),
                "psnr_unedit_part": row.get("psnr_unedit_part"),
                "lpips_unedit_part": row.get("lpips_unedit_part"),
                "mse_unedit_part": row.get("mse_unedit_part"),
                "ssim_unedit_part": row.get("ssim_unedit_part"),
                "structure_distance_unedit_part": row.get("structure_distance_unedit_part"),
                "locality_ratio": row.get("locality_ratio"),
            }
        )

    filtered_rows.sort(
        key=lambda row: (
            str(row["sample_id"]),
            ordered_methods.index(next(name for name, label in METHOD_DISPLAY_NAMES.items() if label == row["method_name"])),
        )
    )

    case_table_path = run_dir / "metrics_overview_methods_case_level.csv"
    save_csv_records(case_table_path, filtered_rows)

    summary_rows: list[dict[str, object]] = []
    for method_name in ordered_methods:
        display_name = display_method_name(method_name)
        method_rows = [row for row in filtered_rows if row["method_name"] == display_name]
        summary_rows.append(
            {
                "method_name": display_name,
                "sample_count": len(method_rows),
                "target_reference_count": sum(1 for row in method_rows if row["edit_reference_mode"] == "target_reference"),
                "clip_similarity_source_image_mean": _metric_mean([row["clip_similarity_source_image"] for row in method_rows]),
                "clip_similarity_source_image_std": _metric_std([row["clip_similarity_source_image"] for row in method_rows]),
                "clip_similarity_target_image_mean": _metric_mean([row["clip_similarity_target_image"] for row in method_rows]),
                "clip_similarity_target_image_std": _metric_std([row["clip_similarity_target_image"] for row in method_rows]),
                "clip_similarity_target_image_edit_part_mean": _metric_mean([row["clip_similarity_target_image_edit_part"] for row in method_rows]),
                "clip_similarity_target_image_edit_part_std": _metric_std([row["clip_similarity_target_image_edit_part"] for row in method_rows]),
                "psnr_mean": _metric_mean([row["psnr"] for row in method_rows]),
                "psnr_std": _metric_std([row["psnr"] for row in method_rows]),
                "lpips_mean": _metric_mean([row["lpips"] for row in method_rows]),
                "lpips_std": _metric_std([row["lpips"] for row in method_rows]),
                "mse_mean": _metric_mean([row["mse"] for row in method_rows]),
                "mse_std": _metric_std([row["mse"] for row in method_rows]),
                "ssim_mean": _metric_mean([row["ssim"] for row in method_rows]),
                "ssim_std": _metric_std([row["ssim"] for row in method_rows]),
                "structure_distance_mean": _metric_mean([row["structure_distance"] for row in method_rows]),
                "structure_distance_std": _metric_std([row["structure_distance"] for row in method_rows]),
                "psnr_unedit_part_mean": _metric_mean([row["psnr_unedit_part"] for row in method_rows]),
                "psnr_unedit_part_std": _metric_std([row["psnr_unedit_part"] for row in method_rows]),
                "lpips_unedit_part_mean": _metric_mean([row["lpips_unedit_part"] for row in method_rows]),
                "lpips_unedit_part_std": _metric_std([row["lpips_unedit_part"] for row in method_rows]),
                "mse_unedit_part_mean": _metric_mean([row["mse_unedit_part"] for row in method_rows]),
                "mse_unedit_part_std": _metric_std([row["mse_unedit_part"] for row in method_rows]),
                "ssim_unedit_part_mean": _metric_mean([row["ssim_unedit_part"] for row in method_rows]),
                "ssim_unedit_part_std": _metric_std([row["ssim_unedit_part"] for row in method_rows]),
                "structure_distance_unedit_part_mean": _metric_mean([row["structure_distance_unedit_part"] for row in method_rows]),
                "structure_distance_unedit_part_std": _metric_std([row["structure_distance_unedit_part"] for row in method_rows]),
                "locality_ratio_mean": _metric_mean([row["locality_ratio"] for row in method_rows]),
                "locality_ratio_std": _metric_std([row["locality_ratio"] for row in method_rows]),
            }
        )

    summary_table_path = run_dir / "metrics_overview_methods_summary.csv"
    save_csv_records(summary_table_path, summary_rows)
    save_json(run_dir / "metrics_overview_methods_summary.json", {"summary": summary_rows})
    return case_table_path, summary_table_path
