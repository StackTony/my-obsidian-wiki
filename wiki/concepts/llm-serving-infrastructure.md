---
title: 推理服务化
category: concepts
tags: [AI, LLM, 服务化, Triton, Ray Serve, PD分离]
summary: 从单机引擎走向生产级集群：推理服务化要围绕SLO、资源隔离、弹性伸缩和发布回滚组织系统
source_dir: AI 人工智能/AI infra/大模型基础设施工程系列
source_files: [【大模型基础设施工程】21：推理服务化.md]
provenance:
  extracted: 0.60
  inferred: 0.35
  ambiguous: 0.05
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-11
relationships:
  - target: "[[concepts/llm-inference-engine]]"
    type: extends
  - target: "[[concepts/llm-infra-landscape]]"
    type: derived_from
  - target: "[[concepts/llm-gateway]]"
    type: related_to
---

# 推理服务化

单机推理引擎解决了"怎么高效计算"的问题，但生产环境需要解决"怎么可靠服务"的问题——推理服务化要围绕SLO、资源隔离、弹性伸缩和发布回滚组织系统。

## 推理服务化的核心挑战

| 挑战 | 描述 |
|------|------|
| **SLO管理** | TTFT/TPOT/吞吐指标必须有明确目标 |
| **资源隔离** | 不同模型/不同优先级请求需隔离资源 |
| **弹性伸缩** | 请求波动大，需自动扩缩容 |
| **发布回滚** | 模型版本切换需要零停机 |
| **多模型共存** | 同一集群可能服务多个模型版本 |

## 推理服务框架

### Triton Inference Server（NVIDIA）
- 支持多框架后端（TensorRT、PyTorch、ONNX、自定义）
- Dynamic Batching：自动将请求拼成batch
- 多模型实例并发：同一GPU上多个模型实例
- 模型版本管理：支持多版本共存和渐进发布

### Ray Serve
- 基于Ray分布式框架的推理服务
- 支持模型组合（多模型pipeline）
- 自动伸缩：基于请求量调整副本数
- 适合：需要多模型编排的复杂推理pipeline

### KServe（原KFServing）
- Kubernetes原生推理服务
- 自动伸缩（基于Prometheus指标）
- Canary rollout：渐进发布新模型版本
- 适合：云原生环境、K8s生态

## PD分离架构

- Prefill节点和Decode节点独立部署
- Prefill节点：高MFU、大batch、FlashAttention
- Decode节点：高带宽利用、小batch、[[concepts/paged-attention-continuous-batching|PagedAttention]]
- KV cache通过网络传递（RDMA/InfiniBand）
- 代表方案：Mooncake（清华）、DistServe
- 优势：各阶段独立优化→整体吞吐更高 ^[inferred]
- 劣势：KV传递的网络开销和一致性管理 ^[inferred]

## 来源

- 大模型基础设施工程系列21：推理服务化（raw/sources/AI 人工智能/AI infra/大模型基础设施工程系列/）