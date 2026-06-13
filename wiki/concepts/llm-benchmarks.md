---
title: LLM评测基准数据集
category: concepts
tags: [AI, LLM, 评测, 基准, Benchmark]
aliases: [LLM Benchmarks, 大模型评测基准, 评测数据集]
source_dir: AI 人工智能/Agent架构/评估系统
source_files: [大语言模型LLM的评测基准数据集（BenchMarks）汇总.md]
summary: LLM评测基准按六大能力分类：知识语言理解(MMLU/ARC/GLUE)、推理(GSM8K/DROP/BBH)、多轮对话(MT-bench)、抽取生成(MS-MARCO)、内容审核(TruthfulQA/HHH)、编程(HumanEval/MBPP)
provenance:
  extracted: 0.80
  inferred: 0.18
  ambiguous: 0.02
base_confidence: 0.70
lifecycle: draft
lifecycle_changed: 2026-06-12
tier: supporting
created: 2026-06-12
updated: 2026-06-13
relationships:
  - target: "[[concepts/evaluation-metrics]]"
    type: extends
  - target: "[[concepts/rag-engineering]]"
    type: related_to
  - target: "[[concepts/llm-observability]]"
    type: related_to
---

# LLM评测基准数据集

LLM评测基准(Benchmarks)按六大能力维度组织，每个维度有专门的数据集测量特定能力。选择基准时先确定评估维度，再在该维度中选择与场景匹配的数据集。

## 六大能力维度

| 维度 | 评估什么 | 核心基准 | 代表场景 |
|------|----------|----------|----------|
| **知识语言理解** | 世界知识广度+语言理解深度 | MMLU、ARC、GLUE/SuperGLUE | 通用问答、教育辅导 |
| **推理能力** | 逻辑推理+数学+反事实 | GSM8K、DROP、BBH、AGIEval | 数学解题、战略分析 |
| **多轮对话** | 连贯性+上下文维持 | MT-bench、QuAC | 聊天助手、教育对话 |
| **抽取生成** | 信息抽取+摘要+物理常识 | MS-MARCO、QMSum、PIQA | 搜索引擎、会议摘要 |
| **内容审核** | 安全性+真实性+道德对齐 | TruthfulQA、HHH、ToxiGen | 内容审核、安全评估 |
| **编程能力** | 代码生成+代码理解 | HumanEval、MBPP、CodeXGLUE | 代码助手、自动化编程 |

## 知识与语言理解

| 基准 | 全称 | 评估内容 | 规模 |
|------|------|----------|------|
| **MMLU** | Massive Multitask Language Understanding | 57学科的通用知识和推理 | 多项选择题 |
| **ARC** | AI2 Reasoning Challenge | 小学科学问题的逻辑推理 | Challenge/Easy两集 |
| **GLUE** | General Language Understanding Evaluation | 多任务语言理解整体能力 | 9个子任务 |
| **SuperGLUE** | GLUE高级版 | 更深层次的理解和推理 | 更难的子任务 |
| **Natural Questions** | Google搜索真实问题 | 从维基百科提取长短答案 | 真实Web问题 |
| **HellaSwag** | — | 段落续写=自然语言推理 | 上下文理解 |
| **TriviaQA** | — | 复杂文本中的情境阅读理解 | Wikipedia+Web |
| **WinoGrande** | Winograd Schema大规模版 | 微妙上下文消歧 | 44K问题 |

## 推理能力

| 基准 | 全称 | 评估内容 | 特色 |
|------|------|----------|------|
| **GSM8K** | Grade School Math 8K | 小学多步数学问题 | 8.5K问题，基本到中级运算 |
| **DROP** | Discrete Reasoning Over Paragraphs | 段落中的离散推理(加减排序) | 对抗性阅读理解 |
| **BBH** | Big-Bench Hard | BIG-Bench中最难的多步推理子集 | 推理能力上限测试 |
| **AGIEval** | — | GRE/GMAT/SAT/LSAT等标准化考试 | 人类认知能力对标 |
| **BoolQ** | — | 从不明确上下文推断是非 | 15K+真实Google问题 |

## 多轮对话

| 基准 | 评估内容 |
|------|----------|
| **MT-bench** | 聊天助手多轮连贯性和上下文相关性（LLM-as-Judge范式） |
| **QuAC** | 14K对话+100K问答对，模拟学生-教师互动 |

## 抽取与生成能力

| 基准 | 评估内容 |
|------|----------|
| **MS-MARCO** | 真实Web查询的阅读理解（搜索引擎质量核心基准） |
| **QMSum** | 基于查询的会议内容摘要提取 |
| **PIQA** | 物理交互常识推理（假设性场景+解决方案） |

## 内容审核与叙事控制

| 基准 | 评估内容 | 重要性 |
|------|----------|--------|
| **TruthfulQA** | LLM回答的真实性（容易产生错误信念的问题） | 防止模型模仿人类常见谬误 |
| **HHH** | Helpful/Honest/Harmless道德对齐 | Anthropic RLHF训练核心基准 |
| **ToxiGen** | 隐含仇恨言论检测（少数群体） | 内容审核核心 |

## 编程能力

| 基准 | 评估内容 |
|------|----------|
| **HumanEval** | 根据指令生成功能性代码（164个编程挑战） ^[inferred] |
| **MBPP** | 1000个基础Python编程问题 |
| **CodeXGLUE** | 代码理解+生成+补全+翻译全任务 |

## 选型指南

选择LLM评测基准时遵循**维度优先**原则：先确定评估维度（知识/推理/对话/安全/编程），再在该维度中选择与具体应用场景匹配的基准 ^[inferred]。

- **通用助手评估** → MMLU + GSM8K + MT-bench + TruthfulQA
- **代码助手评估** → HumanEval + MBPP + CodeXGLUE
- **RAG系统评估** → Natural Questions + MS-MARCO + RAGAS（见 [[entities/ragas-framework]]）
- **安全评估** → TruthfulQA + HHH + ToxiGen

## 与已有概念的连接

- [[concepts/evaluation-metrics]] 提供了评测的**底层指标体系**（精确率/召回率/F1），本页则是**具体数据集**的选择
- [[concepts/rag-engineering]] 的评估层使用 RAGAS 和 Natural Questions/MS-MARCO 等基准
- [[concepts/llm-observability]] 的语义质量维度同样依赖这些基准来验证模型能力

## 来源

- 大语言模型LLM的评测基准数据集（BenchMarks）汇总（raw/sources/AI 人工智能/Agent架构/评估系统/）