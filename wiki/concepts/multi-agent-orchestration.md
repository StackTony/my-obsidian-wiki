---
title: Multi-Agent协同编排
category: concepts
tags: [AI, Agent, Multi-Agent, 编排, 协同]
aliases: [多Agent协同, Multi-Agent编排, Agent协同]
source_dir: AI 人工智能/AI Agent/Multi-Agent协同
source_files: [多Agent协同：Oh My OpenCode 深度架构分析报告.md, 单Agent 智能体.md, 多 Agent 协作 github项目示例.md]
  # Self learn 补充（credibility: low）
  # source_dir: Self learn/Agent范式
  # source_files: [Multi-Agent-5种协调模式.md, Multi-Agent-架构演进思考.md, LangGraph-圣经-multi-agent入门.md]
provenance:
  extracted: 0.45
  inferred: 0.45
  ambiguous: 0.10
base_confidence: 0.58
lifecycle: draft
lifecycle_changed: 2026-09-16
tier: supporting
created: 2026-06-27
updated: 2026-09-16
summary: Multi-Agent协同编排是单Agent到多Agent的跃迁——关键设计模式包括角色分化与工具隔离、主编排+子执行分层、证据驱动完成标准、并发控制与防递归委派、completion_promise自动续跑
relationships:
  - target: "[[concepts/multi-agent-framework-comparison]]"
    type: extends
  - target: "[[concepts/agent-framework-engineering]]"
    type: extends
  - target: "[[entities/oh-my-opencode]]"
    type: derived_from
  - target: "[[concepts/harness-engineering]]"
    type: related_to
  - target: "[[concepts/agent-architecture-landscape]]"
    type: related_to
---

# Multi-Agent协同编排

Multi-Agent协同编排从"单Agent自由聊天"进化到"多角色分工协作+结构化编排"。不同于 [[concepts/multi-agent-framework-comparison|框架对比]] 关注的是选择哪个框架，本页关注的是**编排设计模式**——无论用什么框架，好的 multi-agent 系统都遵循相似的设计原则。

核心洞察来自 [[entities/oh-my-opencode|Oh My OpenCode]]（OMO）的实践：910 个源文件、11 个命名 agent、精细化工具权限矩阵、三级并发控制——这不是简单的"多个 agent 轮流说话"，而是有明确职责分工和工程约束的编排系统。

## 从单Agent到多Agent的跃迁

单Agent的局限：
- 上下文窗口有限，复杂任务容易迷失
- 同一个 agent 既做规划又做执行，"自己审查自己"有盲点
- 不同认知任务需要不同模型能力（规划需要强推理、搜索需要低成本、执行需要代码能力）

多Agent的核心价值不是"更多人干活"，而是**分工+约束+成本优化**： ^[inferred]
- 不同角色做不同认知任务，避免角色混淆
- 工具权限隔离防止"顾问自己动手"
- 低成本 agent 做搜索，高成本 agent 做推理，降低总体 token 消耗

## 编排设计模式

### 模式一：角色分化与工具隔离

OMO 的实践：每个 agent 有明确的职责边界和工具权限矩阵。

| 角色 | 允许 | 禁止 | 设计意图 |
|------|------|------|----------|
| 顾问（Oracle） | read, search | write, edit, task | 只给建议不动手 |
| 搜索（Explore/Librarian） | read, grep, search | write, edit, task, call_omo_agent | 只搜索不修改，不能派生子 agent |
| 规划（Prometheus） | read, write(.md only) | 写代码 | 只做计划不写代码 |
| 执行（Hephaestus） | 全部 | 询问用户 | 100% 自主执行 |

**设计原则**：权限越少越安全，但分工越细协调成本越高。关键是在安全和效率之间找到平衡。 ^[inferred]

### 模式二：主编排 + 子执行分层

OMO 的 Sisyphus 是"管理者"而非"执行者"——委派优先，自己动手是最后选择。分阶段决策流水线：

```
Phase 0 (Intent Gate) → 意图分类（Trivial/Explicit/Exploratory/Open-ended/Ambiguous）
Phase 1 (Codebase Assessment) → 评估代码库状态
Phase 2A/2B/2C → 根据意图走不同路径
Phase 3 (Completion) → 证据驱动的完成标准
```

**为什么委派优先**：主编排 agent 的价值在于判断"应该让谁做"，而非"自己做得更好"。这是管理思维而非执行思维。 ^[inferred]

### 模式三：双轨主Agent哲学

不同任务需要不同的行为模式——有些适合快速委派，有些适合深度自主。

| 维度 | 编排型（Sisyphus） | 自主型（Hephaestus） |
|------|--------------------|--------------------|
| 行为 | 委派优先，自己动手是最后选择 | 禁止询问，只管做 |
| 完成标准 | 委派→验证结果 | 100% OR NOTHING |
| 适用 | 协调型任务（"帮我查一下这个 API"） | 深度执行（"重构整个认证模块"） |
| 风险 | 可能过度委派导致延迟 | 可能忽略用户意图 |

**Prompt 工程实践表明**：行为模式切换比参数微调更可靠——LLM 对"你是管理者"和"你是执行者"的响应差异远大于 "autonomy=0.7 vs 0.3"。 ^[inferred]

### 模式四：证据驱动完成标准

OMO 的 Sisyphus 要求每个任务有明确的完成证据：

| 动作类型 | 完成标准 |
|----------|----------|
| File edit | `lsp_diagnostics` clean on changed files |
| Build command | Exit code 0 |
| Test run | All tests pass |
| Delegation | Agent result received and verified |
| NO EVIDENCE | = NOT COMPLETE |

这与 [[concepts/harness-engineering|Harness Engineering]] 中"约束必须机械化"的原则一致——完成标准不是 prompt 里的软约束，而是工具返回的硬证据。 ^[inferred]

### 模式五：并发控制与防递归委派

并发控制是 multi-agent 系统的工程难点。OMO 的三级并发控制：

```
模型级限制（如 Opus 2并发、Haiku 10并发）
  → Provider 级限制（如 Anthropic 5并发）
    → 全局默认（5并发）
```

**防递归委派**：Sisyphus-Junior 允许 `call_omo_agent` 但禁止 `task`——可以调搜索 agent 但不能委派新 task，防止无限递归。这类似于 [[concepts/agent-framework-engineering|Agent框架工程]] 中"可观测状态机"的边界约束思想。 ^[inferred]

### 模式六：completion_promise 自动续跑

Ralph Loop 的 `completion_promise` 机制让用户定义"完成"的标准，agent 在输出中搜索该字符串。这是 [[concepts/harness-engineering|Harness Engineering]] 中 Loop Engineering 的具体实现——自动续跑+用户定义完成条件=多次运行自主可控。 ^[inferred]

双通道检测（transcript 文件扫描+API 回退）比"agent 说 done 就停"更可靠——agent 可能说 "I'm done" 但测试还没跑。 ^[inferred]

### 模式七：AgentPromptMetadata 自描述系统

每个 agent 通过 `AgentPromptMetadata` 声明式描述自己的能力边界（category、cost、triggers、useWhen、avoidWhen）。主编排 agent 的 prompt 通过 `dynamic-agent-prompt-builder` 自动聚合所有 agent 的元数据。

**开放-封闭原则**：添加新 agent 不需要修改主编排的代码，第三方 agent 通过 `buildCustomAgentMetadata()` 自动融入。 ^[inferred]

## 与其他概念的关系

- [[concepts/multi-agent-framework-comparison|Multi-Agent框架对比]] — 框架选择层面的对比（LangGraph/CrewAI/AutoGen/AgentX），本页是设计模式层面的提炼
- [[concepts/agent-framework-engineering|Agent框架工程]] — 五大支柱（工作流/状态/记忆/工具/协议），本页关注的是多 Agent 间的编排关系
- [[concepts/harness-engineering|Harness Engineering]] — 编排约束是 Harness 的核心：工具权限矩阵=约束系统、completion_promise=反馈回路、并发控制=资源管理
- [[entities/oh-my-opencode|Oh My OpenCode]] — 本页核心洞察的实践来源
- [[concepts/agent-architecture-landscape|Agent架构全景]] — 导航枢纽

## 开放问题

- Multi-Agent 编排的**最优分层深度**：OMO 用两层（主→子），是否需要三层或更多？更深的层次意味着更多延迟和上下文传递损耗 ^[inferred]
- **成本优化 vs 延迟优化**：低成本 agent 做搜索降低 token 成本，但更多 agent 调用增加延迟。如何量化权衡？ ^[ambiguous]
- **编排 agent 的可靠性**：主编排（Sisyphus）本身可能做出错误的委派决策——如何约束编排者的行为？ ^[inferred]

## Self learn 补充（2026-09-16，credibility: low）

来源：`raw/sources/Self learn/Agent范式/`（Multi-Agent-5种协调模式等）与 `Self learn/Harness Engineering/`（AddyOsmani-Long-Running-Agents）。

### Anthropic 五种协调模式（来自 Multi-Agent 系统官方工程博客）

| 模式 | 结构 | 适用 |
|------|------|------|
| **Generator-Verifier** | 生成器产出→验证器检查→循环 | 输出可客观判定的任务（代码+测试） |
| **Orchestrator-Subagent** | 主编排拆解分派，子代理隔离执行 | 子任务独立、领域各异 |
| **Agent Teams（持久 Worker）** | 长驻团队成员通过共享文件协作 | 长周期项目（文件系统=协作面） |
| **Message Bus（Pub/Sub）** | Agent 发布/订阅事件解耦 | 松耦合、动态拓扑 |
| **Shared State（去中心化）** | 全员读写共享状态，无中心编排 | 高并发、需弹性扩缩 |

与本页七大模式的对应：OMO 的 Sisyphus 委派≈Orchestrator-Subagent；completion_promise 双通道检测≈Generator-Verifier；Anthropic Agent Teams 的"文件系统是天然协作面"呼应 Claude Code 的 worktree 隔离实践。 ^[inferred]

### Cursor 三角色与模型-角色匹配

Cursor 生产系统（ planners/ workers/ judges）：planner 持续探索代码库产出任务（可递归生成子 planner）、worker 专注执行不问大局、judge 决定迭代何时结束。两个反直觉发现：①"系统行为的惊人部分取决于怎么 prompt 这些 agent"——超过 harness 和模型本身的影响；②**不同模型适配不同角色**——GPT 模型在长时间自主工作上反而优于 Opus（Opus 倾向提前停下走捷径）。同任务不同角色配不同模型，模型匹配正在成为设计面的一部分。此外 Cursor 的三代架构演化（锁→乐观并发控制→planner/worker/judge）说明：平权 Agent + 文件锁是死路，Agent 变得风险规避互相空转。 ^[inferred]

### 长运行五模式（Saboo & Osmani）

Checkpoint-and-resume（粒度自选：不是每步、不只是结尾）/ Delegated approval（原地暂停等人工，亚秒恢复）/ Memory-layered context（警惕 **memory drift**：从少数非典型交互学到的捷径被泛化——"像治理微服务一样治理记忆"）/ Ambient processing（策略放 Gateway 层，改策略不重部署）/ Fleet orchestration（专家各持 Identity 权限，坏部署不级联）。五模式可组合。开门问题永远是："你的 Agent 最长需要不间断工作多久？"分钟级不需要长运行 Agent，小时/天级从这五模式开始。

## 参考项目示例

多 Agent 协作的开源项目索引（来源文件仅含链接，待后续深读）^[inferred]：

- **猫咖 clowder-ai** — github.com/zts212653/clowder-ai
- **tutti** — github.com/tutti-os/tutti（OS 级别的多 Agent 协作探索）^[inferred]

## 来源

- 多Agent协同：Oh My OpenCode 深度架构分析报告（raw/sources/AI 人工智能/AI Agent/Multi-Agent协同/）
- 单Agent 智能体（raw/sources/AI 人工智能/AI Agent/Multi-Agent协同/）— 仅含 2 个 GitHub 链接，内容稀疏
- 多 Agent 协作 github项目示例（同目录）— 猫咖 + tutti 两个项目链接
- Multi-Agent-5种协调模式、Multi-Agent-架构演进思考、LangGraph-圣经-multi-agent入门（raw/sources/Self learn/Agent范式/，credibility: low）
- AddyOsmani-Long-Running-Agents（raw/sources/Self learn/Harness Engineering/，credibility: low）— Cursor/Anthropic/Google 长运行案例与五模式
