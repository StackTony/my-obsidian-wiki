---
title: Linux锁机制全景
category: concepts
tags: [linux, 内核, 同步, 锁, spinlock, mutex, RCU]
aliases: [Linux锁, 内核同步, spinlock, mutex锁, RCU锁]
relationships:
  - target: "[[concepts/linux-interrupt-system]]"
    type: uses
  - target: "[[concepts/linux-process-scheduling]]"
    type: related_to
  - target: "[[concepts/linux-network-stack]]"
    type: related_to
  - target: "[[concepts/linux-io-stack]]"
    type: related_to
  - target: "[[concepts/memory-barriers]]"
    type: uses
  - target: "[[concepts/cpu-cache-coherence]]"
    type: related_to
source_dir: Linux 操作系统/Linux 锁机制
source_files: ["1 Linux 锁机制全景介绍.md", Linux SpinLock锁.md, Linux Mutex锁.md, Linux RCU锁.md]
summary: Linux内核同步机制完整框架：从Spinlock到RCU的演进与选择指南。Spinlock忙等(微秒级/qspinlock+MCS队列)、Mutex睡眠锁(乐观自旋+PI/owner编码)、RWLock/Seqlock读写分离、RCU读零开销(宽限期机制)、WW Mutex/Local Lock/Bit Spinlock等扩展。决策树指导锁选择。
provenance:
  extracted: 0.80
  inferred: 0.15
  ambiguous: 0.05
base_confidence: 0.85
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: core
created: 2026-06-01
updated: 2026-11-10
---

# Linux锁机制全景

Linux内核同步机制是理解内核并发控制的核心框架，涵盖忙等、睡眠、无锁三大范式共十余种锁类型。Spinlock适合中断上下文的微秒级保护（现代x86用qspinlock+MCS队列），Mutex适合进程上下文的毫秒级互斥（乐观自旋+优先级继承），RWLock/Seqlock提供读写分离，RCU追求读侧零开销的极致性能，WW Mutex/Local Lock/Bit Spinlock等则覆盖特殊场景。所有锁的acquire/release操作都隐含[[concepts/memory-barriers|内存屏障]]语义，确保跨核可见性——锁与缓存一致性（[[concepts/cpu-cache-coherence]]）紧密耦合。

## 核心观点

- 内核同步机制分三大范式：忙等（spinlock/seqlock/rwlock/bit spin）、睡眠（mutex/semaphore/rwsem/rt_mutex/ww_mutex）、无锁（RCU/atomic/per-cpu），选择取决于执行上下文和临界区时长。
- Spinlock经历了三代演进：Test-And-Set→Ticket→MCS/Queued。x86用qspinlock（locked/pending/tail三段编码+per-CPU MCS node队列），ARM64用LSE原子指令+WFE低功耗等待，不同架构的实现路径不同。
- Spinlock的acquire/release隐含内存屏障语义：acquire保证临界区操作不被重排到锁获取之前，release保证临界区操作不被重排到锁释放之后——这是跨核可见性的底层保证（详见 [[concepts/memory-barriers]]）。 ^[inferred]
- raw_spinlock 与 spinlock 在 PREEMPT_RT 下语义不同：raw_spinlock 不允许抢占（真正的忙等，用于调度器/中断核心），spinlock 可能被编译为 rt_mutex（可睡眠，保持API兼容）。
- Mutex 引入乐观自旋（optimistic spinning，osq队列）和优先级继承（PI），owner字段低2位编码状态标志（bit0=MUTEX_FLAG_WAITERS，bit1=MUTEX_FLAG_HANDOFF），高位存储task_struct指针。
- RCU的核心设计是读侧零开销（不加锁、不原子、不屏障），通过宽限期（grace period）保证读者完成后才释放旧数据。RCU读侧临界区也可用于链表遍历（list_for_each_entry_rcu），写侧用spinlock保护修改。变体包括Classic/SRCU/RCU-sched/Tasks RCU（rcu_read_lock_trace）。
- WW Mutex（Wound-Wait）用于GPU/DRM等多锁场景，通过ww_acquire_ctx事务化锁获取避免死锁；Local Lock封装preempt_disable/irq_disable语义；Bit Spinlock在单bit上实现锁（如page->flags），极低内存开销。
- 锁选择决策树：中断上下文→spinlock+irqsave；进程上下文→看临界区时长，<微秒用spinlock、>微秒用mutex、读多写少短CS用RWLock/长CS用RW Semaphore、读极多用RCU。

## 关键细节

### 锁分类全景

| 范式 | 机制 | 适用上下文 | 适用时长 | 特性 |
|------|------|-----------|---------|------|
| 忙等 | spinlock | 中断/进程 | <微秒 | 关抢占，忙等不睡眠，qspinlock/MCS |
| 忙等 | rwlock | 中断/进程 | <微秒 | 读写分离，多读者并行，写者独占 |
| 忙等 | seqlock | 进程 | <微秒 | 读不锁，写互斥，读侧需校验序列号 |
| 忙等 | bit spin | 进程 | 极短 | 单bit锁，极低内存开销（page->flags） |
| 忙等 | local lock | 进程 | 无锁区 | preempt_disable/irq_disable封装 |
| 睡眠 | mutex | 进程 | >微秒 | 乐观自旋+睡眠，PI支持，owner编码 |
| 睡眠 | rwsem | 进程 | 毫秒+ | 读写分离，睡眠版，downgrade_write |
| 睡眠 | semaphore | 进程 | 毫秒+ | 计数信号量，无PI，资源池 |
| 睡眠 | rt_mutex | 进程 | 毫秒+ | 优先级继承，实时系统，PREEMPT_RT基础 |
| 睡眠 | ww_mutex | 进程 | 毫秒+ | Wound-Wait事务锁，GPU/DRM多锁 |
| 无锁 | RCU | 进程 | 读零开销 | 宽限期机制，写侧重，链表遍历 |
| 无锁 | atomic | 任意 | 单操作 | 单个原子操作，refcount |
| 无锁 | per-cpu | 进程 | 无临界区 | 每CPU独立数据，无竞争 |

### Spinlock 三代演进

**第一代：Test-And-Set**
- 最简单的spinlock：循环test-and-set一个标志位（`while (test_and_set(&lock->locked))`）
- 问题：无公平性，可能导致饥饿——后来的等待者可能先获得锁；cache line bouncing严重

**第二代：Ticket Lock（Linux 早期采用）**
- 原理：像排队取票，每位顾客有号码，按号码顺序服务
- 实现：`next`字段（下一个可用票号）+ `owner`字段（当前服务号）；获取时 `atomic_fetch_add(&next, 1)`
- 优势：FIFO公平性，按获取顺序排队，避免饥饿
- 问题：所有等待者检查同一 `owner` 变量，缓存行竞争严重（cache line contention）

**第三代：MCS Lock / Queued Spinlock（现代 Linux，x86）**
- 原理：每个等待者在自己的local变量上spin，形成链表队列
- 实现：每个CPU一个 `mcs_spinlock` 节点（`next`指针 + `locked`本地变量），prev→next链表传递锁
- x86 qspinlock结构：`locked`(u8) + `pending`(u8) + `tail`(u16队列尾部CPU编码)
  - 快速路径：`atomic_try_cmpxchg_acquire(&val, 0, 1)` 直接获取
  - 慢速路径：加入MCS队列尾部，在自己的本地变量上自旋（避免缓存争用）
- ARM64实现：LSE（Large System Extensions）原子指令（LDAXR/STXR独占访问） + WFE（Wait For Event）低功耗等待——锁释放时发SEV唤醒等待者，比纯自旋更节能
- 优势：每个CPU只spin自己的local变量，大幅减少缓存行争用，NUMA系统性能优异

### raw_spinlock vs spinlock

在 PREEMPT_RT 内核中：
- `raw_spinlock` — 真正的忙等，关抢占，不允许睡眠，不受RT影响，用于调度器/中断核心代码
- `spinlock` — 可能被编译为 `rt_mutex_base`（睡眠锁），可抢占，保持API兼容，用于一般驱动/文件系统
- 非 PREEMPT_RT 内核中：`spinlock` 内部直接包裹 `raw_spinlock`，两者等价 ^[inferred]
- 使用规则：调度器、中断核心代码 → 必须用 `raw_spinlock`；一般驱动、文件系统 → 用 `spinlock`

### Spinlock 的内存屏障语义

Spinlock 的 acquire/release 操作隐含内存屏障，这是锁能正确工作的底层保证：
- `spin_lock`（acquire语义）：保证临界区内的读/写不被重排到锁获取之前
- `spin_unlock`（release语义）：保证临界区内的读/写不被重排到锁释放之后
- `queued_spin_lock` 快速路径用 `atomic_try_cmpxchg_acquire`，慢速路径节点间用 `atomic_set_release`
- 在弱内存序架构（ARM64/PowerPC）上屏障至关重要；x86 TSO模型下多数屏障是no-op，但编译器屏障仍生效
- 详见 [[concepts/memory-barriers]] 和 [[concepts/cpu-cache-coherence]] ^[inferred]

### Spinlock API 变体

| API | 关中断 | 保存IRQ标志 | 关softirq | 适用场景 |
|-----|--------|-----------|-----------|---------|
| spin_lock | 否 | 否 | 否 | 进程上下文，无中断干扰 |
| spin_lock_irq | 是 | 否 | 否 | 进程上下文，需关硬中断 |
| spin_lock_irqsave | 是 | 是 | 否 | 不确定当前中断状态（最安全） |
| spin_lock_bh | 否 | 否 | 是 | 进程上下文，需关softirq |

**决策规则**：
- 中断上下文 → 必须用 spin_lock_irqsave（最安全）
- 进程上下文且与中断共享数据 → spin_lock_irqsave
- 进程上下文且只与softirq共享数据 → spin_lock_bh
- 进程上下文且无中断共享 → spin_lock（但irqsave是更安全的默认选择） ^[inferred]

### Mutex 设计

Mutex 是内核主要的睡眠锁，相比 semaphore 有多项改进（`struct mutex` 含 `owner`/`count`/`wait_lock`/`wait_list`/`osq`）：

**乐观自旋（Optimistic Spinning）**：
- 释放前短暂spin等待（osq_lock，CONFIG_MUTEX_SPIN_ON_OWNER），避免立即睡眠的上下文切换开销（~5-10μs）
- 自旋条件：owner正在运行（on_cpu）+ 只有一个等待者 + 无更高优先级任务等待 + 自旋次数未超限
- owner离开CPU则立即睡眠（schedule）

**优先级继承（Priority Inversion Prevention）**：
- rt_mutex 内嵌在 mutex 中（CONFIG_RT_MUTEX），低优先级持锁者被高优先级等待者临时提升优先级
- 避免经典优先级反转问题：Task L持锁→Task M抢占L→Task H等锁死等；PI临时提升L到H优先级，L快速释放后H获取

**owner 字段编码**：
- `atomic_long_t owner`：高位存储持锁者task_struct指针
- 低2位编码状态标志：bit0 = `MUTEX_FLAG_WAITERS`（有等待者），bit1 = `MUTEX_FLAG_HANDOFF`（正在交接）
- 等待者可直接从owner找到持锁者，触发PI提升

**严格所有权语义**：
- mutex有明确owner，只有持有者才能释放（`mutex_unlock`）
- 不允许递归获取同一mutex（会死锁）
- 嵌套不同锁时需保持全局统一的获取顺序

### RCU 机制

RCU（Read-Copy-Update）是读侧零开销的同步机制：

**读侧**：
- 不加锁、不做原子操作、不使用内存屏障
- 读者只需要在RCU读侧临界区内（`rcu_read_lock`/`rcu_read_unlock`）
- 开销接近于零——仅标记 preempt_count 防止抢占
- 支持链表无锁遍历：`list_for_each_entry_rcu`

**写侧（宽限期机制）**：
1. 写者创建新数据副本，修改副本
2. 用 `rcu_assign_pointer()` 替换旧指针为新指针（含release屏障语义）
3. 等待宽限期（grace period）——所有读者退出临界区
4. 宽限期结束后，回调函数释放旧数据（`kfree_rcu` 或 `call_rcu`）

**链表操作模式**：写侧修改（`list_add_rcu`/`list_del_rcu`）需用spinlock保护，删除后用 `kfree_rcu` 延迟释放旧节点。

**宽限期检测**：
- Classic RCU：检测所有CPU经过静止状态（quiescent state）
- SRCU：可睡眠的RCU，用srcu_struct计数器检测
- RCU-sched：基于调度器上下文切换检测（`rcu_read_lock_sched`）
- RCU-bh：基于softirq上下文检测
- Tasks RCU：基于任务跟踪（`rcu_read_lock_trace`）

**RCU变体**：

| 变体 | 读侧开销 | 可睡眠 | 适用场景 |
|------|---------|--------|---------|
| Classic RCU | 极低（关抢占） | 否 | 通用内核数据 |
| SRCU | 低（计数器） | 是 | 可睡眠路径 |
| RCU-sched | 极低 | 否 | 调度器相关 |
| RCU-bh | 极低 | 否 | softirq/网络相关 |
| Tasks RCU | 低 | 是 | 任务级跟踪 |

### RWLock（读写自旋锁）

- 多读者并行，写者独占；忙等，任意上下文可用
- 读锁API：`read_lock`/`read_lock_irqsave`/`read_trylock`
- 写锁API：`write_lock`/`write_lock_irqsave`/`write_trylock`
- **缺点**：写者饥饿（新读者不断到来导致写者无限等待）；读侧每次都要原子更新计数器，高并发读时缓存行争用严重

### Seqlock（顺序锁）

- 写者用spinlock保护，通过序列号标记写入状态（奇数=正在写，偶数=写完）
- 读者无锁读取，通过校验序列号判断是否需重试
- API：`write_seqlock`/`write_sequnlock`/`read_seqbegin`/`read_seqretry`
- 适用：读极多、读操作快速、数据可容忍短暂不一致后重试（经典应用：时间读取、统计计数器）
- 不适合：读者需修改数据、复杂数据结构（指针/链表）、写操作频繁

### 扩展锁类型

**RT Mutex（实时互斥锁）**：支持优先级继承，`struct rt_mutex` 含 `wait_lock`/`waiters`(红黑树)/`owner`，用于实时系统和PREEMPT_RT基础。

**WW Mutex（Wound-Wait Mutex）**：用于GPU/DRM等多锁获取场景。通过 `ww_acquire_ctx` 事务化锁获取，解决无序获取的死锁问题。冲突时通过wound（伤害）或wait策略回滚重试。

**Local Lock**：封装 `preempt_disable`/`local_irq_disable` 语义，替代隐式的禁用操作，提供可调试的API（`local_lock`/`local_lock_irq`/`local_lock_irqsave`）。

**Bit Spinlock**：在单个bit上实现自旋锁（`bit_spin_lock`/`bit_spin_unlock`），用于 `page->flags` 等位域，极低内存开销。

### 性能对比

相对开销比较（基准：无操作=1x，无竞争单次操作）：

| 机制 | 相对开销 | 无竞争周期 | 说明 |
|------|---------|-----------|------|
| 无操作 | 1x | — | 基准 |
| per-cpu | 2.5x | — | 无竞争 |
| atomic_inc | 3x | — | 单个原子操作 |
| seqlock(读) | 3x | — | 序列号校验 |
| RCU(读) | 3x | — | 关抢占开销极小 |
| spinlock | 4x | lock:~50-100, unlock:~10-20 | 忙等+内存屏障 |
| rwlock(读) | 5x | — | 原子更新计数器 |
| rwsem(读) | 6x | — | 睡眠版读写 |
| mutex | 6x | ~100-200 | 上下文切换开销 |
| semaphore | 8x | ~200-300 | 直接上下文切换 |

**持锁时间 vs 锁选择**：`<100 cycles` → atomic/无锁；`<1μs` → spinlock；`>1μs` → 考虑mutex；`>10μs` → 必须mutex；`>1ms` → mutex或semaphore。

> 注：实际性能取决于硬件、竞争程度、持锁时间。有竞争时spinlock持续消耗CPU，mutex短暂自旋+上下文切换，semaphore直接上下文切换。

## 未解问题

- PREEMPT_RT 对 spinlock 转换为 rt_mutex 的完整影响——是否所有spinlock都应被转换？调度器和中断核心用raw_spinlock豁免，其余被转换的spinlock在中断上下文的行为如何？ ^[ambiguous]
- RCU宽限期的精确延迟在不同负载下的表现——高负载下宽限期可能显著延长（`synchronize_rcu` 典型 ~10-100ms）。 ^[inferred]
- RWLock的写者饥饿问题在哪些内核版本中是否已有缓解策略？ ^[inferred]

## Mutex vs Spinlock vs Semaphore 核心对比

| 特性 | Spinlock | Mutex | Semaphore |
|------|---------|-------|-----------|
| 等待方式 | 忙等待（自旋） | 睡眠+乐观自旋 | 睡眠等待 |
| 上下文限制 | 任意上下文 | 仅进程上下文 | 仅进程上下文 |
| 所有权 | 无 | 有（严格） | 无 |
| 计数语义 | 0/1（二值） | 0/1（二值） | 任意正整数 |
| 递归获取 | 需特殊处理 | 不支持 | 不支持 |
| 优先级继承 | 不支持 | 支持（rt_mutex） | 不支持 |
| 乐观自旋 | 内置 | 支持（可选） | 不支持 |
| 持锁时睡眠 | 绝对禁止 | 允许 | 允许 |


## 延伸阅读

- 实操指南：[[skills/linux-lock-selection]]
- 内存屏障与acquire/release语义：[[concepts/memory-barriers]]
- CPU缓存一致性与锁的缓存行为：[[concepts/cpu-cache-coherence]]
- IO模型与锁的关系：[[concepts/linux-io-models]]

## 来源

- 原文：`raw/sources/Linux 操作系统/Linux 锁机制/1 Linux 锁机制全景介绍.md`（74KB，2026-11-10 重蒸馏）
- [[summaries/linux-rcu-lock]] — RCU机制详解
- [[summaries/linux-softirq-detail]] — softirq与RCU-bh的关系
- [[summaries/linux-network-protocol-stack-impl]] — 网络栈中spinlock_bh的使用场景