from __future__ import annotations

from .operator_routing_v2 import (
    OperatorRoutingV2Config,
    apply_operator_routing_v2_eps,
    build_operator_routing_v2_weights,
)
from .preservation_field_v2 import (
    PreservationFieldV2Config,
    build_preservation_field_v2,
    build_source_consistency_field_v2,
)
from .schemas import MaterializedSample
from .transformation_field_v2 import (
    TransformationFieldV2Config,
    build_transformation_field_v2,
)
from .v1_source_prompt_source_anchored_hard_roi import V1SourcePromptSourceAnchoredHardRoiEditor

import torch


class V1SourcePromptSourceAnchoredOperatorRoutingV2Editor(V1SourcePromptSourceAnchoredHardRoiEditor):
    def __init__(
        self,
        pipe,
        config,
        transform_discrepancy_weight: float = 1.0,
        transform_attention_weight: float = 1.0,
        preserve_gate_power: float = 1.0,
        interiority_bias: float = 1.0,
        boundary_bias: float = 1.0,
        disable_stabilize_operator: bool = False,
        diffedit_config=None,
        inversion_backend=None,
    ) -> None:
        super().__init__(
            pipe,
            config,
            diffedit_config=diffedit_config,
            inversion_backend=inversion_backend,
        )
        self.transform_config = TransformationFieldV2Config(
            discrepancy_weight=float(transform_discrepancy_weight),
            attention_weight=float(transform_attention_weight),
        )
        self.preservation_config = PreservationFieldV2Config(
            transform_gate_power=float(preserve_gate_power),
        )
        self.routing_config = OperatorRoutingV2Config(
            interiority_bias=float(interiority_bias),
            boundary_bias=float(boundary_bias),
            use_stabilize_operator=not bool(disable_stabilize_operator),
        )
        self._latest_routing_weights: dict[str, torch.Tensor] | None = None

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_operator_routing_v2",
                "mechanism": "Hard ROI support with outside-roi source anchoring and roi-internal epsilon-level rewrite/stabilize/preserve routing",
                "transformation_formula": "T_t = Norm(w_d * D_t + w_a * A_t)",
                "source_consistency_formula": "S_t = 1 - C_t",
                "preservation_formula": "P_t = Norm(S_t * (1 - T_t)^p)",
                "routing_formula": {
                    "rewrite": "roi * T_t * (1 + b_i * interiority + (1-S_t))",
                    "stabilize": "roi * sqrt(T_t * S_t) * (1 + b_b * boundaryness)",
                    "preserve": "roi * P_t * (1 + b_b * boundaryness)",
                },
                "execution_formula": "eps = (1-roi) * eps_src + roi * [w_r * eps_tar + w_s * eps_stabilize + w_p * eps_src]",
                "transform_discrepancy_weight": self.transform_config.discrepancy_weight,
                "transform_attention_weight": self.transform_config.attention_weight,
                "preserve_gate_power": self.preservation_config.transform_gate_power,
                "interiority_bias": self.routing_config.interiority_bias,
                "boundary_bias": self.routing_config.boundary_bias,
                "use_stabilize_operator": self.routing_config.use_stabilize_operator,
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
        config = TransformationFieldV2Config(
            discrepancy_weight=self.transform_config.discrepancy_weight,
            attention_weight=attention_weight,
        )
        return build_transformation_field_v2(
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
        source_consistency = build_source_consistency_field_v2(aux_tensor["latent_drift"])
        preservation_field = build_preservation_field_v2(
            latent_drift=aux_tensor["latent_drift"],
            transformation_field=transformation_field,
            config=self.preservation_config,
        )
        routing_weights = build_operator_routing_v2_weights(
            transformation_field=transformation_field,
            source_consistency=source_consistency,
            preservation_field=preservation_field,
            roi_mask=roi_mask,
            config=self.routing_config,
        )
        self._latest_routing_weights = routing_weights
        aux_tensor.update(routing_weights)
        return roi_mask

    def _step_latents_from_mask(
        self,
        method_name: str,
        latents: torch.Tensor,
        timestep: torch.Tensor,
        eps_src: torch.Tensor,
        eps_tar: torch.Tensor,
        effective_mask: torch.Tensor,
        roi_mask: torch.Tensor | None,
        source_latents: list[torch.Tensor],
        step_idx: int,
        total_steps: int,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        if (
            roi_mask is None
            or method_name == "target_only"
            or not self._uses_diffedit_roi_cap(method_name)
            or self._latest_routing_weights is None
        ):
            return super()._step_latents_from_mask(
                method_name=method_name,
                latents=latents,
                timestep=timestep,
                eps_src=eps_src,
                eps_tar=eps_tar,
                effective_mask=effective_mask,
                roi_mask=roi_mask,
                source_latents=source_latents,
                step_idx=step_idx,
                total_steps=total_steps,
            )

        eps = apply_operator_routing_v2_eps(
            eps_src=eps_src,
            eps_tar=eps_tar,
            routing_weights=self._latest_routing_weights,
        )
        prev_latents = self.pipe.scheduler.step(eps, timestep, latents).prev_sample
        return eps, prev_latents
