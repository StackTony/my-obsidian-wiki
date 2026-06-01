上一篇我们用 Go 拼出了一个能跑的迷你容器运行时。但它有个致命问题：**只有我们自己能用它**。

containerd 不认识它。Kubernetes 不认识它。`docker run` 背后调的是 runc，不是我们的 miniruntime。

这不是因为我们的运行时功能不够，而是因为它不说”标准语言”。这个标准语言就是 [OCI Runtime Specification](https://github.com/opencontainers/runtime-spec)。

本文的目标：**把 miniruntime 改造成 OCI 兼容的运行时，让 `ctr`（containerd 的 CLI）能直接调用它**。

---

## 一、OCI 是什么：容器世界的 USB 接口

OCI（Open Container Initiative）定义了两个规范：

1. **Image Spec** — 容器镜像的格式（layer、manifest、config）
2. **Runtime Spec** — 容器运行时的行为（怎么创建、启动、停止容器）

我们关心的是 Runtime Spec。它定义了：

- 容器的配置格式（`config.json`）
- 运行时必须实现的命令（create、start、state、kill、delete）
- 容器的生命周期状态机
- 运行时与外部工具的交互方式（hooks）

任何实现了这个规范的程序，都可以被 containerd/CRI-O 作为底层运行时使用。runc 是参考实现，但 crun（C 实现）、youki（Rust 实现）、kata-containers（microVM 实现）都遵循同一个规范。

---

## 二、config.json：容器的蓝图

OCI 规范的核心是 `config.json`，描述了创建容器需要的一切信息。来看一个最小版本：

```
{
  "ociVersion": "1.0.2",
  "process": {
  "terminal": true,
  "user": { "uid": 0, "gid": 0 },
  "args": ["/bin/sh"],
  "env": [
  "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
  "TERM=xterm"
  ],
  "cwd": "/"
  },
  "root": {
  "path": "rootfs",
  "readonly": false
  },
  "hostname": "minicontainer",
  "mounts": [
  {
  "destination": "/proc",
  "type": "proc",
  "source": "proc"
  },
  {
  "destination": "/dev",
  "type": "tmpfs",
  "source": "tmpfs",
  "options": ["nosuid", "strictatime", "mode=755", "size=65536k"]
  },
  {
  "destination": "/sys",
  "type": "sysfs",
  "source": "sysfs",
  "options": ["nosuid", "noexec", "nodev", "ro"]
  }
  ],
  "linux": {
  "namespaces": [
  { "type": "pid" },
  { "type": "ipc" },
  { "type": "uts" },
  { "type": "mount" },
  { "type": "network" }
  ],
  "resources": {
  "memory": { "limit": 268435456 },
  "cpu": { "quota": 50000, "period": 100000 }
  }
  }
}
```

### 关键字段

  
|字段|含义|MUST/SHOULD|
|---|---|---|
|`ociVersion`|规范版本|MUST|
|`process.args`|容器启动命令|MUST|
|`root.path`|根文件系统路径（相对于 bundle 目录）|MUST|
|`hostname`|容器主机名|SHOULD|
|`mounts`|挂载点列表|SHOULD|
|`linux.namespaces`|要创建的 namespace 列表|MUST|
|`linux.resources`|cgroup 资源限制|SHOULD|
|`linux.uidMappings` / `linux.gidMappings`|rootless 的 UID/GID 映射|SHOULD|
|`linux.rootfsPropagation`|挂载传播语义|SHOULD|

---

rootless bundle 最小会长这样：

```
"linux": {
  "uidMappings": [
    { "containerID": 0, "hostID": 1000, "size": 1 },
    { "containerID": 1, "hostID": 100000, "size": 65536 }
  ],
  "gidMappings": [
    { "containerID": 0, "hostID": 1000, "size": 1 },
    { "containerID": 1, "hostID": 100000, "size": 65536 }
  ]
}
```

容器里的 root 只是映射后的 root，不是宿主机 root。这两个字段看起来不起眼，但没有它们，rootless 就不成立。

OCI Runtime Spec 要求运行时实现以下命令：

### create

```
miniruntime create <container-id> --bundle <path-to-bundle>
```

bundle 目录包含 `config.json` 和 `rootfs/`。create 命令必须： 1. 读取 `config.json` 2. 创建 namespace、cgroup 3. 准备 rootfs 4. 启动 init 进程但**不执行 `process.args`**（init 进程阻塞等待 start 信号）

### start

```
miniruntime start <container-id>
```

通知 init 进程开始执行 `process.args`。

### state

```
miniruntime state <container-id>
```

输出 JSON 格式的容器状态：

```
{
  "ociVersion": "1.0.2",
  "id": "mycontainer",
  "status": "running",
  "pid": 12345,
  "bundle": "/path/to/bundle"
}
```

### kill

```
miniruntime kill <container-id> SIGTERM
```

### delete

```
miniruntime delete <container-id>
```

---

## 四、Go 实现：解析 config.json

```go
type OCISpec struct {
  Version  string  `json:"ociVersion"`
  Process  OCIProcess  `json:"process"`
  Root  OCIRoot  `json:"root"`
  Hostname string  `json:"hostname"`
  Mounts  []OCIMount  `json:"mounts"`
  Linux  OCILinux  `json:"linux"`
  Hooks  *OCIHooks  `json:"hooks,omitempty"`
}

type OCIProcess struct {
  Terminal bool  `json:"terminal"`
  User  OCIUser  `json:"user"`
  Args  []string `json:"args"`
  Env  []string `json:"env"`
  Cwd  string  `json:"cwd"`
}

type OCIRoot struct {
  Path  string `json:"path"`
  Readonly bool  `json:"readonly"`
}

type OCILinux struct {
  Namespaces []OCINamespace `json:"namespaces"`
  Resources  *OCIResources  `json:"resources,omitempty"`
}

func loadSpec(bundlePath string) (*OCISpec, error) {
  data, err := os.ReadFile(filepath.Join(bundlePath, "config.json"))
  if err != nil {
  return nil, fmt.Errorf("read config.json: %w", err)
  }
  var spec OCISpec
  if err := json.Unmarshal(data, &spec); err != nil {
  return nil, fmt.Errorf("parse config.json: %w", err)
  }
  return &spec, nil
}
```

从 config.json 到系统调用的映射很直接：

```go
func namespaceFlagsFromSpec(nss []OCINamespace) uintptr {
  var flags uintptr
  for _, ns := range nss {
  switch ns.Type {
  case "pid":
  flags |= syscall.CLONE_NEWPID
  case "uts":
  flags |= syscall.CLONE_NEWUTS
  case "mount":
  flags |= syscall.CLONE_NEWNS
  case "ipc":
  flags |= syscall.CLONE_NEWIPC
  case "network":
  flags |= syscall.CLONE_NEWNET
  case "user":
  flags |= syscall.CLONE_NEWUSER
  }
  }
  return flags
}
```

### Mounts：从 config.json 到 mount() 系统调用

config.json 里的 `mounts` 数组看起来是声明式的，但运行时处理它的方式很直白——逐条翻译成 `mount(2)` 系统调用：

```go
func setupMounts(spec *OCISpec) error {
  for _, m := range spec.Mounts {
  // 确保挂载目标目录存在
  target := filepath.Join(spec.Root.Path, m.Destination)
  os.MkdirAll(target, 0755)

  // options 字符串拆分成 flags 和 data
  flags, data := parseMountOptions(m.Options)

  // 直接映射到 mount(source, target, fstype, flags, data)
  if err := syscall.Mount(m.Source, target, m.Type, flags, data); err != nil {
  return fmt.Errorf("mount %s -> %s: %w", m.Source, m.Destination, err)
  }
  }
  return nil
}
```

映射关系很机械：

  
|config.json 字段|mount() 参数|例子|
|---|---|---|
|`source`|第一个参数 `source`|`"proc"`, `"tmpfs"`, `"/dev/sda1"`|
|`destination`|第二个参数 `target`（拼上 rootfs 前缀）|`"/proc"` → `"rootfs/proc"`|
|`type`|第三个参数 `filesystemtype`|`"proc"`, `"tmpfs"`, `"sysfs"`|
|`options` 中的标志|第四个参数 `mountflags`|`"nosuid"` → `MS_NOSUID`, `"ro"` → `MS_RDONLY`|
|`options` 中的非标志|第五个参数 `data`|`"mode=755"`, `"size=65536k"`|

`parseMountOptions` 的逻辑就是把 `options` 数组里的字符串分成两类：能映射到 `MS_*` 常量的归入 flags（按位或），剩下的用逗号拼接成 data 字符串。runc 的实现在 `libcontainer/rootfs_linux.go` 里，逻辑完全一样，只是多了一堆 bind mount 和 propagation 的特殊处理。

---

## 五、Hooks：容器生命周期的扩展点

OCI Hooks 让外部程序在容器生命周期的关键节点执行操作：

```
{
  "hooks": {
  "prestart": [{ "path": "/usr/bin/setup-network" }],
  "createRuntime": [{ "path": "/usr/bin/gpu-setup" }],
  "poststart": [{ "path": "/usr/bin/notify-ready" }],
  "poststop": [{ "path": "/usr/bin/cleanup" }]
  }
}
```

- **createRuntime** — create 完成后、start 之前。用于 GPU 设备映射、网络配置
- **prestart** — 已废弃，用 createRuntime 替代
- **poststart** — start 之后。用于通知监控系统
- **poststop** — 容器退出后。用于清理临时资源

NVIDIA Container Toolkit 就是通过 createRuntime hook 把 GPU 设备映射到容器里的。我们来看一个具体例子——用 createRuntime hook 做 GPU 设备准备：

### 具体例子：createRuntime hook 做 GPU 设备映射

config.json 的 hooks 部分：

```
{
  "hooks": {
  "createRuntime": [
  {
  "path": "/usr/bin/gpu-container-hook",
  "args": ["gpu-container-hook", "--device=0"],
  "env": ["PATH=/usr/bin", "NVIDIA_VISIBLE_DEVICES=0"]
  }
  ]
  }
}
```

运行时在调用 hook 时，会通过 **stdin** 把容器的 state JSON 传给 hook 程序。hook 程序读 stdin 拿到容器的 PID 和 bundle 路径，然后做它该做的事。

hook 脚本 `/usr/bin/gpu-container-hook` 的核心逻辑：

```
#!/bin/bash
# 从 stdin 读取容器 state（JSON 格式）
STATE=$(cat)
PID=$(echo "$STATE" | jq -r '.pid')
BUNDLE=$(echo "$STATE" | jq -r '.bundle')

# 在容器的 mount namespace 里创建 GPU 设备节点
ROOTFS=$(jq -r '.root.path' "$BUNDLE/config.json")

# 把宿主机的 /dev/nvidia0 绑定挂载到容器的 rootfs
CONTAINER_ROOTFS="/proc/$PID/root"
mkdir -p "$CONTAINER_ROOTFS/dev/nvidia0"
mount --bind /dev/nvidia0 "$CONTAINER_ROOTFS/dev/nvidia0"

# 挂载 NVIDIA 用户态驱动库
mkdir -p "$CONTAINER_ROOTFS/usr/lib/x86_64-linux-gnu"
mount --bind /usr/lib/x86_64-linux-gnu/libnvidia-ml.so.1 \
  "$CONTAINER_ROOTFS/usr/lib/x86_64-linux-gnu/libnvidia-ml.so.1"
```

再来一个更常见的场景——用 createRuntime hook 配置容器网络（CNI 风格）：

```
{
  "hooks": {
  "createRuntime": [
  {
  "path": "/opt/cni/bin/bridge-hook",
  "args": ["bridge-hook", "--subnet=10.88.0.0/16"],
  "timeout": 10
  }
  ],
  "poststop": [
  {
  "path": "/opt/cni/bin/bridge-hook",
  "args": ["bridge-hook", "--action=teardown"]
  }
  ]
  }
}
```

注意 `timeout` 字段——如果 hook 在指定秒数内没有完成，运行时会杀掉它并报错。这在网络配置 hook 里很重要：你不希望一个 DHCP 超时卡死整个容器创建流程。

运行时调用 hook 的 Go 实现大致如下：

```go
func runHooks(hooks []OCIHook, state []byte) error {
  for _, h := range hooks {
  cmd := exec.Command(h.Path, h.Args[1:]...)
  cmd.Stdin = bytes.NewReader(state)  // 通过 stdin 传递容器 state
  cmd.Env = h.Env

  if err := cmd.Start(); err != nil {
  return fmt.Errorf("hook %s: %w", h.Path, err)
  }
  if h.Timeout != nil {
  // 设置超时定时器
  timer := time.AfterFunc(time.Duration(*h.Timeout)*time.Second, func() {
  cmd.Process.Kill()
  })
  defer timer.Stop()
  }
  if err := cmd.Wait(); err != nil {
  return fmt.Errorf("hook %s exited with: %w", h.Path, err)
  }
  }
  return nil
}
```

多个 hook 按数组顺序执行；前一个失败，后面的根本不会跑。工程上通常是 `createRuntime` 先做设备和网络准备，`prestart` 再做进入容器命名空间后的最后补丁。别把 hook 当普通插件系统乱塞——它本质上是”宿主机上执行的任意程序”。安全做法是严格管控 hook 二进制——它们跑在宿主机上，权限和你的 runtime 一样大。

---

## 六、用 ctr 测试我们的运行时

containerd 的 CLI 工具 `ctr` 支持指定自定义运行时：

```
# 拉一个镜像
sudo ctr image pull docker.io/library/alpine:latest

# 用我们的运行时创建容器
sudo ctr run --runtime /usr/local/bin/miniruntime \
  docker.io/library/alpine:latest mycontainer /bin/sh
```

如果 miniruntime 正确实现了 OCI 接口，ctr 就能无缝调用它。这就是标准的力量 — 你不需要修改上层工具的一行代码。

---

## 七、MUST vs SHOULD vs MAY：务实的兼容策略

OCI 规范里充满了 RFC 2119 的关键词。对于一个迷你运行时，务实的策略是：

|级别|含义|我们的策略|
|---|---|---|
|MUST|必须实现|全部实现|
|SHOULD|应该实现|实现常用的|
|MAY|可以实现|暂时跳过|

**必须实现的**：create、start、state、kill、delete 五个命令，config.json 的核心字段解析。

**MVP 阶段可以跳过，但你要知道自己跳过了什么**：

- `linux.seccomp` — 系统调用过滤。没有它，容器进程可以调用 `reboot()`、`kexec_load()` 等危险系统调用。生产环境**绝对不能跳过**。我们在[第八篇](https://quant67.com/post/containers/08-security/security.html)专门处理。
    
- `process.capabilities` — Linux Capabilities 裁剪。root 的超能力被拆成了 40 多个小能力（`CAP_NET_ADMIN`、`CAP_SYS_PTRACE` 等），容器应该只拿需要的。跳过它意味着容器进程以完整 root 权限运行——这在开发环境勉强能接受，上生产就是在裸奔。同样在[第八篇](https://quant67.com/post/containers/08-security/security.html)展开。
    
- `linux.rootfsPropagation` — 控制 mount 事件是否在容器和宿主机之间传播。我们硬编码了 `MS_PRIVATE`（完全隔离），这对大多数场景是对的。但如果你需要 systemd 类容器或者容器内挂载宿主机目录实时可见，就需要 `MS_SHARED` 或 `MS_SLAVE`。Kubernetes 的 `mountPropagation: Bidirectional` 就依赖这个字段。
    
- `hooks` — 容器生命周期回调。简单场景不需要，但只要涉及 GPU（NVIDIA Container Toolkit）、网络（CNI 插件）、日志采集、服务注册，hooks 就是唯一标准扩展点。跳过它意味着你的运行时无法和这些生态集成。
    
- `linux.devices` — 设备白名单和设备节点创建。跳过它，容器就访问不了 GPU（`/dev/nvidia*`）、FUSE 设备（`/dev/fuse`）、串口（`/dev/ttyUSB*`）等硬件。纯计算型容器可以不管，但只要涉及硬件交互就必须支持。
    
- `linux.intelRdt` — Intel Resource Director Technology，用于 L3 缓存和内存带宽隔离。绝大多数场景用不到，但在多租户高性能计算环境中，它能防止一个容器的缓存抖动拖垮同一台机器上的其他容器。
    
- `linux.uidMappings` / `linux.gidMappings` — User namespace 的 UID/GID 映射。没有它就不能做 rootless 容器。Podman 默认用 rootless 模式，全靠这个字段。
    

---

## 八、我们还缺什么

回头看看第七节那个”可以跳过”的清单，你会发现我们跳过的东西拼在一起，恰好是一个**生产级容器运行时和玩具之间的差距**。

**最紧迫的：安全**。目前我们的容器没有 seccomp 过滤、没有 capability 裁剪、没有 AppArmor/SELinux。一个恶意容器进程可以调用几乎所有系统调用——`reboot()` 重启宿主机、`mount()` 挂载宿主机磁盘、`ptrace()` 注入其他进程。这不是理论攻击，这是真实的容器逃逸路径。

config.json 里的 `process.capabilities` 和 `linux.seccomp` 就是为了堵住这些洞。它们的关系是：Capabilities 决定”你有没有权限做这件事”（粗粒度），Seccomp 决定”你能不能调用这个系统调用”（细粒度）。两者缺一不可，因为有些危险操作不受任何 capability 管控，只有 seccomp 才能拦住。

**其次是生态兼容**。没有 hooks 支持，NVIDIA 的 GPU 容器跑不起来，CNI 网络插件接不进去。没有 devices 支持，任何需要硬件访问的工作负载都跑不了。没有 UID mapping，rootless 容器无从谈起——而 rootless 是现在容器安全的大趋势。

**最后是调试体验**。真正的运行时需要给出有意义的错误信息，而不是一个 “exit status 1” 让用户自己猜。这个我们在下一节专门处理。

下一篇我们集中攻克安全这块硬骨头。`process.capabilities` 和 `linux.seccomp` 这两个字段，对应的是 Linux 内核里两套完全不同的机制——前者拆分 root 权限，后者过滤系统调用。理解了它们，你就明白 Docker 默认的安全策略到底在保护什么。

下一篇：[Seccomp-BPF 与 Capabilities：容器安全的两道防线](https://quant67.com/post/containers/08-security/security.html)。

## 九、调试 OCI 配置

你的 config.json 写好了，运行时一跑就报错——但错误信息只有一句 “container creation failed”。怎么办？

### 用 runc spec 生成基准配置

别从零写 config.json。先让 runc 给你生成一个标准的：

```
mkdir my-bundle && cd my-bundle
mkdir rootfs
# 用 alpine 的 rootfs 或者 docker export 导出一个
runc spec
# 会在当前目录生成 config.json，包含所有常用字段的默认值
```

这个默认 config.json 是一个**已知能工作**的起点。然后逐步修改、逐步测试，每次只改一个字段——这比从零开始写然后祈祷它能跑靠谱得多。

### 常见错误和报错信息

  
|你犯的错|运行时报什么|怎么修|
|---|---|---|
|`root.path` 指向不存在的目录|`container rootfs does not exist`|检查 bundle 目录下是否有 rootfs/|
|`process.args` 为空数组|`args must not be empty`|至少要有一个元素，如 `["/bin/sh"]`|
|`process.args[0]` 在 rootfs 里不存在|`exec: "/bin/bash": stat ... no such file`|确认 rootfs 里有这个二进制，alpine 没有 bash|
|`ociVersion` 写错或缺失|`unsupported spec version`|用 `"1.0.2"` 或 `"1.1.0"`|
|namespace type 拼写错误|`invalid namespace type "nets"`|检查拼写：`pid`, `network`, `mount`, `uts`, `ipc`, `user`, `cgroup`|
|`mounts` 里 destination 不是绝对路径|`invalid mount destination`|必须以 `/` 开头|
|`linux.resources` 里 memory limit 太小|容器立即被 OOM kill|至少给 4MB，`"limit": 4194304`|
|JSON 语法错误（多了逗号、少了引号）|`parse config.json: invalid character...`|先用 `jq . config.json` 验证 JSON 语法|

### 验证 config.json

在运行之前先验证配置文件的正确性：

```
# 方法一：用 jq 检查 JSON 语法
jq . config.json > /dev/null && echo "JSON OK" || echo "JSON broken"

# 方法二：用 oci-runtime-tool 做规范级验证（需要安装）
go install github.com/opencontainers/runtime-tools/cmd/oci-runtime-tool@latest
oci-runtime-tool validate --path config.json

# 方法三：自己写一个最小验证脚本
python3 -c "
import json, sys
spec = json.load(open('config.json'))
assert 'ociVersion' in spec, 'missing ociVersion'
assert spec.get('process', {}).get('args'), 'process.args is empty'
assert spec.get('root', {}).get('path'), 'root.path is empty'
print('Basic validation passed')
"
```

### 运行时调试技巧

当 config.json 语法正确但容器还是起不来时，问题出在运行时执行阶段。几个排查手段：

**1. 开运行时的 debug 日志**

```
# runc 支持 --debug 和 --log 参数
runc --debug --log /var/log/runc-debug.log create mycontainer --bundle ./my-bundle
cat /var/log/runc-debug.log
```

**2. strace 运行时本身**

运行时也只是一个用户态程序。strace 它，能看到它到底在哪个系统调用上失败了：

```
strace -f -e trace=clone,mount,unshare,pivot_root,execve \
  runc create mycontainer --bundle ./my-bundle 2>&1 | tail -50
```

`-f` 跟踪子进程很关键——运行时会 fork 出 init 进程，真正的错误往往在子进程里。重点关注返回 `-1 EPERM` 或 `-1 ENOENT` 的调用。

**3. 检查运行时的状态目录**

runc 在 `/run/runc/` 下维护每个容器的状态（state.json）。如果容器卡在奇怪的状态：

```
# 查看容器状态
cat /run/runc/<container-id>/state.json | jq .

# 如果容器状态是 "created" 但 start 失败，检查 init 进程是否还活着
ls -la /proc/$(jq -r '.init_process_pid' /run/runc/<container-id>/state.json)/

# 强制清理僵尸容器
runc delete --force <container-id>
```

**4. 最小化复现**

如果不确定是哪个字段出了问题，回到 `runc spec` 的默认配置，确认它能工作，然后**二分法**加入你的修改。这比盯着一个 100 行的 config.json 猜问题高效得多。

---

## 相关阅读

- [Raft 实现拆解：etcd 的共识算法](https://quant67.com/post/distributed/raft-etcd/raft-etcd.html) — 另一个”拆解规范实现”的例子
- [Go 调度器深度拆解](https://quant67.com/post/go/scheduler/scheduler.html) — 理解 Go runtime 与容器的交互

## 同主题继续阅读

把当前热点继续串成多页阅读，而不是停在单篇消费。

2026-04-12 · linux / containers

### [【从零造容器】runc 源码考古：OCI 参考实现到底长什么样](https://quant67.com/post/containers/12-runc-source/runc-source.html)

我们的迷你运行时有 500 行，runc 有 15000 行。多出来的代码在干什么？本文拆解 runc 的核心流程：从 runc create 到容器 init 进程，libcontainer 的设计，nsenter 里那段神秘的 C 代码，以及 Go runtime fork 的天坑。

2026-04-06 · linux / containers

### [【从零造容器】用 Go 组装迷你容器运行时：把积木拼起来](https://quant67.com/post/containers/06-mini-runtime/mini-runtime.html)

五篇文章攒了一堆内核积木：namespace、netns、rootfs、cgroup、overlayfs。现在是时候用 Go 把它们拼成一个能跑的容器运行时了。不到 500 行代码，create/start/exec/kill/delete，五个命令走完容器的一生。

2026-04-01 · linux / containers

### [【从零造容器】Linux Namespaces：用 50 行 C 隔离一个进程](https://quant67.com/post/containers/01-namespaces/namespaces.html)

容器不是魔法。它就是几个系统调用。本文用 C 从 clone() 开始，逐个开启 PID/UTS/Mount/IPC namespace，看隔离到底是怎么回事。50 行代码，你就拥有了一个'容器'的雏形。

2026-04-01 · linux / containers

### [【从零造容器】Network Namespace：给你的进程接上虚拟网线](https://quant67.com/post/containers/02-netns/netns.html)

上一篇我们用 clone() 隔离了 PID、主机名和挂载点，但那个'容器'连 lo 都 ping 不通。本文从 CLONE_NEWNET 出发，用 veth pair + bridge + iptables MASQUERADE，一步步给容器接上网。