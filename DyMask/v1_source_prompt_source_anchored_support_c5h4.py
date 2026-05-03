from __future__ import annotations

import torch

from .schemas import MaterializedSample
from .v1_source_prompt_source_anchored_support_c5h3 import V1SourcePromptSourceAnchoredSupportC5H3Editor


class V1SourcePromptSourceAnchoredSupportC5H4Editor(V1SourcePromptSourceAnchoredSupportC5H3Editor):
    def __init__(
        self,
        pipe,
        config,
        underedit_temporal_rho: float = 0.55,
        **kwargs,
    ) -> None:
        super().__init__(pipe, config, **kwargs)
        self.underedit_temporal_rho = self._validate_unit_interval(
            underedit_temporal_rho,
            "underedit_temporal_rho",
        )
        self._underedit_temporal_state: torch.Tensor | None = None

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_support_c5h4_temporal_underedit_guard_v1",
                "underedit_temporal_guard": {
                    "formula": (
                        "u_t = gamma * u_(t-1) + (1-gamma) * r_t; "
                        "r'_t = min(r_t, u_t); "
                        "phi'_t = clamp(phi_t + lambda_s * r'_t, 0, 1); "
                        "M'_t = clamp(M_t + lambda_m * r'_t, 0, 1); "
                        "A'_t = lerp(A_t, 1, lambda_a * r'_t)"
                    ),
                    "temporal_rho": self.underedit_temporal_rho,
                },
            }
        )
        return payload

    def _prepare_source_attention_pass(self, step_idx: int, total_steps: int) -> None:
        if step_idx == 0:
            self._underedit_temporal_state = None
        super()._prepare_source_attention_pass(step_idx, total_steps)

    def _update_underedit_temporal_state(self, raw_rescue_mask: torch.Tensor) -> torch.Tensor:
        previous_state = self._underedit_temporal_state
        if (
            previous_state is None
            or previous_state.shape != raw_rescue_mask.shape
            or previous_state.device != raw_rescue_mask.device
            or previous_state.dtype != raw_rescue_mask.dtype
        ):
            temporal_state = ((1.0 - self.underedit_temporal_rho) * raw_rescue_mask).clamp(0.0, 1.0)
        else:
            temporal_state = (
                self.underedit_temporal_rho * previous_state
                + (1.0 - self.underedit_temporal_rho) * raw_rescue_mask
            ).clamp(0.0, 1.0)
        self._underedit_temporal_state = temporal_state.detach()
        return temporal_state

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
        raw_rescue_mask = (soft_roi_mask * dynamic_mask * underedit_ratio).clamp(0.0, 1.0)
        temporal_state = self._update_underedit_temporal_state(raw_rescue_mask)
        rescue_mask = torch.minimum(raw_rescue_mask, temporal_state).clamp(0.0, 1.0)
        temporal_gate = torch.where(
            raw_rescue_mask > self.underedit_eps,
            rescue_mask / (raw_rescue_mask + self.underedit_eps),
            torch.zeros_like(raw_rescue_mask),
        ).clamp(0.0, 1.0)

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
            "underedit_raw_rescue_mask": raw_rescue_mask,
            "underedit_temporal_state": temporal_state,
            "underedit_temporal_gate": temporal_gate,
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
