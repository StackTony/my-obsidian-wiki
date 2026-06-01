上一篇 [12：PagedAttention 与 Continuous Batching](https://quant67.com/post/llm-infra/12-paged-continuous/12-paged-continuous.html) 从机制层讲清了现代推理引擎的两块基石。本篇把视角拉回产品层：当一家公司要把一个 70B 级别的模型真正推到线上，**到底该选哪个引擎**？本文覆盖 vLLM、SGLang、TensorRT-LLM、TGI、LMDeploy、MindIE、llama.cpp / Ollama、DeepSpeed-MII 八大家族，从架构、性能、生态、部署模式、量化、结构化输出、多模态、社区活跃度等维度做横向拆解，最后给出一套”按硬件 × 场景”的选型决策树。

下图用 SVG 概括四大主流引擎 + 国产 + 端侧在”硬件层 / 核心优化 / 服务层”的分布。

## 一、引擎全景

![引擎全景](https://quant67.com/post/llm-infra/13-vllm-sglang/images/13-vllm-sglang-fig1.svg)

### 1.1 八大家族速览

    
|引擎|主导方|首发|定位|License|
|---|---|---|---|---|
|vLLM|UC Berkeley Sky Lab → 社区（PyTorch Foundation 托管）|2023-06|开源事实标准|Apache-2.0|
|SGLang|LMSYS → xAI、DeepSeek 重度使用|2024-01|高性能 + 结构化输出|Apache-2.0|
|TensorRT-LLM|Nvidia|2023-10|Nvidia 极致性能|Apache-2.0（含闭源 kernel）|
|TGI（Text Generation Inference）|HuggingFace|2022-11|早期事实标准，现回退企业内场景|Apache-2.0（1.x 一度 HFOIL）|
|LMDeploy|上海 AI Lab（InternLM 团队）|2023-06|国产对标 vLLM|Apache-2.0|
|MindIE|华为|2024|昇腾 NPU 专用|闭源商业|
|llama.cpp / Ollama|ggerganov / Ollama 团队|2023-03|端侧、CPU、Mac|MIT|
|DeepSpeed-MII|微软|2022-11|与 DeepSpeed 训练栈配套|Apache-2.0|

此外还有： - **MLX-LM**：Apple Silicon 原生； - **ExLlamaV2**：社区量化推理引擎，面向单卡大模型； - **Aphrodite-engine**：vLLM 分支，加了更多 sampler； - **Nim（Nvidia）**：在 TensorRT-LLM 之上的容器化产品封装； - **RTP-LLM、rtp-llm（阿里）**、**FasterTransformer（Nvidia 已归档）**； - **TGI 的接替品 text-generation-launcher**，HF 内部仍维护。

### 1.2 为什么这么多引擎

推理栈本质是 “模型前向 + KV cache + 调度 + 通信 + 服务化” 的组合。每个环节都可能被不同团队优化到极致：

- Nvidia 垄断 GPU → TensorRT-LLM 深度绑定 CUDA / cuBLAS / cuDNN / NCCL，允许使用闭源 kernel；
- 学术界 / 社区要跨硬件、要 hackable → vLLM、SGLang 走纯 PyTorch + Triton 路线；
- 云厂 / 大模型厂要定制调度、要做 PD 分离 → 基于 vLLM / SGLang fork；
- 端侧场景内存 / 指令集完全不同 → llama.cpp 走 CPU + Metal + GGUF；
- 国产 NPU 没有 CUDA → MindIE、MindFormers 单独一套。

### 2.1 架构要点

vLLM 的核心是 **PagedAttention + Continuous Batching**（上一篇详述）。v0 版本是经典 block-level KV 管理；2024 下半年开始的 **v1 架构**（2025 正式成为默认）做了几项关键重构：

- **Scheduler 与 Worker 解耦**：engine core 进程专管调度与 block 分配，worker 进程只做前向；
- **Chunked prefill 默认打开**：把长 prompt 切块与 decode 混跑，消除首 token 长尾；
- **Prefix caching 默认打开**：系统 prompt、RAG context 自动复用；
- **OpenAI 兼容 server 完整化**：`/v1/chat/completions`、`/v1/embeddings`、`/v1/rerank`、tool-call、reasoning content（DeepSeek-R1、QwQ）；
- **多模态统一 IO**：Qwen-VL、LLaVA、Phi-Vision、Pixtral、InternVL 均走同一 `multi_modal_data` 接口；
- **Speculative decoding 重构**：支持 draft model、Medusa、MLP / Eagle、n-gram；
- **Spec+PD 分离**：基于 `NIXL` / `MoonCake-style transfer` 的 P-D 解耦实验特性。

### 2.2 生态位

vLLM 已成为绝大多数开源项目默认后端：

- **Ray Serve**、**KServe**、**BentoML**、**Triton (vLLM backend)** 都有官方集成；
- **SkyPilot** 一行 `sky serve up vllm.yaml` 即可上云；
- **Hugging Face** 文本模型发布页多数都附一段 `vllm serve` 命令；
- 国内 **阿里 PAI-EAS、火山方舟、百度千帆** 在自托管模式下大量基于 vLLM fork；
- **xAI Grok 早期、DeepSeek API、Qwen API、Moonshot Kimi** 都公开或半公开承认生产环境使用 vLLM 或其 fork。

### 2.3 启动示例

```
# 单机 4 卡 TP，Qwen2.5-7B-Instruct
pip install vllm==0.8.0

vllm serve Qwen/Qwen2.5-7B-Instruct \
  --tensor-parallel-size 4 \
  --gpu-memory-utilization 0.92 \
  --max-model-len 32768 \
  --enable-prefix-caching \
  --enable-chunked-prefill \
  --served-model-name qwen2.5-7b \
  --port 8000
```

调用：

```
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-7b",
    "messages": [{"role":"user","content":"用一句话解释 PagedAttention"}],
    "max_tokens": 128
  }'
```

## 三、SGLang：后起之秀

### 3.1 核心创新

SGLang（Structured Generation Language）最初是 LMSYS 团队为复杂 prompt 结构（多轮、多分支、工具调用）设计的 DSL，后来逐渐把底层 runtime 单独抽出成一个高性能推理引擎。关键点：

- **RadixAttention**：用 radix tree 组织所有历史请求的 KV cache，前缀自动共享。对 system prompt、few-shot、RAG context、多轮对话的命中率远超 vLLM 经典 prefix caching；
- **Token Attention + FlashInfer**：与 FlashInfer 深度绑定，attention kernel 常年领先；
- **Zero-overhead batch scheduler**：Python 调度器 + CUDA graph + overlap scheduling，把 scheduling overhead 压到接近 0；
- **结构化输出**：集成 **xgrammar**（LMSYS 自研的 GBNF 解析 + token mask 生成器），JSON / 正则 / EBNF 约束生成的吞吐损失 <5%，远好于 outlines 动态 FSM；
- **DeepSeek-V3 / R1 官方推荐**：DeepSeek 团队 repo 里直接给 SGLang 启动脚本，MLA、DP attention、EP（Expert Parallelism）在 SGLang 上最先落地；
- **PD 分离原生**：从 2025 年开始支持 prefill / decode 分离，内置 Mooncake transfer engine。

### 3.2 启动示例

```
pip install "sglang[all]"

python -m sglang.launch_server \
  --model-path Qwen/Qwen2.5-7B-Instruct \
  --tp 4 \
  --mem-fraction-static 0.9 \
  --context-length 32768 \
  --enable-torch-compile \
  --port 30000
```

OpenAI 兼容调用：

```
curl http://localhost:30000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "default",
    "messages": [{"role":"user","content":"输出 JSON: {\"city\":\"Beijing\"}"}],
    "response_format": {
      "type": "json_schema",
      "json_schema": {
        "name": "city_info",
        "schema": {"type":"object","properties":{"city":{"type":"string"}},"required":["city"]}
      }
    }
  }'
```

### 3.3 SGLang vs vLLM 设计哲学差异

  
|维度|vLLM|SGLang|
|---|---|---|
|KV 组织|block table（hash 前缀匹配）|radix tree（前缀共享粒度 = 任意长度）|
|Attention kernel|FlashAttention-2/3、FlashInfer 可选|FlashInfer 为主，紧密耦合|
|调度 overhead|每步 Python 调度|CUDA graph + overlap，接近 0|
|结构化输出|outlines / xgrammar / guided decoding|xgrammar 原生，性能最好|
|Python API|偏”服务器 + REST”|提供 `sgl.function` 前端 DSL|
|社区规模|最大|增速最快|

## 四、TensorRT-LLM：Nvidia 极致性能

### 4.1 架构与定位

TensorRT-LLM 建在 **TensorRT** 之上，本质是一个”为 LLM 特化的编译栈”：

- **Builder → Engine**：把模型编译成 `.engine` plan file，针对 SM 架构（SM80/SM89/SM90/SM100）生成对应 kernel；
- **Custom plugins**：MHA / Paged KV / MoE / quantization 均有手写 CUDA plugin；
- **In-flight batching（IFB）**：等价于 vLLM 的 continuous batching；
- **Paged KV cache**：TRT-LLM 自己的 paged 实现，block size 可配；
- **FP8 first-class**：Hopper 上的 FP8 通路最完整，E4M3 权重 + FP8 GEMM + FP8 KV cache；
- **Triton Inference Server backend**：`tensorrtllm_backend` 提供 gRPC / HTTP 服务化；
- **Nvidia Nim**：在 TRT-LLM 之上的商业化容器镜像。

### 4.2 优势与代价

**优势**：

- Nvidia 硬件上的 **延迟与吞吐天花板**，Hopper / Blackwell 上尤其明显；
- 官方支持 FP8、NVFP4、SmoothQuant、AWQ、GPTQ 多种量化；
- Speculative decoding、Medusa、Eagle、ReDrafter 官方实现；
- 与 Triton 无缝对接，企业部署栈完善。

**代价**：

- 需要”编译”步骤，模型改动、精度切换、TP 大小变更都要重编译；
- 对新模型结构支持滞后于 vLLM / SGLang 约 1–4 周；
- 部分 kernel 闭源（NGC 二进制），调试困难；
- 仅支持 Nvidia，没有跨硬件可能性。

### 4.3 启动示例

```
# 1. 转换权重
python convert_checkpoint.py \
  --model_dir Qwen2.5-7B-Instruct \
  --output_dir ./ckpt \
  --dtype bfloat16 \
  --tp_size 4

# 2. 编译引擎
trtllm-build \
  --checkpoint_dir ./ckpt \
  --output_dir ./engines/qwen2.5-7b-tp4 \
  --gemm_plugin bfloat16 \
  --max_batch_size 256 \
  --max_input_len 30000 \
  --max_seq_len 32768 \
  --use_paged_context_fmha enable

# 3. 通过 Triton 启动
tritonserver --model-repository=./triton_model_repo
```

## 五、TGI：先驱者的退场

### 5.1 简史

TGI 是 HuggingFace 2022 年底推出的推理服务，在 vLLM 出现之前是开源界唯一能把 LLaMA、BLOOM 这类模型高效服务化的选择。功能上：

- Continuous batching（叫 “rolling batch”）；
- Flash Attention、Paged Attention（晚于 vLLM 接入）；
- 量化：bitsandbytes、GPT-Q、EETQ、AWQ、Marlin；
- Rust HTTP server + Python worker，性能稳定。

### 5.2 为什么式微

- 2023 年底一度改 license 为 **HFOIL**（禁止商业竞品使用），生态受伤严重；
- 随后虽改回 Apache-2.0，但主力用户已迁至 vLLM；
- 功能迭代节奏慢于 vLLM（尤其在 MoE、多模态、speculative decoding、结构化输出上）；
- HF 内部产品线 `text-generation-inference` 与 `text-embeddings-inference`、`text-generation-router` 依然活跃，但更多是 **HF Inference Endpoints 服务内部使用**，不再是社区默认。

结论：2025 年的新项目，除非已经在 HF Endpoints 上，否则无强理由选 TGI。

## 六、LMDeploy / MindIE / 端侧引擎

### 6.1 LMDeploy（上海 AI Lab）

LMDeploy 是国产开源引擎中最完整的一个：

- **TurboMind 后端**：手写 C++/CUDA kernel，对 InternLM、Qwen、Llama 支持良好，小并发延迟极好；
- **PyTorch 后端**：面向新模型快速适配；
- **W4A16 / W8A8 / AWQ / SmoothQuant / FP8** 量化齐全；
- 工具链：`lmdeploy chat`、`lmdeploy serve`、`lmdeploy lite`（量化校准）。

使用体验上，TurboMind 在 A100 / H800 单机 7B 模型小并发场景延迟优于 vLLM 默认配置；但大并发、新模型支持速度不如 vLLM。

### 6.2 MindIE（华为昇腾）

MindIE 是 **昇腾 910B / 910C / 310P** 上的唯一商业推理引擎，闭源：

- 对标 vLLM，提供 OpenAI 兼容 API；
- 依赖 CANN / ATB（Ascend Transformer Boost）底层；
- 支持 Qwen、Llama、DeepSeek 系列；
- 在华为 Atlas 推理服务器、银行 / 运营商私有云中是事实标准；
- 新模型适配需华为团队配合，社区贡献通道有限。

对一般开发者：没有昇腾卡不用关心；有昇腾卡则基本只能用 MindIE（或 MindFormers）。

### 6.3 llama.cpp / Ollama / MLX

- **llama.cpp**：纯 C/C++，CPU + CUDA + Metal + Vulkan + SYCL + HIP 全后端；GGUF 格式是端侧量化事实标准；
- **Ollama**：llama.cpp 之上的包管理 + daemon + OpenAI API，面向开发者笔电；
- **MLX-LM**：Apple Silicon 原生（统一内存 + Metal），在 M 系列芯片上比 llama.cpp Metal 后端快 1.5–2×；
- **LM Studio / Jan**：GUI 包装。

端侧场景下选型基本就是：Mac 用 Ollama 或 MLX，Windows / Linux 桌面用 Ollama，嵌入式用 llama.cpp 直接编译。

### 6.4 DeepSpeed-MII

微软出品，与 DeepSpeed-Inference 一脉相承，支持 ZeRO-Inference、张量并行、混合精度。优势在于能直接吃 DeepSpeed 训练产物，但社区活跃度早已落后 vLLM，生产部署不推荐作为首选。

## 七、核心技术对照

### 7.1 KV cache 管理

    
|引擎|机制|前缀共享|粒度|多租户隔离|
|---|---|---|---|---|
|vLLM v1|Block table + hash prefix caching|系统 prompt 级别|block（16 / 32 token）|靠 request id|
|SGLang|**Radix tree**（RadixAttention）|任意前缀|token|tree 节点自然隔离|
|TensorRT-LLM|Paged KV + 可选 prefix reuse|有限前缀复用|block|Triton session|
|TGI|Paged（借鉴 vLLM）|有限|block|session|
|LMDeploy|Block（TurboMind 自研）|系统 prompt|block|session|

RadixAttention 的直观优势：同一系统 prompt 下 1000 个用户的上下文，SGLang 仅需保留一份前缀 KV；vLLM 如果 prompt hash 不同（例如 few-shot 略有差异），则可能退化为各自独立存储。

### 7.2 Scheduling

- **vLLM**：continuous batching，v1 默认 chunked prefill；调度在 engine core 进程；
- **SGLang**：radix-aware scheduling + overlap（把 CPU 调度与 GPU 前向 overlap）+ CUDA graph；长输入会自动拆块；
- **TensorRT-LLM**：in-flight batching，C++ runtime 实现，调度极低开销但灵活性差；
- **TGI**：rolling batch，功能比较基础。

### 7.3 Attention kernel

  
|引擎|默认 kernel|备选|
|---|---|---|
|vLLM|FlashAttention-2/3（prefill），FlashInfer / xFormers（decode）|Triton attention、custom CUDA|
|SGLang|FlashInfer 全程|Triton|
|TensorRT-LLM|TRT-LLM 自研 MHA plugin（闭源为主）|-|
|TGI|Flash Attention|Paged attention kernel|

FlashInfer 已成为开源引擎的共同依赖，其 page attention、append attention、MLA、cascade inference 都是业界最快实现之一。

### 7.4 量化支持

|量化方案|vLLM|SGLang|TRT-LLM|LMDeploy|llama.cpp|
|---|---|---|---|---|---|
|FP16/BF16|Y|Y|Y|Y|Y|
|FP8 (E4M3/E5M2)|Y (Hopper+)|Y|Y|Y (Hopper)|部分|
|INT8 SmoothQuant|Y|Y|Y|Y|-|
|AWQ (W4A16)|Y|Y|Y|Y|-|
|GPTQ|Y|Y|Y|Y|-|
|GGUF (Q4_K_M 等)|部分|-|-|-|**原生**|
|NVFP4 / MXFP4|Y (Blackwell)|Y|Y|早期|-|
|INT4 weight-only (Marlin)|Y|Y|-|-|-|

> 注：量化方案细节与校准方法将在 [14 量化工程](https://quant67.com/post/llm-infra/14-quantization/14-quantization.html) 中展开。

### 7.5 推测解码（Speculative Decoding）

|方法|vLLM|SGLang|TRT-LLM|
|---|---|---|---|
|Draft model|Y|Y|Y|
|Medusa|Y|Y|Y|
|Eagle / Eagle-2 / Eagle-3|Y|Y|Y|
|MLP / ReDrafter|部分|Y|Y|
|N-gram / Prompt lookup|Y|Y|部分|
|MTP（DeepSeek-V3 multi-token prediction）|Y|**Y（首发）**|部分|

SGLang 与 DeepSeek 紧密合作，DeepSeek-V3 / R1 的 MTP 层最早在 SGLang 落地；vLLM 紧随其后。推测解码细节留给 [15 Speculative & MTP](https://quant67.com/post/llm-infra/15-speculative-mtp/15-speculative-mtp.html)。

## 八、部署模式

### 8.1 单机单卡 / 多卡（TP）

- 7B 级别：单张 A10 / L20 / RTX 4090（24GB）足够，INT4 甚至能塞到 12GB；
- 32B 级别：2–4 卡 TP，bfloat16 需 ~64GB；
- 70B 级别：4–8 卡 TP，FP8 能压到 4 卡 H100；
- 200B+ MoE（DeepSeek-V3 671B、Qwen2-MoE）：必须多机 + EP（Expert Parallelism）+ DP + TP 组合。

### 8.2 多机（TP × PP × EP）

- **TP（Tensor Parallel）**：每层算子拆到多卡，对 NVLink / NVSwitch 带宽敏感；
- **PP（Pipeline Parallel）**：按层拆到多机，推理场景收益小（bubble + 延迟），通常只用于超大模型；
- **EP（Expert Parallel）**：MoE 专家拆到多卡多机，SGLang 与 vLLM 近期都已支持；
- **DP attention**：DeepSeek-V3 风格，attention 层走数据并行以避开 TP 的 KV 重复。

### 8.3 PD 分离（Prefill / Decode Disaggregation）

PD 分离是 2024–2025 年最大的一项架构演进，核心观察：prefill 是 compute-bound，decode 是 memory-bound，放一起互相踩踏。代表实现：

- **DistServe**（北大）：论文最早提出 PD 分离；
- **Mooncake**（月之暗面）：生产级 KV cache 池 + P/D 解耦 + 分布式调度，开源 `mooncake-transfer-engine`；
- **vLLM v1 的 disagg 支持**：通过 `KVConnector` 抽象接入 Mooncake / NIXL；
- **SGLang PD**：原生内置，启动时通过 `--disaggregation-mode prefill|decode`；
- **TRT-LLM**：Nvidia 在 2024Q4 后也放出 PD 分离 reference。

架构图（Mermaid）：

### 8.4 请求在各引擎的流转

## 九、生态 / 服务器

### 9.1 OpenAI 兼容 API

四大引擎都实现 OpenAI 兼容端点，但细节差异不可忽视：

    
|能力|vLLM|SGLang|TRT-LLM (Triton)|TGI|
|---|---|---|---|---|
|`/v1/chat/completions`|Y|Y|Y（自定义）|Y|
|Tool calling（function_call）|Y（多 parser：hermes / llama3 / qwen / mistral）|Y|需自行解析|部分|
|Reasoning content（DeepSeek-R1 思维链分离）|Y|Y|部分|N|
|Structured output（JSON schema）|Y（xgrammar / outlines / lm-format-enforcer）|Y（xgrammar 原生）|Y（XGrammar / Outlines 插件）|部分|
|Vision / 多模态|Y|Y|部分|部分|
|Embedding / rerank|Y|Y|需另起模型|另有 TEI|

### 9.2 服务化框架

- **Nvidia Triton Inference Server**：支持 TRT-LLM backend、vLLM backend、Python backend；企业 ops 栈成熟；
- **KServe**（Kubernetes）：通过 InferenceService CRD 托管 vLLM / TGI / TRT-LLM；
- **Ray Serve**：vLLM 官方集成，支持多副本调度 + 自动扩缩容；
- **BentoML**：简化 Python-first 打包；
- **SkyPilot**：跨云拉 spot 实例；
- **国产**：阿里 PAI-EAS、火山方舟、百度千帆、腾讯 TI-ONE 都内置 vLLM / SGLang / TRT-LLM 镜像。

## 十、性能对比

### 10.1 公开 benchmark 数据（综合）

以下是综合 Anyscale、HF、LMSYS、Nvidia 2024Q4–2025Q1 公开数据在 Llama-3 8B / 70B、H100 SXM 下的相对结论（数字仅用于定量级比较，实际以业务负载为准）：

    
|场景|vLLM v1|SGLang|TRT-LLM|TGI|
|---|---|---|---|---|
|8B, 1×H100, 单并发 TTFT|1.0×|0.9×|**0.75×**|1.3×|
|8B, 1×H100, 32 并发 吞吐|1.0×|**1.05×**|1.15×|0.7×|
|70B, 4×H100 TP4, 32 并发 吞吐|1.0×|**1.1×**|1.2×|0.65×|
|长 prompt（16k，RAG）|1.0×|**1.4×**（RadixAttention）|1.1×|0.8×|
|FP8 70B 吞吐|1.0×|1.05×|**1.25×**|-|
|JSON 结构化输出 吞吐|1.0×（outlines）|**1.3×**（xgrammar）|1.1×|0.6×|

定性结论：

- **极致延迟 / 极致吞吐**：TRT-LLM（尤其 FP8、Hopper / Blackwell）；
- **长前缀 / RAG / 多轮**：SGLang（RadixAttention）；
- **通用 / 生态 / 适配新模型**：vLLM；
- **企业 HF 深度用户**：TGI 仍可用，新项目不推荐。

### 10.2 真实负载下的陷阱

公开 benchmark 常在”定长输入 + 定长输出”下测，而生产负载是重尾分布：

- 少量 long context（代码 / 文档问答）会拖垮 batch，需要 chunked prefill + PD 分离；
- tool-call 多轮会放大每轮调度开销，SGLang 与 vLLM v1 的 overlap scheduler 在这种场景优势明显；
- 多模态请求（图像 token 很多）会打爆 KV 预算，需要单独限流。

## 十一、选型决策

### 11.1 决策树

```
硬件？
 ├─ Nvidia GPU
 │    ├─ 追求极致延迟 / 已用 Triton / 商业闭源可接受 → TensorRT-LLM
 │    ├─ 追求开源可 hack / 新模型最快适配 → vLLM
 │    ├─ 结构化输出密集 / 长前缀 / DeepSeek 生态 → SGLang
 │    └─ 已在 HF Endpoints → TGI
 ├─ 华为昇腾 → MindIE（必选）
 ├─ AMD ROCm → vLLM（官方支持最好）/ SGLang（逐步跟进）
 ├─ Intel Gaudi / Habana → vLLM-fork-gaudi / Optimum
 ├─ Apple Silicon → MLX-LM / Ollama
 └─ CPU / 嵌入式 / 端侧 → llama.cpp / Ollama

模型规模？
 ├─ ≤13B，单机单卡 → 以上任一
 ├─ 30–70B，单机多卡 TP → vLLM / SGLang / TRT-LLM 均可
 ├─ 100B+ MoE → SGLang（EP + DP attention 最完善）/ vLLM v1
 └─ 超长上下文（128k+）→ SGLang / vLLM + PD 分离

约束？
 ├─ 强合规 / 信创 / 国产化 → LMDeploy / MindIE
 ├─ 低代码 / 快速 PoC → Ollama + OpenAI 兼容 API
 └─ 需要自定义调度 / 研究 → vLLM / SGLang（Python 层可改）
```

### 11.2 常见组合拳

- **vLLM + Ray Serve + KServe**：云原生最主流；
- **TRT-LLM + Triton + Nim**：Nvidia 全家桶，企业包；
- **SGLang + Mooncake**：Kimi / DeepSeek 风格 PD 分离大规模部署；
- **LMDeploy TurboMind + Nginx**：私有化小并发；
- **Ollama**：个人 / 小团队内部工具。

## 十二、工程经验与陷阱

### 12.1 关键参数调优

**vLLM**：

```
--gpu-memory-utilization 0.90   # 留 ~10% 给 CUDA workspace；太高易 OOM
--max-model-len 32768           # 超过训练长度会数值不稳
--max-num-seqs 256              # 并发上限
--max-num-batched-tokens 8192   # 单 step token 预算；决定 TTFT vs 吞吐
--enable-chunked-prefill        # v1 默认开
--enable-prefix-caching         # v1 默认开
--kv-cache-dtype fp8            # Hopper 上 2× KV 容量
--swap-space 16                 # CPU swap（v0 遗留，v1 建议 0）
--quantization awq              # or fp8 / gptq / bitsandbytes
```

**SGLang**：

```
--mem-fraction-static 0.88
--context-length 32768
--max-running-requests 256
--schedule-policy lpm           # longest-prefix-match，RadixAttention 配套
--enable-torch-compile          # 首次启动慢，稳态吞吐 +10%
--attention-backend flashinfer
--enable-dp-attention           # DeepSeek-V3 类场景
--disaggregation-mode null|prefill|decode
```

**TensorRT-LLM**：

```
# build 时
--max_batch_size 256
--max_input_len 30000
--max_seq_len 32768
--max_num_tokens 16384          # paged ctx fmha 关键参数
--use_paged_context_fmha enable
--use_fp8_context_fmha enable   # Hopper
--gemm_plugin fp8 / bfloat16
--gather_generation_logits      # speculative / logprobs 需要
```

### 12.2 多模态 / 工具调用常见坑

- **多模态**：图像 token 数随分辨率指数增长（Qwen-VL `min_pixels / max_pixels`、InternVL `dynamic patch`），需在 gateway 层限流；
- **Tool calling**：不同模型 tool schema 不同（hermes、qwen、mistral、llama3、deepseek），vLLM `--tool-call-parser` / SGLang `--tool-call-parser` 需对应选择；
- **Reasoning content**：DeepSeek-R1、QwQ 的 `<think>` 段需要用 `--reasoning-parser deepseek_r1` 拆出，否则前端会把思考链当成回答显示；
- **Prefix caching 与采样**：`temperature=0` + 长 system prompt 时 prefix 命中最高；但 `seed` 变化会让结果散开，影响调试；
- **Chunked prefill 的尾延迟**：开启后平均 TTFT 降低但 p99 可能升高，需业务观测。

### 12.3 观测指标

- 系统侧：GPU 利用率、SM 活跃度、HBM 带宽、NVLink 流量；
- 引擎侧：`num_running`、`num_waiting`、`gpu_cache_usage_perc`、`prefix_cache_hit_rate`、`time_to_first_token`、`time_per_output_token`、`prompt_throughput`、`generation_throughput`；
- 业务侧：按 route / 模型 / 租户拆分的 QPS、p50/p95/p99 延迟、token 成本。

vLLM 与 SGLang 均暴露 Prometheus `/metrics`，直接接 Grafana 即可，具体 dashboard 与 SLO 设计在 [23 可观测性](https://quant67.com/post/llm-infra/23-observability/23-observability.html) 展开。

## 十三、代码：同一 Qwen-7B 同时用 vLLM 与 SGLang 服务

目标：在同一台 4×H100 机器上，用 vLLM 起 `:8000`，SGLang 起 `:30000`，用同一脚本压测比较。

### 13.1 启动

```
# 终端 1：vLLM
CUDA_VISIBLE_DEVICES=0,1,2,3 \
vllm serve Qwen/Qwen2.5-7B-Instruct \
  --tensor-parallel-size 4 \
  --gpu-memory-utilization 0.90 \
  --max-model-len 32768 \
  --enable-prefix-caching \
  --enable-chunked-prefill \
  --served-model-name qwen \
  --port 8000

# 终端 2：SGLang（另一台机器或另一组 4 卡）
CUDA_VISIBLE_DEVICES=4,5,6,7 \
python -m sglang.launch_server \
  --model-path Qwen/Qwen2.5-7B-Instruct \
  --tp 4 \
  --mem-fraction-static 0.88 \
  --context-length 32768 \
  --enable-torch-compile \
  --schedule-policy lpm \
  --port 30000
```

### 13.2 统一压测脚本

```
import asyncio, time, httpx, statistics, random

PROMPTS = [
    "用一句话解释 PagedAttention。",
    "写一个 Python 函数反转字符串。",
    "解释 RadixAttention 与 PagedAttention 的关键差异。",
    "写一首五言绝句描写推理引擎。",
]

async def one(client, url, model):
    p = random.choice(PROMPTS)
    t0 = time.time()
    r = await client.post(url, json={
        "model": model,
        "messages": [{"role":"user","content": p}],
        "max_tokens": 256,
        "temperature": 0.0,
    }, timeout=120)
    dt = time.time() - t0
    n = r.json()["usage"]["completion_tokens"]
    return dt, n

async def bench(url, model, concurrency=64, total=512):
    async with httpx.AsyncClient() as client:
        sem = asyncio.Semaphore(concurrency)
        async def wrap():
            async with sem:
                return await one(client, url, model)
        results = await asyncio.gather(*[wrap() for _ in range(total)])
    latencies = [x[0] for x in results]
    tokens = sum(x[1] for x in results)
    elapsed = max(latencies)
    print(f"{url}: p50={statistics.median(latencies):.2f}s "
          f"p95={sorted(latencies)[int(len(latencies)*0.95)]:.2f}s "
          f"throughput={tokens/elapsed:.1f} tok/s")

if __name__ == "__main__":
    asyncio.run(bench("http://localhost:8000/v1/chat/completions", "qwen"))
    asyncio.run(bench("http://localhost:30000/v1/chat/completions", "default"))
```

在笔者测试的典型场景（4×H100、concurrency=64、短 prompt 长回答）下，两者吞吐差距在 ±10% 以内；一旦加大 system prompt 到 2k token 并保持 64 并发，SGLang 吞吐领先 30–50%，这正是 RadixAttention 的主战场。

## 十四、社区现状与趋势

### 14.1 贡献者与 governance

- **vLLM**：2024 年 11 月正式加入 PyTorch Foundation 管理，贡献者超过 900 人，主要 maintainer 来自 UC Berkeley、Anyscale、Roblox、NeuralMagic / Red Hat、Nvidia、Meta、Google 等；
- **SGLang**：LMSYS 发起，xAI、DeepSeek、NovaSky、Berkeley Sky 深度参与，贡献者约 400+；
- **TRT-LLM**：Nvidia 自研，外部贡献主要集中在模型适配与 bug 修复；
- **TGI**：HF 内部维护，外部 PR 接受度有所下降。

### 14.2 趋势判断

1. **vLLM 仍将是开源事实标准**：生态最广、文档最全、云厂默认；
2. **SGLang 会在”大规模生产部署”方向继续领先**：PD 分离、MTP、结构化输出；
3. **两者正在相互抄作业**：chunked prefill、prefix caching、radix 化 block table、xgrammar 集成都在双向流动；
4. **TRT-LLM 会保持”Nvidia 旗舰硬件天花板”**，但在非 Nvidia 场景不存在；
5. **国产引擎（LMDeploy、MindIE、RTP-LLM）** 会在信创与自有模型生态里守住阵地，但不会成为国际主流；
6. **端侧 llama.cpp / MLX / Ollama** 会随着小模型（3B / 1B）能力上升变得越来越重要，催生”端云协同”架构。

## 十五、深入：两个引擎 Python 代码路径对照

为了把”架构差异”落到”代码差异”，下面用高度简化的伪代码对比 vLLM v1 与 SGLang 在一次请求生命周期内的关键路径。

### 15.1 vLLM v1：请求落入 EngineCore

```
# 简化版 vllm/v1/engine/core.py
class EngineCore:
    def __init__(self, ...):
        self.scheduler = Scheduler(...)       # continuous batching
        self.kv_cache_manager = KVCacheManager(block_size=16)
        self.model_executor = ModelExecutor(...)

    def add_request(self, req):
        # 1. prefix hash 查找 block 复用
        hits, new_blocks = self.kv_cache_manager.allocate(req)
        req.block_table = hits + new_blocks
        self.scheduler.waiting.append(req)

    def step(self):
        # 2. 组 batch：waiting -> running，chunked prefill 混合 decode
        running, scheduled_tokens = self.scheduler.schedule()
        # 3. 前向
        logits = self.model_executor.execute(running, scheduled_tokens)
        # 4. 采样 + guided decode mask
        tokens = sample_with_guidance(logits, running)
        # 5. 回写 KV，step 计数
        for r, t in zip(running, tokens):
            r.append_token(t)
            if r.is_finished():
                self.kv_cache_manager.free(r)
```

核心抽象：`Request → BlockTable → 固定 block_size 的 KV 页`。prefix caching 做 block 级哈希（16 或 32 token 对齐）。

### 15.2 SGLang：请求落入 TokenizerManager → Scheduler

```
# 简化版 sglang/srt/managers/scheduler.py
class Scheduler:
    def __init__(self, ...):
        self.tree_cache = RadixCache(...)     # radix tree，任意前缀粒度
        self.token_to_kv_pool = TokenToKVPool(...)
        self.runner = ModelRunner(...)        # FlashInfer + CUDAGraph

    def handle_request(self, req):
        # 1. radix 匹配：最长公共前缀
        prefix_nodes, prefix_len = self.tree_cache.match_prefix(req.input_ids)
        req.prefix_indices = prefix_nodes
        req.extend_input_len = len(req.input_ids) - prefix_len
        self.waiting_queue.append(req)

    def run_step(self):
        # 2. batch 构造（overlap：在 GPU 跑 batch N 时 CPU 准备 batch N+1）
        batch = self.get_new_batch_prefill() or self.get_new_batch_decode()
        # 3. 前向：CUDAGraph 回放（decode）或 eager（prefill）
        logits = self.runner.forward(batch)
        # 4. 采样 + xgrammar mask（无额外 GPU-CPU 同步）
        tokens = self.sampler.sample(logits, batch)
        # 5. KV 回写 radix tree（延迟回写，请求完成时插入共享节点）
        for r, t in zip(batch.reqs, tokens):
            r.append_token(t)
            if r.is_finished():
                self.tree_cache.insert(r.input_ids + r.output_ids, r.kv_indices)
```

核心抽象：`Request → RadixNode 指针 + token-level KV 池`。每个 token 在 KV 池里有一条索引，radix 树节点直接引用这些索引，**前缀共享粒度 = 单 token**。

### 15.3 关键差异落点

  
|步骤|vLLM v1|SGLang|
|---|---|---|
|prefix 匹配|block 级 hash|token 级 radix|
|KV 释放|请求结束立即释放或挂 LRU|radix 节点引用计数，自动共享|
|采样调度|Python per-step，有同步|CPU/GPU overlap，cuda graph 回放|
|约束解码|mask 在 CPU 构造|xgrammar 的 mask 在 GPU / 异步|

这两种抽象各有优劣：SGLang 在多租户共享长前缀时省内存、省算力；vLLM block 级抽象实现简单、对多模态 / MoE 改造更友好。两者近年都在吸取对方优点。

## 十六、常见问题 FAQ

**Q1：vLLM 和 SGLang 能共用同一份权重吗？** A：几乎可以。两者都读 HuggingFace 标准权重（safetensors），量化格式（AWQ / GPTQ / FP8）也互通。少数模型（DeepSeek-V3 MLA、部分 MoE）在特定版本上支持先后不一，以 issue tracker 为准。

**Q2：OpenAI 兼容 API 的细节差异？** A：最大差异在 `stream_options.include_usage`、`logprobs`、`tool_choice=required`、`reasoning_content` 这几个字段。vLLM 覆盖最全；SGLang 在 2025 年逐步补齐；TRT-LLM + Triton 常需额外写一个适配层（nim 里封装好了）。

**Q3：能否在 Kubernetes 里把 vLLM 和 SGLang 作为同一 Service 的两个 backend 灰度？** A：可以，通过网关（LiteLLM、One-API、HiggsField 等）做路由即可。关键是对齐 `model` 名、tool-call parser 与 token 计费口径。

**Q4：为什么我本地 llama.cpp 速度比 vLLM 还快？** A：大概率是你在对比”单并发 + 短输出 + 量化 GGUF”，此时 llama.cpp 没有调度开销、GGUF 量化访存极省；一旦并发 > 4 或上下文 > 4k，vLLM 会反超几倍到几十倍。

**Q5：在一张 RTX 4090（24GB）上跑 Qwen2.5-32B，选哪个？** A：只能靠量化。选项：① vLLM + AWQ（W4A16）；② LMDeploy TurboMind + W4A16；③ llama.cpp + Q4_K_M。吞吐要求高选 vLLM/LMDeploy，便捷选 Ollama。

**Q6：Mooncake 与 vLLM / SGLang 什么关系？** A：Mooncake 本身不是推理引擎，而是一个**以 KV cache 为中心的分布式存储 + 传输层**。vLLM 与 SGLang 都可以把 Mooncake 作为 KV transfer backend，从而实现跨机 PD 分离或 KV 复用。

**Q7：如果我只想支持 OpenAI 兼容 API，不关心底层引擎，用什么？** A：看规模。小规模：Ollama；中等：vLLM serve 足够；大规模多模型路由：加一层 LiteLLM / One-API，后端挂 vLLM/SGLang 多副本。

**Q8：TGI 真的完全不推荐吗？** A：如果你是 HuggingFace Inference Endpoints 付费用户、或者已经深度集成了 `text-embeddings-inference`，TGI 依然是稳定选择。新自建项目建议优先 vLLM。

## 十七、一个更完整的部署样例：Ray Serve + vLLM 多副本

```
# serve_vllm.py
from ray import serve
from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.engine.async_llm_engine import AsyncLLMEngine
from fastapi import FastAPI, Request
import json

app = FastAPI()

@serve.deployment(
    num_replicas=2,
    ray_actor_options={"num_gpus": 4},
    max_ongoing_requests=128,
)
@serve.ingress(app)
class VLLMDeployment:
    def __init__(self, model: str):
        engine_args = AsyncEngineArgs(
            model=model,
            tensor_parallel_size=4,
            gpu_memory_utilization=0.90,
            max_model_len=32768,
            enable_prefix_caching=True,
            enable_chunked_prefill=True,
        )
        self.engine = AsyncLLMEngine.from_engine_args(engine_args)

    @app.post("/v1/chat/completions")
    async def chat(self, req: Request):
        body = await req.json()
        # 省略：转 prompt、sampling params、SSE 流式输出
        ...

if __name__ == "__main__":
    serve.run(VLLMDeployment.bind("Qwen/Qwen2.5-7B-Instruct"))
```

部署拓扑：

把这套模板换成 SGLang 只需替换副本内部的启动命令；而换成 TensorRT-LLM 则需要切到 Triton Inference Server 作为副本内部 runtime（Ray Serve 仅做路由与扩缩容）。

## 十八、落地 checklist

上线一个 LLM 推理服务前可用这张 checklist 自检：

- 硬件选型与显存预算（模型 weight + KV + activation + overhead）
- 引擎选型（本篇决策树）与版本锁定（pin 到 patch 版）
- 量化方案（Q14 单独一篇）
- `max_model_len`、`max_num_seqs`、`max_num_batched_tokens` 三元组
- 是否开启 chunked prefill / prefix caching / CUDA graph
- 是否使用 PD 分离（长上下文 + 高 QPS 才收益明显）
- tool-call parser、reasoning parser、结构化输出方案
- Prometheus metrics + Grafana dashboard + p99 告警
- 压测脚本与 SLO（TTFT、TPOT、吞吐、成功率）
- 灰度方案（双副本双引擎并行观察一周）
- 回滚方案（镜像 tag + 权重 hash 全部可追溯）

## 十九、小结

- 本篇把 vLLM、SGLang、TensorRT-LLM、TGI 四大推理引擎做了从架构、KV cache、调度、kernel、量化、结构化输出、部署模式、生态、性能到社区现状的全面对比；
- 顺带盘点了 LMDeploy、MindIE、llama.cpp / Ollama / MLX、DeepSpeed-MII 等补位玩家；
- 给出了一棵可操作的”按硬件 × 场景”选型决策树，以及各引擎的关键参数调优建议；
- 性能对比引用了 2024Q4–2025Q1 的公开 benchmark 趋势，同时强调真实负载重尾分布会改变结论，需要以业务数据为准。

下一篇 [14 量化工程](https://quant67.com/post/llm-infra/14-quantization/14-quantization.html) 会把本篇略过的量化细节（INT8 / FP8 / AWQ / GPTQ / NVFP4 / MXFP4 / GGUF）展开到机制与工程落地层面。

## 参考资料

- vLLM：[https://github.com/vllm-project/vllm](https://github.com/vllm-project/vllm) · 《Efficient Memory Management for Large Language Model Serving with PagedAttention》(SOSP’23)
- vLLM v1 blog：[https://blog.vllm.ai/2025/01/27/v1-alpha-release.html](https://blog.vllm.ai/2025/01/27/v1-alpha-release.html)
- SGLang：[https://github.com/sgl-project/sglang](https://github.com/sgl-project/sglang) · 《SGLang: Efficient Execution of Structured Language Model Programs》(NeurIPS’24)
- RadixAttention 原论文同上
- FlashInfer：[https://github.com/flashinfer-ai/flashinfer](https://github.com/flashinfer-ai/flashinfer)
- xgrammar：[https://github.com/mlc-ai/xgrammar](https://github.com/mlc-ai/xgrammar)
- TensorRT-LLM：[https://github.com/NVIDIA/TensorRT-LLM](https://github.com/NVIDIA/TensorRT-LLM)
- Triton Inference Server：[https://github.com/triton-inference-server/server](https://github.com/triton-inference-server/server)
- TGI：[https://github.com/huggingface/text-generation-inference](https://github.com/huggingface/text-generation-inference)
- LMDeploy：[https://github.com/InternLM/lmdeploy](https://github.com/InternLM/lmdeploy)
- llama.cpp：[https://github.com/ggerganov/llama.cpp](https://github.com/ggerganov/llama.cpp)
- Ollama：[https://github.com/ollama/ollama](https://github.com/ollama/ollama)
- MLX-LM：[https://github.com/ml-explore/mlx-examples](https://github.com/ml-explore/mlx-examples)
- DeepSpeed-MII：[https://github.com/microsoft/DeepSpeed-MII](https://github.com/microsoft/DeepSpeed-MII)
- Mooncake：[https://github.com/kvcache-ai/Mooncake](https://github.com/kvcache-ai/Mooncake) · 《Mooncake: A KVCache-centric Disaggregated Architecture for LLM Serving》
- DistServe：《DistServe: Disaggregating Prefill and Decoding for Goodput-optimized Large Language Model Serving》(OSDI’24)
- Anyscale LLM inference benchmark：[https://www.anyscale.com/blog/benchmarking-llm-inference](https://www.anyscale.com/blog/benchmarking-llm-inference)
- LMSYS SGLang vs vLLM benchmark：[https://lmsys.org/blog/2024-07-25-sglang-llama3/](https://lmsys.org/blog/2024-07-25-sglang-llama3/)
- HF TGI benchmarks：[https://huggingface.co/docs/text-generation-inference](https://huggingface.co/docs/text-generation-inference)
- Nvidia TRT-LLM performance：[https://nvidia.github.io/TensorRT-LLM/performance/perf-overview.html](https://nvidia.github.io/TensorRT-LLM/performance/perf-overview.html)

---

**上一篇**：[12 PagedAttention 与 Continuous Batching](https://quant67.com/post/llm-infra/12-paged-continuous/12-paged-continuous.html) **下一篇**：[14 量化工程：INT8 / FP8 / AWQ / GPTQ](https://quant67.com/post/llm-infra/14-quantization/14-quantization.html)

## 同主题继续阅读

把当前热点继续串成多页阅读，而不是停在单篇消费。

2026-04-22 · architecture / ai-infra

### [大模型基础设施工程](https://quant67.com/post/llm-infra/index.html)

面向中国工程团队的大模型基础设施系列。从 GPU/CUDA/互联、训练框架与 3D 并行、vLLM/SGLang 推理引擎、量化与推测解码、RAG/Agent 到服务化、网关、可观测性与安全合规，覆盖 LLMOps 全链路。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】12：PagedAttention 与 Continuous Batching](https://quant67.com/post/llm-infra/12-paged-continuous/12-paged-continuous.html)

vLLM 的两大核心革新——Continuous Batching 让 GPU 打满、PagedAttention 让显存不再碎，推理吞吐量因此跃升一个数量级。本篇从操作系统类比到工程实操全盘拆解。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】11：推理引擎基础](https://quant67.com/post/llm-infra/11-inference-basics/11-inference-basics.html)

从 Prefill/Decode 两阶段、KV Cache、Continuous Batching 到 PD 分离，系统讲清楚大模型推理的工程基础。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】09：RLHF 与对齐流水线](https://quant67.com/post/llm-infra/09-rlhf-pipeline/09-rlhf-pipeline.html)

从 SFT、奖励模型到 PPO、DPO、GRPO 的完整对齐流水线工程实践，覆盖 OpenAI o1、DeepSeek-R1 等推理模型的 RL 路线与主流框架选型。