---
title: my-obsidian-wiki 知识库
category: projects
tags: [obsidian, wiki, 知识管理, llm]
aliases: [本vault, my-obsidian-wiki]
sources: [projects/my-obsidian-wiki]
summary: 本 vault 自身的项目知识枢纽：Karpathy 式 LLM wiki（raw/wiki/schema 三层），2026-06-01 经 wiki-setup 诞生，11 个知识域、940 来源、169 页；架构决策索引、运营模式、git 备份流与待办债务。
provenance:
  extracted: 0.70
  inferred: 0.27
  ambiguous: 0.03
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-11-09
tier: supporting
created: 2026-11-09
updated: 2026-11-09
relationships:
  - target: "[[concepts/linux-os-virtualization-landscape]]"
    type: related_to
---

# my-obsidian-wiki 知识库

本页是 vault 自我描述的项目枢纽——给 3 个月后零上下文的自己（或新 session）快速恢复"这是什么、怎么运转、现在什么状态"。约定与工作流的权威定义在 `CLAUDE.md`，本页不重复其全文，只做索引与状态记录。

## 概述

- **定位**：基于 obsidian-wiki 框架的 Karpathy 式 LLM wiki，老板的知识第二大脑——LLM 负责所有整理维护（写 `wiki/`），人类是产品经理和审核者。
- **诞生**：2026-06-01 经 `/wiki-setup` 初始化（首日即执行过 rebuild，快照存于 `wiki/_archives/2026-06-01-rebuild/`）。
- **规模快照**（2026-11-09）：11 个知识域、940 个已 ingest 来源、169 个 wiki 页面、66 个 git 提交。
- **仓库**：GitHub `StackTony/my-obsidian-wiki`；工作流为定期"vault backup"全量提交 + remote 推送。
- **双重身份**：既是知识库，又是 Obsidian 沉浸式主页——根目录 `dashboard.md` 定义沉浸式面板（快捷操作/天气/倒数日/音乐卡片），`.dashboard-backup/` 存面板配置备份。

## 架构决策

全部 codified 在 `CLAUDE.md`，此处只列决策与理由索引：

1. **三层 Zone 边界** — `raw/`（原始来源，AI 只读）、`wiki/`（AI 自治领地）、`CLAUDE.md`（schema）。原始资料不可变保证可追溯，wiki 可完全自动维护。
2. **编译而非检索** — ingest 时更新每个相关页面而非只建摘要；manifest SHA-256 delta 追踪支持增量 ingest，知识随时间复合而非每次查询重推导。
3. **来源透明** — `^[inferred]`/`^[ambiguous]` 行内标记 + frontmatter provenance 比例；隐藏猜测的 wiki 会无声腐烂，标记猜测的 wiki 保持可信。
4. **信任双轨** — `base_confidence`（来源数量×质量的公式化估计）× `lifecycle` 状态机（draft 由 ingest 设置，其余状态人工转换；stale 是计算叠加不是状态）。
5. **tier 分层** — core/supporting/peripheral 控制 ingest 更新意愿与检索优先级，防止低价值页面消耗上下文预算。
6. **可信度隔离** — `raw/sources/Self learn/` 为低可信度区（AI 自主收集、未经用户审核），其余 raw 目录高可信度。
7. **Recommendations 链接隔离** — 推荐报告禁止 wikilink 连核心知识页，Obsidian 图谱只显示知识网络本体。

## 关键模式（运营中沉淀）

- **知识域扩张路线**：Linux 基础（6月）→ 虚拟化 → AI Agent 协议（8月）→ skill 化运维（9月）→ IO/面板（10月）→ 物理硬件层（11月）——从软件栈逐层向下打通到物理世界。 ^[inferred]（读自 git log 提交序列的归纳）
- **重叠来源合并**：多篇讲同一主题的来源合并为一个 summary、source_files 双列（如 PCIe 错误双文、softirq 三件套）。
- **稀薄笔记折叠**：<1KB 的来源不建独立页，并入相关页面并在 manifest 登记产出（如芯片功耗 280B、ECC 792B）。
- **vault backup 自动提交**：git 定期全量提交（"vault backup: <时间戳>"），配合 GitHub remote 双端保存。
- **skill 生态外置**：35+ 驱动 skills（wiki-ingest/lint/dedup/update/cross-linker/daily-update 等）装在用户全局 `~/.claude/skills/`，vault 内 `.claude/` 仅存 anthropic-agent-skills——skill 迭代不污染知识库 git 历史。 ^[inferred]
- **hot.md 会话接力**：每次重大写入后更新 ~500 字语义快照，新 session 从 `hot.md` 恢复上下文而无需全库扫描。

## 待办

- **manifest vault_path 过期**：顶层 `vault_path` 仍是旧机器路径（`C:\Users\23363\Data\code\...`），实际在 `D:\lkj_Data\`——多次上报，待老板决策修复。
- **draft 页面待人工审核**：几乎全部页面 `lifecycle: draft`；CLAUDE.md 未来候选已记录 `--consolidate` 自动提升模式（30天+confidence>0.7），引入时机待定。
- **CLAUDE.md 已记录的未来候选**：QMD 语义检索（vault>100 页后）、projects 子目录结构（≥3 活跃项目时）、`_raw/` 暂存区模式、跨项目 wiki-update。
- **暂存区待消化**：git 暂存区已有一批"Linux 内存管理"新增/重命名 raw 文件（CPU Cache 一致性、内存屏障、TLB 改名），待下次 `/wiki-ingest`。

## 相关概念

- [[concepts/linux-os-virtualization-landscape]] — Linux OS/虚拟化知识域导航页（最大知识域的入口）
- [[synthesis/linux-kernel-subsystem-interactions]] — 内核子系统交互综合页（tier: core 的跨领域枢纽）
- 基础设施文件（纯文本路径）：`wiki/index.md`（内容目录）、`wiki/hot.md`（近期快照）、`wiki/.manifest.json`（来源账本）、`wiki/log.md`（操作日志）、`CLAUDE.md`（schema 权威）
