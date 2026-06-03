---
title: Linux资源隔离：Namespace与Cgroups
category: concepts
tags: [linux, 内核, namespace, cgroups, 容器, 隔离]
aliases: [Linux Namespace, Linux Cgroups, 容器隔离, 资源限制]
relationships:
  - target: "[[concepts/linux-system-v-ipc]]"
    type: related_to
  - target: "[[concepts/linux-process-scheduling]]"
    type: related_to
  - target: "[[concepts/linux-interrupt-system]]"
    type: related_to
  - target: "[[concepts/linux-network-stack]]"
    type: related_to
  - target: "[[concepts/container-runtime-deep-dive]]"
    type: related_to
  - target: "[[concepts/cgroups-v2-deep-dive]]"
    type: related_to
  - target: "[[concepts/seccomp-capabilities]]"
    type: related_to
source_dir: Linux 操作系统/Linux 资源隔离
source_files: [Linux Namespace与Cgroups介绍.md, "System V IPC/Linux Namespace  -  IPC.md"]
summary: Linux内核资源隔离双引擎：Namespace实现视图隔离(6种类型-PID/Net/UTS/IPC/Mount/User)、Cgroups实现资源限制(CPU/内存/IO/网络)。两者组合构成容器技术基础。
provenance:
  extracted: 0.80
  inferred: 0.15
  ambiguous: 0.05
base_confidence: 0.70
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: core
created: 2026-06-01
updated: 2026-06-02
---

# Linux资源隔离：Namespace与Cgroups

Linux内核的资源隔离由两大引擎驱动：Namespace 提供视图隔离（让进程看到不同的系统资源视图），Cgroups 提供资源限制（控制进程能使用多少系统资源）。两者的组合构成了容器技术的内核基础——Docker/LXC/Podman 等容器运行时本质上就是组合配置多种Namespace和Cgroups来创建隔离的运行环境。

## 核心观点

- Namespace 实现视图隔离——让不同进程组看到不同的PID空间、网络栈、文件系统挂载点等，但本质是"看不到"而非"不能访问"。 ^[inferred]
- Cgroups 实现资源限制——控制进程组能使用的CPU时间、内存大小、IO带宽等，是"硬限制"而非"软隔离"。
- 两者正交组合：Namespace 做隔离（"你只能看到这些"），Cgroups 做限制（"你只能用这么多"），容器 = Namespace集合 + Cgroups配置。
- User namespace 是特权隔离的关键：通过UID映射，容器内root映射到宿主普通用户，实现无特权容器。

## 关键细节

### Namespace 6种类型 + Cgroup ns

| 类型 | 隔离内容 | CLONE_NEW*标志 | 内核版本 | 容器用途 |
|------|----------|---------------|---------|---------|
| PID | 进程ID空间 | CLONE_NEWPID | 3.8 | 容器内PID独立，容器内PID=1的init |
| Network | 网络栈（接口、路由、防火墙） | CLONE_NEWNET | 2.6.24 | 容器独立网络栈，veth pair连接 |
| UTS | 主机名和NIS域名 | CLONE_NEWUTS | 2.6.19 | 容器可设独立hostname |
| IPC | System V IPC和POSIX消息队列 | CLONE_NEWIPC | 2.6.19 | 容器独立IPC通信 |
| Mount | 文件系统挂载点 | CLONE_NEWNS | 2.4.19 | 容器独立文件系统视图 |
| User | 用户和组ID空间 | CLONE_NEWUSER | 3.8(完整3.12) | 容器内UID映射，无特权容器 |
| Cgroup | Cgroup自身视图 | CLONE_NEWCGROUP | 4.6 | 容器内可见不同cgroup层次 |

### Namespace API

三种操作方式：

| API | 用途 | 说明 |
|-----|------|------|
| `clone(CLONE_NEW*)` | 创建新namespace | 子进程在新namespace中运行 |
| `setns(fd, CLONE_NEW*)` | 加入已有namespace | fd = /proc/[pid]/ns/下的namespace文件 |
| `unshare(CLONE_NEW*)` | 离开当前namespace | 当前进程移到新namespace |

### /proc/[pid]/ns/ 目录

每个进程的namespace信息通过 /proc/[pid]/ns/ 暴露：

```
/proc/1/ns/
├── cgroup  → cgroup:[4026531835]
├── ipc     → ipc:[4026531839]
├── mnt     → mnt:[4026531840]
├── net     → net:[4026531969]
├── pid     → pid:[4026531836]
├── user    → user:[4026531837]
├── uts     → uts:[4026531838]
```

每个namespace文件是一个符号链接，目标中的inode编号标识该namespace。两个进程如果指向同一个inode编号，说明它们在同一个namespace中。

### User Namespace 与 UID 映射

User namespace 是实现无特权容器（rootless containers）的关键：

- 容器内UID 0（root）映射到宿主普通用户UID（如1000）
- 映射通过 /proc/[pid]/uid_map 和 /proc/[pid]/gid_map 配置
- 映射规则：`容器内UID范围 → 宿主UID范围 → 映射长度`
- 示例：`0 1000 1` 表示容器内UID 0 映射到宿主UID 1000，映射长度1个ID
- 在user namespace内拥有全部capabilities（但映射到宿主时受限）

### Cgroups 四大功能与组件

**四大功能**：
1. **资源限制（Limit）** — 限制进程组可使用的资源量
2. **资源优先（Prioritize）** — 分配更多资源给重要进程组
3. **资源统计（Account）** — 统计进程组的资源使用量
4. **资源隔离（Isolate）** — 将进程组隔离到特定资源分区

**核心组件**：

| 组件 | 含义 | 说明 |
|------|------|------|
| task | 任务 | cgroups中的被控对象（进程/线程） |
| cgroup | 控制组 | 一组task按某种标准划分的组 |
| hierarchy | 层级树 | 多个cgroup组成的树状结构 |
| subsystem | 子系统 | 具体的资源控制器（cpu/memory等） |

### Cgroups 子系统

| 子系统 | 功能 | 配置文件示例 |
|--------|------|-------------|
| cpu | CPU时间限制和分配 | cpu.cfs_quota_us, cpu.shares |
| memory | 内存使用限制 | memory.limit_in_bytes |
| blkio | 块设备IO限制 | blkio.throttle.read_bps_device |
| cpuset | CPU核和内存节点绑定 | cpuset.cpus, cpuset.mems |
| devices | 设备访问控制 | devices.allow, devices.deny |
| freezer | 进程组冻结/解冻 | freezer.state (FROZEN/THAWED) |
| net_cls | 网络包分类标记 | net_cls.classid |
| net_prio | 网络优先级设置 | net_prio.prio_idx |
| hugetlb | 大页内存限制 | hugetlb.2MB.limit_in_bytes |

### Cgroups 配置示例

CPU限制配置：
```
# /sys/fs/cgroup/cpu/container1/
cpu.cfs_quota_us = 50000    # 50ms 时间配额
cpu.cfs_period_us = 100000  # 100ms 周期
# 50ms/100ms = 50% CPU限制
```

内存限制配置：
```
# /sys/fs/cgroup/memory/container1/
memory.limit_in_bytes = 512M  # 最大512MB内存
memory.memsw.limit_in_bytes = 1G  # 内存+swap最大1GB
```

配置目录结构：
```
/sys/fs/cgroup/
├── cpu/
│   ├── container1/
│   └── container2/
├── memory/
│   ├── container1/
│   └── container2/
├── blkio/
└── cpuset/
```

### Cgroups v1 vs v2

| 特性 | v1 | v2 |
|------|-----|-----|
| 挂载方式 | 每个子系统独立挂载 | 统一层级单一挂载 |
| 层级关系 | 子系统可独立层级树 | 所有子系统共享同一层级 |
| 控制器 | 各子系统独立配置 | 统一在cgroup.controllers配置 |
| 核心版本 | 2.6.24+ | 4.5+（4.15+完整功能） |

现代系统（如Ubuntu 21.10+）默认使用cgroup v2。 ^[inferred]

## 未解问题

- Cgroups v2 的完整迁移路径——v1到v2的兼容性和迁移策略仍有争议。 ^[ambiguous]
- Namespace嵌套的安全边界——多层namespace嵌套下的capability传递和边界安全尚未完全明确。 ^[inferred]


## 延伸阅读

实操指南：[[skills/linux-ipc-programming]]

综合分析：[[synthesis/linux-kernel-subsystem-interactions]], [[synthesis/cloud-native-infrastructure-landscape]]

## 来源

- [[summaries/linux-meminfo-params]] — Cgroups memory子系统与meminfo的关系
- [[summaries/linux-network-protocol-stack-impl]] — Network namespace对网络栈的隔离