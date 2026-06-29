---
title: SAG（SQL检索增强生成）
category: concepts
tags: [AI, RAG, SAG, SQL, Hyperedge, 多跳检索]
aliases: [SAG, SQL-RAG, SQL检索增强生成]
summary: SAG用SQL+向量混合检索替代GraphRAG的全局图构建——查询时用SQL join临时激活局部Hyperedge结构，避免全局图维护成本，多跳Recall@5达80%
source_dir: AI 人工智能/AI Agent/RAG/高级RAG/SAG
source_files: [SAG 核心思路介绍（利用SQL构建查询时的Hyperedge超边）.md, Zleap技术解密：后RAG时代已来，SAG重新定义AI搜索.md]
provenance:
  extracted: 0.60
  inferred: 0.35
  ambiguous: 0.05
base_confidence: 0.70
lifecycle: draft
lifecycle_changed: 2026-06-22
tier: supporting
created: 2026-06-22
updated: 2026-06-22
relationships:
  - target: "[[concepts/graphrag-engineering]]"
    type: related_to
  - target: "[[concepts/rag-engineering]]"
    type: extends
  - target: "[[concepts/rag-storage-technology]]"
    type: uses
---

# SAG（SQL检索增强生成）

SAG（SQL-Retrieval Augmented Generation）是Zleap AI提出的一种RAG新范式，核心思路：**把GraphRAG中最重的部分——全局图构建和维护——改为查询时用SQL join临时激活局部结构**。用MySQL做结构化存储，Elasticsearch做全文和向量检索；新数据来了append event/entity记录即可，不需要重建全局图。

## 核心设计：三层架构

### 1. Event-Entity Index（数据准备层）

普通GraphRAG把文本拆成三元组（谁—做了什么—对象），语义容易被拆碎。SAG反其道而行：

- **Event**：把每个chunk总结为一个原子事件，保留完整语义
- **Entity**：从event中抽出多维度实体（time/location/person/organization/topic/product/action/metric/label等）
- **自然语言向量**：Entity属性作为维度，属性值作为维度的值——类似向量但用自然语言而非数字表达 ^[inferred]

一个event连着多个entity，本质上是一条隐含的**超边（Hyperedge）**——多个实体共享同一个事件。

### 2. Seed Retrieval（双路入口）

查询来了，SAG分两路找入口：

| 入路 | 机制 | 优势 | 短板 |
|------|------|------|------|
| **结构入口** | LLM从query抽seed entities → entity vector expansion → SQL join找关联events | 更懂结构关系 | 可能漏掉隐含语义 |
| **语义入口** | query vector直接检索event index中语义相似的events | 语义兜底 | 缺乏多跳链路 |

两路合并形成初始candidate event set。**SQL负责结构入口，向量负责语义兜底**——二者互补而非对立。

### 3. Query-Time Dynamic Hyperedges（核心创新）

传统GraphRAG提前建好全局图（节点、边、社区结构都预计算）。SAG反过来：

- 取seed events → 反向SQL join找关联frontier entities
- 用frontier entities继续join找新events
- 最多扩展H hops（论文默认H=1）
- 检索结束后，这个局部结构就结束——**不提前枚举全局超边**

**本质**：围绕当前问题在数据库里join出一片局部关系网，查询结束不保留。

论文实验证明expansion的价值：MuSiQue Recall@5从69.4→80.0，不是装饰而是把断开证据链链接起来的关键。

## 输出合并

两路输出：
- **结构路径**：candidates粗排到Kcand=100 → LLM rerank → Kevent=5个最相关events → 映射回原始chunk
- **语义路径**：query vector直接检索Kdirect=5个chunks

结构路径负责多跳证据链，语义路径负责直接命中原文。两路合并既不完全依赖图结构，也不退回纯向量检索。

纯语义路径MuSiQue Recall@5=56.2；加入5个event-derived candidates后达到80.0——event路径真正补上了结构能力。

## 实验结果

在HotpotQA、2WikiMultiHopQA、MuSiQue三个多跳问答基准上：

| 方法 | 平均Recall@2 | 平均Recall@5 | MuSiQue Recall@5 |
|------|-------------|-------------|-------------------|
| SAG | 79.3% | 88.2% | 80.0 |
| HippoRAG 2 | 68.2% | 83.3% | 65.1 |

SAG在9个Recall@K指标中拿到8个最好。Event-level hyperedge版本优于triple-decomposition（80.0 vs 77.1）——多跳问答需要完整事件上下文，过早拆成三元组会丢语义。

## 与GraphRAG对比

| 维度 | GraphRAG | SAG |
|------|----------|-----|
| 索引方式 | 全局图（提前建好） | Event-Entity表（增量append） |
| 检索方式 | 图遍历/社区查询 | SQL join临时激活局部Hyperedge |
| 更新成本 | 增量数据需重建图 | 仅append新event/entity记录 |
| 多跳能力 | 全图传播 | H hops局部扩展 |
| LLM参与 | 索引阶段大量调用 | 仅在rerank环节 |
| 数据存储 | 图数据库 | MySQL + Elasticsearch |

**核心差异**：GraphRAG问"图怎么建得更大"，SAG问"哪些结构可以查询时再临时生成"。

## 应用方向

- **企业决策助手**：唤醒沉睡历史数据，实时连接最新业务数据
- **通用数据处理引擎**：重构企业所有非结构化数据（电商推荐/金融风控/广告投放）
- **个人知识库底座**：笔记、文档变成可检索可关联的知识体系
- **Agent记忆基座**：为Agent提供更精准的上下文（替代grep正则匹配的粗糙检索）
- **低成本AI转型**：小模型异步处理+夜间闲置算力，甚至可离线运行在手机上 ^[inferred]

## 未解问题

- 论文默认H=1，更深hop扩展的效果和成本权衡尚不明确 ^[inferred]
- MySQL作为结构化存储在超大规模场景的性能瓶颈未知 ^[ambiguous]
- Zleap的商业推广声明（"后RAG时代"）与论文实验严谨性之间有张力 ^[ambiguous]

## 来源

- `raw/sources/AI 人工智能/AI Agent/RAG/高级RAG/SAG/SAG 核心思路介绍（利用SQL构建查询时的Hyperedge超边）.md` — 论文深度解读
- `raw/sources/AI 人工智能/AI Agent/RAG/高级RAG/SAG/Zleap技术解密：后RAG时代已来，SAG重新定义AI搜索.md` — CEO视角的产品与技术介绍
- [[concepts/graphrag-engineering]] — GraphRAG工程（SAG的替代对象）
- [[concepts/rag-engineering]] — RAG工程全景（SAG的演进方向）
