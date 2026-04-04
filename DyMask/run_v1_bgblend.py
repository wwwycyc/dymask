from __future__ import annotations

import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import DyMask.run_v1 as base_run

from DyMask.v1_bgblend import V1BackgroundBlendEditor


def _has_output_root_arg(argv: list[str]) -> bool:
    return any(arg == "--output-root" or arg.startswith("--output-root=") for arg in argv)


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not _has_output_root_arg(argv):
        argv.extend(["--output-root", "runs/dymask_v1_bgblend"])

    original_editor = base_run.V1Editor
    base_run.V1Editor = V1BackgroundBlendEditor
    try:
        base_run.main(argv)
    finally:
        base_run.V1Editor = original_editor


if __name__ == "__main__":
    main()
