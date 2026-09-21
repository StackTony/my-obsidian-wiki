---
title: Agent范式选型
category: concepts
tags: [AI, Agent, ReAct, ReWOO, Ralph Loop, 范式]
aliases: [Agent Paradigms, Agent行为范式, ReAct vs ReWOO, Ralph Loop]
summary: Agent行为范式全景与选型：ReAct(TAO循环)、Plan-Exec、ReWOO(计划前置省80% token)、Reflect(质量增强层)、Ralph Loop(无限循环+Stop Hook)、Harness(工程范式而非行为范式)——按任务结构/成本/延迟/可控性四维选型
source_dir: Self learn/Agent范式
source_files: [5大Agent范式-20张图穿透.md, ReWOO-vs-ReAct-选型指南.md, ReAct到Ralph-Loop两大范式.md, ReAct-AI-Agent设计模式.md, ReAct-Agent六层架构.md, LangGraph-ReAct-实战.md]
provenance:
  extracted: 0.70
  inferred: 0.27
  ambiguous: 0.03
base_confidence: 0.62
lifecycle: draft
lifecycle_changed: 2026-09-16
tier: supporting
created: 2026-09-16
updated: 2026-09-16
relationships:
  - target: "[[concepts/agent-framework-engineering]]"
    type: extends
  - target: "[[concepts/harness-engineering]]"
    type: related_to
  - target: "[[concepts/agent-reliability-engineering]]"
    type: related_to
  - target: "[[concepts/multi-agent-orchestration]]"
    type: related_to
  - target: "[[entities/langgraph-framework]]"
    type: uses
---

# Agent范式选型

Agent 的行为范式解决"怎么做决策、怎么执行"——从最朴素的 ReAct 循环到无限自转的 Ralph Loop，范式的演进方向是**把智能从"临场发挥"迁移到"结构化前置"**。与之正交的是 [[concepts/harness-engineering|Harness Engineering]]——它不是行为范式，而是工程架构范式（Engineering Paradigm），定义"如何用工程手段约束模型的不确定性"。

> ⚠️ 来源可信度：本页蒸馏自 `raw/sources/Self learn/Agent范式/`（AI 自主收集的网络博客，credibility: low），数值均为单源博客声明，未经交叉验证。

## 范式全景

```
行为范式（Behavioral Paradigm）—— 定义决策与执行的逻辑流
├── ReAct          思考→行动→观察 循环，边走边看
├── Plan-and-Execute  先全局规划，再逐步执行，可重新规划
├── ReWOO          计划前置+占位符，Worker执行，Solver汇总
├── Reflect        质量增强层（非独立范式），自评→修正→重试
└── Ralph Loop     无限循环 + Stop Hook 拦截 + 完成承诺

工程范式（Engineering Paradigm）—— 定义约束不确定性的架构
└── Harness        Agent = Model + Harness，环境决定下限
```

## 各范式核心机制

### ReAct：TAO 循环

Thought → Action → Observation 循环，LLM 每步根据观察决定下一步。由姚顺雨（Shunyu Yao）2022 年提出（ICLR 2023 Oral，后续上万引用），是几乎所有 Agent 框架的默认骨架。

- **优势**：灵活自适应、实现简单、模型原生工具调用（Tool Calling）即可支撑
- **局限**：每步调用 LLM，成本高速度慢；上下文随步骤线性膨胀；LLM 可能走偏
- 能上线的 ReAct Agent 远不止"模型+工具"——还需要 Tool Registry、权限层、流式输出、状态持久化、重试/超时/熔断、Trace 审计、Human-in-the-Loop 七大配套系统 ^[inferred]

### Plan-and-Execute：先谋后动

Planner 先把目标分解为完整计划，Executor 逐步执行，执行偏差可触发重新规划（Re-plan）。

- **优势**：全局视角、步骤可见可审计、执行器可用小模型降成本
- **局限**：计划质量依赖 Planner；环境突变时计划失效需重规划

### ReWOO：计划前置 + 占位符

ReWOO（Reasoning WithOut Observation）三角色：**Planner** 分解目标为带抽象占位符的任务 → **Worker** 并行执行工具填占位符 → **Solver** 汇总所有结果产出答案。推理全部前置，无需等待中间结果，部分任务可并行。

HotpotQA 基准数据（GPT-3.5）：ReWOO 准确率 42.4% vs ReAct 40.8%，token 用量约 2,000 vs 9,795——**token 节省 80%**，准确率还略升。

- **适用**：任务结构清晰、步骤可预先枚举、中间观察不需要反馈到决策（如多跳问答、批量数据收集）
- **不适用**：后续步骤依赖前序观察结果的探索型任务 ^[inferred]

### Reflect：质量增强层

Self-Refine / Reflexion 引入"从错误中学习"：生成→自评→修正的重试循环。关键认知：**Reflect 不是独立范式，而是叠加在任何范式之上的质量增强层** ^[inferred]——ReAct+Reflect、Plan-Exec+Reflect 都是合法组合。Tree of Thoughts 则把单路径反思扩展为多路径搜索式推理。

### Ralph Loop：无限循环 + 完成承诺

以《辛普森一家》角色命名的模式（ghuntley.com/loop），核心是三件套：

| 组件 | 机制 | 目的 |
|------|------|------|
| **无限循环** | 外层 for 循环反复唤醒 Agent | 强制持续工作 |
| **Stop Hook 拦截** | Hook 拦截 Agent 的退出请求，重新喂入相同 Prompt | 阻止过早退出 |
| **完成承诺** | `--completion-promise "DONE"`——Agent 输出指定短语且验证通过才停 | 定义明确的退出标准，避免无限循环 |

Agent 声称完成 ≠ 完成。Ralph Loop 把"完成"的裁判权从 Agent 手里拿走，交给外部验证。与 [[concepts/harness-engineering|Harness Engineering]] 的"约束必须机械化"和 maker/checker 分离原则一脉相承。

## 选型决策表

| 任务特征 | 推荐范式 | 理由 |
|----------|----------|------|
| 步骤依赖前序观察、探索型 | ReAct | 每步决策需要最新观察 |
| 任务可预先分解、追求低成本 | ReWOO | 计划前置省 80% token |
| 长流程需要全局视角和审计 | Plan-and-Exec | 计划可见可检查 |
| 产出质量 > 成本 | 任意 + Reflect | 自评修正循环 |
| 长时无人值守、验收标准可机器判定 | Ralph Loop | 外部强制续跑+完成验证 |
| 生产环境、可靠性第一 | 范式 + Harness | 工程约束托底下限 |

**范式不是互斥的单选题**：生产系统常见"Plan-Exec 骨架 + ReAct 叶子节点 + Reflect 关键步骤 + Ralph Loop 外壳"的混合模式。 ^[inferred]

## 与工程范式的正交关系

5大Agent范式源文的核心洞察：ReAct/Plan-Exec/Reflect/混合范式定义 Agent 的**行为逻辑**（决策流），Harness 定义**工程约束**（架构流）。正交意味着：

- 任何行为范式都跑在某种 Harness 里（哪怕是裸 API 调用也算极简 Harness）^[inferred]
- 行为范式选型决定"智能上限"，Harness 质量决定"可靠性下限" ^[inferred]
- LangGraph 把 ReAct 建模为图（推理节点/工具节点/观察节点/终止节点），是行为范式向工程范式收敛的典型——"从 Prompt 驱动走向 Graph 驱动"

## 未解问题

- ReWOO 的 42.4% vs 40.8% 提升在统计上是否显著？单源基准数据，样本细节不明 ^[ambiguous]
- 混合范式的复杂度边界：组合多少层范式后边际收益归零？无系统研究 ^[inferred]
- Ralph Loop 的成本失控风险：无限循环 + 强模型 + 无预算上限 = 一个下午烧掉一周 API 预算（Addy Osmani 警告）

## 来源

- 5大Agent范式-20张图穿透、ReWOO-vs-ReAct-选型指南、ReAct到Ralph-Loop两大范式、ReAct-AI-Agent设计模式、ReAct-Agent六层架构、LangGraph-ReAct-实战（raw/sources/Self learn/Agent范式/，credibility: low）
- 工程约束侧详见 [[concepts/harness-engineering]]；可靠性侧详见 [[concepts/agent-reliability-engineering]]；多Agent协作详见 [[concepts/multi-agent-orchestration]]
