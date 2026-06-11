---
title: Linux CPU性能分析方法
category: concepts
tags: [linux, cpu, 性能分析, 虚拟化, perf]
aliases: [CPU性能分析, perf CPU分析, kvmtop, steal time]
relationships:
  - target: "[[concepts/linux-process-scheduling]]"
    type: uses
  - target: "[[entities/perf-tool]]"
    type: uses
  - target: "[[concepts/linux-interrupt-system]]"
    type: related_to
source_dir: DFX工具
source_files: [==CPU==/perf工具抓取CPU使用率情况.md, ==CPU==/perf工具分析虚拟机的性能事件.md, ==CPU==/perf工具抓取单核CPU的进程调度轨迹.md, ==CPU==/kvmtop的 EXT 各项的理解.md, ==CPU==/分析虚拟机的%ST抢占.md, ==CPU==/查看当前某些CPU上跑的哪些进程.md, ==CPU==/获取qemu所有处于D状态的vcpu和线程.md]
summary: Linux CPU性能分析三大场景：perf采样分析、kvmtop虚拟机VM-Exit统计、%ST抢占率分析，覆盖物理机和虚拟化环境的CPU瓶颈定位方法。
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

# Linux CPU性能分析方法

CPU性能分析分为物理机场景和虚拟化场景两大类。物理机侧重调度和采样，虚拟化还需分析 VM-Exit 和 Steal Time。

## 核心观点

- **perf** 是CPU性能分析的基石：`perf record` 记录热点、`perf sched` 追踪[[concepts/linux-process-scheduling|CFS调度器]]调度、`perf kvm stat` 分析虚拟机性能事件
- **kvmtop** 专用于虚拟化CPU分析，EXT各项代表 KVM VM-Exit 原因分类，是虚拟化性能问题的核心诊断入口
- **%ST（Steal Time）** 是虚拟化环境特有的指标：top 的 `%ST` 反映物理机整体抢占，kvmtop 的 `%ST` 反映单个虚拟机的CPU被抢占比例
- **D状态vcpu** 检测可快速定位虚拟机是否因宿主机资源竞争而阻塞
- perf 的采样原理是定期中断采样，运行时间越长的函数被击中概率越大 ^[inferred]

## 关键细节

### perf CPU分析三板斧

| 场景 | 命令 | 说明 |
|------|------|------|
| CPU使用率热点 | `perf record -C 64-67 -g -- sleep 10` | 指定CPU核范围采集调用栈 |
| 虚拟机性能事件 | `perf kvm stat record -p <pid> -- sleep 10` | 采集VM-Exit原因统计 |
| 进程调度追踪 | `perf sched record -g -p <pid> sleep 10` | 追踪[[concepts/linux-process-scheduling|CFS调度器]]切换事件 |

### kvmtop EXT各项（VM-Exit原因）

| EXT项 | 含义 | 分析方向 |
|-------|------|----------|
| EXThvc | 虚拟机主动HVC指令调用Hypervisor | 虚拟机主动退出，一般正常 |
| EXTwfe/EXTwfi | WFE/WFI等待事件/中断 | halt-polling相关，关注是否过度等待 |
| EXTmmioU/EXTmmioK | MMIO访问退出 | IOMMU相关操作 |
| EXTfp | 浮点/向量指令退出 | 浮点计算频繁导致退出 |
| **EXTirq** | **核间中断(IPI)退出** | **最常见性能问题** — 检查VM内 `/proc/interrupts` 的 IPI_RESCHEDULE/IPI_CALL_FUNC |
| EXTsys64 | 64位系统调用(SVC指令) | 应用频繁syscall |
| EXTmabt | 内存访问异常(缺页) | 缺页中断导致退出 |

### %ST抢占率分析

**top %ST vs kvmtop %ST**：

| 指标 | 数据源 | 关注范围 | 采集原理 |
|------|--------|----------|----------|
| top %ST | `/proc/stat` | 物理机整体Steal | `steal差值/总CPU差值×100%`，1分钟周期 |
| kvmtop %ST | `dfx_debugfs_entries` 或 `/sys/kernel/debug/kvm/vcpu_stat` | 单虚拟机CPU抢占 | x86读 `/var/run/sysinfo/kvmtop/kvmtop_info`；ARM用 `kvmtop -b -n 2 -z` |

**告警阈值**：
- top %ST ≥10% → 物理机资源竞争激烈
- kvmtop %ST 连续3周期 ≥20% → 虚拟机CPU被抢占严重

**超分场景**：即使1:3超分且一个VM满载D状态，配置了 `shares` 字段的其他VM仍能获得最小保障CPU时间片，但性能显著下降。

### D状态vcpu检测

```bash
ps -eL -o pid,tid,psr,state,comm,cmd | grep -E '(KVM|qemu)' | grep -v grep | grep "D "
```

D状态表示进程在等待IO完成，vcpu处于D状态意味着宿主机无法调度该虚拟CPU。

### 查看指定CPU核上的进程

```bash
ps -eL -o pid,tid,psr,pcpu,comm --sort=-pcpu | awk 'NR==1 || $3==64'
```

## 未解问题

- EXTirq 高时如何精确区分 IPI_RESCHEDULE vs IPI_CALL_FUNC vs 设备中断
- kvmtop %ST 在ARM和x86的采集路径差异是否影响阈值判断
- halt-polling 特性对 EXTwfe/EXTwfi 的影响机制


## 延伸阅读

实操指南：[[skills/linux-vm-debugging]]

综合分析：[[synthesis/linux-dfx-tool-landscape]]

## 来源

- [[entities/perf-tool]] — perf性能分析工具
- [[entities/libvirt-virsh]] — virsh虚拟机管理