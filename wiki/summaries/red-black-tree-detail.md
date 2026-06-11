---
title: 红黑树详解原文摘要
category: summaries
tags: [数据结构, 红黑树, AVL, 平衡树]
source_dir: 数据结构与算法/树
source_files: [红黑树详解.md]
summary: 红黑树五大性质、与4阶B树等价、12种插入情况、5类删除修复、AVL vs红黑树完整对比原文摘要
provenance:
  extracted: 0.88
  inferred: 0.10
  ambiguous: 0.02
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-11
tier: supporting
created: 2026-06-11
updated: 2026-06-11
---

# 红黑树详解原文摘要

来源：`raw/sources/数据结构与算法/树/红黑树详解.md`

## 概述

红黑树由Rudolf Bayer于1978年发明（平衡二叉B树），后被Guibas和Sedgewick改为红黑树。是一种自平衡二叉查找树，查找/插入/删除均为O(logN)。应用广泛：Java TreeMap、JDK1.8 HashMap、C++ STL map。

## 核心观点

- **五大性质**：节点红或黑、根黑、叶子(null)黑、红色子节点黑、任一路径黑节点数相同
- **等价4阶B树**：红节点上移与父同层即形成4阶B树；黑色节点中间、红色节点两边
- **插入12种情况**：4种parent黑色(不需修复)+4种uncle非红(染色+旋转)+4种uncle红(上溢合并)
- **删除**：红色直接删；1个红色子节点→替代染黑；黑色叶子→兄弟借出/父向下合并/兄弟红先转黑
- **AVL vs红黑树**：AVL严格平衡(高度差≤1)查找更快；红黑树弱平衡旋转更少，混合操作场景更优

## 未解问题

- 红黑树删除黑色叶子节点时兄弟为红色→转黑色后的修复递归是否总能终止？
- Windows进程地址空间管理用AVL而非红黑树的具体原因未说明