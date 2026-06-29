---
title: Agent 系统架构设计：从执行循环到智能协作
category: summaries
tags: [AI, Agent, 执行循环, Skill, Memory, Sub-agent]
summary: Agent执行循环Observe-Think-Act架构：AgentLoop/AgentRunner分离设计、Skill vs Tool方法论区分、三层Memory（短期Session+中期history.jsonl+长期memory.md）+Consolidator压缩+Dream知识提取、Sub-agent完整AgentLoop实例+并发控制+禁止递归spawn、声明式架构+渐进式上下文加载+单一职责三大设计原则
source_dir: AI 人工智能/AI Agent/Agent架构设计
source_files: [Agent 系统架构设计：从执行循环到智能协作.md]
provenance:
  extracted: 0.70
  inferred: 0.25
  ambiguous: 0.05
base_confidence: 0.78
lifecycle: draft
lifecycle_changed: 2026-06-29
tier: supporting
created: 2026-06-29
updated: 2026-06-29
---

# Agent 系统架构设计：从执行循环到智能协作

原文：https://segmentfault.com/a/1190000047833249

## 核心内容

Agent与传统Chatbot的本质区别是**执行循环**——给定目标后自主迭代执行。本文从执行循环出发，构建Skill系统、MCP集成、Memory机制、Sub-agent协作，完成Agent架构的关键模块。

### 第一章 核心架构与执行循环

- **三步迭代**：Observe→Think→Act
- **AgentLoop/AgentRunner分离**：Loop控制流程+Runner执行细节，Runner可被Dream复用
- **Session管理**：对话对应Session对象，并发串行控制(session_locks)，mid-turn消息注入(pending_queue)
- **终止条件**：completed/max_iterations/error/ask_user四种，断点续传每次迭代后保存checkpoint
- **设计原则**：声明式架构（声明能力/知识/约束而非if-else）、渐进式上下文加载（4层分层避免token耗尽）、单一职责分离

### 第二章 Skill系统

- **Tool vs Skill**：Tool定义"能做什么"（Python类），Skill定义"如何做好"（Markdown文件）
- **渐进式加载**：目录扫描→摘要注入→完整内容按需读取
- **Workspace vs Builtin**：Workspace skill优先级高于builtin，用户无需编码即可注入领域知识

### 第三章 MCP集成

- **三种能力统一为Tool接口**：Tool（执行操作）、Resource（读取数据）、Prompt（返回模板）
- **命名规则**：mcp_{server_name}_{tool_name}
- **错误处理**：临时错误指数退避重试、永久错误修改参数、连接断开标记重连

### 第四章 Memory系统

- **三层记忆**：短期(Session.messages)、中期(history.jsonl)、长期(memory.md)
- **Consolidator**：prompt token>75%时压缩旧消息，在用户回合边界切割
- **Dream**：后台进程两阶段——Phase 1分析生成建议+Phase 2执行编辑，Git集成自动commit

### 第五章 Sub-agent机制

- **Sub-agent是完整AgentLoop实例**：独立ToolRegistry（不含spawn和message）、临时messages、精简System Prompt
- **禁止spawn防止递归，禁止message必须通过主Agent转发**
- **并发上限5个，级联清理**
- **错误分类**：tool_error部分完成、error执行失败、max_iterations步数限制、completed正常完成

### 第六章 总结

六大核心能力对照表+Chatbot vs Agent对比表+设计权衡（Session集中vs Memory分布式、同步工具vs异步Sub-agent、功能丰富vs约束安全）
