---
title: ftrace/kprobe/bpftrace框架概述
category: summaries
tags: [linux, tracing, ftrace, kprobe, bpftrace]
source_dir: DFX工具
source_files: [==设置trace点==/1 ftrace和kprobe和bpftrace.md]
summary: 内核追踪三大框架概览：ftrace(静态函数追踪、完整调用链但开销大)、kprobe(动态探针、灵活追踪任意内核函数)、bpftrace(eBPF可编程追踪)。
provenance:
  extracted: 0.70
  inferred: 0.25
  ambiguous: 0.05
base_confidence: 0.78
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-02
---

# ftrace/kprobe/bpftrace框架概述

源文档以树状结构对比了三大内核追踪框架。

## 概述

Linux内核追踪框架分为静态(ftrace)和动态(kprobe/bpftrace)两类。

## 核心观点

- **ftrace**：优点是完整函数调用链和 function_graph；缺点是只能追踪静态函数、开销大
- **kprobe**：优点是可追踪任意内核函数、灵活；典型应用场景为 sched_switch、virtio_notify 等
- **bpftrace**：源文档仅以树状图形式提及，未详细展开使用方法 ^[ambiguous]

## 来源

- 原始文档：`DFX工具/==设置trace点==/1 ftrace和kprobe和bpftrace.md`