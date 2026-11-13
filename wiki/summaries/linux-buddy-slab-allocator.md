---
title: 伙伴分配器与 SLAB 分配器
category: summaries
tags: [linux, 内核, 内存, 伙伴系统, slab]
aliases: [伙伴分配器, Buddy Allocator, SLAB分配器, kmem_cache]
relationships:
  - target: "[[concepts/linux-memory-management]]"
    type: related_to
  - target: "[[summaries/linux-meminfo-params]]"
    type: related_to
source_dir: Linux 操作系统/Linux 内存管理
source_files: [Linux 伙伴分配器与 SLAB 分配器.md]
summary: 物理内存分配的两级分工：伙伴系统按 2^n 页管理大块页框、靠分裂/合并对抗外部碎片；SLAB 从伙伴取页再切成固定大小对象、用 kmem_cache 对抗内部碎片。含分配释放流程、伙伴地址公式、/proc/buddyinfo 与 /proc/slabinfo 读法。
provenance:
  extracted: 0.88
  inferred: 0.09
  ambiguous: 0.03
base_confidence: 0.44
lifecycle: draft
lifecycle_changed: 2026-11-12
tier: supporting
created: 2026-11-12
updated: 2026-11-12
---

# 伙伴分配器与 SLAB 分配器

Linux 物理内存分配不是一套算法，而是两级分工：**伙伴系统负责"页框"**（以 4KB 页为单位的 2^n 连续块），**SLAB 负责"对象"**（内核结构体这类几十字节到几 KB 的小内存）。前者解决外部碎片，后者解决内部碎片。^[inferred]

## 核心观点

- **阶（Order）是伙伴系统的唯一尺度**：n 阶页块 = `2^n` 个连续页；0 阶 1 页、5 阶 32 页（128KB）、9 阶 512 页（2MB）。
- **分配 = 向上取整 + 逐级分裂**：请求 100KB（约 25 页）向上取整到 5 阶（32 页）；目标阶无空闲就向更高阶借，分裂到目标阶，剩余半块挂回对应阶的空闲链表。
- **释放 = 查伙伴 + 递归合并**：释放后若"伙伴"空闲则合并为高一阶，继续向上合并直到无法合并；不合并则挂入当前阶链表。
- **伙伴地址由异或算出**：`伙伴地址 = 块地址 ^ (1 << (order + PAGE_SHIFT))`，PAGE_SHIFT 通常为 12（4KB 页）。
- **内部碎片是伙伴系统的固有代价**：3 页请求分配 4 页（浪费 25%）、5 页请求分配 8 页（浪费 37.5%）；这正是 SLAB 存在的理由。
- **SLAB 的三级结构是 cache → slab → object**：`kmem_cache` 按对象类型划分（如 `task_struct`），每个 slab 由一个或多个连续页组成，再切成等长对象；分配/释放是 O(1)。
- **两者是上下游而非替代**：SLAB 的页来自伙伴系统，伙伴系统不直接服务小对象；内核启动后绝大多数小分配走 SLAB，页表/DMA 等大块才直接走伙伴。 ^[inferred]

## 关键细节

### 伙伴系统的数据结构

| 结构 | 作用 |
|---|---|
| `free_area[]` | 每个内存 zone 一个数组，下标即阶数（0~MAX_ORDER） |
| `free_list` | 每个阶按迁移类型（Unmovable/Movable/Reclaimable 等）挂空闲页块 |
| `nr_free` | 当前阶空闲页块计数 |
| `per_cpu_pages` | 每 CPU 缓存小阶页块（常见 0~3 阶），减少 zone 锁竞争 |

### 分配与释放流程

```
分配 order=n：
  查 free_area[n] → 空则向 n+1、n+2… 找
  找到 order=m 的空闲块 → 逐级对半分裂 → 取一半，另一半挂回
  返回页块起始地址

释放 order=n：
  计算伙伴地址 → 伙伴空闲且同阶？
    是 → 合并为 n+1 阶 → 继续向上检查
    否 → 挂入 free_area[n]
```

### 一个 16 页（64KB）的手算例子

| 步骤 | 结果 |
|---|---|
| 初始 | 1 个 4 阶块（16 页） |
| 申请 3 页 | 取整 4 页（2 阶）；4 阶分裂成两个 3 阶，再分裂出一个 2 阶；分配 `0x0000`，剩余 2 阶 `0x1000`、3 阶 `0x2000` |
| 申请 1 页 | 2 阶 `0x1000` 分裂成两个 1 阶，再分裂出一个 0 阶；分配 `0x1000`，剩 0 阶 `0x1400`、1 阶 `0x1800` |
| 申请 6 页 | 取整 8 页（3 阶），直接分配 `0x2000` |
| 释放 0x0000（2 阶） | 伙伴 `0x4000` 非空闲 → 直接挂 2 阶链表 |
| 释放 0x1000（0 阶） | 伙伴 `0x1400` 空闲 → 合并 1 阶；再与 `0x1800` 合并为 2 阶 `0x1000` |

### 内部碎片量化

| 请求大小 | 实际分配 | 碎片率 |
|---|---|---|
| 1 页 | 1 页 | 0% |
| 3 页 | 4 页 | 25% |
| 5 页 | 8 页 | 37.5% |
| 7 页 | 8 页 | 12.5% |

### 观测接口

- **`/proc/buddyinfo`**：`Node 0, zone DMA 1 1 0 0 2 ...`，从左到右是 order 0、1、2… 的空闲块数，可直接看出高阶块是否枯竭（外部碎片信号）。
- **`/proc/pagetypeinfo`**：按 migrate type 分列各阶空闲页数，并给出 `Page block order`（常见 9，即 2MB）与每块页数；用于判断 Movable/Unmovable 的碎片结构。
- **`/proc/slabinfo`**：`name active_objs num_objs objsize objperslab pagesperslab`，可算对象利用率；活跃对象长期接近总数说明缓存偏小，长期为 0 说明缓存可回收。^[inferred]

### SLAB 的工作流程

1. `kmem_cache_create("task_struct", sizeof(struct task_struct), ...)` 创建专用缓存；
2. `kmem_cache_alloc(cache, GFP_KERNEL)` 取对象；
3. `kmem_cache_free(cache, obj)` 归还；
4. `kmem_cache_destroy(cache)` 销毁缓存（模块卸载时）。

### 两者对比

| 特性 | 伙伴分配器 | SLAB 分配器 |
|---|---|---|
| 管理单元 | 物理页框 | 内核对象 |
| 分配粒度 | 4KB~几 MB | 几十字节~几 KB |
| 主要目标 | 大块连续内存 | 小对象高效复用 |
| 碎片类型 | 外部碎片 | 内部碎片 |
| 时间复杂度 | O(log n) | O(1) |
| 典型场景 | 页表、DMA 缓冲 | task_struct、inode、dentry |

## 未解问题

- 现代内核的 SLUB 已取代 SLAB 成为默认实现，本文的 `kmem_cache` 语义仍适用，但 per-CPU 结构与调试接口（`/sys/kernel/slab`）未覆盖。 ^[ambiguous]
- `MAX_ORDER` 与 CMA/大页预留的交互、`/proc/buddyinfo` 高阶块长期为 0 时的调优手段，源文未展开。 ^[inferred]
- 迁移类型（migratetype）如何影响碎片整理与 `compaction`，本文只给了观测方法。 ^[inferred]

## 来源

- `raw/sources/Linux 操作系统/Linux 内存管理/Linux 伙伴分配器与 SLAB 分配器.md` — 原文：blog.csdn.net/weixin_45842280/article/details/149341321（含 buddyinfo/pagetypeinfo/slabinfo 实测截图）
- 交叉：[[concepts/linux-memory-management]]（meminfo 与 LRU 回收）、[[summaries/linux-meminfo-params]]（Slab/SReclaimable 字段口径）
