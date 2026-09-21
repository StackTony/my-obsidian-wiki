---
title: Agent可靠性工程
category: concepts
tags: [AI, Agent, 可靠性, 幂等性, 重试, 工具调用]
aliases: [Agent Reliability, Agent幂等性, 重试浪费, Agent可靠性]
summary: Agent可靠性工程：幂等键由编排器派生(agent_run_id, step_id, tool_name, business_scope)、重试90.8%浪费于幻觉工具名(需错误分类+熔断+确定性路由)、高级工具调用三技术(Tool Search/Programmatic Calling/Examples)与HITL动态中断
source_dir: Self learn/Agent范式
source_files: [Agent幂等性-编排契约.md, ReAct-Agent-90-重试浪费.md, Agent高级工具调用-并行嵌套错误处理.md, LangGraph-Human-in-the-loop实战.md, AI-Agent开发踩坑实录.md]
provenance:
  extracted: 0.72
  inferred: 0.25
  ambiguous: 0.03
base_confidence: 0.62
lifecycle: draft
lifecycle_changed: 2026-09-16
tier: supporting
created: 2026-09-16
updated: 2026-09-16
relationships:
  - target: "[[concepts/agent-paradigm-selection]]"
    type: related_to
  - target: "[[concepts/harness-engineering]]"
    type: extends
  - target: "[[entities/langgraph-framework]]"
    type: uses
  - target: "[[concepts/tool-calling-mcp]]"
    type: extends
---

# Agent可靠性工程

Agent 范式解决"怎么决策"，可靠性工程解决"决策错了怎么办"。三个失败重灾区：**重复执行副作用**（幂等性）、**重试预算浪费**（幻觉工具名）、**工具调用质量**（上下文膨胀+参数幻觉）。这是 [[concepts/harness-engineering|Harness Engineering]] "约束必须机械化"原则在执行层的具体化。

> ⚠️ 来源可信度：蒸馏自 `raw/sources/Self learn/Agent范式/`（credibility: low），数值为单源博客基准数据。

## 幂等性：编排器的契约

Agent 会重试、重新规划、子智能体会重叠执行——同一业务动作可能被触发多次。幂等性设计回答"工具被调用第二次时世界会怎样"。

### 幂等键必须由编排器派生

有效结构：`(agent_run_id, step_id, tool_name, business_scope)`

| 字段 | 作用 |
|------|------|
| `agent_run_id` | 锚定到特定用户请求，防止跨运行的重复 |
| `step_id` | **逻辑步骤**而非工具调用计数——"向客户收费"的两次重新规划折叠为同一 step_id |
| `tool_name` | 同一运行中 refund_card 不与 charge_card 冲突 |
| `business_scope` | 客户ID/订单ID等业务对象——防止稍后运行为不同目的调用同工具 |

**反面教材**：从模型参数哈希派生幂等键——温度、采样随机性导致同一逻辑请求产生不同键，幂等完全失效。

### 重复检测命中后的三种策略

| 策略 | 行为 | 适用 |
|------|------|------|
| **Merge** | 复用已有结果，跳过执行 | 结果确定性可复用 |
| **Refuse** | 返回结构化"已执行过"错误，规划器自行恢复 | 副作用不可逆（扣款、发邮件） |
| **Bypass** | 人工操作员明确请求重执行，生成新键接受重复 | 人工兜底通道 |

### 子智能体的关联 ID 问题

规划器分发任务给多个子智能体时，若各自维护工具 ID 空间，两个重叠职责的子智能体可能为同一业务目的调用同一工具。解法：`agent_run_id` 加入幂等键 + 传播机制让每个子智能体继承。这正是微服务十年前的 correlation ID 机制在智能体时代的重生。

## 重试浪费：90.8% 的教训

200 任务基准中 **90.8% 的重试被浪费**——不是因为模型判断错误，而是系统在重试**根本不存在的工具**。

### 根因链

```
LLM 幻觉工具名（web_browser / sql_query / python_repl）
  → TOOLS.get(tool_name) 返回 None
    → 全局重试计数器无错误分类
      → TOOL_NOT_FOUND 被当作 TRANSIENT 网络抖动同等对待
        → 烧尽重试预算 → 任务静默失败
```

关键认知：**幻觉工具名是永久性错误，任何重试都不可能成功**——重试无法让字典里凭空出现一个键。Prompt 工程修不了这个问题。

### 三层修复

1. **错误分类法**：retryable（网络超时）vs non-retryable（TOOL_NOT_FOUND、权限拒绝）——非重试错误直接短路
2. **每工具熔断**：单工具连续失败 N 次后熔断，防止一个坏工具拖垮整个预算
3. **确定性路由**：LLM 只输出 step type，经 `plan_workflow` → `STEP_TO_TOOL` 字典查找——查找结果永远合法，幻觉在结构上不可能发生

对照组（受控工作流）在同一基准下 **0 次浪费重试**。这就是"约束必须机械化"的量化证明。

## 高级工具调用：Anthropic 三技术

| 技术 | 机制 | 数据 |
|------|------|------|
| **Tool Search Tool** | 工具按需加载（defer_loading），Agent 先搜后载 | 上下文 ~77K → 8.7K tokens，**降 85%** |
| **Programmatic Tool Calling** | 工具调用写入 Python 代码块，解释器编排 | 复杂研究任务 token **降 37%** |
| **Tool Use Examples** | 提示中给参数构造示例 | 复杂参数处理准确率 72% → **90%** |

（另见 [[concepts/tool-calling-mcp|工具调用与MCP]] 的基础层。）

三技术共同点：把"工具组织方式"从静态全量注入改为动态按需装配——与 Harness Engineering 的渐进披露（progressive disclosure）同一哲学。 ^[inferred]

## Human-in-the-Loop：动态中断

LangGraph 的两代中断机制：

- **静态中断**：`interrupt_before` / `interrupt_after` 在图定义时固定暂停点
- **动态中断**：节点内任意位置调用 `interrupt(payload)` → 图暂停、checkpointer 持久化状态 → 人工决策后 `Command(resume=value)` 恢复

动态中断的前提是**可持久化的 checkpointer**（生产用 PostgresSaver 而非内存版）——中断可能持续数天，状态必须活过进程重启。这正是"delegated approval"模式：Agent 原地暂停保留完整执行状态（推理链、工作记忆、工具历史、待执行动作），人工耗时数小时期间零计算消耗，恢复延迟亚秒级。

## 生产落地经验（病历质控 Agent 案例）

一个真实企业 Agent 的三阶段技术选型演进：

| 阶段 | 目标 | 技术栈 | 理由 |
|------|------|--------|------|
| 预研 | 验证可行性 | LangChain | 快速试错 |
| 打单/MVP | 快速演示 | Spring AI (Java) | 框架封装好、开发快 |
| 生产 | 稳定可控 | WebClient + Jackson | 少一层抽象，超时/重试/日志/Schema校验/错误码映射每层可见可控 |

配套决策：pgvector 而非 Qdrant——已有 PostgreSQL 加插件零新增基础设施，Qdrant 留作规模化后的迁移选项。

**模式迁移到工程域**：这组案例的共同启示是 Agent 可靠性不是模型问题而是系统工程问题——幂等键设计、错误分类、熔断策略、中断恢复，每一项都是分布式系统的老问题在新上下文的再现。 ^[inferred]

## 未解问题

- 90.8% 数字来自单篇博客的合成基准（`HALLUCINATION_RETRY_BURN=3` 常数直接驱动该值），真实生产系统分布未知 ^[ambiguous]
- 幂等键的 step_id 粒度如何自动判定？目前依赖规划器显式声明，模型自发生成 step_id 的可靠性未验证 ^[inferred]
- Bypass 策略的审计责任：人工重执行的副作用归责模型还是操作员？合规场景未覆盖

## 来源

- Agent幂等性-编排契约、ReAct-Agent-90-重试浪费、Agent高级工具调用-并行嵌套错误处理、LangGraph-Human-in-the-loop实战、AI-Agent开发踩坑实录（raw/sources/Self learn/Agent范式/，credibility: low）
- Agent生产落地-血泪经验（同目录，多文章合集：病历质控 Agent 选型部分）
- 范式侧详见 [[concepts/agent-paradigm-selection]]；记忆侧详见 [[entities/langgraph-framework]] 的 Memory 架构
