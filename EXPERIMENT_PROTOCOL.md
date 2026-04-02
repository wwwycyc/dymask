# Experiment Protocol

## 1. Purpose

This document fixes the comparison protocol for the current project so later runs are reproducible and fair.

The main comparison tracks are:

- `Ours`: source-prompt version of DyMask
- `DiffEdit + shared inversion`
- `P2P + shared inversion`

The goal of the main table is to compare **editing mechanisms**, not different inversion systems.


## 2. Main Table Methods

### 2.1 Ours

- Entry: `DyMask/run_v1_source_prompt.py`
- Main method to report: `full_dynamic_mask`

Optional ablations can be reported separately:

- `target_only`
- `global_blend_*`
- `discrepancy_only`
- `discrepancy_attention`
- `discrepancy_latent`

### 2.2 DiffEdit Baseline

- Entry: `DyMask/run_diffedit.py`
- Main-table setting: **shared inversion only**
- Do **not** use `DiffEditPipeline.invert()` in the main table

### 2.3 Prompt-to-Prompt Baseline

- Entry: `DyMask/run_p2p.py`
- Main-table setting: **shared inversion only**
- Use a fixed method-specific protocol


## 3. Shared Protocol

These settings must be identical across all three main-table methods.

### 3.1 Dataset / Samples

- Use the same dataset split
- Use the same image size
- Use the same frozen sample set

Recommended workflow:

1. First freeze the sample set once using fixed `--row-indices` or a single reference run.
2. Reuse the same `row_indices` for all methods.
3. For single-sample reruns, reuse the same `sample.json`.

Do not independently random-sample each method run.

### 3.2 Model / Runtime

- Same base model checkpoint
- Same `guidance_scale`
- Same `num_inversion_steps`
- Same `num_edit_steps`
- Same image resolution

### 3.3 Inversion

Main-table inversion policy:

- Use the same shared inversion for all methods
- Default shared inversion: `source-prompt DDIM inversion`

That means:

- `Ours` uses the source-prompt inversion path
- `DiffEdit` reuses the same inversion outputs
- `P2P` reuses the same inversion outputs

Do not mix:

- empty-prompt DDIM
- source-prompt DDIM
- NTI
- native DiffEdit inversion

inside the same main comparison table.

Those belong to ablations / appendix only.

### 3.4 Metrics

Primary reported metrics:

- `clip_score`
- `edit_ref_psnr`
- `edit_ref_lpips`
- `edit_source_psnr`
- `edit_source_lpips`

If GT mask is available, also report:

- `outside_psnr`
- `outside_lpips`
- `locality_ratio`

For reconstruction sanity check, also save:

- `source_recon_psnr`
- `source_recon_lpips`

### 3.5 Tuning Policy

- No per-image method switching
- No per-image manual hyperparameter tuning
- No hidden fallback logic in the main protocol


## 4. Method-Specific Protocol

### 4.1 Ours

Main-table method:

- `full_dynamic_mask`

Do not change mask logic per image.

### 4.2 DiffEdit

Main-table policy:

- shared inversion
- standard DiffEdit mask generation
- standard DiffEdit masked denoising

Do not use native DiffEdit inversion in the main table.

Appendix-only option:

- `DiffEdit + native invert`

### 4.3 Prompt-to-Prompt

Prompt-to-Prompt is not a single black-box method. It requires explicit method-specific choices.

For the **main table**, fix it to:

- controller mode: `refine`
- `cross_replace_steps = 0.8`
- `self_replace_steps = 0.5`
- `local_blend = off`
- `equalizer = off`

This is intentionally conservative and avoids image-by-image manual tuning.

Main-table command rules:

- Always pass `--controller-mode refine`
- Do not pass `--blend-words-source`
- Do not pass `--blend-words-target`
- Do not pass `--equalizer-words`
- Do not pass `--equalizer-values`

These options are allowed by the code, but they are **not** part of the main-table protocol.

Appendix-only options:

- `replace` controller
- local blend with manually provided words
- equalizer with manually provided weights


## 5. What Counts as Appendix / Ablation

The following should be reported separately from the main table:

- `DiffEdit + native invert`
- `P2P` with `replace`
- `P2P` with local blend
- `P2P` with equalizer
- `NTI + P2P`
- `NTI + DiffEdit`
- empty-prompt DDIM instead of source-prompt DDIM
- DyMask internal ablations (`target_only`, `global_blend`, `D_t`, `D_t + A_t`, `D_t - C_t`)


## 6. Recommended Commands

### 6.1 Ours

```powershell
& 'E:\Anaconda_envs\envs\imgedit\python.exe' DyMask/run_v1_source_prompt.py `
  --phase custom `
  --methods full_dynamic_mask `
  --parquet-path assets/data/V1-00000-of-00001.parquet `
  --row-indices <same_rows_for_all_methods> `
  --run-limit <N> `
  --num-inversion-steps 10 `
  --num-edit-steps 10
```

### 6.2 DiffEdit

```powershell
& 'E:\Anaconda_envs\envs\imgedit\python.exe' DyMask/run_diffedit.py `
  --parquet-path assets/data/V1-00000-of-00001.parquet `
  --row-indices <same_rows_for_all_methods> `
  --run-limit <N> `
  --num-inversion-steps 10 `
  --num-edit-steps 10
```

### 6.3 Prompt-to-Prompt

```powershell
& 'E:\Anaconda_envs\envs\imgedit\python.exe' DyMask/run_p2p.py `
  --parquet-path assets/data/V1-00000-of-00001.parquet `
  --row-indices <same_rows_for_all_methods> `
  --run-limit <N> `
  --controller-mode refine `
  --num-inversion-steps 10 `
  --num-edit-steps 10
```


## 7. Reuse of Existing Samples

For single-sample comparison, rerun all methods from the same `sample.json`.

Examples:

```powershell
& 'E:\Anaconda_envs\envs\imgedit\python.exe' DyMask/run_v1_source_prompt.py --sample-json <sample.json> --phase custom --methods full_dynamic_mask
& 'E:\Anaconda_envs\envs\imgedit\python.exe' DyMask/run_diffedit.py --sample-json <sample.json>
& 'E:\Anaconda_envs\envs\imgedit\python.exe' DyMask/run_p2p.py --sample-json <sample.json> --controller-mode refine
```


## 8. Rules to Keep

- Main table compares editing methods under a shared inversion protocol
- P2P main-table protocol is fixed and not tuned per image
- DiffEdit main-table protocol does not use native inversion
- Any deviation from the above must be marked as appendix / ablation


## 9. Current Code Mapping

- Ours: `DyMask/run_v1_source_prompt.py`
- DiffEdit baseline: `DyMask/run_diffedit.py`
- P2P baseline: `DyMask/run_p2p.py`

