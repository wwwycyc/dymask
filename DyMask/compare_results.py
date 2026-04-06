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
    ("target_only", "target-only"),
    ("global_blend", "global blend"),
    ("discrepancy_only", "D_t"),
    ("discrepancy_attention", "D_t + A_t"),
    ("discrepancy_latent", "D_t - C_t"),
    ("full_dynamic_mask", "Full"),
]

SUMMARY_CANDIDATES = (
    "metrics_overview_methods_summary.json",
    "metrics_five_methods_summary.json",
    "metrics_summary.json",
)


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


def build_metric_specs(summary: list[dict]) -> list[tuple[str, str, bool]]:
    specs: list[tuple[str, str, bool]] = []
    if any(row.get("clip_similarity_mean") is not None for row in summary):
        specs.append(("clip_similarity_mean", "CLIP Similarity", True))
    specs.append(("clip_score_mean", "CLIPScore", True))
    if any(row.get("clip_score_edit_part_mean") is not None for row in summary):
        specs.append(("clip_score_edit_part_mean", "Edit-part CLIPScore", True))
    specs.extend(
        [
            ("source_psnr_mean", "Source PSNR", True),
            ("source_lpips_mean", "Source LPIPS", False),
        ]
    )
    if any(row.get("outside_lpips_mean") is not None for row in summary):
        specs.extend(
            [
                ("outside_psnr_mean", "Outside PSNR", True),
                ("outside_mse_mean", "Outside MSE", False),
                ("outside_ssim_mean", "Outside SSIM", True),
                ("outside_lpips_mean", "Outside LPIPS", False),
                ("locality_ratio_mean", "Locality Ratio", True),
            ]
        )
    return [spec for spec in specs if any(row.get(spec[0]) is not None for row in summary)]


def make_metric_bar_chart(summary: list[dict], out_path: Path) -> None:
    methods = [row["method_name"] for row in summary]
    chart_specs = [
        ([row.get(key) or 0.0 for row in summary], title, higher_better)
        for key, title, higher_better in build_metric_specs(summary)
    ]
    if not chart_specs:
        return

    x = np.arange(len(methods))
    fig, axes = plt.subplots(1, len(chart_specs), figsize=(len(chart_specs) * 3, 5))
    if len(chart_specs) == 1:
        axes = [axes]
    fig.suptitle("Method Comparison", fontsize=13, y=1.01)

    colors = plt.cm.tab10(np.linspace(0, 0.6, len(methods)))

    for ax, (values, title, higher_better) in zip(axes, chart_specs):
        bars = ax.bar(x, values, color=colors, edgecolor="white", linewidth=0.5)
        ax.set_xticks(x)
        ax.set_xticklabels(methods, rotation=25, ha="right", fontsize=9)
        ax.set_title(f"{title} ({'up' if higher_better else 'down'})", fontsize=11)
        ax.set_ylabel(title)
        value_offset = (max(values) if values else 0.0) * 0.01
        for bar, val in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + value_offset,
                f"{val:.4f}",
                ha="center",
                va="bottom",
                fontsize=7,
            )
        best_idx = int(np.argmax(values) if higher_better else np.argmin(values))
        bars[best_idx].set_edgecolor("red")
        bars[best_idx].set_linewidth(2.5)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved metric chart -> {out_path}")


def _metric_sort_value(value: float | None, higher_better: bool) -> float:
    if value is None:
        return float("inf")
    return -float(value) if higher_better else float(value)


def make_metric_tree_image(summary: list[dict], out_path: Path) -> None:
    specs = build_metric_specs(summary)
    if not specs or not summary:
        return

    fig_height = max(6.0, len(specs) * 2.1)
    fig, ax = plt.subplots(figsize=(16, fig_height))
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.axis("off")

    root_x = 0.06
    metric_x = 0.30
    leaf_x = 0.63
    root_y = 0.5
    metric_positions = np.linspace(0.88, 0.12, len(specs))

    ax.text(
        root_x,
        root_y,
        "Metrics",
        ha="center",
        va="center",
        fontsize=14,
        bbox={"boxstyle": "round,pad=0.45", "fc": "#e8eef8", "ec": "#4c72b0", "lw": 1.5},
    )

    for metric_index, (key, title, higher_better) in enumerate(specs):
        metric_y = float(metric_positions[metric_index])
        ax.plot([root_x + 0.05, metric_x - 0.04], [root_y, metric_y], color="#8c8c8c", linewidth=1.2)
        ax.text(
            metric_x,
            metric_y,
            title,
            ha="center",
            va="center",
            fontsize=11,
            bbox={"boxstyle": "round,pad=0.35", "fc": "#f6f6f6", "ec": "#555555", "lw": 1.0},
        )

        ordered_rows = sorted(summary, key=lambda row: _metric_sort_value(row.get(key), higher_better))
        spread = min(0.11, 0.42 / max(len(specs), 1))
        leaf_positions = np.linspace(metric_y - spread, metric_y + spread, len(ordered_rows))
        for rank, (leaf_y, row) in enumerate(zip(leaf_positions, ordered_rows), start=1):
            value = row.get(key)
            value_text = "NA" if value is None else f"{float(value):.4f}"
            leaf_text = f"{rank}. {row['method_name']}  {value_text}"
            edge_color = "#2ca02c" if rank == 1 else "#b0b0b0"
            face_color = "#eef8ee" if rank == 1 else "#fbfbfb"
            ax.plot([metric_x + 0.06, leaf_x - 0.04], [metric_y, float(leaf_y)], color=edge_color, linewidth=1.0)
            ax.text(
                leaf_x,
                float(leaf_y),
                leaf_text,
                ha="left",
                va="center",
                fontsize=9,
                bbox={"boxstyle": "round,pad=0.22", "fc": face_color, "ec": edge_color, "lw": 1.0},
            )

    fig.suptitle("Metric Tree", fontsize=14, y=0.995)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved metric tree -> {out_path}")


def make_metric_table_image(summary: list[dict], out_path: Path) -> None:
    methods = [row["method_name"] for row in summary]
    specs = build_metric_specs(summary)
    if not specs:
        return

    cols = [title for _, title, _ in specs]
    keys = [key for key, _, _ in specs]
    higher = [higher_better for _, _, higher_better in specs]

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
    summary_path = None
    for candidate_name in SUMMARY_CANDIDATES:
        candidate = run_dir / candidate_name
        if candidate.exists():
            summary_path = candidate
            break
    if summary_path is None:
        raise FileNotFoundError(f"No summary JSON found in {run_dir}")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))["summary"]
    summary = [row for row in summary if row["method_name"] != "phase0_reconstruction"]

    make_metric_tree_image(summary, run_dir / "metric_tree.png")
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
