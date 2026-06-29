---
title: Agent系统架构设计
category: concepts
tags: [AI, Agent, 架构设计, 执行循环, 消息总线]
aliases: [Agent Architecture Design, Agent执行循环, Agent消息总线]
summary: Agent系统架构两种视角：执行循环（Observe-Think-Act迭代+Skill/Memory/Sub-agent）和消息总线（Channel-Bus-Agent解耦+多渠道并发）——从单轮问答到自主循环执行的质变
source_dir: AI 人工智能/AI Agent/Agent架构设计
source_files: [Agent 系统架构设计：从执行循环到智能协作.md, Agent 架构设计解析：消息总线如何驱动多渠道智能体.md]
provenance:
  extracted: 0.55
  inferred: 0.40
  ambiguous: 0.05
base_confidence: 0.78
lifecycle: draft
lifecycle_changed: 2026-06-29
tier: supporting
created: 2026-06-29
updated: 2026-06-29
relationships:
  - target: "[[concepts/agent-framework-engineering]]"
    type: extends
  - target: "[[concepts/agent-architecture-landscape]]"
    type: related_to
  - target: "[[concepts/tool-calling-mcp]]"
    type: uses
  - target: "[[concepts/harness-engineering]]"
    type: related_to
  - target: "[[entities/langgraph-framework]]"
    type: related_to
---

# Agent系统架构设计

传统聊天机器人是单轮问答：用户提问，系统回答，流程结束。Agent不同——**它具备执行循环**：给定目标后自主迭代，观察中间结果，调整策略，直到达标或触发终止条件。从"被动响应"到"主动执行"的质变，需要回答核心问题：**如何让LLM驱动的系统循环执行、管理状态、调用工具、处理错误，并在合适时机停止？**

本文从两种架构视角展开：**执行循环**（单Agent内部迭代）和**消息总线**（多渠道Agent接入解耦）。

## 视角一：执行循环架构

### Agent的三步迭代

每次迭代：**Observe**（收集当前信息）→ **Think**（LLM推理决策下一步）→ **Act**（执行工具或生成回复）

### 分层架构

| 组件 | 职责 | 不负责 |
|------|------|--------|
| **AgentLoop** | 循环控制、会话序列化、终止判断、历史压缩触发 | 单次执行细节 |
| **AgentRunner** | 构建Prompt、调用LLM、解析响应、执行工具 | 上下文构建、消息路由 |
| **ContextBuilder** | Prompt组装（System Prompt+Memory+Skill摘要） | 执行逻辑 |
| **MemoryStore** | 文件I/O（MEMORY.md/SOUL.md/USER.md） | 数据分析 |

AgentLoop和AgentRunner分离的原因：Runner可被Dream等子系统复用，可独立测试单次执行逻辑，Loop专注流程控制而Runner专注执行细节。

### Skill vs Tool

**Tool定义"能做什么"（可执行操作），Skill定义"如何做好"（方法论知识）。** ^[inferred]

| 维度 | Tool | Skill |
|------|------|-------|
| 形式 | Python类 | Markdown文件 |
| 扩展方式 | 编写代码、注册、发布版本 | 添加.md文件即可 |
| 示例 | read_file工具 | "调试方法论"文档 |

Skill三层渐进加载：
- **层次1**：目录扫描（启动时收集所有SKILL.md路径）
- **层次2**：摘要注入（每轮对话将name+description清单注入System Prompt）
- **层次3**：完整内容（LLM自主调用read_file按需读取）

**Workspace skill优先级高于builtin**——用户无需修改Agent代码，只需在`workspace/skills/`目录创建Markdown文件即可注入领域知识。

### Memory三层架构

| 层次 | 存储 | 时效 | 内容 |
|------|------|------|------|
| 短期 | Session.messages | 单次对话 | 问答历史、工具调用记录 |
| 中期 | history.jsonl | 数周~数月 | 对话摘要、关键决策 |
| 长期 | memory.md | 永久 | 项目约束、固化知识 |

**Consolidator**：当prompt token占用超过75%时压缩旧消息——在用户回合边界切割，LLM将50条消息压缩为~500 tokens摘要，写入history.jsonl后移除Session中原始消息。

**Dream**：后台进程定期分析history.jsonl提取长期知识更新memory.md。两阶段设计——Phase 1（单次LLM调用生成建议，快速）+ Phase 2（多轮工具调用执行编辑，成本高）。Git集成：长期记忆纳入版本控制。

### Sub-agent机制

Sub-agent是**完整的AgentLoop实例**，不是简单工具调用。它拥有临时messages、独立ToolRegistry（不含spawn和message工具）、精简System Prompt、独立FileStates缓存。

| 维度 | 主Agent | Sub-agent |
|------|---------|-----------|
| Session | 持久化 | 临时（不持久化） |
| 工具集 | 完整+spawn+message | 完整但不含spawn和message |
| System Prompt | 完整上下文 | 精简版 |
| 用户交互 | 直接交互 | 不能直接联系用户 |

禁止spawn防止递归创建孙Agent，禁止message则必须通过主Agent转发消息。并发上限默认5个Sub-agent。

### 终止条件与错误恢复

| 终止原因 | 触发条件 |
|----------|----------|
| completed | LLM返回文本回复，无工具调用 |
| max_iterations | 达到步数上限（默认100步） |
| error | LLM调用失败或工具执行不可恢复错误 |
| ask_user | LLM请求用户确认或澄清 |

断点续传：每次迭代后保存checkpoint到Session.metadata，下次会话从失败点恢复。 ^[inferred]

### 设计原则

1. **声明式架构**：声明能力（注册工具）、声明知识（编写Skill文档）、声明约束（配置Memory规则）——LLM根据目标自主组合工具，无需预设流程
2. **渐进式上下文加载**：System Prompt分层加载避免token耗尽——Layer 1/2始终加载(~1k tokens)，Layer 3 LLM自主决定是否读取，Layer 4保留最近N条超出则压缩
3. **单一职责分离**：每个组件职责单一——独立测试、易于替换、降低耦合

## 视角二：消息总线架构

### 核心痛点

接入飞书/钉钉等不同IM平台时，每换一个平台之前的工作几乎无法复用——消息格式、回调接口、鉴权方式都不同。消息总线将Channel和Agent**完全解耦**。

### 总线即边界

消息总线本质是两个异步队列：`InboundQueue`接收各渠道消息，`OutboundQueue`存放Agent响应。Channel只和InboundQueue打交道，Agent只和OutboundQueue打交道，两者互不感知。接入新渠道只需实现三个接口：`start()`、`stop()`、`send()`——Agent代码一行不动。

### 四层架构

| 层级 | 职责 | 稳定性 |
|------|------|--------|
| 渠道层（Channels） | 接入各类IM平台，处理协议差异 | 易变，频繁新增 |
| 消息总线（Bus） | 异步解耦，不关心内容 | 最稳定，几乎不变 |
| 核心Agent层 | 上下文构建、工具调度、会话管理 | 稳定，慢速迭代 |
| Provider/工具层 | LLM调用、工具执行 | 稳定，但会扩展 |

**好边界的特征**：让变化的部分独立演化，让不变的部分保持稳定。

### 多渠道并发调度

**同Session串行，不同Session并发**。如果Session正在处理消息，新消息进入pending_queue排队等待；不同渠道的消息则并发执行互不阻塞。

### LLM Provider层

统一接口抹平各家差异：Anthropic用betas thinking，OpenAI用function calling，DeepSeek返回reasoning_content。关键设计：`error_should_retry`字段把"这个错误是否应该重试"的判断从调用方下沉到Provider内部——Agent不需要知道什么是rate_limit_exceeded。

重试策略：标准模式1s→2s→4s最多3次；持久模式最长60s延迟。降级处理：LLM返回非瞬时错误时去除图片内容后重试。

### 工具调用上限

AgentLoop内部维护迭代计数器，工具执行超过200次后停止返回超时提示，防止LLM进入无限循环。

### 响应分发

AgentLoop调用publish_outbound时消息带目标channel字段，所有Channel并发监听同一个outbound队列各自判断"这条消息是不是发给我的"——Agent不需要维护路由表。

## Chatbot vs Agent

| 维度 | Chatbot | Agent |
|------|---------|-------|
| 决策机制 | 规则引擎（if-else） | LLM推理 |
| 能力边界 | 预定义模板 | 动态工具调用 |
| 知识来源 | 硬编码 | Skill+Memory持续学习 |
| 执行模式 | 单轮对话 | 多轮迭代+工具执行 |

## 与已有Wiki页面的关系

- **执行循环视角** extends [[concepts/agent-framework-engineering|Agent框架工程]]的五大支柱——增加Skill/Tool区分、渐进式上下文加载、Sub-agent机制的细节
- **消息总线视角** related_to [[concepts/harness-engineering|Harness Engineering]]——两者都强调"边界即约束"，但消息总线关注Channel-Agent解耦而Harness关注Model-Harness解耦 ^[inferred]
- **Sub-agent机制** related_to [[concepts/multi-agent-orchestration|Multi-Agent协同编排]]——主从模式而非对等协作 ^[inferred]

## 未解问题

- 工具固化问题——新增工具需编码，未实现自动创造
- 完全依赖LLM——推理质量受限于模型能力
- 记忆被动——Dream依赖定时触发而非事件驱动 ^[ambiguous]
- 消息总线架构的控制粒度优势是否在简单场景下过度设计？^[ambiguous]

## 来源

- [[summaries/agent-system-architecture-design]] — Agent 系统架构设计：从执行循环到智能协作
- [[summaries/agent-message-bus-architecture]] — Agent 架构设计解析：消息总线如何驱动多渠道智能体
