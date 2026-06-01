---
title: Wiki Log
---

# Wiki Log

## [2026-06-01] init | Vault 创建
- vault_path="C:\Users\23363\Data\code\my-obsidian-wiki"
- wiki_dir=wiki categories=concepts,entities,skills,summaries,synthesis,journal,projects,recommendations
- raw/ 为只读区域，wiki/ 为 AI 自治区域

## [2026-06-01] restructure | 目录重构
- 将 references/ 重命名为 summaries/（与 karpathy wiki 命名一致）
- 添加 recommendations/ 目录（学习推荐报告）
- CLAUDE.md 重写为中文，纳入完整工作流规范

## [2026-06-01] enhance | CLAUDE.md 融入 obsidian-wiki 核心思想
- 新增来源标记（Provenance）：^[inferred]、^[ambiguous] 行内标记
- 新增类型化关系（Typed Relationships）：extends/implements/contradicts 等7种
- 新增置信度与生命周期（Confidence & Lifecycle）：base_confidence + lifecycle 状态机
- 新增重要性分层（Tier）：core/supporting/peripheral
- 新增 Delta 追踪（Manifest）：SHA-256 哈希检测内容变化
- 新增分级检索协议（Retrieval Primitives）：从 cheapest 到 expensive 逐步升级
- 新增页面模板（Page Template）：含 Open Questions、Sources、Provenance
- 新增目录：_meta/、_raw/、.manifest.json
- 操作模式明确化：Append/Rebuild/Restore