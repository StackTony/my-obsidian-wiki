你的容器能调用 `reboot()`。

不是假设，不是理论。你现在就可以写一个 C 程序，编译，放进 `docker run` 里跑。如果没有人拦住它——你的宿主机就重启了。

“但容器不是隔离的吗？” Namespace 隔离的是**可见性**——进程看不到外面的东西。Cgroup 隔离的是**资源**——进程用不了太多 CPU 和内存。但是，**进程能调用哪些系统调用**，这两个机制都管不了。

一个容器进程仍然和宿主机共享同一个内核。每一个 `syscall` 指令都直接打到宿主机内核上。内核有 300 多个系统调用，其中不少能直接搞崩整台机器：`reboot()`、`kexec_load()`、`mount()`、`swapon()`……

所以我们需要两道额外的防线：

1. **Capabilities** — 拆分 root 的超能力，只给容器需要的那几个
2. **Seccomp-BPF** — 在系统调用入口放一个过滤器，逐个审查

这是本系列第八篇。[第一篇](https://quant67.com/post/containers/01-namespaces/namespaces.html)我们用 `clone()` 创建了 namespace 隔离。那只是看不到外面。这一篇，我们要确保容器**做不到**不该做的事。

> 本文所有代码在 `examples/containers/08-seccomp/` 目录，`make` 即可编译。测试环境：Linux 6.x, x86_64。

---

## 一、Linux Capabilities：把 root 劈成碎片

### 旧模型：全有或全无

传统 UNIX 的权限模型极其粗暴——进程的 effective UID 是 0 就是 root，拥有一切权力；不是 0 就是普通用户，什么特权操作都做不了。

问题在于，很多程序只需要 root 的一小部分能力。`ping` 只需要发 raw socket，`ntpd` 只需要调整系统时钟，`nginx` 只需要绑定 80 端口。但在旧模型下，它们要么以 root 运行（获得所有特权），要么无法工作。

这就是 Capabilities 要解决的问题。

### 37+ 个独立能力

从 Linux 2.2 开始，内核把 root 的权限拆成了几十个独立的 capability。每个进程有三组 capability 位图：

- **Permitted** — 进程”允许拥有”的能力上限
- **Effective** — 进程当前”生效”的能力
- **Inheritable** — 通过 `execve()` 传递给子程序的能力

几个关键 capability：

  
|Capability|允许做什么|容器里需要吗？|
|---|---|---|
|`CAP_NET_ADMIN`|修改路由表、防火墙规则、网络接口配置|通常不需要|
|`CAP_SYS_ADMIN`|mount、pivot_root、设置 hostname、管理 cgroup……|极其危险|
|`CAP_MKNOD`|创建设备文件|Docker 默认保留|
|`CAP_NET_BIND_SERVICE`|绑定 1024 以下端口|通常需要|
|`CAP_SYS_PTRACE`|`ptrace()` 其他进程|调试时需要|
|`CAP_NET_RAW`|使用 raw socket（ping 需要）|Docker 默认保留|
|`CAP_SYS_TIME`|修改系统时钟|绝对不需要|
|`CAP_SYS_BOOT`|调用 `reboot()`|绝对不需要|

完整列表见 `man 7 capabilities`，截至 Linux 6.x 有 41 个。

### Docker 的默认 capability 集

Docker 默认只保留 14 个 capability，丢弃其余所有的。保留的包括：

```
CAP_CHOWN, CAP_DAC_OVERRIDE, CAP_FSETID, CAP_FOWNER,
CAP_MKNOD, CAP_NET_RAW, CAP_SETGID, CAP_SETUID,
CAP_SETFCAP, CAP_SETPCAP, CAP_NET_BIND_SERVICE,
CAP_SYS_CHROOT, CAP_KILL, CAP_AUDIT_WRITE
```

注意这里面**没有** `CAP_SYS_ADMIN`、`CAP_NET_ADMIN`、`CAP_SYS_PTRACE`、`CAP_SYS_TIME`、`CAP_SYS_BOOT`。

这意味着容器进程即使是 root（UID 0），也不能 mount 文件系统、修改路由表、ptrace 其他进程、改系统时钟或者重启机器。

可以手动调整：

```
# 丢掉所有 capability，只留网络
docker run --cap-drop=ALL --cap-add=NET_BIND_SERVICE nginx

# 给容器完整 root 权限（千万别在生产环境用）
docker run --privileged nginx
```

`--privileged` 就是把所有 capability 全部加回来，同时禁用 seccomp。等于拆掉两道防线。

### 用 C 操作 Capabilities

```c
#include <sys/capability.h>
#include <stdio.h>

int main() {
  // 获取当前进程的 capabilities
  cap_t caps = cap_get_proc();
  if (!caps) {
  perror("cap_get_proc");
  return 1;
  }

  // 打印可读格式
  char *text = cap_to_text(caps, NULL);
  printf("Current caps: %s\n", text);

  cap_free(text);
  cap_free(caps);
  return 0;
}
```

编译需要 `libcap`：`gcc -o show_caps show_caps.c -lcap`

更底层的方式是直接用 `capget()` / `capset()` 系统调用：

```c
#include <sys/syscall.h>
#include <linux/capability.h>
#include <unistd.h>
#include <stdio.h>
#include <string.h>

int main() {
  struct __user_cap_header_struct hdr = {
  .version = _LINUX_CAPABILITY_VERSION_3,
  .pid = 0,  // 0 = 当前进程
  };
  struct __user_cap_data_struct data[2];
  memset(data, 0, sizeof(data));

  if (syscall(SYS_capget, &hdr, data) == -1) {
  perror("capget");
  return 1;
  }

  printf("Effective[0]: 0x%08x\n", data[0].effective);
  printf("Effective[1]: 0x%08x\n", data[1].effective);
  printf("Permitted[0]: 0x%08x\n", data[0].permitted);
  printf("Permitted[1]: 0x%08x\n", data[1].permitted);

  return 0;
}
```

### CAP_SYS_ADMIN：新的 root

`CAP_SYS_ADMIN` 是 capability 体系里最大的设计失败。它控制的操作包括：

- `mount()` / `umount()`
- `pivot_root()`
- `sethostname()` / `setdomainname()`
- `quotactl()`
- `ioprio_set()`
- `keyctl()`
- 部分 `prctl()` 操作
- `bpf()` 的部分功能
- ……

太多了。任何内核开发者在给新功能做权限检查时，如果不确定该用哪个 capability，就往 `CAP_SYS_ADMIN` 里塞。结果它变成了一个”什么都管”的垃圾桶。

拥有 `CAP_SYS_ADMIN` 的容器，几乎等同于拥有宿主机 root。这就是为什么 Docker 默认不给它。

---

Seccomp（Secure Computing Mode）最早出现在 Linux 2.6.12（2005 年），是给 grid computing 设计的——你把不可信代码跑在一个只能使用 4 个系统调用的沙箱里：

- `read()`
- `write()`
- `exit()`（后来加了 `exit_group()`）
- `sigreturn()`

就这样。任何其他系统调用，进程直接被 `SIGKILL`。

```c
#include <linux/seccomp.h>
#include <sys/prctl.h>

// 进入严格模式 — 只能 read/write/exit/sigreturn
prctl(PR_SET_SECCOMP, SECCOMP_MODE_STRICT);
```

这对容器来说完全不可用。一个正常的程序至少需要 `mmap`、`brk`、`open`、`close`、`stat`……strict mode 出生就被判了死刑。

但 seccomp 的思想是对的：**在系统调用入口放一个看门人**。只是需要一个更灵活的方式来定义”谁能进谁不能进”。

---

## 三、Seccomp-BPF：灵活的系统调用过滤器

2012 年，Linux 3.5 引入了 Seccomp-BPF（也叫 seccomp mode 2）。它用 BPF（Berkeley Packet Filter）程序来做系统调用过滤。

### BPF 在这里做什么

BPF 原本是为网络包过滤设计的（`tcpdump` 用的就是它）。它是一个简单的虚拟机，有寄存器、条件跳转和算术运算。Seccomp-BPF 借用了这台虚拟机，但输入不再是网络包，而是一个描述系统调用的结构体：

```c
struct seccomp_data {
  int  nr;  // 系统调用号
  __u32 arch;  // 架构（x86_64、arm64 等）
  __u64 instruction_pointer;  // 调用者的 RIP
  __u64 args[6];  // 系统调用的 6 个参数
};
```

BPF 程序检查这些字段，然后返回一个动作：

|动作|效果|
|---|---|
|`SECCOMP_RET_ALLOW`|放行，正常执行|
|`SECCOMP_RET_KILL`|立即杀死进程（SIGSYS）|
|`SECCOMP_RET_KILL_PROCESS`|杀死整个线程组|
|`SECCOMP_RET_ERRNO`|不执行系统调用，返回指定的 errno|
|`SECCOMP_RET_TRACE`|通知 ptrace tracer|
|`SECCOMP_RET_LOG`|放行但记录日志（audit log）|
|`SECCOMP_RET_TRAP`|发送 SIGSYS 信号（可以 catch）|

![Seccomp-BPF 过滤流程](https://quant67.com/post/containers/08-security/seccomp-filter-flow.svg)

### 安装过滤器

用 `prctl()` 或 `seccomp()` 系统调用安装过滤器：

```c
#include <linux/seccomp.h>
#include <linux/filter.h>
#include <linux/audit.h>
#include <sys/prctl.h>

// BPF 过滤程序：禁止 mount() 和 reboot()
struct sock_filter filter[] = {
  // 加载系统调用号到累加器
  BPF_STMT(BPF_LD | BPF_W | BPF_ABS,
  offsetof(struct seccomp_data, nr)),

  // 如果是 mount (165)，跳到 ERRNO
  BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_mount, 1, 0),
  // 如果是 reboot (169)，跳到 ERRNO
  BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_reboot, 0, 1),

  // 返回 ERRNO（EPERM）
  BPF_STMT(BPF_RET | BPF_K,
  SECCOMP_RET_ERRNO | (EPERM & SECCOMP_RET_DATA)),

  // 默认：放行
  BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),
};

struct sock_fprog prog = {
  .len = sizeof(filter) / sizeof(filter[0]),
  .filter = filter,
};

// 允许非特权进程设置 seccomp 过滤器
prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0);

// 安装过滤器
prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &prog);
```

`BPF_STMT` 和 `BPF_JUMP` 是经典 BPF 宏。看起来像汇编——因为它本质上就是在写虚拟机指令。每条指令有操作码、偏移量和立即数。

**关键点**：`PR_SET_NO_NEW_PRIVS` 是必须的。没有它，非 root 进程不能安装 seccomp 过滤器（否则你可以先设过滤器再 exec 一个 setuid 程序来提权）。

### 用 libseccomp 简化

手写 BPF 指令是原始人的做法。`libseccomp` 提供了高层 API：

```c
#include <seccomp.h>

int main() {
  // 创建过滤器上下文，默认动作是 ALLOW
  scmp_filter_ctx ctx = seccomp_init(SCMP_ACT_ALLOW);
  if (!ctx) return 1;

  // 禁止 mount()，返回 EPERM
  seccomp_rule_add(ctx, SCMP_ACT_ERRNO(EPERM),
  SCMP_SYS(mount), 0);

  // 禁止 reboot()，返回 EPERM
  seccomp_rule_add(ctx, SCMP_ACT_ERRNO(EPERM),
  SCMP_SYS(reboot), 0);

  // 禁止 kexec_load()，直接杀进程
  seccomp_rule_add(ctx, SCMP_ACT_KILL,
  SCMP_SYS(kexec_load), 0);

  // 加载过滤器到内核
  seccomp_load(ctx);
  seccomp_release(ctx);

  // 现在试试 mount...
  if (mount("none", "/mnt", "tmpfs", 0, NULL) == -1)
  perror("mount");  // 输出: mount: Operation not permitted

  return 0;
}
```

编译：`gcc -o seccomp_easy seccomp_easy.c -lseccomp`

`libseccomp` 在底下生成同样的 BPF 字节码，但你不需要手动算跳转偏移。Docker、Podman、containerd 都用它来实现 seccomp profile。

---

## 四、Docker 的默认 Seccomp Profile

Docker 默认启用一个 seccomp profile，大约阻止了 44 个系统调用（总共 300 多个里面的）。这个 profile 用 JSON 格式定义，你可以在 Moby 源码里找到 `default.json`。

### 被阻止的关键系统调用

 
|被阻止的系统调用|危险在哪里|
|---|---|
|`mount` / `umount2`|挂载文件系统，可以访问宿主机存储|
|`reboot`|重启宿主机|
|`kexec_load` / `kexec_file_load`|加载新内核并重启——绕过安全启动链|
|`bpf`|加载 eBPF 程序到内核——攻击面太大|
|`perf_event_open`|性能监控——可以泄露其他进程信息|
|`add_key` / `keyctl`|操作内核密钥环——可能泄露凭据|
|`init_module` / `finit_module`|加载内核模块——直接往内核注入代码|
|`delete_module`|卸载内核模块|
|`acct`|启用进程记账——写宿主机文件|
|`swapon` / `swapoff`|控制 swap——影响宿主机内存管理|
|`pivot_root`|改变根文件系统——逃逸工具|
|`unshare`|创建新 namespace（部分受限）|
|`clone`（带 `CLONE_NEWUSER`）|创建 user namespace——历史上大量提权漏洞的入口|

### 设计哲学

Docker 的 seccomp profile 不是”阻止已知危险的”，而是”只放行已知安全的”。不过因为默认动作是 ALLOW，所以它更像是一个黑名单。

为什么不用白名单？因为不同应用需要的系统调用差异太大。一个白名单要么太严（正常应用跑不起来），要么太松（和黑名单没区别）。

查看当前容器的 seccomp 状态：

```
# 容器内部
$ grep Seccomp /proc/self/status
Seccomp:  2
Seccomp_filters: 1
```

`Seccomp: 2` 表示 filter mode（0 = disabled，1 = strict，2 = filter）。

---

## 五、实战调试：为什么我的应用在容器里挂了

你写了一个应用，在宿主机上跑得好好的，一放进 Docker 就 crash 或者报 `Operation not permitted`。这是容器安全机制最常见的”副作用”。

### 第一步：先怀疑 Capabilities

```
# 在容器里查看当前 capabilities
$ cat /proc/self/status | grep Cap
CapInh: 0000000000000000
CapPrm: 00000000a80425fb
CapEff: 00000000a80425fb
CapBnd: 00000000a80425fb
CapAmb: 0000000000000000

# 解码
$ capsh --decode=00000000a80425fb
```

如果你的应用需要某个特权操作，先试试加 capability：

```
docker run --cap-add=SYS_PTRACE myapp  # 需要 ptrace
docker run --cap-add=NET_ADMIN myapp  # 需要修改网络
```

### 第二步：如果加了 capability 还是不行，怀疑 Seccomp

用 `strace` 找出哪个系统调用被阻止了：

```
# 方法一：在容器外用 strace 附加到容器进程
$ strace -f -p $(docker inspect --format '{{.State.Pid}}' mycontainer)

# 方法二：用 --security-opt 禁用 seccomp 测试
$ docker run --security-opt seccomp=unconfined myapp
# 如果这样能跑，说明确实是 seccomp 的问题
```

### 第三步：用 SECCOMP_RET_LOG 定位

如果你在写自定义过滤器，可以先用 `SECCOMP_RET_LOG` 代替 `SECCOMP_RET_ERRNO`。这样系统调用还是会执行，但每次都会记录到 audit log：

```
# 查看哪些系统调用触发了 seccomp
$ dmesg | grep seccomp
$ journalctl -k | grep seccomp
# 或者
$ cat /var/log/audit/audit.log | grep SECCOMP
```

日志里会显示系统调用号和进程信息：

```
audit: type=1326 audit(1650000000.000:100): auid=1000 uid=0 gid=0
  ses=1 pid=12345 comm="myapp" exe="/usr/bin/myapp" sig=0 arch=c000003e
  syscall=165 compat=0 ip=0x7f... code=0x7ffc0000
```

`syscall=165` 就是 `mount`。用 `ausyscall 165` 或查 `/usr/include/asm/unistd_64.h` 可以反查。

### 自定义 seccomp profile

如果默认 profile 太严格，可以自定义：

```
# 使用自定义 JSON profile
docker run --security-opt seccomp=my-profile.json myapp
```

JSON 格式和 Docker 默认的 `default.json` 一样。你可以从默认 profile 开始，按需加减规则。

真正实用的做法不是从空白 JSON 开始，而是从 Docker 默认 profile 复制一份，然后按 syscall 差集做增量：

```
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "architectures": ["SCMP_ARCH_X86_64"],
  "syscalls": [
    { "names": ["read", "write", "exit", "rt_sigreturn"], "action": "SCMP_ACT_ALLOW" },
    { "names": ["openat", "newfstatat", "mmap", "munmap", "brk"], "action": "SCMP_ACT_ALLOW" },
    { "names": ["mount", "reboot", "kexec_load"], "action": "SCMP_ACT_ERRNO" }
  ]
}
```

一个靠谱的裁剪流程：

1. 先用 `strace -f` 跑业务启动路径，拿到 syscall 集
2. 先用 `SCMP_ACT_LOG` / `SECCOMP_RET_LOG` 观察，不要一上来 `KILL`
3. 最后再把真正危险且确实不用的 syscall 改成 `ERRNO` 或 `KILL`

---

## 六、Seccomp-BPF vs eBPF：同源不同命

看到 BPF 这个名字，你可能会想：这和现在火爆的 eBPF 是什么关系？

它们确实同源——都从 Berkeley Packet Filter 演化而来，都运行在内核中的虚拟机上。但 2014 年之后它们走上了截然不同的道路：

  
| |Seccomp-BPF (cBPF)|eBPF|
|---|---|---|
|**BPF 版本**|经典 BPF（classic BPF）|扩展 BPF（extended BPF）|
|**寄存器**|2 个（A, X）|11 个（r0-r10）|
|**指令集**|~30 条指令|~100+ 条指令|
|**映射（Maps）**|无|支持多种数据结构|
|**尾调用**|不支持|支持|
|**Helper 函数**|不支持|可调用内核 helper|
|**用途**|系统调用过滤|网络、追踪、安全、调度……|
|**验证器**|简单（DAG 检查）|复杂（路径敏感分析）|
|**输入数据**|`struct seccomp_data`（固定）|可以访问各种内核数据结构|
|**谁在用**|Docker/Podman/容器运行时|Cilium, Falco, bpftrace, tc|

Seccomp-BPF 故意保持简单。它运行在系统调用的关键路径上，每次系统调用都要过一遍。如果过滤器太复杂，系统调用的性能就会受影响。经典 BPF 的简单性保证了过滤器的执行时间是有界的。

eBPF 则在另一个方向上疯狂进化——它已经变成了一个内核态的通用编程框架。更多关于 eBPF 的内容，参见 [eBPF：Linux 内核的隐藏武器](https://quant67.com/post/linux/ebpf/ebpf.html)。

**注意**：虽然内核内部已经把所有 cBPF 程序翻译成 eBPF 指令集执行，但 seccomp 的用户态 API 仍然只接受 cBPF 格式。你不能直接给 seccomp 写 eBPF 程序。

### 性能代价

Seccomp 过滤器在每次系统调用入口执行，所以有真实的性能开销。在一个典型的 Web 服务器上（~10万 次/秒 syscall）：

- **Docker 默认 profile（~240 条规则）**：~1-2% 额外 CPU 开销
- **极简 allow-list（~30 条规则）**：< 0.5% 开销
- **空 profile（无过滤）**：0 开销

对大多数服务来说这可以忽略。但如果你的程序是系统调用密集型的（比如大量小文件 IO），值得关注。

### Docker 默认 profile 到底禁了什么？

Docker 的默认 seccomp profile 用 `seccomp-tools` 可以可视化：

```
# 安装
$ gem install seccomp-tools

# 导出 Docker 默认 profile 并反编译
$ docker run --rm -it --security-opt seccomp=default.json alpine cat /proc/self/status | grep -i seccomp
Seccomp:  2  # 2 = SECCOMP_MODE_FILTER

# 在容器内查看过滤规则（需要 seccomp-tools）
$ seccomp-tools dump /bin/ls
```

简单总结：Docker 默认 profile 阻止约 44 个系统调用，主要分三类：

1. **内核管理**：`reboot`, `kexec_load`, `swapon/swapoff` — 直接搞崩宿主机
2. **文件系统**：`mount`, `umount2`, `pivot_root` — 逃逸容器的基础工具
3. **设备与内核模块**：`mknod`, `init_module`, `finit_module` — 加载恶意内核模块

---

## 七、两道防线的组合：纵深防御

Capabilities 和 Seccomp 不是互相替代的关系，它们保护不同的层面：

**Capabilities** 回答的是：“这个进程**有没有权限**做这件事？”

- 粒度是**能力类别**（网络、挂载、ptrace……）
- 检查发生在内核的各个子系统里
- 可以在运行时动态调整

**Seccomp-BPF** 回答的是：“这个进程**能不能发起**这个系统调用？”

- 粒度是**系统调用号 + 参数**
- 检查发生在系统调用入口，统一的拦截点
- 一旦安装就不能放松（只能加更严格的过滤器）

为什么需要两道？因为单独一道都有漏洞：

1. **只有 Capabilities，没有 Seccomp**：进程没有 `CAP_SYS_ADMIN`，内核不让它 `mount()`——但如果内核的 capability 检查有 bug 呢？Seccomp 在系统调用入口直接拦住，甚至不给内核执行到 capability 检查的机会。
    
2. **只有 Seccomp，没有 Capabilities**：seccomp 不阻止 `ioctl()`（因为太多设备驱动需要它），但某些 `ioctl` 操作需要 `CAP_NET_ADMIN`。去掉 capability 就能限制这些操作。
    

Docker 的做法是两者同时使用：

```
┌─────────────────────────────────────────────────┐
│  User Process  │
│  │
│  syscall(mount, ...)  │
│  │  │
│  ▼  │
│  ┌──────────────┐  │
│  │ Seccomp-BPF  │ ← 第一道：系统调用号 + 参数检查 │
│  │  Filter  │  mount → EPERM  │
│  └──────┬───────┘  │
│  │ (如果 ALLOW)  │
│  ▼  │
│  ┌──────────────┐  │
│  │ Capability  │ ← 第二道：能力检查  │
│  │  Check  │  需要 CAP_SYS_ADMIN  │
│  └──────┬───────┘  │
│  │ (如果有权限)  │
│  ▼  │
│  ┌──────────────┐  │
│  │ Kernel  │  执行实际操作  │
│  │  Subsystem  │  │
│  └──────────────┘  │
└─────────────────────────────────────────────────┘
```

这就是**纵深防御**（defense-in-depth）。每道防线都假设另一道可能失效。

在 Docker 的默认配置下，一个容器进程面对的安全边界是：

1. **Namespace** — 看不到宿主机的进程/网络/挂载（[第一篇](https://quant67.com/post/containers/01-namespaces/namespaces.html)）
2. **Cgroup** — 不能用光宿主机的 CPU/内存
3. **Capabilities** — 没有 root 的大部分特权
4. **Seccomp-BPF** — 44 个危险系统调用被阻止
5. **AppArmor/SELinux** — MAC 策略（这是另一个话题）

五层防线，全部需要被突破才能逃逸。这就是为什么容器逃逸漏洞是高价值的——它通常需要同时绕过多道机制。

---

## 八、动手实验

完整的示例代码在 `examples/containers/08-seccomp/` 下：

- `caps_demo.c` — 展示和操控 capabilities
- `seccomp_demo.c` — 安装 seccomp-BPF 过滤器，阻止特定系统调用

### Capabilities 实验

```
$ cd examples/containers/08-seccomp && make
$ sudo ./caps_demo
```

这个程序会： 1. 打印当前进程的所有 capabilities 2. 尝试一些特权操作（修改主机名、创建 raw socket） 3. 主动丢弃一些 capabilities 4. 再次尝试同样的操作——观察失败

### Seccomp 实验

这个程序会： 1. 安装一个 seccomp-BPF 过滤器，阻止 `mount()`、`reboot()`、`kexec_load()` 2. 尝试调用被阻止的系统调用——观察返回 `EPERM` 3. 验证正常的系统调用（`getpid()`、`write()` 等）不受影响

---

## 九、后面的路

Capabilities 和 Seccomp 解决了”容器进程不应该做什么”的问题。但还有一个更根本的问题：**容器为什么要以 root 运行？**

下一篇 [Rootless 容器](https://quant67.com/post/containers/09-rootless/rootless.html) 将探讨如何让整个容器运行时都以普通用户运行——不靠 capabilities 的精细控制，而是从一开始就不给 root。这是另一种思路，也是更彻底的思路。

## 相关阅读

- [Linux Namespaces：用 50 行 C 隔离一个进程](https://quant67.com/post/containers/01-namespaces/namespaces.html) — 隔离可见性的第一步
- [Rootless 容器](https://quant67.com/post/containers/09-rootless/rootless.html) — 不用 root 的终极方案
- [eBPF：Linux 内核的隐藏武器](https://quant67.com/post/linux/ebpf/ebpf.html) — Seccomp-BPF 的”远房表亲”

## 同主题继续阅读

把当前热点继续串成多页阅读，而不是停在单篇消费。

2026-05-10 · linux / security

### [【eBPF 系列】eBPF 安全监控：不改内核也能审计 syscall](https://quant67.com/post/linux/ebpf-security/ebpf-security.html)

Seccomp 只能说 yes or no，但攻击者早就学会了在 yes 里面做文章。是时候让 eBPF 接管安全审计了。

2026-04-02 · linux / containers

### [【从零造容器】Mount Namespace 与 pivot_root：构建容器文件系统](https://quant67.com/post/containers/03-rootfs/rootfs.html)

chroot 不是安全边界——10 行 C 就能逃出去。本文用 pivot_root 构建真正隔离的容器根文件系统：从 Alpine minirootfs 到设备节点，从 mount propagation 到只读根，一步步把容器的'地基'打牢。

2026-04-09 · linux / containers

### [【从零造容器】User Namespace 与 Rootless 容器：不需要 root 也能跑](https://quant67.com/post/containers/09-rootless/rootless.html)

容器运行时需要 root 权限？不一定。User namespace 让普通用户也能创建容器——容器内是 root，容器外是你自己。Podman 就是这么干的。但 rootless 不是免费午餐，限制比你想象的多。

2026-04-01 · linux / containers

### [【从零造容器】Linux Namespaces：用 50 行 C 隔离一个进程](https://quant67.com/post/containers/01-namespaces/namespaces.html)

容器不是魔法。它就是几个系统调用。本文用 C 从 clone() 开始，逐个开启 PID/UTS/Mount/IPC namespace，看隔离到底是怎么回事。50 行代码，你就拥有了一个'容器'的雏形。
