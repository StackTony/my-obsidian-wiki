---
title: Linux DMA 与 IOMMU 子系统（SoC 驱动视角）
category: summaries
tags: [linux, DMA, IOMMU, 驱动, SoC]
aliases: [DMA子系统, IOMMU子系统, dma_alloc_coherent, iommu_domain]
relationships:
  - target: "[[concepts/linux-dma-mapping]]"
    type: extends
  - target: "[[concepts/linux-iommu-subsystem]]"
    type: extends
  - target: "[[summaries/linux-iommu-deep-dive]]"
    type: related_to
  - target: "[[concepts/linux-driver-model]]"
    type: implements
source_dir: Linux 操作系统/Linux 驱动管理/Linux IOMMU
source_files: [Linux DMA和IOMMU.md]
summary: SoC 驱动视角的 DMA/IOMMU：三类 DMA 内存（一致性/流式/散射聚集）+三段传输类型 + 四步工作流；IOMMU 五大功能与传统裸 DMA 四缺陷；dma_alloc_coherent/iommu_map/iommu_attach_device 等 API 与 RK3588 实验。
provenance:
  extracted: 0.80
  inferred: 0.17
  ambiguous: 0.03
base_confidence: 0.59
lifecycle: draft
lifecycle_changed: 2026-11-11
tier: supporting
created: 2026-11-11
updated: 2026-11-11
---

# Linux DMA 与 IOMMU 子系统（SoC 驱动视角）

野火 RK356x 驱动教程第 1 章的蒸馏。与本 vault 已有的 x86 视角材料（[[summaries/linux-iommu-deep-dive]] 六部曲、[[concepts/linux-iommu-subsystem]] 框架层）互补：本文是**写驱动的人**会用到的那一层——分配什么内存、调什么 API、失败时看哪里。

## 概述

一句话分工：**DMA 搬数据，IOMMU 管地址、管权限、管隔离**。无 IOMMU 时驱动把物理地址直接交给设备；有 IOMMU 时驱动交 IOVA，硬件实时翻译并校验权限。

## 核心观点

- **三类 DMA 内存对应三种使用习惯**：一致性（长期持有、硬件自动同步缓存、小控制块）／流式（临时 map-unmap、手动同步缓存、大数据）／散射聚集（物理不连续、一次提交多段，依赖硬件 SG 能力）。
- **三类传输方向**：DEV_TO_MEM（采集）、MEM_TO_DEV（输出）、MEM_TO_MEM（内存搬运，CPU 完全不参与）。
- **四步工作流固定不变**：CPU 初始化配置 → 硬件自动搬运 → 中断收尾 → 资源释放；驱动错误多出在第一步（掩码/尺寸）和第四步（漏释放）。
- **IOMMU 解决的是裸 DMA 的四个结构性缺陷**：4GB 寻址天花板、碎片内存不可用、无隔离、无权限。
- **一致性 DMA 的代价值得记住**：内存利用率低（对齐与冗余）、长期运行易碎片化，所以"控制块用 coherent、数据流用 streaming"是默认选择。 ^[inferred]

## 关键细节

### 传统裸 DMA 的四缺陷与 IOMMU 的五功能

| 裸 DMA 缺陷 | IOMMU 对应能力 |
|---|---|
| 老旧设备只能访问 4GB 以内 | 地址翻译：设备用 IOVA，硬件翻成 64 位物理地址 |
| 必须物理连续内存，碎片化后无法传大数据 | 碎片整合：零散物理页拼成连续 IOVA |
| 所有设备共用同一内存空间，可互相篡改 | 设备隔离：每设备独立地址空间 |
| 设备默认有全部读写权限 | 权限管控：可设只读，防篡改内核数据 |

第五项能力是**虚拟机直通**：把物理设备直接分给虚机使用（详见 [[concepts/linux-device-passthrough]]）。

### 有/无 IOMMU 的流程对比

- 无：CPU 分配物理连续内存 → 把物理地址告诉设备 → 设备直接访存（无翻译、无校验）。
- 有：CPU 分配物理内存 → IOMMU 建页表（IOVA → PA）→ 驱动把 IOVA 交给设备 → 设备用 IOVA 访存 → IOMMU 实时翻译并校验权限。

### 核心结构体与 API

| 层 | 结构体/API | 用途 |
|---|---|---|
| DMA 控制器 | `dma_device`、`dma_chan`、`dma_slave_config`、DMA 通道设备节点 | 通道分配与从设备配置（音频/串口/SPI 这类 slave DMA） |
| DMA 缓冲 | `dma_buf` 相关挂载/导出结构 | 缓冲区共享与导出 |
| DMA-IOMMU 桥 | `dma_iommu_mapping` | DMA 映射落到 IOMMU 域 |
| 掩码 | `dma_set_mask` / `dma_set_coherent_mask` | 声明设备可寻址位数 |
| 一致性内存 | `dma_alloc_coherent` / `dma_free_coherent` | 分配硬件自动一致的物理连续内存 |
| SG | `dma_get_sgtable_attrs` | 取带属性的散射聚集表 |
| IOMMU 域 | `iommu_ops`、`iommu_domain`、`iommu_domain_geometry` | 硬件操作集、地址域、域孔径几何属性 |
| 域生命周期 | `iommu_domain_alloc` / `iommu_domain_free` | 分配/释放地址域 |
| 映射 | `iommu_map` / `iommu_unmap` / `iommu_map_sg` | 单页映射、解映射、SG 批量映射 |
| 绑定 | `iommu_attach_device` | 设备绑定到域（域生效的前提） |
| 故障与预留 | `iommu_set_fault_handler`、预留固定映射区 | 异常回调、保留区 |
| 缓存 | `iommu_flush_iotlb_all` | 刷 IOTLB |

### 实验锚点

RK3588（LubanCat）平台：设备树插件声明 reserved-memory 与 DMA 节点 → 驱动里 `dma_alloc_coherent` 分配、写数据、交给设备读回 → 验证 CPU 与设备看到的是同一份内容（一致性内存不需要手动 flush）。^[inferred]

### 与已有页面的关系

- DMA 映射的两种类型与 Intel IOMMU 下的分流 → [[concepts/linux-dma-mapping]]
- IOMMU 框架五层与 ARM SMMU → [[concepts/linux-iommu-subsystem]]
- Group/Domain 隔离粒度 → [[concepts/iommu-group-domain-isolation]]
- SWIOTLB bounce 排查 → [[skills/swiotlb-troubleshooting]]

## 未解问题

- `dma_alloc_coherent` 在 IOMMU 使能时究竟拿到物理连续内存还是 IOVA 连续，本文与 x86 六部曲口径需要对齐。^[ambiguous]
- slave DMA（`dma_request_chan`）与 dmaengine 描述符链的编程模型未展开。
- `dma_iommu_mapping` 与 IOMMU 默认域的创建顺序未给出源码依据。
- SG 表在 IOMMU 下的合并策略（`iommu_map_sg` 的边界条件）缺具体数值。

## 来源

- `raw/sources/Linux 操作系统/Linux 驱动管理/Linux IOMMU/Linux DMA和IOMMU.md` — 野火 RK356x 驱动教程第 1 章：DMA/IOMMU 概念、核心结构体与函数、RK3588 一致性 DMA 实验
- 交叉：[[concepts/linux-dma-mapping]]、[[concepts/linux-iommu-subsystem]]
