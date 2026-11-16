---
title: Swap Cache 与匿名页换入换出
category: concepts
tags: [linux, 内核, 内存, swap, 匿名页]
aliases: [swap cache, swap分区, 交换分区, 匿名页换出, 页槽, swp_entry_t]
relationships:
  - target: "[[concepts/page-cache-vs-buffer-cache]]"
    type: related_to
  - target: "[[concepts/lru-page-reclaim]]"
    type: related_to
  - target: "[[concepts/copy-on-write]]"
    type: related_to
  - target: "[[concepts/linux-memory-management]]"
    type: related_to
source_dir: Linux 操作系统/Linux 内存管理
source_files: [Linux 内存回收机制.md]
summary: swap 分区按 4KB 页槽编号，其 address_space 即 swap cache；匿名页换出经过分配页槽、登记基树、改写 PTE 为 swap 页表项、反向映射与回写，换入则按页槽查 swap cache 决定直接映射还是读盘。
provenance:
  extracted: 0.86
  inferred: 0.12
  ambiguous: 0.02
base_confidence: 0.44
lifecycle: draft
lifecycle_changed: 2026-11-13
tier: supporting
created: 2026-11-13
updated: 2026-11-13
---

# Swap Cache 与匿名页换入换出

匿名页没有磁盘文件作载体，内核用 **swap 分区 + swap cache** 给它补一个"后备存储"：换出时把页写进 swap 分区并改写页表，换入时按页槽编号找回。swap cache 是这条通路上的中转层，既做页槽到内存页的索引，也避免"正在换出的页"被重复读盘。

## 核心观点

- **swap 分区被内核当作"文件"看待**：不是块设备分区语义，而是一个拥有 `address_space` 的连续存储对象。 ^[inferred]
- **swap cache 就是 swap 分区的 `address_space`**：基树以页槽 ID 为索引，保存"页槽 → 内存页描述符"的映射，同时承担并发访问的同步。
- **匿名页换出的标志是加入 swap cache**：一旦 `PG_swapcache` 置位，就意味着此页已被要求换出，后续回收流程会改写页表并回写。
- **页表项是换出的"收据"**：内核用页槽 ID 生成 swap 类型页表项，写入 `page->private`，并通过反向映射把所有映射该页的进程 PTE 改写成这个 swap 页表项。
- **swap cache 的核心价值是消除等待**：页尚未完全写入 swap 时，若有进程再次访问，可直接映射内存中的同一页并取消换出，无需等磁盘 IO 完成再换入。 ^[inferred]
- **page cache 与 swap cache 是一对同构结构**：文件页对应文件的 `address_space`（page cache），匿名页对应 swap 分区的 `address_space`（swap cache），回收算法几乎相同。

## 关键细节

### swap 分区的组织

- 磁盘上是连续的物理扇区，例如 1 GB swap 分区占 1 GB 磁盘块；
- 第一块 4 KB 存放 swap 分区描述结构；
- 其余空间切成一个个 4 KB **页槽**（page slot），并编号；
- 每个页槽恰好保存一个内存页的数据，ID 即 swap 页表项的索引。

### 换出步骤

1. 在 swap 分区分配一个空闲页槽；
2. 以页槽 ID 为索引，在 swap cache 基树中建立结点，存入该页的页描述符；
3. 以页槽 ID 为偏移生成 swap 页表项，保存到 `page->private`；
4. 反向映射：把所有映射此页的进程页表项改写为 swap 页表项；
5. 将 `page->mapping` 指向 swap 分区的 `address_space`，并把页标记为脏；
6. 通过该 `address_space` 的操作集回写页到 swap 分区；
7. 回写完成；
8. 页被回收时，从 swap cache 中摘除。

### 换入步骤

1. 进程访问该页，命中之前写入的 swap 页表项；
2. 触发缺页异常，判定页在 swap 分区而不在内存；
3. 分配一个新页；
4. 由 swap 页表项找到页槽与 swap cache；
5. 若 swap cache 中找不到该页槽：页已被回收，从 swap 分区读入；
6. 若找到：页仍在内存中（尚未回收），直接建立映射。

### 与文件页回收的差异

| 维度 | 匿名页 | 文件页 |
|---|---|---|
| 后备存储 | swap 分区 | 磁盘文件 |
| 是否加入 swap cache | 必须加入 | 不加入，直接使用文件的 page cache |
| 页表项处理 | 改写成 swap 类型页表项 | 直接清空，缺页时由 vma + 文件系统重新定位 |
| 回写前提 | 有进程映射时必须先回写 | 即使是脏页也要回写 |
| buffer_heads | 不需要（swap 连续） | 需要，回收时释放 `page->private` 中的 buffer_heads 链 |

### 与 Page Cache 的关系

`address_space` 是统一抽象：文件页在 page cache 中按文件偏移索引，匿名页在 swap cache 中按页槽索引。区别只在数据组织方式——文件数据可以不连续，swap 分区连续。相关历史与结构关系见 [[concepts/page-cache-vs-buffer-cache]]。

## 未解问题

- zswap / zram / frontswap 作为 swap 前置压缩层的行为，原文只提到"压缩内存换空间"，未说明与 swap cache 的交互。
- swapfile（文件形式）与 swap 分区在页槽映射上的差异未展开。
- swap 预读（swap readahead）与多页换入策略没有覆盖。
- `swappiness` 对换出比例的影响口径存在 0–100 与 0–200 两种说法。 ^[ambiguous]

## 来源

- `raw/sources/Linux 操作系统/Linux 内存管理/Linux 内存回收机制.md` — 知乎文章《Linux 内存回收机制》
- 蒸馏页：[[summaries/linux-memory-reclaim-triggers]] — 匿名页在回收流程中的位置
- 相关：[[concepts/lru-page-reclaim]]（非活动匿名页链表）、[[concepts/copy-on-write]]（匿名页与写时复制）、[[concepts/linux-memory-management]]（SwapCached 等 meminfo 口径）
