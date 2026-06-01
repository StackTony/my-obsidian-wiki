---
title: Linux启动与关机
category: concepts
tags: [linux, 启动, 关机, 内核]
aliases: [Linux Boot Process, Linux Shutdown]
relationships:
  - target: "[[concepts/linux-namespace-cgroups]]"
    type: uses
  - target: "[[concepts/linux-process-scheduling]]"
    type: uses
source_dir: Linux 操作系统/Linux 系统启动关闭
source_files: [Linux 启动详细过程（开机启动顺序）.md, Linux 关机流程深度解析：从内核机制到硬件控制的完整理论框架.md]
summary: Linux启动10步流程：BIOS→MBR→GRUB→Kernel(start_kernel)→init→login。关机是多子系统精密协调：SIGTERM→SIGKILL→sync+unmount→ACPI断电。systemd并行化设计。
provenance:
  extracted: 0.75
  inferred: 0.20
  ambiguous: 0.05
base_confidence: 0.608
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: supporting
created: 2026-06-01
updated: 2026-06-01
---

# Linux启动与关机

## 核心观点

### 启动10步流程

| 步骤 | 动作 | 关键点 |
|---|---|---|
| 1 | BIOS加载 | 检测硬件、确定启动顺序 |
| 2 | MBR读取 | 硬盘0磁道第一扇区(512字节)，复制到0x7c00 |
| 3 | Boot Loader(GRUB) | 加载内核映像、解压缩 |
| 4 | Kernel(start_kernel) | 初始化各种设备、建立核心环境，设备发现流程见 [[concepts/linux-io-stack]] |
| 5 | init进程 | 第一个用户进程(PID=1)，读取/etc/inittab |
| 6 | runlevel设定 | Linux运行等级0-6(关机/单用户/多用户/X-Window) |
| 7 | rc.sysinit | 设定PATH、网络、swap、/proc |
| 8 | 内核模块加载 | 依据/etc/modules.conf |
| 9 | rc.d脚本 | 按运行级别执行初始化脚本 |
| 10 | login | 执行/bin/login，等待用户登录 |

### 关机子系统协同

关机是多子系统精密协调的过程：

**进程管理子系统**：
1. SIGTERM广播 → 进程优雅退出(守护进程执行清理)
2. 超时等待(5-10秒) → SIGKILL强制终止
3. 停止非关键内核线程，保留kthreadd等核心线程

**文件系统子系统**：
1. 构建挂载点依赖图
2. `sync()`触发数据落盘
3. 遍历superblock执行write_super
4. 调用kill_sb()释放资源

**设备管理子系统**：
1. 刷新块设备缓存
2. 驱动shutdown方法
3. ACPI/APM硬件断电

### systemd并行化革新

systemd重新定义启动/关机流程：

- **依赖图+cgroups**：并行停止单元，批量终止进程组
- **journald日志**：完整时间线，`systemd-analyze blame`分析耗时
- **target单位**：替代runlevel概念(poweroff.target/reboot.target)

### 硬件抽象层差异

不同架构关机实现：

| 架构 | 关机指令序列 | 特点 |
|---|---|---|
| x86 | cli禁中断 → halt指令 | 简单直接 |
| ARM | wfi指令 → ATF → PSCI | 需TrustZone Firmware配合^[inferred] |
| RISC-V | pm_cfg寄存器 → SRET → SBI | 通过Supervisor Binary Interface |

### 异常处理机制

防止关机死锁的多层防护：

- **硬件看门狗**：CONFIG_WATCHDOG，定期喂狗防止重置
- **进程树监控**：检测循环依赖，强制回收僵尸进程
- **资源泄漏检测**：检查/proc/slabinfo、vmalloc区域

## 未解问题

- Fast Boot/Skip Boot优化技术细节？
- 容器环境下关机流程的命名空间协调？

## 来源

- `raw/sources/Linux 操作系统/Linux 系统启动关闭/Linux 启动详细过程（开机启动顺序）.md` — 10步启动流程、runlevel含义
- `raw/sources/Linux 操作系统/Linux 系统启动关闭/Linux 关机流程深度解析：从内核机制到硬件控制的完整理论框架.md` — 子系统协同、systemd并行化、架构差异