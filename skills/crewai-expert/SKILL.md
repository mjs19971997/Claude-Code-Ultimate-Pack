---
name: crewai-expert
description: >-
  Builds CrewAI applications: role-based agents, tasks with structured output and guardrails, sequential and hierarchical crews, Flows for event-driven multi-crew orchestration, tools, memory and testing. Use when writing or reviewing code that imports crewai or crewai_tools, editing crew.jsonc or agents/*.jsonc (or classic agents.yaml/tasks.yaml), designing Agent/Task/Crew/Process setups, building a Flow with @start, @listen, @router or @persist, adding custom BaseTool tools or Task guardrails, or configuring CrewAI Memory and LLMs. Not for LangChain or LangGraph code (use langchain-expert), framework-neutral agent architecture (use ai-agent-architect) or retrieval pipelines (use rag-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# CrewAI

This skill covers building and operating CrewAI applications: agents with roles, tasks with typed outputs and guardrails, crews with sequential or hierarchical processes, Flows that orchestrate crews and plain code, tools, memory, observability and tests. It does not cover general agent architecture choices that are independent of CrewAI, or LangChain and LangGraph.

> Verified against CrewAI 1.15.33 (PyPI release of 2026-10-28; Python 3.10 to 3.13) and docs.crewai.com (2026-10).

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

- **Crews**: a team of `Agent`s working through `Task`s under a `Process` (sequential or hierarchical).
- **Flows**: event-driven orchestration with typed state, where steps can run crews, single agents or plain Python.
- **Supporting pieces**: `LLM` configuration, custom tools, task guardrails, `Memory`, callbacks, streaming, async kickoff.
- **Projects**: the JSON-first project created by `crewai create crew` and the classic Python/YAML layout.

## 2. Core Expertise

- **Agent**: `role`, `goal`, `backstory` (required), plus `llm`, `tools`, `max_iter` (default 25), `max_execution_time`, `max_rpm`, `max_retry_limit`, `allow_delegation` (default False), `respect_context_window` (default True), `reasoning`, `memory`, `verbose`. `Agent.kickoff()` and `kickoff_async()` run one agent without a crew and return a `LiteAgentOutput`.
- **Task**: `description`, `expected_output`, `agent`, `context` (upstream tasks), `tools`, `output_pydantic` or `output_json` (set one), `output_file`, `markdown`, `async_execution`, `human_input`, `callback`, `guardrail` or `guardrails`, `guardrail_max_retries` (default 3; `max_retries` is deprecated).
- **Guardrails**: a function `(TaskOutput) -> tuple[bool, Any]` returning `(True, value)` or `(False, "reason")`, or a plain-language string that CrewAI turns into an LLM-checked guardrail using the task's agent. Failures are sent back to the agent for a retry.
- **Crew**: `agents`, `tasks`, `process`, `manager_llm` or `manager_agent` (needed for hierarchical), `planning` and `planning_llm`, `memory`, `embedder`, `cache` (tool result cache, default True), `max_rpm`, `step_callback`, `task_callback`, `output_log_file`, `stream`.
- **Kickoff**: `kickoff(inputs=...)`, `kickoff_for_each(...)`, thread-based `kickoff_async()` and `kickoff_for_each_async()`, and native async `akickoff()` and `akickoff_for_each()` for high concurrency. Results are `CrewOutput` with `raw`, `pydantic`, `json_dict`, `tasks_output` and `token_usage`.
- **LLM**: `from crewai import LLM`; model strings are `provider/model-id`. OpenAI, Anthropic, Google Gemini, Azure, AWS Bedrock and Snowflake Cortex use native SDKs via extras (for example `crewai[anthropic]`); other providers go through LiteLLM (`crewai[litellm]`). Anthropic requires `max_tokens`.
- **Tools**: subclass `crewai.tools.BaseTool` with `name`, `description`, `args_schema` and `_run` (may be `async def`), or use the `@tool("name")` decorator; built-in tools come from `crewai_tools` (`pip install 'crewai[tools]'`). A tool's `cache_function` decides which results are cached.
- **Memory**: one `Memory` class (`from crewai import Memory`) replaces the older short-term, long-term and entity memory types. `Crew(memory=True)` creates a default instance; `Memory(...)` accepts recency weighting, a storage path or backend and an embedder; `memory.scope("/path")` and `memory.slice(...)` restrict what an agent reads and writes. Default storage is LanceDB under `./.crewai/memory`.
- **Checkpoints**: `Crew(checkpoint=True)` or a `CheckpointConfig` saves run state automatically, and `kickoff(from_checkpoint=...)` resumes it; check the docs for storage options before relying on it.
- **Flows**: `Flow[StateModel]`, `@start()`, `@listen(method_or_label)`, `@router(method)` returning a label, `or_` and `and_`, `@persist` for SQLite-backed state, `@human_feedback` for review steps, `kickoff()` and `kickoff_async()`. Details in [references/flows-and-projects.md](references/flows-and-projects.md).

## 3. Workflow

1. Write the workflow, its inputs, the final output schema and the success criterion.
2. Decide the orchestration level: a single `Agent.kickoff()` for one role, a crew for collaborating roles, a Flow when steps branch, loop, mix code with crews or need persisted state.
3. Define roles with specific titles, action-oriented goals and short backstories that set expertise and constraints.
4. Break the work into tasks; give each an `expected_output`, an owner agent, `context` links and a Pydantic output model where code consumes the result.
5. Add guardrails for checks that code can verify (length, required fields, citations present); use string guardrails only for checks that need judgement.
6. Pick the process: sequential when the order is known, hierarchical when a manager must assign work; set `manager_llm` explicitly.
7. Give each agent only the tools it needs; write custom tools with typed `args_schema`.
8. Bound cost and time: `max_iter`, `max_execution_time`, `max_rpm`, model `max_tokens`.
9. Configure memory only if it measurably improves results, with scopes per user or tenant.
10. Test with mocked tools and recorded fixtures, then run an eval set against real models before release.

## 4. Decision Rules

- Prefer sequential crews; move to hierarchical only when assignment genuinely depends on intermediate results, because the manager adds calls and cost.
- Prefer a Flow over hand-written Python glue between crews when you need routing, state, persistence or resumption.
- Prefer `output_pydantic` over parsing free text whenever another task or program consumes the output.
- Prefer function guardrails over string guardrails; they are deterministic and cost nothing.
- Prefer `allow_delegation=False` unless one agent clearly lacks a capability another has; delegation adds loops.
- Prefer `akickoff()` for many concurrent runs in an async service; `kickoff_async()` wraps the sync path in a thread.
- Prefer enabling `planning` only for long multi-task crews where it improves the eval score; it adds a planning call.
- Prefer a cheaper model for simple roles and a stronger one for the manager or the hardest task, then confirm on the eval set.

## 5. Coding Standards

- Build crews in factory functions or `@CrewBase` classes, not inline in request handlers.
- One Pydantic output model per machine-consumed task; never set both `output_json` and `output_pydantic`.
- Use the `provider/model-id` string form and set `max_tokens` and `timeout` on every `LLM`.
- Custom tools: typed `args_schema`, clear `description`, explicit timeouts on network calls, errors returned as readable strings rather than raw stack traces.
- Keep prompts (role, goal, backstory, task descriptions) in JSONC or YAML config or versioned constants, with `{placeholders}` filled from `inputs`.
- Keep Flow state in a Pydantic model with defaults for every field.
- Naming: agents `researcher`, `analyst`; tasks `research_task`; crews `report_crew`; flows `ReportFlow`; tools `SearchOrdersTool`.

## 6. Project Structure

`crewai create crew <name>` creates a JSON-first project (classic Python/YAML is available with `--classic`):

```text
research_crew/
├── agents/
│   └── researcher.jsonc     # role, goal, backstory, llm, tools, settings
├── crew.jsonc               # name, agents, tasks, process, memory, inputs
├── knowledge/               # knowledge sources
├── skills/
├── tools/                   # custom tools, referenced as "custom:<name>"
├── tests/                   # added by you: unit tests and eval runner
├── .env                     # local secrets only; never commit
└── pyproject.toml
```

`crewai run` reads `crew.jsonc`, loads the agents and runs the crew. Larger services usually wrap crews and Flows in a package (`src/<app>/crews`, `src/<app>/flows`, `src/<app>/tools`) behind an API layer.

## 7. Design Patterns

| Pattern | Use when | Sketch |
|---|---|---|
| Sequential crew | Fixed order of steps | `Process.sequential`; later tasks list earlier ones in `context` |
| Hierarchical crew | A manager must assign and review | `Process.hierarchical`, `manager_llm=...`, tasks may omit `agent` |
| Single agent | One role, no hand-offs | `Agent(...).kickoff("...")` |
| Guarded task | Output must satisfy checks | `guardrail=fn`, `guardrail_max_retries=2` |
| Flow router | Next step depends on a result | `@router(step)` returns a label; `@listen("label")` |
| Flow with persistence | Long or resumable runs | `@persist` on the class; resume with `kickoff(inputs={"id": ...})` |
| Human review | A person approves before continuing | `human_input=True` on a task, or `@human_feedback` in a Flow |

## 8. Best Practices

- Write `expected_output` as a concrete description of format and content; the agent treats it as the definition of done.
- Keep backstories short and relevant; long narratives cost tokens without improving results.
- Pass data between tasks through `context` and typed outputs rather than asking agents to remember.
- Use `callback` and `task_callback` for logging and metrics, not for business logic.
- Use `output_log_file` or a tracing integration in staging to inspect agent reasoning steps.
- Set `max_rpm` at the crew level to protect provider rate limits; it overrides agent values.
- Record `token_usage` from `CrewOutput` (and `flow.usage_metrics` for Flows) per run for cost tracking.

## 9. Performance

- Run independent tasks with `async_execution=True` and join them via `context` on a later task.
- Use `kickoff_for_each` or `akickoff_for_each` for batches instead of a Python loop of kickoffs.
- Keep tool caching on for deterministic read-only tools; use `cache_function` to skip caching volatile results.
- Lower `max_iter` for simple roles; agents that hit the limit return their best answer, so measure quality at the chosen value.
- Prefer a smaller model for classification and extraction tasks in a Flow and a larger one only where needed.

## 10. Security

- Treat tool output, scraped pages and knowledge sources as untrusted; instructions inside them must not change an agent's goal. Keep write tools away from agents that read untrusted content.
- Gate destructive or outbound actions (payments, emails, deletes) behind `human_input`, a `@human_feedback` step or an approval service, not a prompt instruction.
- Bind tenant and user identity in the tool from the authenticated request; never accept a tenant id as a tool argument chosen by the model.
- Scope memory per tenant or user with `memory.scope(...)`, and mark personal records private; there is no built-in tenant concept.
- Only run JSON crew projects from trusted sources: `"custom:<name>"` tools and `{"python": "module.attribute"}` references execute local Python on load.
- Code execution through `allow_code_execution` is deprecated; if agents must run code, call an isolated sandbox service through a tool.
- Keep API keys in the environment or a secret manager; `.env` is for local development only.

## 11. Testing

- Unit-test custom tools directly (`tool._run(...)` or the decorated function) with mocked HTTP clients.
- Unit-test guardrail functions with crafted `TaskOutput` objects or plain strings passed to the underlying check.
- Test Flow routing by calling router methods with prepared state and asserting the returned label.
- Run crews against a small golden set with real models before release; compare output schemas, guardrail pass rate, `token_usage` and latency to the last baseline.
- Keep live model calls out of the unit test suite.

## 12. Review Checklist

- [ ] Roles are specific; goals are actionable; backstories are short.
- [ ] Every task has `expected_output`; machine-consumed tasks have `output_pydantic`.
- [ ] Guardrails cover checkable requirements; `guardrail_max_retries` is set deliberately.
- [ ] `LLM` objects use `provider/model-id`, `max_tokens` and `timeout`.
- [ ] `max_iter`, `max_execution_time` and `max_rpm` are set for production.
- [ ] Hierarchical crews set `manager_llm` or `manager_agent`.
- [ ] Tools have typed `args_schema`, timeouts and no model-supplied tenant ids.
- [ ] Destructive actions require human approval outside the prompt.
- [ ] Memory is scoped per user or tenant, or disabled.
- [ ] Multi-crew logic lives in a Flow with typed state, not ad-hoc glue.
- [ ] Deprecated parameters (`max_retries` on Task, `allow_code_execution`) are removed.
- [ ] Unit tests do not call live models; an eval set exists.

## 13. Production Notes

- Run crews from a worker or queue for long tasks; return a run id and stream or poll results.
- Use `@persist` on Flows that must survive restarts; resume by passing the stored state `id` in `inputs`.
- Pin the `crewai` version and read the release notes before upgrading. The default memory embedder (OpenAI `text-embedding-3-large`, 3072 dimensions) may not match stores built with another embedder, so reset memory or set the old embedder explicitly.
- Log per-run `token_usage`, task durations and guardrail failures; alert on rising retries.
- Set provider-level retries and timeouts on the `LLM`; handle exceptions from `kickoff` and return a partial or error result to the caller.

## 14. Examples

### Example 1: Sequential crew with typed output and a guardrail

```python
from typing import Any

from crewai import LLM, Agent, Crew, Process, Task
from crewai.tasks.task_output import TaskOutput
from pydantic import BaseModel, Field


class Finding(BaseModel):
    claim: str
    source_url: str


class Brief(BaseModel):
    title: str
    summary: str = Field(description="At most 150 words")
    findings: list[Finding]


def summary_is_short(result: TaskOutput) -> tuple[bool, Any]:
    brief = result.pydantic
    if brief is None:
        return (False, "Return the brief in the required schema.")
    if len(brief.summary.split()) > 150:
        return (False, "Shorten the summary to at most 150 words.")
    return (True, result)


llm = LLM(model="anthropic/claude-sonnet-5-5", max_tokens=4096, timeout=120)

researcher = Agent(
    role="Market Researcher",
    goal="Collect verifiable facts about {topic} with a source URL for each",
    backstory="Works only from sources that can be cited.",
    llm=llm,
    max_iter=10,
    max_execution_time=300,
)
writer = Agent(
    role="Brief Writer",
    goal="Turn research notes into a short, accurate brief",
    backstory="Writes plainly and never adds facts that are not in the notes.",
    llm=llm,
    max_iter=5,
)

research_task = Task(
    description="Research {topic}. List each fact with its source URL.",
    expected_output="A bullet list of facts, each with a source URL.",
    agent=researcher,
)
brief_task = Task(
    description="Write a brief on {topic} from the research notes only.",
    expected_output="A title, a summary of at most 150 words and the supporting findings.",
    agent=writer,
    context=[research_task],
    output_pydantic=Brief,
    guardrail=summary_is_short,
    guardrail_max_retries=2,
)

crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, brief_task],
    process=Process.sequential,
    max_rpm=30,
)

result = crew.kickoff(inputs={"topic": "heat pump adoption in Europe"})
brief: Brief = result.pydantic
print(brief.title, result.token_usage)
```

### Example 2: Custom tool with a typed schema and tenant bound outside the model

```python
from typing import Type

import httpx
from crewai.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr


class OrderLookupInput(BaseModel):
    order_id: str = Field(..., description="Order id, for example ORD-1234")


class OrderLookupTool(BaseTool):
    name: str = "lookup_order"
    description: str = "Look up the status of one order by id. Read-only."
    args_schema: Type[BaseModel] = OrderLookupInput
    _tenant_id: str = PrivateAttr()
    _base_url: str = PrivateAttr()

    def __init__(self, tenant_id: str, base_url: str, **kwargs):
        super().__init__(**kwargs)
        self._tenant_id = tenant_id  # from the authenticated request, not from the model
        self._base_url = base_url

    def _run(self, order_id: str) -> str:
        try:
            response = httpx.get(
                f"{self._base_url}/tenants/{self._tenant_id}/orders/{order_id}",
                timeout=10.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            return f"Order lookup failed: {type(exc).__name__}"
        return response.text
```

Create one tool instance per request (`OrderLookupTool(tenant_id=session.tenant_id, base_url=...)`) and pass it in the agent's `tools`. URL-encode or validate `order_id` against its expected format before use.

### Example 3: Flow that routes to different crews and persists state

```python
from typing import Literal

from crewai.flow.flow import Flow, listen, router, start
from crewai.flow.persistence import persist
from pydantic import BaseModel


class TicketState(BaseModel):
    ticket: str = ""
    category: str = ""
    reply: str = ""


@persist
class SupportFlow(Flow[TicketState]):
    @start()
    def classify(self):
        text = self.state.ticket.lower()
        self.state.category = "billing" if "invoice" in text or "refund" in text else "technical"

    @router(classify)
    def route(self) -> Literal["billing", "technical"]:
        return "billing" if self.state.category == "billing" else "technical"

    @listen("billing")
    def handle_billing(self):
        result = build_billing_crew().kickoff(inputs={"ticket": self.state.ticket})
        self.state.reply = result.raw

    @listen("technical")
    def handle_technical(self):
        result = build_technical_crew().kickoff(inputs={"ticket": self.state.ticket})
        self.state.reply = result.raw


flow = SupportFlow()
flow.kickoff(inputs={"ticket": "I was charged twice on my last invoice."})
print(flow.state.category, flow.state.reply)
```

`build_billing_crew` and `build_technical_crew` are your crew factories. Replace the keyword rule with a model call when classification needs judgement.

## 15. Common Mistakes

- **Generic roles** ("Assistant"): vague output. Use specific roles and goals.
- **Free-text hand-offs**: downstream parsing breaks. Use `output_pydantic` and `context`.
- **Hierarchical by default**: extra manager calls and cost for a fixed workflow. Use sequential unless assignment is dynamic.
- **Hierarchical without `manager_llm` or `manager_agent`**: the crew cannot run as intended. Set one explicitly.
- **Old memory configuration**: `short_term_memory`, `long_term_memory` and `entity_memory` setups from older releases. Use the unified `Memory` class with scopes.
- **Bare model names** like `gpt-4` in `LLM(model=...)`: use `provider/model-id`.
- **Checks written only into task descriptions**: the agent may ignore them. Use guardrails.
- **Model-chosen tenant or user ids in tools**: cross-tenant access. Bind identity when constructing the tool.
- **Running untrusted JSON crew projects**: custom tool references execute local code.
- **Live model calls in unit tests**: slow and non-deterministic. Mock tools and keep real calls in the eval run.

## 16. References

- [references/flows-and-projects.md](references/flows-and-projects.md): Flow decorators, state, persistence and resume, human feedback, hierarchical crews, JSON-first project files and memory scoping.
- Official docs: https://docs.crewai.com/ , https://docs.crewai.com/concepts/flows , https://docs.crewai.com/concepts/crews , https://docs.crewai.com/concepts/tasks , https://pypi.org/project/crewai/
