---
title: Linux内核锁选择指南
category: skills
tags: [linux, 内核, 锁, spinlock, mutex, rcu, 同步]
source_dir: Linux 操作系统/Linux 锁机制
source_files: ["1 Linux 锁机制全景介绍.md", Linux SpinLock锁.md, Linux Mutex锁.md, Linux RCU锁.md]
summary: 内核锁类型选择决策树与API速查：Spinlock(忙等/任意上下文/短CS)、Mutex(睡眠/进程上下文/长CS)、RWLock/RW Semaphore(读写分离)、Seqlock(顺序锁)、RCU(读零开销/高R/W比)、WW Mutex/Local Lock/Bit Spinlock等13种锁的适用场景与常见陷阱。
provenance:
  extracted: 0.85
  inferred: 0.10
  ambiguous: 0.05
base_confidence: 0.85
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: supporting
created: 2026-06-01
updated: 2026-11-10
relationships:
  - target: "[[concepts/linux-lock-mechanisms]]"
    type: implements
  - target: "[[concepts/linux-interrupt-system]]"
    type: uses
  - target: "[[concepts/linux-process-scheduling]]"
    type: uses
  - target: "[[concepts/memory-barriers]]"
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

| 锁类型 | 等待方式 | 上下文限制 | 开销(相对) | 最佳场景 |
|--------|----------|-----------|------------|----------|
| Spinlock | 忙等 | 任意上下文 | 极小(4x) | 中断、极短临界区 |
| Mutex | 睡眠+乐观自旋 | 仅进程上下文 | 中等(6x) | 通用互斥、可睡眠操作 |
| RWLock | 忙等读+写 | 任意上下文 | 小(5x读) | 读多写少、短CS |
| RW Semaphore | 睡眠读+写 | 仅进程上下文 | 中等(6x读) | 读多写少、长CS |
| Seqlock | 忙等(仅写) | 任意上下文 | 小(3x读) | 读极多、时间/统计 |
| RCU | 无锁读 | 任意(读)/进程(写) | 读零(3x) | 读极多写极少 |
| Semaphore | 睡眠 | 仅进程上下文 | 大(8x) | 资源计数、同步 |
| Atomic | 原子操作 | 任意上下文 | 极小(3x) | 简单计数器/标志 |
| per-cpu | 无锁 | 任意上下文 | 最低(2.5x) | per-CPU统计 |
| rt_mutex | 睡眠+优先级继承 | 仅进程上下文 | 中等 | 实时系统防优先级反转 |
| ww_mutex | 睡眠+Wound-Wait | 仅进程上下文 | 中等 | GPU/DRM多锁避免死锁 |
| Local Lock | preempt/irq封装 | 任意上下文 | 极小 | 替代隐式preempt_disable |
| Bit Spinlock | 忙等(单bit) | 任意上下文 | 极小 | page->flags等位域 |

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
    读极多但需读侧统计 → Seqlock
      ↓ 简单计数器？→ Atomic/per-cpu
      ↓ 多锁需避免死锁？→ WW Mutex (GPU/DRM)
      ↓ 只需禁用抢占/中断？→ Local Lock
```

**持锁时间 vs 锁选择速查**：`<100 cycles` → atomic/无锁；`<1μs` → spinlock；`>1μs` → 考虑mutex；`>10μs` → 必须mutex；`>1ms` → mutex或semaphore。

### 3. Spinlock API选择

**关键问题：你的临界区数据与谁共享？**

| 共享对象 | API | 说明 |
|----------|-----|------|
| 硬件中断ISR | `spin_lock_irqsave` / `spin_unlock_irqrestore` | 禁用本地中断+获取锁；保存/恢复原始中断状态 |
| 软中断/tasklet | `spin_lock_bh` / `spin_unlock_bh` | 仅禁用softirq（local_bh_disable）；允许硬中断；更轻量 |
| 仅其他进程 | `spin_lock` / `spin_unlock` | 不禁用中断；跨核互斥+关抢占（preempt_count++） |
| 已在硬中断中 | `spin_lock` / `spin_unlock` | 中断已被禁用，无需再禁用 |
| 已在软中断中 | `spin_lock` / `spin_unlock` | 已在软中断上下文 |

**API变体矩阵**：基础(`spin_lock`) | 禁用中断(`spin_lock_irq`/`spin_lock_irqsave`) | 禁用下半部(`spin_lock_bh`) | 尝试获取(`spin_trylock`/`spin_trylock_irqsave`)

**优先使用 `irqsave` 而非 `irq`：** `irqsave` 保存原始中断状态，嵌套调用安全；`irq` 在unlock时无差别启用所有中断（`spin_unlock_irq`会改变外部中断状态，危险）。

**嵌套锁规则：** irqsave 放在最外层锁；内层用普通 `spin_lock`。`spin_lock_irqsave` 只禁用本地CPU中断——锁提供跨CPU互斥，irqsave防止同CPU递归获取死锁。

**内存屏障语义：** `spin_lock` 隐含 acquire 屏障（临界区操作不重排到锁前），`spin_unlock` 隐含 release 屏障（临界区操作不重排到锁后）。详见 [[concepts/memory-barriers]]。

### 4. Mutex API速查

| API | 行为 | 适用场景 |
|-----|------|----------|
| `mutex_lock(&lock)` | 阻塞等待，不可被信号中断 | 一般互斥 |
| `mutex_lock_interruptible(&lock)` | 可被信号中断，返回 -ERESTARTSYS | 用户空间可中断操作 |
| `mutex_lock_killable(&lock)` | 仅 SIGKILL 可中断 | 大部分场景推荐 |
| `mutex_trylock(&lock)` | 非阻塞尝试，成功1失败0 | 避免死锁风险 |
| `mutex_lock_io(&lock)` | I/O 超时版本（5min） | IO密集操作 |
| `mutex_is_locked(&lock)` | 检查是否被持有 | 状态查询 |
| `guard(mutex)(&lock)` | 自动作用域释放(Linux 6.x) | 简化代码 |

**严格所有权规则：** 只有持有者才能释放（`mutex_unlock`）；不允许递归获取同一mutex（会死锁）；嵌套不同锁需保持全局统一顺序。

**绝对禁止：** 在中断/软中断上下文使用 mutex（会睡眠→死锁）；持有者之外的任务调用 `mutex_unlock`。

**正确返回路径处理：** 使用 `goto out` 模式统一释放点，避免多分支忘记unlock。

### 5. RCU 使用规则

**读侧：**
```c
rcu_read_lock();         // preempt_disable — 不能睡眠！
ptr = rcu_dereference(p); // 安全读取指针（含屏障语义）
// 只读使用数据，绝不修改！
rcu_read_unlock();       // preempt_enable
```

**链表无锁遍历：**
```c
rcu_read_lock();
list_for_each_entry_rcu(node, &list, list) {
    process(node);       // 无锁遍历
}
rcu_read_unlock();
```

**写侧选择：**

| 写侧 API | 行为 | 适用场景 |
|-----------|------|----------|
| `synchronize_rcu()` | 阻塞等待宽限期(~10-100ms) | 可阻塞的写侧 |
| `synchronize_rcu_expedited()` | 快速但CPU密集 | 紧急场景 |
| `call_rcu(&old->rcu, cb)` | 异步回调 | 不能阻塞 |
| `kfree_rcu(old, rcu)` | 异步释放 | 简单 kfree 回调 |

**链表修改（需spinlock保护）：** `list_add_rcu`/`list_del_rcu` 在spinlock内调用，删除后用 `kfree_rcu` 延迟释放。

**RCU 变体选择：**
- 需要睡眠？→ SRCU（`srcu_read_lock`，开销更大）
- 网络软中断？→ RCU-bh（`rcu_read_lock_bh`）
- 调度器内部？→ RCU-sched（`rcu_read_lock_sched`）
- 任务级跟踪？→ Tasks RCU（`rcu_read_lock_trace`）

**适用条件：** R/W比 > 100:1 → 明确受益；10:1~100:1 → 可能受益；< 10:1 → 用 RWLock/Mutex。

**RCU读侧铁律：** 只读不写；Classic RCU读区不可睡眠（preempt_disable）；宽限期内不可访问已释放数据（必须先 `rcu_assign_pointer` 再延迟释放）。

### 6. 场景匹配速查

| 场景 | 推荐锁 | 原因 |
|------|--------|------|
| ISR 与进程共享数据 | `spin_lock_irqsave` | 安全禁用本地中断防同CPU死锁 |
| 极短CS(<100指令) | Spinlock | 开销最低 |
| 含IO或可睡眠操作 | Mutex | 长持有+可睡眠 |
| 路由表查找(VFS dentry) | RCU | 读极多写极少 |
| 资源池(连接池) | Semaphore | 计数语义 |
| 简单计数器 | Atomic/per-cpu | 无锁高效 |
| 实时系统 | rt_mutex | 优先级继承防反转 |
| GPU/DRM多锁 | ww_mutex | Wound-Wait事务化避免死锁 |
| 时间读取/统计计数 | seqlock | 读无锁+序列号校验 |
| 读多写少短CS | rwlock | 读并发 |
| 读多写少长CS | rwsem | 睡眠版读写分离 |
| page->flags位域保护 | bit_spinlock | 单bit极低内存开销 |
| 替代隐式preempt_disable | local_lock | 可调试+可审计 |
| 写后继续读（降级） | rwsem `downgrade_write` | 避免释放+重新获取读锁 |

## 常见问题与陷阱

| 错误 | 原因 | 正确做法 |
|------|------|----------|
| Spinlock 内调用 `kmalloc(GFP_KERNEL)` | GFP_KERNEL 可睡眠→死锁 | 用 `GFP_ATOMIC` |
| Spinlock 内调用 `copy_from_user` | 可能睡眠 | 改用 Mutex |
| Spinlock 内调用 `msleep` | 明确睡眠 | 绝对禁止，改用 Mutex |
| Mutex 在 ISR 中使用 | 中断上下文不能睡眠 | 改用 Spinlock |
| 持锁者外释放 mutex | 无所有权语义→状态混乱 | 只有持有者可 `mutex_unlock` |
| 忘记 `spin_unlock_irqrestore` | 只调 `unlock` 未恢复中断状态 | 始终成对使用 irqsave/irqrestore |
| 递归获取同一 spinlock | 同CPU同锁死锁 | 重新设计锁保护范围 |
| 递归获取同一 mutex | 死锁 | mutex不支持递归，重新设计 |
| `spin_unlock_irq` 嵌套在 irqsave 中 | 过早无差别启用中断 | 内层用 `spin_unlock`，仅外层 irqrestore |
| 持锁时间过长(Spinlock) | CPU空转浪费 | >10us 必须用 Mutex |
| RCU 读侧修改数据 | RCU 读区只读不写 | 修改在写侧拷贝-替换流程完成 |
| RCU 读侧睡眠(classic) | preempt_disable 下不可睡眠 | 改用 SRCU |
| 宽限期内释放旧数据 | 读者可能仍在访问 | 必须先 `rcu_assign_pointer` 后 `kfree_rcu` |
| RWLock写者饥饿 | 读者不断到来 | 考虑用RCU或rwsem替代 |

## 进阶用法

- **Lockdep**：`CONFIG_DEBUG_LOCK_ALLOC` + `CONFIG_LOCKDEP=y` — 自动检测锁依赖顺序和潜在死锁（如 lock1→lock2 后出现 lock2→lock1）
- **Spinlock 调试**：`CONFIG_DEBUG_SPINLOCK` — 检测递归获取、未初始化使用、错误释放，记录 owner_cpu/owner
- **Lock 统计**：`CONFIG_LOCK_STAT=y` — `cat /proc/lock_stat` 查看持锁时间、等待时间、争用次数
- **Mutex 调试**：`CONFIG_DEBUG_MUTEXES` — magic/owner_task/name/dep_map 调试字段
- **Crash 工具**：`crash> struct mutex <addr>` — 解析 mutex owner/waiter 队列
- **RT 内核**：`CONFIG_PREEMPT_RT` — spinlock 编译为 rt_mutex（API兼容，可睡眠），raw_spinlock 豁免
- **Ftrace**：`echo 1 > tracing/events/lock/lock_acquire/enable` — 追踪锁获取/释放事件

**性能基准参考：**
- 无竞争 spin_lock: ~50-100 cycles；spin_unlock: ~10-20 cycles
- 无竞争 mutex_lock: ~100-200 cycles；semaphore: ~200-300 cycles
- 相对开销：per-cpu 2.5x，atomic_inc 3x，spinlock 4x，rwlock(读) 5x，mutex/rwsem(读) 6x，semaphore 8x

## 来源

- [[concepts/linux-lock-mechanisms]] — 锁机制全景框架
- [[concepts/linux-interrupt-system]] — 中断上下文与锁选择
- [[concepts/linux-process-scheduling]] — preempt_count 机制
- [[concepts/memory-barriers]] — acquire/release 屏障语义
- [[summaries/linux-rcu-lock]] — RCU API 与适用条件