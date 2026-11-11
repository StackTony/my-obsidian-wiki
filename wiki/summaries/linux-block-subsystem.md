---
title: Linux 块设备子系统
category: summaries
tags: [linux, block, 内核, blk-mq, 存储]
aliases: [块设备子系统, blk-mq, gendisk, bio]
relationships:
  - target: "[[concepts/linux-io-stack]]"
    type: implements
  - target: "[[summaries/linux-scsi-subsystem]]"
    type: related_to
  - target: "[[concepts/linux-driver-model]]"
    type: implements
  - target: "[[concepts/linux-io-performance-analysis]]"
    type: related_to
source_dir: Linux 操作系统/Linux 驱动管理/Linux Block块设备 系统
source_files: [Linux内核块设备.md]
summary: 块设备子系统：扇区/块/bio/request/调度器五概念、blk-mq 软队列(每CPU)+硬队列双层模型、gendisk/blk_mq_tag_set/blk_mq_ops.queue_rq/bio/bio_vec 结构体链与从 submit_bio 到 blk_mq_end_request 的驱动骨架。
provenance:
  extracted: 0.82
  inferred: 0.15
  ambiguous: 0.03
base_confidence: 0.59
lifecycle: draft
lifecycle_changed: 2026-11-11
tier: supporting
created: 2026-11-11
updated: 2026-11-11
---

# Linux 块设备子系统

野火 RK356x 驱动教程第 4 章的蒸馏。块设备是三大设备类型中与存储强绑定的一类：**以固定大小数据块为单位、支持随机寻址、有页缓存与 IO 调度**，这三条决定了它与字符设备的根本差异。

## 概述

块层的核心矛盾是"文件系统按页组织、硬件按扇区寻址"，中间靠三级抽象过渡：bio（一次 IO 的语义单位）→ request（调度后的硬件任务）→ 驱动的 `queue_rq`（下发）。blk-mq 则解决多核时代的锁竞争：每个 CPU 一个软件队列，硬件队列做汇总。^[inferred]

## 核心观点

- **五个名词构成一条链**：扇区（硬件寻址最小单位，512B/4K）→ 块（文件系统与内核交互单位，页的整数倍）→ bio（一次 IO，含一个或多个页 + 目标扇区 + 操作类型）→ request（相邻 bio 合并后交给驱动的任务）→ IO 调度器（排序与合并，优化寻道或并发）。
- **blk-mq 是双层队列**：软件队列 `mq_ctx` 每 CPU 私有，入队无跨核锁竞争；硬件队列 `hw_ctx` 数量通常等于 CPU 核数或硬件通道数，负责汇总下发给设备。
- **`queue_rq` 是驱动唯一必须实现的回调**——其余（`commit_rqs`、`timeout`、`init_hctx`、`init_request`）都是可选优化或资源管理。
- **完成通知走 `blk_mq_end_request`**：无论在中断还是轮询里，驱动调它把请求标记完成并唤醒等待进程；漏调就是 IO 挂死。
- **容量与块大小是两组独立参数**：`set_capacity`（扇区数）、逻辑块大小（文件系统可见）、物理块大小（介质真实）、单次最大扇区数（拆分依据）。

## 关键细节

### 数据流向（六步）

1. 用户态 `read/write`。
2. VFS/文件系统：文件偏移 → 逻辑块号，生成 bio。
3. 块层：bio 经调度器合并成 request，放入硬件队列。
4. 驱动：`blk_mq_ops.queue_rq` 取 request，操作硬件寄存器或内存缓冲。
5. 硬件：执行物理读写，完成后中断。
6. 驱动：中断/轮询中 `blk_mq_end_request`，唤醒等待进程。

### 核心结构体链

| 结构体 | 作用 | 关键字段 |
|---|---|---|
| `gendisk` | 一个完整磁盘设备 | `major/first_minor/minors`、`fops`、`queue`、`capacity`（扇区）、`state`（GD_ADDED/GD_DEAD…） |
| `block_device_operations` | 设备级回调 | `submit_bio`、`open/release`、`ioctl`、`check_events`、`getgeo` |
| `blk_mq_tag_set` | 队列资源总配置 | `nr_hw_queues`、`queue_depth`、`numa_node`、`timeout`、`ops` |
| `blk_mq_ops` | 请求处理回调集 | `queue_rq`（必需）、`commit_rqs`、`queue_rqs`、`timeout`、`init_hctx/exit_hctx` |
| `request` | 一次硬件任务 | `mq_ctx/mq_hctx`、`cmd_flags`、`tag`、`__sector`、`__data_len`、`bio/biotail`、`end_io` |
| `bio` | 一次 IO 语义单位 | `bi_bdev`、`bi_opf`、`bi_iter`、`bi_io_vec`、`bi_end_io`、内嵌 `bi_inline_vecs[]` |
| `bio_vec` | 一段页内缓冲 | `bv_page`、`bv_len`、`bv_offset` |
| `req_iterator` | 遍历 request 内所有 bio_vec | `iter` + `bio` |

### 驱动注册骨架

`register_blkdev`（设备号）→ `blk_mq_alloc_tag_set`（标签集）→ `blk_mq_alloc_disk`/`blk_mq_init_queue`（gendisk + 请求队列）→ 填 `fops` 与 `queue_rq` → `set_capacity` → `add_disk`；卸载逆序 `del_gendisk` / `blk_mq_free_tag_set` / `unregister_blkdev`。实验用 RAM 模拟盘验证了这条骨架。^[inferred]

### 与上层的关系

- 往上：VFS 的 `submit_bio` 进入块层；Page Cache 命中时不进块层（见 [[concepts/page-cache-vs-buffer-cache]]）。
- 往下：现代 SSD/NVMe 走自己的队列，SATA/SCSI 盘经 [[summaries/linux-scsi-subsystem]] 转成 SCSI 命令。
- 横向：调度器（Noop/Deadline/CFQ/BFQ）在 blk-mq 下变成 `mq-deadline`、`bfq`、`kyber`、`none` 的选择，见 [[concepts/linux-io-stack]]。

## 未解问题

- blk-mq 的 tag 分配与 `hctx tags busy` 阻塞机制只在他处有结论，本文未给源码路径。
- 分区扫描（`GD_NEED_PART_SCAN`）与 `check_events` 的触发时序未展开。
- zone 设备（ZNS）与 `null_blk` 这类多队列测试设备的差异未覆盖。

## 来源

- `raw/sources/Linux 操作系统/Linux 驱动管理/Linux Block块设备 系统/Linux内核块设备.md` — 野火 RK356x 驱动教程第 4 章：块设备概念、blk-mq 原理、核心结构体与函数、RAM 模拟块设备实验
- 交叉：[[summaries/linux-scsi-subsystem]]（SCSI 命令如何被块层调用）、[[concepts/linux-io-stack]]（IO 栈全局）
