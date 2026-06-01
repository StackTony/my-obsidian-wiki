---
credibility: low
---

## 系列文章

- [Cilium 系列文章](https://ewhisper.cn/tags/Cilium/)

## 前言

将 Kubernetes 的 CNI 从其他组件切换为 Cilium, 已经可以有效地提升网络的性能. 但是通过对 Cilium 不同模式的切换/功能的启用, 可以进一步提升 Cilium 的网络性能. 具体调优项包括不限于:

- 启用本地路由(Native Routing)
- 完全替换 KubeProxy
- IP 地址伪装(Masquerading)切换为基于 eBPF 的模式
- Kubernetes NodePort 实现在 DSR(Direct Server Return) 模式下运行
- 绕过 iptables 连接跟踪(Bypass iptables Connection Tracking)
- 主机路由(Host Routing)切换为给予 BPF 的模式 (需要 Linux Kernel >= 5.10)
- 启用 IPv6 BIG TCP (需要 Linux Kernel >= 5.19)
- ~~禁用 Hubble(但是不建议, 可观察性比一点点的性能提升更重要)~~
- 修改 MTU 为巨型帧(jumbo frames) (需要网络条件允许)
- 启用带宽管理器(Bandwidth Manager) (需要 Kernel >= 5.1)
- 启用 Pod 的 BBR 拥塞控制 (需要 Kernel >= 5.18)
- 启用 XDP 加速 (需要 支持本地 XDP 驱动程序)
- (高级用户可选)调整 eBPF Map Size
- Linux Kernel 优化和升级
	- `CONFIG_PREEMPT_NONE=y`
- 其他:
	- tuned network-\* profiles, 如: `tuned-adm profile network-latency` 或 `network-throughput`
		- CPU 调为性能模式
		- 停止 `irqbalance` ，将网卡中断引脚指向特定 CPU

在网络/网卡设备/OS等条件满足的情况下, 我们尽可能多地启用这些调优选项, 相关优化项会在后续文章逐一更新. 敬请期待.

上篇文章我们启用了 [Cilium本地路由](https://ewhisper.cn/posts/47083/), 启用后对网络吞吐量提升明显.

今天我们来使用 Cilium 完全替换 KubeProxy, 创建一个没有 KubeProxy 的 Kubernetes 集群, 以此来大幅减少 iptables 规则链(还有 netfilter), 从而全方位提升网络性能.

### 测试环境

- Cilium 1.13.4
- K3s v1.26.6+k3s1
- OS
	- 3台 Ubuntu 23.04 VM, Kernel 6.2, x86

## 背景

Kubernetes 集群中, 在 Kube Proxy 里大量用到了 iptables, 在 Kubernetes 集群规模较大的情况下, 数以千/万计的 iptables 规则会极大地拖慢 Kubernetes 网络性能, 导致网络请求响应缓慢.

大量 IPTables 规则链的示例如下:

### Kube Proxy 的用途

Kube Proxy 的负责以下几个方面的流量路由:

1. **ClusterIP**: 集群内通过 ClusterIP 的访问
2. **NodePort**: 集群内外通过 NodePort 的访问
3. **ExternalIP**: 集群外通过 external IP 的访问
4. **LoadBalancer**: 集群外通过 LoadBalancer 的访问.

而 Cilium 完全实现了这些功能, 并做到了性能上的大幅提升, 具体 Cilium 官方测试结果如下:

![NodePort Latency Performance](https://img2023.cnblogs.com/other/3034537/202307/3034537-20230726101219591-780364935.png)

启用了 DSR 后性能会更强:

![NodePort Latency Performance with DSR](https://img2023.cnblogs.com/other/3034537/202307/3034537-20230726101219874-1487541478.png)

## 实施步骤

接下来我们开始实施替换, Cilium 的 eBPF kube-proxy 可在直接路由和隧道模式下进行替换。

### 重新安装 K3s

```bash
# Server Node
curl -sfL https://rancher-mirror.rancher.cn/k3s/k3s-install.sh | INSTALL_K3S_MIRROR=cn INSTALL_K3S_EXEC='--write-kubeconfig-mode=644 --flannel-backend=none --disable-network-policy --disable=servicelb --prefer-bundled-bin --disable-kube-proxy' INSTALL_K3S_VERSION=v1.26.6+k3s1 sh -
```

说明如下:

- `--disable=servicelb` K3s servicelb 不是 Kubernetes 的标准组件, 为了减少干扰, 先去掉它.
- `--disable-kube-proxy` 禁用 Kube Proxy

### 重新安装 Cilium

视情况不同, 可能需要卸载 Cilium:

```bash
helm uninstall cilium -n kube-system
```

重新安装, 重新安装时直接加上 `kubeProxyReplacement` 参数:

```bash
helm install cilium cilium/cilium --version 1.13.4 \
   --namespace kube-system \
   --set operator.replicas=1 \
   --set k8sServiceHost=192.168.2.43 \
   --set k8sServicePort=6443 \
   --set hubble.relay.enabled=true \
   --set hubble.ui.enabled=true \
   --set tunnel=disabled \
   --set autoDirectNodeRoutes=true \
   --set ipv4NativeRoutingCIDR=10.0.0.0/22 \
   --set kubeProxyReplacement=strict
```

说明如下:

- `kubeProxyReplacement=strict` Kube Proxy 替换使用严格模式. 而在默认情况下, Helm 会设置 `kubeProxyReplacement=disabled` ，这只会启用 ClusterIP 服务的群集内负载平衡。

### 基本信息验证

执行完成后进行验证:

```bash
$ kubectl -n kube-system exec ds/cilium -- cilium status | grep KubeProxyReplacement
KubeProxyReplacement:    Strict   [eth0 192.168.2.3 (Direct Routing)]
```

使用 `--verbose` 查看全部细节:

```bash
$ kubectl -n kube-system exec ds/cilium -- cilium status --verbose
...
KubeProxyReplacement Details:
  Status:                 Strict
  Socket LB:              Enabled
  Socket LB Tracing:      Enabled
  Socket LB Coverage:     Full
  Devices:                eth0 192.168.2.3 (Direct Routing)
  Mode:                   SNAT
  Backend Selection:      Random
  Session Affinity:       Enabled
  Graceful Termination:   Enabled
  NAT46/64 Support:       Disabled
  XDP Acceleration:       Disabled
  Services:
  - ClusterIP:      Enabled
  - NodePort:       Enabled (Range: 30000-32767)
  - LoadBalancer:   Enabled
  - externalIPs:    Enabled
  - HostPort:       Enabled
```

### 实战验证

接下来, 我们可以创建一个 Nginx 部署。然后，创建一个新的 NodePort 服务，并验证 Cilium 是否正确安装了该服务。

创建 Nginx Deploy：

```bash
cat << EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-nginx
spec:
  selector:
    matchLabels:
      run: my-nginx
  replicas: 2
  template:
    metadata:
      labels:
        run: my-nginx
    spec:
      containers:
      - name: my-nginx
        image: nginx
        ports:
        - containerPort: 80
EOF
```

下一步，为这两个实例创建一个 NodePort 服务：

```bash
$ kubectl expose deployment my-nginx --type=NodePort --port=80
service/my-nginx exposed
```

查看 NodePort 服务端口等信息:

```bash
$ kubectl get svc my-nginx
NAME       TYPE       CLUSTER-IP      EXTERNAL-IP   PORT(S)        AGE
my-nginx   NodePort   10.43.204.231   <none>        80:32727/TCP   96s
```

借助 `cilium service list` 命令，我们可以验证 Cilium 的 eBPF kube-proxy 替代程序是否创建了新的 NodePort 服务。在本例中，创建了端口号为 32727 的服务（位于网卡设备 eth0）：

```bash
$ kubectl -n kube-system exec ds/cilium -- cilium service list
ID   Frontend             Service Type   Backend
...
32   192.168.2.3:32727    NodePort       1 => 10.0.0.70:80 (active)
                                         2 => 10.0.2.96:80 (active)
33   0.0.0.0:32727        NodePort       1 => 10.0.0.70:0 (active)
                                         2 => 10.0.2.96:80 (active)
```

同时，我们还可以使用主机名空间中的 `iptables` 验证是否存在针对该服务的 `iptables` 规则：

```bash
casey@cilium-62-1:~$ sudo iptables-save | grep KUBE-SVC
[sudo] casey 的密码：
casey@cilium-62-1:~$
```

上方结果为空, 证明已经没有了 `KUBE-SVC` 相关的 IPTables 规则.

我们可以使用 `curl` 对 NodePort ClusterIP PodIP 等进行测试:

```bash
node_port=$(kubectl get svc my-nginx -o=jsonpath='{@.spec.ports[0].nodePort}')
# localhost+NodePort
curl 127.0.0.1:$node_port
# eth0+NodePort
curl 192.168.2.3:$node_port
# ClusterIP
curl 10.43.204.231:80
# 本机PodIP
curl 10.0.0.70:80
# 其他Node PodIP
curl 10.0.2.96:80
```

> 📝 **Note**
> 
> 最后 2 条能访问到也是因为之前启用了本地路由(Native Routing)的原因

都可以成功访问:

```html
<!DOCTYPE html>
<html>
<head>
<title>Welcome to nginx!</title>
...
```

🎉🎉🎉

## 总结

Kube Proxy 对 iptables 的大量使用给大规模 Kubernetes 集群的网络性能带来了负面影响, 通过利用 Cilium 完全替换 Kube Proxy, 可以大幅提升 Kubernetes 处理 ClusterIP/NodePort/LoadBalancer/externalIPs 等的网络性能表现.

至此, 性能调优已完成:

- ✔️ 启用本地路由(Native Routing)
- ✔️ 完全替换 KubeProxy
- IP 地址伪装(Masquerading)切换为基于 eBPF 的模式
- Kubernetes NodePort 实现在 DSR(Direct Server Return) 模式下运行
- 绕过 iptables 连接跟踪(Bypass iptables Connection Tracking)
- 主机路由(Host Routing)切换为给予 BPF 的模式 (需要 Linux Kernel >= 5.10)
- 启用 IPv6 BIG TCP (需要 Linux Kernel >= 5.19)
- 修改 MTU 为巨型帧(jumbo frames) (需要网络条件允许)
- 启用带宽管理器(Bandwidth Manager) (需要 Kernel >= 5.1)
- 启用 Pod 的 BBR 拥塞控制 (需要 Kernel >= 5.18)
- 启用 XDP 加速 (需要 支持本地 XDP 驱动程序)

## 📚️参考文档

- [Kubernetes Without kube-proxy — Cilium 1.13.4 documentation](https://docs.cilium.io/en/stable/network/kubernetes/kubeproxy-free/#kubeproxy-free)
- [Liberating k8s from kube-proxy and iptables - Google 幻灯片](https://docs.google.com/presentation/d/1cZJ-pcwB9WG88wzhDm2jxQY4Sh8adYg0-N3qWQ8593I/edit?pli=1#slide=id.g7055f48ba8_0_0)

> *三人行, 必有我师; 知识共享, 天下为公.* 本文由东风微鸣技术博客 [EWhisper.cn](https://ewhisper.cn/) 编写.