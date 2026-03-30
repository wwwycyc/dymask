from __future__ import annotations

import numpy as np
import torch

from .adapters import clear_cuda_memory, configure_ntip2p_module, load_ntip2p_module
from .config import RuntimeConfig
from .schemas import InversionOutput


class NTIInversionBackend:
    """Null-Text Inversion baseline without any Prompt-to-Prompt editing control."""

    def __init__(self, pipe, runtime: RuntimeConfig) -> None:
        self.pipe = pipe
        self.runtime = runtime
        self.ntip2p = load_ntip2p_module()
        configure_ntip2p_module(self.ntip2p, pipe, runtime)

    def _module_dtypes(self) -> dict[str, torch.dtype]:
        return {
            "unet": self.pipe.unet.dtype,
            "vae": self.pipe.vae.dtype,
            "text_encoder": self.pipe.text_encoder.dtype,
        }

    def _set_module_dtypes(self, dtype: torch.dtype) -> None:
        self.pipe.unet.to(dtype=dtype)
        self.pipe.vae.to(dtype=dtype)
        self.pipe.text_encoder.to(dtype=dtype)

    @staticmethod
    def _ensure_finite(name: str, tensor: torch.Tensor) -> None:
        if not torch.isfinite(tensor).all():
            raise RuntimeError(f"NTI produced non-finite values in {name}.")

    @torch.no_grad()
    def _reconstruct_with_null_embeddings(
        self,
        inversion,
        zt_src: torch.Tensor,
        source_prompt: str,
        null_embeddings: list[torch.Tensor],
    ) -> tuple[list[torch.Tensor], np.ndarray]:
        tokenizer = self.pipe.tokenizer
        text_input = tokenizer(
            [source_prompt],
            padding="max_length",
            max_length=tokenizer.model_max_length,
            truncation=True,
            return_tensors="pt",
        )
        text_embeddings = self.pipe.text_encoder(text_input.input_ids.to(self.pipe.device))[0]

        latents = zt_src.detach().clone().to(self.pipe.device, dtype=self.pipe.unet.dtype)
        trajectory: list[torch.Tensor] = []
        timesteps = list(self.pipe.scheduler.timesteps)
        for step_idx, timestep in enumerate(timesteps):
            trajectory.append(latents.detach().clone())
            null_embedding = null_embeddings[step_idx].to(device=text_embeddings.device, dtype=text_embeddings.dtype)
            null_embedding = null_embedding.expand_as(text_embeddings)
            context = torch.cat([null_embedding, text_embeddings], dim=0)
            latents = inversion.get_noise_pred(latents, timestep, is_forward=False, context=context)
            self._ensure_finite(f"reconstruction_latent_step_{step_idx}", latents)

        reconstruction = inversion.latent2image(latents)
        return trajectory, reconstruction

    def invert(self, source_image: np.ndarray, source_prompt: str | None = None) -> InversionOutput:
        prompt = (source_prompt or "").strip()
        if not prompt:
            raise ValueError("NTIInversionBackend requires a non-empty source prompt.")

        self.ntip2p.ptp_utils.register_attention_control(self.pipe, None)
        inversion = self.ntip2p.NullInversion(self.pipe)
        original_dtypes = self._module_dtypes()
        xformers_reenable = bool(getattr(self.runtime, "enable_xformers", False))
        try:
            self._set_module_dtypes(torch.float32)
            try:
                self.pipe.disable_xformers_memory_efficient_attention()
            except Exception:
                xformers_reenable = False

            with torch.no_grad():
                inversion.init_prompt(prompt)
                ddim_reconstruction_image, ddim_latents = inversion.ddim_inversion(source_image)
            null_embeddings = inversion.null_optimization(
                ddim_latents,
                self.runtime.nti_num_inner_steps,
                self.runtime.nti_early_stop_epsilon,
            )
            zt_src = ddim_latents[-1].detach().clone()
            self._ensure_finite("zt_src", zt_src)
            for step_idx, embedding in enumerate(null_embeddings):
                self._ensure_finite(f"null_embedding_{step_idx}", embedding)
            src_latents, nti_reconstruction_image = self._reconstruct_with_null_embeddings(
                inversion,
                zt_src,
                prompt,
                null_embeddings,
            )
            inversion_timesteps = [
                int(timestep.item()) if hasattr(timestep, "item") else int(timestep)
                for timestep in self.pipe.scheduler.timesteps
            ]
            return InversionOutput(
                zt_src=zt_src,
                src_latents=src_latents,
                reconstruction_image=nti_reconstruction_image,
                null_embeddings=[embedding.detach().clone() for embedding in null_embeddings],
                metadata={
                    "backend": "nti",
                    "source_prompt": prompt,
                    "num_inversion_steps": self.runtime.num_inversion_steps,
                    "nti_num_inner_steps": self.runtime.nti_num_inner_steps,
                    "nti_early_stop_epsilon": self.runtime.nti_early_stop_epsilon,
                    "inversion_timesteps": inversion_timesteps,
                    "ddim_reconstruction_available": True,
                },
            )
        finally:
            self.pipe.unet.to(dtype=original_dtypes["unet"])
            self.pipe.vae.to(dtype=original_dtypes["vae"])
            self.pipe.text_encoder.to(dtype=original_dtypes["text_encoder"])
            if xformers_reenable:
                try:
                    self.pipe.enable_xformers_memory_efficient_attention()
                except Exception:
                    pass
            clear_cuda_memory()
