---
title: Linux内核追踪实操手册
category: skills
tags: [linux, 内核, tracing, ftrace, kprobe, perf, 火焰图]
aliases: [内核追踪实操, ftrace实操, kprobe实操]
relationships:
  - target: "[[concepts/linux-tracing-frameworks]]"
    type: implements
  - target: "[[entities/perf-tool]]"
    type: uses
  - target: "[[entities/flamegraph-tool]]"
    type: uses
  - target: "[[skills/linux-kernel-debugging]]"
    type: extends
source_dir: DFX工具
source_files: [==设置trace点==/1 ftrace和kprobe和bpftrace.md, ==设置trace点==/2 perf工具.md, ==设置trace点==/3 火焰图.md, "==设置trace点==/trace：ftrace使用方法.md", "==设置trace点==/trace：kprobe使用方式.md", "==CPU==/kprobe抓CPU单核调度轨迹.md", "==CPU==/火焰图抓取CPU占用情况.md"]
summary: 内核追踪四类场景实操手册：ftrace函数追踪、kprobe动态探针、perf事件采样、火焰图可视化。每种场景包含开启→采集→分析→关闭的完整流程。
provenance:
  extracted: 0.75
  inferred: 0.20
  ambiguous: 0.05
base_confidence: 0.72
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-02
---

# Linux内核追踪实操手册

内核追踪四大工具的实操步骤：ftrace → kprobe → perf → 火焰图，覆盖从逻辑流程追踪到性能热点定位的全部场景。

## 前置条件

- root 或 sudo 权限访问 `/sys/kernel/debug/tracing/`
- 理解 [[concepts/linux-tracing-frameworks]] 基础概念
- 关闭 rasdaemon：`systemctl stop rasdaemon.service`（否则报 "Device or resource busy"）

## 步骤

### 1. ftrace 函数追踪

**适用场景**：需要完整函数调用链、函数调用图

#### 开启追踪

```bash
cd /sys/kernel/debug/tracing/
echo > trace                      # 清空缓存
echo 0 > tracing_on               # 先关闭
echo function_graph > current_tracer  # 选择调用图模式
echo cma_alloc > set_graph_function   # 设置追踪函数
echo 1 > tracing_on               # 开启追踪
```

#### 查看结果

```bash
cat trace                         # 查看全局trace
cat per_cpu/cpu0/trace            # 查看指定CPU核的trace
```

#### 关闭追踪

```bash
echo 0 > tracing_on
echo > set_ftrace_filter          # 清空过滤器（重要！否则影响后续追踪）
echo nop > current_tracer         # 重置追踪器
```

#### 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| "Device or resource busy" | rasdaemon 占用 tracing | `systemctl stop rasdaemon.service` |
| 追踪数据过多 | 未设置过滤函数 | 使用 `set_ftrace_filter` 或 `set_graph_function` |

### 2. kprobe 动态探针

**适用场景**：追踪特定内核函数入口/返回、抓取调度轨迹

#### 单函数追踪

```bash
# 查看可用函数列表
cat /sys/kernel/debug/tracing/available_filter_functions

# 添加探针（p:入口探针，r:返回探针）
echo 'p:my_probe queue_work' > /sys/kernel/debug/tracing/kprobe_events
echo 1 > /sys/kernel/debug/tracing/events/kprobes/enable
echo 1 > /sys/kernel/debug/tracing/tracing_on
echo 1 > options/stacktrace       # 开启调用堆栈
```

#### 抓单核调度轨迹

```bash
echo 1 > events/sched/sched_wakeup/enable
echo 1 > events/sched/sched_switch/enable
echo 'cpu0 || cpu1 || cpu2' > events/sched/sched_wakeup/filter
echo 'cpu0 || cpu1 || cpu2' > events/sched/sched_switch/filter
echo 1 > options/stacktrace
```

#### 关闭探针

```bash
echo 0 > /sys/kernel/debug/tracing/events/kprobes/enable
echo 0 > /sys/kernel/debug/tracing/tracing_on
echo '' > /sys/kernel/debug/tracing/kprobe_events
```

#### 脚本化追踪

```bash
# 使用方法: xxx.sh <要抓的函数名>
func=$1
tracepath="/sys/kernel/debug/tracing"
echo "p:$func $func" >> kprobe_events
echo $func > set_event
echo stacktrace > trace_options
echo 1 > events/kprobes/enable
echo > trace
```

### 3. perf 事件采样

**适用场景**：性能热点定位、CPU使用率分析、调度统计

| 场景 | 命令 |
|------|------|
| CPU热点采样 | `perf record -C 64-67 -g -- sleep 10` |
| 全系统采样 | `perf record -e cpu-clock -g -p \`pidof xxx\`` |
| 调度追踪 | `perf sched record -g -p <pid> sleep 10` |
| 虚拟机事件 | `perf kvm stat record -p <pid> -- sleep 10` |
| slab内存分析 | `perf kmem --alloc --caller record sleep 1` |

分析结果：
```bash
perf report [--no-ch]             # 分析record数据
perf sched script > cpu_sched.log # 导出调度日志
perf kmem --alloc --caller stat   # 显示slab分配统计
```

### 4. 火焰图可视化

**适用场景**：直观展示CPU调用栈和热点函数

#### 标准流程

```bash
# 1. perf采集
perf record -F 99 -p <pid> -g -- sleep 60
# 2. 解析
perf script > out.perf
# 3. 折叠
/opt/FlameGraph/stackcollapse-perf.pl out.perf > out.folded
# 4. 生成SVG
/opt/FlameGraph/flamegraph.pl out.folded > cpu.svg
```

#### 指定CPU核范围

```bash
perf record -C 33-38 -g -a -- sleep 20
perf script -i perf.data > perf.unfold
./FlameGraph-master/stackcollapse-perf.pl perf.unfold > perf.folded
./FlameGraph-master/flamegraph.pl perf.folded > perf.svg
```

#### 解读要点

- **宽度大 = 执行时间长** → 性能瓶颈嫌疑
- **平顶(plateau)** = 函数占据大量CPU时间 → 重点关注
- X轴按字母排序合并，不代表时间轴

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| ftrace echo失败 | rasdaemon占用 | 关闭rasdaemon服务 |
| kprobe不支持的函数echo失败 | 该函数不可追踪 | 查看 available_filter_functions |
| blktrace Invalid argument | cpuset cgroup限制 | `echo $$ >> /sys/fs/cgroup/cpuset/cgroup.procs` |

## 进阶用法

- **ftrace + kprobe组合**：ftrace看整体调用链 → kprobe在关键函数插入探针验证参数 ^[inferred]
- **perf + 火焰图组合**：perf record 采集 → FlameGraph 可视化 → 回到 perf report 精细分析
- **时间戳对齐**：`echo "test \`date\`" > /dev/kmsg` 可将时间戳换成与 tracing 相同格式

## 来源

- [[concepts/linux-tracing-frameworks]] — 追踪框架对比
- [[entities/perf-tool]] — perf工具详细属性
- [[entities/flamegraph-tool]] — 火焰图工具详细属性