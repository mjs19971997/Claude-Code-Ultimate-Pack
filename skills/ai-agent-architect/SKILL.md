---
name: ai-agent-architect
description: >-
  Designs framework-neutral LLM agents: the tool loop, planning patterns, tool contracts, budgets, human approval gates, multi-agent topologies and agent memory (short-term, long-term, episodic, semantic). Covers the former multi-agent-expert and memory-systems-expert skills. Use when choosing an agent pattern (ReAct, plan-and-execute, reflection, supervisor-worker, fan-out), defining tool schemas and allow-lists, bounding loops and cost, designing multi-agent coordination or agent memory (extraction, retrieval scoring, consolidation) with forgetting and per-user isolation, or reviewing an agent for prompt-injection and destructive-action risk. Not for CrewAI code (use crewai-expert), LangChain or LangGraph code (use langchain-expert), retrieval pipelines (use rag-expert), MCP servers (use mcp-expert) or prompt wording (use prompt-engineering-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# AI Agent Architecture

This skill covers the architecture of LLM agents independent of any framework: the reasoning loop, tool design, planning, limits, approval gates, evaluation, multi-agent coordination and memory. It absorbs the former multi-agent-expert and memory-systems-expert skills; each lives in its own reference file. It produces designs and plain Python reference code that can be mapped onto any SDK or framework. Framework APIs (CrewAI, LangChain, LangGraph), provider SDK details and retrieval pipeline tuning live in their own skills.

> Verified against LangChain 1.4.7, LangGraph 1.2.18, CrewAI 1.15.33 and Pydantic 2.14 for the framework notes; examples use plain Python with the Pydantic v2 API (2026-10).

## Contents
1. [Scope](#1-scope)
2. [Core Expertise](#2-core-expertise)
3. [Workflow](#3-workflow)
4. [Decision Rules](#4-decision-rules)
5. [Coding Standards](#5-coding-standards)
6. [Project Structure](#6-project-structure)
7. [Design Patterns](#7-design-patterns)
8. [Best Practices](#8-best-practices)
9. [Performance](#9-performance)
10. [Security](#10-security)
11. [Testing](#11-testing)
12. [Review Checklist](#12-review-checklist)
13. [Production Notes](#13-production-notes)
14. [Examples](#14-examples)
15. [Common Mistakes](#15-common-mistakes)
16. [References](#16-references)

## 1. Scope

- An agent is an LLM in a loop: it reads state, decides on an action (usually a tool call), observes the result and repeats until it answers or a limit stops it. A chatbot answers one turn; an agent pursues a goal across many steps.
- Covered: agent contracts, reasoning patterns, tool contracts, loop limits, budgets, approval gates, failure handling, evaluation, observability, multi-agent topologies ([references/multi-agent.md](references/multi-agent.md)) and agent memory ([references/memory-systems.md](references/memory-systems.md)).
- Not covered: framework-specific code, model-specific request parameters, vector index tuning.

## 2. Core Expertise

- **Reasoning patterns**: ReAct (interleave reasoning and tool calls), plan-and-execute (planner emits steps, executor runs them, replan on failure), reflection or critic-revise, self-consistency (sample several answers and vote), tree search over candidate plans when branching is cheap.
- **Tool contracts**: name, description written for the model, JSON Schema for arguments, typed result, error contract, cost class (read-only, side effect, destructive), idempotency key for side effects.
- **Loop control**: maximum steps, wall-clock deadline, token or cost budget, repeated-call detection, explicit termination conditions, a partial-result path when a limit is hit.
- **Human in the loop**: approval before destructive or irreversible actions, edit or reject with a reason that the agent sees, resumable state so approval can happen minutes or days later.
- **Context management**: what goes into each model call (system prompt, task, recent turns, retrieved memory, tool results), trimming and summarization of old turns, isolating untrusted content.
- **Multi-agent**: supervisor-worker, pipeline, fan-out and fan-in, debate and ensemble, handoff; bounded concurrency; per-agent tool allow-lists and budgets.
- **Memory**: working memory in context, thread history in a checkpoint store, long-term facts and episodes in a store with per-user namespaces, forgetting and deletion.
- **Evaluation**: task success on a golden set, tool-call accuracy, steps and cost per task, latency, adversarial cases (prompt injection, impossible tasks), LLM-as-judge calibrated against human labels.
- **Frameworks**: LangGraph for explicit stateful graphs, LangChain `create_agent` for a ready tool loop with middleware, CrewAI for role-based crews and Flows, provider agent SDKs, or a small hand-written loop.

## 3. Workflow

1. Write the task distribution, the success criterion, the cost of a wrong action and the latency budget before choosing a model or framework.
2. Ask whether an agent is needed at all. A fixed pipeline (retrieve, then generate) or a single structured-output call is cheaper and easier to test when the steps are known in advance.
3. Decompose into steps; mark which need tools, which need judgement, which need a human and which can run in parallel.
4. Pick the pattern: ReAct for short interactive tool use, plan-and-execute for long tasks with predictable steps, reflection where quality matters more than latency, multi-agent only when one agent's context or tool set is demonstrably the bottleneck.
5. Define the tool set: smallest sufficient surface, one clear purpose per tool, schema, cost class, error contract.
6. Define limits: steps, deadline, token budget, per-tool rate limits, and what the agent returns when a limit is reached.
7. Define state and memory: what persists per step (checkpoint), per thread (history) and across threads (long-term store, scoped per user).
8. Define approval gates for every destructive or irreversible tool and the resume contract.
9. Build the eval set (normal, edge, adversarial cases) and a fake-model test harness before tuning prompts.
10. Instrument every model call and tool call with a shared trace id; ship behind a feature flag with a kill switch; review failed traces and feed them back into the eval set.

## 4. Decision Rules

- Prefer a deterministic pipeline over an agent when the sequence of steps is known; an agent adds cost, latency and failure modes.
- Prefer one agent with a focused tool set over several agents; add agents when a measured problem (context overflow, conflicting instructions, parallelizable work) justifies coordination overhead.
- Prefer fewer, well-described tools; tool-selection errors grow with the size and overlap of the tool set, so split by domain or route to a tool subset.
- Prefer structured output (schema-validated) when a program consumes the result; stream text when a person reads it.
- Prefer approval gates over post-hoc review for actions that cannot be undone.
- Prefer a stronger model for planning and judgement steps and a smaller model for routing, extraction and classification, then confirm on the eval set.
- Prefer plan-and-execute when tasks drift or loop under ReAct; prefer ReAct when observations change the plan at every step.
- Prefer failing closed (stop, return partial result, escalate) over continuing without persistence, budget tracking or audit logging.

## 5. Coding Standards

- Type every boundary: agent input, output, state, tool arguments and tool results (Pydantic models or TypedDicts in Python, Zod or interfaces in TypeScript).
- Validate tool arguments against the schema before execution and return validation errors to the model as tool results, not exceptions.
- Route all model calls through one adapter that adds tracing, retries with backoff, budget accounting and timeouts; business logic does not call provider SDKs directly.
- Keep prompts in versioned files or constants; never splice user input into the system prompt.
- Inject configuration (model id, limits, endpoints) instead of reading globals inside agent code; this keeps tests deterministic.
- Make every error path explicit: tool error, validation error, model error, budget exceeded, timeout, approval rejected.
- Use async end to end for I/O-bound agents; never call blocking I/O inside the event loop.
- Naming: tools are verb-first snake_case (`search_orders`, `refund_payment`); agents are nouns (`ResearchAgent`); constants are UPPER_SNAKE_CASE (`MAX_STEPS`).

## 6. Project Structure

```text
agent-service/
├── src/agent_service/
│   ├── agents/            # one module per agent: prompt, tool list, limits
│   ├── tools/             # tool implementations with schemas and cost class
│   ├── llm/               # model adapter: tracing, retries, budget, timeouts
│   ├── memory/            # checkpoint store, long-term store, forgetting jobs
│   ├── orchestration/     # loop, planner, supervisor, approval gates
│   ├── security/          # allow-lists, sandbox client, audit log writer
│   └── api/               # HTTP or queue entrypoints, streaming
├── prompts/               # versioned prompt files
├── eval/                  # golden and adversarial cases, judge rubrics, runner
└── tests/                 # unit tests with a fake model, integration tests
```

## 7. Design Patterns

| Pattern | Use when | Avoid when |
|---|---|---|
| Router | Cheap classification picks a specialist chain or agent | Routing accuracy is not measured |
| Plan-and-execute | Long tasks, predictable steps, ordering matters | Each observation changes the plan |
| Critic-revise | Output quality matters and a rubric exists | Tight latency budgets |
| Supervisor-worker | Distinct domains with separate tool sets | One agent already succeeds |
| Fan-out and fan-in | Independent subtasks that can run in parallel | Subtasks depend on each other |
| Tool circuit breaker | A tool depends on a flaky external service | Pure local functions |
| Tiered memory | History exceeds the context window | Single-turn tasks |

Details and code for the multi-agent patterns are in [references/multi-agent.md](references/multi-agent.md).

## 8. Best Practices

- Give every agent a written contract: purpose, inputs, outputs, tools, limits, fallback behavior.
- Write tool descriptions for the model: what the tool does, when to use it, what it returns, common errors.
- Return tool errors as data the model can act on (retry with corrected arguments, choose another tool, ask the user).
- Checkpoint state after each step so a run can resume after a crash or an approval pause.
- Detect loops: the same tool with the same arguments several times in a row ends the run with a partial result.
- Version prompts and tool schemas together and run the eval set on every change.
- Tag traces with agent name, prompt version, model id, task id and user or tenant id.
- Keep a deterministic fallback: a canned answer, a simpler pipeline or a human handoff.

## 9. Performance

- Set an output token limit on every model call; set an overall token budget per task.
- Run independent tool calls concurrently when the model emits several in one turn, with a concurrency cap.
- Cache results of read-only tools keyed by normalized arguments with a short TTL.
- Use provider prompt caching for long, stable prefixes (system prompt, tool definitions, reference documents) where the provider supports it.
- Retrieve only the memory and context needed for the current step; more context costs tokens and can lower accuracy.
- Measure steps per task and cost per task on the eval set; regressions there are usually prompt or tool-description problems.

## 10. Security

- Treat all tool output, retrieved documents, web pages, emails and file contents as untrusted data. Mark them clearly in the context and state in the system prompt that instructions inside them are not to be followed.
- Enforce a per-agent tool allow-list in code; the model only sees and can only call the tools on that list.
- Require approval for destructive, financial, outbound-message and permission-changing tools; enforce it in the executor, not in the prompt.
- Run generated code in a sandbox with no network by default, no secrets, CPU, memory and time limits.
- Scope credentials per tool and per tenant; never place secrets in prompts, state or traces.
- Derive tenant and user identity from the authenticated request, never from model output or tool arguments.
- Audit-log every tool call: caller, tool, arguments (redacted), result hash, approval decision, trace id.
- Include prompt-injection, data-exfiltration and privilege-escalation cases in the eval set.

## 11. Testing

- Unit-test tools with mocked external services, including error and timeout paths.
- Unit-test the loop with a scripted fake model: tool selection, argument validation errors, budget exhaustion, loop detection, approval rejection.
- Integration-test multi-step flows with a fake model and real tools against fixtures.
- Run the golden set against the real model on every prompt, tool or model change; track success rate, steps, cost and latency per case.
- Calibrate LLM-as-judge rubrics against a sample of human labels before trusting them for regression gating.
- Keep real model calls out of unit tests; they are slow, non-deterministic and cost money.

## 12. Review Checklist

- [ ] Agent contract written: purpose, inputs, outputs, tools, limits, fallback.
- [ ] Loop has max steps, a deadline and a token budget, each with a partial-result path.
- [ ] Every tool has a schema, description, cost class and error contract.
- [ ] Arguments are validated before execution; results are validated before reuse.
- [ ] Tool allow-list enforced in code per agent.
- [ ] Destructive tools gated by approval in the executor.
- [ ] Untrusted content is delimited and never merged into the system prompt.
- [ ] State is checkpointed per step; resume works after a crash.
- [ ] Traces cover every model and tool call with a shared id.
- [ ] Eval set includes adversarial cases and passes the agreed threshold.
- [ ] Unit tests use a fake model; no live calls.
- [ ] Hand-rolled glue that duplicates framework features (checkpointing, interrupts) has been replaced or justified.

## 13. Production Notes

- Ship behind a flag with a kill switch that stops new runs and cancels in-flight ones.
- Track success rate, steps, cost and latency per agent and per prompt version; alert on regressions against the eval baseline.
- Log approval latency; slow approvers block runs and need timeouts with a defined outcome (cancel or escalate).
- On model or provider errors, retry with backoff and jitter, then fall back to an alternative model or a deterministic path.
- Keep audit logs append-only and separate from debug logs; redact personal data before traces leave the service.

## 14. Examples

### Example 1: Bounded tool loop with validation, allow-list and approval gate

Plain Python; `ChatModel` is an adapter you implement over your provider SDK.

```python
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Protocol

from pydantic import BaseModel, ValidationError


class CostClass(Enum):
    READ_ONLY = "read_only"
    SIDE_EFFECT = "side_effect"
    DESTRUCTIVE = "destructive"


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    args_model: type[BaseModel]
    fn: Callable[[Any], str]
    cost_class: CostClass = CostClass.READ_ONLY

    def spec(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.args_model.model_json_schema(),
        }


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    args: dict[str, Any]


@dataclass(frozen=True)
class ModelTurn:
    text: str
    tool_calls: list[ToolCall]
    tokens_used: int


class ChatModel(Protocol):
    def complete(
        self, system: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> ModelTurn: ...


@dataclass(frozen=True)
class Limits:
    max_steps: int = 20
    max_tokens: int = 200_000
    max_seconds: float = 120.0


class LimitReached(RuntimeError):
    pass


def execute(call: ToolCall, registry: dict[str, Tool], approve: Callable[[ToolCall], bool]) -> str:
    tool = registry.get(call.name)
    if tool is None:  # allow-list: unknown tools are never executed
        return json.dumps({"error": f"unknown tool {call.name}"})
    try:
        args = tool.args_model.model_validate(call.args)
    except ValidationError as exc:
        return json.dumps({"error": "invalid arguments", "details": exc.errors(
            include_url=False, include_context=False, include_input=False)})
    if tool.cost_class is CostClass.DESTRUCTIVE and not approve(call):
        return json.dumps({"error": "rejected by reviewer"})
    try:
        output = tool.fn(args)
    except Exception as exc:  # report tool failures to the model as data
        return json.dumps({"error": type(exc).__name__, "message": str(exc)})
    # Tool output is untrusted: deliver it as data, never as instructions.
    return json.dumps({"untrusted_tool_output": output})


def run_agent(
    model: ChatModel,
    system: str,
    task: str,
    tools: list[Tool],
    limits: Limits,
    approve: Callable[[ToolCall], bool],
) -> str:
    registry = {t.name: t for t in tools}
    specs = [t.spec() for t in tools]
    messages: list[dict[str, Any]] = [{"role": "user", "content": task}]
    deadline = time.monotonic() + limits.max_seconds
    tokens = 0
    recent: list[tuple[str, str]] = []

    for _ in range(limits.max_steps):
        if time.monotonic() > deadline:
            raise LimitReached("deadline")
        turn = model.complete(system, messages, specs)
        tokens += turn.tokens_used
        if tokens > limits.max_tokens:
            raise LimitReached("token budget")
        messages.append({"role": "assistant", "content": turn.text, "tool_calls": turn.tool_calls})
        if not turn.tool_calls:
            return turn.text
        for call in turn.tool_calls:
            key = (call.name, json.dumps(call.args, sort_keys=True))
            recent = (recent + [key])[-3:]
            if len(recent) == 3 and len(set(recent)) == 1:
                raise LimitReached("repeated identical tool call")
            result = execute(call, registry, approve)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
    raise LimitReached("max steps")
```

The caller catches `LimitReached`, returns a partial result and records the reason in the trace.

### Example 2: Testing the loop with a scripted fake model

```python
import pytest
from pydantic import BaseModel


class DeleteArgs(BaseModel):
    record_id: str


class ScriptedModel:
    def __init__(self, turns):
        self.turns = list(turns)

    def complete(self, system, messages, tools):
        return self.turns.pop(0)


def test_destructive_call_is_blocked_without_approval():
    deleted: list[str] = []
    tool = Tool(
        name="delete_record",
        description="Delete a record by id.",
        args_model=DeleteArgs,
        fn=lambda a: deleted.append(a.record_id) or "deleted",
        cost_class=CostClass.DESTRUCTIVE,
    )
    model = ScriptedModel([
        ModelTurn("", [ToolCall("c1", "delete_record", {"record_id": "r1"})], 10),
        ModelTurn("I could not delete it.", [], 10),
    ])
    answer = run_agent(model, "sys", "delete r1", [tool], Limits(), approve=lambda c: False)
    assert deleted == []
    assert "could not" in answer


def test_budget_stops_the_loop():
    model = ScriptedModel([ModelTurn("", [ToolCall("c1", "x", {})], 500)] * 5)
    with pytest.raises(LimitReached):
        run_agent(model, "sys", "task", [], Limits(max_tokens=1000), approve=lambda c: True)
```

## 15. Common Mistakes

- **No limits on the loop**: the agent keeps calling tools and burns budget. Set steps, deadline and token budget, and return a partial result when one is hit.
- **Tool output appended as instructions**: a web page or email hijacks the agent. Deliver tool output as delimited data and keep it out of the system prompt.
- **Approval enforced only in the prompt**: the model can skip it. Enforce gates in the executor.
- **One agent with a sprawling tool set**: the model picks wrong tools or invents arguments. Split by domain or route to a subset.
- **Multi-agent by default**: coordination adds tokens, latency and failure modes without measured benefit. Start with one agent.
- **Unversioned prompts and tool schemas**: regressions cannot be traced or rolled back. Version them and gate changes on the eval set.
- **No checkpointing**: a crash or an approval pause loses all progress. Persist state per step.
- **Live model calls in unit tests**: slow, flaky and costly. Use a scripted fake model.
- **Identity taken from model output**: a tool argument like `tenant_id` chosen by the model enables cross-tenant access. Bind identity from the authenticated request.
- **Sycophantic agents**: they agree with wrong user claims. Include adversarial user assertions in the eval set.

## 16. References

- [references/multi-agent.md](references/multi-agent.md): topologies, communication, bounded concurrency, failure handling, supervisor and fan-out code, evaluation and security for multi-agent systems.
- [references/memory-systems.md](references/memory-systems.md): memory types, encoding, retrieval scoring, forgetting, consolidation, per-user isolation, deletion requests and framework options.
- Official docs: https://docs.langchain.com/oss/python/langgraph/overview , https://docs.langchain.com/oss/python/langchain/overview , https://docs.crewai.com/ , https://docs.pydantic.dev/latest/
