---
title: MoE训练工程
category: concepts
tags: [AI, LLM, MoE, 稀疏激活, 专家混合]
summary: MoE用稀疏激活换取参数规模——路由均衡、Expert Parallel和All-to-All通信才是真正的工程难点，而非"多几个专家"
source_dir: AI 人工智能/AI infra/大模型基础设施工程系列
source_files: [【大模型基础设施工程】08：MoE 训练工程.md]
provenance:
  extracted: 0.60
  inferred: 0.35
  ambiguous: 0.05
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-02
relationships:
  - target: "[[concepts/llm-training-pipeline]]"
    type: extends
  - target: "[[concepts/llm-parallelism-strategies]]"
    type: uses
  - target: "[[entities/megatron-deepspeed]]"
    type: uses
---

# MoE训练工程

MoE（Mixture of Experts，专家混合）的核心是用**稀疏激活**换取参数规模：模型总参数很多，但每个token只激活少数专家，实际计算量远小于Dense模型。

## MoE演进

| 模型 | 专家数 | 激活参数 | 总参数 | 路由方式 | 关键创新 |
|------|--------|----------|--------|----------|----------|
| GShard | 每层数百专家 | ~2 | 数百B | Top-2 | 首次大规模MoE |
| Switch Transformer | 每层128专家 | ~1 | 1.6T | Top-1 | 单专家路由，简化计算 |
| Mixtral 8x7B | 每层8专家 | ~2 | 47B | Top-2 | 首个开源MoE基座 |
| DeepSeek-V2/V3 | 每层160+专家+共享专家 | ~1-6 | 236B | Top-6 | 细粒度+共享专家+MLA |

## 三个工程难点

### 1. 路由均衡（Load Balancing）
- 问题：如果所有token都路由到同一个专家，其他专家空闲→浪费计算和显存
- 解决方案：
  - **Auxiliary Loss**：在训练目标中加入负载均衡惩罚项
  - **Expert Choice路由**：让专家选择token而非token选择专家
  - **共享专家**：DeepSeek首创，1-2个专家始终激活，处理通用知识 ^[inferred]

### 2. Expert Parallel（专家并行）
- 每个GPU只存储一部分专家的权重 → EP
- Token路由到其他GPU的专家 → All-to-All通信
- All-to-All通信量 = batch_size × hidden_dim × 2（send+receive）
- 通信瓶颈：跨节点All-to-All比AllReduce更难优化 ^[inferred]

### 3. All-to-All通信优化
- MoE训练的通信热点是All-to-All（而非AllReduce）
- 优化策略：
  - **Expert Placement**：热点专家多放几个GPU副本
  - **通信计算重叠**：发送上一批token时同时计算当前批
  - **DualPipe**：DeepSeek的PP+EP并行方案，通信和计算流水重叠 ^[inferred]

## MoE推理的挑战

- **Expert权重加载**：总参数远大于激活参数，显存瓶颈更严重
- **路由决策开销**：每个token需要路由计算（Gating网络），增加延迟
- **动态batch**：不同token路由到不同专家，batch组成因token而异 ^[inferred]

## 来源

- 大模型基础设施工程系列08：MoE训练工程（raw/sources/AI 人工智能/AI infra/大模型基础设施工程系列/）