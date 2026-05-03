from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from einops import rearrange
from PIL import Image
import torch
import torch.nn.functional as F
from diffusers import DDIMScheduler
from torchvision.io import read_image

if __package__ is None or __package__ == "":
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))
    sys.path.insert(0, str(repo_root / "PnPI"))

from DyMask.adapters import clear_cuda_memory
from DyMask.backfill_run_metrics import main as backfill_main
from DyMask.data import MagicBrushParquetDataset, PIEBenchDataset
from DyMask.utils import save_json
from models.masactrl.diffuser_utils import MasaCtrlPipeline
from models.masactrl.masactrl import MutualSelfAttentionControl
from models.masactrl.masactrl_utils import AttentionBase, regiter_attention_editor_diffusers


DEFAULT_MODEL_ID = "/root/autodl-tmp/dymask-v1/models/models--runwayml--stable-diffusion-v1-5/snapshots/451f4fe16113bff5a5d2269ed5ad43b0592e9a14"
DEFAULT_CLIP_MODEL_ID = "/root/autodl-tmp/dymask-v1/models/models--openai--clip-vit-large-patch14/snapshots/32bd64288804d66eefd0ccbe215aa642df71cc41"


class PairwiseMutualSelfAttentionControl(MutualSelfAttentionControl):
    @staticmethod
    def _pairwise_attend(q: torch.Tensor, k: torch.Tensor, v: torch.Tensor, *, num_heads: int, scale: float) -> torch.Tensor:
        batch_items = q.shape[0] // num_heads
        if batch_items % 2 != 0:
            raise ValueError(f"MasaCtrl edit batch must contain source-target pairs, got branch batch={batch_items}")
        pair_count = batch_items // 2
        q_pairs = rearrange(q, "(p t h) n d -> p t h n d", p=pair_count, t=2, h=num_heads)
        k_pairs = rearrange(k, "(p t h) n d -> p t h n d", p=pair_count, t=2, h=num_heads)
        v_pairs = rearrange(v, "(p t h) n d -> p t h n d", p=pair_count, t=2, h=num_heads)
        q_flat = rearrange(q_pairs, "p t h n d -> p h (t n) d")
        k_source = k_pairs[:, 0]
        v_source = v_pairs[:, 0]
        sim = torch.einsum("p h i d, p h j d -> p h i j", q_flat, k_source) * scale
        attn = sim.softmax(-1)
        out = torch.einsum("p h i j, p h j d -> p h i d", attn, v_source)
        return rearrange(out, "p h (t n) d -> (p t) n (h d)", t=2)

    def forward(self, q, k, v, sim, attn, is_cross, place_in_unet, num_heads, **kwargs):
        if is_cross or self.cur_step not in self.step_idx or self.cur_att_layer // 2 not in self.layer_idx:
            return super().forward(q, k, v, sim, attn, is_cross, place_in_unet, num_heads, **kwargs)

        qu, qc = q.chunk(2)
        ku, kc = k.chunk(2)
        vu, vc = v.chunk(2)
        scale = float(kwargs.get("scale", 1.0))
        out_u = self._pairwise_attend(qu, ku, vu, num_heads=num_heads, scale=scale)
        out_c = self._pairwise_attend(qc, kc, vc, num_heads=num_heads, scale=scale)
        return torch.cat([out_u, out_c], dim=0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run MasaCtrl DDIM editing on PIE-Bench.")
    parser.add_argument("--piebench-path", required=True)
    parser.add_argument("--output-root", default="runs/masactrl_full_piebench_parallel")
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--clip-model-id", default=DEFAULT_CLIP_MODEL_ID)
    parser.add_argument("--sample-count", type=int, default=700)
    parser.add_argument("--run-limit", type=int, default=700)
    parser.add_argument("--sample-seed", type=int, default=42)
    parser.add_argument("--row-indices", nargs="*", type=int, default=None)
    parser.add_argument("--image-size", type=int, default=512)
    parser.add_argument("--guidance-scale", type=float, default=7.5)
    parser.add_argument("--num-inversion-steps", type=int, default=50)
    parser.add_argument("--num-edit-steps", type=int, default=50)
    parser.add_argument("--sample-batch-size", type=int, default=4)
    parser.add_argument("--min-sample-batch-size", type=int, default=1)
    parser.add_argument("--disable-auto-batch-fallback", action="store_true")
    parser.add_argument("--disable-batch-warmup-probe", action="store_true")
    parser.add_argument("--controller-step", type=int, default=4)
    parser.add_argument("--controller-layer", type=int, default=10)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--dtype", default="float16", choices=("float16", "float32"))
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--enable-tf32", action="store_true")
    parser.add_argument("--channels-last", action="store_true")
    parser.add_argument("--skip-backfill", action="store_true")
    parser.add_argument("--method-name", default="masactrl")
    parser.add_argument("--variant-name", default="masactrl_ddim")
    return parser.parse_args()


def resolve_indices(dataset: PIEBenchDataset, args: argparse.Namespace) -> list[int]:
    if args.row_indices:
        return list(args.row_indices[: args.run_limit])
    if args.sample_count >= len(dataset):
        return list(range(min(len(dataset), args.run_limit)))
    sampled = dataset.sample_indices(args.sample_count, args.sample_seed)
    return sampled[: args.run_limit]


def clean_prompt(prompt: str) -> str:
    return prompt.replace("[", "").replace("]", "")


def load_image_tensor(path: Path, device: torch.device, dtype: torch.dtype, image_size: int) -> torch.Tensor:
    image = read_image(str(path))[:3].unsqueeze(0).float() / 127.5 - 1.0
    image = F.interpolate(image, (image_size, image_size), mode="bilinear", align_corners=False)
    return image.to(device=device, dtype=dtype)


def load_source_batch(samples, *, device: torch.device, dtype: torch.dtype, image_size: int) -> torch.Tensor:
    tensors = [load_image_tensor(sample.sample_dir / "source.png", device, dtype, image_size) for sample in samples]
    return torch.cat(tensors, dim=0)


def tensor_to_uint8_image(image: torch.Tensor) -> np.ndarray:
    if image.ndim == 4:
        image = image[0]
    image = image.detach().float().clamp(0.0, 1.0).cpu()
    image = image.permute(1, 2, 0).numpy()
    return (image * 255.0).round().astype(np.uint8)


def save_uint8_image(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(image).save(path)


def build_run_dir(output_root: Path) -> Path:
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M")
    run_dir = output_root / f"masactrl_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def build_config_payload(args: argparse.Namespace) -> dict:
    return {
        "experiment": {
            "runtime": {
                "model_id": args.model_id,
                "clip_model_id": args.clip_model_id,
                "inversion_backend": "ddim",
                "device": args.device,
                "dtype": args.dtype,
                "image_size": args.image_size,
                "num_inversion_steps": args.num_inversion_steps,
                "num_edit_steps": args.num_edit_steps,
                "guidance_scale": args.guidance_scale,
                "local_files_only": bool(args.local_files_only),
                "attention_slicing": False,
                "vae_slicing": False,
                "enable_cpu_offload": False,
                "nti_num_inner_steps": 0,
                "nti_early_stop_epsilon": 0.0,
                "sample_batch_size": max(1, int(args.sample_batch_size)),
                "min_sample_batch_size": max(1, int(args.min_sample_batch_size)),
                "auto_batch_fallback": not args.disable_auto_batch_fallback,
                "batch_warmup_probe": not args.disable_batch_warmup_probe,
                "enable_tf32": bool(args.enable_tf32),
                "channels_last": bool(args.channels_last),
                "enable_xformers": False,
                "clear_cuda_cache_between_methods": True,
            },
            "sampling": {
                "piebench_path": args.piebench_path,
                "output_root": args.output_root,
                "sample_count": args.sample_count,
                "sample_seed": args.sample_seed,
                "run_limit": args.run_limit,
                "manifest_name": "sample_manifest",
            },
            "mask": {
                "mode": "external_editor",
                "selected_step_count": None,
                "selected_step_stride": None,
            },
            "metrics": {
                "enable_psnr": True,
                "enable_lpips": True,
                "enable_clipscore": True,
                "lpips_net": "squeeze",
                "clip_local_files_only": True,
                "strict": False,
            },
            "methods": [args.method_name],
            "phase": "custom",
            "save_inversion_tensors": False,
            "dry_run": False,
            "skip_metrics": bool(args.skip_backfill),
        },
        "masactrl": {
            "controller_step": args.controller_step,
            "controller_layer": args.controller_layer,
            "editor": "mutual_self_attention_control",
            "default_inversion_backend": "ddim",
        },
    }


def configure_torch(args: argparse.Namespace, device: torch.device) -> torch.dtype:
    if args.enable_tf32 and device.type == "cuda":
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        if hasattr(torch, "set_float32_matmul_precision"):
            torch.set_float32_matmul_precision("high")
    return torch.float16 if args.dtype == "float16" else torch.float32


def load_pipeline(args: argparse.Namespace, device: torch.device, dtype: torch.dtype) -> MasaCtrlPipeline:
    scheduler = DDIMScheduler(
        beta_start=0.00085,
        beta_end=0.012,
        beta_schedule="scaled_linear",
        clip_sample=False,
        set_alpha_to_one=False,
    )
    pipe = MasaCtrlPipeline.from_pretrained(
        args.model_id,
        scheduler=scheduler,
        torch_dtype=dtype,
        local_files_only=args.local_files_only,
        safety_checker=None,
        requires_safety_checker=False,
    )
    pipe = pipe.to(device)
    if args.channels_last:
        pipe.unet.to(memory_format=torch.channels_last)
        pipe.vae.to(memory_format=torch.channels_last)
    return pipe


def capture_attention_forwards(pipe: MasaCtrlPipeline):
    originals = []

    def visit(module):
        for child in module.children():
            if child.__class__.__name__ == "Attention":
                originals.append((child, child.forward))
            else:
                visit(child)

    visit(pipe.unet)
    return originals


def restore_attention_forwards(originals) -> None:
    for module, forward in originals:
        module.forward = forward


def build_overview(source_path: Path, recon_path: Path, edited_path: Path, overview_path: Path) -> None:
    source = np.asarray(Image.open(source_path).convert("RGB"))
    recon = np.asarray(Image.open(recon_path).convert("RGB"))
    edited = np.asarray(Image.open(edited_path).convert("RGB"))
    overview = np.concatenate([source, recon, edited], axis=1)
    save_uint8_image(overview_path, overview)


def save_sample_outputs(
    sample,
    *,
    method_name: str,
    source_prompt: str,
    target_prompt: str,
    controller_step: int,
    controller_layer: int,
    guidance_scale: float,
    num_inversion_steps: int,
    num_edit_steps: int,
    reconstruction_image: np.ndarray,
    source_render: np.ndarray,
    edited_image: np.ndarray,
) -> None:
    sample_dir = sample.sample_dir
    method_dir = sample_dir / method_name
    method_dir.mkdir(parents=True, exist_ok=True)

    recon_path = sample_dir / "source_reconstruction.png"
    edited_path = method_dir / "edited.png"
    source_render_path = method_dir / "source_render.png"

    save_uint8_image(recon_path, reconstruction_image)
    save_uint8_image(source_render_path, source_render)
    save_uint8_image(edited_path, edited_image)
    build_overview(sample_dir / "source.png", recon_path, edited_path, sample_dir / "overview.png")

    save_json(
        sample_dir / "inversion.json",
        {
            "backend": "ddim",
            "num_inversion_steps": num_inversion_steps,
            "num_edit_steps": num_edit_steps,
            "guidance_scale": guidance_scale,
        },
    )
    save_json(
        method_dir / "debug.json",
        {
            "method_name": method_name,
            "source_prompt": source_prompt,
            "target_prompt": target_prompt,
            "controller_step": controller_step,
            "controller_layer": controller_layer,
        },
    )


@torch.no_grad()
def prepare_sample(
    pipe: MasaCtrlPipeline,
    *,
    sample,
    original_attention_forwards,
    guidance_scale: float,
    num_inversion_steps: int,
    num_edit_steps: int,
    device: torch.device,
    dtype: torch.dtype,
    image_size: int,
) -> tuple[torch.Tensor, torch.Tensor]:
    restore_attention_forwards(original_attention_forwards)
    try:
        source_image = load_source_batch([sample], device=device, dtype=dtype, image_size=image_size)
        start_code, _ = pipe.invert(
            source_image,
            "",
            guidance_scale=guidance_scale,
            num_inference_steps=num_inversion_steps,
            return_intermediates=True,
        )
        regiter_attention_editor_diffusers(pipe, AttentionBase())
        source_prompt = clean_prompt(sample.metadata.source_prompt or "")
        source_reconstruction = pipe(
            [source_prompt],
            latents=start_code,
            num_inference_steps=num_edit_steps,
            guidance_scale=guidance_scale,
        )
        return start_code, source_reconstruction
    finally:
        restore_attention_forwards(original_attention_forwards)


@torch.no_grad()
def run_sample_batch(
    pipe: MasaCtrlPipeline,
    *,
    samples,
    original_attention_forwards,
    method_name: str,
    controller_step: int,
    controller_layer: int,
    guidance_scale: float,
    num_inversion_steps: int,
    num_edit_steps: int,
    device: torch.device,
    dtype: torch.dtype,
    image_size: int,
    write_outputs: bool,
) -> None:
    restore_attention_forwards(original_attention_forwards)
    try:
        start_codes = []
        source_reconstructions = []
        for sample in samples:
            start_code, source_reconstruction = prepare_sample(
                pipe,
                sample=sample,
                original_attention_forwards=original_attention_forwards,
                guidance_scale=guidance_scale,
                num_inversion_steps=num_inversion_steps,
                num_edit_steps=num_edit_steps,
                device=device,
                dtype=dtype,
                image_size=image_size,
            )
            start_codes.append(start_code)
            source_reconstructions.append(source_reconstruction)

        if len(samples) == 1:
            editor = MutualSelfAttentionControl(controller_step, controller_layer, total_steps=num_edit_steps)
        else:
            editor = PairwiseMutualSelfAttentionControl(controller_step, controller_layer, total_steps=num_edit_steps)
        regiter_attention_editor_diffusers(pipe, editor)

        edit_prompts: list[str] = []
        for sample in samples:
            edit_prompts.extend(["", clean_prompt(sample.core_input.target_prompt)])
        start_codes_batch = torch.cat(start_codes, dim=0)
        edited_batch = pipe(
            edit_prompts,
            latents=start_codes_batch.repeat_interleave(2, dim=0),
            num_inference_steps=num_edit_steps,
            guidance_scale=guidance_scale,
        )

        if not write_outputs:
            return

        source_reconstruction_batch = torch.cat(source_reconstructions, dim=0)
        source_renders = edited_batch[0::2]
        edited_images = edited_batch[1::2]
        for index, sample in enumerate(samples):
            save_sample_outputs(
                sample,
                method_name=method_name,
                source_prompt=sample.metadata.source_prompt or "",
                target_prompt=sample.core_input.target_prompt,
                controller_step=controller_step,
                controller_layer=controller_layer,
                guidance_scale=guidance_scale,
                num_inversion_steps=num_inversion_steps,
                num_edit_steps=num_edit_steps,
                reconstruction_image=tensor_to_uint8_image(source_reconstruction_batch[index:index + 1]),
                source_render=tensor_to_uint8_image(source_renders[index:index + 1]),
                edited_image=tensor_to_uint8_image(edited_images[index:index + 1]),
            )
    finally:
        restore_attention_forwards(original_attention_forwards)


def is_cuda_oom_error(exc: BaseException) -> bool:
    if isinstance(exc, torch.cuda.OutOfMemoryError):
        return True
    message = str(exc).lower()
    return "cuda" in message and "out of memory" in message


def next_batch_size(current: int, minimum: int) -> int:
    if current <= minimum:
        return minimum
    next_batch = max(minimum, (current + 1) // 2)
    if next_batch >= current:
        next_batch = current - 1
    return max(minimum, next_batch)


def run_all_batches(
    pipe: MasaCtrlPipeline,
    *,
    samples,
    original_attention_forwards,
    args: argparse.Namespace,
    device: torch.device,
    dtype: torch.dtype,
) -> None:
    batch_size = max(1, int(args.sample_batch_size))
    min_batch_size = max(1, min(int(args.min_sample_batch_size), batch_size))
    auto_batch_fallback = not args.disable_auto_batch_fallback and batch_size > min_batch_size
    active_batch_size = batch_size

    if len(samples) > 1 and active_batch_size > 1 and not args.disable_batch_warmup_probe:
        probe_batch_size = min(active_batch_size, len(samples))
        while True:
            probe_batch = samples[:probe_batch_size]
            probe_ids = ",".join(sample.sample_id for sample in probe_batch)
            try:
                print(f"[warmup-batch-probe][{args.method_name}] probing batch={probe_batch_size} on {probe_ids}")
                run_sample_batch(
                    pipe,
                    samples=probe_batch,
                    original_attention_forwards=original_attention_forwards,
                    method_name=args.method_name,
                    controller_step=args.controller_step,
                    controller_layer=args.controller_layer,
                    guidance_scale=args.guidance_scale,
                    num_inversion_steps=args.num_inversion_steps,
                    num_edit_steps=args.num_edit_steps,
                    device=device,
                    dtype=dtype,
                    image_size=args.image_size,
                    write_outputs=False,
                )
                print(f"[warmup-batch-probe][{args.method_name}] batch={probe_batch_size} passed")
                break
            except RuntimeError as exc:
                if not auto_batch_fallback or not is_cuda_oom_error(exc) or probe_batch_size <= min_batch_size:
                    raise
                reduced_batch_size = next_batch_size(probe_batch_size, min_batch_size)
                print(
                    f"[warmup-batch-probe][{args.method_name}] CUDA OOM at batch={probe_batch_size}; "
                    f"retrying with batch={reduced_batch_size}"
                )
                active_batch_size = reduced_batch_size
                probe_batch_size = reduced_batch_size
                clear_cuda_memory()
        active_batch_size = min(active_batch_size, probe_batch_size)
        print(f"[warmup-batch-probe] using sample_batch_size={active_batch_size} for full run")

    start = 0
    while start < len(samples):
        current_batch_size = min(active_batch_size, len(samples) - start)
        batch = samples[start:start + current_batch_size]
        try:
            run_sample_batch(
                pipe,
                samples=batch,
                original_attention_forwards=original_attention_forwards,
                method_name=args.method_name,
                controller_step=args.controller_step,
                controller_layer=args.controller_layer,
                guidance_scale=args.guidance_scale,
                num_inversion_steps=args.num_inversion_steps,
                num_edit_steps=args.num_edit_steps,
                device=device,
                dtype=dtype,
                image_size=args.image_size,
                write_outputs=True,
            )
        except RuntimeError as exc:
            if not auto_batch_fallback or not is_cuda_oom_error(exc) or current_batch_size <= min_batch_size:
                raise
            reduced_batch_size = next_batch_size(current_batch_size, min_batch_size)
            failed_ids = ",".join(sample.sample_id for sample in batch)
            print(
                f"[auto-batch-fallback][{args.method_name}] CUDA OOM at batch={current_batch_size} "
                f"for {failed_ids}; retrying with batch={reduced_batch_size}"
            )
            active_batch_size = reduced_batch_size
            clear_cuda_memory()
            restore_attention_forwards(original_attention_forwards)
            continue
        start += current_batch_size
        clear_cuda_memory()


def run_backfill(run_dir: Path, args: argparse.Namespace) -> None:
    argv = [
        "backfill_run_metrics.py",
        str(run_dir),
        "--model-id",
        args.model_id,
        "--clip-model-id",
        args.clip_model_id,
        "--piebench-path",
        args.piebench_path,
        "--device",
        args.device,
    ]
    original_argv = sys.argv[:]
    try:
        sys.argv = argv
        backfill_main()
    finally:
        sys.argv = original_argv


def main() -> None:
    args = parse_args()
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    run_dir = build_run_dir(output_root)

    dataset = PIEBenchDataset(Path(args.piebench_path))
    indices = resolve_indices(dataset, args)
    records = dataset.load_records(indices)
    materialized, manifest = dataset.materialize_samples(records, run_dir / "samples", args.image_size)
    MagicBrushParquetDataset.write_manifest(run_dir, "sample_manifest", manifest)

    config_payload = build_config_payload(args)
    save_json(run_dir / "config.json", config_payload)
    save_json(
        run_dir / "variant.json",
        {
            "variant_name": args.variant_name,
            "editing_rule": "masactrl_ddim",
            "default_inversion_backend": "ddim",
        },
    )

    device = torch.device(args.device)
    dtype = configure_torch(args, device)
    pipe = load_pipeline(args, device, dtype)
    original_attention_forwards = capture_attention_forwards(pipe)
    run_all_batches(
        pipe,
        samples=materialized,
        original_attention_forwards=original_attention_forwards,
        args=args,
        device=device,
        dtype=dtype,
    )

    if not args.skip_backfill:
        run_backfill(run_dir, args)

    print(run_dir)


if __name__ == "__main__":
    main()
