---
title: Linux IOMMU子系统与ARM SMMU
category: concepts
tags: [linux, IOMMU, SMMU, ARM, 内核]
aliases: [SMMU, ARM SMMU, IOMMU抽象层, System MMU, SVA]
relationships:
  - target: "[[concepts/linux-dma-mapping]]"
    type: implements
  - target: "[[summaries/linux-iommu-deep-dive]]"
    type: related_to
  - target: "[[concepts/virtual-memory-and-paging]]"
    type: extends
  - target: "[[concepts/iommu-group-domain-isolation]]"
    type: related_to
source_dir: Linux 操作系统/Linux 设备驱动管理
source_files: [Linux IOMMU、SMMU(ARM)技术图解.md]
summary: Linux内核抽象统一IOMMU层，屏蔽Intel VT-d/AMD/ARM SMMU硬件差异；框架五层：DMA-MAP API、IOVA分配(RCACHE)、IO页表、驱动回调、VFIO接口。SVA让CPU与设备共享页表。
provenance:
  extracted: 0.50
  inferred: 0.45
  ambiguous: 0.05
base_confidence: 0.44
lifecycle: draft
lifecycle_changed: 2026-11-10
tier: supporting
created: 2026-11-10
updated: 2026-11-10
---

# Linux IOMMU子系统与ARM SMMU

硬件上能完成设备IOVA到物理地址转换的单元不止一种：Intel的IOMMU（VT-d）、AMD的IOMMU、ARM的SMMU等等。它们不会各自作为独立子系统存在于内核——Linux在驱动与硬件之间**抽象出一层统一的IOMMU层**，向外部设备驱动提供统一结构，隐藏底层不同架构的差异。x86 Intel VT-d的实现细节见[[summaries/linux-iommu-deep-dive]]。

## 核心观点

### 统一抽象的分层框架

IOMMU框架自上而下分为五层：

| 层 | 职责 |
|----|------|
| **DMA-MAP层** | 对其他驱动提供DMA MAP/UNMAP的API接口 |
| **IOVA层** | IOVA的分配与释放，提供RCACHE缓存机制 |
| **IO页表层** | 对IO设备页表的操作 |
| **SMMU/IOMMU驱动层** | SMMU/IOMMU驱动初始化，提供IOMMU对应的回调函数 |
| **其它API接口** | 对VFIO等提供API接口 |

分层意味着驱动代码只面对 `dma_map_*` 这类稳定接口与回调函数指针，更换IOMMU硬件不触及上层——与内核其他子系统（如调度器sched、中断irq_domain）的"框架+驱动注册回调"设计模式一致 ^[inferred]。DMA-MAP层对上的语义即[[concepts/linux-dma-mapping]]的两类映射。

### SMMU：ARM的IOMMU

- SMMU（System Memory Management Unit）是ARM体系中的IOMMU实现，作用与x86的Intel VT-d对等：把设备发出的地址翻译为内存物理地址 ^[inferred]
- 在SoC中，SMMU位于设备（master）与内存之间——设备访问内存的路径上串接SMMU，如同CPU访存路径上串接MMU；IOMMU的master只能是设备，slave是Host Memory或经BAR映射的设备Memory
- SMMU的软硬件交互过程（命令队列、TLB、页表遍历）原文以图为主，待补 ^[ambiguous]
- SMMU与MMU对偶：MMU做CPU虚拟地址→物理地址，SMMU/VT-d/AMD IOMMU做设备总线地址→物理地址；内核统一IOMMU抽象让三者共享上层框架 ^[inferred]

### SVA：共享虚拟地址

SVA（Share Virtual Addressing）：CPU和Device**共享同一份页表**。设备DMA不再使用独立的IOVA空间，而是直接用与CPU相同的虚拟地址——省去两套地址空间之间的映射与同步 ^[inferred]。这是IOMMU能力从"隔离与重映射"向"地址空间统一"的延伸方向 ^[inferred]。具体实现（共享页表的缺页处理、权限模型）本来源未展开。

## 关键细节

- RCACHE缓存机制位于IOVA层：IOVA的分配/释放走缓存池以降低开销 ^[inferred]（本来源仅提及名称，细节待补）
- 抽象层的收益在虚拟化场景放大：VMM只需面对统一IOMMU API即可管理任意平台的设备直通，见[[concepts/linux-device-passthrough]]
- Group/Domain模型同样定义在统一抽象之上，与具体硬件无关，见[[concepts/iommu-group-domain-isolation]]

## 未解问题

- SMMUv3的命令队列、event queue等具体机制？
- SVA由哪个SMMU版本开始支持？与Intel的Scalable IOV（S-IOV）的关系？
- RCACHE（IOVA per-CPU缓存）的回收与批量归还策略？

## 来源

- `raw/sources/Linux 操作系统/Linux 设备驱动管理/Linux IOMMU、SMMU(ARM)技术图解.md` — 内核IOMMU框架分层、多厂商抽象、SMMU位置、SVA
