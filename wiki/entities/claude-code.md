---
title: Claude Code
category: entities
tags: [AI, Claude, Agent工具, 代码助手, Anthropic]
aliases: [Claude Code, claudian]
source_dir: AI 人工智能/Agent架构/Claude Code
source_files: [Claude Code 工作原理深度解析：从技术架构到设计哲学.md, Claude Code 使用技巧：从入门到精通.md]
provenance:
  extracted: 0.65
  inferred: 0.25
  ambiguous: 0.10
base_confidence: 0.80
lifecycle: draft
lifecycle_changed: 2026-06-16
tier: core
created: 2026-06-16
updated: 2026-06-16
summary: Claude Code是Anthropic的AI编程Agent——极简while循环架构而非复杂DAG、Bash作为核心工具、六层记忆系统、子代理上下文隔离、Hook自动化
relationships:
  - target: "[[concepts/harness-engineering]]"
    type: implements
  - target: "[[entities/langgraph-framework]]"
    type: related_to
  - target: "[[concepts/agent-framework-engineering]]"
    type: uses
---

# Claude Code

Claude Code 是 Anthropic 推出的 AI 编程 Agent。它不是代码补全工具，而是重新定义程序员工作方式的系统——程序员成为指导者，AI 成为执行者。其商业价值蒸蒸日上，本质就是在做 [[concepts/harness-engineering|Harness工程]]。

## 核心设计哲学

### 简单至上：从复杂DAG到简单循环

核心突破：**极简架构**。传统AI Agent构建复杂DAG（有向无环图）系统预定义流程。Claude Code 回到最简单的 **while循环**——名为"N0"的核心引擎：

```
while True:
    user_input = get_user_input()
    tool_calls = model.generate_tool_calls(user_input)
    results = execute_tools(tool_calls)
    model.update_context(results)
```

为什么简单更好？复杂系统试图预判所有可能性无法适应新情况；简单系统信任模型能力让它探索解决方案。

### 信任模型：探索而非工程化

核心理念："有疑问时，不要试图用if语句处理每个边缘情况。相信模型会探索并找到解决方案。"

实践原则：**less scaffolding, more model**——每增加一行脚手架代码，都要问"真的需要吗？"通常答案是"不需要"。

### Bash：人类与AI的通用语言

Bash作为核心工具的三大优势：
1. **功能全面且简单**：一个工具替代十几个专用工具
2. **丰富的训练数据**：数十年的使用数据，模型已学会人类如何使用它
3. **人类与模型的桥梁**：减少认知摩擦

工具系统演变：从专用工具（read_file/write_file/search_files等）简化为通用工具（bash/read/grep/glob/edit）。

## 技术架构

### 上下文管理：智能压缩

最大技术挑战：对话进行上下文越来越长，模型性能下降。

**92%阈值压缩策略**：
- 保留对话开始10-15条消息（建立任务上下文）
- 保留最近10-15条消息（当前工作状态）
- 中间部分智能总结：提取关键决策、代码修改、错误修复

### 子代理系统：上下文隔离

子代理解决"上下文污染"问题——创建专门用于特定任务的独立上下文子代理：
- **代码审查**：专门安全审查代理
- **深度研究**：研究代理深入挖掘文档
- **测试运行**：测试代理专注验证

### 技能系统：可扩展机制

Skill 是 Claude Code 的可扩展能力，三层加载系统：
1. YAML frontmatter — 始终加载
2. SKILL.md body — 相关时才加载
3. 链接文件 — 按需发现

好 Skill 的设计原则：**渐进式披露**、**写给AI看不是写给人看**、**保持简洁**。

## 记忆系统

详见 [[concepts/agent-framework-engineering|Agent框架工程]] 的记忆部分。Claude Code 六层记忆架构：

| 层级 | 名字 | 作用 |
|------|------|------|
| 6 | Agent Memory | 子代理的专属记忆 |
| 5 | Auto Memory | AI自己管理的长期记忆 |
| 4 | Local Memory | 项目私有配置 |
| 3 | Project Memory | 项目级指令（如CLAUDE.md） |
| 2 | User Memory | 用户全局偏好 |
| 1 | Managed Memory | 管理员策略 |

### Auto Memory工作方式

- **写入**：用户明确要求记住，或AI主动从对话中提取
- **四类内容**：user（用户偏好）、feedback（用户指导）、project（项目背景）、reference（外部参考）
- **读取**：扫描记忆目录（最多200文件）→ 排除已展示过的 → 小模型打分选出最相关5个 → 注入上下文

### 记忆时间衰减

| 年龄 | 处理 |
|------|------|
| 1-2天 | 正常使用 |
| >2天 | 显示"这段记忆可能是旧的"提醒 |
| >30天 | 标记stale，谨慎使用 |

### 三级上下文预警

| 使用率 | 提示 |
|--------|------|
| 60% | "记忆使用量较高" |
| 80% | "建议手动整理或开新对话" |
| 92% | "正在整理记忆..."触发压缩 |

## 使用技巧

### 上下文管理

| 需求 | 解决方案 |
|------|----------|
| 临时测试新想法 | `--fork-session` |
| 长期项目开发 | 主会话保存上下文，任务会话fork |
| 方案对比 | 多个fork并行探索 |
| 纎错 | `/rewind` 回退或fork新会话 |

### 并行工作：Worktree

Worktree 有独立上下文和文件快照，互不干扰。`claude --worktree` 进入。

### Hook机制：流程自动化

Hooks在特定事件发生时执行自定义脚本——安全确认、代码质量门禁、异步通知、端到端自动化。

## 内部开发哲学

- **蚂蚁喂养**：70-80%内部工程师每天使用，每5分钟一条反馈
- **潜在需求**：构建可被"滥用"的产品 → 观察用户如何使用 → 将"滥用"正式化为功能
- **双重用途工具**：人类和AI使用相同工具，统一心智模型

## 关键属性

| 属性 | 说明 |
|------|------|
| 开发者 | Anthropic |
| 核心架构 | while循环（N0引擎） |
| 核心工具 | Bash + read/grep/glob/edit |
| 记忆层级 | 6层（Agent→Auto→Local→Project→User→Managed） |
| 上下文压缩阈值 | 92% |
| 并行工作 | Worktree + Fork Session |

## 来源

- Claude Code 工作原理深度解析（raw/sources/AI 人工智能/Agent架构/Claude Code/）
- Claude Code 使用技巧：从入门到精通（raw/sources/AI 人工智能/Agent架构/Claude Code/）
- Claude Code 记忆系统设计（raw/sources/AI 人工智能/Agent架构/Memory记忆/）
