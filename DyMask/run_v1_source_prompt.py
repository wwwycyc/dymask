from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from DyMask.adapters import build_stable_diffusion_pipeline
from DyMask.data import MagicBrushParquetDataset, PIEBenchDataset
from DyMask.logging_utils import MarkdownExperimentLogger
from DyMask.metrics import MetricRunner
from DyMask.nti_inversion import NTIInversionBackend
from DyMask.run_v1 import (
    build_config,
    build_parser,
    build_run_overview,
    build_sample_overview,
    materialize_from_sample_json,
    phase_title,
    resolve_overview_methods,
    write_overview_method_metric_tables,
)
from DyMask.utils import make_timestamped_run_dir, save_csv_records, save_json
from DyMask.v1_source_prompt import V1SourcePromptEditor


def _has_output_root_arg(argv: list[str]) -> bool:
    return any(arg == "--output-root" or arg.startswith("--output-root=") for arg in argv)


def main(argv: list[str] | None = None) -> None:
    argv_list = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(argv_list)
    if not _has_output_root_arg(argv_list):
        args.output_root = "runs/dymask_v1_source_prompt"

    config = build_config(args)
    run_prefix = f"{config.phase}_source_prompt" if config.phase != "custom" else "v1_source_prompt"
    run_dir = make_timestamped_run_dir(config.sampling.output_root, prefix=run_prefix)
    logger = MarkdownExperimentLogger(Path("log.md"))

    save_json(
        run_dir / "variant.json",
        {
            "variant_name": "source_prompt_v1",
            "ddim_inversion_prompt_mode": "source_prompt",
            "reference_branch_prompt_mode": "source_prompt",
            "attention_prompt_mode": "target_prompt",
        },
    )

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
                "variant": "source_prompt_v1",
            },
            conclusion="将按 sample.json 当前内容复跑该样本，并在反演与参考分支使用 source prompt。",
            next_step="进入对应 phase 的单样本验证。",
        )
    else:
        if config.sampling.piebench_path is not None:
            dataset = PIEBenchDataset(config.sampling.piebench_path)
            schema_info = {"dataset": "PIE-Bench", "path": str(config.sampling.piebench_path)}
            logger.log(
                stage="数据准备",
                operation="加载 PIE-Bench 数据集",
                inputs={"piebench_path": str(config.sampling.piebench_path)},
                result=schema_info,
                conclusion="已确认 PIE-Bench 数据集，将使用 GT mask 计算 masked 指标。",
                next_step="抽样并固化 sample manifest。",
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
            "variant": "source_prompt_v1",
        },
        conclusion="样本清单已冻结，后续所有阶段应复用同一批样本。",
        next_step="根据 phase 进入分阶段验证。",
    )

    if config.dry_run:
        logger.log(
            stage="执行控制",
            operation="dry-run 结束",
            inputs={"dry_run": True, "phase": config.phase, "variant": "source_prompt_v1"},
            result={"run_dir": str(run_dir)},
            conclusion="本次仅验证数据抽样、样本留存和日志链路。",
            next_step="取消 dry-run 后再执行对应 phase。",
        )
        return

    pipe = build_stable_diffusion_pipeline(config.runtime)
    inversion_backend = None
    if config.runtime.inversion_backend == "nti":
        inversion_backend = NTIInversionBackend(pipe, config.runtime)
    editor = V1SourcePromptEditor(pipe, config, inversion_backend=inversion_backend)
    metric_runner = None if config.skip_metrics else MetricRunner(config.runtime, config.metrics)

    overview_methods = resolve_overview_methods(config.methods)
    case_rows: list[dict] = []
    run_samples = materialized_samples[: config.sampling.run_limit]
    batch_results = editor.run_samples(run_samples)
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
                "variant": "source_prompt_v1",
            },
            result={"sample_dir": str(sample.sample_dir)},
            conclusion="进入反演与阶段方法运行。",
            next_step="保存 reconstruction、方法结果和指标。",
        )

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
            "variant": "source_prompt_v1",
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
                    source_text=sample.source_prompt,
                    target_text=sample.target_prompt,
                    reference_edited=target_reference,
                    gt_mask=sample.gt_mask,
                )
            method_result.metrics = metrics
            row = {
                "sample_id": sample.sample_id,
                "method_name": method_result.method_name,
                "source_prompt": sample.source_prompt,
                "edit_prompt": sample.edit_prompt,
                "target_prompt": sample.target_prompt,
                "variant": "source_prompt_v1",
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

        overview_path = build_sample_overview(sample, method_results, config.runtime.image_size, overview_methods)

        logger.log(
            stage=phase_title(config.phase),
            operation="单样本阶段验证完成",
            inputs={"sample_id": sample.sample_id, "phase": config.phase, "variant": "source_prompt_v1"},
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
    overview_method_case_table_path, overview_method_summary_table_path = write_overview_method_metric_tables(
        run_dir,
        case_rows,
        overview_methods,
    )
    run_overview_path = build_run_overview(run_dir, run_samples)

    logger.log(
        stage="实验汇总",
        operation="落盘阶段 case-level 与 summary 指标",
        inputs={
            "phase": config.phase,
            "run_limit": config.sampling.run_limit,
            "methods": list(config.methods),
            "variant": "source_prompt_v1",
        },
        result={
            "case_metrics_csv": str(metrics_path),
            "summary_metrics_csv": str(run_dir / "metrics_summary.csv"),
            "summary_metrics_json": str(run_dir / "metrics_summary.json"),
            "overview_method_case_metrics_csv": str(overview_method_case_table_path),
            "overview_method_summary_metrics_csv": str(overview_method_summary_table_path),
            "overview_all_samples_path": str(run_overview_path) if run_overview_path else None,
            "variant_json": str(run_dir / "variant.json"),
        },
        conclusion="当前阶段的可视化、指标、日志和样本留存已齐备。",
        next_step="用同一批 sample 对比基线 run_v1 与 source_prompt 变体。",
    )


if __name__ == "__main__":
    main()
