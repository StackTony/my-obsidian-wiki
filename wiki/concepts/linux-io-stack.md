---
title: Linux IO栈
category: concepts
tags: [linux, 内核, IO, block, 存储, 调度器]
aliases: [Linux IO架构, Block层, IO调度, 存储栈]
relationships:
  - target: "[[concepts/linux-memory-management]]"
    type: uses
  - target: "[[concepts/linux-lock-mechanisms]]"
    type: related_to
  - target: "[[concepts/linux-virtio-architecture]]"
    type: related_to
  - target: "[[concepts/linux-interrupt-system]]"
    type: related_to
source_dir: Linux 操作系统/Linux 内核 IO 栈
source_files: [Linux IO全景介绍.md, Linux IO调度算法.md]
summary: Linux IO栈分层架构：VFS→Block层→SCSI/NVMe→驱动→硬件。Block层请求排队调度，IO调度器选择指南，设备发现从pci_device_probe开始，gendisk核心结构。
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

# Linux IO栈

Linux IO栈是内核从用户态读写请求到硬件存储设备的完整数据通路，采用分层架构设计，每一层都有明确的职责和抽象边界。Block层是核心枢纽，负责请求排队、合并和调度。

## 核心观点

- IO栈采用五层分层架构：VFS → Block层 → SCSI/NVMe → 驱动 → 硬件，每层通过标准化接口解耦上下层。 ^[inferred]
- Block层是IO栈的核心枢纽，bio/request_queue/IO调度器三者协作完成请求排队和优化。
- IO调度器根据场景选择：noop适合SSD/NVMe（设备自带调度）、CFQ适合桌面多任务（公平性）、deadline适合数据库（延迟保证）。 ^[inferred]
- 设备发现流程从 pci_device_probe 开始，经过驱动probe→scan→add_disk 最终在 /dev 下暴露设备节点。
- gendisk 是Block层的核心数据结构，承载 major/minor 编号、操作函数表、请求队列和容量信息。

### 重要说明

IO调度算法源文件（Linux IO调度算法.md）仅为 stub（76字节），内容极为稀疏。本文关于IO调度器的对比分析主要基于推断，置信度较低。

## 关键细节

### 五层架构

| 层级 | 名称 | 核心职责 | 关键数据结构 |
|------|------|----------|-------------|
| L1 | VFS | 文件系统抽象，统一POSIX接口 | inode, dentry, super_block, file |
| L2 | Block层 | 请求排队、合并、调度 | bio, request, request_queue |
| L3 | SCSI/NVMe | 协议层，命令封装 | scsi_cmnd, nvme_command |
| L4 | 驱动 | 硬件交互，DMA设置 | driver特定结构 |
| L5 | 硬件 | 物理存储设备 | N/A |

### Block层核心机制

**bio 结构**：描述一个IO请求的向量化描述
- bi_sector — 起始扇区号
- bi_size — 请求大小（字节）
- bi_io_vec — iov数组（支持分散-聚集IO）
- bi_bdev — 目标块设备

**request_queue**：每个 gendisk 关联一个请求队列
- queue_lock — 保护队列的spinlock
- elevator — IO调度器实例
- boundary_tags — 请求合并边界

**请求合并优化**：
- 前向合并（forward merge）— 新请求接在已有请求后面
- 后向合并（backward merge）— 新请求插在已有请求前面
- 合合条件：连续扇区、相同方向、未超过最大段数限制

### IO调度器对比

| 调度器 | 策略 | 适用场景 | 延迟特性 |
|--------|------|----------|----------|
| noop | FIFO，不做排序 | SSD/NVMe（设备自带调度）、虚拟机 | 延迟取决于请求到达顺序 |
| CFQ | 时间片轮转，按进程公平分配 | 桌面多任务、通用场景 | 保证公平但单流延迟可能较高 |
| deadline | 请求按扇区排序 + 读/写过期时间 | 数据库、低延迟要求场景 | 严格保证最大延迟 |
| mq-deadline | deadline的多队列版本 | NVMe等多队列设备 | 同deadline但支持多硬件队列 |

**选择指南**：
- NVMe设备 → noop 或 mq-deadline ^[inferred]
- 传统机械盘 + 数据库 → deadline
- 传统机械盘 + 桌面通用 → CFQ（但内核5.x已默认弃用CFQ） ^[ambiguous]

### 设备发现流程

从PCI总线到 /dev/sda 的完整路径：

```
pci_device_probe()
  → xxx_probe()          # 驱动绑定
    → xxx_scan()          # 扫描发现设备
      → scsi_add_device()  # (SCSI路径)
      → add_disk()         # 注册gendisk
        → /dev/sda         # 设备节点出现
```

每个步骤的职责：
- pci_device_probe — PCI子系统匹配设备与驱动
- xxx_probe — 驱动初始化硬件、注册中断
- xxx_scan — 发现连接的存储目标（如SCSI target）
- add_disk — 将 gendisk 注册到内核，触发 uevent 创建 /dev 节点

### gendisk 核心结构

gendisk 是Block层对块设备的抽象：

| 字段 | 含义 |
|------|------|
| major / first_minor | 设备编号（主/次设备号） |
| fops | block_device_operations 函数表 |
| queue | 关联的 request_queue |
| capacity | 设备容量（扇区数） |
| disk_name | 设备名（如 "sda"） |

### IO路径与 Page Cache 交互

写路径：用户数据 → Page Cache（Write Back模式） → 标记脏页 → pdflush/kworker → bio → Block层 → 硬件

读路径：用户请求 → 检查 Page Cache → 缓存命中直接返回 / 缓存未命中 → bio → Block层 → 硬件 → 数据进入 Page Cache → 返回用户

IO栈与 [[concepts/linux-memory-management]] 的 Page Cache 紧密交互，Write Back 模式下写请求不直接到达Block层，而是先写入 Page Cache 后异步刷盘。

### Write Through vs Write Back

| 策略 | 写路径 | 性能 | 数据安全 |
|------|--------|------|----------|
| Write Through | 用户→Page Cache→同步写磁盘 | 低 | 高 |
| Write Back | 用户→Page Cache→异步刷盘 | 高 | 低（断电风险） |

## 未解问题

- NVMe多队列调度器（blk-mq）与传统单队列调度器的完整对比仍缺少源文件支撑。 ^[inferred]
- io_uring 对传统IO栈路径的绕过程度——是否完全跳过Block层调度？ ^[ambiguous]


## 延伸阅读

实操指南：[[skills/linux-io-debugging]]

综合分析：[[synthesis/linux-kernel-subsystem-interactions]]

## 来源

- [[summaries/linux-page-cache]] — Page Cache与IO路径的交互
- [[summaries/linux-meminfo-params]] — 内存统计中与IO相关的Buffers/Cached字段