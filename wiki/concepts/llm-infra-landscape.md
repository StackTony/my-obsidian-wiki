---
title: 大模型基础设施全景
category: concepts
tags: [AI, LLM, 基础设施, 训练, 推理, Agent]
summary: 大模型基础设施的五层工程栈：硬件、系统软件、框架、应用、运营，从GPU底层到服务上层的系统化工程视角
source_dir: AI 人工智能/AI infra/大模型基础设施工程系列
source_files: [【大模型基础设施工程】01：大模型基础设施全景 —— 训练、推理、RAG、Agent、观测.md]
provenance:
  extracted: 0.65
  inferred: 0.30
  ambiguous: 0.05
base_confidence: 0.83
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: core
created: 2026-06-02
updated: 2026-06-11
relationships:
  - target: "[[concepts/gpu-computing-architecture]]"
    type: uses
  - target: "[[concepts/llm-training-pipeline]]"
    type: uses
  - target: "[[concepts/llm-inference-engine]]"
    type: uses
  - target: "[[concepts/rag-engineering]]"
    type: uses
  - target: "[[concepts/agent-framework-engineering]]"
    type: uses
  - target: "[[concepts/llm-serving-infrastructure]]"
    type: uses
---

# 大模型基础设施全景

大模型（LLM）不是传统的Web服务、OLTP或OLAP——它同时是**计算密集+访存密集+状态极重+故障常态+成本极高+生命周期长**的混合负载，必须当作独立基础设施领域对待。LLM基础设施之上是 [[concepts/agent-architecture-landscape|Agent架构全景]]，两者边界详见该页面。

## 五层工程栈

| 层级 | 覆盖内容 | 代表组件 |
|------|----------|----------|
| **硬件** | GPU/TPU、HBM、[[concepts/gpu-interconnect-networks|GPU互联]] | H100、A100、昇腾910B |
| **系统软件** | [[concepts/cuda-software-stack|CUDA软件栈]]、Triton、CUTLASS | CUDA 12、NCCL 2 |
| **框架** | 训练框架、推理引擎、RAG/Agent SDK | [[entities/megatron-deepspeed|Megatron-LM]]、[[entities/vllm-sglang-tensorrt|推理引擎对比]]、[[entities/langgraph-framework|LangGraph]] |
| **应用** | 训练流水线、推理服务、RAG系统、Agent应用 | RLHF pipeline、PD分离、GraphRAG |
| **运营** | 网关、可观测、成本、合规与安全 | LiteLLM、Langfuse、AI Act |

## 四个工程分水岭（2022-2026）

1. **ChatGPT（2022.11）**：确立了LLM推理SaaS的工程范式——流式返回、速率限制、多租户
2. **LLaMA + HuggingFace（2023.2）**：确立了模型分发与微调的工程栈——llama.cpp、LoRA/QLoRA
3. **[[entities/vllm-sglang-tensorrt|推理引擎对比]] + [[concepts/paged-attention-continuous-batching|PagedAttention]]（2023.6）**：确立了推理引擎的现代范式——[[concepts/paged-attention-continuous-batching|PagedAttention]]消除碎片、Continuous Batching提升吞吐2-4倍
4. **DeepSeek-V3 + FP8 + MLA（2024末-2026）**：确立了"工程创新降低10倍成本"的范式——MLA压缩KV缓存一个数量级、FP8训练全流程落地 ^[inferred]

## 大模型的工程特征

- **Prefill vs Decode 性质不同**：Prefill算术强度高（矩阵乘密集），Decode访存瓶颈（逐token读权重+KV缓存），不能共用一套调参逻辑 ^[inferred]
- **70B模型显存不足=高并发失败**：权重140GB FP16 + 临时buffer + KV缓存随batch和上下文长度膨胀，并发上限受限于显存预算 ^[inferred]
- **万卡训练容错是常态**：节点故障、网络抖动、HBM ECC错误每天发生，必须把容错做进设计
- **推理成本正在急速下降**：从2023年的60美元/百万token压到2026年的1美元以下 ^[inferred]

## 中国与全球两条栈

- **全球**：OpenAI、Anthropic、Meta、Google、xAI、Mistral → NVIDIA GPU生态 → CUDA/TensorRT
- **中国**：DeepSeek、Qwen、GLM、Kimi、豆包、文心、盘古 → 昇腾/海光/摩尔线程国产替代路线 → 自研训练框架 ^[inferred]

开源（[[entities/vllm-sglang-tensorrt|推理引擎对比]]/SGLang/[[entities/megatron-deepspeed|Megatron-LM]]/DeepSpeed/Ray/[[entities/langgraph-framework|LangGraph]]）与商业（TensorRT-LLM/Triton/Bedrock/PAI/veMLP/千帆）并重，各有不可替代场景。

## 推荐阅读路径

- **硬件与系统基础** → GPU计算 → CUDA栈 → 互联网络
- **训练路线** → 训练全景 → 3D并行 → Megatron/DeepSpeed → MoE → RLHF → Checkpoint
- **推理路线** → 推理引擎 → PagedAttention → 推理引擎对比 → 量化 → 推测解码 → 长上下文
- **RAG/Agent路线** → RAG全景 → 向量库/GraphRAG → Agent框架 → 工具调用/MCP
- **平台与运营** → 服务化 → 网关 → 可观测 → 成本/合规/安全 → 未来展望


## 延伸阅读

综合分析：[[synthesis/llm-infra-evolution-2022-2026]], [[synthesis/cloud-native-infrastructure-landscape]]

## 来源

- 大模型基础设施工程系列01：大模型基础设施全景（raw/sources/AI 人工智能/AI infra/大模型基础设施工程系列/）