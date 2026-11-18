---
title: Linux 内核 tick 定时器
category: summaries
tags: [linux, 内核, 定时器, tick, 中断]
aliases: [tick定时器, 内核节拍, 时钟节拍]
relationships:
  - target: "[[concepts/linux-tick-and-hz]]"
    type: related_to
  - target: "[[concepts/kernel-timer-wheel]]"
    type: related_to
source_dir: Linux 操作系统/Linux 时钟系统
source_files: [Linux 内核 tick 定时器.md]
summary: tick 定时器全景：HZ/节拍定义、clocksource/clockevent 硬件抽象、timer_list 五级时间轮注册-触发-销毁链路、NO_HZ 与 HZ 取舍。
provenance:
  extracted: 0.70
  inferred: 0.20
  ambiguous: 0.10
base_confidence: 0.44
lifecycle: draft
lifecycle_changed: 2026-11-17
tier: supporting
created: 2026-11-17
updated: 2026-11-17
---

# Linux 内核 tick 定时器

一句话：tick 是内核按固定频率 `HZ` 产生的时钟中断，是调度、时间维护、定时器三者共用的时间基准；本文从概念讲到 `timer_list` 的注册/触发/销毁，再讲 HZ 与 NO_HZ 的性能取舍。

## 核心观点

- tick 是硬件定时器周期性中断的软件抽象：频率叫节拍率（HZ），一次中断叫一个 tick，周期 = 1/HZ。
- tick 承担三件事：给调度器提供抢占检查点（`scheduler_tick`）、推进系统时间与 jiffies、驱动到期定时器（`run_local_timers`）。
- tick 与用户态定时器不是一回事：内核空间 vs 用户空间、全系统 vs 单进程、精度受 HZ 限制（100 Hz → 10 ms）vs 可达微秒/纳秒级。
- 硬件定时器在内核里被拆成两个角色：**clocksource** 读计数换算时间、**clockevent** 产生中断；按 rating 择优注册。
- 内核定时器（`timer_list`）不等于 tick：tick 是触发源，`timer_list` 是挂在 tick 上的到期任务，最终在 `TIMER_SOFTIRQ` 中执行。
- HZ 是取舍而非常数：高 HZ 响应快但中断开销大；`NO_HZ`（tickless）在 CPU 空闲时停掉周期中断，把"固定心跳"换成"按需闹钟"。 ^[inferred]

## 关键细节

### 三个层次

| 层 | 组成 | 职责 |
|---|---|---|
| 硬件层 | ARM Generic / Global / Local Timer、SoC 厂商定时器 | 提供计数与中断信号 |
| 抽象层 | `clocksource` / `clockevent` / `tick_device` | 时间基准 + 中断产生 |
| 使用者 | `scheduler_tick`、jiffies 与系统时间、`timer_list` / hrtimer | 调度、计时、定时 |

ARM 通用定时器同时提供物理计数 `CNTPCT` 与虚拟计数 `CNTVCT`（64 位精度），在多核平台上还可能需要全局定时器做核间时间同步；设备树用 `compatible` 匹配驱动，再由驱动把硬件注册为 clocksource 与 clockevent。

### tick 中断里发生了什么

源文给出的调用链：

1. 时钟中断进入 → `run_local_timers()`
2. 先 `hrtimer_run_queues()` 处理高精度定时器队列
3. 若 `jiffies >= base->next_timer` → `raise_softirq(TIMER_SOFTIRQ)`
4. `run_timer_softirq()` → `__run_timers()` 逐个 `expire_timers()`
5. `call_timer_fn()` 在 `local_bh_disable()` 保护下执行回调

展开见 [[concepts/kernel-timer-wheel]]。

### 定时器的三级生命周期

- **注册**：`add_timer()` → `__mod_timer()`，按 `expires - jiffies` 算出的索引落到 5 级链表的某一槽位，全程持 `base->lock` 自旋锁；已超时的定时器直接执行而不入链。
- **触发**：由 tick 推进，走 `TIMER_SOFTIRQ`，从链表头开始处理到期者。
- **销毁**：`del_timer()` 只摘链（回调可能正在别的 CPU 上跑）；`del_timer_sync()` 等到所有 CPU 上的回调退出——必须在进程上下文调用且不能持有自旋锁，否则与正在等锁的回调互相等待而死锁。

### 应用场景（源文举例）

- 进程调度：tick 提供检查点，时间片或虚拟运行时间到期触发切换
- 时间管理：tick 推进系统时间、文件时间戳
- 网络协议：TCP 超时重传的定时基准
- 设备驱动：串口等设备的定时轮询

### 性能旋钮

- HZ：100 / 250 / 1000，编译期选择（menuconfig 的 "Timer frequency"）
- NO_HZ：空闲时停 tick；源文提到 `NO_HZ_MODE_LOWRES` / `NO_HZ_MODE_HIGHRES` 两种模式 ^[ambiguous]
- CFS 粒度参数：`sched_min_granularity_ns`、`sched_wakeup_granularity_ns`
- tuned profile 批量调整（如 `throughput-performance`、`virtual-guest`）

## 未解问题

- 源文的源码示例横跨多个内核版本：`tvec_base`、`setup_timer`、`xtime` 都是旧接口（`xtime` 自 2.6.24 起被 timekeeper 取代，`setup_timer` 自 4.15 起被 `timer_setup` 取代） ^[inferred]。当前 time wheel 是 8 级 per-CPU `timer_base` 带 bitmap ^[inferred]，本页保留源文语义，未按新版本改写。
- §3.1 的 `scheduler_tick` 示例用 `time_slice` 递减，属 O(1) 调度器时代写法，与同节 CFS 的 vruntime 叙述不是同一版本 ^[ambiguous]。
- 源文给出的 NO_HZ 配置名与启动参数（`nohz=on`）与真实内核配置项（`CONFIG_NO_HZ_IDLE` / `CONFIG_NO_HZ_FULL`）不一致 ^[ambiguous]。
- tick 与 hrtimer 的分工边界（何时由 hrtimer 接替周期 tick）源文只有 `hrtimer_run_queues()` 一句，需要新来源补齐。

## 来源

- 原始文档：`raw/sources/Linux 操作系统/Linux 时钟系统/Linux 内核 tick 定时器.md`（知乎专栏，2026-11-13 落入 raw）
- 派生页面：[[concepts/linux-tick-and-hz]]、[[concepts/clocksource-and-clockevent]]、[[concepts/kernel-timer-wheel]]、[[skills/linux-kernel-timer-template]]
