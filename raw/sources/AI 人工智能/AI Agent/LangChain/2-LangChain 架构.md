---
tags: [LangChain]
---

# LangChain 设计原理分析系列博客链接

 整理自稀土掘金
> https://juejin.cn/tag/LangChain


以下链接按编号顺序排列：

1. [LangChain 设计原理分析¹ | 架构总览：现代 AI 应用的基石](https://juejin.cn/post/7532992678108561418)

2. [LangChain 设计原理分析² | Runnable 和 LCEL 是如何实现的](https://juejin.cn/post/7533162298254393396)

3. [LangChain 设计原理分析³ | 从零实现一个自定义 Runnable 模块](https://juejin.cn/post/7533801117521936422)

4. [LangChain 设计原理分析⁴ | BaseLanguageModel 接口解构：多模型适配的设计模式](https://juejin.cn/post/7534294702697054223)

5. [LangChain 设计原理分析⁵ | PromptTemplate 模板系统与上下文注入机制](https://juejin.cn/post/7534727257337102390)

6. [LangChain 设计原理分析⁶ | Memory 系统设计：如何构建上下文感知的链](https://juejin.cn/post/7535265187823026186)

7. [LangChain 设计原理分析⁷ | Agent 架构设计详解：决策循环与 ReAct](https://juejin.cn/post/7535015508150517770)

8. [LangChain 设计原理分析⁸ | Agent 架构设计详解：自定义 Tool、插件与中间态管理](https://juejin.cn/post/7535450893078528036)

9. [LangChain 设计原理分析⁹ | 如何实现检索增强生成（RAG）](https://juejin.cn/post/7536086728110342171)

10. [LangChain 设计原理分析¹⁰ | 向量数据库与 Retriever 机制](https://juejin.cn/post/7537520455809613860)

11. [LangChain 设计原理分析¹¹ | LangGraph 系统解构——图式 Agent 工作流架构](https://juejin.cn/post/7537606213686214702)

12. [LangChain 设计原理分析¹² | LangGraph 解构——持久化、有状态协作与长时间任务](https://juejin.cn/post/7537879474639896617)

13. [LangChain 设计原理分析¹³ | LangChain Serve 快速部署](https://juejin.cn/post/7539938717805854766)

14. [LangChain 设计原理分析¹⁴ | 模拟实现一个精简版 LangChain](https://juejin.cn/post/7540111428108959807)

---

# 核心内容总结

---

1. [LangChain 设计原理分析¹ | 架构总览：现代 AI 应用的基石](https://juejin.cn/post/7532992678108561418)
## ¹ | 架构总览：现代 AI 应用的基石

**核心概念**：LangChain 是一套有系统设计、可维护、可实践、可扩展的 LLM 应用平台架构，不仅是抽象 LLM API 的 SDK，而是支持运行时模块组合与执行流程组织的框架。

**关键技术点**：
1. **包结构分离**：2024年后期完全分离为 langchain-core（核心设计）、langchain（高级组合）、langchain-community（社区扩展）、langgraph（图形性设计）、langserve（应用部署）、langsmith（可观测化）
2. **核心模型 Runnable + LCEL**：将全部组件抽象为可执行单元（Runnable），支持 `.invoke()` / `.stream()` / `.batch()` 等统一接口
3. **模块分层**：Model I/O、Prompt/Memory、Chains、Agents、Retriever & VectorStore、LangGraph
4. **设计模式**：抽象层、工厂方法、组合模式、策略模式

**架构要点**：

```python
class Runnable(ABC, Generic[Input, Output]):
    """可调用、批处理、流式处理、转换和组合的工作单元"""
    # invoke/ainvoke: 单次执行
    # batch/abatch: 批量处理
    # stream/astream: 流式输出
```

---

2. [LangChain 设计原理分析² | Runnable 和 LCEL 是如何实现的](https://juejin.cn/post/7533162298254393396)
## ² | Runnable 和 LCEL 是如何实现的

**核心概念**：Runnable 是 LangChain 架构中的核心抽象单元，LCEL（LangChain Expression Language）是声明式编排语言，用链式操作符（`|`）将多个 Runnable 组合成数据流管道。

**关键技术点**：
1. **Runnable 核心方法**：`.invoke()`（同步执行）、`.stream()`（流式输出）、`.batch()`（批量处理）、`.transform()`（输出转换）、`.with_fallbacks()`（备用路径）、`.with_retry()`（自动重试）
2. **运算符重载**：通过实现 `__or__()` 方法使 Runnable 可用 `|` 组合，形成 RunnableSequence
3. **扩展功能**：RunnableParallel（并行执行）、RunnableBranch（条件分支）
4. **自定义 Runnable**：继承 Runnable，重写 `invoke()` 方法

**代码示例**：

```python
# LCEL 链式组合
chain = RunnableMap({"name": lambda _: "LangChain"}) \
    | RunnableLambda(lambda d: f"Hello, {d['name']}!")

# 自定义 Runnable
class AddOne(Runnable[int, int]):
    def invoke(self, input: int, config=None) -> int:
        return input + 1

# 组合使用
workflow = AddOne() | RunnableLambda(lambda x: x * x)
workflow.invoke(2)  # 输出：9
```

---

3. [LangChain 设计原理分析³ | 从零实现一个自定义 Runnable 模块](https://juejin.cn/post/7533801117521936422)
## ³ | 从零实现一个自定义 Runnable 模块

**核心概念**：从头构建一个自定义 Runnable 模块，以它为基础搭建小型执行链，亲手实现 retry、fallback 等功能，从代码层面掌握核心执行架构。

**关键技术点**：
1. **RunnableSerializable 继承**：相比直接继承 Runnable，它自动提供 `.batch()`、`.stream()`、`.bind()` 等方法实现，支持 JSON 序列化和可观测配置导出
2. **自定义实现要点**：只需实现核心方法 `.invoke()`，就能立刻接入整个 LCEL 执行框架
3. **LCEL 组合链**：使用 `|` 运算符将自定义模块与其他 Runnable 组合成执行流水线
4. **Retry 机制**：通过 `.with_retry()` 包裹，设置异常类型、指数抖动退避、重试次数
5. **Fallback 机制**：通过 `.with_fallbacks()` 设置备用模块，主逻辑出错后自动切换

**代码示例**：

```python
from langchain_core.runnables import RunnableSerializable

class AddOne(RunnableSerializable[int, int]):
    def invoke(self, input: int, config=None, **kwargs) -> int:
        return input + 1

# LCEL 组合链
double = RunnableLambda(lambda x: x * 2)
add_one = AddOne()
pipeline = double | add_one  # 先乘2再加1
print(pipeline.invoke(3))  # 输出: 7

# Retry + Fallback 联合使用
robust_add_one = add_one.with_retry(
    retry_if_exception_type=(ValueError, ZeroDivisionError),
    wait_exponential_jitter=True,
    stop_after_attempt=2
)
add_one_with_fallback = robust_add_one.with_fallbacks([
    RunnableLambda(lambda x: x + 5)  # fallback 模块
])

# 批量处理
print(pipeline.batch([-1, 0, 1, 2, 3]))  # 输出: [1, 1, 3, 5, 7]
```

---

4. [LangChain 设计原理分析⁴ | BaseLanguageModel 接口解构：多模型适配的设计模式](https://juejin.cn/post/7534294702697054223)
## ⁴ | BaseLanguageModel 接口解构：多模型适配的设计模式

**核心概念**：BaseLanguageModel 是语言模型的统一抽象层，为所有 LLM 提供统一的接口规范，实现多模型提供商的无缝切换。

**关键技术点**：
1. **统一抽象层**：支持 OpenAI、Anthropic、DeepSeek、ChatGLM 等多种模型提供商
2. **类继承层次**：Runnable → BaseLanguageModel → BaseLLM/BaseChatModel → 各具体实现
3. **核心方法对比**：
   | 方法 | 用途 | 返回值 |
   |------|------|--------|
   | `invoke()` | 单次调用 | string |
   | `generate()` | 批量生成 | LLMResult |
   | `batch()` | 并行批处理 | string[] |
   | `stream()` | 流式输出 | AsyncIterator |
4. **工厂模式**：通过 `from_config()` 和 `.from_chain_type` 快捷构造

**架构要点**：PromptValue 支持、配置下发机制、与 Runnable 协议集成

---

5. [LangChain 设计原理分析⁵ | PromptTemplate 模板系统与上下文注入机制](https://juejin.cn/post/7534727257337102390)
## ⁵ | PromptTemplate 模板系统与上下文注入机制

**核心概念**：PromptTemplate 是模板化提示词的核心组件，通过变量注入和模板格式化实现动态 Prompt 构建。

**关键技术点**：
1. **模板创建方式**：`from_template()` 或显式定义 `input_variables`
2. **上下文注入**：支持部分变量填充（`.partial()`）、动态变量注入、格式化输出
3. **高级模板**：ChatPromptTemplate（多角色对话）、SystemMessage/HumanMessage/AIMessage
4. **LCEL 集成**：`chain = prompt | llm | StrOutputParser()`

**代码示例**：

```python
# 方式一
template = PromptTemplate.from_template("请回答：{question}")

# 方式二
template = PromptTemplate(
    template="你好{name}, 请回答：{question}",
    input_variables=["name", "question"]
)

# ChatPromptTemplate
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个助手"),
    ("human", "{question}")
])
```

---

6. [LangChain 设计原理分析⁶ | Memory 系统设计：如何构建上下文感知的链](https://juejin.cn/post/7535265187823026186)
## ⁶ | Memory 系统设计：如何构建上下文感知的链

**核心概念**：Memory 系统用于在对话过程中保持和检索信息，解决 LLM 无状态问题。

**关键技术点**：
1. **核心记忆类型**：
   | 类型 | 描述 | 适用场景 |
   |------|------|----------|
   | ConversationBufferMemory | 存储所有对话历史 | 简单短对话 |
   | ConversationBufferWindowMemory | 只保留最近N轮 | 长对话token控制 |
   | ConversationSummaryMemory | 自动摘要对话内容 | 大量历史压缩 |
   | VectorStoreMemory | 向量数据库存储 | 大规模知识检索 |
   | EntityMemory | 跟踪对话中的关键实体 | 实体追踪 |
2. **核心方法**：`save_context()` 保存、`load_memory_variables()` 加载
3. **与链集成**：通过 `input_key` 和 `output_key` 与 ConversationChain 交互
4. **智能压缩**：在保持关键信息的同时减少 token 使用

**代码示例**：

```python
memory = ConversationBufferMemory()
memory.save_context({"input": "你好"}, {"output": "你好，有什么可以帮你？"})
context = memory.load_memory_variables({})

chain = ConversationChain(llm=llm, memory=memory, verbose=True)
```

---

7. [LangChain 设计原理分析⁷ | Agent 架构设计详解：决策循环与 ReAct](https://juejin.cn/post/7535015508150517770)
## ⁷ | Agent 架构设计详解：决策循环与 ReAct

**核心概念**：LangChain Agent 架构的核心执行逻辑，解析 AgentExecutor 如何驱动 LLM 推理、工具调用与中间态反馈循环，结合 ReAct 思维链模式。

**关键技术点**：
1. **Agent 基本职责**：接收用户输入 → LLM 推理 → 选择工具并调用 → 接收反馈继续推理 → 判断是否输出最终答案
2. **ReAct 模式**：采用"思考-行动-观察"循环（Think → Act → Observe）
3. **AgentExecutor 决策循环**：用户输入 → LLM 推理出 Action → 执行 Tool 获取 Observation → 拼接进 scratchpad → 循环直到 Final Answer
4. **scratchpad 中间记忆**：让 LLM 看到自己曾经做了什么，帮助规划下一步
5. **核心组件**：AgentExecutor、ReActAgent、Tool、AgentAction、AgentFinish

**代码示例**：

```python
from langchain_core.tools import Tool
tool = Tool(name="乘法计算工具", func=multiply_tool, 
            description="输入形如 '3*5' 的字符串，返回乘积")

agent = create_react_agent(llm=llm, tools=[tool], prompt=prompt)
executor = AgentExecutor.from_agent_and_tools(
    agent=agent, tools=[tool], verbose=True, handle_parsing_errors=True
)
```

---

8. [LangChain 设计原理分析⁸ | Agent 架构设计详解：自定义 Tool、插件与中间态管理](https://juejin.cn/post/7535450893078528036)
## ⁸ | Agent 架构设计详解：自定义 Tool、插件与中间态管理

**核心概念**：LangChain Agent 系统的扩展能力，如何自定义工具、编写插件，以及如何灵活管理 Agent 的中间推理状态。

**关键技术点**：
1. **自定义 Tool**：继承 BaseTool 类，实现 `_run()` 同步方法和 `_arun()` 异步方法
2. **AgentPlugin 插件机制**：通过 BaseCallbackHandler 实现日志追踪、缓存、限制等额外逻辑
3. **AgentAction 数据结构**：表示下一步调用哪个工具、用什么参数、以及对应的思考日志
4. **AgentFinish 数据结构**：表示 Agent 推理结束，输出最终结果
5. **中间态管理**：`intermediate_steps` 自动构造 scratchpad

**代码示例**：

```python
class ReverseTool(BaseTool):
    name: str = "reverse"
    description: str = "反转输入字符串"
    
    def _run(self, query: str) -> str:
        return query[::-1]

class LoggingPlugin(BaseCallbackHandler):
    def on_agent_action(self, action, **kwargs):
        print(f"Agent 决策：调用工具 {action.tool}")
    
    def on_tool_end(self, output, **kwargs):
        print("工具返回：", output)

# AgentExecutor 循环伪代码
while True:
    action_or_finish = agent.plan(...)
    if isinstance(action_or_finish, AgentFinish):
        return action_or_finish.return_values
    observation = tool.run(action_or_finish.tool_input)
    intermediate_steps.append((action_or_finish, observation))
```

---

9. [LangChain 设计原理分析⁹ | 如何实现检索增强生成（RAG）](https://juejin.cn/post/7536086728110342171)
## ⁹ | 如何实现检索增强生成（RAG）

**核心概念**：深度剖析 RAG 实现，理解如何把"检索 + 生成"安全、可扩展地拼接起来。

**关键技术点**：
1. **Retriever（检索器）**：接收自然语言查询，返回 Document 列表，需实现 `_get_relevant_documents(query: str)`
2. **Embedding（向量化）**：把文本转换为向量，保证 query 与文档使用相同的 embedding 模型
3. **ChainType（合并策略）**：
   - `stuff`：直接拼接所有片段（简单但易触发 token 限制）
   - `map_reduce`：先对每片段分别生成小答案再汇总
   - `refine`：迭代用更多文档精炼答案
4. **整体流程**：query → Retriever → 按 chain_type 拼接 → LLM 生成 → 返回答案
5. **迁移建议**：旧的 RetrievalQA 已废弃，建议迁移到 `create_retrieval_chain`

**代码示例**：

```python
from langchain.chains.retrieval import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain

# 1. 加载文档并切分
loader = DirectoryLoader("docs", glob="**/*.txt")
raw_docs = loader.load()
splitter = RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=20)
texts = splitter.split_documents(raw_docs)

# 2. 嵌入并构建向量索引
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-zh-v1.5")
vectorstore = FAISS.from_documents(texts, embeddings)

# 3. 构建 Retriever 和 Chain
retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 2})
combine_docs_chain = create_stuff_documents_chain(llm, prompt)
chain = create_retrieval_chain(retriever=retriever, combine_docs_chain=combine_docs_chain)

out = chain.invoke({"input": "问题"})
```

---

10. [LangChain 设计原理分析¹⁰ | 向量数据库与 Retriever 机制](https://juejin.cn/post/7537520455809613860)
## ¹⁰ | 向量数据库与 Retriever 机制

**核心概念**：理解向量检索的实现机制、VectorStore 与 Retriever 在 LangChain 中的职责划分，掌握 FAISS 与 Chroma 的实践用法。

**关键技术点**：
1. **VectorStore 与 Retriever 区别**：VectorStore 是存储层，Retriever 是查询接口层
2. **向量检索流程**：文本 → Embedding → 向量存储 → 相似度查询 → 返回相关文档
3. **常用向量库**：FAISS（本地高效）、Chroma（轻量级）、Weaviate（云原生）
4. **Retriever 类型**：
   - VectorStoreRetriever：基于向量相似度
   - MultiQueryRetriever：多角度查询扩展
   - ContextualCompressionRetriever：上下文压缩
5. **接入 RAG 流水线**：`vectorstore.as_retriever()` 转换为 Retriever

**架构要点**：

```python
# VectorStore 存储
vectorstore = FAISS.from_documents(texts, embeddings)

# 转换为 Retriever
retriever = vectorstore.as_retriever(
    search_type="similarity",  # 或 "mmr", "similarity_score_threshold"
    search_kwargs={"k": 4}
)

# 检索
docs = retriever.get_relevant_documents("查询内容")
```

---

11. [LangChain 设计原理分析¹¹ | LangGraph 系统解构——图式 Agent 工作流架构](https://juejin.cn/post/7537606213686214702)
## ¹¹ | LangGraph 系统解构——图式 Agent 工作流架构

**核心概念**：LangGraph 是 LangChain 的图式扩展，用于构建有状态、多步驱动、支持分支循环的 Agent 工作流，突破 LCEL 的线性管道限制。

**关键技术点**：
1. **图式 vs 线性**：LangChain Chain 是线性管道，LangGraph 支持复杂 DAG 结构（分支、循环、并发）
2. **核心组件**：
   - StateGraph：状态图容器
   - Node：执行节点（Runnable）
   - Edge：条件边/普通边
   - State：共享状态对象
3. **状态管理**：通过 TypedDict 定义 State，节点间通过 State 传递数据
4. **条件边**：根据 State 动态选择下一节点，实现 if-else 逻辑
5. **并发执行**：支持多节点并行执行，提升多工具 Agent 效率

**代码示例**：

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

class AgentState(TypedDict):
    messages: list
    next_action: str

def think_node(state: AgentState) -> AgentState:
    # LLM 推理
    return {"next_action": "search"}

def act_node(state: AgentState) -> AgentState:
    # 执行工具
    return {"messages": state["messages"] + ["tool_result"]}

workflow = StateGraph(AgentState)
workflow.add_node("think", think_node)
workflow.add_node("act", act_node)
workflow.add_edge("think", "act")
workflow.add_conditional_edges("act", lambda s: s["next_action"], 
                               {"search": "think", "end": END})
app = workflow.compile()
```

---

12. [LangChain 设计原理分析¹² | LangGraph 解构——持久化、有状态协作与长时间任务](https://juejin.cn/post/7537879474639896617)
## ¹² | LangGraph 解构——持久化、有状态协作与长时间任务

**核心概念**：LangGraph 的持久化机制，支持长时间任务的中断恢复、多 Agent 协作、人类反馈介入等场景。

**关键技术点**：
1. **Checkpoint 机制**：通过 checkpointer 存储执行状态，支持中断后恢复
2. **持久化方案**：
   - MemorySaver：内存持久化（调试用）
   - SqliteSaver：SQLite 数据库
   - RedisSaver：Redis 存储
3. **长时间任务**：支持跨 session 保持状态，适合需要人工审核的场景
4. **人类反馈介入**：在关键节点暂停，等待人工输入后继续
5. **多 Agent 协作**：多个 Agent 共享 State，实现协作任务

**代码示例**：

```python
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph

checkpointer = SqliteSaver("checkpoints.db")
app = workflow.compile(checkpointer=checkpointer)

# 执行并保存 checkpoint
config = {"configurable": {"thread_id": "user_123"}}
result = app.invoke(initial_state, config)

# 恢复执行
app.invoke(None, config)  # 从上次 checkpoint 继续
```

---

13. [LangChain 设计原理分析¹³ | LangChain Serve 快速部署](https://juejin.cn/post/7539938717805854766)
## ¹³ | LangChain Serve 快速部署

**核心概念**：LangServe 用于将 Runnable 部署为 REST API 服务，实现生产级部署。

**关键技术点**：
1. **核心依赖**：langserve、fastapi、uvicorn
2. **部署流程**：Runnable → add_routes() → FastAPI app → uvicorn 启动
3. **自动特性**：
   - 支持 invoke/stream/batch 等所有 Runnable 方法
   - 自动生成 OpenAPI 文档
   - 支持异步调用
4. **配置项**：`enable_playground=True` 启用交互界面
5. **生产建议**：配合 LangSmith 实现可观测、日志追踪、性能评估

**代码示例**：

```python
from fastapi import FastAPI
from langserve import add_routes

app = FastAPI(title="LangChain Service")

# 添加 Runnable 路由
add_routes(app, chain, path="/chain", enable_playground=True)

# 启动服务
# uvicorn server:app --host 0.0.0.0 --port 8000
```

---

14. [LangChain 设计原理分析¹⁴ | 模拟实现一个精简版 LangChain](https://juejin.cn/post/7540111428108959807)
## ¹⁴ | 模拟实现一个精简版 LangChain

**核心概念**：从零开发小框架，综合运用前文知识，动手复刻 LangChain 核心原型。

**关键技术点**：
1. **总体设计**：实现 MVP 版本，覆盖 LangChain 核心理念
2. **核心抽象**：
   - Runnable 抽象：提供 invoke / stream / batch
   - LCEL 组合：支持 `|` 运算符链式组合
3. **实现组件**：
   - MockLLM：模拟语言模型
   - PromptTemplate：简单模板系统
   - Memory：基础对话记忆
   - Agent：简单 ReAct 循环
4. **验证方式**：通过实际调用验证各组件功能
5. **学习价值**：理解 LangChain 内部设计原理

**架构要点**：

```python
# MVP Runnable 抽象
class Runnable:
    def invoke(self, input) -> Any:
        raise NotImplementedError
    
    def __or__(self, other):
        return RunnableSequence([self, other])

class RunnableSequence(Runnable):
    def invoke(self, input):
        for runnable in self.steps:
            input = runnable.invoke(input)
        return input

# 验证
chain = PromptTemplate("你好{name}") | MockLLM() | OutputParser()
result = chain.invoke({"name": "用户"})
```

---

## 整体架构演进脉络

| 序号 | 主题 | 核心抽象 | 层级 |
|------|------|----------|------|
| ¹ | 架构总览 | Runnable + LCEL | 概览层 |
| ² | Runnable 实现 | RunnableSequence | 核心层 |
| ³ | 自定义 Runnable | RunnableSerializable | 核心层 |
| ⁴ | 模型接口 | BaseLanguageModel | 模型层 |
| ⁵ | 模板系统 | PromptTemplate | 输入层 |
| ⁶ | Memory系统 | ConversationMemory | 记忆层 |
| ⁷ | Agent决策 | AgentExecutor + ReAct | Agent层 |
| ⁸ | 工具扩展 | BaseTool + AgentAction | Agent层 |
| ⁹ | RAG实现 | Retriever + ChainType | 检索层 |
| ¹⁰ | 向量检索 | VectorStore + Retriever | 检索层 |
| ¹¹ | LangGraph图式 | StateGraph + Node | 图式层 |
| ¹² | LangGraph持久化 | Checkpointer | 图式层 |
| ¹³ | 服务部署 | LangServe + FastAPI | 部署层 |
| ¹⁴ | 原型复刻 | MVP Runnable | 实践层 |
