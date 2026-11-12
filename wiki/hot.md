---
title: Hot Cache
updated: 2026-11-11
---

# Hot Cache

*~500字的近期活动语义快照。每次重大写入操作后自动更新。*

## Recent Activity

- [2026-11-11] INGEST — `Linux 操作系统` append 增量（11 非空新 / 11 空占位登记 / 10 仅格式变更 / 42 未变）：六个子系统手册（PCI 242KB、网络 231KB、SCSI 139KB、USB 95KB、块设备 54KB、DMA与IOMMU 52KB）蒸馏为 6 篇摘要 [[summaries/linux-pci-subsystem]] / [[summaries/linux-network-device-subsystem]] / [[summaries/linux-scsi-subsystem]] / [[summaries/linux-usb-subsystem]] / [[summaries/linux-block-subsystem]] / [[summaries/linux-dma-iommu-subsystem]]，加总纲 [[concepts/linux-driver-model]]；更新 [[concepts/linux-io-stack]]（blk-mq 双层队列、SCSI 中间层定位、fsync/fdatasync/sync）、[[concepts/linux-dma-mapping]]（三类 DMA 内存口径对齐、四步工作流、DMAC 六部件与总线握手）、[[concepts/linux-iommu-subsystem]]（iommu_domain/map/attach/flush API 面）、[[concepts/linux-network-stack]]（net_device 抽象层）、[[concepts/linux-io-models]]（三类 IO 各自动机）、[[concepts/linux-fs-mount]]（VFS 四大对象）；路径两次对齐（`设备驱动管理`→`驱动管理` 11 页、`Linux IOMMU` 迁入 `Linux 内核 IO 栈/` 10 页 + 8 键迁移）。manifest 964→984，total_pages 197→204
- [2026-11-11] WIKI_UPDATE — 项目枢纽页同步 3 个提交 delta；新增 [[skills/raw-source-link-sanitization]]（437 处追踪链接清洗流程）；记录 raw 目录按子系统重组与 18 个 manifest 键迁移
- [2026-11-11] INGEST — 设备驱动管理目录（1新+1修改+1重命名）：新建 [[summaries/linux-smmu-io-bypass]]（STE=Bypass 旁路、三模式对比、内核参数）；BAR 枚举流程并入 [[summaries/pci-bar-dma-space]]；SMMU图解文迁入 `Linux IOMMU/` 子目录
- [2026-11-10] INGEST — IOMMU/SMMU 图解单来源：新建 [[concepts/linux-iommu-subsystem]] / [[concepts/iommu-group-domain-isolation]] / [[concepts/vm-address-translation-chain]] + [[summaries/linux-iommu-smmu-illustrated]]
- [2026-11-10] INGEST — 目录重组增量（24新+9修改）：cpu-cache-coherence / memory-barriers / linux-io-models / page-cache-vs-buffer-cache / linux-dma-mapping 五概念页 + 2 摘要页
- [2026-11-10] 0 字节占位文件哈希碰撞（`e3b0c442...`）已解释并按独立新条目登记，非数据损坏

## Active Threads

- **驱动域骨架已闭环** ^[inferred]：驱动架构 + PCI/SCSI/Block/USB/网络设备/IOMMU 六个子系统手册 + DMA 技术，共覆盖"LDM 总线模型 → 各类控制器 → 框架层结构体/API → 数据面通路"。上游总纲为 [[concepts/linux-driver-model]]，与 [[concepts/linux-io-stack]]、[[concepts/linux-interrupt-system]]、[[concepts/linux-dma-mapping]] 交叉成网
- **raw 目录仍在被用户重组**（2026-11-11 全会话）：`Linux IOMMU/` 已从 `Linux 驱动管理/` 迁至 `Linux 内核 IO 栈/`，文件系统、内存、IO 栈三个目录陆续建/改名。ingest 前务必重新扫盘，不能沿用会话早期的路径快照
- **剩余空占位 11 个（0 字节）**：内存管理（伙伴分配器 / 缺页异常 / 虚拟地址和物理地址 / 页回收机制 / MMU / 页面置换算法）、IO 栈（异步AIO libaio、io_uring / 用户态驱动IO SPDK、DPDK）、文件系统（ext4 / proc / sysfs）、网络（NAT协议）、驱动管理（系统总线总览 / PCIe设备枚举）。补内容后再 ingest；0 字节文件 SHA-256 相同，不可作改名判据
- **子系统解析下一步缺口**：SCSI 的 ULD（sd/sr/st）与 LLD 具体驱动、Block 的 io_uring 直通路径（当前源仅讲 bio/blk-mq 与 libaio）、网络 NAPI 与 XDP 的分界、DTS 中断/clk/reset 属性全集
- **DMA/IOMMU 域双轴完备**：x86 轴（SWIOTLB 软件 bounce vs Intel VT-d 硬件 I/O 页表，互斥）+ ARM/框架轴（统一抽象层、Group/Domain 隔离、SVA、STE 级 bypass）
- **待人工审核**：几乎全库 `lifecycle: draft`；manifest 顶层 `vault_path` 仍为旧机器路径（`C:\Users\23363\Data\code\...`），实际在 `D:\lkj_Data\`——多次上报待老板决策；manifest 残留 2 条（`Linux 缓存IO和直接IO.md` 旧键、ClickHouse 源已删）

## Key Takeaways

- **内核所有设备子系统都是"框架层 + 驱动实现层"同构** ^[inferred]：PCI 是 pci_driver+pci_ops、SCSI 是 host_template+scsi_host、Block 是 blk_mq_ops.queue_rq、网络是 net_device_ops、IOMMU 是 iommu_ops——注册回调、框架统一调度
- **blk-mq 是双层队列**：软件队列 `mq_ctx`（每 CPU 一份，避免锁争用）+ 硬件队列 `hw_ctx`（对应设备队列），`blk_mq_tag_set` 分配 tag、`blk_mq_ops.queue_rq` 是驱动唯一必填回调，完成走 `blk_mq_end_request`
- **SCSI 三层是"协议栈式"抽象**：较高层（sd/sr/st，懂块语义）→ 中间层（把 bio/request 翻成 CDB）→ 较低层（HBA 驱动发命令），CDB 长度决定命令族（6/10/16 字节，opcode 0x28 READ10 / 0x2A WRITE10 / 0x25 READ CAPACITY）
- **网络收包是"中断 + 轮询"混合**：硬中断只唤醒 NAPI，`napi_struct` 在软中断上下文按 budget 轮询收包，兼顾低延迟与高吞吐；`sk_buff` 用 head/data/tail/end 四个指针在单块 buffer 内做各层头部的增删
- **USB 驱动匹配的是接口而非设备**：`usb_interface` 才是绑定单元，所以一个复合设备可被多个驱动分治；数据面统一走 URB（分配→fill→submit→回调→重提），HID 键盘不主动报释放，必须比对前后两帧差分判定
- **IOMMU API 四步**：`iommu_domain_alloc` → `iommu_map` → `iommu_attach_device`（映射才对设备生效）→ 解绑释放；改完映射必须 `iommu_flush_iotlb_all`
- **驱动域的三类设备模型**：PCI（内存读写式，靠 BAR+MMIO）/ 字符设备（流式字节）/ 块设备（按扇区随机寻址，走 bio→request→blk-mq），三者驱动写法完全不同但共享 LDM 的 bus-device-driver 与 sysfs/devtmpfs/udev 基础设施
- **MESI 四态演进都在解 Invalid 延迟** ^[inferred]：MESIF 加 F 态（唯一转发者）、MOESI 加 O 态（脏数据直接转发免写回）
- **内存屏障两层根源**：编译器重排（`barrier()`）与 CPU 乱序（体系结构屏障）；x86-TSO 只允许 StoreLoad 重排，故 x86 全屏障=StoreLoad 屏障
- **IOMMU 本质是 DMA 地址翻译环节**：无 IOMMU 时 32-bit 设备够不到高地址→SWIOTLB 用预留 bounce 池 memcpy 中转；Intel VT-d 用 I/O 页表做硬件重映射后 DMA 地址=IOVA
- **IO Bypass≠关闭 SMMU**：SMMU 上电即工作，把设备对应 STE 配成 Bypass 才令该 SID 直通 PA（不经 S1/S2、不查 IOTLB 与页表权限）；BIOS 关闭才是硬件不工作
- **BAR 大小是探测出来的**：向 BAR 写全 1 再读回，最低非零位定 2^n，按对齐分配后基址写入高位
- **Group 是隔离粒度、Domain 是地址空间粒度**：同 group 设备共享 domain 页表，必须整体直通同一 VM

## Flagged Contradictions

- **DMA 内存分类：教材三类 vs x86 两类** ^[ambiguous]：野火教材分一致性/流式/散射聚集，x86 资料分 Coherent/Streaming（SG 是 Streaming 的 `dma_map_sg` 变体）——已在 [[concepts/linux-dma-mapping]] 并列对照标注
- **Deadline 调度器读 FIFO 超时 500ms vs 5ms** ^[ambiguous]：不同来源数值相差 100 倍，两处并存标注
- **sendfile 提升 50% 吞吐** ^[ambiguous]：源文自述"未亲测"，仅作量级参考
- **Page Cache 组织结构 radix tree vs xarray** ^[ambiguous]：内核版本口径差异（4.x 起 xarray 替代 radix tree）
