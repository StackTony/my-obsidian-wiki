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
source_dir: Linux 操作系统/Linux 锁机制
source_files: [Linux 锁机制全景介绍.md, Linux SpinLock锁.md, Linux Mutex锁.md, Linux RCU锁.md, "Linux 锁机制全景介绍.md"]
summary: Linux内核同步机制完整框架：从Spinlock到RCU的演进与选择指南。Spinlock忙等(微秒级)、Mutex睡眠锁(乐观自旋+PI)、RCU读零开销(宽限期机制)。决策树指导锁选择。
provenance:
  extracted: 0.75
  inferred: 0.20
  ambiguous: 0.05
base_confidence: 0.85
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: core
created: 2026-06-01
updated: 2026-06-11
---

# Linux锁机制全景

Linux内核同步机制是理解内核并发控制的核心框架，从忙等到睡眠再到无锁，三种范式各有适用场景。Spinlock适合中断上下文的微秒级保护，Mutex适合进程上下文的毫秒级互斥，RCU则追求读侧零开销的极致性能。

## 核心观点

- 内核同步机制分三大范式：忙等（spinlock/seqlock/bit spin）、睡眠（mutex/semaphore/rwsem）、无锁（RCU/atomic/per-cpu），选择取决于执行上下文和临界区时长。
- Spinlock经历了三代演进：Test-And-Set→Ticket→MCS/Queued，x86用qspinlock、ARM64用LSE+WFE，不同架构的实现路径不同。
- raw_spinlock 与 spinlock 在 PREEMPT_RT 下语义不同：raw_spinlock 不允许抢占（真正的忙等），spinlock 可被转化为 mutex。 ^[inferred]
- Mutex 引入乐观自旋（optimistic spinning）和优先级继承（PI），owner字段编码持锁者信息，显著改善了传统semaphore的性能和实时性。
- RCU的核心设计是读侧零开销（不加锁、不原子、不屏障），通过宽限期（grace period）保证读者完成后才释放旧数据，代价是写侧较重。
- 锁选择决策树：中断上下文→spinlock+irqsave；进程上下文→看临界区时长，<微秒用spinlock、>微秒用mutex、读多写少用RCU。

## 关键细节

### 锁分类全景

| 范式 | 机制 | 适用上下文 | 适用时长 | 特性 |
|------|------|-----------|---------|------|
| 忙等 | spinlock | 中断/进程 | <微秒 | 关抢占，忙等不睡眠 |
| 忙等 | seqlock | 进程 | <微秒 | 读不锁，写互斥，读侧需校验序列号 |
| 忙等 | bit spin | 进程 | 极短 | 单bit锁，极低内存开销 |
| 睡眠 | mutex | 进程 | >微秒 | 乐观自旋+睡眠，PI支持 |
| 睡眠 | semaphore | 进程 | 毫秒+ | 计数信号量，无PI |
| 睡眠 | rwsem | 进程 | 毫秒+ | 读写分离，写者优先 |
| 无锁 | RCU | 进程 | 读零开销 | 宽限期机制，写侧重 |
| 无锁 | atomic | 任意 | 单操作 | 单个原子操作 |
| 无锁 | per-cpu | 进程 | 无临界区 | 每CPU独立数据，无竞争 |

### Spinlock 三代演进

**第一代：Test-And-Set**
- 最简单的spinlock：循环test-and-set一个标志位
- 问题：不公平（先抢到的总是赢），cache line bouncing严重

**第二代：Ticket Lock**
- 掟理：像排队取票，每位顾客有号码，按号码顺序服务
- 实现：owners字段当前服务号 + next字段下一个票号
- 优势：保证公平（FIFO顺序），避免饥饿
- 问题：所有等待者spin在同一个变量上，cache line bouncing仍然严重

**第三代：MCS Lock / Queued Spinlock**
- 原理：每个等待者在自己的local变量上spin，形成链表队列
- 实现：每个CPU一个mcs_node，prev→next链表传递锁
- 优势：每个CPU只spin自己的local变量，无cache line bouncing
- x86实现：qspinlock（queued spinlock），2字节锁+per-cpu node队列
- ARM64实现：LSE（Large System Extensions）原子指令 + WFE（Wait For Event）低功耗等待

### raw_spinlock vs spinlock

在 PREEMPT_RT 内核中：
- `raw_spinlock` — 真正的忙等，关抢占，不允许睡眠，中断上下文可用
- `spinlock` — 可能被转化为 rt_mutex（睡眠锁），可抢占
- 非 PREEMPT_RT 内核中两者等价 ^[inferred]

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

Mutex 是内核主要的睡眠锁，相比 semaphore 有多项改进：

**乐观自旋（Optimistic Spinning）**：
- 释放前短暂spin等待（osq_lock），避免立即睡眠的上下文切换开销
- 仅在 owner 正在运行（on_cpu）时自旋，owner离开CPU则立即睡眠

**优先级继承（Priority Inversion Prevention）**：
- 低优先级持锁者被高优先级等待者临时提升优先级
- 避免经典优先级反转问题：低优先级持锁→中优先级抢占低→高优先级等锁死等

**owner 字段编码**：
- mutex.owner 存储持锁者task_struct指针
- 低3位编码状态标志：0=未锁、1=已锁无等待者、2=已锁有等待者
- 等待者可直接从owner找到持锁者，触发PI提升

### RCU 机制

RCU（Read-Copy-Update）是读侧零开销的同步机制：

**读侧**：
- 不加锁、不做原子操作、不使用内存屏障
- 读者只需要在RCU读侧临界区内（rcu_read_lock/rcu_read_unlock）
- 开销接近于零——仅标记 preempt_count 防止抢占

**写侧（宽限期机制）**：
1. 写者创建新数据副本，修改副本
2. 用 rcu_assign_pointer() 替换旧指针为新指针
3. 等待宽限期（grace period）——所有读者退出临界区
4. 宽限期结束后，回调函数释放旧数据

**宽限期检测**：
- Classic RCU：检测所有CPU经过静止状态（quiescent state）
- SRCU：可睡眠的RCU，用srcu_struct计数器检测
- RCU-sched：基于调度器上下文切换检测
- RCU-bh：基于softirq上下文检测

**RCU变体**：

| 变体 | 读侧开销 | 可睡眠 | 适用场景 |
|------|---------|--------|---------|
| Classic RCU | 极低（关抢占） | 否 | 通用内核数据 |
| SRCU | 低（计数器） | 是 | 可睡眠路径 |
| RCU-sched | 极低 | 否 | 调度器相关 |
| RCU-bh | 极低 | 否 | softirq/网络相关 |

### 性能对比

相对开销比较（基准：无锁直接访问=1x）：

| 机制 | 相对开销 | 说明 |
|------|---------|------|
| per-cpu | 1x | 无竞争 |
| RCU读侧 | ~1x | 关抢占开销极小 |
| atomic | ~3x | 单个原子操作 |
| spinlock | ~4x | 忙等+内存屏障 |
| mutex | ~8x | 上下文切换开销 |

## 未解问题

- PREEMPT_RT 对 spinlock 转换为 rt_mutex 的完整影响——是否所有spinlock都应被转换？ ^[ambiguous]
- RCU宽限期的精确延迟在不同负载下的表现——高负载下宽限期可能显著延长。 ^[inferred]


## 延伸阅读

实操指南：[[skills/linux-lock-selection]]

## 来源

- [[summaries/linux-rcu-lock]] — RCU机制详解
- [[summaries/linux-softirq-detail]] — softirq与RCU-bh的关系
- [[summaries/linux-network-protocol-stack-impl]] — 网络栈中spinlock_bh的使用场景