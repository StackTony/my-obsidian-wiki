---
title: Hot Cache
updated: 2026-06-11
---

# Hot Cache

*~500字的近期活动语义快照。每次重大写入操作后自动更新。*

## Recent Activity

- [2026-06-11] INGEST — 数据结构与算法 → 9个新wiki页面（4 concepts + 4 summaries + 1 skill + 1 synthesis）
- [2026-06-11] CROSS-LINK FIX — 系统性扫描全部wiki页面，修复35个文件中共约60处缺失行内wikilink

## Active Threads

- **数据结构与算法知识链成型**：二叉树 → 红黑树 → B/B+树 → 图论算法
- **平衡树演进视角**：BST→AVL→红黑树→B+树是逐步放松平衡约束的路线
- **LLM基础设施链接网补全**：infra-landscape、inference-engine、serving-infrastructure、observability 页面间的核心子概念（PagedAttention、量化、并行策略、推理引擎对比）现在都有行内wikilink

## Key Takeaways

- 最常见的链接遗漏模式：**页面在relationships块中声明了类型化关系但正文无行内链接**——读者必须看frontmatter才能发现关联
- LLM基础设施页面尤其容易遗漏：全景页提及6+个子概念但只通过relationships连接
- Linux内核页面：跨子系统讨论（如网络栈→零拷贝、锁→追踪框架、cgroup→CFS调度）最易遗漏交叉链接
- Summaries按设计不含wikilinks（它们是被引用的源文档蒸馏），不视为链接遗漏

## Flagged Contradictions

- Windows进程地址空间用AVL而非红黑树——原因未说明 ^[ambiguous]
- SPFA可能被特殊构造数据卡到O(nm)退化 ^[ambiguous]