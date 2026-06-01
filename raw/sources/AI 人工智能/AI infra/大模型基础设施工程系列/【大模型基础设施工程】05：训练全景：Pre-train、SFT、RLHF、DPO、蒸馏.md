## 一、为什么要把训练当作一条”流水线”而不是一个训练脚本

很多同学第一次读 `torchrun --nproc_per_node=8 train.py` 的时候，会产生一种错觉：大模型训练=加大 batch、加大模型、加大数据、跑几个月。真实世界里完全不是这样。一个规模化 LLM 项目的训练栈更像一条炼油厂流水线：

- 上游是**数据工程**：抓取、清洗、去重、分类、配比、打包、打 tokenizer 的 tokens。
- 中游是**预训练（Pre-train）**：几千张 GPU 跑几十天，输出一个 base 模型 checkpoint。
- 再接**中训（Mid-train / Continued-PT）**：在 base 上注入数学、代码、推理、长上下文等”强化口味”的数据。
- 下游是**SFT（Supervised Fine-tuning）**：把模型从”补全文本”调成”能听懂指令”。
- 再经过**对齐（Alignment）**：RLHF、DPO、GRPO、RLAIF 等，把”会听懂”变成”有用、无害、诚实”。
- 旁路还有**蒸馏（Distillation）**：从大模型蒸出小模型，从推理模型蒸出非推理模型。

这一篇不去钻 3D 并行的细节（那是第 06 篇），也不展开 RLHF 的具体算法（第 09 篇），而是帮你建立一张**整体地图**：知道训练里每个环节在干什么、卡点在哪、业界主流选型是什么。如果你是团队里新加入的训练工程师，读完这一篇，至少在项目例会里能接得上大家的黑话。

## 二、四阶段工程栈：从 Pre-train 到 Alignment

### 2.1 总览

现代大模型（以 2024–2025 年 DeepSeek-V3、Qwen2.5、LLaMA-3.1、Kimi K1.5 的公开披露为参考）典型训练栈是四段：

```
原始文本/代码/多模态
        │
        ▼
┌──────────────────┐
│  Pre-train       │  数 T ~ 十几 T tokens；causal LM loss；几十天
└──────────────────┘
        │ base model (foundation)
        ▼
┌──────────────────┐
│  Mid-train /     │  数百 B ~ 数 T tokens；数学/代码/推理加权；长上下文扩展
│  Continued-PT    │
└──────────────────┘
        │ enhanced base
        ▼
┌──────────────────┐
│  SFT             │  数十万 ~ 数百万 instruction pairs；学格式 + 学行为
└──────────────────┘
        │ instruct model
        ▼
┌──────────────────┐
│  Alignment:      │  偏好数据；RLHF / DPO / GRPO / RLAIF / KTO ...
│  RL / DPO        │
└──────────────────┘
        │ aligned model (chat / reasoning)
        ▼
┌──────────────────┐
│  Distillation    │  旁路：teacher → student；推理蒸馏（o1/R1 范式）
└──────────────────┘
```

不同公司在这四段里投入的算力占比差别很大。粗略规律：

- **Pre-train** 吃掉 90%+ 的 GPU-hour。
- **Mid-train** 5% 左右，但对下游能力上限至关重要。
- **SFT** 通常不到 1%。
- **Alignment** 的算力不高，但**工程复杂度最高**（需要 reward model、PPO actor/critic、online rollout、数据反馈闭环）。

### 2.2 Pre-train：让模型”见过世界”

预训练阶段目标很朴素：给定一段文本前缀，预测下一个 token（causal LM）。Loss 是标准交叉熵。

工程上的核心挑战不是算法，而是：

1. **数据够不够、干不干净**：一次 13T tokens 的预训练，数据出错一轮，损失的是几千万美金。
2. **训练稳不稳**：loss spike、NaN、grad norm 爆炸，需要 checkpoint + 回滚 + 跳 batch。
3. **吞吐能不能打满**：3D 并行 + 通信重叠 + FP8，MFU（Model FLOPs Utilization）从 30% 抠到 50%+。
4. **故障能不能容忍**：千卡训练几十天，单卡 MTBF 几千小时，意味着**每天都有卡挂**。

### 2.3 Mid-train / Continued-PT：把”通才”拉向”硬核”

Mid-train 是 2024 年以后越来越标准化的阶段。在 base 快训完时，调整数据配比，显著加权**数学、代码、STEM、推理**类数据，同时往往把**上下文长度**从 4K/8K 扩到 32K/128K/1M。

- DeepSeek-V3 在后期阶段把上下文从 4K 扩到 32K 再到 128K，配合 YaRN 类方法。
- Qwen2.5 在 Continued-PT 阶段使用了更大比例的代码/数学数据，base 模型 MATH/HumanEval 分数大幅上升。
- LLaMA-3 也有类似的 “annealing” 阶段：降低学习率、换数据配比、刷高质量数据。

这一阶段的工程意义是：**在不重新花一遍预训练钱的前提下，用 5%~10% 的额外算力，拿到显著的能力跃升**。

### 2.4 SFT：教模型”听人话”

SFT 用指令-回答对（instruction pairs）做监督学习，loss 仅在 response 部分计算（prompt mask 掉）。典型规模：

- 早年 Alpaca / Vicuna：几万~几十万条；
- 当下头部开源模型：几百万条，且多轮、多任务、多领域。

SFT 的工程重点：

- **数据质量 >> 数据数量**：一条 GPT-4 生成的高质量答案，胜过十条人工糙活。
- **多轮对话拼接**：loss mask 只打在 assistant turn 上，system/user turn 不算 loss。
- **长样本打包（packing）**：把多条短样本拼到一个序列里，但用 attention mask 隔离，以榨干显存利用率。

### 2.5 Alignment：让模型”对得上人”

对齐阶段有一堆算法，工程上常见：

- **RLHF（PPO）**：经典三件套——SFT 模型、reward model、PPO actor+critic。复杂、吃显存、对超参敏感，但上限最高。
- **DPO（Direct Preference Optimization）**：不用 RL，直接在偏好对 `(chosen, rejected)` 上做对比损失。训练稳定、成本低，是开源社区主力。
- **GRPO（Group Relative Policy Optimization）**：DeepSeek 提出，去掉 critic，用一组 rollout 的相对 reward 做优势估计，在推理模型训练（R1）中大放异彩。
- **RLAIF**：用更强的 LLM 做 reward，替代人工标注，便宜但有偏差。
- **KTO、IPO、SimPO、ORPO**：DPO 变体，各家在稳定性与性能上微调。

第 09 篇会展开 RLHF 流水线，这里只需记住：**Alignment 的硬件需求小于 pretrain，但工程链路最长**——它闭环连接数据、模型、评测、灰度与线上反馈。

### 2.6 蒸馏：旁路的重要组件

蒸馏有两类：

1. **能力蒸馏**：大模型生成响应，小模型模仿。典型例子是 DeepSeek-R1 把 671B MoE 的推理能力蒸到 7B/14B/32B 的 Qwen/LLaMA 稠密模型。
2. **行为蒸馏**：让”推理模型”把思考链（CoT）蒸给”非推理模型”，得到成本可控的 production 模型。

工程上，蒸馏通常**复用 SFT 的代码路径**，区别是数据来源从”人工/GPT-4”变成”teacher model 在线生成”。

### 2.7 四阶段的算力 / 数据 / 工程复杂度速查

    
|阶段|典型 tokens|算力占比|主要瓶颈|典型 wall-clock|
|---|---|---|---|---|
|Pre-train|数 T ~ 15T|90%+|3D 并行 + 故障容忍|几周 ~ 几个月|
|Mid-train|数百 B ~ 2T|3%~8%|数据配比 + 上下文扩展|几天 ~ 几周|
|SFT|10M ~ 1B|<1%|数据质量 + packing|几小时 ~ 几天|
|Alignment|100M ~ 数 B（含 rollout）|1%~5%|rollout 吞吐 + reward 稳定性|几天 ~ 几周|
|Distillation|10B ~ 数百 B|视蒸馏深度|teacher 推理吞吐|几天|

这张表的意义在于预算规划：如果老板问”我给你 1000 张 H100 两个月，能不能训一版模型”，你至少知道时间主要花在哪，改哪个阶段能腾出空间做实验。

## 三、数据工程：训练成败的上限

### 3.1 数据源生态

- **Common Crawl**：互联网抓取的原始 HTML，数 PB，脏乱差但”量大管饱”，是所有预训练的基石。
- **C4（Colossal Clean Crawled Corpus）**：Google T5 清洗过的 Common Crawl 子集。
- **RedPajama**：开源社区复现 LLaMA-1 数据配方的 1.2T tokens 数据集。
- **The Pile**：EleutherAI 出品，825GB，多来源（书籍、代码、论文、Stack Exchange 等）。
- **书籍**：Books3（已因版权争议被下架）、Project Gutenberg、Anna’s Archive 等，争议持续存在。
- **代码**：The Stack（Hugging Face + ServiceNow），v2 有 900+ 语言、近 70TB。GitHub 数据是代码能力核心。
- **多语种**：CC-100、mC4、OSCAR；中文专项有 WuDaoCorpora、SkyPile-150B、MAP-CC 等。
- **学术/问答**：arXiv、PubMed、Stack Exchange、Wikipedia。
- **合成数据**：2024 年之后强势崛起——用 GPT-4 / Claude / DeepSeek 生成的高质量 QA、数学、代码是 Qwen、Phi、DeepSeek 等公开承认使用的资源。

国内公开数据集：

- **WuDaoCorpora**：智源，中文 5TB。
- **SkyPile-150B**：昆仑万维。
- **MAP-CC**：开源中文语料联盟。
- **CCI / CCI3**：智源+上海 AI Lab 的中文互联网清洗集。

### 3.2 去重：MinHash 与 SimHash

去重对 loss 与泛化的影响被反复验证。LLaMA、RefinedWeb、Dolma 都把**激进去重**写进了配方。

两大类技术：

- **MinHash + LSH**：对每个文档用 shingles → MinHash 签名 → LSH 分桶找近似重复。LLaMA、RedPajama、Dolma 都用它。阈值一般设 Jaccard ≥ 0.8。
- **SimHash**：Google 网页去重经典，签名短、速度快，但召回略低于 MinHash。

```
# datasketch 做 MinHash LSH 的最小示例
from datasketch import MinHash, MinHashLSH

def minhash(text, num_perm=128):
    m = MinHash(num_perm=num_perm)
    for shingle in (text[i:i+5] for i in range(len(text)-4)):
        m.update(shingle.encode("utf-8"))
    return m

lsh = MinHashLSH(threshold=0.8, num_perm=128)
for doc_id, text in docs:
    lsh.insert(doc_id, minhash(text))

# 查询近似重复
dups = lsh.query(minhash(new_text))
```

生产里一般不会直接用 datasketch，而是 Spark/Ray + GPU 加速的流水线（如 NVIDIA NeMo Curator、DataComp-LM 工具链）。

### 3.3 质量过滤与毒性过滤

典型流水线层次（从粗到细）：

1. **语言识别**：fastText、CLD3。
2. **启发式规则**：行长度、标点比例、重复率、HTML 残留、关键词黑名单（Gopher rules、C4 rules 都开源）。
3. **分类器过滤**：FastText 训练的质量分类器（以 Wikipedia、书籍为正样本，CC 为负样本），或 perplexity filter（用小 LM 过滤）。
4. **毒性/NSFW 过滤**：Perspective API、自研分类器；性暴力、仇恨言论、PII 打分。
5. **PII 脱敏**：邮箱、手机号、身份证号、信用卡号用正则 + NER 匹配替换。
6. **近似去重**：上节的 MinHash/SimHash。
7. **基准污染过滤（decontamination）**：扫描训练集里是否混入了 MMLU、GSM8K、HumanEval 等评测题目，必须清除，否则评测分是”偷来的”。

### 3.4 数据配比：几家公开配方

 
|模型|披露 / 推测的配比（摘要）|
|---|---|
|LLaMA-1|CC 67%、C4 15%、GitHub 4.5%、Wikipedia 4.5%、Books 4.5%、arXiv 2.5%、Stack Exchange 2%|
|LLaMA-3|未公开具体比例，但披露”代码占比显著提高、多语种 5%“、总量 15T tokens|
|DeepSeek-V3|14.8T tokens，中英双语为主，代码/数学比重高于 V2；FP8 训练|
|Qwen2.5|18T tokens，强化代码、数学、多语种；长文本阶段 1M 上下文|
|Mistral / Mixtral|未公开|
|Phi-3|强调”textbook quality”合成数据 + 精选网页|

**Mid-train 的配比变化**是能力突跳的关键：把代码+数学+推理从 20% 拉到 40%+，STEM 基准线性上涨，但会牺牲一些通识问答上的分布。

### 3.5 数据打包与 tokens 计数

预训练前，数据要被”打包”成固定长度的序列（如 4096 或 8192）。两种做法：

- **Document concat**：多篇文档用 `<eos>` 拼接后切片。训练效率高，但跨文档的 attention 可能引入噪声。
- **In-sample packing with attn mask**：拼接但用 block-diagonal attention mask 隔离文档，保证因果但避免跨文档污染。现代框架（Megatron-LM、DeepSpeed、Axolotl）基本都支持。

### 3.6 数据质量评估的几个实用维度

光看 token 数不够，下面几个维度是头部团队实际在盯的：

- **有效 tokens（effective tokens）**：去重 + 过滤后的净 tokens，不是原始抓取量。
- **语言/领域分布**：CC 天然偏英文和新闻，刻意补中文、代码、数学、STEM、长文本。
- **文档长度分布**：过短（< 128 tokens）和过长（> 64K）都要特别处理。
- **perplexity 分布**：用一个小 LM 打分，剔除极高（乱码）和极低（重复模板）。
- **重复 n-gram 率**：整体 6-gram 重复率 < 某阈值是常见准入条件。
- **毒性 / 偏见评分分布**：防止后续 alignment 需要花很大力气”洗”。
- **合成数据占比**：2024 年后一个新监控点，过高会放大模型自身的幻觉。

把这些指标做成每批数据的”data card”，与训练 ckpt 一起归档，是可审计训练流程的基础。

## 四、Tokenizer：经常被低估的关键组件

### 4.1 主流算法

- **BPE（Byte Pair Encoding）**：GPT-2、LLaMA、Mistral、Qwen、DeepSeek 都在用。从字节/字符出发，贪心合并频率最高的 pair。
- **WordPiece**：BERT 系列经典，和 BPE 类似但合并准则是似然而非频率。
- **SentencePiece**：Google 的实现，支持 BPE 与 Unigram，直接吃原始字节流（无需预分词），对多语种友好。
- **Unigram LM**：SentencePiece 的另一模式，LLaMA tokenizer 之前也用过。
- **Tiktoken**：OpenAI 的高性能 BPE 实现（Rust），被 GPT-3.5/4/4o 使用。

### 4.2 词表大小的权衡

  
|词表|优势|劣势|
|---|---|---|
|小（32K，LLaMA-1/2）|embedding 小，学习充分|中文、代码切碎，序列变长|
|中（64K~128K，LLaMA-3、Qwen2、DeepSeek-V3）|多语种友好，序列短|embedding 显存变大|
|大（200K+，GPT-4o）|极致多语种与符号覆盖|embedding 参数暴涨|

序列长度与词表的关系是**乘法关系**：词表翻倍，平均 tokens 数显著降低，训练和推理吞吐直接受益。DeepSeek-V3 的 tokenizer 词表扩到 128K，核心动机之一就是把中文压缩率提上去。

### 4.3 中文与 Unicode 的坑

- **BPE 要基于字节（byte-level BPE）**，而非 Unicode 字符，否则 emoji、罕见字会 OOV。GPT-2 以后都是 byte-level。
- **中文预分词**：SentencePiece 不需要，Tiktoken 用正则切分，会把中文切成单字或字+符号，对中文模型并不理想。
- **组合 emoji、ZWJ 序列**：测试 tokenizer 一定要覆盖。
- **数字处理**：LLaMA-1 的 tokenizer 把数字单独拆成 digit，对数学推理更友好；GPT-4 的 Tiktoken 在 o200k 词表里也调整了数字拆分。

```
# 用 tokenizers 库训练一个 byte-level BPE 的最小骨架
from tokenizers import Tokenizer, models, trainers, pre_tokenizers, decoders

tok = Tokenizer(models.BPE(unk_token="<unk>"))
tok.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
tok.decoder = decoders.ByteLevel()

trainer = trainers.BpeTrainer(
    vocab_size=128_000,
    special_tokens=["<|endoftext|>", "<|im_start|>", "<|im_end|>"],
    initial_alphabet=pre_tokenizers.ByteLevel.alphabet(),
)
tok.train(files=["corpus/*.txt"], trainer=trainer)
tok.save("tokenizer.json")
```

## 五、训练目标：不止 Causal LM

### 5.1 Causal LM

主流 decoder-only 模型的 loss：

```
L = -(1/T) * Σ_t log P(x_t | x_<t)
```

实现上就是把 `input_ids` 右移一位作为 `labels`，用交叉熵。

### 5.2 Masked LM

BERT 系列，15% 随机 mask 预测原 token。现在很少用于大模型预训练，但在 embedding 模型、检索模型、编码器上仍然是主力（BGE、E5、GTE 等）。

### 5.3 MoE 路由损失

MoE（Mixture of Experts）模型除了主 loss，还有**负载均衡损失（load balancing loss）**和**router z-loss**。DeepSeek-V3 在这一块提出了 **Auxiliary-Loss-Free Load Balancing**：不再靠额外 loss 强推 expert 均衡，而是在 gating 时对每个 expert 加一个动态 bias，运行时根据实际负载调整。这避免了辅助 loss 对主 loss 的扰动，是 V3 训练稳定的一个重要原因。

### 5.4 Multi-Token Prediction（MTP）

DeepSeek-V3 还引入了 MTP：每一步不仅预测下一个 token，还预测**未来 k 个 token**。这给了三重好处：

1. 训练信号更稠密，数据利用率提高；
2. 推理时可以作为**推测解码（speculative decoding）**的 draft，提升解码吞吐；
3. 对长距离依赖有轻微正则作用。

MTP 的 loss：

```
L_total = L_CE(t+1) + λ_1 * L_CE(t+2) + λ_2 * L_CE(t+3) + ...
```

第 15 篇会详细讲推测解码与 MTP 的推理侧应用。

### 5.5 几种训练目标的组合

现代 frontier 模型的 loss 很少只有一项。一个典型的 DeepSeek-V3 风格 loss：

```
L = L_CE(next)                         # 主 causal LM
  + λ_mtp * Σ_k L_CE(next+k)           # Multi-Token Prediction
  + λ_z * (logsumexp(logits))^2        # router z-loss（MoE）
  +  0                                 # aux-loss-free 负载均衡，不进 loss
```

对 LLaMA-3 这样的稠密模型则简单很多，几乎只有主 CE loss。多项 loss 之间的权重 λ 是工程玄学，一般会在小规模（1B~7B）上扫一次，然后 scale up 沿用。

## 六、优化器与学习率调度

### 6.1 Adam / AdamW：老将仍在

大模型训练事实标准是 **AdamW**：Adam + decoupled weight decay。原因：

- 自适应二阶动量对不同参数量级鲁棒；
- decoupled weight decay 避免和动量混淆，泛化更好。

代价是**显存 2x**：每参数除了 FP32 master weight 外，还有 m、v 两个状态。

典型超参（沿用 GPT-3/LLaMA 配方）：

```
AdamW(lr=peak_lr, betas=(0.9, 0.95), eps=1e-8, weight_decay=0.1)
```

`beta2=0.95`（而非默认 0.999）是大模型实践的共识，降低二阶动量的惯性可以避免长训练中的后期发散。

### 6.2 Lion：更省显存的黑马

Google 2023 年提出的 Lion 优化器只保留动量 m，用 sign-based 更新：

```
update = sign(β1 * m + (1 - β1) * g)
```

显存比 AdamW 省一半，在 ViT、语言模型上表现接近或更好。但对学习率和 weight decay 的调参窗口更窄，社区采用率不如 AdamW。

### 6.3 Muon：2024 的新秀

Muon（Keller Jordan 等）基于**矩阵正交化（Newton-Schulz 迭代）**对梯度做预处理，再施加动量更新。在 nanoGPT-speedrun 社区刷榜，**Kimi K2 在公开技术报告中明确使用 Muon 作为预训练优化器**，这是 Muon 在大规模生产里的重要背书。

工程上，Muon 只适合 2D 参数矩阵（全连接层、attention 投影），对 embedding、LayerNorm、1D bias 仍用 AdamW。这种”混合优化器”写法：

```
muon_params, adamw_params = [], []
for n, p in model.named_parameters():
    if p.ndim == 2 and "embed" not in n and "lm_head" not in n:
        muon_params.append(p)
    else:
        adamw_params.append(p)

opt_muon = Muon(muon_params, lr=0.02, momentum=0.95)
opt_adam = torch.optim.AdamW(adamw_params, lr=3e-4)
```

### 6.4 学习率调度

主流两种：

- **Warmup + Cosine Decay**：前 1%~3% 步 warmup 到峰值，然后 cosine 降到 10% 峰值。GPT-3、LLaMA、Qwen 等都用它。
- **WSD（Warmup-Stable-Decay）**：warmup → 长时间恒定 → 最后短衰减。MiniCPM、DeepSeek 等用过，好处是”decay 前可以当作 mid-train 的 base”，继续训练或 annealing 都方便。

```
lr
 │       cosine 方案
 │     /‾‾‾‾\
 │    /      \__________
 │___/                  \_
     warmup  plateau     end

 │       WSD 方案
 │     /‾‾‾‾‾‾‾‾‾‾‾‾\___
 │    /                 \
 │___/                   \_
     warmup   stable      decay
```

### 6.5 WSD 为什么适合现代训练

WSD 的一个隐性好处是”**stable 阶段的 checkpoint 可以当 base**”。你可以：

- 在 stable 阶段末尾存 ckpt，作为 continued-PT / mid-train 的起点；
- 不同方向的 mid-train（代码强化 / 数学强化 / 多语强化）基于同一 stable ckpt 分支实验；
- 最终 decay 阶段可以针对不同业务做多次独立 decay（用不同的数据配比），形成多个线上模型。

cosine scheduler 则要求你在训练开始时就决定好总步数，中途改步数会破坏几何性质，分支实验成本高。这也是为什么 MiniCPM、DeepSeek 之后越来越多团队切到 WSD。

## 七、精度：FP32 → BF16 → FP8 → FP6/FP4

精度演化直接决定训练成本：

   
|精度|典型硬件|代表|备注|
|---|---|---|---|
|FP32|所有 GPU|2017 以前|稳，慢|
|FP16 混合精度|Volta 以后|GPT-3、早期 LLaMA|需 loss scaling；动态范围小|
|BF16 混合精度|A100/H100|LLaMA-2/3、Qwen、GPT-4 训练主流|动态范围大 = FP32，精度略低|
|FP8|H100 Hopper|DeepSeek-V3 全流程 FP8、Llama-3 部分 FP8|E4M3 / E5M2 两种格式|
|FP6 / FP4|B200 Blackwell|2025 年起|推理主导，训练探索中|

### 7.1 混合精度的基本结构

```
forward / backward 用 BF16（或 FP8）
gradient all-reduce 用 BF16
optimizer state 用 FP32
master weight 用 FP32
每一步：FP32 master -> cast -> BF16 weight for forward
```

### 7.2 FP8 训练的工程要点

DeepSeek-V3 是第一个在完整预训练里把 **GEMM、通信、激活、梯度** 大面积切到 FP8 的公开案例。关键技巧：

- **每 block / 每 tile 动态 scaling**：粗粒度 per-tensor scaling 范围太小，per-token 或 per-128-elements scaling 更稳。
- **选择性回退**：对 LayerNorm、softmax、优化器 state 保留 BF16/FP32。
- **通信也用 FP8**：all-to-all、all-reduce 的带宽压力减半。

FP8 训练的工程难点不是”能不能跑起来”，而是”能不能全程无 spike 跑完 14T tokens”。

### 7.3 FP8 的两种格式：E4M3 vs E5M2

FP8 有两个 IEEE 近似变体：

- **E4M3**：4 位指数 + 3 位尾数，精度高、动态范围小，**用于前向激活和权重**。
- **E5M2**：5 位指数 + 2 位尾数，范围大、精度低，**用于反向梯度**（梯度的动态范围更广）。

NVIDIA Transformer Engine、Microsoft MS-AMP、DeepSeek 自研 FP8 kernel 都是基于这套分工。工程上最容易踩的坑是忘了给 **gradient** 用 E5M2，导致小梯度被 flush 到 0，训练后期 loss 不再下降。

### 7.4 精度选型的决策树

```
训练目标 = base 预训练？
├── 是 → 是否有 H100+ 和 FP8 工程能力？
│        ├── 有 → FP8（DeepSeek 风格），省 30%+ 成本
│        └── 无 → BF16，稳妥首选
└── 否（SFT/RLHF） → BF16 即可，FP8 收益小风险大
```

SFT/RLHF 阶段样本量小、迭代快，FP8 带来的吞吐收益有限，反而 debug 成本高，一般不建议。

## 八、批大小、学习率与训练稳定性

### 8.1 批大小 scaling

大 batch 的好处是通信代价被摊薄；坏处是**有效学习率**变大，容易发散。

- **线性缩放律**：batch 翻倍，lr 翻倍（Goyal 2017，ImageNet）。
- **平方根缩放律**：理论更稳，但 LLM 社区多数仍沿用线性，只是给足 warmup。
- **Critical batch size**：Kaplan 的论文给出”超过某个 batch，收益递减甚至负面”的临界点。大模型的临界 batch 在几百万到几千万 tokens 级别。

LLaMA-3、DeepSeek-V3 的全局 batch 常见于 4M~16M tokens。

### 8.2 损失 spike 的工程处理

长训练不可避免会遇到 loss spike。处理手段：

1. **梯度裁剪（grad norm clip）**：clip 到 1.0 是事实标准。
2. **skip batch**：遇到 NaN/Inf，丢弃当前 batch，回滚 optimizer 状态到上一步。
3. **checkpoint + 回滚**：如果 spike 不可恢复，从之前的 checkpoint 载回，跳过问题数据区段。
4. **数据怀疑论**：spike 80% 的原因是数据（长重复、乱码、错误标注），应先看数据。
5. **embedding 归一化 / weight decay 微调**：部分 spike 由 embedding 爆炸触发。
6. **监控 z-loss、router entropy**：MoE 模型专项。

### 8.3 一段值班日志的”标准 SOP”

假设你半夜收到告警：`grad_norm > 20, loss increased by 1.5`。标准排查：

1. 看最近 200 step 的 loss / grad_norm / lr 曲线，确认不是 scheduler 阶段性变化。
2. dump 当前 batch 的 input_ids，反 tokenize 看内容；统计 token 熵、重复 n-gram。
3. 检查 NCCL / IB 是否有 retransmit、是否掉卡。
4. 如果只是瞬时 spike 且后续 recover，不动；超过 3 个 batch 没 recover，从最近一个 ckpt rollback，跳过这段 data shards。
5. 记录事件：时间、step、影响 tokens、措施、结论，进事故库。

头部团队的训练事故库动辄几百页——这是最值钱的工程资产。

## 九、3D 并行的组合策略（概览）

详细内容在第 06、07 篇。这里只给一张速记表：

   
|并行方式|切什么|通信|何时用|
|---|---|---|---|
|DP（Data Parallel）|切 batch|all-reduce grad|永远用|
|TP（Tensor Parallel）|切 weight 矩阵|all-reduce activation|单层太大装不下单卡时|
|PP（Pipeline Parallel）|切 layer|P2P send/recv|模型层数很多、机间带宽不够时|
|SP（Sequence Parallel）|切 seq|all-gather / reduce-scatter|长上下文训练|
|EP（Expert Parallel）|切 MoE experts|all-to-all|MoE 专用|
|ZeRO（1/2/3）|切 optimizer / grad / param|reduce-scatter + all-gather|DP 的显存优化|

千亿-万亿规模的典型组合（以 DeepSeek-V3 / Qwen2.5-72B / LLaMA-3-405B 为参考）：

- **TP = 8**（单机内，NVLink 带宽足）
- **PP = 8 ~ 16**（跨机，容忍 IB 带宽）
- **EP = 8 ~ 64**（MoE 专用）
- **DP / ZeRO**：剩下的 GPU 数都分给 DP 维度
- **SP**：长上下文时打开

### 9.1 一条朴素的选型经验

- 单卡显存塞不下**一层** → 开 TP。
- 单机（8 卡 NVLink）塞不下**一整份模型** → 开 PP 或 ZeRO-3。
- 机间 IB 带宽紧张、PP bubble 不可接受 → 优先 ZeRO + 较大 micro-batch。
- 序列超过 32K → 打开 SP / context parallel。
- MoE 模型 → EP 先于其他维度考虑，all-to-all 是最贵的通信。

### 9.2 并行维度选择对通信量的直觉

定性上：

- TP 通信量 = O(batch × seq × hidden)，每一层都有，**最怕跨机**。
- PP 通信量 = O(batch × seq × hidden)，只有相邻 stage，**不怕跨机但怕 bubble**。
- DP/ZeRO 通信量 = O(params)，每步一次，**带宽敏感、延迟不敏感**。
- EP 通信量 = O(batch × seq × hidden × topk)，每层两次 all-to-all，**对对称带宽和 crossbar 敏感**。

所以”TP 放在 NVLink 域内，DP/ZeRO 放在 IB/RoCE 跨机域上”是黄金法则。

## 十、Scaling Laws：花钱怎么花最合算

### 10.1 Kaplan 2020

OpenAI 的 Kaplan 等人给出了第一个系统的 scaling law：loss 是模型参数 N、数据量 D、算力 C 的幂律函数。结论鼓舞人心——但它低估了数据的作用。

### 10.2 Chinchilla（Hoffmann 2022）

DeepMind 重新做实验后发现，Kaplan 对数据和模型的最优比例错了。**最优比例**大约是：

```
D* ≈ 20 * N
```

即每个参数配 ~20 tokens。GPT-3（175B 参数、300B tokens）被严重”undertrained”，而 Chinchilla（70B 参数、1.4T tokens）在同等算力下效果更好。

这之后，开源社区”**小而多数据**”成为共识：LLaMA-1 用 7B/13B/33B/65B + 1T~1.4T tokens，LLaMA-3 干脆把 8B/70B 训到 15T tokens——**远超 Chinchilla 最优**，因为推理时代，**推理成本 >> 训练成本**，把更多训练算力砸进去换来推理侧便宜是划算的。

### 10.3 推理时 scaling（o1 范式）

2024 年 OpenAI o1 带来新范式：**推理时算力**也是 scaling 维度。模型可以在推理时生成长 CoT、反思、回溯，用更多 tokens 换更高正确率。DeepSeek-R1、Kimi K1.5、Qwen QwQ 都跟进了这条路线。

对训练基础设施的影响：

- RL 阶段需要**大规模 online rollout**，推理集群和训练集群边界变模糊。
- 长 CoT 训练样本动辄几万 tokens，对长上下文训练压力大。
- 奖励建模变成”可验证答案（数学、代码）优先”的新范式。

### 10.4 三代 scaling 的对照

   
|范式|代表|scaling 的维度|主要成本|
|---|---|---|---|
|预训练 scaling|GPT-3 / LLaMA / DeepSeek-V3|参数 × 数据|训练算力|
|后训练 scaling|LLaMA-3 SFT+DPO、GPT-4 turbo|高质量偏好数据|数据标注 + 少量训练|
|推理时 scaling|o1 / R1 / K1.5|每 query 的 thinking tokens|推理算力（serving 成本）|

这三种 scaling 并不互斥。2025 年以后的头部模型基本都是”三种 scaling 同时吃”——预训练把 base 打到极限、后训练注入对齐与风格、推理时 CoT 堆出 top-tier 指标。

## 十一、训练成本估算

一个简洁近似：

```
训练 FLOPs ≈ 6 * N * D
```

其中 N 是参数量，D 是训练 tokens 数，系数 6 来自 forward + backward 的矩阵乘法计数。

代入几款模型：

    
|模型|参数|tokens|FLOPs 估算|公开 / 推测 GPU-hour|
|---|---|---|---|---|
|GPT-3|175B|300B|3.14e23|~3.6K PFs-days，估 ~$4.6M|
|LLaMA-3-70B|70B|15T|6.3e24|~6.4M H100-hours|
|LLaMA-3-405B|405B|15.6T|3.8e25|~30M H100-hours，约 $60M+|
|DeepSeek-V3|671B(37B 激活)|14.8T|约 3.3e24（激活记）|2.664M H800-hours，公开成本约 $5.58M|
|Qwen2.5-72B|72B|18T|7.8e24|未公开|
|GPT-4|未公开（推测 ~1.8T MoE）|~13T|~2e25|推测 60M 100M|

DeepSeek-V3 用不到 600 万美金完成训练成本震动行业，核心并非”算法新”，而是**把 FP8、MoE、通信重叠、MTP、国产 H800 集群工程**全部抠到极致。这个故事在第 07、08 篇会继续讲。

### 11.1 自己怎么估

对一个 N 参数稠密模型、D tokens 训练，用一张 H100（BF16 峰值 ~989 TFLOPS，实际 MFU 打 40%）来估：

```
有效算力  ≈ 989e12 * 0.40 = 3.96e14 FLOPs/s
总 FLOPs  = 6 * N * D
GPU-seconds = 总 FLOPs / 有效算力
GPU-hours   = GPU-seconds / 3600
```

以 70B × 2T tokens 为例：

```
总 FLOPs = 6 * 7e10 * 2e12 = 8.4e23
GPU-hours ≈ 8.4e23 / 3.96e14 / 3600 ≈ 5.9e5 ≈ 59 万 H100-hours
```

按 118 万，再叠加数据准备、失败重跑、调参实验，总成本 × 2~3 才接近真实预算。

### 11.2 MoE 为什么便宜

MoE 模型（如 DeepSeek-V3 的 671B/37B 激活）训练时只有激活参数参与梯度回传，等效 FLOPs 按 **激活参数量** 计算。所以 671B MoE 的训练成本接近一个 37B 稠密模型 × 训练 tokens，而推理效果接近 671B 稠密。这就是 MoE 的”参数便宜、FLOPs 贵”——训练时其实两头都占到好处。第 08 篇会展开 MoE 的训练工程细节。

## 十二、代表性训练框架

### 12.1 全球主流

- **Megatron-LM**（NVIDIA）：TP/PP/SP/EP 的工程标杆，LLaMA 之外大半头部公司基于它做二开。
- **DeepSpeed**（微软）：ZeRO 发源地，和 Megatron 整合成 Megatron-DeepSpeed。
- **PyTorch FSDP / FSDP2**：PyTorch 原生，社区优先，FSDP2 对 dtensor 与 TP 友好。
- **Colossal-AI**（潞晨，中国）：国产训练框架代表，兼容 PyTorch，提供 Gemini、ZeRO++、推理一体能力。
- **MegaBlocks**：MoE 训练专用，基于稀疏块矩阵乘法，Mixtral、Databricks DBRX 使用。
- **NeMo**（NVIDIA）：Megatron 之上的端到端套件，含数据 curation。
- **torchtitan**：Meta 出品，面向 LLaMA-3 一代的极简训练栈，FSDP2 + TP。
- **Levanter / EasyLM / MaxText**：JAX 生态。

### 12.2 中国实践

- **DeepSeek HAI-LLM**：自研训练框架，2048 张 H800 训练 V3；工程公开信息显示其 MFU 很高。
- **Qwen（阿里）**：基于 Megatron 二开；阿里 PAI-Megatron-Patch 对外开源。
- **Kimi（Moonshot）**：训练细节部分公开，K2 使用 Muon + MoE。
- **MiniMax**：abab 系列，自研稀疏注意力与 MoE。
- **智谱（GLM）**：自研 GLM 训练栈，开源 ChatGLM / GLM-4。
- **百川 / 书生·浦语（InternLM）**：均基于 Megatron/DeepSpeed 二开，InternEvo 开源。
- **火山方舟、百度千帆、阿里 PAI**：云厂商训练平台，封装上述框架并提供数据-训练-服务闭环。

### 12.3 怎么选

给到落地团队的建议：

- **1B 以下 / 学习研究**：直接 HuggingFace Trainer + Accelerate + FSDP，或 nanoGPT/torchtitan。别过早优化。
- **10B 量级 / 单机 8 卡 ~ 单集群**：FSDP2 + torch.compile + flash-attn 是性价比最高组合；想要 TP 的话切 Megatron-LM。
- **70B 量级 / 跨机**：Megatron-LM 或 Megatron-DeepSpeed；MoE 走 Megatron-Core + MegaBlocks。
- **400B+ / MoE 万亿**：几乎一定要在 Megatron-Core 上自研 patch。参考 DeepSeek 公开的 DualPipe、auxiliary-loss-free 实现，投入一支专门的训练基础设施团队。
- **国产卡集群**：优先看 MindSpore、PaddlePaddle、Colossal-AI、InternEvo、华为 ModelEngine 等对目标硬件（昇腾、海光、沐曦、摩尔线程）的适配度，别硬移 Megatron。

### 12.4 FSDP2 vs Megatron 的定位差

FSDP2（PyTorch 原生）的思路是”参数 shard + 按需 all-gather”，用户态代码改动小，对动态图友好，但 TP 能力弱。Megatron-LM 从一开始就是 TP 优先的，kernel 层深度定制，对 Transformer 模型更快，但侵入性强。2024 年以后两者在互相靠拢：FSDP2 加入 DTensor/TP 支持；Megatron-Core 把自己拆成可插拔模块。对大多数团队，**先 FSDP2，遇到吞吐/显存瓶颈再迁 Megatron**，是一条低风险路径。

## 十三、训练观测：你得盯住哪些曲线

一次长训练，值班工程师盯的是下面这几组曲线：

1. **loss / lm-loss**：整体是否单调下降；是否有 spike；是否在 plateau。
2. **grad norm**：应当相对稳定。突然变大多是问题。
3. **param norm / weight decay effect**：监控 embedding、lm_head、attention 投影的 L2。
4. **learning rate**：确保 scheduler 按预期。
5. **GPU util / MFU / tokens-per-sec-per-GPU**：吞吐核心指标。MFU 30% 是及格线，50%+ 是优秀，60%+ 是顶级。
6. **NCCL all-reduce 带宽 / bus bandwidth**：通信是否达到理论值的 80%。
7. **PP bubble ratio**：流水并行空泡占比。
8. **MoE：expert load、router entropy、drop rate**。
9. **显存水位**：剩余多少给 activation recomputation 的空间。
10. **硬件：NVLink error、ECC、温度、掉卡计数、链路 flap**。

典型栈：Prometheus + Grafana + DCGM Exporter + NCCL tests + 自研 trainer hook，把 loss/grad/lr 写到 W&B / TensorBoard / Swanlab。

### 13.1 MFU 的计算口径

MFU（Model FLOPs Utilization）= 实际达到 FLOPs / 理论峰值 FLOPs。**实际 FLOPs** 通常按 `6 * N * D / time` 近似；**理论峰值**取你卡的 BF16/FP8 TFLOPS × GPU 数。常见口径陷阱：

- 用了 FP8 GEMM 但算 FLOPs 仍按 BF16 峰值：会显著低估 MFU。
- 算进了 activation recomputation 的多余计算：会”伪高估” MFU。
- 没扣除 dataloading/checkpoint/eval 时间：分母偏大，MFU 偏低。

社区惯例：报 MFU 时应注明是否包含 recompute、精度是什么、是否 steady-state（跳过 warmup 步）。DeepSeek-V3、LLaMA-3 论文在附录都明确交代了这一点。

### 13.2 一份最小观测 checklist

每 step 至少打：step、loss、grad_norm、lr、tokens/s、mem_alloc、mem_reserved。每 N step 打一次：MFU、NCCL bandwidth、ckpt latency、loader queue size。每次 eval 打：MMLU / GSM8K / HumanEval / 中文 C-Eval / 领域集分数（不要只看 loss，loss 降了能力不一定涨）。

## 十四、单步训练循环（Mermaid）

## 十五、训练流水线全景图（SVG）

![训练流水线全景图（SVG）](https://quant67.com/post/llm-infra/05-training-overview/images/05-training-overview-fig1.svg)

## 十六、一个最小可跑的训练骨架

用 PyTorch + FSDP + BF16，演示单步循环所有关键动作，供理解概念（不要直接拿去训千亿模型）。

```
import torch
import torch.distributed as dist
from torch.distributed.fsdp import FullyShardedDataParallel as FSDP
from torch.distributed.fsdp import MixedPrecision
from torch.utils.data import DataLoader
from transformers import AutoModelForCausalLM, AutoTokenizer

def main():
    dist.init_process_group("nccl")
    rank = dist.get_rank()
    torch.cuda.set_device(rank % torch.cuda.device_count())

    tok = AutoTokenizer.from_pretrained("meta-llama/Llama-3.2-1B")
    model = AutoModelForCausalLM.from_pretrained(
        "meta-llama/Llama-3.2-1B", torch_dtype=torch.bfloat16
    ).cuda()

    mp = MixedPrecision(
        param_dtype=torch.bfloat16,
        reduce_dtype=torch.bfloat16,
        buffer_dtype=torch.bfloat16,
    )
    model = FSDP(model, mixed_precision=mp, use_orig_params=True)

    opt = torch.optim.AdamW(model.parameters(), lr=3e-4, betas=(0.9, 0.95),
                            weight_decay=0.1)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=10_000)

    loader = DataLoader(my_packed_dataset, batch_size=4, num_workers=4)
    grad_accum = 8

    model.train()
    for step, batch in enumerate(loader):
        ids = batch["input_ids"].cuda(non_blocking=True)
        labels = batch["labels"].cuda(non_blocking=True)

        out = model(input_ids=ids, labels=labels)
        loss = out.loss / grad_accum
        loss.backward()

        if (step + 1) % grad_accum == 0:
            gn = model.clip_grad_norm_(1.0)
            opt.step(); sched.step(); opt.zero_grad(set_to_none=True)

            if rank == 0 and step % 100 == 0:
                print(f"step {step} loss={loss.item()*grad_accum:.4f} "
                      f"grad_norm={gn.item():.2f} lr={sched.get_last_lr()[0]:.2e}")

        if (step + 1) % 5000 == 0 and rank == 0:
            torch.save({"model": model.state_dict(), "opt": opt.state_dict(),
                        "step": step}, f"ckpt-{step}.pt")

if __name__ == "__main__":
    main()
```

这个骨架你会发现它就是前面”单步训练循环”Mermaid 图的代码翻译：data → forward → loss → backward → all-reduce → optimizer → scheduler → ckpt → metrics。

## 十七、常见踩坑清单（工程经验）

### 17.1 数据类

- **重复样本进了训练集**：去重阈值设得太松，某条热门文章在 CC 里出现几千次，模型反复”背”它。表现：perplexity 局部异常低，loss 曲线在某些 token 上”奇迹般地”降得特别快。治理：Jaccard 0.8 起步、文档级 + 段落级双层去重。
- **评测集污染**：MMLU、GSM8K、MATH、HumanEval、BBH、MBPP、AGIEval、C-Eval、CMMLU 的题目以各种形式混进训练集（论坛抄题、答案解析博客、GitHub）。治理：把所有评测集建成 bloom filter / MinHash 签名库，数据准备阶段强制扫描。对命中样本不光删除，还要审计它污染了几期 snapshot。
- **HTML 残留**：`<script>`、`<style>`、导航栏广告、“订阅我们的 newsletter”模板文，这类噪声累计起来相当可观。治理：trafilatura / jusText / 自研 extractor，同时监控行长分布和标点密度。
- **PDF 抽取错位**：论文 PDF 两栏布局被抽成乱序行，数学公式变成 `( 1 ) + + x - 2`，越多越害。治理：Nougat、MinerU、Mathpix 等结构化抽取 + 人工 spot check。
- **编码问题**：中英混合 gbk/utf-8 切错、emoji 被 replacement char 替代、零宽字符潜伏。治理：chardet + 强制 utf-8 round-trip。

### 17.2 训练类

- **第一小时 loss 不降**：99% 是 lr、data、mask 之一出错。常见：pad token 的 loss 没 mask 掉，导致 loss 常数地高。
- **训到一半显存突增**：activation 缓存 + 长序列 + gradient checkpointing 没开满。治理：torch.cuda.memory 分析 + 只在前 N 层开 activation recompute。
- **grad norm 先平稳后缓慢爬升**：embedding 或 lm_head 的 L2 在无界增长。治理：weight decay 加到 lm_head、embedding tying、或加 z-loss。
- **AdamW 的 beta2=0.999 对大 batch 不稳**：LLaMA-3 把 beta2 降到 0.95。
- **FP8 loss spike**：per-tensor scale 太粗，长尾激活炸掉。治理：tile-wise scale + 选择性 BF16 fallback。
- **MoE expert dead**：某些 expert 永远拿不到 token。治理：aux-loss-free balancing、router reset、或在初始化阶段做 expert dropout。

### 17.3 基础设施类

- **一张卡挂了，整个 job 挂**：没做弹性。治理：torchrun elastic、Megatron 的 resilient training、或 DeepSpeed 的 robust checkpoint。
- **NCCL 超时**：掉卡、链路闪断、IB retransmit 堆积。治理：`NCCL_TIMEOUT`、`TORCH_NCCL_ASYNC_ERROR_HANDLING=1`，监控 IB 的 counters。
- **存储慢导致 ckpt 写 30 分钟**：异步 checkpoint 几乎是必选项。PyTorch DCP、Nebula、GCS 等各家都在做。
- **读数据慢导致 GPU idle**：webdataset / tar shard / mmap Arrow，预取和解码多进程一定要够。
- **时钟漂移 / NTP 不同步**：rank 之间 timing 奇怪，偶发 hang。治理：集群级 chrony + 预检脚本。

## 十八、训练与推理的工程分界正在模糊

2024 年之后的一个新趋势：训练和推理的工程栈在打通。

- **RLHF / GRPO 的 rollout 阶段需要大规模高吞吐推理**：vLLM、SGLang、TensorRT-LLM 现在常被用作 RL 训练管线里的 policy 推理后端。DeepSeek-R1、Kimi K1.5 的技术报告都提到使用专用推理集群做 rollout。
- **推测解码的 draft 模型是训练产物**：MTP head 本身就是预训练阶段联合训出来的，推理时直接启用。
- **合成数据闭环**：teacher 模型（往往是上一代自家大模型）在推理集群批量生成，直接喂进下一代训练。训练-推理共用同一套 tokenizer、同一套模板、同一套 chat format，任何偏差都会被放大。
- **在线学习 / online RL**：未来几年会看到更多”边推理边采集偏好，分钟级更新 reward model”的系统。训练侧与服务侧的边界会进一步消失。

这是第 11～22 篇（推理、服务化、RAG、Agent）会反复呼应的主题：**“先训练、后推理”的瀑布模型，正在被”训练-推理-反馈”的闭环模型取代**。作为基础设施工程师，你需要同时理解两端。

### 18.1 一个正在成形的”训推一体”架构

可以预期未来 2~3 年，头部团队的底层架构会长成这样：

```
 ┌───────────────┐       ┌───────────────┐
 │  训练集群      │◀─────▶│  推理集群      │
 │ Megatron/HAI  │ sync  │ vLLM/SGLang    │
 └──────┬────────┘       └──────┬─────────┘
        │                         │
        ▼                         ▼
  ┌──────────────────────────────────────┐
  │ 共享 tokenizer / chat template / 评测 │
  └──────────────────────────────────────┘
        ▲                         ▲
        │ data feedback           │ rollout
        │                         │
  ┌──────────────────────────────────────┐
  │  数据 / 标注 / 偏好 / 奖励模型        │
  └──────────────────────────────────────┘
```

训练集群不再只吃静态 dataset，而是持续消费推理集群生成的 rollout 和用户反馈；推理集群不只是产品入口，也充当训练的”数据工厂”。这个拓扑对网络、存储、对象桶、元数据管理提出了完全不同的要求，也是后面几章会持续展开的方向。

## 十九、写给新人的学习路径

如果你是刚加入训练团队的工程师，下面这条学习路径被验证过是有效的：

1. **用 nanoGPT（Andrej Karpathy）在单卡 A100 上从零训一个 100M 的 char-level 模型**。走完一遍 data → tokenizer → forward → backward → ckpt → eval，感性认知。
2. **在 2 张卡上跑 torchrun + FSDP 训一个 1B 模型**。理解 DP、shard、all-reduce、显存水位。
3. **在 8 张卡上跑 Megatron-LM 的 GPT 例子**，打开 TP=2, PP=2, DP=2，观察 MFU、bubble、通信。
4. **读一遍 Chinchilla 和 DeepSeek-V3 的论文**，算一次 FLOPs 账。
5. **把一次小规模 SFT + DPO 跑通**，用 TRL 或 OpenRLHF 之类的上层工具。
6. **最后再回头**读 Megatron 源码的 `transformer_engine` 集成、`distributed_optimizer` 实现——这时你看代码不再是看天书，而是看到”每一行在解决我当初遇到的那个 OOM / spike / slow”。

一个小建议：**每一步都写训练日志**。不是代码 log，是你自己的工程笔记——“为什么这个 lr 先炸，改到多少稳下来”“这个 spike 最终定位是哪批数据”“这个 MFU 从 28% 提到 41% 靠的是什么”。半年后回头看这些笔记，胜过读十篇论文。

## 二十、小结：训练是一条流水线，不是一个脚本

回到开头的那张图。如果要给准备做训练基础设施的工程师留三句话：

1. **数据决定上限**：再好的 infra 也补不回脏数据。把去重、过滤、配比、污染检测做成可复用、可 diff、可审计的流水线，比加卡更重要。
2. **小步快跑、监控前置**：loss、grad norm、MFU、expert balance，这些曲线是训练事故的”X 光片”。事故永远不会提前预约，但曲线会。
3. **栈要开源友好**：Megatron、DeepSpeed、FSDP2、Colossal-AI、HAI-LLM、InternEvo——没有任何团队能闭门造车。把自己的 patch 提回上游，既是社区贡献，也是组内知识资产化。

补充三条”非技术”的经验：

4. **训练项目要有剧本**：什么阶段产出什么 ckpt、在什么评测集上验证、谁来决定是否 promote 到下一阶段——写进 runbook，避免临时拍板。
5. **每一轮失败都归档**：OOM、NaN、spike、掉卡，每一次异常都写进事故库并关联到具体 commit 与数据 snapshot。知识沉淀的速度决定了第二次、第三次训练能比第一次快多少。
6. **别信”最佳实践”**：整个行业每半年一次大变（FP8、MoE、Muon、WSD、GRPO）。保持读最新技术报告的习惯，**尤其是中国团队的**——DeepSeek、Kimi、Qwen、MiniMax 的公开细节是过去两年信息密度最高的一批。

后面的章节会把本篇”概览提到但没展开”的关键点拆开：第 06 篇讲 3D 并行细节，第 07 篇讲 Megatron + DeepSpeed 的实操，第 08 篇讲 MoE，第 09 篇讲 RLHF 流水线，第 10 篇讲 checkpoint 与故障容忍。希望这一篇帮你在脑中建好了训练栈的”骨架”，后续内容挂上去就是”血肉”。

## 参考资料

- Kaplan et al., “Scaling Laws for Neural Language Models”，2020
- Hoffmann et al., “Training Compute-Optimal Large Language Models”（Chinchilla），2022
- Touvron et al., “LLaMA 2 / LLaMA 3” technical reports，Meta，2023–2024
- DeepSeek-AI, “DeepSeek-V3 Technical Report”，2024
- DeepSeek-AI, “DeepSeek-R1: Incentivizing Reasoning via Reinforcement Learning”，2025
- Qwen Team, “Qwen2.5 Technical Report”，Alibaba，2024
- Moonshot AI, “Kimi K2 / K1.5 Technical Report”，2025
- NVIDIA, “Megatron-LM” 与 “NeMo” 官方文档
- Microsoft, “DeepSpeed” 与 “ZeRO” 系列论文
- Rajbhandari et al., “ZeRO: Memory Optimizations Toward Training Trillion Parameter Models”，2020
- Jordan, “Muon: An optimizer for hidden layers in neural networks”，2024
- Rafailov et al., “Direct Preference Optimization”，2023
- Shao et al., “GRPO / DeepSeekMath”，2024
- Common Crawl / RedPajama / The Pile / The Stack 官方数据集文档

---

**上一篇**：[互联与网络：NVLink、InfiniBand、RoCE、国产替代](https://quant67.com/post/llm-infra/04-interconnect/04-interconnect.html) **下一篇**：[3D 并行深度：数据 / 张量 / 流水 / 序列 / ZeRO](https://quant67.com/post/llm-infra/06-parallelism/06-parallelism.html)

## 同主题继续阅读

把当前热点继续串成多页阅读，而不是停在单篇消费。

2026-04-22 · architecture / ai-infra

### [大模型基础设施工程](https://quant67.com/post/llm-infra/index.html)

面向中国工程团队的大模型基础设施系列。从 GPU/CUDA/互联、训练框架与 3D 并行、vLLM/SGLang 推理引擎、量化与推测解码、RAG/Agent 到服务化、网关、可观测性与安全合规，覆盖 LLMOps 全链路。

2026-04-25 · architecture / ai-infra

### [【大模型基础设施工程·特别篇】DeepSeek-V4 与国产芯片：从备份路线到主路径](https://quant67.com/post/llm-infra/26-deepseek-v4-domestic-chip/26-deepseek-v4-domestic-chip.html)

DeepSeek-V4 发布后，如果国产芯片已经支撑旗舰模型的关键训练或推理链路，它会怎样影响 NVIDIA 生态、国产 AI 芯片、云厂商、模型团队和工程师的技术选择？

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】01：大模型基础设施全景 —— 训练、推理、RAG、Agent、观测](https://quant67.com/post/llm-infra/01-intro/01-intro.html)

面向工程师的大模型基础设施开篇地图，覆盖 2022 到 2026 的工程分水岭、五层工程栈、训练与推理的工程差异、中国与全球行业版图以及成本曲线。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】09：RLHF 与对齐流水线](https://quant67.com/post/llm-infra/09-rlhf-pipeline/09-rlhf-pipeline.html)

从 SFT、奖励模型到 PPO、DPO、GRPO 的完整对齐流水线工程实践，覆盖 OpenAI o1、DeepSeek-R1 等推理模型的 RL 路线与主流框架选型。