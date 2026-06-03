---
title: GPU互联网络架构
category: concepts
tags: [AI, GPU, NVLink, InfiniBand, RoCE, 网络]
aliases: [GPU互联, NVLink, IB网络, 训练网络]
relationships:
  - target: "[[concepts/gpu-computing-architecture]]"
    type: extends
  - target: "[[concepts/llm-parallelism-strategies]]"
    type: related_to
  - target: "[[concepts/cuda-software-stack]]"
    type: related_to
  - target: "[[concepts/llm-infra-landscape]]"
    type: derived_from
  - target: "[[concepts/linux-network-stack]]"
    type: related_to
source_dir: AI 人工智能/AI infra/大模型基础设施工程系列
source_files: [【大模型基础设施工程】04：互联与网络——NVLink、InfiniBand、RoCE 与国产替代.md]
summary: GPU互联两层架构：Scale-up(NVLink/NVSwitch/NVL72机柜级全连接)+Scale-out(IB/RoCEv2跨机万卡集群)；NVLink5达1.8TB/s，IB NDR 400Gb/s；GPUDirect RDMA使跨机AllReduce带宽增30-50%
provenance:
  extracted: 0.80
  inferred: 0.17
  ambiguous: 0.03
base_confidence: 0.75
lifecycle: draft
lifecycle_changed: 2026-06-02
tier: supporting
created: 2026-06-02
updated: 2026-06-02
---

# GPU互联网络架构

大模型训练从单卡扩展到万卡，**互联网络是决定MFU天花板的关键**。同一张H100，在3.2Tb/s无损RDMA网络上MFU 50%+，在普通100G以太网上MFU仅~20%。互联不是"基础设施"——它是**训练效率的核心变量**。

## 核心观点

- **Scale-up（机内）+ Scale-out（跨机）两层架构**：Scale-up目标是"让一组GPU成为一块巨型GPU"（NVLink/NVSwitch/NVL72）；Scale-out目标是横向扩展到10,000+卡（IB/RoCE/Fat-Tree/Rail-optimized）。
- **并行策略由互联带宽决定**：TP必须在NVLink域内（600 GB/s+）；PP可以跨节点IB（400 Gbps）；DP跨更大范围。带宽决定了并行效率上限。 ^[inferred]
- **GPUDirect RDMA是训练必备**：NIC直接DMA到GPU显存，绕过系统内存拷贝，跨节点AllReduce带宽增加30-50%。需要NIC和GPU在同一PCIe Switch下。
- **IB是"黄金标准"但贵2-3倍**；RoCEv2便宜30-50%但工程门槛高（PFC/ECN/DCQCN调优是一门艺术）。国内大厂（阿里、字节、腾讯）选RoCEv2。 ^[inferred]
- **fail-slow比fail-stop更危险**：NIC降速、光模块误码率升高、NVSwitch半死——带宽下降但不报错，整个步骤被一根慢链路拖慢2倍。

## Scale-up：机内/柜内互联

### NVLink带宽演进

| 代际 | GPU | 每GPU总带宽 | 关键特性 |
|------|-----|------------|---------|
| NVLink 1 | P100 (2016) | 160 GB/s | 首次替代PCIe P2P |
| NVLink 2 | V100 (2017) | 300 GB/s | 引入NVSwitch |
| NVLink 3 | A100 (2020) | 600 GB/s | 12链路 |
| NVLink 4 | H100 (2022) | 900 GB/s | 18链路+SHARP网内计算 |
| NVLink 5 | B200 (2024) | 1.8 TB/s | 18链路×100G PAM4 |

PCIe 5.0 x16单向仅64 GB/s——GPU间通信必须用NVLink/xGMI/HCCS，PCIe只用于CPU/NIC/NVMe连接。

### NVSwitch与NVL72

NVSwitch将多GPU连接成全连接交换网络。NVL72机柜：72个B200 GPU + 36个Grace CPU通过18个NVSwitch v4芯片（7.2 TB/s）全连接。铜缆背板（无retimer或光模块），120 kW液冷。任意P2P带宽1.8 TB/s。

### AMD Infinity Fabric

MI300X：7条IF链路，每条128 GB/s双向，总~896 GB/s。8-GPU全网格拓扑（无独立交换机芯片）。无法扩展到NVL72级别的72 GPU。

### 华为HCCS

昇腾910B：7条HCCS链路，每条~56 GB/s，总~392 GB/s（单向）。910C带宽翻倍。跨节点用HCCN RDMA NIC+HCCL库（对标NCCL）。

### CloudMatrix 384

华为2024超节点：384个昇腾910C，全高速光互连。300 PFLOPS (fp16)。500+ kW液冷。与NVL72对标但GPU更多、带宽略低、功耗更高。

## Scale-out：跨机万卡互联

### InfiniBand速率演进

| 代际 | 4X带宽 | 年份 | 代表 |
|------|--------|------|------|
| HDR | 200 Gb/s | 2018 | ConnectX-6 |
| NDR | 400 Gb/s | 2022 | ConnectX-7 |
| XDR | 800 Gb/s | 2024-2025 | ConnectX-8 |
| GDR | 1.6 Tb/s | 2027规划 | — |

IB生态（NVIDIA/Mellanox）：原生lossless+RDMA+SHARP网内计算。Quantum-2 800G每端口比同速以太网贵2-3倍。

### RoCEv2 (RDMA over Converged Ethernet)

在UDP/IP上运行RDMA，使用现有以太网基础设施。需要PFC/ECN/DCQCN三件套实现无损：
- **PFC**（IEEE 802.1Qbb）：后备机制，零丢包但有死锁/Pause风暴风险
- **ECN**：常态机制，IP头2位标记拥塞，发送端主动降速
- **DCQCN**：Mellanox拥塞控制算法，基于ECN反馈速率调节

RoCEv2成本：以太网交换机每端口比IB便宜30-50%。

### 拓扑选择

| 拓扑 | 特性 | 适用场景 |
|------|------|---------|
| **Fat-Tree/Clos** | 全无阻塞理论带宽，ECMP哈希冲突问题 | 通用数据中心 |
| **Rail-optimized** | 每GPU连自己的轨交换机，DP在同一轨内 | Meta/阿里/字节大规模训练 |
| **Dragonfly** | 组内全连接+组间少量链路，最多3跳 | CRAY/HPE超算 |

### Spectrum-X与UEC

- **Spectrum-X**：NVIDIA的以太网训练方案（Spectrum-4交换机+BlueField-3 DPU），将IB好处移植到以太网
- **UEC**（Ultra Ethernet Consortium）：AMD/Broadcom/Cisco/Meta/微软联盟，让以太网"训练原生"，packet spray+网内集合通信。UBEC 1.0预计2025-2026

## 关键细节

### GPUDirect RDMA

传统路径：GPU HBM → 系统内存 → NIC DMA → 网络（两次拷贝）。GPUDirect RDMA：NIC直接DMA GPU显存（零拷贝）。需要`nvidia-peermem`驱动，NIC和GPU在同一PCIe Switch下。

**实测效果**：加载`nvidia-peermem`后跨节点AllReduce busbw从180→260 GB/s（+44%）。

### AllReduce算法选择

| 算法 | 延迟 | 适用 | NCCL默认 |
|------|------|------|---------|
| Ring | O(N)带宽受限 | 大消息 | — |
| Tree | O(log N) | 小消息 | — |
| Double-binary tree | 带宽+延迟兼顾 | 大消息 | ✅ 默认 |
| SHARP | IB网内归约 | IB环境 | CollnetDirect |

### 实测带宽参考（nccl-tests, 1GB大消息）

| 场景 | 理论busbw | 实测可达 |
|------|-----------|---------|
| H100单机NVLink4 | 450 GB/s | 380-420 GB/s |
| H100跨机IB NDR×8 | 400 GB/s | 320-380 GB/s |
| H100跨机RoCEv2×8 | 400 GB/s | 280-360 GB/s（调优后） |

### 故障修复案例（4096-H100集群）

| 步骤 | 操作 | busbw改进 |
|------|------|----------|
| 1 | 加载nvidia-peermem | 180→260 GB/s |
| 2 | 调整DCQCN+降低PFC阈值 | 260→300 GB/s |
| 3 | 多QP+packet spray | 300→345 GB/s |
| 4 | 修复拓扑文件+NUMA pin | 345→360 GB/s |

MFU从28%→46%，训练时间从90天→55天。

### 选型决策流程

1. ≤1k卡，预算紧张 → IB NDR 400G×8 rail（简单，生态稳定）
2. 1k-10k卡，公有云 → 云厂商自研网络（阿里HPN，腾讯星脉，AWS EFA）
3. 10k-100k卡，自建 → Rail-optimized 3层Clos+800G RoCEv2+自研拥塞控制
4. ≥100k卡 → 多平面/多池，单池1-2万卡
5. 国产化 → CloudMatrix 384+华为/锐捷400G/800G以太网+HCCL

### CXL与光互连

- **CXL**：在PCIe PHY上运行，三种语义（CXL.io/cache/mem）。对LLM是次要角色，潜力在于KV缓存溢出和优化器状态offload。
- **CPO**（Co-Packaged Optics）：光引擎与交换机ASIC并置，功耗降30-50%，密度翻倍。可维护性是缺点。
- **光I/O进芯片**：Lightmatter/Ayar Labs，未来GPU芯片直接出光I/O。

## 未解问题

- UALink 1.0能否真正替代NVLink？AMD/Broadcom联盟vs NVIDIA垄断
- 跨DC训练的可行性？Google Gemini Ultra已做，DCI成为新战场
- CPO商用时间表？800G→1.6T迭代中

## 来源

- 【大模型基础设施工程】04 — NVLink/IB/RoCE/国产替代完整技术解析
- [[concepts/gpu-computing-architecture]] — HBM带宽+decode瓶颈
- [[concepts/llm-parallelism-strategies]] — 并行策略与互联约束映射