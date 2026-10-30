# Production and LangSmith

Reference for tracing, evaluation, local serving and production hardening of LangChain and LangGraph applications. Verified against langsmith 0.14.16, langgraph 1.2.18, langgraph-cli 0.4.40, langgraph-checkpoint 4.3.1 and langgraph-checkpoint-postgres 3.2.0 (Python 3.10+) (2026-10). LangSmith platform features (hosted deployments, annotation queues, online evaluators) change often; check the current LangSmith docs for anything not listed here.

## 1. Tracing

```bash
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=...            # from the environment or a secret manager; never commit
export LANGSMITH_PROJECT=support-agent  # groups runs; defaults to a shared project if unset
# optional: LANGSMITH_ENDPOINT for EU or self-hosted instances, LANGSMITH_TRACING_SAMPLING_RATE=0.1
```

- With the variables set, LangChain runnables, `create_agent` agents and LangGraph graphs are traced automatically; no code changes are needed.
- Name and tag runs that matter: `chain.with_config(run_name="triage", tags=["prod"], metadata={"prompt_version": "v7"})`, or pass the same keys in the call config.
- Trace your own functions with `@traceable` from `langsmith`; limit tracing for a block with `with tracing_context(enabled=True, project_name="eval", tags=[...]):`.
- Tracing is sent in the background, so short-lived processes (scripts, serverless functions) should call `Client().flush()` before exit.
- `LANGSMITH_TRACING_SAMPLING_RATE` (0 to 1) traces a fraction of runs. Combine sampling with metadata so failures are still easy to find.
- Middleware spans can be shaped with `TracePolicy` (`omit_payload` drops message payloads while keeping span timing); graph nodes accept a `trace_policy` too.

## 2. Privacy controls

- Traces store inputs, outputs and metadata. Decide up front whether prompts and tool results contain personal or confidential data.
- `LANGSMITH_HIDE_INPUTS=true` and `LANGSMITH_HIDE_OUTPUTS=true` drop inputs or outputs from every trace; for selective redaction build a client with `Client(hide_inputs=fn, hide_outputs=fn)` or `anonymizer=`, and pass it to `tracing_context(client=...)`.
- Redact before the model when the model provider should not see the data either: `PIIMiddleware` in agents.
- Self-hosted LangSmith keeps trace data in your infrastructure; check the docs for deployment options.
- Never put API keys or credentials in messages, state, metadata or tags; they are stored and displayed.

## 3. Datasets and evaluation

```python
from langsmith import Client, evaluate

client = Client()
dataset = client.create_dataset("triage-v1")
client.create_examples(
    dataset_id=dataset.id,
    examples=[
        {"inputs": {"text": "Site is down"}, "outputs": {"category": "bug"}},
        {"inputs": {"text": "Invoice question"}, "outputs": {"category": "billing"}},
    ],
)

def target(inputs: dict) -> dict:
    ticket = classifier.invoke(inputs["text"])        # your chain or agent
    return {"category": ticket.category}

def category_matches(outputs: dict, reference_outputs: dict) -> bool:
    return outputs["category"] == reference_outputs["category"]

results = evaluate(
    target,
    data="triage-v1",
    evaluators=[category_matches],
    experiment_prefix="triage",
    max_concurrency=4,
)
```

- Evaluator functions take any of `inputs`, `outputs`, `reference_outputs`, `run`, `example` by parameter name and return a bool, a number, or a dict/`EvaluationResult` with `key` and `score`.
- `evaluate` accepts a function or a `Runnable` as the target (a compiled graph works). `aevaluate` is the async variant. `num_repetitions` repeats each example to expose variance.
- Start with deterministic checks (schema valid, expected tool called, forbidden content absent). Add LLM-as-judge evaluators for open-ended quality only after calibrating them against human labels.
- Build datasets from real production failures and keep them versioned; compare experiments before changing prompts, models or middleware.
- For agents, evaluate trajectories (which tools in which order) as well as final answers.
- `langsmith.testing` (`log_inputs`, `log_outputs`, `log_reference_outputs`, `log_feedback`) logs results from pytest-style tests; check the docs for the pytest integration.

## 4. Local serving with the LangGraph CLI

```json
{
  "dependencies": ["."],
  "graphs": { "agent": "./src/app/agent.py:agent" },
  "env": "./.env",
  "python_version": "3.12"
}
```

```bash
pip install "langgraph-cli[inmem]"
langgraph dev        # local API server with an in-memory backend and hot reload
langgraph build      # build a Docker image of the API server
langgraph up         # run the server locally with Docker
langgraph dockerfile ./Dockerfile   # generate a Dockerfile to customize
```

- `langgraph.json` maps graph ids to `path:variable` entries (a compiled graph or a factory), lists dependencies and points at an env file. The CLI documents more keys (auth, HTTP app, store); read the CLI docs for the current schema.
- Keep credentials out of `langgraph.json` and out of dependency URLs; the CLI warns about credentials in Git URLs. Use environment variables or a secret-backed credential helper.
- The dev server keeps state in memory or local files; it is for development, not production.
- Hosted deployment and the `langgraph deploy` commands are marked beta in the CLI; check the LangSmith deployment docs before relying on them.
- Alternatively embed the compiled graph in your own FastAPI or other service and manage threads yourself, as long as you provide a real checkpointer and authentication.

## 5. Postgres persistence

```python
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver

with ConnectionPool(
    conninfo=DB_URI,                                    # from the environment
    max_size=10,
    kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
) as pool:                                              # in a server, open once at startup and close on shutdown
    saver = PostgresSaver(pool)
    saver.setup()              # migrations: run once per deploy, not per request
    graph = builder.compile(checkpointer=saver)
```

- Use the same connection options that `from_conn_string` uses (`autocommit=True`, `prepare_threshold=0`, `row_factory=dict_row`) when you build your own connection or pool.
- Async services use `AsyncPostgresSaver` with `AsyncConnectionPool` and `await saver.setup()`.
- A shared Postgres lets any worker resume any thread, which is what makes interrupts and long-running runs survive deploys.
- Plan retention: delete checkpoints of finished or abandoned threads, and monitor table growth, because every superstep writes a checkpoint.
- Long-term memory in Postgres uses `PostgresStore` (`langgraph.store.postgres`) with its own `setup()`.

## 6. Serializer hardening

- Checkpoints and store values are serialized with msgpack by `JsonPlusSerializer`. Deserializing data written by an attacker can execute code, so treat checkpoint database write access as code-execution-level access.
- Set `LANGGRAPH_STRICT_MSGPACK=true` to restrict deserialization to a built-in allowlist of safe types. When your state contains custom classes, pass `allowed_msgpack_modules` to the serializer explicitly rather than turning strict mode off. Test resume with real state after enabling it.
- Leave `pickle_fallback=False` (the default).
- Keep application state to JSON-friendly types plus the message classes; avoid storing arbitrary objects, clients or open resources in state.

## 7. Operational checklist

- Pin and upgrade `langchain`, `langchain-core`, `langgraph`, checkpointer packages and provider packages together; run the test suite with warnings visible, since deprecations show up as warnings first.
- Set explicit `recursion_limit`, call limits, per-request timeouts and cost alerts per environment.
- Authenticate every request, derive tenant and user ids from the authenticated session, and verify that the `thread_id` belongs to that user before reading or writing it.
- Run `setup()` for Postgres saver and store in the deploy pipeline; make migrations part of release, not application start for every replica.
- Test a restart: start a run, kill the process at an interrupt, restart, and resume with the same `thread_id`.
- Alert on error rates, latency percentiles, token usage and tool failure rates using trace data; sample full traces for debugging.
- Document which tools need human approval, and test that the approval path rejects, edits and approves correctly.
- Review dependencies of tool code (HTTP clients, database drivers) as ordinary application dependencies with the same patching process.
