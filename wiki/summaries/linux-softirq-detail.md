---
title: Linux软中断实现细节
category: summaries
tags: [linux, 内核, softirq, 中断, ksoftirqd]
source_dir: Linux 操作系统/Linux 中断系统
source_files: [Linux ksoftirqd软中断内核线程详解.md, "Linux 硬中断irq + 软中断softirq原理.md", Linux 软中断softirq.md]
summary: Linux软中断下半部实现：__do_softirq预算控制(MAX_SOFTIRQ_TIME/RESTART)、ksoftirqd兜底线程、preempt_count防抢占、tasklet同类型串行保证。
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

# Linux软中断实现细节

软中断(softirq)是Linux中断下半部的核心机制，在硬中断(IRQ)上半部快速响应后，延迟处理复杂逻辑。

## 核心观点

### __do_softirq预算控制

每次软中断处理有严格预算防止霸占CPU：
- **MAX_SOFTIRQ_TIME**：不超过2 jiffies(约10ms)
- **MAX_SOFTIRQ_RESTART**：循环重启不超过10次
- 超过限制则唤醒ksoftirqd在进程上下文兜底处理^[inferred]

### ksoftirqd内核线程

每个CPU一个ksoftirqd线程(ksoftirqd/0, ksoftirqd/1...)，当软中断过多时兜底：
- `ksoftirqd_should_run()`检查pending软中断
- `run_ksoftirqd()`调用`__do_softirq()`处理
- 监控：`/proc/softirqs`显示per-CPU软中断统计；`top`命令`si`字段显示软中断CPU占用

### 软中断两条执行路径

1. **硬中断退出路径**：`irq_exit()` → `invoke_softirq()` → `__do_softirq()`（优先）
2. **ksoftirqd调度路径**：softirq过多时由ksoftirqd线程在进程上下文处理（兜底）

### tasklet串行保证

tasklet基于softirq(HI_SOFTIRQ/TASKLET_SOFTIRQ)实现，关键串行保证：
- 同类型tasklet不会在不同CPU上并发执行（`test_and_set_bit`原子操作）
- 不同类型tasklet可在不同CPU上并行^[inferred]

### 临界区保护选择

| 场景 | 保护方式 |
|------|----------|
| 跨核共享数据 | `spin_lock` |
| 同核进程上下文 | `spin_lock_bh`（禁止softirq，允许硬中断） |

## 来源

- [[concepts/linux-interrupt-system]] — 中断系统整体框架
- [[concepts/linux-lock-mechanisms]] — spin_lock_bh用于softirq临界区保护
- `raw/sources/Linux 操作系统/Linux 中断系统/Linux ksoftirqd软中断内核线程详解.md`
- `raw/sources/Linux 操作系统/Linux 中断系统/Linux 硬中断irq + 软中断softirq原理.md`
- `raw/sources/Linux 操作系统/Linux 中断系统/Linux 软中断softirq.md`