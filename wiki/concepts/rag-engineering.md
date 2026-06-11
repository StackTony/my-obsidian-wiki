---
title: RAG工程全景
category: concepts
tags: [AI, RAG, 检索, 向量库, 知识图谱]
summary: RAG工程不是"向量检索+大模型生成"这么简单，而是从文档解析到答案评估的完整流水线——准确率更多取决于数据和检索工程
source_dir: AI 人工智能/Agent架构/RAG
source_files: [2-RAG 全栈介绍.md, 1-RAG 核心术语速查表.md, RAG 搭建研究.md, 3-RAG 工程全景.md]
provenance:
  extracted: 0.70
  inferred: 0.25
  ambiguous: 0.05
base_confidence: 0.85
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: core
created: 2026-06-02
updated: 2026-06-11
relationships:
  - target: "[[concepts/llm-infra-landscape]]"
    type: uses
  - target: "[[concepts/rag-chunking-strategies]]"
    type: uses
  - target: "[[concepts/agent-framework-engineering]]"
    type: related_to
  - target: "[[entities/vector-database-comparison]]"
    type: uses
  - target: "[[concepts/data-flywheel]]"
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
  用户Query → 查询改写/路由 → 混合检索(向量+BM25) → 重排(Rerank)
            → 上下文组装(Prompt模板) → LLM生成 → 引用回填 → 返回
```

### 文档解析

工业RAG的准确率70%以上取决于文档解析质量。没有单一工具能打通所有文档类型，生产上分文件类型路由再加VLM兜底链路。

| 文档类型 | 难点 | 典型工具 |
|----------|------|----------|
| 原生PDF | 双栏排版、页眉页脚、公式、表格 | PyMuPDF、pdfplumber、Unstructured |
| 扫描PDF/图片 | OCR精度、版式还原 | PaddleOCR、OlmOCR、MinerU |
| HTML/Markdown | 噪声（广告、导航）、嵌套结构 | trafilatura、readability |
| Office | 批注、嵌入对象 | python-docx、python-pptx |
| 表格 | 跨页、合并单元格 | Camelot、Tabula、pdfplumber |
| 图像/图表 | 语义理解 | GPT-4o、Qwen-VL |
| 代码 | 语法边界 | tree-sitter |

关键工程细节：
- **清洗不是可选项**：去掉页眉页脚、合并断句、规范化空白、抽出标题层级
- **metadata必须打标**：`doc_id/page/section/source_url`，决定能否按部门/时间/权限过滤
- **表格不切**：标记为原子Element，独占一个chunk，大表单建索引
- **VLM兜底**：对解析失败的"图片+表格+公式"页面，喂给Qwen-VL/GPT-4o转Markdown

### Chunking

详见 [[concepts/rag-chunking-strategies]]

核心经验值：中文300–800字/英文256–512 token，overlap 10–15%。必须用目标Embedding模型的tokenizer计数，不能按字符估算。

### Embedding与索引

**主流模型**：

| 模型 | 维度 | 特色 |
|------|------|------|
| BGE-M3 | 1024 | 中文强，同时出稠密+稀疏+ColBERT多向量 |
| Qwen3-Embedding | 1024–4096 | 阿里2025新出，C-MTEB SOTA |
| OpenAI text-embedding-3-large | 3072(可截断) | Matryoshka，闭源 |
| E5-Mistral-7B | 4096 | 大参数，MTEB强 |
| Jina jina-embeddings-v3 | 1024 | 长文(8K) |

**ColBERT**：Late Interaction，每个token存一个向量，MaxSim求和。精度接近cross-encoder，但存储膨胀~30×。代表：Jina-ColBERT-v2、BGE-M3 multi-vector模式。

**索引三元组**：向量(HNSW)负责语义召回、倒排(BM25)负责关键词和过滤、图(Neo4j)负责多跳推理。工程上三者往往同时存在。

**工程坑**：归一化(cosine vs dot product)要确认；指令式embedding(E5/Qwen3)需加prompt前缀否则精度下降；Embedding升级意味着全量重建索引，必须有A/B双写机制。

### 混合检索与融合

单独向量不够——专有名词、型号、错误码(`ORA-00942`)embedding经常分不清。BM25在这些场景稳如老狗。两者互补。

**融合方法**：
- **RRF**（工业默认）：`score = Σ 1/(k + rank_i)`，k=60，不需要分数归一化
- **Weighted Sum**：`α * vec + (1-α) * bm25`，需min-max归一化
- **Learned Fusion**：小模型学融合权重，适合大型搜索系统

### 重排（Rerank）

Embedding是bi-encoder（query与doc独立编码），Rerank用cross-encoder一起编码精度更高但O(N)只能在Top-K上做。

| 模型 | 特点 |
|------|------|
| BGE-Reranker-v2(m3/gemma) | 开源中英双语，m3轻量gemma质量更好 |
| Jina-Reranker-v2 | 多语，延迟友好 |
| Cohere Rerank 3 | 闭源API，开箱即用 |
| Qwen3-Reranker | 阿里2025，中文场景优势 |

**三级漏斗**：向量召回Top-200 → ColBERT rescore Top-50 → cross-encoder Top-5。精度与延迟最佳平衡，但工程复杂度高。

**工程要点**：cross-encoder最大512 token；rerank分数低于阈值直接拒答可降幻觉；多语混检需多语版本reranker。

### Query改写与路由

- **HyDE**：LLM先"假装回答"，假答案embedding检索，对事实问答型+5–15个百分点
- **Multi-Query**：一个问题改写3–5表述，分别检索RRF合并
- **Subquery分解**：复杂问题拆多个子问题并行检索（Agentic RAG基础）
- **Query路由**：意图分类→知识库选择→改写vs直连

### 上下文组装与引用回填

- "禁止脱离资料"指令放在最前面，LLM对指令位置敏感
- 每块带编号`[i]`方便引用，后处理映射回URL+页码
- 长上下文按Relevance倒序摆放（重要放开头结尾，对抗Lost in the Middle）
- 加"不知道就说不知道"——一句指令显著降幻觉

## 高级RAG范式

| 范式 | 核心思路 | 工程复杂度 | 适用场景 |
|------|----------|-----------|----------|
| Self-RAG | 模型自己决定是否检索、检索到的是否相关 | 高(需微调模型) | 动态控制检索 |
| CRAG | 检索评估器判correct/ambiguous/incorrect，错误走Web搜索 | 低(加评估模型即可) | 最易落地的纠偏方案 |
| Adaptive RAG | 按问题难度路由：简单→单跳→多跳 | 中 | 节省成本与延迟 |
| GraphRAG | 实体→关系→社区发现→社区摘要 | 高(LLM调用量大) | 全局型/综述型问题 |
| Agentic RAG | 规划→子查询→检索→反思→再查→综合 | 高(延迟3–5×) | 多跳问答、跨库综合 |

**Long-context vs 小chunk RAG**：现实答案几乎总是混合——大部分问题走小chunk RAG，少数需全局视角的走长上下文或GraphRAG ^[inferred]。

## 评估

**两层评估**（底层指标原理见 [[concepts/evaluation-metrics]]）：
- 检索层：Recall@K、MRR、nDCG@K
- 生成层（RAGAS）：Faithfulness、Answer Relevancy、Context Precision、Context Recall

评估数据集：自建500–2000条人工标注、开源(CRAG/MS MARCO/BEIR/T2Ranking/MultiHop-RAG)、LLM-as-Judge(GPT-4o/DeepSeek-V3)

## 生产架构

**离线ETL**：源系统→采集→解析清洗(Spark/Ray/Prefect)→Chunking+Embedding(GPU批推)→写入(Milvus+ES+MySQL)→索引校验

**在线服务**：API Gateway→Router→Query Rewriter→Retriever(向量+BM25并行→RRF)→Reranker→Prompt Builder→LLM Gateway→Citation Postprocessor→返回+记录观测

**延迟预算**（中文企业问答）：改写150–400ms / 向量召回20–80ms / BM25 10–30ms / Rerank 100–300ms / LLM首字300–1000ms / 全程1.5–4s

## 国内外生态

| 维度 | 托管云(百炼/Bedrock KB) | 开源低代码(Dify/FastGPT/RagFlow) | 自研(LlamaIndex/LangChain) |
|------|-------------------------|----------------------------------|----------------------------|
| 上线速度 | 天级 | 周级 | 月级 |
| 可定制性 | 低 | 中 | 高 |
| 数据主权 | 看部署 | 私有化友好 | 完全自主 |

经验法则：**POC快速验证→中期用开源平台沉淀→核心业务再走自研** ^[inferred]。

## 延伸阅读

相关概念：[[concepts/data-flywheel]] — 数据飞轮与RAG的数据基础循环
相关实体：[[entities/vector-database-comparison]]、[[entities/graphify-gitnexus]]

## 来源

- 2-RAG 全栈介绍（raw/sources/AI 人工智能/Agent架构/RAG/）
- 1-RAG 核心术语速查表（raw/sources/AI 人工智能/Agent架构/RAG/）
- RAG 搭建研究（raw/sources/AI 人工智能/Agent架构/RAG/）
- 3-RAG 工程全景（raw/sources/AI 人工智能/Agent架构/RAG/）