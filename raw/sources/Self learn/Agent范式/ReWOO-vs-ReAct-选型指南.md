---
credibility: low
---
![ReWOO vs. ReAct: Choosing the right agent architecture for the job](https://www.nutrient.io/_astro/article-header.DRitc8N4_nlEwh.webp)

ReWOO vs. ReAct: Choosing the right agent architecture for the job

Picture this: You’re building an AI agent to process hundreds of documents, extract specific data, and generate reports. Should your agent think and act in real time? Or should it plan everything upfront like a project manager?

This fundamental choice between reactive and planned execution shapes how your AI agent will perform. And this blog post will explore ReAct vs. ReWOO — two powerful but very different approaches to agent architecture.

TL;DR

ReAct agents think-act-observe in loops — great for interactive tasks. ReWOO agents plan everything upfront, and then execute — perfect for structured processing.

## ReAct: Costly (sometimes), slow (sometimes), but reliable (sometimes)

The [ReAct](https://arxiv.org/abs/2210.03629) pattern is simple. The “Re” stands for reasoning, and the “Act” stands for action. It’s essentially the trial and error pattern.

ReAct instructs the agent to operate in a loop. The agent generates a thought (chain-of-thought reasoning), takes an action (like searching or calling a tool), observes the result, and repeats.

Here’s how a ReAct agent processes a document analysis task, showing the think-act-observe cycle in action with predefined tools:

```plaintext
User: Please flag this document for review if it exceeds the $100,000 threshold.

Thought: I need to find the contract value in this PDF.
Action: search_document("contract value")
Observation: Found "contract value: $125,000" on page 7.

Thought: Now I need to check if this exceeds our threshold.
Action: compare_value(125000, threshold=100000)
Observation: Value exceeds threshold by 25%.

Thought: I should flag this for review...
```

This tight feedback loop makes ReAct incredibly powerful for dynamic, interactive tasks where the goal isn’t well defined at the time of development and requires more context at runtime. [Research](https://arxiv.org/abs/2210.03629) showed it outperformed reasoning-only or acting-only methods (single-pass methods) across QA and decision-making tasks.

But there are drawbacks: Each cycle requires a new LLM prompt with the full conversation history. If the result isn’t found within the first few loops, you’re looking at large token costs and long delays. Essentially, sometimes it’s fast and cheap. Sometimes it’s slow and expensive. And most of that variance comes down to access to tools and the model’s ability.

## ReWOO: Plan first, execute later

Would you build a house without a plan? No. Neither should your agent. And that’s ReWOO.

[ReWOO](https://arxiv.org/abs/2305.18323) uses three distinct stages:

1. **Planner** — Breaks down the goal into tasks with placeholders.
2. **Worker** — Executes the plan with tools.
3. **Solver** — Pulls the results together to create a result.

Here’s how ReWOO handles the same document analysis task from above, breaking it into distinct planning and execution phases:

```plaintext
User: Please flag this document for review if it exceeds the $100,000 threshold.

# Planner
Goal: Determine whether the contract should be flagged for review based on its value.

Plan:
1. Extract the contract value from the document. → {{contract_value}}
2. Compare the extracted value to a threshold of $100,000. → {{comparison_result}}

# Worker
{{contract_value}} = search_document("contract value") → "contract value: $125,000" (page 7)
{{comparison_result}} = compare_value(125000, threshold=100000) → "Value exceeds threshold by 25%"

# Solver
The contract value is $125,000, which exceeds the threshold of $100,000 by 25%.
Therefore, this contract should be flagged for review.
```

All reasoning happens upfront with abstract placeholders. There’s no waiting for intermediate results, there are no token-heavy loops, and some work can even be done in parallel. On [HotpotQA benchmarks](https://hotpotqa.github.io/), GPT-3.5 ReWOO achieved 42.4 percent accuracy vs 40.8 percent for ReAct, while using ~2,000 tokens instead of 9,795. That’s an 80 percent reduction in token usage.

## Each approach has tradeoffs

While it may seem like you should jump on the ReWOO train right now, wait. Both approaches have their strengths and weaknesses. The best choice depends on the specific task and its requirements.

| Aspect | ReAct | ReWOO |
| --- | --- | --- |
| **Token usage** | High (~5× more) | Low |
| **Adaptability** | Can pivot mid-task | Plan is fixed upfront (mistakes are possible) |
| **Error recovery** | Can adapt and adjust tool calling | Usually a hard failure |
| **Latency** | Sequential, slower | Can parallelize execution |

## Real-world document use cases

So when should you choose each approach? It comes down to predictability and interaction patterns.

**ReAct shines when you need flexibility and adaptability**

**Live document chat** is where ReAct truly excels. When users are asking follow-up questions about documents, you never know what they’ll ask next. Your agent needs to adapt on the fly, building context from previous interactions and pivoting based on what users actually want to explore.

**Dynamic form filling** is another perfect fit. When each field depends on previous answers — like determining eligibility questions based on initial responses — ReAct’s ability to reason through dependencies step by step becomes invaluable.

**Exploratory data analysis** scenarios like “What patterns do you see in this report?” are inherently unpredictable. The agent might need to dig deeper into unexpected findings or change direction based on what the data reveals.

**ReWOO excels when you have structured, repeatable workflows**

**Batch document processing** is ReWOO’s sweet spot. When you need to extract data from 1,000 invoices that all follow the same structure, you can plan the extraction steps once and execute them efficiently in parallel across all documents.

**Compliance checks** work beautifully with ReWOO because you’re verifying contracts against a standard set of criteria. The checklist is known upfront, so you can plan all the validation steps and execute them systematically.

**Report generation** that combines data from multiple sources into summaries follows a predictable pattern that ReWOO can execute efficiently. Plan the data gathering, execute the collection, and then synthesize the results.

## How to improve on ReAct and ReWOO

An area we at Nutrient — and others — have been exploring is a hybrid approach. There are many directions you can go with this, but here are a few we’ve explored.

### 1\. ReWOO with ReAct fallbacks

First, the agent plans the tasks for the workers, and the workers begin to execute in a ReWOO fashion.

If any of these workers fail, we revert to a ReAct execution loop with all the context gained from the ReWOO workers and attempt a recovery.

Here’s an example of how the hybrid approach recovers from a failed ReWOO execution:

```plaintext
User: Please flag this document for review if it exceeds the $100,000 threshold.

# Planner
Goal: Determine whether the contract should be flagged for review based on its value.

Plan:
1. Extract the contract value from the document. → {{contract_value}}
2. Compare the extracted value to a threshold of $100,000. → {{comparison_result}}

# Worker
{{contract_value}} = search_document("contract value") → ❌ ERROR: Term not found
{{comparison_result}} = skipped (due to missing input)

# ReAct Recovery
Thought: The direct search for "contract value" failed. Maybe it's phrased differently in the document.
Action: search_document("total amount")
Observation: Found "Total Contract Amount: $125,000" on page 7

Thought: This is likely the value we need. Let's try the comparison again.
Action: compare_value(125000, threshold=100000)
Observation: Value exceeds threshold by 25%

# Solver
The total contract amount is $125,000, which exceeds the threshold of $100,000 by 25%.
Therefore, this contract should be flagged for review.
```

### 2\. ReAct for structure discovery → ReWOO to scale

Sometimes you need to process thousands of documents, but you don’t know upfront how the data is structured or labeled. In this case, you can use ReAct iteratively on sample documents to discover field locations and phrasing, and then shift to a ReWOO pipeline to process the rest of the documents at scale. Here’s how this two-phase approach works:

```plaintext
User: Please flag any document for review if it exceeds the $100,000 threshold.

# Phase 1: ReAct (Exploration on Sample Documents)

Goal: Discover how target fields (e.g. contract value) are phrased or located in documents.

Document 1:
Thought: I need to find the contract value in this document.
Action: search_document("contract value")
Observation: Not found.

Thought: Try a different phrasing like "total amount".
Action: search_document("total amount")
Observation: Found "Total Contract Amount: $125,000" on page 7

Thought: This phrasing works. Note the label: "Total Contract Amount"
→ Field Mapping Learned: contract_value → "Total Contract Amount"

Document 2:
Thought: Try using "Total Contract Amount" directly.
Action: search_document("Total Contract Amount")
Observation: Found "Total Contract Amount: $93,400" on page 3
→ Field Mapping Confirmed

...

# Phase 2: Generalize Field Mapping
Discovered Field Mapping:
- contract_value → ["Total Contract Amount", "Contract Value", "Contract Total", etc.]

# Phase 3: ReWOO (Scale Up with Learned Field Phrases)

# Planner
Goal: Extract and evaluate contract values from a batch of documents

Plan:
1. Find the contract value using known label variations → {{contract_value}}
2. Compare it against the threshold of $100,000 → {{comparison_result}}

# Worker (for each document)
{{contract_value}} = search_document(["Total Contract Amount", "Contract Value", "Contract Total"])
→ e.g. "$93,400" on page 3

{{comparison_result}} = compare_value(93400, threshold=100000)
→ "Below threshold by 6.6%"

# Solver
For this document, the contract value is $93,400, which is below the threshold. No flag required.
```

In this, you can see field mappings were discovered via ReAct reasoning and trial/error, and once the agent has “learned” enough about the task at hand, it can hand off to the ReWOO executors.

### 3\. ReWOO within a ReAct executor

A ReAct agent may decide to run a high-level action (e.g. `run_financial_summary`), which internally executes a well-defined ReWOO-style pipeline — layering structured execution within an adaptable control shell. This is similar to a multi-agent approach where a supervisor can call subagents to complete a task. Here’s how this nested approach works:

```plaintext
User: Please run a financial summary on this contract

# ReAct Loop Begins

Thought: I need to determine whether this document presents any financial risks.
Action: run_financial_summary(document)

# Inside Action: run_financial_summary → triggers ReWOO pipeline

--- Begin Embedded ReWOO Pipeline ---

# Planner
Goal: Summarize key financial indicators and assess risk.

Plan:
1. Extract total contract value → {{contract_value}}
2. Extract payment terms → {{payment_terms}}
3. Extract penalties or late fees → {{penalties}}
4. Evaluate risk based on extracted values → {{risk_assessment}}

# Worker
{{contract_value}} = search_document(["Total Contract Amount", "Contract Value"])
→ "$125,000"

{{payment_terms}} = search_document(["Payment Terms", "Payable within", "Due in"])
→ "Payable within 30 days of invoice"

{{penalties}} = search_document(["Penalty", "Late fee", "Interest charge"])
→ "Late payments incur a 5% monthly fee"

{{risk_assessment}} = assess_financial_risk(contract_value=125000, payment_terms="30 days", penalties="5% monthly fee")
→ "Moderate risk: High penalty rate for late payment"

# Solver
The document outlines a $125,000 contract payable within 30 days, with a 5% monthly penalty for late payment. This indicates a moderate financial risk.

--- End ReWOO Pipeline ---

# Back to ReAct Loop

Observation: Financial summary complete. Risk level: moderate.

Thought: Since the risk is moderate, I should flag this for manual review.
Action: flag_document(reason="Moderate financial risk")
Observation: Document flagged successfully.

Thought: Task complete.
```

## Conclusion

As you can see, agents can become complicated fast. So the best advice I can offer is this:

> Start simple with ReAct, and create quality tools that an LLM can reason about well.

ReAct helps you learn what tools your agent actually needs, how it reasons with them, and where things tend to break. That feedback loop is invaluable early on. Here’s a practical roadmap I follow when developing agents:

1. **Start with ReAct** — Build a simple agent with 2–3 core tools for your specific use case.
2. **Refine your tools** — Monitor how your agent uses each tool. Split tools that handle multiple distinct tasks into smaller, focused ones.
3. **Track token usage** — Identify where costs spike and which workflows consume the most tokens.
4. **Spot repetitive patterns** — Look for predictable sequences of tool calls that happen consistently across tasks.
5. **Migrate to ReWOO** — Convert your most token-heavy, repetitive workflows to ReWOO’s planned execution.
6. **Experiment with hybrid approaches** — For complex scenarios, combine ReAct’s flexibility with ReWOO’s efficiency using the patterns explored above.

Don’t feel pressured to complete every step — stop when your agent performs well enough for your needs.

Remember: The best architecture is the one that solves your specific problem efficiently. Don’t optimize prematurely — let your use case guide your choice.