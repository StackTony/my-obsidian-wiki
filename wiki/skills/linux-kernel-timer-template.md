---
title: 内核定时器模块模板（timer_list）
category: skills
tags: [linux, 内核, 定时器, 模块, 实操]
aliases: [timer_list 模板, add_timer 用法, del_timer_sync]
relationships:
  - target: "[[concepts/kernel-timer-wheel]]"
    type: uses
source_dir: Linux 操作系统/Linux 时钟系统
source_files: [Linux 内核 tick 定时器.md]
summary: 写一个周期性内核定时器模块的六步骨架（初始化→注册→回调续期→注销），以及卸载竞态、软中断上下文、jiffies 回绕等六个高频坑。
provenance:
  extracted: 0.50
  inferred: 0.45
  ambiguous: 0.05
base_confidence: 0.44
lifecycle: draft
lifecycle_changed: 2026-11-17
tier: supporting
created: 2026-11-17
updated: 2026-11-17
---

# 内核定时器模块模板（timer_list）

要写一个"每隔 N 毫秒做点事"的内核模块，最短路径就是 `timer_list`：填结构、定回调、注册、在回调里续期、卸载时同步删除。模板只有二十行，但错一处就是 use-after-free 或 `scheduling while atomic`。本页给出可照抄的骨架和踩坑清单。

## 前置条件

- 与目标内核版本一致的头文件（`linux/timer.h`、`linux/jiffies.h`、`linux/module.h`）
- 能够编译并加载内核模块（`make -C /lib/modules/$(uname -r)/build M=$PWD`）
- 明确内核版本：`setup_timer()` 在 4.15 被 `timer_setup()` 取代 ^[inferred]

## 步骤

### 1. 定义定时器与私有数据结构

```c
struct my_dev {
    struct timer_list timer;   // 嵌入式放，便于 from_timer 反推
    int count;
};
static struct my_dev *dev;
```

### 2. 写回调（运行在软中断上下文）

```c
static void my_timer_fn(struct timer_list *t)
{
    struct my_dev *d = from_timer(d, t, timer);
    pr_info("tick %d\n", ++d->count);
    // 周期续期；一次性定时器就不要再 mod_timer
    mod_timer(t, jiffies + msecs_to_jiffies(1000));
}
```

### 3. 初始化（两种写法按内核版本选）

```c
/* 4.15+ */
timer_setup(&dev->timer, my_timer_fn, 0);

/* 旧内核 */
setup_timer(&dev->timer, my_timer_fn, (unsigned long)dev);
```

### 4. 注册

```c
dev->timer.expires = jiffies + msecs_to_jiffies(1000);  // 旧接口需要显式设 expires
add_timer(&dev->timer);
/* 或者直接：mod_timer(&dev->timer, jiffies + msecs_to_jiffies(1000)); */
```

### 5. 回调里续期（周期定时器）

用 `mod_timer()` 而不是重复 `add_timer()`：前者对已激活的定时器会先摘链再插入，后者对同一节点重复入链会破坏链表。

### 6. 卸载时同步删除

```c
static void __exit my_exit(void)
{
    del_timer_sync(&dev->timer);   // 等所有 CPU 上的回调退出
    kfree(dev);                    // 之后才能释放
}
```

## 常见问题

| 症状 | 原因 | 处理 |
|---|---|---|
| 卸载后 panic / use-after-free | 只 `del_timer()` 或干脆没删，回调仍在跑并访问已释放内存 | 用 `del_timer_sync()`，且放在 `kfree` 之前 |
| `BUG: scheduling while atomic` | 回调里 `msleep`/`mutex_lock`/`kmalloc(GFP_KERNEL)` | 回调在 softirq 上下文，只能 `GFP_ATOMIC`、`spin_lock_bh`，耗时工作丢给 workqueue |
| 定时器提前/推迟触发 | 用 `jiffies + HZ` 或直接比较大小 | 用 `msecs_to_jiffies()`；比较用 `time_after/time_before` 处理回绕 |
| 定时器只触发一次 | 回调里没有续期 | 周期定时器必须在回调里 `mod_timer()` |
| 定时器重复触发、链表损坏 | 对同一未结束的定时器调用两次 `add_timer()` | 改时间用 `mod_timer()`；插入前可先 `timer_pending()` 判断 |
| 精度达不到预期 | `timer_list` 分辨率是 jiffies（HZ=100 时 10 ms） | 亚 jiffy 精度改用 hrtimer ^[inferred] |

## 进阶用法

- **延迟定时器**：`timer_setup(&t, fn, TIMER_DEFERRABLE)`，CPU 空闲时不当场唤醒，配合 NO_HZ 省电 ^[inferred]
- **传参**：把 `timer_list` 嵌进自己的结构体，用 `from_timer()` 反推，比 `data` 裸转指针安全
- **一次性 vs 周期**：需要固定间隔就续期；需要"事件后 N ms 再执行"就只注册一次
- **更高精度**：hrtimer（`hrtimer_init` / `hrtimer_start`），可在硬中断上下文运行，精度到纳秒 ^[inferred]
- **观测**：`/proc/timer_list` 在启用相关配置的内核上可列出活动定时器与 hrtimer ^[ambiguous]

## 来源

- [[summaries/linux-tick-timer]] — 源文的定时器示例与注册/触发/销毁说明
- [[concepts/kernel-timer-wheel]] — 背后的时间轮与软中断执行链
- 原始文档：`raw/sources/Linux 操作系统/Linux 时钟系统/Linux 内核 tick 定时器.md`
