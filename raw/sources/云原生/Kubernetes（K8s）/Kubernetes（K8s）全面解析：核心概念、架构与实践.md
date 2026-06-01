https://www.cnblogs.com/clnchanpin/p/19515989

**目录**
[一、K8s 是什么？](#%E4%B8%80%E3%80%81K8s%20%E6%98%AF%E4%BB%80%E4%B9%88%EF%BC%9F)
[二、K8s 的核心优势](#%E4%BA%8C%E3%80%81K8s%20%E7%9A%84%E6%A0%B8%E5%BF%83%E4%BC%98%E5%8A%BF)
[三、K8s 的核心概念](#%E4%B8%89%E3%80%81K8s%20%E7%9A%84%E6%A0%B8%E5%BF%83%E6%A6%82%E5%BF%B5)
[1. Pod](#1.%20Pod)
[2. 控制器（Controller）](#2.%20%E6%8E%A7%E5%88%B6%E5%99%A8%EF%BC%88Controller%EF%BC%89)
[3. Service](#3.%20Service)
[4. 命名空间（Namespace）](#4.%20%E5%91%BD%E5%90%8D%E7%A9%BA%E9%97%B4%EF%BC%88Namespace%EF%BC%89)
[5. 配置与存储](#5.%20%E9%85%8D%E7%BD%AE%E4%B8%8E%E5%AD%98%E5%82%A8)
[6. 标签与选择器（Label/Selector）](#6.%20%E6%A0%87%E7%AD%BE%E4%B8%8E%E9%80%89%E6%8B%A9%E5%99%A8%EF%BC%88Label%2FSelector%EF%BC%89)
[四、K8s 的架构设计](#%E5%9B%9B%E3%80%81K8s%20%E7%9A%84%E6%9E%B6%E6%9E%84%E8%AE%BE%E8%AE%A1)
[1. 控制平面（Master 节点）](#1.%20%E6%8E%A7%E5%88%B6%E5%B9%B3%E9%9D%A2%EF%BC%88Master%20%E8%8A%82%E7%82%B9%EF%BC%89)
[2. 节点（Node 节点）](#2.%20%E8%8A%82%E7%82%B9%EF%BC%88Node%20%E8%8A%82%E7%82%B9%EF%BC%89)
[五、K8s 的基本使用流程](#%E4%BA%94%E3%80%81K8s%20%E7%9A%84%E5%9F%BA%E6%9C%AC%E4%BD%BF%E7%94%A8%E6%B5%81%E7%A8%8B)
[1. 环境部署](#1.%20%E7%8E%AF%E5%A2%83%E9%83%A8%E7%BD%B2)
[2. 核心命令](#2.%20%E6%A0%B8%E5%BF%83%E5%91%BD%E4%BB%A4)
[（1）集群信息查看](#%EF%BC%881%EF%BC%89%E9%9B%86%E7%BE%A4%E4%BF%A1%E6%81%AF%E6%9F%A5%E7%9C%8B)
[（2）资源操作（以 Deployment 为例）](#%EF%BC%882%EF%BC%89%E8%B5%84%E6%BA%90%E6%93%8D%E4%BD%9C%EF%BC%88%E4%BB%A5%20Deployment%20%E4%B8%BA%E4%BE%8B%EF%BC%89)
[（3）Service 操作](#%EF%BC%883%EF%BC%89Service%20%E6%93%8D%E4%BD%9C)
[（4）配置与存储操作](#%EF%BC%884%EF%BC%89%E9%85%8D%E7%BD%AE%E4%B8%8E%E5%AD%98%E5%82%A8%E6%93%8D%E4%BD%9C)
[3. 资源清单（YAML 文件）](#3.%20%E8%B5%84%E6%BA%90%E6%B8%85%E5%8D%95%EF%BC%88YAML%20%E6%96%87%E4%BB%B6%EF%BC%89)
[（1）Deployment 清单（nginx-deployment.yaml）](#%EF%BC%881%EF%BC%89Deployment%20%E6%B8%85%E5%8D%95%EF%BC%88nginx-deployment.yaml%EF%BC%89)
[（2）Service 清单（nginx-service.yaml）](#%EF%BC%882%EF%BC%89Service%20%E6%B8%85%E5%8D%95%EF%BC%88nginx-service.yaml%EF%BC%89)
[六、K8s 的核心功能实践](#%E5%85%AD%E3%80%81K8s%20%E7%9A%84%E6%A0%B8%E5%BF%83%E5%8A%9F%E8%83%BD%E5%AE%9E%E8%B7%B5)
[1. 应用部署与扩缩容](#1.%20%E5%BA%94%E7%94%A8%E9%83%A8%E7%BD%B2%E4%B8%8E%E6%89%A9%E7%BC%A9%E5%AE%B9)
[2. 滚动更新与回滚](#2.%20%E6%BB%9A%E5%8A%A8%E6%9B%B4%E6%96%B0%E4%B8%8E%E5%9B%9E%E6%BB%9A)
[3. 服务暴露与访问](#3.%20%E6%9C%8D%E5%8A%A1%E6%9A%B4%E9%9C%B2%E4%B8%8E%E8%AE%BF%E9%97%AE)
[4. 数据持久化](#4.%20%E6%95%B0%E6%8D%AE%E6%8C%81%E4%B9%85%E5%8C%96)
[七、K8s 的生态工具](#%E4%B8%83%E3%80%81K8s%20%E7%9A%84%E7%94%9F%E6%80%81%E5%B7%A5%E5%85%B7)
[八、总结](#%E5%85%AB%E3%80%81%E6%80%BB%E7%BB%93)

---

        Kubernetes（简称 K8s）是 Google 开源的**容器编排平台**，旨在自动化容器的部署、扩展、运维和管理，是云原生生态的核心技术。它将零散的容器组织成高可用、可伸缩的应用集群，解决了大规模容器管理的复杂性问题。以下从**核心概念、架构设计、核心功能、使用流程**等维度，全面拆解 K8s。

### 一、K8s 是什么？

K8s 的名字源于希腊语 “舵手” 或 “飞行员”，寓意为容器集群的 “导航系统”。其核心目标是：**让容器化应用在集群中高效、可靠地运行**，提供自动化的容器编排能力（如调度、伸缩、自愈、负载均衡）。

简单来说：如果 Docker 是 “集装箱”（封装应用），K8s 就是 “港口调度系统”（管理集装箱的装卸、运输、堆叠）。

### 二、K8s 的核心优势

- **自动化运维**：自动完成容器的部署、重启、扩缩容，减少人工干预。
- **高可用性**：节点或容器故障时自动调度到其他节点，保证服务不中断。
- **弹性伸缩**：根据 CPU 使用率、QPS 等指标自动增减容器数量。
- **负载均衡**：内置服务发现和负载均衡，实现容器间的通信与流量分发。
- **滚动更新与回滚**：无停机更新应用版本，更新失败时可快速回滚。
- **跨环境兼容**：支持公有云（AWS、Azure）、私有云、混合云，实现 “一次部署，到处运行”。

### 三、K8s 的核心概念

#### 1. Pod

- **定义**：K8s 的最小部署单元，是一个或多个容器的组合（共享网络、存储）。
- **特性**：
    - 容器共享 Pod 的 IP 和端口空间（Pod 内容器可通过localhost通信）。
    - 生命周期短暂（被调度到节点后，若节点故障或 Pod 被删除，不会重建，需通过控制器管理）。
    - 包含 “基础设施容器”（Pause 容器），用于维持 Pod 的网络命名空间。
- **示例**：一个 Web 应用 Pod 可能包含 “应用容器 + 日志收集容器”。

#### 2. 控制器（Controller）

用于管理 Pod 的生命周期，确保 Pod 按期望状态运行。常见控制器：

- **Deployment**：最常用的控制器，管理无状态应用，支持滚动更新、扩缩容、回滚。
- **StatefulSet**：管理有状态应用（如数据库），保证 Pod 的名称、网络标识、存储的唯一性。
- **DaemonSet**：在集群每个节点上运行一个 Pod 副本（如日志收集、监控 Agent）。
- **Job/CronJob**：运行一次性任务（Job）或定时任务（CronJob）。

#### 3. Service

- **定义**：为 Pod 提供稳定的网络访问入口，解决 Pod 动态 IP 变化的问题。
- **类型**：
    - **ClusterIP**：默认类型，仅集群内部可访问（通过虚拟 IP）。
    - **NodePort**：在每个节点开放一个静态端口，外部可通过 “节点 IP + 端口” 访问。
    - **LoadBalancer**：结合云服务商的负载均衡器，对外暴露服务（公有云常用）。
    - **Ingress**：非 Service 类型，通过 Ingress Controller 实现 HTTP/HTTPS 路由（如域名转发）。

#### 4. 命名空间（Namespace）

- **定义**：用于隔离集群资源（如 Pod、Service、Deployment），实现多租户管理。
- **默认命名空间**：
    - `default`：未指定命名空间的资源默认放在这里。
    - `kube-system`：K8s 系统组件所在的命名空间。
    - `kube-public`：公共资源命名空间（所有用户可读）。

#### 5. 配置与存储

- **ConfigMap**：存储非敏感配置数据（如环境变量、配置文件），可挂载到 Pod 中。
- **Secret**：存储敏感数据（如密码、Token、证书），数据会被 Base64 编码（需加密增强安全性）。
- **Volume**：Pod 的持久化存储，支持多种存储类型（如本地存储、NFS、云存储）。
- **PersistentVolume（PV）/PersistentVolumeClaim（PVC）**：PV 是集群的存储资源，PVC 是 Pod 对存储的申请（类似 “存储租赁”）。

#### 6. 标签与选择器（Label/Selector）

- **标签**：键值对形式的元数据（如`app=nginx`、`env=prod`），用于标识资源。
- **选择器**：通过标签筛选资源（如 Deployment 通过`selector`匹配 Pod 标签），实现资源关联。

### 四、K8s 的架构设计

K8s 采用**主从架构（Master-Node）**，分为控制平面（Control Plane）和节点（Node）两部分。

#### 1. 控制平面（Master 节点）

负责集群的全局决策（调度、管理），包含以下核心组件：

- **kube-apiserver**：集群的统一入口，所有操作通过 API Server 执行（RESTful API），提供认证、授权、准入控制。
- **etcd**：集群的数据库，存储所有集群状态数据（配置、元数据），需保证高可用。
- **kube-scheduler**：负责 Pod 的调度（将 Pod 分配到合适的 Node 节点），基于资源需求、节点亲和性等策略。
- **kube-controller-manager**：包含多种控制器（节点控制器、副本控制器、Service 控制器等），维护集群状态。
- **cloud-controller-manager**：与云服务商集成的控制器（可选），管理云资源（如负载均衡器、云存储）。

#### 2. 节点（Node 节点）

负责运行容器化应用，包含以下核心组件：

- **kubelet**：Node 节点的代理，与 API Server 通信，管理 Pod 的生命周期（启动、停止容器），确保 Pod 按期望运行。
- **kube-proxy**：维护 Node 节点的网络规则，实现 Service 的负载均衡（转发流量到 Pod）。
- **容器运行时（Container Runtime）**：运行容器的软件，如 containerd、CRI-O（早期用 Docker，需通过 cri-dockerd 适配）。
- **容器网络接口（CNI）**：实现 Pod 间的网络通信（如 Flannel、Calico、Cilium）。

### 五、K8s 的基本使用流程

#### 1. 环境部署

K8s 的部署方式有多种，适合不同场景：

- **Minikube**：单机版 K8s，适合开发测试（`minikube start`一键启动）。
- **kubeadm**：官方工具，用于部署生产级集群（需多台服务器）。
- **云服务商托管 K8s**：如 AWS EKS、Azure AKS、阿里云 ACK（无需手动维护控制平面）。

#### 2. 核心命令

K8s 的命令行工具是`kubectl`，常用命令如下：

##### （1）集群信息查看
```
# 查看集群节点
kubectl get nodes
# 查看集群信息
kubectl cluster-info
# 查看命名空间
kubectl get namespaces
```

##### （2）资源操作（以 Deployment 为例）
```
# 创建Deployment（从YAML文件）
kubectl apply -f nginx-deployment.yaml
# 查看Deployment
kubectl get deployments
# 查看Pod
kubectl get pods
# 查看Pod详情
kubectl describe pod 
# 查看Pod日志
kubectl logs 
# 进入Pod容器
kubectl exec -it  -- /bin/bash
# 扩缩容Deployment
kubectl scale deployment nginx-deployment --replicas=5
# 删除Deployment
kubectl delete deployment nginx-deployment
```

##### （3）Service 操作
```
# 创建Service
kubectl apply -f nginx-service.yaml
# 查看Service
kubectl get services
# 查看Service详情
kubectl describe service nginx-service
```

##### （4）配置与存储操作
```
# 创建ConfigMap
kubectl create configmap app-config --from-literal=env=prod --from-file=app.conf
# 创建Secret
kubectl create secret generic db-secret --from-literal=username=root --from-literal=password=123456
# 查看ConfigMap/Secret
kubectl get configmaps
kubectl get secrets
```

#### 3. 资源清单（YAML 文件）

K8s 通过 YAML 文件定义资源（声明式 API），以下是一个完整的 Deployment+Service 示例：

##### （1）Deployment 清单（nginx-deployment.yaml）
```
apiVersion: apps/v1  # API版本（不同资源版本不同）
kind: Deployment     # 资源类型
metadata:
  name: nginx-deployment  # 资源名称
  namespace: default      # 命名空间
spec:
  replicas: 3  # 副本数
  selector:
    matchLabels:
      app: nginx  # 匹配Pod标签
  template:
    metadata:
      labels:
        app: nginx  # Pod标签
    spec:
      containers:
      - name: nginx  # 容器名称
        image: nginx:1.25  # 容器镜像
        ports:
        - containerPort: 80  # 容器端口
        resources:  # 资源限制
          limits:
            cpu: "1"
            memory: "1Gi"
          requests:
            cpu: "0.5"
            memory: "512Mi"
        env:  # 环境变量（从ConfigMap/Secret注入）
        - name: ENV
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: env
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: password
```

##### （2）Service 清单（nginx-service.yaml）
```
apiVersion: v1
kind: Service
metadata:
  name: nginx-service
spec:
  type: NodePort  # Service类型
  selector:
    app: nginx  # 匹配Pod标签
  ports:
  - port: 80        # Service端口
    targetPort: 80  # Pod端口
    nodePort: 30080 # 节点端口（范围30000-32767）
```

### 六、K8s 的核心功能实践

#### 1. 应用部署与扩缩容

- **部署应用**：`kubectl apply -f nginx-deployment.yaml`
- **手动扩缩容**：`kubectl scale deployment nginx-deployment --replicas=5`
- **自动扩缩容**：通过 HPA（Horizontal Pod Autoscaler）基于 CPU 使用率自动扩缩容：

```
kubectl autoscale deployment nginx-deployment --min=2 --max=10 --cpu-percent=50
```

#### 2. 滚动更新与回滚

- **更新镜像版本**：
```
kubectl set image deployment/nginx-deployment nginx=nginx:1.26
```
- **查看更新状态**：`kubectl rollout status deployment/nginx-deployment`
- **回滚到上一版本**：`kubectl rollout undo deployment/nginx-deployment`

#### 3. 服务暴露与访问

- **NodePort 访问**：通过`节点IP:30080`访问服务。
- **Ingress 访问**：配置 Ingress 实现域名访问（需先部署 Ingress Controller，如 Nginx Ingress）：
```
apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: nginx-ingress
    spec:
      rules:
      - host: nginx.example.com
        http:
          paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: nginx-service
                port:
                  number: 80
```

#### 4. 数据持久化

通过 PV/PVC 实现 Pod 数据持久化：

```
# PV清单
apiVersion: v1
kind: PersistentVolume
metadata:
  name: nginx-pv
spec:
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: /data/nginx-pv  # 本地存储路径
# PVC清单
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: nginx-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
# Deployment挂载PVC
spec:
  containers:
  - name: nginx
    volumeMounts:
    - name: nginx-storage
      mountPath: /usr/share/nginx/html
  volumes:
  - name: nginx-storage
    persistentVolumeClaim:
      claimName: nginx-pvc
```

### 七、K8s 的生态工具

- **监控与日志**：Prometheus（监控）+ Grafana（可视化）、ELK Stack（日志收集分析）、Loki（轻量级日志系统）。
- **服务网格**：Istio（流量管理、安全、可观测性）、Linkerd（轻量级服务网格）。
- **CI/CD 集成**：Jenkins、GitLab CI、ArgoCD（GitOps 工具）。
- **容器镜像仓库**：Harbor（私有仓库）、Docker Hub（公有仓库）。
- **集群管理工具**：KubeSphere（可视化管理平台）、Rancher（多集群管理）。

### 八、总结

Kubernetes 是容器编排领域的事实标准，通过抽象化的资源定义和自动化的管理能力，解决了大规模容器集群的运维复杂性。掌握 K8s 的核心概念（Pod、Deployment、Service）、架构设计和实践操作，是云原生开发和运维的必备技能。后续可深入学习 K8s 的高级特性（如调度策略、安全机制、集群联邦），以及云原生生态的其他技术（如 Service Mesh、Serverless）。