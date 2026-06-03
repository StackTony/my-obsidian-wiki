---
title: Linux设备直通：IOMMU+SR-IOV+VFIO
category: concepts
tags: [linux, 虚拟化, 直通, IOMMU, SR-IOV, VFIO]
aliases: [设备直通, IOMMU虚拟化, VFIO, SR-IOV]
relationships:
  - target: "[[concepts/linux-virtio-architecture]]"
    type: related_to
  - target: "[[concepts/linux-namespace-cgroups]]"
    type: uses
source_dir: Linux 虚拟化/IO虚拟化
source_files: ["设备直通 iommu+sriov、vfio.md"]
summary: 设备直通将物理设备直接分配给VM使用，跳过软件模拟层。IOMMU提供DMA地址翻译和安全隔离，SR-IOV将一个物理设备虚拟出多个VF，VFIO是Linux用户态驱动框架。
provenance:
  extracted: 0.50
  inferred: 0.35
  ambiguous: 0.15
base_confidence: 0.538
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: supporting
created: 2026-06-01
updated: 2026-06-01
---

# Linux设备直通：IOMMU+SR-IOV+VFIO

设备直通(Passthrough)让物理设备直接供VM使用，几乎零开销——数据面在VM与硬件间直通，无需Host软件介入。这是性能最高的虚拟化IO方式，但牺牲了灵活性和可管理性^[inferred]。

## 核心观点

### 三大技术组件

**IOMMU（Input-Output Memory Management Unit）**
- DMA地址翻译：将Guest物理地址(GPA)翻译为Host物理地址(HPA)，使设备DMA能正确访问VM内存
- 安全隔离：限制设备DMA访问范围，防止恶意设备越界读写^[inferred]
- 类似CPU侧的MMU，但面向设备DMA而非CPU访存

**SR-IOV（Single Root I/O Virtualization）**
- 一个物理网卡(PF)虚拟出多个虚拟功能(VF)
- VF可直接分配给VM，每个VF有独立的配置空间和DMA引擎
- PF：使用VFIO方式将物理设备直通给VM，Host侧不再可见该设备
- VF：使用SR-IOV方式，先在Host侧虚拟出多个设备再分配给VM

**VFIO（Virtual Function I/O）**
- Linux内核用户态驱动框架
- 提供安全的设备访问接口，配合IOMMU实现DMA隔离
- QEMU通过VFIO驱动将物理设备映射到VM的地址空间^[inferred]

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

- IOMMU的2-stage翻译（GPA→IOVA→HPA）的具体实现细节？
- VFIO的group/container/device三层抽象设计？
- SR-IOV VF数量上限与性能线性度关系？


## 延伸阅读

综合分析：[[synthesis/virtio-architecture-evolution]]

## 来源

- `raw/sources/Linux 虚拟化/IO虚拟化/设备直通 iommu+sriov、vfio.md` — PF/VF区别、IOMMU/VFIO概念