---
title: 容器运行时深度解析
category: concepts
tags: [云原生, 容器, 运行时, Linux内核, OCI]
aliases: [容器运行时, 从零造容器]
relationships:
  - target: "[[concepts/linux-namespace-cgroups]]"
    type: extends
  - target: "[[concepts/overlayfs-container-images]]"
    type: uses
  - target: "[[concepts/seccomp-capabilities]]"
    type: uses
  - target: "[[entities/containerd-runtime]]"
    type: related_to
  - target: "[[entities/runc-oci-reference]]"
    type: related_to
  - target: "[[concepts/container-vs-microvm]]"
    type: contradicts
  - target: "[[concepts/container-network-benchmarking]]"
    type: uses
source_dir: 云原生/容器运行时/从零造容器系列
source_files: [【从零造容器】1 Linux Namespaces：用 50 行 C 隔离一个进程.md, 【从零造容器】2 Network Namespace：给你的进程接上虚拟网线.md, 【从零造容器】3 Mount Namespace 与 pivot_root：构建容器文件系统.md, 【从零造容器】6 用 Go 组装迷你容器运行时：把积木拼起来.md, 【从零造容器】7 OCI 规范兼容：让迷你运行时说标准语言.md, 从零造容器系列文章.md]
summary: 容器不是发明而是拼装——8种Namespace隔离视图+pivot_root构建独立rootfs+veth/bridge/NAT组网+cgroups限制资源+OverlayFS分层镜像+Go组装运行时+OCI规范标准化接口；四阶段递进：内核积木→存储组装→安全加固→性能对比
provenance:
  extracted: 0.78
  inferred: 0.20
  ambiguous: 0.02
base_confidence: 0.80
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: core
created: 2026-06-02
updated: 2026-06-13
---

# 容器运行时深度解析

"容器不是魔法，它是一堆 Linux 内核特性的组合拳。"——Mount Namespace 2002年就有了，比 Docker (2013) 早11年。容器技术不是发明，是**拼装**。

## 核心观点

- **容器 = Namespace(可见性隔离) + Cgroup(资源限制) + pivot_root(文件系统) + OverlayFS(分层存储) + Seccomp/Capability(安全)**——五个内核特性的组合。 ^[inferred]
- **50行C代码**就能创建有 PID/UTS/Mount/IPC 隔离的进程，但生产级运行时(runc)需要15000行处理各种边缘情况。
- **PID 1 是容器最大的坑**：只接受显式注册的信号处理、收养孤儿进程、PID1退出整个namespace被杀。Docker `--init` (tini) 和 Kubernetes zombie 进程问题都源于此。
- **chroot 不是安全边界**：10行C就能逃逸（第二次chroot+chdir向上走）。pivot_root 才是容器根文件系统的正确实现。
- **容器进程与宿主机共享内核**：300+个syscall中不少能直接搞崩机器——这就是 [[concepts/seccomp-capabilities]] 和 [[concepts/container-vs-microvm]] 存在的原因。

## 四阶段递进结构

| 阶段 | 篇目 | 内容 | 依赖 |
|------|------|------|------|
| **第一阶段：内核积木** | #01-04 | Namespace/Network/Mount+Cgroups | 无依赖 |
| **第二阶段：存储与组装** | #05-07 | OverlayFS/Go运行时/OCI规范 | 依赖#01-04 |
| **第三阶段：安全加固** | #08-09 | Seccomp+Capability/User Namespace+Rootless | 最好看完#01-07 |
| **第四阶段：性能与对比** | #10-12 | microVM/网络性能/runc源码 | #10看全文,#11看#02,#12看#06/07 |

## Namespace 体系（容器可见性隔离）

### 8种 Namespace

| Namespace | 内核版本 | 隔离内容 | 对容器意义 |
|-----------|---------|----------|-----------|
| **Mount** | 2.4.19 (2002) | 文件系统挂载点 | 独立rootfs |
| **UTS** | 2.6.19 (2006) | 主机名和NIS域名 | 独立hostname |
| **IPC** | 2.6.19 (2006) | System V IPC/POSIX消息队列 | IPC隔离 |
| **PID** | 2.6.24 (2008) | 进程ID编号空间 | 独立PID |
| **Network** | 2.6.29 (2009) | 网络栈/接口/路由/iptables | 独立网络 |
| **User** | 3.8 (2013) | 用户/组ID | Rootless容器基础 |
| **Cgroup** | 4.6 (2016) | Cgroup视图 | Cgroup层级隔离 |
| **Time** | 5.6 (2020) | 系统时钟 | 时间隔离 |

### 三个系统调用

| 调用 | 功能 | 典型用途 |
|------|------|----------|
| `clone()` | 创建子进程+放入新Namespace | 容器运行时创建容器进程 |
| `unshare()` | 将当前进程移入新Namespace | 调试/实验 |
| `setns()` | 加入已有Namespace | `nsenter`/`docker exec`底层 |

### PID 1 陷阱

PID 1 在PID Namespace中有三个特殊语义：
1. **只接受显式注册的信号处理**：SIGTERM默认行为不是终止，而是被忽略 → `docker stop` 挂住
2. **收养孤儿进程**：父进程退出的子进程被PID1收养 → 必须`wait()`否则zombie堆积
3. **PID 1退出 → 整个Namespace被杀**：所有进程一起终止

**解法**：Docker用tini（`--init`）作为PID1；Kubernetes依赖容器进程自己做好信号处理和zombie回收。

## 容器网络构建

新 Network Namespace 只有 `lo`（DOWN状态），空路由表，空iptables。从空网络栈到互联网需要：

1. **veth pair**：虚拟以太网线，一端在容器(ns eth0)，一端在宿主机
2. **Bridge (br0)**：二层虚拟交换机，相当于Docker的`docker0`
3. **iptables MASQUERADE**：NAT源地址替换，让容器包看起来来自宿主机IP

**路径**：eth0 → veth pair → bridge → netfilter/NAT → 物理网卡，多了2-4次协议栈遍历。 ^[inferred]

**bridge-nf-call-iptables 设计缺陷**：包两次经过netfilter（bridge层+IP层），增加不必要的开销。

## pivot_root 与文件系统

chroot 逃逸方式：第二次`chroot()` + `chdir("..")` 向上走穿越边界。10行C即可逃逸。

pivot_root 交换整个挂载树的根：旧根变为子挂载点可umount，真正隔离。要求 `new_root` 必须是挂载点（需先bind mount到自身）。

**systemd默认根挂载为shared**：不设 `MS_PRIVATE | MS_REC` 则子Namespace的mount事件会传播回宿主机。runc先设MS_SLAVE再设MS_PRIVATE处理内核版本edge case。

**runc安全加固**：bind mount `/dev/null` 到 `/proc/kcore`, `/proc/keys` 等敏感路径防止信息泄露。

## 运行时组装与OCI规范

### miniruntime vs runc

| 维度 | miniruntime | runc |
|------|-------------|------|
| 代码量 | ~500行 | ~15000行 |
| 语言 | Go | Go+C(nsenter) |
| 功能 | 基本容器生命周期 | OCI完整规范+安全+边缘情况 |
| init机制 | reexec(/proc/self/exe) | C bootstrap + Go standard |

**create和start分开不只是规范形式**：编排系统利用空档做cgroup/网络/seccomp配置。

### OCI Runtime Specification

两个规范：Image Spec + Runtime Spec。config.json 是容器蓝图：ociVersion/process/root/hostname/mounts/linux。

**Hooks机制**：createRuntime(GPU/网络)、poststart(监控通知)、poststop(清理)。Hook通过stdin传递容器state JSON。

**实现兼容性**：runc、crun(C)、youki(Rust)、kata-containers(microVM)都遵循同一OCI Runtime Spec。

### 容器运行时五层安全防线

Namespace(视图隔离) + Cgroup(资源限制) + Capabilities(权限拆分) + Seccomp-BPF(syscall过滤) + AppArmor/SELinux(MAC强制访问) → 五层纵深防御。 ^[inferred]

## 未解问题

- namespace泄漏、cgroup残留、挂载点残留——这些是容器运行时最常见的bug，但如何系统化检测和预防？
- PID 1的信号处理和zombie回收在不同语言runtime中的行为差异？
- pivot_root失败但bind mount已完成时的"幽灵挂载点"如何自动恢复？


## 延伸阅读

综合分析：[[synthesis/cloud-native-infrastructure-landscape]]

## 来源

- 从零造容器系列 #01-07 — 内核积木到OCI规范的递进教学
- [[summaries/k8s-terminology-cheatsheet]] — Namespace/Cgroup术语定义