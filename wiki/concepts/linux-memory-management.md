---
title: Linux内存管理
category: concepts
tags: [linux, 内核, 内存, meminfo, page-cache, LRU]
aliases: [Linux内存, meminfo参数, Page Cache, 内存管理]
relationships:
  - target: "[[concepts/linux-io-stack]]"
    type: uses
  - target: "[[concepts/linux-lock-mechanisms]]"
    type: uses
  - target: "[[concepts/linux-interrupt-system]]"
    type: related_to
source_dir: Linux 操作系统/Linux 内存管理
source_files: [Linux meminfo参数详细解释.md, Linux 页缓存 Page Cache.md, Linux 内存与CPU之间的关系.md, Linux 内存管理 TLB.md]
summary: Linux内存管理：meminfo参数体系、Page Cache架构(基数树+预读)、内存黑洞(alloc_pages不可追踪)、LRU分类与Write策略，向下承接虚拟内存/分页与TLB的原理基础。
provenance:
  extracted: 0.82
  inferred: 0.13
  ambiguous: 0.05
base_confidence: 0.78
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: core
created: 2026-06-01
updated: 2026-10-21
---

# Linux内存管理

Linux内存管理是内核最复杂的子系统之一，涵盖物理内存分配、Page Cache缓存、LRU回收以及 /proc/meminfo 参数体系。理解这些参数和机制是排查内存问题的基础。**上层的 meminfo/Page Cache 统计，都建立在下层的分页、页表与 TLB 机制之上**——原理链路见 [[concepts/virtual-memory-and-paging]]。详见 [[concepts/linux-os-virtualization-landscape|Linux全景]]。

## 核心观点

- /proc/meminfo 是观察内核内存状态的核心接口，每个字段对应内核中特定的计数器或统计值。
- Page Cache 是文件IO的性能加速器，采用基数树(Radix Tree)索引 + 预读(Readahead)机制，将磁盘数据缓存到内存中避免重复IO。
- 内存黑洞指通过 `alloc_pages()` 等底层分配器直接分配的内存不被任何meminfo字段追踪，导致 MemFree 与实际可用内存之间有难以解释的差额。 ^[inferred]
- LRU（Least Recently Used）回收算法将页面分为 Active 和 Inactive 两个链表，Inactive 链表尾端是回收候选。
- 本页描述的是**上层机制**（统计口径、缓存组织、回收策略）；**下层机制**（地址空间抽象、分页与页表项、TLB 加速与刷新、页面置换算法的理论对比）由 [[concepts/virtual-memory-and-paging]] 承载。 ^[inferred]

## 关键细节

### 分页、页表与 TLB（下层基础）

理解内存回收与缓存之前，需要先明确地址是怎么被翻译的：

- **分页**：虚拟地址空间切为固定大小的**页**，物理内存切为同样大小的**页框**，由 MMU 通过页表映射。
- **页表项**：包含页框号、在/不在位、保护位、修改位（脏页需写回）、访问位（LRU/置换算法的输入信号）。**Linux 的 Active/Inactive 移动与页面回收，正是在消费硬件的访问位。**
- **缺页中断**：MMU 发现页不在内存 → 陷入内核 → 换出牺牲页（脏页先写回）→ 调入缺失页 → 重新执行原指令。
- **TLB**：MMU 内缓存页表项的硬件，每核私有。进程切换时若不刷新会读到错误映射，全量刷新又导致 cold TLB；**PCID/ASID** 通过给地址翻译加上进程上下文 ID 来消除这一成本（Linux 4.15 全面启用 PCID）。
- **页面置换算法的工程结论**：LRU 效果好但难以低成本实现，**老化算法（aging）与 WSClock 是最优近似**——Linux 用 Active/Inactive 双链表 + kswapd 实现同类的近似。

完整原理与九种置换算法对比见 [[concepts/virtual-memory-and-paging]]，TLB 硬件细节见 [[summaries/linux-tlb-management]]。

### /proc/meminfo 关键字段

| 字段 | 含义 | 内核对应 |
|------|------|----------|
| MemTotal | 物理内存总量 | totalram_pages × PAGE_SIZE |
| MemFree | 完全未使用的内存 | free_pages（buddy system中的空闲页） |
| MemAvailable | 真正可用的内存（含可回收部分） | 估算值 = MemFree + Active(file) + Inactive(file) + SReclaimable - 内核保留 |
| Buffers | 块设备缓冲区 | buffer_heads 统计 |
| Cached | Page Cache大小 | page cache 统计（不含 SwapCached） |
| SwapCached | 同时在swap和page cache中的页 | 避免重复IO的优化 |
| Active(anon) | 活跃匿名页（进程堆栈） | ACTIVE_ANON LRU |
| Active(file) | 活跃文件页（Page Cache） | ACTIVE_FILE LRU |
| Inactive(anon) | 非活跃匿名页 | INACTIVE_ANON LRU |
| Inactive(file) | 非活跃文件页 | INACTIVE_FILE LRU |
| Slab | Slab分配器总量 | slab统计 |
| SReclaimable | 可回收的Slab | dentry和inode cache等 |
| SUnreclaim | 不可回收的Slab | 内核不可释放的slab对象 |
| HugePages | 预分配的大页数量 | hugetlb相关 |
| AnonHugePages | THP(透明大页)数量 | mm/huge_memory |

### Page Cache 计算公式

Page Cache 的实际大小为：
```
Page Cache = Buffers + Cached + SwapCached
```

其中 Buffers 主要用于块设备元数据缓存，Cached 用于文件内容缓存，SwapCached 是同时在swap和内存中的页面（避免swap-in后重复读磁盘）。

### Page Cache 架构

Page Cache 的核心数据结构：
- **基数树（Radix Tree）**：以 (mapping, index) 为键快速定位缓存页，避免遍历链表
- **address_space**：每个文件对应一个 address_space，包含基数树根、host inode、a_ops（操作函数表）
- **预读（Readahead）**：当首次读取文件某区域时，内核根据预读窗口（initial_size/readahead_size）提前读入相邻页面，减少后续IO次数

预读机制的关键参数：
- `initial_window` = min(4 × PAGE_SIZE, readahead_size) — 首次预读窗口
- `readahead_window` — 后续预读大小，动态调整
- 预读仅对顺序读有效，随机读会关闭预读 ^[inferred]

### 内存黑洞

`alloc_pages()` 是内核最底层的物理页分配器，通过 buddy system 管理。但通过 alloc_pages 直接分配的页面：
- 不计入 Cached/Buffers/Slab
- 不计入 MemAvailable 的可回收部分
- 只有当页面被释放回到 buddy system 后才回归 MemFree

这导致 MemTotal - (MemFree + 所有已用字段) 之间存在难以解释的差额，这就是"内存黑洞"。 ^[inferred] 典型的黑洞消费者包括：内核栈、per-cpu数据、某些直接分配的内核结构。

### LRU 回收算法

Linux 使用双链表 LRU 实现：
- **Active LRU**：最近被访问过的页面，不易被回收
- **Inactive LRU**：较长时间未访问的页面，回收候选

页面在两个链表之间移动：
- 新页面进入 Inactive 链表头
- Inactive 链表中的页面被再次访问 → 提升到 Active 链表
- Active 链表中的页面逐渐老化 → 降级到 Inactive 链表尾

匿名页（anon）和文件页（file）分别有独立的 Active/Inactive 链表，共4个LRU链表。这套双链表近似的是**工作集/老化类置换算法**——见 [[concepts/virtual-memory-and-paging]] 中九种算法的对比。 ^[inferred]

### Write Through vs Write Back

| 策略 | 行为 | 性能 | 安全性 |
|------|------|------|--------|
| Write Through | 写操作同时写Page Cache和磁盘 | 低（每次写都等磁盘） | 高（断电不丢数据） |
| Write Back | 写操作只写Page Cache，后台pdflush刷盘 | 高（写操作立即返回） | 低（断电可能丢数据） |

Linux默认使用 Write Back 策略，通过 pdflush/kworker 线程定期将脏页刷回磁盘。

## 未解问题

- 内存黑洞的精确量化仍然困难，不同内核版本和配置下黑洞大小差异显著。 ^[ambiguous]
- THP（透明大页）在数据库等应用场景中的性能争议——有的场景显著提升，有的场景因内存碎片反而下降。 ^[ambiguous]
- 教材视角的页面置换算法（OPT/NRU/老化/WSClock）与 Linux 实际的 Active/Inactive 双链表 + kswapd 之间，还缺少一份"从算法到实现"的对应推导。 ^[inferred]
- TLB shootdown 在高核数场景下的实际开销没有量化数据。 ^[ambiguous]


## 延伸阅读

综合分析：[[synthesis/linux-kernel-subsystem-interactions]]

## 来源

- [[summaries/linux-meminfo-params]] — meminfo参数详解
- [[summaries/linux-page-cache]] — Page Cache架构与预读机制
- [[summaries/linux-memory-cpu-relationship]] — 虚拟内存与页面置换算法原理
- [[summaries/linux-tlb-management]] — TLB 硬件细节与 PCID
- `raw/sources/Linux 操作系统/Linux 内存管理/Linux 内存与CPU之间的关系.md`（原文：zhuanlan.zhihu.com/p/450505454）
- `raw/sources/Linux 操作系统/Linux 内存管理/Linux 内存管理 TLB.md`（原文：developer.aliyun.com/article/1479067）