# Repo State 2026-04-05

## Current Git State

- Active branch: `exp/source-prompt-static-roi`
- HEAD commit: `da6f65a` - add prompt temporal support variant
- Dirty files:
  - `log.md` (left untouched on purpose)

## Branches

- `exp/source-prompt-static-roi`
  - Main research branch for the current prompt-based DyMask line.
- `master`
  - Older general branch, not the current research line.
- `restart-6dc862e`
  - Older restart branch around the `(1-a_t)` removal experiments.

## Variant Progression

This is the actual evolution order for the current prompt-based line:

1. `6bbe831` - checkpoint before source-prompt static ROI work
2. `c49c9f0` - source-prompt stagewise static ROI
3. `25ba295` - stabilize standalone DiffEdit baseline and mask alignment logging
4. `747efa4` - source-prompt + DiffEdit ROI upperbound
5. `7808a9c` - source-prompt hard ROI locked
6. `3fcea21` - fix hard ROI locked overview generation
7. `da6f65a` - source-prompt temporal support accumulation

## Core Code Map

### Shared Core

- `DyMask/v1.py`
  - Shared dynamic mask builder and the original mask logic (`D_t`, `A_t`, `C_t`).
- `DyMask/run_v1.py`
  - Original non-source-prompt driver.
- `DyMask/run_v1_nti.py`
  - Original NTI shortcut for the non-source-prompt driver.

### Prompt-Based Main Line

- `DyMask/v1_source_prompt.py`
  - Base prompt version.
  - Uses `source_prompt` for inversion/reference branch and `target_prompt` for editing.
- `DyMask/run_v1_source_prompt.py`
  - Driver for the base prompt version.
  - Output root: `runs/dymask_v1_source_prompt`

### Prompt-Based Mechanism Variants

- `DyMask/v1_source_prompt_stagewise.py`
  - Stagewise static ROI from early source-trajectory discrepancy.
  - Early steps: static ROI
  - Late steps: static ROI times dynamic mask
- `DyMask/run_v1_source_prompt_stagewise.py`
  - Driver
  - Output root: `runs/dymask_v1_source_prompt_stagewise`

- `DyMask/v1_source_prompt_diffedit_roi.py`
  - DiffEdit ROI upperbound variant.
  - Early steps: hard DiffEdit ROI
  - Late steps: hard ROI times dynamic mask
- `DyMask/run_v1_source_prompt_diffedit_roi.py`
  - Driver
  - Output root: `runs/dymask_v1_source_prompt_diffedit_roi`

- `DyMask/v1_source_prompt_hard_roi_locked.py`
  - Hard ROI locked variant.
  - All steps: hard ROI times dynamic mask
- `DyMask/run_v1_source_prompt_hard_roi_locked.py`
  - Driver
  - Output root: `runs/dymask_v1_source_prompt_hard_roi_locked`

- `DyMask/v1_source_prompt_temporal_support.py`
  - Latest mechanism variant.
  - Evidence: `phi_t = roi_mask * dynamic_mask`
  - Support state: `S_t = rho * S_{t-1} + (1-rho) * phi_t`
  - Effective mask: `M_t = S_t`
- `DyMask/run_v1_source_prompt_temporal_support.py`
  - Driver
  - Output root: `runs/dymask_v1_source_prompt_temporal_support`

### Other Side Lines

- `DyMask/diffedit.py`
  - Standalone DiffEdit baseline support and utilities.
- `DyMask/run_diffedit.py`
  - Standalone DiffEdit experiment driver.
  - Output root: `runs/diffedit`

- `DyMask/v1_bgblend.py`
  - Background blending side experiment.
  - Not the current main research line.
- `DyMask/run_v1_bgblend.py`
- `DyMask/run_v1_bgblend_nti.py`
  - Output root: `runs/dymask_v1_bgblend`

## Run Directory Map

- `runs/dymask_v1`
  - Older non-prompt DyMask runs
- `runs/dymask_v1_source_prompt`
  - Base prompt runs
- `runs/dymask_v1_source_prompt_stagewise`
  - Stagewise static ROI runs
- `runs/dymask_v1_source_prompt_diffedit_roi`
  - DiffEdit ROI upperbound runs
- `runs/dymask_v1_source_prompt_hard_roi_locked`
  - Hard ROI locked runs
- `runs/dymask_v1_source_prompt_temporal_support`
  - Temporal support accumulation runs
- `runs/diffedit`
  - Standalone DiffEdit baseline
- `runs/dymask_v1_bgblend`
  - Background blending side experiments

## Current Reference Runs

These are the runs worth checking first.

- Base prompt:
  - `runs/dymask_v1_source_prompt/v1_source_prompt_20260404-1359`
- Prompt stagewise static ROI:
  - `runs/dymask_v1_source_prompt_stagewise/v1_source_prompt_stagewise_20260404-1415`
- Prompt + DiffEdit ROI:
  - `runs/dymask_v1_source_prompt_diffedit_roi/v1_source_prompt_diffedit_roi_20260404-1711`
- Prompt hard ROI locked:
  - `runs/dymask_v1_source_prompt_hard_roi_locked/v1_source_prompt_hard_roi_locked_20260405-1010`
- Prompt temporal support:
  - `runs/dymask_v1_source_prompt_temporal_support/v1_source_prompt_temporal_support_20260405-1801` (`rho=0.85`)
  - `runs/dymask_v1_source_prompt_temporal_support/v1_source_prompt_temporal_support_20260405-1822` (`rho=0.70`)
  - `runs/dymask_v1_source_prompt_temporal_support/v1_source_prompt_temporal_support_20260405-1840` (`rho=0.95`)
- Standalone DiffEdit:
  - `runs/diffedit/diffedit_20260404-1603`

## Recommended Reading Order

If you want to quickly recover context, read in this order:

1. `DyMask/v1.py`
   - Shared `D_t / A_t / C_t` logic
2. `DyMask/v1_source_prompt.py`
   - Base prompt version
3. `DyMask/v1_source_prompt_stagewise.py`
   - First major prompt-line mechanism change
4. `DyMask/v1_source_prompt_diffedit_roi.py`
   - External hard ROI integration
5. `DyMask/v1_source_prompt_hard_roi_locked.py`
   - Full-time hard ROI locking
6. `DyMask/v1_source_prompt_temporal_support.py`
   - Current latest mechanism

## Current Practical Status

- Current paper-oriented main line:
  - Prompt-based variants only
- Side lines to mostly ignore for now:
  - Non-prompt `runs/dymask_v1`
  - Background blending `runs/dymask_v1_bgblend`

- Current strict background-protection reference:
  - Hard ROI locked
- Current latest mechanism:
  - Temporal support accumulation
- Current best temporal-support setting tested so far:
  - `rho = 0.70`
  - Better balance than `0.85` and `0.95`

## Notes

- `log.md` is intentionally not part of the commit history here.
- The temporal-support line is conceptually:
  - hard support from ROI
  - dynamic evidence from DyMask
  - temporal accumulation for edit eligibility
