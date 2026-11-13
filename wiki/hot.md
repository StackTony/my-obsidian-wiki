---
title: Hot Cache
updated: 2026-11-12
---

# Hot Cache

*~500字的近期活动语义快照。每次重大写入操作后自动更新。*

## Recent Activity

- [2026-11-12] INGEST — Linux 驱动域 + 内存增量（6 新建 / 6 更新）：新建 [[summaries/linux-char-device-driver]]（dev_t 12+20 位、cdev_map `major%255`、五步注册、open→def_chr_fops→chrdev_open→replace_fops）、[[skills/linux-char-device-driver-template]]（六步可照抄骨架）、[[summaries/linux-system-bus]]（总线四维分类、带宽=频率×位宽/8、ISA→PCI→AGP→PCIe 演进）、[[skills/sre-interview-question-map]]（三份面试题覆盖地图）、[[summaries/linux-buddy-slab-allocator]]（阶/分裂合并/伙伴地址异或/SLAB 对象缓存）、[[summaries/linux-memory-reclaim-triggers]]（紧缺/kswapd/drop_caches 三入口）；更新 [[summaries/linux-pci-subsystem]]（BDF 8/5/3 位、ACPI 根节点→pci_scan_child_bus 递归枚举）、[[summaries/linux-interrupt-classification]]（典型例子速查表 + 10 种 softirq）、[[concepts/linux-memory-management]]（伙伴/SLAB 与回收两节）、[[concepts/linux-driver-model]]（字符设备小节）、[[concepts/linux-interrupt-system]]（源文件改名同步）、[[concepts/linux-io-stack]]（磁盘上报识别流程）。manifest 985→991，total_pages 206→212
- [2026-11-12] INGEST — 内存管理单来源 COW（9.5KB）：新建 [[summaries/linux-copy-on-write]]（fork 三代价、copy_page_range 三级复制、is_cow_mapping、handle_pte_fault 写保护分支、do_wp_page 四路分流、四步总结）与 [[concepts/copy-on-write]]（延迟复制不变量、判定速查、mmap/OverlayFS/零拷贝边界）；更新 [[concepts/virtual-memory-and-paging]]（写保护缺页小节）、[[concepts/linux-memory-management]]、[[summaries/linux-page-cache]]（私有文件映射）、[[concepts/overlayfs-container-images]]（copy-up 粒度对比）、[[concepts/zero-copy-memory-mapping]]（消除 vs 推迟复制）。manifest 984→985，total_pages 204→206
- [2026-11-11] INGEST — `Linux 操作系统` append 增量（11 非空新 / 11 空占位登记 / 10 仅格式变更 / 42 未变）：六个子系统手册（PCI 242KB、网络 231KB、SCSI 139KB、USB 95KB、块设备 54KB、DMA与IOMMU 52KB）蒸馏为 6 篇摘要 [[summaries/linux-pci-subsystem]] / [[summaries/linux-network-device-subsystem]] / [[summaries/linux-scsi-subsystem]] / [[summaries/linux-usb-subsystem]] / [[summaries/linux-block-subsystem]] / [[summaries/linux-dma-iommu-subsystem]]，加总纲 [[concepts/linux-driver-model]]；更新 [[concepts/linux-io-stack]]（blk-mq 双层队列、SCSI 中间层定位、fsync/fdatasync/sync）、[[concepts/linux-dma-mapping]]（三类 DMA 内存口径对齐、四步工作流、DMAC 六部件与总线握手）、[[concepts/linux-iommu-subsystem]]（iommu_domain/map/attach/flush API 面）、[[concepts/linux-network-stack]]（net_device 抽象层）、[[concepts/linux-io-models]]（三类 IO 各自动机）、[[concepts/linux-fs-mount]]（VFS 四大对象）；路径两次对齐（`设备驱动管理`→`驱动管理` 11 页、`Linux IOMMU` 迁入 `Linux 内核 IO 栈/` 10 页 + 8 键迁移）。manifest 964→984，total_pages 197→204
- [2026-11-11] WIKI_UPDATE — 项目枢纽页同步 3 个提交 delta；新增 [[skills/raw-source-link-sanitization]]（437 处追踪链接清洗流程）；记录 raw 目录按子系统重组与 18 个 manifest 键迁移
- [2026-11-11] INGEST — 设备驱动管理目录（1新+1修改+1重命名）：新建 [[summaries/linux-smmu-io-bypass]]（STE=Bypass 旁路、三模式对比、内核参数）；BAR 枚举流程并入 [[summaries/pci-bar-dma-space]]；SMMU图解文迁入 `Linux IOMMU/` 子目录
- [2026-11-10] INGEST — IOMMU/SMMU 图解单来源：新建 [[concepts/linux-iommu-subsystem]] / [[concepts/iommu-group-domain-isolation]] / [[concepts/vm-address-translation-chain]] + [[summaries/linux-iommu-smmu-illustrated]]
- [2026-11-10] INGEST — 目录重组增量（24新+9修改）：cpu-cache-coherence / memory-barriers / linux-io-models / page-cache-vs-buffer-cache / linux-dma-mapping 五概念页 + 2 摘要页
- [2026-11-10] 0 字节占位文件哈希碰撞（`e3b0c442...`）已解释并按独立新条目登记，非数据损坏

## Active Threads

- **驱动域骨架已闭环** ^[inferred]：驱动架构 + PCI/SCSI/Block/USB/网络设备/IOMMU 六个子系统手册 + DMA 技术 + 字符设备链路，共覆盖"LDM 总线模型 → 各类控制器 → 框架层结构体/API → 数据面通路"。字符设备补齐了 VFS→cdev→fops 这一环，见 [[summaries/linux-char-device-driver]]；上游总纲为 [[concepts/linux-driver-model]]，与 [[concepts/linux-io-stack]]、[[concepts/linux-interrupt-system]]、[[concepts/linux-dma-mapping]] 交叉成网
- **内存管理上下层已接通**：上层 meminfo/Page Cache/LRU 与下层分页/TLB 之间，本轮补入伙伴/SLAB 分配侧（[[summaries/linux-buddy-slab-allocator]]）与回收侧（[[summaries/linux-memory-reclaim-triggers]]），形成"分配→使用→回收"闭环；仍缺口：MMU、缺页异常、虚拟地址与物理地址三篇 0 字节源
- **raw 目录仍在被用户重组**（2026-11-11 全会话）：`Linux IOMMU/` 已从 `Linux 驱动管理/` 迁至 `Linux 内核 IO 栈/`，文件系统、内存、IO 栈三个目录陆续建/改名。ingest 前务必重新扫盘，不能沿用会话早期的路径快照
- **空占位补齐进度**：本轮补上 `Linux 系统总线`、`Linux PCIe设备枚举`、`Linux 伙伴分配器与 SLAB 分配器`、`Linux 内存回收机制` 四个原 0 字节/占位来源；当前仍有 12 个 0 字节 .md：内存管理（MMU / 缺页异常 / 虚拟地址和物理地址）、IO 栈（异步AIO libaio、io_uring / 用户态驱动IO SPDK、DPDK）、文件系统（ext4 / proc / sysfs）、网络（NAT协议）、AI（ACL访问控制 / Ollama）、数据结构（有向无环图）。0 字节文件 SHA-256 相同，不可作改名判据
- **子系统解析下一步缺口**：SCSI 的 ULD（sd/sr/st）与 LLD 具体驱动、Block 的 io_uring 直通路径（当前源仅讲 bio/blk-mq 与 libaio）、网络 NAPI 与 XDP 的分界、DTS 中断/clk/reset 属性全集
- **DMA/IOMMU 域双轴完备**：x86 轴（SWIOTLB 软件 bounce vs Intel VT-d 硬件 I/O 页表，互斥）+ ARM/框架轴（统一抽象层、Group/Domain 隔离、SVA、STE 级 bypass）
- **待人工审核**：几乎全库 `lifecycle: draft`；manifest 顶层 `vault_path` 仍为旧机器路径（`C:\Users\23363\Data\code\...`），实际在 `D:\lkj_Data\`——多次上报待老板决策；manifest 残留 2 条（`Linux 缓存IO和直接IO.md` 旧键、ClickHouse 源已删）

## Key Takeaways

- **字符设备 open 是"两段式"绑定**：inode 起初只挂通用 `def_chr_fops`，`chrdev_open()` 用 `inode->i_rdev` 在 `cdev_map`（`major % 255` 散列）中查出 `cdev`，`replace_fops()` 把 `file->f_op` 换成驱动 fops，再回调驱动 `open()`；设备号 `dev_t` 高 12 位主、低 20 位次，主号标识驱动、次号标识实例
- **系统总线带宽的口径**：带宽 = 频率 × 位宽 / 8（单沿），DDR 乘 2；PCI 32bit/33MHz≈133MB/s、AGP 8x≈2.1GB/s、PCIe 3.0 x16≈15.75GB/s（编码开销前）；ISA→PCI→AGP→PCIe 的演进主线是"并行共享 → 串行点对点"
- **BDF 是配置空间的全局地址**：Bus 8 位（0–255）、Device 5 位（0–31）、Function 3 位（0–7），每 Function 4KB 配置空间（前 256B 兼容 PCI）；枚举从 ACPI `PNP0A03` 根节点开始，`pci_scan_child_bus` 遍历 32 Device × 8 Function，遇桥再建子总线递归
- **物理内存是两级分配**：伙伴系统按 `2^n` 页管页框，分配向上取整后逐级分裂、释放用 `伙伴地址 = 块地址 ^ (1 << (order+12))` 找伙伴递归合并；SLAB 从伙伴取整页切固定对象（`kmem_cache_alloc`），前者治外部碎片、后者治内部碎片
- **内存回收只有两个执行器**：`shrink_zone` 收页框（消费 LRU/PTE 访问位）、`shrink_slab` 收可回收对象；三条入口分别是分配慢路径同步回收、kswapd 后台周期性回收、`drop_caches` 用户手动回收，回收失败才进 OOM
- **COW 的开关是 PTE 保护位**：fork 只复制页表、把私有可写页在父子两侧置只读，写保护缺页才复制；`do_wp_page` 先判是否真共享（`reuse_swap_page` 且 `total_mapcount==1` 则 `wp_page_reuse` 直接复用）。**粒度决定代价**：页级 COW 复制 4KB，OverlayFS copy-up 复制整个文件（100MB 首次写慢 263 倍）
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
