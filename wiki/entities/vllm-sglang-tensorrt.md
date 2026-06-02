---
title: 推理引擎对比（vLLM/SGLang/TensorRT-LLM/TGI）
category: entities
tags: [AI, vLLM, SGLang, TensorRT-LLM, 推理引擎]
summary: 四大主流推理引擎对比：vLLM开源生态最强、SGLang延迟最优、TensorRT-LLM吞吐最高、TGI企业级最稳
source_dir: AI 人工智能/AI infra/大模型基础设施工程系列
source_files: [【大模型基础设施工程】13：vLLM  -  SGLang  -  TensorRT-LLM  -  TGI 对比.md]
provenance:
  extracted: 0.60
  inferred: 0.35
  ambiguous: 0.05
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: core
created: 2026-06-02
updated: 2026-06-02
relationships:
  - target: "[[concepts/llm-inference-engine]]"
    type: implements
  - target: "[[concepts/paged-attention-continuous-batching]]"
    type: uses
  - target: "[[concepts/llm-infra-landscape]]"
    type: related_to
---

# 推理引擎对比（vLLM/SGLang/TensorRT-LLM/TGI）

推理引擎选型取决于延迟、吞吐、功能和运维约束——没有万能最优，只有场景最优。

## 四大引擎定位

| 引擎 | 定位 | 核心优势 | 核心劣势 |
|------|------|----------|----------|
| **vLLM** | 开源推理引擎标杆 | PagedAttention、生态最广、社区活跃 | 多LoRA支持弱、延迟不如SGLang |
| **SGLang** | 低延迟推理引擎 | RadixAttention前缀缓存、延迟最优 | 生态不如vLLM、模型覆盖少 |
| **TensorRT-LLM** | NVIDIA官方推理引擎 | 吞吐最高、GPU深度优化、KV cache量化 | 闭源、NVIDIA绑定、编译慢 |
| **TGI** | HuggingFace企业级引擎 | 模型兼容性最好、开箱即用、FlashAttention | 吞吐不如vLLM/TensorRT |

## 核心技术差异

| 技术 | vLLM | SGLang | TensorRT-LLM | TGI |
|------|------|--------|--------------|-----|
| KV缓存管理 | PagedAttention | RadixAttention | 连续分配+量化 | FlashAttention |
| Batching | Continuous | Continuous | Continuous | Continuous |
| 前缀缓存 | 支持 | 自动RadixTree | 支持 | 支持 |
| 量化 | FP8/AWQ/GPTQ | FP8/AWQ/GPTQ | FP8/INT8/INT4 | bitsandbytes/GPTQ |
| PD分离 | 支持 | 支持 | 支持 | 不支持 |
| 多LoRA | 实验性 | 实验性 | 支持 | 支持 |
| 流式输出 | 支持 | 支持 | 支持 | 支持 |

## 选型决策

### 按延迟优先 → SGLang
- RadixAttention自动缓存共享前缀（system prompt）
- 单token延迟（TPOT）通常比vLLM低30-50%
- 适合：对话式应用、实时交互

### 按吞吐优先 → TensorRT-LLM
- NVIDIA深度优化kernel
- 吞吐通常比vLLM高20-40%
- 适合：批量处理、高QPS服务

### 按生态/运维优先 → vLLM
- 社区最活跃、模型支持最广、文档最完善
- 开源、无厂商绑定
- 适合：通用推理服务、快速迭代

### 按开箱即用优先 → TGI
- HuggingFace模型一键部署
- 适合：企业快速上线、非深度优化场景

## 来源

- 大模型基础设施工程系列13：推理引擎对比（raw/sources/AI 人工智能/AI infra/大模型基础设施工程系列/）