你跑了个容器，`iperf3` 一测，带宽只有裸机的 80%。延迟多了 20μs。谁偷了你的性能？

答案是 **veth + bridge + iptables** — Docker 默认的网络模型。每个包从容器到宿主机要经过：veth pair → bridge → netfilter/iptables → 物理网卡。其中 iptables 的 conntrack 是最大的性能杀手。

但这不是唯一的选择。macvlan 跳过了 bridge，ipvlan 共享了 MAC 地址，Cilium 用 eBPF 替掉了整个 iptables 链。到底该用哪个？我们用数据说话。

> **测试环境**：4 核 Intel Xeon E-2278G @ 3.40GHz, 32GB DDR4, Intel X550 10Gbps NIC (ixgbe driver), Linux 6.1, kernel 默认参数, Docker 24.0, Cilium 1.14。所有测试在同一台物理机上完成，容器与宿主机间通信。每组测试跑 30 秒，取 5 次中位数。

---

## 一、Docker 默认网络：veth + bridge + iptables

### 数据路径

```
Container  Host
┌─────────┐  ┌──────────┐
│  eth0  │ ←── veth pair ──→ │ vethXXX  │
│10.0.0.2 │  │  │
└─────────┘  │ docker0  │ (bridge)
  │  │
  │ iptables │ (NAT + filter)
  │  │
  │  eth0  │ → 物理网络
  └──────────┘
```

每个包的旅程：

1. 容器内 `send()` → 经过容器的网络栈
2. 通过 veth pair 到达宿主机端的 vethXXX
3. vethXXX 是 bridge（docker0）的端口，包进入 bridge 转发
4. bridge 把包送到 **netfilter**（iptables 规则）
5. PREROUTING → FORWARD → POSTROUTING 链
6. NAT（MASQUERADE）修改源 IP
7. 最终从物理网卡出去

**两次经过 netfilter** — 一次在 bridge 层（br_nf），一次在 IP 层。这是设计缺陷，但为了兼容 iptables 规则，Docker 默认开启了 `bridge-nf-call-iptables`。

### conntrack 的代价

iptables 的 NAT 需要 conntrack（连接追踪）。conntrack 表的每条记录约 300 字节，默认最大 65536 条。高并发场景下：

- conntrack 表满 → 新连接被丢弃（`nf_conntrack: table full, dropping packet`）
- conntrack 查找是 O(1) 哈希，但在高 PPS（packets per second）下仍然可见
- conntrack 锁在多核场景下的竞争

工程上最常见的缓解是先把表调大，再观察命中率：

```
sysctl -w net.netfilter.nf_conntrack_max=262144
sysctl -w net.netfilter.nf_conntrack_buckets=65536
```

这能延后 `table full` 的爆炸点，但解决不了每个包都要过 conntrack 的事实。规则多、PPS 高时，CPU 时间还是会烧在 netfilter 上。

### 性能数据

在我的测试环境（4 核 Xeon, 10Gbps NIC）上用 iperf3：

```
裸机 TCP 吞吐:  9.41 Gbps
Docker bridge (veth):  7.52 Gbps  (-20%)
Docker bridge 延迟:  +18μs (vs 裸机)
```

P99 延迟对比:

```
裸机 TCP P99:  42μs
Docker bridge P99:  185μs  (4.4x)
```

20% 的吞吐损失在很多场景下可以接受。但 P99 才是真正杀人的指标 — 平均延迟好看不代表尾部不炸。对在线服务来说，1% 的请求慢 4 倍，用户体验就是”偶尔卡一下”，排查起来还特别痛苦。如果你跑的是高频交易或实时通信，这 185μs 的 P99 可能是致命的。

---

## 二、macvlan：跳过 bridge

macvlan 让容器直接拥有一个”虚拟网卡”，绑定到物理网卡上，每个容器有自己的 MAC 地址：

```
Container A  Container B  Host
┌─────────┐  ┌─────────┐  ┌──────────┐
│  eth0  │  │  eth0  │  │  eth0  │
│ MAC: AA │  │ MAC: BB │  │ MAC: CC  │
└────┬────┘  └────┬────┘  └────┬─────┘
  │  │  │
  └───────────────────────┴────────────────────┘
  物理网卡 (promiscuous mode)
```

**没有 bridge，没有 veth pair，没有 iptables NAT**。包直接从容器的虚拟网卡到物理网卡。

```
# 创建 macvlan 网络
docker network create -d macvlan \
  --subnet=192.168.1.0/24 \
  --gateway=192.168.1.1 \
  -o parent=eth0 \
  macnet

docker run --network macnet --ip 192.168.1.100 alpine
```

### 性能

```
macvlan TCP 吞吐:  9.28 Gbps  (-1.4% vs 裸机)
macvlan 延迟:  +2μs
macvlan P99:  58μs
```

几乎等于裸机。但有限制： - 容器和宿主机**不能直接通信**（macvlan 的 bridge 模式可以解决，但增加复杂度） - 需要物理网卡支持 promiscuous mode - 某些云环境（AWS EC2）不支持

如果你必须让宿主机和 macvlan 容器通信，常见 workaround 是在宿主机再创建一个 macvlan 子接口，把它也挂到同一物理网卡和网段：

```
ip link add mac0 link eth0 type macvlan mode bridge
ip addr add 192.168.1.10/24 dev mac0
ip link set mac0 up
```

这样宿主机就不再直接从 `eth0` 和容器说话，而是通过自己的 macvlan 身份进入同一二层网络。

---

## 三、ipvlan：共享 MAC 地址

ipvlan 类似 macvlan，但所有容器共享物理网卡的 MAC 地址。只在 IP 层区分：

```
docker network create -d ipvlan \
  --subnet=192.168.1.0/24 \
  -o parent=eth0 \
  -o ipvlan_mode=l2 \
  ipnet
```

**优势**：不需要 promiscuous mode，兼容更多环境。

**性能与 macvlan 接近**，因为数据路径几乎一样。P99 延迟 62μs，略高于 macvlan 的 58μs。

---

## 四、Cilium eBPF：替掉整个 iptables

Cilium 是 Kubernetes 的 CNI 插件，用 eBPF 替代 iptables 做包过滤、NAT、负载均衡。

### 传统 iptables 路径

```
包进入 → PREROUTING → conntrack → routing → FORWARD
  → conntrack → POSTROUTING → 出去

每个阶段都遍历规则链，O(n) 复杂度
```

### Cilium eBPF 路径

```
包进入 → eBPF 程序 (tc/XDP) → 直接转发
  ↓
  BPF map 查找 (O(1) 哈希)
```

eBPF 程序在 tc（traffic control）或 XDP（eXpress Data Path）层拦截包，用 BPF map 做路由查找，跳过整个 netfilter 框架。

### 性能数据

```
iptables (1000 规则):  6.83 Gbps
iptables (10000 规则):  5.21 Gbps  (规则越多越慢)
Cilium eBPF:  9.15 Gbps  (几乎不受规则数影响)
```

Cilium 在规则多的时候优势巨大。iptables 是线性匹配，规则从 1000 增到 10000，性能下降 24%。eBPF 用 map 查找，O(1)。

以上 iptables 数据是在 1000/10000 规则下的表现。实际 Kubernetes 集群中，每个 Service 会产生 2-4 条 iptables 规则。一个 500 Service 的集群就有 1000-2000 条规则。所以 Cilium 的优势不是理论上的 — 中等规模集群就能感受到 iptables 的瓶颈。

### XDP：在网卡驱动层拦截

XDP 比 tc 更早拦截包——在网卡驱动的 `napi_poll` 回调里，包还没进入内核网络栈：

```
网卡 DMA → XDP 程序 → DROP/PASS/REDIRECT/TX
  ↓
  跳过整个内核网络栈
```

XDP 能实现的场景： - **DDoS 防护**：在最早阶段丢弃恶意包 - **负载均衡**：Facebook 的 Katran 用 XDP 做 L4 负载均衡 - **容器间转发**：直接把包从一个网卡 redirect 到另一个

---

## 五、综合对比

|方案|吞吐 (Gbps)|额外延迟|P99 延迟|复杂度|适用场景|
|---|---|---|---|---|---|
|veth + bridge|7.52|+18μs|185μs|低|通用，Docker 默认|
|macvlan|9.28|+2μs|58μs|中|高性能，无需容器↔︎宿主通信|
|ipvlan|9.20|+3μs|62μs|中|云环境，无 promiscuous mode|
|Cilium eBPF|9.15|+5μs|68μs|高|Kubernetes，大规模集群|
|XDP redirect|9.35|+1μs|46μs|很高|极致性能，专用场景|
|host network|9.41|0|42μs|最低|无网络隔离|

**没有银弹**。选择取决于你的场景：

- **Docker 单机**：默认 bridge 足够
- **高性能服务**：macvlan 或 host network
- **Kubernetes 生产**：Cilium（eBPF 带来的可观测性是 bonus）
- **超低延迟**：host network 或 XDP

### 怎么选？

问自己三个问题：

1. **需要网络隔离吗？** 不需要 → host network
2. **延迟敏感吗？** 是 → macvlan/ipvlan（P99 < 65μs）
3. **Kubernetes 集群，Service 超过 500 个？** 是 → Cilium eBPF
4. **以上都不是？** → Docker bridge 够了

另一个常被忽略的指标是 CPU。bridge/iptables 的问题不只是延迟高，而是每多 1 个包就多几次 netfilter/conntrack 路径；eBPF/macvlan 的收益往往先体现在”同样吞吐下 CPU 更低”，然后才是尾延迟更稳。

---

## 六、测试方法论

如果你要自己跑 benchmark，注意几个陷阱：

1. **iperf3 只测吞吐**，不测尾延迟。用 `sockperf` 或 `netperf` 测 P99 延迟
2. **单连接不够**，要测多连接。Docker bridge 的 conntrack 锁在低连接数时不明显
3. **关掉 TCP offload 比较公平**：`ethtool -K eth0 tso off gso off gro off`
4. **测 PPS（packets per second）**，不只测 Gbps。小包场景 PPS 是瓶颈
5. **多次取中位数**，不取平均值。网络性能有毛刺
6. **关注 P99，不看平均值**。sockperf 的 `--percentile 99` 参数。平均延迟 50μs 可能意味着 P99 是 500μs — 对在线服务来说，P99 才是用户体验

```
# 吞吐测试
iperf3 -c <ip> -t 30 -P 4

# 延迟测试
sockperf ping-pong -i <ip> -p 12345 -t 30

# PPS 测试（64 字节小包）
iperf3 -c <ip> -t 30 -l 64 --udp -b 10G
```

下一篇是本系列最后一篇 — [runc 源码考古](https://quant67.com/post/containers/12-runc-source/runc-source.html)：看看工业级的 OCI 运行时到底长什么样。

## 相关阅读

- [eBPF：Linux 内核的隐藏武器](https://quant67.com/post/linux/ebpf/ebpf.html) — Cilium 的底层技术
- [eBPF + io_uring：高性能网络栈的终极形态](https://quant67.com/post/linux/ebpf-iouring/ebpf-iouring.html) — 更极致的内核网络优化
- [Network Namespace：给你的进程接上虚拟网线](https://quant67.com/post/containers/02-netns/netns.html) — 本系列 #02，veth 的基础
- [跨越世纪的挑战：C10K 到 C10M](https://quant67.com/post/system-design/c10k/c10k.html) — 网络编程的演进

## 同主题继续阅读

把当前热点继续串成多页阅读，而不是停在单篇消费。

2026-04-25 · linux / networking

### [【Linux 网络子系统深度拆解】虚拟网络设备内核实现：veth、bridge 与 macvlan](https://quant67.com/post/linux-net/16-veth-bridge/veth-bridge.html)

容器网络不能没有虚拟设备。本文从 Linux 6.6 内核源码拆解四类核心虚拟网络设备的实现：veth pair 的 veth_xmit 零拷贝转发与 XDP native 模式、Linux bridge 的 br_handle_frame 转发路径与 FDB 学习/老化机制、macvlan 五种模式的内核实现差异、tun/tap 的内核态与用户态数据交换路径，以及各类设备的性能特征对比。

2026-04-03 · linux / networking

### [【Kubernetes 网络深度系列】虚拟网络设备：veth / bridge / tun/tap / macvlan / ipvlan](https://quant67.com/post/k8s-network/02-virtual-devices/virtual-devices.html)

五种 Linux 虚拟网络设备的内核实现原理、数据流路径、性能代价与适用场景，附手工实验验证。

2025-07-22 · linux / networking

### [【Linux 网络子系统深度拆解】eBPF 网络钩子全景：TC/XDP/socket/cgroup](https://quant67.com/post/linux-net/22-ebpf-network-hooks/ebpf-network-hooks.html)

从内核源码全面拆解 eBPF 在网络子系统中的所有挂载点：TC BPF direct-action 模式与 bpf_mprog 多程序链、XDP 驱动级钩子回顾、socket ops 回调与 TCP 生命周期事件、cgroup BPF 策略控制、sk_msg/sk_skb 的 sockmap 重定向引擎、struct_ops 实现自定义拥塞控制，以及 bpftrace 可观测实战。

2025-07-21 · linux / networking

### [【Linux 网络子系统深度拆解】XDP 内核实现：在驱动层重编程网络栈](https://quant67.com/post/linux-net/21-xdp-internals/xdp-internals.html)

从内核源码拆解 XDP 的完整实现：xdp_buff 数据结构、驱动级钩子、五种动作路径、AF_XDP 零拷贝通道、devmap/cpumap/xskmap 重定向机制、多缓冲区支持，以及 bpftrace 可观测实战。