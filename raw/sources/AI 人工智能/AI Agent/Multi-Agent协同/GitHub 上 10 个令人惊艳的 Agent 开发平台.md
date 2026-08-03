原文链接：
https://zhuanlan.zhihu.com/p/1989277883168989967

### 01、**AutoGPT**

AutoGPT 是 AI Agent 领域的**鼻祖级**项目，现在已经 18 万+的 Star 了。

与[聊天机器人](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=%E8%81%8A%E5%A4%A9%E6%9C%BA%E5%99%A8%E4%BA%BA&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiLogYrlpKnmnLrlmajkuroiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjgzNTkwMDEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.DkzIvp0UgntEcz3t_zfzy6aKn_XfSHo5mhWNssO0AeQ&zhida_source=entity)不一样，AutoGPT 能够**自主地将一个大目标拆解为子任务**，并利用互联网搜索、本地文件等操作来**一步步实现目标。**

![](https://pic3.zhimg.com/v2-788416232ac24e6d9db3ac117c2e2d6c_1440w.jpg)

AutoGPT **具备强大的工具调用和环境交互能力。**

它能够通过访问互联网搜索最新信息、管理本地文件的读写、执行代码以及保留长期和短期记忆来[辅助决策](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=%E8%BE%85%E5%8A%A9%E5%86%B3%E7%AD%96&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiLovoXliqnlhrPnrZYiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjgzNTkwMDEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.FQfm7JtRKVEdqBGurCbooE-UTKZO1S7utXnr1KeKr6U&zhida_source=entity)。

核心机制是一个**思考-计划-行动**的循环：模型会评估当前状态，制定下一步计划，执行操作，并根据反馈结果进行自我修正，这使得它能够处理比单一对话更复杂、耗时更长的[自动化工作流](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=%E8%87%AA%E5%8A%A8%E5%8C%96%E5%B7%A5%E4%BD%9C%E6%B5%81&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiLoh6rliqjljJblt6XkvZzmtYEiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjgzNTkwMDEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.EEHRhOKwb13SL7stsf4-6hx5I9CR8tBPy0A7CJ5LnhE&zhida_source=entity)。

![](https://pic4.zhimg.com/v2-06edfd45d1608198f19578641a85ef7d_1440w.jpg)

AutoGPT 这个[开源项目](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=%E5%BC%80%E6%BA%90%E9%A1%B9%E7%9B%AE&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiLlvIDmupDpobnnm64iLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjgzNTkwMDEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.ywmi7Ff7waaL10zzvY994MPd6iKIHESDrOtMlZ_TqYA&zhida_source=entity)绝对是推动 AI Agent 领域的快速发展，是研究[自主智能体](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=%E8%87%AA%E4%B8%BB%E6%99%BA%E8%83%BD%E4%BD%93&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiLoh6rkuLvmmbrog73kvZMiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjgzNTkwMDEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.0FbmskL2TcSHv-aTB4mG53IjeSsOX2-1srRVg_bEr4Y&zhida_source=entity)（Autonomous Agents）的必看项目。

```
开源地址: https://github.com/Significant-Gravitas/AutoGPT
```

### 02、**[Dify](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=Dify&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiJEaWZ5IiwiemhpZGFfc291cmNlIjoiZW50aXR5IiwiY29udGVudF9pZCI6MjY4MzU5MDAxLCJjb250ZW50X3R5cGUiOiJBcnRpY2xlIiwibWF0Y2hfb3JkZXIiOjEsInpkX3Rva2VuIjpudWxsfQ.JSztXgJRKB2UN9nEvxzYP7ra9p6gWPr7AQx4fh23Ls8&zhida_source=entity)**

Dify 目前 12 万+ 的 Star 了。

它不仅仅是 Agent 框架，还是融合了 **[Backend-as-a-Service](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=Backend-as-a-Service&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiJCYWNrZW5kLWFzLWEtU2VydmljZSIsInpoaWRhX3NvdXJjZSI6ImVudGl0eSIsImNvbnRlbnRfaWQiOjI2ODM1OTAwMSwiY29udGVudF90eXBlIjoiQXJ0aWNsZSIsIm1hdGNoX29yZGVyIjoxLCJ6ZF90b2tlbiI6bnVsbH0.0Ac9dEcM1SEJpd6ya-nhoJh8_Xc3aWh2DL0fiahkFLY&zhida_source=entity) (BaaS)** 和 **[LLMOps](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=LLMOps&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiJMTE1PcHMiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjgzNTkwMDEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.GkNbcWL1JwUInYh_w_OezTtBtBoyAOvv5tPzRMUUmho&zhida_source=entity)** 理念的大模型应用[开发平台](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=%E5%BC%80%E5%8F%91%E5%B9%B3%E5%8F%B0&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiLlvIDlj5HlubPlj7AiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjgzNTkwMDEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.h0XvZg49FtUBnr7cZpaew96hI5JTLe0M0R_TnICeqAg&zhida_source=entity)。

![](https://pic1.zhimg.com/v2-2313b04e641bed7699c67f391191c746_1440w.jpg)

它提供了可视化的 [Prompt 编排](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=Prompt+%E7%BC%96%E6%8E%92&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiJQcm9tcHQg57yW5o6SIiwiemhpZGFfc291cmNlIjoiZW50aXR5IiwiY29udGVudF9pZCI6MjY4MzU5MDAxLCJjb250ZW50X3R5cGUiOiJBcnRpY2xlIiwibWF0Y2hfb3JkZXIiOjEsInpkX3Rva2VuIjpudWxsfQ.3ehJVXChKpv1QX53qRO6Lpi9rVpLHlF6HY-xCuYn9No&zhida_source=entity)、运营管理、知识库 RAG 集成等功能。

通过 Dify，不需要从头编写后端代码，即可快速将简单的 Prompt 转化为功能完备、**可投入生产的 AI 应用**。

![动图封面](https://pica.zhimg.com/v2-5c87346d3171473aba8f653d228846a6_b.jpg)

Dify 支持**可视化编排**，拖拽节点来定义复杂的 Agent 逻辑和工具调用。并且内置了高质量的 RAG 引擎，能够自动处理文档解析、分段和[向量化](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=%E5%90%91%E9%87%8F%E5%8C%96&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiLlkJHph4_ljJYiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjgzNTkwMDEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.gQsi2ATTJAq34SrHLavRKaSMf0qorIkFEo5kIUeje5o&zhida_source=entity)，轻松构建企业级知识库。

它提供了可视化的 Prompt 编排、运营管理、知识库 RAG 集成等功能。

![动图封面](https://picx.zhimg.com/v2-387844f0c8d46622b9844eadc1b5e247_b.jpg)

关于它和 Dify、n8n、Coze 的区别，让 Nano Banana Pro 画了一个图：

![](https://pic1.zhimg.com/v2-6ffa7778e412bece47646abad39cf19e_1440w.jpg)

```
开源地址: https://github.com/langgenius/dify
```

### 03、**[LangChain](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=LangChain&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiJMYW5nQ2hhaW4iLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjgzNTkwMDEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.yhTbwNu4CrIvWmRVqKSDplsEOqwu15mQnSnZ4LKUaxU&zhida_source=entity)**

![](https://picx.zhimg.com/v2-82721615fb37826aa6c61e99f0ff22df_1440w.jpg)

虽然 LangChain 是一个通用的 LLM 开发框架，但它目前是构建 Agent 的事实标准基础设施之一。

对于初学者来说，**它的学习曲线还是很陡峭的**，一旦掌握了会发现它确实是构建复杂逻辑最稳健的地基。

它有很多高度模块化的组件，包括**链 Chains、代理 Agents 和记忆 Memory。**

开发者可以像**搭积木**一样，将提示词管理、文档加载、向量检索以及模型调用串联成一个完整的工作流。

特别是其强大的 Agent 机制，大模型充当[推理引擎](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=%E6%8E%A8%E7%90%86%E5%BC%95%E6%93%8E&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiLmjqjnkIblvJXmk44iLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjgzNTkwMDEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.GOVYJJSh6AFs-F-RYiIr3t1RhMv0S4ESGH9Hl-nFgDI&zhida_source=entity)，动态决定调用哪些外部工具，比如 Google 搜索、计算器或 API 啥的来解决问题。

![](https://pic1.zhimg.com/v2-232698356a781f84594242907a8e003a_1440w.jpg)

特别是其子项目 **[LangGraph](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=LangGraph&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiJMYW5nR3JhcGgiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjgzNTkwMDEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.06AS9I5h-XJXxopb3bfq98tUpaYb9d2LiZHp7jH1ZAY&zhida_source=entity)**，专门用于构建有状态的、多角色的 Agent 应用。

它提供了高度可控的[循环计算](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=%E5%BE%AA%E7%8E%AF%E8%AE%A1%E7%AE%97&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiLlvqrnjq_orqHnrpciLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjgzNTkwMDEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.1AqfaGJsgs0seFw8j_-AgOSb3JLiE79joNbyEuD9GY8&zhida_source=entity)能力，让开发者能够精细地控制 Agent 的决策流程，是 [Python](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=Python&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiJQeXRob24iLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjgzNTkwMDEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.wJSxHTAz-uFewwRyU9BE_5L4sKYAu0Eic-AkfpHZbnk&zhida_source=entity) 开发者构建复杂 Agent 的首选底层框架。

```
开源地址：https://github.com/langchain-ai/langchain
```

### 04、**MetaGPT**

MetaGPT 现在在 [GitHub](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=GitHub&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiJHaXRIdWIiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjgzNTkwMDEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.2P8_qeRsHQoUsZOOPo6ZyI4FrOmVra7XkX8gMC6WzyY&zhida_source=entity) 上有 6 万多 Star 了。

如果想研究**[多智能体协作](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=%E5%A4%9A%E6%99%BA%E8%83%BD%E4%BD%93%E5%8D%8F%E4%BD%9C&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiLlpJrmmbrog73kvZPljY_kvZwiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjgzNTkwMDEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.NVznJt17WUTCoa4qXB3M61fvNoJ6ZTD5nQSXmDgMUZM&zhida_source=entity)**，这个开源项目可以说是最重要的框架之一。

![](https://picx.zhimg.com/v2-a7d9d8c757b5ff17de4688170fc21947_1440w.jpg)

它**模拟了一个虚拟的软件公司**，内部包含产品经理、架构师、[项目经理](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=%E9%A1%B9%E7%9B%AE%E7%BB%8F%E7%90%86&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiLpobnnm67nu4_nkIYiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjgzNTkwMDEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.z8Hzck63kRVXoaTPEoG7J61UXPxLQBiSsB7rKD-EMnw&zhida_source=entity)和工程师等不同角色的 Agent。

只要输入一句话需求，这些 **Agent 就会协同工作**，输出用户故事、[竞品分析](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=%E7%AB%9E%E5%93%81%E5%88%86%E6%9E%90&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiLnq57lk4HliIbmnpAiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjgzNTkwMDEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.43-LDgVyVsAgZKhP7et2y1VRVN5PK-i3XP58a7Dr_l8&zhida_source=entity)、设计图甚至可运行的代码。

适合对多智能体协作（Multi-Agent Collaboration）感兴趣的开发者，特别适合那种流程固定、对输出稳定性要求高的场景。

```
开源地址: https://github.com/geekan/MetaGPT
```

### 05、**[Microsoft AutoGen](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=Microsoft+AutoGen&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiJNaWNyb3NvZnQgQXV0b0dlbiIsInpoaWRhX3NvdXJjZSI6ImVudGl0eSIsImNvbnRlbnRfaWQiOjI2ODM1OTAwMSwiY29udGVudF90eXBlIjoiQXJ0aWNsZSIsIm1hdGNoX29yZGVyIjoxLCJ6ZF90b2tlbiI6bnVsbH0.r5gdq-uG98OTtRI70GhOb1ACkN_CCJfxehSaHesInz0&zhida_source=entity)**

微软开源的框架，之前也介绍过，现在已经 的 Star 了。

![](https://pic2.zhimg.com/v2-5719af5ae5ec674e90e60d15b1595dcd_1440w.jpg)

它专注于[多智能体对话](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=%E5%A4%9A%E6%99%BA%E8%83%BD%E4%BD%93%E5%AF%B9%E8%AF%9D&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiLlpJrmmbrog73kvZPlr7nor50iLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjgzNTkwMDEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.ZYzW7WnXfFvBzPDfEjt80eozmXjbiMJraLOA6SC-0fs&zhida_source=entity)。可以定义多个可以相互对话的 Agent，可以是 LLM、人类或工具，它们通过对话来协作解决任务。

该框架高度抽象和灵活，支持多种对话模式，是目前**工业界和学术界探索[多智能体系统](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=%E5%A4%9A%E6%99%BA%E8%83%BD%E4%BD%93%E7%B3%BB%E7%BB%9F&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiLlpJrmmbrog73kvZPns7vnu58iLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjgzNTkwMDEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.f0_8MNvPWh6pFh2ZLHZEGVRMYPnZLf3etxLbTc-teHM&zhida_source=entity)（Multi-Agent Systems）最主流的框架之一。**

```
开源地址: https://github.com/microsoft/autogen
```

### 06、**Flowise**

Flowise 是一个[低代码](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=%E4%BD%8E%E4%BB%A3%E7%A0%81&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiLkvY7ku6PnoIEiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjgzNTkwMDEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.Ppnvs7jo-1mMYuB33JvwQ4Lev2DKnjym5eTqr02TbMk&zhida_source=entity)/无代码的 UI 可视化工具，现在 48k 的 Star 了。

如果你被 LangChain 晦涩的文档劝退了，**不妨先试试 Flowise。**

![动图封面](https://pic3.zhimg.com/v2-d517d078f90ae505446e0191cbd621b0_b.jpg)

通过拖拽的方式构建大模型应用，它**底层基于 LangChain**，用户可以通过连接不同的节点，比如 PDF 加载器、[OpenAI 模型](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=OpenAI+%E6%A8%A1%E5%9E%8B&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiJPcGVuQUkg5qih5Z6LIiwiemhpZGFfc291cmNlIjoiZW50aXR5IiwiY29udGVudF9pZCI6MjY4MzU5MDAxLCJjb250ZW50X3R5cGUiOiJBcnRpY2xlIiwibWF0Y2hfb3JkZXIiOjEsInpkX3Rva2VuIjpudWxsfQ.di4CRYzYer8qO26uogJ9KUpMLQwLxm4eB4vydwhkw48&zhida_source=entity)、Agent[执行器](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=%E6%89%A7%E8%A1%8C%E5%99%A8&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiLmiafooYzlmagiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjgzNTkwMDEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.6Idyu2ntRac9U1RJbNmk1XwkJWSqZrtV7R1xyOVMcTw&zhida_source=entity)等来构建自定义的逻辑流。

对于不擅长写代码但想快速搭建 Agent 原型的用户来说，**这是一个非常友好的平台。**

![](https://picx.zhimg.com/v2-d9e8eb790d30b90f7985766139068f33_1440w.jpg)

```
开源地址: https://github.com/FlowiseAI/Flowise
```

### 07、**[CrewAI](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=CrewAI&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiJDcmV3QUkiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjgzNTkwMDEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.HGClW4FI8j3_GxLkwD_6W_tSOgIkB5s5GP8bAU8BFU4&zhida_source=entity)**

CrewAI 是近年来异军突起的 Python 框架，它主打**角色扮演（Role-Playing）**的编排， 现在已经 42k 的 Star 了。

这个开源项目不像 AutoGen 那么抽象，写 CrewAI 的代码感觉就像是在给员工写任务书，非常清晰易懂，**是 Python 开发者上手多智能体的首选**

![](https://pic3.zhimg.com/v2-b45c5331cec9d6789b174adf1cb85bb6_1440w.jpg)

它让开发者可以轻松定义具有特定角色、目标和背景故事的 Agent，并将它们组成一个团队来按顺序或层级执行任务。

它的设计非常直观，不仅易于上手，而且能很好地与 LangChain 工具生态集成。

```
开源地址: https://github.com/crewAIInc/crewAI
```

### 08、**ChatDev**

这个 28K 星星的开源项目是**清华大学团队 OpenBMB 开源。**

类似于 MetaGPT，ChatDev 也是打造了一个虚拟的软件开发公司。

它通过**聊天链**的方式，让不同角色的智能体（CEO、[CTO](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=CTO&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiJDVE8iLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjgzNTkwMDEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.Shu-LXvBrzDopWwVLf7mCzP3fXaQrZ8Z3VC6Szxg2pA&zhida_source=entity)、程序员、测试员）在如设计、编码、测试、文档等环节进行深度协作。

其特点是过程可视化强，像是在**玩一个[模拟经营游戏](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=%E6%A8%A1%E6%8B%9F%E7%BB%8F%E8%90%A5%E6%B8%B8%E6%88%8F&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiLmqKHmi5_nu4_okKXmuLjmiI8iLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjgzNTkwMDEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.Lvq-A3tzUzgMpmiNWco4MaLFedKxrIzwim7C1fiys_I&zhida_source=entity)一样看着软件被开发出来。**

看着一个个小人儿协作写代码确实很治愈，它为我们展示了未来软件开发的终极形态，非常有启发性。

```
开源地址: https://github.com/OpenBMB/ChatDev
```

### 09、**SuperAGI**

![](https://pic1.zhimg.com/v2-33c230c77b8c25ab33dbd597f8cfcb94_1440w.jpg)

这个自主 AI [智能体框架](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=%E6%99%BA%E8%83%BD%E4%BD%93%E6%A1%86%E6%9E%B6&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiLmmbrog73kvZPmoYbmnrYiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjgzNTkwMDEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.pRIJXd4EmG7Jfah0ZA20aBEG33vEsD1cjL-uDCq7qGo&zhida_source=entity)现在已经 15K 的 Star 了。对于**需要长期稳定运行、监控多个 Agent 的企业级场景来说，这个开源项目基建非常必要。**

它有一套完整的基础设施，开发者用它可以构建、管理和运行自主 Agent。

它拥有图形化界面、Agent 市场、Tools、并发代理运行等功能，旨在解决 AutoGPT 在生产环境中使用难的问题，是一个功能比较完备的 Agent 管理平台。

![](https://pic3.zhimg.com/v2-5cfb2bcad8e2ea1a9244dffc67bb0642_1440w.jpg)

而且还能通过可视化的仪表盘**同时运行和监控多个 Agent**，查看其思维链（Chain of Thought）和执行日志。

开发者可以将自己开发的自定义工具包、[智能体模板](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=%E6%99%BA%E8%83%BD%E4%BD%93%E6%A8%A1%E6%9D%BF&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiLmmbrog73kvZPmqKHmnb8iLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjgzNTkwMDEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.YFY2tZLCLrkdGXK56moCGstbKuKe6r_tf2OH5CvRZrs&zhida_source=entity)发布到市场中供社区复用。

```
开源地址: https://github.com/TransformerOptimus/SuperAGI
```

### 10、**[Letta](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=Letta&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiJMZXR0YSIsInpoaWRhX3NvdXJjZSI6ImVudGl0eSIsImNvbnRlbnRfaWQiOjI2ODM1OTAwMSwiY29udGVudF90eXBlIjoiQXJ0aWNsZSIsIm1hdGNoX29yZGVyIjoxLCJ6ZF90b2tlbiI6bnVsbH0.KdC5eGOh4Hgj5-E2WkzxRfBMzbvMsq1TF0dL0oEt8eA&zhida_source=entity)**

大模型最让人头疼的就是聊着聊着就忘了，Letta 恰好切中了这个痛点。

如果**你想开发一个能陪伴用户几个月、甚至几年的伴侣型应用，一定要看看这个可以构建有状态（Stateful）AI 智能体的[开源框架](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=%E5%BC%80%E6%BA%90%E6%A1%86%E6%9E%B6&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiLlvIDmupDmoYbmnrYiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjgzNTkwMDEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.G9ezZuml9R4U91q_kAT66B-x_FqZLmK42Q0JaEkOR1U&zhida_source=entity)。**

它也是著名的 [MemGPT](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=MemGPT&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiJNZW1HUFQiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjgzNTkwMDEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.mcdSNkckIHatnejlrjFUOS_IREv-Gx3iCFTCYoAcKDw&zhida_source=entity) 项目的继任者和正式化版本。

![](https://pic3.zhimg.com/v2-df8dc6ddc5ed7f133ad28e8cfcee8256_1440w.jpg)

Letta 通过引入类似操作系统的内存管理机制，**让 AI 智能体能够拥有[持久化](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=%E6%8C%81%E4%B9%85%E5%8C%96&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiLmjIHkuYXljJYiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjgzNTkwMDEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.OTho45bflhk0YEriMK4vWm95k2r5QNjrWnZHP5yoWog&zhida_source=entity)的长期记忆，并在不同的会话和时间跨度中保持一致的身份和知识。**

Letta 延续并强化了**大模型即[操作系统](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=2&q=%E6%93%8D%E4%BD%9C%E7%B3%BB%E7%BB%9F&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiLmk43kvZzns7vnu58iLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjgzNTkwMDEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MiwiemRfdG9rZW4iOm51bGx9.rbWbXhXLEKE_IwM5uxrSZhgza3nycheQ89kAvcHlnW8&zhida_source=entity)**的理念。

它通过一种分层内存结构，将信息在当前上下文窗口和[外部数据库](https://zhida.zhihu.com/search?content_id=268359001&content_type=Article&match_order=1&q=%E5%A4%96%E9%83%A8%E6%95%B0%E6%8D%AE%E5%BA%93&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODU5MTYwNTEsInEiOiLlpJbpg6jmlbDmja7lupMiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyNjgzNTkwMDEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.oeNkw4KWjP0GDrWRm0PonMmNENdLyS-J7QagYNrCRqA&zhida_source=entity)之间动态调度。

智能体具备自我编辑记忆的能力，能够自主决定何时将关键信息写入长期存储或从历史记录中检索数据，从而在不增加 Token 消耗的前提下，**实现了理论上无限的上下文窗口。**

![](https://pic1.zhimg.com/v2-331242a31817b66698f18cf0a462f8bc_1440w.jpg)

```
开源地址：https://github.com/letta-ai/letta
```