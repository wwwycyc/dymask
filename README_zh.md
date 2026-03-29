# DyMask 中文说明

[English](D:/Program/dymask/README.md) | [中文](D:/Program/dymask/README_zh.md)

## 1. 项目简介
DyMask 是一个基于以下组件的图像编辑实验系统：

- Stable Diffusion 1.5
- Null-Text Inversion
- 基于动态 mask 的噪声混合编辑
- Prompt 条件注意力分析

主要代码位于 [DyMask](D:/Program/dymask/DyMask)。

## 2. 主要脚本
- [DyMask/run_v1.py](D:/Program/dymask/DyMask/run_v1.py)
  主实验入口。负责样本准备、反演、编辑、可视化和指标导出。
- [DyMask/visualize_attention.py](D:/Program/dymask/DyMask/visualize_attention.py)
  单样本 attention 探针，用于查看 target prompt attention。
- [DyMask/backfill_run_metrics.py](D:/Program/dymask/DyMask/backfill_run_metrics.py)
  对已有 run 目录重新计算指标。
- [DyMask/inspect_pt.py](D:/Program/dymask/DyMask/inspect_pt.py)
  查看保存下来的 `.pt` 张量结构。

## 3. 支持的数据格式
当前 [DyMask/data.py](D:/Program/dymask/DyMask/data.py) 支持两类 parquet。

旧版成对编辑格式：
- `original_prompt`
- `original_image`
- `edit_prompt`
- `edited_prompt`
- `edited_image`

V1 单图编辑格式：
- `image`
- `id`
- `source_prompt`
- `target_prompt`
- `edit_action`
- `aspect_mapping`
- `blended_words`
- `mask`

## 4. 环境说明
下面所有命令默认：

- 当前目录是 `D:\Program\dymask`
- `python` 指向可用环境

如果要显式使用本机环境，可以写：

```powershell
& 'E:\Anaconda_envs\envs\imgedit\python.exe' ...
```

## 5. 安装方式
先单独安装 PyTorch，再安装其余依赖。

CUDA 12.1 示例：

```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

CPU 示例：

```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

然后再安装项目依赖：

```powershell
pip install -r requirements.txt
```

## 6. 查看帮助
```powershell
python DyMask/run_v1.py --help
python DyMask/visualize_attention.py --help
python DyMask/backfill_run_metrics.py --help
python DyMask/inspect_pt.py --help
```

## 7. 主实验脚本 run_v1.py
最基本的启动方式：

```powershell
python DyMask/run_v1.py
```

常用参数：
- `--parquet-path`
  指定输入 parquet
- `--sample-json`
  复跑已有样本
- `--sample-count`
  抽样数量
- `--run-limit`
  实际执行样本数
- `--row-indices`
  指定行号
- `--phase`
  使用预定义方法组合
- `--methods`
  自定义方法列表
- `--mask-mode dynamic|static`
  动态 mask 或冻结 mask
- `--skip-metrics`
  跳过指标
- `--dry-run`
  只做样本准备，不跑模型
- `--save-inversion-tensors`
  保存反演张量

## 8. 反演步数和编辑步数
现在已经支持解耦：

- `--num-inversion-steps`
- `--num-edit-steps`

兼容旧参数：

- `--num-ddim-steps`

说明：
- 只传 `--num-ddim-steps 10` 时，等价于反演和编辑都设为 10
- 如果显式传了 `--num-inversion-steps` 或 `--num-edit-steps`，则以新参数为准

示例：

```powershell
python DyMask/run_v1.py --num-inversion-steps 10 --num-edit-steps 20
```

## 9. phase 对应关系
- `phase0`
  只做 inversion / reconstruction
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
  手动指定 `--methods`

## 10. 常用五组实验
固定五组方法：

- `target_only`
- `global_blend`
- `discrepancy_only`
- `discrepancy_attention`
- `full_dynamic_mask`

推荐命令：

```powershell
python DyMask/run_v1.py --phase custom --methods target_only global_blend discrepancy_only discrepancy_attention full_dynamic_mask
```

显示名称对应：
- `target_only` -> `target-only`
- `global_blend` -> `global blend`
- `discrepancy_only` -> `D_t`
- `discrepancy_attention` -> `D_t + A_t`
- `full_dynamic_mask` -> `Full`

## 11. 常用启动命令
### 11.1 在默认 parquet 上跑 8 个样本
```powershell
python DyMask/run_v1.py --phase custom --methods target_only global_blend discrepancy_only discrepancy_attention full_dynamic_mask --sample-count 8 --run-limit 8
```

### 11.2 在 `V1-00000-of-00001.parquet` 上跑 8 个样本
```powershell
python DyMask/run_v1.py --phase custom --methods target_only global_blend discrepancy_only discrepancy_attention full_dynamic_mask --parquet-path assets/data/V1-00000-of-00001.parquet --sample-count 8 --run-limit 8
```

### 11.3 只跑指定行
```powershell
python DyMask/run_v1.py --parquet-path assets/data/V1-00000-of-00001.parquet --row-indices 6 26 28 --run-limit 3 --phase custom --methods target_only global_blend discrepancy_only discrepancy_attention full_dynamic_mask
```

### 11.4 单样本最小验证
```powershell
python DyMask/run_v1.py --parquet-path assets/data/V1-00000-of-00001.parquet --row-indices 6 --sample-count 1 --run-limit 1 --phase custom --methods target_only --skip-metrics
```

### 11.5 反演 5 步，编辑 8 步
```powershell
python DyMask/run_v1.py --parquet-path assets/data/V1-00000-of-00001.parquet --row-indices 6 --sample-count 1 --run-limit 1 --phase custom --methods target_only --skip-metrics --num-inversion-steps 5 --num-edit-steps 8
```

### 11.6 只做 dry-run
```powershell
python DyMask/run_v1.py --parquet-path assets/data/V1-00000-of-00001.parquet --sample-count 8 --run-limit 8 --dry-run
```

### 11.7 跳过指标
```powershell
python DyMask/run_v1.py --phase custom --methods target_only global_blend discrepancy_only discrepancy_attention full_dynamic_mask --skip-metrics
```

### 11.8 使用 static mask
```powershell
python DyMask/run_v1.py --phase phase4 --mask-mode static
```

### 11.9 从已有 sample.json 复跑
```powershell
python DyMask/run_v1.py --sample-json runs/dymask_v1/<run_dir>/samples/<sample_id>/sample.json --phase custom --methods target_only global_blend discrepancy_only discrepancy_attention full_dynamic_mask
```

## 12. Attention 探针脚本
基本用法：

```powershell
python DyMask/visualize_attention.py
```

### 12.1 从 parquet 取单样本
```powershell
python DyMask/visualize_attention.py --parquet-path assets/data/V1-00000-of-00001.parquet --row-index 6
```

### 12.2 从 sample.json 复跑
```powershell
python DyMask/visualize_attention.py --sample-json runs/dymask_v1/<run_dir>/samples/<sample_id>/sample.json
```

### 12.3 单独设置反演和编辑步数
```powershell
python DyMask/visualize_attention.py --parquet-path assets/data/V1-00000-of-00001.parquet --row-index 6 --num-inversion-steps 10 --num-edit-steps 20
```

输出目录：
- `runs/attention_probe/<timestamp>/samples/<sample_id>/attention_only`

常见产物：
- `attention_overview.png`
- `selected_steps/*.png`
- `delta_trace.csv`
- `attention_debug.json`

## 13. 指标回填脚本
给已有 run 目录重算指标：

```powershell
python DyMask/backfill_run_metrics.py runs/dymask_v1/<run_dir>
```

会更新：
- `metrics_case_level.csv`
- `metrics_summary.csv`
- `metrics_summary.json`

说明：
- 这个脚本只回填通用指标
- 不重建 overview
- 不重建五组专用 summary 表

## 14. inspect_pt.py
查看张量文件：

```powershell
python DyMask/inspect_pt.py runs/dymask_v1/<run_dir>/samples/<sample_id>/zt_src.pt
python DyMask/inspect_pt.py runs/dymask_v1/<run_dir>/samples/<sample_id>/src_latents.pt --max-items 10
```

## 15. 输出目录结构
典型 run 目录：

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

说明：
- `target_reference.png` 只有数据集本身提供目标编辑图时才存在

## 16. overview.png
每个样本的 `overview.png` 当前包含 7 张图：

1. source
2. target-only
3. global blend
4. D_t
5. D_t + A_t
6. Full
7. D/A/C/mask maps

## 17. 指标说明
常见字段：
- `clip_score`
- `source_recon_psnr`
- `source_recon_lpips`
- `edit_ref_psnr`
- `edit_ref_lpips`
- `edit_source_psnr`
- `edit_source_lpips`
- `edit_reference_mode`

含义：
- `clip_score`
  编辑图与 `target_prompt` 的图文对齐分数
- `source_recon_*`
  原图和重建图的差异
- `edit_ref_*`
  编辑图和目标参考图的差异
- `edit_source_*`
  编辑图和原图的差异

重要说明：
- 如果数据集没有目标编辑图，则 `edit_ref_*` 为空
- 这时只能直接参考 `clip_score` 和 `edit_source_*`
- `edit_source_*` 表示改动强度，不表示编辑正确性

## 18. step_diagnostics
每个方法目录里现在有：
- `step_diagnostics.csv`
- `step_diagnostics.json`

这些文件用于判断 dynamic mask 是否退化成软 global blend。

每步会导出：
- `mean`
- `std`
- `p10`
- `p90`
- `top_bottom_gap`
- `gt_0_5_ratio`
- `entropy`
- `blend_strength`

一般解读：
- `global_blend` 的 mask 统计应接近常数图
- 如果 `Full` 的 mask 统计明显有结构，但视觉仍和 `global_blend` 接近，说明问题更像是“mask 有结构但影响不够强”，而不是“mask 完全退化”

## 19. 建议工作流
### 19.1 快速 sanity check
```powershell
python DyMask/run_v1.py --parquet-path assets/data/V1-00000-of-00001.parquet --row-indices 6 --sample-count 1 --run-limit 1 --phase custom --methods target_only global_blend discrepancy_only discrepancy_attention full_dynamic_mask --skip-metrics
```

### 19.2 跑 8 个样本
```powershell
python DyMask/run_v1.py --parquet-path assets/data/V1-00000-of-00001.parquet --sample-count 8 --run-limit 8 --phase custom --methods target_only global_blend discrepancy_only discrepancy_attention full_dynamic_mask
```

### 19.3 看结果
- 先看 `samples/<sample_id>/overview.png`
- 再看 `metrics_five_methods_summary.csv`
- 如果视觉差异不明显，再看 `step_diagnostics.json`

### 19.4 做 attention 探针
```powershell
python DyMask/visualize_attention.py --parquet-path assets/data/V1-00000-of-00001.parquet --row-index 6
```

## 20. 默认推荐命令模板
```powershell
python DyMask/run_v1.py --phase custom --methods target_only global_blend discrepancy_only discrepancy_attention full_dynamic_mask --parquet-path <your.parquet> --sample-count 8 --run-limit 8 --num-inversion-steps 10 --num-edit-steps 10
```
