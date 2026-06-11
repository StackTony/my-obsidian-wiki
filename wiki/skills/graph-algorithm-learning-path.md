---
title: 图论算法学习路线
category: skills
tags: [数据结构, 图论, 学习路线, 算法]
source_dir: 数据结构与算法/图
source_files: [图 合集.md]
summary: 图论算法从入门到进阶的学习路线、代码模板清单和经典模型映射
provenance:
  extracted: 0.60
  inferred: 0.35
  ambiguous: 0.05
base_confidence: 0.65
lifecycle: draft
lifecycle_changed: 2026-06-11
tier: supporting
created: 2026-06-11
updated: 2026-06-11
relationships:
  - target: "[[concepts/graph-algorithms]]"
    type: implements
---

# 图论算法学习路线

## 前置条件

- 基础数据结构：数组、链表、栈、队列
- 基础算法：递归、排序
- 编程语言基础

## 学习路线

### 第1步：图基础 + 邻接表

- 理解有向图/无向图、有权图/无权图
- 掌握邻接矩阵和邻接表两种存储方式
- **邻接表是最常用存储**（稀疏图省空间）
- 代码：邻接表建图模板

### 第2步：BFS + DFS

- BFS：队列实现，层序遍历，最短无权路径
- DFS：递归/栈实现，连通性判断，环检测
- 代码：BFS模板 + DFS递归+迭代模板

### 第3步：并查集

- 合并集合 + 查找根节点
- 路径压缩 + 按秩合并 → 近O(1)
- 应用：连通性判断、朋友圈、岛屿数量
- 代码：并查集模板

### 第4步：最短路

- Floyd → Dijkstra → Bellman-Ford → SPFA（按难度递进）
- Dijkstra堆优化是重点
- SPFA日常最常用
- 代码：堆优化Dijkstra模板 + SPFA模板

### 第5步：拓扑排序

- 入度表 + BFS方法
- 判环、任务编排、编译顺序
- 代码：拓扑排序模板

### 第6步：最小生成树

- Prim（贪心扩展）
- Kruskal（排序选边 + 并查集）
- 代码：Prim模板 + Kruskal模板

### 第7步：强连通分量

- Tarjan SCC算法（O(n+m））
- 有向图缩点
- 代码：Tarjan模板

### 第8步：二分图

- 染色判定
- 匈牙利算法最大匹配
- König定理

### 第9步：网络流（进阶）

- Dinic最大流
- 最小割（最大流最小割定理）
- 费用流

## 经典题目映射

| 题目 | 对应算法 | 学习阶段 |
|------|----------|----------|
| 岛屿数量 | BFS/DFS/并查集 | 第2-3步 |
| 省份数量 | 并查集/DFS | 第3步 |
| 迷宫最短路径 | BFS | 第2步 |
| 课程表 | 拓扑排序 | 第5步 |
| 朋友圈 | 并查集 | 第3步 |
| 物流最短路 | Dijkstra/SPFA | 第4步 |
| 行程规划 | Dijkstra | 第4步 |
| 二分图匹配排班 | 匈牙利算法 | 第8步 |

## 常见问题

- **邻接矩阵vs邻接表**：稀疏图用邻接表（省空间），稠密图可用邻接矩阵
- **Dijkstra不能处理负权边**：有负权用Bellman-Ford或SPFA
- **SPFA可能被卡**：最坏O(nm)，特殊构造数据会退化^[ambiguous]
- **BFS/DFS选择**：求最短无权路径用BFS，其余DFS更灵活

## 进阶方向

- 网络流 → 最大流最小割定理 → 费用流
- 树上问题 → LCA → 树链剖分
- 计算几何图论 → 凸包 → 最近点对