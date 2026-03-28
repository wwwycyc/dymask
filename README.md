# DyMask

[English](D:/Program/dymask/README.md) | [中文](D:/Program/dymask/README_zh.md)

## Overview
DyMask is an image editing experiment system built around:

- Stable Diffusion 1.5
- Null-Text Inversion
- Dynamic mask based blending
- Prompt-conditioned attention analysis

The main entry points are under [DyMask](D:/Program/dymask/DyMask).

## Main Scripts
- [DyMask/run_v1.py](D:/Program/dymask/DyMask/run_v1.py)
  Main experiment runner. Handles sampling, inversion, editing, visualization, and metrics.
- [DyMask/visualize_attention.py](D:/Program/dymask/DyMask/visualize_attention.py)
  Single-sample attention probe for target prompt attention maps.
- [DyMask/backfill_run_metrics.py](D:/Program/dymask/DyMask/backfill_run_metrics.py)
  Recompute metrics for an existing run directory.
- [DyMask/inspect_pt.py](D:/Program/dymask/DyMask/inspect_pt.py)
  Inspect saved `.pt` tensors.

## Supported Parquet Formats
The loader in [DyMask/data.py](D:/Program/dymask/DyMask/data.py) supports two dataset formats.

Legacy paired-edit format:
- `original_prompt`
- `original_image`
- `edit_prompt`
- `edited_prompt`
- `edited_image`

V1 single-image edit format:
- `image`
- `id`
- `source_prompt`
- `target_prompt`
- `edit_action`
- `aspect_mapping`
- `blended_words`
- `mask`

## Environment
All commands below assume:

- current working directory is `D:\Program\dymask`
- `python` points to the correct environment

If you want to use the local existing environment explicitly:

```powershell
& 'E:\Anaconda_envs\envs\imgedit\python.exe' ...
```

## Help
```powershell
python DyMask/run_v1.py --help
python DyMask/visualize_attention.py --help
python DyMask/backfill_run_metrics.py --help
python DyMask/inspect_pt.py --help
```

## run_v1.py
Basic invocation:

```powershell
python DyMask/run_v1.py
```

Common arguments:
- `--parquet-path`
- `--sample-json`
- `--sample-count`
- `--run-limit`
- `--row-indices`
- `--phase`
- `--methods`
- `--mask-mode dynamic|static`
- `--skip-metrics`
- `--dry-run`
- `--save-inversion-tensors`

### Inversion Steps vs Edit Steps
These are now decoupled.

Use:
- `--num-inversion-steps`
- `--num-edit-steps`

Legacy compatibility:
- `--num-ddim-steps N` still works
- it sets both inversion and edit steps to `N` unless the new arguments override it

Example:

```powershell
python DyMask/run_v1.py --num-inversion-steps 10 --num-edit-steps 20
```

### Phase Mapping
- `phase0`
  inversion / reconstruction only
- `phase1`
  `target_only`
- `phase2`
  `target_only + global_blend_0.3/0.5/0.7`
- `phase3`
  `discrepancy_only`
- `phase4`
  `discrepancy_attention`
- `phase5`
  `full_dynamic_mask`
- `custom`
  explicit `--methods`

### Common Five-Method Setup
If you want the common five-method comparison, use:

```powershell
python DyMask/run_v1.py --phase custom --methods target_only global_blend discrepancy_only discrepancy_attention full_dynamic_mask
```

Method display names:
- `target_only` -> `target-only`
- `global_blend` -> `global blend`
- `discrepancy_only` -> `D_t`
- `discrepancy_attention` -> `D_t + A_t`
- `full_dynamic_mask` -> `Full`

## Common Commands
### Run 8 samples on the default parquet
```powershell
python DyMask/run_v1.py --phase custom --methods target_only global_blend discrepancy_only discrepancy_attention full_dynamic_mask --sample-count 8 --run-limit 8
```

### Run 8 samples on `V1-00000-of-00001.parquet`
```powershell
python DyMask/run_v1.py --phase custom --methods target_only global_blend discrepancy_only discrepancy_attention full_dynamic_mask --parquet-path assets/data/V1-00000-of-00001.parquet --sample-count 8 --run-limit 8
```

### Run selected rows only
```powershell
python DyMask/run_v1.py --parquet-path assets/data/V1-00000-of-00001.parquet --row-indices 6 26 28 --run-limit 3 --phase custom --methods target_only global_blend discrepancy_only discrepancy_attention full_dynamic_mask
```

### Minimal single-sample validation
```powershell
python DyMask/run_v1.py --parquet-path assets/data/V1-00000-of-00001.parquet --row-indices 6 --sample-count 1 --run-limit 1 --phase custom --methods target_only --skip-metrics
```

### Inversion 5 steps, edit 8 steps
```powershell
python DyMask/run_v1.py --parquet-path assets/data/V1-00000-of-00001.parquet --row-indices 6 --sample-count 1 --run-limit 1 --phase custom --methods target_only --skip-metrics --num-inversion-steps 5 --num-edit-steps 8
```

### Dry run only
```powershell
python DyMask/run_v1.py --parquet-path assets/data/V1-00000-of-00001.parquet --sample-count 8 --run-limit 8 --dry-run
```

### Skip metrics
```powershell
python DyMask/run_v1.py --phase custom --methods target_only global_blend discrepancy_only discrepancy_attention full_dynamic_mask --skip-metrics
```

### Static mask
```powershell
python DyMask/run_v1.py --phase phase4 --mask-mode static
```

### Re-run from an existing `sample.json`
```powershell
python DyMask/run_v1.py --sample-json runs/dymask_v1/<run_dir>/samples/<sample_id>/sample.json --phase custom --methods target_only global_blend discrepancy_only discrepancy_attention full_dynamic_mask
```

## visualize_attention.py
Basic invocation:

```powershell
python DyMask/visualize_attention.py
```

### Probe one row from parquet
```powershell
python DyMask/visualize_attention.py --parquet-path assets/data/V1-00000-of-00001.parquet --row-index 6
```

### Probe from an existing `sample.json`
```powershell
python DyMask/visualize_attention.py --sample-json runs/dymask_v1/<run_dir>/samples/<sample_id>/sample.json
```

### Use different inversion and edit steps
```powershell
python DyMask/visualize_attention.py --parquet-path assets/data/V1-00000-of-00001.parquet --row-index 6 --num-inversion-steps 10 --num-edit-steps 20
```

Output goes to:
- `runs/attention_probe/<timestamp>/samples/<sample_id>/attention_only`

Common outputs:
- `attention_overview.png`
- `selected_steps/*.png`
- `delta_trace.csv`
- `attention_debug.json`

## backfill_run_metrics.py
Recompute metrics for an existing run:

```powershell
python DyMask/backfill_run_metrics.py runs/dymask_v1/<run_dir>
```

It refreshes:
- `metrics_case_level.csv`
- `metrics_summary.csv`
- `metrics_summary.json`

Note:
- this script backfills the generic metrics tables
- it does not rebuild sample overviews
- it does not rebuild the five-method-only summary tables

## inspect_pt.py
Inspect saved tensors:

```powershell
python DyMask/inspect_pt.py runs/dymask_v1/<run_dir>/samples/<sample_id>/zt_src.pt
python DyMask/inspect_pt.py runs/dymask_v1/<run_dir>/samples/<sample_id>/src_latents.pt --max-items 10
```

## Output Layout
Typical run directory:

```text
runs/dymask_v1/<run_dir>/
  config.json
  sample_manifest.json
  sample_manifest.csv
  metrics_case_level.csv
  metrics_summary.csv
  metrics_summary.json
  metrics_five_methods_case_level.csv
  metrics_five_methods_summary.csv
  metrics_five_methods_summary.json
  samples/
    <sample_id>/
      sample.json
      source.png
      target_reference.png
      source_reconstruction.png
      overview.png
      <method_name>/
        edited.png
        mask_summary.png
        aux_summary.png
        selected_steps/
        delta_trace.csv
        delta_trace.json
        step_diagnostics.csv
        step_diagnostics.json
        debug.json
```

`target_reference.png` exists only when the dataset actually provides a target edited image.

## overview.png
Each sample `overview.png` currently contains 7 tiles:

1. source
2. target-only
3. global blend
4. D_t
5. D_t + A_t
6. Full
7. D/A/C/mask maps

## Metrics Notes
Common fields:
- `clip_score`
- `source_recon_psnr`
- `source_recon_lpips`
- `edit_ref_psnr`
- `edit_ref_lpips`
- `edit_source_psnr`
- `edit_source_lpips`
- `edit_reference_mode`

Interpretation:
- `clip_score`
  image-text alignment to `target_prompt`
- `source_recon_*`
  reconstruction quality of inversion
- `edit_ref_*`
  edited image vs target reference image
- `edit_source_*`
  edited image vs source image

Important:
- for datasets without target edited images, `edit_ref_*` is empty
- in that case, use `clip_score` plus `edit_source_*`
- `edit_source_*` measures edit magnitude, not edit correctness

## Diagnostics
Each method directory now stores:
- `step_diagnostics.csv`
- `step_diagnostics.json`

These include per-step statistics for:
- `discrepancy`
- `attention`
- `latent_drift`
- `mask`
- `blend_strength`

Useful fields:
- `mean`
- `std`
- `p10`
- `p90`
- `top_bottom_gap`
- `gt_0_5_ratio`
- `entropy`

Heuristic:
- `global_blend` should have mask variance near zero
- if dynamic variants show non-trivial mask statistics but still look visually similar, the issue is likely not "mask collapsed to a constant", but "mask structure is still too weak to create a clear visual advantage"

## Suggested Workflow
### 1. Quick sanity check
```powershell
python DyMask/run_v1.py --parquet-path assets/data/V1-00000-of-00001.parquet --row-indices 6 --sample-count 1 --run-limit 1 --phase custom --methods target_only global_blend discrepancy_only discrepancy_attention full_dynamic_mask --skip-metrics
```

### 2. Run 8 samples
```powershell
python DyMask/run_v1.py --parquet-path assets/data/V1-00000-of-00001.parquet --sample-count 8 --run-limit 8 --phase custom --methods target_only global_blend discrepancy_only discrepancy_attention full_dynamic_mask
```

### 3. Inspect outputs
- first check `samples/<sample_id>/overview.png`
- then read `metrics_five_methods_summary.csv`
- then inspect `step_diagnostics.json` if the visual gap is small

### 4. Probe attention if needed
```powershell
python DyMask/visualize_attention.py --parquet-path assets/data/V1-00000-of-00001.parquet --row-index 6
```

## Practical Notes
- default behavior is local model loading only
- add `--allow-download` only if downloading is intended
- if VRAM is tight, do not launch multiple runs at the same time
- `phase2` expands to `global_blend_0.3/0.5/0.7`, not a single `global_blend`
- for the fixed five-method comparison, use:

```powershell
--phase custom --methods target_only global_blend discrepancy_only discrepancy_attention full_dynamic_mask
```

## Default Template
```powershell
python DyMask/run_v1.py --phase custom --methods target_only global_blend discrepancy_only discrepancy_attention full_dynamic_mask --parquet-path <your.parquet> --sample-count 8 --run-limit 8 --num-inversion-steps 10 --num-edit-steps 10
```
