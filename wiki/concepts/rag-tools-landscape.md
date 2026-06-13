---
title: RAG核心工具全景
category: concepts
tags: [AI, RAG, 工具, 解析, 向量模型, 重排序]
summary: RAG工具链全景：7类文档解析工具+分块策略演进+Embedding模型选型+向量库+重排序——选型先确认瓶颈再选工具
source_dir: AI 人工智能/Agent架构/RAG/传统RAG
source_files: [RAG 核心工具大全 - 7大解析工具+向量模型+数据库+检索排序.md]
provenance:
  extracted: 0.75
  inferred: 0.20
  ambiguous: 0.05
base_confidence: 0.65
lifecycle: draft
lifecycle_changed: 2026-06-13
tier: supporting
created: 2026-06-13
updated: 2026-06-13
relationships:
  - target: "[[concepts/rag-engineering]]"
    type: implements
  - target: "[[concepts/rag-chunking-strategies]]"
    type: uses
  - target: "[[entities/vector-database-comparison]]"
    type: uses
---

# RAG核心工具全景

RAG效果取决于整条流水线的工具选择——没有单一工具能打通所有环节。选型原则：**先确认瓶颈再选工具**。

## 7类文档解析工具

解析是RAG准确率的70%决定因素（详见 [[concepts/rag-engineering]]）。

| 工具 | 定位 | 优势 | 不足 | 适用场景 |
|------|------|------|------|----------|
| **Unstructured** | 通用解析框架 | 50+格式、分区(标题/表格/图片) | 速度偏慢 | 多格式混合文档 |
| **Marker** | PDF转Markdown | 高精度、表格保持、公式识别 | 仅PDF | 技术论文、双栏PDF |
| **PyMuPDF** | 原生PDF解析 | 极快、内存占用低 | 布局还原有限 | 简单PDF快速提取 |
| **Docling** | IBM开源解析 | 多格式、表格OCR、公式 | 较新生态不成熟 | 企业文档批量处理 |
| **MinerU** | PDF学术解析 | 公式→LaTeX、表格→HTML | 仅PDF、GPU依赖 | 学术论文深度解析 |
| **PaddleOCR** | OCR引擎 | 中文强、开源、多语言 | 仅图片/扫描 | 扫描PDF/图片文档 |
| **DeepSeek-OCR** | VLM驱动OCR | 理解版式、抗噪声 | API依赖 | 高精度OCR兜底 |

**工程选择路径**：
- 原生PDF → PyMuPDF快速提取 / Marker高质量
- 扫描PDF → PaddleOCR / MinerU
- 混合格式 → Unstructured分区路由
- VLM兜底 → GPT-4o/Qwen-VL（图片/表格/公式页面）

## 分块策略演进

详见 [[concepts/rag-chunking-strategies]]

三代演进路线：

| 代际 | 方法 | 代表 |
|------|------|------|
| 第一代(固定) | 固定大小/滑动窗口 | LangChain CharacterTextSplitter |
| 第二代(语义) | 语义分割/Meta-chunking/Late chunking | Jina Segmenter/LangChain SemanticSplitter |
| 第三代(代理) | Agent决定分块策略 | Agentic Chunker ^[inferred] |

## Embedding模型选型

详见 [[concepts/rag-engineering]] 的Embedding章节

| 模型 | 维度 | 特点 | 适用场景 |
|------|------|------|----------|
| **BGE-M3** | 1024 | 中文强、同时出稠密+稀疏+ColBERT | 中文RAG首选 |
| **Qwen3-Embedding** | 1024-4096 | 2025新出、C-MTEB SOTA | 中文场景最新选择 |
| **OpenAI text-embedding-3-large** | 3072(可截断) | Matryoshka、闭源 | 英文/国际化场景 |
| **E5-Mistral-7B** | 4096 | 大参数、MTEB强 | 学术研究 |
| **Jina v3** | 1024 | 长文8K、多任务 | 长文档场景 |
| **m3e-base/large** | 768/1024 | 国产中文专属、效果稳速度快 | 中文社区常用 |

**选型注意**：
- 归一化(cosine vs dot product)要确认
- 指令式embedding(E5/Qwen3)需加prompt前缀否则精度下降
- Embedding升级=全量重建索引，必须有A/B双写机制

## 向量库

详见 [[entities/vector-database-comparison]]

| 库 | 特点 | 适用规模 |
|----|------|----------|
| Milvus/Zilliz | 10B+、GPU加速 | 大规模生产 |
| Qdrant | Rust高性能、过滤强 | 中等规模 |
| Weaviate | 模块化、多模态 | 中等规模 |
| pgvector | PG扩展、零新系统 | 小规模/已有PG |
| ChromaDB | 轻量本地 | 开发调试 |
| LanceDB | 嵌入式、零服务器 | 低成本嵌入式 |

## 重排序(Rerank)

| 模型 | 特点 | 适用场景 |
|------|------|----------|
| **BGE-Reranker-v2(m3/gemma)** | 开源中英双语、m3轻量gemma质量更好 | 中文生产首选 |
| **RankGPT** | LLM做rerank、质量极高 | 高精度低延迟要求 |
| **FlashRank** | 极快、轻量 | 实时场景 |
| **Jina-Reranker-v2** | 多语、延迟友好 | 多语言场景 |
| **Cohere Rerank 3** | 闭源API、开箱即用 | 快速部署 |
| **Qwen3-Reranker** | 阿里2025、中文优势 | 中文场景 |

**三级漏斗**：向量召回Top-200 → ColBERT rescore Top-50 → cross-encoder Top-5

## 延伸阅读

- [[concepts/rag-engineering]] — RAG工程全景
- [[concepts/rag-chunking-strategies]] — 分块策略详解
- [[concepts/rag-storage-technology]] — RAG四层存储架构
- [[entities/vector-database-comparison]] — 向量库选型深度对比

## 来源

- RAG 核心工具大全 - 7大解析工具+向量模型+数据库+检索排序（raw/sources/AI 人工智能/Agent架构/RAG/传统RAG/）
