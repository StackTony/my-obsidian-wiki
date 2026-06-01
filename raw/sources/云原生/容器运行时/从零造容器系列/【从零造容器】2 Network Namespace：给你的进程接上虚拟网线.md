[上一篇](https://quant67.com/post/containers/01-namespaces/namespaces.html)我们用 50 行 C 造了个”容器”：进程有自己的 PID 空间、主机名、挂载点表、IPC 空间。看起来很酷，但你试过在里面 `curl google.com` 吗？

不行。因为那个进程的网络栈还是宿主机的。它能看到宿主机的 `eth0`，能绑定宿主机的端口，能 sniff 宿主机的所有流量。这哪叫隔离？

更糟糕的是，如果你加了 `CLONE_NEWNET`，容器里**什么网络设备都没有** — 连 loopback 都是 DOWN 的。从”看到一切”直接跳到”什么都没有”。

这篇文章的任务就是：**在”什么都没有”和”连通互联网”之间，搭一座桥** — 字面意义上的桥。

> 本文所有代码在 `examples/containers/02-netns/` 目录，`make` 即可编译。Shell 脚本可直接运行。测试环境：Linux 6.x, x86_64。

---

## 一、CLONE_NEWNET：一个空荡荡的网络世界

Network namespace 隔离的东西比你想象的多：

- 网络接口（interfaces）
- IPv4/IPv6 协议栈
- 路由表（routing table）
- iptables/nftables 规则
- socket — 是的，不同 netns 的 socket 完全隔离
- `/proc/net`、`/sys/class/net` 等伪文件系统

创建一个新的 network namespace 后，里面只有一个 `lo` 接口，而且状态是 **DOWN**。

来验证一下：

```c
// 子进程在新的 network namespace 里
static int child_fn(void *arg) {
  printf("=== 容器内的网络状态 ===\n");
  system("ip link show");
  printf("\n=== 路由表 ===\n");
  system("ip route show");
  printf("\n=== iptables ===\n");
  system("iptables -L -n 2>/dev/null || echo 'iptables not available'");
  return 0;
}

// clone() 时加上 CLONE_NEWNET
pid_t pid = clone(child_fn, stack + STACK_SIZE,
  CLONE_NEWNET | CLONE_NEWPID | CLONE_NEWUTS | SIGCHLD, NULL);
```

输出：

```
=== 容器内的网络状态 ===
1: lo: <LOOPBACK> mtu 65536 qdisc noop state DOWN mode DEFAULT
  link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00

=== 路由表 ===
(空)

=== iptables ===
Chain INPUT (policy ACCEPT)
Chain FORWARD (policy ACCEPT)
Chain OUTPUT (policy ACCEPT)
```

看到了吧： - `lo` 存在，但 `state DOWN`，连自己 ping 自己都不行 - 路由表是空的 — 包往哪发都不知道 - iptables 是空的 — 一个全新的 netfilter 实例

这就是 Docker 容器启动的起点。每个容器都从这个”真空”状态开始，然后容器运行时（Docker、containerd、CRI-O）帮你把网线接上。

### lo 为什么默认是 DOWN？

你可能觉得内核可以自动把 lo 拉起来。但内核的设计哲学是：**新 namespace 里什么都不预设，让用户态决定一切**。这给了容器运行时最大的灵活性 — 也许你根本不需要 loopback（虽然这种场景几乎不存在）。

手动拉起 lo：

或者在 C 里通过 netlink 做，但那是几百行代码的事情。我们后面用 `system()` 调 `ip` 命令来简化。

---

## 二、veth pair：一根虚拟网线

好，容器里是空的。怎么接进去？

Linux 提供了 **veth**（Virtual Ethernet）设备。它是成对创建的 — 你可以想象成一根网线的两头。从一头塞进去的包，会从另一头出来。

```
# 创建一对 veth
ip link add veth-host type veth peer name veth-container
```

这条命令创建了两个接口：`veth-host` 和 `veth-container`。它们目前都在宿主机的 namespace 里。

关键操作：**把 veth 的一端移动到容器的 network namespace 里**：

```
# 把 veth-container 移到 PID 为 $PID 的进程所在的 netns
ip link set veth-container netns $PID
```

移动之后： - 宿主机看不到 `veth-container` 了 - 容器里多了一个 `veth-container` 接口 - 从宿主机的 `veth-host` 发的包，会出现在容器的 `veth-container` 上

这就是 Docker 网络的核心机制。没有什么虚拟交换机的魔法 — 就是一对一对的虚拟网线。

---

## 三、一步步搭建容器网络

现在来完整地走一遍流程。我们的目标是让容器进程能访问互联网。

![veth + bridge 网络拓扑](https://quant67.com/post/containers/02-netns/veth-bridge-topology.svg)

整个拓扑是这样的：

1. 宿主机有一个 **bridge**（网桥），类似于一个虚拟交换机
2. 每个容器通过 **veth pair** 连到这个 bridge
3. bridge 有自己的 IP，作为容器的网关
4. 宿主机配 **iptables MASQUERADE**（NAT），容器出去的包用宿主机 IP

### 第一步：创建 bridge

```
# 创建 bridge
ip link add br0 type bridge
ip addr add 10.0.0.1/24 dev br0
ip link set br0 up
```

`br0` 就是 Docker 里的 `docker0`。它是一个二层交换机 — 连到它的接口之间可以直接通信，不需要路由。

### 第二步：创建 veth pair，一端连到 bridge

```
# 创建 veth pair
ip link add veth-host type veth peer name veth-container

# 把 host 端连到 bridge
ip link set veth-host master br0
ip link set veth-host up
```

### 第三步：把另一端移到容器 namespace

```
# 获取容器进程的 PID
PID=$(container_pid)

# 移动 veth 到容器的 netns
ip link set veth-container netns $PID
```

### 第四步：在容器内配置网络

```
# 以下命令在容器的 namespace 内执行（通过 nsenter 或在子进程中）
ip link set lo up
ip link set veth-container name eth0  # 改个好听的名字
ip addr add 10.0.0.2/24 dev eth0
ip link set eth0 up
ip route add default via 10.0.0.1  # 网关指向 bridge
```

现在容器可以 ping 到宿主机的 `br0`（10.0.0.1）了。但还不能上网 — 因为外部网络不认识 10.0.0.2 这个地址。

### 第五步：NAT — 让容器伪装成宿主机

```
# 在宿主机上
echo 1 > /proc/sys/net/ipv4/ip_forward
iptables -t nat -A POSTROUTING -s 10.0.0.0/24 ! -o br0 -j MASQUERADE
```

这就是 Docker 在你安装完之后默默做的事情。`MASQUERADE` 会把容器发出的包的源地址替换成宿主机的出口 IP，外部服务器以为是宿主机在说话。回来的包再被 NAT 回去给容器。

来看一下实际的规则长什么样：

```
$ iptables -t nat -L POSTROUTING -v -n
Chain POSTROUTING (policy ACCEPT 0 packets, 0 bytes)
 pkts bytes target  prot opt in  out  source  destination
  42  2520 MASQUERADE  all  --  *  !br0  10.0.0.0/24  0.0.0.0/0

$ iptables -t nat -L -v -n | head -20
# 以及 conntrack 表里的映射记录：
$ conntrack -L -n 2>/dev/null | head -5
tcp  6 117 TIME_WAIT src=10.0.0.2 dst=142.250.80.46 sport=41234 dport=80 \
  src=142.250.80.46 dst=192.168.1.100 sport=80 dport=41234 [ASSURED]
```

`conntrack` 里的这条记录就是 MASQUERADE 的核心：它记住了 `10.0.0.2:41234 → 192.168.1.100:41234` 的映射，回来的包按这个映射送回容器。

`[ASSURED]` 表示这个连接已经看到了双向流量，conntrack 不会把它当成”半开连接”提前回收。线上如果你只看到大量 `UNREPLIED` 记录，通常意味着回包没回来——NAT、路由或防火墙有地方断了。

到这里，容器可以 `curl google.com` 了。

---

## 四、完整 C 代码：从 clone() 到联网

下面的 C 代码演示了创建一个带 network namespace 的子进程，并在子进程中展示网络隔离状态：

```c
#define _GNU_SOURCE
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>
#include <sys/mount.h>

#define STACK_SIZE (1024 * 1024)

static int child_fn(void *arg) {
  (void)arg;
  sethostname("netns-demo", 10);

  /* 切断挂载传播 */
  mount("", "/", "", MS_PRIVATE | MS_REC, NULL);
  mount("proc", "/proc", "proc", 0, NULL);

  printf("\n===== 容器网络状态 =====\n");
  printf("PID: %d\n", getpid());

  printf("\n[1] 网络接口 (只有 lo，且 DOWN):\n");
  system("ip link show");

  printf("\n[2] 路由表 (空的):\n");
  system("ip route show 2>/dev/null");

  printf("\n[3] 拉起 loopback:\n");
  system("ip link set lo up");
  system("ping -c 1 -W 1 127.0.0.1");

  printf("\n===== 等待网络配置 =====\n");
  printf("父进程现在可以配置 veth pair。\n");
  printf("容器 PID (在宿主机上): 看父进程输出\n");

  /* 启动 shell，让用户可以观察状态 */
  char *argv[] = {"/bin/sh", NULL};
  execv("/bin/sh", argv);
  perror("execv");
  return 1;
}

int main(void) {
  char *stack = malloc(STACK_SIZE);
  if (!stack) { perror("malloc"); return 1; }

  int flags = CLONE_NEWNET  /* 新网络栈 */
  | CLONE_NEWPID  /* 新 PID 空间 */
  | CLONE_NEWUTS  /* 新主机名 */
  | SIGCHLD;

  pid_t pid = clone(child_fn, stack + STACK_SIZE, flags, NULL);
  if (pid == -1) { perror("clone"); return 1; }

  printf("parent: 容器进程 PID = %d\n", pid);
  printf("parent: 现在可以在另一个终端执行:\n");
  printf("  ip link add veth-host type veth peer name veth-ct\n");
  printf("  ip link set veth-ct netns %d\n", pid);
  printf("  ... (详见 setup_netns.sh)\n\n");

  waitpid(pid, NULL, 0);
  free(stack);
  return 0;
}
```

完整代码见 `examples/containers/02-netns/netns_demo.c`。配合 `setup_netns.sh` 使用效果更佳 — 先启动 C 程序创建容器进程，然后用脚本配置网络。

---

## 五、用 tcpdump 看包的旅程

理论讲完了，来实际抓包验证。假设容器（10.0.0.2）要 ping 外部的 8.8.8.8：

```
# 终端 1: 在 bridge 上抓包
sudo tcpdump -i br0 -n icmp

# 终端 2: 在宿主机出口抓包
sudo tcpdump -i eth0 -n icmp

# 终端 3: 在容器里 ping
ping -c 1 8.8.8.8
```

你会看到这样的流程：

**br0 上**（容器端）：

```
10.0.0.2 > 8.8.8.8: ICMP echo request
8.8.8.8 > 10.0.0.2: ICMP echo reply
```

**eth0 上**（出口端，经过 NAT）：

```
192.168.1.100 > 8.8.8.8: ICMP echo request  # 源地址被 MASQUERADE 替换
8.8.8.8 > 192.168.1.100: ICMP echo reply
```

看到区别了吗？在 `br0` 上看到的源地址是容器的 10.0.0.2，但到了 `eth0` 就变成宿主机的 192.168.1.100 了。这就是 MASQUERADE 的工作 — conntrack 记住了这个映射关系，把回来的包正确地送回给容器。

包的完整路径：

```
容器 eth0 (10.0.0.2)
  → veth pair
  → br0 (bridge 转发)
  → iptables POSTROUTING (MASQUERADE: 10.0.0.2 → 192.168.1.100)
  → 宿主机 eth0
  → 互联网
```

如果你对网络栈的每一层感兴趣，可以看 [C10K 到 C10M](https://quant67.com/post/system-design/c10k/c10k.html) 那篇。容器网络最终还是走的内核网络栈，性能瓶颈和优化手段都一样。

---

## 六、Docker 为什么创建 docker0 bridge

你安装完 Docker 后执行 `ip addr`，会看到一个叫 `docker0` 的接口。现在你知道它是什么了 — 就是我们手动创建的 `br0`。

Docker 默认网络模式（bridge mode）的架构：

1. 启动时创建 `docker0` bridge，默认网段 172.17.0.0/16
2. 每个容器启动时，创建一对 veth，一端连 `docker0`，一端放进容器
3. 容器内的 IP 由 Docker 的 IPAM（IP Address Management）分配
4. `iptables -t nat -A POSTROUTING -s 172.17.0.0/16 ! -o docker0 -j MASQUERADE`

多容器场景下：

```
Container A (172.17.0.2)  ←→  veth-a  ←→  docker0 (172.17.0.1)  ←→  veth-b  ←→  Container B (172.17.0.3)
  ↓
  iptables MASQUERADE
  ↓
  eth0 (宿主机)
  ↓
  Internet
```

因为 `docker0` 是 L2 bridge，Container A 和 Container B 可以直接通信，不需要经过 NAT。只有出外网的流量才需要 MASQUERADE。

这也是为什么 Docker Compose 里的多个服务默认可以互相 ping — 它们都连在同一个 bridge 上。Docker 还会帮你配 DNS，让你可以用服务名访问。

### bridge 的局限

bridge 模式简单好用，但跨主机通信就不行了。Node A 的容器怎么访问 Node B 的容器？这就需要 overlay network（VXLAN）、host 模式、或者 CNI 插件（Flannel、Calico、Cilium）。

同一个 bridge 上的容器彼此也能直接看到 ARP 广播。这很方便，但意味着二层隔离几乎没有。Kubernetes 里的 sidecar、本地代理、多网卡容器，本质上也只是往同一个 netns 再塞一块 veth 和更多路由/iptables 规则，不是什么额外的魔法。

Cilium 用 eBPF 替代了 iptables，如果你对 eBPF 感兴趣，可以看 [这篇文章](https://quant67.com/post/linux/ebpf/ebpf.html)。

---

## 七、iptables MASQUERADE vs nftables：新旧之争

我们一直在用 `iptables`，但实际上 iptables 的内核后端（xt_tables）已经逐渐被 nftables 替代了。

```
# iptables 方式
iptables -t nat -A POSTROUTING -s 10.0.0.0/24 ! -o br0 -j MASQUERADE

# nftables 等价写法
nft add table nat
nft add chain nat postrouting { type nat hook postrouting priority 100 \; }
nft add rule nat postrouting ip saddr 10.0.0.0/24 oifname != "br0" masquerade
```

为什么要迁移？

  
|对比项|iptables|nftables|
|---|---|---|
|规则匹配|线性遍历每条规则|支持集合（sets）和映射（maps），O(1) 查找|
|内核 API|每次操作全量替换表|增量更新|
|语法|每个协议族一个命令（iptables, ip6tables, arptables）|统一的 `nft` 命令|
|原子性|不支持事务|原子提交多条规则|

对于容器场景，几百条 iptables 规则（每个容器几条）开始出现性能问题。Kubernetes 的 kube-proxy 在 iptables 模式下，Service 数量多了之后延迟明显增加，这也是为什么有了 IPVS 模式和 eBPF 替代方案。

现在大多数容器运行时还是默认用 iptables（实际上可能是 iptables-nft，即 iptables 语法 + nftables 内核后端）。但趋势很明确：nftables 是未来。

---

## 八、权限问题：为什么非 root 不能 CLONE_NEWNET

你可能尝试过不加 `sudo` 跑我们的代码，得到了：

```
clone: Operation not permitted
```

`CLONE_NEWNET` 需要 `CAP_SYS_ADMIN` 能力。这不只是因为网络栈是敏感资源 — 更重要的原因是 **network namespace 可以绕过基于 UID 的网络策略**。

想象一下：普通用户创建一个 network namespace，在里面配自己的 iptables，绑定特权端口（< 1024），或者直接抓取宿主机的 raw socket。这会打开巨大的安全漏洞。

### 但有一个例外：User Namespace

如果你先创建一个 User namespace（`CLONE_NEWUSER`），在那个 namespace 里你就是”root”。然后你可以在这个 User namespace 里创建其他 namespace，包括 network namespace：

```
// 普通用户可以这样做
int flags = CLONE_NEWUSER  /* 先创建 user namespace，获得"假 root" */
  | CLONE_NEWNET  /* 然后就可以创建 net namespace 了 */
  | SIGCHLD;

pid_t pid = clone(child_fn, stack + STACK_SIZE, flags, NULL);
```

但这个 network namespace 里的网络配置受限 — 你不能创建 veth pair 连到宿主机的 namespace（因为那需要宿主机的 `CAP_NET_ADMIN`）。

这就是 rootless 容器（Podman 的默认模式）面临的核心挑战。它们通常用 slirp4netns 或 pasta 来做用户态网络栈，性能比 veth + bridge 差，但不需要 root。我们在 [第九篇 Rootless 容器](https://quant67.com/post/containers/09-rootless/rootless.html) 会详细讨论。

---

## 九、动手实验：一键搭建容器网络

说了这么多，不如亲手试试。用 `examples/containers/02-netns/setup_netns.sh` 可以一键完成完整的网络配置：

脚本会： 1. 创建一个 network namespace（用 `ip netns`） 2. 创建 bridge `br0` 3. 创建 veth pair 4. 配置 IP、路由、NAT 5. 在容器 namespace 里测试联网 6. 最后清理所有资源

核心步骤摘录：

```
# 创建 namespace
ip netns add container0

# 创建 bridge
ip link add br0 type bridge
ip addr add 10.0.0.1/24 dev br0
ip link set br0 up

# 创建 veth pair 并连接
ip link add veth-host type veth peer name veth-ct
ip link set veth-host master br0
ip link set veth-host up
ip link set veth-ct netns container0

# 容器内配置
ip netns exec container0 ip link set lo up
ip netns exec container0 ip link set veth-ct name eth0
ip netns exec container0 ip addr add 10.0.0.2/24 dev eth0
ip netns exec container0 ip link set eth0 up
ip netns exec container0 ip route add default via 10.0.0.1

# NAT
echo 1 > /proc/sys/net/ipv4/ip_forward
iptables -t nat -A POSTROUTING -s 10.0.0.0/24 ! -o br0 -j MASQUERADE

# 验证
ip netns exec container0 ping -c 2 8.8.8.8
```

当你看到 ping 成功的那一刻，就理解了容器网络的全部本质。

---

## 十、深入一点：netlink — 内核的网络配置 API

前面我们一直用 `ip` 命令。但 `ip` 命令底层调用的是 **netlink** — Linux 内核的用户态通信接口。

真正的容器运行时（runc、crun）不会 fork 出 `ip` 命令来配网络，它们直接用 netlink socket 操作：

```c
#include <linux/netlink.h>
#include <linux/rtnetlink.h>

// 打开 netlink socket
int nl_sock = socket(AF_NETLINK, SOCK_RAW, NETLINK_ROUTE);

// 构造创建 veth pair 的消息
struct {
  struct nlmsghdr  nlh;
  struct ifinfomsg ifm;
  char  attrbuf[1024];
} req;

// ... 填充 IFLA_IFNAME, IFLA_LINKINFO, VETH_INFO_PEER 等属性 ...
// ... 光是创建一对 veth 就需要几十行代码 ...

send(nl_sock, &req, req.nlh.nlmsg_len, 0);
```

Go 语言有 `vishvananda/netlink` 库，Rust 有 `rtnetlink` crate，封装得很好。但纯 C 的 netlink 编程是体力活 — 这也是为什么我们的示例代码用 `system("ip ...")` 来演示。理解概念是第一步，工程优化是第二步。

---

## 十一、容器网络的性能代价

veth + bridge + NAT 不是免费的。每个包经过的路径：

1. 容器内的网络栈处理（TCP/IP）
2. 通过 veth pair 传到宿主机
3. bridge 进行 L2 转发
4. iptables/netfilter 规则匹配（NAT）
5. 宿主机的网络栈再处理一次
6. 最终从物理网卡发出

和直接在宿主机上跑相比，容器网络多了 2-4 次协议栈遍历和 netfilter 处理。在高吞吐场景下（比如 [C10K 问题](https://quant67.com/post/system-design/c10k/c10k.html)），这个开销不可忽视。

绕过方案：

  
|方案|原理|适用场景|
|---|---|---|
|`--net=host`|容器共享宿主机网络栈，零开销|对隔离要求不高的高性能场景|
|macvlan/ipvlan|容器直接拿物理网卡的子接口|需要 L2 可达的场景|
|SR-IOV|硬件虚拟化网卡|极致性能（DPDK、NFV）|
|eBPF 替代 iptables|[Cilium](https://quant67.com/post/linux/ebpf/ebpf.html) 用 BPF 程序替代 netfilter|Kubernetes 大规模集群|

Docker 的 `--net=host` 是最粗暴的优化：直接不隔离。性能和裸机一样，但容器间可以互相看到网络接口。Redis、Nginx 这类对延迟敏感的服务经常这么用。

---

## 十二、总结一下我们学到了什么

从零搭建容器网络的完整链路：

```
CLONE_NEWNET → 空网络栈
  → 创建 veth pair（虚拟网线）
  → 一端连 bridge（虚拟交换机）
  → 另一端移入容器
  → 配 IP + 路由
  → iptables MASQUERADE（NAT）
  → 容器可以上网了
```

这套架构从 Docker 0.x 沿用至今，简单、可靠、够用。Docker 的网络创新不在于发明新技术，而在于把已有的内核能力（namespace、veth、bridge、netfilter）自动化串起来。

但”够用”不代表”快”。每个从容器出去的包都要经过 **veth → bridge → netfilter → NAT**，至少两次 netfilter 遍历。在 Kubernetes 集群里，当 iptables 规则膨胀到几万条（每个 Service 一组规则），网络延迟可以劣化到令人惊讶的程度。[第十一篇](https://quant67.com/post/containers/11-network-perf/network-perf.html)会用 benchmark 数据量化这个代价。

到目前为止，我们的”容器”有了： - 是 PID 隔离（[第一篇](https://quant67.com/post/containers/01-namespaces/namespaces.html)） - 是 主机名隔离 - 是 挂载点隔离 - 是 IPC 隔离 - 是 **网络隔离 + 连通性**（本篇） - 否 独立的根文件系统 — 现在容器还是用宿主机的 `/`

下一篇，我们解决最后这个大问题：[用 pivot_root 给容器一个自己的根文件系统](https://quant67.com/post/containers/03-rootfs/rootfs.html)。到那时候，我们的手搓容器就真的可以跑 Alpine Linux 了。

## 相关阅读

- [Linux Namespaces：用 50 行 C 隔离一个进程](https://quant67.com/post/containers/01-namespaces/namespaces.html) — 本系列第一篇，PID/UTS/Mount/IPC namespace
- [eBPF：Linux 内核的隐藏武器](https://quant67.com/post/linux/ebpf/ebpf.html) — Cilium 用 eBPF 替代 iptables 做容器网络
- [跨越世纪的挑战：C10K 到 C10M](https://quant67.com/post/system-design/c10k/c10k.html) — 网络性能的终极追问，容器网络是其中一环

## 同主题继续阅读

把当前热点继续串成多页阅读，而不是停在单篇消费。

2026-04-01 · linux / containers

### [【从零造容器】Linux Namespaces：用 50 行 C 隔离一个进程](https://quant67.com/post/containers/01-namespaces/namespaces.html)

容器不是魔法。它就是几个系统调用。本文用 C 从 clone() 开始，逐个开启 PID/UTS/Mount/IPC namespace，看隔离到底是怎么回事。50 行代码，你就拥有了一个'容器'的雏形。

2026-04-02 · linux / containers

### [【从零造容器】Mount Namespace 与 pivot_root：构建容器文件系统](https://quant67.com/post/containers/03-rootfs/rootfs.html)

chroot 不是安全边界——10 行 C 就能逃出去。本文用 pivot_root 构建真正隔离的容器根文件系统：从 Alpine minirootfs 到设备节点，从 mount propagation 到只读根，一步步把容器的'地基'打牢。

2026-04-03 · linux / containers

### [【从零造容器】Cgroups v2：让容器不能吃掉整台机器](https://quant67.com/post/containers/04-cgroups/cgroups.html)

你给容器设了 512MB 内存限制，结果宿主机上的数据库被 OOM-kill 了。Cgroups 不是'加个限制'那么简单 — v1 的设计是个历史错误，v2 才是正确答案。本文用 C 代码从 mkdir 开始，手动创建 cgroup，设 CPU/内存/IO 限制，压测，看它怎么把进程关进笼子。

2026-04-06 · linux / containers

### [【从零造容器】用 Go 组装迷你容器运行时：把积木拼起来](https://quant67.com/post/containers/06-mini-runtime/mini-runtime.html)

五篇文章攒了一堆内核积木：namespace、netns、rootfs、cgroup、overlayfs。现在是时候用 Go 把它们拼成一个能跑的容器运行时了。不到 500 行代码，create/start/exec/kill/delete，五个命令走完容器的一生。