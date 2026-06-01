你 `docker pull nginx`，下载了 5 个 layer。你 `docker pull node`，发现其中 3 个 layer 已经存在 — 因为它们共享同一个 Debian base image。每个 layer 只存储与上一层的差异，就像 Git 的 commit。

这不是 Docker 发明的。这是 Linux 内核的 OverlayFS，一个联合挂载文件系统。

但”分层”和”共享”听起来太美好了。当你在容器里修改一个 1GB 的文件时，OverlayFS 会把整个文件复制一遍 — 这就是 copy-on-write 的代价。什么时候这个代价会杀死你的性能？我们来实测。

> 本文代码在 `examples/containers/05-overlayfs/`，`make run` 即可体验。

---

## 一、联合挂载：把多个目录叠成一个

OverlayFS 的核心概念很简单：把多个目录”叠”在一起，呈现为一个合并后的视图。

```
  merged (用户看到的)
  ┌──────────────┐
  │ file_a (upper)│
  │ file_b (lower)│
  │ file_c (lower)│
  └──────────────┘
  ▲
  ┌────────┴────────┐
  │  │
upperdir  lowerdir
┌─────────┐  ┌──────────┐
│ file_a'  │  │ file_a  │
│  │  │ file_b  │
│  │  │ file_c  │
└─────────┘  └──────────┘
```

四个关键目录：

|目录|作用|读写|
|---|---|---|
|**lowerdir**|底层，只读。可以有多个，用 `:` 分隔|只读|
|**upperdir**|上层，所有修改写入这里|读写|
|**workdir**|内核内部使用（原子操作的临时空间）|内核专用|
|**merged**|合并后的视图，用户实际操作的挂载点|读写|

一条 mount 命令就能创建：

```
mount -t overlay overlay \
  -o lowerdir=/lower,upperdir=/upper,workdir=/work \
  /merged
```

读文件时，OverlayFS 先看 upperdir，找不到再看 lowerdir。写文件时，如果文件在 lowerdir，先把它复制到 upperdir（copy-up），然后修改 upper 的副本。lowerdir 永远不变。

![OverlayFS 分层读写流程](https://quant67.com/post/containers/05-overlayfs/overlayfs-layers.svg)

---

## 二、手工构建分层”镜像”

不用 Docker，我们手工构建一个三层镜像：

```
#!/bin/bash
set -e

# 创建目录结构
mkdir -p /tmp/overlay/{base,app,config,upper,work,merged}

# Layer 1: base — 模拟操作系统基础层
echo "I'm /etc/os-release from base layer" > /tmp/overlay/base/os-release
echo "I'm /bin/hello from base layer" > /tmp/overlay/base/hello
chmod +x /tmp/overlay/base/hello

# Layer 2: app — 模拟应用层
mkdir -p /tmp/overlay/app
echo "I'm the app binary" > /tmp/overlay/app/myapp
echo "I'm app config, overriding base" > /tmp/overlay/app/os-release

# Layer 3: config — 模拟运行时配置层
mkdir -p /tmp/overlay/config
echo "runtime-specific config" > /tmp/overlay/config/runtime.conf

# 挂载：多层 lowerdir，从右到左优先级递增
# config 层 > app 层 > base 层
sudo mount -t overlay overlay \
  -o lowerdir=/tmp/overlay/config:/tmp/overlay/app:/tmp/overlay/base,\
upperdir=/tmp/overlay/upper,\
workdir=/tmp/overlay/work \
  /tmp/overlay/merged

echo "=== Merged view ==="
ls -la /tmp/overlay/merged/
echo ""
echo "os-release content (from app layer, overrides base):"
cat /tmp/overlay/merged/os-release
echo ""
echo "hello content (from base layer):"
cat /tmp/overlay/merged/hello
echo ""
echo "runtime.conf content (from config layer):"
cat /tmp/overlay/merged/runtime.conf
```

lowerdir 可以有多个，用 `:` 分隔，**左边的优先级高**。所以 `config:app:base` 意味着 config 层覆盖 app 层，app 层覆盖 base 层。

这就是 Docker 镜像分层的本质。每个 `RUN` 指令产生一层 lowerdir，`docker run` 时在最上面加一层 upperdir 作为容器的可写层。

---

## 三、Copy-on-Write：天下没有免费的午餐

当你在 merged 目录里修改一个只存在于 lowerdir 的文件时，OverlayFS 需要：

1. 从 lowerdir 把整个文件复制到 upperdir（**copy-up**）
2. 在 upperdir 上修改副本

这意味着：

- 修改一个 1GB 文件的第一个字节，OverlayFS 要复制整个 1GB
- 第一次写入很慢，后续写入正常速度（因为已经在 upper 了）
- 元数据操作（chmod、chown）也触发 copy-up

### 实测 copy-up 开销

```c
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

static double now_ms(void) {
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return ts.tv_sec * 1000.0 + ts.tv_nsec / 1e6;
}

int main(int argc, char **argv) {
  if (argc < 2) {
  fprintf(stderr, "Usage: %s <file-in-merged>\n", argv[0]);
  return 1;
  }

  double t0 = now_ms();

  /* 第一次写入：触发 copy-up */
  int fd = open(argv[1], O_WRONLY);
  if (fd < 0) { perror("open"); return 1; }
  write(fd, "X", 1);
  fsync(fd);
  close(fd);

  double t1 = now_ms();

  /* 第二次写入：文件已在 upper，无需 copy-up */
  fd = open(argv[1], O_WRONLY);
  write(fd, "Y", 1);
  fsync(fd);
  close(fd);

  double t2 = now_ms();

  printf("First write (with copy-up):  %.2f ms\n", t1 - t0);
  printf("Second write (no copy-up):  %.2f ms\n", t2 - t1);
  printf("Copy-up overhead:  %.1fx\n", (t1 - t0) / (t2 - t1));

  return 0;
}
```

在 SSD 上用 100MB 文件测试：

```
First write (with copy-up):  47.32 ms
Second write (no copy-up):  0.18 ms
Copy-up overhead:  263.0x
```

**第一次写入慢了 260 倍**。文件越大，差距越大。

### 数据库场景的灾难

想象一个 MySQL 容器，数据文件 `ibdata1` 有 10GB。如果它在 lowerdir（比如镜像的某一层预装了数据），第一次写入会触发 10GB 的 copy-up。这就是为什么 Docker 文档反复强调：**数据库文件必须放在 volume 上，不要放在容器的可写层**。

---

## 四、删除文件：Whiteout 的魔法

在联合挂载中，删除 lowerdir 的文件是个有趣的问题 — 你不能修改 lowerdir（它是只读的），那怎么让文件”消失”？

答案是 **whiteout 文件**：一个字符设备文件（主设备号 0，次设备号 0），名字和被删除的文件一样。OverlayFS 看到 whiteout 就知道这个文件”不存在”了。

```
# 在 merged 里删除一个 lower 层的文件
rm /merged/somefile

# 查看 upper 层
ls -la /upper/
# 你会看到：
# c--------- 1 root root 0, 0 ... somefile
```

删除目录用 **opaque directory**：在 upper 层创建同名目录，并设置 `trusted.overlay.opaque` 扩展属性为 `y`。

```
# 删除 lower 层的一个目录
rm -rf /merged/somedir

# upper 层会有一个 opaque 目录
getfattr -n trusted.overlay.opaque /upper/somedir
# trusted.overlay.opaque="y"
```

---

## 五、存储驱动对比：为什么 overlay2 赢了

Docker 历史上支持过很多存储驱动：

   
|驱动|机制|优点|缺点|
|---|---|---|---|
|**overlay2**|OverlayFS|内核原生，性能好，简单|copy-up 开销|
|**devicemapper**|LVM 精简配置|块级 COW，无 copy-up 大文件问题|配置复杂，默认 loop 模式性能差|
|**btrfs**|Btrfs 子卷 + 快照|块级 COW，快照快|需要 Btrfs 文件系统|
|**zfs**|ZFS 克隆|块级 COW，数据完整性好|内核外模块，内存消耗大|
|**aufs**|联合挂载（非内核主线）|Docker 最早的存储驱动|没进内核主线，已弃用|

overlay2 从 Docker 18.09 开始成为默认驱动，因为：

1. **OverlayFS 在内核主线**（3.18+），不需要额外模块
2. **inode 效率**：overlay2 利用 kernel 4.0+ 的多层 lowerdir 支持，每个镜像只需一个 overlay mount（老的 overlay 驱动每层需要一个）
3. **性能足够好**：对大多数工作负载来说，copy-up 开销可以接受
4. **配置简单**：不像 devicemapper 需要配置直接 LVM

但如果你的容器频繁修改大文件（比如数据库），块级 COW 的 devicemapper/btrfs/zfs 理论上更好。实际上？大家都用 volume — 这是正确的做法。数据库文件绝对不应该放在 overlay 层上，因为每次写入都可能触发 copy-up，一个 1GB 的 WAL 文件首次写入时会被完整复制，延迟直接飙到秒级。`docker run -v /data/postgres:/var/lib/postgresql/data` 才是生产环境的标配。

如果你在 OCI bundle 里表达这个最佳实践，本质上就是一个 bind mount：

```
{
  "destination": "/var/lib/postgresql/data",
  "type": "bind",
  "source": "/data/postgres",
  "options": ["rbind", "rw"]
}
```

镜像层继续放在 OverlayFS 的 lowerdir 链上，真正频繁写的数据走独立 volume。Docker/Kubernetes 的分工就是这样：镜像管分发，volume 管持久化。

> **底层文件系统的影响**：OverlayFS 的性能还取决于底层文件系统。ext4 是最成熟的选择。XFS 在 Linux < 4.17 上有 inode 编号溢出问题（d_ino 不一致）。生产环境建议 ext4 + overlay2，除非你有特殊理由。

---

### 读性能

如果文件在 lowerdir，OverlayFS 的读性能几乎等于直接读底层文件系统，因为 OverlayFS 直接把读请求转发到底层 inode。**没有额外的拷贝或缓存层**。

但有一个细微差异：`open()` 比直接文件系统稍慢，因为 OverlayFS 需要做目录查找确定文件在哪一层。层数越多，查找越慢。Docker 默认限制镜像最多 128 层是有道理的。

### 写性能

- **upper 层文件**：和直接操作底层文件系统一样快
- **lower 层文件首次写入**：触发 copy-up，慢
- **lower 层文件后续写入**：已经在 upper，正常速度
- **创建新文件**：直接写入 upper，快

### 元数据操作

`stat()`、`readdir()` 需要合并多层信息，比单层文件系统稍慢。如果目录在多层都有文件，`readdir()` 需要合并去重。

---

## 七、用 C 操作 OverlayFS

用 C 的 `mount()` 系统调用挂载 OverlayFS：

```c
#include <sys/mount.h>
#include <stdio.h>

int setup_overlay(const char *lower, const char *upper,
  const char *work, const char *merged) {
  char opts[4096];
  snprintf(opts, sizeof(opts),
  "lowerdir=%s,upperdir=%s,workdir=%s",
  lower, upper, work);

  if (mount("overlay", merged, "overlay", 0, opts) == -1) {
  perror("mount overlay");
  return -1;
  }
  return 0;
}
```

这段代码会出现在我们的迷你容器运行时里 — [第六篇](https://quant67.com/post/containers/06-mini-runtime/mini-runtime.html)会用 Go 重写它。

---

## 八、Docker 是怎么用 OverlayFS 的

看看真实的 Docker overlay2 目录结构：

```
$ ls /var/lib/docker/overlay2/
l/  # 符号链接快捷目录
a1b2c3d4.../  # layer 1
  diff/  # 这一层的文件内容
  link  # 这一层在 l/ 下的短链接名
  lower  # 指向更低层的链接
e5f6g7h8.../  # layer 2
  diff/
  link
  lower
i9j0k1l2-init/  # init layer（/etc/hostname 等）
i9j0k1l2/  # 容器的可写层
  diff/  # upperdir
  link
  lower
  merged/  # 合并后的挂载点（容器的根文件系统）
  work/  # workdir
```

每个镜像层有一个 `diff/` 目录存储文件内容，一个 `link` 文件存储短链接名（因为 mount options 有长度限制，Docker 用短符号链接避免路径过长）。

容器的 `-init` 层是 Docker 自动添加的，包含容器特定的配置文件（`/etc/hostname`、`/etc/resolv.conf`），放在 lower 和 upper 之间。

---

## 九、我们还缺什么

现在我们有了： - Namespace 隔离（[#01](https://quant67.com/post/containers/01-namespaces/namespaces.html)） - 网络连接（[#02](https://quant67.com/post/containers/02-netns/netns.html)） - 根文件系统（[#03](https://quant67.com/post/containers/03-rootfs/rootfs.html)） - 资源限制（[#04](https://quant67.com/post/containers/04-cgroups/cgroups.html)） - 分层镜像（本文）

下一步，是把所有这些积木用 Go 组装成一个能跑的容器运行时 — [#06 迷你容器运行时](https://quant67.com/post/containers/06-mini-runtime/mini-runtime.html)。

## 相关阅读

- [io_uring vs epoll 性能对比](https://quant67.com/post/io_uring/uring-vs-epoll-benchmark/benchmark.html) — I/O 性能测试方法论
- [内存分配器擂台](https://quant67.com/post/linux/allocator-arena/allocator-arena.html) — 容器内存限制如何影响分配器行为
- [用 Rust 重写 C 网络服务器](https://quant67.com/post/rust/rewrite-c-server/rewrite-c-server.html) — 另一个”自己造一遍就懂了”的例子

## 同主题继续阅读

把当前热点继续串成多页阅读，而不是停在单篇消费。

2026-04-02 · linux / containers

### [【从零造容器】Mount Namespace 与 pivot_root：构建容器文件系统](https://quant67.com/post/containers/03-rootfs/rootfs.html)

chroot 不是安全边界——10 行 C 就能逃出去。本文用 pivot_root 构建真正隔离的容器根文件系统：从 Alpine minirootfs 到设备节点，从 mount propagation 到只读根，一步步把容器的'地基'打牢。

2026-04-06 · linux / containers

### [【从零造容器】用 Go 组装迷你容器运行时：把积木拼起来](https://quant67.com/post/containers/06-mini-runtime/mini-runtime.html)

五篇文章攒了一堆内核积木：namespace、netns、rootfs、cgroup、overlayfs。现在是时候用 Go 把它们拼成一个能跑的容器运行时了。不到 500 行代码，create/start/exec/kill/delete，五个命令走完容器的一生。

2026-04-08 · linux / containers

### [【从零造容器】Seccomp-BPF 与 Capabilities：容器安全的两道防线](https://quant67.com/post/containers/08-security/security.html)

你的容器能调用 reboot()。是的，现在就能。除非有人拦住它。Capabilities 拆分 root 权限，Seccomp-BPF 过滤系统调用——两道防线，缺一不可。本文用 C 代码拆解这两套机制，看看 Docker 到底替你挡住了什么。

2026-04-01 · linux / containers

### [【从零造容器】Linux Namespaces：用 50 行 C 隔离一个进程](https://quant67.com/post/containers/01-namespaces/namespaces.html)

容器不是魔法。它就是几个系统调用。本文用 C 从 clone() 开始，逐个开启 PID/UTS/Mount/IPC namespace，看隔离到底是怎么回事。50 行代码，你就拥有了一个'容器'的雏形。