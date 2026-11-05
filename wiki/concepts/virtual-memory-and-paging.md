---
title: 虚拟内存与分页
category: concepts
tags: [linux, 内存, 虚拟内存, 分页, 页面置换]
aliases: [虚拟内存, 分页机制, 页表, TLB, 页面置换算法, 地址空间]
relationships:
  - target: "[[concepts/linux-memory-management]]"
    type: related_to
  - target: "[[concepts/linux-vmcore-analysis]]"
    type: related_to
  - target: "[[concepts/linux-process-scheduling]]"
    type: related_to
  - target: "[[concepts/linux-os-virtualization-landscape]]"
    type: related_to
source_dir: Linux 操作系统/Linux 内存管理
source_files: [Linux 内存与CPU之间的关系.md, Linux 内存管理 TLB.md]
summary: 虚拟内存的抽象与实现链：地址空间→分页与页表项→TLB(含PCID/ASID与TLB shootdown)→多级/倒排页表→九种页面置换算法(WSClock与老化最优)。
provenance:
  extracted: 0.85
  inferred: 0.12
  ambiguous: 0.03
base_confidence: 0.671
lifecycle: draft
lifecycle_changed: 2026-10-21
tier: supporting
created: 2026-10-21
updated: 2026-10-21
---

# 虚拟内存与分页

虚拟内存是操作系统给进程的最重要抽象：进程看到一段从 0 开始、连续、独占的**地址空间**，而实际物理内存的分配、共享与回收全部由内核在幕后完成。[[concepts/linux-memory-management|Linux 内存管理]]中的 meminfo、Page Cache、LRU 等都是这套抽象在上层的表现；本页则聚焦它的原理链条——**地址空间 → 分页 → 页表 → TLB → 页面置换**。

## 核心观点

- **虚拟内存的本质是"解耦"**：虚拟地址与物理地址解耦，使进程无需关心物理内存布局，也让内存超额分配（overcommit）、按需调页、共享与保护成为可能。 ^[inferred]
- **分页是这套解耦的实现机制**：固定大小的页与页框一一映射，由 MMU 用页表完成翻译。
- **每次优化都在解决上一次抽象带来的代价**：分页让访存变成两次访问 → TLB 缓存页表项；页表自身占用过大 → 多级页表 / 倒排页表；TLB 是每核私有 → 进程切换刷新与 TLB shootdown。
- **TLB 是理解"进程切换很贵"的关键**：切地址空间不只是换 CR3，还意味着大量地址翻译缓存失效——PCID/ASID 正是为消除这一成本而生。
- **页面置换算法的工程结论**：LRU 效果最好但无法低成本实现，**老化（aging）与 WSClock 是实践中最优的近似**。

## 关键细节

### 抽象的演进

| 阶段 | 机制 | 局限 |
|------|------|------|
| 无抽象 | 程序直接用物理地址 | 多程序无法共存 |
| 基址 + 界限寄存器 | 运行时相加并做越界检查 | 每次访存都有额外运算；需连续存放 |
| 基址/变址分段 | 代码段只读可共享、数据段可写，各自加基址 | 依赖编译期分段信息 |
| 虚拟内存/分页 | 页级映射 + 按需调页 | 引入页表开销与缺页开销 |

**交换（swapping）** 与 **内存紧缩（compaction）** 是虚拟内存之前的补丁：整体换出进程、靠搬移空闲块合并碎片——代价高且不适用于非连续分配。

### 空闲内存管理

- **位图**：每分配单元 1 bit；查找连续空闲块需按字扫描，慢。
- **空闲链表**：按地址排序的段链表，记录起始地址与长度。
- **适配算法**：首次适配（最快、常用）、下次适配、最佳适配（碎片多）、最差适配（大块被迅速打散）；**快速适配**为常见大小各设一条链表。

### 页表项与缺页中断

页表项通常包含：**页框号**、**在/不在位**、**保护位**、**修改位（脏位）**、**访问位（引用位）**、**禁用缓存位**。

**缺页处理流程**：MMU 发现"在/不在位"= 0 → CPU 陷入内核 → 选择牺牲页（脏页先写回）→ 调入缺失页并更新页表 → **重新执行触发缺页的那条指令**。最后一步是虚拟内存可以"透明"的原因——指令无需修改即可重试。 ^[inferred]

### TLB 与硬件细节

TLB 缓存的失败分两类：页在内存但 TLB 未命中（**软失效**）与页不在内存需读磁盘（**硬失效**），对应 minor / major page fault 的区别。

**硬件形态（ARM Cortex-A72）**：L1 iTLB 48 项全相联、L1 dTLB 32 项全相联、L2 统一 TLB 1024 项 4 路组相联。**TLB 每核私有**，工作集超出容量则出现 **cold TLB** 与 **TLB 颠簸**。

**进程切换的两难**：

| 策略 | 代价 |
|------|------|
| 刷新整个 TLB | 内核映射也被清空，切换后立即 cold TLB |
| 只刷 local 表项、保留 global（内核）表项 | 需硬件在页表描述符中支持 global/local 标记 |

**PCID / ASID**：把 TLB 表项从 (VA → PA) 扩展为 (VA + 进程上下文 ID → PA)。设置 `CR4.PCID = 1` 后**加载 CR3 不再刷新 TLB**，进程切换成本大幅下降；PCID 位数有限（最多 4096 个 ID）。ARM 对应机制为 **ASID**。代价是全局生效的映射变更必须靠 **IPI 触发 TLB shootdown**。Linux 在 **4.14 部分支持、4.15 全面启用 PCID**。

### 大地址空间：两种页表方案

| 方案 | 思路 | 代价 |
|------|------|------|
| 多级页表 | 页表本身再分页，只保留使用到的部分 | 单次访存需多次读页表（由 TLB 缓解） |
| 倒排页表 | 每物理页框一项，记录 (进程, 虚拟页号) | 开销与物理内存成正比；查找需哈希 |

### 页面置换算法对比

| 算法 | 策略 | 评价 |
|------|------|------|
| OPT | 换出未来最久不再访问的页 | 不可实现，理论基准 |
| NRU | 按 R/M 位分四类，优先 R=0,M=0 | 简单，效果一般 |
| FIFO | 先进先出 | 存在 Belady 异常 |
| 第二次机会 | FIFO + R 位检查并给一次机会 | 低成本改进 |
| 时钟 | 环形链表实现第二次机会 | 常见工程形式 |
| LRU | 换出最久未访问 | 效果好，实现代价极高 |
| NFU | 计数器累加 R 位（频次） | 不区分访问时间远近 |
| **老化 aging** | 计数器先右移再把 R 位加到最高位 | **推荐**，低成本近似 LRU |
| 工作集 | 记录最近 k 次访问时间，换出窗口外页 | 效果好，有时间戳开销 |
| **WSClock** | 工作集 + 时钟：R=0 且 age>τ 即换出 | **推荐** |

### 与 Linux 具体实现的对应

| 理论概念 | Linux 实现 |
|----------|-----------|
| 页 / 页框 | 4KB 基础页、THP 2MB 大页、hugetlb |
| 多级页表 | x86_64 四级页表（pgd→pud→pmd→pte），见 [[summaries/linux-task-struct-mm-struct]] |
| 页表项状态位 | 由 PTE 位 + 页表遍历（page table walk）维护，脏位/访问位由硬件置位 |
| 时钟/工作集置换 | 内核的 Active/Inactive 双 LRU 链表 + kswapd 回收 |
| TLB 刷新 | `flush_tlb_*` 系列 + PCID；跨核靠 IPI |
| 地址空间 | `mm_struct` + `vm_area_struct` |

## 未解问题

- 页面大小的定量权衡（内部碎片 vs 页表规模 vs 缺页次数 vs IO 效率）缺少量化结论。 ^[ambiguous]
- 原文对预调页、颠簸（thrashing）与工作集模型的定量关系讨论较浅。 ^[inferred]
- 教材视角与 Linux 实际（四级页表、folio、多级 LRU、memory cgroup 的 per-cgroup LRU）之间还有一层映射需要专门来源补齐。 ^[inferred]
- 虚拟化场景下的二级地址翻译（EPT/NPT）与 TLB 的交互未涉及。 ^[inferred]

## 来源

- [[summaries/linux-memory-cpu-relationship]] — 教材视角的虚拟内存原理
- [[summaries/linux-tlb-management]] — TLB 硬件与内核实现细节
- [[concepts/linux-memory-management]] — Linux 内存管理具体机制
- [[concepts/linux-vmcore-analysis]] — 页表结构在崩溃分析中的应用
- [[concepts/linux-process-scheduling]] — 上下文切换中的地址空间切换
