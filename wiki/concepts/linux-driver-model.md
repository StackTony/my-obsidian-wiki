---
title: Linux 驱动模型与三大设备类型
category: concepts
tags: [linux, 内核, 驱动, 设备模型, 设备树]
aliases: [Linux驱动模型, 设备模型, LDM, bus-device-driver, 字符设备, 块设备, 网络设备]
relationships:
  - target: "[[summaries/linux-pci-subsystem]]"
    type: implements
  - target: "[[summaries/linux-block-subsystem]]"
    type: implements
  - target: "[[summaries/linux-network-device-subsystem]]"
    type: implements
  - target: "[[summaries/linux-usb-subsystem]]"
    type: implements
  - target: "[[concepts/linux-interrupt-system]]"
    type: uses
  - target: "[[concepts/linux-dma-mapping]]"
    type: uses
  - target: "[[synthesis/linux-kernel-subsystem-interactions]]"
    type: related_to
source_dir: Linux 操作系统/Linux 驱动管理
source_files: [1 Linux 驱动架构.md, Linux 字符设备 系统/Linux字符设备驱动.md]
summary: Linux 驱动总纲：字符/块/网络三类设备访问模型、LDM 的 bus-device-driver 三角与 probe 匹配、platform/PCI/I2C/SPI/USB/AMBA 总线框架、DTS 与中断/时钟/PM/DMA/GPIO/regmap 六大基础设施、devm 托管范式，以及字符设备 dev_t/cdev/fops 的注册与 open 路径。
provenance:
  extracted: 0.80
  inferred: 0.18
  ambiguous: 0.02
base_confidence: 0.76
lifecycle: draft
lifecycle_changed: 2026-11-11
tier: supporting
created: 2026-11-11
updated: 2026-11-12
---

# Linux 驱动模型与三大设备类型

Linux 驱动的核心思想只有一句：**把硬件抽象成文件，统一用 VFS 接口访问**。围绕这句话展开的全部机制——三大设备类型、设备模型、总线框架、DTS、子系统基础设施——构成了本页。它是本 vault 中 PCI/Block/网络/SCSI 四个子系统摘要的共同上游。

## 概述

内核分「框架层 + 驱动实现层」：框架处理通用逻辑（枚举、匹配、资源、电源），驱动只写硬件相关代码（寄存器序列、DMA 描述符、中断处理）。现代驱动范式可以压成一行：**DTS 描述硬件 + 框架驱动 + devm 托管资源**。

## 核心观点

- **三类设备按访问模型划分，不按硬件划分**：字符设备流式顺序访问（`cdev` + `file_operations`）／块设备按块随机访问（`gendisk` + `bio`）／网络设备不经 VFS、无设备文件（`net_device` + `sk_buff`）。
- **`miscdevice` 是简化版字符设备**：自动分配次设备号，写简单驱动常用。
- **LDM（Linux Device Model）是 2.6 以来所有硬件管理的底座**：`bus_type` / `device` / `device_driver` 三角，总线 `match()` 命中即调 `probe()`，拔出调 `remove()`；sysfs 与热插拔都建立在它上面。
- **总线框架的价值是"设备发现方式的差异"**：platform 靠 DTS、PCI 靠枚举、I2C/SPI 靠地址、USB 靠描述符——对驱动而言都收敛成 `probe(device)`。
- **驱动写法有代际差**：裸写 `cdev`（懂原理）→ 总线框架驱动（产品标准）→ devm 托管（自动释放，防泄漏）。
- **上下文限制是硬约束**：中断上下文不能睡眠（不能 `mutex_lock`、不能 `GFP_KERNEL` 分配）、不能直接解引用用户指针（必须 `copy_to_user/copy_from_user`）。

## 关键细节

### 分层总览

```
用户态应用
  ↓ syscall / socket
VFS / netlink / sysfs / udev        ← 统一接口层
  ↓
字符设备(cdev) | 块设备(bio/gendisk) | 网络设备(net_device) | TTY/input/misc
  ↓
Driver Core：bus_type / device_driver / device / kobject
  ↓
platform | PCI | USB | I2C | SPI | SDIO | AMBA     ← 物理/虚拟总线
  ↓
regmap / gpiod / pinctrl / clkdev / reset / PHY    ← 公共抽象
  ↓
中断(GIC/IOAPIC) | DMA(SMMU) | 内存(IOMEM/IOPORT)   ← 硬件资源
  ↓
硬件寄存器
```

### 三类设备对照

| 类型 | 访问模型 | 核心结构 | 典型设备 | 是否经 VFS |
|---|---|---|---|---|
| 字符设备 | 字节流、顺序 | `cdev`、`file_operations`、主/次设备号 | 串口、键鼠、LED、传感器、I2C/SPI 外设 | 是 |
| 块设备 | 扇区、随机、可缓存 | `block_device`、`gendisk`、`bio`、request 队列 | SSD、HDD、eMMC、SD | 是（有缓存与合并） |
| 网络设备 | 包、收发队列 | `net_device`、`sk_buff`、`ndo_start_xmit` | 网卡、WiFi、tap/veth | 否（socket 直达） |

### 字符设备：从设备号到 open

字符设备是三类设备中最基础的一类，其完整链路可作为理解"VFS 如何找到驱动"的样板：

- **设备号 `dev_t`**：32 位，高 12 位主设备号、低 20 位次设备号；`MAJOR/MINOR/MKDEV` 做位运算。主设备号标识驱动，次设备号标识实例。
- **`struct cdev`**：字符设备对象，内嵌 `kobject`、持有 `file_operations *ops` 与 `dev_t`；内核用 `cdev_map` 散列表（`major % 255`）按设备号管理所有 `cdev`。
- **`file_operations`**：`open/read/write/release/unlocked_ioctl/llseek` 等函数指针，是系统调用与驱动的桥梁。
- **注册五步**：申请设备号 → `cdev_init()` → `cdev_add()` → `device_create()`（或 `mknod`）→ 退出时逆序注销。
- **open 的关键一跳**：inode 初始只挂通用 `def_chr_fops`；`chrdev_open()` 用 `inode->i_rdev` 在 `cdev_map` 中查出 `cdev`，`replace_fops()` 把 `file->f_op` 换成驱动 fops，再回调驱动 `open()`。

数据面必须用 `copy_to_user()` / `copy_from_user()` 跨越用户/内核边界，不能直接解引用用户指针。完整展开见 [[summaries/linux-char-device-driver]]，可照抄的代码骨架见 [[skills/linux-char-device-driver-template]]。

### 重点总线框架

| 总线 | 适用 | 设备来源 |
|---|---|---|
| platform（虚拟总线，最常用） | SoC 片内外设（UART/GPIO/TIMER/RTC） | 设备树 DTS（旧版 board 文件） |
| PCI | 网卡、SSD、显卡 | 总线枚举 + 配置空间 |
| I2C | 传感器、EEPROM | `i2c_adapter` + `i2c_client` |
| SPI | Flash、ADC | `spi_master` + `spi_device` |
| USB | 外设 | host/device/gadget 三层，支持热插拔 |
| AMBA（ARM） | AHB/APB 内置外设 | DTS |

platform 的链路最典型：`DTS → platform_device → platform_driver → probe`。物理层的总线分类、带宽公式与 ISA→PCI→AGP→PCIe 演进见 [[summaries/linux-system-bus]]。

### USB 总线的特殊性

USB 是这批总线里唯一"设备发现不靠地址、不靠枚举表，而靠描述符"的，也是唯一**以接口（`usb_interface`）为驱动匹配粒度**的：一个物理设备可拆给多个驱动管。数据传输还多了一层 URB 抽象——不是直接读写寄存器，而是把请求封装成块提交给核心层。详见 [[summaries/linux-usb-subsystem]]。

### 六大核心基础设施

- **设备树 DTS**：硬件描述语言，把寄存器地址、中断号、时钟、电源、引脚从驱动代码剥离；`.dts` 板级、`.dtsi` SOC 公共；启动时解析生成各类 device，驱动在 probe 里用 `of_*` 读资源。
- **中断子系统**：GIC（ARM）/ IOAPIC（x86）；`request_irq` / `devm_request_irq`；下半部三选一——tasklet（简单原子）／workqueue（可睡眠，最常用）／threaded irq。
- **时钟 clk**：`struct clk`，开关与频率设置，SOC 必备。
- **电源管理 PM**：runtime PM（运行时开关）与 system sleep（suspend/resume），驱动给 `dev_pm_ops` 回调。
- **DMA 子系统**：`dma_alloc_coherent` 分配一致性内存，网卡与高速外设的标配（详见 [[concepts/linux-dma-mapping]]）。
- **GPIO**：gpiolib，DTS 指定引脚，`gpiod_*` 取代旧 `gpio_*`。
- **regmap**：统一封装 I2C/SPI/MMIO 寄存器访问，驱动只写 `regmap_read/write`。

### sysfs / devtmpfs / udev

- sysfs（`/sys`）：LDM 的文件化呈现，`bus/device/driver` 目录即内核对象树。
- devtmpfs：内核启动自动生成 `/dev` 节点。
- udev：用户态根据 uevent 创建设备节点、设权限、加载固件。

### 驱动上下文约束

| 上下文 | 能否睡眠 | 可用分配/锁 |
|---|---|---|
| 中断上下文（硬中断、softirq、tasklet） | 否 | `GFP_ATOMIC`、自旋锁 |
| 进程上下文（probe、read/write、workqueue） | 是 | `GFP_KERNEL`、mutex |

内核态不可直接解引用用户指针，必须经 `copy_to_user` / `copy_from_user`。

## 未解问题

- LDM 的 `kobject` 引用计数与 sysfs 生命周期细节，本页只到结构体名。
- 设备树 overlay（插件）在运行时的加载流程未展开；DMA 实验里用到过，但机制缺源。
- `devm_*` 的释放顺序（与 probe 失败路径的 unwind 顺序）需要单独确认。
- ACPI 与 device tree 双栈共存时的匹配优先级未覆盖。

## 来源

- `raw/sources/Linux 操作系统/Linux 驱动管理/1 Linux 驱动架构.md` — 驱动架构总览：三类设备、LDM、总线框架、六大基础设施、sysfs/udev、两种写法、上下文约束、学习路线
- `raw/sources/Linux 操作系统/Linux 驱动管理/Linux 字符设备 系统/Linux字符设备驱动.md` — 字符设备抽象、设备号/cdev/fops/file/inode、注册五步与 open 路径
- 交叉：[[summaries/linux-pci-subsystem]]、[[summaries/linux-block-subsystem]]、[[summaries/linux-network-device-subsystem]]、[[summaries/linux-scsi-subsystem]]、[[summaries/linux-usb-subsystem]]（五个子系统的具体实现）、[[summaries/linux-system-bus]]（物理总线标准）
