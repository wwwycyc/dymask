from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import torch
from diffusers import DDIMScheduler, StableDiffusionPipeline

from .config import RuntimeConfig


def _repo_root() -> Path:
    return Path(__file__).resolve().parent


def resolve_ntip2p_root(runtime: RuntimeConfig | None = None) -> Path:
    explicit = None
    if runtime is not None:
        explicit = getattr(runtime, "ntip2p_root", None)
    env_value = os.environ.get("DYMASK_NTIP2P_ROOT")
    candidates = [
        Path(explicit) if explicit else None,
        Path(env_value) if env_value else None,
        _repo_root() / "third_party" / "NTIP2P",
        _repo_root().parent / "NTIP2P",
    ]
    for candidate in candidates:
        if candidate is not None and candidate.exists():
            return candidate.resolve()
    checked = [str(candidate) for candidate in candidates if candidate is not None]
    raise FileNotFoundError(
        "NTIP2P dependency not found. Checked: " + ", ".join(checked) +
        ". Set runtime.ntip2p_root or DYMASK_NTIP2P_ROOT, or vendor NTIP2P under DyMaskRefactor/third_party/NTIP2P."
    )


def load_ntip2p_module(runtime: RuntimeConfig | None = None):
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    ntip2p_dir = resolve_ntip2p_root(runtime)
    if str(ntip2p_dir) not in sys.path:
        sys.path.insert(0, str(ntip2p_dir))
    return importlib.import_module("null_text_w_ptp")


def build_stable_diffusion_pipeline(runtime: RuntimeConfig) -> StableDiffusionPipeline:
    device = runtime.device if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device.startswith("cuda") and runtime.dtype == "float16" else torch.float32
    if device.startswith("cuda"):
        torch.backends.cuda.matmul.allow_tf32 = runtime.enable_tf32
        torch.backends.cudnn.allow_tf32 = runtime.enable_tf32
        if hasattr(torch, "set_float32_matmul_precision"):
            torch.set_float32_matmul_precision("high" if runtime.enable_tf32 else "highest")
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


def configure_ntip2p_module(module, pipe: StableDiffusionPipeline, runtime: RuntimeConfig) -> None:
    module.device = torch.device(pipe.device)
    module.tokenizer = pipe.tokenizer
    module.prompts = []
    module.NUM_DDIM_STEPS = runtime.num_inversion_steps
    module.GUIDANCE_SCALE = runtime.guidance_scale
    module.LOW_RESOURCE = False


def clear_cuda_memory() -> None:
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
