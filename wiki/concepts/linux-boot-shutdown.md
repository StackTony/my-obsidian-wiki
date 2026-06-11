---
title: Linux启动与关机
category: concepts
tags: [linux, 内核, 启动, 关机, systemd, ACPI]
aliases: [Linux启动流程, Linux关机流程, boot process, shutdown]
relationships:
  - target: "[[concepts/linux-process-scheduling]]"
    type: related_to
  - target: "[[concepts/linux-interrupt-system]]"
    type: related_to
  - target: "[[concepts/linux-namespace-cgroups]]"
    type: related_to
source_dir: Linux 操作系统/Linux 系统启动关闭
source_files: [Linux 启动详细过程（开机启动顺序）.md, Linux 关机流程深度解析：从内核机制到硬件控制的完整理论框架.md]
summary: Linux启动10步流程(BIOS→MBR→GRUB→Kernel→init→rc.sysinit→modules→runlevel→rc.local→login)，关机多子系统协调(SIGTERM→sync→unmount→driver shutdown→ACPI power off)。
provenance:
  extracted: 0.80
  inferred: 0.15
  ambiguous: 0.05
base_confidence: 0.85
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: supporting
created: 2026-06-01
updated: 2026-06-11
---

# Linux启动与关机

Linux的启动与关机是内核生命周期中最复杂的多子系统协调过程。启动涉及从硬件自检到用户登录的10步链式流程，关机则需要用户空间与内核空间的精确协作，确保数据完整性和硬件安全断电。

## 核心观点

- Linux启动遵循10步链式流程：BIOS → MBR → GRUB → Kernel → init → rc.sysinit → modules → runlevel → rc.local → login，每一步依赖前一步的正确完成。
- 关机流程是一个多子系统协调过程：用户空间发起 → SIGTERM广播 → SIGKILL强制 → sync刷盘 → 依赖序卸载文件系统 → 驱动shutdown回调 → ACPI电源管理 → 架构特定停机指令。
- systemd 对传统 SysVinit 的关键改进：并行启动服务、[[concepts/cgroups-v2-deep-dive|Cgroups v2]] 资源追踪、journal 日志系统、target 替代 runlevel。 ^[inferred]
- ACPI 是关机的最终执行者，通过 DSDT 表中的 _PTS/_GTS 方法通知硬件即将断电，最终触发架构特定的停机指令。

## 关键细节

### 启动10步流程

| 步骤 | 名称 | 核心职责 |
|------|------|----------|
| 1 | BIOS | 硬件自检(POST)，读取MBR引导扇区 |
| 2 | MBR | 主引导记录（512字节），定位活动分区 |
| 3 | GRUB | 引导加载器，选择内核+initrd，传递参数 |
| 4 | Kernel | 内核初始化：解压、硬件检测、驱动加载、mount rootfs |
| 5 | init | 第一个用户进程(PID=1)，读取/etc/inittab |
| 6 | rc.sysinit | 系统初始化脚本：设置主机名、挂载文件系统、启动swap |
| 7 | modules | 按需加载内核模块(modprobe) |
| 8 | runlevel | 执行对应运行级别的服务脚本(/etc/rc.d/rcN.d/) |
| 9 | rc.local | 用户自定义启动脚本 |
| 10 | login | 用户登录界面（getty + login） |

**内核初始化（步骤4）详细过程**：
- 内核解压到内存合适位置
- 检测CPU类型和内存布局
- 初始化中断控制器、时钟、[[concepts/linux-memory-management|Linux内存管理]]
- 加载initrd中的必要驱动（如存储驱动）
- mount rootfs（根文件系统）
- 启动 init 进程（PID=1）

### 运行级别（Runlevels）

| Runlevel | 含义 | systemd target |
|----------|------|----------------|
| 0 | 关机 | poweroff.target |
| 1 | 单用户模式（维护） | rescue.target |
| 2 | 多用户（无NFS） | multi-user.target |
| 3 | 完整多用户（命令行） | multi-user.target |
| 4 | 未使用/自定义 | multi-user.target |
| 5 | 图形界面 | graphical.target |
| 6 | 重启 | reboot.target |

systemd 用 target 替代 runlevel，支持更多粒度的状态定义。

### 关机流程

关机是一个多阶段、多子系统协作的过程：

**1. 用户空间阶段**：
- 用户执行 shutdown/poweroff/halt 命令
- systemd 发起有序关机（并行按依赖序停服务）

**2. 进程管理阶段**：
- SIGTERM 广播给所有用户进程（等待超时）
- SIGKILL 强制杀死未响应进程
- 内核线程逐步停止（非关键线程先停）

**3. 文件系统阶段**：
- sync() 将所有脏页刷回磁盘
- 更新 superblock 时间戳和状态
- 按依赖顺序卸载文件系统（先非根、后根）
- 标记文件系统为clean状态

**4. 驱动与子系统阶段**：
- 非关键驱动执行 shutdown 回调
- 网络子系统断开连接
- 停止定时器和工作队列

**5. 内核最终阶段**：
- 检查 CAP_SYS_BOOT 权限
- 调用 kernel_power_off() / kernel_halt()
- 非关键CPU停止
- 主CPU执行架构特定停机指令

**6. ACPI 阶段**（poweroff）：
- 执行 DSDT 中的 _PTS(Power Transition) 方法通知硬件
- 发送 GPE(General Purpose Event) 事件
- 写入 ACPI 寄存器触发硬件断电
- 架构特定：x86 → cli + halt; ARM → wfi + ATF + PSCI; RISC-V → SBI ecall

### systemd 对 SysVinit 的改进

| 特性 | SysVinit | systemd |
|------|----------|---------|
| 启动方式 | 串行执行脚本 | 并行启动按依赖排序的unit |
| 进程追踪 | PID文件（不可靠） | cgroups（可靠追踪所有子进程） |
| 日志系统 | /var/log 下分散文件 | journal（二进制结构化日志） |
| 服务管理 | service命令 | systemctl命令 |
| 状态定义 | 7个runlevel | 多种target（更细粒度） |

## 未解问题

- 快速启动技术（如 systemd-analyze blame 分析慢服务）的优化策略，本文未深入展开。 ^[inferred]
- kexec 跳过BIOS直接加载新内核的快速重启机制，来源中未涉及。 ^[ambiguous]


## 延伸阅读

综合分析：[[synthesis/linux-kernel-subsystem-interactions]]

## 来源

- [[summaries/linux-meminfo-params]] — 启动过程中内存管理器初始化的背景
- [[summaries/linux-softirq-detail]] — 内核初始化中断子系统