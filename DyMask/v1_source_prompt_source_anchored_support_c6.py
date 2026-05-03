from __future__ import annotations

import torch

from .schemas import MaterializedSample
from .v1_source_prompt_source_anchored_support_c5 import V1SourcePromptSourceAnchoredSupportC5Editor


class V1SourcePromptSourceAnchoredSupportC6Editor(V1SourcePromptSourceAnchoredSupportC5Editor):
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
        consistency_floor: float = 0.20,
        roi_trust_max_strength: float = 0.60,
        roi_trust_start_ratio: float = 0.45,
        roi_trust_full_ratio: float = 0.80,
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
            anchor_relax_start_strength=anchor_relax_start_strength,
            anchor_relax_end_strength=anchor_relax_end_strength,
            diffedit_config=diffedit_config,
            inversion_backend=inversion_backend,
        )
        self.consistency_floor = self._validate_unit_interval(consistency_floor, "consistency_floor")
        self.roi_trust_max_strength = self._validate_unit_interval(roi_trust_max_strength, "roi_trust_max_strength")
        self.roi_trust_start_ratio = self._validate_unit_interval(roi_trust_start_ratio, "roi_trust_start_ratio")
        self.roi_trust_full_ratio = self._validate_unit_interval(roi_trust_full_ratio, "roi_trust_full_ratio")
        if self.roi_trust_full_ratio < self.roi_trust_start_ratio:
            raise ValueError("roi_trust_full_ratio must be >= roi_trust_start_ratio")

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_support_c6_confidence_roi_trust_v1",
                "roi_mask_policy": (
                    "baseline adaptive temporal support plus confidence-gated local anchor relaxation with "
                    "late roi-trust fallback; soft roi participates in readout and local relaxation only, "
                    "not support-memory writes"
                ),
                "background_anchor_policy": (
                    "after each scheduler step, use baseline adaptive anchor mask and relax it where "
                    "discrepancy confirms editing, or later where roi/support remain stable even if early "
                    "discrepancy is weak"
                ),
                "background_anchor_relaxation": {
                    "start_strength": self.anchor_relax_start_strength,
                    "end_strength": self.anchor_relax_end_strength,
                    "consistency_floor": self.consistency_floor,
                    "roi_trust_max_strength": self.roi_trust_max_strength,
                    "roi_trust_start_ratio": self.roi_trust_start_ratio,
                    "roi_trust_full_ratio": self.roi_trust_full_ratio,
                    "formula": (
                        "R_t = alpha_t * roi_soft * max(sqrt(discrepancy * dynamic_mask), "
                        "beta_t * sqrt(max(support_state, mask))) * "
                        "(c_min + (1-c_min) * (1 - |mask - dynamic_mask|)); "
                        "A'_t = lerp(A_t, 1, R_t)"
                    ),
                },
            }
        )
        return payload

    def _roi_trust_gate(self, step_idx: int, total_steps: int) -> float:
        progress = self._schedule_progress(step_idx, total_steps)
        if progress <= self.roi_trust_start_ratio:
            return 0.0
        if progress >= self.roi_trust_full_ratio:
            return self.roi_trust_max_strength
        span = max(self.roi_trust_full_ratio - self.roi_trust_start_ratio, 1e-6)
        local_progress = (progress - self.roi_trust_start_ratio) / span
        return self.roi_trust_max_strength * self._cosine_schedule(0.0, 1.0, local_progress)

    def _roi_trust_base(
        self,
        support_state: torch.Tensor | None,
        effective_mask: torch.Tensor,
        dynamic_mask: torch.Tensor | None,
    ) -> torch.Tensor:
        _ = dynamic_mask
        if support_state is None:
            return effective_mask
        return torch.maximum(support_state, effective_mask)

    def _confidence_roi_mask(
        self,
        roi_mask: torch.Tensor,
        soft_roi_mask: torch.Tensor,
    ) -> torch.Tensor:
        _ = roi_mask
        return soft_roi_mask.clamp(0.0, 1.0)

    def _confidence_anchor_components(
        self,
        aux_tensor: dict[str, torch.Tensor] | None,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> dict[str, torch.Tensor] | None:
        if aux_tensor is None or roi_mask is None:
            return None
        soft_roi_mask = self._resolve_soft_roi_mask(roi_mask)
        discrepancy = self._clamp_unit_tensor(aux_tensor.get("discrepancy"))
        dynamic_mask = self._clamp_unit_tensor(aux_tensor.get("dynamic_mask"))
        effective_mask = self._clamp_unit_tensor(aux_tensor.get("mask"))
        support_state = self._clamp_unit_tensor(aux_tensor.get("support_state"))
        if soft_roi_mask is None or discrepancy is None or dynamic_mask is None or effective_mask is None:
            return None
        confidence_roi_mask = self._confidence_roi_mask(roi_mask, soft_roi_mask)
        evidence = torch.sqrt((discrepancy * dynamic_mask).clamp(0.0, 1.0))
        consistency_raw = (1.0 - torch.abs(effective_mask - dynamic_mask)).clamp(0.0, 1.0)
        consistency = (
            self.consistency_floor + (1.0 - self.consistency_floor) * consistency_raw
        ).clamp(0.0, 1.0)
        roi_trust_base = self._roi_trust_base(support_state, effective_mask, dynamic_mask)
        roi_trust = torch.sqrt(roi_trust_base.clamp(0.0, 1.0))
        roi_trust_gate = self._roi_trust_gate(step_idx, total_steps)
        roi_trust_branch = (roi_trust_gate * roi_trust).clamp(0.0, 1.0)
        signal = torch.maximum(evidence, roi_trust_branch).clamp(0.0, 1.0)
        confidence = (confidence_roi_mask * signal * consistency).clamp(0.0, 1.0)
        return {
            "soft_roi_mask": soft_roi_mask,
            "confidence_roi_mask": confidence_roi_mask,
            "evidence": evidence,
            "consistency_raw": consistency_raw,
            "consistency": consistency,
            "roi_trust": roi_trust,
            "roi_trust_gate": torch.full_like(soft_roi_mask, roi_trust_gate),
            "signal": signal,
            "confidence": confidence,
        }

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
        components = self._confidence_anchor_components(aux_tensor, roi_mask, step_idx, total_steps)
        if components is None:
            return base_anchor_mask, None
        relax_strength = self._anchor_relax_strength(step_idx, total_steps)
        relax_mask = (relax_strength * components["confidence"]).clamp(0.0, 1.0)
        relaxed_anchor_mask = torch.lerp(base_anchor_mask, torch.ones_like(base_anchor_mask), relax_mask).clamp(0.0, 1.0)
        enriched = dict(components)
        enriched["base_anchor_mask"] = base_anchor_mask
        enriched["relax_mask"] = relax_mask
        enriched["relaxed_anchor_mask"] = relaxed_anchor_mask
        enriched["relax_strength"] = torch.full_like(base_anchor_mask, relax_strength)
        return relaxed_anchor_mask, enriched

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
        context = self._latest_anchor_confidence_context if self._latest_anchor_confidence_context is not None else aux_tensor
        _anchor_mask, components = self._relaxed_anchor_mask(
            roi_mask=roi_mask,
            step_idx=step_idx,
            total_steps=total_steps,
            aux_tensor=context,
        )
        if components is None:
            return aux_tensor
        aux_tensor["confidence_anchor_evidence"] = components["evidence"]
        aux_tensor["confidence_anchor_consistency_raw"] = components["consistency_raw"]
        aux_tensor["confidence_anchor_consistency"] = components["consistency"]
        aux_tensor["confidence_anchor_roi_trust"] = components["roi_trust"]
        aux_tensor["confidence_anchor_roi_trust_gate"] = components["roi_trust_gate"]
        aux_tensor["confidence_anchor_signal"] = components["signal"]
        aux_tensor["confidence_anchor_confidence"] = components["confidence"]
        aux_tensor["confidence_anchor_relax_mask"] = components["relax_mask"]
        aux_tensor["confidence_anchor_mask"] = components["relaxed_anchor_mask"]
        return aux_tensor
