---
credibility: low
---

## 解析LangGraph中的状态、状态图和工作流

发布日期：2025-05-18 09:19:30 浏览次数： 2916

为了充分发挥大语言模型的潜力，构建强大的应用程序，我们借助LangChain、LangGraph、Agno、Crew AI等多种框架。LangGraph作为LangChain团队推出的又一力作，在处理复杂工作流程方面表现卓越。与LangChain通过灵活链接提示、工具和内存构建大语言模型驱动的应用不同，LangGraph引入了基于图的结构，这一特性使其在管理动态、有状态和非线性任务（如分支逻辑、循环或多智能体交互）时更加得心应手。简而言之，LangGraph是对LangChain的扩展，旨在满足超越简单链式操作的高级用例需求。深入理解LangGraph中的三个基本概念——状态（State）、状态图（StateGraph）和工作流（Workflow），对于掌握这一框架的精髓至关重要。

## 一、状态（State）：数据传递与更新的载体

在LangGraph的体系中，状态指的是在图遍历节点的过程中传递并更新的信息。可以将其形象地比喻为一个背包，这个背包装载着AI工作流所需的所有信息，包括当前的对话内容、用户提出的问题以及中间计算结果等。每当执行一个操作（比如调用一个工具或者做出一个决策），背包里的信息就会随之更新。

例如，在一个智能客服的场景中，状态可能初始化为包含空对话记录、未接收到的用户输入以及未生成的客服回复。当用户输入问题时，状态中的“用户输入”字段被更新；客服模型根据用户输入生成回复后，“客服回复”字段又会被更新。状态在整个交互过程中不断演变，记录并传递着关键信息。

从数据结构的角度来看，状态通常是一个Pydantic模型或者类似字典的对象，它明确规定了数据的结构和内容。以一个简单的问答系统为例：

```python
from typing_extensions import Annotated, TypedDict
class MyState(TypedDict):
    input: str
    result: str = None
```

在这个定义中， `MyState` 规定了状态必须包含 `input` 字段（类型为字符串），用于存储用户输入的问题； `result` 字段（类型也为字符串，默认值为 `None` ），用于存储模型给出的回答。这种严格的数据结构定义使得代码更加安全可靠，当尝试向不符合规定的字段中存储数据时，类型检查工具（如mypy）会及时抛出错误，避免潜在的运行时问题。

## 二、状态图（StateGraph）：工作流的蓝图

状态图就像是流程图的设计蓝图，它详细定义了以下关键要素：

- **状态的结构**
	：明确状态应该具备哪些属性和数据类型，为状态的创建和更新提供规范。
- **节点（步骤）**
	：定义工作流中包含哪些具体的操作或任务，每个节点代表一个独立的功能模块。
- **数据流向**
	：描述数据如何在不同节点之间传递，确定了工作流的执行顺序和逻辑关系。
- **状态更新机制**
	：规定在每个节点执行时，状态是如何被更新的，确保状态随着工作流的推进而准确演变。

状态图可以被看作是一个智能的流程图，它在每一步操作中携带并更新状态信息。与状态不同，状态图侧重于定义结构和流程，而状态则是实际在这个结构中流动的数据。

以一个图像识别与处理的工作流为例，状态图可能包含以下节点：“图像输入”节点用于接收待处理的图像数据，更新状态中的“图像数据”字段；“特征提取”节点根据输入图像提取特征，更新“图像特征”字段；“分类预测”节点利用提取的特征进行图像分类预测，更新“预测结果”字段。状态图通过定义这些节点以及它们之间的连接关系，清晰地规划了数据的处理流程和状态的变化路径。

在代码实现中，使用 `StateGraph` 类来构建状态图。例如：

```python
from langgraph.graph import StateGraph
class MyState(TypedDict):
    image_data: bytes
    image_features: list
    prediction_result: str = None
builder = StateGraph(MyState)
```

在上述代码中， `StateGraph(MyState)` 表示要构建一个状态图，该状态图中的每个步骤都可以访问和更新 `MyState` 定义的状态结构。这就如同为工作流绘制了一张精确的地图，指引着数据的流向和状态的变化。

## 三、工作流（Workflow）：状态图的运行实例

在LangGraph中，工作流是状态图经过编译和运行后得到的实际执行系统。可以将其类比为按下一台遵循设计蓝图（状态图）运作的机器的启动按钮，这台机器利用背包（状态）中的信息进行处理。

当定义好状态图（包括所有的步骤、逻辑和状态设计）后，需要调用 `.compile()` 方法将其转换为工作流。编译后的工作流可以通过 `.invoke()` 或 `.stream()` 方法来执行。在执行过程中，工作流获取初始状态，并按照状态图定义的规则，逐步将状态在各个节点间传递和更新，直至完成整个工作流程。

继续以图像识别与处理的工作流为例，假设已经构建好了状态图并进行了编译：

```python
graph = builder.compile()
initial_state = {
    "image_data": b"",
    "image_features": [],
    "prediction_result": None
}
final_state = graph.invoke(initial_state)
```

在这段代码中，首先创建了一个初始状态，包含空的图像数据、空的图像特征列表和未确定的预测结果。然后，通过 `graph.invoke(initial_state)` 启动工作流，工作流根据状态图的定义，依次执行各个节点的操作，最终得到包含处理结果的最终状态。

如果需要多次执行工作流，后续的执行可以将上一次执行得到的最终状态作为新的输入。例如：

```python
second_state = graph.invoke(final_state)
```

这样，工作流可以基于之前的处理结果继续进行处理，实现更复杂的功能，比如对一系列相关图像进行连续处理时，就可以利用这种方式不断更新状态并推进工作流。

## 四、类比理解：以柠檬水工厂为例

为了更直观地理解状态、状态图和工作流之间的关系，我们可以想象一个自动化柠檬水工厂的场景。

- **状态图（StateGraph）**
	：就像是柠檬水工厂的设计蓝图。这个蓝图详细规划了生产柠檬水的步骤，包括询问用户想要的柠檬水类型（甜口还是咸口）、挤压柠檬、根据用户选择添加糖或盐、倒水、搅拌均匀以及最终提供柠檬水。它明确了每个步骤的顺序、数据（柠檬水原料和成品）在各个生产环节之间的流动方式，以及每个步骤如何改变柠檬水的制作状态，是整个生产流程的规划框架。
- **状态（State）**
	：可以看作是生产线上正在制作的那杯柠檬水。在生产过程的不同阶段，这杯柠檬水的状态不断变化。最初，它可能处于“柠檬水类型未确定、柠檬未添加、未加糖或盐、未倒水、未搅拌、未提供”的初始状态。随着生产流程的推进，每经过一个生产环节（对应状态图中的一个节点），柠檬水的状态就会更新。比如，当确定了用户想要甜口柠檬水后，状态中的“柠檬水类型”字段被更新；挤压柠檬后，“柠檬添加量”字段被更新。状态记录了柠檬水在制作过程中的实时进展情况。
- **工作流（Workflow）**
	：则是启动整个柠檬水制作过程的实际操作。当根据工厂蓝图（状态图）准备好生产设备，并从初始状态（一杯空的、未制作完成的柠檬水）开始生产时，工作流就启动了。在工作流的执行过程中，这杯柠檬水依次经过各个生产环节，原料不断被添加，状态持续被更新，最终生产出可供饮用的柠檬水。这一过程就如同状态在状态图定义的路径上流动，完成整个工作流程。

## 五、实际实现中的深入理解：简单聊天机器人案例

下面通过一个使用LangGraph实现的简单聊天机器人案例，进一步深入理解这三个概念在实际编程中的应用。

```python
from langgraph.graph import StateGraph
from typing import TypedDict, Optional

class GraphState(TypedDict):
    messages: list[str]
    user_input: Optional[str]
    ai_response: Optional[str]
```

在这个案例中， `GraphState` 定义了聊天机器人工作流中的状态结构。其中， `messages` 用于存储整个对话历史，是一个字符串列表； `user_input` 用于存放用户最新输入的消息，它可以是字符串或者 `None` ； `ai_response` 用于保存AI生成的回复，同样可以是字符串或者 `None` 。这种使用 `TypedDict` 定义状态结构的方式，为代码提供了类型安全保障，确保只有符合规定的数据类型才能被存储在状态中。

接下来，定义聊天机器人工作流中的各个节点（步骤）以及它们如何改变状态：

```python
def get_user_input_fn(state: GraphState) -> GraphState:
    user_question = input("Please enter your question: ")
    return {
        **state,
        "user_input": user_question
    }

def run_chat_model_fn(state: GraphState) -> GraphState:
    user_input = state["user_input"]
    # 假设这里有一个已定义的llm_model用于生成回复
    ai_response = llm_model.invoke(user_input)
    return {
        **state,
        "ai_response": ai_response,
    }

def update_history_fn(state: GraphState) -> GraphState:
    updated_messages = [
        f"User: {state['user_input']}",
        f"AI: {state['ai_response']}"
    ]
    return {
        **state,
        "messages": updated_messages
    }

builder = StateGraph(GraphState)
builder.add_node("get_user_input", get_user_input_fn)
builder.add_node("run_chat_model", run_chat_model_fn)
builder.add_node("update_history", update_history_fn)
builder.set_entry_point("get_user_input")
builder.add_edge("get_user_input", "run_chat_model")
builder.add_edge("run_chat_model", "update_history")
graph = builder.compile()
```

在这段代码中，首先定义了三个节点函数。 `get_user_input_fn` 函数用于获取用户输入，并更新状态中的 `user_input` 字段； `run_chat_model_fn` 函数根据用户输入调用聊天模型生成回复，更新 `ai_response` 字段； `update_history_fn` 函数将用户输入和AI回复添加到对话历史 `messages` 列表中。

然后，使用 `StateGraph` 类构建状态图。通过 `add_node` 方法添加各个节点，使用 `set_entry_point` 方法指定工作流的起始节点为 `get_user_input` ，并通过 `add_edge` 方法定义节点之间的连接关系，确定了状态在节点间的流动路径。最后，调用 `.compile()` 方法将状态图转换为可执行的工作流。

在工作流执行时：

```python
initial_state = {
    "messages": [],
    "user_input": None,
    "ai_response": None
}
final_state = graph.invoke(initial_state)
print("After first run:", final_state)
second_state = graph.invoke(final_state)
print("After second run:", second_state)
```

首先创建一个初始状态，然后通过 `graph.invoke(initial_state)` 启动工作流。在第一次运行时，工作流按照状态图的定义依次执行各个节点，更新状态并得到最终状态。第二次运行时，将第一次运行得到的最终状态作为输入再次调用 `invoke` 方法，工作流继续执行，状态进一步更新。通过这种方式，可以不断进行对话交互，实现聊天机器人的功能。

## 六、状态管理与常见陷阱

在多次运行工作流的过程中，状态管理是一个关键问题。如果在更新状态时不加以注意，可能会出现覆盖旧数据的问题。例如，在聊天机器人案例中，如果 `get_user_input` 节点直接用新的用户输入替换旧的用户输入，而不是将其添加到对话历史中，就会导致之前的用户输入丢失； `run_chat_model` 节点如果直接覆盖旧的AI回复，也会造成对话历史的不完整。

为了避免这种情况，在更新状态时需要谨慎处理。例如，对于保存对话历史的 `messages` 列表，可以通过修改 `update_history_fn` 函数来实现数据的追加而不是覆盖：

```python
def store_history_fn(state: GraphState) -> GraphState:
    updated_messages = state["messages"] + [
        f"User: {state['user_input']}",
        f"AI: {state['ai_response']}"
    ]
    return {
        **state,
        "messages": updated_messages
    }
```

通过这种方式，每次运行工作流时，对话历史都会被完整地保存下来，使得聊天机器人能够基于完整的对话记录进行更智能的交互。

状态、状态图和工作流是LangGraph的核心概念。状态作为信息的载体，在工作流执行过程中不断传递和更新；状态图为工作流提供了结构化的设计蓝图，定义了节点、数据流向和状态更新方式；工作流则是状态图的实际运行实例，将状态在状态图规定的路径上推进，实现复杂的AI任务。通过深入理解和正确运用这三个概念，开发者能够充分发挥LangGraph的优势，构建出功能强大、灵活高效的AI应用程序。在未来的人工智能开发中，随着对复杂工作流需求的不断增加，对这些基础概念的深入掌握将成为开发者的必备技能，为创造更加智能、交互性更强的应用奠定坚实的基础。
