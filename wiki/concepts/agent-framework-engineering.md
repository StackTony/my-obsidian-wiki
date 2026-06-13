---
title: Agent框架工程
category: concepts
tags: [AI, Agent, LangGraph, MCP, 工具调用]
summary: Agent工程的核心洞察：可靠Agent更像可观测状态机，而非自由聊天循环——工作流、状态、记忆、工具和协议是五大支柱
source_dir: AI 人工智能/AI infra/大模型基础设施工程系列
source_files: [【大模型基础设施工程】19：Agent 框架工程.md]
  # 跨目录补充
  # source_dir: AI 人工智能/Agent架构/Agent智能体
  # source_files: [Multi-Agent 框架终极对比：LangGraph、CrewAI、AutoGen.md]
provenance:
  extracted: 0.60
  inferred: 0.35
  ambiguous: 0.05
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: core
created: 2026-06-02
updated: 2026-06-13
relationships:
  - target: "[[concepts/llm-infra-landscape]]"
    type: derived_from
  - target: "[[concepts/tool-calling-mcp]]"
    type: uses
  - target: "[[concepts/rag-engineering]]"
    type: uses
  - target: "[[entities/langchain-framework]]"
    type: uses
  - target: "[[entities/langgraph-framework]]"
    type: uses
  - target: "[[concepts/multi-agent-framework-comparison]]"
    type: extends
---

# Agent框架工程

Agent的核心挑战不是"让模型更聪明"，而是**让模型在结构化流程中可靠执行**。可靠Agent更像可观测状态机，而不是自由聊天循环。

## Agent的五大支柱

| 支柱 | 核心问题 | 代表方案 |
|------|----------|----------|
| **工作流（Workflow）** | Agent如何决定下一步做什么？ | LangGraph（图驱动）、AutoGen（对话驱动） |
| **状态（State）** | Agent记住什么、状态如何持久化？ | LangGraph Checkpoint、Redis、数据库 |
| **记忆（Memory）** | 短期（对话内）和长期（跨对话）信息如何管理？ | LangGraph Store、向量库 |
| **工具（Tools）** | Agent如何调用外部能力？ | Function Call、MCP协议 |
| **协议（Protocol）** | 工具调用的接口标准是什么？ | OpenAI Function Call格式、Anthropic MCP |

## Agent架构演进

### ReAct模式
- Reasoning（推理）+ Acting（行动）循环
- 思考→行动→观察→思考→行动→...
- 局限：每步调用LLM，成本高、速度慢

### 工作流模式（LangGraph为代表）
- 将Agent行为建模为**有向图**：节点=动作、边=条件转移
- 支持循环（反思、重试）、分支（条件路由）、并行（多工具同时调用）
- **状态驱动**：每个节点的输入输出由全局状态管理

### 对比
| 维度 | ReAct | LangGraph工作流 |
|------|-------|-----------------|
| 执行模式 | LLM自由决策 | 结构化图+条件边 |
| 可观测性 | 黑盒，难以追踪 | 每步状态可检查 |
| 循环支持 | 自然支持（LLM决策） | 图中显式循环边 |
| 可靠性 | 低（LLM可能走偏） | 高（结构约束） |
| 调试难度 | 高 | 低（每步可检查状态） |

## Agent记忆架构

详见 [[entities/langgraph-framework]] 中的Memory部分。

关键区分：
- **短期记忆**：线程内，通过检查点持久化，包括对话历史和检索结果
- **长期记忆**：跨线程共享，通过Store管理，包括用户偏好、历史摘要、知识积累

## Agent框架对比

| 框架 | 定位 | 特点 |
|------|------|------|
| **LangGraph** | 工作流编排 | 图驱动、状态持久化、支持循环 |
| **AutoGen** | 多Agent对话 | Agent间对话协作、支持人参与 |
| **Coze** | 低代码Agent平台 | 可视化编排、插件生态、商业化 |
| **CrewAI** | 角色化多Agent | 定义角色和任务，Agent分工协作 |


## Multi-Agent框架对比

详见 [[concepts/multi-agent-framework-comparison]] 的完整对比。

四大框架的核心差异：
- **LangGraph**：状态图驱动，可靠性最高，适合生产环境
- **CrewAI**：角色分工驱动，上手最快，适合快速验证
- **AutoGen**：对话驱动，最灵活，适合研究实验
- **AgentX**：企业工作流驱动，安全性最高

生产环境最常用LangGraph——可靠性+可调试性是第一优先。 ^[inferred]

## 延伸阅读

相关概念：[[concepts/data-flywheel]] — 数据飞轮：Agent决策的数据基础正反馈循环
相关概念：[[concepts/multi-agent-framework-comparison]] — Multi-Agent框架终极对比
相关概念：[[concepts/agent-security]] — Agent安全与对抗
相关实体：[[entities/graphify-gitnexus]]

## 来源

- 大模型基础设施工程系列19：Agent框架工程（raw/sources/AI 人工智能/AI infra/大模型基础设施工程系列/）