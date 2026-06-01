上一篇讲了 RAG 的端到端工程。这一篇把视角下沉到**存储与检索层**：向量索引算法怎么选、量化怎么压、产品生态怎么看，以及 2024—2026 年工业界最热的**图增强 RAG（GraphRAG）**怎么把知识图谱与向量检索缝合起来。

全文按”**算法底层 → 产品选型 → 工程实操 → 图 RAG 与趋势**”四段展开，尽量给能直接落地的参数与代码。

> 阅读提示：本篇偏工程向，配置参数、代码和决策树较多；图 RAG 部分建议结合前一篇 RAG 工程全景一起看；最后的案例与排错手册可作为实施时的 checklist。
> 
> 本文涉及的所有参数推荐值都是**起点**，实际生产需要用自己的数据做 A/B 后调优。

## 一、向量索引：从暴力到近似

向量检索的核心矛盾是：**维度 d 通常 768~4096，库大小 N 通常 106~1010，要在毫秒级返回 top-k**。暴力扫的复杂度是 O(N·d)，十亿规模根本过不去，所以工程上 99% 用 ANN（Approximate Nearest Neighbor）。

下表是主流索引算法的工程视角速查：

|算法|复杂度|内存|召回率|典型场景|
|---|---|---|---|---|
|Flat（暴力）|O(Nd)|100%|100%|<1M、离线评测 baseline|
|IVF-Flat|O(√N·d)|100%|95~99%|10M~100M、需 GPU|
|IVF-PQ|O(√N·d/m)|5~25%|85~95%|100M~10B、内存受限|
|HNSW|O(log N·d)|120~150%|95~99%|1M~1B、毫秒级、主流默认|
|DiskANN / Vamana|O(log N·d)|5~10%|93~97%|10B+、磁盘驻留|
|SPANN|O(log N·d)|10~15%|93~97%|10B+、Microsoft 方案|
|ScaNN|O(√N·d)|30~60%|96~99%|Google 内部、学术 SOTA|

### 1.1 Flat：离线评测的”金标准”

Flat 就是把所有向量摊平，查询时挨个算相似度。它的唯一作用是：**给其它索引算法做 recall 基线**。工程上几乎不用它上线，但离线调参必须用它跑一遍 ground-truth。

FAISS 里 `IndexFlatL2`、Milvus 里 `FLAT`、pgvector 不建索引直接 `<->` 就是暴力。100 万 × 768 维 fp32 就 3 GB、查询几百毫秒，10 亿就别想了。

### 1.2 IVF 家族：倒排 + 聚类

IVF（Inverted File）的思路很朴素：先用 k-means 把向量聚成 nlist 个簇，查询时只扫距离最近的 nprobe 个簇。N=10^8、nlist=4096、nprobe=32，扫的量从 10^8 降到 10^6，快 100 倍。

- **IVF-Flat**：簇内仍用原始向量，内存 100%，召回高；
- **IVF-PQ**：簇内向量做 Product Quantization，内存降到 1/16~1/32，召回降 3~5 个点；
- **IVF-SQ8**：簇内用 8-bit 标量量化，内存 1/4，召回损失 1 个点。

调参经验：

- **nlist ≈ 4·√N**：10^8 → nlist ≈ 40000；
- **nprobe**：先扫 1% 的 nlist，比如 nprobe=64，逐步加到召回达标；
- **训练样本**：k-means 至少要 nlist × 39 个训练点，否则质心不稳。

IVF 对 GPU 友好：大 batch 查询时，每个簇独立算，可以打满 H100 的 HBM 带宽。Milvus GPU 版、NVIDIA RAFT 都走这条路。

### 1.3 HNSW：图索引的工业标配

HNSW（Hierarchical Navigable Small World）是 2016 年 Malkov 提出的**分层图**，目前所有主流向量库（Milvus、Qdrant、Weaviate、Elasticsearch、pgvector）的默认索引。

核心思想：

1. 每个节点以概率 p=1/M 进入上一层，形成自顶向下的稀疏金字塔；
2. 查询从最顶层的入口点出发，贪心找到该层最近点；
3. 降到下一层，从该点继续贪心，直到 0 层；
4. 0 层做一次 ef_search 宽度的 beam search 返回 top-k。

![HNSW：图索引的工业标配](https://quant67.com/post/llm-infra/18-vector-graph/images/18-vector-graph-fig1.svg)

关键参数：

- **M**：每个节点在上层的邻居数，越大图越密，召回越高但内存越大。`M=16` 是工业默认，高维稠密可以到 32~64；
- **ef_construction**：建索引时 beam 宽度，默认 200，SOTA 召回建议 400~800；
- **ef_search**：查询时 beam 宽度，**上线可动态调**，通常 32~256，直接和 recall 挂钩。

内存估算：`mem ≈ N · (d·4 + M·2·4 + 8)` 字节。10^8 × 768 dim fp32 + M=32 ≈ 335 GB，这就是为什么十亿级上要配合量化或 DiskANN。

### 1.4 DiskANN / Vamana：把图搬到 SSD

微软 2019 年的 DiskANN 解决了一个痛点：**HNSW 内存吃不消**。它的 Vamana 图构造算法产生的图连通性更好，平均路径短，使得即便把大部分图放在 SSD 上，查询也只需要几十次随机 IO。

工程形态：

- 内存只放 PQ 压缩向量（16~32 字节/向量）做粗排；
- SSD 放完整精度向量 + 图邻接表；
- 查询：PQ 在内存里贪心找候选 → SSD 读精确向量重排。

10 亿向量、768 维、NVMe SSD 上，DiskANN 能做到 **P99 < 10 ms**、内存只需 32~64 GB，成本比全内存 HNSW 降一个数量级。Milvus 2.4+、Weaviate、Pinecone serverless 都内置了 DiskANN 形态。

### 1.5 SPANN / SCaNN：大厂方案

- **SPANN（Microsoft 2021）**：把 IVF 中心点放内存，posting list 放 SSD，用动态质心 + 边界扩张保证召回。和 DiskANN 同出微软，定位都是”百亿级磁盘驻留”。
- **SCaNN（Google 2020）**：核心是 **Anisotropic Vector Quantization**——不均匀地分配量化精度，对检索更关心的方向更精细。在 ANN-Benchmarks 上长期位居 Pareto 最前沿，但开源实现（ScaNN Python 库）部署生态不如 HNSW。Vertex Matching Engine 底层就是它。

## 二、量化：压缩率与召回率的博弈

量化是把 fp32 向量压成更少比特，本质是”**用精度换内存和带宽**”。

### 2.1 SQ / PQ / OPQ 基线

- **SQ（Scalar Quantization）**：fp32 → int8 / int4，每维独立截断。压缩 4×/8×，召回损失 1~3%。最简单也最常用；
- **PQ（Product Quantization）**：把 d 维切成 m 段，每段 256 个质心，一个向量压成 m 字节。d=768、m=96 → 96 B，压缩 32×；
- **OPQ（Optimized PQ）**：先旋转向量再 PQ，让段间更独立。召回平均提升 2~5 个点；
- **RQ / AQ**：Residual / Additive Quantization，层层逼近残差，召回更高但查询更慢。

### 2.2 RaBitQ：2024 的黑马

RaBitQ（SIGMOD 2024）把向量二值化到 1 bit/维，配合随机旋转和理论上可控的误差界，实测压缩 **32× 的同时召回几乎无损**。Milvus 2.5+、Qdrant 都在集成。它的核心是**有保证的无偏估计**，不像过去 BQ（Binary Quantization）那样召回崩塌。

### 2.3 工程选型

|压缩|方案|召回损失|何时用|
|---|---|---|---|
|2×|fp16|0|默认、显存敏感|
|4×|int8 SQ|<1%|通用|
|8~16×|PQ/OPQ|2~5%|亿级内存受限|
|32×|RaBitQ|<2%|百亿级、2025 推荐|
|64×+|BQ（朴素）|5~15%|仅粗排，需精排|

## 三、向量库产品地图

2026 年向量数据库市场大致分四类：**专用、扩展、云托管、国产**。

### 3.1 专用向量库

- **Milvus / Zilliz Cloud**：开源 + 商业托管，中国 Zilliz 主导，社区最活跃。2.4+ 支持 HNSW / IVF / DiskANN / GPU / 多租户 / Hybrid Search。千亿级生产案例（腾讯、字节、OPPO）最多；
- **Qdrant**：Rust 写的，单机性能极佳，payload filter 做得比 Milvus 灵活。2025 推出 Qdrant Cloud 和托管量化，成本刷新行业；
- **Weaviate**：Go 语言，GraphQL 接口，内置 hybrid search 和模块化 vectorizer；
- **Chroma**：Python 开发者友好，笔记本首选，生产级不足；
- **LanceDB**：基于 Lance 列式格式，**存算分离、零拷贝、S3 原生**，2025 爆火，适合 Agent / Notebook 场景；
- **Vespa**：Yahoo 开源的老牌搜索引擎，同时支持 BM25 + 张量 + HNSW，Spotify、Perplexity 在用。

### 3.2 扩展型（在 OLTP/搜索引擎上加向量）

- **pgvector**：PostgreSQL 扩展，HNSW + IVFFlat，配合 **pgvectorscale**（Timescale 出品）可做 DiskANN，十亿级仍在 Postgres 里；
- **pgvecto.rs**：Rust 重写的 pg 扩展，更快但生态略小；
- **Elasticsearch / OpenSearch**：8.x+ 原生支持 HNSW（基于 Lucene 9），和 BM25 混检天然顺手；
- **Redis Search（RediSearch 2.x）**：HNSW + Flat，延迟极低，适合热数据 + 小规模；
- **ClickHouse、DuckDB、StarRocks**：OLAP 加 VECTOR 类型，分析 + 向量融合查询。

### 3.3 云托管

- **Pinecone**：最早的 SaaS，2024 推出 **Serverless**：存储算力分离、按查询计费，成本较 Pod 版下降 50~70%；
- **AWS OpenSearch / Kendra / S3 Vectors**：AWS 2025 推出 S3 Vectors 预览，把向量当对象存；
- **Azure AI Search**：原 Cognitive Search，深度集成 Azure OpenAI；
- **GCP Vertex Matching Engine**：SCaNN 托管版；
- **阿里 DashVector、火山 VikingDB、腾讯云 VectorDB、百度 VectorDB**：国内云厂全入场。

### 3.4 国产

- **Milvus / Zilliz**：国产开源代表；
- **OceanBase Vector**、**TiDB Vector**、**PolarDB Vector**：传统数据库加 VECTOR，事务 + 向量一体；
- **StarRocks Vector**、**Doris Vector**：OLAP 融合向量；
- **TencentVectorDB**、**华为 GaussDB Vector**：云原生商业版。

国内选型的一般建议：中小规模在 PG 生态（pgvector / PolarDB）；海量专用选 Milvus；OLAP + 向量分析选 StarRocks。

### 3.5 Turbopuffer 与成本革命

2024 年 Turbopuffer、Qdrant Cloud 等把 **“对象存储 + 按查询计费”** 做到极致：冷数据驻 S3、查询时按需加载 + LRU 缓存，成本做到 **每百万向量每月 <$1**。这对传统”买 n 台内存机常驻”的模式是降维打击。Lance、Pinecone Serverless、pgvectorscale 都在向这个方向演进。

## 四、混合检索：不是非稠密即稀疏

工业 RAG 里，**纯稠密检索的召回一般打不过 hybrid**。混合检索的基本配方：

- **稠密**：HNSW + BGE / E5 / text-embedding-3 / Qwen3-Embedding；
- **稀疏**：BM25 或学习到的稀疏编码（SPLADE、uniCOIL）；
- **融合**：RRF（Reciprocal Rank Fusion）、加权求和、learning-to-rank。

示例：SPLADE 把 query 和 doc 都映射到 30000 维稀疏向量（BERT vocab），点积 = 语义 BM25。Milvus 2.4+、Elastic 8.x、Qdrant 1.10+、Vespa 都原生支持稀疏向量。

```
# Milvus 2.4 Hybrid Search 示例
from pymilvus import MilvusClient, AnnSearchRequest, RRFRanker

client = MilvusClient(uri="http://localhost:19530")

dense_req = AnnSearchRequest(
    data=[dense_query],
    anns_field="dense",
    param={"metric_type": "IP", "params": {"ef": 128}},
    limit=50,
)
sparse_req = AnnSearchRequest(
    data=[sparse_query],
    anns_field="sparse",
    param={"metric_type": "IP"},
    limit=50,
)
res = client.hybrid_search(
    collection_name="docs",
    reqs=[dense_req, sparse_req],
    ranker=RRFRanker(k=60),
    limit=10,
)
```

### 4.1 Filtered ANN

纯 ANN 之外，生产里 90% 的查询带过滤：`tenant_id = X AND created_at > Y AND lang = "zh"`。实现方式有三：

1. **Pre-filter**：先按标量索引筛出候选 ID，再在 ID 集上做 ANN。选择率低时 OK，选择率高时 ANN 图跳转失效；
2. **Post-filter**：先 ANN 取 top-n·k，再过滤。选择率高时准但慢，选择率低时召回崩；
3. **Filtered HNSW**（Qdrant、Milvus 2.3+）：在图遍历时实时判断是否满足过滤，不满足的邻居继续扩展。这是目前 SOTA，Qdrant payload index 是教科书实现。

在 Milvus 和 Qdrant 里配合**按 tenant 分 partition/shard** 可以把多租户场景的 filter 成本压到 0，这是 SaaS 架构的必修。

## 五、多向量与 Late Interaction

单向量（dense bi-encoder）把整段文本压成一个向量，损失大。ColBERT 把**每个 token 都存成向量**，查询时做”token 级”MaxSim：

```
score(q, d) = Σ_i max_j <q_i, d_j>
```

这叫 Late Interaction。召回率比单向量高 5~10 个点，代价是存储膨胀 20~100×。

- **ColBERT v2**：残差压缩（Residual Compression）把每个 token 向量压到 32 字节，存储可接受；
- **PLAID**：ColBERT v2 官方加速引擎，剪枝 + 质心过滤，让 late-interaction 可做到毫秒级；
- **Vespa、LanceDB、Qdrant**：原生支持 multi-vector 字段 + MaxSim；2026 年开始进入主流 RAG 管线。

## 六、Graph RAG：知识图谱归来

纯向量 RAG 的两个死穴：

1. **多跳推理弱**：问”A 公司 CEO 的母校在哪个城市”，向量检索一跳就蒙；
2. **全局问题答不好**：问”本报告讲的主要主题是什么”，向量 top-k 只能看局部。

GraphRAG 的核心思路：**用 LLM 预先把语料抽取成图（实体 + 关系）**，查询时沿图游走或用图摘要。2024 年 Microsoft GraphRAG 把这条路线带火。

### 6.1 Microsoft GraphRAG

流程（离线索引 + 在线查询）：

1. **Chunking**：切块（600~1200 token）；
2. **Entity / Relation Extraction**：对每个 chunk 调 LLM 抽三元组 `(entity, relation, entity)` + 描述；
3. **Graph Construction**：实体去重合并、关系聚合；
4. **Community Detection**：用 Leiden 算法把图划分为层次社区（Level 0 ~ Level N）；
5. **Community Summarization**：每个社区调 LLM 生成摘要；
6. **查询**：
    - _Local search_：实体出发，游走邻居 + 关联 chunk → LLM 回答；
    - _Global search_：遍历所有社区摘要，map-reduce 出答案。

![Microsoft GraphRAG](https://quant67.com/post/llm-infra/18-vector-graph/images/18-vector-graph-fig2.svg)

### 6.2 LightRAG / HippoRAG / Nano-GraphRAG

Microsoft GraphRAG 最大的痛点是**索引成本高**：对中型语料就要烧几百刀 token。社区出现一批更轻的方案：

- **LightRAG（HKU 2024）**：只抽 entity 邻接，不做社区摘要，索引成本降一个数量级，质量接近；
- **HippoRAG（UCSB 2024）**：类比海马体索引，用 PageRank 在 KG 上做检索，冷启动性能好；
- **Nano-GraphRAG**：<1000 行 Python 的极简实现，适合学习与小语料；
- **Neo4j LLM Graph Builder**：Neo4j 官方的 LLM-to-KG 流水线，图 + 向量天然融合。

### 6.3 KG + Vector 混合

工程上最务实的做法：

1. **关键实体、关系、数值**用 KG 存（Neo4j / Nebula）；
2. **大段描述、背景**用向量存（Milvus / Qdrant）；
3. 查询时**先 KG 定位实体** → **再向量拉上下文** → 给 LLM。

这对金融、医疗、法律场景特别有效，因为这些领域有**明确的 schema 和可验证的关系**。

## 七、图数据库简表

    
|产品|模型|语言|典型规模|特点|
|---|---|---|---|---|
|Neo4j|Property Graph|Cypher|单机亿级|生态最全、企业版分布式|
|NebulaGraph|Property Graph|nGQL|分布式千亿|国产、vesoft、字节在用|
|TigerGraph|Property Graph|GSQL|分布式千亿|商业、并行计算强|
|JanusGraph|Property Graph|Gremlin|分布式|基于 Cassandra/HBase|
|ArangoDB|多模（图+文档）|AQL|单机亿级|多模方便|
|Neptune|Property / RDF|Cypher/Gremlin/SPARQL|AWS 托管|兼容性广|
|GraphDB / Stardog|RDF|SPARQL|知识图谱|推理能力强|

**属性图 vs RDF**：属性图（LPG）灵活、工程友好，适合业务；RDF / SPARQL 语义严格、可推理，适合学术和本体管理。2026 年 Neo4j、Nebula 主导 LLM + 图的生产场景；RDF 主要在学术和特定行业本体里。

## 八、百亿级工程实践

### 8.1 HNSW 参数速查

|场景|M|ef_construction|ef_search|备注|
|---|---|---|---|---|
|平衡默认|16|200|64|大多数中小规模|
|高召回|32|400|128~256|金融、医疗|
|内存紧张|8|200|64|小集群|
|大规模 + PQ|16|200|64|10^9、配 IVF-PQ 粗排|
|Filter 重|32|400|128|补偿过滤掉的邻居|

### 8.2 内存 vs 磁盘决策树

```
N < 1e6        → Flat / pgvector 默认
1e6 ~ 1e7      → HNSW 全内存（默认）
1e7 ~ 1e8      → HNSW + fp16 / int8 SQ
1e8 ~ 1e9      → IVF-PQ（GPU）或 HNSW + RaBitQ
1e9 ~ 1e10+    → DiskANN / SPANN / 对象存储形态
```

### 8.3 大厂实践片段

- **字节豆包 / 抖音搜索**：自研 + Milvus 改造，百亿级 HNSW + 磁盘缓存；
- **阿里淘宝推荐**：Proxima 向量库，IVF-PQ + GPU，召回 + 排序一体；
- **百度文心**：百亿级 HNSW + 分片，多租户隔离；
- **腾讯 QQ 浏览器 / 微信搜一搜**：TencentVectorDB，HNSW + RaBitQ；
- **Pinterest**：HNSWlib 魔改，图片 embedding 百亿级；
- **Spotify**：Vespa + ScaNN，个性化推荐。

共同经验：

1. **Shard 按 tenant / 主键**，单 shard 内控制在 5000 万向量以内；
2. **热 / 温 / 冷分层**：热数据全内存 HNSW，温数据 IVF-PQ，冷数据 DiskANN on SSD / 对象存储；
3. **写入用 IVF 批量 flush，不要实时 HNSW 插入**——HNSW 写放大高；
4. **定期 compact + rebuild**，避免删除墓碑累积；
5. **recall SLO > 95%** 通常是业务合格线，低于此用户能感知。

## 九、代码示例：Milvus / Qdrant 10 行起步

### 9.1 Milvus 2.4

```
from pymilvus import MilvusClient
import numpy as np

client = MilvusClient("http://localhost:19530")
client.create_collection(
    collection_name="demo",
    dimension=768,
    metric_type="IP",
    index_type="HNSW",
    index_params={"M": 16, "efConstruction": 200},
)

docs = [{"id": i, "vector": np.random.rand(768).tolist(),
         "tag": "tech" if i % 2 == 0 else "news"} for i in range(1000)]
client.insert("demo", docs)

res = client.search(
    "demo", data=[np.random.rand(768).tolist()],
    filter='tag == "tech"', limit=5,
    search_params={"params": {"ef": 64}},
)
print(res)
```

### 9.2 Qdrant

```
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct, Filter, FieldCondition, MatchValue
import numpy as np

qc = QdrantClient("http://localhost:6333")
qc.recreate_collection("demo",
    vectors_config=VectorParams(size=768, distance=Distance.COSINE))
qc.upsert("demo", points=[
    PointStruct(id=i, vector=np.random.rand(768).tolist(),
                payload={"tag": "tech" if i % 2 == 0 else "news"})
    for i in range(1000)])

hits = qc.search("demo",
    query_vector=np.random.rand(768).tolist(),
    query_filter=Filter(must=[FieldCondition(key="tag", match=MatchValue(value="tech"))]),
    limit=5)
print(hits)
```

### 9.3 pgvector + HNSW

```
CREATE EXTENSION vector;
CREATE TABLE docs (id bigserial, content text, tag text, embedding vector(768));

CREATE INDEX ON docs USING hnsw (embedding vector_ip_ops)
  WITH (m = 16, ef_construction = 200);

SET hnsw.ef_search = 64;
SELECT id, content FROM docs
WHERE tag = 'tech'
ORDER BY embedding <#> $1
LIMIT 10;
```

### 9.4 Neo4j + GraphRAG 最小示例

```
from neo4j import GraphDatabase
drv = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "pass"))

with drv.session() as s:
    s.run("""
    MERGE (a:Person {name:$a})
    MERGE (b:Company {name:$b})
    MERGE (a)-[:CEO_OF]->(b)
    """, a="Jensen Huang", b="NVIDIA")

    rec = s.run("""
    MATCH (p:Person)-[:CEO_OF]->(c:Company {name:$c})
    RETURN p.name AS ceo
    """, c="NVIDIA").single()
    print(rec["ceo"])
```

真实 GraphRAG 工程里用 LangChain `LLMGraphTransformer` 或 Microsoft graphrag 包做自动抽取。

## 十、趋势与落地建议

2026 年向量 + 图 RAG 领域的几条趋势线：

1. **Serverless / 对象存储化**：Pinecone Serverless、Turbopuffer、LanceDB、pgvectorscale 把”向量库”变成按查询计费的服务，成本下降一个数量级；
2. **二值化与 RaBitQ 普及**：32× 压缩几乎无损召回，百亿级上线门槛大幅降低；
3. **Late Interaction 回潮**：ColBERT v2 / PLAID / Vespa multi-vector 成为精排标配；
4. **Filtered ANN 成熟**：多租户 SaaS 的基石，Qdrant、Milvus 持续优化；
5. **GraphRAG 工程化**：LightRAG、Nano-GraphRAG、Neo4j LLM Graph Builder 降低准入；KG + 向量混合在金融、医疗、法律场景起量；
6. **一体化数据库加码向量**：OceanBase、TiDB、PolarDB、Postgres、Elasticsearch 都有原生向量，中小规模不再需要独立向量库；
7. **国产替代成熟**：Milvus / Zilliz、TencentVectorDB、DashVector 进入头部互联网生产；
8. **幻觉缓解**：GraphRAG 对全局问答、多跳问答的事实准确率相对纯向量 RAG 提升 10~30 个点，是缓解幻觉的有效工程手段。

**落地建议的一句话版本**：

- <1 亿向量、业务简单：**pgvector / pgvectorscale**，一套 Postgres 搞定；
- 1 亿~10 亿、需要 hybrid / filter / 多租户：**Milvus 或 Qdrant**；
- 10 亿+、预算敏感：**DiskANN / SPANN / Turbopuffer / Pinecone Serverless**；
- 多跳、全局问答、合规：**GraphRAG + Neo4j / Nebula**，与向量库并行；
- 云上无运维：直接上 **Zilliz Cloud / Qdrant Cloud / Pinecone / DashVector**。

## 十一、深入：算法与工程细节补遗

前面给了速查表，这一节把几个工程里经常踩坑、面试也常问的点讲透。

### 11.1 距离度量的选择

- **L2（欧式距离）**：几何直观，图像 embedding 常用；
- **IP（内积）**：和 cosine 在 L2 归一化后等价，**大模型 embedding 首选**；
- **Cosine**：等价于先归一化再 IP，很多向量库会自动帮你归一化；
- **Hamming**：二值向量（BQ / RaBitQ 粗排）用，XOR + popcnt，硬件友好。

一个常见坑：**同一个库不能混用不同 metric**。BGE 官方推荐 cosine，但如果你用 L2 存、查询时用 cosine，结果会完全错。插入前务必 `x = x / ||x||` 归一化一次，然后整库统一 IP。

### 11.2 HNSW 的图退化问题

HNSW 的图质量在**大量删除 + 插入**后会退化。典型症状是：召回率随时间漂移、P99 延迟慢慢变大。原因是：

1. 删除只打墓碑（soft delete），图结构不变，邻居仍指向”幽灵节点”；
2. 插入时新节点的邻居选择基于当前图，墓碑越多图越偏；
3. 热点节点的邻居列表长期没更新。

工程上两类对策：

- **周期性 compact + rebuild**：Milvus 的 compaction、Qdrant 的 optimize、pgvector 的 `REINDEX`。按业务节奏每周或每月跑一次；
- **版本化 segment**：Milvus 用 segment 模型，新写进新 segment，老 segment 冻结不改，定期合并。这种设计从根本上回避了”原地改图”的退化。

### 11.3 IVF 的训练陷阱

IVF 的质心来自 k-means 训练，训练集的分布决定了索引质量。两个常见错误：

1. **训练集太小**：不到 `nlist × 39`，质心不稳，召回波动；
2. **训练集偏态**：只用某一天/某一类样本训练，质心严重偏离全库。

解决：用**全库的分层采样**（按 tenant、时间、类别）做训练集，至少 `nlist × 50` 个样本。生产环境强烈建议每季度重训一次。

### 11.4 PQ 段数 m 与精度

PQ 把 d 维切 m 段，每段用 256 个质心（1 byte）。m 越大压缩率越低但召回越高：

|d|m|压缩率|召回相对 Flat|
|---|---|---|---|
|768|48|64×|80~85%|
|768|96|32×|88~92%|
|768|192|16×|92~95%|
|1536|96|64×|82~88%|
|1536|192|32×|88~93%|

经验公式：`m ≈ d / 8`，再根据召回微调。维度必须能被 m 整除，且 d/m 不宜 < 4，否则每段信息太少。

### 11.5 SIMD 与硬件亲和

HNSW / IVF 的热点是**大量的点积或 L2 距离**，SIMD 化收益极大：

- **AVX2**：fp32 × 8 lane，基础版 HNSW 库都支持；
- **AVX-512 / VNNI**：fp32 × 16 lane，int8 dot 加速；
- **ARM NEON / SVE**：鲲鹏、倚天、Graviton 上的对应实现；
- **GPU**：IVF-PQ 非常适合 GPU，Milvus GPU、NVIDIA RAFT / cuVS 在 H100 上能打满 3 TB/s HBM 带宽。

Qdrant 的 Rust 实现、hnswlib 的 C++ SIMD 模板，是开源里 SIMD 写得最彻底的两个项目，值得读。

### 11.6 Filtered ANN 的代价曲线

Filtered ANN 的性能强依赖过滤选择率 s（通过过滤的比例）：

```
s ≈ 1.0   → 等价于无过滤，HNSW 最优
s ≈ 0.1   → 图遍历 2~3× 减速，可接受
s ≈ 0.01  → 图遍历 10× 减速，建议切换 pre-filter
s ≈ 0.001 → 改用倒排 + 暴力
s < 1e-5  → 退化到 OLTP 等值查询，直接用 B+Tree
```

所以生产里常见的做法是**基于选择率的自适应路由**：查询规划器估算选择率，动态选 pre-filter / filtered HNSW / post-filter。Qdrant 和 Vespa 都有这个优化。

### 11.7 Embedding 漂移与灰度

模型升级换 embedding（例如从 BGE-v1 升到 BGE-M3），旧索引全部作废。工程上两种做法：

1. **双写双查 + 灰度**：新旧两套索引并存，按流量比例灰度切换；
2. **Adapter 层**：在 embedding 上加可训练的投影层，新模型输出投影回旧空间。代价是精度略降。

SaaS 向量库（Pinecone、Zilliz）一般提供 namespace / alias 切换，业务侧只改一个 alias 指向。

### 12.1 抽取质量：schema-guided 比 free-form 好

Microsoft GraphRAG 默认让 LLM free-form 抽取实体与关系，质量参差。生产里强烈建议 **schema-guided**：预定义实体类型和关系类型，LLM 只能在给定集合里填。

```
SCHEMA = {
    "entities": ["Person", "Company", "Product", "Location", "Event"],
    "relations": ["CEO_OF", "SUBSIDIARY_OF", "LOCATED_IN", "FOUNDED", "PARTNERED_WITH"],
}
prompt = f"""只在下列类型中抽取三元组，其它忽略。
Entities: {SCHEMA['entities']}
Relations: {SCHEMA['relations']}
Text: {chunk}
输出 JSON：[[{{"head":..,"type":..}},"REL",{{"tail":..,"type":..}}],...]
"""
```

金融、医疗、合规场景基本都要 schema-guided，否则后续查询无法对得上。

### 12.2 实体消歧

同一实体不同写法（“OpenAI”、“Open AI”、“OpenAI Inc.”）必须合并，否则图碎成粉。典型链路：

1. **表面形式归一化**：大小写、空格、标点；
2. **embedding 相似度**：cosine > 0.95 的候选合并；
3. **LLM 判断**：边界样本让 LLM 判断”是否同一实体”；
4. **KG linking**：链接到 Wikidata / DBpedia 等外部 KG。

Neo4j 的 `APOC` 库、LightRAG 里都内置了实体合并流水线。

### 12.3 社区检测算法

GraphRAG 用 Leiden（Louvain 的改进版），对稀疏图效果好。其它常用：

- **Louvain**：经典，快，但可能产生”不连通”社区；
- **Leiden**：解决了 Louvain 的连通性问题，Microsoft GraphRAG 默认；
- **Label Propagation**：超快，质量略差，适合十亿节点；
- **Infomap**：基于信息论，学术圈流行。

社区层级数（Level）通常 3~5 层合理：Level 0 最细（几十节点一组），Level N 最粗（整图几大板块）。

### 12.4 查询策略组合

Microsoft 后续在 GraphRAG 里又加了 **DRIFT search**：

1. 用 query 匹配社区摘要（global 思路）找到相关社区；
2. 在这些社区里做 local 游走；
3. 合并证据给 LLM。

实测在多数场景比单纯 local 或 global 好。生产里建议按 query 类型路由：

- **事实型查询**（“谁是 NVIDIA 的 CEO”）→ Local；
- **总结型查询**（“本季度报告的主要主题”）→ Global；
- **多跳推理**（“X 的供应商在哪些国家上市”）→ DRIFT 或显式图游走。

### 12.5 成本

对 100 万 token 语料（约 1500 页 PDF）做一次完整 GraphRAG 索引：

- 实体关系抽取：~ 1.5× 原 token（prompt + output），用 GPT-4o-mini 约 $30~50；
- 社区摘要：~ 0.2× 原 token，约 $5~10；
- 嵌入：~ $0.1；
- 总计 $40~60，耗时 1~3 小时。

对比纯向量 RAG（嵌入 ~ $0.1），贵了 500×。所以别对所有语料都跑 GraphRAG，**只对高价值、多跳、全局问答需求的语料用**。LightRAG 把成本压到 1/5~1/10，是中间折中。

## 十三、RAG 评测与监控

向量库选型离不开评测。关键指标：

- **[Recall@k](mailto:Recall@k)**：召回 top-k 中真正相关的比例（需要 ground-truth）；
- **[nDCG@k](mailto:nDCG@k)**：带排序的相关性；
- **QPS / P50 / P99**：压测指标；
- **内存 / 磁盘占用**：成本相关；
- **写入吞吐**：实时系统关键；
- **Recall 漂移**：长期运行后的召回变化。

开源工具：

- **ann-benchmarks**：学术 benchmark 大全，覆盖几乎所有索引算法；
- **BEIR**：IR 评测集，13 个数据集、多语言；
- **MTEB**：embedding 模型评测；
- **RAGAS**、**TruLens**：端到端 RAG 评测（召回 + 回答质量）。

生产监控建议：

1. 线上开 1% 影子流量跑 Flat 基线，算实时 recall；
2. 采样问答日志送人工 / LLM 评审，算答案质量；
3. P99 延迟、写入 backlog、segment 数、碎片率都上 Prometheus；
4. Embedding 模型 A/B 分流：灰度 10% 流量走新模型 + 新索引，评测后全量。

### 13.1 评测集构建

搭自己的评测集比借 BEIR 更重要，流程：

1. 从线上随机采样 500~2000 条真实 query；
2. 对每条 query 用 Flat 跑 top-100 作为候选；
3. 人工或强 LLM（GPT-4o / Claude）标注相关性（0/1 或 0~3 分）；
4. 按时间滚动更新，每月加新样本。

有了这份评测集后，换 embedding、换索引、调参数都能量化评估，不再靠拍脑袋。

### 13.2 线上 / 线下一致性

经常见到的坑：离线评测 recall 95%，上线后用户反馈”搜不到”。常见原因：

- **query 分布漂移**：评测集用的历史 query，实际线上 query 分布不同；
- **tokenizer 不一致**：embedding 服务和索引用了不同 tokenizer；
- **filter 差异**：线下评测没带 filter，线上带，选择率低导致召回降；
- **冷启动**：新上架内容没被评测集覆盖。

解决：线上线下用**同一份** embedding 服务与 filter 逻辑，评测集覆盖各 tenant / 各时间段。

## 十四、一个完整案例：金融研报 RAG

最后给一个端到端的示例，串联本文所讲。

**场景**：证券公司研报库，50 万份 PDF、2 亿中文 token、每天新增 500 份。需要：

1. 相似研报检索（向量）；
2. 按公司、行业、日期过滤（filter）；
3. 回答”某公司最近的供应链风险”（向量 + 多跳）；
4. 回答”本季度半导体板块主要主题”（全局总结）。

**架构**：

```
              ┌─────────────┐
   PDF ──▶ 解析 + chunk ──▶ │  Embedding  │──▶ Milvus（HNSW + filter）
                            │  BGE-M3     │        │
                            └─────────────┘        │
              ┌─────────────┐                      │
              │  LLM 抽取    │──▶ Neo4j（实体图）─┐ │
              └─────────────┘                    │ │
              ┌─────────────┐                    │ │
              │  社区摘要    │──▶ Milvus 社区集合 │ │
              └─────────────┘                    ▼ ▼
                                          Query Router
                                                │
                           ┌────────────────────┼─────────────────────┐
                           ▼                    ▼                     ▼
                      事实查询              多跳查询              全局总结
                     (Local GraphRAG)     (DRIFT)             (Global GraphRAG)
```

**关键参数**：

- Milvus collection：HNSW，M=32，ef_construction=400，ef_search=128；按 `industry` partition；
- 过滤字段：`company`、`industry`、`date`，全部建 scalar index；
- Neo4j：约 100 万实体、500 万关系；Leiden 4 层社区；
- 压缩：BGE-M3 1024 维 + int8 SQ，压缩 4×；
- 更新节奏：向量实时写入；图每天凌晨增量抽取 + 每周重新社区检测。

**成本（估算）**：

- Milvus 集群：3 节点 × 128 GB 内存 × 2 TB NVMe，云上 ~ ¥15k/月；
- Neo4j：单机 Enterprise ¥8k/月；
- Embedding + 抽取：初次 ~ ¥5 万，日增 ~ ¥200/天；
- LLM 问答：按量，~ ¥100/日/千问答。

**效果**（某真实券商案例匿名化数据）：

- 研报召回 [Recall@10](mailto:Recall@10) 从纯 BM25 的 72% 提升到 hybrid 的 91%；
- 全局总结类问答事实准确率从 58%（纯向量 RAG）提升到 83%（GraphRAG）；
- P99 延迟 < 400 ms（含 LLM 生成）。

这个配方可以直接迁到医疗、法律、咨询等知识密集行业。核心思路不变：**向量管相似、图管关系、LLM 管理解与生成**。

### 14.1 实施路线建议

上线一个类似系统，建议按下面的阶段推进，避免一次性上齐导致难以收敛：

1. **Week 0~2**：只上纯向量 RAG（pgvector / Milvus 都行），打通 ingest → 嵌入 → 检索 → 生成；
2. **Week 3~4**：加 BM25 / SPLADE 和 RRF 融合，召回基线拉起来；
3. **Week 5~6**：加 filter（公司、行业、日期），多租户隔离；
4. **Week 7~10**：评测发现多跳 / 全局问答差 → 上 GraphRAG 或 LightRAG；
5. **Week 11~12**：监控、A/B、灰度新 embedding；
6. **Week 13+**：成本优化：量化 / DiskANN / serverless 迁移。

不要在 Week 0 就把 GraphRAG、多模态、Late Interaction 全上，**工程复杂度会吞掉所有精力，也很难定位问题到底在哪一层**。

### 14.2 失败模式总结

同类项目失败的常见原因：

- **Chunk 策略错**：按字符硬切，切碎了语义，召回永远上不去。正解是按段落 / 小节切，配合滑动窗口；
- **embedding 模型选错**：中文场景硬用 OpenAI text-embedding-3-small，召回差 10+ 个点。中文优先 BGE / M3E / Qwen3-Embedding；
- **没做 reranker**：top-50 召回对了，但没精排，给 LLM 的 top-5 是噪声；
- **GraphRAG 语料没筛**：把所有文档都扔进去抽图，烧了几千刀 token，结果全局问答并没变好。GraphRAG 只对有多跳结构的语料有用；
- **监控盲区**：只看延迟和 QPS，不看 recall，问题爆发时已经积累几周。

## 十五、补充：更多算法细节与基准

### 15.1 ANN-Benchmarks Pareto 前沿

在标准 sift-1M、glove-100、deep-1M 数据集上，2025 年的 Pareto 前沿大致长这样（recall 90%+ 下的 QPS，单核）：

|算法|sift-1M QPS|glove-100 QPS|备注|
|---|---|---|---|
|hnswlib|~20000|~8000|社区基准|
|Qdrant HNSW|~18000|~7500|Rust 实现|
|Milvus HNSW|~15000|~6500|有一层服务化开销|
|Vamana / DiskANN 全内存|~14000|~6000|图略好但慢|
|ScaNN|~25000|~12000|学术 SOTA|
|Weaviate|~10000|~4500|Go 实现|
|pgvector HNSW|~8000|~3000|带 PG 开销|
|Faiss IVF-PQ|~12000|~5000|CPU，GPU 更快|

需要注意：**单核 benchmark 不等于生产性能**。生产里 P99、filter、并发、写入混合、冷热分层才是主题。

### 15.2 学习到的索引（Learned Index）

2023—2025 年学术界探索**用神经网络替代 k-means 质心或图结构**：

- **Neural LSH**：NN 学哈希函数；
- **DeepPQ**：NN 端到端学 PQ 码本；
- **BLISS**、**DESSERT**：学稀疏签名代替向量。

工业落地不多，原因是 HNSW / IVF-PQ 已经非常强，Learned Index 的增益在 5% 以内但引入模型维护复杂度。值得关注，但短期不会替代。

### 15.3 稀疏检索的变迁

稀疏检索从 BM25 走到 SPLADE，背后有几代演进：

- **BM25**（1994）：词频 + 逆文档频率 + 长度归一化，至今仍是稀疏 baseline；
- **doc2query / docTTTTTquery**：用 seq2seq 为文档生成扩展 query，拓展词汇匹配；
- **DeepImpact、uniCOIL**：在 BERT 上学 term 权重；
- **SPLADE v2 / v3**：学习到的稀疏表示，MRR 接近稠密，稀疏度可控；
- **LexMAE、SparseEmbed**：2024 年更强的稀疏预训练。

生产建议：BM25 + 稠密两路 RRF 是最低成本的 hybrid；对质量要求高可加一路 SPLADE。

### 15.4 向量库的一致性与可用性

向量库作为有状态系统，CAP 取舍非常现实：

- **Milvus**：基于 Pulsar / etcd，最终一致；写入到可见有秒级延迟；
- **Qdrant**：Raft 强一致；
- **Weaviate**：可配，一致性级别 ONE/QUORUM/ALL；
- **Vespa**：文档组内强一致；
- **pgvector**：继承 Postgres MVCC，最强；
- **Pinecone**：托管，对外承诺”秒级可见”。

对高写入场景（日志型、IM 型），**最终一致 + WAL** 的设计更合理；对金融、医疗等一致性要求高的，**pgvector 或 OceanBase Vector** 可能更合适。

## 十六、易踩坑清单与排错手册

工程里遇到过的典型问题，汇总成表方便排查：

  
|症状|可能原因|排查手段|
|---|---|---|
|召回骤降|删除墓碑累积 / segment 碎片|compact、观察 segment 数|
|P99 突增|ef_search 太大 / 过滤选择率低|调 ef_search、查选择率|
|内存 OOM|HNSW M 过大 / 未量化|降 M、加量化、分 shard|
|写入 backlog|HNSW 实时插入 / segment 未 flush|改批量写、加 flush 频率|
|查询结果错乱|metric 不一致 / 未归一化|统一 metric、插入前归一化|
|多租户泄漏|filter 漏写 / partition 未生效|强制 partition key、审计|
|升级 embedding 召回崩|新旧索引未切换|双写双查 + 灰度|
|GraphRAG 实体爆炸|free-form 抽取 / 未消歧|加 schema、加消歧流水线|
|社区摘要答非所问|社区过大 / 层级过浅|调 Leiden 参数、加层|
|成本飞起|全量 GraphRAG / 密集 ef_search|精选语料、调 ef|
|查询结果乱序|未归一化 + IP 度量|归一化 / 改 cosine|
|冷启动召回低|训练样本不足|补样本、重训 IVF|
|多语言召回差|单语模型|换 BGE-M3 / multilingual-e5|

### 16.1 一个真实事故复盘

某电商的商品检索库，某天突然 P99 延迟从 80 ms 飙到 800 ms，召回率也降到 78%。排查步骤：

1. **查 metrics**：QPS 没变、内存没变、segment 数从 30 涨到 210；
2. **查写入日志**：过去一周新上了”分钟级商品状态同步”，每条商品每小时更新一次 → 删除 + 重新插入；
3. **查删除比例**：soft delete 率 45%，幽灵节点占图一半；
4. **临时手段**：强制 compact，P99 回到 120 ms；
5. **根因**：HNSW 图质量随频繁 upsert 退化；
6. **长期方案**：改”变更字段独立存 KV”，向量不变就不重插，只有 embedding 变的商品才更新向量。

教训：**HNSW 最怕高频 upsert**。如果业务要求高频更新 payload 但 embedding 稳定，把 payload 和向量分离存储是正解。

### 16.2 黄金法则

1. **先基准后上线**：生产环境上线前必须跑 ann-benchmarks 风格的召回 / QPS 压测；
2. **离线 ground-truth 不可省**：用 Flat 跑 top-100 当 ground-truth，线上索引和它对比；
3. **灰度 + 影子**：新索引上线用影子流量跑 1~2 周再切；
4. **监控 recall，不仅仅是 QPS**：QPS 好看不代表结果对；
5. **预留 compact 窗口**：系统设计时就要把定期 compact / rebuild 当作一等公民。

## 十七、进阶主题：多模态与时空向量

### 17.1 多模态检索

CLIP、SigLIP、BLIP、Qwen2-VL、InternVL 等跨模态模型产出的向量可以直接塞进同一个向量库，实现”文搜图、图搜图、图搜文”：

- 统一嵌入空间：CLIP 512~768 维，SigLIP 1024 维；
- 存储与纯文本向量相同，metric 用 cosine；
- 查询侧：文字 query → text encoder → 向量 → ANN；图片 query → image encoder → 向量 → ANN。

工程坑：**不同模态的向量分布方差不一致**，直接混在同一 index 里，文搜文容易被图干扰。解决：按 modality 分 partition，或者用带 modality 字段的 filtered ANN。

### 17.2 视频与时空向量

视频检索常把视频切成 shot 或 2 秒 clip，对每 clip 出一个向量。问题是**一个视频产生上百向量**，库规模膨胀百倍。常见优化：

- **关键帧 + 补偿**：每 shot 只存 1~3 个关键帧向量；
- **层次向量**：一个视频一个粗向量（整体摘要）+ N 个细向量（clip 级），粗筛再精排；
- **时序 attention pooling**：把 clip 序列压成一个时序向量，召回时用 MaxSim。

快手、YouTube、TikTok 内部的视频检索都是这种层次化架构。

### 17.3 地理 / 时间混合

推荐、LBS 场景会把地理位置、时间和语义向量一起检索。三类做法：

1. **编码进 vector**：把经纬度 / 时间戳做傅里叶编码拼到 embedding；
2. **多路召回融合**：语义 ANN + 地理 R-Tree + 时间 B+Tree 分别召回后融合；
3. **Hybrid Score**：`score = α·sim + β·exp(-d/σ) + γ·exp(-|t|/τ)`。

Vespa、Elastic、Milvus 都支持这种 hybrid scoring。

## 十八、开源选型决策树

```
你的规模?
├── <100 万：Chroma / pgvector / LanceDB（笔记本 / 小业务）
├── 100 万~1 亿：
│   ├── 已用 Postgres？→ pgvector + pgvectorscale
│   ├── 需要 hybrid / filter？→ Qdrant / Milvus / Weaviate
│   └── 已用 ES？→ Elasticsearch / OpenSearch
├── 1 亿~10 亿：
│   ├── 自建：Milvus / Qdrant（配 PQ 或 RaBitQ）
│   ├── 云上：Zilliz / Qdrant Cloud / Pinecone / DashVector
│   └── 强 OLAP 需求：StarRocks Vector / Vespa
└── 10 亿+：
    ├── 极致成本：DiskANN / SPANN / Turbopuffer / LanceDB on S3
    ├── 百度级延迟：Milvus + GPU + 分层存储
    └── 国内合规：OceanBase / TiDB / TencentVectorDB

是否多跳 / 全局问答?
├── 不需要 → 纯向量即可
├── 少量高价值语料 → LightRAG / Nano-GraphRAG
└── 生产级知识库 → Microsoft GraphRAG / Neo4j + 向量库

是否多模态?
├── 纯文本 → BGE-M3 / text-embedding-3
├── 图文 → SigLIP / Qwen2-VL + 向量库
└── 视频 → 层次向量 + Vespa 或自建
```

## 十九、与前后章的联动

- **第 17 篇（RAG 工程全景）**：讲 RAG 的端到端链路。本篇是其中”检索”一环的深化；
- **第 19 篇（Agent 框架）**：Agent 的记忆与工具调用会大量依赖向量库与 KG；
- **第 21 篇（推理服务化）**：向量库经常和 LLM 服务部署在同一集群，调度与 QoS 协同；
- **第 23 篇（可观测性）**：recall、P99、embedding 漂移都是可观测指标；
- **第 24 篇（成本、合规）**：向量化多租户隔离、数据脱敏、合规删除（GDPR 被遗忘权）在向量库里实现代价不低，需要专门设计。

## 二十、一句话总结

**向量库是 LLM 时代的”数据库”，图 RAG 是它的”多跳拓展”。选型先看规模与成本，再看 filter 与 hybrid 需求，最后看是否需要多跳与全局问答——用对工具比堆参数重要得多。**

如果只能记三条：

1. **HNSW 是默认选择**，M=16、ef_construction=200、ef_search=64 起步；
2. **过亿量级必须考虑量化**（SQ / PQ / RaBitQ）或 **DiskANN / 对象存储**形态；
3. **多跳 / 全局问答才上 GraphRAG**，且要做 schema 约束和实体消歧，否则烧钱又不准。

剩下所有事情——hybrid、filter、multi-vector、多模态——都是在这三条基础上的增量优化。保持”能回到最简基线”的心态，比追最新算法重要得多。

## 参考资料

- Malkov & Yashunin, Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs, 2016.
- Jégou et al., Product Quantization for Nearest Neighbor Search, 2011.
- Jayaram Subramanya et al., DiskANN: Fast Accurate Billion-point Nearest Neighbor Search on a Single Node, NeurIPS 2019.
- Chen et al., SPANN: Highly-efficient Billion-scale Approximate Nearest Neighbor Search, NeurIPS 2021.
- Guo et al., Accelerating Large-Scale Inference with Anisotropic Vector Quantization (ScaNN), ICML 2020.
- Gao & Long, RaBitQ: Quantizing High-Dimensional Vectors with a Theoretical Error Bound, SIGMOD 2024.
- Khattab & Zaharia, ColBERT / ColBERT v2 / PLAID.
- Microsoft Research, GraphRAG: From Local to Global, 2024.
- Guo et al., LightRAG: Simple and Fast Retrieval-Augmented Generation, 2024.
- HippoRAG: Neurobiologically Inspired Long-Term Memory for LLMs, 2024.
- Milvus / Qdrant / Weaviate / pgvector / Neo4j 官方文档。
- Douze et al., The Faiss Library, 2024.
- Neo4j LLM Graph Builder 官方博客。
- Turbopuffer、Pinecone Serverless、pgvectorscale 工程博客。
- Qdrant、Milvus 关于 Filtered HNSW 的工程笔记。
- BEIR、MTEB、RAGAS 项目 README。
- 腾讯、字节、阿里、百度在 QCon / CommunityOverCode / VLDB 上关于向量库的公开分享。
- Anthropic、OpenAI、Google 关于 long-context 与 hybrid retrieval 的官方文档。
- HKU LightRAG、UCSB HippoRAG、Nano-GraphRAG 的开源仓库与论文。
- 中国信通院《向量数据库技术与产业发展报告》2024 / 2025。

---

**上一篇**：[RAG 工程全景](https://quant67.com/post/llm-infra/17-rag-engineering/17-rag-engineering.html) **下一篇**：[Agent 框架工程](https://quant67.com/post/llm-infra/19-agent-framework/19-agent-framework.html)

## 同主题继续阅读

把当前热点继续串成多页阅读，而不是停在单篇消费。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】17：RAG 工程全景](https://quant67.com/post/llm-infra/17-rag-engineering/17-rag-engineering.html)

从文档解析、切片、嵌入、索引、检索、重排到生成与评估，系统梳理 RAG 的工程流水线、进阶范式与国内外生态

2026-04-22 · architecture / ai-infra

### [大模型基础设施工程](https://quant67.com/post/llm-infra/index.html)

面向中国工程团队的大模型基础设施系列。从 GPU/CUDA/互联、训练框架与 3D 并行、vLLM/SGLang 推理引擎、量化与推测解码、RAG/Agent 到服务化、网关、可观测性与安全合规，覆盖 LLMOps 全链路。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】11：推理引擎基础](https://quant67.com/post/llm-infra/11-inference-basics/11-inference-basics.html)

从 Prefill/Decode 两阶段、KV Cache、Continuous Batching 到 PD 分离，系统讲清楚大模型推理的工程基础。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】09：RLHF 与对齐流水线](https://quant67.com/post/llm-infra/09-rlhf-pipeline/09-rlhf-pipeline.html)

从 SFT、奖励模型到 PPO、DPO、GRPO 的完整对齐流水线工程实践，覆盖 OpenAI o1、DeepSeek-R1 等推理模型的 RL 路线与主流框架选型。