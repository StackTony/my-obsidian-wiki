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
  - target: "[[summaries/linux-smmu-io-bypass]]"
    type: related_to
source_dir: Linux 操作系统/Linux 设备驱动管理/Linux IOMMU
source_files: [Linux IOMMU、SMMU(ARM)技术图解.md, Linux SMMU的IO Bypass.md]
summary: Linux内核抽象统一IOMMU层，屏蔽Intel VT-d/AMD/ARM SMMU硬件差异；五层框架：DMA-MAP API、IOVA分配(RCACHE)、IO页表、驱动回调、VFIO接口。SVA共享页表；SMMU可STE级bypass直通PA。
provenance:
  extracted: 0.55
  inferred: 0.40
  ambiguous: 0.05
base_confidence: 0.61
lifecycle: draft
lifecycle_changed: 2026-11-10
tier: supporting
created: 2026-11-10
updated: 2026-11-11
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

### SMMU IO Bypass：STE级别的翻译旁路

IO Bypass 常被误读为"关闭 SMMU"。实际上 SMMU 硬件照常上电工作，只是把特定设备 SID 对应的 **STE（Stream Table Entry）配置成 Bypass 模式**：该设备的 DMA 流量直接透传物理地址，不经过 Stage1/Stage2 翻译、不做 IOTLB 查找、不做页表权限检查。这与 BIOS 关闭 SMMU（整个硬件不工作）是两回事。

- 三种模式并存：正常翻译（设备见 IOVA）/ SMMU 开启+bypass（设备见 PA，硬件直通）/ BIOS 关闭 SMMU（设备见 PA，内核用 SWIOTLB bounce 兜底）
- 控制参数：`iommu.passthrough=1`（全局默认 bypass）、`smmu.bypassdev=<BDF>`（仅指定设备，最常用）、`disable_bypass`（禁用旁路能力，强制所有 SID 走翻译）
- bypass 跳过页表权限检查，等于对该设备开放全部物理内存——安全敏感场景应选 `disable_bypass` ^[inferred]

完整机制、参数与模式对比见[[summaries/linux-smmu-io-bypass]]；"bypass 用 PA 不拷贝"与"BIOS 关闭后 SWIOTLB 拷贝"在排查时极易混淆，见[[skills/swiotlb-troubleshooting]]。

## 关键细节

- RCACHE缓存机制位于IOVA层：IOVA的分配/释放走缓存池以降低开销 ^[inferred]（本来源仅提及名称，细节待补）
- 抽象层的收益在虚拟化场景放大：VMM只需面对统一IOMMU API即可管理任意平台的设备直通，见[[concepts/linux-device-passthrough]]
- Group/Domain模型同样定义在统一抽象之上，与具体硬件无关，见[[concepts/iommu-group-domain-isolation]]

## 未解问题

- SMMUv3的命令队列、event queue等具体机制？
- SVA由哪个SMMU版本开始支持？与Intel的Scalable IOV（S-IOV）的关系？
- RCACHE（IOVA per-CPU缓存）的回收与批量归还策略？

## 来源

- `raw/sources/Linux 操作系统/Linux 设备驱动管理/Linux IOMMU/Linux IOMMU、SMMU(ARM)技术图解.md` — 内核IOMMU框架分层、多厂商抽象、SMMU位置、SVA
- `raw/sources/Linux 操作系统/Linux 设备驱动管理/Linux IOMMU/Linux SMMU的IO Bypass.md` — STE Bypass 机制（不经 S1/S2、不查 IOTLB、不查权限）、bypass 与 BIOS 关闭的区别、内核控制参数、三模式对比
