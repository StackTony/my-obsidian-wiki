---
title: LLM并行策略
category: concepts
tags: [AI, LLM, 并行, 3D并行, ZeRO, 训练]
summary: 3D并行策略（DP/TP/PP/SP/EP/ZeRO）的组合选择：按瓶颈组合——内存切DP、计算切TP、通信切PP
source_dir: AI 人工智能/AI infra/大模型基础设施工程系列
source_files: [【大模型基础设施工程】06：3D 并行深度——数据  -  张量  -  流水  -  序列  -  ZeRO.md]
provenance:
  extracted: 0.65
  inferred: 0.30
  ambiguous: 0.05
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: core
created: 2026-06-02
updated: 2026-06-02
relationships:
  - target: "[[concepts/llm-training-pipeline]]"
    type: uses
  - target: "[[concepts/gpu-interconnect-networks]]"
    type: uses
  - target: "[[concepts/cuda-software-stack]]"
    type: uses
  - target: "[[entities/megatron-deepspeed]]"
    type: uses
---

# LLM并行策略

万卡训练中，DP、TP、PP、SP、EP、ZeRO不是都开越多越好。正确做法是按瓶颈组合——哪些并行策略切的是内存、哪些切的是计算、哪些切的是通信。

## 六种并行策略对比

| 策略 | 切分对象 | 内存节省 | 通信开销 | 适用场景 |
|------|----------|----------|----------|----------|
| **DP（数据并行）** | 数据batch | 优化器状态可切（ZeRO） | AllReduce梯度 | 模型能装进单卡时首选 |
| **TP（张量并行）** | 模型权重矩阵 | 权重和激活按切分比减少 | AllReduce每层前后 | 单节点NVLink内通信快 |
| **PP（流水并行）** | 模型层 | 各stage只存自己层 | 点对点传递激活 | 跨节点、网络慢时 |
| **SP（序列并行）** | 序列长度/token | 激活按token数切 | AllGather/ReduceScatter | 长上下文训练 |
| **EP（专家并行）** | MoE专家 | 各GPU只存部分专家 | All-to-All路由分发 | MoE模型 |
| **ZeRO** | 优化器状态/梯度/权重 | 三级递增 | 与DP相同但通信量不同 | 大模型DP时节省显存 |

## 三个约束

1. **内存约束**：权重+优化器+激活+临时buffer必须装进HBM → DP+ZeRO、TP、PP分别切不同部分
2. **通信约束**：TP要求NVLink（600GB/s）、PP可走InfiniBand（400Gbps） → TP放节点内、PP放节点间
3. **流水bubble**：PP的stage间存在空闲时间 → micro-batch填充、 interleaved schedule减少bubble

## 组合策略

### 小模型（<7B）→ DP为主
- 单卡装下全部权重+优化器+激活
- ZeRO-1切优化器状态即可，通信仅AllReduce梯度

### 中等模型（7B-70B）→ DP + TP
- 单节点8卡，TP=8在NVLink内切权重
- DP跨节点，ZeRO-2切优化器+梯度

### 大模型（70B+）→ DP + TP + PP（3D并行）
- TP在节点内切权重（TP=4或8）
- PP跨节点切层（PP=2或4）
- DP跨更多节点，ZeRO-3切全部状态

### MoE模型 → DP + EP + TP/PP
- EP按专家切分，All-to-All通信
- 共享专家不走EP，用TP/PP处理
- DeepSeek的DualPipe方案：PP+EP同时优化 ^[inferred]

## ZeRO三级详解

| 级别 | 切分内容 | 显存节省 | 通信量 |
|------|----------|----------|--------|
| **ZeRO-1** | 优化器状态 | 4×（Adam占大头） | =DP（AllReduce梯度） |
| **ZeRO-2** | 优化器+梯度 | 8× | ReduceScatter梯度+AllGather权重 |
| **ZeRO-3** | 优化器+梯度+权重 | N×（N=DP数） | AllGather权重每层前后 |

ZeRO-3的通信量是DP的1.5倍，但换来的是显存N倍节省——权衡取决于瓶颈在哪。 ^[inferred]

## 工程要点

- **不是越多越好**：TP增加→通信增加，PP增加→bubble增加，EP增加→All-to-All增加。组合需按瓶颈算账 ^[inferred]
- **拓扑优先**：TP放NVLink域内、PP放跨节点、DP放更大范围——通信带宽决定并行策略的效率上限 ^[inferred]
- **FSDP vs ZeRO**：PyTorch FSDP ≈ ZeRO-3，但实现不同；DeepSpeed ZeRO提供更多控制选项 ^[inferred]

## 来源

- 大模型基础设施工程系列06：3D并行深度（raw/sources/AI 人工智能/AI infra/大模型基础设施工程系列/）