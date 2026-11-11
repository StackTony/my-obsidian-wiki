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
  - target: "[[concepts/ssd-trim-write-amplification]]"
    type: related_to
  - target: "[[concepts/linux-io-models]]"
    type: related_to
source_dir: Linux 操作系统/Linux 内核 IO 栈
source_files: [Linux IO全景介绍.html, Linux IO栈介绍.md, Linux IO下发流程.md, "==Linux IO调度算法==/Linux 内核的 4 大 IO 调度算法.md", "Linux IO技术/Linux 文件一致性问题&Dirty概念&解决方案.md", "Linux 操作系统/Linux 驱动管理/Linux Block块设备 系统/Linux内核块设备.md", "Linux 操作系统/Linux 驱动管理/Linux SCSI 系统/Linux内核SCSI子系统.md", "物理硬件/磁盘/TRIM擦除指令.md", "物理硬件/PCIe/PCIE错误类型与NVMe掉盘根因诊断指南.md"]
summary: Linux IO栈分层架构：VFS→Block层→SCSI/NVMe→驱动→硬件。Block层bio/request_queue/调度器协作；4大IO调度器对比（Noop/CFQ/Deadline/Anticipatory）；设备发现从pci_device_probe到add_disk；hctx tags busy确认IO阻塞；cache_type决定write through/back。
provenance:
  extracted: 0.82
  inferred: 0.15
  ambiguous: 0.03
base_confidence: 0.72
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: supporting
created: 2026-06-01
updated: 2026-11-11
---

# Linux IO栈

Linux IO栈是内核从用户态读写请求到硬件存储设备的完整数据通路，采用分层架构设计，每一层都有明确的职责和抽象边界。Block层是核心枢纽，负责请求排队、合并和调度。

![[Pasted image 20260424165505.png]]

## 核心观点

- IO栈采用五层分层架构：VFS → Block层 → SCSI/NVMe → 驱动 → 硬件，每层通过标准化接口解耦上下层。 ^[inferred]
- Block层是IO栈的核心枢纽，bio/request_queue/IO调度器三者协作完成请求排队和优化。
- IO调度器通过**合并**（merge相邻扇区请求）和**排序**（按磁盘转动方向排列）两种方式减少磁头移动；4大调度器各有侧重：Noop仅合并排序（适合SSD）、CFQ按进程公平分配时间片（适合通用服务器）、Deadline保证最大延迟（适合数据库）、Anticipatory在Deadline基础上预测等待（适合随机+顺序IO混合）。
- 设备发现流程从 `pci_device_probe` 开始，经过驱动probe→scan→`add_disk` 最终在 /dev 下暴露设备节点。
- gendisk 是Block层的核心数据结构，承载 major/minor 编号、操作函数表、请求队列和容量信息。

## 关键细节

### 五层架构

| 层级 | 名称 | 核心职责 | 关键数据结构 |
|------|------|----------|-------------|
| L1 | VFS | 文件系统抽象，统一POSIX接口 | inode, dentry, super_block, file |
| L2 | Block层 | 请求排队、合并、调度 | bio, request, request_queue |
| L3 | SCSI/NVMe | 协议层，命令封装 | scsi_cmnd, nvme_command |
| L4 | 驱动 | 硬件交互，DMA设置 | driver特定结构 |
| L5 | 硬件 | 物理存储设备 | N/A |

### L5 硬件层：SSD介质语义（TRIM与写放大）

IO栈最底层L5并非黑盒：NAND闪存读/写以page为单位、擦除以block为单位且不允许覆盖写，这直接决定上层行为——文件系统的"删除"只标记自身元数据，介质并不知道哪些page无效；无TRIM时SSD必须以read-erase-modify-write整block的方式服务覆盖写，产生写放大并拖慢GC。TRIM指令（Linux的discard请求）把"已删除"信息从文件系统下推到介质。详见 [[concepts/ssd-trim-write-amplification]]，检测与启用实操见 [[skills/linux-io-debugging]]。此外，NVMe设备"从系统消失"类故障往往不在本栈任何一层，而在更底下的PCIe链路——见 [[concepts/pcie-error-aer-nvme-drive-loss]]。

触发来源：物理硬件/磁盘/TRIM擦除指令.md、物理硬件/PCIe/PCIE错误类型与NVMe掉盘根因诊断指南.md（2026-11-06 ingest）。

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
- 合并条件：连续扇区、相同方向、未超过最大段数限制

**blk-mq 双层队列**（4.x 后期起的默认架构，取代 `queue_lock` 保护的全局单队列）：
- 软件队列 `mq_ctx` — 每个 CPU 一个私有队列，入队无跨核锁竞争
- 硬件队列 `hw_ctx` — 数量通常等于 CPU 核数或硬件通道数，负责汇总下发
- 标签集 `blk_mq_tag_set` 统一配置队列数、深度、超时、NUMA 节点；驱动唯一必需的 `blk_mq_ops.queue_rq` 取 request 操作硬件
- 完成侧统一走 `blk_mq_end_request`，漏调即 IO 挂死

详见 [[summaries/linux-block-subsystem]]。^[inferred]

### SCSI 中间层在栈中的位置

L3 的 SCSI 不是单一驱动，而是三层：**较高层**（块请求 → SCSI 命令、设备枚举与节点创建）→ **中间层**（主机适配器管理、命令队列调度、Sense 解析、SG 拷贝）→ **较低层**（厂商 HBA 驱动）。命令单位是 CDB（6/10/16 字节，现代默认 `READ_10` 0x28 / `WRITE_10` 0x2A），失败以 Sense Data 回报。详见 [[summaries/linux-scsi-subsystem]]。

### IO下发流程

![[Diagram 2.svg]]

简易流程：**P层（VFS/文件系统）→ Block层 → SCSI层 → 驱动 → 硬件**

1. 通用Block层：把请求排队，进入调度层
2. SCSI层：提交给驱动层等待返回
3. 硬件：返回处理成功或超时

### IO调度器对比

IO调度器决定块设备上IO操作提交的顺序，目的有二：提高IO吞吐量、降低IO响应时间。两者往往矛盾，不同调度器在不同场景下取舍。每个块设备有自己的 `request_queue`，每个请求队列可选择一个IO调度器。调度器自身维护额外的队列，排在最前面的request适时被移动到 `request_queue` 中等待响应。

| 调度器 | 核心策略 | 队列结构 | 适用场景 |
|--------|----------|----------|----------|
| Noop | FIFO+合并排序（又称电梯算法） | 单FIFO队列 | SSD/NVMe、NAS、虚拟机 |
| CFQ | 按进程公平分配时间片 | 每进程请求队列+17个异步队列 | 通用服务器、桌面 |
| Deadline | 排序+FIFO过期保证 | 排序队列+读FIFO+写FIFO | 数据库、DSS |
| Anticipatory | Deadline+预测等待 | 排序队列+读写FIFO+预测窗口 | 随机+顺序IO混合 |

**Noop**（No Operation）：请求来一个处理一个，但并非完全不优化——新请求到来时先尝试合并，不能合并则尝试按位置排序插入，都无法满足则放到队尾。因实现简单有效，适合不需要寻道的SSD/NVMe设备，也适合上层已有智能调度的NAS设备或已精心优化IO请求的应用。

**CFQ**（Completely Fair Queuing，Linux 2.6.18起默认）：为竞争块设备的每个进程分配请求队列和时间片，时间片内进程可发送读写请求，耗尽后队列挂起等待。时间片和队列长度取决于进程的IO优先级（RT/BE/IDLE三大类，RT和BE各分8个子优先级，可通过`ionice`查看和修改）。同步请求放入进程自身队列，同优先级异步请求放入公共队列（共17个：8 RT + 8 BE + 1 IDLE）。通用服务器的较好选择。

**Deadline**：在排序队列（Elevator方式按物理位置排序）基础上，额外为读IO和写IO各维护一个FIFO队列。FIFO队列内请求的优先级高于排序队列，读FIFO又高于写FIFO：**FIFO(Read) > FIFO(Write) > 排序队列**。读请求的最大等待时间远短于写请求（因读请求通常阻塞调用进程，写请求一般异步写回），保证单个IO请求以最小延迟被处理。适合数据库等随机读写场景。但注意：对binlog/online log等调用fsync的写密集分区，Deadline可能不是最优选择——写完不成会严重影响应用性能。

> 读FIFO最大等待时间：原文一处称500ms、另一处称5ms，两处不一致。 ^[ambiguous]

**Anticipatory**：在Deadline基础上，为每个读IO设置6ms等待窗口。在此窗口内若收到相邻位置的读IO请求，可立即满足。设计目的是在随机IO和顺序IO混合场景下兼顾连续IO的优化——CFQ和Deadline聚焦零散IO，对顺序读无优化。

**选择指南**：
- SSD/NVMe → Noop（设备无寻道，其他调度器的排序优化无意义）
- 传统SAS盘 + 数据库 → Deadline（吞吐量和响应时间均表现良好）
- 传统SAS盘 + 通用服务器 → CFQ（Linux 2.6.18起默认）
- 随机+顺序IO混合 → Anticipatory

> CFQ在内核5.x以后的默认状态存在争议——部分发行版已切换默认调度器，但源文件未明确说明具体版本和替代者。 ^[ambiguous]

### 设备发现流程

从PCI总线到 /dev/sda 的完整路径：

```
硬件枚举
    │
    ▼
pci_device_probe()                    # PCI 驱动匹配
    │
    ▼
xxx_probe()                           # 存储驱动 probe (ahci_init_one/nvme_probe)
    │
    ▼
控制器初始化 + 设备发现
    │
    ▼
xxx_scan()                            # 扫描设备 (scsi_scan_host/nvme_scan_ns)
    │
    ▼
设备识别                               # 获取设备信息
    │
    ▼
块设备注册
    │
    ├── alloc_disk()                  # 分配 gendisk
    ├── 设置容量、队列、操作函数
    └── add_disk()                    # 注册到内核
    │
    ▼
device_add() + kobject_uevent()       # 发送到用户空间
    │
    ▼
用户空间可见: /dev/sda, /sys/block/sda
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

IO栈与 [[concepts/linux-memory-management]] 的 Page Cache 紧密交互，Write Back 模式下写请求不直接到达Block层，而是先写入 Page Cache 后异步刷盘。Page Cache的预读策略和脏页写回机制详见 [[concepts/linux-io-models]]。

### Write Through vs Write Back

![[Pasted image 20260430114122.png]]

| 策略 | 写路径 | 性能 | 数据安全 |
|------|--------|------|----------|
| Write Through | 用户→Page Cache→同步写磁盘 | 低 | 高 |
| Write Back | 用户→Page Cache→异步刷盘 | 高 | 低（断电风险） |

存储侧同样存在此区分：阵列卡 cache_type（`cat /sys/class/scsi_disk/0:2:0:0/cache_type`）决定写路径——write through 不利用阵列Cache直接与磁盘交互；write back 以阵列Cache为二传手（系统→Cache→磁盘）。

**文件一致性由两种方式落地**：Write Through 由应用主动调接口保证；Write Back 由内核线程周期性回写（Linux 默认）。两种方式最终都收敛到三个系统调用：

| 调用 | 范围 |
|---|---|
| `fsync(fd)` | 该文件的脏数据 + 脏元数据全部落盘 |
| `fdatasync(fd)` | 该文件的脏数据 + 必要元数据（不必刷所有元数据） |
| `sync()` | 系统内所有脏数据与脏元数据 |

写操作命中 Page Cache 时数据先写内存，未回写前该 page 即 **Dirty page**——此时内存数据领先于磁盘，断电即丢。^[inferred]

### IO阻塞确认

判断IO是否卡在块层等待硬件返回：读 `/sys/kernel/debug/block/sdX/hctx0/tags`，busy 值非0代表存在等待IO返回的请求，即可能存在IO阻塞。实操细节见 [[skills/linux-io-debugging|IO调试实操]]。

## 未解问题

- NVMe多队列调度器（blk-mq）与传统单队列调度器的完整对比：blk-mq 的软/硬队列与 tag 机制已由野火教材补全，但调度器本身（`none`/`mq-deadline`/`bfq`/`kyber`）的来源仍缺。 ^[inferred]
- io_uring 对传统IO栈路径的绕过程度——是否完全跳过Block层调度？ ^[ambiguous]

## 延伸阅读

- IO模型体系（阻塞/非阻塞/多路复用/异步、缓存IO vs 直接IO）：[[concepts/linux-io-models]]
- Page Cache与Buffer Cache：[[concepts/page-cache-vs-buffer-cache]] — Buffer Cache 在块设备层的角色与2.4统一机制
- DMA地址翻译与IOMMU：[[summaries/linux-iommu-deep-dive]]、[[concepts/linux-dma-mapping]] — `dma_map_single` 后经 swiotlb/intel_dma_ops 分流；启用Intel IOMMU后DMA地址表现为IOVA而非物理地址，是IO栈中地址语义的重要变化
- 实操指南：[[skills/linux-io-debugging]]
- 综合分析：[[synthesis/linux-kernel-subsystem-interactions]]

## 来源

- [[summaries/linux-page-cache]] — Page Cache与IO路径的交互
- [[summaries/linux-meminfo-params]] — 内存统计中与IO相关的Buffers/Cached字段
- [[concepts/linux-io-models]] — IO模型与缓存IO/直接IO
