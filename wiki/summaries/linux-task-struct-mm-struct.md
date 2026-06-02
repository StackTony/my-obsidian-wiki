---
title: task_struct与mm_struct结构体详解
category: summaries
tags: [linux, 内核, task_struct, mm_struct, 进程, 内存]
source_dir: DFX工具
source_files: [==vmcore解析==/进程结构task_struct和mm_struct.md]
summary: Linux内核进程描述符task_struct与内存描述符mm_struct的详细结构关系：task→mm→VMA→pgd四级链式结构、多线程共享mm、内核线程active_mm借用机制。
provenance:
  extracted: 0.90
  inferred: 0.08
  ambiguous: 0.02
base_confidence: 0.78
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-02
---

# task_struct与mm_struct结构体详解

源文档详细描述了Linux内核进程和内存管理的两大核心数据结构及其关系。

## 概述

- **task_struct**（进程描述符/PCB）是内核围绕进程建立的核心数据结构，包含进程标识/调度信息/内存管理/文件系统/信号处理
- **mm_struct**（内存描述符）描述进程的完整虚拟地址空间，包含VMA链表/红黑树/页表pgd/各段起止地址
- 二者通过 `task_struct.mm` 指针连接，形成 task→mm→VMA→pgd 四级链式结构

## 核心观点

- task_struct 的 `mm` 和 `active_mm` 是理解进程内存的关键：普通进程 mm≠NULL，内核线程 mm=NULL 借用 active_mm
- mm_struct 内部通过 VMA 链表(`mmap`)和红黑树(`mm_rb`)双重组织虚拟内存区域
- 页表映射链：mm_struct → pgd → pmd → pte → 物理页框
- 多线程共享：同线程组的所有 task_struct 指向同一个 mm_struct（共享地址空间但各线程栈独立）

## 关键细节

### task_struct 核心字段

| 字段 | 说明 |
|------|------|
| pid, tgid | 进程ID和线程组ID |
| *parent | 父进程指针 |
| children, sibling | 子进程链表和兄弟链表 |
| *mm | 用户空间内存描述符 ★ |
| *active_mm | 内核线程借用的内存描述符 ★ |
| *files | 打开文件表 |
| *signal | 信号处理 |

### mm_struct 核心字段

| 字段 | 说明 |
|------|------|
| *mmap | VMA链表头 ★ |
| mm_rb | VMA红黑树根 ★ |
| mmap_base | mmap区域基址 |
| start_code/end_code | 代码段起止 |
| start_data/end_data | 数据段起止 |
| start_brk/brk | 堆起止 |
| start_stack | 栈起始 |
| *pgd | 页全局目录 ★ |
| mm_users/mm_count | 用户计数和引用计数 |

### vm_area_struct (VMA) 字段

| 字段 | 说明 |
|------|------|
| vm_start/vm_end | 区域起止虚拟地址 |
| *vm_next | 链表下一个 |
| vm_rb | 红黑树节点 |
| vm_flags | 权限标志(读/写/执行) |
| *vm_ops | 操作函数 |
| *vm_file | 关联文件(映射时) |

### 关系总结

| 关系 | 说明 |
|------|------|
| task→mm | 一对一(普通进程)或共享(多线程) |
| mm→VMA | 一对多，一个地址空间包含多个VMA |
| mm→pgd | 每个进程独立页表实现地址空间隔离 |
| 线程共享 | 同线程组共享mm_struct |
| 内核线程 | mm=NULL，借用active_mm |

## 来源

- 原始文档：`DFX工具/==vmcore解析==/进程结构task_struct和mm_struct.md`