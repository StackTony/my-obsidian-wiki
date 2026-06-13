---
title: Hot Cache
updated: 2026-06-13
---

# Hot Cache

*~500字的近期活动语义快照。每次重大写入操作后自动更新。*

## Recent Activity

- [2026-06-13] PATH_FIX — 全量路径引用修复：21个wiki页面source_dir/source_files + 7个manifest键 + 1个JSON结构修复，零mismatch验证通过
- [2026-06-13] INGEST — RAG目录变动：2-RAG全栈介绍SHA-256变更，更新rag-engineering（补充m3e+落地路径+避坑清单）
- [2026-06-12] INGEST — 评估系统增量：RAGAS+LLM评测基准，补全AI评估知识链

## Active Threads

- **路径一致性完成**：全量审计raw/sources实际路径与wiki引用的匹配，三类系统性错误（缺云原生/前缀、Linux操作系统过浅、大小写）全部修复，manifest和wiki零mismatch
- **RAG工程实践链充实**：rag-engineering现已包含三阶段落地路径和避坑清单
- **GraphRAG知识即将构建**：自学推荐已下载9篇GraphRAG博客，等待ingest蒸馏
- **101个新文件未ingest**：Self learn(84)+Obsidian使用(10)+软件工程(3)+Agent智能体1+知识图谱2+安全性2——需后续ingest

## Key Takeaways

- 路径引用最常见错误：顶级目录名缺前缀（K8s→云原生/K8s，容器运行时→云原生/容器运行时）
- 跨目录整合的source_files必须含子目录路径前缀，否则无法解析
- Manifest JSON结构问题：数据结构与算法条目在sources对象外部（已修复）

## Flagged Contradictions

- 3-RAG工程全景与【17】RAG工程全景内容完全相同（同一文件出现在两个路径），不是矛盾而是副本
- KAG"以推理为始" vs GraphRAG"以检索为始"——不同范式而非矛盾
