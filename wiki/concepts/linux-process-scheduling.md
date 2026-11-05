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
  - target: "[[concepts/red-black-tree]]"
    type: uses
source_dir: Linux 操作系统/Linux 进程调度
source_files: [Linux 进程调度器.md, Linux 进程调度策略.md, Linux CFS调度器.md, Linux 完全公平调度器CFS.md]
summary: Linux内核进程调度：CFS用红黑树按vruntime选下一个进程，五个调度类(stop>dl>rt>fair>idle)决定优先级层级，实时进程绝对优先于普通进程，六种调度策略覆盖不同场景。
provenance:
  extracted: 0.72
  inferred: 0.22
  ambiguous: 0.06
base_confidence: 0.77
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: core
created: 2026-06-01
updated: 2026-10-21
---

# Linux进程调度

Linux进程调度器决定哪个进程在何时获得CPU时间，是内核最核心的决策引擎。CFS（完全公平调度器）自2.6.23引入后成为默认调度策略，用[[concepts/red-black-tree|红黑树]]按vruntime排序实现"完全公平"的时间分配。调度优先级由**五个调度类**的层级决定，实时进程绝对优先于普通进程。

### 重要说明

早期来源仅约3.5KB，内容稀疏；本次 ingest 补入两篇 CFS 源码分析（`Linux CFS调度器.md`、`Linux 完全公平调度器CFS.md`），补齐了 vruntime 换算公式、调度周期/粒度、`cfs_rq`/`sched_class` 结构与调度类优先级体系，置信度由 0.538 提升至 0.77。实现层细节见 [[summaries/linux-cfs-scheduler-impl]]。

## 核心观点

- CFS的核心思想是"完全公平"：所有进程应获得均等的CPU时间，用vruntime（加权虚拟运行时间）衡量进程已获得的CPU时间份额。
- CFS使用红黑树管理所有可运行进程，按vruntime排序，每次选择vruntime最小的进程投入运行——这保证了"最吃亏"的进程优先获得CPU。 ^[inferred]
- **调度是分层的**：内核不直接在进程之间比较优先级，而是先比较**调度类**（`sched_class`）。五个调度类优先级严格有序：`stop > dl > rt > fair > idle`，只有高优先级类无可运行任务时才会落到下一层。
- 用户可见的调度策略有六种（`SCHED_NORMAL/FIFO/RR/BATCH/IDLE/DEADLINE`），日常讨论通常只关注其中三种（`SCHED_OTHER/FIFO/RR`）——**SCHED_OTHER 就是 SCHED_NORMAL 的用户态别名**。 ^[ambiguous]
- 实时进程（SCHED_FIFO/RR）绝对优先于普通进程（SCHED_OTHER），只要有实时进程可运行，普通进程就无法获得CPU。 ^[inferred]
- CFS 的"公平"只对普通进程成立：deadline 与 real-time 类不参与 vruntime 竞争，它们靠各自的调度类抢占 fair 层。

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

### 调度类与优先级体系

调度器的第一层判断不是"哪个进程优先级高"，而是"哪个**调度类**有活干"：

```
stop_sched_class > dl_sched_class > rt_sched_class > fair_sched_class > idle_sched_class
```

| 调度类 | 负责的策略 | 说明 |
|--------|-----------|------|
| `stop_sched_class` | — | 最高优先级，供 CPU 停机/热插拔等内核内部动作使用 |
| `dl_sched_class` | SCHED_DEADLINE | 截止时间调度（EDF） |
| `rt_sched_class` | SCHED_FIFO / SCHED_RR | 实时进程 |
| `fair_sched_class` | SCHED_NORMAL / SCHED_BATCH | CFS，普通进程 |
| `idle_sched_class` | （无用户态策略） | 无用户态入口，仅服务于每 CPU 的 idle 线程（swapper） |

**优先级数值范围**（数字越小优先级越高）：

| 类别 | 范围 | 常量 |
|------|------|------|
| 实时 | 0 ~ 99 | `MAX_USER_RT_PRIO = 100` |
| 普通 | 100 ~ 139 | `MAX_PRIO = MAX_RT_PRIO + NICE_WIDTH = 140` |
| 默认（nice 0） | 120 | `DEFAULT_PRIO = MAX_RT_PRIO + NICE_WIDTH/2` |

### 六种调度策略

| 策略 | 枚举值 | 调度类 | 时间片 | 适用场景 |
|------|--------|--------|--------|---------|
| SCHED_NORMAL（= SCHED_OTHER） | 0 | fair | CFS 动态分配 | 日常应用 |
| SCHED_FIFO | 1 | rt | 无（运行到让出） | 紧急任务、不可中断 |
| SCHED_RR | 2 | rt | 固定（默认 100ms） | 实时但需轮转 |
| SCHED_BATCH | 3 | fair | CFS 动态分配 | 批处理，不抢占交互任务 |
| SCHED_IDLE | 5 | fair（极小权重） | CFS 动态分配 | 最低优先级后台任务 |
| SCHED_DEADLINE | 6 | dl | 按 runtime/deadline/period | 硬实时 |

> **口径差异**：早期来源只列三种策略（OTHER/FIFO/RR），内核 `sched.h` 的枚举实际有六个值。二者不矛盾——SCHED_OTHER 是 SCHED_NORMAL 的用户态别名，其余三种是后期加入的扩展。 ^[ambiguous]
>
> **命名与实现的两处落差**（易踩坑）：① `SCHED_IDLE` 策略在主线上由 `fair_sched_class` 以极小权重实现，而 `idle_sched_class` 服务的是每 CPU 的 idle 线程——**策略名与调度类名并不对应**；② `SCHED_NORMAL` 与 `SCHED_OTHER` 是同一个值（0）的两个名字。 ^[ambiguous]

**SCHED_FIFO 行为**：
- 选择优先级最高的FIFO进程运行
- 该进程运行直到：主动调用sched_yield()、被更高优先级抢占、或阻塞等待IO
- 同优先级FIFO进程：当前进程让出后，按先进先出顺序选择下一个

**SCHED_RR 行为**：
- 与FIFO类似，但增加了时间片轮转
- 同优先级RR进程：时间片耗尽后轮转到下一个
- 时间片长度可通过 /proc/sys/kernel/sched_rr_timeslice_ms 配置

### CFS 实现要点

**vruntime 与调度周期**：

```
runtime  = 调度周期 × 进程权重 / 所有进程权重之和
vruntime = runtime × nice_0_weight / weight        # nice_0_weight = 1024
```

源码通过 `sched_slice()` / `sched_vslice()` 计算，用定点乘法避开除法：`vruntime = (runtime * weight * lw->inv_weight) >> WMULT_SHIFT`。

| 条件 | 调度周期 | 调度粒度 |
|------|----------|----------|
| 单 CPU，就绪任务 ≤ 8 | 6 ms | 0.75 ms |
| 单 CPU，就绪任务 > 8 | 按粒度累加 | 0.75 ms |
| 多 CPU | × (1 + log2(ncpus)) | 同样放大 |

8 核机器：粒度 = 0.75 ms × (1 + log2 8) = 3 ms，调度周期 = 6 ms × 4 = 24 ms。 ^[inferred]

**核心数据结构**：

- `struct rq`（每 CPU 一个运行队列）→ 内含各调度类子队列
- `struct cfs_rq`：`load`、`nr_running`、`min_vruntime`、`tasks_timeline`（红黑树根）、`rb_leftmost`、`curr/next/last/skip`、`sched_avg`
- `struct sched_entity`：调度实体（进程或进程组），CFS 直接排序的对象
- `struct sched_class`：函数指针表，`enqueue_task` / `dequeue_task` / `pick_next_task` / `task_tick` / `task_fork` / `yield_task` / `put_prev_task` / `switched_to` 等

**关键函数**：

| 函数 | 作用 |
|------|------|
| `update_curr()` | 按实际运行时间累加当前实体的 vruntime |
| `task_fork_fair()` | 子进程 vruntime 对齐父进程并做补偿，避免刚 fork 就饿死 |
| `pick_next_task_fair()` | 取红黑树最左节点（`rb_leftmost`）→ 接近 O(1) |
| `task_tick_fair()` | 时钟中断驱动的周期性检查 |
| `yield_task_fair()` | 打 `skip` 标记并放回红黑树**最右端** |

实现层完整梳理见 [[summaries/linux-cfs-scheduler-impl]]。

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

- CFS在极端负载（数千可运行进程）下的红黑树性能是否仍是瓶颈？`rb_leftmost` 缓存缓解了取最小值，但插入仍是 O(log n)。 ^[inferred]
- EEVDF（Earliest Eligible Virtual Deadline First）调度器是否会在未来版本中替代CFS？内核社区正在讨论。 ^[ambiguous]
- 组调度（group scheduling）与cgroups的交互——`task_group` 的层级权重换算、`CONFIG_CFS_BANDWIDTH` 限流（`throttled` 字段）的完整状态机，现有来源均未展开。 ^[ambiguous]
- `sched_entity` 的 PELT 负载跟踪（`sched_avg`）只有字段名，缺少算法推导与半衰期含义。 ^[inferred]


## 延伸阅读

实操指南：[[skills/linux-lock-selection]]

综合分析：[[synthesis/linux-kernel-subsystem-interactions]]

## 来源

- [[summaries/linux-cfs-scheduler-impl]] — CFS 实现细节（vruntime 公式、cfs_rq/sched_class、调度类优先级）
- [[summaries/linux-softirq-detail]] — softirq与调度器的交互（scheduler_tick触发调度）
- [[summaries/linux-rcu-lock]] — RCU-sched基于调度上下文切换检测宽限期
- `raw/sources/Linux 操作系统/Linux 进程调度/Linux CFS调度器.md`（原文：zhuanlan.zhihu.com/p/556295381）
- `raw/sources/Linux 操作系统/Linux 进程调度/Linux 完全公平调度器CFS.md`（原文：zhuanlan.zhihu.com/p/500583213）