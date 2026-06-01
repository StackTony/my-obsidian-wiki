---
title: Linux 页缓存（Page Cache）
created: 2026-06-01
updated: 2026-06-01
tags: [linux, kernel, page-cache, file-io, memory]
category: summaries
source_dir: Linux 操作系统/Linux 内存管理
source_files: [Linux 页缓存（Page Cache）.md]
summary: Page Cache机制：基数树结构、预读算法、Write Through与Write Back一致性、Dirty page回写
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: "2026-06-01"
tier: supporting
---

# Linux 页缓存（Page Cache）

Page Cache 是 Linux 内核管理的内存区域，用于缓存磁盘文件数据。通过 mmap 和 buffered I/O 读取文件实际上都读取到 Page Cache。

## Page Cache 定义与组成

```
Page Cache = Buffers + Cached + SwapCached
```

内核计算：Cached = file_pages - SwapCached - Buffers

Page Cache 包含：
- 普通文件数据页
- 目录页
- 块设备直接读取的数据页
- 用户态进程数据页（如 shm）
- 特殊文件系统页（tmpfs）

**Buffers vs Cached**：Buffers 缓存块设备的块数据（物理概念），Cached 缓存文件的页数据（逻辑概念）。Linux 2.4 后两者融合：文件页进入 Page Cache 时，buffer cache 只维护块指向页的指针。

## File-backed vs Anonymous pages

用户可访问内存分两类：
- **File-backed pages**：对应磁盘文件，内存不足可直接 page-out 回文件，无需 swap
- **Anonymous pages**：不对应磁盘文件（进程堆栈），必须 swap-out 到交换区

Anonymous pages 回收代价更高，需要随机写入交换设备。

## 基数树结构与预读

Page Cache 中每个文件是一棵基数树（radix tree），节点是页。根据文件偏移量可快速定位页。

预读机制：用户请求 4KB 数据时，内核利用局部性原理预读后续 12KB，一次性加载 16KB 到 Page Cache，减少后续 I/O。

## 数据一致性机制

文件 = 数据 + 元数据。写操作若数据在 Page Cache，会直接作用于缓存，此时内存数据领先磁盘，该页成为 Dirty page。

两种一致性方案：

| 方案 | 特点 | 适用场景 |
|------|------|----------|
| Write Through | 应用主动调用接口，确保落盘 | 数据不能丢失 |
| Write Back | 内核线程周期回写脏页 | 默认方案，高吞吐 |

三种系统调用：
- `sync()` — 回写所有文件系统和块设备的脏页
- `fsync(fd)` — 回写指定文件的脏数据和元数据
- `fdatasync(fd)` — 回写指定文件的脏数据（不含元数据）

Write Back 实现细节：
- 每存储设备一个刷新线程，管理线程监控脏页情况
- 脏文件按设备组织成 inode 链表
- 回写时机：应用主动调用、周期唤醒、内存不足回收

**可靠性差异**：Write Through 确保落盘不丢失；Write Back 在系统宕机时可能丢失数据（进程被 kill 时操作系统仍会确保落盘）。

## SwapCached

匿名页先被 swap-out 到磁盘，再 swap-in 回内存后，原 Swap File 还在，此时页计入 SwapCached，仍属于 File-backed page（Page Cache的一部分）。SwapCached 不与 Cached 重叠，同时计入 AnonPages 或 Shmem。

## Page Cache 优劣

**优势**：
- 加快数据访问 — 命中缓存无需磁盘 I/O
- 减少 I/O 次数 — 预读机制一次加载多页

**劣势**：
- 占用额外物理内存 — 内存紧张时触发频繁 swap
- 缺乏用户 API — 应用层难以优化管理策略
- 比 Direct I/O 多一次读写 — Direct I/O 绕过 Page Cache

## 来源

- `Linux 操作系统/Linux 内存管理/Linux 页缓存（Page Cache）.md` — Page Cache 原理与一致性机制

## 相关概念

- [[concepts/linux-memory-management]] — Linux 内存管理架构
- [[summaries/linux-meminfo-params]] — meminfo 中 Cached/Buffers 字段详解
- [[concepts/linux-file-io]] — 文件 I/O 与 Direct I/O