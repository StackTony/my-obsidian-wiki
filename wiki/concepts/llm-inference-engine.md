---
title: LLM推理引擎基础
category: concepts
tags: [AI, LLM, 推理, KV cache, batching]
summary: LLM推理的两阶段（Prefill+Decode）心智模型：推理优化首先是资源调度问题，而非纯粹的算法优化
source_dir: AI 人工智能/AI infra/大模型基础设施工程系列
source_files: [【大模型基础设施工程】11：推理引擎基础.md]
provenance:
  extracted: 0.70
  inferred: 0.25
  ambiguous: 0.05
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: core
created: 2026-06-02
updated: 2026-06-11
relationships:
  - target: "[[concepts/llm-infra-landscape]]"
    type: derived_from
  - target: "[[concepts/paged-attention-continuous-batching]]"
    type: uses
  - target: "[[concepts/llm-quantization-engineering]]"
    type: uses
  - target: "[[concepts/speculative-decoding-mtp]]"
    type: uses
---

# LLM推理引擎基础

推理优化的第一要义不是"让计算更快"，而是**让[[concepts/gpu-computing-architecture|GPU计算架构]]的资源（HBM带宽、SM算力、显存空间）在动态请求流中被持续高效利用**。

## Prefill vs Decode：两种截然不同的负载

| 维度 | Prefill | Decode |
|------|---------|--------|
| **目的** | 处理输入prompt，生成KV cache | 逐token自回归生成 |
| **算术强度** | 高（矩阵乘，>100 FLOP/Byte） | 极低（≈1 FLOP/Byte） |
| **瓶颈** | **计算**（Tensor Core利用率高） | **带宽**（读权重+KV cache，SM饥饿） |
| **MFU** | 60%+ | 5-10% |
| **优化方向** | FlashAttention、Chunked Prefill | PagedAttention、Continuous Batching、量化 |

Prefill是"加工原材料"，Decode是"逐个产品出库"。同一GPU上两者不能共享调参逻辑——Prefill要最大化计算吞吐，Decode要最大化带宽利用。 ^[inferred]

## KV Cache：推理显存的核心账

- 70B FP16模型，单token KV cache约140GB（权重）+ 2-4MB/token（KV cache）
- 一个batch=32、上下文=4K的请求，KV cache约占2-4GB显存
- 上下文增长到128K时，KV cache可能占掉一半甚至更多HBM → 并发上限骤降
- **GQA/MLA**：GQA将KV头数减少（如8:1），MLA将KV压缩到低秩latent，分别压缩KV缓存几倍到一个数量级 ^[inferred]

## Batching演进：从静态到动态

| Batching方式 | 描述 | 优缺点 |
|-------------|------|--------|
| **Static Batching** | 等凑够N个请求一起处理 | 简单但浪费：短请求等长请求完成 |
| **Continuous Batching** | 请求完成即释放slot，新请求立即填充 | 吞吐提升2-4倍，vLLM核心设计 |
| **Chunked Prefill** | 将长prompt分块处理，与decode混合调度 | 减少Prefill占用，提高GPU利用率 |

Continuous Batching是推理引擎的现代范式——所有主流引擎（vLLM、SGLang、TensorRT-LLM、TGI）都已采纳。 ^[inferred]

## 推理性能指标

| 指标 | 定义 | 目标 |
|------|------|------|
| **TTFT（首token延迟）** | 用户发送prompt到收到第一个token的时间 | Prefill阶段决定，越短越好 |
| **TPOT（每token延迟）** | 生成每个后续token的时间 | Decode阶段决定，影响用户感知 |
| **吞吐** | 单GPU每秒生成的token总数 | 并发×TPOT的优化目标 |

## [[concepts/llm-serving-infrastructure|推理服务化]]中的PD分离（Prefill-Decode Disaggregation）

- 将Prefill和Decode放在不同GPU上独立优化
- Prefill节点：大batch、高MFU、FlashAttention
- Decode节点：小batch、高带宽利用率、PagedAttention
- KV cache通过网络传递（RDMA/PCIe），实现"生产者-消费者"架构 ^[inferred]
- 代表方案：Mooncake、DistServe

## 来源

- 大模型基础设施工程系列11：推理引擎基础（raw/sources/AI 人工智能/AI infra/大模型基础设施工程系列/）