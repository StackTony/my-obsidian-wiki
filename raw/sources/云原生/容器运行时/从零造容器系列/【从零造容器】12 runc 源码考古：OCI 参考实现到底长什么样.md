本系列从零造了一个容器运行时。500 行 Go，能跑，能隔离，能限制资源。

但 runc 有 15000 行。containerd 有 10 万行。Kubernetes 有 200 万行。

多出来的代码在干什么？

这一篇我们回到 runc — OCI Runtime 的参考实现，看看工业级容器运行时比我们的玩具多了什么。重点不是”每一行代码”，而是**那些我们的迷你运行时没考虑到的 edge case**。

> 本文基于 runc v1.1.x 版本分析。

---

```
runc
├── main.go  # CLI 入口
├── create.go / start.go  # OCI 命令实现
├── libcontainer/  # 核心引擎（可独立使用）
│  ├── container_linux.go  # Container 接口实现
│  ├── init_linux.go  # 容器 init 进程
│  ├── process_linux.go  # 进程管理
│  ├── nsenter/  # C 代码！
│  │  └── nsexec.c  # namespace 切换
│  ├── cgroups/  # cgroup 管理
│  ├── seccomp/  # seccomp 过滤
│  └── specconv/  # OCI spec → libcontainer config
└── ...
```

关键架构决策：

1. **libcontainer 是可独立使用的库**。runc 只是 libcontainer 的 CLI 封装。Docker/containerd 可以直接调用 libcontainer。
2. **nsenter 是 C 代码**。Go runtime 不能在 fork 后、exec 前安全执行代码（下面详解），所以 namespace 切换必须用 C。
3. **两阶段 init**。容器 init 进程分为 “bootstrap” 和 “standard” 两个阶段，中间通过 pipe 通信。

libcontainer 内部的包结构也值得了解：

  
|包|职责|代码量|
|---|---|---|
|`libcontainer/`|Container 接口、Factory、State 管理|核心约 3000 行|
|`libcontainer/cgroups/`|cgroup v1/v2 抽象层、systemd driver|~4000 行|
|`libcontainer/nsenter/`|C 代码，constructor 方式的 namespace 切换|~500 行 C|
|`libcontainer/seccomp/`|seccomp profile 加载|~300 行|
|`libcontainer/specconv/`|OCI runtime-spec JSON → libcontainer Config|~800 行|
|`libcontainer/devices/`|设备节点白名单管理|~400 行|

最大的包是 `cgroups/`——v1 的 9 个子系统 + v2 统一接口 + systemd driver，加起来比容器核心逻辑还多。这也解释了为什么 cgroups 管理是容器运行时里最复杂的部分。

---

## 二、为什么 nsenter 必须用 C

这是 runc 里最反直觉的设计。我们的 Go 运行时用 `cmd.SysProcAttr.Cloneflags` 就能创建 namespace，为什么 runc 要写一段 C 代码？

答案在 Go runtime 的 goroutine 调度器。

### Go 的 fork 问题

Go 程序是多线程的。`runtime.GOMAXPROCS` 默认等于 CPU 核数，所以一个 Go 程序通常有 4-8 个 OS 线程。

`clone()` 只复制调用线程，不复制其他线程。这意味着子进程里： - Go runtime 的调度器线程没了 - GC 线程没了 - 其他 goroutine 持有的锁可能永远不会释放

**在 fork 后、exec 前执行任何 Go 代码都是不安全的。**

但容器 init 进程需要在 fork 后做很多事情： - 加入 namespace（`setns()`） - 切换用户（`setuid()`/`setgid()`） - 设置 seccomp 过滤器 - 这些必须在 exec 用户命令之前完成

runc 的解决方案：用 CGo 的 `__attribute__((constructor))` 在 Go runtime 启动之前执行 C 代码。

```c
// nsenter/nsexec.c (简化版)
__attribute__((constructor)) static void nsexec(void) {
  // 在 Go runtime 初始化之前执行
  // 此时进程是单线程的，fork 是安全的

  int pipefd = getenv_int("_LIBCONTAINER_INITPIPE");
  if (pipefd == -1)
  return;  // 不是容器 init 进程，正常启动 Go

  // 读取父进程发来的 namespace 配置
  struct nlconfig_t config;
  read(pipefd, &config, sizeof(config));

  // clone() 进入新 namespace
  pid_t child = clone(child_func, stack,
  config.cloneflags | SIGCHLD, &config);

  // 等待 child 完成 namespace setup
  // 然后退出，让 Go runtime 在新 namespace 里启动
}
```

`__attribute__((constructor))` 让 `nsexec()` 在 `main()` 之前执行。如果环境变量 `_LIBCONTAINER_INITPIPE` 存在，说明这是一个容器 init 进程，执行 namespace 切换；否则正常启动 Go 程序。

这个机制值得展开说。GCC/Clang 的 `__attribute__((constructor))` 标记的函数会被链接器放入 ELF 的 `.init_array` 段，在 `_start` → `__libc_start_main` → `main` 链路中，`main()` 之前执行。Go 的 runtime 初始化（创建 M、启动 sysmon 等）也是在 `main()` 里。所以 constructor 函数跑的时候，进程还是纯粹的单线程状态——这正是 clone() 安全执行的前提。

runc 实际上做了**三次 clone**（parent → stage-1 → stage-2 → init），每次切换一部分 namespace。这种多级跳是为了处理 user namespace 的特殊情况：user namespace 必须最先创建，其他 namespace 才能以非特权身份创建。

这段 C 代码只有约 500 行，但它是整个 runc 里最关键的部分。

---

## 三、两阶段 init

runc 的容器创建不是一步完成的：

```
runc create
  │
  ├── 1. 父进程（runc）
  │  ├── 创建 pipe 用于父子通信
  │  ├── 设置环境变量 _LIBCONTAINER_INITPIPE
  │  └── exec /proc/self/exe init  (reexec)
  │
  ├── 2. Bootstrap init（C 代码，nsexec）
  │  ├── 读取 namespace 配置
  │  ├── clone() → 创建新 namespace
  │  ├── setns() → 加入已有 namespace
  │  ├── 设置 UID/GID 映射
  │  └── 通过 pipe 通知父进程
  │
  └── 3. Standard init（Go 代码）
  ├── 此时已在新 namespace 内
  ├── pivot_root
  ├── 挂载 /proc, /dev, /sys
  ├── 设置 seccomp
  ├── Drop capabilities
  ├── 关闭多余的 fd
  ├── 阻塞等待 start 信号
  └── exec 用户命令
```

两阶段的原因： - **Bootstrap**（C）：处理 namespace 和进程相关的操作（必须在单线程、Go runtime 启动前完成） - **Standard**（Go）：处理文件系统、安全、挂载等操作（可以安全使用 Go）

这里的 `exec /proc/self/exe init` 不是炫技，而是典型的 reexec 模式：父进程和子进程复用同一个二进制，但靠不同的 argv 和环境变量走不同代码路径。好处是不用再带一个额外 helper 程序；代价是你必须非常小心 `init` 这条内部入口，不要让它变成随手可调的后门。

---

## 四、exec fifo：create 和 start 的同步机制

OCI 规范要求 `create` 和 `start` 是两个独立命令。那 init 进程在 `create` 之后、`start` 之前怎么”暂停”？

runc 用一个 FIFO（命名管道）：

```go
// create 时
fifoPath := filepath.Join(stateDir, "exec.fifo")
syscall.Mkfifo(fifoPath, 0622)

// init 进程在 standard init 阶段末尾
// 打开 fifo 会阻塞，直到有人写入
fd, _ := unix.Open(fifoPath, unix.O_WRONLY|unix.O_CLOEXEC, 0)
// 阻塞在这里，等待 start 命令

// start 时
fd, _ := os.OpenFile(fifoPath, os.O_RDONLY, 0)
// 读取会解除 init 进程的阻塞
```

为什么用 FIFO 而不是 pipe？因为 pipe 需要父子进程关系，但 `runc create` 和 `runc start` 是两个独立进程。FIFO 是文件系统上的命名管道，任何进程都能打开。

---

## 五、我们漏掉了什么

对比 runc 和我们的 miniruntime：

  
|问题|miniruntime|runc|
|---|---|---|
|Go fork 安全|没处理|nsenter C 代码|
|容器进程继承了多余的 fd|没处理|`closeExecFrom()` 关闭所有非标准 fd|
|cgroup manager|直接写文件|支持 cgroupfs 和 systemd driver|
|seccomp|没有|完整的 seccomp-bpf 支持|
|AppArmor/SELinux|没有|支持|
|console/PTY|没处理|完整的 PTY 管理|
|rootfs propagation|硬编码 MS_PRIVATE|可配置|
|hooks|没有|createRuntime/prestart/poststart/poststop|
|错误回滚|基础清理|详细的 rollback 逻辑|

所谓 rollback 也不是简单 `rm -rf bundle/`。`create` 走到一半失败时，可能已经创建了 cgroup、挂上了 mount、写进了 state.json、开了 exec fifo、甚至把部分 fd 传给了 init 进程。生产级 runtime 必须按”创建顺序的逆序”回滚，否则留下来的不是脏目录，而是会影响后续容器启动的系统级残留。

最值得学习的几个：

### 1. 关闭多余的 fd

容器进程不应该继承父进程的文件描述符（可能包括 host 上的 socket、日志文件等）。runc 在 exec 用户命令前关闭所有 fd > 2（stdin/stdout/stderr）：

```go
func closeExecFrom(minFd int) error {
  fdDir, err := os.Open("/proc/self/fd")
  // 遍历所有 fd，关闭 > minFd 的
  for _, entry := range entries {
  fd, _ := strconv.Atoi(entry.Name())
  if fd > minFd {
  unix.Close(fd)
  }
  }
}
```

这不只是”防止信息泄漏”这么简单。否则容器可能继承宿主机监听 socket、日志 fd、匿名 memfd，最糟时会出现两类 bug：容器意外继续持有 host 资源，或者攻击者通过 `/proc/self/fd/*` 间接读写本不该看到的对象。

### 2. cgroup manager：cgroupfs vs systemd

runc 支持两种 cgroup 管理方式：

- **cgroupfs**：直接读写 `/sys/fs/cgroup` 文件系统（我们的做法）
- **systemd**：通过 systemd 的 D-Bus API 管理 cgroup

Kubernetes 推荐 systemd driver，因为 systemd 已经在管理 cgroup 树了。两个 manager 同时操作一棵树会冲突。

### 3. console/PTY 管理

`docker run -it` 需要一个伪终端（PTY）。runc 的 PTY 管理涉及： - 在 host 上创建 PTY master/slave pair（`posix_openpt()` + `grantpt()` + `unlockpt()`） - 把 slave 传给容器 init 进程 - init 进程调用 `setsid()` 创建新 session，然后 `ioctl(TIOCSCTTY)` 设置控制终端 - 把 slave 设为 stdin/stdout/stderr（`dup2(slave_fd, 0/1/2)`） - 通过 UNIX socket + `SCM_RIGHTS` 传递 PTY master fd 给 `runc` 进程

为什么要这么复杂？因为 PTY master 必须留在容器外——它是 `docker attach` 和 `kubectl exec` 的入口。而 slave 必须在容器内作为控制终端，这样 `Ctrl-C` 才能正确发送 SIGINT 给前台进程组。UNIX socket 传 fd 是唯一能跨 PID namespace 传递文件描述符的方式。

这是容器运行时里最容易出 bug 的部分之一。常见问题包括：窗口大小变化（`SIGWINCH`）没有同步到容器内、detach 后 master fd 泄漏、以及 slave 关闭顺序不对导致容器 init 收到 SIGHUP。

---

## 六、从 runc 学到的教训

1. **C 和 Go 的分工**：底层 namespace 操作用 C（因为 Go runtime 的限制），上层逻辑用 Go。不要在不合适的地方硬用一种语言。
    
2. **安全默认值**：关闭多余 fd、drop capabilities、seccomp 默认 profile——安全应该是默认行为，不是可选配置。
    
3. **两阶段 init 的价值**：把”必须在单线程完成”和”可以用高级语言完成”的操作分开，是优雅的工程决策。
    
4. **FIFO 同步是天才**：用文件系统上的命名管道解决两个独立进程的同步问题，简单、可靠、易于调试。
    
5. **cgroup 管理不是写几个文件那么简单**：systemd 集成、cgroup v1/v2 兼容、resource accounting——每一个都是一篇文章的复杂度。
    

---

## 七、系列回顾

12 篇文章，我们从零开始：

  
|篇目|主题|内核机制|
|---|---|---|
|[#01](https://quant67.com/post/containers/01-namespaces/namespaces.html)|Namespace 隔离|clone, unshare, setns|
|[#02](https://quant67.com/post/containers/02-netns/netns.html)|网络连接|veth, bridge, NAT|
|[#03](https://quant67.com/post/containers/03-rootfs/rootfs.html)|根文件系统|pivot_root, bind mount|
|[#04](https://quant67.com/post/containers/04-cgroups/cgroups.html)|资源限制|cgroups v2|
|[#05](https://quant67.com/post/containers/05-overlayfs/overlayfs.html)|分层镜像|OverlayFS|
|[#06](https://quant67.com/post/containers/06-mini-runtime/mini-runtime.html)|Go 运行时|reexec, pipe|
|[#07](https://quant67.com/post/containers/07-oci-spec/oci-spec.html)|OCI 规范|config.json, hooks|
|[#08](https://quant67.com/post/containers/08-security/security.html)|安全加固|seccomp-bpf, capabilities|
|[#09](https://quant67.com/post/containers/09-rootless/rootless.html)|Rootless|user namespace|
|[#10](https://quant67.com/post/containers/10-microvm/microvm.html)|microVM|KVM, virtio|
|[#11](https://quant67.com/post/containers/11-network-perf/network-perf.html)|网络性能|macvlan, eBPF, XDP|
|[#12](https://quant67.com/post/containers/12-runc-source/runc-source.html)|源码考古|runc, libcontainer|

容器不是魔法。它是一堆内核原语的组合。理解了这些原语，你就能理解从 Docker 到 Kubernetes 的整个生态。

## 相关阅读

- [Go 调度器深度拆解](https://quant67.com/post/go/scheduler/scheduler.html) — Go runtime 的多线程模型，直接导致了 nsenter 必须用 C
- [Raft 实现拆解：etcd 的共识算法](https://quant67.com/post/distributed/raft-etcd/raft-etcd.html) — 另一个”拆解工业级实现”的文章
- [用 Rust 重写 C 网络服务器](https://quant67.com/post/rust/rewrite-c-server/rewrite-c-server.html) — 如果用 Rust 写容器运行时（youki），fork 问题就不存在

## 同主题继续阅读

把当前热点继续串成多页阅读，而不是停在单篇消费。

2026-04-07 · linux / containers

### [【从零造容器】OCI 规范兼容：让迷你运行时说标准语言](https://quant67.com/post/containers/07-oci-spec/oci-spec.html)

我们的迷你容器运行时能跑了，但没人能用它——因为 containerd、Kubernetes 不认识它。OCI Runtime Spec 就是容器世界的通用语言。本文拆解规范的每个关键字段，把迷你运行时改造成 containerd 能调用的标准运行时。

2026-04-06 · linux / containers

### [【从零造容器】用 Go 组装迷你容器运行时：把积木拼起来](https://quant67.com/post/containers/06-mini-runtime/mini-runtime.html)

五篇文章攒了一堆内核积木：namespace、netns、rootfs、cgroup、overlayfs。现在是时候用 Go 把它们拼成一个能跑的容器运行时了。不到 500 行代码，create/start/exec/kill/delete，五个命令走完容器的一生。

2026-04-01 · linux / containers

### [【从零造容器】Linux Namespaces：用 50 行 C 隔离一个进程](https://quant67.com/post/containers/01-namespaces/namespaces.html)

容器不是魔法。它就是几个系统调用。本文用 C 从 clone() 开始，逐个开启 PID/UTS/Mount/IPC namespace，看隔离到底是怎么回事。50 行代码，你就拥有了一个'容器'的雏形。

2026-04-01 · linux / containers

### [【从零造容器】Network Namespace：给你的进程接上虚拟网线](https://quant67.com/post/containers/02-netns/netns.html)

上一篇我们用 clone() 隔离了 PID、主机名和挂载点，但那个'容器'连 lo 都 ping 不通。本文从 CLONE_NEWNET 出发，用 veth pair + bridge + iptables MASQUERADE，一步步给容器接上网。