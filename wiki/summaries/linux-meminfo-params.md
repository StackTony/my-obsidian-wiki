---
title: Linux meminfo参数详解
category: summaries
tags: [linux, 内核, memory, meminfo, page-cache]
source_dir: Linux 操作系统/Linux 内存管理
source_files: [Linux meminfo参数详细解释.md]
summary: /proc/meminfo各字段含义与关系：MemTotal/MemFree/MemAvailable区分、Buffers/Cached/SReclaimable组成、Active/Inactive(anon/file)LRU分类、HugePages与THP区别、内存黑洞。
provenance:
  extracted: 0.85
  inferred: 0.10
  ambiguous: 0.05
base_confidence: 0.775
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: supporting
created: 2026-06-01
updated: 2026-06-01
---

# Linux meminfo参数详解

`/proc/meminfo`是Linux内存状态的主要接口，`free`/`vmstat`命令的数据均源于此。

## 核心观点

### 三种"可用内存"区分

| 字段 | 含义 | 注意 |
|------|------|------|
| MemTotal | BIOS/kernel预留后的总可用RAM | 不含预留部分 |
| MemFree | 完全未使用的内存 | 不含可回收的缓存 |
| MemAvailable | 估计的可用内存 | =MemFree + 可回收缓存/slab |

### Buffers vs Cached

- **Buffers**：块设备缓存页（元数据、直接块IO）
- **Cached**：Page Cache文件数据页；包含tmpfs和共享内存
- Page Cache = Buffers + Cached + SwapCached

### LRU分类：Active vs Inactive

- **Active(anon)** + **Inactive(anon)** ≈ AnonPages + Shmem
- **Active(file)** + **Inactive(file)** = Page Cache活跃/非活跃部分
- 页面回收优先从Inactive(file)开始^[inferred]

### HugePages vs THP(AnonHugePages)

- **HugePages_***：预分配大页，独立管理，不计入RSS/PSS
- **AnonHugePages**：THP透明大页，属于AnonPages的一部分，自动合并2MB连续页

### 内存黑洞

`alloc_pages`分配的内存可能不出现在meminfo中——除非驱动主动报告。这导致实际内存使用量可能比meminfo显示的更大^[ambiguous]。

### 关键公式

```
Page Cache = Active(file) + Inactive(file) + Shmem + SwapCached
MemTotal = MemFree + kernel内存 + (Active+Inactive+Unevictable+HugePages)
```

## 来源

- [[concepts/linux-memory-management]] — 内存管理整体框架
- [[summaries/linux-page-cache]] — Page Cache机制详解
- `raw/sources/Linux 操作系统/Linux 内存管理/Linux meminfo参数详细解释.md`