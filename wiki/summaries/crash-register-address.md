---
title: 崩溃寄存器与地址分布解读
category: summaries
tags: [linux, 寄存器, x86, ARM64, 崩溃分析, 调用约定]
source_dir: DFX工具
source_files: [==vmcore解析==/寄存器和地址分布.md]
summary: x86_64和ARM64两大架构的寄存器体系、函数调用约定、常见崩溃场景寄存器分析方法，以及栈回溯原理对比。
provenance:
  extracted: 0.90
  inferred: 0.05
  ambiguous: 0.05
base_confidence: 0.78
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-02
---

# 崩溃寄存器与地址分布解读

源文档详细对比了 x86_64 和 ARM64 两大架构的寄存器体系、函数调用约定、栈回溯机制和常见崩溃场景分析。

## 概述

寄存器是vmcore崩溃分析的起点——通过崩溃时保存的寄存器值可以定位崩溃指令、分析函数入参、回溯调用链。

## 核心观点

- **崩溃分析三大关键寄存器**：程序计数器(定位崩溃指令)、栈指针(检查栈溢出)、帧指针(回溯调用栈)
- x86_64 用栈保存返回地址（调用时压栈），ARM64 用 LR(X30) 寄存器保存——栈回溯方式不同
- **System V AMD64 ABI** vs **AAPCS64**：参数传递寄存器完全不同（x86: RDI/RSI/RDX/RCX/R8/R9；ARM64: X0-X5）
- ARM64 有 EL0-EL3 四级异常级别，EL2=Hypervisor、EL3=Secure Monitor，这是虚拟化崩溃分析的关键维度

## 关键细节

### 架构对比速查表

| 功能 | x86_64 | ARM64 |
|------|--------|-------|
| 程序计数器 | RIP | PC |
| 栈指针 | RSP | SP |
| 帧指针 | RBP | X29(FP) |
| 返回地址 | 栈上保存 | X30(LR) |
| 第1-6参数 | RDI,RSI,RDX,RCX,R8,R9 | X0-X5 |
| 返回值 | RAX | X0 |
| 状态寄存器 | RFLAGS | PSTATE |
| 内核态 | Ring 0 | EL1 |

### 常见崩溃信息解读

| 崩溃信息 | 类型 | 分析要点 |
|----------|------|----------|
| `NULL pointer dereference at 0x123` | 空指针解引用 | 偏移0x123处，指针本身为NULL |
| `paging request at ffffdeadbeef0000` | 毒值地址 | 可能UAF(Use After Free) |
| `stack segment: 0000 [#1] SMP` | 栈溢出 | SP非法地址 |

### ARM64 栈回溯

ARM64栈帧结构：FP指向保存的上一级FP和LR位置。回溯链：`FP → 保存的FP → 保存的LR → 上一级FP → ...`

## 来源

- 原始文档：`DFX工具/==vmcore解析==/寄存器和地址分布.md`