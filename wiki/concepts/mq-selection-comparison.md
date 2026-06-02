---
title: 消息队列选型对比（Kafka/RocketMQ/RabbitMQ）
category: concepts
tags: [消息队列, Kafka, RocketMQ, RabbitMQ, 选型]
summary: 三大MQ全面对比：Kafka(高吞吐低可靠)、RocketMQ(高可靠支持事务)、RabbitMQ(低延迟灵活路由)——选型围绕可靠性、吞吐量、队列数三个维度
source_dir: 消息队列
source_files: [三大MQ选型对比-博客园.md]
provenance:
  extracted: 0.60
  inferred: 0.35
  ambiguous: 0.05
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-02
relationships:
  - target: "[[concepts/kafka-architecture]]"
    type: related_to
---

# 消息队列选型对比（Kafka/RocketMQ/RabbitMQ）

三大MQ各有擅长，选型核心围绕三个维度：**可靠性要求、吞吐量需求、队列数量规模**。

## 基础对比

| 维度 | RabbitMQ | RocketMQ | Kafka |
|------|----------|----------|-------|
| 开发语言 | Erlang | Java | Scala & Java |
| 协议 | AMQP等多种 | 自定义 | 自定义 |
| 单机吞吐 | ~1万TPS | ~10万TPS | ~10万TPS |
| 消息延迟 | 微秒级 | 毫秒级 | 毫秒级 |
| 消息可靠性 | 高 | 高 | 一般 |
| 单机队列数 | 少 | 最高5万 | 超过64分区性能严重下降 |
| 开源社区 | 活跃 | 国内活跃 | 全球最活跃 |

## 详细对比

### 性能
- **Kafka**：高吞吐著称，擅长大规模消息流处理。单Partition吞吐可达10万+TPS
- **RocketMQ**：同样10万TPS级别，大规模数据处理场景表现稳定
- **RabbitMQ**：约1万TPS，高并发大吞吐场景可能遇到瓶颈 ^[inferred]

### 功能特性
- **RocketMQ**：事务消息、顺序消息、广播消息、延迟消息、死信队列——最丰富的业务功能集
- **Kafka**：分区/副本/多副本机制保证高可用，批量处理+压缩提高传输效率
- **RabbitMQ**：多种交换机类型（直连/主题/扇出），灵活路由+丰富插件生态

### 可靠性
- **RocketMQ**：分布式架构+多副本+持久化+故障转移，节点故障时快速恢复
- **Kafka**：多副本+分布式存储保证容错，但acks=0/1时可能丢消息 ^[inferred]
- **RabbitMQ**：持久化+镜像队列，但大规模集群维护可靠性复杂度较高 ^[inferred]

### 队列数/分区数
- **RocketMQ**：单机支持最高5万队列，性能稳定——这是阿里自研的核心动机之一
- **Kafka**：单机超过64个分区/队列，消息发送性能严重下降（京东曾深度改造） ^[ambiguous]
- **RabbitMQ**：大型业务场景很少使用

### 运维
- **RocketMQ**：可视化控制台，运维相对简单
- **Kafka**：集群部署运维复杂，需要分布式系统专业知识
- **RabbitMQ**：管理界面完善，但集群扩展和调优需要经验

## 为什么阿里自研RocketMQ？

1. **Kafka定位于日志传输**：对复杂业务（如交易）支持不够，数据可靠性要求满足不了阿里交易场景
2. **数据可靠性/实时性/队列数**：阿里业务对这三个维度要求极高，Kafka针对海量数据但正确度要求不严格
3. **技术栈**：Kafka用Scala开发，阿里是Java系——维护成本问题
4. **自研能力**：阿里在团队/成本/资源投入方面约束几乎为零 ^[inferred]

## 选型建议

| 场景 | 推荐 | 原因 |
|------|------|------|
| 消息**高**可靠 + 队列数庞大 | RocketMQ | 事务消息+5万队列稳定支持 |
| 消息**低**可靠 + 队列数较少 | Kafka | 高吞吐+成熟生态 |
| 中小企业一般需求 + 灵活路由 | RabbitMQ | 低延迟+丰富插件+AMQP协议 |
| 大数据管道/日志聚合 | Kafka | 专门为此设计 |
| 金融交易/电商订单 | RocketMQ | 事务消息+顺序消息+高可靠 |
| 异步任务/消息通知 | RabbitMQ | 灵活路由+低延迟 |

## 来源

- 三大MQ选型对比-博客园（raw/sources/消息队列/）