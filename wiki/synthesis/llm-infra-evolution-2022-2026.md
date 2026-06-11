---
title: 大模型基础设施2022-2026演进分析
category: synthesis
tags: [AI, LLM, 基础设施, 演进, DeepSeek]
summary: 从ChatGPT到DeepSeek-V4的四年演进：推理范式确立、开源运动爆发、成本革命——工程创新而非硬件堆量成为新范式
source_dir: AI 人工智能/AI infra/大模型基础设施工程系列
source_files: [大模型基础设施工程.md, 【大模型基础设施工程】01：大模型基础设施全景 —— 训练、推理、RAG、Agent、观测.md, 【大模型基础设施工程】26：特别篇 DeepSeek-V4 与国产芯片：从备份路线到主路径.md, 【大模型基础设施工程】27：特别篇 DeepSeek-V4 的极致性价比从哪来.md]
provenance:
  extracted: 0.55
  inferred: 0.40
  ambiguous: 0.05
base_confidence: 0.80
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: core
created: 2026-06-02
updated: 2026-06-11
relationships:
  - target: "[[concepts/llm-infra-landscape]]"
    type: derived_from
  - target: "[[concepts/llm-inference-engine]]"
    type: derived_from
  - target: "[[concepts/llm-training-pipeline]]"
    type: derived_from
---

# 大模型基础设施2022-2026演进分析

四年时间里，LLM基础设施从"单机跑一个7B"进化到"万卡训练万亿参数、百万QPS推理、RAG与Agent工业化"。这不是渐进式优化，而是四轮范式转移。

## 四轮范式转移

### 第一轮：推理范式确立（2022.11 - ChatGPT）
- 工程意义：LLM推理SaaS成为全球级运营模式
- 催生技术：流式返回、速率限制、多租户、模型路由
- 确立认知：**LLM不是传统Web服务，是新工作负载**

### 第二轮：开源运动爆发（2023.2 - LLaMA）
- 工程意义：模型分发与微调的工程栈确立
- 催生技术：llama.cpp（消费级推理）、LoRA/QLoRA（单卡微调）、HuggingFace（模型分发中心）
- 确立认知：**开源模型可以逼近闭源水平**

### 第三轮：推理引擎革命（2023.6 - [[entities/vllm-sglang-tensorrt|推理引擎对比]]/[[concepts/paged-attention-continuous-batching|PagedAttention]]）
- 工程意义：推理引擎的现代范式确立
- 催生技术：[[concepts/paged-attention-continuous-batching|PagedAttention]]（消除碎片）、Continuous Batching（吞吐2-4倍）、KV cache按页管理
- 确立认知：**推理优化首先是资源调度问题，而非算法优化**

### 第四轮：成本革命（2024末-2026 - DeepSeek-V3/V4）
- 工程意义：通过工程创新而非硬件堆量降低10倍成本
- 催生技术：MLA（KV压缩数量级级）、细粒度[[concepts/moe-training-engineering|MoE训练工程]]+共享专家、[[concepts/llm-quantization-engineering|FP8全流程训练]]、DualPipe[[concepts/llm-parallelism-strategies|并行]]
- 确立认知：**工程密度 > 硬件堆量**

## 跨领域连接

### 训练→推理的工程差异

| 维度 | 训练 | 推理 |
|------|------|------|
| 算术强度 | 高（矩阵乘密集） | 低（权重+KV逐token读） |
| 瓶颈 | 计算MFU | HBM带宽利用率 |
| 状态 | TB级checkpoint | KV缓存动态增长 |
| 扩展策略 | [[concepts/llm-parallelism-strategies|3D并行]]+ZeRO | Continuous Batching+PD分离 |
| 容错 | 必须容错（故障常态） | 请求级容错（单请求重试） |

训练和推理不能共享调参逻辑——同一个GPU上，Prefill和Decode的性能特征完全不同。 ^[inferred]

### GPU硬件→推理策略→成本曲线

[[concepts/gpu-computing-architecture|GPU计算架构]]决定了推理优化空间：
- HBM带宽限制Decode吞吐 → [[concepts/paged-attention-continuous-batching|PagedAttention]]管理碎片、量化压缩KV
- Tensor Core加速Prefill → FlashAttention减少内存、Chunked Prefill混合调度
- NVLink带宽限制TP通信 → TP放节点内、PD分离把Prefill和Decode分开

每一层硬件约束都在反向塑造上层策略。 ^[inferred]

### RAG→Agent→服务化的递进关系

- **RAG**：让LLM能查外部知识 → 但流水线僵化
- **Agent**：让LLM能自主决定何时检索 → 但需要可靠编排
- **服务化**：让LLM服务可治理 → 网关+可观测+成本管控

这三者不是替代关系，而是递进叠加：RAG打底、Agent增强、服务化保障运营。 ^[inferred]

## DeepSeek-V4：工程密度的极致案例

DeepSeek-V4展示了"工程创新降低10倍成本"的完整路径：
- **MLA**：KV缓存压缩一个数量级 → 推理显存瓶颈解绑
- **[[concepts/moe-training-engineering|MoE训练工程]]+共享专家**：细粒度专家+1-2个共享专家 → 激活比极低但能力不降
- **[[concepts/llm-quantization-engineering|FP8训练]]**：全流程BF16→FP8 → 训练吞吐翻倍、显存减半
- **DualPipe**：PP+EP[[concepts/llm-parallelism-strategies|并行]]通信重叠 → 万卡利用率更高
- **磁盘级KV cache**：冷KV offload到NVMe → 长上下文推理成本可控 ^[inferred]
- **FP4 QAT**：量化感知训练到4bit → 推理成本再降
- **专家蒸馏**：大专家→小专家 → 保持能力但减少激活参数

## 来源

- 大模型基础设施工程目录页（raw/sources/AI 人工智能/AI infra/大模型基础设施工程系列/）
- 大模型基础设施工程01：全景
- 大模型基础设施工程26：DeepSeek-V4与国产芯片
- 大模型基础设施工程27：DeepSeek-V4极致性价比