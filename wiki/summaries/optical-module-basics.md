---
title: 光模块简介
category: summaries
tags: [硬件, 光模块, 光纤, SFP, 光电转换]
aliases: [光模块入门, 光模块学习笔记]
source_dir: 物理硬件/光模块
source_files: [光模块简介.md]
summary: 光模块入门基础：核心功能电↔光双向转换；TOSA/ROSA/BOSA三大器件、PIN与APD探测器对比、TIA/CDR功能电路、SFP封装结构、发送/接收两个方向的完整信号链。
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

# 光模块简介

光模块入门学习笔记的蒸馏。实体知识沉淀于 [[entities/optical-transceiver-module]]。

## 核心观点

- 光模块是光纤通信系统的核心可插拔器件，本质是高速光电转换设备："翻译官"——发送端电→光，接收端光→电。
- 核心元器件：TOSA(含激光器/透镜/监控PD，电→光)；ROSA(含PIN/APD探测器/透镜，光→电)；BOSA(TOSA+ROSA集成方案，用于单纤双向BiDi模块；双纤用TOSA+ROSA)。
- 监控PD是光电二极管，将激光器背面微弱光电信号转为光电流，实时监控发光功率供自动功率控制。
- PIN探测器：结构简单、响应快、工作电压低、无内部增益——适合短距离强信号；APD雪崩探测器：高压雪崩增益、可探极微弱光——适合长距离衰减严重的场景。
- 功能电路：驱动电路、TIA(跨阻放大器)、CDR(时钟数据恢复，从失真信号提取时钟+重定时+判决再生，25G+必备)、MCU控制、DDM监控。
- 电接口金手指(SFP 20-pin)，光接口LC/SC/MPO连接器；激光器短距多模用850nm VCSEL，长距单模用1310/1550nm DFB/EML。
- SFP封装外围：防尘帽、裙片(SFP特有)、标签、接头、外壳、收发接口、拉环(不同波段不同颜色)。
- 辅助元件：TEC半导体制冷(稳定激光器波长)、隔离器(防光反射损坏激光器)、滤波片(分离波长)、透镜(提高耦合效率)、光纤阵列(多通道对准)。
- 结构与封装：金属屏蔽壳防EMI、导热路径(激光器→外壳)、气密封装、金线键合。
- 发送链：高速差分电信号→驱动IC放大(预加重)→激光器→透镜准直+隔离器→光纤。接收链：透镜聚焦→PIN/APD→光生电流→TIA转电压→CDR重定时+EQ均衡→金手指输出。

## 未解问题

- DDM(数字诊断监控)的具体参数(温度/发光功率/接收光功率/偏置电流)与告警阈值未展开——这是光模块排障最实用的部分，需补充来源。 ^[inferred]
- 光模块速率等级(1G/10G/25G/100G)与封装(SFP/SFP28/QSFP28/QSFP-DD)的对应关系未覆盖。 ^[inferred]

## 来源

- raw/sources/物理硬件/光模块/光模块简介.md（掘金）
