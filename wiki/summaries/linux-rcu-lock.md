---
title: Linux RCU锁详解
category: summaries
tags: [linux, 内核, rcu, 锁, 同步]
source_dir: Linux 操作系统/Linux 锁机制
source_files: [Linux RCU锁.md]
summary: RCU读零开销哲学：读侧仅preempt_disable约15-30周期、写侧拷贝-修改-替换指针后等宽限期释放旧数据。适用条件：R/W比>100:1。
provenance:
  extracted: 0.80
  inferred: 0.15
  ambiguous: 0.05
base_confidence: 0.775
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: supporting
created: 2026-06-01
updated: 2026-06-01
---

# Linux RCU锁详解

RCU(Read-Copy-Update)的核心哲学：读侧几乎零开销，写侧付出代价。

## 核心观点

### 读侧流程（~15-30周期）

```c
rcu_read_lock()    // preempt_disable
rcu_dereference()  // smp_load_acquire屏障 → 获取指针
// 使用数据（只读！不能修改）
rcu_read_unlock()  // preempt_enable
```

### 写侧流程

```
1. 拷贝旧数据
2. 修改拷贝
3. rcu_assign_pointer() → smp_store_release屏障 → 替换指针
4. synchronize_rcu()阻塞等待 或 call_rcu()异步回调
5. 宽限期结束后释放旧数据
```

### 宽限期(Grace Period)

从指针替换到所有先前读者退出临界区的时间。静止状态(quiescent state)检测点：上下文切换、idle进入、用户态进入——这些时刻确定不在RCU读区。

### Tree RCU分层检测

大规模系统使用分层节点结构检测宽限期，复杂度O(log N)。小系统用Tiny RCU单CPU优化。

### RCU变体

| 变体 | 读侧禁用 | 可否睡眠 | 适用场景 |
|------|----------|---------|----------|
| Classic RCU | preempt_disable | ❌ | 通用内核路径 |
| SRCU | 显式srcu_struct | ✅ | 需要睡眠的路径 |
| RCU-sched | preempt_disable | ❌ | 调度器路径 |
| RCU-bh | local_bh_disable | ❌ | 网络softirq |

### 适用条件

| R/W比 | 建议 |
|-------|------|
| >100:1 | 明确受益 |
| 10:1~100:1 | 可能受益 |
| <10:1 | 需仔细分析 |

### 内核典型使用场景

VFS dentry/inode查找、路由表、设备列表、task_struct字段、LSM hooks、SELinux策略^[inferred]


## 延伸阅读

实操指南：[[skills/linux-lock-selection]]

## 来源

- [[concepts/linux-lock-mechanisms]] — 锁机制全景框架
- [[concepts/linux-interrupt-system]] — RCU读侧使用preempt_disable与中断系统关联
- `raw/sources/Linux 操作系统/Linux 锁机制/Linux RCU锁.md`