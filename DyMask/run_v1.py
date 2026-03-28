from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

import numpy as np
from PIL import Image

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from DyMask.adapters import build_stable_diffusion_pipeline
from DyMask.config import ExperimentConfig
from DyMask.data import MagicBrushParquetDataset
from DyMask.logging_utils import MarkdownExperimentLogger
from DyMask.metrics import MetricRunner
from DyMask.schemas import MaterializedSample, SampleManifestEntry
from DyMask.utils import compose_labeled_overview, make_timestamped_run_dir, save_csv_records, save_image, save_json
from DyMask.v1 import V1Editor


PHASE_METHODS = {
    "phase0": (),
    "phase1": ("target_only",),
    "phase2": ("target_only", "global_blend_0.3", "global_blend_0.5", "global_blend_0.7"),
    "phase3": ("discrepancy_only",),
    "phase4": ("discrepancy_attention",),
    "phase5": ("full_dynamic_mask",),
}

OVERVIEW_METHODS = (
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask",
)

METHOD_DISPLAY_NAMES = {
    "target_only": "target-only",
    "global_blend": "global blend",
    "discrepancy_only": "D_t",
    "discrepancy_attention": "D_t + A_t",
    "full_dynamic_mask": "Full",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run DyMask phased V1 experiments.")
    parser.add_argument("--parquet-path", default="assets/data/train-00000-of-00262-57cebf95b4a9170c.parquet")
    parser.add_argument("--sample-json", default=None, help="Rerun a single existing sample.json with its current prompts.")
    parser.add_argument("--output-root", default="runs/dymask_v1")
    parser.add_argument("--sample-count", type=int, default=8)
    parser.add_argument("--sample-seed", type=int, default=42)
    parser.add_argument("--row-indices", nargs="+", type=int, default=None, help="Use explicit parquet row indices instead of random sampling.")
    parser.add_argument("--run-limit", type=int, default=1)
    parser.add_argument("--model-id", default="runwayml/stable-diffusion-v1-5")
    parser.add_argument("--clip-model-id", default="openai/clip-vit-base-patch32")
    parser.add_argument("--image-size", type=int, default=512)
    parser.add_argument("--num-ddim-steps", type=int, default=10, help="Legacy alias: sets both inversion and edit steps unless overridden.")
    parser.add_argument("--num-inversion-steps", type=int, default=None)
    parser.add_argument("--num-edit-steps", type=int, default=None)
    parser.add_argument("--guidance-scale", type=float, default=7.5)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--dtype", default="float16")
    parser.add_argument("--allow-download", action="store_true")
    parser.add_argument("--skip-metrics", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--phase",
        choices=["phase0", "phase1", "phase2", "phase3", "phase4", "phase5", "custom"],
        default="custom",
    )
    parser.add_argument(
        "--methods",
        nargs="+",
        default=None,
        help="Only used when --phase custom.",
    )
    parser.add_argument("--mask-mode", choices=["dynamic", "static"], default="dynamic")
    parser.add_argument("--global-blend-alpha", type=float, default=0.45)
    parser.add_argument(
        "--global-blend-alphas",
        nargs="+",
        type=float,
        default=[0.3, 0.5, 0.7],
    )
    parser.add_argument("--selected-step-count", type=int, default=5)
    parser.add_argument("--save-inversion-tensors", action="store_true")
    return parser


def resolve_methods(args: argparse.Namespace) -> tuple[str, ...]:
    if args.phase != "custom":
        if args.phase == "phase2":
            return ("target_only", *tuple(f"global_blend_{alpha}" for alpha in args.global_blend_alphas))
        return PHASE_METHODS[args.phase]
    if args.methods:
        return tuple(args.methods)
    return (
        "target_only",
        "global_blend_0.3",
        "global_blend_0.5",
        "global_blend_0.7",
        "discrepancy_only",
        "discrepancy_attention",
        "full_dynamic_mask",
    )


def build_config(args: argparse.Namespace) -> ExperimentConfig:
    config = ExperimentConfig()
    legacy_steps = args.num_ddim_steps
    config.phase = args.phase
    config.sampling.parquet_path = Path(args.parquet_path)
    config.sampling.output_root = Path(args.output_root)
    config.sampling.sample_count = args.sample_count
    config.sampling.sample_seed = args.sample_seed
    config.sampling.run_limit = args.run_limit
    config.runtime.model_id = args.model_id
    config.runtime.clip_model_id = args.clip_model_id
    config.runtime.image_size = args.image_size
    config.runtime.num_inversion_steps = args.num_inversion_steps if args.num_inversion_steps is not None else legacy_steps
    config.runtime.num_edit_steps = args.num_edit_steps if args.num_edit_steps is not None else legacy_steps
    config.runtime.guidance_scale = args.guidance_scale
    config.runtime.device = args.device
    config.runtime.dtype = args.dtype
    config.runtime.local_files_only = not args.allow_download
    config.metrics.clip_local_files_only = not args.allow_download
    config.methods = resolve_methods(args)
    config.mask.mode = args.mask_mode
    config.mask.global_blend_alpha = args.global_blend_alpha
    config.mask.global_blend_alphas = tuple(args.global_blend_alphas)
    config.mask.selected_step_count = args.selected_step_count
    config.save_inversion_tensors = args.save_inversion_tensors or args.phase == "phase0"
    config.skip_metrics = args.skip_metrics
    config.dry_run = args.dry_run
    return config


def materialize_from_sample_json(sample_json_path: Path, output_dir: Path) -> tuple[list[MaterializedSample], list[SampleManifestEntry]]:
    payload = json.loads(sample_json_path.read_text(encoding="utf-8"))
    sample_id = payload["sample_id"]
    sample_dir = output_dir / sample_id
    sample_dir.mkdir(parents=True, exist_ok=True)

    source_source_path = Path(payload["source_image_path"])
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
    rewritten_payload["source_image_path"] = str(source_path)
    rewritten_payload["target_reference_path"] = rewritten_target_reference_path
    save_json(sample_dir / "sample.json", rewritten_payload)

    materialized_sample = MaterializedSample(
        sample_id=sample_id,
        row_index=int(payload["row_index"]),
        source_prompt=payload["source_prompt"],
        edit_prompt=payload["edit_prompt"],
        target_prompt=payload["target_prompt"],
        source_image_path=source_path,
        target_image_path=target_path if rewritten_target_reference_path else None,
        sample_dir=sample_dir,
        extras=payload.get("extras") or {},
    )
    manifest_entry = SampleManifestEntry(
        sample_id=sample_id,
        row_index=int(payload["row_index"]),
        source_prompt=payload["source_prompt"],
        edit_prompt=payload["edit_prompt"],
        target_prompt=payload["target_prompt"],
        source_image_path=str(source_path),
        target_image_path=rewritten_target_reference_path,
        record_id=payload.get("record_id"),
    )
    return [materialized_sample], [manifest_entry]


def phase_title(phase: str) -> str:
    titles = {
        "phase0": "Phase 0 反演与重建",
        "phase1": "Phase 1 target-only 编辑",
        "phase2": "Phase 2 全局融合基线",
        "phase3": "Phase 3 仅 D_t",
        "phase4": "Phase 4 D_t + A_t",
        "phase5": "Phase 5 D_t + A_t + C_t",
        "custom": "Custom 多方法运行",
    }
    return titles.get(phase, phase)


def canonical_method_name(method_name: str) -> str:
    return "global_blend" if method_name.startswith("global_blend") else method_name


def display_method_name(method_name: str) -> str:
    return METHOD_DISPLAY_NAMES.get(canonical_method_name(method_name), method_name)


def build_sample_overview(
    sample: MaterializedSample,
    method_results: list,
    image_size: int,
) -> Path | None:
    result_by_method = {
        canonical_method_name(result.method_name): result
        for result in method_results
    }
    if not all(method in result_by_method for method in OVERVIEW_METHODS):
        return None

    items: list[tuple[str, np.ndarray]] = [
        ("source", np.asarray(Image.open(sample.source_image_path).convert("RGB"))),
    ]
    for method_name in OVERVIEW_METHODS:
        result = result_by_method[method_name]
        items.append((display_method_name(method_name), np.asarray(Image.open(result.edited_image_path).convert("RGB"))))

    full_result = result_by_method["full_dynamic_mask"]
    if full_result.aux_summary_path is None or not Path(full_result.aux_summary_path).exists():
        return None
    items.append(("D/A/C/mask maps", np.asarray(Image.open(full_result.aux_summary_path).convert("RGB"))))

    overview = compose_labeled_overview(
        items,
        columns=4,
        tile_size=(image_size, image_size),
        title=sample.sample_id,
    )
    overview_path = sample.sample_dir / "overview.png"
    save_image(overview_path, overview)
    return overview_path


def _metric_mean(values: list[float | None]) -> float | None:
    numeric = [float(value) for value in values if value is not None]
    if not numeric:
        return None
    return float(np.mean(numeric))


def _metric_std(values: list[float | None]) -> float | None:
    numeric = [float(value) for value in values if value is not None]
    if not numeric:
        return None
    return float(np.std(numeric, ddof=0))


def write_five_method_metric_tables(run_dir: Path, case_rows: list[dict]) -> tuple[Path, Path]:
    ordered_methods = list(OVERVIEW_METHODS)
    filtered_rows: list[dict[str, object]] = []

    for row in case_rows:
        method_name = row.get("method_name")
        if not isinstance(method_name, str):
            continue
        canonical_name = canonical_method_name(method_name)
        if canonical_name not in OVERVIEW_METHODS:
            continue
        filtered_rows.append(
            {
                "sample_id": row.get("sample_id"),
                "method_name": display_method_name(canonical_name),
                "edit_reference_mode": row.get("edit_reference_mode"),
                "clip_score": row.get("clip_score"),
                "target_lpips": row.get("edit_ref_lpips"),
                "target_psnr": row.get("edit_ref_psnr"),
                "source_lpips": row.get("edit_source_lpips"),
                "source_psnr": row.get("edit_source_psnr"),
            }
        )

    filtered_rows.sort(
        key=lambda row: (
            str(row["sample_id"]),
            ordered_methods.index(next(name for name, label in METHOD_DISPLAY_NAMES.items() if label == row["method_name"])),
        )
    )

    case_table_path = run_dir / "metrics_five_methods_case_level.csv"
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
                "clip_score_mean": _metric_mean([row["clip_score"] for row in method_rows]),
                "clip_score_std": _metric_std([row["clip_score"] for row in method_rows]),
                "target_lpips_mean": _metric_mean([row["target_lpips"] for row in method_rows]),
                "target_lpips_std": _metric_std([row["target_lpips"] for row in method_rows]),
                "target_psnr_mean": _metric_mean([row["target_psnr"] for row in method_rows]),
                "target_psnr_std": _metric_std([row["target_psnr"] for row in method_rows]),
                "source_lpips_mean": _metric_mean([row["source_lpips"] for row in method_rows]),
                "source_lpips_std": _metric_std([row["source_lpips"] for row in method_rows]),
                "source_psnr_mean": _metric_mean([row["source_psnr"] for row in method_rows]),
                "source_psnr_std": _metric_std([row["source_psnr"] for row in method_rows]),
            }
        )

    summary_table_path = run_dir / "metrics_five_methods_summary.csv"
    save_csv_records(summary_table_path, summary_rows)
    save_json(run_dir / "metrics_five_methods_summary.json", {"summary": summary_rows})
    return case_table_path, summary_table_path


def main() -> None:
    args = build_parser().parse_args()
    config = build_config(args)
    run_dir = make_timestamped_run_dir(config.sampling.output_root, prefix=config.phase if config.phase != "custom" else "v1")
    logger = MarkdownExperimentLogger(Path("log.md"))

    sample_output_dir = run_dir / "samples"
    if args.sample_json:
        sample_json_path = Path(args.sample_json)
        materialized_samples, manifest = materialize_from_sample_json(sample_json_path, sample_output_dir)
        logger.log(
            stage="样本复跑",
            operation="从已有 sample.json 载入单样本并保留当前提示词",
            inputs={"sample_json": str(sample_json_path)},
            result={
                "sample_id": materialized_samples[0].sample_id,
                "source_prompt": materialized_samples[0].source_prompt,
                "target_prompt": materialized_samples[0].target_prompt,
                "run_dir": str(run_dir),
            },
            conclusion="将按 sample.json 当前内容复跑该样本，不再回源 parquet 覆盖提示词。",
            next_step="进入对应 phase 的单样本验证。",
        )
    else:
        dataset = MagicBrushParquetDataset(config.sampling.parquet_path)
        schema_info = dataset.inspect_schema()
        logger.log(
            stage="数据准备",
            operation="探测 parquet schema",
            inputs={"parquet_path": str(config.sampling.parquet_path)},
            result=schema_info,
            conclusion="已确认数据集字段结构，可用于 source/target 成对抽样。",
            next_step="抽样并固化 sample manifest。",
        )

        sampled_indices = dataset.sample_indices(config.sampling.sample_count, config.sampling.sample_seed)
        if args.row_indices:
            sampled_indices = [int(index) for index in args.row_indices]
        sampled_records = dataset.load_records(sampled_indices)
        materialized_samples, manifest = dataset.materialize_samples(
            sampled_records,
            sample_output_dir,
            config.runtime.image_size,
        )
    MagicBrushParquetDataset.write_manifest(run_dir, config.sampling.manifest_name, manifest)
    save_json(run_dir / "config.json", config.to_dict())
    logger.log(
        stage="样本抽样",
        operation="生成样本清单并导出缓存图片",
        inputs={
            "sample_count": config.sampling.sample_count,
            "sample_seed": config.sampling.sample_seed,
            "row_indices": args.row_indices,
            "phase": config.phase,
            "methods": list(config.methods),
        },
        result={
            "run_dir": str(run_dir),
            "manifest_json": str(run_dir / f"{config.sampling.manifest_name}.json"),
            "manifest_csv": str(run_dir / f"{config.sampling.manifest_name}.csv"),
            "sample_ids": [sample.sample_id for sample in materialized_samples],
        },
        conclusion="样本清单已冻结，后续所有阶段应复用同一批样本。",
        next_step="根据 phase 进入分阶段验证。",
    )

    if config.dry_run:
        logger.log(
            stage="执行控制",
            operation="dry-run 结束",
            inputs={"dry_run": True, "phase": config.phase},
            result={"run_dir": str(run_dir)},
            conclusion="本次仅验证数据抽样、样本留存和日志链路。",
            next_step="取消 dry-run 后再执行对应 phase。",
        )
        return

    pipe = build_stable_diffusion_pipeline(config.runtime)
    editor = V1Editor(pipe, config)
    metric_runner = None if config.skip_metrics else MetricRunner(config.runtime, config.metrics)

    case_rows: list[dict] = []
    run_samples = materialized_samples[: config.sampling.run_limit]
    for sample in run_samples:
        logger.log(
            stage=phase_title(config.phase),
            operation="开始执行单样本阶段验证",
            inputs={
                "sample_id": sample.sample_id,
                "source_prompt": sample.source_prompt,
                "edit_prompt": sample.edit_prompt,
                "target_prompt": sample.target_prompt,
                "methods": list(config.methods),
            },
            result={"sample_dir": str(sample.sample_dir)},
            conclusion="进入反演与阶段方法运行。",
            next_step="保存 reconstruction、方法结果和指标。",
        )

        inversion, method_results = editor.run_sample(sample)
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
            "reconstruction_path": str(sample.sample_dir / "source_reconstruction.png"),
            "zt_src_path": str(sample.sample_dir / "zt_src.pt") if config.save_inversion_tensors else None,
            "src_latents_path": str(sample.sample_dir / "src_latents.pt") if config.save_inversion_tensors else None,
        }
        if metric_runner is not None:
            phase0_metrics = {}
            if metric_runner.metric_config.enable_psnr:
                phase0_metrics["source_recon_psnr"] = metric_runner.compute_psnr(source_image, inversion.reconstruction_image)
            if metric_runner.metric_config.enable_lpips:
                try:
                    phase0_metrics["source_recon_lpips"] = metric_runner.compute_lpips(source_image, inversion.reconstruction_image)
                except Exception as exc:
                    phase0_metrics["source_recon_lpips"] = None
                    phase0_metrics["source_recon_lpips_error"] = str(exc)
            phase0_row.update(phase0_metrics)
        case_rows.append(phase0_row)

        for method_result in method_results:
            metrics = {}
            if metric_runner is not None and config.phase != "phase0":
                metrics = metric_runner.evaluate_case(
                    source_image=source_image,
                    reconstruction_image=inversion.reconstruction_image,
                    edited_image=method_result.edited_image,
                    target_text=sample.target_prompt,
                    reference_edited=target_reference,
                )
            method_result.metrics = metrics
            row = {
                "sample_id": sample.sample_id,
                "method_name": method_result.method_name,
                "source_prompt": sample.source_prompt,
                "edit_prompt": sample.edit_prompt,
                "target_prompt": sample.target_prompt,
                **metrics,
                "edited_image_path": str(method_result.edited_image_path),
                "mask_summary_path": str(method_result.mask_summary_path) if method_result.mask_summary_path else None,
                "aux_summary_path": str(method_result.aux_summary_path) if method_result.aux_summary_path else None,
                "delta_trace_path": str(method_result.delta_trace_path) if method_result.delta_trace_path else None,
                "diagnostics_csv_path": str(method_result.diagnostics_csv_path) if method_result.diagnostics_csv_path else None,
                "diagnostics_json_path": str(method_result.diagnostics_json_path) if method_result.diagnostics_json_path else None,
                "debug_json_path": str(method_result.debug_json_path),
            }
            case_rows.append(row)

        overview_path = build_sample_overview(sample, method_results, config.runtime.image_size)

        logger.log(
            stage=phase_title(config.phase),
            operation="单样本阶段验证完成",
            inputs={"sample_id": sample.sample_id, "phase": config.phase},
            result={
                "reconstruction_path": str(sample.sample_dir / "source_reconstruction.png"),
                "methods": [result.method_name for result in method_results],
                "artifacts": [str(result.edited_image_path) for result in method_results],
                "overview_path": str(overview_path) if overview_path else None,
            },
            conclusion="该样本已保存固定产物和阶段产物，可进入下一样本或汇总。",
            next_step="继续剩余样本，或检查 summary 指标和中间图。",
        )

    metrics_path = run_dir / "metrics_case_level.csv"
    save_csv_records(metrics_path, case_rows)
    summary_rows = []
    if metric_runner is not None:
        summary_rows = metric_runner.summarize(case_rows)
        save_csv_records(run_dir / "metrics_summary.csv", summary_rows)
        save_json(run_dir / "metrics_summary.json", {"summary": summary_rows})
    five_method_case_table_path, five_method_summary_table_path = write_five_method_metric_tables(run_dir, case_rows)

    logger.log(
        stage="实验汇总",
        operation="落盘阶段 case-level 与 summary 指标",
        inputs={
            "phase": config.phase,
            "run_limit": config.sampling.run_limit,
            "methods": list(config.methods),
        },
        result={
            "case_metrics_csv": str(metrics_path),
            "summary_metrics_csv": str(run_dir / "metrics_summary.csv"),
            "summary_metrics_json": str(run_dir / "metrics_summary.json"),
            "five_method_case_metrics_csv": str(five_method_case_table_path),
            "five_method_summary_metrics_csv": str(five_method_summary_table_path),
        },
        conclusion="当前阶段的可视化、指标、日志和样本留存已齐备。",
        next_step="按顺序进入下一阶段，而不是一次性堆叠所有模块。",
    )


if __name__ == "__main__":
    main()
