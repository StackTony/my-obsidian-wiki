---
title: DSH插件生态
category: entities
tags: [AI, Agent, DeepSeek, 插件, 工具]
aliases: [DSH, DeepSeek Harness插件, dsh-plugin]
relationships:
  - target: "[[entities/claude-code]]"
    type: related_to
  - target: "[[concepts/harness-engineering]]"
    type: implements
source_dir: AI 人工智能/AI Agent/Deepseek Harness
source_files: [DSH几个插件推荐.md]
summary: DeepSeek Harness插件生态Top10：web-ui全家桶(⭐1312)/modlens纯文本模型看图/better-sidebar工作台/TUI终端/workflow多Agent编排/chat-import迁移，dsh plugin命令行安装。
provenance:
  extracted: 0.85
  inferred: 0.12
  ambiguous: 0.03
base_confidence: 0.475
lifecycle: draft
lifecycle_changed: 2026-09-15
tier: supporting
created: 2026-09-15
updated: 2026-09-15
---

# DSH插件生态

DeepSeek Harness（DSH）的插件生态精选——通过 `dsh plugin --profile web add <repo>` 命令行安装。插件体系补齐了官方Web UI的短板，覆盖界面增强、视觉能力、终端体验、多Agent编排等方向。

## 简介

DSH是围绕DeepSeek模型的Agent Harness（见 [[concepts/harness-engineering]]），其插件生态采用GitHub仓库+dsh-plugin标签的分布模式。推荐安装分三个梯队：第一梯队立竿见影（web-ui/better-sidebar/TUI），第二梯队生产力（modlens/browser/workflow），第三梯队探索玩法。^[inferred]

## 关键插件（按Star排序）

| 插件 | ⭐ | 定位 |
|------|-----|------|
| dsh-web-ui | 1312 | 界面增强全家桶：五列任务看板、Git图谱、右侧面板、手机远程、Token实时统计、皮肤 |
| modlens | 1274 | "给纯文本模型装眼睛"：图片→结构化文本证据→模型作答；OCR/页面结构分析/JSON输出 |
| DSH-better-sidebar | 702 | 文件树→完整工作台：文件编辑、xterm.js终端、Git管理、子Agent管理、自定义Tab |
| dsh-TUI | 643 | Claude Code风格全屏终端：流式思考展开、上下文进度条、TPS表、会话恢复 |
| dsh-deep-whale | 378 | 深海鲸鱼萌系主题皮肤 |
| dsh-vision-toolkit | 267 | 开发/测试场景视觉包：意图图片问答、长截图OCR、UI还原、像素级对比——"参考图→写页面→截图→对比→再改"前端闭环 |
| dsh-browser | 64 | 操控真实Chrome：网页转结构化文本+元素编号操作，保留Cookie登录态 |
| dsh_workflow | 49 | 多Agent工作流治理层：可保存/审计/复用、成本权限留痕、快照续跑 |
| dsh-chat-import | 14 | 14+平台聊天历史迁移（Claude Code/ChatGPT/Cursor/Gemini/Codex），导入可续聊 |
| dsh-find-plugin | 7 | 插件搜索助手：按模糊需求搜GitHub dsh-plugin标签，返回排序候选+安装命令 |

## 与其他实体的关系

- **设计取向与 [[entities/claude-code]]** 生态互补：DSH插件把"一次性调度"升级为可治理workflow（dsh_workflow），思路接近Claude Code的skill/hook体系 ^[inferred]
- **modlens/dsh-vision-toolkit** 解决纯文本模型无视觉的短板——通过工具转换而非多模态模型，是 [[concepts/harness-engineering]] "外围工程补模型短板"的典型案例 ^[inferred]
- **dsh-chat-import** 反映Agent工具迁移痛点：聊天历史=上下文资产，跨工具可携带性是护城河也是迁移成本 ^[inferred]

## 来源

- 原文：AI 人工智能/AI Agent/Deepseek Harness/DSH几个插件推荐.md
