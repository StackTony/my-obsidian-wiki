---
title: Megatron-LM与DeepSpeed训练框架
category: entities
tags: [AI, Megatron, DeepSpeed, 训练框架]
summary: 开源训练框架双雄对比：Megatron-LM偏高性能内核优化、DeepSpeed偏显存优化和易用性，选型取决于规模、拓扑和团队维护能力
source_dir: AI 人工智能/AI infra/大模型基础设施工程系列
source_files: [【大模型基础设施工程】07：Megatron-LM 与 DeepSpeed.md]
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
  - target: "[[concepts/llm-parallelism-strategies]]"
    type: implements
  - target: "[[concepts/llm-training-pipeline]]"
    type: uses
  - target: "[[concepts/cuda-software-stack]]"
    type: uses
---

# Megatron-LM与DeepSpeed训练框架

框架选型不是"哪个更好"——而是取决于规模、拓扑、并行策略和团队维护能力。

## Megatron-LM

NVIDIA开发的分布式训练框架，核心特点：
- **TP+PP原生支持**：Tensor Parallel和Pipeline Parallel从底层设计
- **高性能kernel**：大量CUTLASS自定义GEMM kernel，追求极致MFU
- **并行策略组合**：TP在节点内（NVLink）、PP跨节点（InfiniBand）、DP+ZeRO更大范围
- **适用场景**：大规模训练（千卡+）、追求最高MFU、NVIDIA生态用户

## DeepSpeed

Microsoft开发的分布式训练框架，核心特点：
- **ZeRO显存优化**：三级ZeRO方案（ZeRO-1/2/3），从优化器状态到权重逐步切分
- **易用性优先**：与PyTorch深度集成，少量代码改动即可启用
- **Offload能力**：优化器状态/权重可offload到CPU/NVMe，突破GPU显存限制
- **适用场景**：资源受限、中小规模训练、PyTorch生态用户

## 核心对比

| 维度 | Megatron-LM | DeepSpeed |
|------|-------------|-----------|
| **设计哲学** | 高性能内核优化 | 显存优化+易用性 |
| **并行实现** | TP+PP内核级优化 | ZeRO+Offload策略级优化 |
| **MFU上限** | 更高（自定义kernel） | 较低（通用实现） |
| **显存效率** | 中等 | 更高（ZeRO-3+Offload） |
| **易用性** | 低（需深度修改代码） | 高（少量配置即可） |
| **生态绑定** | NVIDIA GPU | 更通用 |
| **社区活跃度** | 活跃 | 非常活跃 |

## 组合使用

- **Megatron-DeepSpeed**：Megatron负责TP/PP内核优化，DeepSpeed负责ZeRO显存管理
- 两者可以组合使用——Megatron的并行+DeepSpeed的ZeRO ^[inferred]
- 实际组合需要仔细处理通信重叠和内存管理

## 来源

- 大模型基础设施工程系列07：Megatron-LM与DeepSpeed（raw/sources/AI 人工智能/AI infra/大模型基础设施工程系列/）