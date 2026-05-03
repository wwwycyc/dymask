from __future__ import annotations

"""Compatibility re-export for latest-mainline support variants.

The concrete latest-mainline implementation now lives in focused modules:
- mainline_hardcore.py: C5H0-C5H1 hard-core support and thin-boundary variants
- mainline_roi.py: C5H2 deterministic DiffEdit ROI cache and core/boundary decomposition
- mainline_underedit.py: C5H3-C5H4 under-edit rescue and temporal guard variants

Keeping this file as a thin re-export preserves existing imports from registry,
runner wiring, and notebooks while letting the latest mainline evolve in
smaller concern-focused modules.
"""

from DyMaskRefactor.support_line.mainline_hardcore import (
    RefactorSupportC5H0Editor,
    RefactorSupportC5H1Editor,
)
from DyMaskRefactor.support_line.mainline_roi import RefactorSupportC5H2Editor
from DyMaskRefactor.support_line.mainline_underedit import (
    RefactorSupportC5H3Editor,
    RefactorSupportC5H4Editor,
)

__all__ = [
    "RefactorSupportC5H0Editor",
    "RefactorSupportC5H1Editor",
    "RefactorSupportC5H2Editor",
    "RefactorSupportC5H3Editor",
    "RefactorSupportC5H4Editor",
]
