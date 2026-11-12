---
title: "SMMU IO Bypass：SMMU开启时的翻译旁路"
category: summaries
tags: [linux, SMMU, IOMMU, ARM, DMA]
aliases: [IO Bypass, SMMU Bypass, STE Bypass, iommu.passthrough, smmu.bypassdev]
relationships:
  - target: "[[concepts/linux-iommu-subsystem]]"
    type: extends
  - target: "[[concepts/iommu-group-domain-isolation]]"
    type: related_to
  - target: "[[concepts/linux-dma-mapping]]"
    type: related_to
  - target: "[[skills/swiotlb-troubleshooting]]"
    type: related_to
source_dir: Linux 操作系统/Linux 内核 IO 栈/Linux IOMMU
source_files: [Linux SMMU的IO Bypass.md]
summary: SMMU上电即工作；把设备对应STE配成Bypass，该SID的DMA即直通物理地址，不经S1/S2翻译、不查IOTLB、不做页表权限检查。含三模式对比与iommu.passthrough/smmu.bypassdev/disable_bypass参数。
provenance:
  extracted: 0.80
  inferred: 0.15
  ambiguous: 0.05
base_confidence: 0.44
lifecycle: draft
lifecycle_changed: 2026-11-11
tier: supporting
created: 2026-11-11
updated: 2026-11-11
---

# SMMU IO Bypass：SMMU开启时的翻译旁路

一条短笔记，澄清一个常见误解：**IO Bypass 不是"关闭 SMMU"**，而是 SMMU 照常工作时，为特定设备单独配置的一条"跳过翻译流水线"的通道。它是 [[concepts/linux-iommu-subsystem]] 中 ARM SMMU 部分的机制补充，也是排查"SMMU 明明开着、设备却在用物理地址"这类现象的关键。

## 核心观点

- **SMMU 的功能**：替设备将 DMA 请求的地址翻译成设备真正能用的物理地址。
- **IO Bypass 的功能**：在开启 SMMU 的情况下，通过配置参数让某些硬件不使用 SMMU 的地址翻译——硬件层面 SMMU 能力开启，OS 层面进行控制，设备直接使用物理地址做 DMA。
- **机制（一句话）**：SMMU 硬件本身上电即开启、正常工作；只是把该设备对应的 **STE（Stream Table Entry）配置成 Bypass 模式**：该 SID 的 DMA 流量直接透传，**不经过 Stage1/Stage2 地址翻译、不做 IOTLB 查找、不做页表权限检查**。
- **与"BIOS 关掉 SMMU"的本质区别**：
  - BIOS 关掉 SMMU = **整个 SMMU 硬件不工作**；
  - SMMU 开启时再开 IO Bypass = **硬件还在跑，只是这一路设备不走翻译流水线**。

旁路发生在 STE 层，而不是取消设备的 SID（BDF）标记——硬件仍凭 BDF 定位到 STE，只是那条 STE 指向"直通"。 ^[inferred] 这与 [[concepts/iommu-group-domain-isolation]] 中"BDF 是每设备 DMA 请求的唯一标记"的前提一致。

## 关键细节

### 内核配置参数（鲲鹏 / ARM）

| 参数 | 作用 |
|------|------|
| `iommu.passthrough=1` | **全局默认 bypass**，所有设备不走 SMMU 翻译 |
| `smmu.bypassdev=BDF` | **只对指定 PCI 设备 BDF 开启 bypass**，其他设备继续 SMMU 翻译（最常用） |
| `disable_bypass` | 关闭 bypass 能力，**强制所有 SID 必须走翻译** |

### 三模式对比

| 模式 | SMMU 硬件 | STE 配置 | 设备 DMA 地址 |
|------|-----------|----------|---------------|
| SMMU 正常翻译 | 开启 | 正常 S1/S2 | IOVA（内核维护映射） |
| SMMU 开启 + IO Bypass | 开启 | STE=Bypass | PA（直接透传） |
| BIOS 关闭 SMMU | 关闭 | 不存在 STE | PA，内核走 SWIOTLB |

### 与相邻概念的关系

- **IOVA 与 PA**：正常翻译模式下设备看到的是 IOVA，由内核维护 IOVA→PA 映射（见 [[concepts/linux-dma-mapping]]）；bypass 模式下设备直接拿到 PA，IOVA 这一层被整体跳过。
- **SWIOTLB 兜底**：BIOS 关闭 SMMU 时设备只能用 PA，32 位设备够不到高内存，于是内核退化为 SWIOTLB 的 bounce 拷贝；而 SMMU+bypass 是**硬件旁路**，不产生拷贝。两种情形"地址看起来都是 PA"，但性能和故障表现完全不同，排查方法见 [[skills/swiotlb-troubleshooting]]。
- **安全含义**：Bypass 跳过页表权限检查，被旁路的设备可访问任意物理地址——只在信任该设备或追求性能时使用，安全敏感场景应选 `disable_bypass`。 ^[inferred]

## 未解问题

- 被旁路的设备若是 32 位寻址且要访问 4GB 以上内存，内核是否仍需 SWIOTLB 兜底？本来源未说明。 ^[inferred]
- `smmu.bypassdev` 传入多个设备时的写法与匹配粒度（BDF 列表？RID？），以及 `disable_bypass` 在 arm-smmu 与 arm-smmu-v3 驱动中的实际参数名差异？
- SMMUv3 的 STE 中 Bypass 的具体位域编码，本来源未展开。

## 来源

- `raw/sources/Linux 操作系统/Linux 内核 IO 栈/Linux IOMMU/Linux SMMU的IO Bypass.md` — STE Bypass 机制、BIOS 关闭与 bypass 的区别、内核参数（iommu.passthrough / smmu.bypassdev / disable_bypass）、三模式对比
