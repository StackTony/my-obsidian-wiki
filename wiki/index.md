---
title: Wiki Index
updated: 2026-11-11
---

# Wiki Index

*自动维护。上次更新：2026-11-11 (WIKI_UPDATE：项目枢纽页同步 3 个提交 delta，新增 raw 源追踪链接清洗技能页)*

## Summaries (数据结构与算法)

- [binary-tree-basics](summaries/binary-tree-basics.md) — 二叉树核心概念、三种形态、五个性质、四种遍历、链式/顺序存储与高频面试题原文摘要 — `数据结构` `二叉树` `遍历` `BST`
- [red-black-tree-detail](summaries/red-black-tree-detail.md) — 红黑树五大性质、与4阶B树等价、12种插入情况、5类删除修复、AVL vs红黑树完整对比原文摘要 — `数据结构` `红黑树` `AVL` `平衡树`
- [avl-redblack-btree-intro](summaries/avl-redblack-btree-intro.md) — BST→AVL→红黑树→B/B+树演进路线、各树特性对比、B+树更适合数据库索引的两大原因 — `数据结构` `AVL` `红黑树` `B树` `B+树`
- [graph-algorithms-overview](summaries/graph-algorithms-overview.md) — 图论算法学习路线全景图：BFS/DFS→并查集→最短路→拓扑→MST→强连通→二分图→网络流 — `数据结构` `图论` `BFS` `DFS` `最短路`

## Summaries (Linux)

- [linux-softirq-detail](summaries/linux-softirq-detail.md) — Linux软中断完整实现：注册与raise触发、__do_softirq预算控制、ksoftirqd兜底、tasklet串行保证与临界区保护选择 — `linux` `kernel` `softirq` `interrupt` `ksoftirqd`
- [linux-fs-mount-process](summaries/linux-fs-mount-process.md) — mount系统调用逐函数分析：mountpoint/mount/vfsmount三结构体、do_mount五分支、vfs_kern_mount+do_add_mount两步挂载 — `linux` `内核` `mount` `VFS` `文件系统`
- [linux-meminfo-params](summaries/linux-meminfo-params.md) — /proc/meminfo 40+字段全景：MemAvailable三因子估算、内存黑洞、LRU五类、HugePages与THP、Slab/SReclaimable、Bounce/SwapCached语义 — `linux` `kernel` `memory` `meminfo` `page-cache`
- [linux-page-cache](summaries/linux-page-cache.md) — Page Cache机制：基数树/XArray组织、预读窗口算法、Write Back一致性、Dirty page回写与丢失问题、Buffered/Direct IO选择 — `linux` `kernel` `page-cache` `file-io` `memory`
- [linux-network-protocol-stack-impl](summaries/linux-network-protocol-stack-impl.md) — Linux网络协议栈收发路径、sk_buff零拷贝机制与NAPI接收模型 — `linux` `kernel` `network` `tcp` `ip` `sk_buff` `protocol-stack`
- [linux-rcu-lock](summaries/linux-rcu-lock.md) — RCU读零开销哲学：宽限期机制、Tree RCU分层检测、五种变体(含Tasks RCU)与链表RCU操作、R/W比适用条件 — `linux` `kernel` `rcu` `lock` `synchronization`
- [gdb-common-commands](summaries/gdb-common-commands.md) — hellogcc/100-gdb-tips整理的GDB常用命令速查：断点/观察点/执行控制/内存查看/多线程/多进程/TUI — `linux` `gdb` `调试` `命令速查`
- [linux-task-struct-mm-struct](summaries/linux-task-struct-mm-struct.md) — task→mm→VMA→pgd四级链式结构、多线程共享mm、内核线程active_mm借用机制 — `linux` `内核` `task_struct` `mm_struct` `进程` `内存`
- [crash-vmcore-analysis](summaries/crash-vmcore-analysis.md) — crash工具分析vmcore的基本操作：bt/struct/dis/rd/kmem常用命令、时间戳转换 — `linux` `vmcore` `crash` `崩溃分析`
- [crash-register-address](summaries/crash-register-address.md) — x86_64和ARM64寄存器体系、函数调用约定、栈回溯原理、常见崩溃场景分析 — `linux` `寄存器` `x86` `ARM64` `崩溃分析` `调用约定`
- [linux-interrupt-monitoring-script](summaries/linux-interrupt-monitoring-script.md) — 不依赖额外模块的bash脚本：基于/proc/interrupts两次采样的每秒中断增量观测 — `linux` `中断` `监控脚本` `/proc/interrupts`
- [linux-interrupt-classification](summaries/linux-interrupt-classification.md) — 中断分类四维框架：同步/异步主轴、"软中断"歧义、上下半部阶段、功能×机制映射；SPI/PPI/LPI/MSI-X/IPI/NMI/LVT与Fault/Trap/Abort术语速查 — `linux` `中断` `分类` `IRQ` `架构`
- [linux-interrupt-lifecycle](summaries/linux-interrupt-lifecycle.md) — ARM GICv3中断全链路：三组件分工、中断号段、irq_domain映射hwirq→virq、request_irq注册与线程化中断、ARM64异常向量处理、workqueue五元组 — `linux` `中断` `GIC` `ARM` `irq_domain`
- [linux-ftrace-kprobe-overview](summaries/linux-ftrace-kprobe-overview.md) — ftrace(静态/开销大) vs kprobe(动态/灵活) vs bpftrace(eBPF)三大追踪框架概览 — `linux` `tracing` `ftrace` `kprobe` `bpftrace`
- [kernel-bonding-debug-log](summaries/kernel-bonding-debug-log.md) — 内核网络Bonding调试日志开启：printk级别调整+dynamic debug开启bond_3ad/bond_main源码打印 — `linux` `内核` `网络` `bonding` `dynamic-debug`
- [virtio-io-notification-mechanism](summaries/virtio-io-notification-mechanism.md) — Virtio前后端双向零拷贝通知：ioeventfd(Guest→Host)和irqfd(Host→Guest) — `linux` `虚拟化` `virtio` `ioeventfd` `irqfd`
- [virtio-vring-data-sharing](summaries/virtio-vring-data-sharing.md) — vring三大表(desc/avail/used)组成的生产者-消费者数据共享机制 — `linux` `虚拟化` `virtio` `vring` `数据共享`
- [linux-live-migration-flow](summaries/linux-live-migration-flow.md) — 虚拟机热迁移三阶段流程：内存迭代拷贝、停机拷贝、网络恢复与关键参数 — `linux` `虚拟化` `热迁移` `QEMU` `libvirt`
- [linux-memory-cpu-relationship](summaries/linux-memory-cpu-relationship.md) — 教材式虚拟内存原理：地址空间→空闲内存五种适配算法→分页与页表项→TLB→多级/倒排页表→九种页面置换算法(最优为老化+WSClock) — `linux` `内存` `虚拟内存` `分页` `页面置换`
- [linux-tlb-management](summaries/linux-tlb-management.md) — TLB作为MMU内的页表缓存：表项结构、ARM Cortex-A72两级TLB、global/local刷新策略、多核TLB shootdown与PCID(4.15全面启用)/ASID — `linux` `内核` `TLB` `分页` `PCID`
- [linux-zero-copy-impl](summaries/linux-zero-copy-impl.md) — 零拷贝机制推导：CPU COPY vs DMA COPY分工、read+send四次拷贝/四次上下文切换、sendfile(2.1)三次拷贝、sendfile+SG-DMA(2.4)零CPU拷贝 — `linux` `零拷贝` `sendfile` `DMA` `性能优化`
- [linux-cfs-scheduler-impl](summaries/linux-cfs-scheduler-impl.md) — CFS实现细节：vruntime换算公式、调度周期/粒度(6ms与0.75ms、多核×(1+log2(ncpus)))、rq/cfs_rq/sched_entity结构、五个调度类优先级与六种策略枚举 — `linux` `内核` `调度器` `CFS` `vruntime`
- [kernel-devmem-register-access](summaries/kernel-devmem-register-access.md) — devmem命令用法与/dev/mem依赖、内核配置项、open+mmap映射物理地址的实现原理——无需写驱动即可验证寄存器行为 — `linux` `内核调试` `devmem` `寄存器` `物理地址`
- [pci-bar-dma-space](summaries/pci-bar-dma-space.md) — PCIe驱动四大支柱：设备枚举(BIOS扫描配置空间)、BAR空间映射(ioremap)、DMA传输、MSI-X中断；BAR大小写全1读回探测+对齐分配，BAR配错是驱动故障最常见根因 — `linux` `pcie` `bar` `dma` `驱动`
- [linux-iommu-deep-dive](summaries/linux-iommu-deep-dive.md) — IOMMU六部曲：SWIOTLB软件bounce(memcpy)与Intel VT-d硬件I/O页表重映射互斥、初始化流程、DMA Coherent Mapping实践(Linux 5.5.4/x86-64) — `linux` `iommu` `vt-d` `swiotlb` `dma`
- [linux-iommu-smmu-illustrated](summaries/linux-iommu-smmu-illustrated.md) — IOMMU/SMMU图解综述：IOMMU与MMU对偶、内核框架五层、ARM SMMU、SVA共享页表、Group/Domain、VFIO MAP_DMA、GPA/HVA/HPA地址链与透传一致性 — `linux` `IOMMU` `SMMU` `虚拟化` `ARM`
- [linux-smmu-io-bypass](summaries/linux-smmu-io-bypass.md) — SMMU的STE级旁路：硬件照常开启，仅该SID的DMA直通PA(不经S1/S2、不查IOTLB、不查权限)；与BIOS关闭SMMU的区别、三模式对比、iommu.passthrough/smmu.bypassdev/disable_bypass — `linux` `smmu` `iommu` `arm` `dma`

## Entities (Linux)

- [libvirt-virsh](entities/libvirt-virsh.md) — libvirt命令行管理工具，覆盖VM全生命周期运维操作 — `linux` `虚拟化` `libvirt` `virsh` `工具`
- [perf-tool](entities/perf-tool.md) — Linux原生性能分析工具perf：基于事件采样，stat/top/record/report/kmem覆盖CPU/内存/调度/IO分析 — `linux` `perf` `性能分析` `CPU` `采样`
- [crash-tool](entities/crash-tool.md) — crash vmcore崩溃转储分析核心工具：bt/struct/kmem/dis命令回溯崩溃内核状态 — `linux` `vmcore` `crash` `崩溃分析` `内核调试`
- [gdb-tool](entities/gdb-tool.md) — GNU Debugger：断点/观察点/多线程/多进程/Core Dump/汇编/TUI，可调试QEMU初始化流程 — `linux` `gdb` `调试` `开发工具`
- [flamegraph-tool](entities/flamegraph-tool.md) — 火焰图(FlameGraph)：CPU调用栈可视化SVG，平顶=性能瓶颈，基于perf record数据生成 — `linux` `火焰图` `FlameGraph` `性能分析` `CPU可视化`

## Concepts (Linux 操作系统)

- [linux-os-virtualization-landscape](concepts/linux-os-virtualization-landscape.md) — OS+虚拟化+DFX导航枢纽：7个OS子领域+4个虚拟化子领域+7条OS→虚拟化映射+4个核心矛盾 — `linux` `虚拟化` `全景图` `内核` `DFX`
- [linux-interrupt-system](concepts/linux-interrupt-system.md) — Linux中断全景：同步/异步四维分类、IRQ/softirq两阶段设计、三种延迟机制、GIC组件与irq_domain映射、ksoftirqd、SMP IRQ Affinity — `linux` `kernel` `interrupt` `irq` `softirq`
- [linux-memory-management](concepts/linux-memory-management.md) — Linux内存管理：meminfo参数、Page Cache架构、内存黑洞、LRU与Write策略，并向下承接分页/页表/TLB原理基础 — `linux` `kernel` `memory` `meminfo` `page-cache` `lru`
- [virtual-memory-and-paging](concepts/virtual-memory-and-paging.md) — 虚拟内存的抽象与实现链：地址空间→分页与页表项→TLB(PCID/ASID与shootdown)→多级/倒排页表→九种页面置换算法(WSClock与老化最优) — `linux` `内存` `虚拟内存` `分页` `页面置换`
- [linux-io-stack](concepts/linux-io-stack.md) — Linux IO栈全景：VFS→Block→SCSI五层架构、IO生命周期与下发流程、四大IO调度器、Page/Buffer Cache缓存层次、hctx tags busy阻塞确认，向下衔接SSD介质语义与PCIe链路 — `linux` `kernel` `io` `block` `scheduler`
- [linux-fs-mount](concepts/linux-fs-mount.md) — 文件系统与Mount机制：mount/mountpoint/vfsmount三大结构+sys_mount五分支+do_new_mount两步挂载+lookup_mnt穿越挂载点 — `linux` `内核` `mount` `VFS` `文件系统`
- [linux-boot-shutdown](concepts/linux-boot-shutdown.md) — Linux启动与关机：10步启动流程、关机多子系统协调、systemd与架构差异 — `linux` `kernel` `boot` `shutdown` `systemd`
- [linux-network-stack](concepts/linux-network-stack.md) — Linux网络栈：TCP/IP四层模型、ARP/MAC/路由三张表与MAC老化、IP分片与PMTU、sk_buff零拷贝、NAPI混合模式 — `linux` `kernel` `network` `tcp` `ip` `sk_buff`
- [linux-lock-mechanisms](concepts/linux-lock-mechanisms.md) — Linux内核13种同步机制全景：qspinlock/Mutex/信号量/读写锁/WW Mutex/seqlock/RCU等演进与选择指南 — `linux` `kernel` `synchronization` `lock` `spinlock` `mutex` `rcu`
- [linux-namespace-cgroups](concepts/linux-namespace-cgroups.md) — Linux内核资源隔离双引擎：Namespace实现视图隔离，Cgroups实现资源限制 — `linux` `kernel` `namespace` `cgroups` `container` `isolation`
- [linux-process-scheduling](concepts/linux-process-scheduling.md) — Linux内核进程调度核心：CFS的vruntime红黑树机制、五个调度类优先级体系(stop>dl>rt>fair>idle)与六种调度策略 — `linux` `kernel` `scheduler` `CFS` `process` `scheduling`
- [linux-system-v-ipc](concepts/linux-system-v-ipc.md) — System V IPC三大机制：信号量集合、共享内存、消息队列的原理与API — `linux` `ipc` `semaphore` `shared-memory` `message-queue` `system-v`
- [linux-tracing-frameworks](concepts/linux-tracing-frameworks.md) — 内核追踪框架对比：ftrace(静态)/kprobe(动态)/perf(采样)/bpftrace(eBPF)/dynamic debug(源码级调试打印) — `linux` `内核` `tracing` `ftrace` `kprobe` `perf`
- [linux-cpu-performance-analysis](concepts/linux-cpu-performance-analysis.md) — CPU性能分析三大场景：perf采样/kvmtop VM-Exit/%ST抢占率 — `linux` `cpu` `性能分析` `虚拟化` `perf`
- [linux-vmcore-analysis](concepts/linux-vmcore-analysis.md) — vmcore崩溃转储分析：crash工具、x86/ARM64寄存器、task/mm结构体、栈回溯，辅以devmem在线读写寄存器 — `linux` `vmcore` `crash` `崩溃分析` `寄存器`
- [linux-io-performance-analysis](concepts/linux-io-performance-analysis.md) — IO性能分析：iostat监控/fio压测/dd测速/blktrace追踪/block_dump日志 — `linux` `io` `性能分析` `iostat` `fio`
- [cpu-cache-coherence](concepts/cpu-cache-coherence.md) — CPU读写内存完整路径(寄存器→L1/L2/L3→内存)、cache line与局部性原理、MESI/MESIF/MOESI缓存一致性协议演进、伪共享与缓存友好编程 — `linux` `cpu` `cache` `mesi` `缓存一致性`
- [memory-barriers](concepts/memory-barriers.md) — 内存屏障：编译器重排与CPU乱序执行、Store Buffer/Invalid Queue引入弱缓存一致性、读/写/全屏障精细控制、x86-TSO仅需StoreLoad屏障 — `linux` `内存屏障` `x86-tso` `store-buffer` `乱序执行`
- [linux-io-models](concepts/linux-io-models.md) — 五种IO模型、select/poll/epoll对比(epoll红黑树+就绪链表O(1))、缓存IO vs 直接IO(O_DIRECT绕过Page Cache) — `linux` `io` `epoll` `多路复用` `direct-io`
- [page-cache-vs-buffer-cache](concepts/page-cache-vs-buffer-cache.md) — Page Cache(页/逻辑层)与Buffer Cache(块/物理层)：2.4前双重缓存问题、统一后buffer_head的b_page指向Page Cache页、Buffer Cache成为子集 — `linux` `page-cache` `buffer-cache` `缓存` `内核`
- [linux-dma-mapping](concepts/linux-dma-mapping.md) — DMA映射两类：Coherent(一致性/长期映射)与Streaming(流式/按需map，可触发SWIOTLB bounce)；Intel IOMMU启用后DMA地址为IOVA经I/O页表翻译；IOMMU可把分散物理页聚合为连续IOVA — `linux` `dma` `iommu` `iova` `内存`
- [linux-iommu-subsystem](concepts/linux-iommu-subsystem.md) — Linux内核统一IOMMU抽象层：屏蔽Intel VT-d/AMD/ARM SMMU差异；框架五层(DMA-MAP API/IOVA+RCACHE/IO页表/驱动回调/VFIO接口)；SVA让CPU与设备共享页表 — `linux` `IOMMU` `SMMU` `ARM` `内核`

## Concepts (Linux 虚拟化)

- [linux-virtio-architecture](concepts/linux-virtio-architecture.md) — Virtio半虚拟化IO框架：前后端分离+四种架构演进(传统→vhost→vhost-user→vDPA) — `linux` `虚拟化` `virtio` `IO虚拟化` `半虚拟化`
- [linux-interrupt-virtualization](concepts/linux-interrupt-virtualization.md) — 中断虚拟化三种场景：物理设备中断→vCPU、虚拟外设中断→vCPU、Guest IPI — `linux` `虚拟化` `中断` `VGIC` `KVM`
- [linux-device-passthrough](concepts/linux-device-passthrough.md) — 设备直通三大技术：IOMMU(Intel VT-d DMA重映射+隔离，PCIe TLP以BDF标记设备)、SR-IOV(PF/VF)、VFIO(用户态驱动，Group/Container)；透通要求EPT与IOMMU映射一致 — `linux` `虚拟化` `直通` `IOMMU` `SR-IOV` `VFIO`
- [iommu-group-domain-isolation](concepts/iommu-group-domain-isolation.md) — IOMMU Group是DMA隔离最小硬件单元(同组共享domain页表PGD，须整体直通)；PCIe-PCI桥下游共享Source Identifier被迫同组；VFIO_IOMMU_MAP_DMA四步映射流程 — `linux` `IOMMU` `VFIO` `隔离` `虚拟化`
- [vm-address-translation-chain](concepts/vm-address-translation-chain.md) — 虚拟化四层地址空间：GVA→GPA(虚机页表，遍历本身经EPT)→HPA(EPT)；HVA由Qemu mmap+KVM_SET_USER_MEMORY_REGION桥接；设备透传要求HPA1(EPT)==HPA2(IOMMU) — `linux` `虚拟化` `EPT` `KVM` `内存`

## Skills (Linux 操作系统)

- [linux-kernel-debugging](skills/linux-kernel-debugging.md) — 内核各子系统监控命令与排查路径：softirq/meminfo(RSS≥PSS≥USS)/Page Cache/IO/关机/cgroup/IPC — `linux` `内核` `调试` `监控` `性能分析`
- [swiotlb-troubleshooting](skills/swiotlb-troubleshooting.md) — swiotlb buffer is full排查：slots统计分流根因+修复矩阵（扩池/q35/dma_debug），meminfo Bounce字段观测与IOMMU互斥关系 — `linux` `kernel` `DMA` `swiotlb` `调试`
- [linux-ipc-programming](skills/linux-ipc-programming.md) — System V IPC三大机制C编程实操：信号量集合+共享内存+消息队列的API速查与demo — `linux` `ipc` `编程` `信号量` `共享内存` `消息队列`
- [linux-lock-selection](skills/linux-lock-selection.md) — 内核锁类型选择决策树与API速查：Spinlock/Mutex/RCU等10种锁的适用场景与常见陷阱 — `linux` `内核` `锁` `spinlock` `mutex` `rcu` `同步`
- [linux-kernel-tracing](skills/linux-kernel-tracing.md) — 内核追踪实操手册：ftrace函数追踪→kprobe动态探针→perf事件采样→火焰图可视化四类场景 — `linux` `内核` `tracing` `ftrace` `kprobe` `perf` `火焰图`
- [linux-vmcore-debugging](skills/linux-vmcore-debugging.md) — vmcore崩溃分析实操：crash加载→堆栈回溯→寄存器解读→结构体分析→崩溃类型识别 — `linux` `vmcore` `crash` `崩溃分析` `寄存器` `内核调试`
- [linux-io-debugging](skills/linux-io-debugging.md) — IO性能排查与压测实操：iostat→fio→dd→blktrace→block_dump四步流程+SSD TRIM确认+IO调度器查看切换 — `linux` `io` `iostat` `fio` `blktrace` `dd` `性能分析`
- [linux-network-debugging](skills/linux-network-debugging.md) — 网络调试实操：tcpdump抓包+iperf打流+Bonding调试日志+ARP/路由三张表排查 — `linux` `网络` `tcpdump` `iperf` `bonding`
- [gdb-debugging-guide](skills/gdb-debugging-guide.md) — GDB调试实操速查：断点/观察点/执行控制/内存查看/多线程/多进程/Core Dump/QEMU调试 — `linux` `gdb` `调试` `QEMU` `断点` `观察点`

## Skills (Linux 虚拟化)

- [virsh-vm-management](skills/virsh-vm-management.md) — virsh管理KVM虚拟机的实操指南：生命周期、热迁移、CPU绑定等常用命令组合 — `linux` `虚拟化` `virsh` `运维` `操作手册`
- [linux-vm-debugging](skills/linux-vm-debugging.md) — 虚拟化调试实操：kvmtop EXT/%ST抢占/D状态vcpu/中断脚本/NUMA/QEMU gdb七大场景 — `linux` `虚拟化` `调试` `kvmtop` `虚拟机监控` `NUMA`

## Skills (知识管理与维护)

- [raw-source-link-sanitization](skills/raw-source-link-sanitization.md) — 中文技术站导入源追踪链接清洗：三类跳转链识别、perl正则替换、计数闭合验证、manifest哈希同步（不重蒸馏）、单文件回滚 — `obsidian` `wiki` `维护` `正则` `来源清洗`

## Synthesis (Linux)

- [linux-os-virtualization-landscape](concepts/linux-os-virtualization-landscape.md) — OS+虚拟化+DFX导航枢纽：7个OS子领域+4个虚拟化子领域+7条OS→虚拟化映射+4个核心矛盾（同时在Concepts中索引） — `linux` `虚拟化` `全景图` `内核` `DFX`
- [linux-kernel-subsystem-interactions](synthesis/linux-kernel-subsystem-interactions.md) — Linux内核六大子系统交互机制：preempt_count统一上下文追踪、softirq跨子系统分发、Page Cache交汇点、锁跨上下文协调 — `linux` `内核` `子系统交互` `preempt_count` `softirq` `page-cache` `锁`
- [linux-dfx-tool-landscape](synthesis/linux-dfx-tool-landscape.md) — DFX调试工具全景图：六大领域(CPU/IO/内存/网络/追踪/vmcore)+代码调试+硬件层×三种模式(监控/追踪/事后)的工具矩阵与互补关系 — `linux` `DFX` `调试` `工具全景` `性能分析`
- [virtio-architecture-evolution](synthesis/virtio-architecture-evolution.md) — Virtio四种架构演进分析：数据面从软件模拟到硬件直通，性能与灵活性的核心矛盾 — `linux` `虚拟化` `virtio` `vhost` `DPDK` `vDPA`

## Summaries (物理硬件)

- [pcie-error-nvme-drive-loss-guide](summaries/pcie-error-nvme-drive-loss-guide.md) — PCIe三级错误(CE/NFE/FE)与NVMe掉盘根因：掉盘是链路静默失败而非盘坏，链路层错误不写入SMART；四步定位法+四类高频场景+PRS监控 — `硬件` `PCIe` `NVMe` `AER` `故障诊断`
- [ssd-trim-command](summaries/ssd-trim-command.md) — TRIM指令原理：SSD页读块擦不对称→写放大，TRIM把无效页信息下推给SSD；三方支持检测与三种启用方法(fstrim.timer推荐) — `硬件` `SSD` `TRIM` `写放大` `NAND`
- [nic-smp-irq-affinity](summaries/nic-smp-irq-affinity.md) — SMP IRQ Affinity：APIC把硬中断绑定到指定CPU，smp_affinity位掩码配置，RPS/RFS补单队列网卡软中断均衡 — `硬件` `网卡` `中断` `affinity` `irqbalance`
- [bmc-intro](summaries/bmc-intro.md) — BMC带外管理控制器入门：与BIOS经IPMI/SMBus通信，IPMI/SOL/KVM-over-IP/SNMP/Redfish五大管理接口一览 — `硬件` `BMC` `IPMI` `带外管理` `服务器`
- [ipmi-sol-usage](summaries/ipmi-sol-usage.md) — IPMI SOL串口重定向：BMC把OS/BIOS串口输出转IPMI协议送LAN，远程操控控制台；grub/ESXi重定向配置+ipmitool sol activate — `硬件` `IPMI` `SOL` `串口` `远程管理`
- [optical-module-basics](summaries/optical-module-basics.md) — 光模块入门：TOSA/ROSA/BOSA三大器件、PIN vs APD探测器、TIA/CDR功能电路、SFP封装与收发两个方向的信号链 — `硬件` `光模块` `光纤` `SFP` `光电转换`
- [memory-spd-xmp](summaries/memory-spd-xmp.md) — 内存SPD与XMP：SPD是EEPROM自描述参数供BIOS自动配置，XMP是写入SPD的官方超频预设 — `硬件` `内存` `SPD` `XMP` `DDR`

## Entities (物理硬件)

- [bmc-baseboard-management-controller](entities/bmc-baseboard-management-controller.md) — BMC服务器带外管理微控制器：独立于主机OS，IPMI/SOL/KVM-over-IP/SNMP/Redfish五接口生态 — `硬件` `BMC` `IPMI` `带外管理`
- [optical-transceiver-module](entities/optical-transceiver-module.md) — 光模块：电↔光双向转换的可插拔器件，TOSA/ROSA/BOSA+PIN/APD+TIA/CDR构成收发链 — `硬件` `光模块` `TOSA` `ROSA` `光电转换`

## Concepts (物理硬件)

- [pcie-error-aer-nvme-drive-loss](concepts/pcie-error-aer-nvme-drive-loss.md) — PCIe错误体系与NVMe掉盘机理：CE/NFE/FE三级错误对应协议栈容错层级，链路错误不进SMART形成观测盲区，错误累积触发控制器复位 — `硬件` `PCIe` `AER` `NVMe` `可靠性`
- [ssd-trim-write-amplification](concepts/ssd-trim-write-amplification.md) — SSD介质语义：NAND页读块擦不对称→read-modify-write与写放大，TRIM缝合文件系统删除语义与介质知情断层 — `硬件` `SSD` `TRIM` `NAND` `写放大`
- [memory-spd-xmp-ecc](concepts/memory-spd-xmp-ecc.md) — 内存硬件基础：SPD自描述EEPROM+XMP超频预设；ECC纠错从冗余到汉明码——纠1bit检2bit — `硬件` `内存` `SPD` `XMP` `ECC`

## Skills (物理硬件)

- [nvme-pcie-drop-troubleshooting](skills/nvme-pcie-drop-troubleshooting.md) — NVMe掉盘PCIe根因排查实操：lspci链路初筛→AER+dmesg时间戳对齐→nvme-cli设备层深挖→最小系统隔离四步法 — `硬件` `PCIe` `NVMe` `故障诊断` `AER`
- [ipmi-sol-remote-console](skills/ipmi-sol-remote-console.md) — IPMI SOL远程串口控制台配置：BMC启IPMI over LAN→UEFI串口重定向→grub/ESXi console重定向→ipmitool sol activate — `硬件` `IPMI` `SOL` `串口` `远程运维`

## Synthesis (物理硬件)

- [hardware-layer-debugging-landscape](synthesis/hardware-layer-debugging-landscape.md) — 硬件层调试全景：硬件问题在软件指标中显形的五条规律——静默失败链、信息断层下推、亲和性杠杆、带外观察平面、功耗换时延 — `硬件` `调试` `全景图` `物理层` `性能分析`

## Concepts (数据结构与算法)

- [binary-tree-basics](concepts/binary-tree-basics.md) — 二叉树核心概念：三种形态、五个性质、链式/顺序存储、四种遍历方式与高频面试题型 — `数据结构` `二叉树` `遍历` `递归` `BST`
- [red-black-tree](concepts/red-black-tree.md) — 红黑树五大性质、与4阶B树等价性、12种插入+5类删除修复策略、AVL vs红黑树选型指南 — `数据结构` `红黑树` `AVL` `平衡树` `B树`
- [b-tree-bplus-tree](concepts/b-tree-bplus-tree.md) — B树与B+树的多路搜索结构、B+树更适合数据库索引的两大原因、B树vsB+树关键差异 — `数据结构` `B树` `B+树` `数据库索引` `磁盘IO`
- [graph-algorithms](concepts/graph-algorithms.md) — 图论核心算法全景：BFS/DFS遍历、最短路(Dijkstra/SPFA/Floyd)、拓扑排序、MST、并查集、Tarjan SCC、二分图匹配、网络流 — `数据结构` `图论` `BFS` `DFS` `最短路` `拓扑排序`

## Concepts (消息队列 & IO优化)

- [kafka-architecture](concepts/kafka-architecture.md) — Kafka分布式消息队列完整架构：ISR/HW/LEO可靠性+PageCache+零拷贝+顺序追加高性能三板斧 — `消息队列` `Kafka` `分布式` `高性能` `零拷贝`
- [mq-selection-comparison](concepts/mq-selection-comparison.md) — 三大MQ选型对比：Kafka(高吞吐低可靠)/RocketMQ(高可靠事务)/RabbitMQ(低延迟灵活路由) — `消息队列` `Kafka` `RocketMQ` `RabbitMQ` `选型`
- [zero-copy-memory-mapping](concepts/zero-copy-memory-mapping.md) — 零拷贝工具组：sendfile/splice/mmap/io_uring/DPDK各自解决不同瓶颈，选型先分清 CPU COPY / DMA COPY 再选工具 — `零拷贝` `sendfile` `mmap` `io_uring` `DPDK` `性能优化`

## Concepts (软件工程)

- [ood-principles-and-patterns](concepts/ood-principles-and-patterns.md) — 软件设计是对"变化"的辩证处理——六大设计原则（面向接口/依赖倒置/组合优于继承/SRP/OCP/LSP）+9种架构模式+23种GoF设计模式 — `软件工程` `设计原则` `设计模式` `OOP` `架构`

## Skills (数据结构与算法)

- [graph-algorithm-learning-path](skills/graph-algorithm-learning-path.md) — 图论算法从入门到进阶的学习路线、代码模板清单和经典模型映射 — `数据结构` `图论` `学习路线` `算法`

## Synthesis (数据结构与算法)

- [balanced-tree-evolution](synthesis/balanced-tree-evolution.md) — BST→AVL→红黑树→B/B+树平衡策略演进：严格平衡→弱平衡→多路矮胖，每种放松换取不同场景的性能收益 — `数据结构` `平衡树` `BST` `AVL` `红黑树`

## Concepts (AI)

### LLM基础设施 (训练/推理/服务化)  — 15条

- [llm-infra-landscape](concepts/llm-infra-landscape.md) — 大模型基础设施五层工程栈：硬件、系统软件、框架、应用、运营的系统化视角 — `AI` `LLM` `基础设施` `训练` `推理` `Agent`
- [gpu-computing-architecture](concepts/gpu-computing-architecture.md) — GPU与CPU架构差异：海量弱核+延迟隐藏，Roofline模型解释Prefill/Decode瓶颈 — `AI` `GPU` `CUDA` `HBM` `NVLink`
- [gpu-interconnect-networks](concepts/gpu-interconnect-networks.md) — GPU互联两层架构：Scale-up(NVLink/NVSwitch/NVL72)+Scale-out(IB/RoCEv2)；NVLink5达1.8TB/s；GPUDirect RDMA带宽增30-50% — `AI` `GPU` `NVLink` `InfiniBand` `RoCE` `网络`
- [cuda-software-stack](concepts/cuda-software-stack.md) — CUDA栈分工：cuBLAS/cuDNN/NCCL/Triton/CUTLASS，上层框架性能最终落到kernel和算子库 — `AI` `CUDA` `GPU` `cuBLAS` `cuDNN` `NCCL`
- [llm-training-pipeline](concepts/llm-training-pipeline.md) — LLM四阶段训练栈：Pre-train→中训→SFT→对齐，数据是第一生产力 — `AI` `LLM` `训练` `Pre-train` `SFT` `RLHF`
- [llm-parallelism-strategies](concepts/llm-parallelism-strategies.md) — 3D并行策略组合：DP/TP/PP/SP/EP/ZeRO按瓶颈组合——内存、计算、通信三个约束 — `AI` `LLM` `并行` `3D并行` `ZeRO` `训练`
- [llm-inference-engine](concepts/llm-inference-engine.md) — 推理两阶段(Prefill+Decode)心智模型：推理优化首先是资源调度问题 — `AI` `LLM` `推理` `KV cache` `batching`
- [speculative-decoding-mtp](concepts/speculative-decoding-mtp.md) — 推测解码：draft生成K候选+target单次验证；EAGLE-3达3.5-6.5x加速；batch增大加速递减；MTP训练范式变革 — `AI` `LLM` `推理` `推测解码` `MTP`
- [paged-attention-continuous-batching](concepts/paged-attention-continuous-batching.md) — PagedAttention+Continuous Batching：OS式内存管理+请求级动态调度，vLLM核心设计 — `AI` `LLM` `推理` `PagedAttention` `vLLM`
- [llm-quantization-engineering](concepts/llm-quantization-engineering.md) — LLM量化：精度/指令能力/服务成本三方博弈，FP8/INT8/AWQ/GPTQ方案对比 — `AI` `LLM` `量化` `FP8` `AWQ` `GPTQ`
- [moe-training-engineering](concepts/moe-training-engineering.md) — MoE稀疏激活：路由均衡+Expert Parallel+All-to-All才是工程难点 — `AI` `LLM` `MoE` `稀疏激活` `专家混合`
- [rlhf-alignment-pipeline](concepts/rlhf-alignment-pipeline.md) — 对齐流水线：PPO/DPO/GRPO在数据/奖励/采样/稳定性间做工程取舍 — `AI` `LLM` `RLHF` `DPO` `对齐` `PPO`
- [llm-serving-infrastructure](concepts/llm-serving-infrastructure.md) — 推理服务化：Triton/Ray Serve/PD分离，围绕SLO/资源隔离/弹性伸缩组织系统 — `AI` `LLM` `服务化` `Triton` `PD分离`
- [llm-gateway](concepts/llm-gateway.md) — 大模型网关：多供应商路由/配额/计费/语义缓存/Guardrails/可观测的统一入口 — `AI` `LLM` `网关` `LiteLLM` `路由`
- [llm-observability](concepts/llm-observability.md) — LLM可观测性：性能/语义质量/成本三维观测，Langfuse/OpenLLMetry — `AI` `LLM` `可观测` `Langfuse` `OpenTelemetry`

### RAG (检索增强生成)  — 7条（传统RAG 4条 + 高级RAG/GraphRAG 1条 + SAG 1条 + 向量库选型1条）

- [rag-engineering](concepts/rag-engineering.md) — RAG工程全景：从文档解析到答案评估的完整流水线+下一代演进方向(GraphRAG/HyDE/Self-RAG/Code-RAG/行业黑话/多模态RAG/SAG)，数据质量决定上限；文档解析+Chunking+Embedding(m3e)+混合检索+Rerank+5种高级范式+评估+三阶段落地路径+避坑清单 — `AI` `RAG` `检索` `向量库` `知识图谱`
- [rag-chunking-strategies](concepts/rag-chunking-strategies.md) — 21种RAG分块策略：基础→结构感知→语义驱动，分块决定检索质量 — `AI` `RAG` `Chunking` `分块` `文本分割`
- [rag-storage-technology](concepts/rag-storage-technology.md) — RAG存储四层架构：原始文件→元数据→切片(ES)→向量(Milvus/Qdrant/pgvector)，缺一层则功能失能 — `AI` `RAG` `存储` `向量库` `Elasticsearch`
- [rag-tools-landscape](concepts/rag-tools-landscape.md) — RAG工具链全景：7类解析工具+分块策略+Embedding选型+向量库+重排序+7个RAG开源框架对比——选型先确认瓶颈再选工具 — `AI` `RAG` `工具` `解析` `向量模型`
- [graphrag-engineering](concepts/graphrag-engineering.md) — GraphRAG用知识图谱解决全局型问题：实体→关系→Leiden社区摘要→全局/局部/DRIFT三种搜索，代价是LLM调用量大 — `AI` `RAG` `知识图谱` `GraphRAG` `社区检测`
- [sag-sql-retrieval-augmented-generation](concepts/sag-sql-retrieval-augmented-generation.md) — SAG用SQL+向量混合检索替代GraphRAG全局图构建——查询时用SQL join临时激活局部Hyperedge结构，多跳Recall@5达80% — `AI` `RAG` `SAG` `SQL` `Hyperedge`
- [vector-database-comparison](entities/vector-database-comparison.md) — 向量库选型：HNSW原理实践+四大局限+灵积DashScope全栈；DiskANN 10B+解+RaBitQ 32x压缩；Milvus/Qdrant/pgvector三强；向量库非银弹，混合检索是务实标配 — `AI` `RAG` `向量库` `Milvus` `Qdrant` `HNSW`

### Agent框架 (智能体/工具调用)  — 9条（含landscape导航页面+Harness Engineering+Multi-Agent编排+OMO+系统架构设计+通信协议三层）

- [agent-architecture-landscape](concepts/agent-architecture-landscape.md) — Agent架构7个子领域导航枢纽：树状拓扑+4个核心矛盾+子领域连接+LLM基础设施边界 — `AI` `Agent` `RAG` `知识图谱` `全景图`
- [agent-paradigm-selection](concepts/agent-paradigm-selection.md) — Agent行为范式选型：ReAct(TAO循环)/Plan-Exec/ReWOO(计划前置省80% token)/Reflect/Ralph Loop(无限循环+Stop Hook)/Harness，按任务结构/成本/延迟/可控性四维选型 — `AI` `Agent` `ReAct` `范式` `选型`
- [agent-reliability-engineering](concepts/agent-reliability-engineering.md) — Agent可靠性工程：幂等键由编排器派生、重试90.8%浪费于幻觉工具名(需错误分类+熔断+确定性路由)、高级工具调用三技术与HITL动态中断 — `AI` `Agent` `可靠性` `幂等性` `工具调用`
- [loop-engineering](concepts/loop-engineering.md) — Loop Engineering用系统替代人肉提示Agent：六原语+四层循环栈(Agent/验证/事件驱动/爬山)+四次范式跃迁(Prompt→Context→Harness→Loop)+企业级治理 — `AI` `Agent` `Loop` `自动化` `范式演进`
- [agent-framework-engineering](concepts/agent-framework-engineering.md) — Agent五大支柱：工作流/状态/记忆/工具/协议，可靠Agent=可观测状态机 — `AI` `Agent` `LangGraph` `MCP` `工具调用`
- [agent-system-architecture](concepts/agent-system-architecture.md) — Agent系统架构设计：执行循环+消息总线+Skill vs Tool+三层Memory+Sub-agent+声明式设计 — `AI` `Agent` `架构设计` `执行循环` `消息总线`
- [harness-engineering](concepts/harness-engineering.md) — Harness Engineering（驾驭工程）：围绕AI Agent构建约束、反馈回路与执行控制——模型负责推理，Harness负责一切外围工程 — `AI` `Agent架构` `Harness` `约束系统` `工程范式`
- [tool-calling-mcp](concepts/tool-calling-mcp.md) — 工具调用与MCP：JSON Schema+结构化输出+MCP统一工具生态，协议与安全边界；含三大协议栈定位（MCP工具驱动层/ACP协作通信层/A2A公共发现层） — `AI` `Agent` `MCP` `Function Call` `工具调用`
- [agent-communication-protocols](concepts/agent-communication-protocols.md) — Agent通信协议三大分类：MCP（工具驱动层Agent↔Resource）+ACP（协作通信层Agent↔Agent企业内）+A2A（公共发现层跨厂商）——像网络协议栈一样各司其职，开源中间件将"翻译"成统一接口 — `AI` `Agent` `MCP` `ACP` `A2A`
- [multi-agent-framework-comparison](concepts/multi-agent-framework-comparison.md) — 四大Multi-Agent框架对比：LangGraph(可靠)/CrewAI(简单)/AutoGen(灵活)/AgentX(安全) — `AI` `Agent` `LangGraph` `CrewAI` `AutoGen`
- [multi-agent-orchestration](concepts/multi-agent-orchestration.md) — Multi-Agent协同编排7个设计模式：角色分化+工具隔离、主编排+子执行、双轨主Agent、证据完成、并发防递归、completion_promise续跑、AgentPromptMetadata自描述 — `AI` `Agent` `Multi-Agent` `编排` `协同`
- [agent-development-platforms-landscape](concepts/agent-development-platforms-landscape.md) — Agent开发平台全景图：10+主流平台按定位分5类（自主任务执行/可视化编排/通用LLM框架/多Agent协作/有状态Agent）——AutoGPT/Dify/LangChain/MetaGPT/CrewAI/Letta等 — `AI` `Agent` `平台` `全景图` `开源`
- [llm-wiki-methodology](concepts/llm-wiki-methodology.md) — Karpathy LLM Wiki方法论：编译式知识库（vs RAG检索式）、Raw/Wiki/Schema三层、Ingest/Query/Lint三操作、渐进式披露——本vault的方法论根基 — `AI` `LLM` `知识管理` `Obsidian` `知识库`
- [obsidian-ai-toolchain](concepts/obsidian-ai-toolchain.md) — Obsidian AI工具链：Claudian/OpenCode/Copilot接入层+Clipper/Terminal插件层+Start My Day技能层+qmd/Tavily检索层 — `AI` `Obsidian` `工具链` `插件` `知识管理`

### 评估系统 (评测/指标)  — 2条

- [evaluation-metrics](concepts/evaluation-metrics.md) — 分类评估指标核心：混淆矩阵→准确率/精确率/召回率/F1；类别不平衡时准确率失效；7个RAG检索排序指标(P@K/MRR/MAP/nDCG) — `AI` `评估` `混淆矩阵` `准确率` `精确率` `召回率`
- [llm-benchmarks](concepts/llm-benchmarks.md) — LLM评测基准六大维度：知识(MMLU/ARC)、推理(GSM8K/DROP/BBH)、对话(MT-bench)、抽取(MS-MARCO)、安全(TruthfulQA/HHH)、编程(HumanEval/MBPP) — `AI` `LLM` `评测` `Benchmark` `基准`

### 安全 (对抗攻击)  — 1条

- [agent-security](concepts/agent-security.md) — Claude Fable 5破解事件揭示LLM安全分类器4类绕过手法——安全是动态对抗而非静态防御 — `AI` `安全` `Agent` `对抗攻击`

### 数据飞轮 (正反馈循环)  — 1条

- [data-flywheel](concepts/data-flywheel.md) — 数据飞轮：数据和业务间的正反馈循环——AI辅助决策产出更多数据，更多数据强化AI决策，飞轮越转越快 — `AI` `数据飞轮` `数据要素` `知识管理` `企业数字化`

## Summaries (AI)

- [agent-system-architecture-design](summaries/agent-system-architecture-design.md) — Agent执行循环Observe-Think-Act架构+Skill vs Tool+三层Memory+Sub-agent+声明式设计 — `AI` `Agent` `执行循环` `Skill` `Memory`
- [agent-message-bus-architecture](summaries/agent-message-bus-architecture.md) — 消息总线解耦Channel-Agent+四层架构+同Session串行不同并发+LLM Provider统一接口 — `AI` `Agent` `消息总线` `多渠道` `解耦`
- [a2a-protocol](summaries/a2a-protocol.md) — A2A协议：Google推出的Agent间开放协议——Agent Card+Task+Message/Part+Artifact，HTTP/JSON-RPC/SSE，异步+模态无关 — `AI` `Agent` `A2A` `协议` `互操作性`
- [acp-protocol](summaries/acp-protocol.md) — ACP协议：IBM/LinuxFoundation的Agent协作协议——REST+Agent/Run两阶段+离线发现，企业防火墙内多Agent协作 — `AI` `Agent` `ACP` `协议` `协作`
- [ai-protocols-comparison](summaries/ai-protocols-comparison.md) — 三大AI协议对比：MCP(外接大脑/工具)+ACP(本地对讲机/企业内Agent协作)+A2A(国际通用语/跨厂商发现) — `AI` `Agent` `MCP` `ACP` `A2A`
- [agent-development-platforms-top10](summaries/agent-development-platforms-top10.md) — 10个Agent开发平台：AutoGPT/Dify/LangChain/MetaGPT/AutoGen/Flowise/CrewAI/ChatDev/SuperAGI/Letta定位对比 — `AI` `Agent` `平台` `AutoGPT` `Dify`

## Entities (AI)

### LLM基础设施  — 2条

- [vllm-sglang-tensorrt](entities/vllm-sglang-tensorrt.md) — 推理引擎四强对比：vLLM生态最强/SGLang延迟最优/TensorRT吞吐最高/TGI最稳 — `AI` `vLLM` `SGLang` `TensorRT-LLM` `推理引擎`
- [megatron-deepspeed](entities/megatron-deepspeed.md) — Megatron偏高性能内核/DeepSpeed偏显存优化易用性，选型取决于规模拓扑维护能力 — `AI` `Megatron` `DeepSpeed` `训练框架`

### Agent框架  — 5条

- [langchain-framework](entities/langchain-framework.md) — LangChain框架：Runnable+LCEL统一可执行单元，六大包分离架构 — `AI` `LangChain` `LCEL` `框架`
- [langgraph-framework](entities/langgraph-framework.md) — LangGraph工作流编排：有向图+状态持久化+循环支持+完整Memory架构(短期Checkpoint+长期Store)，Agent从自由聊天升级为可观测状态机 — `AI` `LangGraph` `工作流` `状态机` `Agent`
- [claude-code](entities/claude-code.md) — Claude Code：Anthropic的AI编程Agent——极简while循环架构+六层记忆系统+子代理上下文隔离+Hook自动化 — `AI` `Claude` `Agent工具` `代码助手` `Anthropic`
- [oh-my-opencode](entities/oh-my-opencode.md) — Oh My OpenCode：OpenCode超级插件——11个希腊神话命名agent编排+Ralph Loop自动续跑+Hashline Edit防幻觉+三级并发+Claude Code兼容层 — `AI` `Agent` `Multi-Agent` `OpenCode` `编排`
- [headroom-tool](entities/headroom-tool.md) — Headroom上下文压缩中间件：ContentRouter+5策略(SmartCrusher/CodeCompressor/Kompress-base/CacheAligner/CCR)，SRE日志92%Token节省，MCP server模式跨Agent共享记忆 — `AI` `Agent` `Token压缩` `上下文压缩` `中间件`
- [dsh-plugin-ecosystem](entities/dsh-plugin-ecosystem.md) — DeepSeek Harness插件生态Top10：web-ui全家桶⭐1312、modlens纯文本模型看图、better-sidebar工作台、dsh_workflow多Agent编排治理 — `AI` `Agent` `DeepSeek` `插件` `工具`

### RAG  — 1条

- [ragas-framework](entities/ragas-framework.md) — RAGAS RAG量化评估框架：Context Precision/Recall检索层+Faithfulness/Answer Relevancy生成层，把"感觉对"变成"数据证明对" — `AI` `RAG` `评估` `RAGAS` `量化评估`

### 知识图谱  — 1条

- [graphify-gitnexus](entities/graphify-gitnexus.md) — Graphify偏认知整合/GitNexus偏工程执行，两种知识图谱工具的设计哲学差异 — `AI` `知识图谱` `Graphify` `GitNexus` `MCP`

## Synthesis (AI)

- [llm-infra-evolution-2022-2026](synthesis/llm-infra-evolution-2022-2026.md) — 大模型基础设施四年四轮范式转移：推理确立→开源爆发→引擎革命→成本革命，工程密度>硬件堆量 — `AI` `LLM` `基础设施` `演进` `DeepSeek`

## Concepts (云原生)

### K8s 核心（编排+网络+安全）  — 5条（含新的landscape导航页面）

- [k8s-cloud-native-landscape](concepts/k8s-cloud-native-landscape.md) — 云原生5个子领域导航枢纽：树状拓扑+4条Linux→云原生映射+3个核心矛盾+与Linux/AI边界 — `云原生` `Kubernetes` `全景图` `导航`
- [k8s-architecture](concepts/k8s-architecture.md) — K8s声明式API+协调循环驱动自愈/弹性/滚动更新；控制面+数据面核心组件；Pod/Deployment/Service核心抽象 — `云原生` `Kubernetes` `容器编排` `分布式系统` `声明式API`
- [k8s-networking](concepts/k8s-networking.md) — K8s网络四层模型：容器内localhost→Pod间CNI→Service ClusterIP+CoreDNS→Ingress L7路由 — `云原生` `Kubernetes` `网络` `CNI` `Service`
- [k8s-security](concepts/k8s-security.md) — K8s安全五维度加固：RBAC+NetworkPolicy+PSS restricted+Secret加密+API Server管控 — `云原生` `Kubernetes` `安全` `RBAC` `NetworkPolicy`
- [k8s-cni-comparison](concepts/k8s-cni-comparison.md) — 五大CNI对比：Flannel VXLAN/Calico BGP/Cilium eBPF/Weave Net/Kube-router；iptables O(n)→IPVS→eBPF三代演进 — `云原生` `Kubernetes` `CNI` `网络` `eBPF`
- [helm-package-management](concepts/helm-package-management.md) — Helm是K8s的包管理器("apt-get/yum of K8s")：Chart打包+Values多环境分离+Release全生命周期；Helm 3移除Tiller转纯CLI — `云原生` `Kubernetes` `Helm` `包管理` `CI/CD`

### 容器运行时（隔离+存储+安全+性能）  — 6条

- [container-runtime-deep-dive](concepts/container-runtime-deep-dive.md) — 容器=Namespace+Cgroup+pivot_root+OverlayFS+Seccomp拼装；8种Namespace+PID1陷阱+chroot逃逸+OCI规范 — `云原生` `容器` `运行时` `Linux内核` `OCI`
- [cgroups-v2-deep-dive](concepts/cgroups-v2-deep-dive.md) — Cgroups v2统一层级：cpu.max/weight+memory low/high/max三道防线+writeback-aware IO+PSI压力指标 — `云原生` `Linux` `Cgroups` `容器` `资源限制`
- [overlayfs-container-images](concepts/overlayfs-container-images.md) — OverlayFS联合挂载+Copy-on-Write(100MB文件首次写慢263倍)+overlay2 Docker默认驱动+数据库必须放volume — `云原生` `OverlayFS` `容器` `存储` `Copy-on-Write`
- [seccomp-capabilities](concepts/seccomp-capabilities.md) — Seccomp-BPF syscall拦截+Capabilities权限拆分=容器安全纵深防御两道防线；Docker --privileged拆掉两道防线 — `云原生` `Linux` `安全` `Seccomp` `Capabilities` `容器安全`
- [container-vs-microvm](concepts/container-vs-microvm.md) — 容器共享内核vs microVM独立内核；Firecracker 125ms启动与容器同量级；Kata Containers=OCI接口+microVM隔离 — `云原生` `容器` `microVM` `Firecracker` `KVM` `安全`
- [container-network-benchmarking](concepts/container-network-benchmarking.md) — 容器网络实测：veth+bridge吞吐-20%/P99 4.4x；macvlan近裸机；Cilium eBPF不受iptables规则影响 — `云原生` `容器` `网络` `性能` `eBPF`

### 可观测  — 1条

- [prometheus-architecture](concepts/prometheus-architecture.md) — Prometheus Pull模型+ServiceDiscovery+PromQL；每样本~3.5字节；Histogram可聚合Summary不可；ServiceMonitor CRD — `云原生` `Prometheus` `监控` `TSDB` `可观测性`

## Entities (云原生)

- [containerd-runtime](entities/containerd-runtime.md) — containerd容器生命周期管理器：K8s≈Nova/containerd≈libvirtd/runc≈QEMU三层类比；CRI内置+shim解耦 — `云原生` `containerd` `容器运行时` `CRI` `Kubernetes`
- [runc-oci-reference](entities/runc-oci-reference.md) — OCI Runtime Spec参考实现(~15000行Go+C)；nsenter C代码+三次clone+两阶段init+exec FIFO同步 — `云原生` `runc` `OCI` `容器运行时` `Go`

## Summaries (云原生)

- [k8s-terminology-cheatsheet](summaries/k8s-terminology-cheatsheet.md) — K8s集群13类核心术语中文速查：声明式API/协调循环/控制面/数据面/etcd/Raft/Pod/Deployment/Service/CNI/RBAC — `云原生` `Kubernetes` `术语` `速查表`
- [k8s-official-architecture](summaries/k8s-official-architecture.md) — K8s官方文档架构蒸馏：控制面+数据面+四种架构变体+kube-proxy可选 — `云原生` `Kubernetes` `架构` `官方文档`
- [k8s-alibaba-cloud-principles](summaries/k8s-alibaba-cloud-principles.md) — 阿里云K8S技术原理深度解读：声明式API+协调循环+网络三铁律+CNI三强+Service Mesh+GitOps+Operator — `云原生` `Kubernetes` `技术原理` `阿里云`

## Skills (云原生)

- [k8s-security-hardening](skills/k8s-security-hardening.md) — K8s安全五维度实操：RBAC+NetworkPolicy默认拒绝+PSS restricted+Secret加密+API Server匿名禁用 — `云原生` `Kubernetes` `安全` `RBAC` `NetworkPolicy`
- [k8s-network-troubleshooting](skills/k8s-network-troubleshooting.md) — K8s网络故障排查：三类真实故障复盘(网段冲突NAT/主节点DNS断服/容器网络抖动KubeSkoop)+通用五步排查法+命令速查 — `云原生` `Kubernetes` `网络` `排错` `Cilium`
- [container-network-benchmarking-skill](skills/container-network-benchmarking-skill.md) — 容器网络性能测试方法论：iperf3测吞吐+sockperf测P99+关闭TCP offload；六种方案实测数据 — `云原生` `容器` `网络` `性能测试` `iperf3`

## Synthesis (云原生)

- [k8s-cloud-native-landscape](concepts/k8s-cloud-native-landscape.md) — 云原生5子领域导航枢纽+4条Linux→云原生映射+3个核心矛盾（同时在Concepts中索引） — `云原生` `Kubernetes` `全景图` `导航`
- [cloud-native-infrastructure-landscape](synthesis/cloud-native-infrastructure-landscape.md) — 云原生三层架构全景：底层Linux内核特性→中间containerd/shim/runc→上层K8s编排+Service Mesh+GitOps+可观测 — `云原生` `Kubernetes` `容器` `全景图` `架构`

## Recommendations (学习推荐)

- [2026-06-25](recommendations/2026-06-25.md) — Loop Engineering 学习推荐：12篇深度推荐+3篇博客下载+五要素/四代演进/Loopcraft/Salty Lesson/验证器瓶颈/Hill Climbing Loop — `Loop Engineering` `循环工程` `Agent架构` `验证器瓶颈` `Loopcraft`
- [2026-06-15](recommendations/2026-06-15.md) — Harness Engineering 第二次推荐：9篇新博客+Meta-Harness/Loop Engineering/CDLC/Context Flywheel/Ralph Loop实践 — `Harness Engineering` `Agent架构` `Meta-Harness` `Loop Engineering` `上下文工程`
- [2026-06-13](recommendations/2026-06-13.md) — Harness Engineering 首次推荐：15篇博客+9章节报告+核心术语表 — `Harness Engineering` `Agent架构` `约束系统` `反馈回路` `可靠性`
- [2026-06-12](recommendations/2026-06-12.md) — LangGraph + GraphRAG 学习推荐
- [2026-05-27](recommendations/2026-05-27.md) — 消息队列 学习推荐
- [2026-05-26](recommendations/2026-05-26.md) — 消息队列（Kafka/RabbitMQ）
- [2026-05-22](recommendations/2026-05-22.md) — Linux/Agent 学习推荐
- [2026-05-21](recommendations/2026-05-21.md) — Agent范式 学习推荐
- [2026-05-20](recommendations/2026-05-20.md) — Agent范式（ReAct/Human-in-the-loop/幂等性）
- [2026-05-19](recommendations/2026-05-19.md) — Agent范式 学习推荐
- [2026-05-18](recommendations/2026-05-18.md) — LangChain/LangGraph 学习推荐
- [2026-05-16](recommendations/2026-05-16.md) — 云原生 学习推荐
- [2026-05-15](recommendations/2026-05-15.md) — 大模型基础设施 学习推荐

## Projects

- [my-obsidian-wiki](projects/my-obsidian-wiki.md) — 本 vault 自身的项目知识枢纽：三层架构、架构决策索引、运营模式（重叠合并/稀薄折叠/backup 流/链接清洗/键迁移）、知识域扩张史与待办债务 — `obsidian` `wiki` `知识管理` `llm`

## Journal
