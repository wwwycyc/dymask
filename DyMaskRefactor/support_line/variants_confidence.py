from __future__ import annotations

import torch

from DyMaskRefactor.schemas import MaterializedSample

from DyMaskRefactor.support_line.base import RefactorSupportBaselineEditor
from DyMaskRefactor.support_line.schedules import cosine_gate, cosine_schedule, schedule_progress, validate_unit_interval


class RefactorSupportC5Editor(RefactorSupportBaselineEditor):
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
        self.anchor_relax_start_strength = validate_unit_interval(
            anchor_relax_start_strength,
            "anchor_relax_start_strength",
        )
        self.anchor_relax_end_strength = validate_unit_interval(
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
        return cosine_schedule(
            self.anchor_relax_start_strength,
            self.anchor_relax_end_strength,
            schedule_progress(step_idx, total_steps),
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

    def _after_support_evidence(
        self,
        method_name: str,
        dynamic_mask: torch.Tensor,
        aux_tensor: dict[str, torch.Tensor],
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
        support_evidence: torch.Tensor,
    ) -> None:
        if roi_mask is None or method_name == "target_only" or not self._uses_diffedit_roi_cap(method_name):
            return
        self._cache_anchor_context(
            aux_tensor,
            dynamic_mask=dynamic_mask,
            roi_mask=roi_mask,
        )

    def _after_effective_mask(
        self,
        method_name: str,
        support_state: torch.Tensor,
        effective_mask: torch.Tensor,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> None:
        if (
            roi_mask is None
            or method_name == "target_only"
            or not self._uses_diffedit_roi_cap(method_name)
            or self._latest_anchor_confidence_context is None
        ):
            return
        self._cache_anchor_context(
            self._latest_anchor_confidence_context,
            support_state=support_state,
            effective_mask=effective_mask,
            roi_mask=roi_mask,
        )

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
        enriched = dict(components)
        enriched["base_anchor_mask"] = base_anchor_mask
        enriched["relax_mask"] = relax_mask
        enriched["relaxed_anchor_mask"] = relaxed_anchor_mask
        enriched["relax_strength"] = torch.full_like(base_anchor_mask, relax_strength)
        return relaxed_anchor_mask, enriched

    def _anchor_mask(
        self,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor | None:
        anchor_mask, _components = self._relaxed_anchor_mask(
            roi_mask=roi_mask,
            step_idx=step_idx,
            total_steps=total_steps,
            aux_tensor=self._latest_anchor_confidence_context,
        )
        return anchor_mask

    def _extra_step_aux_tensors(
        self,
        method_name: str,
        aux_tensor: dict[str, torch.Tensor],
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> dict[str, torch.Tensor]:
        if roi_mask is None or method_name == "target_only" or not self._uses_diffedit_roi_cap(method_name):
            return {}
        _anchor_mask, components = self._relaxed_anchor_mask(
            roi_mask=roi_mask,
            step_idx=step_idx,
            total_steps=total_steps,
            aux_tensor=aux_tensor,
        )
        if components is None:
            return {}
        return {
            "confidence_anchor_evidence": components["evidence"],
            "confidence_anchor_consistency": components["consistency"],
            "confidence_anchor_confidence": components["confidence"],
            "confidence_anchor_relax_mask": components["relax_mask"],
            "confidence_anchor_mask": components["relaxed_anchor_mask"],
            "confidence_anchor_strength": components["relax_strength"],
        }


class RefactorSupportC6Editor(RefactorSupportC5Editor):
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
        self.consistency_floor = validate_unit_interval(consistency_floor, "consistency_floor")
        self.roi_trust_max_strength = validate_unit_interval(roi_trust_max_strength, "roi_trust_max_strength")
        self.roi_trust_start_ratio = validate_unit_interval(roi_trust_start_ratio, "roi_trust_start_ratio")
        self.roi_trust_full_ratio = validate_unit_interval(roi_trust_full_ratio, "roi_trust_full_ratio")
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
        return self.roi_trust_max_strength * cosine_gate(
            step_idx,
            total_steps,
            start_ratio=self.roi_trust_start_ratio,
            full_ratio=self.roi_trust_full_ratio,
        )

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

    def _extra_step_aux_tensors(
        self,
        method_name: str,
        aux_tensor: dict[str, torch.Tensor],
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> dict[str, torch.Tensor]:
        if roi_mask is None or method_name == "target_only" or not self._uses_diffedit_roi_cap(method_name):
            return {}
        context = self._latest_anchor_confidence_context if self._latest_anchor_confidence_context is not None else aux_tensor
        _anchor_mask, components = self._relaxed_anchor_mask(
            roi_mask=roi_mask,
            step_idx=step_idx,
            total_steps=total_steps,
            aux_tensor=context,
        )
        if components is None:
            return {}
        return {
            "confidence_anchor_evidence": components["evidence"],
            "confidence_anchor_consistency_raw": components["consistency_raw"],
            "confidence_anchor_consistency": components["consistency"],
            "confidence_anchor_roi_trust": components["roi_trust"],
            "confidence_anchor_roi_trust_gate": components["roi_trust_gate"],
            "confidence_anchor_signal": components["signal"],
            "confidence_anchor_confidence": components["confidence"],
            "confidence_anchor_relax_mask": components["relax_mask"],
            "confidence_anchor_mask": components["relaxed_anchor_mask"],
            "confidence_anchor_strength": components["relax_strength"],
        }


class RefactorSupportC6BEditor(RefactorSupportC6Editor):
    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_support_c6b_confidence_roi_agreement_v1",
                "background_anchor_policy": (
                    "same as C6, but the late roi-trust fallback is tightened to regions where support state "
                    "and effective mask both agree, to avoid broad-roi over-relaxation"
                ),
                "background_anchor_relaxation": {
                    **payload.get("background_anchor_relaxation", {}),
                    "roi_trust_formula": "roi_trust_base = support_state * mask; roi_trust = sqrt(roi_trust_base)",
                },
            }
        )
        return payload

    def _roi_trust_base(
        self,
        support_state: torch.Tensor | None,
        effective_mask: torch.Tensor,
        dynamic_mask: torch.Tensor | None,
    ) -> torch.Tensor:
        _ = dynamic_mask
        if support_state is None:
            return effective_mask
        return (support_state * effective_mask).clamp(0.0, 1.0)


class RefactorSupportC6CEditor(RefactorSupportC6Editor):
    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_support_c6c_support_gap_recovery_v1",
                "background_anchor_policy": (
                    "same as C6, but the late roi-trust branch is converted into a recovery-only branch that "
                    "opens anchor only where support memory stays high while the current effective mask has "
                    "collapsed, to refill under-edited holes instead of broadly relaxing the roi"
                ),
                "background_anchor_relaxation": {
                    **payload.get("background_anchor_relaxation", {}),
                    "roi_trust_formula": (
                        "roi_trust_base = relu(support_state - mask); roi_trust = sqrt(roi_trust_base)"
                    ),
                },
            }
        )
        return payload

    def _roi_trust_base(
        self,
        support_state: torch.Tensor | None,
        effective_mask: torch.Tensor,
        dynamic_mask: torch.Tensor | None,
    ) -> torch.Tensor:
        _ = dynamic_mask
        if support_state is None:
            return torch.zeros_like(effective_mask)
        return (support_state - effective_mask).clamp(0.0, 1.0)

class RefactorSupportC6DEditor(RefactorSupportC6CEditor):
    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_support_c6d_dynamic_gap_recovery_v1",
                "background_anchor_policy": (
                    "same as C6c, but the late support-gap recovery branch is further gated by the live "
                    "dynamic mask, so stale support memory cannot reopen regions where current edit evidence "
                    "has already disappeared"
                ),
                "background_anchor_relaxation": {
                    **payload.get("background_anchor_relaxation", {}),
                    "roi_trust_formula": (
                        "roi_trust_base = relu(support_state - mask) * dynamic_mask; "
                        "roi_trust = sqrt(roi_trust_base)"
                    ),
                },
            }
        )
        return payload

    def _roi_trust_base(
        self,
        support_state: torch.Tensor | None,
        effective_mask: torch.Tensor,
        dynamic_mask: torch.Tensor | None,
    ) -> torch.Tensor:
        if support_state is None or dynamic_mask is None:
            return torch.zeros_like(effective_mask)
        support_gap = (support_state - effective_mask).clamp(0.0, 1.0)
        return (support_gap * dynamic_mask).clamp(0.0, 1.0)

__all__ = [
    "RefactorSupportC5Editor",
    "RefactorSupportC6Editor",
    "RefactorSupportC6BEditor",
    "RefactorSupportC6CEditor",
    "RefactorSupportC6DEditor",
]
