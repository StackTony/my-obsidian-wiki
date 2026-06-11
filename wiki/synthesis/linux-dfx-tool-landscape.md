---
title: Linux DFX调试工具全景图
category: synthesis
tags: [linux, DFX, 调试, 工具全景, 性能分析]
aliases: [DFX工具全景, 调试工具地图]
relationships:
  - target: "[[concepts/linux-tracing-frameworks]]"
    type: uses
  - target: "[[concepts/linux-cpu-performance-analysis]]"
    type: uses
  - target: "[[concepts/linux-vmcore-analysis]]"
    type: uses
  - target: "[[concepts/linux-io-performance-analysis]]"
    type: uses
  - target: "[[skills/linux-kernel-debugging]]"
    type: extends
source_dir: DFX工具
source_files: [==CPU==/perf工具抓取CPU使用率情况.md, ==CPU==/perf工具分析虚拟机的性能事件.md, ==CPU==/perf工具抓取单核CPU的进程调度轨迹.md, ==CPU==/kvmtop的 EXT 各项的理解.md, ==CPU==/分析虚拟机的%ST抢占.md, ==CPU==/查看当前某些CPU上跑的哪些进程.md, ==CPU==/获取qemu所有处于D状态的vcpu和线程.md, ==CPU==/火焰图抓取CPU占用情况.md, ==CPU==/kprobe抓CPU单核调度轨迹.md, ==IO==/IO常用工具.md, ==gdb调试==/gdb常用命令.md, ==gdb调试==/gdb调试qemu初始化流程.md, ==vmcore解析==/vmcore解析.md, ==vmcore解析==/寄存器和地址分布.md, ==vmcore解析==/开源crash网站.md, ==vmcore解析==/调度sched.md, ==vmcore解析==/进程结构task_struct和mm_struct.md, ==中断==/中断数变化实时观测脚本.md, ==内存==/perf工具分析slab内存占用.md, ==内存==/各node上进程内存（含qemu）占用情况.md, ==内存==/查看虚拟机OS预占的内存情况.md, ==网络==/iperf打流.md, ==网络==/网络分析工具tcpdump.md, ==设置trace点==/1 ftrace和kprobe和bpftrace.md, ==设置trace点==/2 perf工具.md, ==设置trace点==/3 火焰图.md, "==设置trace点==/trace：ftrace使用方法.md", "==设置trace点==/trace：kprobe使用方式.md"]
summary: Linux DFX调试工具全景图：六大领域(CPU/IO/内存/网络/追踪/vmcore) × 三种模式(监控/追踪/事后分析)的工具矩阵，以及工具间的互补关系和选择决策路径。
provenance:
  extracted: 0.40
  inferred: 0.50
  ambiguous: 0.10
base_confidence: 0.68
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: core
created: 2026-06-02
updated: 2026-06-11
---

# Linux DFX调试工具全景图

DFX(Debug For X)工具覆盖六大领域、三种分析模式，形成从运行时监控到事后分析的完整调试矩阵。

## 概述

DFX工具不是孤立的——它们在分析模式、数据来源和应用场景上相互补充。理解工具间的关系比记住单个命令更重要。 ^[inferred]

## 跨领域连接

### 六大领域 × 三种模式

| 领域 | 监控模式 | 追踪模式 | 事后分析 |
|------|----------|----------|----------|
| **CPU** | top/iostat(%ST)/kvmtop(EXT)/ps | perf record/sched/kprobe(ftrace) | perf report/[[entities/flamegraph-tool|火焰图]] |
| **IO** | iostat(-dmx)/iotop | blktrace | block_dump日志 |
| **内存** | free/meminfo/numastat | perf kmem(slab) | vmcore→mm_struct |
| **网络** | /proc/interrupts(脚本) | tcpdump | Wireshark(.pcap) |
| **追踪** | - | ftrace/kprobe/bpftrace/perf | trace日志分析 |
| **崩溃** | - | - | crash(vmcore) |
| **代码调试** | - | [[entities/gdb-tool|GDB]] attach/break | [[entities/gdb-tool|GDB]](core dump) |

### 工具互补关系

**perf ↔ [[entities/flamegraph-tool|火焰图]]**：perf record 采集 → FlameGraph 脚本可视化 → 回到 perf report 精细分析。这是最典型的"采集→可视化→精细化"三步链路。 ^[inferred]

**ftrace ↔ kprobe**：ftrace 看全局调用链（function_graph）→ kprobe 在关键函数插入探针验证参数和时序。ftrace 是广角镜头，kprobe 是显微镜。 ^[inferred]

**perf ↔ crash**：perf 是运行时动态采样的"预防"，crash 是事后静态分析的"诊断"。perf 可以发现趋势（如 cache-miss 率上升），crash 可以定位崩溃瞬间状态。 ^[inferred]

**[[entities/gdb-tool|GDB]] ↔ crash**：[[entities/gdb-tool|GDB]] 用于用户态程序逐步调试（交互式），crash 用于内核 vmcore 批量分析（命令式）。调试QEMU虚拟化进程时两者可串联：[[entities/gdb-tool|GDB]]调试初始化流程 → 运行中perf监控 → 崩溃后crash分析。 ^[inferred]

**iostat ↔ blktrace**：iostat 发现"await>>svctm"（队列过长）→ blktrace 追踪IO在scheduler和硬件层的耗时分配 → 精确定位瓶颈层。 ^[inferred]

### 虚拟化特有工具链

虚拟化环境有独特的DFX维度：

- **kvmtop** → VM-Exit原因分类（EXTirq/EXTwfi等）→ 虚拟化层特有的CPU退出分析
- **%ST** → top(物理机Steal) + kvmtop(虚拟机ST) → 双维度抢占率分析
- **D状态vcpu** → ps筛选qemu D状态线程 → 快速定位宿主机资源竞争
- **[[entities/gdb-tool|GDB]]+libvirtd** → [[entities/gdb-tool|GDB]] attach libvirtd → follow-fork-mode child → 调试QEMU初始化

## 综合洞察

### 工具选择决策路径

```
问题发现 → 先用监控工具(iostat/top/kvmtop/free)量化
        → 性能问题？→ perf stat 定方向 → perf record + 火焰图 定热点
        → 流程问题？→ ftrace看调用链 → kprobe探关键函数
        → 崩溃问题？→ crash分析vmcore → struct/dis 深入
        → 网络问题？→ tcpdump抓包 → iperf测带宽
        → IO问题？  → iostat量化 → blktrace追踪路径
```

### DFX工具的设计哲学 ^[inferred]

- **分层递进**：每个领域都有监控→追踪→深入的三级工具，先量化再定性
- **接口统一**：ftrace/kprobe/perf 通过 `/sys/kernel/debug/tracing/` 共享接口
- **数据流转**：perf.data → FlameGraph → SVG；vmcore → crash → 堆栈/结构体
- **架构适配**：寄存器/调用约定在x86和ARM上完全不同，工具需适配架构差异

## 开放问题

- bpftrace 在源文件中仅简略提及，缺少实操方法——未来需补充eBPF追踪内容 ^[ambiguous]
- iotop 和 blktrace 的详细使用方法在源文件中缺失
- 调度sched源文件仅描述概念缺少结构体字段，vmcore中调度分析的实际操作需要更多资料
- 内存领域的追踪工具偏少（perf kmem仅覆盖slab），缺缺页追踪和Page Cache追踪的方法

## 来源

- [[concepts/linux-tracing-frameworks]] — 追踪框架对比
- [[concepts/linux-cpu-performance-analysis]] — CPU性能分析
- [[concepts/linux-io-performance-analysis]] — IO性能分析
- [[concepts/linux-vmcore-analysis]] — vmcore崩溃分析
- [[entities/perf-tool]] — perf工具
- [[entities/crash-tool]] — crash工具
- [[entities/gdb-tool]] — GDB调试器
- [[entities/flamegraph-tool]] — 火焰图工具