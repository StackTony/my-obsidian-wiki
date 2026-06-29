---
title: Oh My OpenCode
category: entities
tags: [AI, Agent, Multi-Agent, OpenCode, 编排]
aliases: [OMO, Oh My OpenCode]
source_dir: AI 人工智能/AI Agent/Multi-Agent协同
source_files: [多Agent协同：Oh My OpenCode 深度架构分析报告.md]
provenance:
  extracted: 0.65
  inferred: 0.30
  ambiguous: 0.05
base_confidence: 0.55
lifecycle: draft
lifecycle_changed: 2026-06-27
tier: supporting
created: 2026-06-27
updated: 2026-06-27
summary: Oh My OpenCode（OMO）是OpenCode的超级插件——把单agent工具变成多agent编排平台，以希腊神话命名11个角色agent+Ralph Loop自动续跑+Hashline Edit防幻觉+三级并发控制+Claude Code兼容层
relationships:
  - target: "[[concepts/multi-agent-framework-comparison]]"
    type: implements
  - target: "[[concepts/harness-engineering]]"
    type: implements
  - target: "[[entities/claude-code]]"
    type: related_to
  - target: "[[concepts/agent-framework-engineering]]"
    type: extends
  - target: "[[concepts/agent-architecture-landscape]]"
    type: related_to
---

# Oh My OpenCode

Oh My OpenCode（OMO）是 [OpenCode](https://github.com/opencode-ai/opencode) 的超级插件，定位是 AI 编程工具的 "oh-my-zsh"——不改变宿主核心，但通过插件机制注入一整套 agent 体系、工具链、自动化循环和智能降级策略，让 OpenCode 从单 agent 工具变成多 agent 编排平台。

分析版本 v3.7.4，代码规模 910 个源文件（68k 行实现 + 67k 行测试），256 个测试文件，技术栈 TypeScript + Bun + Zod + MCP SDK。

核心卖点：
- 多 agent 编排（Sisyphus 指挥、Oracle 顾问、Librarian 查资料、Explore 搜代码……）
- 后台并行 agent（OpenCode session API + tmux 可视化）
- LSP/AST-grep 工具（给 AI 真正的代码理解能力）
- Ralph Loop（自动续跑机制，agent 停了自动踢一脚继续干）
- Claude Code 兼容层（加载 Claude Code 的 agent、skill、MCP 配置）
- 多 provider 智能降级（Claude/OpenAI/Gemini/Copilot 自动切换）

参见 [[concepts/multi-agent-framework-comparison|Multi-Agent框架对比]] 和 [[concepts/harness-engineering|Harness Engineering]] 的概念上下文。

## 四大支柱架构

OMO 的架构由 `src/index.ts` 依次创建四个核心组件：

| 支柱 | 入口 | 职责 |
|------|------|------|
| **Managers** | `create-managers.ts` | 后台 agent 并发、tmux 窗格、skill MCP 服务、配置处理 |
| **Tools** | `create-tools.ts` | 注册所有工具（LSP、AST-grep、background task、session manager 等） |
| **Hooks** | `create-hooks.ts` | 事件钩子（Ralph Loop、上下文监控、预压缩、通知等） |
| **PluginInterface** | `plugin-interface.ts` | 将以上三者组装成 OpenCode 期望的插件接口 |

分层清晰——每一层只依赖上一层的输出，职责边界明确。

## ConfigHandler 6 步处理管线

`createConfigHandler()` 按固定顺序调用 6 个子处理器：

1. `applyProviderConfig` → 提取模型上下文限制
2. `loadPluginComponents` → 加载第三方插件（10秒超时保护）
3. `applyAgentConfig` → 最复杂（226行）：迁移旧版名称→发现 skill→创建 builtin agents→合并→排序
4. `applyToolConfig` → 禁用冲突工具，设置精细权限矩阵
5. `applyMcpConfig` → 合并 builtin→用户→Claude Code→插件 MCPs
6. `applyCommandConfig` → 14 级优先级命令合并

顺序有严格依赖关系——`applyAgentConfig` 的返回值被传给 `applyToolConfig`。

## 希腊神话 Agent 体系

OMO 设计了一套以希腊神话命名的 agent 体系，每个 agent 有明确的职责、工具权限和模型匹配策略。核心设计理念：**不同的认知任务需要不同的模型能力和工具权限**。

### 角色拓扑

| Agent | 默认模型 | 温度 | 模式 | 核心职责 |
|-------|----------|------|------|----------|
| **Sisyphus** | claude-opus-4-6 | 0.1 | primary | 主编排器，意图分类、委派任务、验证结果 |
| **Hephaestus** | gpt-5.3-codex | 0.1 | primary | 自主深度执行器，端到端完成复杂任务 |
| **Prometheus** | claude-opus-4-6 | 0.1 | — | 战略规划师，只做计划不写代码 |
| **Atlas** | claude-sonnet-4-6 | 0.1 | primary | Todo 列表编排器，按波次并行调度 |
| **Oracle** | gpt-5.2 | 0.1 | subagent | 只读高智商顾问，架构决策和疑难调试 |
| **Metis** | claude-opus-4-6 | **0.3** | subagent | 规划前顾问，做 gap 分析 |
| **Momus** | gpt-5.2 | 0.1 | subagent | 计划审查员，验证可执行性 |
| **Librarian** | glm-4.7 | 0.1 | subagent | 外部文档/代码搜索 |
| **Explore** | grok-code-fast-1 | 0.1 | subagent | 内部代码库搜索 |
| **Multimodal Looker** | gemini-3-flash | 0.1 | subagent | 多模态文件分析 |
| **Sisyphus-Junior** | claude-sonnet-4-6 | 0.1 | all | 分类任务执行器，不能再委派 task() |

协作拓扑：

```
用户请求
    ├─→ Sisyphus (日常编排) ──→ Explore/Librarian (后台搜索)
    │       │                  ──→ Oracle (高难度咨询)
    │       │                  ──→ task(category=X) → Sisyphus-Junior (执行)
    ├─→ Hephaestus (深度自主) ──→ 同上，但更自主
    ├─→ Prometheus (规划模式) ──→ Metis (前置分析) → Momus (计划审查)
    └─→ Atlas (计划执行) ──→ task(category=X) → Sisyphus-Junior (按波次)
```

命名哲学：Sisyphus 永不放弃推石头（持续执行）、Oracle 是神谕（只给建议不动手）、Prometheus 是先知（规划未来）——用户不需读文档就能直觉理解角色。 ^[inferred]

### AgentPromptMetadata 自描述系统

每个 agent 通过 `AgentPromptMetadata` 声明式描述能力边界：

```typescript
export interface AgentPromptMetadata {
  category: AgentCategory        // "exploration" | "specialist" | "advisor" | "utility"
  cost: AgentCost                // "FREE" | "CHEAP" | "EXPENSIVE"
  triggers: DelegationTrigger[]  // 什么场景下应该委派
  useWhen?: string[]             // 详细使用场景
  avoidWhen?: string[]           // 不应使用的场景
  keyTrigger?: string            // Phase 0 快速触发条件
  dedicatedSection?: string      // 专属 prompt 段落
}
```

**核心价值：添加或移除一个 agent 时，Sisyphus 的 prompt 自动更新。** 每个 agent 自描述能力，`dynamic-agent-prompt-builder.ts` 自动聚合生成委派表和工具选择表，实现了真正的开放-封闭原则。第三方插件注册的 agent 通过 `buildCustomAgentMetadata()` 自动融入。

### Sisyphus vs Hephaestus 双轨哲学

**Sisyphus（编排者）** 约 500 行 prompt，核心设计：
1. **分阶段决策流水线**：Phase 0 (Intent Gate) → Phase 1 → Phase 2A/2B/2C → Phase 3 (Completion)
2. **委派优先**：先检查有没有合适的 agent，再检查 category+skill 组合，最后才考虑自己做
3. **并行是默认行为**：Explore 和 Librarian 必须用 `run_in_background=true` 并行发射 2-5 个
4. **Oracle 的特殊地位**：唯一"永远不能取消"的 agent——**高质量推理的价值在你认为不需要它的时候最高** ^[inferred]
5. **证据驱动的完成标准**：File edit → lsp_diagnostics clean；Build → exit code 0；Test → pass；NO EVIDENCE = NOT COMPLETE

**Hephaestus（自主执行者）** 与 Sisyphus 共享基础设施，但行为指令根本不同：
- **禁止询问，只管做**："Should I proceed?" → JUST DO IT；"Do you want me to run tests?" → RUN THEM
- **Intent Extraction 机制**：表面"Did you do X?" = 真实意图"你忘了 X，现在做"
- **`<turn_end_self_check>` 自我约束**：每个 turn 结束前做四项检查，任何失败都不能结束

设计灵感来自 AmpCode 的 deep mode——让 agent 像"不需要管理的高级工程师"工作。 ^[inferred]

### Prometheus 三段式质量保证链

| 角色 | 职责 | 设计 |
|------|------|------|
| **Metis** | 前置 gap 分析 | 在 Prometheus 生成计划前发现盲点 |
| **Prometheus** | 计划生成 | 只做计划不写代码，身份锁定强制执行 |
| **Momus** | 后置审查 | APPROVAL BIAS（默认通过），只拦截真正的 blocker |

身份锁定最核心——即使用户说 "just do it"，Prometheus 也必须拒绝并解释为什么需要规划。`prometheus-md-only` hook 在系统层面强制执行（非 `.md` 文件的写入会被拦截）。

### 工具权限矩阵

| Agent | 禁止的工具 | 设计意图 |
|-------|------------|----------|
| Oracle | write, edit, apply_patch, task | 只读顾问，防止"顾问自己动手" |
| Librarian / Explore | write, edit, apply_patch, task, call_omo_agent | 只搜索不修改，不能派生子 agent |
| Multimodal Looker | 只允许 read | 最严格，只能读文件 |
| Metis / Momus | write, edit, apply_patch, task | 只分析/审查不执行 |
| Atlas | task, call_omo_agent | 可读写但不能再派生 agent |
| Sisyphus-Junior | task（但允许 call_omo_agent） | 可调 explore/librarian 但不能委派新 task |

微妙设计：Sisyphus-Junior 允许 `call_omo_agent` 但禁止 `task`——防止无限递归委派。

## Hashline Edit 防幻觉编辑

OMO 工具体系中最具创新性的设计。每行内容生成 2 字符 CID 哈希（字符集 `ZPMQVRWSNKTXJBYH`），格式 `LINE#ID`（如 `5#VK`）。编辑操作必须携带正确的 LINE#ID 锚点，哈希不匹配则拒绝编辑并提示重新读取文件。

4 种操作：`set_line`、`replace_lines`、`insert_after`、`replace`。编辑从底部向上应用（bottom-up），保持行号引用稳定。

**解决的核心痛点**：传统精确文本匹配在 AI 记忆不一致时会静默失败。Hashline Edit 将"文件是否过时"的检测前置到工具层，从根本上消除了基于过时内容编辑的问题。 ^[inferred]

2 字符哈希在 token 开销和碰撞率之间平衡——16^2 = 256 种组合，单个文件行数碰撞概率极低。 ^[inferred]

## LSP + AST-grep 双引擎代码理解

**LSP 4 层架构**：
```
LSPClient (lsp-client.ts)           — 高层 API：openFile/definition/references/diagnostics
  └── LSPClientConnection            — JSON-RPC 连接管理
       └── lsp-client-transport.ts   — stdio 传输层
            └── lsp-process.ts       — LSP 服务器进程管理
```

提供 6 个工具：`lsp_goto_definition`、`lsp_find_references`、`lsp_symbols`、`lsp_diagnostics`、`lsp_prepare_rename`、`lsp_rename`。关键设计：文档版本追踪、内容去重（`lastSyncedText`）、双重诊断源（pull + push 回退）、服务器自动发现和安装。

**AST-grep** 基于 [ast-grep](https://ast-grep.github.io/) 实现结构化代码搜索，与 LSP 互补——LSP 擅长精确符号操作，AST-grep 擅长模式匹配。支持 25 语言、元变量模式（`$VAR` 单节点、`$$$` 多节点）。`getEmptyResultHint()` 在空结果时给出修正建议，大幅降低工具调用失败率。

## 后台 Agent 并发 + tmux 可视化

### 三级并发控制

`ConcurrencyManager` 实现三级粒度：模型级限制（如 Claude Haiku 10 并发、Opus 2）→ Provider 级限制 → 全局默认 5。

并发槽通过 Promise 队列实现等待，`settled-flag` 防 double-resolution——当 `cancelWaiters()` 和 `release()` 同时操作时防止 Promise 被 resolve 又被 reject。

### 双重完成检测

两条路径互为备份：
- **事件驱动**：监听 `session.idle` 事件，经过 MIN_IDLE_TIME_MS（5秒）校验
- **轮询兜底**：`pollRunningTasks()` 定期检查所有 session 状态

`tryCompleteTask()` 用状态检查实现原子性防止重复完成，并发槽在异步操作前释放防止槽泄漏。

### TmuxSessionManager QDEU 架构

Query-Decide-Execute-Update 四步架构将 tmux 实际状态作为唯一真实来源，内部 Map 仅作缓存：

1. **QUERY**：`queryWindowState()` → 获取 tmux 实际 pane 状态
2. **DECIDE**：`decideSpawnActions()` → 纯函数决定操作（可测试）
3. **EXECUTE**：`executeActions()` → 执行 tmux 操作
4. **UPDATE**：`sessions.set()` → 仅在 tmux 确认成功后更新缓存

这让用户能在 tmux 里**实时看到**每个后台 agent 在干什么——不是黑盒，而是透明的。 ^[inferred]

## Ralph Loop 自动续跑

Ralph Loop 是 OMO 最有"性格"的功能——当 agent 完成一轮后如果任务还没完成，自动注入 continuation prompt 让它继续干。名字来源于"像 Ralph 一样不知疲倦地工作"。

两条启动路径：Skill 命令路径（`/ralph-loop` 或 `/ulw-loop`）或消息模板路径（检测 `<user-task>` 标签）。

**completion_promise 机制**：用户指定完成承诺（如 `--completion-promise="all tests pass"`），Ralph Loop 在 agent 输出中搜索该字符串。检测采用双通道策略：
1. **Transcript 文件扫描**（快速、无网络开销）
2. **Session Messages API**（准确但慢）

这比"agent 说 done 就停"更可靠——agent 可能说 "I'm done" 但测试还没跑。 ^[inferred]

Ralph Loop 是 [[concepts/harness-engineering|Harness Engineering]] 中 Loop Engineering 的**具体实现**——自动续跑+completion_promise 让多次运行自主可控。 ^[inferred]

`ulw-loop` 是增强版，在续写前触发 ultrawork 模型覆盖（通过 SQLite 切换到更强大模型）。

## Hook 系统

Hook 创建分三大类：`createCoreHooks()`（会话生命周期+工具守卫+消息变换）、`createContinuationHooks()`（续写/自动化）、`createSkillHooks()`（技能相关）。

事件分发器 `createEventHandler()` 按 18 个 hook 固定顺序执行——监控类先执行，内容注入类中间，控制流类最后。

关键 Hook：
- **context-window-monitor**：区分 Anthropic "显示限制"(1M) vs "实际限制"(200K/1M)
- **preemptive-compaction**：上下文快满前主动压缩
- **tool-output-truncator**：根据模型窗口动态截断
- **session-recovery**：检测可恢复错误自动恢复
- **Context Injector**：4 级优先级上下文注入系统（critical/high/normal/low），`synthetic: true` 标记实现"agent 可见、用户不可见"

## 多 Provider 双层模型降级

| 层 | 机制 | 特点 |
|----|------|------|
| **安装时静态降级** | `ProviderAvailability` 布尔结构体 | 简单确定性强，基于用户声明订阅 |
| **运行时动态降级** | 四级优先级管道（UI选择→Category默认→Fallback Chain→系统默认） | 基于实际可用模型列表，带 fuzzy match |

运行时降级带 `provenance` 字段标记模型来源（override / category-default / provider-fallback / system-default），便于调试。

Agent 模型需求矩阵示例：
- sisyphus：claude-opus-4-6 → kimi-k2p5 → glm-5 → big-pickle
- hephaestus：gpt-5.3-codex（无降级，requiresProvider: openai）
- librarian：gemini-3-flash → minimax-m2.5-free → big-pickle（免费模型优先）

## Claude Code 兼容层

OMO 能加载 Claude Code 生态的全部扩展点：commands、agents、MCP servers、plugins、skills、hooks。四个 Loader 各司其职：

| Loader | 加载内容 | 来源路径 |
|--------|----------|----------|
| **claude-code-plugin-loader** | 第三方插件 | node_modules 扫描 |
| **claude-code-command-loader** | Markdown 命令 | `.claude/commands/` 等 4 位置 |
| **claude-code-agent-loader** | Agent 定义 | `.claude/agents/` |
| **claude-code-mcp-loader** | MCP 配置 | `.mcp.json` 等 4 位置 |

设计意图：让用户从 [[entities/claude-code|Claude Code]] 迁移到 OpenCode+OMO 时零成本复用已有配置。 ^[inferred]

## 配置系统

三级配置来源：项目级 `.opencode/oh-my-opencode.json[c]` → 用户级 `~/.config/opencode/oh-my-opencode.json[c]` → 内置默认值。

支持 JSONC（带注释的 JSON），Zod schema 验证，两级容错（完整验证→部分加载逐字段 safeParse），deepMerge 带原型链污染防护。

配置迁移系统处理 4 种变更：Agent 名称、Hook 名称、模型版本、字段迁移。`_migrations` 记录防止重复迁移，迁移前创建 `.bak` 备份。

## 8 大创新亮点

1. **AgentPromptMetadata 自描述系统** — 开放-封闭原则，新 agent 自动融入编排
2. **Hashline Edit 防幻觉编辑** — CID 哈希锚点，过时内容检测前置到工具层
3. **Ralph Loop completion_promise** — 用户定义"完成"，双通道检测
4. **双轨主 Agent** — Sisyphus（委派优先）vs Hephaestus（自主优先），行为模式切换比参数微调更可靠 ^[inferred]
5. **三级并发控制 + settled-flag** — 模型→Provider→全局精细控制
6. **TmuxSessionManager QDEU 架构** — tmux 状态为唯一真实来源
7. **Prometheus 三段式质量链** — Metis→Prometheus→Momus，避免"自己审查自己"
8. **Context Injector Synthetic Part** — `synthetic: true` 实现 agent 可见、用户不可见

## 局限与改进方向

- `delegate-task/tools.ts` 220+ 行承担多重职责，需要拆分
- Sisyphus prompt 约 500 行随 agent/category/skill 增加持续膨胀
- 多处硬编码魔数（`setTimeout 200ms` 等），缺乏自适应等待机制
- `fuzzyMatchModel()` 重复实现需要合并
- Ralph Loop 启动逻辑分散在 `chat-message.ts` 和 `tool-execute-before.ts`
- MCP 全依赖远程服务，网络不可用时完全不可用
- 自定义 Agent 元数据过于简化（统一 specialist/CHEAP），应允许声明真实成本

## 与其他实体的关系

- [[entities/claude-code|Claude Code]] — OMO 提供完整 Claude Code 兼容层，是 Claude Code 用户迁移到 OpenCode 的桥梁
- [[entities/langgraph-framework|LangGraph]] — LangGraph 是框架层面的 multi-agent 方案，OMO 是工具层面的实践实现 ^[inferred]
- [[concepts/harness-engineering|Harness Engineering]] — OMO 是 Harness Engineering 的杰出实现案例：工具权限矩阵=约束系统、Ralph Loop=自动续跑、并发控制=资源管理
- [[concepts/multi-agent-framework-comparison|Multi-Agent框架对比]] — OMO 不在框架对比中（它是插件而非框架），但体现了框架对比中的编排设计哲学

## 来源

- 多Agent协同：Oh My OpenCode 深度架构分析报告（raw/sources/AI 人工智能/AI Agent/Multi-Agent协同/）
