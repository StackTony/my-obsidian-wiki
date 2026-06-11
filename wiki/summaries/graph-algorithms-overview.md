---
title: 图论算法全景原文摘要
category: summaries
tags: [数据结构, 图论, BFS, DFS, 最短路]
source_dir: 数据结构与算法/图
source_files: [图 合集.md]
summary: 图论算法学习路线全景图：BFS/DFS→并查集→最短路→拓扑→MST→强连通→二分图→网络流
provenance:
  extracted: 0.75
  inferred: 0.20
  ambiguous: 0.05
base_confidence: 0.65
lifecycle: draft
lifecycle_changed: 2026-06-11
tier: supporting
created: 2026-06-11
updated: 2026-06-11
---

# 图论算法全景原文摘要

来源：`raw/sources/数据结构与算法/图/图 合集.md`

## 概述

图论算法必学全景路线图，从基础概念到高阶网络流，含经典模型与代码模板清单。

## 核心观点

- **两大遍历是根基**：BFS(最短无权路径/层序) + DFS(连通性/环/回溯)
- **最短路四算法**：Floyd(多源暴力O(n³)) > Dijkstra(单源无负权) > Bellman-Ford(负权可跑) > SPFA(队列优化BF，日常最常用)
- **拓扑排序**：入度表+BFS，判环+任务编排+编译依赖
- **MST**：Prim(贪心扩展) + Kruskal(排序选边+并查集)
- **并查集是图论神器**：连通性判断+Kruskal必备+岛屿朋友圈
- **Tarjan SCC**：有向图缩点O(n+m)，割点割边
- **二分图**：染色判定+匈牙利最大匹配+König定理
- **网络流进阶**：Dinic最大流+最小割+费用流
- **学习路线**：图基础→邻接表→BFS/DFS→并查集→最短路→拓扑→生成树→强连通→二分图→网络流