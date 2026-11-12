---
title: Linux设备直通：IOMMU+SR-IOV+VFIO
category: concepts
tags: [linux, 虚拟化, 直通, IOMMU, SR-IOV, VFIO]
aliases: [设备直通, IOMMU虚拟化, VFIO, SR-IOV, Intel VT-d]
relationships:
  - target: "[[concepts/linux-virtio-architecture]]"
    type: related_to
  - target: "[[concepts/linux-namespace-cgroups]]"
    type: uses
  - target: "[[summaries/linux-iommu-deep-dive]]"
    type: extends
  - target: "[[concepts/linux-dma-mapping]]"
    type: uses
  - target: "[[summaries/pci-bar-dma-space]]"
    type: related_to
  - target: "[[concepts/iommu-group-domain-isolation]]"
    type: uses
  - target: "[[concepts/vm-address-translation-chain]]"
    type: related_to
  - target: "[[concepts/linux-iommu-subsystem]]"
    type: related_to
source_dir: Linux 虚拟化/IO虚拟化
source_files:
  - "设备直通 iommu+sriov、vfio.md"
  - "Linux 操作系统/Linux 内核 IO 栈/Linux IOMMU/Linux x86-64 IOMMU详解（1）——IOMMU简介.md"
  - "Linux 操作系统/Linux 内核 IO 栈/Linux IOMMU/Linux x86-64 IOMMU详解（3）——Intel IOMMU（硬件IOMMU）的功能与基本原理.md"
  - "Linux 操作系统/Linux 内核 IO 栈/Linux IOMMU/Linux x86-64 IOMMU详解（5）——Intel IOMMU初始化流程_noiommu.md"
  - "Linux 操作系统/Linux 内核 IO 栈/Linux IOMMU/Linux IOMMU、SMMU(ARM)技术图解.md"
summary: 设备直通将物理设备直接分配给VM使用，跳过软件模拟层。IOMMU提供DMA地址翻译和安全隔离（以Group为隔离粒度），SR-IOV虚拟出多个VF，VFIO是用户态驱动框架。x86平台Intel VT-d通过I/O页表实现DMA/中断重映射。
provenance:
  extracted: 0.60
  inferred: 0.30
  ambiguous: 0.10
base_confidence: 0.78
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: supporting
created: 2026-06-01
updated: 2026-11-10
---

# Linux设备直通：IOMMU+SR-IOV+VFIO

设备直通(Passthrough)让物理设备直接供VM使用，几乎零开销——数据面在VM与硬件间直通，无需Host软件介入。这是性能最高的虚拟化IO方式，但牺牲了灵活性和可管理性^[inferred]。

## 核心观点

### 三大技术组件

**IOMMU（Input-Output Memory Management Unit）**
- DMA地址翻译：将Guest物理地址(GPA)翻译为Host物理地址(HPA)，使设备DMA能正确访问VM内存
- 安全隔离：限制设备DMA访问范围，防止恶意设备越界读写^[inferred]
- 类似CPU侧的MMU，但面向设备DMA而非CPU访存

### x86平台硬件IOMMU：Intel VT-d

Intel x86平台的硬件IOMMU全称**Intel VT-d**（Virtualization Technology for Direct I/O），核心功能是**重映射（Remapping）**——在虚拟化场景下截获设备的DMA和中断请求，重定向到设备所连接的虚拟机。解决设备寻址能力有限只是其附带功能。

**DMA重映射**：Intel IOMMU截获设备DMA请求，将GPA映射为HPA。设备向GPA发起DMA，IOMMU翻译为HPA完成传输。这一过程对设备透明——设备只知道自己连接了一台"机器"。

**中断重映射**：截获设备中断请求，重定向到虚拟机所占有的CPU，通过中断重映射表（IRT）索引中断服务程序。

**I/O页表机制**（类比[[concepts/virtual-memory-and-paging]]的多级页表）：
- 顶级：Root Table（按Bus索引）→ Context Table（按Device/Function索引）→ 映射到不同Domain
- 次级：Second-Level Page Table：真正的GPA→HPA翻译，与MMU页表原理一致
- 不同设备的Context Table可指向同一Domain——多设备归属同一虚拟机

**为什么隔离能做到设备级**：PCIe协议在TLP上为每个外设的DMA请求打上与设备关联的唯一flag——设备的BDF号（Bus/Device/Function），IOMMU通过BDF索引到该设备的IOVA转换表。早期PCI协议做不到：PCI设备经仲裁机制独占总线（同一时间只有一个设备使用总线），DMA请求中没有BDF号，硬件无法区分请求来源。SR-IOV场景下"直通给VM-A的设备不会DMA到VM-B内存"正是以此TLP标记为物理基础。

**SWIOTLB与硬件IOMMU不可共存**：内核初始化时SWIOTLB可能先被初始化（物理内存>4GB触发），但Intel IOMMU初始化后将全局变量 `swiotlb` 置0，随后late_init阶段 `swiotlb_exit()` 释放SWIOTLB Buffer。完整初始化时序与竞争分析详见[[summaries/linux-iommu-deep-dive]]。

DMA映射类型（Coherent vs Streaming）及IOVA/IOMMU页表的映射流程详见[[concepts/linux-dma-mapping]]。

**SR-IOV（Single Root I/O Virtualization）**
- 一个物理网卡(PF)虚拟出多个虚拟功能(VF)
- VF可直接分配给VM，每个VF有独立的配置空间和DMA引擎
- PF：使用VFIO方式将物理设备直通给VM，Host侧不再可见该设备
- VF：使用SR-IOV方式，先在Host侧虚拟出多个设备再分配给VM

**VFIO（Virtual Function I/O）**
- Linux内核用户态驱动框架
- 提供安全的设备访问接口，配合IOMMU实现DMA隔离
- QEMU通过VFIO驱动将物理设备映射到VM的地址空间^[inferred]
- 两个核心抽象：**Group**（IOMMU能进行DMA隔离的最小硬件单元，由平台拓扑决定；组内设备必须整体直通给同一个VM，不能拆给两个VM或部分留Host——否则guest可经DMA攻击获取另一guest数据）；**Container**（对虚机=VM Domain的物理内存空间，对用户态驱动=多个Group的集合）
- 建立映射的核心命令 `VFIO_IOMMU_MAP_DMA`：把iova经IOMMU映射到vaddr对应的物理地址，映射的物理页pin住不可换出。Group/Domain模型与完整映射流程见[[concepts/iommu-group-domain-isolation]]

### 透通的映射一致性

设备透通后虚机配置DMA时直接填GPA：GPA经**EPT**映射为HPA1（虚机内存视角），经**IOMMU**映射为HPA2（设备DMA视角），**HPA1==HPA2是透通有意义的前提**。VMM把HVA作为vaddr传给 `VFIO_IOMMU_MAP_DMA`，使两条路径汇于同一物理页。GVA/GPA/HVA/HPA四层地址空间与完整推理链见[[concepts/vm-address-translation-chain]]。

### 直通 vs 半虚拟化(virtio)

| 维度 | 设备直通 | Virtio半虚拟化 |
|------|----------|---------------|
| 性能 | 最高（硬件直通） | 较高（共享内存+通知） |
| 灵活性 | 低（设备独占） | 高（软件模拟，可迁移） |
| 可迁移性 | 不可迁移 | 可热迁移 |
| 可扩展性 | 受限于物理设备数 | 可创建数百虚拟设备 |
| 设备共享 | SR-IOV VF方式 | virtio队列方式 |

vDPA架构试图融合两者优势——保留virtio标准接口的同时获得直通级性能。详见[[concepts/linux-virtio-architecture]]。

## 未解问题

- ~~IOMMU的2-stage翻译（GPA→IOVA→HPA）的具体实现细节？~~ 已由IOMMU六部曲系列补充：Intel VT-d通过Root/Context Table映射到Domain，Second-Level Page Table做GPA→HPA翻译，详见[[summaries/linux-iommu-deep-dive]]
- 中断重映射表（IRT）的具体结构与MSI/MSI-X消息的关系？^[inferred]
- ~~VFIO的group/container/device三层抽象设计？~~ 已由IOMMU、SMMU(ARM)图解来源补充：Group/Container语义与VFIO_IOMMU_MAP_DMA流程见[[concepts/iommu-group-domain-isolation]]
- VFIO是否还有group之下的device层抽象？^[inferred]
- SR-IOV VF数量上限与性能线性度关系？


## 延伸阅读

综合分析：[[synthesis/virtio-architecture-evolution]]

## 来源

- `raw/sources/Linux 虚拟化/IO虚拟化/设备直通 iommu+sriov、vfio.md` — PF/VF区别、IOMMU/VFIO概念
- `raw/sources/Linux 操作系统/Linux 内核 IO 栈/Linux IOMMU/Linux x86-64 IOMMU详解（1）——IOMMU简介.md` — IOMMU动机、DMA地址翻译、bounce/sync概念
- `raw/sources/Linux 操作系统/Linux 内核 IO 栈/Linux IOMMU/Linux x86-64 IOMMU详解（3）——Intel IOMMU（硬件IOMMU）的功能与基本原理.md` — VT-d重映射、DMA/中断重映射、I/O页表（Root/Context/Second-Level）
- `raw/sources/Linux 操作系统/Linux 内核 IO 栈/Linux IOMMU/Linux x86-64 IOMMU详解（5）——Intel IOMMU初始化流程_noiommu.md` — SWIOTLB与Intel IOMMU初始化竞争时序、swiotlb_exit释放
- `raw/sources/Linux 操作系统/Linux 内核 IO 栈/Linux IOMMU/Linux IOMMU、SMMU(ARM)技术图解.md` — BDF设备级隔离、PCIe TLP标记、VFIO Group/Container、透通映射一致性(HPA1==HPA2)