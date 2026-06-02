---
title: Prometheus 监控架构
category: concepts
tags: [云原生, Prometheus, 监控, TSDB, 可观测性]
aliases: [Prometheus原理, Prometheus架构]
relationships:
  - target: "[[concepts/k8s-architecture]]"
    type: related_to
  - target: "[[concepts/llm-observability]]"
    type: related_to
  - target: "[[concepts/linux-tracing-frameworks]]"
    type: related_to
source_dir: Prometheus
source_files: [Prometheus-博客园-原理详解.md]
summary: Prometheus是Google BorgMon开源版+K8s标配监控；Pull模型+ServiceDiscovery+PromQL查询；每样本~3.5字节存储；Histogram可聚合但Summary不可聚合；ServiceMonitor CRD实现K8s自动发现
provenance:
  extracted: 0.70
  inferred: 0.25
  ambiguous: 0.05
base_confidence: 0.55
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-02
---

# Prometheus 监控架构

Prometheus 是 Google BorgMon 的开源版本 ^[ambiguous]（社区对此说法有争议，更准确说是"受BorgMon启发"），2016年作为CNCF第二个托管项目加入。随着Kubernetes成为容器编排主流，Prometheus成为K8s容器监控的标准解决方案。

## 核心观点

- **Pull模型**是Prometheus的核心设计：Server主动拉取(scrape)目标指标，而非agent推送。与Pushgateway配合处理短生命周期或不可达任务。
- **每个样本约3.5字节**：百万时间序列×30秒间隔×60天保留 ≈ 200+GB存储。
- **Prometheus Server是唯一必需组件**：Pushgateway、Alertmanager、Exporter、Client Library都是可选的。
- **Histogram可聚合但Summary不可聚合**：Histogram客户端便宜（只增计数器）但服务端计算分位数贵；Summary客户端贵（流式计算）但服务端便宜。
- **ServiceMonitor CRD是K8s集成的关键**：Prometheus Operator观察ServiceMonitor变化，动态生成配置，无需重启。

## 架构组件

| 组件 | 功能 | 是否必需 |
|------|------|---------|
| **Prometheus Server** | 存储+抓取+查询+告警规则 | 必需 |
| **Pushgateway** | 短生命周期/不可达任务的推送缓冲 | 可选 |
| **Alertmanager** | 告警去重/分组/路由 | 可选 |
| **Exporter** | 第三方系统指标代理 | 可选 |
| **Client Library** | 应用内嵌指标暴露 | 可选 |

## 数据模型

### 时间序列 = metric_name + labels

每个数据点 = 64位时间戳 + 64位样本值（所有值都是float64）。metric_name是语义标识（如`http_requests_total`），labels是维度区分（如`method="GET"`）。内部metric_name存为特殊label `__name__`——所有时间序列是扁平key-value结构。

### 四种指标类型

| 类型 | 用途 | 关键特性 |
|------|------|---------|
| **Counter** | 只增计数 | 累计值，`rate()`计算速率 |
| **Gauge** | 可增可减 | 当前值（温度/内存使用） |
| **Histogram** | 观察值分布 | 可配置bucket+sum+count；服务端计算分位数 |
| **Summary** | 观察值分位数 | 客户端流式计算分位数；不可聚合 |

### Histogram vs Summary

| 维度 | Histogram | Summary |
|------|-----------|---------|
| 客户端开销 | 低（只增计数器） | 高（流式计算） |
| 服务端开销 | 高（PromQL计算分位数） | 低 |
| 聚合能力 | **可聚合** | **不可聚合** |
| 分位数精度 | 取决于bucket配置 | 客户端配置 |
| 推荐场景 | 多实例聚合 | 单实例精确分位数 |

## Pushgateway 使用与限制

**使用场景**：短生命周期任务（Prometheus来不及scrape就退出）；防火墙隔离的目标；业务数据聚合。

**三大缺陷**：
1. 单点故障风险（多节点聚合时）
2. Prometheus `up` 状态只反映Pushgateway健康，不反映个体目标
3. 离线目标的陈旧数据残留，需手动清理

**推荐做法**：Exporter集成优先于Pushgateway——将Client Library直接嵌入应用代码（如Kubernetes和ETCD的做法）。 ^[inferred]

## ServiceDiscovery 与 K8s 集成

Prometheus支持多种发现机制：DNS、Kubernetes、Consul、`file_sd`。

### ServiceMonitor CRD工作流

```
ServiceMonitor (CRD, label selector选择Service)
  → Prometheus Operator 观察变化
  → 动态生成 Prometheus 配置
  → 无需手动编辑/重启
```

### additionalScrapeConfigs

外部监控目标（MySQL/Redis/Nacos/ES/Zookeeper/Nginx）通过Secret资源配置，Prometheus Operator通过`additionalScrapeConfigs`引用——无需修改核心Prometheus配置。

## TSDB 内部

### 特征

| 维度 | TSDB特性 |
|------|---------|
| 写模式 | 大部分顺序写 |
| 更新 | 很少 |
| 删除 | 按时间范围批量删 |
| 数据量 | 超内存 |
| 读模式 | 顺序升序/降序 |

### 存储引擎

原文声称Prometheus使用LevelDB引擎 ^[ambiguous]（这可能反映Prometheus v1.x；现代v2.x使用自定义TSDB实现而非LevelDB）。LevelDB高顺序读写性能适合TSDB模式。

### 存储效率

每样本约3.5字节（引用官方PPT数据）。百万时间序列×30秒间隔×60天保留 ≈ 200+GB。

## 关键细节

### PromQL 数据类型

| 类型 | 说明 |
|------|------|
| Instant Vector | 某一时刻的一组时间序列 |
| Range Vector | 一段时间范围内的时间序列 |
| Scalar | 纯数字值 |
| String | 纯字符串（目前未使用） |

### Job/Instance 语义

- **Instance**：单个scrape目标（一个进程）
- **Job**：同一用途的instance集合（如多个副本的API服务器）

### K8s部署模式

node-exporter用DaemonSet部署（每Node一个）；Prometheus Operator（kube-prometheus）管理整个监控栈。

## 未解问题

- Prometheus v2.x 自定义TSDB与LevelDB的具体差异？ ^[ambiguous] 来源声称LevelDB但可能过时。
- Pushgateway陈旧数据自动清理机制？
- Histogram bucket边界的最佳选择策略？

## 来源

- Prometheus-博客园-原理详解 — 架构+数据模型+K8s部署+ServiceMonitor

> **可信度注意**：来源标记为 `credibility: low`（博客园个人博客），LevelDB声称可能过时，"BorgMon开源版"说法在社区有争议。