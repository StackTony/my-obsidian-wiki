> 单卡 80GB HBM 理论上只能放约 40B 个 FP16 参数；70B 模型光权重就约 140GB，还没算梯度、优化器和激活。 要训 DeepSeek-V3 这样的 671B MoE，必须把模型切成几千片，让几千张 GPU 像一台机器一样工作。 切分的艺术，就是并行的艺术。

## 一、为什么单卡再也装不下

### 1.0 开胃菜：一张时间线

|年份|事件|规模/突破|
|---|---|---|
|2017|Transformer 原论文|65M 参数|
|2018|BERT-Large|340M|
|2019|Megatron-LM 发布|8B，奠定 TP|
|2019|ZeRO-1/2/3|DeepSpeed，DP 极致省显存|
|2020|GPT-3 175B|PTD-P 3D 并行|
|2022|Megatron-Turing NLG 530B、BLOOM 176B|多集群合训|
|2023|GPT-4（推测 MoE）、Llama 2 70B|MoE 工程化|
|2024|DeepSeek-V3 671B MoE + DualPipe|零气泡 + FP8|
|2025|Llama 3 405B、Qwen 2.5、GLM-4.5|10T+ tokens 成常态|

每一次规模跨越都伴随并行策略的一次补刀。

### 1.1 显存的四项开销

训练一个 Transformer，GPU 显存的消耗大体分为四块：

  
|组成|大小（以参数 N 为单位）|说明|
|---|---|---|
|参数（Weights）|2N（FP16）|前向、反向都要用|
|梯度（Gradients）|2N（FP16）|反向累积|
|优化器状态（Optimizer）|12N（Adam FP32 m+v+master）|混合精度下的主拷贝|
|激活（Activations）|与 batch、seq、depth 成正比|反向 recompute 时需要|

以 Adam 混合精度训 70B 为例：参数 + 梯度 + 优化器 ≈ `2+2+12 = 16 × 70B = 1120 GB`，再加激活——单卡 80GB 连塞一角都不够。

### 1.2 算力的两堵墙

除了显存，还有两堵看不见的墙：

- **内存带宽墙**：H100 HBM3 约 3.35TB/s，H200 HBM3e 约 4.8TB/s。FP8/BF16 GEMM 的算力 / 带宽比越来越高，batch、sequence packing 和算子融合不够好时，Tensor Core 很容易等数据。
- **集合通信墙**：一次 AllReduce 70B 参数 FP16 = 140GB，哪怕是 NVLink 900GB/s，梯度同步也要几百毫秒。跨机 IB/RoCE 更慢。

所以并行化的目标不是”把模型切开能装下”就完事，而是在**切分带来的通信代价**和**计算能完成的比例（MFU）**之间找平衡。工业界 Pre-train 的 MFU 目标：密集模型 40%+，MoE 30%+，能稳到 50% 算极优。

## 二、并行的五个维度

### 2.0 先认清四种集合通信原语

后面所有讨论都离不开这四种 NCCL 原语，先一次性说清楚：

```
AllReduce(x_i)      → 每个 rank 拿到 Σ x_i         ；流量 ≈ 2(N-1)/N × |x|
ReduceScatter(x_i)  → 每个 rank 拿到 Σ x_i 的 1/P 片；流量 ≈ (N-1)/N × |x|
AllGather(s_i)      → 每个 rank 拿到全部 s_i 拼接   ；流量 ≈ (N-1)/N × |s|×P
All-to-All(x_i[j])  → rank i 的第 j 片发给 rank j  ；流量 ≈ (N-1)/N × |x|
```

**恒等式**：`AllReduce = ReduceScatter + AllGather`。完整做完两步时，总流量与 AllReduce 同阶；真正省流量的是那些**只需要分片结果**的场景，比如 ZeRO-2 的梯度 ReduceScatter，或者 SP 里把 AllReduce 拆开后顺手降低激活峰值。

### 2.1 DP：数据并行（Data Parallel）

最朴素：每张卡完整持有一份模型副本，把 global batch 切成 N 份，每卡前向 / 反向各一份，反向后对梯度做 **AllReduce**。

```
GPU0: model | batch[0:B/N]  --\
GPU1: model | batch[B/N:2B/N] --> AllReduce(grad) --> update
GPU2: model | batch[2B/N:..] --/
```

- 通信量：每步 `2N` 字节（FP16 参数规模的梯度）× AllReduce 因子 `2(N-1)/N ≈ 2`。
- 特点：**bandwidth-bound**，模型越大越痛。70B 模型一步 280GB AllReduce，跨节点极容易成为瓶颈。
- 变种：Gradient Bucketing（PyTorch DDP）、Hierarchical AllReduce、Gradient Compression（PowerSGD，精度有损，工业界很少用于 Pre-train）。

### 2.2 TP：张量并行（Tensor Parallel）

把单个大矩阵乘法切到多卡上，由 Megatron-LM 定型。切法两种：

- **列切（Column Parallel）**：`Y = XA`，把 `A` 按列切 `[A1, A2]`，每卡输出 `Yi = X Ai`。如果下一层能直接消费分片结果，就不必立刻 AllGather。
- **行切（Row Parallel）**：`Y = XA`，把 `A` 按行切，同时 X 也按列切，每卡算 `Yi = Xi Ai`，**最后 AllReduce** 求和。

Megatron 的 MLP（Linear → GELU → Linear）采用”列切 + 行切”配对：

```
X --[col-split Linear]--> Y(split) --GELU--> Z(split) --[row-split Linear]--> AllReduce --> Out
```

Attention 的 QKV Linear 是列切（切 head 维度），Output Linear 是行切。一层 Transformer 有 **2 次 AllReduce**（forward）+ **2 次 AllReduce**（backward，与 SP 结合可以换成 ReduceScatter/AllGather）。

- 通信量：每层 `4 × batch × seq × hidden` 字节（FP16）。
- 特点：**通信频繁、强依赖 NVLink**，一般只在 node 内（TP ≤ 8）。跨 NVSwitch 会掉 MFU。

### 2.3 PP：流水线并行（Pipeline Parallel）

按层切，不同 stage 放到不同 GPU 上。前向像流水一样：GPU0 算完第 1-8 层，把激活送到 GPU1 算 9-16 层……反向反着走。

经典问题是”气泡（bubble）“——头尾阶段的 GPU 必然有空闲。后文 §五 专门讲。

通信：stage 之间只发送 / 接收激活与激活梯度，是 **P2P send/recv**，数据量远小于 DP 的 AllReduce，跨节点友好。

### 2.4 SP：序列并行（Sequence / Context Parallel）

当 seq_len 达到 32K、128K 乃至 1M，**激活**（`B × S × H`）本身就爆显存，单 TP 切不动了。SP 沿 **序列维度** 切分：

- **Megatron-SP**：在 TP 的基础上，把 LayerNorm、Dropout 等”行无关”算子的激活按 seq 切，TP 通信由 AllReduce 换成 `ReduceScatter + AllGather` 等价变换，峰值激活降 TP 倍。
- **Ring Attention**（Liu et al. 2023）：把 KV 在环形拓扑上传递，每卡算局部 attention，然后传 KV 到下一个节点，几乎线性扩展到任意长序列。
- **Ulysses**（DeepSpeed）：在 attention 内部做 all-to-all，把 `(B, S/P, H)` 换成 `(B, S, H/P)`，走完 attention 再换回来。head 数要能被并行度整除。
- **Context Parallel（CP）**：Megatron-Core 的术语，通常指 Ring Attention 风格。

实操上：**Ulysses 在 TP 已经切了 head 的情况下不好叠加**，Ring/CP 与 TP 的正交性更好；长上下文训练通常会把 CP 与 TP / PP / DP 组合起来，MoE 场景再叠 EP。

### 2.5 EP：专家并行（Expert Parallel，MoE 专用）

MoE 每层有几十到几百个 expert，但 token 只路由到 top-k 个。EP 做的就是把 expert 分散到 N 张卡：

```
token routing -> all-to-all dispatch -> local experts -> all-to-all combine
```

- 通信：两次 **all-to-all**，网络消耗 = 激活 × 2 × top-k × (1-1/EP)。
- 痛点：路由抖动（expert 负载不均）、all-to-all 拖尾、drop-token vs capacity factor。
- DeepSeek-V3 技术报告披露的核心组合是 EP=64、PP=16、无 TP，并通过 node-limited routing 限制跨节点 all-to-all 的范围。

五个维度的关系可以用一张图表达：

![EP：专家并行（Expert Parallel，MoE 专用）](https://quant67.com/post/llm-infra/06-parallelism/images/06-parallelism-fig1.svg)

## 三、ZeRO 与 FSDP：DP 的进化形态

DP 的痛点是”每张卡都完整保存参数 / 梯度 / 优化器”，冗余极大。**ZeRO**（Zero Redundancy Optimizer，DeepSpeed 2019）把这三份状态切分到 DP 各卡上。

### 3.1 ZeRO 三阶段

   
|阶段|切分内容|单卡状态显存|额外通信|
|---|---|---|---|
|ZeRO-1|优化器状态|2N + 2N + 12N/Ndp|无（只在优化器 step 时处理）|
|ZeRO-2|+梯度|2N + 2N/Ndp + 12N/Ndp|ReduceScatter 替 AllReduce|
|ZeRO-3|+参数|(2N + 2N + 12N)/Ndp|前向 / 反向前 AllGather 参数|

ZeRO-3 的通信量通常高于标准 DDP，因为前向和反向都要按需 AllGather 参数，反向还要 ReduceScatter 梯度；换来的收益是参数、梯度、优化器状态都按 `1/Ndp` 切分。

### 3.2 FSDP（Fully Sharded Data Parallel）

PyTorch 原生实现的 ZeRO-3：

```
import torch
from torch.distributed.fsdp import FullyShardedDataParallel as FSDP
from torch.distributed.fsdp import ShardingStrategy

model = FSDP(
    model,
    sharding_strategy=ShardingStrategy.FULL_SHARD,  # ZeRO-3
    mixed_precision=mp_policy,
    device_id=torch.cuda.current_device(),
)
```

关键细节：

- **Unit 切分**：以 Transformer Block 为粒度 wrap，前向进入 block 时 AllGather、退出时 free。
- **Prefetch**：下一个 block 的 AllGather 与当前 block 计算 overlap。
- **FSDP2（PyTorch 2.4+）**：基于 `DTensor`，取消 `FlatParameter`，与 TP / PP / TorchTitan 组合更干净。
- **HSDP（Hybrid Shard）**：节点内 FullShard + 节点间 Replicate，减少跨节点 AllGather。

### 3.3 ZeRO-Offload / CPU / NVMe

- **ZeRO-Offload**：优化器状态放 CPU，step 在 CPU 上算（Adam）。
- **ZeRO-Infinity**：参数也能下放到 NVMe，做到单机训百亿以上。适合”穷人 / 实验室”场景，吞吐会显著下降。

工业预训练一般不用 Offload，SFT / LoRA 经常用。

### 3.4 ZeRO-R：激活与临时 buffer

ZeRO 家族里还有常被忽视的一档：

- **P_a（partitioned activations）**：把激活按 TP 切到各卡，与 `--sequence-parallel` 等价。
- **C_B（constant buffer size）**：把 AllReduce buffer 固定，避免大张量 OOM。
- **M_D（memory defragmentation）**：周期整理显存碎片。

这些在纯 DeepSpeed 栈里是 ZeRO-R；Megatron / FSDP 都内化实现了类似机制。

### 3.5 FSDP vs DeepSpeed 实战差异

|维度|FSDP2|DeepSpeed ZeRO-3|
|---|---|---|
|代码集成|纯 PyTorch，改动小|需要 deepspeed engine 包一层|
|与 `torch.compile`|逐步完善|兼容有限|
|CPU/NVMe Offload|有限|成熟（Infinity）|
|MoE 支持|需配合 Expert Parallel 手写|集成 MoE + EP|
|Checkpoint|DCP（Distributed Checkpoint）|内置切片 + 合并工具|
|生态|TorchTitan / HF Accelerate|HF Trainer / colossal / DS-Chat|

选型不是二选一：常见组合是 **Megatron 主干负责 TP/PP/SP**，DeepSpeed 或 Megatron distributed optimizer 负责优化器状态切分，FSDP2 / TorchTitan 用在可读性和迭代速度更重要的 SFT、RL 或研究原型里。

单用任何一种都不够，工业训练都是 **TP × PP × DP (× SP × EP)** 的笛卡儿积。

### 4.1 经典配置

      
|场景|规模|TP|PP|DP|SP/CP|EP|
|---|---|---|---|---|---|---|
|Megatron 175B（8×A100 node×多节点）|175B dense|8|8|128|1|-|
|Llama 3 70B（官方）|70B dense|8|4|-|1|-|
|DeepSeek-V3 Pre-train|671B MoE|1（无 TP）|16|2|-|64|
|长上下文 SFT（128K）|13B|2|2|32|8 (CP)|-|

> DeepSeek-V3 的一个设计亮点：放弃 TP，用 **EP + PP + DP/ZeRO-1** 组合，因为 MoE 的 FFN 已被 expert 天然切分，不再需要 TP 切 MLP；这样避免了 TP 带来的每层 AllReduce，换来更大的 PP 调度空间。

### 4.2 Group 布局与通信域

以 `TP=8, PP=4, DP=16` 共 512 卡为例，NCCL 里会创建三类 ProcessGroup：

```
rank = tp_rank + tp_size * (dp_rank + dp_size * pp_rank)

TP group：同一 (pp_rank, dp_rank) 的 8 张卡 → 放 node 内 NVLink
PP group：同一 (tp_rank, dp_rank) 的 4 张卡 → 跨节点，但通信量小
DP group：同一 (tp_rank, pp_rank) 的 16 张卡 → 跨节点 AllReduce
```

**Rail-optimized 拓扑**：`ibN` 网卡与 `GPUn` 一一配对，DP AllReduce 走自己的 rail，避免 cross-rail。这是 NCCL 2.18+ `NCCL_CROSS_NIC=0` 的默认行为。

### 4.3 通信量粗算（每 step）

记：`a = batch × seq × hidden`，`L` 层，`N` 参数。

|维度|数据量|说明|
|---|---|---|
|DP AllReduce|2N（FP16）|一次|
|TP AllReduce|4L × a|每层 4 次（fwd 2 + bwd 2）|
|PP P2P|2L/PP × a|stage 边界激活 + 梯度|
|SP（与 TP 合并）|4L × a（总量不变，换成 RS/AG）|峰值激活 ↓ TP 倍|
|EP all-to-all|2 × topk × a × (1−1/EP)|MoE 层才算|

**经验规则**：若 DP AllReduce 超过 20% 单步时间，考虑升 ZeRO 或砍 DP；若 TP AllReduce 跑出节点，直接掉 MFU 30%+。

### 4.4 Rank 布局的可视化

以 `TP=4, PP=2, DP=2`，共 16 GPU 为例：

```
                 PP stage 0              PP stage 1
            ┌──────────────┐       ┌──────────────┐
DP group 0  │ R0 R1 R2 R3  │──PP──▶│ R8 R9 R10 R11│
            │ ◀── TP ────▶ │       │ ◀── TP ────▶ │
            └──────┬───────┘       └──────┬───────┘
                   │ DP AllReduce         │ DP AllReduce
            ┌──────┴───────┐       ┌──────┴───────┐
DP group 1  │ R4 R5 R6 R7  │──PP──▶│R12 R13 R14 R15│
            └──────────────┘       └──────────────┘
```

- TP 组：`{0,1,2,3}`、`{4,5,6,7}`、`{8,9,10,11}`、`{12,13,14,15}`。
- PP 组：`{0,8}`、`{1,9}`、…、`{7,15}`。
- DP 组：`{0,4}`、`{1,5}`、…、`{11,15}`。

Megatron 按 `tp × dp × pp` 的顺序把 rank 扁平化，这也是”TP 放同 node”自然成立的原因——同一个 node 上的 8 个 rank 天然落入同一 TP 组。

## 五、流水线气泡：从 GPipe 到 DualPipe

### 5.1 气泡公式

设 PP 度 `P`，micro-batch 数 `M`：

- **GPipe**（先全前向再全反向）：空转相对有效计算的比例约为 `(P-1) / M`。若 `P=8, M=16`，额外空转约 43.8%；按总 wall-clock 计，气泡占比约 `7 / (16+7) = 30.4%`。
- **1F1B**（PipeDream-Flush / Megatron）：空转阶数仍是 `(P-1) / M`，但**峰值激活从 GPipe 的 M 份降到约 P 份**。
- **Interleaved 1F1B**（Virtual Pipeline）：每卡持有 `v` 个非相邻层段，空转近似变为 `(P-1) / (v × M)`，代价是 P2P 次数 ×v。
- **Zero Bubble**（Sun et al. 2024）：把反向拆成 **B**（input grad）和 **W**（weight grad），重排 `F / B / W` 让气泡降到理论 0。
- **DualPipe**（DeepSeek-V3）：**双向流水**，两个方向上交错做前 / 反向，并把计算与通信重叠。公开 profile 的目标是接近零气泡，同时把 MoE all-to-all 尽量藏到计算后面。

### 5.2 时序对比（Mermaid）

0 0 0 0 0 0 0 0 0 0 1GPU0 F1 GPU0 F1 GPU0 F1+ GPU0 F2 GPU0 F3 GPU0 F4 GPU0 B1 GPU0 B2 GPU0 B3 GPU0 B4 GPU0 F2 GPU0 B1 GPU0 W1 GPU0 F3 GPU0 B2 GPU0 F2+B1- GPU0 F3+B2- GPU0 F4+B3- GPU0 B4- 1F1BZeroBubbleDualPipe1F1B vs Zero Bubble vs DualPipe（P=4，单位 = micro-batch 步）

### 5.3 Zero Bubble 关键：`B / W` 拆分

反向传播中：

- `B`（`grad_input = grad_output @ W.T`）：下游需要 → 必须尽早算。
- `W`（`grad_weight = X.T @ grad_output`）：只自己用 → 可以延后到流水尾巴。

把 `W` 往后推，中间空档让其他 micro-batch 的 F/B 填进来。

### 5.4 DualPipe 的双向 + 重叠

DualPipe 核心思想：

1. **双向调度**：把模型分成两份对称流水，一份从头到尾、一份从尾到头，两股数据流反向流动，共享 GPU 计算单元。
2. **细粒度 chunk**：将 attention / MLP / all-to-all dispatch / all-to-all combine 切为 4 块，按 `ATTN → MLP → combine → dispatch` 重排，让**反向计算遮蔽前向 all-to-all**。
3. **不需要 TP**，天然适配 EP-heavy MoE。

代价：显存需要保存 2 份参数副本（因为两个方向同时在算），适合 MoE 这种参数相对 sparse 的结构；Dense 大模型用 DualPipe 不划算。

## 六、通信与计算 overlap

MFU 上 50% 的关键：让每一次集合通信都藏到 GEMM 后面。

### 6.1 NCCL stream 与 CUDA graph

```
# PyTorch 内部约定：通信走单独的 NCCL stream
comm_stream = torch.cuda.Stream()
with torch.cuda.stream(comm_stream):
    dist.all_reduce(grad, async_op=True)
# 计算继续在默认 stream
```

DDP 的 `bucket` 机制：梯度按桶（默认 25MB）触发 AllReduce，反向还没结束、前面桶的 AllReduce 已经在跑。

### 6.2 Chunk / micro-batch

- **TP AllGather-MatMul Fusion**（Megatron `--sequence-parallel` + FlashAttention 2.x + cuBLASLt）：把 AllGather 拆 chunk 与 MatMul pipeline 重叠，近年的”tensor parallelism with sequence parallel communication overlap”即此。
- **NCCL SendRecv + Compute**：PP 的 stage 通信可以先 issue send，再做下一 micro-batch 前向。

### 6.3 DualPipe 的 all-to-all 重叠

MoE 的 all-to-all 最痛苦。DualPipe 把 `dispatch / combine` 拆成 4 个 warp group，与本 chunk 的反向 compute 用不同 SM：

```
Compute SMs:  | attn_bwd | mlp_bwd |
Comm SMs:     |          dispatch(next) / combine(prev) |
```

这是 DeepSeek-V3 技术报告里最有工程含金量的一块：在 H800 这类互联受限的环境下，调度器把 MoE all-to-all 从主路径里尽量挪出去，才有机会把 MFU 推到 40% 左右。

## 七、激活重计算与梯度累积

### 7.1 Activation Checkpointing

反向用到的中间激活占用极大（`B × S × H × L × 12` 级别）。**checkpoint**：前向时只存 block 入口激活，反向时重新跑一次前向。换显存与 1/3 额外算力。

- **Full Recompute**：每个 Transformer Block 都重算，显存 ↓ ~5×，算力 ↑ ~33%。
- **Selective Recompute**（Megatron-LM / Megatron-Core）：只 recompute 占内存大但算力相对便宜的部分（LayerNorm、Dropout、激活函数）。FlashAttention 的 softmax 中间态本身就不落全量 HBM，和 selective recompute 叠加效果更好。
- **Offload Activations**：把激活换到 CPU，适合长序列。

### 7.2 梯度累积

```
for step, batch in enumerate(loader):
    loss = model(batch) / accum_steps
    loss.backward()                       # 累在 .grad 上
    if (step + 1) % accum_steps == 0:
        optimizer.step()
        optimizer.zero_grad()
```

梯度累积把有效 batch size 放大而不增显存，但**会降低 PP / DP AllReduce 的 overlap 机会**（因为最后一次累积后必须同步）。Megatron 的做法是把 `global_batch = DP × micro_batch × accum`，accum 等于 PP micro-batch 数。

### 7.3 激活显存粗算

一个 Transformer Block，FlashAttention 2/3 下保存的激活量大约是：

```
act ≈ B × S × H × (34 / TP)  bytes（BF16，含 norm / residual / proj 输出）
```

L 层全保留：`L × B × S × H × 34 / TP`。以 `L=96, B=2, S=4096, H=12288, TP=8` 估算： `96 × 2 × 4096 × 12288 × 34 / 8 ≈ 41 GB / micro-batch`，1F1B 再 × P = 几百 GB，不开 recompute 铁定 OOM。

开 **selective recompute** 后约 `10 / TP`，激活减到 12GB/micro-batch，完全可控。

### 7.4 与 CPU/GPU 传输的激活 offload

对超长序列（256K+），就算 recompute 仍然很痛。可以把 block 前向输出 offload 到 CPU，反向时异步拷回：

```
act = act.to("cpu", non_blocking=True)        # 前向尾部
...                                           # 其他 block 继续算
act = act.to("cuda", non_blocking=True)       # 反向前预取
```

PyTorch/FSDP 生态里的 checkpoint wrapper、activation offload 封装，以及 Megatron 的 `--cpu-offloading` 都能做类似处理。代价是 PCIe 带宽（Gen5 x16 理论约 64GB/s，实际更低）会成为新瓶颈，常见结果是吞吐明显下降。

## 八、负载均衡的工程痛点

### 8.1 MoE 路由抖动

MoE 训练最头疼：某些 expert 成”网红”，其他 expert 饥饿。解决：

- **Load-balancing loss**（Switch Transformer）：softly 惩罚负载不均。
- **Capacity factor**：每个 expert 最多收 `cf × avg_tokens`，超出 drop。
- **Auxiliary-free balancing**（DeepSeek-V3）：取消 aux loss，用 bias 调节路由，既不污染主 loss 又保证负载。
- **Node-limited routing**：top-k 里限定跨的 node 数 ≤ M，把跨节点 all-to-all 压到可控。

### 8.2 PP 切分不均

每层 TFLOPS 不同：embedding、LayerNorm、FinalHead 比中间层轻。静态均分会让 stage0、stage_last 变慢成木桶短板。

- **DP 切分法**：测每层耗时 → 动态规划最小化 `max(sum_stage)`。Megatron 的 `--pipeline-model-parallel-split-rank` 支持自定义。
- **Embedding 复制**：头尾两个 stage 都放 embedding + head，拉近 workload。

### 8.3 动态 batch / seq

长短样本混批时，seq=4K 和 seq=128K 同 batch 等于短样本陪跑。做法：

- **Sequence packing**：把短样本塞进长 context，用 attention mask 隔离。
- **Dynamic micro-batch**：按 `tokens` 而非 `samples` 定义 batch。
- **Sorted batching**：同长度样本聚在一起（SFT 常用）。

### 8.4 PP 切分的动态规划伪码

给每一层一个 profile 耗时 `t[i]`，要切成 `P` 段使 `max(Σt)` 最小：

```
def split_pp(t, P):
    L = len(t)
    # dp[i][p]: 前 i 层切 p 段的最小瓶颈耗时
    INF = float("inf")
    dp = [[INF] * (P + 1) for _ in range(L + 1)]
    cut = [[0] * (P + 1) for _ in range(L + 1)]
    dp[0][0] = 0
    prefix = [0]
    for x in t:
        prefix.append(prefix[-1] + x)
    for i in range(1, L + 1):
        for p in range(1, P + 1):
            for j in range(p - 1, i):
                seg = prefix[i] - prefix[j]
                val = max(dp[j][p - 1], seg)
                if val < dp[i][p]:
                    dp[i][p] = val
                    cut[i][p] = j
    # 回溯 cut 得到每 stage 的层区间
    return dp[L][P], cut
```

生产上通常会先 profile 每层耗时，再用类似思路做 stage 均衡；Megatron-Core、Colossal-AI 这类框架也都提供了自定义或自动化的流水切分入口。

## 九、通信优化细节

### 9.1 FP8 AllReduce / FP8 训练

NVIDIA Transformer Engine（TE）把 GEMM 输入做动态 scaling 转到 **FP8（E4M3 / E5M2）**，AllReduce 本身一般仍走 BF16 / FP16（Hopper 的 NCCL 现已支持 FP8 collective，但数值稳定性需谨慎）。

DeepSeek-V3 自研了一套 **E4M3-only 的 FP8 混合精度**，对 GEMM 使用 FP8，对累加 / 权重更新保持 FP32，在 H800 上把算力吃干。

### 9.2 NCCL 拓扑感知

- **Ring**：所有 rank 串成环，带宽 = 最慢链路。简单但大规模下 latency 高。
- **Tree**：reduction 走树，延迟 `O(log N)`，大规模 DP AllReduce 默认。
- **CollNet / SHARP**（InfiniBand in-network reduction）：交换机里做加法，再降一半流量。
- **Rail**：每卡配专属网卡，避免 PCIe / NVSwitch 跨行。

Megatron 启动脚本常见：

```
export NCCL_IB_HCA=mlx5
export NCCL_IB_GID_INDEX=3
export NCCL_SOCKET_IFNAME=eth0
export NCCL_ALGO=Tree
export NCCL_CROSS_NIC=0
export NCCL_IB_SL=1
```

### 9.3 ZeRO Offload / CPU / NVMe

真显存不够时的兜底。一般组合：

- **训练**：工业预训练优先用 ZeRO / distributed optimizer + Activation Checkpointing + FP8，把 Offload 当兜底而不是主路径。
- **SFT / LoRA**：70B 级模型通常要配合 QLoRA/4-bit、ZeRO-3 或 CPU/NVMe Offload；单靠 ZeRO-2 + CPU Adam 仍然会被参数副本卡住。
- **推理**：不用 ZeRO，用 TP + PP + KV cache 分页（见 §12）。

## 十、实战栈

### 10.1 Megatron-LM（NVIDIA）

- 标配 TP + SP + PP + DP，社区最成熟。
- `transformer_engine` 集成 FP8。
- 新版 Megatron-Core 把并行化拆成可组合的 `ParallelConfig`，支持 Mamba 等 hybrid arch。
- 中国：百川、智谱、MiniMax、Qwen 的 pretrain 主干多为 Megatron fork。

### 10.2 DeepSpeed（微软）

- ZeRO 发源地，3 阶段 + Infinity + Offload。
- 流水线偏教学向，工业 pretrain 少用。
- 生态：HF Accelerate / Trainer 深度集成；国内火山引擎、阿里 PAI 都有 DS 预置镜像。

### 10.3 FSDP2 / HSDP（PyTorch 官方）

- 纯 Python，代码可读。
- PyTorch 2.4 起推荐 **FSDP2 + DTensor + TorchTitan**，官方给的 Llama 训练 demo。
- 与 `torch.compile` 搭配越来越丝滑。

### 10.4 Colossal-AI / TorchTitan / veScale / MindSpeed

- **Colossal-AI**（潞晨）：国内团队，支持 2D/2.5D/3D TP 等花式切法，中小规模适合。
- **TorchTitan**（Meta）：官方极简 pretrain 模板，TP + FSDP2 + PP 正在补齐。
- **veScale**（字节）：nD 并行 + DTensor，豆包训练栈。
- **MindSpeed**（华为）：昇腾生态的 Megatron 移植。
- **Megatron-DeepSpeed**（微软 + NV 联合分支）：BLOOM 训练所用。

### 10.5 DualPipe（DeepSeek 2024 开源）

DeepSeek 在 v3 后开源了 `DualPipe` 调度器（github.com/deepseek-ai/DualPipe），以及 `EPLB`（Expert Parallelism Load Balancer）和 `profile-data`。对做 MoE 预训练的团队是一手材料。

## 十一、代码示例：PyTorch FSDP2 + TP 最小样例

下面给出一个可运行骨架（需要 PyTorch 2.4+，实际训练请结合 TorchTitan）。

```
import os
import torch
import torch.nn as nn
import torch.distributed as dist
from torch.distributed.device_mesh import init_device_mesh
from torch.distributed.tensor.parallel import (
    ColwiseParallel,
    RowwiseParallel,
    parallelize_module,
)
from torch.distributed._composable.fsdp import fully_shard


class MLP(nn.Module):
    def __init__(self, d):
        super().__init__()
        self.w1 = nn.Linear(d, 4 * d, bias=False)
        self.w2 = nn.Linear(4 * d, d, bias=False)

    def forward(self, x):
        return self.w2(torch.nn.functional.gelu(self.w1(x)))


class Block(nn.Module):
    def __init__(self, d):
        super().__init__()
        self.attn = nn.MultiheadAttention(d, 8, batch_first=True)
        self.mlp = MLP(d)
        self.n1 = nn.LayerNorm(d)
        self.n2 = nn.LayerNorm(d)

    def forward(self, x):
        x = x + self.attn(self.n1(x), self.n1(x), self.n1(x), need_weights=False)[0]
        x = x + self.mlp(self.n2(x))
        return x


def build_model(num_layers=12, d=1024):
    return nn.Sequential(*[Block(d) for _ in range(num_layers)])


def main():
    dist.init_process_group("nccl")
    world = dist.get_world_size()
    rank = dist.get_rank()
    torch.cuda.set_device(rank % torch.cuda.device_count())

    # 2D mesh：行是 DP（FSDP），列是 TP
    tp_size = 2
    dp_size = world // tp_size
    mesh = init_device_mesh(
        "cuda",
        mesh_shape=(dp_size, tp_size),
        mesh_dim_names=("dp", "tp"),
    )

    model = build_model().cuda()

    # === TP：把每个 Block 的 MLP 列切 + 行切 ===
    tp_mesh = mesh["tp"]
    for block in model:
        parallelize_module(
            block.mlp,
            tp_mesh,
            {
                "w1": ColwiseParallel(),
                "w2": RowwiseParallel(),
            },
        )

    # === FSDP2：按 Block 粒度做 ZeRO-3 切分 ===
    dp_mesh = mesh["dp"]
    for block in model:
        fully_shard(block, mesh=dp_mesh)
    fully_shard(model, mesh=dp_mesh)

    model = torch.compile(model)

    opt = torch.optim.AdamW(model.parameters(), lr=1e-4)
    x = torch.randn(4, 256, 1024, device="cuda")

    for step in range(10):
        loss = model(x).square().mean()
        loss.backward()
        opt.step()
        opt.zero_grad()
        if rank == 0:
            print(f"step {step} loss {loss.item():.4f}")


if __name__ == "__main__":
    main()
```

启动：

```
torchrun --nproc_per_node=8 fsdp_tp_demo.py
```

### 11.1 扩展到 PP

PyTorch 2.4+ 提供 `torch.distributed.pipelining`（PP），基本接口：

```
from torch.distributed.pipelining import pipeline, SplitPoint, ScheduleGPipe, Schedule1F1B

stage_mod = pipeline(model, mb_args=(x,),
                     split_spec={"layer4": SplitPoint.BEGINNING})
schedule = Schedule1F1B(stage_mod, n_microbatches=8, loss_fn=loss_fn)
schedule.step(x, target=y)
```

TorchTitan 里有 TP + PP + FSDP2 的完整 llama3 demo，可以直接参考。

### 11.2 Megatron-LM 启动片段

作为对比，Megatron 的启动参数：

```
torchrun --nproc_per_node=8 --nnodes=128 \
  pretrain_gpt.py \
  --tensor-model-parallel-size 8 \
  --pipeline-model-parallel-size 16 \
  --num-layers 96 --hidden-size 12288 --num-attention-heads 96 \
  --seq-length 2048 --max-position-embeddings 2048 \
  --micro-batch-size 2 --global-batch-size 1024 \
  --sequence-parallel \
  --use-distributed-optimizer \
  --num-layers-per-virtual-pipeline-stage 4 \
  --recompute-activations --recompute-granularity selective \
  --bf16 --use-flash-attn \
  --transformer-impl transformer_engine \
  --fp8-format hybrid --fp8-amax-history-len 1024 --fp8-amax-compute-algo max
```

逐项意义：

- `--sequence-parallel`：把 TP 不切分的张量（LayerNorm 输入等）按 seq 维切，激活 /= TP。
- `--use-distributed-optimizer`：等价于 ZeRO-1，优化器状态按 DP 切。
- `--num-layers-per-virtual-pipeline-stage 4`：Interleaved 1F1B 的 v，进一步压气泡。
- `--recompute-granularity selective`：只 recompute 内存性价比高的 op。
- `--fp8-format hybrid`：E4M3 前向 + E5M2 反向（Transformer Engine 默认策略）。

### 11.3 DeepSpeed 配置片段

```
{
  "train_micro_batch_size_per_gpu": 2,
  "gradient_accumulation_steps": 16,
  "zero_optimization": {
    "stage": 3,
    "overlap_comm": true,
    "contiguous_gradients": true,
    "reduce_bucket_size": 5e8,
    "stage3_prefetch_bucket_size": 5e8,
    "stage3_param_persistence_threshold": 1e6,
    "offload_optimizer": {"device": "cpu", "pin_memory": true}
  },
  "bf16": {"enabled": true},
  "activation_checkpointing": {
    "partition_activations": true,
    "contiguous_memory_optimization": true
  }
}
```

## 十二、工程经验：选型与调参

### 12.1 决策树：到底用哪种并行？

```
模型能塞进单卡（含优化器）？
├─ 是 → DDP / FSDP1 即可
└─ 否 → 看参数规模
         ├─ < 20B：FSDP2（或 ZeRO-3） + Activation Ckpt，单节点搞定
         ├─ 20B–200B dense：TP(node 内 ≤ 8) + PP(跨节点) + DP + SP
         ├─ > 200B dense：TP + PP + DP + SP + Interleaved 或 Zero Bubble
         └─ MoE：EP(node 内或 node-limited) + PP + DP (+ 小 TP 或 无 TP) + DualPipe
```

并结合序列长度：

```
seq ≤ 8K    : 不需要 SP
seq 8K–32K  : Megatron-SP
seq ≥ 64K   : Context Parallel / Ring Attention
seq ≥ 256K  : CP + Activation Offload + FlashAttention
```

### 12.2 Batch size 怎么定

- **Global tokens / step** = `DP × micro_batch × grad_accum × seq_len`。Pre-train 常见 `2M–4M tokens / step`。
- **Micro batch** 受单卡显存限制，通常按”能塞满但不 OOM”取；70B/175B 这类规模常从 1、2、4 试起，而不是盲目拉大。
- **Critical batch size**（McCandlish et al.）：超过某 GBS，继续扩大收敛收益递减，需要调 LR 或换 optimizer（LAMB、AdamW 的 warmup+cosine）。

### 12.3 MFU 目标

|场景|MFU 参考线|
|---|---|
|A100/H100 dense pretrain|45–55%|
|H800 dense（砍 NVLink）|35–45%|
|H800 MoE DualPipe|35–42%|
|长上下文（CP > 1）|30–40%|
|国产 910B / MX|25–40%（和算子库成熟度强相关）|

> MFU 30% 以下，先查：TP 是否跨节点；PP 气泡是否过大；ZeRO-3 是否 AllGather 打爆 IB；FlashAttention 版本；FP8 是否真开。

### 12.4 常见翻车

1. **TP 跨节点**：立刻 MFU 腰斩。规矩是 TP ≤ 节点 GPU 数。
2. **PP micro-batch 太小**：气泡吃掉一切。`M ≥ 4P` 是最低线。
3. **Activation Ckpt 开太猛**：浪费 30% 算力。用 selective + FlashAttention 后，full recompute 通常可以关掉。
4. **DP 维度巨大**：几千路 DP 做 AllReduce 跨机网络会饱和，用 HSDP 分层 reduce。
5. **MoE expert 不够大 / EP 太粗**：`experts_per_rank = 1` 时 all-to-all 代价 > 计算；建议 2–4。
6. **CP + Ulysses 混用**：路由和 head 维度冲突，debug 极难，选一个就行。
7. **混合精度 NaN**：FP8 scaling 窗口、amax history、loss scaler 或梯度裁剪没跟上。先回 BF16 复现，再逐项打开 FP8，比盲调更快。

## 十三、深入：一个 175B 训练的完整账本

把上面所有维度放到一次真实训练上算一笔账。假设：

- 模型：175B dense（类似 GPT-3），`L=96`，`H=12288`，`heads=96`，`seq=2048`。
- 硬件：1024 × H100 80GB，8 卡 / node，共 128 node。节点内 NVLink 900GB/s，跨节点 8×400G IB（单机 3.2Tbps）。
- 目标：`global_batch = 4M tokens`，MFU ≥ 45%。

### 13.1 切分配置

选 `TP=8, PP=16, DP=8`。

- `TP=8` 贴节点 GPU 数，MLP/Attn 的 AllReduce 全在 NVLink。
- `PP=16` 跨 16 个节点（每节点只属于一个 PP stage 的一片），stage 间 P2P 走 IB。
- `DP=8` 跨剩下 8 组节点做 AllReduce，用 HSDP 即可。

单卡参数：`175B / (TP × PP) = 175B / 128 ≈ 1.37B`，BF16/FP16 权重约 2.74GB。若优化器状态不切分，Adam 相关状态约 16.4GB；若使用 Megatron distributed optimizer / ZeRO-1，再按 DP 维切一遍，优化器状态约降到 2GB 量级。实际还要给梯度、通信 bucket、CUDA graph workspace 和碎片留空间。

激活是更容易被低估的一项。粗略看，每个 stage 有 `L/PP = 6` 层，单 micro-batch 的激活量与 `B × S × H × 层数 × 保存系数` 成正比；是否开启 SP、FlashAttention、selective recompute，会让常数差出数倍。1F1B 下同时在飞的 micro-batch 约为 `P` 级别，所以 175B 训练通常必须打开 **selective recompute**，并让 SP/TP 一起分摊激活。

### 13.2 通信预算

单步数据流：

- TP 通信：每层量级约 `4 × B × S × H × 2 ≈ 400MB`（含 forward/backward 里的多次 collective，按 BF16/FP16 估算），发生在节点内 NVLink，必须和 GEMM overlap。
- PP P2P：每个边界每个 micro-batch 发送激活 / 激活梯度，量级是 `B × S × H × dtype`，是否按 TP/SP 分片取决于框架实现；它比 DP/TP 低频，适合跨节点。
- DP / distributed optimizer：每 step 对本地参数 shard 做 ReduceScatter / AllGather 或 AllReduce，量级是数 GB，必须被反向 bucket overlap，否则尾部会直接拖慢 step。

### 13.3 时序估算

单 micro-batch 的训练 FLOPs 量级约为 `6 × N × B × S`。代入 `N=175B, B=2, S=2048`，全模型约 `4.3e15` FLOPs；摊到 `TP × PP = 128` 张模型并行卡上，每卡约 `3.4e13` FLOPs。若按 H100 FP8 峰值 `989 TFLOPS`、有效利用率 50% 粗估，单 stage 一个 micro-batch 的计算下界是几十毫秒级。真实耗时会被 kernel 形状、通信 overlap、重计算、PP 调度拉高。

为了达到 `4M tokens / step`，在 `DP=8, B=2, S=2048` 下需要 `M ≈ 4M / (8×2×2048) ≈ 122`，生产上通常取 128 这类方便调度的数。此时普通 1F1B 的额外空转约 `(P-1)/M = 15/128 ≈ 12%`；如果 M 只有 32，则会变成 47%，明显偏高。方案：

- **加 M**：M=128 → 气泡 15/128 ≈ 12%。
- **改 Interleaved 1F1B**，v=4 → 在 M=32 时也能把近似气泡压到 15/(4×32) ≈ 12%。
- **改 Zero Bubble**，气泡趋近 0，但要拆 B/W。

生产上 Megatron 常用 Interleaved 1F1B，DeepSeek-V3 这类 MoE 训练则用 DualPipe 把流水气泡和 all-to-all 一起处理。

### 13.4 成本曲线

1024 × H100 跑一年的总成本很容易到千万美元级。MFU 每提高 1 个百分点（例如 45% → 46%），对应的训练时间和预算节省就是数十万美元级别。这就是为什么大厂愿意自研调度器、死磕 FP8 和零气泡——算力涨 1% 都是真金白银。

## 十四、国产与异构

### 14.1 华为昇腾（910B/910C）

- **MindSpeed** = Megatron 的昇腾移植；CANN 提供 HCCL（对标 NCCL）。
- 公开生态主线仍以 BF16 / FP16 为主，FP8 能力要看具体芯片、CANN 版本和算子覆盖。
- TP 通信走 HCCS（对标 NVLink，但带宽与拓扑不同），TP ≤ 8 同样适用。
- MoE + 3D 并行在昇腾上实现成熟度略落后于 N 卡，但盘古、Qwen 昇腾版已跑通。

### 14.2 寒武纪、天数、沐曦、摩尔线程

- 大多通过 PyTorch plugin + 自己的集合通信库做对接。
- 实际训练规模以中小（百亿级）为主；大规模训练的生态尚在补齐。

### 14.3 AMD MI300X / MI325X

- ROCm + RCCL（NCCL API 兼容）。
- PyTorch FSDP2 / Megatron 的 ROCm fork 可跑，Meta、微软公开过 MI300X 训练报告。
- FP8（OCP 规范）已支持；生态距 CUDA 还有 1–2 年。

### 14.4 TPU v5p / Trillium

- 完全不同体系：**XLA + JAX + `pjit`**。
- 并行通过 `Mesh + PartitionSpec` 声明，编译期决定通信。
- Google PaLM、Gemini 走这条路，外部团队使用较少，但 JAX + `jax.experimental.shard_map` 的模型定义极简洁。

## 十五、调试与性能分析

### 15.1 工具

- **PyTorch Profiler** + **HTA（Holistic Trace Analysis）**：画出每张卡的 kernel / comm timeline。
- **Nsight Systems / nsys**：GPU 侧最细粒度。
- **NCCL_DEBUG=INFO**：通信拓扑、算法选择一目了然。
- **Megatron-Core `--profile` flag**：自动标注每段耗时。
- **torch.cuda.memory._snapshot()**：查显存泄漏 / 碎片。

### 15.2 一个典型 MFU 排查流程

1. 看 `tokens/sec/GPU`，算 MFU。低于目标 5% 以上就要查。
2. nsys 看一个 step：
    - GEMM 占比 < 50%？→ 算子 / 精度问题（没开 FP8、没用 FlashAttention）。
    - 通信 kernel 与 GEMM 同时在跑？→ overlap OK。否则看是不是 `async_op=False`、或 bucket 太小。
    - PP 气泡是否如预期？→ M 调大或换调度。
3. 单独跑单卡 benchmark，对比理论峰值（`989 TFLOPS × 0.7` 为单 GEMM 经验线）。
4. 把 TP 调成 1（只 DP + PP）看 MFU，隔离 TP 跨节点问题。

### 15.3 数值稳定性坑

- **FP8 溢出**：检查 `amax_history`，必要时换 E5M2 / 回 BF16。
- **MoE loss spike**：aux-loss 权重太大、capacity 太紧、router 初始化。
- **长上下文 NaN**：attention softmax 的数值在 128K 以上很敏感，需要 FlashAttention-3 + scale trick。
- **Gradient AllReduce 溢出**：ZeRO-3 反向多步累积，换成 FP32 reduce。

### 15.4 真实世界的”诡异故障”案例

工业训练的大部分时间都在和一些”看不见的坑”做斗争。下面几例是公开工程报告和故障复盘里反复出现的类型化问题，不逐条对应某一家公司：

1. **静默数据损坏（SDC）**：某 GPU 的 SM 偶发算错一个 bit，loss 缓慢偏离。定位靠 replay 两个不同 rank 的同批次数据比对。解决：周期性 checksum；故障卡打标，调度绕开。
2. **HBM ECC 错误累积**：BF16 训到后期突然 NaN，日志查到 ECC 纠正计数暴增。换卡 + 重 load checkpoint。
3. **NCCL 死锁**：某个 rank 因为磁盘满/dataset 读超时，集合通信全链卡住。方案：全 rank watchdog + 超时自动 dump stack。
4. **慢节点（straggler）**：一张卡因散热问题降频 20%，PP/DP 全阻塞在 AllReduce。方案：周期性 ping 各 rank 的 step time，异常值剔除。
5. **NVLink 一条挂了**：节点内 8 卡变 7 卡有效，TP 全锅。nvidia-smi `nvlink -s` 自动巡检。
6. **IB 抖动**：丢包导致 NCCL 超时。方案：`NCCL_IB_TIMEOUT`/`NCCL_IB_RETRY_CNT` 调大 + 网络侧 BER 监控。
7. **MoE 路由爆炸**：某 step top-1 命中 > 80% 集中到单 expert，capacity overflow 丢 token，loss 直接跳 10×。方案：auxiliary-free balancing + bias EMA。
8. **Checkpoint 写崩**：`torch.save` 单机写 1TB 权重写到一半掉线。方案：分片并行写 + 原子 rename + 异步（见第 10 篇）。

这些坑没有哪一条能靠”看论文”避开，全是血泪。一套成熟训练系统的差异就体现在这里。

## 十六、FAQ：十个被频繁问到的问题

**Q1：既然 ZeRO-3 能省到 1/N 显存，为什么还要 TP/PP？** ZeRO-3 的代价是前 / 反向前要 AllGather 完整权重，跨节点带宽一被打爆，MFU 就崩。TP/PP 切的是”永久切”，权重常驻本地，通信量反而小。超 50B 后纯 ZeRO-3 不现实。

**Q2：FSDP2 和 Megatron-LM 二选一怎么选？** Python 代码可读性、快速试错、与 HF 生态打通 → FSDP2 / TorchTitan。 追求极限 MFU、成熟 3D 并行、FP8、稳定支持 671B 级 → Megatron-Core。

**Q3：MoE 非得用 EP 吗？** 小 MoE（< 8 expert）可以用 TP 切。但 expert 多起来（DeepSeek 256 个），TP 切不动，必须 EP。EP + all-to-all 的瓶颈正是当下的主战场。

**Q4：PP 的 micro-batch 越多越好？** 一定范围内是的。`M ≥ 4P` 气泡才可接受。但 M 太大会让激活存不下（1F1B 下激活 = P 份，不受 M 影响；GPipe 下 = M 份，会爆）。

**Q5：ZeRO-Offload 到 CPU 真的能训 70B 吗？** 能，但吞吐常是纯 GPU 方案的 1/5–1/3。更适合 SFT / LoRA / 消融实验。

**Q6：TP 为什么不能跨节点？** TP 每层 AllReduce 几百 MB，一步几十次。NVLink 900GB/s 和 IB 50GB/s 差一个数量级，跨节点 TP 的通信时间会盖住 GEMM。

**Q7：DualPipe 是银弹吗？** 不是。显存要多一份权重副本，Dense 大模型不划算；对 MoE 的 all-to-all 重叠收益大。对上下文极长（激活巨大）场景也未必适合。

**Q8：Sequence Parallel 和 Context Parallel 有什么差别？** Megatron 术语里，**SP** 特指与 TP 合体的版本（切非线性算子的 seq 维，通信量不变）。**CP**（Context Parallel）切真正的 attention 部分 seq 维，跟 Ring Attention 同类。两者通常合起来用。

**Q9：FlashAttention 与并行怎么搭？** FlashAttention 本身不引入额外通信，与 TP/PP/DP 正交；与 CP 搭配时，通常由训练框架负责 ring / all-gather 调度，FlashAttention kernel 负责每个局部块的高效 attention。

**Q10：万卡训练什么时候必须上？** 当 training tokens > 10T、model > 300B、或你想 3–4 周内出 checkpoint。小于这个规模，千卡 + 更好的工程更划算。

## 十七、一页速查表

   
|维度|通信 op|通信量级|合适的域|
|---|---|---|---|
|DP / DDP|AllReduce|O(N)|任意（跨节点）|
|ZeRO-1|AllReduce grad|O(N)|任意|
|ZeRO-2|ReduceScatter + …|O(N)|任意|
|ZeRO-3 / FSDP|AllGather + RS|1.5×O(N)|节点内优先，跨节点用 HSDP|
|TP（Megatron）|AllReduce|O(a) × 层|节点内|
|TP + SP|RS + AG|同上|节点内|
|PP|P2P send/recv|O(a) / stage|跨节点|
|Context Parallel|Ring send/recv|O(a) × ring|节点内或专属 ring|
|EP|All-to-All × 2|O(a × topk)|node-limited|

**通用口诀**：

- 带宽密集 → 留在 NVLink 内（TP/EP/SP）。
- 延迟不敏感、量小 → 放跨节点（PP）。
- 每 step 只一次 → DP/ZeRO 可以全局跨机。
- 有 MoE → EP 优先，配合 DualPipe + node-limited routing。
- 长上下文 → SP + CP，激活显存才是真敌人。

## 十八、小结

并行不是把模型切开就完事，真正的工程在于：**谁切、切到哪个通信域、与什么计算 overlap、在哪个阶段同步**。

- **DP/ZeRO/FSDP** 是基础盘——省显存，代价是 AllReduce。
- **TP** 切 hidden，吃 NVLink，**严格节点内**。
- **PP** 切 layer，跨节点友好，核心斗争是气泡——1F1B → Zero Bubble → DualPipe。
- **SP/CP** 切 seq，长上下文时代的必备。
- **EP** 是 MoE 的天然并行，配合 DualPipe 才有机会在互联受限的 GPU 集群上把 MoE 训练推到 40% 左右的 MFU。
- 没有银弹，**3D 乃至 5D 并行的组合 + 通信 overlap + 高质量算子库** 才是万卡训练的基石。

下一篇我们拆解最具代表性的两套实现：**Megatron-LM 与 DeepSpeed**。

## 参考资料

- Shoeybi et al., _Megatron-LM: Training Multi-Billion Parameter Language Models Using Model Parallelism_, 2019
- Narayanan et al., _Efficient Large-Scale Language Model Training on GPU Clusters (PTD-P)_, 2021
- Rajbhandari et al., _ZeRO: Memory Optimizations Toward Training Trillion Parameter Models_, 2020
- PyTorch FSDP / FSDP2 官方文档，torchtitan 仓库
- Huang et al., _GPipe_, 2019；Fan et al., _DAPPLE / PipeDream_, 2020
- Qi et al., _Zero Bubble Pipeline Parallelism_, 2024
- DeepSeek-AI, _DeepSeek-V3 Technical Report_, 2024；DualPipe / EPLB 开源仓库
- Liu et al., _Ring Attention with Blockwise Transformers_, 2023
- Jacobs et al., _DeepSpeed Ulysses_, 2023
- NVIDIA Transformer Engine 与 NCCL 官方文档
- Korthikanti et al., _Reducing Activation Recomputation in Large Transformer Models (Selective Recompute)_, 2022
- McCandlish et al., _An Empirical Model of Large-Batch Training_, 2018

---

**上一篇**：[训练全景：Pre-train、SFT、RLHF、DPO、蒸馏](https://quant67.com/post/llm-infra/05-training-overview/05-training-overview.html) **下一篇**：[Megatron-LM 与 DeepSpeed](https://quant67.com/post/llm-infra/07-megatron-deepspeed/07-megatron-deepspeed.html)

## 同主题继续阅读

把当前热点继续串成多页阅读，而不是停在单篇消费。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】07：Megatron-LM 与 DeepSpeed](https://quant67.com/post/llm-infra/07-megatron-deepspeed/07-megatron-deepspeed.html)

开源训练框架双雄对比，覆盖 Megatron-LM、DeepSpeed、FSDP2、torchtitan、Colossal-AI，含选型与工程实操。

2026-04-22 · architecture / ai-infra

### [大模型基础设施工程](https://quant67.com/post/llm-infra/index.html)

面向中国工程团队的大模型基础设施系列。从 GPU/CUDA/互联、训练框架与 3D 并行、vLLM/SGLang 推理引擎、量化与推测解码、RAG/Agent 到服务化、网关、可观测性与安全合规，覆盖 LLMOps 全链路。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】11：推理引擎基础](https://quant67.com/post/llm-infra/11-inference-basics/11-inference-basics.html)

从 Prefill/Decode 两阶段、KV Cache、Continuous Batching 到 PD 分离，系统讲清楚大模型推理的工程基础。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】09：RLHF 与对齐流水线](https://quant67.com/post/llm-infra/09-rlhf-pipeline/09-rlhf-pipeline.html)

从 SFT、奖励模型到 PPO、DPO、GRPO 的完整对齐流水线工程实践，覆盖 OpenAI o1、DeepSeek-R1 等推理模型的 RL 路线与主流框架选型。