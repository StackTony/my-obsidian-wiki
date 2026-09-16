---
title: Obsidian AI工具链
category: concepts
tags: [AI, Obsidian, 工具链, 插件, 知识管理]
aliases: [Obsidian AI生态, Claudian, OpenCode插件]
relationships:
  - target: "[[concepts/llm-wiki-methodology]]"
    type: implements
  - target: "[[entities/claude-code]]"
    type: uses
source_dir: Obsidian使用
source_files: [插件/Claudian 插件.md, 插件/OpenCode 插件.md, 插件/插件记录.md, Skill和MCP/obsidian相关skill和mcp.md]
summary: Obsidian接入AI的插件与工具全景：Claudian/OpenCode插件直连claude.exe、12个功能插件清单(Copilot/Clipper/qmd/Terminal)、obsidian-skills/Start My Day/web-access技能、Tavily/qmd MCP。
provenance:
  extracted: 0.75
  inferred: 0.22
  ambiguous: 0.03
base_confidence: 0.6
lifecycle: draft
lifecycle_changed: 2026-09-15
tier: supporting
created: 2026-09-15
updated: 2026-09-15
---

# Obsidian AI工具链

把Obsidian从被动笔记工具升级为AI驱动知识库所需的插件、技能和MCP配置——本vault运行环境的落地记录。

## 核心观点

### AI接入插件（三选一）

| 插件 | 仓库 | 说明 |
|------|------|------|
| **Claudian** | github.com/YishenTu/claudian | 在Obsidian内直接驱动Claude：重构文章、拆解概念、生成大纲/TODO/知识卡片、统一文档风格、散笔记→系统知识 |
| **OpenCode** | github.com/mtymek/opencode-obsidian | OpenCode的Obsidian集成 |
| **Copilot** | — | AI agent工具集成 |

npm安装的Claude Code需把插件指向实际二进制路径：`C:/Users/.../npm/node_modules/@anthropic-ai/claude-code/bin/claude.exe`（Claudian和OpenCode插件都支持此配置）。

### 功能插件清单

- **Clipper** — 网页抓取为markdown（LLM Wiki入库的入口）
- **Git** — 远程仓库管理
- **Image Toolkit** — 图片查看
- **Diagram.net** — 绘图
- **Docxer / Pandoc** — docx→md、多格式导出
- **Linter** — Markdown风格统一
- **Terminal** — 调用终端跑opencode或claude code
- **qmd** — 笔记量大后的类增强型RAG检索（BM25+向量混合，github.com/tobi/qmd）
- **Apex dashboard** — 工作台

### AI Skills（技能层）

- **obsidian-skills**（github.com/kepano/obsidian-skills）— kepano官方技能集
- **Start My Day / OrbitOS**（github.com/MarsWang42/OrbitOS）— AI自主学习探索笔记：每日任务自动学习，配套 scheduled_tasks.json 定时调度 + Day learn 示例规划
- **web-access**（github.com/eze-is/web-access）— 替代Claude Code默认web-search/web-fetch（仅限google）

### MCP（协议层）

- **Tavily** — 联网搜索MCP（本vault CLAUDE.md指定的默认搜索通道）
- **qmd** — markdown混合检索MCP server，LLM可作为原生工具调用

### 分层视角

工具链呈四层结构 ^[inferred]：**AI接入层**（Claudian/OpenCode，赋予执行权）→ **功能插件层**（Clipper/Git/Terminal，处理素材与运维）→ **技能层**（Start My Day等，封装工作流）→ **检索层**（qmd/Tavily MCP，规模化的查询基础设施）。这是 [[concepts/llm-wiki-methodology]] 三层架构在工具侧的映射 ^[inferred]。

## 关键细节

- Start My Day的"优先了解/后续了解"两段式学习规划，正是本vault CLAUDE.md Learn工作流读取的 `wiki/recommendations/1-Day learn.md` 的原型 ^[inferred]
- Day learn 示例中"推荐完成后通过Clipper保存到raw/sources/Self learn"的闭环，定义了Self learn目录的来源与低可信度定位

## 未解问题

- qmd 与本vault现有"index+grep分级检索"何时切换（Karpathy参考是~100源后引入）
- web-access 仅支持google，与Tavily的分工边界

## 来源

- 原文：Obsidian使用/插件/ 4个文件 + Skill和MCP/obsidian相关skill和mcp.md
- 方法论见 [[concepts/llm-wiki-methodology]]
