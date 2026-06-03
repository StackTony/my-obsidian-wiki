---
title: Linux进程调度
category: concepts
tags: [linux, 内核, 调度器, CFS, 进程, 调度]
aliases: [CFS调度器, 进程调度器, vruntime, Linux调度]
relationships:
  - target: "[[concepts/linux-lock-mechanisms]]"
    type: uses
  - target: "[[concepts/linux-interrupt-system]]"
    type: related_to
  - target: "[[concepts/linux-namespace-cgroups]]"
    type: related_to
source_dir: Linux 操作系统/Linux 进程调度
source_files: [Linux 进程调度器.md, Linux 进程调度策略.md]
summary: Linux内核进程调度核心：CFS完全公平调度器使用红黑树按vruntime排序选择下一个进程。三种调度策略(SCHED_OTHER/FIFO/RR)，实时进程绝对优先于普通进程。
provenance:
  extracted: 0.60
  inferred: 0.30
  ambiguous: 0.10
base_confidence: 0.538
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: supporting
created: 2026-06-01
updated: 2026-06-01
---

# Linux进程调度

Linux进程调度器决定哪个进程在何时获得CPU时间，是内核最核心的决策引擎。CFS（完全公平调度器）自2.6.23引入后成为默认调度策略，用红黑树按vruntime排序实现"完全公平"的时间分配。三种调度策略覆盖不同场景，实时进程绝对优先于普通进程。

### 重要说明

来源文件总量约3.5KB，内容极为稀疏。本文推断比例（0.30）较高，部分内容基于对CFS原理的推断而非来源直接描述，置信度较低（base_confidence=0.538）。

## 核心观点

- CFS的核心思想是"完全公平"：所有进程应获得均等的CPU时间，用vruntime（加权虚拟运行时间）衡量进程已获得的CPU时间份额。
- CFS使用红黑树管理所有可运行进程，按vruntime排序，每次选择vruntime最小的进程投入运行——这保证了"最吃亏"的进程优先获得CPU。 ^[inferred]
- 三种调度策略覆盖不同需求：SCHED_OTHER（时间分享，普通进程）、SCHED_FIFO（实时无时间片，运行到主动让出）、SCHED_RR（实时有时间片，轮转）。
- 实时进程（SCHED_FIFO/RR）绝对优先于普通进程（SCHED_OTHER），只要有实时进程可运行，普通进程就无法获得CPU。 ^[inferred]

## 关键细节

### CFS 完全公平调度器

**核心设计原则**：
- 不使用固定时间片，而是通过vruntime追踪每个进程已获得的"加权CPU时间"
- 目标：让所有进程的vruntime尽可能接近——越接近越"公平"
- 实现：红黑树按键vruntime排序，O(log n)插入和查找最小值

**vruntime 计算**：
- `vruntime += 实际运行时间 × (NICE_0_LOAD / 进程权重)`
- nice值为0的进程权重为NICE_0_LOAD（1024），作为基准
- nice值越低（优先级越高）→ 权重越大 → 实际运行时间对vruntime贡献越小 → 在红黑树中位置越靠左 → 获得更多CPU时间
- nice值每变化1，权重变化约25%（非线性） ^[inferred]

**调度决策**：
1. 时钟中断触发 scheduler_tick()
2. 更新当前进程的vruntime
3. 如果当前进程的vruntime不再是红黑树中最小的，或已运行超过ideal_runtime
4. 触发抢占：选择红黑树中vruntime最小的进程投入运行

### 三种调度策略

| 策略 | 类别 | 时间片 | 适用场景 | 优先级范围 |
|------|------|--------|---------|-----------|
| SCHED_OTHER | 普通 | CFS动态分配 | 日常应用 | nice -20~19 (0~139映射) |
| SCHED_FIFO | 实时 | 无（运行到让出） | 紧急任务、不可中断 | 1~99 |
| SCHED_RR | 实时 | 固定（默认100ms） | 实时但需轮转 | 1~99 |

**SCHED_FIFO 行为**：
- 选择优先级最高的FIFO进程运行
- 该进程运行直到：主动调用sched_yield()、被更高优先级抢占、或阻塞等待IO
- 同优先级FIFO进程：当前进程让出后，按先进先出顺序选择下一个

**SCHED_RR 行为**：
- 与FIFO类似，但增加了时间片轮转
- 同优先级RR进程：时间片耗尽后轮转到下一个
- 时间片长度可通过 /proc/sys/kernel/sched_rr_timeslice_ms 配置

### 实时进程绝对优先

Linux的优先级体系：
- 实时优先级1~99（映射到内核优先级0~98）
- 普通优先级nice -20~19（映射到内核优先级100~139）
- 数值越小→优先级越高
- **关键规则**：只要存在可运行的实时进程（优先级<100），调度器绝不会选择普通进程运行 ^[inferred]

这意味着一个SCHED_FIFO优先级1的进程，即使nice=-20的普通进程也无法与之竞争CPU。

### 进程状态

| 状态 | 标识 | 含义 | 可调度 |
|------|------|------|--------|
| R (Running) | TASK_RUNNING | 正在运行或等待CPU | 是 |
| D (Disk sleep) | TASK_UNINTERRUPTIBLE | 不可中断的IO等待 | 否 |
| T (Stopped) | TASK_STOPPED | 被信号停止 | 否 |
| Z (Zombie) | TASK_DEAD - EXIT_ZOMBIE | 已退出但父进程未回收 | 否 |
| S (Sleeping) | TASK_INTERRUPTIBLE | 可中断的睡眠等待 | 否 |

### 上下文切换

上下文切换是调度器执行"进程换人"的核心操作：
- 保存当前进程的寄存器状态到其task_struct的内核栈
- 从新进程的内核栈恢复寄存器状态
- 切换地址空间（mm_struct，用户态进程）
- 更新TLS和FPU状态

上下文切换的开销通常在1-10微秒之间，频繁切换会显著降低系统性能。 ^[inferred]

### 调度域（Scheduling Domains）

调度域是多核系统中的调度层次结构：
- 每个调度域包含一组共享调度策略的CPU
- 域之间有层次关系：单核域 → 多核域 → NUMA域
- 负载均衡在域内优先进行，跨域负载均衡开销更大
- SMT（超线程）核被组织在最底层域中

## 未解问题

- CFS在极端负载（数千可运行进程）下的红黑树性能是否仍是瓶颈？O(log n)在n很大时开销可能显著。 ^[inferred]
- EEVDF（Earliest Eligible Virtual Deadline First）调度器是否会在未来版本中替代CFS？内核社区正在讨论。 ^[ambiguous]
- 组调度（group scheduling）与cgroups的交互——如何确保cgroup内的公平性与跨cgroup的公平性？ ^[ambiguous]


## 延伸阅读

实操指南：[[skills/linux-lock-selection]]

综合分析：[[synthesis/linux-kernel-subsystem-interactions]]

## 来源

- [[summaries/linux-softirq-detail]] — softirq与调度器的交互（scheduler_tick触发调度）
- [[summaries/linux-rcu-lock]] — RCU-sched基于调度上下文切换检测宽限期