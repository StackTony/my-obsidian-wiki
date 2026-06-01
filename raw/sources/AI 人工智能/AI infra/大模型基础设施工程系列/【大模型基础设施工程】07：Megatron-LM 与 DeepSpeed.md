上一篇我们系统梳理了 3D 并行的原理。到了 1B 参数以上的规模，训练团队通常不会从零实现这些并行策略，而是站在 **Megatron-LM / Megatron-Core**、**DeepSpeed**、**FSDP2** 这几条成熟路线之上。公开论文、技术报告和开源代码能确认的一点是：Megatron 系和 ZeRO 系方案共同塑造了过去几年大模型训练栈的基本形态。

本篇是系列第 7 篇，聚焦开源训练框架：

- 框架全景：为什么有这么多选择，它们在解决什么问题
- Megatron-LM 深度：TP / SP / PP / Mcore
- DeepSpeed 深度：ZeRO / Offload / MoE / Ulysses
- PyTorch 官方路线：FSDP、FSDP2、torchtitan
- Colossal-AI 与国产生态
- 选型矩阵与工程踩坑
- 公开材料中的训练框架线索

## 一、框架全景：一张地图先看清位置

训练框架本质上是在把 PyTorch 里的 `nn.Module` 拆到多个 GPU 上，同时尽量不让算法工程师察觉。但”拆”有几种完全不同的哲学，于是演化出了多个流派。

### 1.1 三大流派

**流派 A：PyTorch 原生（DDP → FSDP → FSDP2）**

- Meta 主导，PyTorch 官方。
- 哲学：**切权重 + 切优化器状态**（ZeRO 风格），但保持张量形状完整。
- 优点：与原生 `nn.Module` 无缝；代码最少；调试最容易。
- 缺点：Tensor Parallelism 支持较晚（2024 DTensor 才成熟），超大模型仍吃力。

**流派 B：Megatron-LM / Megatron-Core（Nvidia）**

- Nvidia 2019 年起维护，为大模型量身定制。
- 哲学：**切模型**（张量并行 + 流水线并行），对 Transformer 结构硬编码。
- 优点：MFU（Model FLOPs Utilization）最高；一线大厂标配；生态深入（TE、cuBLAS、Flash-Attn 全家桶）。
- 缺点：侵入式 API，改一个 layer 要改一堆代码；调试门槛高。

**流派 C：DeepSpeed（Microsoft）**

- 微软 2020 年发布，与 Megatron 同期崛起。
- 哲学：**ZeRO + Offload**，尽可能不改模型代码。
- 优点：易用（一个 JSON 配置）；Offload / NVMe 支持让穷人也能训大模型；生态外延广（MoE、Chat/RLHF、推理）。
- 缺点：TP / PP 支持不如 Megatron；近两年势头被 FSDP2 追赶。

三者并非互斥：早期 BLOOM、GPT-NeoX 流行的 “Megatron-DeepSpeed” 组合，就是 TP / PP 用 Megatron、ZeRO-1 用 DeepSpeed。

### 1.2 其他重要选手

|框架|组织|定位|
|---|---|---|
|torchtitan|Meta / PyTorch|官方示例，演示 FSDP2 + TP + PP + FP8|
|Colossal-AI|潞晨科技（新加坡国大 → 商业化）|国内易用派，全家桶|
|GPT-NeoX|EleutherAI|基于 Megatron-DeepSpeed 的研究分支|
|OSLO|TUNiB（韩国）|曾活跃，现合并进 HF Accelerate|
|Mesh-TensorFlow / T5X / Pax|Google|JAX 路线，TPU 原生|
|MaxText|Google|JAX 最新旗舰示例|
|Axolotl / LLaMA-Factory / unsloth|社区|SFT/LoRA 微调包装器|
|NeMo|Nvidia|端到端产品，封装 Megatron-Core|
|HAI-LLM|DeepSeek|闭源，DualPipe 已开源|
|Internevo / InternLM-train|上海 AI Lab|书生系列自研|
|昆仑镜 / PaddleNLP|百度|飞桨大模型套件|

### 1.3 一张对比表

     
|维度|FSDP2|Megatron-Core|DeepSpeed|torchtitan|Colossal-AI|
|---|---|---|---|---|---|
|主要组织|Meta / PyTorch|Nvidia|Microsoft|Meta / PyTorch|潞晨|
|主要并行|DP + ZeRO-3|TP+PP+SP+CP+DP|ZeRO 1/2/3|FSDP2+TP+PP+CP|ZeRO + Gemini|
|代码侵入|极低|高|极低|中|中|
|MFU 潜力（70B，经验区间）|35–45%|45–55%+|30–40%|40–50%|35–45%|
|Offload|有（实验）|无|NVMe 成熟|无|有|
|MoE|需第三方|内置|内置|实验|内置|
|FP8|实验（torchao）|成熟（TE）|实验|成熟|实验|
|长上下文|CP（新）|CP + SP 成熟|Ulysses|CP|实验|
|学习成本|低|高|低-中|中|中|

### 1.4 什么时候用什么

先给结论，后面再展开：

- **参数 < 1B**：单机 DDP 或 FSDP2 就够了。
- **1B – 10B**：FSDP2 + 可选 TP，或 Megatron TP=2 / TP=4。
- **10B – 70B**：Megatron-LM / Megatron-Core（TP + PP + DP）是主流。
- **> 100B / MoE**：Megatron-Core + 自研补丁，或 DeepSpeed-MoE / MegaBlocks。
- **研究原型 / 小团队**：torchtitan、Axolotl、Colossal-AI。
- **NVMe offload、单机榨干**：DeepSpeed ZeRO-3 Offload。

上表里的 MFU 不是 benchmark 结论，只是 2025–2026 年常见硬件和 LLaMA 类 dense 模型上的经验区间。真实数值会被 GPU 代际、网络拓扑、seq length、micro-batch、重计算策略、数据管线和算子版本一起拉动。

### 2.1 起源与定位

2019 年 Nvidia 发表 _“Megatron-LM: Training Multi-Billion Parameter Language Models Using Model Parallelism”_，首次在工业界给出了 Transformer 张量并行（Tensor Parallelism，后文简称 TP）的完整实现。之后持续演化：

- **2019**：原始论文，TP 切分。
- **2021**：_Efficient Large-Scale Language Model Training on GPU Clusters_，引入交错 1F1B 流水线。
- **2022**：_Reducing Activation Recomputation_，提出 Sequence Parallelism（序列并行，SP）。
- **2023**：Megatron-Core 独立，作为可嵌入库。
- **2024–2025**：Zero-Bubble Pipeline、Context Parallelism、MoE、FP8、Mamba/SSM 支持陆续合入。

**定位**：Nvidia 为自家 GPU 训练栈提供的参考实现和底层库。它的优势来自长期围绕 A100 / H100 / B200、NCCL、Transformer Engine、FlashAttention 等组件做协同优化；在 70B LLaMA 类模型上，配置得当时能把 MFU 推到 50% 左右甚至更高，但这不是脱离硬件和模型结构的通用保证。

### 2.2 目录结构一览

一个 2025 年的 Megatron-LM 仓库大致如下：

```
Megatron-LM/
├── megatron/
│   ├── core/                   # Megatron-Core，可 pip
│   │   ├── tensor_parallel/    # ColumnParallelLinear 等
│   │   ├── pipeline_parallel/  # 1F1B / Interleaved / ZB 调度
│   │   ├── transformer/        # Block、LayerNorm、MLP、Attention
│   │   │   └── moe/            # GroupedMLP、token dispatcher
│   │   ├── distributed/        # DDP、param buckets
│   │   ├── optimizer/          # 分布式 Adam
│   │   └── datasets/           # GPT dataset、blended dataset
│   ├── training/               # pretrain 入口、checkpoint 逻辑
│   ├── inference/              # 推理入口（轻量）
│   └── legacy/                 # 老版保留
├── examples/                   # GPT、BERT、T5、Retro 的启动脚本
├── tools/                      # preprocess_data、checkpoint convert
└── tests/
```

初学者的主路径：`examples/gpt3/`（启动脚本）→ `megatron/training/pretrain.py`（训练循环）→ `megatron/core/models/gpt/gpt_model.py`（模型）→ `megatron/core/tensor_parallel/layers.py`（并行层）。

### 2.3 Tensor Parallelism 实现细节

Transformer 里主要两块计算：**Attention** 和 **MLP**。Megatron 对它们都做了 TP。

**MLP 块（最典型）**：`Y = GeLU(XA) · B`

- 第一个 Linear `XA`：**按列切** A 成 `[A1, A2, ..., An]`，每 rank 算 `X · Ai`。这一步没有通信。
- GeLU 激活：逐元素，不影响切分。
- 第二个 Linear `· B`：**按行切** B 成 `[B1; B2; ...; Bn]`，每 rank 算 `GeLU(XAi) · Bi`。这一步结果需要在 rank 间 **all-reduce 求和**。

一个 MLP 前向有 1 次 all-reduce。反向多一次 all-reduce。

**Attention 块**：

- QKV 投影：按 head 维度列切（每 rank 管若干 head）。
- Attention 本体：每 rank 独立做自己的 head，不通信。
- Output 投影：按行切，最后 all-reduce。

所以一个 Transformer Layer 的 TP 通信成本固定是 **2 次前向 + 2 次反向 all-reduce**（attention + mlp 各一次）。这也是为什么 TP 的规模受限于 NVLink/NVSwitch 域——8 卡 NVLink 内 all-reduce 还能承受，跨节点走 IB 就变成灾难。

伪代码示意：

```
class ColumnParallelLinear(nn.Module):
    def __init__(self, in_f, out_f, tp_size):
        super().__init__()
        self.weight = nn.Parameter(torch.empty(out_f // tp_size, in_f))

    def forward(self, x):
        return F.linear(x, self.weight)  # 无通信

class RowParallelLinear(nn.Module):
    def __init__(self, in_f, out_f, tp_size):
        super().__init__()
        self.weight = nn.Parameter(torch.empty(out_f, in_f // tp_size))

    def forward(self, x):
        out = F.linear(x, self.weight)
        dist.all_reduce(out, group=tp_group)  # 关键通信点
        return out
```

### 2.4 Sequence Parallelism（序列并行 / 激活切分）

TP 切了权重，但激活值（`X` 本身）还是在每个 rank 完整存一份——这在 seq_len 很长时会成为显存瓶颈。

Megatron 2022 年的 SP 把 **LayerNorm 和 Dropout** 这些”沿序列维度 element-wise”的算子，按 seq 维度切到 TP ranks 上。代价是把 all-reduce 替换成 **reduce-scatter + all-gather**（带宽总量一样，但中间激活省一半）。

开启方式：`--sequence-parallel`（依赖 `--tensor-model-parallel-size > 1`）。

### 2.5 Pipeline Parallelism：从 1F1B 到 Zero Bubble

**朴素 PP (GPipe)**：切成 N 段，第一段算完全部前向再反向。bubble（流水线气泡）巨大。

**1F1B**：一个 forward 接一个 backward，稳态下 bubble 比例为 `(p-1)/(m+p-1)`，`p` 是 stage 数，`m` 是 micro-batch 数。Megatron 默认调度。

**Interleaved 1F1B（虚拟流水线）**：每个 GPU 持有多个非连续 stage（比如 GPU0 管 layer 0–3 和 layer 16–19），bubble 变成 `(p-1)/(v·m+p-1)`，`v` 是每 GPU 的 chunk 数。通信次数增加 `v` 倍，换 bubble 缩减。

**Zero Bubble Pipeline (ZB-H1 / ZB-V)**：2023 年 Sea AI Lab 提出，利用”权重梯度计算可以延后”的特性，把 backward 拆成 `B` 和 `W` 两部分，理论上 bubble 可以降到 0。Megatron 在 2024 年合入。

开启方式：

```
--pipeline-model-parallel-size 8
--num-layers-per-virtual-pipeline-stage 2   # 开 interleaved
--use-zero-bubble-pipeline                  # 开 ZB（较新版本）
```

### 2.6 Megatron-Core：从”脚本”到”库”

早期 Megatron-LM 是一坨脚本 + 模型实现，整合进下游项目很痛苦。2023 年 Nvidia 把核心并行、优化器、通信逻辑抽出为 `megatron.core`（俗称 **Mcore**），作为可 `pip install` 的库：

- `megatron.core.transformer`：Transformer block 构建。
- `megatron.core.tensor_parallel`：ColumnParallelLinear 等。
- `megatron.core.pipeline_parallel`：1F1B、Interleaved、ZB 调度。
- `megatron.core.distributed`：DistributedDataParallel、param buckets。
- `megatron.core.optimizer`：fused Adam、分布式优化器（Megatron 版 ZeRO-1）。
- `megatron.core.transformer.moe`：MoE 支持（dispatcher、grouped GEMM）。

**NeMo、Nemotron、国内多数大厂自研训练栈**（通义、Baichuan、零一万物、MiniMax、阶跃星辰等）都是包一层 Mcore。Mcore 现在才是 Nvidia 战略重心，Megatron-LM 仓库更多是”示例”角色。

### 2.7 Context Parallelism（上下文并行）

Megatron 2024 年加入 Context Parallelism（CP）专门处理长序列（32K 以上）。思路类似 DeepSpeed Ulysses，但实现路径不同——用 **Ring Attention** 在 seq 维度切分 KV，通过环形 all-gather 拼回完整 attention 结果。

- CP 切 seq，SP 切激活，两者正交可叠加。
- 通信模式是环形 P2P（send/recv）而非 all-to-all，对非 NVLink 的互联更友好。
- 开启：`--context-parallel-size 4`。

### 2.8 分布式优化器

Megatron 2022 年引入的 Distributed Optimizer（俗称 “Mcore ZeRO-1”）把 Adam 的 FP32 优化器状态沿 DP 维度切分：

- 每个 rank 只持有 `1/DP` 的优化器状态。
- 梯度 reduce-scatter 到负责的 rank 上做更新。
- 更新后 all-gather 回完整参数。

效果与 DeepSpeed ZeRO-1 等价，显存省约 4x（FP32 m/v）。与 TP / PP 完全正交，打开即用：`--use-distributed-optimizer`。

### 2.9 最小可用示例

从 `NVIDIA/Megatron-LM` 仓库跑一个 GPT 预训练最小配置（单节点 8xH100，约 7B 模型）：

```
# pretrain_gpt.sh 精简
GPUS_PER_NODE=8
NNODES=1
TP=2
PP=1
MICRO_BATCH=2
GLOBAL_BATCH=128

torchrun --nproc_per_node=$GPUS_PER_NODE pretrain_gpt.py \
  --tensor-model-parallel-size $TP \
  --pipeline-model-parallel-size $PP \
  --sequence-parallel \
  --num-layers 32 \
  --hidden-size 4096 \
  --num-attention-heads 32 \
  --seq-length 4096 \
  --max-position-embeddings 4096 \
  --micro-batch-size $MICRO_BATCH \
  --global-batch-size $GLOBAL_BATCH \
  --lr 3e-4 --min-lr 3e-5 \
  --lr-decay-style cosine \
  --weight-decay 0.1 \
  --clip-grad 1.0 \
  --bf16 \
  --use-flash-attn \
  --use-distributed-optimizer \
  --recompute-activations \
  --train-iters 100000 \
  --data-path /data/my_gpt_text_document \
  --tokenizer-type GPTSentencePieceTokenizer \
  --tokenizer-model /data/tokenizer.model \
  --save /ckpt --save-interval 2000 \
  --tensorboard-dir /tb
```

要点：

- `--use-distributed-optimizer`：启 ZeRO-1 风格分布式优化器。
- `--recompute-activations`：激活重计算，trade 算力换显存。
- `--bf16` 是主流稳定选择；FP8 通常还要配合 Transformer Engine、H100+ 硬件和对应版本参数。
- 数据是预先 tokenize 过的二进制 `.bin + .idx`（`tools/preprocess_data.py` 生成）。

## 三、DeepSpeed 深度

### 3.1 ZeRO：显存革命

DeepSpeed 2020 年发布，核心贡献是 **ZeRO (Zero Redundancy Optimizer)**：把 DDP 下每张卡冗余存一份的”优化器状态、梯度、参数”切到各 rank 上。

- **ZeRO-1**：切 **优化器状态**（Adam 的 m、v）。显存省 4x（FP32 优化器状态占大头），几乎零通信开销。首选。
- **ZeRO-2**：切 **梯度**。显存再省 2x，反向多一次 reduce-scatter（代替原 all-reduce，带宽不变）。
- **ZeRO-3**：切 **参数本身**。每次前向 / 反向需要临时 all-gather 权重，通信 1.5 倍于 DDP。显存最省，可以训练的模型上限取决于单层临时 gather 后的大小。

对照：FSDP = 大体等价于 ZeRO-3；FSDP2 = 基于 DTensor 重写，API 更现代。

### 3.2 ZeRO-Offload 与 ZeRO-Infinity

- **ZeRO-Offload**：优化器状态 + 梯度放 CPU，前向反向仍在 GPU。适合单机训 10B 量级。
- **ZeRO-Infinity**：进一步支持 **NVMe offload**（SSD）。论文声称可以在单机上训 32 trillion 参数（“理论上”），实际用 NVMe 会把训练速度打到地板，多用于 fine-tune 或资源极度受限场景。

配置片段：

```
{
  "zero_optimization": {
    "stage": 3,
    "offload_optimizer": {"device": "cpu", "pin_memory": true},
    "offload_param":     {"device": "nvme", "nvme_path": "/mnt/nvme"},
    "overlap_comm": true,
    "contiguous_gradients": true,
    "reduce_bucket_size": 5e8,
    "stage3_prefetch_bucket_size": 5e8,
    "stage3_param_persistence_threshold": 1e6
  },
  "bf16": {"enabled": true},
  "gradient_accumulation_steps": 16,
  "train_micro_batch_size_per_gpu": 2
}
```

### 3.3 集成方式：几乎零侵入

DeepSpeed 的卖点之一是 API 极简：

```
import deepspeed

model = MyTransformer(config)  # 原生 nn.Module
model_engine, optimizer, _, _ = deepspeed.initialize(
    model=model,
    model_parameters=model.parameters(),
    config="ds_config.json",
)

for batch in loader:
    loss = model_engine(batch).loss
    model_engine.backward(loss)
    model_engine.step()
```

`deepspeed` 命令行启动器会自动处理 torchrun 的 rank 分配。HF Transformers 的 `Trainer` 内置了 DeepSpeed 集成，大量 SFT/RLHF 脚本直接用。

### 3.4 ZeRO++：通信压缩

大规模 ZeRO-3 的瓶颈是权重 all-gather 的带宽。ZeRO++ 提出：

- **qwZ**：all-gather 权重时量化到 INT8，到达后反量化。
- **hpZ**：把 all-gather 限制在节点内（用节点内冗余副本），跨节点只做小量通信。
- **qgZ**：reduce-scatter 梯度时量化。

结合起来在 400G IB 集群上可以把 ZeRO-3 的 throughput 提升 2x 左右。

### 3.5 DeepSpeed-MoE

比 Megatron-MoE 更早的工业级 MoE 实现，提供：

- Expert Parallelism（EP）+ Data Parallelism 混合。
- 残差 MoE、PR-MoE、Mixture-of-Students（训练大 MoE，蒸馏成小 dense）。
- 通信优化：hierarchical all-to-all。

Azure OpenAI 早期 MoE 训练、BLOOM-ZeRO 都用过。下一篇 MoE 训练会展开。

### 3.6 DeepSpeed-Chat：开源 RLHF 流水线

2023 年春发布，一键跑完 SFT → RM → PPO 三阶段，是当时最早的开源 RLHF 全家桶。但现在 **OpenRLHF、trl、veRL、ColossalChat** 已经接管主流，DeepSpeed-Chat 维护变慢。第 9 篇会详细对比。

### 3.7 DeepSpeed-Ulysses：序列并行

2023 年 DeepSpeed 提出 Ulysses，把 attention 在 **head 维度** 上分到不同 rank（与 Megatron SP 切 seq 不同思路）。通过两次 all-to-all（进入 attention 前和出 attention 后）来实现，单次通信量为 `O(N·d/P)`，比 Megatron 的 Ring Attention / Context Parallelism 在某些配置下更省。

长上下文训练（32K+）的事实标准之一。第 16 篇会再讲。

### 3.8 DeepSpeed 的现在与未来

2024 年起 Microsoft 内部把更多精力投向 PyTorch 官方 FSDP2 / torchtitan 的贡献，DeepSpeed 的维护节奏放缓。但它仍是：

- **ZeRO-Offload / NVMe** 的唯一工业级实现。
- **HuggingFace Trainer** 大量脚本默认使用。
- **MoE 早期探索**（Tutel、DeepSpeed-MoE）的源头。

如果你在 2026 年开新项目，不是”必须用 DeepSpeed”的场景（例如历史代码、NVMe offload）都可以评估一下 FSDP2 是否更合适。

## 四、FSDP 与 FSDP2：PyTorch 官方路线

### 4.0 从 DDP 说起

最早的 PyTorch 多卡方案是 `DistributedDataParallel (DDP)`：每张卡复制一份模型，反向时 all-reduce 梯度。简单可靠，但显存上限由单卡决定——训 7B 模型光模型 + Adam 状态就要 ~112GB（FP32 优化器），放不下 A100。于是 FSDP 出现。

### 4.1 FSDP (v1)

2022 年随 PyTorch 1.11 引入，参考了 FairScale 的 FSDP 实现。等价于 ZeRO-3：

- 参数按 rank 切分（shard），前向前 all-gather、算完 free。
- 梯度 reduce-scatter。
- 优化器只更新本 rank 负责的 shard。

API：

```
from torch.distributed.fsdp import FullyShardedDataParallel as FSDP

model = MyTransformer(...)
model = FSDP(
    model,
    sharding_strategy=ShardingStrategy.FULL_SHARD,
    mixed_precision=MixedPrecision(
        param_dtype=torch.bfloat16,
        reduce_dtype=torch.float32,
    ),
    auto_wrap_policy=transformer_auto_wrap_policy(...),
)
```

**局限**：flat parameter（把一组 param 拼成一个大 tensor 再切）导致与 TP / PP 组合困难；自定义 wrap policy 坑多。

### 4.2 FSDP2：基于 DTensor 重写

2024 年 PyTorch 2.4+ 正式推出 FSDP2，底层换成 **DTensor**（分布式 tensor 抽象）：

- 每个 parameter 本身就是一个 `DTensor`，自然支持与 TP 共存（TP 切 dim 0，FSDP 切 dim 1）。
- API 更简单：`fully_shard(module)` 就地 wrap，不再创造新 class。
- 对 LoRA / param group / `torch.compile` 友好。

示例：

```
from torch.distributed._composable.fsdp import fully_shard, MixedPrecisionPolicy

for layer in model.layers:
    fully_shard(layer, mp_policy=MixedPrecisionPolicy(
        param_dtype=torch.bfloat16,
        reduce_dtype=torch.float32,
    ))
fully_shard(model)

for batch in loader:
    loss = model(batch).loss
    loss.backward()
    optimizer.step()
    optimizer.zero_grad()
```

FSDP2 的哲学是”组合而非封装”：TP 用 `parallelize_module`（`torch.distributed.tensor.parallel`），PP 用 `torch.distributed.pipelining`，三者都基于 DTensor，可以叠加。这也是 torchtitan 的设计基础。

### 4.3 FSDP / ZeRO-3 的坑

无论 FSDP 还是 DeepSpeed ZeRO-3，“临时 all-gather 完整权重” 是公共限制：

- **单层过大时爆显存**：MoE 的 expert 聚合、embedding 层可能在 gather 时瞬时占用很大。要么分 shard、要么开 `CPU offload`。
- **Auto-wrap 粒度**：粒度太细，通信次数多；粒度太粗，显存峰值高。经验上按 Transformer block 切是最合理的。
- **与 `torch.compile` 组合**：FSDP1 对 `torch.compile` 支持差；FSDP2 基本可用，但仍有 graph break。
- **Checkpoint 格式**：FSDP1 的 `FULL_STATE_DICT` 在大模型上会 OOM；必须用 `SHARDED_STATE_DICT`。FSDP2 默认 DTensor-aware，友好很多。

## 五、torchtitan：PyTorch 的”参考实现”

`pytorch/torchtitan` 2024 年发布，定位类似 Megatron-LM 的”官方示例仓库”，演示如何用纯 PyTorch 组合出 3D 并行：

- **FSDP2** 做数据并行 + 参数切分。
- **Tensor Parallel**（基于 DTensor）做张量并行。
- **Pipeline Parallel**（基于 `torch.distributed.pipelining`）做流水。
- **Context Parallel** 做长序列并行（Ring Attention）。
- **FP8**（通过 `torchao`）。
- **`torch.compile`** 端到端编译。

```
# torchtitan llama3 config 片段
[parallelism]
data_parallel_replicate_degree = 1
data_parallel_shard_degree = 64
tensor_parallel_degree = 8
pipeline_parallel_degree = 2
context_parallel_degree = 1

[training]
seq_len = 8192
mixed_precision_param = "bfloat16"
compile = true

[float8]
enable_float8_linear = true
```

torchtitan 的代码量远小于 Megatron-LM（~5k LOC 对 Megatron 的 ~100k），适合学习 3D 并行源码。它不是生产框架，但越来越多公司把它当作自研训练栈的”起点”。

## 六、Colossal-AI：国内易用派

潞晨科技（尤洋团队从新加坡国大衍生出的创业公司）2022 年开源 Colossal-AI。卖点：

- **把 Megatron、DeepSpeed、FSDP 的能力打包成一个 API**。
- **Gemini**：自研的 ZeRO-3 优化器，Chunk 管理做得比 DeepSpeed 激进。
- **ColossalChat**：早期 RLHF 开源实现。
- **ColossalAI Inference**：训练推理一体。
- 中文文档、中文社区活跃。

```
import colossalai
from colossalai.booster import Booster
from colossalai.booster.plugin import GeminiPlugin

colossalai.launch_from_torch(config={})
plugin = GeminiPlugin(precision="bf16", placement_policy="auto")
booster = Booster(plugin=plugin)
model, optimizer, _, _, _ = booster.boost(model, optimizer)
```

国内中小团队 / 高校用得较多；但在头部大厂，自研栈或 Megatron-Core 仍然占主导。

## 七、选型决策：我到底该用哪个

没有银弹。下面是经验矩阵，覆盖 2025 主流场景。

### 7.1 决策矩阵（SVG）

![决策矩阵（SVG）](https://quant67.com/post/llm-infra/07-megatron-deepspeed/images/07-megatron-deepspeed-fig1.svg)

### 7.2 几条经验法则

1. **能用 FSDP2 就用 FSDP2**，直到撞墙（显存不够 / 通信瓶颈）。
2. **需要 TP 跨 NVLink 域的时刻**，就该考虑 Megatron-Core。
3. **PP 是上了 128 卡才开始真正有意义**；<32 卡几乎不用。
4. **ZeRO-3 + Offload 是微调万金油**，预训练则效率不够。
5. **FP8 / MoE / Long Context 等新特性**，Megatron-Core 和 torchtitan 跟进最快。
6. **团队能力决定上限**：没有能啃源码的人，别碰 Megatron-LM 魔改。

## 八、工程实操：从启动到调优

### 8.1 参数设置的优先级

对于 Megatron 风格 3D 并行，配置顺序建议：

1. **DP size**：先定总卡数 `N`，预留 `TP × PP × DP = N`。
2. **TP size**：不超过单机 GPU 数（8 或 16），通常 2/4/8。注意 `num_heads` 必须能整除 TP。
3. **PP size**：如果 TP×DP 已够装下模型 + 激活，就 `PP=1`。否则 2/4/8。`num_layers` 必须能整除 PP。
4. **Micro-batch**：先调大 micro-batch 直到 OOM，再往回退一级。
5. **Global batch**：一般 LLM 预训练在 1M–4M tokens / step，用 `grad_accum` 凑。
6. **Seq length**：数据先决定，不够再开 Context Parallel / Ulysses。

### 8.2 MFU / HFU 是检查表

**MFU（Model FLOPs Utilization）= 训练实际完成的模型 FLOPs / 理论峰值 FLOPs**。H100 SXM 的 BF16 Tensor Core 峰值常按 989 TFLOPS 估算。一个 70B LLaMA 类模型在 H100 上跑，如果 MFU 长期低于 35%，通常说明数据管线、通信 overlap、micro-batch 或重计算策略还有明显优化空间。

**HFU（Hardware FLOPs Utilization）**：把激活重计算也算进来的”含水率”。HFU 总是 ≥ MFU。

调 MFU 的常见动作：

- 开 `--use-flash-attn`（或更新的 Flash-Attn-3）。
- 开 `--sequence-parallel` + `--tp-comm-overlap`。
- 打开 TE（Transformer Engine）FP8。
- 减少 `--recompute-granularity full` → `selective`，只重计算 attention。
- 调整 micro-batch，让 GPU 利用率饱和而不让 HBM 爆。
- 检查数据 pipeline（DataLoader）是否成为 CPU 瓶颈。

### 8.3 损失异常排查 Checklist

大模型训练最怕 loss spike（损失突然飙升）。遇到时按顺序排查：

1. **数据质量**：一段重复文本 / 乱码 / 异常 token 都可能让 loss 爆。
2. **学习率**：warmup 是否太短；grad norm 是否异常（>10 开始警觉，>100 必炸）。
3. **混合精度**：bf16 一般稳；fp16 + loss scaling 不稳；fp8 必须开 delayed scaling。
4. **TP / PP bug**：`num_heads % TP != 0`、`num_layers % PP != 0`、rank 分配错。
5. **Checkpoint 恢复**：RNG state、dataloader cursor、optim state 都要恢复。
6. **梯度 NaN**：立刻打印 grad norm per layer，找出源头 layer。
7. **硬件**：ECC、NVLink 抖动，定期跑 `dcgmi diag -r 3`。

调试技巧：开 `--log-throughput --log-memory --log-world-size-to-tensorboard`，以及 `NVTE_DEBUG=1` / `TORCH_DISTRIBUTED_DEBUG=DETAIL`。

### 8.4 Profiler 动作

- `torch.profiler` + Chrome trace：看算子级时间。
- Nsight Systems (`nsys profile`)：看 GPU / 通信 overlap。
- `nccl-tests`：单独压测集合通信带宽。
- `py-spy dump`：抓 CPU 端 pickle / dataloader 卡死。

### 8.5 通信 overlap 的常见开关

“计算与通信 overlap” 是 MFU 最重要的来源，框架提供了若干开关：

   
|开关|Megatron-LM|DeepSpeed|FSDP2|
|---|---|---|---|
|梯度 reduce 与 backward overlap|`--overlap-grad-reduce`|`"overlap_comm": true`|默认开|
|参数 gather 与 forward overlap|`--overlap-param-gather`|`"stage3_prefetch"`|`forward_prefetch`|
|TP all-reduce 与 GEMM overlap|`--tp-comm-overlap`（需 TE）|N/A|需要手动写|
|PP P2P 与计算 overlap|自动（1F1B）|自动|PP 自动|

TE（Transformer Engine）的 `--tp-comm-overlap` 是 Megatron 高 MFU 的秘密武器之一：它把 all-reduce 拆成 reduce-scatter + all-gather，分别与前后两个 GEMM overlap。

### 8.6 显存账本：一个 7B 模型例子

以 LLaMA-7B、bf16、seq=4096、micro-batch=1 为例，先做一笔粗账：

- 权重：7B × 2B = 14 GB
- 梯度：7B × 2B = 14 GB
- Adam 状态（FP32 m/v）：7B × 8B = 56 GB
- FP32 master weights（若优化器保留）：7B × 4B = 28 GB
- 激活：与实现、attention kernel、是否保存中间态、是否重计算强相关；seq=4096 时通常会成为除优化器状态外的第二个大头

不做任何切分时，光权重、梯度、Adam 状态和 master weights 就接近 112 GB，还没算激活，单张 A100-80G 放不下。方案：

1. `ZeRO-1 (DP=8)`：优化器状态切 8，Adam m/v 从 56 GB 降到单卡 7 GB；如果保留 master weights，还要另算 28 GB 或依赖优化器实现切分。
2. `ZeRO-3 (DP=8)`：权重、梯度、优化器状态都切，单卡参数状态显存大幅下降，但每层前向 / 反向会引入参数 all-gather。
3. `TP=2, DP=4`：权重 + 激活都切 2；优化器仍可 ZeRO-1。

这笔账一定要动手算，否则选型全凭感觉。

## 九、代码样例对比

在进入具体代码前，先摆出三者的心智模型差异：

- **FSDP2**：你写”单卡 PyTorch”，框架自动切分。代码量最少，但 TP / PP 要手动拼。
- **DeepSpeed**：你写”单卡 PyTorch”，传一个 JSON，框架接管。代码量少，ZeRO 开箱即用，但 TP 依赖 Megatron。
- **Megatron-LM**：你照着它的 `pretrain_gpt.py` 改配置，模型必须符合它的 block 约定。代码量看起来多，但并行”全免费”。

### 9.1 FSDP2 风格训练骨架

下面这个片段只保留 FSDP2 包裹和训练 step 的关键路径，不是完整可运行脚本。真实工程还要补 dataloader、tokenizer padding、checkpoint、分布式采样和异常恢复。

```
import torch
import torch.distributed as dist
from torch.distributed._composable.fsdp import fully_shard, MixedPrecisionPolicy
from transformers import AutoModelForCausalLM, AutoTokenizer

def main():
    dist.init_process_group("nccl")
    rank = dist.get_rank()
    torch.cuda.set_device(rank % torch.cuda.device_count())

    model = AutoModelForCausalLM.from_pretrained(
        "meta-llama/Llama-3-8B", torch_dtype=torch.bfloat16
    )
    mp = MixedPrecisionPolicy(
        param_dtype=torch.bfloat16, reduce_dtype=torch.float32
    )
    for block in model.model.layers:
        fully_shard(block, mp_policy=mp)
    fully_shard(model, mp_policy=mp)

    optim = torch.optim.AdamW(model.parameters(), lr=1e-5, betas=(0.9, 0.95))
    tok = AutoTokenizer.from_pretrained("meta-llama/Llama-3-8B")

    model.train()
    for step, batch in enumerate(load_data(tok)):
        batch = {k: v.cuda() for k, v in batch.items()}
        out = model(**batch, labels=batch["input_ids"])
        out.loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optim.step()
        optim.zero_grad(set_to_none=True)
        if rank == 0 and step % 10 == 0:
            print(f"step {step} loss {out.loss.item():.4f}")

if __name__ == "__main__":
    main()
```

启动形态通常是：`torchrun --nproc_per_node=8 train.py`。能否全量微调 8B 模型，取决于显存、batch、seq length、activation checkpointing 和优化器实现，不能只由这段骨架保证。

### 9.2 Megatron-LM 同规模训练骨架

Megatron 不走 `nn.Module` 裸写，而是通过 `pretrain_gpt.py` 这类入口 + 大量参数。核心差异大致长这样：

```
# my_pretrain.py
from megatron.training import pretrain
from megatron.core.models.gpt import GPTModel
from megatron.core.transformer.transformer_config import TransformerConfig

def model_provider(pre_process, post_process):
    cfg = TransformerConfig(
        num_layers=32,
        hidden_size=4096,
        num_attention_heads=32,
        use_cpu_initialization=False,
        bf16=True,
        tensor_model_parallel_size=2,
        pipeline_model_parallel_size=1,
        sequence_parallel=True,
    )
    return GPTModel(config=cfg,
                    vocab_size=128256,
                    max_sequence_length=4096,
                    pre_process=pre_process,
                    post_process=post_process)

def forward_step(data_iter, model):
    batch = next(data_iter)
    return model(batch["tokens"], batch["position_ids"], batch["attention_mask"]), \
           lambda loss: {"lm_loss": loss}

if __name__ == "__main__":
    pretrain(train_valid_test_dataset_provider,
             model_provider,
             ModelType.encoder_or_decoder,
             forward_step)
```

这类代码不能脱离 Megatron 的训练入口直接运行；真正的成本不在 Python 行数，而在参数 registry、checkpoint 格式、dataset index、并行 group 和恢复逻辑这些约定上。

### 9.3 DeepSpeed 集成片段

```
import deepspeed, torch
from transformers import AutoModelForCausalLM

model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-7B")
engine, opt, _, _ = deepspeed.initialize(
    model=model,
    model_parameters=model.parameters(),
    config="ds_zero3.json",
)

for batch in loader:
    out = engine(**batch, labels=batch["input_ids"])
    engine.backward(out.loss)
    engine.step()
```

启动形态通常是：`deepspeed --num_gpus 8 train.py --deepspeed ds_zero3.json`。完整工程仍要补 `ds_zero3.json`、dataloader、checkpoint 和分布式随机种子处理。

### 9.4 启动命令速查

```
# FSDP2 / torchtitan
torchrun --nproc_per_node=8 --nnodes=$N --node_rank=$R \
  --master_addr=$MASTER --master_port=29500 train.py

# Megatron-LM
torchrun --nproc_per_node=8 --nnodes=$N --node_rank=$R \
  --master_addr=$MASTER --master_port=29500 pretrain_gpt.py \
  --tensor-model-parallel-size 4 --pipeline-model-parallel-size 2 ...

# DeepSpeed（内置 launcher，读 hostfile）
deepspeed --hostfile=hostfile --num_gpus=8 train.py \
  --deepspeed --deepspeed_config ds_config.json

# NeMo（基于 PyTorch Lightning）
python examples/nlp/language_modeling/megatron_gpt_pretraining.py \
  --config-path=conf --config-name=megatron_llama_config.yaml \
  trainer.devices=8 model.tensor_model_parallel_size=4
```

三者都依赖 `NCCL` 环境变量：`NCCL_IB_HCA`、`NCCL_SOCKET_IFNAME`、`NCCL_IB_GID_INDEX` 是跨机训练最常踩的坑，第 4 篇互联讲过一次，实战中别忘了设。

## 十、Megatron-Core 生态：NeMo、Nemotron

### 10.0 三者关系图

```
                   ┌──────────────────────────────┐
                   │   Megatron-LM (GitHub 仓库)  │
                   │  示例脚本 + 研究 feature 首发│
                   └──────────────┬───────────────┘
                                  │ 复用底层
                                  ▼
                   ┌──────────────────────────────┐
                   │   Megatron-Core (pip 库)     │
                   │  TP / PP / SP / MoE / CP     │
                   │  + 分布式优化器 + FP8        │
                   └──────────────┬───────────────┘
                                  │ 封装
                                  ▼
                   ┌──────────────────────────────┐
                   │   NeMo Framework (产品)      │
                   │  数据 / 训练 / 对齐 / 推理   │
                   │  + Recipes + 商业支持        │
                   └──────────────┬───────────────┘
                                  │ 训练出
                                  ▼
                   ┌──────────────────────────────┐
                   │   Nemotron 模型家族          │
                   │  340B / 5 / Mini / Nano      │
                   └──────────────────────────────┘
```

Nvidia 的全景：

- **Megatron-LM**：研究分支 + 示例仓库。
- **Megatron-Core (Mcore)**：可 pip 的底层库。
- **NeMo Framework**：端到端产品，封装 Mcore，提供 NeMo Recipes（LLM、多模态、Speech、Vision）。
- **Nemotron**：Nvidia 自家大模型（Nemotron-4 340B、Nemotron-5）的开源权重 + NeMo 训练配方。
- **NeMo Curator**：数据清洗。
- **NeMo Aligner**：对齐（SFT/DPO/RLHF）。
- **NeMo Guardrails**：安全护栏。
- **NIM (Nvidia Inference Microservices)**：推理侧。

对企业客户：Nvidia 提供的不是 Megatron，而是整个 **NeMo 平台**。对研究者和大厂自研团队：**Mcore** 是核心。对个人 / 学习：**Megatron-LM** 仓库 + torchtitan。

## 十一、公开材料中的训练框架线索

这一节只做证据分层，不把闭源系统的传闻写成事实。括号里写“公开”的条目来自论文、技术报告、官方文档或开源仓库；公开材料不足的地方，只说明边界，不把社区推测当作训练栈披露。

### 11.1 全球

- **OpenAI GPT-3（公开论文）**：训练论文采用了 Megatron-LM 风格的模型并行思想；GPT-4 之后的底层训练栈没有完整公开。
- **Meta LLaMA 系列（公开论文 / 技术报告）**：LLaMA 早期工作与 Megatron-LM 路线关系很深；Llama 3 技术报告披露了 FSDP、tensor parallel、pipeline parallel、context parallel 等组合。
- **Google Gemini（公开材料）**：Google 大模型训练长期走 JAX / XLA / TPU 生态，Pax、T5X、MaxText 都是这条路线上的公开参考。
- **BLOOM / OPT / GPT-NeoX（公开论文与仓库）**：三者给出了较完整的 Megatron、DeepSpeed 或二者组合的历史样本。
- **Anthropic、Mistral、Cohere、xAI 等闭源训练栈**：公开材料不足以把底层框架钉死，本文不把社区推测列为事实。

### 11.2 中国

- **DeepSeek V3 / R1（公开技术报告与开源组件）**：论文披露了 HAI-LLM、DualPipe、DeepEP 等训练系统与通信组件；DualPipe / DeepEP 的公开代码能作为后续 MoE 训练文章的主要材料。
- **Qwen、GLM、InternLM 等开源模型（公开报告 / 仓库线索）**：公开材料里能看到 Megatron-LM、Megatron-Core、DeepSpeed 或厂内 fork 的影响，但不同版本差异很大，不能简单归成一个框架。
- **文心 / 盘古 / 豆包等厂内系统（公开生态）**：更多体现为厂内平台路线，例如 PaddleNLP、MindSpore 或火山内部训练平台；底层细节不完整公开。
- **Kimi、MiniMax、阶跃星辰、零一万物等闭源模型**：公开资料不足以支撑“基于某个具体框架”的强结论，最多只能说它们大概率都有自研训练基础设施。

更稳妥的判断是：**Megatron-Core 已经成为 CUDA 训练栈里非常重要的底层选项**。但在 PyTorch FSDP2、JAX/XLA、各家厂内框架和国产加速器生态并存的情况下，不能把它写成所有头部训练的唯一答案。

### 11.3 历史切片：BLOOM、OPT、GPT-NeoX

三个 2022 年的开源大模型给了我们难得的”框架考古”机会：

- **BLOOM（176B，BigScience）**：使用 **Megatron-DeepSpeed**。TP=4（Megatron）、PP=12（Megatron 1F1B）、DP=8（DeepSpeed ZeRO-1）。训练 Jean Zay 集群 384×A100。公开的训练日志、loss 曲线、故障记录至今仍是大模型 MLOps 的教科书级案例。
- **OPT（175B，Meta）**：基于 Megatron-LM 的 Meta 内部分支。日志里充斥着 loss spike、硬件故障、重启——与 BLOOM 一起揭示了 175B 规模训练的真实痛苦。
- **GPT-NeoX（20B，EleutherAI）**：基于 Megatron-DeepSpeed，研究型项目。后续 NeoX 分支被 Stability AI、MosaicML 广泛参考。

这三个项目间接奠定了 2023 年后 LLM 训练栈的共识：**Megatron 管并行，DeepSpeed 管 ZeRO**。2024 年后 Mcore 吃掉 DP 和 ZeRO-1 能力，这个”双人组”开始被单一 Mcore 替代。

## 十二、FAQ：一些高频疑问

**Q1：FSDP2 能不能完全替代 DeepSpeed？**

对 ZeRO-2/3 场景基本可以。但 DeepSpeed 的 NVMe offload、MoE、Ulysses、推理引擎是一揽子生态，不是单点功能。做 SFT/LoRA 或中小模型预训练，FSDP2 已足够；搞复杂 RLHF 或离线训练探索，DeepSpeed 仍有独到优势。

**Q2：Megatron-LM 和 Megatron-Core 到底选哪个？**

新项目一律选 **Megatron-Core**。Megatron-LM 现在是”官方示例仓库”，新 feature 先进 Core 再进 LM 脚本。你要嵌入自研训练栈，必须用 Core。

**Q3：我要训练一个带视觉输入的多模态模型，用哪个？**

- 如果底座是标准 Transformer（LLaVA 风格）：NeMo 或 torchtitan 都支持 variable seq。
- 如果要复杂 variable batch + 图像 tokenizer：Megatron-Core 配自定义 dataloader，或者 HF `accelerate` + FSDP2。
- 视频 / 超长序列：必须 Context Parallel / Ulysses。

**Q4：训练中途换框架现实吗？**

Checkpoint 格式是最大障碍。Megatron-Core 的 checkpoint 格式与 FSDP 的 DCP（Distributed Checkpoint）互不兼容。可以写 converter（HF 格式 `safetensors` 是中间枢纽），但需要仔细验证 LN、embedding tying、RoPE 等细节。

**Q5：MFU 多高才算好？**

经验值（H100，bf16，LLaMA 架构）：

- 7B 模型：MFU 45–55%。
- 70B 模型：MFU 40–50%。
- MoE 模型：MFU 30–40%（all-to-all 拖后腿）。
- 多模态 / 长上下文：MFU 30% 就算优秀。

低于这些值，先查 dataloader、通信 overlap、activation recompute 粒度。

**Q6：国产卡上哪个框架可以用？**

- Ascend（昇腾）：MindSpore / ModelEngine，也有 Megatron-NPU、DeepSpeed-NPU 分支。
- 摩尔线程 MUSA、寒武纪 MLU、壁仞 BR：主要走 PyTorch 插件路线 + FSDP / DeepSpeed。
- 2025 年开始，Megatron-Core 社区出现非 CUDA 适配 PR；但稳定性与 CUDA 差距仍大。

**Q7：什么时候该自研训练框架？**

一般大厂经历的路径：

1. 用 Megatron-LM + 小补丁（< 1B 训练）。
2. 用 Megatron-Core + 厂内数据侧、checkpoint 侧、调度侧改造（10B – 100B）。
3. 核心并行 / 调度 / 容错重写（100B+，且要上万卡）。

DeepSeek 的 HAI-LLM、字节的豆包自研栈、Meta 的 torch-native 都属于第 3 阶段。中小团队最合理的路线是长期停留在 2。

**Q8：训练稳定性和框架的关系有多大？**

中等。大部分 loss spike 来源于数据、学习率、数值精度，与框架无关；但框架会在三个地方影响稳定性：

- **梯度累加时的数值精度**：FP16 / BF16 + FP32 主权重的策略要对，否则 grad 累加会掉精度。
- **TP/PP rank 同步误差**：Megatron 内部用 FP32 allreduce 梯度；自研实现如果偷懒用 BF16 allreduce 会慢慢累计 bias。
- **Checkpoint 恢复后 optim state 漂移**：三分钟内 loss 变化不大就基本没事。

**Q9：2026 年一个新团队的”最优默认”是什么？**

保守版本：torchtitan（研究）+ Megatron-Core（生产）+ veRL / OpenRLHF（对齐）。激进版本：押注 FSDP2 + TP + PP 纯官方栈，赌 PyTorch 生态的长期胜利。

## 十三、未来趋势：框架在融合

观察 2024–2026 的走向：

1. **DTensor 统一**：FSDP2、PyTorch TP、PP 都基于 DTensor；Megatron 的 Mcore 也在接入。长远看，“哪个框架”这个问题会变得不重要，因为底层抽象在统一。
2. **编译器接管并行**：`torch.compile` + `functorch` + Inductor 正在尝试自动插入通信算子；Google Pax/XLA 已经这么做了很多年。
3. **Zero Bubble / DualPipe / Chimera** 这类新流水线调度成为标配。
4. **FP8 / MXFP8 / FP4**：训练也开始下探到 4bit；只有紧跟 Nvidia 栈的框架跟得上。
5. **Multimodal 训练**：图像 / 视频 / 音频 tokenizer、variable seq length、Context Parallel 成为一等公民；torchtitan、Mcore、Colossal-AI 都在做。
6. **国产加速器对接**：Ascend（MindSpore / Megatron-NPU）、摩尔线程、壁仞、燧原、寒武纪都有各自 Megatron/FSDP 的移植分支；2025 年开始出现可用版本。
7. **训练-推理一体化**：框架边界在推理侧也变模糊。NeMo、Colossal-AI、vLLM + RLHF 整合都在往”一份权重，训练和推理共享”的方向走。
8. **异构训练**：H100 + B200 混布、CPU + GPU offload 自动调度，是 2026 的下一个热点。

### 13.1 对一线工程师的建议

如果你是刚入行的训练工程师，一条合理的学习路径：

1. 先跑通 **单机 FSDP2**，弄清 ZeRO 三阶段的区别和显存占用。
2. 跑通 **torchtitan LLaMA-3 8B 配方**，体验 TP + FSDP2 + FP8。
3. 阅读 **Megatron-LM `megatron/core/tensor_parallel/layers.py`**，理解 ColumnParallelLinear、RowParallelLinear、gather/scatter 的数学。
4. 阅读 **`megatron/core/pipeline_parallel/schedules.py`**，手画一遍 1F1B 时空图。
5. 跑通一个 **Megatron-Core 32B 预训练**（云上租 16×H100 一两小时即可），看 MFU 能调到多少。
6. 在此基础上选一个方向深入：MoE / 长上下文 / RLHF / FP8。

### 13.2 对架构师的建议

1. **不要给算法团队两个框架**：选定后把 dataloader、checkpoint、metric 都封装到厂内统一 SDK，算法同学只看模型结构。
2. **Checkpoint 格式长期押注 `safetensors` + DCP**：HF 生态兼容，离线转换好做。
3. **把 MFU 做成一级 KPI**：所有训练任务上报 MFU / HFU / DCGM 指标到统一看板，否则优化无从谈起。
4. **抽象层不要太厚**：Colossal-AI 早期的 API 层太重，追新特性困难；Mcore 作为底层 + 厂内轻封装是更可持续的设计。
5. **接纳国产卡，但分级**：小规模实验可用，大规模关键训练谨慎；提前规划 CUDA / 非 CUDA 的两套 CI。

下一篇我们进入 **MoE 训练工程**，看看 Mixtral、DeepSeek V3、Qwen MoE 是怎样把稀疏激活玩成工程的——Expert Parallelism、All-to-All、负载均衡、DeepEP、MegaBlocks 一次性讲透。

## 参考资料

1. Shoeybi et al., _Megatron-LM: Training Multi-Billion Parameter Language Models Using Model Parallelism_, 2019.
2. Narayanan et al., _Efficient Large-Scale Language Model Training on GPU Clusters Using Megatron-LM_, 2021.
3. Korthikanti et al., _Reducing Activation Recomputation in Large Transformer Models_, 2022.
4. Qi et al., _Zero Bubble Pipeline Parallelism_, 2023.
5. Rajbhandari et al., _ZeRO: Memory Optimizations Toward Training Trillion Parameter Models_, 2020.
6. Ren et al., _ZeRO-Offload_ / Rajbhandari et al., _ZeRO-Infinity_, 2021.
7. Wang et al., _ZeRO++: Extremely Efficient Collective Communication for Giant Model Training_, 2023.
8. Jacobs et al., _DeepSpeed Ulysses: System Optimizations for Training Extremely Long Sequence Transformer Models_, 2023.
9. Meta PyTorch, _FSDP2 Design & API_, 2024；PyTorch `torchtitan` 官方仓库。
10. NVIDIA, _Megatron-Core Documentation_ & _NeMo Framework User Guide_。
11. DeepSeek AI, _DeepSeek-V3 Technical Report_ 及 DualPipe / DeepEP 开源代码。
12. Meta AI, _The Llama 3 Herd of Models_, 2024.
13. Colossal-AI 官方文档、潞晨科技技术博客。
14. BigScience, _BLOOM: A 176B-Parameter Open-Access Multilingual Language Model_, 2022.
15. Zhang et al., _OPT: Open Pre-trained Transformer Language Models_, 2022.
16. Black et al., _GPT-NeoX-20B: An Open-Source Autoregressive Language Model_, 2022.
17. Qwen Team, _Qwen2.5 Technical Report_, 2024.
18. NVIDIA, _Transformer Engine Documentation_（FP8 / TP comm overlap）。

---

**上一篇**：[3D 并行深度：数据 / 张量 / 流水 / 序列 / ZeRO](https://quant67.com/post/llm-infra/06-parallelism/06-parallelism.html) **下一篇**：[MoE 训练工程](https://quant67.com/post/llm-infra/08-moe-training/08-moe-training.html)

## 同主题继续阅读

把当前热点继续串成多页阅读，而不是停在单篇消费。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】06：3D 并行深度——数据 / 张量 / 流水 / 序列 / ZeRO](https://quant67.com/post/llm-infra/06-parallelism/06-parallelism.html)

万卡训练的基石：从 DP、TP、PP、SP、EP 到 ZeRO/FSDP，再到 DualPipe 的零气泡流水，一篇讲透并行策略的工程选型与通信优化。

2026-04-22 · architecture / ai-infra

### [大模型基础设施工程](https://quant67.com/post/llm-infra/index.html)

面向中国工程团队的大模型基础设施系列。从 GPU/CUDA/互联、训练框架与 3D 并行、vLLM/SGLang 推理引擎、量化与推测解码、RAG/Agent 到服务化、网关、可观测性与安全合规，覆盖 LLMOps 全链路。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】11：推理引擎基础](https://quant67.com/post/llm-infra/11-inference-basics/11-inference-basics.html)

从 Prefill/Decode 两阶段、KV Cache、Continuous Batching 到 PD 分离，系统讲清楚大模型推理的工程基础。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】09：RLHF 与对齐流水线](https://quant67.com/post/llm-infra/09-rlhf-pipeline/09-rlhf-pipeline.html)

从 SFT、奖励模型到 PPO、DPO、GRPO 的完整对齐流水线工程实践，覆盖 OpenAI o1、DeepSeek-R1 等推理模型的 RL 路线与主流框架选型。