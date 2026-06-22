原文： https://www.53ai.com/news/RAG/2026062413409.html

一篇来自 Zleap AI 的论文：**SAG**。
论文标题: SAG: SQL-Retrieval Augmented Generation with Query-Time Dynamic Hyperedges
论文链接: https://arxiv.org/abs/2606.15971
GitHub: https://github.com/Zleap-AI/SAG-Benchmark

这篇论文最有意思的地方是把 GraphRAG 里最重的那部分——结构化多跳检索——交给了 SQL。

过去做 RAG，常见两条路都不完美：向量检索很快，但它更像“找语义相似段落”，不擅长处理实体关系、时间约束和多步依赖；GraphRAG 能补结构，但通常要提前抽三元组、合并实体、维护一张全局图，数据一更新，维护成本就上来了。

SAG 的思路很工程：**别急着先造一张全局图。把 chunk 写成 event，把 entity 写进表，查询来了再用 SQL join 把相关事件临时串起来。**

![[Image 31.png]]

## SAG方案详解

### 1. 先把 chunk 变成 event，而不是拆碎成 triple

SAG 的第一步叫 **Event-Entity Index**。

普通 GraphRAG 经常会把文本拆成三元组，比如“谁—做了什么—对象是谁”。这样确实方便建图，但也容易把一段话里的完整语义拆碎。

SAG 没有这么做。它把每个 chunk 总结成一个 **event**，让 event 保留完整语义；同时从这个 event 里抽出 entity，作为可以被数据库检索和连接的索引点。

论文里 entity 覆盖了 time、location、person、organization、topic、product、action、metric、label 等多类信息。也就是说，一个 event 可以同时连着多种实体：人、地点、时间、组织、动作、指标都能成为后续检索的入口。

大白话说，event 负责“保留这段话到底在讲什么”，entity 负责“让不同事件能被串起来”。一个 event 连着多个 entity，本质上就像一条隐含的超边。

![[Image 32.png]]

### 2. 查询来了，SQL 和向量两条路先找入口

建好 event-entity index 后，SAG 的第二步是 **Seed Retrieval**。

它不是只靠一种检索方式，而是分两路找入口。

第一路是**结构入口**。LLM 先从 query 里抽出 seed entities，再通过 entity vector expansion 找相似实体，最后用 SQL join 找到这些实体关联的 events。

第二路是**语义入口**。直接用 query vector 去 event index 里检索语义相似的 events。

这两路各补一个短板：实体路径更懂结构，但可能漏掉 query 里的隐含语义；向量路径更宽松，可以补回那些没有被实体抽取覆盖的相关事件。最后两路合并，形成初始 candidate event set。

这一点很关键：**SAG 没有把 SQL 和向量检索对立起来，而是让 SQL 负责结构入口，向量负责语义兜底**。

### 3. 真正的新东西：查询时用 SQL join 临时激活超边

SAG 最核心的模块叫 **Query-Time Dynamic Hyperedges**。

传统 GraphRAG 倾向于提前建好图：节点、边、全局结构都先算出来。SAG 反过来：**不提前枚举全局超边，而是在当前 query 的候选空间附近临时激活局部结构**。

具体做法是：先拿 seed events，反向 SQL join 找到它们关联的 frontier entities；再用这些 frontier entities 继续 join 找新的 events，最多扩展 H hops，论文默认 H=1。

所以它的多跳扩展本质不是 PageRank，也不是全图传播，而是数据库里的 join：

- event 找 entity；
    
- entity 再找 event；
    
- 围绕当前问题扩出一片局部结构；
    
- 检索结束后，这个局部结构也就结束。
    

查询一来，SQL 把共享实体的事件临时拉到一个局部关系网里；查询结束，不需要维护这张临时网。

![[Image 33.png]]

Table也说明了 query-time expansion 的价值：没有 expansion 时，MuSiQue Recall@5 是 69.4；加入 expansion 后达到 80.0。对多跳问题来说，这一步不是装饰，而是把断开的证据链接起来的关键。

## 输出不是一条路：结构路径 + 语义路径一起给答案

SAG 的最后输出也分两路。

第一路是**结构路径**。它先把候选 events 粗排到 `Kcand=100`，再让 LLM rerank，选出 `Kevent=5` 个最相关事件，然后映射回原始 chunk。

第二路是**语义路径**。query vector 直接检索 `Kdirect=5` 个 chunks。

这套设计很实用：结构路径负责找多跳证据链，语义路径负责保留直接命中的原文段落。两路合并后，既不完全依赖图结构，也不退回纯向量检索。

![[Image 34.png]]

Table里这个对比很直观：纯语义路径在 MuSiQue 上 Recall@5 是 56.2；加入 5 个 event-derived candidates 后，Recall@5 到了 80.0。

也就是说，event 路径不是锦上添花，而是在多跳检索里真正补上了结构能力。

## 结果

论文在 HotpotQA、2WikiMultiHopQA、MuSiQue 三个多跳问答基准上做了实验。

主结果里，SAG 在 9 个 Recall@K 指标中拿到 8 个最好。平均 Recall@2 / Recall@5 分别是 79.3% / 88.2%，高于 HippoRAG 2 的 68.2% / 83.3%。

在最考验多跳链路的 MuSiQue 上，差距尤其明显：SAG Recall@5 = 80.0，而 HippoRAG 2 是 65.1；SAG Recall@2 = 64.1，而 HippoRAG 2 是 49.5。

![[Image 35.png]]

论文还做了 event-level hyperedge 和 triple-decomposition 的对比。Table 3 中，hyperedge 版本 MuSiQue Recall@5 是 80.0，高于 triple 的 77.1。

![[Image 36.png]]

这也符合直觉：多跳问答需要的不只是“关系边”，还需要一段事件里的完整上下文。如果过早拆成三元组，结构有了，但语义可能丢了。

## 总结

SAG 的核心贡献可以压成一句话：**它把多跳 RAG 从“先建全局图”改成了“查询时用 SQL join 激活局部结构”。**

论文里使用 MySQL 做结构化存储，Elasticsearch 做全文和 dense vector 检索。新数据来了，不需要重建全局图，只需要 append event 和 entity 记录；查询时再通过 SQL join 动态激活局部结构。

它保留了 GraphRAG 对结构关系的利用，又避免了全局图维护的高成本；它保留了向量检索的语义召回，又用 event-entity index 和 SQL join 把多跳证据链补了回来；它仍然使用 LLM，但把 LLM 放在候选压缩后的 rerank 环节。

但它的方向很清楚：如果 GraphRAG 想真正进入生产系统，可能不该只问“图怎么建得更大”，也要问“哪些结构其实可以查询时再临时生成”。
