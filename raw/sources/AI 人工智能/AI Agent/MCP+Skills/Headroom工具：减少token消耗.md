原文： https://dev.to/arshtechpro/headroom-cut-your-llm-token-usage-by-up-to-95-without-changing-your-answers-5g06

Headroom 是一款面向 AI Agent、LLM 流水线的开源上下文压缩中间件，部署在应用与大模型服务商之间，**在内容送入 LLM 前自动压缩，最高减少 95% Token 消耗，且完全可逆、不降低模型输出质量**，专门解决工具返回数据、日志、RAG 分片、对话历史造成的上下文膨胀、调用成本高昂问题。

项目开源地址：
https://github.com/chopratejas/headroom

## 一、核心压缩架构与多策略分流

内置`ContentRouter`自动识别内容类型，匹配专属压缩算法，原始内容本地永久存储，LLM 可按需调取完整原文，属于无损可逆压缩：

1. **SmartCrusher**：JSON / 数组 / 嵌套结构化数据专用压缩；
2. **CodeCompressor**：基于 AST 语法树压缩多编程语言代码（Python/JS/Go/Java 等）；
3. **Kompress-base**：HuggingFace 专用模型，处理自然文本、Agent 运行日志；
4. **CacheAligner**：优化提示词前缀，稳定 KV 缓存，大幅提升缓存命中率；
5. **CCR（内容压缩检索）**：原文本地留存，支持模型按需还原完整数据。

## 二、实测压缩效果（真实 Agent 业务负载）

表格

|业务场景|压缩前 Token|压缩后 Token|Token 节省比例|
|---|---|---|---|
|代码检索（100 条结果）|17765|1408|92%|
|SRE 故障日志排查|65694|5118|92%|
|GitHub 工单分类处理|54174|14761|73%|
|代码库全局浏览|78502|41254|47%|

精度测试：在 GSM8K 数学、TruthfulQA、SQuAD、工具调用 BFCL 等标准数据集评测，压缩后模型准确率持平甚至小幅提升，原因是过滤冗余噪声，模型更容易抓取关键信号。

## 三、三种极简接入方案，适配各类开发环境

### 方案 1：一键包装现有 Agent（零代码改动）

仅一行命令自动拦截 Claude Code、Cursor、Copilot 等工具流量：

plaintext

```
pip install "headroom-ai[all]"
headroom wrap claude
```

### 方案 2：本地代理 Proxy

启动本地端口代理，只需修改 SDK 请求地址，不限编程语言、框架：

plaintext

```
headroom proxy --port 8787
```

### 方案 3：内嵌代码库（精细控制）

提供 Python/TS 原生 API，原生兼容 Anthropic SDK、LangChain、Vercel AI SDK，直接嵌入业务代码实现压缩逻辑。

## 四、特色高阶功能

1. **MCP 服务端模式**
    
    执行`headroom mcp install`，对外暴露`headroom_compress/retrieve/stats`三个 MCP 工具，适配 Claude Desktop 等 MCP 客户端，集成进 Agent 工具循环。
2. **跨 Agent 共享内存**
    
    多 Agent 共用压缩上下文存储，自动去重，避免多智能体流水线重复传输相同内容。
3. **自动学习命令`headroom learn`**
    
    解析失败会话日志，提炼错误经验，自动写入`CLAUDE.md`/`AGENTS.md`配置，规避同类问题重复发生。
4. **数据统计`headroom stats`**
    
    统计累计 Token 节省量、各类内容压缩比例，直观展示成本优化收益。

## 五、适用 / 不适用人群

### 推荐使用

1. 高频使用 Claude Code、Cursor 等 AI 编程工具，有大额 Token 账单；
2. 业务存在大量工具返回 JSON、长日志、批量 RAG 检索的 LLM 流水线；
3. 多 Agent 协作场景，需要统一共享上下文；
4. 要求压缩后可完整还原原始数据，不能粗暴截断文本。

### 谨慎使用

1. 仅依赖厂商原生上下文管理、无大量冗余输入；
2. 沙箱 / 受限环境，无法运行本地进程；
3. 单次简单问答、上下文几乎无膨胀的轻量场景。

## 六、基础安装与常用命令

Python：`pip install "headroom-ai[all]"`

Node/TS：`npm install headroom-ai`

核心指令：包装 Agent、启动代理、安装 MCP、查看节省数据、自动学习故障经验。
