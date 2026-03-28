from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from DyMask.adapters import build_stable_diffusion_pipeline
from DyMask.config import ExperimentConfig
from DyMask.data import MagicBrushParquetDataset
from DyMask.logging_utils import MarkdownExperimentLogger
from DyMask.schemas import MaterializedSample, SampleManifestEntry
from DyMask.utils import make_timestamped_run_dir, save_json
from DyMask.v1 import V1Editor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Visualize target-prompt attention for a single sample.")
    parser.add_argument("--parquet-path", default="assets/data/V1-00000-of-00001.parquet")
    parser.add_argument("--row-index", type=int, default=6)
    parser.add_argument("--sample-json", default=None)
    parser.add_argument("--output-root", default="runs/attention_probe")
    parser.add_argument("--model-id", default="runwayml/stable-diffusion-v1-5")
    parser.add_argument("--clip-model-id", default="openai/clip-vit-base-patch32")
    parser.add_argument("--image-size", type=int, default=512)
    parser.add_argument("--num-ddim-steps", type=int, default=20, help="Legacy alias: sets both inversion and edit steps unless overridden.")
    parser.add_argument("--num-inversion-steps", type=int, default=None)
    parser.add_argument("--num-edit-steps", type=int, default=None)
    parser.add_argument("--guidance-scale", type=float, default=7.5)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--dtype", default="float16")
    parser.add_argument("--allow-download", action="store_true")
    parser.add_argument("--selected-step-count", type=int, default=5)
    return parser


def build_config(args: argparse.Namespace) -> ExperimentConfig:
    config = ExperimentConfig()
    legacy_steps = args.num_ddim_steps
    config.runtime.model_id = args.model_id
    config.runtime.clip_model_id = args.clip_model_id
    config.runtime.image_size = args.image_size
    config.runtime.num_inversion_steps = args.num_inversion_steps if args.num_inversion_steps is not None else legacy_steps
    config.runtime.num_edit_steps = args.num_edit_steps if args.num_edit_steps is not None else legacy_steps
    config.runtime.guidance_scale = args.guidance_scale
    config.runtime.device = args.device
    config.runtime.dtype = args.dtype
    config.runtime.local_files_only = not args.allow_download
    config.metrics.clip_local_files_only = not args.allow_download
    config.mask.selected_step_count = args.selected_step_count
    return config


def materialize_from_sample_json(sample_json_path: Path, output_dir: Path) -> MaterializedSample:
    payload = json.loads(sample_json_path.read_text(encoding="utf-8"))
    sample_dir = output_dir / payload["sample_id"]
    sample_dir.mkdir(parents=True, exist_ok=True)
    source_path = sample_dir / "source.png"
    shutil.copy2(Path(payload["source_image_path"]), source_path)
    target_reference_path = payload.get("target_reference_path")
    target_path = None
    if target_reference_path:
        target_path = sample_dir / "target_reference.png"
        shutil.copy2(Path(target_reference_path), target_path)
    rewritten = dict(payload)
    rewritten["source_image_path"] = str(source_path)
    rewritten["target_reference_path"] = str(target_path) if target_path else None
    save_json(sample_dir / "sample.json", rewritten)
    return MaterializedSample(
        sample_id=payload["sample_id"],
        row_index=int(payload["row_index"]),
        source_prompt=payload["source_prompt"],
        edit_prompt=payload["edit_prompt"],
        target_prompt=payload["target_prompt"],
        source_image_path=source_path,
        target_image_path=target_path,
        sample_dir=sample_dir,
        extras=payload.get("extras") or {},
    )


def materialize_from_parquet(args: argparse.Namespace, output_dir: Path) -> MaterializedSample:
    dataset = MagicBrushParquetDataset(Path(args.parquet_path))
    records = dataset.load_records([args.row_index])
    samples, manifest = dataset.materialize_samples(records, output_dir, args.image_size)
    MagicBrushParquetDataset.write_manifest(output_dir.parent, "sample_manifest", manifest)
    return samples[0]


def main() -> None:
    args = build_parser().parse_args()
    config = build_config(args)
    run_dir = make_timestamped_run_dir(Path(args.output_root), prefix="attention")
    logger = MarkdownExperimentLogger(Path("log.md"))
    sample_root = run_dir / "samples"

    if args.sample_json:
        sample = materialize_from_sample_json(Path(args.sample_json), sample_root)
    else:
        sample = materialize_from_parquet(args, sample_root)

    save_json(run_dir / "config.json", config.to_dict())
    pipe = build_stable_diffusion_pipeline(config.runtime)
    editor = V1Editor(pipe, config)
    overview_path = editor.visualize_attention_only(sample, sample.sample_dir / "attention_only")
    logger.log(
        stage="A_t 单独可视化",
        operation="运行单样本 target prompt attention 探针",
        inputs={
            "sample_id": sample.sample_id,
            "row_index": sample.row_index,
            "source_prompt": sample.source_prompt,
            "target_prompt": sample.target_prompt,
        },
        result={
            "run_dir": str(run_dir),
            "overview_path": str(overview_path),
        },
        conclusion="已保存若干 timestep 的 A_t，用于检查 attention 是否落在语义对象附近。",
        next_step="人工查看 attention_overview.png 和 selected_steps/*.png。",
    )


if __name__ == "__main__":
    main()
