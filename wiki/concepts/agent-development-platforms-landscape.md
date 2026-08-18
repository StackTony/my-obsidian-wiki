---
title: Agent开发平台全景图（10+主流平台）
category: concepts
tags: [AI, Agent, 平台, 全景图, 开源]
aliases: [Agent平台全景, Agent开发平台, GitHub Agent平台]
summary: Agent开发平台5分类：自主执行(AutoGPT)+可视化编排(Dify)+通用框架(LangChain)+多Agent协作(MetaGPT/CrewAI)+有状态Agent(Letta)，含选型决策树
source_dir: AI 人工智能/AI Agent/Multi-Agent协同
source_files: [GitHub 上 10 个令人惊艳的 Agent 开发平台.md, 多 Agent 协作 github项目示例.md]
provenance:
  extracted: 0.55
  inferred: 0.40
  ambiguous: 0.05
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-08-03
tier: supporting
created: 2026-08-03
updated: 2026-08-03
relationships:
  - target: "[[concepts/agent-architecture-landscape]]"
    type: related_to
  - target: "[[concepts/multi-agent-framework-comparison]]"
    type: extends
  - target: "[[concepts/agent-framework-engineering]]"
    type: related_to
  - target: "[[entities/langchain-framework]]"
    type: uses
  - target: "[[entities/langgraph-framework]]"
    type: uses
---

# Agent开发平台全景图（10+主流平台）

Agent开发平台从单Agent自主执行到多Agent协作形成完整光谱。本文按平台定位分类，提供选型参考。

## 5大平台分类

| 分类 | 代表平台 | 核心特征 | 适用场景 |
|------|----------|----------|----------|
| **自主任务执行** | AutoGPT、SuperAGI | 大目标自动拆解为子任务，思考-计划-行动循环 | 自主智能体研究、长期运行Agent |
| **可视化编排平台** | Dify、Flowise | 低代码/无代码UI拖拽编排 | 快速原型、非技术用户、企业知识库 |
| **通用LLM框架** | LangChain | 模块化组件（Chain/Agent/Memory），事实标准 | 复杂逻辑稳健地基 |
| **多Agent协作框架** | MetaGPT、AutoGen、CrewAI、ChatDev | 角色分工+协作流程 | 多智能体协作研究/生产 |
| **有状态Agent框架** | Letta | 持久化长期记忆，大模型即操作系统 | 伴侣型应用、长期记忆Agent |

## 自主任务执行平台

### AutoGPT（18万+ Star）

**Agent领域鼻祖级项目**——能够自主地将一个大目标拆解为子任务，并利用互联网搜索、本地文件等操作一步步实现目标。

**核心机制**：**思考-计划-行动**循环
1. 模型评估当前状态
2. 制定下一步计划
3. 执行操作
4. 根据反馈结果自我修正

**核心能力**：互联网搜索、本地文件读写、代码执行、长期和短期记忆辅助决策。

### SuperAGI（15k Star）

解决AutoGPT在生产环境中使用难的问题——完备的基础设施平台。

**核心能力**：
- 图形化界面+Agent市场+Tools+并发代理运行
- 可视化仪表盘同时运行和监控多个Agent，查看思维链（CoT）和执行日志
- 开发者可发布自定义工具包、智能体模板到市场供社区复用

**适合**：长期稳定运行、监控多Agent的企业级场景。

## 可视化编排平台

### Dify（12万+ Star）

融合**Backend-as-a-Service (BaaS)**和**LLMOps**理念的大模型应用开发平台。

**核心能力**：
- 可视化Prompt编排、运营管理、知识库RAG集成
- 不需要从头编写后端代码，快速将简单Prompt转化为可投入生产的AI应用
- 内置高质量RAG引擎，自动处理文档解析、分段和向量化

### Flowise（48k Star）

低代码/无代码UI可视化工具，**底层基于LangChain**。

**核心优势**：通过拖拽方式构建大模型应用——连接PDF加载器、OpenAI模型、Agent执行器等节点构建自定义逻辑流。LangChain文档劝退者的入门选择。

## 通用LLM框架

### LangChain

通用LLM开发框架，目前是构建Agent的**事实标准基础设施**之一。

**核心组件**：链 Chains、代理 Agents、记忆 Memory——开发者像搭积木一样串联提示词管理、文档加载、向量检索和模型调用。

**子项目LangGraph**（详见 [[entities/langgraph-framework]]）：专门构建有状态、多角色Agent应用，提供高度可控的循环计算能力。

详见 [[entities/langchain-framework]]。

## 多Agent协作框架

### MetaGPT（6万+ Star）

**模拟虚拟软件公司**——内部包含产品经理、架构师、项目经理、工程师等不同角色Agent。输入一句话需求，Agent协同工作输出用户故事、竞品分析、设计图甚至可运行代码。

**适合**：流程固定、输出稳定性要求高的多Agent协作场景。

### Microsoft AutoGen

微软开源的**多智能体对话框架**——可以定义多个可以相互对话的Agent（可以是LLM、人类或工具），通过对话协作解决任务。高度抽象和灵活，是工业界和学术界探索多智能体系统最主流的框架之一。

### CrewAI（42k Star）

近年来异军突起的Python框架，主打**角色扮演（Role-Playing）**编排。写CrewAI代码感觉像在给员工写任务书，**Python开发者上手多智能体的首选**。

让开发者轻松定义具有特定角色、目标和背景故事的Agent，组成团队按顺序或层级执行任务。

### ChatDev（28k Star）

清华大学OpenBMB开源，通过**聊天链**方式让不同角色智能体（CEO、CTO、程序员、测试员）在设计、编码、测试、文档等环节深度协作。过程可视化强，像在玩模拟经营游戏一样看着软件被开发出来。

详见 [[concepts/multi-agent-framework-comparison|Multi-Agent框架对比]]。

## 有状态Agent框架

### Letta

**MemGPT项目的继任者和正式化版本**——构建有状态（Stateful）AI智能体的开源框架。

**核心痛点解决**：大模型聊着聊着就忘了——通过引入类似操作系统的内存管理机制，让AI智能体拥有**持久化的长期记忆**，在不同会话和时间跨度中保持一致的身份和知识。

**核心理念**：**大模型即操作系统**——通过分层内存结构，将信息在当前上下文窗口和外部数据库之间动态调度。智能体具备自我编辑记忆的能力，自主决定何时将关键信息写入长期存储或从历史记录中检索数据，从而在不增加Token消耗的前提下**实现理论上无限的上下文窗口**。

**适合**：开发能陪伴用户几个月甚至几年的伴侣型应用。

## 选型决策树

```
你的场景是什么？
├── 自主任务执行（大目标拆解子任务）
│   ├── 研究自主智能体 → AutoGPT
│   └── 企业生产+多Agent监控 → SuperAGI
├── 快速原型/非技术用户
│   ├── 需要BaaS+LLMOps完整平台 → Dify
│   └── 只需LangChain可视化 → Flowise
├── 复杂逻辑稳健地基
│   └── 通用LLM框架 → LangChain（+LangGraph）
├── 多Agent协作
│   ├── 流程固定+输出稳定 → MetaGPT
│   ├── 灵活对话协作 → AutoGen
│   ├── 角色分工+Python友好 → CrewAI
│   └── 软件开发全流程可视化 → ChatDev
└── 需要持久化长期记忆
    └── 伴侣型应用 → Letta（大模型即OS）
```

## 与已有Wiki页面的关系

- **Agent架构全景** 详见 [[concepts/agent-architecture-landscape]]——平台全景是架构全景在工具层的展开
- **Multi-Agent框架深度对比** 详见 [[concepts/multi-agent-framework-comparison]]——本页是更广的平台视角，对比页是更深的框架细节
- **Agent框架五大支柱** 详见 [[concepts/agent-framework-engineering]]——平台是支柱的具体实现
- **LangChain框架详解** 详见 [[entities/langchain-framework]]
- **LangGraph框架详解** 详见 [[entities/langgraph-framework]]

## 未解问题

- 自主Agent平台（AutoGPT/SuperAGI）的"思考-计划-行动"循环在生产环境中的稳定性是否足够？^[ambiguous]
- Letta的"大模型即OS"理念是否能成为长期记忆的事实标准？还是会被其他方案（如RAG+Memory文件）取代？^[ambiguous]
- 多Agent协作框架是否会最终统一到少数几个标准？还是继续保持碎片化？^[inferred]

## 来源

- [[summaries/agent-development-platforms-top10]] — 10个Agent开发平台原文摘要
- 多 Agent 协作 github项目示例.md（raw/sources/AI 人工智能/AI Agent/Multi-Agent协同/）
- 原文：https://zhuanlan.zhihu.com/p/1989277883168989967
