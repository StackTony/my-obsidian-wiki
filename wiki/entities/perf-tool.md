---
title: perf性能分析工具
category: entities
tags: [linux, perf, 性能分析, CPU, 采样]
aliases: [perf, linux perf, 性能事件]
relationships:
  - target: "[[concepts/linux-tracing-frameworks]]"
    type: related_to
  - target: "[[concepts/linux-cpu-performance-analysis]]"
    type: related_to
  - target: "[[concepts/linux-io-stack]]"
    type: uses
source_dir: DFX工具
source_files: [==设置trace点==/2 perf工具.md, ==CPU==/perf工具抓取CPU使用率情况.md, ==CPU==/perf工具分析虚拟机的性能事件.md, ==CPU==/perf工具抓取单核CPU的进程调度轨迹.md, ==内存==/perf工具分析slab内存占用.md]
summary: Linux原生性能分析工具perf：基于事件采样原理，支持PMU硬件事件/软件事件/tracepoint事件，提供stat/top/record/report/kmem等子工具覆盖CPU/内存/调度/IO分析。
provenance:
  extracted: 0.80
  inferred: 0.15
  ambiguous: 0.05
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: core
created: 2026-06-02
updated: 2026-06-02
---

# perf性能分析工具

perf 是 Linux 内核原生提供的性能分析工具集，基于事件采样原理，以性能事件为基础支持处理器和操作系统相关指标的剖析。

## 简介

perf 的核心原理：**每隔固定时间在CPU上产生中断，在中断处统计当前pid和函数**，运行时间越多的函数被击中概率越大。CPU周期(cpu-cycles)是默认性能事件。

## 关键属性

| 属性 | 值 |
|------|-----|
| 来源 | Linux内核原生工具 |
| 采样原理 | 基于PMU硬件事件的周期性中断采样 |
| 事件分类 | Hardware Event(PMU) / Software Event(内核计数器) / Tracepoint Event(ftrace) |
| 数据格式 | perf.data 二进制文件 |
| 符号依赖 | 需要 vmlinux(带符号表) 或 debuginfo 包 |

### 性能事件三大类

| 类型 | 来源 | 示例 |
|------|------|------|
| Hardware Event | PMU硬件 | cache命中、cpu-cycles |
| Software Event | 内核计数器 | 进程切换、tick数 |
| Tracepoint Event | ftrace静态tracepoint | slab分配次数 |

查看支持的事件列表：`perf list [hw|sw|cache|tracepoint|event_glob]`

## 与其他实体的关系

- **ftrace** — perf 的 tracepoint 事件基于内核 ftrace 机制
- **火焰图** — perf record 采集的数据经 FlameGraph 脚本转换为可视化火焰图
- **kprobe** — perf 可附加 kprobe 动态探针作为事件源 ^[inferred]
- **crash** — vmcore 分析和 perf 分析互补：前者事后静态、后者运行时动态 ^[inferred]

## 子工具一览

| 子工具 | 功能 | 常用命令 |
|--------|------|----------|
| perf-stat | 全局统计事件 | `perf stat -e <event> <command>` 或 `perf kvm stat record -p <pid> -- sleep 10` |
| perf-top | 实时热点函数 | `perf top [-e <event>] [-p <pid>] [-g]` |
| perf-record | 记录采样数据 | `perf record -C 64-67 -g -- sleep 10` 或 `perf record -e cpu-clock -g -p <pid>` |
| perf-report | 分析record数据 | `perf report [--no-ch]` |
| perf-sched | 调度事件追踪 | `perf sched record -g -p <pid> sleep 10` |
| perf-kmem | slab内存分析 | `perf kmem --alloc --caller record sleep 1` |

### perf-stat 关键指标解读

| 指标 | 含义 | 性能方向 |
|------|------|----------|
| task-clock | 占用的任务时钟周期 | 值高→CPU计算而非IO |
| context-switches | 上下文切换次数 | 频繁切换需避免 |
| cpu-migrations | CPU迁移次数 | 跨核迁移影响缓存 |
| page-faults | 页错误次数 | 内存访问异常 |

### perf-top 交叉分析技巧

如果某函数在 `perf top -e instructions` 排名靠后，但在 `perf top -e cache-misses` 和 `perf top -e cycles` 排名靠前 → 该函数存在大量cache-miss → 优化内存访问策略减少cache-miss。


## 延伸阅读

实操指南：[[skills/linux-kernel-tracing]]

综合分析：[[synthesis/linux-dfx-tool-landscape]]

## 来源

- [[concepts/linux-tracing-frameworks]] — 追踪框架对比
- [[concepts/linux-cpu-performance-analysis]] — CPU性能分析场景
- [[entities/flamegraph-tool]] — 火焰图工具