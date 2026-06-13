---
title: RAGAS评估框架
category: entities
tags: [AI, RAG, 评估, RAGAS, 量化评估]
aliases: [RAGAS, Retrieval Augmented Generation Assessment]
source_dir: AI 人工智能/Agent架构/评估系统
source_files: [RAGAS 评估框架.md]
summary: RAGAS是RAG/LLM应用的自动化量化评估框架，核心4指标：Context Precision/Recall检索层+Faithfulness/Answer Relevancy生成层，把"感觉对"变成"数据证明对"
provenance:
  extracted: 0.75
  inferred: 0.22
  ambiguous: 0.03
base_confidence: 0.65
lifecycle: draft
lifecycle_changed: 2026-06-12
tier: supporting
created: 2026-06-12
updated: 2026-06-13
relationships:
  - target: "[[concepts/evaluation-metrics]]"
    type: implements
  - target: "[[concepts/rag-engineering]]"
    type: uses
  - target: "[[entities/langchain-framework]]"
    type: uses
---

# RAGAS评估框架

RAGAS（Retrieval Augmented Generation Assessment）是VibrantLabsAI开源的RAG/LLM应用评估框架（Apache 2.0），核心解决**RAG好坏靠主观感觉、没有统一量化指标、迭代没数据闭环**的问题。口号：**把"感觉对"变成"数据证明对"**。

> 注：早期仓库名为 `explodinggradients/ragas`，后迁移到 `vibrantlabsai/ragas`，是同一个项目。

## 四个核心指标

RAGAS把评估分成**检索质量**和**生成质量**两大块：

### 检索层指标

| 指标 | 含义 | 对应概念 |
|------|------|----------|
| **Context Precision** | 检索出来的片段中，有多少是真正相关的 | 对应 [[concepts/evaluation-metrics]] 中的精确率思想 |
| **Context Recall** | 所有相关片段中，有多少被成功检索到 | 对应 [[concepts/evaluation-metrics]] 中的召回率思想 |

### 生成层指标

| 指标 | 含义 | 核心作用 |
|------|------|----------|
| **Faithfulness** | 回答中的事实必须全部来自检索上下文，无幻觉 | 防止Hallucination |
| **Answer Relevancy** | 回答直接、完整地解决用户问题，不跑题不冗余 | 防止偏题 |

另有20+扩展指标：Answer Correctness、Completeness、AspectCritic（自定义维度）等。

## 核心功能

### 一键评估（5行代码）

```python
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy

result = evaluate(
    dataset=my_rag_dataset,
    metrics=[faithfulness, answer_relevancy]
)
print(result)  # 输出各指标分数（0~1）
```

### 自动生成测试集

- **输入**：一堆文档（PDF/MD/TXT）
- **输出**：自动生成**问题+答案+上下文**的测试样本
- **支持**：事实、推理、对比类问题

### 框架集成

- 支持 [[entities/langchain-framework]]、LlamaIndex、Haystack等主流RAG框架
- 支持OpenAI、Anthropic、本地部署LLM（如Llama 2）

### 实验对比与可视化

每次改动（换Embedding、换切块策略、换Prompt）都跑一次评估，**指标自动对比**，直观看到"改坏了还是改好了"。

## RAGAS vs 传统评估

| 方面 | BLEU/ROUGE | RAGAS |
|------|------------|-------|
| **评估层面** | 文本表面相似度 | 语义级评估 |
| **幻觉检测** | ❌ 不理解语义，无法检测 | ✅ 用LLM判断事实是否来自上下文 |
| **适用场景** | 机器翻译、摘要评价 | RAG系统全链路评估 |

一句话：传统基准只看"表面像不像"，RAGAS看"事实对不对、回答好不好"。 ^[inferred]

## 与已有概念的连接

- [[concepts/evaluation-metrics]] — RAGAS的四个核心指标是精确率/召回率思想在RAG领域的具体实现
- [[concepts/rag-engineering]] — RAGAS是RAG工程全景中"评估层"的核心工具
- [[concepts/llm-observability]] — RAGAS指标可以作为可观测性的语义质量维度

## 来源

- RAGAS 评估框架（raw/sources/AI 人工智能/Agent架构/评估系统/）
- GitHub: https://github.com/vibrantlabsai/ragas