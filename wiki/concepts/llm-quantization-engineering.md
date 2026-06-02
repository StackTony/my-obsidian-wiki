---
title: LLM量化工程
category: concepts
tags: [AI, LLM, 量化, FP8, AWQ, GPTQ]
summary: LLM量化本质是在精度、指令能力和服务成本之间交易——从FP16到FP8/INT8/FP4，每一级量化都是硬件能力和精度的权衡
source_dir: AI 人工智能/AI infra/大模型基础设施工程系列
source_files: [【大模型基础设施工程】14：量化工程 —— INT8  -  FP8  -  FP4  -  AWQ  -  GPTQ.md]
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
  - target: "[[concepts/llm-inference-engine]]"
    type: uses
  - target: "[[entities/vllm-sglang-tensorrt]]"
    type: uses
  - target: "[[concepts/gpu-computing-architecture]]"
    type: uses
---

# LLM量化工程

量化不是"精度损失换速度提升"这么简单。每种量化方案背后是**硬件指令能力、精度容忍度和服务成本**的三方博弈。

## 数据类型演进

| 类型 | 位宽 | 范围 | 精度 | 硬件支持 | 用途 |
|------|------|------|------|----------|------|
| FP32 | 32bit | ±3.4e38 | 最高 | 所有GPU | 训练master weight |
| BF16 | 16bit | ±3.4e38 | 低（7位尾数） | A100/H100 | 训练激活、推理权重 |
| FP16 | 16bit | ±6.5e4 | 中（10位尾数） | V100/A100 | 训练激活（需loss scaling） |
| FP8 (E4M3/E5M2) | 8bit | E4M3:±448/E5M2:±57344 | 极低 | H100/昇腾910B | 训练和推理权重 |
| INT8 | 8bit | -128~127 | 整数 | 所有GPU（Tensor Core） | 推理权重+KV |
| FP4 | 4bit | 极窄 | 极极低 | 未来GPU | 推理权重（实验性） |

## PTQ vs QAT

| 方法 | 描述 | 优势 | 劣势 |
|------|------|------|------|
| **PTQ（后训练量化）** | 训练完成后直接量化 | 无需重新训练、快速 | 精度可能下降 |
| **QAT（量化感知训练）** | 训练时模拟量化误差 | 精度更好 | 需要重新训练 |

## 主要量化方案

### FP8量化
- H100原生支持FP8 Tensor Core（1979 TFLOPS）
- FP8训练已由DeepSeek-V3工程化落地：全流程BF16→FP8混合训练 ^[inferred]
- E4M3用于前向权重和激活，E5M2用于反向梯度 ^[inferred]

### INT8量化（W8A8/W8A16）
- W8A8：权重INT8 + 激活INT8 → 最高加速
- W8A16：权重INT8 + 激活FP16 → 精度更好
- 量化校准：用校准数据集统计激活范围，确定缩放因子

### AWQ（Activation-aware Weight Quantization）
- 核心洞察：不是所有权重同等重要——保护"激活显著通道"对应的权重
- 按激活幅度缩放权重分组，再量化
- 在4bit量化下保持接近FP16精度 ^[inferred]

### GPTQ（GPT Quantization）
- 基于近似二阶信息（Hessian）的逐层量化
- 量化每列权重时补偿对后续列的影响
- 适合大模型（>70B）的INT4/INT3量化
- 需要校准数据集，量化时间较长 ^[inferred]

### KV Cache量化
- KV缓存是长上下文推理的显存瓶颈
- FP8 KV Cache：精度损失可控，显存节省一半 ^[inferred]
- INT4/INT8 KV Cache：更激进，适合吞吐优先场景

## 工程要点

- **量化不是越低越好**：FP8→INT8损失小、FP4→INT4损失大，选择要看场景容忍度 ^[inferred]
- **硬件是硬约束**：FP8只有H100+才有Tensor Core加速，INT4在大部分GPU上没有专用指令 ^[inferred]
- **校准数据集很重要**：PTQ的效果取决于校准数据的分布代表性 ^[inferred]

## 来源

- 大模型基础设施工程系列14：量化工程（raw/sources/AI 人工智能/AI infra/大模型基础设施工程系列/）