---
title: Linux 锁机制
created: 2026-06-01
updated: 2026-06-01
tags: [linux, kernel, synchronization, lock, spinlock, mutex, rcu]
category: concepts
source_dir: Linux 操作系统/Linux 锁机制
source_files: [Linux 锁机制全景介绍.md, Linux SpinLock锁.md, Linux Mutex锁.md, Linux RCU锁.md]
summary: Linux内核同步机制的完整框架：从Spinlock到RCU的演进与选择指南
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: "2026-06-01"
tier: supporting
provenance:
  extracted: 0.7
  inferred: 0.25
  ambiguous: 0.05
relationships:
  - target: "[[concepts/linux-interrupt-system]]"
    type: uses
  - target: "[[concepts/linux-memory-management]]"
    type: uses
---

# Linux 锁机制

Linux内核提供多层次的同步机制，按等待行为分为三类：忙等待锁、睡眠锁、无锁机制。选择的核心权衡是**持锁时间**与**上下文限制**。

## 核心对比

| 锁类型 | 等待方式 | 上下文限制 | 开销 | 适用场景 |
|--------|----------|------------|------|----------|
| **Spinlock** | 忙等待 | 任意 | 极小 | 中断、极短临界区(<1μs) |
| **Mutex** | 睡眠 | 仅进程 | 中等 | 一般互斥、可睡眠 |
| **RWLock** | 忙等待 | 任意 | 小 | 读多写少、短临界区 |
| **RW Semaphore** | 睡眠 | 仅进程 | 中等 | 读多写少、长临界区 |
| **Seqlock** | 忙等待(写) | 任意 | 极小(读) | 读远多于写(时间戳) |
| **RCU** | 无锁 | 任意(读) | 读零 | 读极多写极少 |
| **Semaphore** | 睡眠 | 仅进程 | 大 | 资源计数 |
| **Atomic** | 原子操作 | 任意 | 极小 | 简单计数/标志 |
| **Per-CPU** | 无锁 | 任意 | 极小 | 高性能计数器 |

## 忙等待锁：Spinlock

核心原则："快进快出，绝不睡眠"。持锁时间必须短于上下文切换开销(~5-10μs)。

### 实现演进：解决公平性

1. **Test-And-Set**：简单但无公平性，可能饥饿
2. **Ticket Lock**：FIFO公平，但所有等待者检查同一变量导致缓存行争用
3. **MCS/Queued Spinlock**(现代)：每个CPU在本地节点自旋，避免缓存争用，NUMA性能优异

### API变体决策树

```
与硬件中断共享数据？
  是 → spin_lock_irqsave(推荐) / spin_lock_irq(危险)
  否 → 与软中断共享？
        是 → spin_lock_bh
        否 → spin_lock

已在中断上下文？
  硬件中断 → spin_lock(中断已禁用)
  软中断   → spin_lock(已在软中断中)
```

**关键点**：`irqsave`只禁用本地CPU中断，锁提供跨CPU互斥。与[[concepts/linux-interrupt-system]]紧密关联。

### raw_spinlock vs spinlock

- `raw_spinlock`：真正的自旋锁，RT内核不变，用于调度器/中断核心
- `spinlock`：RT内核下转为`rt_mutex`，保持API兼容

## 睡眠锁：Mutex

仅进程上下文可用，持锁期间可睡眠。核心优化是**乐观自旋**。

### 乐观自旋机制

获取失败时先短时间自旋(而非立即睡眠)，若持有者很快释放则避免上下文切换开销。条件：
- 持有者正在运行(其他CPU)
- 自旋次数未超限
- 无更高优先级任务等待

### Owner字段编码

```
[task_struct指针(高位)] [flags(低3位)]
  bit 0: MUTEX_FLAG_WAITERS(有等待者)
  bit 1: MUTEX_FLAG_HANDOFF(移交锁)
```

### 优先级继承

内嵌`rt_mutex`，高优先级等待时暂时提升持有者优先级，防止优先级反转。^[inferred]

## 无锁机制：RCU

**"读者零开销"**的极致设计。读侧无锁、无原子操作、仅~15-30 cycles。

### 宽限期机制

写者替换指针后，等待所有"替换前进入"的读者退出，才释放旧数据。不是等所有读者，只等看到旧版本的读者。

静止点(quiescent state)：上下文切换、用户态执行、idle状态——这些时刻一定不在RCU读临界区。

### Tree RCU

大规模系统用分层树状结构检测静止状态，复杂度O(log N)。^[inferred]

### RCU变体

| 变体 | 读侧特点 | 适用场景 |
|------|----------|----------|
| Classic RCU | 不可睡眠 | 内核通用 |
| SRCU | 可睡眠 | 需copy_to_user/I/O |
| RCU-sched | 禁用抢占 | 调度器相关 |
| RCU-bh | 禁用软中断 | 网络软中断 |

### 适用条件

读/写比例 > 100:1 时RCU明显优于传统锁。读侧收益总和 > 写侧额外开销(复制+宽限期等待)。

## 锁选择决策树

```
中断上下文？
  是 → Spinlock(+irqsave/bh变体)
  否 → 持锁时间？
        < 1μs → Spinlock
        > 1μs → Mutex(可睡眠)
        读多写少？
          极多(>100x) → RCU
          中等(10-100x) + 短临界 → RWLock
          中等 + 长临界 → RW Semaphore
          读远多于写 + 简单数据 → Seqlock
        资源计数 → Semaphore
        简单计数 → Atomic/Per-CPU
```

## 未解问题

- PREEMPT_RT内核下spinlock转mutex的性能边界如何精确量化？
- 大规模NUMA系统下queued spinlock的最优队列深度？
- RCU宽限期在虚拟化环境下的行为差异？^[ambiguous]

## 来源

- `raw/sources/Linux 操作系统/Linux 锁机制/Linux 锁机制全景介绍.md`
- `raw/sources/Linux 操作系统/Linux 锁机制/Linux SpinLock锁.md`
- `raw/sources/Linux 操作系统/Linux 锁机制/Linux Mutex锁.md`
- `raw/sources/Linux 操作系统/Linux 锁机制/Linux RCU锁.md`