from __future__ import annotations

from .operator_routing import (
    OperatorRoutingConfig,
    RegionRoleConfig,
    apply_operator_routing,
    build_operator_routing_weights,
)
from .preservation_field import build_source_consistency_field
from .schemas import MaterializedSample
from .transformation_field import TransformationFieldConfig, build_transformation_field
from .v1_source_prompt_source_anchored_hard_roi import V1SourcePromptSourceAnchoredHardRoiEditor

import torch


class V1SourcePromptSourceAnchoredOperatorRoutingEditor(V1SourcePromptSourceAnchoredHardRoiEditor):
    def __init__(
        self,
        pipe,
        config,
        transform_discrepancy_weight: float = 1.0,
        transform_attention_weight: float = 1.0,
        core_kernel_size: int = 5,
        disable_boundary_band: bool = False,
        rewrite_boundary_scale: float = 0.5,
        stabilize_scale: float = 1.0,
        preserve_scale: float = 1.0,
        disable_stabilize_operator: bool = False,
        frequency_kernel_size: int = 5,
        stabilize_low_source_weight: float = 0.35,
        stabilize_high_source_weight: float = 0.75,
        diffedit_config=None,
        inversion_backend=None,
    ) -> None:
        super().__init__(
            pipe,
            config,
            diffedit_config=diffedit_config,
            inversion_backend=inversion_backend,
        )
        self.transform_config = TransformationFieldConfig(
            discrepancy_weight=float(transform_discrepancy_weight),
            attention_weight=float(transform_attention_weight),
        )
        self.routing_config = OperatorRoutingConfig(
            role=RegionRoleConfig(
                core_kernel_size=int(core_kernel_size),
                use_boundary_band=not bool(disable_boundary_band),
            ),
            rewrite_boundary_scale=float(rewrite_boundary_scale),
            stabilize_scale=float(stabilize_scale),
            preserve_scale=float(preserve_scale),
            use_stabilize_operator=not bool(disable_stabilize_operator),
            frequency_kernel_size=int(frequency_kernel_size),
            stabilize_low_source_weight=float(stabilize_low_source_weight),
            stabilize_high_source_weight=float(stabilize_high_source_weight),
        )
        self._latest_routing_weights: dict[str, torch.Tensor] | None = None

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_operator_routing_v1",
                "mechanism": "Hard ROI support with outside-roi source anchoring and roi-internal rewrite/stabilize/preserve operator routing",
                "transformation_formula": "T_t = (w_d * D_t + w_a * A_t) / (w_d + w_a)",
                "source_consistency_formula": "S_t = 1 - C_t",
                "routing_logits": {
                    "rewrite": "core * T_t + lambda_b * boundary * T_t * (1-S_t)",
                    "stabilize": "boundary * sqrt(T_t * S_t)",
                    "preserve": "roi * S_t * (1-T_t)",
                },
                "execution_formula": "z_{t-1} = roi * [w_r * rewrite + w_s * stabilize + w_p * preserve] + (1-roi) * z_{t-1}^{src}",
                "transform_discrepancy_weight": self.transform_config.discrepancy_weight,
                "transform_attention_weight": self.transform_config.attention_weight,
                "core_kernel_size": self.routing_config.role.core_kernel_size,
                "use_boundary_band": self.routing_config.role.use_boundary_band,
                "rewrite_boundary_scale": self.routing_config.rewrite_boundary_scale,
                "stabilize_scale": self.routing_config.stabilize_scale,
                "preserve_scale": self.routing_config.preserve_scale,
                "use_stabilize_operator": self.routing_config.use_stabilize_operator,
                "frequency_kernel_size": self.routing_config.frequency_kernel_size,
                "stabilize_low_source_weight": self.routing_config.stabilize_low_source_weight,
                "stabilize_high_source_weight": self.routing_config.stabilize_high_source_weight,
            }
        )
        return payload

    def _transformation_field_for_method(
        self,
        method_name: str,
        aux_tensor: dict[str, torch.Tensor],
    ) -> torch.Tensor:
        attention_weight = self.transform_config.attention_weight
        if method_name not in {"discrepancy_attention", "full_dynamic_mask"}:
            attention_weight = 0.0
        config = TransformationFieldConfig(
            discrepancy_weight=self.transform_config.discrepancy_weight,
            attention_weight=attention_weight,
        )
        return build_transformation_field(
            discrepancy=aux_tensor["discrepancy"],
            attention=aux_tensor["attention"],
            config=config,
        )

    def _compose_effective_mask_from_aux(
        self,
        method_name: str,
        dynamic_mask: torch.Tensor,
        aux_tensor: dict[str, torch.Tensor],
        roi_mask: torch.Tensor | None,
        step_idx: int,
        total_steps: int,
    ) -> torch.Tensor:
        if method_name == "target_only" or roi_mask is None or not self._uses_diffedit_roi_cap(method_name):
            self._latest_routing_weights = None
            return dynamic_mask

        transformation_field = self._transformation_field_for_method(method_name, aux_tensor)
        source_consistency = build_source_consistency_field(aux_tensor["latent_drift"])
        routing_weights = build_operator_routing_weights(
            transformation_field=transformation_field,
            source_consistency=source_consistency,
            roi_mask=roi_mask,
            config=self.routing_config,
        )
        self._latest_routing_weights = routing_weights
        aux_tensor.update(routing_weights)
        return roi_mask

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

        next_source_idx = min(step_idx + 1, len(source_latents) - 1)
        source_anchor = source_latents[next_source_idx]
        if source_anchor.shape != prev_latents.shape:
            raise ValueError(
                f"source anchor shape mismatch: expected {tuple(prev_latents.shape)}, got {tuple(source_anchor.shape)}"
            )
        if self._latest_routing_weights is None:
            return roi_mask * prev_latents + (1.0 - roi_mask) * source_anchor
        return apply_operator_routing(
            edited_latents=prev_latents,
            source_latents=source_anchor,
            routing_weights=self._latest_routing_weights,
            config=self.routing_config,
        )
