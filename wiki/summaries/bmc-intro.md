---
title: BMC介绍
category: summaries
tags: [硬件, BMC, IPMI, 带外管理, 服务器]
aliases: [BMC简介, BMC与BIOS]
source_dir: 物理硬件/串口
source_files: [BMC介绍.md]
summary: BMC基础概念：主板上的带外管理微控制器，与BIOS经IPMI或SMBus通信；IPMI/SOL/KVM-over-IP/SNMP/Redfish五大管理接口一览，各自定位与用途。
provenance:
  extracted: 0.85
  inferred: 0.12
  ambiguous: 0.03
base_confidence: 0.44
lifecycle: draft
lifecycle_changed: 2026-11-06
tier: supporting
created: 2026-11-06
updated: 2026-11-06
---

# BMC介绍

BMC(Baseboard Management Controller)与BIOS分工的入门介绍 + 五大管理接口一览。实体知识沉淀于 [[entities/bmc-baseboard-management-controller]]，SOL深入使用见 [[summaries/ipmi-sol-usage]]。

## 核心观点

- BMC是专门用于监控和管理计算机硬件的微控制器，负责远程管理、电源控制、传感器监控等功能；BIOS则负责系统启动时的硬件初始化与操作系统加载。某些系统中两者需要通信以实现部分功能。
- BMC与BIOS的通信路径：IPMI(Intelligent Platform Management Interface)或SMBus(System Management Bus)。
- IPMI是开放标准的硬件管理协议，定义服务器BMC与系统管理软件之间的通信接口——通过网络远程管理服务器（监控硬件状态、重启、诊断）。BMC通过Ethernet接口连接到服务器网络。
- SOL(Serial-over-LAN)：通过串口将BMC与远程控制台连接，远程访问BIOS设置界面和OS命令行；BMC充当串口服务器转发串口输入输出流。
- KVM-over-IP：将服务器图形输出转换为网络数据包传输，实现键盘/视频/鼠标的远程图形控制。
- SNMP：常用网络管理协议，部分BMC支持，可监控和控制BMC（获取硬件信息、修改配置参数）。
- Redfish：新一代开放标准硬件管理协议，基于RESTful API和JSON；新款服务器BMC支持，可远程管理（硬件状态、BIOS设置、远程操作）。
- 协议演进脉络：IPMI(1998-era命令式) → SNMP(通用网管) → Redfish(RESTful+JSON)，管理接口正在向Web化迁移。 ^[inferred]

## 未解问题

- 文章为概览级：各协议的报文格式、BMC与BIOS经SMBus通信的具体内容均未展开，SOL细节由 [[summaries/ipmi-sol-usage]] 补充。

## 来源

- raw/sources/物理硬件/串口/BMC介绍.md（CSDN）
