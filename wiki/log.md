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