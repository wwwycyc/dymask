from __future__ import annotations

import torch

from DyMaskRefactor.schemas import MaterializedSample

from DyMaskRefactor.support_line.base import RefactorSupportBaselineEditor
from DyMaskRefactor.support_line.schedules import cosine_gate, validate_unit_interval


class RefactorSupportC1Editor(RefactorSupportBaselineEditor):
    def __init__(
        self,
        pipe,
        config,
        support_rho: float = 0.85,
        soft_roi_start_weight: float = 0.75,
        soft_roi_end_weight: float = 0.10,
        anchor_hardness_start: float = 0.35,
        anchor_hardness_end: float = 1.0,
        support_soft_roi_blend: float = 0.50,
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
        self.support_soft_roi_blend = validate_unit_interval(support_soft_roi_blend, "support_soft_roi_blend")

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_support_c1_soft_memory_v1",
                "roi_mask_policy": "adaptive support with soft-aware support memory and unchanged adaptive anchoring",
                "support_memory_policy": {
                    "soft_roi_blend": self.support_soft_roi_blend,
                    "formula": "phi_t = dynamic_mask * lerp(roi_hard, roi_soft, beta)",
                },
            }
        )
        return payload

    def _support_memory_blend(self, step_idx: int, total_steps: int) -> float | None:
        return self.support_soft_roi_blend


class RefactorSupportC2Editor(RefactorSupportC1Editor):
    def __init__(
        self,
        pipe,
        config,
        support_rho: float = 0.85,
        soft_roi_start_weight: float = 0.75,
        soft_roi_end_weight: float = 0.10,
        anchor_hardness_start: float = 0.35,
        anchor_hardness_end: float = 1.0,
        support_soft_roi_blend: float = 0.50,
        anchor_enable_start_ratio: float = 0.20,
        anchor_enable_full_ratio: float = 0.50,
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
            support_soft_roi_blend=support_soft_roi_blend,
            diffedit_config=diffedit_config,
            inversion_backend=inversion_backend,
        )
        self.anchor_enable_start_ratio = validate_unit_interval(anchor_enable_start_ratio, "anchor_enable_start_ratio")
        self.anchor_enable_full_ratio = validate_unit_interval(anchor_enable_full_ratio, "anchor_enable_full_ratio")
        if self.anchor_enable_full_ratio < self.anchor_enable_start_ratio:
            raise ValueError("anchor_enable_full_ratio must be >= anchor_enable_start_ratio")

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_support_c2_delayed_anchor_v1",
                "background_anchor_policy": "after each scheduler step, source anchoring is delayed early and then smoothly enabled before the original adaptive roi-hardness schedule takes over",
                "background_anchor_enable_schedule": {
                    "start_ratio": self.anchor_enable_start_ratio,
                    "full_ratio": self.anchor_enable_full_ratio,
                    "formula": "g_t = 0 before start, cosine-ramp to 1 by full; A'_t = lerp(1, A_t, g_t)",
                },
            }
        )
        return payload

    def _anchor_enable_gate(self, step_idx: int, total_steps: int) -> float:
        return cosine_gate(
            step_idx,
            total_steps,
            start_ratio=self.anchor_enable_start_ratio,
            full_ratio=self.anchor_enable_full_ratio,
        )

    def _anchor_mask(
        self,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor | None:
        base_anchor_mask = self._adaptive_anchor_mask(roi_mask, step_idx, total_steps)
        if base_anchor_mask is None:
            return None
        anchor_enable_gate = self._anchor_enable_gate(step_idx, total_steps)
        return torch.lerp(torch.ones_like(base_anchor_mask), base_anchor_mask, anchor_enable_gate).clamp(0.0, 1.0)

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
        delayed_anchor_mask = self._anchor_mask(roi_mask, step_idx, total_steps)
        if delayed_anchor_mask is None:
            return {}
        return {
            "anchor_enable_gate": torch.full_like(roi_mask, self._anchor_enable_gate(step_idx, total_steps)),
            "delayed_anchor_mask": delayed_anchor_mask,
        }


class RefactorSupportC3Editor(RefactorSupportC2Editor):
    def __init__(
        self,
        pipe,
        config,
        support_rho: float = 0.85,
        soft_roi_start_weight: float = 0.75,
        soft_roi_end_weight: float = 0.10,
        anchor_hardness_start: float = 0.35,
        anchor_hardness_end: float = 1.0,
        support_soft_roi_blend: float = 0.50,
        anchor_enable_start_ratio: float = 0.20,
        anchor_enable_full_ratio: float = 0.50,
        support_soft_enable_start_ratio: float = 0.25,
        support_soft_enable_full_ratio: float = 0.60,
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
            support_soft_roi_blend=support_soft_roi_blend,
            anchor_enable_start_ratio=anchor_enable_start_ratio,
            anchor_enable_full_ratio=anchor_enable_full_ratio,
            diffedit_config=diffedit_config,
            inversion_backend=inversion_backend,
        )
        self.support_soft_enable_start_ratio = validate_unit_interval(
            support_soft_enable_start_ratio,
            "support_soft_enable_start_ratio",
        )
        self.support_soft_enable_full_ratio = validate_unit_interval(
            support_soft_enable_full_ratio,
            "support_soft_enable_full_ratio",
        )
        if self.support_soft_enable_full_ratio < self.support_soft_enable_start_ratio:
            raise ValueError("support_soft_enable_full_ratio must be >= support_soft_enable_start_ratio")

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_support_c3_delayed_anchor_delayed_soft_support_v1",
                "roi_mask_policy": "adaptive support with delayed source anchoring and delayed soft-aware support memory",
                "support_memory_policy": {
                    "soft_roi_blend": self.support_soft_roi_blend,
                    "enable_start_ratio": self.support_soft_enable_start_ratio,
                    "enable_full_ratio": self.support_soft_enable_full_ratio,
                    "formula": "phi_t = dynamic_mask * lerp(roi_hard, roi_soft, beta * q_t), q_t = delayed cosine gate",
                },
            }
        )
        return payload

    def _support_soft_enable_gate(self, step_idx: int, total_steps: int) -> float:
        return cosine_gate(
            step_idx,
            total_steps,
            start_ratio=self.support_soft_enable_start_ratio,
            full_ratio=self.support_soft_enable_full_ratio,
        )

    def _support_memory_blend(self, step_idx: int, total_steps: int) -> float | None:
        return self.support_soft_roi_blend * self._support_soft_enable_gate(step_idx, total_steps)

    def _extra_step_aux_tensors(
        self,
        method_name: str,
        aux_tensor: dict[str, torch.Tensor],
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> dict[str, torch.Tensor]:
        tensors = super()._extra_step_aux_tensors(method_name, aux_tensor, roi_mask, step_idx, total_steps)
        if roi_mask is None or method_name == "target_only" or not self._uses_diffedit_roi_cap(method_name):
            return tensors
        tensors["support_soft_enable_gate"] = torch.full_like(roi_mask, self._support_soft_enable_gate(step_idx, total_steps))
        return tensors


class RefactorSupportC4Editor(RefactorSupportC3Editor):
    def __init__(
        self,
        pipe,
        config,
        support_rho: float = 0.85,
        soft_roi_start_weight: float = 0.75,
        soft_roi_end_weight: float = 0.10,
        anchor_hardness_start: float = 0.35,
        anchor_hardness_end: float = 1.0,
        support_soft_roi_blend: float = 0.50,
        anchor_enable_start_ratio: float = 0.20,
        anchor_enable_full_ratio: float = 0.50,
        support_soft_enable_start_ratio: float = 0.25,
        support_soft_enable_full_ratio: float = 0.60,
        support_floor_start_ratio: float = 0.45,
        support_floor_full_ratio: float = 0.80,
        support_floor_max: float = 0.20,
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
            support_soft_roi_blend=support_soft_roi_blend,
            anchor_enable_start_ratio=anchor_enable_start_ratio,
            anchor_enable_full_ratio=anchor_enable_full_ratio,
            support_soft_enable_start_ratio=support_soft_enable_start_ratio,
            support_soft_enable_full_ratio=support_soft_enable_full_ratio,
            diffedit_config=diffedit_config,
            inversion_backend=inversion_backend,
        )
        self.support_floor_start_ratio = validate_unit_interval(support_floor_start_ratio, "support_floor_start_ratio")
        self.support_floor_full_ratio = validate_unit_interval(support_floor_full_ratio, "support_floor_full_ratio")
        self.support_floor_max = validate_unit_interval(support_floor_max, "support_floor_max")
        if self.support_floor_full_ratio < self.support_floor_start_ratio:
            raise ValueError("support_floor_full_ratio must be >= support_floor_start_ratio")

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_support_c4_late_roi_floor_v1",
                "roi_mask_policy": "adaptive support with delayed source anchoring, delayed soft-aware support memory, and a late roi floor to avoid vanishing edit drive",
                "support_floor_policy": {
                    "start_ratio": self.support_floor_start_ratio,
                    "full_ratio": self.support_floor_full_ratio,
                    "max_strength": self.support_floor_max,
                    "formula": "F_t = alpha_t * lerp(roi_hard, roi_soft, beta * q_t), alpha_t is a late cosine gate",
                },
            }
        )
        return payload

    def _support_floor_gate(self, step_idx: int, total_steps: int) -> float:
        return cosine_gate(
            step_idx,
            total_steps,
            start_ratio=self.support_floor_start_ratio,
            full_ratio=self.support_floor_full_ratio,
        )

    def _support_floor_strength(self, step_idx: int, total_steps: int) -> float:
        return self.support_floor_max * self._support_floor_gate(step_idx, total_steps)

    def _support_floor_mask(
        self,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor | None:
        support_memory_roi = self._support_memory_roi(roi_mask, step_idx, total_steps)
        if support_memory_roi is None:
            return None
        return (self._support_floor_strength(step_idx, total_steps) * support_memory_roi).clamp(0.0, 1.0)

    def _extra_step_aux_tensors(
        self,
        method_name: str,
        aux_tensor: dict[str, torch.Tensor],
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> dict[str, torch.Tensor]:
        tensors = super()._extra_step_aux_tensors(method_name, aux_tensor, roi_mask, step_idx, total_steps)
        if roi_mask is None or method_name == "target_only" or not self._uses_diffedit_roi_cap(method_name):
            return tensors
        support_floor_mask = self._support_floor_mask(roi_mask, step_idx, total_steps)
        if support_floor_mask is None:
            return tensors
        tensors["support_floor_gate"] = torch.full_like(roi_mask, self._support_floor_gate(step_idx, total_steps))
        tensors["support_floor_strength"] = torch.full_like(roi_mask, self._support_floor_strength(step_idx, total_steps))
        return tensors

__all__ = [
    "RefactorSupportC1Editor",
    "RefactorSupportC2Editor",
    "RefactorSupportC3Editor",
    "RefactorSupportC4Editor",
]
