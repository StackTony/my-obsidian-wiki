---
title: 网卡中断绑定：SMP IRQ Affinity
category: summaries
tags: [硬件, 网卡, 中断, affinity, irqbalance]
aliases: [SMP IRQ Affinity, 网卡中断绑定, smp_affinity]
source_dir: 物理硬件/网卡
source_files: [网卡中断绑定 smp irq affinity介绍.md]
summary: SMP IRQ Affinity：kernel 2.4+利用APIC把不同硬件IRQ绑定到指定CPU，避免中断风暴打满单核；smp_affinity十六进制位掩码配置，RPS/RFS补单队列网卡软中断均衡。
provenance:
  extracted: 0.78
  inferred: 0.17
  ambiguous: 0.05
base_confidence: 0.44
lifecycle: draft
lifecycle_changed: 2026-11-06
tier: supporting
created: 2026-11-06
updated: 2026-11-06
---

# 网卡中断绑定：SMP IRQ Affinity

硬件中断发生频繁且消耗CPU资源，多核条件下把大量硬件中断分配给不同CPU处理能很好地平衡性能——kernel 2.4以后利用可编程中断控制器的特性，把不同IRQ分配到特定CPU，这个绑定技术称为SMP IRQ Affinity。已并入 [[concepts/linux-interrupt-system]] 的"中断的CPU亲和性"一节。

## 核心观点

- APIC(高级可编程中断控制器)是SMP体系的核心，通过它将中断分发到不同CPU处理——绑定或摊平，即SMP IRQ Affinity；传统8259A只适合单CPU。
- 名词链：IRQ号决定CPU处理优先级(号越小优先级越高)；中断分上下两半(硬中断=上半部，软中断=下半部)，中间以中断控制器为分隔；SMP=各CPU共享内存子系统与总线、完全对等。
- 配置接口：`/proc/irq/{IRQ}/smp_affinity`(十六进制CPU位掩码)与`/proc/irq/{IRQ}/smp_affinity_list`(十进制CPU列表)；默认值在`/proc/irq/default_smp_affinity`。
- 位掩码解读：8个逻辑core对应11111111；`cat /proc/irq/76/smp_affinity`得`20`(二进制00100000)=绑定CPU5；`fff`(111111111111)=CPU0-11；list格式支持`0-11`或逗号分隔。
- **手动绑定前必须停掉irqbalance**等自动调节服务，否则修改会被其覆盖。
- 多队列网卡(`cat /proc/interrupts | grep eth0`见eth0-TxRx-0~7多个IRQ)可用SMP IRQ affinity直接绑定硬中断；**单队列网卡配置多CPU无效**，需RPS/RFS软件均衡——RPS单纯把包均衡到不同CPU，RFS进一步确保软中断处理CPU与应用所在CPU同核，利用CPU cache局部性。
- 使用经验：一般机器一般应用用irqbalance省心；**大量小包系统**上irqbalance几乎无效且造成CPU消耗分配不均，应停掉改手动绑定；文件/高流量Web服务器把不同网卡IRQ均衡绑到不同CPU；数据库服务器"磁盘控制器绑一个CPU、网卡绑另一个CPU"可优化响应时间；多网卡存储服务器是手动绑定的典型场景。
- 中断在 `/proc/interrupts` 的行含义：IRQ号 + 每CPU计数 + 类型(IR-IO-APIC-edge/fasteoi、IR-PCI-MSI-edge) + 设备名；表尾还有NMI/LOC(本地时钟)/RES(重新调度)/CAL(函数调用)/TLB(TLB shootdown)等架构级中断统计。
- 性能优化是过程而不是结果，需要大量测试、监测与持续观察改进。

## 未解问题

- RPS/RFS的实现细节(文中引用的"网卡软中断过高问题优化总结""多队列网卡简介""Linux内核RPS和RFS功能详细测试分析"三篇)不在vault中，机制层面只有定性描述。
- IRQ号与优先级的关系("号越小优先级越高")与现代MSI/MSI-X中断(IRQ号动态分配)的适配情况未说明。 ^[inferred]

## 来源

- raw/sources/物理硬件/网卡/网卡中断绑定 smp irq affinity介绍.md（cnblogs）
