from __future__ import annotations

import json
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps


def decode_piebench_rle(rle: list[int], height: int = 512, width: int = 512) -> np.ndarray:
    """Decode PIE-Bench RLE mask [start0, len0, start1, len1, ...] to H×W uint8 array."""
    mask = np.zeros(height * width, dtype=np.uint8)
    for i in range(0, len(rle) - 1, 2):
        start, length = rle[i], rle[i + 1]
        mask[start:start + length] = 1
    mask = mask.reshape(height, width)
    # align with PnPI: force boundary to 1 to avoid annotation errors
    mask[0, :] = 1
    mask[-1, :] = 1
    mask[:, 0] = 1
    mask[:, -1] = 1
    return mask


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def timestamp_to_minute() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def slugify(text: str, max_length: int = 64) -> str:
    normalized = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in text.strip())
    normalized = "_".join(filter(None, normalized.split("_")))
    return normalized[:max_length] if normalized else "item"


def make_timestamped_run_dir(root: Path, prefix: str = "run") -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    base = root / f"{prefix}_{stamp}"
    candidate = base
    counter = 1
    while candidate.exists():
        candidate = root / f"{prefix}_{stamp}_{counter:02d}"
        counter += 1
    candidate.mkdir(parents=True, exist_ok=False)
    return candidate


def save_json(path: Path, payload: dict) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def save_csv_records(path: Path, rows: Iterable[dict]) -> None:
    ensure_parent(path)
    rows = list(rows)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    import pandas as pd

    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def decode_image_bytes(blob: bytes) -> Image.Image:
    return Image.open(BytesIO(blob)).convert("RGB")


def center_crop_square(image: Image.Image) -> Image.Image:
    width, height = image.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    return image.crop((left, top, left + side, top + side))


def prepare_image(image: Image.Image, size: int) -> Image.Image:
    return center_crop_square(image).resize((size, size), Image.Resampling.LANCZOS)


def image_to_numpy(image: Image.Image | np.ndarray) -> np.ndarray:
    if isinstance(image, Image.Image):
        return np.asarray(image.convert("RGB"))
    array = np.asarray(image)
    if array.dtype != np.uint8:
        array = np.clip(array, 0, 255).astype(np.uint8)
    return array


def numpy_to_image(array: np.ndarray) -> Image.Image:
    return Image.fromarray(image_to_numpy(array))


def save_image(path: Path, image: Image.Image | np.ndarray) -> None:
    ensure_parent(path)
    numpy_to_image(image).save(path)


def normalize_map(array: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    array = array.astype(np.float32)
    min_value = float(array.min())
    max_value = float(array.max())
    if max_value - min_value < eps:
        return np.zeros_like(array, dtype=np.float32)
    return (array - min_value) / (max_value - min_value)


def mask_to_rgb(mask: np.ndarray) -> np.ndarray:
    mask = normalize_map(mask)
    mask_uint8 = np.clip(mask * 255.0, 0, 255).astype(np.uint8)
    return np.stack([mask_uint8, mask_uint8, mask_uint8], axis=-1)


def make_labeled_strip(images: list[np.ndarray], labels: list[str]) -> np.ndarray:
    if not images:
        raise ValueError("images must not be empty")
    font = ImageFont.load_default()
    rendered: list[Image.Image] = []
    label_height = 28
    for image, label in zip(images, labels):
        canvas = Image.new("RGB", (image.shape[1], image.shape[0] + label_height), color="white")
        canvas.paste(numpy_to_image(image), (0, label_height))
        drawer = ImageDraw.Draw(canvas)
        drawer.text((8, 6), label, fill="black", font=font)
        rendered.append(canvas)
    width = sum(image.width for image in rendered)
    height = max(image.height for image in rendered)
    strip = Image.new("RGB", (width, height), color="white")
    offset = 0
    for image in rendered:
        strip.paste(image, (offset, 0))
        offset += image.width
    return np.asarray(strip)


def summarize_step_maps(step_maps: list[np.ndarray], labels: tuple[str, ...] = ("early", "mid", "late")) -> np.ndarray | None:
    if not step_maps:
        return None
    sample_count = max(1, len(labels))
    indices = np.linspace(0, len(step_maps) - 1, num=sample_count, dtype=int).tolist()
    images = [mask_to_rgb(step_maps[index]) for index in indices]
    return make_labeled_strip(images, list(labels))


def compose_labeled_overview(
    items: list[tuple[str, Image.Image | np.ndarray]],
    columns: int = 4,
    tile_size: tuple[int, int] = (512, 512),
    title: str | None = None,
) -> np.ndarray:
    if not items:
        raise ValueError("items must not be empty")

    columns = max(1, columns)
    tile_width, tile_height = tile_size
    label_height = 32
    gap = 16
    outer_padding = 20
    rows = (len(items) + columns - 1) // columns
    canvas_width = outer_padding * 2 + columns * tile_width + (columns - 1) * gap
    title_height = 0 if not title else 48
    row_height = tile_height + label_height
    canvas_height = outer_padding * 2 + title_height + rows * row_height + (rows - 1) * gap

    canvas = Image.new("RGB", (canvas_width, canvas_height), color="white")
    drawer = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()

    if title:
        drawer.text((outer_padding, outer_padding), title, fill="black", font=font)

    start_y = outer_padding + title_height
    inner_padding = 8
    content_width = tile_width - inner_padding * 2
    content_height = tile_height - inner_padding * 2

    for index, (label, image) in enumerate(items):
        row = index // columns
        col = index % columns
        x = outer_padding + col * (tile_width + gap)
        y = start_y + row * (row_height + gap)

        drawer.rectangle(
            (x, y, x + tile_width - 1, y + label_height + tile_height - 1),
            outline="black",
            width=1,
        )
        drawer.text((x + 8, y + 8), label, fill="black", font=font)

        tile = Image.new("RGB", (content_width, content_height), color="white")
        fitted = ImageOps.contain(numpy_to_image(image), (content_width, content_height))
        offset_x = (content_width - fitted.width) // 2
        offset_y = (content_height - fitted.height) // 2
        tile.paste(fitted, (offset_x, offset_y))
        canvas.paste(tile, (x + inner_padding, y + label_height + inner_padding))

    return np.asarray(canvas)
