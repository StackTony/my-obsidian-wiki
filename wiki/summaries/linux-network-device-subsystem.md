---
title: Linux 网络设备子系统（网卡驱动视角）
category: summaries
tags: [linux, 网络, 网卡驱动, NAPI, sk_buff]
aliases: [网络设备子系统, net_device, 网卡驱动框架, NAPI 实现]
relationships:
  - target: "[[concepts/linux-network-stack]]"
    type: extends
  - target: "[[concepts/linux-driver-model]]"
    type: implements
  - target: "[[summaries/linux-pci-subsystem]]"
    type: related_to
  - target: "[[concepts/linux-interrupt-system]]"
    type: uses
source_dir: Linux 操作系统/Linux 驱动管理/Linux 网络设备 系统
source_files: [Linux内核网络子系统.md]
summary: 网卡驱动视角的网络子系统：net_device/net_device_ops/napi_struct 设备抽象层、sk_buff 与 sk_buff_head 的内存布局、NAPI 中断+轮询 API 组（netif_napi_add/schedule/complete）、MAC-PHY 分层与 DTS 解析。
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

# Linux 网络设备子系统（网卡驱动视角）

野火 RK356x 驱动教程第 9 章的蒸馏。与 [[concepts/linux-network-stack]]（协议视角：四层模型、三张表、TCP 状态机）互补——本页关心的是**驱动的另一侧**：数据包怎么从硬件进到 `sk_buff`，又怎么交给协议栈。

## 概述

网络设备是三大设备类型里唯一**没有设备文件、不走 VFS** 的一类：用户态用 socket，驱动用 `net_device` + `net_device_ops`，收包靠 NAPI 而不是逐包中断。这三点决定了网卡驱动的结构与字符/块设备驱动完全不同。

## 核心观点

- **四层架构，两侧解耦**：用户态接口层（socket/sysfs/ethtool/ip）→ 内核协议栈层（TCP/UDP/IP/ARP/路由/流控）→ 网络设备抽象层（`net_device`、`net_device_ops`、NAPI、skb 队列、统计）→ 硬件适配驱动层（物理网卡或纯软件的虚拟网卡）。
- **NAPI 是"中断触发 + 轮询收包"的混合模式**：空闲时靠硬中断唤醒，繁忙时关中断、批量轮询队列，处理完再开中断；`budget` 限制单次轮询包数，避免 CPU 被网络独占。
- **收包路径的锚点是 `netif_receive_skb`**：驱动把 skb 交给协议栈的唯一入口；发包路径则是协议栈调 `ndo_start_xmit`。
- **sk_buff 的内存布局就是性能设计**：`head/data/tail/end` 四个指针让各层协议头通过移动 `data` 指针"加头/去头"，不拷贝数据；`transport_header/network_header/mac_header` 记录各层偏移。
- **MAC 与 PHY 分层**：MAC 控制器驱动处理 DMA 环与寄存器，PHY 驱动处理链路协商；两者由设备树描述，平台胶水层（如瑞芯微）负责把它们接起来。

## 关键细节

### 协议与帧格式要点

| 项 | 要点 |
|---|---|
| TCP/IP 四层 | 应用 / 传输 / 网络 / 网络接口；Linux 实现更接近四层，但跨层耦合更多 |
| 以太网 II 帧 | 目的 MAC(6) + 源 MAC(6) + 类型(2) + 载荷(46~1500) + FCS(4) |
| 类型值 | 0x0800 IPv4、0x0806 ARP、0x86DD IPv6、0x8035 RARP |
| 字节序 | 网络序为大端，x86/ARM 为小端，协议栈组装/解析必须 `htons/ntohs` 转换 |
| ARP | 32 位 IP ↔ 48 位 MAC；请求广播、应答单播，结果进 ARP 缓存 |
| IPv4 | 无连接不可靠，负责编址/路由/分片重组；转发修改后必须重算首部校验和 |
| ICMP | 无端口，ping/traceroute 的基础；内核自动组应答 |
| TCP / UDP | 面向连接可靠 vs 无连接低开销；头部字段差异见原文章节 |

### 核心结构体

- `sk_buff` — 全系统统一的包描述：链表 `next/prev/dev`、`len/data_len/mac_len/hdr_len`、`pkt_type`（单播/广播/组播/回环）、`ip_summed`（硬件/软件/免校验）、`protocol`、三层头偏移、`head/data/tail/end`、`truesize`、`users` 引用计数。
- `sk_buff_head` — skb 双向链表头，前两个成员与 sk_buff 对齐，便于统一遍历；`qlen` + `lock`。
- `net_device` — 所有网卡（物理/虚拟/lo）的统一抽象：名称、MAC、MTU、链路状态、`netdev_ops`、特性、统计。
- `net_device_ops` — `ndo_start_xmit` 等硬件操作回调集。
- `napi_struct` — NAPI 实例：轮询回调、budget、状态。
- `netdev_stats` / `ethtool_ops` — 统计与调试配置回调。

### 驱动 API 分组

| 阶段 | 函数 |
|---|---|
| 分配/释放 | `alloc_netdev`、`alloc_etherdev`、`free_netdev`、`netdev_priv` |
| 注册/注销 | `register_netdev` / `unregister_netdev` |
| 以太网初始化 | `ether_setup`、`eth_hw_addr_random` |
| 队列控制 | `netif_start_queue` / `netif_stop_queue` |
| 链路状态 | `netif_carrier_on` / `netif_carrier_off` |
| NAPI | `netif_napi_add` / `netif_napi_del`、`napi_enable/disable`、`napi_schedule`、`napi_complete_done` |
| 收包交栈 | `netif_receive_skb`、`eth_type_trans` |
| skb 队列 | `skb_queue_head/tail`、`skb_dequeue`、`skb_queue_purge`、`kfree_skb` |

### MAC-PHY 与设备树

设备树声明 MAC 控制器节点（寄存器、中断、时钟、PHY 句柄、`phy-mode`）与 PHY 节点（地址、ID）；平台胶水层解析 DTS 后注册 `net_device`，MAC 核心层负责 DMA 环收发与 NAPI 调度，PHY 驱动负责链路协商（自协商、速率、双工）。虚拟网卡回环实验（纯软件 `net_device` + `ndo_start_xmit` 回灌）验证了这套抽象的最小闭环。^[inferred]

## 未解问题

- GRO/GSO/TSO 等软硬件卸载机制未覆盖，只提到 `ip_summed` 的校验和状态。
- XDP 与 `ndo_bpf` 路径未涉及。
- 多队列（`netif_set_real_num_tx_queues`）与 RSS 的配合未展开。
- MAC 驱动的 DMA 环细节被压缩在源码解析章节，本页只保留结论。

## 来源

- `raw/sources/Linux 操作系统/Linux 驱动管理/Linux 网络设备 系统/Linux内核网络子系统.md` — 野火 RK356x 驱动教程第 9 章：网络基础与协议格式、NAPI、四层架构、核心结构体与函数、瑞芯微 MAC/PHY 驱动解析、虚拟网卡回环实验
- 交叉：[[concepts/linux-network-stack]]（协议栈视角）、[[concepts/linux-interrupt-system]]（中断下半部与 NAPI 的关系）
