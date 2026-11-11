---
title: Linux IO模型体系
category: concepts
tags: [linux, IO, epoll, 多路复用, 缓存IO]
aliases: [Linux IO模型, IO多路复用, select poll epoll, 缓存IO与直接IO]
source_dir: Linux 操作系统/Linux 内核 IO 栈
source_files: [1 Linux IO类型.md, Linux IO分类汇总/Linux 直接IO、缓存IO、内存映射mmap.md, "==Linux IO技术==/1 Linux IO多路复用（select、poll、epoll）技术.md"]
summary: Linux IO模型体系：五种IO模型、select/poll/epoll对比（epoll红黑树+就绪链表实现O(1)）、缓存IO vs 直接IO（O_DIRECT绕过Page Cache），及Buffered IO/mmap/Direct IO在IO栈中的位置关系。
provenance:
  extracted: 0.78
  inferred: 0.18
  ambiguous: 0.04
base_confidence: 0.775
lifecycle: draft
lifecycle_changed: 2026-11-10
tier: supporting
created: 2026-11-10
updated: 2026-11-11
relationships:
  - target: "[[concepts/linux-io-stack]]"
    type: related_to
  - target: "[[concepts/zero-copy-memory-mapping]]"
    type: related_to
  - target: "[[concepts/linux-memory-management]]"
    type: uses
---

# Linux IO模型体系

Linux IO模型描述的是用户进程如何发起和等待IO操作完成。从"进程是否阻塞等待"和"数据如何搬运"两个维度，可将IO模型分为五种；从"数据是否经过内核缓存"维度，又分为缓存IO与直接IO。理解这些模型的关键前提是IO操作的两阶段性。

## 核心观点

- IO操作分两个阶段：**数据准备阶段**（内核从设备读取数据到内核缓冲区）和**数据拷贝阶段**（内核缓冲区→用户缓冲区）。"IO就绪"指第一阶段完成。
- 五种IO模型的区别在于进程如何感知和响应这两个阶段：阻塞IO全程等待、非阻塞IO轮询、多路复用由内核通知就绪、信号驱动由内核发信号、异步IO全程不等待。 ^[inferred]
- select/poll/epoll是IO多路复用的三代实现，核心进化方向是**消除内核遍历开销**：select/poll每次调用都遍历全部FD（O(n)），epoll用红黑树+就绪链表+回调机制实现O(1)。
- 缓存IO（默认）在VFS与真实文件系统之间插入Page Cache，减少磁盘IO但多一次内存拷贝；直接IO（O_DIRECT）绕过Page Cache，数据直接在用户空间与块设备间传输，适合自管理缓存的数据库。
- 在IO栈中，Buffered IO、mmap、Direct IO分别位于不同层次：Buffered IO经过Page Cache全路径，mmap把Page Cache映射到用户地址空间省掉一次拷贝，Direct IO直接对接块层放弃Page Cache。

## 关键细节

### 五种IO模型

| 模型 | 数据准备阶段 | 数据拷贝阶段 | 典型接口 |
|------|-------------|-------------|----------|
| 阻塞IO（BIO） | 阻塞等待 | 阻塞等待 | read()/write() |
| 非阻塞IO | 轮询检查（O_NONBLOCK） | 阻塞等待 | read(O_NONBLOCK) |
| IO多路复用 | 内核通知就绪（阻塞等待） | 阻塞等待 | select()/poll()/epoll_wait() |
| 信号驱动IO | 内核发信号通知 | 阻塞等待 | fcntl(FASYNC)+SIGIO |
| 异步IO（AIO） | 不等待 | 不等待（内核完成全部） | aio_read()/io_uring |

阻塞IO是传统模型：`read()`触发用户态→内核态切换，DMA将数据从磁盘拷到内核Read Buffer，CPU再拷到用户Buffer，最后切回用户态。单次read涉及2次上下文切换+1次DMA拷贝+1次CPU拷贝。

非阻塞IO设置`O_NONBLOCK`标志后，数据未就绪时`read()`立即返回EAGAIN，进程需轮询检查，存在空轮询浪费CPU的问题。

信号驱动IO通过`FASYNC`标志注册，内核在数据就绪时向进程发送SIGIO信号，进程在信号处理函数中发起实际IO操作。 ^[inferred]

异步IO由内核完成全部两阶段工作后通知进程，进程全程不阻塞。Linux 5.1引入的io_uring是现代异步IO实现，详见 [[concepts/zero-copy-memory-mapping]]。

### select vs poll vs epoll

#### 文件描述符（FD）与IO就绪

Linux中"一切皆文件"，网络Socket、磁盘文件、管道都对应一个整数型FD（标准输入=0，标准输出=1，标准错误=2，新建从3开始）。IO多路复用的核心是**一个线程管理多个FD，仅在FD就绪时才进行IO操作**，避免了BIO的"一连接一线程"和纯非阻塞IO的"空轮询"问题。

#### 三代多路复用对比

| 特性 | select | poll | epoll（Linux 2.6+） |
|------|--------|------|---------------------|
| FD数量限制 | 默认1024 | 无限制（仅受内存） | 无限制（仅受系统FD上限） |
| 时间复杂度 | O(n)（遍历所有FD） | O(n)（遍历所有FD） | O(1)（仅遍历就绪FD） |
| 存储结构 | fd_set（位图） | pollfd数组 | 红黑树+就绪链表 |
| 就绪FD排查 | 用户遍历所有FD | 用户遍历所有FD | 内核返回就绪链表 |
| 数据拷贝 | 每次调用重新拷贝FD集合 | 每次调用重新拷贝pollfd | 仅注册时拷贝，后续复用 |
| 事件触发 | 仅水平触发（LT） | 仅水平触发（LT） | LT（默认）+ 边缘触发（ET） |

**select**（POSIX标准）：用户通过`fd_set`位图传入FD集合，内核遍历全部FD检查就绪状态并修改位图。每次调用需重新传入FD集合（内核清空就绪标记），存在重复的用户态→内核态拷贝。核心API：`select(nfds, readfds, writefds, exceptfds, timeout)`，辅以`FD_ZERO`/`FD_SET`/`FD_ISSET`/`FD_CLR`宏操作fd_set。

**poll**：用`struct pollfd`数组替代`fd_set`，解除1024限制。`events`（用户关注）和`revents`（内核返回）分离，无需每次重置集合。但内核仍需遍历所有FD，核心O(n)问题未解决。

**epoll**（Linux 2.6+）三个核心组件彻底解决select/poll的性能问题：

| 组件 | 作用 |
|------|------|
| 红黑树 | 存储注册的FD和事件，增删改查O(log n) |
| 就绪链表 | 内核主动将就绪FD加入链表，无需遍历所有FD |
| 回调机制 | 内核为每个FD注册回调，数据准备完成时自动加入就绪链表 |

epoll执行流程：`epoll_create()`创建实例（含红黑树+就绪链表+等待队列）→ `epoll_ctl(ADD/MOD/DEL)`注册FD并绑定回调 → `epoll_wait()`检查就绪链表（空则挂起等待）→ 从就绪链表获取FD（O(1)）。就绪FD处理完成后无需重新注册（除非主动删除）。

**边缘触发（ET）vs 水平触发（LT）**：
- LT（默认）：FD就绪后每次`epoll_wait()`都返回，直到数据被读完
- ET：仅在FD从"未就绪"→"就绪"时通知一次，需一次性读完所有数据，性能更高（减少重复通知）但编程复杂

epoll通常与非阻塞FD配合使用，避免数据拷贝阶段阻塞。Java NIO的`Selector`在Linux下默认使用epoll——`Selector.open()`对应`epoll_create()`，`register()`对应`epoll_ctl(ADD)`，`select()`对应`epoll_wait()`。

### 缓存IO vs 直接IO

#### 缓存IO（Buffered I/O，默认）

不指定`O_DIRECT`标志时默认使用缓存IO。数据路径：用户空间 ↔ Page Cache ↔ 块设备。缓存IO位于虚拟文件系统与真实文件系统中间。

- 优点：减少对块设备的IO操作（命中Page Cache时无需磁盘IO），readahead预读和异步写入提升性能
- 缺点：读写都先经过缓存再复制到用户空间，多一次内存拷贝

Page Cache读取策略：先检查数据是否在Page Cache中——命中则直接返回，未命中则内核调度块IO从磁盘读取，并预读紧随其后的少数页面（通常3页），然后放入Page Cache。

Page Cache写入策略：数据先写入Page Cache，对应页标记为"脏"并加入脏页链表，由flusher回写线程异步写回磁盘。脏页写回触发条件：空闲内存低于特定阈值、脏页在内存中驻留超过特定阈值、用户调用`sync()`/`fsync()`。

#### 直接IO（Direct I/O，O_DIRECT）

`open()`时指定`O_DIRECT`标志，用户IO操作直接与块设备交互，不经过Page Cache缓存。

- 优点：不对IO数据块缓存，减少一次内存拷贝；应用程序可自行管理缓存，更加灵活
- 缺点：每次IO操作都直接与块设备交互，增加了对块设备的读写操作，失去Page Cache的预读和合并优化

内核实现路径（以ext2读取为例）：

```
sys_open() → filp_open() → dentry_open()     # flags保存到file->f_flags
sys_read() → generic_file_read()              # 检查 f_flags & O_DIRECT
  → generic_file_direct_IO()                  # 核心分流
    → map_user_kiobuf()                       # 为用户虚拟内存申请物理页
    → direct_IO() (ext2_direct_IO)            # 文件系统特定接口
      → generic_direct_IO()
        → get_block()                         # 获取数据块号
        → brw_kiovec()                        # 提交IO到通用块层
          → submit_bh()                       # 最终提交块IO请求
```

`brw_kiovec()`完成三项工作：设置数据保存地址（用户空间内存）、设置完成回调`end_buffer_io_kiobuf()`、提交`submit_bh()`到通用块层。数据直接保存到用户空间内存，不经过内核缓存中转。

**对齐要求**：mmap和Direct IO要求数据按页对齐；Direct IO还要求读写大小是底层存储设备块大小的整数倍（Linux 2.4还要求是文件系统逻辑块的整数倍）。接口越底层，效率提升越大，但应用程序需要做更多工作。 ^[inferred]

### IO栈中的三种机制定位

| 机制 | 在IO栈中的位置 | 拷贝次数 | 特点 |
|------|---------------|----------|------|
| Buffered IO | VFS→Page Cache→Block层 | 2次（DMA+CPU） | 默认，支持自由偏移读写 |
| mmap | Page Cache映射到用户地址空间 | 1次DMA（省掉CPU拷贝） | 随机访问高效，需处理SIGBUS |
| Direct IO | 用户空间→Block层（跳过Page Cache） | 1次DMA | 自管理缓存，需对齐 |

从冷文件读取的完整路径：`open()` → `read()` → 文件系统层发现Page Cache未命中 → 创建Page Cache关联扇区 → 请求进入块设备层IO队列 → 调度后到设备驱动层 → DMA读取磁盘扇区到Page Cache → CPU拷贝到用户Buffer。mmap省掉最后一步CPU拷贝（用户指针直接指向页缓存），Direct IO省掉Page Cache层（DMA直接在用户空间与磁盘间传输）。

### 补充：三者各自的"为什么"

- **内核缓冲区存在的理由**：读时若数据已在缓冲则免去一次磁盘访问；写时只写缓冲即返回成功，落盘由策略延时完成——这正是它快的来源，也是断电丢数据的来源。
- **Direct IO 的代价与搭配**：数据不在应用缓存时每次都直接读盘，缓慢；因此实践中常与异步 IO 结合（发起请求后线程继续做别的事，不阻塞等待）。数据库是典型用户——它要自己实现缓存与写延迟策略以配合查询优化，同时省掉内核缓冲区占用的系统内存。
- **mmap 的本质是"取消 IO 操作"**：文件位置与进程地址空间的一段一一对应后，读写内存即读写文件，不再需要"申请缓冲 → 读入 → 回写 → 释放"四步；大量数据传输时效率显著。代价是缺页与 SIGBUS 的处理要应用自己兜住。 ^[inferred]

### I/O Buffering层次

用户数据到达磁盘经过两层缓冲：

1. **stdio buffer**（用户态）：C标准库的跨平台封装函数（fread/fwrite等），聚合小尺寸读写减少系统调用次数。`fflush()`主动刷新，`setbuf()`可设置或取消缓冲。
2. **Kernel buffer cache**（内核态）：系统调用read/write与真实磁盘之间。Linux中文件缓存称Page Cache（缓存文件内容，与文件系统相关），设备缓存称Buffer Cache（缓存存储设备块/扇区，文件系统元数据缓存在此）。VFS只与Page Cache交互，具体文件系统通过Buffer Cache与块设备交互。详见 [[summaries/linux-page-cache]]。

## 未解问题

- io_uring作为现代异步IO对五种模型分类的影响——它模糊了多路复用和异步IO的边界。 ^[inferred]
- Direct IO在NVMe多队列路径下的完整数据流（是否经过blk-mq调度器）缺少源文件支撑。 ^[inferred]

## 来源

- [[concepts/linux-io-stack]] — IO栈分层架构与Block层调度
- [[concepts/zero-copy-memory-mapping]] — 零拷贝工具组（sendfile/splice/mmap/io_uring/DPDK）
- [[summaries/linux-page-cache]] — Page Cache机制详解
- [[concepts/linux-memory-management]] — 内核内存管理
