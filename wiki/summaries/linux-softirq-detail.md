---
title: Linux软中断实现细节
category: summaries
tags: [linux, 内核, softirq, 中断, ksoftirqd]
relationships:
  - target: "[[concepts/linux-interrupt-system]]"
    type: related_to
  - target: "[[concepts/linux-lock-mechanisms]]"
    type: uses
source_dir: Linux 操作系统/Linux 中断系统
source_files: ["Linux 软中断内核线程 ksoftirqd详解.md", "Linux 硬中断 irq + 软中断 softirq原理.md", "Linux 软中断 softirq.md"]
summary: Linux软中断下半部实现：设计由来(快vs复杂的矛盾)、softirq静态注册与raise触发、__do_softirq预算控制、ksoftirqd兜底、preempt_count防重入、tasklet串行保证与临界区保护选择。
provenance:
  extracted: 0.80
  inferred: 0.15
  ambiguous: 0.05
base_confidence: 0.775
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: supporting
created: 2026-06-01
updated: 2026-11-09
---

# Linux软中断实现细节

软中断(softirq)是Linux中断下半部的核心机制。IRQ handler 有内在矛盾：执行必须非常快（否则事件与数据丢失），但要做的事可能非常多（如收包的协议栈处理）——因此 Linux 将中断处理一分为二：上半部硬中断只做最紧急的响应后立刻释放 CPU，下半部 softirq 在开中断环境下延迟执行耗时任务。

## 核心观点

### softirq 的注册与触发（静态机制）

softirq 是**编译时确定的静态机制**，新增类型需修改并重新编译内核，因此直接使用者很少（网络收发等核心路径），驱动开发多用构建在其上的 tasklet。

- **注册**：`open_softirq(nr, action)` 把 handler 写入 `softirq_vec[NR_SOFTIRQS]` 数组（如 `open_softirq(NET_RX_SOFTIRQ, net_rx_action)`）。
- **触发三阶段**：① `open_softirq` 注册 → ② `raise_softirq()` 将软中断标记为 pending（内部 `raise_softirq_irqoff` 在 `!in_interrupt()` 时顺带 `wakeup_softirqd`）→ ③ 内核调度执行对应 handler。
- 5.10 内核定义 10 种（HI/TIMER/NET_TX/NET_RX/BLOCK/IRQ_POLL/TASKLET/SCHED/HRTIMER/RCU），即 `cat /proc/softirqs` 看到的条目。

### __do_softirq 预算控制

每次软中断处理有严格预算防止霸占CPU，用户态线程只能等待（`top` 的 `si` 字段即软中断开销）：

- **MAX_SOFTIRQ_TIME**：不超过 2 jiffies（200Hz 系统约 10ms）
- **MAX_SOFTIRQ_RESTART**：循环重启不超过 10 次
- 执行循环：`ffs(pending)` 从低位（最高优先级）开始逐个执行 `h->action(h)`；清空 pending 后再次检查，须同时满足 `time_before(jiffies, end) && !need_resched() && --max_restart` 三条件才 `goto restart`，否则 `wakeup_softirqd()` 兜底。
- 进入时 `__local_bh_disable_ip(_RET_IP_, SOFTIRQ_OFFSET)` 增加 preempt_count 软中断域计数，退出时对称减少——标记"当前处于软中断上下文"。整个过程借用被中断任务的上下文执行 ^[inferred]（代码里特意 mask 掉 `PF_MEMALLOC` 再恢复，防止网络收包等 handler 借用上下文污染内存分配语义）。

### ksoftirqd 内核线程

每个CPU一个 ksoftirqd/%u 线程，通过 `smpboot_register_percpu_thread` 注册 `ksoftirqd_should_run`/`run_ksoftirqd` 回调，由 `kernel/smpboot.c` 的事件驱动循环调度：

- `ksoftirqd_should_run()` 检查本核 pending 软中断，有则 `run_ksoftirqd()` → `__do_softirq()` 兜底处理
- 唤醒条件：`wakeup_softirqd()` 仅在 `tsk->state != TASK_RUNNING` 时 `wake_up_process(tsk)`
- 监控：`/proc/softirqs` 显示 per-CPU 软中断统计；`top` 的 `si` 字段显示软中断 CPU 占用
- 软中断频率过高时，即便有 ksoftirqd 兜底仍可能处理不及时，引发网络收发延迟、调度缓慢等性能问题——预算机制只是缓解，根治需配合硬件侧 IRQ 亲和性/RPS 分担（见 [[summaries/nic-smp-irq-affinity]]）

### 软中断两条执行路径

1. **硬中断退出路径**：`do_IRQ()` → `irq_exit()` 检查 `!in_interrupt() && local_softirq_pending()` → `invoke_softirq()` → `__do_softirq()`（优先路径）
2. **ksoftirqd 调度路径**：软中断过多、超出预算时由 ksoftirqd 线程在进程上下文处理（兜底）

### 抢占与防重入

- `in_interrupt()` 非零（处于任何中断上下文）则不允许再进入软中断执行——**软中断本身不可嵌套**；但软中断执行期间开中断，硬中断可以打断它。
- ARM 上中断返回路径（`__irq_svc`）：恢复现场前检查 `TIF_NEED_RESCHED` 且 `preempt_count==0` 时执行调度（svc_preempt），实现内核可抢占——抢占条件与软中断上下文计数直接挂钩 ^[inferred]。

### tasklet：动态机制，基于 softirq

tasklet 是**运行时可创建初始化的 softirq**，基于两个 per-CPU 链表：

- `tasklet_vec`（普通，回调 `tasklet_action`）与 `tasklet_hi_vec`（高优先级，回调 `tasklet_hi_action`），分别挂在 TASKLET_SOFTIRQ 与 HI_SOFTIRQ 上
- 执行时先把本核链表整体摘下（`local_irq_disable` 保护摘链过程），再逐个 `tasklet_trylock` 后执行 `func`；`TASKLET_STATE_SCHED` 状态防止同一 tasklet 重复入队
- **串行保证**：同一 tasklet 不会在多个 CPU 上并发执行（原子置位 RUN 状态）；不同 tasklet 可在不同 CPU 并行 ^[inferred]

### 临界区保护选择

| 场景 | 保护方式 |
|------|----------|
| 仅跨核进程上下文共享数据 | `spin_lock` |
| 数据被软中断/tasklet 上下文共享 | `spin_lock_bh`（禁止本核 softirq，允许硬中断） |
| 数据被硬中断上下文共享 | `spin_lock_irqsave`（保存并关闭本地中断） |

### 收包场景示例（NET_RX_SOFTIRQ）

- IRQ handler **不执行 NAPI，只触发它**：`napi_schedule()` 后 `raise NET_RX_SOFTIRQ`；真正收包在 softirq 中调用网卡 `poll()` 方法
- 处理该包的 softirq 与 IRQ 在**同一个 CPU** 运行：大量包进同一 RX queue 时 IRQ 开销不大，但该核被 softirq 占满
- 解决：RPS 把包重新分发（RXQ→CPU），不降延迟只做均衡；RFS 进一步让软中断处理 CPU 与应用所在 CPU 同核，利用 cache 局部性

## 延伸阅读

实操指南：[[skills/linux-kernel-debugging]]（softirq/中断监控命令）

## 未解问题

- PREEMPT_RT 实时内核将中断线程化后，ksoftirqd 与 `[irq/xxx]` 线程的优先级协调关系。 ^[inferred]
- `raise_softirq` 在硬中断上下文中只标记 pending 不唤醒 ksoftirqd 的完整语义（唤醒依赖 irq_exit 路径接力）。 ^[inferred]

## 来源

- `raw/sources/Linux 操作系统/Linux 中断系统/Linux 软中断内核线程 ksoftirqd详解.md`
- `raw/sources/Linux 操作系统/Linux 中断系统/Linux 硬中断 irq + 软中断 softirq原理.md`
- `raw/sources/Linux 操作系统/Linux 中断系统/Linux 软中断 softirq.md`
- [[concepts/linux-interrupt-system]] — 中断系统整体框架
- [[concepts/linux-lock-mechanisms]] — spin_lock_bh 用于 softirq 临界区保护
- [[summaries/nic-smp-irq-affinity]] — 硬件侧中断亲和性调优（与本页 softirq 均衡配对）
