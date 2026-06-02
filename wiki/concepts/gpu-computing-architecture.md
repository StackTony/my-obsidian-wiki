---
title: GPU计算架构
category: concepts
tags: [AI, GPU, CUDA, HBM, NVLink]
summary: GPU与CPU架构的本质差异：海量弱核+极简控制+以计算吞吐为主，通过延迟隐藏而非延迟避免提升性能
source_dir: AI 人工智能/AI infra/大模型基础设施工程系列
source_files: [【大模型基础设施工程】02：GPU 计算入门——SM、Tensor Core、HBM、NVLink.md]
provenance:
  extracted: 0.70
  inferred: 0.25
  ambiguous: 0.05
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: core
created: 2026-06-02
updated: 2026-06-02
relationships:
  - target: "[[concepts/llm-infra-landscape]]"
    type: derived_from
  - target: "[[concepts/cuda-software-stack]]"
    type: uses
  - target: "[[concepts/gpu-interconnect-networks]]"
    type: uses
---

# GPU计算架构

理解GPU内部机制是后续并行策略、推理调度、量化的根基。同一张H100，跑训练能打满60% MFU，跑decode却只能用到5%算力——差异来自架构。

## CPU vs GPU：本质差异

| 特征 | CPU | GPU |
|------|-----|-----|
| 设计目标 | 单条串行控制流最快 | 海量并行数据吞吐最大 |
| 晶体管分配 | 控制30-40%、Cache30-40%、计算10-20% | 控制5-10%、Cache10-20%、计算50-60% |
| 延迟策略 | **延迟避免**：大cache、乱序执行、分支预测 | **延迟隐藏**：SM挂几十到上百warp，访存时切到另一个 |
| 算力密度 | 低（FLOPs per mm²低） | 高（同样工艺节点峰值FLOPS高1-2个数量级） |

以H100 SXM5 vs Intel Sapphire Rapids对比：算力差100倍以上（989 TFLOPS vs 7 TFLOPS），带宽差10倍以上（3.35 TB/s vs 300 GB/s）。这不是工艺差异，是**架构目标**差异。

## GPU执行模型：Grid/Block/Warp/Thread

CUDA把并行抽象成三级嵌套：
- **Grid** → 整个kernel的线程集合，分布在多个SM上
- **Block** → 一个SM上执行的线程组，共享Shared Memory
- **Warp** → 32条lane同步执行一条指令，是真正的执行单位
- **Thread** → 单条ALU lane，不是传统意义上的"核心"

单个CUDA核心没有分支预测、乱序执行、独立指令指针。**真正的调度单位是SM，真正的执行单位是warp**。 ^[inferred]

## SM（Streaming Multiprocessor）

H100的SM构成：
- 128 CUDA核心
- 4× Tensor Core（FP16/BF16/FP8/INT8矩阵乘加速）
- 256 KB寄存器文件
- 228 KB Shared Memory（可配置为L1 cache）
- 4 warp scheduler

关键指标：**occupancy（活跃warp数/最大warp数）** 决定延迟隐藏能力。batch size=1的decode，每层只有很少的活干，SM饥饿——这就是decode算力利用率极低的根本原因。 ^[inferred]

## Tensor Core

Tensor Core是矩阵乘法专用加速器，每个周期完成4×4矩阵的FMA运算：
- FP16/BF16：989 TFLOPS（H100 SXM5，不含稀疏）
- FP8：1979 TFLOPS（含稀疏可达3958 TFLOPS）
- INT8：与FP8吞吐相同

Transformer前向中QKV投影、MLP两个GEMM、输出投影全部落在Tensor Core上——这是GPU跑大模型比CPU快100倍的核心硬件原因。 ^[inferred]

## HBM（High Bandwidth Memory）

- HBM3：80GB容量、3.35 TB/s带宽（H100 SXM5）
- 对比DDR5：8通道≈300 GB/s，GPU带宽优势10倍以上

decode阶段的瓶颈不是算力而是**HBM带宽**：每生成一个token，需要从HBM读出140GB权重+KV缓存，算术强度极低（≈140 GFLOPs / 140 GB ≈ 1 FLOP/Byte）。 ^[inferred]

## Roofline模型

| 操作类型 | 算术强度 | 瓶颈 | 典型场景 |
|----------|----------|------|----------|
| 矩阵乘（GEMM） | 高（>100 FLOP/Byte） | **计算** | Prefill、训练前向 |
| Element-wise | 中 | 计算或带宽 | GELU、RMSNorm、Softmax |
| Decode逐token | 极低（≈1 FLOP/Byte） | **带宽** | 自回归生成 |

Roofline是理解GPU性能瓶颈的第一工具：算术强度低于拐点→带宽瓶颈，高于拐点→计算瓶颈。 ^[inferred]

## 来源

- 大模型基础设施工程系列02：GPU计算入门（raw/sources/AI 人工智能/AI infra/大模型基础设施工程系列/）