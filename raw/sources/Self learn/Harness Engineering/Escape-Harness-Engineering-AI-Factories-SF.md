I spent the last week of March 2026 in San Francisco talking to CTOs, CPOs, and engineering leaders from companies of every size about how they actually build with AI agents today. I've met solo founders of pre-series A startups, I attended [Y Combinator](https://www.ycombinator.com/?ref=escape.tech) DevTool Day on March 27 and [All Things Dev](https://allthingsweb.dev/2026-03-31-all-things-web-workos?ref=escape.tech) on March 31, sat down with our advisors, and had dozens of conversations with founders and tool builders working at the frontier.

This document is what I brought back. It is a field report: what I learned, what I think matters, and where the industry seems to be heading. It is also the reference document my team and I will use to structure how we adopt these practices ourselves.

The audience are startup Founders, CTOs, CPOs, and senior engineers/product managers who are already past the "what is an LLM" stage and want to know what actually works in production. San Francisco is not the whole market, but it is often a leading indicator, and right now, the signal is strong.

The terms below are overloaded, so I use them narrowly:

- **Model / LLM:** The base intelligence layer: tokens in, tokens out. On its own it does not remember sessions, read your repo, run commands, or verify its work. LLM is a specific technology of models.
- **Harness:** Everything around the model: instructions, context, tools, runtime, permissions, review loops, verification.
- **Agent:** A harnessed loop that can decide, act, observe, and continue until done or blocked.
- **Vibe coding:** A low-structure accept-and-iterate workflow. Useful for exploration and prototypes. Weak for correctness, repeatable delivery, and regulated workflows.
- **AI factory:** The org-level system that repeatedly turns intent into shipped work: issue framing, execution, review, deployment, telemetry, feedback. Partly engineering, partly product operations. AI Factory enables Vibe Coding at Scale.

## 1\. What's Happening and What It Means — Tech and Product Hot Takes from the Bay Area

This section is intentionally opinionated. These are not consensus statements. They are recurring arguments, observed shifts, and directional predictions heard across both conferences and in every conversation I had that week.

## Productivity x10 since December 2025

This was a common framing, but it should not be presented as an audited universal benchmark.

The charitable and defensible version is:

- The comparison several aggressive teams make is against December 2025 workflows, not against the pre-AI era.
- In one quarter, models improved, harnesses improved, and orchestration improved at the same time.
- The operating ceiling for one engineer with good agents feels materially different than it did a few months earlier.

Treat "10x" as a directional claim from fast adopters, not as settled measurement science.

## Startups that don't adopt will die

This is rhetorical, but the underlying claim is serious.

What the statement is really pointing at:

- The compounding advantage is not only code generation speed.
- It is shorter build-review-ship-learn loops.
- Teams that delay adoption entirely are not just slower at implementation; they are slower at learning.

The real decision is not "AI or no AI." The real decision is how much of the delivery loop remains human-led, and which work becomes agent-native now.

## The rise of the "Builder"

The distinction between UI designer, UX researcher, product owner, and developer is collapsing. The recurring claim is that a new profile is emerging: the Builder, someone who owns the problem end-to-end and uses agents to cover the skills they lack.

- A PM with no frontend experience ships a working UI change.
- A designer pushes code, not just mockups.
- A founder prototypes a full feature before involving the team.

The threshold for producing a first-pass pull request dropped so sharply that role boundaries stopped being the constraint. What matters now is not your job title but whether you can judge the output: does this diff belong in the product, is it correct, and is it coherent with everything else?

## The bottleneck is moving to product strategy

When implementation gets cheaper, bad strategy gets more expensive.

The reason is simple:

- Slow implementation used to absorb weak decisions.
- Fast implementation removes that buffer.
- Teams can now ship low-quality strategy much faster than before.

This is why product quality now depends more on prioritization discipline, not less.

## The startup lifecycle is compressing

Agent-driven development compresses the time between:

- hypothesis
- first product
- early traction
- version-two confusion

You reach "the first vision is basically built, now what?" much faster.

That creates a new failure mode:

- the company has engineering leverage
- but it does not yet have strategic clarity for what to do with it

The result is feature volume without product direction.

## The IDE is dead

Also rhetorical.

The stronger version is:

- The center of gravity is moving from the editor to the agent console.
- Editors still matter.
- But for multi-step work, the critical surface is now orchestration, visibility, review, status, and control over parallel sessions.

The terminal wins whenever the work looks more like operating a system than typing code line by line.

## There is no excuse not to run 24 hours a day

This follows directly from the previous point. If the compounding advantage is loop speed, then leaving agents idle overnight is a deliberate choice to slow that loop.

The argument is not about developer working hours. It is about asset utilization. Agents are infrastructure. Leaving them idle from 7pm to 9am is the equivalent of shutting down your CI pipeline every evening and restarting it in the morning.

The technical capability is no longer in question. Rakuten engineers ran Claude Code autonomously for seven hours on a 12.5-million-line codebase, achieving 99.9% accuracy. OpenAI published a Codex stress test that ran for 25 hours uninterrupted. These are logged runs, not demos.

What the strongest teams described:

- Engineers push work at end of day. Agents pick up test writing, code review, refactoring, and security scans overnight.
- By morning, the codebase has been tested, reviewed, and flagged. The engineer's first task is triage, not implementation.
- Nothing merges without human approval. The overnight cycle produces candidates, not commits.

## Do we need fewer PMs or more?

This is still the wrong framing. Three product people for fifteen engineers is more than enough: possibly too many. The old ratio of 1 PM per 5-7 engineers assumed the PM was the translation layer between business intent and technical execution. When agents eliminate most of that translation cost, the PM's value shifts entirely upstream.

What changes is not mainly the headcount math. It is the job shape.

Work that shrinks:

- detailed ticket translation
- backlog grooming as a communication bridge
- implementation-level handholding

Work that grows:

- market understanding
- synthesis of customer signal
- prioritization under much faster engineering throughput
- deciding what not to build

The PM role moves upstream. Less project management. More judgment.

## Tasks for me or for the agent?

| Usually better delegated to agents | Usually still human-led |
| --- | --- |
| Correctness sweeps | Where to start |
| Testing | Architecture |
| Error handling | Design direction and consistency |
| Debugging after reproduction | Abstraction boundaries |
| Boilerplate | Data model and API shape |
| Translation | Refactoring intent |
| Thoroughness | Product judgment |
| Repetitive implementation | Priority tradeoffs |

The practical question is not "can the model do this?" It is "what is the cost of a silent mistake here, and how cheaply can I detect it?"

## Model choice: Claude 4.6 vs GPT-5.4? You should use both

| Claude Opus 4.6 | GPT-5.4 in Codex |
| --- | --- |
| Better first-pass writing tone | Better implementation reliability |
| Better exploratory docs and explanation | Better verification, testing and final passes |
| Strong for frontend and UI taste | Strong for correctness-sensitive backend work |
| Strong for interactive computer use | Strong for long, tool-heavy execution in Codex |

This is a heuristic, not a law. The real point is to stop treating model choice as a religion and start treating it as task routing.

The strongest proof point: on March 30, 2026, OpenAI open-sourced `codex-plugin-cc`: an official plugin that lets you invoke Codex directly from Claude Code. OpenAI shipping a plugin inside a competitor's tool confirms the moat is the harness, not the model. They'd rather have Codex running inside Claude Code (collecting API charges per review) than have users not use Codex at all. The ecosystem is converging on interoperability, not lock-in.

The category is still moving fast. Overbuilding orchestration too early is an easy way to create your own internal product to maintain.

## 2\. Harness Engineering Pillars

Harness engineering is not "writing a better prompt." It is the design of the system around the model so output quality depends less on raw model brilliance and more on structure.

## Minimal AI Factory Architecture

If you strip the category down to its minimum useful shape, an AI factory has seven layers:

1. **Intent capture:** Product request, bug, support signal, roadmap item, or internal need.
2. **Spec or issue framing:** A bounded instruction with constraints, acceptance criteria, and links to context.
3. **Context and instruction layer:** Repo guidance, scoped rules, skills, docs, APIs, and environment facts.
4. **Execution layer:** One or more agents editing code, calling tools, and running commands.
5. **Verification layer:** Tests, static analysis, review agents, CI, and human sign-off.
6. **Isolation and permission layer:** Worktrees, sandboxes, runtime isolation, secret boundaries, and approval flows.
7. **Feedback layer:** Production telemetry, customer signal, review outcomes, and repeated failures fed back into rules, prompts, or process.

If one of these layers is weak, the whole system regresses:

- No issue framing: fast implementation of vague intent.
- No context discipline: expensive wandering.
- No verification: vibe coding at scale.
- No isolation: parallelism without control.
- No feedback loop: repeated mistakes with better marketing.

## Instructions, rules, plugins and skills

The important instruction artifacts are:

| Artifact | Primary use | Notes |
| --- | --- | --- |
| `AGENTS.md` | Shared project instructions across agent tools, auto-imported by Codex. | Standard format used by all providers but Anthropic |
| `CLAUDE.md` | Same as `AGENTS.md` auto-imported by Claude. | Can symlink `AGENTS.md` |
| `SKILL.md` | Narrow, on-demand workflow or capability | Use for reusable task methods, not global policy |
| `.cursor/rules/*.md` | Cursor-specific structured rules | Useful when you need metadata or path scoping |

**Plugin vs. Skill:**

A skill is a single `SKILL.md` file invoked via slash command (`/deploy`). A plugin is a directory with a `.claude-plugin/plugin.json` manifest that bundles multiple skills, hooks, agents, and MCP configs into a distributable package (`/plugin-name:command`). Use skills for personal workflows. Use plugins when sharing across teams.

ℹ️ Avoiding duplication between Claude Code and Codex: If you use both tools on the same repo, pick one source of truth:

- **Symlink (simplest):** `ln -sf AGENTS.md CLAUDE.md`. Both filenames point to the same content. Zero drift.
- **Reference:** Put `@AGENTS.md` inside your [CLAUDE.md](http://claude.md/?ref=escape.tech). Claude Code reads the referenced file inline. Add Claude-specific instructions below.
- **Pointer:** Keep all shared instructions in [AGENTS.md](http://agents.md/?ref=escape.tech). Make [CLAUDE.md](http://claude.md/?ref=escape.tech) a one-liner: `READ AGENTS.md FIRST`. Add overrides below.

Concrete architecture: multi-tool project

```
my-project/
├── AGENTS.md                          # Source of truth (shared instructions)
├── CLAUDE.md -> AGENTS.md             # Symlink for Claude Code
├── .claude/
│   ├── CLAUDE.md                      # Claude-specific overrides (optional)
│   ├── rules/
│   │   ├── testing.md                 # "Always run pytest before committing"
│   │   └── frontend.md               # "Use Tailwind, no inline styles"
│   └── skills/
│       ├── deploy/
│       │   └── SKILL.md              # /deploy: push to prod workflow
│       └── review/
│           └── SKILL.md              # /review: pre-landing PR checks
├── .cursor/
│   └── rules/
│       ├── base.md                    # Cursor-specific conventions
│       └── api.md                     # Path-gated to src/api/**
└── src/
    └── api/
        └── AGENTS.md                  # Directory-scoped: "All endpoints need auth"
```

What happens at session start:

- **Claude Code** loads: `CLAUDE.md` (-> [AGENTS.md](http://agents.md/?ref=escape.tech) via symlink) + `.claude/CLAUDE.md` + `.claude/rules/*.md` + skill names from `.claude/skills/`. When you type `/deploy`, the full `deploy/SKILL.md` loads into context.
- **Codex** loads: `AGENTS.md` at root. When working in `src/api/`, also loads `src/api/AGENTS.md`. The `.claude/` directory is ignored.
- **Cursor** loads: `.cursor/rules/*.md` + `AGENTS.md` at root. The `.claude/` directory is ignored.

## Keep root context lean

The best recent corrective on context-file enthusiasm came from ETH Zurich: detailed repository context often increases cost and can reduce task success when it adds unnecessary requirements.

| Use the root file for | Do not use the root file for |
| --- | --- |
| Build, test, and lint commands | Generic clean-code slogans |
| Dangerous areas and non-obvious constraints | Style rules your formatter already enforces |
| Generated-code boundaries | README duplication |
| Migration or deployment cautions | Long architecture tutorials the agent can read elsewhere |
| Review and verification expectations |  |

What matters in practice:

- Keep one shared source of truth for durable project instructions.
- Put tool-specific behavior only where it belongs.
- Put local or path-specific constraints in narrower scopes, not in the root file.
- Prefer on-demand skills for workflows that are occasionally needed, not always needed.

## Verification beats advice

The rule of thumb is simple: if an error class recurs, stop describing it and start preventing it.

| Failure mode | Better fix |
| --- | --- |
| Agent stops too early | Explicit build-verify-fix loop |
| Agent forgets tests | Pre-completion verification hook plus CI |
| Agent edits the wrong area | Scoped instructions and path-specific rules |
| Agent repeats the same bug class | Linter, static rule, or regression test |
| Agent misses architectural context | Better issue framing and smaller task boundaries |

Example: LangChain published one of the clearest public examples of this pattern in February 2026: their coding agent moved from 52.8% to 66.5% on Terminal Bench 2.0 by changing the harness, not the model.

## Review loops and context drift

Over time, agent-generated code drifts:

- Conventions soften
- Dead code accumulates
- Review comments repeat
- Context files become stale

Useful mitigations:

- Automated review on every meaningful PR
- A second model for high-stakes review when possible
- Periodic cleanup of root instruction files
- Tracing and postmortems on agent failures
- Converting recurring review comments into deterministic checks

## Example: coding standards in AGENTS.md

```markdown
# Global Coding Standards

1. **YAGNI**: Don't build it until you need it
2. **DRY**: Extract patterns after second duplication, not before
3. **Fail Fast**: Explicit errors beat silent failures
4. **Simple First**: Write the obvious solution, optimize only if needed
5. **Delete Aggressively**: Less code = fewer bugs
6. **Semantic Naming**: Always name variables, parameters, and API endpoints with verbose, self-documenting names that optimize for comprehension by both humans and LLMs, not brevity (e.g., \`wait_until_obs_is_saved=true\` vs \`wait=true\`)
```

Source: [**All Things Web @ WorkOS**](https://allthingsweb.dev/2026-03-31-all-things-web-workos?ref=escape.tech)**, 31st of March 2026**

## 3\. Engineering and Product Playbook for Founders and teams

As mentioned in the hot takes, adopting Harness Engineering rapidly is a matter of life or death for companies, whatever their size is. As stated by Y Combinator, the trend show come from the top, the Founders, specifically those owning the Technical and the Product Roles, summarized as the CTO and CPO in the rest of the document. With that framing, the CTO controls how fast the org can ship. The CPO controls whether what ships is worth shipping. When agents make the CTO side 10x faster, every CPO mistake compounds 10x faster too.

## First 30 days

Don't standardize on day one. Run agents on real work for two weeks and log every revert, rework, and rejection. Then build guardrails around the failure modes you actually saw: not hypothetical ones.

- **CTO:** pick one harness (Claude Code or Codex, not both), add a minimal instruction file, require CI + automated review on all agent PRs, set a per-session cost alert.
- **CPO:** rewrite issue templates around intent and success criteria (agents execute literally), define an explicit "do not build" list for the quarter, pull customer signal into written artifacts.
- **Together:** review merged agent-assisted PRs weekly. Update process from real failures, not theory.

## Autonomy tiers

Not all PRs need the same scrutiny. Start everything at full review. Promote downward only with evidence.

| Tier | Examples | Required before merge |
| --- | --- | --- |
| **Full autonomy** | Typo fixes, test additions, dependency bumps, boilerplate | CI + automated review |
| **Light review** | Feature work within established patterns, bug fixes with clear repro | CI + automated review + human skim (< 5 min) |
| **Full review** | New endpoints, data model changes, auth/payment flows | CI + automated review + thorough human review |
| **Human-led** | Schema migrations, infra changes, security-critical paths | Human writes or co-writes. Agent assists. |

## Cadence

- **Weekly:** review agent-authored regressions. Convert the top recurring mistake into a deterministic rule. Check whether issues were specific enough for agents to act without churn.
- **Monthly:** reclassify work across autonomy tiers. Remove dead rules and stale instructions. Audit feature velocity vs. feature impact: are we shipping noise?
- **Quarterly:** revisit the stack, permission model, cost structure, and PM staffing ratio.

## Metrics

- Lead time from issue to merged PR
- Agent autonomy rate (% of tasks without human intervention)
- Reopen and rollback rate on agent-authored changes
- Wasted work rate (features reverted or unused within 30 days)
- Issue clarity (% of issues agents can act on without clarification)
- Monthly agent API cost per engineer
- Cycle time from customer signal to shipped outcome

## 4\. Agent Factory Tooling

The point is not to install everything below. The point is to identify the bottleneck you actually have.

## The winning stack pattern

This is the stack pattern I would describe as convergent, not mandatory:

| Layer | Standard choice | Why it keeps showing up |
| --- | --- | --- |
| Source of truth | GitHub | Claude Code authors ~4% of all public commits (~135K/day). Every agent tool produces PRs against GitHub repos. The entire agent factory pattern assumes Git and GitHub as the substrate. |
| Planning | Linear | Declared " [issue tracking is dead](https://linear.app/next?ref=escape.tech) " (March 2026). Coding agents installed in 75% of enterprise workspaces. Deeplinks send issue context directly into Claude Code, Cursor, or Copilot as prefilled prompts. Agent work volume up 5x in three months. |
| Trigger and coordination | Slack | Non-engineers describe a problem or request in Slack; an MCP integration routes it to an agent that opens a PR. The barrier drops from "file a ticket" to "describe it in a message." |
| Thinking and notes | Obsidian | Local markdown files that agents can read via MCP. Where intent gets structured before it becomes an issue or a prompt. |
| Runtime | Cloudflare Agents | Agents SDK, Durable Objects for state, Workflows for long-running tasks. Workers AI runs frontier models on-platform with 77% cost reduction on 7B token/day workloads vs. external API calls. |
| Observability | Sentry | Error tracking plus LLM-specific monitoring: agent runs, tool calls, token usage, conversation replay. Also maintains Claude Code agent skills (iterate-pr, code review): sits on both sides of the workflow. |
| Business signal | HubSpot | Customer feedback, support tickets, and sales conversations flow into the planning layer, giving agents business context for what to build next. |

## Terminal & orchestration

| Tool | Bottleneck it solves | Why it matters |
| --- | --- | --- |
| [cmux](https://cmux.com/?ref=escape.tech) / [repo](https://github.com/manaflow-ai/cmux?ref=escape.tech) | 5+ agent sessions with no status visibility: constant tab-switching | macOS-native terminal with GPU-accelerated rendering (libghostty), per-agent green/yellow/red status indicators, git branch + PR status per workspace. Works with Claude Code, Codex, Gemini CLI. |
| [Superset](https://superset.sh/?ref=escape.tech) / [repo](https://github.com/superset-sh/superset?ref=escape.tech) | Parallel agents stepping on each other's files and git state | Git worktree isolation per agent. Each agent gets its own sandbox with no shared mutable state. Launched March 2026. |
| [Conductor](https://github.com/garrytan/gstack?ref=escape.tech) | Running agents sequentially: throughput capped at 1x | Orchestration layer from gstack. Runs multiple Claude Code sessions in parallel, each in its own isolated workspace. Garry Tan regularly runs 10-15 parallel sprints. |
| [Claude Manager](https://github.com/Bendzae/claude-manager?ref=escape.tech) | Losing track of which Claude session is running, waiting, or finished | Rust TUI that organizes sessions by project/task hierarchy. Live status indicators, diff preview without attaching, worktree lifecycle management. First published March 2026. |

## Spec & planning

| Tool | Bottleneck it solves | Why it matters |
| --- | --- | --- |
| [OpenSpec](https://openspec.dev/?ref=escape.tech) | Agents coding before the problem is well-defined: expensive iterations on work that doesn't match intent | Three-phase state machine (proposal, apply, archive). Agent must produce a ~250-line spec before writing code. Supports Claude Code, Cursor, Copilot, and 20+ tools. 27K+ stars, YC-backed. |

## Quality & review

| Tool | Bottleneck it solves | Why it matters |
| --- | --- | --- |
| [Codex plugin for Claude Code](https://github.com/openai/codex-plugin-cc?ref=escape.tech) | Want a second opinion from a different model without leaving Claude Code | OpenAI's official plugin (open-sourced March 30, 2026). Adds `/codex:review` and `/codex:adversarial-review`. Uses the same harness as Codex itself. Runs in background using your ChatGPT subscription. |
| [CodeRabbit](https://docs.coderabbit.ai/?ref=escape.tech) | PR reviews are slow (waiting for humans) or shallow (humans skim large diffs) | Always-on AI review on every PR. 13M+ PRs reviewed, 2-3M connected repos, 75M defects found. GitHub/GitLab/Azure DevOps/Bitbucket. Free tier available, SOC 2 Type II. |
| [Taskless](https://taskless.io/?ref=escape.tech) | Agent keeps making the same class of mistake: you fix it once but nothing prevents it from reappearing | Converts code review corrections into deterministic syntax-tree rules (tree-sitter). Tag @taskless on a PR or file an issue; it creates a pass/fail rule that runs on every PR, in every IDE, on every run. Same result every time: not AI opinions, not prompt engineering. 25+ languages, zero instrumentation. |
| [Sentry iterate-pr](https://github.com/getsentry/skills/tree/main/plugins/sentry-skills/skills/iterate-pr?ref=escape.tech) | Manual PR-fix-CI loops: developer re-runs checks, reads logs, applies fix, resubmits | Encodes the fix-CI-resubmit loop as a reusable skill. Agent detects failures, applies fixes, and re-runs checks without human intervention. Good reference for encoding any mechanical review iteration as a skill. |
| [gstack](https://github.com/garrytan/gstack?ref=escape.tech) | No structured review/QA patterns beyond basic linting | Pattern library, not a package: role-based review, directory freezes, visual QA, pre-landing checks. Steal the patterns that match your failure mode, ignore the rest. |

## Context & memory

|  | Bottleneck it solves | Why it matters |
| --- | --- | --- |
| [Claude-Mem](https://github.com/thedotmack/claude-mem?ref=escape.tech) | Sessions are stateless: everything the agent learned is lost when the session ends | Auto-captures session activity, compresses it with AI (agent-sdk), injects relevant context into future sessions. Adds dynamic, session-derived memory on top of static [CLAUDE.md](http://claude.md/?ref=escape.tech) files. 44K+ stars. |

## Runtime isolation

| Tool | Bottleneck it solves | Why it matters |
| --- | --- | --- |
| [Coasts](https://coasts.dev/?ref=escape.tech) / [repo](https://github.com/coast-guard/coasts?ref=escape.tech) | Two agents both running `localhost:3000`: port collisions block parallel testing | Each worktree gets its own containerized runtime with dynamic port assignment. Agnostic to AI providers. Single config file. |
| Docker-in-Docker / Docker Sandboxes | Need N isolated full-stack copies (app, database, workers) per agent | Docker Compose with per-agent port mappings. Docker Desktop 4.60+ supports Sandboxes in dedicated microVMs with network isolation. Heavier than Coasts but gives full stack isolation. |

## Other tools worth watching

Not all of these belong in a default stack. They are still worth tracking because they attack real bottlenecks.

| Tool | What it does | Why it's interesting |
| --- | --- | --- |
| [Ghost](https://ghost.build/?ref=escape.tech) | Instant, ephemeral Postgres databases: agents spin them up like git branches. MCP/CLI only, no UI. | Standard SQL, no proprietary SDK. 100 hrs/month free. Pairs with Memory Engine, TigerFS, and Ox (sandboxed execution), all Postgres-native. |
| [fp](https://fp.dev/?ref=escape.tech) | CLI-first, local-first issue tracking for Claude Code. `/fp-plan`, `/fp-execute`, `/fp-review`. | Local code review interface that sends inline comments back to the agent. No external service required. Mac desktop app. |
| [GitButler](https://gitbutler.com/?ref=escape.tech) | Parallel branches in a single working directory via virtual branching: no worktree directories. | Assign file changes to different branches visually. All branches start from the same state, guaranteed to merge cleanly. Lighter than worktree-based isolation. |
| [FinalRun](https://finalrun.app/?ref=escape.tech) | Vision-based mobile testing on real iOS/Android devices. Test cases written in plain English. | 76.7% on Android World Benchmark (116 tasks): ahead of DeepSeek, Alibaba, ByteDance agents. ~99% flaky-free. 2-person startup. |
| [SuperBuilder](https://www.superbuilder.sh/?ref=escape.tech) | Mac-native command center for Claude Code with per-message cost tracking, rate-limit queuing, and Branch Battle. | Free, BYOK. Tracks cost per thread/project, queues tasks through rate limits, compares two approaches side by side. |
| [AgentsMesh](https://agentsmesh.ai/?ref=escape.tech) | Remote AgentPods for running multiple coding agents (Claude Code, Codex, Gemini CLI, Aider, OpenCode). | Self-hosted runners, gRPC + mTLS control plane, Kanban with ticket-to-pod binding. One dev built 965K lines in 52 days using it. |
| [Ghostgres](https://github.com/timescale/ghostgres?ref=escape.tech) | Experimental Postgres fork from Timescale: "there are no dumb queries, only dumb databases." | Early-stage (32 stars), but Timescale's broader push includes pgai (embeddings + NL-to-SQL in Postgres) and Ox (agent sandbox TUI). |

## 5\. References

- Y Combinator DevTool Day (March 27): [https://www.ycombinator.com/](https://www.ycombinator.com/?ref=escape.tech)
- All Things Dev (March 31): [https://allthingsweb.dev/2026-03-31-all-things-web-workos](https://allthingsweb.dev/2026-03-31-all-things-web-workos?ref=escape.tech)
- Anthropic: Manage Claude's memory: [https://docs.anthropic.com/en/docs/claude-code/memory](https://docs.anthropic.com/en/docs/claude-code/memory?ref=escape.tech)
- Anthropic: Claude Opus 4.6: [https://www.anthropic.com/news/claude-opus-4-6](https://www.anthropic.com/news/claude-opus-4-6?ref=escape.tech)
- Anthropic: Claude Sonnet 4.6: [https://www.anthropic.com/news/claude-sonnet-4-6](https://www.anthropic.com/news/claude-sonnet-4-6?ref=escape.tech)
- OpenAI: Introducing Codex: [https://openai.com/index/introducing-codex/](https://openai.com/index/introducing-codex/?ref=escape.tech)
- OpenAI: Introducing GPT-5.4: [https://openai.com/index/introducing-gpt-5-4/](https://openai.com/index/introducing-gpt-5-4/?ref=escape.tech)
- [AGENTS.md](http://agents.md/?ref=escape.tech) standard: [https://agents.md/](https://agents.md/?ref=escape.tech)
- Cursor docs on rules and [AGENTS.md](http://agents.md/?ref=escape.tech): [https://docs.cursor.com/en/context](https://docs.cursor.com/en/context?ref=escape.tech)
- ETH Zurich / SRI Lab: Evaluating [AGENTS.md](http://agents.md/?ref=escape.tech): [https://www.sri.inf.ethz.ch/publications/gloaguen2026agentsmd](https://www.sri.inf.ethz.ch/publications/gloaguen2026agentsmd?ref=escape.tech)
- LangChain: Improving Deep Agents with harness engineering: [https://blog.langchain.com/improving-deep-agents-with-harness-engineering/](https://blog.langchain.com/improving-deep-agents-with-harness-engineering/?ref=escape.tech)
- Linear changelog, deeplinks to coding tools: [https://linear.app/changelog/2026-02-26-deeplink-to-ai-coding-tools](https://linear.app/changelog/2026-02-26-deeplink-to-ai-coding-tools?ref=escape.tech)
- Cloudflare Agents docs: [https://developers.cloudflare.com/agents/](https://developers.cloudflare.com/agents/?ref=escape.tech)