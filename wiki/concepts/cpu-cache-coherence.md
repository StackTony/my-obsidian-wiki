---
title: CPU Cache与缓存一致性
category: concepts
tags: [linux, 硬件, 缓存, cpu, 内存管理]
aliases: [CPU缓存一致性, MESI协议, Cache Coherence]
source_dir: "Linux 操作系统/Linux 内存管理"
source_files: [Linux CPU Cache缓存一致性：从理论到实战.md, Linux CPU是如何读写内存的？.md]
summary: "CPU读写内存完整路径(寄存器→L1/L2/L3→内存→磁盘)、cache line结构与局部性原理、MESI缓存一致性协议、伪共享与缓存友好编程实践。"
provenance:
  extracted: 0.72
  inferred: 0.23
  ambiguous: 0.05
base_confidence: 0.61
lifecycle: draft
lifecycle_changed: 2026-11-10
tier: supporting
created: 2026-11-10
updated: 2026-11-10
relationships:
  - target: "[[concepts/memory-barriers]]"
    type: related_to
  - target: "[[concepts/virtual-memory-and-paging]]"
    type: related_to
  - target: "[[concepts/linux-memory-management]]"
    type: related_to
  - target: "[[concepts/linux-lock-mechanisms]]"
    type: uses
---

# CPU Cache与缓存一致性

CPU与内存之间存在巨大速度差异（约100倍），缓存（Cache）用SRAM充当中间层，凭程序局部性原理以小容量获得70-90%命中率，是存储体系结构的灵魂。多核时代同一数据在多个核心cache中各有副本，引入缓存一致性问题，需MESI等协议维护，程序员也需写出缓存友好的代码。

## 核心观点

- **存储层次结构**：寄存器 → L1 → L2 → L3 cache → 主存(DRAM) → 磁盘。越往上越快、越小、越贵。缓存让整体性能接近寄存器，每字节成本接近内存。
- **CPU读写内存完整路径**：CPU发出虚拟地址 → [[concepts/virtual-memory-and-paging|MMU转为物理地址]] → 查L1 → L2 → L3 cache → 查主存（主存也是磁盘的cache，可能未命中需查磁盘）。这一看似简单的操作涉及cache、MMU、内存、磁盘和操作系统的密切配合。 ^[inferred]
- **cache line是缓存最小管理单元**：通常64字节，含Flag、Tag、Data三部分。从内存加载数据按整个缓存行加载。缓存按组(Set)×路(Way)矩阵排列，定位地址时先算组号 `Set Index = (addr >> 6) % M`，再遍历路匹配Tag。
- **局部性原理是缓存有效的根基**：时间局部性（访问过的数据很可能再次访问）和空间局部性（访问某数据后很可能访问相邻数据）。程序局部性使很小的cache能获得高命中率，"四两拨千斤"。
- **多核引入缓存一致性问题**：同一变量X在C1和C2的cache中各有副本，C1修改后若不同步C2，C2读到的仍是旧值。经典反例：X初值2，C1执行+2、C2执行+4，正确结果应为8，但若无一致性协议内存中只得6。
- **伪共享(False Sharing)**是缓存一致性的典型性能陷阱：两线程各自修改同一缓存行中的相邻变量，互相使对方缓存行失效，迫使从内存重新加载。用padding将变量分到不同缓存行可解决。

## 关键细节

### 缓存写策略

| 维度 | 策略 | 说明 |
|------|------|------|
| 缓存↔内存 | 写回(write-back) | 修改不立即传播到内存，缓存行被替换时才回写；性能好但复杂 |
| 缓存↔内存 | 写直达(write-through) | 任何修改立即穿透到内存；简单但耗时 |
| 核间 | 写更新(Write Update) | 写时通知其他核心更新值；其他核心立即获得最新值但总线带宽消耗大 |
| 核间 | 写无效(Write Invalidate) | 写时将其他核心缓存行置为无效；多次写只需一次总线事件，节省带宽 |
| 加载 | 写分配(Write Allocate) | 写前先将数据块读入缓存；局部性好时高效 |
| 加载 | 写不分配(Not Write Allocate) | 直接写内存不读入缓存；数据少用时高效 |

### MESI协议四状态

- **M(Modified)**：缓存行脏（与主存不同），当前缓存拥有系统中唯一有效数据
- **E(Exclusive)**：缓存行干净，只在当前缓存中，等于主存数据
- **S(Shared)**：缓存行存在于多个缓存中且干净，可随时抛弃
- **I(Invalid)**：缓存行无效

MESI基于**总线嗅探(Bus Snooping)**：所有读写请求通过总线广播，各核心嗅探后根据本地状态响应。处理器请求(PrRd/PrWr)和总线请求(BusRd/BusRdX/BusUpgr/Flush/FlushOpt)驱动四状态机转换。

各厂商有变种：**Intel MESIF**（增加F转发状态，多个S中选一个转为F负责应答，解决NUMA系统缓存一致性）；**AMD MOESI**（增加O拥有状态，脏数据可直接在缓存间传输无需先回写主存）。

### 缓存缺失与局部性的性能量化

来源1的基准测试（-O0无编译器优化）：

- 步长4096遍历32KB数组（L1d命中）vs 64KB（全部未命中）：301ms vs 959ms，3倍差距
- 行优先遍历（利用空间局部性）vs 列优先：314ms vs 1187ms，近4倍差距
- 伪共享场景：相邻long long不加padding 512ms，加`noop[8]`后181ms，2.8倍提升

### CPU访存的双重驱动

CPU访问内存有两个来源：程序数据读写和指令读取（[[summaries/linux-memory-cpu-relationship|冯诺依曼架构]]下程序与数据一视同仁）。RISC用Load/Store指令显式访存，x86(CISC)指令可直接操作内存数据。 ^[inferred]

## 未解问题

- 各MESI变种（MESIF/MOESI）的具体性能差异缺乏来源间量化对比数据。 ^[ambiguous]
- 缓存替换策略除LRU外现代CPU实际采用的变种，来源仅提及LRU及位矩阵实现，未详述其他策略。
- [[concepts/linux-io-stack|IO栈]]中DMA操作与CPU缓存一致性的交互（DMA绕过cache直接访问内存时的coherency问题）需要更多来源补充。 ^[inferred]

## 来源

- `raw/sources/Linux 操作系统/Linux 内存管理/Linux CPU Cache缓存一致性：从理论到实战.md` — 缓存原理、MESI/MOESI/MESIF协议详解、伪共享、内存屏障与x86-TSO、基准测试、CAS与无锁队列实战
- `raw/sources/Linux 操作系统/Linux 内存管理/Linux CPU是如何读写内存的？.md` — CPU读写内存完整路径、局部性原理、多核缓存一致性问题的直观推导
