github仓地址：
https://github.com/microsoft/graphrag

这是微软官方开源的 **GraphRAG** 仓库（2024-07-02 发布，MIT 协议），核心是**用知识图谱替代纯文本块做 RAG**，解决传统 RAG 在**多跳推理、全局主题、跨实体关系**上的短板。下面从定位、架构、核心能力、使用方式、关键差异、成本与风险几方面讲清楚。

---

## 一、项目定位与核心价值
- **全称**：Graph Retrieval-Augmented Generation（图谱增强检索生成）
- **核心思想**：不只是切文本+向量检索，而是**先把全文本建成知识图谱（实体–关系–属性）**，再在图上做检索与推理
- **解决传统 RAG 痛点**：
  1. 信息碎片化，跨文档关联弱
  2. 多跳推理能力差
  3. 难以回答“全局主题/核心观点”类问题

---

## 二、整体架构：索引阶段 + 查询阶段
### 1）索引阶段（离线，最耗时）
输入：一堆文档（.txt/.md 等）
输出：知识图谱 + 社区摘要 + 向量索引

关键步骤：
1. **Text Chunking**：文本切块（和普通 RAG 类似）
2. **Entity & Relation Extraction**：LLM 提取实体（人/事/物/组织）和关系（A–关系→B）
3. **Build Graph**：把三元组拼成图（节点=实体，边=关系）
4. **Community Detection**：用 **Leiden 算法**做社区聚类（稠密节点归为一类）
5. **Community Summarization**：LLM 给每个社区生成摘要（从高层主题到低层细节）
6. **Embedding & Index**：实体/社区/摘要向量化，建混合索引

### 2）查询阶段（在线）
提供两种核心查询模式：
- **Local Search（局部）**：查具体事实、实体关系、细节（如“某人的职位”）
- **Global Search（全局）**：查主题、趋势、核心观点（如“全文核心主题是什么”）
- （新版）**DRIFT Search**：跨社区、多跳推理的复杂查询

---

## 三、仓库核心内容（目录结构）

```
microsoft/graphrag
├── graphrag/              # 核心库
│   ├── indexer/           # 索引流水线（抽实体、建图、聚类、摘要）
│   ├── query/             # 查询引擎（Local/Global/DRIFT）
│   ├── llm/               # LLM 适配器（OpenAI/Azure/本地模型）
│   ├── vector_store/      # 向量存储（默认内置，可接外部）
│   └── prompt/            # 提示词模板（可自定义）
├── samples/                # 示例数据+notebook
├── docs/                   # 官方文档
├── .env.example            # 环境变量模板（API_KEY等）
└── settings.yaml           # 主配置文件
```

---

## 四、快速上手（CLI 极简流程）
1. **安装**
```bash
pip install graphrag
```

2. **初始化项目**
```bash
graphrag init
# 生成：input/、.env、settings.yaml
```

3. **放入文档**
把要处理的文件丢到 `input/`

4. **构建索引（建图）**
```bash
graphrag index
# 输出到 output/（parquet 图谱+社区摘要+向量）
```

5. **查询**
```bash
# 全局查询（主题类）
graphrag query "What are the main themes?"

# 局部查询（事实类）
graphrag query "Who is X and what relations does he have?" --method local
```

---

## 五、GraphRAG vs 传统 RAG（关键差异）
| 维度 | 传统 RAG（Chunk+Vector） | GraphRAG（知识图谱） |
|---|---|---|
| 检索单位 | 文本块（Chunk） | 实体+关系+社区 |
| 多跳推理 | 弱（最多1–2跳） | 强（图路径遍历） |
| 全局问答 | 差（碎片化） | 优（社区摘要+全局归纳） |
| 可解释性 | 弱（只给片段） | 强（答案→子图→社区→原文） |
| 成本 | 低（少量 LLM 调用） | 高（索引阶段大量 LLM 调用） |
| 速度 | 快（毫秒级） | 较慢（秒级/查询） |

---

## 六、成本与风险
- **索引成本高**：比普通 RAG **贵几十到上百倍**，因为要反复调用 LLM 做抽取、聚类、摘要
- **速度慢**：索引可能跑数小时；查询通常 **10–30秒**
- **依赖 LLM 质量**：实体/关系抽取质量直接决定图谱质量，建议用 GPT-4/Claude 3
- **适合场景**：**深度分析、企业知识库、法律/医疗/学术文献、代码库**；不适合高并发、低延迟场景