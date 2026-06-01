你在终端里敲下 `docker run -it alpine sh`，Docker 花了不到一秒就给你一个”干净的操作系统”。`ps` 只看到 shell 自己，`hostname` 是随机字符串，文件系统是 Alpine 的。看起来像虚拟机？不是。没有 hypervisor，没有 guest kernel，没有硬件模拟。

这一切的底层，就是一个系统调用：`clone()`，加上几个 flag。

本系列文章将从零实现一个 OCI 兼容的迷你容器运行时。这是第一篇，我们只聊一个问题：**Linux 怎么让一个进程以为自己是整个世界的唯一居民**。

> 本文所有代码在 `examples/containers/01-namespaces/` 目录，`make` 即可编译运行。测试环境：Linux 6.x, x86_64。
> 
> 注意：**实验环境建议**：本文的代码会修改 namespace、挂载点和主机名。请在虚拟机或专用测试机上运行，不要在你的工作笔记本上直接 `sudo`。

---

## 一、Namespace 是什么：内核视角的”平行宇宙”

操作系统的很多资源是全局的：进程 ID 空间、主机名、挂载点表、网络栈、IPC 队列。所有进程共享同一份。

Namespace 的作用很简单：**给某些进程一份独立的副本**。同一个内核，但不同的进程看到不同的”世界”。

Linux 提供 8 种 namespace：

   
|Namespace|Flag|隔离的内容|内核版本|
|---|---|---|---|
|Mount|`CLONE_NEWNS`|挂载点表|2.4.19 (2002)|
|UTS|`CLONE_NEWUTS`|主机名和域名|2.6.19 (2006)|
|IPC|`CLONE_NEWIPC`|System V IPC、POSIX 消息队列|2.6.19 (2006)|
|PID|`CLONE_NEWPID`|进程 ID 空间|2.6.24 (2008)|
|Network|`CLONE_NEWNET`|网络栈（接口、路由、iptables）|2.6.29 (2009)|
|User|`CLONE_NEWUSER`|UID/GID 映射|3.8 (2013)|
|Cgroup|`CLONE_NEWCGROUP`|Cgroup 根目录视图|4.6 (2016)|
|Time|`CLONE_NEWTIME`|系统时钟偏移|5.6 (2020)|

注意这些年份。Mount namespace 在 2002 年就有了，比 Docker（2013）早了 11 年。容器技术不是发明，是拼装。

![Namespace 隔离层级](https://quant67.com/post/containers/01-namespaces/namespace-layers.svg)

两种方式创建 namespace：

1. **`clone()`** — 创建子进程的同时放进新 namespace
2. **`unshare()`** — 把当前进程移入新 namespace（不创建子进程）

我们从 `clone()` 开始，因为它更接近容器运行时的实际做法。

---

## 二、第一步：PID Namespace — “我是 PID 1”

PID namespace 让子进程以为自己的 PID 是 1。这不只是”改个数字”那么简单 — PID 1 在 Linux 里有特殊语义：

- 同一个 PID namespace 内的其他进程不能随便给 PID 1 发信号：只有 PID 1 显式注册了处理函数的信号才会被投递。例外是来自祖先 namespace 的 `SIGKILL` 和 `SIGSTOP`，内核会强制投递
- 所有孤儿进程会被 PID 1 收养
- PID 1 退出，整个 PID namespace 里的进程全部被杀

这就是为什么容器里经常看到 zombie 进程 — 如果你的 PID 1 不 `wait()` 子进程，它们就永远留在那里。

来看代码（为突出重点，只保留核心逻辑，完整版本见第六节）：

```c
#define _GNU_SOURCE
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/wait.h>

#define STACK_SIZE (1024 * 1024)

static int child_fn(void *arg) {
  printf("child: PID = %d\n", getpid());
  printf("child: PPID = %d\n", getppid());

  // 在新 PID namespace 里，我们是 PID 1
  char *argv[] = {"/bin/sh", NULL};
  execv("/bin/sh", argv);
  perror("execv");
  return 1;
}

int main() {
  char *stack = malloc(STACK_SIZE);
  if (!stack) {
  perror("malloc");
  return 1;
  }

  // CLONE_NEWPID: 创建新的 PID namespace
  pid_t pid = clone(child_fn, stack + STACK_SIZE,
  CLONE_NEWPID | SIGCHLD, NULL);
  if (pid == -1) {
  perror("clone");
  return 1;
  }

  printf("parent: child PID in our namespace = %d\n", pid);
  waitpid(pid, NULL, 0);
  free(stack);
  return 0;
}
```

编译运行（需要 root）：

```
$ gcc -o pid_ns pid_ns.c
$ sudo ./pid_ns
parent: child PID in our namespace = 28431
child: PID = 1
child: PPID = 0
```

子进程看到自己的 PID 是 1，但父进程看到的是宿主机上的真实 PID（28431）。这就是 namespace 的本质：**同一个进程，从不同 namespace 看到不同的 ID**。

注意 PPID 是 0 — 因为父进程不在子进程的 PID namespace 里，内核用 0 表示”不可见的父进程”。

### 但是有个问题

在子进程的 shell 里执行 `ps aux`，你会发现看到的还是宿主机的所有进程。为什么？

因为 `ps` 读的是 `/proc` 文件系统，而我们还没有隔离挂载点。现在的 `/proc` 还是宿主机的。要解决这个问题，我们需要 Mount namespace + 重新挂载 `/proc`。

---

## 三、加上 UTS Namespace — “我叫什么名字”

UTS namespace 隔离主机名和域名。这是最简单的 namespace，但也最能直观体现隔离效果：

```c
static int child_fn(void *arg) {
  // 设置新主机名
  sethostname("mycontainer", 11);

  char hostname[64];
  gethostname(hostname, sizeof(hostname));
  printf("child hostname: %s\n", hostname);

  execv("/bin/sh", (char *[]){"/bin/sh", NULL});
  return 1;
}

int main() {
  char *stack = malloc(STACK_SIZE);
  pid_t pid = clone(child_fn, stack + STACK_SIZE,
  CLONE_NEWPID | CLONE_NEWUTS | SIGCHLD, NULL);
  // ...
}
```

子进程可以随意改主机名，不影响宿主机。Docker 的 `--hostname` 就是这么实现的。

---

## 四、Mount Namespace — 让 /proc 说真话

这是最关键的一步。Mount namespace 让子进程拥有独立的挂载点表，这意味着子进程里的 `mount` / `umount` 不影响宿主机。

加上 Mount namespace 后，我们可以重新挂载 `/proc`，让 `ps` 只看到容器内的进程：

```c
static int child_fn(void *arg) {
  sethostname("container", 9);

  // 重新挂载 /proc，让它反映新的 PID namespace
  if (mount("proc", "/proc", "proc", 0, NULL) == -1) {
  perror("mount /proc");
  return 1;
  }

  printf("child PID: %d\n", getpid());
  printf("--- ps output inside container ---\n");
  system("ps aux");

  execv("/bin/sh", (char *[]){"/bin/sh", NULL});
  return 1;
}

int main() {
  char *stack = malloc(STACK_SIZE);
  pid_t pid = clone(child_fn, stack + STACK_SIZE,
  CLONE_NEWPID | CLONE_NEWUTS | CLONE_NEWNS | SIGCHLD,
  NULL);
  // ...
}
```

现在 `ps` 只能看到容器内的进程了。但这里有一个坑：**我们直接改了宿主机的 `/proc`**。

为什么？因为虽然 mount namespace 是新的，但它是父 namespace 的副本。默认情况下，新旧 namespace 之间的挂载点是**共享的**（shared propagation）。你在新 namespace 里 mount `/proc`，宿主机上的 `/proc` 也被覆盖了。

解决方法是在子进程里先把根文件系统的 propagation 改成 private：

```c
// 阻止挂载事件传播到父 namespace
mount("", "/", "", MS_PRIVATE | MS_REC, NULL);

// 现在安全地重新挂载 /proc
mount("proc", "/proc", "proc", 0, NULL);
```

`MS_PRIVATE | MS_REC` 递归地把所有挂载点设为 private，切断与父 namespace 的传播链。这条语句在几乎所有容器运行时里都能找到。

---

## 五、IPC Namespace — 隔离进程间通信

IPC namespace 隔离 System V IPC 对象（共享内存段、消息队列、信号量）和 POSIX 消息队列。

加上 `CLONE_NEWIPC` 即可：

```c
pid_t pid = clone(child_fn, stack + STACK_SIZE,
  CLONE_NEWPID | CLONE_NEWUTS | CLONE_NEWNS |
  CLONE_NEWIPC | SIGCHLD, NULL);
```

隔离前，容器进程可以用 `ipcs` 看到宿主机上的 IPC 对象，甚至可以 attach 宿主机的共享内存段。这是一个真实的安全风险。加上 IPC namespace 后，容器看到的是一个干净的 IPC 空间。

---

下面是完整版本。它同时创建 PID、UTS、Mount、IPC 四个 namespace，重新挂载 `/proc`，设置主机名，然后启动一个 shell：

```c
#define _GNU_SOURCE
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/mount.h>
#include <sys/wait.h>

#define STACK_SIZE (1024 * 1024)

static int child_fn(void *arg) {
  const char *hostname = (const char *)arg;
  sethostname(hostname, strlen(hostname));

  // 切断挂载传播
  mount("", "/", "", MS_PRIVATE | MS_REC, NULL);
  // 重新挂载 /proc
  mount("proc", "/proc", "proc", 0, NULL);

  printf("\n=== Inside container ===\n");
  printf("PID:  %d\n", getpid());

  char hn[64];
  gethostname(hn, sizeof(hn));
  printf("Hostname: %s\n", hn);
  printf("========================\n\n");

  // 启动 shell
  char *argv[] = {"/bin/sh", NULL};
  execv("/bin/sh", argv);
  perror("execv");
  return 1;
}

int main(int argc, char **argv) {
  const char *hostname = argc > 1 ? argv[1] : "container";

  char *stack = malloc(STACK_SIZE);
  if (!stack) { perror("malloc"); return 1; }

  int flags = CLONE_NEWPID | CLONE_NEWUTS | CLONE_NEWNS |
  CLONE_NEWIPC | SIGCHLD;

  pid_t pid = clone(child_fn, stack + STACK_SIZE,
  flags, (void *)hostname);
  if (pid == -1) { perror("clone"); return 1; }

  printf("parent: child PID = %d\n", pid);
  waitpid(pid, NULL, 0);
  free(stack);
  return 0;
}
```

运行效果：

```
$ sudo ./container mybox
parent: child PID = 31024

=== Inside container ===
PID:  1
Hostname: mybox
========================

/ # ps aux
PID  USER  TIME  COMMAND
  1 root  0:00 /bin/sh
  2 root  0:00 ps aux
/ # hostname
mybox
/ # ipcs
------ Message Queues --------
key  msqid  owner  perms  used-bytes  messages

------ Shared Memory Segments --------
key  shmid  owner  perms  bytes  nattch  status

------ Semaphore Arrays --------
key  semid  owner  perms  nsems
```

干净的进程列表，自定义主机名，空的 IPC 空间。50 行 C，没有 Docker，没有 containerd。

---

到目前为止我们用的都是 `clone()`。但还有另一种方式：`unshare()` 把**当前进程**移入新 namespace。

```c
// 当前进程进入新的 UTS namespace
unshare(CLONE_NEWUTS);
sethostname("unshared", 8);
// 主机名的改变不影响父 namespace
```

`unshare` 命令行工具就是封装了这个系统调用：

```
$ sudo unshare --pid --mount --uts --ipc --fork /bin/sh
# 效果和我们的 C 程序一样
```

**选择建议**： - 容器运行时用 `clone()`，因为需要创建子进程 - 调试和实验用 `unshare`，因为更方便 - `nsenter` 用于进入已有的 namespace（`docker exec` 的底层）

---

## 八、PID 1 的特殊责任

前面提到 PID 1 不会被内核杀死，但这也带来了责任。在容器里，PID 1 必须：

### 1. 回收僵尸进程

容器里如果跑了 daemon 进程，它 fork 的子进程退出后会变成僵尸，等待 PID 1 回收：

```c
// 容器 init 进程应该做的事
for (;;) {
  int status;
  pid_t pid = waitpid(-1, &status, WNOHANG);
  if (pid <= 0) break;
  // 收割完毕
}
```

这就是为什么 Docker 加了 `--init` 选项（使用 tini 作为 PID 1），以及为什么 Kubernetes 的 Pod 里经常看到 zombie 进程 — 应用程序没有处理 `SIGCHLD`。

### 2. 正确转发信号

PID 1 收到 `SIGTERM` 时，应该把信号转发给子进程，然后等它们退出。否则 `docker stop` 超时后只能用 `SIGKILL` 强杀，导致数据丢失。

```c
void handle_signal(int sig) {
  // 转发给所有子进程
  kill(0, sig);
}

signal(SIGTERM, handle_signal);
signal(SIGINT, handle_signal);
```

---

## 九、从内核看 Namespace

想看一个进程属于哪些 namespace？看 `/proc/PID/ns/`：

```
$ ls -la /proc/self/ns/
lrwxrwxrwx 1 root root 0 Apr  1 12:00 cgroup -> 'cgroup:[4026531835]'
lrwxrwxrwx 1 root root 0 Apr  1 12:00 ipc -> 'ipc:[4026531839]'
lrwxrwxrwx 1 root root 0 Apr  1 12:00 mnt -> 'mnt:[4026531841]'
lrwxrwxrwx 1 root root 0 Apr  1 12:00 net -> 'net:[4026531840]'
lrwxrwxrwx 1 root root 0 Apr  1 12:00 pid -> 'pid:[4026531836]'
lrwxrwxrwx 1 root root 0 Apr  1 12:00 user -> 'user:[4026531837]'
lrwxrwxrwx 1 root root 0 Apr  1 12:00 uts -> 'uts:[4026531838]'
```

方括号里的数字是 namespace 的 inode 号。两个进程如果某个 namespace 的 inode 号相同，它们就在同一个 namespace 里。

用代码获取：

```c
#include <sys/stat.h>

struct stat st;
stat("/proc/self/ns/pid", &st);
printf("PID namespace inode: %lu\n", st.st_ino);
```

这也是 `nsenter` 的工作原理 — 它打开目标进程的 `/proc/PID/ns/xxx` 文件，然后用 `setns()` 系统调用加入那个 namespace：

```c
int fd = open("/proc/12345/ns/pid", O_RDONLY);
setns(fd, CLONE_NEWPID);
// 现在我们和 PID 12345 在同一个 PID namespace 里了
```

---

## 十、我们还缺什么

这 50 行代码距离一个真正的容器还有很远：

  
|缺什么|为什么重要|本系列哪篇解决|
|---|---|---|
|Network namespace|容器需要独立的网络栈|[#02 Network Namespace](https://quant67.com/post/containers/02-netns/netns.html)|
|pivot_root|需要独立的根文件系统，chroot 不安全|[#03 Mount 与 pivot_root](https://quant67.com/post/containers/03-rootfs/rootfs.html)|
|Cgroups|不限制资源，一个容器能吃掉整台机器|[#04 Cgroups v2](https://quant67.com/post/containers/04-cgroups/cgroups.html)|
|OverlayFS|需要分层镜像，不能每次从零构建 rootfs|[#05 OverlayFS](https://quant67.com/post/containers/05-overlayfs/overlayfs.html)|
|Seccomp|容器进程不应该能调用所有系统调用|[#08 Seccomp-BPF](https://quant67.com/post/containers/08-security/security.html)|
|User namespace|不想用 root 跑容器|[#09 Rootless 容器](https://quant67.com/post/containers/09-rootless/rootless.html)|

还有两个 namespace 这篇只点到为止：`CLONE_NEWCGROUP` 和 `CLONE_NEWTIME`。前者影响容器里看到的 cgroup 路径，后者影响时钟偏移。它们对”做出第一个能跑的容器”不是必须，但在生产级运行时里都不是摆设。

但核心思想已经展示清楚了：**容器就是 namespace + cgroup + rootfs 的组合**。没有魔法，没有虚拟化，就是内核提供的隔离原语。

下一篇，我们给这个进程接上网线 — [Network Namespace](https://quant67.com/post/containers/02-netns/netns.html)。

## 相关阅读

- [eBPF：Linux 内核的隐藏武器](https://quant67.com/post/linux/ebpf/ebpf.html) — Seccomp 和 eBPF 共享同一个 BPF 虚拟机
- [io_uring 核心概念](https://quant67.com/post/io_uring/01-core-concepts.html) — 另一个”用几个系统调用改变一切”的内核特性
- [跨越世纪的挑战：C10K 到 C10M](https://quant67.com/post/system-design/c10k/c10k.html) — 网络编程的演进，容器网络是其中一环

## 同主题继续阅读

把当前热点继续串成多页阅读，而不是停在单篇消费。

2026-04-01 · linux / containers

### [【从零造容器】Network Namespace：给你的进程接上虚拟网线](https://quant67.com/post/containers/02-netns/netns.html)

上一篇我们用 clone() 隔离了 PID、主机名和挂载点，但那个'容器'连 lo 都 ping 不通。本文从 CLONE_NEWNET 出发，用 veth pair + bridge + iptables MASQUERADE，一步步给容器接上网。

2026-04-02 · linux / containers

### [【从零造容器】Mount Namespace 与 pivot_root：构建容器文件系统](https://quant67.com/post/containers/03-rootfs/rootfs.html)

chroot 不是安全边界——10 行 C 就能逃出去。本文用 pivot_root 构建真正隔离的容器根文件系统：从 Alpine minirootfs 到设备节点，从 mount propagation 到只读根，一步步把容器的'地基'打牢。

2026-04-03 · linux / containers

### [【从零造容器】Cgroups v2：让容器不能吃掉整台机器](https://quant67.com/post/containers/04-cgroups/cgroups.html)

你给容器设了 512MB 内存限制，结果宿主机上的数据库被 OOM-kill 了。Cgroups 不是'加个限制'那么简单 — v1 的设计是个历史错误，v2 才是正确答案。本文用 C 代码从 mkdir 开始，手动创建 cgroup，设 CPU/内存/IO 限制，压测，看它怎么把进程关进笼子。

2026-04-06 · linux / containers

### [【从零造容器】用 Go 组装迷你容器运行时：把积木拼起来](https://quant67.com/post/containers/06-mini-runtime/mini-runtime.html)

五篇文章攒了一堆内核积木：namespace、netns、rootfs、cgroup、overlayfs。现在是时候用 Go 把它们拼成一个能跑的容器运行时了。不到 500 行代码，create/start/exec/kill/delete，五个命令走完容器的一生。