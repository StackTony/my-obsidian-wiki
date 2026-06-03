---
title: crash vmcore分析工具
category: entities
tags: [linux, vmcore, crash, 崩溃分析, 内核调试]
aliases: [crash, crash工具, vmcore crash]
relationships:
  - target: "[[concepts/linux-vmcore-analysis]]"
    type: related_to
  - target: "[[entities/gdb-tool]]"
    type: related_to
source_dir: DFX工具
source_files: [==vmcore解析==/vmcore解析.md, ==vmcore解析==/开源crash网站.md]
summary: crash是Linux内核vmcore崩溃转储分析的核心工具，加载vmcore+vmlinux后，通过bt/struct/kmem/dis等命令回溯崩溃时的完整内核状态。
provenance:
  extracted: 0.75
  inferred: 0.20
  ambiguous: 0.05
base_confidence: 0.65
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-02
---

# crash vmcore分析工具

crash 是分析 Linux 内核 vmcore 崩溃转储的核心工具，结合 vmcore 文件和 vmlinux（带符号表的内核映像）进行事后分析。

## 简介

crash 工具需要在目标系统安装 kernel-debuginfo 包后使用。基本命令格式：`./crash vmcore vmlinux`。

**重要提醒**：硬件关闭 SPCR 开关会导致无法记录硬件日志！

## 关键属性

| 属性 | 值 |
|------|-----|
| 前置条件 | 安装 kernel-debuginfo 包 |
| 启动命令 | `./crash vmcore vmlinux` |
| 堆栈增强 | `bt -slf` 显示函数偏移+源文件+每帧详细内容 |
| 时间戳转换 | `date -d@'<timestamp>' "+%Y-%m-%d %H:%M:%S"` |

## 与其他实体的关系

- **GDB** — crash 与 GDB 功能重叠但定位不同：crash 专用于内核vmcore，GDB 更通用 ^[inferred]
- **perf** — crash 是事后静态分析，perf 是运行时动态采样，二者互补 ^[inferred]

## 常用命令速查

| 命令 | 功能 |
|------|------|
| `bt` | 查看崩溃进程堆栈 |
| `bt -slf` | 增强版堆栈（函数偏移+源码+详细内容） |
| `foreach bt -c <cpu_id>` | 查看指定CPU上所有进程 |
| `bt -a | grep -i COMMAND | grep -v "PID: 0"` | 筛选问题堆栈 |
| `struct <结构体> <addr>` | 查看结构体内容 |
| `dis -s <addr>` | 源码级反汇编 |
| `dis -r <addr>` | 反汇编代码流程 |
| `rd -S <addr> <len>` | 查看内存并尝试解析符号 |
| `kmem -p <addr>` | 查看内存页信息 |
| `ps / files / mount / net` | 列出进程/文件/挂载/网络信息（输出地址可用于struct命令） |

## Bug搜索资源

- Launchpad bugs搜索：https://bugs.launchpad.net/ — 可输入关键异常堆栈搜索已知问题


## 延伸阅读

实操指南：[[skills/linux-vmcore-debugging]]

综合分析：[[synthesis/linux-dfx-tool-landscape]]

## 来源

- [[concepts/linux-vmcore-analysis]] — vmcore分析方法
- [[summaries/crash-vmcore-analysis]] — vmcore解析源文档摘要