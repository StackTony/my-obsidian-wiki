
## 什么是记忆？

AI 应用中的记忆指处理、存储和有效回忆过往交互信息的能力。有了记忆，您的智能体可以从反馈中学习并适应用户的偏好。本指南根据记忆召回的范围分为两个部分：短期记忆和长期记忆。

**短期记忆** ，或 [线程](https://github.langchain.ac.cn/langgraphjs/concepts/persistence/#threads) 范围的记忆，可以随时在与用户的单个对话线程 **内** 被召回。LangGraph 将短期记忆作为智能体 [状态](https://github.langchain.ac.cn/langgraphjs/concepts/low_level/#state) 的一部分进行管理。状态使用 [检查点](https://github.langchain.ac.cn/langgraphjs/concepts/persistence/#checkpoints) 持久化到数据库中，以便线程可以随时恢复。当图被调用或步骤完成时，短期记忆会更新，并且在每个步骤开始时读取状态。

**长期记忆** 在对话线程 **之间** 共享。它可以\*随时\*且在 **任何线程** 中被召回。记忆可以限定在任何自定义命名空间内，而不仅仅是单个线程ID。LangGraph 提供 [存储](https://github.langchain.ac.cn/langgraphjs/concepts/persistence/#memory-store) （ [参考文档](https://github.langchain.ac.cn/langgraphjs/reference/classes/checkpoint.BaseStore.html) ）来让您保存和召回长期记忆。

理解并在您的应用程序中实现这两种记忆都非常重要。

![](https://github.langchain.ac.cn/langgraphjs/concepts/img/memory/short-vs-long.png)

## 短期记忆

短期记忆让您的应用程序能够记住单个 [线程](https://github.langchain.ac.cn/langgraphjs/concepts/persistence/#threads) 或对话中的先前交互。 [线程](https://github.langchain.ac.cn/langgraphjs/concepts/persistence/#threads) 在一个会话中组织多个交互，类似于电子邮件将消息分组到单个对话中的方式。

LangGraph 将短期记忆作为智能体状态的一部分进行管理，通过线程范围的检查点进行持久化。此状态通常可以包括对话历史以及其他有状态数据，例如上传的文件、检索到的文档或生成的工件。通过将这些存储在图的状态中，机器人可以访问给定对话的完整上下文，同时保持不同线程之间的分离。

由于对话历史是表示短期记忆最常见的形式，因此在下一节中，我们将介绍当消息列表变得 **冗长** 时管理对话历史的技术。如果您想坚持高层概念，请继续阅读 [长期记忆](#long-term-memory) 部分。

### 管理长对话历史

长对话对当今的 LLM 构成了挑战。完整的历史记录甚至可能无法完全适应 LLM 的上下文窗口，从而导致不可恢复的错误。即使您的 LLM 在技术上支持完整的上下文长度，大多数 LLM 在长上下文中表现仍然不佳。它们会被陈旧或偏离主题的内容“分散注意力”，同时响应时间更慢且成本更高。

管理短期记忆是平衡 [准确率和召回率](https://en.wikipedia.org/wiki/Precision_and_recall#:~:text=Precision%20can%20be%20seen%20as,irrelevant%20ones%20are%20also%20returned) 与您应用程序的其他性能要求（延迟和成本）的实践。一如既往，批判性地思考如何为您的 LLM 表示信息并查看您的数据非常重要。我们在下面介绍了几种管理消息列表的常见技术，并希望为您提供足够的上下文，以便您为应用程序选择最佳权衡方案。

- [编辑消息列表](#editing-message-lists) ：如何考虑在将消息列表传递给语言模型之前对其进行修剪和过滤。
- [总结过往对话](#summarizing-past-conversations) ：当您不仅仅想过滤消息列表时，一种常用的技术。

### 编辑消息列表

聊天模型使用 [消息](https://js.langchain.ac.cn/docs/concepts/#messages) 接受上下文，其中包括开发者提供的指令（系统消息）和用户输入（人类消息）。在聊天应用程序中，消息在人类输入和模型响应之间交替，导致消息列表随时间增长。由于上下文窗口有限且富含 token 的消息列表可能成本高昂，许多应用程序可以受益于使用手动删除或遗忘陈旧信息的技术。

![](https://github.langchain.ac.cn/langgraphjs/concepts/img/memory/filter.png)

最直接的方法是从列表中删除旧消息（类似于 [最近最少使用缓存](https://en.wikipedia.org/wiki/Page_replacement_algorithm#Least_recently_used) ）。

在 LangGraph 中从列表中删除内容的典型技术是，从节点返回一个更新，告诉系统删除列表的某个部分。您可以定义此更新的外观，但一种常见的方法是让您返回一个对象或字典，指定要保留哪些值。

```typescript
import { Annotation } from "@langchain/langgraph";

const StateAnnotation = Annotation.Root({
  myList: Annotation<any[]>({
    reducer: (
      existing: string[],
      updates: string[] | { type: string; from: number; to?: number }
    ) => {
      if (Array.isArray(updates)) {
        // Normal case, add to the history
        return [...existing, ...updates];
      } else if (typeof updates === "object" && updates.type === "keep") {
        // You get to decide what this looks like.
        // For example, you could simplify and just accept a string "DELETE"
        // and clear the entire list.
        return existing.slice(updates.from, updates.to);
      }
      // etc. We define how to interpret updates
      return existing;
    },
    default: () => [],
  }),
});

type State = typeof StateAnnotation.State;

function myNode(state: State) {
  return {
    // We return an update for the field "myList" saying to
    // keep only values from index -5 to the end (deleting the rest)
    myList: { type: "keep", from: -5, to: undefined },
  };
}
```

当在键“myList”下返回更新时，LangGraph 将调用“ [reducer](https://github.langchain.ac.cn/langgraphjs/concepts/low_level/#reducers) ”函数。在该函数中，我们定义要接受的更新类型。通常，消息会添加到现有列表中（对话将增长）；但是，我们也添加了支持接受一个字典，让您可以“保留”状态的某些部分。这允许您以编程方式丢弃旧消息上下文。

另一种常见的方法是让您返回一个“删除”对象列表，指定要删除的所有消息的ID。如果您在 LangGraph 中使用 LangChain 消息和 [`messagesStateReducer`](https://github.langchain.ac.cn/langgraphjs/reference/functions/langgraph.messagesStateReducer.html) reducer（或使用相同底层功能的 [`MessagesAnnotation`](https://github.langchain.ac.cn/langgraphjs/reference/variables/langgraph.MessagesAnnotation.html) ），则可以使用 `RemoveMessage` 来完成此操作。

```typescript
import { RemoveMessage, AIMessage } from "@langchain/core/messages";
import { MessagesAnnotation } from "@langchain/langgraph";

type State = typeof MessagesAnnotation.State;

function myNode1(state: State) {
  // Add an AI message to the \`messages\` list in the state
  return { messages: [new AIMessage({ content: "Hi" })] };
}

function myNode2(state: State) {
  // Delete all but the last 2 messages from the \`messages\` list in the state
  const deleteMessages = state.messages
    .slice(0, -2)
    .map((m) => new RemoveMessage({ id: m.id }));
  return { messages: deleteMessages };
}
```

在上面的示例中， `MessagesAnnotation` 允许我们将新消息附加到 `messages` 状态键，如 `myNode1` 所示。当它看到 `RemoveMessage` 时，它将从列表中删除具有该ID的消息（然后该RemoveMessage将被丢弃）。有关LangChain特定消息处理的更多信息，请查看 [此关于使用 `RemoveMessage` 的操作指南](https://github.langchain.ac.cn/langgraphjs/how-tos/memory/delete-messages/) 。

有关示例用法，请参阅此操作 [指南](https://github.langchain.ac.cn/langgraphjs/how-tos/manage-conversation-history/) 。

### 总结过往对话

如上所示，修剪或删除消息的问题在于，我们可能会因为筛选消息队列而丢失信息。因此，一些应用程序受益于使用聊天模型总结消息历史的更复杂方法。

![](https://github.langchain.ac.cn/langgraphjs/concepts/img/memory/summary.png)

可以使用简单的提示和编排逻辑来实现这一点。例如，在 LangGraph 中，我们可以扩展 [`MessagesAnnotation`](https://github.langchain.ac.cn/langgraphjs/reference/variables/langgraph.MessagesAnnotation.html) 以包含 `summary` 键。

```typescript
import { MessagesAnnotation, Annotation } from "@langchain/langgraph";

const MyGraphAnnotation = Annotation.Root({
  ...MessagesAnnotation.spec,
  summary: Annotation<string>,
});
```

然后，我们可以生成聊天历史的摘要，使用任何现有摘要作为下一个摘要的上下文。此 `summarizeConversation` 节点可以在 `messages` 状态键中积累一定数量的消息后调用。

```typescript
import { ChatOpenAI } from "@langchain/openai";
import { HumanMessage, RemoveMessage } from "@langchain/core/messages";

type State = typeof MyGraphAnnotation.State;

async function summarizeConversation(state: State) {
  // First, we get any existing summary
  const summary = state.summary || "";

  // Create our summarization prompt
  let summaryMessage: string;
  if (summary) {
    // A summary already exists
    summaryMessage =
      \`This is a summary of the conversation to date: ${summary}\n\n\` +
      "Extend the summary by taking into account the new messages above:";
  } else {
    summaryMessage = "Create a summary of the conversation above:";
  }

  // Add prompt to our history
  const messages = [
    ...state.messages,
    new HumanMessage({ content: summaryMessage }),
  ];

  // Assuming you have a ChatOpenAI model instance
  const model = new ChatOpenAI();
  const response = await model.invoke(messages);

  // Delete all but the 2 most recent messages
  const deleteMessages = state.messages
    .slice(0, -2)
    .map((m) => new RemoveMessage({ id: m.id }));

  return {
    summary: response.content,
    messages: deleteMessages,
  };
}
```

有关示例用法，请参见 [此处](https://github.langchain.ac.cn/langgraphjs/how-tos/memory/add-summary-conversation-history/) 。

### 知道何时删除消息

大多数 LLM 都有一个最大支持上下文窗口（以 token 计）。决定何时截断消息的一个简单方法是计算消息历史中的 token 数量，并在接近该限制时进行截断。朴素截断很容易自行实现，尽管有一些“陷阱”。某些模型 API 进一步限制了消息类型的序列（必须以人类消息开头，不能有相同类型的连续消息等）。如果您正在使用 LangChain，可以使用 [`trimMessages`](https://js.langchain.ac.cn/docs/how_to/trim_messages/#trimming-based-on-token-count) 工具并指定要从列表中保留的 token 数量，以及用于处理边界的 `strategy` （例如，保留最后 `maxTokens` ）。

下面是一个示例。

```typescript
import { trimMessages } from "@langchain/core/messages";
import { ChatOpenAI } from "@langchain/openai";

trimMessages(messages, {
  // Keep the last <= n_count tokens of the messages.
  strategy: "last",
  // Remember to adjust based on your model
  // or else pass a custom token_encoder
  tokenCounter: new ChatOpenAI({ modelName: "gpt-4" }),
  // Remember to adjust based on the desired conversation
  // length
  maxTokens: 45,
  // Most chat models expect that chat history starts with either:
  // (1) a HumanMessage or
  // (2) a SystemMessage followed by a HumanMessage
  startOn: "human",
  // Most chat models expect that chat history ends with either:
  // (1) a HumanMessage or
  // (2) a ToolMessage
  endOn: ["human", "tool"],
  // Usually, we want to keep the SystemMessage
  // if it's present in the original history.
  // The SystemMessage has special instructions for the model.
  includeSystem: true,
});
```

## 长期记忆

LangGraph 中的长期记忆允许系统在不同对话或会话中保留信息。与线程范围的短期记忆不同，长期记忆保存在自定义的“命名空间”中。

LangGraph 将长期记忆作为 JSON 文档存储在 [存储](https://github.langchain.ac.cn/langgraphjs/concepts/persistence/#memory-store) （ [参考文档](https://github.langchain.ac.cn/langgraphjs/reference/classes/checkpoint.BaseStore.html) ）中。每个记忆都组织在一个自定义的 `namespace` （类似于文件夹）和一个独特的 `key` （像文件名）下。命名空间通常包含用户或组织ID或其他标签，以便更容易组织信息。这种结构支持记忆的层次化组织。然后通过内容过滤器支持跨命名空间搜索。请参见下面的示例。

```typescript
import { InMemoryStore } from "@langchain/langgraph";

// InMemoryStore saves data to an in-memory dictionary. Use a DB-backed store in production use.
const store = new InMemoryStore();
const userId = "my-user";
const applicationContext = "chitchat";
const namespace = [userId, applicationContext];
await store.put(namespace, "a-memory", {
  rules: [
    "User likes short, direct language",
    "User only speaks English & TypeScript",
  ],
  "my-key": "my-value",
});
// get the "memory" by ID
const item = await store.get(namespace, "a-memory");
// list "memories" within this namespace, filtering on content equivalence
const items = await store.search(namespace, {
  filter: { "my-key": "my-value" },
});
```

当向智能体添加长期记忆时，重要的是要考虑如何 **写入记忆** 、如何 **存储和管理记忆更新** ，以及如何为应用程序中的 LLM **召回和表示记忆** 。这些问题都是相互关联的：您希望如何为 LLM 召回和格式化记忆，决定了您应该存储什么以及如何管理它。此外，每种技术都有其权衡。正确的方法在很大程度上取决于您应用程序的需求。LangGraph 旨在为您提供低级原语，以便您根据记忆 [存储](https://github.langchain.ac.cn/langgraphjs/concepts/persistence/#memory-store) 直接控制应用程序的长期记忆。

长期记忆远非一个已解决的问题。虽然很难提供通用建议，但我们在下面提供了一些可靠的模式供您在实现长期记忆时参考。

**您希望在“主路径”中写入记忆还是在“后台”写入记忆？**

记忆可以作为主要应用程序逻辑的一部分（例如，在应用程序的“主路径”上）或作为后台任务（作为根据主要应用程序状态生成记忆的独立函数）进行更新。我们在 [下面的写入记忆部分](#writing-memories) 中记录了每种方法的一些权衡。

**您希望将记忆作为单个档案管理还是作为文档集合管理？**

我们提供了两种管理长期记忆的主要方法：单个持续更新的文档（称为“档案”或“模式”）或文档集合。每种方法都有其自身的好处，具体取决于您需要存储的信息类型以及您打算如何访问它。

当您希望记住有关用户、组织或其他实体（包括智能体本身）的范围明确、具体的信息时，将记忆作为单个、持续更新的“档案”或“模式”进行管理非常有用。您可以预先定义档案的模式，然后使用 LLM 根据交互进行更新。查询“记忆”很容易，因为它只是对 JSON 文档的简单 GET 操作。我们在 [记住档案](#manage-individual-profiles) 中更详细地解释了这一点。这种技术可以提供更高的准确性（在已知信息用例中），但召回率较低（因为您必须预测和建模您的领域，并且文档更新倾向于以更高的频率删除或重写旧信息）。

另一方面，将长期记忆作为文档集合进行管理，可以存储无限量的信息。当您希望在长时间范围内重复提取和记住项目时，这项技术非常有用，但随着时间的推移，查询和管理可能会更复杂。与“档案”记忆类似，您仍然为每个记忆定义模式。您将插入新文档（并在此过程中可能更新或重新情境化现有文档），而不是覆盖单个文档。我们在 [“管理记忆集合”](#manage-a-collection-of-memories) 中更详细地解释了这种方法。

**您希望将记忆作为更新的指令还是作为少量样本示例呈现给您的智能体？**

记忆通常作为系统提示的一部分提供给 LLM。为 LLM“框架”记忆的一些常见方式包括提供原始信息，如“与用户 A 之前交互的记忆”，作为系统指令或规则，或作为少量样本示例。

将记忆框定为“学习规则或指令”通常意味着将系统提示的一部分专门用于 LLM 可以自行管理的指令。在每次对话后，您可以提示 LLM 评估其性能并更新指令，以便将来更好地处理此类任务。我们在 [本节](#update-own-instructions) 中更详细地解释了这种方法。

将记忆存储为少量样本示例，可以让您将指令存储和管理为因果关系。每个记忆都存储一个输入或上下文以及预期的响应。包含推理轨迹（思维链）也有助于提供足够的上下文，从而降低未来错误使用记忆的可能性。我们在 [本节](#few-shot-examples) 中更详细地阐述了这一概念。

我们将在以下部分详细介绍写入、管理以及召回和格式化记忆的技术。

### 写入记忆

人类在睡眠时形成长期记忆，但我们的智能体何时以及如何创建新记忆？我们看到智能体写入记忆的两种最常见方式是“在主路径中”和“在后台”。

#### 在主路径中写入记忆

这涉及在应用程序运行时创建记忆。举一个流行的生产示例，ChatGPT 使用“save\_memories”工具以内容字符串的形式插入（upsert）记忆。它每次收到用户消息时都会决定是否（以及如何）使用此工具，并将记忆管理与其他用户指令多任务处理。

这有几个好处。首先，它“实时”发生。如果用户立即开始一个新线程，该记忆将存在。用户也能透明地看到记忆何时被存储，因为机器人必须明确决定存储信息并将其与用户关联起来。

这也有几个缺点。它使智能体必须做出的决策（要提交什么到记忆中）变得复杂。这种复杂性会降低其工具调用性能并降低任务完成率。它会减慢最终响应速度，因为它需要决定要提交什么到记忆中。它通常还会导致更少的东西被保存到记忆中（因为助手是多任务的），这将在后续对话中导致 **较低的召回率** 。

#### 在后台写入记忆

这涉及将记忆更新作为一个概念上独立的任务，通常是作为完全独立的图或函数。由于它在后台发生，因此不会产生延迟。它还将应用程序逻辑与记忆逻辑分离，使其更模块化且易于管理。它还允许您分离记忆创建的时间，从而避免重复工作。您的智能体可以专注于完成其即时任务，而无需刻意思考需要记住什么。

然而，这种方法并非没有缺点。您必须考虑多久写入一次记忆。如果它不是实时运行，用户在其他线程上的交互将无法从新上下文中受益。您还必须考虑何时触发此作业。我们通常建议在某个时间点后安排记忆，如果给定线程上发生新事件，则取消并重新安排未来的记忆。其他流行的选择是根据 cron 计划形成记忆，或让用户或应用程序逻辑手动触发记忆形成。

### 管理记忆

一旦您理清了记忆调度，重要的是要考虑 **如何用新信息更新记忆** 。

有两种主要方法：您可以持续更新单个文档（记忆档案），或者每次收到新信息时插入新文档。

我们将在下面概述这两种方法之间的一些权衡，理解大多数人会发现结合这两种方法并在中间找到平衡点是最合适的。

#### 管理个人档案

档案通常只是一个 JSON 文档，包含您选择的各种键值对来表示您的领域。在记忆档案时，您会希望确保每次都 **更新** 档案。因此，您会希望传入先前的档案并要求 LLM 生成一个新的档案（或一些要应用于旧档案的 JSON 补丁）。

文档越大，就越容易出错。如果您的文档变得 **过大** ，您可能需要考虑将档案拆分为不同的部分。在生成文档时，您可能需要使用带重试的生成和/或 **严格** 解码，以确保记忆模式保持有效。

#### 管理记忆集合

将记忆保存为文档集合可以简化一些事情。每个单独的记忆可以范围更窄，更容易生成。这也意味着您随着时间的推移 **丢失** 信息的可能性更小，因为 LLM 为新信息生成 *新* 对象比将其与密集档案中的信息进行协调更容易。这通常会导致下游的召回率更高。

这种方法将一些复杂性转移到您如何提示 LLM 应用记忆更新上。您现在必须使 LLM 能够 *删除* 或 *更新* 列表中的现有项目。提示 LLM 执行此操作可能很棘手。一些 LLM 可能会默认过度插入；另一些可能会默认过度更新。在此处调整行为最好通过评估来完成，您可以使用 [LangSmith](https://langsmith.langchain.ac.cn/tutorials/Developers/evaluation) 等工具来做到这一点。

这也将复杂性转移到记忆 **搜索** （召回）上。您必须考虑使用哪些相关项目。目前我们支持按元数据过滤。我们很快将添加语义搜索。

最后，这也将一些复杂性转移到您如何为 LLM 表示记忆（以及由此引申出的用于保存每个记忆的模式）上。编写很容易在脱离上下文时被误解的记忆非常容易。重要的是要提示 LLM 在给定记忆中包含所有必要的上下文信息，以便您在后续对话中使用它时不会错误地误用该信息。

### 表示记忆

一旦您保存了记忆，您随后检索并向 LLM 呈现记忆内容的方式，将在很大程度上影响您的 LLM 在其响应中整合这些信息的表现。以下部分介绍了两种常见方法。请注意，这些部分也将主要指导您如何写入和管理记忆。记忆中的一切都是相互关联的！

#### 更新自己的指令

虽然指令通常是开发者编写的静态文本，但许多 AI 应用程序受益于允许用户个性化智能体在与该用户交互时应遵循的规则和指令。理想情况下，这可以通过智能体与用户的交互来推断（因此用户无需在您的应用程序中明确更改设置）。从这个意义上说，指令是长篇记忆的一种形式！

应用此功能的一种方法是使用“反思”或“元提示”步骤。向 LLM 提示当前的指令集（来自系统提示）以及与用户的对话，并指示 LLM 精炼其指令。这种方法允许系统动态更新和改进其自身行为，从而可能在各种任务上获得更好的性能。这对于那些难以预先指定指令的任务特别有用。

元提示使用过往信息来精炼提示。例如，一个 [推文生成器](https://www.youtube.com/watch?v=Vn8A3BxfplE) 采用元提示来增强其针对 Twitter 的论文摘要提示。您可以使用 LangGraph 的记忆存储来实现此功能，将更新的指令保存在共享命名空间中。在这种情况下，我们将记忆命名为“agent\_instructions”，并根据智能体给记忆加键。

```typescript
import { BaseStore } from "@langchain/langgraph/store";
import { State } from "@langchain/langgraph";
import { ChatOpenAI } from "@langchain/openai";

// Node that *uses* the instructions
const callModel = async (state: State, store: BaseStore) => {
  const namespace = ["agent_instructions"];
  const instructions = await store.get(namespace, "agent_a");
  // Application logic
  const prompt = promptTemplate.format({
    instructions: instructions[0].value.instructions,
  });
  // ... rest of the logic
};

// Node that updates instructions
const updateInstructions = async (state: State, store: BaseStore) => {
  const namespace = ["instructions"];
  const currentInstructions = await store.search(namespace);
  // Memory logic
  const prompt = promptTemplate.format({
    instructions: currentInstructions[0].value.instructions,
    conversation: state.messages,
  });
  const llm = new ChatOpenAI();
  const output = await llm.invoke(prompt);
  const newInstructions = output.content; // Assuming the LLM returns the new instructions
  await store.put(["agent_instructions"], "agent_a", {
    instructions: newInstructions,
  });
  // ... rest of the logic
};
```

#### 少量样本示例

有时“展示”比“讲述”更容易。LLM 善于从示例中学习。少量样本学习允许您通过用输入-输出示例更新提示来 [“编程”](https://x.com/karpathy/status/1627366413840322562) 您的 LLM，以说明预期的行为。虽然可以使用各种 [最佳实践](https://js.langchain.ac.cn/docs/concepts/#1-generating-examples) 来生成少量样本示例，但挑战通常在于根据用户输入选择最相关的示例。

请注意，记忆存储只是将数据存储为少量样本示例的一种方式。如果您希望有更多开发人员参与，或者将少量样本更紧密地与您的评估工具结合，您还可以使用 [LangSmith 数据集](https://langsmith.langchain.ac.cn/how_to_guides/datasets) 来存储您的数据。然后，动态少量样本选择器可以开箱即用地实现相同目标。LangSmith 将为您索引数据集，并根据关键字相似性（ [使用类似 BM25 的算法](https://langsmith.langchain.ac.cn/how_to_guides/datasets/index_datasets_for_dynamic_few_shot_example_selection) 进行基于关键字的相似性）启用检索与用户输入最相关的少量样本示例。

有关 LangSmith 中动态少量样本示例选择的示例用法，请参见此操作 [视频](https://www.youtube.com/watch?v=37VaU7e7t5o) 。此外，请参见这篇 [博客文章](https://blog.langchain.dev/few-shot-prompting-to-improve-tool-calling-performance/) ，展示了如何使用少量样本提示来提高工具调用性能，以及这篇 [博客文章](https://blog.langchain.dev/aligning-llm-as-a-judge-with-human-preferences/) ，展示了如何使用少量样本示例来使 LLM 与人类偏好保持一致。