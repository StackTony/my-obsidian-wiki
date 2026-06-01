---
title: Wiki Index
updated: 2026-06-01
---

# Wiki Index

*自动维护。上次更新：2026-06-01*

## Summaries

- [linux-softirq-detail](summaries/linux-softirq-detail.md) — Linux软中断的完整实现：preempt_count防抢占机制、__do_softirq执行流、ksoftirqd溢出处理 — `linux` `kernel` `softirq` `interrupt` `ksoftirqd`
- [linux-meminfo-params](summaries/linux-meminfo-params.md) — /proc/meminfo各字段含义与关系：内存黑洞、LRU分类、HugePages与THP区别、关键公式 — `linux` `kernel` `memory` `meminfo` `page-cache`
- [linux-page-cache](summaries/linux-page-cache.md) — Page Cache机制：基数树结构、预读算法、Write Through与Write Back一致性、Dirty page回写 — `linux` `kernel` `page-cache` `file-io` `memory`
- [linux-network-protocol-stack-impl](summaries/linux-network-protocol-stack-impl.md) — Linux网络协议栈收发路径、sk_buff零拷贝机制与NAPI接收模型 — `linux` `kernel` `network` `tcp` `ip` `sk_buff` `protocol-stack`
- [linux-rcu-lock](summaries/linux-rcu-lock.md) — RCU读零开销哲学：宽限期机制、Tree RCU分层检测、SRCU可睡眠变体与适用条件 — `linux` `kernel` `rcu` `lock` `synchronization`
- [virtio-io-notification-mechanism](summaries/virtio-io-notification-mechanism.md) — Virtio前后端双向零拷贝通知：ioeventfd(Guest→Host)和irqfd(Host→Guest) — `linux` `虚拟化` `virtio` `ioeventfd` `irqfd`
- [virtio-vring-data-sharing](summaries/virtio-vring-data-sharing.md) — vring三大表(desc/avail/used)组成的生产者-消费者数据共享机制 — `linux` `虚拟化` `virtio` `vring` `数据共享`
- [linux-live-migration-flow](summaries/linux-live-migration-flow.md) — 虚拟机热迁移三阶段流程：内存迭代拷贝、停机拷贝、网络恢复与关键参数 — `linux` `虚拟化` `热迁移` `QEMU` `libvirt`

## Entities

- [libvirt-virsh](entities/libvirt-virsh.md) — libvirt命令行管理工具，覆盖VM全生命周期运维操作 — `linux` `虚拟化` `libvirt` `virsh` `工具`

## Concepts

- [linux-interrupt-system](concepts/linux-interrupt-system.md) — Linux中断系统：IRQ/softirq两阶段设计、三种延迟机制、ksoftirqd — `linux` `kernel` `interrupt` `irq` `softirq`
- [linux-memory-management](concepts/linux-memory-management.md) — Linux内存管理：meminfo参数、Page Cache架构、内存黑洞、LRU与Write策略 — `linux` `kernel` `memory` `meminfo` `page-cache` `lru`
- [linux-io-stack](concepts/linux-io-stack.md) — Linux IO栈：五层IO架构、IO调度器、设备发现与gendisk结构 — `linux` `kernel` `io` `block` `scheduler`
- [linux-boot-shutdown](concepts/linux-boot-shutdown.md) — Linux启动与关机：10步启动流程、关机多子系统协调、systemd与架构差异 — `linux` `kernel` `boot` `shutdown` `systemd`
- [linux-network-stack](concepts/linux-network-stack.md) — Linux网络栈：TCP/IP四层模型、三张核心表、sk_buff零拷贝、NAPI混合模式 — `linux` `kernel` `network` `tcp` `ip` `sk_buff`
- [linux-lock-mechanisms](concepts/linux-lock-mechanisms.md) — Linux内核同步机制的完整框架：从Spinlock到RCU的演进与选择指南 — `linux` `kernel` `synchronization` `lock` `spinlock` `mutex` `rcu`
- [linux-namespace-cgroups](concepts/linux-namespace-cgroups.md) — Linux内核资源隔离双引擎：Namespace实现视图隔离，Cgroups实现资源限制 — `linux` `kernel` `namespace` `cgroups` `container` `isolation`
- [linux-process-scheduling](concepts/linux-process-scheduling.md) — Linux内核进程调度核心：CFS完全公平调度器的红黑树机制与三种调度策略 — `linux` `kernel` `scheduler` `CFS` `process` `scheduling`
- [linux-system-v-ipc](concepts/linux-system-v-ipc.md) — System V IPC三大机制：信号量集合、共享内存、消息队列的原理与API — `linux` `ipc` `semaphore` `shared-memory` `message-queue` `system-v`
- [linux-virtio-architecture](concepts/linux-virtio-architecture.md) — Virtio半虚拟化IO框架：前后端分离+四种架构演进(传统→vhost→vhost-user→vDPA) — `linux` `虚拟化` `virtio` `IO虚拟化` `半虚拟化`
- [linux-interrupt-virtualization](concepts/linux-interrupt-virtualization.md) — 中断虚拟化三种场景：物理设备中断→vCPU、虚拟外设中断→vCPU、Guest IPI — `linux` `虚拟化` `中断` `VGIC` `KVM`
- [linux-device-passthrough](concepts/linux-device-passthrough.md) — 设备直通三大技术：IOMMU(DMA翻译+隔离)、SR-IOV(PF/VF)、VFIO(用户态驱动) — `linux` `虚拟化` `直通` `IOMMU` `SR-IOV` `VFIO`

## Skills

- [virsh-vm-management](skills/virsh-vm-management.md) — virsh管理KVM虚拟机的实操指南：生命周期、热迁移、CPU绑定等常用命令组合 — `linux` `虚拟化` `virsh` `运维` `操作手册`

## Synthesis

- [virtio-architecture-evolution](synthesis/virtio-architecture-evolution.md) — Virtio四种架构演进分析：数据面从软件模拟到硬件直通，性能与灵活性的核心矛盾 — `linux` `虚拟化` `virtio` `vhost` `DPDK` `vDPA`

## Journal