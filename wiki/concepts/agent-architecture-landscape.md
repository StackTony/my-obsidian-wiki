---
title: Agent架构全景
category: concepts
tags: [AI, Agent, RAG, 知识图谱, 全景图]
aliases: [Agent架构全景, Agent Landscape, Agent架构导航]
summary: Agent架构领域导航枢纽：7个子领域的树状拓扑、4个核心矛盾、子领域间连接关系、与LLM基础设施的边界划分
source_dir: AI 人工智能/Agent架构
source_files: []
provenance:
  extracted: 0.15
  inferred: 0.80
  ambiguous: 0.05
base_confidence: 0.60
lifecycle: draft
lifecycle_changed: 2026-06-13
tier: core
created: 2026-06-13
updated: 2026-06-13
relationships:
  - target: "[[concepts/llm-infra-landscape]]"
    type: related_to
  - target: "[[concepts/agent-framework-engineering]]"
    type: extends
  - target: "[[concepts/rag-engineering]]"
    type: related_to
  - target: "[[concepts/graphrag-engineering]]"
    type: related_to
  - target: "[[concepts/evaluation-metrics]]"
    type: related_to
  - target: "[[concepts/agent-security]]"
    type: related_to
  - target: "[[concepts/data-flywheel]]"
    type: related_to
---

# Agent架构全景

Agent架构是LLM基础设施之上的**应用层工程领域**——从"模型能生成文本"到"系统能完成任务"。本页是Agent架构7个子领域的导航枢纽，帮助读者快速定位知识并理解子领域间的连接关系。

## 树状导航图

```
Agent架构
├── RAG（检索增强生成）
│   ├── 传统RAG
│   │   ├── [[concepts/rag-engineering|RAG工程全景]]          — 完整流水线+5种高级范式+落地路径
│   │   ├── [[concepts/rag-chunking-strategies|分块策略]]      — 21种方法从基础到语义驱动
│   │   ├── [[concepts/rag-storage-technology|存储技术]]       — 四层架构：文件→元数据→切片→向量
│   │   └── [[concepts/rag-tools-landscape|核心工具全景]]     — 7类解析+Embedding+向量库+重排序
│   └── 高级RAG
│       └── [[concepts/graphrag-engineering|GraphRAG工程]]    — 知识图谱解决全局型问题
├── Agent框架
│   ├── [[concepts/agent-framework-engineering|Agent框架工程]] — 五大支柱+可靠Agent=可观测状态机
│   ├── [[concepts/tool-calling-mcp|工具调用与MCP]]           — JSON Schema+MCP统一工具生态
│   └── [[concepts/multi-agent-framework-comparison|Multi-Agent对比]] — LangGraph/CrewAI/AutoGen/AgentX
├── 评估系统
│   ├── [[concepts/evaluation-metrics|分类评估指标]]          — 混淆矩阵→准确率/精确率/召回率/F1
│   └── [[concepts/llm-benchmarks|LLM评测基准]]              — 六大维度20+基准数据集
├── 安全
│   └── [[concepts/agent-security|Agent安全与对抗]]           — 4类绕过手法+纵深防御
├── 知识图谱
│   └── [[entities/graphify-gitnexus|Graphify vs GitNexus]]  — 认知整合 vs 工程执行
├── 数据飞轮
│   └── [[concepts/data-flywheel|数据飞轮]]                  — 数据与业务正反馈循环
└── LangChain生态
    ├── [[entities/langchain-framework|LangChain框架]]        — Runnable+LCEL统一可执行单元
    ├── [[entities/langgraph-framework|LangGraph框架]]        — 有向图+状态持久化+循环支持
    └── [[entities/ragas-framework|RAGAS评估框架]]            — RAG量化评估4核心指标
```

## 4个核心矛盾

| 矛盾 | 表现 | 代表页面 |
|------|------|----------|
| **可靠性 vs 自由度** | 自由聊天循环灵活但不稳定，结构化状态图可靠但受限 | [[concepts/agent-framework-engineering]] vs [[concepts/multi-agent-framework-comparison]] |
| **全局 vs 局部** | 传统RAG擅长局部检索，全局型/多跳型需要知识图谱 | [[concepts/rag-engineering]] vs [[concepts/graphrag-engineering]] |
| **开放 vs 安全** | Agent需要开放工具调用能力，但越开放越容易被攻击 | [[concepts/tool-calling-mcp]] vs [[concepts/agent-security]] |
| **飞轮 vs 冷启动** | 数据飞轮需要数据积累才能转动，但初期数据不足飞轮无法启动 | [[concepts/data-flywheel]] |

## 子领域间连接

```
Agent ←→ RAG          Agent需要RAG获取外部知识，RAG是Agent的认知基础
Agent ←→ 知识图谱      知识图谱为Agent提供结构化世界模型，GraphRAG是两者的交汇点
Agent ←→ 评估          评估量化Agent/RAG效果，RAGAS连接了评估与RAG
Agent ←→ 数据飞轮      飞轮为Agent/RAG提供持续数据供给，Agent产出反过来推动飞轮
Agent ←→ 安全          工具调用越开放安全风险越高，MCP协议试图划定安全边界
```

## 与LLM基础设施的边界

| 维度 | LLM基础设施 | Agent架构 |
|------|-------------|-----------|
| **关注层级** | 硬件→系统软件→框架→训练→推理→服务化 | 应用层：检索→编排→工具→记忆→评估 |
| **核心问题** | 算力、显存、通信、吞吐、延迟、SLO | 可靠性、知识获取、工具调用、安全、数据闭环 |
| **代表页面** | [[concepts/llm-infra-landscape]] | 本页 |
| **交汇点** | 推理引擎是Agent的运行基础；[[concepts/llm-observability]]是Agent可观测的前置条件 | |

边界判断规则：如果一个页面的核心问题是"GPU/显存/并行/推理优化"，它属于LLM基础设施；如果核心问题是"Agent如何可靠执行/如何检索知识/如何安全调用工具"，它属于Agent架构。

## 推荐阅读路径

- **RAG入门** → RAG工程全景 → 分块策略 → 存储技术 → 工具全景 → GraphRAG
- **Agent入门** → Agent框架工程 → 工具调用/MCP → Multi-Agent对比 → Agent安全
- **评估路线** → 分类评估指标 → LLM评测基准 → RAGAS框架
- **闭环路线** → 数据飞轮 → RAG工程（数据侧） → Agent框架（应用侧）
