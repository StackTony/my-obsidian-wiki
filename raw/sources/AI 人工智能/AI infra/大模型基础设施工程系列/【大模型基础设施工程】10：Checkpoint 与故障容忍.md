## 一、引子：万卡训练，为什么每天都在断

如果只看论文，LLM 预训练像是一段优雅的长跑：给定数据、给定超参、给定 N 天的时间，loss 曲线就会优雅地下降。但真正在万卡集群里跑过一次 100B+ 模型预训练的人都知道，现实根本不是那样。

现实是：**训练每隔一两个小时就会断一次**。

Meta 在 LLaMA-3 技术报告里诚实地披露了一组数字：在 16K H100 的集群上训练 405B 模型的 54 天窗口期内，一共发生了 **466 次作业中断**，其中 419 次是”非预期中断”，平均下来大约每 3 小时一次。GPU 相关故障占比最高（约 58%），其中 HBM ECC、NVLink、SM 故障是前三名。xAI 的 Colossus 集群规模到了 10 万卡量级，按线性外推，MTBF（平均无故障时间）只会更短；公开的分享里，xAI 工程师说他们一开始几乎每几分钟就要处理一次故障报警。

这就是万卡训练的第一性现实：**硬件从统计上是”一定会坏”的**，问题不是坏不坏，而是坏的时候你能多快恢复。一次 1 小时的中断，在 1.6 万卡 H100 上按 2 美元/小时算，直接成本就是 32,000 美元；如果恢复要半小时，再乘以一半。真正的代价还不止这些：训练时间被拉长会让模型晚上线，而在 LLM 竞赛里，晚上线一个月等于直接少赚一个数量级的钱。

所以这一篇讲 checkpoint 与故障容忍——它不是训练流水线里最”性感”的模块，却是决定一次千亿级训练能不能按期跑完的关键工程。我们会覆盖：常见故障谱系、checkpoint 的大小与写入路径、异步与分布式 checkpoint、健康检查、弹性训练、以及 Meta / xAI / DeepSeek 的公开经验，最后给一份可以照着落地的 checklist。

## 二、故障谱系：一台训练机到底会怎么坏

在正式进入分类之前，先给一个直观的数字感。假设单颗 GPU 的年故障率（AFR）是 2%——这是业界比较乐观的估计。对一个 16,000 卡的集群，整体**每天**发生至少一次 GPU 硬故障的概率是：

每天 58% 意味着”几乎每天都有事”。而真实的 H100 大规模集群 AFR 显著高于 2%（新硬件磨合期尤甚），加上 GPU 不是唯一故障源，LLaMA-3 那个”平均 3 小时一次中断”就不奇怪了。

下面按硬件层次展开。

### 2.1 GPU 自身：ECC、TDR、SM 故障

**HBM ECC（Error-Correcting Code）错误**：H100 单卡 80 GB HBM3，粒子翻转（bit flip）是物理事实。可纠正的（SBE, single-bit error）会被硬件自动修复并上报；不可纠正的（DBE, double-bit error）会触发 CUDA ERROR_ECC_UNCORRECTABLE，当前 CUDA context 整个作废。LLaMA-3 报告里 HBM 故障占 GPU 故障的相当大比例。

**TDR（Timeout Detection and Recovery）** / GPU hang：某个 kernel 长时间不返回，驱动复位 GPU。通常是死锁（比如 NCCL 集合通信挂起）、非法访问、硬件卡死。复位后 CUDA context 丢失，必须整个进程重来。

**SM 故障**：H100 有 132 个 SM，个别 SM 出现永久故障时，驱动会把这颗卡标为不健康。Nvidia 的 `nvidia-smi -q -d ECC,ROW_REMAPPER` 可以看到行重映射（row remapping）发生了多少次——这是 HBM 老化的强信号。

**温度/功耗**：H100 TDP 700 W，液冷故障时很快热失控降频，整排机柜的 step time 会一起变慢，形成”隐性故障”。

### 2.2 互联：NVLink、NVSwitch、NIC、交换机

**NVLink 降级**：H100 上 18 条 NVLink 单向 450 GB/s，个别链路挂掉时 NCCL 还能跑，但 all-reduce 带宽腰斩。这类故障极其隐蔽，它不会让作业崩，只会让每步时间从 3.2 秒涨到 4.5 秒。

**NVSwitch 故障**：HGX 板上 4 颗 NVSwitch，挂一颗就是 1/4 的内部互联消失。

**IB / RoCE NIC**：每台 H100 服务器通常 8×400Gb IB 或 RoCE NIC，每卡一张。单 NIC 的 link flap（物理层断开重连）几百毫秒就能让 NCCL 超时；更糟的是 PFC 死锁在 RoCE 网络里会让整个 pod 的流量瞬间停住。注：大规模 RoCE 集群下微秒级的 congestion 会使得故障诊断非常困难，通常需要配合网卡硬件层的流级监测（xAI 做法）和交换机 INFA（In-Network Telemetry）。

**交换机 hash 冲突**：ECMP hash 不均导致 leaf-spine 上 8 条 400G 链路里有一两条被打爆，体现为”训练周期性抖动”。xAI 公开提到过他们专门做了 flow-level 的 telemetry 去抓这类问题。

### 2.3 主机、OS、电源、机房

- **OS 内核 panic**：驱动 bug、内存 ECC、PCIe AER 风暴都可能导致宿主机宕机。这类故障粒度粗（整台 8 卡一起没），但恢复相对直接——拉起一个备用节点。
- **PCIe 错误**：PCIe AER 的 Correctable Error 达到阈值后会 link retrain，CUDA 调用会短暂出错。
- **电源 / PDU**：单相断电会掉一排机柜。训练时 16,000 张 H100 瞬时功耗能冲到 11 MW 级别，电网侧电压跌落都可能触发机柜级保护。
- **散热 / 冷却液循环**：液冷 CDU（Coolant Distribution Unit）故障能在几分钟内让整个 pod 停机。

### 2.4 最阴险的一类：SDC

**SDC（Silent Data Corruption）** 是计算结果错了但没有任何硬件报错——ECC 没告警、kernel 没 panic、loss 看上去也没炸。SDC 的来源有：

- 某颗 SM 的运算单元在特定指令序列下偶发错误（Google、Meta 都公开报告过，概率约 到 每操作每天）；
- 内存控制器或 interconnect 在高压下 bit flip 但没被 ECC 覆盖；
- 编译器/驱动 bug 在特定 shape 下走到错误路径。

SDC 的恐怖在于它会**污染 checkpoint**——你过了几个小时才从 loss 发散反推回来，发现两个 checkpoint 前就已经坏了。工业界的对策是：关键节点做 **重复计算对比（redundant execution）**，或者训练流程里抽样 re-run 一个 step，比较两次的 loss/grad norm 是否 bit-wise 一致。

### 3.1 大小估算

Checkpoint 的内容大致是：**模型参数 + 优化器状态 + RNG 状态 + 训练 step / 数据迭代器位置**。前两项占绝对大头。

对一个 参数、Adam 优化器、混合精度训练的模型，fp32 master weight + fp32 的 `m` 和 `v`，每参数需要 12 字节；bf16 的工作参数额外 2 字节；bf16 梯度 2 字节。粗算 **16 字节/参数**。另外需要注意，除了模型参数和优化器，Activation Checkpointing 和部分 CPU Offload 机制占用的 Pinned Memory（见后文 14.2 节）在万卡集群上也极大占用空间，其规划不足极易引发 OOM 或写盘竞争。

  
|模型|参数|Checkpoint 大小（含优化器）|
|---|---|---|
|LLaMA-2 7B|7 × 10⁹|~112 GB|
|LLaMA-2 70B|70 × 10⁹|~1.12 TB|
|LLaMA-3 405B|405 × 10⁹|~6.5 TB（Meta 报告中优化器状态本身约 5 TB）|
|DeepSeek-V3 671B（含 MoE）|671 × 10⁹|~10 TB 量级，分片后单 expert 文件小但总量大|

6.5 TB 单次全量 checkpoint，按 100 GB/s 的分布式文件系统峰值带宽也要 65 秒；如果要 1 分钟做一次、训练不被打断，就必须异步化。

### 3.2 三种写入模式：全量、分片、按 rank 写

**全量单文件（rank-0 集中写）**：rank-0 gather 所有参数，写一个大文件。实现最简单，Hugging Face 的 `model.save_pretrained` 本质就是这种。不适合万卡场景——rank-0 成为带宽瓶颈，gather 自身也是 O(P) 通信。

**分片 checkpoint（ZeRO-style）**：每个 DP rank 写自己那一份 shard，不做聚合。恢复时按相同分片拓扑加载。Megatron、DeepSpeed 默认走这条路。缺点是**分片拓扑改了（比如从 8-way TP 改到 4-way）就很难直接加载**，需要 reshard 工具。

**拓扑无关分片（PyTorch DCP 风格）**：把每个 tensor 的分片元信息单独记录，加载时按目标拓扑重新切分。这也是本篇后面会演示的主流做法。

### 3.3 存储层：本地 NVMe → 分布式文件系统 → 对象存储

```
+------------------+     +-----------------------+     +------------------+
| 训练节点          |     | 存储层                 |     | 冷归档            |
|  local NVMe      | --> | Lustre / BeeGFS /     | --> | S3 / OSS / GCS   |
|  (stage buffer)  |     |  CephFS / GPFS /      |     | (7-day retain)   |
|                  |     |  JuiceFS              |     |                  |
+------------------+     +-----------------------+     +------------------+
      ~3.5 GB/s/卡            100+ GB/s 聚合             TB/s 不要求，便宜就行
```

工程上的主流结构是**三层**：

1. **本地 NVMe 作为 staging**：每节点 8–30 TB NVMe，先把各 rank 的 shard 写到本地（100% 并行，不走网络），这一步是毫秒到秒级的。
2. **并行文件系统（Lustre / BeeGFS / CephFS / GPFS / JuiceFS）作为主存**：用独立的 background 进程把 staging 的文件 rsync / multipart upload 到并行文件系统。Meta、xAI、国内大厂普遍使用 Lustre 或自研类 Lustre；阿里 PAI 有 CPFS、火山有 vePFS、百度 PFS 都是类似形态。
3. **对象存储作为冷备**：每隔 N 个 checkpoint 归档一份到 S3/OSS/GCS，同时用来跨 region 灾备和后续 fine-tune 分发。

为什么一定要有本地 NVMe 这层？因为训练节点写本地盘时带宽能吃到接近硬件上限（H100 节点 Gen5 NVMe 随便 10 GB/s），而写并行文件系统要走 RDMA / TCP，一窝蜂并发容易打爆存储网络，反过来影响训练通信本身。

### 3.4 异步与流式 checkpoint

朴素做法是**同步 checkpoint**：`save_checkpoint()` 里先 `barrier`，所有 rank 一起写，写完再 `barrier`，训练线程整段阻塞。如果 checkpoint 要 60 秒，这 60 秒纯亏。

异步 checkpoint 的核心思路：**把”打快照”和”写盘”解耦**。

- 快照阶段（在主 stream 上、毫秒级）：调用 `tensor.clone()` 或 pinned-host copy，把 GPU tensor 拷贝到 CPU 固定内存。这步必须和训练同步，因为下一 step 就要覆盖这些参数了。
- 写盘阶段（在 background thread / process）：从 CPU buffer 往 NVMe / PFS 写，这步完全异步，训练 step 继续跑。

DeepSpeed 的 `DeepSpeedCheckpoint` async mode、Megatron 的 `--async-save`、以及 PyTorch DCP 的 `async_save` API 都是这个模型。Meta 在 LLaMA-3 里特别强调他们做了异步 checkpoint，把 checkpoint 时间从分钟级压到了秒级。

再进一步是**流式 / in-memory checkpoint**：不落盘，直接把 shard 复制到另一节点的内存里。代表工作是 ByteDance 的 Gemini（SOSP’23），以及 Meta 的 Check-N-Run。思路是：内存比磁盘快 100 倍，而整个集群的 CPU 总内存足够大，完全可以做 “peer memory as checkpoint storage”；只有当多节点同时宕机（远低于单节点故障率）时才需要回退到磁盘版本。

## 四、代码示例：PyTorch DCP 异步保存

下面给一个最小可用的 DCP（Distributed Checkpoint）异步保存与恢复示例，适用于 FSDP / HSDP 训练。

```
# ckpt_dcp.py
# PyTorch >= 2.3，推荐 2.4+
import os
import torch
import torch.distributed as dist
import torch.distributed.checkpoint as dcp
from torch.distributed.checkpoint.state_dict import (
    get_state_dict, set_state_dict,
    StateDictOptions,
)
from torch.distributed.checkpoint import FileSystemWriter, FileSystemReader

CKPT_ROOT = "/mnt/pfs/runs/llama3-405b/ckpt"

def save_async(model, optimizer, step: int, writer_threads: int = 8):
    """异步分布式 checkpoint：快照在主线程同步，写盘在后台。"""
    path = os.path.join(CKPT_ROOT, f"step-{step:09d}")
    model_sd, optim_sd = get_state_dict(
        model, optimizer,
        options=StateDictOptions(full_state_dict=False, cpu_offload=True),
    )
    state = {"model": model_sd, "optim": optim_sd, "step": step}
    writer = FileSystemWriter(path, thread_count=writer_threads, single_file_per_rank=True)
    # async_save 返回一个 Future，训练线程立刻可以继续
    fut = dcp.async_save(state, storage_writer=writer)
    return fut

def load_latest(model, optimizer) -> int:
    """按目录中最新 step 恢复，返回下一步的 step。"""
    steps = sorted(
        int(d.split("-")[1]) for d in os.listdir(CKPT_ROOT)
        if d.startswith("step-")
    )
    if not steps:
        return 0
    step = steps[-1]
    path = os.path.join(CKPT_ROOT, f"step-{step:09d}")
    model_sd, optim_sd = get_state_dict(
        model, optimizer,
        options=StateDictOptions(full_state_dict=False, cpu_offload=True),
    )
    state = {"model": model_sd, "optim": optim_sd, "step": 0}
    dcp.load(state, storage_reader=FileSystemReader(path))
    set_state_dict(
        model, optimizer, model_state_dict=state["model"], optim_state_dict=state["optim"]
    )
    if dist.get_rank() == 0:
        print(f"[ckpt] resumed at step={step}")
    return step + 1

# 训练主循环
def train_loop(model, optimizer, dataloader, max_steps, save_every=200):
    start_step = load_latest(model, optimizer)
    pending_fut = None
    for step in range(start_step, max_steps):
        batch = next(dataloader)
        loss = model(batch).loss
        loss.backward()
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)

        if step > 0 and step % save_every == 0:
            if pending_fut is not None:
                pending_fut.result()  # 上一轮必须写完再发新快照
            pending_fut = save_async(model, optimizer, step)
    if pending_fut is not None:
        pending_fut.result()
```

几点工程注意：

- `cpu_offload=True` 在 `get_state_dict` 里是关键——它把分片从 GPU 拷到 CPU pinned memory，这是异步化的前提。
- `single_file_per_rank=True` 让每个 rank 独立写一个文件，避免并发写同一 HDF5/tar。
- **必须在发下一个 async_save 之前 `.result()` 上一个**，否则两个后台写会同时抢 NVMe 带宽，还可能把 CPU 快照 buffer 冲掉。
- 分片拓扑（FSDP rank 数、TP 大小）改变后重启，DCP 会自动 reshard；但张量名字不能改。

## 五、恢复时间（RTO）优化

一次故障的总恢复时间可以拆成四段：

  
|阶段|主要耗时|优化手段|
|---|---|---|
|detect|NCCL timeout 默认 30 分钟；进程挂掉后 k8s/slurm 上报|把 NCCL_TIMEOUT 调到 2–5 分钟；心跳 watchdog|
|reschedule|找到替换节点、拉镜像、起容器|热备池（standby nodes）、镜像本地缓存|
|load|读 checkpoint + 建 NCCL communicator|本地 staging + 并发读；NCCL lazy init|
|warmup|torch.compile / CUDA graph 重建|编译 cache 持久化|

### 5.1 Detect：别傻等 NCCL timeout

默认 `NCCL_IB_TIMEOUT=18`、`NCCL_TIMEOUT=1800000` 毫秒——一次挂起要等 30 分钟才被发现。万卡训练里这绝对不可接受。工程做法：

- 把 NCCL timeout 调到 2–5 分钟；
- 训练脚本里单起一个 watchdog 线程，监控 step time 的滑窗 P99，连续 N 步超阈值就强制 abort；
- 节点级 agent 订阅 `nvidia-smi dmon`、ib_diag、SMART、`ipmitool sel`，发现硬件异常直接发 SIGTERM。

### 5.2 Reschedule：热备池

Meta / xAI 的做法都是预留 2%–5% 的**热备节点（standby pool）**。它们平时在跑健康检查，一旦某台挂了，调度器（基于 k8s Volcano / Slurm / 自研）从热备池抽一台顶上，镜像和 dataset 已经预热，分钟级切换。阿里 PAI 的 DLC、火山 veMLP 都有类似设计。

### 5.3 Load：并发读 + 本地预热

- **并发读**：分布式 checkpoint 可以让每个 rank 只读自己那一份，不走 rank-0 broadcast。DCP 默认如此。
- **本地预热**：训练过程中后台持续把最新 checkpoint 预热到每个节点的本地 NVMe（类似 DRAM cache），故障时从本地盘直接读。
- **lazy comm init**：NCCL communicator 的构建本身在万卡上要几十秒，上次通信计划能复用的尽量复用。

### 5.4 一个好指标：**Resume at nearest step**

Meta 在 LLaMA-3 文中用了一个朴素但好用的指标：**从故障发生到恢复到第一个有效训练 step 的墙钟时间**。他们的目标是 < 10 分钟；做到后，每天损失的有效训练时间从十几小时压到两小时以内。

## 六、健康检查：启动前、运行中、结束后

### 6.1 启动前：NCCL all-reduce 打桩

每次作业启动，**先跑 60 秒的 NCCL 健康测试**，不合格直接踢节点：

```
# 节点级 NCCL 自测
mpirun -np $(( 8 * NNODES )) \
  --hostfile hosts \
  nccl-tests/build/all_reduce_perf \
    -b 8 -e 8G -f 2 -g 1 \
    --check 1 --iters 50
```

关键检查项：

- 每 GPU 到每 GPU 的 NVLink P2P 带宽达到标称（H100 NVLink 约 900 GB/s 双向）；
- all-reduce 的 bus bandwidth 不应有超过 5% 的节点间离群；
- IB 带宽每卡应≥ 350 Gbps（理论 400）；
- `ibstat`、`nvidia-smi -q` 没有 ECC/Xid 错误。

任一项不过，节点打 `NODE_UNHEALTHY` 标签，调度器自动挑热备。

### 6.2 运行中：loss、grad、每步耗时

运行时健康监控三件套：

1. **loss / grad norm 异常**：loss 突然 NaN 或 grad norm 飙到历史中位数的 100 倍，暂停并打 checkpoint，留待人工判断是 SDC 还是 loss spike。
2. **Slow node 识别**：每个 rank 每步上报 forward / backward / all-reduce 的墙钟时间，prometheus 聚合后按节点 boxplot。某个节点连续 50 步 P99 慢于集群中位数 1.5×，判定为 straggler。
3. **硬件 telemetry**：`dcgm-exporter` 把 ECC、温度、SM 利用率、NVLink error counter 打到 Prometheus，有告警规则。

### 6.3 SDC 检测：重复计算对比

这是 Meta / Google 都公开投资的方向：每隔 M 步，随机抽一个 micro-batch，在”另一组卡”上 re-run 一次，比较输出 tensor 的哈希。不一致就触发 RCA 工作流。成本约 0.5%–2% 的 throughput，换来的是”能不能检测到已经污染了多个小时训练的 SDC”——值。

## 七、容错机制的四种范式

### 7.1 Checkpoint + Restart

最主流、最朴素：训练定期 checkpoint，出故障就 kill 全作业、修/换节点、从最近 checkpoint 重启。LLaMA-3、DeepSeek、Qwen、GLM 的大模型训练报告里都是这个主框架。

优点：实现简单、语义干净、checkpoint 本来就要有。 缺点：RTO 分钟级；浪费一个 checkpoint 间隔的训练进度。

### 7.2 Elastic：Torch Elastic / Ray Train

**弹性训练**允许 world size 在作业生命周期内变化。Torch Elastic（`torchrun --standalone --nnodes=1:8`）和 Ray Train、Nvidia Resiliency 都支持：某节点挂了，剩下的节点可以缩容继续跑，也可以等新节点加入后再扩回去。

工程现实：弹性是好，但**真正在大 TP/PP 拓扑下弹性扩缩容很难**——张量并行度变化意味着切分要重来。实际采用 elastic 更多是”缩容保命 + checkpoint 后原拓扑重启”的组合，而不是真的在 3D 并行下动态变化。

### 7.3 In-place replacement：热备替换

热备节点已经带好镜像、挂好存储、跑过健康检查；故障发生后，调度器把它注入作业的那一 rank 位置，其他 rank 不动。需要训练框架支持”局部 rank 重连”，Nvidia Resiliency、MSFT Resiliency 的核心能力就是这个。代价是有持续的热备开销（通常 2%–5% 集群），但对万卡 7×24 训练这个代价非常值。

### 7.4 Pipeline-stage 粒度重启

在流水线并行（PP）里，一个故障 rank 通常只影响它所在的 stage。可以做”单 stage 重启 + pipeline flush”，比整作业重启快很多。Megatron-LM 在大作业里会启用这类优化。

## 八、一些工业界公开的数字和经验

先列一张横向对比表，方便有个整体 sense。数据来源于各家公开报告、博客、会议分享，不同口径之间有些出入，仅供参考。

    
|项目|规模|MTBF 量级|典型 RTO|有效训练时间占比|
|---|---|---|---|---|
|Meta LLaMA-3 405B|16K H100|~3 h|分钟级|~90%|
|xAI Colossus|100K H100|小时级（公开估计）|分钟级|公开未披露|
|DeepSeek-V3|约 2K H800|天级|分钟级|90%+|
|MosaicML MPT|数百 A100|数天|小时级（早期）|~85%|
|Google PaLM / Gemini|数千 TPU pod|工程实现自研|分钟级|>95%（官方口径）|

### 8.1 Meta LLaMA-3（405B）

Meta 的技术报告（2024 年 7 月）是目前公开最详尽的万卡故障报告：

- 16K H100、54 天训练窗口；
- **419 次非预期中断**，~每 3 小时一次；
- 故障构成：GPU ~58%、HBM ECC 是 GPU 故障里的头号原因、NVLink/NVSwitch 次之；host 硬件 ~12%；网络 ~8%；软件 bug、调度系统等占剩下的。
- 核心对策：**大幅异步化的 checkpoint + 热备节点 + 启动健康检查**，把”恢复到下一个有效 step”的时间压到分钟级。
- 他们特别提到：PyTorch 的 `NCCL_ASYNC_ERROR_HANDLING`、自研 NCCL flight recorder（记录最后 N 条集合通信）大大加速了 RCA。

### 8.2 xAI Colossus

xAI 2024 年在 Memphis 部署的 Colossus 集群，第一阶段 10 万张 H100，第二阶段扩到 20 万。公开分享里强调了几点：

- **液冷 + 高密度**，故障面首先是冷却和供电；
- **Ethernet（RoCE）而非 IB** 是大胆选择；为此他们做了极激进的 QoS 和 flow 级 telemetry；
- 10 万卡级的训练，**checkpoint 从内存到对象存储的全链路吞吐**是一个独立课题；
- 热备池常备数千张卡，调度层几分钟级换人。

### 8.3 DeepSeek HAI-LLM

DeepSeek 在 V2/V3 论文和 HAI-LLM 博客里透露：

- 训练框架 HAI-LLM 深度定制，针对 MoE 路由做过大量故障容错专项；
- MoE 的特点是 **单 expert 故障不会让整个模型失效**，但路由层 any2any 通信里任一环挂掉都会阻塞。他们做了 expert-replica + routing bypass。
- 在 V3 训练中报告了 “平均每两天一次的大中断 + 分钟级恢复” 的实操经验。

### 8.4 国内其他：Qwen、豆包、盘古

阿里 Qwen 团队在 PAI-DLC 平台上跑，依赖 PAI 的任务级 elastic（故障自动替换 + 按 rank 重启）；字节豆包大模型团队公开披露过用”in-memory checkpoint + cross-datacenter 异步对象存储”；华为盘古在昇腾上自研了 MindSpore + ModelArts 的容错栈，checkpoint 格式绑定 HCCL 拓扑。

## 九、慢节点（straggler）：没挂，但拖垮大家

Straggler 的特征是”没崩”——但只要有一颗卡每步慢 200 ms，同步的集合通信会让整个集群跟着等 200 ms。万卡等一颗卡，代价巨大。

常见原因：

- 单卡 HBM 退化，自动降频；
- NVLink 丢链路但未达到整卡下线阈值；
- PCIe Correctable Error 风暴；
- 宿主机上有噪声邻居（不该在训练节点上跑的 daemon）；
- 数据加载 I/O 偶发性慢。

工程对策：

1. **P99 step time per rank** 打 metric，5 分钟滑窗判定；
2. 判定后**直接从作业里踢出**该节点（依赖 elastic），用热备顶；
3. 如果是 HBM 老化，下线送修；如果是软件问题，发到平台组的分诊队列。

Meta 披露他们在 LLaMA-3 训练里自动化踢掉了”几十个 straggler”，每踢一个集群 tput 回升 1%–3%，累计十几个点的 effective throughput。

## 十、loss spike：保留多 checkpoint、回滚、跳 batch

loss spike 不是硬件故障，但后果一样严重——一次发散能把几小时训练打飞。工业界的共识做法：

- **保留最近 K 个 checkpoint**（K=5–10），不是只留最新。
- loss 发散时，从 spike 前 2–3 个 checkpoint 回滚。
- **跳过 bad batch**：记录发散时的 data iterator 位置和 batch seed，回滚后 skip 该 batch，或者把该 batch 强行 clip 梯度。
- 监控 grad norm 的分布，提前设置 grad clip 阈值（常用 1.0），大多数 spike 会被 clip 住。
- 有些团队（如 DeepSeek、Qwen）在训练里加 `z-loss` 或输出 logit clamp，显著压低 spike 频率。

## 十一、全链路图解：故障恢复与健康检查

### 11.1 故障与恢复时间线

![一张图看故障 + 恢复时间线](https://quant67.com/post/llm-infra/10-checkpoint-fault/images/10-checkpoint-fault-fig1.svg)

### 11.2 健康检查流程

## 十二、落地清单（Checklist）

一套能”抗万卡”的 checkpoint & 容错栈应该具备：

- 分布式 checkpoint（按 rank 分片，拓扑元信息分离，DCP 风格）；
- 异步写盘（主 stream 只做 CPU pinned copy，后台线程/进程写盘）；
- 本地 NVMe staging + 并行文件系统主存 + 对象存储冷备 三层；
- 每 100–500 steps 一次 checkpoint，保留 K=5–10 份；
- 启动前 NCCL 健康检查，不过则踢；
- NCCL timeout 2–5 分钟 + watchdog step-time 监控；
- `dcgm-exporter` + Prometheus 告警；
- 热备节点池（2%–5% 容量），镜像预热；
- Elastic / in-place replacement 支持（Torch Elastic / 自研）；
- Straggler 自动识别 + 踢出；
- SDC 采样重复计算对比；
- loss/grad 异常自动快照 + 人工复核流程；
- checkpoint 跨 region 异步归档 + 完整性校验（哈希）。

做到这套，万卡训练能把”实际有效训练时间 / 墙钟时间”做到 90%+；做不到，就是 60%–70% 甚至更低——这里面就是几千万美元的差距。

## 十三、深入：Checkpoint 格式与序列化的工程坑

### 14.1 Pickle、safetensors、zarr、自研二进制

早期 PyTorch 训练全栈基本都是 `torch.save` 一把梭，底层是 Python `pickle`。到了大模型时代，pickle 的几个弱点被放大：

1. **安全问题**：pickle 允许反序列化出任意对象，Hugging Face 上就发生过数次被植入恶意代码的”后门 checkpoint”事件。safetensors 由此诞生——只存 tensor 数据和元信息（JSON header + 连续 byte blob），**没有代码执行路径**。
2. **随机 I/O 不友好**：pickle 是流式的，想只读取某一层必须从头 parse。safetensors 的 header 里直接记录每个 tensor 的 byte offset 和 length，支持 mmap + 零拷贝加载。这对万卡场景非常重要——每个 rank 只加载自己那一份分片时，不希望把整个文件都读进来。
3. **多语言互操作**：pickle 是 Python 独占的；safetensors 在 Rust 里有一等公民实现，Triton Inference Server、vLLM、TGI 都能直接读。

safetensors 已经是推理世界的事实标准。但**训练 checkpoint**（带优化器状态、LR scheduler、RNG、step 等）通常比推理 checkpoint 复杂得多，社区还没有完全统一。主流选择：

- **PyTorch DCP**：自研二进制格式，每个 rank 一个 `.distcp` 文件 + 一个全局 `.metadata`。Meta 内部就在用这个；也是未来 PyTorch 官方方向。
- **DeepSpeed `universal checkpoint`**：支持在不同 ZeRO stage / TP / PP 拓扑间 reshard。
- **Megatron `distributed_checkpoint`**：类似 DCP，针对 TP/PP 拓扑做了优化。
- **自研**：Meta 的 Bellow、字节 veOmni 的 checkpoint 层、DeepSeek HAI-LLM 的 ckpt 模块都是自家重写的。

### 14.2 写入路径里的几个”看不见的坑”

踩过万卡作业的人会共鸣这些：

- **filesystem metadata 压力**：一次全量 checkpoint 如果每个 rank 一个文件，16K rank 就是 16K 个文件；加上优化器、一层一层的切分，实际可能几十万个小文件。Lustre 的 MDS（metadata server）经常被打爆。对策：按 rank group 聚合，或者 `single_file_per_rank` 用大文件。
- **fsync 成本**：把数据推到 NVMe 是一回事，保证断电不丢是另一回事。`fsync` 一个几百 GB 的文件要十几秒；多数实现会在最外层 barrier 前只做一次全局 fsync。
- **pinned memory 不够用**：启用 CPU offload 异步 checkpoint 时，需要的 pinned memory = checkpoint size / DP world size。一个 405B 模型 DP=128，每个 rank pinned buffer ≈ 50 GB。节点如果总共就 1 TB DRAM，这就挤占得很紧，要预先 `torch.cuda.memory.set_per_process_memory_fraction` 并预留足够大的 pinned pool。
- **写放大**：很多并行文件系统的 stripe size 不对时，1 MB 的小 I/O 会打成若干个 4 MB 的 OST 写，实际带宽只能吃到标称的 30%。要针对 Lustre 的 `lfs setstripe -c -1 -S 4M` 做作业级调优。
- **对象存储 multipart**：上 S3/OSS 的 checkpoint 单文件通常 100 GB+，必须 multipart upload；part size 推荐 64 MB–512 MB，并发度 8–32；遇到 5xx 要指数退避重试，否则一个瞬时抖动就废了。

### 14.3 checkpoint 的正确性：完整性校验与幂等

一个惨痛教训是：“checkpoint 写成功了” ≠ “checkpoint 可以恢复”。常见翻车：

- 写到一半作业被 OOM kill，产生了**不完整但看起来存在**的 checkpoint 目录；
- PFS 客户端 cache 没 flush，某几个 rank 的文件在 PFS 上还没真正落盘就被覆盖；
- 对象存储的 multipart upload 成功了一半，`CompleteMultipartUpload` 失败；
- 两个作业并发写同一路径（比如重启后旧 job 还没死透）造成交错。

生产上的做法：

1. **写入走临时目录，rename 原子提交**：`path.tmp-<uuid>` → 全部完成 → `rename` 成 `step-XXXXXXXXX`。rename 在大多数 POSIX FS 上是原子的。
2. **记录 manifest**：checkpoint 目录里放一个 `manifest.json`，列每个 shard 文件的路径、字节数、sha256。恢复时先校验 manifest。
3. **多 checkpoint 链式保留**：`latest` 是个软链或游标文件，只有新 checkpoint 完全写入并校验后才更新。
4. **幂等恢复**：恢复脚本对同一 step 多次运行结果应一致（这条对弹性场景特别重要，一个节点重启了可能触发多次 load）。

## 十四、一个真实的事故回放

不妨用一个综合案例把前面的概念串起来。以下是基于公开披露和笔者所了解的几个大厂故事综合、简化后的场景，**纯属示例**，不对应任何具体公司。

### 15.1 背景

- 10K H100，3D 并行 TP=8 PP=16 DP=80；
- 训练一个 200B dense 模型，global batch = 16M tokens；
- checkpoint 每 300 step、异步、三层存储；
- 热备池 300 张卡。

### 15.2 事故时间线

**T+0**：作业跑到 step 87,500，一切正常，step time ~4.2 秒。

**T+12s**：节点 `h100-pod3-r14` 上的 rank 1,784 收到 CUDA Xid 63（unrecoverable ECC）。进程立即 abort，相邻 7 个同主机 rank 跟着退出。

**T+14s**：其他 rank 在下一次 NCCL 集合通信上开始阻塞。这里有个细节——**默认 NCCL timeout 30 分钟**，如果没改，集群会干等半小时。

**T+90s**：因为启用了 `NCCL_ASYNC_ERROR_HANDLING=1` 加上自研 watchdog（NCCL 超时阈值调到 90 秒），所有 rank 被统一 abort，作业整体退出 code 137。

**T+105s**：k8s Operator 检测到 Pod 退出，触发自动重启流程。前置动作： - 从热备池申请 1 个 8-GPU 节点替换挂掉的 `h100-pod3-r14`； - 热备节点拉起 pod（镜像本地有，0 拉取时间）； - 新节点跑 60 秒 NCCL 健康检查——通过。

**T+3m**：所有 rank 重新调度到位，开始加载 checkpoint step 87,300（距离故障点丢 200 step，约 13 分钟有效训练）。 - 每个 rank 从本地 NVMe 找到 last-known-good 的 checkpoint——命中（因为有后台预热）； - 不命中的几台从 Lustre 并发读，P99 读完时间 45 秒。

**T+4m20s**：NCCL communicator 重建，第一次 all-reduce 通过，训练恢复。

**T+5m**：前 5 个 step 属于 warmup（torch.compile cache 重建、PP bubble 没填满），step time 6 秒；之后回到 4.2 秒稳态。

**净损失**：5 分钟墙钟 + 200 step（~13 分钟）训练进度 ≈ 18 分钟。对比”没做容错工程”的场景（NCCL 30 分钟 timeout + 人肉拉新节点 + 镜像冷启动 + 全量从对象存储拉 checkpoint），同样故障可能要 2–3 小时才能恢复。

### 15.3 事后 RCA

- 挂掉的节点走流程送修，板厂诊断是某颗 HBM 堆叠颗粒永久故障；
- 工单里记录”该节点上周已经出现过 2 次可纠正 ECC，DCGM 告警级别 WARN”——如果告警策略更激进一点，可以在周级别主动 drain，完全避免这次中断；
- 告警规则调整：单节点 HBM SBE 周累计 >500 次 → 自动 drain。

这是万卡运维团队每天在做的事。

## 十五、不同规模下的容错策略差异

不同作业规模的”经济最优”容错姿势差别很大，不能一招吃遍天：

  
|规模|MTBF 估计|建议策略|
|---|---|---|
|单节点 8 卡|数周|同步 checkpoint，每 30 min，保留 3 份足矣|
|64–256 卡|数天|异步 checkpoint + DCP；Torch Elastic 就够|
|1K–4K 卡|1 天–数小时|异步 + 三层存储 + 热备池 + 启动健康检查|
|10K+ 卡|小时级|上述全套 + SDC 检测 + straggler 自动驱逐 + 专职 SRE 7×24|
|50K+ 卡|分钟级|+ in-memory checkpoint + 流水线 stage 重启 + 跨 pod 故障域设计|

小作业过度工程纯属浪费人力；大作业省这些工程，每年烧掉的 GPU 时长换成工程师工资够养整个团队。

## 十六、与训练框架的集成点

### 17.1 Megatron-LM

```
torchrun --nproc_per_node 8 --nnodes $NNODES pretrain_gpt.py \
    --tensor-model-parallel-size 8 \
    --pipeline-model-parallel-size 16 \
    --distributed-optimizer \
    --use-distributed-optimizer \
    --save-interval 300 \
    --save /mnt/pfs/ckpt/llm \
    --load /mnt/pfs/ckpt/llm \
    --async-save \
    --ckpt-format torch_dist \
    --ckpt-assume-constant-structure \
    --no-load-optim-on-reshard false
```

关键点： - `--ckpt-format torch_dist` 用 DCP 格式，支持 reshard； - `--async-save` 开启异步； - `--ckpt-assume-constant-structure` 优化：同一作业内拓扑/层结构不变，metadata 可复用。

### 17.2 DeepSpeed

```
engine.save_checkpoint(
    save_dir="/mnt/pfs/ckpt/llm",
    tag=f"step-{step:09d}",
    client_state={"data_iter_state": dl.state_dict()},
    save_latest=True,
    exclude_frozen_parameters=False,
)
# async
engine.save_checkpoint(..., non_blocking=True)
```

ZeRO-3 下每个 DP rank 只写自己那份参数+优化器分片。`universal_checkpoint` 支持从 ZeRO-3 导成”拓扑无关”格式，再加载回不同并行度。

### 17.3 PyTorch FSDP + DCP

上文已有代码示例。要强调的点：`get_state_dict(..., StateDictOptions(cpu_offload=True))` 搭配 `dcp.async_save` 是 PyTorch 2.4+ 上的推荐范式。FSDP2 结合 DTensor 对 DCP 的原生无缝支持，是当下解决万卡 checkpoint 拓扑变换的最佳实践，这也使得 DCP 的 reshard 逻辑更干净。

### 17.4 JAX / T5X / MaxText

Google 栈里 checkpoint 走 Orbax，和 GCS 深度整合。默认 async + `AsyncCheckpointer` + multi-host barrier。T5X / MaxText 里训练配置中直接一行 `checkpoint_period = 300` 就够。Pax / Pathways 在超大规模下做了跨 pod 的 checkpoint 聚合。

## 十七、容灾：不只是”训练能恢复”

到万卡规模，还有一类容灾是”整个 pod / 数据中心挂掉”。典型场景： - 某个可用区电力跳闸； - 大面积网络故障把该 zone 与控制面隔离； - 机房级事故（火灾、水淹）。

对应的容灾手段： - **跨 AZ 异步复制 checkpoint**：每 N 个小时把最新 checkpoint 推到另一个 region 的对象存储； - **跨 pod 训练**（少数团队尝试过，xAI、Google 有公开的跨数据中心训练设计）：把 DP 维度跨 pod 铺开，中间用高速专线；pod 间故障不致命； - **训练数据、代码、镜像异地备份**：这条看起来 trivial，但每年都有人因为数据只在一个桶里丢过。

## 十八、安全与合规维度

Checkpoint 本身就是模型，是受控资产。落到生产上通常要考虑：

- **加密**：对象存储侧 SSE-KMS；某些场景（政务、金融）要求传输也是 mTLS + 存储侧客户主密钥。
- **审计**：谁在什么时候读了/拷贝了哪份 checkpoint。
- **保留策略**：很多公司约定”最终模型上线后，训练中间 checkpoint 保留 90 天后删除”，一方面省存储，一方面降低数据泄露面。
- **跨境**：如果训练数据或 checkpoint 包含境外用户数据，跨境传输受出海合规约束。

这些看起来不像”训练工程”，但真正的生产训练平台必须考虑。

## 十九、监控看板：一眼看出集群是否健康

容错工程落到每天的运维上，就是一块”训练作业 + 集群健康”综合看板。下面列出一组在业界被反复验证有效的关键指标，分四个面板：

### 24.1 作业层面板（Job Health）

- **Step time P50 / P99 / max**（折线图）：实际 step time 与预期 step time 的比值；预期值由模型大小、并行度、batch size 推算得到。
- **Tokens per second per GPU**：归一化后的”每卡有效吞吐”，用于横向比较不同作业/不同拓扑。
- **Effective training ratio**：过去 24 小时内，实际训练墙钟时间 / 总墙钟时间。业界优秀水位 > 90%。
- **Loss / Grad norm**：主指标，带告警（NaN、偏离滑窗 P99 的 3σ）。
- **Last checkpoint step / age**：最新成功落盘的 checkpoint 步数与距今时间；超过 2× 预期间隔要告警。
- **Pending save queue**：异步 checkpoint 未完成写盘的个数；持续 > 1 意味着存储压力过大，需要扩容或调节频率。

### 24.2 GPU / 节点层面板（Hardware Health）

- 每 GPU 的 SM 利用率、HBM 利用率、NVLink 流量；
- Xid 错误计数（按错误码分类）；
- HBM row-remap 次数、可纠正/不可纠正 ECC 次数；
- 温度、功耗、风扇转速；
- NVLink 链路 state（up / degraded / down）。

这些都来自 `dcgm-exporter`，打到 Prometheus 后按”节点”和”卡”两个维度做 heatmap 最直观——一眼能看出某个机柜整排变红。

### 24.3 网络层面板（Network Health）

- IB / RoCE 每 NIC 的吞吐、PFC pause frame 数、符号错误计数；
- NCCL 每个 comm 的 step-level 带宽（需要 PyTorch NCCL flight recorder 或者自研 hook）；
- 交换机 buffer 占用（从网管 SNMP 拉）；
- 顶层 leaf-spine 链路的使用率分布（不均衡就是 hash 冲突信号）。

### 24.4 存储层面板（Storage Health）

- Lustre OSS / MDS 的 I/O 吞吐、IOPS、排队延迟；
- NVMe wear leveling（老化指标，DWPD）；
- 对象存储上传成功率、P99 延迟、失败重试率；
- Checkpoint 空间占用趋势 + 保留策略执行情况。

### 24.5 告警的分级设计

一个好的告警分级大概是：

  
|级别|条件示例|动作|
|---|---|---|
|INFO|单节点单次 SBE|记录，不告警|
|WARN|step P99 超阈值、SBE 累计、Lustre 延迟上升|通知平台组日间处理|
|ERROR|Xid 48/63/64、NCCL hang、训练 stalled 5 min|自动 drain + pager|
|CRITICAL|作业整体失败、loss NaN、checkpoint 写失败 > 3 次|pager + 立即上人|

再强调一句：**告警必须可执行**。报警满屏但没人处理、或者处理不了，比不报警还糟，因为真告警会被淹没。

### 24.6 从指标到 playbook

更成熟的团队还会把”指标 → 应对动作”沉淀成 runbook / playbook，比如：

- “IB 口 CRC 错误连续 10 分钟 > 100/s” → 自动切该卡上的 NCCL 到备用 rail → 同步通知网络组；
- “某节点 HBM SBE 24 小时 > 1000” → 标记 drain pending，等下一次 checkpoint 周期平滑替换；
- “连续 3 个 checkpoint 写盘时间 > 预期 2×” → 自动降低 checkpoint 频率 + 通知存储组扩容。

这些 playbook 一旦自动化到位，运维人力就从”救火”解放为”改进”，集群可用率会踏上另一个台阶。

## 二十、再复盘：这套东西的 ROI

很多团队初期会问：“训练成本已经很高了，再投 10% 资源做容错工程，划算吗？”

按 16K H100 集群年成本 3 亿美元算：

- **不做容错**：按行业平均 60% 有效训练时间，浪费 1.2 亿美元；
- **做到行业中位**：75%，浪费 0.75 亿美元，省 4500 万美元；
- **做到 Meta / DeepSeek 水平**：90%+，浪费 3000 万以下，省 9000 万美元；
- **额外投入**：一支 10 人的 SRE/平台团队 + 5% 热备硬件冗余 ≈ 2000 万美元。

简单算账：**每一块钱投在容错工程上，回报 4–5 倍**。这还没算”按期上线”的战略价值——一个 405B 模型晚上线 3 个月，商业上意味着什么每个团队心里都有数。

## 二十一、小结

Checkpoint 与故障容忍在 LLM 基础设施里的地位，类似于数据库的 WAL：平时不怎么被提起，但决定了这台机器是不是”生产级”。

这一篇的几个要点：

1. **万卡训练一定会断**。LLaMA-3 每 3 小时一次中断的数字是常态不是例外；到 10 万卡会更频繁。
2. **故障谱系从 HBM ECC 到 SDC 到散热**，covering everything。工程上必须有分层的检测和对策。
3. **Checkpoint 的第一性问题是”大”**（405B 几个 TB），所以必须分片 + 异步 + 三层存储。
4. **恢复时间目标是 10 分钟内**，靠热备池 + 并发读 + lazy NCCL init 达成。
5. **健康检查贯穿启动前 / 运行时 / 结束后**，NCCL 打桩、step-time watchdog、SDC 采样对比是三件套。
6. **容错范式以 Checkpoint+Restart 为主，Elastic / in-place 为辅**，真正在 3D 并行下弹性扩缩容仍然是难题。
7. **Straggler 和 loss spike 是”没崩但拖垮”的隐性杀手**，自动化识别 + 果断踢出是标准动作。
8. **经济上的 ROI 非常高**，这是”必须投入”的基础工程，而不是”有条件再做”的加分项。

## 二十二、延伸阅读路线图

如果这一篇让你想继续深挖，可以按下面的路径继续：

**硬件与 telemetry**

- Nvidia DCGM 手册：理解每一个 GPU health 指标背后的物理含义；
- SMARTCTL / ib_diag 的手册：硬盘和 IB 的故障模型；
- 阅读 Google《The Tail at Scale》（2013）：straggler 问题的经典论文，搬到 GPU 集群完全适用。

**Checkpoint 学术**

- Check-N-Run（NSDI ’22）：Meta 在推荐模型训练里的 checkpoint 系统；
- CheckFreq（FAST ’21）：动态调节 checkpoint 频率；
- Gemini（SOSP ’23）：in-memory checkpoint 代表作；
- Bamboo（NSDI ’23）：抢占式训练下的 checkpoint 设计。

**SDC 与可靠性**

- Meta《Silent Data Corruptions at Scale》（2021）：CPU 侧 SDC 的首次大规模数据；
- Google《Cores that don’t count》（HotOS ’21）：类似主题的姊妹篇；
- 关注 Nvidia GTC 每年的 “Reliability in AI” session。

**工业实践**

- Meta LLaMA-3 技术报告 §5 Training Infrastructure；
- DeepSeek-V3 技术报告里关于 HAI-LLM 的 §Training Framework；
- xAI 工程师在 Hot Chips / SIGCOMM 的公开分享；
- 国内阿里 PAI、火山 veMLP、百度千帆的公开技术博客。

## 二十三、常见 FAQ

**Q1：checkpoint 多久一次最合适？**

经验区间：**每 15–30 分钟 / 100–500 step 一次**。更高的频率不会明显降低期望损失（损失 ≈ checkpoint 间隔 / 2），但会增加存储压力和管理复杂度；更低的频率会让每次故障成本显著上升。推荐做法：按”期望每次故障损失 < 15 分钟训练”来反推频率。

**Q2：需要保留多少份历史 checkpoint？**

主链 5 份、每周 1 份永久、每个里程碑（end of pretrain、mid-training eval 节点）永久。主链用来抗 loss spike（一般回滚 2–3 份就够）；每周那份是真出事了要”回到几天前某状态”时用的保险。

**Q3：checkpoint 格式在 TP/PP 改变后能加载吗？**

- Megatron 旧格式（`torch`）：不行，需要 reshard 工具；
- Megatron `torch_dist` / PyTorch DCP：可以自动 reshard；
- DeepSpeed universal ckpt：可以，中间有一步转换；
- HuggingFace safetensors（通常是全量，不含优化器）：推理端加载随意，训练端要重建优化器状态。

**Q4：可以跨硬件平台（H100 → MI300、NVIDIA → 昇腾）加载 checkpoint 吗？**

参数本身是 fp16/bf16 数值，平台无关；但优化器 state 里可能有平台特有的常量精度差异。更大的坑是**模型实现本身**——同一份 Transformer 在不同栈里 layer 命名不一样，需要映射脚本。工业实践是”参数层面可跨，完整 optimizer state 跨平台要做 transform”。

**Q5：云厂商的”抢占式实例”能跑大模型训练吗？**

能跑小规模（单节点到几十节点），必须做**秒级 checkpoint** + **Bamboo / AntMan 式抢占保存**。万卡级训练目前基本不用抢占式——故障率太高，价格优势不足以抵消训练效率损失。

**Q6：checkpoint 本身要不要版本化、要不要跑 CI？**

大公司都会对 checkpoint 做版本化（以 git SHA + 数据版本 + 超参哈希为标签），并做”加载-推理一小步”的 CI 验证，确保产出的 checkpoint 不是废的。这个成本很小，但救命。

**Q7：训练时可以边训边 eval 吗？会不会影响 checkpoint？**

常见做法是：每 N 个 checkpoint 拉出来在独立 eval 集群上跑。不要在训练集群上原地 eval——内存布局、显存预算、随机状态都容易被污染。让 eval 作业异步消费 checkpoint 目录，结果汇回训练方的看板。

**Q8：开源社区有没有开箱即用的”容错栈”？**

目前最接近”开箱即用”的是：PyTorch DCP + TorchElastic + NCCL flight recorder + DCGM exporter + Prometheus/Grafana 看板。这套搭起来对 1K 卡以内规模够用；再往上需要自研热备池调度、straggler 驱逐、SDC 检测。Nvidia Resiliency Extension、MSFT Project Forge 是正在开源化的方向，值得关注。

## 附录：一线运维与排查速查表

### 附录 A：常见 Xid 错误速查

Nvidia 驱动在 `dmesg` 里打的 `NVRM: Xid (PCI:xxxx): <code>, ...` 是排查 GPU 故障的第一手线索。实战中最常见的几个：

   
|Xid|含义|通常原因|处置|
|---|---|---|---|
|13|Graphics Engine Exception|非法 kernel，越界访问|一般是用户代码 bug，kill 作业|
|31|GPU memory page fault|同上，HMM/UVM 地址问题|同上|
|43|Reset channel verif error|多是 kernel hang 触发 reset|观察是否反复出现|
|48|Double Bit ECC|**HBM 硬件故障**|节点 drain + 送修|
|63|Row-remapper: uncorr err|HBM 不可纠正错误|drain|
|64|Row-remapper: failure|行重映射失败|drain，送修|
|74|NVLink error|NVLink 链路问题|可先观察，持续出现则 drain|
|79|GPU fallen off the bus|PCIe 链路断开|通常机箱/主板/散热问题|
|92|High single-bit ECC rate|HBM 老化征兆|告警但可暂不 drain|
|119/120|GSP RPC timeout|新固件栈常见|升级驱动/VBIOS|

生产集群一般会把 `dmesg` 流式推到集中日志（Loki / ES），针对 Xid 关键字设规则，符合级别自动触发 drain 流程。

### 附录 B：NCCL 调参与排查清单

万卡 NCCL 行为不对时，手边这个清单经常救命：

```
# 观测环境变量
export NCCL_DEBUG=INFO
export NCCL_DEBUG_SUBSYS=COLL,INIT,NET,GRAPH
export NCCL_ASYNC_ERROR_HANDLING=1
export TORCH_NCCL_TRACE_BUFFER_SIZE=2000    # flight recorder
export TORCH_NCCL_DUMP_ON_TIMEOUT=1

# 超时
export TORCH_NCCL_HEARTBEAT_TIMEOUT_SEC=600
export NCCL_TIMEOUT=180000    # 3 分钟，按需调

# IB / RoCE
export NCCL_IB_HCA=mlx5_0,mlx5_1,mlx5_2,mlx5_3,mlx5_4,mlx5_5,mlx5_6,mlx5_7
export NCCL_IB_GID_INDEX=3
export NCCL_IB_TC=106
export NCCL_IB_SL=3

# 性能
export NCCL_ALGO=Ring,Tree
export NCCL_PROTO=Simple,LL,LL128
export NCCL_NVLS_ENABLE=1    # H100 NVLink SHARP
export NCCL_P2P_DISABLE=0
export NCCL_COLLNET_ENABLE=0  # 视拓扑
```

排查时的分层思路：

1. **Ring 算法 vs Tree 算法**：某些拓扑下 Ring 比 Tree 快一倍，或反过来；强制一个试试。
2. **逐对 P2P 测试**：用 `nccl-tests` 的 `p2pBandwidthLatencyTest` 看是不是某两颗卡之间的 NVLink 降级。
3. **按 rail 拆分**：万卡一般 8 rail（每台 8 NIC），如果 rail-aware 路由没配好，会产生 hotspot。`NCCL_TOPO_FILE` 可以指定手写拓扑。
4. **`torch.distributed.elastic` rendezvous 失败**：多数是域名/DNS 问题，或者 `MASTER_ADDR` 选了个奇怪的接口。

### 附录 C：一个简化版的作业级 watchdog

下面给一个最小可用的 step-time watchdog，生产里可以扩展为和 Prometheus、调度器对接的 sidecar。

```
# watchdog.py
import time, signal, os
from collections import deque

class StepWatchdog:
    def __init__(self, window: int = 50, slow_factor: float = 1.5,
                 stall_sec: float = 180.0):
        self.times = deque(maxlen=window)
        self.slow_factor = slow_factor
        self.stall_sec = stall_sec
        self.last_tick = time.time()

    def tick(self, step: int):
        now = time.time()
        dt = now - self.last_tick
        self.last_tick = now
        self.times.append(dt)
        if len(self.times) == self.times.maxlen:
            median = sorted(self.times)[len(self.times) // 2]
            if dt > median * self.slow_factor:
                self._warn(step, dt, median)

    def stall_check(self):
        """在独立线程中周期性调用，检测 step 是否卡住。"""
        if time.time() - self.last_tick > self.stall_sec:
            self._panic()

    def _warn(self, step, dt, median):
        print(f"[watchdog] slow step {step}: {dt:.2f}s vs median {median:.2f}s")

    def _panic(self):
        print("[watchdog] stalled >{:.0f}s, aborting".format(self.stall_sec))
        os.kill(os.getpid(), signal.SIGTERM)
```

实际项目里建议： - 把 `tick` 的数值打到 Prometheus，每个 rank 一条； - 在 rank-0 聚合，做跨 rank 的离群检测（例如某 rank P99 比全局 median 慢 1.5×）； - panic 前先尝试 dump stack（`py-spy`、`gstack`），方便事后 RCA。

### 附录 D：一个”checkpoint 预算”测算工具

很多团队没精确估算过 checkpoint 的时间预算，这里给一个简易公式和代码：

其中 是单 rank checkpoint 大小， 是节点本地 NVMe 写带宽， 是节点到 PFS 的有效网络带宽（典型 200 Gbps ≈ 25 GB/s）， 是每节点 rank 数（一般 8）。

```
# ckpt_budget.py
def ckpt_time(total_params: float, bytes_per_param: int = 16,
              dp: int = 128, ranks_per_host: int = 8,
              nvme_gbs: float = 6.0, net_gbs: float = 25.0,
              meta_overhead_s: float = 2.0) -> dict:
    total_bytes = total_params * bytes_per_param
    per_rank_bytes = total_bytes / dp
    per_rank_gb = per_rank_bytes / 1e9
    t_nvme = per_rank_gb / nvme_gbs
    t_net = per_rank_gb / (net_gbs / ranks_per_host)
    t_total = max(t_nvme, t_net) + meta_overhead_s
    return dict(per_rank_gb=per_rank_gb,
                t_nvme=t_nvme, t_net=t_net,
                t_total_sync=t_total,
                t_async_visible=meta_overhead_s + per_rank_gb / nvme_gbs * 0.1)

if __name__ == "__main__":
    print(ckpt_time(total_params=405e9, dp=128))
```

跑出来对 405B / DP=128 单 rank ≈ 50 GB，同步 checkpoint 墙钟 8–10 秒，异步只暴露 ~1 秒给训练。这种测算在上 10K+ 卡作业前一定要过一遍。

## 总结论

### 写在最后

从 GPT-3 时代起，“把万卡开起来跑”就是个非平凡工程；到了 10 万卡规模，**容错本身变成训练的第一性制约**。有一句业内半开玩笑的话：

> “在万卡训练里，你不是在训练一个模型，而是在维护一个高频故障的分布式系统，顺便做了一下反向传播。”

这个观察放在 2026 年依然成立。当模型继续从 405B 走向 1T、10T，训练窗口从 54 天走向 200 天，每一次故障的代价、每一分钟恢复时间的价值，都会继续以指数级放大。这也是为什么顶尖团队会把相当一部分工程精力从”算法”分流到”基础设施容错”——算法决定上限，容错决定能不能跑到那个上限。

希望这一篇给到你足够具体、能直接用于立项和落地的工程信息。下一篇我们切换赛道，从训练走到推理：[推理引擎基础](https://quant67.com/post/llm-infra/11-inference-basics/11-inference-basics.html)，讨论 prefill / decode 的计算特性、KV cache 的内存账本、以及为什么推理需要完全不同的一套系统架构。

### 额外话题：把容错当成产品

最后再留一个思考：很多公司把”容错”当成纯内部工程，做得再好也不对外。但近两年出现了一个新趋势——**把训练容错做成 PaaS / MaaS 的一个卖点**：

- **Anyscale / Ray Train**：把弹性调度和 checkpoint 管理标准化成 SaaS；
- **Nvidia DGX Cloud + Run:ai**：托管训练 + 故障自动恢复 + SLA；
- **阿里 PAI-DLC**、**火山 veMLP**、**百度千帆训练平台**：都打”训练作业 SLA”牌，容错能力作为差异化；
- **AWS SageMaker HyperPod**、**Azure AI Foundry**、**GCP Vertex Training**：同上。

对选型的启示：**如果你的团队不是顶级 infra 背景、训练规模不是最头部，那”买”比”造”很可能是更理性的选择**。真正的自研容错栈要吃下数以万计的故障案例才能成熟，这是金钱换不来的时间。

当然，如果你是头部团队或者有特殊需求（国产替代、自主可控、极致成本），那自研依然值得。但”我们能不能做”和”我们应不应该做”是两个问题。

### 一句话总结

> **万卡训练的世界里，不挂掉不是目标；挂掉后 10 分钟内回来才是。**

---

**上一篇**：[RLHF 与对齐流水线](https://quant67.com/post/llm-infra/09-rlhf-pipeline/09-rlhf-pipeline.html) **下一篇**：[推理引擎基础](https://quant67.com/post/llm-infra/11-inference-basics/11-inference-basics.html)

## 参考资料

1. Meta AI. _The Llama 3 Herd of Models_. 2024. [https://ai.meta.com/research/publications/the-llama-3-herd-of-models/](https://ai.meta.com/research/publications/the-llama-3-herd-of-models/)
2. PyTorch. _Distributed Checkpoint (DCP)_ documentation. [https://pytorch.org/docs/stable/distributed.checkpoint.html](https://pytorch.org/docs/stable/distributed.checkpoint.html)
3. DeepSpeed team. _Universal Checkpointing & Async Checkpoint_. [https://www.deepspeed.ai/](https://www.deepspeed.ai/)
4. NVIDIA Megatron-LM. _Async save / distributed optimizer_. [https://github.com/NVIDIA/Megatron-LM](https://github.com/NVIDIA/Megatron-LM)
5. NVIDIA. _Resiliency in Large-Scale Training_ (Nemotron). [https://developer.nvidia.com/blog/](https://developer.nvidia.com/blog/)
6. Microsoft. _Project Forge / Resiliency for AI training_. MSR blog.
7. Wang et al. _Gemini: Fast Failure Recovery in Distributed Training with In-Memory Checkpoints_. SOSP 2023.
8. Meta. _Check-N-Run: A Checkpointing System for Training Deep Learning Recommendation Models_. NSDI 2022.
9. Dixit et al. _Silent Data Corruptions at Scale_. Meta, 2021.
10. Hochschild et al. _Cores that don’t count_. Google, HotOS 2021.
11. DeepSeek. _DeepSeek-V3 Technical Report_. 2024.
12. xAI. _Colossus cluster_ 公开分享（2024 Hot Chips / 媒体报道）。
13. NVIDIA DCGM. _Data Center GPU Manager_ docs. [https://docs.nvidia.com/datacenter/dcgm/](https://docs.nvidia.com/datacenter/dcgm/)
14. NCCL Tests. [https://github.com/NVIDIA/nccl-tests](https://github.com/NVIDIA/nccl-tests)
15. PyTorch Elastic. [https://pytorch.org/docs/stable/distributed.elastic.html](https://pytorch.org/docs/stable/distributed.elastic.html)
16. Mohan et al. _CheckFreq: Frequent, Fine-Grained DNN Checkpointing_. FAST 2021.
17. Thorpe et al. _Bamboo: Making Preemptible Instances Resilient for Affordable Training of Large DNNs_. NSDI 2023.
18. HuggingFace. _safetensors_ repository. [https://github.com/huggingface/safetensors](https://github.com/huggingface/safetensors)
19. 阿里云 PAI 团队技术博客：训练作业弹性与容错实践。
20. 字节跳动 ByteDance 团队：Gemini / veOmni / HAI-Engine 相关公开分享。
21. Dean & Barroso. _The Tail at Scale_. CACM 2013.
22. Orbax (JAX checkpoint library). [https://github.com/google/orbax](https://github.com/google/orbax)
23. 华为昇腾 MindSpore 分布式训练容错文档。

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

### [【大模型基础设施工程】07：Megatron-LM 与 DeepSpeed](https://quant67.com/post/llm-infra/07-megatron-deepspeed/07-megatron-deepspeed.html)

开源训练框架双雄对比，覆盖 Megatron-LM、DeepSpeed、FSDP2、torchtitan、Colossal-AI，含选型与工程实操。