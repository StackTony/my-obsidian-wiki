---
title: my-obsidian-wiki 知识库
category: projects
tags: [obsidian, wiki, 知识管理, llm]
aliases: [本vault, my-obsidian-wiki]
sources: [projects/my-obsidian-wiki]
summary: 本 vault 自身的项目知识枢纽：Karpathy 式 LLM wiki（raw/wiki/schema 三层），2026-06-01 经 wiki-setup 诞生，11 个知识域、984 来源、204 内容页；架构决策索引、运营模式、raw 维护流程与待办债务。
provenance:
  extracted: 0.70
  inferred: 0.27
  ambiguous: 0.03
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-11-09
tier: supporting
created: 2026-11-09
updated: 2026-11-11
relationships:
  - target: "[[concepts/linux-os-virtualization-landscape]]"
    type: related_to
---

# my-obsidian-wiki 知识库

本页是 vault 自我描述的项目枢纽——给 3 个月后零上下文的自己（或新 session）快速恢复"这是什么、怎么运转、现在什么状态"。约定与工作流的权威定义在 `CLAUDE.md`，本页不重复其全文，只做索引与状态记录。

## 概述

- **定位**：基于 obsidian-wiki 框架的 Karpathy 式 LLM wiki，老板的知识第二大脑——LLM 负责所有整理维护（写 `wiki/`），人类是产品经理和审核者。
- **诞生**：2026-06-01 经 `/wiki-setup` 初始化（首日即执行过 rebuild，快照存于 `wiki/_archives/2026-06-01-rebuild/`）。
- **规模快照**（2026-11-11）：11 个知识域、984 个已 ingest 来源、204 个内容页（concepts 91 / summaries 53 / entities 20 / skills 18 / synthesis 7 / recommendations 14 / projects 1）、76 个 git 提交。
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
- **raw 目录重排会打断 manifest 键**：manifest 以"vault 相对路径"为键，源文件移动后哈希不变但旧键指向不存在的路径，delta 检测会报 missing。正确做法是**迁移键**（保留 hash/pages/ingested_at）并同步改 wiki 页面里的 `source_files`/来源路径，而不是重新 ingest；`log.md` 历史条目保持原样不回改。2026-11-11 一次批量对账迁移了 18 个键（内存管理 4 个重命名、`设备驱动管理/`→`驱动管理/` 8 个、PCI/IO 目录归属 6 个），迁移依据是「git 明确重命名」或「旧记录哈希与磁盘文件逐一比对命中」，不靠文件名猜测。 ^[inferred]
- **导入源追踪链接清洗**：知乎/腾讯云文章复制进 raw 后，正文术语被包成 `[文字](zhida.zhihu.com/search?zd_token=...)`、外链被 `cloud.tencent.com/developer/tools/blog-entry?target=` 或 `link.zhihu.com/?target=` 包裹。2026-11-11 清洗 14 个文件、437 处，只保留链接文字；文首 `原文：` 裸 URL 保留。因文字语义未变，**只同步 manifest 哈希，不重新蒸馏**。完整流程见 [[skills/raw-source-link-sanitization]]。
- **raw 目录按内核子系统重组**：`Linux 设备驱动管理/` 更名 `Linux 驱动管理/`，下分 PCI / SCSI / Block / 字符设备 / USB / 网络设备 子目录；IOMMU 后续独立迁入 `Linux 内核 IO 栈/Linux IOMMU/`。配套新增六份子系统手册（PCI 242KB、网络 231KB、SCSI 139KB、USB 95KB、块设备 54KB、DMA 与 IOMMU 52KB）。知识域正从"主题文集"向"子系统手册"演化。 ^[inferred]
- **子系统手册入库补齐了驱动域骨架**：六篇文档蒸馏为 6 篇摘要（`linux-pci-subsystem`/`linux-scsi-subsystem`/`linux-block-subsystem`/`linux-usb-subsystem`/`linux-network-device-subsystem`/`linux-dma-iommu-subsystem`）+ 1 篇总纲概念页（`linux-driver-model`）。六个子系统的结构体/API 命名高度同构，说明内核"框架层+驱动实现层"是横跨所有总线的统一范式，不是各子系统各自发明。 ^[inferred]
- **ingest 期间 raw 目录可能被并发重组**：2026-11-11 这次 ingest 全程 raw 树在变（IOMMU 目录迁位、文件改名、新手册陆续落入）。教训是 delta 结果只是"某一时刻的快照"——写 manifest 前必须重新扫盘并按 basename/哈希做键迁移，否则会写出指向不存在路径的键。 ^[inferred]

## 待办

- **manifest vault_path 过期**：顶层 `vault_path` 仍是旧机器路径（`C:\Users\23363\Data\code\...`），实际在 `D:\lkj_Data\`——多次上报，待老板决策修复。
- **draft 页面待人工审核**：几乎全部页面 `lifecycle: draft`；CLAUDE.md 未来候选已记录 `--consolidate` 自动提升模式（30天+confidence>0.7），引入时机待定。
- **CLAUDE.md 已记录的未来候选**：QMD 语义检索（vault>100 页后）、projects 子目录结构（≥3 活跃项目时）、`_raw/` 暂存区模式、跨项目 wiki-update。
- **待 ingest 积压（0 个非空）**：2026-11-11 一次 append ingest 消化了 `Linux 驱动管理/` 全部 10 个非空新来源（五大子系统文档 242/231/139/54/52KB、驱动架构、DMA 介绍、直接IO/mmap、文件一致性、学习大纲），Linux 操作系统目录已无未入库的非空文件。
- **空占位来源（11 个 0 字节）**：内存管理域 6 个（MMU / 页表管理 / 页面置换算法 / 伙伴分配器 / 缺页异常 / 虚拟地址和物理地址 / 页回收机制）、IO 栈 2 个（异步AIO libaio、io_uring；用户态驱动IO SPDK、DPDK）、文件系统 3 个（ext4 / proc / sysfs）、网络 1 个（NAT协议）、驱动管理 2 个（系统总线总览 / PCIe设备枚举）。补内容后再 ingest；0 字节文件的 SHA-256 相同（`e3b0c442...`），不能作为改名判据。
- **manifest 残留旧键（待确认）**：`Linux 内核 IO 栈/Linux IO全景介绍.html`（源已被用户删除，产出页仍在）、`Linux 内核 IO 栈/Linux 缓存IO和直接IO.md`（内容已由 `Linux 直接IO、缓存IO、内存映射mmap.md` 取代）、`Self learn/cpp_blog/【NO.358】ClickHouse...`（源已删除，无产出页）。0 字节陈旧键已在 2026-11-11 清理（`页表管理.md`、`设备驱动管理/Linux DMA传输.md`）。
- **来源路径已对齐**：`Linux 设备驱动管理` → `Linux 驱动管理`（11 页）、`Linux 驱动管理/Linux IOMMU` → `Linux 内核 IO 栈/Linux IOMMU`（10 页，manifest 8 键按 basename 迁移）；`log.md` 历史条目按约定不回改。**raw 目录 2026-11-11 全天在重组**，ingest 前需重新扫盘。

## 相关概念

- [[concepts/linux-os-virtualization-landscape]] — Linux OS/虚拟化知识域导航页（最大知识域的入口）
- [[concepts/linux-driver-model]] — 驱动域总纲（三大设备类型 + LDM + 总线框架），PCI/Block/网络/SCSI 四篇摘要的上游
- [[synthesis/linux-kernel-subsystem-interactions]] — 内核子系统交互综合页（tier: core 的跨领域枢纽）
- [[skills/raw-source-link-sanitization]] — raw 导入源的追踪链接清洗流程（本 vault 维护技能）
- 基础设施文件（纯文本路径）：`wiki/index.md`（内容目录）、`wiki/hot.md`（近期快照）、`wiki/.manifest.json`（来源账本）、`wiki/log.md`（操作日志）、`CLAUDE.md`（schema 权威）
