---
title: 光模块（Optical Transceiver）
category: entities
tags: [硬件, 光模块, 光纤, SFP, 光电转换]
aliases: [光模块, Optical Transceiver, 光收发一体模块]
relationships:
  - target: "[[concepts/linux-network-stack]]"
    type: related_to
  - target: "[[synthesis/hardware-layer-debugging-landscape]]"
    type: related_to
source_dir: 物理硬件/光模块
source_files: [光模块简介.md]
summary: 光模块是完成电↔光双向转换的可插拔器件：TOSA(发射)/ROSA(接收)/BOSA(单纤双向集成)三大光电器件+PIN/APD探测器+TIA/CDR功能电路，SFP封装经金手指接设备、LC/SC/MPO接光纤。
provenance:
  extracted: 0.80
  inferred: 0.17
  ambiguous: 0.03
base_confidence: 0.44
lifecycle: draft
lifecycle_changed: 2026-11-06
tier: supporting
created: 2026-11-06
updated: 2026-11-06
---

# 光模块（Optical Transceiver）

光模块是光纤通信系统中的核心可插拔器件，核心功能是完成"光电"与"电光"的转换——连接电子设备和光纤网络的"翻译官"：发送端把交换机/路由器/服务器的电信号转成光信号经光纤传输；接收端把光信号还原成电信号供设备处理。在网络协议栈中位于 [[concepts/linux-network-stack]] 最底层之下的物理传输器件。

## 关键属性

### 三大光电器件

| 器件 | 全称 | 组成 | 职责 |
|------|------|------|------|
| TOSA | 光发射组件 | 激光器、透镜、监控PD等 | 电→光转换 |
| ROSA | 光接收组件 | 探测器(PIN/APD)、透镜等 | 光→电转换 |
| BOSA | 双向光组件 | TOSA+ROSA集成 | 单纤双向(BiDi)模块用 |

- 一个模块不会同时包含TOSA、ROSA、BOSA：**双纤模块用TOSA+ROSA，单纤模块用BOSA**。
- **监控PD**：本质是光电二极管，把激光器背面发出的微弱光信号转成光电流，实时监控激光器发光功率，供驱动电路做自动功率控制。

### PIN vs APD 探测器

| 探测器 | 特点 | 增益 | 适用场景 |
|--------|------|------|----------|
| PIN | 正-本征-负型光电二极管；结构简单、响应快、工作电压低 | 无内部增益(一个光子→一个电子-空穴对) | 短距离、信号较强 |
| APD | 雪崩光电二极管；结构复杂、需较高工作电压 | 高压下雪崩效应放大光生电流(一个光子激发多个电子) | 长距离、信号衰减严重 |

### 功能电路与接口

- 功能电路：驱动电路、TIA(跨阻放大器，光生电流μA~mA级→电压信号)、CDR(时钟数据恢复：从失真信号中提取时钟、重定时、判决再生，25G+模块必备)、MCU控制、DDM监控。
- 电接口：金手指(如SFP的20-pin)连接设备主板；光接口：光纤连接器(LC/SC/MPO)连接光纤。
- 激光器选型：短距多模用850nm VCSEL(垂直腔面发射激光器)；长距单模用1310/1550nm DFB/EML(分布反馈/电吸收调制激光器)。

### 封装与外围(SFP为例)

防尘帽(保护光接口)、裙片(SFP特有，保证与设备光接口良好搭接)、标签(关键参数与厂家)、接头(与单板连接，传信号+供电)、外壳(SFP/QSFP等)、拉环(插拔用，**不同波段对应不同拉环颜色**)；辅助元件：TEC半导体制冷片(精确控温稳定激光器波长)、隔离器(阻止光反射回激光器)、滤波片(分离不同波长，如BOSA双通滤波)、透镜(提高光耦合效率)。结构设计：金属屏蔽壳防EMI、导热结构(激光器/芯片→外壳)、气密封装(防潮防尘防氧化)、金线键合(芯片↔PCB，影响信号完整性)。

### 工作原理（双纤模块）

**发送方向(电→光)**：设备输出高速差分电信号→金手指入模块→驱动IC放大(高速模块启用预加重补偿高频损耗)→电信号驱动激光器(VCSEL或DFB/EML)发光→透镜准直+隔离器防反射→耦合至光纤。

**接收方向(光→电)**：光纤光经透镜聚焦到探测器(PIN短距/APD长距)→光生电流(μA~mA级)→TIA转为电压信号→CDR重定时判决再生(对抗抖动/色散)+均衡器EQ补偿信道损耗(DFE/FFE)→清洁电信号经金手指返回主机。

## 与其他实体的关系

- 与交换机/网卡：光模块是 [[concepts/linux-network-stack]] 物理层之下的最终传输载体——网络排障时"链路Down"需下钻到光模块层面(发光功率、DDM监控)定位。 ^[inferred]
- 在硬件层调试全景中的位置见 [[synthesis/hardware-layer-debugging-landscape]]。

## 来源

- raw/sources/物理硬件/光模块/光模块简介.md（掘金）
