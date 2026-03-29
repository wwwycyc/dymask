#!/usr/bin/env python
"""Aggregate PIE-Bench by-type run results into a single summary table."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

TYPE_NAMES = {
    "0": "random",
    "1": "add object",
    "2": "texture",
    "3": "replace object",
    "4": "global color",
    "5": "style",
    "6": "weather",
    "7": "action",
    "8": "background",
    "9": "facial",
}

METHOD_ORDER = ["target_only", "global_blend", "discrepancy_only", "discrepancy_attention", "discrepancy_latent", "full_dynamic_mask"]
METHOD_LABELS = {
    "target_only": "target-only",
    "global_blend": "global blend",
    "discrepancy_only": "D_t",
    "discrepancy_attention": "D_t + A_t",
    "discrepancy_latent": "D_t + C_t",
    "full_dynamic_mask": "Full",
}


def infer_type_id(run_dir: Path) -> str:
    """Infer editing_type_id from first sample key (PIE-Bench key starts with type_id)."""
    samples_dir = run_dir / "samples"
    if not samples_dir.exists():
        return "?"
    first = sorted(samples_dir.iterdir())[0].name
    # sample_000_pie_XXXXXXXXXXX -> key = XXXXXXXXXXX -> first char is type_id
    key = first.split("_pie_")[-1] if "_pie_" in first else "?"
    return key[0] if key != "?" else "?"


def load_run_summary(run_dir: Path) -> list[dict]:
    p = run_dir / "metrics_summary.json"
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))["summary"]
    return [r for r in data if r["method_name"] != "phase0_reconstruction"]


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: aggregate_piebench_types.py <runs_dir>")
        sys.exit(1)

    runs_dir = Path(sys.argv[1])
    run_dirs = sorted(d for d in runs_dir.iterdir() if d.is_dir())

    # build rows: type_id, method_name, metrics...
    all_rows: list[dict] = []
    for run_dir in run_dirs:
        type_id = infer_type_id(run_dir)
        summary = load_run_summary(run_dir)
        for row in summary:
            all_rows.append({"type_id": type_id, "type_name": TYPE_NAMES.get(type_id, type_id), **row})

    if not all_rows:
        print("No data found.")
        return

    df = pd.DataFrame(all_rows)
    out_dir = runs_dir

    # Save full per-type per-method CSV
    csv_path = out_dir / "aggregate_by_type.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"Saved {csv_path}")

    # Per-method summary across all types
    metric_cols = [c for c in df.columns if c.endswith("_mean")]
    method_summary = df.groupby("method_name")[metric_cols].mean().reset_index()
    method_summary_path = out_dir / "aggregate_method_summary.csv"
    method_summary.to_csv(method_summary_path, index=False, encoding="utf-8-sig")
    print(f"Saved {method_summary_path}")

    # Key metrics to plot
    key_metrics = [
        ("clip_score_mean", "CLIP Score (↑)", True),
        ("edit_source_lpips_mean", "Src LPIPS (↓)", False),
        ("edit_source_psnr_mean", "Src PSNR (↑)", True),
        ("outside_lpips_mean", "Outside LPIPS (↓)", False),
        ("outside_psnr_mean", "Outside PSNR (↑)", True),
        ("locality_ratio_mean", "Locality Ratio (↑)", True),
    ]

    type_ids = sorted(df["type_id"].unique())
    type_labels = [f"{t}:{TYPE_NAMES.get(t,t)}" for t in type_ids]
    methods = [m for m in METHOD_ORDER if m in df["method_name"].values]
    colors = plt.cm.tab10(np.linspace(0, 0.9, len(methods)))

    # Plot 1: per-metric, x=type, lines=methods
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    axes = axes.flatten()
    for ax, (col, title, higher) in zip(axes, key_metrics):
        for method, color in zip(methods, colors):
            mdf = df[df["method_name"] == method]
            vals = [mdf[mdf["type_id"] == t][col].mean() if t in mdf["type_id"].values else None for t in type_ids]
            vals_plot = [v if v is not None else float("nan") for v in vals]
            ax.plot(range(len(type_ids)), vals_plot, marker="o", label=method, color=color, linewidth=1.5)
        ax.set_xticks(range(len(type_ids)))
        ax.set_xticklabels(type_labels, rotation=30, ha="right", fontsize=7)
        ax.set_title(title, fontsize=10)
        ax.legend(fontsize=6)
        ax.grid(axis="y", alpha=0.3)
    fig.suptitle("PIE-Bench: Metrics by Editing Type", fontsize=13)
    fig.tight_layout()
    chart_path = out_dir / "metrics_by_type.png"
    fig.savefig(chart_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {chart_path}")

    # Plot 2: per-method bar chart (mean across all types)
    fig2, axes2 = plt.subplots(2, 3, figsize=(18, 10))
    axes2 = axes2.flatten()
    x = np.arange(len(methods))
    for ax, (col, title, higher) in zip(axes2, key_metrics):
        vals = [method_summary[method_summary["method_name"] == m][col].values[0]
                if m in method_summary["method_name"].values else float("nan")
                for m in methods]
        bars = ax.bar(x, vals, color=colors, edgecolor="white")
        ax.set_xticks(x)
        ax.set_xticklabels(methods, rotation=25, ha="right", fontsize=8)
        ax.set_title(title, fontsize=10)
        for bar, val in zip(bars, vals):
            if not np.isnan(val):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(v for v in vals if not np.isnan(v))*0.01,
                        f"{val:.3f}", ha="center", va="bottom", fontsize=7)
        non_nan = [v for v in vals if not np.isnan(v)]
        if non_nan:
            best = int(np.nanargmax(vals) if higher else np.nanargmin(vals))
            bars[best].set_edgecolor("red")
            bars[best].set_linewidth(2.5)
        ax.grid(axis="y", alpha=0.3)
    fig2.suptitle("PIE-Bench: Overall Method Comparison (mean across 10 types × 8 samples)", fontsize=12)
    fig2.tight_layout()
    overall_path = out_dir / "metrics_overall.png"
    fig2.savefig(overall_path, dpi=150, bbox_inches="tight")
    plt.close(fig2)
    print(f"Saved {overall_path}")

    # Print summary table
    print("\n=== Overall Method Summary ===")
    cols_print = ["method_name", "clip_score_mean", "edit_source_lpips_mean", "edit_source_psnr_mean",
                  "outside_lpips_mean", "outside_psnr_mean", "locality_ratio_mean"]
    cols_print = [c for c in cols_print if c in method_summary.columns]
    print(method_summary[cols_print].to_string(index=False, float_format="{:.4f}".format))


if __name__ == "__main__":
    main()
