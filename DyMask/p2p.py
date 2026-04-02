from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image

from .adapters import configure_ntip2p_module, load_ntip2p_module
from .config import ExperimentConfig
from .schemas import InversionOutput, MaterializedSample, MethodResult
from .utils import compose_labeled_overview, save_csv_records, save_image, save_json


@dataclass
class P2PConfig:
    controller_mode: str = "replace"
    cross_replace_steps: float = 0.8
    self_replace_steps: float = 0.5
    blend_words_source: tuple[str, ...] = ()
    blend_words_target: tuple[str, ...] = ()
    equalizer_words: tuple[str, ...] = ()
    equalizer_values: tuple[float, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class P2PEditor:
    def __init__(
        self,
        pipe,
        config: ExperimentConfig,
        p2p_config: P2PConfig,
        inversion_backend,
    ) -> None:
        self.pipe = pipe
        self.config = config
        self.p2p_config = p2p_config
        self.inversion_backend = inversion_backend
        self.ntip2p = load_ntip2p_module()
        configure_ntip2p_module(self.ntip2p, pipe, config.runtime)

    @staticmethod
    def _load_sample_image(path: Path) -> np.ndarray:
        return np.asarray(Image.open(path).convert("RGB")).copy()

    def _build_controller(
        self,
        source_prompt: str,
        target_prompt: str,
    ) -> tuple[object, dict[str, Any]]:
        self.ntip2p.NUM_DDIM_STEPS = int(self.config.runtime.num_edit_steps)
        prompts = [source_prompt, target_prompt]
        blend_words = None
        if self.p2p_config.blend_words_source and self.p2p_config.blend_words_target:
            blend_words = (
                tuple(self.p2p_config.blend_words_source),
                tuple(self.p2p_config.blend_words_target),
            )
        controller_mode = self.p2p_config.controller_mode
        cross_replace_steps = {"default_": float(self.p2p_config.cross_replace_steps)}
        self_replace_steps = float(self.p2p_config.self_replace_steps)
        eq_params = None
        if self.p2p_config.equalizer_words:
            if len(self.p2p_config.equalizer_words) != len(self.p2p_config.equalizer_values):
                raise ValueError("equalizer_words and equalizer_values must have the same length.")
            eq_params = {
                "words": tuple(self.p2p_config.equalizer_words),
                "values": tuple(float(value) for value in self.p2p_config.equalizer_values),
            }
        metadata: dict[str, Any] = {
            "requested_controller_mode": controller_mode,
            "cross_replace_steps": cross_replace_steps,
            "self_replace_steps": self_replace_steps,
            "blend_words": [list(group) for group in blend_words] if blend_words is not None else None,
            "equalizer": eq_params,
        }
        controller = self.ntip2p.make_controller(
            prompts,
            controller_mode == "replace",
            cross_replace_steps,
            self_replace_steps,
            blend_words=blend_words,
            equilizer_params=eq_params,
        )
        metadata["resolved_controller_mode"] = controller_mode
        return controller, metadata

    def _save_attention_summary(
        self,
        controller,
        prompts: list[str],
        method_dir: Path,
    ) -> Path | None:
        try:
            self.ntip2p.prompts = prompts
            images = self.ntip2p.get_cross_attention_visualization(controller, 16, ["up", "down"], select=1)
        except Exception:
            return None
        if not images:
            return None
        grid = self.ntip2p.make_image_grid(images, num_rows=2)
        attention_path = method_dir / "attention_summary.png"
        save_image(attention_path, grid)
        return attention_path

    def _save_aux_summary(
        self,
        sample: MaterializedSample,
        inversion: InversionOutput,
        source_render: np.ndarray,
        edited_image: np.ndarray,
        method_dir: Path,
        attention_summary_path: Path | None,
    ) -> Path:
        items: list[tuple[str, np.ndarray]] = [
            ("source", np.asarray(Image.open(sample.source_image_path).convert("RGB"))),
            ("reconstruction", inversion.reconstruction_image),
            ("p2p source", source_render),
            ("edited", edited_image),
        ]
        if sample.target_image_path is not None and Path(sample.target_image_path).exists():
            items.append(("target reference", np.asarray(Image.open(sample.target_image_path).convert("RGB"))))
        if attention_summary_path is not None and attention_summary_path.exists():
            items.append(("attention", np.asarray(Image.open(attention_summary_path).convert("RGB"))))
        overview = compose_labeled_overview(
            items,
            columns=min(3, len(items)),
            tile_size=(self.config.runtime.image_size, self.config.runtime.image_size),
            title=sample.sample_id,
        )
        aux_summary_path = method_dir / "aux_summary.png"
        save_image(aux_summary_path, overview)
        return aux_summary_path

    def _run_p2p(self, sample: MaterializedSample, inversion: InversionOutput) -> MethodResult:
        method_name = "p2p"
        method_dir = sample.sample_dir / method_name
        method_dir.mkdir(parents=True, exist_ok=True)

        prompts = [sample.source_prompt, sample.target_prompt]
        controller, controller_meta = self._build_controller(sample.source_prompt, sample.target_prompt)
        latent = inversion.zt_src.detach().clone().to(self.pipe.device, dtype=self.pipe.unet.dtype)
        uncond_embeddings = inversion.null_embeddings if inversion.null_embeddings else None
        images, _latent = self.ntip2p.text2image_ldm_stable(
            self.pipe,
            prompts,
            controller,
            latent=latent,
            num_inference_steps=self.config.runtime.num_edit_steps,
            guidance_scale=self.config.runtime.guidance_scale,
            generator=None,
            uncond_embeddings=uncond_embeddings,
        )
        source_render = np.asarray(images[0]).copy()
        edited_image = np.asarray(images[1]).copy()

        source_render_path = method_dir / "source_render.png"
        edited_path = method_dir / "edited.png"
        save_image(source_render_path, source_render)
        save_image(edited_path, edited_image)

        attention_summary_path = self._save_attention_summary(controller, prompts, method_dir)
        aux_summary_path = self._save_aux_summary(
            sample=sample,
            inversion=inversion,
            source_render=source_render,
            edited_image=edited_image,
            method_dir=method_dir,
            attention_summary_path=attention_summary_path,
        )

        diagnostics_row = {
            "requested_controller_mode": controller_meta["requested_controller_mode"],
            "resolved_controller_mode": controller_meta["resolved_controller_mode"],
            "cross_replace_default": float(self.p2p_config.cross_replace_steps),
            "self_replace_steps": float(self.p2p_config.self_replace_steps),
            "used_local_blend": controller_meta["blend_words"] is not None,
        }
        diagnostics_csv_path = method_dir / "p2p_diagnostics.csv"
        diagnostics_json_path = method_dir / "p2p_diagnostics.json"
        save_csv_records(diagnostics_csv_path, [diagnostics_row])
        save_json(
            diagnostics_json_path,
            {
                "method_name": method_name,
                "prompts": prompts,
                "controller": controller_meta,
                "source_render_path": str(source_render_path),
                "edited_path": str(edited_path),
                "attention_summary_path": str(attention_summary_path) if attention_summary_path else None,
            },
        )

        debug_json_path = method_dir / "debug.json"
        save_json(
            debug_json_path,
            {
                "method_name": method_name,
                "source_prompt": sample.source_prompt,
                "target_prompt": sample.target_prompt,
                "edit_prompt": sample.edit_prompt,
                "inversion": inversion.metadata,
                "runtime": {
                    "num_inversion_steps": self.config.runtime.num_inversion_steps,
                    "num_edit_steps": self.config.runtime.num_edit_steps,
                    "guidance_scale": self.config.runtime.guidance_scale,
                },
                "p2p": self.p2p_config.to_dict(),
                "controller": controller_meta,
                "paths": {
                    "source_render_path": str(source_render_path),
                    "edited_image_path": str(edited_path),
                    "aux_summary_path": str(aux_summary_path),
                    "attention_summary_path": str(attention_summary_path) if attention_summary_path else None,
                    "diagnostics_csv_path": str(diagnostics_csv_path),
                    "diagnostics_json_path": str(diagnostics_json_path),
                },
            },
        )

        return MethodResult(
            method_name=method_name,
            edited_image=edited_image,
            edited_image_path=edited_path,
            mask_summary_path=attention_summary_path,
            aux_summary_path=aux_summary_path,
            delta_trace_path=None,
            diagnostics_csv_path=diagnostics_csv_path,
            diagnostics_json_path=diagnostics_json_path,
            debug_json_path=debug_json_path,
        )

    def run_samples(self, samples: list[MaterializedSample]) -> dict[str, tuple[InversionOutput, list[MethodResult]]]:
        if not samples:
            return {}

        results: dict[str, tuple[InversionOutput, list[MethodResult]]] = {}
        for sample in samples:
            source_image = self._load_sample_image(sample.source_image_path)
            try:
                inversion = self.inversion_backend.invert(source_image, source_prompt=sample.source_prompt)
            except TypeError:
                inversion = self.inversion_backend.invert(source_image)

            save_image(sample.sample_dir / "source_reconstruction.png", inversion.reconstruction_image)
            save_json(sample.sample_dir / "inversion.json", inversion.metadata)
            if self.config.save_inversion_tensors:
                torch.save(inversion.zt_src.detach().cpu(), sample.sample_dir / "zt_src.pt")
                torch.save([latent.detach().cpu() for latent in inversion.src_latents], sample.sample_dir / "src_latents.pt")

            method_result = self._run_p2p(sample, inversion)
            results[sample.sample_id] = (inversion, [method_result])
        return results
