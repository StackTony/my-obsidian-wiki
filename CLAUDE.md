# CLAUDE.md — Obsidian Wiki Vault

## Vault Architecture

This vault follows a **Karpathy wiki** model: strict separation between AI-maintained and human-maintained zones.

```
my-obsidian-wiki/
├── wiki/              ← AI AUTONOMOUS ZONE (read + write)
│   ├── concepts/      Distilled concepts & mental models
│   ├── entities/      People, orgs, tools, frameworks
│   ├── skills/        Practical techniques & how-tos
│   ├── references/    Annotated source summaries
│   ├── synthesis/     Cross-domain connections & insights
│   ├── journal/       Date-stamped reflections & digests
│   ├── projects/      Per-project knowledge hubs
│   ├── _archives/     Snapshots for wiki-rebuild/restore
│   ├── _staging/      Review queue (used when WIKI_STAGED_WRITES=true)
│   ├── index.md       Auto-maintained wiki index
│   ├── log.md         Activity log (append-only)
│   └── hot.md         ~500-word semantic snapshot of recent activity
├── raw/               ← HUMAN / READ-ONLY ZONE (AI reads only, never writes)
│   ├── sources/       Original notes, articles, downloads (231 .md files)
│   └── resources/     Images & attachments
├── .obsidian/         ← Obsidian config (do not modify unless asked)
├── .env               ← Environment config (gitignored)
└── CLAUDE.md          ← This file
```

## Core Rules

### 1. Zone Boundaries — NEVER violate these

| Zone | Path | AI can read? | AI can write? |
|------|------|-------------|--------------|
| **Wiki** | `wiki/` | ✅ | ✅ — this is AI's workspace |
| **Raw** | `raw/` | ✅ | ❌ NEVER write, move, or delete anything here |
| **Obsidian config** | `.obsidian/` | ✅ | ❌ unless explicitly asked |
| **Environment** | `.env` | ✅ | ❌ set during `/wiki-setup`, not changed later |

**If you need to modify `raw/`, ask the user first.** The raw zone preserves original documents untouched — wiki-ingest copies/transforms them into `wiki/`.

### 2. Writing Standards

- **Frontmatter**: Every wiki page must have YAML frontmatter with at minimum `title` and `tags`
- **Wiki-links**: Use `[[wiki/concepts/DAG]]` style for internal links (Obsidian resolves within vault)
- **Cross-zone links**: Reference raw sources with `![[raw/sources/path/to/file.md]]` for embeds, or describe the path in prose
- **Language**: Write in the same language as the source material (this vault is predominantly Chinese — preserve that)
- **Tags**: Use hierarchical tags `#ai/llm`, `#os/linux`, `#cs/algorithm` etc. — see `/tag-taxonomy`
- **Conciseness**: Wiki pages should distill, not copy. A 5000-word source should become a 500-word concept page

### 3. Page Lifecycle

```
raw/sources/X.md  →  wiki-ingest  →  wiki/concepts/X.md (distilled)
                                    wiki/references/X.md (annotated summary)
                                    wiki/synthesis/X→Y.md (cross-link)
```

- `wiki-ingest` reads from `raw/`, writes to `wiki/` — it never touches `raw/`
- `wiki-rebuild` archives current `wiki/` to `_archives/` then regenerates
- `wiki-dedup` merges duplicate pages within `wiki/`
- `wiki-lint` audits health: broken links, missing frontmatter, orphan pages

### 4. Staged Writes (currently disabled)

`WIKI_STAGED_WRITES=false` — pages written directly. If enabled later:
- New/updated pages land in `wiki/_staging/`
- Run `/wiki-stage-commit` to review and promote
- Pages in staging are NOT visible in Obsidian's graph until promoted

## Configuration Reference

| Variable | Value | Purpose |
|----------|-------|---------|
| `OBSIDIAN_VAULT_PATH` | vault root | Absolute path to this directory |
| `OBSIDIAN_SOURCES_DIR` | `raw/sources` | Where wiki-ingest reads from |
| `WIKI_DIR` | `wiki` | Where AI writes output pages |
| `WIKI_TOKEN_WARN_THRESHOLD` | `100000` | Warn when full-wiki read > 100K tokens |
| `WIKI_STAGED_WRITES` | `false` | Direct writes, no staging review |

## Source Topics

The `raw/sources/` directory contains 231 markdown files organized by topic:

- `AI 人工智能/` — AI infra, Agent架构, 大模型LLM
- `DFX工具/` — Development tools
- `Linux 操作系统/` — Linux OS knowledge
- `Linux 蛛拟化/` — Virtualization
- `Obsidian使用/` — Obsidian usage tips
- `Self learn/` — Self-study notes (图论 etc.)
- `云原生/` — Cloud native / Kubernetes
- `数据结构与算法/` — Data structures & algorithms
- `消息队列/` — Message queues
- `软件工程/` — Software engineering

## Recommended Workflows

1. **First ingest**: `/wiki-ingest` — process all 231 sources into wiki pages
2. **Daily maintenance**: `/daily-update` — runs lint, dedup, cross-link, digest cycle
3. **Research**: `/wiki-research <topic>` — autonomous multi-source research → wiki page
4. **Query**: `/wiki-query <question>` — answer questions from wiki knowledge
5. **Status check**: `/wiki-status` — show vault health, delta, token footprint
6. **History mining**: `/claude-history-ingest` — turn past conversations into wiki pages

## Preferences

- User name: 老板
- Language: Chinese (zh-CN) — communicate in Chinese, write wiki content matching source language
- Permission mode: yolo (agentic, minimal prompting)
- Model: GLM-5.1 via Anthropic-compatible proxy