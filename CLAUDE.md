# LLM Wiki 规范

这是一个 Karpathy 风格的 LLM Wiki。LLM 是程序员；你是产品经理和审核者。

## 架构

三层结构：
1. **Raw sources** - `raw/sources/` 中的原始文档
2. **Wiki** - `wiki/` 中 LLM 生成的 markdown 文件
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
    ├── _archives/    # wiki-rebuild 时的快照存档
    ├── _staging/     # 审核队列（WIKI_STAGED_WRITES=true 时启用）
    ├── skills/       # 实践技巧与教程
    ├── index.md      # 内容目录（自动更新）
    ├── log.md        # 按时间顺序的操作日志
    └── hot.md        # 近期活动的语义快照（~500字）
```

## 核心约定

### 页面命名
- 使用 kebab-case：`machine-learning-foundations.md`
- 实体：`[[entities/person-name]]`
- 概念：`[[concepts/topic-name]]`
- 摘要：`[[summaries/source-name]]`

### Frontmatter
```yaml
---
title: 页面标题
created: 2026-06-01
updated: 2026-06-01
tags: [标签1, 标签2]
source_dir: 目录路径
source_files: [文件1.md, 文件2.md]
---
```

### Sources 格式规范

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

**设计意义**：
- `source_dir`：主题领域一目了然，便于分类索引
- `source_files`：精确追溯每个来源文件，便于更新维护

### Cross-References（交叉引用）
- 使用 wiki-links：`[[entities/entity-name]]`、`[[concepts/topic-name]]`
- 始终链接到相关概念和实体
- 跨区域引用原始文件用纯文本路径或 prose 描述，不用 wiki-link

### Zone 边界 — 绝不可违反

| Zone | Path | AI 可读？ | AI 可写？ |
|------|------|----------|----------|
| **Wiki** | `wiki/` | ✅ | ✅ — AI 的自治领地 |
| **Raw** | `raw/` | ✅ | ❌ 永不写入、移动或删除 |
| **Obsidian config** | `.obsidian/` | ✅ | ❌ 除非明确要求 |
| **Environment** | `.env` | ✅ | ❌ 仅在 `/wiki-setup` 时设置 |

**如果需要修改 `raw/`，先询问用户。** 原始资料不可变，wiki-ingest 从 `raw/` 读取、写入 `wiki/`。

## 工作流程

### Ingest（添加新来源）- 自建更新
1. 对于原始文件是新增的，依次执行下面的动作：
    1. 从 `raw/sources/` 读取来源文档
    2. 将摘要写入 `wiki/summaries/[source-name].md`
    3. 更新 `wiki/index.md` 添加新条目
    4. 更新/创建 `wiki/entities/` 中的相关实体页面
    5. 更新/创建 `wiki/concepts/` 中的概念页面
    6. 在 `wiki/log.md` 中追加条目
2. 对于原始文件已经是删除的，对应的相关引用和 summaries 和 concepts 也需要删除掉
3. 对于原始文件是有修改的，需要分析根据原始文件生成的 summaries 下的文件，summaries 和 concepts 下文件总结出来的内容是否需要优化更新，保持摘要内容和原始文件内容的高度一致性

### Query（回答问题）
1. 读取 `wiki/index.md` 查找相关页面
2. 阅读相关页面
3. 综合回答并附上引用
4. 输出的形式可以很多：Markdown、对比表格、幻灯片、图表
5. **重要**：如果回答有价值，将其存档为新的 wiki 页面

### Lint（健康检查）- 自检检查
结合 raw 下原始文件检查 wiki 目录下的内容，发现并处理以下动作：
- 对比原始文件和 summaries 摘要内容的一致性
- 找出矛盾的数据或页面之间的矛盾
- 标记过时的结论或被新来源取代的过时陈述
- 清理重复、孤立的页面或没有入站链接的孤立页面
- 发现并处理重复数据、数据缺口或缺失的交叉引用和索引链接
- 自动搜索补全空白或被提及但缺少页面的 concepts 概念

### Learn（学习推荐新知识）- 自学推荐
每日自动执行的学习推荐流程，发现并整理新知识：

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
- 每个条目：`[页面名称](链接)` - 一行摘要 - 元数据

## 日志格式

`wiki/log.md` 使用前缀：`## [YYYY-MM-DD] 操作 | 标题`

示例：
```markdown
## [2026-06-01] ingest | 文章：神经网络入门
- 创建 summaries/neural-networks-intro.md
- 更新 concepts/deep-learning.md
- 从 entities/backpropagation.md 添加链接
```

## Hot Cache 格式

`wiki/hot.md` — ~500字的近期活动语义快照，包含：
- Recent Activity：最近操作记录
- Active Threads：正在推进的主题
- Key Takeaways：关键洞察
- Flagged Contradictions：发现的矛盾

## 配置参考

| Variable | Value | Purpose |
|----------|-------|---------|
| `OBSIDIAN_VAULT_PATH` | vault root | 仓库绝对路径 |
| `OBSIDIAN_SOURCES_DIR` | `raw/sources` | wiki-ingest 读取来源 |
| `WIKI_DIR` | `wiki` | AI 写入输出页面 |
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

- **Wiki 是持久的** - 知识编译一次，保持最新并可以持续增量构建积累。即知识是一次性编译好的，不是每次查询重新推导
- **LLM 写，人读** - LLM 负责所有的整理维护工作。原始资料（Raw Sources）内容不可变，AI 只读不写；Wiki 才是 AI 完全拥有和维护的领地
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