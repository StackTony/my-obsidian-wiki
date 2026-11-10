---
title: Linux 零拷贝（Zero-Copy）
category: summaries
tags: [linux, 零拷贝, sendfile, DMA, 性能优化]
aliases: [零拷贝原理, Zero-Copy, CPU COPY, DMA COPY]
source_dir: Linux 操作系统/Linux 内核 IO 栈
source_files: [==Linux IO技术==/2 Linux IO零拷贝（Zero-Copy）技术.md]
summary: 零拷贝的机制推导：CPU COPY vs DMA COPY分工、Page/Buffer Cache与VFS关系、read+send的四次拷贝与四次上下文切换、sendfile(2.1)三次拷贝、sendfile+scatter-gather(2.4)零CPU拷贝。
provenance:
  extracted: 0.90
  inferred: 0.08
  ambiguous: 0.02
base_confidence: 0.442
lifecycle: draft
lifecycle_changed: 2026-10-21
tier: supporting
created: 2026-10-21
updated: 2026-11-10
---

# Linux 零拷贝（Zero-Copy）

本页是 [[concepts/zero-copy-memory-mapping]] 的机制底稿：先说清"拷贝"由谁执行，再逐版本推导 read+send / sendfile / sendfile+scatter-gather 三条数据路径的拷贝次数与上下文切换次数。

## 核心观点

- **"零拷贝"的严格定义是：用户态与内核态之间的数据拷贝次数为 0**，而不是数据完全不移动。 ^[inferred]
- 零拷贝的三项收益：**减少 CPU 拷贝开销、减少内存带宽占用、减少上下文切换次数**。
- 数据搬运有两类执行主体，区分它们是理解一切零拷贝优化的前提：
  - **DMA COPY** —— 由 DMA 控制器在内核缓冲区与设备之间搬运
  - **CPU COPY** —— 由 CPU 在内核缓冲区与用户缓冲区（或内核缓冲区之间）搬运
- 传统 `read()` + `write()`（Socket 发送）路径的浪费在于**第 2、3 次 CPU 拷贝**：数据被原封不动地从内核拷到用户空间、又从用户空间拷回内核。
- `sendfile()` 的演进方向很清晰：**先把用户态这一环拿掉（消除 2 次 CPU 拷贝中的 1 次），再让网卡直接从页缓存取数据（消除最后 1 次）**。

## 关键细节

### 内核数据结构关系

- 早期 Page Cache 与 Buffer Cache 是两套独立缓存，**2.4 之后合并**。
- 层次关系：**VFS 只与 Page Cache 交互**，具体文件系统通过 Buffer Cache 与块设备交互。每一个 Page Cache 包含若干 Buffer Cache。
- 页缓存的核心属性包括**基数树（Radix Tree）索引 + LRU 链表 + address_space**，`mmap` 让用户态指针直接落在页缓存上，从而省掉"内核缓冲区→用户缓冲区"的拷贝。详见 [[summaries/linux-page-cache]]。
- 操作系统在内核态维护"内核缓冲区"（kernel buffer）出于两项性能优化需要：**readahead cache**（预读后续数据）和**异步写入**（write 后不必等磁盘完成）。但这也导致数据在到达应用程序前可能被多次拷贝。

### mmap 的内部机制

mmap 将 Cache 项映射到用户空间，使应用程序可像使用内存指针一样访问文件。内核采用请求页面机制实现：

1. 应用程序调用 `mmap()`，陷入内核调用 `dommappgoff()`，从地址空间分配一段区域作为映射地址，用 VMA（vm_area_struct）结构代表该区域后返回
2. 应用程序访问返回的地址指针时，虚实映射尚未建立，触发**缺页中断**
3. 缺页中断处理函数通过 VMA 判断该区域属于文件映射，调用具体文件系统的接口读入相应的 Page Cache 项，并填写虚实映射表
4. 此后应用程序即可正常访问相应的内存区域

### 模型一：read + send（传统路径）

```
用户态 read() ──①上下文切换──> 内核
  ┌── DMA COPY：磁盘 → 内核缓冲区（Page Cache）
  └── CPU COPY：内核缓冲区 → 用户缓冲区           ← 浪费
用户态 send() ──②上下文切换──> 内核
  ┌── CPU COPY：用户缓冲区 → Socket 缓冲区         ← 浪费
  └── DMA COPY：Socket 缓冲区 → 网卡
③上下文切换回用户态
```

**合计：4 次拷贝（2 次 DMA + 2 次 CPU）+ 4 次上下文切换 + 2 次 CPU 中断。**

其中第 2、3 次拷贝发生在 CPU 上，对大文件传输（如 1GB）意味着可观的 `memcpy` 开销与缓存污染。

### 模型二：sendfile（Linux 2.1）

用户态不再参与数据搬运，数据从页缓存直接进入 Socket 缓冲区：

**合计：3 次拷贝（2 次 DMA + 1 次 CPU）+ 2 次上下文切换 + 1 次 CPU 中断。**

相比传统路径省掉了 1 次 CPU 拷贝与 2 次上下文切换，但内核仍需把数据从页缓存 CPU 拷贝到 Socket 缓冲区。

### 模型三：sendfile + scatter-gather（Linux 2.4+）

当网卡支持 **SG-DMA（scatter-gather DMA）** 时，内核只把数据的位置与长度（描述符）写入 Socket 缓冲区，DMA 控制器直接按描述符从页缓存取数据发送：

**合计：2 次 DMA 拷贝、0 次 CPU 拷贝、2 次上下文切换。**

这就是"真正的零拷贝"——数据在用户态与内核态之间没有任何拷贝。

sendfile 相对传统 I/O 通过减少 2 次上下文切换和 1 次 CPU COPY，可将网络数据 I/O 性能提高 50% 以上。 ^[ambiguous]

### 接口约束

```c
ssize_t sendfile(int out_fd, int in_fd, off_t *offset, size_t count);
```

- `in_fd` 必须是**真实的文件**（支持 mmap），不能是 Socket 或管道
- `out_fd` 必须是 **Socket**
- 数据全程不经过用户空间，因此**无法在传输途中修改数据**（加密/压缩/协议改写都不行）

系统调用与工具选型对比见 [[concepts/zero-copy-memory-mapping]]。

## 未解问题

- sendfile 的 50% 性能提升为原文声称的网络数据场景数据（原文标注"未亲测"），实际收益取决于文件大小、网卡能力和并发量。 ^[ambiguous]
- Socket 缓冲区残留的那 1 次 CPU 拷贝（模型二）与页缓存-描述符机制（模型三）的取舍条件：何种网卡/驱动配置下 SG-DMA 才可用，原文未详细说明。 ^[inferred]
- 零拷贝与 Direct I/O、io_uring 的组合关系原文未涉及。 ^[inferred]

## 来源

- [[concepts/zero-copy-memory-mapping]] — 零拷贝工具组与选型指南
- [[summaries/linux-page-cache]] — Page Cache 的基数树与 LRU 结构
- [[concepts/linux-io-stack]] — Linux IO 栈层次
- `raw/sources/Linux 操作系统/Linux 内核 IO 栈/Linux IO技术/2 Linux IO零拷贝（Zero-Copy）技术.md`（原文：zhuanlan.zhihu.com/p/430848775）
