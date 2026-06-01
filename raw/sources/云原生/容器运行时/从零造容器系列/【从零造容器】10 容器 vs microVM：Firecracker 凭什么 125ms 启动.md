这个系列到现在已经实现了一个容器运行时。但有一个根本性的问题我们一直回避：**namespace 隔离到底有多强？**

答案是：**不够强**。

容器共享内核。一个内核漏洞就能从容器逃逸到宿主机。2019 年的 CVE-2019-5736（runc 逃逸），2022 年的 CVE-2022-0185（user namespace 堆溢出），2024 年的多个 eBPF 逃逸漏洞——都证明了这一点。

所以 AWS 做了 Firecracker：一个极简的 microVM，用**硬件虚拟化**代替 namespace 隔离。每个 Lambda 函数跑在自己的虚拟机里，有自己的内核。125ms 启动，5MB 内存开销。

这篇文章拆解两种隔离模型的本质差异。

---

## 一、隔离模型对比

```
容器 (namespace)  microVM (KVM)
┌─────────────────┐  ┌─────────────────┐
│  Container A  │  │  VM A  │
│  ┌───────────┐  │  │  ┌───────────┐  │
│  │ App  │  │  │  │ App  │  │
│  ├───────────┤  │  │  ├───────────┤  │
│  │ libc  │  │  │  │ libc  │  │
│  └───────────┘  │  │  ├───────────┤  │
│  │  │  │ Guest  │  │
├─────────────────┤  │  │ Kernel  │  │
│  Host Kernel  │ ← 共享  │  └───────────┘  │
│  (单点故障)  │  ├─────────────────┤
└─────────────────┘  │  KVM/Host Kernel │
  └─────────────────┘
```

关键区别：

|维度|容器|microVM|
|---|---|---|
|隔离机制|namespace + cgroup + seccomp|硬件虚拟化 (VT-x/AMD-V)|
|内核共享|是（单点故障）|否（每个 VM 独立内核）|
|攻击面|整个宿主内核 syscall 接口|VMX 指令集 + virtio 设备|
|启动时间|< 100ms|~125ms (Firecracker)|
|内存开销|~几 MB（共享内核）|~5MB + guest kernel|
|适用场景|可信工作负载、开发环境|多租户、不可信代码|

---

## 二、KVM：Linux 内核里的 hypervisor

Linux 内核从 2.6.20（2007）开始内置 KVM（Kernel-based Virtual Machine）。KVM 把 Linux 内核变成一个 Type-1 hypervisor。

用 KVM 创建虚拟机只需要几个 ioctl：

```c
#include <linux/kvm.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <sys/mman.h>

int main(void) {
  // 1. 打开 KVM 设备
  int kvm_fd = open("/dev/kvm", O_RDWR);

  // 2. 创建虚拟机
  int vm_fd = ioctl(kvm_fd, KVM_CREATE_VM, 0);

  // 3. 分配 guest 内存
  void *mem = mmap(NULL, 0x1000, PROT_READ | PROT_WRITE,
  MAP_SHARED | MAP_ANONYMOUS, -1, 0);

  struct kvm_userspace_memory_region region = {
  .slot = 0,
  .guest_phys_addr = 0x1000,
  .memory_size = 0x1000,
  .userspace_addr = (unsigned long)mem,
  };
  ioctl(vm_fd, KVM_SET_USER_MEMORY_REGION, &region);

  // 4. 创建 vCPU
  int vcpu_fd = ioctl(vm_fd, KVM_CREATE_VCPU, 0);

  // 5. 设置寄存器，加载 guest 代码
  struct kvm_regs regs;
  ioctl(vcpu_fd, KVM_GET_REGS, &regs);
  regs.rip = 0x1000;  // guest 入口地址
  regs.rflags = 0x2;
  ioctl(vcpu_fd, KVM_SET_REGS, &regs);

  // 把 guest 代码复制到 guest 内存
  // ...

  // 6. 运行！
  for (;;) {
  ioctl(vcpu_fd, KVM_RUN, NULL);
  // 处理 VM exit
  }
}
```

这就是一个最简的虚拟机。当然，要跑 Linux 内核需要设置更多东西：GDT、页表、中断控制器……但核心就是这几个 ioctl。

---

传统虚拟机（QEMU）模拟完整 PC：BIOS、ACPI、PCI 总线、IDE/SATA 控制器、VGA 显卡……这些对服务器容器毫无意义，但 QEMU 启动时必须初始化它们。

Firecracker 的做法：**全部砍掉**。

|组件|QEMU|Firecracker|
|---|---|---|
|BIOS/UEFI|有|无（直接 Linux boot protocol）|
|ACPI 表|有|无|
|PCI 总线|有|无（用 virtio-mmio）|
|显卡|有（VGA）|无|
|USB|有|无|
|音频|有|无|
|块设备|IDE/SCSI/virtio-blk-pci|virtio-blk-mmio|
|网络|e1000/virtio-net-pci|virtio-net-mmio|
|串口|16550A|精简版串口|

virtio-mmio 是关键：它跳过 PCI 总线枚举，设备直接映射到固定内存地址。guest kernel 启动时不需要先 probe 总线、读取 config space、分配 BAR、处理中断路由，再决定驱动绑定谁。对服务器工作负载来说，这一整套”发现硬件”流程都是纯启动税。Firecracker 直接告诉 guest：“磁盘在这，网卡在这”，省掉的就是几十毫秒级的初始化噪音。

### 启动时间拆解

> **测试环境**：以下数据来自 AWS i3.metal 实例（Intel Xeon E5-2686 v4, 64 vCPU, 关闭超线程），Linux 5.10, Firecracker v1.1。不同硬件和内核版本结果会有差异——在 ARM Graviton2 上，guest kernel boot 阶段约快 15%。

Firecracker 的 125ms 启动时间花在哪？

```
VMM 初始化（创建 KVM VM、设置内存）:  ~5ms
加载 guest kernel 到内存:  ~10ms
Guest kernel boot (到 init):  ~80ms
init 进程启动:  ~30ms
───────────────────────────────────────────
总计:  ~125ms
```

瓶颈在 **guest kernel boot**。Firecracker 为此做了优化： - 使用精简的内核配置（去掉不需要的驱动） - 支持 kernel boot 参数 `reboot=k panic=1`（异常直接退出，不挂起） - 共享内存的 balloon driver 按需回收空闲页（代价是回收时 guest 侧会有一次抖动，不适合极端 latency-sensitive 场景）

### 代码量对比

| |QEMU|Firecracker|
|---|---|---|
|语言|C|Rust|
|代码行数|~200 万|~5 万|
|安全漏洞历史|数百个 CVE|个位数|

Firecracker 用 Rust 写不是为了性能——它为了**安全**。更少的代码 + 内存安全语言 = 更小的攻击面。

为什么这对 VMM 特别重要？VMM 直接处理 guest 的 virtio 请求——本质上是在解析不可信输入。QEMU 的 CVE 历史里，大量是设备模拟代码的缓冲区溢出和 use-after-free。Rust 的所有权模型在编译期消除了这两类问题。Firecracker 的 unsafe 代码块被严格限制在 KVM ioctl 调用和 MMIO 地址映射（约占总代码 2%），每个 unsafe 块都有注释说明为什么需要以及不变量是什么。

---

## 四、性能对比

### 启动时间

|方案|冷启动时间|
|---|---|
|Docker (runc)|~300ms（含镜像加载）|
|Docker (runc, 镜像已缓存)|~100ms|
|crun|~50ms|
|Firecracker|~125ms|
|QEMU (最小配置)|~800ms|
|Cloud Hypervisor|~100ms|

Firecracker 的 125ms 与容器在同一量级。对 Lambda 这样的 serverless 场景，这个启动时间完全可接受。

### 内存开销

|方案|最小内存开销|
|---|---|
|容器|~2MB（共享宿主内核）|
|Firecracker|~5MB VMM + guest kernel 内存|
|QEMU|~30MB+|

Firecracker 的 5MB 开销包括 VMM 进程本身和 virtio 队列。guest kernel 最少需要约 20MB，但可以用 balloon driver 按需回收。

### I/O 性能

这是 microVM 相对容器的最大劣势：

```
容器: app → syscall → host kernel → 设备
VM:  app → syscall → guest kernel → virtio → VM exit → host kernel → 设备
```

每次 I/O 操作，microVM 多了一次 guest kernel 处理和一次 VM exit。VM exit 的代价是 ~1-5μs，对高频小包场景（比如 Redis）影响显著。

Firecracker 通过 **vhost-net** 减少 VM exit：网络包直接在内核空间从 host 转发到 guest 的 virtio 队列，跳过 VMM 进程的用户态。

---

## 五、安全模型对比

### 容器的攻击面

容器进程通过系统调用直接与宿主内核交互。即使有 seccomp 过滤（只允许 ~260 个 syscall），每个 syscall 都是潜在的攻击入口。内核的 syscall 处理代码有数百万行。

```
容器进程 → seccomp filter → 宿主内核 (数百万行代码)
  ↓
  内核漏洞 = 逃逸
```

### microVM 的攻击面

VM 进程与 KVM 交互，KVM 处理的是 **VMX 指令集**（Intel VT-x），比 syscall 接口小得多。virtio 设备的攻击面也远小于整个 syscall 接口。

```
Guest 进程 → Guest 内核 → VM exit → KVM (数千行代码)
  ↓
  KVM 漏洞 = 逃逸
```

KVM 的代码量约 5 万行，远小于整个内核的 syscall 处理路径。

### Kata Containers：两全其美？

Kata Containers 把 OCI 容器接口和 microVM 隔离结合起来：外部看起来是容器（兼容 Kubernetes），内部是 microVM：

```
kubelet → containerd → kata-runtime → Firecracker/QEMU/Cloud Hypervisor
  ↓
  每个 Pod 一个 VM
```

它解决的是”接口兼容”问题，不是”把 VM 变成和容器一样轻”。你依然要付 guest kernel、guest agent、virtio-fs/9p 共享目录的成本——冷启动数百毫秒，内存底线几十 MB 起跳。换来的是 Kubernetes 不用改 API，安全边界更接近 VM。对多租户场景（如公有云），这笔账是值得的。

---

## 六、选择指南

|场景|推荐方案|原因|
|---|---|---|
|开发环境|容器|快、轻、够用|
|CI/CD|容器|速度优先|
|单租户生产|容器 + seccomp|性能好，安全足够|
|多租户 SaaS|microVM (Firecracker)|不可信代码需要硬隔离|
|Serverless|microVM|AWS Lambda 的选择|
|边缘计算|容器或 WASM|资源受限|

没有银弹。容器和 microVM 是不同的权衡点。

下一篇，我们回到容器的实际性能问题 — [容器网络性能真相](https://quant67.com/post/containers/11-network-perf/network-perf.html)。

## 相关阅读

- [io_uring 核心概念](https://quant67.com/post/io_uring/01-core-concepts.html) — I/O 模型与容器/VM 性能直接相关
- [unsafe Rust](https://quant67.com/post/rust/unsafe-rust/unsafe-rust.html) — Firecracker 用 Rust 写，但 virtio 设备模拟需要 unsafe
- [Seccomp-BPF 与 Capabilities](https://quant67.com/post/containers/08-security/security.html) — 容器安全的软件层方案

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

2026-04-03 · linux / containers

### [【从零造容器】Cgroups v2：让容器不能吃掉整台机器](https://quant67.com/post/containers/04-cgroups/cgroups.html)

你给容器设了 512MB 内存限制，结果宿主机上的数据库被 OOM-kill 了。Cgroups 不是'加个限制'那么简单 — v1 的设计是个历史错误，v2 才是正确答案。本文用 C 代码从 mkdir 开始，手动创建 cgroup，设 CPU/内存/IO 限制，压测，看它怎么把进程关进笼子。