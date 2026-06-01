---
title: Milvus Hybrid Search 多向量列融合检索
source_url: https://zilliz.com.cn/blog/Hybrid-Search
source_site: Zilliz 向量数据库
author: Zilliz Team
date_extracted: 2026-05-16
credibility: low
tags: [RAG, Milvus, Hybrid Search, 多向量列, RRF, WeightedRanker]
---

# 一文玩转 Milvus 新特性之 Hybrid Search

Milvus 2.4 新增了单 collection 多向量列的支持，同时提供了针对多向量列 hybrid search 的搜索方法。

---

## 多向量列是什么？

多向量列，顾名思义，就是在单个集合里支持多个独立的向量列。不同的向量列可以用来存储和表示：

1. **多个角度的信息**，如电商产品图片的正视图、侧视图和俯视图
2. **不同 embedding 模型的侧重**，比如 dense embedding 更关注整体，而 sparse embedding 更关注局部和关键词
3. **多模态的融合**，如司法刑侦场景下，自然人可以通过指纹、声纹、人脸等不同模态的生物信息表征

---

## 融合策略（Rerank Strategy）

目前 Milvus 可支持的融合策略包括基于排名的 RRF 以及基于 Score 的加权平均算法 WeightedRanker。

### 策略一：RRF

RRF（Ranked Retrieval Fusion，排序检索融合）是一种常见的检索融合算法，此方法侧重于使用排名信息。

**基本步骤：**
1. 召回阶段收集排名：多个检索器对其查询分别生成排序结果
2. 排名融合：使用简单的评分函数（如倒数和）将各检索器的排名位置加权融合

**公式：**

$$RRF(d) = \sum_{i=1}^{N} \frac{1}{k + rank_i(d)}$$

其中：
- $N$ 代表不同召回路的数量
- $rank_i(d)$ 是第 $i$ 个检索器对文档 $d$ 的排名位置
- $k$ 是平滑参数，通常取 60

### 策略二：WeightedRanker

WeightedRanker 分数加权平均算法的核心思想是对多个召回路的输出结果的分数进行加权平均计算。

**基本步骤：**
1. 召回阶段收集分数
2. **分数归一化**：将各路的分数做归一化，使其值落在 [0,1] 之间
3. 权重分配：为每一路分配一个权重 $w_i$，取值范围 [0,1]
4. 分数融合：采用加权平均的方式计算最终得分

**归一化公式：**

由于不同 Metric Type 的 Score 分布范围不一样（IP: [-∞,+∞]，L2: [0,+∞]），Milvus 通过 arctan 函数做归一化。

---

## 多向量列搜索实战

### 场景：多模态图片搜索

**数据集**：交通灯照片
**Target**：一张包含红绿灯和建筑物背景的图片

**向量列配置**：
- 第一列：ResNet（图像特征）
- 第二列：CLIP（文本-图像双模态）

### 单向量列搜索结果

**ResNet 搜索**：返回结果突出【红绿灯】这一对象，但 target 不是最相似的

**CLIP 搜索**：输入 "with buildings at background"，返回结果围绕【建筑物】，target 依旧不是最相似的

### 多向量列搜索

采用平均加权方式融合两路结果，ResNet 和 CLIP 列权重分别设置为 0.7 和 0.8。

**结果**：target 作为最相似 Top1 返回，精准召回。

### 效果分析

通过多向量列和 hybrid search 融合检索，结合了【局部特征+背景信息】，形成更全面的信息输入，获得比单路召回更精准的结果。

---

## 总结

多向量列和 Hybrid Search 是 Milvus 新版本的重要功能，通过融合多种搜索方法的优势，极大提升了搜索的灵活性和准确性。

**未来规划**：
- 拓展基于时间排序的融合
- 加入更强大的 fusion 算法和 rerank model

---

*来源：Zilliz 向量数据库 | 提取日期：2026-05-16*
