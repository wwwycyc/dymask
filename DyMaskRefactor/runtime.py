from __future__ import annotations

import torch
from diffusers import AutoencoderKL, DDIMScheduler, StableDiffusionPipeline, UNet2DConditionModel
from transformers import CLIPTextModel, CLIPTokenizer


def build_pipeline(runtime):
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
