---
title: 深入理解rerank重排序的工作原理
source_url: https://juejin.cn/post/7440705321942663207
source_site: 稀土掘金
author: 掘金团队
date_extracted: 2026-05-16
credibility: low
tags: [RAG, Rerank, Bi-Encoder, Cross-Encoder, Embedding, Pinecone]
---

# 深入理解rerank重排序的工作原理

---

## 一、为什么需要重排序？

RAG通过在大量文本文档中进行语义搜索来工作。向量搜索将文本压缩成768或1536维向量，这一过程不可避免地会**丢失一些信息**。

**召回率问题**：即使是排名前三的文档，也可能遗漏了一些关键信息。

### 解决方案

通过检索尽可能多的文档来最大化检索召回率，然后通过重排序只保留最相关的文档。

---

## 二、什么是重排序算法？

重排序模型（Cross-Encoder）是一种能够针对查询和文档对输出相似度分数的模型。

### 二阶段检索系统

```
第一阶段（检索器）: 从大数据集提取一组相关文档
第二阶段（重排序器）: 对提取出的文档进行重新排序
```

---

## 三、Bi-Encoder vs Cross-Encoder

### Bi-Encoder（双编码器）

**工作方式**：Query和Document各自独立编码成向量

**优点**：
- 检索快
- 可ANN加速
- 文档可预计算索引

**缺点**：
- 信息压缩导致语义丢失
- 查询和文档缺乏交互
- 语義理解有限

### Cross-Encoder（交叉编码器）

**工作方式**：Query + Document拼接后输入Transformer

**优点**：
- 精度高
- 上下文理解强
- 细粒度语义分析

**缺点**：
- 计算成本高
- 无法预计算索引
- 实时性受限

---

## 四、为什么Cross-Encoder精度更高？

### 1. 查询和文档的联合编码

Cross-Encoder将Query和Document作为一个整体输入，通过Transformer层捕获两者之间的细粒度语义关系。

**Input**: `[CLS]Query Tokens[SEP]Document Tokens[SEP]`

### 2. 细粒度的词级交互

查询中的每个词可以与文档中的每个词进行关联。

例如：
- Query: "What is the capital of France?"
- Document: "Paris is the capital city of France."

Cross-Encoder可以直接识别：
- "capital" ↔ "capital city"
- "France" ↔ "France"
- "What is" ↔ "Paris is"

### 3. 利用上下文信息

查询的词义可以因文档内容而变化。

### 4. 避免信息压缩

Bi-Encoder必须将文档的所有潜在含义压缩成一个向量。Cross-Encoder直接处理原始信息。

### 5. 实验结果支持

- Bi-Encoder: 70-80% 精度
- Cross-Encoder: 95%+ 精度

---

## 五、效率代价

假设4000万条记录，使用BERT在V100 GPU上：

| 方法 | 时间 |
|------|------|
| Cross-Encoder | >50小时 |
| Bi-Encoder + ANN | <100毫秒 |

**因此**：Cross-Encoder通常用于二阶段排序，而不是大规模初筛。

---

## 六、Embedding Model局限性总结

| 局限性 | 说明 |
|--------|------|
| 信息压缩 | 固定大小向量丢失信息 |
| 缺乏动态交互 | Query和Document独立编码 |
| 长文档处理困难 | 无法识别相关段落 |
| 复杂语义关系 | 难以捕捉否定、因果等 |
| 多义性问题 | "bank"可能是银行或河岸 |
| 领域适配受限 | 需要领域微调 |

---

## 七、总结

**最佳实践**：两阶段检索系统

```
Bi-Encoder + ANN → 快速初筛（Top 100）
    ↓
Cross-Encoder → 精确重排（Top 5-10）
    ↓
LLM → 生成答案
```

兼顾效率与效果。

---

*来源：稀土掘金 | 翻译自Pinecone | 提取日期：2026-05-16*