> 本文是【大模型基础设施工程】系列第 2 篇。上一篇给出全景，本篇把镜头推近到一块 GPU 的内部：它凭什么能让万亿参数的矩阵乘在几毫秒内完成？为什么同一张 H100，跑训练能打满 60% MFU，跑 decode 却只能用到 5% 算力？理解这些，后面的并行策略、推理调度、量化才有根基。

### 1.1 一次 GPT 前向里到底在做什么

一个 70B 参数的 Transformer，单 token 前向算一次，大约要做：

- 约 140 GFLOPs 的矩阵乘法（主要是 QKV 投影、MLP 的两个 GEMM、输出投影）
- 从权重矩阵读出约 140 GB 数据（FP16 一份权重就是 140 GB）
- 少量非线性（SiLU / GELU）、归一化（RMSNorm）、Softmax

这三件事本质上是三类负载：**稠密矩阵乘、海量顺序读取、element-wise 算子**。它们共同的特征是——**没有分支、没有指针追逐、没有小而随机的访存**，每一次操作都能在成千上万个数据元素上同时展开。

### 1.2 CPU 为什么不擅长这件事

CPU 的设计目标是”让单条串行控制流尽可能快”。为此它把晶体管预算砸在：

- 乱序执行（out-of-order execution）
- 分支预测（branch prediction）
- 巨大的 L1/L2/L3 cache
- 复杂的内存子系统、一致性协议（MESI）

代价是：**一个物理核心的面积非常大，算力密度（FLOPs per mm²）很低**。以 2024 年 Intel Sapphire Rapids 的顶级 Xeon 为例：

- 60 核心、单核 3.8 GHz
- AVX-512 FMA 峰值 FP32 约 2.5 TFLOPS
- 整芯片 FP32 峰值约 2.5 TFLOPS × 60 / 1 ≈ 7 TFLOPS 量级
- DDR5 带宽 8 通道 ≈ 300 GB/s

对比 NVIDIA H100 SXM5：

- 约 16896 CUDA 核心、132 个 SM
- FP16/BF16 Tensor Core 峰值 ≈ 989 TFLOPS（不含稀疏）
- HBM3 带宽 3.35 TB/s

**算力差 100 倍以上，带宽差 10 倍以上**。这不是制造工艺差异，是**架构目标**的差异。

### 1.3 一句话总结

CPU 是”少量强核 + 复杂控制 + 以访存为主”，GPU 是”海量弱核 + 极简控制 + 以计算吞吐为主”。GPU 用**晶体管面积换算力密度**，代价是放弃了对不规则负载的友好。

## 二、CPU 与 GPU 架构对比

### 2.1 晶体管都花在哪儿

一块芯片的面积预算可以粗略分为：控制逻辑、缓存、计算单元、互联、IO。CPU 与 GPU 的分配比例差异极大：

|类别|CPU 占比（典型）|GPU 占比（典型）|
|---|---|---|
|控制 / 调度 / 分支预测|30–40%|5–10%|
|Cache（L1/L2/L3）|30–40%|10–20%（包括 Shared Memory）|
|计算单元（ALU/FPU/Tensor Core）|10–20%|50–60%|
|互联 / IO / 内存控制器|10–20%|15–25%|

GPU 把缓存 + 控制预算几乎全都省下来，砸进了计算单元。这就是为什么同样工艺节点，GPU 的峰值 FLOPS 能比 CPU 高一到两个数量级。

### 2.2 延迟隐藏 vs 延迟避免

CPU 通过**避免延迟**来提速：大 cache 让数据离 ALU 近，乱序执行让阻塞的指令让位给别的指令。

GPU 通过**隐藏延迟**来提速：一个 SM（Streaming Multiprocessor）同时挂几十到上百个 warp，一个 warp 卡在访存上，调度器立刻切到另一个 warp。只要**活跃并行度足够大**，访存延迟就被”吞”掉了。

这个差异带来的工程影响：

- CPU 上，减少 cache miss 是王道
- GPU 上，**让每个 SM 挂够活跃 warp**（提高 occupancy）是王道
- GPU 最怕的是”可并行度不够”——比如 batch size = 1 的 decode，每层只有很少的活干，SM 饥饿

### 2.3 一张图对比

```
CPU（示意）                     GPU（示意）
+-------------------+           +-----------------------------+
| 控制 | 分支预测   |           | 132 × SM                   |
|---------+--------|            |  每个 SM:                   |
| L1 |  ALU × 少   |            |   - 128 CUDA core          |
|---------+--------|            |   - 4 × Tensor Core        |
|        L2        |            |   - 256 KB 寄存器          |
|---------+--------|            |   - 228 KB Shared Memory   |
|        L3        |            |   - 4 warp scheduler       |
+-------------------+           |                             |
                                | 全局：L2 50 MB              |
                                |       HBM3 80 GB / 3.35 TB/s|
                                +-----------------------------+
```

### 2.4 GPU 架构分层图

![GPU 架构分层图](https://quant67.com/post/llm-infra/02-gpu-primer/images/02-gpu-primer-fig1.svg)

### 2.5 GPU 的”弱核”到底有多弱

GPU 的单个 CUDA 核心没有分支预测、没有乱序执行、没有独立指令指针——它甚至不是传统意义上的”核心”，只是一条 ALU lane。**真正的执行单位是 warp**（32 条 lane 同步执行一条指令），真正的调度单位是 SM。理解这点，后面 SIMT、divergence 才讲得通。

## 三、GPU 执行模型：Grid / Block / Warp / Thread

### 3.1 逻辑层次

CUDA 把并行抽象成三级嵌套：

```
Grid     (kernel 启动一次就是一个 Grid)
 └── Block    (一个 Block 绑定到一个 SM)
      └── Warp     (32 个线程，SIMT 单位)
           └── Thread  (最小逻辑单位，对应一条 ALU lane)
```

- **Grid**：一次 kernel launch，可以有几百万个线程
- **Block**（线程块）：编程者手动划分，通常 128 / 256 / 512 / 1024 线程。同一个 Block 内的线程可以用 Shared Memory 通信、可以 `__syncthreads()`
- **Warp**：硬件单位，32 线程，永远一起前进
- **Thread**：最小单位，有自己的寄存器、自己的线程 ID，但没有独立指令指针

一个 Block 会被分成若干个 Warp（例如 256 线程 = 8 个 Warp），全部挂到同一个 SM 上。一个 SM 可以同时挂多个 Block，只要寄存器和 Shared Memory 够用。

### 3.2 SIMT 到底是什么

SIMT（Single Instruction, Multiple Threads）：**同一条指令同时驱动 32 条 lane**。和 CPU 的 SIMD（SSE / AVX）区别是：SIMT 每条 lane 有自己的寄存器和”逻辑上的”程序计数器，允许不同 lane 走不同路径——代价是**走不同路径的 lane 会被串行化**，这就是 warp divergence。

### 3.3 分支发散（divergence）

看一个最典型的反例：

```
__global__ void bad_kernel(float* x, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i % 2 == 0) {
        x[i] = expensive_a(x[i]);
    } else {
        x[i] = expensive_b(x[i]);
    }
}
```

一个 warp 里 16 个线程走 `expensive_a`、16 个走 `expensive_b`。硬件会：

1. 先让偶数 lane 激活、奇数 lane 掩蔽，执行 `expensive_a`
2. 再让奇数 lane 激活、偶数 lane 掩蔽，执行 `expensive_b`

**两条路径被串行执行，warp 吞吐砍半**。如果是 8 路分支，吞吐砍到 1/8。

工程经验：

- Warp 内尽量分支一致（例如把分支按 32 的倍数对齐）
- 能用 `select` / `fmaxf` 消除的分支就消除
- Attention 里 mask 实现要特别小心，用乘法而不是 `if`

### 3.4 Block 大小怎么选

一般经验（H100 / A100）：

- Block ≥ 128 线程，才能让 4 个 warp scheduler 都有活干
- Block ≤ 1024 线程，这是硬件上限
- 不要卡在 33 / 65 / 97 这种”多一个 warp 只填一个线程”的尺寸
- Shared Memory 用量限制了一个 SM 能挂几个 Block

## 四、内存层级：从寄存器到主机内存

GPU 的内存层级比 CPU 更陡峭，也更需要程序员显式管理。

### 4.1 各级存储的数量级

以 H100 SXM5 为例：

    
|层级|容量|延迟|带宽|管理方式|
|---|---|---|---|---|
|寄存器|256 KB / SM（每线程最多 255 × 32bit）|1 cycle|——|编译器分配|
|Shared Memory / L1|228 KB / SM|~20 cycle|~19 TB/s 聚合|用户显式声明|
|L2 Cache|50 MB|~200 cycle|~5 TB/s|硬件管理|
|HBM3（显存）|80 GB|~400–600 cycle|3.35 TB/s|硬件管理|
|NVLink 到邻居 GPU|对端显存|~1 μs 量级|900 GB/s 双向|程序显式|
|PCIe Gen5 到主机|主机 DRAM / NVMe|~10 μs|64 GB/s 双向|程序显式|
|以太网 / RoCE / IB|跨节点|几 μs 到几十 μs|400 Gb/s ~ 800 Gb/s|程序显式|

**相邻两层之间，带宽至少差一个数量级，延迟差一到两个数量级**。

### 4.2 两条黄金法则

1. **尽量让数据在高层停留久一些**。权重只能放在 HBM，但计算时应尽量让一块 tile 驻留在 Shared Memory / 寄存器，反复使用。
2. **同一个 warp 的 32 个线程要访问连续地址**（coalesced access）。否则一次访存变成 32 次独立的 32 字节事务，带宽下降数倍。

### 4.3 一张内存层级图

![GPU 内存层级图](https://quant67.com/post/llm-infra/02-gpu-primer/images/02-gpu-primer-fig2.svg)

## 五、SM（Streaming Multiprocessor）内部

SM 是 GPU 的”小 CPU”——调度、执行、Shared Memory 都在这一层。

### 5.1 H100 一个 SM 内部大致构成

- 4 个处理分区（processing block），每个有：
    - 1 个 warp scheduler + dispatch unit
    - 16K × 32bit 寄存器堆
    - 16 FP32 CUDA core + 16 INT32 CUDA core + 8 FP64 core + 1 Tensor Core
- 整个 SM 共享：
    - 228 KB 的 Shared Memory / L1（可配置切分）
    - 若干 Load/Store 单元、SFU（Special Function Unit，算 sin / exp / rsqrt）
    - Tensor Memory Accelerator（TMA，Hopper 新加的异步拷贝引擎）

### 5.2 Occupancy（占用率）是什么

Occupancy = 一个 SM 上活跃 warp 数 / 硬件上限。H100 每个 SM 最多挂 64 个 warp，如果你的 kernel 一个 Block 用了太多寄存器或 Shared Memory，一个 SM 就挂不了几个 Block，occupancy 低，延迟隐藏失败。

但是——**高 occupancy 不等于高性能**。FlashAttention、cutlass 里大量用”低 occupancy + 大 tile + 寄存器复用”的路线，反而比高 occupancy 快。占用率只是手段，**SM 每 cycle 发射的指令数**才是目的。

### 5.3 一个 SM 一 cycle 能做多少事

以 H100 SM 的一个处理分区为例（一 cycle 周期）：

- 1 条 warp scheduler 可以发射 1 条指令（FP32 FMA / INT32 / load-store / tensor op 都算一条）
- 其中 Tensor Core 指令一条能做 `128×128×16 的 FP16 MMA`（等效 4096 MAC = 8192 FLOPs）
- 而一条 FP32 FMA 只完成 16 个 FMA = 32 FLOPs

算力差 256 倍。这就是为什么**只要能换成 Tensor Core，就一定要换**——手写 loop 的算力常常只有峰值 1%。

### 5.4 Tensor Memory Accelerator（TMA）

Hopper 新增。传统 CUDA：每个线程用 `ld.global` 指令把数据从 HBM 搬到 Shared Memory，一个 tile 32×32 需要 32 个线程合作搬 32 次，并且**占用寄存器和 warp**。TMA 是一个独立的硬件搬运工：

```
// 伪代码
cp.async.bulk.tensor.2d.shared::cluster.global 
    [dst_smem], [src_gmem], {tile_dim}, barrier;
```

一条指令让硬件自动搬一个 tile，**线程可以立刻去算别的东西**，搬完后 barrier 通知。FlashAttention-3 的 warp specialization 就是利用 TMA 实现”一组 warp 专门发 TMA、一组专门做 MMA”。

## 六、Tensor Core 演进

Tensor Core 是专门做”小矩阵乘累加”的硬件单元。**普通 CUDA core 一次做一次 FMA，Tensor Core 一次做一个 4×4×4 的矩阵乘累加**（早期），到今天已经变成 16×8×16 / 16×8×32 等更大形状。它是过去八年 GPU 峰值算力暴涨的直接原因。

### 6.1 Volta V100（2017，FP16 起步）

- 第一代 Tensor Core
- 精度：FP16 输入、FP32 累加
- 形状：4×4×4
- 峰值：125 TFLOPS FP16（相比 15 TFLOPS FP32 翻 8 倍）
- **训练第一次能在合理时间内做 BERT-large**

### 6.2 Turing T4（2018，INT8 推理）

- 加了 INT8 / INT4，推理场景成本大降
- 峰值 260 TOPS INT8

### 6.3 Ampere A100（2020，TF32 / BF16 / 结构化稀疏）

- 引入 **TF32**（8bit 指数 + 10bit 尾数，范围同 FP32，精度比 FP16 略低），把 FP32 训练”免费”提速
- **BF16** 成为主流训练精度（指数范围和 FP32 一样，梯度不容易 overflow）
- **2:4 结构化稀疏**：硬件识别”每 4 个权重里有 2 个是 0”的模式，吞吐翻倍
- 峰值：312 TFLOPS BF16 / FP16，624 TFLOPS（稀疏）

### 6.4 Hopper H100（2022，FP8 + Transformer Engine + TMA）

- **FP8**：两种格式，E4M3（精度优先）和 E5M2（范围优先）。前向用 E4M3，反向用 E5M2
- **Transformer Engine**：硬件 + 软件协同，自动做 FP8 动态缩放、per-tensor scaling，工程师只要改配置
- **TMA**（Tensor Memory Accelerator）：异步把一块 tile 从 HBM 搬到 Shared Memory，不占用寄存器和线程，GEMM kernel 可以”一边搬一边算”
- **DPX 指令**：加速动态规划
- 峰值：989 TFLOPS BF16、1979 TFLOPS FP8（不含稀疏）
- **H200 是 H100 的显存升级版**：HBM3e、141 GB、4.8 TB/s，算力不变

### 6.5 Blackwell B200 / GB200 / B300（2024–2025）

- **FP4**：进一步降精度，主要给推理和部分训练用
- 双 die 设计：两个 die 通过 10 TB/s 的 NV-HBI 互联，对软件呈现为一张 GPU
- 第二代 Transformer Engine：微尺度 FP8、块级缩放
- **GB200 NVL72**：72 张 B200 + 36 个 Grace CPU，用第五代 NVLink（1.8 TB/s 双向）组成一个”超节点”，对软件呈现为一个超大 NUMA
- 峰值：FP4 约 20 PFLOPS / GPU、FP8 约 10 PFLOPS / GPU
- B300 是 B200 的 refresh 版本，显存更大

### 6.6 Rubin R100（规划 2026）

NVIDIA 公开路线图里 Rubin 会采用：

- HBM4，带宽进一步到 10 TB/s 量级
- 新一代 NVLink（第六代）
- 和 Vera CPU 配对组成 Vera Rubin 超节点
- 第三代 Transformer Engine，进一步探索 FP4 / FP6 训练

### 6.7 一张精度速查表

|精度|bits|指数|尾数|典型用途|
|---|---|---|---|---|
|FP32|32|8|23|早期训练、科学计算|
|TF32|19 实际|8|10|A100/H100 训练默认 FP32 替代|
|FP16|16|5|10|V100 起主流训练|
|BF16|16|8|7|A100 起主流训练，梯度稳|
|FP8 E4M3|8|4|3|H100 前向权重/激活|
|FP8 E5M2|8|5|2|H100 反向梯度|
|FP4|4|2|1（或 E2M1）|B200 推理、部分训练|
|INT8|8|——|——|推理量化|
|INT4|4|——|——|推理极致量化（AWQ/GPTQ）|

## 七、算力与带宽全家桶

### 7.1 NVIDIA 主力卡一览

       
|型号|发布|制程|FP16/BF16 TFLOPS|FP8 TFLOPS|显存|HBM 带宽|NVLink 双向|
|---|---|---|---|---|---|---|---|
|V100 SXM2|2017|12 nm|125|—|32 GB HBM2|900 GB/s|300 GB/s|
|A100 SXM4|2020|7 nm|312|—|80 GB HBM2e|2039 GB/s|600 GB/s|
|H100 SXM5|2022|4 nm|989|1979|80 GB HBM3|3350 GB/s|900 GB/s|
|H200 SXM|2024|4 nm|989|1979|141 GB HBM3e|4800 GB/s|900 GB/s|
|B200|2024|4NP|2250|4500（FP4 ~9000）|192 GB HBM3e|8000 GB/s|1800 GB/s|
|GB200|2024|4NP|2 × B200 + Grace|——|2 × 192 GB|2 × 8 TB/s|1800 GB/s|

### 7.2 其它玩家

      
|型号|厂商|FP16/BF16|FP8|显存|带宽|备注|
|---|---|---|---|---|---|---|
|MI300X|AMD|1307 TFLOPS|2614 TFLOPS|192 GB HBM3|5.3 TB/s|CDNA3 + ROCm|
|MI325X|AMD|1307|2614|256 GB HBM3e|6 TB/s|2024|
|MI355X|AMD|—|5000（FP4 10000）|288 GB HBM3e|8 TB/s|2025，对标 B200|
|Gaudi 3|Intel|1835 TFLOPS（BF16）|—|128 GB HBM2e|3.7 TB/s|OAM，RoCE 200 GbE ×24|
|TPU v5p|Google|459 TFLOPS BF16|—|95 GB HBM|2.76 TB/s|ICI 互联|
|TPU v6e（Trillium）|Google|~918 TFLOPS BF16|INT8 1836|32 GB|1.6 TB/s|2024|
|Ascend 910B|华为|320 TFLOPS FP16|—|64 GB HBM|1.6 TB/s|达芬奇架构|
|Ascend 910C|华为|800 TFLOPS 级（双 die）|—|128 GB HBM|3.2 TB/s|2024 末量产|
|BR100|壁仞|1024 TOPS INT8 / 256 TFLOPS BF16|—|64 GB HBM2e|2.3 TB/s|受制裁后 SKU 调整|
|MXN100 / MXN260|沐曦|200–400 TFLOPS 级|—|64 GB|~1.5 TB/s|曦云系列|
|DCU Z100 / K100|海光|——|——|64 GB HBM2|~1 TB/s|ROCm 兼容路线|
|摩尔线程 MTT S4000|摩尔线程|100 TFLOPS 级 FP16|—|48 GB|~768 GB/s|MUSA 生态|

表中数据以厂商公开材料为准，实际可用因受制裁、散热、固件而异。**国产卡的通用趋势：峰值算力追到 A100–H100 之间，但软件栈（编译器、通信库、框架兼容）仍是主要差距**。后面第 4 篇会展开讲互联，第 3 篇展开讲软件栈。

## 八、Roofline 模型：瓶颈到底在哪

Roofline 是分析 GPU kernel 性能的最基本工具。核心思想一句话：**性能上限 = min(峰值算力，算术强度 × 带宽)**。

### 8.1 算术强度（Arithmetic Intensity）

AI = 浮点运算次数 / 访存字节数，单位 FLOPs/Byte。

- GEMM `C = A × B`（M=N=K=4096，FP16）：算 2·M·N·K = 137 GFLOPs，访存 2·M·K·2 + N·K·2 ≈ 100 MB，AI ≈ 1370 FLOPs/B——**完全计算受限**
- 向量加 `c = a + b`：1 FLOP / 12 Byte ≈ 0.083 FLOPs/B——**完全带宽受限**
- Attention 的 decode 阶段：KV cache 读取远多于计算，AI 通常 < 10 FLOPs/B——**带宽受限**

### 8.2 H100 的屋顶线

H100 FP16：989 TFLOPS，HBM 3.35 TB/s。拐点 AI = 989e12 / 3.35e12 ≈ **295 FLOPs/B**。

- AI < 295：性能 ≈ AI × 3.35 TB/s（带宽墙）
- AI > 295：性能 ≈ 989 TFLOPS（算力墙）

所以：**只有 AI 接近或超过 295，才能吃满 H100 的 FP16 算力**。FP8 拐点更高（约 590），更难打满。

### 8.3 Prefill vs Decode

LLM 推理天然分两段：

- **Prefill**（处理 prompt）：把 L 个 token 一次性 forward。每个权重被 L 个 token 共用，AI ≈ L 量级（典型 2000–8000），**计算受限**，MFU 可以做到 50–70%
- **Decode**（逐 token 生成）：batch=1 时一个 token 一次，权重读一遍只用一次，AI ≈ 1 量级，**彻底带宽受限**，MFU 通常 2–8%

这就是为什么**同一张 H100，训练 MFU 能到 60%，而单条 decode 只有 5%**。解法是 continuous batching、speculative decoding、MTP，这些后面第 12、15 篇细讲。

![Prefill vs Decode](https://quant67.com/post/llm-infra/02-gpu-primer/images/02-gpu-primer-fig3.svg)

## 九、多卡之间的带宽：NVLink / NVSwitch 快览

后面第 4 篇会完整讲互联，这里先给出工程直觉——做完 Roofline 单卡分析后，多卡的瓶颈才是下一个战场。

### 9.1 为什么单卡装不下

70B 模型：

- 权重 FP16：140 GB，**一张 80 GB H100 装不下**
- 训练时还要额外 optimizer state（AdamW FP32 约 4×）、gradient、activation——70B 全量训练最少 8 卡、通常 32–64 卡起步
- 推理单卡可以放 FP8 / FP4 的 70B，但 KV cache 超长 context 时也吃紧

于是必然多卡，必然要讲通信。

### 9.2 NVLink vs PCIe 的差距

|路径|带宽（双向）|延迟|
|---|---|---|
|PCIe Gen4 x16|64 GB/s|~1 μs|
|PCIe Gen5 x16|128 GB/s|~1 μs|
|NVLink 3（A100）|600 GB/s|~300 ns|
|NVLink 4（H100）|900 GB/s|~250 ns|
|NVLink 5（B200）|1800 GB/s|~200 ns|
|InfiniBand NDR 400G|50 GB/s|~2 μs|
|RoCEv2 400G|50 GB/s|~3–5 μs|

**NVLink 比 PCIe 高一个数量级**。所以 all-reduce、all-gather 这些集合通信必须走 NVLink，走 PCIe 训练直接死。跨节点则依赖 InfiniBand / RoCE，又掉一个数量级——这就是为什么”节点内并行”和”节点间并行”策略截然不同。

### 9.3 NVSwitch 与 NVL72

DGX H100 里 8 张 GPU 通过 NVSwitch 全互联，任意两张之间都是 900 GB/s。Blackwell 代的 **NVL72 机柜** 把 72 张 GPU 通过第五代 NVLink + NVSwitch 全互联，整个机柜对软件呈现为一个大显存池（13.5 TB HBM）。

**工程意义**：MoE 的 all-to-all、张量并行的 all-reduce，以前受限于单节点 8 卡；NVL72 之后可以在 72 卡内做——这是训练超大 MoE（DeepSeek 级、GPT-4 级）的硬件前提。第 6 篇（3D 并行）会据此重新讨论 TP 维度上界。

### 9.4 国产互联生态

- **华为 HCCS**：910B 一个 8 卡全互联节点，总带宽对标 NVLink 3，跨节点用 200 GbE RoCE
- **壁仞 BLink**、**沐曦 MetaLink**：对标 NVLink，产品化程度仍在追赶
- **阿里磐久 + AliNIC**：自研 RDMA 网卡，支撑千卡训练

## 十、Attention 的访存特性与 FlashAttention

### 10.1 标准 Attention 是怎么跑的

标准实现分 4 步，每一步都是一次 kernel：

1. `Q = X·Wq`、`K = X·Wk`、`V = X·Wv`（3 次 GEMM）
2. `S = Q·Kᵀ / √d`（GEMM）
3. `P = softmax(S)`（element-wise + 归约）
4. `O = P·V`（GEMM）

问题在第 2、3 步之间：`S` 的形状是 `[B, H, L, L]`，序列长 8K 时光是 S 就 64 MB × batch × head 个数——**必须落回 HBM**，再读进来做 softmax，再写回 HBM 做 `P·V`。

### 10.2 一张算力/带宽比分析表

|步骤|算力（FLOPs）|访存（Bytes）|AI|瓶颈|
|---|---|---|---|---|
|Q/K/V 投影|6 B·L·d²|权重 3·d²·2|高|计算受限（prefill）|
|QKᵀ|2 B·H·L²·d|S 写 B·H·L²·2 + 读 Q/K|中|视 L 而定|
|Softmax|O(B·H·L²)|2 × B·H·L²·2|**极低**|带宽受限|
|P·V|2 B·H·L²·d|读 P、V，写 O|中|中等|

**Softmax 和中间的 S 写回/读取是最大的带宽瓶颈**。序列越长，L² 项越主导，性能越差。

### 10.3 FlashAttention 的核心思想

**不实体化 S 矩阵**，在 SRAM（Shared Memory）里把 tile 算完。

三要素：

1. **Tiling**：把 Q 分成块 `Qi`、K/V 分成块 `Kj/Vj`，每次只算一小块 `Qi·Kjᵀ`，留在 SRAM
2. **Online Softmax**：softmax 本来需要先扫一遍求 max / sum，FlashAttention 用”在线”递推，边扫边更新 max 和 sum，允许流式处理
3. **反向重算**：反向时不存 S 和 P，用保存的 max / sum 重新算一遍，以”多算一次”换”不落盘”

### 10.4 v1 / v2 / v3 的工程差异

- **FlashAttention v1**（2022，Tri Dao）：最早实现。沿 seq 方向 tile，对 A100 的 Shared Memory 大小做了手工优化。推理 / 训练加速 2–4 倍，显存从 O(L²) 降到 O(L)
- **FlashAttention v2**（2023）：
    - 调度改成”**Q 外循环，K/V 内循环**”，每个 tile 的输出可以直接写一次
    - 减少非矩阵乘指令（softmax 等），让更多时间花在 Tensor Core 上
    - 对 causal mask 做了特化，只算下三角
    - H100 上 FP16 训练 MFU 从 ~35% 提到 ~55%
- **FlashAttention v3**（2024）：专门吃 Hopper 新特性
    - 用 **TMA** 异步加载 tile，掩盖 HBM 延迟
    - 用 **warp specialization**：一部分 warp 做生产者（加载数据），一部分做消费者（算 GEMM），流水线重叠
    - **FP8 支持**：利用 Hopper FP8 Tensor Core，进一步 1.5–2 倍加速
    - 在 H100 上达到 ~75% MFU

FlashAttention 之后，**vLLM / SGLang / TensorRT-LLM 推理引擎里的 attention 基本都是 FlashAttention 变种**；decode 阶段发展出了 FlashDecoding、FlashDecoding++、FlashInfer 等，专门优化 decode 这种 Q 很短、K 很长的形状。

## 十一、Demo：用 Triton 写一个调用 Tensor Core 的 GEMM

手写 CUDA GEMM 要处理 tile、Shared Memory、bank conflict、WMMA API——对入门太重。Triton 让你用 Python 写 kernel，自动生成调用 Tensor Core 的 PTX。

### 11.1 最小可运行 GEMM

```
import torch
import triton
import triton.language as tl

@triton.jit
def matmul_kernel(
    a_ptr, b_ptr, c_ptr,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    a_ptrs = a_ptr + offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak
    b_ptrs = b_ptr + offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for k in range(0, K, BLOCK_K):
        a = tl.load(a_ptrs, mask=offs_k[None, :] < K - k, other=0.0)
        b = tl.load(b_ptrs, mask=offs_k[:, None] < K - k, other=0.0)
        # tl.dot 会被编译成 Tensor Core 的 mma.sync 指令
        acc += tl.dot(a, b)
        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk

    c_ptrs = c_ptr + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
    tl.store(c_ptrs, acc.to(tl.float16))


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    M, K = a.shape
    _, N = b.shape
    c = torch.empty((M, N), device=a.device, dtype=torch.float16)
    grid = (triton.cdiv(M, 128), triton.cdiv(N, 128))
    matmul_kernel[grid](
        a, b, c,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        c.stride(0), c.stride(1),
        BLOCK_M=128, BLOCK_N=128, BLOCK_K=32,
    )
    return c


if __name__ == "__main__":
    M = N = K = 4096
    a = torch.randn(M, K, device="cuda", dtype=torch.float16)
    b = torch.randn(K, N, device="cuda", dtype=torch.float16)
    c = matmul(a, b)
    ref = a.float() @ b.float()
    print("max abs err:", (c.float() - ref).abs().max().item())
```

关键点：

- `tl.dot(a, b)` 在编译后会生成 `mma.sync.aligned.m16n8k16.row.col.f32.f16.f16.f32` 之类的 PTX 指令，**直接调 Tensor Core**
- `BLOCK_M/N/K` 就是 tile 大小；Triton 自动处理 Shared Memory 分配
- 加上 `@triton.autotune` 可以让 Triton 自动搜 tile 配置

### 11.2 用 `ncu` 看 Tensor Core 是否被真的用起来

```
ncu --set full \
    --metrics sm__inst_executed_pipe_tensor_op_hmma.sum,\
sm__cycles_elapsed.sum,\
dram__bytes.sum.per_second \
    python bench_matmul.py
```

- `sm__inst_executed_pipe_tensor_op_hmma.sum` > 0 → 的确走了 Tensor Core
- `dram__bytes.sum.per_second` 可以和 3.35 TB/s 峰值对比
- `sm__cycles_elapsed` + FLOPs 算出 MFU

## 十二、工程师视角：怎么读 nvidia-smi / Nsight

### 12.1 nvidia-smi 最常看的几项

```
nvidia-smi \
  --query-gpu=index,name,utilization.gpu,utilization.memory,\
memory.used,memory.total,power.draw,pstate,clocks.sm,clocks.mem \
  --format=csv -l 1
```

- `utilization.gpu`：SM 被任一 kernel 占用的时间比例——**这是一个”活没活着”的指标，不是”算力用满”的指标**
- `utilization.memory`：HBM 控制器忙的时间比例
- `power.draw`：实际功耗。SXM5 H100 TDP 700 W。**低功耗 + 高 util% → 几乎肯定是带宽受限或 kernel launch 受限**
- `pstate`：P0 = 全速，P8 = 低频，调度问题经常卡在 P2
- `clocks.sm / clocks.mem`：降频了通常是散热或功耗墙

### 12.2 Nsight Systems（nsys）看时间线

```
nsys profile -o train_run \
  --trace=cuda,nvtx,osrt,cudnn,cublas \
  --sample=cpu \
  python train.py
```

看三件事：

1. **GPU 是否持续忙**：时间线上有没有大片空白（kernel gap）。有空白说明 dataloader / 通信是瓶颈
2. **通信与计算是否重叠**：NCCL kernel 是不是在 compute 的同时进行
3. **kernel launch 间隙**：每个 kernel 前有几十微秒 gap 的话，说明 Python 开销/启动开销大，考虑 CUDA Graph

### 12.3 Nsight Compute（ncu）看 kernel 内部

ncu 给单个 kernel 做细粒度分析：

- **Memory Workload Analysis**：L1 / L2 / HBM 各自带宽利用率
- **Compute Workload Analysis**：SM 流水线利用率
- **Scheduler Statistics**：每 cycle 发射指令数、stall 原因
- **Source Counters**：把指令数映射回源码行

常见定位路径：

- util% 高但算力低 → 看 SM busy 原因，通常是 long scoreboard（访存 stall）
- SM busy 中等、HBM 带宽打满 → 带宽受限，能做的只有减少数据量（量化、缓存、fusion）
- SM busy 低、HBM 带宽也低 → kernel launch 受限或 CPU 侧瓶颈

## 十三、常见误区

### 13.1 “GPU 利用率 100% = 算力用满”——错

`nvidia-smi` 的 util% 含义是”过去 1 秒里，有 kernel 在跑的时间占比”。一个打满 SM 的 GEMM 和一个只占 1 个 SM 的 memset，在 util% 上一样是 100%。

**真正的算力利用率叫 MFU（Model FLOPs Utilization）**：实际 FLOPs / 峰值 FLOPs。训练 H100 打到 50% MFU 是很好的成绩，decode 阶段 5% 也是常态。

### 13.2 “显存大 = 能跑大模型”——只对了一半

还得看带宽。同样 80 GB：

- A100 80GB 带宽 2 TB/s
- H100 80GB 带宽 3.35 TB/s

跑 70B 的 decode，H100 decode 单 token latency 大约比 A100 快 1.7 倍——差距主要来自**带宽**而不是算力。

### 13.3 “FP16 永远比 BF16 准”——错

FP16 尾数多 3 bit，但指数少 3 bit，梯度很容易 overflow。A100 之后几乎所有训练都默认 BF16，牺牲一点精度换稳定。

### 13.4 “稀疏算力翻倍 = 免费午餐”——错

Ampere 的 2:4 结构化稀疏要求**每 4 个权重中恰好 2 个是 0**，而且位置是硬件规定的，需要专门剪枝训练才能达到。直接把 dense 权重塞进去，算力是一样的，硬件并不自动识别稀疏。

### 13.5 “增大 batch 一定快”——不一定

- prefill 已经算力受限，再加 batch 只会让 L2 miss 增加、latency 变差
- decode 在 batch 增大到 HBM 带宽瓶颈前都划算，之后就进入计算受限区间

### 13.6 “Tensor Core 只做 FP16”——过时了

现在 Tensor Core 支持 FP64 / TF32 / FP16 / BF16 / FP8 / FP4 / INT8 / INT4。规划精度选型时，先问”这张卡上这个精度有没有 Tensor Core 加速”——比如 V100 就没有 FP8/BF16，别在上面跑 BF16 训练。

### 13.7 “国产 GPU 峰值算力追上 H100 就可以替换”——远远不够

峰值之外还要看：

- 通信库（对标 NCCL）是否成熟
- 编译器（对标 CUDA + cuDNN + cuBLAS）的算子覆盖率
- 框架兼容（PyTorch / vLLM 适配）
- 互联拓扑（NVLink 等价物）
- 生态（模型权重、kernel 库、开发者）

参数表漂亮，工程落地通常要先踩半年到一年的坑。

## 十四、进阶话题：几个工程师天天踩的坑

### 14.1 寄存器溢出（register spill）

每个线程的寄存器上限是 255 × 32bit。kernel 里变量一多，编译器会把一部分”寄存器”放到**本地内存**（Local Memory，物理上其实是 HBM 的一段，只是每线程私有）。一旦溢出：

- 每次访问变成一次 HBM 访问，延迟暴涨
- occupancy 下降（因为 per-thread 资源没减）

`nvcc -Xptxas -v` 编译时会打印每个 kernel 用了多少寄存器、是否 spill。写 kernel 时看到 `stack frame: 128 bytes` 就要警惕。

### 14.2 Shared Memory 的 bank conflict

Shared Memory 被分成 32 个 bank，每个 bank 宽 4 字节。同一个 warp 的 32 个线程，如果同时访问**同一个 bank 的不同地址**，就会串行化。最典型的例子：

```
__shared__ float tile[32][32];
// 所有线程读同一列 tile[threadIdx.x][0] —— 全部落在 bank 0，冲突 ×32
// 解决：tile[32][33]，加一列 padding，把列错开
```

写 GEMM / conv 的手搓 kernel 必踩这个坑。Triton / CUTLASS 会自动处理。

### 14.3 L2 cache 的作用被严重低估

H100 的 L2 有 50 MB，装下一整个 70B 模型的一层权重（FP8）绰绰有余。对小 batch decode，让权重**在 L2 里 hit 率高**比什么优化都有用。Hopper 还加了 L2 **驻留控制**（`cudaAccessPropertyPersisting`），可以显式让某段地址长期留在 L2。

### 14.4 Kernel launch 开销

每次 launch 一个 kernel，PCIe / Host 侧都要花大约 5–10 μs 准备。decode 阶段一个 token 可能 launch 上百个 kernel，累积起来就是几毫秒——**和 kernel 本身的算时间一样长**。对策：

- **CUDA Graph**：把一串 kernel 录制成一张图，一次提交
- **算子融合**：把 RMSNorm + QKV 投影 + RoPE 融进一个 kernel
- **持续内核**（persistent kernel）：一个 kernel 常驻在 SM 里循环处理多个 batch

vLLM、TensorRT-LLM 的 decode 路径里基本都上了 CUDA Graph。

### 14.5 ECC 与内存可靠性

数据中心级 GPU（A100/H100/B200）的 HBM 默认开 ECC。打开 ECC 会：

- 损失约 6.25% 可用容量（64→60 GB 有效）
- 损失一点点带宽（硬件做校验）

消费级卡（如 RTX 4090）没有 ECC，做大规模训练会遇到”偶发 NaN、无法复现”的诡异故障。生产训练永远用数据中心卡。

### 14.6 ECC 错误与 SRAM bit flip

H100 引入了**Row Remapping** 和 SBE / DBE 计数（可在 nvidia-smi `--query-remapped-rows` 看到）。当某一行 HBM 出现不可纠正错误时，会启用备用行。大规模集群每周都会有零星 ECC 事件，**不需要立即换卡**，但连续多颗 GPU 的 DBE 率上升通常是散热或电源问题的前兆。这也是第 10 篇（checkpoint 与故障容忍）的重要输入。

### 14.7 NUMA 与 CPU 绑定

一张 DGX H100 有 2 个 CPU socket、8 张 GPU，GPU 0–3 和 GPU 4–7 分别挂在不同的 CPU 上。dataloader 进程如果不绑 NUMA，会出现”CPU 从远端内存读数据 → 再喂给本地 GPU”的性能浪费。训练前：

```
numactl --cpunodebind=0 --membind=0 python train.py  # GPU0-3 训练进程
```

PyTorch 2.x 可用 `torchrun --local-ranks-filter ... --cpu-set ...` 控制。

### 14.8 Stream 与并发

CUDA 里每次 kernel launch 默认在 `default stream` 上排队，完全串行。要让”计算和通信重叠”或”两个无关 kernel 并发”，必须创建多条 stream：

```
cudaStream_t s_comp, s_comm;
cudaStreamCreate(&s_comp);
cudaStreamCreate(&s_comm);
// 计算 stream
gemm_kernel<<<..., s_comp>>>(...);
// 通信 stream 同时进行
ncclAllReduce(..., s_comm);
// 需要同步时
cudaEventRecord(e, s_comm);
cudaStreamWaitEvent(s_comp, e, 0);
```

Megatron-LM 的 TP all-reduce 和下一层计算就是这样重叠的，DeepSpeed ZeRO-3 的 param fetch 也是。PyTorch 里对应 `torch.cuda.Stream` + `record_stream`。

### 14.9 GPU Direct RDMA（GDR）

默认数据路径：GPU → PCIe → CPU → PCIe → NIC。GDR 允许 NIC 直接读写 GPU 显存，跳过 CPU：

- 延迟减少 2–3 μs
- 不挤 CPU 内存带宽
- 大 batch all-reduce 吞吐提升显著

需要启用 `NCCL_IB_GID_INDEX`、安装 `nvidia-peermem`、NIC 与 GPU 在同一 PCIe Switch 下。这些在第 4 篇会细讲。

## 十五、一个完整的例子：把 decode 打到 80% HBM 利用率

串起来看一个实战：LLaMA-3 70B，单 H100，batch=16 的 decode 阶段怎么优化。

### 15.1 基线

- 原生 PyTorch + SDPA：latency 每 token 约 140 ms，HBM 带宽利用率约 55%
- util% 显示 100%——**util 100% 不等于好**，实际算力利用率 4%

### 15.2 优化项与贡献

  
|优化|原理|单项收益|
|---|---|---|
|FlashDecoding|把 decode 的 KV 分块，多个 SM 并行扫同一条序列|1.3×|
|GQA + KV cache FP8|减少 KV 带宽|1.4×|
|CUDA Graph|消除 kernel launch gap|1.15×|
|算子融合（RMSNorm+QKV）|减少 kernel 数|1.1×|
|Continuous batching|让 batch 真的是 16|1.5×|
|W8A16（权重 INT8）|权重带宽减半|1.7×|

组合起来，latency 从 140 ms → 22 ms，HBM 利用率 ~80%，MFU 从 4% 提到 18%。**decode 能做到 20% 已是工业界顶尖水平**——物理定律（Roofline）决定了上限。

### 15.3 为什么还上不去

计算 AI：70B × 2 字节权重 / (70B 参数 × 2 FLOPs × 16 batch) ≈ 0.03 FLOPs/B——**decode AI 天生比 H100 拐点（295）小 4 个数量级**。想突破，要么：

- 增大 batch（拉 AI，延迟变差）
- 推测解码（一次验证多个 token，AI 倍增）
- MTP（multi-token prediction，DeepSeek-V3 路线）
- 权重量化到极致（W4、W2）

这些留到第 12、14、15 篇讲。

## 十六、附录：选卡速查与 FAQ

### 16.1 场景 → 推荐卡

   
|场景|首选|次选|备注|
|---|---|---|---|
|70B 模型预训练|H100/H200 × N 节点|A100 × 更多|核心看 NVLink / IB 拓扑|
|70B 模型微调（LoRA）|1×H100 80G 或 2×A100 80G|1×A100 80G|QLoRA 可降到 48 GB|
|70B 推理高吞吐|H200 / MI300X|8×A100|HBM 容量决定 batch 上限|
|13B 推理低延迟|H100 / L40S|4090（受限）|decode 带宽是关键|
|RAG embedding|L40S / A10 / 消费卡|——|算力需求低|
|训练 MoE 1T|B200 NVL72|多节点 H100|all-to-all 对互联要求极高|

### 16.2 FAQ

**Q：RTX 4090 24GB 能跑 70B 吗？** A：单卡不行（70B FP16 权重 140 GB），量化到 Q4 约 40 GB，需要 2 张 4090 + tensor parallel。但消费卡 NVLink 被阉割，TP 通信走 PCIe，吞吐会很差，适合玩玩不适合生产。

**Q：H100 SXM 和 PCIe 版本差多少？** A：SXM5 TDP 700W、HBM 3.35 TB/s、NVLink 900 GB/s；PCIe 350W、3 TB/s、NVLink 600 GB/s。峰值 BF16 也有差（989 vs 756 TFLOPS）。训练必用 SXM，推理 PCIe 性价比更高。

**Q：H100 和 H800 区别？** A：H800 是出口合规版，算力相同，**NVLink 带宽砍到 400 GB/s**。对 TP / all-reduce 密集的训练影响较大，推理基本无感。H20、H200 合规版类似逻辑。

**Q：MI300X 为什么没打赢 H100？** A：单卡纸面算力和带宽都超过 H100，但 ROCm 生态距 CUDA 2–3 年差距；NCCL 替代（RCCL）、FlashAttention 移植、框架适配都还在补齐。Meta、微软已在大规模部署，生态在 2025 年进步明显。

**Q：国产卡做推理可行吗？** A：可行度顺序大致是：Ascend 910B/910C（华为全栈，MindSpore / vLLM-Ascend 可用）> 海光 DCU（ROCm fork，移植成本低）> 沐曦 / 壁仞（生态更早期）。训练级别仍主要靠 Ascend 集群。

**Q：什么时候轮到 Rubin / B300？** A：B300 预计 2025 下半年量产，Rubin R100 路线图指向 2026，配套 HBM4、Vera CPU、NVLink 6。大厂 2026 采购主轴会从 H100/H200 切到 B200/B300，部分客户直接跳到 Rubin。

**Q：训练一定要 BF16 吗，FP8 现在能用了吗？** A：H100 之后，主力训练框架（Megatron-Core、NeMo、TransformerEngine）都支持 FP8 训练。典型路线：权重主副本 FP32，前向/反向激活 + 权重计算 FP8，优化器状态 BF16 或 FP32。实测 70B 规模 FP8 vs BF16 loss 曲线几乎重合，吞吐快 1.5–1.8×。但 1B 以下小模型 FP8 有时不稳，慎用。

**Q：消费卡做推理服务合规吗？** A：NVIDIA 驱动 EULA 明确禁止”数据中心场景”使用 GeForce 系列。生产部署用 L40S / L20 / H100 PCIe / 国产替代。

**Q：一张卡能跑多少 QPS？** A：无法一概而论。70B Q4 模型，H100 单卡典型 ~30 QPS（每请求 512 token，batch=32）；7B BF16，L40S 可以做到 200+ QPS。**具体数字得上 vLLM / SGLang 压测**，理论值参考意义有限。

### 16.3 一页命令速查

```
# 查看 GPU 列表与显存
nvidia-smi
nvidia-smi topo -m              # 拓扑：NV4 / PHB / SYS
nvidia-smi nvlink -s            # NVLink 链路状态

# 查看 driver / CUDA / 固件
nvidia-smi -q | grep -E "Driver|CUDA|VBIOS"

# 实时 watch
watch -n 1 nvidia-smi
nvidia-smi dmon -s pucvmet      # power/util/clock/mem/ecc/temp

# 锁频（排查降频）
nvidia-smi -lgc 1980            # 锁定 SM 1980 MHz
nvidia-smi -rgc                 # 恢复

# 查看 remap 行（HBM 健康）
nvidia-smi --query-remapped-rows=gpu_uuid,remapped_rows.pending --format=csv

# 使用 DCGM 采集
dcgmi dmon -e 1001,1002,1003,1004  # SM 活跃、mem 活跃、FP64、Tensor

# Nsight 采样
nsys profile -o run python train.py
ncu --set full -o kernel python bench.py
ncu --target-processes all --launch-skip 5 --launch-count 1 python bench.py

# 查 PyTorch 感知到的 GPU
python -c "import torch; print(torch.cuda.get_device_properties(0))"

# 清显存（当进程已死但显存未释放）
nvidia-smi --gpu-reset -i 0     # 需要 root
fuser -v /dev/nvidia*           # 找出占着的进程
```

### 16.4 学习资源清单

- 入门：NVIDIA《CUDA C++ Programming Guide》前 5 章
- 进阶：Jeremy Appleyard 的 cuBLAS / cuDNN talks；Horace He 的 PyTorch 性能博客
- 代码：[cuda-samples](https://github.com/NVIDIA/cuda-samples)、[cutlass](https://github.com/NVIDIA/cutlass)、[flash-attention](https://github.com/Dao-AILab/flash-attention)
- 视频：GTC 每年的 “Making Transformers Fast” 系列
- 中文：NVIDIA 开发者博客、李沐《动手学深度学习》算力章节
- Triton：官方 tutorials + OpenAI Triton 主仓 examples

## 十七、小结：大模型工程师的 GPU 心智模型

1. **“GPU 是一堆 SM，每个 SM 是一堆 warp，每个 warp 是 32 条 lane 同步执行”**——忘掉”GPU 有一万个核心”的说法
2. **“内存层级是 5 个数量级的带宽阶梯，谁让 tile 在 SRAM/寄存器里多活几下，谁就赢”**
3. **“所有大模型负载先分两类：计算受限 还是 带宽受限”**——Roofline 先拍一下，方案就定了一半
4. **“训练的瓶颈在通信，推理 decode 的瓶颈在带宽，prefill 的瓶颈在算力”**——这三个结论会贯穿后面 20 篇
5. **“MFU 不是 util%，util% 不是 MFU”**——看真指标
6. **“NVLink 和 HBM 这两个数量级的带宽，是 LLM 时代的基础设施红利”**——离开它们，再大的算力也用不起来
7. **“国产替代看的是软件栈，不是 spec sheet”**——算力追上容易，生态追上要年头

后面的 23 篇，所有关于并行、调度、KV cache、量化、推理引擎的讨论，都是在上面这 7 条基础上做工程展开。带着这套心智模型去看 Megatron 的切分、vLLM 的 PagedAttention、DeepSpeed 的 ZeRO、FlashAttention 的 tiling，会发现它们的思路惊人一致：**让正确的数据在正确的时刻出现在正确的存储层级**。

下一篇进入 CUDA 软件栈：cuBLAS / cuDNN / NCCL / Triton / CUTLASS 各自负责什么、什么时候用 PyTorch 自带、什么时候要手写 kernel、国产替代的工具链长什么样。

## 参考资料

1. NVIDIA. _CUDA C++ Programming Guide_，v12.x
2. NVIDIA. _H100 Tensor Core GPU Architecture Whitepaper_，2022
3. NVIDIA. _Blackwell Architecture Whitepaper_，2024
4. NVIDIA. _Hopper Architecture In-Depth_，GTC 2022
5. Tri Dao 等. _FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness_，NeurIPS 2022
6. Tri Dao. _FlashAttention-2: Faster Attention with Better Parallelism and Work Partitioning_，2023
7. Shah 等. _FlashAttention-3: Fast and Accurate Attention with Asynchrony and Low-precision_，2024
8. Williams 等. _Roofline: An Insightful Visual Performance Model for Multicore Architectures_，CACM 2009
9. Hennessy & Patterson. _Computer Architecture: A Quantitative Approach_，6th ed.
10. Jia 等. _Dissecting the NVIDIA Volta GPU Architecture via Microbenchmarking_，2018
11. Luo 等. _Benchmarking and Dissecting the NVIDIA Hopper GPU Architecture_，2024
12. Triton 官方文档：[https://triton-lang.org/](https://triton-lang.org/)
13. CUTLASS 官方仓库与教程：[https://github.com/NVIDIA/cutlass](https://github.com/NVIDIA/cutlass)
14. NVIDIA Nsight Compute / Systems 用户手册
15. 华为昇腾. _CANN 架构与达芬奇 Cube 说明_
16. 华为昇腾. _Ascend 910B Architecture Reference_
17. AMD. _CDNA3 Architecture Whitepaper_，2023
18. AMD. _Instinct MI300X Performance Characterization_，2024
19. Google. _TPU v5p System Architecture_，2024
20. MLPerf Training / Inference 历年结果，[https://mlcommons.org/](https://mlcommons.org/)
21. DeepSeek 团队. _DeepSeek-V3 Technical Report_（FP8 训练章节），2024
22. Horace He. _Making Deep Learning Go Brrrr From First Principles_，2022

---

**上一篇**：[大模型基础设施全景：训练、推理、RAG、Agent、观测](https://quant67.com/post/llm-infra/01-intro/01-intro.html) **下一篇**：[CUDA 生态：cuBLAS、cuDNN、NCCL、Triton、CUTLASS](https://quant67.com/post/llm-infra/03-cuda-stack/03-cuda-stack.html)

## 同主题继续阅读

把当前热点继续串成多页阅读，而不是停在单篇消费。

2026-04-25 · architecture / ai-infra

### [【大模型基础设施工程·特别篇】DeepSeek-V4 与国产芯片：从备份路线到主路径](https://quant67.com/post/llm-infra/26-deepseek-v4-domestic-chip/26-deepseek-v4-domestic-chip.html)

DeepSeek-V4 发布后，如果国产芯片已经支撑旗舰模型的关键训练或推理链路，它会怎样影响 NVIDIA 生态、国产 AI 芯片、云厂商、模型团队和工程师的技术选择？

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】03：CUDA 生态——cuBLAS、cuDNN、NCCL、Triton、CUTLASS](https://quant67.com/post/llm-infra/03-cuda-stack/03-cuda-stack.html)

从 nvcc 到 Triton，把 NVIDIA 软件栈的每一层拆给大模型工程师看，顺便谈谈 ROCm、CANN 为什么一直追不上。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】04：互联与网络——NVLink、InfiniBand、RoCE 与国产替代](https://quant67.com/post/llm-infra/04-interconnect/04-interconnect.html)

从 NVLink / NVSwitch / NVL72 到 InfiniBand NDR 与 RoCEv2，再到华为 CloudMatrix、阿里 HPN、腾讯星脉，系统梳理万卡集群互联的工程选型与踩坑。

2026-04-22 · architecture / ai-infra

### [大模型基础设施工程](https://quant67.com/post/llm-infra/index.html)

面向中国工程团队的大模型基础设施系列。从 GPU/CUDA/互联、训练框架与 3D 并行、vLLM/SGLang 推理引擎、量化与推测解码、RAG/Agent 到服务化、网关、可观测性与安全合规，覆盖 LLMOps 全链路。