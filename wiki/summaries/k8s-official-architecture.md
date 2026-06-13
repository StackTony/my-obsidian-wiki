---
title: K8s官方文档架构摘要
category: summaries
tags: [云原生, Kubernetes, 架构, 官方文档]
source_dir: 云原生/Kubernetes（K8s）
source_files: [K8s云原生-官方文档-K8s架构.md]
summary: K8s官方文档架构：控制面(apiserver+etcd+scheduler+controller-manager+cloud-controller-manager)+数据面(kubelet+kube-proxy+容器运行时)；四种架构变体；kube-proxy可选
provenance:
  extracted: 0.90
  inferred: 0.10
  ambiguous: 0.00
base_confidence: 0.90
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-13
---

# K8s官方文档架构摘要

原文来自 kubernetes.io/zh-cn 官方文档，权威性最高。以下是关键事实蒸馏。

## 控制面组件

- **kube-apiserver**：可水平扩展；集群前端
- **etcd**：一致高可用KV存储；必须备份
- **kube-scheduler**：基于资源需求/约束/亲和性/数据局部性/工作负载干扰/截止时间选Node
- **kube-controller-manager**：逻辑独立但编译为一个二进制；Node/Job/EndpointSlice/ServiceAccount控制器
- **cloud-controller-manager**：云特定控制逻辑；自有环境不含此组件

## 数据面组件

- **kubelet**：只管理K8s创建的容器；不接受非K8s容器
- **kube-proxy**：**可选**——网络插件可提供等效Service代理行为
- **容器运行时**：支持containerd/CRI-O/任何CRI实现

## Addon

- **CoreDNS**：几乎所有集群必备；为Service提供DNS记录
- **Dashboard**：Web管理界面
- **网络插件**：实现CNI规范；分配Pod IP；启用Pod间通信

## 架构变体

| 变体 | 控制面运行方式 | 典型工具 |
|------|----------------|----------|
| 传统部署 | systemd服务 | — |
| Static Pod | kubelet管理 | kubeadm |
| Self-hosted | 集群内Pod | — |
| 托管K8s | 云平台抽象 | EKS/AKS/GKE |


## 延伸阅读

综合分析：[[synthesis/cloud-native-infrastructure-landscape]]

## 来源

- 原文：K8s云原生-官方文档-K8s架构.md（kubernetes.io/zh-cn翻译）