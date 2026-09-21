---
title: Helm 应用包管理
category: concepts
tags: [云原生, Kubernetes, Helm, 包管理, CI/CD]
aliases: [Helm, Helm Chart, K8s包管理]
relationships:
  - target: "[[concepts/k8s-architecture]]"
    type: related_to
  - target: "[[concepts/k8s-security]]"
    type: related_to
  - target: "[[synthesis/cloud-native-infrastructure-landscape]]"
    type: related_to
source_dir: Self learn/K8s和容器
source_files: [Helm深入理解-博客园.md, Helm部署模板编写指南-博客园.md]
summary: Helm是K8s的包管理器（"apt-get/yum of K8s"）：Chart打包+Values多环境分离+Release全生命周期；Helm 3移除Tiller转纯CLI；Go模板引擎+nindent缩进+--dry-run调试是核心技能
provenance:
  extracted: 0.72
  inferred: 0.22
  ambiguous: 0.06
base_confidence: 0.58
lifecycle: draft
lifecycle_changed: 2026-09-16
tier: supporting
created: 2026-09-16
updated: 2026-09-16
---

# Helm 应用包管理

Helm 是 Kubernetes 的应用包管理器——类比传统领域的 apt-get/yum，但带模板引擎。它解决 K8s 原生 YAML 管理的三大痛点：

- **碎片化管理**：多个 YAML（Deployment/Service/ConfigMap）→ 单一 Chart 包
- **环境差异化**：values 文件实现 dev/test/prod 配置分离
- **生命周期管理**：install/upgrade/rollback/delete 全流程可追溯

> ⚠️ 来源可信度：蒸馏自 `raw/sources/Self learn/K8s和容器/`（credibility: low），部分命令细节与官方文档有出入（已标 ^[ambiguous]）。

## 发展历史：从 Deis 到 CNCF

| 年份 | 事件 |
|------|------|
| 2015 | Deis 团队为简化 K8s 部署创建 Helm，引入 Chart 概念 |
| 2016 | 捐赠给 CNCF |
| 2018 | Helm 2.0：引入 Tiller 服务端组件（C/S 架构） |
| 2019 | 成为 CNCF 孵化项目 |
| 2020 | **Helm 3.0：移除 Tiller，纯 CLI 架构** |
| 2025 | 发展到 3.13，累计下载超 10 亿次 |

## 核心概念

- **Chart**：应用打包格式——K8s 资源定义+默认配置+元数据
- **Release**：Chart 在集群中的一次具体部署实例（同一 Chart 可装多次，每次一个新 Release）
- **Repository**：Chart 仓库（公共如 Artifact Hub / 私有自建）

Chart 目录结构：

```
mychart/
├── Chart.yaml          # 元数据（名称、版本、依赖）
├── values.yaml         # 默认配置
├── charts/             # 依赖 Chart
├── templates/          # K8s 资源模板
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── _helpers.tpl    # 命名模板助手
│   └── NOTES.txt       # 安装后提示
└── values.schema.json  # 配置校验
```

## 架构演进：C/S → 纯 CLI

**Helm 2.x**：Helm CLI（用户交互+模板渲染）+ Tiller（集群内服务端，与 API Server 交互、存储 Release 状态）。Tiller 需要过高集群权限，是安全隐患。

**Helm 3.0**：移除 Tiller——
- 直接通过 Kubeconfig 与 API Server 认证
- Release 状态存储在集群内 ^[ambiguous]（原文称"CustomResource + release-history ConfigMap"；实际 Helm 3 默认以 Secret 形式存储于 Release 所属命名空间——两说不一致，以官方文档为准）

**渲染五步流程**：参数合并（values.yaml → -f 文件 → --set，后者覆盖前者）→ Go 模板引擎渲染 → 递归解析依赖 → API Server 校验（admission webhook）→ 提交部署。

**版本控制**：每次 upgrade 生成新 REVISION 记录，`helm history` 查看，`helm rollback <release> <revision>` 按修订号恢复。

## 模板语法核心（编写 Chart 必备）

### 五大内置对象

| 对象 | 访问内容 | 示例 |
|------|----------|------|
| `.Values` | values.yaml / --set 传入值 | `{{ .Values.replicaCount }}` |
| `.Release` | 发布信息 | `.Release.Name`、`.Release.Namespace` |
| `.Chart` | Chart.yaml 元数据 | `.Chart.Name`、`.Chart.Version` |
| `.Files` | Chart 中非模板文件 | — |
| `.Capabilities` | 集群信息（API 版本等） | — |

### 管道与函数（Go 模板 + Sprig 函数库）

```
{{ .Release.Name | lower | trunc 63 }}              # 小写+截断63字符（K8s 名称限制）
{{ .Values.image.pullPolicy | default "IfNotPresent" }}  # 默认值兜底
{{ .Values.service.port | int }}                    # 类型转换
{{- include "mychart.labels" . | nindent 4 }}       # 包含命名模板并缩进4空格
```

### 控制流

```
{{- if .Values.ingress.enabled }} ... {{- end }}    # 条件；{{- 删除前导空白
{{- range $key, $value := .Values.env }}             # 循环遍历
- name: {{ $key }}
  value: {{ $value | quote }}
{{- end }}
```

### 命名模板（_helpers.tpl）

```
{{- define "mychart.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
```

**缩进是模板最大坑**：`include` 展开多行片段时必须用 `nindent`（换行+缩进）而非 `indent`，否则 YAML 层级错乱。

## 常用命令速查

| 类别 | 命令 | 说明 |
|------|------|------|
| 仓库 | `helm repo add/list/update/remove` | Chart 仓库管理 |
| 查询 | `helm search repo/hub`、`helm show values` | **`helm show values` 先看默认配置再写覆盖文件** |
| 生命周期 | `helm install/upgrade/rollback/uninstall`、`helm history` | Release 全流程 |
| 检查 | `helm list -n <ns>`、`helm status`、`helm get values/manifest` | 查看已部署状态 |
| 开发 | `helm create/lint/template/package` | Chart 骨架/检查/本地渲染/打包 |
| 依赖 | `helm dependency update` | 按 Chart.yaml 拉取依赖到 charts/ |

**部署前三连（调试铁律）**：

```
helm lint ./mychart                                    # 1. 语法检查
helm template my-release ./mychart                     # 2. 本地渲染看最终 YAML
helm install my-release ./mychart --dry-run --debug    # 3. 模拟安装+详细渲染信息
```

## 多环境配置管理

同一 Chart + 不同 values 文件实现环境分离：

```
helm install my-nginx-dev  . -f values-dev.yaml    # 1副本 NodePort
helm install my-nginx-test . -f values-test.yaml   # 2副本 ClusterIP
helm install my-nginx-prod . -f values-prod.yaml   # 3副本 LoadBalancer
```

依赖声明（backend 依赖 mysql）：

```yaml
# Chart.yaml
dependencies:
- name: mysql
  version: "5.2.4"
  repository: "https://charts.bitnami.com/bitnami"
```

## 最佳实践

- **敏感信息不入 values.yaml**：用 K8s Secrets（模板中 `.Values.secretName` 引用）或 HashiCorp Vault 注入——见 [[concepts/k8s-security]]
- **`helm template` 预渲染做安全审计**：部署前看到将创建的全部资源
- **`--set` 只用于临时调试**，正式环境用 `-f` values 文件（可版本化）
- **CI/CD 集成**：`helm package` 构建产物 → `helm upgrade --install` 幂等部署（GitLab CI/Argo CD/Jenkins X）
- **私有仓库**：ChartMuseum 或 OCI registry 承载企业级 Chart 分发

## 未解问题

- 原文中部分命令疑为 Helm 2 语法或不存在（`helm delete --purge`、`helm config set`、`helm snapshot save`）^[ambiguous]——使用前应对照官方文档核验
- Helm 与 Kustomize 的分工边界（模板渲染 vs 无模板覆盖）原文未涉及 ^[inferred]

## 来源

- Helm深入理解-博客园（历史/架构/生命周期/CI-CD 集成）
- Helm部署模板编写指南-博客园（模板语法/命令速查/调试技巧）
- 均位于 raw/sources/Self learn/K8s和容器/（credibility: low）
- 相关页面：[[concepts/k8s-cni-comparison]]（同主题群）、[[concepts/k8s-networking]]
