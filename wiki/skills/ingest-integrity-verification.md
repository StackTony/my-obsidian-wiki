---
title: ingest 完整性校验（源文件对账）
category: skills
tags: [obsidian, wiki, 维护, manifest, 校验]
aliases: [源文件对账, ingest 对账, 哈希校验]
relationships:
  - target: "[[projects/my-obsidian-wiki]]"
    type: related_to
  - target: "[[skills/raw-source-link-sanitization]]"
    type: related_to
summary: ingest 前后用「磁盘大小 + SHA-256」与 manifest 账本对账的三步法，识别只吞了一张图的伪已入库、0 字节占位、编辑器并发重存与目录重组四类症状。
provenance:
  extracted: 0.62
  inferred: 0.33
  ambiguous: 0.05
base_confidence: 0.55
lifecycle: draft
lifecycle_changed: 2026-11-17
tier: supporting
created: 2026-11-17
updated: 2026-11-17
---

# ingest 完整性校验（源文件对账）

摘要蒸馏自哪一版原文，决定它是否可信。manifest 里记着 `size_bytes` 与 `content_hash`，磁盘上还有一份当下的事实——两者不是同一份东西时，delta 检测会把"只有一张图的存根"当成"已入库"，后续所有下游页面都建在残片上。本页给出三步对账法和四类症状的处理口径。

## 前置条件

- vault 根目录下的 `wiki/.manifest.json` 可读
- 能算哈希：Git Bash 用 `sha256sum`，无 Node 也可（`node` 仅用于批量扫描）

## 步骤

### 1. 取磁盘事实

```bash
f="raw/sources/<目录>/<文件>.md"
stat -c '%s %y' "$f" && sha256sum "$f"
```

### 2. 取账本记录

`manifest.sources["<vault 相对路径>"]` 中的 `size_bytes`、`content_hash`、`ingested_at`。注意键是**不含 `raw/sources/` 前缀**的路径。

### 3. 判定并处置

| 磁盘 vs 账本 | 含义 | 动作 |
|---|---|---|
| 哈希一致 | 真正的无变化 | 跳过（不要因为 mtime 变了就重蒸馏） |
| 磁盘远大于账本（十倍以上） | 只入库过占位图/存根 | 按**新增来源**全文重蒸馏，不是小修小补 |
| 大小差几十字节、哈希不同 | 外部格式化器重存 | 只校正账本哈希，**不重蒸馏**，在 log 写明 diff 性质 |
| 账本键路径不存在 | 目录重组或源被删 | 按 basename/哈希迁移键或清理，不重新 ingest |
| 磁盘文件 0 字节 | 占位，尚未有内容 | 不 ingest；记入积压清单，等补内容 |

对账必须在**写页面之前**做——顺序反了，就会先蒸馏出错误的摘要再回头发现源变了。

## 常见问题

- **「已登记」不等于「已入库」**：2026-11-13 的 `Linux 内存回收机制.md` 账本记 36 B（正文只有一张回收调用图），磁盘上已是 125 KB 全文，此前的摘要蒸馏自那张图。判据是体积比值，不是哈希是否匹配。^[inferred]
- **0 字节文件的哈希没有信息量**：所有空文件都是 `e3b0c442…`，不能拿来判断"是不是改名后的同一篇"。
- **编辑器会与 ingest 抢文件**：同一天源文件在蒸馏期间被 Obsidian 重存两次（125,882→125,903 B、5,041↔5,063 B），diff 只有标题编号空格与 `[NR_WMARK]`→`\[NR_WMARK\]` 转义。做法：ingest 时不要在 Obsidian 里打开该笔记；蒸馏后再算一次哈希；把"格式变更 vs 内容变更"写进 log。^[inferred]
- **账本 stats 与文件数可能差一**：Learn 流程新建 `recommendations/` 报告时容易忘记同步 `total_pages`（2026-11-12 那篇导致 217 vs 实际 218）。定期用文件数校准，而不是信任 stats 自增。

## 进阶用法

**扫出"非空但未入库"的真实积压**（比 stats 更可靠）：

```bash
node -e "const fs=require('fs'),p=require('path');
const m=JSON.parse(fs.readFileSync('wiki/.manifest.json','utf8'));const k=new Set(Object.keys(m.sources));
(function w(d){for(const n of fs.readdirSync(d)){const f=p.join(d,n),s=fs.statSync(f);
if(s.isDirectory())w(f);else if(n.endsWith('.md')&&s.size>0){
const r=p.relative('raw/sources',f).split(p.sep).join('/');if(!k.has(r))console.log(s.size,r);}}})('raw/sources');"
```

**0 字节巡检**：`find raw/sources -type f -name "*.md" -size 0`

**反向核验账本键**：列出 manifest 中路径已不存在的键（源被删/被改名未迁移），这批是 delta 检测的噪声来源。

## 来源

- `wiki/log.md` 2026-11-13 两条 INGEST 记录（来源状态说明、哈希刷新经过）
- [[projects/my-obsidian-wiki]] — 本 vault 的运营状态与积压清单
- [[skills/raw-source-link-sanitization]] — 链接清洗后"只同步哈希、不重蒸馏"的同一口径
