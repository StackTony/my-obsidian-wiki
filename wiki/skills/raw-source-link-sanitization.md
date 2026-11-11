---
title: 导入源追踪链接清洗（中文技术站）
category: skills
tags: [obsidian, wiki, 维护, 正则, 来源清洗]
aliases: [追踪链接清洗, zhida链接清理, 知乎链接还原]
relationships:
  - target: "[[projects/my-obsidian-wiki]]"
    type: related_to
  - target: "[[summaries/linux-iommu-smmu-illustrated]]"
    type: related_to
summary: 把知乎/腾讯云等中文技术站的跳转链 `[文字](https://zhida.zhihu.com/...)` 还原为纯文本的实操流程：三类形态识别、正则替换、数量闭合验证、manifest 哈希同步（不重新蒸馏）与单文件回滚。
provenance:
  extracted: 0.60
  inferred: 0.35
  ambiguous: 0.05
base_confidence: 0.42
lifecycle: draft
lifecycle_changed: 2026-11-11
tier: supporting
created: 2026-11-11
updated: 2026-11-11
sources:
  - conversation:2026-11-11
---

# 导入源追踪链接清洗（中文技术站）

从知乎、腾讯云开发者社区复制的文章，正文术语常被自动包成带追踪参数的跳转链接。本页记录一次完整清洗（437 处、14 个 raw 源文件）验证过的流程，供后续其他目录复用。

## 概述

三类需要处理的形态：

| 形态 | 特征 | 示例 |
|---|---|---|
| 知乎知了 | `zhida.zhihu.com/search?...zd_token=...` 包裹正文术语 | `[计算机技术](https://zhida.zhihu.com/search?q=...)` |
| 腾讯云跳转 | `cloud.tencent.com/developer/tools/blog-entry?target=<原URL>` 包裹外链 | `[mmap](https://cloud.tencent.com/developer/tools/blog-entry?target=...)` |
| 知乎外链 | `link.zhihu.com/?target=<原URL>` 包裹外链 | `[fs/mount.h](https://link.zhihu.com/?target=...)` |

处理目标：只保留方括号内的链接文字，丢掉整个 URL。追踪参数里的 `zd_token` 会过期，且属于第三方追踪标识。

## 前置条件

- 已获得用户对写入 `raw/` 的明确授权（raw 区默认 AI 只读）。
- 目标文件已被 git 跟踪且工作区干净，或用 git 可精确回滚。
- 先做**只读扫描**，确认形态单一再动手。

## 步骤

1. **扫描计数，先看形态是否单一**：

   ```bash
   grep -ro  "zhida\.zhihu\.com" <dir> --include="*.md" | wc -l   # 域名总出现次数
   grep -roE "\[[^][]*\]\(https?://zhida\.zhihu\.com[^) ]*\)" <dir> --include="*.md" | wc -l  # markdown 链接数
   grep -rhoE "https?://zhida\.zhihu\.com" <dir> --include="*.md" | sort | uniq -c  # 协议变体
   ```

   两者相等才能用统一正则；不等说明有裸 URL 或 `原文：` 溯源链接，需逐条看过再决定。

2. **按文件执行替换**（perl 字节级匹配，UTF-8 多字节字符不含 ASCII 字节，无需转码）：

   ```bash
   grep -rl "zhida\.zhihu\.com" <dir> --include="*.md" | while IFS= read -r f; do
     perl -i -pe 's/\[([^\[\]]*)\]\(https:\/\/zhida\.zhihu\.com\/[^)\s]*\)/$1/g' "$f"
   done
   ```

   三个域名分别替换，正则只改域名部分。

3. **验证数量闭合**：替换后域名 markdown 链接必须为 0；剩余出现次数应恰好等于「文首原文 URL + 裸 URL」。

   ```bash
   grep -roE "\[[^][]*\]\(https?://(zhida\.zhihu\.com|cloud\.tencent\.com|link\.zhihu\.com)[^) ]*\)" <dir> --include="*.md" | wc -l
   git diff --stat -- <dir>   # 变更行数应与命中行数一致，排除整文件重写
   ```

4. **同步 manifest，不重新蒸馏**：raw 内容变了但**文字语义不变**，摘要无需重写；只更新 `content_hash` 和 `size_bytes`，避免下次 lint 误报来源过期。若文件同时被重命名，先迁键再算哈希。

5. **记录**：在 `wiki/log.md` 记一条维护操作，在项目枢纽页更新状态。

## 常见问题

| 现象 | 处理 |
|---|---|
| URL 中含 `)` | 替换会截断，需先单独确认该行 |
| 链接文字本身就是 URL（`[url](url)`） | 替换后变裸 URL，信息无损，可接受 |
| `developer.cloud.tencent.com` 子域 | 不在 `https://cloud.tencent.com/` 前缀内，不会被匹配；通常只出现在文首溯源行，应保留 |
| git 报 `LF will be replaced by CRLF` | 既有 autocrlf 配置的提示，不代表本次改动损坏行尾；用 `git diff --stat` 确认只改目标行 |
| 文件名含空格/中文 | 批量循环用 `find -print0` + `IFS= read -r -d ''`，不要 `for f in $(...)` |
| 0 字节文件哈希相同（`e3b0c442...`） | 是空文件 SHA-256 碰撞，不能当作改名依据 |

## 进阶用法

- **以计数闭合作为完成判据**：替换前域名总次数 = 替换数 + 剩余有效引用数，三者对不上就不算完成。
- **重命名与链接清洗叠加时**：先迁 manifest 键（保留 `pages_created`/`ingested_at`），再用磁盘内容重算哈希；顺序反过来会留下指向旧路径的键。
- **判断"是否要重新蒸馏"的边界**：仅剥除链接外壳 → 只同步哈希；任何文字增删改 → 按 CLAUDE.md 的「修改来源」流程重新蒸馏并传播更新。

## 来源

- 2026-11-11 会话操作记录：`raw/sources/Linux 操作系统/` 下 14 个文件、437 处链接（zhida 321 / cloud.tencent 104 / link.zhihu 12），manifest 18 个键迁移 + 哈希同步。
- [[projects/my-obsidian-wiki]] — 本 vault 的运营模式索引。
