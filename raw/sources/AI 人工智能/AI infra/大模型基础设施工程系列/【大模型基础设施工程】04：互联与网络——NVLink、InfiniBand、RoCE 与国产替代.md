> 算力决定上限，**互联决定利用率**。
> 
> —— 做过万卡训练的人都懂这句话

在 2023 年之前，很多训练团队把精力都放在”怎么把 GPU 堆多”。到了 2024—2026 年，业界共识变了：**GPU 本身已经不是瓶颈，网络才是**。同样一批 H100，接在 3.2 Tb/s 无损 RDMA 上，训练一个 70B 模型的 MFU（Model FLOPs Utilization）能做到 50%+；接在普通 100G 以太网上，可能只有 20%，甚至跑着跑着因为 PFC 死锁挂掉。

这一篇就围绕**互联网络**展开，分两条主线：

- **Scale-up**：机内、柜内，极致带宽、极低延迟，目标是”把一堆 GPU 变成一台巨型 GPU”。代表技术：NVLink / NVSwitch / NVL72 / Infinity Fabric / HCCS / CXL。
- **Scale-out**：跨机、跨 Pod，横向扩展到万卡、十万卡。代表技术：InfiniBand、RoCEv2、UEC、Fat-Tree、Rail-optimized、Dragonfly。

我们会从物理层聊到拓扑层，从 AllReduce 聊到故障域，最后给出训练工程师视角下”集合通信打不满怎么办”的排查清单，以及 `nccl-tests` 的实操。

## 一、为什么 LLM 训练对网络这么敏感

### 1.1 万卡训练的流量特征

传统 HPC 里，通信占比高的是 CFD、分子动力学；传统数据中心里，流量是典型的 “南北向为主 + 东西向微服务”。**LLM 训练不是这两者**，它的流量画像非常独特：

1. **周期性、同步、大包、突发**：一个 step 内所有 GPU 同时发起 AllReduce / AllGather / ReduceScatter，瞬时把链路打满，下一秒又全部静默。
2. **Bandwidth-bound**：梯度、激活、KV 的传输都是几 MB 到几 GB 的大块，对带宽敏感远大于对延迟敏感（小消息 latency 影响流水线气泡，但绝大多数算子是带宽受限）。
3. **尾延迟决定全局**：一个 step 的结束时间 = `max(所有 rank 的完成时间)`。任何一条慢链路都拖慢整体，这就是万卡训练里常说的 **“straggler 问题”**。
4. **长连接 + 零丢包容忍**：一次 AllReduce 丢一个包触发重传，整个 step 就塌了。所以 RDMA 网络必须是**无损**或**近似无损**的。

### 1.2 一次 step 里的通信量

以 GPT-3 175B、TP=8、PP=8、DP=128（总 8192 卡）为例，粗算一个 step 的通信量：

- **TP AllReduce**：Attention / MLP 后每层一次，175B 模型约 96 层，每次 AllReduce 的张量大小 ~ `batch × seq × hidden × 2B`（fp16），单次几十 MB。TP 发生在**机内 NVLink**。
- **PP 点对点**：每个 micro-batch 发送 activation，几十 MB，跨机走 **RDMA**。
- **DP AllReduce**：梯度规模 ~ 350 GB（fp16），ZeRO-1 下切成 DP 组；跨机跨 rail，走 **RDMA AllReduce**。

所以训练一次 step，机内 NVLink 跑 TB 级别流量，机间 RDMA 也跑几百 GB。任何一个维度”瘸腿”，利用率立刻掉一大截。

## 二、Scale-up：机内与柜内互联

机内互联的目标很朴素：**越像一块 GPU 越好**。这意味着：高带宽、低延迟、统一地址空间、原生支持 P2P 和集合通信硬件加速。

### 2.1 PCIe：通用但不够用

PCIe 是 CPU—GPU、GPU—NIC 之间绕不开的通道。它的带宽演进：

    
|版本|单 lane 带宽|x16 双向|落地年份|代表平台|
|---|---|---|---|---|
|PCIe 4.0|16 GT/s|64 GB/s|2017|A100、Milan|
|PCIe 5.0|32 GT/s|128 GB/s|2022|H100、SPR、Genoa|
|PCIe 6.0|64 GT/s（PAM4）|256 GB/s|2024—2025|B200、Turin、GH200|
|PCIe 7.0|128 GT/s|512 GB/s|2027（规划）|—|

问题在于：**PCIe 5.0 x16 才 64 GB/s 单向**，而 H100 单卡 HBM 带宽已经 3 TB/s，NVLink 4 是 450 GB/s 单向。让 GPU 之间只走 PCIe，等于让法拉利走乡间小路。所以训练场景里，PCIe 主要用来接 CPU、NIC、NVMe，GPU 之间一定要走 NVLink / xGMI / HCCS 这种”专用高速通道”。

### 2.2 NVLink 与 NVSwitch：N 卡训练的护城河

NVLink 是 NVIDIA 自研的 GPU 间互联协议，和 PCIe 并行存在。演进如下：

    
|代|首发 GPU|单 link 双向|每 GPU 总带宽|关键特性|
|---|---|---|---|---|
|NVLink 1|P100（2016）|40 GB/s|160 GB/s|首次替代 PCIe P2P|
|NVLink 2|V100（2017）|50 GB/s|300 GB/s|引入 NVSwitch（DGX-2）|
|NVLink 3|A100（2020）|50 GB/s|600 GB/s|12 links|
|NVLink 4|H100（2022）|50 GB/s|900 GB/s|18 links，SHARP in-network|
|NVLink 5|B200（2024）|100 GB/s|1.8 TB/s|18 links × 100G PAM4|

**NVSwitch** 是把多块 GPU 连成 all-to-all 交换网的芯片。早期 DGX-2（V100 × 16）靠 6 颗 NVSwitch 做全连接；H100 HGX 8 卡靠 4 颗 NVSwitch v3；到了 B200，NVSwitch v4 芯片带宽 7.2 TB/s。

#### GB200 NVL72：把一个机柜变成一块 GPU

这是 2024—2026 年最重要的**产品级**变化。NVL72 的结构：

- 18 个 compute tray，每个 tray 放 2 颗 Grace CPU + 4 颗 B200 GPU（共 72 GPU + 36 CPU）
- 9 个 NVSwitch tray，每个 tray 2 颗 NVSwitch v4
- 所有 72 颗 GPU 之间**全 NVLink 互联**，任意两卡 P2P 带宽 1.8 TB/s
- 铜缆背板（copper cable cartridge），省掉 retimer 和光模块
- 整柜 120 kW，液冷必备

业务价值：**72 GPU 的 TP / EP 都能塞进一个 NVLink domain**。以前 TP 只能 8，现在可以 TP=16 甚至 TP=72；MoE 的 EP 也可以一柜内搞定，跨柜只走 DP 和 PP。训练 DeepSeek-R1 这种 671B MoE 模型，NVL72 几乎是天选硬件。

```
    NVL72 机柜示意（简化）
  ┌──────────────────────────────────────────┐
  │  Compute Tray × 18（每 tray 4 × B200）   │
  │  ┌───┐ ┌───┐ ┌───┐ ... ┌───┐            │
  │  │ G │ │ G │ │ G │     │ G │            │
  │  └─┬─┘ └─┬─┘ └─┬─┘     └─┬─┘            │
  │    └─────┴─────┴─────────┘              │
  │      NVLink5 Spine（Copper Cartridge）  │
  │    ┌──────────────────────────────┐     │
  │    │ NVSwitch Tray × 9（18 芯片） │     │
  │    └──────────────────────────────┘     │
  └──────────────────────────────────────────┘
```

对应的 SVG 示意图见文末。

### 2.3 AMD Infinity Fabric（xGMI）

AMD MI300X / MI325X / MI350X 用的是 **Infinity Fabric**（IF），也叫 xGMI（外部 GMI）。MI300X 单卡 7 条 IF link，每条 128 GB/s 双向，合计 ~ 896 GB/s，和 H100 一个量级。

MI300X 8 卡平台是全 mesh 互联（每卡到其他 7 卡各一条 link），没有独立 switch 芯片。好处是简单、低功耗；坏处是**扩不到 72 卡那种 NVL 级别**。AMD 在 MI355 / MI400 代推出类似 NVL 的 **UALink**（Ultra Accelerator Link）联盟标准，对标 NVLink。

### 2.4 华为昇腾 HCCS

华为 Atlas 900 / CloudMatrix 里，昇腾 910B / 910C 之间走 **HCCS（Huawei Cache Coherent System）**：

- 910B：每卡 7 条 HCCS，每条 ~ 56 GB/s，合计 ~ 392 GB/s（单向）
- 910C：带宽翻倍
- 单节点 8 卡全 mesh
- 跨节点经 **HCCN**（华为高速 RDMA 网卡），逻辑上把集合通信交给 HCCL 库（对标 NCCL）

2024 年华为发布 **CloudMatrix 384**：一个超节点 384 颗昇腾 910C，全高速互联，对标 NVL72 但卡数更多。代价是功耗巨大，整柜 500+ kW，基本是”液冷 + 自建数据中心”的配置。

### 2.5 CXL：内存池化对 LLM 的意义

CXL（Compute Express Link）跑在 PCIe PHY 上，三种语义：

- **CXL.io**：对齐 PCIe
- **CXL.cache**：设备缓存宿主机内存
- **CXL.mem**：宿主机访问设备内存（内存扩展 / 池化）

对 LLM 的直接意义有限但值得关注：

1. **推理侧 KV cache 溢出**：CXL memory 作为 HBM/DRAM 之下的第三层，用来装长上下文的 KV。
2. **训练侧 optimizer state offload**：ZeRO-Infinity 已经在用 NVMe，CXL 内存比 NVMe 快两个数量级，未来可能替代部分 offload 场景。
3. **CXL 3.0 fabric**：支持 switch 和多主机共享内存池，长期看有”训练数据随取随用”的想象空间。

但 2026 年实际生产里，CXL 对 LLM 还是**次要角色**，因为 HBM 自己在涨容量（HBM3e 192 GB、HBM4 288 GB），短期不缺内存。

## 三、Scale-out：机间互联

Scale-up 终点是一柜（NVL72 / CM384），再往外就必须 scale-out。机间互联的两大流派：**InfiniBand** 与 **RoCEv2**。

### 3.1 InfiniBand：训练网络的”黄金标准”

InfiniBand 自带 lossless、credit-based flow control、硬件 RDMA，几乎为 HPC 而生。速率演进：

|代|速率|带宽（4X）|年份|
|---|---|---|---|
|FDR|14 Gbps|56 Gb/s|2011|
|EDR|25 Gbps|100 Gb/s|2014|
|HDR|50 Gbps|200 Gb/s|2018|
|NDR|100 Gbps|400 Gb/s|2022|
|XDR|200 Gbps|800 Gb/s|2024—2025|
|GDR|400 Gbps|1.6 Tb/s|2027 规划|

NVIDIA 通过收购 Mellanox，把 IB 生态完全握在手里：**ConnectX-7 / 8、Quantum-2 / 3 交换机、SHARP（在网计算）**。SHARP 尤其关键——它把 AllReduce 的 reduction 操作下沉到交换机做，树形累加，带宽和延迟都打骨折。

IB 的代价：**贵，而且锁死在 NVIDIA 生态**。一套 Quantum-2 800G 方案，每端口价格是等速以太网的 2—3 倍。

### 3.2 RoCEv2：大厂的务实选择

RoCE（RDMA over Converged Ethernet）v2 跑在 UDP/IP 上，能直接用现有以太网基础设施，只要交换机支持 PFC / ECN / DCQCN 就行。国内大厂（阿里、字节、腾讯、百度）主力都是 **RoCEv2 over 以太网**，理由：

- **省钱**：以太网交换机白牌化程度高，同速率比 IB 便宜 30%—50%
- **生态解耦**：不依赖 NVIDIA，换 Broadcom / Marvell / 国产芯片都行
- **复用运维栈**：BGP / VXLAN / 监控体系全部沿用
- **易扩展**：万卡到十万卡，以太网的可扩展性更好

代价是**工程门槛高**：无损以太网不是”打开 PFC 就行”，需要全链路调优 buffer、拥塞控制、哈希，否则 PFC 死锁或风暴能让整个训练崩掉。

### 3.3 无损网络三件套：PFC / ECN / DCQCN

#### PFC（Priority-based Flow Control）

基于 802.1Qbb。某端口某优先级 buffer 快满了，向上游发 Pause 帧暂停该优先级流量。好处是**真正零丢包**；坏处是：

- **head-of-line blocking**：Pause 阻塞整条链路的该优先级
- **死锁**：拓扑成环 + 流量成环 → 所有端口互相 Pause，全局冻结。训练场景里 rail-optimized 拓扑特别容易踩这个
- **风暴**：一个慢节点把 Pause 传导到全网

所以 PFC 只能作为”兜底”，不能作为”常态”。

#### ECN（Explicit Congestion Notification）

IP 头里 2 个 bit，交换机排队超过阈值就标 CE（Congestion Experienced），接收端回 CNP（Congestion Notification Packet）给发送端。发送端收到 CNP 主动降速，**在丢包和 PFC 触发之前就把流量压下来**。ECN 才是常态工作机制。

#### DCQCN（Data Center QCN）

Mellanox / NVIDIA 提出的拥塞控制算法，结合 ECN 反馈做速率调节。关键参数（NIC 侧）：

- `Rai` / `Rhai`：加性增、乘性增的步长
- `Alpha`：根据 CNP 频率估计拥塞程度
- Timer：多久没收到 CNP 就加速恢复

DCQCN 的调参是门艺术：太激进导致抖动，太保守导致 throughput 上不去。阿里 HPN、字节 MegaScale 都有自研的拥塞控制（HPCC、Swift 等）作为替代。

### 3.4 800G 以太网与 UEC

2024—2026 年以太网侧最大的事：

1. **800G 商用落地**：Broadcom Tomahawk 5（51.2 Tb/s）、Marvell Teralynx 10、思科 Silicon One G200 全部支持 800G。
2. **1.6T 规划中**：Tomahawk 6（102.4 Tb/s）2025—2026 出样。
3. **UEC（Ultra Ethernet Consortium）成立**：AMD、Broadcom、Cisco、Arista、Meta、微软等发起，目标是把以太网重做成”训练原生”：packet spray、可选择丢包、in-network collective、更轻量的传输层（替代传统 RoCE 的 Go-Back-N）。

UEC 的潜台词就是”**我们不想一直给 NVIDIA IB 交保护费**”。预计 2025—2026 UEC 1.0 兼容网卡和交换机陆续上市，对 NVIDIA Spectrum-X 构成直接竞争。

### 3.5 NVIDIA 的反击：Spectrum-X

NVIDIA 当然不会放任以太网吃掉 IB 的份额，于是推出 **Spectrum-X**：Spectrum-4 交换机 + BlueField-3 / ConnectX-8 DPU/NIC，基于以太网但集成了：

- **adaptive routing**：流级别重新哈希，对抗 ECMP hash 冲突
- **packet spray + reorder**：NIC 侧重排序，把多链路负载均衡做到极致
- **拥塞控制协同**：交换机 telemetry 实时反馈到 NIC

本质上是”把 IB 的好处搬到以太网上”，抢以太网阵营的单。

## 四、拓扑：Fat-Tree、Rail-optimized、Dragonfly

拓扑决定了**对分带宽（bisection bandwidth）** 和**最坏情况延迟**。

### 4.1 Fat-Tree / Clos

两层或三层 Clos 网络，是通用数据中心的默认拓扑：

```
        Spine 层（core switch）
       /    |    |    \
    Leaf  Leaf  Leaf  Leaf
    /|\   /|\   /|\   /|\
   ...服务器...
```

- 理论上全对分无阻塞（非阻塞 fat-tree）
- 扩展性好，常规 3 层可支撑十万卡级别
- 问题：**ECMP hash 冲突**。两条大象流哈希到同一 uplink，链路利用率上不去

### 4.2 Rail-optimized（Meta / 字节 / 阿里都在用）

Rail-optimized 的核心想法：**按卡号分轨**。

每台 8 卡服务器的 GPU0 全部连到 rail-0 交换机，GPU1 连到 rail-1 交换机……共 8 条独立 rail。DP AllReduce 只在同 rail 内发生，机间只走本 rail 的带宽，完全避免跨 rail 的 ECMP 冲突。

```
       rail-0 switch          rail-7 switch
       /  |  |  \             /  |  |  \
  Server0 Server1 ...    Server0 Server1 ...
   GPU0   GPU0             GPU7   GPU7
```

优点：

- AllReduce 带宽稳定，逼近理论值
- 故障域清晰（rail-x 挂了只影响 GPU-x）

缺点：

- 跨 rail 通信（PP、EP）要多跳
- 拓扑感知必须做对，否则退化

阿里 HPN、Meta RSC、字节 MegaScale 集群基本都是 rail-optimized 变体。

### 4.3 Dragonfly

CRAY / HPE 在超算上用的拓扑，分 group，group 内全连接，group 间少量长链路。

- 优点：对分带宽高，全局跳数少（最多 3 跳）
- 缺点：需要 adaptive routing + UGAL 调度，生态小众

国内训练场景里不常见，主要是 Frontier、Aurora 这种超算集群用。

### 4.4 Multi-rail

一台服务器接 4—8 张 NIC（现在 H100 / B200 标配 **1 GPU : 1 NIC**，每卡独立一张 400G / 800G NIC）。NCCL 会自动把 AllReduce 拆成 N 条流在 N 条 rail 上并发，总带宽线性叠加。

Multi-rail 的关键：

- **NUMA / PCIe 亲和**：NIC 必须和它服务的 GPU 挂在同一 PCIe Switch / CPU，否则走 QPI / UPI 过去带宽腰斩
- **拓扑文件**：NCCL 的 `NCCL_TOPO_FILE` 要正确声明 GPU-NIC 关系

## 五、集合通信与网络的关系

### 5.1 AllReduce 是带宽受限的

Ring AllReduce 的数据量分析：

- N 卡、数据量 D、一次 Ring-AllReduce 总步骤 = `2(N-1)`
- 每步传输 `D/N`，总传输量 `2D(N-1)/N ≈ 2D`
- 理论最优时间 `T = 2D(N-1) / (N · B)`，其中 B 是单链路带宽

结论：**N 很大时，AllReduce 时间几乎只取决于 B**。这就是为啥大家拼命堆带宽而不是堆卡数——带宽不够，加卡只会让每卡 throughput 更低。

### 5.2 Tree / Double-binary tree / SHARP

- **Tree AllReduce**：延迟 O(log N)，适合小消息
- **Double-binary tree**：NCCL 默认大消息策略，带宽利用率接近 ring，延迟 O(log N)
- **SHARP**：IB 交换机做在网规约，一次 AllReduce 只需要”上树 + 下树”，延迟和带宽都显著改善

NCCL 2.18+ 默认自动选择，也可以 `NCCL_ALGO=Ring` / `Tree` / `CollnetChain` / `CollnetDirect` 手动指定。

### 5.3 计算通信重叠

训练框架（Megatron、DeepSpeed、FSDP）都会做 overlap：反向传播算出一层梯度立刻开始 AllReduce，下一层计算并行进行。前提是**网络 throughput 足够稳**，否则 overlap 窗口小于通信时间，优化失效。

## 六、万卡故障域

### 6.1 fail-stop vs fail-slow

- **fail-stop**：GPU 挂了、NIC 挂了、节点宕机——监控立刻能抓到，重启 / 换节点恢复
- **fail-slow**：更可怕。一张 NIC 降速、一个 optic 模块误码率升高、一颗 NVSwitch 半死，**带宽从 400G 降到 200G 但不报错**。整个 step 被这一根慢链路拖慢 2 倍

fail-slow 的典型表现：某个 rank 的 AllReduce 时间突然从 50ms 涨到 200ms，且持续一段时间；NCCL 监控 per-rank 时间就能发现。

### 6.2 链路抖动

光模块温度波动、DSP 误码、SerDes 重训练都会导致短时抖动。无损网络下，抖动可能触发 PFC，进一步诱发风暴。缓解：

- 光模块选用长期稳定的 200G-per-lane 甚至 100G-per-lane（别追最新的 200G PAM4）
- 交换机 buffer 调大，吸收瞬时突发
- 分级 QoS，训练流量独占一个优先级类

### 6.3 hash 冲突与大象流

ECMP 基于五元组哈希，训练流都是长连接大象流，很容易两条流撞同一 uplink。缓解：

- **rail-optimized 从源头避免**
- **adaptive routing**（Spectrum-X、IB）
- **packet spray**（UEC）
- **多 QP 打散**：NCCL 开多 QP（`NCCL_IB_QPS_PER_CONNECTION=4`），哈希变成 5 元组 × 4

### 6.4 Checkpoint 与故障域隔离

这是下一篇（05 / 10）的主题，这里只提一句：万卡集群的 MTBF 是按**小时**算的，Ckpt 间隔必须小于 MTBF，否则训练永远卡在回滚。

## 七、国产互联生态

### 7.1 网络设备

- **华为**：CloudEngine 16800 系列，400G / 800G 以太网，配合昇腾 HCCN NIC，支持 RoCEv2 无损
- **锐捷网络**：RG-S6980、S8920 系列，阿里、字节都大量采购
- **新华三（H3C）**：S12500G、S9825 系列，百度、腾讯用得多
- **中兴**：ZXR10 9900X 系列

国产 51.2T 交换芯片（盛科、华为自研）已在 2025 年陆续上市，国产替代在**可用**级别，性能对标 Tomahawk 4—5。

### 7.2 华为 CloudMatrix 384

2024 年底发布，2025 年大规模部署：

- 384 颗昇腾 910C
- 超节点内全高速光互联（华为自研光模块）
- 对外接口兼容标准以太网 / RoCEv2
- 单超节点算力 ~ 300 PFLOPS（fp16）

对标 NVL72（72 GPU），卡数更多、带宽略低、功耗更大。在国内外管制背景下是 DeepSeek、Kimi 等团队的重要备选。

### 7.3 腾讯星脉网络

腾讯自研，特点：

- 全自研交换机（基于 Tomahawk / 自研芯片）
- 自研 **TiTa 拥塞控制**（替代 DCQCN），更快收敛
- rail-optimized + 多平面
- 支持万卡至十万卡

### 7.4 阿里 HPN（High Performance Network）

阿里云训练集群底座：

- 自研 **HPCC / Swift** 拥塞控制
- **双上联**：每台服务器双 NIC 接不同 leaf，一侧挂了另一侧接管，消除单点
- **eRDMA**：在 VPC 里跑 RDMA，云上训练也能享受无损
- PAI-DLC、通义训练都跑在 HPN 上

### 7.5 字节 MegaScale

《MegaScale》论文披露了字节的万卡方案：

- rail-optimized 3 层 Clos
- 400G RoCEv2
- 大量 fail-slow 检测探针
- NCCL 深度魔改，感知拓扑选最优算法

## 八、SuperPod / SuperCluster：十万卡级别

### 8.1 NVIDIA DGX SuperPod

标准化万卡方案：

- 以 DGX H100 / B200 node 为单元
- IB Quantum-2（NDR 400G）组 rail-optimized 3 层
- SHARP in-network reduction
- 配 BCM（Bright Cluster Manager）+ NVIDIA Base Command 软件栈

2024—2026 年 Blackwell 代：**GB200 NVL72 × N** 组成 SuperPod，NVL72 间走 IB XDR 800G。

### 8.2 Meta Research SuperCluster（RSC）与 Grand Teton

Meta 训练 Llama 3 / 4 的基础设施：

- 两个 24k H100 集群（一个 RoCE、一个 IB，做 A/B 对比）
- Grand Teton 整机柜设计，OCP 标准
- **无损以太网 + rail-optimized + 自研调度**

结论是”两边都能跑 Llama 3，生态视角 RoCE 更划算”。

### 8.3 xAI Colossus：10 万卡

2024 年 Elon Musk 在孟菲斯建的超级集群：

- 100k H100 → 2025 扩到 200k H200 / B200
- Spectrum-X 以太网 + NVL72
- 号称 19 天从零部署完 10 万卡（实际是分阶段，但节奏极猛）

工程意义：**证明以太网阵营能打 10 万卡级别**。

### 8.4 国内超大集群

- 字节：北京怀来、山西、新疆万卡—十万卡级
- 阿里：张北、乌兰察布，多个 HPN 万卡集群
- 腾讯：星脉支持的万卡集群，训练混元
- 华为云：乌兰察布 / 贵安，CloudMatrix 384 × N
- 百度：阳泉百舸 4.0 万卡

## 九、光互联与 CPO

### 9.1 可插拔光模块的瓶颈

传统 QSFP-DD / OSFP 可插拔光模块，功耗和密度已经到极限：

- 800G OSFP 模块功耗 14—17 W，一个 51.2T 交换机光模块总功耗接近交换机本体
- 前面板密度有限，再往上到 1.6T / 3.2T 已经插不下

### 9.2 CPO（Co-Packaged Optics）

CPO 的思路：**把光引擎贴到交换机 ASIC 旁边**，省掉 SerDes 跑前面板这段距离。

- 功耗降低 30%—50%
- 密度翻倍
- 代价：维修性差（坏一个要换整板），可靠性需要时间验证

Broadcom 2024 年发布 Tomahawk 5 Bailly CPO 版本；NVIDIA 2025 年宣布 Spectrum-X 和 Quantum-X 都会有 CPO 产品线；国内光迅、中际旭创、新易盛都在押注。

### 9.3 硅光（Silicon Photonics）

硅光是 CPO 的底层技术路线之一：用 CMOS 工艺做光调制器 / 探测器。代表公司：Intel（Silicon Photonics 已分拆）、Ayar Labs、Lightmatter、国内的光迅。

对训练的直接好处：**未来可能看到 GPU die 上直接出光**（optical I/O），NVLink 跨机柜不再需要铜缆 + 电—光转换。

## 十、训练工程师视角：集合通信打不满怎么办

### 10.1 排查清单

一个 step 的 AllReduce 时间比理论值高 20% 以上，按顺序查：

1. **NCCL 是不是用对了网络**
    
    ```
    export NCCL_DEBUG=INFO
    export NCCL_DEBUG_SUBSYS=INIT,GRAPH,NET
    ```
    
    看启动日志里 `NCCL INFO NET/IB : Using [0]mlx5_0:1/IB` 或 `NET/Socket`。如果是 Socket，说明 RDMA 根本没起来。
    
2. **GPU-NIC 亲和**
    
    看 GPU 和 NIC 之间是 `PIX`（同 PCIe switch，最优）、`PXB`（跨 bridge）、`NODE`（同 NUMA）、`SYS`（跨 NUMA，最差）。跨 NUMA 的组合必须修正拓扑文件。
    
3. **多 QP 和 rail 数**
    
    ```
    export NCCL_IB_QPS_PER_CONNECTION=4
    export NCCL_IB_SPLIT_DATA_ON_QPS=1
    export NCCL_IB_HCA=mlx5_0,mlx5_1,mlx5_2,mlx5_3,mlx5_4,mlx5_5,mlx5_6,mlx5_7
    ```
    
4. **算法选对**
    
    ```
    export NCCL_ALGO=Ring,Tree,CollnetChain,CollnetDirect
    export NCCL_PROTO=Simple,LL,LL128
    ```
    
    大消息用 Ring + Simple，小消息用 Tree + LL128。打开 NCCL autotune 后一般不用手调。
    
5. **PFC / ECN 配置**
    
    交换机上 `show pfc statistics`、`show ecn statistics`，看有没有大量 Pause 帧或 CNP。正常训练应该只有少量 ECN，PFC 接近 0。
    
6. **慢节点检测**
    
    写个 per-rank allreduce 时间统计，看有没有某一两个 rank 一直比别人慢。慢节点隔离出来单独测带宽。
    

### 10.2 NCCL 常用环境变量速查

|变量|作用|
|---|---|
|`NCCL_DEBUG=INFO/WARN`|调试日志|
|`NCCL_DEBUG_SUBSYS=ALL`|细分子系统日志|
|`NCCL_IB_HCA`|指定使用的 IB HCA|
|`NCCL_IB_GID_INDEX`|RoCEv2 下必须设，通常 3|
|`NCCL_SOCKET_IFNAME`|控制面网卡|
|`NCCL_P2P_DISABLE`|禁用 P2P（调试用）|
|`NCCL_SHM_DISABLE`|禁用 SHM|
|`NCCL_NET_GDR_LEVEL`|GPUDirect RDMA 级别|
|`NCCL_BUFFSIZE`|NCCL 内部 buffer 大小|
|`NCCL_MIN_NCHANNELS` / `NCCL_MAX_NCHANNELS`|并行 channel 数|

### 10.3 nccl-tests 实操

这是工程师的万能基准测试工具。

```
git clone https://github.com/NVIDIA/nccl-tests
cd nccl-tests
make MPI=1 CUDA_HOME=/usr/local/cuda NCCL_HOME=/usr/local/nccl

# 8 卡单机 AllReduce（默认 NVLink 带宽测试）
./build/all_reduce_perf -b 8 -e 8G -f 2 -g 8

# 跨机：16 节点 × 8 GPU = 128 卡
mpirun -np 128 -H host1:8,host2:8,...,host16:8 \
  -x NCCL_DEBUG=INFO \
  -x NCCL_IB_HCA=mlx5_0,mlx5_1,mlx5_2,mlx5_3,mlx5_4,mlx5_5,mlx5_6,mlx5_7 \
  -x LD_LIBRARY_PATH \
  ./build/all_reduce_perf -b 8 -e 8G -f 2 -g 1
```

关注两列：

- `busbw`：总线带宽，= `algbw × 2(N-1)/N`。对 ring AllReduce，**busbw 应该接近单链路带宽**
- `time`：耗时

经验值参考（大消息 1 GB）：

|场景|理论 busbw|实测可达|
|---|---|---|
|H100 单机 NVLink4|450 GB/s|380—420 GB/s|
|B200 NVL72 内|900 GB/s|750—850 GB/s|
|H100 跨机 IB NDR × 8 rail|400 GB/s|320—380 GB/s|
|H100 跨机 RoCEv2 400G × 8|400 GB/s|280—360 GB/s（调优后）|

低于这个范围就说明有问题，按 10.1 排查。

### 10.4 拓扑感知：`NCCL_TOPO_FILE` 示例

NCCL 会自动探测拓扑，但云虚机 / 容器里经常探不准。手动写：

```
<system version="1">
  <cpu numaid="0" affinity="ffff,00000000" arch="x86_64">
    <pci busid="0000:0a:00.0" class="0x060400" link_speed="32.0 GT/s" link_width="16">
      <pci busid="0000:0b:00.0" class="0x030200">
        <gpu dev="0" sm="90" rank="0"/>
      </pci>
      <pci busid="0000:0c:00.0" class="0x020000">
        <nic>
          <net name="mlx5_0" dev="0" speed="400000" port="1" latency="0" guid="..."/>
        </nic>
      </pci>
    </pci>
  </cpu>
  ...
</system>
```

启动时 `NCCL_TOPO_FILE=/path/to/topo.xml`。现代 NCCL（2.18+）结合 `NCCL_GRAPH_FILE` 还可以进一步固化通信图。

## 十一、两张拓扑示意图

### 11.1 Fat-Tree vs Rail-optimized

![Fat-Tree vs Rail-optimized](https://quant67.com/post/llm-infra/04-interconnect/images/04-interconnect-fig1.svg)

### 11.2 NVL72 机柜示意

![NVL72 机柜示意](https://quant67.com/post/llm-infra/04-interconnect/images/04-interconnect-fig2.svg)

## 十二、进阶话题：GPUDirect、RDMA 编程与内核旁路

### 12.1 GPUDirect RDMA

传统数据路径：GPU HBM → 系统内存 → NIC DMA → 网络。两次拷贝，CPU 介入，带宽腰斩。

**GPUDirect RDMA** 让 NIC 直接 DMA GPU 显存：

- 需要 NIC、GPU 挂在同一 PCIe Root Complex 或同一 PCIe Switch 下
- 内核驱动 `nvidia-peermem`（取代老的 `nv_peer_mem`）把 GPU BAR 映射给 NIC
- 对应 NCCL 环境变量 `NCCL_NET_GDR_LEVEL=PIX`（同 switch 才启用）或 `=SYS`（强制启用）

启用后跨机 AllReduce 带宽能再涨 30%—50%，是**训练必开**项。

### 12.2 GPUDirect Storage（GDS）

`cuFile` API，让 NVMe 直接 DMA GPU 显存。训练里用得不多（数据 pipeline 有 CPU 侧 DataLoader 处理），但推理侧大模型权重加载、KV offload 到 NVMe 时很有用。

### 12.3 用 `ibv_*` 直接写 RDMA

多数情况下不需要，但排障时有用。一个最小化的 WRITE 操作：

```
struct ibv_send_wr wr = {};
struct ibv_sge sge = {
    .addr   = (uintptr_t)local_buf,
    .length = size,
    .lkey   = mr->lkey,
};
wr.wr_id           = 0;
wr.sg_list         = &sge;
wr.num_sge         = 1;
wr.opcode          = IBV_WR_RDMA_WRITE;
wr.send_flags      = IBV_SEND_SIGNALED;
wr.wr.rdma.remote_addr = remote_addr;
wr.wr.rdma.rkey        = remote_rkey;

struct ibv_send_wr *bad;
ibv_post_send(qp, &wr, &bad);

struct ibv_wc wc;
while (ibv_poll_cq(cq, 1, &wc) == 0) {}
if (wc.status != IBV_WC_SUCCESS) { /* 错误处理 */ }
```

排障时可以用 `ib_write_bw` / `ib_read_bw` 直测链路：

```
# 服务器端
ib_write_bw -d mlx5_0 -F -x 3 --report_gbits

# 客户端
ib_write_bw -d mlx5_0 -F -x 3 --report_gbits <server_ip>
```

正常 400G IB 应该能跑到 395+ Gb/s，低于 380 就要查 PCIe 亲和或光模块。

### 12.4 DPU / IPU 的角色

BlueField-3 / Pensando / AWS Nitro 这些 DPU，在 AI 训练集群里主要做：

1. **RDMA 卸载**：本来就是 NIC 功能
2. **虚拟化**：多租户云训练里，把 VPC、overlay、安全组全部卸载到 DPU，让 CPU 和 GPU 专心算
3. **存储加速**：NVMe-oF initiator 在 DPU 上跑
4. **训练观测**：DPU 天然在网卡侧，telemetry、packet capture 都最合适

阿里 eRDMA、AWS EFA 都高度依赖 DPU。

## 十三、真实案例：一次万卡训练的网络复盘

这一节把前面所有技术点串起来，讲一个真实（虚构但贴近行业）的案例：某团队用 4096 卡 H100 训练一个 100B 模型，MFU 迟迟上不去。

### 13.1 现象

- 单机 8 卡 nccl-tests AllReduce：400 GB/s（正常）
- 跨机 16 机 128 卡 AllReduce：预期 ~ 350 GB/s，实测 180 GB/s
- 训练 MFU 只有 28%，期望 45%+

### 13.2 排查步骤

**Step 1：看 NCCL 日志**

```
export NCCL_DEBUG=INFO
export NCCL_DEBUG_SUBSYS=NET,GRAPH
```

日志里发现：

```
NCCL INFO NET/IB : Using [0]mlx5_0:1/IB [1]mlx5_1:1/IB ... [7]mlx5_7:1/IB
NCCL INFO Channel 00 : 0[0] -> 1[0] via NET/IB/0
```

8 张 NIC 都识别到了，OK。

**Step 2：查 GPU-NIC 亲和**

```
nvidia-smi topo -m
```

发现 GPU4—GPU7 和对应 NIC 是 `SYS`（跨 NUMA），而 GPU0—GPU3 是 `PIX`（同 PCIe switch）。**根因 1**：服务器 BIOS 里 PCIe Root Complex 划分不对，NIC 全部挂在 Socket 0。

**Step 3：改硬件或改拓扑文件**

硬件不能动，只能接受跨 NUMA。但发现系统没有加载 `nvidia-peermem`：

```
lsmod | grep peermem
# 空
modprobe nvidia-peermem
```

**根因 2**：GPUDirect RDMA 没启用，数据绕了一圈 CPU。

**Step 4：检查交换机 ECN / PFC**

```
show interface counters errors
show pfc statistics interface Ethernet1/1
```

发现某几个 leaf 的 PFC Pause 计数每秒上万，**根因 3**：拥塞控制没调好，训练流量经常触发 PFC。

**Step 5：查 QP 和 channel 数**

```
NCCL_IB_QPS_PER_CONNECTION=1（默认）
```

多 rail 下单 QP 容易哈希冲突，改成：

```
export NCCL_IB_QPS_PER_CONNECTION=4
export NCCL_IB_SPLIT_DATA_ON_QPS=1
```

### 13.3 修复后

- 加载 `nvidia-peermem`：busbw 从 180 → 260 GB/s
- 调 DCQCN + 降 PFC 阈值：→ 300 GB/s
- 开多 QP + packet spray：→ 345 GB/s
- 修拓扑文件 + NUMA pin：→ 360 GB/s

MFU 从 28% 涨到 46%。训练时长从 90 天缩到 55 天。

### 13.4 启示

这个案例里，没有一个”致命 bug”，全是几个百分点的小问题叠加。万卡训练的网络调优就是这样——**每个环节省 10%，整体翻倍**。所以基建团队必须对 NCCL、NIC、交换机、拓扑、NUMA 全栈都懂。

## 十四、展望 2026—2028

1. **NVLink 走出机柜**：NVIDIA 路线图里 NVLink Fusion / NVL576，用光互联把多个 NVL72 连成更大的 scale-up 域
2. **UALink 1.0 出货**：AMD / Broadcom / Cisco 阵营推出替代 NVLink 的开放标准
3. **UEC 1.0 大规模部署**：预计 2026—2027 年成为以太网训练的事实标准
4. **CPO 商用**：800G → 1.6T 迭代中，CPO 从试点走向规模部署
5. **光 I/O 进芯片**：Lightmatter、Ayar Labs 的 optical I/O 可能首次出现在商用 AI 芯片上
6. **国产超节点 1000+ 卡**：华为 CloudMatrix 下一代、寒武纪、壁仞可能推出千卡级超节点
7. **跨 DC 训练**：Google Gemini Ultra 已经在做跨数据中心训练，DCI（DC Interconnect）成为新战场

网络演进的速度会比过去五年更快——因为 GPU 单卡算力增长在放缓，scale-up / scale-out 的想象力变成了整个行业的新增长点。

## 十五、选型决策速查

训练团队做网络选型时，建议按这个决策流：

1. **规模 ≤ 1k 卡，预算紧**：单柜或 2—3 机柜，IB NDR 400G × 8 rail，省事、生态稳
2. **规模 1k—1 万卡，走公有云**：用云商自研网络（阿里 HPN、腾讯星脉、AWS EFA、Azure InfiniBand），不要自己折腾
3. **规模 1 万—10 万卡，自建**：rail-optimized 3 层 Clos + 800G RoCEv2 + 自研拥塞控制；或 Spectrum-X；IB 仅在成本允许时考虑
4. **规模 ≥ 10 万卡**：必须多平面 / 多池，单池 1—2 万卡，池间走骨干或分层调度
5. **国产化路线**：昇腾 CloudMatrix 384 + 华为 / 锐捷 400G / 800G 以太网，HCCL + 自研 RoCEv2 栈
6. **推理集群**：KV cache 以 intra-node 为主，对跨机带宽要求远低于训练；可以用 200G RoCE 或甚至 100G

## 参考资料

1. NVIDIA, _NVLink and NVSwitch Architecture Whitepaper_, 2022—2024
2. NVIDIA, _GB200 NVL72 Datasheet / System Guide_, 2024
3. NVIDIA, _Spectrum-X Platform Whitepaper_, 2023
4. NVIDIA, _nccl-tests_ 仓库：[https://github.com/NVIDIA/nccl-tests](https://github.com/NVIDIA/nccl-tests)
5. Mellanox, _DCQCN: Data Center Quantized Congestion Notification_, SIGCOMM 2015
6. Alibaba, _HPN: A Data Center Network for Large Language Model Training_, SIGCOMM 2024
7. ByteDance, _MegaScale: Scaling Large Language Model Training to More Than 10,000 GPUs_, NSDI 2024
8. Meta, _RDMA over Ethernet for Distributed AI Training at Meta Scale_, SIGCOMM 2024
9. Tencent, _Tencent Xingmai (Starlink) Network_, 2023—2024 技术博客
10. AMD, _Infinity Fabric / xGMI Documentation_, MI300X 平台
11. Huawei, _CloudMatrix 384 超节点白皮书_, 2024
12. Ultra Ethernet Consortium, _UEC Specification 1.0 (Draft)_, 2024—2025
13. CXL Consortium, _CXL 3.0 Specification_, 2023
14. Broadcom, _Tomahawk 5 Product Brief_, 2023
15. xAI, _Colossus Cluster Overview_, 2024—2025

---

**上一篇**：[CUDA 生态：cuBLAS、cuDNN、NCCL、Triton、CUTLASS](https://quant67.com/post/llm-infra/03-cuda-stack/03-cuda-stack.html) **下一篇**：[训练全景：Pre-train、SFT、RLHF、DPO、蒸馏](https://quant67.com/post/llm-infra/05-training-overview/05-training-overview.html)

## 同主题继续阅读

把当前热点继续串成多页阅读，而不是停在单篇消费。

2026-04-25 · architecture / ai-infra

### [【大模型基础设施工程·特别篇】DeepSeek-V4 与国产芯片：从备份路线到主路径](https://quant67.com/post/llm-infra/26-deepseek-v4-domestic-chip/26-deepseek-v4-domestic-chip.html)

DeepSeek-V4 发布后，如果国产芯片已经支撑旗舰模型的关键训练或推理链路，它会怎样影响 NVIDIA 生态、国产 AI 芯片、云厂商、模型团队和工程师的技术选择？

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】02：GPU 计算入门——SM、Tensor Core、HBM、NVLink](https://quant67.com/post/llm-infra/02-gpu-primer/02-gpu-primer.html)

从 CPU 与 GPU 的架构差异出发，讲清楚 SM、Warp、Tensor Core、HBM、NVLink 的工程含义，并结合 Roofline、FlashAttention 与国产算力栈，给出大模型工程师能直接上手的 GPU 心智模型。

2026-04-22 · architecture / ai-infra

### [大模型基础设施工程](https://quant67.com/post/llm-infra/index.html)

面向中国工程团队的大模型基础设施系列。从 GPU/CUDA/互联、训练框架与 3D 并行、vLLM/SGLang 推理引擎、量化与推测解码、RAG/Agent 到服务化、网关、可观测性与安全合规，覆盖 LLMOps 全链路。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】11：推理引擎基础](https://quant67.com/post/llm-infra/11-inference-basics/11-inference-basics.html)

从 Prefill/Decode 两阶段、KV Cache、Continuous Batching 到 PD 分离，系统讲清楚大模型推理的工程基础。