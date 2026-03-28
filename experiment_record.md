# DyMask 阶段实验记录

## `.pt` 文件说明
`.pt` 是 PyTorch 的序列化文件，不是图片，也不是纯文本，通常用来保存：

- 单个 `Tensor`
- `list[Tensor]`
- `dict`
- 训练权重或中间变量

当前项目里主要有两类：

- `zt_src.pt`
  - 含义：反演结束时的源图起点 latent，等价于 `zT_src`
- `src_latents.pt`
  - 含义：源图反演轨迹中每一步的 latent 列表

它不能直接用记事本正常打开。推荐用 Python + `torch.load` 查看。

示例：

```python
import torch

zt_src = torch.load("runs/dymask_v1/phase0_20260328-1051/samples/sample_000_row_000228/zt_src.pt", map_location="cpu")
print(type(zt_src), zt_src.shape, zt_src.dtype)

src_latents = torch.load("runs/dymask_v1/phase0_20260328-1051/samples/sample_000_row_000228/src_latents.pt", map_location="cpu")
print(type(src_latents), len(src_latents), src_latents[0].shape)
```

如果只是想“看内容结构”，用上面这种方式最合适。  
如果只是双击打开，通常只会看到乱码，因为它本质上是二进制张量文件。

---

## 总体原则
开发和实验顺序固定为：

1. `Phase 0`：先证明图像能稳定反演回来
2. `Phase 1`：再证明从反演起点出发，target prompt 的编辑能发生
3. `Phase 2`：再证明全局双分支混合是一个合理 baseline
4. `Phase 3`：再证明 `D_t` 能定位编辑区域
5. `Phase 4`：再证明 `A_t` 能帮助语义聚焦
6. `Phase 5`：再证明 `C_t` 能减少无关区域漂移
7. 最后才做平滑、阈值、时序稳定等 refinement

当前代码已经改成按阶段运行，而不是默认一上来堆完整方法。

---

## 产物命名说明

### 数据与样本层
- `sample_manifest.json`
  - 本轮冻结样本清单，给程序和后续分析使用
- `sample_manifest.csv`
  - 同一份清单的表格版，方便人工查看
- `samples/sample_xxx/sample.json`
  - 单样本元数据，包含 prompt、row index、缓存图路径
- `samples/sample_xxx/source.png`
  - 从 parquet 解码并裁剪到固定尺寸后的 source 图
- `samples/sample_xxx/target_reference.png`
  - parquet 中的编辑后参考图，只作为参考，不参与 V1 生成

### 反演层
- `samples/sample_xxx/source_reconstruction.png`
  - 反演后再重建得到的图，用于 Phase 0 质量检查
- `samples/sample_xxx/zt_src.pt`
  - 反演终点 latent，后续编辑从这里出发
- `samples/sample_xxx/src_latents.pt`
  - 整条 source 反演轨迹的 latent 列表
- `samples/sample_xxx/inversion.json`
  - 当前反演 backend 和步数等元信息

### 方法层
- `samples/sample_xxx/<method>/edited.png`
  - 该方法的最终编辑结果
- `samples/sample_xxx/<method>/mask_summary.png`
  - 该方法选取若干 timestep 后汇总的 mask 图
- `samples/sample_xxx/<method>/aux_summary.png`
  - 该方法的中间图汇总，通常包含 `D_t / A_t / C_t / M_t`
- `samples/sample_xxx/<method>/debug.json`
  - 调试摘要，例如步数、mask 均值、mask 方差
- `samples/sample_xxx/<method>/selected_steps/*.png`
  - 被挑出来的关键 timestep 中间图，后续做归因主要看这些
- `samples/sample_xxx/<method>/selected_steps/selected_steps.json`
  - selected step 图片的索引文件

### 汇总层
- `config.json`
  - 本轮运行的完整配置快照
- `metrics_case_level.csv`
  - 每个样本、每个方法一行的明细指标
- `metrics_summary.csv`
  - 按方法聚合后的均值和标准差
- `metrics_summary.json`
  - 同一份聚合结果的 JSON 版本

以后每次新增产物，都应在本文件里补一句“它是什么、怎么用”。

---

## 新 parquet 结构适配记录

### 新文件
- `assets/data/V1-00000-of-00001.parquet`

### 与旧结构的主要差异
- 旧结构：
  - `original_image`
  - `edited_image`
  - `original_prompt`
  - `edited_prompt`
  - 有 source/target 成对图
- 新结构：
  - `image`
  - `source_prompt`
  - `target_prompt`
  - `edit_action`
  - `aspect_mapping`
  - `blended_words`
  - `mask`
  - 没有 `edited_image`

### 当前适配策略
- `image.bytes` 作为 `source.png`
- `source_prompt` 作为 source prompt
- `target_prompt` 作为 target prompt
- `edit_action` 作为 `edit_prompt` 写入 `sample.json`
- `edited_image` 不存在，因此：
  - `target_reference_path = null`
  - `edit_ref_psnr / edit_ref_lpips` 自动跳过
- 额外字段写入 `sample.json -> extras`
  - `aspect_mapping`
  - `blended_words`
  - `mask`
  - `dataset_format`

### 代码改动
- [data.py](/D:/Program/dymask/DyMask/data.py)
  - 支持 `legacy_edit_pair` 和 `single_image_prompt_edit` 两种 schema
- [schemas.py](/D:/Program/dymask/DyMask/schemas.py)
  - `target_image_path` 改为可选
  - 保留 `record_id` 和 `extras`
- [run_v1.py](/D:/Program/dymask/DyMask/run_v1.py)
  - 允许在无 target reference 的情况下继续评测和落盘

---

## 阶段总览

| Phase | 目标 | 当前状态 | 运行目录 |
| --- | --- | --- | --- |
| Phase 0 | inversion + reconstruction | 已做最小 smoke test | `runs/dymask_v1/phase0_20260328-1051` |
| Phase 1 | target-only edit | 未正式执行 | 待运行 |
| Phase 2 | global blend baseline | 已做最小 smoke test | `runs/dymask_v1/phase2_20260328-1051` |
| Phase 3 | discrepancy-only | 未执行 | 待运行 |
| Phase 4 | `D_t + A_t` | 未执行 | 待运行 |
| Phase 5 | `D_t + A_t + C_t` | 未执行 | 待运行 |

---

## Phase 0：反演与重建

### 目标
- 只做 inversion 和 reconstruction
- 不做编辑
- 保存 `zT_src` 和 `src_latents`

### 当前运行
- 运行目录：`runs/dymask_v1/phase0_20260328-1051`
- 样本：`sample_000_row_000228`
- source prompt：`painting of tree on river banks by Janine Robertson`
- edit prompt：`as a cubist painting`
- target prompt：`cubist painting of tree on river banks by Janine Robertson`

### 当前配置
- backend：`DDIM inversion`
- `num_ddim_steps=2`
- `image_size=512`
- `skip_metrics=true`
- `save_inversion_tensors=true`

### 已保存产物
- `source.png`
- `source_reconstruction.png`
- `zt_src.pt`
- `src_latents.pt`
- `inversion.json`
- `sample_manifest.json/csv`

### 产物注释
- `source_reconstruction.png`
  - Phase 0 最关键结果图，直接判断 reconstruction 是否够稳
- `zt_src.pt`
  - 后续 Phase 1-5 的统一编辑起点
- `src_latents.pt`
  - 后续 `C_t` 和 source reference 需要用到的轨迹

### 当前结论
- `Phase 0` 的最小链路已跑通
- 已经能把 source 图反演并保存 reconstruction
- 已经能保存后续阶段需要用的 inversion 中间量

### 当前不足
- 这里只做了最小 smoke test，还没有做多样本 reconstruction 质量检查
- backend 目前是 `DDIM`，还不是 `NTI`
- 还没系统统计 `PSNR / LPIPS / SSIM`

### 下一步
- 用固定 `8-10` 个样本先跑完整 `Phase 0`
- 人工检查 reconstruction 是否足够稳定
- 决定是否需要先升级 inversion backend

### 补充记录：8 样本 Phase 0 正式首轮
- 运行目录：`runs/dymask_v1/phase0_20260328-1109`
- 样本数：`8`
- `num_ddim_steps=10`
- `save_inversion_tensors=true`
- 总览图：`runs/dymask_v1/phase0_20260328-1109/reconstruction_overview.png`

#### 产物注释
- `reconstruction_overview.png`
  - 8 个样本的总览图，左侧是 `source`，右侧是 `reconstruction`
- `metrics_case_level.csv`
  - 每个样本一行，记录重建指标和对应的 `.pt` 路径
- `metrics_summary.csv`
  - 当前这 8 个样本的均值和标准差

#### 指标结果
- `source_recon_psnr_mean = 28.1760`
- `source_recon_psnr_std = 3.8630`
- `source_recon_lpips_mean = 0.0459`
- `source_recon_lpips_std = 0.0181`

#### 当前观察
- 这轮 8 样本的重建链路已经稳定跑通
- 从指标看，重建质量整体可用，说明当前 DDIM inversion 至少足够支撑后续阶段验证
- 个别样本的 PSNR 明显低于高分样本，后续仍需人工看总览图判断是否存在结构崩坏或风格丢失

#### 当前结论
- `Phase 0` 已经不再只是 smoke test，而是有了第一轮小批量 reconstruction 结果
- 当前可以进入 `Phase 1`，验证 target-only 编辑是否能发生
- 但要保留一个判断点：如果后续编辑阶段不稳定，需要回头核查这些低分 reconstruction 样本

---

## Phase 1：target-only 编辑

### 目标
- 从 `zT_src` 出发
- 只用 target prompt 采样
- 不接 `eps_src / D_t / A_t / C_t / M_t`

### 当前状态
- 已完成 8 样本首轮运行
- 运行目录：`runs/dymask_v1/phase1_20260328-1119`
- 总览图：`runs/dymask_v1/phase1_20260328-1119/phase1_overview.png`

### 待保存产物
- `source.png`
- `source_reconstruction.png`
- `target_only/edited.png`
- 如有需要，可加若干中间步 decode

### 已保存产物
- 每个样本都有：
  - `source.png`
  - `source_reconstruction.png`
  - `target_only/edited.png`
  - `target_only/mask_summary.png`
  - `target_only/aux_summary.png`
  - `target_only/debug.json`
- 汇总文件：
  - `metrics_case_level.csv`
  - `metrics_summary.csv`
  - `metrics_summary.json`
  - `phase1_overview.png`

### 产物注释
- `target_only/edited.png`
  - Phase 1 的最终编辑图，直接回答 target prompt 能不能起作用
- `target_only/mask_summary.png`
  - 这里是全 1 mask 的汇总图，主要用于保持和后续阶段的目录结构一致
- `target_only/aux_summary.png`
  - Phase 1 的辅助图，更多是调试结构一致性，不是主要分析对象
- `target_only/debug.json`
  - 记录了步数和 mask 统计，当前 target-only 的 mask 均值应恒为 1
- `phase1_overview.png`
  - 每行三列：`source | reconstruction | target_only`，是这轮 Phase 1 最值得先看的总览图

### 已跑配置
- 样本数：`8`
- `num_ddim_steps=10`
- backend：`DDIM inversion`
- 方法：`target_only`
- 指标：`PSNR / LPIPS / CLIPScore / edit_ref_psnr / edit_ref_lpips`

### 指标结果
- `clip_score_mean = 0.2981`
- `clip_score_std = 0.0324`
- `edit_ref_psnr_mean = 15.1837`
- `edit_ref_psnr_std = 4.0886`
- `edit_ref_lpips_mean = 0.4850`
- `edit_ref_lpips_std = 0.1296`

### 当前观察
- target-only 已经能在 8 个样本上稳定跑完，说明从 `zT_src` 出发做 target 引导在工程上是可行的
- `debug.json` 中 mask 均值恒为 `1.0`，符合 Phase 1 设计
- 这一阶段的重点已经不再是“能不能跑”，而是人工看 `phase1_overview.png`：
  - 目标属性是否真的被改出来
  - 非编辑区域是否开始漂移
  - 主体结构是否被破坏

### 当前结论
- `Phase 1` 已经成立：target prompt 可以直接作用到从 source inversion 出发的采样过程
- 下一步应进入 `Phase 2` 和 `Phase 3`，分别回答：
  - 全局混合能不能作为一个足够强的简单 baseline
  - `D_t` 是否真的带来局部定位能力

### 补充记录：第一次 Phase 1 复查后的问题定位
- 你人工复查后认为“基本没发生任何编辑”
- 回查代码后确认，当时的 `target_only` 没有走标准 CFG，只是直接用 target 条件做单分支预测
- 这会显著削弱 target prompt 的驱动能力，因此该轮 `Phase 1` 不能作为有效结论

### 补充记录：修正后重新运行
- 修正内容：
  - `TargetPromptPredictor` 改为标准 CFG：
    - `noise_uncond + guidance_scale * (noise_cond - noise_uncond)`
- 重新运行目录：
  - `runs/dymask_v1/phase1_20260328-1124`
  - `runs/dymask_v1/phase1_20260328-1126`
- 其中 `phase1_20260328-1126` 使用：
  - `num_ddim_steps=20`
  - 样本数：`8`
  - 方法：`target_only`
  - 总览图：`runs/dymask_v1/phase1_20260328-1126/phase1_overview.png`

#### 修正后指标结果
- `clip_score_mean = 0.3104`
- `clip_score_std = 0.0478`
- `edit_ref_psnr_mean = 14.0322`
- `edit_ref_lpips_mean = 0.5002`

#### 当前判断
- 修 CFG 后，target-only 的语义驱动比旧版本略有增强，但提升不算大
- 步数从 `10 -> 20` 后，`clip_score` 继续小幅上升，但 `edit_ref_psnr` 下降，说明编辑强度在增加，同时偏离参考图也更明显
- 是否“真正开始发生编辑”，还要以 `phase1_overview.png` 的人工观察为准

#### 当前结论更新
- `Phase 1` 的工程错误已经修掉
- 现在如果仍然看起来“几乎没编辑”，那问题就不再是 CFG 缺失，而更可能在：
  - 当前 DDIM inversion backend 对编辑不够友好
  - target-only 从这个反演起点出发仍然太保守
  - 这类任务本身需要更强的控制信号，而不能指望 target-only
- 因此下一步不应直接跳到完整方法，而应先进入：
  - `Phase 2`：确认 global blend 作为强简单 baseline 的表现
  - `Phase 3`：确认 `D_t` 是否能提供额外局部性

### 补充记录：guidance scale 扫描（8 样本，20 步）
- 运行目录：
  - `runs/dymask_v1/phase1_20260328-1558` 对应 `guidance_scale=10`
  - `runs/dymask_v1/phase1_20260328-1600` 对应 `guidance_scale=12`
  - `runs/dymask_v1/phase1_20260328-1602` 对应 `guidance_scale=20`

#### 指标对比

| guidance | clip_score_mean | edit_ref_psnr_mean | edit_ref_lpips_mean |
| --- | ---: | ---: | ---: |
| 10 | 0.3088 | 13.4797 | 0.5237 |
| 12 | 0.3116 | 13.0920 | 0.5458 |
| 20 | 0.3129 | 12.2107 | 0.6027 |

#### 当前观察
- `guidance_scale` 从 `10 -> 12 -> 20` 时，`clip_score` 只有小幅上升
- 同时 `edit_ref_psnr` 持续下降、`edit_ref_lpips` 持续升高
- 这说明更大的 guidance 确实在增强 target 语义，但代价是结果与参考编辑图偏离得更多

#### 当前结论
- 单纯继续增大 guidance，不会从根本上解决“编辑不明显”的问题
- `Phase 1` 的瓶颈已经不太像是 guidance 太小，而更像是：
  - `target-only` 机制本身不够
  - 或者 `DDIM inversion` 起点对编辑不友好

### 观察重点
- target prompt 能否真的驱动编辑
- 无关区域是否明显漂移
- 主体身份和布局是否容易崩

### 通过标准
- 目标属性能改出来
- 但可以接受背景/结构有一定漂移

### 下一步
- 先跑 `run_limit=1` 的 smoke test
- 再扩到 `8` 个样本

---

## Phase 2：全局融合 baseline

### 目标
- 保留双分支
- 不使用空间 mask
- 只做全局混合：
  - `global_blend_0.3`
  - `global_blend_0.5`
  - `global_blend_0.7`

### 当前运行
- 运行目录：`runs/dymask_v1/phase2_20260328-1051`
- 样本：`sample_000_row_000228`
- 方法：
  - `global_blend_0.3`
  - `global_blend_0.5`
  - `global_blend_0.7`

### 当前配置
- backend：`DDIM inversion`
- `num_ddim_steps=2`
- `skip_metrics=true`
- `selected_step_count=5`

### 已保存产物
- `source_reconstruction.png`
- 每个 `lambda` 各自保存：
  - `edited.png`
  - `mask_summary.png`
  - `aux_summary.png`
  - `debug.json`
  - `selected_steps/*.png`

### 产物注释
- `edited.png`
  - 对应不同 `lambda` 的最终编辑结果，后续和 `target_only`、`D_t only` 对比
- `mask_summary.png`
  - 这里虽然是常数全局 mask，但仍会输出，主要是为了保持和后续阶段结构一致
- `aux_summary.png`
  - 用于观察全局混合时中间信号的整体趋势
- `selected_steps/*.png`
  - 用于抽查固定时刻的中间图，后续做归因时复用相同机制

### 当前可确认事实
- `Phase 2` 最小链路已跑通
- 三个 `lambda` 版本都能独立落盘
- `global_blend_0.5` 的 `debug.json` 显示：
  - `num_steps=2`
  - `mask_mean_per_step=[0.5, 0.5]`
  - `mask_std_per_step=[0.0, 0.0]`

### 当前不足
- 还没有做人工比较，无法判断哪个 `lambda` 更合理
- 还没有加定量指标
- 还没有和 `target-only` 同批样本对比

### 下一步
- 先补 `Phase 1`
- 然后在同一批样本上比较：
  - `target_only`
  - `global_blend_0.3`
  - `global_blend_0.5`
  - `global_blend_0.7`

### 补充记录：8 样本 Phase 2 正式首轮
- 运行目录：`runs/dymask_v1/phase2_20260328-1625`
- 样本数：`8`
- `num_ddim_steps=20`
- `guidance_scale=7.5`
- 总览图：`runs/dymask_v1/phase2_20260328-1625/phase2_overview.png`

#### 新增产物说明
- `delta_trace.csv`
  - 每一步记录一次 `delta = mean(abs(noise_cond - noise_uncond))`
  - 字段：`step_idx, timestep, delta`
- `delta_trace.json`
  - 同一份 delta 轨迹的 JSON 版
- `debug.json`
  - 现在除了 mask 统计，还会记录：
    - `delta_mean_per_step`
    - `delta_mean`
    - `delta_max`
    - `delta_min`

#### 量化结果
- `global_blend_0.3`
  - `clip_score_mean = 0.3075`
  - `edit_ref_psnr_mean = 15.1366`
  - `edit_ref_lpips_mean = 0.4644`
- `global_blend_0.5`
  - `clip_score_mean = 0.3073`
  - `edit_ref_psnr_mean = 14.8609`
  - `edit_ref_lpips_mean = 0.4696`
- `global_blend_0.7`
  - `clip_score_mean = 0.3100`
  - `edit_ref_psnr_mean = 14.5553`
  - `edit_ref_lpips_mean = 0.4739`

#### 与 Phase 1 的直接比较
- 以 `Phase 1, guidance=7.5, 20 步` 为参照：
  - `target_only`: `clip_score_mean = 0.3104`, `edit_ref_psnr_mean = 14.0322`, `edit_ref_lpips_mean = 0.5002`
- 对比可见：
  - `global_blend_0.3` 与 `0.5` 的语义强度略低于 `target_only`
  - 但参考保持更好，`edit_ref_psnr` 更高、`edit_ref_lpips` 更低
  - `global_blend_0.7` 的 `clip_score` 已经接近 `target_only`，同时保持性仍优于 `target_only`

#### 当前结论
- `Phase 2` 已经给出一个比 `target_only` 更稳的简单 baseline
- 如果你后面看到 `D_t only` 或 `D_t + A_t + C_t` 的提升不明显，至少不能比 `global_blend_0.7` 差
- 当前最值得保留的 Phase 2 对照，优先是：
  - `global_blend_0.5`
  - `global_blend_0.7`

### 补充记录：按更强变化的 8 张图重跑 Phase 2
- 运行目录：`runs/dymask_v1/phase2_20260328-1700`
- 总览图：`runs/dymask_v1/phase2_20260328-1700/phase2_overview.png`
- 使用的 row indices：
  - `7, 11, 48, 113, 209, 285, 428, 501`
- 对应编辑类型更偏向：
  - 增加大型实体
  - 场景替换
  - 材质或天气变化
  - 大范围语义改动

#### 本轮比较方法
- `target_only`
- `global_blend_0.3`
- `global_blend_0.5`
- `global_blend_0.7`

#### 本轮汇总指标表

| 方法 | clip_score_mean | edit_ref_psnr_mean | edit_ref_lpips_mean |
| --- | ---: | ---: | ---: |
| target_only | 0.3072 | 15.0325 | 0.4596 |
| global_blend_0.3 | 0.2998 | 16.2691 | 0.4163 |
| global_blend_0.5 | 0.3003 | 15.9512 | 0.4260 |
| global_blend_0.7 | 0.3031 | 15.5821 | 0.4368 |

#### 当前观察
- 这批更强变化样本上，`target_only` 的语义强度仍然最高，但保持性最弱
- 三个 `global_blend` 都明显更稳，尤其 `0.3` 的参考保持最好
- `global_blend_0.7` 在保持性和语义强度之间更平衡，是当前最值得保留的全局融合 baseline

#### delta 记录说明
- 本轮每个方法都输出：
  - `delta_trace.csv`
  - `delta_trace.json`
- `delta` 定义为：
  - `mean(abs(noise_cond - noise_uncond))`
- 用途：
  - 粗看 target prompt 在每个 timestep 对噪声预测的影响强弱
  - 后续可对比 `target_only`、`global_blend`、`D_t only` 在相同样本上的步级响应差异

#### 当前结论更新
- 这轮重跑后，`Phase 2` 已经满足“4 组对比 + 表格汇总 + 更强变化样本”的要求
- 下一步进入 `Phase 3` 时，应该至少和下面两组做对照：
  - `target_only`
  - `global_blend_0.7`

### 补充记录：再次更换 8 张图后的 Phase 2 重跑
- 运行目录：`runs/dymask_v1/phase2_20260328-1715`
- 总览图：`runs/dymask_v1/phase2_20260328-1715/phase2_overview.png`
- 本轮 row indices（与上一轮完全不重合）：
  - `16, 18, 38, 52, 66, 160, 251, 457`

#### 本轮样本特征
- `16`：背景改成 beach
- `18`：星空改成 purple rainbows
- `38`：增加 horse
- `52`：人物穿上 firefighter outfit
- `66`：增加 cat
- `160`：背景增加 tornado
- `251`：snow -> rain
- `457`：sky -> purple

#### 本轮汇总指标表

| 方法 | clip_score_mean | edit_ref_psnr_mean | edit_ref_lpips_mean |
| --- | ---: | ---: | ---: |
| target_only | 0.3043 | 14.9561 | 0.4419 |
| global_blend_0.3 | 0.3019 | 16.8128 | 0.3829 |
| global_blend_0.5 | 0.3031 | 16.1950 | 0.3973 |
| global_blend_0.7 | 0.3057 | 15.6394 | 0.4142 |

#### 当前观察
- 这轮全新样本上，趋势仍然和上一轮一致：
  - `target_only` 语义更强
  - `global_blend` 更稳
- `global_blend_0.7` 再次表现出最平衡的状态：
  - `clip_score` 已经非常接近 `target_only`
  - 但 `edit_ref_psnr` 和 `edit_ref_lpips` 明显更优

#### delta 记录补充说明
- 本轮 4 组方法都保留了：
  - `delta_trace.csv`
  - `delta_trace.json`
- 示例：
  - `runs/dymask_v1/phase2_20260328-1715/samples/sample_000_row_000016/target_only/delta_trace.csv`
- 这份 trace 现在可以直接和后续 `Phase 3` 的 `D_t` 一起看：
  - 一个反映 prompt 驱动力
  - 一个反映 source-target discrepancy

#### 当前结论更新
- 现在 `Phase 2` 已经在两批不同 8 样本上重复验证过，结论相对稳定
- 后续 `Phase 3` 应优先拿这批全新 8 样本继续做，以避免样本偏置影响判断

### 补充记录：再次全部更换 8 张图后的最终 Phase 2 对照
- 运行目录：`runs/dymask_v1/phase2_20260328-1715`
- 本轮 8 个 row indices：
  - `16, 18, 38, 52, 66, 160, 251, 457`
- 与上一轮 `7, 11, 48, 113, 209, 285, 428, 501` 完全不重合

#### 本轮汇总指标表

| 方法 | clip_score_mean | edit_ref_psnr_mean | edit_ref_lpips_mean |
| --- | ---: | ---: | ---: |
| target_only | 0.3043 | 14.9561 | 0.4419 |
| global_blend_0.3 | 0.3019 | 16.8128 | 0.3829 |
| global_blend_0.5 | 0.3031 | 16.1950 | 0.3973 |
| global_blend_0.7 | 0.3057 | 15.6394 | 0.4142 |

#### 当前结论
- 这轮完全换样本后，结论仍然没变：
  - `target_only` 最激进
  - `global_blend` 更稳
  - `global_blend_0.7` 依然最平衡
- 说明 `Phase 2` 的结论已经有一定稳健性，不太像是某一批样本偶然造成的

### 补充记录：新 parquet `V1-00000-of-00001.parquet` 首轮 Phase 2
- 运行目录：`runs/dymask_v1/phase2_20260328-1912`
- 总览图：`runs/dymask_v1/phase2_20260328-1912/phase2_overview.png`
- 数据格式：`single_image_prompt_edit`
- 样本数：`8`
- 这轮没有 target reference 图，因此只保留：
  - `source_recon_psnr`
  - `source_recon_lpips`
  - `clip_score`

#### 这轮样本
- 使用固定 seed 抽样得到 row indices：
  - `6, 26, 28, 35, 57, 62, 70, 139`

#### 这轮汇总指标表

| 方法 | clip_score_mean |
| --- | ---: |
| target_only | 0.3294 |
| global_blend_0.3 | 0.3065 |
| global_blend_0.5 | 0.3163 |
| global_blend_0.7 | 0.3256 |

#### 当前观察
- 新 parquet 上，`target_only` 和 `global_blend_0.7` 的 `clip_score` 很接近
- `global_blend_0.7` 仍然是最接近 `target_only` 的简单稳定版本
- 由于缺少参考编辑图，这轮暂时不能判断保持性，只能看：
  - reconstruction 质量
  - target 语义匹配

#### 当前结论
- 新 parquet 结构已经成功适配
- 现在这个数据源已经可以直接进入后续 Phase 3/4/5
- 如果要继续在这个新数据源上做机制验证，建议先从 `Phase 2 -> Phase 3` 沿同一批 8 样本推进

### 补充说明：无 `target_reference` 时的指标解释
- 新 parquet 没有编辑后参考图，因此：
  - `edit_ref_psnr`
  - `edit_ref_lpips`
  不再表示“与目标图的接近程度”
- 现在它们改为对 `source.png` 计算：
  - `edit_ref_psnr` 越高，表示结果越接近原图，改动越保守
  - `edit_ref_lpips` 越低，表示结果越接近原图，改动越保守
- 因此在新 parquet 上：
  - `clip_score` 主要看是否朝 target prompt 走
  - `edit_ref_psnr / lpips` 主要看是否偏离原图太多

### 新 parquet 上沿同一批 8 样本的阶段结果

使用样本：
- row indices：`6, 26, 28, 35, 57, 62, 70, 139`

#### 总览图
- `Phase 2`: `runs/dymask_v1/phase2_20260328-1912/phase2_overview.png`
- `Phase 3`: `runs/dymask_v1/phase3_20260328-1932/phase3_overview.png`
- `Phase 4`: `runs/dymask_v1/phase4_20260328-2006/phase4_overview.png`
- `Phase 5`: `runs/dymask_v1/phase5_20260328-2009/phase5_overview.png`

#### 汇总指标表

| 方法 | clip_score_mean | source-ref PSNR | source-ref LPIPS |
| --- | ---: | ---: | ---: |
| target_only | 0.3294 | 14.9608 | 0.5204 |
| global_blend_0.3 | 0.3065 | 18.9051 | 0.3793 |
| global_blend_0.5 | 0.3163 | 17.3127 | 0.4366 |
| global_blend_0.7 | 0.3256 | 16.1160 | 0.4724 |
| discrepancy_only | 0.3082 | 18.4601 | 0.3753 |
| discrepancy_attention | 0.2936 | 20.4253 | 0.3149 |
| full_dynamic_mask | 0.2970 | 20.0472 | 0.3274 |

#### 当前观察
- 新 parquet 上，`target_only` 语义最强，但偏离原图也最大
- `global_blend_0.7` 仍然是最接近 `target_only` 的简单 baseline
- `discrepancy_only` 比 `global_blend_0.7` 更保守，但语义更弱
- `discrepancy_attention` 和 `full_dynamic_mask` 都继续往“更保守”方向走
- 这意味着在这个数据源上，`A_t` 和 `C_t` 目前没有把保守性转化成更强的目标语义

#### 当前结论
- 新 parquet 上，这套 `D_t / A_t / C_t` 当前版本还没有打赢 `Phase 2`
- 如果继续优化，优先方向应是：
  - 修正 `A_t` 的 token 选择与 cond branch 提取
  - 调 `threshold / temperature / alpha / beta / gamma`

### 补充记录：修复 A_t 后在新 parquet 上重跑
- 核心修复：
  - inversion 结束后重新挂回 attention controller
  - `A_t` 聚合优先只看编辑相关词
  - 单样本 probe 已确认不再是全黑 attention
- 单样本 probe 目录：
  - `runs/attention_probe/attention_20260328-2117`

#### 修复后新 parquet 的阶段结果

| 方法 | clip_score_mean | source-ref PSNR | source-ref LPIPS |
| --- | ---: | ---: | ---: |
| discrepancy_only | 0.3082 | 18.4601 | 0.3753 |
| discrepancy_attention | 0.3122 | 18.3850 | 0.3861 |
| full_dynamic_mask | 0.3148 | 18.0504 | 0.3980 |

#### 当前观察
- 修好 `A_t` 之后：
  - `Phase 4` 的 `clip_score` 从 `0.2936` 提升到 `0.3122`
  - `Phase 5` 的 `clip_score` 提升到 `0.3148`
- 说明之前 `A_t` 全黑确实是实现问题，而不是 attention prior 完全无效
- 修复后趋势变成：
  - `D_t only` 最保守
  - `D_t + A_t` 语义增强
  - `D_t + A_t + C_t` 再进一步增强一点语义，但也更偏离原图

#### 当前结论更新
- 修复后的 `A_t` 是有效的
- 在新 parquet 上：
  - `Phase 4` 现在已经优于旧版 `Phase 4`
  - `Phase 5` 也优于旧版 `Phase 5`
- 但即便如此，它们暂时还是没有超过 `Phase 2 global_blend_0.7`
- 所以下一步如果继续优化，最合理的是围绕：
  - `A_t` 权重
  - `C_t` 权重
  - `threshold / temperature`
  做小范围调参，而不是再加新模块

---

## Phase 3：仅 `D_t`

### 当前状态
- 已完成 8 样本首轮运行
- 运行目录：`runs/dymask_v1/phase3_20260328-1732`
- 使用 row indices：
  - `16, 18, 38, 52, 66, 160, 251, 457`
- 总览图：`runs/dymask_v1/phase3_20260328-1732/phase3_overview.png`

### 已保存产物
- 每个样本都有：
  - `discrepancy_only/edited.png`
  - `discrepancy_only/mask_summary.png`
  - `discrepancy_only/aux_summary.png`
  - `discrepancy_only/debug.json`
  - `discrepancy_only/delta_trace.csv`
  - `discrepancy_only/delta_trace.json`
  - `discrepancy_only/selected_steps/*.png`

### 本轮汇总指标表

| 方法 | clip_score_mean | edit_ref_psnr_mean | edit_ref_lpips_mean |
| --- | ---: | ---: | ---: |
| discrepancy_only | 0.2995 | 16.8342 | 0.3823 |

### 与 Phase 2 的主对照比较

| 方法 | clip_score_mean | edit_ref_psnr_mean | edit_ref_lpips_mean |
| --- | ---: | ---: | ---: |
| target_only | 0.3043 | 14.9561 | 0.4419 |
| global_blend_0.7 | 0.3057 | 15.6394 | 0.4142 |
| discrepancy_only | 0.2995 | 16.8342 | 0.3823 |

### 当前观察
- `discrepancy_only` 的保持性目前是三者里最强的：
  - `edit_ref_psnr` 最高
  - `edit_ref_lpips` 最低
- 但语义强度没有超过 `target_only` 或 `global_blend_0.7`
- 这说明 `D_t` 当前更像是在“帮你收缩编辑范围”，而不是在增强编辑语义

### 中间量观察
- `debug.json` 已经记录：
  - `mask_mean_per_step`
  - `mask_std_per_step`
  - `delta_mean_per_step`
- 以 `sample_000_row_000016` 为例：
  - 前几步 `mask_mean` 较高，后面逐步收缩
  - 说明 discrepancy mask 的时序行为已经不是常数 mask

### 当前结论
- `Phase 3` 已经成立一半：
  - `D_t` 确实在帮助限制无关区域漂移
- 但还没有证明：
  - `D_t` 能把编辑区域“更准确地聚焦到目标语义”
- 所以按顺序应进入 `Phase 4`，看 `A_t` 是否能把 `D_t` 的保守性转换成更好的语义聚焦

---

## Phase 4：`D_t + A_t`

### 当前状态
- 已完成 8 样本首轮运行
- 运行目录：`runs/dymask_v1/phase4_20260328-1743`
- 使用 row indices：
  - `16, 18, 38, 52, 66, 160, 251, 457`
- 总览图：`runs/dymask_v1/phase4_20260328-1743/phase4_overview.png`

### 已保存产物
- 每个样本都有：
  - `discrepancy_attention/edited.png`
  - `discrepancy_attention/mask_summary.png`
  - `discrepancy_attention/aux_summary.png`
  - `discrepancy_attention/debug.json`
  - `discrepancy_attention/delta_trace.csv`
  - `discrepancy_attention/delta_trace.json`
  - `discrepancy_attention/selected_steps/*.png`

### 本轮汇总指标表

| 方法 | clip_score_mean | edit_ref_psnr_mean | edit_ref_lpips_mean |
| --- | ---: | ---: | ---: |
| discrepancy_attention | 0.2996 | 17.1129 | 0.3787 |

### 与 Phase 3 的直接比较

| 方法 | clip_score_mean | edit_ref_psnr_mean | edit_ref_lpips_mean |
| --- | ---: | ---: | ---: |
| discrepancy_only | 0.2995 | 16.8342 | 0.3823 |
| discrepancy_attention | 0.2996 | 17.1129 | 0.3787 |

### 当前观察
- 加入 `A_t` 之后：
  - `clip_score` 基本持平，但略高
  - `edit_ref_psnr` 上升
  - `edit_ref_lpips` 下降
- 这说明 `A_t` 至少没有把结果弄坏，而且当前这批样本上是**小幅正收益**

### 当前结论
- `Phase 4` 初步成立：
  - `A_t` 对 `D_t only` 是有帮助的，但当前提升幅度不大
- 也就是说，`A_t` 现在更像是在做细化和稳态修正，而不是带来根本性的编辑能力提升
- 下一步应进入 `Phase 5`，看 `C_t` 是否还能进一步减少无关区域漂移

### 补充记录：修复 A_t 提取链路
- 发现问题：
  - inversion 之后 attention controller 没重新挂回去
  - 导致 `Phase 4/5` 里的 `A_t` 基本为空，单独可视化时图几乎全黑
- 修复内容：
  - 在 inversion 完成后，重新执行 `register_attention_control(self.pipe, self.attention_store)`
  - attention probe 现在改为优先只看编辑词：
    - 例如 `toy / cat / fur`
- 单样本 probe：
  - 目录：`runs/attention_probe/attention_20260328-2117`
  - 总览图：`runs/attention_probe/attention_20260328-2117/samples/sample_000_row_000026/attention_only/attention_overview.png`
  - 现在单步 attention 图不再是 91 字节的全黑图，而是有几 KB 的正常图片

### 补充记录：修复后重新运行新 parquet 的 Phase 4
- 运行目录：`runs/dymask_v1/phase4_20260328-2119`
- 总览图：`runs/dymask_v1/phase4_20260328-2119/phase4_overview.png`

#### 修复前后对比

| 版本 | clip_score_mean | source-ref PSNR | source-ref LPIPS |
| --- | ---: | ---: | ---: |
| 修复前 `discrepancy_attention` | 0.2936 | 20.4253 | 0.3149 |
| 修复后 `discrepancy_attention` | 0.3122 | 18.3850 | 0.3861 |

#### 当前结论更新
- 修好 `A_t` 以后，`Phase 4` 有明显改善：
  - `clip_score` 从 `0.2936 -> 0.3122`
  - 说明之前全黑 `A_t` 确实是实现问题，不是 attention prior 本身没用
- 同时保持性有所下降：
  - 说明 `A_t` 现在终于在推动编辑，而不是只做保守约束
- 当前修复后的 `Phase 4` 已经比 `Phase 3` 更有说服力

---

## Phase 5：`D_t + A_t + C_t`

### 当前状态
- 已完成 8 样本首轮运行
- 运行目录：`runs/dymask_v1/phase5_20260328-1748`
- 使用 row indices：
  - `16, 18, 38, 52, 66, 160, 251, 457`
- 总览图：`runs/dymask_v1/phase5_20260328-1748/phase5_overview.png`

### 已保存产物
- 每个样本都有：
  - `full_dynamic_mask/edited.png`
  - `full_dynamic_mask/mask_summary.png`
  - `full_dynamic_mask/aux_summary.png`
  - `full_dynamic_mask/debug.json`
  - `full_dynamic_mask/delta_trace.csv`
  - `full_dynamic_mask/delta_trace.json`
  - `full_dynamic_mask/selected_steps/*.png`

### 本轮汇总指标表

| 方法 | clip_score_mean | edit_ref_psnr_mean | edit_ref_lpips_mean |
| --- | ---: | ---: | ---: |
| full_dynamic_mask | 0.2982 | 17.1051 | 0.3784 |

### 与 Phase 4 的直接比较

| 方法 | clip_score_mean | edit_ref_psnr_mean | edit_ref_lpips_mean |
| --- | ---: | ---: | ---: |
| discrepancy_attention | 0.2996 | 17.1129 | 0.3787 |
| full_dynamic_mask | 0.2982 | 17.1051 | 0.3784 |

### 当前观察
- 加入 `C_t` 之后：
  - `edit_ref_psnr` 与 `Phase 4` 基本持平
  - `edit_ref_lpips` 略好一点
  - `clip_score` 略有下降
- 这说明 `C_t` 当前更多是在做微弱的保守性修正，并没有带来明显的新提升

### 当前结论
- 目前这版 `full_dynamic_mask` 没有显著优于 `D_t + A_t`
- 如果后面要继续优化，最应该优先检查的不是再堆模块，而是：
  - `C_t` 的定义是否过弱
  - `alpha / beta / gamma` 是否失衡
  - `C_t` 是否真正提供了和 `D_t + A_t` 不同的信息

### 当前阶段总判断

| 阶段方法 | clip_score_mean | edit_ref_psnr_mean | edit_ref_lpips_mean | 当前判断 |
| --- | ---: | ---: | ---: | --- |
| target_only | 0.3043 | 14.9561 | 0.4419 | 最激进，语义强，但漂移大 |
| global_blend_0.7 | 0.3057 | 15.6394 | 0.4142 | 当前最平衡的简单 baseline |
| discrepancy_only | 0.2995 | 16.8342 | 0.3823 | 最强保守性，语义偏弱 |
| discrepancy_attention | 0.2996 | 17.1129 | 0.3787 | 比 D-only 略好，Phase 4 小幅成立 |
| full_dynamic_mask | 0.2982 | 17.1051 | 0.3784 | 与 Phase 4 几乎持平，C_t 贡献不明显 |

---

## Phase 3：仅 `D_t`

### 目标
- 计算 `D_t = mean_channel(abs(eps_tar - eps_src))`
- 用 `D_t` 单独构造 `M_t`
- 不接 `A_t`
- 不接 `C_t`

### 当前状态
- 代码入口已具备，对应方法名：`discrepancy_only`
- 尚未正式执行阶段实验

### 待保存产物
- `edited.png`
- `D_t` selected steps
- `M_t` selected steps
- `debug.json`

### 观察重点
- `D_t` 是否大致高亮编辑区域
- 最终结果是否比全局混合更局部

### 风险
- `D_t` 很散
- `D_t` 过于全局
- `M_t` 太弱导致编辑打不进去

### 下一步
- 先跑单样本 smoke test
- 再看是否需要调 `threshold / temperature`

---

## Phase 4：`D_t + A_t`

### 目标
- 抓 target token 的 cross-attention
- 聚合得到 `A_t`
- 与 `D_t` 一起构造 `M_t`

### 当前状态
- 代码入口已具备，对应方法名：`discrepancy_attention`
- 尚未正式执行阶段实验

### 待保存产物
- `D_t`
- `A_t`
- `M_t`
- `edited.png`
- `selected_steps`

### 观察重点
- `A_t` 是否有明确语义区域
- 加入 `A_t` 后是否比 `D_t only` 更聚焦

### 下一步
- 先做单样本 attention 可视化
- 确认 `A_t` 本身有意义后再批量跑

---

## Phase 5：`D_t + A_t + C_t`

### 目标
- 在 `D_t + A_t` 基础上加入 preservation prior `C_t`
- 减少无关区域漂移

### 当前状态
- 代码入口已具备，对应方法名：`full_dynamic_mask`
- 尚未正式执行阶段实验

### 待保存产物
- `D_t`
- `A_t`
- `C_t`
- `M_t`
- `edited.png`
- `selected_steps`

### 观察重点
- 背景是否更稳
- 非编辑区域是否更少被改
- 是否出现 `C_t` 过强、把编辑压死的问题

### 下一步
- 在 `Phase 4` 跑通后再做
- 先看单样本，再上小批量

---

## 后续固定记录模板

每次完成一个阶段，建议按下面结构追加：

```md
## Phase X：阶段名

### 运行目录
- 

### 样本
- sample_id:
- source prompt:
- edit prompt:
- target prompt:

### 配置
- backend:
- num_ddim_steps:
- methods:
- metrics:

### 保存产物
- 

### 现象观察
- 

### 结论
- 

### 下一步
- 
```

---

## 当前建议执行顺序

1. 先补 `Phase 1` 的正式 smoke test
2. 再把 `Phase 1` 和 `Phase 2` 放到同一批样本上对比
3. 然后进入 `Phase 3`
4. `Phase 3` 成立后再进 `Phase 4`
5. 最后才做 `Phase 5`

不要跳步，不要一次性把所有模块堆上去。
