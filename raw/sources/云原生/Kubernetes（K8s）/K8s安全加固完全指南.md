随着Kubernetes在企业中的大规模普及，安全加固成为运维团队的首要任务。本文从RBAC权限控制、网络策略、Pod安全准入、Secrets加密、API Server加固五个维度，提供可直接落地的实战配置。

## 一、RBAC 权限控制

每个应用使用独立 ServiceAccount，绑定最小权限 Role。禁止使用 default SA。

ServiceAccount + Role + RoleBinding：

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: myapp-sa
  namespace: production
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: myapp-role
  namespace: production
rules:
- apiGroups: [""]
  resources: ["configmaps", "pods"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: myapp-rb
  namespace: production
subjects:
- kind: ServiceAccount
  name: myapp-sa
  apiGroup: ""
roleRef:
  kind: Role
  name: myapp-role
  apiGroup: ""
```

定期执行 `kubectl who-can '*' '*'` 审计高危权限。

## 二、网络策略（NetworkPolicy）

默认拒绝所有入站，按需放行必要流量。

默认拒绝入站：

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress
```

放行 ingress 到 backend:8080：

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-ingress
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: ingress-controller
    ports:
    - protocol: TCP
      port: 8080
```

限制出口（DNS + postgres:5432）：

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-egress
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
    ports:
    - protocol: UDP
      port: 53
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
```

## 三、Pod 安全（PSA）

PSP 已废弃，使用内置 **Pod Security Standards（PSS）** 。

命名空间启用 restricted：

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: latest
```

Pod 安全上下文：

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secure-app
  namespace: production
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 10000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: myapp:latest
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
```

四项核心要求：禁止 root 运行（ `runAsNonRoot` ）、禁止提权（ `allowPrivilegeEscalation: false` ）、丢弃所有 Capabilities（ `drop: ALL` ）、根文件系统只读（ `readOnlyRootFilesystem: true` ）。

## 四、Secrets 加密

Secrets 默认 base64 明文存储在 etcd，必须加密。

生成密钥： `head -c 32 /dev/urandom | base64`

加密配置：

```yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
    - secrets
    providers:
    - aescbc:
        keys:
        - name: key1
          secret: <base64编码的32字节密钥>
    - identity: {}
```

kube-apiserver 启动参数：

```bash
--encryption-provider-config=/etc/kubernetes/encryption-config.yaml
--encryption-provider-config-auto-reload=true
```

密钥轮换后重加密已有 Secrets：

```bash
kubectl get secrets --all-namespaces -o json | kubectl replace -f -
```

生产推荐 HashiCorp Vault / AWS Secrets Manager。

## 五、API Server 加固

关闭匿名访问：

```bash
--anonymous-auth=false
```

启用 AlwaysPullImages 准入控制器：

```bash
--enable-admission-plugins=AlwaysPullImages,...
```

Kubelet 收紧认证授权：

```yaml
authentication:
  anonymous:
    enabled: false
  webhook:
    enabled: true
authorization:
  mode: Webhook
```

## 检查清单

```
[ ] Pod Security restricted 已启用
[ ] 应用使用独立 ServiceAccount
[ ] RBAC 符合最小权限原则
[ ] etcd Secrets 加密已启用
[ ] API Server --anonymous-auth=false
[ ] Kubelet 认证授权已开启
[ ] Pod 以非 root 运行
[ ] NetworkPolicy 默认 deny 已配置
```

以上配置纳入 GitOps，安全基线成为默认状态。