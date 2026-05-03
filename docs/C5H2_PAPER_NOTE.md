# C5H2 方法说明与论文写作草稿

## 1. 这份文档是干什么的

这份文档的目标不是单纯解释代码，而是把 `C5H2` 这套方案整理成一份接近论文方法小节的说明。你可以直接拿它去写：

- 方法章节
- 实验设置章节
- 指标定义章节
- 补充材料里的实现细节

需要先说明一点：

- `C5H2` 不是当前仓库里“最后一个版本”，后面还有 `C5H3-C5H4`。
- 但 `C5H2` 是这条主线里非常适合写论文的一版，因为它的新增机制比较集中，也比较容易讲清楚。

一句话概括 C5H2：

- 它把 `source-anchored temporal support` 这条编辑框架里的 ROI 先验，从“随机生成、直接拿来用的 soft ROI”，改成了“确定性的 DiffEdit soft ROI + adaptive hard core + normalized soft boundary”，并分别接到 support 写入、mask 读出和 source anchoring 中。

## 2. 问题设定

我们考虑文本引导的真实图像编辑问题。

输入为：

- 源图像 `I_s`
- 源文本 `p_s`
- 目标文本 `p_t`

输出为：

- 编辑后的图像 `I_hat`

目标是同时满足两件事：

1. 在该改的区域内，`I_hat` 要尽量符合目标语义 `p_t`。
2. 在不该改的区域内，`I_hat` 要尽量保持与源图像 `I_s` 一致。

如果用一句很直白的话说：

- 我们既想“改对”，又想“别带脏背景”。

## 3. C5H2 所在的大框架

C5H2 不是独立于 DyMask 的全新编辑系统，它建立在下面这条主线之上：

1. 先用 DDIM inversion 把源图像反演到扩散模型的 latent 轨迹。
2. 在每一个去噪步里，同时跑 source prompt 分支和 target prompt 分支。
3. 用两分支差异、cross-attention 和 latent drift 构造 dynamic mask。
4. 用 temporal support 在时间维度上累计“哪里值得持续编辑”的记忆。
5. 用 effective mask 融合 source / target 两个噪声预测。
6. 每一步 scheduler 之后，再用 source latent 做 background/source anchoring，防止背景漂移。

所以 C5H2 主要改的不是：

- inversion
- 双分支预测
- dynamic mask 的底层计算

它主要改的是：

- **ROI 先验本身如何生成**
- **ROI 如何进入 support memory**
- **ROI 如何进入 effective mask**
- **ROI 如何进入 source anchoring**

## 4. 为什么需要 C5H2

在 C5H2 之前，baseline support 版本已经能工作，但存在三个明显问题。

### 4.1 问题一：soft ROI 本身带随机性

原来的 DiffEdit soft ROI 是运行时生成的。如果不做额外处理：

- 同一张图多跑几次，soft ROI 可能会有波动
- 后面的 support memory 和 anchor 都会跟着波动
- 结果不稳定，也不利于分析坏例子

### 4.2 问题二：直接拿整个 soft ROI 去参与 support，容易把边界搞脏

soft ROI 的优点是柔和，但缺点也明显：

- 它会把“高置信编辑区”和“边缘模糊区”混在一起
- 如果 support memory 直接写到整张 soft ROI，上下文很容易向边缘外扩散

简单说：

- 该硬的地方不够硬
- 该软的地方又太早被放进主驱动力里

### 4.3 问题三：只用 hard ROI 又会过于保守

反过来，如果你只拿阈值化后的 hard ROI：

- 轮廓会太硬
- 边界过渡很差
- 一些真实该改、但响应比较弱的区域容易直接被裁掉

于是就出现了一个典型矛盾：

- 用全 soft ROI，容易编辑外溢
- 用全 hard ROI，容易欠编辑

C5H2 的核心目标，就是在这两者之间找到一个更稳定的折中。

## 5. 符号与记号

下面统一记号。

- `I_s`：源图像
- `p_s`：源文本
- `p_t`：目标文本
- `z_t^src`：源图像经过 DDIM inversion 得到的第 `t` 步 latent
- `z_t`：当前编辑分支第 `t` 步 latent
- `eps_t^src`：source prompt 分支预测的噪声
- `eps_t^tar`：target prompt 分支预测的噪声
- `R_soft`：DiffEdit 生成的 soft ROI
- `R_core`：从 `R_soft` 中提取出来的 hard core
- `R_bnd`：`R_soft` 在 core 外的 normalized boundary
- `D_t`：source / target 两分支差异得到的 discrepancy map
- `A_t`：cross-attention 聚合得到的 attention map
- `L_t`：latent drift map
- `M_t^dyn`：dynamic mask
- `S_t`：temporal support state
- `M_t`：effective mask
- `B_t`：source anchoring 的 base anchor mask
- `B_t'`：经过 confidence relax 后的最终 anchor mask

这里需要特别说明：

- 在本代码实现里，anchor mask 越接近 `1`，表示越保留编辑后的 latent。
- 越接近 `0`，表示越强地拉回 source latent。

## 6. 整体流程

### 6.1 输入与反演

给定 `I_s, p_s, p_t`，我们先对 `I_s` 做 DDIM inversion，得到：

- 初始噪声 latent `z_T^src`
- 源图像对应的整条 latent 轨迹 `{z_t^src}`

这样做的意义是：

- 后面每一步编辑时，我们都能拿到“如果不编辑，source 本来应该走到哪”
- 这为 source anchoring 提供了参照轨迹

### 6.2 生成 ROI 先验

我们不直接手工指定 ROI，而是使用 DiffEdit 生成语义相关的 soft ROI：

`R_soft = DiffEdit(I_s, p_s, p_t)`

但 C5H2 不是简单调用就结束，而是先做两件额外处理：

1. 对每个样本构造稳定随机种子，使 `R_soft` 对同一样本是确定的。
2. 将结果缓存到磁盘，避免重复生成与重复波动。

### 6.3 逐步去噪编辑

对于每一个扩散步 `t`，C5H2 执行：

1. source 分支预测 `eps_t^src`
2. target 分支预测 `eps_t^tar`
3. 聚合 cross-attention 得到 `A_t`
4. 结合 discrepancy、attention、latent drift 构造 `M_t^dyn`
5. 用 `R_core` 更新 temporal support
6. 用 `R_core + R_bnd` 读出 effective mask `M_t`
7. 用 `M_t` 融合 source/target 噪声
8. scheduler 更新 latent
9. 用 boundary-aware source anchoring 对背景和不可信区域做回拉

### 6.4 解码输出

当全部编辑步完成后，将最终 latent 解码得到编辑结果 `I_hat`。

## 7. C5H2 的四个关键模块

### 7.1 模块一：确定性的 DiffEdit soft ROI

### 动机

DiffEdit 给出的 soft ROI 对语义是有帮助的，但如果每次运行都带随机波动，那么：

- 实验可重复性会变差
- case-level 诊断会变困难

### 做法

对于每个样本 `i`，C5H2 用样本本身的信息构造稳定随机种子：

`s_i = hash(row_index_i, p_s^i, p_t^i, seed_offset)`

然后用这个 `s_i` 去生成 ROI：

`R_soft^i = DiffEdit(I_s^i, p_s^i, p_t^i ; s_i)`

并把它缓存到磁盘。缓存路径还会绑定：

- model id
- image size
- edit steps
- DiffEdit 配置

这样做的结果是：

- 同一张图、同一套配置、同一个 seed offset，会得到同一个 soft ROI

### 意义

这一步本身不直接提升编辑质量，但它显著提升了：

- 实验稳定性
- 分析可解释性
- 复现性

对于论文来说，这一点很重要，因为它减少了“ROI 先验本身的随机噪声”。

### 7.2 模块二：core-boundary 分解

这是 C5H2 最核心的算法改动。

### 7.2.1 从 soft ROI 中提取 core

记 `R_soft(x)` 为像素位置 `x` 处的 soft ROI 值。先取峰值：

`peak = max_x R_soft(x)`

只在激活足够明显的区域内计算分位数。设激活下界为 `a_floor`，则有效激活集为：

`Omega_act = { x | R_soft(x) >= a_floor }`

在这个集合上计算分位数：

`q_act = Quantile({R_soft(x) | x in Omega_act}, q)`

然后定义阈值：

`tau = clip(max(q_act, gamma * peak), tau_min, tau_max)`

其中：

- `q` 对应 `roi_core_quantile`
- `gamma` 对应 `roi_core_peak_ratio`
- `tau_min` 对应 `roi_core_threshold_min`
- `tau_max` 对应 `roi_core_threshold_max`

于是 hard core 定义为：

`R_core(x) = 1[ R_soft(x) >= tau ]`

### 7.2.2 最小激活面积保护

如果当前 `R_core` 太小，说明阈值太激进，会造成后续欠编辑。

因此 C5H2 还加入了最小激活比例约束。若：

`|R_core| < eta * |Omega_act|`

则进一步降低 `tau`，直到 `R_core` 至少覆盖一个最小激活比例。

这里：

- `eta` 对应 `roi_core_min_active_ratio`

### 7.2.3 定义 boundary

有了 core 后，soft ROI 中剩余的那部分就作为 boundary：

`R_bnd_raw(x) = relu(R_soft(x) * (1 - R_core(x)))`

然后按峰值归一化：

`R_bnd(x) = R_bnd_raw(x) / max_x R_bnd_raw(x)`

如果边界完全为空，则直接置零。

### 为什么要这样拆

你可以把这个分解理解成：

- `R_core`：确定性高、适合做“主编辑驱动力”
- `R_bnd`：确定性低一些、适合做“边界补充和柔和过渡”

这比“整张 soft ROI 一把梭”要细，也比“单个 hard ROI 二值图”更灵活。

### 7.3 模块三：temporal support 只写 core，读出时再带 boundary

### 7.3.1 dynamic mask 的来源

C5H2 没有重写底层 dynamic mask builder，而是继承 DyMask 的这套构造。

在 `full_dynamic_mask` 设定下，raw mask 可以写成：

`U_t = w_d * D_t + w_a * A_t - w_l * L_t`

其中：

- `D_t` 是 discrepancy
- `A_t` 是 attention map
- `L_t` 是 latent drift
- `w_d, w_a, w_l` 是对应权重

然后再经过：

1. optional smoothing
2. sigmoid thresholding
3. clamp

得到最终的 dynamic mask：

`M_t^dyn = clamp(sigmoid((smooth(U_t) - theta) * T), m_min, m_max)`

这里的具体实现继承自 `DyMaskRefactor/v1.py`。

### 7.3.2 support memory 的写入

在普通 temporal support 里，support evidence 一般可以写成：

`phi_t = ROI * M_t^dyn`

而在 C5H2 里，support 写入只使用 core：

`phi_t = R_core * M_t^dyn`

然后时间上递推：

`S_t = rho * S_{t-1} + (1-rho) * phi_t`

初始条件为：

`S_0 = phi_0`

### 为什么只写 core

因为 support memory 是会被时间累积的。如果一开始就把整张 soft ROI 都写进去，那么：

- 模糊边界里的弱证据也会被不断积累
- 编辑趋势容易向外扩散

只写 core 的好处是：

- 记忆更稳定
- 主驱动力更集中

### 7.3.3 effective mask 的读出

虽然 support 只写 core，但真正用于融合 source / target 噪声的 effective mask 不能只看 core，否则会太硬、太保守。

于是 C5H2 定义：

`M_t = clamp(lerp(S_t, R_core, c_t) + b_t * R_bnd, 0, 1)`

其中：

- `c_t` 是 core read 权重，随时间余弦衰减
- `b_t` 是 boundary read 权重，随时间余弦衰减

更直白地说：

- 主体编辑仍然由 `S_t` 和 `R_core` 决定
- 边界由一层较弱的 `R_bnd` 补上
- 而且这种补充在后期会逐渐减弱

### 7.3.4 噪声融合

得到 effective mask 后，编辑噪声按如下方式融合：

`eps_t = eps_t^src + M_t * (eps_t^tar - eps_t^src)`

这一步的意思很简单：

- 如果 `M_t(x)` 接近 0，当前位置更接近 source 分支
- 如果 `M_t(x)` 接近 1，当前位置更接近 target 分支

### 7.4 模块四：boundary-aware source anchoring

source anchoring 是这条线里抑制背景漂移的关键。

### 7.4.1 基础 anchor mask

C5H2 不是直接拿 `R_core` 做 anchor，也不是拿整张 `R_soft`，而是定义：

`B_t = clamp(R_core + a_t * R_bnd, 0, 1)`

其中：

- `a_t` 是 boundary anchor 权重，随时间余弦衰减

这意味着：

- core 区域默认允许编辑保留
- boundary 区域也给一点点保留编辑的空间
- 但这个空间会逐渐缩小

### 7.4.2 confidence-gated relax

光有 `B_t` 还不够，因为有些位置虽然在 ROI 里，但模型当步并没有足够证据支持编辑。

因此 C5H2 还引入 confidence-gated relax。先定义：

`E_t = sqrt(D_t * M_t^dyn)`

表示编辑证据强度。

再定义一致性项：

`C_t_cons = 1 - |M_t - M_t^dyn|`

表示 support 读出的 mask 与当前 dynamic mask 是否一致。

然后构造 confidence ROI：

`R_t_conf = clamp(R_core + beta * R_bnd, 0, 1)`

其中 `beta` 对应 `boundary_confidence_weight`。

最终 confidence 为：

`Conf_t = R_t_conf * E_t * C_t_cons`

再乘以一个时间衰减的 relax strength `alpha_t`：

`R_t = alpha_t * Conf_t`

于是得到最终 anchor mask：

`B_t' = lerp(B_t, 1, R_t)`

### 7.4.3 post-step source anchoring

scheduler 更新出当前步编辑 latent `z_{t-1}^{edit}` 后，再与 source 轨迹上的 latent 做融合：

`z_{t-1} = B_t' * z_{t-1}^{edit} + (1 - B_t') * z_{t-1}^{src}`

这里非常关键的一点是：

- `B_t'` 越大，当前位置越保留编辑结果
- `B_t'` 越小，当前位置越被拉回 source latent

### 为什么这一步有效

如果没有 confidence gating，只按 ROI 放松 anchor：

- 边界模糊区域也可能被过早放开
- 背景更容易漂移

如果没有 boundary，只按 core 放松：

- 则又容易回到过硬、欠编辑的状态

所以 C5H2 不是单纯“放松 anchor”，而是：

- 在 core 主导下，用 boundary 做少量补充
- 同时要求 discrepancy、dynamic mask 和 effective mask 三者基本一致，才允许放松

## 8. 从小白角度怎么理解 C5H2

如果不用公式，只讲直觉，C5H2 可以理解成下面这件事。

先把编辑区域分成两圈：

- 里面一圈是“八成以上确定该改的地方”，这叫 `core`
- 外面一圈是“可能也该改，但没那么确定的地方”，这叫 `boundary`

然后：

1. 记忆系统主要记里圈，不记外圈
2. 真正动手编辑时，允许外圈稍微跟一点
3. 每一步结束后，又把不够确定的地方往源图拉回去
4. 只有模型在某个位置真的表现出足够一致的编辑证据，才允许那个位置继续保留编辑

所以它不像一种“全局猛推编辑”的方案，更像：

- 主体区域稳稳推进
- 边缘区域谨慎补充
- 背景区域尽量拉回

## 9. 与 baseline、DiffEdit、Prompt-to-Prompt、MasaCtrl 的关系

### 9.1 与 support baseline 的关系

baseline 的做法更像：

- 用 soft ROI 直接参与 effective mask
- anchor 则从 soft ROI 逐渐收紧到 hard ROI

C5H2 相比 baseline 的变化是：

1. soft ROI 改为 deterministic per-sample
2. 不再把整张 soft ROI 直接作为主驱动力
3. support 只写 `core`
4. readout 和 anchor 只弱使用 `boundary`
5. confidence relax 也改成 core-dominant、boundary-supplementary

换句话说，C5H2 的重点不是“更强地编辑”，而是：

- 把 ROI 先验组织得更细，减少无效扩散

### 9.2 与 DiffEdit 的关系

DiffEdit 本身的核心贡献是：

- 根据 source/target prompt 差异生成语义 ROI
- 再围绕这个 ROI 做编辑

C5H2 并不是要替代 DiffEdit，而是把 DiffEdit 作为：

- `ROI prior generator`

然后在此基础上再叠加：

- temporal support
- source anchoring
- confidence-gated local relaxation

因此可以把 C5H2 理解成：

- “把 DiffEdit ROI 用在 source-anchored support 框架里，并做了 deterministic core-boundary 改造”

### 9.3 与 Prompt-to-Prompt 的关系

Prompt-to-Prompt 更偏向：

- 通过 cross-attention control 直接约束编辑内容

而 C5H2 更偏向：

- 用 ROI + support + anchor 控制“哪里改、改多少、哪里拉回 source”

所以两者的主要区别不是“谁更高级”，而是控制手段不同：

- Prompt-to-Prompt 是 attention control 主导
- C5H2 是 ROI/support/latent anchoring 主导

### 9.4 与 MasaCtrl 的关系

MasaCtrl 强调的是：

- mutual self-attention control
- 保持结构和 identity 一致性

C5H2 没有改 self-attention 机制，而是改：

- ROI 如何组织
- temporal support 如何写入
- anchor 如何按 confidence 局部放松

所以 C5H2 的创新点不在 attention operator，而在：

- `ROI prior -> support memory -> anchor relaxation` 这条链路的组织方式

## 10. C5H2 的创新点可以怎么写

如果你要在论文里写 contribution，可以考虑比较稳妥地表述成下面几条。

### 写法 A：偏保守

1. 我们提出了一种用于 source-anchored diffusion editing 的 deterministic core-boundary ROI organization strategy。
2. 我们将 DiffEdit 生成的 soft ROI 分解为 adaptive hard core 与 normalized soft boundary，并分别接入 temporal support 与 source anchoring。
3. 我们提出了 boundary-aware confidence-gated local anchor relaxation，使编辑放松只发生在 ROI、discrepancy 和 support 一致的局部区域。

### 写法 B：更强调机制链条

1. 我们指出，在 source-anchored 编辑中，直接使用随机 soft ROI 容易引入结果波动，而直接使用 hard ROI 又容易导致欠编辑。
2. 为此，我们提出 deterministic core-boundary ROI decomposition，将稳定的 core 用作 support 主驱动力，将弱边界仅作为 readout 与 anchoring 的辅助项。
3. 我们进一步设计了 boundary-aware confidence gating，在保留局部可编辑性的同时抑制背景漂移。

### 不建议写得过满的地方

不建议把 C5H2 写成：

- 全新 diffusion editing framework
- 全新 ROI generator
- 全新 attention control method

更准确的定位仍然是：

- 在既有 source-anchored support 框架上的关键机制升级

## 11. 失败模式与局限性

论文里最好不要只写优点，还要把局限性讲清楚。

### 11.1 ROI 先验错了，后面很难完全救回来

如果 DiffEdit 生成的 `R_soft` 本身就漏掉了目标区域，那么：

- `R_core` 会更小
- support memory 无法稳定写进去
- 后续仍然可能欠编辑

所以 C5H2 不是完全摆脱 ROI 先验，而是更稳定地利用它。

### 11.2 如果 dynamic evidence 很弱，confidence relax 也不会强行放开

这本来是为了保护 locality，但副作用是：

- 某些本来就难改的样本，仍可能偏保守

特别是在：

- 目标属性很抽象
- 视觉证据很弱
- ROI 边界本来就不明确

的情况下更明显。

### 11.3 对大结构变化任务可能仍然偏保守

如果编辑不是局部外观改动，而是明显的几何或大结构重排，那么：

- source anchoring 天然会形成更大阻力

这类任务并不是 C5H2 最擅长的方向。

## 12. 代码中的指标定义

当前代码里常用的几项指标都来自 `DyMaskRefactor/metric_runtime.py`。

### 12.1 `edit_clip`

代码里实际汇总用的是：

- `clip_score_edit_part`

它等价于：

- `clip_similarity_target_image_edit_part`

实现方式是：

1. 用 GT edit mask 只保留编辑区域
2. 将 masked edited image 与 `target_prompt` 做 CLIP image-text similarity
3. 结果乘以 `100`

如果写成式子，可以近似记为：

`EditCLIP = 100 * cos(f_img(I_hat * G), f_txt(p_t))`

其中：

- `G` 是 GT edit mask
- `f_img` 和 `f_txt` 是 CLIP 编码器

### 需要注意

这不是所有论文都完全一样的一套 CLIP 指标定义。它更准确地说是：

- “基于 GT 局部区域的 CLIP image-text similarity”

### 12.2 `outside_psnr`

代码别名为：

- `outside_psnr = psnr_unedit_part`

即只在 GT 未编辑区域上计算 source image 与 edited image 的 PSNR：

`OutsidePSNR = PSNR(I_s * (1-G), I_hat * (1-G))`

越高表示：

- 未编辑区域保持得越好

### 12.3 `outside_lpips`

代码别名为：

- `outside_lpips = lpips_unedit_part`

定义为：

`OutsideLPIPS = LPIPS(I_s * (1-G), I_hat * (1-G))`

越低表示：

- 未编辑区域越接近源图

### 12.4 `locality_ratio`

当前实现先计算 source 与 edited 之间的 spatial LPIPS change map `Delta`，再统计变化量落在 GT mask 内的比例：

`Locality = sum(Delta * G) / (sum(Delta * G) + sum(Delta * (1-G)))`

越高表示：

- 变化更集中在应编辑区域内

### 12.5 `structure_distance`

代码里用的是基于 DINO self-similarity 的 MSE。可以理解成：

- 比较 source 和 edited 在 DINO 特征空间里的结构自相似矩阵是否变化过大

数值越低通常表示：

- 结构破坏更小

## 13. 关键超参数怎么写

如果论文里要放实现细节，可以把 C5H2 的关键参数分成 4 组。

### 13.1 temporal support

- `support_rho`
  - temporal support 的时间平滑系数
  - 越大越依赖历史记忆

### 13.2 core read

- `core_read_start_weight`
- `core_read_end_weight`

作用：

- 控制 `support_state` 向 `R_core` 靠拢的强度

### 13.3 boundary read / anchor

- `boundary_read_start_weight`
- `boundary_read_end_weight`
- `boundary_anchor_start_weight`
- `boundary_anchor_end_weight`

作用：

- 控制 boundary 在 effective mask 和 anchor 中的参与强度

### 13.4 confidence ROI

- `boundary_confidence_weight`

作用：

- 控制 boundary 在 confidence relax 中的占比

### 13.5 core threshold policy

- `roi_core_quantile`
- `roi_core_peak_ratio`
- `roi_core_threshold_min`
- `roi_core_threshold_max`
- `roi_core_min_active_ratio`
- `roi_core_active_floor`

作用：

- 决定如何从 soft ROI 自动提取 core

## 14. 可以直接放进论文的方法小节草稿

下面这段可以直接作为中文方法小节初稿，再按你的论文风格润色。

### 14.1 方法概述

我们提出 C5H2，一种面向 source-anchored diffusion editing 的 deterministic core-boundary ROI 组织策略。给定源图像和目标文本描述，我们首先通过 DDIM inversion 获取源图像在扩散过程中的 latent 轨迹，并基于 DiffEdit 生成语义相关的 soft ROI。不同于直接使用该 soft ROI 作为编辑先验，C5H2 对其进行确定性缓存，并进一步分解为一个自适应 hard core 与一个归一化 soft boundary。我们仅使用 hard core 更新 temporal support memory，以避免模糊边界在时间维度上被持续放大；同时，在 mask readout 与 source anchoring 阶段，我们以衰减方式引入 soft boundary，以兼顾局部编辑完整性与背景保持。进一步地，我们设计了 boundary-aware confidence-gated local anchor relaxation，使 anchor 的放松仅发生在 discrepancy、dynamic mask 与 effective mask 共同支持的局部区域，从而在减少欠编辑的同时抑制背景漂移。

### 14.2 ROI 分解

对于 DiffEdit 生成的 soft ROI `R_soft`，我们先在有效激活区域内估计其高分位响应，并结合峰值比例构造阈值 `tau`。该阈值被限制在预设的最小和最大范围内；若得到的 core 面积过小，则进一步下调阈值以满足最小激活面积约束。由此得到的 hard core `R_core` 表示高置信编辑区域，而 soft boundary `R_bnd` 则由 `R_soft` 在 core 外部的残差构成，并经过归一化处理。这样的设计使我们能够将稳定区域和模糊边界在后续编辑中分开处理。

### 14.3 Core-driven temporal support

在每个去噪步，我们首先利用 source/target 双分支噪声差异、cross-attention 响应以及 latent drift 构建 dynamic mask。随后，仅使用 `R_core` 与该 dynamic mask 的乘积作为 support evidence，并通过指数平滑方式递推 temporal support state。这样可以避免模糊边界被长期积累为主导编辑驱动力。为了避免过度保守，我们在 readout 阶段再引入衰减的 boundary 项，构造 effective mask 用于融合 source 与 target 噪声预测。

### 14.4 Boundary-aware source anchoring

在 scheduler 更新得到编辑 latent 后，我们使用由 `R_core` 和衰减 boundary 共同构成的 anchor base，将不可信区域向源图像的 latent 轨迹拉回。进一步地，我们基于 discrepancy、dynamic mask 以及 effective mask 与 dynamic mask 的一致性定义局部 confidence，并只在高 confidence 区域内放松 anchor。相比于全局放松策略，这种局部化的 confidence-gated relaxation 能够更有效地抑制背景漂移，同时为真正需要补充编辑的边界区域留下必要自由度。

## 15. 可直接放进论文的贡献点草稿

下面这段也可以直接改写进论文。

1. 我们提出一种 deterministic core-boundary ROI 组织策略，将 DiffEdit 的 soft ROI 分解为 adaptive hard core 与 normalized soft boundary，从而显式区分高置信主编辑区与低置信边界区。
2. 我们提出 core-driven temporal support 机制，仅使用 hard core 更新 support memory，并在 readout 阶段以衰减方式引入 boundary，以缓解 soft ROI 直接累积带来的外溢问题。
3. 我们提出 boundary-aware confidence-gated source anchoring，通过 discrepancy、dynamic mask 与 mask consistency 共同调制 anchor relax，仅在局部高置信区域内释放编辑自由度。

## 16. 参考文献与可搜索链接

下面这些文献足够支撑 C5H2 的写作背景。链接我尽量给到论文主页或 arXiv / OpenReview / CVF 页面，方便你直接检索。

1. Song, Meng, Ermon. *Denoising Diffusion Implicit Models*. ICLR 2021.  
   OpenReview: https://openreview.net/forum?id=St1giarCHLP

2. Rombach, Blattmann, Lorenz, Esser, Ommer. *High-Resolution Image Synthesis with Latent Diffusion Models*. CVPR 2022.  
   arXiv: https://arxiv.org/abs/2112.10752

3. Radford et al. *Learning Transferable Visual Models From Natural Language Supervision*. ICML 2021.  
   arXiv: https://arxiv.org/abs/2103.00020

4. Hertz, Mokady, Tenenbaum, Aberman, Pritch, Cohen-Or. *Prompt-to-Prompt Image Editing with Cross-Attention Control*. ICLR 2023.  
   arXiv: https://arxiv.org/abs/2208.01626

5. Couairon, Verbeek, Schwenk, Cord. *DiffEdit: Diffusion-based Semantic Image Editing with Mask Guidance*. ICLR 2023.  
   arXiv: https://arxiv.org/abs/2210.11427

6. Cao, Wang, Cheng, Xia, Shan. *MasaCtrl: Tuning-Free Mutual Self-Attention Control for Consistent Image Synthesis and Editing*. ICCV 2023.  
   arXiv: https://arxiv.org/abs/2304.08465

7. Caron et al. *Emerging Properties in Self-Supervised Vision Transformers*. ICCV 2021.  
   arXiv: https://arxiv.org/abs/2104.14294

8. Zhang, Isola, Efros, Shechtman, Wang. *The Unreasonable Effectiveness of Deep Features as a Perceptual Metric*. CVPR 2018.  
   CVF Open Access: https://openaccess.thecvf.com/content_cvpr_2018/html/Zhang_The_Unreasonable_Effectiveness_CVPR_2018_paper.html

## 17. 最后一句话怎么概括 C5H2

如果整篇论文里只能用一句话定义 C5H2，我建议写成：

- C5H2 是一种建立在 source-anchored temporal support 框架上的 deterministic core-boundary ROI 编辑策略，它将 DiffEdit soft ROI 拆成稳定的 hard core 与弱边界补充项，并通过 core-driven support 与 boundary-aware confidence anchoring，在编辑充分性与背景保持之间取得更稳的平衡。
