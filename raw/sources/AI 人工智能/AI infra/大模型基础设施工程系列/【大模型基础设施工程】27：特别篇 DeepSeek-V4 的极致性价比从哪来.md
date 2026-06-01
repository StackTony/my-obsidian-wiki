DeepSeek-V4 真正惊人的地方，不是“把价格牌改小了”，而是它把**旗舰能力**和**低单位成本**做进了同一套架构里。公开资料已经给出足够硬的信号：DeepSeek-V4-Pro 是 1.6T 总参数、49B 激活参数的 MoE 模型，V4-Flash 是 284B 总参数、13B 激活参数；两者都把 1M context 作为官方默认配置；而且在 1M 上下文下，V4-Pro 的单 token 推理 FLOPs 只有 DeepSeek-V3.2 的 27%，KV cache 只有 10%。

如果只把这理解成“价格战”，会错过最重要的东西。DeepSeek-V4 便宜，不是因为它把一个本来就昂贵的系统赔本卖给你，而是因为它从**模型结构、训练稳定性、并行内核、缓存系统、后训练范式、Agent runtime**一路往下，把真正烧钱的地方一项一项削掉了。本文只讨论目前在 DeepSeek 官方技术报告和 API 文档里已经公开的技术项。

## 一、先把“极致性价比”量化出来

截至本文写作时（2026-05-27），DeepSeek 官方 API 文档给出的关键信息如下：

|项目|DeepSeek-V4-Pro|DeepSeek-V4-Flash|
|---|---|---|
|总参数 / 激活参数|1.6T / 49B|284B / 13B|
|官方上下文长度|1M|1M|
|最大输出|384K|384K|
|输入价格（Cache Hit）|$0.003625 / 1M tok|$0.0028 / 1M tok|
|输入价格（Cache Miss）|$0.435 / 1M tok|$0.14 / 1M tok|
|输出价格|$0.87 / 1M tok|$0.28 / 1M tok|

这张表要和另一组数字一起看：技术报告明确写到，在 1M context 下，DeepSeek-V4-Pro 相比 DeepSeek-V3.2，**单 token 推理 FLOPs 降到 27%，KV cache 降到 10%**；V4-Flash 更激进，分别降到 10% 和 7%。也就是说，价格不是悬在半空里的市场动作，而是被底层效率变化支撑起来的。

接下来按“到底是哪几项技术把成本打下来了”的顺序展开。

## 二、第一项：DeepSeekMoE 把“总参数规模”和“每 token 成本”拆开

DeepSeek-V4 延续的是 DeepSeek 自己已经跑通的 DeepSeekMoE 路线，而不是重新回到稠密模型。它的关键价值在于：**总参数决定上限，激活参数决定每个 token 的边际成本。**

对 V4-Pro 来说，模型总参数是 1.6T，但每个 token 实际只激活 49B；对 V4-Flash 来说，是 284B 总参数、13B 激活。技术报告里还公开了更细的配置：

- V4-Pro 有 61 层，所有 Transformer block 都是 MoE FFN；
- 每层有 1 个 shared expert 和 384 个 routed experts；
- 每个 token 只激活 6 个 routed experts；
- 前 3 层用 Hash routing，后面再交给可学习路由。

这件事为什么直接等价于“便宜”？因为稠密模型的痛点是：**总参数就是你每一步都要付的钱**。而 MoE 不是。MoE 把“我需要一个很大的模型容量”和“我不想每个 token 都扫描全部参数”这两件事拆开处理。这样一来：

1. 预训练时，你可以用更大的总参数去存知识和能力；
2. 推理时，你只为真正被路由到的专家付算力和访存成本；
3. 在代码、推理、Agent 这类 token 特征差异很大的任务里，不同 token 会落到不同专家，模型容量利用率更高。

当然，MoE 不是白送的。它把“算力问题”变成了“通信 + 路由 + 并行调度问题”。所以 DeepSeek-V4 真正厉害的地方，不只是用了 MoE，而是后面几节会讲到的：它把 MoE 最贵的那部分工程代价也一起做掉了。

## 三、第二项：CSA + HCA 混合注意力，把 1M 上下文从“理论支持”变成“能日常开”

DeepSeek-V4 最核心的降本技术，是它的混合注意力：**CSA（Compressed Sparse Attention）+ HCA（Heavily Compressed Attention）**。

问题背景很简单。长上下文之所以贵，不是因为“多了点输入”，而是因为 attention 的成本会随着上下文长度迅速爆炸，KV cache 也会跟着膨胀。1M context 如果还沿着常规 dense attention 走，模型能力再强，服务成本也会非常难看。

DeepSeek-V4 的做法是分两层压：

### 3.1 CSA：先压缩，再稀疏选 top-k

CSA 不是直接做 sparse attention，而是先把 KV 压成更小的表示，再在压缩后的块上做稀疏选择。以 V4-Pro 为例：

- 压缩率 `m = 4`：每 4 个 token 先压成 1 个 compressed KV；
- 再用 DeepSeek Sparse Attention 做选择；
- 每个 query 只保留 1024 个 compressed KV block 参与主注意力；
- 另外再拼上一段 `nwin = 128` 的 sliding window，保住最近邻细节。

这里有两个细节特别关键。

第一，DeepSeek 没有用一个昂贵的全精度 selector 去找相关块，而是用了一个所谓的 **lightning indexer**：先把 query 压到低秩 latent，再去给历史 compressed KV 打分，最后只保留 top-k。也就是说，模型不是在 1M token 上“全看一遍再决定看谁”，而是在一个更便宜的索引空间里先粗筛，再做主注意力。

第二，CSA 不是完全抛弃局部精细信息。它额外保留 sliding window 分支，让 query 同时看到最近的一小段未压缩 KV。这样做的意义是：**全局靠压缩和稀疏，局部靠原始细节补精度**。这也是它不像某些长上下文方案那样，一旦上下文超长就明显变“糊”的原因。

### 3.2 HCA：进一步重压缩，但保留 dense attention

HCA 比 CSA 更狠。技术报告里给出的 V4-Pro 配置是：

- HCA 的压缩率 `m' = 128`；
- 它不再做 sparse selection；
- 而是在被重压缩后的 KV 上继续做 dense attention。

这个设计很聪明。因为不是所有层都需要同样细的注意力分辨率。DeepSeek 把一部分层做成 CSA，让模型保留“挑重点看”的能力；另一部分层做成 HCA，让模型在极低 KV 成本下继续处理很长的历史。两者交替使用，才是 V4 真正能把 1M 做成默认能力的原因。

### 3.3 为了让压缩注意力不掉精度，V4 又补了四个小设计

技术报告里还有四个常被忽略、但实际上很值钱的细节：

1. **RMSNorm on query / KV**：在 core attention 前，对 query 和 compressed KV 做额外 RMSNorm，防止 attention logit 爆炸。
2. **Partial RoPE**：不是把完整 RoPE 套到所有维度，而是只对最后 64 维施加位置编码，并对输出做逆向位置修正，保住相对位置信息。
3. **Sliding Window Branch**：上面提过，本质是给被压缩的 attention 体系补一个高保真“近场观察窗”。
4. **Attention Sink**：为每个 head 引入可学习 sink logit，让注意力总质量不必强行等于 1，避免部分 head 在长上下文下被迫把注意力摊平。

### 3.4 这项技术直接换来了什么

V4 报告给出的结果非常直接：

- 在 1M context 下，V4-Pro 的单 token FLOPs 只有 V3.2 的 **27%**；
- KV cache 只有 V3.2 的 **10%**；
- 如果拿常见的 BF16 GQA8 配置做基线，V4 系列在 1M context 下的 KV cache 大约只剩其 **2%** 量级；
- V4 还把 KV 存储做成了混合格式：RoPE 维度保留 BF16，非 RoPE 维度转 FP8，KV cache 体积再砍近一半；
- lightning indexer 的 attention 计算进一步用了 FP4。

这就是 DeepSeek-V4 性价比的第一大支柱：**不是“1M 也能跑”，而是“1M 跑起来时还不至于贵得离谱”。**

## 四、第三项：mHC 把深层大模型里最容易炸的残差路径重新设计了

DeepSeek-V4 在结构上的第二个大改动，是用 **mHC（Manifold-Constrained Hyper-Connections）** 替代普通残差连接。

普通残差连接的好处是简单、稳、便宜；坏处是当模型越来越深、越来越大时，残差流的表达能力和稳定性会一起成为瓶颈。Hyper-Connections 的想法是把残差流扩宽，给跨层信息流动更多自由度；但普通 HC 一旦堆太深，很容易出现数值不稳定。

DeepSeek-V4 的 mHC 不是简单“多加几条残差边”，而是给残差映射矩阵加了一个很强的约束：把它限制在**双随机矩阵的流形**里，也就是 Birkhoff polytope。工程上怎么做到？技术报告给出的做法是：

- 把残差映射矩阵 `B_l` 约束为双随机矩阵；
- 这样它的谱范数上界被限制在 1；
- 残差变换就成了 non-expansive，不会一路把数值放大；
- 具体投影通过 Sinkhorn-Knopp 迭代完成，V4 里 `tmax = 20`；
- 输入映射 `A_l` 和输出映射 `C_l` 也都通过 Sigmoid 保证非负、受界。

把这套话翻译成人话：**DeepSeek 不是只想让残差“更强”，它想让残差“更强但不失控”。**

这和性价比的关系非常直接。万亿级 MoE 训练里，最贵的不是理论 FLOPs，而是“不稳定导致的失败步骤、回滚和反复试错”。mHC 并不直接降低单步算力，但它提高了深层网络训练的可控性和表达效率，让“更深、更大、更长上下文”的模型仍能落在一个可训练的区域里。对旗舰模型来说，这本身就是成本优化。

## 五、第四项：Muon 优化器在大多数模块上替掉 AdamW，换更快收敛和更稳训练

DeepSeek-V4 的第三个结构级升级，是把 **Muon** 引入到大部分模块的训练里。

很多人提到优化器时只会说一句“换 Muon 了”，但 V4 的关键其实不在“名字”，而在它把什么问题解决了。技术报告里说得很明确：DeepSeek 之所以在大部分参数上使用 Muon，是因为它能带来**更快收敛**和**更好的训练稳定性**。

V4 不是全模型一刀切都上 Muon。它的分工是：

- **AdamW 继续保留**：embedding、prediction head、mHC 的静态 bias 和 gating、所有 RMSNorm；
- **其余大多数模块用 Muon**。

Muon 的核心步骤，是对梯度矩阵做近似正交化。V4 的实现里不是直接用标准 Newton-Schulz，而是用了 **hybrid Newton-Schulz**：

- 总共 10 次迭代；
- 前 8 次用更激进的系数，让奇异值快速逼近 1；
- 后 2 次改用更稳定的系数，把奇异值钉在 1 附近。

再叠加两件事：

1. **Nesterov trick**；
2. **对更新矩阵 RMS 重新缩放**，尽量复用原来 AdamW 的学习率超参。

这背后的工程目标很现实：不要为了换一个优化器，把整套训练调参体系重新推倒重来。

为什么这会带来性价比？

- 对 32T~33T token 级别的预训练来说，**收敛快一点**就是少烧很多卡时；
- 对万亿 MoE 来说，**稳定一点**就是少遇到 loss spike、少回滚、少做保护性保守配置；
- 对长上下文训练来说，优化器如果更稳，就能更放心地把 sequence length 一路推到 1M。

一句话：**Muon 不是“学术上的更优”，而是“在这个训练规模上更省钱”。**

## 六、第五项：训练稳定性本身就是成本项，V4 直接为 loss spike 做了两套保险

V4 技术报告里有一段很值得工程师反复读：DeepSeek 明确承认，训练万亿级 MoE 时，他们确实遭遇了显著的不稳定；简单 rollback 只能暂时恢复，不能从根上消掉 spike。最后他们公开了两种实用手段。

### 6.1 Anticipatory Routing：把“主干更新”和“路由更新”临时错开

DeepSeek 观察到，loss spike 经常和 MoE 层里的异常值有关，而路由机制又会放大这种异常。于是他们引入 **Anticipatory Routing**：

- 在 step `t`，主干特征仍用当前参数 `θ_t` 算；
- 但路由索引改用历史参数 `θ_{t-Δt}` 计算；
- 为了避免重复加载模型参数，系统会提前在前面的 step 预取数据并缓存路由索引；
- 这套模式不是永久开启，而是在自动检测到 spike 时才短暂触发。

报告给出的数字是：即便这样，额外墙钟开销也只被压在大约 **20%**，而且因为只在异常时刻短暂开启，整体额外代价很小。

这是一种很典型的“性价比工程”：**我不追求理论最优，我追求训练不要炸，而且修 spike 的成本不要比 spike 本身更贵。**

### 6.2 SwiGLU Clamping：直接把异常值截掉

第二个手段更朴素，但也更工程化：**SwiGLU clamp**。

DeepSeek 在实际训练里发现，对 SwiGLU 做数值截断很有效：

- 线性分量 clamp 到 `[-10, 10]`；
- gate 分量上界截到 `10`。

效果是明显抑制异常值，但又不损害最终性能。注意这里的价值不是“某个技巧多优雅”，而是它让一条 33T token 的预训练曲线更可控。万亿级训练里，能稳定跑完全程，本身就是最值钱的能力。

### 6.3 稀疏注意力不是一开始就开，而是逐步引入

V4 训练不是从第一步就把所有复杂机制全打开。它的策略是：

- 序列长度从 `4K → 16K → 64K → 1M` 逐步拉长；
- sparse attention 不是一开始就用，而是先用 dense attention warmup；
- Flash 版前 1T token 先做 dense attention，再在 64K 序列长度引入 sparse attention；
- 引入 sparse attention 时，还先单独 warmup 一段 lightning indexer。

这同样是在省钱。因为最昂贵的训练，不是“每一步都慢”，而是“你以为在训练，实际上在用不稳定的配置反复试错”。

## 七、第六项：MoE 最贵的不是专家本身，而是专家之间的通信；V4 用 wave pipeline 把它吃掉

MoE 的理论便宜，很容易死在工程上：token 要 dispatch 到专家，再 combine 回来，中间还要做两次大矩阵乘法。如果 dispatch / combine 的 All-to-All 打不满、等得太久，MoE 的账很快就算不平。

DeepSeek-V4 在这件事上的核心设计是：**把通信、计算和访存塞进同一个细粒度流水线里做 overlap。**

报告把一个 MoE layer 拆成四段：

1. Dispatch（通信）
2. Linear-1（计算）
3. Linear-2（计算）
4. Combine（通信）

他们的 profiling 发现：在一个 layer 内，通信时间总量其实小于计算时间总量。于是 V4 不是去一味追更粗的互联，而是把专家切成多个 **wave**：

- 一个 wave 里只放一小部分专家；
- 某个 wave 的 token 一通信完，马上开始计算；
- 当前 wave 在算的同时，下一个 wave 继续传 token，上一个 wave 继续回传结果；
- 这样就形成了持续不断的细粒度 pipeline。

结果是非常硬的：

- 一般推理 workload 上，**1.50~1.73×** 加速；
- RL rollout、高速 Agent serving 这类更偏尾延迟敏感的场景里，最高 **1.96×**。

更有意思的是，DeepSeek 还把这个思路反过来提炼成了一个硬件观点：**关键不是盲目堆带宽，而是把计算/通信比打到一个能完整 overlap 的平衡点。**

这节还有一个容易被带偏的地方。技术报告说，他们在 **NVIDIA GPUs 和 HUAWEI Ascend NPUs** 上都验证了这套 fine-grained EP scheme。但它并没有公开披露“到底多少训练或推理成本来自哪种芯片”“国产硬件对 API 价格贡献具体占比多少”。所以公开能下的结论是：**DeepSeek 确实在做跨硬件的 MoE 高效内核验证**；不能下的结论是任何未披露的采购或路线图细节。

## 八、第七项：TileLang、确定性内核、细粒度 checkpoint，把“能跑”推到“能量产”

很多文章只盯模型结构，不盯内核和框架；但对 V4 这种系统来说，真正把账打薄的往往正是这些“看起来不性感”的地方。

### 8.1 TileLang：把几百个碎 ATen operator 变成少量高效 fused kernels

V4 的结构太复杂：混合注意力、MoE、indexer、grouped projection、mHC……如果全都用细碎的 Torch ATen operator 去拼，CPU 调度开销和 kernel launch 开销会非常大。

DeepSeek 的做法是用 **TileLang** 去写 fused kernels。报告里提到几个具体收益：

- device kernel 和 host launcher 一起生成；
- 把本来在 Python 侧做的 shape / dtype / stride 检查下推到生成的 host code；
- CPU 侧每次调用的校验开销，从几十到几百微秒，降到 **1 微秒以内**；
- 还把 Z3 SMT solver 接进编译器，做更强的整数分析，方便向量化、barrier 插入和代码简化。

这类优化不会出现在 benchmark 首页，但它直接决定了复杂模型能不能被稳定、高密度地服务化。

### 8.2 Batch-invariant + deterministic kernels：让训练、后训练、推理三条链路真正对齐

DeepSeek 明确把“位级可复现”当成设计目标。这一点很少有团队公开写得这么重。

为什么重要？因为 V4 后训练里既有 RL，也有 OPD，还有 rollout、故障恢复、Agent 评测。如果同一个 token 只是因为 batch 里邻居变了，结果就不同，那你会很难判断问题到底来自模型、数据还是系统。

所以他们做了三类事：

1. **Attention**：不用会破坏 batch invariance 的 split-KV 方案，而是设计双 kernel，既保吞吐也保 bitwise identity。
2. **Matrix Multiplication**：需要 batch invariance 的地方，不依赖传统 cuBLAS 路线，而是 end-to-end 切到 DeepGEMM。
3. **Backward**：对 sparse attention、MoE backward、mHC 的小矩阵乘法都单独做确定性规约，避免 atomicAdd 带来的非确定性。

这看似是在为调试服务，实际上也是在为成本服务：**系统越可复现，定位 spike、回归性能和验证新 kernel 的时间越短。**

### 8.3 训练框架也为“新结构”重写过

V4 不是把 Muon、mHC、CSA/HCA 塞进旧框架就完事了。报告公开了几项关键配套：

- **Hybrid ZeRO for Muon**：因为 Muon 需要完整梯度矩阵，不能直接照搬 AdamW 式的 ZeRO 切法，于是他们为 Muon 单独设计 bucket assignment。
- **mHC fused kernels + selective recomputation**：把 mHC 带来的额外开销压到 overlapped 1F1B pipeline stage 的 **6.7%**。
- **Contextual Parallelism**：为了适配 CSA/HCA 的压缩 attention，重新设计了两阶段通信流程，解决“压缩块跨 rank 边界”的问题。
- **Tensor-level activation checkpointing**：不是整模块 checkpoint，而是 tensor 级别标注 + TorchFX 自动生成重算图，在不牺牲 autograd 编程体验的前提下做更细粒度的显存/重算平衡。

这些优化的共同作用是：让“1M context 训练”不只是论文里可以写，而是工程上能持续迭代。

对 DeepSeek-V4 这种 1M context + Agent 模型来说，缓存不是锦上添花，而是 API 价格的一部分。

### 9.1 V4 先把 KV cache 本体重构了

V4 的混合注意力让 KV cache 不再是一个统一的扁平数组。因为它同时有：

- CSA compressed KV；
- HCA compressed KV；
- sliding window attention 的未压缩 KV；
- 还没攒够一个压缩块、暂时不能压的 tail states。

这会直接打破传统 PagedAttention 的一些前提。DeepSeek 因此把 KV cache 划成两部分：

1. **classical KV cache**：存 CSA/HCA 的 compressed KV；
2. **state cache**：存 SWA 和还没准备好压缩的尾部状态。

这是一件很重要的工程取舍：**先承认 hybrid attention 的 KV 不是同一种东西，再分别管理它们，而不是强行塞进一个统一抽象里。**

### 9.2 磁盘级 context caching：把重复 prefill 直接挪成缓存命中

DeepSeek API 文档明确写了：**Context Caching on Disk 默认对所有用户开启**。当多个请求共享前缀时，重叠部分直接从磁盘缓存读取，不必重新 prefill。

V4 技术报告进一步解释了它在模型内部怎么配合这个机制：

- 对 CSA/HCA：把 compressed KV 全部落盘；
- 命中前缀时，直接读回完整压缩块对应的 KV；
- 对还不完整的尾部压缩块，重新计算补齐；
- 对 SWA：提供 full caching / periodic checkpointing / zero caching 三种策略，按“存储开销 vs 重算代价”做权衡。

这和官方 API 的缓存命中规则是对应起来的。文档里写得很清楚，缓存前缀单元有三种持久化来源：

1. **请求边界持久化**：一轮请求结束时，把边界位置固化成 cache prefix unit；
2. **公共前缀检测**：多次请求出现共同前缀后，把共同部分单独固化；
3. **固定 token 间隔切块**：超长输入/输出按固定间隔切成可命中的块。

要注意的是，它不是模糊相似命中，而是**必须完整匹配某个 cache prefix unit**。另外官方也强调：缓存是 best-effort，不保证 100% 命中。

### 9.3 这为什么会直接反映到价格上

因为长文档问答、代码 Agent、企业知识库、工具型多轮对话，都有一个共同特征：**同一大段前缀会被反复复用。**

如果每次都重做 prefill，模型再强也会很贵。DeepSeek 把这部分从 GPU 昂贵计算改成“读磁盘 + 补一点尾部重算”，就可以理直气壮地把 cache-hit 价格拉到远低于 cache-miss。以 V4-Pro 为例，写作时官方定价里：

- cache hit：$0.003625 / 1M tok
- cache miss：$0.435 / 1M tok

两者差了两个数量级。这不是市场活动而已，而是**系统在主动引导开发者把工作负载组织成 cache-friendly 的形式**。

## 十、第九项：后训练不再靠“一个大模型混着学一切”，而是先练专家，再统一蒸馏

DeepSeek-V4 的后训练范式，也明显是为了效率服务的。

技术报告写得很直接：和 V3.2 相比，V4 后训练里一个关键变化是，**把 mixed RL 阶段整个替换成了 On-Policy Distillation（OPD）**。

它分两步：

### 10.1 先训 specialist

针对数学、代码、Agent、指令跟随等不同领域，DeepSeek 不是让一个统一模型直接混着学，而是先分别做：

1. SFT；
2. 再用 GRPO 做 RL，对不同领域施加不同的 reward；
3. 对不同 reasoning effort（Non-think / High / Max）还用不同长度惩罚和上下文窗口去训练。

这一步的意义是：**把每种能力先练到“足够尖”，不要太早混。**

### 10.2 再用多教师 OPD 把能力收编进一个统一学生模型

随后，DeepSeek 用多教师 OPD 做统一模型合并。它不是权重平均，也不是把多个专家模型串在服务层外面，而是让学生模型在自己的采样轨迹上，对齐多个 teacher 的输出分布。

报告披露了几个关键点：

- 使用 **10 多个 teacher models** 覆盖不同领域；
- 采用的是 **reverse KL** 目标；
- 不是常见的 token-level KL 近似，而是做 **full-vocabulary logit distillation**；
- 这样梯度方差更小，稳定性更好，不容易出现传统 mixed RL / weight merge 里的能力互相打架。

这套范式为什么和性价比有关？因为它把“练很多专科能力”和“最终只维护一个统一大模型”这两件事同时做到了。你可以把它理解成：**训练时允许能力分治，部署时坚持能力收敛。**

## 十一、第十项：FP4 QAT 不是宣传词，而是 V4 部署成本里真正落地的一刀

DeepSeek-V4 并没有把低精度停留在“我们也支持 FP8/FP4”这种口号层面。它在后训练里明确做了 **FP4 Quantization-Aware Training**。

应用对象有两个：

1. **MoE expert weights**；
2. **CSA indexer 的 QK path**。

为什么恰好选这两个？

- MoE expert weights 是显存和内存带宽的大头之一；
- indexer QK path 是 1M context 下高频、反复执行的选择路径。

技术报告公开的实现细节很有意思：

- 优化器维护 FP32 master weights；
- 前向时先量化成 FP4，再无损地反量化到 FP8 参与计算；
- 之所以能做到“FP4 → FP8 无损”，是因为他们当前的 block 量化设置允许 FP8 的动态范围完整吸收 FP4 的缩放信息；
- 这样一来，整条 QAT pipeline 可以最大程度复用现有 FP8 训练栈；
- 到真正 inference / rollout 时，就直接用 native FP4 权重，不只是“模拟量化”。

另外，DeepSeek 还把 CSA indexer 的 index score 从 FP32 进一步量化到 BF16，在保持 **99.7% KV entry recall** 的同时，让 top-k selector 获得 **2×** 加速。

这一节的核心结论是：**V4 不是“理论上未来硬件更适合 FP4”，而是已经把 FP4 变成今天部署成本的一部分。**

## 十二、第十一项：Quick Instruction 和长链推理上下文管理，连 Agent 的“胶水成本”都在省

如果只看基础模型，很容易低估 Agent 场景里真正烧钱的地方。很多系统的额外成本不在主模型，而在一堆外围“小动作”：

- 要不要搜网页；
- 要不要读 URL；
- 这个问题属于什么 domain；
- 要不要生成一个标题；
- 工具调用过程中上一轮思路要不要保留。

DeepSeek-V4 针对这些“胶水工作”做了两件很工程化的优化。

### 12.1 Quick Instruction：别起一个小模型，直接复用当前 KV cache

很多聊天系统会用一个额外的小模型来做 search intent、authority 判断、query 生成这类预处理。问题是：小模型虽然便宜，但它要重新 prefill，之前主模型已经算好的 KV cache 完全复用不上。

V4 的做法是引入一组 special tokens，例如：

- `<|action|>`
- `<|query|>`
- `<|authority|>`
- `<|domain|>`
- `<|read_url|>`

直接把这些辅助任务附着在原输入序列上跑。这样它们就能重用已经算好的 KV cache，还能并行做一部分预处理任务。技术报告给出的结论非常明确：这样可以显著降低 **TTFT**，而且少维护一个单独的小模型。

### 12.2 Interleaved Thinking：工具回合里的思路不要白白冲掉

DeepSeek API 文档和 V4 报告都强调了“thinking mode + tool calls”的上下文管理。V4 的一个升级是：

- 普通对话里，新用户消息到来后，旧 reasoning trace 仍可丢弃，避免上下文膨胀；
- 但在**工具调用型 Agent 场景**里，reasoning content 会跨轮次保留，包括跨 user message 边界也保留。

这件事对 Agent 很重要。因为很多工具型任务不是“单次思考 → 单次回答”，而是“思考 → 调工具 → 再思考 → 再调工具”。如果每来一轮用户消息就把前面思路冲掉，模型会不断重建问题状态，既浪费 token，又拉长延迟。

V4 借着 1M context，把这种 interleaved thinking 真正做成了长链任务优化。这不是最显眼的创新，但对代码 Agent、复杂浏览器任务、多步工具调用来说，它能实打实减少无效重复推理。

## 十三、哪些流行说法现在还不能写成结论

写 DeepSeek-V4 这类文章时，最容易犯的错误不是“不懂”，而是把二手传播里的推断写成官方事实。就当前公开资料来说，下面三条边界要守住：

1. **可以确认**：DeepSeek-V4 的关键降本技术是 MoE、CSA/HCA、mHC、Muon、EP overlap、磁盘 KV cache、OPD、FP4 QAT。  
    **不能确认**：任何官方尚未公开披露的具体供应链细节、采购价格、芯片路线图。
2. **可以确认**：V4 的 EP 方案在 NVIDIA GPU 和华为昇腾 NPU 上做过验证。  
    **不能确认**：API 价格中到底有多少比例来自某一类芯片或某个集群部署形态。
3. **可以确认**：DeepSeek API 的磁盘缓存默认开启，cache hit 很便宜。  
    **不能确认**：缓存命中“必然”能到某个固定百分比，因为官方文档明确说它是 best-effort，不保证 100% 命中。

这一节看起来像在泼冷水，但恰恰是技术写作里最应该守住的地方：**把真正公开的工程创新讲透，比把没公开的猜测写满更有价值。**

## 十四、小结

DeepSeek-V4 的极致性价比，绝不是某一个“黑科技”的结果，而是一整串相互咬合的设计：

1. 用 **DeepSeekMoE** 把大模型容量和每 token 成本分离；
2. 用 **CSA + HCA** 把 1M context 的 attention FLOPs 和 KV cache 一起砍下来；
3. 用 **mHC + Muon + 稳定性机制** 让深层、超长上下文、万亿级 MoE 真能稳定训完；
4. 用 **EP overlap、TileLang、deterministic kernels、tensor-level checkpointing** 把复杂结构做成可量产的系统；
5. 用 **磁盘 KV cache、Quick Instruction、interleaved thinking** 把在线 Agent 场景里的重复计算打薄；
6. 用 **specialist training + OPD + FP4 QAT** 把后训练和部署成本一起压下去。

所以 DeepSeek-V4 便宜，不是因为它只是在卖一个“稍弱但更低价”的模型，而是因为它在公开技术报告里已经证明：**它确实把长上下文、推理、Agent、缓存、后训练这些最烧钱的环节，一层层做成了更高的单位效率。**

## 参考资料

1. DeepSeek-AI. _DeepSeek-V4: Towards Highly Efficient Million-Token Context Intelligence_. 2026.  
    
2. DeepSeek API Docs: [DeepSeek-V4 Preview](https://api-docs.deepseek.com/news/news260424)  
    
3. DeepSeek API Docs: [Pricing](https://api-docs.deepseek.com/quick_start/pricing)  
    
4. DeepSeek API Docs: [Context Caching on Disk](https://api-docs.deepseek.com/guides/kv_cache)  
    
5. DeepSeek API Docs: [Thinking Mode](https://api-docs.deepseek.com/guides/thinking_mode)

## 延伸阅读

- [MoE 训练工程：GShard、Switch、Mixtral、DeepSeek](https://quant67.com/post/llm-infra/08-moe-training/08-moe-training.html)
- [推理引擎基础：prefill、decode、KV cache、batching](https://quant67.com/post/llm-infra/11-inference-basics/11-inference-basics.html)
- [量化工程：FP8、FP4、AWQ、GPTQ、KV 量化](https://quant67.com/post/llm-infra/14-quantization/14-quantization.html)
- [长上下文工程：RoPE 扩展、YaRN、Ring Attention、MLA](https://quant67.com/post/llm-infra/16-long-context/16-long-context.html)
- [DeepSeek-V4 与国产芯片：从备份路线到主路径](https://quant67.com/post/llm-infra/26-deepseek-v4-domestic-chip/26-deepseek-v4-domestic-chip.html)

---

**上一篇**：[DeepSeek-V4 与国产芯片：从备份路线到主路径](https://quant67.com/post/llm-infra/26-deepseek-v4-domestic-chip/26-deepseek-v4-domestic-chip.html)

## 同主题继续阅读

把当前热点继续串成多页阅读，而不是停在单篇消费。

2026-04-22 · architecture / ai-infra

### [大模型基础设施工程](https://quant67.com/post/llm-infra/index.html)

面向中国工程团队的大模型基础设施系列。从 GPU/CUDA/互联、训练框架与 3D 并行、vLLM/SGLang 推理引擎、量化与推测解码、RAG/Agent 到服务化、网关、可观测性与安全合规，覆盖 LLMOps 全链路。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】01：大模型基础设施全景 —— 训练、推理、RAG、Agent、观测](https://quant67.com/post/llm-infra/01-intro/01-intro.html)

面向工程师的大模型基础设施开篇地图，覆盖 2022 到 2026 的工程分水岭、五层工程栈、训练与推理的工程差异、中国与全球行业版图以及成本曲线。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】08：MoE 训练工程](https://quant67.com/post/llm-infra/08-moe-training/08-moe-training.html)

混合专家（MoE）模型训练工程实战：从 GShard、Switch、Mixtral 到 DeepSeek-V3，覆盖门控、负载均衡、Expert Parallel、All-to-All 通信与 DeepEP / MegaBlocks 等开源栈

2026-04-25 · architecture / ai-infra

### [【大模型基础设施工程·特别篇】DeepSeek-V4 与国产芯片：从备份路线到主路径](https://quant67.com/post/llm-infra/26-deepseek-v4-domestic-chip/26-deepseek-v4-domestic-chip.html)

DeepSeek-V4 发布后，如果国产芯片已经支撑旗舰模型的关键训练或推理链路，它会怎样影响 NVIDIA 生态、国产 AI 芯片、云厂商、模型团队和工程师的技术选择？