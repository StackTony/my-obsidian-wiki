---
title: Linux 软锁 Softlockup 与硬锁 Hardlockup 的区别
category: summaries
tags: [linux, 内核, 死锁, watchdog, NMI]
aliases: [Softlockup, Hardlockup, 软死锁, 硬死锁, NMI watchdog]
relationships:
  - target: "[[concepts/kernel-lockup-detection]]"
    type: related_to
  - target: "[[concepts/linux-interrupt-system]]"
    type: related_to
  - target: "[[concepts/linux-process-scheduling]]"
    type: related_to
source_dir: Linux 操作系统/Linux 进程调度
source_files: [Linux 软锁Softlockup和硬锁Hardlockup区别.md]
summary: 软锁与硬锁对比：软锁是中断仍可响应但调度器切不走的 CPU 长时间占用（watchdog 线程 + tick 检查，2×watchdog_thresh）；硬锁是关中断死循环、只有 PMU 触发的 NMI 能探测（watchdog_thresh）。
provenance:
  extracted: 0.90
  inferred: 0.08
  ambiguous: 0.02
base_confidence: 0.47
lifecycle: draft
lifecycle_changed: 2026-11-13
tier: supporting
created: 2026-11-13
updated: 2026-11-13
---

# Linux 软锁 Softlockup 与硬锁 Hardlockup 的区别

两者都是 CPU 被长时间异常占用、无法处理其他任务的"卡死"状态，但分界线在**中断是否还能进入**：软锁是中断能跑、调度器切不走；硬锁是本地 IRQ 被关掉、只有 NMI 能进来。

## 核心观点

- **Softlockup：中断还能跑，调度切不动线程**（抢占关闭 / 内核死循环 / 自旋锁长时间持有）。
- **Hardlockup：本地 IRQ 直接关掉，tick 中断卡死，只能靠 NMI 来抓**。
- 共同点：都在**内核态**发生，都会让当前 CPU 长时间不返回调度器；区别不在"卡多久"，而在**检测者能否进入这个 CPU**。 ^[inferred]
- 软锁的检测者是 per-CPU `watchdog` 内核线程（SCHED_FIFO 最高优先级），硬锁的检测者是 PMU 触发的 NMI 处理函数。
- 默认 `watchdog_thresh=10`：软锁阈值 `2×watchdog_thresh`=20s，硬锁阈值 `watchdog_thresh`=10s。
- 严重度不同：软锁下 CPU 仍在处理中断，只是用户进程/其他内核线程跑不了；硬锁下本地中断通路失效，常规内核恢复手段失效。

## 关键细节

### 对比表

| 维度 | Soft Lockup（软死锁） | Hard Lockup（硬死锁 / NMI Watchdog） |
|------|----------------------|--------------------------------------|
| 根本原因 | CPU 在内核态**开启中断**的前提下长时间不主动调度（抢占关闭、死循环、自旋锁长时间持有），调度器无法切走当前上下文 | CPU **关中断（`local_irq_disable`）** 后死循环，普通中断完全无法进入，时钟中断也进不来 |
| 中断状态 | 可以响应硬件中断、时钟中断；只是调度器没机会跑 | 普通中断被屏蔽；**只有 NMI 能进来** |
| 检测主体 | per-CPU `watchdog` 内核线程（高优先级 SCHED_FIFO） | per-CPU NMI 处理函数（PMU 硬件计数器触发 NMI） |
| 检测逻辑 | watchdog 线程每次运行更新 `watchdog_touch_ts`；tick 中断检查距上次 touch 是否超过 `2*watchdog_thresh` | PMU 周期性触发 NMI；NMI 里检查上一次 NMI 到现在 tick 有没有前进，超时 `watchdog_thresh` 判定硬死锁 |
| 默认阈值 | `watchdog_thresh=10` → 软死锁 20s | `watchdog_thresh=10` → 硬死锁 10s |
| 严重度 | 较轻，CPU 还在处理中断；由 `softlockup_panic` 决定是否 panic | 极严重，本地 CPU 中断通路卡死；由 `hardlockup_panic` 控制 panic |
| 典型场景 | 自旋锁循环等待、内核大循环没加 `cond_resched`、抢占关闭长时间执行 | `spin_lock_irq`/`local_irq_disable` 之后死循环、硬件异常导致中断入口卡死 |

### Soft Lockup 检测链路

1. 每个 CPU 启动一个 SCHED_FIFO 最高优先级的 watchdog 线程。
2. 线程逻辑很简单：`touch_softlockup_watchdog()` 更新本 CPU 时间戳，然后睡眠。
3. **时钟中断（tick 中断上下文）**里做检查：读取当前时间，对比 `watchdog_touch_ts`，超过 `2*watchdog_thresh` 没更新就打印 soft lockup 栈回溯。

> 重点：**唤醒 watchdog 的不是 hrtimer，是调度器；tick 中断负责检查，不是唤醒**。只要中断还能进，tick 就能跑；但如果 CPU 一直跑在内核态、抢占关闭，调度器没有机会切到 watchdog 线程，时间戳就不会更新。

### Hard Lockup（NMI Watchdog）检测链路

> 前提：依赖硬件 PMU，部分虚拟机 / 部分 ARM 平台不支持 NMI watchdog。

1. 内核配置 PMU 硬件计数器，周期性触发 NMI（不可屏蔽中断，`local_irq_disable` 拦不住）。
2. NMI handler 里记录上一次 tick 计数并对比当前 tick；如果连续 `watchdog_thresh` 时间 tick 完全不增长，判定硬死锁。
3. 为什么不用普通中断：硬死锁场景就是本地 IRQ 被关掉，tick 中断根本进不来，tick 计数器停滞。

> 误区纠正：不是去查 hrtimer 计数器，是看全局 tick 有没有推进；NMI 是唯一能在关 IRQ 场景下跑的探查入口。

## 未解问题

- `watchdog_thresh` 设为 0 时是"关闭检测"还是"关闭 watchdog 线程"，不同内核版本文档口径不一。 ^[ambiguous]
- 无 PMU 的虚拟机 / ARM 平台上硬锁检测的替代实现（pseudo-NMI、perf NMI）来源未覆盖。 ^[inferred]
- 软锁阈值取 `2×watchdog_thresh`、硬锁取 `1×watchdog_thresh` 的原因，原文未解释。 ^[inferred]
- lockup 与 hung_task（D 状态不运行）、RCU stall 的告警边界与优先级，需要额外来源。 ^[inferred]

## 来源

- `raw/sources/Linux 操作系统/Linux 进程调度/Linux 软锁Softlockup和硬锁Hardlockup区别.md` — 原文（5KB 技术笔记，2026-11-13 ingest）
- 概念整合：[[concepts/kernel-lockup-detection]]
