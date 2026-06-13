---
title: Kubernetes 架构与核心原理
category: concepts
tags: [云原生, Kubernetes, 容器编排, 分布式系统, 声明式API]
aliases: [K8s架构, K8s核心原理]
relationships:
  - target: "[[concepts/linux-namespace-cgroups]]"
    type: uses
  - target: "[[concepts/k8s-networking]]"
    type: uses
  - target: "[[concepts/k8s-security]]"
    type: uses
  - target: "[[concepts/container-runtime-deep-dive]]"
    type: uses
  - target: "[[entities/containerd-runtime]]"
    type: uses
  - target: "[[concepts/k8s-cni-comparison]]"
    type: related_to
  - target: "[[concepts/prometheus-architecture]]"
    type: uses
source_dir: 云原生/Kubernetes（K8s）
source_files: [1-K8s 核心术语速查表.md, K8s云原生-官方文档-K8s架构.md, K8s云原生-阿里云-K8S技术原理.md, Kubernetes（K8s）全面解析：核心概念、架构与实践.md]
summary: K8s声明式API+协调循环驱动自愈/弹性/滚动更新；控制面(apiserver+etcd+scheduler+controller-manager)+数据面(kubelet+kube-proxy+容器运行时)；Pod最小部署单元+Service稳定网络入口+Deployment无状态管理
provenance:
  extracted: 0.85
  inferred: 0.12
  ambiguous: 0.03
base_confidence: 0.85
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: core
created: 2026-06-02
updated: 2026-06-13
---

# Kubernetes 架构与核心原理

Kubernetes（K8s）是 Google 开源的容器编排平台，已成为云原生生态的核心技术。它从一个"容器编排器"演变为"云时代的分布式操作系统"——所有自愈、弹性、滚动更新能力都源自同一个驱动机制：**声明式 API + 协调循环**。 ^[inferred] 详见 [[concepts/k8s-cloud-native-landscape|云原生技术全景导航]]。

## 核心观点

- **声明式 API 是 K8s 的灵魂**：你用 YAML 声明期望状态（"我要 3 个副本"），系统自动协调到目标。不是一步步命令式操作，而是持续逼近。 ^[inferred] 对比 Imperative 模式：手动 `kubectl run` → `kubectl scale` → `kubectl rollout`，每个步骤都需要人介入。
- **协调循环（Reconciliation Loop）**：Observe → Compare → Act → Repeat，永不停止。所有自愈、弹性伸缩、滚动更新都是它的不同表现形式。
- **K8s 不自己创建容器**：它站在 Linux 内核之上，用 [[concepts/linux-namespace-cgroups]] 提供隔离、用容器运行时（[[entities/containerd-runtime]]）执行。
- **etcd 是"唯一真相源"**：所有期望状态和实际状态数据存储在 etcd 中。etcd 崩溃 = K8s "失忆"。 ^[inferred] etcd 使用 Raft 共识算法保证强一致性：Leader选举 + 日志复制 + Quorum多数规则。3节点集群容忍1节点故障，5节点容忍2节点。
- **K8s 网络三铁律**：(1) 每个 Pod 有集群唯一可见IP；(2) Pod间通信无需NAT；(3) Node与Pod间通信无需NAT。

## 控制面组件

| 组件 | 功能 | 关键特性 |
|------|------|----------|
| **kube-apiserver** | 集群唯一入口，RESTful API | 认证→授权→准入→写入etcd；可水平扩展 |
| **etcd** | 分布式KV存储，唯一真相源 | Raft共识；Quorum多数确认写入；需备份策略 |
| **kube-scheduler** | 为新Pod选择最合适Node | 基于资源需求、亲和性/反亲和性、数据局部性、工作负载干扰、截止时间 |
| **kube-controller-manager** | 运行多个控制器 | ReplicaSet/Node/Deployment/Job/EndpointSlice/ServiceAccount控制器，逻辑独立但编译为一个二进制 |
| **cloud-controller-manager** | 云特定控制逻辑 | 将云交互组件与集群交互组件分离；Node/Route/Service云控制器 |

## 数据面组件

| 组件 | 功能 | 关键特性 |
|------|------|----------|
| **kubelet** | Node代理，管理Pod生命周期 | 只与apiserver通信；接受PodSpec确保容器运行健康；不管理非K8s容器 |
| **kube-proxy** | 网络代理，实现Service | iptables模式O(n)/IPVS模式O(1)；可选——CNI插件可提供等效行为 |
| **容器运行时** | 执行容器 | 支持 containerd、CRI-O 及任何 CRI 实现 |

## 核心抽象

### Pod — 最小部署单元

Pod 不是单个容器，而是一个"工作站"：一个或多个紧密关联的容器共享 **网络 Namespace**（同一IP、同一localhost）和存储。Pause 容器（基础设施容器）维持 Pod 的网络 Namespace——即使应用容器重启，Pod IP 不变。 ^[inferred]

- Pod 内容器通过 localhost 通信，毫秒级延迟
- Pod 生命周期短暂：Node故障或Pod删除后，无控制器不会重建

### Deployment — 无状态应用管理

Deployment → ReplicaSet → Pods 三层结构。Deployment 创建 ReplicaSet，ReplicaSet 确保 Pod 副本数。滚动更新通过新建 ReplicaSet + 逐步缩旧实现。

### Service — 稳定网络入口

Pod IP 是临时性的，Service 提供稳定的 ClusterIP。kube-proxy 将 ClusterIP DNAT 到实际 Pod IP，实现负载均衡。

| Service类型 | 范围 | 说明 |
|-------------|------|------|
| ClusterIP | 集群内部 | 默认类型，虚拟IP |
| NodePort | 集群内外 | 30000-32767静态端口 |
| LoadBalancer | 云平台LB | 云厂商负载均衡器集成 |
| Ingress | L7路由 | Ingress Controller统一入口 |

### 有状态/节点级/任务控制器

| 控制器 | 用途 | 关键特性 |
|--------|------|----------|
| **StatefulSet** | 有状态应用 | 保证Pod名称、网络身份、存储唯一性和顺序 |
| **DaemonSet** | 节点级任务 | 每个Node一个Pod副本（日志/监控） |
| **Job/CronJob** | 一次性/定时任务 | 完成后退出/按计划运行 |

## 架构部署变体

| 变体 | 控制面运行方式 | 典型场景 |
|------|----------------|----------|
| **传统部署** | systemd服务 | 自建机房 |
| **Static Pod** | kubelet管理的静态Pod | kubeadm使用此模式 |
| **Self-hosted** | 集群内Pod运行自身控制面 | 高级自托管 |
| **托管K8s** | 云平台抽象控制面 | EKS/AKS/ACK |

## 从声明式API到高级形态

K8s 通过 CRD + 自定义控制器（Operator 模式）从"容器编排器"升级为"通用编排器"。Operator 编码运维专家知识为自动化——cert-manager 是最著名的 Operator 之一。

| 高级形态 | 机制 | 关键能力 |
|----------|------|----------|
| **Knative (Serverless)** | KPA + Activator + Istio路由 | Scale-to-Zero、冷启动自动激活 |
| **KubeVirt (VM管理)** | QEMU+libvirt在Pod中运行VM | VM共享K8s CNI和CSI |
| **GitOps (ArgoCD)** | Git仓库为真相源 | 自动检测偏移并纠正 |
| **Service Mesh (Istio)** | Sidecar Envoy注入 | mTLS零信任、L7授权、熔断/重试 |

## 关键细节

### 协调循环的本质

所有控制器共享同一模式：
1. **Observe**：从 apiserver 读取期望状态和实际状态
2. **Compare**：计算差异（如期望3副本实际2副本）
3. **Act**：执行操作消除差异（创建1个新Pod）
4. **Repeat**：永不停止

这是 K8s 自愈的根源——Node故障后控制器检测到副本不足，自动在新Node创建Pod。

### iptables vs IPVS

| 模式 | 复杂度 | 适用规模 | 实现 |
|------|--------|----------|------|
| iptables | O(n) | 小集群 | 规则链遍历 |
| IPVS | O(1) | 大生产集群 | 内核L4负载均衡哈希表 |

500 Service 的集群就有1000-2000条 iptables 规则，规模增长后性能显著恶化。 ^[inferred]

## 未解问题

- 协调循环如何处理极端情况（冲突期望状态、级联故障）？
- Cilium eBPF 方案在极大规模下的性能表现？
- Knative 冷启动延迟与传统常驻部署的量化对比？


## 延伸阅读

综合分析：[[synthesis/cloud-native-infrastructure-landscape]]

## 来源

- [[summaries/k8s-terminology-cheatsheet]] — K8s核心术语速查表
- [[summaries/k8s-official-architecture]] — K8s官方文档架构
- [[summaries/k8s-alibaba-cloud-principles]] — 阿里云K8S技术原理