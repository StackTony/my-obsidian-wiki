---
title: Zone 水位线
category: concepts
tags: [linux, 内核, 内存, 水位线, watermark]
aliases: [watermark, 内存水位, WMARK_MIN, WMARK_LOW, WMARK_HIGH, min_free_kbytes]
relationships:
  - target: "[[concepts/linux-memory-management]]"
    type: related_to
  - target: "[[concepts/lru-page-reclaim]]"
    type: related_to
  - target: "[[summaries/linux-memory-reclaim-triggers]]"
    type: related_to
source_dir: Linux 操作系统/Linux 内存管理
source_files: [Linux 内存回收机制.md]
summary: zone 的 min/low/high 三条水位线：各自的触发动作、水位与保留页框的判定公式、由 min_free_kbytes 推导 low/high 的比例关系，以及它们如何区分快速/直接/kswapd 三种回收。
provenance:
  extracted: 0.88
  inferred: 0.10
  ambiguous: 0.02
base_confidence: 0.44
lifecycle: draft
lifecycle_changed: 2026-11-13
tier: supporting
created: 2026-11-13
updated: 2026-11-13
---

# Zone 水位线

水位线（watermark）是内核给每个 zone 的空闲页框划出的三条警戒线。分配路径用它们判断"还能不能继续分配"，回收路径用它们判断"要回收多少、回收到什么程度"。理解水位，等于拿到内存回收的触发开关。

## 核心观点

- 每个 zone 维护 `watermark[NR_WMARK]` 数组，三个元素分别是 **WMARK_MIN / WMARK_LOW / WMARK_HIGH**，保存的是页框数量而非字节。 ^[inferred]
- 三条线的关系固定为 `min < low < high`，初始化时按 `low = min + min/4`、`high = min + min/2` 计算。
- **分配是否继续、是否需要回收，看的是"分配后剩余页框"而不是当前空闲页框**：只有 `分配后剩余 > 水位 + zone 保留页框（lowmem reserve）` 才算通过。 ^[inferred]
- 三种回收对应不同水位：快速回收在 `get_page_from_freelist()` 中按本次分配使用的水位判断；直接回收是"所有 zone 连 min 水位都分配失败"的结果；kswapd 在 low 水位失守时被唤醒，目标是把 zone 拉回 high 水位以上。
- 水位是**按 zone** 而非全局计算的：NUMA 下不同 node、不同 zone 各有自己的三条线，因此"系统还有空闲内存"不代表当前 zone 能满足分配。 ^[inferred]

## 关键细节

### 三条线的含义

| 水位 | 含义 | 内核动作 |
|---|---|---|
| `WMARK_MIN` | 最低警戒线，保留给内核关键分配 | 慢速分配仍失败则进入直接回收/快速回收，最坏 OOM |
| `WMARK_LOW` | 快速分配的默认水位 | 空闲页框低于此线时触发快速回收，并唤醒 kswapd |
| `WMARK_HIGH` | zone 满意的空闲水平 | kswapd 回收的目标；空闲回到此线以上才停止 |

### 触发判定

快速分配（`get_page_from_freelist()`）对 zonelist 中的 zone 逐个判断：

```
分配后剩余页框 > 水位 + zone 保留页框  → 允许分配
否则                                  → 对该 zone 执行快速回收（zone_reclaim）
```

慢速分配传入 min 水位，OOM 前的分配尝试则使用 high 水位；同一套判定函数因此会在不同阶段触发不同强度的回收。

### 水位的计算与观察

- `vm.min_free_kbytes` 换算为 `pages_min`；
- `pages_low = pages_min × 5/4`；
- `pages_high = pages_min × 3/2`；
- 初始化函数为 `__setup_per_zone_wmarks()`，按总内存与各 zone 管理的页框数分摊；
- `/proc/zoneinfo` 可直接查看每个 zone 的 `min/low/high` 与 `managed`；水位数通常不到 managed 的 1%。

### 与三种回收的关系

- **快速回收**：在 `get_page_from_freelist()` 内发生，水位可能是 min/low/high 中任意一个，取决于当前处在快速分配、慢速分配还是 OOM 前分配。
- **直接回收**：触发条件是 zonelist 中所有 zone 都以 min 水位分配失败，因此它不逐 zone 判断水位，而是对全部 zone 回收。
- **kswapd 回收**：唤醒条件是 low 水位失守；回收时逐 zone 检查 `分配后剩余 > high + 保留页框`，不满足的 zone 即"不平衡"，从第一个不平衡 zone 起向后回收，直到 node 内所有 zone 都回到 high 以上。

## 未解问题

- 原文未覆盖现代内核的 `watermark_boost`、`watermark_scale_factor` 与 per-memcg 水位，公式与行为可能与文中版本不同。
- lowmem reserve 的按比例预留算法（`lowmem_reserve_ratio`）只有概念性提及，缺少定量例子。
- 水位与内存压缩（compaction）之间的协同条件（何时先压缩再回收）原文只给出结论，未展开判定细节。 ^[ambiguous]

## 来源

- `raw/sources/Linux 操作系统/Linux 内存管理/Linux 内存回收机制.md` — 知乎文章《Linux 内存回收机制》
- 蒸馏页：[[summaries/linux-memory-reclaim-triggers]] — 三种回收的完整调用链
- 相关：[[concepts/lru-page-reclaim]]（水位触发的回收执行器）、[[concepts/linux-memory-management]]（meminfo 与 zone 统计口径）
