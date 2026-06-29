---
title: LangGraph框架
category: entities
tags: [AI, LangGraph, 工作流, 状态机, Agent]
summary: LangGraph将Agent行为建模为有向图：节点=动作、边=条件转移，支持循环/分支/并行——让Agent从自由聊天升级为可观测状态机
source_dir: AI 人工智能/AI Agent/LangChain
source_files: [LangGraph-工作流编排原理.md, LangGraph-状态-状态图-工作流.md]
  # 跨目录补充
  # source_dir: AI 人工智能/AI Agent/Memory记忆
  # source_files: [LangGraph-Agent记忆Memory架构.md]
provenance:
  extracted: 0.65
  inferred: 0.28
  ambiguous: 0.07
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: core
created: 2026-06-02
updated: 2026-06-29
relationships:
  - target: "[[entities/langchain-framework]]"
    type: extends
  - target: "[[concepts/agent-framework-engineering]]"
    type: implements
  - target: "[[entities/oh-my-opencode]]"
    type: related_to
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

## 状态/状态图/工作流三层概念

LangGraph的核心可拆解为三个层次，各有明确的职责边界：

### State（状态）—— 数据传递与更新的载体

状态是在图遍历节点的过程中传递并更新的信息。可以形象地比喻为一个**背包**：背包装载着AI工作流所需的所有信息（对话内容、用户输入、中间计算结果等），每执行一个操作，背包里的信息就随之更新。

从数据结构角度，状态通常使用 `TypedDict` 或 `Pydantic` 模型定义，明确规定数据的结构和内容：

```python
from typing_extensions import TypedDict
class MyState(TypedDict):
    input: str
    result: str = None
```

这种严格的数据结构定义使代码更安全可靠——类型检查工具会在数据不符合规定时及时抛出错误。^[inferred] （原文强调类型安全优势，推断这有助于避免运行时问题）

### StateGraph（状态图）—— 工作流的蓝图

状态图是流程图的设计蓝图，详细定义了四个关键要素：

| 要素 | 说明 |
|------|------|
| **状态的结构** | 明确状态应具备哪些属性和数据类型 |
| **节点（步骤）** | 定义工作流中包含哪些具体操作或任务 |
| **数据流向** | 描述数据如何在不同节点之间传递 |
| **状态更新机制** | 规定每个节点执行时状态如何更新 |

与状态不同，**状态图侧重于定义结构和流程**，而状态则是实际在这个结构中流动的数据。

### Workflow（工作流）—— 状态图的运行实例

工作流是状态图经过编译后的实际执行系统。定义好状态图后，调用 `.compile()` 将其转换为工作流，然后通过 `.invoke()` 或 `.stream()` 执行：

```python
graph = builder.compile()                        # 编译为工作流
final_state = graph.invoke(initial_state)         # 执行工作流
```

工作流获取初始状态，按照状态图定义的规则逐步传递和更新状态，直至完成整个流程。后续执行可将上一次的最终状态作为新输入，实现连续处理。

### 柠檬水工厂类比

以自动化柠檬水工厂为例，三层概念的关系一目了然：

| 概念 | 类比 | 说明 |
|------|------|------|
| **StateGraph** | 工厂设计蓝图 | 规划生产步骤（询问口味→挤柠檬→加糖/盐→倒水→搅拌→提供），定义原料和成品在各环节间的流动方式 |
| **State** | 正在制作的那杯柠檬水 | 随生产流程推进，状态不断更新——确定口味后"柠檬水类型"字段更新，挤柠檬后"柠檬添加量"字段更新 |
| **Workflow** | 启动生产的实际操作 | 根据蓝图准备好设备，从初始状态（空杯）开始，柠檬水依次经过各环节，最终产出成品 |

**设计蓝图是静态的规划框架，柠檬水是动态的数据载体，启动操作是运行时的执行过程**——三者缺一不可。

## 工作流编排演进

LLM应用的工作流经历了从简单到复杂的四个阶段演进：

### 顺序 → 条件 → 分支 → 循环

| 阶段 | 执行方式 | 代表场景 | 局限 |
|------|----------|----------|------|
| **顺序** | 线性执行 A→B→C→D | 简单RAG pipeline | 无法根据结果调整路径 |
| **条件** | 条件边决定下一步 | 路由器选择检索还是搜索 | 只能走一条路，不支持多路并行 |
| **分支** | 多条路径并行或择一执行 | 多检索器并行检索+合并 | 仍然不支持回退重试 |
| **循环** | 节点间有环路 | Agent反思、重试、迭代优化 | 需要图结构才能实现 |

早期框架主要提供两种编排方式：一是封装更高层的组件与API（如RouterRetriever），二是提供链式或DAG结构的可编排方法（如LangChain的Chain/LCEL、LlamaIndex的QueryPipeline）。但高层组件缺乏灵活性且内部黑盒，链式/DAG结构无法支持循环——这推动了LangGraph等图式编排框架的诞生。^[inferred] （原文列举了高层封装和链式DAG两种方式的局限，推断这构成了图式编排框架的诞生动力）

以一个RAG Agent的完整工作流为例，四种模式交织使用：路由器做条件判断（条件）、向量检索或网页搜索并行（分支）、文档评分后可能回退重写查询（循环）。

### Runnable协议—— 统一抽象基石

在LangChain 0.1之前，Prompt/LLM等基础组件的抽象粒度较低且相对碎散。后来LangChain将它们统一到**Runnable协议**——就像Java里的一切皆Object，原子组件标准化后，以此为基础提出了编排组件LCEL和LangGraph。

实现了Runnable接口的类可以拿上一个链的输出作为自己的输入，核心方法包括：

| 方法 | 说明 |
|------|------|
| `invoke/ainvoke` | 单个输入转为输出 |
| `batch/abatch` | 批量转换 |
| `stream/astream` | 流式处理，精细化控制各节点产生的数据 |
| `stream_events` | 流式获取中间事件（比token更粗、比final answer更细） |

类似Runnable协议的思路在业界有广泛应用。KAG中文档入库的pipeline也采用了Runnable抽象：

```python
class DiseaseBuilderChain(BuilderChainABC):
    def build(self, **kwargs):
        source = PdfReader(output_type="Chunk", file_path=xx)
        splitter = LengthSplitter(split_length=2000)
        extractor = KAGExtractor()
        vectorizer = BatchVectorizer()
        sink = KGWriter()
        return source >> splitter >> extractor >> vectorizer >> sink
```

KAG复用了 `>>` 运算符重载（即 `__rshift__` 方法），与LCEL的 `|` 管道操作符思路一致：统一抽象让组件可编排。^[inferred]

## 四种驱动机制

| 驱动 | 特点 | 适用 | 代表实现 |
|------|------|------|----------|
| **顺序驱动** | 按序执行，无法循环 | 简单pipeline | LCEL `prompt | model | parser` |
| **图驱动** | 显式有向图+条件边，支持循环 | 需要条件路由和循环的场景 | LangGraph、LlamaIndex Workflow |
| **事件驱动** | Step间通过事件触发，解耦发送方和接收方 | 需要松耦合、动态订阅的场景 | LlamaIndex Workflow（事件总线） |
| **LLM驱动** | LLM决策下一步，自主规划 | 需要自主决策的场景 | ReAct Agent（AgentExecutor） |

### 图驱动 vs 事件驱动对比

| 维度 | 图驱动 | 事件驱动 |
|------|--------|----------|
| **控制流定义** | 显式定义节点和边，流程可预测 | 事件总线隐式连接，流程更灵活 |
| **耦合度** | 紧耦合——节点必须知道下游是谁 | 松耦合——Step只需发布/订阅事件 |
| **可观测性** | 流程图可可视化，调试直观 | 事件流需要追踪工具 |
| **动态性** | 条件边提供有限动态路由 | 可运行时动态添加/移除Step |
| **循环支持** | 有向图天然支持（LangGraph） | 需额外机制支持循环 |

图驱动适合流程可预测、需要精细控制的场景（如Agent工作流）；事件驱动适合需要松耦合和动态扩展的场景。^[inferred] （原文分别描述了两种驱动的特点，推断它们的适用场景差异）

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

- LangGraph-工作流编排原理（raw/sources/AI 人工智能/AI Agent/LangChain/）
- LangGraph-状态-状态图-工作流（raw/sources/AI 人工智能/AI Agent/LangChain/）
- LangGraph-Agent记忆Memory架构（raw/sources/AI 人工智能/AI Agent/Memory记忆/）