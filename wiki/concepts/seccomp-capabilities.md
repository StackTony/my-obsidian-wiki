---
title: Seccomp-BPF 与 Linux Capabilities
category: concepts
tags: [云原生, Linux, 安全, Seccomp, Capabilities, 容器安全]
aliases: [Seccomp, Capabilities, 容器安全防线]
relationships:
  - target: "[[concepts/container-runtime-deep-dive]]"
    type: related_to
  - target: "[[concepts/linux-lock-mechanisms]]"
    type: related_to
  - target: "[[concepts/k8s-security]]"
    type: related_to
  - target: "[[concepts/container-vs-microvm]]"
    type: contradicts
source_dir: 容器运行时/从零造容器系列
source_files: [【从零造容器】8 Seccomp-BPF 与 Capabilities：容器安全的两道防线.md]
summary: Seccomp-BPF在syscall入口拦截+Capabilities在各子系统检查权限=容器安全纵深防御两道防线；Docker默认14个capability+44个syscall阻止；--privileged等于拆掉两道防线；cBPF与eBPF同源不同命
provenance:
  extracted: 0.82
  inferred: 0.16
  ambiguous: 0.02
base_confidence: 0.80
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-02
---

# Seccomp-BPF 与 Linux Capabilities

容器进程与宿主机**共享内核**——300+个syscall中不少能直接搞崩机器。"你的容器能调用 reboot()。不是假设，不是理论。" Linux Capabilities 和 Seccomp-BPF 构成容器安全的**纵深防御两道防线**：Seccomp在syscall入口拦截（第一道）+ Capability在各子系统检查权限（第二道）。

## 核心观点

- **Docker `--privileged` 等于拆掉两道防线**：把所有capability全加回来并禁用seccomp。
- **Seccomp-BPF 与 eBPF 同源不同命**：cBPF（2寄存器、~30指令）vs eBPF（11寄存器、~100+指令、maps）。内核内部已把cBPF翻译成eBPF执行，但seccomp用户态API只接受cBPF。
- **容器安全五层防线**：Namespace + Cgroup + Capabilities + Seccomp + AppArmor/SELinux。
- **`PR_SET_NO_NEW_PRIVS` 必须**：防止先设过滤器再exec setuid程序提权。
- **Docker默认seccomp profile性能开销约1-2% CPU**（240条规则）。

## Capabilities：权限拆分

Linux 2.2开始把root拆成41个独立能力。进程有三组位图：Permitted（允许获取）、Effective（当前生效）、Inheritable（可继承）。

### CAP_SYS_ADMIN 是"新的root"

控制的操作太多，设计失败。Docker默认不给这个capability。

### Docker默认14个capability

| Capability | 功能 |
|-----------|------|
| CAP_CHOWN | 改文件所有权 |
| CAP_DAC_OVERRIDE | 跳过文件权限检查 |
| CAP_FSETID | 文件set-id标志 |
| CAP_FOWNER | 跳过文件owner检查 |
| CAP_MKNOD | 创建设备节点 |
| CAP_NET_RAW | 原始网络包 |
| CAP_SETGID | 改GID |
| CAP_SETUID | 改UID |
| CAP_SETFCAP | 设置文件capability |
| CAP_SETPCAP | 修改进程capability |
| CAP_NET_BIND_SERVICE | 绑定<1024端口 |
| CAP_SYS_CHROOT | chroot |
| CAP_KILL | 发信号 |
| CAP_AUDIT_WRITE | 写审计日志 |

## Seccomp-BPF：syscall过滤

### 两种模式

| 模式 | 内核版本 | 限制 | 适用 |
|------|---------|------|------|
| **strict (mode 1)** | 2.6.12 | 只允许read/write/exit/sigreturn | 对容器不可用 |
| **filter/BPF (mode 2)** | 3.5 | BPF程序过滤syscall | 容器安全核心 |

`Seccomp: 2` 表示filter mode（0=disabled, 1=strict, 2=filter）。

### BPF返回动作

| 动作 | 效果 |
|------|------|
| **ALLOW** | 允许syscall |
| **KILL** | 杀进程 |
| **KILL_PROCESS** | 杀整个进程组 |
| **ERRNO** | 返回错误码 |
| **TRACE** | 通知ptrace |
| **LOG** | 允许但记录 |
| **TRAP** | 发SIGSYS |

### 输入结构

`struct seccomp_data`：nr（syscall编号）、arch（架构）、args[6]（参数）。

### Docker默认seccomp profile

阻止约44个syscall（总共300+个）。使用libseccomp高层API（Docker/Podman/containerd都用它）。

## Seccomp-BPF vs eBPF

| 维度 | cBPF (Seccomp) | eBPF (Cilium/Falco/bpftrace) |
|------|----------------|------------------------------|
| 寄存器 | 2个 | 11个 |
| 指令数 | ~30 | ~100+ |
| Maps | 无 | 有（key-value存储） |
| 用户态API | seccomp专用 | 通用内核钩子 |
| 使用场景 | syscall过滤 | 网络/追踪/安全观测 |

内核内部已把cBPF翻译成eBPF执行——两者最终都跑在eBPF引擎上，但用户态API不同。 ^[inferred]

## 关键细节

### libseccomp 和 seccomp-tools

- **libseccomp**：高层API，Docker/Podman/containerd使用
- **seccomp-tools**：反汇编seccomp profile的工具（`seccomp-tools dump $PID`）
- **capsh --decode**：解码capability位图
- **strace**：跟踪进程syscall（辅助seccomp profile编写）
- **ausyscall**：查询syscall编号

### 纵深防御层次

1. **Namespace**：视图隔离（"看到什么"）
2. **Cgroup**：资源限制（"用多少"）
3. **Capabilities**：权限拆分（"能做什么"）
4. **Seccomp-BPF**：syscall过滤（"能调用什么"）
5. **AppArmor/SELinux**：MAC强制访问（"能访问什么资源"）

五层防线各有侧重，组合形成容器安全纵深防御。 ^[inferred]

## 未解问题

- 自定义seccomp profile的编写方法论（如何确定需要ALLOW哪些syscall）？
- Seccomp与eBPF的未来统一可能性？
- Capabilities细粒度控制（41个capability的设计合理性评估）？

## 来源

- 从零造容器系列 #08 — Seccomp-BPF+Capabilities纵深防御+Docker默认profile拆解