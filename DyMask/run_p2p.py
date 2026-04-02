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
from DyMask.p2p import P2PConfig, P2PEditor
from DyMask.run_v1 import build_config, build_parser, materialize_from_sample_json
from DyMask.utils import compose_labeled_overview, make_timestamped_run_dir, save_csv_records, save_image, save_json
from DyMask.v1_source_prompt import SourcePromptDDIMInversionBackend


def _has_output_root_arg(argv: list[str]) -> bool:
    return any(arg == "--output-root" or arg.startswith("--output-root=") for arg in argv)


def _build_parser():
    parser = build_parser()
    parser.add_argument("--controller-mode", choices=["replace", "refine"], default="replace")
    parser.add_argument("--cross-replace-steps", type=float, default=0.8)
    parser.add_argument("--self-replace-steps", type=float, default=0.5)
    parser.add_argument("--blend-words-source", nargs="+", default=None)
    parser.add_argument("--blend-words-target", nargs="+", default=None)
    parser.add_argument("--equalizer-words", nargs="+", default=None)
    parser.add_argument("--equalizer-values", nargs="+", type=float, default=None)
    return parser


def _build_sample_overview(sample, inversion, method_result, image_size: int) -> Path:
    items: list[tuple[str, np.ndarray]] = [
        ("source", np.asarray(Image.open(sample.source_image_path).convert("RGB"))),
        ("reconstruction", inversion.reconstruction_image),
        ("edited", np.asarray(Image.open(method_result.edited_image_path).convert("RGB"))),
    ]
    source_render_path = method_result.edited_image_path.parent / "source_render.png"
    if source_render_path.exists():
        items.insert(2, ("p2p source", np.asarray(Image.open(source_render_path).convert("RGB"))))
    if sample.target_image_path is not None and Path(sample.target_image_path).exists():
        items.append(("target reference", np.asarray(Image.open(sample.target_image_path).convert("RGB"))))
    if method_result.mask_summary_path is not None and Path(method_result.mask_summary_path).exists():
        items.append(("attention", np.asarray(Image.open(method_result.mask_summary_path).convert("RGB"))))
    overview = compose_labeled_overview(
        items,
        columns=min(3, len(items)),
        tile_size=(image_size, image_size),
        title=sample.sample_id,
    )
    overview_path = sample.sample_dir / "overview.png"
    save_image(overview_path, overview)
    return overview_path


def _build_run_overview(run_dir: Path, samples) -> Path | None:
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
    run_overview_path = run_dir / "overview_all_samples.png"
    save_image(run_overview_path, overview)
    return run_overview_path


def main(argv: list[str] | None = None) -> None:
    argv_list = list(sys.argv[1:] if argv is None else argv)
    parser = _build_parser()
    args = parser.parse_args(argv_list)
    if not _has_output_root_arg(argv_list):
        args.output_root = str(Path(__file__).resolve().parents[1] / "samples" / "p2p_runs")

    config = build_config(args)
    config.methods = ("p2p",)
    p2p_config = P2PConfig(
        controller_mode=args.controller_mode,
        cross_replace_steps=args.cross_replace_steps,
        self_replace_steps=args.self_replace_steps,
        blend_words_source=tuple(args.blend_words_source or ()),
        blend_words_target=tuple(args.blend_words_target or ()),
        equalizer_words=tuple(args.equalizer_words or ()),
        equalizer_values=tuple(float(value) for value in (args.equalizer_values or ())),
    )

    run_dir = make_timestamped_run_dir(Path(args.output_root), prefix="p2p")
    logger = MarkdownExperimentLogger(run_dir / "log.md")
    save_json(
        run_dir / "variant.json",
        {
            "variant_name": "prompt_to_prompt",
            "editing_rule": "classic_prompt_to_prompt",
            "default_inversion_backend": config.runtime.inversion_backend,
        },
    )
    save_json(
        run_dir / "config.json",
        {
            "experiment": config.to_dict(),
            "p2p": p2p_config.to_dict(),
        },
    )

    sample_output_dir = run_dir / "samples"
    if args.sample_json:
        sample_json_path = Path(args.sample_json)
        materialized_samples, manifest = materialize_from_sample_json(sample_json_path, sample_output_dir)
        logger.log(
            stage="样本复跑",
            operation="从已有 sample.json 载入单样本并运行 Prompt-to-Prompt 基线",
            inputs={"sample_json": str(sample_json_path)},
            result={
                "sample_id": materialized_samples[0].sample_id,
                "run_dir": str(run_dir),
                "variant": "prompt_to_prompt",
            },
            conclusion="将复用 sample.json 当前提示词，并运行纯 Prompt-to-Prompt 编辑。",
            next_step="进入单样本 P2P 验证。",
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
    logger.log(
        stage="样本抽样",
        operation="生成 P2P 样本清单并导出缓存图片",
        inputs={
            "sample_count": config.sampling.sample_count,
            "sample_seed": config.sampling.sample_seed,
            "row_indices": args.row_indices,
        },
        result={
            "run_dir": str(run_dir),
            "manifest_json": str(run_dir / f"{config.sampling.manifest_name}.json"),
            "manifest_csv": str(run_dir / f"{config.sampling.manifest_name}.csv"),
            "sample_ids": [sample.sample_id for sample in materialized_samples],
            "variant": "prompt_to_prompt",
        },
        conclusion="样本清单已冻结，后续对比应复用同一批样本。",
        next_step="运行 Prompt-to-Prompt 与现有方法做并排对比。",
    )

    if config.dry_run:
        logger.log(
            stage="执行控制",
            operation="P2P dry-run 结束",
            inputs={"dry_run": True, "variant": "prompt_to_prompt"},
            result={"run_dir": str(run_dir)},
            conclusion="本次仅验证数据抽样、样本留存和日志链路。",
            next_step="取消 dry-run 后再执行真实 P2P 编辑。",
        )
        return

    pipe = build_stable_diffusion_pipeline(config.runtime)
    if config.runtime.inversion_backend == "nti":
        inversion_backend = NTIInversionBackend(pipe, config.runtime)
    else:
        inversion_backend = SourcePromptDDIMInversionBackend(pipe, config.runtime)
    editor = P2PEditor(
        pipe=pipe,
        config=config,
        p2p_config=p2p_config,
        inversion_backend=inversion_backend,
    )
    metric_runner = None if config.skip_metrics else MetricRunner(config.runtime, config.metrics)

    case_rows: list[dict] = []
    run_samples = materialized_samples[: config.sampling.run_limit]
    batch_results = editor.run_samples(run_samples)
    for sample in run_samples:
        inversion, method_results = batch_results[sample.sample_id]
        method_result = method_results[0]

        logger.log(
            stage="Prompt-to-Prompt",
            operation="执行单样本 P2P 基线",
            inputs={
                "sample_id": sample.sample_id,
                "source_prompt": sample.source_prompt,
                "edit_prompt": sample.edit_prompt,
                "target_prompt": sample.target_prompt,
                "variant": "prompt_to_prompt",
            },
            result={"sample_dir": str(sample.sample_dir)},
            conclusion="进入现有 inversion + Prompt-to-Prompt 编辑流程。",
            next_step="保存 reconstruction、edited、attention 与指标。",
        )

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
            "variant": "prompt_to_prompt",
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

        metrics = {}
        if metric_runner is not None:
            metrics = metric_runner.evaluate_case(
                source_image=source_image,
                reconstruction_image=inversion.reconstruction_image,
                edited_image=method_result.edited_image,
                target_text=sample.target_prompt,
                reference_edited=target_reference,
                gt_mask=sample.gt_mask,
            )
        method_result.metrics = metrics
        case_rows.append(
            {
                "sample_id": sample.sample_id,
                "method_name": "p2p",
                "source_prompt": sample.source_prompt,
                "edit_prompt": sample.edit_prompt,
                "target_prompt": sample.target_prompt,
                "variant": "prompt_to_prompt",
                **metrics,
                "edited_image_path": str(method_result.edited_image_path),
                "mask_summary_path": str(method_result.mask_summary_path) if method_result.mask_summary_path else None,
                "aux_summary_path": str(method_result.aux_summary_path) if method_result.aux_summary_path else None,
                "delta_trace_path": None,
                "diagnostics_csv_path": str(method_result.diagnostics_csv_path) if method_result.diagnostics_csv_path else None,
                "diagnostics_json_path": str(method_result.diagnostics_json_path) if method_result.diagnostics_json_path else None,
                "debug_json_path": str(method_result.debug_json_path),
            }
        )

        overview_path = _build_sample_overview(sample, inversion, method_result, config.runtime.image_size)
        logger.log(
            stage="Prompt-to-Prompt",
            operation="单样本 P2P 完成",
            inputs={"sample_id": sample.sample_id, "variant": "prompt_to_prompt"},
            result={
                "reconstruction_path": str(sample.sample_dir / "source_reconstruction.png"),
                "edited_image_path": str(method_result.edited_image_path),
                "attention_summary_path": str(method_result.mask_summary_path) if method_result.mask_summary_path else None,
                "overview_path": str(overview_path),
            },
            conclusion="该样本已保存 P2P 产物，可与现有方法做并排对比。",
            next_step="继续剩余样本，或检查指标汇总。",
        )

    metrics_path = run_dir / "metrics_case_level.csv"
    save_csv_records(metrics_path, case_rows)
    summary_rows = []
    if metric_runner is not None:
        summary_rows = metric_runner.summarize(case_rows)
        save_csv_records(run_dir / "metrics_summary.csv", summary_rows)
        save_json(run_dir / "metrics_summary.json", {"summary": summary_rows})
    run_overview_path = _build_run_overview(run_dir, run_samples)

    logger.log(
        stage="实验汇总",
        operation="落盘 P2P case-level 与 summary 指标",
        inputs={"run_limit": config.sampling.run_limit, "variant": "prompt_to_prompt"},
        result={
            "case_metrics_csv": str(metrics_path),
            "summary_metrics_csv": str(run_dir / "metrics_summary.csv"),
            "summary_metrics_json": str(run_dir / "metrics_summary.json"),
            "overview_all_samples_path": str(run_overview_path) if run_overview_path else None,
            "variant_json": str(run_dir / "variant.json"),
        },
        conclusion="Prompt-to-Prompt 基线结果已经完整落盘。",
        next_step="和 run_v1 / run_v1_source_prompt / run_diffedit 对同一批样本做 A/B 对比。",
    )


if __name__ == "__main__":
    main()
