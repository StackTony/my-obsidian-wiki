---
title: runc — OCI 参考实现
category: entities
tags: [云原生, runc, OCI, 容器运行时, Go]
aliases: [runc]
relationships:
  - target: "[[entities/containerd-runtime]]"
    type: related_to
  - target: "[[concepts/container-runtime-deep-dive]]"
    type: related_to
  - target: "[[concepts/seccomp-capabilities]]"
    type: implements
source_dir: 云原生/容器运行时/从零造容器系列
source_files: [【从零造容器】12 runc 源码考古：OCI 参考实现到底长什么样.md]
summary: runc是OCI Runtime Spec参考实现(~15000行Go+C)；nsenter C代码解决Go runtime fork不安全；三次clone+两阶段init(Bootstrap C+Standard Go)；exec FIFO同步create/start；cgroupfs vs systemd driver
provenance:
  extracted: 0.82
  inferred: 0.16
  ambiguous: 0.02
base_confidence: 0.80
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-13
---

# runc — OCI 参考实现

runc 是 OCI Runtime Specification 的参考实现，源自 Docker捐献的 libcontainer。~15000行代码（Go + C），是容器运行时的"底层执行器"——只管创建/启动/杀死容器进程，不管镜像管理或网络配置。

## 核心观点

- **nsenter ~500行C代码是runc最关键部分**：Go runtime fork不安全（多线程、调度器、GC线程），用 `__attribute__((constructor))` 在Go runtime启动前执行C代码设置namespace/UID映射。
- **三次clone + 两阶段init**：parent → stage-1 → stage-2 → init，处理user namespace特殊顺序。
- **exec FIFO是create/start同步的桥梁**：命名管道实现跨进程同步；FIFO在文件系统上，任何进程都能打开。
- **PTY管理是容器运行时最容易出bug的部分**：master在容器外（docker attach入口）、slave在容器内（控制终端）；UNIX socket + SCM_RIGHTS传fd。
- **cgroups/包~4000行比容器核心逻辑还多**——资源管理的边缘情况远多于容器创建本身。

## 架构

### 三层结构

```
CLI入口 (main.go)
  → libcontainer (可独立使用的核心库)
    → nsenter (C代码, __attribute__((constructor)))
```

libcontainer 源自Docker捐献的 libcontainer——runc只是libcontainer的OCI规范化封装。

### nsenter C代码的必要性

| 问题 | 原因 | nsenter解法 |
|------|------|-------------|
| Go runtime多线程 | fork只复制调用线程 | 在Go runtime启动前用C代码执行 |
| namespace设置顺序 | User namespace必须先设 | C bootstrap阶段按顺序设置 |
| UID/GID映射 | 需要写/proc/PID/uid_map | C代码直接写文件 |

`__attribute__((constructor))` 让函数在ELF `.init_array`段，`main()`之前执行——Go runtime还没启动，C代码在单线程环境中安全操作。

### 三次clone

| 进程 | 角色 | namespace操作 |
|------|------|--------------|
| parent | CLI入口 | 无 |
| stage-1 | Bootstrap | 设置user namespace + UID映射 |
| stage-2 | Standard init | 设置其余namespace + rootfs + seccomp |
| init | 最终容器进程 | 执行用户命令 |

### 两阶段init

| 阶段 | 语言 | 操作 | 原因 |
|------|------|------|------|
| **Bootstrap** | C | namespace/UID映射 | 需单线程环境 |
| **Standard** | Go | rootfs/seccomp/capabilities | 需高级语言安全和便利 |

## exec FIFO 同步

create和start通过命名管道(FIFO)同步：
- **create阶段**：runc创建FIFO并等待容器init打开它
- **start阶段**：runc打开FIFO另一端，init收到信号开始执行用户命令

FIFO在文件系统上——任何进程都能打开，包括编排系统（在空档做cgroup/网络/seccomp配置）。

## cgroup manager

| 模式 | 实现 | 推荐 |
|------|------|------|
| **cgroupfs** | 直接写文件 | runc默认 |
| **systemd** | D-Bus API | K8s推荐 |

systemd模式避免systemd和手动运行时互相覆盖subtree_control的冲突。

## 关键细节

### closeExecFrom()

关闭所有fd > 2，防止容器继承宿主机socket/fd——安全措施。

### PTY管理

```
容器外: PTY master (docker attach入口)
容器内: PTY slave (控制终端)
通信: UNIX socket + SCM_RIGHTS 传递fd
```

`posix_openpt()` → `grantpt()` → `unlockpt()` → `TIOCSCTTY` 设置控制终端。

### 容器进程资源清理

namespace泄漏、cgroup残留、挂载点残留——容器运行时最常见的三类bug。pivot_root失败但bind mount已完成时产生"幽灵挂载点"。

## 与miniruntime对比

| 维度 | miniruntime | runc |
|------|-------------|------|
| 代码量 | ~500行 | ~15000行 |
| init | reexec(/proc/self/exe) | C bootstrap + Go standard |
| cgroup | 基础设置 | ~4000行边缘情况处理 |
| PTY | 不实现 | 完整PTY管理 |
| seccomp | 不实现 | 完整profile支持 |

## 来源

- 从零造容器系列 #12 — runc源码架构+nsenter解析+三次clone+FIFO同步