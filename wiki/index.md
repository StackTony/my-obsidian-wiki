---
title: Wiki Index
updated: 2026-06-02
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
- [gdb-common-commands](summaries/gdb-common-commands.md) — hellogcc/100-gdb-tips整理的GDB常用命令速查：断点/观察点/执行控制/内存查看/多线程/多进程/TUI — `linux` `gdb` `调试` `命令速查`
- [linux-task-struct-mm-struct](summaries/linux-task-struct-mm-struct.md) — task→mm→VMA→pgd四级链式结构、多线程共享mm、内核线程active_mm借用机制 — `linux` `内核` `task_struct` `mm_struct` `进程` `内存`
- [crash-vmcore-analysis](summaries/crash-vmcore-analysis.md) — crash工具分析vmcore的基本操作：bt/struct/dis/rd/kmem常用命令、时间戳转换 — `linux` `vmcore` `crash` `崩溃分析`
- [crash-register-address](summaries/crash-register-address.md) — x86_64和ARM64寄存器体系、函数调用约定、栈回溯原理、常见崩溃场景分析 — `linux` `寄存器` `x86` `ARM64` `崩溃分析` `调用约定`
- [linux-interrupt-monitoring-script](summaries/linux-interrupt-monitoring-script.md) — 不依赖额外模块的bash脚本：基于/proc/interrupts两次采样的每秒中断增量观测 — `linux` `中断` `监控脚本` `/proc/interrupts`
- [linux-ftrace-kprobe-overview](summaries/linux-ftrace-kprobe-overview.md) — ftrace(静态/开销大) vs kprobe(动态/灵活) vs bpftrace(eBPF)三大追踪框架概览 — `linux` `tracing` `ftrace` `kprobe` `bpftrace`

## Entities

- [libvirt-virsh](entities/libvirt-virsh.md) — libvirt命令行管理工具，覆盖VM全生命周期运维操作 — `linux` `虚拟化` `libvirt` `virsh` `工具`
- [perf-tool](entities/perf-tool.md) — Linux原生性能分析工具perf：基于事件采样，stat/top/record/report/kmem覆盖CPU/内存/调度/IO分析 — `linux` `perf` `性能分析` `CPU` `采样`
- [crash-tool](entities/crash-tool.md) — crash vmcore崩溃转储分析核心工具：bt/struct/kmem/dis命令回溯崩溃内核状态 — `linux` `vmcore` `crash` `崩溃分析` `内核调试`
- [gdb-tool](entities/gdb-tool.md) — GNU Debugger：断点/观察点/多线程/多进程/Core Dump/汇编/TUI，可调试QEMU初始化流程 — `linux` `gdb` `调试` `开发工具`
- [flamegraph-tool](entities/flamegraph-tool.md) — 火焰图(FlameGraph)：CPU调用栈可视化SVG，平顶=性能瓶颈，基于perf record数据生成 — `linux` `火焰图` `FlameGraph` `性能分析` `CPU可视化`

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
- [linux-tracing-frameworks](concepts/linux-tracing-frameworks.md) — 内核追踪四大框架对比：ftrace(静态)/kprobe(动态)/perf(采样)/bpftrace(eBPF) — `linux` `内核` `tracing` `ftrace` `kprobe` `perf`
- [linux-cpu-performance-analysis](concepts/linux-cpu-performance-analysis.md) — CPU性能分析三大场景：perf采样/kvmtop VM-Exit/%ST抢占率 — `linux` `cpu` `性能分析` `虚拟化` `perf`
- [linux-vmcore-analysis](concepts/linux-vmcore-analysis.md) — vmcore崩溃转储分析：crash工具、x86/ARM64寄存器、task/mm结构体、栈回溯 — `linux` `vmcore` `crash` `崩溃分析` `寄存器`
- [linux-io-performance-analysis](concepts/linux-io-performance-analysis.md) — IO性能分析：iostat监控/fio压测/dd测速/blktrace追踪/block_dump日志 — `linux` `io` `性能分析` `iostat` `fio`
- [linux-virtio-architecture](concepts/linux-virtio-architecture.md) — Virtio半虚拟化IO框架：前后端分离+四种架构演进(传统→vhost→vhost-user→vDPA) — `linux` `虚拟化` `virtio` `IO虚拟化` `半虚拟化`
- [linux-interrupt-virtualization](concepts/linux-interrupt-virtualization.md) — 中断虚拟化三种场景：物理设备中断→vCPU、虚拟外设中断→vCPU、Guest IPI — `linux` `虚拟化` `中断` `VGIC` `KVM`
- [linux-device-passthrough](concepts/linux-device-passthrough.md) — 设备直通三大技术：IOMMU(DMA翻译+隔离)、SR-IOV(PF/VF)、VFIO(用户态驱动) — `linux` `虚拟化` `直通` `IOMMU` `SR-IOV` `VFIO`

## Skills

- [virsh-vm-management](skills/virsh-vm-management.md) — virsh管理KVM虚拟机的实操指南：生命周期、热迁移、CPU绑定等常用命令组合 — `linux` `虚拟化` `virsh` `运维` `操作手册`
- [linux-kernel-debugging](skills/linux-kernel-debugging.md) — 内核各子系统监控命令、常见问题排查路径与调试技巧：softirq/meminfo/Page Cache/IO/关机/cgroup/IPC — `linux` `内核` `调试` `监控` `性能分析`
- [linux-ipc-programming](skills/linux-ipc-programming.md) — System V IPC三大机制C编程实操：信号量集合+共享内存+消息队列的API速查与demo — `linux` `ipc` `编程` `信号量` `共享内存` `消息队列`
- [linux-lock-selection](skills/linux-lock-selection.md) — 内核锁类型选择决策树与API速查：Spinlock/Mutex/RCU等10种锁的适用场景与常见陷阱 — `linux` `内核` `锁` `spinlock` `mutex` `rcu` `同步`
- [linux-kernel-tracing](skills/linux-kernel-tracing.md) — 内核追踪实操手册：ftrace函数追踪→kprobe动态探针→perf事件采样→火焰图可视化四类场景 — `linux` `内核` `tracing` `ftrace` `kprobe` `perf` `火焰图`
- [linux-vm-debugging](skills/linux-vm-debugging.md) — 虚拟化调试实操：kvmtop EXT/%ST抢占/D状态vcpu/中断脚本/NUMA/QEMU gdb七大场景 — `linux` `虚拟化` `调试` `kvmtop` `虚拟机监控` `NUMA`
- [linux-vmcore-debugging](skills/linux-vmcore-debugging.md) — vmcore崩溃分析实操：crash加载→堆栈回溯→寄存器解读→结构体分析→崩溃类型识别 — `linux` `vmcore` `crash` `崩溃分析` `寄存器` `内核调试`
- [linux-io-debugging](skills/linux-io-debugging.md) — IO性能排查与压测实操：iostat→fio→dd→blktrace→block_dump四步流程 — `linux` `io` `iostat` `fio` `blktrace` `dd` `性能分析`
- [linux-network-debugging](skills/linux-network-debugging.md) — 网络调试实操：tcpdump抓包分析（参数/表达式/实例）+ iperf打流测试 — `linux` `网络` `tcpdump` `iperf` `网络分析`
- [gdb-debugging-guide](skills/gdb-debugging-guide.md) — GDB调试实操速查：断点/观察点/执行控制/内存查看/多线程/多进程/Core Dump/QEMU调试 — `linux` `gdb` `调试` `QEMU` `断点` `观察点`

## Synthesis

- [virtio-architecture-evolution](synthesis/virtio-architecture-evolution.md) — Virtio四种架构演进分析：数据面从软件模拟到硬件直通，性能与灵活性的核心矛盾 — `linux` `虚拟化` `virtio` `vhost` `DPDK` `vDPA`
- [linux-kernel-subsystem-interactions](synthesis/linux-kernel-subsystem-interactions.md) — Linux内核六大子系统交互机制：preempt_count统一上下文追踪、softirq跨子系统分发、Page Cache交汇点、锁跨上下文协调 — `linux` `内核` `子系统交互` `preempt_count` `softirq` `page-cache` `锁`
- [linux-dfx-tool-landscape](synthesis/linux-dfx-tool-landscape.md) — DFX调试工具全景图：六大领域(CPU/IO/内存/网络/追踪/vmcore)×三种模式(监控/追踪/事后)的工具矩阵与互补关系 — `linux` `DFX` `调试` `工具全景` `性能分析`

## Journal