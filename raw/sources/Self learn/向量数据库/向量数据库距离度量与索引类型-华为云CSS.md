---
credibility: low
---

[查看PDF](https://support.huaweicloud.com/usermanual-css/%E4%BA%91%E6%90%9C%E7%B4%A2%E6%9C%8D%E5%8A%A1%E7%94%A8%E6%88%B7%E6%8C%87%E5%8D%97-pdf.pdf)

## 创建向量索引

向量索引通过在Mapping中定义向量维度、索引算法（如HNSW、IVF）及度量方式（如余弦距离、欧式距离），可以将海量特征数据构建为优化的拓扑结构。这不仅解决了大规模数据下的“维度灾难”问题，还通过“量化压缩”和“多层图导航”技术，在千万级甚至十亿级数据规模下，依然能提供兼顾高召回率与低延迟的搜索体验。

#### 索引算法类型介绍

如 [表1](#ZH-CN_TOPIC_0000002523711048__table2388155616495) 所示，CSS向量数据库支持多种主流的索引算法，可根据业务场景选择合适的算法类型。

| 索引算法类型 | 原理介绍 | 适用场景 | 支持的集群版本 |
| --- | --- | --- | --- |
| FLAT | 全量暴力计算。不构建索引结构，将目标向量依次与库中所有向量计算距离。  召回率100%（无损失），但计算量随数据量线性增长。 | **万级以下** 的小规模数据，或对召回精度有要求的业务场景。 | Elasticsearch：7.6.2、7.10.2  OpenSearch：1.3.6、2.19.0 |
| GRAPH | 内嵌深度优化的HNSW算法。通过多层拓扑图实现快速跳转检索。  检索速度极快，精度高，但内存消耗较大（需常驻内存）。 | **亿级以下** 规模的数据量。对响应时间（毫秒级）和精度要求均较高的业务场景。 | Elasticsearch：7.6.2、7.10.2  OpenSearch：1.3.6、2.19.0 |
| GRAPH\_PQ | HNSW与乘积量化结合的算法。将向量切分并编码，大幅降低存储开销。  压缩率极高，可达1/16甚至更高，精度随压缩率增加而下降，但内存消耗小。 | **十亿级** 规模的数据量。 | Elasticsearch：7.6.2、7.10.2  OpenSearch：1.3.6、2.19.0 |
| GRAPH\_SQ8 | HNSW与8位标量量化结合的算法。将32位浮点数压缩为8位整数。  压缩率为1/4，内存消耗降低，精度损失小。 | **十亿级** 规模的数据量。 | Elasticsearch：7.10.2  OpenSearch：2.19.0 |
| GRAPH\_SQ4 | HNSW与4位标量量化结合的算法。将32位浮点数压缩为4位整数。  压缩率为1/8，大幅节省内存，但召回率下降较多，计算效率比GRAPH\_SQ8高。 | **十亿级** 规模的数据量。 | Elasticsearch：7.10.2  OpenSearch：2.19.0 |
| IVF\_GRAPH | 倒排聚类与HNSW结合的算法。先将全量空间划分为多个聚类子空间（指由聚类中心点向量表示的子空间），检索时仅扫描相关的子空间。  极大提升检索效率，同时会带来微小的检索精度损失。 | 对写入性能要求较高，且能接受中心点预构建带来的运维复杂度。 | Elasticsearch：7.6.2、7.10.2  OpenSearch：1.3.6、2.19.0 |
| IVF\_GRAPH\_PQ | 倒排聚类、HNSW与乘积量化结合的算法。进一步通过编码压缩提升系统的容量、降低系统开销。 | 对写入性能要求较高，且能接受中心点预构建带来的运维复杂度。 | Elasticsearch：7.6.2、7.10.2  OpenSearch：1.3.6、2.19.0 |

![](https://support.huaweicloud.com/usermanual-css/public_sys-resources/caution_3.0-zh-cn.png)

当选择“IVF\_GRAPH”或“IVF\_GRAPH\_PQ”算法类型时，需要先 [（可选）预构建与注册中心点向量](#ZH-CN_TOPIC_0000002523711048__section1291152903010) 再创建向量索引。

#### 登录开发工具

进入Dev Tools执行DSL命令。

- **Elasticsearch集群登录Kibana**
	1. 登录 [云搜索服务管理控制台](https://console.huaweicloud.com/elasticsearch/) 。
		2. 在左侧导航栏，选择“集群管理 > Elasticsearch”。
		3. 在集群列表，选择目标集群，单击操作列的“Kibana”，登录Kibana。
		4. 在Kibana左侧导航栏选择“Dev Tools”，进入操作页面。
		控制台左侧是命令输入框，其右侧的三角形图标为执行按钮，右侧区域则显示执行结果。
- **OpenSearch集群登录Dashboards**
	1. 登录 [云搜索服务管理控制台](https://console.huaweicloud.com/elasticsearch/) 。
		2. 在左侧导航栏，选择“集群管理 > OpenSearch”。
		3. 在集群列表，选择目标集群，单击操作列的“Dashboards”，登录OpenSearch Dashboards。
		4. 在OpenSearch Dashboards左侧导航栏选择“Dev Tools”，进入操作页面。
		控制台左侧是命令输入框，其右侧的三角形图标为执行按钮，右侧区域则显示执行结果。

#### 创建向量索引

定义索引结构，指定向量字段的算法参数。

例如，创建一个名为“my\_index”的索引，该索引包含一个名为“my\_vector”的向量字段和一个名为“my\_label”的文本字段，其中，向量字段创建了GRAPH图索引，并使用欧式距离作为相似度度量。

```
PUT my_index 
{
  "settings": {
    "index": {
      "vector": true,
      "number_of_shards": 1,
      "number_of_replicas": 1
    }
  },
  "mappings": {
    "properties": {
      "my_vector": {
        "type": "vector",
        "dimension": 2,
        "indexing": true,
        "algorithm": "GRAPH",
        "metric": "euclidean"
      },
      "my_label": {
        "type": "keyword"
      }
    }
  }
}
```

| 参数 | 是否必选 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| index.vector | 是 | Boolean | 无 | 是否启用向量索引功能。  该参数值必须配置为“true”，否则无法创建向量索引。 |
| index.number\_of\_shards | 否 | Integer | 1 | 索引的分片数量，通常设置为节点数的整数倍。  取值范围：1~1024 |
| index.number\_of\_replicas | 否 | Integer | 1 | 索引的副本数量，副本用于数据冗余和提升高可用性。  取值范围：0~（节点数-1） |
| index.vector.exact\_search\_threshold | 否 | Integer | null（不切换） | 控制从前置过滤搜索自动切换到暴力搜索的阈值。当Segment中过滤后的中间结果集数量小于此值时，执行暴力搜索。  取值范围：null（不启用切换）或正整数。 |
| index.vector.search.concurrency.enabled | 否 | Boolean | false | 是否开启Segment间并发搜索。在Elasticsearch中，每个索引分片由多个Segment组成，执行查询时默认采用Segment间串行搜索机制。开启Segment间并发搜索，查询可在满足条件的Segment上并行执行，可降低查询时延，但并不会提升集群的最大查询吞吐量，同时集群的平均CPU使用率可能会升高。  约束限制：仅支持Elasticsearch集群，且要求镜像版本号不低于7.10.2\_25.3.0\_xxx。  取值范围： - true：并发搜索。 - false：串行搜索。 |

| 参数 | 是否必选 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| type | 是 | String | 无 | 字段类型，定义字段存储的数据类型。  该参数值必须配置为“vector”，不可更改，用于标识向量字段。 |
| dimension | 是 | Integer | 无 | 向量数据维度，指定向量数据的长度。  取值范围：1~4096 |
| indexing | 否 | Boolean | false | 是否开启向量索引加速。  取值范围： - true：开启向量索引加速，系统将创建额外的向量索引，索引算法由“algorithm”参数指定，写入数据后可以使用VectorQuery进行查询。 - false：关闭向量索引加速，向量数据仅写入docvalues，只支持使用ScriptScore以及Rescore进行向量查询。 |
| lazy\_indexing | 否 | Boolean | false | 是否开启向量索引的延迟构建模式。开启后，系统在数据写入阶段仅持久化向量数据，不会实时构建索引结构，待全量数据写入完成后再统一执行 [离线构建](https://support.huaweicloud.com/usermanual-css/css_01_0296.html#ZH-CN_TOPIC_0000002353678449__section164656265118) 。该模式旨在平衡写入吞吐量与索引构建开销。适用于海量数据离线导入、追求写入吞吐量且在导入期间无需进行实时检索的场景。  约束限制： - 必须在Mapping中设置“indexing”为“true”时，该参数配置才生效。 - Elasticsearch集群要求镜像版本号不低于7.10.2\_24.3.3\_xxx。 - OpenSearch集群要求集群版本号为2.19.0。  取值范围： - true：开启延迟构建。写入性能提升，但在手动触发离线构建完成前，该字段无法通过VectorQuery进行查询。 - false：实时构建。数据写入过程中同步构建索引，实现数据“写完即可查”。 |
| algorithm | 否 | String | GRAPH | 向量索引的算法类型。  约束限制： - 必须在Mapping中设置“indexing”为“true”时，该参数配置才生效。 - 选择“IVF\_GRAPH”或“IVF\_GRAPH\_PQ”时，必须先执行 [（可选）预构建与注册中心点向量](#ZH-CN_TOPIC_0000002523711048__section1291152903010) 再创建向量索引。  取值范围：FLAT、GRAPH、GRAPH\_PQ、GRAPH\_SQ8、GRAPH\_SQ4、IVF\_GRAPH、IVF\_GRAPH\_PQ  算法类型的选型指导和集群版本支持情况请参见 [索引算法类型介绍](#ZH-CN_TOPIC_0000002523711048__section10145155620319) 。  - 当选择GRAPH类算法（GRAPH、GRAPH\_PQ、GRAPH\_SQ8、GRAPH\_SQ4）时，可以参考 [表4](#ZH-CN_TOPIC_0000002523711048__table96225128514) 调整图索引的拓扑结构与构建质量。 - 当选择GRAPH\_PQ算法时，可以参考 [表5](#ZH-CN_TOPIC_0000002523711048__table119841865016) 控制乘积量化的精度。 |
| dim\_type | 否 | String | float | 向量维度值的类型，指定向量数据的数值类型。  取值范围： - binary：二值向量。 - float：浮点数向量。 |
| metric | 否 | String | euclidean | 向量距离度量方式。定义向量之间相似度或距离的计算方法。  取值范围：  - euclidean：欧式距离。 - inner\_product：内积距离。 - cosine：余弦距离。 - hamming：汉明距离，仅支持“dim\_type”为“binary”时使用。 |

| 参数 | 是否必选 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| neighbors | 否 | Integer | 64 | 图索引中每个向量节点的最大邻居数。值越大，图的连通性越强，检索精度（召回率）越高，但会增加索引文件的体积，且导致构建速度和查询速度变慢。  约束限制：必须在Mapping中设置“indexing”为“true”且“algorithm”为GRAPH类算法（GRAPH、GRAPH\_PQ、GRAPH\_SQ8、GRAPH\_SQ4）时，该参数配置才生效。  取值范围：20~255 |
| shrink | 否 | Float | 1 | 构建索引时的裁边系数。该参数控制图结构的稠密程度。值越小，裁剪越激进，图结构越稀疏，有利于搜索加速但可能损失精度。  约束限制：必须在Mapping中设置“indexing”为“true”且“algorithm”为GRAPH类算法（GRAPH、GRAPH\_PQ、GRAPH\_SQ8、GRAPH\_SQ4）时，该参数配置才生效。  取值范围：0.1~10 |
| scaling | 否 | Integer | 50 | HNSW算法中上层图节点数的缩放比例。该参数影响多层图结构的层级分布。合理的缩放比例能确保检索在各层级间的快速跳转效率。  约束限制：必须在Mapping中设置“indexing”为“true”且“algorithm”为GRAPH类算法（GRAPH、GRAPH\_PQ、GRAPH\_SQ8、GRAPH\_SQ4）时，该参数配置才生效。  取值范围：0~128 |
| efc | 否 | Integer | 200 | 构建HNSW索引时考察邻居节点的候选队列大小。该参数决定了构建索引时的“搜索深度”。值越大，构建出的图结构质量越高，查询精度越好，但索引构建耗时会显著增加。  约束限制：必须在Mapping中设置“indexing”为“true”且“algorithm”为GRAPH类算法（GRAPH、GRAPH\_PQ、GRAPH\_SQ8、GRAPH\_SQ4）时，该参数配置才生效。  取值范围：0~100000  建议在大规模数据下适当调大。 |
| max\_scan\_num | 否 | Integer | 10000 | 单次查询中允许扫描的最大节点上限。该参数用于限制单次检索的计算深度。值越大，检索结果越精确，但响应时延会增加。  约束限制：必须在Mapping中设置“indexing”为“true”且“algorithm”为GRAPH类算法（GRAPH、GRAPH\_PQ、GRAPH\_SQ8、GRAPH\_SQ4）时，该参数配置才生效。  取值范围：0~1000000 |

| 参数 | 是否必选 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| centroid\_num | 否 | Integer | 255（对应8-bit量化） | PQ算法中每段子空间的聚类中心点数目。该参数决定了量化后的编码精度。值越大，对原始向量的表达越精准，召回率越高，但计算开销和内存占用也会略微增加。  约束限制：必须在Mapping中设置“indexing”为“true”且“algorithm”为“GRAPH\_PQ”时，该参数配置才生效。  取值范围：0~65535 |
| fragment\_num | 否 | Integer | 0（系统会自动根据向量维度设置合适的段数） | 向量分段数（M）。将原始高维向量切分为M个子向量进行量化。段数越多，量化后的压缩向量越接近原始向量，精度越高，但会消耗更多存储空间。  约束限制：必须在Mapping中设置“indexing”为“true”且“algorithm”为“GRAPH\_PQ”时，该参数配置才生效。  取值范围：0~4096  当设为“0”时，系统将自动根据向量维度“dim”计算最优段数：  ``` if dim <= 256:     fragment_num = dim / 4 elif dim <= 512:     fragment_num = dim / 8 else:     fragment_num = 64 ``` |

#### （可选）预构建与注册中心点向量

当索引算法选择“IVF\_GRAPH”或“IVF\_GRAPH\_PQ”时，需要先预构建与注册中心点向量再创建向量索引。

在向量索引加速算法中，“IVF\_GRAPH”和“IVF\_GRAPH\_PQ”适用于十亿级以上的超大规模场景。这两种算法需要通过对子空间的切割缩小查询范围，子空间的划分通常采用聚类或者随机采样的方式。在预构建之前，需要通过聚类或者随机采样得到所有的中心点向量。通过将中心点向量预构建成GRAPH或者GRAPH\_PQ索引，同时注册到CSS向量数据库中，实现在多个节点间共享此索引文件。中心点索引在分片间复用能够有效减少训练的开销、中心点索引的查询次数，进而提升写入和查询性能。

1. 创建中心点索引表。
	例如，执行以下命令，创建中心点索引表“my\_dict”。
	```
	PUT my_dict 
	 { 
	   "settings": { 
	     "index": { 
	       "vector": true 
	     }, 
	     "number_of_shards": 1, 
	     "number_of_replicas": 0 
	   }, 
	   "mappings": { 
	     "properties": { 
	       "my_vector": { 
	         "type": "vector", 
	         "dimension": 2, 
	         "indexing": true, 
	         "algorithm": "GRAPH", 
	         "metric": "euclidean" 
	       } 
	     } 
	   } 
	 }
	```
	参数说明请参见 [创建向量索引](#ZH-CN_TOPIC_0000002523711048__zh-cn_topic_0000001309709789_section137344225249) ，需要关注以下必配参数：
	- index.number\_of\_shards：索引分片数必须配置为“1”，否则无法注册中心点索引。
	- indexing：必须配置为“true”，开启向量索引加速。
	- algorithm：必须指定特定的索引类型。当使用IVF\_GRAPH索引时配置为“GRAPH”，当使用IVF\_GRAPH\_PQ索引时配置为“GRAPH\_PQ”。
2. 写入中心点向量数据。将采样或者聚类得到的中心点向量写入新建的中心点索引表“my\_dict”中。
3. 调用注册接口。
	例如，执行以下命令，将中心点索引表注册具有全局唯一标识名称（dict\_name）的Dict对象。
	```
	PUT _vector/register/my_dict 
	 { 
	   "dict_name": "my_dict" 
	 }
	```
4. 创建IVF\_GRAPH或IVF\_GRAPH\_PQ算法类型的向量索引。
	在创建向量索引时，不再需要指定dimension以及metric信息，但需要指定注册好的Dict对象。关键参数配置如 [表6](#ZH-CN_TOPIC_0000002523711048__table3711163717243) 所示。
	例如，执行以下命令，创建IVF\_GRAPH类型的向量索引。
	```
	PUT my_index 
	 { 
	   "settings": { 
	     "index": { 
	       "vector": true,
	       "sort.field": "my_vector.centroid" # 将向量字段的centroid子字段设置为排序字段
	     } 
	   }, 
	   "mappings": { 
	     "properties": { 
	       "my_vector": { 
	         "type": "vector", 
	         "indexing": true, 
	         "algorithm": "IVF_GRAPH", 
	         "dict_name": "my_dict", 
	         "offload_ivf": true 
	       } 
	     } 
	   } 
	 }
	```
	| 参数 | 是否必选 | 类型 | 默认值 | 说明 |
	| --- | --- | --- | --- | --- |
	| dict\_name | 是 | String | 无 | 指定向量字段所依赖的中心点Dict对象，例如“my\_dict”。该向量字段的向量维度和度量方式将与Dict对象保持一致，无需重复配置。 |
	| offload\_ivf | 是 | Boolean | false | 是否将IVF倒排索引卸载到Elasticsearch/OpenSearch引擎层实现。  取值范围： - true：开启卸载，将倒排索引表交由Elasticsearch/OpenSearch引擎层进行物理存储管理。该配置能显著降低向量引擎对堆外内存的占用，并减少超大规模数据在写入与合并时的CPU及内存开销。 - false：不开启卸载，倒排索引将完全驻留在向量检索引擎专用的内存缓冲区中。  在处理亿级及以上规模数据，且希望在保证检索性能的同时优化集群内存配比时，建议设为true。 |

**父主题：** [CSS向量数据库](https://support.huaweicloud.com/usermanual-css/css_01_0143.html)