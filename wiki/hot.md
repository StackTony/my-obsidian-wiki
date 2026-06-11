---
title: Hot Cache
updated: 2026-06-11
---

# Hot Cache

*~500字的近期活动语义快照。每次重大写入操作后自动更新。*

## Recent Activity

- [2026-06-11] INGEST — 分类评估指标(evaluation-metrics)：混淆矩阵→准确率/精确率/召回率/F1 + 与RAG评估的连接
- [2026-06-11] INGEST — AI 人工智能增量：data-flywheel + rag-engineering大幅扩充 + 3路径变更
- [2026-06-11] INGEST — 数据结构与算法 → 9个新wiki页面

## Active Threads

- **RAG工程知识深度大幅提升**：从概述→完整流水线细节(解析/切片/Embedding/检索/重排/改写/组装/评估/生产架构)
- **数据飞轮概念引入**：清华经管学院视角——知识循环→数据飞轮的进化，连接了RAG和Agent的数据基础
- **AI知识库与业务循环的闭环**：数据飞轮→RAG→Agent形成"数据→AI→业务→数据"正反馈链 ^[inferred]

## Key Takeaways

- RAG工程70%的准确率取决于文档解析质量——没有单一工具能打通所有文档
- ColBERT的Late Interaction在召回和重排之间提供"准Rerank"精度，但存储膨胀30倍
- CRAG(检索评估器+Web搜索兜底)是性价比最高的RAG纠偏方案，比Self-RAG(需微调)更易落地
- 数据飞轮核心洞察：记录内容从"提炼过的知识"转为"未经提炼的底层数据"，知识专家从"提炼"转为"原理级思考"
- 三级漏斗(向量Top-200→ColBERT Top-50→cross-encoder Top-5)是精度与延迟的最佳平衡

## Flagged Contradictions

- 3-RAG工程全景与【17】RAG工程全景内容完全相同（同一文件出现在两个路径），不是矛盾而是副本
- Prompt提示词.md从RAG目录移到Memory目录，暗示它更属于Agent记忆而非检索增强范畴