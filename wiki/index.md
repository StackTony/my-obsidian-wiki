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

## Entities

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

## Synthesis

## Journal