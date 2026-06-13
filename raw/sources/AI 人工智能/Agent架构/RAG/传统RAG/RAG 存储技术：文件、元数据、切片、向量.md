原文： https://mp.weixin.qq.com/s?__biz=MzYyNTI3MTg2NQ==&mid=2247484481&idx=1&sn=0ebcf850b63e2927dddb59aa3372c691&chksm=f02bf117c75c7801e9a74c26892f24fbf6a2e82544c504305bd33d9452a1ff16e7772bf6999a&cur_album_id=4277987273339404300&scene=190#rd

检索增强生成（RAG）技术已成为解决大语言模型（LLM）知识滞后、数据幻觉问题的关键技术方案，其核心逻辑是将 LLM 的生成过程锚定到企业私有可信知识库上，通过检索外部权威文档作为生成上下文，将模型的固有记忆限制转化为可修复、可溯源、数据主权明确的外部知识增强能力。从数据流转的视角看，一套完整的 RAG 应用数据生命周期可分为四个相互衔接的关键阶段：

- **原始文件存储**：上传的未经处理的各类源文件
    
- **元数据存储**：描述原始文件的属性信息，如文件作者、发布时间、保密级别等
    
- **切片存储**：为适配 LLM 输入长度，切割生成的文件文本片段
    
- **向量存储**：切片经 Embedding 模型转化而成的高维向量，用于相似度检索
    

单看数据关联逻，四层数据的绑定关系是通过全局唯一 ID 实现的：原始文件的 ID 会作为外键关联到元数据记录；切片记录会同时携带原始文件 ID 和自身切片 ID；向量记录则以切片 ID 作为唯一主键，由此形成完整的、可双向回溯的链路。

从技术选型上，RAG 应用全阶段的存储方案分云存储与私有化存储两条路线。云存储的核心优势是弹性扩容、低运维成本和全球分发能力；私有化存储则以数据安全、合规与可控性见长。就技术栈演进来看，两条路线方案分化不大：主流存储产品大多同时支持云和私有化部署，部分还可实现两类环境间的无缝迁移。

本篇我们将基于数据存储的技术特性差异，将上述四个阶段划归为三层存储架构，这也是当前工业界生产级 RAG 系统的主流设计方案，各层的核心存储对象与技术定位如下表所示：

|**存储层级**|**核心存储对象**|**技术定位**|
|---|---|---|
|内容存储层|原始文件、切片数据|存储非结构化内容的原始形态或处理后的中间形态，保障数据的可溯源、可重处理|
|管理与元数据层|文件元数据|提供结构化的数据关联能力与检索过滤依据|
|向量检索层|向量数据|支撑高效的语义相似度检索，是 RAG 区别于传统关键词检索的核心|

## 原始文件存储技术选型

原始文件是RAG系统的数据源起点，其完整性、读取性能和持久化能力是后续切片、向量化、检索等所有环节的前提。一旦原始文件丢失或损坏，整个数据管道将失去可信基础。

该阶段的存储需求明确：一是高持久性，确保数据不丢失；二是支持高并发读取，以应对数据更新和重处理（如重新切片）时的频繁访问；三是兼容多格式存储，覆盖PDF、Word、Excel、PPT、Markdown、HTML等常见非结构化文档。

需要强调的是，原始文件的存储性能对RAG上层检索并无直接影响，正常检索流程不直接读取原始文件。存储层对原始文件的支持，本质上是对数据管道容错机制的保障：一旦切片或向量数据因误删或业务逻辑变更（如调整切片token大小）而失效，系统可基于原始文件快速重处理，恢复检索数据。

![图片](https://mmbiz.qpic.cn/mmbiz_png/ViaQXLHAMb3LM0y1VEu8ic58v6Z9w6m8kyn7YmnauA5bYvRSkAbEJtblYr0nrQfribxeGicaQtLxPowYOQaE3bcTLuliavvFYXrZR0KzxY2JQaqw/640?wx_fmt=png&from=appmsg&watermark=1&tp=webp&wxfrom=5&wx_lazy=1#imgIndex=0)

这个阶段要解决的是海量非结构化数据的落地问题。过去很多企业喜欢用HDFS存大数据，但技术趋势已经变了。现在云原生、Kubernetes和微服务这么火，计算和存储分离已是行业共识。HDFS把计算和数据强行绑在一起，处理海量小文件时效率极低，扩展起来也极其痛苦。

现在大家都在转向对象存储和新型分布式文件系统。对象存储的好处是，把数据打包成一个个带唯一标识符的对象，在扁平命名空间里管理。这种设计让它具备了极其恐怖的横向扩展能力。

## 轻量级云原生对象存储：MinIO

![图片](https://mmbiz.qpic.cn/mmbiz_png/ViaQXLHAMb3LboKZ03ia6uicbcTIh8hOT1URg6P1TYsUdqfPjkpQga44f5ib63YVdS8ZMlaOatd5m8hjIHY49iaVNf85j5xTV8LnLGN19JHCBicSs/640?wx_fmt=png&from=appmsg&watermark=1&tp=webp&wxfrom=5&wx_lazy=1#imgIndex=1)

- Github: https://github.com/minio/minio
    
- 开发文档：https://docs.min.io/aistor/reference/cli/#quickstart
    
- 官网：https://min.io/docs/
    

如果要在公司内部自建对象存储，工程师脑子里蹦出的第一个词多半是MinIO。MinIO 是用 Go 语言写的高性能、分布式、云原生对象存储系统。

**优点：**

- 完全兼容 AWS S3 API，迁移无痛
    
- 采用极简的去中心化设计，无需专门的元数据服务器
    
- 数据高可用全靠纠删码技术，相比传统三副本方案，硬盘利用率高
    
- 高性能，吞吐量狂暴。八核NVMe环境下能跑出读取2.8 GB/s、写入2.1 GB/s的狂暴吞吐量
    

**缺点：**

- 硬件排布要求苛刻，部署标准 MinIO 存储池，通常要4到16块硬盘，节点之间硬件规格尽量保持一致
    
- 对服务器资源胃口不小，方建议每个节点至少4个以上CPU核心、4到32GB内存。
    

## 大而全的统一存储平台：Ceph (RGW)

![图片](https://mmbiz.qpic.cn/sz_mmbiz_png/ViaQXLHAMb3Kg2QjalWm9KdiaGLuIHmn037xJuEhViaMPcmiaMM8OWNWrELL1Dqq9sIgNOlESuLJzfvNfq0GkzvkCmXlDFxqUdU36QibDe7n2Nsk/640?wx_fmt=png&from=appmsg&watermark=1&tp=webp&wxfrom=5&wx_lazy=1#imgIndex=2)

- Github: https://github.com/ceph/ceph
    
- 官网：https://ceph.io/
    

如果说MinIO是轻骑兵，那Ceph绝对是存储界的航空母舰。运维一套Ceph集群简直就是新手的噩梦，如果没有专门的资深存储工程师团队，千万别碰它。

Ceph是开源的软件定义存储平台，野心非常大，想在一个集群里同时搞定对象存储、块存储和文件系统。

**优点：**

- 统一存储平台，对象、块、文件一把梭
    
- 极度灵活的数据分布控制：通过Crush Map算法，可以精细控制每份数据到底存在哪个机房、哪个机架、甚至哪块特定磁盘上
    
- 支持异地多活和冷热数据分层
    

**缺点：**

- 架构复杂，运维门槛极高，上面组件密密麻麻：管理磁盘的OSD守护进程、维护集群状态的Monitor节点、监控指标的Manager进程
    
- 极度吃内存，资源开销大，一个OSD进程通常要吃掉8到16GB内存
    
- 小文件处理延迟偏高，大概在6.3毫秒左右
    

## 海量小文件的救星：SeaweedFS

![图片](https://mmbiz.qpic.cn/mmbiz_png/ViaQXLHAMb3L2O0QDMSf8umqOqzXaMiaDibx0sDTRViabriaV80GwLibKh89dExWfYq0BxWm5j8gjnqfYSDXA48gd3vD7WuG0LOmicWiaHkKNibiaQicmI/640?wx_fmt=png&from=appmsg&watermark=1&tp=webp&wxfrom=5&wx_lazy=1#imgIndex=3)

- Github: https://github.com/seaweedfs/seaweedfs
    
- 官网：https://seaweedfs.com/
    

SeaweedFS 专为海量小文件而生，适合几百万、上千万个几十KB的文本或图片。它的设计灵感来自 Facebook 的 Haystack 论文 「https://research.facebook.com/publications/finding-a-needle-in-haystack-facebooks-photo-storage/」。核心思想把元数据和数据存储彻底分开。主节点只管理卷的映射关系，不关心具体文件。真正的文件和元数据都紧凑地塞在卷服务器里。

**优点：**

- 海量小文件下读写快、延迟低
    
- 元数据压力小，主节点不存文件信息
    
- 内存占用低，适合大并发场景
    
- 支持冷数据自动推到云端 S3
    
- 集成了 Iceberg REST Catalog，能直接对接数据湖分析引擎
    

**缺点：**

- 大文件（几百MB以上）性能不如 Ceph 或 MinIO
    
- 社区和生态不如 Ceph 成熟，企业级工具少
    
- 单卷有大小上限（默认 30GB），需提前规划
    
- 部署和运维比 MinIO 复杂
    

## 废旧硬件与边缘计算的黑马：Garage

![图片](https://mmbiz.qpic.cn/mmbiz_png/ViaQXLHAMb3LlspHMJqParOzdwUMu6GgWxSqcGUcqWNafib2Q0zFrvbSWKo8SOD5vwGHtc65PpuYBJK4VgJcspuuqhTcJicRD5BHmobCuzTxB4/640?wx_fmt=png&from=appmsg&watermark=1&tp=webp&wxfrom=5&wx_lazy=1#imgIndex=4)

- Github: https://github.com/deuxfleurs-org/garage
    
- 开发文档：https://garagehq.deuxfleurs.fr/documentation/quick-start/
    
- 官网：https://garagehq.deuxfleurs.fr/
    

Garage 适合预算很低的团队。不需要买昂贵的企业级 NVMe 服务器，用配置参差不齐的旧机器或便宜的 VPS 也能跑。它用 Rust 语言编写，主打轻量、安全、容错强。设计思路来自亚马逊 Dynamo「https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf」论文和 CRDT 研究。不做复杂的纠删码，而是简单做 3 副本复制，配合一致性哈希来分布数据。

**优点：**

- 运维门槛极低，硬件要求低，旧机器、VPS 都能用
    
- 内存占用小，单节点只要 1 到 2 GB 内存，适合资源紧张的环境
    
- 容错能力强，能承受高延迟和跨机房部署
    
- 部署简单，支持 K8s 一键安装
    

**缺点：**

- 3 副本方式浪费存储空间，不如纠删码省容量
    
- 性能一般，不如 Ceph 或 SeaweedFS
    
- 生态和社区较小，企业级功能少
    
- 暂不支持全托管的 S3 兼容界面，需自行对接
    

## AI计算的高性能缓存网关：JuiceFS

![图片](https://mmbiz.qpic.cn/sz_mmbiz_png/ViaQXLHAMb3KjR16Dl8ew4BAPhNWNtH5JhFsTzteWSEtUW1iaYPAbOfibTcKQYY3lohXMOMCHMcJPCJJnjrrhCpfNArvNLUbSbV6dRuqMVia4icU/640?wx_fmt=png&from=appmsg&watermark=1&tp=webp&wxfrom=5&wx_lazy=1#imgIndex=5)

- Github: https://github.com/juicedata/juicefs
    
- 开发文档：https://juicefs.com/docs/zh/csi/introduction/
    
- 官网：https://juicefs.com/
    

JuiceFS 让算法工程师不用改代码，就能把对象存储当成本地硬盘来用。它提供标准的 POSIX 接口，数据存在便宜的 S3 等对象存储里，目录树等元数据存在 Redis 或 TiKV 这类高性能 KV 数据库里。

它在 AI 圈很火。数据和元数据分离，既有对象存储的低成本、无限容量，又通过本地多级缓存，实现了接近本地 SSD 的读写速度。很适合跑模型训练或 RAG 数据清洗，能让 GPU 充分利用起来，不用等数据加载。

**优点：**

- 像本地硬盘一样用，代码无需改造
    
- 数据放对象存储，成本低、容量几乎无限
    
- 多级缓存加速，读性能接近本地 SSD
    
- 元数据单独存 KV 数据库，操作快
    

**缺点：**

- 依赖外部 KV 存储（如 Redis、TiKV），多一个组件要维护
    
- 首次读冷数据时，延迟比纯本地盘高
    
- 写小文件频繁时，元数据压力较大
    
- 多机同时写同一文件时，一致性开销偏大
    

|**原始文件存储方案**|**架构流派与核心设计**|**最适用的业务场景**|**硬件资源占用与运维门槛**|
|---|---|---|---|
|**AWS S3 / 阿里云OSS**|公有云全托管对象存储|资金充足、不愿碰底层运维的通用业务|资源零占用，运维门槛极低|
|**MinIO**|去中心化对象存储，严格纠删码|追求极致吞吐量，服务器规格统一的私有云|中高内存占用，扩缩容略显死板，中等门槛|
|**Ceph (RGW)**|统一存储平台，组件繁杂，极度灵活|超大型数据中心，需要精细化控制数据分布|极度吃内存，需要资深专家，门槛极高|
|**SeaweedFS**|主从解耦，O(1)寻址，集成数据湖|应对海量小文件，极低延迟要求，冷热分层|轻量内存，部署简便，门槛较低|
|**Garage**|Rust编写，3副本一致性哈希，抗高延迟|边缘节点，二手废旧服务器利旧，预算极低|极微小内存占用，跨机房部署极易，门槛极低|
|**JuiceFS**|POSIX兼容，元数据与数据物理分离|AI模型训练，需要将对象存储挂载为本地目录|依赖外部Redis/TiKV，架构稍显冗余，门槛中等|

## 元数据（Metadata）存储技术选型

文件元数据是描述原始文件属性的结构化数据，是连接原始文件、切片数据与向量数据的核心枢纽。它与原始文件为「一对一」关系，与切片及向量数据为「一对多」关系，通过文件ID或切片ID实现绑定。在检索中，元数据是重要的过滤与溯源依据，用户可通过精准的元数据过滤先排除不符合业务属性的文档，再进入向量相似度检索，从而大幅提升检索性能和结果精准度。

RAG场景下的元数据主要分三类：

- **基础属性**：原始文件名、文件大小、格式、存储唯一标识（如对象存储URI）、生成/修改时间、上传人、部门、业务标签等
    
- **处理属性**：解析状态、最终切片大小、切片版本、向量化进度、关联切片ID、关联向量索引ID等
    
- **权限属性**：可访问用户组、用户ID集合、部门权限集合，以及检索时需应用的权限控制规则
    

该阶段的存储需求与原始文件层有本质差异：

- 支持高并发下的快速查询与精准更新，因元数据检索是RAG检索的前置过滤器
    
- 具备强一致性事务能力，确保增删改时元数据与原始文件、切片、向量数据的关联关系不出现异常
    
- 支持随数据量增长的水平扩展能力
    
- 兼容企业现有生态的标准查询接口（如SQL）及必要的检索索引（如倒排索引、组合索引）
    
- 具备完善的备份恢复与数据安全加密能力
    

![图片](https://mmbiz.qpic.cn/sz_mmbiz_png/ViaQXLHAMb3IC6EIUxGlqz0nPBAtgEPC73aNIojyNg0X2Dvy3QtwM2tJDRZUMjmlkak9Fdf5gJPeGUdOC3GamuqBWGiaAoWoTOkzTgGYGwIEM/640?wx_fmt=png&from=appmsg&watermark=1&tp=webp&wxfrom=5&wx_lazy=1#imgIndex=6)

## 关系型老大哥：PostgreSQL

如果公司知识库的元数据结构很固定，比如只有 ID、标题、创建时间、作者、密级这几个字段，用 PostgreSQL 就足够了。它成熟、稳定、事务强一致。PostgreSQL 15+版本对 JSON 支持也很好，偶尔存点非结构化数据也没问题。而且，如果后面要用 pgvector 做向量检索，把元数据和向量放在同一个库，用一条 SQL 就能查，对开发者非常方便。

## 灵活的文档型数据库：MongoDB

- 官网： https://www.mongodb.com/
    
- 博客：https://www.puppygraph.com/blog/mongodb-vs-neo4j
    

真实业务经常变化。今天加「点赞数」，明天加「数据留存周期」。关系型数据库频繁改表结构很麻烦。这时，MongoDB 这种文档型数据库更合适。

MongoDB 用 BSON 格式存数据（类似 JSON）。不管多深的嵌套、多复杂的结构，都不用提前定义 Schema。在 RAG 应用里，适合存长文档切分后的上下文信息。它的聚合框架和索引机制很强大，按元数据查文档也很快。

## 复杂推理的利器：图数据库 Neo4j

- 官网：https://neo4j.com/
    

上面两种数据库在处理单一属性查询没啥问题，但，查询里包含多层关系，比如：「既给现代汽车供货、又在2025年报过供应链违约风险的欧洲企业，相关应急预案有哪些？」这种问题有三四层关联，传统数据库用 JOIN 会卡死。

Neo4j 可以很好地解决上述问题。它天生为处理关系而生，采用免索引邻接架构：节点在物理层面上直接相连。遍历关系的速度只取决于局部子图的大小，和总数据量无关。

在 Graph RAG 中，可以把文档切片挂在公司、城市、高管等实体节点下。系统把用户问题翻译成 Cypher 查询，按公司、国家、情感等条件沿图路径遍历，让 RAG 的逻辑推理能力大大提升。

如果不想把数据搬到 Neo4j，也可以用 PuppyGraph。它在 MongoDB 上直接跑图查询，不用 ETL，避免数据搬家。

## 极速的内存缓存：Redis

- 官网：https://redis.io/
    
- 博客：https://redis.io/blog/hybrid-search-benefits-rag-systems/
    

高并发的 RAG 系统里，不能每次检索都查磁盘数据库。Redis 是内存数据库的王者，常用来存用户会话、高频元数据和做全局限流。它的读写速度在亚毫秒级。Redis Stack 还支持混合检索，在轻量级、对延迟要求极高的场景下，地位不可替代。

## 切片（Chunk）存储技术选型

切片数据是原始文件经解析、切分后得到的文本片段，是连接原始文件与向量数据的核心枢纽，也是RAG检索中命中的最小单元。其存在的核心逻辑是适配LLM输入上下文窗口的token长度限制：以text-embedding-v4模型为例，单次输入上限为2048 token，超长文档直接向量化会被截断，破坏语义完整性；切分成小片段后，每个片段token长度控制在模型上限内，从而保障向量检索精度。

切片数据存储的内容并非单纯文本，而是一个三元组：切片唯一ID、切片文本内容、对应部分元数据（如原始文档来源、页码、章节信息等）。

该阶段存储技术选型与原始文件层高度类似，但有两处细节差异：

- 切片数据的读取频率远高于原始文件，向量检索命中后，需立即读取对应切片文本，作为注入LLM的上下文；
    
- 部分RAG场景需支持基于切片元数据的过滤，如仅检索某书特定章节或某产品特定版本文档。
    

## 混合检索的无冕之王：Elasticsearch / OpenSearch

- Github1: https://github.com/elastic/elasticsearch
    
- 官网1：https://www.elastic.co/elasticsearch
    
- Github2: https://github.com/opensearch-project/OpenSearch
    
- 官网2：https://docs.opensearch.org/latest/about/
    

纯向量检索能理解语义，但像近视眼。搜具体报错代码或偏门人名时，容易失败，因为它重整体含义、轻字面匹配。所以现在RAG领域都使用混合检索（Hybrid Search）。

混合检索就是让两套引擎同时干活。一边用向量引擎去找意思相近的，另一边用传统的BM25算法去找包含特定关键词的。最后，用一种叫RRF（倒数排名融合，Reciprocal Rank Fusion）的算法，把两边的排名结果综合一下，这种做法能大幅度兜底大模型的检索质量。

## 向量（Vector）存储技术选型

向量数据是切片数据经Embedding模型转化后的高维数组，是RAG架构中最特殊的一层存储：无法被人类直接理解，也无法用传统关系型数据库进行精准匹配或范围扫描。支撑其高效近似近邻检索能力，是RAG系统性能优化的核心技术点。

RAG的实际检索流程分三步联合完成：

- **元数据过滤**：基于用户过滤条件（如某部门文档），从元数据层筛选出符合条件的文档集合
    
- **向量检索**：将用户检索词通过同一Embedding模型转化为向量，在过滤后的集合内进行相似度计算，找出最接近的向量结果
    
- **溯源**：根据命中向量关联的切片ID，读取切片原文及原始文件URI，作为上下文注入LLM生成答案
    

该阶段存储技术需求最为专业，是四层数据中技术门槛最高的一层：

- 必须支持高并发、低延迟的近似最近邻检索，千万级以上向量规模下响应时间需控制在毫秒级
    
- 支持高维向量的高效存储与索引，维度通常在数百至数千维
    
- 具备与元数据层、切片层的高关联查询能力，需先元数据过滤再向量相似度比对
    
- 集群架构支持水平扩展，应对数据量与并发增长
    
- 最好具备混合检索能力，同时支持向量相似度检索与传统关键词检索，可通过加权或RRF算法进行结果融合
    

![图片](data:image/svg+xml,%3C%3Fxml%20version='1.0'%20encoding='UTF-8'%3F%3E%3Csvg%20width='1px'%20height='1px'%20viewBox='0%200%201%201'%20version='1.1'%20xmlns='http://www.w3.org/2000/svg'%20xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg%20stroke='none'%20stroke-width='1'%20fill='none'%20fill-rule='evenodd'%20fill-opacity='0'%3E%3Cg%20transform='translate\(-249.000000,%20-126.000000\)'%20fill='%23FFFFFF'%3E%3Crect%20x='249'%20y='126'%20width='1'%20height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

现在的向量数据库市场竞争激烈，按架构流派可以分为几类。

## 零运维的云原生 SaaS：Pinecone 与 Turbopuffer

如果团队有预算但缺专业运维，就别自建了，直接上云托管。

- **Pinecone**：最知名的闭源商业向量数据库。采用存算分离架构，不用自己调 HNSW 参数、操心内存或扩容。适合平时没流量、偶尔爆发的业务，表现很稳定。缺点是贵，高并发场景一个月几千美金是常事。标准版只能建 20 个索引，虽然支持 10 万个命名空间，但灵活性还是有限。
    
- **Turbopuffer**：后起之秀，很特别。它完全架在 S3 这种廉价对象存储上，是 Serverless 的。最适合有成千上万小租户的 SaaS 产品，因为不限制命名空间数量，且隔离性好。最低每月 64 美金，就能处理海量读写请求。
    

## 公有云基础设施：AWS S3 Vectors 与 Cloudflare Vectorize

很多人不想为了 RAG 单独买一个数据库。云大厂直接在现有基础设施里加入向量能力。

- AWS S3 Vectors：亚马逊的新产品。既然原始文件就在 S3，为何不直接在 S3 里做向量检索？它提供专门的向量桶，用简单 API 把向量传进去，底层扩容全由 AWS 负责。跟 Bedrock、SageMaker 打通。按次计费、零服务器管理、亚秒级检索，成本优势很大。
    
- Cloudflare Vectorize：适合边缘 AI 计算，尤其是跑在 Cloudflare Workers 上。它支持 5 万个索引，配合 D1 和 R2 使用，能在离用户最近的边缘节点返回 RAG 结果。缺点是不支持混合检索，单索引最多 500 万向量。
    

## 十亿级海量数据的开源霸主：Milvus / Zilliz

当向量数据突破一亿，甚至到十亿、百亿级别，轻量级数据库会崩溃。这时是 Milvus 的主场。

- **开源版 Milvus**：专为超大云原生环境设计。架构极度解耦，能无限扩展，还支持 GPU 加速。但自己搭非常折磨人，内部依赖一堆中间件，分布式组件一挂就很难排查，运维成本极高。
    

- Github: https://milvus.io/
    
- 官网： https://github.com/milvus-io/milvus
    

- **托管版 Zilliz Cloud**：想用 Milvus 又不想脱发，就花钱买托管版。内置专有的 Cardinal 引擎，检索速度比开源版快 10 倍。
    

## 预算友好与混合检索先锋：Qdrant 与 Weaviate

如果数据量在 5000 万以内，又坚持开源，这两个用 Rust 和 Go 写的明星项目值得关注。

- **Qdrant**：预算有限的团队最爱。天生支持混合检索（向量 + BM25 + 元数据）。Qdrant Cloud 提供 1GB 永久免费额度。在 5000 万数据量、99% 召回率下，QPS 能到 41，非常稳健。
    
- **Weaviate**：把混合检索做到极致。自带图属性，对细粒度的元数据过滤有原生支持，适合需要复杂条件筛选的 RAG 系统。
    
- **Vespa**（雅虎开源）：功能大而全，适合复杂实时计算和机器学习重排序。
    
- **FAISS**（Meta 开源）：极致批处理索引速度，性能天花板，适合纯极客玩家。
    

## 传统数据库的最强外挂：pgvector 与 pgvectorscale

在 2026 年，务实潮流是不建新数据库。如果你们已经把 PostgreSQL 玩得出神入化，何必再引入不熟悉的专用向量库？

- **pgvector**：C 语言写的 PG 向量扩展。数据量小于几千万时用起来很顺手，可以用一条 SQL 在同一事务里查出业务数据和向量。但超过 5000 万后，延迟和吞吐量会急剧恶化。
    
- **pgvectorscale**：Timescale 开源的神器，用 Rust 和 pgrx 框架写的。采用受微软 DiskANN 启发的索引结构。在 5000 万向量、99% 召回率下，它跑出 471 QPS，比 Qdrant 快 11.4 倍。配合 pgai 库，可以用外挂的 vectorizer worker 异步处理大模型嵌入，不会拖垮数据库主进程。这套组合拳，几乎成了中型 RAG 项目的终极首选。
    

- Github: https://github.com/timescale/pgvectorscale
    

## 原型开发与边缘独立的轻量级利器：ChromaDB 与 Turso

- **ChromaDB**：适合快速做 MVP。就是个 Python 或 JS 包，像 NumPy 一样好用，完全嵌在代码里，不用起服务端。2025 年用 Rust 重写后快 4 倍，但官方承认不适合大规模生产环境。
    
- **LanceDB**：基于列式存储的嵌入式向量库，支持零拷贝访问。很适合本地环境或数据科学家的 Jupyter Notebook。
    
- **Turso** (sqlite-vec)：如果不想用 Pinecone 的命名空间隔离，Turso 提供了一个思路：给每个租户建一个完全物理隔离的 SQLite 节点，放在边缘网络上。一租户一库，彻底杜绝数据泄露风险。不能做全局搜索，但在合规场景下是降维打击。
    

|**向量存储技术**|**底层架构与语言**|**性能与规模上限**|**核心优势**|**适用场景**|
|---|---|---|---|---|
|**Pinecone**|专有闭源托管|亿级以上|彻底免运维，自动扩缩容，计费灵活|资金充裕、无运维团队的企业，流量波动的SaaS|
|**AWS S3 Vectors**|依托对象存储|无缝无限扩展|极低成本，零服务器配置，原生打通Bedrock|已经重度绑定AWS生态的Serverless RAG应用|
|**Milvus / Zilliz**|云原生分布式组件|十亿、百亿级极限并发|吞吐量天花板，支持GPU，解耦极其彻底|海量数据场景，拥有资深基础设施运维团队|
|**pgvectorscale**|PostgreSQL Rust扩展|5000万~1亿级|DiskANN索引性能逆天，同事务混查关系数据|熟练使用PG的团队，力求系统架构精简降本|
|**Qdrant**|Rust专用开源|5000万以内较优|原生混合检索能力强，Cloud版免费层极其慷慨|预算有限但需要强悍混合检索的初创中型团队|
|**Weaviate**|Go专用开源|亿级左右|原生融合BM25与元数据深度过滤，图属性加持|高度依赖元数据复杂条件过滤的精准RAG|
|**ChromaDB**|嵌入式内存/磁盘|1000万以内|零环境配置，开发者API极度友好，极速上手|前期概念验证（PoC）、本地MVP产品原型开发|

## 云端与本地：公有云与私有化部署的综合碰撞

盘点完四个阶段的存储选项，最后看整体部署架构：公有云还是私有化，RAG 场景下优缺点都很明显。

**团队人手不足、核心竞争力在业务逻辑**: 选公有云。

把原始文件放 S3，元数据和切片用云上 RDS PostgreSQL，向量交给 Pinecone 或 S3 Vectors。弹性扩缩容、自动备份、双活全由云厂商搞定。流量爆了也能瞬间扩容。代价是贵，向量突破几亿条后账单会让你头疼。

**数据极其敏感（医疗、金融）**: 选私有化。

用 MinIO 或 Garage 搭本地对象存储，MongoDB 存切片，大内存机器跑 Qdrant 或 Milvus 集群。数据绝对安全，十亿级别下硬件成本比公有云划算。但运维很痛苦：参数配错、硬盘坏了、网络堵死，全得自己扛。

RAG 存储选型不是非黑即白，而是权衡召回率、延迟、成本和运维复杂度。不要盲目追跑分，看清团队能力和数据规模，选择契合当前业务的组合，并留出平滑迁移的余地，这才是最大的智慧。