---
title: Linux Virtio架构
category: concepts
tags: [linux, 虚拟化, virtio, IO虚拟化, 半虚拟化]
aliases: [virtio, virtio框架, Virtio IO]
relationships:
  - target: "[[concepts/linux-io-stack]]"
    type: extends
  - target: "[[concepts/linux-interrupt-system]]"
    type: uses
  - target: "[[concepts/linux-interrupt-virtualization]]"
    type: uses
  - target: "[[concepts/linux-device-passthrough]]"
    type: related_to
  - target: "[[concepts/linux-network-stack]]"
    type: uses
source_dir: Linux 虚拟化/IO虚拟化
source_files: [virtio整体介绍.md, "virtio-blk和virtio-scsi的理解.md", virtio相关博客.md]
summary: Virtio是Linux半虚拟化IO框架，通过前后端分离+共享内存+eventfd通知实现高效IO。四种架构演进：传统virtio→vhost-net→vhost-user(DPDK)→vDPA，数据面逐步脱离QEMU。
provenance:
  extracted: 0.70
  inferred: 0.25
  ambiguous: 0.05
base_confidence: 0.775
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: supporting
created: 2026-06-01
updated: 2026-06-01
---

# Linux Virtio架构

Virtio是Linux半虚拟化IO的标准框架，核心思想是让Guest知道自己在虚拟环境中，从而使用高效的共享内存+通知机制而非完全模拟硬件。前后端分离是其根本架构——前端是Guest内核驱动，后端是Host上的处理程序。

## 核心观点

### 前后端分离架构

Virtio设备驱动分前端（Guest内核驱动）和后端（Host上的QEMU/内核/DPDK程序），两大核心机制支撑通信：

1. **消息通知机制** — 前端kick通知后端取请求，后端interrupt通知前端处理完成。通过[[summaries/virtio-io-notification-mechanism]]的ioeventfd/irqfd实现零拷贝通知。
2. **数据共享机制** — 前端在Guest内存中创建vring共享区域，后端直接从共享内存存取数据。详见[[summaries/virtio-vring-data-sharing]]。

### vring生产者-消费者模型

每个Virtqueue由一个Available Ring + Used Ring组成：
- Available Ring：前端向后端发送数据（前端写、后端读）
- Used Ring：后端向前端返回结果（后端写、前端读）

前端是请求的生产者和响应的消费者，后端是请求的消费者和响应的生产者^[inferred]。

### virtio-blk vs virtio-scsi

| 特性 | virtio-blk | virtio-scsi |
|------|-----------|-------------|
| 设备标识 | /dev/vda | /dev/sda |
| 通知机制 | ioeventfd前端→后端，中断注入后端→前端 | 同上 |
| 可扩展性 | ~30个设备，耗尽PCI插槽 | 数百个设备 |
| 后端驱动 | virtio_blk | scsi-block → virtio-scsi |

virtio-scsi是新一代半虚拟化SCSI控制器，提供更好的可扩展性^[inferred]。

### IO请求完整流程

```
1. Guest IO请求 → 前端virtio驱动接收 → 存入scatterlist
2. virtqueue_add_buf → 将数据映射至vring共享区域
3. kick通知 → 写PCI配置空间 → kvm_exit → ioeventfd通知QEMU
4. QEMU从vring取数据 → 封装virtioreq → 发送至硬件
5. 硬件完成 → QEMU更新vring_used → irqfd注入中断到Guest
6. Guest中断处理 → 从used ring取结果 → 释放desc表项
```

**控制面始终经过QEMU**：设备初始化、特性协商、队列配置、热迁移等由QEMU管理（保持虚拟化功能完整性）。

### 四种架构演进对比

| 架构 | 控制面过QEMU | 数据面过QEMU | 数据面过内核KVM | 性能 |
|------|-------------|-------------|---------------|------|
| 传统virtio | ✅ | ✅ | ✅ | 基础 |
| vhost-net | ✅ | ❌ | ✅ | 较高 |
| vhost-user(DPDK) | ✅ | ❌ | ❌ | 高 |
| vDPA | ✅ | ❌ | ❌ | 最高 |

演进逻辑：数据面逐步脱离QEMU用户态，从完全软件模拟到内核态offload再到用户态DPDK轮询再到硬件直通^[inferred]。

## 关键细节

### vhost-net（内核态后端）

QEMU用户态后端性能不佳（频繁上下文切换、低效数据拷贝），于是内核实现了vhost-net驱动：
- QEMU通过ioctl与/dev/vhost-net交互（控制面）
- 数据面：virtio-net与vhost-net共享vring，基于eventfd通知
- 仍通过TAP设备与外界交换数据包
- vhost-net工作在内核态，减少用户态/内核态切换开销

### vhost-user（DPDK用户态后端）

DPDK社区基于vhost协议设计了vhost-user协议：
- 通信方式从ioctl改为Unix Socket
- 特性协商、内存区域mmap映射、Vring配置、eventfd通知都通过Socket完成
- DPDK优化技术：CPU亲和性、巨页、轮询模式驱动(PMD)
- OVS-DPDK支持vhost-user端口
- Guest内部也可用DPDK virtio PMD作为前端（100% CPU占用轮询取包）

### vDPA（硬件加速数据面）

vDPA(vhost Data Path Acceleration)让virtio数据平面不需主机干预：
- 控制面仍通过vDPA driver传递到硬件
- 数据面：虚拟机与网卡之间直通，类似SR-IOV直通性能
- 网卡可直接将中断发送到虚拟机中，无需主机介入
- 硬件必须至少支持virtio ring标准
- 保留virtio标准接口，云服务提供商无需改变前端驱动

## 未解问题

- Packed Ring vs Split Ring的性能差异和切换时机？
- vDPA在实际云环境中的部署成熟度？
- virtio设备初始化的realize流程细节？


## 延伸阅读

综合分析：[[synthesis/virtio-architecture-evolution]]

## 来源

- [[summaries/virtio-io-notification-mechanism]] — ioeventfd/irqfd机制详解
- [[summaries/virtio-vring-data-sharing]] — vring数据共享机制
- `raw/sources/Linux 虚拟化/IO虚拟化/virtio整体介绍.md` — 四种架构演进、整体流程
- `raw/sources/Linux 虚拟化/IO虚拟化/virtio-blk和virtio-scsi的理解.md` — blk/scsi对比
- `raw/sources/Linux 虚拟化/IO虚拟化/virtio相关博客.md` — 参考博客链接