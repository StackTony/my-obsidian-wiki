---
title: Harness Engineering（驾驭工程）
category: concepts
tags: [AI, Agent架构, Harness, 约束系统, 工程范式]
aliases: [驾驭工程, Harness]
source_dir: AI 人工智能/Agent架构/Harness工程
source_files: [Harness Engineering：AI Agent 时代的工程范式革命.md, Harness-从零理解到动手代码实践.md, Harness-起源原理与落地实践.md, Harness-驾驭工程介绍.md]
provenance:
  extracted: 0.65
  inferred: 0.30
  ambiguous: 0.05
base_confidence: 0.82
lifecycle: draft
lifecycle_changed: 2026-06-16
tier: core
created: 2026-06-16
updated: 2026-06-27
summary: Harness Engineering是围绕AI Agent构建约束、反馈回路与执行控制的工程方法——模型负责推理，Harness负责一切外围工程：工具系统、上下文管理、权限控制、反馈回路、状态持久化
relationships:
  - target: "[[concepts/agent-framework-engineering]]"
    type: extends
  - target: "[[concepts/llm-observability]]"
    type: uses
  - target: "[[entities/claude-code]]"
    type: uses
  - target: "[[entities/oh-my-opencode]]"
    type: related_to
---

# Harness Engineering（驾驭工程）

Harness Engineering 的核心主张只有一句话：**Agent = Model + Harness**。模型负责推理，Harness 负责一切外围工程——工具系统、上下文管理、权限控制、反馈回路、状态持久化。过去以为瓶颈在模型不够聪明，现在发现瓶颈在外围工程。

这个概念由 HashiCorp 联合创始人 Mitchell Hashimoto 在 2026 年 2 月 5 日首次命名："每当发现 Agent 犯了一个错误，就花时间工程化一个解决方案，让它永远不再犯同样的错误。"六天后 OpenAI 在百万行代码实验报告中正式采用，随后 Martin Fowler 撰文深度分析，一个月内成为开发者社区高频词。

参见 [[concepts/agent-framework-engineering|Agent框架工程]] 和 [[concepts/agent-architecture-landscape|Agent架构全景]] 的上下文。

## 核心观点

- **瓶颈在基础设施，不在模型智能**：Can.ac 改 Harness 就让分数从 6.7% 跳到 68.3%；LangChain 改 Harness 从 Terminal Bench 第 30 名飙到第 5 名——底层模型一个参数都没动
- **上下文利用率控制在 40% 以下**：Dex Horthy 量化数据，168K token 窗口前 40% 是 Smart Zone（推理聚焦且准确），超过阈值进入 Dumb Zone（幻觉、死循环、格式错误齐上阵）
- **约束必须机械化**："不能机械执行的规则，Agent 一定会偏离"——软约束（写在Prompt里）不够，必须硬约束（编码为Linter、CI、类型系统）
- **思考与执行必须分离**：所有团队独立发现"先规划再执行"模式——初始化 Agent 先生成计划，后续 Agent 每次只处理一个子任务

## 三次范式跃迁

| 阶段 | 核心问题 | 优化对象 | 工程师角色 |
|------|----------|----------|-----------|
| Prompt Engineering | 该怎么问？ | 输入措辞 | 写指令的人 |
| Context Engineering | 该让模型看到什么？ | 信息输入 | 搭信息环境的人 |
| Harness Engineering | 整个环境该怎么运作？ | 运行控制系统 | 设计运行气候的人 |

类比：Prompt 是**对马喊话的技巧**，Context 是**给马看的地图**，Harness 是**给马造一条高速公路，配上护栏、限速牌和加油站**。

## Agent常见失败模式

Anthropic 工程师总结三种典型翻车：

1. **试图一步到位（One-shotting）**：一个会话里把所有功能做完 → 上下文窗口耗尽 → 留下无文档半成品
2. **过早宣布胜利**：部分功能完成就宣布任务完成，即使大量功能未实现
3. **过早标记功能完成**：写完代码就标完成，没做端到端验证

更隐蔽的：**模式复制**——代码库中坏模式占比>5%时，Agent 生成新代码采用该模式的概率>70%。AI 扩散坏模式的速度是指数级的。

## 四大支柱

综合 OpenAI、Anthropic、LangChain、Martin Fowler 的实践，四根"护栏"：

### 支柱一：上下文工程——新员工手册

**AGENTS.md** 是 Agent 进入代码仓库时看到的第一份指南。关键原则：**全量灌输不如渐进披露**。

- Mitchell Hashimoto 的 Ghostty 项目 AGENTS.md 只有几百行，每一行对应一个历史 Agent 失败案例
- OpenAI 从单个巨大 AGENTS.md 迁移到分层架构，构建小型入口文件指向深层事实源
- 后台 Agent 定期扫描过期文档并提交清理 PR——**Agent 为 Agent 维护文档**

### 支柱二：架构约束——缰绳

**软约束不够，关键流程必须有硬约束。**

- OpenAI 团队建立层级依赖模型：Types → Config → Repo → Service → Runtime → UI，下层不能反向依赖上层
- 规则编码为自定义 Linter，CI 中强制阻断——人写的还是 AI 写的，违规就合不进去
- Linter 错误信息不只是"违反规则 X"，还解释为什么存在、正确做法是什么——Agent 读到后能自动修正

### 支柱三：反馈循环——智能体审智能体

**生成和评估必须分开**——Agent 自己评自己容易"放水"。

- "沉默即成功"协议：测试通过→零输出（<10 token）；失败→结构化错误信息
- HumanLayer 实验：采用此协议后，10步内完成任务比例从 43% → 78%，平均节省 35% 上下文 token
- 执行与评审拆开：一个 Agent 负责执行，另一个负责审查

### 支柱四：熵管理——垃圾回收

AI 复制坏模式的速度是指数级的。**集中清理模式已失效**——OpenAI 从"每周五清理技术债"改为每天下午4-5点的 **"垃圾回收日"**：

1. 每天一小时不再开发新功能
2. 审视当天 Agent 生成的所有代码和 PR
3. 立即将坏模式"编译"成 Linter 规则或 AGENTS.md 条目

技术债像高息贷款——持续小额偿远比集中清账更可持续。

## Harness vs Workflow

区别在于**主导权**：

| 维度 | Workflow | Harness |
|------|----------|---------|
| 执行路径 | 固定线性 | 动态，Agent自主规划 |
| 模型角色 | 执行者 | 主导者（受约束） |
| 异常处理 | 预设之外会断裂 | 可动态调整 |
| 适用场景 | 确定性高的简单流程 | 复杂、不确定的长周期任务 |

模型越来越强的当下，Harness 更能发挥模型能力，同时确保不过失。

## 实战案例

### OpenAI：零手写的百万行代码

3名工程师5个月产出100万行代码，手写0行，合并~1,500 PR。核心原则：设计环境而非编写代码、依赖方向用Linter机械化enforce、所有知识放代码仓库当唯一事实源、对抗熵。

### Anthropic：16 Agent 造 C 编译器

2周、16并行 Opus 4.6 实例、~2,000次 Claude Code 会话、10万行 Rust 代码。GCC torture test 通过率 99%。关键设计：日志写文件不占上下文、确定性测试子采样、四类专业化分工。

### LangChain：Terminal Bench 第30→5名

固定模型为 gpt-5.2-codex，只改 Harness。三项核心优化：
1. 系统提示词+中间件强制"构建-验证"循环
2. LocalContextMiddleware 直接注入环境信息
3. 推理三明治策略：规划(xhigh)→实现(high)→验证(xhigh)

### Can Boluk：Hashline协议

给每行代码加内容哈希标签，模型引用标签而非精确匹配原文。Grok Code Fast 1 从 6.7% → 68.3%，Grok 4 Fast 输出token降61%。**训练成本为零**。

### Oh My OpenCode：Multi-Agent编排的Harness实现

[[entities/oh-my-opencode|Oh My OpenCode]]（OMO）是 Harness Engineering 的杰出实践案例——它不是框架而是插件，但把 Harness 四大支柱全部落地：

| Harness 支柱 | OMO 实现 | 说明 |
|--------------|----------|------|
| **上下文工程** | Context Injector（4级优先级）+ `synthetic: true` 隐藏注入 | agent 可见、用户不可见的上下文管理 |
| **架构约束** | 工具权限矩阵 + Prometheus `md-only` hook + Hephaestus FORBIDDEN 指令 | 机械化约束——顾问不能动手、规划不能写代码、执行不能询问 |
| **反馈循环** | Ralph Loop completion_promise + 双通道完成检测 + 证据驱动完成标准 | 用户定义"完成"，工具验证证据，自动化反馈闭环 |
| **熵管理** | preemptive-compaction + Hashline Edit 防幻觉 + settled-flag 防竞态 | 防止上下文腐烂、防止基于过时内容编辑、防止并发竞态 |

特别值得注意的是 Ralph Loop——这正是 [[concepts/multi-agent-orchestration|Loop Engineering]] 的具体实现：agent 停了自动踢一脚继续干，completion_promise 让多次运行自主可控。 ^[inferred]

## 六大行业共识

| # | 共识 | 核心观点 |
|---|------|----------|
| 1 | 瓶颈在基础设施 | 五个独立团队得出相同结论 |
| 2 | 文档必须是活的反馈循环 | 静态文档是坟场，后台Agent定期清理 |
| 3 | 思考与执行分离 | 所有团队独立发现此模式 |
| 4 | 上下文不是越多越好 | 40%甜区有量化数据支撑 |
| 5 | 约束必须自动化 | 不能机械执行的规则Agent必偏离 |
| 6 | 工程师角色在变 | 从写代码转向设计环境和管理 |

## 三阶段落地路线图

| 阶段 | 核心目标 | 主要手段 | 验证标准 |
|------|----------|----------|----------|
| Phase 1 信息层 | 解决信息混乱 | 文档拆解、建立索引 | Agent能根据索引找到正确文档 |
| Phase 2 约束层 | 强制执行关键规则 | Linter规则、CI集成、Hook | 违规代码被CI阻断 |
| Phase 3 自动化层 | 自动化管理和持续优化 | 多Agent协作、清理Agent | 系统自动扫描债务并加固 |

## 未解问题

- **棕地改造**：所有成功案例都是绿地项目，十年遗留代码库怎么引入Harness？零方法论
- **行为验证**：擅长约束Agent不做错事，但验证Agent做对了事远未解决
- **长期可维护性**：防止"功能没问题但维护性很差"的代码渗进代码库，没人回答

## 来源

- Harness Engineering：AI Agent 时代的工程范式革命（raw/sources/AI 人工智能/Agent架构/Harness工程/）
- Harness-从零理解到动手代码实践（raw/sources/AI 人工智能/Agent架构/Harness工程/）
- Harness-起源原理与落地实践（raw/sources/AI 人工智能/Agent架构/Harness工程/）
- Harness-驾驭工程介绍（raw/sources/AI 人工智能/Agent架构/Harness工程/）
