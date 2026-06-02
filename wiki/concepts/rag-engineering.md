---
title: RAG工程全景
category: concepts
tags: [AI, RAG, 检索, 向量库, 知识图谱]
summary: RAG工程不是"向量检索+大模型生成"这么简单，而是从文档解析到答案评估的完整流水线——准确率更多取决于数据和检索工程
source_dir: AI 人工智能/Agent架构/Prompt + RAG
source_files: [2-RAG 全栈介绍.md, 1-RAG 核心术语速查表.md, RAG 搭建研究.md]
provenance:
  extracted: 0.65
  inferred: 0.30
  ambiguous: 0.05
base_confidence: 0.80
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: core
created: 2026-06-02
updated: 2026-06-02
relationships:
  - target: "[[concepts/llm-infra-landscape]]"
    type: uses
  - target: "[[concepts/rag-chunking-strategies]]"
    type: uses
  - target: "[[concepts/agent-framework-engineering]]"
    type: related_to
  - target: "[[entities/vector-database-comparison]]"
    type: uses
---

# RAG工程全景

RAG（Retrieval-Augmented Generation，检索增强生成）是大模型应用落地的核心武器。但RAG效果差，通常不能只怪大模型或Prompt——需要沿离线解析→清洗→切片→Embedding→索引→混合检索→重排→上下文组装→引用和评估逐层排查。

## RAG解决什么、不解决什么

**解决**：知识时效性（外部库随时更新）、幻觉抑制（答案有据可查）、私有知识接入、可追溯性、成本可控

**未解决**：复杂推理（多步逻辑推导）、极致实时性、跨文档关联推理——这些是Advanced RAG和Agentic RAG的目标 ^[inferred]

## RAG五代演进

| 代际 | 时间 | 特征 | 局限 |
|------|------|------|------|
| 第一代 | 2020 | 端到端可训练（Facebook AI Research） | 训练成本高、工程难度大 |
| 第二代 | 2022-2023 | 松散耦合：检索器+生成器，Prompt Engineering | Demo效果好、生产效果差 |
| 第三代 | 2023-2024 | Advanced RAG：查询重写、混合检索、重排 | 各组件优化但流水线僵化 |
| 第四代 | 2024-2025 | Modular RAG：模块化pipeline，可替换组件 | 模块组合需编排引擎 |
| 第五代 | 2025+ | Agentic RAG：Agent决定何时检索、检索什么、检索几次 | 复杂度高、可控性差 ^[inferred] |

## RAG完整流水线

```
离线处理链：
  文档 → 解析(PDF/HTML/Office) → 清洗 → 切片(Chunking) → Embedding → 索引(向量+倒排+图)

在线服务链：
  用户Query → 查询重写 → 混合检索(向量+BM25) → 重排(Rerank) → 上下文组装 → LLM生成 → 引用标注 → 评估
```

### 关键环节详解

1. **文档解析**：PDF结构提取、OCR扫描件处理、表格识别
2. **Chunking**：详见 [[concepts/rag-chunking-strategies]]
3. **Embedding**：选择模型（OpenAI text-embedding-3-large、BGE-M3等）、维度、批量编码
4. **索引**：向量索引（ANN：HNSW/IVF）、倒排索引（BM25）、图索引（GraphRAG）
5. **混合检索**：向量检索抓语义相似、BM25抓关键词匹配，RRF融合
6. **重排**：Cross-encoder模型对候选文档精排，Top-K裁剪
7. **上下文组装**：将检索结果拼入Prompt，控制token预算
8. **评估**：RAGAS框架（Faithfulness、Answer Relevancy、Context Relevancy、Context Precision）

## GraphRAG

- 在向量检索之外增加**图索引**——实体→关系→社区的结构化知识
- Microsoft GraphRAG：从文档提取实体和关系，构建知识图谱，生成社区摘要
- 优势：跨文档关联推理、可解释性更强
- 代价：构建成本高、更新维护复杂 ^[inferred]

## RAG工程要点

- **数据质量决定上限**：垃圾数据进→垃圾答案出，清洗和切片比Prompt重要 ^[inferred]
- **混合检索是标配**：纯向量检索漏关键词、纯BM25漏语义，两者融合效果最好 ^[inferred]
- **评估先行**：先建评估数据集和流水线，再调参数，否则无法量化改进 ^[inferred]

## 来源

- 2-RAG 全栈介绍（raw/sources/AI 人工智能/Agent架构/Prompt + RAG/）
- 1-RAG 核心术语速查表（raw/sources/AI 人工智能/Agent架构/Prompt + RAG/）
- RAG 搭建研究（raw/sources/AI 人工智能/Agent架构/Prompt + RAG/）