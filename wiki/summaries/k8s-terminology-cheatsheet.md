---
title: K8s 核心术语速查表摘要
category: summaries
tags: [云原生, Kubernetes, 术语, 速查表]
source_dir: Kubernetes（K8s）
source_files: [1-K8s 核心术语速查表.md]
summary: K8s集群13类核心术语中文速查：声明式API/协调循环/控制面/数据面/etcd/Raft/Pod/Deployment/Service/CNI/Flannel/Calico/Cilium/RBAC/PSS/Prometheus/Operator/GitOps
provenance:
  extracted: 0.95
  inferred: 0.05
  ambiguous: 0.00
base_confidence: 0.85
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-02
---

# K8s 核心术语速查表摘要

原文是按13类组织的术语速查表，所有内容为直接提取（EXTRACTED），无推断。这里是蒸馏摘要。

## 核心设计哲学

- **声明式API**：用YAML声明期望状态，系统自动协调到目标
- **协调循环**：Observe → Compare → Act → Repeat，永不停止

## 控制面/数据面

- **Control Plane**：集群大脑——apiserver/etcd/scheduler/controller-manager
- **Data Plane**：集群手——Worker Node运行容器化应用
- **etcd**：分布式KV存储，唯一真相源；Raft共识+Quorum多数规则
- **kube-apiserver**：集群唯一入口，RESTful API，认证→授权→准入→写入etcd
- **kube-scheduler**：为新Pod选择最合适Node
- **kube-controller-manager**：运行ReplicaSet/Node/Deployment/Job等控制器
- **kubelet**：Node代理，管理Pod生命周期
- **kube-proxy**：iptables/IPVS模式实现Service DNAT

## 核心抽象

- **Pod**：最小部署/调度单元，多容器共享网络和存储
- **Deployment**：无状态应用，创建ReplicaSet→Pods
- **Service**：稳定ClusterIP，kube-proxy负载均衡到Pod
- **StatefulSet**：有状态应用，保证Pod名称/网络/存储唯一性
- **DaemonSet**：每Node一个Pod副本（日志/监控）
- **Namespace**：集群资源隔离/多租户

## 网络

- **CNI**：容器网络接口标准，K8s定义/插件实现
- **Flannel**：VXLAN Overlay，"包中包"封装，有性能开销和MTU损失
- **Calico**：BGP纯L3路由，Felix+BIRD，近裸机性能
- **Cilium**：eBPF CNI，可替换kube-proxy，L3-L7 NetworkPolicy
- **iptables mode**：O(n)规则链；**IPVS mode**：O(1)哈希表
- **NetworkPolicy**：Pod级防火墙L3/L4访问控制

## 存储

- **PV/PVC**：集群存储资源+存储租用请求
- **CSI**：容器存储接口标准
- **StorageClass**：存储分级(SSD/HDD)，动态供给
- **ConfigMap**：非敏感配置；**Secret**：敏感数据，默认Base64明文需加密

## 安全

- **RBAC**：ServiceAccount→Role→RoleBinding
- **PSS**：取代PSP，三级privileged/baseline/restricted
- **SecurityContext**：runAsNonRoot/drop ALL capabilities/readOnlyRootFilesystem

## 可观测性

- **Prometheus**：Pull模型+K8s ServiceDiscovery自动发现
- **Grafana**：可视化面板
- **Loki**：日志系统，只索引labels非全文，存储极低
- **Jaeger**：分布式追踪TraceID+Span

## 高级形态

- **CRD+Operator**：自定义资源+编码运维知识为自动化
- **GitOps (ArgoCD)**：Git为真相源，自动检测偏移并纠正
- **Knative**：Serverless框架，Scale-to-Zero+冷启动
- **KubeVirt**：在Pod中运行VM（QEMU+libvirt）

## 来源

- 原文：1-K8s 核心术语速查表.md — 13类术语完整速查表