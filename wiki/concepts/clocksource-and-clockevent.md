---
title: clocksource 与 clockevent（硬件定时器抽象）
category: concepts
tags: [linux, 内核, 定时器, clocksource, clockevent]
aliases: [时钟源, 时钟事件设备, tick_device]
relationships:
  - target: "[[concepts/linux-tick-and-hz]]"
    type: implements
  - target: "[[concepts/linux-driver-model]]"
    type: related_to
source_dir: Linux 操作系统/Linux 时钟系统
source_files: [Linux 内核 tick 定时器.md]
summary: 内核对硬件定时器的两分抽象：clocksource 负责"读出现在几点"、clockevent 负责"到点叫一声"；tick_device 把后者包装成每 CPU 的节拍源。
provenance:
  extracted: 0.65
  inferred: 0.28
  ambiguous: 0.07
base_confidence: 0.44
lifecycle: draft
lifecycle_changed: 2026-11-17
tier: supporting
created: 2026-11-17
updated: 2026-11-17
---

# clocksource 与 clockevent（硬件定时器抽象）

一颗 SoC 上有好几种硬件定时器，Linux 不直接使用它们，而是把它们注册成两类设备：一类只会"报数"，一类只会"报时"。前者叫 clocksource，后者叫 clockevent。tick、调度时间、墙上时间都是这两类设备的上层消费者。

## 核心观点

- **clocksource 回答"现在几点"**：提供单调递增的自由运行计数器，内核读它并换算成时间；它是 timekeeping 与 `sched_clock` 的底层基准。
- **clockevent 回答"到点叫我"**：可按周期或单次编程一个中断，`set_next_event()` 设定下一次到期时间，`set_mode()` 切换周期性/一次性。
- **同一颗硬件可以两用**：ARM 通用定时器就用物理计数做 clocksource、用比较器中断做 clockevent；x86 上 TSC 做 clocksource、LAPIC/HPET 做 clockevent。 ^[inferred]
- **选谁由 rating 决定**：每个设备自带 `rating`，内核在候选集中挑精度与稳定性最好的那个；不稳定的源（如老 TSC）会被降级。 ^[inferred]
- **tick_device 是每 CPU 的一层包装**：把 `clock_event_device` 和本 CPU 的 tick 模式（周期/单次/停摆）绑在一起，tick 子系统只跟它打交道。

## 关键细节

### 结构体骨架（源文给出）

```c
struct clock_event_device {
    const char *name;
    u32 features;      // PERIODIC / ONESHOT 等能力位
    u32 rating;        // 择优依据
    int  (*set_next_event)(unsigned long evt, struct clock_event_device *dev);
    void (*set_mode)(enum clock_event_mode mode, struct clock_event_device *dev);
};

struct tick_device {
    int cpu;
    enum tick_device_mode mode;   // 周期性 / 单次
    struct clock_event_device *evtdev;
    void (*handle)(struct clock_event_device *dev);
};
```

`tick_device` 不独立存在，它是 per-CPU 数组 `tick_cpu_device[]` 的一项，cpuset 化后随 CPU 热插拔重建。

### 典型注册路径

1. 设备树声明定时器节点（`compatible = "arm,armv8-timer"` 之类），驱动 probe 拿到寄存器基址与中断号
2. 驱动填充 `clocksource` / `clock_event_device` 结构并注册
3. 内核按 rating 选出系统 clocksource 与每个 CPU 的 clockevent
4. tick 子系统用选中的 clockevent 驱动节拍：周期模式下 `tick_setup_periodic()` 设置 `CLOCK_EVT_FEAT_PERIODIC` 并编程下一次事件

### ARM 平台上的定时器家族（源文列举）

| 定时器 | 位置 | 用途 |
|---|---|---|
| ARM Generic Timer | ARMv7-A/R、ARMv8-A 核内 | 物理/虚拟计数（CNTPCT/CNTVCT），主力 clocksource + clockevent |
| Global Timer | 部分多核（如 Cortex-A9） | 多核间全局时间同步 |
| Local Timer | 每核私有（如 ARM11） | 核内私有定时任务 |
| 厂商定时器 | TI OMAP、三星 S3C 等 | 芯片定制场景（PWM、看门狗等） |

### 与 tick 的关系

clocksource 提供"时间轴"，clockevent 提供"刻度事件"，tick 子系统把刻度变成 jiffies 与调度检查点。没有 clockevent 就没有 tick；没有 clocksource 就算不出两次 tick 之间的真实间隔——两者缺一，时间就会漂或停。 ^[inferred]

### 怎么观测

- `/sys/devices/system/clocksource/clocksource0/current_clocksource` 看当前时钟源；`available_clocksource` 看候选与 rating
- dmesg 中 `clocksource: ... rating: N` 一行即为选型结果
- `/proc/interrupts` 中对应定时器中断计数可验证 clockevent 是否在工作

## 未解问题

- broadcast 机制（CPU 进入深 C-state 后本地 clockevent 关闭，改由全局 broadcast 设备唤醒）本 vault 尚无来源。
- 虚拟化场景下 Guest 使用何种 clockevent（kvm-clock / PIT / LAPIC timer 的选择与降级）未覆盖，见 [[concepts/linux-interrupt-virtualization]] 的相关缺口。
- clocksource watchdog（监测 TSC 漂移并切换）机制缺失来源。

## 来源

- [[summaries/linux-tick-timer]] — 硬件基础与数据结构、rating 选型、DTS 注册链路
- [[concepts/linux-tick-and-hz]] — 上层消费者
- 原始文档：`raw/sources/Linux 操作系统/Linux 时钟系统/Linux 内核 tick 定时器.md`
