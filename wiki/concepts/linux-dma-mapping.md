---
title: Linux DMA映射类型：Coherent与Streaming
category: concepts
tags: [linux, DMA, 内核, IOMMU, 内存映射]
aliases: [DMA映射, DMA Coherent Mapping, DMA Streaming Mapping, IOVA, IOMMU页表]
relationships:
  - target: "[[summaries/linux-iommu-deep-dive]]"
    type: derived_from
  - target: "[[concepts/linux-device-passthrough]]"
    type: uses
  - target: "[[concepts/virtual-memory-and-paging]]"
    type: derived_from
  - target: "[[skills/swiotlb-troubleshooting]]"
    type: related_to
  - target: "[[concepts/linux-iommu-subsystem]]"
    type: related_to
source_dir: Linux 操作系统/Linux 设备驱动管理/Linux IOMMU
source_files:
  - Linux x86-64 IOMMU详解（2）——SWIOTLB（软件IOMMU）.md
  - Linux x86-64 IOMMU详解（6）——Intel IOMMU参与下的DMA Coherent Mapping.md
  - "Linux 操作系统/Linux 设备驱动管理/Linux IOMMU、SMMU(ARM)技术图解.md"
summary: Linux DMA映射两类：Coherent（一致性，长期映射，大buffer）和Streaming（流式，按需map/unmap，可触发SWIOTLB bounce）。Intel IOMMU启用后DMA地址为IOVA，经IOMMU页表翻译为PA；IOMMU还可把分散物理页聚合映射为连续IOVA。
provenance:
  extracted: 0.66
  inferred: 0.31
  ambiguous: 0.03
base_confidence: 0.78
lifecycle: draft
lifecycle_changed: 2026-11-10
tier: supporting
created: 2026-11-10
updated: 2026-11-10
---

# Linux DMA映射类型：Coherent与Streaming

Linux内核DMA子系统提供两种映射方式，对应不同的使用场景和性能特征。理解两者的区别是分析DMA路径（包括SWIOTLB bounce触发条件和IOMMU翻译流程）的基础。

## 核心观点

### 两种映射方式的分工

| 维度 | DMA Coherent Mapping | DMA Streaming Mapping |
|------|---------------------|----------------------|
| 生命周期 | 长期持有（alloc/free配对） | 按需map/unmap，单次传输 |
| 典型场景 | 大buffer、网卡环形缓冲区 | 单次IO请求的scatter-gather |
| 与SWIOTLB | **无关**（Linux 4.0+） | **可能触发bounce** |
| 单次上限 | 无256KB限制 | 256KB（128 slab × 2KB） |
| 缓存一致性 | 硬件保证coherent | 需显式sync（或由map函数处理） |

关键规则：**Linux 4.0及更高版本，只有DMA Streaming Mapping可能触发SWIOTLB机制，DMA Coherent Mapping与SWIOTLB没有任何联系。** Linux 4.0之前Coherent Mapping也会借助SWIOTLB，此后被移除。

### Streaming Mapping的map函数

map函数（`dma_map_single`、`dma_map_sg`等）的核心流程：
1. 设备提供位于高地址的原始页（high buffer），请求map
2. map函数根据设备寻址能力+启动参数决定行为：
   - 设备能直接寻址→不映射，直接返回物理地址作为DMA地址（x86中DMA地址=物理地址）
   - 设备不能直接寻址→在SWIOTLB Buffer申请low buffer，复制内容，返回low buffer地址作为DMA地址（触发bounce）
   - `swiotlb=force`→即使设备能寻址也强制映射

函数调用路径：`dma_map_single`/`dma_map_sg` → `dma_map_page_attrs` → `dma_direct_map_page` → `swiotlb_map` → `swiotlb_tbl_map_single` → `swiotlb_bounce` → `memcpy`

### IOVA——IOMMU启用后的DMA地址

启用Intel IOMMU后，DMA Address的表现形式变为**IOVA（I/O Virtual Address）**。IOMMU的作用是将IOVA翻译为PA（物理地址），与MMU将VA翻译为PA的机制完全类似。

- MMU：VA → PA（面向CPU访存）
- IOMMU：IOVA → PA（面向设备DMA）

IOMMU的三大作用：让只有32位DMA能力的设备访问4GB以上地址空间；**把多个分散的DMA操作聚合成一个连续的DMA操作**；屏蔽物理地址起保护作用。第二点正是scatter-gather的本质收益——分散的物理页可映射为连续的IOVA区间，设备面对一段连续DMA地址即可完成大块传输，无需大块连续物理内存，绕开了传统DMA对物理内存连续性的苛刻要求。^[inferred] 内核侧的分层框架（DMA-MAP层/IOVA层/IO页表层/驱动层）见[[concepts/linux-iommu-subsystem]]。

IOVA由 `intel_alloc_iova()` 从slab分配器申请（`struct iova`），分配后建立IOVA到PA的页表映射。设备向IOVA发起DMA，IOMMU根据页表翻译为DMA Buffer的物理地址。

### IOMMU页表

Intel IOMMU维护专用的IOMMU页表，与MMU页表独立但原理相同，默认4级。地址翻译流程（基于4K标准页）与MMU多级页表一致。

DMA重映射的I/O页表结构：
- **Root Table**（按Bus索引）→ **Context Table**（按Device/Function索引）→ 映射到不同Domain
- **Second-Level Page Table**：真正的IOVA→PA翻译，从次级页表开始与MMU页表完全相同

不同设备的Context Table可指向同一Domain，实现多设备归属同一虚拟机。

## 关键细节

### Coherent Mapping在Intel IOMMU下的分流

`intel_alloc_coherent()` 根据 `iommu_need_mapping()` 分流：
- **false**（设备dma_mask >= ~1GB）→ `dma_direct_alloc()`：传统流程，不经过IOMMU翻译
- **true**（设备需映射）→ `__intel_map_single()`：申请IOVA + 建立IOMMU页表映射

`iommu_need_mapping()` 的判断依据：(1) 设备的 `archdata.iommu` 属性（identity mapping）(2) 设备的 `dma_mask` 寻址能力。关键判断 `dma_mask >= dma_direct_get_required_mask(dev)` 时不需要映射——与SWIOTLB map的触发条件逻辑相似。

### __intel_map_single的映射过程

1. `intel_alloc_iova()` → `alloc_iova_fast()` → `alloc_iova()` → `kmem_cache_alloc()` 从slab分配器分配 `struct iova`
2. `domain_pfn_mapping()` → `__domain_mapping()` 遍历IOMMU页表各级，用 `cmpxchg64_local(&pte->val, 0ULL, pteval)` 原子设置PTE，建立IOVA→PA映射
3. 返回IOVA作为DMA地址给设备

设备后续向IOVA发起DMA读写时，Intel IOMMU根据已建立的页表映射翻译为物理地址，完成数据传输。

### intel_dma_ops结构体

Intel IOMMU通过实例化 `struct dma_map_ops` 的函数指针实现DMA操作：

```c
static const struct dma_map_ops intel_dma_ops = {
    .alloc = intel_alloc_coherent,
    .free = intel_free_coherent,
    .map_sg = intel_map_sg,
    .unmap_sg = intel_unmap_sg,
    .map_page = intel_map_page,
    .unmap_page = intel_unmap_page,
    ...
};
```

注意：`intel_dma_ops` 未实例化任何sync函数——因为IOMMU映射的buffer对设备和CPU都是coherent的，无需额外sync操作。^[inferred]

### Streaming Mapping与SWIOTLB的256KB限制

SWIOTLB的 `IO_TLB_SEGSIZE=128` 限制了单次DMA Streaming Mapping最大申请 128 × 2KB = 256KB。超过此限制的DMA请求应使用DMA Coherent Mapping。这是两种映射方式分工的工程依据——Coherent Mapping适用于较大内存申请，Streaming Mapping适用于单次传输。^[inferred]

## 未解问题

- DMA Streaming Mapping在Intel IOMMU启用后是否仍会触发bounce？还是完全由IOVA翻译替代？^[inferred]
- `intel_dma_ops` 未实例化sync函数是否意味着IOMMU映射的buffer天然coherent？^[inferred]
- ~~scatter-gather列表（sg）在IOMMU页表映射中的处理方式？~~ 已由IOMMU、SMMU(ARM)图解来源补充：IOMMU将分散物理页聚合映射为连续IOVA区间（见本页IOVA一节），完整机制见[[concepts/linux-iommu-subsystem]]
- Coherent Mapping分配的物理内存是否必须连续？CMA（Contiguous Memory Allocator）的角色？^[inferred]

## 来源

- `raw/sources/Linux 操作系统/Linux 设备驱动管理/Linux IOMMU/Linux x86-64 IOMMU详解（2）——SWIOTLB（软件IOMMU）.md` — Coherent与Streaming映射的区别、Linux 4.0分界、map函数行为、SWIOTLB触发条件
- `raw/sources/Linux 操作系统/Linux 设备驱动管理/Linux IOMMU/Linux x86-64 IOMMU详解（6）——Intel IOMMU参与下的DMA Coherent Mapping.md` — intel_dma_ops、iommu_need_mapping分流、IOVA、IOMMU页表、__intel_map_single映射过程
- `raw/sources/Linux 操作系统/Linux 设备驱动管理/Linux IOMMU、SMMU(ARM)技术图解.md` — IOMMU三大作用（32位设备扩容/scatter-gather聚合/地址保护）
