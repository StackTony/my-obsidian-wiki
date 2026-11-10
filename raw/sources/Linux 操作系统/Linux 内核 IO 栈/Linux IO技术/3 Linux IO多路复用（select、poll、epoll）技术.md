原文： https://www.cnblogs.com/qixing/p/19682955

IO多路复用是解决高并发IO的核心技术（Java NIO的`Selector`、Redis、Nginx等都基于它实现），select、poll、epoll是Linux系统下三种主流的多路复用机制，本质都是让**一个线程管理多个IO文件描述符（FD）**，仅在FD就绪（可读/可写/异常）时才进行IO操作，避免了BIO的“一连接一线程”和纯非阻塞IO的“空轮询”问题。

本文会从**核心概念**、**底层原理**、**对比分析**、**使用场景**四个维度，由浅入深讲清楚这三种机制的本质区别和实现逻辑。

## 一、前置基础：文件描述符（FD）与IO就绪

### 1. 文件描述符（FD）

Linux中“一切皆文件”，网络套接字（Socket）、磁盘文件、管道等都对应一个**整数型的文件描述符**（File Descriptor），内核通过FD管理所有IO资源。

- 标准输入：FD=0
- 标准输出：FD=1
- 标准错误：FD=2
- 新创建的Socket/文件：从3开始递增

### 2. IO就绪

IO操作分为两个阶段（以读Socket为例）：

1. **数据准备阶段**：内核从网卡/磁盘读取数据到内核缓冲区（耗时，可能阻塞）；
2. **数据拷贝阶段**：内核将数据从内核缓冲区拷贝到用户缓冲区（耗时短）。

“IO就绪”指**第一阶段完成**，此时FD可无阻塞地进行读写操作。IO多路复用的核心就是“监听多个FD的就绪状态”。

## 二、select：第一代多路复用

### 1. 底层原理

select是最早的多路复用接口（POSIX标准），核心逻辑是**内核遍历用户传入的FD集合，检查是否就绪**。

#### 执行流程

#### 核心细节

- **FD集合存储**：用户进程通过`fd_set`结构体（位图）传入要监听的FD，内核修改该位图标记就绪的FD；
- **FD数量限制**：`fd_set`的大小固定（默认1024），因此select最多监听1024个FD；
- **内核遍历逻辑**：每次调用select，内核必须遍历所有传入的FD（即使只有1个就绪），时间复杂度$O(n)$；
- **数据拷贝**：每次调用select，用户需重新传入FD集合（内核会清空就绪标记），存在重复的用户态→内核态拷贝。

### 2. 核心API（C语言）

```
#include <sys/select.h>

// 参数：最大FD+1、读FD集合、写FD集合、异常FD集合、超时时间
int select(int nfds, fd_set *readfds, fd_set *writefds, fd_set *exceptfds, struct timeval *timeout);

// 辅助宏：操作fd_set
FD_ZERO(fd_set *set);       // 清空FD集合
FD_SET(int fd, fd_set *set); // 将FD加入集合
FD_ISSET(int fd, fd_set *set); // 检查FD是否就绪
FD_CLR(int fd, fd_set *set); // 从集合移除FD
```

### 3. 缺点

1. **FD数量限制**：默认最大1024（可修改内核参数，但不推荐）；
2. **性能低效**：内核每次需遍历所有FD，FD越多，遍历耗时越长；
3. **重复拷贝**：每次调用select都要重新传入FD集合，且就绪FD需用户进程自己遍历排查；
4. **内核/用户态切换成本**：每次调用都要切换，且无就绪FD时进程会被挂起。

## 三、poll：select的改进版

### 1. 底层原理

poll解决了select的“FD数量限制”问题，核心逻辑与select一致，但存储FD的结构不同。

#### 执行流程

#### 核心细节

- **FD存储结构**：使用`struct pollfd`数组替代`fd_set`，数组大小无固定限制（仅受系统内存限制）：
    
    ```
    struct pollfd {
        int fd;         // 要监听的文件描述符
        short events;   // 要监听的事件（POLLIN/POLLOUT等）
        short revents;  // 内核返回的就绪事件（由内核修改）
    };
    ```
    
- **遍历逻辑**：与select一致，内核仍需遍历所有传入的FD，时间复杂度$O(n)$；
- **数据拷贝**：仍需每次传入pollfd数组，存在重复拷贝；
- **事件分离**：`events`（用户关注的事件）和`revents`（内核返回的就绪事件）分离，无需每次重置集合（select的fd_set会被内核清空）。

### 2. 核心API（C语言）

```
#include <poll.h>

// 参数：pollfd数组、数组长度、超时时间（毫秒）
int poll(struct pollfd *fds, nfds_t nfds, int timeout);
```

### 3. 改进与缺点

#### 改进

- 解除了FD数量限制（无1024上限）；
- 无需每次重置FD集合（events和revents分离）。

#### 缺点

- 核心问题未解决：内核仍需遍历所有FD，FD越多性能越差（$O(n)$）；
- 仍需用户进程遍历排查就绪FD；
- 重复的用户态→内核态拷贝问题依然存在。

## 四、epoll：Linux高性能多路复用

epoll（Linux 2.6+引入）是select/poll的终极改进版，专为高并发场景设计（Java NIO的`Selector`在Linux下默认使用epoll），核心是**事件驱动+红黑树+就绪链表**，时间复杂度优化至$O(1)$。

### 1. 核心设计

epoll引入了三个核心组件，彻底解决select/poll的性能问题：

|组件|作用|
|---|---|
|红黑树|存储用户注册的所有FD和关注的事件（增删改查效率高，$O(logn)$）|
|就绪链表|内核主动将就绪的FD加入链表，无需遍历所有FD|
|回调机制|内核为每个FD注册回调函数，数据准备完成时自动将FD加入就绪链表|

### 2. 底层原理

epoll的执行流程分为“初始化-注册FD-等待就绪-处理事件”四个阶段：

Syntax error in textmermaid version 11.16.0

#### 核心细节

1. **初始化（epoll_create）**：
    
    - 用户进程调用`epoll_create()`，内核创建一个epoll实例，包含：
        - 红黑树：存储所有注册的FD和事件；
        - 就绪链表：存储就绪的FD；
        - 等待队列：存储调用`epoll_wait()`的进程。
2. **注册FD（epoll_ctl）**：
    
    - 用户进程调用`epoll_ctl()`（ADD/MOD/DEL），将FD和关注的事件（EPOLLIN/EPOLLOUT）注册到红黑树；
    - 内核为该FD的驱动程序注册回调函数：当数据准备完成时，驱动自动将FD加入就绪链表。
3. **等待就绪（epoll_wait）**：
    
    - 用户进程调用`epoll_wait()`，内核检查就绪链表：
        - 若链表非空：直接返回就绪FD数量，用户进程可遍历就绪链表获取FD；
        - 若链表为空：将进程挂起到等待队列，直到有FD就绪或超时。
4. **事件处理**：
    
    - 用户进程从就绪链表中直接获取就绪FD，无需遍历所有注册的FD，时间复杂度$O(1)$；
    - 就绪FD处理完成后，无需重新注册（除非主动删除）。

### 3. 核心API（C语言）

```
#include <sys/epoll.h>

// 1. 创建epoll实例，返回epoll_fd（文件描述符）
int epoll_create(int size); // size仅为提示，无实际限制

// 2. 注册/修改/删除FD和事件
// 参数：epoll_fd、操作类型（EPOLL_CTL_ADD/MOD/DEL）、要监听的FD、事件结构体
int epoll_ctl(int epfd, int op, int fd, struct epoll_event *event);

// 3. 等待就绪事件
// 参数：epoll_fd、存储就绪事件的数组、数组大小、超时时间（毫秒）
int epoll_wait(int epfd, struct epoll_event *events, int maxevents, int timeout);

// 事件结构体
struct epoll_event {
    uint32_t events; // 关注的事件（EPOLLIN/POLLOUT/EPOLLERR等）
    epoll_data_t data; // 关联的FD（或自定义数据）
};
typedef union epoll_data {
    void *ptr;
    int fd;         // 核心：存储就绪的FD
    uint32_t u32;
    uint64_t u64;
} epoll_data_t;
```

### 4. 关键特性

- **边缘触发（ET）vs 水平触发（LT）**：
    - 水平触发（LT，默认）：只要FD就绪，每次调用`epoll_wait()`都会返回该FD（直到数据被读完）；
    - 边缘触发（ET）：仅在FD从“未就绪”→“就绪”时返回一次（需一次性读完所有数据，否则后续不会再通知），性能更高（减少重复通知）。
- **无FD数量限制**：仅受系统最大文件描述符数（`/proc/sys/fs/file-max`）限制；
- **零拷贝/少拷贝**：FD注册后无需重复传入，就绪事件直接从内核链表拷贝到用户态，拷贝成本极低；
- **非阻塞IO**：epoll通常与非阻塞FD配合使用，避免数据拷贝阶段阻塞。

## 五、select、poll、epoll核心对比

|特性|select|poll|epoll（Linux 2.6+）|
|---|---|---|---|
|FD数量限制|默认1024（可改内核参数）|无（仅受内存/系统限制）|无（仅受系统FD上限限制）|
|时间复杂度|$O(n)$（遍历所有FD）|$O(n)$（遍历所有FD）|$O(1)$（仅遍历就绪FD）|
|存储结构|fd_set（位图）|pollfd数组|红黑树+就绪链表|
|就绪FD排查|用户进程遍历所有FD|用户进程遍历所有FD|内核返回就绪链表，直接遍历|
|数据拷贝|每次调用重新拷贝FD集合|每次调用重新拷贝pollfd数组|仅注册时拷贝，后续复用|
|事件触发方式|水平触发（LT）|水平触发（LT）|LT（默认）+ 边缘触发（ET）|
|适用场景|低并发（FD<1024）|中并发（FD<10000）|高并发（FD>10000，如Nginx/Redis）|
|内核开销|高（每次遍历所有FD）|高（每次遍历所有FD）|低（仅处理就绪FD）|

## 六、实际应用场景

### 1. select

- 兼容性优先的场景（跨平台，如Windows/macOS/Linux都支持）；
- 低并发场景（如嵌入式设备、简单工具程序，FD数量少）；
- 老系统兼容（Linux 2.4及以下）。

### 2. poll

- 需突破1024 FD限制，但并发量不高（如几千个FD）；
- 跨平台场景（macOS无epoll，仅支持poll/select）；
- 无需高性能的中低并发服务。

### 3. epoll

- 高并发网络服务（Nginx、Redis、Netty、Tomcat NIO模式）；
- 百万级连接场景（如直播服务器、IM聊天系统）；
- 对性能要求极高的中间件（如消息队列、数据库代理）。

## 七、Java NIO与epoll的关联

Java的`Selector`（多路复用器）在不同操作系统下的底层实现：

- Linux：默认使用epoll（JDK 1.5+）；
- Windows：使用IOCP（异步IO）；
- macOS/BSD：使用kqueue（类似epoll的高性能多路复用）；
- 老Linux系统：降级为poll/select。

`Selector`的核心逻辑与epoll完全对齐：

- `Selector.open()` → `epoll_create()`；
- `SocketChannel.register(selector, OP_READ)` → `epoll_ctl(ADD)`；
- `selector.select()` → `epoll_wait()`；
- `selector.selectedKeys()` → epoll的就绪链表。

---

### 总结

1. **核心进化**：select（有限FD+遍历）→ poll（无FD限制+遍历）→ epoll（事件驱动+$O(1)$），核心目标是降低高并发下的内核遍历开销；
2. **性能关键**：epoll的优势在于“就绪事件主动通知”（回调+就绪链表），无需遍历所有FD，是高并发场景的最优选择；
3. **使用原则**：低并发/跨平台用select/poll，高并发（Linux）用epoll，Java NIO/Netty会自动适配最优实现。