# Server Experiment Plan (2026-04-07)

## Goal
Current research direction is no longer "dynamic mask decides support".

Current mainline is:
- hard ROI decides where editing is allowed
- source anchoring keeps non-ROI regions on the source trajectory
- any future modules should improve editing **inside** the ROI

## Current best local result
Main comparison set: standard 8 PIE-Bench samples, `20/20`, `full_dynamic_mask`.

### DiffEdit baseline
Run:
- `D:\Program\dymask\scratch_diffedit_runs\diffedit_base\diffedit_20260407-1521`

Summary:
- `clip_score_mean = 25.2701`
- `clip_score_edit_part_mean = 18.1022`
- `edit_source_psnr_mean = 22.0151`
- `outside_psnr_mean = 25.7668`
- `outside_lpips_mean = 0.0484`
- `locality_ratio_mean = 0.3177`

### Source-anchor + hard ROI
Run:
- `D:\Program\dymask\scratch_source_anchor_hard_roi_runs\sp_anchor_hard_roi\sp_anchor_hard_roi_20260407-1916`

Summary:
- `clip_score_mean = 24.9073`
- `clip_score_edit_part_mean = 18.1350`
- `edit_source_psnr_mean = 21.8845`
- `outside_psnr_mean = 26.0370`
- `outside_lpips_mean = 0.0455`
- `locality_ratio_mean = 0.3193`

Interpretation:
- already beats DiffEdit on `edit_clip`, `outside_psnr`, `outside_lpips`, `locality`
- still slightly behind on overall `clip` and `source_psnr`

### Source-anchor + soft ROI
Run:
- `D:\Program\dymask\scratch_source_anchor_soft_roi_runs\sp_anchor_soft_roi\sp_anchor_soft_roi_20260407-2226`

Summary:
- `clip_score_mean = 24.8836`
- `clip_score_edit_part_mean = 17.7530`
- `edit_source_psnr_mean = 21.7537`
- `outside_psnr_mean = 26.1995`
- `outside_lpips_mean = 0.0455`
- `locality_ratio_mean = 0.3303`

Interpretation:
- soft ROI improves `outside_psnr` and `locality`
- but it loses `edit_clip` relative to hard ROI
- treat it as a valid ablation, not the new mainline

### Random-8 generalization
Same-tier behavior already verified on random 8 samples.

Source-anchor + hard ROI:
- `D:\Program\dymask\scratch_source_anchor_hard_roi_runs\sp_anchor_hard_roi_random\sp_anchor_hard_roi_20260407-2132`

DiffEdit:
- `D:\Program\dymask\scratch_diffedit_runs\diffedit_base_random\diffedit_20260407-2204`

Result:
- hard ROI + source anchor remains competitive beyond deletion-heavy samples

## Available code variants
### Stable baselines
- `DyMask/run_diffedit.py`
- `DyMask/run_v1_source_prompt_source_anchored_hard_roi.py`

### New variants ready to run
- `DyMask/run_v1_source_prompt_source_anchored_hard_roi_feature_injection.py`
  - idea: PnP-style decoder feature injection on top of hard ROI + source anchor
  - status: code ready, not benchmarked yet

### New variants already benchmarked locally
- `DyMask/run_v1_source_prompt_source_anchored_soft_roi.py`
  - idea: use raw DiffEdit soft mask for updates, but keep hard outside-ROI anchoring
  - status: benchmarked once locally; see soft-ROI run above

### Existing but low-priority / known-bad
- `DyMask/run_v1_source_prompt_source_anchored_hard_roi_self_attention_injection.py`
  - local smoke tests were visually bad
  - do not prioritize unless reworked

## Recommended experiment order on server
### Priority 1: decoder feature injection smoke
Hypothesis:
- the main bottleneck is now ROI-internal editing quality
- decoder feature injection is a cleaner PnP-style attempt than the failed self-attention injection
- likely risk: under-editing

Start with small smoke tests, not full 8:
```powershell
E:\Anaconda_envs\envs\imgedit\python.exe D:\Program\dymask\DyMask\run_v1_source_prompt_source_anchored_hard_roi_feature_injection.py `
  --piebench-path D:\Program\dymask\assets\PIE-Bench `
  --row-indices 300 310 370 `
  --sample-count 3 `
  --run-limit 3 `
  --phase custom `
  --methods full_dynamic_mask `
  --num-inversion-steps 20 `
  --num-edit-steps 20 `
  --inversion-backend ddim `
  --inject-start-ratio 0.25 `
  --inject-end-ratio 0.75 `
  --inject-strength 0.25 `
  --inject-up-blocks 2 3 `
  --inject-resnets 0 1 2
```

Then sweep strength only:
- `0.15`
- `0.25`
- `0.40`

Only if visual quality is acceptable, promote to full 8.

### Priority 2: soft ROI random-8 generalization
Only run this if you want to verify the locality gain on a broader sample mix.

```powershell
E:\Anaconda_envs\envs\imgedit\python.exe D:\Program\dymask\DyMask\run_v1_source_prompt_source_anchored_soft_roi.py `
  --piebench-path D:\Program\dymask\assets\PIE-Bench `
  --row-indices 6 26 28 35 57 62 70 139 `
  --sample-count 8 `
  --run-limit 8 `
  --phase custom `
  --methods full_dynamic_mask `
  --num-inversion-steps 20 `
  --num-edit-steps 20 `
  --inversion-backend ddim `
  --output-root scratch_source_anchor_soft_roi_runs\sp_anchor_soft_roi_random
```

### Priority 3: compare against fixed references
Always compare new runs against:
- `scratch_diffedit_runs\diffedit_base\diffedit_20260407-1521`
- `scratch_source_anchor_hard_roi_runs\sp_anchor_hard_roi\sp_anchor_hard_roi_20260407-1916`

## How to judge success
For a new mainline candidate, the minimum target is:
- keep `outside_psnr` and `outside_lpips` at least on par with current hard ROI
- improve either `clip_score_mean` or `clip_score_edit_part_mean`
- avoid obvious under-editing on visual inspection

Priority metrics:
1. `clip_score_edit_part_mean`
2. `locality_ratio_mean`
3. `outside_lpips_mean`
4. `outside_psnr_mean`

## Visual checks
Do not trust metrics alone.

For each run, inspect:
- `overview_all_samples.png`
- at least these cases when present:
  - bird/flowers-type delete case
  - balloons delete case
  - one non-delete or complex structural case

Low-quality signs:
- edited object remains clearly present
- object interior becomes muddy or duplicated
- hard ROI boundary creates visible halos
- source feature injection freezes edited regions too aggressively

## Git checkpoints
Important recent commits:
- `680346a` source-anchor + hard ROI
- `6a9c11e` source-anchor + soft ROI
- `503a4b3` source-anchor + decoder feature injection

## 2026-04-08 mechanistic update
Current mechanistic branch:
- `exp/proedit-mechanistic-rewrite`

New files:
- `DyMask/conflict_gated_feature_mix.py`
- `DyMask/v1_source_prompt_source_anchored_hard_roi_conflict_gated_mix.py`
- `DyMask/run_v1_source_prompt_source_anchored_hard_roi_conflict_gated_mix.py`

Mechanism:
- keep `DiffEdit hard ROI` as support
- keep `outside source anchoring`
- replace constant inside target-relax with `inside rewrite gain` gated by source-target feature conflict
- keep `outside source pull`

Important correction:
- the aborted local run `scratch_conflict_gated_mix_runs\sp_anchor_conflict_gated\sp_anchor_conflict_gated_20260408-2220` is invalid
- it accidentally ran on the parquet dataset and defaulted to all methods
- do not use that run for any comparison

The runner has been fixed so that its defaults are now:
- `--piebench-path assets\PIE-Bench`
- `--methods full_dynamic_mask`

Recommended server command:
```powershell
E:\Anaconda_envs\envs\imgedit\python.exe D:\Program\dymask\DyMask\run_v1_source_prompt_source_anchored_hard_roi_conflict_gated_mix.py `
  --piebench-path D:\Program\dymask\assets\PIE-Bench `
  --row-indices 165 162 273 275 346 360 411 409 440 423 468 490 510 521 `
  --sample-count 8 `
  --run-limit 14 `
  --phase custom `
  --methods full_dynamic_mask `
  --num-inversion-steps 10 `
  --num-edit-steps 10 `
  --inversion-backend ddim `
  --disable-batch-warmup-probe `
  --mix-inside-rewrite-gain-strength 0.05 `
  --mix-outside-source-strength 0.15
```

Comparison targets:
- `scratch_source_anchor_hard_roi_runs\sp_anchor_hard_roi\sp_anchor_hard_roi_20260408-2055`
- `scratch_proedit_like_runs\sp_anchor_proedit_like\sp_anchor_proedit_like_20260408-2147`

Recommended checkout anchors:
- `680346a`
  - strongest current hard-ROI baseline
- `6a9c11e`
  - soft-ROI ablation on top of hard anchoring
- `503a4b3`
  - decoder feature-injection branch ready for smoke tests

## What not to spend time on next
- new support-state variants
- more `D_t/A_t/C_t`-based support generation
- the current self-attention injection path without redesign

## Offline / server reminder
This repo assumes local model caches are already available.
If the server has no usable network, copy:
- Hugging Face SD1.5 cache
- Hugging Face CLIP cache
- torch hub squeezenet checkpoint
- LPIPS squeeze weights

Then set:
```powershell
$env:HF_HOME="YOUR_HF_CACHE_ROOT"
$env:HF_HUB_OFFLINE="1"
$env:TRANSFORMERS_OFFLINE="1"
$env:TORCH_HOME="YOUR_TORCH_CACHE_ROOT"
```
