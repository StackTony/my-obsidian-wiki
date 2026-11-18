---
title: tick 与 HZ（内核节拍）
category: concepts
tags: [linux, 内核, 定时器, tick, hz]
aliases: [jiffies, 节拍率, tickless, NO_HZ]
relationships:
  - target: "[[concepts/linux-process-scheduling]]"
    type: uses
  - target: "[[concepts/kernel-lockup-detection]]"
    type: related_to
  - target: "[[concepts/linux-interrupt-system]]"
    type: uses
source_dir: Linux 操作系统/Linux 时钟系统
source_files: [Linux 内核 tick 定时器.md]
summary: tick 是 HZ 频率的周期时钟中断，jiffies 是它的计数；它同时驱动调度检查点、时间维护与 timer_list 到期，HZ 与 tickless 决定精度和功耗的取舍。
provenance:
  extracted: 0.62
  inferred: 0.30
  ambiguous: 0.08
base_confidence: 0.44
lifecycle: draft
lifecycle_changed: 2026-11-17
tier: supporting
created: 2026-11-17
updated: 2026-11-17
---

# tick 与 HZ（内核节拍）

内核里"时间在走"的最底层证据是一个周期性中断：频率 `HZ`，每次中断叫一个 tick，中断次数记在 `jiffies` 里。调度器靠它检查是否该抢占，timekeeping 靠它推进系统时间，`timer_list` 与超时机制挂在它的到期检查后。理解 tick，等于拿到了内核所有"时间相关行为"的共同分母。

## 核心观点

- **三个名字一件事**：`tick`（事件）、`HZ`（频率，次/秒）、`jiffies`（累计次数，无符号长整型，会回绕）。tick 周期 = 1/HZ，HZ=100 时一个 tick 是 10 ms。
- **tick 是三个子系统的公共时钟**：调度器的 `scheduler_tick()`、时间维护（更新墙上时间与单调时间）、定时器到期扫描（`run_local_timers()`）。
- **tick 精度 ≠ 定时器精度**：`timer_list` 的到期分辨率受 jiffies 粒度限制，但需要亚毫秒精度的场景走的是 hrtimer（`HRTIMER_SOFTIRQ` / 硬中断），不靠加 HZ。 ^[inferred]
- **HZ 是编译期常数**，运行时不可改：改 HZ 要重编内核。`getconf CLK_TCK` 返回的是用户态 `USER_HZ`（恒为 100），**不是** 内核 `CONFIG_HZ`，这是最常见的混淆点。 ^[inferred]
- **tickless 不是没有时钟**：`NO_HZ` 只在 CPU 空闲（或只有一个任务，`NO_HZ_FULL`）时停掉周期性 tick，改由下一个到期事件把 CPU 唤醒；省电，但调度精度和统计口径随之变化。 ^[inferred]
- **tick 停摆是可观测的故障信号**：软锁检测看 watchdog 线程有没有被 tick 唤醒，硬锁检测看 tick 计数在 `watchdog_thresh` 内是否推进——见 [[concepts/kernel-lockup-detection]]。

## 关键细节

### tick 与用户态定时器的边界

| 维度 | tick / 内核定时器 | 用户态定时器 |
|---|---|---|
| 运行环境 | 内核空间，可访问硬件 | 用户空间，经系统调用 |
| 作用范围 | 全系统（调度、计时、中断） | 单个进程 |
| 精度来源 | `HZ` 粒度，或 hrtimer | `nanosleep`/`timerfd`，微秒至纳秒级 |
| 典型代表 | `timer_list`、hrtimer、watchdog | `sleep()`、`timerfd`、`setitimer` |

用户态 `sleep(2)` 与内核 tick 之间没有直接调用关系：前者最终落到 hrtimer/高精度唤醒，后者是系统级心跳。源文用 `sleep()` 示例对比两者，只说明"一个是用户循环、一个是硬件中断驱动"。

### tick 一次中断的职责

1. `scheduler_tick()` → 更新当前任务的运行时间，必要时置 `need_resched`
2. 更新 jiffies 与墙上时间（旧实现写 `xtime`，新实现走 timekeeper）
3. `run_local_timers()` → 处理到期的 hrtimer 与 `timer_list`（后者转 `TIMER_SOFTIRQ`）

### HZ 的取值与代价

- 常见 100 / 250 / 1000，桌面发行版多用 250 或 1000，服务器偏 100–250。 ^[inferred]
- 高 HZ：抢占与定时更及时，但每秒多出的中断与调度检查全是纯开销，对吞吐和功耗都不友好。
- 低 HZ：开销小，但 ms 级定时和调度响应的粒度变粗。
- 现代内核用 hrtimer + NO_HZ 把"精度"和"心跳频率"解耦，HZ 的取舍没有早期那么敏感。 ^[inferred]

### tickless（NO_HZ）三种形态

| 配置 | 行为 | 代价 |
|---|---|---|
| `CONFIG_NO_HZ_IDLE` | 仅空闲 CPU 停 tick | 唤醒延迟取决于下一个事件 |
| `CONFIG_NO_HZ_FULL` | 单个任务运行时也停 tick（需要 CPU 隔离配合） | 该 CPU 不做时钟记账，需 `nohz_full=` 指定核 |
| 无 NO_HZ | 永远周期 tick | 空闲功耗高，但时间统计最简单 |

源文提到的 `nohz=on` 启动参数与 `NO_HZ_MODE_LOWRES/HIGHRES` 命名与真实配置项不符 ^[ambiguous]，实际以 `CONFIG_NO_HZ_IDLE` / `CONFIG_NO_HZ_FULL` 与 `nohz_full=<cpulist>` 为准。 ^[inferred]

### 怎么观测

- `/proc/interrupts` 里的本地定时器中断计数在长，说明 tick 还在跑
- `dmesg` 里 softlockup/hardlockup 报警直接以 tick 是否推进为判据
- `CONFIG_HZ` 只能从内核配置读（`/boot/config-$(uname -r)` 中的 `CONFIG_HZ=`），不能从 `getconf` 推

## 未解问题

- hrtimer 全面接管后，周期性 tick 在 `NO_HZ_FULL` 之外还承担哪些不可替代的记账职责（负载统计、RCU 静默态判定）？现有来源未展开。
- `jiffies` 回绕（32 位约 49.7 天）对超时判断的影响，需要 `time_after` 系列宏的正确用法，来源未覆盖。
- tick 与 `sched_clock` / `clocksource` 的精度差异（`sched_clock` 可到 ns）在本 vault 尚无独立页面。

## 来源

- [[summaries/linux-tick-timer]] — 原始文档的蒸馏（HZ、硬件抽象、timer_list 链路、NO_HZ）
- 原始文档：`raw/sources/Linux 操作系统/Linux 时钟系统/Linux 内核 tick 定时器.md`
