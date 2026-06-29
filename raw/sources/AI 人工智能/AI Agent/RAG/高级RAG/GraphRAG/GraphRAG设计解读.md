原文： https://www.cnblogs.com/fanzhidongyzby/p/18252630/graphrag

**检索增强生成** （RAG：Retrieval Augmented Generation）技术旨在把信息检索与大模型结合，以缓解大模型推理“幻觉”的问题。近来关于RAG的研究如火如荼，支持RAG的开源框架也层出不穷，并孕育了大量专业领域的AI工程应用。我们设计了一个通用的开源RAG框架，以兼容未来多样化的基础研究建设和工程化应用诉求。

## 1\. 概述

RAG的目标是通过知识库增强内容生成的质量，通常做法是将检索出来的文档作为提示词的上下文，一并提供给大模型让其生成更可靠的答案。更进一步地，RAG的整体链路还可以与提示词工程（Prompt Engineering）、模型微调（Fine Tuning）、知识图谱（Knowledge Graph）等技术结合，构成更广义的RAG问答链路。  
![广义的RAG问答链路](https://pic1.zhimg.com/80/v2-d013c786b40fce9ae975c75667d9ad4e_1440w.png)

除了传统意义上的增强内容生成，RAG的理念还可以进一步泛化到链路的其他阶段：

- **增强训练** ： [REALM](https://arxiv.org/abs/2002.08909) 引入了知识检索器增强大模型预训练，以改进大模型的问答质量和可解释性。
- **增强微调** ： [RA-DIT](https://arxiv.org/abs/2310.01352) 实现了对大模型和检索器的双指令微调， [RAFT](https://arxiv.org/abs/2403.05313) 通过微调让大模型可以识别干扰文档。
- **增强语料** ： [MuRAG](https://arxiv.org/abs/2210.02928) 支持了多模态数据的检索，提升了大模型在文本/图像混合检索场景下的推理质量。
- **增强知识** ： [GraphRAG](https://arxiv.org/abs/2404.16130) 使用图社区摘要解决总结性查询任务的问题，将知识图谱技术应用到RAG。
- **增强检索** ： [CRAG](https://arxiv.org/abs/2401.15884) 通过对检索到的文档置信度进行评估，提升问答上下文的质量。
- **增强推理** ： [RAT](https://arxiv.org/abs/2403.05313) 在推理阶段将RAG与CoT相结合，以改进长期推理和生成任务的效果。

我们希望向大家分享一下：引入知识图谱技术后，传统RAG链路到Graph RAG链路会有什么样的变化，如何兼容RAG中的向量数据库（Vector Database）和图数据库（Graph Database）基座，以及蚂蚁的Graph RAG开源技术方案和未来优化方向。

## 2\. 传统RAG

首先回顾一下传统RAG的核心链路。  
![基于Vector的RAG链路](https://picx.zhimg.com/80/v2-86d6ed4556c4efc5db3ea30bdaa3f20d_1440w.png)

传统RAG的核心链路分为三个阶段：

- **索引（向量嵌入）** ：通过Embedding模型服务实现文档的向量编码，写入向量数据库。
- **检索（相似查询）** ：通过Embedding模型服务实现查询的向量编码，使用相似性查询（ANN）实现topK结果搜索。
- **生成（文档上下文）** ：Retriver检索的结果文档作为上下文和问题一起提交给大模型处理。

传统RAG希望通过知识库的关联知识增强大模型问答的上下文以提升生成内容质量，但也存在诸多问题。  
![传统RAG的不足](https://pic1.zhimg.com/80/v2-346b1b7115241d8b00198665bd0dc877_1440w.png)

**论文\[23\]《Seven Failure Points...》** 总结了传统RAG的7个问题：

1. **知识库内容缺失** ：现有的文档其实回答不了用户的问题，系统有时被误导，给出的回应其实是“胡说八道”，理想情况系统应该回应类似“抱歉，我不知道”。
2. **TopK截断有用文档** ：和用户查询相关的文档因为相似度不足被TopK截断，本质上是相似度不能精确度量文档相关性。
3. **上下文整合丢失** ：从数据库中检索到包含答案的文档，因为重排序/过滤规则等策略，导致有用的文档没有被整合到上下文中。
4. **有用信息未识别** ：受到LLM能力限制，有价值的文档内容没有被正确识别，这通常发生在上下文中存在过多的噪音或矛盾信息时。
5. **提示词格式问题** ：提示词给定的指令格式出现问题，导致大模型/微调模型不能识别用户的真正意图。
6. **准确性不足** ：LLM没能充分利用或者过度利用了上下文的信息，比如给学生找老师首要考虑的是教育资源的信息，而不是具体确定是哪个老师。另外，当用户的提问过于笼统时，也会出现准确性不足的问题。
7. **答案不完整** ：仅基于上下文提供的内容生成答案，会导致回答的内容不够完整。比如问“文档 A、B和C的主流观点是什么？”，更好的方法是分别提问并总结。

总的来看：

- 问题1-3：属于知识库工程层面的问题，可以通过完善知识库、增强知识确定性、优化上下文整合策略解决。
- 问题4-6：属于大模型自身能力的问题，依赖大模型的训练和迭代。
- 问题7：属于RAG架构问题，更有前景的思路是使用Agent引入规划能力。

## 3\. Graph RAG

考虑到传统RAG能力上的不足，Graph RAG从增强知识确定性角度做了进一步的改进，也就是最开始提到的知识内容增强的思路。相比于传统的基于Vector格式的知识库存储，Graph RAG引入了知识图谱技术，使用Graph格式存储知识。

正如 **论文\[2\]《Retrieval-Augmented Generation...》** 所阐述的：基于知识图谱，可以为RAG提供高质量的上下文，以减轻模型幻觉。

> Structured data, such as knowledge graphs (KGs), provide high-quality context and mitigate model hallucinations.

![基于Graph的RAG链路](https://pica.zhimg.com/80/v2-5dd2a5405d3b684c237aa4e9b9547ca2_1440w.png)

类似地，Graph RAG的核心链路分如下三个阶段：

- **索引（三元组抽取）** ：通过LLM服务实现文档的三元组提取，写入图数据库。
- **检索（子图召回）** ：通过LLM服务实现查询的关键词提取和泛化（大小写、别称、同义词等），并基于关键词实现子图遍历（DFS/BFS），搜索N跳以内的局部子图。
- **生成（子图上下文）** ：将局部子图数据格式化为文本，作为上下文和问题一起提交给大模型处理。

需要说明的是，从文本中提取三元组和关键词借助了现有的文本大模型的能力，传统的NLP技术如分词、句法分析、实体识别等已经不再是SOTA。另外，借助于大模型微调技术，可以针对性的构建面向知识抽取、实体识别、自然语言翻译的专有大模型。比如由蚂蚁和浙大联合研发的大模型知识抽取框架 [OneKE](https://github.com/zjunlp/DeepKE/blob/main/example/llm/OneKE.md) 在零样本泛化性能上全面超过了现有模型。以及借助于Text2GQL、Text2Cypher技术微调的图查询语言专有模型，可以直接将自然语言转换为图查询语言，代替基于关键词中心的子图搜索从而获得更精确的图谱数据。

![OneKE知识抽取模型能力透视](https://pic1.zhimg.com/80/v2-010ad701f8abc571f0fc0b9cfee2ad18_1440w.png)

## 4\. 通用RAG设计

基于以上对传统RAG和Graph RAG的能力介绍，我们可以发现两种RAG架构的核心差异在于知识存储格式的变化（从Vector到Graph），从而导致了RAG中索引、检索和生成阶段流转数据格式的变化。而RAG的关键流程并未发生根本的改变，基于这个相似性前提，我完全可以抽象出一个更通用的RAG结构，以兼容向量索引和图索引，甚至更多的索引格式（如全文索引等）。

## 4.1 架构设计

于是一个兼容多种知识索引格式的通用RAG架构，可以按照如下方式设计。

- 所有的索引存储统一抽象为IndexStore，LLM服务作为构建索引能力依赖（文本模型、嵌入模型等）。
- 索引存储当下支持向量存储（VectorStore）和知识图谱（Knowledge Graph）两种，保留对其他索引格式的扩展能力。
- 知识图谱层负责知识的表示和语义抽象，数据底座是图存储（GraphStore）。当然也可以直接对接外部的知识图谱系统。
- 最底层接入多样化的向量数据库、图数据库、大模型服务等外部组件。
- 最上层借助于IndexStore核心抽象，搭配外围的Loader/Splitter实现文本读取切分、Transformer实现索引的构建、Retriver/Synthesizer实现知识检索与合成，构建完整的RAG能力。

![通用RAG架构](https://picx.zhimg.com/80/v2-42b2622482ae3cce7c5c3434557c2fa8_1440w.png)

## 4.2 领域建模

建模是架构落地的第一步，这里对通用RAG的核心设计做出说明：

- 为了让框架有足够的灵活性，我们将索引的加工和存储进行了分离，并使用“桥接模式”构建抽象依赖关系。
- 索引的加工接口（Transformer）提供三类特定实现：嵌入、抽取、翻译。向量索引走嵌入的方式，如Text2Vector、OpenAI Embedding等。图索引走Extractor，如三元组抽取、关键词抽取等。翻译可以作为通用能力单独对待，承载DSL的模型微调能力，如Text2SQL、Text2GQL、Text2Cypher等。索引加工的输入是Splliter切分好的文本块（未来也可以是多模态数据），输出是索引存储系统，是连接内容和存储的桥梁。
- 索引的存储接口（IndexStore）提供了向量存储和知识图谱两类实现，知识图谱接口依赖于图存储接口，也可以单独实现。从这里也能看出图存储系统的定位是数据基座而非搜索语义，它和向量存储不在同一个架构层次。
- 大模型服务的接口设计未在图中展开，我们可以将其看做索引加工过程依赖的内部能力。

![通用RAG建模](https://pic1.zhimg.com/80/v2-104fd654b0a239b4228b2cd7938ab6ba_1440w.png)

## 4.3 技术选型

综上所述，要构建一个完整的开源Graph RAG链路，离不开三个重要的子系统：一个可以支持RAG的AI工程框架，一个知识图谱系统和一个图存储系统。开源的AI工程框架有诸多选型： [LangChain](https://github.com/langchain-ai/langchain) 、 [LlamaIndex](https://github.com/run-llama/llama_index) 、 [RAGFlow](https://github.com/infiniflow/ragflow) 、 [DB-GPT](https://github.com/eosphoros-ai/DB-GPT) 等。知识图谱系统有： [Jena](https://github.com/apache/jena) 、 [RDF4J](https://github.com/eclipse-rdf4j/rdf4j) 、 [Oxigraph](https://github.com/oxigraph/oxigraph) 、 [OpenSPG](https://github.com/OpenSPG/openspg) 等。图存储系统有 [Neo4j](https://github.com/neo4j/neo4j) 、 [JanusGraph](https://github.com/JanusGraph/janusgraph) 、 [NebulaGraph](https://github.com/vesoft-inc/nebula) 、 [TuGraph](https://github.com/TuGraph-family/tugraph-db) 等。

而作为蚂蚁首个对外开源的Graph RAG框架，我们采用蚂蚁全自主的开源产品：DB-GPT + OpenSPG + TuGraph。  
![蚂蚁Graph RAG开源方案](https://picx.zhimg.com/80/v2-2192e6d1fdd3c4a2a430001ed0e51e4b_1440w.png)

### 4.3.1 AI工程框架（@DB-GPT）

DB-GPT是一个开源的AI原生数据应用开发框架，目的是构建大模型领域的基础设施，通过开发多模型管理(SMMF)、Text2SQL效果优化、RAG框架以及优化、Multi-Agents框架协作、AWEL(智能体工作流编排)等多种技术能力，让围绕数据库构建大模型应用更简单，更方便。  
![DB-GPT技术架构](https://picx.zhimg.com/80/v2-95c44967f7f2bfb3add1ea535c203351_1440w.png)

### 4.3.2 知识图谱（@OpenSPG）

OpenSPG是蚂蚁集团结合多年金融领域多元场景知识图谱构建与应用业务经验的总结，并与OpenKG联合推出的基于SPG(Semantic-enhanced Programmable Graph)框架研发的知识图谱引擎。  
![OpenSPG技术架构](https://pica.zhimg.com/80/v2-627891a405b406c20f9ac75331a9a252_1440w.png)

### 4.3.3 图数据库（@TuGraph）

TuGraph是蚂蚁集团与清华大学联合研发的大规模图处理系统，构建了包含图数据库、图计算引擎、图机器学习、图研发平台的完善图技术体系。支持海量多源的关联数据的实时处理，显著提升数据分析效率，支撑了蚂蚁支付、安全、社交、公益、数据治理等300多个场景应用，多次打破图数据库性能基准测试LDBC-SNB世界纪录，并跻身IDC中国图数据库市场领导者象限。  
![TuGraph技术架构](https://picx.zhimg.com/80/v2-35ecf150edd5d39b0655bf9dac3c7deb_1440w.png)

## 5\. 开源技术方案

在DB-GPT的 [v0.5.6](https://github.com/eosphoros-ai/DB-GPT/releases/tag/v0.5.6) 版本中，我们提供了完整的Graph RAG框架实现（ [PR 1506](https://github.com/eosphoros-ai/DB-GPT/pull/1506) ）。接下来我们结合这个PR，阐述Graph RAG的关键实现细节。  
![PR-1506：DB-GPT支持了Graph RAG框架](https://pica.zhimg.com/80/v2-f58ce74fc7ab8a73aa434a57a8d14961_1440w.png)

## 5.1 索引

索引加工的统一抽象是 `TransformerBase` 接口，目前提供了嵌入、抽取、翻译三类转换器。而图索引的构建，则通过三元组提取器 `TripletExtractor` 来实现。  
![TransformerBase接口的继承树](https://pic1.zhimg.com/80/v2-75be864cc3f969dfd615f2c60980bca8_1440w.png)

`ExtractorBase` 接口负责信息提取的职责，当下已有的三元组提取器和关键词提取器都依赖了大模型能力，所以抽象类 `LLExtractor` 负责与LLM交互的公共逻辑，具体的实现类只需要提供提示词模板和结果解析即可。三元组提取器 `TripletExtractor` 的提示词模板（受LlamaIndex启发），核心理念是通过few-shot样本引导大模型生成三元组结构。

```python
TRIPLET_EXTRACT_PT = (
    "Some text is provided below. Given the text, "
    "extract up to knowledge triplets as more as possible "
    "in the form of (subject, predicate, object).\n"
    "Avoid stopwords.\n"
    "---------------------\n"
    "Example:\n"
    "Text: Alice is Bob's mother.\n"
    "Triplets:\n(Alice, is mother of, Bob)\n"
    ...TL;DR...
    "Text: Philz is a coffee shop founded in Berkeley in 1982.\n"
    "Triplets:(Philz, is, coffee shop)\n(Philz, founded in, Berkeley)\n(Philz, founded in, 1982)\n"
    "---------------------\n"
    "Text: {text}\n"
    "Triplets:\n"
)
```

大模型让三元组抽取变成了一件非常简单的事情，但是要提高三元组的抽取质量也不是一件容易的事情。最简单的是通过提示词工程不断优化提示词模板，让通用大模型给出更理想的答案。另外使用专有的知识抽取大模型（如OneKE）可以取得更好的效果，这部分工作还在进行中，我们期望看到 `OnekeExtractor` 的社区贡献早日发布。

## 5.2 存储

索引存储的统一抽象是 `IndexStoreBase` 接口，目前提供了向量、图、全文三类索引实现。知识图谱接口 `KnowledgeGraphBase` 是Graph RAG的存储底座，目前DB-GPT内置的 `BuiltinKnowledgeGraph` 实现就是基于文本大模型能力构建的， `OpenSPG` 的接入工作已经在逐步推进。  
![IndexStoreBase接口的继承树](https://picx.zhimg.com/80/v2-290e4a95ff2406822cba9c83255f51c7_1440w.png)

知识图谱提供了和向量数据库同样的接口，让知识的存取过程透明化。文档内容经过三元组解析器 `_triplet_extractor` 解析后，直接写入图存储 `_graph_store` 。

```python
async def aload_document(self, chunks: List[Chunk]) -> List[str]:
    """Extract and persist triplets to graph store.
    Args:
        chunks: List[Chunk]: document chunks.
    Return:
        List[str]: chunk ids.
    """
    for chunk in chunks:
        triplets = await self._triplet_extractor.extract(chunk.content)
        for triplet in triplets:
            self._graph_store.insert_triplet(*triplet)
        logger.info(f"load {len(triplets)} triplets from chunk {chunk.chunk_id}")
    return [chunk.chunk_id for chunk in chunks]
```

图存储接口 `GraphStoreBase` 提供统一的图存储抽象，目前内置了 `MemoryGraphStore` 和 `TuGraphStore` 的实现，分别用于本地测试和生产部署，并预留了 `Neo4jStore` 的扩展点。  
![GraphStoreBase接口的继承树](https://picx.zhimg.com/80/v2-f58f03b21f29b540058cff82c27113cd_1440w.png)

具体的图存储提供了三元组写入的实现，一般会调用图数据库的查询语言来完成。例如 `TuGraphStore` 会根据三元组生成具体的Cypher语句并执行。

```python
def insert_triplet(self, subj: str, rel: str, obj: str) -> None:
    """Add triplet."""
    ...TL;DR...
    subj_query = f"MERGE (n1:{self._node_label} {{id:'{subj}'}})"
    obj_query = f"MERGE (n1:{self._node_label} {{id:'{obj}'}})"
    rel_query = (
        f"MERGE (n1:{self._node_label} {{id:'{subj}'}})"
        f"-[r:{self._edge_label} {{id:'{rel}'}}]->"
        f"(n2:{self._node_label} {{id:'{obj}'}})"
    )
    self.conn.run(query=subj_query)
    self.conn.run(query=obj_query)
    self.conn.run(query=rel_query)
```

## 5.3 检索

接口 `ExtractorBase` 的另一个实现则是关键词抽取器 `KeywordExtractor` ，负责提取用户问题中涉及的实体关键词，它也是借助大模型的能力实现的，同样继承于 `LLExtractor` ，提示词模板如下。

```python
KEYWORD_EXTRACT_PT = (
    "A question is provided below. Given the question, extract up to "
    "keywords from the text. Focus on extracting the keywords that we can use "
    "to best lookup answers to the question.\n"
    "Generate as more as possible synonyms or alias of the keywords "
    "considering possible cases of capitalization, pluralization, "
    "common expressions, etc.\n"
    "Avoid stopwords.\n"
    "Provide the keywords and synonyms in comma-separated format."
    "Formatted keywords and synonyms text should be separated by a semicolon.\n"
    "---------------------\n"
    "Example:\n"
    "Text: Alice is Bob's mother.\n"
    "Keywords:\nAlice,mother,Bob;mummy\n"
    "Text: Philz is a coffee shop founded in Berkeley in 1982.\n"
    "Keywords:\nPhilz,coffee shop,Berkeley,1982;coffee bar,coffee house\n"
    "---------------------\n"
    "Text: {text}\n"
    "Keywords:\n"
)
```

关键词的抽取涉及到文本中实体识别技术，在构造提示词时需要考虑单词的大小写、别称、同义词等情况，这部分还有很大的优化空间。另外，借助于模型微调直接翻译自然语言到图查询语句也是值得探索的方向。

图存储接口 `GraphStoreBase` 提供了基于关键词的探索接口 `explore` ，会根据抽取的关键词召回局部子图。

```python
@abstractmethod
def explore(
    self,
    subs: List[str],
    direct: Direction = Direction.BOTH,
    depth: Optional[int] = None,
    fan: Optional[int] = None,
    limit: Optional[int] = None,
) -> Graph:
    """Explore on graph."""
```

这里对接口含义做补充说明：

- subs：子图搜索的起点列表。
- direct：搜索方向，默认双向搜索，即同时探索引用和被引用关系。
- depth：搜索深度，控制图搜索的最大跳数，默认不做限制。
- fan：扇出限制，控制每一跳的最大邻居数，避免数据热点问题，默认不做限制。
- limit：结果边数限制，默认不做限制。
- 返回值：Graph接口类型，表示搜索结果子图，提供了便捷的点边更新API。

TuGraph的 `explore` 接口实现核心逻辑是将上述参数转化为Cypher查询语句，形如：

```python
query = (
    f"MATCH p=(n:{self._node_label})"
    f"-[r:{self._edge_label}*1..{depth}]-(m:{self._node_label}) "
    f"WHERE n.id IN {subs} RETURN p LIMIT {limit}"
)
```

## 5.4 生成

和其他向量数据库类似， `BuiltinKnowledgeGraph` 同样实现了 `IndexStoreBase` 的相似性查询接口。

```python
async def asimilar_search_with_scores(
    self,
    text,
    topk,
    score_threshold: float,
    filters: Optional[MetadataFilters] = None,
) -> List[Chunk]:
    """Search neighbours on knowledge graph."""
    if not filters:
        logger.info("Filters on knowledge graph not supported yet")

    # extract keywords and explore graph store
    keywords = await self._keyword_extractor.extract(text)
    subgraph = self._graph_store.explore(keywords, limit=topk)
    logger.info(f"Search subgraph from {len(keywords)} keywords")

    content = (
        "The following vertices and edges data after [Subgraph Data] "
        "are retrieved from the knowledge graph based on the keywords:\n"
        f"Keywords:\n{','.join(keywords)}\n"
        "---------------------\n"
        "You can refer to the sample vertices and edges to understand "
        "the real knowledge graph data provided by [Subgraph Data].\n"
        "Sample vertices:\n"
        "(alice)\n"
        "Sample edges:\n"
        "(alice)-[reward]->(alice)\n"
        "---------------------\n"
        f"Subgraph Data:\n{subgraph.format()}\n"
    )
    return [Chunk(content=content, metadata=subgraph.schema())]
```

关键词通过关键词抽取器 `_keyword_extractor` 完成，抽取到的关键词传递给图存储对象 `_graph_store` 进行子图探索，探索结果子图直接格式化到提示词上下文字符串 `content` 内。

细心的读者可以发现，子图探索的结果直接封装为 `Graph` 接口类型，我们甚至还提供了一个 `MemoryGraph` 工具类实现。这样实现图探索接口时，就无需将查询结果转化为Path/Table等内存不友好的格式了，同时也降低了提示词中编码子图数据的token开销。当然这是建立大模型对Graph数据结构原生的理解基础上，我们相信这是当下主流大模型的基本能力。  
![Graph接口的核心API](https://pic1.zhimg.com/80/v2-a9c3f2efc37d4d59d8e8df519f2cf553_1440w.png)

## 5.5 测试

我们使用《变形金刚》的故事材料 [tranformers\_story.md](https://github.com/eosphoros-ai/DB-GPT/blob/main/examples/test_files/tranformers_story.md) 作为测试文本，验证DB-GPT上Graph RAG的效果。具体操作手册见DB-GPT的文档 [《Graph RAG User Manual》](https://docs.dbgpt.site/docs/latest/cookbook/rag/graph_rag_app_develop) 。

启动DB-GPT后，新增Knowledge Space，选择Knowledge Graph存储类型。上传tranformers\_story.md后切片自动构建图索引。  
![创建知识图谱](https://pic1.zhimg.com/80/v2-db0e5d8a4719c8162c74bfaaf55ce29d_1440w.png)

构建好的知识图谱支持快速预览。  
![知识图谱预览](https://picx.zhimg.com/80/v2-cb57ce4fe659c46dd8c9aadfb199663c_1440w.png)

基于知识图谱的对话测试。  
![知识图谱对话](https://picx.zhimg.com/80/v2-774ee87f37fc19dd68499850fa952a23_1440w.png)

## 6\. 优化方向

其实大家在对DB-GPT上Graph RAG实现进行初步的测试后，会发现当下仍有不少体验问题。不避讳的讲，这里除了功能完善度的原因之外，还有Graph RAG自身设计上的不足，这也为后续的进一步优化方向提供了思路。

**文章\[26\]《From RAG to GraphRAG...》** 总结了Graph RAG的不足：

> GraphRAG, like RAG, has clear limitations, which include how to form graphs, generate queries for querying these graphs, and ultimately decide how much information to retrieve based on these queries. The main challenges are ‘query generation’, ‘reasoning boundary’, and ‘information extraction’.

总的来看分为三大类：

1. **信息抽取** ：如何构建高质量的知识图谱？
2. **查询生成** ：如何在生成知识图谱上的查询？
3. **推理边界** ：如何限制查询结果的规模？

像前边提到的，知识抽取/关键词/查询语言的微调模型主要专注于信息抽取和查询生成。另外， **论文\[24\]《Reasoning on Graphs...》** 实现的基于图的推理增强框架（RoG）则是在推理边界方向尝试的创新（思路有点类似RAT）：  
![RoG：基于图的推理增强](https://picx.zhimg.com/80/v2-edca3e71b652d017ec35d288607bb1fe_1440w.png)

当然上述三个阶段也可以被简化合并为两个阶段：内容索引阶段和检索生成阶段。我们就这两个大的阶段分别讨论Graph RAG后续可能的优化方向和思路。

## 6.1 内容索引阶段

Graph RAG的内容索引阶段主要目标便是构建高质量的知识图谱，值得继续探索的有以下方向：

- **图谱元数据** ：从文本到知识图谱，是从非结构化信息到结构化信息的转换的过程，虽然图一直被当做半结构化数据，但有结构的LPG（Labeled Property Graph）除了有利于图存储系统的性能优化，还可以协助大模型更好地理解知识图谱的语义，帮助其生成更准确的查询。
- **知识抽取微调** ：通用大模型在三元组的识别上实际测试下来仍达不到理想预期，针对知识抽取的微调模型反而表现出更好地效果，如前面提到的OneKE。
- **图社区总结** ：这部分源自于微软的Graph RAG的研究工作，通过构建知识图谱时生成图社区摘要，以解决知识图谱在面向总结性查询时“束手无策”的问题。另外，同时结合图社区总结与子图明细可以生成更高质量的上下文。
- **多模态知识图谱** ：多模态知识图谱可以大幅扩展Graph RAG知识库的内容丰富度，对客观世界的数据更加友好，浙大的 [MyGO](https://arxiv.org/abs/2404.09468) 框架提出的方法提升MMKGC（Multi-modal Knowledge Graph Completion）的准确性和可靠性。Graph RAG可以借助于MMKG（Multi-modal Knowledge Graph）和MLLM（Multi-modal Large Language Model）实现更全面的多模态RAG能力。
- **混合存储** ：同时使用向量/图等多种存储系统，结合传统RAG和Graph各自的优点，组成混合RAG。参考 **文章\[27\]《GraphRAG: Design Patterns...》** 提出的多种Graph RAG架构，如图学习语义聚类、图谱向量双上下文增强、向量增强图谱搜索、混合检索、图谱增强向量搜索等，可以充分利用不同存储的优势提升检索质量。

![混合检索的Graph RAG](https://picx.zhimg.com/80/v2-730237cbcf16bf1694d95de1e663d0bc_1440w.png)

## 6.2 检索生成阶段

Graph RAG的检索生成阶段主要目标便是从知识图谱上召回高质量上下文，值得继续探索的有以下方向：

- **图语言微调** ：使用自然语言在知识图谱上做召回，除了基本的关键词搜索方式，还可以尝试使用图查询语言微调模型，直接将自然语言翻译为图查询语句，这里需要结合图谱的元数据以获得更准确的翻译结果。过去，我们在 [Text2GQL](https://mp.weixin.qq.com/s/rZdj8TEoHZg_f4C-V4lq2A) 上做了一些初步的工作。
- **混合RAG** ：这部分与前边讲过的混合存储是一体的，借助于底层的向量/图/全文索引，结合关键词/自然语言/图语言多种检索形式，针对不同的业务场景，探索高质量Graph RAG上下文的构建。
- **测试验证** ：Graph RAG的测试和验证可以参考传统RAG的Benchmark方案，如 [RAGAS](https://arxiv.org/abs/2309.15217) 、 [ARES](https://arxiv.org/abs/2311.09476) 、 [RECALL](https://arxiv.org/abs/2311.08147) 、 [RGB](https://arxiv.org/abs/2309.01431) 、 [CRUD-RAG](https://arxiv.org/abs/2401.17043v2) 等。
- **RAG智能体** ：从某种意义上说，RAG其实是Agent的简化形式（知识库可以看到Agent的检索工具），同时当下我们也看到RAG对记忆和规划能力的集成诉求（如RAT/RoG等），因此未来RAG向带有记忆和规划能力的智能体架构演进几乎是必然趋势。另外，Agent自身需要的长期记忆存储也会反向依赖RAG的知识库，所以RAG与Agent其实是相辅相成、互相促进的。

## 7\. 尾记

通过以上介绍，相信大家对RAG到Graph RAG的技术演进有了更进一步的了解，并且基于RAG的索引、检索、生成三个基本阶段抽象出了通用的RAG框架，兼容了Vector、Graph、FullText等多种索引形式，最终在开源技术中完整落地。最后通过探讨Graph RAG未来的优化与演进方向，总结了内容索引和检索生成阶段的不同改进思路，以及RAG向Agent架构的演化趋势。Graph RAG是个相对新颖AI工程领域，需要探索和改进的工作还有很多要做，我们诚邀DB-GPT/OpenSPG/TuGraph的广大开发者们一起参与共建。

前不久Jerry Liu（LlamaIndex CEO）在技术报告《Beyond RAG: Building Advanced Context-Augmented LLM Applications》中也抛出了“RAG的未来是Agent”相似观点。所以，无论是“RAG for Agents”还是“Agents for RAG”，亦或是“从RAG到Graph RAG再到Agents”，目光可及的是智能体将是未来AI应用的主旋律。

## 8\. 参考资料

1. RALM\_Survey： [https://github.com/2471023025/RALM\_Survey](https://github.com/2471023025/RALM_Survey)
2. Retrieval-Augmented Generation for Large Language Models: A Survey： [https://arxiv.org/abs/2312.10997](https://arxiv.org/abs/2312.10997)
3. A Survey on Retrieval-Augmented Text Generation for Large Language Models： [https://arxiv.org/abs/2404.10981](https://arxiv.org/abs/2404.10981)
4. Retrieving Multimodal Information for Augmented Generation: A Survey： [https://arxiv.org/abs/2303.10868](https://arxiv.org/abs/2303.10868)
5. Evaluation of Retrieval-Augmented Generation: A Survey： [https://arxiv.org/abs/2405.07437](https://arxiv.org/abs/2405.07437)
6. GFMPapers： [https://github.com/BUPT-GAMMA/GFMPapers](https://github.com/BUPT-GAMMA/GFMPapers)
7. REALM: Retrieval-Augmented Language Model Pre-Training： [https://arxiv.org/abs/2002.08909](https://arxiv.org/abs/2002.08909)
8. RAT: Retrieval Augmented Thoughts Elicit Context-Aware Reasoning in Long-Horizon Generation： [https://arxiv.org/abs/2403.05313](https://arxiv.org/abs/2403.05313)
9. RAG and RAU: A Survey on Retrieval-Augmented Language Model in Natural Language Processing： [https://arxiv.org/pdf/2404.19543](https://arxiv.org/pdf/2404.19543)
10. RA-DIT: Retrieval-Augmented Dual Instruction Tuning： [https://arxiv.org/abs/2310.01352](https://arxiv.org/abs/2310.01352)
11. RAFT: Adapting Language Model to Domain Specific RAG： [https://arxiv.org/abs/2403.10131](https://arxiv.org/abs/2403.10131)
12. MuRAG: Multimodal Retrieval-Augmented Generator for Open Question Answering over Images and Text： [https://arxiv.org/abs/2210.02928](https://arxiv.org/abs/2210.02928)
13. Corrective Retrieval Augmented Generation： [https://arxiv.org/abs/2401.15884](https://arxiv.org/abs/2401.15884)
14. Full Fine-Tuning, PEFT, Prompt Engineering, and RAG: Which One Is Right for You?： [https://deci.ai/blog/fine-tuning-peft-prompt-engineering-and-rag-which-one-is-right-for-you/](https://deci.ai/blog/fine-tuning-peft-prompt-engineering-and-rag-which-one-is-right-for-you/)
15. An Easy Introduction to Multimodal Retrieval-Augmented Generation： [https://developer.nvidia.com/blog/an-easy-introduction-to-multimodal-retrieval-augmented-generation/](https://developer.nvidia.com/blog/an-easy-introduction-to-multimodal-retrieval-augmented-generation/)
16. Towards Long Context RAG： [https://www.llamaindex.ai/blog/towards-long-context-rag](https://www.llamaindex.ai/blog/towards-long-context-rag)
17. Full Fine-Tuning, PEFT, Prompt Engineering, and RAG: Which One Is Right for You?： [https://deci.ai/blog/fine-tuning-peft-prompt-engineering-and-rag-which-one-is-right-for-you/](https://deci.ai/blog/fine-tuning-peft-prompt-engineering-and-rag-which-one-is-right-for-you/)
18. Advance RAG- Improve RAG performance： [https://luv-bansal.medium.com/advance-rag-improve-rag-performance-208ffad5bb6a](https://luv-bansal.medium.com/advance-rag-improve-rag-performance-208ffad5bb6a)
19. Advanced Retrieval-Augmented Generation: From Theory to LlamaIndex Implementation： [https://towardsdatascience.com/advanced-retrieval-augmented-generation-from-theory-to-llamaindex-implementation-4de1464a9930](https://towardsdatascience.com/advanced-retrieval-augmented-generation-from-theory-to-llamaindex-implementation-4de1464a9930)
20. RAGFlow： [https://github.com/infiniflow/ragflow](https://github.com/infiniflow/ragflow)
21. LangChain RAG： [https://python.langchain.com/v0.1/docs/use\_cases/question\_answering/](https://python.langchain.com/v0.1/docs/use_cases/question_answering/)
22. From Local to Global: A Graph RAG Approach to Query-Focused Summarization： [https://arxiv.org/abs/2404.16130](https://arxiv.org/abs/2404.16130)
23. Seven Failure Points When Engineering a Retrieval Augmented Generation System： [https://arxiv.org/abs/2401.05856](https://arxiv.org/abs/2401.05856)
24. Reasoning on Graphs: Faithful and Interpretable Large Language Model Reasoning： [https://arxiv.org/abs/2310.01061](https://arxiv.org/abs/2310.01061)
25. GraphRAG: Unlocking LLM discovery on narrative private data： [https://www.microsoft.com/en-us/research/blog/graphrag-unlocking-llm-discovery-on-narrative-private-data/](https://www.microsoft.com/en-us/research/blog/graphrag-unlocking-llm-discovery-on-narrative-private-data/)
26. From RAG to GraphRAG, What is the GraphRAG and why i use it?： [https://medium.com/@jeongiitae/from-rag-to-graphrag-what-is-the-graphrag-and-why-i-use-it-f75a7852c10c](https://medium.com/@jeongiitae/from-rag-to-graphrag-what-is-the-graphrag-and-why-i-use-it-f75a7852c10c)
27. GraphRAG: Design Patterns, Challenges, Recommendations： [https://gradientflow.com/graphrag-design-patterns-challenges-recommendations/](https://gradientflow.com/graphrag-design-patterns-challenges-recommendations/)
28. lettria： [https://www.lettria.com/features/graphrag](https://www.lettria.com/features/graphrag)
29. Implementing GraphRAG for Query-Focused Summarization： [https://dev.to/stephenc222/implementing-graphrag-for-query-focused-summarization-47ib](https://dev.to/stephenc222/implementing-graphrag-for-query-focused-summarization-47ib)
30. LlamaIndex Graph RAG： [https://docs.llamaindex.ai/en/stable/examples/query\_engine/knowledge\_graph\_rag\_query\_engine/](https://docs.llamaindex.ai/en/stable/examples/query_engine/knowledge_graph_rag_query_engine/)
31. DB-GPT Graph RAG： [https://docs.dbgpt.site/docs/latest/cookbook/rag/graph\_rag\_app\_develop](https://docs.dbgpt.site/docs/latest/cookbook/rag/graph_rag_app_develop)
32. RAGAS: Automated Evaluation of Retrieval Augmented Generation： [https://arxiv.org/abs/2309.15217](https://arxiv.org/abs/2309.15217)
33. Benchmarking Large Language Models in Retrieval-Augmented Generation： [https://arxiv.org/abs/2309.01431](https://arxiv.org/abs/2309.01431)
34. CRUD-RAG: A Comprehensive Chinese Benchmark for Retrieval-Augmented Generation of Large Language Models： [https://arxiv.org/abs/2401.17043v2](https://arxiv.org/abs/2401.17043v2)
35. ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems： [https://arxiv.org/abs/2311.09476](https://arxiv.org/abs/2311.09476)
36. RECALL: A Benchmark for LLMs Robustness against External Counterfactual Knowledge： [https://arxiv.org/abs/2311.08147](https://arxiv.org/abs/2311.08147)
37. MyGO: Discrete Modality Information as Fine-Grained Tokens for Multi-modal Knowledge Graph Completion： [https://arxiv.org/abs/2404.09468](https://arxiv.org/abs/2404.09468)
38. OneKE： [https://github.com/zjunlp/DeepKE/blob/main/example/llm/OneKE.md](https://github.com/zjunlp/DeepKE/blob/main/example/llm/OneKE.md)
39. Apache Jena： [https://github.com/apache/jena](https://github.com/apache/jena)
40. Eclipse RDF4J： [https://github.com/eclipse-rdf4j/rdf4j](https://github.com/eclipse-rdf4j/rdf4j)
41. Oxigraph： [https://github.com/oxigraph/oxigraph](https://github.com/oxigraph/oxigraph)
42. OpenSPG： [https://github.com/OpenSPG/openspg](https://github.com/OpenSPG/openspg)
43. Neo4j： [https://github.com/neo4j/neo4j](https://github.com/neo4j/neo4j)
44. JanusGraph： [https://github.com/JanusGraph/janusgraph](https://github.com/JanusGraph/janusgraph)
45. NebulaGraph： [https://github.com/vesoft-inc/nebula](https://github.com/vesoft-inc/nebula)
46. TuGraph： [https://github.com/TuGraph-family/tugraph-db](https://github.com/TuGraph-family/tugraph-db)