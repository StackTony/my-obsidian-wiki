---
title: Wiki Index
updated: 2026-06-13
---

# Wiki Index

*自动维护。上次更新：2026-06-13 (云原生领域分类显式化)*

## Summaries (数据结构与算法)

- [binary-tree-basics](summaries/binary-tree-basics.md) — 二叉树核心概念、三种形态、五个性质、四种遍历、链式/顺序存储与高频面试题原文摘要 — `数据结构` `二叉树` `遍历` `BST`
- [red-black-tree-detail](summaries/red-black-tree-detail.md) — 红黑树五大性质、与4阶B树等价、12种插入情况、5类删除修复、AVL vs红黑树完整对比原文摘要 — `数据结构` `红黑树` `AVL` `平衡树`
- [avl-redblack-btree-intro](summaries/avl-redblack-btree-intro.md) — BST→AVL→红黑树→B/B+树演进路线、各树特性对比、B+树更适合数据库索引的两大原因 — `数据结构` `AVL` `红黑树` `B树` `B+树`
- [graph-algorithms-overview](summaries/graph-algorithms-overview.md) — 图论算法学习路线全景图：BFS/DFS→并查集→最短路→拓扑→MST→强连通→二分图→网络流 — `数据结构` `图论` `BFS` `DFS` `最短路`

## Summaries (Linux)

- [linux-softirq-detail](summaries/linux-softirq-detail.md) — Linux软中断的完整实现：preempt_count防抢占机制、__do_softirq执行流、ksoftirqd溢出处理 — `linux` `kernel` `softirq` `interrupt` `ksoftirqd`
- [linux-meminfo-params](summaries/linux-meminfo-params.md) — /proc/meminfo各字段含义与关系：内存黑洞、LRU分类、HugePages与THP区别、关键公式 — `linux` `kernel` `memory` `meminfo` `page-cache`
- [linux-page-cache](summaries/linux-page-cache.md) — Page Cache机制：基数树结构、预读算法、Write Through与Write Back一致性、Dirty page回写 — `linux` `kernel` `page-cache` `file-io` `memory`
- [linux-network-protocol-stack-impl](summaries/linux-network-protocol-stack-impl.md) — Linux网络协议栈收发路径、sk_buff零拷贝机制与NAPI接收模型 — `linux` `kernel` `network` `tcp` `ip` `sk_buff` `protocol-stack`
- [linux-rcu-lock](summaries/linux-rcu-lock.md) — RCU读零开销哲学：宽限期机制、Tree RCU分层检测、SRCU可睡眠变体与适用条件 — `linux` `kernel` `rcu` `lock` `synchronization`
- [gdb-common-commands](summaries/gdb-common-commands.md) — hellogcc/100-gdb-tips整理的GDB常用命令速查：断点/观察点/执行控制/内存查看/多线程/多进程/TUI — `linux` `gdb` `调试` `命令速查`
- [linux-task-struct-mm-struct](summaries/linux-task-struct-mm-struct.md) — task→mm→VMA→pgd四级链式结构、多线程共享mm、内核线程active_mm借用机制 — `linux` `内核` `task_struct` `mm_struct` `进程` `内存`
- [crash-vmcore-analysis](summaries/crash-vmcore-analysis.md) — crash工具分析vmcore的基本操作：bt/struct/dis/rd/kmem常用命令、时间戳转换 — `linux` `vmcore` `crash` `崩溃分析`
- [crash-register-address](summaries/crash-register-address.md) — x86_64和ARM64寄存器体系、函数调用约定、栈回溯原理、常见崩溃场景分析 — `linux` `寄存器` `x86` `ARM64` `崩溃分析` `调用约定`
- [linux-interrupt-monitoring-script](summaries/linux-interrupt-monitoring-script.md) — 不依赖额外模块的bash脚本：基于/proc/interrupts两次采样的每秒中断增量观测 — `linux` `中断` `监控脚本` `/proc/interrupts`
- [linux-ftrace-kprobe-overview](summaries/linux-ftrace-kprobe-overview.md) — ftrace(静态/开销大) vs kprobe(动态/灵活) vs bpftrace(eBPF)三大追踪框架概览 — `linux` `tracing` `ftrace` `kprobe` `bpftrace`
- [virtio-io-notification-mechanism](summaries/virtio-io-notification-mechanism.md) — Virtio前后端双向零拷贝通知：ioeventfd(Guest→Host)和irqfd(Host→Guest) — `linux` `虚拟化` `virtio` `ioeventfd` `irqfd`
- [virtio-vring-data-sharing](summaries/virtio-vring-data-sharing.md) — vring三大表(desc/avail/used)组成的生产者-消费者数据共享机制 — `linux` `虚拟化` `virtio` `vring` `数据共享`
- [linux-live-migration-flow](summaries/linux-live-migration-flow.md) — 虚拟机热迁移三阶段流程：内存迭代拷贝、停机拷贝、网络恢复与关键参数 — `linux` `虚拟化` `热迁移` `QEMU` `libvirt`

## Entities (Linux)

- [libvirt-virsh](entities/libvirt-virsh.md) — libvirt命令行管理工具，覆盖VM全生命周期运维操作 — `linux` `虚拟化` `libvirt` `virsh` `工具`
- [perf-tool](entities/perf-tool.md) — Linux原生性能分析工具perf：基于事件采样，stat/top/record/report/kmem覆盖CPU/内存/调度/IO分析 — `linux` `perf` `性能分析` `CPU` `采样`
- [crash-tool](entities/crash-tool.md) — crash vmcore崩溃转储分析核心工具：bt/struct/kmem/dis命令回溯崩溃内核状态 — `linux` `vmcore` `crash` `崩溃分析` `内核调试`
- [gdb-tool](entities/gdb-tool.md) — GNU Debugger：断点/观察点/多线程/多进程/Core Dump/汇编/TUI，可调试QEMU初始化流程 — `linux` `gdb` `调试` `开发工具`
- [flamegraph-tool](entities/flamegraph-tool.md) — 火焰图(FlameGraph)：CPU调用栈可视化SVG，平顶=性能瓶颈，基于perf record数据生成 — `linux` `火焰图` `FlameGraph` `性能分析` `CPU可视化`

## Concepts (Linux 操作系统)

- [linux-os-virtualization-landscape](concepts/linux-os-virtualization-landscape.md) — OS+虚拟化+DFX导航枢纽：7个OS子领域+4个虚拟化子领域+7条OS→虚拟化映射+4个核心矛盾 — `linux` `虚拟化` `全景图` `内核` `DFX`
- [linux-interrupt-system](concepts/linux-interrupt-system.md) — Linux中断系统：IRQ/softirq两阶段设计、三种延迟机制、ksoftirqd — `linux` `kernel` `interrupt` `irq` `softirq`
- [linux-memory-management](concepts/linux-memory-management.md) — Linux内存管理：meminfo参数、Page Cache架构、内存黑洞、LRU与Write策略 — `linux` `kernel` `memory` `meminfo` `page-cache` `lru`
- [linux-io-stack](concepts/linux-io-stack.md) — Linux IO栈：五层IO架构、IO调度器、设备发现与gendisk结构 — `linux` `kernel` `io` `block` `scheduler`
- [linux-boot-shutdown](concepts/linux-boot-shutdown.md) — Linux启动与关机：10步启动流程、关机多子系统协调、systemd与架构差异 — `linux` `kernel` `boot` `shutdown` `systemd`
- [linux-network-stack](concepts/linux-network-stack.md) — Linux网络栈：TCP/IP四层模型、三张核心表、sk_buff零拷贝、NAPI混合模式 — `linux` `kernel` `network` `tcp` `ip` `sk_buff`
- [linux-lock-mechanisms](concepts/linux-lock-mechanisms.md) — Linux内核同步机制的完整框架：从Spinlock到RCU的演进与选择指南 — `linux` `kernel` `synchronization` `lock` `spinlock` `mutex` `rcu`
- [linux-namespace-cgroups](concepts/linux-namespace-cgroups.md) — Linux内核资源隔离双引擎：Namespace实现视图隔离，Cgroups实现资源限制 — `linux` `kernel` `namespace` `cgroups` `container` `isolation`
- [linux-process-scheduling](concepts/linux-process-scheduling.md) — Linux内核进程调度核心：CFS完全公平调度器的红黑树机制与三种调度策略 — `linux` `kernel` `scheduler` `CFS` `process` `scheduling`
- [linux-system-v-ipc](concepts/linux-system-v-ipc.md) — System V IPC三大机制：信号量集合、共享内存、消息队列的原理与API — `linux` `ipc` `semaphore` `shared-memory` `message-queue` `system-v`
- [linux-tracing-frameworks](concepts/linux-tracing-frameworks.md) — 内核追踪四大框架对比：ftrace(静态)/kprobe(动态)/perf(采样)/bpftrace(eBPF) — `linux` `内核` `tracing` `ftrace` `kprobe` `perf`
- [linux-cpu-performance-analysis](concepts/linux-cpu-performance-analysis.md) — CPU性能分析三大场景：perf采样/kvmtop VM-Exit/%ST抢占率 — `linux` `cpu` `性能分析` `虚拟化` `perf`
- [linux-vmcore-analysis](concepts/linux-vmcore-analysis.md) — vmcore崩溃转储分析：crash工具、x86/ARM64寄存器、task/mm结构体、栈回溯 — `linux` `vmcore` `crash` `崩溃分析` `寄存器`
- [linux-io-performance-analysis](concepts/linux-io-performance-analysis.md) — IO性能分析：iostat监控/fio压测/dd测速/blktrace追踪/block_dump日志 — `linux` `io` `性能分析` `iostat` `fio`

## Concepts (Linux 虚拟化)

- [linux-virtio-architecture](concepts/linux-virtio-architecture.md) — Virtio半虚拟化IO框架：前后端分离+四种架构演进(传统→vhost→vhost-user→vDPA) — `linux` `虚拟化` `virtio` `IO虚拟化` `半虚拟化`
- [linux-interrupt-virtualization](concepts/linux-interrupt-virtualization.md) — 中断虚拟化三种场景：物理设备中断→vCPU、虚拟外设中断→vCPU、Guest IPI — `linux` `虚拟化` `中断` `VGIC` `KVM`
- [linux-device-passthrough](concepts/linux-device-passthrough.md) — 设备直通三大技术：IOMMU(DMA翻译+隔离)、SR-IOV(PF/VF)、VFIO(用户态驱动) — `linux` `虚拟化` `直通` `IOMMU` `SR-IOV` `VFIO`

## Skills (Linux 操作系统)

- [linux-kernel-debugging](skills/linux-kernel-debugging.md) — 内核各子系统监控命令、常见问题排查路径与调试技巧：softirq/meminfo/Page Cache/IO/关机/cgroup/IPC — `linux` `内核` `调试` `监控` `性能分析`
- [linux-ipc-programming](skills/linux-ipc-programming.md) — System V IPC三大机制C编程实操：信号量集合+共享内存+消息队列的API速查与demo — `linux` `ipc` `编程` `信号量` `共享内存` `消息队列`
- [linux-lock-selection](skills/linux-lock-selection.md) — 内核锁类型选择决策树与API速查：Spinlock/Mutex/RCU等10种锁的适用场景与常见陷阱 — `linux` `内核` `锁` `spinlock` `mutex` `rcu` `同步`
- [linux-kernel-tracing](skills/linux-kernel-tracing.md) — 内核追踪实操手册：ftrace函数追踪→kprobe动态探针→perf事件采样→火焰图可视化四类场景 — `linux` `内核` `tracing` `ftrace` `kprobe` `perf` `火焰图`
- [linux-vmcore-debugging](skills/linux-vmcore-debugging.md) — vmcore崩溃分析实操：crash加载→堆栈回溯→寄存器解读→结构体分析→崩溃类型识别 — `linux` `vmcore` `crash` `崩溃分析` `寄存器` `内核调试`
- [linux-io-debugging](skills/linux-io-debugging.md) — IO性能排查与压测实操：iostat→fio→dd→blktrace→block_dump四步流程 — `linux` `io` `iostat` `fio` `blktrace` `dd` `性能分析`
- [linux-network-debugging](skills/linux-network-debugging.md) — 网络调试实操：tcpdump抓包分析（参数/表达式/实例）+ iperf打流测试 — `linux` `网络` `tcpdump` `iperf` `网络分析`
- [gdb-debugging-guide](skills/gdb-debugging-guide.md) — GDB调试实操速查：断点/观察点/执行控制/内存查看/多线程/多进程/Core Dump/QEMU调试 — `linux` `gdb` `调试` `QEMU` `断点` `观察点`

## Skills (Linux 虚拟化)

- [virsh-vm-management](skills/virsh-vm-management.md) — virsh管理KVM虚拟机的实操指南：生命周期、热迁移、CPU绑定等常用命令组合 — `linux` `虚拟化` `virsh` `运维` `操作手册`
- [linux-vm-debugging](skills/linux-vm-debugging.md) — 虚拟化调试实操：kvmtop EXT/%ST抢占/D状态vcpu/中断脚本/NUMA/QEMU gdb七大场景 — `linux` `虚拟化` `调试` `kvmtop` `虚拟机监控` `NUMA`

## Synthesis (Linux)

- [linux-os-virtualization-landscape](concepts/linux-os-virtualization-landscape.md) — OS+虚拟化+DFX导航枢纽：7个OS子领域+4个虚拟化子领域+7条OS→虚拟化映射+4个核心矛盾（同时在Concepts中索引） — `linux` `虚拟化` `全景图` `内核` `DFX`
- [linux-kernel-subsystem-interactions](synthesis/linux-kernel-subsystem-interactions.md) — Linux内核六大子系统交互机制：preempt_count统一上下文追踪、softirq跨子系统分发、Page Cache交汇点、锁跨上下文协调 — `linux` `内核` `子系统交互` `preempt_count` `softirq` `page-cache` `锁`
- [linux-dfx-tool-landscape](synthesis/linux-dfx-tool-landscape.md) — DFX调试工具全景图：六大领域(CPU/IO/内存/网络/追踪/vmcore)×三种模式(监控/追踪/事后)的工具矩阵与互补关系 — `linux` `DFX` `调试` `工具全景` `性能分析`
- [virtio-architecture-evolution](synthesis/virtio-architecture-evolution.md) — Virtio四种架构演进分析：数据面从软件模拟到硬件直通，性能与灵活性的核心矛盾 — `linux` `虚拟化` `virtio` `vhost` `DPDK` `vDPA`

## Concepts (数据结构与算法)

- [binary-tree-basics](concepts/binary-tree-basics.md) — 二叉树核心概念：三种形态、五个性质、链式/顺序存储、四种遍历方式与高频面试题型 — `数据结构` `二叉树` `遍历` `递归` `BST`
- [red-black-tree](concepts/red-black-tree.md) — 红黑树五大性质、与4阶B树等价性、12种插入+5类删除修复策略、AVL vs红黑树选型指南 — `数据结构` `红黑树` `AVL` `平衡树` `B树`
- [b-tree-bplus-tree](concepts/b-tree-bplus-tree.md) — B树与B+树的多路搜索结构、B+树更适合数据库索引的两大原因、B树vsB+树关键差异 — `数据结构` `B树` `B+树` `数据库索引` `磁盘IO`
- [graph-algorithms](concepts/graph-algorithms.md) — 图论核心算法全景：BFS/DFS遍历、最短路(Dijkstra/SPFA/Floyd)、拓扑排序、MST、并查集、Tarjan SCC、二分图匹配、网络流 — `数据结构` `图论` `BFS` `DFS` `最短路` `拓扑排序`

## Concepts (消息队列 & IO优化)

- [kafka-architecture](concepts/kafka-architecture.md) — Kafka分布式消息队列完整架构：ISR/HW/LEO可靠性+PageCache+零拷贝+顺序追加高性能三板斧 — `消息队列` `Kafka` `分布式` `高性能` `零拷贝`
- [mq-selection-comparison](concepts/mq-selection-comparison.md) — 三大MQ选型对比：Kafka(高吞吐低可靠)/RocketMQ(高可靠事务)/RabbitMQ(低延迟灵活路由) — `消息队列` `Kafka` `RocketMQ` `RabbitMQ` `选型`
- [zero-copy-memory-mapping](concepts/zero-copy-memory-mapping.md) — 零拷贝工具组：sendfile/splice/mmap/io_uring/DPDK各自解决不同瓶颈，选型先确认瓶颈再选工具 — `零拷贝` `sendfile` `mmap` `io_uring` `DPDK` `性能优化`

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

### RAG (检索增强生成)  — 6条（传统RAG 4条 + 高级RAG/GraphRAG 1条 + 向量库选型1条）

- [rag-engineering](concepts/rag-engineering.md) — RAG工程全景：从文档解析到答案评估的完整流水线，数据质量决定上限；文档解析+Chunking+Embedding(m3e)+混合检索+Rerank+5种高级范式+评估+三阶段落地路径+避坑清单 — `AI` `RAG` `检索` `向量库` `知识图谱`
- [rag-chunking-strategies](concepts/rag-chunking-strategies.md) — 21种RAG分块策略：基础→结构感知→语义驱动，分块决定检索质量 — `AI` `RAG` `Chunking` `分块` `文本分割`
- [rag-storage-technology](concepts/rag-storage-technology.md) — RAG存储四层架构：原始文件→元数据→切片(ES)→向量(Milvus/Qdrant/pgvector)，缺一层则功能失能 — `AI` `RAG` `存储` `向量库` `Elasticsearch`
- [rag-tools-landscape](concepts/rag-tools-landscape.md) — RAG工具链全景：7类解析工具+分块策略+Embedding选型+向量库+重排序——选型先确认瓶颈再选工具 — `AI` `RAG` `工具` `解析` `向量模型`
- [graphrag-engineering](concepts/graphrag-engineering.md) — GraphRAG用知识图谱解决全局型问题：实体→关系→Leiden社区摘要→全局/局部/DRIFT三种搜索，代价是LLM调用量大 — `AI` `RAG` `知识图谱` `GraphRAG` `社区检测`
- [vector-database-comparison](entities/vector-database-comparison.md) — 向量库选型：HNSW默认+DiskANN 10B+解+RaBitQ 32x压缩；Milvus/Qdrant/pgvector三强；混合检索是生产标配 — `AI` `RAG` `向量库` `Milvus` `Qdrant` `HNSW`

### Agent框架 (智能体/工具调用)  — 4条（含新的landscape导航页面）

- [agent-architecture-landscape](concepts/agent-architecture-landscape.md) — Agent架构7个子领域导航枢纽：树状拓扑+4个核心矛盾+子领域连接+LLM基础设施边界 — `AI` `Agent` `RAG` `知识图谱` `全景图`
- [agent-framework-engineering](concepts/agent-framework-engineering.md) — Agent五大支柱：工作流/状态/记忆/工具/协议，可靠Agent=可观测状态机 — `AI` `Agent` `LangGraph` `MCP` `工具调用`
- [tool-calling-mcp](concepts/tool-calling-mcp.md) — 工具调用与MCP：JSON Schema+结构化输出+MCP统一工具生态，协议与安全边界 — `AI` `Agent` `MCP` `Function Call` `工具调用`
- [multi-agent-framework-comparison](concepts/multi-agent-framework-comparison.md) — 四大Multi-Agent框架对比：LangGraph(可靠)/CrewAI(简单)/AutoGen(灵活)/AgentX(安全) — `AI` `Agent` `LangGraph` `CrewAI` `AutoGen`

### 评估系统 (评测/指标)  — 2条

- [evaluation-metrics](concepts/evaluation-metrics.md) — 分类评估指标核心：混淆矩阵→准确率/精确率/召回率/F1；类别不平衡时准确率失效；7个RAG检索排序指标(P@K/MRR/MAP/nDCG) — `AI` `评估` `混淆矩阵` `准确率` `精确率` `召回率`
- [llm-benchmarks](concepts/llm-benchmarks.md) — LLM评测基准六大维度：知识(MMLU/ARC)、推理(GSM8K/DROP/BBH)、对话(MT-bench)、抽取(MS-MARCO)、安全(TruthfulQA/HHH)、编程(HumanEval/MBPP) — `AI` `LLM` `评测` `Benchmark` `基准`

### 安全 (对抗攻击)  — 1条

- [agent-security](concepts/agent-security.md) — Claude Fable 5破解事件揭示LLM安全分类器4类绕过手法——安全是动态对抗而非静态防御 — `AI` `安全` `Agent` `对抗攻击`

### 数据飞轮 (正反馈循环)  — 1条

- [data-flywheel](concepts/data-flywheel.md) — 数据飞轮：数据和业务间的正反馈循环——AI辅助决策产出更多数据，更多数据强化AI决策，飞轮越转越快 — `AI` `数据飞轮` `数据要素` `知识管理` `企业数字化`

## Entities (AI)

### LLM基础设施  — 2条

- [vllm-sglang-tensorrt](entities/vllm-sglang-tensorrt.md) — 推理引擎四强对比：vLLM生态最强/SGLang延迟最优/TensorRT吞吐最高/TGI最稳 — `AI` `vLLM` `SGLang` `TensorRT-LLM` `推理引擎`
- [megatron-deepspeed](entities/megatron-deepspeed.md) — Megatron偏高性能内核/DeepSpeed偏显存优化易用性，选型取决于规模拓扑维护能力 — `AI` `Megatron` `DeepSpeed` `训练框架`

### Agent框架  — 2条

- [langchain-framework](entities/langchain-framework.md) — LangChain框架：Runnable+LCEL统一可执行单元，六大包分离架构 — `AI` `LangChain` `LCEL` `框架`
- [langgraph-framework](entities/langgraph-framework.md) — LangGraph工作流编排：有向图+状态持久化+循环支持，Agent从自由聊天升级为可观测状态机 — `AI` `LangGraph` `工作流` `状态机` `Agent`

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
- [container-network-benchmarking-skill](skills/container-network-benchmarking-skill.md) — 容器网络性能测试方法论：iperf3测吞吐+sockperf测P99+关闭TCP offload；六种方案实测数据 — `云原生` `容器` `网络` `性能测试` `iperf3`

## Synthesis (云原生)

- [k8s-cloud-native-landscape](concepts/k8s-cloud-native-landscape.md) — 云原生5子领域导航枢纽+4条Linux→云原生映射+3个核心矛盾（同时在Concepts中索引） — `云原生` `Kubernetes` `全景图` `导航`
- [cloud-native-infrastructure-landscape](synthesis/cloud-native-infrastructure-landscape.md) — 云原生三层架构全景：底层Linux内核特性→中间containerd/shim/runc→上层K8s编排+Service Mesh+GitOps+可观测 — `云原生` `Kubernetes` `容器` `全景图` `架构`

## Journal
