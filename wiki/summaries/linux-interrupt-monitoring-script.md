---
title: 中断数变化实时观测脚本
category: summaries
tags: [linux, 中断, 监控脚本, /proc/interrupts]
source_dir: DFX工具
source_files: [==中断==/中断数变化实时观测脚本.md]
summary: 实时观测每秒中断数变化的bash脚本：基于/proc/interrupts两次采样的差值计算，支持屏蔽阈值过滤，不依赖额外模块。
provenance:
  extracted: 0.95
  inferred: 0.05
  ambiguous: 0.00
base_confidence: 0.78
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-02
---

# 中断数变化实时观测脚本

源文档提供了一个不依赖额外模块的bash脚本，用于动态观测每秒中断数变化。

## 概述

脚本通过两次读取 `/proc/interrupts`（间隔1秒），计算差值显示每秒中断增量，支持设定屏蔽阈值只显示大于阈值的数据。

## 核心观点

- 基于 `/proc/interrupts` 两次采样 + diff 计算中断增量
- 屏蔽阈值 `th=1`（可修改），只显示每秒增量大于阈值的中断
- 排除 `arch_timer`（高频定时器中断干扰视图）
- 支持 SIGHUP/SIGINT/SIGTERM 信号清理临时文件

## 关键细节

脚本核心逻辑：
1. `cat /proc/interrupts | grep -E ':([[:space:]]*[0-9]+){3,}' | grep -v arch_timer > pre` — 保存基线
2. `sleep 1` — 等待1秒
3. `cat /proc/interrupts > cur` — 保存新状态
4. `diff pre cur` — 计算差值
5. 对每个中断类型按CPU核计算 delta，超过阈值时输出 `cpuN: delta/s old→new` 格式


## 延伸阅读

实操指南：[[skills/linux-vm-debugging]]

## 来源

- 原始文档：`DFX工具/==中断==/中断数变化实时观测脚本.md`