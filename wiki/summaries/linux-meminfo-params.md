---
title: Linux meminfo 参数详解
created: 2026-06-01
updated: 2026-06-01
tags: [linux, kernel, memory, meminfo, page-cache]
category: summaries
source_dir: Linux 操作系统/Linux 内存管理
source_files: [Linux meminfo参数详细解释.md]
summary: /proc/meminfo各字段含义与关系：内存黑洞、LRU分类、HugePages与THP区别、关键公式
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: "2026-06-01"
tier: supporting
---

# Linux meminfo 参数详解

`/proc/meminfo` 是 Linux 内存使用的主要接口，free、vmstat 等命令的数据来源。理解其字段含义与关系，是内存分析的基础。

## 内存黑洞

内核动态内存分配有四种接口：alloc_pages、vmalloc、slab、kmalloc。其中 slab 和 vmalloc 的使用被精确统计（Slab/SReclaimable/SUnreclaim、VmallocUsed），但 **alloc_pages 分配的内存不会自动统计** — 这就是内存黑洞。例如 VMware Balloon driver 通过 alloc_pages 占用内存，meminfo 中看不出去向，只能看到 MemFree 减少。

内核静态部分（代码、页描述符）在引导阶段分配，不计入 MemTotal，算作 Reserved。

## MemTotal / MemFree / MemAvailable

- **MemTotal**：系统引导后可供内核支配的内存，运行期间基本固定
- **MemFree**：尚未使用的内存
- **MemAvailable**：估算的可用内存 = MemFree + 可回收的 cache/buffer/slab。这是个估计值，用于应用自动调整内存申请

## 内核内存统计

| 字段 | 含义 |
|------|------|
| Slab | slab 分配器总内存 |
| SReclaimable | slab 中可回收部分 |
| SUnreclaim | slab 中不可回收部分 |
| VmallocUsed | vmalloc 分配的内存（含 VM_IOREMAP 等非物理内存映射，需过滤） |
| PageTables | 页表占用的内存 |
| KernelStack | 每线程 8K/16K 内核栈的总和 |
| HardwareCorrupted | 硬件故障删除的内存页 |

内核模块通过 vmalloc 分配，内存计入 VmallocUsed。lsmod 显示的大小是 init_size + core_size，但实际分配按页对齐外加 guard page，比 lsmod 显示的更大。

## 用户进程内存与 LRU

用户内存分两类：
- **File-backed pages**：对应磁盘文件，内存不足可直接 page-out
- **Anonymous pages**：不对应文件（堆、栈），必须 swap-out

LRU lists 管理页面回收：
- Active(anon)/Inactive(anon) — 匿名页，按访问时间分活跃/非活跃
- Active(file)/Inactive(file) — 文件页
- Unevictable — 不能 page-out/swapout 的页（mlock、ramfs）

关键关系：`Active(anon) + Inactive(anon) = AnonPages + Shmem`（因 Shmem 计入 LRU anon 但不计入 AnonPages）

## HugePages vs THP

| 特性 | HugePages | Transparent HugePages (THP) |
|------|-----------|----------------------------|
| 统计位置 | 独立统计，不与 RSS/PSS/Cache 重叠 | AnonHugePages，与 AnonPages 重叠 |
| 进程 RSS | 使用 HugePages 不增加 RSS | 使用 THP 增加 RSS |
| 管理方式 | 预分配，独立管理 | 动态透明，内核自动合并 |
| 配置 | vm.nr_hugepages | /sys/kernel/mm/transparent_hugepage |

HugePages_Total 设置后立即从 MemFree 划出，无论是否使用。

## Shmem / AnonPages / Cached / Mapped

- **Shmem**：共享内存 + tmpfs/devtmpfs。基于 tmpfs 实现，计入 Cached 和 LRU anon，但不计入 AnonPages
- **AnonPages**：匿名页总数，含 THP 的 AnonHugePages
- **Cached**：Page Cache = Buffers + Cached + SwapCached
- **Mapped**：Cached 中被进程映射的页面子集

公式：`Cached + AnonPages + Buffers ≈ 所有进程 PSS之和 + (Cached - Mapped) + Buffers`

## Dirty pages 计算

/proc/meminfo 的 Dirty 未包含全部脏页，完整计算：`Dirty + NFS_Unstable + Writeback`

NFS_Unstable 计入 Slab（nfs request 通过 slab 分配）。匿名页不属于 dirty pages。

## 来源

- `Linux 操作系统/Linux 内存管理/Linux meminfo参数详细解释.md` — meminfo 字段详解与公式推导

## 相关概念

- [[concepts/linux-memory-management]] — Linux 内存管理架构
- [[summaries/linux-page-cache]] — Page Cache 机制详解