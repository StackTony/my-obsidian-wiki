---
title: 红黑树
category: concepts
tags: [数据结构, 红黑树, AVL, 平衡树, B树]
source_dir: 数据结构与算法/树
source_files: [红黑树详解.md, AVL树、红黑树以及B树介绍.md]
summary: 红黑树五大性质、与4阶B树等价性、12种插入+5类删除修复策略、AVL vs红黑树选型指南
provenance:
  extracted: 0.80
  inferred: 0.15
  ambiguous: 0.05
base_confidence: 0.82
lifecycle: draft
lifecycle_changed: 2026-06-11
tier: supporting
created: 2026-06-11
updated: 2026-06-11
relationships:
  - target: "[[concepts/binary-tree-basics]]"
    type: extends
  - target: "[[concepts/b-tree-bplus-tree]]"
    type: related_to
---

# 红黑树

红黑树是一种自平衡的二叉查找树，由 Rudolf Bayer 于1978年发明（当时称"平衡二叉B树"），后被 Guibas 和 Sedgewick 修改为红黑树。它在 O(logN) 时间内完成查找、插入、删除，广泛应用于 Java TreeMap、JDK1.8 HashMap、C++ STL map、Linux CFS 进程调度、epoll sockfd 管理、nginx timer。参见 [[synthesis/balanced-tree-evolution|平衡树演进]] 分析红黑树在平衡策略演进中的位置。

## 为什么需要红黑树

二叉搜索树对有序数据插入会退化为链表（O(N)），AVL树严格平衡但插入删除旋转开销大。红黑树用"弱平衡"换取旋转次数降低——**保证最长路径不超过最短路径的2倍**，而非AVL的严格高度差≤1。

## 五大性质

1. 节点是红色或黑色
2. **根是黑色**
3. **叶子节点（null节点）都是黑色** — 注意：红黑树的"叶子节点"指最底层null节点，不是图上最后一层的有效节点
4. **红色节点的子节点都是黑色**（即不能有2个连续红色节点）
5. **从任一节点到叶子节点的所有路径包含相同数目的黑色节点**（黑高度平衡）

性质5是最容易误判的：判断红黑树时必须算上null节点，而非图上的"最后一层"。

## 与4阶B树的等价性

红黑树与4阶B树（2-3-4树）具有等价性——将红色节点上移到与父节点同层，就形成4阶B树结构：

- 黑色节点+红色子节点融合 → 1个B树节点
- 黑色节点在中间，红色节点在两边
- 红黑树的黑色节点数 = 4阶B树节点总数

这种等价性是理解红黑树插入/删除修复策略的关键框架——所有修复本质上都是在维护等价B树的结构约束。^[inferred]

## 插入操作（12种情况）

新插入节点设为**红色**（仅可能违反性质4，比插入黑色节点调整简单）。

| 父节点颜色 | uncle颜色 | 情况数 | 修复方法 |
|-----------|-----------|--------|----------|
| **黑色** | — | 4种 | 不需处理，性质自动满足 |
| **红色** | 不是红色 | 4种(LL/RR/LR/RL) | 染色+旋转 |
| **红色** | 是红色 | 4种(上溢LL/RR/LR/RL) | 染色+上溢合并 |

### 非上溢修复（uncle不是红色）

- **LL/RR**：parent染黑、grand染红、grand单旋（LL右旋、RR左旋）
- **LR/RL**：插入节点染黑、grand染红、双旋（LR: parent左旋+grand右旋; RL: parent右旋+grand左旋）

### 上溢修复（uncle是红色）

- parent、uncle染黑；grand染红并向上合并（递归处理，若上溢到根则根染黑）

## 删除操作

删除节点一定在最后一层（B树中最终删除都在叶子节点）。

### 删除红色节点 → 直接删除，无需调整

### 删除黑色节点（3种）

| 子节点 | 修复方法 |
|--------|----------|
| **1个红色子节点** | 子节点替代+染黑 |
| **黑色叶子节点（兄弟为黑色，有红色子节点）** | 旋转+中心节点继承父色+左右染黑 |
| **黑色叶子节点（兄弟为黑色，无红色子节点）** | 父节点向下合并：兄弟染红、父染黑；若父为黑色则递归处理父的下溢 |
| **黑色叶子节点（兄弟为红色）** | 先转换：兄弟染黑、父染红、对父旋转 → 回到兄弟为黑色的情况 |

## AVL树 vs 红黑树

| 对比维度 | AVL树 | 红黑树 |
|----------|-------|--------|
| 平衡标准 | 严格：高度差≤1 | 弱平衡：最长路径≤2倍最短路径 |
| 最大高度 | 1.44×log₂n（100W节点→28层） | 2×log₂(n+1)（100W节点→40层） |
| 查找 | 更快（树更矮） | 略慢（树更高） |
| 插入 | O(1)次旋转 | O(1)次旋转 |
| 删除 | O(logn)次旋转 | O(1)次旋转 |
| 选型原则 | 查找远多于插入删除 | 查找/插入/删除频率相近 |

**选型决策**：查找为主选AVL，混合操作选红黑树。红黑树统计平均性能优于AVL，实际应用中更多选用红黑树。

## 实际应用

- Java TreeMap/HashMap（JDK1.8链表转红黑树阈值8）
- C++ STL map/set
- [[concepts/linux-process-scheduling|Linux CFS 进程调度]]（管理进程控制块，按vruntime排序选择下一个进程）
- Linux epoll（管理sockfd）
- nginx timer管理
- Windows进程地址空间管理（AVL）^[ambiguous]

## 来源

- [[summaries/red-black-tree-detail]] — 红黑树详解原文摘要
- [[summaries/avl-redblack-btree-intro]] — AVL/红黑树/B树介绍原文摘要