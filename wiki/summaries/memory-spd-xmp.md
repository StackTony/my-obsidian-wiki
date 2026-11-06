---
title: 内存频率SPD、XMP
category: summaries
tags: [硬件, 内存, SPD, XMP, DDR]
aliases: [SPD与XMP, 内存频率, XMP超频]
source_dir: 物理硬件/内存
source_files: [内存频率SPD、XMP.md]
summary: SPD是内存条上8针EEPROM芯片，出厂写入厂商/频率/电压/时序/容量等参数，POST阶段BIOS读取后自动配置内存控制器；XMP是Intel的官方一键超频预设(写入SPD特定区域)。
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

# 内存频率SPD、XMP

SPD与XMP的入门摘要。与ECC纠错整合后的概念页见 [[concepts/memory-spd-xmp-ecc]]。

## 核心观点

- **SPD(Serial Presence Detect，串行存在检测)**：内存条上一颗8针EEPROM芯片，记录内存的芯片及模组厂商、工作频率、工作电压、速度、容量、电压与行/列地址带宽等参数——出厂前由模组制造商根据内存芯片实际性能写入。
- **SPD的作用**：开机POST自检阶段，主板BIOS读取SPD信息，北桥芯片组据此自动配置内存工作时序与控制寄存器，充分发挥内存条性能；前提是BIOS中内存设置选"By SPD"。检测不到SPD时只能给保守配置。
- SPD是识别内存品牌的重要标志；SPD参数设置不合理反而引起系统不稳定甚至死机——普通/兼容内存厂商为避免兼容性问题把参数设保守，限制了性能发挥。
- **XMP(Extreme Memory Profile)**：Intel 2007年推出的官方一键超频技术，DDR4上广泛使用XMP 2.0版(Intel制定并认证)。原理简单：每条XMP认证内存在SPD特定区域保存超频数据(一般有XMP1和XMP2)，可理解为内存的预设配置文件。
- 未开XMP时内存跑官方基础默认频率(DDR5 4800MHz、DDR4 2133/2666MHz)；BIOS开启后系统自动把频率、电压、时序(CL延迟)调整到厂家标称的最佳高性能状态。
- SPD本质是"设备向配置者声明自身能力"的自描述机制——BIOS无需硬编码每种内存的参数，即插即用的根源。 ^[inferred]

## 未解问题

- JEDEC标准时序与XMP预设的关系(为什么标称高频必须走XMP而非默认)未展开——与内存控制器训练机制的关联需补充来源。 ^[inferred]

## 来源

- raw/sources/物理硬件/内存/内存频率SPD、XMP.md
