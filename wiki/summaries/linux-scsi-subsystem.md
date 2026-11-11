---
title: Linux SCSI 子系统
category: summaries
tags: [linux, scsi, 内核, 存储, 驱动]
aliases: [SCSI子系统, SCSI三层架构, CDB, scsi_cmnd]
relationships:
  - target: "[[concepts/linux-io-stack]]"
    type: implements
  - target: "[[summaries/linux-block-subsystem]]"
    type: related_to
  - target: "[[concepts/linux-driver-model]]"
    type: implements
  - target: "[[summaries/linux-pci-subsystem]]"
    type: related_to
source_dir: Linux 操作系统/Linux 驱动管理/Linux SCSI 系统
source_files: [Linux内核SCSI子系统.md]
summary: SCSI 子系统三层架构（较高层/中间层/较低层）与 Initiator-Target-LUN 模型；CDB 6/10/16 字节命令族及 0x28 READ_10、0x2A WRITE_10、0x35 SYNCHRONIZE_CACHE 等核心操作码；scsi_host_template/scsi_cmnd 驱动骨架。
provenance:
  extracted: 0.85
  inferred: 0.12
  ambiguous: 0.03
base_confidence: 0.59
lifecycle: draft
lifecycle_changed: 2026-11-11
tier: supporting
created: 2026-11-11
updated: 2026-11-11
---

# Linux SCSI 子系统

野火 RK356x 驱动教程第 7 章的蒸馏。核心判断：SCSI 早已不是"一种并行总线"，而是**一套逻辑命令协议**（SPC-4 主命令集 / SBC-3 块命令集），SAS、Fibre Channel、iSCSI、USB 大容量存储最终都映射进这个子系统。

## 概述

SCSI 子系统的价值在于**屏蔽底层物理总线**：不管下面是 SATA、USB 还是网络，上层块设备层只面对标准 SCSI 命令。^[inferred] 因此它是 Linux 存储栈的"公共转接层"，也是理解 [[concepts/linux-io-stack]] 中 Block 层之下发生了什么的关键。

## 核心观点

- **协议与总线分离**：物理总线被串行技术取代（SAS/FC/SATA），命令集协议被保留并标准化——这是 SCSI 存活下来的原因。
- **发起者-目标模型**：Initiator（HBA）发 CDB，Target 执行并返回状态；失败时 Target 回 Sense Data（Sense Key + ASC + ASCQ），内核据此重试或告警。
- **LUN 是 Target 内部的逻辑实体**：一个 Target 可含多个 LUN，一块具体硬盘通常对应一个 LUN。
- **三层各司其职**：较高层做抽象与转换（block 请求 → SCSI 命令），中间层做调度与错误处理（命令队列、Sense 解析、SG 拷贝），较低层只碰硬件。
- **命令长度随容量升级**：6 字节命令寻址空间不够 → 10 字节成为现代默认（32 位 LBA，TB 级）→ 16 字节支持 64 位 LBA（PB 级）；内核优先尝试 16 字节容量查询，失败降级 10 字节。

## 关键细节

### 三层架构

| 层 | 职责 | 与相邻层的关系 |
|---|---|---|
| 较高层（Upper） | 设备枚举、设备节点创建、块请求→SCSI 命令、属性管理、ioctl | 对接 VFS/块层与用户态，与硬件无关 |
| 中间层（Middle） | 主机适配器管理、命令队列调度、命令预处理/后处理、Sense 解析、通用错误处理、SG 数据拷贝 | 承上启下：对上统一入口，对下标准化回调 |
| 较低层（Lower） | 厂商 HBA 驱动：实现回调、下发硬件命令、读写硬件、私有错误处理 | 只适配自身硬件，不关心协议通用逻辑 |

### 核心结构体

- `scsi_driver` — 较高层驱动管理，承接设备生命周期、命令初始化/销毁、完成回调、错误恢复。
- `Scsi_Host` — 一个主机适配器实例。
- `scsi_host_template` — 主机模板，驱动实现 `queuecommand` 等回调。
- `scsi_cmnd` — 一条 SCSI 命令：`cmnd[]` 存 CDB，含 `resid`（残余字节数 = 请求总长 − 实际传输）。
- `scsi_device` / `scsi_target` — 逻辑设备与目标设备。
- `scsi_data_buffer` — 数据缓冲区（SG 表）。
- `scsi_disk` — SCSI 磁盘对块层的封装。

### CDB 结构与命令族

CDB 通用字段：Opcode（第 0 字节，分发依据）、LBA 地址、Transfer Length、Control 控制位。

**6 字节（SCSI-2，老设备兼容）**

| 命令 | 操作码 | 用途 |
|---|---|---|
| TEST_UNIT_READY | 0x00 | 就绪探测，内核高频轮询；上电/扫描/热插拔/超时重试后校验 |
| INQUIRY | 0x12 | 读取厂商/型号/设备类型，总线扫描阶段区分磁盘/光驱/RAID |
| MODE_SENSE_6 | 0x1A | 读工作模式参数（缓存策略、超时、介质类型） |
| MODE_SELECT_6 | 0x15 | 与 MODE_SENSE_6 配对，改设备参数 |
| READ_6 | 0x08 | 小容量读取，现代内核默认改走 READ_10 |
| WRITE_6 | 0x0A | 小容量写入 |

**10 字节（SCSI-3 / SPC-4，现代默认）**

| 命令 | 操作码 | 用途 |
|---|---|---|
| MODE_SENSE_10 | 0x5A | 完整模式页、缓存/PI 校验/电源参数 |
| MODE_SELECT_10 | 0x55 | 配置高级工作模式 |
| READ_CAPACITY_10 | 0x25 | 最大 LBA + 扇区字节数，内核据此算容量 |
| READ_10 | 0x28 | 32 位 LBA 任意扇区批量读 |
| WRITE_10 | 0x2A | 与 READ_10 配对写 |
| VERIFY_10 | 0x2F | 只校验不搬数据：磁盘自检、坏块扫描 |
| SYNCHRONIZE_CACHE | 0x35 | 强制刷设备板载缓存，关机/umount/同步时保数据 |

**16 字节（扩展）**

- `READ_CAPACITY_16`（0x9E）— 64 位 LBA，PB 级设备、SAN、分布式存储。

### 命令生命周期

`scsi_alloc_queue` 建请求队列 → 块层下发 → 中间层组装 `scsi_cmnd` → 较低层 `queuecommand` 写硬件 → 硬件完成中断 → 驱动回调 `scsi_done` → 中间层解析 Sense、累计 `resid` → 回块层完成。 ^[inferred]

验证工具链：`sg3_utils`（`sg_inq` 查 INQUIRY、`sg_readcap` 查容量、`sg_turs` 测就绪、`sg_verify` 校验 LBA 区间、`sg_sync` 刷缓存）。

## 未解问题

- 中间层的错误恢复状态机（EH，`scsi_eh_*`）只有结论级描述，缺超时/重试/设备重置的分支条件。
- 多队列（blk-mq）与 SCSI 中间层队列的对接方式未展开。
- SG_IO 透传（`sg` 驱动）与普通块 IO 的路径差异未覆盖。
- UFS/NVMe 这类"不走 SCSI 命令集"的设备如何与本文模型对照，需另找来源。

## 来源

- `raw/sources/Linux 操作系统/Linux 驱动管理/Linux SCSI 系统/Linux内核SCSI子系统.md` — 野火 RK356x 驱动教程第 7 章：SCSI 基础、三层架构、核心结构体与函数、标准命令族、中间层源码解析、虚拟 SCSI 主机驱动实验
- 交叉：[[summaries/linux-block-subsystem]]（bio/request 如何进入 SCSI）、[[concepts/linux-io-stack]]（五层 IO 栈全局位置）
