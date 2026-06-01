可观测性（Observability）在传统微服务里已经是老生常谈：Metrics、Logs、Traces 三件套，加一点 Profiling 就能覆盖 90% 的排障场景。但把这套方法论直接搬到大模型系统上，会发现它**远远不够**：

- 一次请求的成本不是”CPU 秒”而是”token 数 × 单价”，而且 input / output / cached 三档价格不同；
- 延迟不是”p99 响应时间”一个数，而要拆成 **TTFT（Time To First Token）**、**TPOT（Time Per Output Token）**、**E2E**；
- 一个 Agent 请求可能产生 20 次子 LLM 调用、5 次工具调用、3 次 retriever，任何一步失败都会让用户”感觉变蠢”；
- 最可怕的是——**请求返回 HTTP 200、延迟正常、成本正常，但答案是幻觉**。传统监控一个告警都不会响。

本篇把 LLM 可观测性拆成四层：**基础设施层（GPU / 推理引擎）**、**调用层（LLM / RAG / Agent trace）**、**质量层（Eval / 幻觉 / 用户反馈）**、**业务层（成本 / A/B / 合规）**，并串联主流工具栈：Langfuse、LangSmith、Helicone、Arize Phoenix、W&B Weave、OpenLLMetry、AgentOps、Pezzo、Lunary，以及 OpenTelemetry GenAI Semantic Conventions（2025 稳定版）。

贯穿全文的一个观点：**可观测性不是把监控仪表盘做多花哨，而是”出问题时能 5 分钟定位、3 小时修复，下次不再出现”**。围绕这个目标，本文既会讲指标口径和工具选型，也会给出告警阈值、故事复盘、平台化落地路径。

前置阅读：[21-推理服务化](https://quant67.com/post/llm-infra/21-serving-infra/21-serving-infra.html)、[22-大模型网关](https://quant67.com/post/llm-infra/22-llm-gateway/22-llm-gateway.html)。

### 1.1 与传统微服务的差异

把一个在线 LLM 产品和一个传统 CRUD 微服务放一起对比：

  
|维度|传统微服务|LLM 服务|
|---|---|---|
|计费单位|请求数 / CPU 秒|input / output / cached token，按模型不同价|
|延迟语义|单一 latency（p50/p99）|TTFT（流式首包）+ TPOT（每 token）+ E2E|
|正确性|状态码 200 即可|200 不代表正确，可能幻觉、跑题、拒答|
|调用拓扑|固定 RPC 调用链|动态 Agent 循环，轮次、分支、工具不确定|
|数据敏感|用户 ID / 订单号|完整 Prompt / Completion 可能含 PII、业务秘密|
|重放|SQL 重跑|需要完整 Prompt + 模型版本 + 温度 + 种子|
|资源瓶颈|CPU / DB 连接|GPU SM 利用、HBM、KV cache、网络带宽|
|回归|单测 + 集成测试|数据集 + LLM-as-Judge + 人工标注|

这张表说明：LLM 系统需要**新的信号、新的存储、新的评估闭环**。

### 1.2 四层观测模型

本文按自下而上顺序展开。

## 二、核心指标体系

### 2.1 延迟：TTFT / TPOT / E2E

流式输出是 LLM 的默认交互形态，单一 latency 已不够用：

- **TTFT（Time To First Token）**：从请求到达到首个 token 返回的时间。用户主观”响应快不快”的决定因素；通常由 **Prefill 阶段**和排队等待决定。
- **TPOT（Time Per Output Token）**，又叫 ITL（Inter-Token Latency）：输出每个 token 的平均时间，决定”打字速度”；由 **Decode 阶段**、batch 大小、显存带宽决定。
- **E2E（End-to-End Latency）**：从请求到最后一个 token，等于 `TTFT + TPOT × output_tokens`。
- **Queue Time**：进入引擎之前的排队时间，高并发时往往吞没一切优化。

线上告警的门槛参考（以 13B/32B 模型为例）：

```
TTFT p95  < 500 ms       (对话式)
TTFT p95  < 2  s         (长文档/Agent)
TPOT p95  < 50 ms        (>= 20 tokens/s)
Queue p99 < 1  s
```

### 2.2 吞吐：tokens / req / GPU

- `output_tokens_per_second`：单卡总输出 token 数，最贴近”成本效率”。
- `requests_per_second`：对比同一模型不同后端（vLLM vs SGLang vs TRT-LLM）。
- `goodput`：同时满足 SLO（TTFT、TPOT 都达标）的 throughput，业界新共识指标。

### 2.3 GPU 与引擎内部信号

- **GPU 利用率（SM utilization）**：不是 `nvidia-smi` 那个 100%——它只是”有 kernel 在跑”。真正要看的是 DCGM 的 `DCGM_FI_PROF_SM_ACTIVE`、`DCGM_FI_PROF_PIPE_TENSOR_ACTIVE`。
- **HBM 占用**：`DCGM_FI_DEV_FB_USED`；超 90% 通常意味着 KV cache 即将 swap。
- **KV Cache 使用率**：vLLM 的 `vllm:gpu_cache_usage_perc`。
- **Prefix Cache 命中率**：SGLang 的 `sglang:cache_hit_rate`、vLLM 的 automatic prefix caching 命中率——对多轮对话、RAG 复用 prompt 极其重要，命中 60% 以上 TTFT 能砍一半。
- **Running / Waiting 请求数**：队列深度，扩容信号。

### 2.4 Token 成本：input / output / cached

现代 API 的计价是**三档**：

  
|类型|相对价格|典型应用|
|---|---|---|
|Input (uncached)|1x|新 prompt|
|Cached input|0.1x ~ 0.5x|系统提示、长文档重用（OpenAI / DeepSeek / Anthropic 均支持）|
|Output|3x ~ 5x|生成 token|

因此观测侧要分别记录：

```
usage = {
    "prompt_tokens": 1234,
    "prompt_tokens_details": {"cached_tokens": 1000},
    "completion_tokens": 456,
    "completion_tokens_details": {"reasoning_tokens": 200},  # o1/R1 系列
}
```

**缓存命中率 = cached_tokens / prompt_tokens**。一个成熟 RAG 系统应该稳定在 50%+。

### 2.5 质量：不再是 200 就算对

- **满意度**：用户显式 👍/👎（LangSmith、Langfuse 都有 SDK 回写）；隐式信号包括”是否复制”、“是否追问”、“是否停止生成”。
- **引用覆盖率**（RAG）：answer 中有多少 claim 能对齐到检索片段。
- **Refusal Rate**：模型说”我不能回答”的比例；太低可能越权，太高体验差。
- **Answer Length 分布**：突变往往预示 prompt 被污染。
- **Groundedness / Faithfulness**：RAGAS 等打分 0–1。

## 三、Trace 模型与标准

### 3.1 为什么需要 Trace

一个 Agent 请求的真实调用：

LLM(Summarizer)Tool(SQL)LLM(Planner)EmbedRetrieverAgentUserLLM(Summarizer)Tool(SQL)LLM(Planner)EmbedRetrieverAgentUser"上季度华东区销售?"embed(query)search(vec, k=8)plan(context)call_tool(sql, "...")run_sqlrowssummarize(rows, context)answer + citationsstream

任何一环变慢或出错，都需要 trace 才能定位。

### 3.2 OpenTelemetry GenAI Semantic Conventions

OpenTelemetry 在 2024 底到 2025 陆续把 `gen_ai.*` 语义约定从 experimental 推向 stable。关键字段（节选）：

```
span.kind                    = CLIENT
span.name                    = "chat gpt-4o-mini"
gen_ai.system                = "openai" | "anthropic" | "deepseek" | ...
gen_ai.operation.name        = "chat" | "text_completion" | "embeddings"
gen_ai.request.model         = "gpt-4o-mini"
gen_ai.response.model        = "gpt-4o-mini-2024-07-18"
gen_ai.request.temperature   = 0.2
gen_ai.request.max_tokens    = 2048
gen_ai.usage.input_tokens    = 1234
gen_ai.usage.output_tokens   = 456
gen_ai.response.finish_reasons = ["stop"]
gen_ai.conversation.id       = "conv_..."
```

工具调用、Agent 场景的扩展：

```
gen_ai.tool.name        = "search_sql"
gen_ai.tool.call.id     = "call_abc123"
gen_ai.agent.id / name
gen_ai.server.request.duration (histogram)
gen_ai.client.token.usage (histogram)
```

**原则**：默认不把 prompt / completion 塞进 attribute（PII），而用 **Events**（log-record like）承载；由 `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` 环境变量控制是否采集内容。

### 3.3 OpenInference（Arize）与 OpenLLMetry（Traceloop）

两套早于 OTel 稳定版诞生的”事实标准”：

- **OpenInference**：Arize Phoenix 推动，`openinference.span.kind = LLM/CHAIN/RETRIEVER/RERANKER/EMBEDDING/TOOL/AGENT`，输入输出用 `input.value` / `output.value`。已有向 OTel GenAI 对齐的适配。
- **OpenLLMetry**：Traceloop 推动，基于 OTel 的 SDK `traceloop-sdk`，对 20+ 框架（LangChain、LlamaIndex、Haystack、Mistral、Bedrock…）做 monkey-patch instrumentation，一行 `Traceloop.init()` 即可接管。

2025 年的实际姿势：**后端接收 OTel，SDK 任选**。Langfuse、Phoenix、SigNoz、Jaeger、Tempo、Dynatrace 都开始原生理解 `gen_ai.*`。

### 3.4 Span 层次模板

推荐的 span 分层：

```
Trace: "user chat #U123"
└─ Span: agent.run                           (AGENT)
   ├─ Span: retriever.search                 (RETRIEVER)
   │  └─ Span: embedding.encode              (EMBEDDING)
   ├─ Span: reranker.rerank                  (RERANKER)
   ├─ Span: llm.plan (gpt-4o-mini)           (LLM)
   ├─ Span: tool.sql_query                   (TOOL)
   ├─ Span: tool.http_fetch                  (TOOL)
   └─ Span: llm.summarize (claude-3-5)       (LLM)
```

每个 LLM span 都应带：model、params、usage、cost、TTFT、TPOT、finish_reason、messages（可脱敏）。

## 四、主流工具栈横评

### 4.1 LangSmith（LangChain 官方）

- 商业（有免费额度），深度绑定 LangChain / LangGraph，但也支持任意 SDK（通过 `@traceable` 装饰器或 OTel）。
- 特色：**Playground**（直接改 prompt 重跑）、**Dataset & Eval**（可视化回归）、**Annotation Queue**（人工标注流水线）。
- 缺点：SaaS 为主，数据出境；企业 self-host 价格高。

### 4.2 Langfuse（开源 self-host 首选）

- Apache-2.0，ClickHouse + Postgres 后端，支持 OTel ingest，有完整的 Prompt Management / Eval / Dataset / Session / User 维度。
    
- 一条命令起：
    
    ```
    git clone https://github.com/langfuse/langfuse
    cd langfuse && docker compose up -d
    # 访问 http://localhost:3000
    ```
    
- 跟任何 OpenAI 兼容 SDK 的集成只需包装一层：
    
    ```
    from langfuse.openai import openai  # drop-in 替代 import openai
    
    resp = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "hello"}],
        metadata={"user_id": "u_123", "feature": "chat"},
    )
    ```
    
    无需改其他代码，Langfuse 自动记 prompt、completion、usage、cost、latency。
    
- 优点：**国内可 self-host**（数据不出境），Prompt 版本化一流，Eval 内置 LLM-as-Judge 与 RAGAS/DeepEval 桥接。
    

### 4.3 Helicone

- 开源 + SaaS 双模式，核心卖点是**代理式接入**：把 `base_url` 从 `api.openai.com` 改成 `oai.helicone.ai` 就开始采集，**零代码**。
- 适合不想改代码、只想要”全部请求一份拷贝”的团队。
- 缺点：代理模式引入一跳延迟；高级 Eval 较弱。

### 4.4 Arize Phoenix

- Apache-2.0，Arize AI 开源，**OpenInference** 参考实现。
- 强在**离线调试**：notebook 里一行 `px.launch_app()` 起 UI，边跑边看 trace；有内置 **RAG 三角形可视化**（query/context/answer 嵌入投影）。
- 与 LlamaIndex、DSPy、Haystack、LangChain 都有官方 integration。

### 4.5 Weights & Biases Weave

- W&B 团队出品，针对”习惯 wandb 做实验跟踪”的人。
- `weave.init("my-project")` + `@weave.op()` 装饰函数，自动记录 I/O、版本、成本。
- 优势：和 W&B 训练/评估平台打通，适合一条龙团队。

### 4.6 OpenLLMetry / Traceloop

- SDK：`pip install traceloop-sdk`，`Traceloop.init(app_name="my-app")`；自动 instrument LangChain、LlamaIndex、OpenAI、Anthropic、Bedrock、Vertex、Qdrant、Pinecone、Weaviate、Chroma……
- 纯标准 OTel，后端随便选（Langfuse / SigNoz / Jaeger / Datadog / Dynatrace）。
- 适合”已有 APM 栈，想无缝加 LLM 维度”。

### 4.7 AgentOps

- 专攻 Agent：统计轮次、工具调用成功率、**Session Replay** 一键回放。
- 与 CrewAI、AutoGen、LangGraph、LlamaIndex Agents 集成。
- 对多 Agent 系统友好，能看到 Agent 间消息流。

### 4.8 Pezzo / Lunary

- **Pezzo**：开源 Prompt 管理 + 观测，Prompt 作为一等公民（版本、环境、A/B）。
- **Lunary**（原 LLMonitor）：开源 + SaaS，偏产品化，带用户管理、分析面板、Eval。

### 4.9 选型决策树

## 五、Prompt / Output 存储与脱敏

### 5.1 敏感数据问题

Prompt 里可能出现：

- 用户身份证、手机号、银行卡（客服场景）；
- 内部代码、合同文本（Copilot / 法律场景）；
- 病历、病人姓名（医疗场景）；
- 未公开财报（金融场景）。

直接 full-trace 到 SaaS 就是合规事故。

### 5.2 脱敏策略

1. **客户端脱敏**：SDK 在发送前用正则 / NER 替换 PII 为 `<PHONE>`、`<ID_CARD>`；原文仅本地保留。
2. **网关脱敏**：在 [LLM 网关](https://quant67.com/post/llm-infra/22-llm-gateway/22-llm-gateway.html) 统一处理，观测后端只看到脱敏后的流。
3. **字段级加密**：prompt / completion 用 KMS 加密存储，查询时按角色解密。
4. **采样**：只存 1% 原文 + 100% 结构化（usage、latency、tags）。
5. **TTL**：按法规设置（见 §12）。

Langfuse 的 `mask` 钩子示例：

```
from langfuse import Langfuse

def mask(data):
    import re
    if isinstance(data, str):
        data = re.sub(r"1[3-9]\d{9}", "<PHONE>", data)
        data = re.sub(r"\d{17}[\dxX]", "<ID>", data)
    return data

langfuse = Langfuse(mask=mask)
```

## 六、评估闭环

### 6.1 在线 vs 离线

### 6.2 在线评估：LLM-as-Judge

对采样请求跑一个”裁判模型”，常见维度：

- **Relevance**：答案是否扣题；
- **Groundedness / Faithfulness**：答案是否能被检索上下文支持；
- **Helpfulness**：是否真的解决了问题；
- **Toxicity / Safety**：是否违规；
- **Conciseness**：是否啰嗦。

Langfuse 自带 Evaluator，也可以自己写：

```
judge_prompt = """
你是严格的评审。请根据 [Context] 判断 [Answer] 是否完全由 [Context] 支持。
只输出 0.0-1.0 分数和一行理由。
[Context]
{context}
[Answer]
{answer}
"""
```

注意：**裁判模型必须比生产模型更强或至少同级**，否则存在 judge 偏见；并且要定期和人工标注对齐。

常见坑：

- 只用一个 judge → bias 放大，建议用”pairwise 对比 + 多 judge 投票”；
- judge 本身也会幻觉 → 要求它”只对能在 context 中找到依据的 claim 给高分”；
- 裁判 prompt 过短 → 加 few-shot 示例、加严格的输出格式（JSON schema）；
- 成本失控 → 只在”模型回答置信度低”或”用户点踩”时触发，而非全量。

### 6.3 离线评估框架

- **RAGAS**：RAG 专用，提供 `faithfulness`、`answer_relevancy`、`context_precision/recall`。
- **DeepEval**：pytest-like，写 `assert_test(GEval(...))`，CI 友好。
- **Giskard**：自动扫描（bias、prompt injection、robustness）。
- **promptfoo**：YAML 驱动矩阵评估，适合 prompt 工程师 CLI 流。
- **Arize Phoenix Evals**：和 trace 打通，直接点 trace 加评估。

promptfoo 片段：

```
providers:
  - openai:gpt-4o-mini
  - deepseek:deepseek-chat
  - anthropic:claude-3-5-sonnet
prompts:
  - file://prompts/summarize_v1.txt
  - file://prompts/summarize_v2.txt
tests:
  - vars: {doc: file://data/d1.md}
    assert:
      - type: llm-rubric
        value: 必须包含结论与证据链
      - type: cost
        threshold: 0.01
      - type: latency
        threshold: 3000
```

### 6.4 数据集治理

- **冻结集（Golden Set）**：人工标注、代表性强，不再扩充，用于跨版本对比；
- **滚动集**：从线上 badcase 不断采样，用于回归；
- **对抗集**：安全 / 越狱 / prompt 注入样本；
- 每次 Prompt 或模型变更，**两类数据集分数都不能回退**才允许发布。

## 七、幻觉与事实核查

### 7.1 Groundedness 分数

核心公式：

```
groundedness = (answer 中被 context 支持的 claims) / (answer 中总 claims)
```

实现：让 judge LLM 把 answer 拆成原子 claims，再逐条判 entail / contradict / neutral。

### 7.2 引用对齐

- 让模型在生成时标注 `[1] [2]`；
- 后处理校验：每个引用编号是否命中检索到的 chunk；
- 页面上 hover 引用显示原文片段——这是**用户可感知**的幻觉兜底。

### 7.3 多样性与拒答

- **Refusal rate**：过高检查是否 system prompt 过严 / 安全层误伤；
- **Response entropy**：同 prompt 多次采样，输出相似度太低代表不稳定；
- **Out-of-scope 检测**：retriever score 太低时主动拒答并提示用户。

### 7.4 幻觉的三种典型形态

工程上建议把”幻觉”细分，不同形态处置不同：

1. **事实型幻觉**：捏造人物、日期、数字。→ Groundedness + 外部知识核查。
2. **引用型幻觉**：引了存在的文档但原文不支持结论。→ claim 级 entailment 检查。
3. **指令幻觉**：不按用户要求的格式 / 约束输出。→ 结构化输出（JSON Schema、function call）+ 校验重试。

不同形态的观测指标、告警阈值和修复手段都不一样，把它们混在一个”hallucination rate”里会误导方向。

## 八、A/B 实验

### 8.1 分流维度

- 模型：`gpt-4o-mini` vs `deepseek-v3.5` vs `qwen3-max`；
- Prompt 版本：`v1` vs `v2`；
- 检索参数：`k=5` vs `k=10`；
- Rerank 开关；
- Temperature、top_p。

通常在 [LLM 网关](https://quant67.com/post/llm-infra/22-llm-gateway/22-llm-gateway.html) 或观测 SDK 里按 `user_id` hash 稳定分桶。

### 8.2 在线指标

- 直接：👍/👎、复制率、续问率、会话时长；
- 成本：per-request cost；
- 质量：在线 judge 分数；
- 业务：下单转化、工单解决率、NPS。

Langfuse / LangSmith 都支持 `experiment_id + variant` 打标，然后在面板里对比。

### 8.3 显著性

LLM A/B 样本量往往不如传统互联网大，要警惕：

- 方差大（同模型不同种子答案差异明显）；
- 异质性（不同场景用户偏好不同）；
- 推荐跑 **Sequential Testing / Bayesian A/B**，别纯 frequentist p-value。

## 九、成本观测

### 9.1 多维度计费

每条 trace 至少打上：

```
user_id, tenant_id, feature, model, region, experiment_variant
```

在 Langfuse 里直接 group by；或把 usage 导出到 ClickHouse / BigQuery 自己切。

### 9.2 缓存命中分析

仪表盘必看：

- **Prefix cache hit rate**（引擎侧，vLLM/SGLang）；
- **Prompt cache hit rate**（API 侧，OpenAI/Anthropic/DeepSeek）；
- **Semantic cache hit rate**（网关侧，GPTCache 等）。

三者独立，都能省钱；目标：总 input cost 下降 30–60%。

### 9.3 异常花费告警

```
alert: CostSpike
expr:  sum(rate(llm_cost_usd[5m])) by (feature)
       > 3 * avg_over_time(sum(rate(llm_cost_usd[5m])) by (feature)[1h:5m])
for: 10m
```

并加速率限（见 [22-llm-gateway](https://quant67.com/post/llm-infra/22-llm-gateway/22-llm-gateway.html)）——观测发现、网关止损，是标配组合。

## 十、GPU 与推理引擎观测

### 10.1 DCGM Exporter

NVIDIA 官方 Prometheus exporter，部署一个 DaemonSet 即可采全节点 GPU 指标：

```
apiVersion: apps/v1
kind: DaemonSet
metadata: { name: dcgm-exporter, namespace: monitoring }
spec:
  template:
    spec:
      containers:
      - name: dcgm-exporter
        image: nvcr.io/nvidia/k8s/dcgm-exporter:3.3.5-3.4.1-ubuntu22.04
        ports: [{ containerPort: 9400, name: metrics }]
        securityContext: { capabilities: { add: ["SYS_ADMIN"] } }
```

关键指标：

```
DCGM_FI_PROF_SM_ACTIVE              # SM 实际活跃比例（真利用率）
DCGM_FI_PROF_PIPE_TENSOR_ACTIVE     # Tensor Core 利用
DCGM_FI_DEV_FB_USED / FB_FREE       # HBM
DCGM_FI_DEV_POWER_USAGE             # 功耗
DCGM_FI_PROF_NVLINK_TX/RX_BYTES     # NVLink 流量
DCGM_FI_DEV_ECC_DBE_VOL_TOTAL       # 双比特 ECC（故障预警)
```

### 10.2 vLLM / SGLang 指标

**vLLM** 在 `/metrics` 暴露 Prometheus：

```
vllm:num_requests_running
vllm:num_requests_waiting
vllm:gpu_cache_usage_perc
vllm:time_to_first_token_seconds (histogram)
vllm:time_per_output_token_seconds (histogram)
vllm:e2e_request_latency_seconds
vllm:prompt_tokens_total
vllm:generation_tokens_total
vllm:prefix_cache_hit_rate
```

**SGLang** 类似，另提供 RadixAttention 命中：

```
sglang:cache_hit_rate
sglang:running_requests
sglang:token_usage
sglang:schedule_overhead
```

### 10.3 Grafana 面板模板

一个推理集群的”四行一屏”：

1. **流量行**：RPS / tokens-in / tokens-out / 队列深度；
2. **延迟行**：TTFT p50/p95/p99、TPOT p50/p95、E2E；
3. **资源行**：SM active、HBM used、KV cache %、prefix hit %；
4. **成本行**：$/1k tokens、按 model/tenant 分桶。

社区模板：DCGM 官方 dashboard + vLLM 官方 dashboard（GitHub `vllm-project/vllm` 的 `examples/production_monitoring`）。

### 10.4 深度性能剖析：Nsight

指标发现异常后，需要**剖析**：

- **Nsight Systems (nsys)**：时间线，看 kernel 调度、NCCL 通信气泡、CPU-GPU overlap；
    
    ```
    nsys profile -o vllm_trace --trace=cuda,nvtx,osrt python -m vllm.entrypoints.openai.api_server ...
    ```
    
- **Nsight Compute (ncu)**：单 kernel 占用、cache miss、stall reason；
    
    ```
    ncu --set full -o kernel_report ./my_fused_kernel
    ```
    
- **PyTorch Profiler + Chrome trace**：Python 级热点；
    
- **TensorBoard / W&B**：训练侧更常用。
    

组合拳：**Prometheus 告警 → nsys 抓一段 → ncu 钻到 kernel**。

## 十一、Agent 观测

### 11.1 特有信号

- **轮次（steps）**：每次 user turn 内部的 thought-action-observation 次数；
- **工具成功率**：每个 tool 的 `success / total`，分 HTTP 错、参数错、语义错；
- **卡死 / 环**：连续 N 步调用同一工具同一参数；
- **计划偏移**：Planner 输出的 plan 和实际执行的 action 序列相似度；
- **成本/轮次**：一个 Agent session 总 token / 总工具费。

### 11.2 死循环检测

```
def loop_detector(history, window=4):
    sig = [(a.tool, hash(str(a.args))) for a in history[-window*2:]]
    half = len(sig)//2
    return sig[:half] == sig[half:]  # 后半和前半完全相同 -> 疑似环
```

检测到立刻打断并记 `agent.loop_detected=true`。

### 11.3 Replay

Trace 必须包含：每一步的 `input / output / tool args / tool result / model / params / seed`。AgentOps、LangSmith、Langfuse 都有 replay：点一个失败 session，加载到 playground 里**按原样重跑或改一步重跑**，定位问题比 printf 高效十倍。

### 11.4 多 Agent 拓扑

CrewAI、AutoGen、LangGraph 这类多 Agent 框架下，观测要能展示：

- Agent 间”消息图”（谁发给谁、哪一步触发）；
- 每个 Agent 的子 LLM 成本与延迟归属；
- 角色划分是否按预期生效（例如 “critic” 是否真的在打分）。

LangGraph 的 state machine 天然适合 trace 成一棵树，Langfuse 的 session 视图能覆盖；复杂场景下 AgentOps + 自定义 dashboard 更清晰。

## 十二、日志合规

### 12.1 法规一览

- **EU GDPR**：个人数据，“收集最小化”、“目的限定”、“可被遗忘”；数据泄露 72 小时上报。
- **中国《个人信息保护法》**：敏感个人信息需单独同意；跨境传输需安全评估 / 标准合同。
- **中国《生成式人工智能服务管理暂行办法》**（国家网信办，2023.8 施行）：
    - 要求**保存用户输入、模型输出日志至少 6 个月**；
    - 内容安全审核义务；
    - 训练数据合法性义务；
    - 面向公众提供需备案。
- **美国行业法**：HIPAA（医疗）、FINRA（金融）、FERPA（教育）有特殊留存与脱敏要求。

### 12.2 工程落地要点

1. 日志分级：**结构化指标永久留**、**完整 prompt / completion 按法规 TTL**（中国公众服务建议 ≥ 6 个月，企业内部按行业判断）。
2. **数据分区**：按区域部署观测后端（中国数据留中国）。
3. **审计日志**：谁在什么时候访问了哪个 trace，自身要审计。
4. **“可遗忘”**：提供按 `user_id` 级联删除能力——Langfuse、LangSmith 都有相应 API。
5. **安全审核记录**：拒答、命中黑名单的请求单独入审计库，便于备案自检。

## 十三、代码实战

### 13.1 Langfuse self-host + OpenAI SDK

```
# 1. 起 self-host（生产建议 k8s helm）
git clone https://github.com/langfuse/langfuse && cd langfuse
docker compose up -d

# 2. 登录 http://localhost:3000 拿 PK / SK
export LANGFUSE_PUBLIC_KEY=pk-...
export LANGFUSE_SECRET_KEY=sk-...
export LANGFUSE_HOST=http://localhost:3000
```

最小侵入集成（drop-in）：

```
from langfuse.openai import openai  # 只改这一行
from langfuse.decorators import observe

@observe()
def answer(q: str, user_id: str):
    docs = retrieve(q)
    resp = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "你是客服，请基于 context 回答。"},
            {"role": "user", "content": f"context:\n{docs}\n\n问:{q}"},
        ],
        metadata={"user_id": user_id, "feature": "cs_chat", "variant": "v2"},
    )
    return resp.choices[0].message.content

@observe()
def retrieve(q):
    # 这里会自动成为 answer 的子 span
    return vectorstore.search(q, k=5)
```

附带用户反馈回写：

```
from langfuse import Langfuse
lf = Langfuse()
lf.score(trace_id=trace_id, name="thumb", value=1, comment="有帮助")
```

### 13.2 OpenTelemetry instrument vLLM

vLLM 0.6+ 自带 OTel 支持（`--otlp-traces-endpoint`）；也可以用 OpenLLMetry 在客户端侧一把梭。

服务端：

```
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen3-32B-Instruct \
  --enable-prefix-caching \
  --otlp-traces-endpoint http://otel-collector:4317 \
  --collect-detailed-traces model,worker
```

客户端（OpenLLMetry 自动 instrument）：

```
from traceloop.sdk import Traceloop
from openai import OpenAI

Traceloop.init(
    app_name="my-llm-app",
    api_endpoint="http://otel-collector:4318",  # OTLP HTTP
    disable_batch=False,
)

client = OpenAI(base_url="http://vllm:8000/v1", api_key="none")
resp = client.chat.completions.create(
    model="qwen3-32b",
    messages=[{"role":"user","content":"写一段 quicksort"}],
    stream=True,
)
for chunk in resp:
    ...
```

OTel Collector 把 `gen_ai.*` trace 同时吐到：

- Tempo / Jaeger（可视化）；
- Langfuse OTel ingest（业务面板）；
- ClickHouse / BigQuery（自定义分析）。

Collector 片段：

```
receivers:
  otlp: { protocols: { grpc: {}, http: {} } }
processors:
  batch: {}
  filter/pii:
    traces:
      span:
        - 'attributes["gen_ai.prompt.0.content"] != nil'
  transform/mask:
    trace_statements:
      - context: span
        statements:
          - replace_pattern(attributes["gen_ai.prompt.0.content"],
              "1[3-9][0-9]{9}", "<PHONE>")
exporters:
  otlphttp/langfuse:
    endpoint: http://langfuse:3000/api/public/otel
    headers: { Authorization: "Basic ${LANGFUSE_AUTH}" }
  otlp/tempo:
    endpoint: tempo:4317
service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [transform/mask, batch]
      exporters: [otlphttp/langfuse, otlp/tempo]
```

### 13.3 Prometheus 抓 vLLM + DCGM

```
scrape_configs:
  - job_name: vllm
    static_configs: [{ targets: ["vllm-0:8000","vllm-1:8000"] }]
    metrics_path: /metrics
  - job_name: dcgm
    kubernetes_sd_configs: [{ role: pod }]
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        regex: dcgm-exporter
        action: keep
```

告警示例：

```
groups:
- name: llm
  rules:
  - alert: HighTTFT
    expr: histogram_quantile(0.95,
           sum by (le,model) (rate(vllm:time_to_first_token_seconds_bucket[5m]))) > 2
    for: 10m
    annotations: { summary: "TTFT p95 > 2s on {{$labels.model}}" }
  - alert: KVCacheNearFull
    expr: vllm:gpu_cache_usage_perc > 0.9
    for: 5m
  - alert: GPUECCErrors
    expr: increase(DCGM_FI_DEV_ECC_DBE_VOL_TOTAL[1h]) > 0
    annotations: { summary: "GPU {{$labels.gpu}} 出现双比特 ECC，立即隔离" }
```

### 13.4 LLM-as-Judge 在线采样

```
import random
from langfuse import Langfuse
lf = Langfuse()

def online_judge(trace_id, question, context, answer, judge_model="gpt-4o"):
    if random.random() > 0.01:  # 1% 采样
        return
    score = call_judge(judge_model, question, context, answer)  # 返回 0-1
    lf.score(trace_id=trace_id, name="groundedness", value=score)
    if score < 0.4:
        lf.event(trace_id=trace_id, name="low_groundedness", level="WARNING")
```

## 十四、一个典型排障故事

真实场景串起来看——“周一早上客服机器人变慢”：

1. **Grafana 红灯**：`TTFT p95` 从 0.6 s 冲到 3.5 s，同时 `error_rate` 平稳，所以不是模型返回错，而是”慢”。
2. **拆分维度**：按 model 看，只有 `qwen3-32b` 变差；按 tenant 看，`tenant-A` 占突增 80%；按 region 看集中在单机房。
3. **引擎指标**：`vllm:num_requests_waiting` 堆积、`gpu_cache_usage_perc` 96%、`prefix_cache_hit_rate` 从 55% 掉到 8%、`DCGM_FI_PROF_SM_ACTIVE` 仍然很高——不是 GPU 闲着，而是在”徒劳”地重复 prefill。
4. **结论雏形**：tenant-A 换了新 system prompt，prefix 变了导致缓存全失效，带来 prefill 风暴，KV cache 被挤爆，后续请求排队。
5. **Langfuse 验证**：按 `tenant=A` 过滤 trace，diff 两个版本 system prompt，果然周末上线了新版；通过 [LLM 网关](https://quant67.com/post/llm-infra/22-llm-gateway/22-llm-gateway.html) 的 prompt 模板统一化，并把变动的部分挪到尾部，恢复 prefix 复用。
6. **复盘**：给 Prompt 变更加上”prefix cache hit 回归门槛”——离线 eval 跑 1000 条典型对话，命中率低于基线 10% 不允许发布；同时告警里加上 `prefix_cache_hit_rate` 指标，下次 5 分钟内就能发现。

每一步都依赖不同层的可观测性：业务层告警→基础设施层指标→调用层 trace→Prompt 版本系统。没有任一层都排不出来——这就是”四层观测模型”的价值。

## 十五、国内外厂商生态速览

不同云厂、模型厂对”自带观测”做了不同程度的封装，选型时需要了解边界。

### 15.1 国际

- **OpenAI**
    - Platform Dashboard：usage、cost、rate limit；
    - Responses API / Assistants 自带 `trace_id`，可以关联内部 tool call；
    - 企业版有 “Admin API” 读取组织级用量，审计事件订阅。
- **Anthropic**
    - Console 有 prompt caching 命中统计；
    - 通过 `cache_control` 决定缓存块，观测侧可以逐块看命中率；
    - Claude Code / Bedrock 集成侧都会透出 `usage.cache_read_input_tokens`。
- **Google Vertex AI**
    - Cloud Monitoring 自动采集 model latency、token count、error rate；
    - 与 Cloud Trace 打通，一个请求可在 Trace UI 看完整 RPC 树；
    - `gen_ai.*` OTel 语义已在 Vertex SDK 开启。
- **AWS Bedrock**
    - CloudWatch Metrics：`InvocationLatency`、`InputTokenCount`、`OutputTokenCount`；
    - Bedrock Model Invocation Logging 可把 prompt/completion 投递到 S3 / CloudWatch Logs；
    - Guardrails 拦截事件单独度量。
- **Azure OpenAI**
    - Application Insights + OpenTelemetry 已原生支持 Semantic Kernel、AutoGen；
    - Content Safety 审核日志独立，可按策略归档。

### 15.2 中国

- **阿里云 PAI / 百炼（DashScope）**
    - “模型观测”模块：模型调用量、RT、失败率、token 用量；
    - 和 SLS（日志服务）打通，可长期存 prompt/completion；
    - DashScope SDK 默认把 `request_id` 打回客户端，便于关联。
- **火山引擎方舟**
    - 控制台自带调用明细、按模型/应用维度成本；
    - 与字节内部的 AppMetrics/TCE 体系贯通，企业版支持 OTel 导出。
- **百度千帆**
    - “AI 原生应用开发平台”里有 trace 视图，Agent 调用可视化；
    - 千帆 ModelBuilder 对接自家 Prometheus 指标。
- **腾讯混元 / TI-ONE**
    - 云监控 + CLS（日志服务）组合，有 token 维度计费看板；
- **DeepSeek / 月之暗面 Kimi / 智谱 GLM / MiniMax / 百川**
    - 多数仅在 Dashboard 展示 usage 与 rate，生产观测仍需自己套 Langfuse / LangSmith / 自研。

结论：**厂商 Dashboard 看”账单和健康”够用，真要排障还是得在应用侧独立上一套 trace**。

## 十六、与训练侧观测的对比

本系列前半在训练篇（[06-并行](https://quant67.com/post/llm-infra/06-parallelism/06-parallelism.html)、[07-Megatron-DeepSpeed](https://quant67.com/post/llm-infra/07-megatron-deepspeed/07-megatron-deepspeed.html)、[10-Checkpoint 与容错](https://quant67.com/post/llm-infra/10-checkpoint-fault/10-checkpoint-fault.html)）里提到过训练观测，和在线观测是两套体系：

  
|关注点|训练侧|在线推理 / 应用侧|
|---|---|---|
|迭代周期|一个 job 几天~几周|每秒数百请求|
|关键指标|loss、gradient norm、MFU、TFLOPS、GPU 健康|TTFT/TPOT、QPS、cost、quality|
|工具|W&B、TensorBoard、MLflow、SwanLab|Langfuse、LangSmith、Phoenix、APM|
|失败模式|发散、NaN、节点坏、通信卡顿|幻觉、越权、成本爆炸、延迟尖刺|
|数据产物|Checkpoint、log|Trace、Prompt 版本、Eval score|

两侧共用的基础设施是 **GPU 遥测**（DCGM）、**分布式 tracing**（OTel）、**告警总线**（Alertmanager）。成熟团队会搭一套统一的”AI Observability Platform”，训练 + 推理共用后端，只在前端看板区分语义。

## 十七、前沿方向

### 17.1 自动根因分析（AIOps for AI）

- 用 LLM 看 trace，直接给工程师”这次失败可能是 retriever 返回无关文档 + 模型直接胡编”这类人话结论；
- Arize、Dynatrace、Datadog 都在试；开源侧 Langfuse 的 “trace summary” beta 已上线。
- 进一步还可以把”常见故障模式”沉淀成知识库：token 暴涨、TTFT 尖刺、Tool 反复失败、Agent 打转……由 LLM 基于 trace 主动匹配。

### 17.2 Trace + Weights 联合剖析

- 训练框架（Megatron、Mcore）把 step 级 loss、grad norm 写成 OTel metric，与推理 trace 使用同一套 label 体系（model、version、tenant），这样当线上质量回退时可以快速跳转到对应 checkpoint 的训练曲线；
- W&B Weave + W&B Models 是这个方向的商业样板；国内 SwanLab 也开始提供类似打通能力。

### 17.3 LLM-Native 评估

- **Pairwise judging with Elo**：模型对战，Arena 式实时排名；LMSys Chatbot Arena 的思路正被内化到企业私有评估平台。
- **Preference pair 学习回流**：把人工偏好喂回 DPO 管线，形成”观测 → 偏好 → 再训练”闭环；配合 [09-RLHF 流水线](https://quant67.com/post/llm-infra/09-rlhf-pipeline/09-rlhf-pipeline.html)。
- **Self-consistency 作为不确定度**：对同一 prompt 多采样比一致率，低一致率自动触发人工复核；近似一种零成本的”校准”信号。

### 17.4 边缘 / On-device 观测

手机 / 端侧模型（Apple Intelligence、小米 MiLM、vivo BlueLM、Phi-3-mini）兴起后，观测要：

- 离线采集 + 周期性回传；
- 严格匿名化（端侧没有 tenant，用户就是个人）；
- 电量、内存、温度成为新的一等指标。

### 17.5 跨模态

图像、语音、视频生成的观测目前远不如纯文本成熟：

- **Sora / 可灵 / 海螺 / Runway**：关心”生成是否合规”、“显存占用峰值”、“生成长度/质量曲线”；
- **TTS / ASR**：关心 RTF（Real-Time Factor）、字错率（WER / CER）；
- OTel 的 `gen_ai.*` 正在扩展 `media.*` 语义字段。

## 十八、落地清单

按规模从小到大分三档推进，避免一次上全套。

### 18.1 MVP（1 人周）

- 接一个托管观测后端（Langfuse Cloud 或 LangSmith 免费额度）；
- SDK 一行集成，把所有 LLM 调用流入；
- 打上 `user_id / feature` 两个 tag；
- 建一个”📈 日活 / 成本 / 平均 latency”面板。

### 18.2 生产级（1 人月）

- 指标层：TTFT / TPOT / E2E、tokens、cache hit、GPU（DCGM）。
- 引擎层：vLLM/SGLang `/metrics` 接入 Prometheus。
- Trace 层：SDK 选一套（OpenLLMetry / Langfuse / LangSmith），后端收 OTel。
- 成本层：trace 打 `user_id / feature / variant`；cache 分析面板。
- 质量层：在线 1% 采样 LLM-as-Judge；离线 golden set + promptfoo/RAGAS CI。
- Agent 层：轮次、工具成功率、环检测、replay。
- 合规层：PII mask、TTL 分级、区域部署、审计日志、可遗忘 API。
- 告警层：TTFT、队列深度、KV cache 满、成本 spike、ECC。
- 回归闸门：prompt/模型变更需通过冻结集 + 滚动集评估。

### 18.3 平台化（跨团队）

- 统一观测 Collector（OTel），多后端 fan-out；
- 统一 tag schema（`tenant / user / feature / model / variant / region`）；
- 自助化 dashboard 与告警模板库；
- Prompt/模型发布流水线与 Eval CI 强绑定；
- 合规审计 / “可遗忘” API 自动化；
- 训练侧指标与推理侧指标同 schema，实现”线上质量回退 → 训练曲线”一键跳转。

## 参考资料

1. OpenTelemetry Semantic Conventions for GenAI：[https://opentelemetry.io/docs/specs/semconv/gen-ai/](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
2. OpenInference Spec（Arize）：[https://github.com/Arize-ai/openinference](https://github.com/Arize-ai/openinference)
3. OpenLLMetry / Traceloop SDK：[https://github.com/traceloop/openllmetry](https://github.com/traceloop/openllmetry)
4. Langfuse：[https://langfuse.com/docs](https://langfuse.com/docs)
5. LangSmith：[https://docs.smith.langchain.com/](https://docs.smith.langchain.com/)
6. Helicone：[https://docs.helicone.ai/](https://docs.helicone.ai/)
7. Arize Phoenix：[https://docs.arize.com/phoenix](https://docs.arize.com/phoenix)
8. Weights & Biases Weave：[https://wandb.me/weave](https://wandb.me/weave)
9. AgentOps：[https://docs.agentops.ai/](https://docs.agentops.ai/)
10. Pezzo：[https://docs.pezzo.ai/](https://docs.pezzo.ai/)
11. Lunary：[https://lunary.ai/docs](https://lunary.ai/docs)
12. NVIDIA DCGM Exporter：[https://github.com/NVIDIA/dcgm-exporter](https://github.com/NVIDIA/dcgm-exporter)
13. vLLM Production Monitoring 示例：[https://github.com/vllm-project/vllm/tree/main/examples/online_serving](https://github.com/vllm-project/vllm/tree/main/examples/online_serving)
14. SGLang Metrics：[https://docs.sglang.ai/](https://docs.sglang.ai/)
15. RAGAS：[https://docs.ragas.io/](https://docs.ragas.io/)
16. DeepEval：[https://docs.confident-ai.com/](https://docs.confident-ai.com/)
17. Giskard：[https://docs.giskard.ai/](https://docs.giskard.ai/)
18. promptfoo：[https://www.promptfoo.dev/docs/](https://www.promptfoo.dev/docs/)
19. 国家网信办《生成式人工智能服务管理暂行办法》：[http://www.cac.gov.cn/2023-07/13/c_1690898327029107.htm](http://www.cac.gov.cn/2023-07/13/c_1690898327029107.htm)
20. GDPR 条款全文：[https://gdpr-info.eu/](https://gdpr-info.eu/)

---

**上一篇**：[22-大模型网关](https://quant67.com/post/llm-infra/22-llm-gateway/22-llm-gateway.html) **下一篇**：[24-成本、合规与安全](https://quant67.com/post/llm-infra/24-cost-security/24-cost-security.html)

## 同主题继续阅读

把当前热点继续串成多页阅读，而不是停在单篇消费。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】17：RAG 工程全景](https://quant67.com/post/llm-infra/17-rag-engineering/17-rag-engineering.html)

从文档解析、切片、嵌入、索引、检索、重排到生成与评估，系统梳理 RAG 的工程流水线、进阶范式与国内外生态

2026-04-22 · architecture / ai-infra

### [大模型基础设施工程](https://quant67.com/post/llm-infra/index.html)

面向中国工程团队的大模型基础设施系列。从 GPU/CUDA/互联、训练框架与 3D 并行、vLLM/SGLang 推理引擎、量化与推测解码、RAG/Agent 到服务化、网关、可观测性与安全合规，覆盖 LLMOps 全链路。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】11：推理引擎基础](https://quant67.com/post/llm-infra/11-inference-basics/11-inference-basics.html)

从 Prefill/Decode 两阶段、KV Cache、Continuous Batching 到 PD 分离，系统讲清楚大模型推理的工程基础。

2026-04-22 · architecture / ai-infra

### [【大模型基础设施工程】09：RLHF 与对齐流水线](https://quant67.com/post/llm-infra/09-rlhf-pipeline/09-rlhf-pipeline.html)

从 SFT、奖励模型到 PPO、DPO、GRPO 的完整对齐流水线工程实践，覆盖 OpenAI o1、DeepSeek-R1 等推理模型的 RL 路线与主流框架选型。