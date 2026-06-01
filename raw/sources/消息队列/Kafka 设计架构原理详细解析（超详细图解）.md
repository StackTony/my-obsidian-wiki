### 什么是Kafka？

Apache Kafka是一个开放源代码的[分布式事件流平台](https://zhida.zhihu.com/search?content_id=237424599&content_type=Article&match_order=1&q=%E5%88%86%E5%B8%83%E5%BC%8F%E4%BA%8B%E4%BB%B6%E6%B5%81%E5%B9%B3%E5%8F%B0&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODAxMDU0MzUsInEiOiLliIbluIPlvI_kuovku7bmtYHlubPlj7AiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyMzc0MjQ1OTksImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.dfO0U6YLB-yI1EkdvJo1zoS8_kUspaGCKmPUJsHjylo&zhida_source=entity)，成千上万的公司使用它来实现高性能数据管道，流分析，数据集成和关键任务等相关的应用程序。

### Kafka的应用场景

1. **构造实时流数据管道**，它可以在系统或应用之间可靠地获取数据 (相当于message queue)，特别是在集群情况下，多个服务器需要建立交流
2. **构建实时流式应用程序**，对这些流数据进行转换或者影响。 (就是[流处理](https://zhida.zhihu.com/search?content_id=237424599&content_type=Article&match_order=1&q=%E6%B5%81%E5%A4%84%E7%90%86&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODAxMDU0MzUsInEiOiLmtYHlpITnkIYiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyMzc0MjQ1OTksImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.CZqoGIoaGpjGDmGbAiuwOmCO-4o8rOkZvBG0zg7IvXY&zhida_source=entity)，通过kafka stream topic和topic之间内部进行变化)

### Kafka架构设计

![](https://picx.zhimg.com/v2-8df6c8df51282394ec7b16f70769cae5_1440w.jpg)

**[Producer](https://zhida.zhihu.com/search?content_id=237424599&content_type=Article&match_order=1&q=Producer&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODAxMDU0MzUsInEiOiJQcm9kdWNlciIsInpoaWRhX3NvdXJjZSI6ImVudGl0eSIsImNvbnRlbnRfaWQiOjIzNzQyNDU5OSwiY29udGVudF90eXBlIjoiQXJ0aWNsZSIsIm1hdGNoX29yZGVyIjoxLCJ6ZF90b2tlbiI6bnVsbH0.AizhiTY64kwfke42PimxqwYYNQ7EnyWtBuhJO-IIYas&zhida_source=entity)**：生产者可以将数据发布到所选择的topic（主题）中。生成者负责将记录分配到topic的哪一个分区（partition）中，这里可以使用对多个partition循环发送来实现多个server负载均衡

**[Broker](https://zhida.zhihu.com/search?content_id=237424599&content_type=Article&match_order=1&q=Broker&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODAxMDU0MzUsInEiOiJCcm9rZXIiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyMzc0MjQ1OTksImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.vfcrgs1hV5LnVM6WQKI2Ovz7zPYHOBstaZ-LoM7KAr8&zhida_source=entity)**：日志的分区（partition）分布在Kafka集群的服务器上。每个服务器处理数据和请求时，共享这些分区。每一个分区都会在以配置的服务器上进行备份，确保容错性。

其中，每个分区都有一台server作为leader，零台或堕胎server作为follows。leader server处理一切对分区的读写请求，而follwers只需被动的同步leader上的数据。当leader宕机了，followers中的一台server会自动成为新的eader，每台server都会成为某些分区的leader和某些分区的follower，因此集群的负载是均衡的

**[Consumer](https://zhida.zhihu.com/search?content_id=237424599&content_type=Article&match_order=1&q=Consumer&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODAxMDU0MzUsInEiOiJDb25zdW1lciIsInpoaWRhX3NvdXJjZSI6ImVudGl0eSIsImNvbnRlbnRfaWQiOjIzNzQyNDU5OSwiY29udGVudF90eXBlIjoiQXJ0aWNsZSIsIm1hdGNoX29yZGVyIjoxLCJ6ZF90b2tlbiI6bnVsbH0.cPjbvgXfzxcGgoO7vB3RaCDm9uwKzSQ7agxco4D-1bo&zhida_source=entity)**：消费者使用一个group（消费组）名称来表示，发布到topic中的每条记录将被分配到订阅消费组中的其中一个消费者示例。消费者实例可以分布在多个进程中或多个机器上

这里有两个注意的地方：

1. 如果所有的消费者实例在同一个消费组中，消息记录会负载均衡到消费组中的每一个消费者实例
2. 如果所有的消费者实例在不同的消费组中，则会将每条消息记录广播到所有的消费组或消费者进程中

![](https://picx.zhimg.com/v2-456aff0867014c1422efb3aba5deaa67_1440w.jpg)

如图中所示，这个Kafka集群中有两台server，四个分区（p0-p3）和两个消费组。这时分区中的消息记录会广播到所有的消费者组中

### Kafka 生产者架构

![](https://picx.zhimg.com/v2-9d624e2899460d6f6936e8bde6a14471_1440w.jpg)

基本流程：

1. 主线程Producer中会经过拦截器、序列化器、分区器，然后将处理好的消息发送到消息累加器中
2. 消息累加器每个分区会对应一个队列，在收到消息后，将消息放到队列中
3. 使用`ProducerBatch`批量的进行消息发送到Sender线程处理（这里为了提高发送效率，减少带宽），ProducerBatch中就是我们需要发送的消息，其中消息累加器中可以使用`Buffer.memory`配置，默认为32MB
4. Sender线程会从队列的队头部开始读取消息，然后创建request后会经过会被缓存，然后提交到`Selector`，Selector发送消息到Kafka集群
5. 对于一些还没收到Kafka集群ack响应的消息，会将未响应接收消息的请求进行缓存，当收到Kafka集群ack响应后，会将request请求**在缓存中清除并同时移除消息累加器中的消息**

### Kafka 消费者架构

![](https://pica.zhimg.com/v2-0479d15d24b5ef51adebc88c586ae8b6_1440w.jpg)

基本流程：

**[Consumer Group](https://zhida.zhihu.com/search?content_id=237424599&content_type=Article&match_order=1&q=Consumer+Group&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODAxMDU0MzUsInEiOiJDb25zdW1lciBHcm91cCIsInpoaWRhX3NvdXJjZSI6ImVudGl0eSIsImNvbnRlbnRfaWQiOjIzNzQyNDU5OSwiY29udGVudF90eXBlIjoiQXJ0aWNsZSIsIm1hdGNoX29yZGVyIjoxLCJ6ZF90b2tlbiI6bnVsbH0.K01gT_q0BN5ohLpvpyEe5uTrMgoo8mGT71sq3sS1YCc&zhida_source=entity)**中的Consumer向各自注册的分区上进行消费消息

**Consumer**消费消息后会将当前标注的消费位移信息以消息的方式提交到[位移主题](https://zhida.zhihu.com/search?content_id=237424599&content_type=Article&match_order=1&q=%E4%BD%8D%E7%A7%BB%E4%B8%BB%E9%A2%98&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODAxMDU0MzUsInEiOiLkvY3np7vkuLvpopgiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyMzc0MjQ1OTksImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.YTK1Y5lpVY0QYFn5xJzHaWvEUaiJeuubEArbEkEuXmY&zhida_source=entity)中记录，一个Consumer Group中多个Consumer会做负载均衡，如果一个Consumer宕机，会自动切换到组内别的Consumer进行消费

关键的点：

**Consumer Group**：组内多个的Consumer可以公用一个Consumer Id，组内所有的Consumer只能注册到一个分区上去消费，一个Consumer Group只能到一个Topic上去消费

**位移主题**：

> 位移主题的主要作用是保存Kafka消费者的位移信息

**Kafka老版本之前:**

在Kafka老版本之前处理方式是自动或手动地将位移数据提交到[Zookeeper](https://zhida.zhihu.com/search?content_id=237424599&content_type=Article&match_order=1&q=Zookeeper&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODAxMDU0MzUsInEiOiJab29rZWVwZXIiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyMzc0MjQ1OTksImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.tP7Y6tG7aPePQ-mMzb6u7JcDtt64pkEBScvBS4apWsI&zhida_source=entity)进行保存，Consumer重启后，自动从Zookeeper中读取消费位移信息，从而在上次的offset地方继续消费

**优点：** Kafka Broker中不需要保存位移数据，减少了Broker端需要持有的状态信息，有利于动态扩展  
**缺点：** 每一个Consumer消费后需要发送位移信息到Zookeeper，而Zooker不适用于这种高频的写操作

**Kafka最新版本中位移主题的处理方式：**

Consumer的位移信息offset会当作一条条普通消息提交到位移主题（_consumer_offsets）中。

### Kafka 文件存储架构

![](https://pic4.zhimg.com/v2-1bc6d5df737373fb1d3cde674c2b1c2d_1440w.jpg)

window文件系统中的文件列表：

![](https://pic2.zhimg.com/v2-7c344cdd32b7e6e4606ba0b0c9a9b69b_1440w.jpg)

这里比较好理解：

1. 一个Topic分别存储在不同的partition中
2. 一个partitioin对应着多个replica备份
3. 一个relica对应着一个Log
4. 一个Log对应多个LogSegment
5. 而在LogSegment中存储着log文件、索引文件、其它文件

### Kafka 如何保证数据有序性？

> 一些场景需要保证多个消息的消费顺序，比如订单，但在kafka中一个消息可能被发到多个partition中多个线程处理，被多个消费者消费，无法保证消息的消费顺序

**解决方案**：将需要顺序消费的消息发送的时候设置将某个topic发送到指定的partition（也可以根据key的hash与分区进行运算），则在partition中的消息也是有序的，消费的时候将一组同hash的key放到同一个queue中保证同一个消费者下的同一个线程对此queue进行消费。

**总结**：一个producer->一个partition->一个queue->一个comsumer->一个线程  
当对于需要顺序消费的消息数量大的时候，无法保证吞吐量

### Kafka 如何保证数据可靠性？

**[AR](https://zhida.zhihu.com/search?content_id=237424599&content_type=Article&match_order=1&q=AR&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODAxMDU0MzUsInEiOiJBUiIsInpoaWRhX3NvdXJjZSI6ImVudGl0eSIsImNvbnRlbnRfaWQiOjIzNzQyNDU5OSwiY29udGVudF90eXBlIjoiQXJ0aWNsZSIsIm1hdGNoX29yZGVyIjoxLCJ6ZF90b2tlbiI6bnVsbH0.d1CQI8QbVW9uPp4wYMBBDY130vTP7QUkwikxog6qGas&zhida_source=entity)（Assigned Replicas）**：分区中的所有副本统称为AR。所有消息会先发送到leader副本，然后follower副本才能从leader中拉取消息进行同步。但是在同步期间，follower对于leader而言会有一定程度的滞后，这个时候follower和leader并非完全同步状态

**[OSR](https://zhida.zhihu.com/search?content_id=237424599&content_type=Article&match_order=1&q=OSR&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODAxMDU0MzUsInEiOiJPU1IiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyMzc0MjQ1OTksImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.BWXOiJyPk8HPcrs2o3PdFZuG75ix6Q97s3KT7z-xBwc&zhida_source=entity)（Out Sync Replicas）**：follower副本与leader副本没有完全同步或滞后的副本集合

[ISR](https://zhida.zhihu.com/search?content_id=237424599&content_type=Article&match_order=1&q=ISR&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODAxMDU0MzUsInEiOiJJU1IiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyMzc0MjQ1OTksImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.dL9yNti0PgvyGPioJwZEAkKnkWDbp5ES3PYIyRHWCw0&zhida_source=entity)（In Sync Replicas）：AR中的一个子集，ISR中的副本都**是与leader保持完全同步的副本**，如果某个在ISR中的follower副本落后于leader副本太多，则会被从ISR中移除，否则如果完全同步，会从OSR中移至ISR集合。

在默认情况下，当leader副本发生故障时，只有在ISR集合中的follower副本才有资格被选举为新leader，而OSR中的副本没有机会（可以通过`unclean.leader.election.enable`进行配置）

**[HW](https://zhida.zhihu.com/search?content_id=237424599&content_type=Article&match_order=1&q=HW&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODAxMDU0MzUsInEiOiJIVyIsInpoaWRhX3NvdXJjZSI6ImVudGl0eSIsImNvbnRlbnRfaWQiOjIzNzQyNDU5OSwiY29udGVudF90eXBlIjoiQXJ0aWNsZSIsIm1hdGNoX29yZGVyIjoxLCJ6ZF90b2tlbiI6bnVsbH0.kDKYYN1GOdsh4fHlLYdvHnZSLJVkVqbaLeofmIRN77w&zhida_source=entity)（High Watermark）**：高水位，它标识了一个特定的消息偏移量（offset），消费者只能拉取到这个水位 offset 之前的消息

**[LEO](https://zhida.zhihu.com/search?content_id=237424599&content_type=Article&match_order=1&q=LEO&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODAxMDU0MzUsInEiOiJMRU8iLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyMzc0MjQ1OTksImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.EuXLbnGMVAchrWBAGcdezot6Ft3yrmKPa1EtRqXqXSg&zhida_source=entity)（Log End Offset）**：标识当前日志文件中下一条待写入的消息的offset。在ISR集合中的每个副本都会维护自身的LEO，且HW==LEO。

![](https://pica.zhimg.com/v2-8126647051ca465e184a018106a254ce_1440w.jpg)

图中，HW就是8，Consumer只能拉去0~7的消息，LEO就是15，代表消息还没有同步到follower

下面通过一个例子来说明下ISR、HW、LEO之间的关系：

![](https://pic3.zhimg.com/v2-6374fb3af871a2fdd6caae9062a95e28_1440w.jpg)

假设由一个leader副本，它有两个follower副本，这时候producer向leader写入3、4两条消息，我们来观察下他们是如何同步的

![](https://pic2.zhimg.com/v2-973f9b307fec6ebd5dcecca63f0b9281_1440w.jpg)

这个时候写入两条消息到leader，这个时候LEO变为5，然后follower开始同步leader数据

![](https://pic4.zhimg.com/v2-05aee0ece240f447d3e5a6773bf7596f_1440w.jpg)

由于网络或其它原因，follower2同步效率较低，还没有完成同步，这个时候HW的offset为4，在此offset之前的消息Consumer都可见

![](https://picx.zhimg.com/v2-b3ce92bffdd551e51cf0054f1871728b_1440w.jpg)

在一定的延迟后，follower2也完成了队leader副本的同步，这时HW为5，LEO为5，且两个follower副本都在ISR集合中，在leader或follower宕机后，会在ISR集合的副本中选举一个来当新的leader副本

**HW高水位的弊端：**

1. 高水位更新需要一轮额外的拉取请求
2. leader和follower之间同步会有时间差，可能导致数据不一致或数据丢失  
    接下来通过一个例子来进行详细说明`消息1`消息丢失的过程（min.insync.replicas=1）：

![](https://pic4.zhimg.com/v2-afc4a1bb65fdfc5c17f022cac23e30c1_1440w.jpg)

![](https://pic1.zhimg.com/v2-54bc61d6842b60436eba49b9a48403bc_1440w.jpg)

![](https://pic2.zhimg.com/v2-9b601e7915899126f63cbbc7e8392f77_1440w.jpg)

![](https://pic2.zhimg.com/v2-a7d1870224443d22a14b10a7ad4048f1_1440w.jpg)

**对于消息不一致的情况：**

![](https://pic4.zhimg.com/v2-6b375de5679bff9b93fcf049e8a0843f_1440w.jpg)

![](https://pic3.zhimg.com/v2-60f94a10599f07c6fab8f75cc505f89a_1440w.jpg)

![](https://pica.zhimg.com/v2-a12e9c93418b9d92493d16ebc15df9e4_1440w.jpg)

就是**leader、follower同时宕机**，然后由follower先恢复且写入消息1，HW=1，leader恢复启之后发现HW相等，则不进行同步，但实际上他们的**消息1不是同一个消息**，导致消息不一致

在kafka 0.11.0.0版本中引入Leader Epoch来解决使用高水位导致的数据丢失和数据不一致的问题

所谓leader epoch实际上是一对值：（epoch,offset），epoch标识leader的版本号，从0开始，每变更一次leader，epoch+1；而offset对应于该epoch版本的leader写入第一条消息（成为leader后的首条消息）的位移

（0，0）、（1，120）表示第一个leader从位移0开始写入消息，共写了120条，第二个leader版本号为1，从位移120处开始写入消息

规避数据丢失：

![](https://pic3.zhimg.com/v2-2a6732add270bc931f6b821d84041a7a_1440w.jpg)

规避数据不一致：

![](https://pic4.zhimg.com/v2-818a8a0cc4cfb724a3d765585851f491_1440w.jpg)

### **Kafka 高性能探究**

Kafka 高性能的核心是保障系统低延迟、高吞吐地处理消息，为此，Kafaka 采用了许多精妙的设计：

- [异步发送](https://zhida.zhihu.com/search?content_id=237424599&content_type=Article&match_order=1&q=%E5%BC%82%E6%AD%A5%E5%8F%91%E9%80%81&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODAxMDU0MzUsInEiOiLlvILmraXlj5HpgIEiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyMzc0MjQ1OTksImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.Q4VEGKvLdEz8ALiCSaDVBsak8fyzdPxv1hjEXdQEAd4&zhida_source=entity)
- [批量发送](https://zhida.zhihu.com/search?content_id=237424599&content_type=Article&match_order=1&q=%E6%89%B9%E9%87%8F%E5%8F%91%E9%80%81&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODAxMDU0MzUsInEiOiLmibnph4_lj5HpgIEiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyMzc0MjQ1OTksImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.zN994GvWMuH7hrJmjLGqlHg4rYpCf5NK8wPp8sU-R60&zhida_source=entity)
- [压缩技术](https://zhida.zhihu.com/search?content_id=237424599&content_type=Article&match_order=1&q=%E5%8E%8B%E7%BC%A9%E6%8A%80%E6%9C%AF&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODAxMDU0MzUsInEiOiLljovnvKnmioDmnK8iLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyMzc0MjQ1OTksImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.yvYsuF_5JLjD_w7YwqqtNNyvR8sHe4Lrqqs7lOwG3hQ&zhida_source=entity)
- Pagecache 机制&顺序追加落盘
- [零拷贝](https://zhida.zhihu.com/search?content_id=237424599&content_type=Article&match_order=1&q=%E9%9B%B6%E6%8B%B7%E8%B4%9D&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3ODAxMDU0MzUsInEiOiLpm7bmi7fotJ0iLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyMzc0MjQ1OTksImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.vF14W9sjQxxrhrspGzn-i3kl0ixzFcHPIbRySj_ILBM&zhida_source=entity)
- 稀疏索引
- broker & 数据分区
- 多 reactor 多线程网络模型

### **异步发送**

如上文所述，Kafka 提供了异步和同步两种消息发送方式。在异步发送中，整个流程都是异步的。调用异步发送方法后，消息会被写入 channel，然后立即返回成功。Dispatcher 协程会从 channel 轮询消息，将其发送到 Broker，同时会有另一个异步协程负责处理 Broker 返回的结果。同步发送本质上也是异步的，但是在处理结果时，同步发送通过 waitGroup 将异步操作转换为同步。使用异步发送可以最大化提高消息发送的吞吐能力。

### **批量发送**

Kafka 支持批量发送消息，将多个消息打包成一个批次进行发送，从而减少网络传输的开销，提高网络传输的效率和吞吐量。Kafka 的批量发送消息是通过以下两个参数来控制的：

1. batch.size：控制批量发送消息的大小，默认值为 16KB，可适当增加 batch.size 参数值提升吞吐。但是，需要注意的是，**如果批量发送的大小设置得过大，可能会导致消息发送的延迟增加，因此需要根据实际情况进行调整**。
2. **linger.ms**：控制消息在批量发送前的等待时间，默认值为 0。当 linger.ms 大于 0 时，如果有消息发送，Kafka 会等待指定的时间，如果等待时间到达或者批量大小达到 batch.size，就会将消息打包成一个批次进行发送。可适当增加 linger.ms 参数值提升吞吐，比如 10 ～ 100。

在 Kafka 的生产者客户端中，当发送消息时，如果启用了批量发送，Kafka 会将消息缓存到缓冲区中。当缓冲区中的消息大小达到 batch.size 或者等待时间到达 linger.ms 时，Kafka 会将缓冲区中的消息打包成一个批次进行发送。如果在等待时间内没有达到 batch.size，Kafka 也会将缓冲区中的消息发送出去，从而避免消息积压。

### **压缩技术**

Kafka 支持压缩技术，通过将消息进行压缩后再进行传输，从而减少网络传输的开销(压缩和解压缩的过程会消耗一定的 CPU 资源，因此需要根据实际情况进行调整。)，提高网络传输的效率和吞吐量。Kafka 支持多种压缩算法，在 Kafka2.1.0 版本之前，仅支持 GZIP，Snappy 和 LZ4，2.1.0 后还支持 Zstandard 算法（Facebook 开源，能够提供超高压缩比）。这些压缩算法性能对比（两指标都是越高越好）如下：

- 吞吐量：LZ4>Snappy>zstd 和 GZIP，压缩比：zstd>LZ4>GZIP>Snappy。

在 Kafka 中，压缩技术是通过以下两个参数来控制的：

1. compression.type：控制压缩算法的类型，默认值为 none，表示不进行压缩。
2. compression.level：控制压缩的级别，取值范围为 0-9，默认值为-1。当值为-1 时，表示使用默认的压缩级别。

在 Kafka 的生产者客户端中，当发送消息时，如果启用了压缩技术，Kafka 会将消息进行压缩后再进行传输。在消费者客户端中，如果消息进行了压缩，Kafka 会在消费消息时将其解压缩。注意：Broker 如果设置了和生产者不通的压缩算法，接收消息后会解压后重新压缩保存。Broker 如果存在消息版本兼容也会触发解压后再压缩。

### **Pagecache 机制&顺序追加落盘**

kafka 为了提升系统吞吐、降低时延，Broker 接收到消息后只是将数据写入**PageCache**后便认为消息已写入成功，而 PageCache 中的数据通过 linux 的 flusher 程序进行异步刷盘（避免了同步刷盘的巨大系统开销），将数据**顺序追加写**到磁盘日志文件中。由于 pagecache 是在内存中进行缓存，因此读写速度非常快，可以大大提高读写效率。顺序追加写充分利用顺序 I/O 写操作，避免了缓慢的随机 I/O 操作，可有效提升 Kafka 吞吐。

![](https://pica.zhimg.com/v2-661431145d91f6b833f3ddf83e4642be_1440w.jpg)

如上图所示，消息被顺序追加到每个分区日志文件的尾部。

### **零拷贝**

Kafka 中存在大量的网络数据持久化到磁盘（Producer 到 Broker）和磁盘文件通过网络发送（Broker 到 Consumer）的过程，这一过程的性能直接影响 Kafka 的整体吞吐量。传统的 IO 操作存在多次数据拷贝和上下文切换，性能比较低。Kafka 利用零拷贝技术提升上述过程性能，其中网络数据持久化磁盘主要用 mmap 技术，网络数据传输环节主要使用 sendfile 技术。

### **索引加速之 mmap**

传统模式下，数据从网络传输到文件需要 4 次数据拷贝、4 次上下文切换和两次系统调用。如下图所示：

![](https://pic2.zhimg.com/v2-c457f1be65791b9224130bd51de09ba7_1440w.jpg)

为了减少上下文切换以及数据拷贝带来的性能开销，Kafka使用mmap来处理其索引文件。Kafka中的索引文件用于在提取日志文件中的消息时进行高效查找。这些索引文件被维护为内存映射文件，这允许Kafka快速访问和搜索内存中的索引，从而加速在日志文件中定位消息的过程。mmap 将内核中读缓冲区（read buffer）的地址与用户空间的缓冲区（user buffer）进行映射，从而实现内核缓冲区与应用程序内存的共享，省去了将数据从内核读缓冲区（read buffer）拷贝到用户缓冲区（user buffer）的过程，整个拷贝过程会发生 4 次上下文切换，1 次CPU 拷贝和 2次 DMA 拷贝。

![](https://pic3.zhimg.com/v2-a111a7c49e6d71dabe239bf827a4d1b6_1440w.jpg)

### **网络数据传输之 sendfile**

传统方式实现：先读取磁盘、再用 socket 发送，实际也是进过四次 copy。如下图所示：

![](https://pic3.zhimg.com/v2-671a437a3eb9a81e0a5849f5e0c19bf8_1440w.jpg)

为了减少上下文切换以及数据拷贝带来的性能开销，Kafka 在 Consumer 从 Broker 读数据过程中使用了 sendfile 技术。具体在这里采用的方案是通过 NIO 的 `transferTo/transferFrom` 调用操作系统的 sendfile 实现零拷贝。总共发生 2 次内核数据拷贝、2 次上下文切换和一次系统调用，消除了 CPU 数据拷贝，如下：

![](https://pic1.zhimg.com/v2-95fdd5a238abf5b5887e3c3e2d157e46_1440w.jpg)

### **稀疏索引**

为了方便对日志进行检索和过期清理，kafka 日志文件除了有用于存储日志的.log 文件，还有一个**位移索引文件.index**和一个**时间戳索引文件.timeindex 文件**，并且三文件的名字完全相同，如下：

![](https://pic3.zhimg.com/v2-b2dbf258a375aec31457db97ae1777e0_1440w.jpg)

Kafka 的索引文件是按照稀疏索引的思想进行设计的。**稀疏索引的核心是不会为每个记录都保存索引，而是写入一定的记录之后才会增加一个索引值**，具体这个间隔有多大则通过 log.index.interval.bytes 参数进行控制，默认大小为 4 KB，意味着 Kafka 至少写入 4KB 消息数据之后，才会在索引文件中增加一个索引项。可见，单条消息大小会影响 Kakfa 索引的插入频率，因此 log.index.interval.bytes 也是 Kafka 调优一个重要参数值。由于索引文件也是按照消息的顺序性进行增加索引项的，因此 Kafka 可以利用二分查找算法来搜索目标索引项，把时间复杂度降到了 O(lgN)，大大减少了查找的时间。

**位移索引文件.index**

位移索引文件的索引项结构如下：

![](https://pic3.zhimg.com/v2-e93050a2646d7a5391fabf15a37a5ef6_1440w.jpg)

**相对位移**：保存于索引文件名字上面的起始位移的差值，假设一个索引文件为：00000000000000000100.index，那么起始位移值即 100，当存储位移为 150 的消息索引时，在索引文件中的相对位移则为 150 - 100 = 50，这么做的好处是使用 4 字节保存位移即可，可**以节省非常多的磁盘空间**。

**文件物理位置**：消息在 log 文件中保存的位置，也就是说 Kafka 可根据消息位移，通过位移索引文件快速找到消息在 log 文件中的物理位置，有了该物理位置的值，我们就可以快速地从 log 文件中找到对应的消息了。下面我用图来表示 Kafka 是如何快速检索消息：

![](https://pic2.zhimg.com/v2-60cee1ce461ff1a7d210e9cf8bc6c1f9_1440w.jpg)

假设 Kafka 需要找出位移为 3550 的消息，那么 Kafka 首先会使用二分查找算法找到小于 3550 的最大索引项：[3528, 2310272]，得到索引项之后，Kafka 会根据该索引项的文件物理位置在 log 文件中从位置 2310272 开始顺序查找，直至找到位移为 3550 的消息记录为止。

**时间戳索引文件.timeindex**

Kafka 在 0.10.0.0 以后的版本当中，消息中增加了时间戳信息，为了满足用户需要根据时间戳查询消息记录，Kafka 增加了时间戳索引文件，时间戳索引文件的索引项结构如下：

![](https://pic2.zhimg.com/v2-3ab33f85a570e71e81e37090a44a69db_1440w.jpg)

时间戳索引文件的检索与位移索引文件类似，如下快速检索消息示意图：

![](https://pic2.zhimg.com/v2-98e1fdbc40206d02f48fc8ed96fa280b_1440w.jpg)

### **broker & 数据分区**

Kafka 集群包含多个 broker。一个 topic 下通常有多个 partition，partition 分布在不同的 Broker 上，用于存储 topic 的消息，这使 Kafka 可以在多台机器上处理、存储消息，给 kafka 提供给了并行的消息处理能力和横向扩容能力。

### **多 reactor 多线程网络模型**

多 Reactor 多线程网络模型 是一种高效的网络通信模型，可以充分利用多核 CPU 的性能，提高系统的吞吐量和响应速度。Kafka 为了提升系统的吞吐，在 Broker 端处理消息时采用了该模型，示意如下：

![](https://picx.zhimg.com/v2-b745fe0f6e380c3eb49e5d5c74664b05_1440w.jpg)

**SocketServer**和**KafkaRequestHandlerPool**是其中最重要的两个组件：

- SocketServer：实现 Reactor 模式，用于处理多个 Client（包括客户端和其他 broker 节点）的并发请求，并将处理结果返回给 Client
- KafkaRequestHandlerPool：Reactor 模式中的 Worker 线程池，里面定义了多个工作线程，用于处理实际的 I/O 请求逻辑。

**整个服务端处理请求的流程大致分为以下几个步骤：**

1. Acceptor 接收客户端发来的请求
2. 轮询分发给 Processor 线程处理
3. Processor 将请求封装成 Request 对象，放到 RequestQueue 队列
4. KafkaRequestHandlerPool 分配工作线程，处理 RequestQueue 中的请求
5. KafkaRequestHandler 线程处理完请求后，将响应 Response 返回给 Processor 线程
6. Processor 线程将响应返回给客户端

参考：[Kafka 高可靠高性能原理探究](https://link.zhihu.com/?target=https%3A//mp.weixin.qq.com/s/_g11mmmQse6KrkUE8x4abQ)