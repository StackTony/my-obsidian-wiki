---
title: Hot Cache
updated: 2026-11-11
---

# Hot Cache

*~500字的近期活动语义快照。每次重大写入操作后自动更新。*

## Recent Activity

- [2026-11-11] INGEST — 设备驱动管理目录增量（1新+1修改+1重命名）：新建 [[summaries/linux-smmu-io-bypass]]（STE=Bypass 旁路、三模式对比、内核参数）；BAR 枚举流程并入 [[summaries/pci-bar-dma-space]]；[[concepts/linux-iommu-subsystem]] 增 SMMU IO Bypass 小节、[[skills/swiotlb-troubleshooting]] 增三模式辨析；SMMU图解文迁入 `Linux IOMMU/` 子目录并同步 7 页路径。manifest 963→964，total_pages 180→181
- [2026-11-10] INGEST — Linux IOMMU、SMMU(ARM)技术图解（单来源）：新建 linux-iommu-subsystem（内核IOMMU抽象层+SMMU+SVA）/ iommu-group-domain-isolation（Group/Domain+VFIO+BDF）/ vm-address-translation-chain（GVA/GPA/HVA/HPA+EPT）3概念页 + linux-iommu-smmu-illustrated 摘要页；更新直通页（解决VFIO group/container未解问题）、DMA映射页（scatter-gather聚合）、IOMMU六部曲页（补抽象层引言）。manifest 962→963，total_pages 176→180
- [2026-11-10] INGEST — Linux 操作系统目录重组增量（24新+9修改+2重命名+5空占位）：新建 cpu-cache-coherence / memory-barriers / linux-io-models / page-cache-vs-buffer-cache / linux-dma-mapping 5个概念页 + pci-bar-dma-space / linux-iommu-deep-dive 2个摘要页；更新30页（含 meminfo 全量重写、io-stack hub 重写、锁机制10→13种）。manifest 940→962，total_pages 176
- [2026-11-09] CAPTURE — swiotlb buffer is full 排查沉淀为 [[skills/swiotlb-troubleshooting]]；[2026-11-09] INGEST — 中断系统目录重蒸馏（2新页面+hub更新）；[2026-11-06] INGEST — 物理硬件域首批10来源→15新页面
- [2026-11-10] 用户核实的delta异常：5个空占位文件哈希与3个不相关旧条目（Ollma/有向无环图/ACL）相同——系0字节文件SHA-256(e3b0c442...)必然碰撞，非数据损坏，已解释并按独立新条目登记

## Active Threads

- **下一批待消化**：BAR空间资源映射.md 已消化（BAR探测分配流程并入 [[summaries/pci-bar-dma-space]]）；SMMU的IO Bypass.md 已消化（新页 linux-smmu-io-bypass）；剩余4个0字节占位（Linux MMU / 页表 / PCIe设备枚举 / DMA传输）仍待填充，与 [[concepts/virtual-memory-and-paging]] 天然成对
- **DMA/IOMMU域成型（双轴完备）** ^[inferred]：x86轴=IOMMU六部曲（SWIOTLB软件bounce vs Intel VT-d硬件I/O页表，互斥）+ DMA映射两类 + swiotlb排查skill；ARM/框架轴=SMMU图解（内核统一抽象层、Group/Domain隔离、VFIO Group/Container、[[concepts/vm-address-translation-chain]] GPA/HVA/HPA地址链）+ [[summaries/linux-smmu-io-bypass]]（STE级旁路与三模式）；[[concepts/linux-device-passthrough]] 的VFIO group/container未解问题已闭环。剩余缺口：SMMUv3命令队列/event queue细节、STE位域编码、SVA实现、IRT中断重映射（多页未解问题待源）
- **缓存一致性与内存序线开启**：cpu-cache-coherence（MESI/MESIF/MOESI）与 memory-barriers（Store Buffer/x86-TSO）为本批新建，向上衔接 [[concepts/linux-lock-mechanisms]]（锁的内存序语义）、向下支撑 dma_wmb 等DMA一致性屏障
- **中断知识线已闭环**（2026-11-09）：hub [[concepts/linux-interrupt-system]] 为中断域唯一枢纽，与VGIC/IRQ亲和/TLB Shootdown完成交叉链接
- **历史遗留待用户决策**：manifest顶层vault_path过期旧路径；lint报告provenance漂移72页、提升候选36页（linux-io-stack 18入链为头号）

## Key Takeaways

- **MESI四态的演进方向都是解决Invalid延迟** ^[inferred]：MESIF加F态（转发者唯一，省共享读总线流量）、MOESI加O态（脏数据可直接转发免写回）；伪共享=多核频繁争用同一cache line不同字段，靠`__cacheline_aligned`对齐规避
- **内存屏障的两层根源**：编译器重排（barrier()即可）与CPU乱序（需体系结构屏障）；x86-TSO只允许StoreLoad重排，故x86全屏障=StoreLoad屏障；弱序架构（ARM）需读/写/全屏障精细控制
- **epoll O(1)的核心是就绪链表**：红黑树存监听fd（增删O(logN)）、事件到达时callback摘入rdllist就绪链表，epoll_wait只扫就绪链表而非全量fd——与select/poll每次线性扫描的本质差异
- **Page Cache与Buffer Cache在2.4统一**：此前双重缓存（文件走PC、块设备走BC）浪费内存；统一后buffer_head的b_page指向PC页，BC降为PC的块映射子集（日志文件系统仍需buffer_head）
- **IOMMU本质是DMA地址翻译环节**：无IOMMU时32-bit设备够不到高地址→SWIOTLB用启动预留bounce池memcpy中转（x86_64默认64MB）；Intel VT-d用I/O页表做硬件重映射后DMA地址=IOVA；两者互斥，VT-d初始化完成后释放SWIOTLB buffer
- **DMA映射两类选型**：Coherent（一致性映射，长期持有，硬件自动cache同步，适合小控制块）vs Streaming（流式，map/unmap配对，可用IOMMU映射分散物理页，可触发SWIOTLB bounce）
- **锁全景扩至13种**：qspinlock（MCS队列化自旋，解决锁争用cache line乒乓）、WW Mutex（死锁免疫，GPU/DMA预约场景）、Tasks RCU（以自愿上下文切换为宽限期边界，服务BPF trampoline）
- **Group是隔离粒度、Domain是地址空间粒度**：同group设备共享domain页表PGD，必须整体直通同一VM（拆分即DMA攻击面）；PCIe-PCI桥为下游设备生成共享Source Identifier（device/func=0）→被迫同组；早期PCI仲裁独占总线、DMA请求无BDF，硬件上做不到设备级隔离
- **透传一致性=两条翻译路径殊途同归**：GPA经EPT→HPA1、经IOMMU→HPA2，HPA1==HPA2透通才成立；VMM把HVA作vaddr传VFIO_IOMMU_MAP_DMA保证相等。细节：虚机页表存于HPA但CR3/表项装GPA，遍历页表本身也要经EPT
- **Linux IOMMU是"框架+驱动"抽象**：DMA-MAP API→IOVA(RCACHE)→IO页表→SMMU/IOMMU驱动回调→VFIO接口五层，屏蔽Intel VT-d/AMD/ARM SMMU三种硬件；SVA（CPU与设备共享页表）是统一地址空间的延伸方向
- **IO Bypass≠关闭SMMU**：SMMU上电即工作，把设备对应STE配成Bypass即令该SID的DMA直通PA（不经S1/S2、不查IOTLB、不查页表权限）；BIOS关闭才是整个硬件不工作。三模式（正常翻译IOVA / bypass直通PA / BIOS关闭PA+SWIOTLB）是排查"设备为何在用物理地址"的第一分叉，且bypass不解决32位设备够不到高内存——bounce仍可能发生 ^[inferred]
- **BAR大小是探测出来的**：向BAR写全1再读回，最低非零位定2^n大小，按对齐分配后基址写入高位；BAR在设备端，多个BAR可并存，低位只读兼表大小与类型

## Flagged Contradictions

- **Deadline调度器读FIFO超时 500ms vs 5ms** ^[ambiguous]：不同来源数值不一致（相差100倍），两处并存标注；write超时5ms各源一致
- **sendfile提升50%吞吐** ^[ambiguous]：源文自述"未亲测"，仅作参考量级；零拷贝收益依赖SG-DMA硬件支持
- **Page Cache组织结构 radix tree vs xarray** ^[ambiguous]：不同内核版本口径（4.x起xarray替代radix tree），摘要页并存标注
- **Mutex owner编码**（已修正）：低2位为标志位而非低3位——锁机制页原记录有误，本批按全景介绍源文修正；mutex/semaphore性能倍数亦修正（6x/8x）
- **swiotlb关键数字已闭环**（原标^[ambiguous]现获文档级佐证）：64MB默认池/2KB单slot/128 slots区间，base_confidence 0.55→0.58
