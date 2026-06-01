## 一文看懂Kubernetes网络整体架构
### 一、背景

最近老周做了这么个事情，就是我们总部云是HTTPS访问的，而边缘云是K8S的ServiceIp，协议是HTTP的，由于谷歌逐步禁止HTTPS页面加载HTTP资源，所以总部云访问不了边缘云的HTTP资源。老周的方案是在Nginx做一层反向代理，比如之前是访问/api接口，我现在就在前端代码中做个开关，并提供/proxy/api接口，开关控制走哪个接口；Nginx反向代理遇到/proxy开头的前缀匹配走代理ServiceIp，好，那ServiceIp哪里来的呢？我通过接口请求头放进去的，Lua脚本动态获取看走原先正常的代理还是我现在新增的这个反向代理。

我们总部网络访问边缘云的网络还要开墙，可能开墙没来得及或者整条链路网络有问题，那么可以在Nginx上做文章，把HTTPS 443 端口rewrite成原先HTTP的80端口，开关配置成走旧的HTTP那套逻辑，这样的话即使有问题也能无感兼容。

因为我们管理平台之前是走的ServiceIp的，这次调整成KLB，由于这次涉及到K8S中的网络内容，所以老周借此机会梳理下Kubernetes网络整体架构，希望大家会喜欢。

### 二、前置知识

**2.1 Kubernetes网络是什么**

Kubernetes网络是 **集群中容器间及与外部通信的基础架构** ，核心模型包括：

- **Pod网络‌** ：每个Pod分配独立IP，容器共享网络命名空间‌
- **服务发现‌** ：通过Service实现负载均衡和DNS解析‌
- **网络策略‌** ：控制Pod间流量的访问规则‌
- **‌CNI插件‌** ：如Flannel、Calico等实现跨节点通信‌

**2.2 Kubernetes网络层次**

- 容器网络接口（CNI）
- Pod网络
- Service网络
- Ingress网络

**2.2.1 容器网络接口（CNI）层**

> Kubernetes网络的底层是CNI层，它是一个独立的插件系统，用于为容器分配IP地址、创建网络接口和配置网络环境。 CNI插件可以在Kubernetes的各种云和物理环境中使用，例如AWS、GCP、Azure、OpenStack、Bare metal等。

这一网络层级专门 **处理Pod内部Docker容器间的通信问题** 。Pod作为Kubernetes最小的可调度单元，其设计允许一个或多个容器共存于同一执行环境中。这些容器通过本地回环地址（localhost/127.0.0.1）直接建立通信链路，由于绕过了传统网络协议栈的复杂处理流程，使得数据传输能够实现极低的延迟和显著提升的吞吐效率。

在Pod内部，所有容器通过共享网络命名空间实现无缝通信。这意味着它们共同使用同一个IP地址和端口资源池，既可以通过本地回环地址访问，也可以直接使用Pod分配的IP进行交互。这种共享机制使得容器间的通信就像同一台物理机上的不同进程间通信一样高效直接。

假设某个Pod包含容器A（业务处理器）和容器B（数据服务端），当容器A需要调用容器B的HTTP接口时：首先在配置文件中为容器B分配8080服务端口，随后容器A只需向http://localhost:8080发送请求即可。这种通信完全在Pod内部完成，既保障了数据传输的安全性，又确保了通信过程的高效性。

**2.2.2 Pod网络层**

> Pod网络层是 **容器的网络层** ， **它为Pod提供了单独的IP地址和网络空间** 。Pod网络层可以使用多种网络模型，如host模式、overlay模式、macvlan模式等。

这一网络层级专门 **解决集群中不同Pod之间的通信需求** 。作为Kubernetes最基本的调度单元，每个Pod都被分配了唯一的IP地址，且Pod内部的所有容器共享此IP和网络命名空间。这种设计确保了无论Pod位于集群中的哪个节点，都能通过标准IP网络协议进行直接通信。

Pod间的网络通信依赖于容器网络接口（CNI）插件来实现。业界提供了多种成熟的解决方案，包括Kubernetes原生的CNI插件，以及第三方开发的Flannel、Calico、Weave Net等。这些技术通过Overlay网络、BGP路由或MACVLAN等不同机制，构建起跨节点的Pod网络平面。

不同的CNI插件适用于特定的部署环境和技术需求。Flannel提供简单的Overlay网络方案，Calico则基于BGP协议实现高性能的网络策略，Weave Net通过自有协议建立加密通信隧道。根据集群规模、安全要求和性能需求，管理员可以选择最适合的插件来构建稳定可靠的Pod间通信网络。

**2.2.3 Service网络层**

Service网络层在Kubernetes架构中承担着关键的中间层角色，主要负责 **管理Service实体间的网络通信** 。它通过为每个Service分配一个稳定的虚拟IP地址，建立了一个抽象的服务访问端点，从而将前端请求智能地转发到后端对应的多个Pod实例。

该网络层通过kube-proxy组件与集群DNS协同工作，实现了自动化的服务发现和负载均衡功能。当客户端向Service的虚拟IP发起请求时，系统会根据预设的负载均衡策略（如轮询或会话保持），将流量分发到后端健康的Pod副本，确保服务的高可用性。

Service网络层支持ClusterIP、NodePort和LoadBalancer三种主要类型，分别适用于不同的部署环境。ClusterIP提供集群内部服务访问，NodePort通过节点端口暴露服务，LoadBalancer则借助云平台负载均衡器实现外部访问，这种分层设计满足了从开发测试到生产环境的完整部署需求。

**2.2.4 Ingress网络层**

Ingress网络层作为Kubernetes集群的流量入口网关，通过定义路由规则（如域名、路径）将外部HTTP/HTTPS请求精准分发至内部Service，实现七层流量治理。其核心价值在于：

- **统一入口** ：通过单一IP暴露多个服务，替代NodePort的端口暴露方式
- **高级路由** ：支持基于URL路径、主机名的精细化流量控制
- **扩展能力** ：集成SSL终止、认证等中间件功能

该层依赖Ingress控制器（如Nginx、Traefik）实现动态路由：

- 控制器持续监听Ingress资源变更
- 将规则转换为反向代理配置（如Nginx的location规则）
- 通过Service的ClusterIP将流量转发至后端Pod

**典型架构** ： **客户端 → Ingress Controller → Ingress规则 → Service → Pod**

**典型应用场景** ：

- **多服务路由‌** ：同一IP下按域名区分服务（如api.example.com vs www.example.com）
- **灰度发布‌** ：通过路径权重分配流量（如/old/ 10% /new/ 90%）
- **安全增强‌** ：集中管理HTTPS证书，集成WAF等安全中间件

### 三、Kubernetes网络整体架构

话不多说，我们直接上图，一图胜千言。下面这张图是我画的Kubernetes网络整体架构：

![在这里插入图片描述](https://developer.qcloudimg.com/http-save/yehe-2775261/d30c65421a3204692a17d139654a57be.png)

在这里插入图片描述

**‌第一层：容器间通信层‌**

Pod作为最小调度单元，其内部容器共享网络命名空间和唯一IP地址。容器间通过localhost直接通信，避免了网络协议栈开销，实现毫秒级延迟和高吞吐量的数据交换。这种设计特别适用于Sidecar模式等需要紧密协作的应用场景。

**‌第二层：Pod间通信层‌**

集群内各Pod通过CNI插件实现的网络平面进行通信。Flannel、Calico、Weave Net等插件分别采用VXLAN、BGP路由或Overlay网络等技术，确保跨节点Pod能够通过标准IP协议直接互联，形成扁平化网络空间。

**‌第三层：服务抽象层‌**

Service作为关键抽象层，通过ClusterIP为后端Pod组提供稳定访问端点。结合kube-proxy和CoreDNS实现服务发现与负载均衡，将请求智能分发至健康Pod实例，保障服务的高可用性和弹性扩展。

**第四层：外部接入层‌**

通过Ingress、NodePort和LoadBalancer三种机制暴露服务到外部网络。Ingress控制器提供七层路由能力，NodePort通过节点端口映射，LoadBalancer则借助云平台负载均衡器，形成完整的对外服务通道。

该网络模型通过清晰的职责分离，构建了灵活、可扩展且安全的通信框架，为微服务架构提供了坚实的网络基础设施支撑。

### 四、Kubernetes网络插件

Kubernetes 是一个强大的容器编排平台，它提供了多种网络插件，用于在集群中实现容器之间和容器与外部网络的通信。以下是几种常用的 Kubernetes 网络插件：

- Kube-router
- Flannel
- Calico
- Weave Net
- Cilium

**4.1 Kube-router**

Kube-router 是一种 **基于 BGP 协议的容器网络方案** ，它可以在集群中创建一个虚拟网络，并使用 BGP 协议来管理容器之间的通信。具体来说，Kube-router 会为每个容器分配一个唯一的 IP 地址，并使用 BGP 协议将这些 IP 地址添加到路由表中。Kube-router 还支持多种网络拓扑结构，包括扁平网络、网格网络和点对点网络等。

**使用示例：**

> 以下是使用 Kube-router 网络插件的示例代码， 演示前提：已经安装了 Kubernetes 集群和 Kube-router 网络插件：

创建一个 Kubernetes Deployment

```javascript
apiVersion: apps/v1
kind:Deployment#资源类型为Deployment
metadata:
name:nginx-deployment
spec:
replicas:2
selector:
    matchLabels:
      app:nginx
template:
    metadata:
      labels:
        app:nginx
    spec:
      containers:
      -name:nginx
        image:nginx:latest
        ports:
        -containerPort:80
```

创建一个 Kubernetes Service

```javascript
apiVersion: v1
kind:Service#资源类型为service
metadata:
name:nginx-service
spec:
selector:
    app:nginx
ports:
    -name:http
      port:80
      targetPort:80
type:ClusterIP
```

创建一个 Kubernetes Pod，使用 Kube-router 网络插件

```javascript
apiVersion: v1
kind:Pod#资源类型为pod
metadata:
name:kube-router-pod
spec:
containers:
-name:kube-router-container
    image:kube-router/kube-router:v1.3
    command:
    -kube-router
    -run
    args:
    ---run-router=false
    ---run-firewall=false
    ---run-service-proxy=false
    ---run-egress=false
    ---enable-cni=true
    ---cni-bin-dir=/opt/cni/bin
    ---cni-conf-dir=/etc/cni/net.d
    ---cni-network-config='{
        "cniVersion":"0.3.1",
        "name":"kube-router",
        "type":"kube-router"
      }'
    volumeMounts:
    -name:cni-bin
      mountPath:/opt/cni/bin
    -name:cni-conf
      mountPath:/etc/cni/net.d
volumes:
-name:cni-bin
    hostPath:
      path:/opt/cni/bin
-name:cni-conf
    hostPath:
      path:/etc/cni/net.d
```

在Pod中通过容器化方式部署Kube-router进程，启动时通过命令行参数配置运行模式： `--run-router=true` 启用路由控制器， `--run-firewall=true` 启用防火墙策略， `--run-service-proxy=true` 启用服务代理。各控制器通过健康检查端口（默认20244）维持心跳，若组件在同步时间+5秒内未发送心跳，将被标记为不健康状态。同时支持IPv6/双协议栈配置，确保网络功能的完整性。

使用hostPath卷将宿主机CNI配置文件目录、网络插件目录挂载到容器内部，使kubelet能够正确调用网络插件。这种挂载方式保证了kube-router能够访问到必要的网络配置文件和二进制工具，为集群提供完整的网络服务能力。

**4.2 Flannel**

Flannel **通过在每个节点创建虚拟网络实现跨节点容器通信** ，支持 VXLAN 或 UDP 作为底层封装协议。其 **核心机制是为每个节点分配独立的 IP 子网，并将容器 IP 映射至对应子网中** ，同时 **依赖 etcd 等分布式键值存储系统统一管理网络状态信息** ，确保集群内网络配置的一致性。

**使用示例：**

> 以下是使用 Flannel 网络插件的示例代码， 演示前提：已经安装了 Kubernetes 集群和 Flannel 网络插件

Kubernetes Deployment 与 Kubernetes Service 和上面4.1的一样，这里说下Pod的创建，创建一个 Kubernetes Pod，使用 Flannel 网络插件。

```javascript
apiVersion: v1
kind:Pod#资源类型
metadata:
name:flannel-pod
spec:
containers:
-name:flannel-container
    image:quay.io/coreos/flannel:v0.14.0
    command:
    -/opt/bin/flanneld
    args:
    ---ip-masq
    ---kube-subnet-mgr
    ---iface=eth0
    securityContext:
      privileged:true
    volumeMounts:
    -name:flannel-cfg
      mountPath:/etc/kube-flannel/
volumes:
-name:flannel-cfg
    configMap:
      name:kube-flannel-cfg#挂载
```

在该配置示例中，通过在Pod容器内启动Flannel守护进程（flanneld）来管理网络配置。通过命令行参数灵活设置运行模式，如指定网络后端类型（VXLAN/UDP）、启用IP伪装等功能。Flannel通过etcd存储集群网络状态信息，包括节点子网分配和路由规则。各组件通过健康检查端口（默认8285）维持运行状态，确保网络服务的持续可用性。

使用ConfigMap卷挂载Flannel配置文件，实现配置的集中管理和动态更新。实际部署时需要根据具体网络环境调整关键参数，包括网络地址范围、子网划分规则和后端传输协议。建议参考Flannel官方文档获取详细的配置参数说明和最佳实践指南。

**4.3 Calico**

Calico采用BGP协议构建高性能容器网络，通过分布式路由机制实现Pod间直接通信。其核心工作原理包含三个关键层面：

**‌路由分发机制‌**

Calico在每个节点部署Felix组件和BIRD(BGP客户端)，Felix负责配置本地路由规则，BIRD则通过BGP协议将路由信息广播至集群所有节点‌。每个Pod获得独立IP地址，路由信息通过BGP协议在节点间同步，形成扁平化网络架构‌。

**‌网络通信流程‌**

当容器A(IP:192.168.1.2)需要与容器B(192.168.2.3)通信时，数据包直接通过底层网络转发至目标节点，无需额外封装‌。这种纯三层设计避免了Overlay网络性能损耗，提供接近物理网络的传输效率。

**‌安全策略体系‌**

基于iptables或eBPF技术实现细粒度网络策略，可定义基于标签选择器的访问控制规则。同时支持网络隔离、安全组等高级功能，确保多租户环境下的网络安全‌。

这种架构使Calico **特别适合需要高性能网络和大规模部署的场景** ，同时保持操作简化和策略灵活性。

**4.4 Weave Net**

Weave Net 是 Kubernetes 中一种基于 VXLAN 或 UDP 的容器网络解决方案，它通过以下机制实现跨主机通信：

**虚拟网络构建‌**

Weave Net 在集群中创建覆盖网络（Overlay Network），为每个容器分配唯一 IP 地址。通过运行在节点上的 Weave Router 组件，建立虚拟网络设备，使不同主机上的容器能像在同一局域网内直接通信‌。

**数据传输协议‌**

支持 VXLAN 和 UDP 两种协议：

- VXLAN 模式通过封装数据帧实现跨主机通信，利用 VTEP 设备进行隧道传输‌
- UDP 模式通过轻量级封装降低开销，但可能牺牲部分可靠性‌

**‌网络拓扑灵活性‌**

支持扁平网络（所有节点直连）、网格网络（多跳路由）和点对点网络（特定节点直连）等多种拓扑结构，适应不同规模的集群需求‌。

**核心优势**

- **简单易用‌** ：安装配置仅需几条命令，无需复杂网络知识‌
- **原生体验‌** ：容器间直接通过 IP 通信，无需端口映射‌
- **‌自动发现‌** ：容器启动后自动加入网络，无需手动配置‌
- **加密通信‌** ：支持容器间通信加密，提升安全性‌

**4.5 Cilium**

Cilium 是 Kubernetes 中基于 eBPF 技术的创新型容器网络方案，其核心设计 **聚焦于内核层面的高效通信与安全控制** 。以下从技术实现和应用优势两个维度展开：

**‌4.5.1 技术实现机制‌**

**eBPF 内核级拦截‌**

Cilium 在每个节点部署轻量级 eBPF 程序，直接在内核空间拦截网络数据包。通过动态加载的 eBPF 过滤器，实时监控容器间流量，实现低延迟的数据包处理（相比传统 iptables 规则链，性能提升显著）。

**‌多协议兼容性‌**

支持网络层协议（如 BGP、IP-in-IP）实现跨节点路由，同时兼容应用层协议（如 HTTP、gRPC），通过 eBPF 程序动态解析协议头，实现七层流量控制。例如，可基于 HTTP 路径或 gRPC 方法名定义网络策略。

**‌网络安全策略‌**

基于 eBPF 的标签选择器（Label Selector）实现细粒度访问控制，支持实时流量监控和攻击防御。例如，可限制特定标签的 Pod 仅能访问特定端口的服务，或阻断异常流量模式。

**‌‌4.5.2 应用优势‌**

- ‌高性能网络‌：eBPF 技术避免用户态与内核态切换，数据包处理延迟降低至微秒级，适合高吞吐量场景（如微服务架构）。
- ‌安全即代码‌：通过 Kubernetes CRD 定义网络策略，实现安全策略与应用的统一管理，支持自动化合规审计。
- 可观测性增强‌：集成 Prometheus 和 Grafana，提供实时流量监控、拓扑可视化和故障诊断能力。

**‌4.6 小结**

Kubernetes 提供 Flannel、Calico、Weave Net 和 Cilium 等多样化网络插件，能够灵活适配不同规模的集群部署场景，在选择时需综合评估网络可靠性（如节点故障容错能力）、性能（如数据包转发效率）和安全性（如策略隔离强度）等核心要素，确保方案与业务需求精准匹配
