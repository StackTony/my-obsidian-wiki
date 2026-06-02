---
title: LLM训练流水线
category: concepts
tags: [AI, LLM, 训练, Pre-train, SFT, RLHF]
summary: 现代LLM的四阶段训练栈：预训练→中训→SFT→对齐，训练不是一次脚本而是数据/目标函数/优化器/评测组成的流水线
source_dir: AI 人工智能/AI infra/大模型基础设施工程系列
source_files: [【大模型基础设施工程】05：训练全景：Pre-train、SFT、RLHF、DPO、蒸馏.md]
provenance:
  extracted: 0.65
  inferred: 0.30
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
  - target: "[[concepts/llm-parallelism-strategies]]"
    type: uses
  - target: "[[concepts/moe-training-engineering]]"
    type: extends
  - target: "[[concepts/rlhf-alignment-pipeline]]"
    type: extends
---

# LLM训练流水线

训练不是一次脚本运行，而是数据、目标函数、优化器、评测和发布组成的流水线。现代LLM训练通常分为四个阶段。

## 四阶段训练栈

| 阶段 | 目标 | 数据 | 关键技术 |
|------|------|------|----------|
| **Pre-train** | 学习语言和世界知识 | 海量无标注文本（TB级） | 3D并行、ZeRO、混合精度 |
| **Mid-train（中训）** | 领域知识注入 | 领域相关文本 | 持续训练、数据配比优化 |
| **SFT（监督微调）** | 学会对话格式 | 人工标注的问答数据 | LoRA/QLoRA、Full Fine-tune |
| **Alignment（对齐）** | 安全、有用、可控 | 人类偏好数据 | RLHF、DPO、GRPO |

## Pre-train阶段

- **数据**：通常1-15T tokens，涵盖Web、书籍、代码、科学论文
- **Tokenizer**：BPE变体（GPT用byte-level BPE、Llama用SentencePiece）
- **优化器**：AdamW + Cosine decay + Warmup
- **精度**：BF16混合精度训练（FP32 master weight + BF16 activation）
- **Scaling Law**：Chinchilla论文建议训练token数≈模型参数×20，但实际往往超训（数据质量>数据量） ^[inferred]
- **成本**：70B模型约3-6M美元，405B模型约60M美元（DeepSeek-V3通过工程创新压到6M美元）

## SFT阶段

- 从预训练模型出发，用问答数据微调
- **数据质量>>数量**：几万到几十万高质量问答就够了 ^[inferred]
- **方法**：Full Fine-tune（数据充足）、LoRA/QLoRA（资源有限）
- **目标**：让模型学会"对话格式"——用户提问→模型回答

## 对齐阶段（RLHF/DPO/GRPO）

详见 [[concepts/rlhf-alignment-pipeline]]

## 蒸馏

- 用大模型（教师）生成高质量数据，训练小模型（学生）
- **Logit蒸馏**：学生学习教师的输出概率分布，不只是硬标签
- **特征蒸馏**：学生学习教师的中间层表示
- DeepSeek-V4的专家蒸馏：大专家→小专家，保持能力但减少激活参数 ^[inferred]

## 工程要点

- **数据是第一生产力**：数据质量、配比、清洗流程直接影响模型能力，远比训练技巧重要 ^[inferred]
- **评测贯穿全程**：每个阶段都需要评测（通用能力、领域能力、对话能力、安全性），不能等到最后才测
- **Checkpoint管理**：训练checkpoint动辄TB级，保存和恢复都需要专门的工程方案 ^[inferred]

## 来源

- 大模型基础设施工程系列05：训练全景（raw/sources/AI 人工智能/AI infra/大模型基础设施工程系列/）