# Support 主线 C1 到 C5 记录

## 1. 这条线是在做什么

这条线的目标，是在 `source-anchored support` 框架里，尽量同时做到两件事：

1. 该改的地方改得更到位，减少欠编辑。
2. 不该改的地方尽量别被带脏，保持 locality。

这条线里经常出现的几个词，可以先这样理解：

- `soft ROI`：一个模糊的“应该改哪里”的热力图，不是只有 0 和 1。
- `hard ROI`：把 `soft ROI` 二值化之后的区域图，更硬、更保守。
- `support memory`：逐步去噪时累积出来的“哪里值得继续编辑”的记忆。
- `anchor`：每一步结束后，把不该乱跑的 latent 往 source 轨迹拉回去的保护机制。
- `dynamic mask`：当前步里，根据 source/target 差异、注意力等信息得到的即时编辑强度图。

一句话概括这条线的演化：

- `C1-C4` 是一条连续叠加的主线，核心思路是改 support 写入和 anchor 时序。
- `C5` 不是在 `C4` 上继续叠，而是回到 baseline 重新开了一条支线，改成“只在局部可信区域放松 anchor”。

## 2. 结构图

```text
baseline: source_anchored_support_adaptive
├─ C1: soft-aware support memory
│  └─ C2: delayed anchor
│     └─ C3: delayed soft support
│        └─ C4: late ROI floor
└─ C5: confidence-gated local anchor relaxation

分析分叉:
- C2-only: 只测 delayed anchor，不继承 C1
- C3-only: 只测 delayed soft support，不继承 C1/C2
- C4-only: 只测 late ROI floor，不继承 C1/C2/C3
```

之所以后来专门做 `only` 分叉，是因为我们中途发现：如果前一版本身有副作用，后一版直接叠上去，很难看出到底是谁在起作用。

## 3. baseline 是什么

基线实现：

- 代码：[DyMask/v1_source_prompt_source_anchored_support.py](DyMask/v1_source_prompt_source_anchored_support.py)
- runner：[DyMask/run_v1_source_prompt_source_anchored_support.py](DyMask/run_v1_source_prompt_source_anchored_support.py)

baseline 的核心机制：

- 用 DiffEdit 先生成 `soft ROI`，再阈值化得到 `hard ROI`。
- support memory 用 `soft ROI` 和累积 support 做一个前松后紧的融合。
- 每一步 scheduler 之后，再用一个从 `soft ROI -> hard ROI` 的 anchor schedule，把外部 latent 往 source 轨迹拉回去。

直观理解：

- 前期让编辑区域稍微宽一点，别太早把变化压死。
- 后期再逐渐收紧，防止越改越脏。

代表结果：

- `full700` baseline: `edit_clip 22.219`, `outside_lpips 0.03499`, `outside_psnr 27.033`, `locality 0.55217`
- run: `scratch_source_anchor_runs/sp_anchor_source_anchored_support_adaptive_current_full_700_50x50/v1_source_prompt_source_anchored_support_20260411-0047`

## 4. C1 做了什么

实现：

- 代码：[DyMask/v1_source_prompt_source_anchored_support_c1.py](DyMask/v1_source_prompt_source_anchored_support_c1.py)
- runner：[DyMask/run_v1_source_prompt_source_anchored_support_c1.py](DyMask/run_v1_source_prompt_source_anchored_support_c1.py)

核心改动：

- baseline 里，support memory 的写入更偏向 `hard ROI`。
- `C1` 让 support memory 的写入区域也能“看到”一部分 `soft ROI`。
- 公式直观上是：把原来只在硬边界内记忆编辑，改成“硬边界 + 一点软边界”。

想解决的问题：

- 有些欠编辑样本里，真正该改的边界比较虚，`hard ROI` 太窄，support memory 记不进去，后面就越跑越保守。

小白版理解：

- 原来像是老师只允许你在黑线框内上色。
- `C1` 变成允许你稍微涂到黑线边缘外的灰区里，免得边界附近一直上不满。

主线结果：

| 数据集 | edit_clip | outside_lpips | outside_psnr | locality | structure_unedit |
| --- | ---: | ---: | ---: | ---: | ---: |
| underedit93 | 21.169 | 0.03392 | 27.455 | 0.59081 | 0.002768 |
| random140 | 22.372 | 0.03412 | 28.578 | 0.57775 | 0.004014 |

代表 run：

- `scratch_source_anchor_runs/sp_anchor_source_anchored_support_c1_underedit93_50x50/v1_source_prompt_source_anchored_support_c1_20260411-0837`
- `scratch_source_anchor_runs/sp_anchor_source_anchored_support_c1_random_140_50x50/v1_source_prompt_source_anchored_support_c1_20260411-0849`

我们学到的东西：

- `C1` 的确能让编辑更敢动一点。
- 但它的问题也很明显：因为 support memory 本身就更“软”了，后面容易把编辑趋势扩到 ROI 边缘外，属于典型的“救欠编辑，但开始更脏”。
- 这也解释了为什么后面我们开始关注“不要只靠扩大 support 写入范围”。

## 5. C2 做了什么

实现：

- 代码：[DyMask/v1_source_prompt_source_anchored_support_c2.py](DyMask/v1_source_prompt_source_anchored_support_c2.py)
- runner：[DyMask/run_v1_source_prompt_source_anchored_support_c2.py](DyMask/run_v1_source_prompt_source_anchored_support_c2.py)

核心改动：

- `C2` 在 `C1` 基础上，把 source anchor 改成延迟启用。
- 前一段步数里，anchor 基本不工作；中段再平滑打开；后段再回到原来的自适应 anchor schedule。

想解决的问题：

- 很多欠编辑不是因为模型不会改，而是它一开始刚想改，就立刻被 anchor 拉回 source 了。
- 所以 `C2` 的想法是：先别急着把它拉回来，给它一点起势空间。

小白版理解：

- 原来是你每走一步，就有人马上把你拽回原地。
- `C2` 变成：前半段先让你往前走，等方向稳定了，再慢慢开始纠偏。

主线结果：

| 数据集 | edit_clip | outside_lpips | outside_psnr | locality | structure_unedit |
| --- | ---: | ---: | ---: | ---: | ---: |
| underedit93 | 21.546 | 0.03232 | 27.685 | 0.59949 | 0.002937 |
| random140 | 22.460 | 0.03198 | 28.303 | 0.59011 | 0.003756 |
| full700 | 22.297 | 0.03513 | 26.984 | 0.55321 | 0.003708 |

代表 run：

- `scratch_source_anchor_runs/sp_anchor_source_anchored_support_c2_underedit93_50x50/v1_source_prompt_source_anchored_support_c2_20260411-0927`
- `scratch_source_anchor_runs/sp_anchor_source_anchored_support_c2_random_140_50x50/v1_source_prompt_source_anchored_support_c2_20260411-0927`
- `scratch_source_anchor_runs/sp_anchor_source_anchored_support_c2_full_700_50x50/v1_source_prompt_source_anchored_support_c2_20260411-2026`

后来的隔离分叉：

- 代码：[DyMask/v1_source_prompt_source_anchored_support_c2_only.py](DyMask/v1_source_prompt_source_anchored_support_c2_only.py)
- 目的：把 `C1` 拿掉，只看 delayed anchor 自己有没有价值。

`C2-only` 结果说明：

- delayed anchor 本身是有帮助的，不完全依赖 `C1` 才成立。
- 这一步让我们确认：问题不只是 ROI 写入范围，还有“什么时候开始拉回 source”。

## 6. C3 做了什么

实现：

- 代码：[DyMask/v1_source_prompt_source_anchored_support_c3.py](DyMask/v1_source_prompt_source_anchored_support_c3.py)
- runner：[DyMask/run_v1_source_prompt_source_anchored_support_c3.py](DyMask/run_v1_source_prompt_source_anchored_support_c3.py)

核心改动：

- `C3` 在 `C2` 基础上，又把 support memory 里的 soft ROI 混合也延迟启用。
- 也就是说，不只是 anchor 延迟，连“软边界 support 写入”本身也不要一开始就上。

想解决的问题：

- `C1` 的一个问题是，软 support 虽然能救欠编辑，但太早放进来，会把早期还不稳定的误差也记住。
- `C3` 想做的是：先靠硬一点的证据站稳，再慢慢引入软边界扩展。

小白版理解：

- 不是一上来就允许在模糊边界里自由涂色。
- 先把主体位置画稳了，再慢慢给边缘补柔和过渡。

主线结果：

| 数据集 | edit_clip | outside_lpips | outside_psnr | locality | structure_unedit |
| --- | ---: | ---: | ---: | ---: | ---: |
| underedit93 | 21.582 | 0.03286 | 27.597 | 0.60132 | 0.002860 |
| random140 | 22.500 | 0.03178 | 28.245 | 0.58932 | 0.003620 |

代表 run：

- `scratch_source_anchor_runs/sp_anchor_source_anchored_support_c3_underedit93_50x50/v1_source_prompt_source_anchored_support_c3_20260411-1548`
- `scratch_source_anchor_runs/sp_anchor_source_anchored_support_c3_random_140_50x50/v1_source_prompt_source_anchored_support_c3_20260411-1548`

后来的隔离分叉：

- 代码：[DyMask/v1_source_prompt_source_anchored_support_c3_only.py](DyMask/v1_source_prompt_source_anchored_support_c3_only.py)
- 目的：只测 delayed soft support 自身值不值得保留。

我们学到的东西：

- `C3` 相比 `C2` 是小步推进，不是质变。
- 它说明“延迟把软 support 放进记忆”这件事方向是对的，但单靠它不足以根治欠编辑。

## 7. C4 做了什么

实现：

- 代码：[DyMask/v1_source_prompt_source_anchored_support_c4.py](DyMask/v1_source_prompt_source_anchored_support_c4.py)
- runner：[DyMask/run_v1_source_prompt_source_anchored_support_c4.py](DyMask/run_v1_source_prompt_source_anchored_support_c4.py)

核心改动：

- `C4` 在 `C3` 基础上，引入一个 late ROI floor。
- 做法是：在后期步数里，给 support mask 加一个最小保底值，避免动态证据太弱时，mask 直接塌成接近 0。

想解决的问题：

- 前几版都暴露出同一个现象：有些样本到了后期，dynamic mask 越来越弱，最后编辑 drive 几乎消失，于是欠编辑。
- `C4` 想用一个“后期保底油门”解决这个问题。

小白版理解：

- 车不是完全没油门，而是临近终点时油门越来越小，最后爬不上去。
- `C4` 的做法就是在后段偷偷垫一块最低油门，防止彻底熄火。

主线结果：

| 数据集 | edit_clip | outside_lpips | outside_psnr | locality | structure_unedit |
| --- | ---: | ---: | ---: | ---: | ---: |
| underedit93 | 21.718 | 0.03331 | 27.474 | 0.59365 | 0.002950 |
| random140 | 22.361 | 0.03422 | 28.332 | 0.58274 | 0.003942 |

代表 run：

- `scratch_source_anchor_runs/sp_anchor_source_anchored_support_c4_underedit93_50x50/v1_source_prompt_source_anchored_support_c4_20260411-1620`
- `scratch_source_anchor_runs/sp_anchor_source_anchored_support_c4_random_140_50x50/v1_source_prompt_source_anchored_support_c4_20260411-1619`

后来的隔离分叉：

- 代码：[DyMask/v1_source_prompt_source_anchored_support_c4_only.py](DyMask/v1_source_prompt_source_anchored_support_c4_only.py)
- 目的：只看 late ROI floor 自己的边际价值。

我们学到的东西：

- `C4` 对 underedit 的确有一点帮助，但代价也开始更明显。
- 本质上，它还是在给更大的 edit drive，属于“全局补油门”。
- 这让我们意识到：再沿着 `C1-C4` 这条“全局放松/全局补强”的思路往下叠，可能很难同时兼顾干净度。

## 8. 为什么会从 C1-C4 切到 C5

到 `C4` 为止，我们已经得到一个很清楚的经验：

- 只要是改 support 写入范围、延后 global anchor、或者给后期保底强度，本质上都在增加整体 edit drive。
- 这样通常能把 `edit_clip` 拉高。
- 但它也很容易让本来不该动的背景、边界、纹理一起被带着动。

所以 `C5` 的思路变了：

- 不再继续扩大“哪里都能改”的能力。
- 而是尽量只在“局部证据很强、而且确实像应该改的地方”放松 anchor。

这就是从“全局加油门”转到“局部松刹车”。

## 9. C5 做了什么

实现：

- 代码：[DyMask/v1_source_prompt_source_anchored_support_c5.py](DyMask/v1_source_prompt_source_anchored_support_c5.py)
- runner：[DyMask/run_v1_source_prompt_source_anchored_support_c5.py](DyMask/run_v1_source_prompt_source_anchored_support_c5.py)

最重要的一点：

- `C5` 不是继承 `C4`。
- 它是直接从 baseline `[DyMask/v1_source_prompt_source_anchored_support.py](DyMask/v1_source_prompt_source_anchored_support.py)` 分叉出去重新设计的。

核心改动：

- 先保留 baseline 的 adaptive support 和 adaptive anchor。
- 再额外构造一个 `confidence`，只在局部可信区域放松 anchor。
- `confidence` 由三部分共同决定：
  - `roi_soft`：这个地方本来就应该属于编辑区域。
  - `sqrt(discrepancy * dynamic_mask)`：source/target 差异在这里确实强，而且当前步也确实在想改这里。
  - `1 - |mask - dynamic_mask|`：support 累积状态和当前即时证据彼此一致，不是冲突状态。

然后用这个 `confidence` 去把 anchor 从 `A_t` 松到 `A'_t`：

- 不是把整个背景保护都取消。
- 只是局部地、按强弱地、前强后弱地松一部分。

小白版理解：

- 以前的几版更像是把整台车的油门往上踩。
- `C5` 更像是在弯道里，只给真正该转向的轮子稍微松一点刹车。

原始 C5 结果：

| 数据集 | edit_clip | outside_lpips | outside_psnr | locality | structure_unedit |
| --- | ---: | ---: | ---: | ---: | ---: |
| underedit93 | 21.613 | 0.03238 | 27.444 | 0.61486 | 0.002611 |
| random140 | 22.567 | 0.03213 | 28.195 | 0.58713 | 0.003886 |
| full700 | 22.259 | 0.03492 | 27.061 | 0.55217 | 0.003578 |

代表 run：

- `scratch_source_anchor_runs/sp_anchor_source_anchored_support_c5_underedit93_50x50/v1_source_prompt_source_anchored_support_c5_20260411-2332`
- `scratch_source_anchor_runs/sp_anchor_source_anchored_support_c5_random_140_50x50/v1_source_prompt_source_anchored_support_c5_20260411-2332`
- `scratch_source_anchor_runs/sp_anchor_source_anchored_support_c5_current_full_700_50x50_b4/v1_source_prompt_source_anchored_support_c5_20260412-0221`

这一步我们学到的东西：

- `C5` 是这条线里的一个重要转向点。
- 它不再靠“让 support 更大”来救欠编辑，而是靠“少拉错地方”来给正确区域释放编辑空间。
- 这比 `C1-C4` 的思路更细，也更像一条可以继续深化的主线。

## 10. C5 后来为什么又要重新解释

后面我们发现一个非常关键的问题：

- `C5` 里使用的 `soft ROI`，实际效果并不像我们以为的那样“真的是连续软图”。
- 在真实修正成 `true soft ROI` 之后，整条 `C5` 线明显变保守了。

修正后的 `C5` 结果：

| 数据集 | edit_clip | outside_lpips | outside_psnr | locality | structure_unedit |
| --- | ---: | ---: | ---: | ---: | ---: |
| underedit93 | 19.953 | 0.02460 | 29.334 | 0.57187 | 0.001691 |
| full700 | 21.641 | 0.02642 | 28.790 | 0.54070 | 0.002140 |

修正后的代表 run：

- `scratch_source_anchor_runs/sp_anchor_source_anchored_support_c5_softroi_fix_underedit93_50x50_b4/v1_source_prompt_source_anchored_support_c5_20260415-1035`
- `scratch_source_anchor_runs/sp_anchor_source_anchored_support_c5_softroi_fix_current_full_700_50x50_b8/v1_source_prompt_source_anchored_support_c5_20260415-0948`

这件事说明：

- 原始 `C5` 的一部分“能打”，其实来自控制图幅度被放大了。
- 一旦 `soft ROI` 真正变软，`C5` 里那些依赖它的控制项会一起变保守。
- 所以如果后面要写论文，`C5` 应该优先以修正后的 true-soft 版本为准；原始 `C5` 更像一次重要但带实现偏差的探索记录。

## 11. 从 C1 到 C5，我们到底做了什么

如果用一句话总结这整段探索：

- `C1-C4` 在尝试回答：“怎么让模型别那么保守，别老欠编辑？”
- `C5` 在尝试回答：“不去全局放大 edit drive，而是只在可信局部减少 source anchor 压制，能不能更稳地救欠编辑？”

如果再压缩成更简短的五句话：

1. `C1`：让 support memory 也利用软 ROI，扩大可写入区域。
2. `C2`：把 anchor 延后，避免一开始就把编辑压死。
3. `C3`：把 soft support 也延后，减少早期错误扩散。
4. `C4`：给后期加 ROI floor，防止 edit drive 彻底掉光。
5. `C5`：回到 baseline，不再继续全局加压，而是改成局部 confidence-gated anchor relaxation。

## 12. 当前该怎么引用这份记录

如果只是回顾探索过程：

- 可以把 `C1 -> C4` 看成一条“逐步增加编辑驱动、逐步修时序”的主线。
- 可以把 `C5` 看成从 baseline 重新开出来的“局部可信放松”新主线。

如果是准备写论文：

- `C1-C4` 更适合作为方法演化和失败经验。
- `C5` 才是更值得继续深化的结构性方案。
- 但引用 `C5` 时，要明确区分“原始 C5”和“true-soft 修正后的 C5”。

## 13. 相关文件

- baseline: [DyMask/v1_source_prompt_source_anchored_support.py](DyMask/v1_source_prompt_source_anchored_support.py)
- C1: [DyMask/v1_source_prompt_source_anchored_support_c1.py](DyMask/v1_source_prompt_source_anchored_support_c1.py)
- C2: [DyMask/v1_source_prompt_source_anchored_support_c2.py](DyMask/v1_source_prompt_source_anchored_support_c2.py)
- C2-only: [DyMask/v1_source_prompt_source_anchored_support_c2_only.py](DyMask/v1_source_prompt_source_anchored_support_c2_only.py)
- C3: [DyMask/v1_source_prompt_source_anchored_support_c3.py](DyMask/v1_source_prompt_source_anchored_support_c3.py)
- C3-only: [DyMask/v1_source_prompt_source_anchored_support_c3_only.py](DyMask/v1_source_prompt_source_anchored_support_c3_only.py)
- C4: [DyMask/v1_source_prompt_source_anchored_support_c4.py](DyMask/v1_source_prompt_source_anchored_support_c4.py)
- C4-only: [DyMask/v1_source_prompt_source_anchored_support_c4_only.py](DyMask/v1_source_prompt_source_anchored_support_c4_only.py)
- C5: [DyMask/v1_source_prompt_source_anchored_support_c5.py](DyMask/v1_source_prompt_source_anchored_support_c5.py)
- C1 log: [log_source_anchored_support_c1.md](log_source_anchored_support_c1.md)
- C2 log: [log_source_anchored_support_c2.md](log_source_anchored_support_c2.md)
- C3 log: [log_source_anchored_support_c3.md](log_source_anchored_support_c3.md)
- C4 log: [log_source_anchored_support_c4.md](log_source_anchored_support_c4.md)
- C5 log: [log_source_anchored_support_c5.md](log_source_anchored_support_c5.md)
