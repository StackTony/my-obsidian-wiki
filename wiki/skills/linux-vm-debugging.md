---
title: Linux虚拟机调试与监控实操手册
category: skills
tags: [linux, 虚拟化, 调试, kvmtop, 虚拟机监控, NUMA]
aliases: [虚拟机调试实操, KVM调试, kvmtop实操]
relationships:
  - target: "[[concepts/linux-cpu-performance-analysis]]"
    type: implements
  - target: "[[entities/libvirt-virsh]]"
    type: uses
  - target: "[[entities/gdb-tool]]"
    type: uses
  - target: "[[skills/linux-kernel-debugging]]"
    type: extends
source_dir: DFX工具
source_files: [==CPU==/kvmtop的 EXT 各项的理解.md, ==CPU==/分析虚拟机的%ST抢占.md, ==CPU==/查看当前某些CPU上跑的哪些进程.md, ==CPU==/获取qemu所有处于D状态的vcpu和线程.md, ==中断==/中断数变化实时观测脚本.md, ==内存==/各node上进程内存（含qemu）占用情况.md, ==内存==/查看虚拟机OS预占的内存情况.md, ==gdb调试==/gdb调试qemu初始化流程.md]
summary: 虚拟化环境调试实操手册：kvmtop EXT分析、%ST抢占率监控、D状态vcpu检测、中断数实时观测、NUMA内存布局、QEMU初始化gdb调试七大场景。
provenance:
  extracted: 0.70
  inferred: 0.25
  ambiguous: 0.05
base_confidence: 0.68
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-11
---

# Linux虚拟机调试与监控实操手册

虚拟化环境特有的CPU/中断/内存/调试监控方法，与物理机场景有显著差异。

## 前置条件

- 有宿主机 root 权限
- 安装 kvmtop、[[entities/perf-tool|perf]]、[[entities/crash-tool|crash]]、gdb 工具
- 理解 [[concepts/linux-cpu-performance-analysis]] 基础概念

## 步骤

### 1. kvmtop EXT 分析（VM-Exit原因）

**查看VM-Exit原因统计**：`kvmtop -b -n 2 -z`

| EXT项高 | 排查方向 | 命令 |
|----------|----------|------|
| EXTirq | VM内中断高 | VM内 `irqtop` 或 `cat /proc/interrupts` 对比问题期和非问题期 |
| EXTwfe/wfi | 等待事件 | 检查 halt-polling 配置 |
| EXTsys64 | syscall频繁 | 检查VM内应用IO模式 |
| EXTmabt | 缺页异常 | 检查VM内内存分配模式 |

**EXTirq 高时具体分析**：
```bash
# VM内执行
irqtop                                # 或 cat /proc/interrupts
# 重点检查：IPI_RESCHEDULE(调度中断)、IPI_CALL_FUNC(函数调用中断)、virtio设备中断
```

### 2. %ST抢占率监控

**top %ST**（物理机层面）：
```bash
iostat -c                             # 输出steal指标
# 或间隔1分钟两次读取 /proc/stat 计算差值
cat /proc/stat | egrep "^cpu " | head -1
```
告警阈值：≥10% → 物理机资源竞争激烈

**kvmtop %ST**（虚拟机层面）：
- x86：`cat /var/run/sysinfo/kvmtop/kvmtop_info` → ST值 / 虚拟机CPU核数
- ARM：`sudo kvmtop -b -n 2 -z` → ST值 / 虚拟机CPU核数
告警阈值：连续3周期 ≥20% → 虚拟机CPU被抢占严重

### 3. D状态vcpu检测

```bash
ps -eL -o pid,tid,psr,state,comm,cmd | grep -E '(KVM|qemu)' | grep -v grep | grep "D "
```
D状态 = 等待IO完成 → 宿主机无法调度该虚拟CPU

### 4. 查看指定CPU核上运行的进程

```bash
ps -eL -o pid,tid,psr,pcpu,comm --sort=-pcpu | awk 'NR==1 || $3==64'
```

### 5. 中断数变化实时观测

使用 [[summaries/linux-interrupt-monitoring-script]] 中的脚本，不依赖额外模块：
- 两次采样 `/proc/interrupts`（间隔1秒）
- 计算每秒增量，超过阈值(th=1)时显示
- 排除 arch_timer 高频干扰

### 6. NUMA内存布局分析

**查看NUMA各node内存**：`numastat -m`

**查看进程内存布局**：`cat /proc/<pid>/maps` 或 `pmap <pid>`

**查看各node上进程内存（含qemu）占用**：
```bash
ps aux | grep qemu-kvm | grep -v grep | awk '{print $2}' | xargs numastat -p
```

**注意**：qemu进程自身（堆/栈/二进制）不受配置文件 strict 限制，strict 控制的是用户空间分配。

**查看大页使用**：`cat /proc/*/numa_maps | grep -i huge`

**确认内存具体使用**：`cat /proc/<pid>/numa_maps | grep -w Nxx`

### 7. GDB调试QEMU初始化流程

由于QEMU由libvirtd拉起且初始化极快：

```bash
# 1. 挂到libvirtd
gdb attach $(cat /var/run/libvirtd.pid)

# 2. 在fork前断住
(gdb) break virCommandSetPreExecHook
(gdb) cont

# 3. 外部启动虚拟机
virsh start $GUESTNAME

# 4. 设置进入QEMU子进程
(gdb) break main
(gdb) handle SIGKILL nopass noprint nostop
(gdb) handle SIGTERM nopass noprint nostop
(gdb) set follow-fork-mode child
(gdb) cont
# 进入QEMU main函数，开始调试初始化
```

### 8. 虚拟机OS预占内存查询

```bash
dmesg | grep Memory
# 输出：Memory: 3848740k/5242880k available (7792k kernel code, 1049480k absent, 344660k reserved, ...)
# 实际可用 = 物理内存 - absent - reserved
```

kdump 使用 kexec 引导捕获内核，reserved 内存属于第二内核且不释放。

## 常见问题

| 问题 | 排查路径 |
|------|----------|
| kvmtop EXTirq异常高 | VM内 irqtop → 对比 IPI/设备中断 |
| %ST告警 | iostat -c(物理机) + kvmtop(虚拟机) 双维度分析 |
| 虚拟机卡顿 | 检查D状态vcpu + %ST抢占 |
| qemu进程内存不受NUMA strict | 正常——strict只管用户空间 |
| kdump占用reserved内存 | reserved内存不可释放/交换 |

## 来源

- [[concepts/linux-cpu-performance-analysis]] — CPU性能分析方法
- [[entities/libvirt-virsh]] — virsh虚拟机管理
- [[entities/gdb-tool]] — GDB调试器