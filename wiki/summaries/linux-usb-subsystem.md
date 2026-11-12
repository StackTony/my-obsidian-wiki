---
title: Linux USB 子系统（框架与 HID 驱动）
category: summaries
tags: [linux, USB, 内核, 驱动, HID]
aliases: [USB子系统, USB Core, HCD, URB, usb_driver]
relationships:
  - target: "[[concepts/linux-driver-model]]"
    type: extends
  - target: "[[concepts/linux-dma-mapping]]"
    type: uses
  - target: "[[concepts/linux-interrupt-system]]"
    type: related_to
source_dir: Linux 操作系统/Linux 驱动管理/Linux USB 系统
source_files: [Linux内核USB子系统.md]
summary: 野火 USB 子系统手册：主从拓扑（≤127 设备）、端点/管道/四种传输、三层架构（HCD/USB Core/设备驱动）、以接口为匹配粒度的六大结构体与 URB API、HID 引导协议键鼠 8/4 字节报文。
provenance:
  extracted: 0.85
  inferred: 0.12
  ambiguous: 0.03
base_confidence: 0.59
lifecycle: draft
lifecycle_changed: 2026-11-11
tier: supporting
created: 2026-11-11
updated: 2026-11-11
---

# Linux USB 子系统（框架与 HID 驱动）

USB 是"热插拔 + 即插即用 + 统一接口"的外部总线，内核用一套三层架构把 OHCI/UHCI/EHCI/XHCI 四种主机控制器的差异全部吃掉，驱动开发者只面对 USB Core 与 URB。本页是该子系统的结构与 API 速查，总纲位置见 [[concepts/linux-driver-model]]。

## 概述

驱动只需实现四件事：**设备匹配（`id_table`）→ 初始化（`probe`）→ 数据收发（URB）→ 释放（`disconnect`）**。硬件寄存器、总线时序、DMA、中断由 HCD 层包办。

## 核心观点

### 总线模型：主从 + 单向

- USB 是**主从架构**，只有 Host 能主动发起通信，设备只能被动响应——不存在设备主动上报。所以"设备有数据"要靠主机**周期性轮询**，而不是设备推。
- 拓扑为 `主机控制器 → Hub（可多级级联）→ 外设`，单条总线最多 **127 个设备**。
- **端点（Endpoint）**是最小通信单元，即设备内存中的独立缓冲区，编号 0~15；**0 号端点强制存在**，专用于枚举、配置、状态查询。端点带方向：IN（设备→主机）、OUT（主机→设备）。
- **管道（Pipe）**是内核对"主机↔端点"通道的抽象，把设备地址、端点号、传输类型、方向编码成一个整型值，由 `usb_rcvintpipe`/`usb_sndbulkpipe` 等内联函数生成。

### 四种传输模式与 URB

| 模式 | 特性 | 典型设备 |
|---|---|---|
| 控制传输 Control | 带校验与重传，可靠性最高，带宽占用极低，ep0 专属 | 枚举、配置、状态查询 |
| 中断传输 Interrupt | 周期性轮询、低延迟、小数据 | 鼠标、键盘、触摸板、手柄 |
| 批量传输 Bulk | 无周期、大数据量、保证完整性但无实时性 | U 盘、移动硬盘、USB 网卡 |
| 同步传输 Isochronous | 周期、高实时、允许丢包、**无重传** | 摄像头、USB 声卡 |

所有数据收发都以 **URB（USB Request Block）** 为载体的封装：分配 → `usb_fill_*_urb` 初始化 → `usb_submit_urb` 提交 → 完成回调 → 重提或释放。

### 设备层级与匹配粒度

内核把设备拆成四层：`usb_device`（设备层）→ `usb_config_descriptor`（配置层，一个设备可有多套配置但只激活一套）→ `usb_interface`（接口层）→ `usb_endpoint_descriptor`（端点层）。

关键差异：**USB 驱动匹配的是接口，而非整个设备**——所以一个摄像头可以同时被"视频流驱动"和"麦克风驱动"两个驱动分别管理，这与 PCI 按设备函数匹配、platform 按 DTS 节点匹配都不同。^[inferred]

### 三层架构

| 层 | 职责 | 开发者是否接触 |
|---|---|---|
| HCD 层（主机控制器驱动） | 适配 OHCI/UHCI/EHCI/XHCI：寄存器、总线时序、DMA、中断 | 否，完全透明 |
| USB Core | 总线管理与**设备枚举**、拓扑维护、通用 API 与 URB 调度、驱动管理、热插拔 | 只调其 API |
| 设备驱动层 | 匹配、初始化、收发、释放 | 是 |

## 关键细节

### 核心结构体

| 结构体 | 关键字段 / 作用 |
|---|---|
| `usb_driver` | `name`、`probe(usb_interface*, usb_device_id*)`、`disconnect`、`id_table`、`suspend/resume`、`pre_reset/post_reset`、`supports_autosuspend` |
| `usb_device` | `devnum`(1~127)、`devpath[16]`、`parent`（上级 Hub）、`bus`、`ep0`、`ep_in[16]`/`ep_out[16]`、`descriptor`、`actconfig`、`bus_mA`、`level` |
| `usb_interface` | `altsetting` / `cur_altsetting`（当前生效的备选配置）、`num_altsetting`、`dev`、`usb_dev` |
| `usb_host_interface` | `desc`（接口描述符）+ `endpoint[]` 端点数组 + `extra` 扩展描述符——**probe 里解析资源的入口** |
| `usb_endpoint_descriptor` | `bEndpointAddress`（bit7=方向，低 4 位=端点号）、`bmAttributes`（传输类型）、`wMaxPacketSize`、`bInterval`（轮询间隔） |
| `usb_device_id` | `match_flags` 决定按什么匹配：VID/PID/固件版本，或设备级/接口级的 class-subclass-protocol |
| `urb` | `pipe`、`transfer_buffer`、`transfer_dma`、`transfer_buffer_length`、`actual_length`、`complete` 回调、`context`、`iso_frame_desc[]` |

### 常用 API

| 动作 | API |
|---|---|
| 注册/注销驱动 | `usb_register` / `usb_deregister` |
| URB 生命周期 | `usb_alloc_urb` → `usb_fill_int_urb`（或 bulk/control 版本）→ `usb_submit_urb(urb, mem_flags)` → `usb_kill_urb` / `usb_free_urb` |
| DMA 一致内存 | `usb_alloc_coherent` / `usb_free_coherent` |
| 管道构造 | `usb_rcvintpipe` / `usb_rcvbulkpipe` / `usb_sndbulkpipe`（主机视角：rcv=设备 IN） |
| 端点类型宏 | `USB_ENDPOINT_XFER_{CONTROL,ISOC,BULK,INT}` = 0x00/0x01/0x02/0x03 |

两条硬约束：**中断上下文提交 URB 必须用 `GFP_ATOMIC`**；**管道类型必须与端点实际传输类型一致**，中断端点用 int 系列、批量端点用 bulk 系列，混用直接提交失败。

### HID 引导协议（Boot Protocol）

嵌入式键鼠驱动走"引导协议"而非"报告协议"——报文长度与字段固定，不需要解析报告描述符。接口特征：Class=0x03（HID）、SubClass=0x01（Boot），只有一个 **中断输入端点**，无输出端点。默认轮询 10ms。

**键盘 8 字节报文**

| 偏移 | 含义 |
|---|---|
| Byte 0 | 修饰键位图：bit0~3 = 左 Ctrl/Shift/Alt/Win，bit4~7 = 右 Ctrl/Shift/Alt/Win |
| Byte 1 | 保留，固定 0x00 |
| Byte 2~7 | 普通键码数组，最多 6 键同按，0x00 = 空位，键码范围 0x00~0x73 |

- 例：只按 A（HID 键码 0x04）→ `[00, 00, 04, 00, 00, 00, 00, 00]`。
- **键盘不主动上报"释放"事件**：驱动必须比对前后两帧——新帧有旧帧无 = 按下，旧帧有新帧无 = 释放。这是 HID 键鼠驱动最容易踩的坑。
- 驱动侧还要把 HID 键码映射为内核键码（0x04 → `KEY_A`）再上报 input 子系统。

**鼠标 4 字节报文**：Byte0 按键位（bit0 左 / bit1 右 / bit2 中 / bit3 前进 / bit4 后退），Byte1 X、Byte2 Y、Byte3 滚轮，后三者均为有符号 int8（-127~+127）。**无绝对坐标**，光标位置由系统累加增量得出；单帧位移上限 ±127，快速移动会拆成多帧。

**URB 循环机制**：中断 URB 回调处理完必须**重新提交**，否则只能收到一次数据；传输出错要分致命/非致命，非致命自动重提恢复监听。

### 实验要点（RK356x）

- 8 字节 DMA 缓冲区长度与标准键鼠报告长度绑定，不可随意改，否则解析错乱。
- 系统自带 `hid-generic` 会先占用设备，实验驱动加载前必须屏蔽内置 HID 驱动。
- 卸载路径必须完整释放 URB、DMA 内存、input device，否则内存泄漏 + `/dev` 节点残留。

## 未解问题

- USB 3.x（xHCI）的 Streams 与 SuperSpeed 端点能力本来源未涉及，只讲到 USB 2.0 全速/高速口径。
- Gadget 侧（设备模式，SoC 作从机）完全没有覆盖——驱动架构页把 USB 描述为 "host/device/gadget 三层"，本页只讲 host 侧。
- `usb_device_id` 的 `match_flags` 位定义与"设备级 vs 接口级匹配"的优先级顺序未展开。
- 报告协议（Report Protocol）下报告描述符的解析流程缺源。

## 来源

- `raw/sources/Linux 操作系统/Linux 驱动管理/Linux USB 系统/Linux内核USB子系统.md` — 野火 RK356x 驱动教程第 5 章：USB 基础（拓扑/端点/管道/四种传输/设备层级）、三层架构、7 个核心结构体、13 组核心函数、端点类型宏、USB HID 键鼠协议与实验
