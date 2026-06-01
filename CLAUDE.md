# LLM Wiki 规范

这是一个 Karpathy 风格的 LLM Wiki。LLM 是程序员；你是产品经理和审核者。

Wiki 不是聊天机器人——它是**编译产物**。知识蒸馏一次、持续更新，不是每次查询重新推导。

## 架构

三层结构：
1. **Raw sources** - `raw/sources/` 中的原始文档（不可变）
2. **Wiki** - `wiki/` 中 LLM 生成的 markdown 文件（AI 自治领地）
3. **Schema** - 本文件，定义约定和工作流程

## 目录结构

```
my-obsidian-wiki/
├── CLAUDE.md         # 本文件 - 规范和工作流程
├── .env              # 环境配置（gitignored）
├── raw/
│   ├── sources/      # 原始文档（231个 .md 文件，按主题分目录）
│   └── resources/    # 图片和媒体资源
└── wiki/
    ├── entities/     # 实体页面（人物、组织、工具、框架）
    ├── concepts/     # 概念页面和主题摘要
    ├── summaries/    # 来源文档摘要
    ├── synthesis/    # 跨领域连接与洞察
    ├── recommendations/ # 学习推荐报告
    ├── journal/      # 日期标注的反思与摘要
    ├── projects/     # 项目知识枢纽
    ├── skills/       # 实践技巧与教程
    ├── _archives/    # wiki-rebuild 时的快照存档
    ├── _staging/     # 审核队列（WIKI_STAGED_WRITES=true 时启用）
    ├── _raw/         # 未处理草稿暂存区（wiki-ingest 会消化后删除原文件）
    ├── .manifest.json # 来源追踪账本（SHA-256 哈希 delta 检测）
    ├── _meta/        # 元数据（taxonomy.md 标签词表等）
    ├── _insights.md  # 图谱分析（枢纽、桥梁、凝聚力）
    ├── index.md      # 内容目录（自动更新）
    ├── log.md        # 按时间顺序的操作日志
    └── hot.md        # 近期活动的语义快照（~500字）
```

## Zone 边界 — 绝不可违反

| Zone | Path | AI 可读？ | AI 可写？ |
|------|------|----------|----------|
| **Wiki** | `wiki/` | ✅ | ✅ — AI 的自治领地 |
| **Raw** | `raw/` | ✅ | ❌ 永不写入、移动或删除 |
| **Obsidian config** | `.obsidian/` | ✅ | ❌ 除非明确要求 |
| **Environment** | `.env` | ✅ | ❌ 仅在 `/wiki-setup` 时设置 |

**如果需要修改 `raw/`，先询问用户。** 原始资料不可变，wiki-ingest 从 `raw/` 读取、写入 `wiki/`。

## 核心约定

### 页面命名
- 使用 kebab-case：`machine-learning-foundations.md`
- 实体：`[[entities/person-name]]`
- 概念：`[[concepts/topic-name]]`
- 摘要：`[[summaries/source-name]]`

### Frontmatter（完整版）

```yaml
---
title: 页面标题
category: concepts|entities|summaries|synthesis|skills|journal|projects
tags: [标签1, 标签2]           # 最多5个领域标签
aliases: [别名1, 别名2]         # 可选，用于 dedup 和 cross-linker
created: 2026-06-01
updated: 2026-06-01
summary: 一两句摘要，≤200字符，让读者不用打开页面就能预览  # 重要！

# 来源追溯
source_dir: 目录路径
source_files: [文件1.md, 文件2.md]

# 来源标记（provenance）
provenance:
  extracted: 0.72    # 直接提取的比例
  inferred: 0.25     # LLM 推断的比例
  ambiguous: 0.03    # 有争议的比例

# 置信度与生命周期
base_confidence: 0.65          # [0.0, 1.0] — 基于来源数量和质量的时不变估计
lifecycle: draft               # draft → reviewed → verified → disputed → archived
lifecycle_changed: 2026-06-01  # 上次状态转换的日期
# lifecycle_reason: "..."      # 可选 — 状态转换原因
# superseded_by: "[[new-page]]" # 可选 — 仅 lifecycle=archived 时使用

# 重要性分层
tier: core|supporting|peripheral  # 默认 supporting

# 类型化关系
relationships:
  - target: "[[concepts/related-concept]]"
    type: extends
---
```

**必填字段**：`title`、`category`、`tags`、`summary`、`created`、`updated`、`base_confidence`、`lifecycle`
**可选字段**：其余所有

### 来源格式规范

采用 **目录 + 文件分离** 格式，精确追溯知识来源：

| 字段 | 说明 | 格式要求 |
|------|------|----------|
| `source_dir` | 来源目录（主题领域） | 不带 `raw/sources/` 前缀，不带文件名 |
| `source_files` | 具体文件列表 | 带 `.md` 后缀，相对于 `raw/sources/<source_dir>/` |

**示例**：
```yaml
# 单文件来源
source_dir: 数据结构与算法/树
source_files: [红黑树详解.md]

# 多文件整合
source_dir: Linux操作系统/Linux锁机制
source_files: [Linux 锁机制全景介绍.md, Linux SpinLock锁.md, Linux Mutex锁.md, Linux RCU锁.md]

# 跨目录整合（特殊情况）
source_dir: DFX工具
source_files: [==CPU==/perf工具分析虚拟机的性能事件.md, ==设置trace点==/perf工具.md]
```

### 来源标记（Provenance Markers）

每个 claim 有三种来源状态，行内标记以便区分信号和合成：

| 状态 | 标记 | 含义 |
|------|------|------|
| **提取** | *(无标记 — 默认)* | 直接来自原文的转述 |
| **推断** | `^[inferred]` 后缀 | LLM 综合的 claim — 连接、泛化或隐含推断 |
| **有争议** | `^[ambiguous]` 后缀 | 来源不一致或原文模糊 |

**示例**：
```markdown
- Transformer 可以跨位置并行计算，不同于 RNN。
- 这是它在现代硬件上扩展性更好的原因。 ^[inferred]
- GPT-4 大约在 13T token 上训练。 ^[ambiguous]
```

**为什么用 `^[...]` 语法**：
- 在 Obsidian 中类似脚注，渲染干净，不与 `[[wikilinks]]` 冲突
- 行内标记，一条 bullet 就是一条 bullet
- 默认 = 提取，所以没有标记的现有页面仍然有效

**frontmatter 概览**：可选在页面级别展示大致比例，便于扫描推测过多的页面：
```yaml
provenance:
  extracted: 0.72   # 大致的无标记句子比例
  inferred: 0.25
  ambiguous: 0.03
```
这些是 ingest 时写入的最佳估计值。`wiki-lint` 会重新计算并标记偏差。

### 类型化关系（Typed Relationships）

普通 `[[wikilinks]]` 只表达"相关"，不表达**如何相关**。`relationships:` frontmatter 块添加有类型的、有方向的知识图谱边：

```yaml
relationships:
  - target: "[[concepts/transformer-architecture]]"
    type: extends
  - target: "[[concepts/lstm]]"
    type: contradicts
  - target: "[[concepts/attention-mechanism]]"
    type: implements
```

**允许的关系类型**：

| 类型 | 含义 | 示例 |
|------|------|------|
| `extends` | 建立在目标之上或泛化目标 | GPT extends Transformer |
| `implements` | 目标概念的具体实现 | BERT implements Masked LM |
| `contradicts` | 与目标的 claim 冲突或反驳 | 证据A contradicts 证据B |
| `derived_from` | 基于目标改编或衍生 | 微调 derived_from 迁移学习 |
| `uses` | 依赖或依赖目标 | RAG uses 向量数据库 |
| `replaces` | 取代或废弃目标 | GPT-4 replaces GPT-3 |
| `related_to` | 兜底：相关但无更强方向类型 | 概念A related_to 概念B |

**规则**：
- 可选字段 — 没有已知类型关系时省略整个块
- 不要重复 — 如果 `[[foo]]` 已在行内 wikilink 出现，`relationships:` 条目只是给它加上类型
- 方向重要 — 声明条目的页面是**源**，`target` 是目标
- 不要捏造 — 只在来源材料使关系方向和类型明确时才添加条目，不确定时用 `related_to` 或省略

### 置信度与生命周期

每个页面有两个正交的信任信号：

```yaml
base_confidence: 0.65          # [0.0, 1.0]
lifecycle: draft               # draft|reviewed|verified|disputed|archived
lifecycle_changed: 2026-06-01
```

**置信度公式**：
```
base_confidence = source_count_score × 0.5 + source_quality_score × 0.5
source_count_score   = min(distinct_sources / 3, 1.0)
source_quality_score = avg(各来源的质量分)
```

**来源质量分**：

| 类别 | 分值 | 示例 |
|------|------|------|
| paper | 1.0 | arXiv、会议论文 |
| official | 0.9 | 官方文档、`*.gov` |
| documentation | 0.85 | 第三方技术文档 |
| book | 0.8 | 书籍、技术参考 |
| repository | 0.75 | GitHub README |
| blog | 0.55 | 个人博客 |
| session_transcript | 0.5 | 对话历史 |
| forum | 0.4 | Stack Overflow、HN、Reddit |
| unknown | 0.4 | 兜底 |
| llm_generated | 0.3 | LLM 自行反思 |

**生命周期状态机**：

| 状态 | 进入方式 | 说明 |
|------|----------|------|
| `draft` | 任何 ingest skill 首次写入 | 所有新页面默认 |
| `reviewed` | 仅人工编辑 | |
| `verified` | 仅人工编辑 | 时间不会自动降级 verified 页面 |
| `disputed` | 仅人工编辑 | 显示时覆盖除 `archived` 外的所有状态 |
| `archived` | 人工编辑，或 ingest skill 设置 `superseded_by` | 终态 |

**注意**：`stale` 不是状态——它是计算叠加：`is_stale = (today − updated) > 90天`。只有 ingest skill 可以设置 `draft`；所有其他状态转换必须由人工编辑。

### 重要性分层（Tier）

`tier:` 字段控制 ingest 时哪些页面值得更新，以及 query 时检索优先级：

| 层级 | 含义 | Ingest 行为 | Query 优先级 |
|------|------|-------------|-------------|
| `core` | 承载页面 — 入链多或处于桥梁位置 | 来源即使轻微相关也更新 | 索引和全文读取时最先呈现 |
| `supporting` *(默认)* | 标准页面，适度连接 | 来源有明显新 claim 时更新 | 标准优先级 |
| `peripheral` | 低连接页面 — 少入链、窄范围 | 仅当来源**主要关于**此主题时更新 | 最后备选；裁剪上下文预算时跳过 |

**分配规则**：
- 新页面默认 `tier: supporting`
- 入链 ≥5 或 `wiki-status` 标记为桥梁 → 提升为 `core`
- 入链 ≤1 且 90+ 天未更新 → 降级为 `peripheral`
- 人工 override 始终优先

### Cross-References（交叉引用）
- 使用 wiki-links：`[[entities/entity-name]]`、`[[concepts/topic-name]]`
- 始终链接到相关概念和实体
- 跨区域引用原始文件用纯文本路径或 prose 描述，不用 wiki-link
- 每个新页面应至少链接到 2-3 个已有页面

### 页面模板

创建新 wiki 页面时，使用以下结构：

```markdown
---
title: 页面标题
category: concepts
tags: [ml, 架构]
aliases: [别名]
relationships:
  - target: "[[concepts/related-concept]]"
    type: extends
source_dir: 来源目录
source_files: [来源文件.md]
summary: 一两句摘要，≤200字符
provenance:
  extracted: 0.72
  inferred: 0.25
  ambiguous: 0.03
base_confidence: 0.65
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: supporting
created: 2026-06-01
updated: 2026-06-01
---

# 页面标题

一段话总结本页涵盖的内容。

## 核心观点

- 来源的核心 claim，直接转述。
- 来源隐含但未直接陈述的泛化。 ^[inferred]
- 两个来源不一致的数字。 ^[ambiguous]

使用 [[wikilinks]] 连接相关页面。

## 未解问题

尚待解决或需要更多来源的问题。

## 来源

- [[summaries/source-name]] — 原始文章
```

### Delta 追踪（Manifest）

`wiki/.manifest.json` 是来源追踪账本，记录每个已 ingest 的源文件——路径、时间戳、SHA-256 内容哈希、产生的 wiki 页面。

**Manifest 使能**：
- **Delta 计算** — 自上次 ingest 以来有哪些新增或修改
- **增量模式** — 只处理 delta，不处理全部
- **审计** — 哪个来源产生了哪个 wiki 页面
- **过期检测** — 来源已修改但 wiki 页面未更新

**SHA-256 哈希是关键**：区分真正的内容变化 vs. 仅被 touch 的文件（git checkout、复制、NFS 时间戳漂移）。

## 工作流程

### 操作模式

| 模式 | 适用场景 | 行为 |
|------|----------|------|
| **Append** | 小 delta、增量更新 | 通过 manifest 计算 delta，只 ingest 新/修改来源 |
| **Rebuild** | 重大偏移、需要重新开始 | 将当前 wiki 存档到 `_archives/`，清空后重新处理所有来源 |
| **Restore** | 需要回退 | 恢复之前的存档 |

### Ingest（添加新来源）- 自建更新
1. 对于原始文件是新增的，依次执行下面的动作：
    1. 从 `raw/sources/` 读取来源文档
    2. 将摘要写入 `wiki/summaries/[source-name].md`
    3. 更新 `wiki/index.md` 添加新条目
    4. 更新/创建 `wiki/entities/` 中的相关实体页面
    5. 更新/创建 `wiki/concepts/` 中的概念页面
    6. 在 `wiki/log.md` 中追加条目
    7. 更新 `wiki/.manifest.json` 记录来源哈希和产出页面
    8. 更新 `wiki/hot.md` 语义快照
2. 对于原始文件已经是删除的，对应的相关引用和 summaries 和 concepts 也需要删除掉
3. 对于原始文件是有修改的，需要分析根据原始文件生成的 summaries 下的文件，summaries 和 concepts 下文件总结出来的内容是否需要优化更新，保持摘要内容和原始文件内容的高度一致性

**核心理念**：ingest 不是只创建来源的摘要——它应该**更新每个相关页面**。合并新信息、解决矛盾、加强交叉引用。

### Query（回答问题）- 分级检索协议

读取 wiki 是每个读侧 skill 的主要成本。使用最便宜的检索手段回答问题，**仅在更便宜的手段不足时升级**：

| 需求 | 检索手段 | 相对成本 |
|------|----------|----------|
| 页面是否存在？标题/分类/标签？ | 读 `index.md`；Grep frontmatter | **最便宜** |
| 1-2句页面预览 | 读 `summary:` 字段 | **便宜** |
| 页面中某个具体 claim 或段落 | `Grep -A 10 -B 2 "<term>" <file>` | **中等** |
| 整页内容 | `Read <file>` | **昂贵** — 最后手段 |
| 跨页关系 | `Grep "\[\[.*?\]\]"` 或从已知页面走 wikilink | 视情况而定 |

**执行步骤**：
1. 先读 `wiki/hot.md`（获取近期活动即时上下文）
2. 读 `wiki/index.md` 查找相关页面
3. **索引扫描**：只 grep frontmatter（标题、标签、摘要）
4. **段落扫描**：`Grep -A 10 -B 2` 定位具体 claim
5. **全文读取**（最后手段）：仅对前 3 个候选页面
6. 综合回答并附上 `[[wikilink]]` 引用
7. 注明 stale/disputed 页面

**重要**：如果回答有价值，将其存档为新的 wiki 页面

**为什么这很重要**：20 页的 vault 可以全文扫描。200 页的 vault 不行。分级检索是 vault 扩展到大规模的关键。

### Lint（健康检查）- 自检检查

结合 raw 下原始文件检查 wiki 目录下的内容，按顺序检查：
1. 孤立页面（零入链）
2. 断裂的 wikilinks
3. 缺失 frontmatter 必填字段
4. 缺失 summary（软警告）
5. 过期内容（来源比页面更新）
6. 页面间矛盾
7. 索引一致性
8. 来源标记漂移（AMBIGUOUS > 15%，INFERRED > 40% 且无来源）
9. 离散标签聚类（凝聚力 < 0.15）
10. 置信度/lifecycle schema 验证
11. 类型化关系有效性
12. 可提升页面候选

**合并模式**（`--consolidate`）：修复断裂链接、添加交叉引用、修正 lifecycle 状态、降级过期的 peripheral 页面、规范化标签、添加矛盾标注。

### Dedup（去重）- 身份识别

检测不同名称下覆盖同一概念的页面：
1. 从 frontmatter 构建页面注册表
2. 通过标题相似度检测候选对（Jaccard、编辑距离、子串、aliases）
3. 语义判决：合并 / 保持分离 / 需人工审查
4. 选择规范页面（更多入链、更丰富内容）
5. 合并内容，在次级路径写入重定向 stub（`redirects_to:` frontmatter）
6. vault-wide 重写 wikilinks
7. 更新追踪文件

### Cross-Link（交叉链接）- 自动发现
1. 从 frontmatter 构建页面注册表
2. 扫描未链接的提及（名称、别名、实体名）
3. 评分候选：精确匹配 +4、共享标签 +2、跨类别 +2
4. 应用链接：行内（首次提及）或 Related 段落
5. 推断并写入 `relationships:` 类型

### Learn（学习推荐新知识）- 自学推荐

**前置条件**：用户在 `wiki/recommendations/1-Day learn.md` 的"优先了解"章节指定学习主题

**执行步骤**：
1. **检查学习主题**：读取 `wiki/recommendations/1-Day learn.md`，检查"### 优先了解："章节
   - **如果为空**：直接报告"今日无学习主题，任务结束"，退出流程
   - **如果有内容**：继续执行后续步骤
2. **分析已有知识**：搜索 wiki 目录，识别知识库中已有的相关内容
   - 查看是否有历史推荐报告（`wiki/recommendations/YYYY-MM-DD.md`）
   - 查看已下载的原始文档（`raw/sources/Self learn/<主题目录>/`）
   - 标记 ✅ 已有 / ❌ 缺失
3. **探索下一步学习方向**：
   - 基于已有知识，推荐 **1-2 个新的延伸学习技术点**
   - 延伸方向应与当前主题相关但尚未覆盖
4. **联网搜索**：
   - 整理用户指定主题 + 延伸学习技术点
   - 使用 tavily-search 搜索技术博客（偏好：原理介绍、技术分析、架构图）
   - **避重**：检查历史推荐报告中的"下载博客清单"，排除已搜索/下载过的博客链接
5. **生成推荐报告**：
   - 已有知识总结（附纯文本路径引用）
   - 延伸学习方向（1-2 个新技术点）
   - 推荐博客清单（标题 + 链接 + 摘要 + 重点内容 + 类别）
   - 学习路径建议（入门→延伸→进阶）
   - 知识图谱关联建议
6. **保存报告**：写入 `wiki/recommendations/YYYY-MM-DD.md`
7. **下载博客**：使用 Defuddle CLI 将推荐的所有博客保存到 `raw/sources/Self learn/<按主题新建的目录>`下（标记为低可信度）

**注意**：只检查"优先了解"章节，"后续了解"部分不作为当日推荐依据

### Research（自主研究）
`/wiki-research <topic>` — 自主多源研究，搜索→整理→写入 wiki 页面

### Daily Update（日常维护）
`/daily-update` — 运行 lint、dedup、cross-link、digest 循环

## 索引格式

`wiki/index.md` 应包含：
- 分类标题（## Summaries, ## Entities, ## Concepts, ## Synthesis, ## Journal）
- 每个条目：`[[页面名称]]` — 一行摘要 ( #标签) — 注意标签前有空格

```markdown
## Concepts
- [[transformer-architecture]] — 序列建模的主流架构 ( #ml #架构)
- [[attention-mechanism]] — Transformer 的核心构建块 ( #ml #基础)
```

**格式规则**：标签前加空格。❌ `描述(#标签)` — ✅ `描述 ( #标签)` — 空格确保标签解析正确

## 日志格式

`wiki/log.md` 每条可解析：

```markdown
## [2026-06-01] 操作 | 标题

- [2026-06-01T10:30] INGEST source="数据结构与算法/树/红黑树详解.md" pages_updated=5 pages_created=2
- [2026-06-01T11:00] QUERY query="红黑树的平衡原理？" result_pages=3
- [2026-06-01T12:00] LINT issues_found=3 orphans=1 contradictions=1
```

## Hot Cache 格式

`wiki/hot.md` — ~500字的近期活动语义快照，每次重大写入操作后更新：
- Recent Activity：最近操作记录
- Active Threads：正在推进的主题
- Key Takeaways：关键洞察
- Flagged Contradictions：发现的矛盾

**作用**：下次 session 不需要遍历全 vault，直接从 `hot.md` 恢复上下文。

## 配置参考

| Variable | Value | Purpose |
|----------|-------|---------|
| `OBSIDIAN_VAULT_PATH` | vault root | 仓库绝对路径 |
| `OBSIDIAN_SOURCES_DIR` | `raw/sources` | wiki-ingest 读取来源 |
| `WIKI_DIR` | `wiki` | AI 写入输出页面 |
| `OBSIDIAN_LINK_FORMAT` | `wikilink` | 内部链接格式（wikilink 或 markdown） |
| `WIKI_TOKEN_WARN_THRESHOLD` | `100000` | 全 wiki 读取超 100K token 时警告 |
| `WIKI_STAGED_WRITES` | `false` | 直接写入，不经过审核队列 |

## Source Topics

`raw/sources/` 包含 231 个 markdown 文件，按主题组织：

- `AI 人工智能/` — AI infra, Agent架构, 大模型LLM
- `DFX工具/` — Development tools
- `Linux 操作系统/` — Linux OS knowledge
- `Linux 蛛拟化/` — Virtualization
- `Obsidian使用/` — Obsidian usage tips
- `Self learn/` — Self-study notes（图论等，低可信度）
- `云原生/` — Cloud native / Kubernetes
- `数据结构与算法/` — Data structures & algorithms
- `消息队列/` — Message queues
- `软件工程/` — Software engineering

## 最根本必须遵守的原则

- **编译而非检索** — Wiki 是预编译的知识。ingest 时更新每个相关页面，不只是创建来源摘要
- **随时间复合** — 每次 ingest 应让 wiki 更聪明，不只是更大。合并新信息、解决矛盾、加强交叉引用
- **来源透明** — 每个 claim 应追溯到来源。更新页面时注明哪个来源触发了更新
- **标记推断** — 默认句子是提取的。合成 claim 用 `^[inferred]`，有争议 claim 用 `^[ambiguous]`。隐藏猜测的 wiki 会无声腐烂；标记猜测的 wiki 保持可信
- **Wiki 是持久的** - 知识编译一次，保持最新并可以持续增量构建积累
- **LLM 写，人读** - LLM 负责所有的整理维护工作。原始资料不可变，AI 只读不写；Wiki 是 AI 完全拥有和维护的领地
- **交叉引用是最重要的部分** - 链接与内容同等重要
- **有价值的回答变成页面** - 积累你的知识，分析整合到已有的知识库
- **渐进式披露** - 先传递核心信息、再根据需求逐步补充细节，知识随时间深化
- **蒸馏而非复制** - Wiki 页面应蒸馏精华，5000字原文 → 500字概念页
- **保持中文** - 内容语言跟随源语言，本 vault 以中文为主
- **自我反思** - 每次执行完任务，回复用户前，再自动执行下面两条"神级"指令：
  1. **反驳自己**：主动审视自己的理解、方案是否有漏洞或错误
  2. **检查遗漏**：主动思考是否遗漏了重要信息、规则或细节

## 补充规则

#### 全局联网搜索规则
1. 禁止使用 Claude Code 原生 WebSearch、WebFetch 工具
2. 所有网络搜索、查文档、查资料、查报错 **必须使用 tavily-search MCP 插件**
3. 优先用 tavily-search 做全网检索，再解析页面内容
4. 当 tavily 每月使用次数到达限制无法使用后，可以重新启用 Claude Code 原生 WebSearch、WebFetch 等工具尝试搜索

#### 可信度分级规则
1. 对原始文档进行来源可信度分级索引，索引建立时应对低可信度内容单独标记。注意可信度分级规则**只针对原始文档**（raw 目录下的），wiki 目录下的不需要可信度分级。建议在 frontmatter 中添加 `credibility: low` 字段，或在 index.md 中使用独立分类，高低可信度的划分依据为：
    - **高可信度**：`raw/sources/` 下除 `Self learn` 外的所有目录，内容经过用户审核确认
    - **中可信度**：内容为提问过程中 AI 基于笔记分析整理和自行搜索汇总出来的放在 raw 下的文档
    - **低可信度**：`raw/sources/Self learn/` 目录，内容为 AI 自主探索收集的网络博客，未经用户审核确认
2. 当新增的内容与本地记录的已有内容有冲突时，可以主动寻求用户审核确认来提升新增内容的可信度

#### Recommendations 链接隔离规则
1. `wiki/recommendations/` 目录下的文件**禁止使用 wikilinks**（`[[...]]`）引用 `summaries/`、`concepts/`、`entities/` 或其他 wiki 页面
2. 推荐报告中引用 wiki 内容时，使用**纯文本路径**（如 `summaries/k8s-technical-principles`）或反引号代码引用，不使用双括号
3. 同理，`summaries/` 和 `concepts/` 中的页面也**禁止建立指向 `recommendations/` 的 wikilinks**
4. **设计意图**：recommendations 是临时性的学习推荐报告，不属于持久知识库核心内容。隔离链接确保 Obsidian 关系图谱中只展示核心知识网络（summaries ↔ concepts ↔ entities），避免推荐报告污染知识图谱的链接关系

#### 用户使用 AI 时的规则
给 AI 交流时（比如使用 Obsidian 里的 opencode 或 claudian 插件时），除特别通用的常识（今天几号）、规则类问题（执行xxx命令）回复外，其他复杂任务执行结束后，每次回复用户前，再自动执行下两条"神级"指令：
- 第一条指令是：**"反驳我"。**
- 第二条指令是：**"我遗漏了什么？"。**

## Preferences

- User name: 老板
- Language: Chinese (zh-CN) — 用中文沟通，wiki 内容跟随源语言
- Permission mode: yolo (agentic, minimal prompting)
- Model: GLM-5.1 via Anthropic-compatible proxy