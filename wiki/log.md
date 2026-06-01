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