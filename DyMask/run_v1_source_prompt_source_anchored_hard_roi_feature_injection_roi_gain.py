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
from DyMask.roi_edit_gain import FIELD_SOURCES, RoiEditGainFieldConfig
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
from DyMask.source_feature_injection import SourceDecoderFeatureInjectionConfig
from DyMask.utils import make_timestamped_run_dir, save_csv_records, save_json
from DyMask.v1_source_prompt_source_anchored_hard_roi_feature_injection_roi_gain import (
    V1SourcePromptSourceAnchoredHardRoiFeatureInjectionRoiGainEditor,
)


def main(argv: list[str] | None = None) -> None:
    argv_list = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    parser.add_argument("--num-maps-per-mask", type=int, default=10)
    parser.add_argument("--mask-encode-strength", type=float, default=0.5)
    parser.add_argument("--mask-thresholding-ratio", type=float, default=3.0)
    parser.add_argument("--inpaint-strength", type=float, default=1.0)

    parser.add_argument("--disable-feature-injection", action="store_true")
    parser.add_argument("--inject-start-ratio", type=float, default=0.25)
    parser.add_argument("--inject-end-ratio", type=float, default=0.75)
    parser.add_argument("--inject-strength", type=float, default=0.15)
    parser.add_argument("--inject-up-blocks", nargs="+", type=int, default=[2, 3])
    parser.add_argument("--inject-resnets", nargs="+", type=int, default=[0, 1, 2])

    parser.add_argument("--disable-roi-gain-field", action="store_true")
    parser.add_argument("--gain-source", choices=FIELD_SOURCES, default="dynamic_mask")
    parser.add_argument("--gain-start-ratio", type=float, default=0.25)
    parser.add_argument("--gain-end-ratio", type=float, default=0.85)
    parser.add_argument("--gain-threshold", type=float, default=0.50)
    parser.add_argument("--gain-temperature", type=float, default=8.0)
    parser.add_argument("--gain-smoothing-kernel", type=int, default=1)
    parser.add_argument("--gain-min-scale", type=float, default=1.0)
    parser.add_argument("--gain-max-scale", type=float, default=1.35)
    parser.add_argument("--gain-discrepancy-weight", type=float, default=1.0)
    parser.add_argument("--gain-attention-weight", type=float, default=0.5)
    parser.add_argument("--gain-latent-drift-weight", type=float, default=-0.5)

    args = parser.parse_args(argv_list)
    if not _has_output_root_arg(argv_list):
        args.output_root = "scratch_source_anchor_feature_inject_roi_gain_runs/sp_anchor_feat_inject_roi_gain"

    config = build_config(args)
    run_prefix = (
        f"{config.phase}_sp_anchor_feat_inject_roi_gain"
        if config.phase != "custom"
        else "sp_anchor_feat_inject_roi_gain"
    )
    run_dir = make_timestamped_run_dir(config.sampling.output_root, prefix=run_prefix)
    logger = MarkdownExperimentLogger(Path("log_source_anchored_hard_roi_feature_injection_roi_gain.md"))
    diffedit_config = DiffEditConfig(
        num_maps_per_mask=args.num_maps_per_mask,
        mask_encode_strength=args.mask_encode_strength,
        mask_thresholding_ratio=args.mask_thresholding_ratio,
        inpaint_strength=args.inpaint_strength,
    )
    injection_config = SourceDecoderFeatureInjectionConfig(
        start_ratio=float(args.inject_start_ratio),
        end_ratio=float(args.inject_end_ratio),
        strength=float(args.inject_strength),
        up_block_indices=tuple(int(item) for item in args.inject_up_blocks),
        resnet_indices=tuple(int(item) for item in args.inject_resnets),
    )
    gain_config = RoiEditGainFieldConfig(
        enabled=not args.disable_roi_gain_field,
        source=str(args.gain_source),
        start_ratio=float(args.gain_start_ratio),
        end_ratio=float(args.gain_end_ratio),
        threshold=float(args.gain_threshold),
        temperature=float(args.gain_temperature),
        smoothing_kernel=int(args.gain_smoothing_kernel),
        min_scale=float(args.gain_min_scale),
        max_scale=float(args.gain_max_scale),
        discrepancy_weight=float(args.gain_discrepancy_weight),
        attention_weight=float(args.gain_attention_weight),
        latent_drift_weight=float(args.gain_latent_drift_weight),
    )

    save_json(
        run_dir / "variant.json",
        {
            "variant_name": "source_prompt_source_anchored_hard_roi_feature_injection_roi_gain_v2",
            "ddim_inversion_prompt_mode": "source_prompt",
            "reference_branch_prompt_mode": "source_prompt",
            "attention_prompt_mode": "target_prompt",
            "mechanism": (
                "Hard ROI editing with outside-roi source anchoring, optional decoder feature injection, "
                "and an ROI-local positive edit-gain field"
            ),
            "support_update": "M_t = roi_mask",
            "background_anchor": "z_{t-1} = roi_mask * z_{t-1}^{edit} + (1-roi_mask) * z_{t-1}^{src}",
            "feature_injection_enabled": not args.disable_feature_injection,
            "decoder_feature_injection": {
                "start_ratio": injection_config.start_ratio,
                "end_ratio": injection_config.end_ratio,
                "strength": injection_config.strength,
                "up_block_indices": list(injection_config.up_block_indices),
                "resnet_indices": list(injection_config.resnet_indices),
            },
            "roi_edit_gain_field": gain_config.to_dict(),
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
        stage="source_prompt_source_anchored_hard_roi_feature_injection_roi_gain",
        operation="prepare run",
        inputs={
            "phase": config.phase,
            "methods": list(config.methods),
            "run_dir": str(run_dir),
            "feature_injection_enabled": not args.disable_feature_injection,
            "decoder_feature_injection": {
                "start_ratio": injection_config.start_ratio,
                "end_ratio": injection_config.end_ratio,
                "strength": injection_config.strength,
                "up_block_indices": list(injection_config.up_block_indices),
                "resnet_indices": list(injection_config.resnet_indices),
            },
            "roi_edit_gain_field": gain_config.to_dict(),
            "diffedit": diffedit_config.to_dict(),
        },
        result={"sample_ids": [sample.sample_id for sample in materialized_samples]},
        conclusion="samples and FI+ROI-gain config saved",
        next_step="run inversion and editing",
    )

    if config.dry_run:
        return

    pipe = _build_stable_diffusion_pipeline_safe(config.runtime)
    inversion_backend = None
    if config.runtime.inversion_backend == "nti":
        inversion_backend = NTIInversionBackend(pipe, config.runtime)
    editor = V1SourcePromptSourceAnchoredHardRoiFeatureInjectionRoiGainEditor(
        pipe,
        config,
        injection_config=injection_config,
        gain_config=gain_config,
        enable_feature_injection=not args.disable_feature_injection,
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
                "variant": "source_prompt_source_anchored_hard_roi_feature_injection_roi_gain_v2",
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
        stage="source_prompt_source_anchored_hard_roi_feature_injection_roi_gain",
        operation="complete run",
        inputs={"run_dir": str(run_dir)},
        result={
            "case_metrics_csv": str(run_dir / "metrics_case_level.csv"),
            "summary_csv": str(run_dir / "metrics_summary.csv") if metric_runner is not None else None,
        },
        conclusion="source-anchored hard-roi FI+ROI-gain run finished",
        next_step="compare FI-only, gain-only, and FI+gain on the same split",
    )


if __name__ == "__main__":
    main()
