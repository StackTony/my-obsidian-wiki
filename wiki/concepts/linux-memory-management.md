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
  - target: "[[concepts/copy-on-write]]"
    type: related_to
  - target: "[[concepts/zone-watermark]]"
    type: related_to
  - target: "[[concepts/lru-page-reclaim]]"
    type: related_to
  - target: "[[concepts/swap-cache-mechanism]]"
    type: related_to
source_dir: Linux 操作系统/Linux 内存管理
source_files: [Linux meminfo参数详细解释.md, Linux 页缓存 Page Cache.md, Linux 内存与CPU之间的关系.md, Linux TLB（页表项Cahce）.md, Linux Coye On Write（写时复制）.md, Linux 伙伴分配器与 SLAB 分配器.md, Linux 内存回收机制.md]
summary: Linux内存管理：meminfo参数体系(含Bounce/DirectMap)、Page Cache架构(基数树+预读)、内存黑洞、伙伴系统/SLAB两级分配、zone三水位与三条回收路径(快速/直接/kswapd)、LRU双链表与swap cache、写时复制(COW)，向下承接虚拟内存/分页与TLB原理。
provenance:
  extracted: 0.82
  inferred: 0.14
  ambiguous: 0.04
base_confidence: 0.80
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: core
created: 2026-06-01
updated: 2026-11-13
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
- **写时复制（COW）**：fork 不复制物理页，只复制页表并把私有可写 PTE 在父子两侧置只读；任一方写触发保护性缺页，由 `do_wp_page` 决定复用独占页（`wp_page_reuse`）还是复制新页（`wp_page_copy`）。详见 [[concepts/copy-on-write]]。
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
| Bounce | bounce buffer占用的内存（低端内存DMA跳转） | 与swiotlb相关，见 [[skills/swiotlb-troubleshooting]] |
| DirectMap4k/2M | 反映TLB效率的指标（大页映射减少TLB条目） | 不是内存使用统计 |

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

### 页框分配：伙伴系统与 SLAB 两级分工

物理内存分配分两层，理解它才能读懂 `MemFree` 与 `Slab` 字段：

- **伙伴系统（Buddy Allocator）**：以 `2^n` 页的"阶"管理页框。分配时向上取整到阶、目标阶空则从更高阶逐级分裂；释放时用 `伙伴地址 = 块地址 ^ (1 << (order + PAGE_SHIFT))` 找伙伴，空闲则递归合并。它擅长对抗**外部碎片**，代价是内部碎片（3 页请求分 4 页，浪费 25%）。
- **SLAB/SLUB**：从伙伴系统取整页，切成固定大小的对象缓存（`kmem_cache`），服务 `task_struct`、`inode`、`dentry` 这类小对象。它擅长对抗**内部碎片**，分配释放 O(1)。
- **观测**：`/proc/buddyinfo` 看各阶空闲块（高阶长期为 0 = 外部碎片严重）；`/proc/pagetypeinfo` 按迁移类型看碎片结构；`/proc/slabinfo` 看对象利用率。

完整流程、手算示例与三张观测表见 [[summaries/linux-buddy-slab-allocator]]。

### 回收的触发：水位线与三种回收

回收不是单一入口。每个 zone 先划定 min/low/high 三条水位线（`watermark[NR_WMARK]`），按空闲页框落在哪一段决定动作；详见 [[concepts/zone-watermark]]。

| 路径 | 入口 | 主链路 | 特点 |
|---|---|---|---|
| 快速回收 | `get_page_from_freelist()` 判定"分配后剩余 < 水位 + 保留页框" | `zone_reclaim → __zone_reclaim → shrink_zone/shrink_slab` | 优先级 4、最多 4 轮；脏文件页不回写，是否回写匿名页/解映射由 `zone_reclaim_mode` 决定 |
| 直接回收 | 慢路径所有 zone 连 min 水位都拿不到页框 | `__alloc_pages_slowpath → __alloc_pages_direct_reclaim → try_to_free_pages → shrink_zones → shrink_zone` | 分配者上下文同步执行，默认优先级 12、目标约 32 页；失败进 OOM |
| kswapd 回收 | 分配拿不到 low 水位页框时唤醒 | `kswapd → balance_pgdat → kswapd_shrink_zone → shrink_zone/shrink_slab` | 每 NUMA node 一线程；逐 zone 拉回 high 水位；可回写脏文件页与匿名页 |
| 用户触发 | `drop_caches` | `drop_slab → shrink_slab`、`drop_pagecache_sb` | 手动清干净页，生产慎用 ^[inferred] |

三种回收的执行代码相同，区别只在进入条件与 `struct scan_control` 的初始化（`priority`、`may_writepage`、`may_unmap`、`may_swap`）。所有路径最终落到两个执行器：**`shrink_zone` 回收页框**（消费 LRU 与 PTE 访问位），**`shrink_slab` 回收可回收 slab 对象**。

执行链为 `shrink_zone → 遍历 memcg → shrink_lruvec → shrink_list → shrink_active_list / shrink_inactive_list → shrink_page_list`。回收的本质是把页的 `page->_count` 降到 0：隔离、解映射、回写、从 `address_space` 摘除，最后把页框交还伙伴系统。完整流程与 `_count == 2` 判定见 [[summaries/linux-memory-reclaim-triggers]]。

### LRU 回收算法

Linux 用 **Active / Inactive 双链表 + 访问位** 近似 LRU，匿名页与文件页各一套：

- **Active LRU**：最近被访问过的页，暂不回收；**Inactive LRU**：回收候选，扫描从尾部开始。
- 新页通常进入 Inactive 链表头；被再次访问后升级到 Active；Active 链表尾部长期未访问的页被 `shrink_active_list()` 降级回 Inactive 链表头。
- 匿名页只要任一映射 PTE 的 Accessed 置位就升级；文件页还要看 `PG_referenced` 与访问进程数，最近访问过的可执行文件页会留在 Active。
- 共 5 个链表：Active/Inactive 匿名页、Active/Inactive 文件页、`LRU_UNEVICTABLE`；回收只处理前四个，且只有非活动链表上的页会被真正回收。
- 扫描预算由 `sc->priority`（默认 12，越小扫越多）与 `swappiness`（匿名页/文件页比例）共同决定，每轮每链表最多扫描 32 个页框。

机制细节（页标志、`page->_count` 记账、升降级规则）见 [[concepts/lru-page-reclaim]]。这套双链表近似的是**工作集/老化类置换算法**——见 [[concepts/virtual-memory-and-paging]] 中九种算法的对比。 ^[inferred]

### 匿名页的后备存储：swap 与 swap cache

匿名页没有磁盘文件作载体，回收时先加入 **swap cache**（swap 分区的 `address_space`），再按页槽编号回写到 swap 分区，并把进程页表项改写成 swap 类型页表项。换入时按页槽查 swap cache：命中说明页仍在内存，直接映射；未命中才读盘。文件页则是同构的另一半——回写到文件的 page cache，页表项直接清空。两套 `address_space` 的对偶关系、换出/换入步骤与差异表见 [[concepts/swap-cache-mechanism]]。

### Write Through vs Write Back

| 策略 | 行为 | 性能 | 安全性 |
|------|------|------|--------|
| Write Through | 写操作同时写Page Cache和磁盘 | 低（每次写都等磁盘） | 高（断电不丢数据） |
| Write Back | 写操作只写Page Cache，后台pdflush刷盘 | 高（写操作立即返回） | 低（断电可能丢数据） |

Linux默认使用 Write Back 策略，通过 pdflush/kworker 线程定期将脏页刷回磁盘。

## 未解问题

- 内存黑洞的精确量化仍然困难，不同内核版本和配置下黑洞大小差异显著。 ^[ambiguous]
- THP（透明大页）在数据库等应用场景中的性能争议——有的场景显著提升，有的场景因内存碎片反而下降。 ^[ambiguous]
- 教材视角的页面置换算法（OPT/NRU/老化/WSClock）与 Linux 实际的 Active/Inactive 双链表 + kswapd 之间，已由 [[concepts/lru-page-reclaim]] 补齐"访问位/升降级"层面的对应，但 OPT/WSClock 与 MGLRU 的定量对照仍缺。 ^[inferred]
- 水位公式与 `swappiness` 的取值范围在不同内核版本间有差异（原文的水位与 0–200 口径偏旧），现代语义需要新来源校准。 ^[ambiguous]
- TLB shootdown 在高核数场景下的实际开销没有量化数据。 ^[ambiguous]


## 延伸阅读

综合分析：[[synthesis/linux-kernel-subsystem-interactions]]

内存与CPU的硬件交互：[[concepts/cpu-cache-coherence]]（CPU缓存一致性）、[[concepts/memory-barriers]]（内存屏障）——理解内存可见性与有序性的硬件基础。IO内存管理见 [[concepts/linux-io-models]]。

缓存体系：[[concepts/page-cache-vs-buffer-cache]] — Page Cache与Buffer Cache在2.4后统一的历史演进与区别本质。

设备DMA与IOMMU：[[summaries/linux-iommu-deep-dive]]（swiotlb 用 `memblock_alloc_low` 从低地址预留 bounce 池，是内核早期内存分配的实例）、[[concepts/linux-dma-mapping]]（IOVA/IOMMU页表翻译——IOMMU页表与MMU页表相互独立但原理相同）。

## 来源

- [[summaries/linux-meminfo-params]] — meminfo参数详解
- [[summaries/linux-page-cache]] — Page Cache架构与预读机制
- [[summaries/linux-memory-cpu-relationship]] — 虚拟内存与页面置换算法原理
- [[summaries/linux-tlb-management]] — TLB 硬件细节与 PCID
- [[summaries/linux-buddy-slab-allocator]] — 伙伴系统与 SLAB 的分配/释放流程、观测接口
- [[summaries/linux-memory-reclaim-triggers]] — 紧缺/周期性/用户触发三条回收路径与两个执行器
- `raw/sources/Linux 操作系统/Linux 内存管理/Linux 内存与CPU之间的关系.md`（原文：zhuanlan.zhihu.com/p/450505454）
- `raw/sources/Linux 操作系统/Linux 内存管理/Linux TLB（页表项Cahce）.md`（原文：developer.aliyun.com/article/1479067）