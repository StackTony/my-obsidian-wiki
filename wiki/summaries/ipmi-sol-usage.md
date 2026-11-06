---
title: IPMI的SOL (Serial Over LAN)原理与使用
category: summaries
tags: [硬件, IPMI, SOL, 串口, 远程管理]
aliases: [SOL原理与使用, Serial over LAN, IPMI SOL]
source_dir: 物理硬件/串口
source_files: [IPMI的SOL (Serial Over LAN)原理与使用.md]
summary: SOL重定向本地异步串行控制器数据到LAN：BMC把OS/BIOS串口输出转成IPMI协议经SMBus送LAN控制器，远程经IPMI LAN会话操控OS或BIOS；含Linux/ESXi控制台重定向配置与ipmitool用法。
provenance:
  extracted: 0.80
  inferred: 0.15
  ambiguous: 0.05
base_confidence: 0.44
lifecycle: draft
lifecycle_changed: 2026-11-06
tier: supporting
created: 2026-11-06
updated: 2026-11-06
---

# IPMI的SOL (Serial Over LAN)原理与使用

SOL是IPMI v2.0的功能，提供在局域网上对某台机器串口的远程访问——重定向本地异步串行控制器接口的数据到远端，建立一个虚拟的远程串行终端，用远程软件即可通过串口远程操作机器的操作系统或管理服务。配置实操整理为 [[skills/ipmi-sol-remote-console]]，BMC实体见 [[entities/bmc-baseboard-management-controller]]。

## 核心观点

- **原理**：BMC将OS或BIOS的串口输出转换成IPMI约定的协议，通过SMBus发送到LAN控制器；局域网中其他机器用IPMI接收到目标服务器串口数据并交互——远程通过串口操控OS或BIOS。
- SOL可用于操作系统和操作系统前的异步串行通信；适用于OS命令行、串行重定向的BIOS接口、IPMI LAN会话上的串行文本应用等场景，可执行任何不需要GUI的任务。
- 单个远程控制台应用可在统一用户界面下同时提供局域网访问IPMI平台管理和串口文本重定向；SOL访问权限管理与IPMI共用同一用户配置界面——简化了配置软件与跨平台工具的创建。
- **使用前提**：目标服务器BMC支持IPMI v2.0、启用IPMI over LAN且用户有权限；UEFI中配置串口控制台重定向且参数与ipmitool一致；OS中将console重定向到串口。远程侧推荐ipmitool v1.8.18+。
- Linux配置三件套：grub的`GRUB_CMDLINE_LINUX`末尾加`console=tty0 console=ttyS0,115200`；`GRUB_TERMINAL="serial"`；`GRUB_SERIAL_COMMAND="serial --speed=115200 --unit=0 --word=8 --parity=no --stop=1"`；然后grub2-mkconfig重新生成配置(UEFI与Legacy输出路径不同)。
- ESXi配置：启动时Shift+O编辑boot options，追加`gdbPort=none logPort=none tty2Port=com1`(一次性)；持久化需用CLI命令设置。
- 连接命令：`ipmitool -C 17 -I lanplus -H <BMC IP> -U <user> -P <pwd> sol activate`；断开`sol deactivate`；查看配置`sol info`。连接建立后重启服务器即可在远端看到启动信息。
- **RMCP+会话建立失败三因**：BMC密码错误 / IPMI over LAN端口未开启 / BMC用户无使用权限。

## 未解问题

- ESXi持久化配置的CLI命令原文缺失(文中代码块为空"~~~")，需查VMware官方文档补全。 ^[ambiguous]
- `-C 17`密码套件的含义(RMCP+ AES-17?)未解释。 ^[inferred]

## 来源

- raw/sources/物理硬件/串口/IPMI的SOL (Serial Over LAN)原理与使用.md（CSDN）
