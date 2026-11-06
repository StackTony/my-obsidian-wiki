---
title: IPMI SOL远程串口控制台配置实操
category: skills
tags: [硬件, IPMI, SOL, 串口, 远程运维]
aliases: [SOL配置实操, ipmitool sol, 串口远程控制台]
relationships:
  - target: "[[entities/bmc-baseboard-management-controller]]"
    type: uses
source_dir: 物理硬件/串口
source_files: [IPMI的SOL (Serial Over LAN)原理与使用.md]
summary: SOL远程串口控制台五步配置：BMC启用IPMI over LAN与用户权限→UEFI串口重定向→Linux grub/ESXi控制台重定向到串口→ipmitool sol activate连接→RMCP+会话失败三因排查。
provenance:
  extracted: 0.82
  inferred: 0.13
  ambiguous: 0.05
base_confidence: 0.44
lifecycle: draft
lifecycle_changed: 2026-11-06
tier: supporting
created: 2026-11-06
updated: 2026-11-06
---

# IPMI SOL远程串口控制台配置实操

通过SOL(Serial over LAN)从任何地方远程查看服务器基于文本的控制台并执行无需GUI的任务——包括BIOS设置界面与OS命令行。原理：BMC把串口数据流转成IPMI协议经LAN转发，见 [[entities/bmc-baseboard-management-controller]] 与 [[summaries/ipmi-sol-usage]]。

## 前置条件

- 目标服务器BMC支持 **IPMI v2.0**（SOL是v2.0功能）
- 远程电脑安装 **ipmitool v1.8.18+**（v1.6.0+已支持IPMI v2.0）且与BMC同一局域网
- 记住三处串口参数必须一致：UEFI串口设置 = OS console参数 = ipmitool侧

## 步骤

### 1. BMC侧：启用IPMI over LAN并确认用户权限

BMC Web管理界面：`BMC Configuration → Network → IPMI over LAN` 启用；再到 `BMC Configuration → User/LDAP` 编辑用户，勾选 **IPMI over LAN** 访问权限。（不同品牌路径不同）

### 2. UEFI侧：配置串口控制台重定向

进入BIOS：`系统设置 → 设备和I/O端口 → 控制台重定向设置`，对SOL绑定的COM口(如COM1)开启重定向，记录串口参数（推荐通用默认：115200 8N1，与后续ipmitool/grub保持一致）。

### 3. OS侧(Linux)：console重定向到串口

编辑 `/etc/default/grub`：

```
GRUB_CMDLINE_LINUX="... console=tty0 console=ttyS0,115200"
GRUB_TERMINAL="serial"
GRUB_SERIAL_COMMAND="serial --speed=115200 --unit=0 --word=8 --parity=no --stop=1"
```

生成配置：

```bash
# UEFI mode:
grub2-mkconfig -o /boot/efi/EFI/redhat/grub.cfg
# Legacy mode:
grub2-mkconfig -o /boot/grub2/grub.cfg
```

### 4. OS侧(ESXi)：重定向直接控制台

启动出现加载窗口时按 **Shift+O** 编辑boot options，追加：

```
gdbPort=none logPort=none tty2Port=com1
```

（一次性生效；后续启动的持久化设置需用ESXi CLI命令，原文命令块缺失，查官方文档补全 ^[ambiguous]）

### 5. 远程连接SOL

```bash
ipmitool -C 17 -I lanplus -H <BMC IP> -U ADMIN -P ADMIN sol activate
# 例：ipmitool -C 17 -I lanplus -H 10.10.10.10 -U ADMIN -P ADMIN sol activate
```

连接建立后重启服务器，远端即可看到完整启动信息并交互。

| 功能 | 命令 |
|------|------|
| 查看SOL配置 | `ipmitool sol info [1]` |
| 建立连接 | `ipmitool -C 17 -I lanplus -U <user> -P <pwd> -H <ip> sol activate` |
| 断开连接 | `ipmitool -C 17 -I lanplus -U <user> -P <pwd> -H <ip> sol deactivate` |

## 常见问题

| 报错/现象 | 原因 | 解决 |
|-----------|------|------|
| `Error: Unable to establish IPMI v2 / RMCP+ session` | ① BMC密码错误 ② IPMI over LAN端口未开启 ③ BMC用户无使用权限 | 依次核对BMC Web界面的网络设置与用户权限 |
| 连接后无输出 | UEFI/OS未做console重定向，或串口参数不一致 | 核对步骤2/3/4，三处参数必须一致 |
| ESXi重启后重定向失效 | Shift+O方式仅一次性 | 用ESXi CLI持久化设置 |

## 来源

- [[summaries/ipmi-sol-usage]] — 来源文章蒸馏
- [[entities/bmc-baseboard-management-controller]] — BMC实体页
