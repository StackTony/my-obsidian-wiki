---
title: 云原生基础设施全景
category: synthesis
tags: [云原生, Kubernetes, 容器, 全景图, 架构]
aliases: [云原生全景]
relationships:
  - target: "[[concepts/k8s-architecture]]"
    type: related_to
  - target: "[[concepts/container-runtime-deep-dive]]"
    type: related_to
  - target: "[[concepts/k8s-networking]]"
    type: related_to
  - target: "[[concepts/k8s-security]]"
    type: related_to
  - target: "[[concepts/k8s-cni-comparison]]"
    type: related_to
  - target: "[[concepts/llm-infra-landscape]]"
    type: related_to
  - target: "[[concepts/linux-namespace-cgroups]]"
    type: derived_from
source_dir: 云原生
source_files: [1-K8s 核心术语速查表.md, K8s云原生-官方文档-K8s架构.md, K8s云原生-阿里云-K8S技术原理.md, K8s安全加固完全指南.md, Kubernetes网络/K8s网络整体架构-腾讯云.md, Kubernetes（K8s）全面解析：核心概念、架构与实践.md, Prometheus/Prometheus-博客园-原理详解.md, 容器运行时/从零造容器系列/从零造容器系列文章.md, 容器运行时/容器运行时 containerd.md]
summary: 云原生三层架构全景：底层(Linux内核Namespace+Cgroup+Seccomp+OverlayFS)+中间层(containerd/shim/runc运行时栈)+上层(K8s声明式编排+Service Mesh+GitOps+可观测)；容器→microVM隔离模型演进；iptables→IPVS→eBPF网络三代
provenance:
  extracted: 0.60
  inferred: 0.35
  ambiguous: 0.05
base_confidence: 0.70
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: core
created: 2026-06-02
updated: 2026-06-02
---

# 云原生基础设施全景

云原生不是一项技术——它是一个**三层架构体系**，每层都有自己的演进路径和选型决策。本文综合22个源文件的知识，描绘从Linux内核到K8s编排到可观测的完整全景。

## 跨领域连接

### 底层：Linux内核特性

容器不是发明，是拼装。八个内核特性的组合拳：

| 特性 | 隔离维度 | 演进状态 |
|------|----------|----------|
| **Namespace (8种)** | 可见性隔离 | v1→v2: User Namespace使能Rootless |
| **Cgroup** | 资源限制 | v1→v2: unified hierarchy+writeback-aware IO |
| **pivot_root** | 文件系统隔离 | 替代chroot（有逃逸漏洞） |
| **OverlayFS** | 存储分层 | 替代aufs/devicemapper |
| **Seccomp-BPF** | syscall过滤 | cBPF（同源eBPF但进化方向不同） |
| **Capabilities** | 权限拆分 | 41个独立能力，CAP_SYS_ADMIN是"新root" |
| **veth/bridge/NAT** | 网络连接 | →macvlan/eBPF/XDP更高性能方案 |
| **KVM** | 硬件虚拟化 | →microVM(Firecracker)125ms启动 |

### 中间层：容器运行时栈

```
编排层 (K8s/Docker)
  → 管理层 (containerd/CRI-O)
    → 垫片层 (containerd-shim)
      → 执行层 (runc/crun/kata)
        → 内核层 (Namespace+Cgroup+pivot_root+OverlayFS)
```

| 演进 | 前后 | 驱动力 |
|------|------|--------|
| Docker直连→containerd | Docker 1.11+ | Swarm失败后重新定位 |
| dockershim→CRI内置 | K8s 1.24 | 标准化运行时接口 |
| CRI-Containerd→内置CRI | containerd 1.1 | 减少中间层 |

### 上层：K8s编排与生态

**声明式API+协调循环**驱动所有上层能力：自愈、弹性、滚动更新、偏移纠正。

| 功能域 | 核心组件 | 演进方向 |
|--------|----------|----------|
| **网络** | kube-proxy iptables → IPVS → Cilium eBPF | 规则规模驱动 |
| **安全** | PSP → PSS + RBAC + NetworkPolicy | 标准化+纵深防御 |
| **服务治理** | kube-proxy → Service Mesh Istio | L4→L7零信任 |
| **部署** | kubectl apply → GitOps ArgoCD | push→pull模型 |
| **可观测** | Prometheus + Grafana + Loki + Jaeger | 三支柱一体化 |
| **Serverless** | K8s → Knative | Scale-to-Zero |
| **VM管理** | K8s → KubeVirt | 万物皆K8s |

## 综合洞察

### 容器→microVM：信任边界驱动隔离模型选择

容器共享内核（单点故障）适合企业内部可信代码；microVM独立内核（硬件隔离）适合多租户不可信代码。Kata Containers把两者桥接——外部OCI接口+内部microVM隔离。不是"谁更好"，而是信任模型不同。 ^[inferred]

### iptables→IPVS→eBPF：网络性能的三代演进

规模增长迫使网络方案逐代升级：iptables O(n) → IPVS O(1) → Cilium eBPF（跳过整个netfilter栈）。500 Service集群就有1000-2000条iptables规则，P99延迟暴涨——规模是换代的驱动力。 ^[inferred]

### v1→v2→Rootless：安全的三步演进

Cgroup v1独立层级→v2统一层级+writeback-aware；Namespace全部特权→User Namespace使能Rootless容器；Seccomp strict→filter-BPF→eBPF生态。每一步都让容器更安全、更标准。 ^[inferred]

### 声明式范式扩散：从K8s到GitOps到Agent

声明式API+协调循环从K8s扩散到GitOps(ArgoCD检测偏移自动纠正)→到Agent框架(可观测状态机驱动决策)。同一种心智模型在不同层级反复出现。 ^[inferred]

### 与LLM基础设施的连接

[[concepts/llm-infra-landscape]]的五层工程栈（硬件→系统软件→框架→应用→运营）与云原生三层架构有结构相似性：底层硬件/内核特性→中间管理软件→上层编排和可观测。两者都在解决"如何让大量计算资源可靠运行复杂工作负载"——只是工作负载不同（容器化微服务 vs LLM训练/推理）。 ^[inferred]

## 开放问题

- 云原生与AI基础设施的融合趋势（K8s调度GPU→KubeVirt运行VM→未来？）
- Rootless容器的内核攻击面增加问题——安全与可用性的矛盾
- Cilium eBPF成为K8s网络标准后的生态影响

## 来源

- [[summaries/k8s-terminology-cheatsheet]] — 术语定义
- [[summaries/k8s-official-architecture]] — 官方架构
- [[summaries/k8s-alibaba-cloud-principles]] — 技术原理
- [[concepts/k8s-architecture]] — K8s核心架构
- [[concepts/container-runtime-deep-dive]] — 容器运行时
- [[concepts/k8s-networking]] — K8s网络
- [[concepts/k8s-security]] — K8s安全
- [[entities/containerd-runtime]] — containerd
- [[concepts/prometheus-architecture]] — Prometheus监控