---
title: K8s 安全加固实操指南
category: skills
tags: [云原生, Kubernetes, 安全, RBAC, NetworkPolicy]
source_dir: Kubernetes（K8s）
source_files: [K8s安全加固完全指南.md]
summary: K8s安全五维度实操：RBAC最小权限配置+NetworkPolicy默认拒绝+PSS restricted级+Secret EncryptionConfiguration+API Server匿名禁用；八项检查清单
provenance:
  extracted: 0.85
  inferred: 0.12
  ambiguous: 0.03
base_confidence: 0.80
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-02
---

# K8s 安全加固实操指南

## 概述

K8s安全加固五维度：RBAC权限控制、NetworkPolicy流量隔离、Pod Security标准、Secrets加密存储、API Server入口管控。每个维度都有对应的YAML配置和验证命令。

## 前置条件

- K8s集群已运行
- kubectl已配置
- 了解基本YAML语法

## 步骤

### 1. RBAC配置

为每个应用创建独立ServiceAccount + 最小权限Role：

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-app-sa
  namespace: my-namespace
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: my-app-role
  namespace: my-namespace
rules:
  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: my-app-binding
  namespace: my-namespace
subjects:
  - kind: ServiceAccount
    name: my-app-sa
roleRef:
  kind: Role
  name: my-app-role
  apiGroup: rbac.authorization.k8s.io
```

**验证**：`kubectl auth can-i --list --as=system:serviceaccount:my-namespace:my-app-sa`

### 2. NetworkPolicy默认拒绝

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: my-namespace
spec:
  podSelector: {}
  policyTypes:
    - Ingress
```

然后选择性放行：

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-specific
spec:
  podSelector:
    matchLabels:
      app: my-app
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - port: 8080
```

### 3. Pod Security restricted级

Namespace级标签强制restricted：

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: my-namespace
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

Pod级SecurityContext：

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  allowPrivilegeEscalation: false
  capabilities:
    drop: ["ALL"]
  readOnlyRootFilesystem: true
  seccompProfile:
    type: RuntimeDefault
```

### 4. Secret加密配置

```yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources: ["secrets"]
    providers:
      - aescbc:
          keys:
            - name: key1
              secret: <BASE64_ENCODED_SECRET>
      - identity: {}
```

API Server启动参数：`--encryption-provider-config=/etc/kubernetes/encryption-config.yaml`

密钥轮换：`kubectl get secrets --all-namespaces -o json | kubectl replace -f -`

### 5. API Server加固

启动参数：
- `--anonymous-auth=false`
- 启用AlwaysPullImages准入插件

Kubelet配置：
- `--anonymous-auth=false`
- `--authorization-mode=Webhook`

## 常见问题

| 问题 | 原因 | 解法 |
|------|------|------|
| Pod启动失败 | PSS restricted限制 | 检查SecurityContext字段 |
| 网络不通 | NetworkPolicy默认拒绝 | 添加选择性放行规则 |
| Secret读不了 | 加密配置错误 | 检查EncryptionConfiguration路径 |
| RBAC权限不足 | Role定义不完整 | 用`kubectl auth can-i`逐条验证 |

## 安全检查清单

1. ✅ Pod Security restricted级已启用
2. ✅ 应用使用独立ServiceAccount
3. ✅ RBAC遵循最小权限
4. ✅ etcd Secret加密已启用
5. ✅ API Server `--anonymous-auth=false`
6. ✅ Kubelet认证/授权已启用
7. ✅ Pod非root运行
8. ✅ NetworkPolicy默认拒绝

## 进阶用法

- 使用HashiCorp Vault/AWS Secrets Manager替代原生Secret
- 将所有安全配置纳入GitOps（ArgoCD管理）
- 用`kubectl who-can`工具持续审计RBAC权限

## 来源

- K8s安全加固完全指南 — 五维度YAML配置+检查清单