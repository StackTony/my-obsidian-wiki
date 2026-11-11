---
title: Wiki Log
---

# Wiki Log

## [2026-08-03] INGEST | AI Agent 协议+平台 增量（11新来源+74 CRLF重命名 → 7新页面+3更新）

- [2026-08-03T15:00] INGEST mode=append source_dir="AI 人工智能/AI Agent" pages_created=7 pages_updated=3
- 新建页面（7个）：
  - concepts/agent-communication-protocols — 三大Agent协议（MCP/ACP/A2A）三层协议栈：工具驱动层+协作通信层+公共发现层
  - concepts/agent-development-platforms-landscape — 10+Agent开发平台全景图：5分类（自主执行/可视化编排/通用框架/多Agent协作/有状态Agent）+选型决策树
  - summaries/a2a-protocol — A2A协议原文摘要：Agent Card/Task/Message/Part/Artifact+JSON-RPC方法
  - summaries/acp-protocol — ACP协议原文摘要（上下篇整合）：REST架构+三种部署模式+离线发现
  - summaries/ai-protocols-comparison — 三大AI协议对比原文摘要：MCP外接大脑+ACP本地对讲机+A2A国际通用语
  - summaries/agent-development-platforms-top10 — 10个Agent开发平台原文摘要：AutoGPT/Dify/LangChain/MetaGPT等
  - entities/headroom-tool — Headroom上下文压缩中间件：ContentRouter+5策略+92%SRE日志token节省
- 已有页面更新（3个）：
  - concepts/tool-calling-mcp — 新增"MCP在三大Agent协议中的定位"章节+source_files扩展至5个协议文件+base_confidence 0.75→0.80
  - concepts/agent-system-architecture — source_files更新（消息总线文件重命名：架构设计解析→系统架构设计）
  - summaries/agent-message-bus-architecture — source_files更新（文件重命名同步）
- 跳过4个稀薄文件：Demo进阶指南/多Agent协作github项目/自动化研究skill/codebase-memory-mcp（≤100字节，仅含URL）
- 74个CRLF行尾转换文件：manifest哈希全量更新（无实际内容变化，避免重复ingest）
- 1个文件重命名：Agent 架构设计解析 → Agent 系统架构设计（消息总线），内容字节相同，manifest条目迁移
- manifest: 198 total sources（was 188）

## [2026-06-29] UPDATE | Graphify与GitNexus实体页更新
- [2026-06-29T09:00] UPDATE source="AI 人工智能/AI Agent/知识图谱/Graphify和Gitnexus.md" pages_updated=1
  - entities/graphify-gitnexus.md — 新增GitNexus CLI命令表、MCP工具体系（核心/API/仓库组3类）、Web界面和本地后端模式、设计哲学差异详细展开；source_dir从Agent架构更新为AI Agent

## [2026-06-29] INGEST | AI Agent 增量（2新来源+7修改 → 3新页面+7更新）+ 目录迁移Agent架构→AI Agent

- INGEST mode=append source_dir="AI 人工智能/AI Agent" pages_created=3 pages_updated=7
- 新建页面（3个）：
  - concepts/agent-system-architecture — Agent系统架构设计：执行循环+消息总线+Skill/Memory/Sub-agent
  - summaries/agent-system-architecture-design — Agent执行循环原文摘要
  - summaries/agent-message-bus-architecture — 消息总线架构原文摘要
- 已有页面更新（7个）：
  - entities/langchain-framework — 新增14篇设计原理分析系列+六大核心问题+Memory系统+Agent架构细节
  - entities/langgraph-framework — 新增工作流编排演进+状态/状态图/工作流三层概念+四种驱动机制
  - concepts/agent-framework-engineering — 新增Skill vs Tool区分+Sub-agent机制交叉引用+agent-system-architecture链接
  - concepts/agent-architecture-landscape — 新增Agent系统架构设计导航节点
  - concepts/rag-chunking-strategies — 新增ChineseRecursiveTextSplitter实现细节
  - entities/graphify-gitnexus — 新增GitNexus完整CLI/MCP/API工具体系+扩展对比
- 目录迁移：manifest全部40+条目从Agent架构→AI Agent，wiki页面source_dir同步更新23个页面
- 跳过1个稀薄文件：Claude Code/未命名.md（43字节，仅含链接）
- 9个源文件已登记SHA-256哈希到 .manifest.json

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

- [2026-06-11T14:30] INGEST source="AI 人工智能/AI Agent/评估系统/如何理解准确率、精确率和召回率.md" pages_created=1 pages_updated=1 mode=append

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

- [2026-06-12T17:12] INGEST source="AI 人工智能/AI Agent/评估系统/RAGAS 评估框架.md" pages_created=1 pages_updated=1 mode=append
  - 新增：entities/ragas-framework.md — RAGAS RAG量化评估框架（4核心指标+自动造测试集+框架集成）
  - 更新：concepts/evaluation-metrics.md — 补充LLM评测基准和RAGAS的连接
- [2026-06-12T17:12] INGEST source="AI 人工智能/AI Agent/评估系统/大语言模型LLM的评测基准数据集（BenchMarks）汇总.md" pages_created=1 pages_updated=1 mode=append
  - 新增：concepts/llm-benchmarks.md — LLM评测基准六大维度全景（知识/推理/对话/抽取/安全/编程共20+基准）
  - 更新：concepts/evaluation-metrics.md — 补充LLM评测基准和RAGAS的连接

## [2026-06-13] INGEST | RAG目录变动更新

- [2026-06-13] INGEST source="AI 人工智能/AI Agent/RAG/传统RAG/2-RAG 全栈介绍.md" pages_created=0 pages_updated=1 mode=append
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

- INGEST mode=append source_dir="AI 人工智能/AI Agent" pages_created=5 pages_updated=7

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

## [2026-06-13] LINT_FIX | Orphan救援 + Broken wikilink修复

- LINT_FIX orphans_rescued=5 broken_links_fixed=1 pages_updated=7
- Orphan修复（5个页面添加入链）：
  - agent-architecture-landscape ← tool-calling-mcp, llm-infra-landscape, agent-framework-engineering（从0到3入链）
  - k8s-cloud-native-landscape ← k8s-architecture, container-runtime-deep-dive（从0到2入链）
  - linux-os-virtualization-landscape ← linux-interrupt-system, linux-memory-management（从2到4入链）
  - balanced-tree-evolution ← red-black-tree（从0到1入链）
  - graph-algorithm-learning-path ← graph-algorithms（从0到1入链）
- Broken wikilink修复（1个）：
  - linux-os-virtualization-landscape relationships中 `[[concepts/cloud-native-infrastructure-landscape]]` → `[[synthesis/cloud-native-infrastructure-landscape]]`（frontmatter agent已修复）

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

## [2026-06-15] LEARN | Harness Engineering 学习推荐（第二次）

- LEARN topic="Harness Engineering" category=原理介绍/技术分析/架构图
- [2026-06-15T11:10] LEARN 延续06-13推荐，搜索2026.06新内容
- 新发现：9篇新博客（arXiv学术定义/Meta-Harness/Loop Engineering/Ralph Loop实践/CDLC+Context Flywheel/自定义Harness/SF现场调研/设计师视角）
- 新概念：Meta-Harness（Databricks Omnigent）、Loop Engineering（MindStudio）、CDLC/Context Flywheel（Tessl/Debois）
- 博客下载：9篇新增（Self learn/Harness Engineering/），总计24篇
- 延伸方向更新：1.Harness→Meta-Harness架构演进 2.CDLC×Harness Feedback
- 报告保存：wiki/recommendations/2026-06-15.md

## [2026-06-15] INGEST | DFX工具-网络增量（Bonding调试日志）

- [2026-06-16T11:45] DAILY-UPDATE fresh=155 stale=10 missing=3 index_added=11 index_removed=0 hot_refreshed=false

- [2026-06-15T10:00] INGEST source="DFX工具/==网络==/内核网络Bonding调试日志.md" pages_created=1 pages_updated=4 mode=append
  - 新增：summaries/kernel-bonding-debug-log.md — 内核Bonding调试日志开启方法（printk+dynamic debug）
  - 更新：skills/linux-network-debugging.md — 新增Bonding调试日志实操步骤+常见问题
  - 更新：concepts/linux-tracing-frameworks.md — 新增dynamic debug作为第五种追踪框架+对比表格+使用示例
  - 更新：concepts/linux-network-stack.md — 新增Bonding交叉引用+未解问题
  - 更新：skills/linux-kernel-debugging.md — 新增dynamic debug和printk级别调整进阶用法

## [2026-06-16] INGEST | Harness工程+Claude Code+高级RAG+向量数据库+LangGraph Memory 增量

- INGEST mode=append pages_created=2 pages_updated=5
- 新建页面（2个）：
  - concepts/harness-engineering — Harness Engineering（驾驭工程）：Agent=Model+Harness，四大支柱（上下文工程/架构约束/反馈循环/熵管理），六大行业共识，三阶段落地路线图，四大实战案例（OpenAI百万行代码/Anthropic C编译器/LangChain排名30→5/Can Boluk Hashline协议）
  - entities/claude-code — Claude Code：极简while循环架构(N0引擎)+信任模型哲学+Bash核心工具+六层记忆系统+子代理上下文隔离+技能+Hook+蚂蚁喂养开发哲学
- 已有页面更新（5个）：
  - concepts/rag-engineering — 新增"下一代RAG演进方向"章节：GraphRAG+HyDE+Self-RAG+Code-RAG+行业黑话+多模态RAG七大演进方向
  - entities/vector-database-comparison — 新增"HNSW原理实践与局限"和"向量数据库的局限与务实选型"两大章节：HNSW检索过程+灵积DashScope全栈工具链+四大局限+混合检索务实之选
  - entities/langgraph-framework — Memory架构从简述扩充为完整分类：短期记忆(Checkpoint+管理长对话3技术)+长期记忆(Store+写入2方式+管理2方式+表示2方式)
  - concepts/red-black-tree — 更新日期+标记源文件替换
  - concepts/agent-architecture-landscape — 新增Harness Engineering+Claude Code导航节点+交叉链接
- 交叉链接更新（2个）：
  - concepts/agent-framework-engineering — 新增Harness Engineering延伸阅读链接
  - concepts/agent-architecture-landscape — 新增harness-engineering/claude-code relationships
- 7个新源文件已登记到 .manifest.json（Harness工程4篇+Claude Code 2篇+记忆系统1篇+高级RAG 1篇+向量数据库2篇+LangGraph Memory 1篇）

- [2026-06-18T15:55] DAILY-UPDATE fresh=167 stale=9 missing=4 index_added=0 hot_refreshed=true

## [2026-06-18] manifest-fix | 4个missing源清理 + 红黑树源文件替换登记

- MANIFEST_FIX missing_resolved=4 pages_updated=3
- 处理详情：
  1. `Agent记忆-LangGraph官方-Memory架构.md` → `LangGraph-Agent记忆Memory架构.md`（文件重命名，key+hash更新）
  2. `RAG Chunk分块策略.md` → 拆分为 `RAG Chunk分块策略-代码示例.md` + `RAG Chunk分块策略-图解.md`（旧key删除，2个新key+hash注册）
  3. `红黑树详解.md` → `红黑树讲解.md`（源文件替换，key+hash+size更新）
  4. `_wiki_synthesis/agent-architecture-landscape` — 已有note标记说明非raw源文件，保留不变
- Wiki页面更新（3个frontmatter修正）：
  - concepts/red-black-tree.md — source_files: 红黑树详解.md → 红黑树讲解.md + updated日期

## [2026-06-22] INGEST | SAG + RAG常用框架 + 软件工程 + pending-hash修正

- INGEST mode=append pages_created=2 pages_updated=4
- 新建页面（2个）：
  - concepts/sag-sql-retrieval-augmented-generation — SAG（SQL检索增强生成）：SQL+向量混合检索替代GraphRAG全局图构建，查询时用SQL join临时激活局部Hyperedge结构，MuSiQue多跳Recall@5达80%
  - concepts/ood-principles-and-patterns — 面向对象设计原则与模式：六大设计原则+9种架构模式+23种GoF设计模式，软件设计是对"变化"的辩证处理
- 已有页面更新（4个）：
  - concepts/graphrag-engineering — 新增SAG作为GraphRAG替代范式对比+延伸阅读链接
  - concepts/rag-engineering — 新增SAG段落到"下一代RAG演进方向"章节
  - concepts/rag-tools-landscape — 新增7个RAG开源框架对比表格+RAG常用框架大全来源文件+SAG延伸阅读链接
  - wiki/index.md — 新增SAG条目(RAG从6→7条)+软件工程新分类+更新摘要描述
- Manifest修正（10个pending-hash→真实SHA-256）：
  - Harness工程4篇+Claude Code 2篇+记忆系统1篇+高级RAG 1篇+向量数据库2篇
- 6个新源文件已登记到 .manifest.json
  - summaries/red-black-tree-detail.md — source_files + 正文路径引用更新 + updated日期
  - synthesis/balanced-tree-evolution.md — source_files: 红黑树详解.md → 红黑树讲解.md + updated日期

## [2026-06-25] LEARN | Loop Engineering 学习推荐

- LEARN topic="Loop Engineering" category=原理介绍/技术分析/架构图
- [2026-06-25T14:30] LEARN 主题确认：优先了解章节指定 Loop Engineering
- 已有知识分析：Wiki 已有 Harness Engineering 页面（06-16 创建），但 Loop Engineering 作为第四代独立范式全面缺失
- 联网搜索：tavily-search 4轮（英2+中2），发现15+篇高质量博客
- 新发现：Loop Engineering 在2026年6月7-8日正式命名（Peter Steinberger推文800万浏览+Boris Cherny"我的工作是写Loop"+Addy Osmani命名文章），已成为AI工程第四代范式
- 延伸方向：1.Loopcraft堆叠循环与嵌套设计（Swyx） 2.验证器工程（Verifier Engineering=瓶颈）
- 推荐报告：12篇深度推荐+核心术语表（Loop Engineering/五要素/四代演进/Loopcraft/Salty Lesson/验证器瓶颈/Hill Climbing Loop/on-the-loop/认知投降/理解腐烂/Loop四条件测试/企业级运行时）
- 博客下载：3篇下载（Self learn/Loop Engineering/：AddyOsmani/LangChain/TrueFoundry），8篇tavily提取全文但defuddle下载失败
- 报告保存：wiki/recommendations/2026-06-25.md

## [2026-06-27] INGEST | Multi-Agent协同增量（1路径变更+2新来源 → 2新页面 + 7更新）

- INGEST mode=append source_dir="AI 人工智能/AI Agent/Multi-Agent协同" pages_created=2 pages_updated=7
- 新建页面（2个）：
  - entities/oh-my-opencode — Oh My OpenCode多Agent编排实体：四大支柱架构+希腊神话11agent体系+Sisyphus/Hephaestus双轨哲学+Prometheus三段式质量链+Hashline Edit防幻觉+Ralph Loop自动续跑+三级并发控制+tmux可视化+Claude Code兼容层+8大创新亮点
  - concepts/multi-agent-orchestration — Multi-Agent协同编排7个设计模式：角色分化与工具隔离、主编排+子执行分层、双轨主Agent、证据驱动完成、并发控制与防递归委派、completion_promise续跑、AgentPromptMetadata自描述
- 已有页面更新（7个）：
  - concepts/multi-agent-framework-comparison — 新增OMO实践案例段+延伸阅读扩展+来源更新+source_dir路径修正（Agent智能体→Multi-Agent协同）
  - concepts/agent-framework-engineering — 新增Multi-Agent协同编排7个设计模式段落+延伸阅读扩展
  - concepts/harness-engineering — 新增OMO作为Harness Engineering实践案例段落（四大支柱对照表）
  - concepts/agent-architecture-landscape — 导航树新增Multi-Agent编排节点+Agent工具新增OMO节点
  - entities/claude-code — 新增"与Oh My OpenCode的关系"段落+relationships新增oh-my-opencode
  - entities/langgraph-framework — relationships新增oh-my-opencode related_to
  - wiki/index.md — Agent框架从5→7条+实体新增OMO条目
- 跳过1个稀薄文件：单Agent 智能体.md（286字节，仅含2个GitHub链接，内容不足以独立建页，作为来源引用记入multi-agent-orchestration）
- Manifest更新：旧key迁移（Agent智能体→Multi-Agent协同）+ 2个新源文件SHA-256注册
- [2026-09-10 QUERY query="IO 阻塞不返回，如何查看确认进程卡在哪个内核调用上" result_pages=4 mode=normal escalated=false

## [2026-10-21] INGEST | 内存/调度/零拷贝/devmem 增量（8来源 → 6新页面 + 5更新）

- INGEST mode=append sources=8 pages_created=6 pages_updated=5
- delta来源（8个）：Linux 操作系统/Linux 内存管理/Linux 内存与CPU之间的关系.md、Linux 操作系统/Linux 内存管理/Linux 内存管理 TLB.md、Linux 操作系统/Linux 内核 IO 栈/Linux 零拷贝（Zero-Copy）.md、Linux 操作系统/Linux 进程调度/Linux CFS调度器.md、Linux 操作系统/Linux 进程调度/Linux 完全公平调度器CFS.md、DFX工具/==vmcore解析==/内核调试之devmem直接读写寄存器.md、Obsidian使用/claude的json备份.md、Obsidian使用/opencode的json备份.md
- 新建页面（6个）：
  - summaries/linux-memory-cpu-relationship — 教材式虚拟内存原理：地址空间→空闲内存五种适配算法→分页与页表项→TLB→多级/倒排页表→九种页面置换算法（最优=老化+WSClock）
  - summaries/linux-tlb-management — TLB表项结构、ARM Cortex-A72两级TLB、global/local刷新策略、多核TLB shootdown、PCID与ASID、Linux 4.15全面启用PCID
  - summaries/linux-zero-copy-impl — CPU COPY vs DMA COPY分工、read+send 4次拷贝/4次切换、sendfile(2.1) 3次拷贝、sendfile+SG-DMA(2.4) 0次CPU拷贝
  - summaries/linux-cfs-scheduler-impl — vruntime换算公式、调度周期/粒度(6ms与0.75ms、多核×(1+log2 ncpus))、rq/cfs_rq/sched_entity/sched_class结构、五调度类与六策略枚举
  - summaries/kernel-devmem-register-access — devmem用法、/dev/mem依赖与内核配置项、open("/dev/mem")+mmap实现原理
  - concepts/virtual-memory-and-paging — 新增概念页（跨两来源整合）：抽象演进→分页/页表项→TLB→多级/倒排页表→置换算法→与Linux实现的对应表
- 已有页面更新（5个）：
  - concepts/linux-process-scheduling — 新增"调度类与优先级体系"(stop>dl>rt>fair>idle)与"CFS实现要点"(vruntime公式/周期粒度/数据结构/关键函数)；"三种调度策略"重构为"六种调度策略"并标注口径差异 ^[ambiguous]；base_confidence 0.538→0.77
  - concepts/linux-memory-management — 新增"分页、页表与 TLB（下层基础）"段；LRU段关联工作集/老化算法；修正2处"鈴表"错字；source_files +2
  - concepts/zero-copy-memory-mapping — 新增"CPU COPY 与 DMA COPY"前提段、read+send逐步拆解表、sendfile 2.1/2.4演进表
  - concepts/linux-vmcore-analysis — 新增"devmem 直接读写寄存器"段与 crash/devmem 定位差异表；source_files +1
  - skills/linux-vmcore-debugging — 新增步骤9"在线验证寄存器（devmem）"；source_files +1
- 跨目录来源处理：zero-copy（消息队列/ + Linux 内核 IO 栈/）与 devmem（DFX工具/==vmcore解析==/）无共同前缀，未强行合并 source_dir，改为在"来源"段显式列出 raw 路径 + manifest 记录产出页面
- 跳过建页（2个）：Obsidian使用/claude的json备份.md、Obsidian使用/opencode的json备份.md —— 内容为工具配置备份且含明文密钥，按"配置非知识"处理，仅登记 manifest，不作内容转录
- 安全告警：上述2个JSON备份含明文 ANTHROPIC_AUTH_TOKEN、tavily api_key 与内网代理地址，已随 commit af72905 提交并推送至 github.com:StackTony/my-obsidian-wiki；raw/ 不可变，未做任何修改，已上报用户处置
- Manifest更新：新增8条（6个document + 2个config），last_ingest 2026-09-16→2026-10-21
- 索引/hot更新：index.md 新增5条摘要+1条概念、更新4条既有描述；hot.md 语义快照刷新
- Tier提升（lint规则13，入链≥5）：concepts/linux-process-scheduling（14入链）、concepts/linux-vmcore-analysis（8入链）由 supporting → core
- 事实校正：SCHED_IDLE 与 idle_sched_class 并非同一件事（前者由 fair 类极低权重实现，后者服务每 CPU idle 线程），已在概念页与摘要页标注 ^[ambiguous]
- 跳过项：QMD_WIKI_COLLECTION 未设置（无 .env），按 GUARD 跳过 QMD 刷新
- 未处理（需用户决策）：manifest 顶层 vault_path 仍为过期旧路径 `C:\Users\23363\Data\code\my-obsidian-wiki`，非本次 ingest 范围

## [2026-11-06] INGEST | 物理硬件域首批来源入库（10来源 → 15新页面 + 4更新）

- [2026-11-06T11:45] INGEST mode=append sources=10 pages_created=15 pages_updated=4
- delta来源（10个，全部为新目录 raw/sources/物理硬件/，manifest此前零记录）：PCIe/PCIE错误类型与NVMe掉盘根因诊断指南.md、PCIe/NVMe掉盘真相：PCIe链路错误与AER诊断关系.md、PCIe/芯片功耗.md、串口/BMC介绍.md、串口/IPMI的SOL (Serial Over LAN)原理与使用.md、光模块/光模块简介.md、内存/ECC纠错机制.md、内存/内存频率SPD、XMP.md、磁盘/TRIM擦除指令.md、网卡/网卡中断绑定 smp irq affinity介绍.md
- 新建页面（15个）：
  - summaries/pcie-error-nvme-drive-loss-guide — 两篇PCIe文章合并蒸馏（381行指南+37行精要版高度重叠，合并为一个summary，源文件双列source_files）
  - concepts/pcie-error-aer-nvme-drive-loss — CE/NFE/FE三级错误对应协议栈容错层级、掉盘机制链(Controller Reset 0x04)、观测盲区(链路错误不进SMART)、oaes字段、ASPM双刃剑
  - skills/nvme-pcie-drop-troubleshooting — 四步排查(lspci初筛→AER+dmesg时间戳对齐→nvme-cli深挖→最小系统隔离)+四场景速查+PRS看板
  - summaries/ssd-trim-command — TRIM原理与检测/启用命令
  - concepts/ssd-trim-write-amplification — NAND页读块擦不对称→read-modify-write→写放大→TRIM信息下推；无TRIM vs 有TRIM路径对比表
  - summaries/nic-smp-irq-affinity — SMP IRQ Affinity、smp_affinity位掩码、RPS/RFS、irqbalance使用经验
  - entities/bmc-baseboard-management-controller — BMC实体页：IPMI/SOL/KVM-over-IP/SNMP/Redfish五接口生态
  - entities/optical-transceiver-module — 光模块实体页：TOSA/ROSA/BOSA、PIN vs APD、TIA/CDR、SFP封装、收发链
  - summaries/ipmi-sol-usage — SOL原理+grub/ESXi控制台重定向+ipmitool用法+RMCP+失败三因
  - skills/ipmi-sol-remote-console — SOL五步配置实操（BMC→UEFI→OS→连接→排错）
  - summaries/bmc-intro — BMC与BIOS分工+五接口一览
  - summaries/optical-module-basics — 光模块组成/封装/工作原理
  - summaries/memory-spd-xmp — SPD EEPROM自描述+XMP官方超频预设
  - concepts/memory-spd-xmp-ecc — 内存硬件三件事整合：SPD自描述/XMP预设/ECC纠错(CRC vs 汉明码对比表)
  - synthesis/hardware-layer-debugging-landscape — 硬件问题在软件指标中显形的五条规律：静默失败链、信息断层下推、亲和性杠杆、带外观察平面、功耗换时延
- 已有页面更新（4个）：
  - concepts/linux-interrupt-system — 新增"SMP IRQ Affinity—硬中断的CPU亲和性绑定"一节(smp_affinity位掩码/RPS/RFS/irqbalance经验)；source_files +1；tier保持core
  - concepts/linux-io-stack — 新增"L5硬件层：SSD介质语义(TRIM与写放大)"小节并链接PCIe链路页；relationships +1；source_files +1
  - skills/linux-io-debugging — 新增步骤7"SSD TRIM状态确认与启用"(检测三法+启用三法对比表)；常见问题表+1行(SSD掉速)
  - synthesis/linux-dfx-tool-landscape — 工具矩阵新增"硬件层"行(lspci/setpci/nvme-cli/ipmitool/DDM)+硬件层观测手段小节；source_files +1
- 稀薄来源处理（2个，不建独立页面）：芯片功耗.md(280B，IPU低功耗模式uncore降频影响时延)并入 synthesis/hardware-layer-debugging-landscape 的"功耗换时延"规律；ECC纠错机制.md(792B，CRC vs 汉明码)并入 concepts/memory-spd-xmp-ecc；manifest均登记产出页面
- 来源可信度提醒：本批8个来源均为网络博客(CSDN/cnblogs/掘金，quality=0.55)，含大量未经验证的具体数字(CE>50/h阈值、PRS公式、90%/73%/37台等案例数据)，相关claim已标 ^[ambiguous]，全部lifecycle=draft待人工复核；2个工作笔记(芯片功耗/ECC)按unknown(0.4)计
- 技术性存疑已标注：来源文章将setpci读取的AER状态寄存器(按PCIe规范为按错误类型的位标志)当作累加计数器使用，此用法在summary/concept/skill三页均标注 ^[ambiguous]，dmesg日志流为更可靠证据
- Manifest更新：新增10条document，total_sources_ingested 928→938，last_ingest 2026-10-21→2026-11-06
- 索引/hot更新：index.md 新增"物理硬件"域5个分类区块(7摘要+2实体+3概念+2技巧+1综合)、更新4条既有描述、刷新头部；hot.md 语义快照重写
- 既有lint债务修复（本次顺手处理，超出本批来源范围）：发现5个2026-09-16建的页面存在于磁盘但未入index.md——concepts/agent-paradigm-selection、concepts/agent-reliability-engineering、concepts/loop-engineering、concepts/helm-package-management、skills/k8s-network-troubleshooting（均为Self learn来源，本次已补齐索引条目）；stats按磁盘真实值重算：concepts 82、skills 16、total_pages 166(五分类实际总和，旧值160含9页历史误差)；manifest顶层vault_path仍为过期旧路径（前次ingest已上报，仍未处理，待用户决策）

## [2026-11-09] MAINTAIN | raw来源去重：Linux中断知识点（吐血整理）

- [2026-11-09T14:33] MAINTAIN source="raw/sources/Linux 操作系统/Linux 中断系统/吐血整理！肝翻Linux中断所有知识点（超详细~）.md" action="dedup" removed_lines=96
- 原因：复制粘贴事故——「/proc/interrupts 过渡段＋中断的注册＋中断的处理」整段重复（原509-603行 vs 605-699行，diff 验证逐字节相同），删除第二份；接缝逻辑已校验（异常向量表→三步骤图→恢复现场）
- 性质：用户授权的 raw 例外修改，语义内容零变化；该来源尚未 ingest（manifest 无此文件），无 wiki 级联负担
- 备份：/tmp/wiki-raw-backup/（该文件未被 git 跟踪）；遗留观察：正文称以 el0_irq 为例梳理"保护现场/中断处理/恢复现场"三步，但仅存"恢复现场"小节，缺两节系原始复制缺陷，未凭空补造

## [2026-11-09] MAINTAIN | raw来源增强：中断分类表新增英文全称列

- [2026-11-09T15:05] MAINTAIN source="raw/sources/Linux 操作系统/Linux 中断系统/Linux 中断分类表.md" action="add-column" target="4.1 中断术语汇总表"
- 变更：「中断术语」列后插入「英文全称」列——SPI=Shared Peripheral Interrupt、PPI=Private、LPI=Locality-specific、MSI/MSI-X=Message Signaled Interrupt(eXtended)、IPI=Inter-Processor、SGI=Software Generated、LVT=Local Vector Table、NMI=Non-Maskable、INT n/SVC=Interrupt Instruction/Supervisor Call、Softirq=Software Interrupt；Fault/Trap/Abort 本身即英文全称，标"——"
- 性质：用户授权的 raw 增列，其余各列内容逐字节不变（脚本插列）；该文件已被 git 跟踪可随时 diff/回退，另有 /tmp 备份；manifest 与 wiki 均无此文件引用，无级联负担

## [2026-11-09] INGEST | Linux中断系统目录完整重蒸馏（2新增+4修改来源）

- [2026-11-09T16:13] INGEST source="Linux 操作系统/Linux 中断系统/Linux 中断分类表.md" pages_created=1 pages_updated=1
- [2026-11-09T16:13] INGEST source="Linux 操作系统/Linux 中断系统/Linux中断所有知识点.md" pages_created=1 pages_updated=1
- [2026-11-09T16:13] INGEST source="Linux 操作系统/Linux 中断系统/Linux IPI 核间中断.md" (重蒸馏,hash变更) pages_updated=1
- [2026-11-09T16:13] INGEST source="Linux 操作系统/Linux 中断系统/Linux 软中断内核线程 ksoftirqd详解.md" (重命名+重蒸馏) pages_updated=1
- [2026-11-09T16:13] INGEST source="Linux 操作系统/Linux 中断系统/Linux 硬中断 irq + 软中断 softirq原理.md" (重命名+重蒸馏) pages_updated=2
- [2026-11-09T16:13] INGEST source="Linux 操作系统/Linux 中断系统/Linux 软中断 softirq.md" (重命名+重蒸馏) pages_updated=2
- 新建页面：summaries/linux-interrupt-classification（四维分类框架+术语速查表+分类树+易混淆澄清，蒸馏自中断分类表）；summaries/linux-interrupt-lifecycle（GICv3三组件/irq_domain映射/request_irq注册/ARM64异常处理/workqueue五元组，蒸馏自中断所有知识点）
- hub更新 concepts/linux-interrupt-system(tier=core)：新增"中断分类框架"小节（异步五类/同步三类/GIC组件/irq_domain）、核心观点+分类维度条目、IPI节补ARM SGI对应与TLB/负载均衡用途、下半部节补workqueue进程上下文特性、修正"9种softirq"计数为10种（enum为准）^[ambiguous]、source_files全部刷新为重命名后文件名+2新来源
- 重蒸馏 summaries/linux-softirq-detail：新增softirq注册与raise触发三阶段、preempt_count防重入与__irq_svc抢占、tasklet per-cpu链表与tasklet_action流程、NAPI收包示例与RPS、临界区保护表补spin_lock_irqsave行；source_files刷新
- 交叉链接新增：hub↔两新summary、hub→linux-tlb-management（TLB Shootdown=IPI用例）、softirq-detail→nic-smp-irq-affinity（软硬侧均衡配对）
- Manifest：3条目重键至重命名后路径、4条目hash刷新、新增2条目；total_sources_ingested 938→940、total_summaries 41→43、total_pages 166→168、last_ingest→2026-11-09
- 说明：中断分类表为用户协同整理并已人工审核的分类参考（quality按documentation 0.85计，单来源base_confidence 0.6）；中断所有知识点为知乎blog(0.55)，GIC结构体字段级细节保留在raw、wiki只蒸馏角色与关系

## [2026-11-09] WIKI_UPDATE | my-obsidian-wiki 项目首次同步（vault 自身）

- [2026-11-09T17:10] WIKI_UPDATE project="my-obsidian-wiki" source_repo="github.com/StackTony/my-obsidian-wiki" last_commit_synced="1565714fdc7401009f50f04c3f820c7bd7daa912" pages_created=1 pages_updated=0
- 首次以 /wiki-update 将 vault 自身同步为项目：新建 projects/my-obsidian-wiki.md（项目知识枢纽——三层架构索引、7 条架构决策、6 条运营模式、4 项待办债务、规模快照 11 域/940 来源/169 页）
- 判定依据：CLAUDE.md 已是约定权威，项目页只做索引与"3 个月后零上下文恢复"状态记录，不重复 schema 全文
- manifest 新增顶层 projects 节（source_repo + last_commit_synced）；total_pages 168→169；index.md 新增 ## Projects 区块（Journal 前）
- QMD skipped: QMD_WIKI_COLLECTION 未设置（vault 纯 markdown 为 source of truth）
- 观察备忘：git 暂存区已备好一批“Linux 内存管理”raw 文件（CPU Cache 一致性新增、内存屏障、TLB 改名），是下次 /wiki-ingest 的输入

## [2026-11-09] LINT | 全库健康检查（report-only，无自动修复）

- [2026-11-09T20:04] LINT issues_found=244 orphans=6 broken_links=0 stale=117 contradictions=0 prov_issues=72 missing_summary=1 fragmented_clusters=4 visibility_issues=1 promotion_candidates=36 synthesis_gaps=7 relationship_issues=0 temporal_issues=0 lifecycle_issues=0 oversized=0
- 附加计数：tags_over5=50（软）；uncovered_sources=739（rebuild 时代 manifest 批量登记未回填 pages 数组，201/940 有记录）；hash_mismatch=27（其中 16 条影响产出页）；dead_manifest_keys=5（raw 侧重命名/删除）；pending_raw=17（下次 ingest 输入，lint 运行期间 16→17 仍在实时增长）
- 真孤儿 6 页（正文 wikilink 与 frontmatter 关系边均零入链）：concepts/helm-package-management、concepts/obsidian-ai-toolchain、concepts/ood-principles-and-patterns、entities/dsh-plugin-ecosystem、entities/headroom-tool、summaries/bmc-intro；另有 7 页仅靠 relationships 边连通（正文零链接，cross-linker 候选）；projects/my-obsidian-wiki 仅 hot.md 单链
- 断链 0：两条疑似均为假阳性已排除——log.md:401 行内反引号内的历史修复记录（展示旧链接本身）、linux-interrupt-monitoring-script 的 `[[:space:]]` POSIX 字符类撞 wikilink 语法；另 8 条为 recommendations 外网 .md 结尾 URL
- 方法修正：关系边入链未计入曾致 7 页误报孤儿（kafka-architecture/binary-tree-basics/b-tree-bplus-tree/graph-algorithms/mq-selection-comparison/speculative-decoding-mtp/llm-training-pipeline），复核后剔除
- Schema 完整性零缺陷：必填 8 字段 0 缺失、lifecycle/tier 枚举 0 越界、base_confidence 全 [0,1]、summaries/entities/concepts 的 source_dir/source_files 0 缺失、supersession 0、链接隔离 0 违规
- 过期 117 页全部 lifecycle=draft（无 verified+stale 高危）；来源漂移 16 条影响页：linux-lock-mechanisms/linux-lock-selection/linux-kernel-subsystem-interactions（锁机制全景，06-01 ingest 后源被改）、virtio-io-notification-mechanism/linux-virtio-architecture（ioeventfd）、linux-io-stack/linux-io-debugging（IO全景）、OMO 8 页、ACP 3 页、obsidian-ai-toolchain 3 页、kafka-architecture、agent-system-architecture 4 页等
- Provenance 系统性漂移 72 页：frontmatter 估计（多页 inferred 0.25~0.85）与标记重算（默认=提取约定）偏差 >0.20，最重为 landscape 导航页（fm extracted 0.10~0.15 vs 重算 0.83~1.00）；修复方向=随下次 re-ingest 逐页标记或校准，不建议现在批量改数
- 碎片化标签 4 个：#linux(62页,cohesion 0.08)、#ai(57页,0.08)、#llm(16页,0.10)、#消息队列(5页,0.10)；#学习推荐/#每日报告(12页,0)为 recommendations 链接隔离的设计结果，不计
- 提升候选（入链≥5 且 tier≠core）36 页，头部：linux-io-stack(18)、linux-tracing-frameworks(11)、tool-calling-mcp/multi-agent-framework-comparison/oh-my-opencode(9)；降级候选 2 页（0入链+90天未更新）：ood-principles-and-patterns(140d)、headroom-tool(98d)
- Manifest：中断“Linux中断所有知识点”确认为纯重命名（hash 与 2026-11-09 ingest 记录逐位一致）→ dead key 可安全重键；5 个 dead keys 中 4 个对应用户 raw 重命名（下批 ingest 处理）、1 个已删除（ClickHouse cpp_blog）
- 旧案未决：manifest 顶层 vault_path 仍为过期旧机器路径（多次上报待老板决策）；raw/sources/Obsidian使用/*.json 明文 token 已随历史 commit 推送 GitHub（2026-10-21 已报，raw 不可变，建议轮换密钥）
- 未执行：undated-claims 线级检查（obsidian-wiki CLI 不可用，grep 版噪声大跳过）；矛盾检测为抽样（中断域昨日全量重蒸馏已核对 + softirq 计数/预算口径复查通过，非全库语义比对）

## [2026-11-09] QUERY | swiotlb buffer is full 排查咨询

- [2026-11-09T21:08] QUERY query="现网不使用iommu，报错swiotlb buffer is full，解决方法或规避方法" result_pages=3 mode=normal candidates_seen=4 candidates_used=3 dropped=1
- 附加说明：obsidian-wiki CLI 不可用，按 CLAUDE.md 日志格式手工追加；wiki 无 swiotlb 专页（检索缺口），bounce 概念仅存在于 raw meminfo 原文，已向用户提议沉淀

## [2026-11-09] CAPTURE | swiotlb buffer is full 排查知识沉淀

- [2026-11-09T21:34] CAPTURE type=skills page="skills/swiotlb-troubleshooting" title="swiotlb buffer is full 排查实操手册" sources="conversation:2026-11-09 + raw:Linux meminfo参数详细解释.md(Bounce字段)" pages_created=1
- 用户确认沉淀（查询回复后主动提议，用户回复"沉淀下吧"）；obsidian-wiki CLI 不可用，index/log/hot 按 CLAUDE.md 格式手工更新；无 manifest 变更（conversation 来源非 raw ingest）
- 附带修复：无；关联债：summaries/linux-meminfo-params 蒸馏时漏掉 Bounce 字段（已在 hot.md Active Threads 记录）

## [2026-11-10] INGEST | Linux 操作系统目录重组增量（24新+9修改+2重命名+5空占位 → 7新页面 + 30更新）

- [2026-11-10T11:37] INGEST mode=append source_dir="Linux 操作系统" pages_created=7 pages_updated=30（agents更新22 + 跨批次中心补写8处）
- delta构成（manifest SHA-256比对，等待源文件编辑稳定后冻结快照）：24个新文件、9个修改（重蒸馏）、2个纯重命名（内容哈希逐位一致）、7个旧key失效（改名/转html/移动后由新key替代）、5个0字节空占位（仅登记，无产出）
- 新建页面（7个）：
  - concepts/cpu-cache-coherence — CPU读写内存完整路径、cache line与局部性、MESI/MESIF/MOESI协议演进、伪共享与缓存友好编程（CPU Cache一致性+CPU读写内存两文合并）
  - concepts/memory-barriers — 内存屏障：编译器/CPU重排、Store Buffer/Invalid Queue弱一致性、读/写/全屏障、x86-TSO仅需StoreLoad
  - concepts/linux-io-models — 五种IO模型、select/poll/epoll对比（红黑树+就绪链表O(1)）、缓存IO vs 直接IO（IO类型+IO多路复用+缓存直接IO三文合并）
  - concepts/page-cache-vs-buffer-cache — PC(页/逻辑) vs BC(块/物理)：2.4前双重缓存、统一后BC成PC子集（b_page指向）
  - concepts/linux-dma-mapping — Coherent vs Streaming两类映射、SWIOTLB bounce触发、IOMMU下DMA地址为IOVA（蒸馏自IOMMU六部曲之6）
  - summaries/pci-bar-dma-space — PCIe驱动四大支柱：枚举/BAR映射/DMA/MSI-X，BAR配置错误为驱动故障最常见根因
  - summaries/linux-iommu-deep-dive — IOMMU六部曲全文蒸馏：SWIOTLB软件bounce vs Intel VT-d硬件I/O页表、两者互斥、初始化流程、DMA Coherent Mapping（Linux 5.5.4/x86-64）
- 已有页面更新（agents 22个）：
  - summaries/linux-meminfo-params — 全量重写：40+字段、MemAvailable三因子、Bounce/SwapCached语义（关闭2026-11-09 CAPTURE记录的Bounce遗漏债）
  - summaries/linux-tlb-management、summaries/linux-memory-cpu-relationship、concepts/virtual-memory-and-paging、concepts/linux-memory-management（hub：+IOMMU/PC-BC链接）
  - concepts/linux-io-stack（hub重写：IO生命周期+四大调度器+PC/BC层次，嵌入raw/resources全景图）、summaries/linux-zero-copy-impl、concepts/zero-copy-memory-mapping、summaries/linux-page-cache
  - concepts/linux-network-stack、summaries/linux-network-protocol-stack-impl（+三张表/ARP/MAC老化/IP分片）
  - concepts/linux-process-scheduling、summaries/linux-cfs-scheduler-impl
  - concepts/linux-lock-mechanisms（10→13种锁：+qspinlock/WW Mutex/Tasks RCU；修正Mutex owner编码为低2位）、skills/linux-lock-selection、synthesis/linux-kernel-subsystem-interactions、summaries/linux-rcu-lock（+Tasks RCU行+链表RCU操作）
  - concepts/linux-device-passthrough（+Intel VT-d IOMMU章节呼应）、skills/swiotlb-troubleshooting（数字获文档级佐证，0.55→0.58）
- 跨批次中心补写（8处）：swiotlb进阶用法+Bounce观测+DMA/CPU缓存一致性(dma_wmb)；memory-mgmt/io-stack延伸阅读补链接；kernel-debugging +RSS≥PSS≥USS公式；io-debugging +IO调度器查看切换节；network-debugging +ARP/路由三张表排查节；rcu-lock +Tasks RCU表行；linux-page-cache来源补链
- 矛盾处理：Mutex性能数据修正（mutex 6x/semaphore 8x，原页面反了）；Deadline读FIFO超时500ms vs 5ms标 ^[ambiguous]；sendfile提升50%标 ^[ambiguous]（原文自述未亲测）；radix tree vs xarray标 ^[ambiguous]（不同内核版本口径）
- 空占位文件处理（5个，Linux MMU/页表/PCIe枚举/BAR映射/DMA传输）：0字节，无内容可蒸馏，manifest登记空产出条目；其SHA-256(e3b0c442...)与3个不相关空文件条目（Ollma/有向无环图/ACL）相同属空输入哈希必然碰撞，非数据损坏——已向用户核实解释；填充内容后哈希变化将触发下次ingest
- Manifest：移除7个失效key、迁移2个重命名key（中断分类表/中断流程介绍，保留原ingested_at）、写入33内容条目+5占位条目；total_sources_ingested 940→962、total_pages 169→176、total_concepts 82→87、total_summaries 43→45、total_skills 16→17（磁盘重算，修正旧统计遗漏）、last_ingest→2026-11-10
- 索引/hot更新：index.md 新增7条目（5概念+2摘要）、更新11条既有描述、刷新头部；hot.md 语义快照重写
- 跳过项：QMD_WIKI_COLLECTION 未设置，按 GUARD 跳过 QMD 刷新
- 未处理（需用户决策）：manifest 顶层 vault_path 仍为过期旧路径（多次上报）；lint报告的 provenance 漂移72页/provisional提升候选36页不在本次范围

## [2026-11-10] INGEST | Linux IOMMU、SMMU(ARM)技术图解（1新来源 → 4新页面 + 3更新）

- [2026-11-10T14:07] INGEST mode=append source="Linux 操作系统/Linux 设备驱动管理/Linux IOMMU、SMMU(ARM)技术图解.md" pages_created=4 pages_updated=3
- 来源：知乎图解文章（30.7KB，图为主、正文较少），SHA-256=b323f6f2...；与既有IOMMU六部曲（x86/VT-d视角）互补，补齐ARM SMMU、内核抽象层、Group/Domain、虚拟化地址链四个盲区
- 新建页面（4个）：
  - summaries/linux-iommu-smmu-illustrated — 主蒸馏页：IOMMU/MMU对偶、框架五层、SVA、Group/Domain、VFIO、GPA/HVA/HPA链、透传一致性
  - concepts/linux-iommu-subsystem — 内核统一IOMMU抽象层（屏蔽VT-d/AMD/SMMU差异）、DMA-MAP/IOVA+RCACHE/IO页表/驱动/VFIO五层、SVA共享页表
  - concepts/iommu-group-domain-isolation — Group=DMA隔离最小单元、domain=页表PGD单元、PCIe BDF标记、PCIe-PCI桥Source Identifier同组案例、VFIO Group/Container、VFIO_IOMMU_MAP_DMA四步
  - concepts/vm-address-translation-chain — GVA→GPA(虚机页表,遍历经EPT)→HPA(EPT)、HVA两作用(Qemu mmap+KVM_SET_USER_MEMORY_REGION/vm_exit处理)、透通HPA1==HPA2
- 已有页面更新（3个）：
  - concepts/linux-device-passthrough — 解决未解问题"VFIO group/container抽象"；补BDF设备级隔离(TLP标记vs早期PCI仲裁无BDF)、Group直通铁律、透传映射一致性章节；provenance→0.60/0.30/0.10，base_confidence 0.58→0.78（5来源重算）
  - concepts/linux-dma-mapping — 解决未解问题"scatter-gather在IOMMU页表中的处理"（分散物理页聚合映射为连续IOVA区间）；补IOMMU三大作用；base_confidence 0.61→0.78（3来源重算）
  - summaries/linux-iommu-deep-dive — 引言补多厂商统一抽象层背景（Intel/AMD/ARM SMMU），Domain节点补Group交叉引用
- 矛盾/存疑处理：源文IOVA映射示例排版残损（"00x100000对应DRAM 0x100000000x10100000"），按size=1MB推定为区间0x0~0x100000→0x10000000~0x10100000，两处标 ^[ambiguous]；SMMU软硬件交互/SVA/SMMU位置三节源文以图为主正文为空，未蒸馏内容记入未解问题
- 来源限制：原文多节为外部图片（zhimg链接），图片语义未能蒸馏——图解类来源的固有局限，待相关来源补充
- Manifest：+1内容条目（pages_created=4/pages_updated=3）；total_sources_ingested 962→963、total_pages 176→180、total_concepts 87→90、total_summaries 45→46；JSON经node验证合法
- 协调记录：与并行会话8b（同日目录重组ingest）互认写入范围，无页面冲突；追踪文件重读后增量追加，未覆盖其条目
- 跳过项：QMD_WIKI_COLLECTION 未设置，按 GUARD 跳过 QMD 刷新；obsidian-wiki CLI 不可用，追踪文件手工更新

## [2026-11-11] INGEST | 设备驱动管理目录增量（1新来源 + 1修改 + 1重命名 → 1新页面 + 3更新）

- [2026-11-11T10:20] INGEST mode=append source_dir="Linux 操作系统/Linux 设备驱动管理" delta=new:1 modified:1 renamed:1 unchanged:8
- 新来源：`Linux IOMMU/Linux SMMU的IO Bypass.md`（1425B，SHA-256=811f82fa...）——SMMU STE=Bypass 机制、与 BIOS 关闭 SMMU 的区别、内核参数（iommu.passthrough=1 / smmu.bypassdev=BDF / disable_bypass）、三模式对比
- 修改来源：`Linux BAR空间资源映射.md`（0B占位→2753B，SHA-256=dcd56b3e...）——PCIe BAR 枚举四步（写全1读回探大小、最低非零位定 size、对齐分配、基址写回高位）、4KB NP-MMIO 示例、注意事项
- 重命名来源：`Linux IOMMU、SMMU(ARM)技术图解.md` 移入 `Linux IOMMU/` 子目录（内容哈希未变 b323f6f2...），manifest 键与 7 个 wiki 页面的 source_files/来源路径同步迁移；log 历史条目不回改
- 新建页面（1个）：
  - summaries/linux-smmu-io-bypass — IO Bypass≠关闭SMMU：STE=Bypass 使该SID直通PA（不经S1/S2、不查IOTLB、不查页表权限）；BIOS关闭=整个硬件不工作；三模式对比表；bypass跳过权限检查的安全含义
- 已有页面更新（3个）：
  - concepts/linux-iommu-subsystem — 新增"SMMU IO Bypass：STE级别的翻译旁路"小节（三模式/三参数/安全含义），source_files +1，provenance 0.50/0.45/0.05→0.55/0.40/0.05，base_confidence 0.44→0.61（2来源重算）
  - summaries/pci-bar-dma-space — 新增"BAR大小探测与地址分配流程"（四步+4KB示例+注意事项），source_files +1，provenance 0.75/0.20/0.05→0.74/0.22/0.04，base_confidence 0.44→0.61（2来源重算）
  - skills/swiotlb-troubleshooting — 进阶用法新增"先分清三种模式再动手"（正常翻译/STE=Bypass直通/BIOS关闭走SWIOTLB），解释"iommu=pt 直通模式问题依旧"；source_files +1
- 交叉引用：新摘要页 ↔ IOMMU子系统、Group/Domain隔离、DMA映射、SWIOTLB排查三向互链；bypass页标 relationships extends→linux-iommu-subsystem
- Manifest：键迁移1（SMMU图解文→Linux IOMMU/子目录）、更新1（BAR：2753B/dcd56b3e...）、新增1（IO Bypass：1425B/811f82fa...）；total_sources_ingested 963→964、total_pages 180→181、total_summaries 46→47；JSON经node验证合法（964键）
- 跳过项：同目录 8 个未变文件（含2个0字节占位：PCIe设备枚举、DMA传输）按 hash 跳过；obsidian-wiki CLI 不可用，delta 由手工 SHA-256 比对得出；QMD_WIKI_COLLECTION 未设置，跳过 QMD 刷新

## [2026-11-11] WIKI_UPDATE | my-obsidian-wiki 项目同步（3 提交 delta + raw 维护入库）

- [2026-11-11T16:24] WIKI_UPDATE project=my-obsidian-wiki commits=3 pages_created=1 pages_updated=1
- delta 提交：`31dfcf9` SMMU IO Bypass ingest（wiki 侧已由 /wiki-ingest 消化）；`d77a48a` DMA介绍/DMA传输/DMA和IOMMU 源文档入库；`54665cf` 目录重命名 + 五大子系统源文档（PCI 242KB/网络 231KB/SCSI 139KB/块设备 54KB/DMA与IOMMU 52KB）
- 新建页面（1个）：
  - skills/raw-source-link-sanitization — 中文技术站导入源追踪链接清洗流程：zhida/cloud.tencent/link.zhihu 三类形态识别、perl 字节级正则、计数闭合验证、manifest 只同步哈希不重蒸馏、单文件回滚；含 0 字节哈希碰撞等 6 类常见问题
- 已有页面更新（1个）：
  - projects/my-obsidian-wiki — 规模快照刷新为 964 来源/196 内容页/76 提交；关键模式新增"导入源追踪链接清洗""raw 目录按子系统重组"，manifest 键迁移条目补 2026-11-11 18 键批量对账；待办重写为 14 个待 ingest 积压、wiki 来源路径过期 17 处、manifest 残留 3 条、3 个空占位来源
- 交叉引用：新技能页 ↔ 项目枢纽页、SMMU 图解摘要页；index 新增「Skills (知识管理与维护)」分区
- 维护记录（本同步期间完成，raw 侧）：437 处追踪链接清洗（14 文件）+ manifest 18 键迁移与哈希同步；详见 [[skills/raw-source-link-sanitization]]
- 跳过项：obsidian-wiki CLI 不可用，manifest/index/log/hot 手工更新；QMD_WIKI_COLLECTION 未设置，跳过 QMD 刷新；Step 3b code-understand 不适用（纯 markdown vault，无代码）

## [2026-11-11] INGEST | Linux 操作系统 · Linux 驱动管理五大子系统文档（append delta）

- [2026-11-11T18:10] INGEST mode=append source_dir="Linux 操作系统" delta=new:10 modified:10(cosmetic) unchanged:41 zero:7 created:6 updated:5
- 新建页面（6个）：
  - summaries/linux-pci-subsystem — 242KB 源：PCIe 四层架构、pci_dev/pci_driver/pci_bus/pci_device_id/pci_ops、配置空间 256B→4096B、6 BAR、MSI 32 vs MSI-X 2048、ASPM/CLKREQ/DBI/TLP/AER、Root Complex 拓扑
  - summaries/linux-scsi-subsystem — 139KB 源：三层架构（较高/中间/较低层）、Initiator-Target-LUN、CDB 6/10/16 字节命令族与操作码表、scsi_cmnd/scsi_host_template
  - summaries/linux-block-subsystem — 54KB 源：扇区/块/bio/request/调度器五概念、blk-mq 软队列(每CPU)+硬队列双层、gendisk/blk_mq_tag_set/queue_rq/bio_vec 结构体链
  - summaries/linux-network-device-subsystem — 231KB 源：net_device/net_device_ops/napi_struct、sk_buff/sk_buff_head 内存布局、NAPI API 组、MAC-PHY 与 DTS
  - summaries/linux-dma-iommu-subsystem — 52KB 源：三类 DMA 内存+三类传输+四步工作流、IOMMU 五功能与裸 DMA 四缺陷、iommu_domain/map/attach/flush API、RK3588 实验
  - concepts/linux-driver-model — 驱动域总纲：三类设备访问模型、LDM bus-device-driver、六大总线框架、DTS 与六大基础设施、devm 范式、上下文约束
- 已有页面更新（5个）：
  - concepts/linux-io-stack — 新增 blk-mq 双层队列、SCSI 中间层定位、文件一致性三系统调用（fsync/fdatasync/sync）与 Dirty page；source_files +3
  - concepts/linux-dma-mapping — 新增"三种 DMA 内存口径对齐"（教材三类 vs x86 两类）与四步工作流；source_files +1；source_dir 修正为 `Linux 驱动管理/Linux IOMMU`
  - concepts/linux-iommu-subsystem — 新增"抽象层具体 API 面"（iommu_domain_alloc/map/attach/flush）；source_files +1
  - concepts/linux-network-stack — 新增"设备抽象层：net_device 与驱动 API"；source_files +1
  - concepts/linux-io-models — 新增"三者各自的为什么"（内核缓冲动机、Direct IO+异步搭配、mmap 取消 IO 操作）；source_files 陈旧项替换为新文件
- 来源路径修复：`Linux 设备驱动管理` → `Linux 驱动管理` 全量替换（11 个 wiki 页面：summaries ×5、concepts ×5、skills ×1）；log 历史条目按约定不回改
- Manifest：新增 10 条（含哈希/页产出）、10 条 cosmetic 变更同步哈希（仅格式/标题/空行，未重新蒸馏）、残留 0 字节条目登记 4 条；清理 1 条（`设备驱动管理/Linux DMA传输.md` 0 字节空条目）；total_sources_ingested 964→974、total_pages 197→203、total_summaries 47→52、total_concepts 90→91
- 跳过项：7 个 0 字节占位（MMU/页表管理/页面置换算法/异步AIO/用户态驱动IO/NAT/PCIe枚举）；`Linux 学习大纲.md` 仅 1 行课程链接，不建页只登记；obsidian-wiki CLI 不可用，delta 由手工 SHA-256 比对得出；QMD_WIKI_COLLECTION 未设置，跳过 QMD 刷新
