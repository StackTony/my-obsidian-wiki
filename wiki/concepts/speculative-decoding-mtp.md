---
title: 推测解码与多Token预测
category: concepts
tags: [AI, LLM, 推理, 推测解码, MTP]
aliases: [Speculative Decoding, 推测解码, MTP, Medusa, EAGLE]
relationships:
  - target: "[[concepts/llm-inference-engine]]"
    type: extends
  - target: "[[concepts/paged-attention-continuous-batching]]"
    type: related_to
  - target: "[[concepts/llm-quantization-engineering]]"
    type: related_to
  - target: "[[concepts/gpu-computing-architecture]]"
    type: related_to
  - target: "[[concepts/moe-training-engineering]]"
    type: related_to
source_dir: AI 人工智能/AI infra/大模型基础设施工程系列
source_files: [【大模型基础设施工程】15：推测解码与 MTP.md]
summary: 推测解码让小模型(draft)生成K个候选token，大模型(target)单次前向验证——从decode 1token/step变为验证K tokens/step。EAGLE-3达3.5-6.5x加速；batch增大加速递减(batch=1:3.3x, batch=128:~1.0x)；输出分布数学等价无损
provenance:
  extracted: 0.75
  inferred: 0.20
  ambiguous: 0.05
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-02
---

# 推测解码与多Token预测

LLM decode是**内存瓶颈**：70B模型FP16约140GB权重，每个token必须从HBM读一遍，SM利用率仅5-10%。推测解码（Speculative Decoding）利用这个计算富余——让小模型生成K个候选token，大模型单次前向验证所有K个。从"1 token per step"变为"验证K tokens per step"。

## 核心观点

- **推测解码是数学等价（无损）的**：拒绝采样保证输出分布与直接target采样完全一致。这是生产可用性的关键前提。
- **草稿质量决定一切**：alpha（平均接受长度）是核心指标。alpha~1（草稿太差）→ 加速反而变慢（最常见生产坑）；alpha~3+ → 2-3x加速。
- **batch越大加速越小**：batch=1时计算近免费（3.3x）；batch=128时无收益（~1.0x）。推理服务化场景需要权衡。
- **EAGLE-3是2025开源SOTA**：特征级自回归+多层特征融合，3.5-6.5x加速（batch=1 chat场景）。
- **MTP是训练范式变革**：不仅加速推理，还提升主模型质量（Meta MTP代码任务+3% HumanEval）。但训练成本高（pretraining级别）。
- **PD分离+推测只在Decode节点生效**：Prefill节点不受影响。

## 经典推测解码机制

### 拒绝采样流程

1. **Draft模型q**自回归生成K个候选token x₁...x_K及概率分布
2. **Target模型p**单次前向处理[prefix, x₁, ..., x_K]，产出K+1个位置分布
3. **逐token验证**：对每个x_i，接受概率 = min(1, p_i(x_i) / q_i(x_i))
4. **拒绝时**：从残差分布norm(max(0, p_i - q_i))采样，本轮结束
5. **全部接受**：获得bonus token从p_{K+1}

**关键约束**：draft和target必须共享tokenizer/vocabulary。跨家族draft（Qwen起草Llama）基本不可能。

### 加速公式

```
speedup ≈ alpha × t_t / (K × t_d + t_t)
```

- alpha：平均接受长度（1到K+1）
- t_d：draft前向时间（~0.1×t_t）
- t_f：target前向时间

典型70B+7B：alpha~3, t_d/t_t~0.1 → speedup 2-3x。

## 方法演进

### Medusa（Together AI, 2023）

在target模型上加多个独立LM头，各自预测next-1/2/3/4 token。无独立draft模型。关键创新：**Tree Attention**——各头top-k组合成树结构，target用自定义attention mask一次验证所有路径。

- Vicuna-7B: 2.2x; Vicuna-33B: 2.1x; Medusa-2+联合训练: 2.8x
- 训练成本极低：几千数据样本即可收敛
- 缺点：独立头丢失token依赖链

### EAGLE系列（ICML 2024 → 2025）

| 版本 | 核心创新 | 加速 | 特点 |
|------|---------|------|------|
| **EAGLE-1** | 特征级自回归draft（单层Transformer） | 2.7-3.0x | 真正自回归，保留依赖 |
| **EAGLE-2** | +动态树构建（按期望接受率剪枝） | 3.0-3.5x | 接受率提升~20% |
| **EAGLE-3** | +多层特征融合（低/中/高层拼接） | 3.5-6.5x | 2025开源SOTA |

EAGLE用前一层hidden feature+embedding输入，输出next token的hidden feature，再通过共享LM头。真正自回归，不像Medusa的独立头。

### Multi-Token Prediction (MTP)

**Meta MTP**（ICML 2024）：训练时用n个并行头预测next-1到next-n token。不是推理加速技巧——是**训练范式变革**。
- 提升主模型质量（代码任务+3% HumanEval）
- 效果在7B+规模才显现
- 训练成本：pretraining级别

**DeepSeek-V3串联式MTP**：模块k接收位置t+k-1的hidden + 位置t+k的embedding，通过一个Transformer block，保持因果链。比Meta独立并行头更精确。接受率85-90%，decode ~1.8x加速。可推理时启用self-speculation，训练时丢弃回标准自回归。

### 其他方法

| 方法 | 特点 | 加速 |
|------|------|------|
| **Lookahead Decoding** | Jacobi迭代，无draft/无训练 | 1.5-2x |
| **CLLM** | Jacobi收敛作为训练目标，一步输出W个token | 2.4-3.4x |
| **LayerSkip** | 用target前半层做draft，后半验证 | alpha 1.5-2.0 |
| **Prompt Lookup** | n-gram匹配输入文本生成draft，零训练 | 代码/结构输出效果好 |

## 关键细节

### batch vs 加速（Llama-3 70B + EAGLE-2, A100 tp=4）

| batch | 加速 | tps |
|-------|------|-----|
| 1 | 3.3x | 22→72 |
| 4 | 2.6x | — |
| 16 | 1.8x | — |
| 32 | 1.4x | — |
| 64 | 1.1x | — |
| 128 | ~1.0x | 无收益 |

**原因**：batch增大时decode从内存瓶颈变为计算瓶颈，推测无法利用计算富余。

### 推测+量化

FP8/AWQ量化后decode带宽瓶颈减轻，推测收益下降。但draft可以更激进量化（INT4），总体1.5-2x收益保留。 ^[inferred]

**FP8 target + FP16 draft**：logits漂移导致接受率降5-10个百分点。 ^[inferred]

**Draft头未在target微调后重训练**：接受率降至~20%。 ^[inferred]

### 动态K调整

根据当前接受率动态调整候选token数K。~10%改进。sweet spot K=4-6；太小浪费机会，太大浪费计算。 ^[inferred]

### 引擎支持（2025-2026）

| 引擎 | 推测支持 |
|------|---------|
| vLLM (>=0.6) | Medusa/EAGLE/self-speculative |
| SGLang | EAGLE |
| TensorRT-LLM | Medusa/lookahead |
| TGI (HuggingFace) | `assistant_model`内置 |
| llama.cpp | draft model参数 |
| HuggingFace Transformers (>=4.36) | `assistant_model` |

### DeepSeek-V3 MoE + MTP协同

MoE decode仅激活37B参数，MTP进一步推吞吐——DeepSeek低成本API的关键因素之一。 ^[inferred]

## 未解问题

- 推测解码在online serving（高batch）场景下收益递减，如何与PD分离配合？
- MTP训练成本高昂（pretraining级别），何时值得投入？
- UALink/NVL576等新互联对推测的间接影响？

## 来源

- 【大模型基础设施工程】15 — 推测解码与MTP完整技术解析
- [[concepts/llm-inference-engine]] — decode内存瓶颈+Prefill/Decode二阶段
- [[concepts/paged-attention-continuous-batching]] — Continuous Batching调度是推测步骤的插入点