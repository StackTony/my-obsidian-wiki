---
title: A2A协议（Agent-to-Agent Protocol）
category: summaries
tags: [AI, Agent, A2A, 协议, 互操作性]
summary: Google推出的A2A开放协议——异构Agent间的"国际通用语"：Agent Card+Task+Message/Part+Artifact，HTTP/JSON-RPC/SSE，异步+模态无关+不透明执行，与MCP互补（A2A对智，MCP对物）
source_dir: AI 人工智能/AI Agent/各种协议/A2A
source_files: [A2A协议.md]
provenance:
  extracted: 0.75
  inferred: 0.20
  ambiguous: 0.05
base_confidence: 0.78
lifecycle: draft
lifecycle_changed: 2026-08-03
tier: supporting
created: 2026-08-03
updated: 2026-08-03
---

# A2A协议（Agent-to-Agent Protocol）

原文：https://zhuanlan.zhihu.com/p/1894797987739324876

## 核心内容

### 太长不看版

- **What**：A2A是Google及合作伙伴倡导的**开放协议**，让来自不同供应商/不同框架构建的**异构AI Agent能安全通信和任务协作**——为AI Agent交互定义的"沟通语言"和框架
- **Why**：解决当前AI Agent生态"智能孤岛"问题——缺乏互操作性阻碍跨Agent系统协作，目标是促进开放、协作的Agent生态系统，打破供应商锁定
- **How**：基于HTTP/JSON-RPC 2.0/SSE；核心概念包括`Agent Card`（服务发现+能力描述）、`Task`（工作单元+状态管理）、`Message`+`Part`（多模态信息载体）、`Artifact`（最终成果）；强调**异步优先、模态无关、不透明执行**
- **资源入口**：[Awesome A2A](https://github.com/ai-boost/awesome-a2a)——社区维护的权威资源库

### 设计哲学

A2A设计深受互联网协议成功经验影响，凝练为若干核心原则：

| 原则 | 含义 |
|------|------|
| 简洁性 | 优先重用HTTP/1.1、JSON-RPC 2.0、SSE等成熟标准，降低实现门槛 |
| 企业级就绪 | 内置认证、授权、安全、隐私、可观测性考量 |
| 异步优先 | 优雅处理长时间运行任务和Human-in-the-Loop场景 |
| 模态无关 | 通过标准Part结构支持文本、文件、结构化数据、流媒体 |
| 不透明执行 | 只定义接口规范，不关心Agent内部实现——"黑盒"交互降低耦合度 |

### 架构概览

**核心参与者**：
- **User**：发起任务需求
- **Client Agent**：代表用户与其他Agent交互
- **Remote Agent / Server Agent**：提供能力并响应请求

**传输层**：
- 主要依赖HTTP(S)，所有交互通过标准HTTP请求（POST）
- 生产环境强制HTTPS
- 消息封装格式：JSON-RPC 2.0
- 异步场景：SSE（Server-Sent Events）实现单向事件流

### 核心数据对象

| 对象 | 作用 |
|------|------|
| **Agent Card**（智能体名片） | JSON文档：基本信息、API端点URL、能力（流式/推送）、认证方案、Skills列表——互操作性起点 |
| **Task**（任务） | 协作交互的核心实体：唯一Task ID、可选Session ID、状态（working/completed/input-required）、Message历史、Artifact列表、扩展元数据 |
| **Message** | Agent间非最终成果信息载体：来源角色（user/agent）+Part系列 |
| **Part** | 构成Message/Artifact内容的基本单元：类型（text/file/data）+对应数据 |
| **Artifact** | 任务执行最终输出（报告/代码/确认信息）：通常不可变，由一个或多个Part组成 |

### 关键交互模式

| 方法 | 用途 |
|------|------|
| `tasks/send` | 创建新任务或更新现有任务 |
| `tasks/get` | 轮询任务状态和Artifacts |
| `tasks/cancel` | 取消进行中任务 |
| `tasks/sendSubscribe` | 发起任务+订阅SSE推送更新 |
| `tasks/resubscribe` | SSE中断后重新订阅事件流 |
| `tasks/pushNotification/set` | 配置Webhook URL接收任务状态推送 |
| `tasks/pushNotification/get` | 查询当前推送配置 |

### A2A vs MCP精确辨析

A2A和MCP并非竞争而是**天然互补**：

| 特性 | A2A | MCP |
|------|-----|-----|
| 主要交互对象 | Agent到Agent（智能体间协作对话） | Agent到Tool/Resource（智能体调用外部能力/数据） |
| 交互性质 | 协作性、协商性、状态驱动、长时运行、多模态 | 调用性、请求-响应式、结构化、面向功能执行 |
| 核心目标 | 异构Agent间互操作性与任务协同 | 标准化Agent对外部工具和上下文资源的访问 |
| 抽象层级 | 应用层/协作层协议 | Agent内部决策与执行层面的工具接口协议 |
| 典型场景 | 任务委派、多Agent联合决策、复杂工作流编排 | API调用、数据库查询、文件读写、RAG数据检索 |

**协同模式**：主Agent通过MCP调用多个外部API获取实时数据；当需要更复杂推理时，通过A2A将子任务委派给专门的远程Agent；远程Agent内部又通过MCP调用各自工具集；最终通过A2A返回结果——**MCP负责"对物"交互，A2A负责"对智"交互** ^[inferred]

### 战略价值

1. **打破技术藩篱**——促进生态系统互联互通
2. **赋能复杂智能应用**——组合不同专业Agent能力解决综合性问题
3. **催生Agent服务市场**——标准化接口促进专业化分工
4. **加速企业落地**——企业级特性（认证/安全/合规）融入

### 当前状态与挑战

- 截至2026年8月，A2A仍处早期发展阶段，尚未发布1.0正式版
- 挑战：标准化推广形成网络效应、工具链与基础设施完善、安全实践落地、复杂协作场景细节细化

## 来源

- A2A协议.md（raw/sources/AI 人工智能/AI Agent/各种协议/A2A/）
- 原文：https://zhuanlan.zhihu.com/p/1894797987739324876
- 官方网站：https://google.github.io/A2A
- 官方GitHub：https://github.com/google/A2A
- Awesome A2A资源库：https://github.com/ai-boost/awesome-a2a

## 相关Wiki页面

- [[concepts/agent-communication-protocols]] — 三大Agent协议（MCP/ACP/A2A）三层协议栈概念页
- [[concepts/tool-calling-mcp]] — MCP协议——A2A的"对物"互补
- [[summaries/ai-protocols-comparison]] — 三大协议对比原文摘要
