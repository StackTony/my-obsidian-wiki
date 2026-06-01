---
credibility: low
---

随着微服务架构的普及，服务间的网络通信安全变得至关重要。在Kubernetes集群中，默认情况下所有Pod之间是可以自由通信的，这带来了潜在的安全风险。Kubernetes NetworkPolicy（网络策略）提供了一种强大的机制，允许您定义精细化的网络访问控制规则，实现“零信任”安全模型。本文将深入探讨NetworkPolicy的原理、实践以及最佳实践。

## 什么是Kubernetes网络策略？

Kubernetes NetworkPolicy是一种以Pod为中心的网络隔离规范。它通过标签选择器来定义一组Pod，并规定这组Pod如何与其他网络端点（Pod、命名空间、IP块）进行通信。 **关键点在于，NetworkPolicy本身并不提供网络功能，它只是一个声明式API。实际的网络规则需要由支持NetworkPolicy的CNI（容器网络接口）插件来实施** ，例如Calico、Cilium、Weave Net等。

## 网络策略核心概念

### 1\. 选择器（Selectors）

策略通过 `podSelector` 和/或 `namespaceSelector` 来选择应用策略的Pod。

### 2\. 策略类型（PolicyTypes）

- `Ingress`: 控制进入Pod的流量。
- `Egress`: 控制从Pod流出的流量。

### 3\. 规则（Rules）

每条规则可以指定允许的流量，包括：

- `from`: 入口流量的来源（Pod、命名空间、IP块）。
- `to`: 出口流量的目标。
- `ports`: 允许的端口和协议（TCP/UDP）。

## 实战：编写网络策略

让我们通过几个常见场景来学习如何编写NetworkPolicy。

### 场景一：拒绝所有入口流量（默认安全）

这是推荐的起点策略，先禁止所有入站流量，再逐步开放必要的端口。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: production
spec:
  podSelector: {} # 空选择器匹配命名空间下的所有Pod
  policyTypes:
  - Ingress
  # ingress 规则列表为空，表示不允许任何入口流量
```

### 场景二：允许特定应用接收流量

假设我们有一个前端服务（标签 `app: frontend` ）需要接收来自后端服务（标签 `app: backend` ）在端口 `8080` 上的TCP流量。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-from-backend
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: backend
    ports:
    - protocol: TCP
      port: 8080
```

### 场景三：允许出口流量到外部数据库

微服务经常需要访问外部数据库。以下策略允许带有标签 `app: api-service` 的Pod访问特定外部IP的MySQL数据库。 **在管理这类外部服务连接字符串和进行连通性测试时，使用专业的数据库工具如 [dblens SQL编辑器](https://www.dblens.com/) 会事半功倍，它能安全地管理不同环境的数据库连接，并直接执行测试查询。**

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-egress-to-external-mysql
spec:
  podSelector:
    matchLabels:
      app: api-service
  policyTypes:
  - Egress
  egress:
  - to:
    - ipBlock:
        cidr: 192.168.100.0/24 # 外部数据库IP段
    ports:
    - protocol: TCP
      port: 3306
```

## 最佳实践

1. **采用“默认拒绝”原则** ：首先为命名空间创建默认的拒绝所有入口和出口的策略，然后根据需要添加允许规则。
2. **按命名空间隔离** ：使用 `namespaceSelector` 实现跨命名空间的访问控制，例如只允许 `monitoring` 命名空间的Pod访问应用Pod的度量指标端口。
3. **标签体系化** ：为Pod和命名空间设计清晰、一致的标签体系，这是网络策略能够精准选择目标的基础。
4. **策略即代码（Policy as Code）** ：将NetworkPolicy YAML文件与应用程序代码一同纳入版本控制系统（如Git）。
5. **结合服务网格** ：对于更复杂的场景（如mTLS、细粒度HTTP路由规则），可以考虑结合Istio、Linkerd等服务网格方案，NetworkPolicy负责L3/L4层隔离，服务网格负责L7层控制。
6. **持续验证与测试** ：部署策略后，务必测试通信是否按预期工作。可以编写自动化测试脚本，模拟流量进行验证。在开发和测试策略逻辑时，将复杂的访问关系记录下来至关重要。推荐使用 [QueryNote](https://note.dblens.com/) 这样的笔记工具，它专为技术人员设计，可以很好地记录策略意图、测试用例和排查日志，形成团队知识库。

## 总结

Kubernetes网络策略是实现集群内部微服务安全通信的基石。通过定义精细化的入口（Ingress）和出口（Egress）规则，我们可以有效限制攻击面，遵循最小权限原则。成功实施网络策略的关键在于：

- 理解其声明式模型和对CNI插件的依赖。
- 从“默认拒绝”开始，逐步构建允许规则。
- 建立良好的资源标签规范。
- 将策略管理与应用部署流程整合。

通过将NetworkPolicy与健全的运维实践及配套工具（如dblens提供的数据库管理和知识沉淀工具）相结合，我们能够构建起既灵活又安全的Kubernetes微服务网络环境。

本文来自博客园，作者： [DBLens数据库开发工具](https://www.cnblogs.com/dblens/) ，转载请注明原文链接： [https://www.cnblogs.com/dblens/p/19561871](https://www.cnblogs.com/dblens/p/19561871)

posted on [DBLens数据库开发工具](https://www.cnblogs.com/dblens) 阅读(68) 评论(0) 收藏 [举报](https://report.cnblogs.com/?targetLink=https%3A%2F%2Fwww.cnblogs.com%2Fdblens%2Fp%2F19561871&targetId=19561871&targetType=0)