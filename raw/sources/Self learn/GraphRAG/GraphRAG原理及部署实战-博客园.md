RAG在大模型时代，被寄予了厚望，但在近一年多各大小公司的实施过程中，其效果远没有抖音中宣传的那么振奋人心，其原因是多方面的。这篇文章就RAG中的一个弱项--局部性来展开讨论。

**一、RAG原理**

图1描述了RAG的原理，用户输入了一个指令Instruct，RAG将其与Document store(向量库)中的预存文本进行匹配，然后将符合条件的筛选文本(Retrieved Documents)与指令Instruct，共同合成为一个增强型的Prompt，并将该增强型Prompt喂给大模型，

最终大模型根据此增强型Prompt，生成最终的Response。

图1 RAG原理图(来源于网络)

因为关于RAG的文章，网络上非常多，本文不再缀叙，因前后逻辑理解上的需要，只就RAG基本流程进行说明。需要更详细了解RAG原理，可参考以下两篇博客：

- RAG技术架构与实现原理

https://cloud.tencent.com.cn/developer/article/2436421

- 用通俗易懂的方式讲解：一文详解大模型 RAG 模块

https://blog.csdn.net/python1222\_/article/details/140124845

**二、RAG的缺陷**

目前RAG效果不佳的原因，一个是Document=>Chunks的切分策略，另一个是在向量库检索(Retrieval)与指令Instruct关联的文本(Chunks)策略。

Document=>Chunks的切分策略最大的问题，如何将一篇完整的文档，自动划分为数个具有完整语义的段落集合，但现有的工具，比如Langchain里提供的RecursiveCharacterTextSpliter、CharacterTextSpliter等，都是简单的武断的将文档分成若干个段落，具有完整语义的段落被拆分为数个chunks，或者一个chunk包含几个不同语义的段落，这样的数据预处理，自然会导致在LLM推理时效果不佳。

从向量库检索匹配指令Instruct的文本，存在只能匹配细粒度的问题，如果用户指令需要从宏观上去总结一篇文章，那传统的RAG的表现就很糟糕了，因为这是传统RAG技术架构上的先天缺陷导致。传统RAG是将一篇文章打碎拆分为几个小的章节(chunks)，然后embedding后存入向量库，在查询阶段，RAG将用户指令Instruct挨个在向量库与这些chunks的embedding向量进行相似度匹配，然后输出最匹配的k个作为prompt的上下文(context)，无论是在文档预处理进向量库阶段，还是用户查询阶段，都没家考虑各个chunk之间的关联，这就形成了普通RAG技术的先天设计缺陷。

所以，微软这些牛人就针对上面提到的这个RAG先天设计缺陷，提出了GraphRAG的理念和实现版本。

**三、GraphRAG**

　　论文：《From Local to Global: A Graph RAG Approach to Query-Focused Summarization》

源码：https://github.com/microsoft/graphrag

GraphRAG提出了一种回答总结类(summary)问题的算法思路，图2展示了GraphRAG算法的工作流程，包括索引建立阶段(index time)和查询阶段(query time)。

![](https://img2024.cnblogs.com/blog/1464966/202410/1464966-20241029154057522-1972830154.png)

图2 GraphRAG算法工作流

- 索引建立(index time)

　　　索引建立阶段，属于数据预处理阶段，主要目的是从提供的文档集合中，提取出知识图谱(Knowledge Graph)，然后以聚类算法(Leiden)，将知识图谱分为数个社区(community)，并总结每个社区(community)所表达的含义(community summary)。

- 查询(query time)

　　　查询阶段，是建立在索引建立的阶段基础上，GraphRAG系统的终端用户，在此阶段加入进来，并向系统提供查询指令Instruct。GraphRAG将用户Instruct与每个社区的community summary进行相似度匹配，并将匹配结果作为最终喂给大模型的prompt的上下文(context)，以生成返回给用户的最终回答。

**三、GraphRAG部署**

　　GraphRAG部署分为安装包部署和源码部署，这里推荐源码部署，因为部署过程中，可能会遇到不可预知的问题，有些问题只能修改源码才能规避。

**1、安装依赖环境**

安装依赖管理工具poetry，poetry是比pip更完善依赖管理工具，只要通过poetry安装或删除的包，poetry都会对pyproject.toml文件进行更新。

![](https://img2024.cnblogs.com/blog/1464966/202410/1464966-20241029160616803-378739892.png)

安装graphrag依赖包

![](https://img2024.cnblogs.com/blog/1464966/202410/1464966-20241029161028147-1321006135.png)

安装openai sdk

![](https://img2024.cnblogs.com/blog/1464966/202410/1464966-20241029163956228-1509053936.png)

**2、索引建立**

**2.1 配置.env文件**

配置GRAPHRAG\_API\_KEY，该API\_KEY是OpenAI、Qwen、GLM等大模型API的API Key，可自行去各大模型厂商的官网获取。

![](https://img2024.cnblogs.com/blog/1464966/202410/1464966-20241029162117155-595135144.png)

**2.2 配置settings.yaml**

配置llm->model和llm->api\_base，使GraphRAG能访问到大模型 API接口

![](https://img2024.cnblogs.com/blog/1464966/202410/1464966-20241029163109255-128656081.png)

　配置embeddings的llm->model和llm->api\_base，配置方法同上。

**2.3 搭建数据集**

　将数据集文本 flatten方式存放在input文件夹下，本文目的是展示搭建GraphRAG的流程，数据集只包含一个文本文件。

![](https://img2024.cnblogs.com/blog/1464966/202410/1464966-20241029164553645-2069149204.png)

**2.4 建立索引**

运行poetry run poe index --root. ，

![](https://img2024.cnblogs.com/blog/1464966/202410/1464966-20241029165211728-1034231970.png)

执行到create\_base\_entity\_graph阶段，遇到错误，查日志发现是大模型服务器证书是自验证的证书，而不是CA这类权威机构颁发的证书。，如果所在网络没有报证书校验问题，可忽略下面跳过证书验证的部分。

![](https://img2024.cnblogs.com/blog/1464966/202410/1464966-20241029165731796-2041667964.png)

为解决自验证证书问题，只能修改GraphRAG网络访问部分的代码，需要修改graphrag/llm/openai/create\_openai\_client.py、graphrag/query/oai/base.py和tiktoken/loader.py三个文件。

graphrag/llm/openai/create\_openai\_client.py需要修改：

![](https://img2024.cnblogs.com/blog/1464966/202410/1464966-20241029170933814-652421206.png)

graphrag/query/oai/base.py需要修改：

![](https://img2024.cnblogs.com/blog/1464966/202410/1464966-20241029170123284-1068132899.png)

tiktoken/loader.py需要修改：

![](https://img2024.cnblogs.com/blog/1464966/202410/1464966-20241029170523789-1579674062.png)

然后再执行构建索引指令，即可成功构建索引。

![](https://img2024.cnblogs.com/blog/1464966/202410/1464966-20241029171326204-616987496.png)

**2.4 查询**

执行以下指令，进行global方式查询。

![](https://img2024.cnblogs.com/blog/1464966/202410/1464966-20241029171635827-2081661252.png)

global方式查询效果如下：

![](https://img2024.cnblogs.com/blog/1464966/202410/1464966-20241029171609242-1685138541.png)

执行以下指令，进行local方式查询。

![](https://img2024.cnblogs.com/blog/1464966/202410/1464966-20241029171745678-1050732350.png)

local方式查询效果如下：

![](https://img2024.cnblogs.com/blog/1464966/202410/1464966-20241029171849653-1184836789.png)

至此，GraphRAG调试环境部署完成。

![](https://img2024.cnblogs.com/blog/1464966/202411/1464966-20241105171832869-613910700.png)

关注更多安卓开发、AI技术、股票分析技术及个股诊断等理财、生活分享等资讯信息，请关注本人公众号(木圭龙的知识小屋)