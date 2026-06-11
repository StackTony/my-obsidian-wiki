---
title: Cgroups v2 深度解析
category: concepts
tags: [云原生, Linux, Cgroups, 容器, 资源限制]
aliases: [Cgroups v2, Cgroup深度解析]
relationships:
  - target: "[[concepts/linux-namespace-cgroups]]"
    type: extends
  - target: "[[concepts/container-runtime-deep-dive]]"
    type: related_to
  - target: "[[concepts/linux-memory-management]]"
    type: related_to
source_dir: 容器运行时/从零造容器系列
source_files: [【从零造容器】4 Cgroups v2：让容器不能吃掉整台机器.md]
summary: Cgroups v2统一层级替代v1：cpu.max硬上限+cpu.weight相对权重+memory.low/high/max三道防线+io.max writeback-aware IO控制+PSI压力指标；K8s社区长期争论是否该设CPU limit
provenance:
  extracted: 0.82
  inferred: 0.15
  ambiguous: 0.03
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-11
---

# Cgroups v2 深度解析

Cgroups v1 的设计缺陷被其维护者 Tejun Heo 在2012年公开承认是错误——花了4年实现v2。v1 的独立层级导致进程在不同树中位置不一致、竞争条件、buffered IO完全不受控。v2 的 **unified hierarchy** 用一棵树管所有控制器，一个进程一个位置。

## 核心观点

- **v2 替代 v1 的核心理由**：统一层级消除进程位置不一致和竞争条件；writeback-aware IO控制器解决v1 buffered write不受控问题。
- **"low 保底，high 预警，max 兜底。三道防线，层层递进。"** — memory.low/high/max 构成容器内存管理三层防御体系。
- **[[concepts/linux-process-scheduling|CFS调度器]]带宽节流的尾延迟问题**：quota用完后即使CPU空闲也被throttle，P99延迟暴涨。`nr_throttled / nr_periods > 5-10%`就该放宽限制或只用weight。
- **Kubernetes 社区长期争论是否该设 CPU limit**——因为CFS throttle的P99问题。^[ambiguous] 一方认为不设limit导致邻居干扰（CPU饥饿），另一方认为设limit导致P99尾延迟暴涨。目前共识倾向：生产环境只用CPU requests（weight）不设limits（quota），除非有严格SLA要求。
- **systemd 和手动运行时可能打架**：互相覆盖 `subtree_control`。

## v1 vs v2 设计对比

| 维度 | v1 | v2 |
|------|----|----|
| **层级结构** | 每个控制器一棵树 | unified hierarchy一棵树 |
| **进程位置** | 不同树中可能不一致 | 一个进程一个位置 |
| **竞争条件** | 存在 | 无 |
| **IO控制** | blkio只对direct IO有效 | writeback-aware：page cache记住cgroup来源 |
| **subtree_control** | 无 | "no internal processes"规则 |

## CPU 控制器

### cpu.max — 硬上限

格式 `"quota period"`，[[concepts/linux-process-scheduling|CFS调度器]]带宽控制。quota=100000 period=100000 表示每100ms最多用100ms CPU（1核）。

**尾延迟问题**：quota用完后CPU空闲也throttle → P99延迟暴涨。解法：
- 只用weight不用max（不设硬上限）
- 或设宽松max（如2核quota给3核weight）

### cpu.weight — 相对权重

范围 1-10000，CPU竞争时决定分配比例。不竞争时各cgroup可用的CPU不受weight限制。

## 内存控制器 — 三道防线

| 层级 | 接口 | 行为 | 最佳实践 |
|------|------|------|----------|
| **memory.low** | 最低保障 | 内核尽量不回收 | 容器核心内存 |
| **memory.high** | 软限制 | 超过后内核积极回收+减慢分配 | 设在memory.max的85-90% |
| **memory.max** | 硬限制 | 超过触发OOM kill | 容器内存上限 |

**memory.oom.group**：OOM时杀掉整个cgroup（容器语义）。

**memory.events**：比dmesg更精确——只统计本cgroup的OOM事件。

## IO 控制器

### io.max — 按设备限制

格式 `"MAJOR:MINOR rbps wbps riops wiops"`。v2关键改进：writeback-aware IO控制器。

v1 blkio 只对 direct IO 有效的原因：buffered write 的 page cache 回写在内核线程里不属于任何cgroup。v2 让page cache记住来源cgroup，回写时按来源限速。

### io.stat — 统计

按设备分组：`8:0 rbytes=... wbytes=... rios=... wios=... dbytes=... dios=...`

## PSI (Pressure Stall Information)

`/proc/pressure/{cpu,memory,io}`：衡量资源压力的标准化指标。some/full 百分比表示有多少时间因资源不足被 stall。

- **PSI 补充 usage 统计**：usage告诉你用了多少，PSI告诉你压力多大——尾延迟检测的关键指标。 ^[inferred]

## 关键细节

### "no internal processes" 规则

启用 `subtree_control` 的cgroup不能有进程——进程只能在叶子cgroup中。这是v2设计的关键约束，确保层级一致性。

### systemd vs 手动运行时

systemd自动管理cgroup树（设置subtree_control）；容器运行时也设置subtree_control。两者可能冲突覆盖。解法：`Delegate=yes` 让systemd把子树交给运行时管理。

### Kubernetes QoS 对应

| QoS类 | 内存配置 | CPU配置 |
|--------|----------|---------|
| **Guaranteed** | memory.max=limit | cpu.max=limit |
| **Burstable** | memory.low<limit<memory.max | cpu.weight |
| **BestEffort** | 不设限制 | 不设限制 |

## 未解问题

- [[concepts/linux-process-scheduling|CFS调度器]] throttle尾延迟的精确量化模型？
- writeback-aware IO控制器在不同文件系统(ext4/btrfs/XFS)上的行为差异？
- PSI与HPA/VPA自动伸缩的集成最佳实践？

## 来源

- 从零造容器系列 #04 — Cgroups v2完整接口解析+v1设计缺陷对比