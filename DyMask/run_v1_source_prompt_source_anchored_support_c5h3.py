from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from DyMask.data import MagicBrushParquetDataset, PIEBenchDataset
from DyMask.diffedit import DiffEditConfig
from DyMask.logging_utils import MarkdownExperimentLogger
from DyMask.metrics import MetricRunner
from DyMask.nti_inversion import NTIInversionBackend
from DyMask.run_v1 import (
    build_config,
    build_parser,
    build_run_overview,
    build_sample_overview,
    materialize_from_sample_json,
    resolve_overview_methods,
    write_overview_method_metric_tables,
)
from DyMask.run_v1_source_prompt_hard_roi_locked import (
    _build_stable_diffusion_pipeline_safe,
    _has_output_root_arg,
)
from DyMask.utils import make_timestamped_run_dir, save_csv_records, save_json
from DyMask.v1_source_prompt_source_anchored_support_c5h3 import V1SourcePromptSourceAnchoredSupportC5H3Editor


def main(argv: list[str] | None = None) -> None:
    argv_list = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    parser.add_argument("--num-maps-per-mask", type=int, default=10)
    parser.add_argument("--mask-encode-strength", type=float, default=0.5)
    parser.add_argument("--mask-thresholding-ratio", type=float, default=3.0)
    parser.add_argument("--inpaint-strength", type=float, default=1.0)
    parser.add_argument("--support-rho", type=float, default=0.70)
    parser.add_argument("--anchor-relax-start-strength", type=float, default=0.35)
    parser.add_argument("--anchor-relax-end-strength", type=float, default=0.05)
    parser.add_argument("--core-read-start-weight", type=float, default=0.45)
    parser.add_argument("--core-read-end-weight", type=float, default=0.08)
    parser.add_argument("--boundary-read-start-weight", type=float, default=0.20)
    parser.add_argument("--boundary-read-end-weight", type=float, default=0.04)
    parser.add_argument("--boundary-anchor-start-weight", type=float, default=0.18)
    parser.add_argument("--boundary-anchor-end-weight", type=float, default=0.04)
    parser.add_argument("--boundary-confidence-weight", type=float, default=0.30)
    parser.add_argument("--roi-core-quantile", type=float, default=0.80)
    parser.add_argument("--roi-core-peak-ratio", type=float, default=0.60)
    parser.add_argument("--roi-core-threshold-min", type=float, default=0.15)
    parser.add_argument("--roi-core-threshold-max", type=float, default=0.50)
    parser.add_argument("--roi-core-min-active-ratio", type=float, default=0.05)
    parser.add_argument("--roi-core-active-floor", type=float, default=0.05)
    parser.add_argument("--roi-seed-offset", type=int, default=0)
    parser.add_argument("--roi-cache-root", type=str, default="runs/diffedit_roi_cache/source_prompt_c5h2")
    parser.add_argument("--underedit-support-gain", type=float, default=0.45)
    parser.add_argument("--underedit-mask-gain", type=float, default=0.20)
    parser.add_argument("--underedit-anchor-gain", type=float, default=0.30)
    parser.add_argument("--underedit-eps", type=float, default=1e-6)
    args = parser.parse_args(argv_list)
    if not _has_output_root_arg(argv_list):
        args.output_root = "scratch_source_anchor_runs/dymask_v1_source_prompt_source_anchored_support_c5h3"

    config = build_config(args)
    run_prefix = (
        f"{config.phase}_source_prompt_source_anchored_support_c5h3"
        if config.phase != "custom"
        else "v1_source_prompt_source_anchored_support_c5h3"
    )
    run_dir = make_timestamped_run_dir(config.sampling.output_root, prefix=run_prefix)
    logger = MarkdownExperimentLogger(Path("log_source_anchored_support_c5h3.md"))
    diffedit_config = DiffEditConfig(
        num_maps_per_mask=args.num_maps_per_mask,
        mask_encode_strength=args.mask_encode_strength,
        mask_thresholding_ratio=args.mask_thresholding_ratio,
        inpaint_strength=args.inpaint_strength,
    )

    save_json(
        run_dir / "variant.json",
        {
            "variant_name": "source_prompt_source_anchored_support_c5h3_underedit_rescue_v1",
            "ddim_inversion_prompt_mode": "source_prompt",
            "reference_branch_prompt_mode": "source_prompt",
            "attention_prompt_mode": "target_prompt",
            "support_rho": float(args.support_rho),
            "anchor_relax_start_strength": float(args.anchor_relax_start_strength),
            "anchor_relax_end_strength": float(args.anchor_relax_end_strength),
            "core_read_start_weight": float(args.core_read_start_weight),
            "core_read_end_weight": float(args.core_read_end_weight),
            "boundary_read_start_weight": float(args.boundary_read_start_weight),
            "boundary_read_end_weight": float(args.boundary_read_end_weight),
            "boundary_anchor_start_weight": float(args.boundary_anchor_start_weight),
            "boundary_anchor_end_weight": float(args.boundary_anchor_end_weight),
            "boundary_confidence_weight": float(args.boundary_confidence_weight),
            "roi_core_quantile": float(args.roi_core_quantile),
            "roi_core_peak_ratio": float(args.roi_core_peak_ratio),
            "roi_core_threshold_min": float(args.roi_core_threshold_min),
            "roi_core_threshold_max": float(args.roi_core_threshold_max),
            "roi_core_min_active_ratio": float(args.roi_core_min_active_ratio),
            "roi_core_active_floor": float(args.roi_core_active_floor),
            "roi_seed_offset": int(args.roi_seed_offset),
            "roi_cache_root": str(args.roi_cache_root),
            "underedit_support_gain": float(args.underedit_support_gain),
            "underedit_mask_gain": float(args.underedit_mask_gain),
            "underedit_anchor_gain": float(args.underedit_anchor_gain),
            "underedit_eps": float(args.underedit_eps),
            "mechanism": (
                "Keep the deterministic C5H2 core-boundary support path, then inject an under-edit pressure map "
                "r_t = roi_soft * dynamic_mask * relu(g_src_tar - g_applied)/(g_src_tar + eps) to boost support evidence, "
                "expand the effective write mask, and locally relax source anchoring where the target branch is still under-applied."
            ),
            "support_update": (
                "phi'_t = clamp(phi_t + lambda_s * r_t, 0, 1); "
                "S_t = rho * S_{t-1} + (1-rho) * phi'_t"
            ),
            "adaptive_mask": (
                "M'_t = clamp(M_t + lambda_m * r_t, 0, 1), where M_t keeps the C5H2 core-boundary readout"
            ),
            "background_anchor": (
                "A''_t = lerp(A'_t, 1, lambda_a * r_t), where A'_t is the C5H2 confidence-relaxed anchor mask"
            ),
            "diffedit": diffedit_config.to_dict(),
        },
    )

    sample_output_dir = run_dir / "samples"
    if args.sample_json:
        materialized_samples, manifest = materialize_from_sample_json(Path(args.sample_json), sample_output_dir)
    else:
        if config.sampling.piebench_path is not None:
            dataset = PIEBenchDataset(config.sampling.piebench_path)
        else:
            dataset = MagicBrushParquetDataset(config.sampling.parquet_path)
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
        stage="source_prompt_source_anchored_support_c5h3",
        operation="prepare run",
        inputs={
            "phase": config.phase,
            "methods": list(config.methods),
            "run_dir": str(run_dir),
            "support_rho": float(args.support_rho),
            "anchor_relax_start_strength": float(args.anchor_relax_start_strength),
            "anchor_relax_end_strength": float(args.anchor_relax_end_strength),
            "core_read_start_weight": float(args.core_read_start_weight),
            "core_read_end_weight": float(args.core_read_end_weight),
            "boundary_read_start_weight": float(args.boundary_read_start_weight),
            "boundary_read_end_weight": float(args.boundary_read_end_weight),
            "boundary_anchor_start_weight": float(args.boundary_anchor_start_weight),
            "boundary_anchor_end_weight": float(args.boundary_anchor_end_weight),
            "boundary_confidence_weight": float(args.boundary_confidence_weight),
            "roi_core_quantile": float(args.roi_core_quantile),
            "roi_core_peak_ratio": float(args.roi_core_peak_ratio),
            "roi_core_threshold_min": float(args.roi_core_threshold_min),
            "roi_core_threshold_max": float(args.roi_core_threshold_max),
            "roi_core_min_active_ratio": float(args.roi_core_min_active_ratio),
            "roi_core_active_floor": float(args.roi_core_active_floor),
            "roi_seed_offset": int(args.roi_seed_offset),
            "roi_cache_root": str(args.roi_cache_root),
            "underedit_support_gain": float(args.underedit_support_gain),
            "underedit_mask_gain": float(args.underedit_mask_gain),
            "underedit_anchor_gain": float(args.underedit_anchor_gain),
            "underedit_eps": float(args.underedit_eps),
            "diffedit": diffedit_config.to_dict(),
        },
        result={"sample_ids": [sample.sample_id for sample in materialized_samples]},
        conclusion="samples and C5H3 under-edit rescue config saved",
        next_step="run inversion and editing",
    )

    if config.dry_run:
        return

    pipe = _build_stable_diffusion_pipeline_safe(config.runtime)
    inversion_backend = None
    if config.runtime.inversion_backend == "nti":
        inversion_backend = NTIInversionBackend(pipe, config.runtime)
    editor = V1SourcePromptSourceAnchoredSupportC5H3Editor(
        pipe,
        config,
        support_rho=args.support_rho,
        anchor_relax_start_strength=args.anchor_relax_start_strength,
        anchor_relax_end_strength=args.anchor_relax_end_strength,
        core_read_start_weight=args.core_read_start_weight,
        core_read_end_weight=args.core_read_end_weight,
        boundary_read_start_weight=args.boundary_read_start_weight,
        boundary_read_end_weight=args.boundary_read_end_weight,
        boundary_anchor_start_weight=args.boundary_anchor_start_weight,
        boundary_anchor_end_weight=args.boundary_anchor_end_weight,
        boundary_confidence_weight=args.boundary_confidence_weight,
        roi_core_quantile=args.roi_core_quantile,
        roi_core_peak_ratio=args.roi_core_peak_ratio,
        roi_core_threshold_min=args.roi_core_threshold_min,
        roi_core_threshold_max=args.roi_core_threshold_max,
        roi_core_min_active_ratio=args.roi_core_min_active_ratio,
        roi_core_active_floor=args.roi_core_active_floor,
        roi_seed_offset=args.roi_seed_offset,
        roi_cache_root=args.roi_cache_root,
        underedit_support_gain=args.underedit_support_gain,
        underedit_mask_gain=args.underedit_mask_gain,
        underedit_anchor_gain=args.underedit_anchor_gain,
        underedit_eps=args.underedit_eps,
        diffedit_config=diffedit_config,
        inversion_backend=inversion_backend,
    )
    metric_runner = None if config.skip_metrics else MetricRunner(config.runtime, config.metrics)

    overview_methods = resolve_overview_methods(config.methods)
    case_rows: list[dict] = []
    run_samples = materialized_samples[: config.sampling.run_limit]
    batch_results = editor.run_samples(run_samples)

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
            "source_recon_psnr": metric_runner.compute_psnr(source_image, inversion.reconstruction_image)
            if metric_runner is not None
            else None,
            "source_reconstruction_path": str(sample.sample_dir / "source_reconstruction.png"),
        }
        if metric_runner is not None:
            try:
                phase0_row["source_recon_lpips"] = metric_runner.compute_lpips(source_image, inversion.reconstruction_image)
            except Exception as exc:
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
                "variant": "source_prompt_source_anchored_support_c5h3_underedit_rescue_v1",
            }
            if metric_runner is not None:
                metrics_row = metric_runner.evaluate_case(
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

    save_csv_records(run_dir / "metrics_case_level.csv", case_rows)
    if metric_runner is not None:
        save_csv_records(run_dir / "metrics_summary.csv", metric_runner.summarize(case_rows))
        write_overview_method_metric_tables(run_dir, case_rows, overview_methods)

    for sample in run_samples:
        _inversion, method_results = batch_results[sample.sample_id]
        build_sample_overview(sample, method_results, config.runtime.image_size, overview_methods)
    build_run_overview(run_dir, run_samples)

    logger.log(
        stage="source_prompt_source_anchored_support_c5h3",
        operation="complete run",
        inputs={"run_dir": str(run_dir)},
        result={
            "case_metrics_csv": str(run_dir / "metrics_case_level.csv"),
            "summary_csv": str(run_dir / "metrics_summary.csv") if metric_runner is not None else None,
        },
        conclusion="C5H3 under-edit rescue run finished",
        next_step=(
            "inspect whether the under-edit pressure map recovers the DiffEdit-loss cases without giving back too much preservation"
        ),
    )


if __name__ == "__main__":
    main()
