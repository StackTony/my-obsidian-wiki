---
title: 阿里云K8S技术原理摘要
category: summaries
tags: [云原生, Kubernetes, 技术原理, 阿里云]
source_dir: Kubernetes（K8s）
source_files: [K8s云原生-阿里云-K8S技术原理.md]
summary: 阿里云K8S技术原理深度解读：声明式API+协调循环驱动自愈；etcd Raft共识+Quorum；网络三铁律；Flannel VXLAN/Calico BGP/Cilium eBPF对比；Service Mesh Istio mTLS零信任；GitOps ArgoCD；Operator模式；Knative Serverless+KubeVirt VM
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

# 阿里云K8S技术原理摘要

原文用"餐饮帝国"比喻贯穿全文，叙事性强但技术内容扎实。以下是技术事实蒸馏，忽略比喻包装。

## 声明式API + 协调循环

所有K8s能力（自愈、弹性、滚动更新）都从协调循环推导：Observe→Compare→Act→Repeat。不是一步步命令式操作，而是持续逼近期望状态。

## etcd：唯一真相源

etcd失败 = K8s失忆。Raft共识：Leader选举 + 日志复制 + Quorum多数确认。3节点容忍1故障，5节点容忍2。

## 网络三铁律

1. 每个 Pod 有集群唯一可见IP
2. Pod间通信无需NAT
3. Node与Pod间通信无需NAT

## CNI三强对比

- **Flannel VXLAN**：包中包隧道，简单但性能开销+MTU损失
- **Calico BGP**：纯L3路由无封装，Felix+BIRD，近裸机性能
- **Cilium eBPF**：内核级拦截，可替换kube-proxy，L3-L7 NetworkPolicy

iptables O(n) → IPVS O(1) → Cilium eBPF 三代演进。

## Service Mesh (Istio)

- Istiod(Pilot+Citadel+Galley)控制面 + Envoy Sidecar数据面
- mTLS零信任：Istiod颁发短期X.509证书，自动双向TLS握手，对开发者透明
- Envoy自动生成TraceID+Span，开发者零代码改动即可获得分布式追踪

## 可观测性三支柱

- **Prometheus**：Pull模型+K8s ServiceDiscovery自动发现
- **Loki/Promtail**：只索引labels非全文，存储极低；DaemonSet部署收集/var/log/pods/
- **Jaeger/OpenTelemetry**：TraceID+Span瀑布图

## GitOps (ArgoCD)

Git仓库为真相源；ArgoCD持续观察；检测偏移自动纠正；git log审计+git revert一键回滚。对比push模式CI/CD（Jenkins kubectl apply）——GitOps是pull模型，偏移自动修复。

## Operator模式

CRD（注册新资源类型）+ 自定义控制器（编码运维知识为自动化）。K8s从"容器编排器"升级为"通用编排器"。cert-manager是最著名的Operator。

## Knative Serverless

Scale-to-Zero + Activator拦截首请求触发Pod启动（冷启动）。KPA从0扩到1。

## KubeVirt VM管理

Pod中运行QEMU+libvirt → VM共享K8s CNI和CSI → "万物皆K8s"统一管理。

## 来源

- 原文：K8s云原生-阿里云-K8S技术原理.md（阿里云开发者社区）