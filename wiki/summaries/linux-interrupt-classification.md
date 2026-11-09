---
title: Linux中断分类总览
category: summaries
tags: [linux, 中断, irq, 架构]
relationships:
  - target: "[[concepts/linux-interrupt-system]]"
    type: related_to
source_dir: Linux 操作系统/Linux 中断系统
source_files: [Linux 中断分类表.md]
summary: 中断分类四维度框架：同步/异步是主轴，"软/硬"是通俗叫法，上/下半部是处理阶段，功能视角与机制正交。含SPI/PPI/LPI/MSI-X/IPI/NMI/LVT与Fault/Trap/Abort术语速查表。
provenance:
  extracted: 0.85
  inferred: 0.10
  ambiguous: 0.05
base_confidence: 0.6
lifecycle: draft
lifecycle_changed: 2026-11-09
tier: supporting
created: 2026-11-09
updated: 2026-11-09
---

# Linux中断分类总览

中断分类混淆的根源是存在多个不同视角的维度。本文按四个维度厘清：维度一、二是**机制维度**（相互正交、最核心），维度三是 Linux 内核特有的**处理阶段划分**，维度四是**功能/用途视角**。正文按最本质的同步/异步主轴组织。

## 核心观点

### 分类维度总览

- **维度一：按触发时机（CPU 架构视角，最本质）**——同步中断（异常 Exception）由指令执行引发，向量号由 CPU 架构预定义；异步中断（硬件 Interrupt）由外部硬件随机触发，经中断控制器（APIC/GIC）路由，向量号由操作系统动态分配。
- **维度二：按触发来源（"硬/软"通俗叫法）**——硬中断=异步中断；"软中断"是歧义词（三重含义见下）。
- **维度三：按处理时机（Linux 特有）**——上半部/下半部是**处理阶段**的划分，不是中断类型的划分。
- **维度四：按功能/用途**——"I/O 中断""定时器中断""网卡 IRQ"属于此维度，与机制类别**正交但不能平行混用**："网卡中断"（功能标签）与"MSI-X"（机制实现）不在同一层级。

功能叫法与机制类别的映射：

| 功能类型 | 典型例子 | 机制归属 |
|---|---|---|
| I/O（外设）中断 | 网卡收发包、NVMe I/O 完成、键鼠输入 | 老式设备走引脚中断（SPI/IOAPIC IRQ）；现代高速设备标配 MSI/MSI-X/LPI |
| 定时器中断 | 系统 tick、高精度定时器、调度抢占 | ARM 走 PPI；x86 走 LAPIC LVT 本地定时器或 HPET（MSI/引脚）、老式系统走 PIT（IRQ0）；跨核 tick 广播走 IPI |
| 处理器间中断（IPI） | 调度负载均衡、TLB Shootdown、多核停机 | IPI（x86 LAPIC）/ SGI（ARM GIC） |
| 本地/错误监控中断 | APIC 错误、温度传感器、PMU 采样溢出 | x86 LAPIC LVT 本地中断；ARM 的 PMU/温控多为 PPI |

（NMI 不列入此表：按可屏蔽性单独归类，功能上横跨硬件故障上报与调试监控。）

### 中断术语速查表

| 中断术语 | 英文全称 | 所属大类 | 触发驱动来源 | 管理/规范体系 | 可屏蔽 |
| --- | --- | --- | --- | --- | --- |
| **SPI** | Shared Peripheral Interrupt | 异步硬中断 | 外部物理硬件外设（串口、老网卡） | ARM GIC 体系 | 是 |
| **PPI** | Private Peripheral Interrupt | 异步硬中断 | CPU 核心私有硬件（Local Timer） | ARM GIC 体系 | 是 |
| **LPI** | Locality-specific Peripheral Interrupt | 异步硬中断 | PCIe 等设备基于内存写入的硬件消息 | ARM GICv3/v4（ITS） | 是 |
| **MSI / MSI-X** | Message Signaled Interrupt / eXtended | 异步硬中断 | PCIe 总线报文消息（网卡、NVMe） | PCI/PCIe 局部总线标准 | 是 |
| **IPI（x86）/ SGI（ARM）** | Inter-Processor Interrupt / Software Generated Interrupt | 异步硬中断 | 另一个 CPU 核心发出 | x86 APIC / ARM GIC | 是 |
| **本地中断（x86 LVT）** | Local Interrupt（Local Vector Table） | 异步硬中断 | CPU 核内本地资源（定时器、性能计数器、温控、APIC 错误） | x86 Local APIC（LVT） | 是 |
| **NMI** | Non-Maskable Interrupt | 异步硬中断 | 硬件灾难性故障/高级硬件采样 | x86 / 各架构 | **否** |
| **INT n / SVC** | Interrupt Instruction / Supervisor Call | 同步中断（陷阱） | 软件明确编写的系统调用指令 | CPU 指令集架构 | 否（直接陷入） |
| **Fault / Trap / Abort** | ——（本身即英文全称） | 同步中断（异常） | 指令执行错误或主动调试/检测点 | CPU 指令集架构 | 否（同步，不可屏蔽） |
| **Softirq** | Software Interrupt | 内核机制（非硬件中断） | Linux 内核缓解硬中断压力的软件延时机制 | Linux 操作系统 | —— |

### 同步异常 vs 异步中断

| 对比维度 | 同步异常（Exception） | 异步硬件中断（Interrupt） |
| --- | --- | --- |
| 触发时机 | 与指令执行严格同步 | 与当前指令无关，随机异步触发 |
| 触发源 | CPU 内部：指令异常或主动触发 | 外部硬件、其他 CPU 核心 |
| PC 指向 | 故障指向当前指令；陷阱指向下一条 | 指向被打断处的下一条指令 |
| 可预期性 | 大部分可预期（系统调用、缺页） | 完全随机不可预期 |
| 中断向量 | CPU 架构预定义，固定编号 | 中断控制器/操作系统动态分配 |
| 典型代表 | 缺页、系统调用、断点 | 网卡中断、定时器中断、IPI |

### 分类树

```
中断与异常
├── 同步中断（异常 Exception）—— 由指令执行引发，向量号由 CPU 架构预定义
│   ├── 故障 Fault（缺页、#GP、#DE、#UD）→ 处理后重新执行当前指令
│   ├── 陷阱 Trap（软中断指令 INT n/SVC、INT3 断点、单步调试、INTO）→ 继续执行下一条指令
│   │    └── 软中断指令（INT n / SVC / SWI）＝ 狭义"软中断"，是 Trap 的子类
│   └── 终止 Abort（#DF 双重故障、#MC 机器检查）→ 不可恢复，终止进程/内核崩溃
└── 异步中断（硬件 Interrupt，俗称"硬中断"）—— 随机到达，经中断控制器路由
    ├── 外部外设中断（物理引脚）：ARM GIC 的 PPI / SPI；电平/边沿触发
    ├── 消息信令中断（内存写报文）：MSI / MSI-X（PCIe）、LPI（GICv3 + ITS）
    ├── 处理器间中断 IPI：x86 LAPIC IPI / ARM SGI
    ├── 本地中断（每核私有、核内资源）：x86 LAPIC LVT；ARM 的 PPI 与之概念对应
    └── 不可屏蔽中断 NMI：无法通过 cli 等指令关闭
```

### 异步硬中断五类（要点）

1. **外部外设中断（PPI/SPI）**：物理引脚触发。PPI 每核专属（本地定时器、PMU），不可路由到其他核；SPI 全系统共享（网卡、硬盘、USB），可路由到单核或多核，是 SMP 中断亲和性的硬件基础。触发方式分电平/边沿。
2. **消息信令中断（MSI/MSI-X/LPI）**：向指定内存地址写报文触发，无需引脚。MSI 最多 32 个**连续**向量；MSI-X 最多 2048 个**独立**向量、可各自配置目标 CPU，是多队列网卡/NVMe 标配；LPI 是 GICv3+ 配合 ITS 的接收类型（详见"易混淆"第 5 条）。
3. **处理器间中断（IPI/SGI）**：CPU 核之间主动发送，用于 TLB 刷新、调度抢占、多核停机、时钟广播。SGI 虽由软件写寄存器**发起**，但经 GIC 以硬件中断形式**异步投递**，归类属于异步硬件中断，不属于指令级"软中断"。
4. **不可屏蔽中断（NMI）**：最高优先级的硬件中断，`cli` 关不掉。硬件故障类（看门狗超时、不可纠正 ECC）通常直接崩溃；调试监控类（NMI Watchdog 死锁检测、perf 硬件采样）利用不可屏蔽性在关中断场景采集 CPU 状态。
5. **本地中断（x86 LVT）**：CPU 核内本地资源产生、每核私有，经本地 APIC 的 LVT 直接投递本核、不经 IOAPIC。来源含本地定时器（tick/高精度，支持 TSC-deadline）、性能计数器溢出（perf 采样）、温度传感器、APIC 错误/CMCI。概念上与 ARM 的 PPI 对应。

### 同步异常三类（要点）

1. **故障 Fault**（被动、可恢复）：PC 指向**当前指令**，处理后重新执行。缺页（含按需调页/COW 正常场景与 SIGSEGV 场景）、#GP、#DE、#UD。
2. **陷阱 Trap**（主动）：PC 指向**下一条指令**，处理完继续执行。软中断指令 `INT n`（如 `int 0x80`）、ARM `SVC/SWI` 是 Trap 子类即狭义"软中断"；`syscall` 快速调用不走中断描述符表但行为上仍是同步陷阱 ^[inferred]；断点 `int3`、单步、`into` 同属。
3. **终止 Abort**（被动、不可恢复）：PC 无意义，只能终止进程或内核崩溃。#DF（内核栈溢出典型；再触发则三重故障→CPU 硬件复位）、#MC（硬件物理故障上报；配合 ECC 部分可纠正，并非全部崩溃）。

### "软中断"三重含义与易混淆澄清

**"软中断"一词的三重含义**（语境不明时先确认说的是哪一种）：
- **指令级狭义软中断**：`INT n`、`SVC/SWI` 等 CPU 指令——同步陷阱，用于系统调用；
- **广义软件中断**：泛指 CPU 内部产生的所有同步中断（异常）；
- **Linux 内核 Softirq**：下半部延迟处理机制——不是硬件意义上的中断。

**其他易混淆点**：
1. **上半部 vs 下半部**：上半部即硬中断处理函数（快速响应、清中断标志、登记工作）；下半部（softirq/tasklet/workqueue）负责耗时处理，开中断环境执行。
2. **SGI 与 IPI**：SGI 是 ARM GIC 的中断类型，IPI 是核间中断的功能概念——ARM 平台的 IPI 通过 SGI 实现，是实现与功能的对应关系。
3. **功能叫法与机制类别不在同一层级**：现代网卡 IRQ 的机制实现是 MSI-X，ARM 定时器中断的机制实现是 PPI，x86 本地定时器的机制实现是 LAPIC LVT。跨层混比会产生"网卡中断和 MSI-X 谁包含谁"这类无意义问题。
4. **ARM 上 MSI/MSI-X 与 LPI 的关系**：GICv3+ 平台上，设备发出的 MSI/MSI-X 写请求由 GIC 的 ITS（中断翻译服务）翻译成 LPI，再经 Redistributor 投递到目标 CPU 核——**MSI/MSI-X 是设备侧的"发出形式"（PCIe 总线协议层），LPI 是 GIC 侧的"接收类型"（中断控制器层）**，不是两种并列的中断；x86 上同样的 MSI/MSI-X 写直接落入 Local APIC，没有 LPI 这个中间类型。

## 未解问题

- LPI 中断号范围（8192-MAX）的实际上限取决于 GIC 实现与 ITS 配置，不同 SoC 差异待补充。 ^[inferred]
- `syscall`/`sysenter` 快速调用与传统 `int 0x80` 在入口路径上的具体差异（MSR 寄存器 vs 中断描述符表）本文未展开。

## 来源

- `raw/sources/Linux 操作系统/Linux 中断系统/Linux 中断分类表.md` — 原始文章
- [[concepts/linux-interrupt-system]] — 中断系统整体框架（上下半部、softirq 机制）
- [[summaries/linux-softirq-detail]] — Linux 内核 Softirq 实现细节
- [[summaries/linux-interrupt-lifecycle]] — GIC 硬件到软件注册的全链路
