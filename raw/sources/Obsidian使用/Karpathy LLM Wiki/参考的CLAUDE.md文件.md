# Karpathy LLM Wiki - Schema 配置文件

> 这是 LLM Agent 维护知识库的"操作手册"。它定义了目录结构、文件约定、工作流程。

## 目录结构

```
Karpathy Wiki/
├── CLAUDE.md              # 本文件 - LLM 操作规范
├── index.md               # 内容索引 - 所有页面的目录
├── 00-raw/                # 原始资料层（不可变）
│   ├── sources/           # 原始文档（PDF、网页、文章等）
│   └── assets/            # 图片、附件
├── 01-wiki/               # Wiki 知识层（LLM 维护）
│   ├── entities/          # 实体页面（人物、组织、产品等）
│   ├── concepts/          # 概念页面（技术、理论、方法等）
│   ├── sources/           # 源文档摘要页
│   ├── comparisons/       # 对比分析页面
│   └── synthesis/         # 综合总结页面
└── 99-logs/               # 日志层
    ├── ingest.md          # 摄入日志
    └── query.md           # 查询日志
```

## 文件命名规范

- **使用小写字母 + 连字符**: `llm-wiki-pattern.md`
- **实体页面**: `entities/[entity-name].md`
- **概念页面**: `concepts/[concept-name].md`
- **源文档**: `sources/[YYYY-MM-DD]-[source-title].md`
- **使用 Wiki-links**: `[[page-name]]`

## YAML Frontmatter 规范

每个 Wiki 页面应包含：

```yaml
---
type: [entity|concept|source|comparison|synthesis]
tags: [tag1, tag2]
created: YYYY-MM-DD
updated: YYYY-MM-DD
source: [[related-source]]
summary: "一句话描述"
---
```

## 核心工作流程

### 1. Ingest（摄入新资料）

当用户要求处理新资料时：

1. **读取源文件**: 从 `00-raw/sources/` 读取原始文档
2. **提取关键信息**: 识别核心观点、实体、概念
3. **创建/更新页面**:
   - 创建源文档摘要页 (`01-wiki/sources/`)
   - 更新相关实体页面 (`01-wiki/entities/`)
   - 更新相关概念页面 (`01-wiki/concepts/`)
   - 建立双向链接
4. **更新索引**: 更新 `index.md`
5. **记录日志**: 在 `99-logs/ingest.md` 添加条目

### 2. Query（查询知识）

当用户提问时：

1. **读取索引**: 先查看 `index.md` 找到相关页面
2. **搜索页面**: 在相关目录中搜索关键词
3. **读取上下文**: 读取相关页面及其链接页
4. **合成答案**: 基于 Wiki 内容生成回答
5. **可选 - 归档**: 如果答案有价值，创建新的对比/综合页面

### 3. Lint（健康检查）

定期执行：

1. **检查死链**: 查找不存在的 `[[link]]`
2. **查找孤岛**: 找出没有入链的页面
3. **检测矛盾**: 识别不同页面间的冲突信息
4. **发现缺口**: 识别被频繁提及但没有页面的概念
5. **建议改进**: 提出需要补充的内容

## 页面模板

### 实体页面模板

```markdown
---
type: entity
tags: []
created: {{date}}
updated: {{date}}
---

# {{Entity Name}}

## 概述
一句话描述

## 关键特征
- 特征 1
- 特征 2

## 相关概念
- [[concept-1]]
- [[concept-2]]

## 来源
- [[source-1]]

## 笔记
详细记录
```

### 概念页面模板

```markdown
---
type: concept
tags: []
created: {{date}}
updated: {{date}}
---

# {{Concept Name}}

## 定义
清晰的定义

## 核心要点
1. 要点 1
2. 要点 2

## 与其他概念的关系
- 关联：[[related-concept]]
- 对比：[[contrasting-concept]]

## 应用场景
- 场景 1
- 场景 2

## 来源
- [[source-1]]
```

## 索引文件规范

### index.md 结构

```markdown
# Wiki 索引

## 实体 (Entities)
| 页面 | 摘要 | 标签 |
|------|------|------|
| [[entities/name]] | 一句话描述 | #tag |

## 概念 (Concepts)
| 页面 | 摘要 | 标签 |
|------|------|------|
| [[concepts/name]] | 一句话描述 | #tag |

## 源文档 (Sources)
| 页面 | 摘要 | 日期 |
|------|------|------|
| [[sources/name]] | 一句话描述 | 2026-04-30 |

## 对比分析 (Comparisons)
...

## 综合总结 (Synthesis)
...
```

### ingest.md 日志格式

```markdown
# 摄入日志

## [2026-04-30] ingest | 文章标题

- **源文件**: [[00-raw/sources/file.pdf]]
- **创建的页面**:
  - [[concepts/new-concept]]
  - [[entities/new-entity]]
- **更新的页面**:
  - [[concepts/existing-concept]]
- **关键发现**:
  - 发现 1
  - 发现 2
```

## 最佳实践

1. **渐进式披露**: 先创建基础页面，后续逐步深化
2. **保持链接**: 每个页面至少链接到 2-3 个相关页面
3. **定期 Lint**: 每周执行一次健康检查
4. **原子化**: 每个页面聚焦一个主题
5. **避免重复**: 先搜索再创建
6. **版本控制**: 使用 Git 追踪变化

## 工具建议

- **搜索**: 使用 `grep` 或 `find` 命令
- **批量更新**: 使用脚本或 LLM 多文件编辑
- **可视化**: 在 Obsidian 中查看 Graph View
- **查询**: 使用 Dataview 插件动态生成列表

## 注意事项

1. **永远不要修改 00-raw/ 目录** - 这是源数据，保持不变
2. **每个来源只创建一个来源页面** - 但可能触发多个概念/实体页面
3. **保持链接有效** - 创建页面时确保引用的页面存在
4. **及时更新索引** - 每次变更后更新 index.md
5. **追加日志** - 99-logs 只追加的，除非客户要求否则不删除历史
6. **冲突处理** - 新来源与旧来源矛盾时，在页面中明确标注并讨论
