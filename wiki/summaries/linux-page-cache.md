---
title: Linux Page Cache机制
category: summaries
tags: [linux, 内核, page-cache, file-io, memory]
source_dir: Linux 操作系统/Linux 内存管理
source_files: [Linux 页缓存（Page Cache）.md]
summary: Page Cache=Buffers+Cached+SwapCached，基数树组织，预读算法，Write Through/Back一致性，dirty page回写。2.4后合并buffer cache消除双重缓存。
provenance:
  extracted: 0.85
  inferred: 0.10
  ambiguous: 0.05
base_confidence: 0.775
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: supporting
created: 2026-06-01
updated: 2026-06-01
---

# Linux Page Cache机制

Page Cache是Linux文件IO加速的核心机制——将文件内容缓存到内存，后续访问直接从缓存读取，避免重复磁盘IO。

## 核心观点

### Page Cache组成

```
Page Cache = Buffers + Cached + SwapCached
           = Active(file) + Inactive(file) + Shmem + SwapCached
```

内核2.4后Page Cache与buffer cache合并，消除了双重缓存问题^[inferred]。

### 基数树组织结构

Page Cache使用基数树(radix tree)按文件组织：
- 每个inode一个基数树
- 节点按文件偏移量索引
- 查找：O(log N)时间定位指定页

### 预读机制

基于局部性原理，用户读4KB时OS额外加载16KB：
- 预读窗口动态调整
- 顺序读预读增大，随机读预读缩小^[inferred]

### Write Through vs Write Back

| 模式 | 行为 | 性能 | 安全性 |
|------|------|------|--------|
| Write Through | 数据直接写磁盘 | 低 | 高（无脏页风险） |
| Write Back | 数据先写缓存再异步刷盘 | 高 | 低（宕机可能丢数据） |

Write Back是默认模式。dirty page回写由per存储设备的内核线程定期执行。

### Anonymous页 vs File-backed页

- **File-backed页**：有文件 backing，回收时直接丢弃（下次重新从磁盘读）
- **Anonymous页**：进程堆栈等私有内存，回收需要swap out到磁盘

## 来源

- [[concepts/linux-memory-management]] — 内存管理整体框架
- [[summaries/linux-meminfo-params]] — meminfo中Page Cache相关字段
- `raw/sources/Linux 操作系统/Linux 内存管理/Linux 页缓存（Page Cache）.md`