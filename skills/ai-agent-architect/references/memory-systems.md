# Agent Memory Systems

Absorbed from the former memory-systems-expert skill. Verified against LangGraph 1.2.18 and CrewAI 1.15.33 (2026-10). How agents keep information across steps, sessions and users: what to store, how to retrieve it, when to forget it and how to keep one user's memory away from another's.

## 1. Memory types

| Type | Holds | Typical store | Lifetime |
|---|---|---|---|
| Working | Current context window: system prompt, recent turns, retrieved items | The model call itself | One call |
| Thread (short-term) | Message history and state of one conversation or run | Checkpointer (Postgres, Redis, SQLite) | One thread |
| Semantic | Facts about the user or domain ("prefers metric units") | Key-value or document store with an embedding index | Until changed or deleted |
| Episodic | What happened: task, actions, outcome, timestamp | Document store with an embedding index | Decays, then summarized or archived |
| Procedural | Learned rules and examples ("include tests with code") | Versioned prompt fragments or few-shot examples | Until revised |

## 2. Operations

- **Encode**: extract candidate memories from a turn (often with a small extraction prompt), attach metadata (user id, type, source, timestamp, importance), redact personal data that is not needed, write asynchronously so the user response is not blocked.
- **Retrieve**: query by similarity, then rescore with recency and importance; filter by namespace and type; keep the result small.
- **Update**: merge or replace conflicting facts. For volatile facts (preferences) the newest wins; for additive facts (history) keep both with timestamps; ask the user when the conflict matters.
- **Forget**: decay low-value items, summarize old episodes, delete on request.
- **Consolidate**: a background job turns clusters of episodes into semantic facts or procedural rules, then archives the raw episodes.

## 3. Retrieval scoring

A common scheme combines similarity, recency and importance. The weights and half-life are tuning parameters to set from your own evaluation, not universal constants.

```python
import math
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class MemoryRecord:
    id: str
    user_id: str
    kind: str            # "semantic" | "episodic" | "procedural"
    text: str
    importance: float    # 0.0-1.0, assigned at encode time
    created_at: datetime
    last_used_at: datetime


@dataclass(frozen=True)
class Weights:
    similarity: float = 0.6
    recency: float = 0.25
    importance: float = 0.15
    half_life_days: float = 30.0


def recency_score(last_used_at: datetime, now: datetime, half_life_days: float) -> float:
    age_days = (now - last_used_at).total_seconds() / 86_400
    return math.exp(-math.log(2) * age_days / half_life_days)


def rescore(
    candidates: list[tuple[MemoryRecord, float]],  # (record, similarity in 0..1)
    user_id: str,
    weights: Weights,
    top_k: int,
) -> list[MemoryRecord]:
    now = datetime.now(timezone.utc)
    scored = []
    for record, similarity in candidates:
        if record.user_id != user_id:  # defense in depth; the store query is already scoped
            continue
        score = (
            weights.similarity * similarity
            + weights.recency * recency_score(record.last_used_at, now, weights.half_life_days)
            + weights.importance * record.importance
        )
        scored.append((score, record))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [record for _, record in scored[:top_k]]
```

Fetch more candidates than you need from the vector store (scoped to the user), rescore, and keep the top few. A cross-encoder reranker can replace or follow the weighted score when precision matters (see the rag-expert skill).

## 4. Forgetting and retention

- Write the retention policy down: what is kept, for how long, and what happens at expiry (delete, summarize, archive).
- Decay: drop or archive items whose combined score stays below a threshold for a period you choose.
- Summarize: replace many old episodes with one summary that keeps the outcome and lessons.
- Soft-delete first for routine forgetting so mistakes can be reverted, then hard-delete after a grace period.
- Deletion requests (for example under GDPR) must remove the user's data from every store: memory store, checkpoints, caches, search indexes, backups per your backup policy, and derived summaries. Keep a record that the deletion happened, without the deleted content.

## 5. Isolation and privacy

- Namespace every memory by tenant and user, and derive the namespace from the authenticated identity, never from model output or tool arguments.
- Apply the namespace in the store query itself; post-filtering in application code is a second line of defense, not the first.
- Ask for consent before storing personal memories where your product or jurisdiction requires it, and let users view and delete what is stored.
- Do not store secrets, credentials or payment data as memories.
- Treat recalled memories as untrusted text: a stored memory can carry an injected instruction.

## 6. Example: per-user long-term memory in LangGraph

LangGraph separates thread state (checkpointer) from cross-thread memory (store). Namespaces are tuples; here the user id comes from the run context set by the server, not from the model. Verified against LangGraph 1.2.18; check the store reference for the exact index options of your backend.

```python
import uuid
from dataclasses import dataclass

from langgraph.graph import START, MessagesState, StateGraph
from langgraph.runtime import Runtime
from langgraph.store.memory import InMemoryStore


@dataclass
class UserContext:
    user_id: str  # set by the server from the authenticated session


class State(MessagesState):
    memory_notes: str  # read by the model node and placed in a delimited, untrusted block


def recall(state: State, runtime: Runtime[UserContext]) -> dict:
    namespace = ("memories", runtime.context.user_id)
    hits = runtime.store.search(namespace, query=state["messages"][-1].text, limit=5)
    return {"memory_notes": "\n".join(f"- {item.value['text']}" for item in hits)}


def remember(user_id: str, text: str, store) -> None:
    store.put(("memories", user_id), str(uuid.uuid4()), {"text": text})


def build_graph(embeddings, dims: int):
    """embeddings: any LangChain Embeddings instance; dims: its vector size."""
    store = InMemoryStore(index={"embed": embeddings, "dims": dims})
    builder = StateGraph(State, context_schema=UserContext)
    builder.add_node("recall", recall)
    builder.add_edge(START, "recall")
    # add the model node after "recall"; it reads state["memory_notes"]
    return builder.compile(store=store), store


def handle_request(graph, authenticated_user_id: str, text: str) -> dict:
    return graph.invoke(
        {"messages": [{"role": "user", "content": text}], "memory_notes": ""},
        context=UserContext(user_id=authenticated_user_id),
    )
```

In production use a persistent store (for example `PostgresStore` from `langgraph-checkpoint-postgres`) and a persistent checkpointer.

## 7. Framework options

- **LangGraph**: checkpointers for thread memory, stores with namespaces and optional semantic search for long-term memory.
- **CrewAI**: a unified `Memory` class with scopes; see the crewai-expert skill.
- **Dedicated memory services** such as Mem0, Letta or Zep provide extraction, storage and retrieval as a service. Check their current docs for APIs, data residency and deletion guarantees before adopting one.
- **Custom**: a document or vector store plus an extraction prompt and a scheduled consolidation job.

## 8. Evaluation

- **Accuracy**: are stored facts correct and current?
- **Retrieval relevance**: do recalled items help the current task?
- **Forgetting**: are stale or superseded facts gone?
- **Consistency**: do answers stay consistent across sessions?
- **Isolation**: a test user's queries return nothing from other users, including after deletions.
- **Ablation**: compare task success with and without memory to confirm it helps.

## 9. Common mistakes

- Storing whole transcripts as memory: noisy retrieval, storage growth and personal data spread. Extract facts and episodes instead.
- No retention policy: stale facts keep resurfacing.
- One shared namespace for all users: cross-user leakage.
- Encoding synchronously in the request path: every turn gets slower.
- Mixing embeddings from different models in one index: similarity scores stop meaning anything. Re-embed on model change.
- Deleting from the memory store but not from checkpoints, caches or summaries.
