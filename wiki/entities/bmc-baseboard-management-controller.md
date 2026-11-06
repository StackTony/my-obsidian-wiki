---
title: BMC（Baseboard Management Controller）
category: entities
tags: [硬件, BMC, IPMI, 带外管理, 服务器]
aliases: [BMC, Baseboard Management Controller, 基板管理控制器]
relationships:
  - target: "[[skills/ipmi-sol-remote-console]]"
    type: related_to
  - target: "[[synthesis/hardware-layer-debugging-landscape]]"
    type: related_to
source_dir: 物理硬件/串口
source_files: [BMC介绍.md, "IPMI的SOL (Serial Over LAN)原理与使用.md"]
summary: BMC是服务器主板上独立于主机CPU/OS的带外管理微控制器：远程管理、电源控制、传感器监控；IPMI/SOL/KVM-over-IP/SNMP/Redfish五大管理接口，与BIOS经IPMI或SMBus通信。
provenance:
  extracted: 0.72
  inferred: 0.23
  ambiguous: 0.05
base_confidence: 0.61
lifecycle: draft
lifecycle_changed: 2026-11-06
tier: supporting
created: 2026-11-06
updated: 2026-11-06
---

# BMC（Baseboard Management Controller）

BMC是专门用于监控和管理计算机硬件的微控制器，负责远程管理、电源控制、传感器监控等功能。它与BIOS分工明确：BIOS是系统启动时的硬件初始化与操作系统加载固件，BMC是常驻的带外管理器；两者通信可经IPMI或SMBus(System Management Bus)实现。

## 关键属性

### 五大管理接口

| 接口 | 性质 | 说明 |
|------|------|------|
| IPMI | 开放标准硬件管理协议 | 定义BMC与系统管理软件间的通信接口；BMC经Ethernet接入网络，管理软件通过IPMI命令远程监控硬件状态、重启服务器、诊断问题 |
| SOL (Serial over LAN) | IPMI v2.0功能 | 串口重定向：BMC充当串口服务器，把串口输入输出流转发给管理软件，远程访问BIOS设置界面与OS命令行 |
| KVM-over-IP | 远程图形技术 | 将服务器图形输出转换为网络数据包传输，实现键盘/视频/鼠标的远程图形控制 |
| SNMP | 常用网络管理协议 | 监控网络设备；部分BMC支持，可获取硬件信息、修改配置参数 |
| Redfish | 新一代开放标准 | 基于RESTful API与JSON；新款服务器BMC支持，可远程获取硬件状态、修改BIOS设置、执行远程操作 |

### SOL的转发机制

BMC把OS或BIOS的串口输出转换为IPMI约定的协议，通过SMBus发送到LAN控制器，局域网内的其他机器用IPMI即可收到目标服务器串口数据并交互——即远程通过串口操控OS或BIOS。单个远程控制台应用可在统一界面下同时提供IPMI平台管理与串口文本重定向，SOL的访问权限管理与IPMI共用同一用户配置界面。BMC与BIOS通信路径及SOL实操见 [[skills/ipmi-sol-remote-console]]。

### 使用SOL的前提

- BMC支持IPMI v2.0（SOL是v2.0功能）
- BMC设置中启用IPMI over LAN，且用户具有IPMI over LAN访问权限
- UEFI中配置串口控制台重定向，串口参数与ipmitool侧一致

## 与其他实体的关系

- BMC独立于主机CPU与OS运行——OS挂死时仍可经BMC观测与操控，这构成软件栈(perf/crash)之外的**带外观察平面**，定位见 [[synthesis/hardware-layer-debugging-landscape]]。 ^[inferred]
- 与管理工具的关系：ipmitool是BMC最常见的命令行客户端（`-I lanplus`接口走IPMI v2.0/RMCP+），见 [[summaries/ipmi-sol-usage]]。

## 来源

- raw/sources/物理硬件/串口/BMC介绍.md
- raw/sources/物理硬件/串口/IPMI的SOL (Serial Over LAN)原理与使用.md
