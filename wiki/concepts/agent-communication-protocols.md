---
title: Agent通信协议三大分类（MCP/ACP/A2A）
category: concepts
tags: [AI, Agent, MCP, ACP, A2A, 协议, 互操作性]
aliases: [AI Agent协议, Agent通信协议, 三大AI协议]
summary: AI Agent通信协议三层分工：MCP（工具驱动层Agent↔Resource）+ACP（协作通信层企业内Agent↔Agent）+A2A（公共发现层跨厂商）——像网络协议栈各司其职
source_dir: AI 人工智能/AI Agent/各种协议
source_files: [深度解析三大AI协议：MCP、ACP与A2A.md, A2A/A2A协议.md, ACP/ACP协议让AI团队协作成为现实（上篇）.md, ACP/ACP协议实战指南：从零构建你的AI智能体团队（下篇）.md]
provenance:
  extracted: 0.65
  inferred: 0.30
  ambiguous: 0.05
base_confidence: 0.80
lifecycle: draft
lifecycle_changed: 2026-08-03
tier: supporting
created: 2026-08-03
updated: 2026-08-03
relationships:
  - target: "[[concepts/tool-calling-mcp]]"
    type: extends
  - target: "[[concepts/agent-framework-engineering]]"
    type: uses
  - target: "[[concepts/agent-system-architecture]]"
    type: related_to
  - target: "[[concepts/multi-agent-orchestration]]"
    type: related_to
---

# Agent通信协议三大分类（MCP/ACP/A2A）

随着Agent生态从单打独斗走向协作，**协议标准化**成为决定整个生态运行效率的关键。当前主流的三大协议——MCP、ACP、A2A——并非竞争关系，而是像**网络协议栈**一样各司其职：MCP解决Agent如何连接外部工具，ACP解决企业内部Agent如何协作，A2A解决跨厂商Agent如何相互发现。

## 三层协议栈式分工

| 协议 | 开发者 | 抽象层级 | 比喻 | 通信协议 | 治理 |
|------|--------|----------|------|----------|------|
| **MCP** | Anthropic | 工具驱动层（Agent↔Resource） | "外接大脑" | JSON-RPC | 企业主导 |
| **ACP** | IBM/Linux基金会 | 协作通信层（Agent↔Agent，企业内） | "本地对讲机" | REST/HTTP | 开放治理 |
| **A2A** | Google | 公共发现层（Agent↔Agent，跨厂商） | "国际通用语" | JSON-RPC over HTTP + SSE | 企业主导 |

### MCP：工具驱动层

MCP（Model Context Protocol）解决**Agent如何调用外部能力**的问题——让LLM从"纯文本生成器"升级为"可执行动作的Agent"。

**核心能力**：
1. **上下文数据注入**——给AI开"数据窗口"，文件、数据库记录、API响应通过标准化接口进入模型工作内存
2. **功能路由与调用**——注册工具能力（如`searchCustomerData`/`generateReport`），模型按需调用，工具不用硬编码进模型
3. **提示词编排**——像搭积木动态组装上下文，用户问不同问题时只加载相关信息

详见 [[concepts/tool-calling-mcp|工具调用与MCP协议]]。

### ACP：协作通信层

ACP（Agent Communication Protocol）解决**企业内部Agent间如何协作**的问题——IBM团队推出、Linux基金会管理，被誉为"AI智能体领域的HTTP协议"。

**核心特性**：
- **REST架构**——任何熟悉Web开发的工程师都能快速上手，可用cURL/Postman直接测试
- **框架无关**——LangChain/CrewAI/AutoGen框架Agent都能通过简单适配层接入ACP网络
- **三种部署模式**——单智能体（快速原型）/多智能体单服务器（集中管理）/分布式多服务器（故障隔离+独立扩展）
- **离线发现机制**——把智能体"能力清单"嵌入到分发包中，即使某个智能体暂时不在线，其他系统也能知道它的存在和能力
- **多模态数据传输**——文字、图片、音频、自定义格式都能无缝处理

**核心痛点解决**：当前AI Agent生态像"语言巴别塔"——LangChain框架Agent说"LangChain语"，CrewAI框架Agent说"CrewAI语"，AutoGen框架Agent说"AutoGen语"。每要让不同框架Agent协作，开发者必须为每种组合编写昂贵、脆弱、不可复用的定制化集成代码。ACP让所有Agent说同一种"世界语"。

### A2A：公共发现层

A2A（Agent-to-Agent Protocol）解决**跨厂商Agent如何相互发现和协作**的问题——Google及合作伙伴倡导的开放协议，让异构AI Agent能安全通信和任务协作。

**核心设计原则**：
- 简洁性（重用HTTP/JSON-RPC 2.0/SSE）
- 企业级就绪（内置认证/授权/安全/隐私/可观测性）
- 异步优先（优雅处理长时间运行任务和Human-in-the-Loop）
- 模态无关（通过标准Part结构支持文本/文件/结构化数据/流媒体）
- **不透明执行**（只定义接口规范，不关心Agent内部实现——"黑盒"交互降低耦合度）

**核心数据对象**：
| 对象 | 作用 |
|------|------|
| Agent Card | JSON文档：基本信息、API端点、能力、认证方案、Skills列表——互操作性起点 |
| Task | 协作交互的核心实体：Task ID、Session ID、状态、Message历史、Artifact列表 |
| Message | Agent间非最终成果信息载体：来源角色+Part系列 |
| Part | 构成Message/Artifact内容的基本单元：类型（text/file/data）+数据 |
| Artifact | 任务执行最终输出（报告/代码/确认信息）：通常不可变 |

**关键方法**：`tasks/send`、`tasks/get`、`tasks/cancel`、`tasks/sendSubscribe`（SSE订阅）、`tasks/resubscribe`、`tasks/pushNotification/set`（Webhook配置）

## A2A vs MCP精确辨析

| 特性 | A2A | MCP |
|------|-----|-----|
| 主要交互对象 | Agent到Agent（智能体间协作对话） | Agent到Tool/Resource（智能体调用外部能力/数据） |
| 交互性质 | 协作性、协商性、状态驱动、长时运行、多模态 | 调用性、请求-响应式、结构化、面向功能执行 |
| 核心目标 | 异构Agent间互操作性与任务协同 | 标准化Agent对外部工具和上下文资源的访问 |
| 抽象层级 | 应用层/协作层协议 | Agent内部决策与执行层面的工具接口协议 |
| 典型场景 | 任务委派、多Agent联合决策、复杂工作流编排 | API调用、数据库查询、文件读写、RAG数据检索 |

**协同模式**：主Agent通过MCP调用多个外部API获取实时数据；当需要更复杂推理时，通过A2A将子任务委派给专门的远程Agent；远程Agent内部又通过MCP调用各自工具集；最终通过A2A返回结果——**MCP负责"对物"交互，A2A负责"对智"交互** ^[inferred]

## ACP边缘场景的独树一帜

ACP在边缘设备领域无可替代：
- 超低延迟——适合无人机、机器人车队等实时响应场景
- 无需云依赖——断网也能工作（工厂车间、偏远地区）
- 能力自动识别——代理间能自主分工

**典型案例**：
- 仓库多台机器人协作搬运货物，通过ACP实时广播位置和负载状态，无需云端调度就能避开拥堵
- 智能家居设备间（灯光、温控、安防）联动响应，延迟能控制在毫秒级

## 三种部署架构对比

ACP支持三种部署模式，体现其高度灵活性：

| 模式 | 适用场景 | 优势 |
|------|----------|------|
| 单智能体模式 | 快速原型开发、简单任务处理、调试测试 | 最简单，客户端直接对接一个智能体 |
| 多智能体单服务器模式 | 中等规模应用 | 优化资源利用，便于集中管理 |
| 分布式多服务器架构 | 大型企业级AI系统 | 故障隔离，独立扩展，高可用 |

## 协议融合的未来趋势

未来最可能的趋势是：**开源中间件会把这些协议"翻译"成统一接口**——开发者不用关心底层用了MCP还是A2A，只需调用简单指令，系统自动匹配最合适的协议（就像现在不用懂TCP/IP也能上网一样）。^[inferred]

这种统一接口的出现将大大降低开发者的使用门槛，促进AI Agent技术的更广泛应用。

## 与其他Wiki页面的关系

- **MCP协议详细机制** 详见 [[concepts/tool-calling-mcp|工具调用与MCP协议]]——本页是更高层级的协议栈视角
- **Agent框架五大支柱** 详见 [[concepts/agent-framework-engineering]]——协议是五大支柱之一
- **Agent系统架构设计** 详见 [[concepts/agent-system-architecture]]——消息总线架构与ACP的"协作通信层"目标相似 ^[inferred]
- **Multi-Agent协同编排** 详见 [[concepts/multi-agent-orchestration]]——多Agent编排需要协议支撑

## 未解问题

- 协议融合是否会真的走向统一接口？还是会出现新的"协议栈之争"？^[ambiguous]
- ACP的开放治理（Linux基金会）是否会成为AI协议领域的主流模式，而企业主导的MCP/A2A会面临信任压力？^[inferred]
- 边缘设备领域ACP的优势是否能持续？云原生场景下ACP vs A2A如何分工？^[ambiguous]

## 来源

- [[summaries/ai-protocols-comparison]] — 三大AI协议对比原文摘要
- [[summaries/a2a-protocol]] — A2A协议原文摘要
- [[summaries/acp-protocol]] — ACP协议原文摘要（上下篇）
- 深度解析三大AI协议：MCP、ACP与A2A（raw/sources/AI 人工智能/AI Agent/各种协议/）
- A2A协议（raw/sources/AI 人工智能/AI Agent/各种协议/A2A/）
- ACP协议（上下篇）（raw/sources/AI 人工智能/AI Agent/各种协议/ACP/）
