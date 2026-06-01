---
credibility: low
---

## 引言

### 技术背景

自2014年由Google开源以来，Kubernetes迅速崛起，凭借着其强大的容器编排能力、灵活的扩展性以及丰富的生态系统，稳坐云原生技术栈的头把交椅。它不仅仅是一个容器管理平台，更是云原生架构的引擎，驱动着应用程序的部署、管理和自动化的持续进化，为开发者提供了前所未有的敏捷性和可移植性。

然而，伴随着Kubernetes所带来的巨大灵活性与可扩展性，其内部网络架构的复杂性也日益凸显，成为许多运维工程师和开发者面临的一大挑战。Kubernetes网络的设计旨在实现容器间的无缝通信，同时保障服务发现的便捷性与网络策略的可实施性。这一目标的达成依赖于一系列复杂的组件与抽象概念，包括Pod网络、Service、Ingress、网络策略(NetworkPolicy)以及容器网络接口(CNI)等。每一步配置与调整都可能影响到整个集群的通信效率与安全性，因此，深入理解和掌握Kubernetes网络模型的运作机制，对于高效排查与解决网络故障而言至关重要。

**该单位的A系统在本地私有化环境中部署，采用Docker和Kubernetes（简称K8s）构建了一个高度灵活且可扩展的基础设施** 。私有化部署意味着所有的资源和服务都在内部网络中运行，不依赖公有云服务，这给予了企业更大的控制权和数据隐私保护，但同时也带来了与公有云平台相比的各种差异，特别是Kubernetes（K8s）网络在私有化部署环境下可能会遇到一系列独特的问题，这些问题往往源自于网络架构的复杂性、企业内部网络的特定配置、以及K8s网络组件与私有云平台之间的兼容性。

本文正是在此背景下应运而生，旨在通过实战导向的故障排查指南，带领读者深入Kubernetes网络的每一个角落，揭开其复杂面纱，从而在遇到网络问题时能够迅速定位症结，采取有效措施，保障云原生应用的稳定运行与高效交付。

### 故障背景

这篇文章主要还是想纪实+分析一下，因为作者本人工作单位特殊，所以具体的截图暂时无法提供，这里也不能直接展示出来，请见谅！涉及到的系统也统称为A系统、B系统等，以此类推。

具体的背景是这样的：

**第一部分** ：上级单位开通了一条新内部专线想访问我们k8s架构部署的 **A系统** ，但是很尴尬的一个问题是，该单位的办公网段和我们这个k8s内部集群的 Pod 网段是一致，而由于这个A系统是极其重要的业务系统，全天不间断运行，所以也不敢从内部下手来调整， **最终解决的方案是采用边界防火墙做NAT转换后再进入k8s内部解析** 。

**第二部分** ：当网络问题解决后，上级单位又提出新要求，需要我们的A系统能够直接访问他们B系统域名，当时想着就直接在我们A系统的k8s主节点上加了域名解析，结果保存刷新缓存后A系统所有的对外服务全部无法访问了，排查时发现服务是正常的，服务器内部端口是通的，但是内网其他网段访问不通，即使删除之前的域名解析配置仍然无法访问，经两个小时排查无果后， **最终解决方案是重启服务器，恢复正常** 。

**第三部分** ：除去这两个背景外，还有一个较常发生的就是 **容器网络抖动问题** ，A系统在近一年来有多次出现外部访问容器服务时响应延迟的情况，有时快速响应，有时则非常缓慢，有时甚至出现应用程序报告服务暂时无法访问的情况，这些故障往往持续不到10分钟且随机发生的，难以复现， **目前暂时使用开源工具KubeSkoop exporter来监测和定位这一现象的发生** 。

## Kubernetes 网络基础回顾

在深入探讨Kubernetes（K8s）网络故障排查与优化之前，有必要先奠定坚实的理论基础，理解其背后复杂而又精妙的网络模型。Kubernetes网络模型是云原生应用部署的核心支柱之一，它通过高度抽象化的设计，实现了容器间的无缝通信，同时保证了服务的可发现性与网络策略的灵活性。这一模型主要由三大核心要素构成： **Pod网络、Service网络以及CNI（容器网络接口）** ，共同构建起Kubernetes复杂网络生态的骨架。

**Pod网络** ：Pod作为Kubernetes中的最小部署单元，其网络模型的核心在于为每个Pod提供一个独立的IP地址，并确保Pod间的直接通信如同它们位于同一物理网络一般无缝。这一设计要求底层网络基础设施必须能够识别和路由到这些虚拟的Pod IP，从而实现容器间的高效通信。

**Service网络** ：随着应用规模的扩大，静态的Pod间通信难以满足动态服务发现和负载均衡的需求。Kubernetes Service应运而生，它为一组具有相同功能的Pod提供了统一的访问入口和固定IP，通过Label Selector自动关联相应的Pod集合，实现灵活的服务路由和透明的水平扩展。此外，Kubernetes还支持多种类型的Service，如ClusterIP、NodePort、LoadBalancer和ExternalName，以适应不同的暴露服务需求。

**CNI（容器网络接口）** ：为了实现上述网络模型，Kubernetes采用了插件化的方式，允许用户根据自身需求选择合适的网络方案，这就是CNI（Container Network Interface）的角色。CNI提供了一套标准的接口规范，允许第三方网络插件（如Flannel、Calico、Weave Net等）无缝集成，负责Pod的网络创建、删除以及IP地址分配等操作，确保了网络配置的灵活性和可移植性。

而这三大核心要素，也构成了四类通信要求，这也是Kubernetes网络模型设计的目标。

- **同一Pod内容器的通信（Contarner to Contarner）**
- **Pod间的通信（Pod to Pod）**
- **Service 到 Pod间的通信（Service to Pod）**
- **集群外部与 Service 之间的通信（External to Service）**

### 同一Pod内容器的通信

在最基础的层面上，Kubernetes 网络模型确保了Pod内部容器间的高效通信。由于Pod内的所有容器共享同一个网络命名空间，包括IP地址和端口空间， **且不同Pod之间不存在端口冲突的问题，每个Pod都有自己的IP地址** ，因此容器之间可以直接通过localhost或环回接口（loopback interface）进行通信，无需任何额外配置。这一设计极大地简化了在同一Pod内多个容器间紧密协作的应用场景，如一边容器处理前端请求，另一边容器执行后台计算。如下图所示， **Pod N** 内的Contarner1、Container2、Container3之间通信即为容器通信。

![](https://developer.qcloudimg.com/http-save/yehe-9667716/2a9b8cd602ec6ece62ede14b0dd13b63.png)

### Pod间的通信

Kubernetes 为每个Pod分配唯一的IP地址，并要求网络基础设施（通常通过CNI插件实现）能够路由到这些Pod IP，从而实现Pod间的直接通信。这意味着，无论Pod部署在集群的哪个节点上，它们都能如同在同一个局域网内一样相互通信。这一特性对于构建分布式应用系统至关重要，其中服务间的交互频繁且复杂。

![](https://developer.qcloudimg.com/http-save/yehe-9667716/36ab874ce9d69ab0508b34bc5494b31c.png)

每个Pod都包含一个或多个容器（container1、container2和container3），以及一个名为Pause的特殊容器。Pause容器的作用是为其他容器提供网络共享空间。

每个工作节点上有一个二层交换网络（cbr0），用于连接Pod和宿主机。每个Pod都有一个独立的IP地址，分别位于不同的子网中。

Pod间的通信可以通过二层交换网络实现，因为每个Pod都有自己的MAC地址。当一个Pod向另一个Pod发送数据包时，数据包的目标MAC地址会被设置为接收Pod的MAC地址。在这种情况下，数据包将通过二层交换网络传输，直到到达目标Pod所在的节点。

一旦数据包到达目标节点，它将通过cbr0接口进入目标Pod。然后，数据包将被路由到目标Pod中的适当容器。这种路由通常是通过iptables规则完成的，这些规则将流量定向到正确的容器。

### Service 到 Pod间的通信

在上述方式中，尽管每个Pod都有自己的IP地址， **但这些地址并不是全局可达的** 。要让外部网络可以访问这些Pod，需要使用Service进行代理和负载均衡。Service会为Pod提供一个公共的IP地址和端点列表，外部网络可以通过这个IP地址访问服务。

为了实现服务的发现与负载均衡，Kubernetes **引入了Service概念** 。Service通过标签选择器（label selectors）绑定到一组具有相同标签的Pods，为这些Pods提供一个统一的访问入口和稳定IP。当客户端通过Service的IP和端口发起请求时，Kube-proxy（Kubernetes的网络代理组件）会根据配置的策略（如轮询、最少连接数等）将请求透明地转发给后端的一个或多个Pod。这一机制保障了服务的高可用性和可扩展性，同时也简化了客户端的配置管理。

![](https://developer.qcloudimg.com/http-save/yehe-9667716/70bd678e2fdabc76a1aa28a6ec89ab75.png)

其中,Service是一个逻辑概念，它代表了一组具有相同标签的Pod。在Kubernetes中，Service通过标签选择器（label selector）来确定哪些Pod属于该Service。当Service收到一个请求时，它会将请求转发到后端的一个或多个Pod。

在这个过程中，Netfilter扮演了关键角色。Netfilter是一种Linux内核中的网络包过滤和分发机制，它允许在数据包经过网络栈时对其进行修改和路由。在Kubernetes中，Netfilter被用来实现Service的负载均衡功能。

具体来说，当一个请求到达Service时，Netfilter会检查请求的目标IP地址和端口。如果目标IP地址是Service的IP地址，Netfilter将会把请求重定向到后端的一个Pod。这个过程称为SNAT（源地址转换）。Netfilter会随机选择一个后端Pod并将请求的源IP地址替换为Service的IP地址，这样后端Pod就可以知道请求来自Service而不是直接来自于客户端。

请求将通过Eth0 Host X或Host Y发送到选定的Pod。这是因为在Kubernetes中，每个Pod都有自己的网络空间，而每个节点也有自己的网络空间。为了使Pod能够与其他Pod和外部网络通信，每个节点都需要一个网桥（bridge），以便将Pod的网络空间连接到节点的网络空间。在Kubernetes中，这个网桥被称为cbr0。

因此，当请求到达节点时，它将通过cbr0桥接至选定的Pod。然后，请求将被路由到Pod中的适当容器。这种路由通常是通过iptables规则完成的，这些规则将流量定向到正确的容器。

### 集群外部与 Service 之间的通信

为了使外部客户端能够访问集群内部的服务，Kubernetes 提供了几种方式：NodePort、LoadBalancer和Ingress。NodePort暴露服务在每个节点的一个特定端口上，允许外部通过节点IP+端口直接访问；LoadBalancer（在公有云环境）自动创建云提供商的负载均衡器，将外部流量导向Service；而Ingress则更进一步，提供了HTTP/HTTPS层的路由规则，允许基于路径或域名将外部请求路由到不同的Service。这些机制确保了云原生应用不仅能在集群内部顺畅运行，也能安全高效地与外部世界交互。

**① NodePort** ：此方式下，Kubernetes会在每个集群节点上开放一个静态端口（NodePort），通过这个端口，外部客户端可以直接访问到Service映射的Pods。具体而言，用户可通过任何一个集群节点的IP地址加上NodePort来访问Service，格式如

```js
<NodeIP>:<NodePort>
```

这种方式简单直接，适用于测试环境或对访问来源有限制的场景，但请注意，由于所有节点都暴露了相同的端口，可能带来一定的安全风险，且网络流量需要手动分配到各个节点，无法实现自动负载均衡。

**② LoadBalancer** ：当需要为Service提供更高水平的外部访问能力，特别是需要自动负载均衡和高可用性时，LoadBalancer便成为首选方案。在这种模式下，Kubernetes会与云服务提供商集成，自动创建一个外部负载均衡器（如AWS的ELB、GCP的Load Balancer等）。这个外部负载均衡器负责接收外部流量，并根据预设策略（如轮询、最少连接数等）将其分发到集群内的多个节点，进而通过NodePort访问到对应的Service。这种方式不仅提供了更好的外部访问体验，也确保了服务的高可用性和扩展性，特别适合生产环境中的大规模应用部署。需要注意的是，使用LoadBalancer服务类型会产生云服务费用，并且配置与管理相对复杂，需要与云服务商的负载均衡服务紧密配合。

**③ Ingress** ：Ingress为Kubernetes集群提供了一种更加灵活和强大的流量管理和路由机制。不同于NodePort直接将服务绑定到节点的静态端口，也区别于LoadBalancer通过云提供商的负载均衡器分配外部访问入口，Ingress在更高级别的HTTP/HTTPS层面上工作，支持基于主机名和URL路径的路由规则，从而能够将进入的流量智能地导向到集群内多个Service的不同路径下。

Ingress资源定义了一系列规则，这些规则描述了如何将外部请求转发到内部Service。实际上，Ingress需要与一个Ingress Controller配合使用，该控制器是实际执行路由和负载均衡逻辑的组件。Ingress Controller监测Ingress资源的变动，并据此配置其后端的负载均衡或反向代理服务，以实现请求的正确路由。

例如，可以设置一条规则，使得访问www.example.com/blog的流量被路由到处理博客内容的Service，而www.example.com/shop的流量则导向至电子商务平台的Service，这一切都在同一个入口点（通常是单个公网IP地址）下完成，极大地提升了应用架构的灵活性和可维护性。

总结来说：

- **NodePort提供了基本的外部访问能力，适用于简单的测试或有限的访问需求。**
- **LoadBalancer通过云提供商的负载均衡服务，实现了更高级别的外部访问和自动流量分发，适用于生产环境。**
- **Ingress则进一步提升了流量管理的智能化和灵活性，支持基于URL路径和主机名的复杂路由，是构建现代微服务架构不可或缺的一部分。**

上述部分主要还是回顾了一下Kubernetes网络模型的几个核心方面和通信原理，下面就这次故障来做简要分析。

## 故障及分析

### 第一部分：Kubernetes 集群外的地址与集群内的 Pod 或 Service 网段冲突

一旦出现网络段冲突的情况，最容易引发以下三种问题：

- 冲突： 如果外部 IP 地址或网络段与内部 Pod 或 Service 的 IP 范围重叠， **网络数据包的路由可能会变得混乱** 。这是因为 Kubernetes 集群内外的网络无法区分。
- 路由问题： 网络路由可能会优先考虑其中一个网络。例如，如果 IP 被视为内部网络的一部分，从 Pod 到外部服务的请求可能永远不会离开集群。
- 服务访问： 如果外部 IP 地址被认为是集群内部的一部分，从集群外部访问服务可能变得有问题。

本次碰到的问题就是Kubernetes 集群无法区分内外网络，导致数据通信混乱，服务请求无法正确路由到目标位置，外部单位无法有效访问A系统。

面对这一问题最好的解决方案自然是在 **先期规划时做好网络地址分配** ，确保集群内部使用的IP地址范围与外部网络严格隔离，避免任何重叠。这包括为Pod、Service以及可能的外部访问接口如NodePort、LoadBalancer预先定义独立且不冲突的IP地址池，从而在 **源头上** 消除冲突风险，保证网络通信的顺畅与安全。但是事已至此，也没办法再去改变了，所以只有另辟蹊径。

第二种想到的方法就是可以 **让上级单位修改他们办公网段或者我们修改k8s集群内pod或Service的网段** ，但是很快这个也被否定了。因为人家是我们上级，凭啥说改就改？而且由于A系统极其关键，就算让我们直接修改Kubernetes集群内Pod或Service的网段也必定会导致现有服务的中断，影响业务连续性。

第三种想到的方法就是 **NAT转换** ，这可能也是代价最小的一种。在对应位置的防火墙上设置网络地址转换(NAT)规则。当上级单位的请求到达时， **通过NAT转换映射到一个不冲突的地址范围** ，然后再转发到K8s集群内的Pod。这样，尽管源地址最初与Pod网段冲突，但在实际传输过程中会被转换为一个安全、可接受的地址。

第四种是部署一个 **反向代理或API网关** ，但是这意味着又会新增 **部署级工作** ，且由于时间紧迫，所以这一方案也最终被搁置。

最终，我们还是采用 **NAT转换** 方式解决了这一问题。

![](https://developer.qcloudimg.com/http-save/yehe-9667716/027e0630eb3046505f0089df8968f51f.png)

具体实施过程也比较容易，唯一不同的是，由于我方防火墙功能有限，所以是让对方在出口防火墙上设置了NAT，具体需要明确的几点无非是源IP转换范围、目标IP范围、端口映射策略、NAT类型等。

这个故障带给我的启发就是，在 Kubernetes 集群 **设计阶段开始就真的需要考虑网络地址空间的唯一性与预留** 了，不能按照网上的教程一味照搬，从而忽视了自身环境的特性和潜在的外部因素。

### 第二部分：主节点新增域名解析后对外服务故障

这个故障就非常的致命了，是当时我的团队成员引发的，本意是想解决k8s内部解析外部域名的问题，但由于他几乎没有怎么接触过这个架构，所以说上来直接把主节点服务器里的host文件给改了，改完之后发现没生效，就给网卡重启了一下，重启之后整个A系统就彻底崩溃掉了，一开始在服务器内部连对应端口都无法telnet通，一番操作之后在服务器内部访问终于能通了，但外部访问端口依旧都不通，在排查两个小时后没有找到直接的解决方案，最终通过 **重启服务器** 解决。

这里也简单说一下这个故障吧，Kubernetes 集群 **默认配置** 通常只能解析集群内部的服务名（通过CoreDNS或kube-dns服务），直接解析外部域名的能力较弱，但是我们依然可以通过一些配置来实现对外部域名的解析，下面主要介绍一个k8s利用coredns解析集群外部域名的实例，具体可参考官方文档（ [https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/?spm=a2c6h.12873639.0.0.4e9e5cb0ph0Om9](https://cloud.tencent.com/developer/tools/blog-entry?target=https%3A%2F%2Fkubernetes.io%2Fdocs%2Fconcepts%2Fservices-networking%2Fdns-pod-service%2F%3Fspm%3Da2c6h.12873639.0.0.4e9e5cb0ph0Om9&objectId=2426104&objectType=1&contentType=undefined) ）。

#### 修改coredns配置文件

运行下面命令，添加rewrite stop 这部分配置块（ [https://coredns.io/plugins/rewrite/](https://cloud.tencent.com/developer/tools/blog-entry?target=https%3A%2F%2Fcoredns.io%2Fplugins%2Frewrite%2F&objectId=2426104&objectType=1&contentType=undefined) ） ，可以将解析请求中匹配到的 **xxx.a.b.c.com** 的域名转化为 **xxx.default.svc.cluster.local** 进行解析，且返回的结果中的域名仍显示为 **xxx.a.b.c.com** ：

```js
kubectl edit cm/coredns -n kube-system
```

修改为如下所示;

```js
# Please edit the object below. Lines beginning with a '#' will be ignored,
# and an empty file will abort the edit. If an error occurs while saving this file will be
# reopened with the relevant failures.
#
apiVersion: v1
data:
  Corefile: |
    .:53 {
        errors
        health {
           lameduck 5s
        }
        ready
        rewrite stop {
           name regex (.*)\.a\.b\.c\.com {1}.default.svc.cluster.local
           answer name (.*)\.default\.svc\.cluster\.local {1}.a.b.c.com
        }
        kubernetes cluster.local in-addr.arpa ip6.arpa {
           pods insecure
           fallthrough in-addr.arpa ip6.arpa
           ttl 30
        }
        prometheus :9153
        forward . /etc/resolv.conf {
           max_concurrent 1000
        }
        cache 30
        loop
        reload
        loadbalance
    }
kind: ConfigMap
metadata:
  creationTimestamp: "2024-06-02T12:12:21Z"
  name: coredns
  namespace: kube-system
  resourceVersion: "251"
  uid: be64b336-a0bf-4217-829b-78fbb062463c
```

这样修改后，等待几分钟配置就会自动生效了，此时可以解析到正确的结果。

或者也可以直接在里面添加host记录，如下：

```js
apiVersion: v1
data:
  Corefile: |
    .:53 {
        errors
        health
        kubernetes cluster.local in-addr.arpa ip6.arpa {
           pods insecure
           upstream
           fallthrough in-addr.arpa ip6.arpa
           ttl 30
        }
        hosts {
           XXX.XXX.XXX.XXX 待解析域名
           fallthrough
        }
        prometheus :9153
        forward . /etc/resolv.conf {
           max_concurrent 1000
        }
        cache 30
        loop
        reload
        loadbalance
    }
kind: ConfigMap
metadata:
  creationTimestamp: "2024-06-02T12:12:21Z"
  name: coredns
  namespace: kube-system
  resourceVersion: "251"
  uid: be64b336-a0bf-4217-829b-78fbb062463c
```

以上两种方法都可以实现集群对外部域名的解析，但如果不动本身的配置文件，也可以配置k8s服务器集群的resolv.conf 来新增dns服务器，再刷新k8s集群kube-dns重建以达到解析目的。

执行如下命令检查集群内部resolv.confg文件，确保集群内所有dns配置都一致，如不一致需要手动修改为一致。

```js
cat /etc/resolv.conf
```

再查看kubernetes 集群内 coredns容器

```js
kubectl get pods -n kube-system
```

<p style="text-align:center">!\[image.png\](https://ucc.alicdn.com/pic/developer-ecology/pmur6hy3nphhs\_c4e7588d4a7e48c286569c02cb309e30.png)

</p>

删除这两个等待自动重建即可。

```js
kubectl -n kube-system delete pod coredns-5d78c9869d-4ljkw 

kubectl -n kube-system delete pod coredns-5d78c9869d-zmjmr
```

<p style="text-align:center">!\[image.png\](https://ucc.alicdn.com/pic/developer-ecology/pmur6hy3nphhs\_b9779f9862734c7f93b52ca9e1319bcd.png)

</p>

上面主要是介绍了几个实现集群对外部域名解析的方法，扯的有些远了，不过确实也是比较有用处的。

而对于那次故障，由于业务部门一直催促，我们这边也没有更多的时间去细细排查了，无奈之下只得选择重启服务器来解决此问题，幸好成功解决了。

这个故障带来的启发就是，对于人员的技能培训其实至关重要，尤其是在依赖技术基础设施的环境中。有效的培训不仅能提升团队成员的技术实力，更能增强他们在面对突发事件时的冷静判断和快速响应能力；同时也是有所警醒， **在涉及到复杂网络的调整时，应当采取更加严谨和科学的方法，至少得有事先的规划、模拟测试、以及细致的回滚计划。**

### 第三部分：容器网络抖动问题

说实在的，这块目前我们也仍然没有能够 **根治** 的方法，因为其排查起来实在是困难，每次出现不到10分钟就自动恢复了，（甚至有的时候运维人员、业务人员自身都没察觉到异常），再想回溯起来又得等到下一次。

这里采用的方式主要是以可观测和可定位来缓解此类现象发生，使用到的工具是 **KubeSkoop exporter** 。

#### KubeSkoop exporter

基于网络处理的复杂链路、传统工具在云原生容器场景下的缺陷。基于云原生环境的网络观测要求，KubeSkoop 项目应运而生。

在介绍 KubeSkoop 的网络监测部分，也就是 KubeSkoop exporter 之前，我们先来回顾一下 KubeSkoop 项目的全貌。

KubeSkoop 是一个容器网络问题的自动诊断系统。它针对了网络持续不通问题，如 DNS 解析异常，service 无法访问等场景，提供了一键诊断的能力；针对网络抖动问题，如延迟增高、偶发 reset、偶发丢包等场景，提供了实时监测的能力。KubeSkoop 提供了全链路一键诊断、网络站延迟分析和网络异常事件识别回溯的能力。

![](https://developer.qcloudimg.com/http-save/yehe-9667716/36583d32bdf2f45ebcb499df1d3faa5f.png)

KubeSkoop exporter 基于 eBPF、procfs、netlink 等多种数据源的容器网络异常监控，提供了 Pod 级别的网络监控能力，能够提供网络监控指标、网络异常事件记录和实时事件流，覆盖驱动、netfilter、TCP 等完整协议栈和几十种异常场景，与云上 Prometheus、Loki 等可观测体系对接。

KubeSkoop exporter 提供了针对内核中不同位置采集信息的探针，支持探针的热插拔和按需加载的能力。开启的探针会以 Prometheus 指标或是异常事件的形式透出所采集到的统计信息或网络异常。

#### 如何使用

KubeSkoop exporter 适用于日常监控以及网络异常问题发生时的排查两种场景。这两种场景对 KubeSkoop exporter 的使用方式有所不同，下面简单介绍。

**日常监控**

![](https://developer.qcloudimg.com/http-save/yehe-9667716/0703d7e6a2bf972990d6ca75f703adf3.png)

在日常监控中，推荐使用 Prometheus 收集 KubeSkoop exporter 所透出的指标，以及可选的通过 Loki 来收集异常事件的日志。收集到的指标和日志，可以透过 Grafana 大盘进行展示。KubeSkoo exporter 也提供了现成的 Grafana 大盘，可以直接使用。

在配置好指标收集和大盘后，还需要对 KubeSkoop exporter 本身进行一些配置。我们在日常的监控中，为了对业务的流量造成影响，我们可以选择性开启一些低开销的探针，如基于 porcfs 的大部分探针，和部分基于 netlink、eBPF 的低开销探针。如果使用了 Loki，还需要同时配置 Loki 的服务地址，并且将其启用。在这些准备工作结束之后，我们就可以在大盘上看到所启用的指标和事件情况。

在日常的监控之中，需要关注一些敏感的指标的异常。比如说新建连接数的异常突增，或者是连接建立失败数上涨，reset 报文增加等。针对这些明显能够代表异常的指标，我们也可以通过配置告警的形式，能够在出现异常时，更快的介入去进行问题的排查和恢复。

**异常问题排查**

![](https://developer.qcloudimg.com/http-save/yehe-9667716/e8cc855eb5373302b552569b2965a90d.png)

当我们通过日常监控、业务告警、错误日志等方面发现可能存在网络异常后，需要先对网络异常问题的类型进行一个简单的归类，如 TCP 建连失败、网络延迟抖动等。通过简单的归类，能够更好的帮助我们确立问题的排查方向。

根据问题类型不同，我们就可以根据问题类型，开启适用于该问题的探针。比如出现了网络延迟抖动的问题，我们就可以开启 socketlatency 关注应用从 socket 读数据延迟的情况，或是开启 kernellatency 追踪内核中延迟的情况。

开启这些探针后，我们就可以通过已经配置好的 Grafana 来观测探针暴露出的指标或是事件结果。同时，异常事件也可以直接通过 Pod 日志，或是 exporter 容器中的 inspector 命令来直接观测。如果我们这次开启的探针结果没有异常，或是无法针对问题根因做出结论，可以考虑开启其它方面的探针，继续辅助我们进行问题的定位。

根据这些所得到的指标和异常事件，我们最终会定位到问题的根因。问题的根因可能出自系统中的某一些参数的调整，或者是出现在用户的程序之中。我们根据定位到的根因就可以进行这些系统参数调整或者是程序代码的优化了。

具体排查部分涉及到细节，在此不赘述，这里给出一些实践和快速上手的诀窍。

#### 快速上手

**一键诊断**

```js
skoop -s xxx.xxx.xxx.xxx -d xxx.xxx.xxx.xxx -p 端口号 --http  # 执行诊断命令，指定来源目的，通过--http来让诊断结果通过本地web服务提供
```

诊断完成后会输出诊断结果，可以以可视化的方式打开。

![](https://developer.qcloudimg.com/http-save/yehe-9667716/fccc20f73edd547d649eb5c327000f04.png)

**诊断网络抖动和网络性能问题**

通过以下步骤，可以在Kubernetes集群中快速部署Skoop exporter及其与Prometheus，Grafana和Loki构成的可观测性组合：

```js
kubectl apply -f https://raw.githubusercontent.com/alibaba/kubeskoop/main/deploy/skoopbundle.yaml
```

通过以下步骤，确认安装完成以及获取访问入口：

```js
# 查看Skoop exporter的运行状态
kubectl get pod -n kubeskoop -l app=skoop-exporter -o wide
# 查看Probe采集探针的运行状态
kubectl get --raw /api/v1/namespaces/kubeskoop/pods/skoop-exporter-t4d9m:9102/proxy/status |jq .
# 获取Prometheus服务的入口
kubectl get service -n kubeskoop prometheus-service -o wide
# 获取Grafana控制台的访问入口
kubectl get service -n kubeskoop grafana -o wide
```

通过KubeSkoop等工具确实也能诊断出一部分网络问题，对于识别容器网络层面的抖动问题有帮助，但是在面对复杂且难以预测的较高安全级别的私有云网络环境时，往往没有那么容易识别并解决根因，所以目前仍然还是有些困扰。

## 其他k8s常见网络故障

### 通用排查思路

Kubernetes 集群内不同服务之间的网络通信出现异常，表现为请求超时、连接失败或响应缓慢，导致服务间依赖关系中断，依赖服务的功能不可用或性能下降，甚至可能波及整个微服务架构，引发连锁反应，造成系统整体不稳定。

**排查方法：**

**第一步：检查Pod网络配置与状态**

查看Pod网络配置：

```js
kubectl describe pod <pod-name> -n <namespace>
```

这里要重点关注 **Events部分** 是否有网络配置相关的错误提示，以及IP地址是否已正确分配，如果没有异常则再检查Pod运行状态。

```js
kubectl get pods -n <namespace>
```

查看Pod是否处于Running状态，如果不是，检查其状态（如CrashLoopBackOff）并进一步分析日志。

**第二步：网络连通性测试**

这里主要还是通过常用的ping命令来测试。

进行Pod间连通性测试，在有问题的两个Pod中分别执行以下命令测试连通性，例如使用ping或nc(netcat)。

```js
# 在源Pod中执行
kubectl exec -it <source-pod-name> -n <namespace> -- ping <destination-pod-ip>

# 或者使用nc测试端口连通性
kubectl exec -it <source-pod-name> -n <namespace> -- nc -zv <destination-pod-ip> <port>
```

**第三步：查看网络策略规则**

如果以上都没有问题，则有可能是网络策略问题，执行如下命令确认是否有网络策略限制了Pod间的访问。

```js
kubectl get networkpolicies -n <namespace>
```

如果有相关策略，检查其 **spec-ingress和spec-egress** 规则，确保没有意外地拒绝了必要的通信。

**第四步：检查Service配置**

```js
kubectl describe service <service-name> -n <namespace>

kubectl get endpoints <service-name> -n <namespace>
```

再次执行上述命令来确认Service的类型、选择器、端口配置是否正确，并确保Service **有对应的Endpoints** ，即后端Pod列表。

**第五步：查看集群日志**

根据异常Pod所在节点，检查节点上的kubelet、网络插件的日志，寻找有关网络配置、连接尝试或错误的信息。

```js
kubectl logs <problematic-pod-name> -n <namespace>
```

### 1\. Pod访问外部服务超时

**现象**: Pod尝试访问外部服务(如数据库或API)时超时。

**原因分析**:通常情况下是egress规则未正确设置，导致流量无法流出集群。

**排查方法：**

**第一步：确认网络策略**

首先，还是检查是否有网络策略限制了Pod访问外部网络，确保没有规则阻止Egress（外出）流量。

```js
kubectl get networkpolicies -n <namespace>
```

**第二步：查看Pod网络配置**

确认Pod的网络配置，尤其是iptables规则和路由表。进入Pod内部检查：

```js
kubectl exec -it <pod-name> -n <namespace> -- bash
```

在Pod内执行以下命令查看路由表：

```js
ip route
```

并检查iptables规则：

```js
iptables -L -nv
```

**第三步：测试外部连接**

直接在Pod中尝试访问外部服务，比如ping一个公共DNS服务器或测试端口连接：

```js
ping 8.8.8.8
nc -vz example.com 443
```

**第四步：DNS解析测试**

如果服务访问依赖域名，检查DNS解析是否正常：

```js
nslookup www.baidu.com
```

**第五步：Egress配置检查**

如果发现是因为网络策略限制了Egress流量，那么可以创建或修改一个网络策略来允许外部访问。例如，允许所有Egress流量的网络策略：

```js
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-egress
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - {}
```

然后应用此策略：

```js
kubectl apply -f allow-egress.yaml -n <namespace>
```

生产环境中请确保根据实际情况调整策略，仅开放必要的端口和目标，保证系统的安全性。

### 2\. 服务ClusterIP不可达

**现象: 服务的ClusterIP地址无法从集群内部访问。**

**原因分析: 服务的Kubernetes Service配置错误，或kube-proxy服务异常。**

**排查方法：**

**第一步：确认服务状态**

老生常谈了，第一步还是确认服务的状态，检查服务是否已经创建并且状态正常：

```js
kubectl get svc -n <namespace>
```

需要确保服务存在且其类型为ClusterIP。

**第二步：服务详情检查**

查看服务的详细信息，重点关注ClusterIP、端口映射和Selector是否配置正确：

```js
kubectl describe svc <service-name> -n <namespace>
```

确认Endpoints列表中 **至少有一个Pod IP** ，这表明服务能够找到匹配的Pod。

**第三步：验证DNS解析**

在有问题的Pod中，尝试解析服务名以确认DNS是否工作正常：

```js
kubectl exec -it <problematic-pod-name> -n <namespace> -- nslookup <service-name>
```

此时正常来说应能看到服务对应的ClusterIP地址。

**第四步：网络连通性测试**

从问题Pod向服务的ClusterIP和端口发起ping或TCP连接测试：

```js
kubectl exec -it <problematic-pod-name> -n <namespace> -- bash -c "nc -zv <service-cluster-ip> <service-port>"
```

**第五步：kube-proxy状态检查**

kube-proxy负责服务的网络代理，确保它在所有节点上运行正常：

```js
kubectl get pods -n kube-system | grep kube-proxy
```

如果kube-proxy有问题，查看其日志：

```js
kubectl logs <kube-proxy-pod-name> -n kube-system
```

**第六步：重启kube-proxy**

如果以上都没有异常，作为最后的尝试，可以在所有节点上重启kube-proxy服务，可能会解决可能的临时问题，不过一定需要谨慎！：

```js
sudo systemctl restart kube-proxy
```

### 3\. Ingress 502 Bad Gateway

当使用Ingress资源时遇到502 Bad Gateway错误，这意味着Ingress控制器无法从后端服务正确接收响应。

**第一步：检查Ingress资源配置**

首先，确保Ingress资源配置正确，包括路径、服务名称、端口等：

```js
kubectl describe ingress <ingress-name> -n <namespace>
```

**第二步：检查Ingress资源配置**

检查关联的服务和Pod是否运行正常：

```js
kubectl get svc -n <namespace>
kubectl get pods -n <namespace>
```

确认Pod无CrashLoopBackOff或Error状态，服务有正确的端口映射和Selector。

**第三步：检查Endpoints**

验证服务是否绑定了正确的Pod：

```js
kubectl describe svc <service-name> -n <namespace>
```

在输出中查找 **Endpoints** 部分，确保有Pod IP列表。

**第四步：查看Ingress控制器日志**

根据使用的Ingress控制器（如Nginx Ingress Controller、Istio Ingress Gateway等），获取其日志以获取更多信息：

```js
# 对于Nginx Ingress Controller
kubectl logs -l app.kubernetes.io/name=ingress-nginx -n ingress-nginx
```

分析日志中是否有与502错误相关的错误信息或警告。

**第五步：确认后端服务可达性**

从Ingress所在节点或Pod内尝试直接访问后端服务，以排除网络问题：

```js
kubectl run -it --rm --restart=Never debug --image=busybox -- /bin/sh -n <namespace>

# 在新Pod中执行
nc -vz <backend-service-ip> <service-port>
```

**第六步：重启Ingress控制器**

如果上述步骤未解决问题，尝试重启Ingress控制器Pod：

```js
kubectl delete pod <ingress-controller-pod-name> -n <ingress-controller-namespace>
```

## 附：常用k8s排查命令

### 容器网络故障

#### 确认容器是否已正确启动并运行，并且是否已被正确配置为使用正确的网络。

执行命令，确认 Pod 是否已正确启动并运行。

```js
kubectl get pods
```

执行命令，确认容器的网络配置是否正确。

```js
kubectl describe pod <pod-name>
```

#### 检查 Pod 和容器的网络配置，例如 IP 地址、子网掩码、网关、DNS 等是否正确配置。

执行命令查看容器的网络配置信息。

```js
kubectl describe pod <pod-name>
```

执行命令 ，查看容器的网络接口信息。

```js
kubectl exec <pod-name> -- ifconfig
```

#### 检查网络插件是否正常工作，并尝试重启网络插件。

如果使用 Flannel 网络插件，执行命令 查看 Flannel 的日志信息。

```js
kubectl logs -n kube-system -l k8s-app=flannel
```

如果使用 Calico 网络插件，执行命令，查看 Calico 的日志信息。

```js
kubectl logs -n kube-system -l k8s-app=calico-node
```

重启网络插件：如果使用 Flannel 网络插件，执行命令

```js
kubectl delete pod -n kube-system -l k8s-app=flannel
```

如果使用 Calico 网络插件，执行命令。

```js
kubectl delete pod -n kube-system -l k8s-app=calico-node
```

#### 检查网络设备是否正常工作，例如交换机、路由器、防火墙等是否出现故障。

检查网络设备的日志或配置信息，确认网络设备是否正常工作。

#### 尝试使用 Kubernetes 工具进行诊断，例如 kubectl，以查看 Pod 和容器的状态和日志。

执行命令，查看容器的日志信息。

```js
kubectl logs <pod-name>
```

执行命令 ，查看容器的状态信息。

```js
kubectl describe pod <pod-name>
```

#### 如果以上方法无法解决问题，可以考虑重新部署容器网络或更换网络插件。

如果使用 Flannel 网络插件，执行命令 重新部署 Flannel 网络插件。

```js
kubectl delete -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml && kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml，
```

如果使用 Calico 网络插件，执行命令重新部署 Calico 网络插件。

```js
kubectl delete -f https://docs.projectcalico.org/manifests/calico.yaml && kubectl apply -f https://docs.projectcalico.org/manifests/calico.yaml
```

### 网络策略故障

#### 查看所有网络策略：

```js
kubectl get networkpolicies --all-namespaces
```

#### 查看网络策略的详细信息：

```js
kubectl describe networkpolicy <network-policy-name> -n <namespace>
```

#### 检查网络策略的规则是否正确：

```js
kubectl get networkpolicy <network-policy-name> -n <namespace> -o yaml
```

#### 检查容器是否正确标记：

```js
kubectl get pods --selector=<label-selector> -n <namespace> -o wide
```

#### 检查容器的端口是否正确配置：

```js
kubectl get pods <pod-name> -n <namespace> -o yaml
```

#### 检查节点是否正确配置：

```js
kubectl get nodes -o wide
```

#### 检查网络设备是否正常工作：

```js
kubectl logs <network-device-pod-name> -n <namespace>
```

#### 如果你的Kubernetes集群使用的是Calico网络策略，你可以使用以下命令：

查看所有Calico网络策略：

```js
kubectl get networkpolicies.projectcalico.org --all-namespaces
```

查看Calico网络策略的详细信息：

```js
kubectl describe networkpolicy <network-policy-name> -n <namespace>
```

检查Calico网络策略的规则是否正确：

```js
kubectl get networkpolicy <network-policy-name> -n <namespace> -o yaml
```

检查Calico网络设备是否正常工作：

```js
kubectl logs -n kube-system -l k8s-app=calico-node
```

### DNS 故障

#### 检查网络设备是否连通：

```js
ping <network-device-ip>
```

#### 检查网络设备的日志信息：

```js
kubectl logs <network-device-pod-name> -n <namespace>
```

#### 检查网络设备的配置信息：

```js
kubectl exec -it <network-device-pod-name> -n <namespace> -- <command> <arguments>
```

#### 检查网络设备的版本信息：

```js
kubectl exec -it <network-device-pod-name> -n <namespace> -- <command> <arguments>
```

#### 检查网络设备的连接状态：

```js
kubectl exec -it <network-device-pod-name> -n <namespace> -- <command> <arguments>
```

## 总结

本文全面审视了Kubernetes网络体系的构建与故障排查，从技术背景出发，深入剖析了Kubernetes网络模型的四大核心要素：Pod网络、Service、CNI（容器网络接口）、以及它们间的通信方式。文章通过三个实战案例揭示了网络故障的复杂性：内外网段冲突的NAT解决方案、主节点域名解析导致的服务中断与恢复、及容器网络抖动因监控工具KubeSkoop的定位。这些案例强调了网络规划的前瞻性、故障应对策略、监控重要性与持续学习的价值。

在回顾Kubernetes（K8s）网络故障排查的历程中，也能深刻体会到几个关键要点，这些不仅是技术层面的实践总结，更是策略与思维方法的提炼：

- **前期规划为基，预防为主** ：网络问题的根本解决之道在于预防，初期规划时务必确保网络地址空间的唯一性与预留，避免内外网段冲突。合理的网络架构设计与地址规划是避免未来故障的第一道防线。
- **深入理解网络模型** ：深入掌握K8s网络模型的每一环节，包括Pod、Service、CNI的工作原理及Ingress等，是排查问题的基础。理解这些核心元素如何协同工作，是解决问题的钥匙。
- **谨慎变更** ：任何配置变更，如DNS修改，需审慎之又慎之又慎，以免影响全局。变更管理需有计划和回滚策略。

随着技术的飞速进步，未来Kubernetes网络管理正迈向智能化的新纪元年，寄望借助机器学习之力，洞悉察网络行为趋势，预判潜在冲突及性能瓶颈，自动化调优配置，力图显著降低人工介入，提升自治效能。

[我正在参与2024腾讯技术创作特训营最新征文，快来和我瓜分大奖！](https://cloud.tencent.com/developer/article/2423305?from_column=20421&from=20421)

原创声明：本文系作者授权腾讯云开发者社区发表，未经许可，不得转载。

如有侵权，请联系 [cloudcommunity@tencent.com](mailto:cloudcommunity@tencent.com) 删除。

原创声明：本文系作者授权腾讯云开发者社区发表，未经许可，不得转载。

如有侵权，请联系 [cloudcommunity@tencent.com](mailto:cloudcommunity@tencent.com) 删除。

目录

相关产品与服务

容器服务

腾讯云容器服务（Tencent Kubernetes Engine, TKE）基于原生 kubernetes 提供以容器为核心的、高度可扩展的企业级容器管理服务。首创单集群混合节点的资源管理模式，全面围绕 Agentic AI 应用部署与极致资源效能提供全场景解决方案，为用户释放 AI 时代的无限算力。

[2026采购季 | AI焕新·智启新局](https://cloud.tencent.com/act/pro/featured-202604?from=21344&from_column=21344)