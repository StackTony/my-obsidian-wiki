---
title: my-obsidian-wiki 知识库
category: projects
tags: [obsidian, wiki, 知识管理, llm]
aliases: [本vault, my-obsidian-wiki]
sources: [projects/my-obsidian-wiki]
summary: 本 vault 自身的项目知识枢纽：Karpathy 式 LLM wiki（raw/wiki/schema 三层），2026-06-01 经 wiki-setup 诞生，11 个知识域、993 来源、224 内容页；架构决策索引、运营模式、ingest 对账教训与待办债务。
provenance:
  extracted: 0.70
  inferred: 0.27
  ambiguous: 0.03
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-11-09
tier: supporting
created: 2026-11-09
updated: 2026-11-17
relationships:
  - target: "[[concepts/linux-os-virtualization-landscape]]"
    type: related_to
---

# my-obsidian-wiki 知识库

本页是 vault 自我描述的项目枢纽——给 3 个月后零上下文的自己（或新 session）快速恢复"这是什么、怎么运转、现在什么状态"。约定与工作流的权威定义在 `CLAUDE.md`，本页不重复其全文，只做索引与状态记录。

## 概述

- **定位**：基于 obsidian-wiki 框架的 Karpathy 式 LLM wiki，老板的知识第二大脑——LLM 负责所有整理维护（写 `wiki/`），人类是产品经理和审核者。
- **诞生**：2026-06-01 经 `/wiki-setup` 初始化（首日即执行过 rebuild，快照存于 `wiki/_archives/2026-06-01-rebuild/`）。
- **规模快照**（2026-11-17）：11 个知识域、993 个已 ingest 来源、224 个内容页（concepts 99 / summaries 60 / entities 20 / skills 22 / synthesis 7 / recommendations 15 / projects 1）、83 个 git 提交；另有 14 个非空源未入库（见待办）。
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

- **知识域扩张路线**：Linux 基础（6月）→ 虚拟化 → AI Agent 协议（8月）→ skill 化运维（9月）→ IO/面板（10月）→ 物理硬件层（11月上旬）→ 内核子系统纵深（11月中：驱动六子系统、内存分配与回收闭环、lockup 检测）——先横向铺满软件栈，再回头把每个子系统打穿上中下三层。 ^[inferred]（读自 git log 提交序列与 ingest 日志的归纳）
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
- **小体积不是"已入库"的证据**：2026-11-13 发现 `Linux 内存回收机制.md` 在 manifest 里只有 **36 B**（原文仅一张回收调用图），磁盘上已是 125 KB 全文，此前摘要蒸馏自那张图。判据是**磁盘体积 / 账本体积** 的比值而非哈希匹配：放大十倍以上应按"新增来源"全文重蒸馏。流程见 [[skills/ingest-integrity-verification]]。
- **Obsidian 会在 ingest 期间改写 raw 文件**：同一天源文件被编辑器自动重存两次（125,882→125,903 B、5,041↔5,063 B），diff 只有标题编号空格与 `[NR_WMARK]`→`\[NR_WMARK\]` 转义。教训：ingest 时不要在该笔记上操作，蒸馏后重算哈希，只校正账本、不重蒸馏，并把"格式变更 vs 内容变更"写进 log。 ^[inferred]

## 待办

- **manifest vault_path 过期**：顶层 `vault_path` 仍是旧机器路径（`C:\Users\23363\Data\code\...`），实际在 `D:\lkj_Data\`——多次上报，待老板决策修复。
- **draft 页面待人工审核**：几乎全部页面 `lifecycle: draft`；CLAUDE.md 未来候选已记录 `--consolidate` 自动提升模式（30天+confidence>0.7），引入时机待定。
- **CLAUDE.md 已记录的未来候选**：QMD 语义检索（vault>100 页后）、projects 子目录结构（≥3 活跃项目时）、`_raw/` 暂存区模式、跨项目 wiki-update。
- **待 ingest 积压（14 个未登账非空 + 1 个 180 B 存根，2026-11-17 扫盘）**：`Self learn/Harness Engineering/` 2 篇（30.2 / 18.5 KB）、`Self learn/ACP协议/` 6 篇（12.0 / 6.9 / 5.6 / 5.4 / 2.7 / 2.2 KB）、`AI Agent/逆向+反代工程/` 3 篇（15.9 / 9.0 / 0.7 KB）、`物理硬件/磁盘/Raid卡缓存策略.md`（2.6 KB）、`Self learn/AIGC/` 2 篇（0.1 KB / 72 B）；另 `Linux VFS 虚拟文件系统.md` 已登账但只有 180 B，等同未入库。最大缺口 `Linux 时钟系统/Linux 内核 tick 定时器.md`（50.9 KB）已于 2026-11-17 入库。Self learn 两批为 2026-11-12 Learn 流程下载，`credibility: low`。批量扫描脚本见 [[skills/ingest-integrity-verification]]。
- **空占位来源（12 个 0 字节）**：内存管理 3（MMU / 缺页异常 / 虚拟地址和物理地址）、IO 栈 2（异步AIO、用户态驱动IO）、文件系统 3（ext4 / proc / sysfs）、网络 1（NAT协议）、AI 2（ACL访问控制 / Ollama 本地运行）、数据结构 1（有向无环图）。补内容后再 ingest；0 字节文件 SHA-256 相同（`e3b0c442…`），不能作改名判据。
- **ACP 事实漂移待纠偏**：`summaries/acp-protocol` 与 `concepts/agent-communication-protocols` 仍把 ACP 写成独立的三方协议，而 IBM ACP 已并入 A2A、Zed ACP 是编辑器↔Agent 的另一条线（2026-11-12 Learn 流程发现，报告在 `recommendations/2026-11-12.md`）。下次碰到 A2A/ACP 源时优先改这两页，不要只加新页。
- **manifest 残留旧键（2 条）**：`Linux 内核 IO 栈/Linux 缓存IO和直接IO.md`（内容已由 `Linux 直接IO、缓存IO、内存映射mmap.md` 取代，键仍挂着 `concepts/linux-io-models`）、`Self learn/cpp_blog/【NO.358】ClickHouse 查询优化详细介绍.md`（源已删、无产出页）。需人工确认后迁移或清理。
- **来源路径已对齐**：`Linux 设备驱动管理` → `Linux 驱动管理`（11 页）、`Linux 驱动管理/Linux IOMMU` → `Linux 内核 IO 栈/Linux IOMMU`（10 页，manifest 8 键按 basename 迁移）；`log.md` 历史条目按约定不回改。**raw 目录仍在被重组**，ingest 前需重新扫盘。
- **断链实为 0**：2026-11-17 复核全库 222 页、约 1,750 条 wikilink，脚本报的 2 条全是假阳性（`[:space:]` POSIX 字符类撞 wikilink 语法、log 里带反引号的历史修复记录）——不必再当遗留债务追。

## 相关概念

- [[concepts/linux-os-virtualization-landscape]] — Linux OS/虚拟化知识域导航页（最大知识域的入口）
- [[concepts/linux-driver-model]] — 驱动域总纲（三大设备类型 + LDM + 总线框架），PCI/Block/网络/SCSI 四篇摘要的上游
- [[concepts/linux-memory-management]] — 内存域入口（分配 / 回收 / Page Cache 的整合页）
- [[synthesis/linux-kernel-subsystem-interactions]] — 内核子系统交互综合页（tier: core 的跨领域枢纽）
- [[skills/raw-source-link-sanitization]] — raw 导入源的追踪链接清洗流程（本 vault 维护技能）
- [[skills/ingest-integrity-verification]] — 源文件对账流程（小体积陷阱、哈希抖动、积压扫描）
- 基础设施文件（纯文本路径）：`wiki/index.md`（内容目录）、`wiki/hot.md`（近期快照）、`wiki/.manifest.json`（来源账本）、`wiki/log.md`（操作日志）、`CLAUDE.md`（schema 权威）
