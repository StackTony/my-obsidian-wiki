---
title: Linux内核追踪框架
category: concepts
tags: [linux, 内核, tracing, ftrace, kprobe, perf]
aliases: [ftrace, kprobe, bpftrace, 内核追踪]
relationships:
  - target: "[[concepts/linux-interrupt-system]]"
    type: uses
  - target: "[[concepts/linux-process-scheduling]]"
    type: uses
  - target: "[[entities/perf-tool]]"
    type: uses
source_dir: DFX工具
source_files: [==设置trace点==/1 ftrace和kprobe和bpftrace.md, ==设置trace点==/trace：ftrace使用方法.md, ==设置trace点==/trace：kprobe使用方式.md, ==CPU==/kprobe抓CPU单核调度轨迹.md]
summary: Linux内核四大追踪框架对比：ftrace(静态函数追踪)、kprobe(动态探针)、perf(性能采样)、bpftrace(eBPF追踪)，各框架的适用场景与操作方式。
provenance:
  extracted: 0.65
  inferred: 0.30
  ambiguous: 0.05
base_confidence: 0.72
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-02
---

# Linux内核追踪框架

Linux内核提供四种追踪框架，从静态到动态、从轻量到灵活，覆盖不同深度的调试需求。

## 核心观点

- **ftrace** 是内核内置的函数追踪器，只能追踪静态已注册的内核函数，开销较大但提供完整的 `function_graph` 调用链视图
- **kprobe** 是动态探针机制，可在运行时插入追踪点到任意内核函数入口/返回点，灵活性最高但需要手动管理探针生命周期
- **perf** 基于事件采样而非逐函数追踪，按固定频率中断采样统计热点，更适合性能瓶颈定位而非逻辑流程追踪 ^[inferred]
- **bpftrace** 基于 eBPF 的现代追踪工具，可编程且安全，但需要较新的内核版本支持 ^[inferred]
- ftrace 和 kprobe 通过 `/sys/kernel/debug/tracing/` 统一接口操作，共享同一套过滤和输出机制

## 关键细节

### ftrace 使用流程

1. 清空缓存：`echo > trace`；关闭追踪：`echo 0 > tracing_on`
2. 选择追踪器：`echo function_graph > current_tracer`（调用图）或 `echo function > current_tracer`（函数名）
3. 设置过滤函数：`echo cma_alloc > set_ftrace_filter`（仅追踪指定函数）或 `echo cma_alloc > set_graph_function`（调用图模式）
4. 开启追踪：`echo 1 > tracing_on`
5. 查看结果：`cat trace` 或 `cat per_cpu/cpu0/trace`（按CPU核）
6. 关闭清理：`echo 0 > tracing_on` → `echo > set_ftrace_filter` → `echo nop > current_tracer`

**注意**：使用前需关闭 `rasdaemon.service`（`systemctl stop rasdaemon.service`），否则会报 "Device or resource busy" 错误。

### kprobe 使用流程

1. 查看可用函数：`cat /sys/kernel/debug/tracing/available_filter_functions`
2. 添加探针：`echo 'p:my_probe queue_work' > /sys/kernel/debug/tracing/kprobe_events`（`p:` 表示入口探针）
3. 开启探针：`echo 1 > /sys/kernel/debug/tracing/events/kprobes/enable`
4. 开启追踪：`echo 1 > /sys/kernel/debug/tracing/tracing_on`
5. 开启栈回溯：`echo 1 > options/stacktrace`
6. 关闭清理：`echo 0 > events/kprobes/enable` → `echo 0 > tracing_on` → `echo '' > kprobe_events`

### kprobe 抓单核调度轨迹

```
# 开启调度事件追踪
echo 1 > events/sched/sched_wakeup/enable && echo 1 > events/sched/sched_switch/enable
# 按CPU核过滤
echo 'cpu0 || cpu1 || cpu2' > events/sched/sched_wakeup/filter
echo 'cpu0 || cpu1 || cpu2' > events/sched/sched_switch/filter
# 开启调用堆栈
echo 1 > options/stacktrace
```

### ftrace/kprobe 脚本化

可通过脚本实现一键追踪指定函数：

```bash
func=$1
tracepath="/sys/kernel/debug/tracing"
# 先检查并关闭 kprobes
echo "p:$func $func" >> kprobe_events
echo $func > set_event
echo stacktrace > trace_options
echo 1 > events/kprobes/enable
echo > trace
```

### 框架对比

| 框架 | 追踪方式 | 灵活性 | 开销 | 适用场景 |
|------|----------|--------|------|----------|
| ftrace | 静态函数注册 | 低（仅已注册函数） | 高 | 完整调用链、函数调用图 |
| kprobe | 动态探针 | 高（任意内核函数） | 中 | 特定函数追踪、事件探针 |
| perf | 事件采样 | 中（PMU+tracepoint） | 低 | 性能热点定位、统计分析 |
| bpftrace | eBPF可编程 | 最高 | 极低 | 复杂条件追踪、实时统计 ^[inferred] |

## 未解问题

- bpftrace 在源文件中仅以树状结构提及，缺少详细使用方式 ^[ambiguous]
- ftrace 的 `function_graph` 模式开销较大，生产环境是否需要替代方案
- kprobe 对不支持的函数会 echo 失败，如何判断哪些函数可用

## 来源

- [[summaries/linux-ftrace-kprobe-overview]] — ftrace/kprobe/bpftrace框架概述
- [[entities/perf-tool]] — perf性能分析工具