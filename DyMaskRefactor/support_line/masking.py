from __future__ import annotations

import torch


class SupportMaskingMixin:
    def _support_memory_blend(self, step_idx: int, total_steps: int) -> float | None:
        return None

    def _support_memory_roi(
        self,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor | None:
        if roi_mask is None:
            return None
        blend = self._support_memory_blend(step_idx, total_steps)
        if blend is None:
            return None
        soft_roi_mask = self._resolve_soft_roi_mask(roi_mask)
        if soft_roi_mask is None:
            return roi_mask
        return torch.lerp(roi_mask, soft_roi_mask, blend).clamp(0.0, 1.0)

    def _support_floor_mask(
        self,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor | None:
        return None

    def _anchor_mask(
        self,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor | None:
        return self._adaptive_anchor_mask(roi_mask, step_idx, total_steps)

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
        return None

    def _after_effective_mask(
        self,
        method_name: str,
        support_state: torch.Tensor,
        effective_mask: torch.Tensor,
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> None:
        return None

    def _extra_step_aux_tensors(
        self,
        method_name: str,
        aux_tensor: dict[str, torch.Tensor],
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> dict[str, torch.Tensor]:
        return {}

    def _compose_effective_mask_from_aux(
        self,
        method_name: str,
        dynamic_mask: torch.Tensor,
        aux_tensor: dict[str, torch.Tensor],
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor:
        if roi_mask is None or method_name == "target_only" or not self._uses_diffedit_roi_cap(method_name):
            support_evidence = super()._compose_effective_mask_from_aux(
                method_name,
                dynamic_mask,
                aux_tensor,
                roi_mask,
                step_idx,
                total_steps,
            )
        else:
            support_memory_roi = self._support_memory_roi(roi_mask, step_idx, total_steps)
            if support_memory_roi is None:
                support_evidence = super()._compose_effective_mask_from_aux(
                    method_name,
                    dynamic_mask,
                    aux_tensor,
                    roi_mask,
                    step_idx,
                    total_steps,
                )
            else:
                support_evidence = (support_memory_roi * dynamic_mask).clamp(0.0, 1.0)
        self._after_support_evidence(
            method_name=method_name,
            dynamic_mask=dynamic_mask,
            aux_tensor=aux_tensor,
            roi_mask=roi_mask,
            step_idx=step_idx,
            total_steps=total_steps,
            support_evidence=support_evidence,
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
        if roi_mask is None or method_name == "target_only" or not self._uses_diffedit_roi_cap(method_name):
            effective_mask = support_state
        else:
            soft_roi_mask = self._resolve_soft_roi_mask(roi_mask)
            if soft_roi_mask is None:
                effective_mask = support_state
            else:
                effective_mask = torch.lerp(support_state, soft_roi_mask, self._soft_roi_weight(step_idx, total_steps)).clamp(
                    0.0, 1.0
                )
            support_floor_mask = self._support_floor_mask(roi_mask, step_idx, total_steps)
            if support_floor_mask is not None:
                effective_mask = torch.maximum(effective_mask, support_floor_mask).clamp(0.0, 1.0)
        self._after_effective_mask(
            method_name=method_name,
            support_state=support_state,
            effective_mask=effective_mask,
            roi_mask=roi_mask,
            step_idx=step_idx,
            total_steps=total_steps,
        )
        return effective_mask

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
        anchor_mask = self._anchor_mask(roi_mask, step_idx, total_steps)
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
        soft_roi_mask = self._resolve_soft_roi_mask(roi_mask)
        adaptive_anchor_mask = self._adaptive_anchor_mask(roi_mask, step_idx, total_steps)
        if soft_roi_mask is not None and adaptive_anchor_mask is not None:
            aux_tensor["soft_roi_mask"] = soft_roi_mask
            aux_tensor["adaptive_anchor_mask"] = adaptive_anchor_mask
            aux_tensor["soft_roi_blend"] = torch.full_like(roi_mask, self._soft_roi_weight(step_idx, total_steps))
            aux_tensor["anchor_hardness"] = torch.full_like(roi_mask, self._anchor_hardness(step_idx, total_steps))
        support_memory_roi = self._support_memory_roi(roi_mask, step_idx, total_steps)
        support_memory_blend = self._support_memory_blend(step_idx, total_steps)
        if support_memory_roi is not None and support_memory_blend is not None:
            aux_tensor["support_memory_roi"] = support_memory_roi
            aux_tensor["support_memory_soft_blend"] = torch.full_like(roi_mask, support_memory_blend)
        support_floor_mask = self._support_floor_mask(roi_mask, step_idx, total_steps)
        if support_floor_mask is not None:
            aux_tensor["support_floor_mask"] = support_floor_mask
        aux_tensor.update(self._extra_step_aux_tensors(method_name, aux_tensor, roi_mask, step_idx, total_steps))
        return aux_tensor
