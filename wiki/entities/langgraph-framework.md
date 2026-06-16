---
title: LangGraph框架
category: entities
tags: [AI, LangGraph, 工作流, 状态机, Agent]
summary: LangGraph将Agent行为建模为有向图：节点=动作、边=条件转移，支持循环/分支/并行——让Agent从自由聊天升级为可观测状态机
source_dir: AI 人工智能/Agent架构/LangChain
source_files: [LangGraph-工作流编排原理.md, LangGraph-状态-状态图-工作流.md]
  # 跨目录补充
  # source_dir: AI 人工智能/Agent架构/Memory记忆
  # source_files: [LangGraph-Agent记忆Memory架构.md]
provenance:
  extracted: 0.65
  inferred: 0.30
  ambiguous: 0.05
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: core
created: 2026-06-02
updated: 2026-06-16
relationships:
  - target: "[[entities/langchain-framework]]"
    type: extends
  - target: "[[concepts/agent-framework-engineering]]"
    type: implements
---

# LangGraph框架

LangGraph是LangChain生态中负责**工作流编排**的子框架。它将LLM应用从简单的链式调用（Chain）提升到支持循环、分支、条件路由的有向图工作流。

## 从Chain到Graph：为什么要图？

- **Chain/DAG限制**：链式或DAG结构不支持循环 → Agent反思（Reflection）、C-RAG重试等需要循环的场景无法实现
- **高层组件黑盒**：ReActAgent内部难以精细控制
- **不够简洁直观**：复杂流程需要声明式编排，而非if-else嵌套

## LangGraph核心概念

### StateGraph（状态图）
```python
from langgraph.graph import StateGraph

# 定义状态
class State(TypedDict):
    messages: list[BaseMessage]
    next: str

# 构建图
graph = StateGraph(State)
graph.add_node("agent", agent_node)
graph.add_node("tools", tool_node)
graph.add_edge("agent", "tools")
graph.add_conditional_edges("tools", should_continue, {"continue": "agent", "end": END})
graph.set_entry_point("agent")
app = graph.compile()
```

### 三个关键词
1. **Workflow** → 有向图，节点+边定义执行路径
2. **Step（Node）** → 图中每个节点是一个Runnable，执行一步操作
3. **Context（State）** → 全局状态对象，所有节点共享读写

## 工作流编排模式

| 模式 | 描述 | 代表场景 |
|------|------|----------|
| **顺序** | 线性执行 A→B→C→D | 简单RAG pipeline |
| **条件/分支** | 条件边决定下一步 | 路由器选择检索还是搜索 |
| **循环** | 节点间有环路 | Agent反思、重试、迭代优化 |

### 四种驱动机制
| 驱动 | 特点 | 适用 |
|------|------|------|
| **顺序驱动** | 按序执行，无法循环 | 简单pipeline |
| **图驱动** | 显式有向图+条件边 | LangGraph、LlamaIndex Workflow |
| **事件驱动** | Step间通过事件触发 | LlamaIndex Workflow（事件总线） |
| **LLM驱动** | LLM决策下一步 | ReAct Agent |

## 持久化与检查点

- **Checkpoint**：每个step执行后保存状态到数据库
- **Thread**：一个会话的所有checkpoint构成线程
- 意义：支持暂停恢复、时间旅行调试、多步状态回溯

## Memory架构

LangGraph提供两种记忆，这是理解Agent记忆系统的基础分类：

### 短期记忆（Short-term Memory）

线程范围的记忆，随时在与用户的**单个对话线程内**被召回。

- 通过**Checkpoint**持久化到数据库——线程可以随时恢复
- 状态通常包括对话历史、上传文件、检索到的文档、生成的工件
- 当图被调用或步骤完成时更新，每个步骤开始时读取状态
- **线程（Thread）**组织多个交互，类似电子邮件将消息分组到对话

#### 管理长对话历史

长对话对LLM构成挑战——完整历史可能超出上下文窗口，或即使技术上支持完整长度，大部分LLM在长上下文表现不佳（被陈旧内容分散注意力、响应更慢成本更高）。

**技术一：编辑消息列表**

最直接的方法：从列表中删除旧消息（类似LRU缓存）。LangGraph中可返回更新指定保留部分，或使用 `RemoveMessage` 删除指定ID的消息。

```python
# MessagesAnnotation + RemoveMessage 示例
def myNode2(state):
    # Delete all but the last 2 messages
    deleteMessages = state.messages
        .slice(0, -2)
        .map(lambda m: RemoveMessage(id=m.id))
    return {"messages": deleteMessages}
```

**技术二：总结过往对话**

修剪消息会丢失信息。更好的方法：用聊天模型总结消息历史，然后用摘要替代旧消息。

```python
async def summarizeConversation(state):
    summary = state.summary or ""
    # 生成摘要
    messages = [*state.messages, HumanMessage(content=summaryMessage)]
    response = await model.invoke(messages)
    # 删除旧消息，保留最近2条
    deleteMessages = state.messages.slice(0, -2).map(...)
    return {"summary": response.content, "messages": deleteMessages}
```

**技术三：trimMessages工具**

`trimMessages` 可指定保留的token数量和处理边界的策略（保留最后maxTokens、必须以HumanMessage开头等）。

### 长期记忆（Long-term Memory）

跨对话线程共享，**随时且在任何线程中**被召回。记忆可限定在自定义命名空间内（不只是单个线程ID）。

- 通过**Store**存储JSON文档——每个记忆组织在自定义`namespace`（类似文件夹）+独特`key`（像文件名）
- 命名空间通常包含用户/组织ID或其他标签，支持层次化组织
- 支持内容过滤搜索跨命名空间

#### 写入记忆的两种方式

| 方式 | 优点 | 缺点 |
|------|------|------|
| **主路径写入** | 实时、透明 | 降低工具调用性能、降低任务完成率、保存更少→召回率低 |
| **后台写入** | 不产生延迟、逻辑分离、模块化 | 需考虑写入频率、非实时更新 |

#### 管理记忆的两种方式

| 方式 | 优点 | 缺点 |
|------|------|------|
| **单档案管理** | 查询简单（GET操作）、高准确性 | 召回率低、需预测建模领域、文档过大易出错 |
| **记忆集合** | 信息丢失少、召回率高、每个记忆范围窄 | 搜索复杂、LLM可能过度插入/更新、需包含完整上下文 |

#### 记忆表示方式

| 方式 | 说明 |
|------|------|
| **更新自己的指令** | 元提示精炼指令集——根据交互动态更新行为规则 |
| **少量样本示例** | 存储输入-输出因果关系示例——包含推理轨迹降低误用 |

长期记忆远非已解决的问题，但以上模式提供了可靠的实现基础。^[inferred]

## 来源

- LangGraph-工作流编排原理（raw/sources/AI 人工智能/Agent架构/LangChain/）
- LangGraph-状态-状态图-工作流（raw/sources/AI 人工智能/Agent架构/LangChain/）
- LangGraph-Agent记忆Memory架构（raw/sources/AI 人工智能/Agent架构/Memory记忆/）