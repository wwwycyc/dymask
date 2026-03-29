#!/usr/bin/env python
"""Generate comparison visualizations and metric tables for a run directory."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


METHODS = [
    ("target_only",           "target-only"),
    ("global_blend",          "global blend"),
    ("discrepancy_only",      "D_t"),
    ("discrepancy_attention", "D_t + A_t"),
    ("discrepancy_latent",    "D_t + C_t"),
    ("full_dynamic_mask",     "Full"),
]


def find_method_dir(sample_dir: Path, method_key: str) -> Path | None:
    d = sample_dir / method_key
    if d.exists():
        return d
    if method_key == "global_blend":
        for child in sorted(sample_dir.iterdir()):
            if child.is_dir() and child.name.startswith("global_blend"):
                return child
    return None


def load_img(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"))


def make_sample_grid(sample_dir: Path) -> np.ndarray | None:
    source_path = sample_dir / "source.png"
    if not source_path.exists():
        return None

    images: list[tuple[str, np.ndarray]] = [("source", load_img(source_path))]
    for method_key, label in METHODS:
        mdir = find_method_dir(sample_dir, method_key)
        if mdir is None:
            continue
        edited = mdir / "edited.png"
        if edited.exists():
            images.append((label, load_img(edited)))

    if len(images) < 2:
        return None

    n = len(images)
    fig, axes = plt.subplots(1, n, figsize=(n * 3, 3.6))
    if n == 1:
        axes = [axes]
    for ax, (label, img) in zip(axes, images):
        ax.imshow(img)
        ax.set_title(label, fontsize=9, pad=4)
        ax.axis("off")
    fig.suptitle(sample_dir.name, fontsize=7, y=0.02)
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    fig.canvas.draw()
    buf = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8)
    w, h = fig.canvas.get_width_height()
    grid = buf.reshape(h, w, 4)[:, :, :3]
    plt.close(fig)
    return grid


def make_metric_bar_chart(summary: list[dict], out_path: Path) -> None:
    methods     = [row["method_name"] for row in summary]
    clip_scores = [row.get("clip_score_mean") or 0.0 for row in summary]
    src_lpips   = [row.get("source_lpips_mean") or 0.0 for row in summary]
    src_psnr    = [row.get("source_psnr_mean") or 0.0 for row in summary]
    out_lpips   = [row.get("outside_lpips_mean") for row in summary]
    out_psnr    = [row.get("outside_psnr_mean") for row in summary]
    locality    = [row.get("locality_ratio_mean") for row in summary]

    has_masked = any(v is not None for v in out_lpips)
    n_charts = 6 if has_masked else 3
    x = np.arange(len(methods))
    fig, axes = plt.subplots(1, n_charts, figsize=(n_charts * 3, 5))
    if n_charts == 1:
        axes = [axes]
    fig.suptitle("Method Comparison", fontsize=13, y=1.01)

    colors = plt.cm.tab10(np.linspace(0, 0.6, len(methods)))

    chart_specs = [
        (clip_scores, "CLIP Score (↑)", True),
        (src_psnr,    "Source PSNR dB (↑)", True),
        (src_lpips,   "Source LPIPS (↓)", False),
    ]
    if has_masked:
        chart_specs += [
            ([v or 0.0 for v in out_psnr],  "Outside PSNR dB (↑)", True),
            ([v or 0.0 for v in out_lpips], "Outside LPIPS (↓)", False),
            ([v or 0.0 for v in locality],  "Locality Ratio (↑)", True),
        ]

    for ax, (values, title, higher_better) in zip(axes, chart_specs):
        bars = ax.bar(x, values, color=colors, edgecolor="white", linewidth=0.5)
        ax.set_xticks(x)
        ax.set_xticklabels(methods, rotation=25, ha="right", fontsize=9)
        ax.set_title(title, fontsize=11)
        ax.set_ylabel(title.split(" (")[0])
        for bar, val in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(values) * 0.01,
                f"{val:.4f}",
                ha="center", va="bottom", fontsize=7,
            )
        best_idx = int(np.argmax(values) if higher_better else np.argmin(values))
        bars[best_idx].set_edgecolor("red")
        bars[best_idx].set_linewidth(2.5)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved metric chart -> {out_path}")


def make_metric_table_image(summary: list[dict], out_path: Path) -> None:
    methods = [row["method_name"] for row in summary]
    has_masked = any(row.get("outside_lpips_mean") is not None for row in summary)

    cols = ["CLIP Score", "Src PSNR", "Src LPIPS"]
    keys = ["clip_score_mean", "source_psnr_mean", "source_lpips_mean"]
    higher = [True, True, False]
    if has_masked:
        cols += ["Out PSNR", "Out LPIPS", "Locality"]
        keys += ["outside_psnr_mean", "outside_lpips_mean", "locality_ratio_mean"]
        higher += [True, False, True]

    cell_text = []
    for row in summary:
        cell_text.append([f"{row.get(k) or 0.0:.4f}" for k in keys])

    fig, ax = plt.subplots(figsize=(max(9, len(cols) * 1.8), 0.5 * len(methods) + 1.5))
    ax.axis("off")
    tbl = ax.table(
        cellText=cell_text,
        rowLabels=methods,
        colLabels=cols,
        cellLoc="center",
        loc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    tbl.scale(1.2, 1.6)

    for col_idx, (key, hi) in enumerate(zip(keys, higher)):
        vals = [row.get(key) or 0.0 for row in summary]
        best = int(np.argmax(vals) if hi else np.argmin(vals))
        cell = tbl[(best + 1, col_idx)]
        cell.set_facecolor("#d4f0d4")

    fig.suptitle("Metric Summary Table", fontsize=12, y=0.98)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved metric table -> {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", help="Path to a v1_* run directory")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    summary_path = run_dir / "metrics_five_methods_summary.json"
    if not summary_path.exists():
        summary_path = run_dir / "metrics_summary.json"

    summary = json.loads(summary_path.read_text(encoding="utf-8"))["summary"]
    summary = [r for r in summary if r["method_name"] != "phase0_reconstruction"]

    make_metric_bar_chart(summary, run_dir / "metric_comparison.png")
    make_metric_table_image(summary, run_dir / "metric_table.png")

    samples_dir = run_dir / "samples"
    grids: list[np.ndarray] = []
    for sample_dir in sorted(samples_dir.iterdir()):
        if not sample_dir.is_dir():
            continue
        grid = make_sample_grid(sample_dir)
        if grid is not None:
            grids.append(grid)
            out = sample_dir / "comparison_grid.png"
            Image.fromarray(grid).save(out)
            print(f"Saved {out}")

    if grids:
        combined = np.concatenate(grids, axis=0)
        combined_path = run_dir / "all_samples_comparison.png"
        Image.fromarray(combined).save(combined_path)
        print(f"Saved combined -> {combined_path}")


if __name__ == "__main__":
    main()
