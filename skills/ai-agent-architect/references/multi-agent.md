# Multi-Agent Systems

Design notes and code for systems where several LLM agents cooperate, absorbed from the former multi-agent-expert skill. Verified against LangChain 1.4.7, LangGraph 1.2.18 and CrewAI 1.15.33 (2026-10). Start from a single agent and move to several only when a measured limit (context size, conflicting instructions, independent parallel work, separate permissions) justifies the extra tokens, latency and failure modes.

## 1. Topologies

| Topology | Shape | Good fit | Main risk |
|---|---|---|---|
| Supervisor-worker | A supervisor delegates to workers and reviews results | Distinct domains with separate tools | Supervisor becomes a bottleneck |
| Hierarchical | Supervisors of supervisors | Large task trees | Coordination cost per level |
| Pipeline | Fixed sequence of stages | Draft, review, format flows | Errors propagate downstream |
| Fan-out and fan-in | Parallel workers, one synthesizer | Independent subtasks | Cost multiplies with workers |
| Handoff (swarm) | The active agent transfers control to a peer | Conversational routing between specialists | Ping-pong loops |
| Debate | Agents argue, a judge decides | Questions that benefit from critique | Cost, false consensus |
| Ensemble | Several independent attempts, then a vote | Reducing variance on classification | Cost; correlated errors |
| Blackboard | Agents read and write a shared workspace | Building one shared artifact | Write conflicts |

## 2. Roles

Typical roles are planner, researcher, executor, critic, synthesizer and router. Each role needs written inputs, outputs, tools and a stop condition. Overlapping roles cause duplicated or dropped work; a role without a stop condition causes loops.

## 3. Communication

- Pass typed messages (sender, recipient, task id, trace id, payload) rather than free text between agents.
- Hand each worker only the context it needs; passing the whole transcript to every agent multiplies cost.
- Prefer request-response through the orchestrator over direct peer calls, so every exchange is traced and bounded.
- Validate inter-agent messages against a schema and reject oversized payloads.

## 4. Coordination and failure handling

- Bound concurrency with a semaphore or worker pool; never start an unbounded number of agents.
- Give every agent call a timeout and every run a total budget, split per agent.
- Use retries with backoff for transient errors and a circuit breaker for a worker that keeps failing.
- Decide in advance what partial failure means: continue with the results that arrived, retry the failed branch, or fail the run.
- Detect ping-pong between agents (A hands to B hands to A) with a handoff counter.
- Make side-effecting workers idempotent (idempotency keys) so retries are safe.
- Resolve conflicting outputs explicitly: a judge agent, a vote, or escalation to a human.

## 5. Example: fan-out with bounded concurrency and partial failure

Plain `asyncio`; `run_worker` is your call into a worker agent.

```python
import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable


@dataclass(frozen=True)
class WorkerResult:
    subtask: str
    output: str | None
    error: str | None


async def fan_out(
    subtasks: list[str],
    run_worker: Callable[[str], Awaitable[str]],
    max_concurrency: int = 4,
    per_call_timeout: float = 60.0,
) -> list[WorkerResult]:
    semaphore = asyncio.Semaphore(max_concurrency)

    async def one(subtask: str) -> WorkerResult:
        async with semaphore:
            try:
                output = await asyncio.wait_for(run_worker(subtask), per_call_timeout)
                return WorkerResult(subtask, output, None)
            except asyncio.TimeoutError:
                return WorkerResult(subtask, None, "timeout")
            except Exception as exc:
                return WorkerResult(subtask, None, f"{type(exc).__name__}: {exc}")

    return await asyncio.gather(*(one(s) for s in subtasks))


def require_quorum(results: list[WorkerResult], minimum: int) -> list[WorkerResult]:
    ok = [r for r in results if r.error is None]
    if len(ok) < minimum:
        failed = ", ".join(f"{r.subtask} ({r.error})" for r in results if r.error)
        raise RuntimeError(f"only {len(ok)} of {len(results)} workers succeeded: {failed}")
    return ok
```

The synthesizer receives only the successful results plus a note of which subtasks failed, so the final answer can say what is missing.

## 6. Example: supervisor with subagents as tools (LangChain 1.x)

Wrapping each worker agent as a tool keeps the supervisor in control and makes every delegation a traced, bounded tool call. Verified against LangChain 1.4.7 and LangGraph 1.2.18.

```python
from langchain.agents import create_agent
from langchain.tools import tool

MODEL = "anthropic:claude-sonnet-5-5"  # any tool-calling chat model id


@tool
def search_docs(query: str) -> str:
    """Search the internal documentation and return matching passages."""
    return "..."  # call your search service here


research_agent = create_agent(
    model=MODEL,
    tools=[search_docs],
    system_prompt="Answer research questions from the documentation. Cite passages.",
)


@tool
def research(question: str) -> str:
    """Delegate a research question to the research agent and return its cited answer."""
    result = research_agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config={"recursion_limit": 25},
    )
    return result["messages"][-1].text


supervisor = create_agent(
    model=MODEL,
    tools=[research],
    system_prompt="Break the request into research questions, delegate them, then write the answer.",
)

answer = supervisor.invoke(
    {"messages": [{"role": "user", "content": "Summarize our retention policy for logs."}]},
    config={"recursion_limit": 40},
)
```

`recursion_limit` is a run-time config key, not a compile-time argument. For explicit graphs with shared state, handoffs and checkpointing, see the langchain-expert skill (LangGraph reference).

## 7. Framework options

- **LangGraph**: explicit state graphs, conditional edges, `Send` for dynamic fan-out, checkpointing, interrupts. Best when you need control over every transition.
- **LangChain `create_agent`**: a ready tool loop; subagents can be exposed as tools as above.
- **CrewAI**: role-based crews with sequential or hierarchical processes and Flows for multi-crew orchestration.
- **Provider agent SDKs** and hand-written orchestration: fine when the topology is small and you want few dependencies.

Check each framework's current docs before relying on a specific multi-agent helper; these APIs change between minor releases.

## 8. Evaluation

- **Task success** of the whole system on a golden set.
- **Efficiency**: tokens, cost and wall-clock time versus a single-agent baseline on the same set.
- **Contribution**: ablation runs that remove or replace one agent to see whether it adds value.
- **Communication overhead**: messages and handoffs per task.
- **Failure recovery**: inject worker timeouts and errors and check that the system degrades as designed.

## 9. Security

- Each agent gets its own tool allow-list and credentials; a researcher has no write tools.
- Content produced by one agent is untrusted input for the next; an injected instruction in a fetched page must not propagate through the pipeline.
- Keep per-tenant state separate; never let a shared blackboard mix tenants.
- Audit every delegation with parent trace id, agent, input hash and result hash.

## 10. Common mistakes

- Unbounded parallelism that hits rate limits and multiplies cost.
- Agents calling each other directly with no timeout, trace or budget.
- One agent's failure failing the whole run when a partial answer would do.
- Passing the full transcript to every agent.
- Agents agreeing to be agreeable; give critics an explicit rubric and reward disagreement backed by evidence.
