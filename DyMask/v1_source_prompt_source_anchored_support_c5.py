from __future__ import annotations

import torch

from .schemas import MaterializedSample
from .v1_source_prompt_source_anchored_support import V1SourcePromptSourceAnchoredSupportEditor


class V1SourcePromptSourceAnchoredSupportC5Editor(V1SourcePromptSourceAnchoredSupportEditor):
    def __init__(
        self,
        pipe,
        config,
        support_rho: float = 0.85,
        soft_roi_start_weight: float = 0.75,
        soft_roi_end_weight: float = 0.10,
        anchor_hardness_start: float = 0.35,
        anchor_hardness_end: float = 1.0,
        anchor_relax_start_strength: float = 0.35,
        anchor_relax_end_strength: float = 0.05,
        diffedit_config=None,
        inversion_backend=None,
    ) -> None:
        super().__init__(
            pipe,
            config,
            support_rho=support_rho,
            soft_roi_start_weight=soft_roi_start_weight,
            soft_roi_end_weight=soft_roi_end_weight,
            anchor_hardness_start=anchor_hardness_start,
            anchor_hardness_end=anchor_hardness_end,
            diffedit_config=diffedit_config,
            inversion_backend=inversion_backend,
        )
        self.anchor_relax_start_strength = self._validate_unit_interval(
            anchor_relax_start_strength,
            "anchor_relax_start_strength",
        )
        self.anchor_relax_end_strength = self._validate_unit_interval(
            anchor_relax_end_strength,
            "anchor_relax_end_strength",
        )
        self._latest_anchor_confidence_context: dict[str, torch.Tensor] | None = None

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_support_c5_confidence_local_anchor_v1",
                "roi_mask_policy": (
                    "baseline adaptive temporal support plus confidence-gated local anchor relaxation; "
                    "soft roi participates in readout and local relaxation only, not support-memory writes"
                ),
                "background_anchor_policy": (
                    "after each scheduler step, use baseline adaptive anchor mask and relax it only where roi, "
                    "instant discrepancy, and dynamic support agree"
                ),
                "background_anchor_relaxation": {
                    "start_strength": self.anchor_relax_start_strength,
                    "end_strength": self.anchor_relax_end_strength,
                    "formula": (
                        "R_t = alpha_t * roi_soft * sqrt(discrepancy * dynamic_mask) * "
                        "(1 - |mask - dynamic_mask|); A'_t = lerp(A_t, 1, R_t)"
                    ),
                },
            }
        )
        return payload

    def _prepare_source_attention_pass(self, step_idx: int, total_steps: int) -> None:
        self._latest_anchor_confidence_context = None
        super()._prepare_source_attention_pass(step_idx, total_steps)

    def _anchor_relax_strength(self, step_idx: int, total_steps: int) -> float:
        return self._cosine_schedule(
            self.anchor_relax_start_strength,
            self.anchor_relax_end_strength,
            self._schedule_progress(step_idx, total_steps),
        )

    @staticmethod
    def _clamp_unit_tensor(tensor: torch.Tensor | None) -> torch.Tensor | None:
        if tensor is None:
            return None
        return tensor.clamp(0.0, 1.0)

    def _confidence_anchor_components(
        self,
        aux_tensor: dict[str, torch.Tensor] | None,
        roi_mask: torch.Tensor | None,
    ) -> dict[str, torch.Tensor] | None:
        if aux_tensor is None or roi_mask is None:
            return None
        soft_roi_mask = self._resolve_soft_roi_mask(roi_mask)
        discrepancy = self._clamp_unit_tensor(aux_tensor.get("discrepancy"))
        dynamic_mask = self._clamp_unit_tensor(aux_tensor.get("dynamic_mask"))
        effective_mask = self._clamp_unit_tensor(aux_tensor.get("mask"))
        if soft_roi_mask is None or discrepancy is None or dynamic_mask is None or effective_mask is None:
            return None
        soft_roi_mask = soft_roi_mask.clamp(0.0, 1.0)
        evidence = torch.sqrt((discrepancy * dynamic_mask).clamp(0.0, 1.0))
        consistency = (1.0 - torch.abs(effective_mask - dynamic_mask)).clamp(0.0, 1.0)
        confidence = (soft_roi_mask * evidence * consistency).clamp(0.0, 1.0)
        return {
            "soft_roi_mask": soft_roi_mask,
            "evidence": evidence,
            "consistency": consistency,
            "confidence": confidence,
        }

    def _cache_anchor_context(
        self,
        aux_tensor: dict[str, torch.Tensor],
        *,
        dynamic_mask: torch.Tensor | None = None,
        support_state: torch.Tensor | None = None,
        effective_mask: torch.Tensor | None = None,
        roi_mask: torch.Tensor | None = None,
    ) -> None:
        context: dict[str, torch.Tensor] = dict(aux_tensor)
        if dynamic_mask is not None:
            context["dynamic_mask"] = dynamic_mask
        if support_state is not None:
            context["support_state"] = support_state
        if effective_mask is not None:
            context["mask"] = effective_mask
        if roi_mask is not None:
            context["roi_mask"] = roi_mask
        self._latest_anchor_confidence_context = context

    def _compose_effective_mask_from_aux(
        self,
        method_name: str,
        dynamic_mask: torch.Tensor,
        aux_tensor: dict[str, torch.Tensor],
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor:
        support_evidence = super()._compose_effective_mask_from_aux(
            method_name,
            dynamic_mask,
            aux_tensor,
            roi_mask,
            step_idx,
            total_steps,
        )
        if roi_mask is not None and method_name != "target_only" and self._uses_diffedit_roi_cap(method_name):
            self._cache_anchor_context(
                aux_tensor,
                dynamic_mask=dynamic_mask,
                roi_mask=roi_mask,
            )
        return support_evidence

    def _effective_mask_from_support_state(
        self,
        method_name: str,
        support_state: torch.Tensor,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor:
        effective_mask = super()._effective_mask_from_support_state(
            method_name=method_name,
            support_state=support_state,
            roi_mask=roi_mask,
            step_idx=step_idx,
            total_steps=total_steps,
        )
        if (
            roi_mask is not None
            and method_name != "target_only"
            and self._uses_diffedit_roi_cap(method_name)
            and self._latest_anchor_confidence_context is not None
        ):
            self._cache_anchor_context(
                self._latest_anchor_confidence_context,
                support_state=support_state,
                effective_mask=effective_mask,
                roi_mask=roi_mask,
            )
        return effective_mask

    def _relaxed_anchor_mask(
        self,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
        aux_tensor: dict[str, torch.Tensor] | None,
    ) -> tuple[torch.Tensor | None, dict[str, torch.Tensor] | None]:
        base_anchor_mask = self._adaptive_anchor_mask(roi_mask, step_idx, total_steps)
        if base_anchor_mask is None:
            return None, None
        components = self._confidence_anchor_components(aux_tensor, roi_mask)
        if components is None:
            return base_anchor_mask, None
        relax_strength = self._anchor_relax_strength(step_idx, total_steps)
        relax_mask = (relax_strength * components["confidence"]).clamp(0.0, 1.0)
        relaxed_anchor_mask = torch.lerp(base_anchor_mask, torch.ones_like(base_anchor_mask), relax_mask).clamp(0.0, 1.0)
        components = dict(components)
        components["base_anchor_mask"] = base_anchor_mask
        components["relax_mask"] = relax_mask
        components["relaxed_anchor_mask"] = relaxed_anchor_mask
        components["relax_strength"] = torch.full_like(base_anchor_mask, relax_strength)
        return relaxed_anchor_mask, components

    def _post_scheduler_step_latents(
        self,
        method_name: str,
        prev_latents: torch.Tensor,
        roi_mask: torch.Tensor | None,
        source_latents: list[torch.Tensor],
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor:
        if roi_mask is None or method_name == "target_only" or not self._uses_diffedit_roi_cap(method_name):
            return prev_latents
        if not source_latents:
            return prev_latents
        anchor_mask, _components = self._relaxed_anchor_mask(
            roi_mask=roi_mask,
            step_idx=step_idx,
            total_steps=total_steps,
            aux_tensor=self._latest_anchor_confidence_context,
        )
        if anchor_mask is None:
            return prev_latents
        next_source_idx = min(step_idx + 1, len(source_latents) - 1)
        source_anchor = source_latents[next_source_idx]
        if source_anchor.shape != prev_latents.shape:
            raise ValueError(
                f"source anchor shape mismatch: expected {tuple(prev_latents.shape)}, got {tuple(source_anchor.shape)}"
            )
        return anchor_mask * prev_latents + (1.0 - anchor_mask) * source_anchor

    def _finalize_step_aux_tensor(
        self,
        method_name: str,
        aux_tensor: dict[str, torch.Tensor],
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> dict[str, torch.Tensor]:
        aux_tensor = super()._finalize_step_aux_tensor(method_name, aux_tensor, roi_mask, step_idx, total_steps)
        if roi_mask is None or method_name == "target_only" or not self._uses_diffedit_roi_cap(method_name):
            return aux_tensor
        _anchor_mask, components = self._relaxed_anchor_mask(
            roi_mask=roi_mask,
            step_idx=step_idx,
            total_steps=total_steps,
            aux_tensor=aux_tensor,
        )
        if components is None:
            return aux_tensor
        aux_tensor["confidence_anchor_evidence"] = components["evidence"]
        aux_tensor["confidence_anchor_consistency"] = components["consistency"]
        aux_tensor["confidence_anchor_confidence"] = components["confidence"]
        aux_tensor["confidence_anchor_relax_mask"] = components["relax_mask"]
        aux_tensor["confidence_anchor_mask"] = components["relaxed_anchor_mask"]
        aux_tensor["confidence_anchor_strength"] = components["relax_strength"]
        return aux_tensor
