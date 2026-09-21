---
title: Loop Engineering（循环工程）
category: concepts
tags: [AI, Agent, Loop, 自动化, 范式演进]
aliases: [循环工程, Loop Engineering, loopcraft]
summary: Loop Engineering用系统替代人肉提示Agent：六原语(Automations/Worktrees/Skills/Connectors/Sub-agents/State)+四层循环栈(Agent/验证/事件驱动/爬山)+四次范式跃迁(Prompt→Context→Harness→Loop)+企业级治理(预算/审批/追踪)
source_dir: Self learn/Loop Engineering
source_files: [AddyOsmani-Loop-Engineering.md, Prompt正在过时，Loop才是新范式.md, LangChain-Art-Of-Loop-Engineering.md, TrueFoundry-Loop-Engineering-Enterprise.md]
provenance:
  extracted: 0.70
  inferred: 0.28
  ambiguous: 0.02
base_confidence: 0.64
lifecycle: draft
lifecycle_changed: 2026-09-16
tier: supporting
created: 2026-09-16
updated: 2026-09-16
relationships:
  - target: "[[concepts/harness-engineering]]"
    type: extends
  - target: "[[concepts/agent-paradigm-selection]]"
    type: related_to
  - target: "[[concepts/multi-agent-orchestration]]"
    type: related_to
  - target: "[[concepts/agent-reliability-engineering]]"
    type: uses
---

# Loop Engineering（循环工程）

**Loop Engineering 是把"你自己提示 Agent"这件事自动化——你设计那个替你提示、替你验收、替你派活的系统。** Peter Steinberger："别再给编程 Agent 写提示词了，去设计循环，让循环替你提示 Agent。" Boris Cherny（Claude Code 负责人）："我已经不给 Claude 写提示词了……我的工作，就是写循环。" 黄仁勋："现在根本没有人写 Prompt 了，新时代的核心工作是编写和管理 loop。"

> ⚠️ 来源可信度：蒸馏自 `raw/sources/Self learn/Loop Engineering/`（credibility: low）。该概念 2026 年 6 月由 Addy Osmani 命名，尚在快速演化中。

## 四次范式跃迁

人类对 AI 的**控制粒度不断上移**：

| 阶段 | 时期 | 核心问题 | 人的角色 |
|------|------|----------|----------|
| Prompt Engineering | 2023-2024 | 该怎么问？ | 写指令的人 |
| Context Engineering | 2024-2025 | 给模型看什么？ | 搭信息环境的人 |
| Harness Engineering | 2025-2026 | 环境怎么运作？ | 设计运行系统的人 |
| **Loop Engineering** | 2026- | 系统怎么持续自转？ | 设计循环的人 |

Loop 坐在 Harness 上一层楼：Harness 让单个 Agent 在一次任务中干好活，Loop 决定**哪些任务、何时跑、什么算完成**。 ^[inferred]

## Loop 与 Agent 的区别

- **Agent 是干活的人**——没有 Loop 的 Agent，你提一句它动一下，本质是听话的工具
- **Loop 是管理制度**——套上 Loop 的 Agent 才成为能自转的系统

学术源头可追溯到 ReAct（姚顺雨 2022）：思考→行动→观察的循环结构就是最早的 agent loop 雏形，后续 Reflexion（从错误学习）、Tree of Thoughts（多路径搜索）逐步收敛为工程界的 Loop 系统。

## 六原语（Osmani 解剖学，Codex 与 Claude Code 双栈对照）

| 原语 | 职责 | Codex | Claude Code |
|------|------|-------|-------------|
| **Automations** | 定时发现+分诊，Loop 的心跳 | Automations 面板 + Triage inbox | `/loop`、`/schedule`、cron、hooks、GitHub Actions |
| **Worktrees** | 隔离并行 Agent 防文件冲突 | 每线程内置 worktree | `git worktree`、`--worktree`、子代理 `isolation: worktree` |
| **Skills** | 固化项目知识，停止每轮重新解释 | Agent Skills (`$name`) | Agent Skills (`SKILL.md`) |
| **Plugins/Connectors** | 接入真实工具生态 | Connectors (MCP) + plugins | MCP servers + plugins |
| **Sub-agents** | maker/checker 分离——写的和查的必须是两个 | TOML 定义于 `.codex/agents/` | `.claude/agents/` + agent teams |
| **State** | 记住做到哪了（外部状态文件） | Markdown / Linear | `AGENTS.md`、进度文件 / Linear via MCP |

**第六件最重要也最"笨"**：一份 Markdown 或 Linear 看板，活在对话之外。模型每次运行都是失忆的，记忆必须在磁盘上、不在上下文里——"Agent 会忘，仓库不会忘。"

`/goal` 的精妙设计：跑到验收条件满足为止，且每轮由**另一个独立小模型**（如 Haiku）判断是否完成——写代码的不判自己的卷子，maker/checker 分离应用到停止条件本身。

## 四层循环栈（LangChain loopcraft）

| 层 | 循环 | 作用 | 代表原语 |
|----|------|------|----------|
| 1 | **Agent 循环** | 模型调工具直到任务完成 | `create_agent` |
| 2 | **验证循环** | 输出对照 rubric 评分，不达标带反馈重试 | `RubricMiddleware` |
| 3 | **事件驱动循环** | 事件/定时触发 Agent 更新真实系统 | cron / webhooks / Fleet channels |
| 4 | **爬山循环** | 分析 Agent 自己的 trace，改写 harness 配置 | LangSmith Engine |

第 4 层是范式跃迁点：回环不只回到顶层，而是**伸进内层直接改写 Agent 循环本身**——每次外圈让所有内圈更有效。这就是"自改进 Agent"：trace 是高价值信号源，分析它→改 prompt/工具/评分器→部署。对开源权重模型还可进一步接入 RL 微调。

## 何时值得建 Loop（4 条件测试）

全部满足才值得，否则瞎建只会亏钱：

1. **任务重复发生**——Loop 把设计成本摊销到多次运行；一次性任务一个好 prompt 更快
2. **验收可自动化**——"所有测试通过且 lint 干净"是真停止条件，"看起来不错"不是
3. **Token 预算扛得住浪费**——无人值守的 Loop 也在无人值守地花钱（Noor 周末事件：Loop 对着坏测试环境狂重试两天，周一账单爆炸）
4. **Agent 已有"高级工程师"的工具**——巧妇难为无米之炊

**失败率堆叠警告**：五步链每步 95% 可靠 → 整链约 77% 干净完成；且无人值守的错误会**复合进状态**，明天的运行建立在今天的错误之上。这是 maker/checker 分离是承重墙而非装饰品的原因。

## 实操路线（Codez 14 步法精要）

1. **最小可行 Loop 四件套**：触发器（Automation）+ 技能（Skill）+ 状态文件（STATE.md）+ 门禁（测试/类型检查/构建）
2. **顺序不能跳**：先手动跑通一次 → 写成 Skill → 包进 loop → 最后才上定时。跳步是 Loop 死在生产环境的主要原因
3. **拆卷子别判卷子**：写代码的和验代码的必须分开，验收方不能看到写代码方的推理过程
4. **硬停止条件**：Token 上限、迭代次数上限、时间限制——没有硬停止的 Loop 跑到你看见账单才停
5. **Loop 不碰需要判断的活**：架构重写、鉴权、支付逻辑、产品决策不进 Loop；Lint 自动修复、依赖更新 PR、CI 失败分类、Flaky 测试复现才进
6. **唯一有用的指标**：每个被接受的改动平均成本多少——被接受率 <50% 说明你在做 Loop 本该替你省掉的评审工作

## 企业级治理（TrueFoundry 补充）

个人笔记本 Loop 的四大企业缺口：**生命周期**（合盖即死）、**凭证**（个人 token 跑定时任务=审计灾难）、**成本**（无预算无熔断）、**清单**（五人五份野副本无人盘点）。治理方案：Skills 进版本化注册表、Connectors 走 MCP Gateway（中心化凭证+RBAC）、子代理有自己的身份和范围、审批门禁可暂停数天等人工、每步 trace 全记录。"loop 是穿着工作流外衣的运行时问题。"

## 人的角色：不删除你，而是改变你

三件事 Loop 越好反而越尖锐：

- **验证仍是你的**——checker 让"done"有意义，但 done 是 claim 不是 proof
- **理解力债务**——Loop 合入越快，你读的越少，与"没人读过的系统"的距离越大
- **认知投降**——同一套 Loop，理解工作的人用它加速，逃避理解的人用它加速堕落。Loop 分不出这两者，你分得出

卡帕西："你可以外包你的思考，但你没法外包你的理解。"

## 未解问题

- Loop Engineering 概念本身 <1 个月历史（2026-06 命名），实践词汇和标准还在激烈变动 ^[ambiguous]
- `/goal` 判卷小模型的可靠性：小模型误判"已完成"的比率无公开数据 ^[inferred]
- 组织级 Loop 协作：多个 Loop 互相触发时的死锁/风暴问题未讨论 ^[inferred]

## 来源

- AddyOsmani-Loop-Engineering（命名原文，六原语解剖）
- Prompt正在过时，Loop才是新范式（中文圈综述：黄仁勋/Steinberger/Cherny/吴恩达观点+Codez 14步+四次范式跃迁）
- LangChain-Art-Of-Loop-Engineering（四层循环栈+loopcraft）
- TrueFoundry-Loop-Engineering-Enterprise（企业治理视角，Noor 案例）
- 以上均位于 raw/sources/Self learn/Loop Engineering/（credibility: low）
- 下层建筑详见 [[concepts/harness-engineering]]；范式背景详见 [[concepts/agent-paradigm-selection]]
