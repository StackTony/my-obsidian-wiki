---
title: Page Cache与Buffer Cache的区别与统一
category: concepts
tags: [linux, 内核, page-cache, buffer-cache, io]
aliases: [Page Cache vs Buffer Cache, 页缓存与块缓存, Buffer Cache, buffer_head]
source_dir: Linux 操作系统/Linux 内核 IO 栈/Linux IO技术
source_files: [Linux Page Cache与Buffer Cache的区别.md]
summary: Page Cache以页(4KB)缓存文件数据(逻辑层)，Buffer Cache以块缓存磁盘块数据(物理层)。2.4前完全分离致双重缓存，之后统一：buffer_head的b_page指向Page Cache页，Buffer Cache成为Page Cache子集。
provenance:
  extracted: 0.82
  inferred: 0.13
  ambiguous: 0.05
base_confidence: 0.44
lifecycle: draft
lifecycle_changed: 2026-11-10
tier: supporting
created: 2026-11-10
updated: 2026-11-10
relationships:
  - target: "[[summaries/linux-page-cache]]"
    type: extends
  - target: "[[concepts/linux-io-stack]]"
    type: related_to
  - target: "[[concepts/linux-memory-management]]"
    type: related_to
---

# Page Cache与Buffer Cache的区别与统一

Page Cache与Buffer Cache是Linux内核两大缓存机制。它们在历史演进中从完全分离走向统一，但概念边界和应用场景仍各有侧重。理解二者的关系是排查IO瓶颈和性能调优的基础。

## 核心观点

### 历史演进：从分离到统一

| 时期 | 状态 | 问题 |
|------|------|------|
| **2.4内核之前** | Page Cache与Buffer Cache完全分离 | 块设备数据大多通过文件系统组织，导致同一数据被缓存两次，浪费内存 |
| **2.4内核之后** | 两块缓存近似融合 | 文件页加载到Page Cache时，Buffer Cache只需维护块指向页的指针 |
| **现代内核（2.6+）** | Buffer Cache成为Page Cache的子集 | 统一管理，一块物理内存页同时服务文件和块IO缓存 |

统一后的规则：只有**没有文件表示的块**或**绕过文件系统直接操作**（如`dd if=/dev/sda`）的块，才会真正放入Buffer Cache。

### 本质区别：逻辑层 vs 物理层

| 维度 | Page Cache | Buffer Cache |
|------|------------|--------------|
| **缓存内容** | 文件数据，以页（4KB）为单位 | 磁盘块数据，缓存块级别元数据与原始数据 |
| **抽象层级** | 逻辑层——与文件系统同级 | 物理层——与块设备驱动同级 |
| **数据结构** | `struct page` + `address_space`，基数树/xarray索引 | `struct buffer_head`，内含`b_page`指向对应Page Cache页 |
| **更新策略** | 写入先标记脏页，内核异步回写 | 写入先存Buffer Cache，达磁盘块大小时写入磁盘 |
| **读取单位** | 以内存页(4KB)为单位 | 以磁盘块(通常512B或1KB)为单位 |
| **应用场景** | 文件读写（文件内容缓存） | 磁盘块操作、文件系统元数据(inode/dentry/超级块)、裸设备IO |

### 统一后的结构关系

在现代内核中，同一个物理页在两个层面同时存在：

- **文件系统层面**：该页作为某文件的Page Cache页
- **块设备驱动层面**：该页又表现为设备上一组缓冲区缓存（Buffer Cache）

若磁盘块大小为1KB，则每个4KB的Page Cache页对应4个磁盘块的Buffer Cache。每个Buffer Cache通过`buffer_head`描述符管理，记录对应缓冲区映射的磁盘块物理位置。`buffer_head->b_page`指向所属的Page Cache页。

数据写入流程：通过`inode->i_mapping`找到Page Cache页 → 写入数据并标记脏页 → 同步更新关联磁盘块的`buffer_head`脏标记。

### 二者协同工作

**读取流程**（接力模型）：
1. 磁盘将数据读取到Buffer Cache（按磁盘块组织）
2. Buffer Cache将数据传递给Page Cache（按页缓存并建立文件映射）
3. 后续访问直接从Page Cache命中

**写入流程**：
1. 数据写入Page Cache，标记为脏页
2. 脏页数据传递给Buffer Cache
3. Buffer Cache合并分散的小写入为大写入
4. Buffer Cache批量写入磁盘

### 各自覆盖的IO类型

| IO类型 | 主要缓存 | 说明 |
|--------|----------|------|
| 文件内容读写 | Page Cache | 通过read/write/mmap访问文件 |
| 文件系统元数据 | Buffer Cache | inode、dentry、超级块的读写 |
| 裸块设备IO | Buffer Cache | dd直接操作/dev/sda等块设备 |
| Direct I/O | 均不经过 | O_DIRECT标志绕过Page Cache |

### 调优参数对比

**Page Cache调优**：
- `vm.vfs_cache_pressure`（默认100）：控制dentry/inode缓存回收倾向，增大释放更多空间给Page Cache
- `vm.dirty_ratio`（默认20%）：脏页占总内存比例上限，超限触发同步阻塞回写
- `vm.dirty_background_ratio`（默认10%）：触发后台异步回写的脏页比例阈值
- `/sys/block/sdX/queue/read_ahead_kb`（默认128KB）：预读大小，顺序读大文件场景可增大

**Buffer Cache调优**：
- 数据库层（如Oracle `DB_CACHE_SIZE`、MySQL `innodb_buffer_pool_size`）：应用自管理缓冲区
- 写入策略选择：`data=writeback`（ext4挂载选项）启用写回模式
- 监控缓冲区命中率（Oracle `V$BUFFER_POOL_STATISTICS`，理想>95%）

## 关键细节

### 性能优化实践

- **写密集型**（数据库）：降低`vm.dirty_ratio`使回写更频繁，减少内存压力
- **读密集型**：适当提高`vm.dirty_ratio`，让更多数据留在Page Cache
- **顺序读大文件**（视频/大数据）：增大`read_ahead_kb`，如128KB→512KB
- **频繁小写入**：在应用层批量组装后一次写入，减少Buffer Cache操作次数

### 故障排查路径

1. `cachestat`查看缓存命中率——命中率低(<90%)说明大量请求直达磁盘
2. `free -h`检查内存——内存使用率接近100%且缓存小，需增加物理内存
3. `iostat`检查磁盘——使用率>80%且等待时间长，可能是IO瓶颈
4. `iotop`定位IO消耗最多的进程

### 双重缓存问题已解决

2.4前分离设计导致：磁盘数据大多通过文件系统组织 → 同一数据同时出现在Page Cache和Buffer Cache → 浪费内存。统一后Buffer Cache只需维护指向Page Cache页的指针（`buffer_head->b_page`），消除重复缓存。^[inferred]

## 未解问题

- 来源中提到"2.6.18源码实现"和"2.4后统一"，但未给出精确的commit或版本号对照 ^[ambiguous]
- Buffer Cache在现代内核中是否仍有完全独立的缓存场景（裸设备IO之外）

## 来源

- [[summaries/linux-page-cache]] — Page Cache机制详解，本文是其与Buffer Cache关系的延伸
- [[concepts/linux-io-stack]] — IO栈整体架构，Page Cache与Buffer Cache在栈中的位置
- [[concepts/linux-memory-management]] — 内存管理框架，缓存是内存分配的重要去向
- [[concepts/linux-io-performance-analysis]] — iostat/cachestat等分析工具
- `raw/sources/Linux 操作系统/Linux 内核 IO 栈/Linux IO技术/Linux Page Cache与Buffer Cache的区别.md`（原文：zhuanlan.zhihu.com/p/1985043608181678205）
