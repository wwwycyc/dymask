# trigate迁移分支

## 🧑‍💻 User

我想做图像编辑，主要是利用反演轨迹来计算出soft mask，用来在每步中指导图像编辑。有什么baseline推荐吗，你先联网搜索多找些信息

---
## 🤖 Assistant

可以，先给你一版“**围绕反演轨迹 + soft mask 引导编辑**”的 baseline 地图。我先联网查了一圈，重点看了和 **real image editing / inversion / mask guidance / attention control** 直接相关的论文。你这个方向很像是在做：

> 从反演得到的逐步轨迹里，提取“哪些区域该改、哪些区域该保留”的软掩码，再把它注入每一步 denoising / sampling 中做局部可控编辑。

这个问题最接近的 baseline，通常不是单独一篇，而是 **“反演方法 + 掩码生成方法 + 轨迹注入/注意力控制方法”** 的组合。

---

## 一、我建议你优先看的 baseline 分组

### A. 反演类 baseline
这是你“轨迹”来源的核心。

#### 1) **Null-Text Inversion**  
非常经典的 real image editing baseline。  
特点：
- 先做 DDIM inversion 得到 trajectory / latent path
- 再优化 unconditional embedding（null-text），提升重建质量和可编辑性
- 常与 Prompt-to-Prompt 搭配

为什么适合你：
- 你要从 inversion trajectory 里算 soft mask，NTI 是最标准的“有轨迹”的起点
- 如果你的方法强调“基于每步反演状态估计 mask”，NTI 很适合做主 baseline

来源：
- CVPR 2023 open access:  
  https://openaccess.thecvf.com/content/CVPR2023/papers/Mokady_NULL-Text_Inversion_for_Editing_Real_Images_Using_Guided_Diffusion_Models_CVPR_2023_paper.pdf

---

#### 2) **Direct Inversion**
特点：
- optimization-free
- 目标是更快地做 real image inversion/editing
- 比 NTI 更轻量

为什么适合你：
- 如果你方法里额外加了“逐步 soft mask 估计”，Direct Inversion 是很好的效率对照组
- 能回答：你的收益是来自更好的 mask，还是来自昂贵 inversion

来源：
- arXiv: https://arxiv.org/abs/2211.07825

---

#### 3) **Edit-Friendly DDPM Inversion**
特点：
- 明确就是为“编辑友好”的噪声空间设计
- 强调 inversion 后更利于后续语义操作
- 很适合作为“轨迹空间更适合编辑”的 baseline

为什么适合你：
- 你如果要做“从 trajectory 中提取稳定 soft mask”，这种 edit-friendly inversion 很值得对比
- 它本身就和“编辑期间逐步注入控制”很搭

来源：
- arXiv: https://arxiv.org/abs/2304.06140  
- CVPR 2024 OA PDF:  
  https://openaccess.thecvf.com/content/CVPR2024/papers/Huberman-Spiegelglas_An_Edit_Friendly_DDPM_Noise_Space_Inversion_and_Manipulations_CVPR_2024_paper.pdf

---

#### 4) **Negative-prompt Inversion**
特点：
- 更快的 inversion/editing
- 强调重建 fidelity 与编辑能力平衡

为什么适合你：
- 适合作为更现代一点的 inversion baseline
- 如果你做实验，和 NTI / Direct Inversion 一起构成很完整的 inversion family

来源：
- arXiv: https://arxiv.org/abs/2305.16807  
- WACV 2025 OA PDF:  
  https://openaccess.thecvf.com/content/WACV2025/papers/Miyake_Negative-Prompt_Inversion_Fast_Image_Inversion_for_Editing_with_Text-Guided_Diffusion_WACV_2025_paper.pdf

---

#### 5) **EDICT**
特点：
- exact diffusion inversion 方向
- 强调可逆性和高保真重建

为什么适合你：
- 如果你很在意“轨迹误差会污染 soft mask”，EDICT 是很有价值的对照
- 可作为“高保真 inversion 上限参考”

来源：
- arXiv: https://arxiv.org/abs/2211.12446

---

### B. 自动 mask / soft region 估计类 baseline
这是和你“算 soft mask”最直接相关的一组。

#### 6) **DiffEdit**
这个几乎是你必须对比的 baseline。  
特点：
- 自动生成编辑区域 mask
- 核心思想是对比 source prompt 与 target prompt 下的 diffusion prediction 差异来得到 mask
- 再做 mask-guided editing

为什么特别重要：
- 你的方法是“利用 inversion trajectory 计算 soft mask”
- DiffEdit 则是“利用条件变化产生的差异信号计算 mask”
- 这是最自然、最强的直接 baseline 之一

来源：
- arXiv: https://arxiv.org/abs/2210.11427

---

#### 7) **InstDiffEdit / Instant Attention Masks**
特点：
- 直接利用 cross-attention 生成 mask
- 强调 automatic、training-free、速度快
- attention aggregation + refinement 得到更干净的 mask

为什么适合你：
- 如果你从轨迹中提 mask，它的强对照就是“从 attention 中提 mask”
- 可以验证：trajectory-based mask 是否比 attention-based mask 更稳定、更细致

来源：
- arXiv: https://arxiv.org/abs/2401.07709

---

### C. 逐步注入控制 / 注意力控制类 baseline
你的 soft mask 最后要“每步中指导编辑”，这组最相关。

#### 8) **Prompt-to-Prompt (P2P)**
特点：
- 通过控制 cross-attention map 做文本驱动编辑
- 经典中的经典
- 通常结合 inversion 用于真实图像编辑

为什么适合你：
- 你可以把自己的方法看作：  
  **P2P 的逐步注意力控制 + 你自己的 trajectory-derived soft mask**
- 所以 P2P 几乎是必做 baseline

来源：
- arXiv: https://arxiv.org/abs/2208.01626

---

#### 9) **MasaCtrl**
特点：
- tuning-free mutual self-attention control
- 强调编辑时保持结构/identity consistency
- 对 non-rigid editing 很有帮助

为什么适合你：
- 如果你的 soft mask 是为了在每步保留未编辑区域、同时允许局部几何/外观变化，MasaCtrl 很值得对比
- 它代表“通过 self-attention correspondence 做一致性控制”的路线

来源：
- arXiv: https://arxiv.org/abs/2304.08465  
- ICCV 2023 OA PDF:  
  https://openaccess.thecvf.com/content/ICCV2023/papers/Cao_MasaCtrl_Tuning-Free_Mutual_Self-Attention_Control_for_Consistent_Image_Synthesis_and_ICCV_2023_paper.pdf  
- GitHub: https://github.com/TencentARC/MasaCtrl

---

#### 10) **Plug-and-Play Diffusion Features (PnP)**
特点：
- 从 source image 的中间特征注入到生成过程
- 保结构、保布局能力较强

为什么适合你：
- 你的方法是 mask-based step guidance
- PnP 是 feature injection-based step guidance
- 很适合做“注入什么信号更有效”的对比

来源：
- arXiv: https://arxiv.org/abs/2211.12572  
- CVPR 2023 OA PDF:  
  https://openaccess.thecvf.com/content/CVPR2023/papers/Tumanyan_Plug-and-Play_Diffusion_Features_for_Text-Driven_Image-to-Image_Translation_CVPR_2023_paper.pdf

---

### D. 常见编辑基线/上层任务基线
虽然不一定直接用 trajectory + soft mask，但论文里通常会拿来对比。

#### 11) **pix2pix-zero**
特点：
- zero-shot image-to-image translation
- 借助文本方向进行编辑
- 强调 structure preservation

来源：
- arXiv: https://arxiv.org/abs/2302.03027  
- project page: https://pix2pixzero.github.io/

适合用途：
- 作为“zero-shot editing baseline”
- 但它不是最贴近你方法机制的 baseline

---

#### 12) **LEDITS**
特点：
- DDPM inversion + semantic guidance
- 是 real image editing 的轻量方案之一

来源：
- arXiv: https://arxiv.org/abs/2307.00522

适合用途：
- 如果你论文想展示和 semantic guidance 路线的比较，可以加
- 但优先级低于 NTI / DiffEdit / P2P / MasaCtrl

---

#### 13) **InstructPix2Pix**
特点：
- instruction-based image editing
- 是非常常见的通用编辑 baseline

来源：
- arXiv: https://arxiv.org/abs/2211.09800  
- CVPR 2023 OA PDF:  
  https://openaccess.thecvf.com/content/CVPR2023/papers/Brooks_InstructPix2Pix_Learning_To_Follow_Image_Editing_Instructions_CVPR_2023_paper.pdf

适合用途：
- 作为“指令式强基线”
- 但它不是 inversion-based，也不强调 trajectory-level controllability
- 更适合放在 broad comparison，不是机制最对口的 baseline

---

## 二、如果你的方法核心是“反演轨迹 -> soft mask -> 每步引导”，我建议的 baseline 套餐

我建议你至少分成三层：

### 1. 最核心、最对口的 baseline
这些最应该做：

- **Null-Text Inversion + Prompt-to-Prompt**
- **DiffEdit**
- **MasaCtrl**
- **Edit-Friendly DDPM Inversion**
- **Direct Inversion**

这五个已经能很好覆盖：
- 反演质量
- 自动 mask
- 注意力控制
- 一致性保持
- 编辑友好 latent

---

### 2. 如果实验资源够，再加
- **Negative-prompt Inversion**
- **Plug-and-Play Diffusion Features**
- **pix2pix-zero**
- **LEDITS**

---

### 3. 如果你只想先快速起一个可靠实验框架
我会建议先做下面 4 个：

1. **NTI + P2P**  
2. **DiffEdit**  
3. **MasaCtrl**  
4. **你的方法：NTI trajectory soft mask + step-wise guidance**

这个组合最能说明你的贡献。

---

## 三、从“方法设计角度”看，你的方法最该对比什么 ablation

你这个想法很适合做系统 ablation。建议至少做以下几类：

### Ablation A：mask 来源
比较：
- 固定手工 mask
- attention-derived mask
- prediction-difference mask（类似 DiffEdit）
- **trajectory-derived soft mask（你的）**

这样你能证明：  
**不是有 mask 就行，而是反演轨迹包含更好的局部可编辑性信号。**

---

### Ablation B：mask 作用位置
比较 soft mask 注入到：
- latent blending
- noise prediction residual blending
- cross-attention replacement/gating
- self-attention feature mixing
- decoder feature injection

你最后可能会发现：
- 对局部编辑最稳的，常常是 **noise prediction 或 latent update 层面做 masked interpolation**
- 对语义改动更强的，常常是 **attention 层面做 gating**

---

### Ablation C：mask 的时序策略
这是你的亮点之一，建议重点做：

- 单一静态 mask（所有步相同）
- 仅 early-step mask
- 仅 late-step mask
- coarse-to-fine schedule
- **每步由 inversion trajectory 动态估计的 mask**

这能非常直接地支持“trajectory-aware”这个卖点。

---

### Ablation D：反演器选择
- DDIM inversion
- NTI
- Direct Inversion
- Edit-Friendly DDPM inversion

证明你的方法对 inversion backend 的鲁棒性。

---

## 四、如果你要写论文，我建议你把相关工作这样组织

### Related work 结构建议
1. **Diffusion-based real image inversion**
   - DDIM inversion
   - Null-text inversion
   - Direct Inversion
   - Edit-Friendly DDPM Inversion
   - Negative-prompt Inversion
   - EDICT

2. **Mask-guided / localized image editing**
   - DiffEdit
   - InstDiffEdit
   - inpainting-based editors

3. **Attention/feature control for consistent editing**
   - Prompt-to-Prompt
   - MasaCtrl
   - Plug-and-Play Diffusion Features

4. **Instruction-based / general editing baselines**
   - InstructPix2Pix
   - pix2pix-zero
   - LEDITS

---

## 五、我对你这个方向的判断：最值得打的点

如果你要把方法做得有新意，我觉得最值得强调的不是“我也用了 mask”，而是：

### 方向 1：**trajectory discrepancy as editability signal**
比如从 source prompt / target prompt 的反演或重采样轨迹差异里估计 edit-prone region。

### 方向 2：**time-varying soft mask**
不是一个 static mask，而是：
- 早期步：控制全局语义
- 中期步：控制对象区域
- 后期步：控制边界和纹理

### 方向 3：**mask uncertainty**
soft mask 不是单纯 sigmoid map，而是带 uncertainty/confidence。  
低置信区域保守注入，高置信区域强编辑。这个很容易出效果。

### 方向 4：**双分支 guidance**
每步同时混合：
- preserve branch：跟 source trajectory 对齐
- edit branch：跟 target denoising 对齐
- soft mask 决定二者空间权重

这个和你“利用反演轨迹指导每步编辑”很契合。

---

## 六、我建议你优先阅读顺序

如果你现在时间有限，按这个顺序看最有效：

1. **Null-Text Inversion**  
2. **Prompt-to-Prompt**  
3. **DiffEdit**  
4. **MasaCtrl**  
5. **Edit-Friendly DDPM Inversion**  
6. **Plug-and-Play Diffusion Features**  
7. **Direct Inversion**  
8. **Negative-prompt Inversion**  
9. **LEDITS**  
10. **pix2pix-zero / InstructPix2Pix**

---

## 七、给你一个“最推荐 baseline 清单”

### 必做
- Null-Text Inversion  
- Prompt-to-Prompt  
- DiffEdit  
- MasaCtrl  
- Edit-Friendly DDPM Inversion  

### 建议加
- Direct Inversion  
- Negative-prompt Inversion  
- Plug-and-Play Diffusion Features  

### 可选 broad baselines
- pix2pix-zero  
- LEDITS  
- InstructPix2Pix  

---

## 八、如果你愿意，我下一步可以继续帮你做两件事之一

### 选项 A：我帮你整理成一张表
列成：

- 方法名
- 是否需要 inversion
- 是否自动生成 mask
- mask 类型
- 是否逐步控制
- 控制位置（latent/attention/feature）
- 优点
- 缺点
- 和你方法的关系

### 选项 B：我直接帮你设计你的方法 baseline 实验方案
比如给你一版：
- 数据集
- 对比方法
- 指标
- ablation 列表
- 论文图表怎么画

如果你愿意，我下一条就直接给你整理成 **“baseline 对比总表 + 适合你方法的实验设计”**。

---
## 🧑‍💻 User

我想从已有的代码上进行改进

---
## 🤖 Assistant

那如果你的目标是 **“基于已有代码改，而不是从零写”**，我会把推荐进一步收缩成：

## 最推荐改的代码底座

### 1) **MasaCtrl**
我现在最推荐你先从它改。

原因很直接：
- 它本身就是 **editing / consistency / step-wise control** 路线
- 官方仓库明确说可以通过 **register attention processor** 集成到 diffusers pipeline，这对你插入 **soft mask gating** 很友好  
  来源：MasaCtrl 官方 GitHub  
  https://github.com/TencentARC/MasaCtrl
- 仓库里已经有：
  - real image editing
  - DDIM inversion
  - attention-level control
  - SD / SDXL 支持

这意味着你可以少补很多基础设施，直接把精力放在：
- 从 inversion trajectory 提 mask
- 在 self-attention / cross-attention / latent update 里做 soft mask 注入

**适合你做的改法：**
- 在 inversion 阶段缓存每步 latent / noise pred / attention map
- 由 source-target trajectory discrepancy 生成 `soft_mask_t`
- 在 MasaCtrl 的 attention processor 里加 spatial gating：
  - 编辑区强注入 target
  - 非编辑区保留 source feature

**为什么它排第一：**
你想做的是“每步指导图像编辑”，而 MasaCtrl 的代码结构已经非常接近这个落点。

---

### 2) **Prompt-to-Prompt / Null-Text Inversion 体系**
这个是第二推荐，而且其实非常关键。

来源：
- Prompt-to-Prompt 官方代码：  
  https://github.com/google/prompt-to-prompt
- Null-Text Inversion 论文页面里给到了代码入口，指向 Prompt-to-Prompt 仓库中的扩展  
  可从 CVPR 2023 slides 看到 code 指向  
  https://cvpr.thecvf.com/media/cvpr-2023/Slides/22074.pdf

为什么适合你：
- 这是最经典的 **real image inversion + attention editing** 底座
- 社区里很多后续工作都建立在这套范式上
- 如果你论文里要强调和经典方法兼容，P2P/NTI 是最标准的 starting point

**适合你的改法：**
- 保留 NTI inversion
- 每步从 inverted latent 和编辑 latent 的差异中估计 `soft_mask_t`
- 然后替换原始的 attention replace/refine 逻辑，变成：
  - `edited_attn = mask_t * target_attn + (1-mask_t) * source_attn`
- 或者对 noise prediction 做 masked blending

**优点：**
- paper baseline 很强
- 论文叙事最顺
- 你做出的改动容易被审稿人理解

**缺点：**
- 原始 notebook 风格比较重
- 工程化程度通常不如较新的 diffusers 项目
- 如果你想快速扩展到 SDXL，可能不如 MasaCtrl 顺手

---

### 3) **Edit-Friendly DDPM Inversion 官方代码**
官方仓库：
https://github.com/inbarhub/DDPM_inversion

为什么值得改：
- 这是很强的 inversion 底座
- 仓库里已经显式支持不同 mode，例如 README 里提到：
  - `our_inv`
  - `p2pinv`
  - `ddim`
  - `p2p`
- 也就是说它本身就在“反演 + 编辑”交界处，很适合你插入 trajectory-based mask

**适合你的改法：**
- 先用它的 inversion 得到更“edit-friendly”的轨迹
- 在采样阶段加入你自己的 `soft_mask_t`
- 你甚至可以直接做一个新 mode，比如：
  - `trajmask_inv`
  - `trajmask_p2p`

**优点：**
- 很贴你的“反演轨迹”主题
- 如果你方法核心贡献是 mask 来自 inversion trajectory，这个底座最对题

**缺点：**
- 它更偏研究代码
- 如果你想快速做 attention processor 级别的插拔式实验，可能还是 MasaCtrl / diffusers 更舒服

---

## 不太建议作为第一改造对象的

### 4) **DiffEdit 代码**
我查到的更多是 **非官方/社区实现**，比如：
https://github.com/Gennaro-Farina/DiffEdit

它很适合作为 baseline 参考，但我**不建议你把它作为主开发底座**，因为：
- 你的核心不是“做一个自动 mask 再 inpaint”
- 而是“利用 inversion trajectory，在每一步做软控制”
- DiffEdit 更像是给你一个 **mask 生成 baseline**，不是最自然的主干框架

除非你的方法最后更像：
- 先 trajectory-based 估计 mask
- 再走 inpainting/editing pipeline

否则它更适合拿来比较，不适合拿来深改。

---

## 我的结论：如果只能选一个仓库开改

### 首选：**MasaCtrl**
如果你更重视：
- 代码可改性
- 每步控制
- attention 注入
- 真实图像编辑
- diffusers 兼容

### 次选：**Edit-Friendly DDPM Inversion**
如果你更重视：
- “反演轨迹”本身是你论文的绝对主角
- 你要突出 trajectory-derived mask 的理论与实验

### 第三：**P2P / NTI**
如果你更重视：
- 经典 baseline 说服力
- 论文社区接受度
- 与已有真实图像编辑工作强对齐

---

# 我建议你的实际开发路线

## 路线 A：最稳
**以 MasaCtrl 为主干 + 接入你自己的 inversion trajectory mask**
1. 跑通 MasaCtrl real image editing
2. 缓存 inversion 过程中的每步 latent / feature / noise pred
3. 设计 `soft_mask_t`
4. 在 attention processor 中做 gating
5. 再做 ablation：静态 mask vs 动态 mask

这个最适合快速出结果。

---

## 路线 B：最贴题
**以 Edit-Friendly DDPM Inversion 为主干**
1. 跑通官方 inversion + manipulation
2. 理解它的 `our_inv / p2pinv / p2p`
3. 新增 trajectory-mask 分支
4. 在编辑采样时做 step-wise masked blending
5. 再和 DDIM / P2P / 原方法比较

这个最适合做论文主线。

---

## 路线 C：最经典
**以 P2P/NTI 为主干**
1. 跑通 null-text inversion
2. 跑通 prompt-to-prompt attention control
3. 在 cross-attention replacement 部分加入 soft mask
4. 扩展到 self-attention 或 latent residual gating

这个最容易讲清楚贡献。

---

# 如果你问我“具体先 clone 哪个 repo”
我会回答：

1. **TencentARC/MasaCtrl**  
   https://github.com/TencentARC/MasaCtrl

2. **inbarhub/DDPM_inversion**  
   https://github.com/inbarhub/DDPM_inversion

3. **google/prompt-to-prompt**  
   https://github.com/google/prompt-to-prompt

---

# 如果你愿意，我下一步可以直接继续帮你做更具体的东西，三选一：

### 选项 1：帮你比较这 3 个 repo 的“可改点”
我可以直接写成：
- 哪些文件该看
- 哪些类/函数适合插入 soft mask
- 各自修改难度

### 选项 2：帮你定一个“最小可行改法”
比如基于 MasaCtrl，给你设计：
- 输入输出
- 要缓存哪些 tensor
- soft mask 怎么算
- 每步怎么注入

### 选项 3：帮你画代码结构图
我可以按 repo 给你整理出：
- inversion 流程
- sampling 流程
- 你该插入的 hook 点

如果你愿意，我建议下一条我就直接给你做：
**“MasaCtrl / DDPM_inversion / P2P 三个仓库的修改入口对比表”**。

---
## 🧑‍💻 User

我其实已经做了一版，但是很差而且很难回头了，我想顺着思路重新在已有的工作上改进。我发给你看看，其中原提示词问题可以忽略，之后可以通过工程化改进来解决。然后Instance-Group-Aware Replacement Modeling是我为了适配特殊任务来的，可以忽略。
# Method Overview

## 1. Problem Setting

本文考虑一种更贴近真实使用场景的训练外图像编辑设定。系统输入仅包含一张源图像 `I_s` 与一段目标文本 `y_t`，不依赖任何用户提供的 `source prompt`。目标是在保持源图像全局结构、背景布局与非编辑区域内容基本稳定的前提下，生成编辑结果 `I_e`，使其尽可能准确地实现目标文本中的新增语义。

这一设定带来三个直接困难。首先，在缺少 `source prompt` 的情况下，系统无法通过显式的文本差分判断“哪些语义是新增编辑目标、哪些语义已被源图像满足”。其次，若直接以目标文本对整幅图像施加强条件引导，扩散模型往往会出现背景漂移、主体重绘与局部编辑扩散为全局重生成的问题。最后，图像编辑天然需要在“结构保持”与“语义改写”之间取得平衡：过强的保留约束会导致编辑写不进去，过强的语义注入又会破坏原图外观与几何关系。


## 2. Overview

为解决上述问题，当前系统构建了一条由五个核心部分组成的编辑主线：

1. `source-aligned inversion`：将源图像反演到扩散模型的 latent 空间，建立与输入图像对齐的扩散参考轨迹；
2. `automatic edit phrase discovery`：在仅有目标文本的条件下，自动发现真正需要注入的编辑短语，并区分编辑核心、焦点短语与支持短语；
3. `topology-aware dynamic soft masking`：基于注意力、噪声差异、视觉约束与实例组先验，构造随 diffusion timestep 动态变化的软掩码；
4. `continuous tri-phase editing kernel`：采用连续化的 early/middle/late 三阶段控制，在不同时间步协调结构保持、语义改写与纹理收敛；
5. `replacement-specific control policies`：在对象替换任务上，引入实例组、身份锚点与身体包络等机制，进一步限制替换语义的扩散范围与重绘强度。

整体上，该方法不是将编辑视为一次性的局部覆盖操作，而是将其建模为一个随时间演化的受控扩散过程：系统在每个时间步动态判断“哪些区域属于编辑对象、这些区域当前应写入多少目标语义、哪些区域必须继续回拉到源图像参考状态”，从而实现更加稳定的图像编辑。


## 3. Source-Aligned Inversion

系统首先对输入图像执行基于 DDIM 的反演，将其映射到扩散模型的 latent 表示，并构造一条与源图像对齐的时间步轨迹。该轨迹的作用不是直接完成编辑，而是为后续所有编辑步骤提供一个结构参考基线。与从随机噪声重新生成不同，source-aligned inversion 使后续采样始终围绕原图对应的扩散状态展开，从而显著降低背景漂移与全图重绘的风险。

从方法角色上看，这一部分回答的是“原图在模型内部位于何处”。没有这条参考轨迹，后续的所有语义注入都更容易演化为大范围重生成；有了它，系统便可以在局部区域上有控制地偏离原图，同时在非编辑区域持续回归到源图像对应的扩散参考。


## 4. Automatic Edit Phrase Discovery Without Source Prompt

在无 `source prompt` 条件下，方法必须从目标文本 `y_t` 中自动识别真正需要注入的编辑语义。为此，系统并不直接将整句目标文本等同于编辑目标，而是先生成候选短语集合，再利用一组视觉与语言信号对候选短语进行排序和筛选。

当前实现中，候选短语主要通过句法解析与短语解析获得，并结合以下信息进行打分：

- 语言有效性：该短语是否构成有意义的对象、属性或局部描述；
- 空间可定位性：该短语在 cross-attention 中是否对应稳定且可局部化的区域；
- 扩散影响强度：引入该短语后，噪声预测是否产生显著变化；
- 源图像支持度：该短语对应的语义是否已被源图像满足；
- 稳定性与泄漏性：短语响应是否稳定，以及是否过度扩散到不相关区域。

基于这些分数，系统进一步组织出三类短语：

- `edit phrases`：真正用于驱动编辑的核心短语；
- `focus phrases`：用于补强局部语义定位的焦点短语；
- `support phrases`：用于建立实例关联、组关系或上下文提示的支持短语。

这一层的核心价值在于：系统不再依赖人工指定“要改哪个词”，而是在保持用户接口简洁的同时，将编辑语义的提取内化为模型推理流程的一部分。


## 5. Dynamic Soft Masking

在获得编辑短语后，系统不会立即进行全局强编辑，而是先构造一组动态 soft mask。与固定二值遮罩不同，这些 mask 在空间上是连续值，在时间上则随扩散过程变化。具体而言，系统结合以下三类信号来构造编辑区域图：

### 5.1 Attention-Based Semantic Proposal

首先，系统利用 edit phrases 与 focus phrases 的 cross-attention 构造语义先验图，用于估计“哪些区域与目标语义最相关”。这一分支提供稳定但偏保守的语义定位，尤其在扩散早期更有利于保护原始结构。

### 5.2 Noise-Discrepancy-Based Editing Evidence

其次，系统比较目标条件、源参考以及残差信号之间的噪声预测差异，生成 discrepancy map。该分支更直接反映扩散模型“准备在哪些区域发生语义改写”，因此在中后期对真实编辑区域的定位更加敏感。

### 5.3 Source-Aware Visual Constraint

为避免背景和非目标区域被误改，系统还构造视觉约束图 `C_vis`，根据 latent drift 与噪声偏移抑制不应发生大幅编辑的区域。这一约束保证 soft mask 不会无限制扩张，从而维持全图稳定性。

综合上述三类信号后，系统进一步输出一组更具机制含义的控制图：

- `edit_group_mask`：表示当前哪些区域属于编辑实例组；
- `write_zone`：表示当前哪些区域应当接收目标语义写入；
- `preserve_budget`：表示当前哪些区域仍然应优先保留源图像语义。

因此，当前方法的 soft mask 不再只是“哪里该改”的单一答案，而是逐步演化为对“编辑组、写入强度与保留强度”的联合表达。


## 6. Instance-Group-Aware Replacement Modeling

在对象替换任务中，简单的 attention 峰值通常会导致一个典型失败模式：模型主要修改最显著的头脸区域，而对身体、倒影或第二实例的响应不足。为缓解这一问题，系统显式引入了实例组建模机制。

其基本思想是：编辑目标不一定只对应单一实例，而可能对应一个由主体、身体、镜像或第二实例共同组成的实例组。为此，方法围绕 replacement 分支维护多层区域表示，包括：

- `replacement_group_envelope`
- `replacement_group_write_floor`
- `replacement_group_context`
- `replacement_instance_coverage`

这些量分别负责描述：

- 编辑对象组的大致包络范围；
- 组内区域的最低写入下限；
- 组内语义传播所允许的上下文范围；
- 当前替换主体及其相关身体区域的覆盖程度。

在此基础上，系统进一步加入了两个专门的 replacement 控制模块：

### 6.1 Replacement Identity Anchor

该模块从主体锚点、源图像显著性、前景先验与替换覆盖图中构造一个身份/形状锚点，用于抑制替换语义的过度扩散。它直接作用于：

- `semantic_write_region`
- `preserve_zone`
- `replacement_context_zone`
- `boundary_zone`
- `replacement_mask_zone`

其目标不是强行保留源对象语义，而是限制“替换语义可以在多大程度上偏离主体的可信轮廓与局部结构”。

### 6.2 Replacement Body Envelope

该模块进一步从主体锚点、源显著性、编辑候选区域与前景先验中显式构造身体包络，用于缓解“只改头不改身”的问题。与单纯依赖头部 attention 峰值不同，它会为主体躯干与大尺度实例范围提供一个额外的空间桥梁，从而使 replacement 语义可以更有组织地向身体区域传播。


## 7. Continuous Tri-Phase Editing Kernel

在时间维度上，当前系统采用了连续化的 tri-phase 编辑策略。与早期的硬阶段切分不同，当前实现为每个扩散时间步分配软的：

- `early_strength`
- `middle_strength`
- `late_strength`

并据此得到连续的 `alpha_t` 与结构/语义/纹理权重。三阶段各自承担的功能仍然清晰，但其切换已变为平滑过渡：

- `early phase`：偏向结构保持与源参考约束；
- `middle phase`：偏向语义改写，是主要编辑注入阶段；
- `late phase`：偏向边界收敛与纹理细化。

更重要的是，当前连续 tri-phase 控制并非仅在最后一层采样更新中起作用，而是已经向上游扩展到：

- attention / discrepancy 的融合；
- focus 与 support 分支的混合；
- replacement gate 的刷新与历史动量；
- replacement core / write / context 区域的数值调度；
- canonical mask 与 replacement region policy 的行为调节。

因此，tri-phase 在当前系统中不再只是一个简单的时间切片，而是一个贯穿上游 mask 构造到下游 latent 更新的统一执行框架。


---
## 🤖 Assistant

可以，这版其实**思路很多，但主线过宽、控制量过多、可验证核心不够聚焦**。如果你的目标是“顺着已有思路重做一版，而且建立在已有工作代码上”，我会建议你**不要修这套大系统**，而是把它**坍缩成一个很小但可证实的核心方法**。

我先给你一个直判断：

## 一、这版为什么“很差而且很难回头”

不是因为想法完全错了，而是因为它很像一种典型的研究陷阱：

### 1. 模块太多，贡献边界不清
你现在的方法线里同时有：
- inversion
- phrase discovery
- dynamic soft mask
- tri-phase schedule
- replacement modeling
- 多种控制图
- 多种约束图
- 历史动量/刷新机制

这会导致一个问题：
**任何效果都不知道到底是谁带来的。**

审稿/自我迭代时会出现：
- mask有用，还是phrase discovery有用？
- tri-phase有用，还是replacement envelope有用？
- 视觉约束有用，还是source inversion本身有用？

最后很难形成一个“单句贡献”。

---

### 2. 你把“困难设定”和“方法复杂度”绑死了
你的设定是：
- 只有源图像
- 只有 target prompt
- 没有 source prompt

这是一个合理设定。  
但你当前的方法等于默认：

> 因为设定难，所以必须搞自动 phrase discovery + 多分支 mask + 三阶段控制 + replacement 专项机制。

这其实不一定成立。  
更可能的情况是：

> 真正最关键的，不是把控制逻辑越堆越多，而是找到一个**稳定的编辑区域估计信号**，再把它以最简洁的方式注入每步采样。

而这刚好和你最初说的方向一致：  
**利用 inversion trajectory 计算 soft mask。**

---

### 3. 你现在的方法“像系统工程”，不像“研究核心”
现在这版写法更像：
- 一个做了很多 heuristic 的工业 pipeline
- 各模块相互救火
- 每个模块都在补另一个模块的漏洞

这会导致非常难维护，因为一旦一个门控变了，整个系统行为都会漂。

你自己说“很难回头”，我猜大概率是因为：
- 参数太多
- 中间变量太多
- 每个控制图都在多个地方被复用
- 结果很敏感，但很难定位问题来源

---

## 二、我建议你怎么“顺着思路重做”

核心原则就一句话：

> **保留你最有研究价值的洞察，砍掉大部分上层启发式。**

你这版里最值得保留的核心，不是 phrase discovery，也不是 replacement modeling，而是：

### 最值得保留的核心：
1. **source-aligned inversion**
2. **从 source / target 轨迹差异中估计动态 soft mask**
3. **mask 随 timestep 动态变化**
4. **用 mask 在每步平衡 preserve vs edit**

这四个就已经够形成一篇很完整的方法主线了。

---

## 三、我建议你把方法重构成一个“极简核心版”

可以叫成类似：

- **Trajectory-Guided Soft Mask Editing**
- **Inversion-Trajectory-Aware Localized Editing**
- **Step-wise Soft Preservation for Real Image Editing**
- **Trajectory-Derived Dynamic Masking for Text-Driven Image Editing**

不重要，名字先放一边。

---

# 四、重构后的方法主线

我建议你把整套方法压缩成 **3 个模块**，最多 4 个。

---

## 模块 A：Source inversion as structural reference
保留。

内容非常简单：
- 对输入图像做 DDIM inversion / NTI / Edit-friendly inversion
- 得到 source trajectory：`z_t^src`
- 后续每一步采样都能访问 source reference

它只负责一件事：

> 提供“原图在每个时间步应该长什么样”的参考状态。

不要再给它附带太多解释。

---

## 模块 B：Trajectory-derived dynamic soft mask
这是核心模块。

你应该把现在那堆：
- attention proposal
- discrepancy evidence
- visual constraint
- write_zone
- preserve_budget
- group_mask

尽量统一成一个主对象：

### 主对象：
**dynamic soft edit mask** `M_t ∈ [0,1]^(H×W)`

可选再派生一个：
- `P_t = 1 - M_t` 或 preserve mask

但最好不要再搞太多平行 mask 名词。

---

### B 的关键思想
在每个 timestep，比较：
- 源图像反演轨迹对应的参考状态
- 目标文本条件下的去噪更新趋势

如果某个空间位置：
- target update 和 source reference 差异很大
- 且这种差异具有语义集中性
- 且在时间上相对稳定

那么该位置更可能属于真正的编辑区域。

---

### 你可以把 mask 设计成 3 个信号的简洁融合
这个思路和你原版是一脉相承的，但要压缩：

#### 1) trajectory discrepancy
例如：
- `||eps_t^tar - eps_t^src||`
- 或 `||x0_t^tar - x0_t^src||`
- 或 latent update magnitude difference

这是主信号。

#### 2) attention support
用 target phrase / target noun 的 cross-attention map 作为语义支持项。  
这里只保留最基础的 attention prior，不做复杂 phrase taxonomy。

#### 3) source-preservation prior
用 source drift 小、重建敏感区域强保留，避免背景被误改。

最后：
\[
M_t = Normalize(\lambda_1 D_t + \lambda_2 A_t - \lambda_3 C_t)
\]
再加时序平滑、空间平滑。

这就够了。

---

## 模块 C：Step-wise masked editing update
这是你真正该做出效果的地方。

核心思想：

在每个 denoising step，不是整图应用 target-guided update，而是用 `M_t` 控制“写入多少目标语义”。

例如最简单形式：

\[
\hat{\epsilon}_t = (1-M_t)\odot \epsilon_t^{src/ref} + M_t \odot \epsilon_t^{tar}
\]

或者在 latent update 上做：
\[
z_{t-1} = (1-M_t)\odot z_{t-1}^{preserve} + M_t \odot z_{t-1}^{edit}
\]

这就是你方法的本体。

---

## 模块 D：可选的时间调度，但不要再叫 tri-phase kernel
你原来的 tri-phase 可以保留“思想”，但不要保留“系统感”。

改成更自然的表达：

### time-dependent edit scheduling
- early steps: stronger preservation
- middle steps: stronger semantic writing
- late steps: boundary refinement

但在实现上，只需要做成 1~2 个连续系数：
- `η_edit(t)`
- `η_preserve(t)`

而不是一大堆 early/middle/late strength 控制所有上游模块。

换句话说：

> tri-phase 作为解释可以保留，作为复杂框架应该删掉。

---

# 五、哪些东西建议直接砍掉

## 1. Automatic edit phrase discovery
这是我最建议你先砍的。

原因：
- 你自己都说“原提示词问题可以忽略，之后可工程化解决”
- 那它现在就不应该留在论文核心里
- 它会严重分散主线

替代方案：
- 直接假设 target prompt 已给定
- 若需 token-level定位，只提取简单 noun phrase / edited token
- 或直接使用 target prompt 的主要名词 token attention

**一句话：别在这一版里研究“编辑什么词”，先研究“怎么稳定地局部编辑”。**

---

## 2. Instance-Group-Aware Replacement Modeling
你已经说可以忽略，那我建议真的忽略，不只是弱化。

因为它的问题是：
- 特殊任务专用
- 非通用
- 强 heuristic
- 和主线耦合严重

这类模块很适合以后作为：
- application extension
- supplementary specialized setting
- appendix variant

但不适合作为方法主体。

---

## 3. 多套语义区图命名
例如：
- edit_group_mask
- write_zone
- preserve_budget
- semantic_write_region
- preserve_zone
- context_zone
- boundary_zone
- replacement_mask_zone

这些在工程上可能有用，但在研究表达上会杀死可读性。

建议最后只保留：
- `M_t^edit`
- `M_t^preserve`（可选）
- `B_t` boundary/confidence（如果你特别需要）

能少就少。

---

# 六、你应该借鉴哪些已有工作来“重做”

如果你要在已有工作基础上重建，我建议不是“继承你现在的代码树”，而是**继承别人的清晰主干**，然后把你的核心塞进去。

---

## 方案 1：基于 **MasaCtrl** 重做
最推荐。

因为你的方法最后最像：
- source inversion
- step-wise editing
- attention / feature control
- preserving consistency outside edited region

你可以把你的核心插成一个更简单的模块：

### 改法
- 保留它的 inversion / editing流程
- 删除你那堆复杂上层 heuristic
- 新增一个 `compute_traj_mask(...)`
- 在每步 attention 或 noise update 处做 masked blending

### 这样你最后的方法会像：
**MasaCtrl + trajectory-derived soft edit mask**

这很容易讲，也容易跑通。

---

## 方案 2：基于 **Edit-Friendly DDPM Inversion** 重做
如果你强调 inversion 更强。

你的主张可以变成：
- baseline inversion 已经 edit-friendly
- 但编辑仍会扩散或重绘
- 我们进一步从 inversion trajectory 中提取 dynamic soft mask
- 用于 localize step-wise editing

### 这样你方法会像：
**Edit-friendly inversion + trajectory mask-guided sampling**

这也很顺。

---

## 方案 3：基于 **P2P / NTI** 重做
适合论文叙事，但工程不一定最舒服。

方法叙事会很经典：
- real image inversion by NTI
- editing via P2P-style control
- our contribution: dynamic mask from source-target trajectory discrepancy

---

# 七、最值得做的“新最小方法”

我直接帮你压成一个能落地的版本。

---

## 方法名层面
暂时把核心定义为：

### **Dynamic Trajectory Mask (DTM)**
输入：
- source image `I_s`
- target prompt `y_t`

输出：
- edited image `I_e`

### 过程
1. invert source image to get `z_t^src`
2. run target-conditioned denoising with source initialization
3. at each timestep compute discrepancy map `D_t`
4. combine `D_t` with target attention prior `A_t` and source preservation prior `C_t`
5. obtain soft edit mask `M_t`
6. perform masked update between preserve branch and edit branch

---

## 一个非常干净的数学表达
### source branch
\[
\epsilon_t^{src} = \epsilon_\theta(z_t, \varnothing / y_{ref}, t)
\]

### target branch
\[
\epsilon_t^{tar} = \epsilon_\theta(z_t, y_t, t)
\]

### discrepancy
\[
D_t = \|\epsilon_t^{tar} - \epsilon_t^{src}\|_2
\]

### semantic support
\[
A_t = \text{AggAttn}(y_t)
\]

### preservation prior
\[
C_t = \text{PreservePrior}(z_t, z_t^{src})
\]

### mask
\[
M_t = \sigma(\alpha_t D_t + \beta_t A_t - \gamma_t C_t)
\]

### masked update
\[
\tilde{\epsilon}_t = (1-M_t)\odot \epsilon_t^{src} + M_t\odot \epsilon_t^{tar}
\]

或者你想更强一些：
\[
\tilde{\epsilon}_t = \epsilon_t^{src} + M_t \odot (\epsilon_t^{tar} - \epsilon_t^{src})
\]

这其实就已经是很完整的方法了。

---

# 八、如果你坚持保留一点你原来的“时间分阶段”思想

可以，但一定要降维成简单的 **schedule**：

例如：
\[
M_t' = s_t \cdot M_t
\]
其中 `s_t` 在中期更高，前后期更低。

或者：
- early: stronger preserve prior
- middle: stronger discrepancy weight
- late: stronger boundary smoothing

但这只能是 **mask computation 的调度项**，不要再让它控制十几个子模块。

---

# 九、从研究角度，你的新贡献应该怎么讲

你应该把贡献改写成这种风格：

### Contribution 1
我们研究无 source prompt 的训练外真实图像编辑，重点关注局部编辑与非编辑区域保持之间的平衡。

### Contribution 2
我们提出一种 **trajectory-derived dynamic soft mask**，通过比较 source-aligned inversion trajectory 与 target-guided denoising update 的差异，在每个扩散步自适应估计编辑区域及其写入强度。

### Contribution 3
我们提出一种简单的 **step-wise masked update**，在每一步融合 preserve branch 与 edit branch，从而在不依赖人工 mask 或 source prompt 的情况下提升局部编辑精度与背景稳定性。

看到没，这样就很集中。

---

# 十、你现在最该避免的事情

## 不要做：
- 再往旧系统里补 patch
- 再新增一层 gate
- 再发明几个 zone
- 再把 phrase / replacement / phase 全部绑在一起

## 应该做：
- 选一个清晰 repo 当骨架
- 只实现一个核心模块：`trajectory -> mask`
- 只实现一种注入方式：`masked epsilon blending` 或 `masked attention gating`
- 先把最小版本跑通
- 然后再做非常少量 ablation

---

# 十一、我对你最实际的建议

如果我是你，我会这样重开：

## 版本 V1
基于 **MasaCtrl** 或 **Edit-Friendly DDPM Inversion**：

只做：
1. source inversion
2. target denoising
3. discrepancy map
4. attention prior
5. soft mask
6. masked epsilon blending

### 完全不做：
- phrase discovery
- instance group
- replacement identity anchor
- body envelope
- 多区图联动
- 历史动量控制

---

## 版本 V2
如果 V1 有效果，再考虑加一个最轻的增强：
- temporal smoothing
- boundary refinement
- confidence-aware mask sharpening

只加一个，不要加一堆。

---

# 十二、我看完你这版后的最终判断

你的直觉其实是对的，真正有价值的点就在这里：

> **编辑区域不应该只靠 prompt token attention 决定，而应该从 source-aligned inversion trajectory 与 target-guided update 的差异中动态估计。**

这是一个明确、可实验、可嫁接到现有代码库、也足够像论文贡献的点。

而你现在这版的问题不是“方向错”，而是：

> **把这个核心点埋在了太多启发式模块里。**

---

如果你愿意，下一步我建议我直接帮你做下面其中一个：

### 选项 A：把你这版方法“重写成一页简化版方法”
我直接帮你写成论文里能用的：
- Problem setting
- Method overview
- 3个模块
- 数学公式
- contribution

### 选项 B：帮你映射到现有代码库
我给你具体说：
- 如果基于 MasaCtrl，改哪些文件/类
- 如果基于 DDPM_inversion，改哪些模块
- `M_t` 在哪里算，在哪里注入

### 选项 C：帮你做“删减清单”
我把你当前方法逐项标注：
- 保留
- 合并
- 删除
- 降级为 appendix / engineering trick

我建议现在最有价值的是 **A + C**：  
先把你的方法压缩成一个清晰核心，再决定代码从哪套 repo 上重做。

---
## 🧑‍💻 User

好的，按照你的建议来

---
## 🤖 Assistant

好。那我直接按 **A + C** 来做：

1. **把你当前方法压缩成一版清晰、可重做的核心方法**
2. **给你当前系统做删减清单：保留 / 合并 / 删除 / 降级**

我会尽量写成你后面能直接拿去改 proposal / paper draft / README 的形式。

---

# Part A：重写成一版“可发表也可实现”的简化方法

---

## 1. Problem Setting

我们考虑一种训练外的文本驱动真实图像编辑设定。给定源图像 `I_s` 和目标文本 `y_t`，模型需要生成编辑结果 `I_e`，使其满足目标文本中要求的新语义，同时尽可能保持源图像的全局布局、背景内容和非编辑区域外观稳定。

与许多现有方法不同，该设定**不依赖用户提供 source prompt**。因此，模型无法直接通过 source/target prompt 的文本差分来定位编辑区域，只能从源图像的内部表示和目标文本引导下的生成变化中推断“哪些区域应该被修改，哪些区域应被保留”。

这一设定的核心挑战在于：如果直接对整幅图像施加目标文本引导，扩散模型往往会将局部编辑放大为全局重生成，导致背景漂移、对象结构破坏和身份不一致。为此，我们希望在扩散采样的每个时间步，动态估计编辑区域及其写入强度，并据此平衡语义注入与结构保持。

---

## 2. Method Overview

我们提出一种围绕**反演轨迹动态软掩码**的图像编辑方法。核心思想是：首先通过 source-aligned inversion 建立与源图像对齐的扩散参考轨迹；随后，在目标文本引导的采样过程中，比较“源参考轨迹”与“目标条件更新”之间的逐步差异，以估计当前时间步真正发生编辑需求的空间区域；最后，利用该动态软掩码在每一步融合“保留分支”和“编辑分支”，使目标语义主要写入局部编辑区域，而非编辑区域持续回拉到源图像参考状态。

整个方法由三个核心组件组成：

1. **Source-aligned inversion**：将源图像映射到与扩散模型对齐的 latent 轨迹，作为后续结构保持的参考；
2. **Trajectory-derived dynamic soft mask**：基于源参考与目标条件更新之间的逐步差异，结合目标文本注意力和源图像保持先验，动态估计编辑区域；
3. **Step-wise masked editing update**：在每个 diffusion step 通过软掩码融合 preserve branch 与 edit branch，以实现局部语义写入与全局结构稳定的统一。

与依赖固定 mask、手工区域标注或 source prompt 差分的方法不同，我们的方法将编辑区域建模为一个**随扩散时间演化的软空间分布**，并直接由反演轨迹与目标语义之间的动态偏离来驱动。

---

## 3. Source-Aligned Inversion

给定源图像 `I_s`，我们首先采用 DDIM inversion、Null-text inversion 或其他可编辑友好的 inversion 方法，将其映射到扩散模型的 latent 空间，并获得一条与源图像对齐的时间步轨迹：

\[
\{z_t^{src}\}_{t=1}^{T}.
\]

该轨迹作为后续编辑过程中的结构参考。与从随机噪声直接生成不同，source-aligned inversion 提供了“源图像在每个时间步应处于何种扩散状态”的基线，使得后续采样可以围绕原图对应的扩散路径展开，而不是脱离原图语义和几何结构进行全图重绘。

在我们的框架中，反演轨迹并不直接决定编辑内容，而是承担两个作用：

- 为非编辑区域提供逐步回拉的参考状态；
- 为编辑区域估计提供对照基线，使模型能够识别目标语义引入后哪些位置真正偏离了源图像对应的去噪趋势。

---

## 4. Trajectory-Derived Dynamic Soft Mask

我们的核心观察是：在真实图像编辑中，真正需要修改的区域通常对应于那些**在目标文本条件下显著偏离源参考轨迹**的位置。基于这一点，我们在每个 diffusion timestep 动态构造软掩码 `M_t`，以表示当前空间位置的编辑强度。

### 4.1 Trajectory discrepancy

在时间步 `t`，我们分别计算当前 latent 在源参考条件和目标文本条件下的噪声预测：

\[
\epsilon_t^{src} = \epsilon_\theta(z_t, c_{src}, t), \qquad
\epsilon_t^{tar} = \epsilon_\theta(z_t, c_{tar}, t),
\]

其中 `c_tar` 表示目标文本条件，`c_src` 可以是空条件、反演相关参考条件，或由 source-aligned inversion 导出的保持分支条件。

二者的差异反映了在目标文本驱动下模型倾向于在哪些区域偏离源图像对应的去噪方向。我们据此定义 trajectory discrepancy map：

\[
D_t = \|\epsilon_t^{tar} - \epsilon_t^{src}\|_2.
\]

与单纯依赖 cross-attention map 相比，这种差异信号更直接刻画了“目标语义是否真的推动当前区域发生更新”，因此对于中后期编辑区域定位尤其有效。

### 4.2 Semantic support from target attention

仅依赖差异项可能会受到噪声扰动或全局风格变化的影响，因此我们进一步从目标文本相关 token 的 cross-attention 中提取一个语义支持图 `A_t`，用于提供目标对象的粗定位先验。该项帮助掩码聚焦于与目标语义相关的区域，抑制纯粹由采样噪声导致的伪响应。

### 4.3 Source-preservation prior

为了避免背景或非目标区域被误编辑，我们引入源图像保持先验 `C_t`。该先验由当前 latent 与源参考轨迹的偏移程度、局部重建敏感性或其他结构保持信号构造，用于抑制那些虽然出现轻微差异、但仍应优先保持源内容的区域。

### 4.4 Dynamic soft mask

综合以上三类信号，我们在每个时间步构造动态软掩码：

\[
M_t = \sigma\big(\alpha_t D_t + \beta_t A_t - \gamma_t C_t\big),
\]

其中 `σ` 为归一化或 sigmoid 映射，`\alpha_t,\beta_t,\gamma_t` 为可随时间步变化的权重。`M_t \in [0,1]^{H\times W}` 表示空间上每个位置在当前时间步的编辑写入强度：值越大，表示该区域越应接受目标语义更新；值越小，则越应保持源图像参考状态。

为了获得更稳定的区域边界，我们可对 `M_t` 施加轻量的时序平滑与空间平滑，但整个框架仍保持单一主掩码设计，而不依赖多个并行控制区图。

---

## 5. Step-wise Masked Editing Update

得到 `M_t` 后，我们在每个 diffusion step 显式分离“保留分支”和“编辑分支”。

- **preserve branch**：倾向于沿着源图像参考轨迹继续去噪，以保持背景、布局和非编辑区域稳定；
- **edit branch**：在目标文本引导下执行语义更新，以写入目标对象或属性变化。

我们使用动态软掩码在这两个分支之间进行逐步融合。一个简单而有效的形式是对噪声预测进行空间加权：

\[
\tilde{\epsilon}_t
=
(1-M_t)\odot \epsilon_t^{src}
+
M_t \odot \epsilon_t^{tar}.
\]

等价地，也可以写成残差注入形式：

\[
\tilde{\epsilon}_t
=
\epsilon_t^{src}
+
M_t \odot (\epsilon_t^{tar}-\epsilon_t^{src}).
\]

随后用 `\tilde{\epsilon}_t` 执行标准采样更新，得到下一步 latent。这样，目标语义只会在 `M_t` 较高的区域被强烈写入，而非编辑区域则持续受到源参考分支的约束，从而减少背景漂移和全图重绘。

---

## 6. Time-Dependent Editing Schedule

尽管我们不再使用复杂的 tri-phase 控制框架，但不同扩散阶段对编辑的需求仍然不同。为此，我们仅保留一个轻量的时间调度机制，用于调节 `M_t` 的强度或三项信号的相对权重。

具体而言：

- 在**早期步骤**，更强调 `C_t` 所代表的结构保持，避免目标文本过早破坏全局布局；
- 在**中期步骤**，提高 `D_t` 和 `A_t` 的作用，使编辑语义集中写入真正需要修改的区域；
- 在**后期步骤**，适度平滑 `M_t` 边界，使局部纹理与区域过渡更加自然。

这种时间调度仅作为动态软掩码的辅助项，而非一个作用于多个子模块的大型控制框架，因此方法结构保持简洁且易于分析。

---

## 7. Method Summary

整体而言，我们的方法将真实图像编辑建模为一个**围绕源反演轨迹展开、并由逐步软掩码控制的局部语义偏移过程**。其优势在于：

- 不依赖 source prompt；
- 不依赖人工 mask；
- 掩码由扩散过程中的真实动态偏离产生，而非固定静态估计；
- 每一步都显式平衡“保留原图”与“写入目标语义”，更适合真实图像局部编辑。

---

# Part B：给你当前方法做删减清单

下面我按你原来的模块逐项判断。

---

## 1. Problem Setting
### 处理建议：**保留，但缩短**
你原来的设定是合理的，尤其是：
- 只有 source image
- 只有 target prompt
- 不依赖 source prompt

这个可以保留，因为它确实是方法动机的一部分。

### 但要删掉的写法
不要把问题写得像必须靠一整套复杂系统才能解决。  
改成更聚焦的表达：

- 无 source prompt 导致无法显式做文本差分
- 整图目标引导容易造成全局重绘
- 因此需要逐步估计局部编辑强度

---

## 2. Source-aligned inversion
### 处理建议：**强保留**
这是你的主线基础，必须保留。

### 如何改
只保留它的两个职责：
- 提供结构参考轨迹
- 提供 mask 估计的对照基线

不要再把它扩展成很多下游控制的总源头。

---

## 3. Automatic Edit Phrase Discovery Without Source Prompt
### 处理建议：**删除主线，降级为工程细节/附录**
这是最应该砍的部分之一。

### 原因
- 你自己已经说 prompt 问题可以暂时忽略
- 它会把方法主线从“how to edit stably”扯到“what to edit linguistically”
- 很容易变成另一个研究问题

### 怎么处理
主文里不讲。  
如果你确实用到了简单 token 筛选，就写成一句轻描淡写的话：

> We use target-token attention aggregation to obtain a coarse semantic prior.

如果后面想保留一点点，可放 appendix：
- noun phrase extraction
- token filtering heuristic

但绝不能做成主贡献。

---

## 4. Topology-aware dynamic soft masking
### 处理建议：**保留，但大幅合并**
这是最值得保留的部分，但必须重构。

### 现在的问题
你这一部分里其实混了三件事：
- mask 信号来源
- mask 语义解释
- 多控制图输出

### 应该改成
统一为：

#### 输入信号
- discrepancy map `D_t`
- attention prior `A_t`
- preservation prior `C_t`

#### 输出
- 一个主掩码 `M_t`
- 如果真需要，外加一个保留图 `1-M_t`

### 要删掉的
- `edit_group_mask`
- `write_zone`
- `preserve_budget`

这些都太像工程中间量，不适合当前主线。

---

## 5. Instance-Group-Aware Replacement Modeling
### 处理建议：**删除主线，降级为特殊任务扩展**
你已经提前说了可以忽略，那我建议真的完全拿掉。

### 怎么放置
以后如果你做特定 benchmark，比如：
- person-to-person replacement
- multi-instance object replacement
- reflected subject replacement

可以作为 extension 写：

> For replacement-heavy scenarios, we further explored instance-group-aware constraints ...

但不是现在。

---

## 6. Replacement Identity Anchor / Body Envelope
### 处理建议：**一起删除**
这两个都依赖于 replacement-specific 设定。  
当前重构版里完全不需要。

---

## 7. Continuous Tri-Phase Editing Kernel
### 处理建议：**保留思想，删除框架**
这是另一个非常需要“降级”的部分。

### 可以保留的
“不同时间步的编辑需求不同”这个观点本身是对的。

### 必须删除的
不要再写：
- tri-phase 贯穿上游到下游所有模块
- early/middle/late 分别控制一堆子区图、门控、历史动量

### 改写方式
变成一个简单 schedule：
- `α_t, β_t, γ_t` 随时间变化
- 或对 `M_t` 做时序调制

一句话总结：
**保留 time-dependent schedule，删除 tri-phase kernel 这个大框架。**

---

# Part C：最终的新方法结构图

如果你后面重做论文/代码，我建议目录就长这样：

## 1. Introduction
- real image editing without source prompt
- challenge: local edit vs global preservation
- key idea: trajectory-derived dynamic soft mask

## 2. Related Work
- inversion for real image editing
- localized / mask-guided editing
- attention / feature control in diffusion editing

## 3. Method
### 3.1 Source-Aligned Inversion
### 3.2 Trajectory-Derived Dynamic Soft Mask
- discrepancy
- attention prior
- preservation prior
### 3.3 Step-wise Masked Editing Update
### 3.4 Time-Dependent Scheduling

## 4. Experiments
- comparisons with NTI/P2P, DiffEdit, MasaCtrl, Edit-friendly inversion
- ablations on mask source / dynamic schedule / injection position

---

# Part D：一句话版“保留-删除”总表

## 保留
- source-aligned inversion
- dynamic soft mask
- discrepancy-based localization
- source-preservation prior
- step-wise editing
- 简单时间调度

## 合并
- attention-based proposal + noise discrepancy + visual constraint  
  → 合并为 `D_t + A_t + C_t -> M_t`

- early/middle/late control  
  → 合并为 time-dependent weights

## 删除
- automatic edit phrase discovery（主线删除）
- edit/focus/support phrase taxonomy
- instance-group-aware replacement modeling
- replacement identity anchor
- replacement body envelope
- 多区域并行控制图命名体系

## 降级到附录/工程细节
- token 筛选
- prompt engineering
- 特殊 replacement 任务启发式
- 各种后处理和平滑技巧

---

# Part E：接下来最实用的下一步

我建议你下一步不要继续写方法描述了，而是直接进入**重建实现规划**。

最有用的是这两件事之一：

### 方案 1
我下一条直接帮你写：
## “基于 MasaCtrl / DDPM_inversion 的最小可行实现方案”
包括：
- 该缓存哪些 tensor
- `D_t / A_t / C_t` 怎么算
- `M_t` 在哪里生成
- 在哪一步做 masked blending

### 方案 2
我下一条直接帮你写：
## “新方法的伪代码 + 实验 ablation 设计”
包括：
- algorithm block
- 核心公式
- baseline
- 消融项

我建议先做 **方案 1**，因为你现在最需要的是“怎么从旧系统跳到一个可重做的新骨架”。  
如果你愿意，我下一条就直接给你：
**“基于已有代码重做的最小实现蓝图”**。

---
## 🧑‍💻 User

好的，给我吧

---
## 🤖 Assistant

下面给你一个 **可以直接开工的最小实现蓝图**。目标是：**不救旧系统，直接在清晰骨架上重做一个能出结果的 V1**。

我会优先按 **MasaCtrl 风格 / diffusers 风格** 来讲，因为最适合你做“每步控制 + 局部注入”。最后我也会给一个 **DDPM_inversion 版映射**。

---

# 0. 先定目标：V1 只做什么

## V1 必须实现的功能
1. 输入：
   - source image `I_s`
   - target prompt `y_t`
2. 对 `I_s` 做 inversion，得到 source trajectory/reference
3. 在 target-guided denoising 过程中，每步计算：
   - discrepancy map `D_t`
   - attention prior `A_t`
   - preservation prior `C_t`
4. 生成动态软掩码：
   - `M_t = f(D_t, A_t, C_t)`
5. 用 `M_t` 做一步 masked update：
   - `eps_blend = eps_src + M_t * (eps_tar - eps_src)`
6. 输出编辑结果

---

## V1 不做的功能
这些先全部砍掉：
- phrase discovery
- edit/focus/support phrase hierarchy
- replacement special branch
- identity anchor
- body envelope
- group-aware mask
- multi-zone policy system
- history momentum 那一堆联动

---

# 1. 推荐骨架：基于 MasaCtrl / diffusers 的最小架构

你可以把系统拆成 6 个部件：

```python
Editor
├── Inverter
├── AttentionStore
├── SourceReferenceCache
├── MaskBuilder
├── SchedulerController
└── Sampler
```

---

## 1.1 每个部件做什么

### A. `Inverter`
负责：
- 把 `I_s` 编码到 latent
- 做 DDIM inversion / NTI / edit-friendly inversion
- 输出：
  - `zT_src`
  - 每步参考 latent：`src_latents[t]`
  - 可选每步参考噪声：`src_eps[t]`

---

### B. `AttentionStore`
负责：
- 在 target-guided denoising 时 hook cross-attention
- 存储与 target token 对应的 attention map
- 聚合出 `A_t`

---

### C. `SourceReferenceCache`
负责存：
- `src_latents[t]`
- `src_eps[t]`（如果你预先算）
- 可选 `src_x0[t]`

本质就是 source-aligned reference。

---

### D. `MaskBuilder`
负责每步计算：
- `D_t`
- `A_t`
- `C_t`
- `M_t`

这是你的核心模块。

---

### E. `SchedulerController`
负责简单时间调度：
- early stronger preserve
- middle stronger edit
- late smoother mask

它只输出少量标量权重：
- `alpha_t`
- `beta_t`
- `gamma_t`
- 可选 `mask_gain_t`

---

### F. `Sampler`
负责 denoising loop：
- 跑 source branch / target branch
- 调 `MaskBuilder`
- 做 blended noise prediction
- 调 scheduler step 更新 latent

---

# 2. 最小数据流

我先给你一个最核心的数据流，照着实现就行。

---

## Step 1：source image inversion

输入图像 `I_s`：

```python
z0 = vae.encode(I_s)
zT_src, src_latents = invert(z0, prompt="", num_steps=T)
```

建议缓存：
- `src_latents[t]`: 每步反演轨迹 latent
- 如果方便，再缓存：
  - `src_eps[t]`
  - `src_x0[t]`

### 为什么缓存 `src_latents[t]`
因为后面你要构造 preservation prior，最稳妥的参照就是：
```python
drift_t = || z_t_current - src_latents[t] ||
```

---

## Step 2：开始 target-guided editing sampling

初始化：
- 最简单：从 `zT_src` 开始采样
- 即 source inversion 顶端 latent 作为编辑起点

```python
z_t = zT_src.clone()
for t in timesteps:
    ...
```

---

## Step 3：每步跑两个分支

### 3.1 source/preserve branch
你需要一个“保留参考”噪声预测：

```python
eps_src = unet(z_t, t, cond_src)
```

其中 `cond_src` 可以先用最简单版本：

#### 方案 A：空文本条件
```python
cond_src = null_prompt_embeds
```

#### 方案 B：弱源参考条件
如果你后面有图像反演特定条件，也可以用；但 V1 先别复杂化。

---

### 3.2 target/edit branch
```python
eps_tar = unet(z_t, t, cond_tar)
```

这里 `cond_tar = target_prompt_embeds`

---

# 3. 如何计算三个信号

---

## 3.1 Discrepancy map `D_t`

这是主信号。

### 最小实现
直接用噪声预测差：

```python
D_t = mean_channel(abs(eps_tar - eps_src))   # [B,1,h,w]
```

或者：
```python
D_t = l2_norm(eps_tar - eps_src, dim=channel)
```

### 为什么先用 `eps` 差
因为：
- 它计算简单
- 每步都自然可得
- 和 denoising update 直接相关

### 备选
后面你也可以试：
- `x0` prediction discrepancy
- latent update discrepancy
- guidance residual discrepancy

但 V1 先只用 `eps` 差。

---

## 3.2 Attention prior `A_t`

你需要从 target prompt 的 cross-attention 得到一个空间先验。

### 最小实现方式
在 U-Net 的 cross-attention 层 hook attention probability，然后：
- 选 target prompt 里 1~3 个主 token
- 对这些 token 的 attention map 在层间、头间求平均
- resize 到 latent resolution

伪代码：

```python
attn_maps = attention_store.get_cross_attention_maps(t)
token_ids = select_content_tokens(target_prompt)  # 最简单先选名词或手动指定主词
A_t = aggregate_token_attention(attn_maps, token_ids)  # [B,1,h,w]
A_t = normalize(A_t)
```

---

### V1 简化建议
你现在不要搞自动 phrase discovery。  
可以直接：

#### 方案 1：手工指定主 token
比如 prompt = `"a dog wearing sunglasses"`
你先只取 `dog`, `sunglasses`

#### 方案 2：简单规则自动取
- 去掉 stopwords
- 取名词 / 形容词
- 优先最后一个名词短语

但这属于工程，不是研究核心。

---

## 3.3 Preservation prior `C_t`

这是防止背景漂移的关键。

### 最小实现
用当前 latent 与 source trajectory 对应 latent 的偏移：

```python
drift = mean_channel(abs(z_t - src_latents[t]))
C_t = normalize_inverse(drift)  # 或者直接 normalize 后作为“应保留区域”分数
```

这里有两种定义方式：

---

### 定义法 A：`C_t` 表示“应保留强度”
那你希望：
- 和 source 更接近的地方，`C_t` 更高
- 更容易被抑制编辑

可以写成：

```python
drift = mean_channel(abs(z_t - src_latents[t]))
C_t = exp(-k * normalize(drift))
```

这样 drift 小的区域 `C_t` 高。

---

### 定义法 B：`C_t` 表示“不稳定风险”
那你就把 drift 大作为风险项再单独处理。

但为了和公式
\[
M_t = \sigma(\alpha D_t + \beta A_t - \gamma C_t)
\]
一致，建议 `C_t` 直接定义为 **preserve prior**，即数值越大越应该少编辑。

---

# 4. MaskBuilder：怎么融合成 `M_t`

---

## 4.1 最小公式
直接：

```python
logit = alpha_t * D_t + beta_t * A_t - gamma_t * C_t
M_t = sigmoid(kappa * normalize(logit))
```

建议最终 `M_t` shape：
```python
[B, 1, h, w]
```

然后 broadcast 到 latent channels。

---

## 4.2 加一个轻量平滑
建议你至少做两个小处理：

### 空间平滑
```python
M_t = gaussian_blur(M_t, kernel=3 or 5)
```

### 时间平滑
```python
M_t = rho * M_prev + (1-rho) * M_t
```

其中 `rho` 可以 0.3~0.6。

这样会比裸 mask 稳很多。

---

## 4.3 置信度裁剪
为了避免全图都被轻微编辑，建议做一个软阈值：

```python
M_t = relu(M_t - tau) / (1 - tau)
M_t = clamp(M_t, 0, 1)
```

这一步很有用，因为 discrepancy map 常会在全图都有一点响应。

---

# 5. 时间调度怎么做

不要复杂化。你只需要让权重随时间变化。

---

## 5.1 一个实用版本
设 diffusion 从大噪声到小噪声，归一化时间：
```python
s = t_idx / (T-1)   # 0~1
```

你可以定义：

### discrepancy 权重
中期更强：
```python
alpha_t = alpha_base * bell_curve(s)
```

### attention 权重
前中期较强：
```python
beta_t = beta_base * (1 - 0.5*s)
```

### preserve 权重
前期更强，后期逐渐减弱：
```python
gamma_t = gamma_base * (1.2 - s)
```

---

## 5.2 更简单版本
如果你不想搞 bell curve，就直接分线性：

```python
alpha_t = 0.5 + 0.5 * mid_boost(s)
beta_t  = 1.0
gamma_t = 1.2 - 0.7 * s
```

甚至最开始可以先固定：
```python
alpha_t, beta_t, gamma_t = const
```

V1 能跑起来最重要。

---

# 6. 最关键的注入位置：先用 `epsilon blending`

这是我最建议你 V1 用的注入方式。最简单，效果也通常最稳定。

---

## 6.1 核心公式
```python
eps_blend = eps_src + M_t * (eps_tar - eps_src)
```

等价于：
```python
eps_blend = (1 - M_t) * eps_src + M_t * eps_tar
```

注意：
- `M_t` 要 broadcast 到 `eps` 的 channel 维度
- `M_t` 分辨率应与 latent 一致

---

## 6.2 为什么先不用 attention gating
因为 attention gating 虽然更“高级”，但：
- 更难调
- 容易全模型行为变形
- 难定位问题是 mask 还是 attention 注入导致

而 `epsilon blending` 非常清晰：
- 你只是在每步决定“更像 source 还是更像 target”

很适合做第一版论文原型。

---

# 7. 最小采样伪代码

下面这个伪代码就是你 V1 的核心。

```python
def edit_image(source_image, target_prompt, num_steps):
    # 1) encode and invert
    z0 = vae.encode(source_image)
    zT_src, src_latents = invert(z0, null_prompt, num_steps)

    # 2) prepare conditions
    cond_tar = text_encoder(target_prompt)
    cond_src = text_encoder("")  # simplest preserve branch

    # 3) initialize
    z_t = zT_src.clone()
    M_prev = None

    for i, t in enumerate(timesteps):
        # 4) run two branches
        eps_src = unet(z_t, t, encoder_hidden_states=cond_src).sample
        eps_tar = unet(z_t, t, encoder_hidden_states=cond_tar).sample

        # 5) discrepancy map
        D_t = channel_mean(abs(eps_tar - eps_src))  # [B,1,h,w]
        D_t = normalize(D_t)

        # 6) attention prior
        A_t = attention_store.aggregate(t, target_token_ids)  # [B,1,h,w]
        A_t = normalize(A_t)

        # 7) preservation prior
        drift_t = channel_mean(abs(z_t - src_latents[t]))
        C_t = torch.exp(-k * normalize(drift_t))  # higher => preserve more

        # 8) time-dependent weights
        alpha_t, beta_t, gamma_t = schedule(i, num_steps)

        # 9) build mask
        logits = alpha_t * D_t + beta_t * A_t - gamma_t * C_t
        M_t = torch.sigmoid(kappa * normalize(logits))

        # optional smoothing
        M_t = gaussian_blur(M_t)
        if M_prev is not None:
            M_t = rho * M_prev + (1-rho) * M_t
        M_prev = M_t

        # optional soft threshold
        M_t = torch.clamp((M_t - tau) / (1 - tau), 0, 1)

        # 10) epsilon blending
        M_expand = M_t.expand_as(eps_src)
        eps_blend = eps_src + M_expand * (eps_tar - eps_src)

        # 11) scheduler update
        z_t = scheduler.step(eps_blend, t, z_t).prev_sample

    # 12) decode
    edited_image = vae.decode(z_t)
    return edited_image
```

---

# 8. 在 MasaCtrl / diffusers 里具体改哪里

因为不同仓库文件结构不同，我先按 **diffusers 常见结构** 说“改动点类别”，你对着仓库文件名去映射。

---

## 8.1 你要找的核心入口

### 入口 1：inversion 脚本/函数
你要拿到：
- `zT_src`
- `src_latents[t]`

常见位置：
- `run_editing_*.py`
- `inversion.py`
- `utils/inversion.py`
- notebook 里的 inversion helper

---

### 入口 2：采样主循环
你要找到类似：

```python
for i, t in enumerate(scheduler.timesteps):
    noise_pred = unet(...)
    latents = scheduler.step(noise_pred, t, latents).prev_sample
```

你要把它改造成：
- 调两次 unet：`eps_src`, `eps_tar`
- 中间插入 `MaskBuilder`
- 用 `eps_blend` 替换原始 `noise_pred`

这个是最重要的改动点。

---

### 入口 3：attention hook / processor
如果仓库已经支持 attention processor 注册，那很好。

你要做的是：
- 只存 attention，不改 attention
- 先别在 attention 层做复杂控制

你需要一个类类似：

```python
class AttentionStore:
    def __init__(self):
        self.cross_attn = {}

    def __call__(self, attn_probs, is_cross, place_in_unet, t):
        if is_cross:
            self.cross_attn.setdefault(t, []).append(attn_probs.detach())

    def aggregate(self, t, token_ids):
        ...
```

---

## 8.2 推荐的最小改法
### 只加三个新文件/模块
1. `mask_builder.py`
2. `attention_store.py`
3. `editor_pipeline.py` 或改原有 editing script

---

## 8.3 一个干净的类设计
```python
class DynamicMaskBuilder:
    def __init__(self, config):
        ...

    def discrepancy(self, eps_src, eps_tar):
        ...

    def attention_prior(self, attention_store, t, token_ids, out_shape):
        ...

    def preserve_prior(self, z_t, z_src_t):
        ...

    def build(self, eps_src, eps_tar, z_t, z_src_t, attention_store, t, step_idx):
        return M_t, aux_dict
```

这样你后面做 ablation 很方便。

---

# 9. 如果你基于 DDPM_inversion 改，怎么映射

如果你最后发现 MasaCtrl 工程上不顺，DDPM_inversion 也可以。

---

## 9.1 在 DDPM_inversion 里，你要找的东西
你要找到：
- inversion 返回的 latent trajectory
- manipulation / editing 的 denoising loop
- P2P 或原方法的控制位置

---

## 9.2 最小改法
把原本单一路径编辑改成双分支：

### 原始可能是：
```python
eps = model(z_t, t, cond_tar)
z_t = step(eps)
```

### 改成：
```python
eps_src = model(z_t, t, cond_src)
eps_tar = model(z_t, t, cond_tar)
M_t = build_mask(...)
eps = eps_src + M_t * (eps_tar - eps_src)
z_t = step(eps)
```

---

## 9.3 DDPM_inversion 的优势
- 它本身更贴“反演轨迹”
- 你可以更自然地访问 source-aligned latent path

## 9.4 不足
- attention 抽取和模块插拔可能不如 diffusers 顺
- 工程可扩展性通常弱一点

---

# 10. 你第一周应该产出的中间可视化

这个非常重要。你必须先做可视化，而不是先追最终图像效果。

---

## 每步至少存这些图
对若干代表性 timestep：

1. `D_t`
2. `A_t`
3. `C_t`
4. `M_t`
5. `|eps_tar - eps_src|`
6. 当前编辑图像预览（可每几步 decode 一次）

---

## 为什么必须看这些
因为你方法能不能成立，核心就取决于：

### 你要验证三件事
1. `D_t` 是否真的在编辑对象附近更高
2. `A_t` 是否能给出基本语义位置
3. `M_t` 是否只在真正应编辑区域亮起，而不是全图泛化

如果这三件事不成立，继续堆模块是没意义的。

---

# 11. 最小实验设计

你现在先不要想太大 benchmark，先做最小验证。

---

## 11.1 Baseline
至少比这几个：

1. **target-only editing**
   - 直接从 `zT_src` 开始，用 target prompt 采样
2. **source-preserve only**
   - 强 source branch，几乎不编辑
3. **global blend**
   - 不用空间 mask，只用全局 scalar blending
4. **your dynamic mask**
   - `eps_src + M_t * (eps_tar - eps_src)`

这样你就能证明：
- 不是因为双分支就有效
- 而是因为**空间动态 mask**有效

---

## 11.2 Ablation
最少做这四个：

### A1. 去掉 attention prior
\[
M_t = f(D_t, C_t)
\]

### A2. 去掉 preservation prior
\[
M_t = f(D_t, A_t)
\]

### A3. 静态 mask 替代动态 mask
比如全程用某一步平均 mask

### A4. 去掉时间调度
固定 `alpha,beta,gamma`

这四个已经足够说明你的点。

---

# 12. 你实现时最容易踩的坑

---

## 坑 1：`eps_src` 选空 prompt 可能太弱
这是真的会发生。  
如果空 prompt 导致 preserve branch 不稳，你有两个替代：

### 替代 A
使用 inversion 路径相关条件/重建条件

### 替代 B
直接用 source trajectory 做 latent anchoring，而不是只靠 `eps_src`

例如在 scheduler step 后加：
```python
z_t = z_t + lambda_anchor * (1 - M_t) * (src_latents[t-1] - z_t)
```

但这个属于 V1.5，先别急。

---

## 坑 2：attention map 分辨率和 latent 不匹配
要统一 resize 到 latent 尺寸，比如 `64x64`。

---

## 坑 3：`D_t` 会全图发亮
这是最常见问题。解决：
- normalize 前先按样本做分位数裁剪
- 加 `A_t`
- 加 soft threshold `tau`
- 加时间平滑

---

## 坑 4：mask 太硬导致边界裂开
解决：
- soft mask，不要 binary
- blur 一下
- late step 降低 mask 增益

---

## 坑 5：两次 unet 开销翻倍
是的，这是代价。  
但 V1 先追正确性，不追速度。之后可以考虑：
- 共用部分前向
- 减少 attention 存储
- 减少可视化频率

---

# 13. 建议你先实现的三个版本

---

## V1.0：只用 discrepancy
最简：

\[
M_t = \sigma(\alpha D_t)
\]

看看是否已经能定位编辑区域。

---

## V1.1：discrepancy + attention
\[
M_t = \sigma(\alpha D_t + \beta A_t)
\]

看是不是更聚焦。

---

## V1.2：discrepancy + attention + preserve
\[
M_t = \sigma(\alpha D_t + \beta A_t - \gamma C_t)
\]

这个才是完整版本。

---

# 14. 最后给你一个实际开工顺序

按这个顺序做，不容易乱：

### 第 1 步
跑通 source inversion + target-only editing

### 第 2 步
在 denoising loop 中拿到：
- `eps_src`
- `eps_tar`

### 第 3 步
做 `D_t` 可视化

### 第 4 步
接 attention store，做 `A_t` 可视化

### 第 5 步
接 `C_t`

### 第 6 步
生成 `M_t`

### 第 7 步
做 `eps_blend`

### 第 8 步
做 4 个 ablation

这是最稳的路线。

---

# 15. 我给你的最终建议：先选一个明确实现口径

如果你现在问我“具体应该先按哪个口径写代码”，我建议你直接这样定：

## 你的 V1 方法定义
- **骨架**：MasaCtrl / diffusers 风格采样循环
- **反演**：DDIM inversion 或现成 inversion
- **掩码主信号**：`eps` discrepancy
- **语义先验**：cross-attention token aggregation
- **保留先验**：current latent 与 source trajectory drift
- **注入位置**：`epsilon blending`
- **调度**：简单时间权重
- **不做**：任何 phrase system / replacement system / 多区图系统

---

如果你愿意，我下一条可以继续直接给你两种特别具体的内容中的一个：

### 选项 1：
**给你写成伪代码级模块接口设计**
比如：
- `compute_discrepancy_map()`
- `aggregate_cross_attention()`
- `build_mask()`
- `edit_step()`

### 选项 2：
**按你选定的 repo 给“文件级修改方案”**
比如如果你决定用 MasaCtrl，我就按仓库结构告诉你：
- 哪个文件加类
- 哪个循环改成双分支
- attention hook 放哪
- mask 保存在哪

如果你已经决定用哪个 repo，我建议下一条你直接告诉我：  
**“我准备用 MasaCtrl”** 或 **“我准备用 DDPM_inversion”**，我就能继续给你文件级改造方案。

---
## 🧑‍💻 User

那我用到了MasaCtrl的什么啊，这跟我自己用diffuser搭一个的差别在哪

---
## 🤖 Assistant

你这个问题非常关键。  
短答案是：

## 短答
**如果你现在的方法核心是“source inversion + 每步双分支 + 动态 mask + epsilon blending”，那你其实不一定“用到了 MasaCtrl 的核心方法”。**  
你更多是：

- 可以**借它的工程骨架**
- 借它“真实图像编辑 + 反演后采样控制”的任务形态
- 借它一些 attention hook / 采样组织方式

但**你的核心贡献并不依赖 MasaCtrl**。

---

# 1. 你到底“用到了 MasaCtrl 的什么”

先把 MasaCtrl 拆开看。它本质上有两层：

## 层 1：任务骨架
它处理的是：
- real image editing
- source image inversion
- 扩散过程中的受控编辑
- 保持 identity / layout / non-edited region consistency

这一层和你是相似的。

---

## 层 2：核心技术点
MasaCtrl 真正标志性的点一般是：
- 在采样过程中做 **mutual self-attention control**
- 让 source / edited generation 在 attention 特征层面对齐
- 借 attention correspondence 保持结构与身份一致性

这一层和你现在想做的核心 **不一样**。

你的核心是：
- 从 **trajectory discrepancy** 估计 `M_t`
- 用 `M_t` 控制 **noise/update blending**

所以如果很严格地说：

> 你不是在“用 MasaCtrl 的核心方法做改进”，  
> 你是在“借一个适合真实图像编辑的现成采样工程壳子”。

---

# 2. 那和你自己用 diffusers 搭一个，有什么差别

这个要分两种情况说。

---

## 情况 A：你自己已经很熟 diffusers，能稳定搭 inversion + 双分支采样 + attention hook
那差别其实**不大**。  
甚至我会更建议你**直接自己搭**。

因为你的方法主干并不依赖 MasaCtrl 的 attention control 机制。  
你真正需要的只是：

1. 一个能做 source inversion 的流程
2. 一个可控的 denoising loop
3. 一个能抓取 cross-attention 的接口
4. 一个能在每步替换 `noise_pred` 的地方

这些用 diffusers 原生就能做。

### 这时用 MasaCtrl 的劣势
- 它自带一套方法假设
- 代码里常混有 mutual self-attention 注入逻辑
- 你会花时间理解“哪些是它的方法必须，哪些只是骨架”
- 容易把你的主线搞脏

所以如果你自己能搭，**自己搭通常更干净**。

---

## 情况 B：你现在没有一套稳定的真实图像编辑脚手架
那 MasaCtrl 的价值在于：

### 它能帮你省下的东西
- 已经有 image inversion + editing 的任务组织
- 已经把 prompt / latent / timestep / decode 这些流程串起来了
- 可能已经有 attention storage / hook 机制
- 已经有一些真实图像编辑时会遇到的坑的处理方式

### 它相当于什么
相当于你不是从“空白 diffusers pipeline”开始，而是从一个：
- 面向 image editing
- 已经跑通过真实图像输入
- 已经有 sampling control 接口

的 baseline 开始。

---

# 3. 本质区别：你是要“借论文”，还是“借代码”

这个也要分清。

---

## 3.1 借 MasaCtrl 的论文思路？
**不建议。**

因为你的方法核心不在 mutual self-attention consistency。  
如果你硬说“基于 MasaCtrl”，容易出现叙事问题：

- 别人会问：你到底继承了 MasaCtrl 的什么？
- 你的方法真正创新点又不在它的核心控制机制上
- 容易变成“和 MasaCtrl 并列的另一个控制方法”，而不是自然扩展

所以在论文叙事上，MasaCtrl 更适合做：
- baseline
- related work
- 或工程参考

不一定适合做你的“方法祖宗”。

---

## 3.2 借 MasaCtrl 的代码骨架？
**可以。**

因为代码骨架只要求：
- 输入输出流程合适
- 便于插入你的模块
- 少踩坑

在这个意义上，它和你自己搭 diffusers 的差别主要是：
- **开发速度**
- **调试成本**
- **已有编辑流程成熟度**

---

# 4. 你的方法和 MasaCtrl 的真正关系

如果我帮你严谨地定义，可以这么说：

## 你的方法
- editing signal 来源：**source-target trajectory discrepancy**
- spatial control mechanism：**dynamic soft mask**
- update mechanism：**masked blending in denoising step**

## MasaCtrl
- consistency signal 来源：**mutual self-attention correspondence**
- spatial/structural control mechanism：**attention sharing/control**
- update mechanism：**attention-level feature control**

所以：

> 你们解决的是相近任务，  
> 但核心控制变量不一样。

换句话说，MasaCtrl 对你最有价值的地方，不是“方法思想直接继承”，而是：

- 它证明了“在真实图像编辑里，逐步控制比一次性重生成更有效”
- 它提供了一个接近你任务形态的工程模板

---

# 5. 如果你自己用 diffusers 搭，和基于 MasaCtrl 改，差别具体在哪

我从最实际的工程维度说。

---

## 5.1 你自己搭 diffusers 的优点

### 优点 1：方法边界最干净
你不会混进 MasaCtrl 的控制逻辑。  
最后论文里也更容易说：

> We implement our method on top of a standard latent diffusion editing pipeline.

这个很干净。

---

### 优点 2：代码更适合你的方法
你的核心只需要：
- inversion
- two-branch unet forward
- attention extraction
- mask build
- blended scheduler update

这些你自己搭会非常直。

---

### 优点 3：后面做 ablation 更方便
因为你没有 inherited trick。  
比如你想测：
- only D_t
- D_t + A_t
- D_t + A_t + C_t

自己搭最省事。

---

## 5.2 你自己搭 diffusers 的缺点

### 缺点 1：前期要补基础设施
你得自己搞定：
- inversion
- attention hook
- prompt embedding / cfg
- latent decode
- 保存中间结果

### 缺点 2：真实图像编辑的一些坑要自己踩
比如：
- inversion 不稳
- latent 对齐问题
- scheduler timestep 映射
- attention map 的尺寸和层级选择

---

## 5.3 基于 MasaCtrl 改的优点

### 优点 1：真实图像编辑流程现成
这是最大优点。

### 优点 2：如果它已经有 attention 存储和 feature hook，会省事
你做 `A_t` 会更快。

### 优点 3：有时它已经处理好了 inversion / generation 的对接
这个很烦但很重要。

---

## 5.4 基于 MasaCtrl 改的缺点

### 缺点 1：你要先“剥离”它原本的方法控制
否则你会得到：
- 你的 mask 控制
- 它的 mutual self-attention control
- 两套机制一起作用

这样结果不可解释。

---

### 缺点 2：代码语义不属于你
你会一直问：
- 这一步是因为我的 `M_t`，还是因为它默认 attention 控制？
- 这个效果是谁带来的？

这对研究非常不利。

---

### 缺点 3：论文叙事会模糊
你很容易陷入：
> 我们在 MasaCtrl 基础上加入了 trajectory mask

但审稿人可能会想：
- 所以你的增益是不是主要因为 MasaCtrl 仍然在工作？
- 如果关掉 MasaCtrl 核心模块，你的方法还能成立吗？

这会强迫你做更多额外 ablation。

---

# 6. 所以你现在到底该选哪个

我给你一个非常直接的判断标准。

---

## 选 “自己搭 diffusers” 的条件
如果你满足下面任意两条，我建议你自己搭：

- 你已经能跑通 stable diffusion 的基本采样
- 你已经做过 inversion 或能复用 inversion 代码
- 你能改 U-Net forward / attention processor
- 你希望方法边界清楚，后面写论文更干净
- 你不想背 MasaCtrl 的历史包袱

### 这种情况下
**自己搭更适合你。**

---

## 选 “基于 MasaCtrl 改” 的条件
如果你更接近这种情况，可以考虑先基于它：

- 你现在就有一套 MasaCtrl 跑通环境
- 它的真实图像编辑流程已经稳定
- 你目前最缺的是“先跑出一个能看的版本”
- 你愿意后面再把它剥离重构

### 这种情况下
可以先：
> 用 MasaCtrl 当工程跳板验证想法，  
> 但不要把最终系统长期绑定在它上面。

---

# 7. 我更建议你的路线

基于你前面说的情况，我其实更倾向于：

## 最佳路线
### 论文方法上：
**不要说自己是基于 MasaCtrl 方法。**

### 工程实现上：
有两种可行策略：

#### 策略 A：直接自己用 diffusers 搭
如果你能力允许，这是最好的。

#### 策略 B：先借 MasaCtrl 跑出 V0，再尽快迁到干净 diffusers 实现
如果你现在赶时间，这是最现实的。

---

# 8. 你可以怎么理解“和 MasaCtrl 的差别”

一句话概括：

### 如果你自己搭 diffusers
你是在做：
> 一个以 trajectory-derived soft mask 为核心的全新编辑 pipeline

### 如果你基于 MasaCtrl 改
你更像是在做：
> 在已有真实图像编辑框架中，替换其核心控制策略为 trajectory-mask-guided denoising

前者更适合做研究主线。  
后者更适合做快速原型。

---

# 9. 我帮你做个非常明确的结论

## 你“用到了 MasaCtrl 的什么”？
最多是：
- 真实图像编辑任务骨架
- inversion 后的采样流程
- 可能的 attention hook 工具
- 某些工程组织方式

**不是它的核心方法贡献。**

---

## 跟“自己用 diffusers 搭一个”的差别是什么？
本质差别不是方法，而是：

- 开发起点
- 工程复杂度
- 是否背已有方法包袱
- 最终论文叙事是否干净

---

## 我对你的建议
如果你能自己搭，**就自己搭**。  
因为你现在已经把方法核心收敛到一个很清楚的东西了：

- inversion
- discrepancy
- attention prior
- preservation prior
- dynamic soft mask
- epsilon blending

这套东西**完全可以独立于 MasaCtrl 存在**。

---

如果你愿意，我下一条可以直接继续给你：

### 选项 A
**“从零用 diffusers 搭这个方法的最小代码结构”**
我会给你：
- 目录结构
- 核心类
- 每个函数接口
- forward 数据流

### 选项 B
**“如果仍然想借 MasaCtrl，怎么把它剥成只剩工程骨架”**
我会告诉你：
- 哪些模块必须关掉
- 哪些 attention control 不能保留
- 怎么避免结果被它原方法污染

我建议你现在走 **A**。  
如果你同意，我下一条就直接给你一个 **从零用 diffusers 搭建的最小工程结构图 + 模块接口**。

---
## 🧑‍💻 User

那借用NTI或者P2P呢

---
## 🤖 Assistant

可以，而且**比借 MasaCtrl 更合理**。

## 结论先说
对你现在这套方法来说：

- **P2P/NTI 更适合借“编辑骨架”**
- **MasaCtrl 更适合当 baseline 或工程参考**
- 如果你想让你的方法叙事更自然，**“基于 inversion + prompt-guided editing” 这条线比 “基于 MasaCtrl” 顺得多**

因为你的方法本质上更像是在回答：

> 在没有 source prompt、没有人工 mask 的情况下，  
> 如何在 inversion-based real image editing 中动态定位编辑区域并稳定注入目标语义？

这个问题和 **NTI / P2P 家族** 的关联，比和 MasaCtrl 更强。

---

# 1. 为什么 NTI / P2P 跟你更搭

---

## 1.1 P2P/NTI 的基本范式和你很接近
它们的世界观是：

1. 先把真实图像拉到 diffusion latent 轨道上
2. 再在去噪过程中施加文本控制
3. 希望局部改、全局稳

这和你的基本流程高度一致。

---

## 1.2 你的方法像是 P2P/NTI 的“无 source prompt 局部化扩展”
P2P 类方法常依赖：
- source prompt
- target prompt
- attention map 替换/重加权
- 文本差分定位编辑内容

而你现在的关键点正好是：

- **没有 source prompt**
- 不能做传统 prompt-to-prompt 对齐
- 所以你要用：
  - source inversion trajectory
  - target attention
  - discrepancy map
  来替代 prompt 差分

这在叙事上就很自然：

> P2P 需要 source/target prompt correspondence，  
> 而我们研究的是 no-source-prompt real image editing；  
> 因此我们用 trajectory-derived dynamic masking 替代 explicit prompt correspondence.

这个逻辑非常顺。

---

## 1.3 NTI 更像你的“基础设施来源”
NTI 的主要价值在于：
- 更好地反演真实图像
- 为后续文本编辑提供更稳定的起点

你的方法很需要这个基础。  
而且你完全可以说：

> We build upon inversion-based real image editing pipelines such as DDIM inversion / Null-text inversion.

这就比说“我们基于 MasaCtrl”自然很多。

---

# 2. 借 NTI 和借 P2P，分别适合借什么

---

## 2.1 借 NTI：借的是“真实图像反演基础”
你可以借 NTI 的：

- inversion pipeline
- null-text optimization 后的 editing 起点
- real-image faithful reconstruction

### 适合你借的部分
- `I_s -> latent trajectory`
- 更稳定的 source reconstruction
- 更贴近真实图像的 source-aligned initialization

### 不适合直接借来当你核心的部分
NTI 本身不是你的编辑控制机制。  
它更多是“编辑前提设施”。

所以在你的框架里，NTI 更像：

> source-aligned inversion backend

而不是：

> editing method backbone

---

## 2.2 借 P2P：借的是“采样中逐步控制”的编辑形式
P2P 的核心是：
- 在 denoising 过程中控制 cross-attention
- 用 source/target prompt 对齐实现局部或结构化编辑

### 适合你借的部分
- 编辑循环组织方式
- attention extraction
- prompt-guided denoising structure
- 逐步控制而非一次性重生成

### 你要替换掉的部分
- source prompt / target prompt 对齐
- token replacement logic
- attention replacement/refinement 的核心假设

因为你没有 source prompt。

---

# 3. 如果要严谨地说，和 P2P 的关系是什么

你可以这样理解：

## P2P 的定位方式
“通过 source/target prompt 的 attention correspondence 推断改哪里”

## 你的定位方式
“通过 source inversion trajectory 与 target-guided update 的 discrepancy 推断改哪里”

所以你其实是在做一种：

> **Prompt-to-Prompt without source prompt**
> 或者更准确地说：
> **Trajectory-guided localized editing for no-source-prompt real image editing**

这比挂在 MasaCtrl 名下更容易让人理解。

---

# 4. 工程上借 NTI/P2P 和自己搭 diffusers 的差别

---

## 4.1 借 NTI/P2P 的好处

### 好处 1：你的问题设定和它们血缘更近
尤其是：
- inversion-based real image editing
- denoising-time control
- 保持结构与局部编辑

### 好处 2：更好写论文
你可以在方法动机里自然地说：

- P2P 依赖 source prompt correspondence
- NTI 提供真实图像反演能力
- 但在 no-source-prompt 场景下，缺少显式文本差分
- 因此我们提出 trajectory-derived dynamic masking

这个逻辑特别自然。

---

### 好处 3：代码上往往更“轻”
相较于 MasaCtrl，那种额外 self-attention control 负担更少。  
P2P/NTI 的框架通常更接近你真正要做的事情。

---

## 4.2 借 NTI/P2P 的坏处

### 坏处 1：P2P 很多代码默认有 source prompt
你要拆掉这些逻辑。
比如：
- token alignment
- word swap map
- attention replace schedule

这些你都不能直接用。

---

### 坏处 2：NTI 代码有时更偏“反演工具”，不是干净 pipeline
也就是说：
- inversion 部分好用
- editing loop 可能没那么模块化

你得自己把反演和编辑串起来。

---

# 5. 如果你问我“最该借谁”

我会这样排：

## 第一选择：借 NTI 的 inversion，自己写 editing loop
这是我最推荐的。

原因：
- 你的方法最核心的是编辑控制，不是 inversion 本身
- NTI 给你一个强的 real-image start point
- 你自己写 loop，方法边界最干净

这条路线是：

> NTI as inversion backend  
> + your dynamic-mask editing loop

我觉得这是最漂亮的。

---

## 第二选择：借 P2P 的 denoising loop 和 attention extraction，但去掉 source-prompt 对齐逻辑
这也可以。

这条路线是：

> P2P-style prompt-guided iterative editing  
> but replace prompt correspondence with trajectory discrepancy masking

这在论文叙事上也很好。

---

## 第三选择：纯 diffusers 自己搭
这个也很好，尤其代码最干净。  
但如果你希望“和已有方法谱系更接近”，那 NTI/P2P 的血缘会更自然。

---

## 第四选择：借 MasaCtrl
不是不能借，但优先级低于前面三个。

---

# 6. 你如果借 P2P，需要明确哪些东西不能继承

这个特别重要。

---

## 不能直接继承的 P2P 核心假设
1. **source prompt 存在**
2. **source token 和 target token 可对齐**
3. **替换 token attention 就能得到区域控制**
4. **编辑区域主要来自 prompt 差分**

这些在你问题里都不成立，或者不充分。

---

## 可以继承的部分
1. denoising-time editing 范式
2. cross-attention extraction
3. token-level target semantic support
4. step-wise control schedule

---

# 7. 你如果借 NTI，需要明确它在你方法里是什么角色

最合适的表述不是：

> 我们基于 NTI 做编辑

而是：

> We use NTI (or DDIM inversion) to obtain a source-aligned latent trajectory, which serves as the structural reference for dynamic mask estimation and step-wise preservation.

也就是说：

- NTI 是你的 **source-aligned inversion module**
- 不是你的主要方法贡献

这样最稳。

---

# 8. 我帮你直接做个选择建议

---

## 如果你更关心“论文叙事顺不顺”
选：
### **NTI + 你自己的 editing loop**

因为它最容易讲成：
- inversion-based real image editing
- no source prompt
- dynamic mask from trajectory discrepancy

---

## 如果你更关心“代码开工快”
选：
### **P2P 风格 loop + 自己替换核心控制**
前提是你愿意拆 source prompt 逻辑。

---

## 如果你更关心“最干净、最可控”
选：
### **纯 diffusers + 借 NTI inversion 实现**
这是工程上和研究上都很稳的路线。

---

# 9. 最终一句话结论

## 能不能借 NTI 或 P2P？
**能，而且比借 MasaCtrl 更合适。**

## 借谁更好？
- **借 NTI**：更适合当 inversion backend
- **借 P2P**：更适合当 editing loop 参考
- **最推荐**：NTI inversion + 你自己写 dynamic-mask denoising loop

---

如果你愿意，我下一条可以直接继续给你其中一个：

### 选项 A
**“如果以 NTI 为底座，你的方法应该怎么组织模块”**

### 选项 B
**“如果以 P2P 为底座，哪些模块保留，哪些必须删”**

### 选项 C
**“NTI vs P2P vs 纯 diffusers，按你的方法需求做一个具体对比表”**

我建议你下一步看 **C**，因为这样你可以马上决定工程路线。

---
## 🧑‍💻 User

先按照你推荐的来

---
## 🤖 Assistant

好，那就按我最推荐的路线来：

# 路线
## **NTI 作为 inversion backend + 你自己写 editing loop**

这是目前对你最合适的组合，因为它把问题拆得很清楚：

- **NTI 负责**：把真实图像稳定拉进扩散轨道
- **你的方法负责**：在 denoising 过程中，用 trajectory discrepancy + attention + preservation 构造动态 mask 来做局部编辑

这样：
- 方法边界清楚
- 论文叙事自然
- 工程上也不会背 P2P/MasaCtrl 的多余包袱

---

# 1. 整体系统怎么定义

你的系统可以定义成 2 层：

## Layer A：Source-aligned inversion
输入 source image `I_s`  
输出：
- `z_T^src`
- source latent trajectory `z_t^src`
- 可选 source null embeddings / unconditional embeddings（如果你沿用 NTI）

这一层就是 NTI 提供的基础设施。

---

## Layer B：Dynamic-mask editing loop
从 `z_T^src` 开始，在 target prompt 引导下逐步去噪。  
每一步：
1. 计算 preserve/reference branch
2. 计算 target/edit branch
3. 估计 discrepancy map
4. 聚合 target attention prior
5. 计算 preservation prior
6. 生成 soft mask `M_t`
7. 用 `M_t` 做 noise/update blending
8. scheduler 更新到下一步

这层就是你的核心方法。

---

# 2. 你该如何描述这个方法

建议你从现在开始就用下面这种语言统一自己思路：

## 不是：
- 基于 MasaCtrl
- 基于 P2P 改出来的一个变体

## 而是：
- **An inversion-based real image editing framework**
- **with trajectory-derived dynamic localization**
- **under no-source-prompt setting**

如果写成一句简单中文就是：

> 我们用 NTI 获得真实图像的可编辑反演轨迹，再在目标文本引导的逐步去噪中，通过 source-target discrepancy、target attention 和 source-preservation prior 构造动态软掩码，实现无需 source prompt 的局部可控编辑。

这个定义很稳。

---

# 3. 工程结构：最小项目目录

你现在就按这个目录组织最省事：

```bash
project/
├── configs/
│   └── edit_config.yaml
├── models/
│   └── nti_wrapper.py
├── pipelines/
│   └── dynamic_mask_editor.py
├── modules/
│   ├── attention_store.py
│   ├── mask_builder.py
│   ├── schedulers.py
│   └── utils.py
├── scripts/
│   ├── run_inversion.py
│   ├── run_edit.py
│   └── visualize_maps.py
└── outputs/
```

---

# 4. 每个模块负责什么

---

## 4.1 `models/nti_wrapper.py`
这个模块只做一件事：

### 输入
- source image
- optional prompt（通常空字符串或弱描述）
- diffusion steps

### 输出
至少要有：

```python
{
    "zT_src": ...,
    "src_latents": [...],   # 每步 latent
    "null_embeddings": ..., # 如果 NTI 需要每步 uncond embedding
}
```

如果你能拿到更多，也可以存：
```python
{
    "src_eps": [...],
    "src_x0": [...],
}
```

但不是必须。

---

## 4.2 `modules/attention_store.py`
负责从 U-Net cross-attention 中拿 target token 的空间响应。

### 最小接口
```python
class AttentionStore:
    def reset(self): ...
    def register_to_unet(self, unet): ...
    def aggregate(self, token_ids, out_h, out_w): ...
```

### V1 只做
- 存 cross-attention
- 不做 attention replacement
- 不做 self-attention control
- 不修改模型行为

它只是观察器，不是控制器。

---

## 4.3 `modules/mask_builder.py`
这是你的核心。

### 输入
- `eps_src`
- `eps_tar`
- `z_t`
- `z_t_src_ref`
- `attention_store`
- `token_ids`
- `step_idx`

### 输出
- `M_t`
- 中间结果（便于可视化）：
  - `D_t`
  - `A_t`
  - `C_t`

---

## 4.4 `pipelines/dynamic_mask_editor.py`
这个模块负责总控 denoising loop。

### 它做的事
1. 调 NTI 拿 source inversion 结果
2. 准备 target prompt embedding
3. 每步做双分支 forward
4. 调 `mask_builder`
5. 用 `M_t` 融合噪声预测
6. 调 scheduler 更新 latent
7. 最后 decode

---

# 5. 你真正要写的核心接口

下面这些接口，你可以直接照着实现。

---

## 5.1 NTI wrapper

```python
class NTIInverter:
    def __init__(self, pipe, num_steps=50):
        self.pipe = pipe
        self.num_steps = num_steps

    def invert(self, image, prompt=""):
        """
        Returns:
            zT_src: Tensor [B,C,H,W]
            src_latents: list[Tensor], len=T
            null_embeddings: optional
        """
        ...
        return {
            "zT_src": zT_src,
            "src_latents": src_latents,
            "null_embeddings": null_embeddings,
        }
```

---

## 5.2 Attention store

```python
class AttentionStore:
    def __init__(self):
        self.maps = []

    def reset(self):
        self.maps = []

    def register_to_unet(self, unet):
        # hook cross-attn probs
        ...

    def aggregate(self, token_ids, out_size):
        """
        Returns:
            A_t: [B,1,H,W]
        """
        ...
```

---

## 5.3 Mask builder

```python
class DynamicMaskBuilder:
    def __init__(self, config):
        self.kappa = config.kappa
        self.tau = config.tau
        self.rho = config.rho
        self.prev_mask = None

    def discrepancy(self, eps_src, eps_tar):
        D = (eps_tar - eps_src).abs().mean(dim=1, keepdim=True)
        return normalize_map(D)

    def attention_prior(self, attention_store, token_ids, out_size):
        A = attention_store.aggregate(token_ids, out_size)
        return normalize_map(A)

    def preservation_prior(self, z_t, z_src_t, k=3.0):
        drift = (z_t - z_src_t).abs().mean(dim=1, keepdim=True)
        drift = normalize_map(drift)
        C = torch.exp(-k * drift)
        return C

    def build(self, eps_src, eps_tar, z_t, z_src_t, attention_store, token_ids, step_idx, total_steps):
        D = self.discrepancy(eps_src, eps_tar)
        A = self.attention_prior(attention_store, token_ids, D.shape[-2:])
        C = self.preservation_prior(z_t, z_src_t)

        alpha_t, beta_t, gamma_t = get_time_weights(step_idx, total_steps)

        logits = alpha_t * D + beta_t * A - gamma_t * C
        M = torch.sigmoid(self.kappa * normalize_map(logits))
        M = gaussian_smooth(M)

        if self.prev_mask is not None:
            M = self.rho * self.prev_mask + (1 - self.rho) * M
        self.prev_mask = M.detach()

        M = torch.clamp((M - self.tau) / (1 - self.tau), 0, 1)

        return M, {"D": D, "A": A, "C": C}
```

---

## 5.4 Editor pipeline

```python
class DynamicMaskEditor:
    def __init__(self, pipe, inverter, mask_builder, attention_store):
        self.pipe = pipe
        self.inverter = inverter
        self.mask_builder = mask_builder
        self.attention_store = attention_store

    @torch.no_grad()
    def edit(self, source_image, target_prompt, token_ids, num_steps=50):
        inv = self.inverter.invert(source_image, prompt="")
        z_t = inv["zT_src"].clone()
        src_latents = inv["src_latents"]

        cond_tar = self.pipe.encode_prompt(target_prompt)
        cond_src = self.pipe.encode_prompt("")  # preserve branch
        # 如果你后面想接 NTI 的 null-text embedding，这里再扩展

        self.attention_store.reset()

        all_maps = []

        timesteps = self.pipe.scheduler.timesteps

        for step_idx, t in enumerate(timesteps):
            z_src_t = src_latents[step_idx]

            # source branch
            self.attention_store.reset()
            eps_src = self.pipe.unet(z_t, t, encoder_hidden_states=cond_src).sample

            # target branch
            self.attention_store.reset()
            eps_tar = self.pipe.unet(z_t, t, encoder_hidden_states=cond_tar).sample

            # build mask from target attention + discrepancy + preservation
            M_t, aux = self.mask_builder.build(
                eps_src=eps_src,
                eps_tar=eps_tar,
                z_t=z_t,
                z_src_t=z_src_t,
                attention_store=self.attention_store,
                token_ids=token_ids,
                step_idx=step_idx,
                total_steps=len(timesteps),
            )

            eps_blend = eps_src + M_t.expand_as(eps_src) * (eps_tar - eps_src)
            z_t = self.pipe.scheduler.step(eps_blend, t, z_t).prev_sample

            all_maps.append({
                "t": int(t),
                "mask": M_t.detach().cpu(),
                **{k: v.detach().cpu() for k, v in aux.items()}
            })

        image = self.pipe.decode_latents(z_t)
        return image, all_maps
```

---

# 6. 一个关键问题：NTI 的 null-text embedding 你要怎么用

这里你有两个选择。

---

## 方案 A：V1 先不用 NTI 的每步 null-text optimization 结果
也就是：
- 只借 NTI inversion 得到 `zT_src` 和 `src_latents`
- preserve branch 仍然用普通空 prompt

### 好处
- 工程最简单
- 先验证你的 mask 方法是否成立

### 坏处
- preserve branch 可能不够强
- 某些场景下 source consistency 会偏弱

---

## 方案 B：把 NTI 的 null embeddings 接入 preserve branch
如果 NTI 实现能返回每步优化过的 uncond embedding，那么每一步 source branch 可以这样跑：

```python
eps_src = unet_with_cfg(
    z_t, t,
    cond=target_or_empty,
    uncond=null_embeddings[step_idx]
)
```

但这里要注意：
NTI 的 null embeddings 原本是为 reconstruction 服务的，不一定天然就是你想要的 preserve branch 条件。

所以我的建议仍然是：

## V1 先用方案 A
只把 NTI 当 inversion backend。  
这样你最容易把方法效果归因到 `M_t`。

---

# 7. 每一步应该怎么跑：最推荐 V1 版本

这里我给你一个**最稳 V1**。

---

## 每步有两个预测：

### Preserve branch
```python
eps_src = unet(z_t, t, cond_empty)
```

### Edit branch
```python
eps_tar = unet(z_t, t, cond_target)
```

### 构造 mask
```python
D_t = |eps_tar - eps_src|
A_t = target cross-attn aggregation
C_t = exp(-k * |z_t - z_src_t|)
M_t = sigmoid(alpha D_t + beta A_t - gamma C_t)
```

### 融合更新
```python
eps_blend = eps_src + M_t * (eps_tar - eps_src)
```

这就是最清楚的 V1 主线。

---

# 8. token_ids 怎么选

因为你现在没有 source prompt，所以 target token 选取非常重要。

---

## V1 建议
先手动选，不要自动化。

例如：
- `"a dog wearing sunglasses"` → `dog`, `sunglasses`
- `"a woman with red hair"` → `red`, `hair`
- `"a man in a blue suit"` → `blue`, `suit`

这样做虽然土，但：
- 最稳
- 最可控
- 方便分析 attention prior 是否有效

---

## 不建议 V1 做的事
- 自动 noun phrase parsing
- CLIP phrase mining
- 多 token group 动态权重

这些都晚点再说。

---

# 9. 你第一版一定要做的可视化

这个非常重要，甚至比最终图更重要。

对每个样本存 6 类图：

1. source image
2. 若干 step 的 `D_t`
3. 若干 step 的 `A_t`
4. 若干 step 的 `C_t`
5. 若干 step 的 `M_t`
6. 最终结果图

最好挑 5~8 个 step：
- early
- early-mid
- mid
- late-mid
- late

---

# 10. 你第一阶段实验目标不是“最好看”，而是回答三个问题

---

## Q1. discrepancy 能不能定位编辑区域？
如果 `D_t` 对编辑对象没有明显响应，那主线就有问题。

---

## Q2. attention prior 能不能补充语义定位？
如果 `A_t` 能把 `D_t` 的噪声压下去，说明它有价值。

---

## Q3. preservation prior 能不能抑制背景漂移？
如果加了 `C_t` 之后背景更稳、无关区域更少改动，就说明它有必要。

---

# 11. 你的 V1 baseline 应该怎么设

至少做 4 个：

## Baseline 1: target-only
```python
eps = eps_tar
```

## Baseline 2: global interpolation
```python
eps = eps_src + lambda * (eps_tar - eps_src)
```
这里 `lambda` 是全局常数，不是空间 mask。

## Baseline 3: discrepancy-only mask
```python
M_t = sigmoid(alpha * D_t)
```

## Baseline 4: full method
```python
M_t = sigmoid(alpha D_t + beta A_t - gamma C_t)
```

这样最能说明你的动态空间控制不是噱头。

---

# 12. 你现在不要急着做的东西

我再帮你明确砍一遍：

先不要做：
- phrase discovery
- body/face identity-specific priors
- replacement-special logic
- self-attention injection
- feature-level residual adapters
- region graph / object graph
- extra loss optimization during editing

你现在唯一应该守住的主线就是：

> source inversion trajectory 是否足以支持动态局部编辑定位？

---

# 13. 实际开工顺序

你就按这个清单做：

---

## 第一步：拿到 NTI inversion 输出
确认你能存：
- `zT_src`
- `src_latents`

这一步单独测试 reconstruction。

---

## 第二步：自己写一个最简 editing loop
从 `zT_src` 出发，只跑：
- empty prompt branch
- target prompt branch
- target-only output

不加 mask。

---

## 第三步：接入 `D_t`
每步可视化 discrepancy map。

---

## 第四步：接入 attention store
拿到 `A_t`，看和语义区域是否对齐。

---

## 第五步：接入 `C_t`
看是否抑制了背景区域激活。

---

## 第六步：做 `M_t`
先不平滑，再加平滑。

---

## 第七步：做 `eps_blend`
得到第一版结果。

---

## 第八步：做四个 baseline/ablation
把方法的可解释性立起来。

---

# 14. 我建议你当前版本的方法名都可以先这么记

你内部可以先临时叫：

- **Trajectory-Guided Dynamic Mask Editing**
- **Inversion-Guided Localized Editing**
- **Dynamic Masked Denoising for Real Image Editing**

先不要纠结最终论文名，先把骨架做出来。

---

# 15. 最后给你一个非常直接的判断

如果你按这条路线做，**你借用 NTI 的只有 inversion 能力**，而不是它的编辑方法。  
所以你的系统本质上是：

## 方法归属
- backbone: latent diffusion / stable diffusion
- inversion backend: NTI
- editing mechanism: **你的 dynamic mask denoising**

这个结构非常干净。

---

如果你愿意，下一条我可以直接继续给你下面两个里最实用的一个：

### 选项 1
**给你一版更具体的“伪代码到接近可实现代码”的 diffusers/NTI 主循环模板**

### 选项 2
**给你一版“论文 method section 的技术表述草稿”**
包括：
- problem setup
- notation
- mask formula
- algorithm paragraph

我建议你现在先要 **选项 1**，直接开始写代码。

---
## 🧑‍💻 User

V1 先不用 NTI 的每步 null-text optimization 结果是不是就跟简单用DDIM inversion一样呢

---
## 🤖 Assistant

对，**非常接近**。  
如果你 **V1 不使用 NTI 的每步 null-text embeddings**，那从“编辑阶段实际用到的信息”来看，确实就**很像 DDIM inversion + 你自己的 editing loop**。

但要分清楚：**“像”不等于“完全一样”**。

---

# 1. 为什么说它很像 DDIM inversion

如果你的流程是：

1. 用某种 inversion 得到 `z_T^src`
2. 保存 source trajectory `z_t^src`
3. 编辑时只用：
   - `z_T^src`
   - `z_t^src`
4. preserve branch 用普通空 prompt
5. 不使用 NTI 优化出来的每步 null embedding

那么编辑阶段的控制信息确实只有：

- source inversion latent trajectory
- target prompt
- 你自己构造的 mask

这时 **NTI 相比 DDIM inversion 的额外价值几乎没有被显式使用**。

所以从方法角度看，你可以认为：

> V1 更接近 “DDIM inversion-based editing”  
> 而不是完整意义上的 “NTI-based editing”。

---

# 2. 那 NTI 和 DDIM inversion 在这里还剩什么差别

差别主要只剩在 **你得到的起点 latent/trajectory 本身质量可能不同**。

也就是说，即使你不用 null-text embeddings，  
如果你是“先用 NTI 反演，再只取其反演结果来编辑”，那和纯 DDIM inversion 相比，理论上可能还有：

## 可能差别 1：`z_T^src` 更 source-aligned
如果 NTI 的优化让反演更贴近原图，那你的初始点可能更好。

## 可能差别 2：`z_t^src` 轨迹更稳定
如果你真的保存的是 NTI 优化后对应的 trajectory，它可能更符合 source reconstruction。

但这里有个现实问题：

### 很多 NTI 实现的核心增益其实是：
- **固定 latent inversion**
- **再优化 null-text embedding**
- 从而在采样时更好重建 source**

也就是说，它的“好”很大程度体现在：
> 采样时你使用了优化过的 null embedding

如果你编辑时把这部分完全扔掉，  
那 NTI 相比 DDIM inversion 的优势就会被大幅削弱。

---

# 3. 所以严格说，V1 应该怎么表述最准确

最准确的说法是：

## 如果你不用 null-text embeddings：
### 你的 V1 本质上应该视为
> **DDIM inversion-style real image editing pipeline**

即使你代码里调用的是 NTI 仓库。

因为你真正使用的只是：
- inversion 起点
- source trajectory

而不是 NTI 最关键的 null-text optimization editing mechanism。

---

# 4. 那我为什么还建议你先这么做

因为这对研究来说反而是好事。

---

## 原因 1：先把变量减到最少
你现在真正想验证的是：

> 你的 dynamic mask 是否有效？

如果一开始就把 NTI 的 per-step null embeddings、CFG 变体、各种 trick 全接进来，最后你很难知道提升到底来自：
- 你的 `M_t`
- 还是 NTI 的更强 source preservation

V1 越干净越好。

---

## 原因 2：DDIM inversion 更像一个中性起点
你现在的方法更适合先建在一个简单框架上：

- source inversion trajectory
- target-guided denoising
- dynamic mask blending

这时最中性的 inversion backend 就是 DDIM inversion。

---

## 原因 3：后面你还能把 NTI 当增强模块加回来
也就是说，你完全可以把实验分层：

### Stage 1
DDIM inversion + your method

### Stage 2
NTI inversion backend + your method

### Stage 3
NTI null-text preserve branch + your method

这样层次非常清楚。

---

# 5. 所以你现在最合理的选择是什么

我会给你一个很明确的建议：

## 方案 A：V1 直接就老老实实叫 DDIM inversion
如果你当前还没真正接入 NTI 的 null-text optimization结果，  
那最干净的做法是：

> V1 直接用 DDIM inversion，不要急着挂 NTI 名字

这是最诚实也最简单的。

---

## 方案 B：你可以保留“未来会接 NTI”的接口
比如你的代码结构仍然设计成：

```python
inversion_output = {
    "zT_src": ...,
    "src_latents": ...,
    "null_embeddings": optional
}
```

但 V1 先让 `null_embeddings = None`。

这样你后面无缝升级。

---

# 6. 什么时候你才算“真的用了 NTI”

至少满足下面之一，才更适合说你用了 NTI：

## 情况 1
你编辑阶段显式使用了每步优化后的 null-text embedding

比如 preserve branch 或 reconstruction-guided branch 用：
```python
eps_src = unet_cfg(z_t, t, cond=..., uncond=null_embeddings[t])
```

---

## 情况 2
你把 NTI 反演得到的优化条件真正融入 source reference prediction
比如：
- source-consistent epsilon prediction
- reconstruction branch
- source alignment regularization

---

## 情况 3
你实验中明确对比并展示：
- DDIM inversion 不行
- NTI inversion 作为 backend 明显更好

这时你可以说你借用了 NTI 的 inversion strength。

---

# 7. 对你现在最现实的建议

## 如果你现在还没接任何 NTI-specific conditioning：
**就把 V1 当成 DDIM inversion 版本来做。**

这其实更好，因为：

- 它简单
- 它干净
- 它容易 debug
- 它更方便证明你的 mask 本身有效

然后你后面再做一个 V2：

## V2
在 V1 基础上加入：
- NTI null-text embeddings 作为 preserve branch 条件
或者
- NTI backend 作为更强 inversion initialization

这样可以构成很自然的升级路线。

---

# 8. 最后一句话总结

是的，**如果 V1 不使用 NTI 的每步 null-text optimization 结果，那么它在方法本质上就非常接近“DDIM inversion + 你的动态 mask 编辑”**。  
这不是坏事，反而是一个更干净的起点。

---

如果你愿意，我下一条可以直接帮你做两个很实用的东西之一：

### 选项 A
**把你的 V1 明确定义成“DDIM inversion 版本”的完整流程图**

### 选项 B
**设计一个从 V1(DDIM) 升级到 V2(NTI增强) 的路线图**
这样你后面不会推翻重来。

我建议你现在看 **B**，因为这样你今天就能决定哪些接口要提前预留。

---
## 🧑‍💻 User

好的，看B吧

---
## 🤖 Assistant

好，我给你一个**从 V1（DDIM inversion）到 V2（NTI 增强）**的升级路线图。目标是：

- **V1 能最快跑通并验证核心思想**
- **V2 不推翻 V1，只是增量增强**
- 提前把接口留好，避免以后重构

---

## 0. 总体思路

你的方法拆成三层最稳：

1. **Inversion backend**
   - V1: DDIM inversion
   - V2: NTI inversion / null-text optimized inversion

2. **Reference source signal**
   - V1: source latent trajectory `z_t^src`
   - V2: `z_t^src` + NTI per-step null embeddings / stronger source prediction

3. **Editing mechanism**
   - 一直不变：dynamic discrepancy-attention-preservation mask

也就是说，**真正的“方法贡献”层不要动**。  
升级只发生在 inversion 和 preserve branch 的信息质量上。

---

# 1. V1 应该长什么样

---

## 1.1 V1 的定义
### V1 = DDIM inversion + dynamic-mask denoising

输入：
- source image `I_s`
- target prompt `P_t`

输出：
- edited image `I_e`

中间量：
- `z_T^src`
- source trajectory `{z_t^src}`
- target attention maps
- discrepancy maps
- soft masks

---

## 1.2 V1 每步怎么做
每一步 denoising：

- source/preserve branch:
  ```python
  eps_src = unet(z_t, t, cond_empty)
  ```
- target/edit branch:
  ```python
  eps_tar = unet(z_t, t, cond_target)
  ```
- build mask:
  ```python
  M_t = f(D_t, A_t, C_t)
  ```
- blend:
  ```python
  eps_blend = eps_src + M_t * (eps_tar - eps_src)
  ```
- scheduler step

其中：
- `D_t` 来自 `|eps_tar - eps_src|`
- `A_t` 来自 target cross-attention
- `C_t` 来自与 `z_t^src` 的偏离程度

---

## 1.3 V1 的核心验证目标
你只回答一个问题：

> 在 no-source-prompt 场景下，source inversion trajectory 是否足够支持动态局部编辑定位？

如果答案是 yes，V1 就成功了。

---

# 2. 为什么 V1 要这么设计

因为 V1 要尽量避免把收益来源搞混。

如果你一开始就引入 NTI：
- 更强 reconstruction
- per-step null embeddings
- 更复杂 CFG 控制

那你最后很难判断：
到底是你的 `M_t` 有用，还是 preserve branch 更强导致的。

所以 V1 一定要“朴素”。

---

# 3. 为 V2 预留哪些接口

这是重点。你现在代码里一定要提前留这几个口。

---

## 3.1 inversion 输出统一成一个字典
不管 V1 还是 V2，都返回同样结构：

```python
{
    "zT_src": Tensor,
    "src_latents": List[Tensor],
    "null_embeddings": Optional[List[Tensor]],
    "metadata": dict
}
```

### V1
```python
null_embeddings = None
metadata = {"backend": "ddim"}
```

### V2
```python
null_embeddings = [...]
metadata = {"backend": "nti"}
```

这样你的 editor pipeline 不用改主逻辑。

---

## 3.2 preserve branch 做成可插拔
不要把 preserve branch 写死成：

```python
eps_src = unet(z_t, t, cond_empty)
```

而是写成：

```python
eps_src = self.predict_source(z_t, t, source_context, step_idx)
```

然后：

### V1 的 `predict_source`
```python
def predict_source(...):
    return unet(z_t, t, cond_empty)
```

### V2 的 `predict_source`
可以变成：
```python
def predict_source(...):
    null_emb = source_context["null_embeddings"][step_idx]
    return unet_cfg_with_custom_uncond(z_t, t, cond_empty, null_emb)
```

或者别的 source-aware prediction 形式。

---

## 3.3 mask builder 输入不要绑定具体 backend
你的 `mask_builder.build(...)` 不应该关心：
- 这是 DDIM 还是 NTI
- 有没有 null embedding

它只需要通用量：

```python
build(
    eps_src,
    eps_tar,
    z_t,
    z_src_t,
    attention_store,
    token_ids,
    step_idx,
    total_steps
)
```

这样 V2 只会改变 `eps_src` 的质量，不会动 mask builder。

---

# 4. V2 可以怎么升级

我建议 V2 分成 **V2a / V2b / V2c**，逐步加，不要一步全上。

---

## 4.1 V2a：NTI 只替换 inversion backend
### 做法
- 反演不再用 DDIM inversion
- 用 NTI 得到更好的：
  - `zT_src`
  - `src_latents`
- 但 preserve branch 仍然先用空 prompt

即：

```python
eps_src = unet(z_t, t, cond_empty)
```

### 好处
- 改动很小
- 可以测试“更强 inversion backend 是否提升你方法”

### 你能回答的问题
> source-aligned inversion quality 是否影响 dynamic mask editing？

---

## 4.2 V2b：接入 NTI 的 per-step null embeddings 到 preserve branch
### 做法
NTI 输出：
- `null_embeddings[t]`

然后 preserve branch 用：

```python
eps_src = source_predictor(
    z_t, t,
    cond_empty,
    null_embeddings[step_idx]
)
```

这个 branch 变成更 source-consistent 的“preserve estimate”。

### 作用
它能让：
- `eps_src` 更接近 source reconstruction 动力学
- 从而 `eps_tar - eps_src` 更像“真正需要编辑的部分”
- 背景 preservation 也可能更稳

### 风险
- 可能让 source branch 太强，抑制编辑
- 需要重新调：
  - `alpha/beta/gamma`
  - CFG scale
  - threshold/smoothing

---

## 4.3 V2c：用 NTI source prediction 改造 preservation prior
V1 里的 preservation prior 是：

```python
C_t = exp(-k * |z_t - z_t^src|)
```

V2c 可以变成更强版本，比如综合：
- latent drift
- source branch confidence
- source reconstruction discrepancy

比如：

```python
C_t = w1 * latent_consistency + w2 * source_prediction_consistency
```

但这个我建议放很后面。  
因为它已经开始改方法定义了，不再只是 backend 增强。

---

# 5. 我推荐的升级顺序

最稳的顺序是：

## Step 1
**V1: DDIM inversion + dynamic mask**

先验证主线能跑通。

---

## Step 2
**V2a: NTI inversion backend 替换 DDIM inversion**

只替换 inversion，别动 editing loop。

如果这一步有提升，你就知道：
- 更好的 source initialization 是有帮助的

---

## Step 3
**V2b: NTI null embeddings 接入 preserve branch**

这一步测试：
- source prediction 更强是否让 mask 更准、背景更稳

---

## Step 4
**V2c: 让 preservation prior 也利用 NTI 信息**

这是进阶增强，不是必须。

---

# 6. 每个版本的“方法身份”怎么说

这个对你后面写论文很重要。

---

## V1
> Our base framework performs real image editing from DDIM-inverted source latents, using trajectory-derived dynamic masks for localized denoising control.

关键词：
- DDIM inversion
- dynamic mask
- no source prompt

---

## V2a
> We further improve source alignment by replacing DDIM inversion with NTI-based inversion, while keeping the proposed editing mechanism unchanged.

注意：这里强调**editing mechanism unchanged**。

---

## V2b
> We additionally incorporate NTI-optimized null-text embeddings into the preserve branch, yielding a more source-consistent reference prediction during editing.

这时你才真正把 NTI 用进 editing。

---

# 7. 代码层面该怎么设计，避免以后重构

给你一个推荐抽象。

---

## 7.1 定义统一的 InversionBackend

```python
class InversionBackend:
    def invert(self, image, prompt=""):
        raise NotImplementedError
```

### DDIM 版
```python
class DDIMInversionBackend(InversionBackend):
    def invert(self, image, prompt=""):
        return {
            "zT_src": zT,
            "src_latents": latents,
            "null_embeddings": None,
            "metadata": {"backend": "ddim"}
        }
```

### NTI 版
```python
class NTIInversionBackend(InversionBackend):
    def invert(self, image, prompt=""):
        return {
            "zT_src": zT,
            "src_latents": latents,
            "null_embeddings": null_embeds,
            "metadata": {"backend": "nti"}
        }
```

---

## 7.2 定义 SourcePredictor
这是最关键的可扩展点。

```python
class SourcePredictor:
    def predict(self, z_t, t, step_idx, source_context):
        raise NotImplementedError
```

### V1：EmptyPromptSourcePredictor
```python
class EmptyPromptSourcePredictor(SourcePredictor):
    def __init__(self, unet, empty_cond):
        self.unet = unet
        self.empty_cond = empty_cond

    def predict(self, z_t, t, step_idx, source_context):
        return self.unet(z_t, t, encoder_hidden_states=self.empty_cond).sample
```

### V2b：NullTextSourcePredictor
```python
class NullTextSourcePredictor(SourcePredictor):
    def __init__(self, unet, empty_cond):
        self.unet = unet
        self.empty_cond = empty_cond

    def predict(self, z_t, t, step_idx, source_context):
        null_emb = source_context["null_embeddings"][step_idx]
        return forward_with_custom_null_text(
            self.unet, z_t, t,
            cond=self.empty_cond,
            null_embedding=null_emb
        )
```

这样 editor 根本不需要知道你现在是 V1 还是 V2。

---

## 7.3 Editor 主循环不变
```python
eps_src = self.source_predictor.predict(z_t, t, step_idx, source_context)
eps_tar = self.target_predictor.predict(z_t, t, target_context)
M_t = self.mask_builder.build(...)
eps = eps_src + M_t * (eps_tar - eps_src)
z_t = scheduler.step(eps, t, z_t).prev_sample
```

这就是你要守住的主骨架。

---

# 8. 实验路线图怎么做最自然

---

## 8.1 先做 V1 的主实验
比较：

- target-only
- global interpolation
- discrepancy-only
- full dynamic mask

这里 backend 固定为 DDIM inversion。

---

## 8.2 再做 backend ablation
比较：

- V1 + DDIM inversion
- V2a + NTI inversion

控制变量：
- 同一个 editing loop
- 同一个 mask builder
- 同样参数尽量保持一致

这样你能把 NTI 的贡献隔离出来。

---

## 8.3 最后做 preserve branch ablation
比较：

- empty-prompt source predictor
- NTI null-text source predictor

看：
- 背景稳定性
- identity consistency
- 编辑泄漏程度
- mask quality

---

# 9. 你现在应该怎么开始写代码

我建议你立刻按下面顺序做：

### 第一阶段
- 写 `DDIMInversionBackend`
- 写 `EmptyPromptSourcePredictor`
- 写 `DynamicMaskEditor`

先让 V1 通。

### 第二阶段
- 把 inversion output 格式固定下来
- 给 `source_context["null_embeddings"]` 留字段，但先置空

### 第三阶段
- 以后再补 `NTIInversionBackend`
- 再补 `NullTextSourcePredictor`

这样就不会返工。

---

# 10. 一个很实用的接口模板

你可以直接用这种风格：

```python
class DynamicMaskEditor:
    def __init__(
        self,
        pipe,
        inversion_backend,
        source_predictor,
        target_predictor,
        mask_builder,
        attention_store,
    ):
        self.pipe = pipe
        self.inversion_backend = inversion_backend
        self.source_predictor = source_predictor
        self.target_predictor = target_predictor
        self.mask_builder = mask_builder
        self.attention_store = attention_store

    def edit(self, source_image, target_prompt, token_ids):
        source_context = self.inversion_backend.invert(source_image, prompt="")
        z_t = source_context["zT_src"].clone()
        timesteps = self.pipe.scheduler.timesteps

        target_context = {
            "prompt": target_prompt,
            "token_ids": token_ids,
        }

        for step_idx, t in enumerate(timesteps):
            z_src_t = source_context["src_latents"][step_idx]

            self.attention_store.reset()
            eps_src = self.source_predictor.predict(z_t, t, step_idx, source_context)

            self.attention_store.reset()
            eps_tar = self.target_predictor.predict(z_t, t, step_idx, target_context)

            M_t, aux = self.mask_builder.build(
                eps_src, eps_tar, z_t, z_src_t,
                self.attention_store, token_ids, step_idx, len(timesteps)
            )

            eps = eps_src + M_t * (eps_tar - eps_src)
            z_t = self.pipe.scheduler.step(eps, t, z_t).prev_sample

        image = self.pipe.decode_latents(z_t)
        return image
```

以后升级时，基本只换组件，不换框架。

---

# 11. 最后给你一个明确判断标准

如果你之后发现：

- **V1 就已经能清楚定位编辑区域**
- 并且结果足够稳

那说明你的方法核心是成立的，NTI 只是增强项。

如果你发现：

- V1 的 preserve branch 太弱
- 背景漂移明显
- discrepancy map 很脏

那就说明 V2b 很值得做，因为你确实需要更强 source-consistent prediction。

---

# 12. 一句话总结

## 升级路线最推荐这样走：

- **V1**：DDIM inversion + empty-prompt source predictor + dynamic mask  
- **V2a**：换成 NTI inversion backend  
- **V2b**：再把 NTI null-text embeddings 接入 preserve branch  
- **V2c**：最后再考虑让 preservation prior 也吃到 NTI 信息

核心原则是：

> **你的 editing mechanism 不变，先验证方法；NTI 只作为逐步增强模块接入。**

如果你愿意，我下一条可以直接继续给你：

### 选项 1
**V1 的具体代码骨架（按 diffusers 写到类和函数级别）**

### 选项 2
**V1/V2 论文实验设计表格**
包括每个 ablation 怎么命名、比较什么、预期现象是什么。

我建议现在直接看 **选项 1**。
