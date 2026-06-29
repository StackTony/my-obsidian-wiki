---
title: LangChain框架
category: entities
tags: [AI, LangChain, LCEL, 框架]
summary: LangChain是LLM应用开发框架，核心抽象Runnable+LCEL将全部组件统一为可执行单元，支持链式组合、批处理和流式输出
source_dir: AI 人工智能/AI Agent/LangChain
source_files: [2-LangChain 架构.md, 1-LangChain 核心术语速查表.md, LangChain 解决的核心问题.md, LangChain 递归字符文本分割器原理、源码分析和实践.md]
provenance:
  extracted: 0.55
  inferred: 0.40
  ambiguous: 0.05
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: core
created: 2026-06-02
updated: 2026-06-29
relationships:
  - target: "[[concepts/agent-framework-engineering]]"
    type: implements
  - target: "[[entities/langgraph-framework]]"
    type: extends
  - target: "[[concepts/rag-engineering]]"
    type: uses
---

# LangChain框架

LangChain不仅是抽象LLM API的SDK，而是支持运行时模块组合与执行流程组织的框架。它将LLM应用开发从"拼凑API调用"提升到"声明式编排"。

## LangChain六大核心问题

LangChain 体系对应 AI Agent 开发的六个核心判断层面：

| 核心问题 | LangChain 对应机制 |
|----------|-------------------|
| 模型怎么解耦 | BaseLanguageModel 统一抽象层，支持 OpenAI/Anthropic/DeepSeek 等多模型无缝切换 |
| 上下文怎么组织 | PromptTemplate 模板系统 + 上下文注入，支持部分变量填充和动态注入 |
| 输出怎么约束 | OutputParser 输出解析，结构化约束 LLM 输出格式 |
| 外部动作怎么接入 | Tool + AgentAction，通过 BaseTool 自定义工具接入外部 API 和计算 |
| 历史和知识怎么选择 | Memory 系统（5种记忆类型）+ Retriever 检索机制 |
| 整条流程怎么编排和观测 | Runnable + LCEL 声明式编排 + LangSmith 可观测追踪 |

这六个问题构成了 LLM 应用开发的核心决策框架，LangChain 的每个模块都精确对应一个层面。^[inferred]

## 包结构分离

2024年后期完全分离为六个包：
| 包 | 职责 | 特性 |
|----|------|------|
| `langchain-core` | 核心抽象、Runnable协议、LCEL | 稳定、极少变更 |
| `langchain` | 高级组合、Chain、Agent、算法 | 中等变更频率 |
| `langchain-community` | 第三方集成 | 高频变更、易拆分 |
| `langgraph` | [[entities/langgraph-framework|LangGraph]]图驱动工作流编排 | 新增、独立发展 |
| `langserve` | 应用部署 | 将Chain部署为REST API |
| `langsmith` | 可观测与评测 | 追踪、评测、调试 |

## Runnable协议与LCEL

### Runnable：一切皆可执行单元
```python
class Runnable(ABC, Generic[Input, Output]):
    def invoke(self, input: Input) -> Output     # 单次执行
    def batch(self, inputs: List[Input]) -> List[Output]  # 批量
    def stream(self, input: Input) -> Iterator[Output]    # 流式
```

所有组件（PromptTemplate、LLM、Retriever、Tool、Parser）都实现Runnable接口。

核心方法扩展：`.transform()`（输出转换）、`.with_fallbacks()`（备用路径）、`.with_retry()`（自动重试，支持指数抖动退避）。

### LCEL：声明式编排
- 用 `|` 运算符将Runnable组合成链式管道
- 运算符重载 `__or__()` → RunnableSequence
- 支持RunnableParallel（并行）、RunnableBranch（条件分支）

```python
chain = prompt | llm | output_parser
result = chain.invoke({"question": "什么是RAG?"})
```

### 自定义Runnable模块（RunnableSerializable）

相比直接继承 Runnable，RunnableSerializable 自动提供 `.batch()`、`.stream()`、`.bind()` 等方法实现，支持 JSON 序列化和可观测配置导出。只需实现核心方法 `.invoke()`，即可接入整个 LCEL 执行框架。

```python
from langchain_core.runnables import RunnableSerializable

class AddOne(RunnableSerializable[int, int]):
    def invoke(self, input: int, config=None, **kwargs) -> int:
        return input + 1

# Retry + Fallback 联合使用
robust_add_one = add_one.with_retry(
    retry_if_exception_type=(ValueError, ZeroDivisionError),
    wait_exponential_jitter=True,
    stop_after_attempt=2
)
add_one_with_fallback = robust_add_one.with_fallbacks([
    RunnableLambda(lambda x: x + 5)  # fallback 模块
])
```

## 核心模块

| 模块 | 职责 | 关键类 |
|------|------|--------|
| **Model I/O** | LLM/ChatModel调用 | BaseLanguageModel、ChatOpenAI |
| **Prompt/Memory** | 模板系统+上下文注入 | PromptTemplate、ConversationBufferMemory |
| **Chains** | 多步组合 | LLMChain、SequentialChain |
| **Agents** | 自主决策循环 | ReActAgent、ToolCallingAgent |
| **Retriever & VectorStore** | RAG检索 | VectorStoreRetriever、FAISS |
| **LangGraph** | 工作流编排 | StateGraph、Node、Edge |

## BaseLanguageModel：多模型适配

类继承层次：Runnable → BaseLanguageModel → BaseLLM/BaseChatModel → 各具体实现。统一抽象层支持 OpenAI、Anthropic、DeepSeek、ChatGLM 等多种模型提供商。

| 方法 | 用途 | 返回值 |
|------|------|--------|
| `invoke()` | 单次调用 | string |
| `generate()` | 批量生成 | LLMResult |
| `batch()` | 并行批处理 | string[] |
| `stream()` | 流式输出 | AsyncIterator |

通过 `from_config()` 和 `.from_chain_type` 工厂方法快捷构造。^[inferred]

## PromptTemplate模板系统与上下文注入

模板创建方式：
- `from_template()` 快捷创建
- 显式定义 `input_variables` 构造
- ChatPromptTemplate 支持多角色对话（SystemMessage/HumanMessage/AIMessage）

高级特性：部分变量填充（`.partial()`）、动态变量注入、格式化输出。

```python
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个助手"),
    ("human", "{question}")
])
chain = prompt | llm | StrOutputParser()
```

## Memory系统设计

Memory 系统解决 LLM 无状态问题，在对话过程中保持和检索信息。核心方法：`save_context()` 保存、`load_memory_variables()` 加载。

| 类型 | 描述 | 适用场景 |
|------|------|----------|
| ConversationBufferMemory | 存储所有对话历史 | 简单短对话 |
| ConversationBufferWindowMemory | 只保留最近N轮 | 长对话token控制 |
| ConversationSummaryMemory | 自动摘要对话内容 | 大量历史压缩 |
| VectorStoreMemory | 向量数据库存储 | 大规模知识检索 |
| EntityMemory | 跟踪对话中的关键实体 | 实体追踪 |

智能压缩策略：在保持关键信息的同时减少 token 使用。^[inferred] 通过 `input_key` 和 `output_key` 与 ConversationChain 交互。

```python
memory = ConversationBufferMemory()
memory.save_context({"input": "你好"}, {"output": "你好，有什么可以帮你？"})
chain = ConversationChain(llm=llm, memory=memory, verbose=True)
```

## Agent架构

### ReAct决策循环

Agent 基本职责：接收用户输入 → LLM 推理 → 选择工具并调用 → 接收反馈继续推理 → 判断是否输出最终答案。

ReAct 模式采用"思考-行动-观察"循环（Think → Act → Observe），让 LLM 在每一步先推理再行动。

AgentExecutor 决策循环：用户输入 → LLM 推理出 Action → 执行 Tool 获取 Observation → 拼接进 scratchpad → 循环直到 Final Answer。

**scratchpad 中间记忆**：让 LLM 看到自己曾经做了什么，帮助规划下一步。^[inferred]

核心组件：AgentExecutor、ReActAgent、Tool、AgentAction、AgentFinish。

```python
from langchain_core.tools import Tool
tool = Tool(name="乘法计算工具", func=multiply_tool, 
            description="输入形如 '3*5' 的字符串，返回乘积")

agent = create_react_agent(llm=llm, tools=[tool], prompt=prompt)
executor = AgentExecutor.from_agent_and_tools(
    agent=agent, tools=[tool], verbose=True, handle_parsing_errors=True
)
```

### 自定义Tool + 插件 + 中间态管理

自定义 Tool：继承 BaseTool 类，实现 `_run()` 同步方法和 `_arun()` 异步方法。

AgentPlugin 插件机制：通过 BaseCallbackHandler 实现日志追踪、缓存、限制等额外逻辑。

中间态管理：`intermediate_steps` 自动构造 scratchpad，AgentAction 数据结构表示下一步调用哪个工具和参数，AgentFinish 表示推理结束输出最终结果。

```python
class ReverseTool(BaseTool):
    name: str = "reverse"
    description: str = "反转输入字符串"
    
    def _run(self, query: str) -> str:
        return query[::-1]

class LoggingPlugin(BaseCallbackHandler):
    def on_agent_action(self, action, **kwargs):
        print(f"Agent 决策：调用工具 {action.tool}")
```

## RAG实现

RAG 整体流程：query → Retriever → 按 chain_type 拼接 → LLM 生成 → 返回答案。

ChainType 合并策略：
- `stuff`：直接拼接所有片段（简单但易触发 token 限制）
- `map_reduce`：先对每片段分别生成小答案再汇总
- `refine`：迭代用更多文档精炼答案

Retriever 需实现 `_get_relevant_documents(query: str)`，Embedding 保证 query 与文档使用相同模型。^[inferred]

迁移建议：旧的 RetrievalQA 已废弃，建议迁移到 `create_retrieval_chain`。

## VectorStore与Retriever机制

VectorStore 是存储层，Retriever 是查询接口层。向量检索流程：文本 → Embedding → 向量存储 → 相似度查询 → 返回相关文档。

常用向量库：FAISS（本地高效）、Chroma（轻量级）、Weaviate（云原生）。

Retriever 类型：
- VectorStoreRetriever：基于向量相似度
- MultiQueryRetriever：多角度查询扩展
- ContextualCompressionRetriever：上下文压缩

```python
vectorstore = FAISS.from_documents(texts, embeddings)
retriever = vectorstore.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 4}
)
docs = retriever.get_relevant_documents("查询内容")
```

## LangGraph：图驱动工作流

LangGraph 是 LangChain 的图式扩展，突破 LCEL 的线性管道限制，支持复杂 DAG 结构（分支、循环、并发）。

核心组件：StateGraph（状态图容器）、Node（执行节点）、Edge（条件边/普通边）、State（共享状态对象，通过 TypedDict 定义）。

条件边：根据 State 动态选择下一节点，实现 if-else 逻辑。并发执行：支持多节点并行执行。^[inferred]

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

class AgentState(TypedDict):
    messages: list
    next_action: str

workflow = StateGraph(AgentState)
workflow.add_node("think", think_node)
workflow.add_node("act", act_node)
workflow.add_conditional_edges("act", lambda s: s["next_action"],
                               {"search": "think", "end": END})
app = workflow.compile()
```

### 持久化与人类反馈

Checkpoint 机制：通过 checkpointer 存储执行状态，支持中断后恢复。持久化方案：MemorySaver（内存）、SqliteSaver（SQLite）、RedisSaver（Redis）。

支持跨 session 保持状态、长时间任务中断恢复、关键节点暂停等待人工输入后继续、多 Agent 协作共享 State。^[inferred]

```python
from langgraph.checkpoint.sqlite import SqliteSaver
checkpointer = SqliteSaver("checkpoints.db")
app = workflow.compile(checkpointer=checkpointer)
config = {"configurable": {"thread_id": "user_123"}}
result = app.invoke(initial_state, config)
```

## LangServe部署

LangServe 将 Runnable 部署为 REST API 服务，基于 FastAPI + uvicorn。核心流程：Runnable → `add_routes()` → FastAPI app → uvicorn 启动。

自动特性：支持 invoke/stream/batch 所有 Runnable 方法、自动生成 OpenAPI 文档、支持异步调用、`enable_playground=True` 启用交互界面。^[inferred]

生产建议：配合 LangSmith 实现可观测、日志追踪、性能评估。

## 设计原理分析系列

14篇系列博客从架构总览到原型复刻，逐层深入 LangChain 设计原理：

| 序号 | 主题 | 核心抽象 | 层级 |
|------|------|----------|------|
| 1 | 架构总览 | Runnable + LCEL | 概览层 |
| 2 | Runnable实现与LCEL | RunnableSequence | 核心层 |
| 3 | 自定义Runnable模块 | RunnableSerializable | 核心层 |
| 4 | BaseLanguageModel多模型适配 | BaseLanguageModel | 模型层 |
| 5 | PromptTemplate模板系统+上下文注入 | PromptTemplate | 输入层 |
| 6 | Memory系统设计（5种记忆类型） | ConversationMemory | 记忆层 |
| 7 | Agent架构：ReAct决策循环 | AgentExecutor + ReAct | Agent层 |
| 8 | Agent自定义Tool+插件+中间态 | BaseTool + AgentAction | Agent层 |
| 9 | RAG实现 | Retriever + ChainType | 检索层 |
| 10 | VectorStore+Retriever机制 | VectorStore + Retriever | 检索层 |
| 11 | LangGraph StateGraph图式工作流 | StateGraph + Node | 图式层 |
| 12 | LangGraph持久化+checkpoint+人类反馈 | Checkpointer | 图式层 |
| 13 | LangServe部署 | LangServe + FastAPI | 部署层 |
| 14 | Mini LangChain实现（MVP） | MVP Runnable | 实践层 |

系列覆盖从核心抽象（Runnable/LCEL）→ 模型层 → 输入层 → 记忆层 → Agent层 → 检索层 → 图式层 → 部署层 → 实践复刻的完整路径，形成闭环学习体系。^[inferred]

## 设计模式

- **抽象层**：Runnable协议统一所有组件
- **工厂方法**：不同LLM通过统一接口创建
- **组合模式**：Runnable可嵌套组合
- **策略模式**：不同检索/重排/输出策略可替换

## 来源

- 2-LangChain 架构（raw/sources/AI 人工智能/AI Agent/LangChain/）
- 1-LangChain 核心术语速查表（raw/sources/AI 人工智能/AI Agent/LangChain/）
- LangChain 解决的核心问题（raw/sources/AI 人工智能/AI Agent/LangChain/）
- LangChain 递归字符文本分割器原理、源码分析和实践（raw/sources/AI 人工智能/AI Agent/LangChain/）
