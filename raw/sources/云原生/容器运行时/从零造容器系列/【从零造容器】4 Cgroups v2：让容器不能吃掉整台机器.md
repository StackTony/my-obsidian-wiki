你给容器设了 512MB 内存限制。`docker run --memory=512m postgres`。然后某天凌晨三点，监控报警：宿主机上的数据库被 OOM-killer 干掉了。不是容器里的 — 是宿主机上的。

怎么回事？你的内存限制呢？

答案可能是：你用的是 cgroups v1，你设的 `memory.limit_in_bytes` 不包含内核内存（kmem），或者你的容器绕过了 buffered IO 限制在疯狂写磁盘，page cache 把宿主机内存吃光了。也可能只是你的 cgroup 配置根本没生效 — v1 的 hierarchy 太乱了，控制器之间互相踩脚。

[上一篇](https://quant67.com/post/containers/01-namespaces/namespaces.html)我们用 namespace 隔离了进程的”视野”。但隔离不等于限制 — 一个被隔离的进程照样可以吃掉整台机器的 CPU、内存和磁盘 IO。**Namespace 管的是”能看见什么”，Cgroups 管的是”能用多少”。**

本篇我们深入 cgroups v2，从文件系统接口开始，手动创建 cgroup、设限制、压测、看统计数据。所有代码在 `examples/containers/04-cgroups/` 目录，`make` 即可编译。

> 测试环境：Linux 6.x, x86_64，cgroups v2 unified hierarchy。

---

## 一、Cgroups v1 vs v2：一个历史错误的修正

Cgroups（Control Groups）在 2008 年进入 Linux 内核（2.6.24）。初始设计 — 现在叫 v1 — 是这样的：

**每个控制器独立挂载一棵树。**

```
/sys/fs/cgroup/
├── cpu/  ← cpu 控制器自己一棵树
│  ├── docker/
│  │  └── container_abc/
│  │  ├── cpu.cfs_quota_us
│  │  └── tasks
│  └── ...
├── memory/  ← memory 控制器自己一棵树
│  ├── docker/
│  │  └── container_abc/
│  │  ├── memory.limit_in_bytes
│  │  └── tasks
│  └── ...
├── blkio/  ← blkio 控制器自己一棵树
│  └── ...
└── cpuset/  ← cpuset 控制器自己一棵树
  └── ...
```

看到问题了吗？

1. **同一个进程在不同树里的位置可以不一致。** container_abc 在 cpu 树里限了 50%，在 memory 树里限了 512MB，但在 blkio 树里可能根本没配置。每个控制器独立管理，没有统一的”这个容器的所有限制”的概念。
    
2. **竞争条件。** 把一个进程加入 cgroup 需要分别写每棵树的 `tasks` 文件。在多线程场景下，进程的线程可能在不同控制器树里处于不同的 cgroup — 这不是 bug，这是 v1 的”特性”。
    
3. **内核复杂度爆炸。** 每个控制器可以有自己的层级结构，内核要维护 N 棵独立的树。代码路径交叉，bug 难以复现。
    
4. **buffered IO 的噩梦。** v1 的 blkio 控制器只对 direct IO 生效。应用程序的 buffered write 走的是 page cache，而 page cache 的回写（writeback）发生在内核线程里，不属于任何容器的 blkio cgroup。结果就是：你设了 IO 限制，但 buffered IO 完全无视它。
    

Tejun Heo（cgroup 子系统的维护者）在 2012 年公开说 v1 的设计是个错误。然后花了四年时间设计并实现了 cgroups v2。

**Cgroups v2 的核心改变：unified hierarchy — 一棵树管所有。**

```
/sys/fs/cgroup/  ← 唯一的根
├── cgroup.controllers  ← 可用的控制器列表
├── cgroup.subtree_control  ← 子树启用了哪些控制器
├── mycontainer/  ← 你创建的 cgroup（就是个目录）
│  ├── cgroup.procs  ← 里面有哪些进程
│  ├── cgroup.controllers
│  ├── cgroup.subtree_control
│  ├── cpu.max  ← CPU 限制
│  ├── cpu.weight  ← CPU 权重
│  ├── cpu.stat  ← CPU 统计
│  ├── memory.max  ← 内存硬限制
│  ├── memory.high  ← 内存软限制
│  ├── memory.current  ← 当前内存使用
│  ├── memory.stat  ← 内存统计
│  ├── io.max  ← IO 限制
│  ├── io.weight  ← IO 权重
│  └── io.stat  ← IO 统计
└── system.slice/  ← systemd 创建的 cgroup
  └── ...
```

一个进程在树里只有一个位置。所有控制器共享同一棵层级结构。没有竞争条件。没有不一致。

![Cgroups v2 统一层级结构](https://quant67.com/post/containers/04-cgroups/cgroups-v2-hierarchy.svg)

从 Linux 5.x 开始，所有主流发行版默认使用 cgroups v2。如果你还在用 v1，请认真考虑迁移。

---

## 二、文件系统接口：mkdir 就是创建 cgroup

Cgroups v2 的接口就是文件系统。没有特殊的系统调用，没有 ioctl，就是读写文件。

### 创建 cgroup

```
# 就是创建一个目录
$ sudo mkdir /sys/fs/cgroup/mycontainer
$ ls /sys/fs/cgroup/mycontainer/
cgroup.controllers  cgroup.events  cgroup.procs  cgroup.stat
cgroup.subtree_control  cgroup.type  cpu.stat  io.stat  memory.current
memory.stat  ...
```

创建目录的瞬间，内核自动生成了所有控制文件。这不是普通文件系统 — 这是 `cgroup2fs`，每个文件背后是内核的 cgroup 子系统。

### 查看可用控制器

```
$ cat /sys/fs/cgroup/cgroup.controllers
cpuset cpu io memory hugetlb pids rdma misc
```

### 启用子树控制器

关键概念：**控制器必须在父 cgroup 的 `cgroup.subtree_control` 中启用，才能在子 cgroup 中使用。**

```
# 在根 cgroup 启用 cpu、memory、io 控制器
$ echo "+cpu +memory +io" | sudo tee /sys/fs/cgroup/cgroup.subtree_control
```

### 把进程加入 cgroup

```
# 把 PID 写进 cgroup.procs
$ echo $$ | sudo tee /sys/fs/cgroup/mycontainer/cgroup.procs

# 验证
$ cat /proc/self/cgroup
0::/mycontainer
```

就这样。没有魔法 API。`mkdir` + `echo` 就是全部接口。

### 删除 cgroup

```
# 先确保没有进程在里面
$ cat /sys/fs/cgroup/mycontainer/cgroup.procs
# (应该为空)

# 然后 rmdir
$ sudo rmdir /sys/fs/cgroup/mycontainer
```

注意是 `rmdir`，不是 `rm -rf`。你不能删除包含进程的 cgroup，也不能删除有子 cgroup 的 cgroup。必须自底向上清理。

---

## 三、CPU 控制：不是”限制”那么简单

### cpu.max — 硬上限

`cpu.max` 的格式是 `"quota period"`，单位是微秒：

```
# 每 100ms 里只能用 50ms CPU = 50% 的一个核
$ echo "50000 100000" | sudo tee /sys/fs/cgroup/mycontainer/cpu.max

# 不限制
$ echo "max 100000" | sudo tee /sys/fs/cgroup/mycontainer/cpu.max
```

这是 CFS（Completely Fair Scheduler）的带宽控制。内核在每个 `period` 开始时给 cgroup 分配 `quota` 微秒的 CPU 时间。用完了就等下个 period。

**多核场景**：quota 可以超过 period。`"200000 100000"` 表示每 100ms 可以用 200ms CPU 时间，即两个核的算力。

### cpu.weight — 相对权重

当 CPU 竞争时，`cpu.weight` 决定分配比例：

```
# 范围 1-10000，默认 100
$ echo 200 | sudo tee /sys/fs/cgroup/mycontainer/cpu.weight
```

如果 cgroup A 的 weight 是 200，cgroup B 是 100，CPU 紧张时 A 拿到 2/3，B 拿到 1/3。CPU 空闲时两者都能用满。

**weight 和 max 的区别**：weight 是”竞争时的公平性”，max 是”绝对不能超过”。生产环境两个都要设。

### CFS 带宽节流的隐藏代价

这里有个坑。CFS 带宽控制有个众所周知的尾延迟问题。

假设你设了 `"50000 100000"`（50% CPU）。你的程序在一个 period 的前 50ms 里把 quota 用完了。然后它就被 throttle 了，**即使 CPU 完全空闲**，它也要等到下个 period（还有 50ms）才能运行。

如果你的程序是个 web 服务器，这 50ms 的等待直接加到了请求延迟上。P99 延迟暴涨。

**怎么发现问题？看 `cpu.stat`：**

```
$ cat /sys/fs/cgroup/mycontainer/cpu.stat
usage_usec 23456789
user_usec 20000000
system_usec 3456789
nr_periods 1200
nr_throttled 342
throttled_usec 17100000
```

**`nr_throttled` 是最重要的指标。** 如果这个数字在快速增长，说明你的 CPU 限制太紧了，进程在频繁被节流。很多生产事故的根因都是：容器 CPU limit 设太低 → 频繁 throttle → 延迟飙升 → 超时 → 雪崩。

Kubernetes 社区有个长期争论：到底该不该设 CPU limit。反对方的核心论点就是 CFS 带宽节流的尾延迟问题。你可以只设 `cpu.weight`（对应 K8s 的 `requests`）不设 `cpu.max`（对应 K8s 的 `limits`）— 这样 CPU 竞争时有公平性保障，但不会出现”CPU 空闲却被 throttle”的荒谬场景。

---

## 四、内存控制：soft limit 比 hard limit 更重要

### memory.max — 硬限制

```
# 64MB 硬限制
$ echo 67108864 | sudo tee /sys/fs/cgroup/mycontainer/memory.max
```

超过这个值，内核触发 OOM killer。简单粗暴。

### memory.high — 软限制（更有用）

```
# 56MB 软限制
$ echo 58720256 | sudo tee /sys/fs/cgroup/mycontainer/memory.high
```

`memory.high` 是更温和的方式：超过这个值时，内核会**积极回收**这个 cgroup 的内存（把 page cache 刷到磁盘、压缩匿名页等），并**故意减慢**内存分配速度。具体来说，用户线程会在分配路径上被迫进入 direct reclaim / compaction，自己替内核”还债”。进程会变慢，但不会被杀。

**memory.high、memory.max、memory.low 三者的关系 — 决策指南：**

把它们想成三道防线：

   
|接口|角色|触发后果|类比|
|---|---|---|---|
|`memory.low`|保护线|内核在回收内存时**尽量不动**这个 cgroup，除非全局压力太大|“最低生活保障”|
|`memory.high`|软限制 / 节流线|超过后内核**积极回收 + 故意减慢**内存分配，进程变慢但**不会被杀**|“黄灯，减速”|
|`memory.max`|硬限制 / 生死线|超过且回收失败 → **OOM kill**|“红灯，撞了就死”|

最佳实践：把 `memory.high` 设在 `memory.max` 的 **85–90%** 左右。比如你的硬限制是 512MB，那就把 `memory.high` 设到 ~435–460MB。这样当内存使用接近上限时，进程会先被节流减速（给你发现问题的时间窗口），而不是直接被 OOM 一刀切。`memory.low` 则用来保护关键服务 — 比如你的数据库 cgroup 设一个 `memory.low`，在整机内存紧张时内核会优先回收其他 cgroup 的内存。

简单记：**low 保底，high 预警，max 兜底。三道防线，层层递进。**

### memory.low — 最低保障

```
$ echo 33554432 | sudo tee /sys/fs/cgroup/mycontainer/memory.low
```

`memory.low` 是”尽力保护”：内核在回收内存时会尽量避免动这个 cgroup 的内存，除非系统整体内存压力太大。用来保护关键服务不被饿死。

### OOM 行为：memory.oom.group

默认情况下，OOM killer 挑选 cgroup 里”最胖”的进程杀掉。但容器场景下，你通常希望杀掉**整个** cgroup：

```
# 启用组杀
$ echo 1 | sudo tee /sys/fs/cgroup/mycontainer/memory.oom.group
```

启用后，一旦触发 OOM，cgroup 内的所有进程一起被杀。这更符合容器语义 — 容器要么活着，要么整个死掉，不要搞”杀了一个进程剩下的带着残缺状态继续跑”。

### memory.stat — 理解内存去了哪里

```
$ cat /sys/fs/cgroup/mycontainer/memory.stat
anon 12345678
file 8765432
kernel 2345678
shmem 123456
...
pgfault 98765
pgmajfault 12
...
```

关键字段：

|字段|含义|
|---|---|
|`anon`|匿名页（堆、栈、mmap 的 MAP_ANONYMOUS）|
|`file`|page cache（读写文件产生的缓存）|
|`kernel`|内核为这个 cgroup 分配的内存（slab、页表等）|
|`shmem`|共享内存和 tmpfs|
|`pgfault`|minor page fault 次数|
|`pgmajfault`|major page fault（需要从磁盘读）次数|

`memory.current` 是总数，`memory.stat` 告诉你细分。当你调查”内存去了哪里”的时候，`memory.stat` 是第一个看的地方。

如果你用 jemalloc 或 tcmalloc 这样的内存分配器，它们的 arena 和线程缓存可能导致 `memory.current` 远高于程序实际的工作集。详见 [内存分配器：arena 与碎片](https://quant67.com/post/linux/allocator-arena/allocator-arena.html)。

---

## 五、IO 控制：曾经坏了很多年

### io.max — 硬限制

IO 限制按设备设置，需要先知道设备的 major:minor 号：

```
# 查看设备号
$ lsblk -o NAME,MAJ:MIN
NAME  MAJ:MIN
sda  8:0
├─sda1  8:1
└─sda2  8:2

# 限制 sda 的读写带宽和 IOPS
$ echo "8:0 rbps=10485760 wbps=10485760 riops=1000 wiops=1000" | \
  sudo tee /sys/fs/cgroup/mycontainer/io.max
```

四个参数： - `rbps` / `wbps`：读/写字节带宽（bytes/sec） - `riops` / `wiops`：读/写 IOPS

### io.weight — 比例权重

```
# 范围 1-10000，默认 100
$ echo "default 200" | sudo tee /sys/fs/cgroup/mycontainer/io.weight
```

### 为什么 IO 控制坏了很多年

v1 的 blkio 控制器有个致命缺陷：**它只对 direct IO 生效。**

Linux 的 IO 路径是这样的： 1. 应用程序调用 `write()` — 数据写入 page cache（内存），立刻返回 2. 内核的 writeback 线程在后台把 page cache 刷到磁盘

问题在于，writeback 线程是内核线程，不属于任何容器的 cgroup。v1 的 blkio 控制器在 IO 调度器层做限制，但 buffered write 到达 IO 调度器时，已经不知道它来自哪个 cgroup 了。

结果就是：你设了 `blkio.throttle.write_bps_device`，你的程序用 buffered write 照样可以瞬间把 page cache 塞满，然后 writeback 压力把整台机器的 IO 打满。你的 IO 限制形同虚设。

**Cgroups v2 通过 writeback 感知（writeback-aware IO controller）解决了这个问题。** 在 v2 中，page cache 会记住它属于哪个 cgroup，writeback 时会正确计入对应 cgroup 的 IO 配额。但需要内核和文件系统都支持（ext4 和 btrfs 支持，XFS 在较新内核中支持）。

这是从 v1 迁移到 v2 最重要的理由之一。

---

## 六、完整示例：从创建到压测

下面的 C 程序演示了完整流程：创建 cgroup、设限制、fork 子进程进去、跑压测、监控统计数据。

```c
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

#define CGROUP_ROOT "/sys/fs/cgroup"
#define CGROUP_NAME "demo_container"
#define CGROUP_PATH CGROUP_ROOT "/" CGROUP_NAME

// 向 cgroup 控制文件写入字符串
static int cg_write(const char *path, const char *value) {
  int fd = open(path, O_WRONLY);
  if (fd < 0) { perror(path); return -1; }
  int ret = write(fd, value, strlen(value));
  close(fd);
  return ret < 0 ? -1 : 0;
}

// 读取 cgroup 控制文件
static int cg_read(const char *path, char *buf, size_t len) {
  int fd = open(path, O_RDONLY);
  if (fd < 0) { perror(path); return -1; }
  ssize_t n = read(fd, buf, len - 1);
  close(fd);
  if (n < 0) return -1;
  buf[n] = '\0';
  return 0;
}

// 子进程压测：吃 CPU 和内存
static void stress_workload(void) {
  printf("[child %d] 开始压测...\n", getpid());

  // CPU 压测：忙循环
  volatile unsigned long counter = 0;
  // 内存压测：分配 32MB
  size_t alloc_size = 32 * 1024 * 1024;
  char *mem = malloc(alloc_size);
  if (mem) {
  memset(mem, 0xAA, alloc_size);
  printf("[child] 已分配并填充 %zu MB\n", alloc_size / (1024 * 1024));
  }

  for (int i = 0; i < 5; i++) {
  for (long j = 0; j < 100000000L; j++)
  counter++;
  printf("[child] CPU 循环 %d/5 完成, counter=%lu\n", i + 1, counter);
  }

  free(mem);
  printf("[child] 压测结束\n");
}

int main(void) {
  char buf[4096];

  // 1. 确保子控制器已启用
  printf("=== 启用 cpu 和 memory 控制器 ===\n");
  cg_write(CGROUP_ROOT "/cgroup.subtree_control", "+cpu +memory");

  // 2. 创建 cgroup
  printf("=== 创建 cgroup: %s ===\n", CGROUP_PATH);
  if (mkdir(CGROUP_PATH, 0755) && errno != EEXIST) {
  perror("mkdir cgroup");
  return 1;
  }

  // 3. 设置限制
  printf("=== 设置 CPU 限制: 50%% ===\n");
  cg_write(CGROUP_PATH "/cpu.max", "50000 100000");

  printf("=== 设置内存限制: 64MB ===\n");
  cg_write(CGROUP_PATH "/memory.max", "67108864");
  cg_write(CGROUP_PATH "/memory.high", "58720256");

  // 4. Fork 子进程
  pid_t pid = fork();
  if (pid < 0) { perror("fork"); return 1; }

  if (pid == 0) {
  // 子进程：把自己加入 cgroup
  char pid_str[32];
  snprintf(pid_str, sizeof(pid_str), "%d", getpid());
  cg_write(CGROUP_PATH "/cgroup.procs", pid_str);
  printf("[child %s] 已加入 cgroup\n", pid_str);

  stress_workload();
  _exit(0);
  }

  // 5. 父进程：监控 cgroup 统计数据
  printf("\n=== 父进程监控中 (每秒一次) ===\n");
  for (int i = 0; i < 8; i++) {
  sleep(1);

  printf("\n--- 第 %d 秒 ---\n", i + 1);

  if (cg_read(CGROUP_PATH "/memory.current", buf, sizeof(buf)) == 0)
  printf("memory.current: %s", buf);

  if (cg_read(CGROUP_PATH "/cpu.stat", buf, sizeof(buf)) == 0) {
  // 只打印关键行
  char *line = strtok(buf, "\n");
  while (line) {
  if (strstr(line, "throttled") || strstr(line, "usage"))
  printf("cpu.stat: %s\n", line);
  line = strtok(NULL, "\n");
  }
  }
  }

  // 6. 等待子进程
  int status;
  waitpid(pid, &status, 0);
  printf("\n子进程退出, status=%d\n", WEXITSTATUS(status));

  // 7. 清理
  printf("=== 清理 cgroup ===\n");
  rmdir(CGROUP_PATH);

  return 0;
}
```

编译运行（需要 root）：

```
$ make
$ sudo ./cgroup_demo
=== 启用 cpu 和 memory 控制器 ===
=== 创建 cgroup: /sys/fs/cgroup/demo_container ===
=== 设置 CPU 限制: 50% ===
=== 设置内存限制: 64MB ===
[child 12345] 已加入 cgroup
[child 12345] 开始压测...
[child] 已分配并填充 32 MB

=== 父进程监控中 (每秒一次) ===

--- 第 1 秒 ---
memory.current: 33816576
cpu.stat: usage_usec 498213
cpu.stat: nr_throttled 3
cpu.stat: throttled_usec 1502345

--- 第 2 秒 ---
memory.current: 33816576
cpu.stat: usage_usec 997856
cpu.stat: nr_throttled 8
cpu.stat: throttled_usec 4012345
...
```

注意 `nr_throttled` 在增长 — 因为我们设了 50% CPU 限制，进程的忙循环不断被节流。

完整代码和 OOM 演示见 `examples/containers/04-cgroups/`。

---

## 七、OOM 实战：让 cgroup 一起去死

OOM killer 是 Linux 里最让人头疼的机制之一。我们来故意触发它：

```c
#define CGROUP_PATH "/sys/fs/cgroup/oom_test"

int main(void) {
  // 创建 cgroup，设 8MB 内存限制
  mkdir(CGROUP_PATH, 0755);
  cg_write(CGROUP_PATH "/memory.max", "8388608");
  // 启用组杀 — OOM 时杀掉整个 cgroup
  cg_write(CGROUP_PATH "/memory.oom.group", "1");

  pid_t pid = fork();
  if (pid == 0) {
  // 加入 cgroup
  char s[32]; snprintf(s, sizeof(s), "%d", getpid());
  cg_write(CGROUP_PATH "/cgroup.procs", s);

  // 疯狂分配内存直到被杀
  size_t total = 0;
  while (1) {
  char *p = malloc(1024 * 1024);
  if (!p) break;
  memset(p, 0xFF, 1024 * 1024);
  total += 1024 * 1024;
  printf("已分配 %zu MB\n", total / (1024*1024));
  }
  _exit(0);
  }

  int status;
  waitpid(pid, &status, 0);

  if (WIFSIGNALED(status))
  printf("子进程被信号 %d 杀死 (SIGKILL=%d)\n",
  WTERMSIG(status), SIGKILL);

  // 查看 OOM 事件
  char buf[256];
  cg_read(CGROUP_PATH "/memory.events", buf, sizeof(buf));
  printf("memory.events:\n%s\n", buf);

  rmdir(CGROUP_PATH);
  return 0;
}
```

运行输出：

```
$ sudo ./oom_demo
已分配 1 MB
已分配 2 MB
已分配 3 MB
已分配 4 MB
已分配 5 MB
已分配 6 MB
子进程被信号 9 杀死 (SIGKILL=9)
memory.events:
low 0
high 0
max 12
oom 1
oom_kill 1
oom_group_kill 1
```

`memory.events` 里的 `oom_kill` 和 `oom_group_kill` 计数器清楚地记录了 OOM 事件。这是线上排查 OOM 的关键文件 — 不要去翻 dmesg 了。

完整源码见 `examples/containers/04-cgroups/oom_demo.c`。

---

## 八、给代码加限制时的几个坑

### 坑 1：subtree_control 的”no internal processes”规则

Cgroups v2 有个重要限制：**如果一个 cgroup 启用了 subtree_control，它自身不能包含进程**（leaf cgroup 除外）。

```
# 这样做会报错
$ echo "+cpu" > /sys/fs/cgroup/mygroup/cgroup.subtree_control
$ echo $$ > /sys/fs/cgroup/mygroup/cgroup.procs
# Error: Device or resource busy
```

进程只能放在叶子 cgroup 里。这是为了避免”父 cgroup 的资源限制和子 cgroup 的资源限制互相矛盾”的问题。

### 坑 2：memory.max 的 OOM 是异步的

设了 `memory.max` 后，进程分配内存到达上限时不会立刻收到 SIGKILL。内核会先尝试回收（reclaim），如果回收失败才触发 OOM killer。这中间可能有几十毫秒到几秒的延迟，进程处于半死不活的 reclaim 状态。

所以在实际使用中，`memory.high` 比 `memory.max` 更有用 — 它在到达限制前就开始减速，避免突然死亡。

### 坑 3：CPU 统计的时间基准

`cpu.stat` 里的 `usage_usec` 是 CPU 时间，不是墙钟时间。如果你的程序跑在 4 个核上，1 秒墙钟时间对应 4 秒 CPU 时间（4,000,000 usec）。计算 CPU 使用率时别忘了除以核数。

---

现在让我们把视野拉高。当 Docker 或 containerd 创建一个容器时，在 cgroups 层面发生了什么？

```
/sys/fs/cgroup/
└── system.slice/  ← systemd 创建的
  └── docker-<container_id>.scope/  ← Docker 创建的
  ├── cpu.max  = "100000 100000"  ← --cpus=1
  ├── memory.max  = "536870912"  ← --memory=512m
  ├── memory.high  = "429496729"  ← (Docker 可能自动设)
  ├── pids.max  = "1024"  ← --pids-limit=1024
  └── cgroup.procs  = "12345\n12346\n"  ← 容器里的进程
```

Docker 做的事情和我们上面的 C 代码一模一样：mkdir、写文件、把进程 PID echo 进去。没有魔法。

Kubernetes 更复杂一些 — 它通过 kubelet 管理 cgroup hierarchy，支持 Pod 级别（QoS class）和容器级别的限制：

```
/sys/fs/cgroup/
└── kubepods.slice/
  ├── kubepods-burstable.slice/  ← Burstable QoS
  │  └── kubepods-burstable-pod<id>.slice/
  │  └── cri-containerd-<id>.scope/
  │  ├── cpu.max
  │  └── memory.max
  └── kubepods-besteffort.slice/  ← BestEffort QoS
  └── ...
```

---

## 十、一张表总结 Cgroups v2 接口

  
|文件|用途|示例值|
|---|---|---|
|`cgroup.procs`|加入/查看进程|`echo 1234 > cgroup.procs`|
|`cgroup.controllers`|可用控制器|`cpu memory io pids`|
|`cgroup.subtree_control`|子树启用的控制器|`echo "+cpu +memory" > ...`|
|`cpu.max`|CPU 硬限制 (quota period)|`"50000 100000"` = 50%|
|`cpu.weight`|CPU 相对权重|`1-10000`，默认 `100`|
|`cpu.stat`|CPU 统计|`nr_throttled`, `throttled_usec`|
|`memory.max`|内存硬限制|`67108864` (64MB)|
|`memory.high`|内存软限制（节流）|`58720256` (56MB)|
|`memory.low`|内存保护|`33554432` (32MB)|
|`memory.current`|当前内存使用|只读|
|`memory.stat`|内存细分统计|`anon`, `file`, `kernel`|
|`memory.oom.group`|OOM 时组杀|`0` 或 `1`|
|`memory.events`|OOM 事件计数|`oom`, `oom_kill`|
|`io.max`|IO 限制|`"8:0 rbps=10485760 wbps=10485760"`|
|`io.weight`|IO 相对权重|`"default 100"`|
|`pids.max`|进程数限制|`1024` 或 `max`|
|`pids.events`|PID 限制触发计数|`max 42`|
|`/proc/pressure/{cpu,memory,io}`|PSI 压力指标|`some avg10=0.50 ...`|

`pids.max` 是防 fork bomb 的最后一道闸门。Web 服务、CI worker 这类会短时间拉起大量子进程的容器，建议把 `pids.events` 一起盯上。PSI（Pressure Stall Information）补的是另一个视角：资源也许还没打满，但线程已经开始因为 reclaim、throttle、IO 等待而停顿了。只看 usage，不看 pressure，很容易错过尾延迟恶化的前兆。

---

## 十一、排障指南：Cgroup 配置不生效怎么办

线上最让人崩溃的事：你明明设了限制，但进程就是不受控。下面是一套实用的排查清单。

### 1. 进程到底在哪个 cgroup 里？

第一步永远是确认进程真的在你期望的 cgroup 中：

```
$ cat /proc/<PID>/cgroup
0::/system.slice/docker-abc123.scope
```

如果输出的路径不是你设的那个 cgroup，那限制当然不生效。常见原因：进程被 systemd 或容器运行时移到了别的 cgroup，或者你写 `cgroup.procs` 时用了错误的 PID。

### 2. 控制器启用了吗？

光创建 cgroup 目录不够，控制器必须在**父 cgroup** 的 `subtree_control` 中显式启用：

```
# 查看当前 cgroup 可用的控制器
$ cat /sys/fs/cgroup/mygroup/cgroup.controllers
cpu memory io

# 查看父 cgroup 启用了哪些控制器给子树
$ cat /sys/fs/cgroup/cgroup.subtree_control
cpu memory
```

如果你想在 `mygroup` 里用 `io` 控制器，但父级的 `cgroup.subtree_control` 里没有 `io`，写 `io.max` 会直接报错或者文件根本不存在。修复方法：

```
$ echo "+io" | sudo tee /sys/fs/cgroup/cgroup.subtree_control
```

### 3. “no internal processes” 踩坑

Cgroups v2 的规则：**如果一个 cgroup 的 `subtree_control` 启用了任何控制器，那这个 cgroup 本身不能有进程。** 进程只能待在叶子节点。

典型症状：你往一个有子 cgroup 的目录写 `cgroup.procs`，得到 `Device or resource busy` 错误。

```
# 错误示范
$ echo "+cpu" | sudo tee /sys/fs/cgroup/mygroup/cgroup.subtree_control
$ echo $$ | sudo tee /sys/fs/cgroup/mygroup/cgroup.procs
# echo: write error: Device or resource busy
```

解决方法：把进程放到叶子 cgroup 里，而不是放到启用了 `subtree_control` 的中间节点。

### 4. 谁被 OOM 杀了？怎么查？

进程突然消失了，怀疑是 OOM？三步确认：

```
# 第一步：查看 cgroup 的 OOM 事件计数
$ cat /sys/fs/cgroup/mygroup/memory.events
low 0
high 234
max 12
oom 3
oom_kill 3
oom_group_kill 1

# 第二步：内核日志
$ dmesg | grep -i oom
[12345.678] memory cgroup out of memory: Killed process 9876 (myapp)

# 第三步：systemd journal（如果用 systemd 管理）
$ journalctl -k | grep -i oom
```

`memory.events` 是最精确的 — 它只统计**这个 cgroup** 的 OOM 事件，不会被其他 cgroup 的噪音干扰。`oom_kill` 是实际杀掉进程的次数，`oom` 是触发 OOM 流程的次数（可能回收成功没有真的杀）。

### 5. CPU 被节流了？怎么确认？

应用延迟飙升但 CPU 使用率”看起来不高”？很可能是 CFS 带宽节流。查 `cpu.stat`：

```
$ cat /sys/fs/cgroup/mygroup/cpu.stat
usage_usec 23456789
user_usec 20000000
system_usec 3456789
nr_periods 12000
nr_throttled 3420
throttled_usec 171000000
```

关键看两个数字： - **`nr_throttled`**：被节流的周期数。如果这个数字在持续增长，说明 `cpu.max` 的 quota 设得太紧。 - **`throttled_usec`**：累计被节流的总时间。`throttled_usec / nr_throttled` 就是平均每次被节流多久。

如果 `nr_throttled / nr_periods` 的比例超过 5–10%，就该考虑放宽 CPU 限制了（或者干脆只用 `cpu.weight` 不设 `cpu.max`）。

### 6. systemd 和你的运行时打架

这是个常见但容易被忽略的问题。systemd 会主动管理 cgroup 树 — 它把自己当成 cgroup 层级的”管理员”。如果你同时用 systemd 和另一个运行时（比如直接用 runc、或者自己写的程序）操作同一棵 cgroup 子树，就会出现冲突：

- systemd 可能把你手动创建的 cgroup 当成”不认识的垃圾”给清理掉
- 你的运行时写了 `subtree_control`，systemd 也写了，互相覆盖
- systemd 的 scope/slice 机制会把进程移到它认为”正确”的位置

解决思路：

1. **如果你用 Docker/containerd/CRI-O**：让它们和 systemd 协商，不要手动操作它们管理的 cgroup 子树。
2. **如果你自己管理 cgroup**：在 systemd 管理范围之外创建你的子树，或者用 `systemd-run --scope` 让 systemd 知道你的 cgroup 的存在。
3. **排查方式**：`systemctl status` 和 `systemd-cgls` 可以看到 systemd 视角下的 cgroup 树，对比 `cat /proc/<PID>/cgroup` 的实际位置。

---

## 十二、从这里往哪走

Namespace 管”看见什么”（[第一篇](https://quant67.com/post/containers/01-namespaces/namespaces.html)），Cgroups 管”用多少”。但现在容器的文件系统还是宿主机的 — 每次都要从零构建 rootfs 太蠢了。

下一篇我们来解决分层文件系统的问题：[OverlayFS — 让镜像可以叠加](https://quant67.com/post/containers/05-overlayfs/overlayfs.html)。然后在 [第六篇](https://quant67.com/post/containers/06-mini-runtime/mini-runtime.html) 里，我们把 namespace + cgroups + overlayfs 组装成一个真正能用的迷你容器运行时。

## 相关阅读

- [Linux Namespaces：用 50 行 C 隔离一个进程](https://quant67.com/post/containers/01-namespaces/namespaces.html) — 容器隔离的第一步
- [OverlayFS：让镜像可以叠加](https://quant67.com/post/containers/05-overlayfs/overlayfs.html) — 分层文件系统
- [迷你容器运行时](https://quant67.com/post/containers/06-mini-runtime/mini-runtime.html) — 把所有组件拼起来
- [内存分配器：arena 与碎片](https://quant67.com/post/linux/allocator-arena/allocator-arena.html) — jemalloc/tcmalloc 在 cgroup 限制下的行为

## 同主题继续阅读

把当前热点继续串成多页阅读，而不是停在单篇消费。

2026-04-01 · linux / containers

### [【从零造容器】Linux Namespaces：用 50 行 C 隔离一个进程](https://quant67.com/post/containers/01-namespaces/namespaces.html)

容器不是魔法。它就是几个系统调用。本文用 C 从 clone() 开始，逐个开启 PID/UTS/Mount/IPC namespace，看隔离到底是怎么回事。50 行代码，你就拥有了一个'容器'的雏形。

2026-04-01 · linux / containers

### [【从零造容器】Network Namespace：给你的进程接上虚拟网线](https://quant67.com/post/containers/02-netns/netns.html)

上一篇我们用 clone() 隔离了 PID、主机名和挂载点，但那个'容器'连 lo 都 ping 不通。本文从 CLONE_NEWNET 出发，用 veth pair + bridge + iptables MASQUERADE，一步步给容器接上网。

2026-04-02 · linux / containers

### [【从零造容器】Mount Namespace 与 pivot_root：构建容器文件系统](https://quant67.com/post/containers/03-rootfs/rootfs.html)

chroot 不是安全边界——10 行 C 就能逃出去。本文用 pivot_root 构建真正隔离的容器根文件系统：从 Alpine minirootfs 到设备节点，从 mount propagation 到只读根，一步步把容器的'地基'打牢。

2026-04-08 · linux / containers

### [【从零造容器】Seccomp-BPF 与 Capabilities：容器安全的两道防线](https://quant67.com/post/containers/08-security/security.html)

你的容器能调用 reboot()。是的，现在就能。除非有人拦住它。Capabilities 拆分 root 权限，Seccomp-BPF 过滤系统调用——两道防线，缺一不可。本文用 C 代码拆解这两套机制，看看 Docker 到底替你挡住了什么。