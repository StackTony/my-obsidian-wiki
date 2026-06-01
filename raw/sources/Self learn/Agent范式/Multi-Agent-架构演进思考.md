---
credibility: low
---
## 从单兵作战到群智协作：Multi-agent 架构演进与思考

[社区首页](https://cloud.tencent.com/developer) > [专栏](https://cloud.tencent.com/developer/column) >从单兵作战到群智协作：Multi-agent 架构演进与思考

> ❝当一个 Agent 不够用时，你需要的不是更强的模型，而是更好的协作架构。❞

---

### 写在前面

大模型时代，单个 Agent 能做的事情越来越多——搜索、写代码、分析数据、调用 API。但当任务复杂到一定程度，单体 Agent 的局限性就显现出来了：上下文窗口不够用、专业能力被稀释、系统提示词变成了"万能缝合怪"。

多 Agent 架构应运而生。它的核心思想很简单： **「让不同的 Agent 各司其职，通过某种协作机制共同完成复杂任务」** 。

但"协作机制"这四个字背后，藏着大量的设计决策。本文将从业界主流模式出发，逐层深入到工程实现细节，帮你建立对多 Agent 架构的系统性理解。

---

### 一、三种基础模式：几乎所有框架都绕不开

纵观当前主流 Agent 框架（OpenAI Swarm、LangGraph、AutoGen、CrewAI 等），多 Agent 协作的基础模式可以归纳为三种。

#### 1.1 Handoff / Transfer（控制权移交）

**「一句话概括」** ：当前 Agent 判断"这事不归我管"，把控制权完整交给另一个 Agent。

```javascript
用户 → [售前客服 Agent]
             │
             ├── "我要退货" → 移交给 [售后 Agent]
             ├── "系统报错了" → 移交给 [技术支持 Agent]
             └── "推荐个产品" → 自己处理
```

**「核心特征」** ：

- 同一时刻只有一个 Agent 在工作
- 控制权是"完整移交"，原 Agent 退出执行
- 移交决策由 LLM 自主判断

**「关键实现」** ：Transfer 模式有一个巧妙的设计—— `transfer_to_agent` 工具被调用时 **「不直接执行目标 Agent」** ，而只是打一个标记：

```javascript
// transfer_to_agent 工具：只打标记，不直接执行
func (t *TransferTool) Call(ctx context.Context, jsonArgs []byte) (any, error) {
    var req Request
    json.Unmarshal(jsonArgs, &req)

    // 从上下文获取当前 invocation
    invocation, _ := agent.InvocationFromContext(ctx)

    // 只在 invocation 上打一个标记，标记"要移交给谁"
    invocation.TransferInfo = &agent.TransferInfo{
        TargetAgentName: req.AgentName,
        Message:         req.Message,
    }

    // 立即返回，不在这里启动目标 Agent
    return Response{
        Success:     true,
        Message:     "Transfer initiated to agent: " + req.AgentName,
        TransferType: "agent_handoff",
    }, nil
}
```

真正执行目标 Agent 的是管线中的 **「TransferResponseProcessor」** ，它在工具执行完毕后的下一个处理阶段启动：

```javascript
// TransferResponseProcessor：在管线的正确阶段执行移交
func (p *TransferResponseProcessor) ProcessResponse(
    ctx context.Context,
    invocation *agent.Invocation,
    req *model.Request,
    rsp *model.Response,
    ch chan<- *event.Event,
) {
    // 检查是否有待处理的移交标记
    if invocation.TransferInfo == nil {
        return// 没有移交请求，正常继续
    }

    targetAgentName := invocation.TransferInfo.TargetAgentName

    // 查找目标 Agent
    targetAgent := invocation.Agent.FindSubAgent(targetAgentName)

    // 安全校验：通过 TransferController 检查循环移交、次数限制等
    if controller, ok := agent.GetRuntimeStateValue[agent.TransferController](
        &invocation.RunOptions, agent.RuntimeStateKeyTransferController,
    ); ok && controller != nil {
        nodeTimeout, err := controller.OnTransfer(ctx, invocation.AgentName, targetAgentName)
        if err != nil {
            // 移交被拒绝（如循环检测触发）
            return
        }
    }

    // 创建目标 Agent 的 invocation
    targetInvocation := invocation.Clone(
        agent.WithInvocationAgent(targetAgent),
    )

    // 在正确的上下文中启动目标 Agent
    targetEventChan, _ := agent.RunWithPlugins(ctx, targetInvocation, targetAgent)

    // 将目标 Agent 的事件原样转发到最外层
    for targetEvent := range targetEventChan {
        event.EmitEvent(ctx, ch, targetEvent)
    }

    // 结束原 Agent 的 invocation
    invocation.TransferInfo = nil
    invocation.EndInvocation = true
}
```

**「为什么要这样设计？」** 这里有四个关键原因：

1. **「执行上下文不对」** ： `Call()` 在工具执行处理器中被调用，返回值只是一个字符串。但 Transfer 的语义是"我不干了，你来接管"——目标 Agent 的流式事件、子工具调用等无法通过一个字符串返回值传递。
2. **「管线处理顺序」** ：一次 LLM 响应要经过多个处理器（工具执行 → 移交处理 → 规划处理 → 输出处理），如果在工具执行阶段就启动了目标 Agent，后续处理器的逻辑就被跳过了。
3. **「可以被拦截和拒绝」** ：TransferProcessor 会先做安全校验——移交次数是否超限？是否出现了循环移交（A→B→A→B）？这些防护如果在 `Call()` 里就直接执行了，就没有插入点了。
4. **「事件流的所有权不同」** ：工具处理器需要把结果"回填"给 LLM，而 Transfer 需要把目标 Agent 的事件"原样转发"到最外层——两种完全不同的事件语义。

**「代表框架」** ：OpenAI Swarm（最早提出 handoff 概念）、Anthropic Claude 的 tool\_use + routing。

**「适用场景」** ：客服路由、多角色助手、分工明确的垂直场景。

#### 1.2 Coordinator / Orchestrator（中心编排）

**「一句话概括」** ：一个"指挥官"Agent 持有全局视角，按需调用各专家 Agent，综合结果后给出最终答案。

```javascript
用户 → [协调者 Agent]
             │
             ├── 调用 [需求分析师] → "需要处理高并发..."
             ├── 调用 [方案设计师] → "建议用 Redis 预扣减..."
             ├── 调用 [质量审查员] → "风险：Redis 宕机无降级..."
             ├── 再次调用 [方案设计师] → "补充降级方案..."
             │
             └── 协调者综合所有信息 → 最终答案
```

**「核心特征」** ：

- 有一个明确的"中心决策者"
- 成员 Agent 被协调者按需调用，可以多轮迭代
- 协调者能看到所有成员的输出，做最终综合

**「关键实现」** ：Coordinator 模式的核心设计是 **「把成员 Agent 包装成 Tool」** ，让协调者通过 LLM 的 Function Calling 来调度：

```javascript
// 创建 Coordinator Team 时，成员被包装成 Tool
func newMemberToolSet(members []agent.Agent) tool.ToolSet {
    tools := make([]tool.Tool, 0, len(members))
    for _, m := range members {
        // 把每个成员 Agent 包装成一个 AgentTool
        tools = append(tools, agenttool.NewTool(m))
    }
    return &staticToolSet{tools: tools}
}

// 协调者直接委托给 coordinator Agent，它会通过 function calling 调度成员
func (t *Team) runCoordinator(ctx context.Context, invocation *agent.Invocation) (<-chan *event.Event, error) {
    return t.coordinator.Run(ctx, invocation)
}
```

AgentTool 的 `Call()` 方法——当协调者 LLM 通过 function calling 选择某个成员时，实际执行逻辑：

```javascript
// AgentTool.Call：协调者通过 function calling 调用成员 Agent
func (at *Tool) Call(ctx context.Context, jsonArgs []byte) (any, error) {
    // LLM 传来的参数作为用户消息发给子 Agent
    message := model.NewUserMessage(string(jsonArgs))

    // 复用父 invocation 的 session，让子 Agent 能看到对话历史
    if parentInv, ok := agent.InvocationFromContext(ctx); ok && parentInv.Session != nil {
        // 克隆父 invocation，设置子 Agent 自己的事件过滤键
        subInv := parentInv.Clone(
            agent.WithInvocationAgent(at.agent),
            agent.WithInvocationMessage(message),
            agent.WithInvocationEventFilterKey(childKey),
        )

        // 运行子 Agent
        subCtx := agent.NewInvocationContext(ctx, subInv)
        evCh, _ := agent.RunWithPlugins(subCtx, subInv, at.agent)

        // 收集子 Agent 的所有响应，拼成一个字符串返回给协调者
        return at.collectResponse(evCh)
    }

    // 没有父上下文时，创建一个隔离的执行环境
    return at.callWithIsolatedRunner(ctx, message)
}
```

**「为什么要包装成 Tool 而非直接调用？」** 四个设计考量：

1. **「让 LLM 成为调度器」** ：LLM 可以动态决定调不调、调谁、调几次、什么顺序，甚至并行调多个——这些灵活性硬编码方式无法实现。
2. **「复用 Function Calling 管线」** ：所有主流模型都支持 `tool_calls` → 执行 → 结果回填 → 继续推理的标准协议，不需要发明新的通信机制。
3. **「"免费"获得工具生态能力」** ：并行调用、流式输出透传、历史共享、事件追踪等能力自动可用。
4. **「支持多轮迭代推理」** ：协调者可以根据前一轮结果决定是否追问、补充、甚至推翻重来，这在 Tool 协议下天然支持。

**「代表框架」** ：LangGraph 的 Supervisor、AutoGen 的 GroupChat with selector、CrewAI 的 `Process.hierarchical` 。

**「适用场景」** ：复杂任务分解（研究报告撰写、系统设计、多步骤分析）。

#### 1.3 Swarm / Peer-to-Peer（去中心化群体协作）

**「一句话概括」** ：没有中心控制者，每个 Agent 自主决定下一步找谁，像一群人自由讨论。

```javascript
[Agent A] ←→ [Agent B]
    ↕              ↕
[Agent C] ←→ [Agent D]

每个 Agent 都知道其他成员的存在，
自主决定把对话传递给谁。
```

**「核心特征」** ：

- 完全去中心化，无指挥官
- 每个 Agent 都能主动发起与其他 Agent 的交互
- 系统行为涌现自个体决策，灵活但难以控制

**「关键实现」** ：Swarm 模式在初始化时让每个成员"知道"其他所有成员的存在，运行时从入口成员开始，通过 Transfer 机制在成员间流转：

```javascript
// 创建 Swarm Team
func NewSwarm(name, entryName string, members []agent.Agent) (*Team, error) {
    // 让每个成员知道其他所有成员——互相设置为 SubAgent
    wireSwarmRoster(members)

    return &Team{
        mode:      ModeSwarm,
        entryName: entryName,
        members:   members,
    }, nil
}

// wireSwarmRoster：为每个成员设置其他所有成员为 SubAgent
func wireSwarmRoster(members []agent.Agent) error {
    for _, m := range members {
        setter := m.(agent.SubAgentSetter)
        roster := make([]agent.Agent, 0, len(members)-1)
        for _, other := range members {
            if other.Info().Name != m.Info().Name {
                roster = append(roster, other) // 除了自己以外的所有成员
            }
        }
        setter.SetSubAgents(roster)
    }
    returnnil
}

// 运行 Swarm：从入口成员开始，后续通过 transfer_to_agent 自由流转
func (t *Team) runSwarm(ctx context.Context, invocation *agent.Invocation) (<-chan *event.Event, error) {
    entry := t.memberByName[t.entryName]

    // 注入 Swarm 运行时控制器（循环检测、次数限制等）
    ensureSwarmRuntime(invocation, t.swarm)

    child := invocation.Clone(agent.WithInvocationAgent(entry))
    return entry.Run(agent.NewInvocationContext(ctx, child), child)
}
```

Swarm 运行时控制器——防止无限循环移交：

```javascript
// swarmRuntime 实现 TransferController 接口
func (sr *swarmRuntime) OnTransfer(ctx context.Context, fromAgent, toAgent string) (time.Duration, error) {
    sr.count++
    // 检查最大移交次数
    if sr.cfg.MaxHandoffs > 0 && sr.count > sr.cfg.MaxHandoffs {
        return0, errors.New("max handoffs exceeded")
    }
    // 检查循环移交（滑动窗口内的唯一 Agent 数量过低）
    sr.recent = append(sr.recent, toAgent)
    iflen(sr.recent) == sr.cfg.RepetitiveHandoffWindow &&
        uniqueCount(sr.recent) < sr.cfg.RepetitiveHandoffMinUnique {
        return0, errors.New("repetitive handoff detected")
    }
    return sr.cfg.NodeTimeout, nil
}
```

**「代表框架」** ：OpenAI Swarm、AutoGen 的 `RoundRobinGroupChat` 。

**「适用场景」** ：头脑风暴、多角色辩论、开放式探索。

---

### 二、不止三种：业界的更多模式

上述三种是"基础原语"，但真实世界的需求往往更复杂。业界还发展出了以下几种重要模式。一个共同的问题是： **「Agent 之间如何传递输入和输出？」**

#### 2.1 Pipeline / Chain（流水线）

Agent A → Agent B → Agent C，按 **「预定义顺序」** 执行，上一个的输出是下一个的输入。

```javascript
[规划 Agent] → [研究 Agent] → [写作 Agent] → [审校 Agent]
     ↓              ↓              ↓              ↓
   制定计划      搜集资料        起草文章        校对发布
```

**「与 Coordinator 的关键区别」** ：没有决策者，流转顺序在编码时就已确定。

**「输入输出传递机制」** ：Chain 模式的所有子 Agent **「共享同一个 Session」** 。上一个 Agent 的输出以事件形式写入 Session，下一个 Agent 启动时从 Session 中读取这些事件作为上下文。本质上是 **「通过共享会话传递信息」** 。

```javascript
// Chain 模式核心：按顺序遍历执行子 Agent
func (a *ChainAgent) executeSubAgents(ctx context.Context, invocation *agent.Invocation, ...) {
    for _, subAgent := range a.subAgents {
        // 从基础 invocation 克隆——共享同一个 Session
        // 上一个 Agent 的输出已经作为事件写入了 Session
        subInvocation := invocation.Clone(
            agent.WithInvocationAgent(subAgent),
        )

        // 直接调用子 Agent，不经过任何工具包装
        subEventChan, _ := agent.RunWithPlugins(ctx, subInvocation, subAgent)

        // 转发子 Agent 的所有事件
        for subEvent := range subEventChan {
            // 记录完整响应（下一个 Agent 可以通过 Session 看到）
            if subEvent.Response != nil && !subEvent.Response.IsPartial {
                fullRespEvent = subEvent
            }
            event.EmitEvent(ctx, eventChan, subEvent)
        }
    }
}
```

关键点： `invocation.Clone()` 会继承父 invocation 的 `Session` ，这意味着所有子 Agent 共享同一个会话。Agent B 启动时，Session 中已经包含了 Agent A 的输出，Agent B 的内容处理器会把这些历史事件提取为 LLM 的消息上下文。

**「代表框架」** ：LangChain 的 LCEL chain、CrewAI 的 `Process.sequential` 。

#### 2.2 Cycle / Loop（循环迭代）

在 Pipeline 基础上加入 **「循环」** ——Agent 反复执行直到满足退出条件（如质量达标、达到最大轮次）。

```javascript
[生成 Agent] → [评估 Agent] ─── 不合格 ──→ [生成 Agent]（重来）
                    │
                    └── 合格 → 输出结果
```

**「输入输出传递机制」** ：与 Chain 相同，通过共享 Session 传递。但增加了两个控制维度—— **「最大迭代次数」** 和 **「升级函数（Escalation Function）」** 。

升级函数检查子 Agent 产出的事件内容来判断是否应该退出循环。例如，评估 Agent 返回"质量合格"的工具响应时，升级函数返回 `true` ，循环终止：

```javascript
// Cycle 模式核心：带退出条件的循环执行
func (a *CycleAgent) Run(ctx context.Context, invocation *agent.Invocation) (<-chan *event.Event, error) {
    // ...
    var timesLooped int

    // 主循环：直到达到最大迭代次数或触发退出条件
    for a.maxIterations == nil || timesLooped < *a.maxIterations {
        // 一轮循环 = 按顺序执行所有子 Agent
        if a.runSubAgentsLoop(ctx, invocation, eventChan, &fullRespEvent) {
            break// 升级条件触发，退出循环
        }
        timesLooped++
    }
}

// 升级条件判断：检查事件是否表明应该退出循环
func (a *CycleAgent) shouldEscalate(evt *event.Event) bool {
    // 支持自定义升级函数
    if a.escalationFunc != nil {
        return a.escalationFunc(evt)
    }
    // 默认：错误事件触发退出
    return evt.Error != nil
}

// 单个子 Agent 执行：边运行边检查退出条件
func (a *CycleAgent) runSubAgent(ctx context.Context, subAgent agent.Agent, ...) bool {
    subInvocation := invocation.Clone(agent.WithInvocationAgent(subAgent))
    subEventChan, _ := agent.RunWithPlugins(ctx, subInvocation, subAgent)

    for subEvent := range subEventChan {
        event.EmitEvent(ctx, eventChan, subEvent)
        // 每收到一个事件就检查：是否该退出了？
        if a.shouldEscalate(subEvent) {
            returntrue// 退出循环
        }
    }
    returnfalse// 继续下一轮
}
```

每一轮循环中，子 Agent 都能看到上一轮所有 Agent 的输出（通过共享 Session），从而实现"迭代改进"。

**「适用场景」** ：代码生成+自我修复、迭代优化、质量检验循环。

#### 2.3 Graph / DAG（有向无环图）

最灵活的一种——Agent 之间的流转关系用 **「图」** 来定义，支持条件分支、并行执行、汇合。

```javascript
[开始] → [分类器] ─── 简单问题 ───→ [快速回答] → [结束]
              │
              └── 复杂问题 ──→ [研究] → [分析] ──┐
                                 ↑                │
                                 └── 需要更多信息 ─┘
                                              └── 完成 → [结束]
```

**「输入输出传递机制」** ：Graph 模式使用\*\*共享 State（状态字典）\*\*来传递数据。每个节点执行后返回一个状态更新（State Delta），框架通过 Reducer 函数将更新合并到全局状态。后续节点读取全局状态获取输入。

```javascript
// Graph 中的 Agent 节点：直接调用 agent.Run()
func NewAgentNodeFunc(agentName string, opts ...Option) NodeFunc {
    returnfunc(ctx context.Context, state State) (any, error) {
        // 从全局 State 中查找目标 Agent
        targetAgent := findAgentFromState(state, agentName)

        // 可选：把上一个节点的 last_response 映射为当前节点的 user_input
        parentForInput := mapParentInputFromLastResponse(state, cfg.inputFromLast)

        // 构建子 invocation，注入当前状态
        invocation := buildAgentInvocation(ctx, parentForInput, childState, targetAgent)

        // 直接调用 Agent（不是工具！）
        agentEventChan, _ := targetAgent.Run(subCtx, invocation)

        // 处理事件流，收集最终输出
        streamRes := processAgentEventStream(ctx, agentEventChan, ...)

        // 返回状态更新——写入 last_response 和 node_responses
        return State{
            "last_response":  streamRes.lastResponse,
            "node_responses": map[string]any{nodeID: streamRes.lastResponse},
            "user_input":     "", // 清空，防止下游节点重复消费
        }, nil
    }
}

// 上一个节点的输出 → 当前节点的输入
func mapParentInputFromLastResponse(state State, enabled bool) State {
    if !enabled {
        return state
    }
    lastResponse := state["last_response"].(string) // 上一个节点的输出
    cloned := state.Clone()
    cloned["user_input"] = lastResponse // 变成当前节点的输入
    return cloned
}
```

条件边——根据状态动态决定下一步走向哪个节点：

```javascript
// 添加条件边：根据 State 内容动态路由
graph.AddConditionalEdges("classifier",
    // 条件函数：读取 State，返回下一个节点
    func(ctx context.Context, state State) (ConditionResult, error) {
        msgs := state["messages"].([]model.Message)
        lastMsg := msgs[len(msgs)-1]
        if lastMsg.Content == "simple" {
            return ConditionResult{NextNodes: []string{"quick_answer"}}, nil
        }
        return ConditionResult{NextNodes: []string{"research"}}, nil
    },
    map[string]string{
        "quick_answer": "quick_answer",
        "research":     "research",
    },
)
```

**「代表框架」** ：LangGraph（核心卖点）、AutoGen 0.4 的 `GraphFlow` 。

#### 2.4 Hierarchical（层级委托）

树状结构，经理 → 组长 → 组员，逐层委托和汇报。

```javascript
[CEO Agent]
        /           \
  [Tech Lead]    [PM Agent]
  /        \         |
[Coder] [Tester] [Designer]
```

**「与 Coordinator 的区别」** ：多层嵌套，不是扁平的一层。

**「输入输出传递机制」** ：每一层都是一个 Coordinator 模式。CEO 把成员（Tech Lead、PM）包装成 Tool 调用，Tech Lead 内部再把 Coder、Tester 包装成 Tool 调用。输出沿调用链逆向返回——Coder 的结果返回给 Tech Lead，Tech Lead 汇总后返回给 CEO。

#### 2.5 Debate / Adversarial（对抗辩论）

两个或多个 Agent 持不同立场，通过辩论达成共识。

**「输入输出传递机制」** ：通常通过共享消息列表实现。一个 Agent 的发言追加到消息列表中，另一个 Agent 读取完整列表后产生回应，如此交替进行。循环退出条件可以是达成共识、达到最大轮次、或由第三方裁判 Agent 判定。

**「代表框架」** ：ChatDev 的代码审查流程（开发者 vs 审查者）、CAMEL 的 role-playing。

#### 各模式输入输出传递总结

| 模式 | 传递机制 | 说明 |
| --- | --- | --- |
| 「Chain」 | 共享 Session | 子 Agent 共享同一个会话，前者的输出作为后者的上下文 |
| 「Cycle」 | 共享 Session + 退出条件 | 同 Chain，但每轮都累积历史，升级函数控制退出 |
| 「Graph」 | 共享 State 字典 | 节点返回 State Delta，Reducer 合并，后续节点读取 |
| 「Coordinator」 | Tool 协议（参数→返回值） | LLM 通过 function calling 传参，收集字符串返回值 |
| 「Transfer」 | Invocation 克隆 | 目标 Agent 继承原 invocation 的 Session 和消息 |
| 「Swarm」 | Invocation 克隆 + Transfer 消息 | 同 Transfer，可附带转移消息 |
| 「Hierarchical」 | 嵌套 Tool 协议 | 多层 Coordinator 逐层传递 |
| 「Debate」 | 共享消息列表 | Agent 交替读写同一个消息队列 |

---

### 三、设计哲学：一个核心问题

看到这么多模式，你可能会觉得眼花缭乱。但它们本质上都在回答 **「同一个问题」** ：

> ❝ **「"谁来决定下一步由谁做什么？"」** ❞

根据这个问题的不同答案，所有模式可以归入三大流派：

| 决策方式 | 对应模式 | 特点 |
| --- | --- | --- |
| 「预定义（代码决策）」 | Pipeline / Chain / Cycle / Graph | 流转路径在编码时确定，确定性最强，最可控 |
| 「中心决策（LLM 统筹）」 | Coordinator / Hierarchical / Supervisor | 一个 LLM 统筹全局，灵活但有单点瓶颈 |
| 「去中心化（LLM 自治）」 | Transfer / Swarm / Debate | 每个 Agent 自主判断，最灵活但最难控制 |

实际工程中， **「混合使用」** 才是常态。比如：

- 顶层用 **「Coordinator」** 做任务规划
- 具体子任务内部用 **「Pipeline」** 顺序执行
- 遇到不确定情况用 **「Transfer」** 做动态路由
- 需要多视角验证时用 **「Debate」** 做质量把关

而不同的决策方式也直接决定了 Agent 间的 **「调用机制」** ：

| 模式 | 调度者 | Agent 间调用方式 | 原因 |
| --- | --- | --- | --- |
| 「Chain / Cycle」 | 代码（预定义顺序） | 直接调用 Run() | 顺序已定，不需要 LLM 决策 |
| 「Graph」 | 代码（图拓扑 + 条件边） | 直接调用 Run() | 拓扑已定，分支用条件函数 |
| 「Coordinator」 | LLM（动态决策） | 包装成 Tool | LLM 需要通过 Function Calling 表达调用意图 |
| 「Transfer/Swarm」 | LLM（动态路由） | 标记 + 后置处理器 Run() | LLM 只需表达"移交给谁"，执行在管线层面处理 |

**「核心规律」** ：

> ❝只有当调度决策由 LLM 做出时，才需要通过工具来实现。当调度决策由代码确定时，直接调用 Agent 更简单高效。 ❞

贯穿所有模式的统一抽象不是"工具"，而是 **「Agent 接口 + Event 流」** ：

```javascript
type Agent interface {
    // 统一的执行契约：接收 invocation，返回事件流
    Run(ctx context.Context, invocation *Invocation) (<-chan *event.Event, error)
    Tools() []tool.Tool
    Info() Info
    SubAgents() []Agent
    FindSubAgent(name string) Agent
}
```

不管是 Chain、Cycle、Graph、Coordinator 还是 Transfer，最终都是调用这个 `Run()` 方法，通过 Event Channel 获取结果。区别只在于 **「谁来决定调哪个 Agent、什么时候调、调用结果怎么处理」** 。

---

### 四、业界框架横向对比

| 框架 | 核心模式 | 特色 | Agent 间调用方式 |
| --- | --- | --- | --- |
| 「OpenAI Swarm」 | Handoff / Transfer | 最简单轻量，概念验证级别 | 标记 + 后置处理 |
| 「LangGraph」 | Graph (DAG) + Supervisor | 最灵活，状态机思维，支持任意拓扑 | 图节点直接调用 + Tool |
| 「AutoGen」 | GroupChat + Selector | 多 Agent 对话，支持人类参与 | 对话协议 + Tool |
| 「CrewAI」 | Sequential / Hierarchical | 角色化，最接近人类团队协作 | 直接调用 + Tool |
| 「CAMEL」 | Role-Playing + Debate | 学术导向，侧重 Agent 间协商 | 对话协议 |
| 「ChatDev」 | Pipeline + Review Cycle | 软件开发专用，固定流程 | 直接调用 |

---

### 五、实践建议

结合以上分析，给出几条实践建议：

#### 5.1 从简单模式开始

不要一上来就设计复杂的 Graph 或 Swarm。大多数场景，一个 **「Chain（流水线）」** 或 **「Coordinator（中心编排）」** 就够了。过早引入复杂性只会增加调试难度。

#### 5.2 根据"决策者"选择模式

- 如果你能在编码时画出流程图 → 用 **「Chain / Graph」**
- 如果需要 LLM 动态判断 → 用 **「Coordinator / Transfer」**
- 如果两者兼有 → **「混合使用」** （顶层 Coordinator，子流程内 Chain）

#### 5.3 关注事件流，而非调用方式

不管选择哪种模式， **「Event 流」** 才是系统可观测性的关键。确保：

- 每个 Agent 的执行事件都能被追踪
- 事件能正确归属到发出它的 Agent
- 流式输出能透传到最终用户

#### 5.4 为 Transfer 设置安全边界

如果使用 Transfer / Swarm 模式，务必设置：

- **「最大移交次数」** ：防止无限循环
- **「循环检测」** ：防止 A→B→A→B 死循环
- **「节点超时」** ：防止某个 Agent 无限运行

#### 5.5 Coordinator 的 Prompt 工程

Coordinator 模式的效果高度依赖协调者的系统提示词。关键要素：

- 明确告知协调者有哪些成员可用（Tool 描述要清晰）
- 指导协调者的决策策略（先分析再执行、需要审查才输出等）
- 设定综合输出的格式要求

---

### 总结

多 Agent 架构不是银弹，也不只有一种实现方式。核心是想清楚三个问题：

1. **「谁来决策」** ——代码预定义，还是 LLM 动态判断？
2. **「怎么调用」** ——直接 Run、包装成 Tool、还是标记后处理？
3. **「结果怎么流转」** ——回填给 LLM、直接转发给用户、还是写入共享状态？

回答好这三个问题，你就能为自己的场景选择最合适的架构模式。

> ❝ **「一句话送给你」** ：把"决策"交给最擅长的角色（LLM 或代码），把"执行"交给统一的接口（Agent.Run），把"可观测性"交给标准化的管道（Event 流）。这就是多 Agent 架构的本质。❞

本文参与 [腾讯云自媒体同步曝光计划](https://cloud.tencent.com/developer/support-plan) ，分享自微信公众号。

原始发表：2026-03-31，如有侵权请联系 [cloudcommunity@tencent.com](mailto:cloudcommunity@tencent.com) 删除

本文分享自 有文化的技术人 微信公众号，前往查看

如有侵权，请联系 [cloudcommunity@tencent.com](mailto:cloudcommunity@tencent.com) 删除。

本文参与 [腾讯云自媒体同步曝光计划](https://cloud.tencent.com/developer/support-plan) ，欢迎热爱写作的你一起参与！

目录

相关产品与服务

消息队列

腾讯云消息队列 TDMQ 是腾讯云自主研发的消息中间件产品系列，作为分布式系统中的关键组件，具备稳定可靠、高弹性、低成本的特性，提供异步通信的基础能力，通过应用解耦降低系统复杂度，提升系统可用性和可扩展性。兼容开源主流协议，包含 CKafka、RocketMQ、RabbitMQ、Pulsar、MQTT 五大子产品，覆盖在线（电商交易、社交直播等）、离线场景（大数据、日志监控等）和设备端场景（物联网、车联网等），满足金融、互联网、教育、物流、能源等不同行业和场景的需求。

[2026采购季 | AI焕新·智启新局](https://cloud.tencent.com/act/pro/featured-202604?from=21344&from_column=21344)