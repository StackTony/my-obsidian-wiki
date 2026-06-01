---
title: System V IPC
created: 2026-06-01
updated: 2026-06-01
tags: [linux, ipc, semaphore, shared-memory, message-queue, system-v]
category: concepts
source_dir: Linux 操作系统/Linux 资源隔离/System V IPC
source_files: [System V IPC 之信号量.md, System V IPC 之共享内存.md, System V IPC 之消息队列.md, Linux Namespace  -  IPC.md]
summary: System V IPC三大机制：信号量集合、共享内存、消息队列的原理与API
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: "2026-06-01"
tier: supporting
provenance:
  extracted: 0.7
  inferred: 0.25
  ambiguous: 0.05
relationships:
  - target: "[[concepts/linux-namespace-cgroups]]"
    type: related_to
  - target: "[[concepts/linux-lock-mechanisms]]"
    type: related_to
---

# System V IPC

System V IPC 是 Unix System III 引入的进程间通信机制，包含**信号量集合**、**共享内存**、**消息队列**三种机制。这些资源持久驻留内存，除非显式释放或系统关闭。

## 与 POSIX IPC 的关键区别

System V 信号量是**信号量集合**（semaphore set），而非单个信号量。一个集合包含多个信号量，共用同一 ID。相比之下，POSIX 信号量是单个非负整数，常用于线程间同步，而 System V 信号量更适合进程间同步。 ^[inferred]

- System V 头文件：`<sys/sem.h>`；POSIX 头文件：`<semaphore.h>`
- System V API 更复杂，但提供更强的进程间同步能力

## 公共数据结构：ipc_perm

每个 IPC 资源都有 `ipc_perm` 结构记录权限信息：

```c
struct ipc_perm {
    uid_t uid;      // 所有者有效用户ID
    gid_t gid;      // 所有者有效组ID
    uid_t cuid;     // 创建者有效用户ID
    gid_t cgid;     // 创建者有效组ID
    mode_t mode;    // 访问权限
    ulong seq;      // 应用序号
    key_t key;      // IPC键
};
```

IPC 键（key）由程序员指定，类似文件路径名；IPC 标识符由内核分配，类似文件描述符。

## 三大机制概览

### 信号量集合

信号量集合用于**资源同步控制**，解决互斥共享资源的访问问题。

**数据结构**：
- `semid_ds`：信号量集元信息（包含 `ipc_perm`、信号量个数、操作时间等）
- `sem`：单个信号量的值、等待进程数、最后操作进程 PID

**核心 API**：
| 函数 | 作用 |
|------|------|
| `semget(key, nsems, flg)` | 创建/打开信号量集 |
| `semop(semid, sops, nsops)` | 原子操作信号量集 |
| `semctl(semid, semnum, cmd, arg)` | 控制/删除信号量 |

**sembuf 结构**定义单次操作：
```c
struct sembuf {
    short sem_num;   // 信号量编号
    short sem_op;    // 操作值（>0释放，<0请求，=0等待归零）
    short sem_flg;   // IPC_NOWAIT | SEM_UNDO
};
```

**SEM_UNDO 机制**：进程退出时自动撤销其信号量操作，防止异常退出导致资源永久锁定。

### 共享内存

共享内存是**最快的 IPC 机制**——数据直接映射到进程地址空间，无需内核中转。但需要配合信号量解决同步问题。

**数据结构**：`shmid_ds` 记录共享内存大小、附加进程数、创建/最近操作进程 PID 等。

**核心 API**：
| 函数 | 作用 |
|------|------|
| `shmget(key, size, flg)` | 创建/打开共享内存 |
| `shmat(shmid, addr, flg)` | 附加到进程地址空间 |
| `shmdt(addr)` | 分离共享内存 |
| `shmctl(shmid, cmd, buf)` | 控制/删除共享内存 |

共享内存的不足：多进程同时写入会造成数据混乱，必须使用信号量同步。 ^[inferred]

### 消息队列

消息队列保存在内核中，支持**类型过滤**接收——可按消息类型选择性读取。

**数据结构**：
- `msqid_ds`：队列元信息（消息数、字节数、最近发送/接收进程 PID 等）
- `msgbuf`：消息结构（类型 + 数据）

**核心 API**：
| 函数 | 作用 |
|------|------|
| `msgget(key, flg)` | 创建/打开消息队列 |
| `msgsnd(msqid, msgp, size, flg)` | 发送消息 |
| `msgrcv(msqid, msgp, size, typ, flg)` | 接收消息 |
| `msgctl(msqid, cmd, buf)` | 控制/删除队列 |

**msgtyp 过滤规则**：
| msgtyp 值 | 行为 |
|-----------|------|
| `= 0` | 接收第一条消息 |
| `> 0` | 接收类型等于该值的第一条消息 |
| `< 0` | 接收类型 ≤ |msgtyp| 的最小类型消息 |

## IPC Namespace 隔离

IPC namespace 用于隔离 System V IPC 对象和 POSIX message queues。不同 namespace 中的进程无法看到彼此的 IPC 资源。

**相关命令**：
- `ipcmk`：创建 IPC 资源
- `ipcs`：查看 IPC 资源
- `ipcrm`：删除 IPC 资源
- `unshare -i`：在新建 IPC namespace 中运行程序
- `nsenter -t PID -i`：进入指定进程的 IPC namespace

容器技术利用 IPC namespace 实现进程间通信隔离，是 [[concepts/linux-namespace-cgroups]] 机制的一部分。 ^[inferred]

## 未解问题

- System V IPC 与 POSIX IPC 在现代 Linux 应用中的选择标准？
- IPC 资源的权限模型（mode 字段）具体格式？
- 消息队列的类型设计最佳实践？

## 来源

- `summaries/system-v-ipc-semaphore` — 信号量集合原理与 SEM_UNDO
- `summaries/system-v-ipc-shared-memory` — 共享内存作为最快 IPC
- `summaries/system-v-ipc-message-queue` — 消息队列类型过滤
- `summaries/linux-namespace-ipc` — IPC namespace 隔离机制

## 参见

- [[concepts/linux-lock-mechanisms]] — Linux 锁机制全景（SpinLock、Mutex、RCU）
- [[concepts/linux-namespace-cgroups]] — Linux 资源隔离与容器基础