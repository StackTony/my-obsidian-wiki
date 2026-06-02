---
title: GDB常用命令速查指南
category: summaries
tags: [linux, gdb, 调试, 命令速查]
source_dir: DFX工具
source_files: [==gdb调试==/gdb常用命令.md]
summary: hellogcc/100-gdb-tips整理的GDB常用命令速查：断点管理、观察点、执行控制、内存查看、多线程/多进程调试、TUI界面、Core Dump分析等15类场景。
provenance:
  extracted: 0.95
  inferred: 0.05
  ambiguous: 0.00
base_confidence: 0.85
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-02
---

# GDB常用命令速查指南

源文档整理自 hellogcc 《100 个 GDB 调试技巧》，覆盖15类调试场景的常用命令。

## 概述

GDB命令速查指南涵盖断点/观察点/执行控制/打印/堆栈/多线程/多进程/Core Dump/汇编/信号/TUI/实用技巧/自动化等15个类别。

## 核心观点

- 条件断点 `break ... if condition` 是循环调试利器
- 观察点 `watch/rwatch/awatch` 监控变量变化，硬件观察点性能优于软件观察点
- `x/nfu addr` 内存查看语法是崩溃分析核心工具
- 多线程 `set scheduler-locking on/off` 控制线程运行，调试死锁关键
- 多进程 `set follow-fork-mode child/parent` + `set detach-on-fork off` 可同时调试父子
- TUI模式 `tui enable` 提供源码+汇编+寄存器的图形界面

## 关键细节

### 命令缩写速查表

| 完整 | 缩写 | 说明 |
|------|------|------|
| break | b | 设置断点 |
| run | r | 运行程序 |
| next | n | 单步(不进入函数) |
| step | s | 单步(进入函数) |
| continue | c | 继续 |
| print | p | 打印变量 |
| backtrace | bt | 显示堆栈 |
| info | i | 查看信息 |
| list | l | 显示源码 |

### 五个常见调试场景

1. 循环特定迭代：`break loop.c:20 if i==100`
2. 变量修改追踪：`watch global_var`
3. 多线程死锁：`thread apply all bt` + `set scheduler-locking on`
4. Core文件分析：`gdb ./program core.12345` + `bt full`
5. 调试子进程：`set follow-fork-mode child` + `start`

## 来源

- 原始文档：`DFX工具/==gdb调试==/gdb常用命令.md`
- 参考：https://github.com/hellogcc/100-gdb-tips