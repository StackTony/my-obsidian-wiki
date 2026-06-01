---
title: System V IPC 编程教程
category: skills
tags: [linux, ipc, 编程, 信号量, 共享内存, 消息队列]
source_dir: Linux 操作系统/Linux 资源隔离/System V IPC
source_files: [System V IPC 之信号量.md, System V IPC 之共享内存.md, System V IPC 之消息队列.md]
summary: System V IPC三大机制的C编程实操：信号量集合(semget/semop/semctl)、共享内存(shmget/shmat/shmdt)、消息队列(msgget/msgsnd/msgrcv)，含编译命令与IPC管理命令。
provenance:
  extracted: 0.90
  inferred: 0.05
  ambiguous: 0.05
base_confidence: 0.85
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: supporting
created: 2026-06-01
updated: 2026-06-01
relationships:
  - target: "[[concepts/linux-system-v-ipc]]"
    type: implements
  - target: "[[concepts/linux-namespace-cgroups]]"
    type: uses
---

# System V IPC 编程教程

System V IPC 三大机制（信号量、共享内存、消息队列）的 C 编程实操步骤。每种机制包含：API 速查 → 编程 demo → 管理命令。

## 前置条件

- Linux 系统，gcc 编译器
- 了解 [[concepts/linux-system-v-ipc]] 三大机制的基本原理
- root 权限（部分 IPC namespace 操作需要）

## 步骤

### 1. 信号量(Semaphore)编程

**API 速查：**

| 函数 | 功能 | 关键参数 |
|------|------|----------|
| `semget(key, nsems, flags)` | 创建/打开信号量集合 | key=IPC_PRIVATE或ftok生成；nsems=集合大小 |
| `semop(semid, sops, nsops)` | 操作信号量（原子） | sembuf: sem_num/sem_op(正释放负获取)/sem_flg |
| `semctl(semid, semnum, cmd, arg)` | 控制操作 | SETVAL设初值、GETVAL读值、IPC_RMID删除 |

**编程 demo：**
```c
// 信号量+共享内存联合使用
#include <sys/sem.h>
#include <sys/shm.h>

void locksem(int semid, int semnum) {
    struct sembuf sb = {semnum, -1, SEM_UNDO};
    semop(semid, &sb, 1);
}

void unlocksem(int semid, int semnum) {
    struct sembuf sb = {semnum, 1, SEM_UNDO};
    semop(semid, &sb, 1);
}
```

**SEM_UNDO 机制：** 进程异常退出时内核自动释放该进程持有的信号量，防止死锁。

**编译与运行：**
```bash
gcc -Wall sem.c -o sem_demo
./sem_demo                   # 服务端：打印 SHM id 和 SEM id
sudo ./sem_demo <SHM_id> <SEM_id>  # 客户端：传入ID参数
```

### 2. 共享内存(Shared Memory)编程

**API 速查：**

| 函数 | 功能 | 关键参数 |
|------|------|----------|
| `shmget(key, size, flags)` | 创建/打开共享内存 | size=所需大小；flags=IPC_CREAT|权限 |
| `shmat(shmid, addr, flags)` | 映射到进程地址空间 | addr=0让内核选地址；返回映射指针 |
| `shmdt(addr)` | 解除映射 | 不删除共享内存，仅断开当前进程 |
| `shmctl(shmid, cmd, buf)` | 控制操作 | IPC_RMID删除、IPC_STAT查状态、SHM_LOCK锁定 |

**编程 demo（写入端 shm_a.c）：**
```c
#define MYKEY 24
#define BUF_SIZE 1024
int shmid = shmget(MYKEY, BUF_SIZE, IPC_CREAT);
char *shmptr = shmat(shmid, 0, 0);
while(1) { printf("input:"); scanf("%s", shmptr); }
```

**编程 demo（读取端 shm_b.c）：**
```c
int shmid = shmget(MYKEY, BUF_SIZE, IPC_CREAT);
char *shmptr = shmat(shmid, 0, 0);
while(1) { printf("string:%s\n", shmptr); sleep(3); }
```

**编译与运行：**
```bash
gcc -Wall shm_a.c -o demoa   # 编译写入端
gcc -Wall shm_b.c -o demob   # 编译读取端
./demoa & ./demob            # 同时运行两个进程
```

**注意：** `shmdt` 不删除共享内存；删除需 `shmctl(shmid, IPC_RMID, NULL)` 或 `ipcrm -m <shmid>`。

### 3. 消息队列(Message Queue)编程

**API 速查：**

| 函数 | 功能 | 关键参数 |
|------|------|----------|
| `msgget(key, flags)` | 创建/打开消息队列 | key=IPC_PRIVATE或ftok生成 |
| `msgsnd(msqid, msgp, msgsz, msgflg)` | 发送消息 | 消息追加到队列尾部 |
| `msgrcv(msqid, msgp, msgsz, msgtyp, msgflg)` | 接收消息 | msgtyp过滤：0=首条,>0=指定类型,<0=最低类型 |
| `msgctl(msqid, cmd, buf)` | 控制操作 | IPC_RMID删除、IPC_STAT查状态 |

**编程 demo：**
```c
struct msgbuf {
    long msgtype;
    char msgtext[1024];
};

int msgid = msgget(IPC_PRIVATE, 0666);

// 发送两种类型的消息
sndmsg.msgtype = 111;
sprintf(sndmsg.msgtext, "hello!");
msgsnd(msgid, &sndmsg, sizeof(sndmsg.msgtext)+1, 0);

sndmsg.msgtype = 222;
sprintf(sndmsg.msgtext, "goodbye!");
msgsnd(msgid, &sndmsg, sizeof(sndmsg.msgtext)+1, 0);

// 按类型接收
msgrcv(msgid, &rcvmsg, 80, 222, IPC_NOWAIT);  // 只收type=222
```

**msgtyp 过滤规则：**

| msgtyp 值 | 行为 |
|-----------|------|
| `0` | 接收队列中第一条消息 |
| `>0` | 接收该类型的第一条消息 |
| `<0` | 接收类型值 ≤ |msgtyp| 的最低类型消息 |

**编译：**
```bash
gcc -Wall msgqueue.c -o msgqueue_demo
```

### 4. IPC 资源管理与 Namespace

**管理命令：**

| 命令 | 功能 |
|------|------|
| `ipcs` | 查看所有 IPC 资源 |
| `ipcs -s` / `-m` / `-q` | 仅看信号量/共享内存/消息队列 |
| `ipcrm -s <semid>` | 删除信号量集合 |
| `ipcrm -m <shmid>` | 删除共享内存 |
| `ipcrm -q <msqid>` | 删除消息队列 |
| `ipcmk -s 10` | 创建10个信号量的集合 |

**IPC Namespace 隔离：**
```bash
sudo unshare -i           # 新建 IPC namespace
readlink /proc/$$/ns/ipc  # 确认 namespace ID 不同
sudo nsenter -t <PID> -i  # 进入目标进程的 IPC namespace
```

不同 IPC namespace 的进程互不可见对方的 IPC 资源。详见 [[concepts/linux-namespace-cgroups]]。

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| `semop` 返回 -1 + EIDRM | 信号量集合已被删除 | 检查是否有其他进程调用了 `IPC_RMID` |
| `shmget` 返回 -1 + EINVAL | size 超过内核限制 | 检查 `/proc/sys/kernel/shmmax` |
| 进程退出后共享内存残留 | `shmdt` 不删除共享内存 | `ipcrm -m <shmid>` 或 `shmctl(IPC_RMID)` |
| 消息队列满 | msgsnd 阻塞 | 检查 `/proc/sys/fs/mqueue/msg_max` 限制 |
| SEM_UNDO 未生效 | 进程 crash 但内核已释放 | 正常机制，检查是否有其他原因 |

## 进阶用法

- **ftok()** 生成跨进程一致的 key：`key = ftok("/path/to/file", proj_id)` — 避免使用 IPC_PRIVATE（仅同父子进程可见）
- **POSIX IPC vs System V IPC**：POSIX API 更简洁（`sem_open`/`shm_open`/`mq_open`），System V 更底层、内核支持更完整
- **共享内存+信号量联合**：典型模式是 shmget 创建共享区 + semget 创建信号量保护并发访问（如 demo 所示）
- **IPC namespace 与容器**：Docker 容器默认创建独立 IPC namespace，容器间共享内存隔离

## 来源

- [[concepts/linux-system-v-ipc]] — System V IPC 原理与机制对比
- [[concepts/linux-namespace-cgroups]] — IPC namespace 隔离机制
- [[summaries/linux-softirq-detail]] — 软中断与 IPC 关联