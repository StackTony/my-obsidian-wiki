---
title: Linux vmcore崩溃分析实操手册
category: skills
tags: [linux, vmcore, crash, 崩溃分析, 寄存器, 内核调试]
aliases: [vmcore分析实操, crash实操, 崩溃转储分析]
relationships:
  - target: "[[concepts/linux-vmcore-analysis]]"
    type: implements
  - target: "[[entities/crash-tool]]"
    type: uses
source_dir: DFX工具
source_files: [==vmcore解析==/vmcore解析.md, ==vmcore解析==/寄存器和地址分布.md, ==vmcore解析==/调度sched.md, ==vmcore解析==/进程结构task_struct和mm_struct.md, ==vmcore解析==/开源crash网站.md]
summary: vmcore崩溃分析实操手册：crash工具加载→堆栈回溯→寄存器解读→结构体分析→崩溃类型识别的完整流程，覆盖x86_64和ARM64两大架构。
provenance:
  extracted: 0.65
  inferred: 0.30
  ambiguous: 0.05
base_confidence: 0.72
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-02
---

# Linux vmcore崩溃分析实操手册

vmcore崩溃转储分析的完整实操流程：从加载到解读，覆盖两大架构。

## 前置条件

- 安装 crash 工具和对应版本的 kernel-debuginfo 包
- 准备 vmcore 文件和 vmlinux（带符号表的内核映像）
- 确认硬件 SPCR 开关未关闭（否则无硬件日志）
- 理解 [[concepts/linux-vmcore-analysis]] 基础概念

## 步骤

### 1. 加载 vmcore

```bash
./crash vmcore vmlinux
```

### 2. 堆栈回溯

```bash
# 基本堆栈
crash> bt

# 增强版堆栈（函数偏移+源文件+详细内容）—需debuginfo包
crash> bt -slf

# 按CPU查看
crash> foreach bt -c <cpu_id>

# 筛选问题堆栈
crash> bt -a | grep -i COMMAND | grep -v "PID: 0"
```

### 3. 寄存器解读

#### x86_64 崩溃分析要点

| 字段 | 分析 |
|------|------|
| **RIP** | 崩溃指令地址 → `dis -s <addr>` 查看源码 |
| **RSP** | 栈指针 → 检查栈溢出/损坏 |
| **RDI/RSI/RDX** | 第1-3参数 → 结合源码判断合法性 |
| **RBP** | 帧指针 → 回溯调用栈 |

#### ARM64 崩溃分析要点

| 字段 | 分析 |
|------|------|
| **PC** | 崩溃指令地址 → `dis -s <addr>` 查看源码 |
| **LR(X30)** | 返回地址 → 回溯调用链 |
| **SP** | 栈指针 → 检查栈溢出 |
| **X0-X7** | 函数入参 → 分析参数合法性 |
| **FP(X29)** | 帧指针 → 栈回溯 |

### 4. 结构体分析

```bash
# 进程结构体
crash> struct task_struct <addr>

# 内存描述符
crash> struct mm_struct <addr>

# 内存页信息
crash> kmem -p <addr>
```

### 5. 反汇编与内存查看

```bash
crash> dis -s <addr>    # 源码级反汇编（需debuginfo）
crash> dis -r <addr>    # 反汇编代码流程
crash> rd -S <addr> <len>  # 查看内存+符号解析
```

### 6. 时间戳转换

```bash
date -d@'<timestamp>' "+%Y-%m-%d %H:%M:%S"
```

### 7. 崩溃类型识别

| 崩溃信息 | 类型 | 排查方向 |
|----------|------|----------|
| `NULL pointer dereference at 0x123` | 空指针解引用 | `bt`找崩溃函数 → 检查入参 |
| `paging request at ffffdeadbeef0000` | UAF毒值 | 检查是否有释放后使用 |
| `stack segment: 0000 [#1] SMP` | 栈溢出 | 检查无限递归或大局部变量 |

### 8. Bug搜索

已知内核bug搜索：https://bugs.launchpad.net/ — 输入关键异常堆栈搜索匹配问题。

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 无硬件日志 | SPCR开关关闭 | 确认硬件SPCR开启 |
| bt输出不完整 | 缺debuginfo包 | 安装kernel-debuginfo |
| 地址无法解析符号 | 符号表缺失 | 使用正确的vmlinux版本 |

## 进阶用法

- **ARM64 EL级别判断**：PC在EL1=内核崩溃、EL2=Hypervisor崩溃 ^[inferred]
- **调度分析**：主调度器(进程主动放弃CPU) vs 周期性调度器(定时检测切换) — 两者在vmcore中表现为不同堆栈模式 ^[inferred]
- **交叉引用**：`ps/files/mount/net` 输出地址 → `struct <结构体> <addr>` 深入分析

## 来源

- [[concepts/linux-vmcore-analysis]] — vmcore分析方法
- [[entities/crash-tool]] — crash工具实体页
- [[summaries/linux-task-struct-mm-struct]] — task_struct/mm_struct结构体详解