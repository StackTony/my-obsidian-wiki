---
credibility: low
---
**前言**：
在云原生时代，Kubernetes 已成为容器编排领域的事实标准，推动着现代软件架构向微服务、分布式方向发展。然而，随着应用规模的增长，Kubernetes 原生的 YAML 配置管理方式逐渐暴露出复杂性高、重复劳动多、环境差异难以管理等问题，极大地限制了开发与运维效率。

Helm 的出现，恰似为 Kubernetes 应用交付而生的破局之刃。从 2015 年 Deis 团队为简化 Kubernetes 部署流程而萌生的创意，到如今成为云原生计算基金会（CNCF）的明星项目，Helm 已经发展成为 Kubernetes 生态中不可或缺的基础设施组件。它不仅重新定义了 Kubernetes 应用的打包、部署与管理方式，更以其强大的模板引擎、依赖管理机制和全生命周期管控能力，为开发者、运维人员以及架构师提供了一套高效、灵活且可复用的应用交付解决方案。

通过 Helm，开发团队能够将复杂的微服务架构以标准化的 Chart 包形式进行封装，实现一键式部署与环境隔离；运维团队可以轻松管理多环境配置，快速响应应用更新需求并保障系统稳定性；架构师则能够基于 Helm 构建企业级的自动化 CI/CD 流水线，提升整体研发效能。无论是初创企业快速迭代产品，还是大型组织管理海量微服务集群，Helm 都能提供统一而强大的支撑，成为连接开发、测试、运维的关键桥梁。

本篇博客深入剖析 Helm 的发展脉络、核心特性、原理机制以及实操技巧，旨在帮助读者全面掌握 Helm 在 Kubernetes 生态中的关键作用，开启高效云原生应用交付之旅。

## 一、发展历史：从 Deis 到 CNCF 的孵化之路

Helm 的诞生源于 2015 年 Deis 公司的内部需求——如何简化 Kubernetes 应用的部署与管理。当时 Kubernetes 虽已展现出强大的容器编排能力，但原生 YAML 文件的碎片化管理让复杂应用的部署变得繁琐，开发者需要频繁处理模板、依赖和配置版本等问题。Deis 工程师创建了 Helm 的早期版本，通过引入 "Chart" 概念将 Kubernetes 资源打包成可分发的单元。

2016 年，Deis 将 Helm 捐赠给云原生计算基金会（CNCF），开启了开源社区的协作开发。2018 年，Helm 2.0 发布，引入 Tiller 作为服务端组件，实现了客户端 - 服务端架构，支持 RBAC 权限管理和更复杂的部署场景。随着 Kubernetes 生态的成熟，Helm 在 2019 年成为 CNCF 孵化项目，并于 2020 年推出里程碑式的 Helm 3.0 版本，移除了 Tiller 组件，采用纯 CLI 架构，简化安装流程并强化安全性。

截至 2025 年，Helm 已发展到 3.13 版本，累计下载量超过 10 亿次，成为 Kubernetes 生态中应用最广泛的包管理工具，支撑着从中小企业到大型云服务商的应用交付场景。

## 二、Helm 简介：重新定义 K8s 应用交付

Helm 是 Kubernetes 的应用包管理器，其核心价值在于将复杂的 Kubernetes 资源定义转化为可复用、可分发的软件包（Chart），解决了三大核心问题：

- **碎片化管理** ：将多个 YAML 文件（Deployment、Service、ConfigMap 等）整合为单一 Chart。
- **环境差异化** ：通过 Values 文件实现不同环境（开发 / 测试 / 生产）的配置分离。
- **生命周期管理** ：支持应用的安装、升级、回滚、删除等全流程操作。

类比传统软件领域，Helm 相当于 Kubernetes 的 "apt-get" 或 "yum"，但具备更强大的模板引擎和生态整合能力。其核心概念包括：

- **Chart** ：应用的打包格式，包含 Kubernetes 资源定义、默认配置、元数据等。
- **Release** ：Chart 在 Kubernetes 集群中的一次具体部署实例。
- **Repository** ：Chart 的存储仓库，支持公共仓库（如 Artifact Hub）和私有仓库。

## 三、核心功能：构建高效的应用交付管道

### 1\. 标准化应用定义

通过 Chart 目录结构（templates/、values.yaml、Chart.yaml）实现应用定义的标准化，典型结构如下：

```bash
mychart/
├── Chart.yaml          # 元数据（名称、版本、作者）
├── values.yaml         # 默认配置
├── charts/             # 依赖Chart
├── templates/          # Kubernetes资源模板
│   ├── deployment.yaml
│   ├── service.yaml
│   └── _helpers.tpl    # 模板助手
└── values.schema.json  # 配置校验文件
```

### 2\. 智能模板引擎

基于 Go 模板语言，支持条件渲染、循环控制、函数调用等高级特性：

```yaml
# templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Chart.Name }}
spec:
  replicas: {{ .Values.replicaCount }}
  template:
    spec:
      containers:
      - name: {{ .Chart.Name }}
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
        {{- if .Values.image.pullPolicy }}
        imagePullPolicy: {{ .Values.image.pullPolicy }}
        {{- end }}
```

### 3\. 依赖管理系统

通过 Chart.yaml 中的 dependencies 字段声明依赖，支持版本范围约束：

```yaml
dependencies:
- name: mysql
  version: "5.2.4"
  repository: "https://charts.bitnami.com/bitnami"
```

使用 `helm dependency build` 自动解析并下载依赖 Chart，构建可独立部署的超级 Chart。

### 4\. 全生命周期管理

提供完整的 Release 操作命令：

```bash
helm install my-release ./mychart       # 安装应用
helm upgrade my-release ./mychart --reuse-values  # 升级应用
helm rollback my-release 2              # 回滚到第2个版本
helm list --all-namespaces              # 查看所有命名空间的Release
helm delete my-release --purge          # 删除Release并清除历史记录
```

### 5\. 丰富的扩展能力

支持插件机制扩展功能，例如：

- `helm diff` ：查看升级前后的配置差异。
- `helm test` ：部署后自动执行冒烟测试。
- `helm secrets` ：安全管理敏感配置（通过 CRD 实现）。

## 四、运行原理：解构 Helm 的架构设计

### 1\. 架构演进：从 C/S 到纯 CLI 模式

Helm 2.x 采用客户端 - 服务端架构：

- **Helm CLI** ：负责用户交互、模板渲染、命令分发。
- **Tiller** ：运行在 Kubernetes 集群内，负责与 API Server 交互、存储 Release 状态。

Helm 3.0 移除 Tiller 后，采用纯客户端架构：

- 直接通过 Kubernetes API Server 认证（基于 Kubeconfig）。
- Release 状态作为 Custom Resource（CustomResourceDefinition）存储在集群中，默认存储在 `release-history` ConfigMap。

### 2\. 渲染流程：从模板到 Kubernetes 资源

1. **参数合并** ：合并默认 values.yaml、用户指定 values 文件、命令行参数（--set）。
2. **模板渲染** ：通过 Go 模板引擎生成具体的 Kubernetes 资源 YAML。
3. **依赖解析** ：递归解析 Chart 依赖并生成依赖 Chart 的资源。
4. **对象校验** ：通过 Kubernetes API 进行资源合法性校验（admission webhook）。
5. **提交部署** ：通过 API Server 创建 / 更新 Release 资源。

### 3\. 版本控制机制

每个 Release 升级时会生成新的版本记录，通过 `helm history my-release` 查看：

```bash
REVISION  UPDATED                  STATUS     CHART       APP VERSION DESCRIPTION
1         Thu May  8 14:00:00 2025  deployed   mychart-1.0 1.0        Install complete
2         Thu May  8 14:05:00 2025  deployed   mychart-1.1 1.1        Upgrade complete
```

回滚时通过修订版本号（REVISION）恢复历史状态，底层通过 Kubernetes 的 ResourceVersion 机制实现状态管理。

好的，我将针对“实操指南”部分补充一些常用操作，包括查看和管理已安装的 Release、获取 Release 详细信息、调试和验证 Chart、导出部署的 Kubernetes 资源清单以及管理 Chart 仓库等，使内容更加丰富实用。以下是完善后的“实操指南”部分：

## 深入理解 Helm：Kubernetes 的应用包管理解决方案

## 五、实操指南：从安装到生产部署

### 1\. 环境准备

- Kubernetes 集群（1.20+ 版本）。
- Helm CLI 下载（ [官方安装指南](https://helm.sh/docs/intro/install/) ）：
```bash
# Linux/macOS
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Windows（PowerShell）
iwr -UseBasicParsing -Uri https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3.ps1 | iex
```

### 2\. 初始化配置（RBAC 授权）

创建 Helm 服务账户（推荐生产环境使用）：

```bash
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: helm
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: helm
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
- kind: ServiceAccount
  name: helm
  namespace: kube-system
EOF
```

配置 Helm 使用该账户：

```bash
helm config set --kubeconfig ~/.kube/config --namespace kube-system serviceaccount helm
```

### 3\. 创建第一个 Chart

#### 步骤 1：生成基础 Chart

```bash
helm create my-nginx
cd my-nginx
```

#### 步骤 2：修改配置（values.yaml）

```yaml
replicaCount: 2
image:
  repository: nginx
  tag: 1.23-alpine
  pullPolicy: IfNotPresent
service:
  type: ClusterIP
  port: 80
```

#### 步骤 3：部署到集群

```bash
helm install my-nginx-release .
```

#### 步骤 4：验证部署

```bash
kubectl get pods -l app.kubernetes.io/name=my-nginx
NAME                                   READY   STATUS    RESTARTS   AGE
my-nginx-release-66b6c64d44-5x4kf     1/1     Running   0          2m
my-nginx-release-66b6c64d44-zc2v7     1/1     Running   0          2m

helm status my-nginx-release
```

### 4\. 升级与回滚实战

#### 升级应用（修改副本数为 3）

```bash
helm upgrade my-nginx-release . -f values-prod.yaml --set replicaCount=3
```

#### 查看升级历史

```bash
helm history my-nginx-release
```

#### 回滚到上一版本

```bash
helm rollback my-nginx-release $(helm history my-nginx-release | awk 'NR==2 {print $1}')
```

### 5\. 使用公共 Chart 仓库

添加 Bitnami 仓库并安装 Redis：

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami 
helm repo update
helm install my-redis bitnami/redis -f redis-values.yaml
```

### 6\. 高级技巧：构建私有 Chart 仓库

1. 创建 Nginx 服务器作为仓库载体。
2. 推送 Chart 到仓库：
```bash
helm package mychart
helm push mychart-1.0.0.tgz http://your-repo-server/charts/
```
3. 添加私有仓库：
```bash
helm repo add myrepo http://your-repo-server/charts/
```

### 7\. 多环境配置管理

在实际项目中，不同环境（开发、测试、生产）的配置往往存在差异。我们可以通过创建多个 values 文件来实现多环境配置管理。

例如，在 `my-nginx` Chart 目录下，创建 `values-dev.yaml` 、 `values-test.yaml` 和 `values-prod.yaml` 文件。

`values-dev.yaml` 内容：

```yaml
replicaCount: 1
image:
  tag: 1.23-alpine
service:
  type: NodePort
  port: 30080
```

`values-test.yaml` 内容：

```yaml
replicaCount: 2
image:
  tag: 1.23-alpine
service:
  type: ClusterIP
  port: 80
```

`values-prod.yaml` 内容：

```yaml
replicaCount: 3
image:
  tag: 1.23-alpine
service:
  type: LoadBalancer
  port: 80
```

在不同环境部署时，指定对应的 values 文件：

```bash
# 部署到开发环境
helm install my-nginx-dev . -f values-dev.yaml

# 部署到测试环境
helm install my-nginx-test . -f values-test.yaml

# 部署到生产环境
helm install my-nginx-prod . -f values-prod.yaml
```

### 8\. 复杂应用部署

以部署一个包含数据库、后端服务和前端服务的全栈应用为例。假设我们有 `backend` 、 `frontend` 两个自定义 Chart，且 `backend` 依赖 `mysql` Chart。

首先，在 `backend/Chart.yaml` 中添加 `mysql` 依赖：

```yaml
dependencies:
- name: mysql
  version: "5.2.4"
  repository: "https://charts.bitnami.com/bitnami"
```

然后，在 `backend/values.yaml` 中配置 `mysql` 相关参数：

```yaml
mysql:
  auth:
    username: myuser
    password: mypassword
    database: mydb
```

接着，部署 `backend` 应用：

```bash
helm install my-backend backend
```

最后，部署 `frontend` 应用，并通过 `--set` 参数配置与 `backend` 服务的连接地址：

```bash
helm install my-frontend frontend --set backend.url=http://my-backend-service
```

### 9\. 与 CI/CD 流程集成

以 GitLab CI/CD 为例，实现自动化的 Helm 部署。

在 `.gitlab-ci.yml` 文件中添加如下配置：

```yaml
image:
  name: alpine:latest
  entrypoint: [""] 

stages:
  - build
  - deploy

build_chart:
  stage: build
  script:
    - helm package mychart
  artifacts:
    paths:
      - *.tgz

deploy:
  stage: deploy
  image:
    name: curlimages/curl:latest
    entrypoint: [""] 
  script:
    - helm repo add myrepo http://your-repo-server/charts/
    - helm repo update
    - helm upgrade --install my-release mychart-1.0.0.tgz -n my-namespace
  dependencies:
    - build_chart
  environment:
    name: production
    url: http://your-app-url
```

将代码推送到 GitLab 仓库后，CI/CD 流水线会自动构建 Chart 并部署到 Kubernetes 集群中。

### 10\. 查看和管理已安装的 Release

查看当前集群中所有命名空间下的 Release：

```bash
helm list --all-namespaces
```

查看特定命名空间中的 Release：

```bash
helm list -n <namespace>
```

查看 Release 的详细信息，包括版本、状态和值等：

```bash
helm show all <release-name>
```

筛选特定状态（如已部署、失败等）的 Release：

```bash
helm list --filter "deployed|failed"
```

### 11\. 获取 Release 详细信息

查看 Release 的状态，包括部署的资源、版本信息等：

```bash
helm status <release-name>
```

获取 Release 的值（values）信息：

```bash
helm get values <release-name>
```

获取 Release 的 Kubernetes 资源清单（manifest）：

```bash
helm get manifest <release-name>
```

获取 Release 的钩子（hooks）信息：

```bash
helm get hooks <release-name>
```

### 12\. 调试和验证 Chart

在不实际部署的情况下，预渲染 Chart 的模板文件，验证生成的 Kubernetes 资源清单：

```bash
helm template <release-name> ./mychart -f values.yaml
```

对 Chart 进行静态检查，验证其结构和内容的正确性：

```bash
helm lint ./mychart
```

在调试模式下安装 Chart，获取更详细的日志信息：

```bash
helm install <release-name> ./mychart --debug
```

### 13\. 导出部署的 Kubernetes 资源清单

将已部署的 Release 的 Kubernetes 资源清单导出到文件，方便备份或手动调整：

```bash
helm get manifest <release-name> > <release-name>-manifest.yaml
```

### 14\. 管理 Chart 仓库

更新本地已添加的 Chart 仓库索引：

```bash
helm repo update
```

搜索公共仓库中的 Chart：

```bash
helm search repo <chart-name>
```

移除不再需要的 Chart 仓库：

```bash
helm repo remove <repo-name>
```

查看已添加的 Chart 仓库列表：

```bash
helm repo list
```

### 15\. 其他实用操作

为 Release 添加或更新标签，便于分类和筛选：

```bash
helm label add <release-name> --label <key>=<value>
```

查看 Release 的变更历史记录，包括每次升级或回滚的详情：

```bash
helm history <release-name> --max 10
```

将当前 Release 的状态保存为快照，方便后续恢复或迁移：

```bash
helm snapshot save <release-name> <snapshot-name>
```

从快照恢复 Release 的状态：

```bash
helm snapshot restore <release-name> <snapshot-name>
```

查看 Helm 的版本信息，确保使用的是最新版本：

```bash
helm version
```

清理 Helm 的本地缓存，释放磁盘空间：

```bash
helm registry login <registry-url> -u <username> -p <password>
helm repo remove <repo-name>
```

以上新增的常用操作涵盖了 Helm 的多个方面，包括 Release 的管理、信息获取、调试验证、资源导出、仓库管理以及其他实用功能，希望这些内容能帮助读者更全面地掌握 Helm 的日常使用技巧。

## 六、最佳实践与生态整合

### 1\. 生产环境建议

- 使用 `helm template` 预渲染 YAML 进行安全审计。
- 通过 `helm secrets` 管理敏感配置（结合 Vault 或 Sealed Secrets）。
- 启用 Chartmuseum 进行企业级 Chart 仓库管理。
- 在 CI/CD 流程中集成 Helm（如 Argo CD、Jenkins X）。

### 2\. 生态工具链

- **Helm Hub** ：官方 Chart 搜索和搜索平台（ [https://hub.helm.sh/](https://hub.helm.sh/) ）。
- **起重机（Crane）** ：Helm Chart 依赖分析工具。
- **KubeVela** ：基于 Helm 的应用交付平台，支持多云环境。
- **Prometheus+Grafana** ：监控 Helm Release 的资源使用情况。

## 七、总结：Helm 如何改变 K8s 应用交付

从最初解决 YAML 管理痛点到成为云原生应用交付的事实标准，Helm 的进化史反映了 Kubernetes 生态从基础设施层向开发体验层的演进。其标准化的 Chart 格式、强大的模板引擎和完善的生命周期管理，让复杂微服务架构的部署变得可预测、可复用、可追溯。

无论是初创团队的快速迭代，还是企业级应用的多环境发布，Helm 都提供了统一的解决方案。随着云原生技术的普及，Helm 将继续在 GitOps、声明式 API、服务网格等领域发挥核心作用，成为连接开发、测试、运维的关键桥梁。

立即尝试在你的 Kubernetes 集群中部署第一个 Helm Chart，体验标准化应用交付带来的效率提升 —— 毕竟，管理 100 个微服务的最佳方式，不是维护 1000 个 YAML 文件，而是管理 100 个精心设计的 Chart。  
![](https://img2024.cnblogs.com/blog/3426651/202505/3426651-20250508165639742-619445069.png)