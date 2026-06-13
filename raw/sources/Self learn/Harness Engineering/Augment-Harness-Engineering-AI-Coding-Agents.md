Harness engineering is the discipline of designing environments, constraints, and feedback loops that make AI coding agents reliable at scale, shifting engineers from writing code to designing the systems that govern how agents write code.

## TL;DR

[AI coding agents](https://www.augmentcode.com/tools/best-ai-coding-agent-desktop-apps) generate code faster than teams can review it, and the failures they introduce follow a predictable pattern: architecture drift, inconsistent security controls, and compliance gaps that pass all tests before surfacing in production. The question is not whether to constrain agent behavior, but which type of constraint addresses the specific failure mode. Agents producing inconsistent output across sessions need rules files and a verified architectural context. Agents introducing security gaps need deterministic enforcement at the CI layer. Agents drifting from spec need a verification loop that checks implementations against a persistent contract.

## Why AI Agents Need Constraints, Not Just Instructions

Engineering teams adopting AI coding agents face a paradox: agents generate code at unprecedented speed, but that speed creates a verification bottleneck. The [DORA report](https://dora.dev/insights/balancing-ai-tensions) found that higher AI adoption correlates with increases in both software delivery throughput and software delivery instability. Time saved writing code is often re-spent auditing it.

[Apiiro's Sep 2025 analysis](https://apiiro.com/blog/4x-velocity-10x-vulnerabilities-ai-coding-assistants-are-shipping-more-risks/) found that AI-generated code introduced more than 10,000 new security findings per month by June 2025 across the studied repositories (a 10x increase from Dec 2024). [Spotify's Honk system](https://engineering.atspotify.com/2025/11/spotifys-background-coding-agent-part-1), which has merged 1,500+ AI-generated PRs across hundreds of repositories since mid-2024, addresses similar agent reliability challenges through verification loops.

The root cause is architectural, not behavioral. Telling an agent "follow our coding standards" in a prompt is fundamentally different from wiring a linter that blocks the PR when standards are violated. The first approach relies on probabilistic compliance; the second enforces deterministic constraints. Harness engineering formalizes this distinction.

## What Is Harness Engineering: Origin and Definition

The term "harness engineering" is commonly attributed to Mitchell Hashimoto, co-founder of HashiCorp and creator of Terraform, in a [blog post published in early February 2026](https://mitchellh.com/writing/my-ai-adoption-journey). The original post URL has not been independently recovered, so this attribution is based on secondary reports: the core principle being that whenever an agent makes a mistake, engineers should build a solution ensuring the agent never makes that specific mistake again.

The concept gained a formal definition through an [OpenAI post](https://openai.com/index/harness-engineering/) by Ryan Lopopolo on February 11, 2026, built on the experience of shipping a production application with zero manually written lines of code. The tagline: "Humans steer. Agents execute." A [LangChain post](https://blog.langchain.com/the-anatomy-of-an-agent-harness/) condensed the model: "Agent = Model + Harness."

A common misattribution: Andrej Karpathy coined [context engineering](https://x.com/karpathy/status/2002118205729562949) (Dec 2025) and [agentic engineering](https://x.com/karpathy/status/2026731645169185220) (Feb 2026), not harness engineering.

| Term | Attributed To | Primary Source | Date |
| --- | --- | --- | --- |
| Harness engineering | Mitchell Hashimoto (per secondary reports) | Personal blog, "My AI Adoption Journey." | Early Feb 2026 |
| Harness engineering (formal) | OpenAI / Ryan Lopopolo | openai.com/index/harness-engineering | Feb 11, 2026 |
| Agentic engineering | Andrej Karpathy | x.com/karpathy | Feb 2026 |
| Context engineering | Andrej Karpathy | x.com/karpathy | Dec 19, 2025 |

## Harness Engineering vs. Prompt Engineering vs. Context Engineering

Harness engineering occupies a distinct architectural layer from prompt engineering and context engineering. Understanding the boundaries prevents teams from applying single-turn techniques to multi-session, multi-agent problems.

Prompt engineering optimizes instructions for a single interaction. Context engineering curates the token set across turns within one context window. Harness engineering operates outside both: it introduces context resets, structured handoff artifacts, and phase gates that enable coherent, goal-directed work across multiple context windows.

An [arXiv analysis](https://arxiv.org/html/2603.05344v1) describes the harness as orchestrating tool dispatch, context management, and safety enforcement at runtime, with the tool registry and safety system as distinct components alongside the prompt composition layer.

| Dimension | Prompt Engineering | Context Engineering | Harness Engineering |
| --- | --- | --- | --- |
| Scope | Single interaction | Model's context window across turns | Entire agent system |
| What it controls | Instruction wording | Token selection, ordering, compaction | Tool orchestration, state persistence, verification loops, error recovery |
| Failure modes addressed | Unclear instructions | Wrong or missing information in context | Agent errors, doom loops, multi-session drift, unsafe actions |
| Temporal boundary | One turn | One context window | Multiple context windows; full task lifetime |

### See how Intent's Coordinator, Verifier, and living specs keep multi-agent workflows aligned.

[Build with Intent](https://www.augmentcode.com/product/intent)

Free tier available · VS Code extension · Takes 2 minutes

ci-pipeline

···

$ cat build.log | auggie --print --quiet \\

"Summarize the failure"

Build failed due to missing dependency 'lodash'  
in src/utils/helpers.ts:42

Fix: npm install lodash @types/lodash

## The Three Harness Layers: Constraints, Feedback Loops, Quality Gates

Harness engineering operates through reinforcing layers: preventive controls that stop unwanted outputs before they occur, and corrective controls that detect violations and trigger a response. Teams starting from zero should implement them in order: constraint harnesses first because they reduce failure volume before anything else is in place, feedback loops second because they enable self-correction without human intervention, quality gates third because they enforce what the first two layers could not prevent.

One tradeoff applies to all three: over-constraining is a real failure mode. Complexity limits set too low flag legitimate refactoring; lint rules that reject valid patterns slow agents without improving output quality. Start narrow, measure, then expand.

### Layer 1: Constraint Harnesses (Feedforward)

Constraint harnesses reduce the agent's solution space before generation begins. Rules files, architectural lint configurations, and type systems all function as feedforward controls. They encode what the correct code looks like, so the agent converges faster on compliant output.

[OpenAI's production system](https://openai.com/index/harness-engineering/) enforces what it calls taste invariants: a small set of rules that encode the team's engineering standards and design philosophy, including general coding conventions and reliability requirements. All are enforced as hard CI failures, not warnings.

### Layer 2: Feedback Loops (Corrective)

Feedback loops return structured error signals to the agent, enabling autonomous self-correction. The critical implementation detail is that the lint message itself becomes a prompt. A lint error saying "violation detected" requires human interpretation. A lint error saying "use `logger.info({event: 'name', ...data})` instead of `console.log` " enables the agent to fix the violation without human intervention.

One implementation detail most teams overlook: inline-disable rules, such as `// eslint-disable-next-line`, should be disabled to prevent agents from suppressing violations rather than fixing them.

### Layer 3: Quality Gates (Enforcement)

Quality gates prevent non-compliant code from being merged. Standard CI pipelines are insufficient for AI-generated code because agents introduce problems that conventional checks miss. Some teams add purpose-built staleness gates to catch dependency choices that do not match the codebase's current strategy.

```javascript
// .eslintrc.js: Structural constraints for AI-generated code
module.exports = {
  rules: {
    "complexity": ["error", { "max": 10 }],
    "max-depth": ["error", 4],
    "max-lines-per-function": ["error", { "max": 50 }],
    "max-lines": ["error", { "max": 300 }],
    "max-params": ["error", 4],
    "max-statements": ["error", 15]
  }
}
```

All rules set to `"error"`, not `"warn"`, so they function as hard gates, not advisory signals.

## Rules Files as Constraint Harnesses

Rules files are persistent, repository-scoped instruction sets injected into an agent's context at session start. The mechanical distinction from simple prompts is precise: rules files survive across sessions, are injected automatically by the runtime, scope to an entire directory tree, and compose hierarchically across parent and child directories.

### The Cross-Tool Landscape

The [AGENTS.md spec](https://agents.md/), released in August 2025 as an open standard emerging from collaboration across the AI coding ecosystem including OpenAI, Google, Cursor, Factory, and others, now functions as a shared cross-tool convention. [OpenAI's repository](https://developers.openai.com/codex/guides/agents-md) uses 88 AGENTS.md files across subcomponents, demonstrating monorepo-scale constraint composition.

| Tool | File | Scope |
| --- | --- | --- |
| OpenAI Codex | AGENTS.md | Hierarchical, Git root to CWD |
| Claude Code | CLAUDE.md | Project root + ~/.claude |
| Cursor | .cursor/rules/\*.mdc | Project-scoped |
| GitHub Copilot | .github/copilot-instructions.md | Repo-wide + path-specific |
| Intent | AGENTS.md, CLAUDE.md, plus native Augment Rules | Cross-tool compatible |

### Augment Rules: Three-Type Constraint Architecture

Intent implements a rules system called Augment Rules with three rule types that provide granular control over agent behavior and when rules are loaded into context. Documented in the [rules reference](https://docs.augmentcode.com/cli/rules): `always_apply` rules, included in every prompt automatically; `agent_requested` rules, which load when the agent determines relevance; and `manual` rules, which load only when explicitly invoked. This selective loading preserves constraint enforcement while keeping the context window focused on the task.

Workspace rules live in the repository and are shared via version control. User-level rules in the home directory apply across all projects. The architectural distinction: Intent's Context Engine handles what can be inferred from the codebase; rules files are reserved for what cannot be inferred, such as naming conventions, logging standards, and architectural boundaries.

### Why Rules Files Alone Are Insufficient

Rules files are one layer of the harness, not the complete solution. LLM compliance with instructions is probabilistic, not deterministic. They must be combined with deterministic outer-harness constraints, such as linters and CI gates, to be reliable at scale.

[GitHub's analysis](https://github.blog/ai-and-ml/github-copilot/how-to-write-a-great-agents-md-lessons-from-over-2500-repositories/) of 2,500+ repositories using AGENTS.md files recommends a three-tier boundary pattern:

| Tier | Examples |
| --- | --- |
| Always | Log all notification delivery attempts; use UTC for scheduling |
| Ask First | Adding a new notification channel, changing retry intervals |
| Never | Send notifications without verified opt-in; modify the unsubscribe flow |

Without the "Ask First" tier, an agent building retry logic picks an interval on its own.

## The PEV Loop: Plan, Execute, Verify as a Harness Pattern

The Plan-Execute-Verify (PEV) pattern is a three-phase agent architecture that separates planning from execution and enforces verification as a structured feedback loop. Rather than asking an LLM to solve a multi-step problem in one pass, PEV instructs the agent to decompose the problem into an explicit plan, execute against that plan, then verify the output against both the plan and external quality criteria.

### How PEV Differs from Generate-and-Check

The distinction is architectural, not cosmetic. A generate-and-check workflow runs tests after the agent produces output. PEV enforces phase boundaries with gates at every transition.

| Dimension | Generate-and-Check | PEV Loop |
| --- | --- | --- |
| Planning | None; LLM generates directly | Explicit decomposition with acceptance criteria |
| Execution scope | Unconstrained | Bounded by plan; harness gates fire on every tool call |
| Verification timing | Post-hoc only | Pre-execution + runtime + post-execution + plan alignment |
| Feedback signal | Binary pass/fail | Error messages with context looped back into agent reasoning |
| Human involvement | Review output artifacts | Maintain harness; approve at high-leverage decision points |

Pre-execution gates fire before any tool call: Is this a known tool? Are the arguments valid? Does this action require user approval? Is the requested path inside the workspace?

A distinct gate type addresses what test suites alone cannot: plan alignment. Did the agent use the existing auth middleware or create a new one? Did it follow the response format convention? These are architectural questions invisible to standard test runners.

### Why PEV Addresses Non-Determinism

AI agents introduce [non-determinism](https://www.augmentcode.com/guides/deterministic-vs-non-deterministic-ai-key-differences-for-enterprise-development) into application logic: the same task at different times may produce different reasoning paths. PEV addresses this by reducing degrees of freedom at the Plan phase, rejecting out-of-scope tool calls pre-execution, and catching architecturally non-compliant paths that test suites cannot see.

### Explore how Intent's Coordinator agent decomposes specs into structured plans that constrain parallel Implementor agents.

[Build with Intent](https://www.augmentcode.com/product/intent)

Free tier available · VS Code extension · Takes 2 minutes

## Intent's Verifier Agent as an Automated Harness

Intent implements a Coordinator-orchestrated [multi-agent architecture](https://www.augmentcode.com/guides/swarm-vs-supervisor) with three core agent roles. The Coordinator analyzes the codebase via the [Context Engine](https://augmentcode.com/context-engine), drafts a [living spec](https://www.augmentcode.com/guides/living-specs-vs-static-specs) covering goals, tasks, decisions, and trade-offs, and then delegates to Implementor agents to execute tasks in parallel. The Verifier agent closes the loop.

### How the Verifier Functions as a Harness Primitive

The Verifier agent checks each specialist's implementation against the living spec, validates cross-service dependencies via semantic analysis through the Context Engine, and flags violations before code reaches the PR stage. When the Verifier rejects an implementation, the rejection becomes a structured context for correction rather than being silently dropped.

Open source

augmentcode/augment.vim★611

[Star on GitHub](https://github.com/augmentcode/augment.vim?utm_source=blog&utm_medium=cta&utm_campaign=github&utm_content=harness-engineering-ai-coding-agents)

| Failure Type | Response | Owner |
| --- | --- | --- |
| Spec violation (code diverges from contract) | Block merge; inject failure context into agent retry loop | Agent or author |
| Integration regression (change breaks consumer) | Block deployment; notify dependent teams | Provider team |
| Infrastructure failure (verification tooling unavailable) | Pause gated deployments; investigate separately | Platform team |

Intent's Context Engine provides a shared codebase understanding, enabling cross-service verification. When multiple specialist agents run in parallel, they access the same semantic context and a shared, continuously updated specification. The Context Engine processes 400,000+ files with real-time indexing, so local changes are reflected in context queries in near real time.

### A Documented Limitation

No automated system catches every semantic drift in the spec itself. If the specification is incorrect, downstream validation is affected too. Human review of the spec remains part of the workflow: developers can stop the Coordinator at any time to edit the spec before implementation begins.

## Measuring Harness Effectiveness: Agent Success Rate, Rework Rate, and Beyond

Harness engineering without measurement is guesswork. [DORA guidance](https://dora.dev/guides/how-to-innovate-with-generative-ai/) defines software delivery performance using core metrics that track changes in throughput and stability over time.

| Metric | What It Measures | Measurement Method |
| --- | --- | --- |
| Task Resolution Rate | Percentage of tasks an agent resolves correctly, verified by automated tests | Per-commit or per-PR test pass/fail |
| Code Churn Rate | Percentage of code written, then discarded or rewritten within two weeks | Weekly, attributed by authorship signal |
| Verification Tax | The time engineers spend auditing AI-generated code that offsets the generation speed | Delta between time-to-first-commit and time-to-PR-approval |
| Harness Constraint Effect | Improvement in task success from constraining the agent environment, independent of model changes | Success rate comparison: constrained vs. unconstrained on identical tasks |
| Defect Escape Rate | Rate of defects in AI-generated code reaching production | Monthly, tagged by AI vs. non-AI commit metadata |
| Pass@1 Rate | Whether the agent resolves correctly on the first attempt, without retries | Per evaluation run |

### Benchmarks and Baselines

Top agents achieve 65–76.8% resolution rates on [SWE-bench-verified](https://www.swebench.com/) Python tasks. [METR found](https://metr.org/notes/2026-03-10-many-swe-bench-passing-prs-would-not-be-merged-into-main/), however, that many benchmark-passing PRs would not be merged by actual maintainers. Teams need both metrics.

The DORA report found 30% of developers reported little to no trust in AI-generated code. A harness that makes agent behavior predictable reduces the cognitive burden of review, which DORA frames explicitly as a trust architecture problem.

One finding underscores the power of constraint design: Vercel has reported that reducing an agent's available tools improved task success rates. However, the specific claim that this improvement exceeded any model upgrade is not supported by available evidence and should not be treated as a verified result.

### What to Avoid

DORA warns against relying on narrow, output-based metrics to measure actual productivity. Metrics like "lines of code accepted" or "number of AI suggestions used" measure volume, not reliability, and should not serve as primary signals of harness effectiveness.

## Start with Three Constraints Before Your Next Agent-Generated PR

The diagnostic question: which architectural invariants must hold regardless of who writes the code? OpenAI started with structured logging, naming conventions, file size limits, and reliability requirements.

Audit the last five agent-generated PRs for recurring debt patterns. Pick three constraints that would have blocked those issues. Encode them as lint rules with remediation-instruction error messages, fail CI on violations, and measure review time and defect escape rate before and after.

Intent's [pre-merge verification](https://www.augmentcode.com/guides/ai-agent-pre-merge-verification) architecture implements this pattern at scale: the Verifier agent, Augment Rules, and the Context Engine combine to constrain multi-agent workflows without slowing generation down.

### See how Intent's Verifier agent, Augment Rules, and the Context Engine constrain multi-agent workflows across large codebases.

[Build with Intent](https://www.augmentcode.com/product/intent)

Free tier available · VS Code extension · Takes 2 minutes

## Frequently Asked Questions About AI Agent Harness Engineering

## Related Guides

- [AI Coding Agents vs Autocomplete: 6 Key Architecture Gaps](https://www.augmentcode.com/guides/ai-coding-agents-vs-autocomplete-6-key-architecture-gaps)
- [6 AI-Powered Code Linter Platforms for Quality Gate Automation](https://www.augmentcode.com/guides/6-ai-powered-code-linter-platforms-for-quality-gate-automation)
- [6 AI Tools for Framework-Aware Test Generation](https://www.augmentcode.com/guides/6-ai-tools-for-framework-aware-test-generation)
- [7 Benchmarks to Evaluate AI Security Tools for Enterprise](https://www.augmentcode.com/guides/7-benchmarks-to-evaluate-ai-security-tools-for-enterprise)
- [12 Faster Testing Strategies for Large Codebases That Work](https://www.augmentcode.com/guides/12-faster-testing-strategies)

### Written by

![Molisha Shah](https://www.augmentcode.com/_next/image?url=https%3A%2F%2Fcdn.sanity.io%2Fimages%2Foraw2u2c%2Fproduction%2Fb7a077e3fd165f37be21b9280f6775d2a598d290-432x432.png&w=128&q=75)

#### Molisha Shah

Molisha is an early GTM and Customer Champion at Augment Code, where she focuses on helping developers understand and adopt modern AI coding practices. She writes about clean code principles, agentic development environments, and how teams are restructuring their workflows around AI agents. She holds a degree in Business and Cognitive Science from UC Berkeley.