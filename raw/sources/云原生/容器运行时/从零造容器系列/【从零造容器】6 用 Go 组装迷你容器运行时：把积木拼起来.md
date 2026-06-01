前五篇文章，我们用 C 和 shell 一个一个地拆解了容器的内核积木：

- [Namespace 隔离](https://quant67.com/post/containers/01-namespaces/namespaces.html)
- [网络连接](https://quant67.com/post/containers/02-netns/netns.html)
- [根文件系统](https://quant67.com/post/containers/03-rootfs/rootfs.html)
- [资源限制](https://quant67.com/post/containers/04-cgroups/cgroups.html)
- [分层镜像](https://quant67.com/post/containers/05-overlayfs/overlayfs.html)

现在，把它们拼起来。用 Go。

为什么用 Go？因为容器生态几乎全是 Go 写的 — Docker、containerd、runc、Podman、CRI-O。Go 的 `syscall` 和 `golang.org/x/sys/unix` 包提供了我们需要的所有系统调用封装。更重要的是，Go 的 `/proc/self/exe` reexec 技巧让容器 init 进程的实现优雅得多。

> 完整代码在 `examples/containers/06-mini-runtime/`，`go build` 即可编译。

---

## 一、容器运行时的职责

一个最小的容器运行时需要做什么？

```
miniruntime create <container-id> <rootfs>
miniruntime start <container-id>
miniruntime exec <container-id> <command>
miniruntime kill <container-id> <signal>
miniruntime delete <container-id>
```

五个命令，对应容器的完整生命周期：

1. **create** — 准备 namespace、cgroup、rootfs，但不启动进程
2. **start** — 在准备好的环境中启动容器 init 进程
3. **exec** — 在已运行的容器中执行命令（类似 `docker exec`）
4. **kill** — 给容器进程发送信号
5. **delete** — 清理所有资源

---

## 二、/proc/self/exe 与 reexec 技巧

容器运行时面临一个鸡生蛋的问题：

1. 我们需要在新 namespace 里执行 `pivot_root`、挂载 `/proc` 等初始化操作
2. 这些操作必须在子进程里做（因为 namespace 是子进程的）
3. 但子进程的代码和父进程是同一个二进制文件

解决方案是 **reexec**：父进程 `clone()` 创建子进程后，子进程重新执行自己（`/proc/self/exe`），但传入一个特殊参数（比如 `init`），告诉自己现在是容器 init 进程，应该执行初始化逻辑。

```go
package main

import ("os"
  "os/exec"
  "syscall")

func main() {
  switch os.Args[1] {
  case "run":
  // 父进程：创建子进程并进入新 namespace
  run()
  case "init":
  // 子进程：在新 namespace 里执行初始化
  initContainer()
  }
}

func run() {
  // 重新执行自己，但参数改为 "init"
  cmd := exec.Command("/proc/self/exe", "init")
  cmd.SysProcAttr = &syscall.SysProcAttr{
  Cloneflags: syscall.CLONE_NEWPID |
  syscall.CLONE_NEWUTS |
  syscall.CLONE_NEWNS |
  syscall.CLONE_NEWIPC,
  }
  cmd.Stdin = os.Stdin
  cmd.Stdout = os.Stdout
  cmd.Stderr = os.Stderr
  cmd.Run()
}

func initContainer() {
  // 此时已经在新 namespace 里了
  // 执行 pivot_root、挂载 /proc 等
  setupRootfs()
  setupProc()

  // 最后 exec 用户指定的命令
  syscall.Exec("/bin/sh", []string{"/bin/sh"}, os.Environ())
}
```

这个技巧在 runc 里叫 `nsexec`，是容器运行时的核心模式。

---

## 三、容器状态管理

每个容器需要持久化一些状态信息，这样 `kill` 和 `delete` 命令才能找到它：

```go
type ContainerState struct {
  ID  string `json:"id"`
  PID  int  `json:"pid"`
  Status  string `json:"status"` // created, running, stopped
  Rootfs  string `json:"rootfs"`
  CgroupDir string `json:"cgroup_dir"`
  CreatedAt string `json:"created_at"`
}
```

状态文件存在 `/run/miniruntime/<container-id>/state.json`。

```go
const stateDir = "/run/miniruntime"

func saveState(state *ContainerState) error {
  dir := filepath.Join(stateDir, state.ID)
  os.MkdirAll(dir, 0700)

  data, _ := json.MarshalIndent(state, "", "  ")
  return os.WriteFile(filepath.Join(dir, "state.json"), data, 0600)
}

func loadState(id string) (*ContainerState, error) {
  path := filepath.Join(stateDir, id, "state.json")
  data, err := os.ReadFile(path)
  if err != nil {
  return nil, fmt.Errorf("container %s not found", id)
  }
  var state ContainerState
  json.Unmarshal(data, &state)
  return &state, nil
}
```

---

## 四、Cgroup 设置

把前面 C 代码里的 cgroup 操作翻译成 Go：

```go
func setupCgroup(id string, memLimit, cpuQuota string) (string, error) {
  cgroupPath := filepath.Join("/sys/fs/cgroup", "miniruntime-"+id)

  if err := os.MkdirAll(cgroupPath, 0755); err != nil {
  return "", fmt.Errorf("create cgroup: %w", err)
  }

  // 设置内存限制
  if memLimit != "" {
  if err := os.WriteFile(filepath.Join(cgroupPath, "memory.max"),
  []byte(memLimit), 0644); err != nil {
  return "", fmt.Errorf("set memory.max: %w", err)
  }
  }

  // 设置 CPU 限制
  if cpuQuota != "" {
  if err := os.WriteFile(filepath.Join(cgroupPath, "cpu.max"),
  []byte(cpuQuota), 0644); err != nil {
  return "", fmt.Errorf("set cpu.max: %w", err)
  }
  }

  return cgroupPath, nil
}

func addToCgroup(cgroupPath string, pid int) error {
  return os.WriteFile(filepath.Join(cgroupPath, "cgroup.procs"),
  []byte(fmt.Sprintf("%d", pid)), 0644)
}

func removeCgroup(cgroupPath string) error {
  return os.Remove(cgroupPath)
}
```

---

## 五、Rootfs 与 pivot_root

在 Go 里实现 `pivot_root`：

```go
func setupRootfs(rootfs string) error {
  // 切断挂载传播
  if err := syscall.Mount("", "/", "", syscall.MS_PRIVATE|syscall.MS_REC, ""); err != nil {
  return fmt.Errorf("mount private: %w", err)
  }

  // 把 rootfs bind mount 到自己（pivot_root 要求 new_root 是挂载点）
  if err := syscall.Mount(rootfs, rootfs, "", syscall.MS_BIND|syscall.MS_REC, ""); err != nil {
  return fmt.Errorf("bind mount rootfs: %w", err)
  }

  // 创建 old_root 挂载点
  oldRoot := filepath.Join(rootfs, ".old_root")
  os.MkdirAll(oldRoot, 0700)

  // pivot_root
  if err := syscall.PivotRoot(rootfs, oldRoot); err != nil {
  return fmt.Errorf("pivot_root: %w", err)
  }

  // 切换到新根目录
  os.Chdir("/")

  // 挂载 /proc
  os.MkdirAll("/proc", 0755)
  syscall.Mount("proc", "/proc", "proc", 0, "")

  // 挂载 /dev (最小化)
  os.MkdirAll("/dev", 0755)
  syscall.Mount("tmpfs", "/dev", "tmpfs", syscall.MS_NOSUID|syscall.MS_STRICTATIME, "mode=755")

  // 卸载 old_root
  syscall.Unmount("/.old_root", syscall.MNT_DETACH)
  os.Remove("/.old_root")

  return nil
}
```

这段代码浓缩了 [#03 根文件系统](https://quant67.com/post/containers/03-rootfs/rootfs.html) 整篇文章的核心操作。

---

## 六、网络设置

网络配置比其他部分复杂，因为需要在宿主机和容器两侧同时操作。我们用 `ip` 命令简化：

```go
func setupNetwork(pid int, containerIP, bridgeIP string) error {
  vethHost := "veth-host"
  vethContainer := "veth-ct"

  cmds := [][]string{
  // 创建 veth pair
  {"ip", "link", "add", vethHost, "type", "veth", "peer", "name", vethContainer},
  // 把一端移入容器 netns
  {"ip", "link", "set", vethContainer, "netns", fmt.Sprintf("%d", pid)},
  // 宿主机端配置
  {"ip", "addr", "add", bridgeIP + "/24", "dev", vethHost},
  {"ip", "link", "set", vethHost, "up"},
  // 启用 IP 转发
  {"sysctl", "-w", "net.ipv4.ip_forward=1"},
  // NAT
  {"iptables", "-t", "nat", "-A", "POSTROUTING", "-s",
  containerIP + "/24", "-j", "MASQUERADE"},
  }

  for _, args := range cmds {
  cmd := exec.Command(args[0], args[1:]...)
  if out, err := cmd.CombinedOutput(); err != nil {
  return fmt.Errorf("%s: %s: %w", args[0], string(out), err)
  }
  }
  return nil
}
```

容器内部的网络配置在 init 进程里完成（因为需要在容器的 netns 里操作）。

---

## 七、错误处理与资源清理

容器创建是一个多步骤过程，任何一步失败都需要回滚之前的操作。这是容器运行时最容易出 bug 的地方 — namespace 泄漏、cgroup 残留、挂载点残留都是常见问题。

以 cgroup 为例：如果你的 runtime 在创建 cgroup 后、启动容器前崩溃了，那个 cgroup 目录会永远留在 `/sys/fs/cgroup` 下面。挂载点残留更危险 — `pivot_root` 失败但 bind mount 已完成，宿主机的文件系统上会多出”幽灵挂载点”，`mount | wc -l` 会越来越大。

```go
type Cleanup struct {
  steps []func()
}

func (c *Cleanup) Add(fn func()) {
  c.steps = append(c.steps, fn)
}

func (c *Cleanup) Run() {
  // 逆序执行清理
  for i := len(c.steps) - 1; i >= 0; i-- {
  c.steps[i]()
  }
}

func createContainer(id, rootfs string) error {
  cleanup := &Cleanup{}
  defer func() {
  // 只在出错时执行清理
  // 成功的话清理由 delete 命令负责
  }()

  // Step 1: 创建 cgroup
  cgroupPath, err := setupCgroup(id, "256m", "50000 100000")
  if err != nil {
  return err
  }
  cleanup.Add(func() { removeCgroup(cgroupPath) })

  // Step 2: 准备 rootfs overlay
  // ...

  // Step 3: 创建子进程
  // ...

  return nil
}
```

runc 在这方面做得很好 — 它用了一个两阶段的 init 进程设计：第一个 init 进程做 setup，成功后通过 pipe 通知父进程，然后 exec 成用户进程。如果 setup 失败，父进程能得到错误信息并清理。

---

## 八、完整的 create/start 流程

把所有部分串起来：

```
miniruntime create mycontainer /path/to/rootfs
  │
  ├── 1. 创建 cgroup
  ├── 2. 准备 OverlayFS (upper + work + merged)
  ├── 3. clone() 创建子进程（新 namespace）
  │  子进程：
  │  ├── /proc/self/exe init（reexec）
  │  ├── pivot_root 到 rootfs
  │  ├── 挂载 /proc, /dev, /sys
  │  ├── 阻塞等待 start 信号（通过 pipe）
  │  └── 收到信号后 exec 用户命令
  ├── 4. 父进程把子进程 PID 加入 cgroup
  ├── 5. 配置网络（veth + bridge）
  └── 6. 保存状态到 state.json

miniruntime start mycontainer
  │
  ├── 1. 读取 state.json
  ├── 2. 通过 pipe 发送 start 信号给 init 进程
  └── 3. 更新状态为 "running"
```

create 和 start 分开不只是 OCI 规范的形式要求。编排系统会利用这段空档做很多事：把进程放进正确的 cgroup、补挂卷、注入 seccomp profile、配网络、甚至在某些场景下先 checkpoint 再恢复。换句话说，`create` 解决的是”把容器壳子搭好”，`start` 才是”真的让业务代码跑起来”。

如果 `create` 之后永远没有 `start`，容器会一直停在 `created` 状态，占着 cgroup、overlay mount 和 state 目录。生产级 runtime 一般会有一个 GC：扫描 `/run/miniruntime/*/state.json`，把长时间未启动的容器当作异常中断清理掉。

---

## 九、我们的运行时 vs runc

|特性|miniruntime|runc|
|---|---|---|
|Namespace 隔离|PID + UTS + Mount + IPC + Net|全部 8 种|
|Cgroup|v2 基础限制|v1 + v2，systemd driver|
|Rootfs|手工 pivot_root|libcontainer，支持多种 rootfs|
|网络|简单 veth + bridge|不管网络（交给 CNI）|
|安全|无|Seccomp + Capabilities + AppArmor/SELinux|
|OCI 兼容|部分|完全|
|代码量|~500 行|~15,000 行|

差距是巨大的。但核心思路是一样的：**namespace + cgroup + rootfs + pivot_root**。runc 多出来的代码大部分在处理边界情况和安全加固。

下一篇，我们让这个运行时理解 OCI 规范 — [#07 OCI 规范兼容](https://quant67.com/post/containers/07-oci-spec/oci-spec.html)。有了 OCI 兼容，containerd 和 Kubernetes 就能调用我们的运行时了。最后在 [#12 runc 源码考古](https://quant67.com/post/containers/12-runc-source/runc-source.html) 里，你会看到 runc 如何用 nsenter C 代码解决 Go runtime fork 不安全的问题 — 那是本系列最”反直觉”的工程决策。

---

## 相关阅读

- [Go 调度器深度拆解](https://quant67.com/post/go/scheduler/scheduler.html) — Go runtime fork 的陷阱，与容器运行时直接相关
- [Rust 所有权系统](https://quant67.com/post/rust/ownership-vs-raii/ownership-vs-raii.html) — 如果用 Rust 写容器运行时，资源清理会优雅得多
- [eBPF：Linux 内核的隐藏武器](https://quant67.com/post/linux/ebpf/ebpf.html) — 容器安全的下一层防线

## 同主题继续阅读

把当前热点继续串成多页阅读，而不是停在单篇消费。

2026-04-07 · linux / containers

### [【从零造容器】OCI 规范兼容：让迷你运行时说标准语言](https://quant67.com/post/containers/07-oci-spec/oci-spec.html)

我们的迷你容器运行时能跑了，但没人能用它——因为 containerd、Kubernetes 不认识它。OCI Runtime Spec 就是容器世界的通用语言。本文拆解规范的每个关键字段，把迷你运行时改造成 containerd 能调用的标准运行时。

2026-04-12 · linux / containers

### [【从零造容器】runc 源码考古：OCI 参考实现到底长什么样](https://quant67.com/post/containers/12-runc-source/runc-source.html)

我们的迷你运行时有 500 行，runc 有 15000 行。多出来的代码在干什么？本文拆解 runc 的核心流程：从 runc create 到容器 init 进程，libcontainer 的设计，nsenter 里那段神秘的 C 代码，以及 Go runtime fork 的天坑。

2026-04-01 · linux / containers

### [【从零造容器】Linux Namespaces：用 50 行 C 隔离一个进程](https://quant67.com/post/containers/01-namespaces/namespaces.html)

容器不是魔法。它就是几个系统调用。本文用 C 从 clone() 开始，逐个开启 PID/UTS/Mount/IPC namespace，看隔离到底是怎么回事。50 行代码，你就拥有了一个'容器'的雏形。

2026-04-01 · linux / containers

### [【从零造容器】Network Namespace：给你的进程接上虚拟网线](https://quant67.com/post/containers/02-netns/netns.html)

上一篇我们用 clone() 隔离了 PID、主机名和挂载点，但那个'容器'连 lo 都 ping 不通。本文从 CLONE_NEWNET 出发，用 veth pair + bridge + iptables MASQUERADE，一步步给容器接上网。