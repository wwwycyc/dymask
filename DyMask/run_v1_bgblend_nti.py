from __future__ import annotations

import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from DyMask.run_v1_bgblend import main as run_main


def main() -> None:
    run_main([*sys.argv[1:], "--inversion-backend", "nti"])


if __name__ == "__main__":
    main()
