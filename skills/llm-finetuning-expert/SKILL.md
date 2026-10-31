---
name: llm-finetuning-expert
description: >-
  Fine-tunes open-weight language models with the Hugging Face stack: transformers 5, datasets, chat templates, PEFT (LoRA, QLoRA), TRL (SFTTrainer, DPOTrainer, GRPOTrainer), memory budgeting, evaluation, Hub publishing and vLLM serving. Use when writing SFTConfig, DPOConfig or LoraConfig code, preparing instruction or preference datasets, calling apply_chat_template, merging adapters with merge_and_unload, running lm-eval, or fixing out-of-memory and loss problems. Not for from-scratch training loops (use pytorch-expert), classical models (use ml-engineering-expert), prompt design (use prompt-engineering-expert), retrieval (use rag-expert), or hosted-API tuning (use openai-sdk-expert).
license: MIT
metadata:
  version: "3.2.0"
---

# LLM Fine-Tuning Expert

This skill covers supervised fine-tuning and preference tuning of open-weight causal language models with transformers, PEFT and TRL: dataset formats and chat templates, LoRA and QLoRA, trainer configuration, hyperparameters, memory, evaluation, publishing and serving. It prefers adapter methods on a single node and treats data quality and evaluation as the main sources of success or failure. Custom PyTorch loops, non-LLM models, prompting, retrieval pipelines and hosted fine-tuning APIs belong to other skills.

> Verified against transformers 5.22.1, TRL 1.17.1, PEFT 0.21.2, datasets 5.1.0, tokenizers 0.23.3, accelerate 1.15.0, huggingface_hub 2.4.0 (run locally on CPU with a tiny random model: SFT, packing, assistant-only loss, DPO and GRPO), bitsandbytes 0.50.2, lm-eval 0.4.13 and vLLM 0.32.0 (versions from PyPI; flags from the lm-eval and vLLM docs) (2026-10).

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

- Covered: transformers 5 model and tokenizer loading, `apply_chat_template`, datasets preparation, PEFT (LoRA, QLoRA, DoRA, rsLoRA, merging), TRL `SFTTrainer`, `DPOTrainer` and, briefly, `GRPOTrainer`, accelerate, DeepSpeed and FSDP at overview level, hyperparameters, memory budgeting, held-out evaluation, lm-evaluation-harness, LLM-as-judge caveats, contamination, Hub publishing, model cards, base-model licences, serving with vLLM, and safety and privacy of training data.
- Not covered: hand-written PyTorch training loops, DDP internals and profiling (pytorch-expert); classical ML, experiment tracking and pipelines (ml-engineering-expert); prompt wording and few-shot design (prompt-engineering-expert); retrieval and chunking (rag-expert); fine-tuning through the OpenAI API (openai-sdk-expert); agent frameworks (ai-agent-architect); container images (docker-expert).
- Out of scope by design: pretraining from scratch, distillation research methods, and model-specific recipes. Check the model card and the library docs for a given base model.

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Versions | transformers 5.x requires Python 3.11 or newer; TRL 1.x requires 3.11+; PEFT 0.21 requires 3.10+. The TensorFlow and Flax code was removed in v5 and `torch` is the only backend |
| transformers 5 breaking changes | `apply_chat_template(tokenize=True)` returns a `BatchEncoding` (dict with `input_ids`, `attention_mask`), not a list; `load_in_4bit` and `load_in_8bit` kwargs are removed (use `quantization_config=BitsAndBytesConfig(...)`); `use_auth_token` is replaced by `token`; `safe_serialization=False` no longer exists (safetensors only); `Trainer(tokenizer=...)` is `processing_class=`; `warmup_ratio` is gone (pass a float below 1 to `warmup_steps`); `overwrite_output_dir` is gone; `evaluation_strategy` is `eval_strategy` |
| Loading dtype | `from_pretrained` infers dtype from the model config in v5. TRL loads a model given as a string in `float32` unless `model_init_kwargs={"dtype": ...}` is set. Use the `dtype` argument name |
| Dataset formats (TRL) | Language modeling (`text` or `messages` column), prompt-completion (`prompt` and `completion`, standard text or conversational lists), and for DPO preference data (`prompt`, `chosen`, `rejected`). Conversational means lists of `{"role", "content"}` dicts |
| Loss masking in SFTConfig | `completion_only_loss=None` (default) trains on the completion for prompt-completion data and on everything for plain language-modeling data; `assistant_only_loss=True` needs conversational `messages` data and a chat template with `{% generation %}` markers |
| SFTConfig defaults | `max_length=1024` (truncation is silent; the old `max_seq_length` name is not a field), `packing=False`, `packing_strategy="bfd"`, `learning_rate=2e-5`, `gradient_checkpointing=True`, `bf16` true unless `fp16` is set, `logging_steps=10`, `loss_type="nll"` |
| DPOConfig defaults | `beta=0.1`, `loss_type=["sigmoid"]` (a list; several types can be combined with `loss_weights`), `learning_rate=1e-6`, `max_length=1024`, `precompute_ref_log_probs=False`; there is no `max_prompt_length` field |
| PEFT LoRA | `LoraConfig` defaults: `r=8`, `lora_alpha=8`, `lora_dropout=0.0`, `bias="none"`, `use_rslora=False`, `use_dora=False`; `target_modules="all-linear"` selects every linear layer except the output head; `modules_to_save` trains extra full modules |
| QLoRA | Base weights in 4-bit through bitsandbytes (`nf4`, double quantization, bf16 compute) plus LoRA adapters in higher precision. SFTTrainer and DPOTrainer prepare a quantized model themselves when `quantization_config` is passed |
| GRPO | `GRPOTrainer(model, reward_funcs, args, train_dataset, peft_config)`; reward functions return one float per completion; `GRPOConfig` defaults: `num_generations=8`, `loss_type="dapo"`, `beta=0.0`, `use_vllm=False` |
| Hub CLI | `huggingface_hub` 2.x ships the `hf` command: `hf auth login`, `hf upload REPO_ID LOCAL_PATH`, `hf download`. `trainer.push_to_hub()` also works |
| Evaluation | `lm_eval --model hf --model_args pretrained=...,peft=PATH --tasks ... --apply_chat_template --log_samples --output_path DIR` |
| Serving | `vllm serve BASE --enable-lora --lora-modules name=path` serves adapters; `--max-lora-rank` must cover the adapter rank. A merged model is served as an ordinary model path |

## 3. Workflow

1. State the goal as a measurable behaviour change (format adherence, domain tone, tool-call accuracy, refusal behaviour). Decide whether prompting, retrieval or tuning is the right tool before collecting data (see section 4).
2. Pick the base model: licence, size, context length, chat template, and whether an instruct or a base checkpoint is the better start. Record the exact model id and revision.
3. Build the dataset: clean, deduplicate, scrub personal data, split train, validation and test before any other processing, and render a few examples through the chat template by eye. See [references/data-and-chat-templates.md](references/data-and-chat-templates.md).
4. Write an evaluation first: a held-out set, a task metric, and the base model's score on it. See [references/evaluation.md](references/evaluation.md).
5. Run a tiny smoke test (a few dozen examples, a few steps) to check masking, truncation, template and memory. Inspect one decoded batch with its labels.
6. Train with LoRA or QLoRA first. Log training and validation loss, learning rate, gradient norm and tokens per second. See [references/peft-lora-qlora.md](references/peft-lora-qlora.md) and [references/trl-sft-dpo.md](references/trl-sft-dpo.md).
7. Evaluate on the held-out set, compare with the base model, read samples, and check for regressions in general ability and safety behaviour.
8. Merge or keep the adapter, write the model card, publish privately first, and serve with a pinned stack.

## 4. Decision Rules

- If the need is new facts, changing documents or citations, use retrieval (rag-expert); if it is wording, format or a few examples, try prompting first (prompt-engineering-expert). Tune when behaviour, style or a narrow skill must be consistent and cheap at inference.
- If the GPU has enough memory for the base model in bf16 plus activations, use LoRA in bf16; if not, use QLoRA (4-bit base); use full fine-tuning only with a clear reason (large domain shift, plenty of data and multi-GPU memory).
- If the data is (prompt, ideal response) pairs, use SFT. If it is (prompt, better, worse) pairs and the model already follows instructions, use DPO after SFT. If an automatic verifier can score outputs (unit tests, exact answers), consider GRPO; it needs many generations per step and is the most expensive option.
- If examples are single-turn instructions, use the prompt-completion format so the prompt is masked by default. If they are multi-turn chats, use `messages` and `assistant_only_loss=True` with a template that has generation markers.
- If sequences are short and varied in length, enable `packing=True` to cut padding; keep it off if cross-example contamination through attention is a concern for your attention backend, and check the docs for the active `packing_strategy`.
- If the learning rate is not known, start at 2e-4 for LoRA or QLoRA and 1e-5 to 2e-5 for full fine-tuning, and 5e-6 to 5e-5 for DPO with LoRA (typical starting ranges, not guarantees); change only one setting at a time.
- If validation loss rises while training loss falls, stop earlier, lower the learning rate or rank, or add data; do not train for more epochs.
- If the task is classification or extraction with a fixed schema, consider a small encoder or a classifier head before a generative model (ml-engineering-expert).
- If the base-model licence restricts use, naming, or output reuse, resolve that before training; the derivative inherits the terms.
- If the deployment must serve many tenants or tasks from one base, keep separate adapters and serve them with multi-LoRA; if latency is critical for one task, merge.

## 5. Coding Standards

- Pin the stack in one lock file (`transformers`, `trl`, `peft`, `datasets`, `accelerate`, `bitsandbytes`, `torch`). TRL and transformers rename fields between minor releases; introspect with `dataclasses.fields(SFTConfig)` after an upgrade instead of copying old snippets.
- Use config objects (`SFTConfig`, `DPOConfig`, `LoraConfig`, `BitsAndBytesConfig`) and keep them in one place; never mutate global defaults.
- Use `processing_class=tokenizer`; pass `dtype=` (not `torch_dtype=`) to `from_pretrained`; pass `quantization_config=` rather than `load_in_4bit=`.
- Set the seed (`seed` in the config, `set_seed`) and record the dataset revision, library versions and the full config next to each run.
- Set `pad_token` explicitly when the tokenizer has none, and make sure it differs from the end-of-sequence token or that the collator masks it correctly (check the decoded labels).
- Never construct training text by string concatenation when a chat template exists; call `apply_chat_template` or hand TRL structured `messages`.
- Pass `trust_remote_code=True` only for code you have read and pinned to a revision; the default is `False`.
- Read tokens from the environment (`HF_TOKEN`) or the `hf auth login` store; never put them in scripts or configs.
- Keep the training script runnable on a tiny model and a few rows (`max_steps=2`) so it can run in CI on CPU.

## 6. Project Structure

```text
finetune-project/
  pyproject.toml            # pinned transformers, trl, peft, datasets, accelerate
  configs/
    sft_lora.yaml           # one config per experiment, versioned
    dpo_lora.yaml
  data/
    raw/                    # never edited; excluded from the repo if sensitive
    processed/              # train.jsonl, validation.jsonl, test.jsonl
    DATA_CARD.md            # source, licence, filters, PII handling, split rule
  src/
    prepare_data.py         # clean, dedupe, scrub, split, render-check
    train_sft.py
    train_dpo.py
    merge_adapter.py
    evaluate.py             # held-out loss, task metric, sample dump
  tests/
    test_smoke.py           # tiny-model CPU run, template and mask checks
  runs/                     # outputs, git-ignored
  MODEL_CARD.md
```

- Keep splits as files, not seeds alone, so the evaluation set cannot silently change.
- Keep the evaluation script separate from the training script so it can score any checkpoint, the base model and competitors the same way.

## 7. Design Patterns

- **SFT then DPO**: a supervised stage teaches format and task, a preference stage adjusts style or safety trade-offs. Train DPO from the SFT result and use the SFT result (or the adapter-disabled base) as the reference. Cost: two datasets and two evaluations.
- **Adapter per task**: one frozen base plus small adapters, loaded by name at serving time. Cost: serving stack must support multi-adapter inference.
- **Merge for deployment**: train an adapter, reload the base in 16-bit, merge, save a plain model. Cost: the adapter is no longer separable and a quantized base cannot be merged losslessly.
- **Prompt-completion with masked prompts**: loss only on the answer; the model does not learn to reproduce instructions. Cost: no learning signal from the prompt side.
- **Held-out probe sets**: a fixed set of general prompts and a fixed set of safety prompts, scored for every checkpoint to catch regressions.
- **Synthetic data with a verifier**: generate candidates, keep those that pass an executable check, then tune on the survivors (rejection sampling). Cost: generator bias and licence terms of the generating model apply.
- **Curriculum by length**: filter overlong examples first so truncation does not cut off answers.

## 8. Best Practices

- Spend most of the effort on data: a few thousand clean, diverse, correct examples usually beat a larger noisy set. Remove duplicates and near-duplicates, contradictory answers and examples with wrong labels.
- Match the training format to the inference format exactly: same chat template, same system prompt policy, same end-of-turn token.
- Make sure every training answer ends with the end-of-turn or EOS token that serving will use as a stop condition; a missing one produces models that never stop.
- Keep the effective batch size explicit: `per_device_train_batch_size * gradient_accumulation_steps * number_of_processes`. Typical SFT values are 16 to 128 sequences; scale the learning rate down for larger batches only after checking the loss curve.
- Use a short warmup (a few percent of steps, via a float `warmup_steps` below 1) and a cosine or linear decay.
- One to three epochs are typical for SFT; more epochs raise the risk of memorising the set.
- Evaluate before and after on the same prompts with the same decoding parameters (greedy, fixed `max_new_tokens`).
- Save checkpoints on a schedule, keep only the last few (`save_total_limit`), and record which one was selected and why.
- Write a model card: base model and revision, data sources and licences, method and hyperparameters, evaluation, intended use, limitations and known safety gaps.
- Version the dataset and keep a data card; a model is not reproducible without them.

## 9. Performance

- Memory has four parts: weights, gradients, optimizer state and activations. Rules of thumb: bf16 weights use about 2 bytes per parameter; 4-bit weights about 0.5 bytes plus quantization constants; full fine-tuning with AdamW needs on the order of 12 to 16 bytes per parameter before activations; LoRA adds optimizer state only for the adapter parameters. Measure with `torch.cuda.max_memory_allocated()` on a real batch.
- Activations scale with batch size times sequence length. Lower `per_device_train_batch_size`, raise `gradient_accumulation_steps`, keep `gradient_checkpointing=True` (the TRL default) and reduce `max_length` before reducing rank.
- Use bf16 on hardware that supports it; use fp16 with loss scaling only when bf16 is unavailable. Keep adapter weights in fp32 or bf16 consistently.
- Use packing or padding-free batches to avoid computing on pad tokens; padding-free needs FlashAttention 2 or 3. Sort or bucket by length if not packing.
- Use an optimised attention implementation (`attn_implementation` argument; check which values the installed version and model support) and, where installed, fused kernels such as `use_liger_kernel`.
- QLoRA saves memory and costs speed (dequantization on every forward pass); if the bf16 model fits, LoRA without quantization is faster.
- Multi-GPU: `accelerate launch` with DDP for models that fit on one GPU, FSDP or DeepSpeed ZeRO-3 when parameters, gradients and optimizer state must be sharded. Keep one configuration file per topology and test it on 2 steps first. Details change between releases, so check the accelerate and TRL docs.
- Precompute reference log-probabilities (`precompute_ref_log_probs=True`) in DPO to avoid keeping a reference model in memory; with LoRA the adapter-disabled base serves as the reference at no extra memory.
- Throughput is reported in tokens per second; compare it across configurations, not samples per second.

## 10. Security

- Datasets are an attack surface: poisoned or backdoored examples, prompt-injection text, hidden instructions in scraped pages, and secrets or personal data. Review samples, filter sources and keep provenance.
- Scrub personal data (names, emails, phone numbers, addresses, identifiers, secrets and API keys) before training. Models can memorise and reproduce rare strings; deletion after training is not possible without retraining. Get a lawful basis and consent where required and record the decision in the data card.
- Do not train on private conversations or customer data without permission, and do not publish a model trained on them to a public repository.
- Fine-tuning, including LoRA on benign data, can reduce safety behaviour of an aligned model. Run a safety and refusal evaluation before and after, add refusal examples where the use case needs them, and do not remove safeguards to make a model comply more; get review before release of any model whose purpose touches harmful content.
- Treat downloaded weights and datasets as untrusted: prefer safetensors, leave `trust_remote_code=False`, pin revisions with the `revision` argument, and inspect dataset loading scripts. v5 removed the unsafe serialization fallback.
- Never commit tokens. Use a fine-grained Hub token scoped to the needed repository and an environment variable or `hf auth login`; rotate on exposure.
- Check the licences of the base model and the data (including model-generated data) and honour attribution, naming and acceptable-use clauses when redistributing.
- Publish new models as private first, test them, then change visibility deliberately.
- Do not expose a training or serving endpoint without authentication; vLLM's server has no built-in access control beyond an API key option (check the docs) and should sit behind a gateway.

## 11. Testing

- A CPU smoke test builds a tiny random model from a config (for example a 2-layer Llama-style config) and a toy tokenizer, then runs `SFTTrainer` for a few steps. It catches renamed fields and template mistakes without downloading weights.
- Assert on the data path: decode `input_ids` of the first batch, check that `labels` are `-100` over the prompt (or non-assistant tokens), and that the last supervised token is the end-of-turn token.
- Assert on the chat template: render a conversation with `tokenize=False`, compare with a stored expected string, and check `add_generation_prompt=True` ends where the model should start generating.
- Test merging: save an adapter, reload with `PeftModel.from_pretrained`, run `merge_and_unload()`, and compare logits of the merged model and the adapter model on a fixed input with a tolerance.
- Evaluate with fixed decoding parameters and a fixed seed; report the metric with a confidence interval or at least the sample count.
- Regression suite: keep a small set of general-ability and safety prompts and fail the pipeline when scores drop beyond a set threshold.
- Run data checks in CI: schema validation, empty fields, duplicate rows, split overlap (exact and near duplicates between train and test), and PII regex scans.

## 12. Review Checklist

- [ ] Library versions are pinned and the config uses current field names (`processing_class`, `dtype`, `eval_strategy`, `warmup_steps`).
- [ ] The dataset is split before processing; no overlap between train and test; a data card exists.
- [ ] Personal data and secrets are scrubbed; data and base-model licences allow the intended use.
- [ ] Chat template at training equals chat template at inference; the end-of-turn token is in the labels.
- [ ] Loss masking is verified on a decoded batch (prompt masked when intended).
- [ ] `max_length` covers the data; the share of truncated examples is known.
- [ ] Effective batch size, learning rate, epochs and rank are stated and justified.
- [ ] Base model scores are measured on the same held-out set; improvement is larger than run-to-run noise.
- [ ] Safety and general-ability regressions were checked.
- [ ] `trust_remote_code` is off or reviewed; tokens are not in code or logs.
- [ ] The artifact (adapter or merged model) loads in a fresh process and in the serving stack.
- [ ] A model card describes data, method, evaluation, limits and licence.

## 13. Production Notes

- Record for every run: git commit, library versions, dataset hash, full config, seed, hardware and the selected checkpoint. Store them with the artifact.
- Save the tokenizer and chat template with the model. Saving a trainer output also writes the tokenizer files and `chat_template.jinja`.
- Adapter folders contain `adapter_config.json` and `adapter_model.safetensors`; the base model id is referenced in the config, so keep the base available at the same revision.
- To merge, load the base in bf16 or fp16 (not 4-bit), attach the adapter with `PeftModel.from_pretrained`, call `merge_and_unload()`, then `save_pretrained` and save the tokenizer. Re-run the held-out evaluation on the merged model, since numerical results can differ slightly.
- vLLM: serve an adapter with `vllm serve BASE --enable-lora --lora-modules name=path` and size `--max-lora-rank` for the adapter; serve a merged model by path. Pin the vLLM version, test the chat template through the server, and set explicit `max_model_len` and sampling defaults.
- Track drift: sample production prompts (with consent and scrubbing), re-run the evaluation periodically, and keep the previous model deployable for rollback.
- Quantizing the merged model for serving (GPTQ, AWQ, GGUF and others) changes outputs; evaluate the quantized artifact, not only the 16-bit one.
- Cost control: estimate GPU hours from tokens (training tokens times epochs divided by measured tokens per second) before launching; checkpoint often on pre-emptible hardware and resume with `resume_from_checkpoint`.

## 14. Examples

QLoRA supervised fine-tuning on prompt-completion data with loss on completions only (needs a CUDA GPU and `bitsandbytes`; the same trainer calls were run on CPU with a tiny model):

```python
import torch
from datasets import load_dataset
from peft import LoraConfig
from transformers import BitsAndBytesConfig
from trl import SFTConfig, SFTTrainer

BASE = "org/base-model"  # set to a model whose licence permits your use

train = load_dataset("json", data_files="data/processed/train.jsonl", split="train")
valid = load_dataset("json", data_files="data/processed/validation.jsonl", split="train")
# each row: {"prompt": [{"role": "user", "content": "..."}],
#            "completion": [{"role": "assistant", "content": "..."}]}

bnb = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=torch.bfloat16,
)
lora = LoraConfig(
    r=16, lora_alpha=32, lora_dropout=0.05,
    target_modules="all-linear", task_type="CAUSAL_LM",
)
args = SFTConfig(
    output_dir="runs/sft-qlora",
    model_init_kwargs={"dtype": torch.bfloat16},
    max_length=2048,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=16,   # effective batch 32 on one GPU
    learning_rate=2e-4,
    num_train_epochs=2,
    lr_scheduler_type="cosine",
    warmup_steps=0.05,                # a float below 1 is a ratio of total steps
    eval_strategy="steps",
    eval_steps=100,
    save_steps=100,
    save_total_limit=2,
    logging_steps=10,
    report_to="none",
    seed=42,
)
trainer = SFTTrainer(
    model=BASE,
    args=args,
    train_dataset=train,
    eval_dataset=valid,
    quantization_config=bnb,
    peft_config=lora,
)
trainer.train()
trainer.save_model("runs/sft-qlora/adapter")
```

Merge the adapter into a 16-bit copy of the base model:

```python
import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

BASE = "org/base-model"
base = AutoModelForCausalLM.from_pretrained(BASE, dtype=torch.bfloat16)
model = PeftModel.from_pretrained(base, "runs/sft-qlora/adapter")
merged = model.merge_and_unload()
merged.save_pretrained("runs/merged")
AutoTokenizer.from_pretrained("runs/sft-qlora/adapter").save_pretrained("runs/merged")
```

DPO on top of an SFT adapter result, with LoRA so the reference needs no extra memory:

```python
from datasets import load_dataset
from peft import LoraConfig
from trl import DPOConfig, DPOTrainer

prefs = load_dataset("json", data_files="data/processed/prefs.jsonl", split="train")
# each row: {"prompt": [...], "chosen": [...], "rejected": [...]} as message lists
args = DPOConfig(
    output_dir="runs/dpo",
    beta=0.1,
    learning_rate=5e-6,
    max_length=2048,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=8,
    num_train_epochs=1,
    report_to="none",
)
trainer = DPOTrainer(
    model="runs/merged",
    args=args,
    train_dataset=prefs,
    peft_config=LoraConfig(r=16, lora_alpha=32, target_modules="all-linear", task_type="CAUSAL_LM"),
)
trainer.train()
```

Evaluate with lm-evaluation-harness and serve with vLLM:

```bash
lm_eval --model hf \
  --model_args pretrained=org/base-model,peft=runs/sft-qlora/adapter \
  --tasks <task-name> --apply_chat_template \
  --batch_size 8 --log_samples --output_path results/sft-qlora

vllm serve org/base-model --enable-lora \
  --lora-modules my-task=runs/sft-qlora/adapter --max-lora-rank 16
```

## 15. Common Mistakes

- **Template mismatch**: training with one prompt format and serving with another lowers quality sharply. Use the tokenizer's chat template in both places.
- **Loss on the prompt**: training on instructions teaches the model to produce them. Use prompt-completion data or `assistant_only_loss=True` and check the labels.
- **`assistant_only_loss=True` with a template lacking generation markers**: TRL raises an error. Use a template with `{% generation %}` markers or the patched template from `trl.get_training_chat_template`.
- **No end-of-turn token in the answer**: the fine-tuned model rambles. Check that the last supervised label is the stop token.
- **Silent truncation at `max_length=1024`**: long answers are cut and the end token is lost. Measure the length distribution and raise the limit.
- **Using removed arguments** (`load_in_4bit=`, `warmup_ratio`, `evaluation_strategy`, `tokenizer=`, `max_seq_length`, `max_prompt_length` in DPO): update to `quantization_config`, float `warmup_steps`, `eval_strategy`, `processing_class`, `max_length`.
- **String model in TRL without a dtype**: the model loads in float32 and runs out of memory. Pass `model_init_kwargs={"dtype": ...}` or load the model first.
- **Merging into a 4-bit base**: rounding errors accumulate. Reload the base in 16-bit and merge there.
- **Evaluating on training data or on leaked data**: results look excellent and mean nothing. Split first and check overlap, including with public benchmarks.
- **Reading loss as quality**: lower loss can come from memorisation or a style shift. Add task metrics and sample review.
- **Judging with a model judge without controls**: judges favour long answers and their own style, and are sensitive to order. Randomise order, calibrate against human labels and report agreement.
- **Learning rate copied from full fine-tuning into LoRA** (or the reverse): adapters usually need a much higher rate than full tuning.
- **Large LoRA rank as a default fix**: raise data quality or the target modules first; a higher rank mostly increases overfitting and memory.
- **Fine-tuning away safety**: tuning on compliant-only data can erode refusals. Evaluate and review before release.
- **Forgetting the pad token**: a pad token equal to EOS can mask the real stop token. Inspect the labels.
- **Publishing before checking licences and data privacy**: a public repository is hard to retract.

## 16. References

- [references/data-and-chat-templates.md](references/data-and-chat-templates.md): dataset formats for SFT and DPO, chat template rendering and generation markers, masking, packing, splitting, deduplication, PII scrubbing and data cards.
- [references/peft-lora-qlora.md](references/peft-lora-qlora.md): LoraConfig fields, target modules, rank and alpha, QLoRA with bitsandbytes, saving, loading and merging adapters, multi-adapter use, memory budgeting.
- [references/trl-sft-dpo.md](references/trl-sft-dpo.md): SFTConfig and DPOConfig fields, hyperparameters, accelerate, DeepSpeed and FSDP overview, DPO details, GRPO basics, transformers 5 and TRL 1 migration notes.
- [references/evaluation.md](references/evaluation.md): held-out loss, task metrics, lm-evaluation-harness, LLM-as-judge caveats, contamination, safety regression checks, Hub publishing, model cards, licences and vLLM serving.
- transformers: https://huggingface.co/docs/transformers/ and the v5 migration guide in the repository (MIGRATION_GUIDE_V5.md at https://github.com/huggingface/transformers)
- TRL: https://huggingface.co/docs/trl/ ; PEFT: https://huggingface.co/docs/peft/ ; datasets: https://huggingface.co/docs/datasets/ ; accelerate: https://huggingface.co/docs/accelerate/
- bitsandbytes: https://github.com/bitsandbytes-foundation/bitsandbytes ; lm-evaluation-harness: https://github.com/EleutherAI/lm-evaluation-harness ; vLLM LoRA docs: https://docs.vllm.ai/ (features, LoRA adapters)
