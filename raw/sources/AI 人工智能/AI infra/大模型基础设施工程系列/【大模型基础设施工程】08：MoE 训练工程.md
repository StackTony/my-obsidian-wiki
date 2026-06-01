2023 年之前，稠密（Dense）Transformer 几乎是 LLM 的代名词。2024 年之后，情况变了：Mixtral 8×7B 让开源社区第一次跑上”旗舰级 MoE”，DeepSeek-V2/V3 把稀疏专家做到 671B 总参数 / 37B 激活、训练成本仅 $5.6M 的程度，Qwen3-MoE、Kimi K2、GLM-4.5 相继跟进。MoE（Mixture of Experts，混合专家）从”论文里的奇技”变成了”工业界主力架构”。

本文从工程视角讲：**为什么是 MoE、怎么训 MoE、怎么把 MoE 跑到千卡集群**。前一篇（[Megatron-LM 与 DeepSpeed](https://quant67.com/post/llm-infra/07-megatron-deepspeed/07-megatron-deepspeed.html)）讨论了稠密大模型的五维并行，本文在它之上加入 EP（Expert Parallel）这第六个维度，并把 DeepEP、MegaBlocks、Tutel 这些关键组件讲清楚。

### 1.1 总参数 ≠ 激活参数

稠密模型的一条铁律：**每个 token 的每一次前向，都要走过所有参数**。一个 70B 参数的 LLaMA，每推理一个 token 就要做约 140 GFLOPs 的运算（2N，N = 参数量）。

MoE 打破了这条铁律。MoE 的每个 Transformer Block 里把 FFN 换成 N 个”专家”（各自是一个独立的 FFN），每个 token 只被路由到 K 个专家（典型 K=2 或 K=8），其它专家不参与计算：

```
总参数 = Attention + N × FFN_expert
激活参数 ≈ Attention + K × FFN_expert  （K << N）
```

以 Mixtral 8×7B 为例：总参数约 46.7B（不是 56B，Attention 是共享的），激活参数约 12.9B（K=2）。DeepSeek-V3：总 671B，激活 37B，**激活比仅 5.5%**。

### 1.2 FLOPs 省 70–90%

训练和推理的主算力都在 FFN 上（占 Transformer Block 的 2/3~3/4 FLOPs）。MoE 把 FFN 算力乘以 K/N 的系数，所以：

- **同样激活参数，总参数大 4–16 倍** → 表达能力大幅提升
- **同样总参数，FLOPs 少 70–90%** → 训练和推理都便宜

直觉上，MoE 的学习定律近似：**模型质量取决于总参数，计算成本取决于激活参数**。这是一个极其划算的交易。

### 1.3 训练 vs 推理成本的不对称

MoE 在”训练 TCO”上的优势是实打实的：DeepSeek-V3 只用 2048 张 H800、不到两个月就训完一个 671B 模型，官方估算 GPU 租赁成本 $5.6M——同等质量的稠密模型至少要 10 倍算力。

但在**推理部署**上要打一个折扣：

|维度|稠密 70B|MoE 236B/21B 激活|
|---|---|---|
|算力（FLOPs/token）|140G|42G（-70%）|
|显存（FP16 权重）|140 GB|472 GB（+237%）|
|显存带宽压力|一次性扫 70B|每 token 扫不同专家|
|Batch 友好度|高|低（路由分散）|

结论：MoE 偏向”**算力敏感、显存充裕、batch 巨大**”的场景，比如大厂中心化推理；对边缘端、单机小批量推理并不友好。这也是为什么 Mistral 后续出了 Mistral-Large 稠密、DeepSeek 也保留 V3-Lite 稠密版的原因。

## 二、MoE 的三次里程碑

### 2.1 Shazeer 2017：Sparsely-Gated MoE

Noam Shazeer 等人在 LSTM 时代提出了 Sparsely-Gated Mixture-of-Experts Layer，把 MoE 塞进 RNN 的 stack 里，首次证明稀疏激活能扩展到 1370 亿参数规模。这篇论文定义了后来所有 MoE 工作的基础：**门控 + Top-K + 负载均衡辅助损失**。

### 2.2 GShard 2020：MoE × Transformer × TPU

Google Brain 的 GShard 把 MoE 正式嫁接到 Transformer FFN 层，并解决了工程落地的几个关键问题：

- **Expert Parallel**：专家分布到不同 device，前后加 All-to-All
- **Capacity Factor**：每个专家最多处理的 token 数有上限，溢出的 token 丢弃（drop）或 residual 透传
- **Auxiliary Load Balancing Loss**：防止专家利用率不均

GShard 在 600B MoE 上做 100 种语言翻译，这是 MoE 第一次跑到”真正的大模型”规模。

### 2.3 Switch Transformer 2021：Top-1 极简路由

Google 的 Switch Transformer 把 K 从 2 降到 1——每个 token 只进一个专家。这个”看似粗暴”的简化带来了：

- 通信量减半（All-to-All 一次而不是两次）
- 路由逻辑变简单、梯度更稳定
- 配合 bf16、稀疏 kernel，1.6T 模型训到 SOTA

Switch 是”**MoE 可以粗暴工程化**”这一派的代表。

### 2.4 2024 年的复兴：Mixtral 点燃开源

2023 年 12 月 Mistral AI 放出 Mixtral 8×7B，第一次让开源社区拿到了能跑、能微调、质量逼近 GPT-3.5 的 MoE。2024 年之后 Mixtral 8×22B、DeepSeek-V2/V3、Qwen2.5-MoE、Grok-1（314B）、Kimi K2、Databricks DBRX、Snowflake Arctic 接踵而来，MoE 从”研究项目”变成”默认架构”。

## 三、当代 MoE 模型盘点

      
|模型|年份|总参数|激活|专家数|Top-K|备注|
|---|---|---|---|---|---|---|
|GShard|2020|600B|~|2048|2|机器翻译|
|Switch-XXL|2021|1.6T|~|2048|1|Google|
|GLaM|2021|1.2T|96B|64|2|Google|
|GPT-4（传闻）|2023|~1.8T|~220B|8|2|8×220B，未官方确认|
|Mixtral 8×7B|2023|46.7B|12.9B|8|2|Mistral 开源|
|Mixtral 8×22B|2024|141B|39B|8|2|开源旗舰|
|DBRX|2024|132B|36B|16|4|Databricks|
|Grok-1|2024|314B|79B|8|2|xAI 开源|
|Arctic|2024|480B|17B|128|2|Snowflake，极稀疏|
|Qwen2.5-MoE-A14B|2024|57B|14B|60+4|4|细粒度 + 共享|
|DeepSeek-V2|2024|236B|21B|160+2|6|细粒度 + 共享|
|DeepSeek-V3|2024|671B|37B|256+1|8|Sigmoid 门控、无辅助损失|
|DeepSeek-V3.1|2025|671B|37B|256+1|8|V3 续作|
|Kimi K2|2025|~1T|~32B|384|8|Moonshot|

**几个趋势**：

1. **专家数越来越多，专家越来越小**（DeepSeek、Arctic、Kimi 的细粒度路线）
2. **共享专家（Shared Expert）开始普及**（V2/V3、Qwen2.5-MoE）
3. **Top-K 从 2 升到 6–8**（配合细粒度专家）
4. **路由从 softmax 转向 sigmoid**（DeepSeek V3）
5. **负载均衡从辅助损失转向 bias adjustment**（DeepSeek V3）

## 四、门控网络（Gating / Router）

### 4.1 基础形式

门控网络是一个极小的线性层：输入 token 的 hidden state，输出 N 个专家上的分数。

```
# 经典 softmax + top-k 门控
class TopKGate(nn.Module):
    def __init__(self, d_model, n_experts, top_k):
        super().__init__()
        self.w_gate = nn.Linear(d_model, n_experts, bias=False)
        self.top_k = top_k

    def forward(self, x):                          # x: [B*T, D]
        logits = self.w_gate(x)                    # [B*T, N]
        scores = logits.softmax(dim=-1)            # [B*T, N]
        topk_val, topk_idx = scores.topk(self.top_k, dim=-1)
        topk_val = topk_val / topk_val.sum(-1, keepdim=True)  # 重新归一化
        return topk_idx, topk_val                  # 路由索引与权重
```

### 4.2 Top-1 / Top-2 / Top-K 的取舍

- **Top-1（Switch）**：通信最省，但信号稀疏，容易抖动
- **Top-2（GShard、Mixtral、Grok）**：工程甜区，两个专家加权平均
- **Top-K（DeepSeek V2/V3 K=6/8，Kimi K=8）**：配合细粒度专家使用，单个专家小所以 K 大也便宜

### 4.3 Softmax → Sigmoid：DeepSeek V3 的改动

DeepSeek V3 把门控从 softmax 换成了 sigmoid，然后对 Top-K 的分数做归一化：

```
scores = torch.sigmoid(self.w_gate(x))              # 独立 sigmoid，不互斥
topk_val, topk_idx = scores.topk(k, dim=-1)
gate_w = topk_val / topk_val.sum(-1, keepdim=True)  # renormalize
```

好处：

- Sigmoid 不强制 N 个专家的分数”互斥”（softmax 会），每个专家打分独立
- 数值更稳定，专家越多时 softmax 容易数值坍缩
- 为后面”无辅助损失”的 bias adjustment 留了空间

### 4.4 Noisy Gating 与 Jitter

为了鼓励探索，一些实现会在 gate logits 上加高斯噪声（仅训练时）：

```
if self.training:
    noise = torch.randn_like(logits) * F.softplus(self.w_noise(x))
    logits = logits + noise
```

这招在早期训练特别有用，防止某几个专家先”跑赢”后吃掉所有流量。

## 五、共享专家 + 路由专家

DeepSeek MoE 论文提出了一个影响很大的设计：**Shared Experts + Routed Experts**。

- **共享专家（Shared Expert）**：1–2 个专家，所有 token 都走，负责通用能力
- **路由专家（Routed Expert）**：N 个专家，走 Top-K 路由，负责差异化能力

```
y = shared_expert(x) + Σ_{i ∈ TopK} gate_i × routed_expert_i(x)
```

动机：门控路由存在”**冷启动**”和”**冗余**”问题——很多专家其实学到了高度重叠的通用知识。把这部分显式放到一个共享专家里，路由专家就可以更专注于差异化表征。

Qwen2.5-MoE、DeepSeek-V2/V3、Kimi K2 都采用了这一设计。共享专家的容量通常是路由专家的 1–2 倍。

## 六、负载均衡：让专家”不打架也不闲着”

### 6.1 专家坍缩与抖动

MoE 训练最头疼的两个问题：

1. **Expert Collapse（专家坍缩）**：某几个专家因为初始化或早期运气，被反复路由，其他专家永远收不到 token，训不动
2. **Load Imbalance**：某个 batch 中 80% 的 token 去了 3 个专家，剩下 N-3 个闲着——这会严重拖慢 EP 的 All-to-All，因为短板专家是瓶颈

### 6.2 Auxiliary Load Balancing Loss（GShard 式）

经典解法：加一项辅助损失，惩罚”路由分数方差 × 实际负载方差”。

```
def aux_loss(gate_probs, expert_mask, n_experts):
    # gate_probs: [B*T, N]   每个 token 在每个专家上的概率
    # expert_mask: [B*T, N]  one-hot（或 top-k mask）
    f_i = expert_mask.float().mean(0)     # 实际负载比例
    P_i = gate_probs.mean(0)              # 平均路由概率
    return n_experts * (f_i * P_i).sum()  # 乘 N 使期望值为 1
```

这项 loss 加在主 loss 上，系数通常 0.01~0.1。所有主流 MoE（GShard、Switch、Mixtral）都用它。

### 6.3 DeepSeek V3：无辅助损失的 Bias Adjustment

V3 提出**不用辅助损失**，而是给每个专家加一个可动态调整的 bias：

```
adjusted_logits = gate_logits + bias          # bias 仅影响路由，不进梯度
topk_idx = adjusted_logits.topk(k)
gate_w = sigmoid(gate_logits[topk_idx])       # 权重用原始 logits 算
```

训练循环里：

- 统计每个专家最近 N 步的负载
- 负载偏高的专家：`bias -= γ`
- 负载偏低的专家：`bias += γ`
- γ 是一个极小的步长，在线调整

好处：

- 辅助损失会”污染”主目标的梯度（有时会让模型性能略降）
- Bias 不参与梯度，负载调节和任务学习完全解耦
- 实测 V3 在 2048 卡上 EP 利用率非常均衡

这是一个工程上很优雅的动作，被认为是 V3 众多亮点之一。

### 6.4 Capacity Factor 与 Token Drop

即使有负载均衡，瞬时不均是不可避免的。工程上会给每个专家设一个**容量**：

```
capacity = capacity_factor × (tokens_per_batch / n_experts × top_k)
```

`capacity_factor` 典型 1.0~1.25：

- 超容的 token 被 drop（走 residual 不过 FFN），或者回退到次优专家
- Drop 率是训练监控的核心指标（健康 < 1%）

## 七、Expert Parallel（EP）

### 7.1 把专家切到不同 GPU

EP 的思路：**N 个专家分散到 EP_SIZE 张 GPU 上**，每张 GPU 负责 N/EP_SIZE 个专家。前向时需要把每个 token “送到它该去的那张 GPU”，反向时再送回来——这就是 **All-to-All**。

```
GPU0: Expert 0, 1
GPU1: Expert 2, 3
GPU2: Expert 4, 5
GPU3: Expert 6, 7     # Mixtral 8 专家 EP=4
```

### 7.2 为什么不用 TP 切专家

可以切，但不划算。专家内部的 FFN 很小（比如 DeepSeek V3 每个路由专家只有 ~2B 参数），切了通信开销大于收益。EP 是专为 MoE 设计的维度：**不是切单个专家的内部，而是把专家当作整体、在专家层面切分**。

### 7.3 五维并行的完整组合

现代 MoE 大规模训练往往是：

```
TP × PP × EP × DP × SP    （SP = Sequence Parallel）
```

- **TP（Tensor Parallel）**：切 Attention 和 shared expert 的矩阵
- **PP（Pipeline Parallel）**：切 Transformer 层
- **EP（Expert Parallel）**：切 MoE 层的专家
- **DP（Data Parallel）**：batch 方向复制
- **SP（Sequence Parallel）**：序列长度维度切 LayerNorm/Dropout

DeepSeek V3 的公开配置（2048×H800）：**PP=16, EP=64, DP=2**（无显式 TP，靠 EP + FSDP 等价达成）。

```
世界大小 = TP × PP × EP × DP = 2048
```

## 八、All-to-All：MoE 的通信瓶颈

### 8.1 为什么是 All-to-All

MoE 每层有两次重排：

1. **Dispatch**：每张 GPU 有一批 token，它们各自该去不同专家（分布在不同 GPU）→ All-to-All
2. **Combine**：专家计算完，结果要送回 token 原 GPU → All-to-All

在 8 专家 EP=8 的极端情况下，每层 MoE 产生 2 次 All-to-All。一个 60 层的 MoE 一次前向就是 120 次跨机通信。如果通信没打平，算力直接空转。

### 8.2 All-to-All 通信图

![All-to-All 通信图](https://quant67.com/post/llm-infra/08-moe-training/images/08-moe-training-fig1.svg)

### 8.3 DeepEP：DeepSeek 开源的 All-to-All 库

V3 发布后 DeepSeek 开源了 DeepEP，专为 MoE All-to-All 优化。核心设计：

- **机内 NVLink + 机间 IB 双路径**：先把同机 8 张卡上的 token 通过 NVLink 汇聚，再跨机走 IB；反向亦然
- **PXN（跨卡直连）技术**：利用 NVLink + NVSwitch 拓扑，让跨机通信也能借道 NVLink 加速
- **FP8 通信**：token 在 All-to-All 时以 FP8 传输，带宽减半
- **内核级重叠**：用 CUDA graph + 异步 stream 把 Dispatch、Combine、专家计算流水起来

实测 DeepEP 在 H800 集群上相比 PyTorch 原生 `all_to_all_single` 能达到 2–3× 吞吐。

### 8.4 MegaBlocks：把稀疏 MoE 当稀疏矩阵算

Stanford + Databricks 的 MegaBlocks 走另一条路：**不做 token 重排**，而是把 MoE 重写成**块稀疏矩阵乘法**（Block Sparse Matmul）。

```
[T, D] × [D, N×H]  只在被路由到的块上做 matmul
```

好处：

- 没有 capacity factor，没有 token drop
- 利用专用的 sparse kernel（基于 CUTLASS），GPU 利用率高
- Databricks DBRX、Mosaic 的训练栈基于此

坏处：EP 跨机时仍需 All-to-All，MegaBlocks 主要优化了单机多卡场景。

### 8.5 Tutel：微软的 MoE 通信栈

Microsoft 的 Tutel 强调**自适应并行**：运行时根据 token 分布动态切换 EP 模式（batch 维度 vs 专家维度），也是较早把 MoE All-to-All 工程化的项目之一。

## 九、工程实现：一个简化的 MoE 层

下面给一个最小可跑的 PyTorch 版本，省掉 EP（单卡版），用来说清楚路由和计算的基本结构。

```
import torch
import torch.nn as nn
import torch.nn.functional as F


class Expert(nn.Module):
    """一个标准 SwiGLU FFN 作为单个专家"""
    def __init__(self, d_model, d_ff):
        super().__init__()
        self.w1 = nn.Linear(d_model, d_ff, bias=False)
        self.w2 = nn.Linear(d_ff, d_model, bias=False)
        self.w3 = nn.Linear(d_model, d_ff, bias=False)

    def forward(self, x):
        return self.w2(F.silu(self.w1(x)) * self.w3(x))


class MoELayer(nn.Module):
    def __init__(self, d_model, d_ff, n_experts, top_k,
                 n_shared=1, use_bias_balance=True):
        super().__init__()
        self.n_experts = n_experts
        self.top_k = top_k
        self.routed = nn.ModuleList([Expert(d_model, d_ff) for _ in range(n_experts)])
        self.shared = nn.ModuleList([Expert(d_model, d_ff) for _ in range(n_shared)])
        self.gate = nn.Linear(d_model, n_experts, bias=False)
        self.use_bias_balance = use_bias_balance
        if use_bias_balance:
            self.register_buffer("route_bias", torch.zeros(n_experts))

    def forward(self, x):
        B, T, D = x.shape
        x_flat = x.reshape(-1, D)                               # [N_tok, D]

        # --- 1. 门控：DeepSeek V3 风格 sigmoid + Top-K ---
        logits = self.gate(x_flat)                              # [N_tok, E]
        routing = logits + (self.route_bias if self.use_bias_balance else 0)
        topk_val, topk_idx = routing.topk(self.top_k, dim=-1)   # [N_tok, K]
        gate_w = torch.sigmoid(logits.gather(-1, topk_idx))
        gate_w = gate_w / gate_w.sum(-1, keepdim=True)          # renorm

        # --- 2. 路由专家：循环伪实现，生产代码应换成 scatter / group-gemm ---
        out = torch.zeros_like(x_flat)
        for e in range(self.n_experts):
            # 找出选中专家 e 的 token（在 K 中任一位置）
            mask = (topk_idx == e)
            if not mask.any():
                continue
            # 获取相应权重
            tok_idx, k_idx = mask.nonzero(as_tuple=True)
            w = gate_w[tok_idx, k_idx].unsqueeze(-1)            # [n_sel, 1]
            x_sel = x_flat[tok_idx]
            y_sel = self.routed[e](x_sel) * w
            out.index_add_(0, tok_idx, y_sel)

        # --- 3. 共享专家：所有 token 都走 ---
        for sh in self.shared:
            out = out + sh(x_flat)

        # --- 4. 统计负载（供外部 bias 调整 & 观测） ---
        with torch.no_grad():
            load = torch.zeros(self.n_experts, device=x.device)
            load.scatter_add_(
                0, topk_idx.reshape(-1),
                torch.ones_like(topk_idx.reshape(-1), dtype=torch.float)
            )
            self.load_stat = load / load.sum()                   # [E]

        return out.reshape(B, T, D)

    @torch.no_grad()
    def update_balance_bias(self, gamma=1e-3, target=None):
        """DeepSeek V3 式：按最近一批负载在线调整 bias"""
        if not self.use_bias_balance:
            return
        target = target if target is not None else 1.0 / self.n_experts
        self.route_bias -= gamma * (self.load_stat - target).sign() * self.load_stat.clamp(min=1e-6)
```

一些工程补充：

- 真实实现会用 `scatter` + 分组 `gmm`（group gemm）把所有 token 按专家聚合，一次 batch 一个专家
- EP 版本会在 dispatch 前做 All-to-All，专家本地计算，combine 再 All-to-All
- `update_balance_bias` 每 N 步调用一次，不进 autograd

## 十、MoE 层结构图

![MoE 层结构图](https://quant67.com/post/llm-infra/08-moe-training/images/08-moe-training-fig2.svg)

## 十一、训练中的典型问题与对策

### 11.1 专家坍缩

**现象**：tensorboard 上部分专家 load 长期 < 1/N 的 1/4，甚至归零。

对策： - 辅助损失系数从 0.01 升到 0.1 - 训练初期用 Noisy Gating - V3 风格 bias adjustment，γ 适当调大 - Re-init 坍缩专家（极端情况）

### 11.2 路由抖动

**现象**：相近的 token 在连续步骤中被路由到完全不同的专家，梯度方差大。

对策： - Top-K 从 1 升到 2+ - 加 jitter noise 温度，训练后期退火到 0 - EMA（滑动平均）风格的 gate stats 用在 bias 调整上，而不是即时统计

### 11.3 稀疏反向传播

MoE 的反向比稠密复杂得多：只有被激活的专家参与反向，不同 batch 的计算图结构不同。工程上：

- **梯度累积**要小心：不同 step 激活的专家不同，Optimizer 更新要正确处理”本 step 没被激活的参数无梯度”
- **ZeRO-1/2 + EP**：优化器状态按专家分布，不是按 DP 分布
- **梯度同步**：共享专家走 DP 全员 allreduce，路由专家按 EP 组 allreduce

### 11.4 Dropout / Token Drop

- **Router Dropout**：训练时随机屏蔽少数 token 不过 MoE（直接 residual），可以缓解过拟合，Switch Transformer 用过
- **Expert Dropout**：训练时随机屏蔽一个专家，强制其他专家冗余学习

## 十二、训练栈对比

   
|项目|核心定位|MoE 实现方式|代表用户|
|---|---|---|---|
|**Megatron-MoE**|TP/PP/EP 一体|基于 group gemm + All-to-All|NVIDIA、国内各家|
|**DeepSpeed-MoE**|EP + ZeRO|优化器分区 + 灵活 EP 拓扑|早期 MS / 微调场景|
|**MegaBlocks**|块稀疏 matmul|无 drop、高利用率单机|Databricks DBRX、Mosaic|
|**Tutel**|自适应 MoE 通信|运行时切换 EP 模式|微软内部、OpenPAI|
|**DeepEP**|极致 All-to-All|NVLink/IB 双路径、FP8|DeepSeek、清华、国内部分团队|
|**DeepGEMM**|FP8 group gemm|配合 DeepEP 做 MoE kernel|DeepSeek V3|
|**Colossal-MoE**|开源五维并行|国产 MoE 框架|国内创业公司|

选型指引：

- 做 **SFT / 微调 MoE**：DeepSpeed-MoE 或 HuggingFace + MegaBlocks，简单
- 做 **千卡 pretrain**：Megatron-MoE（NVIDIA 主推），成熟
- 做 **万卡 pretrain**：Megatron-MoE + DeepEP + FP8，像 V3 一样
- 做 **单机多卡高利用率**：MegaBlocks（无 drop 真的香）

## 十二点五、EP 版 MoE 的完整实现骨架

前面给的 MoELayer 是单卡版。生产中的 EP 版本结构更复杂，下面给一个有代表性的骨架（省略 CUDA 细节，用 `torch.distributed` 伪实现）。

```
import torch
import torch.distributed as dist
import torch.nn as nn
import torch.nn.functional as F


class EPMoELayer(nn.Module):
    """Expert Parallel 版 MoE：每 rank 持有 N/EP_SIZE 个本地专家"""

    def __init__(self, d_model, d_ff, n_experts, top_k,
                 ep_group: dist.ProcessGroup):
        super().__init__()
        self.ep_group = ep_group
        self.ep_size = dist.get_world_size(ep_group)
        self.ep_rank = dist.get_rank(ep_group)
        assert n_experts % self.ep_size == 0
        self.n_experts = n_experts
        self.n_local = n_experts // self.ep_size
        self.top_k = top_k

        self.gate = nn.Linear(d_model, n_experts, bias=False)
        self.local_experts = nn.ModuleList(
            [Expert(d_model, d_ff) for _ in range(self.n_local)]
        )

    def forward(self, x):
        B, T, D = x.shape
        x_flat = x.reshape(-1, D)                             # [N, D]
        N = x_flat.size(0)

        # 1. 路由
        logits = self.gate(x_flat)
        scores = torch.sigmoid(logits)
        topk_val, topk_idx = scores.topk(self.top_k, dim=-1)
        gate_w = topk_val / topk_val.sum(-1, keepdim=True)

        # 2. 按目标 rank 分桶（每个 token 有 K 份拷贝）
        target_rank = topk_idx // self.n_local                # [N, K]
        flat_idx = topk_idx.reshape(-1)                       # [N*K]
        flat_rank = target_rank.reshape(-1)
        flat_weight = gate_w.reshape(-1)

        # 重排：同 rank 的 token 放一起
        sort_rank, sort_perm = flat_rank.sort()
        sorted_tok = x_flat.repeat_interleave(self.top_k, dim=0)[sort_perm]
        sorted_expert = flat_idx[sort_perm] % self.n_local
        sorted_weight = flat_weight[sort_perm]

        # 计算每个 rank 的发送长度
        send_counts = torch.bincount(sort_rank, minlength=self.ep_size)
        recv_counts = torch.empty_like(send_counts)
        dist.all_to_all_single(recv_counts, send_counts,
                               group=self.ep_group)

        # 3. All-to-All Dispatch
        recv_tok = torch.empty(
            (recv_counts.sum(), D), dtype=sorted_tok.dtype, device=x.device
        )
        recv_expert = torch.empty(recv_counts.sum(), dtype=torch.long, device=x.device)
        dist.all_to_all_single(
            recv_tok, sorted_tok,
            output_split_sizes=recv_counts.tolist(),
            input_split_sizes=send_counts.tolist(),
            group=self.ep_group,
        )
        dist.all_to_all_single(
            recv_expert, sorted_expert,
            output_split_sizes=recv_counts.tolist(),
            input_split_sizes=send_counts.tolist(),
            group=self.ep_group,
        )

        # 4. 本地 group gemm：按专家聚合
        out_local = torch.empty_like(recv_tok)
        for e in range(self.n_local):
            mask = recv_expert == e
            if mask.any():
                out_local[mask] = self.local_experts[e](recv_tok[mask])

        # 5. All-to-All Combine（反向送回来）
        back_tok = torch.empty_like(sorted_tok)
        dist.all_to_all_single(
            back_tok, out_local,
            output_split_sizes=send_counts.tolist(),
            input_split_sizes=recv_counts.tolist(),
            group=self.ep_group,
        )

        # 6. 反排 + 加权累加
        back_tok = back_tok * sorted_weight.unsqueeze(-1)
        unsort_perm = torch.empty_like(sort_perm)
        unsort_perm[sort_perm] = torch.arange(
            sort_perm.size(0), device=x.device
        )
        flat_back = back_tok[unsort_perm]                     # [N*K, D]
        flat_back = flat_back.view(N, self.top_k, D).sum(dim=1)

        return flat_back.view(B, T, D)
```

几个工程要点：

1. 这里用了**两次 All-to-All**（dispatch + combine），生产实现会合并部分元信息
2. `for e in range(self.n_local)` 在生产中换成 **group gemm**（CUTLASS/DeepGEMM）
3. FP8 版本会在发送前 cast 到 FP8，接收后再反 cast
4. 真实 DeepEP 不走 NCCL 的 all_to_all_single，而是定制 CUDA kernel 实现 NVLink + IB 双路径

## 十二点六、MoE 微调（SFT / LoRA）

社区常见需求：拿到 Mixtral 8×22B 或 DeepSeek-V3，在业务数据上做 SFT。几个工程坑：

### 12.6.1 路由漂移（Router Drift）

如果直接做全参数 SFT，极少量的业务数据可能把 gate 训歪，导致原本均衡的路由变得极不均衡。对策：

- **冻结 gate**：gate 不更新，只微调专家和 attention
- **冻结部分专家**：只调 1–2 个”业务专属”专家
- **LoRA on experts**：每个专家挂 LoRA，gate 保持原始权重

### 12.6.2 MoE 专用 LoRA

稠密模型 LoRA 对所有 Linear 层加 ΔW = BA；MoE 里每个专家都有独立 FFN，可以选择：

- **共享 LoRA**：所有专家共用同一对 A/B，参数量小，但表达弱
- **独立 LoRA**：每个专家独立 A/B，参数量 ∝ N_experts
- **Routed LoRA**：LoRA 本身也做 Top-K 路由，适合超大 MoE

Mixtral-Instruct、DeepSeek-V2-Chat 的社区微调基本采用”**独立 LoRA + 冻结 gate**”组合。

### 12.6.3 MoE 的模型合并（Merging）

Mixtral 出来后社区出现了”**MoE-Merge**”：从多个稠密微调模型合并成一个 MoE（每个微调模型作为一个专家）。代表工具 mergekit 的 `mixtral` 模式：

```
base_model: mistralai/Mistral-7B-v0.1
gate_mode: hidden   # 用 hidden state 训练 gate
experts:
  - source_model: code-model
    positive_prompts: ["write code", "python"]
  - source_model: math-model
    positive_prompts: ["solve", "calculate"]
  - source_model: chat-model
    positive_prompts: ["hello", "chat"]
```

这不是”真正训练出来的 MoE”，但在工程上是一种**零训练 MoE**的捷径，社区 DIY 模型常见。

## 十二点七、MoE 的调试经验

MoE 训练失败往往”表面上看损失正常、模型就是不收敛”。几个经验规则：

1. **先盯 load 分布**：发现坍缩就立即干预，越早越好
2. **gate logits 的范数**不该爆炸或归零；监控 `||gate.weight||`
3. **token drop 率**上升通常意味着数据分布突变（比如换了语料）
4. **专家输出范数差异**：某专家输出明显大于其他，往往是坍缩前兆
5. **aux loss 曲线**：如果一路猛涨，说明主 loss 和 aux loss 在”打架”，要么调权重，要么改 V3 式 bias
6. **先小后大**：新 MoE 结构，先在 8 专家、百万参数规模调通，再放大；结构 bug 在小规模就暴露

一个经典踩坑：**混精度下 softmax gate 的数值不稳定**。专家数 >64 时，BF16 softmax 输入动态范围容易超限，导致 top-k 选择不稳定。解法：gate 的 softmax 在 FP32 里算（`gate.float().softmax(-1)`），整体计算图里只有这一步回 FP32。这也是 V3 干脆换 sigmoid 的诱因之一。

DeepSeek-V3 技术报告公开了相当详细的工程数据，可以作为当代 MoE 训练的教科书案例。

|项目|数值|
|---|---|
|总参数|671B（路由 256 + 共享 1）|
|激活参数|37B（Top-8）|
|训练 token|14.8T|
|GPU|2048 × H800（80GB）|
|训练时长|2.664M H800 GPU 小时（≈ 54 天连续）|
|估算成本|5.576M（2/hour GPU 租赁）|
|并行|PP=16, EP=64, DP=2|
|精度|FP8 训练（BF16 主权重）+ FP8 All-to-All|
|关键组件|DeepEP、DeepGEMM、无辅助损失负载均衡、MTP|

几个值得记住的”工程动作”：

1. **FP8 训练主干**：矩阵乘用 FP8，accumulator 用 FP32；权重存 BF16
2. **FP8 All-to-All**：token 在网络上以 FP8 传输，带宽减半
3. **无辅助损失负载均衡**：bias adjustment 替代 aux loss
4. **MTP（Multi-Token Prediction）**：每步同时预测下一个和下下个 token，提高训练信号密度
5. **双路径 All-to-All（DeepEP）**：NVLink + IB 分层
6. **Pipeline Bubble 优化**：DualPipe 算法，把 attention/FFN 分成两个 micro-step 交错

对比：同等能力的稠密模型（假定 400B 稠密）估算训练成本在 $50M+，**MoE 路线给 DeepSeek 省了 ~10×**。

## 十三点五、细粒度专家（Fine-Grained Experts）深入

DeepSeek MoE 论文的另一贡献是系统论证了”**更多但更小的专家**”为什么好。传统 MoE（Mixtral）是 8 专家、专家大小接近完整 FFN；DeepSeekMoE / V2 / V3 走向 64 → 160 → 256 专家、每个专家只有完整 FFN 的 1/8 甚至 1/16 大小。

### 13.5.1 为什么细粒度更好

给定激活算力预算（比如 Top-K × 专家大小 = 常量），细粒度路线有两个理论优势：

1. **组合数爆炸**：从 8 专家选 2 只有 C(8,2)=28 种组合；从 256 选 8 有 C(256,8) ≈ 4×10¹¹ 种。理论表达空间呈组合爆炸
2. **专家更专业**：小专家更容易”学到一件事”，大专家则往往学成通用 FFN 的稀释版

代价是通信复杂度更高——Top-K 的 K 更大，All-to-All 载荷中 token 会被复制 K 份发往不同专家。这就是为什么 DeepSeek 必须配套开发 DeepEP 这样的定制通信库。

### 13.5.2 工程实现差异

|维度|Mixtral 风格|DeepSeek 风格|
|---|---|---|
|专家数|8|160–256|
|每专家 d_ff|14336（相当于稠密 FFN）|1408–2048（1/8 ~ 1/10）|
|Top-K|2|6–8|
|共享专家|无|1–2|
|负载均衡|aux loss|bias adjustment|
|门控|softmax|sigmoid|
|通信敏感度|低|高（需 DeepEP）|

工程选择上：算力充裕、网络强（NVLink + IB）可以走 DeepSeek 路线；算力紧、网络弱（比如消费 GPU 集群）建议走 Mixtral 路线。

## 十三点六、FP8 训练与 MoE 的联动

V3 的另一大亮点是把 MoE 和 FP8 训练有机结合。

### 13.6.1 为什么 MoE 更适合 FP8

- **专家 GEMM 的规模变小**（细粒度专家），FP8 的”范围不足”问题相对缓和
- **All-to-All 带宽是主瓶颈**，FP8 直接把通信量减半
- **梯度累加** accumulator 用 FP32，实测精度损失可控

### 13.6.2 实现要点

```
Forward  :  act(BF16) × weight(FP8) → out(BF16)     # scaling per-tile
All-to-All: 传输前 cast BF16 → FP8（per-token scale）
Backward : grad(BF16) × weight_T(FP8) → grad_in(BF16)
Optim    : Master weight BF16，Adam states FP32（或 8bit）
```

关键是 **per-tile scaling**（不是整 tensor 一个 scale）——专家输出分布差异巨大，整 tensor scaling 会导致低幅度专家被截断。

## 十三点七、MTP（Multi-Token Prediction）在 MoE 中的意义

V3 还引入了 MTP：每个位置同时预测 token t+1 和 t+2（训练时）。MTP 的核心作用是”提高训练 token 的信号密度”——等效于把 14.8T 训练语料”放大”了接近 2×。

对 MoE 尤其关键，因为：

1. MoE 的路由噪声让每 token 的有效梯度比稠密小
2. MTP 提供更稠密的监督，缓解这个问题
3. 推理时 MTP 还可当 **speculative decoding 的 draft model**，一举两得

## 十三点八、DualPipe：MoE 流水线的气泡治理

PP 本身有气泡（bubble），传统 1F1B 流水线的气泡占比 `(pp-1)/(pp-1 + micro_batches)`。MoE 里因为 All-to-All 让每个 micro-step 变长，气泡成本也变大。

DeepSeek DualPipe 的思路：**把一个 Transformer Block 的前向拆成 attention + MoE 两段**，让前向和反向、attention 和 MoE 在时间轴上交错，用另一个 micro-batch 的反向”填”进本 micro-batch 的 All-to-All 等待时间。实测 V3 的 PP 气泡从 ~10% 降到 ~3%。

实现成本较高：需要手动重写 pipeline schedule，对 autograd 图做切分和重连。这也是 V3 工程实现里最难的几个点之一。

## 十三点九、监控与可观测

MoE 训练的监控项比稠密模型多一倍，工程上强烈建议把下面几类指标放进 TensorBoard / Prometheus：

|指标|健康范围|报警|
|---|---|---|
|每专家 load（占比）|1/N ± 20%|单专家 < 0.3/N|
|Token drop 率|< 1%|> 5%|
|路由 entropy|> log(top_k) 的 80%|持续下降 → 过拟合门控|
|Aux loss（若用）|0.001 – 0.01|失控上升|
|Bias 最大值（V3 式）|\| bias \| < 0.5|超出 → 严重不均|
|All-to-All 耗时 / 步|< 20% step time|> 40% → 网络问题|
|专家 grad norm|同量级|某专家归零 → 坍缩|

另一个强烈建议：**把专家激活热图可视化**。横轴 专家编号，纵轴 训练步，颜色 load——专家坍缩、冷热分布等问题一眼看出。DeepSeek 和 Qwen 在技术报告里都展示过这种图。

```
# 简化的监控 hook
class MoEMonitor:
    def __init__(self, layer: MoELayer, window=1000):
        self.layer = layer
        self.window = window
        self.history = []

    def step(self):
        self.history.append(self.layer.load_stat.detach().cpu().clone())
        if len(self.history) > self.window:
            self.history.pop(0)
        recent = torch.stack(self.history[-100:]).mean(0)
        entropy = -(recent * (recent + 1e-9).log()).sum()
        drop = (recent < 0.3 / len(recent)).float().sum()
        return {"min_load": recent.min(), "entropy": entropy, "cold_experts": drop}
```

## 十三点十、国内 MoE 生态现状（2025）

除 DeepSeek 外的国内 MoE：

- **Qwen3-MoE**（阿里）：继续细粒度路线，开源最大规模 MoE 之一
- **Kimi K2**（Moonshot）：~1T 总参数，超大专家数（384），Sigmoid + 独立 token buffer
- **GLM-4.5-MoE**（智谱）：较保守路线，8 专家 Top-2
- **豆包 / 云雀**（字节）：内部大量使用 MoE，细节未公开
- **MiniMax ABAB-MoE**：业界较早 MoE 实践者之一
- **百川 Baichuan-MoE、昆仑万维天工 MoE**：跟进

框架侧，华为昇腾 MindSpore 提供原生 MoE 支持；百度飞桨 PaddleNLP、阿里 PAI 也都有 MoE 适配。DeepEP 开源后几乎成为国内千卡集群 MoE 训练的事实标准之一。

## 十四、MoE 的推理困局（承上启下）

训练省下的 FLOPs 不会白给，推理要付一部分回来：

1. **显存墙**：671B FP8 也要 ~670GB，必须多机部署
2. **带宽墙**：每 token 访问 37B 不同专家，显存带宽利用率低
3. **batch 要大**：否则每个专家的 token 数太少，group gemm 打不满
4. **All-to-All 仍在**：推理阶段也要做，延迟敏感

这些问题推动了**推理侧 MoE 专用优化**：专家缓存、预取、专家合并、低精度专家等。这些会在后续 [推理引擎基础](https://quant67.com/post/llm-infra/11-inference-basics/11-inference-basics.html)、[vLLM / SGLang / TensorRT-LLM](https://quant67.com/post/llm-infra/13-vllm-sglang/13-vllm-sglang.html) 等篇展开。

## 十四点五、MoE 训练资源估算公式

对架构师和集群 capacity planner 最实用的是一组估算公式。以下符号：N_total 总参数、N_act 激活参数、T token 数、K Top-K、P GPU 数、U 单卡有效算力（TFLOPS）。

### 14.5.1 训练算力

稠密：`FLOPs ≈ 6 × N_total × T` MoE：`FLOPs ≈ 6 × N_act × T + overhead(gate, aux loss)`

以 V3 为例：`6 × 37e9 × 14.8e12 ≈ 3.3e24 FLOPs`。H800 FP8 理论 ~1500 TFLOPs，实测有效算力 ~40–50%，即 ~650 TFLOPs。

`GPU-hours = 3.3e24 / (650e12 × 3600) ≈ 1.41M H800 小时`

实测 V3 报告 2.66M 小时，差距来自 All-to-All 开销、气泡、checkpoint 重算等。经验系数 ≈ 1.8–2.2×。

### 14.5.2 显存估算

每个 EP rank 持有：

```
本 rank 显存 = (N_total / EP + N_shared + N_attention) × bytes_per_param
            + 激活值（取决于 micro batch 和序列长）
            + 优化器状态（如 ZeRO-1：1/DP；Adam → 3× 参数）
            + KV cache（如果训推一体）
```

以 V3 + EP=64：每 rank 专家参数 ≈ 671B / 64 ≈ 10.5B，FP8 约 10.5GB；加 Attention 共享 + 激活 + ZeRO → 单 H800 80GB 刚好可容纳（这是为什么 V3 选 EP=64）。

### 14.5.3 通信量

每层 MoE 单 token 通信量：

`comm_bytes ≈ 2 × K × D × bytes_per_elem`

V3：K=8, D=7168, FP8 → ~115KB / token / layer。61 层 MoE、每 step 4M token → **~28GB / step** 跨机通信。H800 IB 200Gbps × 8 = 200GB/s 卡聚合带宽，理论 ~0.14s / step。实测和计算比对是诊断网络瓶颈的关键手段。

## 十五、小结与展望

MoE 已经从”论文里的奇技”变成了 2024–2026 年大模型的**默认架构选项**。它的工程价值可以用一句话概括：

> 用 5× 总参数、1× 激活算力，换 2–3× 能力。

但要把这句话兑现，需要一整套工程栈配合：细粒度专家、共享专家、sigmoid + bias 负载均衡、五维并行、DeepEP 式 All-to-All、FP8 训练、MTP 训练目标、DualPipe 流水线……DeepSeek-V3 证明了这套组合拳在千卡集群上是可行的，Kimi K2、Qwen3-MoE 也跟进了这条路线。

下一步值得关注的方向：

- **万亿参数稀疏模型**（Kimi K2 已 ~1T）
- **动态专家数**（运行时增删专家）
- **专家蒸馏**（MoE 教师 → 稠密学生，推理友好）
- **MoA（Mixture of Attention）**、**MoD（Mixture of Depth）**：稀疏化从 FFN 拓展到其他组件
- **推理侧稀疏性感知调度器**（下一代 vLLM 必有）

下一篇我们转向另一条主线：**对齐工程**——RLHF、DPO 和更新的后训练方法如何在基础设施上落地。

## 十六、附：MoE 设计决策 Checklist

给工程师一个清单，作为团队内部做 MoE 设计评审的参考：

**架构层** - [ ] 专家粒度：粗（Mixtral 式）还是细（DeepSeek 式） - [ ] Top-K 与专家数的匹配：K/N 比例（V3 是 8/257 ≈ 3%） - [ ] 是否共享专家（通用能力下沉） - [ ] 门控：Softmax 还是 Sigmoid - [ ] 负载均衡：aux loss 还是 bias adjustment

**并行层** - [ ] EP_SIZE 选择：让本 rank 专家参数 ≤ 单卡显存的 40% - [ ] TP/PP/EP/DP 乘积 = 总卡数 - [ ] 是否上 ZeRO（一般 EP 模式下 ZeRO-1 够） - [ ] 通信栈：NCCL / DeepEP / MegaBlocks

**精度层** - [ ] 主权重 BF16 / FP8 - [ ] All-to-All 精度（FP8 省带宽） - [ ] Gate 是否保 FP32（高专家数必选）

**训练层** - [ ] Capacity factor 设定（1.0 稳，1.25 容灾） - [ ] Token drop 告警阈值 - [ ] 专家 load 监控 - [ ] Bias 调整步长 γ（V3 式）

**数据层** - [ ] 训练数据的语义多样性（给不同专家学习机会） - [ ] 课程学习的专家敏感度（切换数据分布时 load 会剧烈变化）

一个团队如果能在这个 checklist 上逐项给出有依据的回答，MoE 训练就基本稳了。

## 参考资料

- Shazeer et al., _Outrageously Large Neural Networks: The Sparsely-Gated Mixture-of-Experts Layer_, 2017
- Lepikhin et al., _GShard: Scaling Giant Models with Conditional Computation and Automatic Sharding_, 2020
- Fedus et al., _Switch Transformers: Scaling to Trillion Parameter Models_, 2021
- Du et al., _GLaM: Efficient Scaling of Language Models with Mixture-of-Experts_, 2021
- Jiang et al., _Mixtral of Experts_, Mistral AI, 2024
- DeepSeek-AI, _DeepSeek-V2: A Strong, Economical, and Efficient Mixture-of-Experts Language Model_, 2024
- DeepSeek-AI, _DeepSeek-V3 Technical Report_, 2024
- Dai et al., _DeepSeekMoE: Towards Ultimate Expert Specialization_, 2024
- Qwen Team, _Qwen2.5-MoE Technical Report_, 2024
- xAI, _Grok-1 Open Release_, 2024
- Databricks, _Introducing DBRX: A New State-of-the-Art Open LLM_, 2024
- Snowflake AI Research, _Arctic: A 480B Open MoE_, 2024
- Gale et al., _MegaBlocks: Efficient Sparse Training with Mixture-of-Experts_, 2022
- Hwang et al., _Tutel: Adaptive Mixture-of-Experts at Scale_, Microsoft, 2022
- DeepSeek, _DeepEP: Expert Parallel All-to-All Library_, GitHub 2025
- DeepSeek, _DeepGEMM: FP8 General Matrix Multiplication_, GitHub 2025
- NVIDIA, _Megatron-LM MoE Implementation_, GitHub
- Microsoft, _DeepSpeed-MoE: Advancing Mixture-of-Experts Inference and Training_, 2022

---

**上一篇**：[Megatron-LM 与 DeepSpeed](https://quant67.com/post/llm-infra/07-megatron-deepspeed/07-megatron-deepspeed.html) **下一篇**：[RLHF 与对齐流水线](https://quant67.com/post/llm-infra/09-rlhf-pipeline/09-rlhf-pipeline.html)

## 同主题继续阅读

把当前热点继续串成多页阅读，而不是停在单篇消费。

2026-04-22 · architecture / ai-infra

### [大模型基础设施工程](https://quant67.com/post/llm-infra/index.html)

面向中国工程团队的大模型基础设施系列。从 GPU/CUDA/互联、训练框架与 3D 并行、vLLM/SGLang 推理引擎、量化与推测解码、RAG/Agent 到服务化、网关、可观测性与安全合规，覆盖 LLMOps 全链路。

2026-04-25 · architecture / ai-infra

### [【大模型基础设施工程·特别篇】DeepSeek-V4 与国产芯片：从备份路线到主路径](https://quant67.com/post/llm-infra/26-deepseek-v4-domestic-chip/26-deepseek-v4-domestic-chip.html)

DeepSeek-V4 发布后，如果国产芯片已经支撑旗舰模型的关键训练或推理链路，它会怎样影响 NVIDIA 生态、国产 AI 芯片、云厂商、模型团队和工程师的技术选择？

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】01：大模型基础设施全景 —— 训练、推理、RAG、Agent、观测](https://quant67.com/post/llm-infra/01-intro/01-intro.html)

面向工程师的大模型基础设施开篇地图，覆盖 2022 到 2026 的工程分水岭、五层工程栈、训练与推理的工程差异、中国与全球行业版图以及成本曲线。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】05：训练全景：Pre-train、SFT、RLHF、DPO、蒸馏](https://quant67.com/post/llm-infra/05-training-overview/05-training-overview.html)

以工程视角串联现代 LLM 的四阶段训练栈——预训练、中训、SFT 与对齐——覆盖数据、Tokenizer、优化器、精度、Scaling Law 与代表性训练框架。