---
title: Hot Cache
updated: 2026-06-03
---

# Hot Cache

*~500字的近期活动语义快照。每次重大写入操作后自动更新。*

## Recent Activity

- [2026-06-03] LINT-FIX P1 — 15个orphan页面全部救援（0个剩余）：从41个concept/summary/entity页面添加反向wikilinks到9个skills+5个synthesis+1个entity
- [2026-06-03] LINT-FIX P1 — 3个矛盾标注完成：aescbc安全风险⚠️、CPU limit争论^[ambiguous]、seccomp/microVM关系类型修正(contradicts→related_to/replaces)
- [2026-06-03] LINT-FIX P2 — 3个缺失目标页面创建（4个broken wikilinks修复）
- [2026-06-03] LINT-FIX P3 — 26个manifest修正（0 stale, 0 missing）

## Active Threads

- **Lint修复已完成P1-P3**：P2(broken links)✅、P3(stale sources)✅、P1(orphans+contradictions)✅。仅剩P0(provenance drift 15页)
- **知识网络连接密度大幅提升**：41个页面新增延伸阅读段落，每个orphan获得1-4个入链
- **云原生知识链成型**：从Linux内核到容器运行时到K8s编排+可观测的完整链条

## Key Takeaways

- Orphan救援不是给orphan自身加链接，而是从**引用它的页面**加反向链接——skills implements concepts，所以concepts应该链接回skills
- `contradicts`关系类型慎用：seccomp(加固容器)和microVM(替代容器)是同一问题的不同路线，不是矛盾——误用`contradicts`会误导读者以为两个方案不可共存
- aescbc是K8s Secret加密的常见错误：CBC模式padding oracle风险，生产应选aesgcm或kms
- CPU limit争论的共识倾向：生产只用CPU requests(weight)不设limits(quota)

## Flagged Contradictions

- aescbc EncryptionConfiguration示例不够安全 → 已标注⚠️推荐aesgcm/kms
- CPU limit双面争论 → 已标注^[ambiguous]共识倾向不设limit
- seccomp↔microVM关系 → 已修正contradicts为related_to/replaces