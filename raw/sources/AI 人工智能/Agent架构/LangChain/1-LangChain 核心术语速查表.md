# LangChain 核心术语速查表

整合知识库中的 LangChain 相关术语，按类别分组。

---

## 一、框架定位

| 术语 | 英文 | 解释 |
|------|------|------|
| **LangChain** | - | LLM 应用开发框架，解决 AI Agent 开发 6 个核心问题：模型解耦、上下文组织、输出约束、外部动作接入、知识检索、流程编排 |
| **langchain-core** | - | 核心抽象层（Runnable、LCEL） |
| **langchain** | - | 高级组合模块 |
| **langchain-community** | - | 社区扩展（各模型适配） |
| **langgraph** | - | 图形化 Agent 工作流 |
| **langserve** | - | REST API 部署服务 |
| **langsmith** | - | 可观测化平台（追踪、评估、调试） |

---

## 二、核心抽象 Runnable

| 术语 | 英文 | 解释 |
|------|------|------|
| **Runnable** | - | 所有组件的统一抽象单元，支持链式组合 |
| **invoke()** | 单次执行 | 同步调用，返回单个结果 |
| **stream()** | 流式输出 | 异步迭代器，实时显示生成过程 |
| **batch()** | 批量处理 | 并行处理多个输入 |
| **with_retry()** | 自动重试 | 错误恢复，指数退避 |
| **with_fallbacks()** | 备用路径 | 降级策略，错误时切换备用模块 |
| **RunnableSequence** | 顺序执行链 | Runnable 顺序组合 |
| **RunnableParallel** | 并行执行 | 多个 Runnable 同时执行 |
| **RunnableBranch** | 条件分支 | 根据条件选择执行路径 |
| **RunnableLambda** | 自定义函数 | 包装普通函数为 Runnable |
| **RunnableMap** | 多输出映射 | 输出字典结构 |
| **RunnableSerializable** | 可序列化 Runnable | 继承后自动获得 batch/stream/bind 方法 |

---

## 三、LCEL 表达式语言

| 术语         | 英文                            | 解释                     |                  |                                       |
| ---------- | ----------------------------- | ---------------------- | ---------------- | ------------------------------------- |
| **LCEL**   | LangChain Expression Language | 声明式编排语言，用 `            | ` 运算符组合 Runnable |                                       |
| **\| 运算符** | Pipe Operator                 | 通过 `__or__()` 方法实现链式组合 |                  |                                       |
| **链式组合**   | Chain Composition             | `prompt                | llm              | parser` 等价于 `RunnableSequence([...])` |

```python
# 示例
chain = prompt | llm | StrOutputParser()
```

---

## 四、模型层 Model I/O

| 术语 | 英文 | 解释 |
|------|------|------|
| **BaseLanguageModel** | - | 模型统一抽象层 |
| **BaseLLM** | - | 补全模型基类 |
| **BaseChatModel** | - | 对话模型基类 |
| **LLM** | Large Language Model | 补全模型（如 GPT-3） |
| **ChatModel** | - | 对话模型（如 GPT-4、Claude） |
| **invoke()** | 单次调用 | 返回 string |
| **generate()** | 批量生成 | 返回 LLMResult |
| **stream()** | 流式输出 | AsyncIterator |

---

## 五、Prompt 模板系统

| 术语 | 英文 | 解释 |
|------|------|------|
| **PromptTemplate** | - | 动态模板，支持变量插值 `{variable}` |
| **ChatPromptTemplate** | - | 多角色对话模板 |
| **from_template()** | 从模板创建 | `PromptTemplate.from_template("回答：{question}")` |
| **from_messages()** | 从消息创建 | `[("system", "角色"), ("human", "{question}")]` |
| **input_variables** | 输入变量 | 模板需要的变量列表 |

---

## 六、Memory 记忆系统

| 术语                                 | 英文    | 解释                   |
| ---------------------------------- | ----- | -------------------- |
| **Memory**                         | 记忆系统  | 保持对话上下文，解决 LLM 无状态问题 |
| **ConversationBufferMemory**       | 缓冲记忆  | 存储所有对话历史             |
| **ConversationBufferWindowMemory** | 窗口记忆  | 只保留最近 N 轮对话          |
| **ConversationSummaryMemory**      | 摘要记忆  | 自动压缩对话内容             |
| **VectorStoreMemory**              | 向量记忆  | 向量数据库存储大规模知识         |
| **EntityMemory**                   | 实体记忆  | 跟踪对话中的关键实体           |
| **save_context()**                 | 保存上下文 | 写入对话历史               |
| **load_memory_variables()**        | 加载记忆  | 读取历史到 Prompt         |

---

## 七、Agent 智能体架构

| 术语 | 英文 | 解释 |
|------|------|------|
| **Agent** | 智能体 | 自主决策、调用工具、与环境交互的 AI 系统 |
| **ReAct** | Reasoning + Acting | Think → Act → Observe 循环模式 |
| **Think** | 思考 | LLM 推理下一步行动 |
| **Act** | 行动 | 执行工具调用 |
| **Observe** | 观察 | 获取工具返回结果 |
| **scratchpad** | 中间记忆 | 让 LLM 看到自己曾经做了什么 |
| **AgentExecutor** | 决策循环驱动器 | 管理整个 Agent 执行流程 |
| **Tool** | 工具 | 外部功能抽象 |
| **AgentAction** | 下一步行动 | LLM 决策的行动指令 |
| **AgentFinish** | 最终输出 | Agent 结束时的结果 |
| **create_react_agent()** | 创建 ReAct Agent | LangChain Agent 构建函数 |

---

## 八、Tool 工具系统

| 术语 | 英文 | 解释 |
|------|------|------|
| **Tool** | 工具 | Agent 可调用的外部功能 |
| **BaseTool** | 工具基类 | 自定义工具继承 |
| **name** | 工具名称 | 唯一标识 |
| **description** | 工具描述 | LLM 选择工具的依据 |
| **_run()** | 执行方法 | 工具核心逻辑 |
| **AgentPlugin** | 插件机制 | 通过 BaseCallbackHandler 扩展 |

```python
class ReverseTool(BaseTool):
    name = "reverse"
    description = "反转输入字符串"
    def _run(self, query: str) -> str:
        return query[::-1]
```

---

## 九、Plan-and-Execute 范式

| 术语 | 英文 | 解释 |
|------|------|------|
| **Plan-and-Execute** | 规划执行范式 | 先制定完整计划，再逐步执行 |
| **Planner** | 规划器 | 生成多步计划（大模型） |
| **Executor** | 执行器 | 执行单步任务（小模型/工具） |
| **Re-planner** | 重规划器 | 判断完成或后续计划 |
| **ReWOO** | Reasoning Without Observation | 变量引用 `#E1`，无需每步规划 |
| **LLMCompiler** | - | DAG + 并行 + 流式执行 |

| 对比 | ReAct | Plan-and-Execute |
|------|-------|------------------|
| 规划方式 | 单步思考 | 全局多步计划 |
| LLM 调用 | 每步调用 1 次 | 仅规划 + 最终响应 |
| 成本 | 高 | 低 |

---

## 十、LangGraph 图式工作流

| 术语 | 英文 | 解释 |
|------|------|------|
| **LangGraph** | - | LangChain 的图式扩展，支持 DAG 工作流 |
| **StateGraph** | 状态图 | 图容器，管理节点和边 |
| **Node** | 节点 | 执行节点（Runnable） |
| **Edge** | 边 | 普通边（固定连接） |
| **Conditional Edge** | 条件边 | 根据状态动态选择路径 |
| **State** | 状态 | TypedDict 定义，节点间共享数据 |
| **END** | 结束节点 | 工作流终止 |

```python
workflow = StateGraph(AgentState)
workflow.add_node("think", think_node)
workflow.add_edge("think", "act")
workflow.add_conditional_edges("act", lambda s: s["next_action"])
```

---

## 十一、Checkpoint 持久化

| 术语 | 英文 | 解释 |
|------|------|------|
| **Checkpoint** | 检查点 | 存储执行状态，支持中断恢复 |
| **Checkpointer** | 持久化器 | 状态存储组件 |
| **MemorySaver** | 内存持久化 | 调试用，不持久 |
| **SqliteSaver** | SQLite 持久化 | 本地数据库 |
| **RedisSaver** | Redis 持久化 | 分布式存储 |
| **thread_id** | 线程 ID | 标识对话线程 |
| **中断恢复** | Resume | 从上次 checkpoint 继续执行 |

---

## 十二、Agent Memory 记忆架构

| 术语 | 英文 | 解释 |
|------|------|------|
| **Short-term Memory** | 短期记忆 | 单个对话线程内，Checkpointer 自动保存 |
| **Long-term Memory** | 长期记忆 | 跨线程共享，Store 显式写入 |
| **Store** | 存储 | 键值数据库，长期记忆持久层 |
| **Semantic Memory** | 语义记忆 | 事实性知识（用户偏好） |
| **Episodic Memory** | 情景记忆 | 事件经历（过去对话） |
| **Procedural Memory** | 程序记忆 | 技能规则（任务指令） |
| **Profile** | 单文档 | 持续更新的个人档案 |
| **Collection** | 多文档集合 | 按类别存储的记忆集合 |

---

## 十三、LangServe 部署

| 术语 | 英文 | 解释 |
|------|------|------|
| **LangServe** | - | 将 Runnable 部署为 REST API |
| **add_routes()** | 添加路由 | FastAPI 集成 |
| **enable_playground** | Playground | 启用交互界面 |
| **invoke/stream/batch** | - | 自动支持所有 Runnable 方法 |
| **OpenAPI** | - | 自动生成 API 文档 |

---

## 十四、RAG 检索组件

| 术语 | 英文 | 解释 |
|------|------|------|
| **Retriever** | 检索器 | 返回相关 Document 列表 |
| **VectorStore** | 向量存储 | FAISS、Chroma、Milvus |
| **as_retriever()** | 转为检索器 | VectorStore → Retriever |
| **VectorStoreRetriever** | - | 基于向量相似度检索 |
| **MultiQueryRetriever** | - | 多角度查询扩展 |
| **ContextualCompressionRetriever** | - | 上下文压缩 |
| **ChainType** | 合并策略 | stuff / map_reduce / refine |
| **stuff** | 直接拼接 | 简单场景 |
| **map_reduce** | 分别生成再汇总 | 大量文档 |
| **refine** | 迭代精炼 | 追求精确 |

---

## 十五、Prompt Engineering 技巧

| 术语 | 英文 | 解释 |
|------|------|------|
| **Prompt Engineering** | 提示词工程 | 设计 Prompt 引导 LLM 输出 |
| **角色定义** | Role Definition | 设定专家身份 |
| **任务描述** | Task Description | 明确目标任务 |
| **Few-shot** | 少样本提示 | 提供示例引导输出格式 |
| **Chain-of-Thought** | 思维链 | 引导模型逐步推理 |

---

## LangChain 架构层级图

```
┌─────────────────────────────────────────────────────────────┐
│  LangSmith 可观测平台（追踪、评估、调试）                      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  LangServe 部署层（REST API）                                │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  LangGraph 图式工作流层                                      │
│  - StateGraph + Node + Edge                                 │
│  - Checkpointer 持久化                                       │
│  - Short-term / Long-term Memory                            │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Agent 自主决策层                                            │
│  - ReAct: Think → Act → Observe                             │
│  - Plan-and-Execute: Planner + Executor                     │
│  - AgentExecutor + Tool                                     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Chains 流程编排层                                           │
│  - LCEL: prompt | llm | parser                              │
│  - RunnableSequence / RunnableParallel                      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Prompt/Memory 输入构建层                                    │
│  - PromptTemplate + ChatPromptTemplate                      │
│  - ConversationMemory                                       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Model I/O 模型调用层                                        │
│  - BaseLanguageModel → LLM / ChatModel                      │
│  - invoke / stream / batch                                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  langchain-core 核心抽象层                                   │
│  - Runnable 统一接口                                         │
│  - LCEL 表达式语言                                           │
└─────────────────────────────────────────────────────────────┘
```
