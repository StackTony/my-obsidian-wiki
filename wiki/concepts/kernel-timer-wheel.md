---
title: 内核定时器（timer_list 与时间轮）
category: concepts
tags: [linux, 内核, 定时器, softirq, 时间轮]
aliases: [timer_list, 时间轮, add_timer, del_timer_sync]
relationships:
  - target: "[[concepts/linux-tick-and-hz]]"
    type: derived_from
  - target: "[[concepts/linux-interrupt-system]]"
    type: uses
source_dir: Linux 操作系统/Linux 时钟系统
source_files: [Linux 内核 tick 定时器.md]
summary: timer_list 的完整生命周期：per-CPU 五级时间轮按 expires-jiffies 分槽、add_timer/__mod_timer 入链、TIMER_SOFTIRQ 里 __run_timers→expire_timers 执行、del_timer_sync 的同步约束。
provenance:
  extracted: 0.68
  inferred: 0.24
  ambiguous: 0.08
base_confidence: 0.44
lifecycle: draft
lifecycle_changed: 2026-11-17
tier: supporting
created: 2026-11-17
updated: 2026-11-17
---

# 内核定时器（timer_list 与时间轮）

`timer_list` 是内核里最"便宜"的定时器：不保证精确到微秒，只保证"到点之后在下一次 tick 扫描时被执行"。它的实现是一个每 CPU 的分级时间轮加一条软中断执行链——结构简单，但把延迟、并发与销毁顺序的坑都集中在几个函数里。

## 核心观点

- **定时器不自己走时间**：`timer_list` 只是挂在时间轮上的一个到期任务，推进它的是 tick 中断；因此它的分辨率上限就是 jiffies 粒度。
- **每 CPU 一套时间轮**：`tvec_bases` 是 per-CPU 变量，各自带 `base->lock` 自旋锁，避免多核争抢同一把锁。
- **五级分级结构**：`tv1` 存 0–255 jiffies 内到期的定时器，`tv2` 存 256–16383，往上依次扩大范围——越远的定时器放在粗粒度槽里，减少每次扫描的链表长度。
- **执行在软中断里**：tick 只负责 `raise_softirq(TIMER_SOFTIRQ)`，真正跑回调的是 `run_timer_softirq()`，所以定时器回调**不能睡眠**。
- **`del_timer` 与 `del_timer_sync` 不是同义词**：前者只摘链，后者等待所有 CPU 上的回调退出，是模块卸载时的正确选择；后者必须在进程上下文、不能持自旋锁。

## 关键细节

### 数据结构

```c
struct timer_list {
    struct hlist_node entry;      // 挂在时间轮槽位上的链表节点
    unsigned long expires;        // 到期 jiffies
    void (*function)(struct timer_list *);  // 4.15+ 签名
    u32 flags;                    // TIMER_DEFERRABLE 等
};
```

旧版本用 `void (*function)(unsigned long)` + `data` 字段传参，4.15 起改为回调接收 `struct timer_list *`、用 `from_timer()` 反推外层结构。 ^[inferred]

### 注册：add_timer / mod_timer

```c
void add_timer(struct timer_list *timer)
{
    struct tvec_base *base = __raw_get_cpu_var(tvec_bases);
    __mod_timer(timer, base, jiffies, 1);
}
```

- 取当前 CPU 的 `tvec_base`，进入 `__mod_timer()`
- 若 `expires` 已过（`time_before(expires, jiffies)`），直接执行回调、不入链
- 否则按 `idx = expires - jiffies` 算出层级与槽位插入；`tv1` 用 `TIMER_INDEX(idx)` 取槽
- 全程持 `base->lock`，避免多核并发改链
- `mod_timer(timer, expires)` 等价于"改到期时间并重新入链"，对未激活的定时器也有效，是周期定时器的续期手段

### 触发：tick → 软中断 → 回调

```
时钟中断
  └─ run_local_timers()
       ├─ hrtimer_run_queues()               // 高精度定时器
       └─ jiffies >= base->next_timer ?
            └─ raise_softirq(TIMER_SOFTIRQ)
                 └─ run_timer_softirq()
                      ├─ __run_timers(base)              // 普通定时器
                      └─ __run_timers(tvec_bases_deferrable)  // CONFIG_NO_HZ_COMMON 下的延迟定时器
                           └─ find_next_expired_timer() → expire_timers()
                                └─ detach_timer() → call_timer_fn()
```

- `__run_timers()` 用 `while (time_after_eq(jiffies, base->timer_jiffies))` 追赶错过的节拍，`base->timer_jiffies++` 逐个推进
- `expire_timers()` 把到期的定时器摘链、记录 `base->running_timer` 便于调试，再执行回调
- `call_timer_fn()` 在 `local_bh_disable()/local_bh_enable()` 之间调用回调，防止被其他软中断重入 ^[ambiguous]（新内核的 bh 保护位置有调整）

### 销毁：del_timer vs del_timer_sync

| 函数 | 行为 | 约束 |
|---|---|---|
| `del_timer()` | 若 `timer_pending()` 为真则 `detach_timer()`，返回是否摘到 | 不能保证回调此时没在别的 CPU 上跑 |
| `del_timer_sync()` | 摘链并等待所有正在执行的回调退出 | 必须在进程上下文；不能持自旋锁，否则与等锁的回调死锁 |

源文给的反例很典型：CPU0 持锁调用 `del_timer_sync()`，CPU1 上的回调正等同一把锁——两边互等，系统卡死。

### 延迟定时器（deferrable）

带 `TIMER_DEFERRABLE` 标志的定时器进入独立的延迟链表，只在 CPU 非空闲时处理，用来配合 NO_HZ 省电：这类定时器"晚一点没关系"，例如统计类、清理类任务。 ^[inferred]

### 版本演进（重要前提）

源文示例基于旧内核（时间轮 `tvec_base`、`setup_timer`、`init_timer`）。4.15 起定时器子系统重构为 per-CPU `timer_base` 的 8 级时间轮（每级 64 槽 + bitmap 加速查找），`setup_timer()` 被 `timer_setup()` 取代，回调签名改为 `struct timer_list *`。 ^[inferred] 语义（分级、软中断执行、`del_timer_sync` 约束）没有变，读源码时注意函数名与结构体差异。

## 未解问题

- `timer_list` 与 hrtimer 的选择边界：什么场景必须用 hrtimer（亚 jiffy、精确唤醒、可在硬中断上下文）？现有来源未给出判据。
- 时间轮 8 级实现中 `calc_wheel_index()` 的具体哈希与级联（cascade）成本，本 vault 无来源。
- `timer_pending()` 在 `TIMER_MIGRATING` 等新标志下的语义变化未覆盖。

## 来源

- [[summaries/linux-tick-timer]] — 注册/触发/销毁三段源码与调用链
- [[concepts/linux-interrupt-system]] — `TIMER_SOFTIRQ` 在 10 种 softirq 中的位置
- 原始文档：`raw/sources/Linux 操作系统/Linux 时钟系统/Linux 内核 tick 定时器.md`
