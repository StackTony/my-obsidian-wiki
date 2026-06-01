---
credibility: low
---
> ****Who this is for**: ML engineers and AI builders running LLM agents in production — especially ReAct-style systems using LangChain, LangGraph, AutoGen, or custom tool loops. If you’re new to ReAct, it’s a prompting pattern where an LLM alternates between Thought, Action, and Observation steps to solve tasks using tools.**

---

are burning the majority of their retry budget on errors that can never succeed.

In a 200-task benchmark, **90.8% of retries were wasted** — not because the model was wrong, but because the system kept retrying tools that didn’t exist. Not “unlikely to succeed.” Guaranteed to fail.

I didn’t find this by tuning prompts. I found it by instrumenting every retry, classifying every error, and tracking exactly where the budget went. The root cause turned out to be a single architectural assumption: letting the model choose the tool name at runtime.

Here’s what makes this particularly dangerous. Your monitoring dashboard is almost certainly not showing it. Right now it probably shows:

- Success rate: fine
- Latency: acceptable
- Retries: within limits

What it does not show: how many of those retries were impossible from the first attempt. That’s the gap this article is about.

> **Simulation note:** All results come from a deterministic simulation using calibrated parameters, not live API calls. The hallucination rate (28%) is a conservative estimate for tool-call hallucination in ReAct-style agents derived from failure mode analysis in published GPT-4-class benchmarks (Yao et al., 2023; Shinn et al., 2023) — it is not a directly reported figure from those papers. Structural conclusions hold as architectural properties; exact percentages will vary in production. Full limitations are discussed at the end. Reproduce every number yourself: `python app.py --seed 42`.

**GitHub Repository:** [https://github.com/Emmimal/react-retry-waste-analysis](https://github.com/Emmimal/react-retry-waste-analysis)

In production, this means you’re paying for retries that cannot succeed—and starving the ones that could.

---

![Architecture diagram comparing two agent designs side by side. Left side labeled ReAct agent shows a flow where the LLM outputs a tool name string, which passes to TOOLS.get(tool_name) at runtime. A hallucinated name returns None, feeds into a global retry counter with no error taxonomy, exhausts the budget, and causes a silent task failure — 466 wasted retries at 90.8%. Right side labeled Controlled workflow shows the LLM outputting a step type only, which passes to plan_workflow, then to STEP_TO_TOOL dict lookup which is always valid, then through error taxonomy classifying retryable versus non-retryable errors, reaching tool_fn cleanly — 0 wasted retries, hallucination impossible.](https://contributor.insightmediagroup.io/wp-content/uploads/2026/04/architecture_diagram-1024x721.png)

Left: string-based tool routing passes the model’s output directly to TOOLS.get() — a hallucinated name returns None, burns retry budget through a global counter with no error taxonomy, and fails silently. Right: deterministic routing resolves tool names from a Python dict at plan time, classifies errors before retrying, and makes hallucination at the routing layer structurally impossible. Image by Author.

---

## TL;DR

**90.8% of retries were wasted on errors that could never succeed. Root cause:** letting the model choose tool names at runtime (`TOOLS.get(tool_name)`). Prompts don’t fix it — a hallucinated tool name is a permanent error. No retry can make a missing key appear in a dictionary.

**Three structural fixes eliminate the problem:** classify errors before retrying, use per-tool circuit breakers, move tool routing into code. Result: 0% wasted retries, 3× lower step variance, predictable execution.

---

## The Law This Article Is Built On

Before the data, the principle — stated once, bluntly:

**Retrying only makes sense for errors that can change. A hallucinated tool name cannot change. Therefore, retrying it is guaranteed waste.**

This is not a probability argument. It is not “hallucinations are rare enough to ignore.” It is a logical property: `TOOLS.get("web_browser")` returns `None` on the first attempt, the second, and every attempt after. The tool does not exist. The retry counter does not know that. It burns a budget slot anyway.

The entire problem flows from this mismatch. The fix does too.

---

## The One Line Silently Draining Your Retry Budget

It appears in almost every ReAct tutorial. You’ve probably written it:

```python
tool_fn = TOOLS.get(tool_name)   # ◄─ THE LINE

if tool_fn is None:
    # No error taxonomy here.
    # TOOL_NOT_FOUND looks identical to a transient network blip.
    # The global retry counter burns budget on a tool
    # that will never exist — and logs that as a "failure".
```

This is the line. Everything else in this article follows from it.

When an LLM hallucinates a tool name — `web_browser`, `sql_query`, `python_repl` — `TOOLS.get()` returns `None`. The agent knows the tool doesn’t exist. The global retry counter does not. It treats `TOOL_NOT_FOUND` identically to `TRANSIENT`: same budget slot, same retry logic, same backoff.

The cascade: every hallucination consumes retry slots that could have handled a real failure. When a genuine network timeout arrives two steps later, there is nothing left. The task fails — logged as generic retry exhaustion, with no trace of a hallucinated tool name being the root cause.

If your logs contain retries on `TOOL_NOT_FOUND`, you already have this problem. The only question is what fraction of your budget it’s consuming. In this benchmark, the answer was 90.8%.

---

## The Benchmark Setup

Two agents, 200 tasks, same simulated parameters, same tools, same failure rates — with one structural difference.

> **Comparison note:** This benchmark compares a naive ReAct baseline against a workflow with all three fixes applied. Fixes 1 (error taxonomy) and 2 (per-tool circuit breakers) are independently applicable to a ReAct agent without changing its architecture. Fix 3 (deterministic tool routing) is the structural differentiator — it’s what makes hallucination at the routing layer impossible. The gap shown is cumulative; keep this in mind when reading the numbers.

**ReAct agent:** Standard Thought → Action → Observation loop. Single global retry counter (`MAX_REACT_RETRIES = 6`, `MAX_REACT_STEPS = 10`). No error taxonomy. Tool name comes from LLM output at runtime. Each hallucinated tool name burns exactly 3 retry slots (`HALLUCINATION_RETRY_BURN = 3`) — this constant directly drives the 90.8% waste figure and is discussed further in Limitations.

**Controlled workflow:** Deterministic plan execution where tool routing is a Python dict lookup resolved at plan time. Error taxonomy applied at the point of failure. Per-tool circuit breakers (trips after 3 consecutive failures, recovery probe after 5 simulated seconds, closes after 2 probe successes). Retry logic scoped to error class.

**Simulation parameters:**

| Parameter | Value | Notes |
| --- | --- | --- |
| Seed | 42 | Global random seed |
| Tasks | 200 | Per experiment |
| Hallucination rate | 28% | Conservative estimate from published benchmarks |
| Loop detection rate | 18% | Applied to steps with history length > 2 |
| `HALLUCINATION_RETRY_BURN` | 3 | Retry slots burned per hallucination |
| `MAX_REACT_RETRIES` | 6 | Global retry budget |
| `MAX_REACT_STEPS` | 10 | Step cap per task |
| Token cost proxy | $3/1M tokens | Mid-range estimate for GPT-4-class models |
| Sensitivity rates | 5%, 15%, 28% | Hallucination rates for sweep |

This constant is the direct mechanical driver of the 90.8% waste figure. At a value of 1, fewer slots are burned per event — the workflow’s wasted count stays at 0 regardless. Run the sensitivity check yourself: modify this constant and observe that the workflow always wastes zero retries.

The simulation uses three tools — `search`, `calculate`, `summarise` — with realistic failure rates per tool. Tool cost is tracked at 200 tokens per LLM step.

Every number in this article is reproduced exactly by `python app.py --seed 42`.

## What the Benchmark Found

### Success Rate Hides the Real Problem

ReAct succeeded on 179/200 tasks (89.5%). The workflow succeeded on 200/200 (100.0%).

![Bar charts comparing ReAct vs deterministic workflow showing success rate and hallucination events across 200 tasks, highlighting higher reliability and zero hallucinations in workflow.](https://contributor.insightmediagroup.io/wp-content/uploads/2026/04/fig1_success_hallucinations-1-1024x427.png)

ReAct vs deterministic workflow comparison shows similar success rates but a critical difference in hallucination events, where ReAct logs 155 hallucinations while the workflow eliminates them entirely, exposing a hidden reliability gap in agent design. Image by Author

The 10.5% gap is real. But success rate is a pass/fail metric — it says nothing about how close to the edge a passing run came, or what it burned to get there. The more informative number is what happened inside those 179 “successful” ReAct runs. Specifically: where did the retry budget go?

### The Retry Budget

![Stacked bar chart showing retry budget usage in ReAct vs workflow, highlighting 90.8% wasted retries in ReAct compared to zero wasted retries in deterministic workflow.](https://contributor.insightmediagroup.io/wp-content/uploads/2026/04/fig2_retry_budget-1-1024x506.png)

ReAct agents waste the majority of retry budget on non-retryable errors, while the workflow ensures every retry targets recoverable failures, revealing a major inefficiency in standard agent retry logic. Image by Author

| Metric | ReAct | Workflow |
| --- | --- | --- |
| Total retries | 513 | 80 |
| Useful (retryable errors) | 47 | 80 |
| Wasted (non-retryable errors) | **466** | **0** |
| Waste rate | **90.8%** | **0.0%** |
| Avg retries / task | 2.56 | 0.40 |

466 of 513 retries — 90.8% — targeted errors that cannot succeed by definition. The workflow fired 80 retries. Every single one was useful. The gap is 6.4× in total retries and 466-to-0 in wasted ones. That is not a performance difference. It is a structural one.

**A note on the mechanics:** `HALLUCINATION_RETRY_BURN = 3` means each hallucinated tool name burns exactly 3 retry slots in the ReAct simulation. The 90.8% figure is sensitive to this constant — at a value of 1, fewer retries are wasted per hallucination event. But the structural property holds at every value: the workflow wastes zero retries regardless, because non-retryable errors are classified and skipped before any slot is consumed. Run the sensitivity check yourself: modify `HALLUCINATION_RETRY_BURN` and observe that the workflow’s wasted count stays at 0.

### Why 19 of 21 ReAct Failures Had Identical Root Causes

| Failure reason | Runs | % of failures |
| --- | --- | --- |
| `hallucinated_tool_exhausted_retries` | 19 | 90.5% |
| `tool_error_exhausted_retries:rate_limited` | 1 | 4.8% |
| `tool_error_exhausted_retries:dependency_down` | 1 | 4.8% |

19 of 21 failures: hallucinated tool name, global retry budget exhausted, task dead. Not network failures. Not rate limits. Hallucinated strings retried until nothing was left. The workflow had zero failures across 200 tasks.

Your success rate dashboard will never surface this. The failure reason is buried inside the retry loop with no taxonomy to extract it. That is the dashboard blindness the title promises — and it is worse than it sounds, because it means you have no signal when things are degrading, only when they’ve already failed.

### The Error Taxonomy: From “Unknown” to Fully Classified

The root fix is classifying errors at the point they are raised. Three categories are retryable; three are not:

```python
# Retryable — can succeed on a subsequent attempt
RETRYABLE = {TRANSIENT, RATE_LIMITED, DEPENDENCY_DOWN}

# Non-retryable — retrying wastes budget by definition
NON_RETRYABLE = {INVALID_INPUT, TOOL_NOT_FOUND, BUDGET_EXCEEDED}
```

When every error carries a class, the retry decision becomes one line:

```python
if not exc.is_retryable():
    log(RETRY_SKIPPED)   # zero budget consumed
    break
```

The full taxonomy from the 200-task run:

![Horizontal bar chart showing error taxonomy distribution for ReAct and workflow agents, highlighting dominance of hallucination errors in ReAct and circuit breaker handling in workflow.](https://contributor.insightmediagroup.io/wp-content/uploads/2026/04/fig4_error_taxonomy-1-1024x506.png)

Error taxonomy exposes the root failure mode in ReAct agents, dominated by hallucination errors, while the workflow replaces them with controlled circuit breaker events for better fault handling. Image by Author

| Error kind | ReAct | Workflow |
| --- | --- | --- |
| hallucination | 155 | 0 |
| rate\_limited | 24 | 22 |
| dependency\_down | 16 | 23 |
| loop\_detected | 8 | 0 |
| transient | 7 | 26 |
| circuit\_open | 0 | 49 |
| invalid\_input | 1 | 0 |

ReAct’s dominant event is `hallucination` — 155 events, all non-retryable, all burning budget. The workflow’s dominant event is `circuit_open` — 49 fast-fails that never touched an upstream service. The workflow logged zero hallucination events because it never asks the model to produce a tool name string.

> **You cannot hallucinate a key in a dict you never ask the model to produce.**

This is an architectural guarantee within the simulation design. In a real system where the LLM contributes to plan generation, hallucinations could still occur upstream of tool routing. The guarantee holds precisely where routing is fully deterministic and the model’s output is limited to plan structure — not tool name strings.

The eight `loop_detected` events in ReAct come from a 18% loop rate applied when `len(history) > 2` — the model “decides to think more” rather than act, consuming a step without calling a tool. The workflow has no equivalent because it doesn’t give the model step-selection authority.

### Step predictability: the hidden instability σ reveals

![Histogram comparing step distribution of ReAct and workflow agents, showing higher variance and unpredictable execution steps in ReAct versus tightly clustered steps in workflow.](https://contributor.insightmediagroup.io/wp-content/uploads/2026/04/fig3_step_distribution-1-1024x410.png)

Step distribution reveals hidden instability in ReAct agents, where high variance leads to unpredictable execution, while the workflow maintains consistent and controlled step counts. Image by Author

| Metric | ReAct | Workflow |
| --- | --- | --- |
| Avg steps / task | 2.88 | 2.69 |
| Std dev (σ) | **1.36** | **0.46** |

The means are nearly identical. The distributions are not. Standard deviation is 3× higher for ReAct.

Workflow σ holds at 0.46 across all hallucination rates tested — not by coincidence, but because plan structure is fixed. Task type (math, summary, search) determines step count at plan time. The hallucination roll doesn’t affect step count when tool routing never passes through the model’s output.

In production, high σ means: unpredictable latency (SLAs cannot be committed to), unpredictable token cost (budget forecasts are inaccurate), and invisible burst load (a bad cluster of long-running tasks arrives with no warning). Predictability is a production property. Success rate does not measure it. σ does.

---

## The Three Structural Fixes

### Fix 1: Classify Errors Before Deciding Whether to Retry

The root fix is classifying errors at the point they are raised. Three categories are retryable; three are not:

```python
def call_tool_with_retry(tool_name, args, logger, ledger,
                         step, max_retries=2, fallback=None):
    for attempt in range(max_retries + 1):
        try:
            return call_tool_with_circuit_breaker(tool_name, args, ...)
        except AgentError as exc:
            if not exc.is_retryable():
                # Non-retryable: RETRY_SKIPPED — zero budget consumed
                logger.log(RETRY_SKIPPED, error_kind=exc.kind.value)
                break                          # ← this line drops waste to 0
            if attempt < max_retries:
                ledger.add_retry(wasted=False)
                backoff = min(0.1 * (2 ** attempt) + jitter, 2.0)
                logger.log(RETRY, attempt=attempt, backoff=backoff)
    if fallback:
        return ToolResult(tool_name, fallback, 0.0, is_fallback=True)
    raise last_error
```

`RETRY_SKIPPED` is the audit event that proves taxonomy is working. Search your production logs for it to see exactly which non-retryable errors were caught at which step, in which task, with zero budget consumed. ReAct cannot emit this event — it has no taxonomy to skip from.

**This fix is applicable to a ReAct agent today** without changing its tool routing architecture. If you run LangChain or AutoGen, you can add error classification to your tool layer and scope your retry decorator to `TransientToolError` without touching anything else. It will not eliminate hallucination-driven waste entirely — that requires Fix 3 — but it prevents `INVALID_INPUT` and other permanent errors from burning retries on attempts that also cannot succeed.

### Fix 2: Per-Tool Circuit Breakers Instead of a Global Counter

A global retry counter treats all tools as a single failure domain. When one tool degrades, it drains the budget for every other tool. Per-tool circuit breakers contain failure locally:

```python
# Each tool gets its own circuit breaker instance
# CLOSED    → calls pass through normally
# OPEN      → calls fail immediately, no upstream hit, no budget consumed
# HALF-OPEN → one probe call; if it succeeds, circuit closes

class CircuitBreaker:
    failure_threshold: int   = 3    # trips after 3 consecutive failures
    recovery_timeout:  float = 5.0  # simulated seconds before probe allowed
    success_threshold: int   = 2    # probe successes needed to close
```

The benchmark logged 49 `CIRCUIT_OPEN` events for the workflow — every one a call that fast-failed without touching a degraded upstream service and without consuming retry budget. ReAct logged zero, because it has no per-tool state. It hammers a degraded tool until the global budget is gone.

Like Fix 1, **this is independently applicable to a ReAct agent**. Per-tool circuit breakers wrap the tool call layer regardless of how the tool was selected. Threshold values will need tuning for your workload.

### Fix 3: Deterministic Tool Routing (The Structural Differentiator)

This is the fix that eliminates the hallucination problem at the routing layer. Fixes 1 and 2 reduce the damage from hallucinations; Fix 3 makes them structurally impossible where it is applied.

```python
# ReAct — tool name comes from LLM output, can be any string
tool_name = llm_response.tool_name       # "web_browser", "sql_query", ...
tool_fn   = TOOLS.get(tool_name)         # None if hallucinated → budget burns

# Workflow — tool name resolved from plan at task start, always valid
STEP_TO_TOOL = {
    StepKind.SEARCH:    "search",
    StepKind.CALCULATE: "calculate",
    StepKind.SUMMARISE: "summarise",
}
tool_name = STEP_TO_TOOL[step.kind]      # KeyError is impossible; hallucination is impossible
```

Use the LLM for reasoning — what steps are needed, in what order, with what arguments. Use Python for tool routing. The model contributes plan structure (step types), not tool name strings.

**The trade-off is worth naming honestly:** deterministic routing requires that your task structure maps onto a finite set of step types. For open-ended agents that need to dynamically compose novel tool sequences across a large registry, this constrains flexibility. For systems with predictable task structures — the majority of production deployments — the reliability and predictability gains are substantial.

**Before/after summary:**

| Dimension | Before (naive ReAct) | After (all three fixes) | Trade-off |
| --- | --- | --- | --- |
| Wasted retries | 90.8% | 0.0% | None |
| Hallucination events | 155 | 0 | Loses dynamic tool discovery |
| Step σ | 1.36 | 0.46 | Loses open-ended composition |
| Circuit isolation | None (global) | Per-tool | Adds threshold-tuning work |
| Auditability | None | Full taxonomy | Adds logging overhead |

---

## The Sensitivity Analysis: The 5% Result Is the Alarming One

![Three-panel chart showing sensitivity analysis across different hallucination rates for success rate, wasted retry rate, and step standard deviation.](https://contributor.insightmediagroup.io/wp-content/uploads/2026/04/fig6_sensitivity-1-1024x354.png)

Sensitivity analysis across hallucination rates (5%, 15%, 28%). The workflow maintains 0% wasted retries and stable σ = 0.46 at every rate, while ReAct’s wasted retries rise sharply with hallucinations. Image by Author.

| Hallucination rate | ReAct wasted % | Workflow wasted % | ReAct σ | Workflow σ | ReAct success |
| --- | --- | --- | --- | --- | --- |
| 5% | 54.7% | 0.0% | 1.28 | 0.46 | 100.0% |
| 15% | 81.4% | 0.0% | 1.42 | 0.46 | 98.0% |
| 28% | 90.8% | 0.0% | 1.36 | 0.46 | 89.5% |

The 5% row deserves particular attention. ReAct shows 100% success — your monitoring reports a healthy agent. But 54.7% of retries are still wasted. The budget is quietly draining.

This is the dashboard blindness made precise. When a real failure cluster arrives — a rate limit spike, a degraded service, a brief outage — less than half your designed retry capacity is available to handle it. You will not see this coming. Your success rate was 100% until the moment it wasn’t.

The workflow wastes 0% of retries at every rate tested. The σ holds at 0.46 regardless of hallucination frequency. These are not rate-dependent improvements — they are properties of the architecture.

---

## Latency: What the CDF Reveals That Averages Hide

![Latency cumulative distribution function comparing ReAct and workflow agents, showing similar P95 latency despite higher average latency in workflow.](https://contributor.insightmediagroup.io/wp-content/uploads/2026/04/fig5_latency_cdf-1-1024x506.png)

Latency distribution shows that despite higher average latency, the workflow matches ReAct at P95, proving that reliability improvements do not come at the cost of tail performance. Image by Author

| Metric | ReAct | Workflow |
| --- | --- | --- |
| Avg latency (ms) | 43.4 | 74.8 |
| P95 latency (ms) | 143.3 | 146.2 |
| Total tokens | 115,000 | 107,400 |
| Estimated cost ($) | $0.3450 | $0.3222 |

The workflow appears slower on average because failed ReAct runs exit early — they look fast because they failed fast, not because they completed efficiently. At P95 — the metric that matters for SLA commitments — the latency is effectively identical: 143.3ms versus 146.2ms.

You are not trading tail latency for reliability. At the tail, the simulation shows you can have both. Token cost favors the workflow by 6.6%, because it doesn’t burn LLM steps on hallucination-retry loops that produce no useful output.

---

## Three Diagnostic Questions for Your System Right Now

Before reading the implementation guidance, answer these three questions about your current agent:

**1\. When a tool name from the model doesn’t match any registered tool, does your system retry?** If yes, budget is draining on non-retryable errors right now.

**2\. Is your retry counter global or per-tool?** A global counter lets one degraded tool exhaust the budget for all others.

**3\. Can you search your logs for `RETRY_SKIPPED` or an equivalent event?** If not, your system has no error taxonomy and no audit trail for wasted budget.

If you answered “yes / global / no” to these three — Fix 1 and Fix 2 are the fastest path to recovery, applicable without changing your agent architecture.

---

## Implementing This in Your Stack Today

These three fixes can be applied incrementally to any framework — LangChain, LangGraph, AutoGen, or a custom tool loop.

**Step 1 — Add error classification (30 minutes).** Define two exception classes in your tool layer: one for retryable errors (`TransientToolError`), one for permanent ones (`ToolNotFoundError`, `InvalidInputError`). Raise the appropriate class at the point the error is detected.

**Step 2 — Scope retries to error class (15 minutes).** If you use `tenacity`, swap `retry_if_exception` for `retry_if_exception_type(TransientToolError)`. If you use a custom loop, add `if not exc.is_retryable(): break` before the retry increment.

**Step 3 — Move tool routing into a dict (1 hour).** If you have a fixed task structure, define it as a `StepKind` enum and resolve tool names from `dict[StepKind, str]` at plan time. Optional if your use case requires open-ended tool composition, but it eliminates hallucination-driven budget waste entirely where it can be applied.

Here is what the vulnerability looks like in LangChain, and how to fix it:

**Vulnerable pattern:**

```python
from langchain.agents import AgentExecutor, create_react_agent

# If the model outputs "web_search" instead of "search",
# AgentExecutor will retry the step before failing —
# consuming budget on an error that cannot succeed.
executor = AgentExecutor(
    agent=create_react_agent(llm, tools, prompt),
    tools=tools,
    max_iterations=10
)
executor.invoke({"input": task})
```

**Fixed pattern — error taxonomy + deterministic routing:**

```python
from tenacity import retry, stop_after_attempt, retry_if_exception_type

class ToolNotFoundError(Exception): pass   # non-retryable
class TransientToolError(Exception): pass  # retryable

# Tool routing in Python — model outputs step type, not tool name
TOOL_REGISTRY = {"search": search_fn, "calculate": calc_fn}

def call_tool(name: str, args: str):
    fn = TOOL_REGISTRY.get(name)
    if fn is None:
        raise ToolNotFoundError(f"'{name}' not registered")  # never retried
    try:
        return fn(args)
    except RateLimitError as e:
        raise TransientToolError(str(e))   # retried with backoff

@retry(
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(TransientToolError)
)
def run_step(tool_name: str, args: str):
    return call_tool(tool_name, args)
```

> **Production note:** The `eval()` call in the benchmark’s `tool_calculate` is present for simulation purposes only. Never use `eval()` in a production tool — it is a code injection vulnerability. Replace it with a safe expression parser such as `simpleeval` or a purpose-built math library.

---

## Benchmark Limitations

**Hallucination rate is a parameter, not a measurement.** The 28% figure is a conservative estimate derived from failure mode analysis in Yao et al. (2023) and Shinn et al. (2023) — not a directly reported figure from either paper. A well-prompted model with a clean tool schema and a small, well-named tool registry may hallucinate tool names far less frequently. Run the benchmark at your actual observed rate.

**`HALLUCINATION_RETRY_BURN` is a simulation constant that drives the waste percentage.** At a value of 1, fewer retries are wasted per hallucination event; the 90.8% figure would be lower. The structural conclusion — the workflow wastes 0% at all values — holds regardless. Run `python app.py --seed 42` with modified values of 1 and 2 to verify.

**The workflow’s zero hallucination count is a simulation design property.** Tool routing never passes through LLM output in this benchmark. In a real system where the LLM contributes to plan generation, hallucinations could occur upstream of routing.

**Three tools is a simplified environment.** Production agents typically manage dozens of tools with heterogeneous failure modes. The taxonomy and circuit breaker patterns scale well; threshold values will need tuning for your workload.

**Latency figures are simulated.** The P95 near-equivalence is the production-relevant finding. Absolute millisecond values should not inform capacity planning. Average latency comparisons are confounded by early-exit failures in ReAct and per-step LLM accounting in the workflow — use P95 for any latency reasoning.

---

## Full Metrics

Complete per-metric results for all 200 tasks (seed=42, hallucination\_rate=28%) are available in \`experiment\_results.json\` in the GitHub repository. Run \`python app.py -seed 42 -export-json\` to regenerate them locally.

---

## References

- Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. (2023). ReAct: Synergizing Reasoning and Acting in Language Models. *ICLR 2023.* [https://arxiv.org/abs/2210.03629](https://arxiv.org/abs/2210.03629)
- Shinn, N., Cassano, F., Gopinath, A., Narasimhan, K., & Yao, S. (2023). Reflexion: Language Agents with Verbal Reinforcement Learning. *NeurIPS 2023.* [https://arxiv.org/abs/2303.11366](https://arxiv.org/abs/2303.11366)
- Fowler, M. (2014). CircuitBreaker. *martinfowler.com.* [https://martinfowler.com/bliki/CircuitBreaker.html](https://martinfowler.com/bliki/CircuitBreaker.html)
- Nygard, M. T. (2018). *Release It! Design and Deploy Production-Ready Software* (2nd ed.). Pragmatic Bookshelf.
- Sculley, D., et al. (2015). Hidden technical debt in machine learning systems. *NeurIPS 2015.* [https://papers.nips.cc/paper/2015/hash/86df7dcfd896fcaf2674f757a2463eba-Abstract.html](https://papers.nips.cc/paper/2015/hash/86df7dcfd896fcaf2674f757a2463eba-Abstract.html)

---

## Disclosure

**Simulation methodology.** All results are produced by a deterministic simulation (`python app.py --seed 42`), not live API calls. The 28% hallucination rate is a calibrated parameter derived from failure mode analysis in published benchmarks — not a directly measured figure from live model outputs.

**No conflicts of interest.** The author has no financial relationship with any tool, framework, model provider, or company mentioned in this article. No products are endorsed or sponsored.

**Original work.** This article, its benchmark design, and its code are the author’s original work. References are used solely to attribute published findings that informed calibration and design.

---

*GitHub: [https://github.com/Emmimal/react-retry-waste-analysis](https://github.com/Emmimal/react-retry-waste-analysis)*

*`python app.py --seed 42` — full results and all six figures.* *`python app.py --replay 7` — verbose single-task execution, step by step.*