# CrewAI Flows, Hierarchical Crews and Projects

Deeper notes for the crewai-expert skill. Verified against CrewAI 1.15.30 docs (2026-10).

## Flow building blocks

```python
from crewai.flow.flow import Flow, and_, listen, or_, router, start
from crewai.flow.persistence import persist
from crewai.flow.human_feedback import human_feedback, HumanFeedbackResult
```

- **State**: `class MyFlow(Flow[MyState])` with a Pydantic model (give every field a default), or `class MyFlow(Flow)` with a dict in `self.state`. Each state gets an auto-generated `id`.
- **`@start()`**: an entry point. Several starts can run; `@start("label")` gates a start on a router label.
- **`@listen(method)`** or **`@listen("name")`**: runs after that method or label and receives its return value as an argument.
- **`or_(a, b)`**: fires when any listed method finishes. **`and_(a, b)`**: fires when all have finished.
- **`@router(method)`**: returns a label string; declare the labels with a `Literal[...]` return annotation or `@router(method, emit=[...])` so plots show the branches.
- **Running**: `flow.kickoff(inputs={...})` returns the output of the last method to finish; `await flow.kickoff_async(inputs={...})` is the async form. `flow.usage_metrics` aggregates token usage.

## Persistence and resume

- `@persist` above the class persists state after each method (SQLite by default); above a single method it persists only that step.
- Resume a run: `flow.kickoff(inputs={"id": stored_state_id})` continues with the stored state.
- Fork a run: `flow.kickoff(restore_from_state_id=stored_state_id)` starts a new run (new `state.id`) from the stored state.
- Keep state JSON-serializable and small; store large artifacts elsewhere and keep references in state.

## Human feedback in Flows

```python
from crewai.flow.flow import Flow, listen, start
from crewai.flow.human_feedback import human_feedback


class DraftFlow(Flow):
    @start()
    @human_feedback(
        message="Approve this draft, reject it, or ask for changes.",
        emit=["approved", "rejected", "needs_revision"],
        llm="anthropic/claude-haiku-5-5",
        default_outcome="needs_revision",
    )
    def write_draft(self):
        return "Draft text..."

    @listen("approved")
    def publish(self):
        ...

    @listen("needs_revision")
    def revise(self):
        ...
```

With `emit`, an LLM maps the reviewer's free-form feedback to one outcome label. Without `emit`, the step only collects feedback and listeners receive a `HumanFeedbackResult` with `.feedback` and `.output`. History is on `self.last_human_feedback` and `self.human_feedback_history`. Human feedback needs CrewAI 1.8.0 or later.

## Running crews and agents inside Flow steps

- Call a crew factory and `kickoff` it inside a step; copy what you need from `CrewOutput` (`raw`, `pydantic`) into state.
- For a single role, `Agent(...).kickoff("prompt")` avoids building a crew.
- In async Flows use `await crew.akickoff(inputs=...)` (native async) or `await crew.kickoff_async(inputs=...)` (thread-based).

## Hierarchical crews

```python
from crewai import LLM, Agent, Crew, Process, Task

manager_llm = LLM(model="anthropic/claude-opus-5-5", max_tokens=8192, timeout=180)
worker_llm = LLM(model="anthropic/claude-sonnet-5-5", max_tokens=4096, timeout=120)

analyst = Agent(role="Data Analyst", goal="Find trends in {topic} data",
                backstory="Quantitative and careful.", llm=worker_llm, max_iter=8)
writer = Agent(role="Report Writer", goal="Write a clear report on {topic}",
               backstory="Writes for executives.", llm=worker_llm, max_iter=5)

report = Task(
    description="Produce a market report on {topic}.",
    expected_output="A Markdown report with findings, risks and recommendations.",
    markdown=True,
)

crew = Crew(
    agents=[analyst, writer],
    tasks=[report],
    process=Process.hierarchical,
    manager_llm=manager_llm,
    max_rpm=20,
)
result = crew.kickoff(inputs={"topic": "residential solar"})
```

- The manager assigns tasks without an `agent`, reviews results and can reassign.
- Use `manager_agent` instead of `manager_llm` to control the manager's role, goal and tools.
- Hierarchical runs make more model calls than sequential ones; compare cost and quality on your eval set before choosing it.

## Planning

`Crew(planning=True, planning_llm=...)` adds a planning step before execution that writes a plan the agents follow. It adds latency and tokens; keep it only where it improves results for long multi-task crews.

## Memory scoping

```python
from crewai import Agent, Crew, Memory, Task

memory = Memory(recency_weight=0.4, recency_half_life_days=14)


def build_support_crew(tenant_id: str) -> Crew:
    # tenant_id comes from the authenticated session, never from model output
    tenant_memory = memory.scope(f"/tenant/{tenant_id}")
    agent = Agent(role="Support Specialist", goal="Resolve the customer's ticket",
                  backstory="Patient and precise.", memory=tenant_memory)
    task = Task(description="Answer this ticket: {ticket}",
                expected_output="A reply to the customer.", agent=agent)
    return Crew(agents=[agent], tasks=[task])
```

- Scopes are hierarchical paths; `memory.slice(scopes=[...], read_only=True)` reads several branches without writing.
- `remember(..., source="user:alice", private=True)` hides a record from recall unless the source matches.
- There is no built-in tenant model, so derive scope paths from authenticated identity and test that one tenant cannot recall another's records.
- Custom storage backends implement the `StorageBackend` protocol; check the docs for production backends.

## JSON-first project files

- `agents/<name>.jsonc`: `role`, `goal`, `backstory` (with `{placeholders}`), `llm` (`provider/model-id`), `tools` (built-in class names such as `"SerperDevTool"` or `"custom:<name>"` for `tools/<name>.py`), `settings` (for example `verbose`, `allow_delegation`).
- `crew.jsonc`: `name`, `agents` (file names), `tasks` (each with `name`, `description`, `expected_output`, `agent`, `context` as prior task names, `output_file`, `markdown`), `process`, `verbose`, `memory`, `inputs` (placeholder defaults).
- Hierarchical projects set `"process": "hierarchical"` and a manager LLM or agent; check the current docs for the exact field placement.
- `crewai run` detects `crew.jsonc`, loads the agents and prompts for missing placeholders.
- The classic layout (`crew.py` with `@CrewBase`, `@agent`, `@task`, `@crew`, plus `config/agents.yaml` and `config/tasks.yaml`) is created with `crewai create crew <name> --classic`.
- JSON projects can execute local Python through custom tools and `{"python": "module.attribute"}` references; only run projects from trusted sources and review them like code.
