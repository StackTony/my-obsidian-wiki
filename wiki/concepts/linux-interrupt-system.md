---
title: Linux中断系统
category: concepts
tags: [linux, 中断, 内核, softirq]
aliases: [Linux IRQ, Linux软中断]
relationships:
  - target: "[[concepts/linux-lock-mechanisms]]"
    type: uses
  - target: "[[concepts/linux-process-scheduling]]"
    type: related_to
  - target: "[[concepts/linux-network-stack]]"
    type: uses
source_dir: Linux 操作系统/Linux 中断系统
source_files: [Linux 硬中断irq + 软中断softirq原理.md, Linux 软中断softirq.md, Linux ksoftirqd软中断内核线程详解.md, Linux IPI 核间中断.md]
summary: Linux中断分上下半部：硬中断(IRQ)上半部快速响应，软中断(softirq)下半部延迟处理。三种延迟机制对比及preempt_count跟踪中断上下文。
provenance:
  extracted: 0.75
  inferred: 0.20
  ambiguous: 0.05
base_confidence: 0.775
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: supporting
created: 2026-06-01
updated: 2026-06-01
---

# Linux中断系统

## 核心观点

### 中断上下半部设计

Linux中断处理分为两个阶段以平衡响应速度和处理复杂度：

- **硬中断(IRQ/ISR)上半部**：由GIC触发，CPU硬件跳转到固定地址执行，期间关本地中断响应，仅处理寄存器设置等关键操作，必须快速完成^[inferred]
- **软中断(softirq)下半部**：ISR执行完后进入，此时开本地中断响应，可被新硬件中断打断，但不会被本CPU上其他任务抢占

这种设计解决了传统中断处理"执行要快"与"逻辑复杂"的内在矛盾。

### preempt_count机制

`current_thread_info()->preempt_count`变量跟踪当前运行上下文，是理解中断系统的关键：

| 值 | 上下文 | 抢占性 |
|---|---|---|
| 0 | 进程上下文 | 可抢占 |
| HARDIRQ_OFFSET | 硬中断上下文 | 不可抢占 |
| SOFTIRQ_OFFSET | 软中断上下文 | 不可抢占 |

在中断返回时(`__irq_svc`)，内核检查`preempt_count==0`且`flags==TIF_NEED_RESCHED`才执行调度切换。软中断通过`add_preempt_count(SOFTIRQ_OFFSET)`保证在本CPU不被抢占。

### 三种延迟机制对比

| 特性 | softirq | tasklet | workqueue |
|---|---|---|---|
| 机制类型 | 静态(编译期确定) | 动态(基于softirq) | 动态(内核进程) |
| 运行上下文 | 软中断上下文 | 软中断上下文 | 进程上下文(可睡眠) |
| 并行性 | 可多核并行 | 同类型串行 | 可配置 |
| 使用场景 | 网络收发、定时器等高频 | 驱动中断延迟处理 | 需要睡眠的复杂处理 |

内核仅9种静态softirq(HI_SOFTIRQ/TIMER_SOFTIRQ/NET_TX_SOFTIRQ/NET_RX_SOFTIRQ/BLOCK_SOFTIRQ等)，通过`open_softirq()`注册handler。

### ksoftirqd兜底与限制机制

每个CPU一个ksoftirqd内核线程，当软中断过多时兜底处理：

- **MAX_SOFTIRQ_TIME**：软中断处理不超过2 jiffies(约10ms)
- **MAX_SOFTIRQ_RESTART**：循环重启不超过10次
- 超过限制则唤醒ksoftirqd在进程上下文处理，避免软中断霸占CPU^[inferred]

### 核间中断(IPI)

IPI用于多核通信，通过ICR寄存器发起，典型场景包括：调度迁移、缓存同步、TLB刷新等^[ambiguous]。

## 未解问题

- 不同架构(x86/ARM)的中断控制器实现差异如何影响softirq行为？
- RTLinux实时补丁对中断处理的改进机制？

## 来源

- `raw/sources/Linux 操作系统/Linux 中断系统/Linux 硬中断irq + 软中断softirq原理.md` — preempt_count机制、tasklet串行原理
- `raw/sources/Linux 操作系统/Linux 中断系统/Linux 软中断softirq.md` — 三种延迟机制对比、ksoftirqd设计
- `raw/sources/Linux 操作系统/Linux 中断系统/Linux ksoftirqd软中断内核线程详解.md` — MAX_SOFTIRQ_TIME限制、__do_softirq流程
- `raw/sources/Linux 操作系统/Linux 中断系统/Linux IPI 核间中断.md` — ICR寄存器