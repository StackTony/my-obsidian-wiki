# Agent Instruction Set Architecture (AISA) — Design Spec

**Date**: 2026-05-26
**Author**: Claudian (AI brainstorming)
**Status**: Draft — conceptual exploration, not implementation-ready

---

## 1. Overview

This document captures the conceptual exploration of mapping OS/ISA architecture concepts to Agent systems, producing both a comprehensive analogy framework and architectural design insights for a hypothetical "Agent Instruction Set Architecture" (AISA).

The analogy is built on three complementary perspectives:
- **Hardware-first** (LLM = non-deterministic CPU)
- **Scheduler-first** (Agent = process, Orchestrator = kernel)
- **Abstraction-first** (AISA = Runnable Protocol + Action Types + Permission Levels)

---

## 2. Core Analogy: Four-Layer Stack

```
Layer 4: Application (User Task / Multi-Agent Collaboration)
Layer 3: OS/Orchestrator (LangGraph StateGraph / Scheduler / Memory Manager)
Layer 2: ISA/Syscall (Runnable Protocol + Tool Calling + Action Types)
Layer 1: Hardware (LLM Engine + Context Window + Memory Store + MCP)
```

---

## 3. Layer 1: Hardware Layer

Key mappings and critical differences:

| Hardware | Agent | Critical Difference |
|----------|-------|---------------------|
| CPU | LLM | **Non-deterministic execution** — `ADD r1, r2` is deterministic; `THINK about X` is not |
| Registers | Context Window | Both finite; overflow handled by stack/memory compression |
| Cache | Prompt Cache | "Recently used data stays in fast storage" principle |
| RAM | Checkpoint | Working memory → thread-level state |
| Disk | Store/RAG | Persistent storage → cross-session knowledge |
| MMU | Context Manager | Virtual→physical address mapping → thread_id→checkpoint mapping |
| I/O devices | External tools | Disk/network card → API/database/browser |
| DMA | MCP | Device-to-memory data transfer → tool-to-agent data transfer |
| Interrupt controller | HITL interrupt | Hardware interrupt → human approval interrupt |
| BIOS | BaseAgent Protocol | Minimum boot specification → minimum agent runtime interface |

---

## 4. Layer 2: ISA/Syscall Layer

### 4.1 Five Instruction Types

| ISA Type | Agent Instruction | Semantics | Determinism | Ring | ReAct Mapping |
|----------|-------------------|-----------|-------------|------|---------------|
| R-type | THINK | Pure reasoning | High non-determinism | ring3 | Thought |
| I-type | OBSERVE | Receive input, update state | Low non-determinism | ring3 | Observation |
| J-type | DECIDE | Conditional branch | Medium non-determinism | ring2 | Conditional edge |
| Load/Store | MEM_OP | Read/write memory | Deterministic | ring1-2 | checkpoint/store |
| Syscall | ACT | Call external tool | High non-determinism | ring0 | Action |

### 4.2 Instruction Encoding Format

```
THINK:  {type:"think", topic:string, depth:int}
OBSERVE: {type:"observe", source:string, filter?:object}
DECIDE: {type:"decide", conditions:Condition[], branches:Branch[]}
MEM_OP: {type:"mem_op", op:"load|store|search|compress", key:string, value?:any}
ACT:    {type:"act", tool:string, input:object, idempotency_key?:string}
```

### 4.3 Three-Level Privilege Model

```
Ring 0: Orchestrator (kernel mode)
  - Schedule Agent execution
  - Manage Checkpoint state
  - Handle interrupt (HITL)
  - Idempotency key enforcement
  - Resource allocation (token/time/cost budget)

Ring 1: Agent (user mode, high privilege)
  - THINK / OBSERVE / DECIDE / MEM_OP
  - Request ACT (requires Ring 0 approval)
  - Request interrupt (requires Ring 0 registration)

Ring 2: Tool (user mode, low privilege)
  - Execute ACT instructions
  - Subject to Ring 0 idempotency constraints

Ring 3: External (no privilege)
  - External API / DB / filesystem
  - Cannot directly access Ring 0/1 state
```

### 4.4 Five-Stage Execution Pipeline

```
FETCH → PARSE → ROUTE → EXEC → COMMIT

FETCH:  LLM generates next Action
PARSE:  OutputParser parses structured output
ROUTE:  Route by instruction type
EXEC:   Execute operation
COMMIT: Update State, write Checkpoint
```

Pipeline hazards and solutions:

| CPU Hazard | Agent Hazard | Solution |
|------------|-------------|----------|
| Structural (resource conflict) | Token budget conflict | Budget allocation + priority scheduling |
| Data (data dependency) | State dependency | Checkpoint sequential guarantee |
| Control (branch prediction) | Decision uncertainty | ReWOO pre-planning ≈ branch prediction |

### 4.5 Interrupt and Exception Architecture

Interrupts (async, from external):
- INT_HITL → human approval (≈ SIGINT)
- INT_TIMEOUT → execution timeout (≈ SIGALRM)
- INT_CANCEL → user cancel (≈ SIGTERM)
- INT_NEW_MSG → new message arrival (≈ SIGIO)

Exceptions (sync, during execution):
- EXC_TOOL_FAIL → tool failure (≈ SIGSEGV)
- EXC_SEMANTIC → hallucination/logic error ← **NEW! Traditional ISA has no equivalent**
- EXC_FORMAT → output format error (≈ encoding error)
- EXC_CONTEXT → Context overflow (≈ OOM)
- EXC_PERMISSION → insufficient privilege (≈ SIGKILL, uncatchable)

Handling strategies:
- RETRY → .with_retry()
- FALLBACK → .with_fallbacks()
- REFLECT → self-correction and re-execute
- ESCALATE → report to Ring 0
- ABORT → terminate Agent

---

## 5. Layer 3: OS/Orchestrator Layer

Key mappings:

| OS Concept | Agent Mapping | Design Insight |
|-----------|---------------|---------------|
| Process scheduler | Agent Router | Deterministic vs LLM-decision scheduling |
| Process states | Agent states | Ready/Running/Blocked → Active/Executing/Waiting_HITL |
| Context switch | Agent switch | Save checkpoint → load new agent state |
| IPC | Agent-to-Agent | Pipe/Shared memory → Channel/Handoff/Message Bus |
| Virtual memory | Context isolation | Independent address space → independent State space |
| Memory protection | State protection | Segfault → Pydantic validation |
| Deadlock detection | Loop detection | Process deadlock → Agent infinite loop |
| OOM Killer | Token handler | Kill process → compress summary reclaim tokens |
| Filesystem | Knowledge Store | VFS → Vector+Graph Store unified retrieval |
| Device driver | Tool Adapter (MCP) | Unified interface + specific implementation |
| Signals | Agent termination | SIGKILL/SIGTERM → force/graceful terminate |
| Daemon | Background Agent | Long-running background Agent |
| Container | Agent Sandbox | Isolation + resource limits + state protection |
| System log | LangSmith trace | dmesg ≈ trace log |

---

## 6. Core Difference: Non-deterministic ISA

The fundamental difference between AISA and traditional ISA:

| Dimension | Traditional ISA | AISA | Essence |
|-----------|----------------|------|---------|
| Execution determinism | Deterministic | Non-deterministic | AISA is a **probabilistic instruction set** |
| Error types | HW fault/SW bug | Hallucination/misunderstanding | New "semantic error" category |
| Debugging | GDB single-step | LangSmith trace | Behavioral analysis vs logical reasoning |
| Verification | Formal verification | Prompt testing + evaluation | Only statistical verification possible |
| Version upgrade | New ISA extensions | New model capabilities | Backward compatibility harder |
| Pipeline | Fixed per-stage time | Variable per-stage time | Non-deterministic pipeline |

Mitigation strategies:

| Strategy | OS equivalent | Agent equivalent |
|----------|--------------|-----------------|
| Redundant execution | RAID | Multi-model cross-validation |
| Exception recovery | Exception handler | .with_retry() + .with_fallbacks() |
| Watchdog | Kernel watchdog | Timeout + Circuit Breaker |
| Idempotency | Idempotent syscall | (run_id, step_id, tool, scope) |
| Privilege downgrade | Capability downgrade | Model downgrade (GPT-4→3.5) |

---

## 7. Architectural Design Opportunities

### 7.1 Agent Container Runtime (类比 Docker)

```
agent run → docker run
├── Agent Template (= Docker Image): Skills + Tools + Prompt + Model spec
├── State Isolation (= namespace/cgroup): thread_id + token_budget + tool_whitelist
├── Memory Volume (= Docker Volume): --mount short-term:checkpointer --mount long-term:store --mount knowledge:rag
└── Health Check (= HEALTHCHECK): quality assessment, hallucination rate, context overflow

Operations:
agent ps / agent logs / agent inspect / agent restart / agent migrate
```

### 7.2 Agent Syscall Table (类比 Linux Syscall)

```
#  syscall_name      privilege  idempotent  description
0  search            ring1      ✅          Query knowledge base
1  read_state        ring1      ✅          Read state
2  write_state       ring2      ❌          Write state
3  tool_call         ring2      ❌          Call external tool
4  interrupt         ring1      ✅          Request human approval
5  checkpoint        ring0      ✅          Save execution state
6  reflect           ring1      ✅          Self-reflection correction
7  delegate          ring2      ❌          Delegate subtask
8  terminate         ring0      ❌          Terminate execution
9  compress          ring0      ✅          Compress context
```

### 7.3 Agent MMU (Context Manager) (类比 OS MMU + kswapd)

```
MMU responsibilities:
├── Virtualization: Agent sees "unlimited Context" (hot + cold data)
├── Mapping: state_key → physical_storage
├── Compression: summarization_node ≈ zswap
├── Recycling: Token GC ≈ kswapd page reclaim
└── Protection: Pydantic validation ≈ MPX

New MEM_OP instructions:
├── compress → Compress current Context
├── swap_out → Evict cold data to Store
├── swap_in → Load hot data from Store
└── gc → Trigger Token reclaim
```

---

## 8. AISA vs Existing Frameworks

| AISA Element | LangGraph | AutoGen | CrewAI | Swarm |
|-------------|----------|---------|--------|-------|
| THINK | Node | generate_reply() | Task.execute() | run() |
| ACT | tool_call→ToolNode | function_call→Executor | Tool.use() | function_call |
| DECIDE | conditional_edge | next_agent | Manager.delegate() | handoff |
| MEM_OP | checkpointer+store | memory_store | memory | context_vars |
| Ring 0 | compile() | Orchestrator | Manager | Client loop |
| INT_HITL | interrupt() | human_input | human_input | None |
| Checkpoint | PostgresSaver | None | None | None |
| Idempotency key | DIY | DIY | None | None |

**Key finding**: Different frameworks have very different implementations of the same AISA specification elements. This is the value of an ISA specification: **define behavioral norms, let implementations compete freely**.

---

## 9. Cross-Domain Knowledge Links

| AISA Concept | Existing Wiki Page | Link Insight |
|-------------|-------------------|-------------|
| Five instruction types | ai-agent (ReAct TAO) | THINK/ACT/OBSERVE maps to Thought/Action/Observation |
| Ring 0 privilege | durable-execution | Durable execution = kernel-mode privilege with idempotency |
| Tool Calling = syscall | tool-calling-idempotency | Idempotency key 4 elements = syscall idempotency mark + transaction isolation |
| Context MMU | langgraph-memory + agent-memory | Current memory layering lacks "automatic compression reclaim" |
| Agent Container | multi-agent-production-patterns | Orchestrator-Worker = container orchestration, missing container runtime |
| LangGraph 3-layer | langgraph-architecture | Runnable→LCEL→StateGraph = ISA→assembly→high-level language |
| HITL interrupt | langgraph-hitl | interrupt() = kernel interrupt; Command(resume) = interrupt resume |
| Runnable protocol | langchain + lcel | Runnable = cross-ISA compatibility layer, similar to JVM |
| Software architecture | software-architecture-patterns | Layers≈AISA4-layer; Pipe-Filter≈Agent pipeline |
| Design principles | software-design-principles | Dependency inversion→ISA spec depends on abstraction; Interface segregation→instruction minimization |

---

## 10. Self-Review

### Placeholder scan
- ✅ No TBD/TODO markers
- ✅ All sections complete

### Internal consistency
- ✅ Four-layer architecture matches feature descriptions
- ✅ Privilege levels consistent across instruction types and syscall table
- ✅ Pipeline hazards align with instruction semantics

### Scope check
- ✅ Focused on conceptual exploration, not implementation blueprint
- ✅ Single spec covering analogy mapping + architectural insights

### Ambiguity check
- ⚠️ "Non-deterministic ISA" concept needs further validation — is a probabilistic ISA meaningful?
  - Resolution: AISA defines **semantic scope** not deterministic result. `THINK` specifies "should produce reasoning about topic" not "must produce exact string"
- ⚠️ Ring levels mapping may not be universal — different frameworks may need different privilege models
  - Resolution: Ring model is AISA's recommendation, not mandate. Implementations can choose different privilege architectures

---

## 11. Open Questions for Further Exploration

1. **"Agent Compiler" concept**: If StateGraph compile() = compilation, what is the "Agent source code" that gets compiled? Is it the Prompt + Skills definition?
2. **AISA backward compatibility**: When a new LLM model is released (e.g., GPT-5), does it "extend" the AISA instruction set? How to ensure old Agent "programs" still work?
3. **AISA formal specification**: Could we write a formal specification document (like x86 ISA manuals) defining exact semantics for each instruction type?
4. **Agent "boot" process**: What's the minimum set of instructions an Agent needs to "boot" from nothing? (类比 BIOS → OS boot → init process)
5. **"Semantic error" detection**: Traditional ISA has parity/ECC for hardware errors. What's the equivalent for detecting LLM semantic errors? (Reflection? Multi-model verification?)