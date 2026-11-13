---
title: Linux 内存回收触发路径
category: summaries
tags: [linux, 内核, 内存, 回收, kswapd]
aliases: [内存回收, 页面回收, kswapd, drop_caches, OOM]
relationships:
  - target: "[[concepts/linux-memory-management]]"
    type: related_to
  - target: "[[summaries/linux-buddy-slab-allocator]]"
    type: related_to
source_dir: Linux 操作系统/Linux 内存管理
source_files: [Linux 内存回收机制.md]
summary: 内存回收三条入口：分配慢路径紧缺回收（slowpath→direct_reclaim→try_to_free_pages→shrink_zone/shrink_slab→OOM）、kswapd 周期性回收（balance_pgdat→kswapd_shrink_zone）、用户 drop_caches；两个执行器为 shrink_zone 与 shrink_slab。
provenance:
  extracted: 0.35
  inferred: 0.55
  ambiguous: 0.10
base_confidence: 0.39
lifecycle: draft
lifecycle_changed: 2026-11-12
tier: supporting
created: 2026-11-12
updated: 2026-11-12
---

# Linux 内存回收触发路径

本页蒸馏的原始来源只有一张调用关系图（`raw/resources/Pasted image 20261112204136.png`），没有正文。图中的节点与箭头是**提取**的，节点之间的因果解释、层次归并是**推断**的。它回答的是"内存不够时，内核从哪些入口开始回收、最后落到哪两个执行器"。

## 核心观点

- **回收有三条入口，按压力来源区分**：内存紧缺（分配路径阻塞式回收）、周期性（kswapd 后台回收）、用户触发（`drop_caches` 手动清缓存）。
- **两条慢路径都收敛到 `try_to_free_pages` / `shrink_zone` / `shrink_slab`**：紧缺回收走 `__alloc_pages_slowpath → __alloc_pages_direct_reclaim → try_to_free_pages`，周期性回收走 `kswapd → balance_pgdat → kswapd_shrink_zone`。
- **回收只有两个执行器**：`shrink_zone` 回收页框（Page Cache / 匿名页，配合 LRU），`shrink_slab` 回收可回收的 slab 对象（dentry、inode 等）。所有入口最终都落到这两者或其上层封装。^[inferred]
- **`wake_all_kswapd` 是"分配路径叫醒后台"的握手**：慢路径发现回收不过来时唤醒所有 node 的 kswapd，把压力转交给后台线程；kswapd 侧也会反向触发唤醒。^[inferred]
- **`out_of_memory` 是最后兜底**：`try_to_free_pages` 失败才进入 OOM，选进程杀掉；它不是回收算法的一部分，而是回收失败的终点。
- **`drop_caches` 是"用户态旁路"**：不走压力检测，直接 `drop_slab`（→`shrink_slab`）与 `drop_pagecache_sb` 清 page cache，常用于测试与紧急释放。^[inferred]

## 关键细节

### 路径一：内存紧缺回收（同步、阻塞）

```
alloc_page_buffers ─┐
                    ├→ free_more_memory
__getblk ───────────┘

__alloc_pages
  └→ __alloc_pages_slowpath
       ├→ wake_all_kswapd          （唤醒后台 kswapd）
       └→ __alloc_pages_direct_reclaim
            └→ try_to_free_pages
                 ├→ shrink_zone     （回收页框）
                 ├→ shrink_slab     （回收 slab 对象）
                 └→ out_of_memory   （回收失败，OOM）
```

- 触发条件：`__alloc_pages` 在快速路径拿不到页，进入 `slowpath`。^[inferred]
- `free_more_memory` 是缓冲区/块设备路径的回收入口：`alloc_page_buffers` 与 `__getblk` 在拿不到 buffer head 页时先尝试释放内存再重试。^[inferred]
- 该路径在**分配者上下文同步执行**，会直接增加分配延迟；这是"内存紧张时系统变慢"的主因之一。^[inferred]

### 路径二：周期性回收（异步、kswapd）

```
kswapd
  └→ balance_pgdat
       ├→ wake_all_kswapd          （跨 node 唤醒）
       └→ kswapd_shrink_zone
            ├→ shrink_zone
            └→ shrink_slab

reap_work
  └→ cache_reap
       └→ slab_destroy
```

- `kswapd` 每个 NUMA node 一个内核线程，在 zone 空闲页低于 watermark 时被唤醒，回收直到回到高位水位。^[inferred]
- `balance_pgdat` 负责在 node 内做平衡，`kswapd_shrink_zone` 对具体 zone 执行回收；两者是"node 级调度 → zone 级执行"的关系。^[inferred]
- `reap_work → cache_reap → slab_destroy` 是 slab 缓存的定期清理支线，与 `shrink_slab` 的目标一致但触发源不同（定时器/工作队列）。^[inferred]

### 路径三：用户触发回收（手动）

```
drop_caches
  ├→ drop_slab
  │    └→ shrink_slab
  └→ drop_pagecache_sb
```

- 通过 `echo 1|2|3 > /proc/sys/vm/drop_caches` 触发；1 清 page cache、2 清 dentry/inode、3 两者都清。^[inferred]
- 只回收**干净页**；脏页需先回写，因此 `drop_caches` 不等于立即释放全部缓存。^[inferred]
- 生产环境慎用：清缓存会让后续访问全部回落到磁盘，造成短时 IO 尖刺。^[inferred]

### 两个执行器的分工

| 执行器 | 回收对象 | 依赖信号 | 失败后果 |
|---|---|---|---|
| `shrink_zone` | 页框：文件页 / 匿名页 | LRU 链表、PTE 访问位、脏页回写 | 继续压缩，最终 OOM |
| `shrink_slab` | 可回收 slab 对象（dentry/inode 等） | `shrinker` 注册的回调 | 保留 SUnreclaim，无法回收 |

## 未解问题

- 图中 `balance_pgdat → wake_all_kswapd` 与 `wake_all_kswapd → kswapd` 的方向按调用惯例解读，源图箭头较密，可能存在误读。 ^[ambiguous]
- `free_more_memory` 与 `try_to_free_pages` 之间是否直接相连，源图未画出明确箭头；本页按"最终仍走 `try_to_free_pages`"推断。 ^[ambiguous]
- 水位（min/low/high watermark）、`watermark_boost`、`min_free_kbytes` 与三条路径的量化关系，源图未覆盖。
- 直接回收（direct reclaim）与 `kswapd` 的并发控制、`pfmemalloc` 预留池未展开。 ^[inferred]

## 来源

- `raw/sources/Linux 操作系统/Linux 内存管理/Linux 内存回收机制.md` — 仅含一张回收调用图（`raw/resources/Pasted image 20261112204136.png`），无正文
- 交叉：[[concepts/linux-memory-management]]（LRU 与 meminfo 口径）、[[summaries/linux-buddy-slab-allocator]]（伙伴系统与 slab 的分配侧）
