上一篇《[推理引擎基础](https://quant67.com/post/llm-infra/11-inference-basics/11-inference-basics.html)》把 Prefill / Decode、KV cache、吞吐/延迟三大指标梳理了一遍。但如果仅靠这些基本盘，LLM 服务大概只能跑出 HuggingFace Transformers 级别的吞吐——面对真实业务几百上千 QPS 的请求洪流，GPU 利用率往往只有 20–30%，显存则一半以上在”等未来可能用到”。

2022 年底 Orca 提出 **iteration-level scheduling（迭代级调度）**、2023 年 vLLM 把它和 **PagedAttention** 合并为一套通用引擎，一举把 LLaMA-13B 的吞吐做到 HF Transformers 的 **14–24 倍**、TGI 的 **2.2–3.5 倍**。从那以后，“连续批处理 + 分页 KV 缓存”几乎成为所有生产级推理引擎（vLLM、SGLang、TensorRT-LLM、TGI、Mindie、LMDeploy、RTP-LLM……）的默认骨架。

本篇把这两项技术、以及围绕它们演化出的 **Chunked Prefill**、**Prefix Caching**、**Priority Scheduling**、**vLLM v1 架构** 讲透，并给出可直接上线的调参手册。

## 一、传统推理为什么慢

### 1.1 静态批处理的三宗罪

静态批处理（static batching）是 TensorFlow Serving / TorchServe 时代的标配：凑齐 N 条请求 → 一起送进模型 → 一起返回。对 CV 的图像分类这很合理——每条请求的计算量几乎一样。但 LLM 不是。

**罪一：等最长**。一个 batch 里最短的请求生成 20 token、最长的 2000 token，整个 batch 得跑 2000 步。先完成的那几条请求的 GPU slot 在剩下 1980 步里完全浪费。

**罪二：按最长预留显存**。HuggingFace `generate()` 习惯用 `max_new_tokens` 预先 allocate KV cache。假设 batch=32、max_seq_len=4096、hidden=5120、num_layers=40，光 KV cache 就是 `32 × 4096 × 40 × 5120 × 2 × 2B ≈ 107 GiB`。即便平均实际长度只有 800 token，**60–80% 的显存被空置**。A100 80G 当场 OOM。

**罪三：Prefill 与 Decode 混批效率低**。Prefill 是 compute-bound（每个 token 一次 matmul），Decode 是 memory-bound（每步一次 KV 读）。硬塞在同一个 step 里，要么 decode 等 prefill，要么 prefill 被拆成小块喂给 decode kernel，两头不讨好。

### 1.2 一个具体的数字

拿 LLaMA-7B / A100-80G 举例：

|方案|batch|平均 GPU util|吞吐（tok/s）|
|---|---|---|---|
|HF `generate()` batch=1|1|8%|40|
|HF 静态 batch=16|16|35%|600|
|vLLM continuous batching|动态 ~64|85%+|5500+|

吞吐差距近 10×，核心不是 kernel 快了，而是**空闲时间被消灭了**。

### 1.3 核心洞察

LLM 推理的 decode 阶段，每一步只前进 1 个 token——**这正是”换人”的最佳切点**。既然每一步都要重新跑一次 attention，那就每一步都重新决定”谁上、谁下、谁插队”。

这就是 Continuous Batching 的立足点。

### 1.4 还有哪些”隐性损耗”

除了以上三宗罪，传统推理还有几类不那么明显但同样致命的损耗：

- **Tokenizer 阻塞主循环**：Python 侧 tokenizer 如果和 forward 同线程，长 prompt 的 tokenize 本身就可能吃掉几十毫秒；
- **Sampling 在 CPU**：top-k、top-p、重复惩罚等后处理如果回到 CPU 做，每步都有 GPU→CPU→GPU 的往返；
- **Request 到达的泊松性**：真实流量不是均匀的，静态 batch 凑不齐就死等；
- **权重加载冷启动**：HF `from_pretrained` 在主循环里做，首次请求 TTFT 爆炸；
- **CUDA graph 缺失**：每步 forward 都走 eager 模式、反复 launch kernel，overhead 在小 batch 下很明显；
- **Attention mask 的 padding**：静态 batch 下 pad 到 max_len，然后让 attention 忽略 pad 位——本质是白算了很多 FLOPs。

现代引擎（vLLM / SGLang / TRT-LLM）这些点基本都处理好了：tokenizer 独立线程池、sampler 完全在 GPU、异步请求队列、权重预加载和 warmup、CUDA graph 捕获常见 shape、PagedAttention 天然无 padding。但自己手搓推理时，这些坑一个都跑不掉。

### 2.1 Orca 的 iteration-level scheduling

2022 OSDI 的 Orca 论文（Yu et al., SNU + FriendliAI）提出：**调度粒度从 request 降到 iteration**。

传统调度：

```
Request A: [====================] 2000 steps
Request B: [===]                  30 steps   ← 完成后 slot 空转 1970 步
Request C: [=======]              500 steps  ← 完成后 slot 空转 1500 步
```

迭代级调度：

```
step 1:  [A, B, C, D]
step 31: B 完成 → [A, C, D, E(新来)]
step 501:C 完成 → [A, D, E, F(新来)]
...
```

每跑完一步 forward，调度器检查： 1. 哪些 sequence 产生了 EOS / 达到 max_tokens → **立即下架**，返回结果给客户端； 2. 队列里有没有新请求 → **立即上架**（先做 prefill，再和大家一起 decode）； 3. 剩余显存够不够容纳下一步的 KV。

### 2.2 Prefill 与 Decode 的混批难题

新请求插队需要先 prefill，其 token 数可能是几百上千；而老请求的 decode 每条只要 1 个 token。把 prefill 和 decode 强行拼到一个 batch 里，shape 不齐、kernel 不友好。

Orca 的做法是 **selective batching**：让 attention 算子按 sequence 各自算，其他算子（Linear、LayerNorm）按 flatten 的 token 维度算。这样不同长度的 token 可以共享 matmul，attention 各算各的。

vLLM 更进一步，用 **PagedAttention kernel**——我们下一节讲。

### 2.4 SVG：Continuous Batching 时序图

下图对比了静态 batch（上）和 continuous batch（下）的 GPU 占用模式。静态 batch 的右侧大片空白是”等最长”的浪费，continuous batch 则被新请求连续填满。

![SVG：Continuous Batching 时序图](https://quant67.com/post/llm-infra/12-paged-continuous/images/12-paged-continuous-fig1.svg)

### 2.5 实现细节：内存屏障与调度周期

调度每步都要做： 1. 收集已到达的新请求 → 放入 waiting queue； 2. 检查上一步完成情况 → 把 EOS/max_tokens 的 seq 从 running 里移除； 3. 尝试从 waiting 里拉请求到 running（需要足够的 KV block）； 4. 构造本步的 batched tensor（token ids、position ids、block_tables、slot_mapping）； 5. 调用 forward； 6. sampling、更新 KV、检查停止条件。

其中 3–6 要非常快——如果这段逻辑比 GPU forward 还慢，GPU 就会空转。这就是为什么 vLLM v0 的 Python 调度被重写成 v1 的 C++ 调度：当 batch 很大、请求翻动频繁时，Python 侧每步几毫秒的 overhead 积累起来就能把 GPU util 打到 60%。

### 2.6 为什么只有 LLM 这么搞

Transformer 的 auto-regressive decode **天然可中断、可恢复**：每一步输入都是”过去的 KV + 当前 token”，没有跨 step 的中间激活需要保留（相对应地，训练就不行——要留所有 activation 做反向）。这让 iteration-level 调度的切换成本几乎为零。

CV 模型（CNN、ViT 分类）、传统 Transformer encoder 做不了 iteration 级调度，因为它们是一次性前向、没有”自我延续”的结构。这也是为什么 continuous batching 基本只在 LLM 推理世界流行。

## 三、PagedAttention：给 KV Cache 做虚拟内存

Continuous Batching 把”谁在跑”的问题解决了，但”跑起来之后 KV cache 怎么放”还是个大问题：每条请求长度不同、还在增长，物理内存必须连续——这和操作系统在 1960 年代面对的内存碎片是同一类问题。

### 3.1 传统做法：预分配 max_seq_len

为每条 sequence 预先 malloc 一段连续显存：

```
GPU DRAM:
[Seq A: reserved 4096 tokens | Seq B: reserved 4096 | Seq C: ... | ... ]
       实际用 230                实际用 88              实际用 12
```

浪费率： - **内部碎片**：reserved - used（预留但没用到） - **外部碎片**：一条 seq 下架后释放出的窟窿，放不下后来 4096 的新请求

vLLM 论文实测 KV 显存**实际利用率只有 20–40%**。

### 3.2 PagedAttention 的操作系统类比

|OS 虚拟内存|PagedAttention|
|---|---|
|进程|Sequence|
|虚拟地址|逻辑 block index|
|物理页（4KB）|KV block（默认 16 token）|
|页表|Block table|
|缺页中断|分配新 block|
|swap in/out|显存/内存/磁盘三级迁移|
|COW（写时复制）|parallel sample / beam search 共享 block|

**核心思想**：KV cache 不再要求物理连续。把每层、每个 head 的 KV 切成固定大小的 block，逻辑 block 到物理 block 通过 block table 查表。

### 3.3 数据结构

```
Sequence A（20 token）：
  block_table = [17, 42, ?]  # block size=16，前 2 个 block 已满，第 3 个还在填
  逻辑地址 token_id=18 → block 1 内 offset 2 → 物理 block 42 offset 2

Sequence B（33 token）：
  block_table = [7, 23, 5, ?]

Physical memory pool（每格 16 token 的 KV）：
  [ blk0 | blk1 | ... | blk5(SeqB) | ... | blk7(SeqB) | ... | blk17(SeqA) | ... ]
```

每次 decode 时： 1. 模型计算出新 token 的 K/V； 2. 查当前 seq 的最后一个 block 有没有空位 → 有则追加；没有则从空闲池 alloc 一个物理 block； 3. Attention kernel 根据 block_table 跳转读取历史 KV。

### 3.4 SVG：逻辑/物理 block 映射

![SVG：逻辑/物理 block 映射](https://quant67.com/post/llm-infra/12-paged-continuous/images/12-paged-continuous-fig2.svg)

### 3.5 天然支持的三类高级场景

**Parallel sampling（同 prompt 生成 N 条）**：prompt 部分的 block 所有 sample 共享（引用计数 += N），只在某个 sample 开始分叉时 COW。省一大截 prefill 计算与 KV 显存。

**Beam search**：beam 候选间也用 COW 共享公共前缀。

**Prefix sharing**：多个请求共享系统 prompt、few-shot demo 的 block——这就是 §5 要讲的 Prefix Caching。

### 3.6 PagedAttention Kernel

核心是把普通 FlashAttention 的 “K[b, h, :T, d]” 连续访问，改成 “按 block_table 跳转访问”。vLLM 基于 FlashAttention 做了 paged 版本：

```
// 伪代码
for (int block_idx = 0; block_idx < num_blocks; block_idx++) {
    int phys_block = block_table[seq_id][block_idx];
    // 从物理 block 地址读 K / V 分块，参与 softmax(QK^T) V
    load_kv_block(kv_cache + phys_block * block_stride, ...);
    online_softmax_accumulate(...);
}
```

对 kernel 侧来说，唯一的新增开销是每个 block 多一次间接跳转（L2 命中良好）。实测 paged attention 比 FlashAttention 原生慢不到 5%，却换来了几倍的显存利用率和吞吐——**完胜**。

### 3.7 block_size 的取舍

默认 16 token/block。可选 8、16、32（早期也支持 64，后期多数引擎收敛到 16）。

  
|block_size|优点|缺点|
|---|---|---|
|8|内部碎片更小，KV 利用率 > 95%|指针开销大、L2 未命中率略高、短 seq 无差异|
|16（默认）|平衡点|——|
|32|kernel 读取连续性更好|短请求内部碎片变大|

一般**别改**。除非在做极端短 prompt（<32 token）且 throughput 敏感的场景，可以试 8。

### 3.8 COW 与引用计数

PagedAttention 对 parallel sample / beam search 的支持，本质是一套简化版的**引用计数 + COW（Copy-On-Write）**：

```
初始：prompt 有 3 个 block（0,1,2），ref_count 都 = 1
parallel_sample(n=4)：
    给 4 个 sample 各自的 block_table 都填 [0, 1, 2]
    ref_count 变成 [4, 4, 4]

sample_0 开始 decode：
    最后一个 block 2 的 ref_count > 1，不能原地追加
    → alloc 新 block 7，把 block 2 的内容复制过去，写入新 token
    → sample_0 的 block_table 变成 [0, 1, 7]
    → block 2 的 ref_count -= 1 → 3

sample_1, sample_2, sample_3 类似各自分叉

最终：blocks 0, 1 永远共享；block 2 在第一次 decode 时被各自 COW
```

在 beam search 中（beam=4，每步保留 top-4 候选），前缀的显存和计算开销几乎只付一份。对 `n=4` 的 parallel sampling，KV 显存从 4× prompt 降到 ~1× prompt，这是 PagedAttention 在实际产品（比如代码补全 “给我 4 个候选”）中隐形省钱的关键。

### 3.9 Swap 的 IO 代价

前面提过抢占时可以 swap 到 CPU。一个 block ~3.5 MiB；PCIe 4.0 x16 理论 32 GB/s、实测 ~25 GB/s。一条 8K seq = 512 blocks = 1.75 GiB，swap out 约 70 ms。对比重算 8K prefill（~200 ms on A100），**swap 通常更快**——但前提是 PCIe 没有和其他流量打架。多卡 TP 时，PCIe 上还有权重加载、NVLink 之外的梯度同步等，swap 的实际延迟会更高。

### 3.10 业界的其他”分页”变体

PagedAttention 并非唯一的 KV 管理方案。一些变体：

- **Block-sparse KV**（DeepSpeed-FastGen）：block 粒度 + 稀疏访问模式；
- **Ring KV**（Ring Attention）：长上下文下 KV 按环拓扑在多卡间分片，和 PagedAttention 正交；
- **Token-level KV pool**（早期 FasterTransformer）：不分块，直接 token 连续存储，抢占代价大；
- **Tile-based KV**（TensorRT-LLM）：和 PagedAttention 概念近似，tile size 可配。

在工程选型上，只要是现代引擎，底层都是”某种形式的分块 + 间接映射”，差别主要在 block 大小、元数据布局、和 attention kernel 的耦合度。PagedAttention 胜在**开源、通用、生态完整**。

## 四、Chunked Prefill：消灭 TTFT 抖动

### 4.1 问题

老的 vLLM 调度策略：**prefill 优先**。只要队列里有新请求，就先做完 prefill 再继续 decode。一条 4K token 的 prefill 可能要跑 30–100 ms，这期间所有正在 decode 的请求都被冻住——**尾延迟（P99 TPOT）爆炸**。

但如果**decode 优先**，新请求可能迟迟得不到响应，**TTFT（首 token 时延）飙高**。

### 4.2 Chunked Prefill 的做法

Sarathi 论文（Microsoft）提出：**把长 prefill 切成小块，每块与正在 decode 的请求混在一个 batch 里**。

配置一个 `max_num_batched_tokens`（例如 2048）： - 本 step 先塞满所有 decode 请求（每条 1 token，比如 64 条 decode）； - 剩下的预算（2048 − 64 = 1984 tokens）分给 prefill：可以是某条新请求 prefill 的一个 chunk，也可以是多条新请求各切一小段； - 下一 step 继续。

```
step t:  [64 × decode] + [A 的 prefill chunk: 1984 tokens]
step t+1:[64 × decode] + [A 的 prefill chunk: 1984 tokens]
step t+2:[64 × decode] + [A 剩余 128 + B 的 prefill 1856]  ← A prefill 完成，开始 decode
step t+3:[65 × decode] + [B 的 prefill chunk ...]
```

效果： - 每 step 总 token 数固定 ≈ `max_num_batched_tokens`，**延迟抖动小**； - decode 不再被整段 prefill 阻塞，**TPOT 稳定**； - 代价是单条请求的 prefill 拖长（但对用户而言 TTFT 仍可控，因为第一块 chunk 出来就能继续）。

vLLM 0.6+ 默认开启 chunked prefill；SGLang、TensorRT-LLM 也都内置了等价机制（TRT-LLM 称之为 “in-flight batching + chunked context”）。

### 4.3 Chunk 大小的选择

`max_num_batched_tokens` 本质是”每步 token 预算”。一些经验值：

|GPU|模型|建议 `max_num_batched_tokens`|
|---|---|---|
|A10 / L4 (24 GB)|7B FP16|1024–2048|
|A100-40G|7B / 13B|2048–4096|
|A100-80G|13B / 34B|4096–8192|
|H100-80G|70B TP=4|8192–16384|

太小 → prefill 切得太碎，单条请求的 TTFT 被拖长；太大 → 每步 forward 耗时长，decode 的 TPOT 尾延迟变差。推荐做法：**压测画 latency-throughput 曲线**，选 P99 TPOT 在 SLA 内的最大值。

### 4.4 和 Continuous Batching 的关系

Continuous Batching 解决”谁在 batch 里”，Chunked Prefill 解决”每个 step 塞多少 token”。两者正交、配合使用。

### 4.5 Prefill-Decode Disaggregation（分离部署）

2024 年后出现一种更激进的方案：**把 prefill 和 decode 放到不同的 GPU / 节点**。

- **Prefill 节点**：compute-bound，堆 FLOPS，batch 小、step 间隔长；
- **Decode 节点**：memory-bound，堆显存带宽、多 batch，step 间隔短；
- 中间通过 **KV cache 传输**（NVLink / RDMA）把 prefill 出的 KV 推给 decode 节点。

代表作：DistServe（2024）、Mooncake（月之暗面，2024）。Mooncake 在 Kimi 生产上落地，把 TTFT 和 TPOT 的互相干扰彻底拆开。代价是架构复杂度爆炸，要做 KV cache 路由、跨机传输、容错。规模 > 千卡的服务值得做，中小规模 chunked prefill 就够。

## 五、Prefix Caching：省下重复的 Prefill

### 5.1 动机

真实业务里大量请求共享前缀：

- **系统 prompt**：`"你是一个专业客服助手，回答要简洁……"`（~500 token），每个请求都带；
- **Few-shot 示例**：`"输入：A 输出：B / 输入：C 输出：D / 输入：E 输出：..."`（~2000 token）；
- **长文档 RAG**：同一份文档被反复问不同问题；
- **多轮对话**：第 N 轮请求 = 第 N-1 轮 prompt + N-1 轮回复 + 新问题。

这些前缀的 KV cache 算一次就能复用，没必要每次都 prefill。

### 5.2 vLLM 的 Prefix Caching（Hash）

vLLM 按 block（16 token）对前缀做哈希：`hash(block_content + hash(prev_block))`。两条请求共享同样的前缀 block → 哈希表命中 → block_table 直接指向同一个物理 block（引用计数 +1）。

- 命中的 block **跳过 prefill 计算**；
- 只有前缀首次 mismatch 的 block 之后才开始新的 KV 计算；
- LRU 淘汰：当 KV 池满，引用数为 0 的 block 按 LRU 释放。

命令行打开：

```
vllm serve Qwen/Qwen2.5-7B-Instruct --enable-prefix-caching
```

### 5.3 SGLang 的 RadixAttention

SGLang（Zheng et al., 2024）把前缀共享做到了极致：**Radix Tree（基数树）管理 token 序列**。

- 所有请求共用一棵 tree；
- 新请求到来时，沿着 tree 走最长公共前缀 → 这部分 KV 直接复用；
- 走到第一个 mismatch 节点 → 从该节点分叉；
- LRU 回收时按 tree 叶子优先淘汰。

相比 vLLM 的 block 级 hash： - 命中粒度是 **token 级**（更准）； - 对 Agent、ReAct、树搜索这类**前缀分叉高**的工作负载优化明显（命中率能到 80–95%）； - SGLang 还内置结构化输出（JSON schema / grammar），对 tool use 场景很舒服。

### 5.4 命中率对数据的影响

一组参考数据（Qwen2.5-7B、A100、系统 prompt 800 tokens）：

|场景|前缀命中率|TTFT|吞吐（req/s）|
|---|---|---|---|
|关闭 prefix cache|0%|220 ms|42|
|vLLM hash prefix cache|92%|38 ms|115|
|SGLang RadixAttention|96%|28 ms|130|

TTFT 降一个数量级、吞吐翻 2–3 倍。**生产环境强烈建议开启**。

### 5.5 注意事项

- **隐私**：prefix cache 跨请求共享 KV，如果前缀里有用户敏感数据，要按 tenant 隔离 cache（vLLM `--enable-prefix-caching` 全局共享，需自行在网关层做 tenant key）；
- **一致性**：模型权重变更后务必清缓存；模型升级、量化精度切换都需要 flush；
- **显存预算**：prefix cache 占住的 block 也算在 KV 池里，命中率高时等于”白赚”，命中率低时会挤压 in-flight 请求的空间；
- **Tokenizer 一致性**：跨服务复用 cache 时（比如多副本、多引擎共享远端 KV），tokenizer 必须逐字节一致，否则哈希对不上；
- **观察 Evict 频率**：若 `prefix_cache_evict_rate` 长期偏高，说明 KV 池装不下热前缀集合，要么加显存要么缩前缀；
- **Prompt 顺序**：即便内容一样，顺序不同的 prompt（如 few-shot 位置变化）也 miss。如果能控制上游，尽量固化前缀顺序。

### 5.6 多级 KV 缓存

生产系统里，prefix cache 通常不只放 GPU 显存。业界正在形成**三级结构**：

```
L1: GPU HBM      —— 高速、容量小（几十 GiB）
L2: CPU DRAM     —— 中速（~20 GB/s PCIe）、容量中（百 GiB 级）
L3: NVMe / 分布式 —— 低速（~5 GB/s）、容量大（TB 级，跨机共享）
```

- Mooncake 把 L2/L3 做成**集群级 KV pool**，所有推理节点共享；
- SGLang `--enable-hierarchical-cache` 支持 CPU offload；
- vLLM 社区也在做 `kv_connector` 插件对接外部 KV 存储（例如 LMCache 项目）。

对长上下文、系统 prompt 超长（8K+）、RAG 文档复用密集的场景，多级 KV 几乎是”必配”。

## 六、Priority Scheduling：当显存不够

### 6.1 抢占（Preemption）

假设当前有 100 条 decode、KV 占满 90%。突然来一条超长 prompt 新请求，prefill 需要 20 个新 block，但池里只剩 5 个。怎么办？

vLLM 的两种抢占策略：

**Recompute**：挑一条优先级最低（或最近到达）的 seq，**释放它的所有 block**、把它踢回等待队列。后续再调度时从头 prefill。 - 优点：简单、无 IO； - 缺点：重算代价 = 之前的 prefill + 已生成 decode 步数的 prefill 等价计算。

**Swap**：把被抢占 seq 的 KV block **换出到 CPU 内存**，通过 PCIe 拷走。恢复时再 swap in。 - 优点：保留已有计算； - 缺点：PCIe 带宽有限（~30 GB/s），大 batch 时 swap 开销可能比 recompute 还大。

经验法则：**seq 短、显存压力偶发 → swap；seq 长、显存压力持续 → recompute**。vLLM 默认 recompute。

### 6.3 优先级调度的几个维度

真实系统里，“谁先跑”通常要看：

- **SLA tier**：付费用户 / 免费用户 / 内部测试；
- **Deadline**：流式场景里，某条请求已经等了 2 秒，再不响应就超时；
- **Job type**：同步 API（低延迟敏感）vs 离线 batch（只看吞吐）；
- **LoRA adapter**：多 LoRA 服务时，已加载的 LoRA 的请求优先，减少 LoRA 切换开销；
- **公平性**：同一 tier 内用 weighted fair queueing 防止大请求饿死小请求。

### 6.4 Fairness vs Throughput

FIFO 调度简单但不公平（长请求饿死短请求）；优先队列（按 deadline / SLA / user tier）更复杂。vLLM 社区近年在做 `priority`、`preempt_mode`、`lora_priority` 等字段。生产系统通常在**网关层**做 user-level rate limiting 和优先级分类，再下发给推理引擎。相关内容第 22 篇”大模型网关”会详细展开。

## 七、vLLM v0 → v1：引擎重写

### 7.1 v0 的痛点

vLLM v0（2023–2024）架构： - **Python 主循环**：调度器用 Python 写，每 step 都要过一次 Python → C++ → CUDA → C++ → Python； - **Block manager 开销**：Python 侧管理 block_table，每 step 有可观的 CPU overhead； - **CPU 阻塞 GPU**：batch 数大、请求变更频繁时，CPU 调度成为瓶颈，GPU 反而空转； - **功能补丁多**：prefix cache、chunked prefill、LoRA、spec decode 都以补丁形式叠加，代码路径复杂。

### 7.2 v1 的重构（2025）

vLLM v1（官方在 2024 年底开始 RFC，2025 年逐步 GA）做了几件事： - **调度器从 Python 搬到 C++**（或用更高效的 Rust/C++ 引擎层）； - **零 CPU 阻塞**：调度与 forward 在不同线程 pipeline，GPU 饱和度提升； - **统一的 request lifecycle**：prefill / decode / preempt / prefix-hit 走同一条路径； - **原生多模态**：Vision encoder 与 LLM decoder 共享调度； - **更好的 PP/TP 支持**：多卡推理的调度同步开销大幅下降。

官方数据：vLLM v1 在 LLaMA-3-70B / 8× H100 上，吞吐相对 v0 再 **+30–100%**，P99 延迟降低 **30–50%**。

启用方式（0.6.x+）：

```
VLLM_USE_V1=1 vllm serve meta-llama/Llama-3.1-8B-Instruct
```

到 0.7.x 已默认启用，并逐步移除 v0。

### 7.3 v1 的新能力

除了性能，v1 还带来几个重要能力：

- **Prefix caching 内建**：v0 下 prefix cache 是可选插件，v1 下是默认路径的一部分；
- **Spec decoding 一等公民**：draft model、Medusa、MTP 都统一到调度器（第 15 篇详细展开）；
- **Structured output**：JSON schema / regex 约束原生支持（追赶 SGLang）；
- **Multi-LoRA**：同时加载多个 LoRA adapter，按请求路由；
- **Disaggregated prefill**：v1 的 `kv_connector` 接口为分离部署铺路。

### 7.4 升级建议

- 生产老服务（vLLM 0.4/0.5）：先小流量灰度 v1，重点验证**吞吐、TTFT、P99 TPOT、prefix 命中率、LoRA 路由**；
- 新服务直接上 v1；
- 某些自定义 kernel / 自研 sampler 在 v1 可能还没 port，临时可 `VLLM_USE_V1=0` 回落；
- 多模态（Vision-LM）v1 支持明显更好，有需求建议直接 v1。

### 7.5 Python 性能的边界

顺带一提：Python 并非全无优势。Python 调度的好处是**生态和灵活性**——插件、钩子、自定义采样器、快速迭代。v1 把**热路径**搬到 C++，但暴露的 Python API 和插件机制仍在。这是”快路径低语言、慢路径高语言”的经典工程取舍。

对自研团队的启示：先用 Python 把功能做对，再用 profiling 识别真正的 overhead 热点做下沉。vLLM 的演化路径是非常好的参考案例。

## 八、工程实操：vLLM 上线手册

### 8.1 起一个 OpenAI 兼容服务器

```
pip install vllm

vllm serve Qwen/Qwen2.5-7B-Instruct \
  --host 0.0.0.0 --port 8000 \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.9 \
  --max-model-len 8192 \
  --max-num-batched-tokens 4096 \
  --max-num-seqs 256 \
  --enable-prefix-caching \
  --enable-chunked-prefill
```

启动后 `http://localhost:8000/v1/chat/completions` 即为 OpenAI 格式接口，可直接对接 LangChain、LlamaIndex、OpenAI SDK。

### 8.2 关键参数解读

  
|参数|含义|建议|
|---|---|---|
|`--gpu-memory-utilization`|KV 池占显存比例|0.85–0.92；留 5–10% 给 activation 和 overhead|
|`--max-model-len`|支持的最大 context|按业务需要；越大 KV 池能塞的请求越少|
|`--max-num-batched-tokens`|单 step 最多处理 token 数（含 prefill + decode）|2048–8192；越大吞吐越高、延迟波动越大|
|`--max-num-seqs`|同时在 batch 里的 seq 上限|128–512；和 KV 池大小一起定|
|`--tensor-parallel-size`|TP 切分数|单机多卡；多机要加 `--pipeline-parallel-size`|
|`--block-size`|KV block 大小|16（默认）|
|`--enable-prefix-caching`|前缀复用|开（除非多租户隔离要求严格）|
|`--enable-chunked-prefill`|分块 prefill|开（vLLM 0.6+ 默认）|
|`--swap-space`|CPU swap 空间（GiB）|4–16；承担抢占换出|
|`--kv-cache-dtype`|KV 精度|`auto` / `fp8`（SM89+，显存翻倍）|

### 8.3 KV 显存测算

启动时 vLLM 会打印类似：

```
# GPU blocks: 2048, # CPU blocks: 512
```

每个 GPU block = `block_size × 2 × num_layers × num_kv_heads × head_dim × dtype_bytes`。

例：Qwen2.5-7B（32 层、28 KV head、128 dim、FP16、block_size=16） `16 × 2 × 32 × 28 × 128 × 2 = 3.5 MiB / block`

A100-80G（扣掉权重 14 GiB、activation ~2 GiB，剩 ~60 GiB 给 KV）→ 约 17000 blocks。同时在线 ≈ 17000 × 16 / 平均 seq_len。若平均 1K token → **~270 条并发**。

### 8.4 压测脚本

```
# bench.py —— 用 vLLM 自带或 wrk/k6 都行，这里用 asyncio + openai SDK
import asyncio, time, random
from openai import AsyncOpenAI

client = AsyncOpenAI(base_url="http://localhost:8000/v1", api_key="x")

SYSTEM = "你是一个简洁的中文客服助手。" * 20  # ~300 token 系统 prompt，测 prefix cache

async def one_req(i):
    t0 = time.time()
    r = await client.chat.completions.create(
        model="Qwen/Qwen2.5-7B-Instruct",
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"帮我写一段关于主题 {i} 的 100 字介绍。"},
        ],
        max_tokens=200,
    )
    return time.time() - t0, r.usage.completion_tokens

async def main(n=200, concurrency=64):
    sem = asyncio.Semaphore(concurrency)
    async def go(i):
        async with sem:
            return await one_req(i)
    t0 = time.time()
    results = await asyncio.gather(*[go(i) for i in range(n)])
    dur = time.time() - t0
    tokens = sum(x[1] for x in results)
    print(f"QPS={n/dur:.1f}, tok/s={tokens/dur:.0f}, avg_latency={sum(x[0] for x in results)/n:.2f}s")

asyncio.run(main())
```

对比开/关 `--enable-prefix-caching`，实测 QPS 能差 2–3 倍。

### 8.5 直接用 `LLM` 离线推理

```
from vllm import LLM, SamplingParams

llm = LLM(
    model="Qwen/Qwen2.5-7B-Instruct",
    gpu_memory_utilization=0.9,
    max_model_len=4096,
    enable_prefix_caching=True,
)

sp = SamplingParams(temperature=0.7, max_tokens=256)

prompts = [
    "用 Python 写一个快速排序。",
    "用 Python 写一个归并排序。",
    "用 Python 写一个堆排序。",
] * 100  # 300 条请求

outputs = llm.generate(prompts, sp)
for o in outputs[:2]:
    print(o.outputs[0].text[:120], "...")
```

vLLM 会自动做 continuous batching——300 条请求并不会按顺序跑，而是同时在引擎里”流动”。

### 8.6 Prefix Caching 效果对比

```
import time
from vllm import LLM, SamplingParams

SYS = "You are a helpful assistant.\n" + "示例：Q: 1+1 A: 2\n" * 100  # 长系统 prompt

def bench(enable_cache):
    llm = LLM(model="Qwen/Qwen2.5-7B-Instruct",
              enable_prefix_caching=enable_cache,
              gpu_memory_utilization=0.85)
    sp = SamplingParams(max_tokens=64)
    prompts = [SYS + f"Q: 求 {i}*{i} 等于多少？A:" for i in range(200)]
    # 预热
    llm.generate(prompts[:4], sp)
    t0 = time.time()
    llm.generate(prompts, sp)
    return time.time() - t0

print("no  cache:", bench(False), "s")
print("with cache:", bench(True),  "s")
# 典型结果：no=42s / with=11s，约 4× 加速
```

### 8.7 关键监控指标

上线后要盯的指标（vLLM 暴露 Prometheus `/metrics` 端点）：

  
|指标|含义|健康区间|
|---|---|---|
|`vllm:num_requests_running`|当前 in-flight 请求数|接近 `max_num_seqs` → batch 打满，好|
|`vllm:num_requests_waiting`|排队请求|持续 > 0 → 容量不足|
|`vllm:num_requests_swapped`|被 swap/抢占的|> 0 → 显存压力，降 GMU 或减 max_seqs|
|`vllm:gpu_cache_usage_perc`|KV 池占用率|70–90% 健康；>95% 易抢占；<50% 资源浪费|
|`vllm:cpu_cache_usage_perc`|CPU swap 池占用|越低越好|
|`vllm:prefix_cache_hit_rate`|前缀命中率|业务相关；客服/RAG 应 > 80%|
|`vllm:time_to_first_token_seconds`|TTFT|P95 < 500 ms（交互场景）|
|`vllm:time_per_output_token_seconds`|TPOT|P95 < 50 ms|
|`vllm:e2e_request_latency_seconds`|端到端延迟|业务 SLA|
|`vllm:prompt_tokens_total` / `generation_tokens_total`|累计 token|算成本|

配合 Grafana dashboard（社区有现成的）实时观察。TTFT 尖峰通常对应 prefill 阻塞；TPOT 尖峰对应 batch 内有长 seq 抢计算；swap 频繁对应 KV 池压力。

### 8.8 常见调参决策树

```
服务刚上线、还没压测？
  ├─ 先用默认：GMU=0.9, max_num_seqs=256, max_num_batched_tokens=2048
  └─ 开 prefix caching + chunked prefill

发现 TTFT 高？
  ├─ max_num_waiting 持续 > 0 → 容量不足，加卡 or 降 max_model_len
  ├─ 长 prompt 多 → 调大 max_num_batched_tokens、看 chunked prefill 是否开
  └─ 前缀固定 → 开 prefix cache

发现 TPOT 尖峰？
  ├─ 查 prefill/decode 混批比例，缩小 prefill chunk
  └─ 看是否有超长 seq 在 decode，考虑 max_model_len 裁剪

发现 OOM / 频繁 swap？
  ├─ 降 GMU 到 0.85
  ├─ 降 max_num_seqs
  ├─ 开 fp8 KV cache（kv_cache_dtype=fp8）
  └─ 量化模型（AWQ/GPTQ，第 14 篇）

吞吐上不去、GPU util 低？
  ├─ max_num_seqs 偏小 → 调大
  ├─ max_num_batched_tokens 偏小 → 调大
  └─ CPU 成瓶颈 → 切 v1
```

### 8.9 多机多卡部署

TP（张量并行）单机内用 NVLink 跑，延迟低；PP（流水并行）跨机，延迟高但能装更大模型。vLLM 支持：

```
# 单机 8 卡 TP=8，跑 70B
vllm serve meta-llama/Llama-3.1-70B-Instruct \
  --tensor-parallel-size 8 \
  --gpu-memory-utilization 0.92

# 2 机 × 8 卡，TP=8 + PP=2，跑 405B
# 用 Ray 做 worker 编排
ray start --head                       # node0
ray start --address=<node0-ip>:6379    # node1
vllm serve meta-llama/Llama-3.1-405B-Instruct \
  --tensor-parallel-size 8 \
  --pipeline-parallel-size 2
```

要点： - 跨机 PP 对延迟有可感的增加（每层多一跳），对吞吐影响小； - 建议跨机走 InfiniBand / RoCE，参见第 4 篇《[互联与网络](https://quant67.com/post/llm-infra/04-interconnect/04-interconnect.html)》； - 调度与 KV 管理在 PP 下复杂度上升，v1 对这一块做了专门优化。

### 8.10 灰度与回滚

生产环境换引擎、升版本、改参数，请遵循：

1. **先离线 benchmark**：用业务采样的真实 prompt 分布，对比新旧配置的 QPS、TTFT、TPOT、准确性；
2. **小流量金丝雀**：1–5% 流量、观察 24h，重点看 P99 尾延迟、OOM 次数、prefix 命中率、生成质量（抽样人审或自动打分）；
3. **逐步放量**：10% → 30% → 50% → 100%，每一档观察至少一个完整的流量周期；
4. **准备回滚**：保留老版本的镜像、配置、warmup 脚本，出问题 5 分钟内切回；
5. **观测大屏对比**：新旧版本关键指标同屏，便于即时判断。

特别注意：vLLM 不同 minor 版本（例如 0.6 → 0.7）之间，默认参数、内部行为可能有变化（比如 v1 默认开、prefix cache 默认开等），**必须重测**，不能直接信赖旧配置。

## 九、性能与对手

### 9.1 吞吐对比（LLaMA-2-13B / A100-80G，来自 vLLM 论文与社区复现）

|引擎|吞吐（req/s）|相对 HF|
|---|---|---|
|HuggingFace Transformers|0.3|1.0×|
|DeepSpeed-MII|0.9|3×|
|FasterTransformer|1.5|5×|
|TGI v0.9|2.1|7×|
|vLLM v0|4.7|16×|
|vLLM v1|6.8|23×|
|SGLang（prefix 命中高）|7.5|25×|
|TensorRT-LLM（手调 kernel）|8.0|27×|

注：吞吐绝对值会随模型、请求分布、上下文长度剧烈变化。**相对排序**比绝对数字更有参考价值。

### 9.1.1 不同请求分布下的差异

同一台 A100-80G、同一个 7B 模型，不同请求分布吞吐能差数倍：

|分布|特点|vLLM 吞吐（req/s）|
|---|---|---|
|短 in / 短 out（Q&A，128/128）|大 batch、decode 为主|160|
|中 in / 中 out（聊天，512/512）|均衡|85|
|长 in / 短 out（摘要，4K/128）|prefill 为主|35|
|短 in / 长 out（创作，128/2K）|decode 为主、长尾|45|
|长 in / 长 out（RAG+长答，4K/1K）|双头压力|18|

所以做容量规划时，**必须用业务真实分布压测**，拍脑袋选”10× HF”这种通用数字会严重偏离。

### 9.2 对手画像

**SGLang**（UC Berkeley / LMSYS）： - RadixAttention → 前缀命中率一流； - 结构化输出 / 语法约束 / DSL（LMQL 风格）； - Agent、tool call、ReAct 场景首选； - 近年也补齐了 TP/PP/量化，差距在缩小。

**TensorRT-LLM**（NVIDIA）： - In-flight batching ≈ continuous batching； - Paged KV cache + 手工优化的 CUDA kernel（MHA/GQA 特化、FP8）； - 极限吞吐最强，但**编译流程复杂**（要 build engine）、灵活性差； - 多卡 / H100 / Blackwell 上优势明显。

**TGI**（HuggingFace）： - 生态好、易上手，但性能近年被 vLLM 拉开； - 2024 之后重构为 TGI v3，吸收了 paged / chunked 思路。

**LMDeploy / RTP-LLM / Mindie**（国内厂）： - 原理一致，都用 continuous batching + paged KV，各有侧重（Mindie 针对昇腾 NPU、LMDeploy 量化完善、RTP-LLM 蚂蚁生产验证）。

### 9.3 不同工作负载的引擎偏好

不同业务特征对引擎的敏感度不同，一张速查表：

  
|负载特征|首选引擎|原因|
|---|---|---|
|短 prompt + 短生成（问答、分类）|vLLM|continuous batching 稳|
|长系统 prompt + 频繁重复（客服、RAG）|SGLang|RadixAttention 命中率高|
|Agent / 多轮 / 树搜索|SGLang|radix + 结构化输出|
|超长上下文（128K+）|SGLang / vLLM v1 + 分级 KV|KV 容量敏感|
|极限 QPS / 稳定流量|TensorRT-LLM|kernel 最优|
|国产 NPU（昇腾 / 寒武纪）|Mindie / 厂商 SDK|硬件适配|
|多 LoRA 服务|vLLM v1 / LMDeploy|原生 multi-LoRA|
|FP8 / INT4 量化重度|LMDeploy / TensorRT-LLM|量化实现成熟|

下一篇《[vLLM / SGLang / TensorRT-LLM / TGI 对比](https://quant67.com/post/llm-infra/13-vllm-sglang/13-vllm-sglang.html)》会做更全面横评。

## 十、小结与实操清单

### 10.1 心智模型一句话

> **Continuous Batching** 让 GPU 永不空转；**PagedAttention** 让显存永不浪费。两者加起来，LLM 推理服务才真的”现代化”了。

### 10.2 从 OS 回看 LLM 推理

如果把 PagedAttention + Continuous Batching + Prefix Caching + 抢占调度串起来看，会发现它就是一个**针对 LLM 工作负载裁剪过的操作系统**：

|操作系统概念|LLM 推理对应|
|---|---|
|进程|Sequence / Request|
|线程调度（CFS / priority）|Continuous Batching + priority|
|虚拟内存 / 分页|PagedAttention|
|Page Cache / TLB|Prefix Cache / block table|
|Swap in/out|KV swap (GPU ↔︎ CPU ↔︎ NVMe)|
|COW fork|Parallel sampling / beam share|
|NUMA|TP/PP 多卡拓扑|
|Scheduler tunables|GMU / max_num_seqs / chunk size|

理解这层类比，对读 vLLM / SGLang 源码、设计自研引擎、排查线上诡异现象都极有帮助。许多生产问题（抖动、OOM、卡顿）在 OS 语境里都是经典问题的变体。

### 10.3 工程要点

1. 生产推理**必须**用 continuous batching 的引擎（vLLM / SGLang / TRT-LLM / TGI v3），别自己用 HF `generate()` 硬撑；
2. **开 prefix caching**——系统 prompt、few-shot、RAG 前缀、多轮对话都吃这个红利；
3. **开 chunked prefill**——降低 TTFT 和 TPOT 的抖动；
4. `gpu_memory_utilization` 设 0.85–0.92，别贪 0.95（会频繁抢占）；
5. `max_num_batched_tokens` 是吞吐—延迟的旋钮，按 SLA 试；
6. 多租户系统要在**网关层**做优先级和隔离，不要指望引擎内部；
7. 显存紧张时优先考虑 **FP8 / INT8 KV cache**、再考虑减 batch；
8. 切到 **vLLM v1** 通常免费送 30% 吞吐；
9. 对于 Agent / 树搜索 / 结构化输出，认真评估 **SGLang**；
10. 对于极限吞吐 + 稳定负载 + NVIDIA 全栈，评估 **TensorRT-LLM**。

### 10.4 常见坑

- **前缀命中率低于预期**：检查 tokenizer 是否一致、系统 prompt 是否每次都完全相同（一个空格差异就会 miss）；
- **TTFT 忽高忽低**：开 chunked prefill、调小 `max_num_batched_tokens` 里留给 prefill 的预算；
- **P99 TPOT 尖峰**：通常是大 prefill 挤压了 decode，同上；
- **OOM**：降 `gpu_memory_utilization`、降 `max_model_len`、开 KV FP8；
- **v1 兼容性**：某些插件（特定 LoRA、老版 spec decode）在 v1 上还没 GA，必要时回落 v0。

下一站：横向对比四大推理引擎，并把选型决策树画出来。

### 10.5 一句话对每一节的总结

 
|章节|核心|
|---|---|
|一 传统低效|等最长、预留 max、prefill/decode 混批差|
|二 Continuous Batching|调度粒度从 request 降到 iteration|
|三 PagedAttention|KV cache 虚拟内存化，零外部碎片|
|四 Chunked Prefill|长 prefill 切块混入 decode，抖动小|
|五 Prefix Caching|共享前缀跳过 prefill，TTFT 降一个数量级|
|六 Priority Scheduling|抢占 = swap or recompute，短用 swap 长用 recompute|
|七 vLLM v1|调度器从 Python 搬到 C++，吞吐 +30–100%|
|八 实操|开 prefix cache + chunked prefill + GMU 0.9|
|九 对手|SGLang Agent 首选，TRT-LLM 吞吐王，LMDeploy/Mindie 国产|

### 10.6 延伸阅读路线图

- 想深入 **kernel 层优化**（paged attention 如何和 FlashAttention-2/3 融合）→ 第 3 篇《[CUDA 生态](https://quant67.com/post/llm-infra/03-cuda-stack/03-cuda-stack.html)》+ 原论文；
- 想做**推理引擎选型**→ 第 13 篇；
- 想进一步**省显存、上速度**→ 第 14 篇（量化）、第 15 篇（推测解码）；
- 想搞**长上下文 128K/1M**→ 第 16 篇；
- 想搭**生产级服务**（网关、多副本、金丝雀、可观测）→ 第 21–23 篇。

### 10.7 思考题

1. 若业务 90% 请求前缀都是同一套 20KB 的系统 prompt，你会怎么分配 `gpu_memory_utilization` 和 `max_num_seqs`？为什么？
2. A100-80G、LLaMA-13B FP16 权重 26 GiB，KV 给 50 GiB，block_size=16，算一下理论最大并发请求数（假设平均 context 2K token）。
3. 什么情况下 **recompute** 优于 **swap**？反之呢？PCIe 4.0 → 5.0 会改变答案吗？
4. SGLang 的 RadixAttention 比 vLLM 的 hash prefix cache 好在哪里？在什么场景下这个差异可忽略？
5. 如果你要做一个**只服务付费 API**的推理网关，从 continuous batching 和优先级调度出发，你会在网关层、引擎层分别做什么？

### 10.8 FAQ

**Q：开 prefix caching 会影响生成结果的确定性吗？** A：不会。KV 命中等价于”这段 token 已经算过了”，和重新算的结果在数学上一致（忽略浮点误差级别的差异）。生成结果由 sampling 和 seed 决定。

**Q：chunked prefill 会让单条请求的 prefill 变慢吗？** A：会一点。一条 prefill 被切成 N 块，每块会和 decode 共享 step，单条 prefill 的 wall time 通常增加 10–30%。但整体 QPS 上升、尾延迟下降，多数业务可以接受。

**Q：PagedAttention kernel 自己写难吗？** A：能写，但不建议。vLLM / FlashInfer / xFormers 都提供了优化版本，覆盖 MHA/MQA/GQA、FP16/BF16/FP8、sliding window、ALiBi、RoPE 变体等组合。自己写很容易在边界（block 不满、跨 block、起始位置对齐）出 bug。

**Q：分离部署（P/D disaggregation）和 chunked prefill，选哪个？** A：中小规模先 chunked prefill（一条命令的事）；百卡/千卡集群、流量大且稳定、对 TTFT 和 TPOT 都有硬 SLA 才值得上分离部署。分离部署要额外处理 KV 路由、跨机传输、容错，不是免费午餐。

**Q：v1 现在稳吗？生产能用吗？** A：vLLM 0.7+ 默认 v1，主流模型（LLaMA、Qwen、Mistral、DeepSeek、GLM）都稳定。冷门模型、自定义 kernel、老版 spec decoding 建议先回归测试。2025 年起新项目直接 v1。

**Q：KV cache 能压缩吗？** A：能。FP8 KV（显存减半、精度几乎无损）、INT4 KV（显存 1/4、需校准）、H2O/StreamingLLM（只保留关键 token 的 KV）都在产线用。细节见第 14 篇量化和第 16 篇长上下文。

**Q：prefix cache 命中率怎么提升？** A：(1) 固化系统 prompt，别每次拼接动态时间戳；(2) few-shot 顺序固定；(3) 多轮对话把历史放在 prompt 前缀；(4) RAG 的 retrieved chunks 按稳定顺序拼接；(5) 考虑 SGLang RadixAttention 做更细粒度复用。

## 参考资料

1. Yu et al., _Orca: A Distributed Serving System for Transformer-Based Generative Models_, OSDI 2022.
2. Kwon et al., _Efficient Memory Management for Large Language Model Serving with PagedAttention_, SOSP 2023.（vLLM 原论文）
3. Agrawal et al., _SARATHI: Efficient LLM Inference by Piggybacking Decodes with Chunked Prefills_, 2023.
4. Zheng et al., _SGLang: Efficient Execution of Structured Language Model Programs_, 2024.（RadixAttention）
5. vLLM 官方文档与 v1 RFC：[https://docs.vllm.ai/](https://docs.vllm.ai/) 、[https://github.com/vllm-project/vllm/issues/8779](https://github.com/vllm-project/vllm/issues/8779)
6. NVIDIA TensorRT-LLM 文档：[https://nvidia.github.io/TensorRT-LLM/](https://nvidia.github.io/TensorRT-LLM/)
7. HuggingFace TGI：[https://github.com/huggingface/text-generation-inference](https://github.com/huggingface/text-generation-inference)
8. Dao et al., _FlashAttention-2_, 2023.
9. Zhong et al., _DistServe: Disaggregating Prefill and Decoding for Goodput-Optimized Large Language Model Serving_, OSDI 2024.
10. Moonshot AI, _Mooncake: A KVCache-Centric Disaggregated Architecture for LLM Serving_, 2024.
11. vLLM v1 blog: [https://blog.vllm.ai/2025/01/27/v1-alpha-release.html](https://blog.vllm.ai/2025/01/27/v1-alpha-release.html)
12. LMCache：跨节点 KV 共享 [https://github.com/LMCache/LMCache](https://github.com/LMCache/LMCache)
13. 内部数据与社区复现：vLLM Discord、SGLang GitHub issues（版本差异较大，落地前建议自测）。

---

**上一篇**：[推理引擎基础](https://quant67.com/post/llm-infra/11-inference-basics/11-inference-basics.html) **下一篇**：[vLLM / SGLang / TensorRT-LLM / TGI 对比](https://quant67.com/post/llm-infra/13-vllm-sglang/13-vllm-sglang.html)

## 同主题继续阅读

把当前热点继续串成多页阅读，而不是停在单篇消费。

2026-04-22 · architecture / ai-infra

### [大模型基础设施工程](https://quant67.com/post/llm-infra/index.html)

面向中国工程团队的大模型基础设施系列。从 GPU/CUDA/互联、训练框架与 3D 并行、vLLM/SGLang 推理引擎、量化与推测解码、RAG/Agent 到服务化、网关、可观测性与安全合规，覆盖 LLMOps 全链路。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】13：vLLM / SGLang / TensorRT-LLM / TGI 对比](https://quant67.com/post/llm-infra/13-vllm-sglang/13-vllm-sglang.html)

主流推理引擎的架构、性能、生态深度对比，给出工程选型与落地决策依据。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】11：推理引擎基础](https://quant67.com/post/llm-infra/11-inference-basics/11-inference-basics.html)

从 Prefill/Decode 两阶段、KV Cache、Continuous Batching 到 PD 分离，系统讲清楚大模型推理的工程基础。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】09：RLHF 与对齐流水线](https://quant67.com/post/llm-infra/09-rlhf-pipeline/09-rlhf-pipeline.html)

从 SFT、奖励模型到 PPO、DPO、GRPO 的完整对齐流水线工程实践，覆盖 OpenAI o1、DeepSeek-R1 等推理模型的 RL 路线与主流框架选型。