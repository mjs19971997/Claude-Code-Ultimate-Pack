# PEFT, LoRA and QLoRA

Parameter-efficient fine-tuning with PEFT 0.21 and transformers 5: LoraConfig fields, choosing rank and target modules, QLoRA with bitsandbytes, saving, loading and merging adapters, using several adapters, and memory budgeting. Field names and defaults were read from the installed packages (PEFT 0.21.2, transformers 5.22.1, bitsandbytes 0.50.2 on PyPI, 2026-10); an adapter save, reload and `merge_and_unload()` round trip was run on CPU with a tiny random model.

## Contents

1. [How LoRA works](#1-how-lora-works)
2. [LoraConfig fields](#2-loraconfig-fields)
3. [Choosing rank, alpha and targets](#3-choosing-rank-alpha-and-targets)
4. [QLoRA with bitsandbytes](#4-qlora-with-bitsandbytes)
5. [Using PEFT with a plain Trainer](#5-using-peft-with-a-plain-trainer)
6. [Saving and loading adapters](#6-saving-and-loading-adapters)
7. [Merging](#7-merging)
8. [Several adapters](#8-several-adapters)
9. [Memory budgeting](#9-memory-budgeting)
10. [Troubleshooting](#10-troubleshooting)

## 1. How LoRA works

LoRA freezes a weight matrix `W` and learns a low-rank update `B @ A` with rank `r`, so the layer computes `W x + (alpha / r) * B A x`. Only `A` and `B` receive gradients. Trainable parameters are usually well under 5 percent of the model, and the adapter file is megabytes, not gigabytes.

- The update is initialised so that the adapter starts as a no-op (`init_lora_weights=True` is the default); the first loss values equal those of the base model.
- Scaling is `lora_alpha / r`. With `use_rslora=True` the scale is `lora_alpha / sqrt(r)`, which keeps higher ranks trainable at the same learning rate.
- `use_dora=True` enables weight-decomposed LoRA, which adds overhead and is not supported by every combination of layer type and quantization; check the PEFT docs before relying on it.
- LoRA is a trade-off, not a free lunch: on tasks needing large knowledge changes or long training it can learn less than full fine-tuning, and it also forgets less.

## 2. LoraConfig fields

Read from `dataclasses.fields(LoraConfig)` in PEFT 0.21.2 (defaults in brackets where relevant):

| Field | Default | Meaning |
|---|---|---|
| `r` | 8 | Rank of the update matrices |
| `lora_alpha` | 8 | Scaling numerator |
| `lora_dropout` | 0.0 | Dropout on the adapter input; 0.05 to 0.1 can help on small data |
| `target_modules` | None | Names (list or regex) of modules to adapt, or the string `"all-linear"` |
| `exclude_modules` | None | Names to skip |
| `bias` | `"none"` | `"none"`, `"all"` or `"lora_only"` |
| `task_type` | None | Use `"CAUSAL_LM"` for decoder language models |
| `modules_to_save` | None | Extra modules trained fully and saved with the adapter (for example resized embeddings or a classifier head) |
| `use_rslora` | False | Rank-stabilised scaling |
| `use_dora` | False | Weight-decomposed variant |
| `init_lora_weights` | True | Initialisation method; other values select alternative initialisers (check the docs) |
| `rank_pattern`, `alpha_pattern` | None | Per-module overrides of `r` and `lora_alpha` |
| `layers_to_transform`, `layers_pattern` | None | Restrict to specific layer indices |
| `target_parameters` | None | Adapt raw parameters (used for mixture-of-experts weights that are not `nn.Linear`); check the docs for supported models |
| `trainable_token_indices` | None | Train selected token embeddings without resizing |

The config has many more fields for variants (EVA, CorDA, LoRA-GA, LoftQ, aLoRA and others). Treat them as advanced options and read the PEFT docs for each before use.

```python
from peft import LoraConfig, get_peft_model

cfg = LoraConfig(
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    target_modules="all-linear",
    task_type="CAUSAL_LM",
)
model = get_peft_model(model, cfg)
model.print_trainable_parameters()
```

With TRL you normally pass `peft_config=cfg` to the trainer and skip `get_peft_model`.

## 3. Choosing rank, alpha and targets

- **Targets**: `"all-linear"` (every linear layer except the output head) is the usual strong default. Adapting only attention projections (`q_proj`, `v_proj` and similar) is cheaper and often weaker. Module names differ per architecture; list them with `[n for n, _ in model.named_modules()]`.
- **Rank**: 8 to 64 covers most instruction-tuning work. Start at 16. Increase only when training loss plateaus high on a clean, large dataset; increasing rank on a small noisy dataset mostly increases overfitting.
- **Alpha**: a common convention is `lora_alpha = 2 * r` or `lora_alpha = r`. Alpha and learning rate interact; change one at a time.
- **Dropout**: 0.0 for large datasets, 0.05 to 0.1 for small ones.
- **Learning rate**: LoRA tolerates and usually needs a higher rate than full fine-tuning. A start around 1e-4 to 2e-4 is typical; reduce when the loss spikes. These are starting points, not guarantees.
- **Embeddings and head**: leave frozen unless you add tokens. If you add special tokens, resize embeddings and add `embed_tokens` and `lm_head` to `modules_to_save` (this increases adapter size and memory).
- **Reproducibility**: PEFT initialises `A` randomly; set the seed.

## 4. QLoRA with bitsandbytes

QLoRA keeps the base model in 4-bit NormalFloat and trains LoRA adapters on top. In transformers 5 the old `load_in_4bit=True` argument to `from_pretrained` is removed; pass a `BitsAndBytesConfig`.

```python
import torch
from transformers import AutoModelForCausalLM, BitsAndBytesConfig

bnb = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=torch.bfloat16,
)
model = AutoModelForCausalLM.from_pretrained(
    "org/base-model",
    quantization_config=bnb,
    dtype=torch.bfloat16,
    device_map="auto",
)
```

- `BitsAndBytesConfig` fields checked: `load_in_4bit`, `load_in_8bit`, `bnb_4bit_compute_dtype`, `bnb_4bit_quant_type` (default `fp4`; use `nf4`), `bnb_4bit_use_double_quant`, `bnb_4bit_quant_storage`, `llm_int8_skip_modules`.
- bitsandbytes needs a supported accelerator and driver; check the bitsandbytes docs for the current hardware list. It is not available for plain CPU training in the same way.
- With TRL, pass the config as `quantization_config=` to `SFTTrainer` or `DPOTrainer` and the model id as a string; the trainer prepares a quantized model for training itself. When building the model yourself outside TRL, call `peft.prepare_model_for_kbit_training(model)` (signature `use_gradient_checkpointing=True, gradient_checkpointing_kwargs=None, auto_clear_cache=True`) before `get_peft_model`.
- Compute dtype should be bf16 where supported; mismatched compute and adapter dtypes cause slow or unstable training.
- Do not merge an adapter into the 4-bit weights for deployment; merge into a 16-bit reload of the base (section 7).
- Multi-GPU QLoRA with DDP needs each process to place the whole quantized model on its own device. A single `device_map="auto"` splits one model across devices (model parallelism) and is a different setup. Check the accelerate and TRL docs for the current recommended settings.
- QLoRA is slower than bf16 LoRA for the same model because of dequantization; use it when memory forces it.

## 5. Using PEFT with a plain Trainer

When you do not use TRL:

```python
from transformers import Trainer, TrainingArguments

model = get_peft_model(model, cfg)
model.enable_input_require_grads()      # needed with gradient checkpointing on a frozen base

args = TrainingArguments(
    output_dir="runs/lora",
    per_device_train_batch_size=4,
    gradient_accumulation_steps=8,
    learning_rate=2e-4,
    num_train_epochs=2,
    warmup_steps=0.05,
    bf16=True,
    gradient_checkpointing=True,
    logging_steps=10,
    eval_strategy="steps",
    eval_steps=100,
    report_to="none",
)
trainer = Trainer(model=model, args=args, train_dataset=train, eval_dataset=valid,
                  data_collator=collator, processing_class=tokenizer)
```

Notes on the transformers 5 `TrainingArguments`: `warmup_ratio` is removed (a float below 1 in `warmup_steps` is the ratio), `evaluation_strategy` is `eval_strategy`, `overwrite_output_dir` is removed, `logging_steps` defaults to 500, `num_train_epochs` to 3.0 and `learning_rate` to 5e-5. Set them explicitly. TRL configs override several of these (`learning_rate=2e-5` for SFT, `logging_steps=10`, `gradient_checkpointing=True`).

## 6. Saving and loading adapters

```python
trainer.save_model("runs/lora/adapter")      # or model.save_pretrained(...)
```

The folder contains `adapter_config.json`, `adapter_model.safetensors`, a generated `README.md`, and (when saved by a Trainer with a tokenizer) the tokenizer files and `chat_template.jinja`.

```python
import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM

base = AutoModelForCausalLM.from_pretrained("org/base-model", dtype=torch.bfloat16)
model = PeftModel.from_pretrained(base, "runs/lora/adapter")        # inference
# model = PeftModel.from_pretrained(base, path, is_trainable=True)   # resume training
```

- `adapter_config.json` records `base_model_name_or_path`. Keep that base model available at the same revision; an adapter is meaningless without it.
- Load the base in the dtype used for training or for serving; loading in a different dtype changes numerical results slightly.
- Adapters from a quantized base load onto a 16-bit base for evaluation, but results differ a little from the 4-bit run; evaluate the form you will serve.
- Push an adapter alone with `model.push_to_hub("user/repo", private=True)` or `hf upload`. The README that PEFT generates is a stub; replace it with a real model card (see [evaluation.md](evaluation.md)).

## 7. Merging

`merge_and_unload()` folds the adapter into the base weights and returns the plain base model. Signature in PEFT 0.21.2: `merge_and_unload(progressbar=False, safe_merge=False, adapter_names=None)`.

```python
import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

base = AutoModelForCausalLM.from_pretrained("org/base-model", dtype=torch.bfloat16)
peft_model = PeftModel.from_pretrained(base, "runs/lora/adapter")
merged = peft_model.merge_and_unload(safe_merge=True)   # safe_merge checks for NaN weights
merged.save_pretrained("runs/merged")
AutoTokenizer.from_pretrained("runs/lora/adapter").save_pretrained("runs/merged")
```

- Merge into a 16-bit base. Merging into 4-bit weights requires dequantization and re-quantization and loses precision.
- After merging, run the held-out evaluation again; bf16 rounding can change outputs slightly.
- Compare logits of `peft_model` and `merged` on a fixed input (maximum absolute difference below a small tolerance) as a unit test.
- Merged models are ordinary checkpoints and can be quantized, converted and served like any other. They carry the licence terms of the base model.
- Keep the adapter as well; it is the cheap, replaceable artifact.
- Do not merge two adapters trained on different bases, or adapters of different ranks, without reading `add_weighted_adapter` in the PEFT docs for the supported combination methods.

## 8. Several adapters

- `model.load_adapter(path, adapter_name="task_b")` loads another adapter into a `PeftModel`; `model.set_adapter("task_b")` switches the active one.
- `with model.disable_adapter():` runs the base model; DPO with LoRA uses this to compute reference log-probabilities without a second model.
- vLLM serves many adapters over one base: `vllm serve BASE --enable-lora --lora-modules name_a=path_a name_b=path_b`, with `--max-lora-rank` at least the largest rank. Requests choose an adapter by its name in the `model` field. Dynamic loading at runtime needs the `VLLM_ALLOW_RUNTIME_LORA_UPDATING` environment variable (see the vLLM LoRA docs) and widens the attack surface of the server.
- Average or combine adapters only after evaluating the result; naive averaging often degrades both tasks.

## 9. Memory budgeting

Estimates for planning; always measure on a real batch.

| Component | Rule of thumb |
|---|---|
| Base weights bf16 | 2 bytes per parameter |
| Base weights 4-bit | about 0.5 bytes per parameter plus small quantization constants |
| Full fine-tuning gradients | 2 to 4 bytes per parameter depending on dtype |
| Full fine-tuning AdamW state | 8 bytes per parameter in fp32 (two moments), plus an fp32 master copy in some mixed-precision setups |
| LoRA gradients and state | only for adapter parameters, usually under a few percent of the model |
| Activations | grows with batch size times sequence length times layers; reduced several-fold by gradient checkpointing at about 30 percent more compute |
| Logits | batch times sequence length times vocabulary size in 32-bit; large vocabularies make this a major term, so lower batch size or sequence length before anything else |

Worked example (estimates): a 7 billion parameter model needs about 14 GB for bf16 weights, about 4 GB for 4-bit weights, and well over 80 GB for full fine-tuning with AdamW before activations. LoRA on bf16 weights needs the 14 GB plus adapter state plus activations; QLoRA needs the 4 GB plus the same extras.

Levers in order of preference: shorter `max_length`, smaller per-device batch with more accumulation, gradient checkpointing (default on in TRL configs), packing or padding-free batches, 8-bit or paged optimizers (`optim` argument; check the installed names), QLoRA, activation offloading (`activation_offloading=True` in TRL configs), then sharding with FSDP or DeepSpeed ZeRO.

## 10. Troubleshooting

- **Loss is NaN**: learning rate too high, fp16 overflow (use bf16), a corrupt batch, or an empty label row. Lower the rate, enable gradient clipping (`max_grad_norm`, default 1.0), and inspect the first failing batch.
- **Loss does not move**: the adapter is not attached (check `print_trainable_parameters()`), `target_modules` matches nothing, labels are all `-100`, or the learning rate is far too low.
- **"element 0 of tensors does not require grad"**: gradient checkpointing with a frozen base; call `enable_input_require_grads()` or use the TRL trainers, which handle it.
- **Out of memory at the first step**: reduce `max_length` and batch size; check that the model did not load in float32 (TRL loads a model passed as a string in float32 unless `dtype` is set in `model_init_kwargs`).
- **Adapter works in training but not after loading**: base revision, dtype or tokenizer differ; the chat template was not saved; special tokens were added without saving the resized embeddings in `modules_to_save`.
- **Quality drops after merging**: merged into a quantized base, or merged with a different dtype than evaluated. Re-evaluate the merged model and compare with the adapter run.
- **Missing target modules error**: names differ per architecture; print module names and match them, or use `"all-linear"`.
