---
title: LangGraph框架
category: entities
tags: [AI, LangGraph, 工作流, 状态机, Agent]
summary: LangGraph将Agent行为建模为有向图：节点=动作、边=条件转移，支持循环/分支/并行——让Agent从自由聊天升级为可观测状态机
source_dir: AI 人工智能/Agent架构/LangChain
source_files: [LangGraph-工作流编排原理.md, LangGraph-状态-状态图-工作流.md]
provenance:
  extracted: 0.65
  inferred: 0.30
  ambiguous: 0.05
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: core
created: 2026-06-02
updated: 2026-06-02
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

详见 [[concepts/agent-framework-engineering]] 中的记忆部分。LangGraph提供两种记忆：
- **短期记忆**：通过Checkpoint在Thread内持久化
- **长期记忆**：通过Store跨Thread共享

### 管理长对话历史的技术
- **编辑消息列表**：从列表中删除旧消息（类似LRU缓存）
- **总结过往对话**：用LLM压缩长历史为摘要
- **RemoveMessage**：LangGraph内置消息删除机制

## 来源

- LangGraph-工作流编排原理（raw/sources/AI 人工智能/Agent架构/LangChain/）
- LangGraph-状态-状态图-工作流（raw/sources/AI 人工智能/Agent架构/LangChain/）