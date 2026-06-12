![picture.image](https://p3-volc-community-sign.byteimg.com/tos-cn-i-tlddhu82om/7989dc3e72cb49f783b4577cb3c21500~tplv-tlddhu82om-image.image?=&rk3s=8031ce6d&x-expires=1781313810&x-signature=LBi1fEdZcS0zVpVWLzsfzcrQBzo%3D)

CAMPING

点个蓝字关注我们

我们已经了解了基于知识图谱的RAG应用原理，在之前的文章中也演示了如何使用LangChain或者LlamaIndex这样的开发框架构建简单的GraphRAG原型应用。但在实际应用中要将GraphRAG应用投入生产还会面临大量的优化工作，所以一些更专业的GraphRAG工具应运而生，微软公司最近开源的GraphRAG就获得了广泛关注。

很多朋友可能在微软的论文中已经了解到GraphRAG的基本思想。尽管如此，我们仍将尝试结合实际案例来深入GraphRAG的内部原理，并演示如何将其与Neo4j图数据库集成，以带来更大的灵活性与更丰富的应用场景。

我们将分为两篇文章介绍，分别侧重在GraphRAG的索引阶段（Index）以及查询阶段（Query）。本篇内容包括：

- **GraphRAG原理**
- ****GraphRAG** 索引构建与源码分析**
- ****GraphRAG** 索引集成到Neo4j**

GraphRAG原理

Microsoft GraphRAG最开始来源微软公司自己的论文《From Local to Global: A Graph RAG Approach to Query-Focused Summarization》，在论文中清晰的表达了其针对的传统RAG的痛点： **无法回答类似于“这些数据集表达了什么主题“这样的需要高层语义理解的总结性查询问题，也称为QFS(Query-Focused Summarization）型任务。**

在论文中提出解决办法是：

**从多个原始知识文档构建知识图谱（这一部分与之前介绍的Graph RAG并无太大区别）；然后利用社区检测算法（比如leiden算法）来把知识图谱划分成多个社区/聚簇，并利用LLM生成这些社区的自然语言摘要。** 而在回答QFS类型的问题时，先在社区执行查询获得中间答案，最后汇总生成全局性的答案。

可以把社区理解成 **围绕某个主题的一组紧密相关的实体与关系信息，** 比如”复仇者联盟与神盾局的复杂关系“这个社区，可能会关联到众多的超级英雄、组织、事件等实体及其关系。

这个过程用下图表示：

图片来自微软论文

这个过程的独特之处在于： **它把原始的自然语言文本转化与压缩为图谱，然后又把图谱总结回自然语言。即从自然语言文本-->结构化的知识图谱-->自然语言摘要。** 由于转化的知识图谱已经组合了来自多个原始文档的实体与关系信息，因此最后基于社区的自然语言摘要也就包含了跨多个数据源与文档的浓缩信息。因此可以更好的用来回答QFS问题。

Microsoft GraphRAG对这个过程的实现可以参考论文中的描述：

图片来自微软论文

这里的处理过程中在查询阶段（QueryTime）相对简单，复杂的是索引阶段（Indexing Time），其处理过程我们用尽量简洁的方式描述如下：

**1\. 文本块拆分：** 将原始文档拆分成多个文本块，这个过程与经典RAG的处理过程一样。

**2\. 实体与关系提取：** 对文本块借助LLM分析，提取实体与关系，这个过程与普通的Graph RAG也类似。

**3\. 生成实体与关系摘要：** 为提取的实体与关系生成简单的描述性信息。这是区别普通Graph RAG的一个步骤。在后面Demo中将看到，这样的信息其实是作为一个属性存放在实体/关系的Graph节点中。比如“神盾局”这样一个实体，其中的description属性就是在这一步生成（后面会介绍如何导入到Neo4j查看）：

这种摘要的好处是：可以借助嵌入embedding向量更有效与准确的对这些实体与关系进行检索，这也是上图中description\_embedding属性的意义。

带来的负面影响是由于需要为大量的实体与关系生成描述信息，将会产生很多的LLM调用，这可能带来过长的耗时与昂贵的大模型API开销！我们建议在测试时优先使用GPT-4o-mini模型。

**4\. 检测与识别社区：** 借助社区检测算法，在Graph中识别出多个社区。

**5\. 生成社区摘要：** 借助LLM生成每个社区的摘要信息，用来了解数据集的全局主题结构和语义。这也是Microsoft GraphRAG的核心价值所在，也是回答QFS问题的关键。这里也可以先看一个后面Demo中的一个社区及属性：

**GraphRAG** 索引构建与源码分析

现在我们用一个文档来构建基于MS GraphRAG的demo应用，当然这里重点关注索引阶段。我们 准备一个自然语言描述漫威漫画世界的文本文件用于测试，内容类似下图（全文约2万汉字）：

构建GraphRAG的索引过程很简单（详细可参考官方文档）：

1. **准备。** 使用pip安装graphrag库，建议在虚拟环境下进行。
2. **初始化。** 这里使用msgraphrag作为应用目录：
```
python -m graphrag.index --init --root ./msgraphrag
```

初始化以后会在指定的根目录下生成基本的文件与目录结构，重要的包括：

- **input目录：** 存放输入原始文档（txt或者csv），这里把测试的txt文件放置到该目录下
- **.env与settings.yaml配置文件** ：你可以在.env或者settings.yaml中修改全部配置项目，默认情况下可以只修改LLM相关的配置，注意目前只支持OpenAI或者Azure OpenAI的模型：

- **prompts目录：** 这里存放了自动生成的LLM提示模板文件，一共有四个，分别会在流程的不同处理阶段使用：
- **entity\_extraction：** 用于从自然语言文本抽取实体与关系。
- **summarize\_descriptions：** 用于生成实体与关系的描述性文本。
- **community\_report：** 用于生成社区的摘要等报告信息。
- **claim\_extraction：** 这是一个可选动作，用来生成一些实体的辅助声明 （由 GRAPHRAG\_CLAIM\_EXTRACTION\_ENABLED 参数控制）。 这里忽略。

尽管可以使用这里初始化的默认提示模板，但强烈建议通过GraphRAG提供的命令来创建 **自适应提示模板：GraphRAG会提取输入数据的信息，并借助大模型来分析与生成更具有针对性的提示模板。** 现在运行下面的命令来创建自适应的提示模板（更多参数请参考官方文档）：

```markdown
python -m graphrag.prompt\_tune --language Chinese
```

执行成功后我们来观察两个prompts目录下新的提示模板文件内容（为了方便理解，这里翻译成中文）：

**先看用于实体/关系摘要生成的summarize\_descriptions提示** 。可以看到，新的提示已经结合了输入文件的内容进行了“个性化”定制：

**再观察用于生成社区摘要的community\_report提示** （这里仅展示一部分）。可以看到在生成社区摘要时，会输出一份完整的“报告”，包含有标题、解释、发现等，这些信息都有助于更准确的解答QFS问题。

3. **创建索引。** 在准备好配置与提示模板后，就可以创建索引：
```markdown
python -m graphrag.index --root ./msgraphrag
```

此后就将进入一系列的工作流程，当看到如下的输出后，表示索引阶段的工作已经完成。

这里从最后输出的信息可以了解到其基本的处理过程：从拆分输入文本开始，到提取实体与关系、生成摘要信息、构建内存中的Graph结构、从Graph识别社区、创建社区报告、创建Graph中的文本块节点和文档节点等。当然，除了上面介绍的几个核心步骤外，还会涉及到大量的中间处理细节，比如embedding生成、持久化到存储、不同的算法策略等。 如果有兴趣了解详细的实现，需要研究GraphRAG的源代码。这里是一些发现与指南：

- Microsoft GraphRAG内部借助了DataShaper来实现了灵活的工作流与处理动作的“装配”。 **DataShaper** 是微软公司开源的一个用于 **定义与执行数据处理工作流的库** 。通过定义一个数据处理的工作流，你可以对输入的数据（比如Pandas的DataFrame）定义一系列数据操作的 **动作** （DataShaper中称作 **Verb** ）、 **参数与步骤** ，执行这个工作流即可完成数据处理过程。在DataShaper中提供了很多开箱即用的Verb，你也可以自定义Verb。多个子工作流也可以组合定义成一个更大的工作流。
- 一种简单的阅读方式：你可以在index/workflows/v1目录下找到基本的工作流的定义，比如上面的create\_base\_extracted\_entities；再根据工作流中的步骤（steps）找到对应的verb，然后在index/verbs中找到对应的verb实现，就可以大致了解这个工作流的内部原理。
- 学习代码目录中examples目录下的例子，可以使用GraphRAG的索引引擎来构建自己的数据处理管道；这非常有助于理解DataShaper与GraphRAG的内部原理。
- Microsoft GraphRAG在索引构建的过程中目前并不支持使用图数据库。其中间数据主要使用Pandas **DataFrame** 这种结构化类型进行交换；Graph的构建与分析主要借助 **Networkx** 这个图计算库；Graph数据的交换使用 **Graphml** （一种xml表示的graph）；在社区识别时则借助了 **Graspologic库** 实现的leiden算法。

GraphRAG索引集成到Neo4j

在完成索引后，默认情况下，GraphRAG会把构建整个知识图谱所需要的数据持久化到output目录下，并以parquet格式文件的方式存放（ **parquet** 是一种专为高效数据存储与分析设计的列式的压缩存储文件格式，想象成是DataFrame的一种持久化格式就行）。这些文件会在查询阶段被用来加载到内存及向量数据库，并用于检索：

由于parquet是一种底层文件格式，我们无法用来直观的了解与观察上面构建的知识图谱索引的细节，有什么办法可以做更直观的可视化、分析与检索呢？

**由于parquet文件可以很简单的通过pandas库读取成DataFrame表，所以在了解其结构后，就可以通过Cypher语句导入成Neo4j图数据库中的节点与关系。** 在Github上已经有大神完成这样的工作（地址见文章最后）：

这里使用其提供的笔记本文件在本地运行，即可成功地把上面构建的知识图谱数据全部导入到Neo4j数据库。 现在我们可以 通过Neo4j管理台看到完整的可视化知识图谱（部分）：

在这个Demo的图谱中，看到的节点包括了上面提取的实体( **entity** ，又分成不同类型），也包含了社区( **community** )、文本块( **chunk** )、原始文档( **document** ）；而关系则包含了 **RELATED** （实体之间）、 **PART\_OF** （chunk与document之间）、 **HAS\_ENTITY** （chunk与entity之间）、 **IN\_COMMUNITY** （entity与community之间）。一共产生了690个节点与1793条关系：

借助Neo4j的Cypher语言可以了解想知道的任何图谱信息，或者点击后快速查看某个节点详情。这里看一个社区的信息，比如“蜘蛛侠与反派角色的关系”这个社区的图谱：

这个社区的报告信息（节点属性）：

为了更好的研究GraphRAG生成的数据，还可以使用Cypher结合可视化库来对知识图谱进行深入分析，比如通过不同节点的关系数量（Node Degree）来了解节点的重要性:

这里最高的节点度接近30，来看看是哪个节点：

```
MATCH (n:\_\_Entity\_\_)   
RETURN n.name AS name, count{(n)-[:RELATED]-()} AS degree  
ORDER BY degree DESC LIMIT 10
```

执行结果如下（钢铁侠永远的神？）：

除了数据分析以外，你还可以在此基础上进行增强，比如联合导入其他已有的知识图谱数据；当然最主要的是，你可以在自己的Neo4j图数据库上定义自己的RAG应用检索与生成器，而不再依赖于GraphRAG项目自带的Query功能，从而带来极大的灵活性。

我们将在下一篇中分析Microsoft GraphRAG中Query功能的实现，并探讨如何基于导入的Neo4j库自定义实现RAG检索器。

参考：

[https://github.com/tomasonjo/blogs/blob/master/msft\\\_graphrag/ms\\\_graphrag\\\_import.ipynb](https://github.com/tomasonjo/blogs/blob/master/msft%5C_graphrag/ms%5C_graphrag%5C_import.ipynb)

END

**点击下方关注我，不迷路**

**交流请识别以下名片并说明来源**