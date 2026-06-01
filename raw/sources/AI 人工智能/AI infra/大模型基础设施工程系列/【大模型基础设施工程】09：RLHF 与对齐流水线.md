> 本文是【大模型基础设施工程】系列第 9 篇。前一篇《MoE 训练工程》聚焦稀疏专家的并行切分与 all-to-all 通信；本篇进入**对齐（alignment）**的世界——从 SFT、奖励模型到 PPO / DPO / GRPO，再到 2024–2025 年以 OpenAI o1、DeepSeek-R1、Kimi K1.5 为代表的 **RL-for-Reasoning** 新范式。对齐不再只是”让模型说人话”，而是直接决定模型**能不能推理、敢不敢拒绝、会不会谄媚**。

## 一、为什么需要对齐流水线

预训练出来的 base model 是一个”补全机”：给它一段文本，它预测下一个 token。它不会主动回答问题、不会遵守安全边界、也不会区分”有用答案”和”可能的答案”。把 base 模型变成 ChatGPT / Claude / 豆包这样的助手，需要一条完整的**对齐流水线（alignment pipeline）**：

1. **SFT（Supervised Fine-Tuning，监督微调）**：用高质量问答 / 指令对把 base 调成”会聊天”。
2. **Reward Modeling（奖励模型）**：用人类偏好数据训练一个能给回答打分的模型。
3. **RL（强化学习）**：用 RM 作为奖励信号，用 PPO / DPO / GRPO 等算法进一步优化策略模型。

InstructGPT（OpenAI，2022）第一次把这三段完整串起来，证明了 1.3B 的 RLHF 模型在人类偏好上能**击败 175B 的 GPT-3**。从此”SFT → RM → PPO”成为工业对齐的标准三段式。到 2023 年 DPO 论文提出无 RM 的闭式优化，2024 年 DeepSeek-R1 用 GRPO 跑出开源推理 SOTA，这条流水线仍在快速演化。

---

## 二、对齐全景与阶段定位

### 2.1 三阶段流水线

- **SFT 决定能力上限的格式**：模型是否会用工具、是否输出 JSON、是否走 think/answer 分段，全看 SFT 数据。
- **RM / DPO 决定偏好**：同一份回答，人更喜欢哪一种？简洁还是详尽？中立还是有观点？
- **RL 阶段决定”自由度内的最优”**：在 SFT 的分布附近做更细的策略搜索，不能偏离太远（靠 KL 散度约束）。

### 2.2 本篇 SVG 全景

> **读图导航**：上方的流程图展示了对齐范式的演变途径。最上方路径即传统的 “SFT → RM → PPO” 路线，需要三个阶段模型参与；中间路径表示 DPO（2023）及后续的 ORPO/SimPO 等基于离线偏好数据的简化方法；下方路径则通向以 RL 为主导的高维探索（如 o1、R1 等推理模型），不再强依赖 RM 打分，而是通过”规则或可验证奖励”作为监督。右下角的回环则代表持续的数据收集和红队（Red Team）评测体系。

![本篇 SVG 全景](https://quant67.com/post/llm-infra/09-rlhf-pipeline/images/09-rlhf-pipeline-fig1.svg)

---

## 三、SFT：对齐的起点

### 3.1 SFT 做什么

SFT 的本质是在”指令 → 回答”的条件分布上做标准的交叉熵训练。数据形如：

```
{
  "messages": [
    {"role": "system", "content": "你是一个助人、诚实、无害的助手。"},
    {"role": "user", "content": "用 Python 写一个快排"},
    {"role": "assistant", "content": "```python\ndef quicksort(arr): ..."}
  ]
}
```

SFT 阶段的几个工程要点：

- **损失只算在 assistant token 上**：user / system 部分的 label 设为 `-100`，否则模型会学会”模仿用户提问”。
- **多轮拼接**：一条多轮对话通常不拆成多条样本，而是整体一次前向，逐回合屏蔽 loss。
- **长度分布**：指令数据常常在几百到几千 token，packing（多条短样本拼到 8k / 32k 一条）能显著提升 GPU 利用率。

### 3.2 Chat Template：被低估的工程细节

现代开源模型都有自己的 chat template（Jinja2 格式），它决定了 system / user / assistant / tool 的分隔符。常见格式：

```
# Llama 3
<|begin_of_text|><|start_header_id|>system<|end_header_id|>
你是助手<|eot_id|><|start_header_id|>user<|end_header_id|>
...

# Qwen2 / Qwen3
<|im_start|>system
你是助手<|im_end|>
<|im_start|>user
...<|im_end|>
<|im_start|>assistant

# DeepSeek-R1（含 thinking）
<｜begin▁of▁sentence｜><｜User｜>...<｜Assistant｜><think>
推理过程
</think>
最终答案
```

**坑点**：

1. SFT 训练用 template A、推理时用 template B，性能断崖式下跌——必须保证训练与部署 tokenizer 版本一致。
2. Qwen3、DeepSeek-R1 引入 `<think>` / `</think>` 标签，训练时要确保这些是**单 token**（加入 special tokens），否则会被拆成多 token，学习效率低。
3. Tool call 格式（OpenAI function calling、Qwen 的 `<tool_call>` XML、Llama 的 `<|python_tag|>`）差异极大，跨模型迁移时必须重新设计模板。

### 3.3 指令数据来源

   
|来源|规模|特点|代表|
|---|---|---|---|
|人工编写|10k–100k|质量最高、成本最高|OpenAI 内部、Anthropic HH|
|模型蒸馏|100k–10M|用 GPT-4 / Claude 生成|Alpaca、WizardLM、OpenHermes|
|开源合集|1M+|质量参差|OpenOrca、UltraChat、Magpie|
|领域数据|变|代码 / 数学 / 医学等|CodeAlpaca、MetaMathQA|
|拒绝采样|变|自举生成 + RM 过滤|Llama 2 / 3、DeepSeek-R1 cold start|

2024 年之后主流做法是 **“大规模 + 严筛”**：生成 10× 量的候选数据，再用打分模型 / 规则 / 去重留下 Top-k。

---

## 四、奖励模型（Reward Model）

### 4.1 Bradley-Terry 偏好建模

给定 prompt 和两个回答 （被选中的）和 （被拒的），RM 输出标量分数。Bradley-Terry 模型假设人选 的概率为：

训练损失是二元交叉熵：

工程上的 RM 实现很简单：在 SFT 模型最后一层挂一个 scalar head（Linear → 1），只取最后一个 token 的 logit 作为分数。

### 4.2 InstructGPT 与 HH-RLHF

- **InstructGPT（OpenAI，2022）**：40 名标注员、约 33k prompt，人对每个 prompt 的 4–9 条回答排序，生成 对偏好对。RM 从 SFT 模型热启动、砍掉 LM head、仅训练 1 个 epoch 避免过拟合。
- **Anthropic HH-RLHF**：170k+ 条偏好对，同时收集 “helpful” 和 “harmless” 两个维度，开源在 HuggingFace `Anthropic/hh-rlhf`。是早期开源 RLHF 的事实标准数据集。

### 4.3 数据质量与 RM 陷阱

RM 是 RL 阶段的”监督信号”，一旦有偏，整个策略都会被带歪。常见陷阱：

- **长度偏见（length bias）**：标注员往往偏好更长的回答，RM 学会”越长越好”，RL 后模型疯狂凑字数。对策：在 RM 训练时加入 length penalty 正则，或者用 **SimPO / ORPO** 这类长度归一化的方法。
- **格式偏见**：带 Markdown 项目符号的答案更容易被选。
- **谄媚偏见（sycophancy）**：用户说”我觉得 2+2=5”，模型附和。根源是标注员偏好”顺着说”。Anthropic 2023 论文专门研究此现象。
- **Reward hacking**：策略学到某种触发高分但实际无用的模式，例如在末尾加 “Hope this helps!” 能稳定加 0.5 分。

### 4.4 RLAIF 与 Constitutional AI

Anthropic 提出的 **Constitutional AI（CAI）** 和 **RLAIF（RL from AI Feedback）** 用 LLM 替代人类打标注：给出一套”宪法”（如”避免输出暴力内容”），让模型自己批评、自己改写、自己生成偏好对。优点是成本低、可扩展；缺点是会放大 judge 模型自身的偏见。

2024 年主流实践是**混合 RLAIF**：人类只标注最难 / 最关键的 5–10%，其余用 GPT-4o / Claude 3.5 生成。

---

## 五、PPO：经典 RLHF 的核心算法

### 5.1 四模型架构

PPO 在对齐场景的完整数据流涉及**四个模型**：

- **Actor**：就是正在被训练的策略 LLM，通常从 SFT 模型热启动。
- **Critic**：一个 value head，估计从当前 token 到序列末尾的期望奖励，形状与 Actor 同（常共享 backbone 或独立一份）。
- **Reward Model**：冻结，给完整轨迹打分。
- **Reference Model**：冻结的 SFT 模型拷贝，用于计算 KL 惩罚 ，防止 actor 偏离 SFT 分布过远。

### 5.2 显存 3–4× 挑战

四个模型同时驻留，显存是标准 SFT 的 **3–4 倍**。以 13B 模型为例（按 bf16 参数 + bf16 梯度 + fp32 Adam 状态 `12 bytes/param` 估算）：

|模型|参数|梯度|优化器|合计|
|---|---|---|---|---|
|Actor|26 GB|26 GB|156 GB（Adam fp32）|208 GB|
|Critic|26 GB|26 GB|156 GB|208 GB|
|RM|26 GB|-|-|26 GB（仅前向激活开销）|
|Reference|26 GB|-|-|26 GB|

合计 **~468 GB**，一台 8×H100（640 GB）才能宽裕放下。工程上的常见优化：

- **LoRA Actor**：只训 LoRA，原权重共享做 reference，等价把 actor + reference 显存减半。
- **Critic 与 Actor 共享 backbone**：只多一个 value head，省 ~150 GB。
- **RM 放单独机器**：通过 gRPC/HTTP 调用，actor 集群不承载 RM 显存。OpenRLHF 的 Ray 架构就是典型。
- **ZeRO-3 + offload**：把冻结模型 offload 到 CPU 也可以（推理慢一点）。

### 5.3 KL 散度控制

PPO 在 RLHF 里最重要的 hyperparameter 就是 KL 系数 ：

- 太小 → actor 放飞自我，reward hacking，输出变乱码。
- 太大 → actor 动不了，等于白训。

两种策略：

1. **固定 KL**：，最稳。
2. **自适应 KL**（InstructGPT 原始做法）：设一个目标 KL，实际 KL 偏离时调整 。

### 5.4 PPO 伪代码

```
# 极简 PPO-RLHF 伪代码
for epoch in range(E):
    prompts = sample_batch()
    # 1. Rollout：actor 生成回答
    responses, old_logprobs = actor.generate(prompts)
    # 2. 打分
    rewards = rm(prompts, responses)                   # [B]
    ref_logprobs = ref.forward(prompts, responses)
    kl = old_logprobs - ref_logprobs                   # [B, T]
    shaped_rewards = rewards - beta * kl.sum(-1)

    values = critic(prompts, responses)                # [B, T]
    advantages, returns = gae(shaped_rewards, values)

    # 3. PPO 多步更新
    for _ in range(ppo_epochs):
        new_logprobs = actor.forward(prompts, responses)
        ratio = torch.exp(new_logprobs - old_logprobs)
        pg_loss = -torch.min(
            ratio * advantages,
            torch.clamp(ratio, 1 - eps, 1 + eps) * advantages
        ).mean()
        vf_loss = (critic(prompts, responses) - returns).pow(2).mean()
        loss = pg_loss + 0.5 * vf_loss
        loss.backward(); optimizer.step()
```

---

## 六、DPO：告别 RM 的闭式优化

### 6.1 核心思想

DPO（Direct Preference Optimization，Rafailov et al. 2023）证明了一个优雅结论：PPO 的最优策略和 reward 之间存在闭式关系，因此**可以直接在偏好数据上用类似监督学习的方式优化策略**，不再需要显式训练 RM、不再需要 actor/critic/RM/ref 四模型 rollout。

给定偏好对 ，DPO 损失：

直观理解：让”被选答案”的策略概率相对 ref 升高、“被拒答案”相对 ref 下降。

### 6.2 DPO 两模型数据流

只有 **actor + reference** 两个模型，都是 forward（reference 不需要 backward），显存和 SFT 同数量级。训练时：

- **无需 rollout**：偏好数据是离线的，一次性完成。
- **无需 RM**：直接在偏好对上训。
- **无需 critic**：不做序列级 value 估计。

### 6.3 DPO 的变体家族

  
|算法|核心改动|解决的问题|
|---|---|---|
|**IPO** (Identity PO)|用平方损失替代 logsigmoid|DPO 偏好对过度自信时会发散|
|**KTO** (Kahneman-Tversky)|只需单条回答 + 好/坏二元标签|不需成对数据，降低标注成本|
|**ORPO**|把 SFT 和偏好对齐合并成单阶段|少一个阶段，少一份 ref model|
|**SimPO**|用 length-normalized 对数似然，完全去掉 ref|进一步减少显存；抑制长度偏见|
|**RSO** (Rejection Sampling Opt)|偏好对来自 on-policy 采样|缓解 DPO 的 off-policy 问题|
|**cDPO / Robust DPO**|对噪声标注更鲁棒|真实偏好数据 label noise|

### 6.4 DPO vs PPO：怎么选

|维度|PPO|DPO|
|---|---|---|
|训练复杂度|高（4 模型 + rollout）|低（2 模型，类 SFT）|
|显存|3–4× SFT|~1.5× SFT|
|数据形式|prompt（在线 rollout）|离线偏好对|
|性能上限|更高（on-policy 探索）|受限于偏好数据分布|
|调参难度|高（KL、clip、lr 等）|低（主要就 β）|
|推理 RL|更主流（可结合可验证 reward）|可以但较弱|

**经验法则**：

- 中小公司 + 通用 Chat 对齐：**先 DPO**，简单有效。
- 推理 / 数学 / 代码任务（有可验证 reward）：**PPO / GRPO**。
- 既要 chat 又要推理：**两阶段**，SFT → DPO（chat 偏好）→ GRPO（推理 RL）。

---

## 七、GRPO：DeepSeek 的去 critic 方案

### 7.1 问题出发点

PPO 的 critic 和 actor 一样大，显存开销巨大，而且 critic 本身难训（一个标量估计要拟合长序列累积奖励）。DeepSeek 在 DeepSeekMath / DeepSeek-R1 中提出 **GRPO（Group Relative Policy Optimization）**：直接**去掉 critic**，用**组内相对奖励**做 baseline。

### 7.2 算法要点

对每个 prompt ，采样 条回答 （通常 ），得到奖励 。组内标准化后的 advantage：

策略梯度用与 PPO 相同的 clipped ratio：

其中 为 token 级策略比值，以此避免序列级 ratio 带来的方差爆炸，并将 reward 计算的 advantage 广播到每个 token。

### 7.3 REINFORCE++ 与 RLOO

除了 GRPO，业界也有同类尝试去除 Critic 的探索。例如 OpenRLHF 的 **REINFORCE++** 和 Cohere 提出的 **RLOO (REINFORCE Leave-One-Out)**，后者核心思想是将每个采样的 baseline 设置为其余 个 response 回报的平均值。这类算法用留一（Leave-One-Out）或组均值取代 Critic 预测累积奖励，是 2024 年之后大规模 RLHF 系统优化的关键分支。

### 7.3 GRPO 为什么对推理任务特别友好

- **可验证 reward**：数学题对错、代码是否通过单测——这类 reward 天然是 0/1 或稀疏浮点，不需要 RM。
- **组内对比天然对”难易”自适应**：简单题 8 条都对，advantage=0，不更新；难题有 1 条对，advantage 集中在那一条上。
- **显存省一半以上**：少了一个和 actor 同大小的 critic。

### 7.4 DeepSeek-R1 / R1-Zero

- **R1-Zero**：在 base model 上**直接 GRPO**，reward 只用”答案正确性 + 格式正确性”，没有任何 SFT。惊人的是，模型**自发学会 CoT、反思、回溯**（“aha moment”）。但语言混杂、可读性差。
- **R1**：在 R1-Zero 基础上引入**冷启动 SFT**（数千条高质量长 CoT 数据）→ 推理导向 RL → 拒绝采样 SFT → 全场景 RL，四阶段流水线产出最终模型。

R1 开源后，GRPO 成为 2025 年推理训练事实标准。

---

## 八、RL for Reasoning：o1 / R1 / K1.5 / Qwen-QwQ

### 8.1 范式转移

2024 年 9 月 OpenAI 发布 o1，宣告”**推理时也要花算力**”的新范式。核心假设：LLM 能通过**超长 CoT（几千到几万 token）**大幅提升数学、代码、科学推理能力，而长 CoT 的”思考策略”可以用 RL 训出来。

之后 2024 Q4 – 2025 Q2，推理模型井喷：

  
|模型|机构|关键技术|
|---|---|---|
|**o1 / o1-pro / o3**|OpenAI|闭源，据信 RL + test-time scaling|
|**DeepSeek-R1 / R1-Zero**|DeepSeek|GRPO + 可验证 reward，全开源权重|
|**Kimi K1.5**|月之暗面|长上下文 RL + online policy mirror descent|
|**Qwen-QwQ / Qwen3 Thinking**|阿里|推理混合模式，thinking / non-thinking 可切换|
|**豆包 1.5 Pro / Seed-Thinking**|字节|自研 veRL 框架 + 大规模 RL|
|**GLM-Zero / GLM-4.6**|智谱|推理 RL + Agent 增强|
|**Claude 3.7 / 4 Sonnet Thinking**|Anthropic|extended thinking 模式|
|**Gemini 2.5 Thinking**|Google|native multimodal reasoning|

### 8.2 可验证 reward（verifiable reward）

推理 RL 与 Chat RLHF 最大的不同：**reward 不再来自 RM，而来自确定性检验器**。

```
def math_reward(response: str, gold: str) -> float:
    # 1. 格式：必须有 <think>...</think> 和最终 \boxed{...}
    if "<think>" not in response or "</think>" not in response:
        return -0.1
    answer = extract_boxed(response)
    if answer is None:
        return 0.0
    # 2. 正确性：数值等价
    return 1.0 if math_equal(answer, gold) else 0.0

def code_reward(response: str, tests: list) -> float:
    code = extract_code_block(response)
    passed = run_tests(code, tests, timeout=10)
    return passed / len(tests)
```

好处：

- **不会 reward hacking**（至少不会在任务 metric 上 hack）。
- **信号密度高**：每个 prompt 独立给奖励，不需要偏好对。
- **成本低**：没有人类标注。

### 8.3 Kimi K1.5 的 online policy mirror descent

Kimi 技术报告强调”**长上下文 RL**”：上下文拉到 128k–1M，让模型生成超长思维链；用 **mirror descent** 风格的稳定策略更新替代 PPO 的 clipped ratio，同时去掉 critic。工程上还提出 **partial rollout**（部分回滚再继续）来重用显存。

### 8.4 Qwen3 / QwQ 的思考模式切换

Qwen3 提出 **hybrid thinking**：同一个模型通过 system prompt `think=true/false` 切换”思考”与”非思考”模式，thinking 模式下输出 `<think>...</think>` 再输出答案。训练时把两类数据混在一起，模型学会”根据任务复杂度自适应调用深思考”。

---

## 九、推理时 scaling：best-of-N 到 MCTS

### 9.1 推理时放算力的几种方式

   
|方法|做法|代价|收益|
|---|---|---|---|
|**best-of-N**|采 N 条答案，选 reward 最高|N× 推理|稳定提升|
|**self-consistency**|采 N 条，多数表决|N× 推理|数学 / 选择题有效|
|**长 CoT（o1 式）**|单条输出几千 token 思考|1× 但长|对复杂推理最有效|
|**PRM-guided search**|逐步用 PRM 打分，beam search|N×L×|更细粒度|
|**MCTS**|蒙特卡洛树搜索展开子问题|很贵|Toolformer/Agent 型任务|

### 9.2 PRM vs ORM

- **ORM（Outcome Reward Model）**：只看最终答案好坏。
- **PRM（Process Reward Model）**：对 CoT 每一步打分，能发现”过程错 + 结果偶然对”的情形。

PRM 数据昂贵（每一步都要标注），DeepSeek / OpenAI 的做法是**用蒙特卡洛展开**自动生成 PRM 监督信号：从中间某步采样 K 条到终点，用成功率估计此步的”正确概率”。

### 9.3 best-of-N 的实际工程与架构

推理服务化时 best-of-N 很常见，结合 vLLM 的 **Prefix Caching**，能在极小开销下显著提升输出水平：

核心代码形态：

```
async def best_of_n(prompt, n=8):
    # 并发采样，tempreture=0.7~1.0，共用 vLLM prefix cache
    responses = await asyncio.gather(*[
        llm.generate(prompt, sampling=SamplingParams(temperature=0.8))
        for _ in range(n)
    ])
    scores = rm.score_batch(prompt, responses)
    return responses[scores.argmax()]
```

prefix cache 让 N 条共享 prompt 的 KV，只在 decode 阶段分叉，**代价远小于 N×**。这是”训练开销大 + 推理开销可控”的重要工程支撑。

---

### 10.1 选型矩阵

   
|框架|主要算法|特点|适用规模|
|---|---|---|---|
|**TRL**（HuggingFace）|SFT/DPO/ORPO/KTO/PPO/GRPO|最通用，生态好；PPO 性能一般|≤ 30B，单 / 多卡|
|**OpenRLHF**|PPO/DPO/GRPO/REINFORCE++|Ray + vLLM + DeepSpeed；业界最常用的开源 PPO|7B ~ 70B+|
|**DeepSpeed-Chat**|端到端三阶段|微软官方；ZeRO-3 深度整合|早期 13B–66B|
|**veRL**|PPO/GRPO/DAPO|字节开源；hybrid engine（训练 + 推理同卡切换）|大规模多任务|
|**LLaMA-Factory**|SFT/DPO/ORPO/PPO|一键脚本 + WebUI；中文社区首选|≤ 70B|
|**TRLX**|PPO/ILQL|CarperAI 早期方案，现维护较少|历史遗产|
|**Nemo-Aligner**|SFT/RM/DPO/PPO|NVIDIA 官方，Megatron 底座|大规模训练|
|**Axolotl**|SFT/DPO/ORPO|yaml 配置驱动，易上手|≤ 70B|

### 10.2 典型部署架构（OpenRLHF 风格）

```
┌─────────────┐        ┌─────────────┐
│ Ray Head    │        │ vLLM Engine │  ← rollout（推理，TP=8）
│ Controller  │←──────→│   Cluster   │
└──────┬──────┘        └─────────────┘
       │
       ├──→ Actor Train（DeepSpeed ZeRO-3，8 GPU）
       ├──→ Critic Train（ZeRO-3，4 GPU）
       ├──→ RM Inference（vLLM，2 GPU）
       └──→ Ref Inference（vLLM，2 GPU）
```

**关键优化**：

- **训推分离**：rollout 用 vLLM（PagedAttention、continuous batching），训练用 DeepSpeed。每个 PPO step 结束后通过 NCCL / Gloo 把 actor 权重同步到 vLLM（增量广播）。
- **权重同步用 CUDA IPC 或 NCCL broadcast**：同机 IPC 几乎零拷贝。
- **Prompt 队列异步化**：rollout 与 train 双 buffer 并行。

### 10.3 veRL 的 Hybrid Engine

字节 veRL 提出在**同一张卡**上切换训练 / 推理模式：训练时用 FSDP/Megatron，推理 rollout 时切回 vLLM 引擎、共享显存上的权重。避免训推两套集群的权重搬运开销，在大规模 GRPO 场景能把吞吐提 30–50%。

---

## 十一、代码示例

### 11.1 用 TRL 做最小 DPO（基于 TRL 0.11+）

```
# pip install trl>=0.11 transformers datasets peft accelerate
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM
from trl import DPOTrainer, DPOConfig
from peft import LoraConfig

model_name = "Qwen/Qwen2.5-1.5B-Instruct"
tok = AutoTokenizer.from_pretrained(model_name)
tok.pad_token = tok.eos_token

model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype="bfloat16")
ref   = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype="bfloat16")

# UltraFeedback：prompt / chosen / rejected 三列
ds = load_dataset("HuggingFaceH4/ultrafeedback_binarized", split="train_prefs")

def to_dpo(ex):
    return {
        "prompt":   tok.apply_chat_template(ex["chosen"][:1],  tokenize=False),
        "chosen":   ex["chosen"][-1]["content"],
        "rejected": ex["rejected"][-1]["content"],
    }
ds = ds.map(to_dpo, remove_columns=ds.column_names).select(range(5000))

cfg = DPOConfig(
    output_dir="./dpo-qwen2.5-1.5b",
    per_device_train_batch_size=2,
    gradient_accumulation_steps=8,
    learning_rate=5e-7,
    num_train_epochs=1,
    beta=0.1,
    max_length=2048,
    max_prompt_length=1024,
    bf16=True,
    logging_steps=10,
    save_steps=500,
)

lora = LoraConfig(r=16, lora_alpha=32, target_modules="all-linear", task_type="CAUSAL_LM")

trainer = DPOTrainer(
    model=model, ref_model=ref, args=cfg,
    train_dataset=ds, processing_class=tok, peft_config=lora,
)
trainer.train()
trainer.save_model("./dpo-qwen2.5-1.5b-final")
```

**要点**：

- `beta=0.1` 是常用默认；偏好数据噪声大时降到 0.01。
- `learning_rate=5e-7` 比 SFT 小 10–100 倍，DPO 对 lr 极敏感，过大直接崩。
- LoRA DPO 在 1.5B–7B 上性价比最高，24 GB 显存即可跑。

### 11.2 用 OpenRLHF 跑一个 PPO

```
# 1. 安装
pip install openrlhf[vllm]

# 2. 单机 8 卡 PPO，以 Qwen2.5-7B 为例
ray start --head --num-gpus=8

python -m openrlhf.cli.train_ppo_ray \
  --ref_num_nodes 1 --ref_num_gpus_per_node 2 \
  --reward_num_nodes 1 --reward_num_gpus_per_node 2 \
  --critic_num_nodes 1 --critic_num_gpus_per_node 2 \
  --actor_num_nodes 1 --actor_num_gpus_per_node 2 \
  --vllm_num_engines 2 --vllm_tensor_parallel_size 1 \
  --colocate_actor_ref \
  --pretrain Qwen/Qwen2.5-7B-Instruct \
  --reward_pretrain OpenRLHF/Llama-3-8b-rm-mixture \
  --save_path ./ckpt/ppo-qwen2.5-7b \
  --micro_train_batch_size 4 --train_batch_size 128 \
  --micro_rollout_batch_size 8 --rollout_batch_size 1024 \
  --max_samples 100000 \
  --prompt_data OpenRLHF/prompt-collection-v0.1 \
  --input_key context_messages --apply_chat_template \
  --max_epochs 1 --num_episodes 1 \
  --prompt_max_len 1024 --generate_max_len 1024 \
  --actor_learning_rate 5e-7 --critic_learning_rate 9e-6 \
  --init_kl_coef 0.01 \
  --zero_stage 3 --bf16 --flash_attn --gradient_checkpointing
```

**读法**：

- `--colocate_actor_ref`：actor 和 reference 共享 GPU，省一半显存。
- `--vllm_num_engines 2`：独立的 rollout 集群。
- `--init_kl_coef 0.01`：KL 惩罚，训练中可自适应。
- `reward_pretrain` 必须提前训好或用开源 RM。

### 11.3 用 TRL + GRPOTrainer 跑数学推理 RL

```
from trl import GRPOConfig, GRPOTrainer
from datasets import load_dataset
import re

def math_reward_func(prompts, completions, **kw):
    """可验证 reward：最终 \\boxed{答案} 是否与 gt 一致"""
    rewards = []
    for completion, gt in zip(completions, kw["gold"]):
        m = re.search(r"\\boxed\{([^}]+)\}", completion)
        pred = m.group(1).strip() if m else ""
        rewards.append(1.0 if pred == str(gt).strip() else 0.0)
    return rewards

ds = load_dataset("openai/gsm8k", "main", split="train")
ds = ds.map(lambda x: {"prompt": x["question"], "gold": x["answer"].split("####")[-1].strip()})

cfg = GRPOConfig(
    output_dir="./grpo-qwen2.5-1.5b",
    learning_rate=1e-6,
    num_generations=8,         # 组大小 G
    max_completion_length=1024,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=4,
    bf16=True,
    beta=0.04,                 # KL 系数
    logging_steps=5,
)
trainer = GRPOTrainer(
    model="Qwen/Qwen2.5-1.5B-Instruct",
    reward_funcs=[math_reward_func],
    args=cfg, train_dataset=ds,
)
trainer.train()
```

这是复现 R1-Zero 思路的最小框架：base / instruct 模型 + 可验证 reward + GRPO。在 GSM8K 上跑几千步就能看到 [pass@1](mailto:pass@1) 显著提升。

---

## 十二、评估：对齐之后的模型怎么量？

### 12.1 能力评估

- **通用 benchmark**：MMLU、MMLU-Pro、C-Eval、CMMLU（中文）、AGIEval。
- **数学推理**：GSM8K、MATH、AIME 2024、CNMO、Olympiad-Bench。
- **代码**：HumanEval、MBPP、LiveCodeBench、SWE-bench。
- **对话 / 指令**：MT-Bench、AlpacaEval 2、Arena-Hard、WildBench。
- **中文对话**：AlignBench、SuperCLUE。

### 12.2 对齐质量评估

- **Chatbot Arena（LMSYS）**：真实用户盲测投票，ELO 排名，目前业界最硬的指标。
- **Reward hacking 检测**：看训练曲线里 reward 暴涨但人工评估停滞——典型 hacking。
- **Sycophancy**：构造”用户先说错答案 → 模型是否附和”的测试集（Anthropic sycophancy eval）。
- **Over-refusal**：XSTest、OR-Bench，测试模型对无害问题的误拒率。对齐太狠的模型会拒”我该怎么杀掉一个 Python 进程”。
- **Jailbreak 鲁棒性**：越狱攻击测试，如 DAN、角色扮演、虚构环境指令（prefix injection 等）。可使用 HarmBench、AdvBench 平台并叠加 GCG / PAIR 自动化红队攻击验证。通常需要专门构建一批”有害指令但安全回复”分布的数据点进行 SFT 或 DPO 混入防御。
- **对齐税（Alignment Tax）**：监测对齐（特别是安全性）介入后通用能力产生的牺牲程度，这需要在 MT-Bench 和 MMLU 这种核心指标里密切监控是否出现降级。

### 12.3 训练期在线指标

|指标|健康范围|异常|
|---|---|---|
|KL(π \| π_ref)|5–30|>100 说明 actor 漂飞|
|Response length|稳定或缓慢上升|突增→长度 hacking|
|Reward 均值|单调上升|停滞或跳水→ RM 失效|
|Entropy|缓慢下降|骤降→ mode collapse|
|Clip fraction|0.1–0.3|>0.5 说明 lr 太大|

---

## 十三、推理模型的数据合成

### 13.1 长 CoT 数据从哪来

R1 / o1 这种长推理模型训练的核心瓶颈不是算力而是**高质量长 CoT 数据**。主流路径：

1. **人工编写**：成本极高，几千条顶天，用作 **冷启动 SFT**。
2. **强模型蒸馏**：让 R1 / o1-preview / GPT-4 生成带 think 标签的 CoT，规则过滤后做 SFT。社区如 OpenThoughts、Bespoke-Stratos 走这条路。
3. **拒绝采样自举**：base 模型采 N 条，只保留答案正确且格式合规的，回灌做 SFT。
4. **MCTS / PRM 搜索**：用搜索拉出高质量轨迹。

### 13.2 拒绝采样流水线（R1 式）

```
def rejection_sample_pipeline(prompts, model, verifier, N=16, topk=2):
    out = []
    for p in prompts:
        candidates = [model.generate(p, temperature=0.9) for _ in range(N)]
        scored = [(c, verifier(p, c)) for c in candidates]
        # 规则过滤：格式 + 答案正确 + 长度合理 + 无语言混杂
        filtered = [c for c, s in scored if s > 0.99 and 200 < len(c) < 8000]
        out.extend(filtered[:topk])
    return out  # 回灌做第二轮 SFT
```

R1 技术报告里明确：第三阶段用约 **60 万条拒绝采样推理数据 + 20 万条通用数据**做 SFT，再进第四阶段全场景 RL。

### 13.3 注意事项

- **难度分布**：太简单的题贡献信号少，太难的题几乎没有成功样本。按通过率 30–70% 筛最有效（“可学区间”）。
- **去污染**：推理训练数据极易和评测集重叠（GSM8K、MATH 网上都有题解），必须做 n-gram 去重。
- **语言一致性**：R1-Zero 出现”中英混杂”，R1 加入 language consistency reward 修复。工程上可用 langdetect + 正则惩罚。

### 13.4 课程式调度（curriculum）

长 CoT RL 训练的一个关键是**难度课程**：开局全是难题会导致 reward 长期为零、策略原地打转；全是简单题又学不到新东西。常见做法：

```
def build_curriculum(prompts, base_model, stages=3):
    # 用 base 模型预估每条 prompt 的 pass@8
    pass_rates = [estimate_pass_at_k(base_model, p, k=8) for p in prompts]
    buckets = {
        "easy":   [p for p, r in zip(prompts, pass_rates) if 0.4 <= r <= 0.8],
        "medium": [p for p, r in zip(prompts, pass_rates) if 0.1 <= r < 0.4],
        "hard":   [p for p, r in zip(prompts, pass_rates) if 0 < r < 0.1],
    }
    # 阶段性放入 easy → medium → hard
    return buckets
```

也可以做**在线难度调度**：训练中持续统计每个 prompt 最近 K 次的通过率，通过率≥0.9 的移出训练集，通过率=0 的暂时冻结，中间区间重点训。DeepSeek-R1 / Kimi K1.5 都提到类似技巧。

### 13.5 长 CoT 的训练端压力

生成长度从 SFT 的几百 token 暴涨到 RL 的 8k–32k，带来几个工程问题：

- **KV cache 爆炸**：rollout 时单条 response 的 KV 可达 GB 级，vLLM PagedAttention 的块大小、swap 空间要相应放大。
- **梯度检查点（gradient checkpointing）必开**：否则 forward 激活吃不下。
- **partial rollout**：对一次没生完的样本保存中间 KV，下一 step 继续解码（Kimi K1.5），提升 GPU 利用率。
- **超长样本截断策略**：超过 max_length 时给一个”未完成惩罚”而不是直接丢弃，避免策略学会刻意超长逃避训练。

---

## 十四、实操建议与选型速查

### 14.0 一张”对齐算法选型决策树”

### 14.1 不同团队的推荐路径

**场景 A：预算有限，只想把 base 做成 chat 助手** - 8×A100 / H100，30B 以内 - 路线：SFT（LoRA，10k 条）→ DPO（UltraFeedback，5k–50k 对） - 框架：LLaMA-Factory 或 TRL

**场景 B：要做垂直领域（医疗 / 金融 / 代码）** - 先做领域 continual pretrain（小步、低 lr） - SFT：领域指令 5k–50k + 通用指令 5k（防遗忘） - DPO：领域偏好 5k + 通用 5k - 评估重点：领域 benchmark + 保留通用 MT-Bench 不掉

**场景 C：做通用推理模型（开源 R1 级别）** - ≥ 64 × H100，资源密集 - 路线：冷启动 SFT（千条长 CoT）→ GRPO（数学 / 代码可验证 reward）→ 拒绝采样 SFT → 全场景 RL - 框架：OpenRLHF 或 veRL - **关键**：验证器稳定性、reward 稀疏性处理、训推权重同步延迟

**场景 D：只做 Agent / 工具调用对齐** - SFT 工具调用模板必须精确 - 偏好数据：成功调用 vs 幻觉参数调用 - 或直接 GRPO + “工具调用是否成功” 作为 0/1 reward

### 14.2 常见问题排查

  
|症状|可能原因|处理|
|---|---|---|
|DPO 训几十步 loss 下降、eval 崩|β 太小 / lr 太大|β 适当升高 (如 0.1→0.3) / lr 减半|
|PPO reward 飙升但回答变差|reward hacking|加 KL、重训 RM、加正则|
|模型疯狂加长答案|length bias|换 SimPO / ORPO，或加 length penalty|
|对齐后推理能力掉|分布偏移太远|混合 SFT 数据进 DPO；降低 epochs|
|GRPO 很多组全对 / 全错|数据难度不匹配|按通过率筛 prompt 到 30–70% 区间|
|过度拒绝|RLHF 太重 safety|混入 over-refusal 反例 SFT|

### 14.3 中国 vs 全球生态对照

  
|维度|中国|全球|
|---|---|---|
|代表对齐开源|DeepSeek-R1、Qwen3、GLM-4.6、Kimi K1.5|Llama 3.3、Mistral Large 2|
|开源 RLHF 框架|OpenRLHF、veRL、LLaMA-Factory|TRL、Nemo-Aligner、Axolotl|
|偏好数据|BELLE、COIG-CQIA、AlignBench-dev|UltraFeedback、HH-RLHF、Nectar|
|云厂 PaaS|阿里 PAI、火山方舟、百度千帆、腾讯 TI|AWS Bedrock、Azure AI、Vertex AI|
|推理模型付费 API|Doubao 1.5-pro、Qwen-Max Thinking、GLM-Zero|o1/o3、Claude thinking、Gemini 2.5|

### 14.4 端到端时间预算参考

以 7B 模型、8×H100 单机为例，完整跑一轮”SFT + DPO + GRPO”的大致时间：

|阶段|数据量|时间|备注|
|---|---|---|---|
|SFT（full）|100k 条，seq 4k|8–12 h|2 epoch，packing|
|SFT（LoRA r=64）|100k 条|3–4 h|显存 <= 40 GB/卡|
|RM 训练|100k 对|6–8 h|单 epoch|
|DPO（LoRA）|50k 对|3–5 h|β=0.1|
|PPO（OpenRLHF）|20k prompt × 1 epoch|24–48 h|rollout 占比大|
|GRPO（G=8，GSM8K）|20k prompt|20–30 h|长 CoT 更慢|

实际资源往往不是瓶颈，**数据准备 + 评估迭代**才是主要工期占用，通常要预留 2–3 周做数据清洗和结果调优。

---

## 十五、深入 PPO 工程细节

### 15.1 GAE 在 RLHF 里的特殊形态

标准 PPO 用 GAE（Generalized Advantage Estimation）平滑 advantage。在 LLM-RLHF 中，reward 大多是**稀疏的序列级 reward**（整条回答只有一个 RM 分数），加上逐 token 的 KL 惩罚构成 shaped reward：

> 此处的负号正是为了让 actor 策略偏离 reference model 时获得实际的**负奖励（惩罚）**。

GAE 展开：

RLHF 里常用 。 对应”把最终 reward 完整回传到每个 token”，比 更稳（否则前几个 token 几乎没有学习信号）。

### 15.2 Rollout 效率：vLLM + Ray 的组合拳

一次 PPO step 里，rollout（生成样本）耗时常占 60–80%。优化手段：

- **continuous batching**：vLLM 默认能在同一 batch 里混合不同长度的请求，显著高于传统 static batching。
- **prefix sharing**：同 prompt 采 N 条时只计算一次 prefill，decode 并行 N 次。GRPO 尤其受益。
- **tensor parallel vs pipeline parallel on rollout**：70B 以上模型 rollout 时 TP=8 比 PP 更低延迟。
- **异步 rollout（overlap）**：rollout 与 train step 双缓冲异步，代价是 off-policy 程度加深（需要 importance sampling 校正）。

### 15.3 On-policy vs Off-policy 的取舍

“严格 on-policy” 意味着每次更新前数据都用最新策略采样。工程上为了效率常引入小幅 off-policy：

- 一次 rollout 样本用于 K 次 PPO 更新（K=2–4 常见）。
- Rollout 引擎权重滞后于训练引擎 1 个 step。

滞后过大会导致 importance weight 偏离 1，触发 PPO 的 clipping 截断，无法推进策略探索。通过 Importance Sampling 去修正策略梯度也是必需的：

实践中保持 **K ≤ 4、rollout/train 权重同步延迟 ≤ 1 step** 是目前大模型离线 PPO 在效率和收敛之间的最优平衡点。

---

## 十六、Reward Model 训练实操

### 16.1 训练配方

- 从 **SFT 模型** 热启动（不是 base，否则学不到指令意图）。
- **替换 LM head 为 1-dim value head**：初始化 `nn.Linear(hidden, 1)`。
- Loss 只算 pairwise logistic（）；**只取 response 最后一个非 pad token** 的 hidden 做打分。
- **lr = 1e-6 ~ 5e-6**，只训 1 epoch，极易过拟合。
- **margin loss 变体**：当人类标注里有”强偏好 / 弱偏好”定级时，可用 ，间距 随置信度缩放。

### 16.2 RM 的评估

RM 本身的准确度是整条管线能否运转的地基，相关指标：

- **Pairwise accuracy**：在 held-out 偏好对集上预测正确的比例，70–75% 合格，>80% 时须警惕数据泄露。
- **RewardBench**：AllenAI 开源评测基准，全面考察推理、对话、代码、安全维度的准确度。
- **参数规模**：RM 规模通常越大越好，但推理成本线性增加。大部分情况下与其主模型对应的 7B–14B 处于性价比拐点。

### 16.3 多目标 RM

真实业务对齐必须对多维度目标如 Helpful, Honest, Harmless 做 Trade-off：

- **单 RM 多 head**：共用主干，由不同 head 评估不同维度指标，最终线性加权送给 PPO Actor。
- **Mixture of Rewards**：不同维度训练独立的 Reward Model（可混搭如规则或者 AI as a Judge），聚合后得分。
- **Rule + RM 混合**：安全、隐私直接截断或者惩罚（-1），内容打分由 RM 承担。

---

## 十七、流水线整体编排与监控

由于训练阶段涉及模型众多，RLHF 工程平台编排相当复杂：

```
┌──────────────────────────────────────────────────┐
│ 数据层：Prompt DB / Preference DB / Gold Dataset │
└───────┬──────────────────────────────────────────┘
        │
┌───────▼──────┐   ┌──────────────┐   ┌──────────┐
│ Trainer Ctrl │──→│ Rollout Pool │──→│ Verifier │
│ (Ray head)   │   │ (vLLM x N)   │   │ (math/code│
└───────┬──────┘   └──────────────┘   │  sandbox)│
        │                              └──────────┘
        ├──→ Actor Train (DeepSpeed)
        ├──→ Critic Train
        ├──→ Weight Sync (NCCL broadcast → vLLM)
        └──→ Metrics (Prom/Grafana + W&B)
```

**监控看板必须有**：

- KL(π‖π_ref) 折线、reward 均值 / 方差、response length p50/p95、entropy；
- GPU 利用率、rollout vs train 时间占比；
- 每 K step 跑一次**离线 eval**（AlpacaEval 2 / GSM8K 小集），与训练 reward 做对比防 hacking；
- **样例可视化**：每步随机 dump 10 条 (prompt, response, reward)，供人工看。

---

## 十八、小结

RLHF 从 InstructGPT 的”SFT + RM + PPO 三段式”起步，到 2024 年 DPO 把它压扁成”一段式”，再到 2025 年 GRPO + 可验证 reward 把它推进到**推理模型新纪元**。这条流水线的工程本质是：

1. **用 SFT 圈定行为模式**——格式、模板、工具调用；
2. **用偏好信号或可验证信号塑造偏好**——RM / DPO / 规则验证；
3. **用 RL 或等价优化在策略空间精细调整**——PPO / GRPO 等；
4. **用推理时 scaling 兑现训练投入**——best-of-N、长 CoT、搜索。

对于基础设施工程师而言，真正的难点不是写 loss 函数——TRL / OpenRLHF 把算法都封装好了——而是：

- **训推权重同步**的低延迟实现；
- **四模型显存拓扑**的合理切分（colocate vs 分离）；
- **大规模偏好数据**的采集、清洗、去污染流水线；
- **长 CoT rollout** 下的显存 / 吞吐平衡（partial rollout、KV cache 复用）；
- **在线评估**和 reward hacking 的快速发现。

过去三年对齐范式演进速度远超其他方向：2022 PPO、2023 DPO、2024 GRPO、2025 长 CoT + 可验证 reward，每一代都在降低工程门槛或抬高能力上限。可以预见的方向是：

- **Self-play / self-improve 闭环**：模型生成数据、验证、回训，人力退出主回路；
- **多模态对齐**：图像 / 视频 / 音频的偏好建模，Reward 从文本单通道扩到多通道；
- **Agent 对齐**：RL on tool-use，奖励来自任务完成度而非单轮文本质量；
- **验证器即瓶颈**：更可靠、更可 scale 的 verifier（含形式化证明、沙箱执行）会成为新的竞争点。

下一篇 10《Checkpoint 与故障容忍》会进入另一个硬工程话题：数百 B 模型、几十天训练周期、几千卡集群下，如何做到”挂了一张卡不必从头再来”——这是支撑所有上面这些训练 / RL 流水线真正落地的底座。

---

**上一篇**：[【大模型基础设施工程】08：MoE 训练工程](https://quant67.com/post/llm-infra/08-moe-training/08-moe-training.html) **下一篇**：[【大模型基础设施工程】10：Checkpoint 与故障容忍](https://quant67.com/post/llm-infra/10-checkpoint-fault/10-checkpoint-fault.html)

## 参考资料

1. Schulman et al., _Proximal Policy Optimization Algorithms_ (PPO), 2017.
2. Christiano et al., _Deep Reinforcement Learning from Human Preferences_, 2017.
3. Stiennon et al., _Learning to summarize from human feedback_, 2020.
4. Ouyang et al., _Training language models to follow instructions with human feedback_ (InstructGPT), NeurIPS 2022.
5. Bai et al., _Training a Helpful and Harmless Assistant with RLHF_, Anthropic 2022.
6. Bai et al., _Constitutional AI: Harmlessness from AI Feedback_, Anthropic 2022.
7. Rafailov et al., _Direct Preference Optimization: Your Language Model is Secretly a Reward Model_, NeurIPS 2023.
8. Azar et al., _A General Theoretical Paradigm to Understand Learning from Human Preferences_ (IPO), 2023.
9. Ethayarajh et al., _KTO: Model Alignment as Prospect Theoretic Optimization_, 2024.
10. Hong et al., _ORPO: Monolithic Preference Optimization without Reference Model_, 2024.
11. Meng et al., _SimPO: Simple Preference Optimization with a Reference-Free Reward_, 2024.
12. Shao et al., _DeepSeekMath: Pushing the Limits of Mathematical Reasoning in Open LMs_ (GRPO), 2024.
13. DeepSeek-AI, _DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning_, 2025.
14. Kimi Team, _Kimi K1.5: Scaling Reinforcement Learning with LLMs_, 2025.
15. OpenAI, _Learning to Reason with LLMs_（o1 blog），2024.
16. Qwen Team, _Qwen3 Technical Report_, 2025.
17. OpenRLHF: [https://github.com/OpenRLHF/OpenRLHF](https://github.com/OpenRLHF/OpenRLHF)
18. TRL: [https://github.com/huggingface/trl](https://github.com/huggingface/trl)
19. veRL: [https://github.com/volcengine/verl](https://github.com/volcengine/verl)
20. DeepSpeed-Chat: [https://github.com/microsoft/DeepSpeedExamples/tree/master/applications/DeepSpeed-Chat](https://github.com/microsoft/DeepSpeedExamples/tree/master/applications/DeepSpeed-Chat)
21. LLaMA-Factory: [https://github.com/hiyouga/LLaMA-Factory](https://github.com/hiyouga/LLaMA-Factory)
22. Chatbot Arena / LMSYS: [https://lmarena.ai](https://lmarena.ai/)
23. Lightman et al., _Let’s Verify Step by Step_（PRM），2023.
24. Zheng et al., _Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena_, 2023.
25. Lambert et al., _RewardBench: Evaluating Reward Models for Language Modeling_, 2024.
26. Sheng et al., _HybridFlow: A Flexible and Efficient RLHF Framework_ (veRL), 2024.
27. Perez et al., _Discovering Language Model Behaviors with Model-Written Evaluations_ (sycophancy), 2022.

## 同主题继续阅读

把当前热点继续串成多页阅读，而不是停在单篇消费。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】05：训练全景：Pre-train、SFT、RLHF、DPO、蒸馏](https://quant67.com/post/llm-infra/05-training-overview/05-training-overview.html)

以工程视角串联现代 LLM 的四阶段训练栈——预训练、中训、SFT 与对齐——覆盖数据、Tokenizer、优化器、精度、Scaling Law 与代表性训练框架。

2026-04-22 · architecture / ai-infra

### [大模型基础设施工程](https://quant67.com/post/llm-infra/index.html)

面向中国工程团队的大模型基础设施系列。从 GPU/CUDA/互联、训练框架与 3D 并行、vLLM/SGLang 推理引擎、量化与推测解码、RAG/Agent 到服务化、网关、可观测性与安全合规，覆盖 LLMOps 全链路。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】11：推理引擎基础](https://quant67.com/post/llm-infra/11-inference-basics/11-inference-basics.html)

从 Prefill/Decode 两阶段、KV Cache、Continuous Batching 到 PD 分离，系统讲清楚大模型推理的工程基础。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】10：Checkpoint 与故障容忍](https://quant67.com/post/llm-infra/10-checkpoint-fault/10-checkpoint-fault.html)

万卡集群训练每天都在断：从 GPU HBM ECC、NVLink 降级到 SDC，本篇系统讲 checkpoint、恢复与弹性容错的工程实践。