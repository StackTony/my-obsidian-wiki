---
title: Kubernetes 安全加固
category: concepts
tags: [云原生, Kubernetes, 安全, RBAC, NetworkPolicy]
aliases: [K8s安全, K8s安全加固]
relationships:
  - target: "[[concepts/k8s-architecture]]"
    type: related_to
  - target: "[[concepts/seccomp-capabilities]]"
    type: uses
  - target: "[[concepts/container-runtime-deep-dive]]"
    type: related_to
source_dir: Kubernetes（K8s）
source_files: [K8s安全加固完全指南.md]
summary: K8s安全五维度加固：RBAC最小权限+NetworkPolicy默认拒绝+PSS restricted+etcd Secret加密+API Server匿名禁用；安全基线纳入GitOps成为默认状态
provenance:
  extracted: 0.88
  inferred: 0.10
  ambiguous: 0.02
base_confidence: 0.80
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-11
---

# Kubernetes 安全加固

K8s 安全不是单一措施——它是**五维度纵深防御**：RBAC权限控制、NetworkPolicy流量隔离、Pod Security标准、Secrets加密存储、API Server入口管控。每个维度都是独立防线，组合形成安全基线。

## 核心观点

- **每个应用必须使用独立 ServiceAccount**：默认 SA 绝不可用，RBAC遵循最小权限原则。
- **NetworkPolicy 默认拒绝入站**是强制最佳实践：先关所有门，再选择性开窗。
- **PSS (Pod Security Standards) 取代 PSP**：三级标准 privileged/baseline/restricted，生产必须 restricted。
- **Secrets 默认是 Base64 明文存于 etcd**：生产必须配置 EncryptionConfiguration 启用加密。
- **所有安全配置应纳入 GitOps**：安全基线成为默认状态，而非事后补救。

## 五维度加固

### 1. RBAC：权限控制

模式：ServiceAccount → Role → RoleBinding（Namespace级）/ClusterRoleBinding（集群级）。

**最佳实践**：
- 每个应用独立 SA + 最小权限 Role
- 禁止使用默认 SA（`default`）
- 定期审计 RBAC 权限

### 2. NetworkPolicy：流量隔离

Pod级防火墙规则，控制L3/L4 Pod间访问。

**最佳实践**：
- Namespace级别 default-deny-ingress（先全关）
- 选择性放行：只允许需要的Pod间通信
- 生产集群必须部署 CNI 插件支持 NetworkPolicy（Calico/Cilium）

### 3. Pod Security：容器安全

PSS 三级标准取代已废弃的 PSP：

| 级别 | 限制强度 | 适用场景 |
|------|----------|----------|
| **privileged** | 不限制 | 系统组件/特殊需求 |
| **baseline** | 最小限制 | 一般应用 |
| **restricted** | 强限制 | 生产推荐 |

**Restricted 级四大核心要求**：
1. `runAsNonRoot: true` — 禁止root运行
2. `allowPrivilegeEscalation: false` — 禁止提权
3. `capabilities: drop ALL` — 丢弃所有Linux权限
4. `readOnlyRootFilesystem: true` — 只读根文件系统

### 4. Secrets Encryption：数据加密

etcd中Secrets默认Base64编码（≈明文）。生产必须配置 EncryptionConfiguration：

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

> ⚠️ **矛盾标注**：原文示例使用 `aescbc` provider，但K8s官方推荐生产环境使用 `aesgcm` 或 `kms` provider。`aescbc` 因CBC模式的padding oracle攻击风险已被认为不够安全。^[ambiguous] ^[inferred]

**密钥轮换流程**：
1. 新增新密钥为第一provider
2. 所有Secret重加密：`kubectl get secrets --all-namespaces -o json | kubectl replace -f -`
3. 将旧密钥移至第二位（解密用）
4. 确认无旧密钥加密数据后移除旧密钥

**生产推荐**：使用 HashiCorp Vault 或 AWS Secrets Manager 替代原生 Secret 管理。

### 5. API Server & Kubelet 加固

| 配置 | 要求 | 说明 |
|------|------|------|
| `--anonymous-auth=false` | 必须 | 关闭API Server匿名访问 |
| `AlwaysPullImages` 准入插件 | 必须 | 强制每次拉取镜像，防缓存攻击 |
| Kubelet `--anonymous-auth=false` | 必须 | 关闭Kubelet匿名 |
| Kubelet `--authorization-mode=Webhook` | 必须 | 启用授权检查 |

## 安全检查清单

1. ✅ Pod Security restricted 级已启用
2. ✅ 应用使用独立 ServiceAccount
3. ✅ RBAC遵循最小权限原则
4. ✅ etcd Secret加密已启用
5. ✅ API Server `--anonymous-auth=false`
6. ✅ Kubelet认证/授权已启用
7. ✅ Pod非root运行
8. ✅ NetworkPolicy默认拒绝已配置

## 关键细节

### SecurityContext 配置示例

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

### Seccomp 与 Capabilities

Seccomp 限制容器系统调用访问（RuntimeDefault 是推荐 profile）；Capabilities 是细粒度 Linux 权限控制——restricted级要求 drop ALL。详见 [[concepts/seccomp-capabilities]]。

## 未解问题

- aescbc之外哪种加密provider最适合生产？
- 大规模密钥轮换的自动化方案？
- RBAC权限的持续审计和监控机制？


## 延伸阅读

实操指南：[[skills/k8s-security-hardening]]

综合分析：[[synthesis/cloud-native-infrastructure-landscape]]

## 来源

- K8s安全加固完全指南 — 五维度YAML配置+检查清单
- [[summaries/k8s-terminology-cheatsheet]] — RBAC/PSS/Seccomp术语定义