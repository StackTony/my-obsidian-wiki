---
title: Linux 内存管理 TLB
category: summaries
tags: [linux, 内核, TLB, 分页, PCID]
aliases: [TLB原理, 转换检测缓冲区, TLB shootdown, PCID, ASID]
source_dir: Linux 操作系统/Linux 内存管理
source_files: [Linux 内存管理 TLB.md]
summary: TLB作为MMU内的页表缓存：表项结构、ARM Cortex-A72两级TLB、进程切换刷新的global/local权衡、多核TLB shootdown与PCID(CR4.PCID/4.15全面启用)、ARM的ASID对应机制。
provenance:
  extracted: 0.88
  inferred: 0.10
  ambiguous: 0.02
base_confidence: 0.442
lifecycle: draft
lifecycle_changed: 2026-10-21
tier: supporting
created: 2026-10-21
updated: 2026-10-21
---

# Linux 内存管理 TLB

TLB（Translation Lookaside Buffer，转换检测缓冲区）是 MMU 内部用于缓存页表项的硬件，直接决定虚拟地址到物理地址转换的命中率与进程切换的开销。本页是 [[concepts/virtual-memory-and-paging]] 中 TLB 一节的硬件/内核实现补充。

## 核心观点

- **TLB 本质是页表的缓存**："TLB 命中率"与"缓存命中率"是同一类问题——目的是避免每次访存都去读内存中的页表。
- **TLB 表项 = 标识区 + 数据区**：标识区存放虚拟地址中用于比对的位，数据区存放物理页号与状态位（有效位、引用位、脏位），与页表项字段一一对应。
- **TLB 是每个 CPU 核私有的**，因此"进程切换"和"多核一致性"各自都需要额外的刷新机制——这是 TLB 管理的两大成本来源。
- 内核地址映射被所有进程共享，因此硬件允许把页表描述符标记为 **global/local**：global 表项在进程切换时**不必**失效，只刷新进程私有的 local 表项即可。 ^[inferred]
- **PCID（Process-Context ID）**是消除进程切换 TLB 刷新的关键机制：虚拟地址与进程上下文 ID 组合后再查 TLB，从而在加载 CR3 时无需 flush；但它把成本转移成了**跨核 TLB shootdown**。

## 关键细节

### 硬件形态（以 ARM Cortex-A72 为例）

| 层级 | 容量 | 结构 |
|------|------|------|
| L1 iTLB（指令） | 48 项 | 全相联 |
| L1 dTLB（数据） | 32 项 | 全相联 |
| L2 统一 TLB | 1024 项 | 4 路组相联 |

- **每个 CPU 核有独立 TLB**，缺失时按 L1 → L2 → 页表遍历（page table walk）的层级查找。
- TLB 容量很小，因此进程刚被调度上来时 TLB 为空，会出现一段 **cold TLB** 性能下降期；工作集超过 TLB 容量则出现 **TLB 颠簸（thrashing）**。

### 进程切换时的 TLB 处理

进程切换后，旧进程的地址映射对新进程无效，必须处理：

| 策略 | 代价 | 适用 |
|------|------|------|
| 刷新整个 TLB（内核空间 + 用户空间） | 高：内核映射也被清掉，切换后立刻 cold TLB | 早期简单实现 |
| 只刷新用户空间 local 表项，保留 global（内核）表项 | 低：内核映射继续可用 | 现代硬件+内核的常规做法 |

### 多核场景与 TLB shootdown

- 一个 task 被调度到不同 CPU 执行后，会在**多个 CPU 上留下该进程的残余 TLB 表项**——即使进程已不在那个核上运行，映射仍然存在。
- 因此刷新粒度有两层选择：**flush all cores（广播给所有核）** vs **flush local core（只刷当前核）**，后者更省但需保证其他核不再持有该映射。
- 由于 TLB 由各核私有，一次需要全局生效的映射变更必须通过 **IPI 通知其他核执行 TLB shootdown**。

### PCID：让进程切换不再刷 TLB

- **Westmere 引入 PCID**（Process-Context ID）：TLB 表项从 (虚拟地址 → 物理地址) 扩展为 (虚拟地址 + 进程上下文 ID → 物理地址)。
- 内核设置 `CR4.PCID = 1` 后，**加载 CR3（切换页表）不再触发 TLB 刷新**，进程切换的 TLB 成本大幅下降。
- 代价：PCID 长度有限，**最多同时区分 4096 个进程 ID**，超出后仍需回收；同时全局生效的映射变更要依赖 IPI 做 TLB shootdown。
- ARM 架构上与之对应的机制是 **ASID（Address Space ID）**。

### Linux 的采纳时间线

| 时间点 | 事件 |
|--------|------|
| 4.14 | PCID 部分支持 |
| 4.15 | **全面启用 PCID**，进程切换默认不再刷新 TLB |

## 未解问题

- TLB shootdown 在高核数服务器上的开销如何量化？原文只说明了机制，未给出 IPI 风暴的实测数据。 ^[ambiguous]
- PCID 只有 4096 个可用 ID，进程数远超该值时内核如何做 PCID 回收（striping 策略）——原文未展开。 ^[inferred]
- ARM ASID 与 x86 PCID 在位数、回收策略、与虚拟化（嵌套页表/EL2）的交互差异，需要额外来源补充。 ^[ambiguous]

## 来源

- [[concepts/virtual-memory-and-paging]] — 虚拟内存与分页的原理基础
- [[concepts/linux-memory-management]] — Linux 内存管理总览
- [[summaries/linux-memory-cpu-relationship]] — 教材视角的分页与 TLB
- `raw/sources/Linux 操作系统/Linux 内存管理/Linux 内存管理 TLB.md`（原文：developer.aliyun.com/article/1479067）
