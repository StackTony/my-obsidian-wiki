> 智能体开发进入“有状态”时代，LangGraph 让多工具智能体既可控又灵活，助你打造真正工程级 AI 系统。

本文将指导高级 AI 工程开发者，如何基于 **LangChain** 的扩展库 **LangGraph** ，使用 Python 构建一个具备多工具调用能力的 **有状态智能体（Multi-Tool Agent）** 。我们将详述如何设计有状态的智能体工作流（如检索 - 计划 - 执行 - 验证等阶段），如何在智能体中注册和选择不同工具、处理记忆模块，以及如何实现并发、分支和回退控制流程。教程还将涵盖观察调试智能体的方法（日志追踪、链路 Trace、决策记录），以及如何进行错误注入与回放来提高智能体的健壮性。最后，我们提供一个端到端示例任务（包含所有可运行的代码片段），并通过 Mermaid 图表直观展示智能体的决策流程与工具链路。请注意，本教程所有代码均采用 Python，实现均兼容本地部署的大语言模型（如 Qwen 或 Ollama），未依赖 OpenAI/Claude 等闭源模型。

## LangGraph 简介：让智能体工作流进入“有状态”时代

**LangGraph** 是由 LangChain 团队推出的用于构建 **循环图工作流** 的库，可以视作 LangChain 在智能体编排上的一个重要扩展模块。传统的 LangChain Chain 是 **无环的** （DAG 形式），而 LangGraph 允许在链中 **引入循环** ，从而实现更复杂的智能体行为（例如让 LLM 在工具调用失败时重新规划、在多轮对话中持续决策等）。这种循环能力本质上就是让 LLM 在一个类似 `for` 循环的结构中不断根据状态进行推理和行动选择。

LangGraph 将智能体的流程视为 **状态机（state machine）** 。开发者可以手动规定智能体的决策流程（如先调用哪个工具、在什么条件下循环/分支），而不仅仅依赖 LLM 的自由推理。这种显式的流程控制对于生产环境尤为重要：例如你可能希望 **强制智能体首先调用某个工具** ，或者根据当前状态采用不同的提示 (prompt)。通过 LangGraph，我们可以将这些流程以 **图（graph） **的形式声明出来，构建出兼具** 灵活推理** 和 **可控流程** 的智能体系统。

**StateGraph** 是 LangGraph 的核心概念，它表示一个状态驱动的图。StateGraph 有一个全局共享的 **状态对象（state）** ，在图的各节点之间传递和更新。节点可以看作对状态的一个操作：每个节点接收当前状态（通常是一个字典）作为输入，执行计算后输出一个字典，用于更新全局状态的一部分。状态的每个字段可以配置为 **覆盖** 更新或 **累加** 更新。当字段设置为累加（例如一个用于记录行动步骤的列表），多个节点循环更新时会自动将新结果附加在列表后面。

使用 LangGraph 定义智能体的基本步骤包括：

- **定义状态结构** ：使用 `TypedDict` 指定 State 对象的字段和类型，以及哪些字段是累加 List 需要用 `operator.add` 标记。
- **添加节点** ：使用 `graph.add_node(name, func)` 注册节点。每个节点要么是一个 Python 函数，要么是 LangChain Runnable，负责完成一个步骤的逻辑。
- **添加边（Edges）** ：用 `graph.set_entry_point(node)` 指定图的起始节点，然后通过 `graph.add_edge` 添加普通顺序边，或通过 `graph.add_conditional_edge` 添加条件分支边。条件边可以让某个节点根据状态判断下一步跳转到哪一个节点。
- **指定结束** ：LangGraph 提供特殊的 `END` 节点表示结束，务必保证循环流程有退出条件。
- **编译运行** ：调用 `graph.compile()` 将定义的图编译为一个可调用的对象（实现了 `.invoke()` 等方法），然后即可像调用链那样调用智能体。

下面将结合这些概念，设计我们的有状态多工具 Agent，并在各环节介绍实现细节。

## 设计有状态智能体的阶段编排与控制流程

为了构建一个多工具 Agent，我们采用 **分阶段的流程设计** ：例如包含“需求分析/检索 → 计划 → 工具执行 → 验证”的流水线。在 LangGraph 中，这些阶段对应为一系列节点按某种逻辑连接成图。我们将用一个示意性任务来说明—— **根据用户查询决定是否需要检索外部数据、调用计算工具，并最终生成答案** 。这个任务中，Agent 可能需要经过以下决策步骤：

1. **分析需求（Plan）** ：解析用户输入，判断是否需要调用工具（以及调用哪些工具）。如果不需要工具，直接生成答案；如果需要，决定下一步要用的工具及其输入。
2. **执行工具（Execute Tool）** ：调用所选工具并获取结果。如果有多个子任务，可能重复调用不同工具。
3. **（可选）验证或后处理（Verify）** ：检查工具结果是否满足要求，是否需要再次调用其他工具或调整计划。如果结果不理想，可以回退到上一步重新规划。
4. **最终回答（Finalize）** ：整合所有信息，形成给用户的最终答复。

在我们的示例中，我们将实现一个智能体能够 **查询国家的人口并计算总和** 。这个智能体会动态决定使用两个工具：

- 一个 **检索工具** ：查找给定国家的人口数据。
- 一个 **计算工具** ：对获得的数值执行算术计算。

我们会让智能体针对用户的问题自动决定调用上述工具的顺序和次数。例如用户问：“法国和日本的人口总和是多少？”，Agent 将判断需要查找法国人口、查找日本人口，然后加总。这一过程中，Agent 会经历 **循环** ：LLM 先规划调用检索工具，获取法国人口；接着再次规划调用检索工具获取日本人口；然后规划调用计算工具求和；最后生成答案。

### 节点设计：Plan 与 Tools

我们为上述流程设计两个主要节点：

- **Plan 节点** （如同智能体的“大脑”）：使用 LLM 或规则逻辑，根据当前状态决定下一步动作（调用工具或输出答案）。该节点会更新状态中的指令，例如选定工具及其输入参数，或者直接写入最终答案。
- **Tools 节点** （工具执行器）：根据 Plan 节点提供的指令，实际调用相应的工具函数，将结果写回状态（供下次 Plan 决策使用）。

此外，可以视需要添加其他节点，例如用于验证或回退的节点。本例中我们简化，将验证逻辑融合在 Plan 节点里，根据需要重复工具调用或结束。

### 状态设计：共享信息和累积中间结果

我们通过定义 State 对象的字段来实现节点间的信息共享和状态跟踪。对于本示例，我们定义状态包含：

- `input` ：用户的原始查询（字符串）。
- `targets` ：待查询的信息目标列表（如\[“France”,“Japan”\]）。在 Plan 节点首次运行时，从 `input` 中解析填充。
- `index` ：当前已处理的目标计数（整数）。用于跟踪已完成了几个工具调用。
- `collected` ：已收集的中间结果列表（如已获取的人口数字列表）。定义为累加列表，这样工具节点每返回一个结果就附加其值。
- `answer` ：最终答案（字符串）。Plan 节点在确定完成所有步骤后写入此字段。

上述字段中， `collected` 使用了 `operator.add` 设置为累加模式，其他字段则用默认覆盖模式。这样 `collected` 会自动累计工具输出，而不是被覆盖。定义状态的代码如下：

```python
from typing import TypedDict, Annotated, List
import operator

class State(TypedDict):
    input: str                        # 用户输入
    targets: List[str]                # 待检索的目标列表
    collected: Annotated[List[int], operator.add]  # 累计收集的数值结果
    index: int                        # 已处理目标计数
    answer: str                       # 最终答案
```

### Plan 节点实现：LLM 计划与决策

Plan 节点的职责是分析当前状态，决定下一步做什么。这里我们可以 **借助大语言模型** 根据提示来决定行动，也可以简化为规则逻辑。在不依赖 OpenAI API 的前提下，我们示范一种 **规则+LLM 结合** 的思路：

- **需求解析** ：当 Plan 节点第一次接收用户输入时，可通过简单规则或提示调用 LLM，从中提取需要查询的目标。例如检测输入中是否包含“…的 **人口** ”，如果有则识别国家名称列表。如果没有外部信息需求，则可以直接回答。
- **动态决策** ：根据当前已收集的数据 (`collected`) 与目标列表 (`targets`)，决定下一步。如果还有未查询的目标，则设置下一步调用检索工具查询下一个目标；如果目标都已查询完且有多个数值，需要汇总，则选择计算工具；如果已经获得最终结果或不需要工具，则直接产生日志和答案。

下面是 Plan 节点函数的示例实现（不依赖外部 LLM API，而是用规则逻辑模拟决策）：

```python
def plan_node_fn(state: dict) -> dict:
    # 提取当前状态信息
    query = state.get('input', '')
    targets = state.get('targets')
    idx = state.get('index', 0)
    values = state.get('collected', [])
    # 若已经计算出最终结果（collected 比 targets 多一个值，则最后一个为汇总结果）
    if targets is not None and len(values) > len(targets):
        final_val = values[-1]
        return {'answer': f"总人口为 {final_val} 万人。"}
    # 首次运行：解析输入找出目标列表
    if targets is None:
        targets = []
        # 简单解析：寻找 "人口 of X" 模式
        text = query.lower()
        if "population of" in text:
            parts = text.split("population of")
            for part in parts[1:]:
                token = part.strip().split()[0]
                if token:
                    targets.append(token.capitalize())
        # 处理 "X and Y" 的情况
        if " and " in query and targets:
            last = query.split(" and ")[-1].strip()
            if last:
                country = last.split()[0].capitalize()
                if country and country not in targets:
                    targets.append(country)
        # 初始化状态字段
        state['targets'] = targets
        state['index'] = 0
        state['collected'] = []
        idx = 0
        values = []
    # 如未找到任何目标，则不需要工具，直接给出回答（这里简单返回一句话）
    if not targets:
        return {'answer': "这个问题不需要调用工具，可直接回答。"}
    # 如果仍有目标未查询，选择调用检索工具查询下一个目标
    if idx < len(targets):
        country = targets[idx]
        return {'tool': 'search_population', 'tool_query': country}
    # 如果所有目标都已查询且存在多个数值，调用计算工具求和
    if idx == len(targets) and len(values) > 1:
        expr = " + ".join(str(val) for val in values)
        return {'tool': 'calculator', 'tool_query': expr}
    # 如果所有目标查询完且只有单个值，则直接输出答案
    if idx == len(targets):
        if values:
            return {'answer': f"{targets[0]}的人口为 {values[0]} 万人。"}
        else:
            return {'answer': "未找到相关数据。"}
    # 默认返回空（正常情况下不会走到这里）
    return {}
```

**实现要点** ：

- 初次运行时， `targets` 为空，我们解析用户输入中的关键词填充目标列表（如找到“France”“Japan”两国），并将它们存入状态。这个解析过程可以用 LangChain 的提示模板结合 LLM 完成，如让模型从问句中提取实体列表；但这里为简明直接用字符串分析。
- 每次决策，根据 `index` 和 `targets` 列表判断进度：若 `index` 尚未到达 `targets` 末尾，则还有国家未查询，于是返回指示调用 `search_population` 工具（并指定查询国家名）；若已收集多个数值，则需要求和，于是返回调用 `calculator` 工具的指令；若只收集了一个值且无进一步操作，则直接准备输出答案。
- 当检测到状态中 `collected` 数量比 `targets` 数多时，说明上一步计算工具已经算出了最终汇总结果，我们便直接构造最终回答放入 `answer` 字段。

### Tools 节点实现：多工具执行与结果写回

Tools 节点负责根据 Plan 给出的指令实际调用工具函数，并把结果更新到状态中。首先需要 **注册工具** ：在 LangChain 中通常将工具封装为 Tool 对象，但在此我们直接用普通的 Python 函数模拟工具功能：

- `search_population(country: str)` ：检索某国家人口。本例中我们用预设的字典模拟数据库。例如 `population_data = {"France": 67, "Japan": 125}` 表示法国人口 67 百万人、日本 125 百万人。函数返回找到的人口数字（为了简化计算，我们返回整数部分）。
- `calculator(expression: str)` ：计算算术表达式结果。可以用 Python 的 `eval` 来处理简单加法表达式（但实际场景应谨慎处理安全）。本例中，我们传入的表达式格式如 `"67 + 125"` ，计算后得到整数结果 `192` 。

工具执行函数完成后，要将结果写入状态。根据之前状态设计，我们希望：

- 检索工具得到的人口数字追加到 `collected` 列表，并将 `index` 递增 1（表示一个目标已完成）。
- 计算工具得到的总和结果也追加到 `collected` 列表。此时列表将比原目标数多一个元素，方便 Plan 节点识别已经完成汇总。

下面是 Tools 节点的示例实现：

```python
# 模拟数据库
population_data = {"France": 67, "Japan": 125}

def tool_node_fn(state: dict) -> dict:
    tool_name = state.get('tool')
    query = state.get('tool_query')
    if tool_name == 'search_population':
        country = query
        if country in population_data:
            result = population_data[country]
            # 将结果追加到 collected 列表（LangGraph 累加机制会自动 append）
            return {'collected': [result], 'index': state.get('index', 0) + 1}
        else:
            # 没找到数据，返回错误信息
            return {'error': f"未找到{country}的人口数据"}
    elif tool_name == 'calculator':
        expr = query  # 形如 "67 + 125"
        try:
            calc_result = eval(expr)
        except Exception as e:
            return {'error': f"计算出错：{e}"}
        # 将计算结果也加入 collected
        return {'collected': [int(calc_result)]}
    else:
        return {'error': f"未知工具:{tool_name}"}
```

**实现要点** ：

- 根据状态中的 `tool` 字段分发到对应的工具逻辑。
- 每个工具通过返回字典来更新状态。对于 `collected` 字段，由于我们在 State 定义中标记了 `operator.add` ，LangGraph 会自动将新列表元素添加到已有列表后面。
- `search_population` 成功时还返回更新后的 `index` （旧值 +1）。 `calculator` 完成汇总后不增 index，因为此时 `index` 已经等于目标数，汇总结果只是附加信息。
- 如果出现错误（如没有找到数据，或表达式计算异常），这里简单地将错误信息写入状态的 `error` 字段。后续我们可以通过检测 `error` 实现异常分支处理。

### 构建状态图（StateGraph）并添加控制边

有了 Plan 和 Tools 两个节点函数，我们就可以把它们加入 StateGraph 并连成工作流：

```python
from langgraph.graph import StateGraph, END

# 初始化状态图
graph = StateGraph(State)
# 添加节点
graph.add_node("plan", plan_node_fn)
graph.add_node("tools", tool_node_fn)
# 指定入口节点
graph.set_entry_point("plan")
# 添加普通边：工具节点执行后回到计划节点（形成循环）
graph.add_edge("tools", "plan")
# 添加条件边：plan 节点根据返回结果决定下一步去向
def should_continue(state: dict) -> str:
    # 若 Plan 返回了最终答案，则结束，否则进入工具执行
    return "end" if state.get('answer') else "continue"

graph.add_conditional_edge(
    "plan",
    should_continue,
    {
        "end": END,
        "continue": "tools"
    }
)
# 编译图为可调用应用
app = graph.compile()
```

在上述代码中，我们建立了如下流程关系：

图 1: 流程关系图

如上图所示，Agent 从 Plan 节点开始：Plan 节点要么决定直接结束（生成最后回答），要么指定需要调用某个工具然后进入 Tools 节点。Tools 节点执行完，再回到 Plan 重新决策。这个循环会持续，直到 Plan 给出结束条件（即 state 中出现 `answer` ）跳转到 End 节点。在我们的示例中，循环可能经历多次工具调用（如两次检索，一次计算）再结束。

### 并发执行与分支：高级控制流

LangGraph 除了支持上述顺序循环，还支持更复杂的 **并发和分支** 控制流。通过一个节点连接出 **多个后继节点** 即可形成 **分叉** （fan-out），LangGraph 可并行执行这些分支节点，然后在某处 **汇合** （fan-in）它们的结果。例如，我们可以改进前述 Agent，让它 **并行地查询多个国家的人口** 以加速流程。当 Plan 节点识别出多个目标时，不是依次一个个调用检索工具，而是同时分叉出多个检索节点，然后汇总结果再进行计算。下图展示了这种并行分支结构的雏形：

图 2: 高级控制流

在 LangGraph 实现并行，可以为一个节点添加 **多条普通边** 指向不同后继节点，如： `graph.add_edge("plan", "searchA"); graph.add_edge("plan", "searchB")` 。当 Plan 节点执行后，LangGraph 将在同一轮中并发执行 `searchA` 和 `searchB` 两个节点，并分别更新状态。为正确汇总并行结果，需在状态定义中为共享字段设置 **自定义合并函数** 。例如让两个检索节点各自返回一个结果列表，然后在汇合节点前通过 reducer 函数合并它们。LangGraph 允许我们在 State 定义时提供自定义 `reducer` 来合并并行分支的输出。完成 fan-in 后，再继续后续节点（如计算和输出）。需要注意，并行工具调用会增加实现复杂度，如处理结果顺序和可能的异步 I/O 等，在实际应用中应根据需要权衡使用。

除了并行，LangGraph 也支持 **条件分支** ：通过 `add_conditional_edge` 可以让某节点根据状态选择不同分支路径（如不同工具、不同应对策略）。这类条件可以由 LLM 决定，也可以由规则函数决定。例如，我们可以在智能体某步引入 **验证节点** ：检查先前答案是否符合要求，如果不符合则走分支调用其它工具重试，符合则直接结束。这相当于实现了一种 **回退/回放机制** 。总之，通过组合 **循环、并行、条件** 三种边类型，LangGraph 能表达几乎任意复杂的智能体流程。

## 多工具调用机制

有状态智能体的优势在于可以灵活地选择并调用多个工具。接下来，我们讨论如何管理 **多工具的注册与调度** ，并确保每次工具调用的输入输出正确、错误可控。

### 工具注册与封装

在 LangChain 框架中，工具通常被封装为 `Tool` 对象，包含名称、描述和实际执行函数。但在 LangGraph 中，我们无需特别封装，直接在 Tools 节点里按照 `state['tool']` 判定来调用相应函数即可（如上所示）。当然，在更复杂情况下，可以维护一个 **工具字典** 或使用 LangChain 提供的工具集合：

```python
# 使用 LangChain 的 Tool 封装（可选）
from langchain.agents import Tool

search_tool = Tool(
    name="search_population",
    func=lambda country: population_data.get(country, "Not found"),
    description="检索指定国家的人口，返回数字"
)
calc_tool = Tool(
    name="calculator",
    func=lambda expr: eval(expr),
    description="计算简单算术表达式的结果"
)
tools = [search_tool, calc_tool]
```

LangChain 中智能体调用工具通常有两种方式： **动态** 和 **静态** 。 **动态工具选择** 指由 LLM 自主决定何时用哪个工具（典型案例如 ReAct Agent，让模型输出“Action: 工具名”），如我们设计的 Plan 节点即属于动态决策。 **静态工具顺序** 则指我们在流程中 **固定某些工具调用步骤** ，不论 LLM 内容如何都执行。例如可以规定“用户请求进入后，Agent **总是先调用检索工具** 然后才回答”，这种需求可以通过 LangGraph 强制一个边顺序来实现。开发者应根据业务需要选择策略：动态方式灵活但不易预料，静态顺序可控但不够高效。也可以二者结合：例如 **第一步静态地调用工具获取背景信息** ，后续再动态决策其它工具。

### 工具输入的验证与格式规范

在多工具场景下， **输入格式** 和 **有效性** 至关重要。LLM 产生的工具调用指令可能有格式错误或不符合预期。为防止这类问题，可以采取以下措施：

- **规范提示** ：通过提示模板严格规范 LLM 输出动作的格式（如“工具名：参数”格式），或者使用 **函数式调用** 能力（Function Calling），让模型输出可解析的 JSON。不过本例未使用 OpenAI 模型，函数调用可由类似机制实现或自行解析模型文本。
- **输入校验** ：在 Tools 节点执行前，对 `state['tool_query']` 进行检查。例如我们的计算工具可先验证表达式只包含安全字符，再用 `eval` 执行；检索工具可检查国家名是否在数据库里，否则提前标记错误。
- **fallback 默认值** ：如果输入不合法，工具可以返回特定的错误结果，让智能体识别并处理。比如我们在 Tools 节点返回了 `{'error': '...信息'}` 来提示上层。

在 Plan 节点或独立的验证节点中，可检测 `state` 是否含有 `'error'` 字段，从而决定走错误处理流程（例如忽略该工具结果、向用户反馈无法完成等）。通过这种方式，即使 LLM 选择了无效的工具或参数，我们的系统也能平稳处理而不会崩溃。

### 错误处理与重试机制

完善的智能体应当在工具失败时具备 **重试或回退** 能力。例如，如果调用 API 出现网络错误，可以等待片刻再次调用；如果连续多次失败，则记录错误并结束，避免死循环。利用 LangGraph 的状态和图结构，我们可以：

- 在 Tools 节点里捕获异常，将错误信息写入状态，如 `state['error']` 。然后通过一个 **条件边** ，如果检测到 `error` 字段则跳转到一个专门的 **错误处理节点** ，否则正常流程。
- 错误处理节点可以根据错误类型选择策略：有些错误可尝试修正参数后重试（例如搜索不到结果时，Agent 可以改变搜索关键词再调用一次）；有些错误则直接终止流程输出抱歉信息。
- LangGraph 的 **持久化** (Persistence) 特性还能使智能体在崩溃或中断后 **恢复** 。StateGraph 可以配合一个\*\*检查点（Checkpointer）\*\*一同编译，自动在每步保存状态。一旦进程故障或异常退出，再次启动时可从上次的检查点继续。这对于长时间运行的循环智能体尤为有用。

总而言之，通过状态中的错误标记与 LangGraph 的条件跳转，我们能够实现 **错误注入与回放** 测试。例如，我们可以 **人为在工具中注入错误** （返回错误码），观察智能体是否按预期走到错误分支并执行了重试或安全退出逻辑。这种测试可以提高智能体应对异常情况的稳健性。

## 记忆模块与状态传递

默认情况下，上述 LangGraph 智能体每次调用都是 **无记忆** 的，即不保留先前对话或操作的上下文。在多轮对话或需要长期引用资料的场景，我们需要为智能体增加 **记忆模块** 。记忆可以分为 **短期记忆** 和 **长期记忆** 两种：

- **短期记忆** （会话记忆）：保存最近若干对话轮次内容，确保智能体能够理解上下文追问。实现方式包括 LangChain 的 `ConversationBufferMemory` （缓冲全部对话）或 `ConversationBufferWindowMemory` （仅保留最近 N 条）。在 LangGraph 中，短期记忆可通过 **State** 实现：例如在状态里加入 `chat_history` 字段（类型为 `list[BaseMessage]` ，并用 `operator.add` 累加）。每次用户/AI 消息都追加到该列表。LangGraph 还提供 `MemorySaver` 等 checkpointer 工具，能够在多次 `invoke` 调用间自动 **持久化对话记录** 。使用时，只需在编译时传入参数 `checkpointer=MemorySaver()` ，并为每次对话提供一个 `thread_id` 标识会话，LangGraph 会将状态与该 ID 关联存储。如下示例：
```python
from langgraph.checkpoint.memory import MemorySaver
memory = MemorySaver()
app = graph.compile(checkpointer=memory)
# 调用时指定线程 ID，以区分不同会话
result = app.invoke({"input": user_input}, metadata={"thread_id": "session_123"})
```

如此，连续多次调用 `app.invoke` ，内部会沿用同一个 `chat_history` 。短期记忆一般存储在内存中，不跨进程。

- **长期记忆** ：针对长周期或跨会话的信息存储，例如把用户提供的事实、Agent 总结的知识存在外部数据库（向量库或 Key-Value 存储）中，以便后续检索。LangChain 提供了多种向量库接口（如 FAISS, Milvus 等）和 `VectorStoreRetrieverMemory` 来实现语义记忆。LangGraph 自身也提供 `InMemoryStore` 等简单存储，可将记忆按 `namespace` 分类保存并搜索。在实践中，可以将长期记忆看作另一种 **工具** ：当智能体需要回忆时，就通过一个“Memory 检索工具”查询外部记忆库，将相关信息并入上下文。例如，我们可以在 Plan 节点判断如果用户问了以前提过的人物细节，则调用 Memory 工具检索过往对话资料。

无论短期还是长期记忆，核心是在 **状态** 中传递上下文信息给 LLM。对于本例简单的计算 Agent，记忆意义不大，我们就不实现实际记忆功能。但在更复杂的对话智能体中，别忘了在状态里维护 `chat_history` ，并在 Plan 节点（LLM 调用）构造 prompt 时包含历史对话。良好的记忆管理可以防止上下文丢失和重复询问，提高用户体验。

## 可观测性与调试：日志、追踪与决策记录

构建复杂智能体时， **可观测性** 是确保系统行为可理解和可调试的关键。LangChain 与 LangGraph 提供了一些工具来记录智能体的内部决策过程：

- **日志追踪** ：可以使用 Python 的 logging 模块或简单的 print，将每个节点的输入输出、LLM 的决定、工具的结果打印出来。比如在 Plan 节点函数中打印 `state['input']` 及决策，在 Tools 节点打印调用了哪个工具以及得到的结果。这样在终端就能实时看到智能体的执行轨迹。LangChain 也支持设置 `verbose=True` 来输出内部信息，不过对高度自定义的 LangGraph 流程，这种通用 verbose 可能不足，应结合自定义日志。
- **链路 Trace** ：LangChain 推出了 LangSmith 平台用于链路追踪，可视化每步调用及消耗。但我们也可以不用外部服务，通过 LangGraph 自带的 `.stream()` 接口实现简单追踪。 `app.stream(input, stream_mode="values")` 会返回一个迭代器，逐步 yield 每个节点执行的输出值。例如：
	```python
	stream = app.stream({"input": query}, stream_mode="values")
	for step in stream:
	    print("Step output:", step)
	```
	这可以逐步获取 Plan 节点和 Tools 节点各自的输出字典，有助于了解每轮循环中文本生成和工具调用的顺序。如果将 `stream_mode` 设置为 `"trace"` （假设有该模式），可能会包含更多元数据。 **注意** ：流式输出在智能体场景下尤其适用，可以让最终答案逐字生成，同时还能监测中间动作。
- **决策记录** ：建议在状态中加入一个字段（如 `intermediate_steps` 或 `action_log` ），将每次 LLM 的动作决定和工具返回结果记录下来。事实上，LangChain 标准智能体通过 `intermediate_steps` 列表保存 `(AgentAction, Observation)` 对。在我们示例中，我们用 `collected` 列表存了中间数字，但未存文本说明。在真实场景，可以把工具名称和返回摘要也记录，例如 `intermediate_steps: Annotated[List[str], operator.add]` 然后每次工具执行返回 `{"intermediate_steps": [f"Action: 搜索{country}, Result: {result}"]}` 。这样最终状态中就保留了整个决策链路，便于日志分析或回答时引用。如果需要让最终答案也附带这些依据，可以让 LLM 参考该记录或在输出阶段直接打印它们。

通过上述方法，我们可以调试每一步决策是否合理。例如，当智能体出现了错误行为，可以通过查看日志和决策记录，找出是哪一步的 LLM 判断失误或者工具输出异常。然后有针对性地调整提示、约束或代码逻辑。

## 错误注入与回放测试

为了确保智能体在各种异常情况下表现稳定，我们应进行 **错误注入测试** 。这通常包括：

- **模拟工具失败** ：手动让某个工具函数在特定输入时抛出异常或返回错误。例如我们可以修改 `search_population` 工具，当 `country=="Japan"` 时故意返回 `{'error': '服务超时'}` 。然后观察智能体是否按预期没有崩溃且转入错误处理分支。如果我们在状态里实现了重试机制（比如 Plan 节点检测到错误就再次调用工具），那么应验证智能体会重新尝试查询日本人口。
- **模拟 LLM 输出不当** ：由于我们的 Plan 节点逻辑比较严谨，这部分问题不明显。但对于真实 LLM 驱动的 Plan 节点，可以构造一些不符合格式的模型回应，看看系统能否检测并纠正。例如模型输出了一个未定义的工具名，我们的 Tools 节点会返回 `{'error': '未知工具'}` ，那么 Plan 节点下一步是否做出了合理处理（比如直接终止回答并告知用户无法完成）？
- **回放与恢复** ：如果使用了 LangGraph 的持久化，在测试中可以 **中途中断** 智能体然后恢复。例如让智能体执行到一半（如已经拿到部分数据）时强行停止进程，再重启看是否能从检查点继续。这模拟了意外宕机的场景。根据 LangGraph 设计，只要启用了 MemorySaver 并使用相同 `thread_id` ，Agent 应该 **从上次状态继续** 。

通过上述测试，我们可以发现智能体流程中的薄弱环节，并完善相应的异常处理逻辑。例如，也许需要在 Plan 节点增加一个最大循环次数，避免 LLM 卡住导致无限循环；或者给某些工具设置超时时间，超时则返回错误等。将这些完善后，再次运行回放测试，直到对各种异常情况都有恰当响应为止。

## 端到端示例：多工具智能体解决实际任务

现在让我们将所有组件组装起来，展示一个完整的端到端示例。我们仍然以“查询国家人口并求和”为任务，演示智能体如何自主决定使用检索和计算工具来回答用户问题。

首先，确保已按照前述代码定义了 `State` 类型、 `plan_node_fn` 、 `tool_node_fn` ，并构建好了 `graph` ：

```python
# （省略前面的 State, plan_node_fn, tool_node_fn 定义和 graph 构建步骤，
#  可假定它们已经按照上述代码执行）
# ...

# 编译智能体应用
app = graph.compile()
```

现在，我们尝试对智能体提问。例如：

```python
# 示例查询 1：需要调用两个工具（检索法国、日本人口并求和）
query1 = "What is the sum of the population of France and Japan?"
result1 = app.invoke({"input": query1})
print(f"Query: {query1}\nAnswer: {result1.get('answer')}")
```

假设我们的本地模型知识涵盖常识数据，上述询问将触发智能体依次调用两个工具。 **预期输出** （由于我们用规则模拟，这里直接给出结果）：

```text
Query: What is the sum of the population of France and Japan?
Answer: The total population is 192 million.
```

Agent 的工作过程大致如下：Plan 节点解析出目标国家列表\[`France`,`Japan`\]，然后输出指示调用检索工具；Tools 节点查询到法国人口为 67（百万），将其存入状态；Plan 再次执行，发现还有一个目标 Japan 未查询，再次输出检索指令；Tools 查询到日本人口 125，存入状态；Plan 第三次执行，检测到已收集两个数值，需要汇总，遂输出计算工具指令；Tools 计算 `67+125=192` ，附加结果 192 到状态；Plan 第四次执行时检测到结果已汇总，生成最终回答。整个过程中，我们可以通过日志看见类似的决策链：

```text
Plan: Parsed targets ['France','Japan'] from query.
Plan: Decided to use tool 'search_population' for France.
Tools: Executing search_population(France) -> 67
Plan: Decided to use tool 'search_population' for Japan.
Tools: Executing search_population(Japan) -> 125
Plan: Decided to use tool 'calculator' for 67 + 125.
Tools: Executing calculator('67 + 125') -> 192
Plan: Produced final answer.
```

你也可以尝试一个不需要工具的问句，验证智能体会直接给出答案而不走工具流程：

```python
# 示例查询 2：不需要任何工具
query2 = "Is 2+2 equal to 4?"
result2 = app.invoke({"input": query2})
print(f"Query: {query2}\nAnswer: {result2.get('answer')}")
```

如果 Plan 节点判断无需外部信息（例如我们实现中如果没有识别出“population of”就直接返回答案模板），Agent 会立即在第一次 Plan 调用就生成 `answer` ，根据我们代码会回答类似：“这个问题不需要调用工具，可直接回答。”（实际应用中，可让 LLM 直接回答数学问题或给出正确的计算结果）。

上述示例表明，我们成功构建了一个可以根据需求 **动态调用多个工具** 的 Agent，并完成了一个端到端任务。开发者可以在此基础上扩展更多工具（例如天气查询、邮件发送等），并丰富 Plan 节点的决策逻辑（通过提示让 LLM 自主选择工具）。

## 最佳实践清单

在构建和部署多工具有状态智能体时，请参考以下最佳实践清单，以确保系统性能和可靠性：

- **上下文管理** ：合理利用记忆模块控制对话上下文大小。短期记忆在 prompt 中提供最近信息，长期记忆在需要时检索历史知识。避免每轮都附加过长历史，防止超出模型上下文窗口并引发性能问题。必要时对旧对话进行总结或截断。
- **避免无限循环** ：在循环流程中设置安全网，例如最大循环次数或时间限制。当 LLM 连续若干次未能完成任务时，中止循环并给出失败反馈，防止智能体陷入死循环。【提示】LangGraph 可在状态中增加一个计数，每次 Plan 循环 +1，超过阈值则走结束分支。
- **工具设计原则** ：确保工具函数 **幂等** 且尽量 **无副作用** ，以便重复调用不会产生不一致结果。对于会修改外部状态的工具（如发消息、下单），需要特殊处理避免重复执行——可考虑在状态中标记已执行过，或在工具本身实现去重逻辑。
- **错误处理** ：充分考虑各种错误场景，例如工具超时、输出格式不符、LLM 回答偏离预期等。为每种异常设计合理的处理分支或 fallback 答案。宁可让智能体礼貌拒绝，也不要挂起或返回奇怪输出。
- **并发与资源** ：如果使用并行工具调用，注意外部 API 的速率限制和本地计算资源占用。LangGraph 允许限制同一“超级步”中的并发数，可根据需要配置，或在工具实现内部加入同步机制。
- **Prompt 设计与测试** ：如果 Plan 节点基于 LLM 输出动作，一定要精心设计提示词，明确告诉模型可用工具列表、调用格式、何时停止等。同时准备多样的测试 query 来验证模型不会误用工具。对于关键任务，可以考虑加入 **少量规则** 校验模型输出，双重保险。
- **调试方法** ：利用日志和 trace 追踪每一步决策，尤其在开发早期多观察智能体内部状态的变化。当结果不符合预期时，通过决策记录找出是哪一步出现问题，是 LLM 理解不对还是工具返回有误。调试时也可固定随机种子或使用较小模型，以获得可重复的行为来分析。
- **性能优化** ：本地部署模型可能较慢。可以考虑对 LLM 的调用进行优化，例如启用 4-bit 量化模型、减少不必要的 prompt 内容等。对于经常要调用的知识库，优先使用工具/检索代替让 LLM 直接记忆，以减轻模型负担。
- **安全控制** ：多工具智能体若可执行任意代码或访问敏感数据，要做好权限隔离和审计。使用 LangChain 时，尽量选择受限的工具函数，不要直接将用户输入传给 `eval` 等高危函数。对 LLM 的输出也需监控，防止其构造恶意指令利用工具。

以上清单并非穷尽，但涵盖了一般场景下开发有状态多工具智能体需要注意的关键点。遵循这些最佳实践，可以大大提升智能体系统在真实环境中的稳定性和可维护性。

## 总结

通过本教程，我们学习了如何使用 LangGraph 提供的 StateGraph 框架，结合 LangChain 的工具和内存组件，创建一个强大的多工具智能体。我们经历了从 **状态设计** 、 **节点编排** 、 **多工具决策** 到 **错误处理** 、 **调试优化** 的完整过程。利用这些方法，开发者可以构建出更 **灵活** 且 **可控** 的智能体系统，应对复杂多变的任务需求。希望本教程为您的智能体开发实践提供了有益的参考！

创建于 2025/10/03 更新于 2025/11/02 11729 字 阅读约 24 分钟