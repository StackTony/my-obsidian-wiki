---
title: Linux meminfo参数详解
category: summaries
tags: [linux, 内核, memory, meminfo, page-cache]
source_dir: Linux 操作系统/Linux 内存管理
source_files: [Linux meminfo参数详细解释.md]
summary: /proc/meminfo全字段详解：内核内存(Slab/VmallocUsed/PageTables/KernelStack/HardwareCorrupted/Bounce)、用户进程内存(HugePages/THP/LRU/Shmem/AnonPages/Mapped/Cached/SwapCached)、内存黑洞、三种统计口径公式、DirectMap与TLB效率。
provenance:
  extracted: 0.82
  inferred: 0.13
  ambiguous: 0.05
base_confidence: 0.775
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: supporting
created: 2026-06-01
updated: 2026-11-10
---

# Linux meminfo参数详解

`/proc/meminfo`是Linux内存状态的主要接口，`free`/`vmstat`命令的数据均源于此。负责输出的源代码是 `fs/proc/meminfo.c: meminfo_proc_show()`。本文按**内核内存**与**用户进程内存**两大分类系统梳理各字段含义、相互关系与常见误区。

## 核心观点

- **三种"可用内存"必须区分**：MemTotal（BIOS/kernel预留后的总RAM，运行期一般不变）、MemFree（完全未使用）、MemAvailable（估算值 = MemFree + 可回收的cache/buffer/slab，并非精确值）。
- **Buffers vs Cached 的本质区别**：Buffers是块设备缓存页（元数据、直接块IO），Cached是文件数据页（Page Cache，包含tmpfs和共享内存）。
- **内存黑洞**：通过 `alloc_pages()` 分配的内存不被任何meminfo字段追踪，导致 MemTotal − MemFree − 所有已用字段之间存在难以解释的差额。典型消费者包括VMware Balloon driver、内核栈、per-cpu数据。 ^[inferred]
- **Bounce字段与低端内存DMA跳转相关**：老设备只能访问低端内存（如16M以下），当DMA目标在高端内存时，内核在低端内存分配临时buffer做跳转拷贝（bounce buffering），降低IO性能并占用额外内存。这与 [[skills/swiotlb-troubleshooting]] 中的 swiotlb bounce 池机制相关。
- **DirectMap不是内存使用统计，而是TLB效率指标**：反映有多少内存被映射为大页（2M/4M/1G）以减少TLB条目数量。

## 关键细节

### 内核内存

内核动态分配内存有三种接口：`alloc_pages`（页级）、`vmalloc`（字节级虚拟连续）、`slab allocator`（`kmalloc`，字节级物理连续）。其中 slab 和 vmalloc 的分配被统计在meminfo中，而 alloc_pages 分配的内存除非驱动主动报告否则不可见（内存黑洞）。

| 字段 | 含义 | 内核对应 |
|------|------|----------|
| Slab | Slab分配器总量 = SReclaimable + SUnreclaim | slab统计 |
| SReclaimable | 可回收Slab（dentry/inode cache等，加SLAB_RECLAIM_ACCOUNT标记） | kmem_getpages() |
| SUnreclaim | 不可回收Slab | — |
| VmallocUsed | vmalloc分配总量（含VM_IOREMAP等非物理消耗） | 只关心VM_ALLOC，查/proc/vmallocinfo |
| PageTables | 页表占用的内存（翻译VA→PA，动态变化，消耗MemTotal） | 区别于Page Frame描述符(mem_map[]，计入Reserved) |
| KernelStack | 每个用户线程的内核栈（x86固定8K或16K），常驻内存不计入LRU/RSS | — |
| HardwareCorrupted | 硬件故障被删除的内存页总量 | mm/memory-failure.c: memory_failure() |
| Bounce | bounce buffer占用的内存（低端内存DMA跳转） | 与swiotlb相关，见 [[skills/swiotlb-troubleshooting]] |

**VmallocUsed的陷阱**：该值不只包括分配的物理内存，还统计了VM_IOREMAP（IO地址映射，不消耗物理内存）、VM_MAP等操作。从物理内存角度只关心VM_ALLOC操作，应查 `/proc/vmallocinfo` 中的vmalloc记录。

**内核模块内存**：`lsmod` 列出的是 `init_size + core_size`，但实际分配以page为单位（不足1page也分配整page），外加每个module一页guard page。因此 lsmod 不准确，应统计 `/proc/vmallocinfo` 中的 vmalloc 记录——kernel module的内存通过vmalloc()分配，包含在VmallocUsed中。 ^[inferred]

**PageTables vs Page Frame**：物理内存最小单位是page frame，每个物理页对应一个 `struct page` 描述符，保存在 `mem_map[]` 数组中（引导阶段分配，计入Reserved，不含在MemTotal中）。而Page Table用于翻译虚拟地址和物理地址，动态变化，从MemTotal中消耗内存。

### 用户进程内存

| 字段 | 含义 | 注意 |
|------|------|------|
| HugePages_* | 预分配大页，独立管理 | 不计入RSS/PSS、LRU、cache/buffer |
| AnonHugePages | THP透明大页 | 包含在AnonPages中，与RSS/PSS有重叠 |
| Active(anon)/Inactive(anon) | 匿名页LRU | 进程堆栈等无文件对应的页 |
| Active(file)/Inactive(file) | 文件页LRU | Page Cache的活跃/非活跃部分 |
| Unevictable | 不能pageout/swapout的页 | mlock页、SHM_LOCK共享内存、ramfs |
| AnonPages | 匿名页总量 | 不含shared memory（基于tmpfs算file-backed） |
| Shmem | 共享内存 + tmpfs + devtmpfs | 计入Cached和Mapped，LRU中放anon但不算AnonPages |
| Mapped | Page Cache中被进程关联的页 | 是Cached的子集 |
| Cached | Page Cache（所有file-backed pages） | 是Mapped的超集；包含tmpfs/shmem |
| SwapCached | 同时在swap和swap cache中的匿名页 | 不属于Cached；避免swap-in后重复读磁盘 |
| Mlocked | mlock()锁定的内存 | 与Unevictable同步增减 |
| Buffers | 块设备缓存页（元数据、直接块IO） | 也在LRU Active(file)/Inactive(file)中 |

**HugePages vs THP 关键区别**：
- HugePages 独立统计，不与其他字段重叠，不计入RSS/PSS/LRU/cache
- THP（AnonHugePages）包含在AnonPages中，与RSS/PSS有重叠
- 使用HugePages的三种方式：mount hugetlbfs + mmap、shmget/shmat（加SHM_HUGETLB标志）、mmap（加MAP_HUGETLB标志）
- HugePages_Rsvd 表示已reserve但未真正使用的页（申请时增加Rsvd，真正读写时Rsvd减少、Free减少）
- AnonHugePages 也可用于shared memory和tmpfs，缺省禁止，通过 `/sys/kernel/mm/transparent_hugepage/shmem_enabled` 控制

**Shmem的"拧巴"之处**：shared memory（SysV/POSIX/shared anonymous mmap）在内核中基于tmpfs实现，被视为file-backed，计入Cached和Mapped；但背后没有真正硬盘文件，内存不足时需要swap-out，所以在LRU中被放在anon list，但不计入AnonPages。 ^[inferred]

**SwapCache机制**：swap cache是交换区设备的"page cache"，用radix-tree管理，与page cache的唯一区别是——匿名页与swap cache的对应关系在即将被swap-out时才确立。SwapCached表示曾被swap-out又swap-in且内容未变化的匿名页——再次swap-out时无需I/O write。SwapCached不属于Cached，两者无交叉；SwapCached同时在LRU中，还在AnonPages或Shmem中，本身不占用额外内存。

### 关键公式与等式

**Page Cache**：
```
Page Cache = Buffers + Cached + SwapCached
```

**LRU等式**（不考虑mlock和swap过渡态）：
```
Active(anon) + Inactive(anon) = AnonPages + Shmem
Active(file) + Inactive(file) + Shmem = Cached + Buffers
```
注：swap-out过程中，shmem可能从Cached转入SwapCached但未立即从swap cache删除，导致等式不平衡。 ^[ambiguous]

**Dirty pages总量**：
```
全部dirty pages = Dirty + NFS_Unstable + Writeback
```
注：anonymous pages不属于dirty pages（由reclaim context写入，不经flusher线程）。

**系统内存总量公式**：
```
MemTotal = MemFree + 内核内存 + 用户进程内存

内核内存 = Slab + VmallocUsed(实际VM_ALLOC) + PageTables + KernelStack + HardwareCorrupted + Bounce + X(黑洞)
```

用户进程内存的三种统计口径：
1. **LRU口径**：`Active + Inactive + Unevictable + (HugePages_Total × Hugepagesize)`
2. **Page Cache口径**（SwapCached=0时）：`Cached + AnonPages + Buffers + (HugePages_Total × Hugepagesize)`
3. **RSS/PSS口径**：`ΣPss + (Cached − Mapped) + Buffers + (HugePages_Total × Hugepagesize)`

### DirectMap 与 TLB 效率

DirectMap4k/DirectMap2M 等字段不统计内存使用，而是反映TLB效率：大页映射（2M/4M/1G）减少地址翻译条目数量，提高TLB命中率。详见 [[summaries/linux-tlb-management]] 和 [[concepts/virtual-memory-and-paging]]。

## 未解问题

- 内存黑洞（alloc_pages分配的内存）的精确量化仍然困难，不同内核版本和配置下差异显著。 ^[ambiguous]
- SwapCached ≠ 0 时Page Cache口径公式不成立——SwapCached可能含Shmem（从Cached转入但未立即删除）又与AnonPages有重叠，原文承认此处等式在内存交换时可能不平衡。 ^[ambiguous]
- THP在数据库等场景的性能争议——有的显著提升，有的因内存碎片反而下降。 ^[ambiguous]
- 理论上 `ΣPss == Mapped + AnonPages`，但实测总有微小偏差——可能是smaps和meminfo采集时间点不同步所致。 ^[ambiguous]

## 来源

- [[concepts/linux-memory-management]] — 内存管理整体框架
- [[summaries/linux-page-cache]] — Page Cache机制详解
- [[summaries/linux-tlb-management]] — TLB与DirectMap
- [[skills/swiotlb-troubleshooting]] — swiotlb bounce 池（Bounce字段相关）
- `raw/sources/Linux 操作系统/Linux 内存管理/Linux meminfo参数详细解释.md`（原文：blog.csdn.net/whbing1471/article/details/105468139）
