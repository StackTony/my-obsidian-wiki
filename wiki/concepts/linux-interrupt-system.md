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
source_dir: Linux 操作系统/Linux 中断系统
source_files: [Linux 硬中断irq + 软中断softirq原理.md, Linux 软中断softirq.md, Linux ksoftirqd软中断内核线程详解.md, Linux IPI 核间中断.md]
summary: Linux中断分上下半部：硬中断(IRQ)上半部快速响应、软中断(softirq)下半部延迟处理。preempt_count跟踪中断上下文，三种延迟机制对比，ksoftirqd兜底。
provenance:
  extracted: 0.75
  inferred: 0.20
  ambiguous: 0.05
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: core
created: 2026-06-01
updated: 2026-06-01
---

# Linux中断系统

Linux中断系统是内核响应硬件事件的核心机制，采用上下半部设计将快速响应与延迟处理解耦，确保系统在处理外部事件时既能及时响应又不阻塞其他关键路径。

## 核心观点

- 中断分上下半部：硬中断(IRQ)上半部在关中断状态下快速响应，只做最紧急的工作；软中断(softirq)下半部在开中断状态下延迟处理耗时操作。
- `preempt_count` 是内核跟踪当前执行上下文的关键机制，通过 HARDIRQ_OFFSET 和 SOFTIRQ_OFFSET 嵌入 `thread_info.preempt_count`，任何代码都可判断自己是否在中断上下文中。 ^[inferred]
- 三种延迟机制各有适用场景：softirq 适合高频率网络收包，tasklet 适合低频率驱动回调，workqueue 适合可睡眠的耗时操作。
- ksoftirqd 是每个CPU的内核线程，当 softirq 持续触发超出 MAX_SOFTIRQ_TIME 或 MAX_SOFTIRQ_RESTART 限制时，由 ksoftirqd 在进程上下文中兜底处理。

## 关键细节

### 上下半部机制

上半部（硬中断 ISR）的设计原则：
- 执行时间极短，关中断运行
- 只做最紧急的硬件响应（如从网卡DMA缓冲区拷贝数据到sk_buff）
- 将耗时的后续工作推迟到下半部

下半部（softirq/tasklet/workqueue）的设计原则：
- 开中断运行，允许新中断嵌套
- 执行网络协议栈处理、块设备完成回调等较耗时的工作

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

### 9种静态 softirq 类型

内核定义了 9 种静态 softirq，优先级从高到低：

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
- 触发条件：`__do_softirq()` 在处理 softirq 时，如果重启次数超过 MAX_SOFTIRQ_RESTART（通常10次），或执行时间超过 MAX_SOFTIRQ_TIME（2ms），则唤醒 ksoftirqd
- 运行方式：在进程上下文中作为 SCHED_OTHER 级别线程运行，可被抢占
- 设计意图：防止 softirq 连续触发导致普通进程长时间无法获得CPU

### IPI 核间中断

IPI（Inter-Processor Interrupt）是跨核通信机制：
- 通过 ICR（Interrupt Command Register）寄存器发送
- 目标可以是特定CPU、所有CPU或除自身外的所有CPU
- x86 通过 `apic->send_IPI()` 接口实现
- 常见用途：TLB flush、reschedule interrupt（唤醒其他CPU上的调度器）、stop CPU等

## 未解问题

- PREEMPT_RT 补丁对中断上下文的影响——实时内核将部分中断处理线程化，这对 softirq 的执行语义有何改变？ ^[inferred]
- tasklet 是否应该被逐步废弃（内核社区有此倾向），统一迁移到 workqueue？ ^[ambiguous]


## 延伸阅读

实操指南：[[skills/linux-lock-selection]], [[skills/linux-kernel-tracing]], [[skills/linux-vm-debugging]]

综合分析：[[synthesis/linux-kernel-subsystem-interactions]]

## 来源

- [[summaries/linux-softirq-detail]] — softirq原理与ksoftirqd详解
- [[summaries/linux-rcu-lock]] — RCU softirq相关
- [[summaries/linux-network-protocol-stack-impl]] — NET_RX_SOFTIRQ在网络收包中的应用