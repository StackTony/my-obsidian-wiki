---
title: K8s 网络故障排查手册
category: skills
tags: [云原生, Kubernetes, 网络, 排错, Cilium]
aliases: [K8s网络排查, K8s Network Troubleshooting]
relationships:
  - target: "[[concepts/k8s-networking]]"
    type: extends
  - target: "[[concepts/k8s-cni-comparison]]"
    type: related_to
  - target: "[[concepts/k8s-security]]"
    type: related_to
source_dir: Self learn/K8s和容器
source_files: [K8s网络故障排查.md]
summary: 三类真实故障复盘（网段冲突NAT/主节点DNS断服/容器网络抖动KubeSkoop）+通用五步排查法（Events→连通性→NetworkPolicy→Service/Endpoints→组件日志）+三类高频故障命令速查
provenance:
  extracted: 0.75
  inferred: 0.22
  ambiguous: 0.03
base_confidence: 0.58
lifecycle: draft
lifecycle_changed: 2026-09-16
tier: supporting
created: 2026-09-16
updated: 2026-09-16
---

# K8s 网络故障排查手册

> ⚠️ 来源可信度：蒸馏自 `raw/sources/Self learn/K8s和容器/K8s网络故障排查.md`（credibility: low）——实战案例来自生产复盘，但具体数值和命令输出未经交叉验证。

## 概述

K8s 网络故障的特征：**表象在应用（超时/502/DNS 失败），根因在网络基础设施（网段冲突/NAT/iptables/CNI 插件）**。本手册提炼三类真实故障复盘 + 通用排查方法论。

## 通用五步排查法

按顺序执行，每步排除一层：

```
1. describe pod 看 Events     → 镜像拉取/调度/探针问题在这里现形（很多"网络问题"其实不是网络问题）
2. 连通性测试 ping/nc/curl   → Pod IP / Service IP / 域名逐层测，定位断点在哪一跳
3. 查 NetworkPolicy          → 是否有策略挡住了流量（kubectl get networkpolicy -A）
4. 查 Service/Endpoints      → endpoints 是否为空、selector 是否匹配、kube-proxy 是否正常
5. 查组件日志                → kubelet / CNI 插件（calico-node/cilium）/ coredns 的日志
```

**关键心法**：从下往上分层排除——先 Pod 自身、再 Pod 网络、再 Service 抽象、最后外部边界。一次只验证一个假设。 ^[inferred]

## 三类真实故障复盘

### 案例一：外部网段与 Pod 网段冲突 → 边界防火墙 NAT

**现象**：Pod 内访问特定外部网段（如公司内网 10.x）超时，其他外部地址正常。

**根因链**：集群 Pod CIDR（如 10.244.0.0/16）与目标外部网段重叠 → 节点把发往 10.x 的包认为是"Pod 网络"内部流量 → 包在集群内打转或被丢弃。

**排查**：
```
# 在 Pod 内对比
ping <外部IP>        # 超时
ip route              # 看路由表，10.x 走了哪条路由
# 在节点上
ip route | grep 10    # flannel/cilium 的路由是否覆盖了目标网段
```

**修复**：在边界防火墙对冲突网段做 NAT（把 Pod 出流量 SNAT 成节点 IP），或规划时避免 Pod CIDR 与企业网段重叠。

### 案例二：主节点加域名解析 → 对外服务全断

**现象**：给 master 节点 `/etc/hosts` 或 `/etc/resolv.conf` 加了域名解析后，所有 K8s 对外服务（Ingress/NodePort）不可达，重启后恢复。

**根因链**：master 上运行着核心组件（kube-apiserver/etcd/coredns 等）→ 域名解析变更影响了 master 上组件的证书校验或控制面通信 → 控制面异常波及全网。 ^[inferred]（原文归因于 hosts 变更连锁反应，具体中断机理表述模糊）

**教训**：**master 节点是控制面，不是普通 Linux 机器**——任何系统级配置（hosts/resolv.conf/sysctl/防火墙）改动都可能级联放大。改 master 前先 `etcdctl snapshot save`。 ^[inferred]

### 案例三：容器网络抖动 → KubeSkoop exporter 监测

**现象**：间歇性网络抖动——服务偶发超时，监控无明显异常，人工抓包难以复现。

**方案**：部署 **KubeSkoop exporter**（阿里云开源的 K8s 网络诊断工具）持续采集：
- 节点级：conntrack 表溢出、软中断丢包、网卡丢包
- Pod 级：读写缓冲区溢出、NAT 转换失败、iptables 丢包计数

配合 Prometheus 建立网络丢包基线，抖动发生时看计数器增量定位丢包位置。

**适用**：肉眼抓不到的偶发问题，靠"持续监测+计数器"而非"重现问题"。 ^[inferred]

## 三类高频故障速查

| 症状 | 首查命令 | 常见根因 |
|------|----------|----------|
| Pod 访问外部超时 | `ip route`、节点 `iptables -t nat -L POSTROUTING -v` | Pod CIDR 与外部网段冲突、缺少 SNAT/MASQUERADE 规则 |
| Service ClusterIP 不可达 | `kubectl get endpoints <svc>`、`ipvsadm -Ln` / `iptables-save \| grep <svc-ip>` | Endpoints 空（selector 不匹配）、kube-proxy 规则未同步 |
| Ingress 返回 502/503 | `kubectl describe ingress`、`kubectl logs -n ingress-nginx <pod>` | 后端健康检查失败、upstream 连接被 NetworkPolicy 拒绝 |
| DNS 解析失败 | `kubectl logs -n kube-system -l k8s-app=kube-dns`、`nslookup kubernetes.default` | CoreDNS 死循环（forward 指回自己）、ndots:5 导致查询放大 |

## Pod 访问外部服务超时：五步排查展开

```
① Pod 内 curl <外部服务> 确认现象 → ② 节点上 curl 同地址（区分 Pod 网络问题 vs 节点网络问题）
→ ③ 检查出口：节点是否做 SNAT、ip_forward 是否开启、conntrack 表是否满（dmesg | grep conntrack）
→ ④ 检查 NetworkPolicy 是否限制 egress → ⑤ CNI 层：flannel/cilium 日志 + iptables POSTROUTING 计数
```

**conntrack 表满是隐蔽杀手**：高并发短连接场景下 `nf_conntrack: table full, dropping packet` 间歇丢包——症状与"网络抖动"一致，必须查 dmesg。 ^[inferred]

## 前置条件

- 熟悉 [[concepts/k8s-networking]] 四层模型（Pod 网络/Service/Ingress/NetworkPolicy）
- 掌握基础工具：kubectl describe/logs、ip route、iptables -L -v、tcpdump、curl/nc
- 生产环境改动前的备份意识（尤其 master 节点）

## 进阶用法

- **KubeSkoop exporter**：持续网络监测（丢包/conntrack/NAT 计数）
- **Cilium 集群**：`cilium status`、`hubble observe` 实时观测 L3-L7 流量（见 [[concepts/k8s-cni-comparison]]）
- **抓包三板斧**：Pod 内 tcpdump → 节点 veth/tcpdump → CNI 隧道接口（cilium_vxlan/flannel.1），逐层对比收发包

## 常见问题

**Q：为什么 describe pod 是第一步？**
A：大量"网络故障"上报实为镜像拉取失败、探针失败、调度失败——Events 一眼可辨，成本最低。 ^[inferred]

**Q：NetworkPolicy 默认行为？**
A：未选中任何 pod 时无影响；选中后默认按策略规则——**一旦 pod 被任何 ingress 策略覆盖，其他未显式放行的流量全部被拒**（白名单语义），这是"加了策略后突然不通"的头号原因。

## 来源

- K8s网络故障排查（raw/sources/Self learn/K8s和容器/，credibility: low）— 三类实战复盘+通用排查法
- 关联概念：[[concepts/k8s-networking]]、[[concepts/k8s-cni-comparison]]、[[concepts/k8s-security]]
