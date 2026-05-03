from __future__ import annotations

import torch

from .schemas import MaterializedSample
from .v1_source_prompt_source_anchored_support_c5h2 import V1SourcePromptSourceAnchoredSupportC5H2Editor


class V1SourcePromptSourceAnchoredSupportC5H3Editor(V1SourcePromptSourceAnchoredSupportC5H2Editor):
    def __init__(
        self,
        pipe,
        config,
        underedit_support_gain: float = 0.45,
        underedit_mask_gain: float = 0.20,
        underedit_anchor_gain: float = 0.30,
        underedit_eps: float = 1e-6,
        **kwargs,
    ) -> None:
        super().__init__(pipe, config, **kwargs)
        self.underedit_support_gain = self._validate_unit_interval(
            underedit_support_gain,
            "underedit_support_gain",
        )
        self.underedit_mask_gain = self._validate_unit_interval(
            underedit_mask_gain,
            "underedit_mask_gain",
        )
        self.underedit_anchor_gain = self._validate_unit_interval(
            underedit_anchor_gain,
            "underedit_anchor_gain",
        )
        self.underedit_eps = float(underedit_eps)
        if self.underedit_eps <= 0.0:
            raise ValueError(f"underedit_eps must be > 0, got {self.underedit_eps}")
        self._latest_underedit_context: dict[str, torch.Tensor] | None = None

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_support_c5h3_underedit_rescue_v1",
                "underedit_rescue": {
                    "formula": (
                        "p_t = relu(g_src_tar - g_applied) / (g_src_tar + eps); "
                        "r_t = roi_soft * dynamic_mask * p_t; "
                        "phi'_t = clamp(phi_t + lambda_s * r_t, 0, 1); "
                        "M'_t = clamp(M_t + lambda_m * r_t, 0, 1); "
                        "A'_t = lerp(A_t, 1, lambda_a * r_t)"
                    ),
                    "support_gain": self.underedit_support_gain,
                    "mask_gain": self.underedit_mask_gain,
                    "anchor_gain": self.underedit_anchor_gain,
                    "eps": self.underedit_eps,
                },
            }
        )
        return payload

    def _prepare_source_attention_pass(self, step_idx: int, total_steps: int) -> None:
        self._latest_underedit_context = None
        super()._prepare_source_attention_pass(step_idx, total_steps)

    def _apply_support_rescue(
        self,
        method_name: str,
        previous_support_state: torch.Tensor | None,
        support_evidence: torch.Tensor,
        support_state: torch.Tensor,
        effective_mask: torch.Tensor,
        dynamic_mask: torch.Tensor,
        aux_tensor: dict[str, torch.Tensor],
        roi_mask: torch.Tensor | None,
        eps_src: torch.Tensor,
        eps_tar: torch.Tensor,
        step_idx: int,
        total_steps: int,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, dict[str, torch.Tensor]]:
        self._latest_underedit_context = None
        if roi_mask is None or method_name == "target_only" or not self._uses_diffedit_roi_cap(method_name):
            return support_evidence, support_state, effective_mask, {}

        soft_roi_mask = self._resolve_soft_roi_mask(roi_mask)
        dynamic_mask = self._clamp_unit_tensor(dynamic_mask)
        if soft_roi_mask is None or dynamic_mask is None:
            return support_evidence, support_state, effective_mask, {}

        if (
            self.underedit_support_gain <= 0.0
            and self.underedit_mask_gain <= 0.0
            and self.underedit_anchor_gain <= 0.0
        ):
            return support_evidence, support_state, effective_mask, {}

        soft_roi_mask = soft_roi_mask.clamp(0.0, 1.0)
        residual = eps_tar - eps_src
        src_tar_gap = residual.abs().flatten(1).mean(dim=1, keepdim=True).view(-1, 1, 1, 1)
        provisional_eps = eps_src + effective_mask * residual
        applied_gap = (provisional_eps - eps_src).abs().flatten(1).mean(dim=1, keepdim=True).view(-1, 1, 1, 1)
        underedit_ratio = torch.relu(src_tar_gap - applied_gap) / (src_tar_gap + self.underedit_eps)
        rescue_mask = (soft_roi_mask * dynamic_mask * underedit_ratio).clamp(0.0, 1.0)

        support_boost = (self.underedit_support_gain * rescue_mask).clamp(0.0, 1.0)
        mask_boost = (self.underedit_mask_gain * rescue_mask).clamp(0.0, 1.0)
        anchor_relax_mask = (self.underedit_anchor_gain * rescue_mask).clamp(0.0, 1.0)

        rescued_support_evidence = (support_evidence + support_boost).clamp(0.0, 1.0)
        rescued_support_state = self._update_support_state(previous_support_state, rescued_support_evidence)
        rescued_effective_mask = self._effective_mask_from_support_state(
            method_name=method_name,
            support_state=rescued_support_state,
            roi_mask=roi_mask,
            step_idx=step_idx,
            total_steps=total_steps,
        )
        rescued_effective_mask = (rescued_effective_mask + mask_boost).clamp(0.0, 1.0)

        context_seed = self._latest_anchor_confidence_context if self._latest_anchor_confidence_context is not None else aux_tensor
        if context_seed is not None:
            self._cache_anchor_context(
                context_seed,
                dynamic_mask=dynamic_mask,
                support_state=rescued_support_state,
                effective_mask=rescued_effective_mask,
                roi_mask=roi_mask,
            )

        expanded_ratio = underedit_ratio.expand_as(rescue_mask)
        expanded_src_gap = src_tar_gap.expand_as(rescue_mask)
        expanded_applied_gap = applied_gap.expand_as(rescue_mask)
        self._latest_underedit_context = {
            "underedit_ratio": expanded_ratio,
            "underedit_rescue_mask": rescue_mask,
            "underedit_support_boost": support_boost,
            "underedit_mask_boost": mask_boost,
            "underedit_anchor_relax_mask": anchor_relax_mask,
            "underedit_src_tar_gap": expanded_src_gap,
            "underedit_applied_gap": expanded_applied_gap,
        }
        return (
            rescued_support_evidence,
            rescued_support_state,
            rescued_effective_mask,
            dict(self._latest_underedit_context),
        )

    def _relaxed_anchor_mask(
        self,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
        aux_tensor: dict[str, torch.Tensor] | None,
    ) -> tuple[torch.Tensor | None, dict[str, torch.Tensor] | None]:
        relaxed_anchor_mask, components = super()._relaxed_anchor_mask(
            roi_mask=roi_mask,
            step_idx=step_idx,
            total_steps=total_steps,
            aux_tensor=aux_tensor,
        )
        if self._latest_underedit_context is None:
            return relaxed_anchor_mask, components

        rescue_relax_mask = self._latest_underedit_context.get("underedit_anchor_relax_mask")
        if rescue_relax_mask is None:
            return relaxed_anchor_mask, components

        if relaxed_anchor_mask is None:
            base_anchor_mask = self._adaptive_anchor_mask(roi_mask, step_idx, total_steps)
            if base_anchor_mask is None:
                return None, components
            relaxed_anchor_mask = base_anchor_mask
        rescue_relax_mask = rescue_relax_mask.clamp(0.0, 1.0)
        if rescue_relax_mask.shape != relaxed_anchor_mask.shape:
            return relaxed_anchor_mask, components

        rescued_anchor_mask = torch.lerp(
            relaxed_anchor_mask,
            torch.ones_like(relaxed_anchor_mask),
            rescue_relax_mask,
        ).clamp(0.0, 1.0)
        components = dict(components or {})
        if "base_anchor_mask" not in components:
            components["base_anchor_mask"] = relaxed_anchor_mask
        if "relax_mask" in components:
            components["confidence_anchor_relax_mask_base"] = components["relax_mask"]
            components["relax_mask"] = torch.maximum(components["relax_mask"], rescue_relax_mask)
        else:
            components["relax_mask"] = rescue_relax_mask
        components["underedit_anchor_relax_mask"] = rescue_relax_mask
        components["underedit_anchor_rescued_mask"] = rescued_anchor_mask
        components["relaxed_anchor_mask"] = rescued_anchor_mask
        return rescued_anchor_mask, components

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
        if self._latest_underedit_context is not None:
            aux_tensor.update(self._latest_underedit_context)
        _anchor_mask, components = self._relaxed_anchor_mask(
            roi_mask=roi_mask,
            step_idx=step_idx,
            total_steps=total_steps,
            aux_tensor=aux_tensor,
        )
        if components is None:
            return aux_tensor
        if "underedit_anchor_relax_mask" in components:
            aux_tensor["underedit_anchor_relax_mask"] = components["underedit_anchor_relax_mask"]
        if "underedit_anchor_rescued_mask" in components:
            aux_tensor["underedit_anchor_rescued_mask"] = components["underedit_anchor_rescued_mask"]
        if "confidence_anchor_relax_mask_base" in components:
            aux_tensor["confidence_anchor_relax_mask_base"] = components["confidence_anchor_relax_mask_base"]
        return aux_tensor
