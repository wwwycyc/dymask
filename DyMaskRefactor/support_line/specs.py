from __future__ import annotations

from argparse import Namespace
from dataclasses import dataclass
from importlib import import_module
from typing import Any


COMMON_SUPPORT_ARG_NAMES = (
    "support_rho",
    "soft_roi_start_weight",
    "soft_roi_end_weight",
    "anchor_hardness_start",
    "anchor_hardness_end",
)


def _resolve_editor_class(editor_ref: str | type[Any]) -> type[Any]:
    if not isinstance(editor_ref, str):
        return editor_ref
    module_name, separator, attr_name = editor_ref.partition(":")
    if not separator or not module_name or not attr_name:
        raise ValueError(f"Unsupported editor reference: {editor_ref}")
    module = import_module(module_name)
    editor_cls = getattr(module, attr_name)
    if not isinstance(editor_cls, type):
        raise TypeError(f"Resolved editor is not a class: {editor_ref}")
    return editor_cls


@dataclass(frozen=True)
class SupportVariantSpec:
    key: str
    display_name: str
    editor_ref: str | type[Any]
    variant_name: str
    description: str
    run_prefix: str
    default_output_root: str
    extra_arg_names: tuple[str, ...] = ()

    @property
    def editor_cls(self) -> type[Any]:
        editor_cls = _resolve_editor_class(self.editor_ref)
        if editor_cls is not self.editor_ref:
            object.__setattr__(self, "editor_ref", editor_cls)
        return editor_cls

    def editor_kwargs(self, args: Namespace) -> dict[str, Any]:
        kwargs = {name: getattr(args, name) for name in COMMON_SUPPORT_ARG_NAMES}
        kwargs.update({name: getattr(args, name) for name in self.extra_arg_names})
        return kwargs

    def variant_payload(self, args: Namespace, diffedit_config) -> dict[str, Any]:
        return {
            "variant_key": self.key,
            "variant_name": self.variant_name,
            "display_name": self.display_name,
            "description": self.description,
            "editor_class": self.editor_cls.__name__,
            "editor_kwargs": self.editor_kwargs(args),
            "diffedit": diffedit_config.to_dict(),
            "ddim_inversion_prompt_mode": "source_prompt",
            "reference_branch_prompt_mode": "source_prompt",
            "attention_prompt_mode": "target_prompt",
            "refactor_package": "DyMaskRefactor",
        }
