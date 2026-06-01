做大模型训练与推理，八成以上的工程师并不直接写 CUDA kernel——他们写的是 PyTorch 算子、Megatron 配置、vLLM 调度逻辑。但是只要性能出问题，问题最后几乎一定沉到 CUDA 这一层。Nsight 里看到的 `volta_sgemm_128x128_nn`、日志里蹦出的 `NCCL WARN`、新硬件要升 cuDNN 9、Triton kernel 里突然 `ptxas` 报错……如果连 CUDA 生态的分层都说不清楚，调起来就只能靠运气。

这一篇把 NVIDIA 的软件栈从下往上拆一遍：**编译链 → Runtime/Driver → 数学库 → 通信库 → 高层 DSL → 工具链**，再顺手对比一下 AMD ROCm、华为 CANN 的定位。读完你应该能回答：

- Triton 跟 CUTLASS 是什么关系？FlashAttention 到底用哪个写？
- cuBLASLt 的 epilogue 能吃掉多少算子融合？
- CUDA Graph 为什么在 decode 阶段真的救命？
- 为什么 AMD 的硬件参数不差，但训练圈还是只认 NVIDIA？

## 一、CUDA 生态全景：从 PTX 到 PyTorch 的 7 层

先上一张分层图，后面所有章节都会回到这张图。

![CUDA 生态全景：从 PTX 到 PyTorch 的 7 层](https://quant67.com/post/llm-infra/03-cuda-stack/images/03-cuda-stack-fig1.svg)

几个你必须内化的”层次感”：

- **PTX 是虚拟 ISA**，前向兼容；**SASS 是真机器码**，每代架构（Volta/Ampere/Hopper/Blackwell）都不同。升级驱动能让老 PTX 重新 JIT 成新 SASS，这是 CUDA 护城河的地基。
- **Runtime API** 大多数 PyTorch 工程师天天用（隐式）；**Driver API** 是 MIG、多进程、IPC、CUDA Graph 捕获这些更底层操作的入口。
- **数学库 vs 通信库** 是 LLM 的两条命门：前者决定单卡 GEMM/Attention 跑多快，后者决定多卡 AllReduce 能不能打满带宽。

## 二、CUDA 语言与编译链：nvcc、PTX、SASS

### 2.1 一个最小 kernel 怎么被编译

```
// add.cu
__global__ void add(const float* a, const float* b, float* c, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) c[i] = a[i] + b[i];
}
```

编译命令：

```
nvcc -arch=sm_90a -O3 -c add.cu -o add.o
# 或一次性产出 fatbin（同时包含多代架构）
nvcc -gencode arch=compute_80,code=sm_80 \
     -gencode arch=compute_90,code=sm_90 \
     -gencode arch=compute_90,code=compute_90 \
     add.cu -o add
```

`nvcc` 本身不是完整编译器，它把 host 代码交给 gcc/clang，把 device 代码送进 NVIDIA 自己的 LLVM 前端，产出 **PTX**；再由 `ptxas` 把 PTX 翻成 **SASS**（最终的 `cubin`）。多个架构的 `cubin` 打包进 **fatbin**，运行时驱动按实际 GPU 选一个。

### 2.2 几个工程上必须知道的细节

- **`compute_XX` vs `sm_XX`**：前者是 PTX 虚拟架构，后者是真实 SASS。只带 PTX 的会在首次运行时 JIT（慢几百毫秒）。生产环境一般两者都带。
- **`sm_90` vs `sm_90a`**：`a` 后缀代表 “architecture-specific”，用到 Hopper TMA、wgmma 这类新指令时必须加。Blackwell 是 `sm_100`、`sm_100a`。
- **反汇编看 SASS**：`cuobjdump --dump-sass a.out` 或 `nvdisasm`。排查 Tensor Core 用没用上时很常用——找 `HMMA.16816`（Ampere FP16）、`QGMMA`（Hopper）、`IMMA`（INT8）。
- **PTX 注入**：可以用 `asm volatile(...)` 内嵌 PTX，`cp.async`、`mbarrier.arrive`、`wgmma` 等新特性最先通过 PTX 暴露，CUDA C++ 再慢慢包装。FlashAttention-3、DeepGEMM 都大量用内联 PTX。

### 2.3 Runtime vs Driver API

  
||Runtime API|Driver API|
|---|---|---|
|头文件|`cuda_runtime.h`|`cuda.h`|
|库|`libcudart.so`|`libcuda.so`（驱动自带）|
|前缀|`cudaXxx`|`cuXxx`|
|上下文|隐式（per-thread）|显式 `CUcontext`|
|典型用户|PyTorch、cuBLAS、99% 应用|CUDA Graph capture、MIG、IPC handle、JIT 编译模块|

实战中最常见的”Driver API 穿透”场景：

- **`cuMemCreate` + `cuMemMap`** 做 VMM（虚拟内存管理），vLLM 的 PagedAttention 显存池、CUDA Graph 下的动态显存都用它。
- **`cuIpcGetMemHandle`**：多进程共享显存，早期张量并行用过。
- **MIG**：`cuDeviceGetUuid`、`CUDA_VISIBLE_DEVICES=MIG-xxx` 识别切分实例。

一个坑：**Driver API 版本必须 ≥ Runtime API 版本**。`nvidia-smi` 显示的 “CUDA Version: 12.4” 是驱动能支持的最高 Runtime，不代表已经安装了 CUDA 12.4 toolkit。

### 2.4 典型错误与对照表

工程上最常见的编译 / 运行期错误，与其对照关系：

  
|症状|根因|处理|
|---|---|---|
|`no kernel image is available`|fatbin 没包含当前 GPU 的 SASS，也没带 PTX|重编译加 `-gencode arch=compute_90,code=compute_90`|
|首次运行慢几百毫秒，之后正常|PTX JIT 编译|预热；或者在部署侧做 `cuModuleLoadData` 预加载|
|`CUDA driver version is insufficient`|驱动低于 Runtime 期望|升级 `nvidia.ko`（重启节点），或降 CUDA Toolkit|
|`ptxas error: Register allocation failed`|kernel 寄存器压力超过 255|降 `--maxrregcount`、拆 kernel、减 `num_stages`|
|`CUDA_ERROR_ILLEGAL_ADDRESS` 随机出现|越界 / race / graph 捕获期地址变化|`compute-sanitizer --tool memcheck/racecheck`|
|`CUBLAS_STATUS_NOT_SUPPORTED`|不支持的 shape/dtype 组合|换 cuBLASLt + heuristic，或 fallback CUTLASS|

`compute-sanitizer`（原 `cuda-memcheck`）是 LLM 团队排查 kernel 崩溃的主力，`--tool memcheck` 查越界，`--tool racecheck` 查 shared memory 竞态，`--tool synccheck` 查 `__syncthreads` 误用。

大模型里的计算其实很集中：**GEMM 占 60–80%，Attention 占 10–25%，剩下是 LayerNorm/激活/Embedding**。所以数学库的选择几乎等价于性能的天花板。

### 3.1 cuBLAS 与 cuBLASLt：GEMM 的两张脸

**cuBLAS** 是经典 BLAS 接口（`cublasSgemm`、`cublasGemmEx`），接口几十年没变。它内部已经调度到 Tensor Core，但接口表达能力差——比如想做 `D = alpha * (A @ B) + bias` 再接 GELU，裸 cuBLAS 就得三次 kernel launch。

**cuBLASLt**（Lt = Light-weight / Lightning？官方没解释过）是新接口，核心概念是 **matmul descriptor + epilogue**：

```
cublasLtMatmulDesc_t  op;
cublasLtMatmulDescCreate(&op, CUBLAS_COMPUTE_32F, CUDA_R_32F);

cublasLtEpilogue_t epi = CUBLASLT_EPILOGUE_GELU_BIAS;
cublasLtMatmulDescSetAttribute(op, CUBLASLT_MATMUL_DESC_EPILOGUE,
                                &epi, sizeof(epi));
cublasLtMatmulDescSetAttribute(op, CUBLASLT_MATMUL_DESC_BIAS_POINTER,
                                &bias_ptr, sizeof(bias_ptr));

cublasLtMatmul(handle, op,
               &alpha, A, Adesc, B, Bdesc,
               &beta,  C, Cdesc, D, Ddesc,
               &algo, workspace, ws_size, stream);
```

epilogue 支持的组合（部分）：

- `BIAS` / `RELU` / `GELU` / `SILU` / `SWISH`
- `BGRADA` / `BGRADB`（反向传播时顺手算 bias grad）
- `DRELU_BGRAD` / `DGELU_BGRAD`（激活 + bias 的反向）
- `AUX` 输出（保存激活前的值给反向用）

**这对 LLM 意味着什么**：Transformer 里 `Linear(x) + bias → GELU` 这类 pattern 直接压成一个 kernel，省一次显存往返。FP8 训练的 scale 更新、INT8 推理的 per-channel scaling 也是通过 epilogue 挂上去的。

cuBLASLt 还暴露了 **heuristic / algo 选择**：

```
cublasLtMatmulPreference_t pref;
cublasLtMatmulPreferenceCreate(&pref);
cublasLtMatmulPreferenceSetAttribute(pref,
    CUBLASLT_MATMUL_PREF_MAX_WORKSPACE_BYTES, &ws, sizeof(ws));

cublasLtMatmulHeuristicResult_t res[8];
int ret = 0;
cublasLtMatmulAlgoGetHeuristic(handle, op, Adesc, Bdesc, Cdesc, Ddesc,
                                pref, 8, res, &ret);
// res[0].algo 就是启发式最优，自己也可以 benchmark 选
```

推理引擎（TensorRT-LLM、vLLM 的 cutlass_w8a8 之外的 fallback）都有一个 **autotuner 缓存**，第一次启动慢是因为在跑这个。

### 3.2 cuDNN：卷积时代的遗产，Attention 时代的新家

**cuDNN v1–v7** 是 CNN 黄金年代的产物，接口就是 conv/pool/rnn。Transformer 兴起后一度被绕过——大家直接用 cuBLAS + 手写 softmax/layernorm。

**cuDNN v8 的 graph API** 是一次重大转型，思路是”给我一个算子图，我帮你融合 + 选 kernel”：

```
// 伪代码
auto graph = cudnn::graph::Graph()
    .tensor(Q).tensor(K).tensor(V)
    .matmul(Q, K.transpose(), &S)
    .softmax(S, &P)
    .matmul(P, V, &O);
graph.validate(); graph.build(handle);
graph.execute(handle, variant_pack);
```

**cuDNN v9** 里直接内置了 **Flash Attention forward/backward**（`SDPA` 算子），包含：

- Causal / sliding window / custom mask
- MQA / GQA（head 分组）
- FP16 / BF16 / FP8（Hopper+）
- dropout、ALiBi bias

PyTorch 的 `F.scaled_dot_product_attention` 在新 GPU 上会优先路由到 cuDNN SDPA，次选 FlashAttention（Tri Dao 的 OSS 实现），最后才是 math backend。可以用 `torch.backends.cuda.sdp_kernel(...)` 显式选。

### 3.3 CUTLASS / CuTe：模板元编程的大锤

cuBLAS/cuDNN 是**闭源黑盒**，给不了你所有形状 / epilogue / 数据类型。CUTLASS 是 NVIDIA 的**开源模板库**，你可以像搭乐高一样拼 GEMM：

```
using Gemm = cutlass::gemm::device::Gemm<
    cutlass::half_t, cutlass::layout::RowMajor,   // A
    cutlass::half_t, cutlass::layout::ColumnMajor,// B
    cutlass::half_t, cutlass::layout::RowMajor,   // C
    float,                                          // accumulator
    cutlass::arch::OpClassTensorOp,
    cutlass::arch::Sm90,
    cutlass::gemm::GemmShape<128, 128, 64>,       // ThreadblockShape
    cutlass::gemm::GemmShape< 64,  64, 64>,       // WarpShape
    cutlass::gemm::GemmShape< 16,   8, 16>>;      // InstructionShape
```

**CuTe** 是 CUTLASS 3.x 的新核心，引入了 **Layout 代数**——一套描述 tensor 在内存 / 寄存器 / 共享内存 / Tensor Core 片段之间怎么排布、怎么切的数学抽象。Hopper 的 wgmma、TMA 都通过 CuTe 暴露。

工程上什么时候需要 CUTLASS：

- 想支持 cuBLAS 没有的 dtype 组合（比如 W4A16 的 GPTQ 反量化 + GEMM 融合）。
- 想把 epilogue 扩展到 cuBLASLt 没提供的（比如 Mixtral 的 routed expert + scale）。
- DeepSeek-V3 的 FP8 GEMM、DeepGEMM、Mixtral 的 MoE kernel、SGLang 的部分 kernel 都是 CUTLASS 写的。

**复杂度警告**：CUTLASS 的模板错误能翻好几屏。新项目先看 Triton 能不能满足；只有 Triton 榨不出来时再下沉 CUTLASS。

## 四、通信库：NCCL 与 NVSHMEM

### 4.0 集合通信的复杂度直觉

先建立一个感性认识。假设 N 个 GPU 每卡 M 字节参数，跨卡带宽 B：

|操作|理想通信量|Ring 实现步数|备注|
|---|---|---|---|
|AllReduce|2M(N-1)/N|2(N-1)|本质是 RS + AG|
|ReduceScatter|M(N-1)/N|N-1|每卡最终只留 1/N|
|AllGather|M(N-1)/N|N-1|每卡最终看到全量|
|All-to-All|M(N-1)/N（每卡发送）|N-1|MoE 场景|
|Broadcast|M|log₂N（tree）|一对多|

对训练：**DP/ZeRO 的梯度同步、TP 的 AllReduce、PP 的 Send/Recv、MoE 的 All-to-All** 四类吃满了通信预算。算一下就知道”理论能打多少带宽”——NCCL 实际 bus bandwidth 在现代硬件上能到 80–90% 的链路上限。

### 4.1 NCCL：集合通信的事实标准

NCCL（NVIDIA Collective Communications Library）提供 MPI 风格的集合 + 点对点 API：

- **AllReduce**：DP 梯度同步、TP 的 `all_reduce`（RowParallel 反向、ColumnParallel 正向）。
- **AllGather**：ZeRO-3 参数前向、TP 的 RowParallel 正向收 shard。
- **ReduceScatter**：ZeRO-2/3 梯度、TP 的 ColumnParallel 反向。
- **Broadcast**：Checkpoint 分发、seed 同步。
- **All-to-All**：MoE expert 路由的主力；Sequence Parallel、Ulysses 也用。
- **Send/Recv**：PP 流水线相邻 rank 之间传激活 / 梯度。

**拓扑算法选择**（NCCL 自动决定，可用环境变量强制）：

- **Ring**：N-1 次点对点，带宽最优但延迟线性。大消息（> 几 MB）默认。
- **Tree**：log N 延迟，小消息好。NCCL 2.4 开始用 **Double Binary Tree**，两棵树方向相反，吃满双向带宽。
- **CollNet / SHARP**：在 IB switch 上做 in-network reduction（Mellanox SHARP），让 switch 直接算加法，AllReduce 带宽翻倍。H100 + Quantum-2 集群默认开。

常用调优环境变量（训练踩坑必备）：

```
export NCCL_DEBUG=INFO                      # 第一次上来先打开
export NCCL_IB_DISABLE=0                    # 有 IB 就别 disable
export NCCL_IB_HCA=mlx5_0,mlx5_1,...        # 选网卡
export NCCL_IB_GID_INDEX=3                  # RoCE 常用
export NCCL_SOCKET_IFNAME=eth0              # TCP fallback 走哪张网卡
export NCCL_P2P_LEVEL=NVL                   # 强制用 NVLink（否则可能走 PCIe）
export NCCL_NVLS_ENABLE=1                   # Hopper NVLink SHARP
export NCCL_ALGO=Ring,Tree,CollNetDirect    # 允许的算法
export NCCL_PROTO=Simple,LL,LL128           # 协议
export NCCL_BUFFSIZE=8388608                # 内部 buffer
```

调优一条心得：**出了问题先 `NCCL_DEBUG=INFO` 看它选了哪条路**。90% 的”AllReduce 怎么这么慢”都是 P2P 没走 NVLink 或 IB 走了单网卡。

### 4.2 NVSHMEM：GPU 直接通信

NCCL 是 kernel **之外**调用的（host 发起），每次都要 launch 一个通信 kernel。NVSHMEM 则把通信 API 暴露给 **device 代码**，kernel 内部可以直接 `nvshmem_put`、`nvshmem_barrier`。

典型用法：

- **MoE dispatch/combine**：DeepEP（DeepSeek 开源）就是基于 NVSHMEM，把 All-to-All 融进 expert forward kernel，消除多次 launch。
- **FlashInfer、某些长序列注意力**：跨 GPU 读 KV Cache 时用 NVSHMEM。
- 细粒度 overlap：compute 还在跑，同一个 warp 发 put 把结果直接扔给邻居。

代价：**复杂**。NVSHMEM 要求对 symmetric heap、quiet/fence、signal pad 都有概念。普通训练不需要碰，但研究前沿系统绕不开。

### 4.3 NCCL 性能测试与诊断

`nccl-tests` 是标定集群健康度的第一工具：

```
# 单机 8 卡
./build/all_reduce_perf -b 8 -e 8G -f 2 -g 8

# 多机（与 mpirun 配合）
mpirun --allow-run-as-root -np 16 -H node1:8,node2:8 \
       -x NCCL_DEBUG=INFO -x NCCL_IB_HCA=mlx5 \
       ./build/all_reduce_perf -b 8M -e 8G -f 2 -g 1
```

重点看 `busBW` 列（bus bandwidth，考虑了算法放大因子）：

- H100 + NVLink 4（单机）：AllReduce busBW 约 370 GB/s（900 GB/s 链路的 82%）。
- H100 + IB NDR 8×400Gb/s（多机）：busBW 约 340 GB/s，接近双向 400 GB/s 上限。
- 如果实测远低于此——要么拓扑没认对，要么 PCIe switch 瓶颈，要么 rail 没配齐。

常见数量级异常信号：

- 单机 AllReduce < 100 GB/s → P2P 没走 NVLink，`nvidia-smi topo -m` 检查。
- 多机 AllReduce < 50 GB/s → IB 走到了单卡单 rail，`NCCL_IB_HCA` 没写全。
- 消息 < 1MB 的小包效率差 → 开 `NCCL_ALGO=Tree` + `NCCL_PROTO=LL128`。

### 4.4 通信与计算 overlap

训练框架会把通信拆成**多个 bucket**，每个 bucket 计算完就发起 AllReduce，这样下一个 bucket 的计算和上一个的通信同时进行。PyTorch DDP 里 `bucket_cap_mb` 默认 25MB——大了延迟高，小了 launch 多、算法效率低。

Hopper + NVLS 之后，NCCL 甚至能把 AllReduce 拆成细粒度、与 GEMM kernel 交错执行（compute/comm overlap in stream）。Megatron-LM 的 `--overlap-grad-reduce` 就是这套。

### 5.1 OpenAI Triton：LLM 算子的”汇编替代品”

Triton 是 Python DSL，可以认为是”用 Python 写 CUDA”。核心思想：**tile 是一等公民**，程序员操作 `BLOCK_M × BLOCK_K` 的 tile，Triton 编译器自动完成 warp 划分、shared memory 分配、async copy pipelining、swizzle。

一个 softmax 的完整示例：

```
import torch
import triton
import triton.language as tl

@triton.jit
def softmax_kernel(out_ptr, in_ptr, stride_row, n_cols,
                   BLOCK_SIZE: tl.constexpr):
    row = tl.program_id(0)
    cols = tl.arange(0, BLOCK_SIZE)
    mask = cols < n_cols

    x = tl.load(in_ptr + row * stride_row + cols,
                mask=mask, other=-float('inf'))
    x = x - tl.max(x, axis=0)
    num = tl.exp(x)
    den = tl.sum(num, axis=0)
    y = num / den

    tl.store(out_ptr + row * stride_row + cols, y, mask=mask)


def softmax(x: torch.Tensor) -> torch.Tensor:
    n_rows, n_cols = x.shape
    BLOCK = triton.next_power_of_2(n_cols)
    out = torch.empty_like(x)
    softmax_kernel[(n_rows,)](out, x, x.stride(0), n_cols,
                              BLOCK_SIZE=BLOCK,
                              num_warps=4)
    return out
```

十几行，性能在 `n_cols ≤ 8192` 时与 cuDNN 打平甚至更快。换成 CUDA C++ 要几百行。

一个更有代表性的 GEMM 例子（Triton 官方教程简化版）：

```
@triton.autotune(
    configs=[
        triton.Config({'BM':128,'BN':128,'BK':32,'GROUP_M':8},
                      num_warps=4, num_stages=3),
        triton.Config({'BM':128,'BN':256,'BK':64,'GROUP_M':8},
                      num_warps=8, num_stages=3),
    ],
    key=['M','N','K'],
)
@triton.jit
def matmul_kernel(a_ptr, b_ptr, c_ptr,
                  M, N, K,
                  stride_am, stride_ak,
                  stride_bk, stride_bn,
                  stride_cm, stride_cn,
                  BM: tl.constexpr, BN: tl.constexpr,
                  BK: tl.constexpr, GROUP_M: tl.constexpr):
    pid = tl.program_id(0)
    num_pid_m = tl.cdiv(M, BM)
    num_pid_n = tl.cdiv(N, BN)
    # L2 cache 友好的 pid swizzle
    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    offs_am = (pid_m * BM + tl.arange(0, BM)) % M
    offs_bn = (pid_n * BN + tl.arange(0, BN)) % N
    offs_k  = tl.arange(0, BK)
    a_ptrs = a_ptr + offs_am[:, None]*stride_am + offs_k[None, :]*stride_ak
    b_ptrs = b_ptr + offs_k[:, None]*stride_bk + offs_bn[None, :]*stride_bn

    acc = tl.zeros((BM, BN), dtype=tl.float32)
    for k in range(0, tl.cdiv(K, BK)):
        a = tl.load(a_ptrs, mask=offs_k[None,:] < K - k*BK, other=0.)
        b = tl.load(b_ptrs, mask=offs_k[:,None] < K - k*BK, other=0.)
        acc += tl.dot(a, b)
        a_ptrs += BK * stride_ak
        b_ptrs += BK * stride_bk

    c = acc.to(tl.float16)
    offs_cm = pid_m * BM + tl.arange(0, BM)
    offs_cn = pid_n * BN + tl.arange(0, BN)
    c_ptrs = c_ptr + offs_cm[:, None]*stride_cm + offs_cn[None, :]*stride_cn
    mask = (offs_cm[:, None] < M) & (offs_cn[None, :] < N)
    tl.store(c_ptrs, c, mask=mask)
```

这段代码在 A100 上能到 cuBLAS 95% 左右。`num_stages` 控制 software pipelining（多少级 `cp.async` 预取），`GROUP_M` 是经典的 L2 swizzle，让相邻 block 共享 A 的 row。

Triton 的位置：**FlashAttention、Mamba、vLLM 的很多 kernel、PyTorch Inductor 的 codegen 后端**都是它。你完全可以把 Triton 当作 “LLM 时代的 CUDA”。

### 5.2 JAX / XLA：编译式框架

XLA（Accelerated Linear Algebra）是 Google 的 tensor 编译器，架构上分 **HLO → MLIR (MHLO/StableHLO) → device-specific lowering**。JAX 把 Python 函数 trace 成 HLO，再交给 XLA。

对 LLM 工程：

- **TPU 上除 XLA 没别的选**。Gemini、PaLM、很多 Google 内部模型都靠它。
- **GPU 上**也能跑（OpenXLA/IREE/GSPMD），但生态远不如 PyTorch。
- **SPMD 分区**（`jax.jit` + `shard_map`）是 JAX 的杀手锏，代码层就能表达张量并行。

国内一些团队（MiniMax 的一些早期实验、部分对齐研究）用过 JAX，但工业主流仍然 PyTorch + Megatron。

### 5.3 TVM / MLIR：编译器体系

- **TVM**：学术 + 华为 + 部分国产 NPU 路径。Relay/Relax IR + schedule / MetaSchedule 做算子 auto-tuning，适合端侧 / 异构后端。
- **MLIR**：LLVM 家族的多级 IR 框架。Triton、XLA、IREE、CUDA-Q、Mojo、TorchMLIR 全都基于 MLIR 的 dialect 体系。某种程度上 MLIR 是编译器世界的”中台”。

工程师层面：**不需要精通**，但读 Triton/XLA 错误栈时会看到 `mhlo.`、`tt.`、`llvm.` 这些 dialect 前缀，知道它在说什么即可。

### 5.4 torch.compile / Inductor：默认编译时代

PyTorch 2.x 的 `torch.compile(model)` 背后是 **TorchDynamo（前端 graph 捕获）+ AOTAutograd（反向图）+ Inductor（codegen）**。对 GPU，Inductor 现在的首选后端就是 **Triton**——你看到的 `/tmp/torchinductor_xxx/xxx.py` 文件里全是 Triton kernel。

对 LLM 工程师：

- 推理：`torch.compile(model, mode="reduce-overhead")` 会自动用 CUDA Graph 包住生成的 Triton kernel。
- 训练：`mode="default"` 或 `"max-autotune"`，后者允许更长编译时间换性能。
- 动态 shape：通过 `dynamic=True` 或 `torch._dynamo.mark_dynamic`，能捕获”序列长度可变”这类常见场景。

工程上不是所有模型都适合 compile——graph break（图分裂）一多，收益打折；自定义 autograd function、复杂 Python 控制流都可能触发 fallback。看收益的标准动作：`TORCH_LOGS=graph_breaks,recompiles python xxx.py`。

## 六、Nsight 工具链：性能问题的唯一真相来源

Nsight 分三件套，定位完全不同：

  
|工具|粒度|回答什么问题|
|---|---|---|
|Nsight Systems（`nsys`）|时间线（毫秒）|GPU 空不空闲？CPU/GPU/NCCL 有没有 overlap？launch 开销多大？|
|Nsight Compute（`ncu`）|单 kernel（指令）|某个 kernel 为什么慢？SM 占用、带宽、Tensor Core 利用率|
|Nsight Graphics|渲染|游戏 / 可视化，LLM 不用|

### 6.1 Nsight Systems 常用命令

```
nsys profile -o trace -t cuda,nvtx,cudnn,cublas \
             --cuda-graph-trace=node \
             python train.py
```

产出 `.nsys-rep`，用 Nsight Systems GUI 打开能看到：

- 每条 CUDA stream 的 kernel 排布
- NCCL 通信条带
- NVTX 用户打点（PyTorch 的 `torch.cuda.nvtx.range_push` 能打标签）
- CPU 侧 Python 调用栈

判断健康的”训练时间线”长什么样：

- GPU compute 条带基本连续，不留大段空白。
- NCCL 通信和 compute **有 overlap**（ZeRO-1 的 AllReduce、DP 的梯度桶）。
- Kernel launch 间隔极短（微秒级），如果看到毫秒级间隔——CPU bottleneck。

### 6.2 Nsight Compute：拆单个 kernel

```
ncu --set full --kernel-regex "sgemm|flash_attn" \
    -o kernel_report python bench.py
```

关键指标（Hopper 举例）：

- **SM Occupancy**：实际 warp 数 / 理论最大。太低 → 寄存器 / shared mem 压力太大。
- **Achieved FLOPS %**：相比 peak FP16/FP8 的百分比。GEMM 期望 > 70%。
- **DRAM Throughput**：memory-bound kernel（softmax / layernorm / attention backward）看这个。
- **Tensor Core Utilization**：Tensor Core 指令数 / 总指令数。低于 50% 说明没吃满 HMMA。

常见诊断：

- Attention 的 `dS = dP ⊙ P` 这类 reduction 慢 → 换 FlashAttention。
- GEMM M/N/K 里有一个很小（典型：decode 阶段 M=1 的 batched GEMM）→ 换 GEMV 或 CUTLASS 的 streamK。
- LayerNorm 慢 → 融合到前/后 GEMM 的 epilogue 里。

### 6.3 一个真实排查流程

举个常见故事：“训练吞吐比上周低 15%”：

1. `nsys profile` 跑 50 步，打开时间线。
2. 对比基线图。发现 GPU 空闲条纹多了，出现在每次 AllReduce 之后。
3. 点 AllReduce 条带，看 duration 从 8ms 涨到 14ms。
4. 检查 `NCCL_DEBUG=INFO` 日志，发现 rank 3 走了 `NET/Socket` 而不是 `NET/IB`——网卡被别的 pod 占了。
5. 隔离节点、重启 fabric manager，恢复正常。

另一个：推理 p99 突然翻倍：

1. `ncu` 抓一个慢请求的 kernel。
2. Attention kernel 的 `Achieved Occupancy` 从 60% 掉到 25%。
3. 检查输入，发现序列长度从典型 2k 涨到 32k，FlashAttention 的 tile 切法没匹配。
4. 加长序列 bucket、调 `softmax_scale` 精度、升 FA3，恢复。

结论：**性能问题不靠猜，工具链给的数据就是真相**。

单 kernel launch 大约 **5–20 微秒**（主要是 CPU 端准备）。训练一个 step 几百毫秒，launch 只占 1%，无所谓。但是——

**Decode 阶段一个 token 可能只需要几毫秒**，几十个 kernel launch 加起来的 overhead 能占到 30–50%！这就是为什么小 batch decode 必须用 CUDA Graph。

核心思路：**一次 capture，多次 replay**。把一整步的 kernel 序列录下来，之后每次直接回放整张图。

```
# 简化版 PyTorch 使用
stream = torch.cuda.Stream()
with torch.cuda.stream(stream):
    # warm up
    for _ in range(3):
        y = model(static_input)
    torch.cuda.synchronize()

    # capture
    g = torch.cuda.CUDAGraph()
    with torch.cuda.graph(g):
        y = model(static_input)  # 所有 tensor 必须地址不变

# replay
for _ in range(N):
    static_input.copy_(real_input)  # 原地拷贝
    g.replay()
    real_output.copy_(static_output)
```

vLLM、SGLang、TensorRT-LLM 都做了 **按 batch size 分桶 capture**——每个 bucket（比如 1/2/4/8/16/32）捕一张图，推理时按 batch 选桶。

坑：

- Graph 里的所有 tensor **地址必须固定**，动态 shape 要么 padding 到 bucket、要么用 **Graph Update / conditional node**（CUDA 12+）。
- PagedAttention 的 block table 是动态的，需要配合 **CUDA Graph + graph input update** 或 **persistent kernel**。
- 调试时 Nsight 里看到的每个 node 要用 `--cuda-graph-trace=node` 才展开，否则显示成一整块。

### 7.1 CUDA Graph 的两种 API

**Stream capture**（推荐，99% 场景够用）：

```
cudaStreamBeginCapture(stream, cudaStreamCaptureModeThreadLocal);
// ... 正常 launch 一堆 kernel / memcpy
cudaGraph_t graph;
cudaStreamEndCapture(stream, &graph);

cudaGraphExec_t exec;
cudaGraphInstantiate(&exec, graph, 0);
for (int i = 0; i < N; ++i)
    cudaGraphLaunch(exec, stream);
```

**Explicit graph API**：手动添加 node、edge，适合需要运行期修改拓扑的场景，比如 conditional node、device graph（CUDA 12 开始支持 kernel 内 launch graph）。

### 7.2 动态性怎么处理

LLM 推理的动态源头：变长 prompt、KV cache 增长、batch 合并拆分。工程上的常见手法：

- **按 seq len / batch 分桶**：16/32/64/128/256/512/1024/2048…，每个桶一张 graph。命中时回放，不命中时 fallback eager。
- **`cudaGraphExecUpdate`**：不改结构只改参数（kernel 参数、memcpy 目的地址），比重建图快得多。vLLM 的 PagedAttention block table 就用它。
- **Device graph（CUDA 12.3+）**：kernel 内部 `cudaGraphLaunch`，让 GPU 自己决定下一个子图。MoE 路由、推测解码树状展开都能用。

### 7.3 收益量化

H100 + Llama-3 8B decode，batch=1：

|模式|单 token 延迟|吞吐|
|---|---|---|
|Eager|~32 ms|31 tok/s|
|CUDA Graph|~17 ms|59 tok/s|
|CUDA Graph + FP8|~11 ms|91 tok/s|

小 batch 收益最明显；batch 变大（≥64），launch 占比被摊薄，graph 收益降到 5–10%。

**Transformer Engine（TE）** 是 NVIDIA 专门为 Transformer 写的库，核心是 **Hopper/Blackwell 上的 FP8 自动混合精度**。

FP8 有两种格式：**E4M3**（4 位指数 3 位尾数，表示范围小但精度高，用于前向 / 激活）和 **E5M2**（范围大精度低，用于梯度）。精度只有 BF16 的 1/3，直接用会训飞。

TE 的核心是 **per-tensor delayed scaling**：

1. 记录每个 tensor 最近 N 步的最大绝对值 `amax`。
2. 用 `amax` 算 scale：`scale = FP8_MAX / amax`。
3. 量化：`x_fp8 = clip(x * scale, -FP8_MAX, FP8_MAX)`；反量化时除以 scale。
4. scale 本身用 FP32 存，随每个 GEMM 走；反向传播时同样套一次。

用法：

```
import transformer_engine.pytorch as te
from transformer_engine.common.recipe import DelayedScaling, Format

fp8_recipe = DelayedScaling(fp8_format=Format.HYBRID,
                            amax_history_len=1024,
                            amax_compute_algo="max")

layer = te.TransformerLayer(hidden_size=4096, ffn_hidden_size=16384,
                             num_attention_heads=32)

with te.fp8_autocast(enabled=True, fp8_recipe=fp8_recipe):
    out = layer(x)
```

性能：H100 FP8 相比 BF16 约 **1.6–1.9x 吞吐**，训练 loss 几乎不掉（<0.05% 差异）。DeepSeek-V3 是第一个大规模开源 FP8 训练，但没用 TE——他们自己写的 block-wise scaling（更激进），说明 TE 并不是唯一方案。

Blackwell（B200）引入 **MXFP8 / MXFP4**（micro-scaling，更细粒度的 block scale），TE 会跟进，但生态还在过渡。

### 8.1 FP8 训练的踩坑清单

真实落地 FP8 训练时，团队常踩这些坑：

- **激活 outlier**：LayerNorm 后某些 token 的某些 channel 值特别大，per-tensor scale 会把其他 channel 压成 0。解法：SmoothQuant 思路的 activation re-scaling，或改 per-channel / per-block（128×128 tile）scale。DeepSeek-V3 的方案是后者。
- **Attention 中间值溢出**：`Q @ K^T` 在 FP8 下容易爆；通常 attention matmul 仍保留 BF16 累加，只有 QKV/Output projection 和 FFN 用 FP8。
- **梯度下溢**：E5M2 的最小正数是 ，比 FP16 的 denormal 还大一点，梯度小于这个的会丢失。搭配 loss scaling（动态调 scale）。
- **Master weight 仍然要 FP32**：否则 Adam 的 累积会漂。FP8 只是前向 / 反向激活 + 权重参与计算，优化器状态保持 FP32。
- **断点续训**：FP8 scale history 也要 checkpoint，否则 restart 前几步质量会抖。

### 8.2 FP8 推理

推理比训练容易：

- 权重离线量化成 FP8（一次性），激活在线量化（每个 token）。
- **TensorRT-LLM、vLLM、SGLang** 都支持 W8A8-FP8，Hopper 上相比 BF16 约 1.5–1.8x 吞吐。
- 精度通常只掉 1–2% 左右（MMLU 等基准），很多场景可以接受。

MXFP4（B200 的 4 bit micro-scaling）更激进——训练端还在研究，但推理端已经有 NVIDIA / AMD 共同推动的 OCP 标准，2026–2027 年会是热点。

FlashAttention 的思想在 [02-gpu-primer](https://quant67.com/post/llm-infra/02-gpu-primer/02-gpu-primer.html) 讲过——tile QKV、online softmax、不落盘 attention matrix。这里对比两种实现流派：

### 9.1 CUTLASS 实现（FlashAttention-2/3 官方）

Tri Dao 团队的 FA2、FA3（Hopper）都是 CUTLASS + 大量内联 PTX：

- **FA2**：A100 上 50–70% peak FP16。
- **FA3**：H100 上 75% peak FP16，FP8 1.2 PFLOPs；用到 wgmma 异步 GEMM、TMA 异步 copy、producer-consumer warp specialization。

优点：极致性能，支持所有主流变体（causal / sliding window / GQA / ALiBi / softcap / deterministic）。 缺点：代码极其复杂，改一个 mask pattern 要懂 CuTe Layout 代数。

### 9.2 Triton 实现（FlashAttention-Triton、FlashInfer 前身）

Triton 版在 OpenAI 官方 tutorial 里就有，社区改出无数变体：

- **vLLM 的 paged attention kernel**
- **FlashInfer 早期实现**
- **Mamba / RetNet / linear attention 的 attention 类算子**

优点：Python 写，150 行就能跑，研究速度快；调度（tile 大小、num_warps）简单。 缺点：Hopper wgmma 支持落后 CUTLASS 半年到一年，Blackwell 支持更慢。

工程选择的经验法则：

- **生产训练 / 推理、标准 causal attention** → 用 FA3 官方库（或 cuDNN SDPA）。
- **需要定制 mask / score bias / 新 attention 变体** → Triton 先原型，性能不够再移植 CUTLASS。

### 9.3 FlashAttention 性能数据参考

A100 (40GB) / H100 (80GB) 上 head_dim=128, causal=True，FP16：

|实现|A100 TFLOPs|H100 TFLOPs|特点|
|---|---|---|---|
|PyTorch 原生（scaled_dot_product + math）|40|60|baseline|
|FA2（CUTLASS）|180|360|经典实现|
|FA3（CUTLASS + wgmma + TMA）|—|540|Hopper 专属|
|FA3-FP8|—|820|掉 1%精度|
|Triton FA（社区）|160|320|代码可改|
|cuDNN SDPA|170|480|闭源黑盒|

数据仅作量级参考，具体随 seq len / head dim / GQA 组数变化很大。典型用法：训练长序列用 FA3，推理短序列 decode 阶段用 PagedAttention kernel。

### 10.1 AMD ROCm / HIP / rocBLAS / RCCL

AMD 的答卷，接口几乎是 CUDA 的一一映射：

|CUDA|ROCm 对应|
|---|---|
|nvcc|hipcc|
|cudart|hip-runtime|
|cuBLAS|rocBLAS / hipBLASLt|
|cuDNN|MIOpen / Composable Kernel|
|NCCL|RCCL|
|CUTLASS|Composable Kernel（CK）|
|Nsight|rocprof / Omniperf|

**HIPify** 工具能自动把 CUDA 代码翻译成 HIP 代码（`cuda*` → `hip*`）。MI300X 硬件参数（FP16 TFLOPS、HBM 带宽）都不输 H100，但：

- rocBLAS 在非标准 shape 上比 cuBLAS 慢 10–30%。
- MIOpen 的 attention 支持落后 cuDNN 一到两代。
- Triton-AMD、PyTorch ROCm 可用但踩坑多；很多算子 fallback 到 eager。
- RCCL 虽然兼容 NCCL 接口，但 Infinity Fabric 拓扑算法成熟度差。

生态圈里真正在 MI300X 上大规模训练的是 Meta、微软、Databricks 等少数厂商，而且都配了专门的 kernel 团队。普通用户还是老老实实买 H100/H200。

### 10.2 华为 CANN / MindSpore / Ascend

华为昇腾（Ascend 910B/910C）的栈：

|层|华为对应|
|---|---|
|CUDA 语言|Ascend C / TBE|
|cuBLAS/cuDNN|AscendCL 算子库、ATB|
|NCCL|HCCL|
|框架|MindSpore（主）、PyTorch via torch_npu|
|编译器|GE（Graph Engine）、MindIR|

工程现状：

- **兼容 PyTorch** 是国内厂商的主力路径（`torch_npu` 插件），代码改动最小。
- **盘古、文心、混元** 等国产大模型都有 Ascend 训练版本。
- DeepSeek-V3 公布过 910B 上的推理适配；Qwen、GLM 都维护 Ascend 分支。
- **出海 / 受制裁场景** 是强驱动力，2024–2026 年 910B/910C 的国内产能爬坡很快。

痛点依然是 **算子覆盖**——FlashAttention-3 级别的优化、FP8 支持、MoE All-to-All 都要华为 / 大厂 kernel 团队手写。

### 10.3 SYCL / OpenCL（衰落）

- **OpenCL**：曾经的”跨厂商 CUDA 替代”，2015 年后基本被各家自家栈（CUDA、ROCm、Metal、CANN）抛弃。
- **SYCL / DPC++**：Intel 主推，Aurora 超算、Ponte Vecchio GPU 用。理念好（单源 C++ + Intel oneAPI），但 Intel 自己的 GPU 在 AI 训练圈份额微乎其微，ARC / Gaudi 又是另一套，生态碎。

简单说：**2026 年，LLM 工程师日常只需要会 CUDA，偶尔碰 ROCm / CANN；SYCL / OpenCL 基本可以忽略**。

### 10.4 国产栈全景一瞥

除了华为 Ascend，国内 2024–2026 的主要 AI 芯片软件栈：

   
|厂商 / 芯片|编程栈|框架适配|定位|
|---|---|---|---|
|华为 Ascend 910B/910C|CANN / Ascend C|MindSpore + torch_npu|训练 + 推理，国企 / 政企首选|
|寒武纪 MLU590/MLU370|Neuware / BANG C|torch_mlu + TensorFlow|推理为主|
|海光 DCU（GPGPU）|DTK（基于 ROCm）|PyTorch DTK|兼容 CUDA 源码|
|壁仞 BR100|BIRENSUPA / suCL|PyTorch 插件|训练推理通用（出货受限）|
|摩尔线程 MTT S4000|MUSA / MUSA C++|torch_musa|消费 + 数据中心|
|昆仑芯 R200/P800|XPU SDK / XDNN|PaddlePaddle 原生、PyTorch 插件|百度内部 + 外供|
|平头哥（含光）|HGAI / HalideIR|阿里内部|阿里云自用推理|

共性问题：**都在追 CUDA 接口**，而不是自建生态。短期务实；长期（2028+）谁能做出自己的算子库 + 编译器 + 工具链一体化体验，谁才算真正立住。

经常有人问：“AMD 的 MI300X 参数明明更好，为什么没人用？”答案不在硬件，而在 **15 年的软件栈复利**：

1. **kernel 库深度**：cuBLAS 的每一个 GEMM shape、cuDNN 的每一个 conv kernel 都有 NVIDIA 工程师调过；autotuner cache 覆盖了几十万种形状。
2. **编译器成熟度**：ptxas 的寄存器分配、指令调度比 ROCm LLVM 后端领先一代。
3. **论文即实现**：FlashAttention、Mamba、Triton、TE——新算法的参考实现默认 CUDA。社区无意中把 NVIDIA 绑定写进了每一篇顶会代码。
4. **工具链**：Nsight Systems / Compute 的体验至今没有等量替代品。rocprof + Omniperf 还差一截。
5. **框架默认值**：PyTorch 的 `.cuda()`、JAX 的 default platform、所有 vllm/sglang/megatron 的 CI 都是 CUDA。
6. **人才**：社招搜”CUDA kernel”简历比”HIP kernel”多一个数量级。

AMD 要追上得做三件事：(a) 把 CK 做到 cuBLAS + CUTLASS 的合体水平；(b) 让主流开源项目把 ROCm 当一等公民；(c) 堆钱赞助顶会实现。三件都需要 3–5 年。

**结论**：短期（到 2028）CUDA 仍然是大模型的操作系统。了解 ROCm / CANN 是为了合规、供应链备份，而不是替代。

## 十二、工程师日常：一条决策链

写一个新 kernel 之前，按这条链问自己：

```
1. cuBLAS / cuBLASLt 能不能做？
   ├─ 能（GEMM + epilogue 组合）→ 直接用，结束
   └─ 不能 ↓

2. cuDNN 有没有现成算子？
   ├─ 有（卷积 / SDPA / RNN）→ 直接用
   └─ 没有 ↓

3. 社区开源 kernel 有没有？
   ├─ FA3 / DeepGEMM / xformers / flashinfer / flux / …
   │   有且满足需求 → 拿来用（顺便提 PR 改 bug）
   └─ 没有 ↓

4. Triton 能写吗？
   ├─ 能（不是极端小 shape / 没有奇怪 layout）→ Triton，工时 1–3 天
   └─ 不能或性能不够 ↓

5. CUTLASS / CuTe
   ├─ 团队有 CUDA 专家 → 值得投入，工时 1–4 周
   └─ 没有 ↓

6. 回头重新审视业务需求
   ├─ 能不能改算法避开这个 kernel？
   └─ 绝大多数情况：能。
```

**reinvent CUDA kernel 是 LLM 团队最容易掉进去的坑之一**。一个业务问题 80% 可以通过 “换算子组合 + 开 torch.compile” 解决，剩下 15% 靠 Triton，真正需要下到 CUTLASS 的不到 5%。

## 十三、一个完整的 Triton GEMM + 性能对比 demo

放一个可以直接跑的脚本，对比 Triton、cuBLAS 在典型 LLM GEMM 形状上的性能：

```
import torch, time
import triton

# 假设上面 matmul_kernel 已定义
def triton_matmul(a, b):
    M, K = a.shape
    K2, N = b.shape
    assert K == K2
    c = torch.empty((M, N), device=a.device, dtype=torch.float16)
    grid = lambda META: (triton.cdiv(M, META['BM']) * triton.cdiv(N, META['BN']),)
    matmul_kernel[grid](a, b, c,
                        M, N, K,
                        a.stride(0), a.stride(1),
                        b.stride(0), b.stride(1),
                        c.stride(0), c.stride(1))
    return c

def bench(fn, *args, iters=50, warmup=10):
    for _ in range(warmup): fn(*args)
    torch.cuda.synchronize()
    t0 = time.perf_counter()
    for _ in range(iters): fn(*args)
    torch.cuda.synchronize()
    return (time.perf_counter() - t0) / iters

# Llama-7B 一个典型 QKV proj shape: [batch*seq, 4096] × [4096, 12288]
shapes = [(4096, 4096, 4096), (4096, 4096, 12288), (8192, 4096, 4096)]
for M, K, N in shapes:
    a = torch.randn((M, K), device='cuda', dtype=torch.float16)
    b = torch.randn((K, N), device='cuda', dtype=torch.float16)
    t_triton = bench(triton_matmul, a, b)
    t_torch  = bench(torch.matmul, a, b)
    flops = 2 * M * N * K
    print(f"M={M} K={K} N={N}: "
          f"triton {flops/t_triton/1e12:6.1f} TF/s | "
          f"cuBLAS {flops/t_torch/1e12:6.1f} TF/s | "
          f"ratio  {t_torch/t_triton:.2f}")
```

在 H100 上典型输出（示意）：

```
M=4096 K=4096 N=4096:  triton  640.2 TF/s | cuBLAS  710.5 TF/s | ratio 1.11
M=4096 K=4096 N=12288: triton  680.0 TF/s | cuBLAS  735.1 TF/s | ratio 1.08
M=8192 K=4096 N=4096:  triton  650.8 TF/s | cuBLAS  720.3 TF/s | ratio 1.10
```

结论和前面一致：**Triton 能到 cuBLAS 的 85–95%**，代码量是 CUDA 的十分之一，自动 autotune。但极限性能（+5–10%）、极端小 M、不规整 shape，还是 cuBLAS/CUTLASS 赢。

## 十四、小结与下一步

这一篇把 CUDA 生态从 nvcc 到 Triton 都扫了一遍，几条你应该记住的骨干：

- **编译链**：`.cu → PTX → SASS`，`sm_90a` 要写对；`cuobjdump` 能看到是否用上了 Tensor Core。
- **数学库分层**：`cuBLAS/LSt`（黑盒 GEMM + epilogue）→ `cuDNN`（SDPA / 卷积）→ `CUTLASS/CuTe`（模板化，能改）。
- **通信**：`NCCL` 吃 90% 场景，`NVSHMEM` 留给 MoE / overlap 前沿。
- **DSL**：`Triton` 是 LLM 时代事实上的 CUDA，PyTorch Inductor 也靠它。
- **工具链**：`Nsight Systems` 看全局，`Nsight Compute` 看单 kernel，出了问题别靠猜。
- **CUDA Graph + FP8** 是 2024–2026 年在 Hopper 上榨性能的两件套。
- **ROCm / CANN** 兼容 CUDA 接口但生态差一截；短期做供应链备份，长期看 3–5 年。
- **工程决策**：先用库，再用 Triton，最后才 CUTLASS；reinvent kernel 的坑很深。

下一篇 [04-interconnect](https://quant67.com/post/llm-infra/04-interconnect/04-interconnect.html) 会从单机走出去，讲 NVLink / NVSwitch / InfiniBand / RoCE 和国产互联（灵衢、神行互联），以及它们怎么决定一个万卡集群能不能真的跑起来。

## 十五、附录：常用命令速查

### 15.1 环境信息

```
# 驱动 + GPU
nvidia-smi
nvidia-smi topo -m                    # NVLink / PCIe 拓扑
nvidia-smi nvlink -s                  # NVLink 状态
nvidia-smi -q -d ECC                  # ECC 错误

# CUDA Toolkit
nvcc --version
cat /usr/local/cuda/version.json

# 库版本
python -c "import torch; print(torch.__version__, torch.version.cuda)"
python -c "import torch; print(torch.backends.cudnn.version())"
python -c "import triton; print(triton.__version__)"
dpkg -l | grep -E 'cuda|cudnn|nccl|tensorrt'
```

### 15.2 编译与反汇编

```
# 编译多架构 fatbin
nvcc -O3 \
  -gencode arch=compute_80,code=sm_80 \
  -gencode arch=compute_90,code=sm_90a \
  -gencode arch=compute_100,code=sm_100a \
  -gencode arch=compute_100,code=compute_100 \
  kernel.cu -o kernel

# 看 SASS
cuobjdump --dump-sass kernel | less
nvdisasm kernel.cubin | grep -E 'HMMA|QGMMA|IMMA'

# 看 PTX
cuobjdump --dump-ptx kernel
```

### 15.3 性能分析

```
# Nsight Systems
nsys profile -o trace -t cuda,nvtx,nccl,cudnn,cublas \
             --capture-range=cudaProfilerApi \
             --gpu-metrics-devices=all \
             python train.py

# Nsight Compute（单 kernel 详查）
ncu --set full --launch-skip 10 --launch-count 1 \
    --kernel-regex "attn|gemm" \
    -o report python bench.py

# 内存 / 竞态检查
compute-sanitizer --tool memcheck python test.py
compute-sanitizer --tool racecheck python test.py

# NCCL 带宽
./all_reduce_perf -b 8 -e 8G -f 2 -g 8
```

### 15.4 运行期调试环境变量

```
# NCCL
export NCCL_DEBUG=INFO
export NCCL_DEBUG_SUBSYS=INIT,NET,GRAPH

# CUDA
export CUDA_LAUNCH_BLOCKING=1         # 把异步 kernel 同步化（排查崩溃）
export CUDA_VISIBLE_DEVICES=0,1,2,3
export CUDA_MODULE_LOADING=LAZY       # 减少启动显存

# cuBLAS / cuDNN
export CUBLASLT_LOG_LEVEL=5
export CUDNN_LOGINFO_DBG=1

# PyTorch
export TORCH_SHOW_CPP_STACKTRACES=1
export TORCH_LOGS=+dynamo,graph_breaks,recompiles
export TORCH_CUDNN_SDPA_ENABLED=1
```

这些命令和变量在排查 90% 的 CUDA / 性能问题时都会用到，值得加书签。

- NVIDIA, _CUDA C++ Programming Guide_（docs.nvidia.com/cuda）
- NVIDIA, _cuBLAS Library / cuBLASLt User Guide_
- NVIDIA, _cuDNN Developer Guide v9_
- NVIDIA, _CUTLASS 3.x & CuTe Documentation_（github.com/NVIDIA/cutlass）
- NVIDIA, _NCCL Developer Guide_（docs.nvidia.com/deeplearning/nccl）
- NVIDIA, _NVSHMEM User Guide_
- NVIDIA, _Nsight Systems / Compute User Manual_
- NVIDIA, _Transformer Engine Documentation_（github.com/NVIDIA/TransformerEngine）
- OpenAI, _Triton: An Intermediate Language and Compiler for Tiled Neural Network Computations_
- Tri Dao et al., _FlashAttention-2 / FlashAttention-3_
- Chen et al., _TVM: An Automated End-to-End Optimizing Compiler for Deep Learning_
- Google, _XLA: Optimizing Compiler for Machine Learning_
- AMD, _ROCm Documentation / Composable Kernel_
- 华为, _CANN 开发者文档 / MindSpore 文档_
- DeepSeek, _DeepGEMM / DeepEP 开源实现_

---

**上一篇**：[GPU 计算入门：SM、Tensor Core、HBM、NVLink](https://quant67.com/post/llm-infra/02-gpu-primer/02-gpu-primer.html) **下一篇**：[互联与网络：NVLink、InfiniBand、RoCE、国产替代](https://quant67.com/post/llm-infra/04-interconnect/04-interconnect.html)

## 同主题继续阅读

把当前热点继续串成多页阅读，而不是停在单篇消费。

2026-04-25 · architecture / ai-infra

### [【大模型基础设施工程·特别篇】DeepSeek-V4 与国产芯片：从备份路线到主路径](https://quant67.com/post/llm-infra/26-deepseek-v4-domestic-chip/26-deepseek-v4-domestic-chip.html)

DeepSeek-V4 发布后，如果国产芯片已经支撑旗舰模型的关键训练或推理链路，它会怎样影响 NVIDIA 生态、国产 AI 芯片、云厂商、模型团队和工程师的技术选择？

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】02：GPU 计算入门——SM、Tensor Core、HBM、NVLink](https://quant67.com/post/llm-infra/02-gpu-primer/02-gpu-primer.html)

从 CPU 与 GPU 的架构差异出发，讲清楚 SM、Warp、Tensor Core、HBM、NVLink 的工程含义，并结合 Roofline、FlashAttention 与国产算力栈，给出大模型工程师能直接上手的 GPU 心智模型。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】21：推理服务化](https://quant67.com/post/llm-infra/21-serving-infra/21-serving-infra.html)

从单机引擎到生产级集群：Triton、Ray Serve、KServe、vLLM OpenAI Server、PD 分离、LoRA 多租户、KEDA 自动扩缩、Serverless GPU 的全景工程实战。

2026-04-22 · architecture / ai-infra

### [大模型基础设施工程](https://quant67.com/post/llm-infra/index.html)

面向中国工程团队的大模型基础设施系列。从 GPU/CUDA/互联、训练框架与 3D 并行、vLLM/SGLang 推理引擎、量化与推测解码、RAG/Agent 到服务化、网关、可观测性与安全合规，覆盖 LLMOps 全链路。