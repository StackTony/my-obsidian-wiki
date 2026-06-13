---
title: GraphRAG工程
category: concepts
tags: [AI, RAG, 知识图谱, GraphRAG, 社区检测]
aliases: [GraphRAG, 图检索增强生成]
summary: GraphRAG用知识图谱解决传统RAG的全局型问题：实体→关系→社区摘要→全局/局部/DRIFT三种搜索模式，代价是LLM调用量大和索引成本高
source_dir: AI 人工智能/Agent架构/RAG/高级RAG/GraphRAG
source_files: [GraphRAG微软源代码理解.md, GraphRAG详解.md, GraphRAG开源生态全景-6大项目PK.md, GraphRAG设计解读.md, GraphRAG原理及部署实战-博客园.md, GraphRAG知识图谱全流程解析.md]
provenance:
  extracted: 0.65
  inferred: 0.30
  ambiguous: 0.05
base_confidence: 0.85
lifecycle: draft
lifecycle_changed: 2026-06-13
tier: core
created: 2026-06-13
updated: 2026-06-13
relationships:
  - target: "[[concepts/rag-engineering]]"
    type: extends
  - target: "[[entities/graphify-gitnexus]]"
    type: related_to
  - target: "[[concepts/agent-framework-engineering]]"
    type: uses
  - target: "[[concepts/rag-chunking-strategies]]"
    type: uses
---

# GraphRAG工程

传统RAG擅长局部型问题（"XX参数怎么设置？"），但在全局型问题上力不从心（"所有文档的核心主题是什么？"）。GraphRAG通过构建知识图谱+社区摘要，为全局型、综述型、多跳型问题提供答案。代价是LLM调用量大、索引成本高、更新困难。

## 传统RAG的失败点

蚂蚁集团设计解读列出了传统RAG的7个典型失败场景：
1. **多跳推理断裂**：答案分散在不同文档，需跨文档关联推理
2. **全局型问题失能**：无法回答"所有数据的核心趋势是什么"
3. **语义鸿沟**：查询表述与文档表述不完全匹配
4. **结构化信息丢失**：表格、代码、层级结构被Chunking切碎
5. **知识关联缺失**：缺乏实体间关系的显式建模
6. **动态更新困难**：增量更新需要重建整个索引
7. **领域适配门槛高**：通用模型对特定领域术语理解不足 ^[inferred]

## 微软GraphRAG索引管线

微软GraphRAG的索引管线包含14个工作流，从原始文本到可查询的知识图谱：

### 管线14步流程

| 步骤 | 工作流 | 输入→输出 |
|------|--------|-----------|
| 1 | `create_base_text_units` | 原始文档 → 文本单元（Chunking） |
| 2 | `create_base_extracted_entities` | 文本单元 → 实体+关系+声明（LLM提取） |
| 3 | `create_summarized_entities` | 实体+关系 → 合并后实体（相同实体去重合并） |
| 4 | `create_base_entity_graph` | 合并实体 → S2图结构（Leiden社区检测输入） |
| 5 | `create_final_entities` | 图结构 → 最终实体节点（含类型、描述、社区归属） |
| 6 | `create_final_nodes` | 实体 → 点层级信息（社区嵌套结构） |
| 7 | `create_final_communities` | 图 → 社区划分（Leiden层次化社区检测） |
| 8 | `create_final_community_reports` | 社区 → LLM生成社区摘要报告 |
| 9 | `create_final_text_units` | 文本单元 → 映射到实体和社区的关联 |
| 10 | `create_final_relationships` | 关系 → 最终边（含权重、描述、社区归属） |
| 11 | `embed_graph_nodes` | 实体描述 → Node2Vec/Embedding向量 |
| 12 | `embed_community_reports` | 社区报告 → Embedding向量 |
| 13 | `create_base_entity_embeddings` | 实体 → Embedding向量存储 |
| 14 | `create_final_covariates` | 声明(Covariate) → 结构化属性表 |

### 实体提取

LLM从每个文本单元中提取三类结构：
- **实体（Entity）**：`name | type | description`，例如 `路飞 | PERSON | 船长`
- **关系（Relationship）**：`source | target | description | strength`，例如 `路飞→草帽团 | 属于 | 10`
- **声明（Claim/Covariate）**：`subject | object | type | status | description`，例如 `路飞 | 海贼王 | 竞争 | ACTIVE | 想成为海贼王`

### 图合并操作

同一实体的多次提取会触发合并：
- **同名实体合并**：取最长描述、合并所有关系
- **关系合并**：权重累加、描述合并
- **图融合**：多个Chunk的子图通过实体名匹配连接成全图

### Leiden社区检测

Leiden算法在图上进行层次化社区划分：
- 输出多层嵌套社区结构（从细粒度到粗粒度）
- 每个社区生成一份摘要报告（LLM生成），覆盖该社区的核心实体、关系、主题
- 社区层级越粗，报告越概括——适合全局型问题

## 三种搜索模式

| 模式 | 输入 | 搜索范围 | 适用场景 |
|------|------|----------|----------|
| **Local Search** | 实体名/关键词 | 实体→相邻实体→所属社区报告 | 局部型问题（"路飞有什么能力？"） |
| **Global Search** | 全局问题 | 从社区报告层级自底向上搜索 | 全局型问题（"海贼王故事的核心主题？"） |
| **DRIFT Search** | 混合 | 实体→社区→跨社区遍历 | 多跳型问题（"路飞的伙伴们分别来自哪个阵营？"） ^[inferred] |

**Global Search实现**：将所有社区报告按层级排序，先搜索最粗粒度社区报告，不够细再搜索更细粒度——Map-Reduce模式，分批喂给LLM再综合。

## 蚂蚁集团统一架构设计

蚂蚁集团的GraphRAG设计走了一条不同于微软的路线——**统一IndexStore抽象**：

### 三元组提取→子图检索→生成

```
索引阶段：
  文档 → Chunk → 三元组提取(TripletExtractor) → 图存储(GraphStoreBase)
  
查询阶段：
  Query → 实体识别 → 子图检索(explore API) → 上下文组装 → LLM生成
```

### 技术选型

| 层 | 选择 | 原因 |
|----|------|------|
| 应用框架 | DB-GPT | 多模型管理+Agent能力 |
| 图引擎 | OpenSPG + TuGraph | OpenSPG语义建模+TuGraph高性能图查询 |
| 向量引擎 | Milvus | 大规模向量检索 |

### 领域建模（桥接模式）

蚂蚁的领域建模采用"桥接模式"——用Schema约束实体/关系类型，而非自由提取：
- 定义EntityType（如`Person`、`Organization`、`Event`）
- 定义RelationType（如`belongs_to`、`located_in`）
- 提取结果必须符合Schema，否则无法入库
- 好处：图结构更干净，查询更精确；代价：需要领域专家定义Schema ^[inferred]

### 优化方向

- 图元数据增强（时间、来源、置信度标注）
- 知识提取微调（减少LLM幻觉实体）
- 社区总结替代全图遍历
- 多模态知识图谱（图像、表格入图）
- 混合存储（向量+图+全文统一查询）
- 图语言微调（让LLM直接生成图查询语句）
- RAG-to-Agent演进（GraphRAG作为Agent的知识基础）

## 6大开源GraphRAG项目PK

| 项目 | 技术路线 | 交互模式 | 硬件门槛 | 多模态 | 动态更新 |
|------|----------|----------|----------|--------|----------|
| **微软GraphRAG** | 完整管线14步+Leiden | 本地/全局/DRIFT | 高（多轮LLM调用） | ❌ | ❌需全量重建 |
| **LightRAG** | 双层检索（低层实体+高层主题） | 低层精确+高层概括 | 中 | ❌ | ✅增量插入 |
| **KAG(OpenSPG)** | Schema约束+逻辑推理 | 结构化查询 | 中 | ✅部分 | ✅增量 |
| **Yuxi-Know** | 轻量图+向量双引擎 | 简单问答 | 低 | ❌ | ✅ |
| **HippoRAG** | 仿人脑记忆索引(PersonalPG) | 个性化检索 | 低 | ❌ | ✅ |
| **NebulaGraph** | 原生图数据库+LLM | 图查询+自然语言 | 中 | ❌ | ✅ |

**选型建议**：
- 追求完整性 → 微软GraphRAG（代价高但最系统）
- 追求轻量和增量更新 → LightRAG
- 有领域Schema → KAG(OpenSPG)
- 快速验证 → Yuxi-Know ^[inferred]

## 部署实践要点

- **配置文件**：`settings.yaml`是核心，配置LLM模型、Chunk大小、社区层级
- **SSL证书问题**：部署时可能遇到OpenSSL版本不匹配，需手动处理
- **成本控制**：索引阶段LLM调用量大，中小文档集可使用便宜模型（gpt-4o-mini）做提取，贵模型只做社区摘要
- **查询调试**：先用Local Search验证实体提取质量，再切换到Global Search
- **Neo4j可视化**：可用Neo4j浏览器直接查看提取出的知识图谱结构

## 与传统RAG的关系

GraphRAG不是替代传统RAG，而是**补充**——局部型问题仍然用传统RAG+向量检索，全局型/多跳型问题用GraphRAG。工程上两者应并存。 ^[inferred]

**GraphRAG vs KAG范式差异**：
- GraphRAG"以检索为始"——先建图再检索
- KAG"以推理为始"——先推理需要什么知识再建图 ^^[ambiguous]

## 延伸阅读

- [[concepts/rag-engineering]] — RAG工程全景（GraphRAG是高级范式之一）
- [[entities/graphify-gitnexus]] — Graphify/GitNexus知识图谱工具对比
- [[concepts/rag-chunking-strategies]] — 分块策略（GraphRAG的Chunking是第一步）
- [[concepts/agent-framework-engineering]] — GraphRAG作为Agent的知识基础

## 来源

- GraphRAG微软源代码理解（raw/sources/AI 人工智能/Agent架构/RAG/高级RAG/GraphRAG/）
- GraphRAG详解（raw/sources/AI 人工智能/Agent架构/RAG/高级RAG/GraphRAG/）
- GraphRAG开源生态全景-6大项目PK（raw/sources/AI 人工智能/Agent架构/RAG/高级RAG/GraphRAG/）
- GraphRAG设计解读（raw/sources/AI 人工智能/Agent架构/RAG/高级RAG/GraphRAG/）
- GraphRAG原理及部署实战-博客园（raw/sources/AI 人工智能/Agent架构/RAG/高级RAG/GraphRAG/）
- GraphRAG知识图谱全流程解析（raw/sources/AI 人工智能/Agent架构/RAG/高级RAG/GraphRAG/）
