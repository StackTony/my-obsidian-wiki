---
title: GDB调试器
category: entities
tags: [linux, gdb, 调试, 开发工具]
aliases: [gdb, GDB调试器, GNU Debugger]
relationships:
  - target: "[[entities/crash-tool]]"
    type: related_to
  - target: "[[entities/libvirt-virsh]]"
    type: uses
source_dir: DFX工具
source_files: [==gdb调试==/gdb常用命令.md, ==gdb调试==/gdb调试qemu初始化流程.md]
summary: GNU Debugger(GDB)是Linux标准调试器，支持断点/观察点/多线程/多进程/汇编/core dump分析，可用于调试QEMU虚拟化进程初始化流程。
provenance:
  extracted: 0.80
  inferred: 0.15
  ambiguous: 0.05
base_confidence: 0.78
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: core
created: 2026-06-02
updated: 2026-06-11
---

# GDB调试器

GDB (GNU Debugger) 是 Linux 下最广泛使用的程序调试器，支持断点管理、观察点、单步执行、堆栈分析、多线程/多进程调试、汇编调试和 core dump 分析。

## 简介

GDB 提供命令行和 TUI 图形界面两种交互模式，涵盖从变量打印到汇编级调试的全部功能。

## 关键属性

| 属性 | 值 |
|------|-----|
| 来源 | GNU项目 |
| 启动方式 | `gdb program` / `gdb attach <pid>` / `gdb program core.<pid>` |
| 交互模式 | 命令行 / TUI (`tui enable`) |
| 缩写支持 | 大部分命令有缩写（b=break, r=run, n=next等） |
| 参考资源 | hellogcc/100-gdb-tips (GitHub) |

## 与其他实体的关系

- **crash** — crash 用于内核[[concepts/linux-vmcore-analysis|vmcore分析]]，GDB 用于用户态程序调试，两者功能互补但定位不同 ^[inferred]
- **libvirt/virsh** — 通过 `gdb attach libvirtd` + `set follow-fork-mode child` 可调试QEMU初始化流程
- **perf** — GDB 是交互式逐步调试，perf 是统计式采样分析 ^[inferred]

## 核心功能模块

### 1. 断点管理

- 基本断点：`break main` / `break file.c:10` / `break *0x400500`
- 条件断点：`break 10 if i==101`（循环中只关注特定迭代）
- 临时断点：`tbreak`（触发一次后自动删除）
- 观察点：`watch var`(写入时停) / `rwatch`(读取时停) / `awatch`(读写都停)

### 2. 执行控制

| 命令 | 缩写 | 说明 |
|------|------|------|
| next | n | 执行下一行，不进入函数 |
| step | s | 执行下一行，进入函数 |
| continue | c | 继续到下一个断点 |
| finish | fin | 执行到当前函数返回 |
| until | u | 执行到指定行或循环结束 |

### 3. 内存查看 (x/nfu)

- `n`：单元个数，`f`：格式(x/d/u/o/t/c/s)，`u`：大小(b/h/w/g)
- 示例：`x/16xb arr`(16字节十六进制)、`x/16xw arr`(16 word十六进制)、`x/s str`(字符串)

### 4. 多线程调试

```bash
info threads              # 列出所有线程
thread apply all bt       # 打印所有线程堆栈
set scheduler-locking on  # 只允许当前线程运行
break func thread 2       # 设置线程断点
```

### 5. 多进程调试

```bash
set follow-fork-mode child   # 跟随子进程
set follow-fork-mode parent  # 跟随父进程
set detach-on-fork off       # 同时调试父和子
info inferiors               # 查看所有进程
```

### 6. Core Dump 分析

```bash
gdb ./program core.12345    # 加载core文件
generate-core-file           # 在GDB中生成core dump
gcore <pid>                  # 对运行中进程生成core dump
```

## QEMU初始化流程调试方法

由于QEMU由libvirtd拉起且初始化极快，无法直接gdb attach：

1. `gdb attach $(cat /var/run/libvirtd.pid)` — 先挂到libvirtd
2. `break virCommandSetPreExecHook` + `cont` — 在fork前断住
3. `virsh start $GUESTNAME` — 外部启动虚拟机
4. `break main` + `handle SIGKILL/SIGTERM nopass noprint nostop` + `set follow-fork-mode child` + `cont`
5. 进入QEMU main函数，开始调试初始化流程


## 延伸阅读

实操指南：[[skills/linux-vm-debugging]]

综合分析：[[synthesis/linux-dfx-tool-landscape]]

## 来源

- [[skills/gdb-debugging-guide]] — GDB调试实操速查手册