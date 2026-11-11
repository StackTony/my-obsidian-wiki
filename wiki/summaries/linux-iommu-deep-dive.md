---
title: Linux x86-64 IOMMU详解（六部曲）
category: summaries
tags: [linux, IOMMU, DMA, VT-d, SWIOTLB, 虚拟化]
aliases: [IOMMU详解, IOMMU六部曲, Intel IOMMU系列, SWIOTLB原理]
relationships:
  - target: "[[concepts/linux-device-passthrough]]"
    type: extends
  - target: "[[skills/swiotlb-troubleshooting]]"
    type: related_to
  - target: "[[concepts/virtual-memory-and-paging]]"
    type: derived_from
  - target: "[[summaries/pci-bar-dma-space]]"
    type: related_to
  - target: "[[concepts/linux-dma-mapping]]"
    type: related_to
  - target: "[[concepts/linux-iommu-subsystem]]"
    type: related_to
  - target: "[[concepts/iommu-group-domain-isolation]]"
    type: related_to
source_dir: Linux 操作系统/Linux 驱动管理/Linux IOMMU
source_files:
  - Linux x86-64 IOMMU详解（1）——IOMMU简介.md
  - Linux x86-64 IOMMU详解（2）——SWIOTLB（软件IOMMU）.md
  - Linux x86-64 IOMMU详解（3）——Intel IOMMU（硬件IOMMU）的功能与基本原理.md
  - Linux x86-64 IOMMU详解（4）——启用Intel IOMMU的配置_bios iommu.md
  - Linux x86-64 IOMMU详解（5）——Intel IOMMU初始化流程_noiommu.md
  - Linux x86-64 IOMMU详解（6）——Intel IOMMU参与下的DMA Coherent Mapping.md
  - "Linux 操作系统/Linux 驱动管理/Linux IOMMU/Linux IOMMU、SMMU(ARM)技术图解.md"
summary: IOMMU是DMA地址翻译环节：SWIOTLB用memcpy做bounce（软件），Intel VT-d用I/O页表重映射（硬件）。两者不可共存，Intel IOMMU初始化后释放SWIOTLB buffer。适用Linux 5.5.4/x86-64。
provenance:
  extracted: 0.72
  inferred: 0.24
  ambiguous: 0.04
base_confidence: 0.78
lifecycle: draft
lifecycle_changed: 2026-11-10
tier: supporting
created: 2026-11-10
updated: 2026-11-10
---

# Linux x86-64 IOMMU详解（六部曲）

IOMMU（Input/Output Memory Management Unit）是DMA过程中的地址翻译环节，功能与CPU侧MMU类似，但面向设备DMA而非CPU访存。本系列系统梳理了IOMMU的软件实现（SWIOTLB）和硬件实现（Intel VT-d），以及二者在内核初始化过程中的竞争与淘汰关系。适用环境：Linux 5.5.4 / Intel x86-64 / BIOS支持Intel IOMMU。

Intel IOMMU只是多厂商实现之一（另有AMD IOMMU、ARM SMMU）——Linux内核以统一IOMMU抽象层向设备驱动提供结构、隐藏底层架构差异，框架分层与SMMU/SVA见[[concepts/linux-iommu-subsystem]]；跨厂商通用的Group/Domain隔离模型见[[concepts/iommu-group-domain-isolation]]。

## 核心观点

### IOMMU的动机（第1篇）

IOMMU将设备地址（总线地址/DMA地址）翻译为内存物理地址，解决两大问题：
1. **安全隔离**——设备无法直接访问物理地址，增加DMA攻击难度
2. **寻址位宽限制**——32位设备只能寻址[0, 4GB)，而现代系统内存常大于4GB。IOMMU在低地址分配low buffer让设备可达，再与high buffer之间做sync（bounce）

这与[[concepts/virtual-memory-and-paging]]中MMU将VA翻译为PA的机制原理一致，只是翻译对象从CPU变为设备。^[inferred]

### SWIOTLB——软件IOMMU（第2篇）

SWIOTLB底层用 `memcpy()` 实现bounce/sync，需要CPU参与，效率低于硬件IOMMU。关键机制：

- **SWIOTLB Buffer**：启动时用memblock分配器从**低地址内存**预留连续物理内存，默认64MB，按2KB粒度切分为slab（非标准4KB页）。默认slab数 = 64MB / 2KB = 32768
- **io_tlb_list数组**：`io_tlb_list[i]` 代表从第i个slab开始有多少连续空闲slab，上限 `IO_TLB_SEGSIZE=128`（由x86 PCIe规范决定每次DMA有效数据≤128字节）
- **单次映射上限**：128 × 2KB = 256KB；超过此限制需用DMA Coherent Mapping
- **触发条件**：仅DMA Streaming Mapping可能触发（Linux 4.0+）；DMA Coherent Mapping与SWIOTLB无关
- **函数调用路径**：`dma_map_single`/`dma_map_sg` → `dma_direct_map_page` → `swiotlb_map` → `swiotlb_tbl_map_single` → `swiotlb_bounce` → `memcpy`

**map函数的三种行为**：设备能直接寻址→不映射直接返回物理地址；不能直接寻址→在SWIOTLB Buffer申请low buffer做bounce；`swiotlb=force`→即使设备能寻址也强制映射（降低效率，不推荐）

实际排查SWIOTLB问题的操作步骤见[[skills/swiotlb-troubleshooting]]。

### Intel IOMMU——硬件IOMMU（第3篇）

Intel IOMMU全称Intel VT-d（Virtualization Technology for Direct I/O），核心功能是**重映射（Remapping）**——在虚拟化场景下对I/O操作（DMA和中断）进行重映射。解决设备寻址能力有限只是其附带功能。

**DMA重映射**：Intel IOMMU截获设备DMA请求，将虚拟机物理地址（GPA）映射为宿主机物理地址（HPA）。设备对GPA发起DMA，IOMMU翻译为HPA完成传输。

**中断重映射**：截获设备中断请求，重定向到设备所连接虚拟机的CPU，通过中断重映射表（IRT）索引中断服务程序。

**I/O页表机制**（类比虚拟内存多级页表）：
- 顶级：Root Table（按Bus索引）→ Context Table（按Device/Function索引）→ 映射到不同Domain
- 次级：Second-Level Page Table，真正的地址翻译过程，与MMU页表原理完全一致

不同设备的Context Table可指向同一Domain——一台虚拟机连接多个设备。Domain作为页表/地址空间单元与Group（隔离单元）的完整关系见[[concepts/iommu-group-domain-isolation]]。

### 启用配置（第4篇）

| 配置层 | SWIOTLB | Intel IOMMU |
|--------|---------|-------------|
| BIOS | 不需要 | 启用VT和VT-d |
| .config | `CONFIG_SWIOTLB=y` | `CONFIG_INTEL_IOMMU=y`（必要非充分） |
| 启动参数 | `iommu=soft intel_iommu=off`（推荐） | `iommu=force intel_iommu=on` |
| 强制 | `swiotlb=force`（不推荐） | — |
| 确认 | dmesg grep swiotlb | `dmesg \| grep "DMAR"` |

### 初始化流程——二虎相争（第5篇）

内核IOMMU初始化的完整流程揭示了SWIOTLB与Intel IOMMU不可共存的原因：

1. **pci_iommu_alloc()**（early init阶段）遍历IOMMU Table，调用各detect函数：
   - `pci_swiotlb_detect_4gb()`：物理内存 > 4GB时 `swiotlb=1`，调用 `pci_swiotlb_init()` → `swiotlb_init()` 初始化SWIOTLB
   - `detect_intel_iommu()`：返回1，设置 `x86_init.iommu.iommu_init = intel_iommu_init`，但无early_init函数

2. **pci_iommu_init()**（late init阶段）调用 `intel_iommu_init()`：
   - 初始化Intel IOMMU数据结构（Root Entry、Domain等）
   - **将全局变量 `swiotlb` 置为0**——条件：`!has_untrusted_dev() || intel_no_bounce`
   - `intel_iommu=nobounce` 可设置 `intel_no_bounce=1` 禁用bounce机制

3. **pci_swiotlb_late_init()**：检测到 `swiotlb==0`，调用 `swiotlb_exit()` 释放SWIOTLB Buffer和管理数据结构

**关键时序**：SWIOTLB先被初始化（因内存>4GB），但Intel IOMMU初始化后将swiotlb置0，随后late_init阶段SWIOTLB buffer被释放——"一山难容二虎"。

### DMA Coherent Mapping流程（第6篇）

Intel IOMMU启用后，所有DMA经由 `intel_dma_ops` 结构体。`intel_alloc_coherent()` 根据 `iommu_need_mapping()` 分流：

- **返回false**（设备dma_mask >= 1GB）→ `dma_direct_alloc()`：传统DMA Coherent Mapping流程，不经过IOMMU
- **返回true**（设备需映射）→ `__intel_map_single()`：IOMMU映射流程

**IOMMU映射的核心概念**：
- **IOVA（I/O Virtual Address）**：设备DMA访问的"虚拟地址"，IOMMU将IOVA翻译为PA。启用Intel IOMMU时，DMA Address的表现形式就是IOVA
- **IOMMU页表**：4级页表，与MMU页表独立但原理相同，将IOVA映射为PA
- `__intel_map_single()` 完成：(1) `intel_alloc_iova()` 从slab分配器申请struct iova (2) `domain_pfn_mapping()` → `__domain_mapping()` 写IOMMU页表PTE（`cmpxchg64_local` 原子设置）

DMA映射类型的系统化分析见[[concepts/linux-dma-mapping]]。

## 关键细节

### SWIOTLB slab查找算法

内核从上一次查找位置开始，沿下标递增方向扫描 `io_tlb_list`，找到 `io_tlb_list[k] >= n`（n=所需slab数）的区段。不满足时直接跳到 `k + io_tlb_list[k] + 1`（跳过已知不满足的区段）。遍历完数组回到起始位置仍未找到则拒绝DMA请求。

### IO_TLB_SEGSIZE的工程含义

IO_TLB_SEGSIZE=128由x86 PCIe规范决定（每次DMA有效数据≤128字节），限制了单次DMA Streaming Mapping最大申请256KB。超过此限制的场景应使用DMA Coherent Mapping——这正是设计上将两种映射方式分工的依据。^[inferred]

### iommu_need_mapping的判断逻辑

设备是否需要IOMMU映射取决于：(1) 设备的 `archdata.iommu` 属性（identity mapping）(2) 设备的 `dma_mask` 寻址能力。关键判断：`dma_mask >= dma_direct_get_required_mask(dev)` 时不需要映射——与SWIOTLB map的触发条件（设备无法直接寻址）逻辑相似。

### noiommu路径

启动参数未启用任何IOMMU时，`no_iommu=1`，`pci_swiotlb_detect_4gb()` 的 `!no_iommu` 条件为false，不会初始化SWIOTLB。此时设备DMA直接使用物理地址，32位设备在高内存场景下将无法正常DMA。^[inferred]

## 未解问题

- IOMMU页表的large page支持（`hardware_largepage_caps`）在什么条件下启用？
- `intel_no_bounce` 禁用bounce后，不可信设备的DMA如何处理？^[inferred]
- 中断重映射表（IRT）的具体结构与MSI/MSI-X消息的关系？
- IOMMU的invalidation队列（QI）机制细节？

## 来源

- `raw/sources/Linux 操作系统/Linux 驱动管理/Linux IOMMU/Linux x86-64 IOMMU详解（1）——IOMMU简介.md` — IOMMU动机、bounce/sync概念
- `raw/sources/Linux 操作系统/Linux 驱动管理/Linux IOMMU/Linux x86-64 IOMMU详解（2）——SWIOTLB（软件IOMMU）.md` — SWIOTLB原理、io_tlb_list管理、slab查找算法、函数调用树
- `raw/sources/Linux 操作系统/Linux 驱动管理/Linux IOMMU/Linux x86-64 IOMMU详解（3）——Intel IOMMU（硬件IOMMU）的功能与基本原理.md` — VT-d重映射、DMA/中断重映射、I/O页表（Root/Context/Second-Level）
- `raw/sources/Linux 操作系统/Linux 驱动管理/Linux IOMMU/Linux x86-64 IOMMU详解（4）——启用Intel IOMMU的配置_bios iommu.md` — BIOS/.config/启动参数配置
- `raw/sources/Linux 操作系统/Linux 驱动管理/Linux IOMMU/Linux x86-64 IOMMU详解（5）——Intel IOMMU初始化流程_noiommu.md` — pci_iommu_alloc/init调用树、二虎相争时序、swiotlb_exit释放
- `raw/sources/Linux 操作系统/Linux 驱动管理/Linux IOMMU/Linux x86-64 IOMMU详解（6）——Intel IOMMU参与下的DMA Coherent Mapping.md` — intel_dma_ops、iommu_need_mapping分流、IOVA/IOMMU页表、__intel_map_single
- `raw/sources/Linux 操作系统/Linux 驱动管理/Linux IOMMU/Linux IOMMU、SMMU(ARM)技术图解.md` — 多厂商IOMMU统一抽象层背景（本页引言补充）
