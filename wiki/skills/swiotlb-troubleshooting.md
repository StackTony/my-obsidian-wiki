---
title: swiotlb buffer is full 排查实操手册
category: skills
tags: [linux, kernel, DMA, swiotlb, 调试]
aliases: [swiotlb排查, swiotlb buffer full, DMA bounce排查]
relationships:
  - target: "[[concepts/linux-device-passthrough]]"
    type: related_to
  - target: "[[concepts/linux-virtio-architecture]]"
    type: related_to
  - target: "[[summaries/linux-iommu-deep-dive]]"
    type: derived_from
  - target: "[[concepts/linux-dma-mapping]]"
    type: related_to
  - target: "[[summaries/linux-smmu-io-bypass]]"
    type: related_to
source_dir: Linux 操作系统/Linux 内存管理
source_files:
  - Linux meminfo参数详细解释.md
  - Linux 操作系统/Linux 设备驱动管理/Linux IOMMU/Linux x86-64 IOMMU详解（2）——SWIOTLB（软件IOMMU）.md
  - Linux 操作系统/Linux 设备驱动管理/Linux IOMMU/Linux x86-64 IOMMU详解（5）——Intel IOMMU初始化流程_noiommu.md
  - Linux 操作系统/Linux 设备驱动管理/Linux IOMMU/Linux SMMU的IO Bypass.md
sources:
  - conversation:2026-11-09
summary: 无IOMMU环境swiotlb buffer is full四步排查：dmesg确认池大小→slots统计分流根因（泄漏/单映射超限/容量不足）→定位guest或宿主机与设备→修复矩阵：扩池/q35机型/驱动升级/dma_debug查泄漏/max_sectors_kb限请求。
provenance:
  extracted: 0.68
  inferred: 0.22
  ambiguous: 0.10
base_confidence: 0.58
lifecycle: draft
lifecycle_changed: 2026-11-09
tier: supporting
created: 2026-11-09
updated: 2026-11-11
---

# swiotlb buffer is full 排查实操手册

不开 IOMMU 的现网环境报 `swiotlb buffer is full` 时，本质是：设备 DMA 寻址能力不足（典型 32-bit，只能到 4GB 以下）而目标缓冲区在设备够不到的物理地址，内核退化为在 swiotlb（Software I/O TLB，一块启动时预留的连续低地址内存池）里做 bounce 拷贝，池耗尽即 `dma_map` 失败——**这是 IO 故障不是性能告警**，请求会直接报错。排查思路：先定位（报错在哪、池多小、什么在占），再按根因分流修复。

## 前置条件

- root 权限；可改内核 cmdline（GRUB）并重启——经典 swiotlb 池大小启动即定，改参必须重启
- 理解 bounce buffering 概念：老设备只能访问低端内存，内核在低端分配临时 buffer 中转，见 `raw/sources/Linux 操作系统/Linux 内存管理/Linux meminfo参数详细解释.md` 的 Bounce 字段一节；文档级原理佐证见[[summaries/linux-iommu-deep-dive]]（SWIOTLB用memblock从低地址预留连续物理内存，默认64MB，按2KB粒度切分为slab，io_tlb_list数组管理连续空闲slab，IO_TLB_SEGSIZE=128限制单次映射≤256KB）；IOMMU 的 DMA 地址翻译角色见 [[concepts/linux-device-passthrough]]
- 先确认环境形态：物理机 / KVM 宿主机 / KVM guest / Hyper-V / Xen——修复路径完全不同

## 步骤

### 1. 确认池现状

```bash
cat /proc/cmdline               # 是否已有 swiotlb= 参数
dmesg | grep -i swiotlb         # boot 打印实际大小："software IO TLB: mapped [mem ...] (64MB)"
```

x86_64 默认 64MB（IO_TLB_DEFAULT_SIZE），slab粒度2KB（IO_TLB_SHIFT=11），每段上限128 slab（IO_TLB_SEGSIZE，由x86 PCIe规范每次DMA有效数据≤128字节决定），单次映射≤256KB——文档级佐证见[[summaries/linux-iommu-deep-dive]]。不同架构/内核版本默认值与槽位大小有差异，一律以 dmesg 打印为准。^[ambiguous]

### 2. 解读报错自带的统计

较新内核的完整报错自带三元组，直接用它分流根因（老内核报 `DMA: Out of SW-IOMMU space for N bytes`，无 slots 统计，只能靠趋势判断）：

```
swiotlb buffer is full (sz: N bytes), total N (slots), used N (slots)
```

| 形态 | 根因判断 |
|------|----------|
| used==total，空闲时段也不回落 | **映射泄漏**——驱动 map 后没 unmap，扩池只是延寿 |
| sz 很大（256KB 量级以上） | **单映射超限**——超过池单段上限（x86_64：128槽×2KB），池没满也会报 ^[ambiguous] |
| 高负载上涨、负载回落后回落 | **容量不足**——并发在途 bounce 总量超池，直接扩池 |

### 3. 定位报错位置与设备

- 报错出现在 **guest 还是宿主机** dmesg——KVM 环境两者都可能，修复路径不同
- 报错本身不含设备名，但通常紧随驱动错误日志或栈回溯出现，结合上下文定位；无上下文时用 bpftrace 按进程计数：

```bash
bpftrace -e 'kprobe:swiotlb_tbl_map_single { @[comm] = count(); }'
```

（追踪工具链见 [[concepts/linux-tracing-frameworks]]）

### 4. 按根因查环境

```bash
# KVM guest：查机型——i440fx 的 virtio 设备是 32-bit DMA，
# guest 内存 >4GB 时全部 virtio IO 走 guest swiotlb
virsh dumpxml <vm> | grep machine    # pc(i440fx-*) = 重灾区；pc-q35 = 64-bit

# 物理机：完整回看 swiotlb 相关日志（含 fallback 提示），
# 结合报错上下文的设备核对 lspci -nn 确认是否老网卡/HBA/RAID 卡
dmesg | grep -i swiotlb
```

## 常见问题（修复矩阵）

| 根因 | 方案 | 说明与代价 |
|------|------|-----------|
| 容量不足 | cmdline 加 `swiotlb=524288`（单位 KiB=512MB；按并发 IO 量取 256MB–1GB），重启后 dmesg 验证 | 最直接规避；启动即预留、实打实吃内存。**单位在不同内核版本历史上有差异，改后必须 dmesg 复核** ^[ambiguous] |
| KVM guest + i440fx 机型 | 换 **q35** 机型，或 libvirt≥5.1 用 `virtio-non-transitional` 设备模型 | 根治——设备变 64-bit DMA 后不再 bounce；换机型需关机，q35↔i440fx 不能直接热迁移（[[summaries/linux-live-migration-flow]]） |
| 物理机 32-bit DMA 设备 | 换/升级 64-bit DMA（DAC）设备或驱动 | 部分老驱动初始化固定 32-bit mask，升级驱动即好 |
| 愿意开 IOMMU | IOMMU 全翻译模式：IOVA 分配在设备可达范围，无需 bounce | **陷阱：`iommu=pt` 直通模式下问题依旧**（身份映射不解决寻址）——见 [[concepts/linux-device-passthrough]] |
| 单映射超限 | `echo 128 > /sys/block/<dev>/queue/max_sectors_kb` 限制单请求 | 限制在单段上限内规避；见 [[concepts/linux-io-stack]] |
| 映射泄漏 | `dma_debug=on`（需 CONFIG_DMA_API_DEBUG）+ 读 `/sys/kernel/debug/dma-api/errors` | 找到泄漏驱动后修复驱动才是根治，扩池只是延寿 |
| 长期 | 升级内核：较新主线内核（≈6.8+）有 CONFIG_SWIOTLB_DYNAMIC 动态扩池 | 版本号与能力以所用内核文档为准 ^[ambiguous] |

其他平台：**Hyper-V storvsc guest** 与 **Xen Dom0（xen-swiotlb）** 是此报错另外两个高发场景，思路同为扩池 + 限制 IO 深度。^[inferred]

## 进阶用法

- **泄漏 vs 容量的鉴别**：用报错行的 used slots 做趋势监控（周期抓 dmesg），只增不减即泄漏；泄漏场景下扩池只是延长故障间隔，最终要靠 dma_debug 定位驱动 bug
- **槽位与架构**：x86_64 槽位 2KB（IO_TLB_SHIFT=11）、每段 128 槽（IO_TLB_SEGSIZE）；ARM64 64K 页内核槽位不同，单段上限随之变化——跨架构现网不能照搬 x86 数字。文档级佐证：IO_TLB_SEGSIZE=128由x86 PCIe规范（每次DMA有效数据≤128字节）确定，见[[summaries/linux-iommu-deep-dive]] ^[ambiguous]
- **池的内存代价**：swiotlb 从启动早期 memblock 分配器预留（`memblock_alloc_low` 强制低地址），扩到 1GB 意味着业务可用内存直接少 1GB；扩池值应基于实测的峰值在途 bounce 量而非拍脑袋 ^[inferred]
- **Coherent Mapping不走swiotlb**：Linux 4.0+ 仅 DMA Streaming Mapping 触发 SWIOTLB，DMA Coherent Mapping 与之无关——排查时若报错伴随大buffer分配，方向应转向 coherent 内存不足而非 swiotlb 池。见[[concepts/linux-dma-mapping]] ^[inferred]
- **Intel IOMMU启用后swiotlb会被释放**：`intel_iommu_init()` 将 `swiotlb=0` 后 `swiotlb_exit()` 释放整个池——启用IOMMU的环境本不应出现swiotlb buffer full，若出现需检查IOMMU是否真正生效（`dmesg | grep DMAR`）或设备走了identity mapping旁路。见[[summaries/linux-iommu-deep-dive]] ^[inferred]
- **先分清三种模式再动手**：①正常翻译（设备见 IOVA，内核维护映射）②SMMU 开启 + 该设备 STE=Bypass（设备直接用 PA，硬件直通、不产生拷贝）③BIOS 关闭 SMMU（设备用 PA，内核走 SWIOTLB bounce）。修复矩阵里"`iommu=pt` 直通模式问题依旧"正是②的近亲——**旁路不解决 32 位设备够不到高内存**，设备 dma_mask 不够时内核仍会走 bounce。ARM 平台对应参数为 `iommu.passthrough=1` / `smmu.bypassdev=<BDF>` / `disable_bypass`。见[[summaries/linux-smmu-io-bypass]] ^[inferred]
- **Bounce 字段可作为压力观测指标**：`/proc/meminfo` 的 Bounce 字段反映 bounce 池占用的低端内存大小，纳入周期监控可提前发现 swiotlb 压力趋势（字段详解见 [[summaries/linux-meminfo-params]]）
- **DMA 与 CPU 缓存一致性**：设备 DMA 绕过 CPU cache 直接访问内存，CPU 写入的数据可能仍在 Store Buffer/Cache 中未刷回——内核用 `dma_wmb()` 等屏障原语保证数据对设备可见，屏障语义见 [[concepts/memory-barriers]]、[[concepts/cpu-cache-coherence]] ^[inferred]

## 来源

- conversation:2026-11-09 — 现网"不使用 IOMMU + swiotlb buffer is full"排查咨询（LLM 领域知识综合，版本相关细节已作存疑标注）
- `raw/sources/Linux 操作系统/Linux 内存管理/Linux meminfo参数详细解释.md` — Bounce 字段一节（bounce buffering 概念与内核内存统计公式）
- `raw/sources/Linux 操作系统/Linux 设备驱动管理/Linux IOMMU/Linux x86-64 IOMMU详解（2）——SWIOTLB（软件IOMMU）.md` — 文档级佐证：SWIOTLB Buffer默认64MB、slab粒度2KB、IO_TLB_SEGSIZE=128、io_tlb_list管理结构、map函数三种行为、swiotlb_bounce→memcpy
- `raw/sources/Linux 操作系统/Linux 设备驱动管理/Linux IOMMU/Linux x86-64 IOMMU详解（5）——Intel IOMMU初始化流程_noiommu.md` — 文档级佐证：物理内存>4GB触发SWIOTLB初始化、Intel IOMMU初始化后swiotlb=0、swiotlb_exit释放池
- `raw/sources/Linux 操作系统/Linux 设备驱动管理/Linux IOMMU/Linux SMMU的IO Bypass.md` — 三种模式对比（正常翻译 / STE=Bypass 直通 / BIOS 关闭走 SWIOTLB）、bypass 内核参数
- [[summaries/linux-iommu-deep-dive]] — IOMMU六部曲系列摘要（SWIOTLB原理+Intel VT-d初始化竞争时序）
- [[concepts/linux-dma-mapping]] — DMA Coherent vs Streaming映射类型、IOVA/IOMMU页表
- [[concepts/linux-device-passthrough]] — IOMMU 的 DMA 翻译与隔离
- [[concepts/linux-virtio-architecture]] — virtio 设备模型（q35/non-transitional 方案的机制背景）
- [[skills/virsh-vm-management]] — virsh 查询机型等实操命令
