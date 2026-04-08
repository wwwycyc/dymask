from __future__ import annotations

import torch

from .boundary_stabilization_field_v3 import BoundaryStabilizationFieldV3Config
from .operator_routing_v3 import (
    OperatorRoutingV3Config,
    apply_operator_routing_v3_eps,
    build_operator_routing_v3_state,
)
from .preservation_field_v2 import build_source_consistency_field_v2
from .schemas import MaterializedSample
from .transformation_field_v2 import (
    TransformationFieldV2Config,
    build_transformation_field_v2,
)
from .v1_source_prompt_source_anchored_hard_roi import V1SourcePromptSourceAnchoredHardRoiEditor


class V1SourcePromptSourceAnchoredOperatorRoutingV3Editor(V1SourcePromptSourceAnchoredHardRoiEditor):
    def __init__(
        self,
        pipe,
        config,
        transform_discrepancy_weight: float = 1.0,
        transform_attention_weight: float = 1.0,
        boundary_gate_power: float = 1.0,
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
        self.routing_config = OperatorRoutingV3Config(
            boundary_stabilization=BoundaryStabilizationFieldV3Config(
                transform_gate_power=float(boundary_gate_power),
            )
        )
        self._latest_routing_state: dict[str, torch.Tensor] | None = None

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_source_anchored_operator_routing_v3",
                "mechanism": "Hard ROI support with outside-roi source anchoring and roi-internal core-rewrite plus boundary-conditioned stabilize routing",
                "transformation_formula": "T_t = Norm(w_d * D_t + w_a * A_t)",
                "source_consistency_formula": "S_t = 1 - C_t",
                "boundary_formula": "B_t = roi * boundaryness * S_t * (1 - T_t)^p",
                "execution_formula": "eps = (1-roi) * eps_src + roi * [(1-B_t) * eps_tar + B_t * eps_stabilize]",
                "transform_discrepancy_weight": self.transform_config.discrepancy_weight,
                "transform_attention_weight": self.transform_config.attention_weight,
                "boundary_gate_power": self.routing_config.boundary_stabilization.transform_gate_power,
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
            self._latest_routing_state = None
            return dynamic_mask

        transformation_field = self._transformation_field_for_method(method_name, aux_tensor)
        source_consistency = build_source_consistency_field_v2(aux_tensor["latent_drift"])
        routing_state = build_operator_routing_v3_state(
            transformation_field=transformation_field,
            source_consistency=source_consistency,
            roi_mask=roi_mask,
            config=self.routing_config,
        )
        self._latest_routing_state = routing_state
        aux_tensor.update(routing_state)
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
            or self._latest_routing_state is None
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

        eps = apply_operator_routing_v3_eps(
            eps_src=eps_src,
            eps_tar=eps_tar,
            routing_state=self._latest_routing_state,
        )
        prev_latents = self.pipe.scheduler.step(eps, timestep, latents).prev_sample
        return eps, prev_latents
