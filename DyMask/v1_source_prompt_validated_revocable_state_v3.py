from __future__ import annotations

import numpy as np
import torch

from .schemas import MaterializedSample
from .v1_source_prompt_validated_revocable_state_v2 import V1SourcePromptValidatedRevocableStateV2Editor


class V1SourcePromptValidatedRevocableStateV3Editor(V1SourcePromptValidatedRevocableStateV2Editor):
    def __init__(
        self,
        pipe,
        config,
        support_rho: float = 0.85,
        support_decay_mu: float = 0.80,
        support_decay_lambda: float = 0.10,
        support_lambda: float = 0.50,
        support_kappa: float = 8.0,
        support_alpha: float = 8.0,
        support_delta: float = 0.35,
        outside_veto_strength: float = 1.0,
        enable_support_competition: bool = True,
        support_keep_ratio: float = 0.20,
        inversion_backend=None,
    ) -> None:
        super().__init__(
            pipe,
            config,
            support_rho=support_rho,
            support_decay_mu=support_decay_mu,
            support_decay_lambda=support_decay_lambda,
            support_lambda=support_lambda,
            support_kappa=support_kappa,
            support_alpha=support_alpha,
            support_delta=support_delta,
            outside_veto_strength=outside_veto_strength,
            inversion_backend=inversion_backend,
        )
        self.enable_support_competition = bool(enable_support_competition)
        self.support_keep_ratio = float(support_keep_ratio)

    def _reference_prompt_metadata(self, sample: MaterializedSample) -> dict[str, object]:
        payload = super()._reference_prompt_metadata(sample)
        payload.update(
            {
                "variant": "source_prompt_validated_revocable_state_v3",
                "support_competition_enabled": self.enable_support_competition,
                "support_keep_ratio": self.support_keep_ratio,
                "mechanism_detail": (
                    "validated revocable state with zero-floor mask, outside veto, and support competition that keeps only "
                    "the highest-confidence support evidence"
                ),
            }
        )
        return payload

    def _competitive_support(self, evidence: torch.Tensor) -> torch.Tensor:
        if not self.enable_support_competition:
            return evidence
        keep_ratio = min(max(self.support_keep_ratio, 1e-4), 1.0)
        flat = evidence.flatten(1)
        token_count = flat.shape[1]
        keep_count = max(1, int(round(keep_ratio * token_count)))
        if keep_count >= token_count:
            return evidence
        topk_values = torch.topk(flat, k=keep_count, dim=1).values
        thresholds = topk_values[:, -1:]
        competitive = torch.where(flat >= thresholds, flat, torch.zeros_like(flat))
        max_values = competitive.amax(dim=1, keepdim=True).clamp(min=1e-6)
        competitive = competitive / max_values
        return competitive.view_as(evidence)

    def _support_evidence(
        self,
        method_name: str,
        dynamic_mask: torch.Tensor,
        aux_tensor: dict[str, torch.Tensor],
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        support_consistent, support_inconsistent, support_probability, support_evidence = super()._support_evidence(
            method_name,
            dynamic_mask,
            aux_tensor,
        )
        support_evidence = self._competitive_support(support_evidence)
        return support_consistent, support_inconsistent, support_probability, support_evidence
