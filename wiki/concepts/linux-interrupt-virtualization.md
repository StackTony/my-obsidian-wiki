---
title: Linux中断虚拟化
category: concepts
tags: [linux, 虚拟化, 中断, VGIC, KVM]
aliases: [中断虚拟化, VGIC, KVM中断注入]
relationships:
  - target: "[[concepts/linux-interrupt-system]]"
    type: extends
  - target: "[[concepts/linux-virtio-architecture]]"
    type: related_to
source_dir: Linux 虚拟化/中断虚拟化
source_files: [KVM中断注入机制.md, vgic中断虚拟化介绍.md]
summary: 中断虚拟化处理三种场景：物理设备中断→vCPU、虚拟外设(QEMU模拟)中断→vCPU、Guest内IPI核间中断。VGIC是ARM架构的中断虚拟化控制器。
provenance:
  extracted: 0.55
  inferred: 0.30
  ambiguous: 0.15
base_confidence: 0.538
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: supporting
created: 2026-06-01
updated: 2026-06-01
---

# Linux中断虚拟化

中断虚拟化是虚拟化技术中最复杂的子系统之一——需要将物理中断信号正确路由到虚拟CPU，同时处理虚拟设备和虚拟核间中断。

## 核心观点

### 三种中断虚拟化场景

1. **物理设备中断 → vCPU**：物理硬件产生中断信号，经Host内核中断处理后路由到目标vCPU
2. **虚拟外设中断 → vCPU**：QEMU模拟的设备产生中断，通过irqfd机制注入到vCPU^[inferred]
3. **Guest内IPI核间中断**：Guest OS中vCPU之间的中断通信，如调度迁移、TLB刷新

### KVM中断注入机制

x86架构的关键组件：
- **LAPIC(Local APIC)**：本地高级可编程中断控制器，每个CPU一个
- **IOAPIC(I/O APIC)**：I/O高级可编程中断控制器，接收外部设备中断并路由到目标CPU

核间中断通过ICR(Interrupt Command Register)寄存器发起——软件按寄存器规则写入信息即可发出IPI^[ambiguous]。

### VGIC（ARM架构中断虚拟化）

VGIC(Virtual GIC)是ARM架构的中断虚拟化实现：

- **GICV2**：早期版本，支持NON-VHE和VHE模式
- VGIC将物理GIC的功能虚拟化，为每个vCPU维护虚拟中断状态
- 中断从产生到路由到vCPU的完整流程涉及VGIC的List Register、虚拟中断优先级等机制^[ambiguous]

**注意**：中断虚拟化源文件内容偏简略，VGIC介绍仅为片段，许多机制细节尚不完整。

## 未解问题

- VGIC的List Register和虚拟中断优先级的具体实现？
- GICV3/GICV4相比GICV2的改进？
- x86 vs ARM中断虚拟化的架构差异对性能的影响？


## 延伸阅读

综合分析：[[synthesis/virtio-architecture-evolution]]

## 来源

- `raw/sources/Linux 虚拟化/中断虚拟化/KVM中断注入机制.md` — LAPIC/IOAPIC概念、ICR寄存器
- `raw/sources/Linux 虚拟化/中断虚拟化/vgic中断虚拟化介绍.md` — 三种中断场景、VGIC介绍片段