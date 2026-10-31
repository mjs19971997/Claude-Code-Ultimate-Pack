# Data and Chat Templates

Preparing datasets for supervised and preference fine-tuning with datasets, transformers 5 and TRL 1: row formats, chat template rendering, loss masking, packing, splitting, deduplication, personal-data scrubbing and data cards. The template and masking snippets were run on CPU with a toy tokenizer (transformers 5.22.1, TRL 1.17.1, 2026-10).

## Contents

1. [Row formats TRL accepts](#1-row-formats-trl-accepts)
2. [Chat templates in transformers 5](#2-chat-templates-in-transformers-5)
3. [Loss masking](#3-loss-masking)
4. [Packing and length](#4-packing-and-length)
5. [Splitting and deduplication](#5-splitting-and-deduplication)
6. [Personal data and secrets](#6-personal-data-and-secrets)
7. [Quality filters and synthetic data](#7-quality-filters-and-synthetic-data)
8. [Data cards](#8-data-cards)

## 1. Row formats TRL accepts

JSON Lines is the simplest source: one object per line, loaded with `load_dataset("json", data_files=..., split="train")`.

| Format | Columns | Used by |
|---|---|---|
| Language modeling, plain text | `text` (column name set by `dataset_text_field`) | SFT, loss on the full sequence |
| Language modeling, conversational | `messages`: list of `{"role", "content"}` | SFT, optionally `assistant_only_loss=True` |
| Prompt-completion, plain text | `prompt`, `completion` (strings) | SFT, loss on the completion by default |
| Prompt-completion, conversational | `prompt` and `completion` as message lists | SFT, loss on the completion by default |
| Preference, conversational or plain | `prompt`, `chosen`, `rejected` | DPO |
| Prompt only | `prompt` | GRPO and other online methods |

```json
{"prompt": [{"role": "user", "content": "Summarise: ..."}], "completion": [{"role": "assistant", "content": "..."}]}
{"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
{"prompt": [{"role": "user", "content": "..."}], "chosen": [{"role": "assistant", "content": "good"}], "rejected": [{"role": "assistant", "content": "bad"}]}
```

- Roles are `system`, `user` and `assistant` (plus `tool` where the template supports tool calls). Do not invent roles the template does not know.
- For DPO, `chosen` and `rejected` must share the exact prompt. TRL can extract a shared prefix from full conversations (`maybe_extract_prompt`), but giving the prompt explicitly is safer.
- Remove extra columns (ids, metadata, source) before training or pass a dataset that contains only the needed ones; stray columns are dropped by the trainer's collation but confuse debugging.
- Keep the system prompt policy consistent: either always include the same system message, or never; mixing teaches the model to depend on it.
- Use `datasets` functions (`map`, `filter`, `train_test_split`) with `num_proc` for speed; they are cached on disk by a fingerprint of the function, so changing helper code can invalidate the cache silently.

## 2. Chat templates in transformers 5

The tokenizer stores a Jinja template that turns a list of messages into the exact string the model was trained on. Use it instead of hand-built strings.

```python
from transformers import AutoTokenizer

tok = AutoTokenizer.from_pretrained("org/base-model")
messages = [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi there"},
]

# String form, for inspection
text = tok.apply_chat_template(messages, tokenize=False)

# Prompt for generation: ends where the assistant should start writing
prompt = tok.apply_chat_template(messages[:1], tokenize=False, add_generation_prompt=True)

# Token form: in transformers 5 this is a BatchEncoding, not a list of ids
enc = tok.apply_chat_template(messages, tokenize=True)
input_ids = enc["input_ids"]
```

Facts checked on transformers 5.22.1:

- `apply_chat_template(..., tokenize=True)` returns a `BatchEncoding` with `input_ids` and `attention_mask` because `return_dict=True` is now the default. Code written for v4 that treats the result as a list of ids breaks. Pass `return_dict=False` to get the list.
- Its signature includes `tools`, `documents`, `chat_template`, `add_generation_prompt`, `continue_final_message`, `tokenize`, `padding`, `truncation`, `max_length`, `return_tensors`, `return_dict`, `return_assistant_tokens_mask` and `tokenizer_kwargs`.
- `add_generation_prompt=True` is for inference prompts. Do not use it to build training text that includes the answer.
- The template can add the beginning-of-sequence token itself. Tokenizing the rendered text again with `add_special_tokens=True` can add a second one; tokenize rendered chat text with `add_special_tokens=False`, or let the trainer handle it.
- Saving a tokenizer writes the template to `chat_template.jinja` next to the tokenizer files. Keep this file with the model.
- Base (non-instruct) checkpoints often have no chat template. Set one explicitly before training, or use plain `text` data. Changing the template of an instruct model discards the format it was aligned with; prefer its own.
- Adding new special tokens (for example role markers) requires resizing the embeddings and training them; list them in `modules_to_save` for LoRA, or avoid new tokens.
- Check that training and serving use the same template version: the serving stack (vLLM, an inference endpoint) reads the template from the tokenizer config of the model path, so a merged model must ship the tokenizer.

A render check belongs in every data-preparation script:

```python
def render_check(tok, rows, n=3):
    for row in rows[:n]:
        msgs = row["messages"]
        print(repr(tok.apply_chat_template(msgs, tokenize=False)))
```

The end-of-turn token differs between templates, so verify it by reading the rendered string and the tail of the label tensor rather than with a generic string test.

## 3. Loss masking

The loss should cover only the tokens the model must produce.

- **Prompt-completion data**: with `completion_only_loss=None` (the default) TRL computes the loss on the completion. A run on a toy model showed labels of `-100` over the prompt tokens and real ids over the completion.
- **Conversational `messages` data**: set `assistant_only_loss=True`. The chat template must contain `{% generation %}` ... `{% endgeneration %}` around assistant content, because the mask comes from `return_assistant_tokens_mask`. Without markers TRL raises an error. `trl.get_training_chat_template(tokenizer)` returns a patched template for supported model families (or `None` when none is needed); set the result as `tokenizer.chat_template`, or pass `chat_template_path` in `SFTConfig`. Check the TRL chat-template docs for the supported list.
- **Plain `text` data**: loss on all tokens. Use this for continued pretraining style data, not for instruction tuning.
- `completion_only_loss=True` is for prompt-completion data only; `assistant_only_loss=True` is for conversational data only.
- Verify with a decoded batch:

```python
batch = next(iter(trainer.get_train_dataloader()))
ids, labels = batch["input_ids"][0], batch["labels"][0]
supervised = [int(t) for t, l in zip(ids, labels) if l != -100]
print("supervised text:", repr(tokenizer.decode(supervised)))
```

- The supervised text should be the answer plus the stop token and nothing else. If it contains the system prompt or the user turn, the mask is wrong.
- Padding is masked automatically; an EOS-equal pad token is a classic source of lost stop tokens, so confirm the stop token is in the supervised text.
- `SFTTrainer` drops examples whose labels are fully masked (for instance when truncation removes the whole completion). Log how many rows disappear.

## 4. Packing and length

- `max_length` (default 1024) truncates silently. Compute token lengths of the rendered examples and pick a limit that covers the 95th to 99th percentile, or drop the longest rows deliberately.
- `packing=True` concatenates examples into fixed-length blocks of `max_length`. `packing_strategy` options in TRL 1.17: `"bfd"` (best-fit decreasing, truncates overflow; the default), `"bfd_split"` (best-fit decreasing, splits overflow sequences) and `"wrapped"` (cuts mid-sequence).
- With the `"bfd"` strategy, padding-free batching is enabled, which needs FlashAttention 2 or 3 for correct isolation of sequences in a block. Without it, check the TRL docs for how attention is handled across example boundaries.
- `eval_packing` controls packing of the evaluation set; leave evaluation unpacked if you want per-example loss numbers.
- Packing changes the effective number of examples per step; recompute epochs and the number of steps from tokens.
- Prefer no packing for very small datasets, where example boundaries and ordering matter more than speed.

```python
import numpy as np

def token_lengths(tok, rows):
    return np.array([len(tok.apply_chat_template(r["messages"], tokenize=True)["input_ids"]) for r in rows])

lens = token_lengths(tok, rows)
print({q: int(np.percentile(lens, q)) for q in (50, 90, 95, 99, 100)})
```

## 5. Splitting and deduplication

- Split before any augmentation, paraphrasing or synthetic expansion. Variants of one source row must stay in the same split.
- Split by group when rows share an origin (same document, same user, same conversation, same template). A random row split leaks near-identical rows into the test set.
- Keep three sets: train, validation (for early stopping and hyperparameters) and test (touched once, at the end).
- Remove exact duplicates (normalised text hash) first, then near-duplicates (MinHash or embedding similarity) within the training set and between the training and evaluation sets.
- Check overlap with public benchmarks that you will report on: n-gram overlap between training text and benchmark items. See contamination in [evaluation.md](evaluation.md).
- Persist the splits as files and record their hashes.

```python
import hashlib
from datasets import load_dataset

ds = load_dataset("json", data_files="data/raw/all.jsonl", split="train")

def key(row):
    return hashlib.sha256(row["group_id"].encode("utf-8")).hexdigest()

def bucket(row):
    return int(key(row)[:8], 16) % 100

train = ds.filter(lambda r: bucket(r) < 90)
valid = ds.filter(lambda r: 90 <= bucket(r) < 95)
test = ds.filter(lambda r: bucket(r) >= 95)
```

Hash-based buckets keep a group in one split across re-runs and when new rows are added.

## 6. Personal data and secrets

- Treat any text from users, tickets, chats, emails, logs, code repositories or scraped pages as possibly containing personal data and secrets.
- Scrub before training and before any upload to the Hub or a shared drive. Keep a mapping from raw to scrubbed data only where the law and policy allow, with restricted access.
- Pattern-based scrubbing catches the easy cases (emails, phone numbers, card-like numbers, IP addresses, API-key shapes, private-key headers). Names and addresses need a named-entity model or manual review. Neither is complete, so sample the output and measure the miss rate.

```python
import re

PATTERNS = {
    "EMAIL": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "IPV4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "PRIVATE_KEY": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "LONG_TOKEN": re.compile(r"\b[A-Za-z0-9_\-]{32,}\b"),
}

def scrub(text: str) -> str:
    for label, pattern in PATTERNS.items():
        text = pattern.sub(f"[{label}]", text)
    return text
```

- Replacement placeholders should look the same across the dataset (`[EMAIL]`), so the model does not learn to emit realistic fake identifiers.
- Rare strings are memorised more readily than common ones. Models trained on private data can leak it through generation; test with extraction prompts before release.
- Respect opt-outs, retention limits and consent terms of the data source. Record the lawful basis and the owner of the data in the data card.
- Do not put raw private data into a public dataset repository, a public model repository or an issue tracker.

## 7. Quality filters and synthetic data

- Filter by length bounds, language, empty or repeated text, refusal boilerplate that does not fit the task, broken markup, and answers that contradict the prompt.
- Check label quality by sampling: read at least 100 random rows before training. Fix the template of generation, not only the rows.
- Balance the topics and difficulty of examples to match expected traffic; very frequent trivial items dominate the loss.
- Synthetic data from another model is allowed only if that model's licence permits training on its outputs; several licences restrict it. Record the generator and its terms.
- Use a verifier where possible (execute code, check an answer against a ground truth, validate JSON against a schema) and keep only passing examples.
- Add a small share of general instruction data when the task is narrow, to reduce forgetting. Measure forgetting with a fixed general-ability probe.
- For preference data, check that chosen answers are better on the criterion you care about and not only longer. Length-controlled pairs reduce verbosity bias.

## 8. Data cards

Keep a `DATA_CARD.md` with the dataset:

- Sources and licences, with links and retrieval dates.
- Collection method, filters, and the share of rows removed by each.
- Personal data handling: what was scrubbed, how, and the residual risk.
- Splits: rule, sizes, group key, and hashes of the files.
- Known gaps: languages, topics and populations that are missing or over-represented.
- Intended and out-of-scope uses.
- Contact and a process for removal requests.

A reviewer should be able to rebuild the dataset from the card and the scripts.
