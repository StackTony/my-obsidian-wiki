---
title: 内核 Lockup 检测（软锁与硬锁）
category: concepts
tags: [linux, 内核, 死锁, watchdog, NMI]
aliases: [Lockup检测, 软死锁, 硬死锁, softlockup, hardlockup, watchdog_thresh]
relationships:
  - target: "[[concepts/linux-interrupt-system]]"
    type: uses
  - target: "[[concepts/linux-process-scheduling]]"
    type: uses
  - target: "[[concepts/linux-lock-mechanisms]]"
    type: related_to
  - target: "[[summaries/linux-softlockup-hardlockup]]"
    type: related_to
  - target: "[[concepts/linux-tick-and-hz]]"
    type: related_to
source_dir: Linux 操作系统/Linux 进程调度
source_files: [Linux 软锁Softlockup和硬锁Hardlockup区别.md]
summary: CPU 在内核态长时间不返回的两种检测：softlockup 靠 per-CPU watchdog 线程 + tick 检查（2×watchdog_thresh），hardlockup 靠 PMU 触发 NMI 检查 tick 是否推进（watchdog_thresh），阈值与 panic 行为均可调。
provenance:
  extracted: 0.65
  inferred: 0.29
  ambiguous: 0.06
base_confidence: 0.47
lifecycle: draft
lifecycle_changed: 2026-11-13
tier: supporting
created: 2026-11-13
updated: 2026-11-17
---

# 内核 Lockup 检测（软锁与硬锁）

Lockup 指某个 CPU 在内核态长时间不返回调度器，导致该核上的任务（包括内核线程）得不到执行。Linux 用两套 watchdog 分别覆盖"中断还能进"和"中断进不来"两种情形：[[concepts/linux-interrupt-system]] 提供中断通路，[[concepts/linux-process-scheduling]] 提供 watchdog 线程的运行机会。

## 核心观点

- **分类依据是中断状态，不是持续时间**：软锁 = 中断可响应、调度器切不走；硬锁 = 本地 IRQ 关闭、只有 NMI 能进。^[inferred]
- **软锁检测是"线程 + tick"协作**：watchdog 线程负责 touch 时间戳，tick 中断负责比较；线程被调度是前提，所以抢占关闭/死循环才是根因。
- **硬锁检测绕开中断控制器**：PMU 周期性产生 NMI，NMI 在 lockup 检测中的 handler 只做 tick 推进检查；不依赖本地 IRQ 通路。
- **同一个旋钮控制两个阈值**：`watchdog_thresh` 默认 10s，软锁取 2 倍、硬锁取 1 倍。
- **检测能力受硬件约束**：没有 PMU 的虚拟机或部分 ARM 平台无法启用 NMI watchdog，硬锁可能完全无告警。^[inferred]

## 关键细节

### 两类检测的判定条件

| 检测器 | 运行上下文 | 判定条件 | 默认触发时间 |
|--------|-----------|----------|--------------|
| softlockup | per-CPU watchdog 内核线程（SCHED_FIFO）+ tick 中断检查 | `now - watchdog_touch_ts > 2 × watchdog_thresh` | 20s |
| hardlockup | per-CPU NMI handler（PMU 计数触发） | 连续 `watchdog_thresh` 时间内 tick 计数不增长 | 10s |

### 判定所依赖的 tick 从哪里来

两类检测的共同裁判是 **tick 是否推进**，所以先要清楚 tick 本身由什么驱动：`clock_event_device` 按 HZ 编程周期中断，每次中断在本地 CPU 上推进 jiffies，并顺带唤醒 watchdog 做检查。这条链路的细节见 [[concepts/linux-tick-and-hz]] 与 [[concepts/clocksource-and-clockevent]]。

由此可以推出两条排查含义 ^[inferred]：

- **clockevent 坏了，lockup 检测会一起哑**：如果时钟中断本身投递不到（不是被屏蔽，而是设备/路由问题），tick 停了，软锁检测拿不到"tick 在走"的证据，NMI 也会报 hardlockup——此时先查定时器与中断投递，而不是软件死锁。
- **hrtimer 在跑 ≠ tick 在跑**：判定比较的是 jiffies/全局 tick，不是 hrtimer 队列是否推进；高精度定时器可以靠一次性事件维持，但周期 tick 已经停摆。

### 软锁：watchdog 线程为什么可能跑不到

watchdog 线程虽然是最高的 SCHED_FIFO 优先级，但它的运行仍要经过调度器：

- CPU 在内核态持有 spinlock 并关闭抢占时，`need_resched` 置位也不会切换。
- 内核大循环没有插入 `cond_resched()`，同样不给调度器机会。
- 中断仍然照常进入，tick 也照常触发——所以**检测者（tick）活着，被检测者（watchdog 线程）饿死**，这正是软锁可被检测到的原因。

反过来，如果连 tick 都进不来（关中断死循环），软锁检测也失效，必须由 NMI 兜底。

### 硬锁：NMI 为什么能进来

NMI（Non-Maskable Interrupt）不受 `local_irq_disable()` 影响，CPU 不能通过常规中断屏蔽位拒绝它。其检测链路：

1. PMU 编程一个周期性事件（如固定的 unhalted cycles），溢出时产生 NMI。
2. NMI handler 读取当前 tick 计数，与上次记录比较。
3. 若 `watchdog_thresh` 时间内 tick 未推进，说明时钟中断已经无法投递，判定 hard lockup 并打印栈回溯。

注意判定对象是**全局 tick 是否推进**，不是 hrtimer 计数器——这是原文明确纠正的误区。

### 阈值与处置旋钮

| 旋钮 | 作用 | 来源 |
|------|------|------|
| `watchdog_thresh` | 两个检测器的基准阈值，默认 10s；软锁 ×2、硬锁 ×1 | 原文 |
| `softlockup_panic` | 软锁时是否 panic | 原文 |
| `hardlockup_panic` | 硬锁时是否 panic | 原文 |
| `watchdog_cpumask` / `nmi_watchdog` | 控制检测覆盖的 CPU、开关 NMI watchdog | 补充 ^[inferred] |
| `softlockup_all_cpu_backtrace` / `hardlockup_all_cpu_backtrace` | 触发时是否抓取所有 CPU 的栈 | 补充 ^[inferred] |

### 与相邻问题的边界

- **hung_task**：检测的是任务处于 `TASK_UNINTERRUPTIBLE`（D 状态）超时，CPU 可能仍在正常跑其他任务；lockup 检测的是 CPU 本身不返回。^[inferred]
- **RCU stall**：宽限期长时间不结束，可能是 CPU 关中断、也可能只是任务长期不主动调度；与软锁有重叠但不等价。^[inferred]
- **spinlock 长时间持有**：是软锁的典型根因（见 [[concepts/linux-lock-mechanisms]]）；`spin_lock_irqsave` 后再死循环则直接落入硬锁场景。

### 排查入口

- `dmesg` 关键字：`BUG: soft lockup`、`Watchdog detected hard LOCKUP`。
- 线程名 `watchdog/N` 对应 CPU N，`ps -eLo pid,tid,cls,rtprio,comm` 可确认其 SCHED_FIFO 优先级。^[inferred]
- 调整阈值前先确认 NMI watchdog 是否可用（x86 看 `nmi_watchdog`），否则硬锁告警永远不会出现。^[inferred]

## 未解问题

- `watchdog_thresh=0` 的语义（关闭检测 / 关闭线程 / 使用默认）在不同版本文档中口径不一。 ^[ambiguous]
- ARM64 的 pseudo-NMI 与 PMU 缺失时的替代检测路径，来源未覆盖，需要新资料校准。 ^[inferred]
- 软锁 20s、硬锁 10s 的倍率设计原因（给 tick 抖动留余量？）原文未解释。 ^[inferred]
- 在 PREEMPT_RT 下 watchdog 线程被线程化中断影响后的阈值语义是否变化，尚不清楚。 ^[inferred]

## 来源

- `raw/sources/Linux 操作系统/Linux 进程调度/Linux 软锁Softlockup和硬锁Hardlockup区别.md` — 原始技术笔记（2026-11-13 ingest）
- 蒸馏摘要：[[summaries/linux-softlockup-hardlockup]]
