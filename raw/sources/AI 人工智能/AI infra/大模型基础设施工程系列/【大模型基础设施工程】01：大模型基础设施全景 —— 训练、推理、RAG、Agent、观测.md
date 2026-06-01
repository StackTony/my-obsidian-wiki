> 这是【大模型基础设施工程】系列第 01 篇。系列共 25 篇，从 GPU 到 Agent，自底向上覆盖训练、推理、RAG、Agent、服务化、网关、观测与成本安全。本篇为开篇，目标是让任何一位后端 / 平台 / 算法 / SRE 工程师，在读完后对「大模型基础设施」这张地图里有哪些地标、自己在哪、要往哪走，有一个清晰的印象。

## 一、为什么需要一个「大模型基础设施」视角

### 1.1 大模型是一种新的工作负载

对后端工程师来说，过去二十年我们熟悉的工作负载大致是这几类：无状态 Web 服务、关系库 OLTP、分析型 OLAP、搜索引擎、消息中间件、批处理 / 流处理。这些工作负载的瓶颈、SLO、扩展模型已经被反复打磨，社区共识也稳定。

大模型不是这些负载中的任何一个。它同时具有以下特征：

- **计算密集并且访存密集**：训练阶段是典型的 HPC（高性能计算）任务，推理阶段的 decode 环节却是典型的内存带宽瓶颈；
- **状态极重**：一次 pre-train 的中间状态（权重 + 优化器 + 激活 + KV 缓存）动辄 TB 级，checkpoint 时长从分钟到小时；
- **故障常态化**：千卡、万卡级集群里，节点故障、网络抖动、HBM（高带宽显存）ECC 错误每天都在发生，训练作业必须把”容错”做进设计；
- **成本极高**：单次大规模训练动辄百万到千万美元；推理侧，每百万 token 的成本从 2023 年的 60 美元级别正被压到 2026 年的 1 美元以下；
- **生命周期长**：一个基座模型从预训练、SFT、RLHF、量化、部署到下线，跨越的时间和团队远大于一个普通微服务。

这就要求把它当作一个**独立的基础设施领域**来对待，而不是”在 K8s 里多起一个 Deployment”。

### 1.2 本系列面向的读者

本系列默认你已经熟悉 Linux、容器、分布式系统和常见后端中间件，但**不要求**你懂 CUDA kernel、不要求你读过 Attention 论文。我们会用工程化的语言把每一层讲清楚：

- **训练工程师**：第 02–10 篇是你的主食；
- **推理 / 性能工程师**：第 11–16 篇是你的主食；
- **RAG / Agent 应用工程师**：第 17–20 篇是你的主食；
- **平台 / SRE 工程师**：第 21–25 篇是你的主食；
- **架构师 / 技术决策者**：建议通读，特别关注第 01、05、11、17、21、24、25 篇。

### 1.3 本系列的写作原则

在深入之前先声明几条原则，方便读者判断这个系列是否值得读：

- **工程优先于论文**：遇到某个技术点时，优先讲”它解决了什么工程问题、在哪一层、替换成本多大”，而不是照搬论文公式；
- **量化优先于定性**：只要能估算，就给数量级；只要能测量，就给方法；
- **中国 + 全球并重**：不做”国外先进 / 国产追赶”的单向叙事，而是把两条栈同时摆出来做对比；
- **开源 + 商业并重**：既承认 vLLM / SGLang 已经足够撑起严肃平台，也承认 TensorRT-LLM、Bedrock、百炼在某些场景有不可替代的工程价值；
- **演进友好**：2026 年的结论不等于 2028 年的结论，每一篇尽量指出”哪些是稳定的、哪些还在快速变化”。

## 二、2022 → 2026：大模型工程的分水岭

一个领域是否”工程化”，看的是**是否形成了可复用、可量化、可替换的工程组件**。大模型正在以非常快的速度走过这段路，时间线大致如下。

### 2.1 2022 年 11 月：ChatGPT 上线

工程意义远比产品意义大：

- 第一次证明了**对话式 LLM**可以作为一个全球级 SaaS 运营；
- 背后引入了一整套**推理服务化**的工程：流式返回、速率限制、多租户、模型多版本路由；
- 催生了整个”LLM as a Service”的市场形态。

### 2.2 2023 年 2 月：LLaMA 泄漏与开源运动

Meta 的 LLaMA（Large Language Model Meta AI）从内部研究走向开源后：

- HuggingFace 成为事实上的模型分发中心；
- llama.cpp 打开了**消费级硬件推理**的可能性，CPU、Apple Silicon、小显存 GPU 第一次能跑 7B/13B 模型；
- LoRA / QLoRA 等轻量微调方法工程化，“自己炼一个模型”门槛从百卡降到单卡。

### 2.3 2023 年 6 月：vLLM 与 PagedAttention

UC Berkeley 发布的 vLLM 是推理侧第一次真正工程意义上的”范式转移”：

- **PagedAttention** 把 KV 缓存按页管理，消除了内存碎片；
- **Continuous Batching**（持续批处理）把传统静态 batch 改成请求级动态拼装，吞吐提升 2–4 倍；
- 此后 SGLang、TensorRT-LLM、TGI 纷纷采纳类似设计，成为推理引擎的新基线。

### 2.4 2024 年：LLaMA-3、Mixtral、长上下文

- Meta LLaMA-3 405B 把开源基座拉到了接近闭源旗舰的水平，训练成本估算 60M 美元以上；
- Mistral 的 Mixtral 把 **MoE（Mixture of Experts，专家混合）** 带回主流视野；
- 上下文窗口从 4K、8K 走向 128K、200K，长上下文工程（YaRN、环形 attention、分块 prefill）成为刚需；
- RAG（Retrieval Augmented Generation，检索增强生成）和 Agent 框架（LangChain、LangGraph、LlamaIndex）开始大规模落地。

### 2.5 2024 年底 – 2025 年：o1 / o3 / Claude 3.7 / Gemini 2.5 与”推理时代”

OpenAI o1、o3，Anthropic Claude 3.7 Sonnet，Google Gemini 2.5 Pro 共同推进了 **reasoning model（推理型模型）**：

- 模型在”思考链”上花费更多 token，推理侧的算力占比第一次**接近甚至超过**训练侧；
- **推理预算（inference budget）** 成为新的调参维度；
- **推测解码（speculative decoding）**、**MTP（Multi-Token Prediction）**、**投机并行** 从论文走到生产。

### 2.6 2024 年末 – 2026 年：DeepSeek 冲击与成本革命

DeepSeek-V2、V3、V3.1、R1 系列带来了一次系统性冲击：

- **MLA（Multi-head Latent Attention）** 把 KV 缓存压缩一个数量级；
- **细粒度 MoE + 共享专家** 把激活参数压到更低；
- **FP8 训练** 全流程工程化落地；
- **DualPipe** 等并行方案让训练在相对少的卡上也能跑得动；
- DeepSeek-V3 训练成本公开估算在 6M 美元级别，对比 LLaMA-3 405B 的 60M+，展示了一条”工程密度”而非”硬件堆量”的路线；
- 2026 年左右，DeepSeek-V3.1、Qwen3 等开源模型将推理单价压到 1 美元 / 百万 token 以内，改写了整个成本结构。

### 2.7 小结：四个工程分水岭

如果只记四件事：

1. **ChatGPT**：确立了 LLM 推理 SaaS 的工程范式；
2. **LLaMA + HuggingFace**：确立了模型分发与微调的工程栈；
3. **vLLM + PagedAttention**：确立了推理引擎的现代范式；
4. **DeepSeek-V3 + FP8 + MLA**：确立了”通过工程创新降低 10 倍成本”的范式。

### 2.8 一张”工程密度”示意图

![工程密度示意图](https://quant67.com/post/llm-infra/01-intro/images/01-intro-fig1.svg)

## 三、大模型工程栈的五层模型

面对一整堆眼花缭乱的组件，最清晰的方式是把它抽象成**五层**，从底到上：硬件、系统软件、框架、应用、运营。

### 3.1 分层总览

```
┌──────────────────────────────────────────────────────────────┐
│ 05 运营层  观测、计费、配额、合规、安全、灰度、成本治理        │
├──────────────────────────────────────────────────────────────┤
│ 04 应用层  RAG、Agent、工具调用、工作流、Prompt 工程           │
├──────────────────────────────────────────────────────────────┤
│ 03 框架层  PyTorch / JAX / Megatron / DeepSpeed / vLLM / SGLang │
├──────────────────────────────────────────────────────────────┤
│ 02 系统软件 CUDA / ROCm / cuBLAS / cuDNN / NCCL / Triton       │
├──────────────────────────────────────────────────────────────┤
│ 01 硬件    GPU / NPU / HBM / NVLink / InfiniBand / RoCE        │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 第一层：硬件

关键抽象：**算力、显存、带宽、互联**。

- **算力单位**：FLOPS（浮点每秒），当前主流关心 FP8/FP16/BF16 Tensor Core 算力，单卡 H100 约 1 PFLOPS FP8；
- **显存**：HBM（High Bandwidth Memory，高带宽显存）容量（40/80/96/141/192 GB）与带宽（2–5 TB/s）直接决定能跑多大模型；
- **卡间互联**：NVLink（单机内）、NVSwitch、InfiniBand（跨机 RDMA）、RoCE（以太网上的 RDMA）；
- **主流型号**：Nvidia H100 / H200 / B200 / GB200，AMD MI300X / MI325X，国产 昇腾 910B / 910C、寒武纪、海光、壁仞、摩尔线程。

### 3.3 第二层：系统软件

这一层的共性特征是”对上层框架提供数学原语和通信原语”。

- **通用计算**：CUDA、ROCm、OpenCL、昇腾 CANN；
- **线性代数**：cuBLAS、rocBLAS、OneDNN；
- **卷积 / Attention**：cuDNN、FlashAttention 系列；
- **集合通信**：NCCL（Nvidia Collective Communications Library）、RCCL、HCCL；
- **内核 DSL**：Triton、CUTLASS，用 Python / C++ 写高性能 kernel 的现代方式。

### 3.4 第三层：框架

这是工程师最频繁打交道的一层。

- **训练框架**：PyTorch（事实标准）、JAX（Google 系）、MindSpore、PaddlePaddle；
- **训练并行库**：Megatron-LM、DeepSpeed、FSDP（Fully Sharded Data Parallel）、ColossalAI；
- **推理引擎**：vLLM、SGLang、TensorRT-LLM、Text Generation Inference（TGI）、llama.cpp、MLC-LLM、lmdeploy；
- **分布式调度 / 运行时**：Ray、Kubeflow、Volcano、KubeRay。

### 3.5 第四层：应用

把”裸模型”变成”有用的产品”的一层。

- **RAG**：向量检索（FAISS、Milvus、Qdrant、Weaviate、pgvector）、BM25、ColBERT、混合检索、重排、图 RAG；
- **Agent**：LangChain、LangGraph、LlamaIndex、AutoGen、CrewAI、Dify、Coze；
- **工具调用**：Function Calling、MCP（Model Context Protocol，模型上下文协议）；
- **Prompt 工程**：模板管理、版本化、A/B 测试、评测。

### 3.6 第五层：运营

让一个 LLM 平台能被多租户、多业务长期使用的一层。

- **可观测性**：Token 级、请求级、会话级追踪，首 token 延迟（TTFT）、token 间延迟（TPOT）、吞吐、成功率；
- **网关与路由**：LiteLLM、OneAPI、Portkey、Kong AI Gateway、商用网关；
- **成本治理**：按业务 / 模型 / 租户的 token 计量与预算；
- **安全合规**：内容审核、PII（Personally Identifiable Information，个人可识别信息）脱敏、越狱防护、红队评测；
- **灰度 / 评测 / 回归**：模型升级时的在线评测与快速回滚。

### 3.7 全景 SVG

![全景 SVG](https://quant67.com/post/llm-infra/01-intro/images/01-intro-fig2.svg)

### 3.8 分层背后的通用模式

如果把上述五层当作一个”协议栈”来看，你会发现它和经典 OSI 模型遵循相同的工程原则：

- **下层只对上层暴露抽象**：上层不关心你用的是 H100 还是昇腾 910B，只要 CUDA / CANN 暴露的原语等价；
- **跨层优化是主要性能来源**：FlashAttention 是跨”系统软件 → 框架”的代表，PagedAttention 是跨”框架 → 硬件”的代表，FP8 训练则是跨三层的工程；
- **标准化正在发生但远未完成**：ONNX、OpenAI API、MCP、Triton IR 是几条较成熟的标准化线，而训练框架之间的标准化（比如并行策略描述）依然是薄弱环节。

在后续每篇里，我们会反复指出：**这一层把什么抽象暴露给了上层？这一层从下层拿到了什么？哪些跨层约定正在松动或固化？**

## 四、训练 vs 推理：工程差异的 N 个维度

训练和推理常被合称为”跑模型”，但它们是**两类完全不同的工程问题**。

### 4.1 计算特性

   
|维度|训练|推理 prefill|推理 decode|
|---|---|---|---|
|主导瓶颈|计算（FLOPS）|计算（FLOPS）|显存带宽|
|算术强度|高|高|极低（每 token 几乎扫一遍权重）|
|Batch|大而静态|中等|必须持续拼 batch 才有吞吐|
|典型利用率目标|MFU（Model FLOPs Utilization） 40–55%|50%+|通过 continuous batching 提吞吐|

`decode` 环节每生成一个 token 就要把整模型权重从 HBM 扫一遍（再加 KV 缓存读写），所以**带宽决定吞吐**。这就是为什么 H200（带宽 4.8 TB/s）在推理场景下相对 H100（3.35 TB/s）的提升远大于 FLOPS 提升。

### 4.2 批处理模型

- **训练**：batch 在作业启动时固定，step 时间可预测；
- **推理**：请求长短不一，且 decode 步数动态变化，必须用 **continuous batching**（持续批处理）按 token 粒度重拼 batch，并配合 **PagedAttention** 管理 KV 缓存。

### 4.3 状态与 checkpoint

- 训练 checkpoint = 权重 + 优化器状态 + 学习率调度 + RNG + 数据 iterator。以 100B 模型、AdamW、FP32 优化器为例，checkpoint 大小近 1.6 TB；
- 推理只需权重（可以量化后更小），但是运行时持有大量 **KV 缓存**，这部分是”准状态”，是推理侧的核心资源之一。

### 4.4 故障模型

- 训练作业寿命以天、周计，必须假设**节点会死**：保存频率、异步保存、弹性并行（Elastic Training）、torch.distributed elastic、DeepSpeed 的 Nebula、Megatron 的 async checkpoint 都是为此而生；
- 推理作业寿命以请求计（毫秒到分钟），但对 SLO 极敏感，故障意味着**尾延迟**飙升，需要重试、多副本、双活、以及 KV 缓存的优雅迁移。

### 4.5 SLO 与衡量指标

推理典型 SLO：

- **TTFT**（Time To First Token，首 token 时间）：对话场景常要求 p95 < 500 ms；
- **TPOT**（Time Per Output Token，每输出 token 时间）：通常 20–80 ms；
- **吞吐**：每 GPU 每秒 token 数；
- **成本**：每百万 token 美元数 / 元。

训练典型 SLO：

- **Tokens/s/GPU**；
- **MFU / HFU**（Hardware FLOPs Utilization）；
- **恢复时间**（从故障到重新达到稳定 step 时间）。

### 4.6 一张对比图

### 4.7 一个常见的误解

很多后端工程师第一次接触推理时会假设”推理就是一次函数调用”，但在工业场景里它更像**一个长连接上的流式生产者**：

- 每个请求是一个**生成任务**，持续输出 token，中间可以被抢占、可以被 evict KV 缓存、可以被 cancel；
- 多个请求在**同一张 GPU 上并发**存在，共享权重、共享 scheduler、独享 KV 缓存的若干 page；
- 因此推理引擎更像**数据库的查询执行器 + 进程调度器**，而不是一个 stateless 的 handler。

记住这个心智模型，第 11–15 篇会用得着。

### 4.8 单卡可行性粗算

一个工程师常被问到的问题是”一张 H100 能跑多大模型”。这里给一个粗算：

- 权重：参数数 × 每参数字节（FP16 = 2，FP8 = 1，INT4 ≈ 0.5）；
- KV 缓存：`2 × layers × heads × head_dim × seq_len × batch × 每元素字节`；
- 激活 / 工作区：一般预留 5–15 GB；
- 留给 PagedAttention 的余量：20–30%。

以 Qwen2.5-72B、FP8、单 H100（80 GB）为例：

- 权重约 72 GB，已经吃掉大部分显存；
- KV 缓存只剩约 5 GB，支撑的上下文非常有限；
- 所以真实部署里 72B 基本都是 2 卡 TP，或者走 INT4。

如果换成 FP8 + 2 卡 TP：

- 每卡权重约 36 GB；
- 每卡 KV 空间约 30 GB，可以在 8K 上下文下支撑几十路并发。

这类估算会在 11–14 篇里不断出现，习惯了以后”看一眼模型就知道要几张卡”会是很有用的直觉。

## 五、核心工作负载速览

把大模型的生命周期拆开，一共有 8 类核心工作负载，每一类都对应不同的工程栈。

### 5.1 Pre-train（预训练）

- 数据：数万亿 token，来自 Common Crawl、代码、书、论文、多语料；
- 规模：数百到数万张 GPU；
- 周期：数周到数月；
- 工程关键：数据流水、3D 并行、checkpoint、故障恢复、吞吐监控；
- 典型栈：PyTorch + Megatron-LM / DeepSpeed + NCCL + InfiniBand。

### 5.2 SFT（Supervised Fine-Tuning，监督微调）

- 数据：十万到千万级高质量指令数据；
- 规模：单机到几十卡居多；
- 周期：小时到几天；
- 关键：数据配比、loss masking、LoRA / QLoRA 降本；
- 工程栈：HuggingFace TRL、LLaMA-Factory、Axolotl、Unsloth。

### 5.3 RLHF / DPO（Direct Preference Optimization，直接偏好优化）

- 三套模型同时在线：Actor、Reference、Reward（PPO 还加 Critic），显存压力很大；
- DPO / KTO / GRPO 等新方法简化为两套；
- 工程关键：多模型协同训练、rollout 与 train 的分布式编排；
- 参考工程：DeepSpeed-Chat、OpenRLHF、TRL、verl、NeMo-Aligner。

### 5.4 蒸馏

- 用大模型作为 teacher，让小模型学 teacher 的 logits / 轨迹 / 推理链；
- 关键：teacher 推理吞吐要高，数据管道要能喂饱 student；
- 工业意义：2025–2026 年，“大模型蒸馏出的 7B 小钢炮”成为端侧、专用任务的主力。

### 5.5 推理 prefill

- 把输入 prompt 一次性过一遍，产生 KV 缓存；
- 计算密集，工程关键：chunked prefill、prefill–decode 解耦；
- DeepSeek、vLLM、SGLang 都在 prefill/decode 分离上下功夫。

### 5.6 推理 decode

- 一步步往外吐 token；
- 带宽密集，工程关键：continuous batching、PagedAttention、推测解码、MTP、量化。

### 5.7 RAG 召回

- 离线：文档切片、embedding、入库、构图；
- 在线：query 改写 → 向量 / BM25 / 图 召回 → 重排 → 拼 prompt；
- 工程关键：召回质量、延迟预算、嵌入模型一致性。

### 5.8 Agent 编排

- 模型主动调用工具、规划多步；
- 工程关键：状态机 / 图、可观测、失败回退、并行执行、沙箱；
- 代表：LangGraph、AutoGen、CrewAI、Dify。

### 5.9 工作负载—资源画像对比

     
|工作负载|计算|显存|网络|存储 IO|典型延迟 / 周期|
|---|---|---|---|---|---|
|Pre-train|极高|极高|极高（AllReduce）|高（数据 + ckpt）|数周~数月|
|SFT|高|高|中|中|小时~天|
|RLHF|高|极高（多模型）|高|中|天~周|
|蒸馏|高|中|中|高（teacher 日志）|天~周|
|Prefill|高|中|低|低|数十 ms~秒|
|Decode|中|高（KV）|低|低|毫秒 / token|
|RAG 离线|中|中|中|高（文档）|小时|
|RAG 在线|低|低|中|中（向量 IO）|毫秒~几十 ms|
|Agent|取决于调用链|同 decode|中（工具调用）|中|秒~分钟|

这张表的意义在于：**一个完整的 LLM 平台需要同时承载性质差异极大的几类负载**，平台层面的调度、配额、优先级都要考虑这些差异。

### 5.10 一张工作负载拓扑图

![工作负载拓扑图](https://quant67.com/post/llm-infra/01-intro/images/01-intro-fig3.svg)

### 5.11 工作负载与团队分工

在一个成熟的 LLM 团队里，这些工作负载通常映射到不同的小组：

- **基座训练组**：Pre-train、继续预训练、数据；
- **对齐组**：SFT、RLHF、DPO、安全微调；
- **推理 / 性能组**：vLLM / SGLang 深改、量化、调度；
- **应用 / RAG 组**：检索、Agent、Prompt；
- **平台 / SRE 组**：调度、网关、观测、成本；
- **评测组**：自动化评测、红队、回归。

小团队里一个人可能身兼数职，但**角色边界还是存在的**，本系列的路线图也是按这些角色组织的。

## 六、行业地图：谁在做什么

### 6.1 全球大模型厂商

- **OpenAI**：闭源，GPT-4o / GPT-4.1 / o1 / o3 / o4-mini / GPT-5 系列，定位通用最强 + 推理；
- **Anthropic**：闭源，Claude 3.5 / 3.7 Sonnet、Claude 4 / Opus，强调代码与 Agent 场景；
- **Google DeepMind**：Gemini 1.5 / 2.0 / 2.5 Pro / Flash，多模态、长上下文领先；
- **Meta**：LLaMA-3、LLaMA-4，开源基座；
- **xAI**：Grok 系列；
- **Mistral**：开源 + 闭源混合，欧洲代表；
- **Cohere**：企业 RAG / embedding；
- **Nvidia**：既是硬件也是软件（NIM、NeMo、TensorRT-LLM）；
- **AMD**：MI300X / MI325X + ROCm 快速追赶。

### 6.2 中国大模型厂商

- **DeepSeek（深度求索）**：DeepSeek-V2/V3/V3.1、R1；工程密度最高，FP8 + MLA + MoE 的代表；
- **阿里 通义千问 Qwen**：Qwen2.5、Qwen3、Qwen3-VL、Qwen-Coder；开源生态最强的中国厂商之一；
- **智谱 GLM**：GLM-4、GLM-4.5、CogVLM、CodeGeeX；
- **月之暗面 Kimi**：Kimi K1.5、K2；长上下文与 Agent；
- **百川智能**：Baichuan 系列；
- **MiniMax**：abab、MiniMax-M1，linear attention 路线；
- **字节 豆包 / Doubao**：豆包 1.5 Pro、豆包 Seed 系列；
- **百度 文心**：文心一言 / ERNIE 4.0 / ERNIE X1；
- **华为 盘古**：盘古 5.0 / 盘古 Ultra MoE，与昇腾深度绑定；
- **腾讯 混元**：Hunyuan-Large、Hunyuan-T1；
- **商汤 日日新**、**科大讯飞 星火**、**昆仑万维 天工**、**阶跃星辰 Step** 等多家。

### 6.3 云厂商的大模型平台

- **AWS**：Bedrock（多模型聚合）+ SageMaker（自训练）+ Trainium / Inferentia；
- **Azure**：Azure OpenAI + Azure AI Foundry；
- **GCP**：Vertex AI + TPU v5p / v5e / Trillium + Gemini；
- **阿里云**：PAI（Platform for AI） + 百炼（Model Studio）；
- **火山引擎**：veMLP + 方舟（Ark）+ 豆包；
- **百度智能云**：千帆 ModelBuilder + 文心；
- **华为云**：ModelArts + 盘古；
- **腾讯云**：TI 平台 + 混元；
- **昇腾云 / Atlas**、**摩尔线程 MCCX** 等国产化专区。

### 6.4 开源基础设施

几乎所有自建 LLM 平台都会用到以下其中几件：

- **HuggingFace**：模型、数据、Transformers / Accelerate / TRL / PEFT / Datasets；
- **vLLM / SGLang / TensorRT-LLM / TGI / lmdeploy**：推理引擎；
- **Megatron-LM / DeepSpeed / FSDP / ColossalAI**：训练并行；
- **Ray / KubeRay**：分布式运行时；
- **LangChain / LangGraph / LlamaIndex / Haystack**：应用编排；
- **Milvus / Qdrant / Weaviate / Chroma / pgvector**：向量库；
- **LiteLLM / OneAPI / Portkey**：网关；
- **Langfuse / LangSmith / Helicone / Arize Phoenix**：观测。

### 6.5 国产硬件与软件栈

2025–2026 年，国产 GPU / NPU 已经不再是 PPT 状态，主流选型如下：

- **昇腾 910B / 910C**：华为自研，配套 CANN（Compute Architecture for Neural Networks）、MindSpore、MindIE。单卡 FP16 约 320 TFLOPS，互联 HCCS；
- **海光 DCU**：基于类 ROCm 栈，兼容性好，金融 / 政企侧采用较多；
- **寒武纪 MLU370 / MLU590**：深度学习专用 ASIC；
- **壁仞 BR100 / BR104**：大算力 GPGPU；
- **摩尔线程 MTT S4000 / KUAE 千卡集群**：国产通用 GPU 代表；
- **燧原**：推理专用加速。

软件栈配套：

- **训练**：MindSpore、PaddlePaddle、DeepSpeed 国产移植；
- **推理**：MindIE、LMDeploy（商汤）、FastDeploy（百度）、昇腾版 vLLM；
- **集合通信**：HCCL（华为）、BCCL（百度）、ACCL（阿里）；
- **云平台**：昇腾云、百度智能云千帆、阿里云灵骏 / 灵积、火山引擎 veMLP。

这条栈的工程特点是：**抽象层更薄，跨层调优空间更大，但生态成熟度仍低于 CUDA**。本系列第 02、04、13 篇会分别展开硬件、互联和推理引擎层面的对比。

### 6.6 选型矩阵的一张速查

  
|场景|推荐栈（全球）|推荐栈（中国）|
|---|---|---|
|从零预训练 100B+|H100/H200 + Megatron + NCCL + IB|H800 / 昇腾 910C + MindSpeed / Megatron + HCCL|
|自建推理平台|H100/H200 + vLLM / SGLang|H20 / 昇腾 910B + vLLM 昇腾版 / MindIE|
|仅调用模型做应用|Azure OpenAI / Bedrock + LangGraph|百炼 / 方舟 / 千帆 + Dify|
|端侧 / 边缘|Apple Silicon / Jetson + llama.cpp / MLC|昇腾 Atlas 300I / 寒武纪 MLU220|
|科研 / 小团队|4090 / L40S + HuggingFace + Unsloth|4090 / 昇腾 300V + LLaMA-Factory|

## 七、成本曲线：为什么 2026 年值得认真讨论「大模型基础设施工程」

### 7.1 训练成本

   
|模型|年份|估算训练成本|备注|
|---|---|---|---|
|GPT-3 175B|2020|~4.6M 美元|V100 集群|
|GPT-4|2023|约 60–100M 美元|非公开，业界估算|
|LLaMA-2 70B|2023|~2M 美元|A100|
|LLaMA-3 405B|2024|~60M+ 美元|H100 × 16k+|
|Gemini Ultra|2023|~100M+ 美元|TPU v4 / v5|
|DeepSeek-V3 671B|2024 末|~5.6M 美元（官方）|H800 × 2048，FP8 + MLA + MoE|
|DeepSeek-R1|2025|≈ V3 + RL 增量|在 V3 基础上|

**关键结论**：成本从”堆硬件”转向”工程密度”。DeepSeek-V3 用 1/10 的钱训出接近第一梯队的模型，其手段几乎全部来自工程（FP8、MLA、MoE 路由、DualPipe、通信压缩、数据配比）。这就是这个系列把”工程”放在最前面的原因。

### 7.2 推理成本

OpenAI 官方定价（美元 / 百万 token，粗略口径）：

|时间|代表模型|输入|输出|
|---|---|---|---|
|2023.03|GPT-4 8K|30|60|
|2024.05|GPT-4o|5|15|
|2024.07|GPT-4o mini|0.15|0.60|
|2025|o3 / GPT-4.1 系列|显著下降|显著下降|

开源 / 中国模型：

|模型|推理单价（元 / 百万 token，输出口径，粗略）|
|---|---|
|GPT-3.5 turbo（2023）|约 15|
|Qwen-Turbo（2024）|2|
|DeepSeek-V2（2024）|2|
|DeepSeek-V3（2024 末）|8（输出）|
|DeepSeek-V3.1（2026 预估）|< 1|
|豆包 Pro（2024–2025）|0.8–2|

**两年量级下降**来自几处工程叠加：

1. **模型侧**：MoE 化（激活参数下降）、MLA（KV 缓存下降）、推测解码 + MTP（每 token 计算摊薄）；
2. **系统侧**：FP8 / INT8 量化、PagedAttention + Continuous Batching、prefill/decode 分离；
3. **硬件侧**：H100 → H200 → B200 带宽翻倍；
4. **规模效应**：大型推理集群的 MFU 和缓存命中率更高。

成本曲线还会继续下降，但**工程门槛越来越高**：把单价从 10 降到 1 靠的是工程，把 1 降到 0.3 靠的是系统级协同设计，这正是本系列的主题。

### 7.3 一个简化的推理成本模型

对于自建推理集群，单 token 成本的近似公式是：

```
cost_per_token ≈ (GPU_hourly_cost × num_gpus) / (tokens_per_second × 3600)
```

举例：一台 8×H100 机器，按云上 30 美元/小时/卡 算，共 240 美元/小时。若整机 decode 吞吐达到 20000 tokens/s：

```
cost = 240 / (20000 × 3600) ≈ 3.3e-6 美元 / token ≈ 3.3 美元 / 百万 token
```

对比 API 定价，就能看出**自建是否划算**的交叉点。后续第 21、24 篇会把这个模型展开成包含 prefill/decode 差异、缓存命中、利用率波动的完整模型。

### 7.4 训练成本的三种口径

工程决策时常见三种口径，不要混淆：

1. **纯算力口径**：GPU 小时数 × 单卡价格（如 H100 $2/h），只反映硬件租金；
2. **含集群 overhead**：加上网络、存储、电力、PUE、运维，一般是 1.5–2 倍纯算力；
3. **含数据 + 人力 + 失败重跑**：大模型训练失败重跑是常态，一次完整项目成本常是纯算力的 3–5 倍。

DeepSeek-V3 公开的 5.6M 美元是第一种口径，很多媒体对比时忽略了这一点，导致对比失真。

## 八、一次 LLM 请求的生命周期

理解整体架构最直接的方式，是跟着一次请求走一遍：

几个值得记的设计要点：

1. **网关是第一公民**：所有鉴权、限流、审核、多模型路由、成本计量都在这一层；
2. **RAG 是可选旁路**：不是每个请求都要检索，但一旦引入，就要把延迟预算切一块给它；
3. **Prefill / Decode 解耦**已经成为主流推理集群的部署方式；
4. **Tool / MCP 调用**会让单次请求变成多轮，生命周期可能横跨秒级到分钟级；
5. **观测**必须与网关同轴，token 级日志是事后一切优化的基础。

### 8.1 一条请求的延迟预算拆解

假设 SLO 是 p95 TTFT < 1200 ms，我们可以给一条典型 RAG 请求的延迟预算做个粗略分解：

|阶段|预算|典型实现|
|---|---|---|
|网关鉴权 / 审核|20 ms|本地缓存 + 异步审核|
|向量 / BM25 召回|60 ms|Milvus / ES，预热索引|
|重排|80 ms|Cross-encoder，小模型|
|Prompt 拼装|10 ms|模板引擎 + 缓存|
|推理 Prefill|800 ms|vLLM / SGLang，chunked prefill|
|首 token 返回|100 ms|流式链路|
|网关回包|30 ms|gRPC → HTTP/SSE|
|观测埋点|async|异步落 Kafka / OTel|

从这张表能看出几件事：

- **Prefill 是 TTFT 的主要贡献者**，长 prompt 下更明显；
- **重排不是免费的**，但可以并行化、可以裁剪；
- **观测不进入延迟预算**，但一旦做成同步会把 p95 拖垮。

### 8.2 一个简单的 Python 客户端示例

```
import requests

resp = requests.post(
    "https://llm-gw.example.com/v1/chat/completions",
    headers={"Authorization": "Bearer $TOKEN"},
    json={
        "model": "qwen3-32b",
        "messages": [
            {"role": "system", "content": "你是后端工程师助手。"},
            {"role": "user", "content": "用 100 字解释 PagedAttention。"},
        ],
        "stream": True,
        "max_tokens": 512,
    },
    stream=True,
    timeout=60,
)

for line in resp.iter_lines():
    if line:
        print(line.decode())
```

后续第 22 篇会把这条客户端路径换成经过 LiteLLM / OneAPI / Kong AI Gateway 的完整生产链路，并给出限流、鉴权、多模型路由的详细配置。

## 九、本系列 25 篇路线图

整个系列按”从底到上、从点到面”的顺序展开，对应第三节的五层模型。

### 9.1 硬件与系统（第 02–04 篇）

- **02 GPU 计算入门**：SM、Tensor Core、HBM、NVLink；
- **03 CUDA 生态**：cuBLAS、cuDNN、NCCL、Triton、CUTLASS；
- **04 互联与网络**：NVLink、InfiniBand、RoCE、国产替代。

### 9.2 训练（第 05–10 篇）

- **05 训练全景**：Pre-train / SFT / RLHF / DPO / 蒸馏；
- **06 3D 并行深度**：数据 / 张量 / 流水 / 序列 / ZeRO；
- **07 Megatron-LM 与 DeepSpeed**：两大主力训练栈对比；
- **08 MoE 训练工程**：路由、负载、通信；
- **09 RLHF 与对齐流水线**：PPO / DPO / GRPO；
- **10 Checkpoint 与故障容忍**：万卡集群的现实。

### 9.3 推理（第 11–16 篇）

- **11 推理引擎基础**：KV 缓存、prefill/decode；
- **12 PagedAttention 与 Continuous Batching**；
- **13 vLLM / SGLang / TensorRT-LLM / TGI 对比**；
- **14 量化工程**：INT8 / FP8 / AWQ / GPTQ；
- **15 推测解码与 MTP**；
- **16 长上下文工程**：YaRN、环形 attention、分块 prefill。

### 9.4 应用（第 17–20 篇）

- **17 RAG 工程全景**；
- **18 向量库与图 RAG**；
- **19 Agent 框架工程**：LangGraph、AutoGen、Dify 对比；
- **20 工具调用与 MCP**。

### 9.5 平台与运营（第 21–25 篇）

- **21 推理服务化**：K8s、Ray Serve、KServe；
- **22 大模型网关**：LiteLLM、OneAPI、Portkey、商用网关；
- **23 LLM 可观测性**：Langfuse、Helicone、Arize；
- **24 成本、合规与安全**；
- **25 大模型基础设施未来**。

### 9.6 按角色推荐阅读路径

- **训练 / 算法工程师**：01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10 → 25；
- **推理 / 性能工程师**：01 → 02 → 03 → 11 → 12 → 13 → 14 → 15 → 16 → 21 → 25；
- **RAG / Agent 应用工程师**：01 → 11 → 17 → 18 → 19 → 20 → 22 → 23 → 24；
- **平台 / SRE 工程师**：01 → 04 → 10 → 13 → 21 → 22 → 23 → 24 → 25；
- **架构师 / 决策者**：01 → 05 → 11 → 17 → 21 → 24 → 25。

### 9.7 每篇你可以期待得到什么

本系列每一篇都会围绕三件事展开：

1. **概念地图**：这一主题下必须知道的 10–20 个术语和它们的关系；
2. **工程决策**：遇到选型、配参时怎么判断，给出经验规则与量化参考；
3. **可执行片段**：代码或配置示例，尽量可以直接拷贝起跑。

我们会尽量避免两件事：

- 只翻译论文或官方文档；
- 只列 benchmark 而不解释它为什么这样。

### 9.8 术语表预览

系列贯穿使用的几十个术语，这里先给出高频 20 个，后续文章会在首次出现时再次注释：

|缩写|全称|含义|
|---|---|---|
|TP|Tensor Parallel|张量并行|
|PP|Pipeline Parallel|流水并行|
|DP|Data Parallel|数据并行|
|SP|Sequence Parallel|序列并行|
|EP|Expert Parallel|专家并行|
|CP|Context Parallel|上下文并行|
|ZeRO|Zero Redundancy Optimizer|优化器分片|
|FSDP|Fully Sharded Data Parallel|全分片数据并行|
|MFU|Model FLOPs Utilization|模型算力利用率|
|HFU|Hardware FLOPs Utilization|硬件算力利用率|
|TTFT|Time To First Token|首 token 时间|
|TPOT|Time Per Output Token|每 token 时间|
|KV Cache|Key-Value Cache|注意力 KV 缓存|
|MLA|Multi-head Latent Attention|多头潜在注意力|
|MoE|Mixture of Experts|专家混合|
|MTP|Multi-Token Prediction|多 token 预测|
|RAG|Retrieval Augmented Generation|检索增强生成|
|RLHF|Reinforcement Learning from Human Feedback|人类反馈强化学习|
|DPO|Direct Preference Optimization|直接偏好优化|
|MCP|Model Context Protocol|模型上下文协议|

## 十、一个最小可跑的「认识推理引擎」示例

为了让开篇不只停留在概念，给一个最小的 vLLM 示例，读完 11–13 篇后你会对每一行都更有感觉。

```
pip install "vllm>=0.6.0"
```

```
from vllm import LLM, SamplingParams

llm = LLM(
    model="Qwen/Qwen2.5-7B-Instruct",
    tensor_parallel_size=1,
    gpu_memory_utilization=0.9,
    max_model_len=8192,
    enforce_eager=False,
)

sp = SamplingParams(
    temperature=0.7,
    top_p=0.95,
    max_tokens=256,
)

prompts = [
    "用一句话解释 PagedAttention。",
    "列出 3 个训练与推理的工程差异。",
]
outputs = llm.generate(prompts, sp)
for o in outputs:
    print("===")
    print(o.prompt)
    print(o.outputs[0].text)
```

或以 OpenAI 兼容方式作为服务跑起来：

```
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-7B-Instruct \
  --tensor-parallel-size 1 \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.9 \
  --port 8000
```

```
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "messages": [{"role": "user", "content": "一句话解释 continuous batching"}],
    "stream": true
  }'
```

建议你在读后续每一篇的时候，都回到这个最小示例，用它验证新学的概念：TTFT 怎么测、KV 缓存多大、改 `--max-num-batched-tokens` 对吞吐的影响、切到 FP8 模型后显存下降多少，等等。

### 10.1 练习：测一次 TTFT 与 TPOT

把推理服务跑起来之后，用下面的脚本测自己的第一张”性能体检表”：

```
import time, requests, json

url = "http://localhost:8000/v1/chat/completions"
payload = {
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "messages": [{"role": "user", "content": "讲一个 300 字的分布式系统小故事"}],
    "stream": True,
    "max_tokens": 400,
}

t0 = time.time()
first_token_t = None
n_tokens = 0

with requests.post(url, json=payload, stream=True) as r:
    for line in r.iter_lines():
        if not line or not line.startswith(b"data: "):
            continue
        data = line[6:]
        if data == b"[DONE]":
            break
        chunk = json.loads(data)
        delta = chunk["choices"][0]["delta"].get("content", "")
        if delta:
            if first_token_t is None:
                first_token_t = time.time()
            n_tokens += 1

t_end = time.time()
ttft = (first_token_t - t0) * 1000
tpot = (t_end - first_token_t) / max(n_tokens - 1, 1) * 1000
print(f"TTFT = {ttft:.1f} ms, TPOT = {tpot:.1f} ms, tokens = {n_tokens}")
```

跑完后，尝试回答这几个问题：

1. TTFT 主要被什么决定？改长 prompt 后它怎么变？
2. 开 4 路并发与 1 路单请求相比，TPOT 是降了还是升了？为什么？
3. 切换 `max_num_batched_tokens` 参数，吞吐和 TPOT 怎么权衡？

这些问题的系统回答在第 11–13 篇。

### 10.2 练习：感受一次量化

```
pip install "vllm>=0.6.0" auto-gptq
```

把模型从 FP16 换到 AWQ / GPTQ 的 INT4 版本，对比：

- 显存占用下降多少？
- 吞吐提升多少？
- 质量有没有退化（用一个小 eval set）？

这正是第 14 篇会系统讲的”量化工程”的入口体验。

## 十一、本篇的几个关键判断

最后留下几条贯穿整个系列的观点，后续文章会反复回到它们：

1. **大模型基础设施是一个独立的工程学科**，套用传统后端经验会在显存、带宽、通信、故障模型上反复碰壁；
    
2. **工程创新正在取代硬件堆量成为主要降本手段**，FP8、MLA、MoE、PagedAttention、推测解码是过去两年最大的几处杠杆；
    
3. **推理侧的重要性会继续超过训练侧**：reasoning 模型让单次请求消耗的算力以 10 倍计增长，推理集群规模会成为 LLM 公司最大的基础设施；
    
4. **中国和全球的工程路径正在并轨又分岔**：架构上殊途同归（MoE + 长上下文 + 推理增强），生态上分化（昇腾 / 海光 / 摩尔线程 vs Nvidia，火山 / 阿里 / 百度 vs AWS / Azure / GCP）；
    
5. **开源基础设施已经足够撑起一个严肃的 LLM 平台**：vLLM + SGLang + LangGraph + Milvus + Langfuse + LiteLLM 这套组合在 2026 年足以覆盖绝大多数企业场景；
    
6. **可观测性决定你能不能活下来**：没有 token 级追踪、没有成本归因、没有评测回归，任何 LLM 平台都只是一个贵而脆的玩具。
    
7. **训练与推理正在工程上再次融合**：RLHF、推理时 reasoning、在线蒸馏、active learning 让”训练集群”和”推理集群”开始共享调度、共享数据通路；
    
8. **RAG 不会消失**：即使上下文窗口到了百万级，成本、可更新性和可解释性三个理由让 RAG 长期存在；
    
9. **Agent 是下一个真正改变形态的点**：它把 LLM 从”文本函数”变成”可以影响世界的进程”，对基础设施的要求是完全新的（沙箱、配额、审计、回滚）；
    
10. **国产替代是一个不得不面对的工程问题**：不是口号，是真实的采购约束，系列中会给出昇腾 / 海光 / 摩尔线程等栈的对比视角。
    

### 11.1 给读者的三个行动建议

如果你是第一次认真学这套栈，建议下一步：

1. **手跑一次 vLLM**（第十节的例子），亲自感受 TTFT / TPOT；
2. **挑一个你本职最相关的角色路径**（9.6 节），按顺序读下去，别跳；
3. **建一个自己的 benchmark 集**：哪怕只有 20 个 prompt，坚持记录不同模型、不同引擎、不同配置下的延迟与质量，这会成为你未来所有决策的基础。

如果你已经在做 LLM 平台：

1. 花一周时间盘一遍自己的**成本结构**（按模型 / 租户 / 场景），这通常会直接指出最大的优化空间；
2. 花一周时间盘一遍自己的**可观测性**，确认能回答”上周这个业务花了多少 token、p95 TTFT 是多少、失败都是什么原因”；
3. 再花一周时间盘一遍自己的**故障剧本**，确认关键组件（推理引擎、向量库、网关）在节点失效、依赖抖动、模型替换时都有预案。

## 参考资料

- vLLM: Easy, Fast, and Cheap LLM Serving with PagedAttention, UC Berkeley, 2023。
- DeepSeek-V3 Technical Report, DeepSeek-AI, 2024。
- LLaMA 3 Herd of Models, Meta AI, 2024。
- Gemini 1.5 / 2.5 Technical Reports, Google DeepMind。
- Anthropic Claude 3 / 3.5 / 3.7 Model Cards。
- OpenAI o1 / o3 System Cards。
- Stanford HAI AI Index Report 2024 / 2025。
- Epoch AI, Training Compute of Frontier AI Models。
- Qwen2.5 / Qwen3 Technical Reports, Alibaba。
- GLM-4.5 Technical Report, Zhipu AI。
- MoonshotAI Kimi K1.5 / K2 Reports。
- Hugging Face Open LLM Leaderboard 与 Inference 报告。
- SGLang: Efficient Execution of Structured Language Model Programs。
- TensorRT-LLM、Text Generation Inference、lmdeploy 官方文档。
- Langfuse / LangSmith / Helicone / Arize Phoenix 官方文档。
- LiteLLM / OneAPI / Portkey 官方文档。
- DeepSeek-R1 技术报告，DeepSeek-AI，2025。
- FlashAttention-2 / FlashAttention-3，Tri Dao 等。
- Megatron-LM 与 NVIDIA NeMo-Framework 文档。
- Hopper / Blackwell 架构白皮书，NVIDIA。
- 昇腾 CANN / MindSpore / MindIE 官方资料。
- 阿里云 PAI、火山引擎 veMLP、百度千帆、华为 ModelArts 官方文档。

---

**下一篇**：[GPU 计算入门：SM、Tensor Core、HBM、NVLink](https://quant67.com/post/llm-infra/02-gpu-primer/02-gpu-primer.html)

## 同主题继续阅读

把当前热点继续串成多页阅读，而不是停在单篇消费。

2026-04-22 · architecture / ai-infra

### [大模型基础设施工程](https://quant67.com/post/llm-infra/index.html)

面向中国工程团队的大模型基础设施系列。从 GPU/CUDA/互联、训练框架与 3D 并行、vLLM/SGLang 推理引擎、量化与推测解码、RAG/Agent 到服务化、网关、可观测性与安全合规，覆盖 LLMOps 全链路。

2026-04-25 · architecture / ai-infra

### [【大模型基础设施工程·特别篇】DeepSeek-V4 与国产芯片：从备份路线到主路径](https://quant67.com/post/llm-infra/26-deepseek-v4-domestic-chip/26-deepseek-v4-domestic-chip.html)

DeepSeek-V4 发布后，如果国产芯片已经支撑旗舰模型的关键训练或推理链路，它会怎样影响 NVIDIA 生态、国产 AI 芯片、云厂商、模型团队和工程师的技术选择？

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】05：训练全景：Pre-train、SFT、RLHF、DPO、蒸馏](https://quant67.com/post/llm-infra/05-training-overview/05-training-overview.html)

以工程视角串联现代 LLM 的四阶段训练栈——预训练、中训、SFT 与对齐——覆盖数据、Tokenizer、优化器、精度、Scaling Law 与代表性训练框架。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】11：推理引擎基础](https://quant67.com/post/llm-infra/11-inference-basics/11-inference-basics.html)

从 Prefill/Decode 两阶段、KV Cache、Continuous Batching 到 PD 分离，系统讲清楚大模型推理的工程基础。