---
title: crash vmcore解析源文档摘要
category: summaries
tags: [linux, vmcore, crash, 崩溃分析]
source_dir: DFX工具
source_files: [==vmcore解析==/vmcore解析.md]
summary: crash工具分析vmcore的基本操作方法：启动命令、bt/struct/dis/rd/kmem等常用命令、时间戳转换、ps/files/mount/net等结构体查询入口。
provenance:
  extracted: 0.90
  inferred: 0.10
  ambiguous: 0.00
base_confidence: 0.78
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-02
---

# crash vmcore解析源文档摘要

源文档提供了 crash 工具分析 vmcore 的基本操作方法和常用命令。

## 概述

crash 分析 vmcore 的核心流程：加载 vmcore 和 vmlinux → 使用 bt/struct/dis 等命令分析崩溃状态。

## 核心观点

- 基本启动命令：`./crash vmcore vmlinux`
- 安装 kernel-debuginfo 包后 `bt -slf` 可显示函数偏移、源文件和每帧详细内容
- `ps/files/mount/net` 命令输出地址，可通过对应结构体的 `struct` 命令查看详情
- 时间戳转换：`date -d@'xxxxx' "+%Y-%m-%d %H:%M:%S"`
- 硬件关闭 SPCR 开关会导致无法记录硬件日志

## 关键细节

### 常用命令

| 命令 | 功能 |
|------|------|
| `bt` | 查看崩溃进程堆栈 |
| `foreach bt -c <cpu_id>` | 按CPU查看所有进程 |
| `bt -a | grep -i COMMAND | grep -v "PID: 0"` | 筛选问题堆栈 |
| `dis -s <addr>` | 源码级反汇编 |
| `dis -r <addr>` | 反汇编代码流程 |
| `rd -S <addr> <len>` | 查看内存内容+符号解析 |
| `struct task_struct <addr>` | 查看进程结构体 |
| `kmem -p <addr>` | 查看内存页信息 |

## 来源

- 原始文档：`DFX工具/==vmcore解析==/vmcore解析.md`