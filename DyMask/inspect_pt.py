from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import torch


def summarize_object(obj: Any, depth: int = 0, max_items: int = 5) -> list[str]:
    indent = "  " * depth
    lines: list[str] = []

    if torch.is_tensor(obj):
        lines.append(
            f"{indent}Tensor(shape={tuple(obj.shape)}, dtype={obj.dtype}, device={obj.device}, "
            f"min={float(obj.min()):.6f}, max={float(obj.max()):.6f})"
        )
        return lines

    if isinstance(obj, dict):
        lines.append(f"{indent}dict(len={len(obj)})")
        for index, (key, value) in enumerate(obj.items()):
            if index >= max_items:
                lines.append(f"{indent}  ...")
                break
            lines.append(f"{indent}  [{key!r}]")
            lines.extend(summarize_object(value, depth + 2, max_items))
        return lines

    if isinstance(obj, (list, tuple)):
        lines.append(f"{indent}{type(obj).__name__}(len={len(obj)})")
        for index, value in enumerate(obj[:max_items]):
            lines.append(f"{indent}  [{index}]")
            lines.extend(summarize_object(value, depth + 2, max_items))
        if len(obj) > max_items:
            lines.append(f"{indent}  ...")
        return lines

    lines.append(f"{indent}{type(obj).__name__}: {obj!r}")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect a .pt file saved by PyTorch.")
    parser.add_argument("pt_path", help="Path to a .pt file.")
    parser.add_argument("--max-items", type=int, default=5, help="Maximum number of items to print per container.")
    args = parser.parse_args()

    pt_path = Path(args.pt_path)
    if not pt_path.exists():
        raise FileNotFoundError(f".pt file not found: {pt_path}")

    payload = torch.load(pt_path, map_location="cpu", weights_only=True)
    print(f"path: {pt_path}")
    print(f"type: {type(payload).__name__}")
    for line in summarize_object(payload, max_items=args.max_items):
        print(line)


if __name__ == "__main__":
    main()
