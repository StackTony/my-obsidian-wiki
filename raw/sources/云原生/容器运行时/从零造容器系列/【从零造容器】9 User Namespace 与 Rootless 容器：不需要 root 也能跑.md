到目前为止，本系列所有示例代码的第一步都是 `sudo`。创建 namespace 需要 `CAP_SYS_ADMIN`，配置 cgroup 需要写 `/sys/fs/cgroup`，挂载 overlayfs 需要 root。

但你想过没有：为什么运行一个 “隔离的进程” 需要最高权限？这就像让银行保安先拿到金库钥匙才能锁门。

User namespace 是解决这个矛盾的关键。它让一个普通用户可以在**自己的 namespace 里成为 root**，同时在宿主机上仍然是普通用户。Podman 的整个 rootless 架构就建立在这个机制上。

> 本文代码在 `examples/containers/09-rootless/`。

---

`CLONE_NEWUSER` 是唯一一个**不需要特权**就能创建的 namespace。普通用户可以：

```
// 普通用户就能执行！
unshare(CLONE_NEWUSER);
```

创建 user namespace 后，进程在新 namespace 里的 UID/GID 是 `65534`（nobody），因为还没有建立映射。需要写 `/proc/PID/uid_map` 和 `/proc/PID/gid_map` 来建立映射：

```
# 把容器内的 UID 0 映射到宿主机的 UID 1000（当前用户）
echo "0 1000 1" > /proc/$PID/uid_map

# 格式：容器内起始UID  宿主机起始UID  映射范围
# "0 1000 1" 表示：容器内 UID 0 = 宿主机 UID 1000，只映射 1 个 UID
```

映射建立后，容器内的进程看到自己是 root（UID 0），但宿主机上它实际是 UID 1000。

### 用 C 实现

```c
#define _GNU_SOURCE
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/wait.h>

static int child_fn(void *arg) {
  (void)arg;
  printf("In user namespace:\n");
  printf("  UID: %d (should be 0)\n", getuid());
  printf("  GID: %d (should be 0)\n", getgid());

  // 现在我们在容器内"是 root"
  // 可以创建其他 namespace 了！
  if (unshare(CLONE_NEWNS | CLONE_NEWPID) == -1) {
  perror("unshare");
  return 1;
  }

  printf("  Created mount + PID namespace as 'root'\n");
  return 0;
}

int main(void) {
  char stack[65536];

  pid_t pid = clone(child_fn, stack + sizeof(stack),
  CLONE_NEWUSER | SIGCHLD, NULL);
  if (pid == -1) { perror("clone"); return 1; }

  // 设置 UID 映射：容器 UID 0 → 宿主机当前 UID
  char path[64], map[64];
  snprintf(path, sizeof(path), "/proc/%d/uid_map", pid);
  snprintf(map, sizeof(map), "0 %d 1\n", getuid());
  FILE *f = fopen(path, "w");
  fprintf(f, "%s", map);
  fclose(f);

  // 必须先写 "deny" 到 setgroups 才能写 gid_map
  snprintf(path, sizeof(path), "/proc/%d/setgroups", pid);
  f = fopen(path, "w");
  fprintf(f, "deny\n");
  fclose(f);

  // 这不是语法怪癖，而是安全要求：必须先禁用 setgroups()
  // 否则进程可以先构造额外组 ID，再写 gid_map，绕过文件权限模型

  snprintf(path, sizeof(path), "/proc/%d/gid_map", pid);
  snprintf(map, sizeof(map), "0 %d 1\n", getgid());
  f = fopen(path, "w");
  fprintf(f, "%s", map);
  fclose(f);

  waitpid(pid, NULL, 0);
  return 0;
}
```

**不需要 sudo。** 普通用户就能运行。

---

## 二、多 UID 映射与 newuidmap

映射单个 UID 够用吗？不够。容器内如果要运行多个用户（比如 `nobody`、`www-data`），需要映射多个 UID。

但 `/proc/PID/uid_map` 的写入有安全限制：非特权进程只能映射自己的 UID。要映射多个 UID，需要 `newuidmap`（一个 setuid 程序）和 `/etc/subuid` 配置：

```
# /etc/subuid — 允许 ubuntu 用户使用的附属 UID 范围
ubuntu:100000:65536

# 意思是：用户 ubuntu 可以使用 UID 100000-165535
```

```
# 映射容器 UID 0 → 宿主机 UID 1000（我自己）
# 映射容器 UID 1-65535 → 宿主机 UID 100000-165535
newuidmap $PID 0 1000 1 1 100000 65536
```

Podman 会自动读取 `/etc/subuid` 并调用 `newuidmap`。

> **subuid/subgid 管理要点**：每个用户的范围不能重叠。如果 `ubuntu` 用户占了 100000-165535，那 `deploy` 用户必须从 165536 开始。`useradd` 在支持的发行版上会自动分配范围。手动管理时记得同时更新 `/etc/subuid` 和 `/etc/subgid`——忘记 subgid 是最常见的”rootless 容器起不来”原因之一。

---

## 三、Rootless 的限制

User namespace 不是万能的。rootless 容器有很多限制：

### 1. 网络

没有 root 就不能创建 veth pair 和 bridge。rootless 容器的网络用 **slirp4netns** — 一个用户态网络栈：

```
┌──────────────────┐  ┌───────────────────┐
│  Container netns │  │  Host namespace  │
│  │  │  │
│  tap0 ←──────── slirp4netns ──→ socket  │
│  10.0.2.100  │  │  │
└──────────────────┘  └───────────────────┘
```

slirp4netns 通过 tap 设备把容器的网络包转发到用户态，再通过普通 socket 发到网络。性能比 veth 差很多（经过用户态拷贝），但不需要任何特权。

粗略数据对比：

|方案|TCP 吞吐|P99 延迟|
|---|---|---|
|veth + bridge (root)|~7.5 Gbps|~185μs|
|slirp4netns|~2.5 Gbps|~800μs|
|pasta (Podman 4.0+)|~5.0 Gbps|~300μs|

slirp4netns 比 veth 慢约 3 倍，因为每个包都要经过用户态拷贝。pasta 通过共享宿主机网络栈（类似 macvlan）避免了拷贝，性能显著改善。

Podman 4.0+ 也支持 **pasta**（Plug A Simple Tap Abstraction），性能比 slirp4netns 好，是目前 rootless 网络的推荐方案。

### 2. 不能绑定低端口

非 root 不能绑定 1024 以下的端口。rootless 容器里 `nginx` 不能监听 80 端口（除非设置 `net.ipv4.ip_unprivileged_port_start=0`）。

### 3. OverlayFS 限制

在某些内核版本（< 5.11）上，rootless 容器不能使用 OverlayFS（因为 mount 需要 `CAP_SYS_ADMIN`）。Podman 退而求其次用 **fuse-overlayfs** — 用户态的 FUSE 实现。5.11+ 内核支持在 user namespace 里挂载 overlay。

### 4. Cgroup 限制

Cgroup v2 支持 delegation（把子树交给非特权用户管理），但 v1 不支持。rootless 容器在 v1 系统上没有资源限制能力。

---

## 四、Podman：rootless 容器的标杆

Podman 是 rootless 容器的标杆实现。它的架构：

```
podman run alpine sh
  │
  ├── 检查是否 root
  │  ├── 是 → 直接用 runc/crun
  │  └── 否 → rootless 模式
  │  ├── 1. 创建 user namespace（newuidmap/newgidmap）
  │  ├── 2. 在 user namespace 内创建其他 namespace
  │  ├── 3. 网络：slirp4netns / pasta
  │  ├── 4. 存储：fuse-overlayfs / kernel overlay (5.11+)
  │  ├── 5. Cgroup：delegation (v2 only)
  │  └── 6. 调用 crun（C 实现，比 runc 快）
```

Podman 默认用 crun 而不是 runc，因为 crun 是 C 实现，启动速度更快，rootless 支持更好。

Docker 也支持 user namespace，但默认思路不同。`--userns-remap` 更像是”rootful daemon + remapped container UID”：容器内的 root 被映射走了，但 Docker daemon 本身仍然是 root。Podman 的 rootless 则是”从 CLI 到 runtime 整条链路都尽量不拿 root”。两者都减少了容器内 root 的危险性，但威胁模型不一样。

---

## 五、安全边界：User Namespace 真的安全吗？

User namespace 的设计目标是让非特权用户安全地使用内核隔离功能。但历史告诉我们：

- **CVE-2022-0185** — user namespace 里创建的文件系统可以触发内核堆溢出
- **CVE-2023-32233** — Netfilter 在 user namespace 里的 use-after-free
- **CVE-2023-2163** — eBPF 验证器在 user namespace 里的逃逸

这些漏洞的共同点：user namespace 让非特权用户能访问**更多的内核攻击面**（mount、netfilter、eBPF）。

所以有些发行版默认禁用非特权 user namespace（Debian 早期版本），或者限制可用的 namespace 数量。这是一个安全性和易用性的权衡。

---

## 六、我们的 miniruntime 怎么加 rootless 支持？

核心改造：

1. 先创建 user namespace（`CLONE_NEWUSER`）
2. 设置 UID/GID 映射
3. **在 user namespace 内**创建其他 namespace

```
cmd.SysProcAttr = &syscall.SysProcAttr{
  Cloneflags: syscall.CLONE_NEWUSER |
  syscall.CLONE_NEWPID |
  syscall.CLONE_NEWUTS |
  syscall.CLONE_NEWNS |
  syscall.CLONE_NEWIPC,
  UidMappings: []syscall.SysProcIDMap{
  {ContainerID: 0, HostID: os.Getuid(), Size: 1},
  },
  GidMappings: []syscall.SysProcIDMap{
  {ContainerID: 0, HostID: os.Getgid(), Size: 1},
  },
}
```

Go 的 `SysProcAttr` 直接支持 UID/GID 映射，比 C 简洁得多。

但网络和存储需要单独处理 — 这就是为什么 rootless 容器运行时比 rootful 复杂得多。

## 八、常见踩坑

  
|症状|原因|解决方法|
|---|---|---|
|`ERRO[0000] cannot find newuidmap`|没安装 `uidmap` 包|`apt install uidmap` 或 `dnf install shadow-utils`|
|`Error: OCI permission denied`|`/etc/subuid` 里没有当前用户|`usermod --add-subuids 100000-165535 $USER`|
|容器启动极慢|fuse-overlayfs 在 I/O 密集场景性能差|升级到 Linux 5.11+ 使用原生 overlay|
|`Error: network slirp4netns: ...`|slirp4netns 未安装|`apt install slirp4netns`|
|`crun: writing to cgroup: Permission denied`|Cgroups v1 不支持 delegation|迁移到 cgroups v2|

下一篇我们跳出容器，看看它的竞争对手 — [容器 vs microVM：Firecracker 凭什么 125ms 启动](https://quant67.com/post/containers/10-microvm/microvm.html)。

## 相关阅读

- [Seccomp-BPF 与 Capabilities](https://quant67.com/post/containers/08-security/security.html) — 容器安全的另一面
- [eBPF：Linux 内核的隐藏武器](https://quant67.com/post/linux/ebpf/ebpf.html) — user namespace 里的 eBPF 是攻击面之一
- [密码学工程中最容易犯的 7 个错误](https://quant67.com/post/crypt/crypto-engineering-mistakes/crypto-engineering-mistakes.html) — 安全永远是多层防御

## 同主题继续阅读

把当前热点继续串成多页阅读，而不是停在单篇消费。

2026-04-08 · linux / containers

### [【从零造容器】Seccomp-BPF 与 Capabilities：容器安全的两道防线](https://quant67.com/post/containers/08-security/security.html)

你的容器能调用 reboot()。是的，现在就能。除非有人拦住它。Capabilities 拆分 root 权限，Seccomp-BPF 过滤系统调用——两道防线，缺一不可。本文用 C 代码拆解这两套机制，看看 Docker 到底替你挡住了什么。

2026-05-10 · linux / security

### [【eBPF 系列】eBPF 安全监控：不改内核也能审计 syscall](https://quant67.com/post/linux/ebpf-security/ebpf-security.html)

Seccomp 只能说 yes or no，但攻击者早就学会了在 yes 里面做文章。是时候让 eBPF 接管安全审计了。

2026-04-01 · linux / containers

### [【从零造容器】Linux Namespaces：用 50 行 C 隔离一个进程](https://quant67.com/post/containers/01-namespaces/namespaces.html)

容器不是魔法。它就是几个系统调用。本文用 C 从 clone() 开始，逐个开启 PID/UTS/Mount/IPC namespace，看隔离到底是怎么回事。50 行代码，你就拥有了一个'容器'的雏形。

2026-04-01 · linux / containers

### [【从零造容器】Network Namespace：给你的进程接上虚拟网线](https://quant67.com/post/containers/02-netns/netns.html)

上一篇我们用 clone() 隔离了 PID、主机名和挂载点，但那个'容器'连 lo 都 ping 不通。本文从 CLONE_NEWNET 出发，用 veth pair + bridge + iptables MASQUERADE，一步步给容器接上网。