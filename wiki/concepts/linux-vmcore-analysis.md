---
title: Linux vmcore崩溃转储分析
category: concepts
tags: [linux, vmcore, crash, 崩溃分析, 寄存器]
aliases: [vmcore分析, crash分析, 内核崩溃, kernel crash]
relationships:
  - target: "[[entities/crash-tool]]"
    type: uses
  - target: "[[concepts/linux-process-scheduling]]"
    type: uses
  - target: "[[concepts/linux-memory-management]]"
    type: uses
source_dir: DFX工具
source_files: [==vmcore解析==/vmcore解析.md, ==vmcore解析==/寄存器和地址分布.md, ==vmcore解析==/调度sched.md, ==vmcore解析==/进程结构task_struct和mm_struct.md, ==vmcore解析==/开源crash网站.md]
summary: vmcore崩溃转储分析方法：crash工具使用、x86/ARM64寄存器解读、task_struct/mm_struct结构体分析、常见崩溃类型识别与栈回溯原理。
provenance:
  extracted: 0.60
  inferred: 0.30
  ambiguous: 0.10
base_confidence: 0.72
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-02
---

# Linux vmcore崩溃转储分析

vmcore是内核崩溃时生成的内存转储文件。通过crash工具加载vmcore和vmlinux（带符号表的内核映像），可以回溯崩溃时的完整内核状态。

## 核心观点

- crash 工具是vmcore分析的核心：`./crash vmcore vmlinux` 加载后，bt/struct/kmem/dis 等命令构成完整的分析链
- **寄存器是崩溃分析的起点**：RIP/PC 定位崩溃指令，RDI-R9/X0-X7 解析函数入参，RBP/X29(FP) 回溯调用栈
- **task_struct 和 mm_struct 是进程分析的两大核心结构体**：task_struct 包含进程身份/调度/信号等全部信息，mm_struct 描述进程的完整虚拟地址空间
- x86_64 和 ARM64 的寄存器体系差异显著：x86用栈保存返回地址，ARM64用 LR(X30) 寄存器；栈回溯方法不同
- 主调度器（主动放弃CPU）和周期性调度器（定时检测切换需求）是调度分析的两个维度

## 关键细节

### bt 命令堆栈字段解析

| 字段 | 含义 | 分析方法 |
|------|------|----------|
| PID | 进程ID | 唯一标识崩溃进程 |
| TASK | task_struct 地址 | `struct task_struct <addr>` 查看详情 |
| CPU | 崩溃时运行的CPU核 | 判断是否CPU相关问题 |
| COMMAND | 进程名称 | 定位哪个进程崩溃 |
| #N | 栈帧编号 | #0是最内层（崩溃点） |
| function+offset | 崩溃函数及偏移 | `dis -s <addr>` 查看源码 |

### x86_64 vs ARM64 寄存器对比

| 功能 | x86_64 | ARM64 | 崩溃分析用途 |
|------|--------|-------|-------------|
| 程序计数器 | RIP | PC | 定位崩溃指令地址 |
| 栈指针 | RSP | SP | 检查栈溢出/损坏 |
| 帧指针 | RBP | X29(FP) | 栈回溯基址 |
| 返回地址 | 栈上保存 | X30(LR) | 回溯调用链 |
| 第1-6参数 | RDI/RSI/RDX/RCX/R8/R9 | X0-X5 | 分析函数入参 |
| 返回值 | RAX | X0 | 检查函数返回值 |
| 状态寄存器 | RFLAGS | PSTATE | 中断/异常标志 |
| 内核态级别 | Ring 0 | EL1 | 异常级别判断 |
| Hypervisor | - | EL2 | 虚拟化层 ^[inferred] |

### ARM64 栈帧结构与回溯

```
栈帧结构:
+------------------+ ← 高地址
|  局部变量        |
+------------------+
|  保存的 FP (X29) | ← 当前 FP 指向这里
+------------------+
|  保存的 LR (X30) |
+------------------+ ← 低地址 (SP)
```

栈回溯过程：`FP → 保存的FP → 保存的LR → 上一级FP → ...`

### mm_struct → vm_area_struct → pgd 三级结构

- **mm_struct**：进程的完整虚拟地址空间描述（代码段/数据段/堆/栈/mmap区域的起止地址、页表pgd指针）
- **vm_area_struct (VMA)**：每个VMA描述一段连续的虚拟内存区域（权限标志vm_flags、关联文件vm_file）
- **pgd → pmd → pte → 物理页框**：多级页表实现虚拟地址到物理地址的映射
- **内核线程**：`mm = NULL`，通过 `active_mm` 借用其他进程的地址空间 ^[inferred]
- **多线程**：同线程组共享同一个 mm_struct（各线程栈独立但同地址空间）

### 常见崩溃类型识别

| 崩溃信息 | 类型 | 分析要点 |
|----------|------|----------|
| `NULL pointer dereference at 0x123` | 空指针解引用 | 偏移0x123处，指针本身为NULL |
| `paging request at ffffdeadbeef0000` | 非法地址（毒值） | 可能是UAF（Use After Free） |
| `stack segment: 0000 [#1] SMP` | 栈溢出 | SP指向非法地址，检查无限递归 |

### crash 常用命令速查

| 命令 | 用途 |
|------|------|
| `bt` | 查看崩溃进程堆栈 |
| `bt -slf` | 带函数偏移+源文件+详细内容的堆栈 |
| `foreach bt -c <cpu_id>` | 查看指定CPU上所有进程的记录 |
| `struct task_struct <addr>` | 查看进程结构体详情 |
| `struct mm_struct <addr>` | 查看内存描述符详情 |
| `kmem -p <addr>` | 查看内存页信息 |
| `dis -s <addr>` | 查看源码级反汇编 |
| `dis -r <addr>` | 反汇编代码流程 |
| `rd -S <addr> <len>` | 查看内存内容并尝试解析符号 |

## 未解问题

- 硬件关闭 SPCR 开关会导致无法记录硬件日志，生产环境应确保开启
- 调度sched源文件仅提到主/周期调度器的概念，缺少具体结构体字段说明
- ARM64 EL2(虚拟化)和EL3(Secure Monitor)在崩溃分析中的具体应用场景

## 来源

- [[entities/crash-tool]] — crash工具实体页
- [[summaries/linux-task-struct-mm-struct]] — task_struct/mm_struct结构体详解
- [[summaries/crash-register-address]] — 寄存器与地址分布