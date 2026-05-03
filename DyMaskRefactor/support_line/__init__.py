"""Support-line refactor package.

Keep this package init light. Most symbols are exposed through lazy imports so
that tooling such as parser inspection or registry listing does not immediately
pull in the full DyMask runtime stack.
"""

from __future__ import annotations

from importlib import import_module


_EXPORTS = {
    'build_config': ('DyMaskRefactor.support_line.configuration', 'build_config'),
    'build_diffedit_config': ('DyMaskRefactor.support_line.configuration', 'build_diffedit_config'),
    'resolve_run_limit': ('DyMaskRefactor.support_line.configuration', 'resolve_run_limit'),
    'build_parser': ('DyMaskRefactor.support_line.parser', 'build_parser'),
    'PreparedSupportRun': ('DyMaskRefactor.support_line.execution', 'PreparedSupportRun'),
    'prepare_support_run': ('DyMaskRefactor.support_line.execution', 'prepare_support_run'),
    'execute_support_run': ('DyMaskRefactor.support_line.execution', 'execute_support_run'),
    'SupportMaskingMixin': ('DyMaskRefactor.support_line.masking', 'SupportMaskingMixin'),
    'SupportRoiMixin': ('DyMaskRefactor.support_line.roi', 'SupportRoiMixin'),
    'RefactorSupportBaselineEditor': ('DyMaskRefactor.support_line.base', 'RefactorSupportBaselineEditor'),
    'RefactorSupportC1Editor': ('DyMaskRefactor.support_line.variants_progressive', 'RefactorSupportC1Editor'),
    'RefactorSupportC2Editor': ('DyMaskRefactor.support_line.variants_progressive', 'RefactorSupportC2Editor'),
    'RefactorSupportC3Editor': ('DyMaskRefactor.support_line.variants_progressive', 'RefactorSupportC3Editor'),
    'RefactorSupportC4Editor': ('DyMaskRefactor.support_line.variants_progressive', 'RefactorSupportC4Editor'),
    'RefactorSupportC5Editor': ('DyMaskRefactor.support_line.variants_confidence', 'RefactorSupportC5Editor'),
    'RefactorSupportC5H0Editor': ('DyMaskRefactor.support_line.variants_mainline', 'RefactorSupportC5H0Editor'),
    'RefactorSupportC5H1Editor': ('DyMaskRefactor.support_line.variants_mainline', 'RefactorSupportC5H1Editor'),
    'RefactorSupportC5H2Editor': ('DyMaskRefactor.support_line.variants_mainline', 'RefactorSupportC5H2Editor'),
    'RefactorSupportC5H3Editor': ('DyMaskRefactor.support_line.variants_mainline', 'RefactorSupportC5H3Editor'),
    'RefactorSupportC5H4Editor': ('DyMaskRefactor.support_line.variants_mainline', 'RefactorSupportC5H4Editor'),
    'RefactorSupportC6Editor': ('DyMaskRefactor.support_line.variants_confidence', 'RefactorSupportC6Editor'),
    'RefactorSupportC6BEditor': ('DyMaskRefactor.support_line.variants_confidence', 'RefactorSupportC6BEditor'),
    'RefactorSupportC6CEditor': ('DyMaskRefactor.support_line.variants_confidence', 'RefactorSupportC6CEditor'),
    'RefactorSupportC6DEditor': ('DyMaskRefactor.support_line.variants_confidence', 'RefactorSupportC6DEditor'),
    'SUPPORT_VARIANTS': ('DyMaskRefactor.support_line.registry', 'SUPPORT_VARIANTS'),
    'get_support_variant': ('DyMaskRefactor.support_line.registry', 'get_support_variant'),
    'main': ('DyMaskRefactor.support_line.runner', 'main'),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str):
    try:
        module_name, attr_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f'module {__name__!r} has no attribute {name!r}') from exc
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
