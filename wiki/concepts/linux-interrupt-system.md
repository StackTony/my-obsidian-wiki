---
title: Linux中断系统
category: concepts
tags: [linux, 内核, 中断, softirq, IRQ]
aliases: [Linux中断, 内核中断机制, IRQ与softirq]
relationships:
  - target: "[[concepts/linux-lock-mechanisms]]"
    type: uses
  - target: "[[concepts/linux-process-scheduling]]"
    type: related_to
  - target: "[[concepts/linux-network-stack]]"
    type: uses
  - target: "[[concepts/linux-interrupt-virtualization]]"
    type: extends
  - target: "[[summaries/linux-interrupt-classification]]"
    type: related_to
source_dir: Linux 操作系统/Linux 中断系统
source_files: ["Linux 中断分类表.md", "Linux中断所有知识点.md", "Linux 硬中断 irq + 软中断 softirq原理.md", "Linux 软中断 softirq.md", "Linux 软中断内核线程 ksoftirqd详解.md", "Linux IPI 核间中断.md", "物理硬件/网卡/网卡中断绑定 smp irq affinity介绍.md"]
summary: Linux中断全景：同步/异步四维分类框架、上下半部两阶段设计、preempt_count上下文跟踪、三种延迟机制、GIC类型与irq_domain映射、ksoftirqd兜底。
provenance:
  extracted: 0.75
  inferred: 0.20
  ambiguous: 0.05
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: core
created: 2026-06-01
updated: 2026-11-09
---

# Linux中断系统

Linux中断系统是内核响应硬件事件的核心机制，采用上下半部设计将快速响应与延迟处理解耦，确保系统在处理外部事件时既能及时响应又不阻塞其他关键路径。详见 [[concepts/linux-os-virtualization-landscape|Linux OS/虚拟化全景]] 导航页。

## 核心观点

- 中断分类有四个正交维度：同步/异步（触发时机，最本质主轴）、软/硬（通俗叫法）、上/下半部（处理阶段）、功能/用途；"软中断"在不同语境分别指指令陷阱（`INT n`/`SVC`）、广义异常或内核 Softirq。
- 中断分上下半部：硬中断(IRQ)上半部在关中断状态下快速响应，只做最紧急的工作；软中断(softirq)下半部在开中断状态下延迟处理耗时操作。
- `preempt_count` 是内核跟踪当前执行上下文的关键机制，通过 HARDIRQ_OFFSET 和 SOFTIRQ_OFFSET 嵌入 `thread_info.preempt_count`，任何代码都可判断自己是否在中断上下文中。 ^[inferred]
- 三种延迟机制各有适用场景：softirq 适合高频率网络收包，tasklet 适合低频率驱动回调，workqueue 适合可睡眠的耗时操作。
- ksoftirqd 是每个CPU的内核线程，当 softirq 持续触发超出 MAX_SOFTIRQ_TIME 或 MAX_SOFTIRQ_RESTART 限制时，由 ksoftirqd 在进程上下文中兜底处理。

## 关键细节

### 中断分类框架

中断分类存在四个正交维度：**同步/异步**（触发时机，最本质主轴）、**软/硬**（通俗叫法）、**上/下半部**（处理阶段划分，Linux 特有）、**功能/用途**（I/O 中断、定时器中断等叫法属此维度，与机制类别正交）。

- **异步硬中断五类**：外设引脚中断（ARM GIC 的 PPI 每核私有/SPI 全系统共享，SMP 中断亲和性的硬件基础）；消息信令中断（MSI 最多 32 个连续向量、MSI-X 最多 2048 个独立向量；ARM GICv3+ 上由 ITS 翻译成 LPI 投递，x86 上直接落入 Local APIC）；处理器间中断（x86 IPI/ARM SGI）；不可屏蔽中断 NMI（`cli` 关不掉，用于看门狗与 perf 硬件采样）；本地中断（x86 LAPIC LVT：本地定时器/性能计数器/温控/APIC 错误，概念上对应 ARM 的 PPI）。
- **同步异常三类**：Fault（PC 指向当前指令，可恢复后重新执行，如缺页/#GP）、Trap（PC 指向下一条指令，主动触发，软中断指令 `INT n`/`SVC` 即其子类）、Abort（不可恢复，如 #DF 双重故障/#MC 机器检查）。
- **GICv3 硬件组成**：Distributor 管理 SPI（全局使能/优先级/分发），Redistributor 管理每核 SGI/PPI/LPI，CPU interface 负责应答与向核投递；多中断控制器下硬件中断号重复，内核用 **irq_domain** 将 hwirq 映射为虚拟中断号 virq，`request_threaded_irq` 注册的线程化中断以 SCHED_FIFO 内核线程执行。
- 完整分类表、术语速查与易混淆澄清见 [[summaries/linux-interrupt-classification]]；GIC 硬件、irq_domain 映射与 ARM64 处理全链路见 [[summaries/linux-interrupt-lifecycle]]。

### 上下半部机制

上半部（硬中断 ISR）的设计原则：
- 执行时间极短，关中断运行
- 只做最紧急的硬件响应（如从网卡DMA缓冲区拷贝数据到sk_buff）
- 将耗时的后续工作推迟到下半部

下半部（softirq/tasklet/workqueue）的设计原则：
- 开中断运行，允许新中断嵌套
- 执行网络协议栈处理、块设备完成回调等较耗时的工作
- workqueue 运行在进程上下文（kworker 线程），允许睡眠与调度；bound 队列每 CPU 有 nice 0 和 -20 两个 worker_pool，unbound 队列可跨核迁移

### preempt_count 跟踪机制

`thread_info.preempt_count` 是一个 32 位字段，划分为多个区段：

| 区段 | 偏移 | 含义 |
|------|------|------|
| PREEMPT_MASK | 0-7 | 抢占计数 |
| SOFTIRQ_MASK | 8-15 | 软中断计数 |
| HARDIRQ_MASK | 16-27 | 硬中断计数 |
| NMI_MASK | 28-31 | NMI计数 |

关键宏：
- `in_irq()` / `in_hardirq()` — 检查是否在硬中断上下文（HARDIRQ_OFFSET 非零）
- `in_softirq()` — 检查是否在软中断上下文（SOFTIRQ_OFFSET 非零）
- `in_interrupt()` — 检查是否在任何中断上下文
- `in_task()` — 检查是否在普通进程上下文

### 三种延迟机制对比

| 特性 | softirq | tasklet | workqueue |
|------|---------|---------|-----------|
| 执行上下文 | 软中断上下文 | 软中断上下文 | 进程上下文 |
| 可睡眠 | 否 | 否 | 是 |
| 并行性 | 同类型可多CPU并行 | 同类型不可并行 | 完全并行 |
| 开销 | 最低 | 中等 | 较高 |
| 适用场景 | 网络收包等高频率 | 驱动回调等低频率 | 需睡眠的耗时操作 |
| 定义方式 | 静态编译(HI_SOFTIRQ等) | 动态注册 | 动态创建kworker |

### 10 种静态 softirq 类型

内核定义了 10 种静态 softirq（5.10 内核 enum，NR_SOFTIRQS=10；部分文献沿用旧内核的 9 种计数，以 enum 列表为准）^[ambiguous]，优先级从高到低：

1. HI_SOFTIRQ — 高优先级tasklet
2. TIMER_SOFTIRQ — 定时器
3. NET_TX_SOFTIRQ — 网络发送
4. NET_RX_SOFTIRQ — 网络接收
5. BLOCK_SOFTIRQ — 块设备
6. IRQ_POLL_SOFTIRQ — IO轮询
7. TASKLET_SOFTIRQ — 低优先级tasklet
8. SCHED_SOFTIRQ — 调度类
9. HRTIMER_SOFTIRQ — 高精度定时器
10. RCU_SOFTIRQ — RCU回调 ^[inferred]（RCU后来改为使用RCU nocb线程处理回调，softirq只是触发入口）

### ksoftirqd 内核线程

每个CPU有一个 ksoftirqd/%u 内核线程：
- 触发条件：`__do_softirq()` 在处理 softirq 时，如果重启次数超过 MAX_SOFTIRQ_RESTART（10次），或执行时间超过 MAX_SOFTIRQ_TIME（2 jiffies，1000Hz 系统≈2ms、200Hz 系统=10ms），则唤醒 ksoftirqd
- 运行方式：在进程上下文中作为 SCHED_OTHER 级别线程运行，可被抢占
- 设计意图：防止 softirq 连续触发导致普通进程长时间无法获得CPU

### IPI 核间中断

IPI（Inter-Processor Interrupt）是跨核通信机制：
- 通过 ICR（Interrupt Command Register）寄存器发送
- 目标可以是特定CPU、所有CPU或除自身外的所有CPU
- x86 通过 `apic->send_IPI()` 接口实现；ARM 平台由 GIC 的 SGI（Software Generated Interrupt，软件写 GICD_SGIR 发起）实现同等功能——SGI 虽由软件发起，但经 GIC 异步投递到目标核，归类属于硬件中断而非指令级"软中断"
- 常见用途：TLB flush（TLB Shootdown，见 [[summaries/linux-tlb-management]]）、reschedule interrupt（唤醒其他CPU上的调度器）、调度负载均衡、时钟事件广播、stop CPU等

### SMP IRQ Affinity — 硬中断的CPU亲和性绑定

多核系统下，硬件中断可经APIC分发并绑定到特定CPU处理（kernel 2.4+支持，即SMP IRQ Affinity），避免单核被中断风暴打满：

- 绑定接口：`/proc/irq/{IRQ}/smp_affinity`（十六进制CPU位掩码，如`fff`=CPU0-11）与`/proc/irq/{IRQ}/smp_affinity_list`（十进制列表，如`0-11`）；默认值见`/proc/irq/default_smp_affinity`。位掩码解读：8核对应`11111111`，`0x20`（二进制00100000）即绑定CPU5。
- 手动绑定前必须停止irqbalance等自动调节服务，否则修改会被其覆盖。
- 多队列网卡（`/proc/interrupts`中`eth0-TxRx-0~N`多个IRQ）可将各队列硬中断分别绑到不同CPU；**单队列网卡配多CPU无效**，需RPS/RFS软件均衡——RPS单纯把包均衡到不同CPU，RFS进一步让软中断处理CPU与应用所在CPU同核，利用CPU cache局部性。
- 经验法则：一般负载交给irqbalance省心；大量小包系统上irqbalance几乎无效且造成CPU消耗分配不均，应停掉改手动绑定；数据库服务器可"磁盘控制器绑一个CPU、网卡绑另一个CPU"降低响应时间；多网卡多硬盘的网络存储服务器是手动绑定的典型场景。

触发来源：物理硬件/网卡/网卡中断绑定 smp irq affinity介绍.md（2026-11-06 ingest）。完整蒸馏见 [[summaries/nic-smp-irq-affinity]]；中断增量观测脚本见 [[summaries/linux-interrupt-monitoring-script]]。

## 未解问题

- PREEMPT_RT 补丁对中断上下文的影响——实时内核将部分中断处理线程化，这对 softirq 的执行语义有何改变？ ^[inferred]
- tasklet 是否应该被逐步废弃（内核社区有此倾向），统一迁移到 workqueue？ ^[ambiguous]


## 延伸阅读

实操指南：[[skills/linux-lock-selection]], [[skills/linux-kernel-tracing]], [[skills/linux-vm-debugging]]

综合分析：[[synthesis/linux-kernel-subsystem-interactions]]

## 来源

- [[summaries/linux-interrupt-classification]] — 中断分类四维度框架与术语速查（2026-11-09 ingest）
- [[summaries/linux-interrupt-lifecycle]] — GIC硬件、irq_domain映射、中断注册与ARM64处理全链路（2026-11-09 ingest）
- [[summaries/linux-softirq-detail]] — softirq原理与ksoftirqd详解
- [[summaries/linux-rcu-lock]] — RCU softirq相关
- [[summaries/linux-network-protocol-stack-impl]] — NET_RX_SOFTIRQ在网络收包中的应用