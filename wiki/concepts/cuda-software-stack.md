---
title: CUDA软件栈
category: concepts
tags: [AI, CUDA, GPU, cuBLAS, cuDNN, NCCL]
summary: CUDA软件栈的分工与层级：上层框架的性能最终落到kernel、算子库和集合通信上
source_dir: AI 人工智能/AI infra/大模型基础设施工程系列
source_files: [【大模型基础设施工程】03：CUDA 生态——cuBLAS、cuDNN、NCCL、Triton、CUTLASS.md]
provenance:
  extracted: 0.65
  inferred: 0.30
  ambiguous: 0.05
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-02
relationships:
  - target: "[[concepts/gpu-computing-architecture]]"
    type: derived_from
  - target: "[[concepts/llm-parallelism-strategies]]"
    type: uses
---

# CUDA软件栈

上层框架（PyTorch/JAX/Megatron）的性能不是凭空来的——它最终会落到kernel质量、算子库选择和集合通信效率上。理解CUDA栈的分工，才能定位性能瓶颈在哪一层。

## CUDA栈分层

| 层级 | 组件 | 职责 |
|------|------|------|
| **应用框架** | PyTorch、JAX、Megatron-LM | 模型定义、训练编排、自动微分 |
| **高级算子库** | cuBLAS、cuDNN | 矩阵乘、卷积、RNN的优化实现 |
| **集合通信** | NCCL | 多GPU间的AllReduce/AllGather/Broadcast |
| **编译/代码生成** | Triton、CUTLASS | 自定义kernel、GEMM模板 |
| **运行时/驱动** | CUDA Runtime、CUDA Driver | 内存管理、kernel launch、stream调度 |

## cuBLAS

NVIDIA的线性代数库，核心是GEMM（矩阵乘法）：
- cuBLASLt：新API，支持混合精度、layout选择、heuristic搜索最优kernel
- 所有Transformer的矩阵乘（QKV投影、MLP、输出投影）最终都走cuBLAS

## cuDNN

深度神经网络专用库：
- 卷积前向/反向的多种算法（Winograd、FFT、implicit GEMM）
- Batch Norm、Softmax、Pooling等element-wise和reduction算子
- cuDNN的heuristic会自动选择最优算法配置

## NCCL

NVIDIA集合通信库，训练扩展的核心：
- **AllReduce**：所有GPU求和后分发（梯度同步）
- **AllGather**：所有GPU收集各自数据（TP权重切分）
- **ReduceScatter**：求和后按切分分发（ZeRO梯度聚合）
- **Broadcast**：单GPU广播到所有（初始化同步）

NCCL性能取决于拓扑——NVLink通信带宽远高于PCIe（600 GB/s vs 64 GB/s），Ring vs Tree算法选择影响通信效率。 ^[inferred]

## Triton

OpenAI开发的Python-level GPU编程语言：
- 用Python语法写kernel，编译器自动优化为PTX
- FlashAttention就是用Triton实现的——显著降低内存占用
- 相比手写CUDA C，开发效率高10倍，性能接近 ^[inferred]

## CUTLASS

NVIDIA的GEMM模板库：
- 提供矩阵乘的各种切分策略（thread tile、warp tile、block tile）
- 支持混合精度（FP16 input → FP32 accumulate）
- Megatron-LM的kernel大量使用CUTLASS

## 工程要点

- **kernel选择**：cuBLASLt的heuristic不是万能的——特定模型+特定shape可能需要手动调优 ^[inferred]
- **NCCL拓扑**：同一台机器的通信拓扑（NVLink mesh vs Ring）会影响训练通信效率 ^[inferred]
- **Triton vs CUDA C**：Triton降低门槛但不降低性能上限，适合快速实现新算子 ^[inferred]

## 来源

- 大模型基础设施工程系列03：CUDA生态（raw/sources/AI 人工智能/AI infra/大模型基础设施工程系列/）