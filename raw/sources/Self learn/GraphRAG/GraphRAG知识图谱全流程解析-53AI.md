![FDE知识库](https://static.53ai.com/uploads/20240717/b4d4dcfc73a94e6379e5f22698fa6744.webp)

FDE知识库

学习大模型的前沿技术与行业落地应用

发布日期：2024-09-06 08:59:19 浏览次数： 4755

在我们上次的交流中，我提及了GraphRAG这个神秘的概念和基础使用。不记得的可以回去阅读：最近爆火的GraphRAG是什么，真的能用于商业应用吗？。我会在接下来过程中用几篇图文丰富的文章，带领你一起彻底解读GraphRAG，并揭示其内部工作流程。

今天，我要和你分享的是如何用GraphRAG从一个普通的txt文件中创建知识图谱，准备好了吗？那就让我们开始吧！

## GraphRAG解决了什么问题

当你问：“这个数据集的主题是什么？”这类高级别、概括性的问题时，传统的RAG可能就会束手无策。为什么呢？那是因为这本质上是一个聚焦于查询的总结性任务(Query-Focused Summarization，QFS)，而不是一个明确的检索任务。

我知道你现在可能在想，“那我们该如何解决这个问题呢？”好消息是，有人已经找到了解决方案，而且还被详细地描述在论文中：

```
In contrast with related work that exploits the structured retrieval and traversal affordances of graph indexes (subsection 4.2)，we focus on a previously unexplored quality of graphs in this context: their inherent modularity (Newman，2006) and the ability of community detection algorithms to partition graphs into modular communities of closely-related nodes (e.g.，Louvain，Blondel et al.，2008; Leiden，Traag et al.，2019). LLM-generated summaries of these community descriptions provide complete coverage of the underlying graph index and the input documents it represents. Query-focused summarization of an entire corpus is then made possible using a map-reduce approach: first using each community summary to answer the query independently and in parallel，then summarizing all relevant partial answers into a final global answer.
```

简单来说，就是利用社区检测算法（如Leiden算法）将整个知识图谱划分模块化的社区(包含相关性较高的节点)，然后大模型自下而上对社区进行摘要，最终再采取map-reduce方式实现QFS: 每个社区先并行执行Query，最终汇总成全局性的完整答案.

与其他RAG系统类似，GraphRAG整个Pipeline也可划分为索引(Indexing)与查询(Query)两个阶段。索引过程利用LLM提取出节点（如实体）、边（如关系）和协变量（如 claim），然后利用社区检测技术对整个知识图谱进行划分，再利用LLM进一步总结。

鉴于篇幅原因，今天的这篇文章主要聚焦于indexing, 下一篇文章会介绍Query的工作原理，敬请期待！

## pipeline

当你运行 "poetry run poe index" 命令时，它会执行 graphrag.index.cli 目录下的 index\_cli 入口函数。在 GraphRAG 中，构建知识图谱被视为一个流水线（pipeline）过程，这个流水线包含多个工作流（workflow），例如文本分块、使用LLM来识别实体等。pipeline涵盖的workflow是通过 settings.yml 配置文件进行指定的。index\_cli 的主要任务是创建 pipeline\_config 对象，并利用 run\_pipeline\_with\_config 函数来运行流水线。所以，我们可以将整个流程概括如下：

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=88815&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL21tYml6X3BuZy9YQTd2djdBaE5lbmFRTTRxV0w4RTBrQjd5aGs0eDRFZE9kMWhSaWIyanJYblZMRmVnV3JXemIyUUhFS1YzQWwxbllpYnNvZXlPQ2dxYmlhUzJnUGZwajFQZy82NDA/d3hfZm10PXBuZyZhbXA=;from=appmsg)

整个过程体现了自上而下的编程思想——每个结果依赖于更底层函数的执行，从顶部开始调用，然后逐步深入到底层函数。这样的结构使得整体流程清晰明了，这也是我们平时在项目开发中的编程思路。

## workflow

讨论workflow之前，先简单了解下项目使用的另一个框架: DataShaper 是微软开源的一款用于执行工作流处理的库，内置了很多组件(专业名词叫做Verb). 通过定义一个数据处理的工作流，你可以对输入的数据（比如Pandas的DataFrame）定义一系列数据操作的 **动作** （DataShaper中称作 **Verb** ）、 **参数与步骤** ，执行这个工作流即可完成数据处理过程。在DataShaper中提供了很多开箱即用的Verb，你也可以自定义Verb。多个子工作流也可以组合定义成一个更大的工作流。

当你通过命令行执行完indexing之后，你会看到如下的输出内容:

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=88815&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL21tYml6X3BuZy9YQTd2djdBaE5lbmFRTTRxV0w4RTBrQjd5aGs0eDRFZEFIWm9HVk5ndkQwaWFSZHJZZ05UMXVFbDhycHdudDc1MzhCNDhtdUV1cDdqVXF5OVBUM2xIdXcvNjQwP3d4X2ZtdD1wbmcmYW1w;from=appmsg)

从这个可以看出GraphRAG的indexing共经历了14个workflow:

1. create\_base\_documents
2. create\_final\_documents
3. create\_base\_text\_units
4. join\_text\_units\_to\_entity\_ids
5. join\_text\_units\_to\_relationship\_ids
6. create\_final\_text\_units
7. create\_base\_extracted\_entities
8. create\_summarized\_entities
9. create\_base\_entity\_graph
10. create\_final\_entities
11. create\_final\_relationships
12. create\_final\_nodes
13. create\_final\_communities
14. create\_final\_community\_reports

基本的处理过程如下：首先，它会将输入文本进行拆分，然后提取实体与关系，生成摘要信息，并根据这些信息构建内存中的图（Graph）结构。接下来，它会从这个图中识别出各个社区，为每个社区创建报告，并在图中创建文本块节点和文档节点。

当然，以上只是些核心步骤，但在实际的处理过程中还涉及到许多细节处理，比如生成嵌入（embedding），持久化到存储，以及应用不同的算法策略等等。当然这些并不是这篇文章的重点。如果感兴趣，评论区留言我会单独开别的文章来讲解。

这里可以多说一点，这14个workflow其实又可以进一步细分为四大类：

1. 关于文档的document\_workflows
- create\_base\_document
- craete\_final\_documents
- 关于文档单元的text\_unit\_workflows
- create\_base\_text\_units
	- join\_text\_units\_to\_entity\_ids
	- join\_text\_units\_to\_relationship\_ids
	- create\_final\_text\_units
- 构建图谱的graph\_workflows
- create\_base\_extracted\_entities
	- create\_summarized\_entities
	- create\_base\_entity\_graph
	- create\_final\_entities
	- create\_final\_relationships
	- create\_final\_nodes
- 社区聚类的community\_workflows
- create\_final\_communities
	- create\_final\_community\_reports

此外，各个工作流之间存在一定的依赖关系，形成了一个工作流流程图。输入数据为存放在 input 目录下的 txt 或 csv 文件(目前只支持这两种，后面我会自己支持更多格式)，经过这些工作流组成的流程图处理后，输出的结果就是最终构建的知识图谱。

接下来，我将以一个包含 "海贼王" 的 txt 文件为例(摘自百度百科)，逐步解析它经历的各个工作流，以及每个工作流的输入和输出是什么.

## 1\. create\_base\_text\_units

整个pipeline的入口输入在源码中是个叫dataset的变量，其存储的值Pandas **DataFrame** ，Pandas **DataFrame** 可以简单看做是一张table, 这个table的每一行代表一个txt文件，text列是txt文件的内容：

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=88815&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL21tYml6X3BuZy9YQTd2djdBaE5lbmFRTTRxV0w4RTBrQjd5aGs0eDRFZE5sY3VvaWJpYU0wVDd2bXBDbUdGWTNTN01SZ0xGQlJjekJpYzFBa1p3MER5eURLVmFpYnRHaWNSQnhBLzY0MD93eF9mbXQ9cG5nJmFtcA==;from=appmsg)

create\_base\_text\_units 是整个pipeline的第一个workflow, 它的作用是对txt的文件内容按照特定的策略进行切分(chunking)操作，目前只支持两种策略: 按照token和按照sentence，默认是按照token, chunk操作的输入是text:

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=88815&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL21tYml6X3BuZy9YQTd2djdBaE5lbmFRTTRxV0w4RTBrQjd5aGs0eDRFZEpFY29mVmxJVFFpYUt6QUZHR2d3NUlQZU9lOUhpYWF4eld4UUxGVTB2UG56UWljSUR5bEN0d2ZpY1EvNjQwP3d4X2ZtdD1wbmcmYW1w;from=appmsg)

对于一个text 经过chunking操作后会得到多个chunks:

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=88815&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL21tYml6X3BuZy9YQTd2djdBaE5lbmFRTTRxV0w4RTBrQjd5aGs0eDRFZENPMk8yUE9IMjZPVnI4S1VsbGliNUZkczRFMGljWG9xSVM4VW9VTDFhaHE0SzhtVUxUUWhkYXdnLzY0MD93eF9mbXQ9cG5nJmFtcA==;from=appmsg)

Microsoft GraphRAG在索引构建的过程中其中间数据主要使用Pandas **DataFrame** 这种结构化类型进行交换, 可以简单理解为Mysql中的table，对DataFrame的一些操作比如select、join等可以类比mysql的select, join等sql语句来理解。

## 2\. create\_base\_extracted\_entities

一旦我们得到了相应的chunk，GraphRAG就会采用特定的策略从每个chunk来 **提取需要的实体entity** 。

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=88815&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL21tYml6X3BuZy9YQTd2djdBaE5lbmFRTTRxV0w4RTBrQjd5aGs0eDRFZG9wVkNiZU9hN2FXbHgzZkxoMXRpY1V0QzdFdmN5Y2Uyb000Rjd3SWlhSnJGUjlpYWljeFJLZHBnM0EvNjQwP3d4X2ZtdD1wbmcmYW1w;from=appmsg)

目前，GraphRAG支持两种抽取策略：

1. graph\_intelligence：这是默认的策略。
	2. nltk：另一种可选策略。

> 在源码中的ExtractEntityStrategyType里，尽管定义了一个名为“graph\_intelligence\_json”的枚举值，但是目前还未对它进行支持。

当处理多个数据块时，GraphRAG会并行调用LLM来抽取实体，而且默认情况下，它会选择使用多线程。不过，如果你想的话，也可以通过配置修改成asyncio模式。

在此流程中，GraphRAG会调用run\_extract\_entities进行实体抽取，该函数会利用目录下的entity\_extraction.txt中的prompt来调用LLM完成实体提取。默认的 entity\_extraction prompt 抽取的实体类型是 \['organization', 'person', 'geo', 'event'\]，你可以根据你的文件内容来修改settings.yml中entity\_extraction，后面我会介绍如何通过prompt tuning来自动适配prompt.

```
entity_extraction:
  ## llm: override the global llm settings for this task
  ## parallelization: override the global parallelization settings for this task
  ## async_mode: override the global async_mode settings for this task
  prompt: "prompts/entity_extraction.txt"
  entity_types: [organization,person,geo,event]
  max_gleanings: 1
```

我截取了其中一个chunk得到的LLM调用结果的部分内容：

```
("entity"<|>欧罗·杰克逊号<|>ORGANIZATION<|>欧罗·杰克逊号是罗杰海贼团的船只)
##
("entity"<|>白胡子<|>PERSON<|>白胡子是“顶上战争”之前的四皇之一，悬赏金为50亿4600万)
##
("entity"<|>百兽<|>PERSON<|>百兽是“顶上战争”之前和之后的四皇之一，悬赏金为46亿1110万)
##
("entity"<|>BIG MOM<|>PERSON<|>BIG MOM是“顶上战争”之前和之后的四皇之一，悬赏金为43亿8800万)
##
("entity"<|>红发<|>PERSON<|>红发是“顶上战争”之前和之后的四皇之一，悬赏金为40亿4890万)
##
("entity"<|>黑胡子海贼团<|>ORGANIZATION<|>黑胡子海贼团是黑胡子的势力)
##
("relationship"<|>弗兰奇<|>卡雷拉公司<|>弗兰奇设计的海贼船由卡雷拉公司协助制作<|>8)
##
("relationship"<|>草帽大船团<|>俊美海贼团<|>俊美海贼团是草帽大船团旗下的一个海贼团<|>7)
##
("relationship"<|>卡文迪许<|>俊美海贼团<|>卡文迪许是俊美海贼团的船长<|>9)
##
("relationship"<|>斯莱曼<|>俊美海贼团<|>斯莱曼是俊美海贼团的船员<|>8)
```

GraphRAG会对LLM的输出结果进行后处理post\_processing，最终形成Graph对象的。我们先看一下实体（entities），每一个实体都有四个主要的属性：name、description、source\_id 和 type。

1. Name：这是实体的名称。
	2. Description：对实体的描述。
	3. Source\_id：在此情况下，source\_id是指那些生成这个特定实体的数据块(chunk)的识别号。
	4. Type：实体的类型。

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=88815&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL21tYml6X3BuZy9YQTd2djdBaE5lbmFRTTRxV0w4RTBrQjd5aGs0eDRFZDIzQjIxRHdHeFlrY2liTFg3V0pxR1dHMHJZSzBHbndHRUFXaFRQT0RkbG9BTnl3ZVN4aWNZVllnLzY0MD93eF9mbXQ9cG5nJmFtcA==;from=appmsg)

每个chunk都生成对应的实体后，会把这些实体添加到一个列表entities中，并把每段chunk对应的表达图形结构的 **Graphml** 也放到一个列表entity\_graph中:

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=88815&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL21tYml6X3BuZy9YQTd2djdBaE5lbmFRTTRxV0w4RTBrQjd5aGs0eDRFZGliZ3U3aWMzTEN2Y2VHbnRyckh0ZktrbWx0aWNVa1pXM3VBSUJ6NElWWXU4eXdPY2tjdGd4VjlpYkEvNjQwP3d4X2ZtdD1wbmcmYW1w;from=appmsg)

> Microsoft GraphRAG在索引构建的过程中对于Graph数据的交换使用 **Graphml** （一种xml表示的graph）

这里有个情况需要考虑，不同的数据块（chunks）可能会抽取出相同的实体。比如说，第一个和第二个数据块都可能包含"草帽路飞"这个实体。这时候，GraphRAG会采用一种名为merge\_graphs的操作，把多个子图合并成一个新的大图。如果遇到相同的节点，那么GraphRAG就会执行concat操作，也就是将对应的属性和关系进行合并。

比如对于一个实体：'哥尔·D·罗杰'， 经过merge之后会包含多个description的列表: \['哥尔·D·罗杰是罗杰海贼团的船长', '哥尔·D·罗杰是被称为“海贼王”的男人，他在被行刑受死之前说了一句话，开启了“大海贼时代”'\]

通过merge\_graphs操作，GraphRAG能够有效地处理重复的实体，并把多个chunk对应的Graph整合成一个新的Graph，形成一个更加完善和详细的数据图:

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=88815&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL21tYml6X3BuZy9YQTd2djdBaE5lbmFRTTRxV0w4RTBrQjd5aGs0eDRFZGljYXVTaWFYemhMM3VFSmlhWUJBM3F5Mms4OGljY2lhTGtOdTdzd05kT0VCZWZXU2ljQU5WcVNKU0N0QS82NDA/d3hfZm10PXBuZyZhbXA=;from=appmsg)

## 3\. create\_summarized\_entities

通过merge\_graphs的操作，将多个子图合并到一个全新的大图之后，GraphRAG会进一步这个大图的节点(node)和关系(relationship)的描述(descriptions)进行总结。

这样做的目的是为了方便查询，因为查询时需要根据问题匹配知识库中的实体信息和关系信息时，只需要根据总结后的实体描述和关系描述就可以进行匹配了. 不然得遍历description list进行匹配。

GraphRAG目前支持的summarize的策略只有一种：graph\_intelligence。

summarize使用的prompt中文翻译如下：

```
你是一位负责生成以下提供数据的综合摘要的有用助手。
根据一个或两个实体，以及一系列描述，这些描述都与同一个实体或一组实体有关。
请将所有这些描述合并成一个单一的、全面的描述。确保包括所有描述中收集到的信息。
如果提供的描述存在矛盾，请解决这些矛盾，并提供一个单一的、连贯的摘要。
确保用第三人称写作，并包括实体名称，以便我们拥有完整的上下文。

#######
-数据-
实体: {entity_name}
描述列表: {description_list}
#######
输出:
```

执行summarize\_descriptions操作后，原来图形中的 **多个description** 就被整合为了 **一个** 全新的、详尽的描述。可以说，summarize\_descriptions是把前一步得到的Graph进行整理的过程，使得Graph更加清晰、准确。

经过summarize之后，上一个workflow create\_base\_extracted\_entities 得到的Graph被更进一步完善了：

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=88815&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL21tYml6X3BuZy9YQTd2djdBaE5lbmFRTTRxV0w4RTBrQjd5aGs0eDRFZGljYXVTaWFYemhMM3VFSmlhWUJBM3F5Mms4OGljY2lhTGtOdTdzd05kT0VCZWZXU2ljQU5WcVNKU0N0QS82NDA/d3hfZm10PXBuZyZhbXA=;from=appmsg)

生成这种摘要的好处是：可以借助嵌入embedding向量更有效与准确的对这些实体与关系进行检索。

## 4\. create\_base\_entity\_graph

这一步是做社群检查的: 将实体进行分类，拿三国举例，比如周瑜和孙策属于吴国，曹操和司马懿属于魏国，刘备和关羽属于蜀国，而吴国、魏国、蜀国都属于东汉，其中东汉是一个大社群，魏蜀吴是三个小社群，当执行查询时，可以指定社区的级别，如果指定的是低级别社群，那么查找的结果就比较微观，比如问三国时期有哪些著名人物，如果指定的社群为吴国，那么匹配的就只有周瑜和孙策，如果指定的社群为东汉，那么就能找到更多的著名人物。

create\_base\_entity\_graph这个workflow会对Graph应用应用层次聚类算法(对应源码中的cluster\_graph方法)， 在Graph中识别出层次结构和社区结构：一个Level对应多个community。

GraphRAG在源码中借助了 **Graspologic库** 实现的Leiden算法: Leiden算法通常比许多其他的社区检测算法更稳定，能更可靠地复现结果, 但是Leiden算法在某些情况下可能会比其他方法慢一些。

在这个workflow中先会进行run\_layout 布局分析，应用Leiden算法对nodes分社区，完成这些步骤后，每一个社区的节点都会被赋予以下属性：

1. Level：表示节点所在的层次。
	2. Cluster：表示节点所在社区的编号。
	3. Human\_readable\_id：这可以被看做是实体（entity）在同一个社区内的编码，从0开始

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=88815&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL21tYml6X3BuZy9YQTd2djdBaE5lbmFRTTRxV0w4RTBrQjd5aGs0eDRFZFJoaWF1WmtaYlgxeUI1UjE1TTdlRE9FVVpIZm5kUHBwMk90WjlpY05oRldTVXlDeWlhaWJ5b21UWmcvNjQwP3d4X2ZtdD1wbmcmYW1w;from=appmsg)

经过create\_base\_entity\_graph之后，Graph按照层级被划分出多个子图，每个子图对应一个level：

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=88815&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL21tYml6X3BuZy9YQTd2djdBaE5lbmFRTTRxV0w4RTBrQjd5aGs0eDRFZFBLNjlibjRNaDZ2MFNPUHlZOHh0VzUyRnFYTjU4aWFBaWNCOEJFaWJFQzdwWUlKRHcycTRUVWd2US82NDA/d3hfZm10PXBuZyZhbXA=;from=appmsg)

## 5\. create\_final\_entities

create\_final\_entities这个workflow的功能是对节点做embedding，方便进行之后的query。

在做embedding之前，为了更好地表示每个节点，我们将节点的'name'和'description'字段拼接起来，形成一个新的'name\_description'字段。这样，每个节点都将有一个通俗易懂，并且信息丰富的标签。

然后，我们把这个新生成的'name\_description'字段通过嵌入过程转换成一个向量表示。这种方法能够捕获和表示文本数据的复杂模式，也使得我们可以针对这些节点进行高效的计算和分析。

经过上面的一些图的修整之后，我们还需要对entity做进一步的embedding操作。在这之前，会经过embedding操作，embedding会对node的 name和description 拼接的 name: description 组成name\_description字段，对这个字段做embedding操作。

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=88815&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL21tYml6X3BuZy9YQTd2djdBaE5lbmFRTTRxV0w4RTBrQjd5aGs0eDRFZGljbE1kRWd4bm1pYm9mdzNKSTh2dFN6N3kwcHhQakwyUDJKeDJHSDdNZnRheE9Pb0J6WDlPNDVnLzY0MD93eF9mbXQ9cG5nJmFtcA==;from=appmsg)

经过embedding之后，新增了一列description\_embedding字段：

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=88815&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL21tYml6X3BuZy9YQTd2djdBaE5lbmFRTTRxV0w4RTBrQjd5aGs0eDRFZGFUQU5ORlpTbU9hSE1aTVJsalk4N0xYdGljb2liclU4QWxlNVZ3VGh0RVNHUkhocmtFWGJGUkJnLzY0MD93eF9mbXQ9cG5nJmFtcA==;from=appmsg)

## 6\. create\_final\_nodes

Network Visualization 阶段，由于生成的图谱一般不是一个平面图（可以通过在平面上绘制其顶点和边而不出现边的交叉），通过使用降维技术操作将非平面图映射到平面上，可以更直观地观察和理解数据的结构和模式。

在图论和网络分析中，图的布局算法（layout algorithm）用于将图中的节点和边在二维或三维空间中进行合理的排列和可视化。其主要目标是使图的结构和关系尽可能清晰地展示出来，以便于人类理解和分析。create\_final\_nodes会对Graph应用layout算法，GraphRAG目前支持两种算法：

1. umap：默认值
	2. zero

workflow的输入是create\_base\_entity\_graph的输出：

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=88815&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL21tYml6X3BuZy9YQTd2djdBaE5lbmFRTTRxV0w4RTBrQjd5aGs0eDRFZGNLQW9seGV5VU9TRzRGTFRYN1l0SlRDWkVWNUdMc25VcnlQRVlaMnp5QkZ5N25LeXFpYnQ5NlEvNjQwP3d4X2ZtdD1wbmcmYW1w;from=appmsg)

每个entity的所有属性现在长这样：

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=88815&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL21tYml6X3BuZy9YQTd2djdBaE5lbmFRTTRxV0w4RTBrQjd5aGs0eDRFZFhKZmRRYk9EU28xZG5hWVZacDV6WTJpY1lVVE01bVd0QklBNmlhU2dBSE5HdGNkT1ZFMUF5R0l3LzY0MD93eF9mbXQ9cG5nJmFtcA==;from=appmsg)

## 7\. create\_final\_communities

这个workflow用于创建community table, 步骤如下：

我们从第4步生成的create\_base\_entity\_graph中抽取节点数据，形成一个名为graph\_nodes的表：

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=88815&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL21tYml6X3BuZy9YQTd2djdBaE5lbmFRTTRxV0w4RTBrQjd5aGs0eDRFZGRRWGJkbXNjZWczVHM2M0p3ZFRSdUNMWVJBZGx2OTBoTzFDblRxSExmUHdvTW5tZkZhdWF2US82NDA/d3hfZm10PXBuZyZhbXA=;from=appmsg)

然后，我们同样从create\_base\_entity\_graph中提取边信息，生成另一个名为graph\_edges的表：

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=88815&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL21tYml6X3BuZy9YQTd2djdBaE5lbmFRTTRxV0w4RTBrQjd5aGs0eDRFZFp2dTBmajdQNkFzMU1CTFdzM1lsMXBWaHI5ZVFnZjBWVHZ4bk5reVZkV0FwbDFNaWNqTHNDV3cvNjQwP3d4X2ZtdD1wbmcmYW1w;from=appmsg)

然后，我们将graph\_nodes和graph\_edges进行left\_join操作，这个新生成的表命名为combined\_clusters：

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=88815&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL21tYml6X3BuZy9YQTd2djdBaE5lbmFRTTRxV0w4RTBrQjd5aGs0eDRFZGVvRkM3Ujg1eTVwWmthMlZpYUVUMEtaUlk2a1dpYUFtMEFtRkFjMlBuVTAyd0p1RlJHMHFxZGFBLzY0MD93eF9mbXQ9cG5nJmFtcA==;from=appmsg)

紧接着，我们对combined\_clusters进行进一步的聚合操作，同样是按照cluster和level进行分组。在这个过程中，我们会把edge的id\_2去重后组合成一个数组，命名为relationship\_ids；同时，也会把node的source\_id\_1去重后组合成另一个数组，命名为text\_unit\_ids：

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=88815&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL21tYml6X3BuZy9YQTd2djdBaE5lbmFRTTRxV0w4RTBrQjd5aGs0eDRFZHJiUkY1dVd5dk1GaWFaY3ZzNnJDcjJVS0RiSHIybFVGQ2paREhpYXo2T3h0bld1OUJMV3ZVNzd3LzY0MD93eF9mbXQ9cG5nJmFtcA==;from=appmsg)

以cluster = 1为例，通过text\_unit\_ids，我们能够知道这个社区来源于哪些chunk；通过relationship\_ids，我们则可以确定这个社区包含了哪些边。

最后，我们还会对上述数据进行一次处理，主要是生成每个社区的名称：

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=88815&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL21tYml6X3BuZy9YQTd2djdBaE5lbmFRTTRxV0w4RTBrQjd5aGs0eDRFZERBaWM0elM4QkVSQk00Y3FnYjZ4YmgxOTg5NjdIQ2xvNWZFOENVS2VkREpzaWNJZlZ0SUg1ZmJ3LzY0MD93eF9mbXQ9cG5nJmFtcA==;from=appmsg)

## 8\. join\_text\_units\_to\_entity\_ids

join\_text\_units\_to\_entity\_ids的作用是建立text\_unit到entity的映射关系。

首先，GraphRAG会提取出每个实体的"id"，以及表示实体来源的字段"text\_unit\_ids"。接着，我们对"text\_unit\_ids"进行“打平”操作，也就是将嵌套的数据结构转化为一维的形式。

然后，我们进行聚合操作。具体来说，我们会按照"text\_unit\_id"对数据进行分类，并把相同类别的实体id聚合成一个数组，命名为"entity\_ids"。

这样，在最终的结果中，每一条记录都会包含一个"text\_unit\_id"，以及一个与之关联的"entity\_ids"数组:

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=88815&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL21tYml6X3BuZy9YQTd2djdBaE5lbmFRTTRxV0w4RTBrQjd5aGs0eDRFZExTVE1pYlpMUzNRaWNRaDRVTVFvNmdyb3NybnY2VHdra1U2RzBSblJsSnlHVUZNaWNITGc0eUF6QS82NDA/d3hfZm10PXBuZyZhbXA=;from=appmsg)

## 9\. create\_final\_relationships

create\_final\_relationships用于创建relationship table, 步骤如下:

首先，我们从create\_base\_entity\_graph中得到的Graph提取出所有的边关系：

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=88815&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL21tYml6X3BuZy9YQTd2djdBaE5lbmFRTTRxV0w4RTBrQjd5aGs0eDRFZGdQVnZVaWJpY2RKbmNnQUM4dFBjb1lXQUd0WjQ2NW9rcWZ5bkwzaGxTc3RNU3VCc0RIdGRTRklnLzY0MD93eF9mbXQ9cG5nJmFtcA==;from=appmsg)

接下来，我们会对edge和nodes使用left\_join操作，在这个步骤中，我们将新增两列：source\_degree和target\_degree。这两列分别表示源实体和目标实体的度数，也就是每个实体连接的边的数量。

最后，我们会创建一个新的列"rank"。这个列的值是通过将source\_degree和target\_degree相加得到的。这样，我们就可以根据rank的值，了解每条边连接的两个实体的总度数:

| source | target | weight | description | text\_unit\_ids | id | human\_readable\_id | source\_degree | target\_degree | rank |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 蒙奇·D·路飞 | 草帽一伙 | 1.0 | 蒙奇·D·路飞是草帽一伙的船长和创立者 | \['2808e991f29115cba505836944beb514'\] | 392be891f8b649fabdc20e7bf549f669 | 0 | 11 | 19 | 30 |
| 蒙奇·D·路飞 | 香克斯 | 1.0 | 蒙奇·D·路飞为了实现与香克斯的约定而出海 | \['2808e991f29115cba505836944beb514'\] | 0111777c4e9e4260ab2e5ddea7cbcf58 | 1 | 11 | 2 | 13 |
| 蒙奇·D·路飞 | ONE PIECE | 1.0 | 蒙奇·D·路飞为了寻找传说中的大秘宝ONE PIECE而扬帆起航 | \['2808e991f29115cba505836944beb514'\] | 785f7f32471c439e89601ab81c828d1d | 2 | 11 | 1 | 12 |

## 10\. join\_text\_units\_to\_relationship\_ids

这个workflow和我们之前讨论过的join\_text\_units\_to\_entity\_ids非常相似，主要区别在于，现在我们是将text\_unit\_id映射到它所包含的relationship\_id，而不再是entity\_ids。

简单来说，我们的目标是理解每个text\_unit\_id（对应"chunk"）都包含了哪些关系（relationship）。为了实现这个目标，我们会创建一种映射关系，把每个text\_unit\_id连接到它所涉及的所有relationship\_id。结果将以类似于字典的形式呈现，其中键是text\_unit\_id，值是一个列表，包含了所有相关的relationship\_id：

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=88815&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL21tYml6X3BuZy9YQTd2djdBaE5lbmFRTTRxV0w4RTBrQjd5aGs0eDRFZEttQkpyVmliUGFxbWliOWp2S2RERzZSSmh4VklkM2RybnY0VXgyaWN6TzNjYlZjaWNib05zQm1ZOFEvNjQwP3d4X2ZtdD1wbmcmYW1w;from=appmsg)

## 11\. create\_final\_community\_reports

这个workflow用于生成社区摘要：借助LLM生成每个社区的摘要信息，用来了解数据集的全局主题结构和语义。这也是Microsoft GraphRAG的核心价值所在，也是回答QFS问题的关键。具体步骤如下：

首先借助 `create_final_nodes` 的输出，并添加了一个 `node_details` 列以存储更多关于节点的信息：

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=88815&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL21tYml6X3BuZy9YQTd2djdBaE5lbmFRTTRxV0w4RTBrQjd5aGs0eDRFZGx5MVhKVlpIM3ZZem90VWY0OWhDelRiaWM5aWJpYllhTk1uTWdtSUhkaWJESTBBVnE1bmduRzlZV3cvNjQwP3d4X2ZtdD1wbmcmYW1w;from=appmsg)

然后对这些nodes使用 `community_hierarchy` 来构建社区的层次结构，通过对(community, level) 的分组，将同一组内的节点title聚合成数组:

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=88815&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL21tYml6X3BuZy9YQTd2djdBaE5lbmFRTTRxV0w4RTBrQjd5aGs0eDRFZFBtWVFUY2lib3VQbTZVdkRDNEFoWWhZYldTQnNWa2FOdkJWT29LSzNOdzl1eG44WmhLbklFOVEvNjQwP3d4X2ZtdD1wbmcmYW1w;from=appmsg)

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=88815&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL21tYml6X3BuZy9YQTd2djdBaE5lbmFRTTRxV0w4RTBrQjd5aGs0eDRFZFRHYjlTZldQMmlhN2R3RWNsdFdtTmlhVjBxVDY3dzFpYmpPMXN1Z2VDWFUzYlVxU3ZoN01BaWM5UGcvNjQwP3d4X2ZtdD1wbmcmYW1w;from=appmsg)

从上图我们可以看到每个community包含了哪些entity。

接下来，GraphRAG开始分析父子社区的构造情况，如果上一级的社区包含了全部下一级社区的成员，那么它们之间就构成了父子社区的关系，我们发现社区1是个大社区，包含了12、13、14三个子社区，但是它们都属于同一个level：

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=88815&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL21tYml6X3BuZy9YQTd2djdBaE5lbmFRTTRxV0w4RTBrQjd5aGs0eDRFZDBPaWNjRmJCYTZQa3l2ZWljaWNZQmtNa3BZSEJDazhkSjdySjBjaWFDWUJsWTJFNG13WmFTQzJpYW5BLzY0MD93eF9mbXQ9cG5nJmFtcA==;from=appmsg)

紧接着GraphRAG会基于三个table: node\_df、edge\_df、claim\_df 做聚合操作，生成每个社区的context\_string: 包含社区的所有节点和relationships信息:

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=88815&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL21tYml6X3BuZy9YQTd2djdBaE5lbmFRTTRxV0w4RTBrQjd5aGs0eDRFZGliOVpuTTltMlZ2SUhWTUJLaDN0aWFDU3VvQVBWQkxPWGg2eXl4RmZWbkd2ZUh4QnFlazhsd2N3LzY0MD93eF9mbXQ9cG5nJmFtcA==;from=appmsg)

为了方便你看到context\_string的内容，我摘取了某个社区的context\_string内容：

```
'-----Entities-----\n'
 'human_readable_id,title,description,degree\n'
 '2,蒙奇·D·路飞,蒙奇·D·路飞是“草帽一伙”的船长，外号“草帽小子”，梦想成为“海贼王”，悬赏金30亿贝里,11\n'
 '20,ONE PIECE,,1\n'
 '17,五老星,五老星认为蒙奇·D·路飞食用的橡胶果实实际上是人人果实·幻兽种·尼卡形态,1\n'
 '10,和之国事件,和之国事件是蒙奇·D·路飞击败原“四皇”之一的“百兽”凯多的事件,1\n'
 '19,尼卡,尼卡是五老星认为蒙奇·D·路飞食用的人人果实·幻兽种的形态,1\n'
 '9,恶魔果实,恶魔果实是一种神秘的果实，食用后可以获得超人能力，但会失去游泳的能力,1\n'
 '11,百兽凯多,百兽凯多是原“四皇”之一，被蒙奇·D·路飞在和之国事件中击败,1\n'
 '\n'
 '\n'
 '-----Relationships-----\n'
 'human_readable_id,source,target,description,rank\n'
 '0,蒙奇·D·路飞,草帽一伙,蒙奇·D·路飞是草帽一伙的船长和创立者,30\n'
 '7,蒙奇·D·路飞,东海,蒙奇·D·路飞的出身地是东海,16\n'
 '1,蒙奇·D·路飞,香克斯,蒙奇·D·路飞为了实现与香克斯的约定而出海,13\n'
 '6,蒙奇·D·路飞,香波地群岛,蒙奇·D·路飞是“极恶的世代”中登陆香波地群岛的11位超新星之一,13\n'
 '9,蒙奇·D·路飞,极恶的世代,蒙奇·D·路飞是“极恶的世代”中登陆香波地群岛的11位超新星之一,13\n'
 '2,蒙奇·D·路飞,ONE PIECE,蒙奇·D·路飞为了寻找传说中的大秘宝ONE PIECE而扬帆起航,12\n'
 '8,蒙奇·D·路飞,五老星,五老星认为蒙奇·D·路飞食用的橡胶果实实际上是人人果实·幻兽种·尼卡形态,12\n'
 '4,蒙奇·D·路飞,和之国事件,蒙奇·D·路飞在和之国事件中击败了百兽凯多,12\n'
 '10,蒙奇·D·路飞,尼卡,五老星认为蒙奇·D·路飞食用的橡胶果实实际上是人人果实·幻兽种·尼卡形态,12\n'
 '3,蒙奇·D·路飞,恶魔果实,蒙奇·D·路飞因误食恶魔果实而成为了橡皮人,12\n'
 '5,蒙奇·D·路飞,百兽凯多,蒙奇·D·路飞在和之国事件中击败了百兽凯多,12\n'
```

接着LLM会使用community\_report.txt中的prompt并把context\_string作为输入， **对社区按照level进行自下而上的总结** ，使用的默认prompt中文翻译如下：

```
你是一个人工智能助手，帮助人类分析员进行一般的信息发现。信息发现是识别和评估与某些实体（例如，组织和个人）相关的相关信息的过程。

# 目标
在给定属于社区的实体列表及其关系和可选的相关声明的情况下，编写社区的全面报告。报告将用于通知决策者有关社区及其潜在影响的信息。报告内容包括社区关键实体的概述、他们的法律合规性、技术能力、声誉和值得注意的声明。

# 报告结构

报告应包括以下部分：

- 标题：代表其关键实体的社区名称——标题应简短但具体。尽可能在标题中包括具有代表性的命名实体。
- 摘要：对社区整体结构、其实体之间的关系以及与其实体相关的重大信息的执行摘要。
- 影响严重性评分：一个介于0-10之间的浮动评分，表示社区内实体所构成的影响的严重程度。影响是社区的重要性评分。
- 评分解释：用一句话解释影响严重性评分。
- 详细发现：关于社区的5-10个关键见解的列表。每个见解应有一个简短的摘要，后跟根据以下基础规则进行的多段解释性文本。要全面。

返回输出为格式良好的JSON格式的字符串，格式如下：
\`\`\`json
{
"title": <report_title>,
"summary": <executive_summary>,
"rating": <impact_severity_rating>,
"rating_explanation": <rating_explanation>,
"findings": [
{
"summary":<insight_1_summary>,
"explanation": <insight_1_explanation>
},
{
"summary":<insight_2_summary>,
"explanation": <insight_2_explanation>
}
]
}
\`\`\`

# 基础规则

支持数据的点应列出其数据引用，如下所示：

“这是一个由多个数据引用支持的示例句子[数据: <dataset name> (记录ID); <dataset name> (记录ID)]。”

在单个引用中不要列出超过5个记录ID。相反，列出最相关的前5个记录ID，并加上“+更多”以表示还有更多。

例如：
“Person X是Company Y的所有者，并且受到许多不当行为指控[数据: 报告 (1), 实体 (5, 7); 关系 (23); 声明 (7, 2, 34, 64, 46, +更多)]。”

其中1, 5, 7, 23, 2, 34, 46和64代表相关数据记录的ID（而不是索引）。

不要包括没有提供支持证据的信息。

# 示例输入
-----------
文本：

实体

id,entity,description
5,VERDANT OASIS PLAZA,绿洲广场是团结游行的地点
6,HARMONY ASSEMBLY,和谐集会是一个在绿洲广场举行游行的组织

关系

id,source,target,description
37,VERDANT OASIS PLAZA,UNITY MARCH,绿洲广场是团结游行的地点
38,VERDANT OASIS PLAZA,HARMONY ASSEMBLY,和谐集会在绿洲广场举行游行
39,VERDANT OASIS PLAZA,UNITY MARCH,团结游行正在绿洲广场进行
40,VERDANT OASIS PLAZA,TRIBUNE SPOTLIGHT,论坛焦点正在报道绿洲广场上的团结游行
41,VERDANT OASIS PLAZA,BAILEY ASADI,Bailey Asadi在绿洲广场上就游行发表演讲
43,HARMONY ASSEMBLY,UNITY MARCH,和谐集会正在组织团结游行

输出:
\`\`\`json
{
"title": "绿洲广场和团结游行",
"summary": "社区围绕绿洲广场展开，该广场是团结游行的地点。广场与和谐集会、团结游行和论坛焦点都有关系，这些都与游行事件有关。",
"rating": 5.0,
"rating_explanation": "由于团结游行期间可能发生的骚乱或冲突，影响严重性评分为中等。",
"findings": [
{
"summary": "绿洲广场作为中心地点",
"explanation": "绿洲广场是该社区的中心实体，作为团结游行的地点。该广场是所有其他实体的共同联系点，表明其在社区中的重要性。广场与游行的关联可能会导致如公共秩序问题或冲突等问题，具体取决于游行的性质和它引起的反应。[数据: 实体 (5), 关系 (37, 38, 39, 40, 41,+更多)]"
},
{
"summary": "和谐集会在社区中的角色",
"explanation": "和谐集会是社区中的另一个关键实体，他们在绿洲广场组织游行。和谐集会的性质和他们的游行可能是潜在的威胁来源，这取决于他们的目标和引起的反应。和谐集会和广场之间的关系对于理解该社区的动态至关重要。[数据: 实体(6), 关系 (38, 43)]"
},
{
"summary": "团结游行作为重要事件",
"explanation": "团结游行是一个在绿洲广场上发生的重要事件。该事件是社区动态的关键因素，具体取决于游行的性质和它引起的反应，可能是潜在的威胁来源。游行和广场之间的关系对于理解社区的动态至关重要。[数据: 关系 (39)]"
},
{
"summary": "论坛焦点的作用",
"explanation": "论坛焦点正在报道在绿洲广场上举行的团结游行。这表明该事件吸引了媒体的关注，可能会放大其对社区的影响。论坛焦点的作用可能在塑造公众对事件和相关实体的看法方面具有重要意义。[数据: 关系 (40)]"
}
]
}
\`\`\`

# 真实数据

使用以下文本作为答案的依据。不要在答案中编造任何内容。

文本:
{input_text}

报告应包括以下部分：

- 标题：代表其关键实体的社区名称——标题应简短但具体。尽可能在标题中包括具有代表性的命名实体。
- 摘要：对社区整体结构、其实体之间的关系以及与其实体相关的重大信息的执行摘要。
- 影响严重性评分：一个介于0-10之间的浮动评分，表示社区内实体所构成的影响的严重程度。影响是社区的重要性评分。
- 评分解释：用一句话解释影响严重性评分。
- 详细发现：关于社区的5-10个关键见解的列表。每个见解应有一个简短的摘要，后跟根据以下基础规则进行的多段解释性文本。要全面。

返回输出为格式良好的JSON格式的字符串，格式如下：
\`\`\`json
{
"title": <report_title>,
"summary": <executive_summary>,
"rating": <impact_severity_rating>,
"rating_explanation": <rating_explanation>,
"findings": [
{
"summary":<insight_1_summary>,
"explanation": <insight_1_explanation>
},
{
"summary":<insight_2_summary>,
"explanation": <insight_2_explanation>
}
]
}
\`\`\`

# 基础规则

支持数据的点应列出其数据引用，如下所示：

“这是一个由多个数据引用支持的示例句子[数据: <dataset name> (记录ID); <dataset name> (记录ID)]。”

在单个引用中不要列出超过5个记录ID。相反，列出最相关的前5个记录ID，并加上“+更多”以表示还有更多。

例如：
“Person X是Company Y的所有者，并且受到许多不当行为指控[数据: 报告 (1), 实体 (5, 7); 关系 (23); 声明 (7, 2, 34, 64, 46, +更多)]。”

其中1, 5, 7, 23, 2, 34, 46和64代表相关数据记录的ID（而不是索引）。

不要包括没有提供支持证据的信息。

输出:
```

我们看下某个社区的报告内容：

```
{'findings': [{'explanation': '蒙奇·D·路飞是草帽一伙的船长和创立者，他的梦想是成为海贼王。他的出身地是东海，并且为了实现与香克斯的约定而出海。他还因误食恶魔果实而成为了橡皮人，这使他获得了超人能力但失去了游泳的能力 '
'[Data: Entities (2, 9); Relationships (0, 7, 1, '
'3)].',
 'summary': '蒙奇·D·路飞的核心地位'},
{'explanation': '和之国事件是蒙奇·D·路飞击败原“四皇”之一的百兽凯多的事件。这一事件标志着他在海贼世界中的地位进一步提升，并对世界格局产生了深远影响 '
'[Data: Entities (10, 11); Relationships (4, '
'5)].',
 'summary': '和之国事件的重要性'},
{'explanation': '五老星认为蒙奇·D·路飞食用的橡胶果实实际上是人人果实·幻兽种·尼卡形态。这一观点揭示了蒙奇·D·路飞的能力可能比之前认为的更为强大和神秘 '
'[Data: Entities (17, 19); Relationships (8, '
'10)].',
 'summary': '五老星的观点'},
{'explanation': '恶魔果实是一种神秘的果实，食用后可以获得超人能力，但会失去游泳的能力。蒙奇·D·路飞因误食恶魔果实而成为了橡皮人，这使他在战斗中具有独特的优势 '
'[Data: Entities (9); Relationships (3)].',
 'summary': '恶魔果实的影响'},
{'explanation': '草帽一伙是由蒙奇·D·路飞创立的海贼团体，他们在海贼世界中扮演着重要角色。蒙奇·D·路飞作为船长，带领着这支团队在寻找传说中的大秘宝ONE '
'PIECE的过程中经历了许多冒险 [Data: Entities (2, 20); '
'Relationships (0, 2)].',
 'summary': '草帽一伙的角色'},
{'explanation': '蒙奇·D·路飞是“极恶的世代”中登陆香波地群岛的11位超新星之一。这一身份使他在海贼世界中备受关注，并进一步提升了他的影响力 '
'[Data: Relationships (6, 9)].',
 'summary': '极恶的世代'}],
 'rating': 8.5,
 'rating_explanation': '该社区的影响力很高，因为蒙奇·D·路飞在和之国事件中的胜利对整个世界格局产生了重大影响。',
 'summary': '该社区围绕着蒙奇·D·路飞展开，他是草帽一伙的船长，梦想成为海贼王。蒙奇·D·路飞与多个实体有着紧密的联系，包括和之国事件、五老星、百兽凯多等。和之国事件是他击败原“四皇”之一的百兽凯多的重要事件。五老星认为他食用的橡胶果实实际上是人人果实·幻兽种·尼卡形态。',
 'title': '蒙奇·D·路飞与和之国事件'}
```

这份报告包含了社区的总体title、summary和发现等等，这个过程也是最耗费token的。

## 12\. create\_final\_text\_units

这个workflow很简单，就是把对应的chunk和这个chunk有的document\_ids, entity\_ids, relationship\_ids 做关联，成一张表

1. **id**: 表示每条记录的唯一标识符。
2. **text**: 包含文本内容的列。
3. **n\_tokens**: 表示文本内容中包含的标记（token）的数量。
4. **document\_ids**: 包含一个或多个文档标识符的列，表示该记录与哪些文档相关联。
5. **entity\_ids**: 包含一个或多个实体标识符的列，表示该记录中提到的实体。
6. **relationship\_ids**: 包含一个或多个关系标识符的列，表示该记录中涉及到的关系。

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=88815&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL21tYml6X3BuZy9YQTd2djdBaE5lbmFRTTRxV0w4RTBrQjd5aGs0eDRFZDhWWXpQam4wZ1Y3SWFyMzRNdEs5TGF5R05xdEZsd0luN09MdURWdGVtbElId3FHTmpZWFE0Zy82NDA/d3hfZm10PXBuZyZhbXA=;from=appmsg)

## 13\. create\_base\_documents

这个流程也很简单，主要是建立document和text\_unit的对应关系表

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=88815&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL21tYml6X3BuZy9YQTd2djdBaE5lbmFRTTRxV0w4RTBrQjd5aGs0eDRFZDRabnJKYUxMZ2NNY2ZQTElzUmdXeGpCMlFPd2tNVW43Q0dMOTdVNW5iZ05EUHVOdFBlU0RTUS82NDA/d3hfZm10PXBuZyZhbXA=;from=appmsg)

## 14\. create\_final\_documents

这个流程完成的工作基本和create\_base\_documents一致，只是把text\_units列名换成了text\_unit\_ids而已

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=88815&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL21tYml6X3BuZy9YQTd2djdBaE5lbmFRTTRxV0w4RTBrQjd5aGs0eDRFZFlBMUFXWWhIeFJvWXlnNGJsWEZZVE45TkxXbEJEakpvb25uOE12RTRVZENMeEM4YW5YTkdYZy82NDA/d3hfZm10PXBuZyZhbXA=;from=appmsg)

## 总结

当GraphRAG完成索引过程后，它默认会将构建知识图谱所需的所有数据持久化。这些数据被存储在输出目录中，并采用Parquet文件格式。Parquet是一种列式压缩存储格式，专为高效的数据存储和分析而设计。你可以将其视为DataFrame的一种持久化方式。

在查询阶段，这些Parquet文件会被加载到内存和向量数据库中。这样做的好处在于，我们可以直接从内存和数据库中检索信息，而无需再次从原始数据源抽取和处理数据。这大大提高了查询的效率和速度。

由于parquet是一种底层文件格式，我们无法用来直观的了解与观察上面构建的知识图谱索引的细节，有什么办法可以做更直观的可视化、分析与检索呢？

由于parquet文件可以很简单的通过pandas库读取成DataFrame表，所以在了解其结构后，就可以通过Cypher语句导入成Neo4j图数据库中的节点与关系。在Github上已经有人完成这样的工作：https://github.com/tomasonjo/blogs/blob/master/msft\_graphrag/ms\_graphrag\_import.ipynb。你如果嫌麻烦，也可以把parquet转成csv格式进行查看，代码也非常简单，不到20行左右，感兴趣的可以评论区留言。下图是抽取的Entity的Neo4j展示：

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=88815&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL21tYml6X3BuZy9YQTd2djdBaE5lbmFRTTRxV0w4RTBrQjd5aGs0eDRFZEl4dldNWHhBTHdrMFlYeEJpY01rakVvZ3llclJyczZobkhTOGpwVlhBUms3bzhIQ1NTSzVndHcvNjQwP3d4X2ZtdD1wbmcmYW1w;from=appmsg)

基于GraphRAG生成的数据导入到Neo4j之后，我们完全可以不再依赖于GraphRAG项目自带的Query功能，可以结合自己的项目需求在自己的Neo4j图数据库上定义自己的RAG应用检索与生成器，从而带来极大的灵活性。

53AI，企业落地大模型首选服务商

**产品** ：场景落地咨询+大模型应用平台+行业解决方案

**承诺** ：免费POC验证，效果达标后再合作。 **零风险落地应用大模型** ，已交付160+中大型企业

[上一篇：解读：知识图谱与大模型的 “完美联姻”](https://www.53ai.com/news/knowledgegraph/2024090721984.html) [下一篇：数据量太大GraphRAG执行Query内存溢出? 没关系，教你基于Neo4j自定义检索和查询](https://www.53ai.com/news/knowledgegraph/2024090651493.html)

![智能化改造方案](https://static.53ai.com/uploads/20240531/5002026623535870b7a07ff223f9f34a.jpg) ![智能化改造方案](https://static.53ai.com/uploads/20240531/5002026623535870b7a07ff223f9f34a.jpg) [联系获取](https://www.53ai.com/solution.html)

![大模型落地应用平台](https://static.53ai.com/uploads/20240529/72a2c0f952f63ef0a546b91beb4bbb32.jpg) [联系获取](https://www.53ai.com/solution.html)[把握AI发展的机遇，共同探索、共同进步](https://www.53ai.com/news/dongtai/2025012294502.html)[

如何打造基于GenAI的员工服务机器人

](https://www.53ai.com/news/dongtai/2025012234192.html)

热点资讯[卡帕西没做完的，开源社区48小时搞定了！完全体知识库，token省70倍](https://www.53ai.com/news/knowledgegraph/2026040757902.html)[

告别 AI 胡说八道！这款开源神器把代码变成知识图谱，让 Cursor 和 Claude 彻底读懂你的项目

](https://www.53ai.com/news/knowledgegraph/2026032641390.html)[

碎片知识终于不乱了！这款开源 AI 工具，把笔记转为知识图谱，还能本地部署！

](https://www.53ai.com/news/knowledgegraph/2026041992465.html)[

当 SAP 买下 Reltio：企业软件进入“上下文时代”

](https://www.53ai.com/news/knowledgegraph/2026032843079.html)[

Ontological Engineering：基于PolarDB-PG智能本体引擎实现“数据驱动”到“决策中心”

](https://www.53ai.com/news/knowledgegraph/2026042329864.html)[

还在关注Palantir本体论吗！看看OntoFlow本体建模平台：从数据 -> 知识图谱 -> 本体 -> 决策的完整链路功能演示

](https://www.53ai.com/news/knowledgegraph/2026042208529.html)[

从可观测到可理解：用 UModel 构建 Agent 原生的代码知识图谱

](https://www.53ai.com/news/knowledgegraph/2026042347823.html)[

思考的快与慢：用 Prolog 给 LLM 装上理性大脑，然后引入知识图谱，做结构化知识双向同步，这个 agent 能力有点炸裂...

](https://www.53ai.com/news/knowledgegraph/2026052625940.html)[

本体（Ontology）与知识图谱（Knowledge Graph）的区别

](https://www.53ai.com/news/knowledgegraph/2026060363059.html)[

腾讯混元干了件大事：Skill Graphs

](https://www.53ai.com/news/knowledgegraph/2026050749316.html)

大家都在问[企业知识图谱如何正确分类？](https://www.53ai.com/news/knowledgegraph/2026061136970.html)[

本体论又火了，他能优化我的 Agent 效果么？

](https://www.53ai.com/news/knowledgegraph/2026052861745.html)[

在大学里“知识图谱”，真的有人用吗？

](https://www.53ai.com/news/knowledgegraph/2026012759463.html)[

什么是本体（Ontology）？

](https://www.53ai.com/news/knowledgegraph/2025122313642.html)[

大模型落地最后一公里：为什么企业必须重构对“本体（Ontology）”的认知？

](https://www.53ai.com/news/knowledgegraph/2025120113496.html)[

文档知识图谱构建：AI代理如何简化复杂流程？

](https://www.53ai.com/news/knowledgegraph/2025072943275.html)[

如何搭建Agent的知识库底座？

](https://www.53ai.com/news/knowledgegraph/2025071476043.html)[

如何为客户数据构建语义视图？

](https://www.53ai.com/news/knowledgegraph/2025061448903.html)

热门标签

[内容创作](https://www.53ai.com/news/neirongchuangzuo) [大模型技术](https://www.53ai.com/news/LargeLanguageModel) [个人提效](https://www.53ai.com/news/gerentixiao) [langchain](https://www.53ai.com/news/langchain) [llamaindex](https://www.53ai.com/news/llamaindex) [多模态技术](https://www.53ai.com/news/MultimodalLargeModel) [RAG技术](https://www.53ai.com/news/RAG) [智能客服](https://www.53ai.com/news/zhinengkefu) [知识图谱](https://www.53ai.com/news/knowledgegraph) [模型微调](https://www.53ai.com/news/finetuning) [RAGFlow](https://www.53ai.com/news/RAGFlow) [coze](https://www.53ai.com/news/coze) [Dify](https://www.53ai.com/news/dify) [Fastgpt](https://www.53ai.com/news/fastgpt) [Bisheng](https://www.53ai.com/news/Bisheng) [Qanything](https://www.53ai.com/news/Qanything) [AI+汽车](https://www.53ai.com/news/AIqiche) [AI+金融](https://www.53ai.com/news/AIjinrong) [AI+工业](https://www.53ai.com/news/AIgongye) [AI+培训](https://www.53ai.com/news/AIpeixun) [AI+SaaS](https://www.53ai.com/news/AISaaS) [Skill](https://www.53ai.com/news/tishicikuangjia) [提示词技巧](https://www.53ai.com/news/tishicijiqiao) [AI+电商](https://www.53ai.com/news/AIdianshang) [AI面试](https://www.53ai.com/news/AImianshi) [数字员工](https://www.53ai.com/news/shuziyuangong) [ChatBI](https://www.53ai.com/news/zhinengbaobiao) [AI知识库](https://www.53ai.com/news/zhishiguanli) [开源大模型](https://www.53ai.com/news/OpenSourceLLM) [智能营销](https://www.53ai.com/news/zhinengyingxiao) [智能硬件](https://www.53ai.com/news/zhinengyingjian) [FDE](https://www.53ai.com/news/zhinenghuagaizao) [AI+医疗](https://www.53ai.com/news/AIyiliao) [MaxKB](https://www.53ai.com/news/MaxKB) [Palantir](https://www.53ai.com/news/Palantir) [Glean](https://www.53ai.com/news/Glean) [Openclaw](https://www.53ai.com/news/Openclaw)

联系我们

回到顶部