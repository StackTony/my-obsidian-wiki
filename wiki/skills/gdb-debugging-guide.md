---
title: GDB调试实操速查手册
category: skills
tags: [linux, gdb, 调试, QEMU, 断点, 观察点]
aliases: [GDB实操速查, gdb速查手册]
relationships:
  - target: "[[entities/gdb-tool]]"
    type: implements
  - target: "[[entities/libvirt-virsh]]"
    type: uses
source_dir: DFX工具
source_files: [==gdb调试==/gdb常用命令.md, ==gdb调试==/gdb调试qemu初始化流程.md]
summary: GDB调试实操速查手册：断点/观察点/执行控制/内存查看/多线程/多进程/Core Dump/汇编调试/信号处理/TUI九类场景命令速查+QEMU初始化调试特殊方法。
provenance:
  extracted: 0.85
  inferred: 0.10
  ambiguous: 0.05
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-02
---

# GDB调试实操速查手册

GDB调试常用命令的实操速查，从断点到QEMU特殊调试方法。

## 前置条件

- 安装 gdb 和目标程序的 debuginfo 包
- 理解 [[entities/gdb-tool]] 基础概念

## 步骤

### 1. 断点管理

```bash
break main               # 函数断点
break file.c:10          # 行号断点
break *0x400500           # 地址断点
tbreak main              # 临时断点（触发一次后删除）
break 10 if i==101       # 条件断点
ignore 1 10              # 忽略前10次触发
save breakpoints bp.txt  # 保存断点
source bp.txt            # 加载断点
```

### 2. 观察点（监控变量变化）

```bash
watch var                # 写入时停止
rwatch var               # 读取时停止
awatch var               # 读写都停止
watch *(int*)0x6009c8    # 监控指定地址内存
```

**注意**：硬件观察点性能优于软件观察点。

### 3. 执行控制

```bash
next/n                   # 不进入函数
step/s                   # 进入函数
continue/c               # 继续到下一个断点
finish                   # 执行到函数返回
return [value]           # 立即返回
until/u                  # 执行到循环结束
```

### 4. 内存查看 (x/nfu)

```bash
x/16xb arr               # 16字节十六进制
x/16tb arr               # 16字节二进制
x/16xw arr               # 16 word十六进制
x/s str                  # 字符串
```

格式：`n`=个数 `f`=格式(x/d/u/o/t/c/s) `u`=大小(b/h/w/g)

### 5. 多线程调试

```bash
info threads             # 列出所有线程
thread apply all bt      # 所有线程堆栈
thread 3                 # 切换线程
set scheduler-locking on # 只允许当前线程运行（调试死锁关键）
break func thread 2      # 线程断点
```

### 6. 多进程调试

```bash
set follow-fork-mode child    # 跟随子进程
set follow-fork-mode parent   # 跟随父进程
set detach-on-fork off        # 同时调试父子
info inferiors                # 查看所有进程
```

### 7. Core Dump 分析

```bash
gdb ./program core.12345      # 加载core文件
generate-core-file             # GDB中生成core dump
gcore <pid>                    # 对运行进程生成core dump
```

### 8. 信号处理

```bash
handle SIGUSR1 nostop          # 信号时不暂停
handle SIGUSR1 noprint         # 不打印
handle SIGUSR1 nopass          # 不传给程序
signal SIGUSR1                 # 发送信号
```

### 9. TUI 图形界面

```
tui enable / Ctrl+X A         # 进入TUI
layout src                    # 源码窗口
layout asm                    # 汇编窗口
layout split                  # 源码+汇编
layout regs                   # 寄存器窗口
Ctrl+X 2                      # 切换双窗口
```

### 10. QEMU初始化流程调试

```bash
# 1. 挂到libvirtd
gdb attach $(cat /var/run/libvirtd.pid)

# 2. 在fork前断住
(gdb) break virCommandSetPreExecHook
(gdb) cont

# 3. 外部启动虚拟机
virsh start $GUESTNAME

# 4. 进入QEMU子进程
(gdb) break main
(gdb) handle SIGKILL nopass noprint nostop
(gdb) handle SIGTERM nopass noprint nostop
(gdb) set follow-fork-mode child
(gdb) cont
# 进入QEMU main函数开始调试
```

## 常见问题

| 场景 | 方法 |
|------|------|
| 循环特定迭代 | `break loop.c:20 if i==100` |
| 变量被谁修改 | `watch global_var` |
| 多线程死锁 | `thread apply all bt` + `set scheduler-locking on` |
| Core文件分析 | `gdb ./program core` + `bt full` |
| 子进程调试 | `set follow-fork-mode child` |
| 无调试信息函数 | `set step-mode on` |

## 来源

- [[entities/gdb-tool]] — GDB工具实体页
- [[summaries/gdb-common-commands]] — GDB常用命令源文档摘要