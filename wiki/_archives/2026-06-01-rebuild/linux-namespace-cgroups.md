---
title: Linux Namespace 与 Cgroups
created: 2026-06-01
updated: 2026-06-01
tags: [linux, kernel, namespace, cgroups, container, isolation]
category: concepts
source_dir: Linux 操作系统/Linux 资源隔离
source_files: [Linux Namespace与Cgroups介绍.md, "==System V IPC==/Linux Namespace  -  IPC.md", "==System V IPC==/System V IPC 之信号量.md", "==System V IPC==/System V IPC 之共享内存.md", "==System V IPC==/System V IPC 之消息队列.md"]
summary: Linux内核资源隔离双引擎：Namespace实现视图隔离，Cgroups实现资源限制
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: "2026-06-01"
tier: supporting
provenance:
  extracted: 0.7
  inferred: 0.25
  ambiguous: 0.05
relationships:
  - target: "[[concepts/linux-interrupt-system]]"
    type: related_to
  - target: "[[concepts/linux-memory-management]]"
    type: related_to
---

# Linux Namespace 与 Cgroups

Linux 容器技术的两大基石：**Namespace** 实现资源视图隔离，让进程以为自己独占系统；**Cgroups** 实现物理资源限制，防止进程过度消耗。两者配合构成完整的资源隔离方案。

## Namespace：视图隔离引擎

Namespace 是 Linux 内核对全局系统资源的封装隔离机制，使不同 namespace 中的进程拥有独立的资源视图，彼此不可见。

### 七种 Namespace 类型

| 类型 | 隔离内容 | 内核版本 | 用途 |
|------|----------|----------|------|
| **Mount** | 文件系统挂载点 | 2.4 | 独立文件系统视图，类似 chroot 但更安全 |
| **UTS** | 主机名与域名 | 2.6 | 容器拥有独立 hostname |
| **IPC** | System V IPC 与 POSIX 消息队列 | 2.6 | 隔离信号量、共享内存、消息队列 |
| **PID** | 进程 ID | 2.6 | 容器内 PID 从 1 开始，看不到宿主进程 |
| **Network** | 网络栈（网卡、路由、端口） | 2.6 | 独立 IP、端口、防火墙规则 |
| **User** | 用户与组 ID | 2.6（3.8 完善） | 容器内 root 对应宿主普通用户 |
| **Cgroup** | Cgroup 根目录 | 4.6 | 隔离 cgroup 视图本身 ^[inferred] |

前六种是实现容器的基础隔离能力，Cgroup namespace 尚未被 Docker 采用。

### 核心设计理念

命名空间建立系统的不同视图。子命名空间中的进程看到独立的 init（PID=1），但实际是宿主中某个进程的映射。父命名空间可见子容器的运行状态，子容器之间互相隔离。

**UID 级别隔离的关键价值**：可以在 namespace 内虚拟化 root 权限，用户在容器内是 root，在宿主机上仍是普通 UID，解决了权限隔离问题。

### 操作 API

| API | 功能 | 典型参数 |
|-----|------|----------|
| **clone()** | 创建新进程并放入新 namespace | CLONE_NEWIPC、CLONE_NEWNET、CLONE_NEWPID 等 |
| **setns()** | 将进程加入已有 namespace | 通过 /proc/[pid]/ns 文件描述符 |
| **unshare()** | 将当前进程移入新 namespace | 同 clone 参数，不创建子进程 |

**命令行工具**：`unshare` 创建新 namespace 运行程序，`nsenter` 进入指定进程的 namespace。

### 查看进程 Namespace

从内核 3.8 起，`/proc/[pid]/ns/` 包含进程所属的 namespace 链接文件：

```bash
readlink /proc/$$/ns/ipc
# ipc:[4026531839] — inode number 标识 namespace ID
```

两个进程的 namespace 文件指向同一 inode，说明共享该 namespace。打开链接文件可防止 namespace 被自动删除（即使所有进程退出）。

## Cgroups：资源限制引擎

Cgroups（Control Groups）限制、记录、隔离进程组的物理资源使用，是 LXC 和 Docker 的资源管理基础。

### 五大功能

| 功能 | 说明 | 典型子系统 |
|------|------|-----------|
| **Resource Limiting** | 设定资源上限，超限触发 OOM | memory |
| **Prioritization** | 分配资源比例（如 CPU share） | cpu |
| **Accounting** | 记录资源使用量 | cpuacct |
| **Isolation** | 隔离 namespace 资源 | ns（已弃用）^[ambiguous] |
| **Control** | 挂起/恢复进程组 | freezer |

### 核心子系统

| 子系统 | 控制内容 | 示例用途 |
|--------|----------|----------|
| **blkio** | 块设备 I/O 限制 | 磁盘读写带宽控制 |
| **cpu** | CPU 时间分配 | 调度优先级、share |
| **cpuacct** | CPU 使用统计 | 生成 CPU 报告 |
| **cpuset** | CPU 核与内存节点绑定 | 多核系统中绑定特定核 |
| **devices** | 设备访问控制 | 允许/拒绝访问特定设备 |
| **freezer** | 进程挂起/恢复 | 快速暂停容器 |
| **memory** | 内存限制与统计 | 设定上限、触发 OOM |
| **net_cls** | 网络包标记 | 流量控制（tc）识别来源 |
| **net_prio** | 网络流量优先级 | QoS 控制 |
| **hugetlb** | 大页内存限制 | HugeTLB 文件系统控制 |

### 使用方式

通过 `/sys/fs/cgroup/` 操作：创建目录即创建 control group，写入 `tasks` 文件添加进程，配置参数文件设定限制。

**内存限制示例**：
```bash
mkdir /sys/fs/cgroup/memory/test
echo 100M > /sys/fs/cgroup/memory/test/memory.limit_in_bytes
echo $$ > /sys/fs/cgroup/memory/test/tasks  # 将当前 shell 加入
```

**CPU 限制示例**：
```bash
mkdir /sys/fs/cgroup/cpu/hello
echo 50000 > /sys/fs/cgroup/cpu/hello/cpu.cfs_quota_us  # 50% CPU
echo $PID > /sys/fs/cgroup/cpu/hello/tasks
```

`cpu.cfs_period_us` 默认 100000（100ms），`cpu.cfs_quota_us` 设为 50000 表示每周期最多使用 50ms CPU。

## IPC Namespace 与 System V IPC

IPC namespace 隔离 System V IPC 对象（信号量、共享内存、消息队列）和 POSIX 消息队列。不同 IPC namespace 的进程互不可见对方的 IPC 资源。详细机制见 [[concepts/linux-system-v-ipc]]。

### System V IPC 三种机制

**信号量（Semaphore）**：用于互斥共享资源的同步控制。System V 信号量是信号量集，包含多个信号量，共用一个 ID。

| API | 功能 |
|-----|------|
| `semget` | 创建/打开信号量集 |
| `semop` | 操作信号量（P/V 操作） |
| `semctl` | 控制（删除、设置值、获取信息） |

核心结构：`semid_ds`（信号量集信息）和 `sem`（单个信号量值、等待进程数）。

**共享内存（Shared Memory）**：最快速的 IPC 机制，进程直接映射同一内存区域，无需中间介质。

| API | 功能 |
|-----|------|
| `shmget` | 创建/打开共享内存 |
| `shmat` | 附加到进程地址空间 |
| `shmdt` | 分离共享内存 |
| `shmctl` | 控制（删除、锁定、获取信息） |

核心结构：`shmid_ds` 记录大小、附加进程数、时间戳等。需要配合信号量实现同步访问。

**消息队列（Message Queue）**：内核中的消息链表，支持按类型接收消息。

| API | 功能 |
|-----|------|
| `msgget` | 创建/打开消息队列 |
| `msgsnd` | 发送消息 |
| `msgrcv` | 接收消息（可按类型过滤） |
| `msgctl` | 控制（删除、获取信息） |

核心结构：`msqid_ds` 和 `msgbuf`（消息类型 + 数据）。`msgtyp` 参数控制接收逻辑：0 表示首条，>0 表示指定类型，<0 表示类型 ≤ |msgtyp| 中最小的。

### IPC Namespace 验证

使用 `unshare -i` 创建新 IPC namespace，通过 `ipcs` 查看 IPC 资源：

```bash
# shell1: 主 namespace
sudo unshare -i  # shell2: 新 IPC namespace
# shell2 创建信号量集
ipcmk -s 10
# shell1 无法看到 shell2 的信号量（隔离生效）
ipcs -s
```

通过 `nsenter -t <pid> -i` 可进入目标进程的 IPC namespace，共享 IPC 资源。

## 双引擎协作模式

Namespace 和 Cgroups 共同构成容器资源隔离的完整方案：

- **Namespace** 解决"看什么"：进程看到独立的 PID、网络、文件系统等视图
- **Cgroups** 解决"用多少"：进程只能使用限定的 CPU、内存、I/O 资源

容器本质是进程加上这两层隔离：Namespace 让进程以为自己在独立系统，Cgroups 防止进程过度消耗宿主资源。二者正交配合，Namespace 的隔离边界通常对应一个 cgroup 的资源控制边界。 ^[inferred]

## 未解问题

- User Namespace 的 root 映射机制在复杂场景（嵌套容器）中的安全边界
- Cgroup v2 与 v1 的架构差异及对容器生态的影响
- Namespace 嵌套（父子 namespace）的资源传递规则细节
- IPC namespace 与 POSIX 消息队列的完整隔离范围

## 来源

- `Linux 资源隔离/Linux Namespace与Cgroups介绍.md` — Namespace 七种类型、API、/proc 查看；Cgroups 五功能、子系统、使用示例
- `Linux 资源隔离/System V IPC/Linux Namespace - IPC.md` — IPC namespace 验证 demo、unshare/nsenter 工具
- `Linux 资源隔离/System V IPC/System V IPC 之信号量.md` — semid_ds/sem 结构、semget/semop/semctl API、同步控制
- `Linux 资源隔离/System V IPC/System V IPC 之共享内存.md` — shmid_ds 结构、shmget/shmat/shmdt/shmctl API、最快速 IPC
- `Linux 资源隔离/System V IPC/System V IPC 之消息队列.md` — msqid_ds/msgbuf 结构、msgget/msgsnd/msgrcv/msgctl API、类型过滤接收