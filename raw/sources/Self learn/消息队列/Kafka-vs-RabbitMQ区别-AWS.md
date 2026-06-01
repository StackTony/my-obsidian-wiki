---
title: Kafka与RabbitMQ区别对比
credibility: low
created: 2026-05-26
---

## Kafka 和 RabbitMQ 之间有何区别？

[创建 AWS 账户](https://portal.aws.amazon.com/gp/aws/developer/registration/index.html)

## 页面主题

## Kafka 和 RabbitMQ 之间有何区别？

Kafka 和 RabbitMQ 是可用于流处理的消息队列系统。数据流是需要高速处理的大容量、连续增量数据。例如，您必须持续收集和处理有关环境的传感器数据，以观察温度或气压的实时变化。RabbitMQ 是一个分布式消息代理，从多个来源收集流式处理数据，然后将其路由到不同的目标进行处理。Apache Kafka 是一个流式处理平台，用于构建实时数据管道和流式处理应用程序。Kafka 提供了一个高度可扩展、容错和持久的消息收发系统，其功能比 RabbitMQ 更多。

[了解流式处理数据 »](https://aws.amazon.com/cn/what-is/streaming-data/)

[了解 Apache Kafka »](https://aws.amazon.com/msk/what-is-kafka/)

## 架构差异：Kafka 与RabbitMQ

RabbitMQ 和 Apache Kafka 均允许生产者向使用者发送消息。 *生产者* 是发布信息的应用程序，而 *消费者* 是订阅和处理信息的应用程序。

在 RabbitMQ 和 Kafka 中，生产者和使用者的互动方式有所不同。在 RabbitMQ 中，生产者发送并监控消息是否到达目标使用者。另一方面，无论使用者是否检索消息，Kafka 生产者都会向队列发布消息。

可以将 RabbitMQ 视为接收邮件并将其传输给预定收件人的邮局。与此同时，Kafka 类似于图书馆，它在书架上整理生产者发布的不同类型消息。然后，使用者读取相应书架上的消息，并记住他们所读取的内容。

### RabbitMQ 架构方法

RabbitMQ 代理允许使用以下组件进行低延迟和复杂的消息分配：

- *交易所* 接收来自生产者的消息并决定应将它们路由到哪里
- *队列* 是从交易所接收消息并将其发送给消费者的存储空间
- *绑* 定是连接交易所和经纪商的路径

在 RabbitMQ 中， *路由密钥* 是一种消息属性，用于将消息从交换路由到特定队列。当生产者向交换机发送消息时，它会将路由密钥作为消息的一部分包含在内。然后，交换机使用此路由密钥来确定消息应传输到哪个队列。

### Kafka 架构方法

Kafka 集群通过更复杂的架构提供高吞吐量流事件处理。以下是 Kafka 的一些关键组件：

- *Kafka 代理* 是一个 Kafka 服务器，允许生产者将数据流式传输给消费者。 Kafka 代理包含主题及其相应的分区。
- *主题* 是在 Kafka 代理中对相似数据进行分组的数据存储。
- *分区* 是消费者订阅的主题中较小的数据存储空间。
- ZooKeeper 是特殊的软件，用于管理 Kafka 集群和分区以提供容错流式处理。ZooKeeper 最近被 Apache Kafka Raft（KRaft）协议所取代。

Kafka 中的生产者为每条消息分配一个消息密钥。然后，Kafka 代理将消息存储在该特定主题的前导分区中。KRaft 协议使用共识算法来确定前导分区。

## Kafka 和 RabbitMQ 如何以不同的方式处理消息？

RabbitMQ 和 Apache Kafka 以不同的方式将数据从生产者转移到使用者。RabbitMQ 是通用消息代理，它优先考虑端到端消息传输。Kafka 是分布式事件流式处理平台，支持持续大数据的实时交换。

RabbitMQ 和 Kafka 针对不同的使用案例而设计，因此它们处理消息的方式有所不同。 接下来，我们讨论一些具体的差异。

### 消息使用

在 RabbitMQ 中，代理确保使用者收到消息。使用者应用程序扮演被动角色，等待 RabbitMQ 代理将消息推送到队列中。例如，银行应用程序可能会等待来自中央交易处理软件的短信提醒。

然而，Kafka 使用者更积极地读取和跟踪信息。当消息加入实体日志文件时，Kafka 使用者会跟踪他们读取的最后一条消息，并相应地更新偏移跟踪器。偏移跟踪器是读取消息后递增的计数器。使用 Kafka，生产者并不知道使用者会检索消息。

### 消息优先级

RabbitMQ 代理允许生产者软件使用优先队列升级某些消息。代理不是按 *先入先出顺序发送消息，而是先* 处理优先级更高的消息，然后再处理普通消息。例如，零售应用程序可能每小时将销售交易排队一次。但是，如果系统管理员发出优先的备份数据库消息，则代理会立即发送该消息。

与 RabbitMQ 不同，Apache Kafka 不支持优先级队列。将所有消息分配到各自的分区时，该代理平等对待这些消息。

### 消息排序

RabbitMQ 按特定顺序发送消息和对其进行排队。除非有更高优先级的消息排入系统，否则使用者会按照消息的发送顺序接收消息。

同时，Kafka 使用主题和分区对消息进行排队。当生产者发送消息时，消息会进入特定的主题和分区。由于 Kafka 不支持直接的生产者与使用者交换，因此使用者以不同的顺序从分区中拉取消息。

### 消息删除

RabbitMQ 代理将消息路由到目标队列。读取后，使用者向代理发送确认（ACK）回复，然后代理将消息从队列中删除。

与 RabbitMQ 不同，Apache Kafka 将消息附加到日志文件中，该日志文件将一直留存到其保留期到期。这样，使用者可以在规定的时间内随时重新处理流式传输的数据。

## 其他主要区别：Kafka 与RabbitMQ

RabbitMQ 通过简单的架构提供复杂的消息路由，而 Kafka 提供耐用的消息代理系统，可让应用程序处理流历史记录中的数据。

接下来，我们分享两个消息代理之间的更多差异。

### 性能

RabbitMQ 和 Kafka 都为其预期使用案例提供高性能的消息传输。但是，在消息传输容量方面，Kafka 的表现优于 RabbitMQ。

Kafka 每秒可以发送数百万条消息，因为它使用顺序磁盘 I/O 来实现高吞吐量消息交换。顺序磁盘 I/O 是一种存储系统，用于存储和访问来自相邻内存空间的数据，比随机磁盘访问更快速。

RabbitMQ 还可以每秒发送数百万条消息，但它需要多个代理才能达成此目标。通常，RabbitMQ 的性能为平均每秒处理数千条消息，如果 RabbitMQ 的队列拥挤，则处理可能会变慢。

### 安全性

RabbitMQ 和 Kafka 允许应用程序安全地交换消息，但使用不同的技术。

RabbitMQ 附带管理工具，用于管理用户权限和代理安全。

同时，Apache Kafka 架构通过 TLS 和 Java 身份验证与授权服务（JAAS）提供安全的事件流。TLS 是一种加密技术，可防止消息被意外窃听，而 JAAS 控制哪个应用程序可以访问代理系统。

### 编程语言和协议

Kafka 和 RabbitMQ 都支持开发人员熟悉的各种语言、框架和协议。

在为 Kafka 和 RabbitMQ 构建客户端应用程序时，可以使用 Java 和 Ruby 编写代码。此外，Kafka 支持 Python 和 Node.js，而 RabbitMQ 支持 JavaScript、Go、C、Swift、Spring、Elixir、PHP 和.NET。

Kafka 在 TCP 上使用二进制协议跨实时数据管道传输消息，而 RabbitMQ 默认支持高级消息队列协议（AMQP）。RabbitMQ 还支持诸如简单文本导向消息收发协议（STOMP）和 MQTT 之类的旧式协议来路由消息。

[了解 MQTT »](https://aws.amazon.com/cn/what-is/mqtt/)

## Kafka 和 RabbitMQ 有什么相似之处？

应用程序需要可靠的消息代理来在云端交换数据。RabbitMQ 和 Kafka 均提供可扩展的容错平台，以满足不断增长的流量需求和高可用性。

接下来，我们将讨论 RabbitMQ 和 Kafka 之间的一些关键相似之处。

### 可扩展性

RabbitMQ 可以横向和纵向扩展其消息处理容量。可以向 RabbitMQ 的服务器分配更多计算资源，以提高消息交换效率。在某些情况下，开发人员使用一种名为 *RabbitMQ 一致性哈希交换* 的消息分发技术来平衡多个代理之间的负载处理。

同样，Kafka 架构允许向特定主题添加更多分区，以均匀分配消息负载。

### 容错能力

Kafka 和 RabbitMQ 都是强大的消息队列架构，可抵御系统故障。

可以将多个 RabbitMQ 代理分组到集群中，并将它们部署在不同的服务器上。RabbitMQ 还可以在分布式节点之间复制队列中的消息。这样系统就可从影响任何服务器的故障中恢复。

与 RabbitMQ 一样，Apache Kafka 通过在不同的服务器上托管 Kafka 集群提供类似的可恢复性和冗余性。每个集群都由日志文件的副本组成，可以在出现故障时恢复这些副本。

### 易于使用

这两个消息队列系统都有强大的社区支持和库，可以轻松发送、读取和处理消息。这使得两个系统上的开发人员都更容易开发客户端应用程序。

例如，可以使用 Kafka Streams（客户端库）在 Kafka 上构建消息系统，而使用 Spring Cloud Data Flow 来借助 RabbitMQ 构建事件驱动的微服务。

## 何时使用 Kafka 与RabbitMQ

务必了解的是，RabbitMQ 和 Kafka 不是相互竞争的消息代理。两者都旨在支持不同使用案例中的数据交换，分别有其适用场景。

接下来，我们将讨论考虑采用 RabbitMQ 和 Kafka 的一些使用案例。

### 事件流重放

Kafka 适用于需要重新分析所接收数据的应用程序。可以在保留期内多次处理流式数据或收集日志文件进行分析。

使用 RabbitMQ 进行日志聚合更具挑战性，因为消息一旦使用就会被删除。解决方法是重放来自生产者的已存储消息。

### 实时数据流式处理

Kafka 以非常低的延迟流式传输消息，适用于实时分析流式数据。例如，可以将 Kafka 用作分布式监控服务，为在线事务处理实时发出提醒。

### 复杂的路由架构

RabbitMQ 为要求模糊或路由场景复杂的客户端提供灵活性。例如，可以将 RabbitMQ 设置为将数据路由到具有不同绑定和交换机的不同应用程序。

### 有效的消息传输

RabbitMQ 采用推送模型，这意味着生产者知悉客户端应用程序是否使用消息。该方法适用于在交换和分析数据时必须遵守特定顺序和传输保证的应用程序。

### 语言和协议支持

开发人员将 RabbitMQ 用于需要向后兼容诸如 MQTT 和 STOMP 等旧式协议的客户端应用程序。与 Kafka 相比，RabbitMQ 还支持更广泛的编程语言。

## Kafka 会使用 RabbitMQ 吗？

Kafka 不使用 RabbitMQ。它是独立的消息代理，无需使用 RabbitMQ 即可分配实时事件流。两者都是独立的数据交换系统，彼此独立运行。

但是，一些开发人员将来自 RabbitMQ 网络的消息路由到 Kafka。他们这样做的因为是解构现有的 RabbitMQ 数据管道并使用 Kafka 重建它们需要付出更多的努力。

## 差异摘要：Kafka 与RabbitMQ

|  | RabbitMQ | Kafka |
| --- | --- | --- |
| 架构 | RabbitMQ 的架构专为复杂的消息路由而设计。该代理使用推送模型。生产者使用不同的规则向使用者发送消息。 | Kafka 使用基于分区的设计进行实时、高吞吐量的流处理。该代理使用拉取模型。生产者向使用者订阅的主题和分区发布消息。 |
| 消息处理 | RabbitMQ 代理监控消息使用。此代理会在消息被使用后将其删除。它支持消息优先级。 | 使用者使用偏移跟踪器跟踪消息检索情况。Kafka 根据保留策略保留消息。其中没有消息优先级。 |
| 性能 | RabbitMQ 提供低延迟。它每秒发送数千条消息。 | Kafka 每秒可实时传输多达数百万条消息。 |
| 编程语言和协议 | RabbitMQ 支持多种语言和旧式协议。 | Kafka 的编程语言选择有限。该代理在 TCP 上使用二进制协议进行数据传输。 |

## AWS 如何支持 RabbitMQ 和 Kafka 要求？

Amazon Web Services（AWS）为 RabbitMQ 和 Kafka 实现提供低延迟和完全托管的消息代理服务：

- 使用 [亚马逊 MQ 预](https://aws.amazon.com/cn/amazon-mq/) 置您的 RabbitMQ 代理，无需耗时的设置。Amazon MQ 对传输中的和静态的 RabbitMQ 消息进行加密。我们还确保 AWS 可用区内的高可用性数据管道。
- 使用 [适用于 Apache Kafka 的 Amazon Managed Streaming（亚马逊 MSK）](https://aws.amazon.com/cn/msk/) 轻松设置、处理和扩展您的实时 Kafka 消息总线。亚马逊 MSK 帮助您使用亚马逊 [虚拟私有云 (亚马逊 V](https://aws.amazon.com/cn/vpc/) PC) 等 AWS 技术构建容错和安全的事件流。

立即 [创建账户，开始在 AWS 上使用](https://portal.aws.amazon.com/gp/aws/developer/registration/index.html) 消息代理。

## 使用 AWS 的后续步骤

## Browse all cloud computing concepts

Browse all cloud computing concepts content here:

正在加载

正在加载

正在加载

正在加载

正在加载

## Did you find what you were looking for today?

Let us know so we can improve the quality of the content on our pages