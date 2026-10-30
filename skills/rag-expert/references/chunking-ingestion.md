# Chunking and Ingestion

Reference for turning documents into indexed chunks: parsing, chunking strategies, metadata, deterministic ids, embedding, incremental updates and deletion. Splitter classes below were checked against langchain-text-splitters 1.1.3; embedding calls against voyageai 0.5.0.

## Contents
1. [Parsing](#1-parsing)
2. [Chunking strategies](#2-chunking-strategies)
3. [Chunk size and overlap](#3-chunk-size-and-overlap)
4. [Metadata](#4-metadata)
5. [Embedding in batches](#5-embedding-in-batches)
6. [Deterministic ids and incremental ingestion](#6-deterministic-ids-and-incremental-ingestion)
7. [Deletion and permission changes](#7-deletion-and-permission-changes)
8. [Ingestion security](#8-ingestion-security)

## 1. Parsing

- Preserve structure while extracting text: headings, lists, tables, code blocks, page numbers. Flattening a PDF to one string loses the boundaries that make chunks coherent.
- Tables: keep a row together with its header (serialize as Markdown or "column: value" lines); consider embedding a short textual description alongside.
- Scanned documents need OCR; check text quality before indexing. Images and charts need captions or a multimodal embedding model; check the current docs of your embedding vendor.
- Remove repeated headers, footers, navigation and cookie banners; deduplicate near-identical documents (content hash, shingling or embedding similarity).
- Detect language per document and store it; lexical legs need language-specific analyzers.
- Parse untrusted files in a sandbox with size, page and time limits.

## 2. Chunking strategies

- **Structure-aware**: split on headings, then paragraphs, then sentences until pieces fit the budget. Use `MarkdownHeaderTextSplitter` and `RecursiveCharacterTextSplitter` from `langchain-text-splitters` (a standalone package; it does not require the full LangChain framework), or write a small splitter for your format.
- **Recursive character/token splitting**: a good default when structure is weak; measure length in tokens of the embedding model's tokenizer where available, not characters.
- **Code**: split by function or class; keep the file path and symbol name in metadata.
- **Semantic splitting** (embed sentences, split where similarity drops): costs embeddings at ingestion; test against structure-aware splitting before adopting.
- **Parent/child**: embed small child chunks, store `parent_id`, return the parent section for context.
- **Contextual headers**: prepend title and section path (and optionally a one-sentence summary of the document or section) to the text that is embedded. Keep the original text for display.
- **Late chunking and contextual embeddings**: Voyage's client exposes `contextualized_embed`, which embeds chunks of a document with awareness of the whole document; check the current Voyage docs for models and limits before relying on it.

```python
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

header_split = MarkdownHeaderTextSplitter(headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")])
size_split = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=100)  # characters unless a length function is supplied

def chunk_markdown(md: str, title: str):
    out = []
    for section in header_split.split_text(md):                 # Documents with .page_content and .metadata
        path = " > ".join(v for k, v in sorted(section.metadata.items()))
        for piece in size_split.split_text(section.page_content):
            out.append({"text": piece, "embed_text": f"{title} | {path}\n{piece}", "section": path})
    return out
```

## 3. Chunk size and overlap

- No universal best size; compare a few sizes on the evaluation set (evaluation.md) using retrieval metrics and answer quality.
- Too small: chunks lose the context needed to match and to answer. Too large: vectors blur several topics, and the prompt fills with irrelevant text.
- Overlap helps when splits cut through sentences; it adds duplicates, so deduplicate neighbours at context-assembly time. With structure-aware splitting little or no overlap is often enough.
- Respect the embedding model's maximum input length; check the vendor's docs for the limit and truncation behavior (Voyage's `embed` has a `truncation` parameter, default true), and avoid silent truncation of the tail of a chunk.

## 4. Metadata

Store with every chunk: `tenant_id`, `doc_id`, `chunk_no`, `source` (URL or path), `title`, `section`, `language`, `acl_groups`, `doc_version`, `updated_at`, `content_hash`, `embedding_model`, `embedding_dim`. Index the fields used in filters. Metadata used for access control (`tenant_id`, `acl_groups`) comes from the identity and permission system, not from the document text or the uploader's form fields.

## 5. Embedding in batches

```python
import os
import voyageai

vo = voyageai.Client()                     # VOYAGE_API_KEY from the server environment
MODEL = os.environ["VOYAGE_EMBED_MODEL"]   # check the current Voyage docs for model names and dimensions

def embed_documents(texts: list[str], batch_size: int = 64) -> list[list[float]]:
    vectors = []
    for i in range(0, len(texts), batch_size):  # check the vendor's documented per-request limits
        resp = vo.embed(texts[i:i + batch_size], model=MODEL, input_type="document")
        vectors.extend(resp.embeddings)
    return vectors
```

- The client retries on its own configuration; for large jobs add a queue with backoff and a dead-letter list.
- Use `input_type="query"` at query time. The optional `output_dimension` and `output_dtype` parameters exist in the client; supported values depend on the model, so check the current docs.
- Other vendors: OpenAI, Cohere and Google each have their own SDKs and model names (openai 3.41.0, cohere 7.3.0 on PyPI at time of writing); check their current docs. Open models run locally through `sentence_transformers.SentenceTransformer` (`encode`), which avoids sending data to a third party.
- Normalize vectors if the model or index metric requires it.

## 6. Deterministic ids and incremental ingestion

- Chunk id = stable function of `(tenant_id, doc_id, chunk_no)`: a composite primary key in Postgres, or `uuid.uuid5` over that string in Qdrant. Re-ingesting a document then replaces its chunks instead of duplicating them, and ids from different tenants cannot collide.
- Compare `content_hash` per chunk; embed only new or changed chunks.
- When a document shrinks, delete the chunks with `chunk_no` above the new count (inside the same transaction in Postgres).
- Version the pipeline (`parser_version`, `chunker_version`, `embedding_model`); a version change triggers re-ingestion into a new index, then a cut-over.
- Make ingestion idempotent and resumable: queue per document, status per document, retries with backoff.

## 7. Deletion and permission changes

- Delete by `(tenant_id, doc_id)` and remove from every copy: primary index, replicas, caches, backups on their retention schedule, derived summaries.
- A revoked permission must take effect at query time (the ACL filter reads current group membership) and be reflected in stored `acl_groups` through a re-sync job; do not rely on re-embedding to change access.
- Tenant offboarding: drop the partition, namespace, tenant or collection where the engine supports it; otherwise delete by tenant filter and verify counts.

## 8. Ingestion security

- Documents are untrusted input: they can carry prompt-injection text, hidden text (white-on-white, metadata fields, alt text), and malicious files. Strip invisible content where feasible and keep provenance metadata so suspicious sources can be removed.
- Keep storage paths out of user control: generate object keys server-side and never build filesystem paths from file names (path traversal).
- Authenticate the uploader, derive `tenant_id` and ACLs from that identity, and ignore tenant or ACL fields inside the uploaded payload.
- Limit file size, page count, archive expansion and parse time; run parsers with minimal privileges.
- Scan for secrets and regulated data before indexing when the policy requires it.
