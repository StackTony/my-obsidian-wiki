---
title: Linux RCU 锁详解
created: 2026-06-01
updated: 2026-06-01
tags: [linux, kernel, rcu, lock, synchronization]
category: summaries
source_dir: Linux 操作系统/Linux 锁机制
source_files: [Linux RCU锁.md]
summary: RCU读零开销哲学：宽限期机制、Tree RCU分层检测、SRCU可睡眠变体与适用条件
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: "2026-06-01"
tier: supporting
---

# Linux RCU 锁详解

RCU（Read-Copy-Update）是 Linux 内核最独特的同步机制，实现"读者零开销"的极致性能。核心哲学：读操作不需要与写操作同步，只需看到一致的数据版本。

## 核心思想与传统锁对比

传统锁困境：读者即使无冲突也有 lock/unlock 开销，读多写少场景下成为瓶颈。

RCU 突破：
- 读者：直接读（无锁），约 15-30 CPU cycles
- 写者：复制 → 修改副本 → 替换指针 → 等待宽限期 → 释放旧数据

代价：写者延迟释放数据，内存短暂增加。

对比：spinlock ~100-200 cycles，mutex ~200-500 cycles，rwlock ~50-100 cycles。RCU 读侧仅为传统锁的 1/10 ~ 1/20。

## 宽限期机制

宽限期是从写者替换指针开始，到所有"在替换前进入"的旧读者退出临界区的时间段。替换指针后进入的读者看到新数据，不影响宽限期。

静止点（Quiescent State）：上下文切换、进入 idle、进入用户态 — 这些时刻一定不在 RCU 读临界区。

## 写者与读者流程

**写者**：
1. `kmalloc` 新副本，复制旧数据
2. 修改副本（不影响旧数据）
3. `rcu_assign_pointer(global_ptr, new)` — 原子替换，含内存屏障
4. `synchronize_rcu()` 阻塞等待宽限期，或 `call_rcu(&old->rcu, callback)` 异步回调
5. `kfree(old)` 释放旧数据

**读者**：
1. `rcu_read_lock()` — 实际是 `preempt_disable()`
2. `rcu_dereference(global_ptr)` — 带内存屏障的指针读取
3. 使用数据（只读！）
4. `rcu_read_unlock()` — `preempt_enable()`

## Tree RCU 分层检测

大规模系统（数百 CPU）宽限期检测开销大。Tree RCU 采用分层树状结构：
- CPU 报告静止 → 叶节点汇总 → 上层节点汇总 → 根节点完成
- 复杂度 O(log N) 而非 O(N)

## RCU 变体

| 变体 | 读侧特点 | 适用场景 |
|------|----------|----------|
| Classic RCU | 不可睡眠（preempt_disable） | 内核通用同步 |
| SRCU | 可睡眠 | 需要调用 copy_to_user、等待 I/O |
| RCU-sched | 禁用抢占 | 调度器相关 |
| RCU-bh | 禁用软中断 | 网络软中断路径 |
| Tiny RCU | 单 CPU 优化 | 嵌入式/单核系统 |

SRCU 需要显式定义 `srcu_struct`，读写侧 API 返回索引，开销更大。原则：能用 Classic 就用 Classic，只有确实需要睡眠时才用 SRCU。

## 常见错误

1. **读者修改数据** — 多读者并发修改导致数据损坏
2. **过早释放** — 替换指针后立即 kfree，旧读者访问已释放内存
3. **经典 RCU 中睡眠** — 基于 preempt_disable，睡眠违反语义，导致宽限期无法结束
4. **忘记 rcu_dereference** — 缺少内存屏障，可能看到旧指针
5. **忘记 rcu_assign_pointer** — 缺少内存屏障，读者可能暂时看不到新指针

## 适用条件判断

经验法则：
- 读/写 > 100:1 → RCU 明显优于传统锁
- 读/写 10:1 - 100:1 → 考虑 RCU（需分析）
- 读/写 < 10:1 → RWLock 或 RW Semaphore
- 读/写 ~1:1 → Mutex 或 Spinlock

其他因素：数据大小（复制开销）、读侧是否需要睡眠、内存压力。

## 内核典型应用

- VFS：dentry 缓存查找、inode 查找
- 网络：路由表查找、网络设备列表
- 进程：task_struct 部分字段、PID 查找
- 定时器：timer_base 管理
- 安全：LSM 钩子、SELinux 策略

## 调试工具

- RCU Stall 检测：宽限期无法结束时内核打印警告
- `/sys/kernel/debug/rcu/rcu_data` — 各 CPU RCU 状态
- Ftrace 追踪：`events/rcu/` 下的追踪点
- CONFIG_PROVE_RCU — lockdep 检测 RCU 语义

## 来源

- `Linux 操作系统/Linux 锁机制/Linux RCU锁.md` — RCU 原理、API、变体与常见错误

## 相关概念

- [[concepts/linux-lock-mechanisms]] — Linux 锁机制全景
- [[summaries/linux-softirq-detail]] — RCU-bh 与软中断的关系