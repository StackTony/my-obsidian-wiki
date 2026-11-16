---
title: Linux 内存回收机制
category: summaries
tags: [linux, 内核, 内存, 回收, kswapd]
aliases: [内存回收, 页面回收, kswapd, drop_caches, OOM, shrink_zone, 页面回收机制]
relationships:
  - target: "[[concepts/linux-memory-management]]"
    type: related_to
  - target: "[[summaries/linux-buddy-slab-allocator]]"
    type: related_to
  - target: "[[concepts/lru-page-reclaim]]"
    type: related_to
  - target: "[[concepts/zone-watermark]]"
    type: related_to
  - target: "[[concepts/swap-cache-mechanism]]"
    type: related_to
source_dir: Linux 操作系统/Linux 内存管理
source_files: [Linux 内存回收机制.md]
summary: 基于页框水位与 LRU 的 Linux 内存回收全景：zone 三水位与分配慢路径、文件页/匿名页回收、swap cache 与 page cache 对偶、shrink_zone→lruvec→list→page_list 执行链，以及快速/直接/kswapd 三种回收的差异与调参。
provenance:
  extracted: 0.82
  inferred: 0.15
  ambiguous: 0.03
base_confidence: 0.44
lifecycle: draft
lifecycle_changed: 2026-11-13
tier: supporting
created: 2026-11-12
updated: 2026-11-13
---

# Linux 内存回收机制

内存回收发生在 zone 的空闲页框低于水位线时：内核扫描 LRU 链表，把不常访问的页写回磁盘文件或 swap 分区，再把这些页框释放回伙伴系统。回收对象只有两大类——**文件页**（Page Cache 中映射磁盘文件的页）与**匿名页**（进程堆、栈、匿名 mmap 与 shmem 映射）。文章的主线是：回收由分配失败与水位驱动，代价主要是 IO，因此重点是"何时回收、回收谁、按什么顺序回收"。

本页最初只蒸馏了一张回收调用图（`raw/resources/Pasted image 20261112204136.png`）；2026-11-13 原文件补全为完整正文后重新蒸馏，图像阶段的结论作为"三入口"骨架保留，正文细节全部来自原文。

## 核心观点

- **回收由水位触发，不是定时任务**：每个 zone 有 min/low/high 三条水位线，空闲页框跌破哪条线就触发对应强度的回收。 ^[inferred]
- **回收有三条入口**：分配慢路径的同步直接回收、kswapd 的后台周期回收、用户 `drop_caches` 手动回收（原文未展开，属补充知识）；执行器最终都是 `shrink_zone`（页框）与 `shrink_slab`（可回收 slab 对象）。 ^[inferred]
- **回收的本质是把 `page->_count` 降到 0**：内核只能回收引用计数为 0 的页；回收过程做的是"隔离、解映射、回写、从 address_space 摘除"，让最后一个引用消失后把页框交还伙伴系统。
- **文件页与匿名页的差别在于落地位置**：文件页回写到所属文件的 Page Cache（`address_space`），匿名页先加入 swap cache、再回写到 swap 分区；文件页的映射页表项直接清空，匿名页的页表项要改写成 swap 类型页表项。
- **三种回收共用同一套执行代码**：快速/直接/kswapd 的区别只在进入前的判定与 `struct scan_control` 参数（优先级、是否允许回写/解映射/swap），执行链完全一致。
- **`swappiness` 与 `zone_reclaim_mode` 是方向旋钮**：前者调节文件页与匿名页的扫描比例，后者决定快速回收是否允许回写与解映射。
- 原文 1.1 节把用户态 `free`/GC 与内核"直接内存回收"混为一谈，这一段的术语使用有误，内核语境下应理解为分配慢路径中的同步回收。 ^[ambiguous]

## 关键细节

### 1. 什么时候回收

**kswapd 周期性回收**：每个 NUMA node 一个 `kswapd` 内核线程，周期性检查内存，按空闲页框落在哪段水位决定是否回收：

```
free < pages_min            → 进程可用内存耗尽，触发直接内存回收（仅内核可分配）
pages_min < free < pages_low → 内存压力大，kswapd 回收直到高于 high 水位
pages_low < free < pages_high → 有压力但还能满足新请求
free > pages_high           → 压力小，不回收
```

**直接内存回收**：慢速分配中所有 zone 都无法用 min 水位拿到页框，且异步压缩仍失败时，由申请者上下文同步回收（原文 1.1 的表述见上文歧义说明）。

**回收哪些内存**：

| 类型 | 回收方式 |
|---|---|
| 干净文件页 | 与磁盘内容一致，直接释放，下次访问再从磁盘读 |
| 脏文件页 | 先回写到磁盘，再释放；回写可由 `fsync` 或内核线程触发 |
| 匿名页 | 有 swap 时写入 swap 后释放，再次访问时换入；无 swap 时基本只能常驻 |
| 页表中标记可回收的页 | 页表项标记可回收后由内存管理器回收 |
| zswap / zram | 压缩内存中的数据腾出物理内存 |
| OOM Killer | 回收后仍不足时，杀掉低优先级或大内存进程兜底 |

### 2. 回收方式的基础：水位、LRU 与引用计数

- **zone 三水位**：`watermark[WMARK_MIN/LOW/HIGH]` 保存在 zone 中，关系为 `min < low < high`；初始化时 `low = min + min/4`、`high = min + min/2`，可通过 `/proc/zoneinfo` 观察。水位值通常不到 managed 页框的 1%，由 `__setup_per_zone_wmarks()` 设置。详见 [[concepts/zone-watermark]]。
- **页描述符标志**：`PG_lru`、`PG_referenced`、`PG_dirty`、`PG_active`、`PG_private`、`PG_writeback`、`PG_swapbacked`、`PG_swapcache`、`PG_reclaim`、`PG_mlocked`，回收逻辑围绕这些位与 PTE 的 Accessed 位展开。
- **`page->_count`**：每被进程映射、加入 LRU 缓存、加入 `address_space` 基树、挂 buffer_heads 都会加一；对应的解映射、摘除会减一。内核真正回收的是 `_count == 0` 的页；回收的工作就是让目标页的计数归零。
- **LRU 五链表**：活动/非活动匿名页、活动/非活动文件页、`LRU_UNEVICTABLE`。回收只处理前四个，且只从**非活动链表尾部**扫描；活动链表只在非活动链表过少时才补充。详见 [[concepts/lru-page-reclaim]]。
- **扫描数量**：`shrink_lruvec()` 每轮对四个链表各扫描最多 `SWAP_CLUSTER_MAX`（32）个页框；`sc->priority` 决定基准扫描量（越小扫得越多，为 0 时全扫一遍，默认 12），`swappiness` 在此基础上调整匿名页/文件页比例。
- **swap 与 page cache 是一对 address_space**：swap 分区被内核当作"文件"看待，其 `address_space` 叫 swap cache；磁盘文件的 `address_space` 叫 page cache。两者都承担"页槽/文件偏移 → 内存页"的关联与并发访问同步。详见 [[concepts/swap-cache-mechanism]]。

### 3. 匿名页换出与换入

匿名页换出时：分配 swap 页槽 → 在 swap cache 基树中登记页描述符 → 用页槽 ID 生成 swap 类型页表项存入 `page->private` → 反向映射改写所有映射页表项 → `mapping` 指向 swap 分区的 `address_space` 并标记脏 → 回写 → 回收时从 swap cache 摘除。

换入时：进程访问到 swap 页表项 → 缺页异常判定页在 swap 中 → 分配新页 → 按页槽 ID 查 swap cache → 未找到则从 swap 分区读入，找到则直接映射内存中的页。**swap cache 的意义**：页尚未被完全回收前，其他进程再访问可直接映射内存页，无需等磁盘 IO。

文件页回收与匿名页几乎同构，区别有三点：文件数据不连续；文件页读入时在文件 page cache 做关联；文件页的进程页表项直接清空（缺页时通过 vma 与文件系统重新定位），而匿名页必须生成 swap 页表项。

### 4. 分配路径：回收的前置上下文

`alloc_page()/alloc_pages()` 最终调用 `__alloc_pages_nodemask()`：

- **快速分配**：用 low 水位在 zonelist 中找 zone，不满足则做一次快速回收再重试。
- **慢速分配**：快速失败后用 min 水位分配，依次做异步内存压缩、直接内存回收、轻同步内存压缩，最后按需 OOM。
- **zonelist / preferred_zone**：NUMA 下优先本 node 的 zone，其次按距离排序的远端 node；32 位系统中 zone 优先级为 `ZONE_HIGHMEM > ZONE_NORMAL > ZONE_DMA`。
- **`scan_control`**：回收/压缩的公共参数集，关键字段为 `priority`（扫描量）、`may_writepage`（能否回写）、`may_unmap`（能否解映射）、`may_swap`（是否扫描匿名页）、`nr_to_reclaim`、`nr_scanned`、`nr_reclaimed`。

gfp 标志也会限制回收：未入 swap cache 的匿名页需要 `__GFP_IO` 才能加入并回写；已在 swap cache 的匿名页回写需要 `__GFP_FS`；文件页回写同样需要 `__GFP_FS`。

### 5. 执行链

```
shrink_zone(zone, sc)
  └→ 遍历 memcg → lruvec → shrink_lruvec(lruvec, swappiness, sc)
       ├→ get_scan_count() 计算每个 LRU 应扫描的数量
       └→ 每轮：shrink_list(lru, ≤32, ...)
            ├→ 活动链表 → shrink_active_list()
            └→ 非活动链表 → shrink_inactive_list() → shrink_page_list()
```

- **`shrink_zone`**：对 zone 的每个 memcg 的 LRU 执行回收；`should_continue_reclaim()` 决定是否再来一轮——目标是回收 `2^(order+1)` 个页框（比本次分配需求多一倍），并且尽量回收到可以进行内存压缩为止。
- **`shrink_active_list`**：从活动链表尾部隔离页，`page_referenced()` 检查并清除 PTE Accessed；只有最近访问过的**可执行文件页**留在活动链表头部，其余全部降级到非活动链表头部；顺手释放 `_count == 0` 的页。
- **`shrink_inactive_list`**：隔离非活动页 → `shrink_page_list()` 尝试回收 → 剩余页放回对应链表；根据脏页/回写/拥塞情况设置 `ZONE_WRITEBACK`、`ZONE_CONGESTED`、`ZONE_DIRTY` 标志。
- **`shrink_page_list`**：逐页判断是否正在回写、最近是否被访问；匿名页加入 swap cache 并标记脏；`try_to_unmap()` 解映射；脏页 `pageout()` 回写并置 `PG_reclaim`；释放文件页的 buffer_heads；`_count == 2` 时从 `address_space` 摘除并释放；其余页放回链表。

**`_count == 2` 是关键判定**：隔离时 +1、加入 address_space 时 +1，解映射后若再无进程引用，计数恰好为 2；此时从基树摘除并减 2 即可释放。计数不为 2 说明又有进程访问，放弃本次回收。

### 6. 三种回收种类对比

| 维度 | 快速回收 | 直接回收 | kswapd 回收 |
|---|---|---|---|
| 触发点 | `get_page_from_freelist()` 发现分配后空闲 < 水位 + 保留页框 | 慢路径所有 zone 都拿不到 min 水位页框 | 分配拿不到 low 水位页框时唤醒 |
| 调用链 | `zone_reclaim → __zone_reclaim → shrink_zone` | `__alloc_pages_slowpath → … → try_to_free_pages → shrink_zones → shrink_zone` | `balance_pgdat → kswapd_shrink_zone → shrink_zone` |
| 优先级 | 4（最多 4 次 `shrink_zone`） | 12（默认，逐级下降） | 12 |
| 目标 | `max(nr_pages, 32)` | 32 个页框 | `max(32, high 水位页框数)` |
| 作用范围 | zonelist 中不满足水位的 zone | 首轮强制全部 zone，之后按扫描比例筛选 | 本 node 中第一个不平衡 zone 及其后的 zone |
| 脏文件页回写 | 不做 | 不做 | 可做 |
| 匿名页 swap | 由 `zone_reclaim_mode` 决定 | 可做 | 可做 |
| 解映射 | 由 `zone_reclaim_mode` 决定 | 可做 | 可做 |

三种回收在内存紧张时可能并发执行，但执行代码相同，差异只体现在 `scan_control` 的初始化和进入条件上。

### 7. 调参

- **`vm.swappiness`**：倾向性旋钮。文章在不同段落给出 0–100（sysctl 口径）与 0–200（`shrink_zone` 内 memcg 口径）两种范围；0 更倾向回收文件页，数值越大越倾向回收匿名页。即使为 0，当"剩余内存 + 文件页 < high 水位"时仍会发生 swap。 ^[ambiguous]
- **`vm.min_free_kbytes`**：换算为 `pages_min`，再推出 `pages_low = pages_min×5/4`、`pages_high = pages_min×3/2`。
- **`/proc/sys/vm/zone_reclaim_mode`**：`0x1` 开启 zone 回收、`0x2` 允许回写、`0x4` 允许解映射；为 0 时快速回收只处理距离近的 zone。
- **`vm.panic_on_oom`**：0 触发 OOM Killer，1 直接 panic。
- **`vm.oom_kill_allocating_task`**：0 杀分数最高的进程，1 杀当前申请者。

## 未解问题

- 原文 1.1 节将用户态 `free`/垃圾回收与内核直接内存回收并列，术语与内核实现不符；本页按内核语境归并，原文这一段的原意仍不明确。 ^[ambiguous]
- `swappiness` 的 0–100 与 0–200 两种口径对应不同内核版本/层级，原文未区分版本。 ^[ambiguous]
- `get_scan_count()` 的页框数计算公式、`page_check_references()` 的完整判定、反向映射 `try_to_unmap()` 的实现细节，原文均明确留待后续文章。
- 原文基于较早内核（出现 `zone_reclaim_mode`、`pdflush`），现代内核的 `watermark_boost`、MGLRU、cgroup v2 内存回收差异未覆盖。

## 来源

- `raw/sources/Linux 操作系统/Linux 内存管理/Linux 内存回收机制.md` — 原文全文（知乎 https://zhuanlan.zhihu.com/p/710960571）；最初版本仅含一张回收调用图，2026-11-13 补全正文后重新蒸馏
- `raw/resources/Pasted image 20261112204136.png` — 回收调用关系图（三入口/两执行器骨架）
- 相关实现页：[[concepts/lru-page-reclaim]]、[[concepts/zone-watermark]]、[[concepts/swap-cache-mechanism]]
- 交叉：[[concepts/linux-memory-management]]（meminfo/Page Cache/LRU 口径）、[[summaries/linux-buddy-slab-allocator]]（回收后的页框去向）
