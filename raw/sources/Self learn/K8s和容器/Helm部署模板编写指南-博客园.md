---
credibility: low
---

Helm作为Kubernetes的包管理工具，通过模板化的方式简化了应用的部署流程。本文将深入探讨Helm模板的编写方法，涵盖常用语法、命令以及注意事项，帮助您快速掌握Helm模板的核心技巧。

## 一、Helm模板基础

Helm模板使用Go模板语言，结合Kubernetes YAML文件，生成最终的部署清单。一个典型的Helm模板文件结构如下：

```
mychart/
├── Chart.yaml          # 定义Chart的元数据（名称、版本、依赖等）
├── values.yaml         # 存储默认配置值
├── templates/          # 存放所有Kubernetes资源模板文件
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── _helpers.tpl    # 定义可重用的命名模板
│   └── NOTES.txt       # 安装后提示信息
├── charts/             # 存放子Chart或依赖Chart
└── .helmignore         # 指定打包时忽略的文件
```

**核心概念** ：

- **Chart** ：一个Helm包，包含运行某个应用所需的所有Kubernetes资源定义。
- **Release** ：在Kubernetes集群中运行的Chart的一个实例。同一个Chart可以安装多次，每次安装都会创建一个新的Release。
- **Repository** ：用于存放和共享Chart的仓库。

Helm的核心价值在于其能够将复杂的Kubernetes应用及其依赖关系打包成一个可版本化、可分享、可重复部署的单元。

## 二、常用模板语法详解

### 1\. 变量与内置对象

Helm模板通过点（`.`）来访问上下文。常用的内置对象包括：

- `.Values` ：访问 `values.yaml` 文件或通过 `--set` 传入的值，这是模板参数化的核心。
- `.Release` ：访问发布信息，如 `.Release.Name` （Release名称）、`.Release.Namespace` （命名空间）。
- `.Chart` ：访问 `Chart.yaml` 文件中定义的元数据，如 `.Chart.Name` 、`.Chart.Version` 。
- `.Files` ：访问Chart中的非模板文件。
- `.Capabilities` ：访问Kubernetes集群的信息，如API版本。

示例：

```
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}-{{ .Chart.Name }} # 生成唯一资源名
spec:
  replicas: {{ .Values.replicaCount }}
  template:
    spec:
      containers:
      - name: {{ .Chart.Name }}
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
        ports:
        - containerPort: {{ .Values.service.port }}
```

### 2\. 管道与函数

Helm提供了强大的管道（Pipeline）功能，允许将多个函数串联处理数据。它还内置了大量函数（包括Go模板函数和Sprig函数库）。

```
# 字符串处理：将Release名称转换为小写，并截断至63个字符
name: {{ .Release.Name | lower | trunc 63 }}

# 默认值设置：如果image.pullPolicy未定义，则使用"IfNotPresent"
imagePullPolicy: {{ .Values.image.pullPolicy | default "IfNotPresent" }}

# 缩进与YAML处理：包含命名模板并正确缩进2个空格
labels:
  {{- include "mychart.labels" . | nindent 2 }}

# 类型转换：将字符串端口号转换为整数
port: {{ .Values.service.port | int }}
```

### 3\. 控制流（条件与循环）

**条件判断** ：使用 `if/else` 根据条件生成不同的配置。

```
{{- if .Values.ingress.enabled }} # 注意 \`-\` 会去除前面的空白符
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ .Release.Name }}-ingress
spec:
  ...
{{- end }} # 结束if语句
```

**循环遍历** ：使用 `range` 遍历列表或键值对。

```
# values.yaml中定义
env:
  LOG_LEVEL: INFO
  DATABASE_URL: postgresql://localhost/mydb

# templates/deployment.yaml中使用
env:
{{- range $key, $value := .Values.env }}
- name: {{ $key }}
  value: {{ $value | quote }}
{{- end }}
```

### 4\. 命名模板与局部模板

为了提高模板的复用性和可维护性，可以在 `_helpers.tpl` 中定义命名模板。

```
# 在 _helpers.tpl 中定义
{{- define "mychart.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end -}}

{{- define "mychart.labels" -}}
app.kubernetes.io/name: {{ include "mychart.fullname" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}
```

在模板文件中使用命名模板：

```
# 在 deployment.yaml 中使用
metadata:
  name: {{ include "mychart.fullname" . }}
  labels:
    {{- include "mychart.labels" . | nindent 4 }} # 使用nindent保证缩进正确
```

## 三、Helm常用命令大全（实操核心）

为了方便查阅，以下将Helm常用命令按功能分类列出。

### 1\. 仓库管理 (helm repo)

| 命令 | 说明 | 示例 |
| --- | --- | --- |
| `helm repo add` | 添加仓库 | `helm repo add bitnami https://charts.bitnami.com/bitnami` |
| `helm repo list` | 列出已添加的仓库 | `helm repo list` |
| `helm repo update` | 更新仓库中的Chart索引 | `helm repo update` |
| `helm repo remove` | 移除仓库 | `helm repo remove bitnami` |

### 2\. Chart查询与检查 (helm search/show)

| 命令 | 说明 | 示例 |
| --- | --- | --- |
| `helm search repo` | 从已添加仓库中搜索Chart | `helm search repo nginx` |
| `helm search hub` | 从Artifact Hub中搜索Chart | `helm search hub mysql` |
| `helm show chart` | 显示Chart的基本信息 | `helm show chart bitnami/nginx` |
| `helm show values` | **显示Chart的默认可配置值（重要）** | `helm show values bitnami/nginx > myvalues.yaml` |
| `helm show all` | 显示Chart的所有信息 | `helm show all bitnami/nginx` |

### 3\. Chart安装与管理 (helm install/list/upgrade...)

| 命令 | 说明 | 示例 |
| --- | --- | --- |
| `helm install` | 安装Chart | `helm install my-release ./mychart` |
| `helm list` | 列出已安装的Release | `helm list -n <namespace>` |
| `helm upgrade` | 升级Release | `helm upgrade my-release ./mychart -f new-values.yaml` |
| `helm history` | 查看Release的修订历史 | `helm history my-release` |
| `helm rollback` | 回滚Release到指定版本 | `helm rollback my-release 1` |
| `helm uninstall` | 卸载Release | `helm uninstall my-release` |

### 4\. Chart开发与调试 (helm create/lint/template...)

| 命令 | 说明 | 示例 |
| --- | --- | --- |
| `helm create` | 创建新的Chart骨架 | `helm create mychart` |
| `helm lint` | 检查Chart的语法和格式是否正确 | `helm lint ./mychart` |
| `helm template` | 本地渲染模板，查看生成的K8s资源清单 | `helm template my-release ./mychart` |
| `helm get manifest` | 获取已安装Release生成的资源清单 | `helm get manifest my-release` |

### 5\. Chart打包与分发 (helm package/dependency...)

| 命令 | 说明 | 示例 |
| --- | --- | --- |
| `helm package` | 将Chart目录打包成`.tgz` 压缩文件 | `helm package ./mychart` |
| `helm dependency update` | 根据 `Chart.yaml` 更新依赖包到 `charts/` 目录 | `helm dependency update ./mychart` |
| `helm pull` | 从仓库拉取（下载）Chart | `helm pull bitnami/nginx --untar` |

### 6\. 调试与预安装（极其重要）

在实际安装之前，强烈建议使用以下命令进行调试和预览：

```
# 1. 语法检查
helm lint ./mychart

# 2. 模拟安装并渲染模板，检查生成的YAML是否正确
# --dry-run 模拟安装，不真正创建资源
# --debug 显示渲染的详细信息
helm install my-release ./mychart --dry-run --debug

# 3. 或者使用 \`helm template\` 仅渲染模板
helm template my-release ./mychart
```

## 四、最佳实践与注意事项

1. **模板命名规范** ：模板文件名应使用小写字母和连字符，如 `my-awesome-chart` 。命名模板（在 `_helpers.tpl` 中）使用点分隔的命名空间，如 `mychart.labels` 。
2. **缩进处理** ：使用 `nindent` 函数可以智能处理包含模板片段后的缩进问题。
	```
	# 正确示例：使用 nindent
	metadata:
	  labels:
	{{- include "mychart.labels" . | nindent 4 }} # 包含内容会被缩进4个空格
	# 错误示例：缩进可能不一致
	metadata:
	  labels:
	{{- include "mychart.labels" . }}
	```
3. **值文件管理** ： 使用 `values.yaml` 作为默认配置。 为不同环境（如开发、测试、生产）创建不同的values文件（ `values-dev.yaml`, `values-prod.yaml` ）。 使用 `-f` 选项指定自定义values文件来覆盖默认值： `helm install -f values-prod.yaml ...`。 使用 `--set` 快速覆盖单个值（适用于临时调试）： `helm upgrade ... --set image.tag=latest` 。
4. **依赖管理** ：在 `Chart.yaml` 中声明依赖，并使用 `helm dependency update` 来下载依赖。
	```
	# Chart.yaml
	dependencies:
	  - name: mysql
	    version: "8.5.0"
	    repository: "https://charts.bitnami.com/bitnami"
	```
5. **安全注意事项** ： **避免在values.yaml中直接存储敏感信息** （如密码、密钥）。应使用Kubernetes Secrets管理敏感数据，在模板中通过`.Values.secretName` 引用，或在安装时通过外部方式（如HashiCorp Vault）注入。 定期更新所依赖的Chart版本，以获取安全补丁和新功能。

## 五、实战案例：调试与故障排查

即使遵循了最佳实践，编写模板时也难免出错。Helm提供了有效的调试工具。

1. **使用 `--dry-run --debug`** ：这是部署前最关键的检查步骤。它可以让你看到模板渲染后的最终YAML内容，而无需真正安装到集群。
	```
	helm install my-app ./my-chart --dry-run --debug
	```
	这个命令会输出所有将被创建的Kubernetes资源清单，仔细检查以确保其符合预期，如资源名称、镜像标签、环境变量等是否正确注入。
2. **常见错误与排查** ： **模板渲染错误** ：通常是模板语法错误或引用了不存在的变量。使用 `helm lint` 和 `helm template --debug` 定位问题。 **依赖冲突** ：使用 `helm dependency list` 和 `helm dependency update` 确保依赖一致。 **资源创建失败** ：检查 `helm get manifest <release-name>` 输出的YAML是否正确，并使用 `kubectl describe` 和 `kubectl get events` 查看Kubernetes的具体报错信息。

## 六、总结

Helm模板通过强大的模板引擎和丰富的功能，极大地简化了Kubernetes应用的部署和管理。掌握模板语法、合理组织文件结构、遵循最佳实践，可以编写出既灵活又可维护的Helm Chart。

本指南从基础概念到常用命令，再到最佳实践和调试技巧，提供了较为全面的概述。建议从创建一个简单的Chart开始，逐步尝试更复杂的模板功能，结合 `--dry-run --debug` 命令不断验证。随着实践的深入，你会越发体会到Helm在管理复杂应用部署时的巨大价值。

本文来自博客园，作者： [dashery](https://www.cnblogs.com/ydswin/) ，转载请注明原文链接： [https://www.cnblogs.com/ydswin/p/19327845](https://www.cnblogs.com/ydswin/p/19327845)

posted on [dashery](https://www.cnblogs.com/ydswin) 阅读(1186) 评论(2) 收藏 [举报](https://report.cnblogs.com/?targetLink=https%3A%2F%2Fwww.cnblogs.com%2Fydswin%2Fp%2F19327845&targetId=19327845&targetType=0)