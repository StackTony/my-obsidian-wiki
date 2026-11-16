---
title: LRU 页回收
category: concepts
tags: [linux, 内核, 内存, LRU, 页面回收]
aliases: [LRU链表, Active/Inactive LRU, shrink_active_list, shrink_inactive_list, PG_referenced]
relationships:
  - target: "[[concepts/virtual-memory-and-paging]]"
    type: implements
  - target: "[[concepts/zone-watermark]]"
    type: related_to
  - target: "[[concepts/swap-cache-mechanism]]"
    type: related_to
  - target: "[[concepts/linux-memory-management]]"
    type: related_to
source_dir: Linux 操作系统/Linux 内存管理
source_files: [Linux 内存回收机制.md]
summary: Linux 用 Active/Inactive 双链表近似 LRU：五个链表只回收非活动匿名页与非活动文件页；PTE Accessed 与 PG_referenced 决定升降级，扫描量由 priority 与 swappiness 控制，回收以 page->_count 归零为终点。
provenance:
  extracted: 0.84
  inferred: 0.14
  ambiguous: 0.02
base_confidence: 0.44
lifecycle: draft
lifecycle_changed: 2026-11-13
tier: supporting
created: 2026-11-13
updated: 2026-11-13
---

# LRU 页回收

Linux 并不是严格实现教科书 LRU，而是用 **Active / Inactive 双链表 + 访问位回写** 来近似：新页先进非活动链表，被再次访问才升级到活动链表，回收只从非活动链表尾部取页。这套结构让"最近使用"的判定可以低成本地分布式完成。

## 核心观点

- **五个链表**：`LRU_ACTIVE_ANON`、`LRU_INACTIVE_ANON`、`LRU_ACTIVE_FILE`、`LRU_INACTIVE_FILE`、`LRU_UNEVICTABLE`；回收只处理前四个，且只有**非活动链表**上的页会被真正回收。 ^[inferred]
- **扫描方向固定**：从非活动链表尾部向前扫描，越靠尾部越"冷"；页回写完成后会被放到非活动链表尾部，因此下次回收优先命中。
- **访问信号有两个来源**：PTE 的 Accessed 位（`page_referenced()` 读取并清零）与页描述符的 `PG_referenced` 位（主要用于文件页的第二机会判定）。
- **活动链表只做"降级/补充"，不直接产出回收页**：`shrink_active_list()` 把冷页搬到非活动链表头部；只有非活动匿名页过少时，才会主动从活动匿名页补充 32 个页框。 ^[inferred]
- **回收终点是 `page->_count == 0`**：任何仍被进程映射、在 `address_space` 基树中、或挂着 buffer_heads 的页都必须先解除这些引用。
- **扫描预算由两个旋钮决定**：`sc->priority` 定基准量（越小扫得越多，0 表示全扫，默认 12），`swappiness` 定匿名页与文件页的比例。

## 关键细节

### 链表之间怎么移动

| 场景 | 动作 |
|---|---|
| 新页加入 | 进入对应类型的非活动链表头部（部分路径经 LRU 缓存批量加入） |
| 非活动页被再次访问 | 匿名页：任一映射 PTE 的 Accessed 置位即升级到活动链表；文件页：多个进程访问，或 `PG_referenced` 置位，或最近访问过的可执行文件页 |
| 活动页老化 | `shrink_active_list()` 从活动链表尾部隔离，检查访问位后，除最近访问过的可执行文件页外全部降级到非活动链表头部 |
| 页被 mlock | 进入 `LRU_UNEVICTABLE`，不参与回收 |

### 与回收相关的页标志

| 标志 | 作用 |
|---|---|
| `PG_lru` | 页在 LRU 链表中 |
| `PG_active` | 页在活动链表（与 `PG_lru` 配合判断链表类型） |
| `PG_referenced` | 页最近被访问；文件页的第二机会信号 |
| `PG_dirty` | 脏页，回收前需回写 |
| `PG_writeback` | 正在回写；回收需等待或跳过 |
| `PG_reclaim` | 回收要求回写；回写完成后据此把页移到非活动链表尾部 |
| `PG_swapcache` | 匿名页已加入 swap cache |
| `PG_swapbacked` | 页可写入 swap，一般表示非文件页 |
| `PG_mlocked` | 页被锁定在内存，不可换出 |

### 引用计数的记账

回收流程会临时抬高再降低 `page->_count`，使"是否还有人引用"变成可判定的数字：

1. 页被进程映射 → +1；取消映射 → -1。
2. 页加入 LRU 缓存 → +1；从缓存加入 LRU 链表 → -1。
3. 页加入 `address_space` 基树 → +1；从基树摘除 → -1。
4. 文件页挂上 buffer_heads → +1；释放 buffer_heads → -1。

`shrink_page_list()` 中，隔离（+1）与加入 `address_space`（+1）之后，若解映射已去掉全部进程引用，计数恰为 **2**；此时摘除基树并减 2 即可释放。计数不为 2，说明页在回收期间又被访问，放弃本次回收。

### 扫描与执行

```
shrink_lruvec(lruvec, swappiness, sc)
  ├→ get_scan_count(): 计算四个链表各自要扫多少页框
  └→ 每轮：对 ACTIVE_ANON → INACTIVE_ANON → ACTIVE_FILE → INACTIVE_FILE
           各取 min(nr[lru], 32) 个页框，调用 shrink_list()
             ├→ 活动链表：inactive_list_is_low() 为真才 shrink_active_list()
             └→ 非活动链表：shrink_inactive_list() → shrink_page_list()
```

- 每轮每链表最多 32 个页框（`SWAP_CLUSTER_MAX`）；回收足够后是否继续扫，由回收类型决定（快速/kswapd 通常直接返回，直接回收首轮可能扫完）。
- 直接回收的 `scan_adjusted` 条件（全局回收 + 非 kswapd + 默认优先级）会让它忽略"已回收足够"继续扫，尽量多释放页框。
- 非活动匿名页过少时，`shrink_lruvec()` 末尾会从活动匿名链表补 32 个页框；写回拥塞时会 `throttle_vm_writeout()` 睡眠 100ms。

### 与教科书算法的对应

双链表 + 访问位清零的做法接近 **二次机会（Clock）/老化类** 算法：访问位给页一次"免死"机会，两次扫描之间都没被访问的页才会被回收。它与严格 LRU 的差别在于不做全局精确排序，代价是 O(1) 的链表操作。 ^[inferred]

## 未解问题

- 多代 LRU（MGLRU）、`refault distance`、workingset 检测在现代内核中已部分取代双链表，原文未覆盖。
- `get_scan_count()` 的完整比例公式与 `page_check_references()` 的判定树原文留待后续文章。
- 大页（THP）在 LRU 上的记账与扫描放大问题没有展开。 ^[ambiguous]
- swappiness 在不同内核中 0–100 与 0–200 的口径差异未澄清。 ^[ambiguous]

## 来源

- `raw/sources/Linux 操作系统/Linux 内存管理/Linux 内存回收机制.md` — 知乎文章《Linux 内存回收机制》
- 蒸馏页：[[summaries/linux-memory-reclaim-triggers]] — 回收全流程与三种回收类型
- 理论对照：[[concepts/virtual-memory-and-paging]] — 页面置换算法与工作集
- 相关：[[concepts/zone-watermark]]（何时启动扫描）、[[concepts/swap-cache-mechanism]]（匿名页换出）
