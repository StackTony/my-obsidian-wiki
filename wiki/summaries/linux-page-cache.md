---
title: Linux Page Cache机制
category: summaries
tags: [linux, 内核, page-cache, file-io, memory]
aliases: [页缓存, Page Cache, Linux页缓存]
source_dir: Linux 操作系统/Linux 内核 IO 栈/Linux IO技术
source_files: [3 Linux IO页缓存（Page Cache）技术.md, Linux 深入理解 Page Cache.md]
summary: Page Cache=Buffers+Cached+SwapCached，inode→address_space→xarray组织，预读算法，Write Through/Back一致性，dirty page回写。2.4后与buffer cache统一。mmap直接映射Page Cache，反向映射PST树支持回收。
provenance:
  extracted: 0.80
  inferred: 0.15
  ambiguous: 0.05
base_confidence: 0.61
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: supporting
created: 2026-06-01
updated: 2026-11-12
relationships:
  - target: "[[concepts/linux-memory-management]]"
    type: related_to
  - target: "[[concepts/linux-io-stack]]"
    type: related_to
  - target: "[[concepts/zero-copy-memory-mapping]]"
    type: related_to
  - target: "[[concepts/virtual-memory-and-paging]]"
    type: related_to
  - target: "[[concepts/page-cache-vs-buffer-cache]]"
    type: related_to
  - target: "[[concepts/copy-on-write]]"
    type: related_to
---

# Linux Page Cache机制

Page Cache是Linux文件IO加速的核心机制——将文件内容缓存到内存，后续访问直接从缓存读取，避免重复磁盘IO。磁盘读取1MB数据的耗时是内存的80倍（SSD也4倍于内存延迟），Page Cache弥合这一鸿沟。

## 核心观点

### Page Cache的本质与位置

Page Cache由内核管理，位于VFS层与具体文件系统层（如ext4）之间。应用程序通过`read`/`write`等系统调用进入VFS层，根据`O_DIRECT`标志决定是否使用Page Cache。`mmap`可将文件内容映射到进程虚拟地址空间，直接与Page Cache映射，省去一次内核缓冲区→用户缓冲区的拷贝。^[inferred]

### 地址空间与组织结构

Page Cache的宿主是inode。每个inode通过`address_space`结构管理该文件的缓存页：

- `address_space->i_pages` 指向一棵 **xarray**（早期称radix tree / 基数树），所有Page Cache页挂在树上
- 根据文件偏移量（按页对齐）快速查找页是否已在缓存中
- 文件和inode一一对应，`inode->i_mapping->i_pages`是Page Cache管理的核心路径

基数树本质是多叉搜索树，每个节点是一个页。根据文件内偏移量可O(log N)定位所在页。

### Page Cache的组成公式

```
Page Cache = Buffers + Cached + SwapCached
           = Active(file) + Inactive(file) + Shmem + SwapCached
```

内核算法：`Cached = Active(file) + Inactive(file) + Shmem - Buffers`

**Cached 不等于 Active(file) + Inactive(file)**，它还包含含目录的页、直接从块设备读出的数据页、特殊文件系统（如shm）的页等。

### SwapCached为何属于Page Cache

匿名页（Active(anon)/Inactive(anon)）被swap out到磁盘后再swap in回内存时，原Swap File还在，该页变为File-backed，即SwapCached也算Page Cache。

### File-backed页 vs Anonymous页

| 类型 | 对应磁盘 | 回收方式 | 回收代价 |
|------|----------|----------|----------|
| **File-backed页** | 磁盘文件数据块 | 无脏页直接丢弃；有脏页先回写再丢弃 | 低——顺序IO落盘或直接丢弃 |
| **Anonymous页** | 无（进程私有） | 必须swap out到磁盘 | 高——随机写、必须持久化 |

### 预读机制（Readahead）

基于局部性原理，用户请求读4KB时，内核实际加载16KB（额外读3个page）：

- 用户请求offset 0-3KB → 磁盘基本单位block(4KB) → 至少读0-4KB（1个page）
- 内核预读[4KB,8KB)、[8KB,12KB)、[12KB,16KB) → 额外3个page

预读窗口动态调整，可通过`/sys/block/sdX/queue/read_ahead_kb`调优（默认128KB）。

### Write Through vs Write Back

| 模式 | 行为 | 性能 | 安全性 |
|------|------|------|--------|
| **Write Through** | 应用主动调用同步接口，数据落盘后才返回 | 低（牺牲吞吐量） | 高——确保不丢失 |
| **Write Back** | 数据先写缓存，标记dirty，内核线程异步刷盘 | 高（默认模式） | 低——宕机可能丢数据；但进程被kill -9时内核仍确保落盘 |

Write Back是Linux默认一致性方案。脏页回写的四种触发时机：

1. **时间间隔**：内核线程定期（约5秒/30秒）扫描脏页回写
2. **内存压力**：内存不足需回收页面时，脏页先回写再释放
3. **脏页比例**：超过`vm.dirty_ratio`（默认20%）或`vm.dirty_background_ratio`（默认10%）阈值
4. **显式同步**：`fsync()`、`fdatasync()`、`sync()`系统调用

### 回写线程架构

Linux采用per存储设备的刷新线程模型（类似Lighttpd架构）：

- **管理线程**：监控各设备脏页情况，按需创建/销毁刷新线程
- **刷新线程**：每个持久存储设备一个，仅负责该设备脏页回写
- 每个设备维护**脏文件链表**（存脏文件inode节点），回写即遍历该链表

### mmap四种映射类型与Page Cache关系

| 映射类型 | 系统调用 | 内存分类 | 与Page Cache关系 |
|----------|----------|----------|------------------|
| 私有匿名 | `MAP_ANON\|MAP_PRIVATE` | AnonPages | 不产生Page Cache |
| 私有文件 | `MAP_FILE\|MAP_PRIVATE` | 只读页=Page Cache；写时复制副本=AnonPages | 只读页共享，写触发COW |
| 共享文件 | `MAP_FILE\|MAP_SHARED` | Page Cache | 读写在同一物理页 |
| 共享匿名 | `MAP_ANON\|MAP_SHARED` | Shmem（Page Cache） | 借助虚拟文件系统实现共享内存 |

其中"私有文件"这一行的写分支就是写时复制：只读访问时进程 PTE 指向 Page Cache 页，首次写触发保护性缺页，内核为该进程复制一个匿名页（计入 AnonPages）并改映射，此后该页与文件脱钩、也不再回写文件。机制细节见 [[concepts/copy-on-write]]。

### 反向映射（Reverse Mapping）

回收Page Cache时，内核需知道页映射到哪些进程以解除页表映射。同一文件可映射到多进程，`address_space`管理两棵树：

- **i_pages（xarray树）**：维护所有Page Cache页——正向查找
- **i_mmap（PST优先查找树）**：维护文件映射的vm_area_struct——反向查找进程

解除Page Cache页映射时，通过`i_mmap`树查找映射该文件的进程VMA，修改对应进程页表项。

### Page Cache的观测

**内存指标**（`/proc/meminfo`、`free`）：
- `Buffers + Cached + SwapCached` = Page Cache总量
- `fincore`命令查看单个文件的Page Cache占用（RES/PAGES/SIZE）
- `lsof`+`fincore`组合查看进程打开文件的Page Cache

**命中率工具**（bcc工具集）：
- `cachestat`：追踪整个系统Page Cache命中率（HITS/MISSES/DIRTIES/HITRATIO）
- `cachetop`：按进程追踪Page Cache命中率（READ_HIT%/WRITE_HIT%）

## 关键细节

### 进程虚拟地址空间与Page Cache的产生

Page Cache产生有两种方式：

1. **Buffered I/O**：数据先入Page Cache，再拷贝到用户缓冲区（多一次copy）
2. **Memory-Mapped file**：Page Cache页直接映射到进程虚拟地址空间（少一次copy）

mmap文件映射流程：`vm_area_struct.vm_file` → `file.f_mapping` → `address_space` → 查`i_pages` xarray树 → 未命中则分配物理页、从磁盘加载、挂入树 → 填写进程页表项完成映射。

### Page Cache的劣势

1. **占用物理内存**：内存紧张时导致频繁swap，反而升高IO负载
2. **应用层管理API缺失**：透明管理，应用难以优化策略——MySQL InnoDB选择用户态16KB页自管理
3. **Direct I/O场景多一次IO**：绕过Page Cache时反而比Direct I/O多一次读/写IO

### 清空Page Cache

```bash
sync && echo 3 > /proc/sys/vm/drop_caches
```

## 未解问题

- XArray与radix tree的具体演进历史和性能差异（来源2提到xarray，来源1称radix tree） ^[ambiguous]
- 不同内核版本中PST树是否已被替代为其他数据结构

## 来源

- [[concepts/linux-memory-management]] — 内存管理整体框架，Page Cache是其核心章节
- [[concepts/linux-io-stack]] — IO栈架构，Page Cache是VFS层核心组件
- [[concepts/zero-copy-memory-mapping]] — mmap与零拷贝机制，直接关联Page Cache映射
- [[concepts/virtual-memory-and-paging]] — 虚拟内存、页表、缺页中断基础
- [[concepts/page-cache-vs-buffer-cache]] — Page Cache与Buffer Cache的历史演进与区别
- [[concepts/linux-io-models]] — 缓存IO vs 直接IO的读取策略（预读）与写入策略（脏页回写三种触发）、stdio buffer与kernel buffer两层缓冲的层次关系
- [[summaries/linux-meminfo-params]] — meminfo中Page Cache相关字段详解
- [[concepts/linux-io-performance-analysis]] — cachestat/cachetop等IO性能分析工具
- `raw/sources/Linux 操作系统/Linux 内核 IO 栈/Linux IO技术/3 Linux IO页缓存（Page Cache）技术.md`（原文：zhuanlan.zhihu.com/p/436313908）
- `raw/sources/Linux 操作系统/Linux 内核 IO 栈/Linux IO技术/Linux 深入理解 Page Cache.md`（原文：cloud.tencent.com/developer/article/2363233）
