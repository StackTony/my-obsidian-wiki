---
title: Linux IOMMU、SMMU(ARM)技术图解
category: summaries
tags: [linux, IOMMU, SMMU, 虚拟化, ARM]
aliases: [IOMMU/SMMU图解, SMMU技术图解, IOMMU图解]
relationships:
  - target: "[[summaries/linux-iommu-deep-dive]]"
    type: extends
  - target: "[[concepts/linux-iommu-subsystem]]"
    type: related_to
  - target: "[[concepts/iommu-group-domain-isolation]]"
    type: related_to
  - target: "[[concepts/vm-address-translation-chain]]"
    type: related_to
  - target: "[[concepts/linux-device-passthrough]]"
    type: related_to
source_dir: Linux 操作系统/Linux 设备驱动管理/Linux IOMMU

source_files: [Linux IOMMU、SMMU(ARM)技术图解.md]
summary: 知乎图解文蒸馏：IOMMU与MMU对偶、内核IOMMU框架五层、ARM SMMU、SVA共享页表、Group/Domain隔离、VFIO Group/Container与MAP_DMA流程、GPA/HVA/HPA地址链与设备透传映射一致性(HPA1==HPA2)。
provenance:
  extracted: 0.68
  inferred: 0.27
  ambiguous: 0.05
base_confidence: 0.44
lifecycle: draft
lifecycle_changed: 2026-11-10
tier: supporting
created: 2026-11-10
updated: 2026-11-10
---

# Linux IOMMU、SMMU(ARM)技术图解

一篇图解风格的综述文章，从IOMMU与MMU的对偶关系出发，覆盖内核IOMMU框架分层、ARM SMMU、SVA、Group/Domain隔离模型、VFIO、虚拟化地址转换链（GVA/GPA/HVA/HPA）直到设备透通的映射一致性。与[[summaries/linux-iommu-deep-dive]]（x86 VT-d实现细节）互补：该系列讲"一种硬件怎么做"，本文讲"内核怎么统一抽象多种硬件、隔离模型与虚拟化全景"。

## 核心观点

### IOMMU与MMU的对偶关系

- MMU将CPU虚拟地址转换为内存物理地址；IOMMU将**设备地址（总线地址）**转换为内存物理地址
- 只要涉及IOMMU的访问路径就没有CPU的事：IOMMU的master只能是设备，slave可以是Host Memory，或经BAR映射的设备Memory总线地址（BAR概念见[[summaries/pci-bar-dma-space]]）
- 引入IOMMU的三个背景：32位老设备寻址能力有限，够不到高于4GB的内存；传统DMA要求连续物理内存，大块连续内存极难分配；设备直接访问物理地址存在DMA攻击风险

**没有IOMMU之前的bounce buffers方案**：在物理内存底端（32位设备可达区域）设缓冲区，设备访问高端内存时由OS先把数据拷贝进/出bounce buffer。数据拷贝极大降低性能——这正是SWIOTLB的思想原型，详见[[skills/swiotlb-troubleshooting]]与[[summaries/linux-iommu-deep-dive]]。

### IOMMU的三大作用

在虚拟化出现之前，IOMMU的主要功能就是把IOVA转换成HPA：

1. 让只有32位DMA能力的设备访问4GB以上地址空间
2. **把多个分散的DMA操作聚合成一个连续的DMA操作**（分散物理页映射为连续IOVA区间，设备看到的是连续地址）——见[[concepts/linux-dma-mapping]]
3. 屏蔽物理地址，起保护作用

### 内核IOMMU框架分层

Linux内核将IOMMU分为五层（详见[[concepts/linux-iommu-subsystem]]）：

- **DMA-MAP层**：对其他驱动提供DMA MAP/UNMAP的API接口
- **IOVA层**：IOVA的分配与释放，提供RCACHE缓存机制
- **IO页表层**：对IO设备页表的操作
- **SMMU/IOMMU驱动层**：驱动初始化，提供IOMMU对应的回调函数
- **其它API接口**：对VFIO等提供接口

### SMMU与IOMMU抽象

- 硬件上能完成设备IOVA→PA转换的有Intel IOMMU、AMD IOMMU、ARM SMMU等多种实现
- 这些不同硬件架构不会各自作为独立子系统——Linux内核**抽象出一层统一的iommu层**，向各外部设备驱动提供结构，隐藏底层架构差异
- SVA（Share Virtual Address）：CPU和Device**共享同一份页表**，是IOMMU能力的延伸方向 ^[inferred]
- SMMU位于SoC中设备与内存之间，是master侧的地址翻译单元；其软硬件交互过程原文以图为主，文字未展开 ^[ambiguous]

### Group与Domain

- 相同IOMMU Group的设备指向相同的IOMMU Domain，每个Domain分配一份页表PGD
- 同一个Group内的设备可以互相访问彼此的IOMMU映射
- 一个 `struct iommu_group` 对应一个或多个硬件设备；一个 `struct iommu_domain` 可包含多个group；每个group经domain最终找到dmar_domain进行转换
- Group是DMA隔离的最小硬件单元——完整隔离模型与PCIe-PCI桥案例见[[concepts/iommu-group-domain-isolation]]

### IOMMU与虚拟化：从转换到"转换+隔离"

数据中心大规模使用虚拟化后，IOMMU的主要作用从单一转换变成**转换加隔离**：

- SR-IOV场景下，IOMMU隔离避免直通给虚拟机A的外设DMA到虚拟机B的内存
- 这一能力的根基是PCIe协议在TLP上的增强：**每个外设发出的DMA请求都带与设备关联的唯一flag，即BDF号**，通过BDF可索引到该设备的IOVA转换表
- 早期PCI协议做不到——PCI设备通过仲裁机制独占总线（同一时间只有一个PCI设备使用总线），DMA请求中根本没有BDF号

**无IOMMU时无法透传的两个原因**：设备必须访问真实物理地址HPA，而虚机可见的是GPA；若让虚机直接填HPA，等于虚机可直接访问物理地址，有安全隐患。因此无IOMMU时设备直接访问由VMM接管，不向虚机暴露HPA。

**有IOMMU时**：虚机可将GPA直接写入设备；设备DMA时请求地址GPA由IOMMU硬件自动转换为HPA。映射关系由VMM维护，HPA对虚机不可见——安全问题与透传兼得。地址链详见[[concepts/vm-address-translation-chain]]。

### VFIO的Group与Container

- **Group**：IOMMU能进行DMA隔离的最小硬件单元，内容取决于物理平台的IOMMU拓扑结构。直通时一个group里的设备必须**整体**直通给同一个VM——不能拆给两个VM，也不能部分留Host、部分给Guest，否则Guest中的设备可用DMA攻击获取另一个Guest的数据，物理上无法做到DMA隔离
- **Container**：对虚机可理解为VM Domain的物理内存空间；对用户态驱动则是多个Group的集合
- 经典案例：PCIe-PCI桥下的两个设备发出DMA时，桥会为它们生成Source Identifier（bus=桥的总线号，device/func=0）——两设备命中同一个Context Entry和同一份页表，因此属于同一个Group，不能分别给两个虚机

### VFIO_IOMMU_MAP_DMA映射流程

用户态驱动建立IOMMU映射的四步：

1. `mmap` 映射1MB虚拟空间（vaddr）——物理地址对用户态不可见，只能经虚拟地址访问物理空间
2. ioctl `VFIO_IOMMU_MAP_DMA`，传入iova与vaddr：iova是设备DMA请求要访问的地址（映射前），vaddr是mmap所得地址
3. 命令为vaddr找到物理页并**pin住**——设备DMA是异步的，随时可能发生，物理页面不能被交换出去
4. 找到Group对应的Context Entry建立页表项，把iova映射到pin住的物理页——对用户态程序完全屏蔽物理地址

示例：IOVA 0x0~0x100000 映射 DRAM 0x10000000~0x10100000，size 1MB（原文此处排版残损，区间为按size推定） ^[ambiguous]。一句话：`VFIO_IOMMU_MAP_DMA` 就是把iova经IOMMU映射到vaddr对应的物理地址上。

### 虚机GPA/HVA/HPA与透传一致性

- 虚机页表完成GVA→GPA；注意虚机各级页表本身也存在HPA中，CR3及页表项里装的都是GPA，**访问页表时也要借助EPT**
- EPT完成GPA→HPA，一层层页表映射，硬件自动完成
- HVA的两个作用：Qemu按虚机RAM大小mmap出HVA，经 `KVM_SET_USER_MEMORY_REGION`（guest_phys_addr + userspace_addr）让KVM建EPT表；vm_exit后VMM处理异常需要访问虚机GPA对应的HPA，而VMM只能经HVA访问，GPA↔HVA关系由Qemu维护
- **透传一致性**：设备透传后，GPA经EPT映射为HPA1，经IOMMU映射为HPA2，**HPA1必须等于HPA2**透传才有意义。VMM把HVA作为vaddr传给 `VFIO_IOMMU_MAP_DMA`，IOMMU将GPA映射到HVA对应的HPA1，即HPA2==HPA1
- IOMMU映射在虚机启动时建立，覆盖整个GPA地址范围；虚机HPA对应的物理页都不会被交换出去

## 未解问题

- 原文多节（SMMU软硬件交互、SVA、SMMU位置）以外部图为主、正文为空，图的语义未能蒸馏——需要后续来源补充
- SVA的具体实现机制（页表如何共享、缺页如何处理）？
- SMMU与Intel VT-d在页表结构上的具体差异？
- 中断重映射（IRT）与BDF索引的关系细节？

## 来源

- `raw/sources/Linux 操作系统/Linux 设备驱动管理/Linux IOMMU/Linux IOMMU、SMMU(ARM)技术图解.md` — 知乎图解文（原文链接 https://zhuanlan.zhihu.com/p/1940345916113548209 ），IOMMU/SMMU/VFIO/虚拟化地址转换全景
