上两篇文章里，我们的”容器”有了[独立的 PID、主机名](https://quant67.com/post/containers/01-namespaces/namespaces.html)、[独立的网络栈](https://quant67.com/post/containers/02-netns/netns.html)。但有个致命的问题：**它还踩在宿主机的文件系统上**。容器进程能看到宿主机的 `/etc/shadow`、`/root/.ssh/`、一切。

你可能会说：用 `chroot` 呀，这不是 Unix 古老的把戏吗？

问题是，chroot 的”隔离”比你想象的脆弱得多。10 行 C 就能逃出去。

> 本文所有代码在 `examples/containers/03-rootfs/` 目录，`make` 即可编译。测试环境：Linux 6.x, x86_64。

---

## 一、chroot 的谎言：10 行代码越狱

`chroot()` 做的事情很简单：改变进程看到的根目录。但它**只改变了一个指针**，不修改当前工作目录，不隔离挂载表，不阻止特权操作。

经典的逃逸方法只需要 4 步：

```c
#include <unistd.h>
#include <sys/stat.h>

int main(void) {
  // 1. 在 chroot 环境内创建一个临时目录
  mkdir(".escape", 0755);

  // 2. 再次 chroot 到这个目录
  //  关键：cwd 不变！它仍然在旧的 chroot 根 "/"
  //  但新的 chroot 根变成了 .escape
  //  于是 cwd 现在"在 chroot 根之外"
  chroot(".escape");

  // 3. chdir("..") 向上走，穿越 chroot 边界
  //  因为 cwd 在根之外，内核允许这个操作
  for (int i = 0; i < 64; i++)
  chdir("..");

  // 4. 把当前目录设为新的根 — 回到真实的 /
  chroot(".");

  // 现在我们在宿主机的真实根目录了
  execl("/bin/sh", "sh", NULL);
}
```

就这么简单。第二次 `chroot()` 之后，`cwd` 和 `root` 不在同一棵子树里了，`chdir("..")` 就能一路向上走到真实的根。

> 完整可编译的逃逸演示见 `examples/containers/03-rootfs/chroot_escape.c`。

这就是为什么 chroot 的 man page 里写着：“This call does not change the current working directory, so that after the call ‘.’ can be outside the tree rooted at ‘/’.” — 这不是 bug，是 feature。一个 1979 年设计的 feature。

**结论：chroot 不是安全边界。从来不是，将来也不是。**

容器需要更硬的手段。

---

在[第一篇文章](https://quant67.com/post/containers/01-namespaces/namespaces.html)里我们已经见过 Mount namespace（`CLONE_NEWNS`）。简单回顾：

- `CLONE_NEWNS` 创建独立的**挂载点表**副本
- 子 namespace 里的 mount/umount 不影响父 namespace（前提：propagation 设对了）
- 这是 Linux 最早的 namespace（2002 年，所以 flag 名叫 `NEWNS` 而不是 `NEWMNT`）

Mount namespace 是 pivot_root 的前提条件。没有独立的挂载表，你做的任何挂载操作都会影响宿主机。

但 mount namespace 本身不够。它只给你一个独立的挂载表副本，你还得亲手把根目录换成容器的文件系统。这就是 pivot_root 的工作。

---

## 三、pivot_root vs chroot：真正的换根

`pivot_root` 和 `chroot` 都能让进程看到不同的根目录，但机制完全不同：

||chroot|pivot_root|
|---|---|---|
|做了什么|只改变进程的 `/` 指针|交换整个挂载树的根|
|旧根去哪了|还在，只是进程”看不见”|变成一个子挂载点，可以 umount|
|能逃逸吗|能，见上文|旧根被 umount 后，无处可逃|
|需要 mount namespace|不需要|需要|
|适用场景|临时改变视角（构建系统等）|容器隔离|

pivot_root 的签名：

```c
int pivot_root(const char *new_root, const char *put_old);
```

它做的事情：

1. 把 `new_root` 变成挂载树的根 `/`
2. 把原来的根挂载到 `put_old`（必须在 `new_root` 之下）
3. 进程的 `/` 现在指向容器的文件系统

然后你可以 `umount(put_old)` — 旧的宿主机根就被彻底移除了。连 `chdir("..")` 都没用，因为挂载点不存在了。

![pivot_root 操作流程](https://quant67.com/post/containers/03-rootfs/pivot-root-flow.svg)

注意 glibc 没有 `pivot_root` 的封装函数，得用 `syscall()`：

```c
#include <sys/syscall.h>

static int pivot_root(const char *new_root, const char *put_old)
{
  return syscall(SYS_pivot_root, new_root, put_old);
}
```

还有一个容易踩的坑：`pivot_root` 要求 `new_root` 必须是一个**挂载点**，不能只是一个普通目录。解决方法是先 bind mount 到自身：

```c
// 让 rootfs 目录成为挂载点
mount(rootfs, rootfs, NULL, MS_BIND | MS_REC, NULL);
```

---

## 四、动手：从零构建容器 rootfs

说了这么多理论，来写代码。我们的目标是：

1. 下载 Alpine minirootfs 作为容器文件系统
2. 创建 namespace
3. 用 pivot_root 切换根
4. 挂载 /proc、/sys、/dev
5. Exec /bin/sh

### 4.1 准备 Alpine minirootfs

Alpine Linux 提供了极小的根文件系统 tarball（约 3MB），非常适合做容器 rootfs：

之所以选 Alpine，不只是因为它小。`minirootfs` 几乎不带额外守护进程，BusyBox + musl 的组合也让依赖关系很干净。拿它做实验，你几乎总能确定”问题在你的容器代码”，而不是发行版启动脚本。

```
# 下载 Alpine 3.21 minirootfs
ALPINE_URL="https://dl-cdn.alpinelinux.org/alpine/v3.21/releases/x86_64"
curl -fSL -o alpine-minirootfs.tar.gz \
  "${ALPINE_URL}/alpine-minirootfs-3.21.3-x86_64.tar.gz"

# 解压到 rootfs 目录
mkdir -p rootfs
tar xzf alpine-minirootfs.tar.gz -C rootfs

# 看看里面有什么
ls rootfs/
# bin  dev  etc  home  lib  media  mnt  opt  proc  root  run  sbin
# srv  sys  tmp  usr  var
```

这就是一个完整的 Linux 用户空间。没有内核，不需要 — 容器共享宿主机的内核。

> 完整的准备脚本见 `examples/containers/03-rootfs/prepare_rootfs.sh`。

### 4.2 pivot_root 的完整流程

整个流程用代码表示：

```c
static int child_fn(void *arg)
{
  const char *rootfs = (const char *)arg;

  // 1. 切断挂载传播（下一节详细讨论）
  mount("", "/", "", MS_PRIVATE | MS_REC, NULL);

  // 2. bind mount rootfs 到自身（pivot_root 要求 new_root 是挂载点）
  mount(rootfs, rootfs, NULL, MS_BIND | MS_REC, NULL);

  // 3. 创建 put_old 目录
  char old_root[256];
  snprintf(old_root, sizeof(old_root), "%s/.old_root", rootfs);
  mkdir(old_root, 0700);

  // 4. pivot_root!
  pivot_root(rootfs, old_root);
  chdir("/");

  // 5. 挂载 /proc, /sys, /dev（下面详述）
  mount("proc", "/proc", "proc", 0, NULL);
  mount("sysfs", "/sys", "sysfs", MS_RDONLY, NULL);

  // chdir("/") 不能省。否则当前 cwd 还可能指向旧 root
  // 即使 umount 成功，进程仍然能通过 cwd 间接引用旧根
  // 6. 卸载旧根 — 这是关键的安全步骤
  umount2("/.old_root", MNT_DETACH);
  rmdir("/.old_root");

  // 7. 启动 shell
  execv("/bin/sh", (char *[]){"/bin/sh", NULL});
  return 1;
}

int main(void)
{
  char *stack = malloc(1024 * 1024);
  int flags = CLONE_NEWPID | CLONE_NEWUTS | CLONE_NEWNS |
  CLONE_NEWIPC | SIGCHLD;

  pid_t pid = clone(child_fn, stack + 1024 * 1024,
  flags, "/path/to/rootfs");
  waitpid(pid, NULL, 0);
  return 0;
}
```

运行效果：

```
$ sudo ./pivot_root_demo ./rootfs mycontainer
[host] 创建容器 (rootfs=./rootfs, hostname=mycontainer)
[host] 容器进程 PID = 42019
[container] pivot_root("./rootfs", "./rootfs/.old_root")
[container] umount("/.old_root")

========================================
  Container ready!
  PID:  1
  Hostname: mycontainer
  Root FS:  Alpine minirootfs
========================================

/ # ls /
bin  dev  etc  home  lib  media  mnt  opt  proc  root
run  sbin  srv  sys  tmp  usr  var
/ # cat /etc/os-release
NAME="Alpine Linux"
/ # ps aux
PID  USER  TIME  COMMAND
  1 root  0:00 /bin/sh
  2 root  0:00 ps aux
```

干净的 Alpine 环境，PID 1，看不到宿主机的任何东西。

> 完整可编译版本：`examples/containers/03-rootfs/pivot_root_demo.c`

---

## 五、Mount Propagation：那条你不能少的语句

记得第一篇文章里这行代码吗？

```c
mount("", "/", "", MS_PRIVATE | MS_REC, NULL);
```

当时我说”切断挂载传播”。现在来详细解释为什么这行不能少。

### 5.1 四种传播类型

Linux 内核为每个挂载点维护一个 propagation 类型：

  
|类型|行为|典型用途|
|---|---|---|
|**shared**|挂载事件双向传播：peer 组内任一成员的 mount/umount 都会传播给其他成员|systemd 默认|
|**slave**|单向传播：master → slave。slave 的变更不回传|容器看到宿主新挂载|
|**private**|完全隔离，不传播也不接收|容器运行时的标准选择|
|**unbindable**|和 private 一样，但额外不能被 bind mount|防止递归 bind|

查看当前挂载的 propagation 类型：

```
$ cat /proc/self/mountinfo | head -5
# ... shared:1 ...  ← 注意 "shared:N" 标记
```

### 5.2 不设 MS_PRIVATE 会怎样

现代 Linux 发行版（使用 systemd）默认把根挂载设为 **shared**。这意味着：

1. clone(CLONE_NEWNS) 创建了新的 mount namespace
2. 新 namespace 是父 namespace 的**副本**，所有挂载点也被复制了
3. 因为是 shared，子 namespace 里的 mount/umount 会**传播回父 namespace**

后果？你在容器里 `mount("proc", "/proc", ...)` — 宿主机的 `/proc` 也被重新挂载了。你在容器里 `umount("/.old_root")` — 宿主机的根也被卸载了。

这不是理论上的风险。早期的容器实现真的遇到过这个问题。runc 的代码里就有一段注释：

> Make the parent mount private to make sure nothing propagates back.

解决方法就是在子进程一开始就设为 private：

```c
// MS_PRIVATE: 设为 private propagation
// MS_REC: 递归应用到所有子挂载点
mount("", "/", "", MS_PRIVATE | MS_REC, NULL);
```

`MS_REC` 很重要 — 没有它，只有根挂载点变成 private，其他挂载点（`/proc`、`/sys`、`/dev` 等）可能仍然是 shared。

### 5.3 容器运行时怎么做的

看看 runc 的做法（Go 代码，但逻辑一样）：

```c
# 在容器初始化阶段：
# 1. 先把所有挂载设为 slave（接收宿主机的新挂载）
mount("", "/", "", MS_SLAVE | MS_REC, NULL);
# 2. 再设为 private（完全隔离）
mount("", "/", "", MS_PRIVATE | MS_REC, NULL);
```

先 slave 后 private 是为了处理一些 edge case — 某些内核版本在直接从 shared 转 private 时可能出问题。

---

## 六、/dev 的秘密：最小化设备节点

容器里的 `/dev` 不能直接用宿主机的 — 那暴露了所有块设备、磁盘分区、GPU。我们需要一个最小化的 `/dev`。

### 6.1 必要的设备节点

一个功能正常的容器至少需要这些：

|设备|Major:Minor|用途|
|---|---|---|
|`/dev/null`|1:3|吞噬一切。`> /dev/null`|
|`/dev/zero`|1:5|无限零字节。`dd if=/dev/zero`|
|`/dev/random`|1:8|随机数（可能阻塞）|
|`/dev/urandom`|1:9|随机数（不阻塞）|
|`/dev/tty`|5:0|控制终端|

用 `mknod` 创建：

```c
#include <sys/stat.h>
#include <sys/sysmacros.h>

// mount tmpfs 作为 /dev 的基础
mount("tmpfs", "/dev", "tmpfs", MS_NOSUID | MS_STRICTATIME, "mode=755");

// 创建设备节点
mknod("/dev/null",  S_IFCHR | 0666, makedev(1, 3));
mknod("/dev/zero",  S_IFCHR | 0666, makedev(1, 5));
mknod("/dev/random",  S_IFCHR | 0444, makedev(1, 8));
mknod("/dev/urandom", S_IFCHR | 0444, makedev(1, 9));
mknod("/dev/tty",  S_IFCHR | 0666, makedev(5, 0));
```

### 6.2 符号链接和伪终端

还需要一些符号链接让标准 I/O 工作：

```c
// /dev/fd → /proc/self/fd
symlink("/proc/self/fd",  "/dev/fd");
symlink("/proc/self/fd/0", "/dev/stdin");
symlink("/proc/self/fd/1", "/dev/stdout");
symlink("/proc/self/fd/2", "/dev/stderr");
```

如果容器需要 PTY（伪终端，`docker exec -it` 需要），还需要挂载 devpts：

```c
mkdir("/dev/pts", 0755);
mount("devpts", "/dev/pts", "devpts", MS_NOSUID | MS_NOEXEC,
  "newinstance,ptmxmode=0666");
```

### 6.3 Docker 的 /dev 策略

实际的容器运行时（runc）用的是 bind mount 策略，而不是 mknod：

```c
// runc 的做法：从宿主机 bind mount 设备节点
// 好处：不需要 CAP_MKNOD 权限
mount("/dev/null", container_path("/dev/null"), NULL, MS_BIND, NULL);
```

这种方式更安全 — mknod 需要 `CAP_MKNOD` capability，而在 user namespace 里可能没有这个权限。[第九篇 rootless 容器](https://quant67.com/post/containers/09-rootless/rootless.html)会详细讨论这个问题。

---

## 七、tmpfs：/tmp 和 /run

容器的 `/tmp` 和 `/run` 应该是 tmpfs — 内存文件系统，容器退出后自动清理：

```c
// /tmp — 所有用户可写，sticky bit
mkdir("/tmp", 01777);
mount("tmpfs", "/tmp", "tmpfs",
  MS_NOSUID | MS_NODEV | MS_STRICTATIME,
  "mode=1777,size=65536k");

// /run — 运行时数据（PID 文件、socket 等）
mkdir("/run", 0755);
mount("tmpfs", "/run", "tmpfs",
  MS_NOSUID | MS_NODEV | MS_STRICTATIME,
  "mode=755,size=65536k");
```

注意 `size=65536k` — 不限制大小的 tmpfs 可以吃光内存。在没有 cgroup 内存限制的情况下（[第四篇](https://quant67.com/post/containers/04-cgroups/cgroups.html)会加上），至少在 tmpfs 层面做个限制。

`/tmp` 的权限 `01777` 中的 `0` 前缀是八进制标记，`1` 是 sticky bit — 防止用户删除其他用户的文件。

---

## 八、只读根文件系统：最后一道防线

容器根文件系统应该是**只读的**。理由：

- 容器镜像是不可变的 — 运行时不应该修改
- 攻击者即使获得了容器内的 root，也写不了文件系统
- 保证了容器的可重复性

实现只读根很简单：

```c
// 在 pivot_root 之后，把根文件系统重新挂载为只读
mount("", "/", "", MS_REMOUNT | MS_RDONLY | MS_BIND, NULL);
```

但完全只读会有问题 — 很多程序需要写 `/tmp`、`/run`、`/var/log`。解决方案是**选择性地挂载可写 tmpfs**：

```c
// 根是只读的
mount("", "/", "", MS_REMOUNT | MS_RDONLY | MS_BIND, NULL);

// 但 /tmp, /run 是可写的 tmpfs
mount("tmpfs", "/tmp", "tmpfs", MS_NOSUID | MS_NODEV, "mode=1777");
mount("tmpfs", "/run", "tmpfs", MS_NOSUID | MS_NODEV, "mode=755");
```

Docker 的 `--read-only` flag 就是这么实现的。Kubernetes 的 `readOnlyRootFilesystem: true` 也是如此。

更进一步，在[第五篇 OverlayFS](https://quant67.com/post/containers/05-overlayfs/overlayfs.html) 里我们会看到，容器镜像本身就是只读层 + 可写层的叠加。只读根文件系统只是顶层的额外保护。

---

## 九、完整的挂载流程

把所有东西拼起来，容器启动时的挂载操作是这样的顺序：

```c
// === 在 clone(CLONE_NEWNS | ...) 之后的子进程中 ===

// 1. 切断挂载传播
mount("", "/", "", MS_PRIVATE | MS_REC, NULL);

// 2. bind mount rootfs（让它成为挂载点）
mount(rootfs, rootfs, NULL, MS_BIND | MS_REC, NULL);

// 3. 创建 .old_root，执行 pivot_root
mkdir(rootfs "/.old_root", 0700);
pivot_root(rootfs, rootfs "/.old_root");
chdir("/");

// 4. 挂载伪文件系统
mount("proc",  "/proc", "proc",  MS_NOSUID | MS_NODEV | MS_NOEXEC, NULL);
mount("sysfs", "/sys",  "sysfs", MS_NOSUID | MS_NODEV | MS_NOEXEC | MS_RDONLY, NULL);

// 5. 设置 /dev
mount("tmpfs", "/dev", "tmpfs", MS_NOSUID | MS_STRICTATIME, "mode=755");
mknod("/dev/null",  S_IFCHR | 0666, makedev(1, 3));
mknod("/dev/zero",  S_IFCHR | 0666, makedev(1, 5));
mknod("/dev/random",  S_IFCHR | 0444, makedev(1, 8));
mknod("/dev/urandom", S_IFCHR | 0444, makedev(1, 9));
mknod("/dev/tty",  S_IFCHR | 0666, makedev(5, 0));

// 6. tmpfs
mount("tmpfs", "/tmp", "tmpfs", MS_NOSUID | MS_NODEV, "mode=1777");
mount("tmpfs", "/run", "tmpfs", MS_NOSUID | MS_NODEV, "mode=755");

// 7. 卸载旧根
umount2("/.old_root", MNT_DETACH);
rmdir("/.old_root");

// 8. (可选) 只读根
mount("", "/", "", MS_REMOUNT | MS_RDONLY | MS_BIND, NULL);

// 9. exec
execve("/bin/sh", argv, envp);
```

注意顺序很重要：

- 步骤 1 必须在任何其他 mount 之前
- 步骤 7 必须在步骤 4-6 之后（否则 /proc 等还挂在旧根上）
- 步骤 8 必须在步骤 6 之后（否则 tmpfs 也会变成只读）

---

## 十、踩坑备忘

### 10.1 pivot_root: Invalid argument

最常见的错误。原因通常是：

```c
# new_root 不是挂载点 → 先 bind mount
mount(rootfs, rootfs, NULL, MS_BIND, NULL);

# new_root 和 put_old 不在同一个文件系统
# → put_old 必须在 new_root 之下

# 没在 mount namespace 里
# → 确保 clone() 加了 CLONE_NEWNS
```

### 10.2 umount: Device or resource busy

旧根可能有文件描述符还在引用它。用 `MNT_DETACH` 做 lazy umount：

```c
// 不用等所有引用释放，立即从挂载表移除
umount2("/.old_root", MNT_DETACH);
```

### 10.3 /proc 里还是宿主机的进程

要么忘了 `CLONE_NEWPID`，要么忘了重新挂载 `/proc`。两个都需要。

### 10.4 容器内 DNS 不工作

别忘了复制宿主机的 `/etc/resolv.conf` 到容器 rootfs：

```
cp /etc/resolv.conf rootfs/etc/resolv.conf
```

---

## 十一、和真正的容器运行时比较

我们这个 demo 和 runc（Docker / Kubernetes 使用的 OCI 运行时）相比还差什么？

|特性|我们的 demo|runc|
|---|---|---|
|pivot_root|是|是|
|Mount propagation|MS_PRIVATE|MS_SLAVE → MS_PRIVATE|
|/dev 设备|mknod|bind mount from host|
|/proc hidepid|否|是 (hidepid=2)|
|Masked paths|否|是 (/proc/kcore 等)|
|Read-only paths|否|是 (/proc/sys 等)|
|Cgroup namespace|否|是|
|OverlayFS rootfs|否|是|
|Seccomp filter|否|是|

runc 还会把一些敏感的 `/proc` 路径设为只读或用 tmpfs 遮蔽：

```
# runc 会 bind mount /dev/null 到这些路径，防止信息泄露
/proc/kcore  # 内核内存映像——泄露整个内核地址空间
/proc/keys  # 内核密钥环——可能包含其他容器的密钥
/proc/timer_list  # 内核定时器——可用于侧信道攻击
/proc/sched_debug  # 调度器调试信息——泄露宿主机进程列表
```

此外，runc 会把 `/proc/sys`、`/proc/bus`、`/proc/irq`、`/proc/acpi` 等路径设为只读，防止容器通过 `/proc` 接口修改内核参数。完整列表见 runc 的 `libcontainer/specconv/spec_linux.go`。

### 踩坑备忘：常见错误与排查

  
|症状|原因|解决方法|
|---|---|---|
|`pivot_root: Invalid argument`|new_root 不是挂载点|先 `mount --bind /newroot /newroot`|
|`pivot_root: Device or resource busy`|有进程的 cwd 还在旧 root|确保所有进程先 `chdir` 到新 root|
|`mount: permission denied` 挂载 `/proc`|没有 `MS_PRIVATE` 导致传播到宿主机后被拒|先执行 `mount("", "/", "", MS_PRIVATE \\| MS_REC, NULL)`|
|容器内 `ls /dev` 什么都没有|忘记挂载 `/dev` 为 tmpfs 并创建设备节点|参考本文第五节的设备节点清单|
|`exec format error`|rootfs 架构不匹配（比如 ARM rootfs 在 x86 上跑）|确认 rootfs 与宿主机 CPU 架构一致|

这些细节我们会在[第八篇安全加固](https://quant67.com/post/containers/08-security/security.html)中详细讨论。

---

## 十二、代码和文件清单

本文的所有代码：

 
|文件|说明|
|---|---|
|`examples/containers/03-rootfs/pivot_root_demo.c`|完整的 pivot_root 容器演示|
|`examples/containers/03-rootfs/chroot_escape.c`|chroot 逃逸演示|
|`examples/containers/03-rootfs/prepare_rootfs.sh`|Alpine rootfs 准备脚本|
|`examples/containers/03-rootfs/Makefile`|编译和运行|

快速开始：

```
cd examples/containers/03-rootfs
make  # 编译
make setup  # 下载并准备 Alpine rootfs（需要 root 和网络）
make run  # 运行容器（需要 root）
make run-escape  # 运行 chroot 逃逸演示
```

---

文件系统是容器的地基。有了 mount namespace + pivot_root，容器进程终于真正”脚踏实地”了 — 踩在自己的 rootfs 上，看不到宿主机的任何文件。

但光有隔离还不够。现在的容器没有资源限制 — 一个容器可以吃掉所有 CPU、所有内存、所有 I/O。

下一篇，我们用 cgroups v2 给容器戴上枷锁 — [Cgroups v2：给容器的资源账本](https://quant67.com/post/containers/04-cgroups/cgroups.html)。

## 同主题继续阅读

把当前热点继续串成多页阅读，而不是停在单篇消费。

2026-04-08 · linux / containers

### [【从零造容器】Seccomp-BPF 与 Capabilities：容器安全的两道防线](https://quant67.com/post/containers/08-security/security.html)

你的容器能调用 reboot()。是的，现在就能。除非有人拦住它。Capabilities 拆分 root 权限，Seccomp-BPF 过滤系统调用——两道防线，缺一不可。本文用 C 代码拆解这两套机制，看看 Docker 到底替你挡住了什么。

2026-04-01 · linux / containers

### [【从零造容器】Linux Namespaces：用 50 行 C 隔离一个进程](https://quant67.com/post/containers/01-namespaces/namespaces.html)

容器不是魔法。它就是几个系统调用。本文用 C 从 clone() 开始，逐个开启 PID/UTS/Mount/IPC namespace，看隔离到底是怎么回事。50 行代码，你就拥有了一个'容器'的雏形。

2026-04-01 · linux / containers

### [【从零造容器】Network Namespace：给你的进程接上虚拟网线](https://quant67.com/post/containers/02-netns/netns.html)

上一篇我们用 clone() 隔离了 PID、主机名和挂载点，但那个'容器'连 lo 都 ping 不通。本文从 CLONE_NEWNET 出发，用 veth pair + bridge + iptables MASQUERADE，一步步给容器接上网。

2026-04-03 · linux / containers

### [【从零造容器】Cgroups v2：让容器不能吃掉整台机器](https://quant67.com/post/containers/04-cgroups/cgroups.html)

你给容器设了 512MB 内存限制，结果宿主机上的数据库被 OOM-kill 了。Cgroups 不是'加个限制'那么简单 — v1 的设计是个历史错误，v2 才是正确答案。本文用 C 代码从 mkdir 开始，手动创建 cgroup，设 CPU/内存/IO 限制，压测，看它怎么把进程关进笼子。