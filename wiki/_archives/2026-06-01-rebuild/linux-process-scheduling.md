---
title: Linux 进程调度
created: 2026-06-01
updated: 2026-06-01
tags: [linux, kernel, scheduler, CFS, process, scheduling]
category: concepts
source_dir: Linux 操作系统/Linux 进程调度
source_files: [Linux 进程调度器.md, Linux 进程调度策略.md]
summary: Linux内核进程调度核心：CFS完全公平调度器的红黑树机制与三种调度策略
base_confidence: 0.7
lifecycle: draft
lifecycle_changed: "2026-06-01"
tier: supporting
provenance:
  extracted: 0.6
  inferred: 0.3
  ambiguous: 0.1
relationships:
  - target: "[[concepts/linux-interrupt-system]]"
    type: uses
  - target: "[[concepts/linux-lock-mechanisms]]"
    type: uses
---

# Linux 进程调度

Linux 内核进程调度器负责决定哪个进程获得 CPU 时间以及何时进行进程切换，是多任务操作系统的核心组件。

## 两种调度器类型

- **主调度器**：进程因睡眠或其他原因主动放弃 CPU 时触发
- **周期性调度器**：以固定频率运行，检测是否有必要进行进程切换

两种调度器协同工作，前者响应主动让出，后者保证公平性。 ^[inferred]

## CFS 完全公平调度器

CFS（Completely Fair Scheduler）是 Linux 默认的调度策略，核心机制：

- **红黑树**：所有可运行进程按 `vruntime` 排序，树中最左节点即为下一个调度目标
- **vruntime（虚拟运行时间）**：综合考虑进程执行时间和优先级，nice 值越小权重越高，vruntime 增长越慢
- **调度策略**：选择 `vruntime` 最小的进程运行，实现"公平"分配 CPU 时间

nice 值影响权重，高优先级进程的 vruntime 增长更慢，从而获得更多 CPU 时间。 ^[inferred]

## 三种主要调度策略

| 策略 | 类型 | 特点 |
|------|------|------|
| SCHED_OTHER | 分时调度 | 普通进程默认策略，基于 nice 和 counter 值决定权值 |
| SCHED_FIFO | 实时调度 | 先到先服务，一直运行直到主动让出或被更高优先级抢占 |
| SCHED_RR | 实时调度 | 时间片轮转，每个进程分配固定时间片 |

实时进程优先于分时进程，实时优先级决定调度顺序；分时进程通过 nice（越小优先级越高）和 counter（曾使用 CPU 越少优先级越高）决定权值。

## 调度类层次结构

内核定义多种调度类，按优先级从高到低：实时调度类 > 公平调度类（CFS）> 空闲调度类。每个调度类有自己的调度策略和数据结构。 ^[inferred]

## 抢占与上下文切换

Linux 是可抢占操作系统，高优先级进程可中断低优先级进程执行。当调度器决定切换进程时：
1. 保存当前进程上下文（寄存器状态）
2. 加载新进程上下文
3. 跳转到新进程执行

调度依赖 [[concepts/linux-interrupt-system]] 实现定时触发，并使用 [[concepts/linux-lock-mechanisms]] 保护调度数据结构。系统启动时 [[concepts/linux-boot-shutdown]] 创建 init 进程（PID=1），这是调度器管理的第一个用户空间进程。

## 关键数据结构

- **调度实体**：`task_struct`，包含调度策略、优先级、vruntime 等信息
- **等待队列**：管理等待特定事件的进程，事件发生时唤醒并加入调度
- **调度域**：一组共享相同调度策略的 CPU，用于跨 CPU 负载均衡

## 未解问题

- CFS 在 NUMA 架构下的调度域如何优化？
- 实时调度策略的截止时间保证如何实现？

## 来源

- Linux 进程调度器.md — CFS 机制与调度器组件
- Linux 进程调度策略.md — 三种调度策略详解