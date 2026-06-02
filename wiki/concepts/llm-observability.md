---
title: LLM可观测性
category: concepts
tags: [AI, LLM, 可观测, Langfuse, OpenTelemetry]
summary: LLM系统必须同时观测性能、语义质量和账单——传统Metrics/Logs/Traces扩展到token、成本、幻觉和链路质量
source_dir: AI 人工智能/AI infra/大模型基础设施工程系列
source_files: [【大模型基础设施工程】23：LLM 可观测性.md]
provenance:
  extracted: 0.60
  inferred: 0.35
  ambiguous: 0.05
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-02
relationships:
  - target: "[[concepts/llm-gateway]]"
    type: related_to
  - target: "[[concepts/llm-serving-infrastructure]]"
    type: related_to
---

# LLM可观测性

LLM系统的可观测性不只是"监控GPU利用率"——它必须同时观测**性能指标、语义质量和运营成本**三个维度。

## 三个可观测维度

| 维度 | 指标 | 工具 |
|------|------|------|
| **性能** | TTFT、TPOT、吞吐、GPU利用率 | Prometheus、Grafana |
| **语义质量** | 幻觉率、引用准确率、答案相关性 | RAGAS、人工评测 |
| **成本** | token消耗、模型调用费用、GPU卡时 | Langfuse、OpenLLMetry |

## 核心观测指标

| 指标 | 定义 | 采集方式 |
|------|------|----------|
| **TTFT** | 用户请求→首token时间 | 框架内置 |
| **TPOT** | 每个后续token延迟 | 框架内置 |
| **Token消耗** | 输入+输出token数 | API header |
| **成本** | 每次请求的美元费用 | 按供应商计价计算 |
| **幻觉率** | 生成内容与检索事实不符的比例 | RAGAS Faithfulness |
| **链路追踪** | 请求从入口→检索→生成→返回的完整路径 | OpenTelemetry |

## 可观测工具

### Langfuse
- LLM专用可观测平台
- 自动追踪请求链路（Prompt→Retriever→LLM→Output）
- Token计费追踪、成本归属
- 幻觉评测、答案质量评估
- 适合：RAG/Agent应用的深度可观测

### LangSmith
- LangChain生态的可观测+评测平台
- 与LangChain/LangGraph深度集成
- Trace、Eval、Dataset管理一体化
- 适合：LangChain生态用户

### OpenLLMetry（OpenTelemetry GenAI扩展）
- 在OpenTelemetry标准上扩展LLM专用span
- 标准化的token、成本、延迟追踪
- 与现有Prometheus/Grafana生态无缝集成
- 适合：已有可观测基础设施的团队

## 工程要点

- **成本是LLM可观测的独特维度**：传统Web服务没有"按token计费"，LLM服务必须追踪每美元的价值 ^[inferred]
- **语义质量需要评测流水线**：不能只靠人工，需要自动化评测框架持续检测幻觉和退化 ^[inferred]
- **链路追踪是RAG/Agent可观测的基础**：一次请求可能跨多步检索和多轮LLM调用，完整链路是排查问题的关键 ^[inferred]

## 来源

- 大模型基础设施工程系列23：LLM可观测性（raw/sources/AI 人工智能/AI infra/大模型基础设施工程系列/）