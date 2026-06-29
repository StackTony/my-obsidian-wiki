原文： [https://segmentfault.com/a/1190000047705765](https://segmentfault.com/a/1190000047705765)

> 系统掌握上下文管理、并行工作与工具扩展，让 AI 成为你的得力开发搭档

## 为什么你只用了 Claude Code 的 10%？

![Claude Code 核心能力全景图](https://image-static.segmentfault.com/414/646/4146461793-69db53b6e4172 "Claude Code 核心能力全景图")

很多开发者把 Claude Code 当作"智能搜索引擎"——问一个问题，得到答案，关闭会话。但这就像把法拉利当买菜车开，只发挥了它 10% 的能力。

本文从四个核心维度，帮你解锁 Claude Code 的完整潜力：

1. **上下文管理** — 让 AI 的"记忆"更可控
2. **并行工作** — 同时处理多个任务
3. **工具扩展** — MCP 与 Skill 的组合使用
4. **流程自动化** — Hook 机制

---

## 第一章：上下文管理 — 像 Git 一样管理对话

Claude Code 的上下文不是简单的聊天记录，而是一个包含文件快照、对话历史、工作目录状态的完整环境。理解这一点，是你进阶的第一步。

![分叉会话（Fork Session）原理图](https://image-static.segmentfault.com/283/401/2834017156-69db53bf5c836 "分叉会话（Fork Session）原理图")

### 1.1 上下文为什么重要？

**限制视角**

上下文窗口是有限的。长期会话会累积大量历史，消耗 Token 的同时，也可能让 Claude 混淆重点。

**可塑性视角**

Claude 的"记忆"来源于当前上下文。通过管理上下文，你可以引导它的行为边界，避免"上下文污染"——即无关历史干扰当前任务。

### 1.2 分叉会话（Fork Session）

想象一下：你正在开发一个功能，突然想尝试另一种方案，但又不想影响当前的进度。传统做法是开一个新终端，重新描述项目背景——这很耗时。

`--fork-session` 解决了这个问题。它像 Git 的 `git branch`，为对话创建一个独立分支。

**基本用法**

```
# 从最近会话分叉
claude --continue --fork-session
# 或简写
claude -c --fork-session

# 从指定会话分叉
claude --resume <会话名称或ID> --fork-session
```

**典型场景**

|场景|操作|
|---|---|
|方案 A/B 对比|分叉两个会话，分别尝试，最后选择|
|临时提问|分叉一个会话提问，完成后删除|
|预热上下文|一次性构建完整上下文，后续任务从这里分叉|

**实战示例：预热上下文**

```
# 第一次，耗时较长但值得
claude --new --name "project-context"
# 灌入项目文档、架构图、编码规范、团队约定...

# 后续任务，快速开始
claude --resume "project-context" --fork-session
# 新会话已包含所有背景知识，直接开始编码
```

### 1.3 回退会话（Rewind）

`/rewind` 类似 `git reset --hard`，在当前会话内回退到某个历史检查点。

**使用方式**

```
/rewind 5  # 回退到 5 个消息之前
```

**什么时候用？**

- 发现方向错了，想重新开始
- 想用不同的提问方式重新尝试

> **注意**：`/rewind` 是破坏性操作。如果只想尝试而不影响当前会话，请用 `--fork-session`。

### 1.4 恢复会话（Resume）

|操作|命令|
|---|---|
|列出所有会话|`claude --list`|
|恢复会话|`claude --resume <会话名称或ID>`|
|恢复并分叉|`claude --resume <ID> --fork-session`|

### 1.5 上下文管理速查表

|需求|解决方案|
|---|---|
|临时测试新想法|`--fork-session`|
|长期项目开发|主会话保存上下文，任务会话 fork|
|方案对比|多个 fork 并行探索|
|纠错|`/rewind` 回退或 fork 新会话|

---

## 第二章：并行工作 — Worktree 让多任务更优雅

在软件开发中，我们经常需要同时处理多个任务：主分支开发新功能、修复紧急 bug、尝试技术方案 A/B……

![Worktree vs Fork Session 对比图](https://image-static.segmentfault.com/206/090/2060906530-69db53c9f2ce3 "Worktree vs Fork Session 对比图")

传统做法是开多个终端窗口，但这会带来问题：重复加载上下文、状态无法共享、切换成本高。

### 2.1 Worktree 是什么？

Worktree 是 Claude Code 的并行工作模式。每个 Worktree 有独立的上下文和文件快照，互不干扰。

**进入 Worktree**

```
claude --worktree    # 或 claude -w
claude --worktree --name feature-branch  # 命名指定
```

**退出 Worktree**

```
/exit
```

退出时可以选择 "keep"（保留）或 "remove"（删除）。保留 Worktree 可以后续继续工作。

### 2.2 典型使用场景

**场景一：紧急 Bug 修复**

```
# 主会话正在开发新功能
claude --continue

# 突然线上出现 bug
claude -w --name hotfix-login-issue
# 独立环境修复，不影响主开发流
```

**场景二：技术方案对比**

```
claude --new --name "scheme-A"
# 在会话 A 中尝试方案

claude --new --name "scheme-B" 
# 在会话 B 中尝试方案 B
```

**场景三：多项目并行**

```
claude -w --name project-microservice   # 微服务
claude -w --name project-frontend       # 前端
claude -w --name project-documentation  # 文档
```

### 2.3 Worktree vs Fork Session

|特性|Worktree|Fork Session|
|---|---|---|
|文件系统隔离|完全独立|共享同一目录|
|适用场景|多项目、多分支|同一项目多方案|
|Git 比喻|`git worktree`|`git branch`|

---

## 第三章：工具扩展 — MCP 与 Skill 的正确打开方式

如果说 MCP 是"工具箱"，Skill 就是"说明书"。它们共同扩展了 Claude Code 的能力边界。

![MCP 与 Skill 的关系流程图](https://image-static.segmentfault.com/359/120/3591208962-69db53d011a75 "MCP 与 Skill 的关系流程图")

### 3.1 MCP 与 Skill 的关系

**MCP（Model Context Protocol）** 连接 Claude 到你的服务（数据库、GitHub、Notion 等），提供实时数据访问和工具调用能力。

**Skill** 则是一套预定义的工作流程，告诉 Claude 应该如何使用这些工具，确保每次交互的一致性和最佳实践。

||MCP（连接）|Skill（知识）|
|---|---|---|
|功能|提供工具和访问能力|定义使用方式|
|意义|Claude **能**做什么|Claude **应该**怎么做|

#### 没有 Skill 的 MCP

用户连接了 MCP 服务器，但每次对话都要从零开始摸索如何使用工具，结果不一致，效率低下。

```
用户：帮我从 Linear 获取这个项目的 ticket
Claude：需要使用 linear.list_issues 工具...
用户：另一个 ticket 呢？
Claude：还是用 linear.list_issues，参数改成...
```

#### 有 Skill 的 MCP

预构建的工作流自动激活，工具使用一致，最佳实践嵌入每次交互。

```
用户：帮我列出这个项目的未完成 ticket
Claude：[自动使用 linear.list_issues，按优先级排序，格式化输出]
用户：总结一下今天的进展
Claude：[自动调用多个工具，按项目规范生成报告]
```

### 3.2 常用 MCP 工具推荐

findskill，openspec, superpowers,frontend-design 等就不赘述了。网上这种太多了 说点下面说点大家可能不知道的但是很好用的。

#### JetBrains MCP

适合 IntelliJ、PyCharm、WebStorm 等 IDE 用户：

- 访问项目结构
- 执行 IDE 命令
- 获取代码分析
- 运行测试
- 管理版本控制
- 重构等功能

**使用效果**

```
用户：帮我重构这个类，遵循 SOLID 原则
Claude：[访问 IDE 的代码分析，识别问题，生成重构方案]
```

```
用户：重命名 xxx 函数
Claude：[访问 IDE refactor 接口]  // 一瞬间就完成，无需全局搜索
```

#### Playwright / Agent-Browser

浏览器自动化工具，适用于：

- 网页测试
- 数据采集
- 表单自动化
- E2E 测试
- 动态内容监控

#### DrawIO MCP/SKILL

直接创建和编辑 draw.io 流程图：

使用示例：

```
用户：画一个微服务架构图，包含 API Gateway、Auth Service、User Service、Order Service
Claude：[生成 draw.io XML，输出为 PNG/PDF]
```

### 3.3 Skill 什么时候该自己写？

社区找不到你要的skill，当一个流程**每周执行 1-2 次**时，就应该考虑 Skill 化。

Skill 的价值：

- **复用性**：一次编写，多次使用
- **标准化**：确保执行一致性
- **效率**：自动化复杂流程

#### Skill 目录结构

```
weather-bot/
├── SKILL.md              # [必需] 元信息 + 指令
├── agents/               # [可选] 展示元数据
├── scripts/              # [可选] 预写代码
├── references/           # [可选] 参考资料
└── assets/               # [可选] 直接素材
```

#### SKILL.md 编写要点

```
---
name: weather-bot
description: |-
  回答天气相关问题。当用户询问某地天气、
  气温预报或穿衣建议时激活此技能。
---
```

**注意事项**：

- description 是触发的唯一依据，写清楚触发条件
- 简洁是美德，问自己：这段话值不值占用的上下文空间

#### 好 Skill 的设计原则

**原则一：渐进式披露**

Skill 使用三层加载系统：

1. YAML frontmatter — 始终加载
2. SKILL.md body — 相关时才加载
3. 链接文件 — 按需发现

**原则二：写给 AI 看，不是写给人看**

避免：

- ❌ "凝聚三年经验" — AI 不需要背景故事
- ❌ "建设性、专业的" — 太抽象
- ❌ "在严格与宽容间找到平衡" — 没有标准答案
- ❌ "全面审查" — 需要明确检查清单

**原则三：保持简洁**

上下文窗口有限，每次加载都要权衡价值。

---

## 第四章：流程自动化 — Hook 机制

Hooks 允许你在特定事件发生时执行自定义命令或脚本，是 Claude Code 自动化能力的核心。

![Hook 事件驱动自动化流程图](https://image-static.segmentfault.com/549/395/549395489-69db53d4c7561 "Hook 事件驱动自动化流程图")

### 4.1 典型应用场景

**安全确认**

拦截高危命令执行，要求人工确认。

**代码质量门禁**

AI 完成文件编辑后，自动执行格式化和检查。

**异步通知**

将耗时任务（测试、批量修改）的状态推送到桌面或 IM 工具。

**端到端自动化**

串联完整开发闭环：编写代码 → 运行测试 → 构建镜像 → 部署环境。

### 4.2 Hook 编写最佳实践

1. **保持简洁** — 复杂逻辑写成脚本
2. **避免阻塞** — 耗时操作拖慢会话启动
3. **错误处理** — Hook 失败不应影响主流程
4. **条件执行** — 使用 `when` 条件避免不必要操作

---

## 第五章：资源汇总

### MCP 与 Skill 市场

- [Claude Marketplaces](https://link.segmentfault.com/?enc=onGTPNTs%2BzoApLwTkNJX1w%3D%3D.Vz3lhbAIAGmsb5k2gNR9vPDkkjh6Yg19SjoNtqGLJqxP7pXP9EmYAbjjgCU6n3ZT)
- [Skills.sh](https://link.segmentfault.com/?enc=zEXo3i6j4jTNtApYf3xNeA%3D%3D.1hZdZl6tMX1r81ozsa2BQ4qMOhqhEcQfc79C1%2BUT0A8%3D)
- [SkillsMP](https://link.segmentfault.com/?enc=EEQtYEjbZds2UGIbeGmzgg%3D%3D.RXYxfybSTIFNqEbvg9egZg1yCYgSThvb0EOcFDx46Js%3D)

### 推荐阅读

- 官方文档：Claude Code 核心功能详解
- MCP 协议规范：如何构建自定义 MCP 服务器
- Skill 开发指南：如何创建高质量 Skill

---

## 总结

Claude Code 远不止是一个聊天工具，而是一个可编程的 AI 辅助开发平台。

**核心技巧回顾**

|维度|关键技巧|
|---|---|
|上下文管理|`--fork-session` 安全探索，`/rewind` 回退，`/resume` 恢复|
|并行工作|Worktree 同时处理多个任务|
|工具扩展|MCP 连接外部服务，Skill 编排工作流|
|流程自动化|Hook 实现事件驱动自动化|

**进阶建议**

1. 创建项目专属"预热"会话，保存背景知识
2. 将重复流程 Skill 化，提升效率
3. 配置多个 MCP 服务器，扩展能力边界
4. 定期清理无用会话，保持系统性能

掌握这些技巧后，你会发现 Claude Code 从一个"智能问答工具"变成了一个真正的"AI 开发搭档"。