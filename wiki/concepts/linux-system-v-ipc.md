---
title: System V IPC
category: concepts
tags: [linux, IPC, 信号量, 共享内存, 消息队列, System-V]
aliases: [SysV IPC, IPC机制, System V进程间通信]
relationships:
  - target: "[[concepts/linux-namespace-cgroups]]"
    type: related_to
  - target: "[[concepts/linux-lock-mechanisms]]"
    type: related_to
  - target: "[[concepts/linux-memory-management]]"
    type: related_to
source_dir: Linux 操作系统/Linux 资源隔离/System V IPC
source_files: [System V IPC 之信号量.md, System V IPC 之共享内存.md, System V IPC 之消息队列.md, "Linux Namespace  -  IPC.md"]
summary: System V IPC三大机制：信号量集合(P/V操作+SEM_UNDO)、共享内存(最快IPC-直接内存映射)、消息队列(类型化消息选择性接收)。ipc_perm公共结构，IPC namespace隔离。
provenance:
  extracted: 0.80
  inferred: 0.15
  ambiguous: 0.05
base_confidence: 0.85
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: supporting
created: 2026-06-01
updated: 2026-06-01
---

# System V IPC

System V IPC是Unix System V引入的三种进程间通信机制：信号量（Semaphore）、共享内存（Shared Memory）、消息队列（Message Queue）。三者共享 ipc_perm 公共权限结构，在IPC namespace中实现隔离，且资源生命周期独立于创建进程——进程退出后IPC资源仍然存在，直到显式删除。

## 核心观点

- 三种IPC机制各有核心特性：信号量用于同步（P/V操作控制资源访问）、共享内存用于数据传输（最快的IPC方式——零拷贝直接映射）、消息队列用于有序通信（类型化消息支持选择性接收）。
- ipc_perm 是三种IPC共享的公共权限结构，包含key、uid/gid、mode（权限位）和seq（序列号），确保权限控制的一致性。
- IPC namespace 隔离意味着不同namespace中的进程看不到彼此的IPC资源，这是容器隔离IPC通信的基础。
- SEM_UNDO 机制自动释放进程持有的信号量——进程异常退出时内核自动执行V操作，防止死锁。
- 消息队列的 msgtyp 过滤规则支持三种模式：0=接收第一条、正数=接收指定类型、负数=接收最小类型≤|msgtyp|，实现了灵活的消息路由。

## 关键细节

### 三种IPC机制对比

| 特性 | 信号量 | 共享内存 | 消息队列 |
|------|--------|---------|---------|
| 核心功能 | 同步/资源计数 | 数据传输（最快IPC） | 有序消息传递 |
| 数据拷贝 | 不涉及数据传输 | 零拷贝（直接内存映射） | 一次拷贝（内核→用户） |
| 同步需求 | 自身就是同步机制 | 需配合信号量同步 | 内核保证有序 |
| 生命周期 | 独立于进程 | 独立于进程 | 独立于进程 |
| 消息类型 | 无 | 无 | 有（msgtyp过滤） |
| 删除方式 | ipcrm -s | ipcrm -m | ipcrm -q |

### ipc_perm 公共结构

三种IPC共享的公共权限管理结构：

```c
struct ipc_perm {
    key_t  key;       // IPC键值（ftok生成或IPC_PRIVATE）
    uid_t  uid;       // 拥有者UID
    gid_t  gid;       // 拥有者GID
    uid_t  cuid;      // 创建者UID
    gid_t  cgid;      // 创建者GID
    mode_t mode;      // 权限位（类似文件权限：rwx for user/group/other）
    int    seq;       // 序列号（防止ID重用后的混淆）
};
```

- key 是用户空间的IPC资源标识，通过 `ftok(path, id)` 生成或使用 IPC_PRIVATE 创建唯一资源
- seq 是内核维护的序列号，每次分配新IPC对象时递增，与index组合形成唯一的IPC ID
- mode 权限位控制读写权限：0666表示所有用户可读写

### 信号量（Semaphore）

**核心数据结构 semid_ds**：
```c
struct semid_ds {
    struct ipc_perm sem_perm;  // 公共权限
    struct sem *sem_base;      // 信号量数组基址
    unsigned short sem_nsems;  // 信号量数量
    time_t sem_otime;          // 最后semop时间
    time_t sem_ctime;          // 最后semctl修改时间
};
```

**单个信号量 sem 结构**：
| 字段 | 含义 |
|------|------|
| semval | 信号量当前值 |
| sempid | 最后操作该信号量的进程PID |
| semncnt | 等待semval增加的进程数 |
| semzcnt | 等待semval变为0的进程数 |

**API**：
| 函数 | 功能 |
|------|------|
| semget(key, nsems, flags) | 创建/获取信号量集合 |
| semop(semid, sops, nsops) | P/V操作（原子执行多个信号量操作） |
| semctl(semid, semnum, cmd, ...) | 控制操作（SETVAL/GETVAL/IPC_RMID等） |

**P/V操作（semop）**：
- sem_op > 0：V操作，增加semval，唤醒等待的进程
- sem_op < 0：P操作，如果semval ≥ |sem_op|则减少，否则阻塞
- sem_op = 0：等待semval变为0

**SEM_UNDO 机制**：
- 在semop中设置 SEM_UNDO 标志后，内核维护一个 undo 结构
- 进程正常或异常退出时，内核自动对该进程的所有SEM_UNDO操作执行反向调整
- 防止进程崩溃后信号量永远被持有导致的死锁问题
- 使用建议：在P操作时设置SEM_UNDO，V操作时通常不设 ^[inferred]

### 共享内存（Shared Memory）

**核心数据结构 shmid_ds**：
```c
struct shmid_ds {
    struct ipc_perm shm_perm;   // 公共权限
    size_t shm_segsz;           // 共享内存段大小（字节）
    void *shmaddr;              // 连接地址（shmat返回）
    pid_t shm_cpid;             // 创建者PID
    pid_t shm_lpid;             // 最后连接/断开者PID
    int shm_nattch;             // 当前连接数
};
```

**特性**：
- 最快的IPC方式——零拷贝，数据直接映射到进程地址空间
- 两个进程访问同一块物理内存，无需内核中转
- 缺点：需要自行实现同步机制（通常配合信号量）
- 连接后访问与普通内存无异，性能开销仅为一次页表映射

**API**：
| 函数 | 功能 |
|------|------|
| shmget(key, size, flags) | 创建/获取共享内存段 |
| shmat(shmid, addr, flags) | 连接到进程地址空间 |
| shmdt(addr) | 断开连接（不从内核删除） |
| shmctl(shmid, cmd, buf) | 控制操作（IPC_RMID/IPC_STAT等） |

**重要区别**：
- shmdt() 只是断开当前进程与共享内存的连接，shm_nattch减1
- IPC_RMID 才是真正删除共享内存段——只有当shm_nattch=0时才立即释放，否则标记为待删除

### 消息队列（Message Queue）

**核心数据结构 msqid_ds**：
```c
struct msqid_ds {
    struct ipc_perm msg_perm;   // 公共权限
    struct msg *msg_first;      // 队列首消息
    struct msg *msg_last;       // 队列尾消息
    unsigned long msg_cbytes;   // 当前队列字节数
    unsigned long msg_qnum;     // 当前队列消息数
    unsigned long msg_qbytes;   // 队列最大字节数
};
```

**单条消息结构**：
```c
struct msgbuf {
    long mtype;    // 消息类型（必须>0）
    char mtext[1]; // 消息正文（变长）
};
```

**API**：
| 函数 | 功能 |
|------|------|
| msgget(key, flags) | 创建/获取消息队列 |
| msgsnd(msqid, msgp, size, flags) | 发送消息 |
| msgrcv(msqid, msgp, size, msgtyp, flags) | 接收消息 |
| msgctl(msqid, cmd, buf) | 控制操作 |

**msgtyp 过滤规则**（msgrcv的核心特性）：

| msgtyp值 | 行为 |
|---------|------|
| 0 | 接收队列中的第一条消息（FIFO顺序） |
| >0 | 接收类型等于msgtyp的第一条消息（选择性接收） |
| <0 | 接收类型≤|msgtyp|中类型值最小的消息（优先级接收） |

msgtyp<0的模式实现了优先级队列：消息按类型值从小到大被优先接收。

### IPC namespace 隔离

IPC namespace（CLONE_NEWIPC）隔离System V IPC和POSIX消息队列：
- 不同namespace中的进程拥有独立的IPC资源集合
- 同一namespace中的进程共享IPC资源
- 信号量、共享内存、消息队列都是namespace隔离的对象
- 容器使用独立的IPC namespace确保容器内进程不会与宿主或其他容器的IPC资源冲突

### IPC 持久性

IPC资源的生命周期独立于创建进程：
- 创建进程退出 → IPC资源仍然存在
- 所有连接进程退出 → 共享内存标记待删除（如果IPC_RMID已调用）
- IPC资源在以下情况被删除：显式调用IPC_RMID、系统重启
- 这与POSIX IPC不同——POSIX mq和sem可以是命名也可以是匿名，匿名IPC随进程消失 ^[inferred]

### IPC 管理命令

| 命令 | 功能 |
|------|------|
| ipcs | 显示所有IPC资源信息（-m共享内存/-q消息队列/-s信号量） |
| ipcrm | 删除IPC资源（-m shmid/-q msqid/-s semid） |
| ipcmk | 创建IPC资源 |

## 未解问题

- System V IPC 与 POSIX IPC 的选择指南——在什么场景下应该优先选择POSIX IPC？ ^[inferred] POSIX IPC接口更简洁、与文件系统统一、但System V IPC功能更丰富（如信号量集合操作）。
- 大量共享内存段导致的内存碎片管理问题，来源中未涉及。 ^[ambiguous]

## 来源

- [[summaries/linux-meminfo-params]] — 共享内存与meminfo中Shmem字段的关系
- [[summaries/linux-rcu-lock]] — IPC资源管理的内核同步机制