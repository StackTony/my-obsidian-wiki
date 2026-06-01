
## Graphify
Graphify是一个将任意语料（代码、文档、论文、图片）转化为持久化、可查询、带审计轨迹的知识图谱引擎，**不只限于代码**。

使用指导：
https://zhuanlan.zhihu.com/p/2031821942278369991


## GitNexus
GitNexus主要识别代码，把代码仓库转化为可交互的知识图谱 

github仓地址：
https://github.com/abhigyanpatwari/GitNexus

使用指导：
https://zhuanlan.zhihu.com/p/2034264951842419611


## 1 核心分析命令
###  1.1 推荐索引（启用语义搜索）

```text
gitnexus analyze --embeddings
```
加上 `--embeddings` 参数后，GitNexus 会用本地 Hugging Face 嵌入模型为每个 symbol 生成向量。这样 `query()` 工具就能做真正的自然语言语义搜索，而不只是关键词匹配。

整个过程**仍然零 Token、零 LLM 调用**，只是索引时间会多 30%–100%（取决于 CPU/GPU 性能）。

### 1.2 完整索引（最推荐）

```text
gitnexus analyze --embeddings --skills --verbose
```

这是日常使用的推荐配置：
- `--embeddings` 启用语义搜索
- `--skills` 把 Leiden 算法识别的每个功能社区生成独立的 SKILL.md，写到 `.claude/skills/generated/<area>/`，让 Claude Code 在不同模块工作时拿到精准的局部架构上下文
- `--verbose` 打印被跳过的文件，方便诊断索引覆盖率

###  1.3 验证索引状态

```text
gitnexus list      # 查看所有已索引的仓库
gitnexus status    # 查看当前仓库索引状态
```


## 2. 完整使用方式

### 2.1 CLI 命令

#### 2.1.1 基础命令

|命令|描述|示例|
|---|---|---|
|`gitnexus setup`|一次性设置：配置 MCP 用于 Cursor、Claude Code 等|`gitnexus setup`|
|`gitnexus analyze [path]`|索引仓库（完整分析）|`gitnexus analyze .`|
|`gitnexus serve`|启动本地 HTTP 服务器用于 Web UI 连接|`gitnexus serve`|
|`gitnexus mcp`|启动 MCP 服务器（stdio）- 服务所有索引的仓库|`gitnexus mcp`|
|`gitnexus list`|列出所有索引的仓库|`gitnexus list`|
|`gitnexus status`|显示当前仓库的索引状态|`gitnexus status`|
|`gitnexus clean`|删除当前仓库的 GitNexus 索引|`gitnexus clean`|

#### 2.1.2 高级命令

|命令|描述|示例|
|---|---|---|
|`gitnexus wiki [path]`|从知识图谱生成仓库 wiki|`gitnexus wiki .`|
|`gitnexus augment <pattern>`|用知识图谱上下文增强搜索模式|`gitnexus augment "user authentication"`|
|`gitnexus query <search_query>`|搜索与概念相关的执行流|`gitnexus query "user login flow"`|
|`gitnexus context [name]`|代码符号的 360 度视图|`gitnexus context "validateUser"`|
|`gitnexus impact <target>`|分析修改符号的影响范围|`gitnexus impact "validateUser"`|
|`gitnexus cypher <query>`|对知识图谱执行原始 Cypher 查询|`gitnexus cypher "MATCH (f:Function) RETURN f.name LIMIT 10"`|

### 2.2 Web 界面

1. 访问 [https://gitnexus.vercel.app](https://gitnexus.vercel.app/)
2. 粘贴 GitHub 仓库链接或上传 ZIP 文件
3. 等待索引完成（完全在浏览器中运行）
4. 探索知识图谱，与 AI 对话

**限制**：浏览器内存限制，适合 5000 文件以下项目

### 2.3 本地后端模式

1. 在仓库目录中运行 `gitnexus serve`
2. 访问 [http://localhost:4747](http://localhost:4747/)
3. Web UI 会自动连接到本地服务器

## 3. MCP 协议提供的能力

GitNexus 通过 MCP 协议向 AI 助手提供以下工具：

### 3.1 核心工具

|工具名|描述|使用场景|
|---|---|---|
|`list_repos`|列出所有索引的仓库|多仓库环境中选择目标仓库|
|`query`|查询与概念相关的执行流|理解代码如何协同工作，查找相关功能|
|`context`|代码符号的 360 度视图|深入了解特定符号的调用关系和参与的执行流|
|`impact`|分析修改符号的影响范围|代码重构前评估潜在影响|
|`detect_changes`|分析未提交的 git 变更影响|提交前审查，PR 准备|
|`rename`|多文件协调重命名|安全地重命名函数、类、方法等|
|`cypher`|对知识图谱执行 Cypher 查询|复杂的结构化查询|

### 3.2 API 相关工具

|工具名|描述|使用场景|
|---|---|---|
|`route_map`|显示 API 路由映射|理解 API 消费模式，查找孤立路由|
|`shape_check`|检查 API 路由的响应形状|检测 API 响应与消费者期望之间的不匹配|
|`api_impact`|API 路由处理程序的变更影响报告|修改 API 路由前的影响评估|

### 3.3 仓库组工具

| 工具名               | 描述             | 使用场景                     |
| ----------------- | -------------- | ------------------------ |
| `group_list`      | 列出所有配置的仓库组     | 发现组以进行同步                 |
| `group_sync`      | 为组重建合同注册表      | 更改 group.yaml 或重新索引成员仓库后 |
| `group_contracts` | 检查组的合同和交叉链接    | 同步后调试跨仓库链接               |
| `group_query`     | 在组的所有仓库中运行查询   | 跨整个产品组的语义/混合搜索           |
| `group_status`    | 报告组中每个仓库的索引陈旧度 | 组同步前或代理应刷新索引时            |

## 4. graphify和gitnexus的区别：
https://cloud.tencent.com/developer/article/2658828

#### Graphify 更偏“知识整合”，GitNexus 更偏“工程作战”
**•Graphify** 的方法论核心，是把更多分散、隐性的知识连接起来。
**•GitNexus** 的方法论核心，是把复杂代码关系预先计算好，降低 agent 在真实工程任务中的认知遗漏

---
#### Graphify 明确区分了三类关系：
**•EXTRACTED**：直接从源材料中抽取
**•INFERRED**：基于上下文的合理推断
**•AMBIGUOUS**：有歧义，需要复核
这个设计很重要。因为它让知识图谱不只是“更丰富”，还尽量做到**更诚实**。

#### Graphify 更适合哪些场景？
如果你处理的是下面这类问题，Graphify 会很有吸引力：
•项目资料很分散，不止有源码
•想把论文、设计稿、截图、会议录屏等一起纳入知识体系
•想让 AI 在长期会话中复用结构化上下文，而不是反复全文扫描
•更关心“理解一个复杂知识域”，而不只是“改一段代码”
•希望用统一图谱组织研究材料、项目文档和实现细节
换句话说，**Graphify 偏“认知整合”**，它把项目看成一个多源知识集合，而不是单一代码仓库。

---
#### GitNexus核心目标
目标很直接：**把代码仓库索引成知识图谱，再通过 CLI、MCP 和智能工具能力，把这些结构化结果直接喂给 AI agent，让它在真实开发中更少漏信息、更少盲改代码。**
GitNexus 的仓库描述里有一句话很关键：它不是只帮助你“理解代码”，而是帮助你“分析代码”。

#### GitNexus 更适合哪些场景？
如果你的目标是这些，GitNexus 会更对路：
•让 Cursor / Claude Code / Codex 等 agent 在大仓库里少走弯路
•做重构前的影响分析
•踪跨模块执行流程
•在多仓库场景里管理服务间契约与关系
•希望基于 MCP，把本地索引长期接入自己的开发工具链
•更强调开发可靠性，而不是单纯知识沉淀
一句话概括：**GitNexus 偏“工程执行”**，它的核心是让 agent 在实际开发里更稳。