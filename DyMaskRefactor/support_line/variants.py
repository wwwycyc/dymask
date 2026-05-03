from __future__ import annotations

"""Compatibility re-export for support-line variant implementations.

The concrete editor families live in focused modules:
- variants_progressive.py: C1-C4 schedule/memory progression variants
- variants_confidence.py: C5-C6d confidence/local-anchor variants
- variants_mainline.py: C5H0-C5H4 latest-mainline hard-core/deterministic-underedit variants

Keeping this file as a thin re-export preserves existing imports while letting
the implementation scale without a single monolithic variants.py.
"""

from DyMaskRefactor.support_line.variants_confidence import (
    RefactorSupportC5Editor,
    RefactorSupportC6BEditor,
    RefactorSupportC6CEditor,
    RefactorSupportC6DEditor,
    RefactorSupportC6Editor,
)
from DyMaskRefactor.support_line.variants_mainline import (
    RefactorSupportC5H0Editor,
    RefactorSupportC5H1Editor,
    RefactorSupportC5H2Editor,
    RefactorSupportC5H3Editor,
    RefactorSupportC5H4Editor,
)
from DyMaskRefactor.support_line.variants_progressive import (
    RefactorSupportC1Editor,
    RefactorSupportC2Editor,
    RefactorSupportC3Editor,
    RefactorSupportC4Editor,
)

__all__ = [
    "RefactorSupportC1Editor",
    "RefactorSupportC2Editor",
    "RefactorSupportC3Editor",
    "RefactorSupportC4Editor",
    "RefactorSupportC5Editor",
    "RefactorSupportC5H0Editor",
    "RefactorSupportC5H1Editor",
    "RefactorSupportC5H2Editor",
    "RefactorSupportC5H3Editor",
    "RefactorSupportC5H4Editor",
    "RefactorSupportC6Editor",
    "RefactorSupportC6BEditor",
    "RefactorSupportC6CEditor",
    "RefactorSupportC6DEditor",
]
