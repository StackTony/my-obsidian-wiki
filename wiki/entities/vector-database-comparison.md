---
title: 向量数据库选型对比
category: entities
tags: [AI, RAG, 向量库, Milvus, Qdrant, HNSW]
aliases: [向量库对比, Vector DB]
relationships:
  - target: "[[concepts/rag-engineering]]"
    type: related_to
  - target: "[[concepts/rag-chunking-strategies]]"
    type: related_to
  - target: "[[concepts/llm-infra-landscape]]"
    type: related_to
  - target: "[[concepts/llm-observability]]"
    type: related_to
source_dir: AI 人工智能/AI infra/大模型基础设施工程系列
source_files: [【大模型基础设施工程】18：向量库与图 RAG.md]
  # 跨目录补充
  # source_dir: AI 人工智能/Agent架构/向量数据库
  # source_files: [HNSW原理实践及阿里云灵积向量检索-博客园.md, 向量数据库是必要之恶，但不是银弹.md]
summary: 向量库选型核心：HNSW是默认索引（95-99%recall毫秒级），DiskANN解决10B+内存瓶颈，RaBitQ 32x压缩近无损；Milvus/Qdrant/pgvector三强覆盖不同规模；混合检索(dense+sparse+RRF)是生产标配
provenance:
  extracted: 0.78
  inferred: 0.19
  ambiguous: 0.03
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-16
---

# 向量数据库选型对比

向量库不是"存向量然后搜一下"——它是**ANN近似搜索+量化压缩+混合检索+过滤+一致性+运维**的系统工程。99%的生产系统用ANN而非暴力搜索；混合检索（dense+sparse+RRF）是标配；10B+规模必须用DiskANN/RaBitQ。

## 核心观点

- **HNSW是所有主流向量库的默认索引**：Milvus/Qdrant/Weaviate/Elasticsearch/pgvector都用它。95-99% recall，毫秒级延迟，内存开销120-150%。
- **DiskANN解决HNSW内存瓶颈**：10B+规模时，HNSW需数百GB内存；DiskANN只存PQ压缩向量（16-32 bytes/vector）在内存，全精度在SSD，P99 <10ms只需32-64GB内存。Milvus 2.4+、Weaviate、Pinecone serverless均已集成。
- **RaBitQ是2025推荐压缩方案**：32x压缩近无损recall（SIGMOD 2024）。比naive BQ（recall崩塌）有理论保证的无偏估计。Milvus 2.5+和Qdrant正在集成。
- **混合检索是生产标配**：纯dense recall无法打败dense+sparse+RRF融合。金融RAG案例：BM25 72% → hybrid 91%。
- **GraphRAG解决纯向量RAG两个弱点**：多跳推理和全局/摘要问答。但索引成本是纯向量RAG的500倍。

## 关键属性

### 索引算法对比

| 算法 | 复杂度 | 内存 | Recall | 适用规模 |
|------|--------|------|--------|---------|
| **Flat（暴力）** | O(N*d) | 100% | 100% | <1M, 离线基线 |
| **IVF-Flat** | O(√N*d) | 100% | 95-99% | 10M-100M, 需GPU |
| **IVF-PQ** | O(√N*d/m) | 5-25% | 85-95% | 100M-10B, 内存受限 |
| **HNSW** | O(log N*d) | 120-150% | 95-99% | 1M-1B, 主流默认 |
| **DiskANN/Vamana** | O(log N*d) | 5-10% | 93-97% | 10B+, 磁盘驻留 |
| **SPANN** | O(log N*d) | 10-15% | 93-97% | 10B+, Microsoft方案 |
| **ScaNN** | O(√N*d) | 30-60% | 96-99% | Google内部, 学术SOTA |

### 量化压缩对比

| 压缩 | 方案 | Recall损失 | 适用场景 |
|------|------|-----------|---------|
| 2x | fp16 | 0 | VRAM敏感 |
| 4x | int8 SQ | <1% | 通用 |
| 8-16x | PQ/OPQ | 2-5% | Billion+内存受限 |
| 32x | RaBitQ | <2% | 10B+, 2025推荐 |
| 64x+ | naive BQ | 5-15% | 仅粗排需rerank |

### 距离度量选择

| 度量 | 适用 | 关键规则 |
|------|------|---------|
| **L2（欧氏）** | 图像embedding | 几何直觉 |
| **IP（内积）** | LLM embedding（归一化后等价cosine） | BGE推荐 |
| **Cosine** | 等价于归一化后IP | 多库自动归一化 |
| **Hamming** | 二值向量（BQ/RaBitQ粗排） | XOR+popcount |

**关键**：同一collection不能混用度量。BGE推荐cosine——先归一化x=x/||x||，然后用IP一致查询。

### 内存vs磁盘决策树

- N < 10⁶：Flat / pgvector默认
- 10⁶ ~ 10⁷：HNSW全内存
- 10⁷ ~ 10⁸：HNSW + fp16/int8 SQ
- 10⁸ ~ 10⁹：IVF-PQ(GPU) 或 HNSW+RaBitQ
- 10⁹ ~ 10¹⁰+：DiskANN / SPANN / 对象存储

### HNSW参数推荐

| 场景 | M | ef_construction | ef_search |
|------|---|----------------|-----------|
| 默认 | 16 | 200 | 64 |
| 高recall | 32 | 400 | 128-256 |
| 内存紧 | 8 | 200 | 64 |
| 大规模+PQ | 16 | 200 | 64 |

## 六大向量库对比

### 专用向量库

| 产品 | 语言 | 核心特性 | 生产规模 |
|------|------|---------|---------|
| **Milvus/Zilliz Cloud** | C++/Go | 开源+商业托管；2.4+支持HNSW/IVF/DiskANN/GPU/多租户/混合检索 | 100B+（腾讯/字节/OPPO） |
| **Qdrant** | Rust | 单节点性能最优；payload filter最灵活 | Cloud托管 |
| **Weaviate** | Go | GraphQL接口；内置混合检索和模块化vectorizer | 中等规模 |
| **Chroma** | Python | 开发者友好；notebook首选 | **非生产级** |
| **LanceDB** | — | Lance列式格式；存算分离；S3原生 | Agent/Notebook场景 |
| **Vespa** | Java | Yahoo老牌搜索引擎；BM25+tensor+HNSW同时支持 | Spotify/Perplexity |

### 扩展型向量库

| 产品 | 特性 |
|------|------|
| **pgvector** | PostgreSQL扩展；HNSW+IVFFlat；pgvectorscale可做DiskANN |
| **Elasticsearch 8.x+** | 原生HNSW(Lucene 9)；BM25混合自然方便 |
| **Redis Search** | HNSW+Flat；超低延迟；热数据+小规模 |
| **ClickHouse/DuckDB/StarRocks** | OLAP+VECTOR类型；分析+向量融合 |

### 云托管服务

| 产品 | 特性 |
|------|------|
| **Pinecone Serverless** | 存算分离+按查询计费；比Pod版成本降50-70% |
| **AWS OpenSearch/Kendra** | AWS托管 |
| **Azure AI Search** | 与Azure OpenAI深度集成 |
| **GCP Vertex Matching Engine** | ScaNN托管版 |

### 国产向量库

| 产品 | 特性 |
|------|------|
| **DashVector（阿里）** | 阿里云向量服务 |
| **VikingDB（字节）** | 火山引擎向量服务 |
| **TencentVectorDB** | 腾讯云原生向量库；HNSW+RaBitQ |
| **OceanBase/TiDB/PolarDB Vector** | 传统DB+VECTOR；事务+向量一体 |

### 一致性模型

| 系统 | 模型 |
|------|------|
| Milvus | 最终一致性（Pulsar/etcd） |
| Qdrant | Raft强一致 |
| Weaviate | 可配置ONE/QUORUM/ALL |
| pgvector | 继承Postgres MVCC（最强） |

## 关键细节

### Filtered ANN

生产查询90%有过滤条件（租户/日期/语言）。三种方案：

| 方案 | 高选择性(s~0.01) | 低选择性(s~0.001) |
|------|----------------|------------------|
| **Pre-filter** | 好 | 好（转B+Tree） |
| **Post-filter** | 好 | 差（ANN n*k后过滤） |
| **Filtered HNSW** | 最佳(SOTA) | 需自适应路由 |

Qdrant和Milvus 2.3+实现Filtered HNSW。性能取决于选择性s：

### 混合检索

Dense(HNSW+embedding) + Sparse(BM25/SPLADE) 融合方式：
- **RRF**（Reciprocal Rank Fusion）— 默认
- 加权求和
- Learning-to-rank

SPLADE：将query和doc映射到30000维稀疏向量（BERT vocab），点积=语义BM25。

### GraphRAG

Microsoft GraphRAG Pipeline：
- Chunk(600-1200 tokens) → Entity/Relation Extraction(LLM) → Graph Construction → Community Detection(Leiden) → Community Summarization → Local/Global/DRIFT search

**索引成本**（1M token语料，~1500 PDF页）：
- 纯向量RAG embedding: ~$0.1
- GraphRAG索引: ~$40-60 (500x差距)
- LightRAG: 成本降至1/5-1/10

**召回效果**（金融研报RAG）：
- BM25: 72%
- 混合检索: 91%
- 纯向量全局摘要准确率: 58%
- GraphRAG全局摘要准确率: 83%

### HNSW退化问题

高频upsert下：软删除(tombstone)累积→邻居选择偏移→热点节点邻居列表过期。解法：周期compact+rebuild（Milvus compaction/Qdrant optimize/pgvector REINDEX），或版本化段（Milvus：新写入新段，旧段冻结，周期合并）。

### IVF训练陷阱

训练集至少nlist×39样本（理想nlist×50）。必须跨租户/时间/类别分层采样。生产环境季度重训练。

## HNSW原理实践与局限

HNSW由Yury Malkov团队2016年提出，核心思想：**层次化图结构**模拟小世界网络特性——上层稀疏图加速导航（快速定位目标区域），下层稠密图保证精度（精准匹配候选向量）。

### 检索过程

1. **顶层导航**：从入口节点贪心搜索（每次跳转至距离query最近的邻居），逐层向下
2. **底层精准匹配**：Layer 0扩大候选范围，计算距离，筛选Top-K

**关键参数**：
- `M`：每层最大连接数（高维D>1024建议20-40）
- `ef_construction`：索引构建候选数（建议M的2-5倍）
- `ef_search`：检索候选数（K=10时建议100-150）

### 阿里云灵积DashScope

阿里云灵积提供从向量嵌入→向量数据库→大语言模型的全栈RAG工具链：
- **text-embedding-v2**：768维向量，中文优化，单条≤100ms
- **向量数据库服务**：原生支持HNSW索引，可配置M/ef_construction/ef_search
- **检索调优实践**：实时交互RAG设M=20-30/ef_search=80-120（延迟≤30ms/recall≥95%）；高精度RAG设M=30-40/ef_search=150-300（延迟≤100ms/recall≥98%）

## 向量数据库的局限与务实选型

### 四大局限

| 局限 | 说明 | 影响 |
|------|------|------|
| **更新困难** | HNSW的"更新"是标记旧节点失效+重新插入，失效节点积累需周期重建索引 | 重建耗时数十分钟，期间服务性能下降 |
| **过滤查询弱** | 元数据（时间/分类/状态）和向量语义不在同一频道，只能"先向量检索→再内存过滤" | 高选择性过滤需先召回1000条才能筛出10条 |
| **精度与性能权衡** | ANN是"近似"，高维(>1024)各维度稀释语义信息 | ef从50升200，精度+4%但搜索时间×2-3 |
| **运维复杂且贵** | 100万×768维向量内存10-17GB（不是3GB），1亿条约1-1.7TB | 无专职DBA搭高可用集群是挑战 |

### 什么时候普通数据库就够了

| 场景 | 推荐 | 原因 |
|------|------|------|
| 精确匹配 | MySQL/PostgreSQL | 一毫秒返回 |
| 结构化过滤 | Elasticsearch倒排索引 | 原生索引远胜向量库元数据过滤 |
| 百万级以下 | pgvector/ES dense_vector | 统一系统两种能力 |
| BM25够用 | Elasticsearch BM25 | 80%场景覆盖，无需Embedding模型 |

**混合检索+场景适配**是比"All in向量数据库"更务实的选择。^[inferred]

## 成本革命

Turbopuffer模型：对象存储+按查询计费，冷数据在S3，查询时按需加载+LRU缓存。<$1/百万向量/月。Lance、Pinecone Serverless、pgvectorscale都在演进向这个模型。 ^[inferred]

## 未解问题

- ColBERT v2/PLAID late interaction能否成为2026 reranking标配？
- UEC 1.0对向量库生态的影响？
- 对象存储+按查询计费模型何时成为主流？

## 来源

- 【大模型基础设施工程】18 — 向量库与图RAG完整技术解析
- HNSW原理实践及阿里云灵积向量检索（raw/sources/AI 人工智能/Agent架构/向量数据库/）
- 向量数据库是必要之恶，但不是银弹（raw/sources/AI 人工智能/Agent架构/向量数据库/）
- [[concepts/rag-engineering]] — RAG工程全景
- [[concepts/rag-chunking-strategies]] — 分块策略