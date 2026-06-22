---
title: Hot Cache
updated: 2026-06-22
---

# Hot Cache

*~500字的近期活动语义快照。每次重大写入操作后自动更新。*

## Recent Activity

- [2026-06-22] INGEST — SAG+RAG常用框架+软件工程+pending-hash修正：2个新页面+4个更新页面+10个manifest hash修正
- [2026-06-18] MANIFEST-FIX — 4个missing源清理+红黑树源文件替换登记：3个wiki页面frontmatter更新
- [2026-06-16] INGEST — Harness工程+Claude Code+高级RAG+向量数据库+LangGraph Memory：2个新页面+5个更新页面

## Active Threads

- **SAG vs GraphRAG范式对比**：SAG用SQL join替代全局图构建——查询时临时激活局部Hyperedge vs 提前建全局图，Recall@5差距明显（80.0 vs 65.1）
- **软件工程领域新开辟**：6大设计原则+9种架构模式+23种GoF设计模式已蒸馏，后续可连接Linux内核设计(KVM架构用Strategy/Observer模式等)
- **pending-hash全部修正**：10个Harness/Claude Code/RAG/向量数据库文件的SHA-256已从pending更新为真实值

## Key Takeaways

- **SAG核心创新**：不提前建全局图，查询时用SQL join临时激活局部结构——多跳检索的工程解法而非学术优雅
- **设计原则本质**：发现变化、隔离变化、以不变应万万变——与wiki的"蒸馏而非复制"理念同构 ^[inferred]
- **RAG框架生态**：7个开源框架各有定位——中文私有部署Chatchat、快速搭建FastGPT/RAGFlow、灵活定制LangChain/LlamaIndex/Haystack

## Flagged Contradictions

- GraphRAG"以检索为始" vs KAG"以推理为始" vs SAG"查询时临时生成"——三种范式而非矛盾
- Zleap商业声明"后RAG时代" vs 论文严谨性有张力——SAG有价值但"取代RAG"尚早 ^[ambiguous]
