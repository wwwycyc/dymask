from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch
from diffusers import AutoencoderKL, DDIMScheduler, StableDiffusionPipeline, UNet2DConditionModel
from PIL import Image
from transformers import CLIPTextModel, CLIPTokenizer

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
from DyMask.utils import make_timestamped_run_dir, save_csv_records, save_json
from DyMask.v1_source_prompt_diffedit_roi import V1SourcePromptDiffEditRoiEditor


def _has_output_root_arg(argv: list[str]) -> bool:
    return any(arg == "--output-root" or arg.startswith("--output-root=") for arg in argv)


def _build_stable_diffusion_pipeline_safe(runtime) -> StableDiffusionPipeline:
    device = runtime.device if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device.startswith("cuda") and runtime.dtype == "float16" else torch.float32
    if device.startswith("cuda"):
        torch.backends.cuda.matmul.allow_tf32 = runtime.enable_tf32
        torch.backends.cudnn.allow_tf32 = runtime.enable_tf32
        if hasattr(torch, "set_float32_matmul_precision"):
            torch.set_float32_matmul_precision("high" if runtime.enable_tf32 else "highest")

    tokenizer = CLIPTokenizer.from_pretrained(
        runtime.model_id,
        subfolder="tokenizer",
        local_files_only=runtime.local_files_only,
    )
    text_encoder = CLIPTextModel.from_pretrained(
        runtime.model_id,
        subfolder="text_encoder",
        torch_dtype=dtype,
        local_files_only=runtime.local_files_only,
    )
    vae = AutoencoderKL.from_pretrained(
        runtime.model_id,
        subfolder="vae",
        torch_dtype=dtype,
        local_files_only=runtime.local_files_only,
        use_safetensors=False,
    )
    unet = UNet2DConditionModel.from_pretrained(
        runtime.model_id,
        subfolder="unet",
        torch_dtype=dtype,
        local_files_only=runtime.local_files_only,
        use_safetensors=False,
    )
    scheduler = DDIMScheduler.from_pretrained(
        runtime.model_id,
        subfolder="scheduler",
        local_files_only=runtime.local_files_only,
        clip_sample=False,
        set_alpha_to_one=False,
    )
    pipe = StableDiffusionPipeline(
        vae=vae,
        text_encoder=text_encoder,
        tokenizer=tokenizer,
        unet=unet,
        scheduler=scheduler,
        safety_checker=None,
        feature_extractor=None,
        requires_safety_checker=False,
    )

    if runtime.enable_cpu_offload and torch.cuda.is_available():
        pipe.enable_model_cpu_offload()
    else:
        pipe = pipe.to(device)
    if runtime.channels_last and device.startswith("cuda"):
        pipe.unet.to(memory_format=torch.channels_last)
        try:
            pipe.vae.to(memory_format=torch.channels_last)
        except Exception:
            pass
    if runtime.attention_slicing:
        pipe.enable_attention_slicing()
    if runtime.vae_slicing:
        try:
            pipe.vae.enable_slicing()
        except AttributeError:
            pass
    if runtime.enable_xformers:
        try:
            pipe.enable_xformers_memory_efficient_attention()
        except Exception:
            pass
    return pipe


def main(argv: list[str] | None = None) -> None:
    argv_list = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    parser.add_argument("--stage-split-ratio", type=float, default=0.5)
    parser.add_argument("--num-maps-per-mask", type=int, default=10)
    parser.add_argument("--mask-encode-strength", type=float, default=0.5)
    parser.add_argument("--mask-thresholding-ratio", type=float, default=3.0)
    parser.add_argument("--inpaint-strength", type=float, default=1.0)
    args = parser.parse_args(argv_list)
    if not _has_output_root_arg(argv_list):
        args.output_root = "runs/dymask_v1_source_prompt_diffedit_roi"

    config = build_config(args)
    run_prefix = (
        f"{config.phase}_source_prompt_diffedit_roi"
        if config.phase != "custom"
        else "v1_source_prompt_diffedit_roi"
    )
    run_dir = make_timestamped_run_dir(config.sampling.output_root, prefix=run_prefix)
    logger = MarkdownExperimentLogger(Path("log.md"))
    diffedit_config = DiffEditConfig(
        num_maps_per_mask=args.num_maps_per_mask,
        mask_encode_strength=args.mask_encode_strength,
        mask_thresholding_ratio=args.mask_thresholding_ratio,
        inpaint_strength=args.inpaint_strength,
    )

    save_json(
        run_dir / "variant.json",
        {
            "variant_name": "source_prompt_diffedit_roi_upperbound_v1",
            "ddim_inversion_prompt_mode": "source_prompt",
            "reference_branch_prompt_mode": "source_prompt",
            "attention_prompt_mode": "target_prompt",
            "stage_split_ratio": float(args.stage_split_ratio),
            "mechanism": "DiffEdit hard ROI for early lock, then DiffEdit ROI times dynamic mask for late refinement",
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
        stage="source_prompt_diffedit_roi",
        operation="prepare run",
        inputs={
            "phase": config.phase,
            "methods": list(config.methods),
            "run_dir": str(run_dir),
            "stage_split_ratio": float(args.stage_split_ratio),
            "diffedit": diffedit_config.to_dict(),
        },
        result={"sample_ids": [sample.sample_id for sample in materialized_samples]},
        conclusion="samples and variant config saved",
        next_step="run inversion and editing",
    )

    if config.dry_run:
        return

    pipe = _build_stable_diffusion_pipeline_safe(config.runtime)
    inversion_backend = None
    if config.runtime.inversion_backend == "nti":
        inversion_backend = NTIInversionBackend(pipe, config.runtime)
    editor = V1SourcePromptDiffEditRoiEditor(
        pipe,
        config,
        stage_split_ratio=args.stage_split_ratio,
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
            "variant": "source_prompt_diffedit_roi_upperbound_v1",
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
                "variant": "source_prompt_diffedit_roi_upperbound_v1",
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
        stage="source_prompt_diffedit_roi",
        operation="finish run",
        inputs={
            "run_dir": str(run_dir),
            "methods": list(config.methods),
            "stage_split_ratio": float(args.stage_split_ratio),
            "diffedit": diffedit_config.to_dict(),
        },
        result={
            "case_metrics_csv": str(metrics_path),
            "summary_metrics_csv": str(run_dir / "metrics_summary.csv"),
            "overview_method_case_metrics_csv": str(overview_method_case_table_path),
            "overview_method_summary_metrics_csv": str(overview_method_summary_table_path),
            "overview_all_samples_path": str(run_overview_path) if run_overview_path else None,
        },
        conclusion="source-prompt diffedit-roi run completed",
        next_step="compare against source-prompt and diffedit baselines",
    )


if __name__ == "__main__":
    main()
