---
title: Kubernetes 网络架构
category: concepts
tags: [云原生, Kubernetes, 网络, CNI, Service]
aliases: [K8s网络, K8s网络四层模型]
relationships:
  - target: "[[concepts/k8s-architecture]]"
    type: related_to
  - target: "[[concepts/k8s-cni-comparison]]"
    type: related_to
  - target: "[[concepts/linux-network-stack]]"
    type: derived_from
  - target: "[[concepts/container-network-benchmarking]]"
    type: related_to
source_dir: Kubernetes（K8s）/Kubernetes网络
source_files: [K8s网络整体架构-腾讯云.md]
summary: K8s网络四层模型：容器内localhost→Pod间CNI→Service ClusterIP+CoreDNS→Ingress L7路由；CNI插件(Flannel VXLAN/Calico BGP/Cilium eBPF)各解决不同瓶颈
provenance:
  extracted: 0.80
  inferred: 0.18
  ambiguous: 0.02
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-02
---

# Kubernetes 网络架构

K8s 网络不是一张网——它是**四层模型**：容器内 localhost → Pod间 CNI → Service ClusterIP+CoreDNS → Ingress L7路由。每一层解决一个不同的问题，每一层有自己的组件和技术栈。

## 核心观点

- **K8s 网络三铁律**是设计前提：(1) 每个 Pod 有集群唯一可见IP；(2) Pod间通信无需NAT；(3) Node与Pod间通信无需NAT。
- **四层模型从低到高**：容器间共享localhost → Pod间靠CNI插件 → Service层靠kube-proxy+CoreDNS → 外部入口靠Ingress Controller。
- **CNI 插件是网络层的实现者**：K8s 定义标准，插件实现具体方案。选型先确认瓶颈再选工具。
- **iptables O(n) 是大规模集群的性能杀手**：500 Service → 1000-2000条 iptables 规则 → IPVS O(1) 或 Cilium eBPF 是出路。 ^[inferred]

## 四层网络模型

### 第一层：容器间通信（Pod内）

Pod 内多容器共享 Network Namespace（Pause容器维持）。通过 localhost 通信，毫秒级延迟，无跨网络开销。

### 第二层：Pod间通信（CNI层）

CNI 独立插件系统负责：容器IP分配、网络接口创建、网络环境配置。kubelet 创建 Pod 网络Namespace后调用 CNI 插件。

支持三种模式：
- **Host模式**：容器直接用宿主机网络栈（`--net=host`）
- **Overlay模式**：VXLAN/IP-in-IP 隧道封装
- **MACVLAN/IPvlan模式**：容器直接拥有物理网络接口

### 第三层：Service抽象层

为动态 Pod IP 提供稳定 ClusterIP 入口：
- **kube-proxy**：iptables/IPVS 模式实现 DNAT
- **CoreDNS**：为 Service 提供 DNS 名称解析
- Service 类型：ClusterIP（内部）→ NodePort（30000-32767）→ LoadBalancer（云LB）

### 第四层：Ingress L7路由层

统一 HTTP/HTTPS 外部入口：
- **Ingress Resource**（YAML规则）+ **Ingress Controller**（Nginx/Traefik 实现）
- 支持域名/路径路由、金丝雀部署（路径权重）、SSL终止
- 架构：Client → Ingress Controller → Ingress规则 → Service → Pod

**Ingress vs API Gateway**：Ingress 是"前台接待"（L7路由）；API Gateway（Kong/APISIX）是"特种接待"（认证、限流、请求变换）。

## 五大 CNI 插件对比

| CNI | 核心技术 | 性能 | 适用场景 | 关键组件 |
|-----|----------|------|----------|----------|
| **Flannel** | VXLAN隧道 | 有封装开销和MTU损失 | 简单小集群 | etcd状态管理 |
| **Calico** | BGP纯L3路由 | 近裸机性能 | 大规模高性能 | Felix+BIRD |
| **Cilium** | eBPF内核拦截 | 微秒级处理 | 现代生产首选 | 可替换kube-proxy |
| **Weave Net** | VXLAN/UDP+加密 | 中等 | 安全要求场景 | 自动节点发现 |
| **Kube-router** | BGP | 高 | 简化架构偏好 | BGP拓扑灵活 |

### Flannel VXLAN

"包中包"隧道模式：Pod数据包封装在UDP中跨Node传输。简单但有性能开销和 MTU 损失（VXLAN头50字节）。依赖 etcd 统一网络状态管理。

### Calico BGP

不封装：纯L3路由。每Node上 Felix 代理配置本地路由规则+iptables/eBPF策略；BIRD BGP客户端广播本地Pod路由。数据包直接路由，近裸机性能。支持 NetworkPolicy。

### Cilium eBPF

下一代 CNI：eBPF 程序注入内核钩子，JIT编译为本地机器码速度运行。可完全替换 kube-proxy。支持 L3-L7 NetworkPolicy（如：只允许 HTTP GET `/api/v1/read`，拒绝 DELETE）。避免用户态/内核态切换，处理延迟降至微秒级。 ^[inferred]

### CNI选型维度

选型评估三维度：网络可靠性、性能、安全。 ^[inferred] 简单集群用 Flannel；高性能大规模用 Calico；现代生产首选 Cilium。

## 关键细节

### iptables vs IPVS vs eBPF

| 模式 | 复杂度 | 规则规模影响 | 延迟特性 |
|------|--------|-------------|----------|
| iptables | O(n) | 10000规则→吞吐降24% | P99暴涨 |
| IPVS | O(1) | 不受规则数影响 | 稳定 |
| Cilium eBPF | O(1) | 几乎不受影响 | 微秒级 |

### Cilium 替换 kube-proxy

官方文档指出 kube-proxy 是可选的——当 CNI 插件提供等效的 Service 流量代理行为时。Cilium 正是如此：用 eBPF map 做 O(1) 路由查找，跳过整个 netfilter 栈。

## 未解问题

- VXLAN 在生产中的 MTU 影响量化？
- Cilium eBPF 在极大规模（万节点+）下的性能边界？
- KLB（Kubernetes Load Balancer）与标准 LoadBalancer Service 的差异？

## 来源

- [[summaries/k8s-terminology-cheatsheet]] — CNI/Service术语定义
- [[summaries/k8s-alibaba-cloud-principles]] — 网络三铁律+IPVS/eBPF对比
- 腾讯云K8s网络架构实战 — 四层模型+生产场景解决方案