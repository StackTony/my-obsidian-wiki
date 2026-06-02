---
title: Linux内核调试与监控实操手册
category: skills
tags: [linux, 内核, 调试, 监控, 性能分析]
source_dir: Linux 操作系统
source_files: [Linux ksoftirqd软中断内核线程详解.md, "Linux 硬中断irq + 软中断softirq原理.md", Linux 软中断softirq.md, Linux meminfo参数详细解释.md, "Linux 页缓存（Page Cache）.md", Linux IO全景介绍.md, "Linux 关机流程深度解析：从内核机制到硬件控制的完整理论框架.md", Linux 网络协议栈.md, Linux Namespace与Cgroups介绍.md, "Linux Namespace  -  IPC.md"]
summary: 内核各子系统的监控命令、常见问题排查路径与调试技巧——softirq/meminfo/Page Cache/IO/关机/cgroup/IPC namespace七类场景。
provenance:
  extracted: 0.85
  inferred: 0.10
  ambiguous: 0.05
base_confidence: 0.78
lifecycle: draft
lifecycle_changed: 2026-06-01
tier: supporting
created: 2026-06-01
updated: 2026-06-02
relationships:
  - target: "[[concepts/linux-interrupt-system]]"
    type: uses
  - target: "[[concepts/linux-memory-management]]"
    type: uses
  - target: "[[concepts/linux-io-stack]]"
    type: uses
  - target: "[[concepts/linux-tracing-frameworks]]"
    type: uses
  - target: "[[concepts/linux-vmcore-analysis]]"
    type: related_to
---

# Linux内核调试与监控实操手册

按子系统分类的内核监控命令、常见问题排查路径和调试技巧。每个场景包含：监控接口 → 症状识别 → 排查步骤。

## 前置条件

- 有 root 或 sudo 权限访问 `/proc`、`/sys`、debugfs
- 理解 [[concepts/linux-interrupt-system]]、[[concepts/linux-memory-management]]、[[concepts/linux-io-stack]] 基础概念

## 步骤

### 1. 软中断(Softirq)监控与排查

**监控命令：**
- `cat /proc/softirqs` — per-CPU 软中断计数（HI/TIMER/NET_TX/NET_RX/BLOCK/IRQ_POLL/TASKLET/SCHED/HRTIMER/RCU）
- `top -n1 | head -n3` — `si` 字段显示软中断 CPU 占用百分比
- `ps aux | grep ksoftirqd` — 查看 per-CPU ksoftirqd 线程状态

**常见问题与排查：**

| 症状 | 可能原因 | 排查路径 |
|------|----------|----------|
| `si` 持续偏高 | 某个 softirq 类型过载 | 查看 `/proc/softirqs` 找哪个类型计数激增 |
| 网络延迟增大 | NET_RX_SOFTIRQ 过多 | 检查 `softirq` 中 NET_RX 计数，考虑 RPS 分散负载 |
| 进程调度变慢 | SCHED_SOFTIRQ 饱占 CPU | 同核上 softirq 频繁抢占进程上下文时间 |

**预算机制：** `__do_softirq` 限制每次处理不超过 2 jiffies(~10ms)和 10 次重启循环；超出则唤醒 ksoftirqd 兜底。

### 2. 内存监控与黑洞追踪

**监控命令：**
- `cat /proc/meminfo` — 核心字段：MemTotal/MemFree/MemAvailable/Buffers/Cached/SReclaimable
- `free -m` — 快速查看 Buffers+Cached 总量
- `cat /proc/vmallocinfo` — vmalloc 分配详情（含调用函数名、地址、大小）
- `grep vmalloc /proc/vmallocinfo | awk '{total+=$2}; END {print total}'` — vmalloc 实际物理内存总量

**内存黑洞追踪：** `alloc_pages` 分配的内存不出现在 `/proc/meminfo` 中。排查方法：
1. `cat /proc/vmallocinfo > vmallocinfo.1` — 保存基线
2. `modprobe -a <module>` — 加载可疑模块
3. `cat /proc/vmallocinfo > vmallocinfo.2` — 保存新状态
4. `diff vmallocinfo.1 vmallocinfo.2` — 查看新增分配（页对齐 4096 + 1 guard page）

**关键公式：**
- Page Cache = Buffers + Cached + SwapCached = Active(file) + Inactive(file) + Shmem + SwapCached
- Active(anon) + Inactive(anon) ≈ AnonPages + Shmem

**HugePages 相关：**
- `echo 128 > /proc/sys/vm/nr_hugepages` — 预分配128个2MB大页
- HugePages 不计入 RSS/PSS/LRU，独立管理

### 3. Page Cache 与脏页监控

**监控命令：**
- `cat /proc/meminfo | grep -E 'Buffers|Cached|SwapCached|Dirty|Writeback'` — 缓存与脏页字段
- `cat /sys/class/scsi_disk/0\:2\:0\:0/cache_type` — 存储设备 Write Through/Write Back 模式

**一致性选择：**

| 系统调用 | 行为 | 适用场景 |
|----------|------|----------|
| `sync()` | 刷新所有文件系统缓冲区 | 全局刷盘，不阻塞 |
| `fsync(fd)` | 刷新指定文件数据+元数据到磁盘 | 需要数据+元数据完整性 |
| `fdatasync(fd)` | 仅刷新数据（不含时间戳等元数据） | 只要数据完整，容忍元数据延迟 |

**脏页总量：** Dirty + NFS_Unstable + Writeback = 系统总脏页数

### 4. IO栈与设备调试

**监控命令：**
- `cat /sys/class/scsi_disk/<device>/cache_type` — 查看 SCSI 设备缓存模式
- `dmesg | grep NR_IRQS` — 系统最大硬件中断数
- `systemd-cgls -k | grep softirq` — ksoftirqd 线程列表

**Write Through vs Write Back 选择：**
- Write Through：写操作直接到磁盘，安全但慢；适合数据一致性要求高的场景
- Write Back：写操作先进阵列卡缓存再转发磁盘，快但宕机可能丢数据

### 5. 关机故障排查

**监控命令：**
- `systemd-analyze blame` — 分析关机耗时最长的 systemd 单元
- `dmesg` — 查看关机前最后的内核日志
- `cat /proc/slabinfo` — 关机前检查内核对象泄漏

**常见问题与排查：**

| 症状 | 排查路径 |
|------|----------|
| 关机卡住 | `dmesg` 查 OOPS/PANIC → 定位故障模块 |
| 文件系统损坏 | Live CD 启动 → `fsck` 修复根分区 |
| 容器阻止关机 | 检查 namespace/cgroup 僵尸进程 → `kill -9` 强制终止 |
| 看门狗重启 | 检查关机流程是否周期性喂狗（`CONFIG_WATCHDOG`） |

**事务文件系统（Btrfs/ZFS）** 支持回滚到一致状态，可从中断的关机恢复。

### 6. Cgroup 资源限制实操

**CPU 限制：**
```
mkdir -p /sys/fs/cgroup/cpu/hello/
echo 50000 > /sys/fs/cgroup/cpu/hello/cpu.cfs_quota_us   # 50% CPU
echo "$PID" > /sys/fs/cgroup/cpu/hello/tasks
```

**内存限制：**
```
mkdir /sys/fs/cgroup/memory/test
echo $$ > /sys/fs/cgroup/memory/test/tasks
echo <value> > /sys/fs/cgroup/memory/test/memory.limit_in_bytes
```
超过限制触发 OOM。

**查看 cgroup 子系统：** `lssubsys -all` 或 `ls /sys/fs/cgroup/`

### 7. IPC Namespace 操作

**创建隔离 IPC namespace：**
```bash
sudo unshare -i                # 新建 IPC namespace
readlink /proc/$$/ns/ipc       # 确认 namespace ID 与父进程不同
```

**进入已有 namespace：**
```bash
sudo nsenter -t <PID> -i       # 进入目标进程的 IPC namespace
```

**IPC 资源管理：**
- `ipcmk -s 10` — 创建10个信号量的集合
- `ipcs -s` — 查看信号量
- `ipcrm -s <semid>` — 删除信号量集合

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| `si` 值突然升高 | 单核 softirq 过载 | 检查 `/proc/softirqs` 定位类型；考虑 RPS 分散 |
| MemFree 很低但 MemAvailable 正常 | Page Cache 占用大量内存 | 正常现象，缓存可回收 |
| 内存莫名减少（黑洞） | `alloc_pages` 分配不被 meminfo 跟踪 | vmallocinfo diff 追踪模块分配 |
| 关机超时挂起 | 某进程/容器拒绝终止 | `systemd-analyze blame` 定位卡住单元 |

## 进阶用法

- **Lockdep**：`CONFIG_LOCKDEP=y` + `CONFIG_DEBUG_MUTEXES=y` → `cat /proc/lockdep` 查锁依赖和潜在死锁
- **Lock 统计**：`CONFIG_LOCK_STAT=y` → `cat /proc/lock_stat` 查锁持有时间、等待时间、竞争次数
- **RCU Stall**：`echo 120 > /sys/module/rcupdate/parameters/rcu_cpu_stall_timeout` 调整 stall 检测超时
- **Ftrace**：`echo function_graph > current_tracer` + `echo <func> > set_graph_function` — 函数调用图追踪
- **Crash 工具**：`crash> struct mutex <addr>` → 解析 mutex 状态、owner、waiter 队列
- **中断数实时观测**：参考 [[summaries/linux-interrupt-monitoring-script]] 的bash脚本，不依赖额外模块

## 来源

- [[concepts/linux-interrupt-system]] — 软中断监控与排查
- [[concepts/linux-memory-management]] — 内存监控与黑洞追踪
- [[concepts/linux-io-stack]] — IO栈与设备调试
- [[concepts/linux-boot-shutdown]] — 关机故障排查
- [[concepts/linux-namespace-cgroups]] — Cgroup 资源限制
- [[concepts/linux-lock-mechanisms]] — Lockdep/Lock统计
- [[summaries/linux-softirq-detail]] — ksoftirqd 与软中断预算机制
- [[summaries/linux-meminfo-params]] — meminfo 字段详解与公式
- [[summaries/linux-page-cache]] — Page Cache 监控与脏页