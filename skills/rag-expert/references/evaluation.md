# RAG Evaluation

Reference for measuring a RAG system. Metrics are described, not given target values: acceptable levels depend on the task, corpus and risk, and must come from your own measurements.

## Contents
1. [Evaluation set](#1-evaluation-set)
2. [Retrieval metrics](#2-retrieval-metrics)
3. [Generation metrics](#3-generation-metrics)
4. [Judges and calibration](#4-judges-and-calibration)
5. [Tooling](#5-tooling)
6. [Retrieval metrics in code](#6-retrieval-metrics-in-code)
7. [Regression and online monitoring](#7-regression-and-online-monitoring)

## 1. Evaluation set

- Each item: a query, the chunk ids or document ids that contain the answer, and (for generation) a reference answer or key facts the answer must include. Include unanswerable questions whose correct outcome is "the documents do not say".
- Sources of queries: real logs (after removing sensitive data), questions written by subject-matter experts, and synthetic questions generated from chunks by a model then reviewed by a human. Synthetic-only sets overstate quality because questions echo the chunk wording.
- Cover query types: exact identifiers, paraphrases, multi-hop questions, long-tail topics, each tenant or permission scenario, and each language you support.
- Version the set with the corpus snapshot it refers to; label changes require a new version.
- Keep a held-out slice that is not used for tuning.

## 2. Retrieval metrics

- **Recall@k**: the fraction of relevant items found in the top k results (averaged over queries). The first metric to watch, because a missing chunk cannot be repaired later.
- **Precision@k**: the fraction of the top k that is relevant; matters when the context budget is small.
- **MRR** (mean reciprocal rank): the average of 1 / rank of the first relevant result; suits one-answer questions.
- **nDCG@k**: rewards putting highly relevant items higher, supports graded relevance labels.
- **Hit rate**: the fraction of queries with at least one relevant result in the top k.
- Evaluate each stage on its own: dense only, keyword only, fused, reranked. A reranker is judged on what it does to the order of a fixed candidate list; the retriever on whether the right chunk is in that list.
- For approximate indexes, also measure **index recall**: the overlap between the ANN result and an exact scan of the same filtered set (vector-databases.md, section 12).
- Report metrics per slice (tenant, language, query type) as well as overall.

## 3. Generation metrics

- **Faithfulness / groundedness**: every claim in the answer is supported by the retrieved context.
- **Answer relevance**: the answer addresses the question asked.
- **Context relevance** (or context precision): how much of the retrieved context was needed.
- **Context recall**: whether the retrieved context contains what the reference answer needs.
- **Citation correctness**: cited ids exist in the retrieved set (checkable in code) and the cited text supports the claim (needs a judge or human review).
- **Abstention quality**: unanswerable questions get a "not found" answer, answerable ones are not refused.
- **Security checks**: injection documents do not alter behavior, no cross-tenant content appears, no secrets or system prompt leak.
- Also track latency per stage, token use and cost per answer.

## 4. Judges and calibration

- A model used as a judge needs a written rubric, a fixed temperature setting where the API allows it, and structured output (verdict plus reason).
- Calibrate against a sample labelled by humans: measure agreement before trusting automated scores, and re-check when the judge model or the rubric changes.
- Do not let the generator grade itself with the same prompt and model without a human check; prefer a separate judge call and spot checks.
- Judge prompts embed retrieved text, so apply the same injection handling as in generation.
- Expect noise: compare configurations on the same items, look at per-item differences, and use enough items that a change is not within run-to-run variation.

## 5. Tooling

- **Ragas** (PyPI `ragas`, 0.4.3 at time of writing) provides RAG metrics such as faithfulness, answer relevancy, context precision and context recall, using an LLM judge. Its Python API and import paths have changed between releases and its dependencies are sensitive to the installed LangChain packages; read the docs for the pinned version, and pin it.
- Other evaluation frameworks exist; verify a package and its current API on PyPI or its repository before adding it.
- A small in-house harness (queries, ids, metric functions, a judge prompt, a results table) is often enough and is easy to run in CI.
- Store every run: configuration (model names, chunker version, index parameters), corpus snapshot, metrics, and per-item outputs.

## 6. Retrieval metrics in code

```python
import math

def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    return len(set(retrieved[:k]) & relevant) / len(relevant)

def reciprocal_rank(retrieved: list[str], relevant: set[str]) -> float:
    for i, doc_id in enumerate(retrieved, start=1):
        if doc_id in relevant:
            return 1.0 / i
    return 0.0

def ndcg_at_k(retrieved: list[str], gains: dict[str, float], k: int) -> float:
    dcg = sum(gains.get(d, 0.0) / math.log2(i + 1) for i, d in enumerate(retrieved[:k], start=1))
    ideal = sorted(gains.values(), reverse=True)[:k]
    idcg = sum(g / math.log2(i + 1) for i, g in enumerate(ideal, start=1))
    return dcg / idcg if idcg else 0.0

def evaluate(dataset, search, k=10):
    """dataset: [{"query": str, "relevant": [ids], "tenant_id": str}]; search(query, tenant_id, k) -> [ids]."""
    rows = []
    for item in dataset:
        got = search(item["query"], item["tenant_id"], k)
        rel = set(item["relevant"])
        rows.append((recall_at_k(got, rel, k), reciprocal_rank(got, rel),
                     ndcg_at_k(got, {d: 1.0 for d in rel}, k)))
    n = len(rows) or 1
    return {"recall@k": sum(r[0] for r in rows) / n, "mrr": sum(r[1] for r in rows) / n,
            "ndcg@k": sum(r[2] for r in rows) / n}
```

The `search` function passed to the harness goes through the same tenant-scoped data layer as production, so evaluation also exercises the filters.

## 7. Regression and online monitoring

- Run the retrieval set in CI on every change to chunking, embedding, index parameters, fusion or reranking; fail on a regression beyond a threshold you set from observed run-to-run variation.
- Sample production traffic for review: the question, retrieved chunk ids, answer, citations, and user feedback. Mask sensitive content.
- Watch: share of "not found" answers, citation validity, retrieval scores distribution drift, latency per stage, cost per query, and complaint rate by tenant.
- After every embedding-model, parser or chunker change, rebuild into a new index and compare against the live one on the evaluation set before cutting over.
