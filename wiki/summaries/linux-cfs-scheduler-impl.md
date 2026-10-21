---
title: Linux CFS调度器实现
category: summaries
tags: [linux, 内核, 调度器, CFS, vruntime]
aliases: [CFS实现, 完全公平调度器, sched_class, cfs_rq]
source_dir: Linux 操作系统/Linux 进程调度
source_files: [Linux CFS调度器.md, Linux 完全公平调度器CFS.md]
summary: CFS实现细节：vruntime与权重换算公式、调度周期/延迟(6ms与0.75ms粒度、多核×(1+log2(ncpus)))、rq/cfs_rq/task_group/sched_entity数据结构、五个调度类优先级顺序、六种调度策略枚举与关键函数流程。
provenance:
  extracted: 0.80
  inferred: 0.15
  ambiguous: 0.05
base_confidence: 0.608
lifecycle: draft
lifecycle_changed: 2026-10-21
tier: supporting
created: 2026-10-21
updated: 2026-10-21
---

# Linux CFS调度器实现

两篇 CFS 源码分析文章的蒸馏：一篇讲 vruntime 的计算与关键函数流程，一篇给出 `sched_class` / `cfs_rq` 的结构定义与调度类优先级体系。二者共同构成 [[concepts/linux-process-scheduling]] 的实现层细节。

## 核心观点

- CFS 只负责**普通进程**（fair_sched_class），它的"公平"不是时间片均分，而是让 `cfs_rq` 中所有调度实体（`sched_entity`）的 **vruntime 尽可能接近**。
- **vruntime 是理解 CFS 的唯一钥匙**：它是一个按权重缩放的虚拟时钟，权重越大（nice 越小），同样的实际运行时间对 vruntime 的贡献越小，进程就能红黑树中更靠左、获得更多 CPU。
- CFS 之上还有一层**调度类体系**：五个调度类严格按优先级排序，只有高优先级类无可运行任务时才会轮到下一层——这解释了"实时进程绝对优先"。
- 调度粒度并非固定值：**单个任务的执行时间有下限 0.75ms，且随 CPU 核数按 `(1 + log2(ncpus))` 放大**——核越多，CFS 越倾向于长粒度以摊薄切换开销。 ^[inferred]
- CFS 用**红黑树**（`tasks_timeline`）维护可运行实体，用 `rb_leftmost` 缓存最左（vruntime 最小）节点，使 `pick_next_task` 接近 O(1) 而非 O(log n)。详见 [[concepts/red-black-tree]]。

## 关键细节

### vruntime 与调度周期

**调度周期 / 调度延迟**：

| 条件 | 调度周期 | 粒度（最小执行时间） |
|------|----------|---------------------|
| 单 CPU，就绪任务 ≤ 8 | 6 ms | 0.75 ms |
| 单 CPU，就绪任务 > 8 | 按粒度累加 | 0.75 ms |
| 多 CPU | 单 CPU 周期 × (1 + log2(ncpus)) | 粒度同样放大 |

例：8 核机器上粒度 = 0.75 ms × (1 + log2 8) = 3 ms，调度周期 = 6 ms × 4 = 24 ms。 ^[inferred]

**换算公式**：

```
runtime  = 调度周期 × 进程权重 / 所有进程权重之和
vruntime = runtime × nice_0_weight / weight          # nice_0_weight = 1024
```

源码中通过 `sched_slice()` / `sched_vslice()` 计算，并用定点乘法避免除法：

```
vruntime = (runtime * weight * lw->inv_weight) >> WMULT_SHIFT
```

### 数据结构

| 结构体 | 角色 |
|--------|------|
| `struct rq` | 每个 CPU 一个运行队列，内含各调度类的子队列 |
| `struct cfs_rq` | CFS 专属运行队列 |
| `struct sched_entity` | 调度实体，`task_struct` 内嵌一个；组调度时还可对应 `task_group` |
| `struct task_struct` | 进程描述符（`prio` / `normal_prio` / `static_prio` 三个优先级字段） |
| `struct task_group` | 组调度（cgroup）单位 |
| `struct sched_class` | 调度类接口（函数指针表） |

**`cfs_rq` 关键字段**：

| 字段 | 含义 |
|------|------|
| `load` | 队列总权重 |
| `nr_running` / `h_nr_running` | 可运行实体数 / 含子层级的可运行数 |
| `min_vruntime` | 队列最小 vruntime，用于新任务入场对齐 |
| `tasks_timeline` | `struct rb_root`，按 vruntime 排序的红黑树 |
| `rb_leftmost` | 缓存最左节点 → `pick_next_task` 快速定位 |
| `curr` / `next` / `last` / `skip` | 当前 / 下一个 / 上一个被抢占 / `sched_yield` 跳过标记 |
| `sched_avg` | 负载跟踪（PELT）统计 |
| `throttled*` | 带宽控制（`CONFIG_CFS_BANDWIDTH`）下的限流状态 |

### 调度类与优先级体系

**五个调度类，优先级从高到低**：

```
stop_sched_class > dl_sched_class > rt_sched_class > fair_sched_class > idle_sched_class
```

**优先级数值范围**（数字越小优先级越高）：

| 类别 | 范围 | 说明 |
|------|------|------|
| 实时（RT） | 0 ~ 99 | 由 `MAX_USER_RT_PRIO = 100` 界定 |
| 普通 | 100 ~ 139 | `MAX_PRIO = MAX_RT_PRIO + NICE_WIDTH = 140` |
| 默认 | 120 | `DEFAULT_PRIO = MAX_RT_PRIO + NICE_WIDTH/2`，对应 nice = 0 |

**调度策略枚举**：

| 值 | 策略 | 归属调度类 |
|----|------|-----------|
| 0 | `SCHED_NORMAL` | fair（即 `SCHED_OTHER` 的内核名） |
| 1 | `SCHED_FIFO` | rt |
| 2 | `SCHED_RR` | rt |
| 3 | `SCHED_BATCH` | fair |
| 5 | `SCHED_IDLE` | fair（主流实现中为极小权重；`idle_sched_class` 服务的是每 CPU idle 线程，二者不同） ^[ambiguous] |
| 6 | `SCHED_DEADLINE` | dl |

### sched_class 接口与关键流程

`struct sched_class` 定义了一组函数指针，调度器核心逻辑通过它调用具体策略：

`enqueue_task` / `dequeue_task` / `yield_task` / `yield_to_task` / `check_preempt_curr` / `pick_next_task` / `put_prev_task` / `select_task_rq` / `set_curr_task` / `task_tick` / `task_fork` / `task_dead` / `switched_from` / `switched_to` / `prio_changed` / `update_curr` / `task_move_group`

核心流程：

| 函数 | 作用 |
|------|------|
| `update_curr()` | 按实际运行时间累加当前实体的 vruntime（加权后的虚拟时间） |
| `task_fork_fair()` | 子进程 vruntime 对齐父进程并减去 `sysctl_sched_child_runs_first` 补偿，避免刚 fork 的孩子饿死 |
| `enqueue_task_fair` / `dequeue_task_fair` | 入队/出队时更新 `min_vruntime`，出队后参与红黑树左端点的更新 |
| `pick_next_task_fair()` | 取红黑树最左节点（`rb_leftmost`）作为下一个运行实体 |
| `task_tick_fair()` | 时钟中断驱动的周期性检查 |
| `yield_task_fair()` | 打 `skip` 标记并把实体放回红黑树**最右端** |
| `put_prev_task_fair()` | 若前一实体仍为 `TASK_RUNNING`，重新插入红黑树最右端 |

### 主调度器 vs 周期调度器

| 调度器 | 触发方式 | 典型入口 |
|--------|----------|----------|
| 主调度器 | 进程主动让出 CPU（阻塞、睡眠、`sched_yield`） | `schedule()` |
| 周期调度器 | 时钟中断周期性检查 | `scheduler_tick()` → `task_tick_fair()` |

**上下文切换**包含两部分成本：切换地址空间（`mm_struct` / CR3）与切换寄存器与内核栈。

## 未解问题

- 两个来源对"调度周期 6ms 与粒度 0.75ms"的表述略有差异（一个直接给数值，一个给公式），具体内核版本的 `sysctl_sched_latency` / `sysctl_sched_min_granularity` 默认值需以源码为准。 ^[ambiguous]
- `CONFIG_CFS_BANDWIDTH` 限流（`throttled` 字段）的完整状态机未展开。 ^[inferred]
- `task_group` 组调度的层级权重换算、以及 cgroup v2 下的行为差异缺少来源。 ^[ambiguous]
- `sched_entity` 的 PELT 负载跟踪（`sched_avg`）只有字段名，无算法推导。 ^[inferred]

## 来源

- [[concepts/linux-process-scheduling]] — 进程调度概念页
- [[concepts/red-black-tree]] — CFS 排序所依赖的红黑树
- [[summaries/linux-softirq-detail]] — 时钟中断/tick 与调度器的触发关系
- `raw/sources/Linux 操作系统/Linux 进程调度/Linux CFS调度器.md`（原文：zhuanlan.zhihu.com/p/556295381）
- `raw/sources/Linux 操作系统/Linux 进程调度/Linux 完全公平调度器CFS.md`（原文：zhuanlan.zhihu.com/p/500583213）
