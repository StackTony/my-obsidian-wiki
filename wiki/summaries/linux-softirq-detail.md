---
title: Linux 软中断机制详解
created: 2026-06-01
updated: 2026-06-01
tags: [linux, kernel, softirq, interrupt, ksoftirqd]
category: summaries
source_dir: Linux 操作系统/Linux 中断系统
source_files: [Linux 软中断softirq.md, Linux ksoftirqd软中断内核线程详解.md]
summary: Linux软中断的完整实现：preempt_count防抢占机制、__do_softirq执行流、ksoftirqd溢出处理
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: "2026-06-01"
tier: supporting
---

# Linux 软中断机制详解

Linux 中断处理分为两阶段：ISR（硬中断）快速响应，softirq（软中断）异步处理后续工作。这种设计提前打开中断响应，提高系统响应能力。

## preempt_count 防抢占机制

软中断执行期间必须防止被本核其他任务抢占，通过 `preempt_count` 变量实现。当执行 softirq 时，调用 `__local_bh_disable` 将 preempt_count 加上 SOFTIRQ_OFFSET，标记处于软中断上下文。此时即使 tick 中断触发调度检查，由于 preempt_count 不为零，中断返回时不会切换线程。软中断结束后恢复 preempt_count，重新允许抢占。

同一机制也用于 spinlock 的核内锁调度。^[inferred]

## softirq_vec 与 tasklet_vec

内核初始化时创建 `softirq_vec` 全局数组，每项对应一种软中断类型及其 action 处理函数。如 TASKLET_SOFTIRQ 的 action 为 tasklet_action。`tasklet_vec` 是 per-CPU 变量，每个核维护独立的任务链表。

使用时通过 `tasklet_init` 创建任务，`tasklet_schedule` 将其提交到当前核的 tasklet_vec，并设置 `__softirq_pending` 位。

## __do_softirq 执行流

ISR 结束后进入 softirq 阶段，`__do_softirq` 执行：

1. 获取 pending 位图，清除软中断寄存器
2. 设置 preempt_count 进入软中断上下文
3. **打开中断** — 允许新 ISR 打断
4. 循环执行 pending 位对应的 softirq_vec action
5. 关闭中断，再次检查 pending
6. 若仍有 pending 且满足条件（时间 < 2 jiffies、循环 < 10 次），重试；否则唤醒 ksoftirqd

打开中断后若被新中断打断，新 ISR 的 do_softirq 会因 `in_interrupt()` 检测到已处于软中断上下文而直接退出，返回原执行流。

## ksoftirqd 溢出处理

每个 CPU 绑定一个 ksoftirqd 内核线程（如 `ksoftirqd/0`）。当软中断负载过高、__do_softirq 重试条件不满足时，唤醒 ksoftirqd 处理剩余任务。它本质是调用 `__do_softirq`，提供后台处理通道，避免软中断占用过多 CPU 时间。

## 监测与关键约束

通过 `/proc/softirqs` 查看各核各类软中断计数。top 命令的 si 字段统计软中断 CPU 使用量。

关键约束：
- 同一 tasklet 不能跨核并行执行（通过 TASKLET_STATE_SCHED 和 TASKLET_STATE_RUN 状态保证）
- 临界区保护：本核无竞争（关抢占），跨核需 spin_lock；进程访问可用 spin_lock_bh 关软中断而非粗暴关中断

## 来源

- `Linux 操作系统/Linux 中断系统/Linux 软中断softirq.md` — preempt_count 机制与 tasklet 流程
- `Linux 操作系统/Linux 中断系统/Linux ksoftirqd软中断内核线程详解.md` — ksoftirqd 触发条件与 __do_softirq 代码分析

## 相关概念

- [[concepts/linux-interrupt-system]] — 中断系统整体架构
- [[concepts/linux-lock-mechanisms]] — spinlock 与 preempt_count 的关系