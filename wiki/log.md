---
title: Wiki Log
---

# Wiki Log

## [2026-06-01] init | Vault 创建
- vault_path="C:\Users\23363\Data\code\my-obsidian-wiki"
- wiki_dir=wiki categories=concepts,entities,skills,summaries,synthesis,journal,projects,recommendations
- raw/ 为只读区域，wiki/ 为 AI 自治区域

## [2026-06-01] restructure | 目录重构
- 将 references/ 重命名为 summaries/（与 karpathy wiki 命名一致）
- 添加 recommendations/ 目录（学习推荐报告）
- CLAUDE.md 重写为中文，纳入完整工作流规范

## [2026-06-01] enhance | CLAUDE.md 融入 obsidian-wiki 核心思想
- 新增来源标记（Provenance）：^[inferred]、^[ambiguous] 行内标记
- 新增类型化关系（Typed Relationships）：extends/implements/contradicts 等7种
- 新增置信度与生命周期（Confidence & Lifecycle）：base_confidence + lifecycle 状态机
- 新增重要性分层（Tier）：core/supporting/peripheral
- 新增 Delta 追踪（Manifest）：SHA-256 哈希检测内容变化
- 新增分级检索协议（Retrieval Primitives）：从 cheapest 到 expensive 逐步升级
- 新增页面模板（Page Template）：含 Open Questions、Sources、Provenance
- 新增目录：_meta/、_raw/、.manifest.json
- 操作模式明确化：Append/Rebuild/Restore

## [2026-06-01] ingest | System V IPC 概念页创建
- [2026-06-01T10:30] INGEST source_dir="Linux 操作系统/Linux 资源隔离/System V IPC" pages_created=1
- 新建页面：`concepts/linux-system-v-ipc.md`
- 来源文件：信号量、共享内存、消息队列、IPC namespace（共4篇）
- 核心内容：三大IPC机制对比、ipc_perm公共结构、SEM_UNDO机制、msgtyp过滤规则
- 关系链接：linux-namespace-cgroups（related_to）、linux-lock-mechanisms（related_to）

## [2026-06-01] ingest | Linux 操作系统（25个原始文件 → 14个wiki页面）
- INGEST mode=append source_dir="Linux 操作系统" pages_created=14 pages_updated=0
- 概念页面（9个）：
  - linux-interrupt-system — 中断系统：IRQ/softirq两阶段、preempt_count、三种延迟机制
  - linux-memory-management — 内存管理：meminfo参数、Page Cache、LRU、内存黑洞
  - linux-io-stack — IO栈：五层架构、IO调度器、gendisk
  - linux-boot-shutdown — 启动与关机：10步启动、多子系统协调
  - linux-network-stack — 网络栈：TCP/IP四层、三表、sk_buff、NAPI
  - linux-lock-mechanisms — 锁机制全景：Spinlock到RCU的选择指南
  - linux-namespace-cgroups — 资源隔离双引擎：Namespace+Cgroups
  - linux-process-scheduling — 进程调度：CFS红黑树与三种策略
  - linux-system-v-ipc — System V IPC：信号量/共享内存/消息队列
- 摘要页面（5个）：
  - linux-softirq-detail — 软中断实现细节
  - linux-meminfo-params — meminfo参数详解
  - linux-page-cache — Page Cache机制
  - linux-network-protocol-stack-impl — 网络协议栈实现
  - linux-rcu-lock — RCU锁详解
- 所有25个源文件已登记SHA-256哈希到 .manifest.json

## [2026-06-01] ingest | Linux 虚拟化（13个原始文件 → 10个新wiki页面 + 3个更新）
- INGEST mode=append source_dir="Linux 虚拟化" pages_created=10 pages_updated=3
- 概念页面（3个新建）：
  - linux-virtio-architecture — Virtio半虚拟化IO框架：前后端分离+四种架构演进
  - linux-interrupt-virtualization — 中断虚拟化三种场景+VGIC/KVM中断注入
  - linux-device-passthrough — IOMMU+SR-IOV+VFIO设备直通三大技术
- 概念页面（3个更新）：
  - linux-interrupt-system — 新增中断虚拟化交叉链接
  - linux-io-stack — 新增virtio架构交叉链接
  - linux-network-stack — 新增virtio-net/vhost交叉链接
- 摘要页面（3个新建）：
  - virtio-io-notification-mechanism — ioeventfd/irqfd双向零拷贝通知机制
  - virtio-vring-data-sharing — vring三大表生产者-消费者数据共享
  - linux-live-migration-flow — 热迁移三阶段流程+关键参数
- 实体页面（1个新建）：
  - libvirt-virsh — libvirt命令行管理工具
- 技巧页面（1个新建）：
  - virsh-vm-management — virsh虚拟机管理操作手册
- 综合页面（1个新建）：
  - virtio-architecture-evolution — Virtio四种架构演进跨领域分析
- 所有13个源文件已登记SHA-256哈希到 .manifest.json

## [2026-06-01] rebuild | Linux 操作系统重建（旧14页面归档 → 新14页面重蒸馏）
- REBUILD mode=rebuild source_dir="Linux 操作系统" pages_recreated=14 pages_archived=14
- 旧页面已归档至 wiki/_archives/2026-06-01-rebuild/
- 概念页面（9个重建）：
  - linux-interrupt-system — 重建：7个wikilinks、4个provenance标记、中断系统全景+软中断预算+延迟机制
  - linux-memory-management — 重建：5个wikilinks、5个provenance标记、内存管理+Page Cache+LRU+内存黑洞
  - linux-io-stack — 重建：7个wikilinks、IO栈五层+调度器+gendisk（源文件稀疏，confidence=0.571）
  - linux-boot-shutdown — 重建：5个wikilinks、10步启动+多子系统关机协调
  - linux-network-stack — 重建：7个wikilinks、TCP/IP+三表+sk_buff+NAPI+virtio交叉链接
  - linux-lock-mechanisms — 重建：7个wikilinks、Spinlock→RCU演进全景+选择指南
  - linux-namespace-cgroups — 重建：6个wikilinks、Namespace+Cgroups双引擎+System V IPC交叉
  - linux-process-scheduling — 重建：5个wikilinks、CFS红黑树+调度策略（源文件稀疏，confidence=0.538）
  - linux-system-v-ipc — 重建：5个wikilinks、三大IPC机制对比+API+内核实现
- 摘要页面（5个重建）：
  - linux-softirq-detail — 重建：softirq预算+preempt_count+ksoftirqd
  - linux-meminfo-params — 重建：meminfo字段+关键公式+内存黑洞
  - linux-page-cache — 重建：基数树+预读+Write Through/Back
  - linux-network-protocol-stack-impl — 重建：收发路径+sk_buff+NAPI
  - linux-rcu-lock — 重建：读零开销+宽限期+变体对比
- .manifest.json 已更新：25个源文件SHA-256哈希刷新

## [2026-06-01] ingest-step5 | Ingest第5步跨分类更新（补做）
- INGEST step=5 source_dir="Linux 操作系统" pages_created=4 pages_updated=0
- 技巧页面（3个新建）：
  - linux-kernel-debugging — 内核调试/监控实操手册（7类场景监控命令+排查路径）
  - linux-ipc-programming — System V IPC 编程教程（信号量/共享内存/消息队列C代码demo）
  - linux-lock-selection — 内核锁选择指南（决策树+API速查+常见陷阱）
- 综合页面（1个新建）：
  - linux-kernel-subsystem-interactions — 内核子系统交互全景（6大交互模式：preempt_count/softirq/Page Cache/锁/关机/容器）
- 触发依据：Ingest流程第5步触发条件表——skills(实操步骤+教程+排错指南)、synthesis(连接2+概念+跨领域洞察)

## [2026-06-02] ingest | DFX工具（29个原始文件 → 16个新wiki页面 + 1个更新）
- INGEST mode=append source_dir="DFX工具" pages_created=16 pages_updated=1
- 概念页面（4个新建）：
  - linux-tracing-frameworks — 内核追踪四大框架对比：ftrace/kprobe/perf/bpftrace
  - linux-cpu-performance-analysis — CPU性能分析：perf采样/kvmtop EXT/%ST抢占
  - linux-vmcore-analysis — vmcore崩溃分析：crash工具/寄存器/task/mm结构体
  - linux-io-performance-analysis — IO性能分析：iostat/fio/dd/blktrace/block_dump
- 实体页面（4个新建）：
  - perf-tool — perf性能分析工具（core tier：7个wikilinks）
  - crash-tool — crash vmcore分析工具
  - gdb-tool — GDB调试器（core tier：7个wikilinks）
  - flamegraph-tool — 火焰图可视化工具
- 摘要页面（7个新建）：
  - gdb-common-commands — GDB常用命令速查指南
  - linux-task-struct-mm-struct — task/mm/VMA/pgd四级链式结构
  - crash-register-address — x86_64/ARM64寄存器体系与调用约定
  - crash-vmcore-analysis — crash工具基本操作方法
  - linux-interrupt-monitoring-script — 中断数实时观测bash脚本
  - linux-ftrace-kprobe-overview — ftrace/kprobe/bpftrace框架概述
- 技巧页面（6个新建）：
  - linux-kernel-tracing — 内核追踪实操手册（ftrace→kprobe→perf→火焰图）
  - linux-vm-debugging — 虚拟机调试与监控实操手册（kvmtop/ST/D状态/中断/NUMA/QEMU gdb）
  - linux-vmcore-debugging — vmcore崩溃分析实操手册
  - linux-io-debugging — IO性能排查与压测实操手册
  - linux-network-debugging — 网络调试实操手册（tcpdump+iperf）
  - gdb-debugging-guide — GDB调试实操速查手册
- 综合页面（1个新建）：
  - linux-dfx-tool-landscape — DFX调试工具全景图（六领域×三模式矩阵+工具互补关系）
- 已有页面更新（1个）：
  - linux-kernel-debugging — 新增追踪框架和vmcore分析交叉链接+中断观测脚本引用
- 所有29个源文件已登记SHA-256哈希到 .manifest.json

## [2026-06-02] ingest | AI 人工智能（50个原始文件 → 17个新wiki页面）
- INGEST mode=append source_dir="AI 人工智能" pages_created=17 pages_updated=0
- 概念页面（12个新建）：
  - llm-infra-landscape — 大模型基础设施全景：五层工程栈+四个分水岭+中国全球两条栈
  - gpu-computing-architecture — GPU计算架构：CPU vs GPU本质差异+SM/Tensor Core/HBM+Roofline模型
  - cuda-software-stack — CUDA软件栈：cuBLAS/cuDNN/NCCL/Triton/CUTLASS分工
  - llm-training-pipeline — LLM训练流水线：四阶段训练栈（Pre-train→SFT→对齐→蒸馏）
  - llm-parallelism-strategies — 3D并行策略：DP/TP/PP/SP/EP/ZeRO按瓶颈组合
  - llm-inference-engine — LLM推理引擎基础：Prefill vs Decode+KV Cache+Continuous Batching
  - paged-attention-continuous-batching — PagedAttention+Continuous Batching：vLLM核心设计
  - llm-quantization-engineering — LLM量化工程：FP8/INT8/AWQ/GPTQ精度/成本/硬件权衡
  - moe-training-engineering — MoE训练工程：路由均衡+EP+All-to-All工程难点
  - rlhf-alignment-pipeline — RLHF与对齐：PPO/DPO/GRPO对比
  - rag-engineering — RAG工程全景：五代演进+完整流水线+GraphRAG
  - rag-chunking-strategies — RAG分块策略：21种方法从基础到语义驱动
  - agent-framework-engineering — Agent框架工程：五大支柱+ReAct vs LangGraph对比
  - tool-calling-mcp — 工具调用与MCP协议：Function Call+MCP统一生态+安全边界
  - llm-serving-infrastructure — 推理服务化：Triton/Ray Serve/PD分离+SLO管理
  - llm-gateway — 大模型网关：LiteLLM/OneAPI+路由/配额/缓存/Guardrails
  - llm-observability — LLM可观测性：性能/语义质量/成本三维+Langfuse/OpenLLMetry
- 实体页面（5个新建）：
  - langchain-framework — LangChain框架：Runnable+LCEL+六大包分离
  - langgraph-framework — LangGraph工作流编排：StateGraph+Checkpoint+Memory架构
  - vllm-sglang-tensorrt — 推理引擎四强对比：生态/延迟/吞吐/运维四维度选型
  - megatron-deepspeed — Megatron vs DeepSpeed：高性能内核 vs 显存优化易用性
  - graphify-gitnexus — Graphify vs GitNexus：认知整合 vs 工程执行
- 综合页面（1个新建）：
  - llm-infra-evolution-2022-2026 — 大模型基础设施四年四轮范式转移+DeepSeek-V4工程密度案例
- 所有50个源文件已登记SHA-256哈希到 .manifest.json

## [2026-06-02] ingest | 消息队列（4个原始文件 → 3个新wiki页面）
- INGEST mode=append source_dir="消息队列" pages_created=3 pages_updated=0
- 概念页面（3个新建）：
  - kafka-architecture — Kafka架构与高性能：ISR/HW/LEO可靠性+PageCache+零拷贝+顺序追加+稀疏索引+多Reactor
  - mq-selection-comparison — 三大MQ选型对比：Kafka(高吞吐低可靠)/RocketMQ(高可靠事务5万队列)/RabbitMQ(低延迟灵活路由)
  - zero-copy-memory-mapping — 零拷贝与内存映射技术全景：sendfile/splice/mmap/io_uring/DPDK工具组+Kafka+Nginx工程案例+数据库mmap争议
- 所有4个源文件已登记SHA-256哈希到 .manifest.json

## [2026-06-02] ingest | 云原生（21个原始文件 → 17个新wiki页面 + 1个更新）
- INGEST mode=append source_dir="云原生" pages_created=17 pages_updated=1
- 概念页面（10个新建）：
  - k8s-architecture — K8s声明式API+协调循环+控制面/数据面+Pod/Deployment/Service+架构变体+高级形态（core tier）
  - k8s-networking — K8s网络四层模型+五大CNI对比+iptables→IPVS→eBPF演进
  - k8s-security — K8s安全五维度加固+检查清单
  - k8s-cni-comparison — Flannel/Calico/Cilium/Weave/Kube-router选型决策树
  - container-runtime-deep-dive — 容器=拼装(8种Namespace+PID1陷阱+chroot逃逸+pivot_root+OCI规范)（core tier）
  - cgroups-v2-deep-dive — v2统一层级+memory三道防线+writeback-aware IO+PSI+CFS throttle
  - overlayfs-container-images — OverlayFS+Copy-on-Write(263倍差)+overlay2驱动+数据库放volume
  - seccomp-capabilities — Seccomp-BPF+Capabilities纵深防御+--privileged拆防线+cBPF vs eBPF
  - container-vs-microvm — 容器共享内核vs microVM独立内核+Firecracker 125ms+Kata Containers
  - container-network-benchmarking — veth+bridge吞吐-20%P99 4.4x+macvlan近裸机+Cilium不受规则影响
  - prometheus-architecture — Pull模型+ServiceMonitor CRD+Histogram vs Summary+TSDB
- 实体页面（2个新建）：
  - containerd-runtime — containerd三层类比(Nova/libvirtd/QEMU)+CRI内置+shim解耦（core tier）
  - runc-oci-reference — nsenter C代码+三次clone+两阶段init+exec FIFO+cgroup manager
- 摘要页面（3个新建）：
  - k8s-terminology-cheatsheet — K8s核心术语13类速查
  - k8s-official-architecture — K8s官方文档架构蒸馏
  - k8s-alibaba-cloud-principles — 阿里云K8S技术原理深度解读
- 技巧页面（2个新建）：
  - k8s-security-hardening — K8s安全加固实操指南(RBAC+NetworkPolicy+PSS+加密+API Server)
  - container-network-benchmarking-skill — 容器网络性能测试实操(iperf3+sockperf方法论)
- 综合页面（1个新建）：
  - cloud-native-infrastructure-landscape — 云原生三层架构全景图(底层内核→中间运行时→上层编排+可观测)
- 已有页面更新（1个）：
  - linux-namespace-cgroups — 新增容器运行时/Cgroups v2/Seccomp交叉链接
- 所有21个源文件已登记SHA-256哈希到 .manifest.json

## [2026-06-02] lint | Wiki健康检查
- [2026-06-02T14:00] LINT issues_found=38 orphans=15 broken_links=4 stale=26(13modified+13deleted) contradictions=3 prov_issues=19(3amb_high+15drift+4hub_inf) missing_summary=0 fragmented_clusters=2(linux:0.105,ai:0.134) visibility_issues=0 promotion_candidates=0 synthesis_gaps=3 relationship_issues=4 lifecycle_issues=0

## [2026-06-02] lint-fix | 创建3个缺失目标页面（修复4个broken wikilinks）
- LINT_FIX broken_links_fixed=3 pages_created=3
- 概念页面（2个新建）：
  - gpu-interconnect-networks — GPU互联两层架构+NVLink/IB/RoCE带宽+GPUDirect RDMA+拓扑选型
  - speculative-decoding-mtp — 推测解码+EAGLE/Medusa/MTP方法演进+batch vs加速+无损保证
- 实体页面（1个新建）：
  - vector-database-comparison — 向量库选型对比+HNSW/DiskANN/RaBitQ+Milvus/Qdrant/pgvector+混合检索

## [2026-06-03] lint-fix | P3过期源文件处理（manifest修正）
- LINT_FIX stale_fixed=26 manifest_keys_updated=13 hash_updated=13
- 修正类型：
  1. 12个Linux OS源文件：hash不匹配→实际为LF→CRLF行尾变更，内容无变化→更新manifest hash为当前CRLF版本
  2. 1个Prometheus源文件：hash不匹配→极小内容变更（1字节级别）+CRLF→更新manifest hash
  3. 12个从零造容器系列源文件：manifest key含错字（买→造、质拟→虚拟、淋襃→洋葱、什乕→什么、什乛→什么）→修正manifest key为实际文件名，内容hash无变化
- 结果：141个源文件全部 OK，0 stale，0 missing

## [2026-06-11] ingest | 数据结构与算法（6个原始文件 → 9个新wiki页面）

- INGEST mode=append source_dir="数据结构与算法" pages_created=9 pages_updated=0
- 概念页面（4个新建）：
  - binary-tree-basics — 二叉树核心：三种形态+五个性质+链式/顺序存储+四种遍历+面试题型
  - red-black-tree — 红黑树五大性质+4阶B树等价+12种插入+5类删除+AVL vs红黑树选型
  - b-tree-bplus-tree — B树/B+树多路搜索+数据库索引选型+B+两大优势
  - graph-algorithms — 图论算法全景：BFS/DFS→最短路→拓扑→MST→并查集→Tarjan→二分图→网络流
- 摘要页面（4个新建）：
  - binary-tree-basics-summary — 二叉树基础原文摘要
  - red-black-tree-detail — 红黑树详解原文摘要
  - avl-redblack-btree-intro — AVL/红黑树/B树介绍原文摘要
  - graph-algorithms-overview — 图论算法全景原文摘要
- 技巧页面（1个新建）：
  - graph-algorithm-learning-path — 图论算法学习路线与代码模板清单
- 综合页面（1个新建）：
  - balanced-tree-evolution — BST→AVL→红黑树→B+树平衡策略演进路线与选型决策树
- 跳过2个空/无实质内容文件：有向无环图.md(0 bytes)、算法合集.md(仅链接)
- 4个有实质内容文件已登记SHA-256哈希到 .manifest.json

- [2026-06-11T14:30] INGEST source="AI 人工智能/Agent架构/评估系统/如何理解准确率、精确率和召回率.md" pages_created=1 pages_updated=1 mode=append

## [2026-06-11] ingest | AI 人工智能增量（1新来源 + 3路径变更 + 2页面更新）

- INGEST mode=append source_dir="AI 人工智能" pages_created=1 pages_updated=2
- 概念页面（1个新建）：
  - data-flywheel — 数据飞轮：数据和业务正反馈循环，从知识循环进化到数据飞轮的五步构建法
- 已有页面更新（2个）：
  - rag-engineering — 大幅扩充：文档解析7类工具对比+Chunking工程细节+Embedding模型选型+混合检索融合方法+Rerank模型对比+三级漏斗+Query改写(HyDE/Multi-Query)5种方法+高级RAG范式(Self-RAG/CRAG/Adaptive/GraphRAG/Agentic)5种对比+评估两层指标+生产架构延迟预算+国内外生态对比+数据飞轮交叉链接
  - agent-framework-engineering — 新增数据飞轮交叉链接
- 文件路径变更（manifest key更新3个）：
  - Prompt 提示词.md：Prompt + RAG/ → Memory记忆/
  - BenchMarks汇总.md：AI infra/ → Agent架构/评估系统/
  - 新增 3-RAG 工程全景.md副本条目（与已有【17】RAG工程全景内容相同）
- 1个新源文件已登记SHA-256哈希到 .manifest.json

## [2026-06-11] cross-link-fix | 系统性跨页面链接遗漏修复

- CROSS_LINK_FIX files_updated=35 wikilinks_added=~60
- 扫描全部106个wiki页面，识别正文提及另一页面核心主题但缺wikilink的遗漏
- LLM基础设施链接网（10个文件，~29个链接）：infra-landscape/inference-engine/serving-infrastructure/observability/speculative-decoding/moe/cuda/vllm/langchain/llm-infra-evolution
- Linux内核跨子系统链接（25个文件，~31个链接）：network-stack→零拷贝/virtio→设备直通+cgroups→CFS/seccomp→eBPF/k8s-networking→Linux网络栈/kafka→Page Cache+工具实体交叉链接
- 所有35个文件updated字段已更新为2026-06-11

## [2026-06-03] lint-fix | P1孤立页面救援 + 矛盾标注
- LINT_FIX orphans_rescued=15 contradictions_annotated=3 pages_updated=46
- 孤立页面救援：
  - 从41个concept/summary/entity页面添加反向wikilinks指向15个orphan页面
  - 9个skills页面：linux-lock-selection、linux-kernel-tracing、linux-vm-debugging、linux-io-debugging、linux-network-debugging、linux-vmcore-debugging、k8s-security-hardening、container-network-benchmarking-skill、linux-ipc-programming
  - 5个synthesis页面：cloud-native-infrastructure-landscape、linux-dfx-tool-landscape、linux-kernel-subsystem-interactions、llm-infra-evolution-2022-2026、virtio-architecture-evolution
  - 1个entity页面：graphify-gitnexus
  - 结果：orphan数从15降到0
- 矛盾标注：
  1. k8s-security.md + k8s-security-hardening.md：aescbc EncryptionConfiguration示例标注⚠️——K8s官方推荐aesgcm或kms
  2. cgroups-v2-deep-dive.md：CPU limit争论标注^[ambiguous]——双面观点+共识倾向
  3. seccomp-capabilities.md + container-vs-microvm.md：修正关系类型contradicts→related_to/replaces——seccomp加固容器 vs microVM替代容器并非矛盾

## [2026-06-12] INGEST | 评估系统增量

- [2026-06-12T17:12] INGEST source="AI 人工智能/Agent架构/评估系统/RAGAS 评估框架.md" pages_created=1 pages_updated=1 mode=append
  - 新增：entities/ragas-framework.md — RAGAS RAG量化评估框架（4核心指标+自动造测试集+框架集成）
  - 更新：concepts/evaluation-metrics.md — 补充LLM评测基准和RAGAS的连接
- [2026-06-12T17:12] INGEST source="AI 人工智能/Agent架构/评估系统/大语言模型LLM的评测基准数据集（BenchMarks）汇总.md" pages_created=1 pages_updated=1 mode=append
  - 新增：concepts/llm-benchmarks.md — LLM评测基准六大维度全景（知识/推理/对话/抽取/安全/编程共20+基准）
  - 更新：concepts/evaluation-metrics.md — 补充LLM评测基准和RAGAS的连接

## [2026-06-13] INGEST | RAG目录变动更新

- [2026-06-13] INGEST source="AI 人工智能/Agent架构/RAG/传统RAG/2-RAG 全栈介绍.md" pages_created=0 pages_updated=1 mode=append
  - 变动：原文SHA-256变更(8a8db40→20cbef0)，文件大小从30595→29737 bytes
  - 更新：concepts/rag-engineering.md — 补充m3e Embedding模型、三阶段落地路径、避坑清单

## [2026-06-13] PATH_FIX | 全量路径引用修复

- [2026-06-13] 全量审计raw/sources路径一致性，修复21个wiki页面的source_dir/source_files引用
- 模式A(缺少云原生/前缀)：8个K8s页面 + 9个容器运行时页面 + 1个Prometheus页面 = 18页
- 模式B(Linux操作系统过浅)：2个跨目录整合页面(linux-kernel-debugging/linux-kernel-subsystem-interactions)，source_files补充子目录路径
- 模式D(大小写)：llm-benchmarks.md的Benchmarks→BenchMarks
- 模式E(JSON结构)：数据结构与算法6个条目从sources对象外部移入内部
- RAG路径迁移（上次已完成）：7个manifest键 + 2个wiki页面frontmatter + 6处prose来源
- 验证结果：manifest 0 mismatch, wiki source_ref 0 mismatch ✅

## [2026-06-13] INGEST | Agent架构增量（15新来源 + 1空文件 → 5新页面 + 7更新）

- INGEST mode=append source_dir="AI 人工智能/Agent架构" pages_created=5 pages_updated=7

## [2026-06-13] STRUCTURE | Agent架构领域分类显式化

- STRUCTURE pages_created=1 pages_updated=2
- 新建页面（1个）：
  - agent-architecture-landscape — Agent架构7个子领域导航枢纽：树状拓扑+4核心矛盾+子领域连接+LLM基础设施边界
- index.md重构（AI部分）：
  - Concepts (AI)：27条扁平列表 → 6个子标题分组（LLM基础设施15条+RAG 6条+Agent框架4条+评估2条+安全1条+数据飞轮1条）
  - Entities (AI)：6条扁平列表 → 4个子标题分组（LLM基础设施2条+Agent框架2条+RAG 1条+知识图谱1条）
  - 新增 Synthesis (AI)：llm-infra-evolution-2022-2026从通用Synthesis移入
- 概念页面（5个新建）：
  - graphrag-engineering — GraphRAG工程：6个源文件蒸馏，微软14步管线+蚂蚁统一架构+6大项目PK+全局/局部/DRIFT搜索
  - rag-storage-technology — RAG存储四层架构：原始文件+元数据+切片+向量，缺一层功能失能
  - rag-tools-landscape — RAG工具全景：7类解析+分块+Embedding+向量库+重排序
  - multi-agent-framework-comparison — 四大Multi-Agent对比：LangGraph/CrewAI/AutoGen/AgentX
  - agent-security — Agent安全与对抗：Claude Fable 5破解4类手法+纵深防御
- 已有页面更新（7个）：
  - rag-engineering — 新增GraphRAG/存储/工具交叉链接+来源文件
  - rag-chunking-strategies — 新增图解11种策略+代码示例21种方法
  - evaluation-metrics — 新增RAG检索排序7指标+评测完整指南
  - agent-framework-engineering — 新增Multi-Agent对比交叉链接
  - graphify-gitnexus — 新增Graphify原理7步流程+God Nodes/Surprising Connections
  - langgraph-framework — updated字段更新
  - ragas-framework — updated字段更新
- 跳过1个空文件：ACL访问控制.md(0 bytes)
- 15个有实质内容文件已登记SHA-256哈希到 .manifest.json

## [2026-06-13] STRUCTURE | Linux OS/虚拟化领域分类显式化

- STRUCTURE pages_created=1 pages_updated=1 (index.md重构)
- 新建页面（1个）：
  - linux-os-virtualization-landscape — OS+虚拟化+DFX导航枢纽：7个OS子领域+4个虚拟化子领域+7条OS→虚拟化映射+4个核心矛盾（性能vs隔离、通用vs专用、硬件vs软件、完整vs增量）
- index.md重构（Linux部分）：
  - 原：扁平通用分组（Summaries 18条含14条Linux、Entities 5条全Linux、Concepts 16条含13条Linux+3虚拟化、Skills 11条含10条Linux、Synthesis 4条含3条Linux）
  - 新：7个专用分组（Summaries(Linux) 14条、Entities(Linux) 5条、Concepts(Linux操作系统) 14条含landscape、Concepts(Linux虚拟化) 3条、Skills(Linux操作系统) 8条、Skills(Linux虚拟化) 2条、Synthesis(Linux) 4条含landscape）
  - 通用分组只保留数据结构与算法（Summaries 4条、Concepts 4条、Skills 1条、Synthesis 1条）

## [2026-06-13] STRUCTURE | 云原生领域分类显式化

- STRUCTURE pages_created=1 pages_updated=1 (index.md云原生部分重构)
- 新建页面（1个）：
  - k8s-cloud-native-landscape — 云原生5子领域导航枢纽：K8s核心(4)+容器运行时(6)+可观测(1)+实体(2)+摘要(3)+技巧(2)+综合(2)，4条Linux→云原生映射(Namespace→视图隔离/Cgroup→资源限制/OverlayFS→镜像/Seccomp→安全防线)，3个核心矛盾(共享vs独立内核/声明式vs命令式/服务网格vs不侵入)
- index.md重构（云原生部分）：
  - 原：Concepts (云原生) 11条扁平列表
  - 新：Concepts (云原生) → 3个子标题分组（K8s核心5条含landscape + 容器运行时6条 + 可观测1条），Synthesis (云原生) 新增landscape引用
  - 与AI/Linux处理方式一致：先landscape导航页+后子领域分组

## [2026-06-13] LEARN | Harness Engineering 学习推荐

- LEARN topic="Harness Engineering" category=原理介绍/技术分析/架构图
- [2026-06-13T12:05] LEARN 主题确认：优先了解章节指定 Harness Engineering
- 已有知识分析：Wiki 已有 Agent框架工程/持久化执行/工具调用/MCP/LangGraph 等基础，但 Harness Engineering 作为独立工程范式全面缺失
- 联网搜索：tavily-search 4轮（英2+中2），发现30+篇高质量博客
- 延伸方向：1.Long-Running Agent持久化架构（Initializer+Coding Agent） 2.Feedforward/Feedback双回路设计
- 推荐报告：12篇深度推荐+核心术语表+三层范式对比+跨领域关联
- 博客下载：15篇成功下载（Self learn/Harness Engineering/），2篇失败（HackMD/BusinessNext SPA防爬）
- 报告保存：wiki/recommendations/2026-06-13.md