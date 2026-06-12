---
title: Hot Cache
updated: 2026-06-12
---

# Hot Cache

*~500字的近期活动语义快照。每次重大写入操作后自动更新。*

## Recent Activity

- [2026-06-12] INGEST — 评估系统增量：RAGAS评估框架+LLM评测基准六维全景，补全AI评估知识链
- [2026-06-12] LEARN — 自学推荐执行：LangGraph+GraphRAG 15篇博客推荐+12篇下载完成
- [2026-06-11] INGEST — 分类评估指标+数据飞轮+RAG工程扩充+数据结构与算法9页

## Active Threads

- **AI评估知识链成型**：evaluation-metrics(底层指标)→llm-benchmarks(评测数据集)→ragas-framework(RAG专用评估)→rag-engineering(评估层)→llm-observability(可观测性)——五层评估栈逐步补全
- **GraphRAG知识即将构建**：自学推荐已下载9篇GraphRAG博客，等待ingest蒸馏
- **LangGraph高级特性待补**：SubGraph/Command/Send/并行流已在自学推荐中，等待ingest

## Key Takeaways

- RAGAS四个核心指标是精确率/召回率思想在RAG领域的具体实现：Context Precision=检索精确率、Context Recall=检索召回率
- LLM评测基准按六大维度组织：知识(MMLU)→推理(GSM8K)→对话(MT-bench)→抽取(MS-MARCO)→安全(TruthfulQA)→编程(HumanEval)
- GraphRAG vs Vector RAG实测：80% vs 50.83%正确率（AWS Lettria数据）；关联型问题召回率70%→99%+
- GraphRAG开源生态四框架定位：MS=摘要生成、LightRAG=增量更新、KAG=逻辑推理、HippoRAG=事实问答

## Flagged Contradictions

- 3-RAG工程全景与【17】RAG工程全景内容完全相同（同一文件出现在两个路径），不是矛盾而是副本
- KAG"以推理为始" vs GraphRAG"以检索为始"——不同范式而非矛盾，取决于应用场景