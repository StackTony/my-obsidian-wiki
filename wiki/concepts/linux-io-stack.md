---
title: Linux IO栈
category: concepts
tags: [linux, IO, 内核, 存储]
aliases: [Linux Block层, Linux IO调度]
relationships:
  - target: "[[concepts/linux-memory-management]]"
    type: uses
  - target: "[[concepts/linux-lock-mechanisms]]"
    type: related_to
  - target: "[[concepts/linux-virtio-architecture]]"
    type: related_to
source_dir: Linux 操作系统/Linux 内核 IO 栈
source_files: [Linux IO全景介绍.md, Linux IO调度算法.md]
summary: Linux IO栈分层架构：VFS→Block层→SCSI/NVMe层→驱动→硬件。Block层请求排队调度，Write Through/Back缓存模式，设备发现从pci_device_probe开始。
provenance:
  extracted: 0.70
  inferred: 0.25
  ambiguous: 0.05
base_confidence: 0.571
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: supporting
created: 2026-06-01
updated: 2026-06-01
---

> 虚拟化环境下的IO栈见[[concepts/linux-virtio-architecture]]——virtio是物理IO栈在虚拟化环境中的半虚拟化替代方案。

# Linux IO栈

## 核心观点

### 分层架构

Linux IO栈从上到下五层：

| 层次 | 功能 | 关键结构 |
|---|---|---|
| VFS层 | 文件系统抽象 | file/dentry/inode/superblock |
| Block层 | 请求排队与调度 | bio/request_queue |
| SCSI/NVMe层 | 协议处理 | scsi_host/nvme_dev |
| 驱动层 | 硬件控制 | 具体驱动实现 |
| 硬件层 | 物理存储 | HDD/SSD/NVMe |

数据流向：`应用read/write → VFS → Page Cache → Block层 → 驱动 → 硬件`

### Block层核心机制

Block层是IO栈调度核心：

- **bio结构**：描述IO请求的segments
- **request_queue**：请求排队，关联IO调度器
- **合并与排序**：合并相邻请求，按起始扇区排序减少寻址

### IO调度器

Block层多种调度策略^[ambiguous]：

| 调度器 | 特点 | 适用场景 |
|---|---|---|
| noop | 不排序，直接下发 | SSD/无需寻址优化 |
| CFQ | 完全公平队列 | 传统HDD，公平分配IO时间 |
| deadline | 读写分离deadline | 高延迟存储，保证响应时间 |

### Write Through vs Write Back磁盘缓存

通过`/sys/class/scsi_disk/*/cache_type`查看：

- **Write Through**：数据直接写磁盘，不利用阵列卡Cache
- **Write Back**：数据先写阵列Cache，再异步刷磁盘，性能更高但宕机风险

### 设备发现流程

从硬件枚举到用户空间可见的完整路径：

```
硬件枚举
    ↓
pci_device_probe()       # PCI驱动匹配
    ↓
xxx_probe()              # 存储驱动probe(ahci_init_one/nvme_probe)
    ↓
控制器初始化 + 设备发现
    ↓
xxx_scan()               # 扫描设备(scsi_scan_host/nvme_scan_ns)
    ↓
alloc_disk() + add_disk() # 注册gendisk到内核
    ↓
device_add() + kobject_uevent() # 通知用户空间
    ↓
/dev/sda, /sys/block/sda # 用户空间可见
```

### gendisk结构

内核表示块设备的核心结构：

- **major/minor**：设备号
- **fops**：块设备操作函数表
- **queue**：关联的请求队列
- **capacity**：设备容量

### IO路径与Page Cache

- 读路径：先查Page Cache，命中则直接返回，未命中则触发磁盘IO加载到Page Cache
- 写路径：写入Page Cache标记dirty，异步回写磁盘(Write Back模式)

## 未解问题

- NVMe队列深度与性能调优细节？
- io_uring与传统syscall的性能对比？

## 来源

- `raw/sources/Linux 操作系统/Linux 内核 IO 栈/Linux IO全景介绍.md` — 分层架构、设备发现流程、gendisk结构
- `raw/sources/Linux 操作系统/Linux 内核 IO 栈/Linux IO调度算法.md` — 仅stub链接，内容缺失^[ambiguous]