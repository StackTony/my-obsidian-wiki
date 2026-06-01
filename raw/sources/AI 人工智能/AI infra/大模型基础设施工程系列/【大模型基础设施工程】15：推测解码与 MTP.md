## 一、为什么需要推测解码

### 1.1 Decode 阶段的根本瓶颈

在 [第 11 篇](https://quant67.com/post/llm-infra/11-inference-basics/11-inference-basics.html) 与 [第 12 篇](https://quant67.com/post/llm-infra/12-paged-continuous/12-paged-continuous.html) 里我们反复强调：大模型推理的 Decode 阶段是**显存带宽受限（memory-bound）**的。每生成一个 token，GPU 必须：

1. 把整套模型权重从 HBM 流过 SM 一遍（对 70B 模型约 140 GB @ FP16）；
2. 把 KV cache 对应部分流过；
3. 算出一个 logits 向量，采样一个 token。

也就是说，**算力大量闲置**——H100 的 FP16 峰值接近 1 PFLOPS，但 Decode 实际只用到其中几 %。带宽被吃满，算力却在睡觉。

### 1.2 核心洞察：验证比生成便宜

推测解码（Speculative Decoding）抓住了一个朴素事实：

> 一次前向 pass 可以同时对 K 个位置的 logits 打分——只要这些 token 作为输入一次性喂进去，attention 的 causal mask 自动保证第 i 个位置只看到前 i-1 个 token。

Transformer 的 Prefill 每天都在做这件事。既然模型已经把权重搬进 SM 一次了，多算几个位置几乎**不要钱**（只要 K 不大，算力还远未打满）。

于是出现了”让小模型 / 额外头先猜，大模型一次验证 K 个”的范式。核心指标是**接受长度（accepted length per step）**：每次 target forward 能推进多少 token。

### 1.3 一张时序图

下图对比原始自回归解码与推测解码的时间轴：

![推测解码时序图](https://quant67.com/post/llm-infra/15-speculative-mtp/images/15-speculative-mtp-fig1.svg)

## 二、经典 Speculative Decoding

### 2.1 算法骨架

Leviathan 等人 2022 年的 _Fast Inference from Transformers via Speculative Decoding_（以及 DeepMind 并行工作 _Accelerating LLM Decoding with Speculative Sampling_）给出了原始范式：

- **Draft model** `q`：一个参数量远小于 Target 的模型，自回归生成 K 个候选 token `x_1...x_K` 及其概率分布 `q_1...q_K`；
- **Target model** `p`：把 `[prefix, x_1, ..., x_K]` 一次性喂入，得到 K+1 个位置的分布 `p_1...p_{K+1}`；
- **验证**（rejection sampling）：
    - 对每个 i，以概率 `min(1, p_i(x_i) / q_i(x_i))` 接受 `x_i`；
    - 若被拒，在残差分布 `norm(max(0, p_i - q_i))` 中采一个 token，结束本轮；
    - 若全部接受，从 `p_{K+1}` 直接再采 1 个 token（免费多出 1 个）。

### 1.2 正确性保证

rejection sampling 的数学可证明：**最终产出的 token 序列与直接从 Target 采样在分布上完全一致**。也就是说，推测解码不是近似，而是精确等价——只要 Target 一样，输出分布就一样。这点非常关键，生产环境任何”无损”加速都必须满足。

### 2.3 加速比直觉

设平均接受长度为 `α`（1 ≤ α ≤ K+1），Draft 一步耗时 `t_d`、Target 一步 `t_t`，则近似：

```
speedup ≈ α × t_t / (K × t_d + t_t)
```

- 当 Draft 对齐度高（α 接近 K+1）、`t_d << t_t`：加速比趋近 K+1；
- 典型 70B + 7B draft：α≈3，t_d/t_t≈0.1，加速比 2–3×；
- **当 Draft 太笨**（α 接近 1）：速度反而变慢，这是生产最常见的踩坑。

### 2.4 Draft 模型的工程选择

```
Target              常用 Draft（同家族小尺寸）
-----------------   ----------------------------
Llama-3-70B         Llama-3-8B、Llama-3.2-1B
Qwen2.5-72B         Qwen2.5-1.5B、Qwen2.5-0.5B
DeepSeek-V3 671B    DeepSeek-V2-Lite / 内建 MTP 头
Mixtral 8x22B       Mistral-7B
```

必须**同 tokenizer、同词表**，否则词元对齐崩盘。不同家族（比如想用 Qwen 给 Llama 当 draft）几乎不可行。

## 三、Medusa：多头直接预测

### 3.1 动机

Draft model 的麻烦在于：要额外部署一个模型、维护它的权重、占一份显存、还得单独调度。Medusa（Together AI，2023）提出：**干脆给 Target 模型加几个额外的 LM head，一次性预测 next-1、next-2、next-3、next-4 个 token**。

### 3.2 结构

```
          ┌── LM head 0  → p(t+1 | hidden)   (原 head)
          │
 hidden ──┼── Medusa head 1 → p(t+2 | hidden)
          │
          ├── Medusa head 2 → p(t+3 | hidden)
          │
          └── Medusa head 3 → p(t+4 | hidden)
```

每个 Medusa head 是一个浅层残差块 + Linear，训练时把 Target 冻住只训这几个头（也可 LoRA 联调）。训练代价极低——几千条数据就能收敛。

### 3.3 Tree Attention

Medusa 的关键创新：**同时保留每个头的 top-k 候选，组合成树**。

例如 head1 top-3 × head2 top-3 × head3 top-2 = 18 条候选路径。通过自定义 attention mask（每个节点只看祖先），Target 在一次 forward 内并行验证这 18 条路径，挑最长被接受的。

```
        Draft tree (Medusa)
                [root]
              /   |    \
          h1_a  h1_b  h1_c
         / | \   |
       h2 h2 h2 h2
       ...
```

这把接受率显著拉高，但也带来”token budget”压力：一次 forward 要算的 K 可能从 4 涨到 60，Target 的算力开销也水涨船高。batch size 大时反而不划算。

### 3.4 性能

官方数据：Vicuna-7B 2.2×；Vicuna-33B 2.1×；后续 Medusa-2 + 联合训练到 2.8×。

## 四、EAGLE 家族：特征级推测

### 4.1 为什么需要 EAGLE

Medusa 把每个 head 做成”独立预测 next-N”——这忽略了**草稿 token 之间的依赖**。真实分布下 token 是链式条件的，多头独立预测会损失准确率。EAGLE（_Extrapolation Algorithm for Greater Language-model Efficiency_，ICML 2024）给出修正：在特征（hidden state）层做自回归。

### 4.2 EAGLE-1

- Draft 一个小的”自回归头”（单层 Transformer），输入 = 上一步 hidden feature + embedding；
- 输出下一个 token 的 hidden feature，再过共享的 LM head；
- 这样 draft 是**真自回归**，不像 Medusa 各头独立；
- 结合 tree attention，接受率远超 Medusa。

加速比：Vicuna/LLaMA2-Chat 上 2.7×–3.0×（on MT-bench）。

### 4.3 EAGLE-2

EAGLE-2（ACL 2024）观察到：**不同位置、不同上下文，最佳 draft tree 不一样**。于是改用**动态 tree**： - 每个草稿节点按期望接受率打分； - 只展开 top-N 节点，剪掉没希望的分支； - 在相同 token budget 下接受率再涨 ~20%。

报告 speedup：3.0×–3.5×。

### 4.4 EAGLE-3

EAGLE-3（2025）进一步把 draft 与 target 的 **多层特征**融合（低/中/高层 hidden 拼接），且放宽了”特征对齐”约束——允许 draft 用数据驱动方式学到自己的特征空间。作者报告在 Llama-3、Qwen2.5、DeepSeek 系列上可达 **3.5×–6.5×** decode 加速，特别是 batch=1 的 chat 场景几乎把自回归成本打掉一半。EAGLE-3 是当前（2025–2026）开源 SOTA 推测方法之一。

### 4.5 部署侧要点

- EAGLE head 的权重需要单独发布（官方在 HuggingFace 放了 Llama/Qwen/Vicuna 各档），官方未发布的需要自己训（~几百 GPU hour）；
- 必须与 Target checkpoint **严格匹配**；Target 做了 LoRA/微调后草稿头通常也要重训；
- vLLM ≥ 0.6、SGLang、TensorRT-LLM 都有原生支持。

## 五、Lookahead Decoding：无需 Draft

### 5.1 思想

LMSYS 2023 年提出的 Lookahead Decoding 把 **Jacobi 迭代**搬到了 LLM 解码上。核心观察：

> 自回归 `x_{t+1} = f(x_1..x_t)` 可以看作不动点方程，Jacobi 迭代可并行求解。

Lookahead 在每个 step：

1. 用当前模型自己并行预测一条长度为 W 的 “n-gram 候选”（**Jacobi branch**）；
2. 从历史见过的 n-gram 池里抽可能的 token 序列（**Lookahead branch**）做 verify；
3. Target 一次 forward 同时验证两类候选。

### 5.2 优缺点

- 优点：**完全不用 draft model / 额外头**，不改模型，不用训练；
- 缺点：接受率一般 1.5×–2×，比不过 EAGLE；对**代码、结构化输出**特别有效（重复 n-gram 多）；
- 适合**私有模型没时间训 draft**、或者对正确性零容忍的场景（数学可证明无损）。

TensorRT-LLM 把 Lookahead 作为首批一等公民实现之一。

## 六、Multi-Token Prediction（MTP）

### 6.1 Meta 2024：把多 token 预测放进预训练

Gloeckle 等人 _Better & Faster Large Language Models via Multi-token Prediction_（ICML 2024）提出：

> 与其预训练只预测 next-1，不如在主干之上放 **n 个平行头**，让模型同时预测 next-1 … next-n（典型 n=4）。

训练 loss：

```
L = Σ_{i=1..n} CE( head_i(hidden_t), token_{t+i} )
```

实验结论： - 在代码任务上显著提升（+3% HumanEval 左右），因为代码 token 长程依赖强； - 小模型上收益有限，中大规模（~7B+）才体现； - 天然支持推测解码——推理时用这 n 个头做 draft，几乎零额外成本。

### 6.2 DeepSeek-V3 的 MTP

DeepSeek-V3（2024.12）把 MTP 作为**正式训练目标之一**：

- 采用**串联式** MTP 模块：MTP module k 的输入 = 主模型在 t+k-1 位置的 hidden + t+k 位置 embedding，再过一层 Transformer block 做预测，**保持因果链**——比 Meta 原版独立头更精确；
- 预训练/后训练都带上 MTP loss；
- 推理时既可以**丢弃 MTP 模块**（只用主干，结果与普通自回归一致），也可以**打开 MTP 做自推测**。

官方汇报：推理打开 MTP 后接受率达 **85–90%**，decode 端到端 **~1.8×** 加速。这是 DeepSeek-V3 公开 benchmark 里绕不过去的一项。

### 6.3 MTP 训练头示意

![MTP 训练头示意](https://quant67.com/post/llm-infra/15-speculative-mtp/images/15-speculative-mtp-fig2.svg)

### 6.4 MTP vs Medusa/EAGLE 比较

|维度|Medusa|EAGLE|MTP (DeepSeek-V3)|
|---|---|---|---|
|是否影响预训练|否|否（head 另训）|**是**，训练目标内嵌|
|Draft 自回归|否（独立头）|是（特征自回归）|是（串联式）|
|训练成本|低|低|高（预训练级）|
|模型质量影响|不影响|不影响|**反而提升主模型**|
|推理加速|2.0–2.5×|2.5–3.5×|~1.8×（接受率高）|
|适用方|已有模型加速|已有模型加速|新模型训练者|

## 七、Self-Speculative Decoding

### 7.1 同一模型自己当 draft

Self-speculative 的思想：**不要另一个模型、也不要额外头，用大模型自己的”廉价版本”做 draft**。主要有两支：

- **Layer Skip / Early Exit（Draft&Verify）**：用前 L/2 层跑一次作为 draft，再用完整 L 层 verify。ACL 2024 Elhoushi 等 _LayerSkip_ 提出在训练期做 layer dropout，让早退也有合理输出；
- **Self-Speculative via Draft Heads**：在自己模型上 LoRA 一组少层 heads 作 draft。

### 7.2 优缺点

- 优点：**完全不加参数**，不用多备一份权重；
- 缺点：layer skip 的 draft 质量受限（α ≈ 1.5–2.0）；需要模型训练时配合（否则早退精度崩）；
- 适合显存极紧、但想榨一点 decode 速度的场景。

## 八、Parallel / Jacobi Decoding 家族

### 8.1 Jacobi Decoding

前面 Lookahead 提过的 Jacobi 迭代也可以单独使用：把 W 个未来位置初始化为任意 token，反复用模型并行 refine，直到收敛。单次迭代就是一次 forward。实际 W=8~16 时通常 3–4 次迭代收敛，实现 ~2× 提速。

### 8.2 Consistency LLMs (CLLM)

SJTU/UCSD 2024 年的 CLLM 把 Jacobi 收敛性做成训练目标——让模型**直接对任意 Jacobi 轨迹都能一步收敛**。推理时把 W 个位置喂进去，一次 forward 就产出 W 个 token。报告 2.4–3.4× 加速，不需要 draft。

### 8.3 Beam-aware / 非贪心

多数推测方法在 top-1 / 贪心解码上效果最好。非贪心（温度高、top-p 广）时接受率会掉——因为 draft 分布 `q` 和 target 分布 `p` 的 KL 在高温下拉大。生产里通常把 speculative 与 `temperature=0` 的代码补全、function-calling 场景强绑定。

## 九、推理引擎对推测解码的支持

截至 2025–2026 初（版本在快速演进，以官方 release notes 为准）：

      
|引擎|Draft model|Medusa|EAGLE|Lookahead|n-gram|MTP|
|---|---|---|---|---|---|---|
|vLLM|是|是|是（EAGLE-1/2/3）|部分|是（prompt lookup）|是（DeepSeek-V3 专用路径）|
|SGLang|是|实验|是（主推 EAGLE-2/3）|—|是|是（DeepSeek-V3 深度适配）|
|TensorRT-LLM|是|是|是|**是（首批实现）**|—|是（via engine plugin）|
|TGI|是|是|是|—|是|有限|
|llama.cpp|是（draft model）|—|—|—|是|—|

### 9.1 vLLM 启用 EAGLE / Medusa 的命令

EAGLE：

```
vllm serve meta-llama/Llama-3.1-70B-Instruct \
    --tensor-parallel-size 4 \
    --speculative-model yuhuili/EAGLE-LLaMA3.1-Instruct-70B \
    --num-speculative-tokens 5 \
    --speculative-draft-tensor-parallel-size 1 \
    --use-v2-block-manager
```

Medusa：

```
vllm serve lmsys/vicuna-7b-v1.3 \
    --speculative-model FasterDecoding/medusa-vicuna-7b-v1.3 \
    --num-speculative-tokens 5 \
    --speculative-disable-by-batch-size 16
```

Draft model（最朴素方案）：

```
vllm serve Qwen/Qwen2.5-72B-Instruct \
    --tensor-parallel-size 8 \
    --speculative-model Qwen/Qwen2.5-1.5B-Instruct \
    --num-speculative-tokens 4
```

Prompt-lookup（n-gram，**零训练、零依赖**，对代码/长文本惊人有效）：

```
vllm serve Qwen/Qwen2.5-Coder-32B-Instruct \
    --speculative-model '[ngram]' \
    --ngram-prompt-lookup-max 4 \
    --num-speculative-tokens 5
```

### 9.2 SGLang 启用 EAGLE-3

```
python -m sglang.launch_server \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --speculative-algorithm EAGLE3 \
    --speculative-draft-model-path lmsys/sglang-EAGLE3-LLaMA3.1-Instruct-8B \
    --speculative-num-steps 5 \
    --speculative-eagle-topk 8 \
    --speculative-num-draft-tokens 64
```

### 9.3 SGLang 启用 DeepSeek-V3 MTP

```
python -m sglang.launch_server \
    --model deepseek-ai/DeepSeek-V3 \
    --tp 8 \
    --speculative-algorithm EAGLE \
    --speculative-num-steps 1 \
    --speculative-eagle-topk 1 \
    --speculative-num-draft-tokens 2 \
    --enable-mtp
```

（参数名称以各引擎最新文档为准，此处反映典型用法。）

### 9.4 TensorRT-LLM Lookahead

```
trtllm-build \
    --checkpoint_dir ./llama3-70b-ckpt \
    --output_dir ./engine \
    --speculative_decoding_mode lookahead_decoding \
    --max_draft_len 7

# runtime
python run.py --engine_dir ./engine \
    --lookahead_config "[7, 7, 7]"   # [W, N, G]
```

## 十、工程权衡与实测数据

### 10.1 Batch size 越大，推测越不划算

推测解码的**算力预算**被接受率摊销。当 batch=1 时 Target forward 几乎没用到多少算力，多算 K 个位置几乎白嫖；但当 batch=64 时 Target forward 已经开始算力受限了，多算 K 个位置开销线性增加——而接受率不会跟着涨。

实践曲线（以 Llama-3 70B + EAGLE-2 为例，A100 tp=4，大致趋势）：

|batch|vanilla tps|EAGLE-2 tps|speedup|
|---|---|---|---|
|1|22|72|3.3×|
|4|68|180|2.6×|
|16|200|360|1.8×|
|32|320|440|1.4×|
|64|440|490|1.1×|
|128|580|580|~1.0×|

所以**对话类（低并发、对 TTFT/TPOT 敏感）** 是推测解码的甜区；**批量离线推理** 常常没收益甚至负收益。vLLM 提供 `--speculative-disable-by-batch-size` 参数在高 batch 时自动关掉。

### 10.2 接受率 vs 草稿长度

- K 太小（2–3）：接受再多也就省 2 步；
- K 太大（>8）：接受率曲线平掉，但 Target verify 算力越堆越多；
- 甜点：**K = 4–6**，tree 方法（Medusa/EAGLE）在相同 budget 下把接受率拉高；
- 动态调整 K（按 recent 接受率）比固定 K 常常再涨 ~10%。

### 10.3 结合量化与 PD 分离

- **量化**（[第 14 篇](https://quant67.com/post/llm-infra/14-quantization/14-quantization.html)）：Target 用 AWQ/FP8 量化后显存带宽大幅下降，**推测解码收益随之下降**（反正 decode 也快了）；但 draft 也可以量化到更狠（INT4），整体还能保留 1.5–2×；
- **PD 分离**（第 13 篇已介绍）：推测解码只作用于 Decode 节点；Prefill 节点完全不用，部署时直接在 Decode pool 开 EAGLE 即可；
- **MoE 模型**：DeepSeek-V3 这种 MoE + MTP，本身 decode 阶段激活 37B 参数，推测解码继续把 tps 推高一档，这是 DeepSeek 能以相对低成本对外提供 API 的关键因素之一。

### 10.4 推测解码对输出一致性

严格使用 rejection sampling 的方法（Speculative / EAGLE / Lookahead / MTP 推测模式）**对采样分布无损**。Medusa 原版做 typical acceptance 近似（不严格无损但视觉上看不出差异），EAGLE 也可选 typical 模式。生产部署若要求 bit-exact 复现，需要检查引擎是否走精确 rejection sampling。

### 10.5 常见翻车

- Draft 和 Target tokenizer 不一致 → 全拒绝；
- 草稿头没随 Target 微调重训 → 接受率掉到 20%；
- 服务端 batch 大了没自动关 speculative → 吞吐反而下降；
- FP8 量化 Target + FP16 Draft，因数值差异 logits 分布漂移，接受率下降 5–10 pp；
- tree 方法下 top-k 设太大，verify forward 算力吃紧反而变慢。

## 十一、代码示例：Hugging Face + 原生 API 手搓 Speculative

给一个最小可跑的演示，用同家族两个尺寸模型做经典 Speculative：

```
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

tok = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-14B-Instruct")
target = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2.5-14B-Instruct", torch_dtype=torch.bfloat16, device_map="cuda:0"
)
draft = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2.5-1.5B-Instruct", torch_dtype=torch.bfloat16, device_map="cuda:0"
)

prompt = "写一个 Python 函数计算两个矩阵的 Kronecker 乘积。"
inputs = tok(prompt, return_tensors="pt").to("cuda:0")

# transformers ≥ 4.36 内置 assistant_model 就是经典 speculative decoding
out = target.generate(
    **inputs,
    assistant_model=draft,
    max_new_tokens=256,
    do_sample=False,
    num_assistant_tokens=5,          # K
    num_assistant_tokens_schedule="heuristic",  # 动态调整 K
)
print(tok.decode(out[0], skip_special_tokens=True))
```

在单张 A100 上 14B + 1.5B 的组合，上面一段代码生成的吞吐从 ~32 tok/s 提升到 ~78 tok/s（2.4×），且输出与关闭 `assistant_model` 时完全一致。

手写版（便于理解算法）：

```
@torch.no_grad()
def speculative_step(target, draft, input_ids, K=5, past_t=None, past_d=None):
    # 1) Draft K 个 token
    draft_tokens = []
    draft_probs = []
    cur = input_ids
    for _ in range(K):
        out = draft(cur, past_key_values=past_d, use_cache=True)
        past_d = out.past_key_values
        probs = torch.softmax(out.logits[:, -1], dim=-1)
        tok = probs.argmax(dim=-1, keepdim=True)  # 这里示意贪心；真正实现要随机采
        draft_tokens.append(tok)
        draft_probs.append(probs.gather(-1, tok))
        cur = tok

    draft_ids = torch.cat(draft_tokens, dim=-1)              # [B, K]
    full = torch.cat([input_ids, draft_ids], dim=-1)

    # 2) Target 一次前向同时打分 K+1 个位置
    out_t = target(full, past_key_values=past_t, use_cache=True)
    past_t = out_t.past_key_values
    t_logits = out_t.logits[:, -(K+1):]                       # [B, K+1, V]
    t_probs = torch.softmax(t_logits, dim=-1)

    # 3) 接受/拒绝
    accepted = []
    for i in range(K):
        p_t = t_probs[:, i].gather(-1, draft_tokens[i])
        r = torch.rand_like(p_t)
        if (r < torch.minimum(torch.ones_like(p_t), p_t / draft_probs[i])).all():
            accepted.append(draft_tokens[i])
        else:
            # 残差分布采样
            residual = (t_probs[:, i] - draft_probs_full[i]).clamp_min(0)
            residual = residual / residual.sum(-1, keepdim=True)
            new_tok = torch.multinomial(residual, 1)
            accepted.append(new_tok)
            return torch.cat(accepted, dim=-1), past_t, past_d
    # 全接受：从 p_{K+1} 再采一个
    bonus = torch.multinomial(t_probs[:, -1], 1)
    accepted.append(bonus)
    return torch.cat(accepted, dim=-1), past_t, past_d
```

生产就不用这么手搓了，交给引擎——但理解算法对调参、排障有决定性帮助。

## 十二、选型建议

 
|场景|推荐|
|---|---|
|已有开源模型，batch=1 聊天|**EAGLE-2/3**（官方发布 head），或 vLLM `--speculative-model` 套小尺寸|
|自研模型，想加速但不改预训练|EAGLE / Medusa head 微调|
|自研模型，从零训练|**学 DeepSeek-V3：预训练就带 MTP**|
|代码/结构化输出|**prompt lookup (n-gram)** 或 Lookahead，零成本见效|
|大 batch 离线推理|推测解码大概率无收益，不要开|
|显存极紧、无法部署 draft|Self-speculative（LayerSkip）|
|要求 bit-exact 无损|经典 Speculative / EAGLE（rejection sampling 模式）|
|数学题、代码补全|EAGLE-3 + 温度 0，目前效果最佳|

## 十三、小结

- 推测解码把 decode 从 “每步一 token” 变成 “每步验证多 token”，吃掉了 memory-bound decode 的算力冗余；
- 方法光谱：经典 Spec → Medusa（多头） → EAGLE（特征级自回归）→ Lookahead（无 draft）→ MTP（训练目标内嵌）→ Self-speculative（自己当 draft）；
- 工程重点：**接受率**、**draft 成本**、**batch 规模**、**与量化/PD 分离的组合**；
- 2025–2026 的事实标准组合：**EAGLE-3**（已有模型）+ **MTP**（新训练的模型，DeepSeek-V3 路线）+ **prompt lookup**（兜底、零成本）；
- 下一篇聊长上下文——当 seq len 上 1M 时，KV cache 和 attention 的工程挑战会把推测解码的收益进一步放大，因为 decode 越慢、推测空间越大。

## 参考资料

- Leviathan, Y., et al. _Fast Inference from Transformers via Speculative Decoding_. ICML 2023.
- Chen, C., et al. _Accelerating Large Language Model Decoding with Speculative Sampling_. DeepMind, 2023.
- Cai, T., et al. _Medusa: Simple LLM Inference Acceleration Framework with Multiple Decoding Heads_. 2023.
- Li, Y., et al. _EAGLE / EAGLE-2 / EAGLE-3: Speculative Sampling Requires Rethinking Feature Uncertainty_. 2024–2025.
- Fu, Y., et al. _Break the Sequential Dependency of LLM Inference Using Lookahead Decoding_. 2023.
- Gloeckle, F., et al. _Better & Faster Large Language Models via Multi-token Prediction_. ICML 2024.
- DeepSeek-AI. _DeepSeek-V3 Technical Report_. 2024.
- Elhoushi, M., et al. _LayerSkip: Enabling Early Exit Inference and Self-Speculative Decoding_. ACL 2024.
- Kou, S., et al. _CLLMs: Consistency Large Language Models_. 2024.
- vLLM / SGLang / TensorRT-LLM 官方文档 speculative decoding 章节。

---

**上一篇**：[【大模型基础设施工程】14：量化工程](https://quant67.com/post/llm-infra/14-quantization/14-quantization.html) **下一篇**：[【大模型基础设施工程】16：长上下文工程](https://quant67.com/post/llm-infra/16-long-context/16-long-context.html)

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