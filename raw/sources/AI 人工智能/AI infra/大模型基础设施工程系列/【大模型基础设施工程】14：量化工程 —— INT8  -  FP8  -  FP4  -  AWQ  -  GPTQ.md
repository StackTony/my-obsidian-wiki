> 系列第 14 篇。上一篇 [vLLM / SGLang / TensorRT-LLM / TGI](https://quant67.com/post/llm-infra/13-vllm-sglang/13-vllm-sglang.html) 对比了推理引擎的调度与吞吐，本篇深入推理优化的另一条主轴 —— **量化（Quantization）**：把模型权重、激活、KV Cache 从 FP16/BF16 压到 FP8、INT8、FP4、INT4，乃至 1.58-bit，换来显存、带宽、成本的数量级收益。

量化是 2023 年以来 LLM 推理侧最显著的工程变量之一。一块 80 GB 的 H100 放不下 Llama-3-70B BF16（140 GB），但 FP8 只要 70 GB、INT4 只要 35 GB，一张卡就能跑起来；生产环境里 decode 是 memory-bound，带宽砍一半，吞吐基本翻一倍。本篇按”**为什么 → 数据类型 → 算法 → 粒度 → 硬件 → 引擎 → 实操**”的顺序把量化这门”黑艺术”拆开。

## 一、为什么量化：显存、带宽、成本

### 1.1 显存账：参数量 × 位宽

对一个参数量为 的模型，权重显存 字节，其中 是每个参数的比特数。以 Llama-3-70B 为例：

|精度|位宽|权重显存|相对 BF16|
|---|---|---|---|
|FP32|32|280 GB|200%|
|BF16 / FP16|16|140 GB|100%|
|FP8 (E4M3)|8|70 GB|50%|
|FP6|6|52.5 GB|37.5%|
|INT4 / FP4|4|35 GB|25%|
|BitNet b1.58|1.58|13.8 GB|9.9%|

加上 KV Cache、activation buffer、CUDA graph，实际占用要再加 10%–30%。但数量级结论很清晰：**BF16 → FP8 节省 50%，BF16 → INT4 节省 75%**。

### 1.2 带宽账：decode 阶段 memory-bound

在自回归 decode 阶段，每生成一个 token 要把全部权重从 HBM 读一遍（prefill 不同，是 compute-bound）。Roofline 模型下：

H100 SXM 的 HBM3 带宽约 3.35 TB/s。Llama-3-70B： - BF16：140 GB / 3.35 TB/s ≈ **42 ms/token**（单卡理论下界） - FP8：70 GB / 3.35 TB/s ≈ **21 ms/token** - INT4：35 GB / 3.35 TB/s ≈ **10.5 ms/token**

这解释了为什么量化 decode 能近似线性提速 —— 带宽减半，延迟减半。实际还要乘上 dequant 开销、kernel 实现效率，通常能拿到 60%–90% 的理想加速。

### 1.3 成本账：更大 batch、更长上下文、更便宜的卡

权重压下去后省出来的显存可以用来：

- **扩 batch**：KV Cache 预算变大，continuous batching 的 max_num_seqs 可以从 128 提到 512；
- **加长上下文**：32k → 128k，对长文档 / Agent 工作流收益大；
- **降级硬件**：70B INT4 可以塞进 A10G（24 GB × 2）或 L40S（48 GB），推理单价可能降一个数量级；
- **节省出口管制下的算力**：H20、910B、4090D 环境里，量化是唯一可行的大模型方案。

## 二、浮点与整数数据类型

### 2.1 传统浮点：FP32 / FP16 / BF16

IEEE 754 浮点结构：`符号位 S | 指数 E | 尾数 M`，数值为 。

|类型|总位|符号|指数|尾数|动态范围|精度|
|---|---|---|---|---|---|---|
|FP32|32|1|8|23|±3.4e38|~7 位十进制|
|FP16|16|1|5|10|±65504|~3–4 位|
|BF16|16|1|8|7|±3.4e38|~2–3 位|
|TF32|19|1|8|10|±3.4e38|~3–4 位|

**BF16** 保留 FP32 的指数范围，牺牲尾数，解决 FP16 训练中常见的溢出问题，是当前训练的主流；**FP16** 精度略高但动态范围窄，训练需要 loss scaling。**TF32** 是 Ampere 起 Tensor Core 内部的 19-bit 格式，用户侧仍写 FP32。

### 2.2 FP8：Hopper/Ada 引入，两种变体

Hopper（H100 / H200 / H20）和 Ada（L40S）原生支持 FP8 Tensor Core，吞吐是 BF16 的 2 倍。两种变体：

|类型|符号|指数|尾数|动态范围|用途|
|---|---|---|---|---|---|
|**E4M3**|1|4|3|±448|权重 / 激活（训练前向、推理）|
|**E5M2**|1|5|2|±57344|梯度（训练反向、动态范围要求高）|

E4M3 精度高但范围窄，E5M2 相反。NVIDIA **Transformer Engine（TE）** 会在训练中自动做 per-tensor scaling：统计 amax，乘 scale 后转 FP8，反向用 E5M2。

### 2.3 FP6：Blackwell 新增

Blackwell（B100 / B200 / GB200）新增 FP6 Tensor Core，位宽在 FP8 和 FP4 之间，精度优于 FP4、吞吐高于 FP8。社区常用的 FP6 布局是 **E3M2**（NVIDIA FP6-LLM 论文中使用 E2M3 和 E3M2 两种）。FP6 适合”INT4 精度不够、FP8 显存太大”的中间地带。

### 2.4 FP4：Blackwell Tensor Core 原生

Blackwell 支持 **FP4（E2M1）**：1 符号 + 2 指数 + 1 尾数，可表示 共 16 个值。B200 的 FP4 Tensor Core 吞吐达到 FP8 的 2 倍、BF16 的 4 倍，官方宣称 GPT-MoE 1.8T 推理吞吐是 H100 的 30 倍主要来自 FP4 + NVLink72。

### 2.5 微缩放（MX）格式：OCP 标准

2023 年 Open Compute Project（AMD、ARM、Intel、Meta、Microsoft、NVIDIA、Qualcomm）联合发布 **Microscaling (MX) Formats v1.0**：

- **共享 scale**：每 32 个元素共享一个 E8M0（8-bit 指数）的 scale，再加上元素自身的低精度浮点；
- **MXFP8 / MXFP6 / MXFP4 / MXINT8**：元素分别是 FP8 / FP6 / FP4 / INT8；
- 每 32-元素块的总位宽 = ，等价有效位宽 。

MX 格式把 per-block scaling 硬件化，Blackwell Tensor Core 直接消费 MXFP8/FP6/FP4，省去 CUDA kernel 手动做 dequant，大幅简化软件栈。2026 年起会逐步成为训练和推理的默认量化格式。

### 2.6 INT8 / INT4

纯整数量化，最简单的线性映射：

其中 是 scale、 是 zero-point。**对称量化** ，**非对称量化** 。INT8 范围 ，INT4 范围 。INT 量化在消费卡（4090、3090）、昇腾、AMD MI250 等没有 FP8 的硬件上仍是首选。

### 2.7 各数据类型位布局 SVG

```
![各数据类型位布局 SVG](images/14-quantization-fig1.svg)
```

## 三、PTQ：训练后量化

**PTQ（Post-Training Quantization）** 不更新权重梯度，只用少量校准数据（通常 128–512 条）统计分布、求 scale / 修正权重，几分钟到几小时完成，是生产部署的主流路径。

### 3.1 朴素 RTN（Round-To-Nearest）

最简单：对每层权重独立求 ，round 到最近的量化格点。INT8 下精度通常可接受，INT4 下 LLM 质量显著下降，需要更聪明的算法。

### 3.2 GPTQ：基于 Hessian 的逐列最小二乘

**GPTQ（Frantar et al., ICLR 2023）** 把权重量化建模为带约束最小二乘：

其中 是校准激活。GPTQ 按列（或分组）贪心量化，每量化一列用剩余列补偿误差，依赖 Hessian 的 Cholesky 分解：

1. 计算 ；
2. 按列遍历 ：当前列 量化为 ，误差 ；
3. 把 均摊到剩余未量化列：（）。

对 175B 模型 4-bit 量化约需 4 小时单卡 A100。GPTQ 是 INT4 权重量化的事实标准之一，`AutoGPTQ` / `GPTQModel` 库覆盖 Llama / Qwen / Mixtral 等主流结构。

### 3.3 AWQ：Activation-aware Weight Quantization

**AWQ（Lin et al., MLSys 2024）** 观察：权重并非同等重要，**被大激活通道乘的权重列更敏感**。做法：

- 对每个 in-channel 乘缩放 ，对应激活除以 ：
- 只量化 ，激活不量化；
- 通过网格搜索最小化 。

AWQ 不依赖反向传播，只需一次前向校准，比 GPTQ 快约 10 倍，在 Llama-7B INT4 上 wikitext PPL 比 GPTQ 低 0.2–0.5。`AutoAWQ` 库是 vLLM / TensorRT-LLM 的首选 INT4 量化器。

### 3.4 SmoothQuant：权重 / 激活联合平滑

**SmoothQuant（Xiao et al., ICML 2023）** 针对 W8A8（权重激活都 INT8）量化：激活 outlier 集中在少数通道，直接量化会严重掉点。SmoothQuant 引入逐通道缩放 ：

参数 （常取 0.5）把量化难度从激活转移一部分到权重，两者都能较平滑地 INT8，无 outlier。SmoothQuant 是 NVIDIA TensorRT-LLM INT8 的默认路径之一。

### 3.5 SpinQuant / QuaRot：旋转矩阵消除 outlier

2024 年涌现的一类方法，观察：outlier 来源于 Transformer residual stream 的 few-channel 集中，用**正交旋转矩阵** （Hadamard 或学习得到）做变换：

在数学上等价（），但旋转后的激活近似高斯，outlier 被打散，可以干净地量化到 INT4 / FP4。

- **QuaRot（Ashkboos et al., 2024）**：用 Hadamard 旋转，计算量 ，支持 W4A4 KV4 端到端 INT4；
- **SpinQuant（Meta, 2024）**：旋转矩阵作为可学习参数，一次小规模 SFT 优化，W4A4 下 Llama-2-7B 相对 FP16 掉点 < 2.9 PPL。

旋转法目前是把 FP4 / INT4 激活量化做到实用的关键技术，Meta Llama 3 的 W4A4 部署方案就是基于 SpinQuant。

## 四、QAT：量化感知训练

PTQ 在 INT4 以下、或权重激活都量化（W4A4、W4A8）时经常掉点。**QAT（Quantization-Aware Training）** 在训练过程中插入 fake-quant 算子，梯度穿透（STE，Straight-Through Estimator）保持可微，让模型”学会”适应量化误差。

### 4.1 LLM-QAT（Meta, 2023）

在 Llama 基座上做 W4A8KV4 的 QAT：用原模型自己生成 100k 条蒸馏数据（避免依赖外部语料），KL 蒸馏 + 交叉熵，几千步训练即可收敛。

### 4.2 BitDistiller

在 SFT 阶段同步做 INT2/INT3 量化训练，结合 self-distillation，把 Llama-2-7B 压到 2-bit 仍保持可用质量。

### 4.3 BitNet 与 BitNet b1.58

**BitNet（Microsoft, 2023）**：1-bit 权重（）从零训练 Transformer，证明在 3B 以下和 FP16 匹敌。

**BitNet b1.58（Microsoft, 2024）**：权重取三值 ，等效 bit。核心变化： - 权重 `absmean` 量化（每矩阵一个 scale）； - 激活 `absmax` 量化到 INT8； - LayerNorm 前加入额外的 scale； - 从头 QAT 训练（PTQ 无法得到三值）。

论文声称 3B 参数下匹敌 FP16 Llama，7B 时速度快 4 倍、显存省 7 倍。社区有 `bitnet.cpp`（Microsoft 官方 CPU 推理）、HuggingFace `BitNet-b1.58-3B` 等复现；主要限制是**必须从头训练**，不能量化现有模型，落地多见于边缘设备和研究项目。

## 五、KV Cache 量化

对长上下文、大 batch 的推理场景，**KV Cache 显存占比可能超过权重**。以 Llama-3-70B（Grouped-Query-Attention、head_dim=128、kv_heads=8、80 层）为例，单 token KV = ；128k 上下文、batch=16 时 KV 总量 = ，远超权重。量化 KV Cache 收益非常可观。

### 5.1 FP8 KV

NVIDIA H100 上 FP8 KV Cache 几乎无损，直接用 E4M3 per-tensor 或 per-token scaling，vLLM、TensorRT-LLM、SGLang 都有原生支持：

```
# vLLM
llm = LLM(model="Qwen/Qwen2.5-72B-Instruct",
          kv_cache_dtype="fp8_e4m3",
          calculate_kv_scales=True)
```

### 5.2 INT8 KV：KVQuant / KIVI

- **KVQuant**：per-channel 量化 Key（K 的通道分布偏态大）、per-token 量化 Value；
- **KIVI**：类似但无需校准，per-channel K + per-token V，对 Llama-2-7B 在 LongBench 上相对 FP16 掉点 < 1%。

### 5.3 INT4 KV

KIVI-2、Atom 等方法可做 INT4 KV，显存省 75%。但 INT4 KV 对长上下文（> 32k）会明显掉质量，工程上常与 FP8 混合（近期 token FP8、历史 token INT4）。

### 5.4 实操：vLLM FP8 KV

```
from vllm import LLM, SamplingParams

llm = LLM(
    model="meta-llama/Meta-Llama-3.1-70B-Instruct",
    quantization="fp8",          # 权重 FP8
    kv_cache_dtype="fp8_e4m3",   # KV FP8
    max_model_len=128000,
    tensor_parallel_size=2,
)
out = llm.generate(["解释 KV Cache 量化的带宽收益"],
                   SamplingParams(max_tokens=256))
print(out[0].outputs[0].text)
```

单机 2×H100 80GB，原本 BF16 70B 需 4 卡，FP8 权重 + FP8 KV 后 2 卡即可，吞吐反而更高。

## 六、激活量化与 outlier 通道

### 6.1 LLM.int8() 的观察（Dettmers, 2022）

Dettmers 在 6.7B 规模首次观察到：**极少数（≈0.1%）激活通道的幅值是其他通道的 100×–1000×**，这些”outlier 通道”直接量化会毁掉数值精度。LLM.int8() 的解法简单粗暴：

- 按通道拆两路：outlier 通道走 FP16，其余走 INT8；
- 最后把两路结果相加。

这给 6.7B 以上模型带来了几乎无损的 INT8，代价是 15%–30% 速度损失（混合精度 kernel 难优化）。

### 6.2 outlier 从何而来

后续研究发现 outlier 与 residual stream 中几个”承载任务路由信息”的固定通道强相关，且随训练稳定。LayerNorm 的 scale 参数 会放大这些通道，使 outlier 在更深层愈发明显。

### 6.3 对策谱系

|方法|思路|代表|
|---|---|---|
|混合精度|outlier 走 FP16|LLM.int8()|
|激活缩放|把难度转移到权重|SmoothQuant|
|权重敏感加权|activation-aware|AWQ|
|正交旋转|打散 outlier|QuaRot / SpinQuant|
|块级 scaling|限制 outlier 影响范围|MXFP4 / MXINT8|

## 七、量化粒度：per-tensor / per-channel / per-group / per-block

    
|粒度|scale 数量|精度|计算开销|典型用途|
|---|---|---|---|---|
|per-tensor|1|低|低|FP8 激活（TE 默认）|
|per-token|seq_len|中|低|INT8 激活|
|per-channel|out_channels|高|中|INT8 权重、KVQuant K|
|per-group|out_channels × (in/g)|高|中|GPTQ/AWQ group_size=128|
|per-block（MX）|每 32 元素一个|很高|硬件支持好|MXFP8/FP6/FP4|

**per-group** 是 INT4 权重的主流，group_size=64 或 128 在精度和 scale 存储间平衡。**per-block（MX）** 是 Blackwell 起的硬件标配，scale 随数据流动，无需软件干预。

## 八、硬件支持矩阵

      
|硬件|BF16|FP8|FP6|FP4|INT8|INT4 权重|
|---|---|---|---|---|---|---|
|NVIDIA H100/H200/H20|✓|✓ E4M3/E5M2|✗|✗|✓|dequant → FP16|
|NVIDIA B100/B200/GB200|✓|✓|✓ MXFP6|✓ MXFP4|✓|dequant → FP8|
|NVIDIA L40S / Ada|✓|✓|✗|✗|✓|dequant → FP16|
|NVIDIA A100|✓|✗|✗|✗|✓|dequant → FP16|
|AMD MI300X / MI325X|✓|✓ E4M3/E5M2|✗|✗|✓|dequant → FP16|
|AMD MI350X（2025）|✓|✓|✓|✓|✓|✓|
|Intel Gaudi 3|✓|✓|✗|✗|✓|✓|
|华为昇腾 910B|✓|✗ (910C 支持)|✗|✗|✓|dequant|
|华为昇腾 910C（2025）|✓|✓|✗|✗|✓|✓|
|寒武纪思元 590|✓|部分|✗|✗|✓|✓|
|海光 DCU K100|✓|✗|✗|✗|✓|dequant|

**“dequant → FP16”** 表示硬件不直接计算 INT4 × FP16 矩阵乘，CUDA kernel 要先把 INT4 权重解压到 FP16 再上 Tensor Core —— 这也是为什么 GPTQ / AWQ 在 Ampere / Hopper 上拿不到理论 4× 的带宽收益，但仍可拿到 1.5×–2× decode 加速。

NVIDIA **Transformer Engine** 是 FP8 训练的官方路径，自动管理 per-tensor amax / scale / history；推理侧 vLLM、TensorRT-LLM 都集成了 TE 的 FP8 GEMM。

## 九、推理引擎的量化支持矩阵

        
|引擎|FP16/BF16|FP8|FP4|INT8 W|INT4 W (AWQ)|INT4 W (GPTQ)|INT8 KV|FP8 KV|
|---|---|---|---|---|---|---|---|---|
|**vLLM**|✓|✓|✓ (B200)|✓|✓|✓|✓|✓|
|**SGLang**|✓|✓|✓ (B200)|✓|✓|✓|✓|✓|
|**TensorRT-LLM**|✓|✓|✓|✓|✓|✓|✓|✓|
|**TGI (HF)**|✓|✓|实验|✓|✓|✓|部分|✓|
|**llama.cpp**|✓|部分|✗|✓|✓ GGUF|✓ GGUF|✓|✗|
|**MLC-LLM**|✓|✗|✗|✓|✓|✓|✗|✗|
|**LMDeploy (书生)**|✓|✓|✗|✓|✓|✓|✓|✓|

### 9.1 llama.cpp 的 GGUF 量化体系

`llama.cpp` 的 **GGUF** 格式是 CPU / 小 GPU / Apple Silicon 的主流，提供一整套精细化量化级别：

|名称|等效位宽|说明|
|---|---|---|
|Q8_0|8.5|FP16 → INT8 block 32，几乎无损|
|Q6_K|6.6|k-quant，6-bit 主 + 8-bit scale/min|
|Q5_K_M|5.7|混合：重要层 Q6_K、其他 Q5_K|
|Q4_K_M|4.8|社区默认：质量 / 大小平衡最好|
|Q4_K_S|4.6|更小|
|Q3_K_M|3.9|明显掉点，极端受限场景|
|IQ2_XS|2.3|基于 importance matrix 的 2-bit|
|Q2_K|2.6|仅 70B 以上可用|

`Q4_K_M` 是桌面 / Mac 跑 70B 的黄金组合，40 GB 左右内存即可，质量接近 FP16。

## 十、工程实操：AutoAWQ 量化 Qwen + 部署 vLLM

### 10.1 环境

```
pip install autoawq==0.2.6 vllm==0.6.3 transformers==4.45.0
```

### 10.2 AutoAWQ 量化脚本

```
from awq import AutoAWQForCausalLM
from transformers import AutoTokenizer

model_path = "Qwen/Qwen2.5-7B-Instruct"
quant_path = "./qwen2.5-7b-awq-int4"
quant_config = {
    "zero_point": True,
    "q_group_size": 128,
    "w_bit": 4,
    "version": "GEMM",
}

model = AutoAWQForCausalLM.from_pretrained(
    model_path, device_map="auto", safetensors=True
)
tok = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)

# 校准数据：通用 + 领域混合 128 条足够
calib = [
    "量化是把高精度张量映射到低位宽的过程。",
    "vLLM 使用 PagedAttention 管理 KV Cache。",
    # ...
] * 16

model.quantize(tok, quant_config=quant_config, calib_data=calib)
model.save_quantized(quant_path, safetensors=True)
tok.save_pretrained(quant_path)
print("AWQ done ->", quant_path)
```

7B 模型单卡 A100 约 20 分钟完成。产物为 safetensors + `quant_config.json`，体积约 5.5 GB（原 BF16 约 14 GB）。

### 10.3 GPTQ 脚本（对比）

```
from gptqmodel import GPTQModel, QuantizeConfig

cfg = QuantizeConfig(bits=4, group_size=128, desc_act=True, sym=True)
model = GPTQModel.from_pretrained("Qwen/Qwen2.5-7B-Instruct", quantize_config=cfg)
model.quantize(calib_dataset=calib, batch_size=1)
model.save("./qwen2.5-7b-gptq-int4")
```

GPTQ 依赖 Hessian，显存峰值和耗时高于 AWQ，但在某些任务（数学、代码）上略稳定。

### 10.4 vLLM 部署

```
python -m vllm.entrypoints.openai.api_server \
  --model ./qwen2.5-7b-awq-int4 \
  --quantization awq_marlin \
  --kv-cache-dtype fp8_e4m3 \
  --max-model-len 32768 \
  --gpu-memory-utilization 0.92 \
  --port 8000
```

`awq_marlin` 是 vLLM 集成的高性能 AWQ kernel（基于 NVIDIA Marlin），decode 吞吐比早期 AWQ 快 2–3 倍。

### 10.5 TensorRT-LLM 部署（FP8）

```
# 权重转换 + 校准
python convert_checkpoint.py \
  --model_dir Qwen2.5-72B-Instruct \
  --output_dir ./ckpt-fp8 \
  --dtype bfloat16 --use_fp8 --fp8_kv_cache

# Engine 构建
trtllm-build --checkpoint_dir ./ckpt-fp8 \
  --output_dir ./engine-fp8 \
  --gemm_plugin fp8 --max_batch_size 64 --max_input_len 32768

# 运行
mpirun -n 2 trtllm-run --engine_dir ./engine-fp8 \
  --input_text "解释 FP8 的 E4M3 与 E5M2 区别"
```

### 10.6 精度前后对比：MMLU / GSM8K / PPL

一个经验性的参考表（Qwen2.5-7B-Instruct，单次评估，具体数值因版本和评测脚本而异）：

|版本|wikitext PPL|MMLU (5-shot)|GSM8K (strict)|显存（单卡）|
|---|---|---|---|---|
|BF16|6.85|74.2|80.5|14.2 GB|
|FP8 (E4M3, per-tensor)|6.87|74.1|80.3|7.3 GB|
|INT8 W + INT8 A (SmoothQuant)|6.92|73.8|79.6|7.6 GB|
|INT4 W AWQ g128|7.08|73.5|78.9|5.7 GB|
|INT4 W GPTQ g128|7.15|73.2|78.4|5.7 GB|
|INT4 W + INT4 KV (Atom)|7.40|72.1|76.3|4.8 GB|
|GGUF Q4_K_M|7.12|73.4|78.7|5.3 GB (CPU/GPU)|

结论： - FP8 几乎无损，显存减半； - W8A8 SmoothQuant 几乎无损； - INT4 AWQ 掉 < 1 分 MMLU，是**显存 / 质量最优解**； - INT4 KV 要谨慎，长上下文任务掉点明显。

## 十一、精度 vs 速度权衡图

```
![精度 vs 速度权衡图](images/14-quantization-fig2.svg)
```

## 十二、常见坑与经验法则

### 12.1 “量化后模型胡说八道”排查

- **校准集不匹配**：用通用语料量化，业务是中文 / 代码，换成业务相关数据再跑一次；
- **group_size 过大**：INT4 g=256 掉点明显，改 128 或 64；
- **outlier 层未跳过**：embedding、lm_head、最后一层 norm 常跳过量化；
- **kv_cache_dtype INT4 太激进**：先只量化权重，再逐步量化 KV。

### 12.2 “量化后速度没变快”排查

- **kernel fallback 到 FP16**：Ampere / 非 Hopper 卡跑 FP8 会 emulate，反而变慢；
- **batch 太大，compute-bound**：量化主要降 decode 延迟，prefill 阶段收益小；
- **max_model_len 过小**：KV 占比低，省带宽价值不明显；
- **未用融合 kernel**：AWQ 要跑在 `awq_marlin`、GPTQ 要跑在 `exllamav2` / `marlin`。

### 12.3 经验法则

1. **有 Hopper 以上就 FP8**：训练推理同构，精度无损，工程最省心；
2. **A100 / Ampere 用 AWQ INT4 + FP16 KV**：单卡跑 70B 的最佳组合；
3. **消费卡跑 70B**：llama.cpp GGUF Q4_K_M；
4. **B200 部署**：MXFP4 权重 + FP8 KV，吞吐最大化；
5. **出口管制硬件（H20、910B）**：FP8（H20） / INT8（910B）是主路径；
6. **KV Cache 量化在长上下文才有价值**：< 8k 场景先别碰；
7. **从 PTQ 开始，不够再 QAT**：QAT 训练成本高，98% 情况 PTQ 足够。

## 十三、产业现状（2026 Q1 快照）

- **OpenAI**：GPT-4o / o3 内部使用 FP8 训练和推理（Blackwell FP4 推理已在灰度）；
- **Anthropic**：Claude 系列 AWS Trainium / H100 上 FP8 + FP8 KV；
- **Meta**：Llama 3 / 3.1 官方发布 BF16 + FP8 + Int4（AWQ / SpinQuant W4A4）三套权重；
- **Google**：Gemini 在 TPU v5p / Trillium 上用 BF16 + INT8；
- **DeepSeek**：V3 原生 FP8 训练（DeepSeek-V3 技术报告），推理默认 FP8；
- **Qwen 系列**：官方发布 GPTQ-Int4 / AWQ / FP8 三种，社区 GGUF 覆盖全系；
- **Kimi / MoonShot**：长上下文场景使用 INT8 KV + FP8 权重；
- **字节豆包 / 火山引擎**：自研推理引擎支持 FP8、INT8、INT4，混合量化策略；
- **llama.cpp 生态**：社区 GGUF 已成为本地部署事实标准，HF Hub 上每个主流开源模型都有 10+ GGUF 变体。

## 十四、小结

量化已从”压缩模型的 trick”演进为推理栈的一等公民：

- **数据类型**：FP8 → FP6/FP4 → MX 格式，硬件和软件都在快速迭代；
- **算法**：AWQ / GPTQ / SmoothQuant / SpinQuant 覆盖 PTQ 主要路径，QAT / BitNet 探索极限；
- **KV Cache**：和权重同等重要，FP8 KV 已是生产标配；
- **工程**：AutoAWQ → vLLM、Transformer Engine → TensorRT-LLM、GGUF → llama.cpp 三套成熟组合；
- **决策**：硬件 → 选位宽 → 选算法 → 选引擎 → 选粒度 → 选 KV 策略。

理解清楚上述每一环，结合业务 SLO（延迟、吞吐、质量、成本），才能做出正确的量化选型。下一篇 [推测解码与 MTP](https://quant67.com/post/llm-infra/15-speculative-mtp/15-speculative-mtp.html) 进入推理优化的”预测并行”维度 —— 和量化正交，叠加使用收益可再翻倍。

## 参考资料

1. Dettmers et al. _LLM.int8(): 8-bit Matrix Multiplication for Transformers at Scale_. NeurIPS 2022.
2. Frantar et al. _GPTQ: Accurate Post-Training Quantization for Generative Pre-trained Transformers_. ICLR 2023.
3. Lin et al. _AWQ: Activation-aware Weight Quantization for LLM Compression and Acceleration_. MLSys 2024.
4. Xiao et al. _SmoothQuant: Accurate and Efficient Post-Training Quantization for LLMs_. ICML 2023.
5. Ashkboos et al. _QuaRot: Outlier-Free 4-Bit Inference in Rotated LLMs_. NeurIPS 2024.
6. Liu et al. _SpinQuant: LLM Quantization with Learned Rotations_. Meta, 2024.
7. Ma et al. _The Era of 1-bit LLMs: All Large Language Models are in 1.58 Bits_. Microsoft, 2024.
8. Xu et al. _KIVI: A Tuning-Free Asymmetric 2-bit KV Cache Quantization_. ICML 2024.
9. Hooper et al. _KVQuant: Towards 10 Million Context Length LLM Inference_. NeurIPS 2024.
10. OCP _Microscaling Formats (MX) Specification v1.0_, 2023.
11. NVIDIA _Transformer Engine Documentation_（FP8 / MXFP8）。
12. NVIDIA _TensorRT-LLM_ 仓库与 Qwen / Llama 量化示例。
13. vLLM / SGLang / llama.cpp / AutoAWQ / GPTQModel 官方仓库与 README。
14. DeepSeek-AI _DeepSeek-V3 Technical Report_（FP8 训练实践）。
15. Meta _Llama 3.1 / 3.2 Quantization Recipes_。

---

**上一篇**：[vLLM / SGLang / TensorRT-LLM / TGI 对比](https://quant67.com/post/llm-infra/13-vllm-sglang/13-vllm-sglang.html) **下一篇**：[推测解码与 MTP](https://quant67.com/post/llm-infra/15-speculative-mtp/15-speculative-mtp.html)

## 同主题继续阅读

把当前热点继续串成多页阅读，而不是停在单篇消费。

2026-04-22 · architecture / ai-infra

### [大模型基础设施工程](https://quant67.com/post/llm-infra/index.html)

面向中国工程团队的大模型基础设施系列。从 GPU/CUDA/互联、训练框架与 3D 并行、vLLM/SGLang 推理引擎、量化与推测解码、RAG/Agent 到服务化、网关、可观测性与安全合规，覆盖 LLMOps 全链路。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】11：推理引擎基础](https://quant67.com/post/llm-infra/11-inference-basics/11-inference-basics.html)

从 Prefill/Decode 两阶段、KV Cache、Continuous Batching 到 PD 分离，系统讲清楚大模型推理的工程基础。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】09：RLHF 与对齐流水线](https://quant67.com/post/llm-infra/09-rlhf-pipeline/09-rlhf-pipeline.html)

从 SFT、奖励模型到 PPO、DPO、GRPO 的完整对齐流水线工程实践，覆盖 OpenAI o1、DeepSeek-R1 等推理模型的 RL 路线与主流框架选型。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】10：Checkpoint 与故障容忍](https://quant67.com/post/llm-infra/10-checkpoint-fault/10-checkpoint-fault.html)

万卡集群训练每天都在断：从 GPU HBM ECC、NVLink 降级到 SDC，本篇系统讲 checkpoint、恢复与弹性容错的工程实践。