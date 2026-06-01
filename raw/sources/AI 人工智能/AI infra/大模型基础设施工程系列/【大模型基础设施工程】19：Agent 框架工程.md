> 本文是【大模型基础设施工程】系列的第 19 篇。RAG 解决了”让模型知道”，Agent 解决的是”让模型会做”：从一句话自然语言需求出发，规划步骤、调用工具、观察结果、纠错重试，直到任务完成。本篇不做”agent 能改变世界”式的宏大叙事，只谈工程栈——抽象、框架、协议、沙箱、评测——以及在落地时真实踩过的坑。

## 一、从 ReAct 到 Agentic Reasoning：五年范式演进

### 1.1 时间线

Agent 并不是 2024 年才出现的概念，但 LLM 让它第一次工程可行。把过去几年的关键节点串起来看：

   
|年份|范式|代表作|核心想法|
|---|---|---|---|
|2022.10|ReAct|Yao 等，Princeton/Google|Reasoning + Acting 交错，推理和工具调用在同一个提示里|
|2023.03|Plan-and-Execute|BabyAGI、LangChain PlanAndExecute|先整体规划再逐步执行，降低短视|
|2023.03|AutoGPT|Significant-Gravitas|自驱动循环、写入长期记忆、文件系统操作|
|2023.05|Reflexion|Shinn 等，Noah|失败后写反思，写入 episodic memory|
|2023.06|Function calling|OpenAI|将”工具”从 prompt 里拆出来，进入 API 一等公民|
|2023.10|AutoGen|微软|多 agent 对话（Conversable Agent）|
|2024.01|CrewAI|João Moura|角色扮演 + 团队协作|
|2024.03|LangGraph|LangChain|图式状态机，取代传统 AgentExecutor|
|2024.10|Computer Use|Anthropic|像素级屏幕操作|
|2024.11|MCP|Anthropic|工具 / 资源的标准协议|
|2025.01|OpenAI Operator / Agents SDK|OpenAI|官方下场|
|2025.04|A2A|Google|Agent 间互操作协议|
|2025 起|Agentic Reasoning|o1、DeepSeek-R1、Claude 3.7 Thinking|推理过程本身就包含规划、反思、工具调用|

### 1.2 ReAct：所有 agent 的共同祖先

ReAct 的核心在于把**思考（Thought）**和**行动（Action）**写在一个 prompt 循环里：

```
Thought: 我需要查询北京今天的 PM2.5
Action: search[北京 PM2.5 今天]
Observation: 今日北京 PM2.5 约 48，良
Thought: 已获取，可以回答
Action: finish[北京今天 PM2.5 大约 48]
```

这种格式有三个工程优势：

- **可追踪**：每一步都是人类可读文本，日志天然就是 trace。
- **可中断**：在 `Action` 后面停下，由外部执行器去跑工具，结果注入 `Observation`。
- **可训练**：SFT 语料天然就是 `Thought/Action/Observation` 序列。

2023 年 OpenAI Function Calling 发布后，ReAct 的文本解析逐渐被**结构化 tool_call**取代，但循环本质未变。

### 1.3 Plan-and-Execute 与 Reflexion

ReAct 的缺点是**短视**：每一步都靠上一步的局部推理，面对多跳任务容易绕圈。Plan-and-Execute 先让 LLM 输出一个 JSON 计划，再按计划调度每一步；Reflexion 则在失败后插入一个”自我反思”步骤，把反思写入 episodic memory，下一次轮次读回来。

这两个思路如今已融进主流框架：LangGraph 里的 `plan → execute → replan` 子图、AutoGen 的 `GroupChatManager`、CrewAI 的 `Process.hierarchical`，本质都是 Plan-and-Execute 的变体。

### 1.4 Agentic Reasoning：推理模型吃掉一部分 agent 框架

2024 年底开始，o1、DeepSeek-R1、Claude 3.7 Thinking 把**长链推理**内化到模型本身——模型在回答前会生成几千到几万 token 的 `<thinking>` 块，里面就包含”规划—执行—反思”的完整循环。

这带来一个结构性变化：**框架层需要做的规划编排变少了**。很多在 GPT-4 时代必须用 LangGraph 显式展开的子图，在 R1/o1 上直接一次调用就能完成。这意味着：

- 单 agent + 强推理模型 + MCP 工具，胜过多 agent + 弱模型 + 复杂编排。
- 框架的重心从”帮模型思考”转向”帮模型执行”：工具路由、沙箱、可观测、记忆。

### 2.1 五个概念

不同框架叫法各异，但跑不出这五个核心对象：

- **Agent**：拥有 system prompt、模型、工具清单、记忆句柄的运行实体。
- **Task / Goal**：一次调用的输入与成功判定条件。
- **Tool**：一个带 schema 的可调用函数，签名决定了模型”能做什么”。
- **Memory**：跨调用持久化的上下文，分短期（会话缓冲）与长期（向量 / 图 / 文件）。
- **State Graph**：一组节点（agent、tool、router）+ 边（条件跳转）+ 全局状态字典。

### 2.2 短期记忆 vs 长期记忆

**短期记忆**就是多轮对话上下文，工程上有几种做法：

- 全量拼接：简单，上下文一爆就废。
- 滑动窗口：保留最近 N 轮。
- 摘要压缩：每到阈值触发一次 LLM 摘要（LangChain `ConversationSummaryMemory`）。
- 分段摘要 + Raw tail：最近几轮保留原文，历史摘要；质量最佳。

**长期记忆**则更分化：

   
|类型|存储|代表|适用|
|---|---|---|---|
|Vector memory|向量库|Mem0、Letta|语义相似检索|
|Episodic memory|结构化 JSON|Reflexion、MemGPT|“上次我做 X 失败了，原因是 Y”|
|Knowledge graph memory|图库|Zep、Graphiti|实体关系、时序演化|
|Document memory|文件系统|AutoGPT、Claude Code|大段文本，按路径访问|
|Procedural memory|代码|voyager skill library|“我学会的技能” 的代码片段|

工程上不必只选一种，生产级 agent 往往短期用摘要、长期用向量 + 图混合。

### 2.3 State Graph：新一代的 agent 运行时

传统 AgentExecutor 是一个 while 循环，控制流写死在代码里。问题是：

- 分支逻辑（比如”如果工具失败则回退到另一个工具”）必须 hack。
- Human-in-the-loop 中断点难以暴露。
- 多 agent 协作时，调用栈嵌套变成意大利面。

LangGraph、Pydantic Graph、OpenAI Agents SDK 的 handoff 等新一代框架统一改用**显式状态图**。节点是纯函数 `state -> state`，边是条件路由函数 `state -> node_name`，状态是一个 Pydantic / TypedDict，持久化到 checkpointer（内存、SQLite、Redis、Postgres 都行）。

这一套抽象的直接好处：**持久化、回放、时间旅行、人工介入**几乎免费获得。

## 三、框架全景：主流 10 家

### 3.1 LangChain / LangGraph

LangChain 是 2022 年底最早一批 LLM 框架，覆盖 Chain、Retriever、Agent、Tool、OutputParser 全套原语。2024 年后官方把 agent 部分独立为 **LangGraph**，核心抽象从 AgentExecutor 变为 StateGraph + Checkpointer。

选型建议：

- 需要复杂编排、需要 Human-in-the-loop、要接 LangSmith 的团队优先。
- 痛点是 API 变动频繁、类型偏弱、层层封装不易调试。

### 3.2 LlamaIndex

从 RAG 起家，Agent 是在 RAG 之上扩展的：`ReActAgent`、`FunctionCallingAgent`、`AgentWorkflow`。它的强项是**数据层**——超过 300 个 data loader 与超强的 document/node 抽象。

选型建议：

- 如果 agent 的主要工作是查询大量异构文档，LlamaIndex 的 `QueryEngineTool` + `AgentWorkflow` 组合很顺手。
- 如果任务主要是通用工具调用，LangGraph 更合适。

### 3.3 AutoGen（微软）

AutoGen 把 agent 建模为**可对话的实体**：任何 agent 都有 `send()` 和 `receive()`，多 agent 之间靠发消息协作。典型模式：

- `UserProxyAgent`（代表人类，也可自动回复）
- `AssistantAgent`（LLM）
- `GroupChatManager`（调度员）

2024 下半年的 **AutoGen 0.4** 大重构为 actor model，引入异步消息总线，更接近分布式系统的编程模型。微软自家的 `Magentic-One` 就建立在上面。

### 3.4 CrewAI

CrewAI 把 agent 拟人化：每个 Agent 有 `role`、`goal`、`backstory`；任务用 `Task` 对象；多个 agent 组成 `Crew`，支持 `sequential` 和 `hierarchical` 两种流程。

```
from crewai import Agent, Task, Crew

researcher = Agent(role="研究员", goal="找齐最新论文", backstory="...")
writer = Agent(role="写作者", goal="产出博文", backstory="...")

crew = Crew(agents=[researcher, writer], tasks=[task1, task2])
crew.kickoff()
```

优点是**心智模型直观**，做 demo 快；缺点是黑盒偏多、生产级可观测性弱、底层仍基于 LangChain。

### 3.5 DSPy

DSPy 的路线完全不同：它把 prompt 当成**可训练参数**。你声明 `Signature`（输入输出类型 + 描述），框架自动生成 prompt，然后用训练集 + metric 去**优化 few-shot 和指令**。

```
class GenerateAnswer(dspy.Signature):
    """Answer questions with short factoid answers."""
    context = dspy.InputField()
    question = dspy.InputField()
    answer = dspy.OutputField()
```

适合**有评测集、想把 prompt 工程自动化**的团队。DSPy 也支持 ReAct 和 tool use，但重点始终是”编译 prompt”。

### 3.6 Pydantic AI

Pydantic AI 是 Pydantic 作者 Samuel Colvin 2024 年推出的框架，卖点是**类型安全**。tool 就是 `@agent.tool` 装饰器，输入输出是 Pydantic model，结构化输出直接走 `result_type`。对 Python 生态重度用户非常友好。

### 3.7 OpenAI Agents SDK（前 Swarm）

OpenAI 在 2024 年底先发布了 Swarm（实验性），2025 年初升级为正式的 **Agents SDK**。核心概念只有两个：

- **Agent**：system prompt + tools + model
- **Handoff**：一个 agent 可以把控制权交给另一个 agent

它故意做得很”薄”，不引入 LangGraph 式的状态图，官方哲学是”让模型自己决定路由”。配合 Responses API + Built-in tools（web search、file search、computer use）可以快速搭建。

### 3.8 Anthropic Claude SDK 与 Computer Use

Anthropic 的官方 SDK 虽然不像 OpenAI Agents SDK 那样强调”agent 框架”，但它提供了两个关键能力：

- **Tool use** 原生支持并行 tool_call
- **Computer use**：Claude 3.5 Sonnet 及以上可以接受屏幕截图、返回鼠标键盘事件

Computer Use 通常搭配一个 Docker 容器 + VNC + Python 控制层（Anthropic 官方的 `anthropic-quickstarts/computer-use-demo`）。

### 3.9 Smolagents（HuggingFace）

HuggingFace 2024 末推出的极简 agent 框架，主打**代码即动作**（CodeAgent）——让 LLM 直接输出 Python 代码，在沙箱里执行，而不是 JSON tool call。这种模式在多步骤数值与数据处理任务上比 function calling 更强，因为 LLM 可以用变量、循环、条件表达复杂逻辑。

### 3.10 国产框架与平台

- **字节 Coze / 扣子**：低代码 agent 平台，节点式工作流 + 插件市场 + 知识库 + 多 bot，面向 C 端和轻量 B 端场景最快的选择。国内版、国际版（coze.com）双站。
- **阿里百炼 Assistant API**：对齐 OpenAI Assistants，托管 thread、RAG、Code Interpreter，底座支持通义千问全家桶。
- **百度千帆 Agent**：与千帆 ModelBuilder 深度集成，支持可视化编排 + 文心系列。
- **腾讯元宝 / 混元助手**：对外提供混元模型 + 知识库 + agent 编排。
- **MetaGPT**：上海 DeepWisdom 开源的多 agent 协作框架，用”软件公司”的角色隐喻（产品经理、架构师、工程师）。
- **AutoGPT 中文分支 / AgentGPT-CN**：多个社区维护版本，接入国产模型与国内搜索 API。
- **LazyLLM（商汤）、Agently**：较新，面向国内工程生态。

### 4.1 四种常见拓扑

- **单 Agent**：默认选择，调试最容易。不到必要不要加 agent 数量。
- **Manager-Worker**：Manager 做规划，把子任务派给 Worker；适合任务能清晰拆分的场景（写报告、抓数据）。
- **Hierarchical**：多层级，比如 MetaGPT、CrewAI hierarchical process。复杂度高，仅在长周期项目里合算。
- **Debate / Swarm**：平权协作，靠互相审稿达成一致；对提升事实准确率有效，但成本高。

### 4.2 什么时候应该多 agent

工程上多 agent 合理的三个条件：

1. **不同角色需要不同 system prompt / 不同模型**：比如代码用 Claude、写作用 GPT、审阅用 DeepSeek。
2. **上下文隔离**：Worker 只看自己的子任务，避免”大上下文污染”。
3. **可并行**：多 worker 可以并发跑，显著缩短 wall-clock 时间。

如果只是为了”架构看起来漂亮”而多 agent，几乎总是退步。

## 五、记忆系统：MemGPT、Letta、Mem0、Zep

### 5.1 MemGPT / Letta

MemGPT（2023，UC Berkeley）把 LLM 上下文窗口类比为”RAM”，把外部存储类比为”硬盘”，让 LLM 通过 tool call 主动把信息换入换出——这就是”memory paging”。Letta 是其后续产品化项目，提供托管 agent 服务。关键能力：

- Core memory（永远在 prompt 里）
- Recall memory（完整对话历史，可检索）
- Archival memory（外部知识，向量检索）

### 5.2 Mem0

Mem0 定位更轻量：一个 Python 库，配一个可选云服务。特点是把”记忆”抽象成三条基本操作：`add` / `search` / `update`，底层可以用 Qdrant、pgvector、Neo4j 等。

```
from mem0 import Memory
m = Memory()
m.add("我对芒果过敏", user_id="alice")
m.search("过敏史", user_id="alice")
```

### 5.3 Zep / Graphiti

Zep 2024 末推出 Graphiti——一个**时序知识图谱记忆**系统。它会把对话抽取为（实体、关系、时间区间）三元组，图上还记录 `valid_from / valid_to`，可以回答”去年三月他住在哪里”这类时序问题。适合需要长期跟踪事实变化的 agent（客服、私人助理、医疗）。

## 六、Agent 工程四大难题

### 6.1 错误累积

Agent 每一步的准确率假设是 95%，10 步后只剩 。工程对策：

- **减少步数**：提高单步能力（用更强的模型、更精的 prompt）远比加长链路有效。
- **显式校验节点**：每隔几步插入 verifier（规则或 LLM-as-judge）。
- **可回退状态**：Checkpointer + rollback，发现失败时回到最近的 good state。

### 6.2 工具选择错误

工具一多，LLM 就会混：“search 还是 search_web 还是 google_search？”对策：

- **控制工具数量**：单次调用暴露的工具 ≤ 10，按场景动态加载。
- **清晰命名 + 描述**：每个 tool 的 description 写清”什么时候用、什么时候别用”。
- **分层路由**：先让 router agent 选子 agent，再由子 agent 选具体 tool。

### 6.3 长链路成本失控

一次 agent run 跑掉几美元、几十万 token 的例子比比皆是。监控维度：

- 每次 run 的总 token / 总调用次数 / wall-clock。
- p95 / p99 的分布，长尾 run 往往是死循环。
- 设置 **max_iterations**、**budget cap**（比如超过 $0.5 立即终止）。

### 6.4 不可观测

不插桩的 agent 出问题基本 debug 不出来。必备三件套：

- **Trace**：每一步的输入/输出/耗时/token（LangSmith、Langfuse、AgentOps、Phoenix）。
- **事件流回放**：能基于 checkpointer 重放一次 run。
- **评测集**：固定一批 case，CI 跑分回归。

## 七、Agent 协议化：MCP、A2A、ANP、AG-UI

### 7.1 MCP（Model Context Protocol）

Anthropic 2024 年 11 月开源，定位是**“Agent 世界的 USB-C”**。客户端（Claude Desktop、Cursor、Continue、Cline 等）通过 JSON-RPC 连接 MCP Server，Server 暴露三类原语：

- **Tools**：可调用函数
- **Resources**：可读的 URI（文件、数据库行、API endpoint）
- **Prompts**：预置 prompt 模板

生态在 2025 年爆发式扩张，GitHub、Notion、Slack、Figma、各大数据库都有官方或社区 MCP server，估计已超过 3000 个。详见下一篇第 20 节。

### 7.2 A2A（Agent-to-Agent Protocol）

Google 2025 年 4 月发布，解决的不是 agent 调工具，而是 **agent 调 agent**。核心概念：

- **Agent Card**：一个 `/.well-known/agent.json`，声明能力、endpoint、认证方式。
- **Task**：A2A 的基本交互单元，有 ID、状态机（submitted / working / input-required / completed / failed）。
- **Streaming**：支持 SSE 流式事件，长任务异步推进。

A2A 与 MCP 的关系：MCP 让 agent **用工具**，A2A 让 agent **雇 agent**。两者互补，不排斥。

### 7.3 ANP 与 AG-UI

- **ANP（Agent Network Protocol）**：中国开源社区发起，强调去中心化身份（DID）、端到端鉴权，愿景是一张”Agent 公网”。目前实现与生态还在早期。
- **AG-UI**：把 agent 侧事件流标准化给前端，使得”LLM chat UI / agent dashboard”可以复用一套协议（类似 LSP 之于编辑器）。CopilotKit 是主要推动方。

### 7.4 协议之间的关系图

可以把三者近似理解成三层：

- **AG-UI**：UI ↔︎ Agent 的事件协议（渲染、交互、流式）
- **MCP**：Agent ↔︎ Tool 的能力协议（做事的手）
- **A2A**：Agent ↔︎ Agent 的协作协议（换人的嘴）

三者解耦，各自演进，2025 年已基本成为行业共识。ANP 解决的是更底层的”agent 在公网如何认身份”，属于 PKI 级别的扩展。

### 7.5 MCP 上手：10 分钟写一个 Server

```
# server.py
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("weather")

@mcp.tool()
def get_weather(city: str) -> dict:
    """查询某城市当前天气（示意）。"""
    return {"city": city, "temp_c": 22, "cond": "clear"}

@mcp.resource("weather://alerts")
def list_alerts() -> str:
    return "无预警"

if __name__ == "__main__":
    mcp.run()
```

在 Claude Desktop 的配置里加上：

```
{
  "mcpServers": {
    "weather": {"command": "python", "args": ["/path/to/server.py"]}
  }
}
```

重启客户端，`get_weather` 就出现在工具列表里。对于企业内部工具，这意味着”写一次，到处可用”——今天给 Claude 用，明天同样的 server 给 Cursor、Cline、自建 agent 用，不需要改一行。

## 八、沙箱与执行环境

Agent 一旦会写代码、能下载文件、会 shell，就必须跑在沙箱里。按隔离度排序：

|方案|隔离度|启动|用途|
|---|---|---|---|
|同进程 exec()|几乎没有|毫秒|绝对不要|
|Docker|容器级|秒|自托管，简单场景|
|gVisor|内核级用户态|秒|强隔离 Python|
|Firecracker microVM|硬件虚拟化|100ms 级|AWS Lambda 同款|
|E2B|云托管 Firecracker|150ms|SaaS 首选|
|Daytona|自托管 / 云双模|亚秒|开发环境沙箱|
|Modal|Serverless Python|秒级冷启动|GPU / 重载计算|

**E2B** 是当前 agent 沙箱里最主流的 SaaS，Anthropic、Perplexity、Cognition 等都在用。核心卖点：

- 每个 sandbox 都是独立 Firecracker VM，毫秒级启动。
- 内置文件系统、浏览器、桌面环境。
- Python / Node SDK：`sandbox.commands.run("ls")` 一行搞定。

自托管场景下最务实的组合仍然是 **Docker + cgroup limits + 只读 rootfs + 无网络或白名单出口**。

## 九、浏览器 / 计算机控制

### 9.1 Browser Use

**Browser Use** 是 2024 末火起来的开源库：基于 Playwright + LLM，把网页 DOM 可见元素编号后喂给模型，让模型输出”点第 N 个元素”“在第 M 个 input 填 X”。开源、可自托管，生态活跃。

```
from browser_use import Agent
from langchain_openai import ChatOpenAI

agent = Agent(task="在 arxiv 上找 2025 年 RLHF 新论文并列出标题",
              llm=ChatOpenAI(model="gpt-4o"))
await agent.run()
```

### 9.2 Playwright MCP

微软官方把 Playwright 暴露成 MCP server，使任何 MCP 客户端（Claude Desktop、Cursor）都能自然语言控制浏览器。适合**让编辑器具备浏览能力**的场景，而不是自建 agent。

### 9.3 Anthropic Computer Use / OpenAI Operator

区别于 Browser Use 的 DOM 模式，**Computer Use** 和 **Operator** 走的是**视觉 + 键鼠**路线：

- 模型看屏幕截图。
- 输出 `click(x,y)` / `type(text)` / `scroll(dy)` 等原子动作。
- 通用性强（任何 GUI 应用），但延迟高、成本高、准确率不如 DOM 模式。

### 9.4 ChatGPT Agent / Claude Code / Cursor Agent

这三个是 **端到端 agent 产品**，而不是框架：

- **ChatGPT Agent**（2025）：浏览器 + 代码 + 文件，通用任务。
- **Claude Code**：CLI 形态，专注软件工程，`agent` 概念内嵌（subagent、skills）。
- **Cursor Agent / Windsurf Cascade**：编辑器形态，以 repo 为上下文，planner + executor 双 agent。

做选型时要区分：自己搭 agent 框架，还是用现成 agent 产品 + 它们的 API/SDK 二次封装。大多数企业应用后者性价比更高。

## 十、评测：Agent 怎么打分

   
|基准|场景|核心指标|代表成绩（2025）|
|---|---|---|---|
|SWE-bench Verified|真实 GitHub issue 修复|通过率|顶级 65–70%|
|τ-bench（Tau）|用户-agent-商家三方对话|任务完成率 + 规则遵守|55–75%|
|AgentBench|8 种环境综合|综合得分|闭源模型领先|
|WebArena / VisualWebArena|真实网页任务|success rate|35–50%|
|GAIA|需要规划+工具的通用任务|三级难度通过率|L1 80%+，L3 40%+|
|OSWorld|桌面级任务|任务完成率|20–40%|
|SWE-Lancer（中文场景可自建变体）|软件工程竞标|美元价值|前沿模型显著领先|

自建评测的工程要点：

- **场景闭合**：每个 case 要有**机器可验证**的成功判定。
- **反作弊**：避免 test leakage，定期刷新。
- **趋势而非绝对值**：同一 harness 下版本间对比才有意义。

## 十一、Agent 基础设施即服务

生产 agent 离不开这几类基础设施 SaaS：

- **AgentOps**：专门为 agent trace 的分析平台，session replay、成本归因。
- **LangSmith**：LangChain 官方，trace + 评测 + prompt hub 一体。
- **Langfuse**：开源优先，可自托管，trace + prompt 管理 + 评测。
- **Helicone**：反向代理模式，改一行 base_url 就开始记录。
- **Phoenix（Arize）**：OpenTelemetry 原生，可私有化。

选型的关键问题：**数据留存**。如果 prompt/response 涉及用户隐私或商业数据，优先选能自托管的（Langfuse、Phoenix）。

## 十二、代码示例

### 12.1 LangGraph：10 行的搜索 + 总结 agent

```
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
tools = [TavilySearchResults(max_results=5)]
agent = create_react_agent(llm, tools)

result = agent.invoke({
    "messages": [("user", "总结 2025 年 Q1 关于 MoE 训练的 3 个新进展")]
})
print(result["messages"][-1].content)
```

底层其实是一张两节点状态图：`agent → tools → agent → END`。想要更复杂行为（校验、重试、人工介入）只需在图上加节点和边。

### 12.2 LangGraph：显式状态图 + Checkpointer

```
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
import operator

class S(TypedDict):
    messages: Annotated[list, operator.add]
    plan: list[str]
    step: int

def planner(s: S):
    plan = ["搜索最新论文", "按机构分组", "提炼共性结论"]
    return {"plan": plan, "step": 0}

def executor(s: S):
    task = s["plan"][s["step"]]
    return {"messages": [f"完成: {task}"], "step": s["step"] + 1}

def router(s: S):
    return END if s["step"] >= len(s["plan"]) else "executor"

g = StateGraph(S)
g.add_node("planner", planner)
g.add_node("executor", executor)
g.set_entry_point("planner")
g.add_edge("planner", "executor")
g.add_conditional_edges("executor", router, {"executor": "executor", END: END})

app = g.compile(checkpointer=SqliteSaver.from_conn_string("agent.db"))
app.invoke({"messages": []}, config={"configurable": {"thread_id": "run-1"}})
```

Checkpointer 让这张图天然支持断点续跑、时间旅行、人工介入。

### 12.3 AutoGen：两个 agent 对话

```
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient

model = OpenAIChatCompletionClient(model="gpt-4o")
coder = AssistantAgent("coder", model_client=model, system_message="你写 Python")
critic = AssistantAgent("critic", model_client=model, system_message="你审代码，最多 3 轮")

team = RoundRobinGroupChat([coder, critic], max_turns=6)
await team.run(task="写一个 LRU 缓存，支持 TTL")
```

### 12.4 CrewAI：团队版

```
from crewai import Agent, Task, Crew, Process

researcher = Agent(role="研究员", goal="找齐材料", backstory="资深情报分析",
                   tools=[search_tool], llm=llm)
writer = Agent(role="写作者", goal="输出博文", backstory="技术编辑", llm=llm)

t1 = Task(description="调研 MCP 生态现状", agent=researcher, expected_output="要点清单")
t2 = Task(description="写 800 字博文", agent=writer, expected_output="markdown")

crew = Crew(agents=[researcher, writer], tasks=[t1, t2], process=Process.sequential)
print(crew.kickoff())
```

### 12.5 OpenAI Agents SDK：handoff

```
from agents import Agent, Runner

triage = Agent(name="triage", instructions="把请求路由给合适的专家",
               handoffs=[billing_agent, tech_agent])
result = Runner.run_sync(triage, "我上周的账单多扣了 30 元")
print(result.final_output)
```

### 12.6 Coze 工作流：低代码搭建

Coze 里搭一个”每天早上总结 arxiv 最新 AI 论文并发到飞书”的 agent：

```
[定时触发 08:00]
  ↓
[HTTP 插件] GET arxiv API（cs.CL，最近 24h）
  ↓
[LLM 节点] 系统提示：筛选 5 条最有价值 + 翻译成中文
  ↓
[知识库写入] 入库 tag=daily-arxiv
  ↓
[飞书机器人] 推送到「AI 日报」群
```

全程无代码，30 分钟能搭完；国内侧可直连豆包/DeepSeek，对接飞书、钉钉、企微插件齐全。缺点是黑盒逻辑改动受限，复杂业务迟早要自建。

## 十三、Mermaid：典型 ReAct 循环与 LangGraph 状态机

### 13.1 ReAct agent 循环

### 13.2 LangGraph 多 agent 状态机

## 十四、选型速查

|场景|推荐|
|---|---|
|个人试玩 / demo|OpenAI Agents SDK、Smolagents|
|国内低代码快速上线|Coze、百炼 Assistant、千帆 Agent|
|复杂编排 + 可观测|LangGraph + LangSmith/Langfuse|
|多 agent 协作|AutoGen、CrewAI|
|类型安全 Python 后端|Pydantic AI|
|prompt 自动优化|DSPy|
|大量文档 RAG + agent|LlamaIndex|
|浏览器自动化|Browser Use（DOM）、Computer Use（视觉）|
|强安全隔离|E2B / Daytona / Firecracker 自托管|
|记忆系统|短期=摘要；长期=Mem0 / Letta / Zep|
|跨 agent / 跨厂商互通|MCP（工具）+ A2A（agent）|

## 十五、深入：四个容易被忽视的工程点

### 15.1 Tool schema 设计的具体规则

一个 agent 的上限，很大程度由 tool schema 的清晰度决定。经验法则：

- **名字动宾化**：`search_papers`、`create_ticket`，而不是 `paper`、`ticket_op`。
- **描述里写「反例」**：“不要用此工具搜索内部代码库，那应该用 `search_repo`”——这比正例更能降低误用率。
- **参数最少化**：可选参数越多，模型漏填/错填的概率越高。能给默认值就给。
- **输出结构固定**：`{status, data, error}` 三段式优于裸返回；给 LLM 稳定的解析契约。
- **错误要可解释**：`PermissionError: user 'alice' lacks 'write' on repo 'foo'` 远好于 `403 Forbidden`，模型看到后能自己决定换工具或求助用户。

### 15.2 并行工具调用

OpenAI、Anthropic、Gemini、Qwen 都已原生支持一次响应中返回多个 tool_call，客户端并发执行后把多个 tool_result 一次性回送。工程上要注意：

- **幂等性**：并发的工具必须是幂等或无副作用（查询类）；写操作并发很容易出脏数据。
- **限流聚合**：并发会让 RPS 暴涨，务必在 tool executor 层做 token bucket。
- **失败隔离**：一个 tool 异常不能让整个并行批次失败，要分别把 success/error 封装回模型。
- **观测维度**：把 “并行度”、“并行批次耗时”、“最慢一个” 分开记录。

### 15.3 Human-in-the-loop 的三种姿势

Agent 接入人工介入有三种层次，成本递增：

- **审批门**：执行前暂停，等待一次 yes/no（高风险动作如删除、支付、发邮件）。LangGraph `interrupt_before=["tool_node"]` 原生支持。
- **协同编辑**：agent 产出草稿，人类修改，再让 agent 继续。Claude Code / Cursor Agent 的 apply-edit 流就是这模式。
- **纠偏反馈**：人类以自然语言指出错误，agent 改写 plan 并重试；需要支持图状态的回溯与分叉。

没有 human-in-loop 机制的 agent 只能做**低权限、可撤销**的动作；一旦触碰不可撤销操作，必须加门。

### 15.4 成本与延迟的实操约束

一张对标表，经验值（2025 中）：

   
|动作|典型 token|典型耗时|备注|
|---|---|---|---|
|单次 LLM 调用（ReAct 一步）|3k in / 500 out|2–6s|取决于模型与上下文|
|一次工具调用 + observation|+1k|+0.2–2s|外部 API 延迟是大头|
|一次完整 agent run（5–15 步）|30k–200k|20s–3min|长尾易失控|
|浏览器截图一次 computer use|+2k（截图 base64）|+1–3s|视觉模型推理慢|
|Code interpreter 一次 exec|0 tokens|0.5–30s|Python 冷启动 + 执行|

由此得到几条务实守则：

- **绝不给 agent 无限预算**。必有 `max_iterations`、`max_tokens`、`max_seconds`、`max_usd` 四道闸。
- **能缓存就缓存**：tool 结果按参数 hash 缓存；相同 prompt prefix 用 prompt caching（Anthropic、OpenAI、DeepSeek 都已支持）。
- **优先短链路**：一个能 3 步跑完的任务，不要设计成 10 步。

## 十六、一个端到端落地样例：企业知识库助手

下面把前面抽象的东西落成一个能上线的方案。

### 16.1 需求

- 企业内知识库（Confluence、飞书文档、Git wiki）聚合检索。
- 用户在 IM 里自然语言提问，agent 回答并给出引用。
- 复杂问题（跨文档、需要写代码统计）能分步回答。
- 要求：p95 < 8s，单次成本 < ¥0.1，所有 trace 可追溯。

### 16.2 架构选型

- **Router Agent**：极小模型（Qwen3-0.6B 或 GPT-4o-mini），只做意图分类，<200ms。
- **RAG Agent**：走标准 RAG + rerank，单次 LLM 调用即可出答案。
- **Worker Agent**：LangGraph 状态机，可调 `run_sql`、`run_python`（E2B 沙箱）、`search_docs`。
- **Gateway**：第 22 篇主题，统一鉴权、限流、计费、trace 注入。
- **Langfuse**：自托管，留存所有 prompt/response/tool_call。

### 16.3 关键工程细节

- **缓存层**：对 RAG 查询做 embedding-hit 缓存，命中率一般 30%+。
- **权限**：每份文档都带 ACL，检索前以 `user_id` 过滤；漏掉就是数据泄露事故。
- **幻觉抑制**：强制 agent 只能引用检索到的片段，开启 citation 模式；答案里没有 `[doc#N]` 的段落丢弃重答。
- **降级**：Worker 超预算时自动退化为 RAG Agent，返回”本问题较复杂，以下是可能相关文档”。
- **评测**：每周从真实 trace 中随机采样 50 条，人工标注准确率，作为下一次模型升级的门槛。

### 16.4 选择框架

同一需求，三种合理实现：

- **LangGraph + 自建**：灵活，上线需要 2–4 周。
- **百炼 Assistant / Coze**：1 周内能跑起来，但权限模型要多做一层适配。
- **Dify 自托管**：折中，开源可改造，生态成熟；知识库、工作流、RAG 开箱即用。

选哪条路取决于团队规模与长期规划。**不要为了短期而锁死在只支持某家模型的平台上**——在大模型价格每年腰斩、能力每半年翻倍的节奏下，可替换性比”今天就跑起来”更重要。

## 十七、前沿趋势

几个正在发生、2026 很可能主导 agent 工程的方向：

### 17.1 Agentic Reasoning 内化

推理模型把”思考—工具—反思”塞进一次 generate 调用。对框架的影响：**更薄的编排 + 更厚的工具层**。框架会收敛到：

- 一个 session / memory
- 一组 MCP 工具
- 一个推理模型

LangGraph 里那些手写的 reflection 子图会慢慢变成反模式。

### 17.2 Agent 市场

MCP server 市场（Smithery、mcp.so、glama）+ A2A agent 市场正在形成。未来三年可能出现”Agent Store”——为某个垂直领域付费订阅一个远程 agent，像今天订阅 SaaS 一样。

### 17.3 长时运行 agent

当前 agent 主要解决”单次任务”（几秒到几分钟）。下一步是”持续运行 agent”（小时/天/周），代表形态：

- 后台巡检（Ops agent 盯着告警）
- 个人助理（跨天跨上下文的代办管理）
- 研究代理（deep research 模式，跑几小时给一份报告）

这类 agent 对**记忆、成本预算、可中断可恢复**提出比现在高一个数量级的要求。

### 17.4 多模态 agent

视觉 + 语音 + 动作统一进入 agent 循环。表现形式包括：

- 桌面 agent（Computer Use、Operator）
- 物理 agent（VLA 模型，机器人领域，参考 Figure、Physical Intelligence）
- 视频理解 agent（解析长视频、做剪辑）

Agent 框架将承担”把这些模态统一接入工具图”的职责。

### 17.5 Agent 的安全与对齐

Agent 带来的安全风险远超 chatbot：

- **Prompt injection via tool output**：工具返回的内容里藏指令，让 agent “代为”执行恶意动作（读私信、转账）。
- **数据外泄**：agent 可能把内部数据当作上下文喂给第三方工具。
- **不可撤销动作**：支付、发邮件、删除文件等需要强审批链。

工程上正在出现专门的**Agent Firewall / Guardrail** 产品（Lakera、Protect AI、国内的有瑞莱智慧等），走反向代理或 SDK 插桩两条路线。这部分将在第 24 篇详细展开。

## 十八、实战：一次真实的 debug 过程

为了让”可观测”“错误累积”这类抽象概念落地，我复述一次真实排查：线上客服 agent 偶发”答非所问”，约 2% 的 session 触发。

### Step 1. 先看 trace 面板

Langfuse 里按失败标签过滤，发现失败 case 有共性：模型调用次数都在 6+，而正常 case 平均 2–3 次。初步判断是**死循环或错误累积**。

### Step 2. 抽一条失败 session 做 replay

基于 LangGraph Checkpointer 回放，看到如下片段：

```
step 1 tool_call: search_kb(q="发票怎么开")      -> ok, 3 docs
step 2 tool_call: search_kb(q="开发票")          -> ok, 3 docs（和上一步 90% 重叠）
step 3 tool_call: search_kb(q="开发票 流程")     -> ok, 3 docs（还是类似）
step 4 tool_call: search_kb(q="开发票 步骤")     -> ok, 3 docs
step 5 tool_call: search_kb(q="开票")            -> ok
step 6 final:      "抱歉我暂时找不到相关信息…"
```

很明显：模型陷入”换关键词重试”循环，其实第一次就拿到了答案，只是答案对模型来说不够”明显”。

### Step 3. 根因

- RAG top-k 返回片段里，核心信息埋在第二段，首段是无关的目录。
- system prompt 里写了 “如果信息不足就继续搜索”，却没写 “不要用同义词反复搜相同问题”。
- agent 缺少 dedup：两次高度相似的查询应该合并。

### Step 4. 修复

三处改动：

1. **Reranker**：在检索之后加一层交叉编码器 rerank（bge-reranker-v2），把最相关片段顶到第一。
2. **改 prompt**：加一句”如你已经搜过近义问题，不要再以同义词重复搜索；如果信息不足请向用户追问”。
3. **工具层 dedup**：search_kb 内部对最近 N 次查询做 embedding 相似度去重，相似度 > 0.9 的返回缓存结果并注明”与前次查询相似”。

### Step 5. 回归

在评测集 200 条里跑回归，原先的 2% 死循环 case 降到 0；顺便整体准确率 +4%。上线后一周监控，p95 延迟下降 1.8s，平均 token 消耗下降 35%。

**这个例子里真正起作用的不是”更好的模型”，而是”能看见 trace 才能找到问题”**。这就是为什么我在前面反复强调可观测性。

本篇走完了 agent 工程的主要面：范式演进、抽象模型、主流框架、多 agent 拓扑、记忆、协议、沙箱、浏览器控制、评测与基础设施。几条工程上反复验证的经验：

- **强模型 + 简单框架 > 弱模型 + 复杂编排**。当 R1/o1/3.7 Thinking 能在一次调用里完成规划—执行—反思，多数 LangGraph 子图其实可以删掉。
- **MCP 是 2025 年 agent 工程的最重要事实标准**。下一篇会专门展开。
- **多 agent 不是越多越好**。当单 agent 能解时，不要上 GroupChat。
- **可观测性从第 0 天就要做**。没有 trace 的 agent 等于没有日志的分布式系统。
- **沙箱是底线不是锦上添花**。任何会跑代码/访问外网的 agent，都必须隔离。

下一篇将聚焦**工具调用与 MCP**：工具 schema 设计、并行 tool_call、MCP server 工程实践、跨 agent 互操作的具体协议细节。

## 十九、附录：常见开源 agent 项目速览

以下是 2025 年工程界真实在用的开源项目清单，按用途分类：

### 19.1 通用 agent 框架

- **LangChain / LangGraph**（Python、JS）：github.com/langchain-ai/langchain
- **LlamaIndex**（Python、TS）：github.com/run-llama/llama_index
- **AutoGen**（Python，微软）：github.com/microsoft/autogen
- **CrewAI**（Python）：github.com/crewAIInc/crewAI
- **Pydantic AI**（Python）：github.com/pydantic/pydantic-ai
- **DSPy**（Python、Stanford NLP）：github.com/stanfordnlp/dspy
- **Smolagents**（Python、HuggingFace）：github.com/huggingface/smolagents
- **Agno / Phidata**（Python）：go.to agno-agi/agno
- **Atomic Agents**（Python）：轻量对 schema 友好

### 19.2 多 agent / 软件工程向

- **MetaGPT**（上海 DeepWisdom）：github.com/geekan/MetaGPT
- **OpenDevin / OpenHands**：软件工程 agent，SWE-bench 一线选手
- **SWE-agent**（Princeton）：修 GitHub issue 的专用 agent
- **Devin**（Cognition 闭源）、**Replit Agent**、**GitHub Copilot Workspace**

### 19.3 浏览器 / 计算机控制

- **Browser Use**：github.com/browser-use/browser-use
- **Stagehand**（Browserbase）：TS，基于 Playwright
- **Skyvern**：表单自动化
- **WebVoyager**、**Agent-E**：学术参考实现
- **anthropic-quickstarts / computer-use-demo**：Anthropic 官方 demo

### 19.4 低代码 / 平台

- **Dify**（苏州语灵）：github.com/langgenius/dify，国内最火自托管平台
- **FastGPT**（Labring）：RAG + agent，易部署
- **Flowise**、**LangFlow**、**n8n（AI 节点）**：拖拽式
- **Coze Studio（字节开源版）**：2025 年字节开源了 Coze 部分核心
- **Bisheng**、**RAGFlow**：国产企业向

### 19.5 记忆 / 存储

- **MemGPT / Letta**：github.com/letta-ai/letta
- **Mem0**：github.com/mem0ai/mem0
- **Zep / Graphiti**：github.com/getzep/zep，graphiti
- **Motorhead**（Metal）：Redis 记忆

### 19.6 沙箱与执行

- **E2B**（开源 SDK + 云服务）：github.com/e2b-dev/e2b
- **Daytona**：github.com/daytonaio/daytona
- **Open Interpreter**：本地 code interpreter
- **Jupyter Kernel Gateway**：把 Jupyter 变 agent 沙箱

### 19.7 观测与评测

- **Langfuse**：github.com/langfuse/langfuse
- **Arize Phoenix**：github.com/Arize-ai/phoenix
- **AgentOps**：github.com/AgentOps-AI/agentops
- **Helicone**：github.com/Helicone/helicone
- **OpenLLMetry**（Traceloop）：OpenTelemetry 扩展
- **Inspect AI**（UK AISI）：评测框架，政府级合规

### 19.8 协议与互操作

- **MCP SDK**（Python / TS / Go / Rust 官方实现）：github.com/modelcontextprotocol
- **MCP server 合集**：github.com/modelcontextprotocol/servers
- **A2A SDK**（Google）：github.com/google-a2a/a2a-python
- **ANP（Agent Network Protocol）**：社区项目
- **CopilotKit / AG-UI**：前端侧协议与组件

## 二十、工程检查清单

把一个原型 agent 推到生产前，请过一遍这份清单：

**稳定性**

- 单次 run 有 `max_iterations`、`max_tokens`、`timeout`、`max_cost` 四重熔断
- 每个工具都有独立超时与重试策略
- 工具失败时有明确降级路径（换工具 / 退化为纯 LLM / 交人工）
- 状态可持久化，断点可续跑

**安全**

- 工具按用户身份授权（不能 agent 以系统身份为所欲为）
- 工具输出经过 prompt injection 过滤（至少剥离常见注入模式）
- 不可撤销动作（支付、删除、发邮件）强制人工审批
- 代码执行在沙箱中，无默认出网权限
- 敏感字段（手机号、身份证、密钥）出入站脱敏

**可观测**

- 每次 run 都写 trace，能按用户 / session / tool 聚合
- prompt/response 留存（注意合规，考虑脱敏 + TTL）
- 成本面板按租户 / agent / tool 拆分
- 告警：失败率、p95 延迟、单 run 成本异常

**质量**

- 有自动评测集，CI 跑分
- 有人工评测回流到评测集的机制
- 线上采样回看频率 ≥ 每周
- Prompt 与模型版本有 registry，能灰度回滚

**成本**

- 启用 prompt caching（Anthropic / OpenAI / DeepSeek）
- 小模型做 router，大模型做兜底
- 工具结果按参数 hash 缓存
- 允许异步 batch（非实时任务走便宜通道）

**协议化**

- 工具逐步迁移到 MCP，降低重复集成
- 外部 agent 协作留 A2A 口子
- 前端事件流遵循 AG-UI 或类似规范

过完上面 25 条，你的 agent 才真正配得上叫”基础设施”。

## 二十一、小结

本篇走完了 agent 工程的主要面：范式演进、抽象模型、主流框架、多 agent 拓扑、记忆、协议、沙箱、浏览器控制、评测与基础设施。几条工程上反复验证的经验：

- **强模型 + 简单框架 > 弱模型 + 复杂编排**。当 R1/o1/3.7 Thinking 能在一次调用里完成规划—执行—反思，多数 LangGraph 子图其实可以删掉。
- **MCP 是 2025 年 agent 工程的最重要事实标准**。下一篇会专门展开。
- **多 agent 不是越多越好**。当单 agent 能解时，不要上 GroupChat。
- **可观测性从第 0 天就要做**。没有 trace 的 agent 等于没有日志的分布式系统。
- **沙箱是底线不是锦上添花**。任何会跑代码/访问外网的 agent，都必须隔离。
- **协议化是红利**：MCP 让工具复用，A2A 让 agent 复用，AG-UI 让前端复用。尽量把自有能力往这三个标准上靠。
- **评测比调参更重要**：没有评测集的优化就是盲调；建立评测集比学会新框架更能提升交付质量。
- **可替换性优先**：不要为了 “今天就上线” 把团队锁死在某个模型/平台上，半年后价格腰斩或更强模型出来时会后悔。

下一篇将聚焦**工具调用与 MCP**：工具 schema 设计、并行 tool_call、MCP server 工程实践、跨 agent 互操作的具体协议细节。

## 参考资料

- Yao et al., _ReAct: Synergizing Reasoning and Acting in Language Models_, 2022
- Shinn et al., _Reflexion: Language Agents with Verbal Reinforcement Learning_, 2023
- Packer et al., _MemGPT: Towards LLMs as Operating Systems_, 2023
- Wu et al., _AutoGen: Enabling Next-Gen LLM Applications_, 微软，2023
- Khattab et al., _DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines_, 2023
- Wang et al., _Voyager: An Open-Ended Embodied Agent with Large Language Models_, 2023
- Xi et al., _The Rise and Potential of Large Language Model Based Agents: A Survey_, 2023
- Anthropic, _Introducing the Model Context Protocol_, 2024.11
- Anthropic, _Computer use with Claude_, 2024.10
- Google, _Agent2Agent Protocol_, 2025.04
- OpenAI, _Introducing the Agents SDK and Responses API_, 2025
- OpenAI, _Introducing Operator_, 2025.01
- LangChain/LangGraph 官方文档、CrewAI 文档、LlamaIndex 文档、Pydantic AI 文档、Smolagents 文档
- SWE-bench（Princeton）、τ-bench（Sierra）、GAIA、WebArena、OSWorld 官方论文与 leaderboard
- Coze 开放平台文档、字节 Coze Studio 开源仓库
- 阿里百炼 Assistant API 文档、百度千帆 Agent 文档、腾讯混元助手文档
- Dify、FastGPT、Bisheng、RAGFlow、MetaGPT 官方文档
- E2B、Daytona、Modal 官方文档
- Langfuse、LangSmith、AgentOps、Arize Phoenix、Helicone 官方文档
- Browser Use、Stagehand、Skyvern 官方仓库与文档

---

**上一篇**：[向量库与图 RAG](https://quant67.com/post/llm-infra/18-vector-graph/18-vector-graph.html) **下一篇**：[工具调用与 MCP](https://quant67.com/post/llm-infra/20-tool-function-call/20-tool-function-call.html)

## 同主题继续阅读

把当前热点继续串成多页阅读，而不是停在单篇消费。

2026-04-22 · architecture / ai-infra

### [大模型基础设施工程](https://quant67.com/post/llm-infra/index.html)

面向中国工程团队的大模型基础设施系列。从 GPU/CUDA/互联、训练框架与 3D 并行、vLLM/SGLang 推理引擎、量化与推测解码、RAG/Agent 到服务化、网关、可观测性与安全合规，覆盖 LLMOps 全链路。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】01：大模型基础设施全景 —— 训练、推理、RAG、Agent、观测](https://quant67.com/post/llm-infra/01-intro/01-intro.html)

面向工程师的大模型基础设施开篇地图，覆盖 2022 到 2026 的工程分水岭、五层工程栈、训练与推理的工程差异、中国与全球行业版图以及成本曲线。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】20：工具调用与 MCP](https://quant67.com/post/llm-infra/20-tool-function-call/20-tool-function-call.html)

从 OpenAI function calling 到 Anthropic MCP，深入剖析大模型工具调用的格式、结构化输出、并行调用、协议设计与工程安全边界。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】11：推理引擎基础](https://quant67.com/post/llm-infra/11-inference-basics/11-inference-basics.html)

从 Prefill/Decode 两阶段、KV Cache、Continuous Batching 到 PD 分离，系统讲清楚大模型推理的工程基础。