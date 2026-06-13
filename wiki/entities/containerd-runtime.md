---
title: containerd 容器运行时管理器
category: entities
tags: [云原生, containerd, 容器运行时, CRI, Kubernetes]
aliases: [containerd]
relationships:
  - target: "[[entities/runc-oci-reference]]"
    type: uses
  - target: "[[concepts/container-runtime-deep-dive]]"
    type: related_to
  - target: "[[concepts/k8s-architecture]]"
    type: related_to
source_dir: 云原生/容器运行时
source_files: [容器运行时 containerd.md]
summary: containerd专注容器生命周期管理，是Docker/K8s与底层runc之间的中间层；类比模型：K8s≈Nova, containerd≈libvirtd, runc≈QEMU；CRI内置+containerd-shim解耦+三种运行时对比
provenance:
  extracted: 0.85
  inferred: 0.13
 ambiguous: 0.02
base_confidence: 0.80
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: core
created: 2026-06-02
updated: 2026-06-13
---

# containerd 容器运行时管理器

containerd 是 Docker/Kubernetes 与底层 runc 之间的**中间管理层**——类比模型：K8s ≈ Nova（编排），containerd ≈ libvirtd（管理），runc ≈ QEMU（执行）。三层架构：上层编排 → 中间管理 → 底层执行。

## 核心观点

- **containerd 只管容器生命周期**：不做镜像构建/网络配置/存储管理——这些留给上层（Docker/K8s）和插件（CNI/CSI）。
- **containerd-shim 是关键解耦**：runc启动完容器后自身退出，containerd-shim成为容器进程的父进程——即使containerd崩溃也不影响已运行容器。
- **CRI内置是最大架构简化**：containerd 1.1+ 内置CRI插件，去掉CRI-Containerd中间shim。dockershim已在K8s 1.24移除。
- **三种运行时接口**：CRI（K8s→容器运行时）、CNI（网络）、CSI（存储）——标准化是K8s生态扩展的基石。 ^[inferred]
- **Docker namespace `moby` ≠ K8s namespace `k8s.io`**：两者在containerd中的命名空间隔离，Docker容器和K8s容器互不可见。

## 关键属性

| 属性 | 说明 |
|------|------|
| **起源** | Docker公司捐献，CNCF托管项目 |
| **语言** | Go |
| **架构** | C/S模式，gRPC API，插件体系 |
| **插件三大块** | Storage（镜像存储）、Metadata（元数据）、Runtime（容器运行） |
| **默认snapshotter** | OverlayFS |
| **CLI工具** | ctr（debug/admin用，非生产工具） |

## 架构演变

### Docker 1.11+ 调用链

```
Docker → containerd → containerd-shim → runc → 容器进程
```

Docker不再直接创建容器，而是请求containerd。containerd创建containerd-shim进程，shim再调用runc启动容器。runc完成后退出，shim成为容器进程的父进程。

### CRI 集成演变

| 阶段 | 方案 | 说明 |
|------|------|------|
| **dockershim** | K8s内置Docker适配器 | 1.20维护模式→1.24移除 |
| **cri-dockerd** | dockershim独立维护 | 临时过渡方案 |
| **CRI-Containerd** | 独立shim | 已弃用 |
| **containerd 1.1+ 内置CRI** | 去掉中间shim | 当前推荐 |

### 三种CRI运行时对比

| 运行时 | 设计目标 | 特点 |
|--------|---------|------|
| **containerd (内置CRI)** | Docker/K8s通用 | 功能全面、生态最大 |
| **CRI-O** | 专门为K8s设计 | 更轻量、更K8s专注 |
| **cri-dockerd** | Docker过渡方案 | 临时兼容 |

## containerd-shim 的意义

| 场景 | 无shim | 有shim |
|------|--------|--------|
| containerd崩溃 | 所有容器退出 | 容器继续运行 |
| containerd升级 | 需停所有容器 | 热升级不影响 |

shim是"垫片"——解耦containerd与容器进程，防止级联故障。

## 命名空间隔离

| 来源 | containerd命名空间 | 说明 |
|------|-------------------|------|
| Docker | `moby` | Docker管理的容器 |
| Kubernetes | `k8s.io` | K8s管理的容器 |
| ctr默认 | `default` | 手动测试用 |

切换到containerd后，`docker ps/inspect/exec`命令看不到K8s容器——它们在不同的命名空间中。

## 关键细节

### systemd配置

```ini
Delegate=yes    # containerd管理自己创建的容器的cgroups
KillMode=process  # 升级/重启containerd不杀现有容器
```

### ctr vs crictl vs critest

| 工具 | 用途 | 说明 |
|------|------|------|
| ctr | containerd CLI | debug/admin用，非生产 |
| crictl | CRI兼容CLI | K8s运维用 |
| critest | CRI合规测试 | 验证运行时符合CRI规范 |

## 与其他实体的关系

- containerd **使用** [[entities/runc-oci-reference]] 执行容器
- containerd **被** Docker/K8s **调用** 管理容器生命周期
- containerd-shim **解耦** containerd与容器进程
- CRI **标准化** K8s与运行时交互


## 延伸阅读

综合分析：[[synthesis/cloud-native-infrastructure-landscape]]

## 来源

- 容器运行时 containerd.md — 架构/演变/配置/使用