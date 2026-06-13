---
title: RAG存储技术
category: concepts
tags: [AI, RAG, 存储, 向量库, Elasticsearch, Milvus]
summary: RAG存储四层架构：原始文件(MinIO/Ceph/SeaweedFS)→元数据(PostgreSQL/MongoDB/Neo4j)→切片(ES/OpenSearch)→向量(Milvus/Qdrant/pgvector/ChromaDB)
source_dir: AI 人工智能/Agent架构/RAG/传统RAG
source_files: [RAG 存储技术：文件、元数据、切片、向量.md]
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
  - target: "[[entities/vector-database-comparison]]"
    type: related_to
---

# RAG存储技术

RAG系统的存储不是"一个向量库就够了"——而是四层架构：原始文件存储、元数据存储、切片存储和向量存储，各层各司其职，缺一不可。

## 四层存储架构

```
┌─────────────────────────────────────────────────────┐
│  Layer 4: 向量存储 — Milvus/Qdrant/pgvector/ChromaDB│  语义检索
│  Layer 3: 切片存储 — Elasticsearch/OpenSearch         │  关键词+过滤
│  Layer 2: 元数据存储 — PostgreSQL/MongoDB/Neo4j/Redis│  关系+属性
│  Layer 1: 原始文件存储 — MinIO/Ceph/SeaweedFS/JuiceFS│  原文追溯
└─────────────────────────────────────────────────────┘
```

## Layer 1：原始文件存储

保存原始文档（PDF、Word、HTML等），用于溯源、重新解析和审计。

| 方案 | 定位 | 特点 | 适用规模 |
|------|------|------|----------|
| **MinIO** | S3兼容对象存储 | 自托管、轻量、K8s友好 | 中小规模 |
| **Ceph** | 分布式存储 | 高可靠、PB级 | 大规模企业 |
| **SeaweedFS** | 轻量对象存储 | 快、简单 | 小规模快速部署 |
| **Garage** | S3兼容分布式 | 极轻量、去中心化 | 极小规模/边缘 |
| **JuiceFS** | POSIX兼容分布式 | Redis/DB做元数据，对象存储做数据 | 需POSIX语义场景 |

**工程要点**：
- 原始文件不删除——重新解析、增量更新、审计追溯都需要
- 文件名含doc_id，与元数据存储对齐
- 大文件分块存储（S3 multipart upload）

## Layer 2：元数据存储

存储文档元信息、实体关系、用户偏好等结构化数据。

| 方案 | 定位 | 适用场景 |
|------|------|----------|
| **PostgreSQL** | 关系数据库 | 文档元数据、用户权限、标签体系 |
| **MongoDB** | 文档数据库 | 灵活schema、嵌套结构（表格/代码块） |
| **Neo4j** | 图数据库 | 实体关系、多跳推理、[[concepts/graphrag-engineering]] |
| **Redis** | 缓存+KV | 会话状态、热点查询缓存、实时更新通知 |

**工程要点**：
- 每个文档必有`doc_id`+`source_url`+`created_at`+`updated_at`+`department`
- Neo4j中的实体关系用于GraphRAG场景（详见[[concepts/graphrag-engineering]]）
- Redis缓存热门Embedding结果，避免重复计算

## Layer 3：切片存储

存储Chunk文本+BM25倒排索引，用于关键词检索和过滤查询。

| 方案 | 定位 | 特点 |
|------|------|------|
| **Elasticsearch** | 全文搜索引擎 | BM25+聚合+过滤，生态成熟 | 
| **OpenSearch** | ES开源分支 | AWS维护，功能等同ES，无许可证争议 |

**工程要点**：
- 切片存储=向量存储的"辅助引擎"——专有名词、型号、错误码必须靠BM25
- 每个Chunk必须带`doc_id`+`page_num`+`section_title`，过滤查询需要
- ES集群和向量库集群可以物理分离，但逻辑上查询必须合并（RRF融合）

## Layer 4：向量存储

存储Embedding向量+HNSW/DiskANN索引，用于语义检索。

详见 [[entities/vector-database-comparison]] 的完整选型对比。

| 方案 | 定位 | 特点 |
|------|------|------|
| **Milvus/Zilliz** | 专业向量数据库 | 10B+向量、GPU加速、云托管可选 |
| **Qdrant** | Rust向量引擎 | 性能好、过滤查询强 |
| **Weaviate** | 向量+模块化 | 内置多模态、GraphQL |
| **pgvector** | PG扩展 | 不引入新系统、小规模首选 |
| **ChromaDB** | 轻量本地 | 开发调试、Demo首选 |
| **LanceDB** | Lance列式 | 嵌入式、零服务器、低成本 |
| **Turso** | libSQL分布式 | 边缘部署、全球复制 |

**存储优化**：
- **RaBitQ**：32×量化压缩，精度损失<5%，存储成本大幅下降 ^[inferred]
- **DiskANN**：磁盘索引，10B+向量不全部常驻内存
- **多向量模式**：ColBERT每个token存一个向量，存储膨胀~30×

## 云vs私有部署

| 维度 | 云托管 | 私有部署 |
|------|--------|----------|
| **初始成本** | 低（按量付费） | 高（硬件+运维） |
| **数据主权** | 依赖供应商 | 完全自主 |
| **弹性** | 自动伸缩 | 手动扩容 |
| **合规** | 需确认供应商合规 | 直接满足 |
| **运维复杂度** | 低 | 高 |

**经验法则**：数据敏感→私有部署；快速验证→云托管；生产长期→混合 ^[inferred]

## 各层联动

```
查询流程：
  用户Query → Embedding → 向量库召回Top-200
                → BM25关键词 → ES召回Top-200
                → RRF融合 → Top-50候选
                → 元数据过滤(部门/时间/权限) → Top-20
                → Rerank → Top-5
                → 原始文件溯源(doc_id→MinIO) → 上下文组装
```

四层缺一层：
- 没有向量层 → 语义检索失能
- 没有切片层 → 关键词/过滤查询失能
- 没有元数据层 → 权限/过滤/多跳推理失能
- 没有原始文件层 → 无法溯源、无法重新解析

## 延伸阅读

- [[concepts/rag-engineering]] — RAG工程全景（存储是底层基础设施）
- [[entities/vector-database-comparison]] — 向量库选型深度对比
- [[concepts/graphrag-engineering]] — GraphRAG存储（Neo4j图存储是核心）

## 来源

- RAG 存储技术：文件、元数据、切片、向量（raw/sources/AI 人工智能/Agent架构/RAG/传统RAG/）
