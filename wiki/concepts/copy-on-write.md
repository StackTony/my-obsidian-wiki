---
title: Copy-on-Write（写时复制）
category: concepts
tags: [linux, 内存, COW, fork, 虚拟内存]
aliases: [COW, 写时复制, Copy On Write, 写保护缺页]
relationships:
  - target: "[[concepts/virtual-memory-and-paging]]"
    type: extends
  - target: "[[concepts/linux-memory-management]]"
    type: related_to
  - target: "[[concepts/zero-copy-memory-mapping]]"
    type: related_to
  - target: "[[concepts/overlayfs-container-images]]"
    type: related_to
  - target: "[[summaries/linux-page-cache]]"
    type: related_to
  - target: "[[summaries/linux-copy-on-write]]"
    type: derived_from
source_dir: Linux 操作系统/Linux 内存管理
source_files: [Linux Coye On Write（写时复制）.md]
summary: COW 把复制推迟到写：fork 只复制页表、父子共享物理页并把私有可写 PTE 置只读；写方触发写保护缺页，do_wp_page 复用独占页或复制新页。同一思想在 mmap 私有映射与 OverlayFS copy-up 中再现。
provenance:
  extracted: 0.71
  inferred: 0.21
  ambiguous: 0.08
base_confidence: 0.44
lifecycle: draft
lifecycle_changed: 2026-11-12
tier: supporting
created: 2026-11-12
updated: 2026-11-12
---

# Copy-on-Write（写时复制）

写时复制（Copy-on-Write, COW）是一种**延迟复制**的资源管理策略：读取阶段多方共享同一份数据，只有当某一方真正要修改时，才为它复制出一份私有副本。在 Linux 内存管理中，它同时解决了 fork 的拷贝成本问题与私有映射的语义问题；同一思想在文件系统与块设备层以不同粒度重复出现。

## 核心观点

- COW 的本质是**用写保护位把复制决策推迟到第一次写**，把 eager copy 变成 lazy copy。
- 正确性依赖两个不变量：共享期间物理页内容对各方一致（因此必须只读）；写方一旦要改，必须先拿到私有副本再改。
- 收益与"写比例"成正比：fork 后紧接 `exec` 的典型场景（子进程几乎不写父进程数据）收益最大；若父子都大量写页，COW 只是把复制成本延后，并额外付出每次首写的缺页开销。 ^[inferred]
- 代价集中在缺页路径：每次首次写都要陷入内核、分配页、拷贝整页、更新页表并刷 TLB，比顺序拷贝更容易造成延迟抖动。 ^[inferred]
- 同一思想在不同层次反复出现：**页级**（fork、mmap 私有映射）、**文件级**（OverlayFS copy-up）、**块级**（devicemapper）、**文件系统级**（btrfs/zfs 快照），粒度与触发点各不相同。

## 关键细节

### 页级 COW 的三个阶段

1. **建立共享**：fork 走 `copy_page_range`，命中 `is_cow_mapping`（私有且可写）的页表项，父子两侧都用 `ptep_set_wrprotect`/`pte_wrprotect` 置只读，物理页不复制。
2. **触发分离**：任一方写入只读 PTE → 保护性缺页 → `handle_pte_fault` 发现 `FAULT_FLAG_WRITE` 且 `!pte_write(entry)` → `do_wp_page`。
3. **完成分离**：真共享时 `wp_page_copy` 分配新页、拷贝内容、重映射；若页面实际只归当前进程（`reuse_swap_page` 且 `total_mapcount == 1`），`wp_page_reuse` 直接恢复可写，不复制。

完整源码路径与分支见 [[summaries/linux-copy-on-write]]。

### do_wp_page 判定速查

| 问题 | 判定 | 结果 |
|------|------|------|
| 是特殊映射吗？ | `vm_normal_page == NULL` | `wp_pfn_shared` 或 `wp_page_copy` |
| 是独占匿名页吗？ | `PageAnon && !PageKsm` 且 `reuse_swap_page`、`total_mapcount == 1` | `wp_page_reuse`（不复制） |
| 非普通匿名页（文件页/KSM 页）且 VMA 可写又共享？ | `VM_WRITE \| VM_SHARED` | `wp_page_shared` |
| 其余（匿名页复用失败，或普通私有共享页） | — | `wp_page_copy`（复制新页） |

### 与其他机制的边界

- **mmap 私有文件映射**：只读访问直接映射 Page Cache 页；首次写触发 COW，副本转为匿名页（计入 AnonPages），此后与文件内容脱钩、也不再回写文件。见 [[summaries/linux-page-cache]]。
- **OverlayFS copy-up**：COW 的复制单位是**整个文件**而非 4KB 页，因此改 1 字节也可能复制 100MB 文件（实测首次写慢 263 倍）。见 [[concepts/overlayfs-container-images]]。
- **零拷贝**：目标是**消除**复制（sendfile/splice），COW 是**推迟**复制；两者都靠"共享 + 延迟"省成本，但优化的对象不同——前者省数据搬运，后者省 fork 时的全量拷贝。 ^[inferred]
- **fork + exec**：shell 场景下 COW 的收益最大，因为子进程随即 `exec` 替换整个地址空间，几乎不写父进程的页。 ^[inferred]

## 未解问题

- 透明大页（THP）下的 COW 粒度未在来源中讨论：是整 2MB 复制还是先拆分，需要更多资料确认。 ^[ambiguous]
- KSM 合并页与 COW 共用只读页时的交互边界（`PageKsm` 分支为何跳过复用）不清楚。 ^[ambiguous]
- `wp_page_copy` 内部的页分配策略、memcg 计费、页锁竞争与 TLB flush 时机缺少细节。
- COW 缺页在延迟敏感负载上的量化影响（相对顺序拷贝的开销比）缺少实测数据。

## 来源

- [[summaries/linux-copy-on-write]] — 来源文档蒸馏（fork/copy_page_range/do_wp_page 源码路径）
- 原始文档：`Linux 操作系统/Linux 内存管理/Linux Coye On Write（写时复制）.md`
- 上游原理：[[concepts/virtual-memory-and-paging]]、[[concepts/linux-memory-management]]
