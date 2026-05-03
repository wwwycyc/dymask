from __future__ import annotations

import argparse
from pathlib import Path

from DyMaskRefactor.diffedit import DiffEditConfig

from DyMaskRefactor.config import ExperimentConfig


def resolve_run_limit(args: argparse.Namespace) -> int:
    if args.run_limit is not None:
        return max(1, int(args.run_limit))
    if args.sample_json:
        return 1
    if args.row_indices:
        return len(args.row_indices)
    return max(1, int(args.sample_count))


def build_config(args: argparse.Namespace, spec) -> ExperimentConfig:
    config = ExperimentConfig()
    config.phase = "custom"
    config.sampling.parquet_path = Path(args.parquet_path)
    config.sampling.piebench_path = Path(args.piebench_path) if args.piebench_path else None
    config.sampling.output_root = Path(args.output_root) if args.output_root else Path(spec.default_output_root)
    config.sampling.sample_count = int(args.sample_count)
    config.sampling.sample_seed = int(args.sample_seed)
    config.sampling.run_limit = resolve_run_limit(args)
    config.runtime.model_id = args.model_id
    config.runtime.clip_model_id = args.clip_model_id
    config.runtime.ntip2p_root = args.ntip2p_root
    config.runtime.inversion_backend = args.inversion_backend
    config.runtime.image_size = int(args.image_size)
    config.runtime.num_inversion_steps = int(args.num_inversion_steps if args.num_inversion_steps is not None else args.num_ddim_steps)
    config.runtime.num_edit_steps = int(args.num_edit_steps if args.num_edit_steps is not None else args.num_ddim_steps)
    config.runtime.guidance_scale = float(args.guidance_scale)
    config.runtime.nti_num_inner_steps = max(1, int(args.nti_num_inner_steps))
    config.runtime.nti_early_stop_epsilon = float(args.nti_early_stop_epsilon)
    config.runtime.device = args.device
    config.runtime.dtype = args.dtype
    config.runtime.sample_batch_size = max(1, int(args.sample_batch_size))
    config.runtime.min_sample_batch_size = max(1, min(int(args.min_sample_batch_size), config.runtime.sample_batch_size))
    config.runtime.auto_batch_fallback = not args.disable_auto_batch_fallback
    config.runtime.batch_warmup_probe = not args.disable_batch_warmup_probe
    config.runtime.enable_tf32 = args.enable_tf32
    config.runtime.channels_last = args.channels_last
    config.runtime.enable_xformers = args.enable_xformers
    config.runtime.clear_cuda_cache_between_methods = not args.keep_cuda_cache
    config.runtime.attention_slicing = not args.disable_attention_slicing
    config.runtime.vae_slicing = not args.disable_vae_slicing
    config.runtime.local_files_only = not args.allow_download
    config.mask.mode = args.mask_mode
    config.mask.global_blend_alpha = float(args.global_blend_alpha)
    config.mask.global_blend_alphas = tuple(float(value) for value in args.global_blend_alphas)
    config.mask.selected_step_count = int(args.selected_step_count)
    config.mask.selected_step_stride = int(args.selected_step_stride) if args.selected_step_stride else None
    config.metrics.clip_local_files_only = not args.allow_download
    config.metrics.enable_structure_distance = not args.disable_structure_distance
    config.metrics.dino_model_name = args.dino_model_name
    config.metrics.dino_weights_path = args.dino_weights_path
    config.metrics.dino_global_patch_size = int(args.dino_global_patch_size)
    config.methods = tuple(args.methods)
    config.save_inversion_tensors = args.save_inversion_tensors
    config.skip_metrics = args.skip_metrics
    config.dry_run = args.dry_run
    return config


def build_diffedit_config(args: argparse.Namespace) -> DiffEditConfig:
    return DiffEditConfig(
        num_maps_per_mask=args.num_maps_per_mask,
        mask_encode_strength=args.mask_encode_strength,
        mask_thresholding_ratio=args.mask_thresholding_ratio,
        inpaint_strength=args.inpaint_strength,
    )
