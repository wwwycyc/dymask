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
from DyMask.proedit_like_feature_mix import ProEditLikeFeatureMixConfig
from DyMask.proedit_like_latent_shift import ProEditLikeLatentShiftConfig
from DyMask.run_v1 import (
    build_config,
    build_parser,
    build_run_overview,
    build_sample_overview,
    materialize_from_sample_json,
    resolve_overview_methods,
    write_overview_method_metric_tables,
)
from DyMask.utils import make_timestamped_run_dir, save_csv_records, save_json
from DyMask.v1_source_prompt_validated_revocable_state_proedit import V1SourcePromptValidatedRevocableStateProEditEditor


def _has_output_root_arg(argv: list[str]) -> bool:
    return any(arg == "--output-root" or arg.startswith("--output-root=") for arg in argv)


def main(argv: list[str] | None = None) -> None:
    argv_list = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    parser.add_argument("--support-rho", type=float, default=0.85)
    parser.add_argument("--support-decay-mu", type=float, default=0.80)
    parser.add_argument("--support-decay-lambda", type=float, default=0.10)
    parser.add_argument("--support-lambda", type=float, default=0.50)
    parser.add_argument("--support-kappa", type=float, default=8.0)
    parser.add_argument("--support-alpha", type=float, default=8.0)
    parser.add_argument("--support-delta", type=float, default=0.35)
    parser.add_argument("--mix-start-ratio", type=float, default=0.20)
    parser.add_argument("--mix-end-ratio", type=float, default=0.80)
    parser.add_argument("--mix-inside-target-relax-strength", type=float, default=0.05)
    parser.add_argument("--mix-outside-source-strength", type=float, default=0.15)
    parser.add_argument("--mix-up-blocks", nargs="+", type=int, default=[2, 3])
    parser.add_argument("--mix-resnets", nargs="+", type=int, default=[0, 1, 2])
    parser.add_argument("--latent-shift-strength", type=float, default=0.05)
    args = parser.parse_args(argv_list)
    if not _has_output_root_arg(argv_list):
        args.output_root = "scratch_source_prompt_validated_revocable_state_proedit_runs/sp_vrs_proedit"

    config = build_config(args)
    run_prefix = (
        f"{config.phase}_source_prompt_validated_revocable_state_proedit"
        if config.phase != "custom"
        else "v1_source_prompt_validated_revocable_state_proedit"
    )
    run_dir = make_timestamped_run_dir(config.sampling.output_root, prefix=run_prefix)
    logger = MarkdownExperimentLogger(Path("log_source_prompt_validated_revocable_state_proedit.md"))

    feature_mix_config = ProEditLikeFeatureMixConfig(
        start_ratio=float(args.mix_start_ratio),
        end_ratio=float(args.mix_end_ratio),
        inside_target_relax_strength=float(args.mix_inside_target_relax_strength),
        outside_source_strength=float(args.mix_outside_source_strength),
        up_block_indices=tuple(int(item) for item in args.mix_up_blocks),
        resnet_indices=tuple(int(item) for item in args.mix_resnets),
    )
    latent_shift_config = ProEditLikeLatentShiftConfig(
        strength=float(args.latent_shift_strength),
    )

    save_json(
        run_dir / "variant.json",
        {
            "variant_name": "source_prompt_validated_revocable_state_proedit_v1",
            "ddim_inversion_prompt_mode": "source_prompt",
            "reference_branch_prompt_mode": "source_prompt",
            "attention_prompt_mode": "target_prompt",
            "support_rho": float(args.support_rho),
            "support_decay_mu": float(args.support_decay_mu),
            "support_decay_lambda": float(args.support_decay_lambda),
            "support_lambda": float(args.support_lambda),
            "support_kappa": float(args.support_kappa),
            "support_alpha": float(args.support_alpha),
            "support_delta": float(args.support_delta),
            "mechanism": "Source-prompt validated revocable state with ProEdit-style KV mix and latent shift",
            "proedit_like_kv_mix": {
                "start_ratio": feature_mix_config.start_ratio,
                "end_ratio": feature_mix_config.end_ratio,
                "inside_target_relax_strength": feature_mix_config.inside_target_relax_strength,
                "outside_source_strength": feature_mix_config.outside_source_strength,
                "up_block_indices": list(feature_mix_config.up_block_indices),
                "resnet_indices": list(feature_mix_config.resnet_indices),
            },
            "proedit_like_latent_shift": {"strength": latent_shift_config.strength},
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
        stage="source_prompt_validated_revocable_state_proedit",
        operation="prepare run",
        inputs={
            "phase": config.phase,
            "methods": list(config.methods),
            "run_dir": str(run_dir),
        },
        result={"sample_ids": [sample.sample_id for sample in materialized_samples]},
        conclusion="samples and validated-revocable-state+proedit config saved",
        next_step="run inversion and editing",
    )

    if config.dry_run:
        return

    pipe = build_stable_diffusion_pipeline(config.runtime)
    inversion_backend = None
    if config.runtime.inversion_backend == "nti":
        inversion_backend = NTIInversionBackend(pipe, config.runtime)
    editor = V1SourcePromptValidatedRevocableStateProEditEditor(
        pipe,
        config,
        feature_mix_config=feature_mix_config,
        latent_shift_config=latent_shift_config,
        support_rho=args.support_rho,
        support_decay_mu=args.support_decay_mu,
        support_decay_lambda=args.support_decay_lambda,
        support_lambda=args.support_lambda,
        support_kappa=args.support_kappa,
        support_alpha=args.support_alpha,
        support_delta=args.support_delta,
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
            "variant": "source_prompt_validated_revocable_state_proedit_v1",
            "reconstruction_path": str(sample.sample_dir / "source_reconstruction.png"),
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
                "variant": "source_prompt_validated_revocable_state_proedit_v1",
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

        _ = build_sample_overview(sample, method_results, config.runtime.image_size, overview_methods)

    save_csv_records(run_dir / "metrics_case_level.csv", case_rows)
    if metric_runner is not None:
        save_csv_records(run_dir / "metrics_summary.csv", metric_runner.summarize(case_rows))
        write_overview_method_metric_tables(run_dir, case_rows, overview_methods)
    build_run_overview(run_dir, run_samples)

    logger.log(
        stage="source_prompt_validated_revocable_state_proedit",
        operation="complete run",
        inputs={"run_dir": str(run_dir)},
        result={
            "case_metrics_csv": str(run_dir / "metrics_case_level.csv"),
            "summary_csv": str(run_dir / "metrics_summary.csv") if metric_runner is not None else None,
        },
        conclusion="validated-revocable-state+proedit run finished",
        next_step="inspect summary tables and support-state diagnostics",
    )


if __name__ == "__main__":
    main()
