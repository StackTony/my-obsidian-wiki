---
title: Linux内存管理
category: concepts
tags: [linux, 内存, 页缓存, 内核]
aliases: [Linux Page Cache, Linux meminfo]
relationships:
  - target: "[[concepts/linux-io-stack]]"
    type: uses
  - target: "[[concepts/linux-lock-mechanisms]]"
    type: related_to
source_dir: Linux 操作系统/Linux 内存管理
source_files: [Linux meminfo参数详细解释.md, Linux 页缓存（Page Cache）.md]
summary: Linux内存管理两大支柱：meminfo参数体系(MemTotal/MemFree/MemAvailable/LRU/Slab/Swap)和页缓存架构。Page Cache = Buffers + Cached + SwapCached。
provenance:
  extracted: 0.80
  inferred: 0.15
  ambiguous: 0.05
base_confidence: 0.608
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: supporting
created: 2026-06-01
updated: 2026-06-01
---

# Linux内存管理

## 核心观点

### meminfo参数体系

`/proc/meminfo`是理解Linux内存的主要接口，核心参数：

| 参数 | 含义 | 特性 |
|---|---|---|
| MemTotal | 内核可用总内存 | 系统运行期间固定 |
| MemFree | 未使用内存 | 立即可分配 |
| MemAvailable | 估计可用内存 | 包含可回收部分 |
| Active/Inactive | LRU链表 | 区分近期/长期未访问 |
| Slab | 内核slab分配器内存 | 含可回收(SReclaimable)和不可回收(SUnreclaim) |

**关键等式**：
- `Page Cache = Buffers + Cached + SwapCached`
- `Cached = Active(file) + Inactive(file) + Shmem - Buffers`

### 内存黑洞问题

内核通过`alloc_pages/__get_free_page`分配的内存不自动统计，是追踪内存使用的盲区。典型例子：VMware Balloon driver通过alloc_pages占用guest内存，但meminfo看不出去向^[inferred]。

### 页缓存架构

Linux 2.4后buffer cache合并进Page Cache，统一管理：

- **File-backed pages**：对应磁盘文件数据块，回收代价低(可直接从磁盘重读)
- **Anonymous pages**：进程堆栈等无文件对应，回收需swap到磁盘

Page Cache用radix tree组织，按文件偏移量快速定位page。

### Write Through vs Write Back

两种缓存一致性策略：

| 方式 | 特点 | 适用场景 |
|---|---|---|
| Write Through | 写入立即落盘 | 数据安全优先 |
| Write Back(默认) | 写缓存，周期回盘 | 性能优先，宕机可能丢数据 |

Write Back由内核线程周期执行脏页回写，每个存储设备一个刷新线程^[inferred]。

### LRU页面回收算法

页面按访问频率分层：

- **Active list**：最近被访问的页面
- **Inactive list**：长时间未访问，优先回收

回收时优先选Inactive list中的clean pages，避免I/O开销。

### Swap机制

匿名页和Shmem(共享内存/tmpfs)需要swap：

- **SwapCached**：曾经swap-out又swap-in的页面，内容未变，再次swap无需I/O
- 与Cached不重叠，两者独立统计

### 文件页vs匿名页swap成本

| 页类型 | swap成本 | 原因 |
|---|---|---|
| File-backed | 低 | 可直接从原文件读取，无需写swap |
| Anonymous | 高 | 必须写入swap设备才能释放 |

`swappiness`参数(0-100)控制系统swap倾向。

## 未解问题

- Hugepages与Transparent HugePages(THP)的性能差异？
- 内存压缩(compaction)与碎片整理机制？

## 来源

- `raw/sources/Linux 操作系统/Linux 内存管理/Linux meminfo参数详细解释.md` — 参数含义、内存黑洞、Slab/Vmalloc统计
- `raw/sources/Linux 操作系统/Linux 内存管理/Linux 页缓存（Page Cache）.md` — Page Cache架构、预读机制、Write Through/Back对比