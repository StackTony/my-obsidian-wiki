RAG 很多人都听说过，或者实践过，目前最直接的应用就是构建智能问答系统。

**什么是 RAG？**

RAG 是 **R**etrieval **A**ugmented **G**eneration 的简写，翻译过来就是**检索增强生成**。

**从名字就可以拆分出 RAG 的三大部分，检索、增强、生成，表面意思就是**：

1、去知识库检索相关的各种东西

2、把检索出来的信息，融合到 prompt 中，增强输入信息

3、最后是大模型生成更符合事实性的回答

**为什么需要用到 RAG 呢？**

大模型"幻觉"的问题一直存在，RAG 是缓解其幻觉的一个很重要的途径，当然还有其他缓解的方式,SFT 这些。

**有几点比较重要的优势吧。**

1. 外挂知识，可以增加 LLM 推理的能力、准确性，能够更加复合客观事实。
    
2. 知识库增删修改更加方便，遇到 bug 及时修复知识库，或者更新知识库即可，基本是用户没有感知的状态，不像 SFT 还需要重新训练，耗费时间。
    
3. 再就是可解释性，通过工程手段，可以给出合理的引用链接，增加可信度，比如现在做的一些智能搜索，后面会列出答案来自的链接。
    

**如果还有其他的，下面评论区留言哈，大家一起探讨。**

那么现在有多少开源框架可以很方便的做这个事情呢？

是否需要重复造轮子呢？

这是个好问题。

> 所以总结下目前都有哪些开源的 RAG 框架，看下是否满足开发需要，就是一个蛮有必要的事情。

**这里总结一些 RAG 框架，有其他的可以评论区留言。**

## 框架一：LangChain

**LangChain 是一个用于开发由大型语言模型 (LLMs) 驱动的应用程序的框架。**

**项目地址**：https://github.com/langchain-ai/langchain

> 目前已获得 86.2k starts 关注，众人关注。

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=83458&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL3N6X21tYml6X3BuZy9zdmRpYVFCd2ZzZVR3R1NvMlplUnlBYko3MTNsOVpRUWpLcnFUcFZkbTNjNFRwVU85V1BORUZITHFQQmlhV1BHWUtMME9BTlhISUZ4bnlzaWN6eENGR0Q3QS82NDA/d3hfZm10PXBuZyZhbXA=;from=appmsg)

对于这些应用程序，LangChain 简化了整个应用程序生命周期：

**开源库**：使用 LangChain 的模块化构建块和组件构建您的应用程序。与数百家第三方提供商集成。

**生产化**：使用 LangSmith 检查、监控和评估您的应用程序，以便您可以充满信心地不断优化和部署。

**部署**：使用 LangServe 将任何链转换为 REST API。

现在市面上有很多人用 LangChain 结合 LLM 构造 RAG 流程，因为 Langchain 里面包含了各种组件，向量检索、文本分割、大模型调用，还有很多其他的都在里面。

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=83458&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL3N6X21tYml6X3BuZy9zdmRpYVFCd2ZzZVR3R1NvMlplUnlBYko3MTNsOVpRUWpKZFU4NEg0MnZ6VGwwM2NWaWE3VzVkNFcxUWZaNjdnOEtMcElUS2ljVHYzVEZIcks3VnFDS3RYQS82NDA/d3hfZm10PXBuZyZhbXA=;from=appmsg)

**这里有一份 LangChain RAG 的教资料，可收藏**：https://python.langchain.com/v0.2/docs/tutorials/rag/

## 框架二：Langchain-Chatchat

> 一种利用 langchain 思想实现的基于本地知识库的问答应用，目标期望建立一套对中文场景与开源模型支持友好、可离线运行的知识库问答解决方案。

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=83458&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL3N6X21tYml6X3BuZy9zdmRpYVFCd2ZzZVR3R1NvMlplUnlBYko3MTNsOVpRUWo1cmcxemJNMnU5RWhIbjhiaWNKV0dzZzRDWm1DcTlaYlhIWmNobk8zMGhkUkVDTjJRRlFLQ253LzY0MD93eF9mbXQ9cG5nJmFtcA==;from=appmsg)

**项目地址**：https://github.com/chatchat-space/Langchain-Chatchat

> 目前已收获 28.7k 关注。

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=83458&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL3N6X21tYml6X3BuZy9zdmRpYVFCd2ZzZVR3R1NvMlplUnlBYko3MTNsOVpRUWpqdFNEd0lRQjdQVjdHWVRkSVhXRDBPbjd4YkZCckdYWk95SFl4Wkg2clBsaWJaT2JtVTkwc0tnLzY0MD93eF9mbXQ9cG5nJmFtcA==;from=appmsg)

这是项目的流程框架。

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=83458&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL3N6X21tYml6X3BuZy9zdmRpYVFCd2ZzZVR3R1NvMlplUnlBYko3MTNsOVpRUWo0bHVuWHM2YkxFbVZhb3Q5VVh3TURlajhjYUVlZnBKVGFvZERCN2dpYkhTWVdiMWlhODdiS2RCUS82NDA/d3hfZm10PXBuZyZhbXA=;from=appmsg)

**它解决的痛点**

该项目是一个可以实现 ****完全本地化****推理的知识库增强方案, 重点解决数据安全保护，私域化部署的企业痛点。

**可以免费商用，无需付费。**

支持市面上主流的本地大语言模型和 Embedding 模型，支持开源的本地向量数据库。

**这里是一份框架的文档：** https://github.com/chatchat-space/Langchain-Chatchat/wiki/

## 框架三：QAnything

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=83458&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL3N6X21tYml6X3BuZy9zdmRpYVFCd2ZzZVR3R1NvMlplUnlBYko3MTNsOVpRUWpweFFxT3lwNlRRaWFVN0l5Wll0RHQwa0pVMFZ4QWxvd2haSXFXaWJQWk5aR2p4NFUxdTd3WXlqdy82NDA/d3hfZm10PXBuZyZhbXA=;from=appmsg)

> QAnything (Question and Answer based on Anything) 是致力于支持任意格式文件或数据库的本地知识库问答系统，可断网安装使用。

> 目前已支持格式: PDF(pdf)，Word(docx)，PPT(pptx)，XLS(xlsx)，Markdown(md)，电子邮件(eml)，TXT(txt)，图片(jpg，jpeg，png)，CSV(csv)，网页链接(html)

**项目地址：** https://github.com/netease-youdao/QAnything/tree/master

> **网易出品，目前已收获 9.9k 关注。**

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=83458&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL3N6X21tYml6X3BuZy9zdmRpYVFCd2ZzZVR3R1NvMlplUnlBYko3MTNsOVpRUWo5QUlLY2xjV2Nlcll4SUtoeVI3Rlhqa1A3aWFsMWlhRVhaN1dpYUtCQUNYbE1zWEVqbm0zSnFpYWpRLzY0MD93eF9mbXQ9cG5nJmFtcA==;from=appmsg)

**架构如下**

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=83458&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL3N6X21tYml6X3BuZy9zdmRpYVFCd2ZzZVR3R1NvMlplUnlBYko3MTNsOVpRUWpnanc4N1VpYThhNTYzNzJoM3NwanV5cjVWN1A1dXFyUHBFS3drbmVUdkxkRWswcTRkUGZpYWViZy82NDA/d3hfZm10PXBuZyZhbXA=;from=appmsg)

**有个很重要的关键点；两阶段检索**

知识库数据量大的场景下两阶段优势非常明显，如果只用一阶段 embedding 检索，随着数据量增大会出现检索退化的问题，如下图中绿线所示，二阶段 rerank 重排后能实现准确率稳定增长，即数据越多，效果越好。

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=83458&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL3N6X21tYml6X3BuZy9zdmRpYVFCd2ZzZVR3R1NvMlplUnlBYko3MTNsOVpRUWoxbXc0QUhrVGVCb0l4QTVRczVOMVZHQ2E0ZWZjMDdseGhCTHAxZkdYZzJ0eVo5cWVkSEdETncvNjQwP3d4X2ZtdD1wbmcmYW1w;from=appmsg)

**这是文档**：https://qanything.ai/docs/introduce

## 框架四：RAGFlow

> RAGFlow 是一款基于深度文档理解构建的开源 RAG（Retrieval-Augmented Generation）引擎。RAGFlow 可以为各种规模的企业及个人提供一套精简的 RAG 工作流程，结合大语言模型（LLM）针对用户各类不同的复杂格式数据提供可靠的问答以及有理有据的引用。

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=83458&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL3N6X21tYml6X3BuZy9zdmRpYVFCd2ZzZVR3R1NvMlplUnlBYko3MTNsOVpRUWpIM3dLQTNydlJMRlJNaDNOYURUSDdpY1hvaFZmYXBUOEZ3QTAzSEkxWEFtREZad1lRcURzYnhnLzY0MD93eF9mbXQ9cG5nJmFtcA==;from=appmsg)

**项目地址：** https://github.com/infiniflow/ragflow/tree/main

> 目前已收获 8.8k 关注

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=83458&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL3N6X21tYml6X3BuZy9zdmRpYVFCd2ZzZVR3R1NvMlplUnlBYko3MTNsOVpRUWo0d0tTYk5vR2hzbUtxaWJUTzlFaWNVR3F5OFlWRmVMWHE4S1FYQ2o2TElHSHdYcW1OVTRQd0dBdy82NDA/d3hfZm10PXBuZyZhbXA=;from=appmsg)

**主要功能**

? **"Quality in, quality out"**

- 基于深度文档理解，能够从各类复杂格式的非结构化数据中提取真知灼见。
    
- 真正在无限上下文（token）的场景下快速完成大海捞针测试。
    

? **基于模板的文本切片**

- 不仅仅是智能，更重要的是可控可解释。
    
- 多种文本模板可供选择
    

? **有理有据、最大程度降低幻觉（hallucination）**

- 文本切片过程可视化，支持手动调整。
    
- 有理有据：答案提供关键引用的快照并支持追根溯源。
    

? **兼容各类异构数据源**

- 支持丰富的文件类型，包括 Word 文档、PPT、excel 表格、txt 文件、图片、PDF、影印件、复印件、结构化数据、网页等。
    

? **全程无忧、自动化的 RAG 工作流**

- 全面优化的 RAG 工作流可以支持从个人应用乃至超大型企业的各类生态系统。
    
- 大语言模型 LLM 以及向量模型均支持配置。
    
- 基于多路召回、融合重排序。
    
- 提供易用的 API，可以轻松集成到各类企业系统
    

**系统架构**

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=83458&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL3N6X21tYml6X3BuZy9zdmRpYVFCd2ZzZVR3R1NvMlplUnlBYko3MTNsOVpRUWpNVERZMEprdUFzUmpJZlRXclZ3aWM4Wmx4dkVIM0p2UUZXbEtFbkNEeWlieEQwVmVON003VFlXQS82NDA/d3hfZm10PXBuZyZhbXA=;from=appmsg)

**这是文档**：https://ragflow.io/docs/dev/

## 框架五：FastGPT

> FastGPT 是一个基于 LLM 大语言模型的知识库问答系统，提供开箱即用的数据处理、模型调用等能力。同时可以通过 Flow 可视化进行工作流编排，从而实现复杂的问答场景！

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=83458&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL3N6X21tYml6X3BuZy9zdmRpYVFCd2ZzZVR3R1NvMlplUnlBYko3MTNsOVpRUWp5Rm1sbWdPRnlnWVh4aWNnQTZ5WW1oZk9VQ2lieHVKMnBVT1NxYkt1RTBpYTFDQnFBcU94cGliaWEwZy82NDA/d3hfZm10PXBuZyZhbXA=;from=appmsg)

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=83458&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL3N6X21tYml6X3BuZy9zdmRpYVFCd2ZzZVR3R1NvMlplUnlBYko3MTNsOVpRUWpxVDh0VzNOSEEyaWFKQTNsaWNxU3BIUWRZNGhlN2ljSzJ0VjdqTVMxOWtCTGdpYVlBaDhLajhoSHhRLzY0MD93eF9mbXQ9cG5nJmFtcA==;from=appmsg)

**项目地址**：https://github.com/labring/FastGPT

> 目前项目已收获 14.2k 关注。

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=83458&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL3N6X21tYml6X3BuZy9zdmRpYVFCd2ZzZVR3R1NvMlplUnlBYko3MTNsOVpRUWpTMWNPaFlqc3RYQXJwTnJGcHZWTGJpYWZkUGFtcFExdG5zc0xOY0M1NE55WlVYdHVkSzRlSHRnLzY0MD93eF9mbXQ9cG5nJmFtcA==;from=appmsg)

介绍文档：https://doc.fastgpt.in/docs/intro/

## 框架六：Haystack

> Haystack 是一个端到端 LLM 框架，允许构建由 LLMs、Transformer 模型、矢量搜索等支持的应用程序。无论想要执行检索增强生成 (RAG)、文档搜索、问答还是答案生成，Haystack 都可以将最先进的嵌入模型和 LLMs 编排到管道中，以构建端到端结束 NLP 应用程序并解决案例。

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=83458&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL3N6X21tYml6X3BuZy9zdmRpYVFCd2ZzZVR3R1NvMlplUnlBYko3MTNsOVpRUWp6SmlicENKd1NwRENXdjM4azFtQVdKbnV2VXJCTUZMYXB2MUNWOFVvM0s4RkR6SndBaGliQkZEZy82NDA/d3hfZm10PXBuZyZhbXA=;from=appmsg)

**项目地址**：https://github.com/deepset-ai/haystack

> 目前已收获 14.2k 关注。

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=83458&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL3N6X21tYml6X3BuZy9zdmRpYVFCd2ZzZVR3R1NvMlplUnlBYko3MTNsOVpRUWpkaWNhY281aWFNZmljZUNpYjlJNDRaQ1BSWmpFS3RqSVMyZWtYblV3VDRNaFJhSDNSNEVCN1NpYlJtZy82NDA/d3hfZm10PXBuZyZhbXA=;from=appmsg)

**重要特点**

- **技术不可知论**：允许用户灵活地决定他们想要的供应商或技术，并可以轻松地将任何组件更换为另一个组件。Haystack 允许使用和比较 OpenAI、Cohere 和 Hugging Face 提供的模型，以及自己的本地模型或 Azure、Bedrock 和 SageMaker 上托管的模型。
    
- **明确**：使不同的移动部件如何相互“对话”变得透明，以便更轻松地适应技术堆栈和用例。
    
- **灵活**：Haystack 在一个地方提供所有工具：数据库访问、文件转换、清理、拆分、训练、评估、推理等。只要需要自定义行为，就可以轻松创建自定义组件。
    
- **可扩展**：为社区和第三方提供统一且简单的方式来构建自己的组件，并围绕 Haystack 培育开放的生态系统。
    

这是文档：https://docs.haystack.deepset.ai/v2.0/docs/get_started

## 框架七：LLAMA_Index

> LlamaIndex 是一个用于构建上下文增强 LLM 应用程序的框架,上下文增强是指在您的私有或特定于域的数据之上应用 LLMs 的任何用例。

**项目地址**：https://github.com/run-llama/llama_index

> 目前已有 32.4k 关注。

![](https://api.ibos.cn/v4/weapparticle/accesswximg?aid=83458&url=aHR0cHM6Ly9tbWJpei5xcGljLmNuL3N6X21tYml6X3BuZy9zdmRpYVFCd2ZzZVR3R1NvMlplUnlBYko3MTNsOVpRUWpvd3hWdnY2N0tIMXU1dUlsVDBjS1g2Y3hrcWlhZlEwbGF4VGdMZmlibjJRTzBaV0hOYlNiTDV6US82NDA/d3hfZm10PXBuZyZhbXA=;from=appmsg)

**提供了以下工具：**

- 提供数据连接器来摄取现有数据源和数据格式（API、PDF、文档、SQL 等）。
    
- 提供构建数据（索引、图表）的方法，以便这些数据可以轻松地与 LLMs 一起使用。
    
- 为数据提供高级检索/查询界面：输入任何 LLM 输入提示，获取检索到的上下文和知识增强输出。
    
- 允许与外部应用程序框架轻松集成（例如与 LangChain、Flask、Docker、ChatGPT 等）。
    

**文档，内容很全，可收藏**: https://docs.llamaindex.ai/en/stable/

**以上一共有 7 个 RAG 框架

- Langchain
    
- Langchain-Chatchat
    
- LLAMAIndex
    
- QAnything
    
- RAGFlow
    
- FastGPT
    
- Haystack
    

想必这些框架能够满足日常的需要，不能够满足的话，参考这些开源框架再自己搭建符合业务需求的框架。