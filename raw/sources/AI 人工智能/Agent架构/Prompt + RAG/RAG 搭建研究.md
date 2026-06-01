---
title: RAG的搭建方式研究
source_url: https://www.cnblogs.com/gccbuaa/p/19283937
source_site: 博客园
author: gccbuaa
date_extracted: 2026-05-16
credibility: low
tags:
  - RAG
  - 分块策略
  - 混合检索
  - Rerank
  - HyDE
  - CRAG
  - 知识图谱
---

# RAG的搭建方式研究

---

## 一、文档分块策略：筑牢知识地基

文档分块是将长文本切割为适合检索的"语义单元"，直接影响后续检索的**召回率**（找到相关信息）与**相关性**（信息精准度）。以下5种分块策略适配不同文档类型与业务需求：

### 1. 基础版RAG（Simple RAG）：快速验证的入门级

```python
from langchain.document_loaders import SimpleDirectoryReader
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
# 加载文档
loader = SimpleDirectoryReader(input_dir="./data")
documents = loader.load()
# 分块（固定长度）
from langchain.text_splitter import CharacterTextSplitter
text_splitter = CharacterTextSplitter(chunk_size=512, chunk_overlap=0)
doc_splits = text_splitter.split_documents(documents)
# 构建向量库
embed_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vectorstore = FAISS.from_documents(doc_splits, embed_model)
```

### 2. 语义分块（Semantic Chunking）：保障语义完整的进阶方案

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter
# 语义分块（按段落、句子拆分，保留语义连贯性）
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=128,
    separators=["\n\n", "\n", "。", "！", "？"], # 按语义分隔符拆分
    length_function=len
)
doc_splits = text_splitter.split_documents(documents)
```

### 3. 上下文增强（Context Enriched）：提升长文档推理的连贯方案

使用滑动窗口（SlidingWindowTextSplitter），通过 window_size 和 step_size 参数控制窗口大小和步长。

### 4. 块头标签（Contextual Headers）：适配结构化文档的精准方案

```python
from langchain.schema import Document
# 为文档添加元数据（标题、章节名）
doc = Document(
    page_content="这是产品功能的具体描述...",
    metadata={"title": "产品功能", "section": "1.1"}
)
```

### 5. 文档增强（Augmentation）：扩大检索覆盖的多视图

---

## 二、检索与排序增强：精准命中知识的关键环节

检索阶段的目标是"**从海量知识库中快速找到与问题最相关的信息**"，需平衡"召回率"（找到所有相关信息）与"精准度"（找到最相关信息）。以下4种方法可实现RAG的"持续进化"：

### 6. 查询改写（Query Transformation）：扩大检索覆盖的多问法

```python
from langchain.retrievers import MultiQueryRetriever
# 初始化MultiQueryRetriever
retriever = MultiQueryRetriever.from_llm(
    llm=ChatOpenAI(model="gpt-3.5-turbo"),
    base_retriever=vectorstore.as_retriever(),
    query_prompt="""请将以下问题改写为3个语义等价的问法：
原始问题：{query}"""
)
# 检索（生成3个问法，分别检索）
results = retriever.get_relevant_documents("如何优化RAG的分块策略")
```

### 7. 重排序（Reranker）：提升精准度的二次筛选

```python
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
# 初始化重排序压缩器
compressor = CrossEncoderReranker(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
# 构建压缩检索器（先检索Top10，再重排序取Top3）
compression_retriever = ContextualCompressionRetriever(
    base_compressor=compressor,
    base_retriever=vectorstore.as_retriever(search_kwargs={"k": 10})
)
# 检索（返回Top3重排序后的文档）
results = compression_retriever.get_relevant_documents("2024年AI领域最新论文")
```

### 8. 相关片段提取（RSE，Relevant Span Extraction）：定位关键信息的精准

### 9. 上下文压缩（Contextual Compression）：降低Token成本的精简方案

```python
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import DocumentCompressorPipeline
from langchain.retrievers.document_compressors import LengthBasedCompressor
# 初始化压缩器（剔除超过500token的文档）
compressor = DocumentCompressorPipeline([
    LengthBasedCompressor(max_length=500)
])
# 构建压缩检索器
compression_retriever = ContextualCompressionRetriever(
    base_compressor=compressor,
    base_retriever=vectorstore.as_retriever()
)
# 检索（返回压缩后的文档）
results = compression_retriever.get_relevant_documents("产品的核心功能")
```

### 10. 混合检索（Hybrid Retrieval）：平衡精度与召回的综合方案

---

## 三、后处理与反馈优化：持续进化的动态系统

优秀的RAG系统不仅能"精准检索"，还能根据用户反馈、业务变化**动态优化**。以下8种方法可实现RAG的"持续进化"：

### 11. 反馈闭环（Feedback Loop）：基于用户行为的优化

### 12. 自适应检索（Adaptive RAG）：多场景适配

### 13. 自我决策RAG（Self RAG）：提升效率的智能跳过

### 14. 知识图谱增强（Knowledge Graph）：结构化知识的深度关联

```cypher
// 查询产品的开发商（实体-关系-属性）
MATCH (p:Product {name: "产品A"})-[:BELONGS_TO]->(c:Company)
RETURN c.name
```

### 15. 层次索引（Hierarchical Indices）：节省计算开销

### 16. 假设性文档嵌入（HyDE，Hypothetical Document Embedding）：应对模糊问题的逆向方案

```python
from dashscope import Generation
# 定义HyDE生成函数
def generate_hyde_query(original_query: str) -> str:
    prompt = f"""请根据以下问题，生成一个假设性的、详细的答案。即使你不确定正确答案，也请模仿百科知识的风格和语气来写。
问题：{original_query}
假设性答案："""
    response = Generation.call(
        model='qwen-max',
        prompt=prompt,
        seed=12345,
        top_p=0.8
    )
    hyde_text = response.output['text'].strip()
    return hyde_text
# 生成假设答案
hyde_query = generate_hyde_query("牛顿第一定律是什么？")
print(hyde_query)
```

### 17. 纠错式RAG（CRAG：Corrective RAG）：容错性强的问题补全

---

## 四、RAG方式的选型指南

实际落地时，无需全部采用17种方式，需根据**业务目标**选择核心方案。以下是不同需求场景的选型推荐：

| **应用目标** | **推荐方法组合** | **核心优势** |
| --- | --- | --- |
| 快速上线（1~2周落地） | Simple RAG + 基础向量库（FAISS） | 开发成本低，无需复杂定制 |
| 提升回答准确性 | 语义分块 + Reranker + RSE | 从分块、排序、提取三环节保障信息精准度 |
| 扩大检索覆盖范围 | Query Transformation + Fusion + 文档增强 | 多问法、多策略、多视图覆盖更多相关内容 |
| 降低成本与提升效率 | Self RAG + Contextual Compression + 多级索引 | 减少检索次数、压缩Token、加速大规模检索 |
| 支持结构化知识查询 | 块头标签分块 + Knowledge Graph | 适配层级文档，挖掘实体关联 |
| 基于用户反馈持续优化 | Feedback Loop + Adaptive RAG | 动态适配用户需求，长期提升系统效果 |
| 应对非专业用户提问 | CRAG + HyDE | 修复问题错误，补充上下文，提升容错性 |

## 五、总结：RAG的核心是灵活组合与持续迭代

RAG并非单一工具，而是"**文档处理→检索增强→生成优化→反馈迭代**"的全链路系统。其核心价值在于"**让LLM用上准确、实时的外部知识**"，解决传统LLM的"知识滞后""幻觉生成""输出不可控"等痛点。

只有让RAG与业务场景深度绑定，才能真正发挥其"**精准、可控、可进化**"的核心价值，为企业带来实际的业务价值（如降低客服成本、提升员工效率、优化用户体验）。

---

*来源：博客园 | 作者：gccbuaa | 提取日期：2026-05-16*