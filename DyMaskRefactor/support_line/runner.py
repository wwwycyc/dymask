from __future__ import annotations

import json
import sys
from pathlib import Path

from DyMaskRefactor.support_line.parser import build_parser
from DyMaskRefactor.support_line.execution import execute_support_run


def _resolve_config_json_path(argv_list: list[str]) -> Path | None:
    for idx, arg in enumerate(argv_list):
        if arg == "--config-json" and idx + 1 < len(argv_list):
            return Path(argv_list[idx + 1])
        if arg.startswith("--config-json="):
            return Path(arg.split("=", 1)[1])
    return None


def _load_config_defaults(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Config JSON must be an object: {path}")
    return payload


def main(argv: list[str] | None = None) -> None:
    argv_list = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    config_path = _resolve_config_json_path(argv_list)
    if config_path is not None:
        parser.set_defaults(**_load_config_defaults(config_path))
    args = parser.parse_args(argv_list)
    execute_support_run(args)


if __name__ == "__main__":
    main()
