from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RuntimeConfig:
    model_id: str = "runwayml/stable-diffusion-v1-5"
    clip_model_id: str = "openai/clip-vit-large-patch14"
    device: str = "cuda"
    dtype: str = "float16"
    image_size: int = 512
    num_inversion_steps: int = 10
    num_edit_steps: int = 10
    guidance_scale: float = 7.5
    local_files_only: bool = True
    attention_slicing: bool = True
    vae_slicing: bool = True
    enable_cpu_offload: bool = False
    sample_batch_size: int = 1
    min_sample_batch_size: int = 1
    auto_batch_fallback: bool = True
    batch_warmup_probe: bool = True
    enable_tf32: bool = False
    channels_last: bool = False
    enable_xformers: bool = False
    clear_cuda_cache_between_methods: bool = True

    @property
    def num_ddim_steps(self) -> int:
        return self.num_edit_steps

    @num_ddim_steps.setter
    def num_ddim_steps(self, value: int) -> None:
        self.num_inversion_steps = value
        self.num_edit_steps = value


@dataclass
class SamplingConfig:
    parquet_path: Path = Path("assets/data/train-00000-of-00262-57cebf95b4a9170c.parquet")
    piebench_path: Path | None = None
    output_root: Path = Path("runs/dymask_v1")
    sample_count: int = 8
    sample_seed: int = 42
    run_limit: int = 1
    manifest_name: str = "sample_manifest"


@dataclass
class MaskConfig:
    mode: str = "dynamic"
    global_blend_alpha: float = 0.45
    global_blend_alphas: tuple[float, ...] = (0.3, 0.5, 0.7)
    discrepancy_use_cfg: bool = False
    discrepancy_weight: float = 0.55
    attention_weight: float = 0.30
    latent_weight: float = 0.15
    temperature: float = 8.0
    threshold: float = 0.35
    min_value: float = 0.0
    max_value: float = 1.0
    smoothing_kernel: int = 5
    attention_locations: tuple[str, ...] = ("down", "mid", "up")
    selected_step_count: int = 5


@dataclass
class MetricConfig:
    enable_psnr: bool = True
    enable_lpips: bool = True
    enable_clipscore: bool = True
    lpips_net: str = "squeeze"
    clip_local_files_only: bool = True
    strict: bool = False


@dataclass
class ExperimentConfig:
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    sampling: SamplingConfig = field(default_factory=SamplingConfig)
    mask: MaskConfig = field(default_factory=MaskConfig)
    metrics: MetricConfig = field(default_factory=MetricConfig)
    methods: tuple[str, ...] = (
        "target_only",
        "global_blend_0.3",
        "global_blend_0.5",
        "global_blend_0.7",
        "discrepancy_only",
        "discrepancy_attention",
        "discrepancy_latent",
        "full_dynamic_mask",
    )
    phase: str = "custom"
    save_inversion_tensors: bool = True
    dry_run: bool = False
    skip_metrics: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
