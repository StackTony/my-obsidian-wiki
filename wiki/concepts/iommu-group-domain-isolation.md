---
title: IOMMU Group与Domain：DMA隔离模型
category: concepts
tags: [linux, IOMMU, VFIO, 隔离, 虚拟化]
aliases: [IOMMU Group, IOMMU Domain, VFIO Group, VFIO Container, BDF, Source Identifier]
relationships:
  - target: "[[summaries/linux-iommu-deep-dive]]"
    type: derived_from
  - target: "[[concepts/linux-device-passthrough]]"
    type: related_to
  - target: "[[concepts/linux-iommu-subsystem]]"
    type: related_to
  - target: "[[concepts/vm-address-translation-chain]]"
    type: related_to
source_dir: Linux 操作系统/Linux 设备驱动管理
source_files: [Linux IOMMU、SMMU(ARM)技术图解.md]
summary: IOMMU Group是DMA隔离最小硬件单元：同组设备共享domain页表PGD，必须整体直通给同一VM。PCIe TLP的BDF标记区分每设备DMA请求；PCIe-PCI桥下游设备共享Source Identifier被迫同组。VFIO Container聚合多个Group。
provenance:
  extracted: 0.63
  inferred: 0.32
  ambiguous: 0.05
base_confidence: 0.44
lifecycle: draft
lifecycle_changed: 2026-11-10
tier: supporting
created: 2026-11-10
updated: 2026-11-10
---

# IOMMU Group与Domain：DMA隔离模型

IOMMU的隔离能力不是以单个设备为粒度，而是以**Group**为粒度。Group是IOMMU能够进行DMA隔离的最小硬件单元，由物理平台的硬件拓扑结构决定——一个group内可能只有一个设备，也可能有多个设备。理解Group/Domain模型是配置设备直通（见[[concepts/linux-device-passthrough]]）的前提：直通时的分配粒度是group而非device。

## 核心观点

### Group与Domain的结构关系

- 一个 `struct iommu_group` 下可以对应一个或多个硬件设备
- 相同IOMMU Group的设备指向相同的IOMMU Domain，**每个Domain分配一份页表PGD**
- 一个 `struct iommu_domain` 里可以有多个iommu_group；每个group通过iommu_domain最终找到dmar_domain（Intel侧的domain实现）进行地址转换
- 同一个Group内的设备可以互相访问彼此的IOMMU映射

结构语义：Group是**隔离**粒度（同组设备无法分开），Domain是**地址空间**粒度（一份页表、一段映射范围）；一group必属一domain，多group可共享一domain ^[inferred]。设备→group→domain→页表 是IOMMU查找路径的骨架，与[[summaries/linux-iommu-deep-dive]]中Root Table→Context Table→Domain的硬件索引结构上下衔接。

### BDF：PCIe每设备标记

为什么PCIe能把隔离做到设备级：

- PCIe协议在TLP上增强：**每个外设发出的DMA请求都打上与该设备关联的、具有唯一性的flag，即设备的BDF号**（Bus/Device/Function）
- 通过BDF号可以索引到这个设备的IOVA转换表——每设备一份映射，隔离才有物理载体
- 早期PCI协议无法实现：PCI设备通过仲裁机制独占总线，同一时间只有一个PCI设备能使用PCI总线，因此DMA请求中**没有BDF号**——硬件层面无法区分请求来自哪个设备

### PCIe-PCI桥案例：为什么会出现多设备同组

PCIe-PCI桥下的两个设备发送DMA请求时，桥会为下游设备**代为生成Source Identifier**：Bus域为桥的总线号，device和func域为0。于是这两个设备命中**同一个Context Entry和同一份页表**——它们不能分别给两个虚机使用，天然属于同一个Group。旧协议设备的"匿名性"顺着桥的拓扑向上传染 ^[inferred]。

### Group的直通铁律

设备直通时，一个group里的设备必须**都**直通给一个虚拟机：

- 不能让一个group里的多个device分别从属于2个不同的VM
- 也不允许部分device在host上而另一部分分配给guest
- 否则一个guest中的设备可以利用DMA攻击获取另外一个guest里的数据——物理上做不到DMA隔离

### VFIO的Group与Container

- **Group**：如上，DMA隔离最小硬件单元
- **Container**：对虚机，可简单理解为一个VM Domain的物理内存空间；对用户态驱动，Container是**多个Group的集合**
- VFIO以Group为分配单元、以Container为地址空间句柄向用户态暴露IOMMU能力 ^[inferred]

### VFIO_IOMMU_MAP_DMA：建立映射的完整流程

1. 用户态先 `mmap` 映射1MB虚拟空间得到vaddr——物理地址对用户态不可见，只能经虚拟地址访问
2. ioctl `VFIO_IOMMU_MAP_DMA`，参数含iova与vaddr：iova是设备发起DMA时要访问的地址（IOMMU映射前的地址），vaddr是mmap地址
3. 为vaddr找到物理页并**pin住**——设备DMA是异步的、随时可能发生，物理页面不能被交换出去
4. 找到Group对应的Context Entry，建立页表项把iova映射到pin住的物理页的物理地址——用户态程序全程不见物理地址

示例：IOVA 0x0~0x100000 映射DRAM 0x10000000~0x10100000，size 1MB（原文排版残损，区间按size推定） ^[ambiguous]。一句话概述：`VFIO_IOMMU_MAP_DMA` 就是将iova通过IOMMU映射到vaddr对应的物理地址上去。

## 关键细节

- Context Entry是group→页表路径上的硬件锚点：Intel VT-d按Bus索引Root Table、按Device/Function索引Context Table，两维度合起来正是BDF（详见[[summaries/linux-iommu-deep-dive]]）
- pin页面是VFIO映射与普通mmap的本质区别：设备DMA没有缺页机制，页必须在物理内存中常驻 ^[inferred]
- 虚机透传场景下，VMM把HVA作为vaddr传入，从而保证EPT与IOMMU两条映射路径汇于同一HPA——推理链见[[concepts/vm-address-translation-chain]]

## 未解问题

- 内核如何从PCIe拓扑/ACPI表（DMAR、IORT）推导group边界？
- VFIO还有device层抽象（group之下的细粒度）？本来源仅提及Group与Container
- 同一domain内多group共享页表时，组间隔离如何退化？^[inferred]

## 来源

- `raw/sources/Linux 操作系统/Linux 设备驱动管理/Linux IOMMU、SMMU(ARM)技术图解.md` — Group/Domain关系、BDF标记、PCIe-PCI桥案例、VFIO Group/Container、VFIO_IOMMU_MAP_DMA流程
