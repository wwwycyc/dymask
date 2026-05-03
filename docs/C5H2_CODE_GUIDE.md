# C5H2 代码导读

## 1. 先说结论

如果你的目标是“最快读懂 C5H2 在做什么”，不要先从旧 `DyMask/` 里那份大文件开始翻。最推荐的顺序是：

1. `DyMaskRefactor/support_line/ARCHITECTURE.md`
2. `DyMaskRefactor/support_line/execution.py`
3. `DyMaskRefactor/support_line/registry.py`
4. `DyMaskRefactor/support_line/specs.py`
5. `DyMaskRefactor/support_line/configuration.py`
6. `DyMaskRefactor/support_line/mainline_roi.py`
7. `DyMaskRefactor/support_line/mainline_hardcore.py`
8. `DyMaskRefactor/support_line/base.py`
9. `DyMaskRefactor/support_line/masking.py`
10. `DyMaskRefactor/support_line/roi.py`
11. `DyMaskRefactor/v1_source_prompt_temporal_support.py`
12. `DyMaskRefactor/v1.py`
13. `DyMaskRefactor/metric_runtime.py`

如果你想追历史实现，再回头看：

1. `DyMask/run_v1_source_prompt_source_anchored_support_c5h2.py`
2. `DyMask/v1_source_prompt_source_anchored_support_c5h2.py`

一句话概括：

- `DyMaskRefactor/` 是现在最适合读的版本，结构清楚。
- `DyMask/` 是历史原版，适合核对“当时到底怎么跑的”。

## 2. C5H2 在整条主线里的位置

先不要把 `C5H2` 理解成“整个项目的最终版”。它更准确的定位是：

- `C5` 系列里，围绕“confidence-gated local anchor relaxation”开的分支。
- `C5H0-C5H1` 先把主线改成更硬的 hard-core 逻辑。
- `C5H2` 在这个基础上，加入了**确定性的 DiffEdit soft ROI**，并把 ROI 拆成**core + boundary** 两部分。
- 后面的 `C5H3-C5H4` 再在 `C5H2` 基础上做 under-edit rescue。

所以读 C5H2 时，要知道它不是从零开始，而是站在 `C5H0-C5H1` 上继续加了一层“deterministic core-boundary ROI”。

## 3. 读代码时先带着这 5 个问题

建议你读之前，先带着这 5 个问题：

1. 这个实验到底从哪里启动，参数怎么进来？
2. C5H2 和 baseline 相比，真正改了哪几处钩子？
3. `soft ROI`、`hard core`、`boundary` 分别在哪里生成？
4. support memory 写到哪里，effective mask 怎么读出来，anchor 又怎么用？
5. 最终指标是怎么定义的，特别是 `edit_clip`、`outside_lpips`、`outside_psnr`、`locality_ratio`？

下面的阅读顺序，就是围绕这 5 个问题展开的。

## 4. 第一层：先看运行入口，不要先看算法细节

### 4.1 `DyMaskRefactor/support_line/ARCHITECTURE.md`

这是最适合热启动的文件。它会先告诉你：

- `support_line/` 只负责 `source_anchored_support` 这一条实验主线的组织层。
- 哪些文件是“运行编排”，哪些文件是“机制实现”，哪些只是“兼容导出”。

如果你一上来就直接看 `mainline_roi.py`，很容易陷进细节，看不清 C5H2 在整个系统里的位置。

### 4.2 `DyMaskRefactor/support_line/execution.py`

这是 refactor 版最关键的调度文件。

你需要重点看两个函数：

- `prepare_support_run()`
- `execute_support_run()`

它们负责的事情很清楚：

- 读取 variant
- 构建 config
- 建 run 目录
- 采样数据并写 manifest
- 创建 pipeline 和 inversion backend
- 实例化 editor
- 跑编辑
- 汇总 case-level 和 summary 指标

你可以把这个文件理解为：

- “这次实验怎么被装起来”

而不是：

- “这次实验怎么编辑图像”

### 4.3 `DyMaskRefactor/support_line/registry.py`

这个文件告诉你：

- `variant='c5h2'` 最后会映射到哪个 editor 类
- 默认输出目录是什么
- 这个 variant 的名字、描述、额外参数是什么

你需要盯住这一段：

- `c5h2 -> RefactorSupportC5H2Editor`

它说明：

- refactor 版里，C5H2 的真正实现类在 `mainline_roi.py`

### 4.4 `DyMaskRefactor/support_line/specs.py`

这个文件不是算法实现，但它很重要，因为它定义了：

- `SupportVariantSpec`
- 哪些参数是这条 support 线公共的
- 哪些参数是 C5H2 自己新增的

如果你以后要复现实验，或者要写论文里的参数表，这个文件非常有用。

### 4.5 `DyMaskRefactor/support_line/configuration.py`

这个文件负责把 CLI 参数变成 `ExperimentConfig` 和 `DiffEditConfig`。

这里建议重点看：

- `build_config()`
- `build_diffedit_config()`

读完之后你会知道：

- `sample_batch_size`
- `min_sample_batch_size`
- `num_inversion_steps`
- `num_edit_steps`
- `mask_mode`
- `enable_structure_distance`

这些运行时配置最后是怎么真正落进实验的。

## 5. 第二层：C5H2 本体到底改了什么

### 5.1 先看 `DyMaskRefactor/support_line/mainline_roi.py`

这是 C5H2 的核心文件。

你可以把它理解为：

- “在 C5H0/C5H1 的 hard-core 主线之上，加了一层 deterministic ROI + core/boundary 分解”

建议按下面顺序读。

### 5.2 `__init__`

先看构造函数，目的是认参数，不是背代码。

C5H2 额外关心的参数，主要分 4 类：

- core read
  - `core_read_start_weight`
  - `core_read_end_weight`
- boundary read
  - `boundary_read_start_weight`
  - `boundary_read_end_weight`
- boundary anchor / confidence
  - `boundary_anchor_start_weight`
  - `boundary_anchor_end_weight`
  - `boundary_confidence_weight`
- core threshold policy
  - `roi_core_quantile`
  - `roi_core_peak_ratio`
  - `roi_core_threshold_min`
  - `roi_core_threshold_max`
  - `roi_core_min_active_ratio`
  - `roi_core_active_floor`

你读这些名字时，只要先记住一个大框架：

- `core` 负责“稳定的主体编辑区”
- `boundary` 负责“柔和的边缘补充区”

### 5.3 `_compute_seeded_soft_roi()` 和 `_load_or_compute_soft_roi()`

这是 C5H2 最重要的第一步：**让 DiffEdit soft ROI 变成 per-sample deterministic**。

它做了两件事：

1. 根据 `row_index + source_prompt + target_prompt + seed_offset` 构造稳定 seed。
2. 把 soft ROI 缓存到磁盘，下次同配置复用。

你要抓住它解决的问题：

- 原来的 soft ROI 带随机性。
- 同一张图多跑几次，ROI 可能不完全一样。
- 这会让实验波动变大，也会让后面的 support / anchor 难分析。

所以 C5H2 先把“输入给后面算法的 ROI 先验”固定住。

### 5.4 `_build_core_boundary_from_soft()`

这是 C5H2 第二个核心点：**把 soft ROI 拆成 core 和 boundary**。

这个函数的逻辑可以直接记成下面这套：

1. 先看 soft ROI 的峰值 `peak`。
2. 从有效激活区域里算一个分位数 `q_active`。
3. 用 `q_active` 和 `peak_ratio * peak` 一起决定阈值 `tau`。
4. 再把 `tau` 限制在 `[tau_min, tau_max]` 内。
5. 如果当前 core 太小，再主动下调阈值，保证至少覆盖一个最小激活比例。

最后得到：

- `roi_core = 1[roi_soft >= tau]`
- `roi_boundary = normalize(relu(roi_soft * (1 - roi_core)))`

小白理解版：

- `core` 是“最该改、最确定、最硬的一圈”
- `boundary` 是“在 core 外面那一圈还有一点编辑倾向的软边缘”

### 5.5 `_generate_diffedit_roi_batch()`

这个函数把前面的结果真正送到 batch 里。

它会同时缓存几种 ROI：

- `soft_roi_mask`
- `roi_core_mask`
- `roi_boundary_mask`
- `legacy_hard_roi_mask`
- `roi_core_threshold`

也就是说，后面在调试图和可视化里，你不只是能看到最终 mask，还能看到：

- 原始 soft ROI
- 新版 core
- 新版 boundary
- 旧版 `soft > 0.5` 的 legacy hard ROI

这对分析为什么一个样本欠编辑或溢出编辑很有帮助。

### 5.6 `_effective_mask_from_support_state()`

这是 C5H2 真正影响编辑强度的地方。

在 baseline 里，effective mask 更像是：

- `support_state` 和 `soft_roi` 做插值

到了 C5H2，逻辑变成：

1. support memory 主要还是写到 `core`
2. 读出来时，先把 `support_state` 往 `core` 拉一点
3. 再额外加一层衰减的 `boundary`

代码层面可以概括成：

`M_t = clamp(lerp(S_t, roi_core, c_t) + b_t * roi_boundary, 0, 1)`

你可以把它理解为：

- 主体编辑范围靠 `core`
- 边缘过渡靠 `boundary`
- 而且两者都是随时间衰减的

### 5.7 `_adaptive_anchor_mask()`

这一步决定 scheduler 之后怎么把 latent 往 source 轨迹拉回去。

在 C5H2 里，anchor base 不再是简单的 hard ROI，也不是直接 soft ROI，而是：

- `roi_core + a_t * roi_boundary`

也就是说：

- 主体区允许保留编辑
- 边界区只给一层薄薄的、逐步衰减的放松

### 5.8 `_confidence_anchor_roi_mask()`

这一步决定“confidence relax”到底在哪些位置起作用。

它不是全图放松，而是：

- `roi_core + beta * roi_boundary`

这样做的意图很清楚：

- confidence 放松主要仍然发生在 core
- boundary 只作为弱补充

### 5.9 `_extra_step_aux_tensors()`

这个函数不是主机制，但非常值得读。

因为它把每一步调试时真正有用的中间量都导出了：

- `roi_core_mask`
- `soft_roi_mask`
- `roi_boundary_mask`
- `legacy_hard_roi_mask`
- `roi_core_threshold`
- `core_read_weight`
- `boundary_read_weight`
- `boundary_anchor_weight`
- `boundary_confidence_weight`

如果你后面要分析坏例子，这个函数几乎是必读的。

## 6. 第三层：C5H2 继承了什么，不要误以为它从零重写了所有东西

### 6.1 `DyMaskRefactor/support_line/mainline_hardcore.py`

C5H2 是继承 `RefactorSupportC5H0Editor` 的，所以这个文件必须看。

你要重点看两件事：

1. C5H0 的 hard-core 逻辑到底是什么
2. confidence-gated anchor relaxation 的基础公式是什么

这个文件里的关键思想是：

- support memory 尽量用 hard ROI
- anchor 只在“ROI、discrepancy、dynamic mask 一起同意”的地方才局部放松

也就是说，C5H2 不是发明了 confidence relax，而是在它上面加了：

- deterministic ROI
- core / boundary 分解

### 6.2 `DyMaskRefactor/support_line/base.py`

这个文件是 support baseline 的壳。

你读它的目的，是理解 baseline 原本在做什么：

- effective mask 会把 `support_state` 和 `soft ROI` 混合
- anchor 会从 `soft ROI` 逐渐收紧到 `hard ROI`

只有知道 baseline 的默认行为，你才能看清 C5H2 到底改掉了哪里。

### 6.3 `DyMaskRefactor/support_line/masking.py`

这个文件很关键，因为它把 support 这条线最核心的几个钩子统一了：

- support evidence 怎么组成
- support state 怎么读成 effective mask
- scheduler 之后怎么做 source anchor
- 调试图里还能额外导出什么

读法建议：

1. 先看 `_compose_effective_mask_from_aux()`
2. 再看 `_effective_mask_from_support_state()`
3. 再看 `_post_scheduler_step_latents()`

你会发现：

- C5H2 其实不是改了整条 denoise loop
- 它主要是改这些“ROI 如何参与 support / anchor”的钩子

### 6.4 `DyMaskRefactor/support_line/roi.py`

这个文件对应的是“默认 ROI 行为”。

baseline 做法是：

- DiffEdit 直接生成 soft ROI
- 保存 soft ROI
- 再阈值化成 hard ROI

C5H2 之所以要单独写 `mainline_roi.py`，就是因为它不满足于这套默认流程，而是要：

- 先 deterministic
- 再拆成 core 和 boundary

## 7. 第四层：真正的逐步去噪循环在哪里

### 7.1 `DyMaskRefactor/v1_source_prompt_temporal_support.py`

这是理解 C5H2 的另一个必读文件。

它负责的是“support memory 怎么嵌到逐步去噪里”。

你重点抓这几步：

1. 先拿到 source / target 两个分支的噪声预测
2. 聚合 cross-attention
3. 构建 dynamic mask
4. 结合 ROI 得到 support evidence
5. 更新 temporal support state
6. 从 support state 读出 effective mask
7. 用 effective mask 融合 source / target 噪声
8. scheduler step
9. 用 source latent 做 post-step anchoring

这里的核心公式是：

- `S_t = rho * S_{t-1} + (1-rho) * phi_t`

也就是：

- 不是每一步都只看当前瞬时证据
- 而是保留一个“前面几步累计下来的编辑记忆”

### 7.2 `DyMaskRefactor/v1.py`

这个文件里最重要的是 `DynamicMaskBuilder`。

因为 C5H2 **没有重写 dynamic mask 的底层构造方式**，而是继承了这套机制。

当前 raw mask 逻辑是：

- `discrepancy_only`
- `discrepancy_attention`
- `discrepancy_latent`
- `full_dynamic_mask`

其中 `full_dynamic_mask` 形式上是：

- `raw_mask = w_d * discrepancy + w_a * attention - w_l * latent_drift`

再经过：

- smoothing
- sigmoid
- clamp

得到最终 `dynamic_mask`

所以论文或说明里千万不要把 C5H2 写成“重写了 dynamic mask”。更准确的说法是：

- C5H2 保留了 DyMask 的 dynamic mask builder，只修改 ROI 的组织方式，以及 ROI 如何进入 support read/write 和 source anchoring。

## 8. 第五层：指标是怎么定义的

### `DyMaskRefactor/metric_runtime.py`

这个文件是评价部分的主入口。

你至少要看清楚下面几个别名：

- `clip_score_edit_part = clip_similarity_target_image_edit_part`
- `outside_psnr = psnr_unedit_part`
- `outside_lpips = lpips_unedit_part`

`locality_ratio` 的实现也在这里，逻辑是：

- 先算 source 和 edited 之间的 spatial LPIPS 变化图
- 再看变化量里，落在 GT mask 内的占比

也就是说：

- 数值越高，表示“变化更集中在该改的区域里”

`structure_distance` 用的是 DINO self-similarity 的 MSE。

如果你后面要写论文里的指标定义，或者要核对和旧实验是不是同一套评测，这个文件是最终依据。

## 9. legacy 版怎么对应

如果你要查“最早实验到底用的是哪份代码”，看下面两个文件：

- `DyMask/run_v1_source_prompt_source_anchored_support_c5h2.py`
- `DyMask/v1_source_prompt_source_anchored_support_c5h2.py`

对应关系可以这么记：

- legacy `run_*.py`
  - 负责旧版 CLI、run 目录、logger、dataset、metric runner 组装
- legacy `v1_source_prompt_source_anchored_support_c5h2.py`
  - 负责旧版 C5H2 本体逻辑
- refactor `support_line/execution.py`
  - 相当于把旧版 run 逻辑拆干净
- refactor `support_line/mainline_roi.py`
  - 相当于把旧版 C5H2 算法主逻辑拆干净

如果你的目标只是“学机制”，直接读 refactor。

如果你的目标是“追溯历史实验和完全复现旧跑法”，再回 legacy。

## 10. 最省时间的阅读路线

### 路线 A：只想先弄懂机制

1. `DyMaskRefactor/support_line/ARCHITECTURE.md`
2. `DyMaskRefactor/support_line/mainline_roi.py`
3. `DyMaskRefactor/support_line/mainline_hardcore.py`
4. `DyMaskRefactor/support_line/masking.py`
5. `DyMaskRefactor/v1_source_prompt_temporal_support.py`
6. `DyMaskRefactor/metric_runtime.py`

### 路线 B：想自己改代码继续做新版本

1. `DyMaskRefactor/support_line/ARCHITECTURE.md`
2. `DyMaskRefactor/support_line/registry.py`
3. `DyMaskRefactor/support_line/specs.py`
4. `DyMaskRefactor/support_line/configuration.py`
5. `DyMaskRefactor/support_line/execution.py`
6. `DyMaskRefactor/support_line/mainline_roi.py`
7. `DyMaskRefactor/support_line/mainline_hardcore.py`
8. `DyMaskRefactor/support_line/base.py`
9. `DyMaskRefactor/support_line/masking.py`
10. `DyMaskRefactor/v1_source_prompt_temporal_support.py`

### 路线 C：想核对旧实验

1. `DyMask/run_v1_source_prompt_source_anchored_support_c5h2.py`
2. `DyMask/v1_source_prompt_source_anchored_support_c5h2.py`
3. `DyMaskRefactor/support_line/mainline_roi.py`

## 11. 看懂 C5H2 后，你应该能回答这 4 个问题

如果你已经读明白了，理论上应该能自己回答：

1. 为什么 C5H2 要把 DiffEdit soft ROI 做成 deterministic？
2. 为什么 support memory 写 core，而不是直接写 whole soft ROI？
3. 为什么 readout 和 anchor 又不能只看 hard core，还要加 boundary？
4. 为什么 confidence relax 不能全图放开，而要被 ROI 和 consistency 一起约束？

如果这 4 个问题你已经能用自己的话讲清楚，那基本就算真正读懂 C5H2 了。

## 12. 一句话总结

C5H2 的本质，不是“换了一个全新的 diffusion 编辑框架”，而是：

- 在既有 `source-prompt + temporal support + source anchoring` 框架中，
- 把 DiffEdit ROI 从“随机、直接拿来用的软图”改成“确定性的、可分解的 core-boundary 先验”，
- 再把这个先验更精细地接到 support write、mask readout 和 anchor relaxation 上。

这也是为什么它很适合写成一篇方法论文里的一个清晰模块。
