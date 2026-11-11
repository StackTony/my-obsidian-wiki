---
title: 虚拟机地址转换链：GVA/GPA/HVA/HPA与EPT
category: concepts
tags: [linux, 虚拟化, EPT, KVM, 内存]
aliases: [GVA, GPA, HVA, HPA, EPT, 二级地址翻译, 虚拟化地址转换]
relationships:
  - target: "[[concepts/virtual-memory-and-paging]]"
    type: extends
  - target: "[[concepts/linux-device-passthrough]]"
    type: related_to
  - target: "[[concepts/iommu-group-domain-isolation]]"
    type: related_to
  - target: "[[concepts/linux-interrupt-virtualization]]"
    type: related_to
source_dir: Linux 操作系统/Linux 设备驱动管理/Linux IOMMU

source_files: [Linux IOMMU、SMMU(ARM)技术图解.md]
summary: 虚拟化四层地址空间：GVA→GPA由虚机页表完成（页表本身存于HPA，遍历需经EPT），GPA→HPA由EPT硬件完成。HVA由Qemu mmap+KVM_SET_USER_MEMORY_REGION桥接。设备透传要求EPT与IOMMU两条映射路径汇于同一HPA。
provenance:
  extracted: 0.65
  inferred: 0.32
  ambiguous: 0.03
base_confidence: 0.44
lifecycle: draft
lifecycle_changed: 2026-11-10
tier: supporting
created: 2026-11-10
updated: 2026-11-10
---

# 虚拟机地址转换链：GVA/GPA/HVA/HPA与EPT

虚拟化把地址空间叠成两层：客户机有自己的GVA（Guest Virtual Address）和GPA（Guest Physical Address），宿主机有HPA（Host Physical Address），VMM作为应用只见HVA（Host Virtual Address）。页表一旦建好，整个映射过程硬件自动完成——但设备透通要求**EPT与IOMMU两条翻译路径殊途同归**，这是本页的核心问题。

## 核心观点

### 四层地址空间与两条翻译路径

```
GVA --(虚机页表)--> GPA --(EPT)--> HPA
                        GPA --(IOMMU)--> HPA   ← 设备DMA路径
HVA --(VMM页表)--> HPA                 ← Qemu/KVM所在路径
```

- **虚机内**：GVA→GPA由虚机自己的页表完成。关键细节：虚机各级页表本身也存在HPA中，而CR3及各级页表项里装的都是GPA——所以**硬件遍历虚机页表时也要借助EPT**，每读一个页表项都是一次GPA→HPA翻译
- **EPT**：GPA→HPA的翻译，一层层页表映射，硬件自动完成
- **IOMMU路径**：设备DMA的地址（透传时为GPA）由IOMMU翻译为HPA，映射由VMM维护

单机MMU的页表机制是这一切的基础，见[[concepts/virtual-memory-and-paging]]；EPT本质上是"给GPA再建一套MMU页表" ^[inferred]。

### HVA为什么存在

纯硬件视角（GVA→GPA→HPA）不需要HVA，但两个软件场景都绕不开它：

1. **Qemu建立EPT映射**：Qemu是应用程序，唯一可见的是HVA。Qemu按虚机RAM大小（GPA范围）mmap出对应的HVA，再用 `KVM_SET_USER_MEMORY_REGION` 命令控制KVM，传入 `guest_phys_addr`（虚机GPA起始）和 `userspace_addr`（mmap所得HVA首地址）。KVM据此为虚机建EPT映射表（GPA→HPA），同时为VMM建立HVA→HPA映射
2. **vm_exit后的异常处理**：VMM处理异常时能拿到GPA，若需访问虚机GPA对应的内存，VMM自己的访存只能走HVA→HPA——所以Qemu必须维护GPA↔HVA的对应关系，给定GPA就能查到HVA

### 设备透传的映射一致性：HPA1 == HPA2

设备透传后，虚机配置设备DMA时直接填GPA。此时：

- GPA经**EPT**映射为HPA1（虚机内存视角）
- GPA经**IOMMU**映射为HPA2（设备DMA视角）
- **HPA1和HPA2必须相等**，透传才有意义——否则设备写到的内存不是虚机看到的内存

保证相等的机制：对IOMMU来说，此时GPA就是iova；GPA经EPT对应HPA1，而VMM知道HPA1对应的虚机地址是HVA；VMM把**HVA作为vaddr**传入 `VFIO_IOMMU_MAP_DMA`（流程见[[concepts/iommu-group-domain-isolation]]），IOMMU把GPA映射到HVA对应的物理地址HPA1——于是HPA2==HPA1。

注意IOMMU映射在**虚机启动时**就已建立，且要涵盖**整个GPA地址范围**；同时虚机HPA对应的物理页都不会被交换出去（设备DMA是异步的）。

### 无IOMMU时为什么不能透传

- 设备必须访问真实的物理地址HPA，而虚机可见的是GPA——地址语义对不上
- 若让虚机直接填HPA，等于虚机可直接访问宿主机物理地址，安全隐患无法接受
- 因此无IOMMU时设备访问一律由VMM软件接管，不向虚机暴露HPA

## 关键细节

- EPT与IOMMU页表是**两套独立页表**，靠VMM用相同的GPA→HPA事实填充才能一致——这是纯软件约定，硬件各自翻译 ^[inferred]
- KVM_SET_USER_MEMORY_REGION是Qemu/KVM间建立内存布局的核心ioctl：声明"GPA区间挂在哪个HVA上"，KVM同时维护两套映射 ^[inferred]
- 虚机页表遍历要经EPT，意味着一次GVA翻译实际发生多次内存访问——这是嵌套虚拟化的固有开销 ^[inferred]
- 中断路径的虚拟化（VGIC/ioeventfd等）与内存路径的这套地址链同属KVM机制，见[[concepts/linux-interrupt-virtualization]]

## 未解问题

- EPT大页（2MB/1GB）如何降低双重翻译开销？
- 影子页表（Software MMU）与EPT的关系及适用场景？（本来源未涉及）
- 内存热插拔/热迁移时GPA↔HVA区间如何动态更新？[[summaries/linux-live-migration-flow]] 中的迭代拷贝与这套映射的交互？

## 来源

- `raw/sources/Linux 操作系统/Linux 设备驱动管理/Linux IOMMU/Linux IOMMU、SMMU(ARM)技术图解.md` — GVA/GPA/HPA映射链、HVA的两个作用、KVM_SET_USER_MEMORY_REGION、透传一致性(HPA1==HPA2)
