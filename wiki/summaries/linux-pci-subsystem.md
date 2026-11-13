---
title: Linux PCI 子系统
category: summaries
tags: [linux, pcie, 内核, 驱动, 总线]
aliases: [PCI子系统, PCIe子系统, Linux内核PCI子系统, pci_dev, pci_bus]
relationships:
  - target: "[[concepts/linux-driver-model]]"
    type: implements
  - target: "[[summaries/pci-bar-dma-space]]"
    type: related_to
  - target: "[[concepts/linux-dma-mapping]]"
    type: related_to
  - target: "[[concepts/linux-interrupt-system]]"
    type: uses
  - target: "[[summaries/linux-block-subsystem]]"
    type: related_to
source_dir: Linux 操作系统/Linux 驱动管理/Linux PCI 系统
source_files: [Linux内核PCI子系统.md, Linux PCI设备BDF号.md, Linux PCIe设备枚举.md]
summary: PCIe 子系统四层架构（硬件适配/总线核心/驱动适配/用户交互）与 pci_dev/pci_driver/pci_bus 三结构体；BDF 三元组寻址、ACPI 根节点匹配与 pci_scan_child_bus 递归枚举、配置空间 256B→4096B、6个BAR、MSI/MSI-X、ASPM/AER/TLP 与 Root Complex 拓扑。
provenance:
  extracted: 0.84
  inferred: 0.13
  ambiguous: 0.03
base_confidence: 0.82
lifecycle: draft
lifecycle_changed: 2026-11-11
tier: supporting
created: 2026-11-11
updated: 2026-11-12
---

# Linux PCI 子系统

野火 RK356x 驱动教程「PCI 子系统」章节的蒸馏：PCIe 在软件层保持与 PCI 向后兼容（配置空间布局、BAR 机制、驱动模型），内核用同一套 `pci_*` 接口描述两者，只在 PCIe Core 层额外处理 ASPM、AER、MSI-X 等专属能力。

## 概述

PCIe 不是"更好的 PCI"，而是换了物理层语义：并行共享总线（PCI，1992，≤533MB/s）→ 串行点对点差分（PCIe，2002，每 Lane 一对收/发差分对，全双工，5.0 单链路 32GT/s）。软件兼容靠三件事保持不变——配置空间、BAR、驱动模型。^[inferred]

## 核心观点

- **配置空间是设备的身份证**：PCI 设备 256 字节（0x00~0xFF），PCIe 扩展到 4096 字节，分标准配置头 / Capability / 扩展 Capability 三段。
- **BAR 是资源申报而非资源分配**：设备通过 BAR 告知"我要多大空间"，内核在枚举阶段探测并分配物理地址，驱动再用 `pci_iomap` 映射为内核虚拟地址。
- **PCIe 三大能力都挂在 Capability 链上**：MSI/MSI-X（中断）、ASPM（链路电源）、AER（错误上报）都是 Capability，内核枚举时解析能力偏移写入 `pci_dev` 的 `msi_cap`/`msix_cap`/`pm_cap` 字段。
- **四层架构的核心意义是把"架构差异"压到最底层**：x86/ARM64/RISC-V 的配置读写、总线扫描、中断路由、DMA 寻址差异全部封在硬件适配层，上层代码平台无关。
- **驱动只写 probe/remove**：枚举、资源仲裁、能力解析、电源状态都由核心层包办，这是 LDM（设备模型）在 PCI 上的具体实现。

## 关键细节

### 关键概念表

| 概念 | 要点 |
|---|---|
| 配置空间 | 256B（PCI）/ 4096B（PCIe）；标准头 + Capability + 扩展 Capability |
| BAR 空间 | 最多 6 个，可映射 MMIO 或 IO 端口；枚举期探测大小并分配物理地址 |
| MSI | 基于内存写的中断，最多 32 个向量，取代 INTx 边带信号 |
| MSI-X | MSI 增强，最多 2048 个向量，向量可灵活配置，适配多队列网卡 |
| ASPM | 链路电源管理，L0 工作 / L1 轻度休眠 / L2 深度休眠 |
| CLKREQ | 硬件级时钟省电，空闲时请求切断参考时钟，降幅大于 ASPM |
| DBI | PCIe 3.0+ 直接后台接口，可访问物理层/链路层私有寄存器，无需复位 |
| 三类资源空间 | IO 空间（x86 端口寻址，现代 PCIe 基本不用）/ 非预取内存（MMIO 寄存器）/ 预取内存（显存、SSD，可预读缓存） |
| TLP | 事务层数据包：包头 + 载荷 + 校验尾；支持乱序、流量控制、重传 |
| AER | 扩展 Capability，细化上报链路 CRC/TLP 校验/协议错误 |

### PCIe 拓扑

树状结构，与 PCI 扁平总线完全不同：

- **Root Complex**：连 CPU 与系统内存的根节点，启动时发起枚举，运行时把 CPU 的内存访问转成 TLP。
- **Root Port**：RC 向外提供的物理槽位/逻辑端口。
- **RCIEP**：根复合体集成端点，板载网卡、NVMe 控制器可直接集成进 RC。
- **Switch**：一个上游端口 + 多个下游端口，内部 Crossbar 做端口间转发。
- **Endpoint**：叶子节点（GPU、NVMe SSD、网卡、USB 控制器）。
- **Link**：点对点、全双工、独立带宽。

### BDF 三元组：配置空间的全局地址

PCI/PCIe 用 **BDF（Bus–Device–Function）** 唯一标识一个功能：

| 字段 | 位宽 | 范围 | 含义 |
|---|---|---|---|
| Bus | 8 bit | 0–255 | Bus 0 通常是 Root Complex 出来的第一根总线；每个桥下游分配新 Bus 号 |
| Device | 5 bit | 0–31 | 每根总线最多 32 个设备插槽；PCIe 中一个端口就是一个设备 |
| Function | 3 bit | 0–7 | 每个设备最多 8 个功能；Function 0 为主功能，1–7 可为多功能（显卡+音频、网卡+iSCSI Offload） |

- 每个 Function 有 4KB 配置空间（PCIe），前 256B 是 PCI 兼容头。
- 硬件访问用 Configuration TLP（`CfgRd`/`CfgWr`）；Linux 映射为 `/sys/bus/pci/devices/0000:02:00.0/` 与 `/proc/bus/pci/`。
- `lspci` 按 BDF 列出设备，`setpci` 按 BDF 精确读写配置寄存器；驱动用 `pci_device_id` 匹配 Vendor/Device ID，同时依赖 BDF 定位设备。

### 枚举流程：从 ACPI 根节点到递归扫描

1. **注册根节点处理器**：ACPI 初始化时把 `pci_root_handler`（匹配 `PNP0A03`）挂到 `acpi_scan_handlers_list`。
2. **创建根设备并匹配**：`acpi_bus_scan()` 创建 ACPI 设备，`acpi_scan_match_handler()` 用 `device->pnp.ids` 匹配到 `pci_root_handler`，回调 `acpi_pci_root_add`。
3. **创建根总线**：`pci_acpi_scan_root()` → `acpi_pci_root_create()` → `pci_create_root_bus()` 创建 Host Bridge 与第一根总线（bus0）。
4. **扫描总线**：`pci_scan_child_bus()` → `pci_scan_child_bus_extend()` → `pci_scan_slot()` 遍历 32 个 Device；每个 Device 内 `pci_scan_single_device()` 遍历 8 个 Function。
5. **扫描单个功能**：`pci_scan_device()` 先读厂商号判断设备是否存在（`pci_bus_read_dev_vendor_id`），再 `pci_alloc_dev()` 分配 `pci_dev`，`pci_setup_device()` 判定 EP/桥并读 BAR（`pci_read_bases`，即"BAR 写全 1 读回大小"的实现）。
6. **注册设备**：`pci_device_add()` 初始化 ACS 等能力、把设备挂到 `bus->devices`、`device_add()` 注册到驱动模型等待匹配。
7. **桥与子总线**：`pci_scan_bridge_extend()` 遍历总线上的设备，识别桥后读取上游/下游总线号，`pci_add_new_bus()` 建立子总线并递归 `pci_scan_child_bus()`；若由 OS 分配总线号，则先清配置空间再重新分配并写回。

### 四层软件架构

1. **硬件适配层** — 对接具体 PCI 控制器：物理扫描、配置空间原生读写、控制器初始化、中断路由、DMA 通道、总线资源区间注册。
2. **总线核心管理层** — 平台无关：逐级枚举（RC → Bridge → Endpoint）、解析配置空间、统一仲裁 IO/内存/预取三类资源、解析 Capability、管理电源与链路、处理 TLP 异常。
3. **驱动适配层** — 给驱动开发者的 API：驱动注册注销、ID 匹配、设备使能、配置读写、BAR 映射、MSI/MSI-X 配置、DMA 掩码、挂起唤醒回调。
4. **用户交互层** — sysfs 暴露总线/设备/资源/链路状态，供 lspci、调试脚本读写。

### 核心结构体

- `struct pci_dev` — 一个枚举到的设备一个实例：`devfn`（设备号+功能号）、`vendor/device/subsystem_*`、`class`、`pci_cap/msi_cap/msix_cap/pm_cap` 能力偏移、`dma_mask`、`resource[]`（BAR 资源域）、`current_state`（D0~D3）、`is_busmaster`、`enable_cnt`。
- `struct pci_driver` — `id_table` 匹配表 + `probe/remove/suspend/resume/shutdown` + `sriov_configure`（SR-IOV 虚拟化）+ `err_handler`（AER 恢复）。
- `struct pci_bus` — `parent/children/devices` 构成总线树，`ops` 指向配置空间读写函数集，`number/primary` 总线号。
- `struct pci_device_id` — `vendor/device/subvendor/subdevice/class/class_mask`，`PCI_ANY_ID` 为通配。
- `struct pci_ops` — 屏蔽平台的配置空间读写实现（`read/write/map_bus`）。

### 常用 API 分组

| 分组 | 函数 |
|---|---|
| 注册/使能 | `pci_register_driver`、`pci_enable_device`、`pci_disable_device` |
| 配置空间 | `pci_read_config_byte/word/dword`、`pci_write_config_*` |
| BAR 资源 | `pci_resource_start/len/flags`、`pci_request_regions` |
| BAR 映射 | `pci_iomap` / `pci_iounmap` |
| 私有数据 | `pci_set_drvdata` / `pci_get_drvdata` |
| 能力/AER | 能力遍历、`pci_enable_msi` / `pci_alloc_irq_vectors`（MSI-X） |
| DMA | `pci_set_master`（开总线主控）、`dma_set_mask_and_coherent` |
| 电源 | `pci_set_power_state`、`pci_save_state`/`pci_restore_state` |

### 一个真实驱动的骨架（8.5 网卡源码解析归纳）

`pci_device_id` 表 → `probe`：`pci_enable_device` → `pci_request_regions` → `pci_iomap` → `dma_set_mask_and_coherent` → 分配 DMA 环 → `pci_alloc_irq_vectors`（MSI-X）→ 注册 netdev；`remove`/`shutdown` 对称释放。 ^[inferred]

## 未解问题

- 热插拔（PCIe hotplug + ACPI `_OSC`）与内核枚举的交互细节，本文未覆盖。
- AER 错误恢复的三级策略（重试 / 链路重置 / 设备降级）只有结论，缺具体状态机。
- SR-IOV 只介绍了 `sriov_configure` 等回调，PF/VF 的 BAR 与 MSI-X 分配策略未展开。
- 与 [[summaries/pci-bar-dma-space]] 的口径差异：BAR 大小探测细节在那边更完整，本文只给结论。 ^[inferred]

## 来源

- `raw/sources/Linux 操作系统/Linux 驱动管理/Linux PCI 系统/Linux内核PCI子系统.md` — 野火 RK356x 驱动教程第 8 章：PCI/PCIe 基础、四层架构、核心结构体与函数、PCIe 网卡驱动源码解析、PCI Explorer/DMA/IRQ 三个实验
- `raw/sources/Linux 操作系统/Linux 驱动管理/Linux PCI 系统/Linux PCI设备BDF号.md` — BDF 三元组、配置空间寻址与 lspci/setpci 实践
- `raw/sources/Linux 操作系统/Linux 驱动管理/Linux PCI 系统/Linux PCIe设备枚举.md` — ACPI 根节点匹配、pci_scan_child_bus 递归扫描、pci_scan_device/pci_device_add、桥与子总线建立
- 交叉：[[summaries/pci-bar-dma-space]]（BAR 探测与枚举实践）、[[concepts/linux-driver-model]]（LDM 与总线框架）、[[summaries/linux-system-bus]]（总线标准演进）
