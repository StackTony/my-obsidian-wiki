---
title: Linux内核锁选择指南
category: skills
tags: [linux, 内核, 锁, spinlock, mutex, rcu, 同步]
source_dir: Linux 操作系统/Linux 锁机制
source_files: [Linux 锁机制全景介绍.md, Linux SpinLock锁.md, Linux Mutex锁.md, Linux RCU锁.md]
summary: 内核锁类型选择决策树与API速查：Spinlock(忙等/任意上下文/短CS)、Mutex(睡眠/进程上下文/长CS)、RCU(读零开销/高R/W比)等10种锁的适用场景与常见陷阱。
provenance:
  extracted: 0.85
  inferred: 0.10
  ambiguous: 0.05
base_confidence: 0.825
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: supporting
created: 2026-06-01
updated: 2026-06-01
relationships:
  - target: "[[concepts/linux-lock-mechanisms]]"
    type: implements
  - target: "[[concepts/linux-interrupt-system]]"
    type: uses
  - target: "[[concepts/linux-process-scheduling]]"
    type: uses
---

# Linux内核锁选择指南

选择正确的锁类型是内核编程的核心决策。本页提供决策树、API速查、场景匹配和常见陷阱。

## 前置条件

- 理解 [[concepts/linux-lock-mechanisms]] 各锁类型的基本原理
- 了解 [[concepts/linux-interrupt-system]] 的上下文层级（硬中断→软中断→进程）
- 知道 [[concepts/linux-process-scheduling]] 的 preempt_count 机制

## 步骤

### 1. 锁类型速查对比

| 锁类型 | 等待方式 | 上下文限制 | 开销 | 最佳场景 |
|--------|----------|-----------|------|----------|
| Spinlock | 忙等 | 任意上下文 | 最低 | 中断、极短临界区 |
| Mutex | 睡眠 | 仅进程上下文 | 中等 | 通用互斥、可睡眠操作 |
| RWLock | 忙等读+写 | 任意上下文 | 小 | 读多写少、短CS |
| RW Semaphore | 睡眠读+写 | 仅进程上下文 | 中等 | 读多写少、长CS |
| Seqlock | 忙等(仅写) | 任意上下文 | 小 | 读极多、时间/统计 |
| RCU | 无锁读 | 任意(读)/进程(写) | 读零 | 读远多于写 |
| Semaphore | 睡眠 | 仅进程上下文 | 大 | 资源计数、同步 |
| Atomic | 原子操作 | 任意上下文 | 最低 | 简单计数器/标志 |
| per-cpu | 无锁 | 任意上下文 | 最低 | per-CPU统计 |
| rt_mutex | 睡眠+优先级继承 | 仅进程上下文 | 中等 | 实时系统防优先级反转 |

### 2. 决策树

```
需要同步？否 → 不用锁
  ↓ 是
在中断上下文？是 → Spinlock 系列
  ↓ 否（进程上下文）
锁持有时间？
  极短(<1us) → Spinlock
  中等(1-10us) → 考虑 Mutex
  长(>10us) → 必须 Mutex
    ↓ 读多写少？
    短CS → RWLock
    长CS → RW Semaphore
    读极多(R/W>100:1) → RCU
      ↓ 简单计数器？→ Atomic/per-cpu
```

### 3. Spinlock API选择

**关键问题：你的临界区数据与谁共享？**

| 共享对象 | API | 说明 |
|----------|-----|------|
| 硬件中断ISR | `spin_lock_irqsave` / `spin_unlock_irqrestore` | 禁用所有中断+获取锁；保存/恢复原始中断状态 |
| 软中断/tasklet | `spin_lock_bh` / `spin_unlock_bh` | 仅禁用softirq；允许硬中断；更轻量 |
| 仅其他进程 | `spin_lock` / `spin_unlock` | 不禁用中断；跨核互斥+关抢占 |

**优先使用 `irqsave` 而非 `irq`：** `irqsave` 保存原始中断状态，嵌套调用安全；`irq` 假定中断原来开启，不安全。

**嵌套锁规则：** irqsave 放在最外层锁；内层用普通 `spin_lock`。

### 4. Mutex API速查

| API | 行为 | 适用场景 |
|-----|------|----------|
| `mutex_lock(&lock)` | 阻塞等待，不可被信号中断 | 一般互斥 |
| `mutex_lock_interruptible(&lock)` | 可被信号中断，返回 -ERESTARTSYS | 用户空间可中断操作 |
| `mutex_lock_killable(&lock)` | 仅 SIGKILL 可中断 | 大部分场景推荐 |
| `mutex_trylock(&lock)` | 非阻塞尝试，成功1失败0 | 避免死锁风险 |
| `mutex_lock_timeout(&lock, jiffies)` | 定时等待 | 限时操作 |
| `guard(mutex)(&lock)` | 自动作用域释放(Linux 6.x) | 简化代码 |

**绝对禁止：** 在中断/软中断上下文使用 mutex（会睡眠→死锁）。

### 5. RCU 使用规则

**读侧：**
```c
rcu_read_lock();         // preempt_disable — 不能睡眠！
ptr = rcu_dereference(p); // 内存屏障安全读取指针
// 只读使用数据，绝不修改！
rcu_read_unlock();       // preempt_enable
```

**写侧选择：**

| 写侧 API | 行为 | 适用场景 |
|-----------|------|----------|
| `synchronize_rcu()` | 阻塞等待宽限期(~10-100ms) | 可阻塞的写侧 |
| `synchronize_rcu_expedited()` | 快速但CPU密集 | 紧急场景 |
| `call_rcu(&old->rcu, cb)` | 异步回调 | 不能阻塞 |
| `kfree_rcu(old, rcu)` | 异步释放 | 简单 kfree 回调 |

**RCU 变体选择：**
- 需要睡眠？→ SRCU（开销更大）
- 网络软中断？→ RCU-bh（`rcu_read_lock_bh`）
- 调度器内部？→ RCU-sched（`rcu_read_lock_sched`）

**适用条件：** R/W比 > 100:1 → 明确受益；10:1~100:1 → 可能受益；< 10:1 → 用 RWLock/Mutex。

### 6. 场景匹配速查

| 场景 | 推荐锁 | 原因 |
|------|--------|------|
| ISR 与进程共享数据 | `spin_lock_irqsave` | 安全禁用中断防同CPU死锁 |
| 极短CS(<100指令) | Spinlock | 开销最低 |
| 含IO或可睡眠操作 | Mutex | 长持有+可睡眠 |
| 路由表查找(VFS dentry) | RCU | 读极多写极少 |
| 资源池(连接池) | Semaphore | 计数语义 |
| 简单计数器 | Atomic/per-cpu | 无锁高效 |
| 实时系统 | rt_mutex | 优先级继承防反转 |
| 多锁需避免死锁 | ww_mutex | 无序获取 |

## 常见问题与陷阱

| 错误 | 原因 | 正确做法 |
|------|------|----------|
| Spinlock 内调用 `kmalloc(GFP_KERNEL)` | GFP_KERNEL 可睡眠→死锁 | 用 `GFP_ATOMIC` |
| Spinlock 内调用 `copy_from_user` | 可能睡眠 | 改用 Mutex |
| Spinlock 内调用 `msleep` | 明确睡眠 | 绝对禁止，改用 Mutex |
| Mutex 在 ISR 中使用 | 中断上下文不能睡眠 | 改用 Spinlock |
| 忘记 `spin_unlock_irqrestore` | 只调 `unlock` 未恢复中断状态 | 始终成对使用 irqsave/irqrestore |
| 递归获取同一 spinlock | 同CPU同锁死锁 | 重新设计锁保护范围 |
| `spin_unlock_irq` 嵌套在 irqsave 中 | 过早恢复中断 | 内层用 `spin_unlock`，仅外层 irqrestore |
| RCU 读侧修改数据 | RCU 读区只读不写 | 修改在写侧拷贝-替换流程完成 |
| RCU 读侧睡眠(classic) | preempt_disable 下不可睡眠 | 改用 SRCU |
| 临界区过长(Spinlock) | CPU空转浪费 | >10us 必须用 Mutex |

## 进阶用法

- **Lockdep**：`CONFIG_LOCKDEP=y` — 自动检测锁依赖顺序和潜在死锁
- **Lock 统计**：`CONFIG_LOCK_STAT=y` — `cat /proc/lock_stat` 查看竞争统计
- **Crash 工具**：`crash> struct mutex <addr>` — 解析 mutex owner/waiter 队列
- **RT 内核**：`CONFIG_PREEMPT_RT` — Spinlock 自动变为 rt_mutex（API兼容，行为改变）
- **Ftrace**：`echo 1 > tracing/events/lock/lock_acquire/enable` — 追踪锁获取/释放事件

**性能基准参考：**
- 无竞争 spin_lock: ~50-100 周期；spin_unlock: ~10-20 周期
- 相对开销：atomic_inc 3x，spinlock 4x，mutex 8x，semaphore 10x

## 来源

- [[concepts/linux-lock-mechanisms]] — 锁机制全景框架
- [[concepts/linux-interrupt-system]] — 中断上下文与锁选择
- [[concepts/linux-process-scheduling]] — preempt_count 机制
- [[summaries/linux-rcu-lock]] — RCU API 与适用条件