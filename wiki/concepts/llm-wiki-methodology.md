---
title: Karpathy LLM Wiki方法论
category: concepts
tags: [AI, LLM, 知识管理, Obsidian, 知识库]
aliases: [LLM Wiki, Karpathy Wiki, 编译式知识库, LLM知识库]
relationships:
  - target: "[[concepts/rag-engineering]]"
    type: related_to
  - target: "[[entities/claude-code]]"
    type: uses
  - target: "[[concepts/agent-framework-engineering]]"
    type: related_to
source_dir: Obsidian使用/Karpathy LLM Wiki
source_files: [Karpathy wiki方法论.md, 期望目标：构建个人的Karpathy LLM Wiki + Obsidian + Claude知识系统.md, 参考的CLAUDE.md文件.md, Obsidian-Wiki：LLM Wiki 的工程化实践.md]
summary: LLM应是知识库的"编译器"而非"检索器"——增量构建持久wiki，知识编译一次持续更新。三层架构(Raw/Wiki/Schema)+Ingest/Query/Lint三操作，本vault即此方法的落地实践。
provenance:
  extracted: 0.75
  inferred: 0.20
  ambiguous: 0.05
base_confidence: 0.7
lifecycle: draft
lifecycle_changed: 2026-09-15
tier: core
created: 2026-09-15
updated: 2026-09-15
---

# Karpathy LLM Wiki方法论

Karpathy 提出的个人知识库构建模式：LLM不是在查询时从原始文档检索（RAG），而是**增量构建并维护一个持久的、互联的 markdown wiki**——知识被编译一次、持续保鲜，而非每次查询重新推导。

## 核心观点

### 编译 vs 检索（与RAG的本质区别）

- **RAG工作流**：用户提问→向量检索→拉取文档碎片→LLM生成答案→结束。知识永远是"原材料"，LLM每次从零拼图，没有累积
- **LLM Wiki工作流**：摄入新文档→LLM提取知识→更新wiki页面、建立链接、标记矛盾→知识被"编译"；用户提问→直接查询已整合的wiki
- Wiki是**持久的、可复利的构件**：交叉引用已就位、矛盾已标记、综合分析反映读过的一切 ^[inferred]
- 两者是互补而非替代：个人/小团队尺度（几十到几百个源文档，Karpathy本人约100篇文章40万字）wiki可全装入context window，token效率更高；超出context window或需精确溯源时RAG更优；最佳实践是混合架构 ^[inferred]
- 关联 [[concepts/rag-engineering]]——本vault的检索协议（index→grep→read分级）正是wiki小规模下替代RAG的实践

### 三层架构

| 层 | 职责 | 谁写 |
|----|------|------|
| **Raw sources** | 原始文档，不可变，source of truth | 人类收集，LLM只读 |
| **Wiki** | summaries/entities/concepts/synthesis等markdown，互相链接 | LLM完全拥有 |
| **Schema** | CLAUDE.md等操作手册：目录结构、约定、工作流 | 人与LLM共同演化 |

**Obsidian是IDE，LLM是程序员，wiki是代码库**——人在一侧开Agent、另一侧开Obsidian实时浏览变化（graph view/链接跳转），人是产品经理和审阅者，负责sourcing、探索和提问；LLM做所有苦力活（总结、交叉引用、归档、记账）。

### 三大操作

- **Ingest**：新源入库→读源→写summary页→更新相关entity/concept页→更新index→追加log。单个源可能触及10-15个页面。可逐个深度参与，也可批量低监督
- **Query**：先读index找相关页→读页面→综合带引用的答案。**有价值的回答应归档回wiki成为新页面**——探索像ingest一样复利
- **Lint**：定期健康检查——矛盾、过期claim、孤儿页、缺失交叉引用、被提及但无页面的概念、可用web搜索填补的数据缺口

### 渐进式披露（Progressive Disclosure）

传统知识管理是一次性暴露（OneNote全记/RAG返回top-k chunks）；LLM Wiki是：
- 第一次摄入：LLM创建基础页面，标记"待深挖"
- 后续摄入：更新、补充、连接，知识逐步深化
- 查询时：只调取相关切片，背后有整个wiki支撑

这是skill发展的基石 ^[inferred]，也是CLAUDE.md"渐进式披露"原则的出处。

### 本vault的落地

本 vault（my-obsidian-wiki）即此方法的直接实践 ^[inferred]：
- 三层结构对应 `raw/sources`（不可变）→ `wiki/`（AI自治领地）→ `CLAUDE.md`（schema）
- Schema比Karpathy原版更工程化：manifest哈希delta追踪、provenance标记、置信度/生命周期状态机、tier分层、分级检索协议（参考 obsidian-wiki 框架的工程化实践，github.com/Ar9av/obsidian-wiki）
- index.md（内容目录）+ log.md（时间日志）双导航；规模增长后可用 qmd（BM25+向量混合本地搜索引擎，github.com/tobi/qmd）
- 适用场景：个人知识管理、研究深潜、读书伴侣wiki、团队内部wiki（Slack/会议记录喂入）、竞品分析/尽调/行程规划

## 关键细节

- Obsidian Web Clipper 浏览器插件：网页转markdown快速入库
- 用户目标文档明确了演进方向：从个人知识库走向"会思考、会协作、会自我进化的Agent系统"——用wiki方法构建ADN Claw（NOE Mate）整网级智能体系统 ^[inferred]
- Karpathy建议的规模参考：~100源文档不需要向量数据库，index+LLM能力足够

## 未解问题

- wiki与RAG混合架构的具体边界（哪些知识"编译"进wiki、哪些留给检索）尚无明确判据 ^[ambiguous]
- 多人协作场景下的review工作流（human-in-the-loop）如何规模化

## 来源

- Karpathy原文 gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- 期望目标分析文（Why/What/How三段式）
- 参考的CLAUDE.md Schema配置（早期版本，含comparisons分类和表格索引格式，后被本vault演进掉）
