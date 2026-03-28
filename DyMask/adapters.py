from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import torch
from diffusers import DDIMScheduler, StableDiffusionPipeline

from .config import RuntimeConfig


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_ntip2p_module():
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    ntip2p_dir = _repo_root() / "NTIP2P"
    if str(ntip2p_dir) not in sys.path:
        sys.path.insert(0, str(ntip2p_dir))
    return importlib.import_module("null_text_w_ptp")


def build_stable_diffusion_pipeline(runtime: RuntimeConfig) -> StableDiffusionPipeline:
    device = runtime.device if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device.startswith("cuda") and runtime.dtype == "float16" else torch.float32
    pipe_kwargs = {
        "torch_dtype": dtype,
        "safety_checker": None,
        "feature_extractor": None,
        "local_files_only": runtime.local_files_only,
        "requires_safety_checker": False,
    }
    try:
        pipe = StableDiffusionPipeline.from_pretrained(runtime.model_id, **pipe_kwargs)
    except TypeError:
        pipe_kwargs.pop("requires_safety_checker", None)
        pipe = StableDiffusionPipeline.from_pretrained(runtime.model_id, **pipe_kwargs)
    pipe.scheduler = DDIMScheduler.from_config(pipe.scheduler.config, clip_sample=False, set_alpha_to_one=False)
    if runtime.enable_cpu_offload and torch.cuda.is_available():
        pipe.enable_model_cpu_offload()
    else:
        pipe = pipe.to(device)
    if runtime.attention_slicing:
        pipe.enable_attention_slicing()
    if runtime.vae_slicing:
        try:
            pipe.vae.enable_slicing()
        except AttributeError:
            pass
    return pipe


def configure_ntip2p_module(module, pipe: StableDiffusionPipeline, runtime: RuntimeConfig) -> None:
    module.device = torch.device(pipe.device)
    module.tokenizer = pipe.tokenizer
    module.prompts = []
    module.NUM_DDIM_STEPS = runtime.num_inversion_steps
    module.GUIDANCE_SCALE = runtime.guidance_scale
    # We use batched CFG in DyMask, so attention controllers should treat the
    # second half of the batch as the conditional branch.
    module.LOW_RESOURCE = False


def clear_cuda_memory() -> None:
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
