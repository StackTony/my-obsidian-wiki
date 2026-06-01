---
title: Hot Cache
updated: 2026-06-01
---

# Hot Cache

*~500字的近期活动语义快照。每次重大写入操作后自动更新。*

## Recent Activity

- [2026-06-01] INGEST — 首批 Linux 操作系统源文件消化完成，25个原始文档蒸馏为14个wiki页面（9个概念+5个摘要）
- [2026-06-01] INIT — vault 创建，目录结构搭建
- [2026-06-01] RESTRUCTURE — wiki/ 成为 AI 自治区，raw/ 为只读源

## Active Threads

- **Linux 内核知识网络**：中断系统、内存管理、IO栈、网络栈、锁机制、资源隔离、进程调度、IPC 八大领域概念页已建立，交叉引用链初步搭建
- **下一步可扩展方向**：云原生（Kubernetes）、数据结构与算法、消息队列等主题尚待消化

## Key Takeaways

- Linux 中断采用 ISR + softirq 两阶段设计，preempt_count 是防抢占的核心机制
- 内存管理有"黑洞"问题：alloc_pages 分配的内存不被 /proc/meminfo 追踪
- Page Cache = Buffers + Cached + SwapCached，Write Back 是默认一致性方案
- 锁选择遵循决策树：中断上下文→Spinlock，进程上下文看持锁时间，读极多写极少→RCU
- Namespace+Cgroups 是容器技术的双引擎：一个管"看什么"，一个管"用多少"

## Flagged Contradictions

- Linux 进程调度源文件较简略（2个文件共~3.5KB），概念页面推断比例偏高
- IO调度算法源文件仅为 stub（76字节），该领域信息可能不完整