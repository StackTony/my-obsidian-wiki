github仓地址：
https://github.com/vibrantlabsai/ragas

### 一、项目基本信息
**Ragas**（Retrieval Augmented Generation Assessment）是 **VibrantLabsAI** 开源的 **RAG/LLM 应用评估框架**（Apache 2.0 协议），
它核心解决：**RAG 好坏靠主观感觉、没有统一量化指标、迭代没数据闭环**的问题，口号是：**把“感觉对”变成“数据证明对”**。

> 注：早期仓库名为 `explodinggradients/ragas`，后迁移到 `vibrantlabsai/ragas`，是同一个项目。

---

### 二、核心定位与价值
- **定位**：LLM 应用（尤其 RAG）的**自动化、可量化、可对比**评估工具。
- **核心价值**：
  1. **客观指标**：用 LLM 评估 LLM，减少人工主观判断。
  2. **全链路评估**：覆盖**检索 → 生成 → 端到端**，不是只看最终回答。
  3. **自动造测试集**：不用人工标注，基于文档自动生成问题/答案/上下文。
  4. **可对比、可迭代**：版本间指标对比，快速定位哪次改动导致效果下降。

---

### 三、核心指标（最常用 4 个）
Ragas 把评估分成**检索质量**和**生成质量**两大块：

#### 1）检索层指标
- **Context Precision（上下文精确率）**：检索出来的片段，有多少是**真正相关**的。
- **Context Recall（上下文召回率）**：所有相关片段里，有多少被**成功检索**到。

#### 2）生成层指标
- **Faithfulness（忠实度）**：回答里的事实，**必须全部来自检索上下文**，无幻觉（Hallucination）。
- **Answer Relevancy（答案相关性）**：回答**直接、完整**地解决用户问题，不跑题、不冗余。

除此之外，还有：**Answer Correctness、Completeness、AspectCritic（自定义维度）**等 20+ 指标。

---

### 四、核心功能
1. **一键评估（5 行代码）**
```python
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy

# 传入：问题、检索上下文、生成答案
result = evaluate(
    dataset=my_rag_dataset,
    metrics=[faithfulness, answer_relevancy]
)
print(result)  # 输出各指标分数（0~1）
```

2. **自动生成测试集**
- 输入：一堆文档（PDF/MD/TXT）
- 输出：自动生成**问题 + 答案 + 上下文**的测试样本，支持事实、推理、对比类问题。

3. **框架无缝集成**
- 支持：**LangChain、LlamaIndex、Haystack** 等主流 RAG 框架。
- 支持：OpenAI、Anthropic、本地部署 LLM（如 Llama 2）。

4. **实验对比与可视化**
- 每次改动（换 Embedding、换切块策略、换 Prompt）都跑一次评估，**指标自动对比**，直观看到“改坏了还是改好了”。

---

### 五、Ragas vs 传统评估（BLEU/ROUGE）
- **传统（BLEU/ROUGE）**：只看**文本表面相似度**，不理解语义，无法检测幻觉，不适合 RAG。
- **Ragas**：**语义级评估**，用 LLM 判断“事实是否来自上下文”“回答是否解决问题”，更贴近真实用户体验。

---

### 六、典型使用场景
- ✅ **RAG 系统迭代**：换 Embedding、切块大小、Prompt 时，量化对比效果。
- ✅ **上线前验收**：批量测试，确保无幻觉、无跑题。
- ✅ **监控生产质量**：定期抽样评估，发现回答质量下降。
- ✅ **AI Agent 评估**：多轮对话、工具调用的正确性评估。

---

### 七、简单总结
- **GraphRAG**：帮你**建知识图谱**，提升 RAG 的**多跳推理、全局问答**能力。
- **Ragas**：帮你**量化评估 RAG 好坏**，确保**没幻觉、回答相关、检索精准**。

一句话：**GraphRAG 负责“变强”，Ragas 负责“验真”**。