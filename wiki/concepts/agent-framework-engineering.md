---
title: Agent框架工程
category: concepts
tags: [AI, Agent, LangGraph, MCP, 工具调用]
summary: Agent工程的核心洞察：可靠Agent更像可观测状态机，而非自由聊天循环——工作流、状态、记忆、工具和协议是五大支柱
source_dir: AI 人工智能/AI infra/大模型基础设施工程系列
source_files: [【大模型基础设施工程】19：Agent 框架工程.md]
  # 跨目录补充
  # source_dir: AI 人工智能/AI Agent/Agent智能体
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
updated: 2026-06-29
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
  - target: "[[concepts/multi-agent-orchestration]]"
    type: extends
  - target: "[[entities/oh-my-opencode]]"
    type: related_to
  - target: "[[concepts/agent-system-architecture]]"
    type: extends
---

# Agent框架工程

Agent的核心挑战不是"让模型更聪明"，而是**让模型在结构化流程中可靠执行**。可靠Agent更像可观测状态机，而不是自由聊天循环。详见 [[concepts/agent-architecture-landscape|Agent架构全景]] 导航页。

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

### Skill vs Tool：方法论知识的注入

详见 [[concepts/agent-system-architecture|Agent系统架构设计]] 中的Skill系统部分。

关键洞察：**Tool定义"能做什么"（可执行操作），Skill定义"如何做好"（方法论知识）**——两者互补。用户无需编码，在workspace/skills/目录创建Markdown文件即可注入领域知识。Skill采用三层渐进式加载避免token耗尽。

### Sub-agent机制

详见 [[concepts/agent-system-architecture|Agent系统架构设计]] 中的Sub-agent部分。

关键洞察：Sub-agent是**完整的AgentLoop实例**而非简单工具调用——它拥有独立ToolRegistry（不含spawn和message）、临时messages、精简System Prompt。禁止spawn防止递归，禁止message必须通过主Agent转发。

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

## Multi-Agent协同编排

详见 [[concepts/multi-agent-orchestration]] 的编排设计模式提炼。

超越框架选择的层面，Multi-Agent编排遵循7个核心设计模式：
1. **角色分化与工具隔离** — 不同认知任务需要不同模型能力和工具权限
2. **主编排+子执行分层** — 编排者判断"让谁做"，而非"自己做得更好"
3. **双轨主Agent哲学** — 编排型（委派优先）vs 自主型（禁止询问），行为模式切换比参数微调更可靠 ^[inferred]
4. **证据驱动完成标准** — File edit→lsp_diagnostics clean、Build→exit code 0，NO EVIDENCE=NOT COMPLETE
5. **并发控制与防递归委派** — 三级粒度并发+禁止子agent委派新task
6. **completion_promise自动续跑** — 用户定义"完成"，双通道检测，Loop Engineering的具体实现 ^[inferred]
7. **AgentPromptMetadata自描述** — 开放-封闭原则，新agent自动融入编排

[[entities/oh-my-opencode|Oh My OpenCode]] 是这些设计模式的杰出实践案例。

## 延伸阅读

相关概念：[[concepts/harness-engineering]] — Harness Engineering（驾驭工程）：Agent=Model+Harness，四大支柱+六大共识+三阶段路线图——Agent框架工程的上层方法论
相关概念：[[concepts/agent-system-architecture]] — Agent系统架构设计：执行循环+消息总线两种架构视角+Skill/Memory/Sub-agent机制细节
相关概念：[[concepts/data-flywheel]] — 数据飞轮：Agent决策的数据基础正反馈循环
相关概念：[[concepts/multi-agent-framework-comparison]] — Multi-Agent框架终极对比
相关概念：[[concepts/multi-agent-orchestration]] — Multi-Agent协同编排设计模式
相关概念：[[concepts/agent-security]] — Agent安全与对抗
相关实体：[[entities/graphify-gitnexus]]
相关实体：[[entities/oh-my-opencode]] — Multi-Agent编排实践案例

## 来源

- 大模型基础设施工程系列19：Agent框架工程（raw/sources/AI 人工智能/AI infra/大模型基础设施工程系列/）