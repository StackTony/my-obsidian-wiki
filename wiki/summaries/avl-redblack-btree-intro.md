---
title: AVL/红黑树/B树介绍原文摘要
category: summaries
tags: [数据结构, AVL, 红黑树, B树, B+树]
source_dir: 数据结构与算法/树
source_files: [AVL树、红黑树以及B树介绍.md]
summary: BST→AVL→红黑树→B/B+树演进路线、各树特性对比、B+树更适合数据库索引的两大原因
provenance:
  extracted: 0.85
  inferred: 0.12
  ambiguous: 0.03
base_confidence: 0.70
lifecycle: draft
lifecycle_changed: 2026-06-11
tier: supporting
created: 2026-06-11
updated: 2026-06-11
---

# AVL/红黑树/B树介绍原文摘要

来源：`raw/sources/数据结构与算法/树/AVL树、红黑树以及B树介绍.md`

## 概述

树结构平衡了数组查询O(1)和链表插入删除O(n)的差距。从BST到AVL到红黑树到B/B+树是逐步放松平衡约束的演进路线。

## 核心观点

- **BST**：有序插入退化为链表O(N)，随机插入接近平衡O(logN)
- **AVL**：严格平衡(高度差≤1)，查找O(logN)，但增删旋转开销大。应用：Windows进程地址空间管理
- **红黑树**：弱平衡(最长≤2×最短)，增删O(1)次旋转。应用：C++ STL map/set、Linux CFS、epoll、nginx timer、Java TreeMap
- **B树**：m阶多路搜索树，搜索等价于全集二分查找，适合磁盘存储
- **B+树**：所有数据在叶子节点+链指针，分支节点纯索引。比B树更适合数据库索引：内部节点更小→IO更少、查询路径稳定、范围遍历高效

## 关键差异

- B树：m子节点m-1关键字，数据在所有节点
- B+树：m子节点m关键字，数据只在叶子节点，叶子有链指针