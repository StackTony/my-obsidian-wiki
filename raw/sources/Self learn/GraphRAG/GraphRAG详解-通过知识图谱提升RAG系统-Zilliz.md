---
title: GraphRAG详解：通过知识图谱提升RAG系统
source: https://zilliz.com.cn/blog/graphrag-explained-enhance-rag-with-knowledge-graphs
credibility: low
downloaded: 2026-06-12
---

# GraphRAG详解：通过知识图谱提升RAG系统

## RAG简介与RAG面临的挑战

检索增强生成（Retrieval Augmented Generation，RAG）是一种连接外部数据源以增强大语言模型（LLM）输出质量的技术。这种技术帮助LLM访问私有数据或特定领域的数据，并解决幻觉问题。

一个基本的RAG通常集成了一个向量数据库和一个LLM，其中向量数据库存储并检索与用户查询相关的上下文信息，LLM根据检索到的上下文生成答案。虽然这种方法在大部分情况下效果都很好，但在处理复杂任务时却面临一些挑战，如多跳推理（multi-hop reasoning）或联系不同信息片段全面回答问题。

以这个问题为例："What name was given to the son of the man who defeated the usurper Allectus?"

一个基本的RAG通常会遵循以下步骤来回答这个问题：

1. 识别那个人：确定谁打败了Allectus。
2. 研究那个人的儿子：查找有关这个人家庭的信息，特别是他的儿子。
3. 找到名字：确定儿子的名字。

通常第一步就会面临挑战，因为基本的RAG根据语义相似性检索文本，而不是基于在数据集中没有明确提及具体细节来回答复杂的查询问题。

为了应对这些挑战，微软研究院引入了GraphRAG，这是一种全新方法，它通过知识图谱增强RAG的检索和生成。

## GraphRAG及其工作原理简介

与使用向量数据库检索语义相似文本的基本RAG不同，GraphRAG通过结合知识图谱（KGs）来增强RAG。知识图谱是一种数据结构，它根据数据间的关系来存储和联系相关或不相关的数据。

GraphRAG流程通常包括两个基本过程：**索引**和**查询**。

### 索引

索引过程包括四个关键步骤：

1. **文本单元分割（Text Unit Segmentation）**：整个输入语料库被划分为多个文本单元（文本块）。这些文本块是最小的可分析单元，可以是段落、句子或其他逻辑单元。通过将长文档分割成较小的文本块，我们可以提取并保留有关输入数据的更详细信息。

2. **提取Entity、关系（Relationship）和Claim**：GraphRAG使用LLM识别并提取每个文本单元中的所有Entity（人名、地点、组织等）、Entity之间的关系以及文本中表达的关键Claim。我们将使用这些提取的信息构建初始知识图谱。

3. **层次聚类**：GraphRAG使用Leiden技术对初始知识图谱执行分层聚类。Leiden是一种community检测算法，能够有效地发现图中的community结构。每个聚类中的Entity被分配到不同的community，以便进行更深入的分析。

4. **生成Community摘要**：GraphRAG使用自下而上的方法为每个community及其中的重要部分生成摘要。这些摘要包括Community内的主要Entity、Entity的关系和关键Claim。这一步为整个数据集提供了概览，并为后续查询提供了有用的上下文信息。

### 查询

GraphRAG有两种不同的查询工作流程：

- **全局搜索**：通过利用Community摘要，对涉及整个数据语料库的整体性问题进行推理。
- **本地搜索**：通过扩展到特定Entity的邻居和相关概念，对特定Entity进行推理。

#### 全局搜索工作流程

1. 用户查询和对话历史：系统将用户查询和对话历史作为初始输入。
2. Community报告分批：Community报告被打乱并分成多个批次。
3. RIR（评级中间响应）：每批Community报告生成中间响应，每个点有数值分数表示重要性。
4. 排名和过滤：选择最重要的点形成聚合的中间响应。
5. 最终响应：聚合的中间响应被用作上下文以生成最终回复。

#### 本地搜索工作流程

1. 用户查询：系统接收用户查询。
2. 搜索相似Entity：使用Milvus向量数据库进行文本相似性搜索，识别语义相关的Entity。
3. Entity-文本单元映射：提取的文本单元被映射到相应的Entity。
4. Entity-关系提取：提取Entity及其相应关系。
5. Entity-协变量（Covariate）映射：将Entity映射到协变量。
6. Entity-Community报告映射：Community报告整合全局信息。
7. 利用对话历史：理解用户意图和上下文。
8. 生成响应：根据过滤和排序的数据生成最终响应。

## 基础RAG与GraphRAG输出质量对比

GraphRAG的开发者在实验中使用了VIINA数据集。基础RAG和GraphRAG都被问到："What are the top 5 themes in the dataset?"

基础RAG提供的结果与战争主题无关，而GraphRAG提供了清晰且高度相关的答案。

论文研究表明，GraphRAG在**全面性**和**多样性**方面都超过了基础RAG。

## 使用Milvus向量数据库搭建GraphRAG应用

GraphRAG依赖于向量数据库来实现检索。步骤包括：

1. 安装依赖：`pip install --upgrade pymilvus`
2. 准备数据：下载达芬奇故事集文本文件
3. 初始化Workspace：`python -m graphrag.index --init --root ./graphrag_index`
4. 配置.env文件：添加OpenAI API key
5. 运行索引pipeline：`python -m graphrag.index --root ./graphrag_index`
6. 查询Milvus向量数据库：将Entity描述向量存储在Milvus中

索引结果示例：
- Entity数量: 651
- Relationship数量: 290
- Community报告数量: 45
- Text单元数量: 51

## 总结

GraphRAG是一种通过整合知识图谱来增强RAG技术的创新方法。与Milvus向量数据库结合使用时，GraphRAG可以驾驭大型数据集中复杂的语义关系，提供更准确的结果。

## 更多资源

- GraphRAG论文: From Local to Global: A Graph RAG Approach to Query-Focused Summarization
- GraphRAG GitHub: https://github.com/microsoft/graphrag