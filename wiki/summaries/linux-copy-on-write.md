---
title: Linux 写时复制（Copy-on-Write）内核实现
category: summaries
tags: [linux, 内核, 内存, COW, fork]
aliases: [Linux COW, COW 内核实现, Linux 写时复制实现]
relationships:
  - target: "[[concepts/copy-on-write]]"
    type: related_to
  - target: "[[concepts/virtual-memory-and-paging]]"
    type: related_to
source_dir: Linux 操作系统/Linux 内存管理
source_files: [Linux Coye On Write（写时复制）.md]
summary: fork 通过 copy_page_range 只复制页表并共享物理页，把私有可写 VMA 的父子 PTE 置只读；任一方写触发写保护缺页，do_wp_page 复用独占页或 wp_page_copy 复制新页，把复制推迟到写。
provenance:
  extracted: 0.85
  inferred: 0.10
  ambiguous: 0.05
base_confidence: 0.44
lifecycle: draft
lifecycle_changed: 2026-11-12
tier: supporting
created: 2026-11-12
updated: 2026-11-12
---

# Linux 写时复制（Copy-on-Write）内核实现

写时复制（Copy On Write, COW）是内核把"复制"从 fork 时刻推迟到第一次写时刻的优化：fork 只为子进程复制页表并共享父进程的物理页，同时把可写页在父子两侧都改成只读；任一方真正写入时才触发保护性缺页，为写方分配新页并拷贝内容。本页按"fork 做准备 → 缺页触发 → do_wp_page 分流 → 四步总结"的顺序还原这条路径。

## 核心观点

- 传统 fork 会复制父进程整个用户空间，代价有三：**占用大量内存、复制耗时、子进程通常用不到被复制的全部资源**。
- COW 的两条原则：只复制父进程的**页表**到子进程，父子共享同一物理内存；当任一方要修改某个物理页时，才触发**写保护的缺页中断**，复制共享页内容，使双方拥有各自副本。
- 因此 COW 是一种**推迟甚至避免复制**的技术，在现代操作系统中广泛使用，省下巨大的拷贝开销。
- fork 阶段本身不复制任何物理页，只做页表级准备：把满足条件的页表项改成只读，为后续 COW 缺页埋好触发点。
- 真正决定"复制还是复用"的是缺页路径上的 `do_wp_page`：若页面实际已只属于当前进程，直接恢复可写即可，根本不需要复制。

## 关键细节

### fork 侧：copy_page_range 与写保护

fork 创建子进程的入口在 `kernel/fork.c`，页表复制按层级展开：

- `copy_pud_range` — 页表上级目录
- `copy_pmd_range` — 页中间目录
- `copy_pte_range` — 页表项

在 `copy_pte_range` 中，对需要 COW 的映射同时改写父子两侧的页表项：

```c
if (is_cow_mapping(vm_flags)) {
    ptep_set_wrprotect(src_mm, addr, src_pte);  // 父进程 PTE 置只读
    pte = pte_wrprotect(pte);                   // 子进程 PTE 值置只读
}
```

`is_cow_mapping` 的判定是"私有且可写"：

```c
static inline bool is_cow_mapping(vm_flags_t flags)
{
    return (flags & (VM_SHARED | VM_MAYWRITE)) == VM_MAYWRITE;
}
```

即 VMA 不含 `VM_SHARED`、含 `VM_MAYWRITE`。此时父进程 PTE 被原地改为只读；子进程的 PTE 只是"即将写入的值"被改为只读——`copy_pte_range` 这一时刻尚未把子进程 PTE 真正写入子进程页表。

### 缺页侧：handle_pte_fault 的 COW 分支

共享期间双方都只读访问，一切正常。一旦任一方写入，硬件因 PTE 只读而触发保护性缺页，进入 `handle_pte_fault`：

```c
if (fe->flags & FAULT_FLAG_WRITE) {   // 这是一次写访问，且 vma 可写
    if (!pte_write(entry))            // 页表项却是只读
        return do_wp_page(fe, entry); // 走 COW 处理
    entry = pte_mkdirty(entry);
}
```

能走到这里，说明同时满足：**页表项存在、物理页在内存、VMA 可写、PTE 只读**——这正是 fork 阶段刻意留下的组合，也是 COW 缺页的判定条件。

### do_wp_page 的分流

`do_wp_page` 先用 `vm_normal_page` 取缺页地址对应的 `struct page`，再按页面类型分流：

| 条件 | 判定 | 处理 |
|------|------|------|
| `vm_normal_page` 返回 NULL（特殊映射，如 `VM_PFNMAP`/`VM_MIXEDMAP`） | 特殊页 | VMA 可写且共享 → `wp_pfn_shared`；否则 → `wp_page_copy` |
| `PageAnon(old_page) && !PageKsm(old_page)` | 普通匿名页 | 见下方复用判定 |
| 匿名复用判定失败，且 VMA 可写且共享 | 共享可写页 | `wp_page_shared` |
| 其余 | 真正共享的私有页 | `wp_page_copy` |

匿名页分支的两个关键动作：

- `trylock_page` 失败说明页已被他人加锁：`get_page` 后释放 PTE 锁、重新加页锁，再取 PTE 并校验是否仍是同一个 `orig_pte`；若 PTE 已变化则直接退出本次异常。
- `reuse_swap_page(old_page, &total_mapcount)` 判定该匿名页是否只被一个进程映射：是则说明页面已是"独占"，`total_mapcount == 1` 时先 `page_move_anon_rmap` 把页迁到当前进程的 `anon_vma`（避免 rmap 继续搜索父进程/兄弟进程），再 `wp_page_reuse` 恢复可写继续用——**不复制**。

其余情况进入 `wp_page_copy`：分配新物理页、拷贝旧页内容、建立写方的新页表映射，完成"分离"。

### 四步总结

1. fork 时父子共享全部物理页（各自的页表映射到同一批页框）。
2. 把需要 COW 的页表项改成只读；任一方写共享页即触发 COW 缺页。
3. 缺页处理为写方重新分配物理页，拷贝原页内容，建立新页的映射。
4. 写方继续执行，另一方不受影响——父子对私有页的访问从此"分道扬镳"。

### 实例：fork 后改一个变量

父进程 `fork()` 后执行 `c = 'v'`：父进程打印的 `&c` 与子进程打印的 `&c` 相同（虚拟地址不变），但父进程读到 `'v'`、子进程仍读到 `'a'`（物理页已不同）。这说明写操作只让写方重新申请物理页并重建映射，未写方的映射与内容保持不变。

## 未解问题

- 原文代码使用 `struct fault_env`，现代内核已改为 `struct vm_fault`，函数签名、分支结构与行号随版本变化，阅读时需对照目标内核源码。 ^[inferred]
- `PageKsm` 页面为何不进入匿名页复用分支，原文只给出判断、未解释 KSM 合并页的特殊性。 ^[ambiguous]
- `wp_page_copy` 内部的页分配、memcg 计费与 TLB flush 时序未展开。
- 原文未标注内核版本，从 `fault_env` 判断约对应 4.x 时期内核。 ^[inferred]

## 来源

- 原始文档：`Linux 操作系统/Linux 内存管理/Linux Coye On Write（写时复制）.md`
- 原文链接：https://zhuanlan.zhihu.com/p/579491341

相关综合页：[[concepts/copy-on-write]]（跨层次 COW 概念页）、[[concepts/virtual-memory-and-paging]]（缺页与页表原理）。
