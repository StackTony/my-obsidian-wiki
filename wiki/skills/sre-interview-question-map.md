---
title: SRE / AI 运维面试问题地图
category: skills
tags: [面试, SRE, 运维, 知识地图, 复盘]
aliases: [面试问题地图, SRE 面试题, AI 运维面试]
source_dir: Self learn/面试经验
source_files: [DeepSeek.md, 佳琪投资.md, 阿里云.md]
summary: 把三份面试记录里的问题按虚拟化、文件系统、网络、内存、调度与中断分组，逐题标注 wiki 覆盖情况与对应页面，并列出尚未覆盖的缺口，作为复习与补源清单。
provenance:
  extracted: 0.55
  inferred: 0.40
  ambiguous: 0.05
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-11-12
tier: peripheral
created: 2026-11-12
updated: 2026-11-12
---

# SRE / AI 运维面试问题地图

本页不是答案库，而是一张**问题 → 已有知识 → 缺口**的对照表。来源是 `Self learn/面试经验/` 下三份零散记录（DeepSeek AI 运维、佳琪投资 SRE、阿里云灵骏 SRE），内容可信度低，仅作为复习线索；具体结论以对应 wiki 页面和原始来源为准。

## 概述

三份记录共约 10 个问题，集中在 Linux 内核与云原生运维：热迁移、文件系统写路径、网络转发路径、透明大页、fork/COW、进程调度、中断上下文、跨洲大文件传输排查、文件缓存。多数问题在 vault 中已有对应页面，少数（跨洲传输排查、Redis 与 THP 的因果链）需要补源。

## 问题地图

### 虚拟化与热迁移

| 问题 | 覆盖情况 | 对应页面 |
|---|---|---|
| 热迁移机制 | ✅ 已有三阶段流程 | [[summaries/linux-live-migration-flow]]、[[skills/virsh-vm-management]] |
| fork 进程时内存是否 fork？fork 线程呢？ | ✅ 已有 COW 机制 | [[concepts/copy-on-write]]、[[summaries/linux-copy-on-write]] |

热迁移的复习重点：内存迭代拷贝 → 停机拷贝 → 网络恢复，以及 dirty page rate 与停机时间的关系。fork 的重点是"页表复制、PTE 置只读、写保护缺页才复制"，线程共享同一 `mm_struct`，不触发地址空间复制。

### 文件系统与存储

| 问题 | 覆盖情况 | 对应页面 |
|---|---|---|
| 文件系统写操作经过的路径 | ✅ 已有 VFS/Page Cache/Block 层链路 | [[concepts/linux-io-stack]]、[[summaries/linux-page-cache]]、[[concepts/page-cache-vs-buffer-cache]] |
| 文件缓存机制 | ✅ 已有 Page Cache 与 Buffer Cache | [[summaries/linux-page-cache]]、[[concepts/page-cache-vs-buffer-cache]] |
| 从美国传 1T 文件到中国很慢，排查点 | ⚠️ 部分覆盖 | [[concepts/linux-network-stack]]、[[summaries/linux-network-protocol-stack-impl]] |

写路径的复习重点：`write()` → VFS → Page Cache（Buffered IO）→ 回写线程 → Block 层 bio/request → 驱动。跨洲传输排查应覆盖：带宽时延积（BDP）、TCP 窗口与拥塞控制、丢包/重传、MTU/分片、磁盘与加密瓶颈、应用层并发与校验；vault 目前只有协议栈原理，缺少系统化排查清单。^[inferred]

### 网络

| 问题 | 覆盖情况 | 对应页面 |
|---|---|---|
| 网络转发经过的路径 | ✅ 已有协议栈收发路径 | [[concepts/linux-network-stack]]、[[summaries/linux-network-protocol-stack-impl]] |

复习重点：收包 NAPI（硬中断唤醒 → 软中断轮询）→ 协议栈 → 路由/Netfilter → 转发或上送 socket；发包 qdisc → 驱动 → 网卡。若涉及 NAT/容器网络，还需补 iptables/nftables 与 veth/bridge 路径。^[inferred]

### 内存

| 问题 | 覆盖情况 | 对应页面 |
|---|---|---|
| 为什么 Redis 不推荐透明大页（THP）？ | ⚠️ 有 THP 基础，缺 Redis 因果链 | [[summaries/linux-meminfo-params]]、[[concepts/linux-memory-management]] |

已知：THP 以 2MB 为单位管理，减少 TLB miss，但会增加内存碎片、延迟抖动与 `khugepaged` 后台开销。Redis 场景的常见解释是 fork 做 RDB/AOF 重写时 COW 粒度从 4KB 变成 2MB，写时复制放大、延迟尖刺；这一因果链 vault 尚未收录，标为缺口。^[inferred] ^[ambiguous]

### 调度与中断

| 问题 | 覆盖情况 | 对应页面 |
|---|---|---|
| 进程调度切换时会发生什么？ | ✅ 已有 CFS 与上下文切换基础 | [[summaries/linux-cfs-scheduler-impl]]、[[concepts/linux-process-scheduling]] |
| 中断上下文中能否进行进程/线程切换？ | ✅ 已有上下文约束 | [[concepts/linux-interrupt-system]]、[[summaries/linux-softirq-detail]] |

调度切换的复习重点：调度类优先级 → `pick_next_task` → `context_switch`（切换 `mm`、寄存器、栈）→ `switch_to`。中断上下文不能睡眠、不能调用可能阻塞的调度函数；硬中断/softirq/tasklet 中不能主动切换进程，需要把工作推迟到 workqueue 或 threaded irq。^[inferred]

## 未解问题 / 补源清单

- **跨洲大文件传输排查**：需要一份从 TCP 层到应用层的系统排查清单（BDP、窗口缩放、重传、MTU、磁盘、加密、并发）。
- **Redis 与 THP**：需要 Redis 官方文档或生产案例，补全 fork + COW + 2MB 页的因果链。
- **热迁移的 dirty page rate 控制**：现有摘要只有三阶段，缺少 `dirty_limit`、自动收敛与 post-copy 对比。
- **中断上下文切换的边界**：需要明确 `preempt_count`、`in_interrupt()` 与 `might_sleep()` 的判定关系。

## 来源

- `raw/sources/Self learn/面试经验/DeepSeek.md` — AI 运维工程师岗位问题清单
- `raw/sources/Self learn/面试经验/佳琪投资.md` — SRE 面试问题（跨洲传输、文件缓存）
- `raw/sources/Self learn/面试经验/阿里云.md` — 灵骏 SRE（仅标题，无内容）
- 交叉：[[concepts/linux-io-stack]]、[[concepts/linux-network-stack]]、[[concepts/linux-interrupt-system]]、[[concepts/copy-on-write]]
