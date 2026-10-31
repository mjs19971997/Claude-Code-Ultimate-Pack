# TRL: SFT, DPO and GRPO

Training with TRL 1.17 on transformers 5.22: SFTTrainer and SFTConfig, DPOTrainer and DPOConfig, a short GRPO section, hyperparameters, multi-GPU launch with accelerate, DeepSpeed and FSDP at overview level, and migration notes from older TRL and transformers 4 code. Field names, defaults and signatures were read from the installed packages (TRL 1.17.1, transformers 5.22.1, accelerate 1.15.0, 2026-10). SFT (prompt-completion, assistant-only loss, packing), DPO and GRPO each ran for a few steps on CPU with a tiny random Llama-style model.

## Contents

1. [Trainer signatures](#1-trainer-signatures)
2. [SFTConfig](#2-sftconfig)
3. [Hyperparameters](#3-hyperparameters)
4. [DPOConfig and DPOTrainer](#4-dpoconfig-and-dpotrainer)
5. [GRPO briefly](#5-grpo-briefly)
6. [Other trainers](#6-other-trainers)
7. [Launching with accelerate](#7-launching-with-accelerate)
8. [DeepSpeed and FSDP overview](#8-deepspeed-and-fsdp-overview)
9. [Migration notes](#9-migration-notes)
10. [Reading the logs](#10-reading-the-logs)

## 1. Trainer signatures

From `inspect.signature` on TRL 1.17.1:

```text
SFTTrainer(model, args=None, data_collator=None, train_dataset=None, eval_dataset=None,
           processing_class=None, compute_loss_func=None, compute_metrics=None, callbacks=None,
           optimizers=(None, None), optimizer_cls_and_kwargs=None, preprocess_logits_for_metrics=None,
           quantization_config=None, peft_config=None, formatting_func=None)

DPOTrainer(model, ref_model=None, args=None, data_collator=None, train_dataset=None,
           eval_dataset=None, processing_class=None, compute_metrics=None, callbacks=None,
           optimizers=(None, None), quantization_config=None, peft_config=None)

GRPOTrainer(model, reward_funcs=None, args=None, train_dataset=None, eval_dataset=None,
            processing_class=None, reward_processing_classes=None, callbacks=None,
            optimizers=(None, None), quantization_config=None, peft_config=None, tools=None,
            rollout_func=None, environment_factory=None)
```

- `model` is a Hub id or path (string), a `PreTrainedModel` or a `PeftModel`. A string is loaded with `args.model_init_kwargs`; if `dtype` is not set there, TRL loads it in `float32`. Set `model_init_kwargs={"dtype": torch.bfloat16}` or load the model yourself.
- `quantization_config` and `peft_config` are first-class arguments; a quantized model is prepared for training by the trainer.
- `processing_class` is the tokenizer (or processor for vision models); the trainer loads it from the model id if omitted. Pass it when you changed the chat template or the pad token.
- `formatting_func` maps a row to a string for custom text formats; prefer structured `messages` or prompt-completion rows.
- The `tokenizer=` argument of older releases is gone.

## 2. SFTConfig

`SFTConfig` extends `transformers.TrainingArguments`. Fields added by TRL (read from the dataclass):

| Field | Default | Notes |
|---|---|---|
| `model_init_kwargs` | None | Passed to `from_pretrained` when `model` is a string |
| `trust_remote_code` | False | Leave off unless the model code is reviewed |
| `chat_template_path` | None | Path to a template file (or a Hub id) to set on the tokenizer |
| `dataset_text_field` | `"text"` | Column for plain text data |
| `dataset_kwargs` | None | Only `skip_prepare_dataset` is supported |
| `dataset_num_proc` | None | Workers for tokenization |
| `eos_token` | None | Overrides the end-of-turn token (defaults to the tokenizer's EOS) |
| `max_length` | 1024 | Truncation length; with packing it is the block length |
| `truncation_mode` | `"keep_start"` | The only supported value (`keep_end` is deprecated) |
| `shuffle_dataset` | False | Shuffle before training |
| `packing` | False | Pack examples into blocks of `max_length` |
| `packing_strategy` | `"bfd"` | `"bfd"`, `"bfd_split"` or `"wrapped"` |
| `padding_free` | False | Flatten a batch without padding; needs FlashAttention 2 or 3; implied by packing with `"bfd"` |
| `eval_packing` | None | Pack the evaluation set (None follows `packing`) |
| `completion_only_loss` | None | None: completion-only for prompt-completion data, full sequence for plain text |
| `assistant_only_loss` | False | Conversational data; the template needs `{% generation %}` markers |
| `loss_type` | `"nll"` | Also `"dft"`; `"chunked_nll"` is a deprecated alias |
| `activation_offloading` | False | Offload activations to CPU memory |
| `pad_token` | None | Deprecated; set `tokenizer.pad_token` instead |

TRL changes these `TrainingArguments` defaults: `learning_rate=2e-5`, `logging_steps=10`, `gradient_checkpointing=True`, and `bf16` is true when `fp16` is not set. Setting `bf16=False` is required on CPU-only machines.

Minimal SFT run on conversational data with assistant-only loss (the template must carry generation markers):

```python
from trl import SFTConfig, SFTTrainer, get_training_chat_template

patched = get_training_chat_template(tokenizer)   # None when the template already qualifies
if patched is not None:
    tokenizer.chat_template = patched

args = SFTConfig(
    output_dir="runs/sft",
    assistant_only_loss=True,
    max_length=2048,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=8,
    num_train_epochs=2,
    report_to="none",
)
trainer = SFTTrainer(model="org/base-model", args=args, train_dataset=train,
                     processing_class=tokenizer, peft_config=lora)
```

## 3. Hyperparameters

Starting points, to be confirmed by a validation curve (they are conventions, not guarantees):

| Setting | LoRA or QLoRA | Full fine-tuning |
|---|---|---|
| Learning rate | 1e-4 to 2e-4 | 1e-5 to 2e-5 (TRL SFT default 2e-5) |
| Schedule | cosine or linear, warmup 3 to 10 percent | same |
| Epochs | 1 to 3 | 1 to 3 |
| Effective batch size | 16 to 128 sequences | 32 to 256 sequences |
| Weight decay | 0.0 to 0.1 | 0.0 to 0.1 |
| `max_grad_norm` | 1.0 (default) | 1.0 |

- Effective batch size = `per_device_train_batch_size * gradient_accumulation_steps * number of processes`. Compute it and write it in the run record.
- Number of optimizer steps = dataset size divided by effective batch size, times epochs (with packing, count blocks, not rows).
- Warmup: `warmup_steps` accepts an integer or a float below 1 as a ratio of total steps. `warmup_ratio` no longer exists.
- If the loss spikes, lower the learning rate by about half before touching anything else; if the loss falls slowly and stably, raise it.
- Early stopping: use `eval_strategy="steps"`, `save_strategy="steps"`, `load_best_model_at_end=True`, `metric_for_best_model="eval_loss"`, and an `EarlyStoppingCallback` from transformers. The evaluation steps and save steps must be compatible.
- Token budget is a better planning unit than epochs: tokens seen = steps times effective batch times mean sequence length.
- DPO uses much smaller learning rates than SFT: the TRL default is 1e-6 for full fine-tuning; with LoRA values from about 5e-6 up to 5e-5 are common starting points.

## 4. DPOConfig and DPOTrainer

Direct Preference Optimization trains on (prompt, chosen, rejected) triples against a reference policy. Fields read from `DPOConfig` in TRL 1.17.1:

| Field | Default | Notes |
|---|---|---|
| `beta` | 0.1 | Higher means staying closer to the reference |
| `loss_type` | `["sigmoid"]` | A list; options include `sigmoid`, `hinge`, `ipo`, `exo_pair`, `nca_pair`, `robust`, `bco_pair`, `sppo_hard`, `aot`, `aot_unpaired`, `apo_zero`, `apo_down`, `discopop`, `sft`, `sigmoid_norm` |
| `loss_weights` | None | Weights when several loss types are combined |
| `label_smoothing` | 0.0 | Used by robust-DPO and EXO variants |
| `max_length` | 1024 | Total length cap; there is no separate `max_prompt_length` field |
| `precompute_ref_log_probs` | False | Compute reference log-probs once before training to save memory |
| `precompute_ref_batch_size` | None | Batch size for that pass |
| `disable_dropout` | True | Dropout is turned off for stable log-probs |
| `use_weighting` | False | WPO-style weighting |
| `sync_ref_model` | False | Periodically mix the reference toward the policy (`ref_model_mixup_alpha`, `ref_model_sync_steps`) |
| `padding_free` | False | The docs say it is temporarily unavailable after the DPO refactor; check before use |
| `learning_rate` | 1e-6 | TRL default for DPO |
| `model_init_kwargs`, `trust_remote_code`, `activation_offloading` | as in SFT | |

- Reference model: with `ref_model=None` and a `peft_config`, the reference is the base weights with the adapter disabled, so no second copy is held. Without PEFT, TRL creates a frozen copy of the policy, which doubles weight memory; `precompute_ref_log_probs=True` avoids that copy at the cost of a pre-pass.
- Start DPO from an SFT result so the reference already follows the format. Training DPO on a base checkpoint without SFT often fails to produce usable output.
- A first-step loss near 0.693 (the natural log of 2) with zero reward margins is the expected starting point for the sigmoid loss.
- Watch `rewards/accuracies` (fraction of pairs where the chosen reward exceeds the rejected one), `rewards/margins`, and sample outputs. Rising margins with falling output quality or growing length indicate over-optimisation; lower `beta` is not the fix, a lower learning rate or fewer steps is.
- DPO is sensitive to data: noisy or length-biased preferences produce verbose models. Balance chosen and rejected lengths.
- Dataset: `prompt`, `chosen`, `rejected`, plain text or conversational (see [data-and-chat-templates.md](data-and-chat-templates.md)).

```python
import torch
from trl import DPOConfig, DPOTrainer

args = DPOConfig(
    output_dir="runs/dpo",
    beta=0.1,
    learning_rate=5e-6,
    max_length=2048,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=8,
    num_train_epochs=1,
    model_init_kwargs={"dtype": torch.bfloat16},
    report_to="none",
)
trainer = DPOTrainer(model="runs/sft-merged", args=args, train_dataset=prefs,
                     processing_class=tokenizer, peft_config=lora)
```

## 5. GRPO briefly

Group Relative Policy Optimization samples several completions per prompt, scores them with reward functions, and updates the policy using the group-relative advantage. It suits tasks with automatic verifiers.

```python
from datasets import Dataset
from peft import LoraConfig
from trl import GRPOConfig, GRPOTrainer

def format_reward(completions, **kwargs):
    # one float per completion; completions are strings for plain-text prompts
    return [1.0 if c.strip().endswith("</answer>") else 0.0 for c in completions]

train = Dataset.from_list([{"prompt": "Solve: 2 + 2. Answer in <answer></answer> tags."}] * 64)
args = GRPOConfig(
    output_dir="runs/grpo",
    num_generations=8,
    max_completion_length=256,
    per_device_train_batch_size=8,
    gradient_accumulation_steps=2,
    learning_rate=1e-5,
    report_to="none",
)
trainer = GRPOTrainer(model="org/sft-model", reward_funcs=format_reward, args=args,
                      train_dataset=train, peft_config=LoraConfig(r=16, lora_alpha=32,
                      target_modules="all-linear", task_type="CAUSAL_LM"))
```

Facts from the installed package:

- `GRPOConfig` defaults: `num_generations=8`, `max_completion_length=512`, `temperature=1.0`, `beta=0.0` (no reference model is loaded), `epsilon=0.2`, `loss_type="dapo"`, `scale_rewards="group"`, `use_vllm=False`, `vllm_mode="colocate"`.
- The effective batch size (processes times per-device batch times gradient accumulation) must be divisible by `num_generations`.
- `reward_funcs` takes callables, model ids or reward models, or a list of them; weights go in `reward_weights`. Extra dataset columns are passed to reward functions as keyword arguments.
- Rewards must be hard to game. Models exploit weak verifiers (empty answers that pass a format check, test files they can edit). Review samples throughout training.
- Generation dominates cost. `use_vllm=True` moves generation to vLLM (colocated or as a separate server); check the TRL and vLLM docs for compatible versions.
- GRPO needs a base that already gets some reward; if all rewards in a group are equal there is no learning signal.
- `GRPOConfig` has many options (importance sampling level, masking of truncated completions, tool use, environments); read the current docs before enabling them.

## 6. Other trainers

TRL 1.17.1 also exports `KTOTrainer`, `RLOOTrainer`, `RewardTrainer` (for reward models), `DistillationTrainer` and their configs, plus utilities such as `get_peft_config`, `get_quantization_config`, `ModelConfig`, `ScriptArguments`, `pack_dataset` and `clone_chat_template`. Their APIs change quickly; introspect the signatures before use. Example scripts are shipped inside the package under `trl/scripts/` (`sft.py`, `dpo.py`, `grpo.py`, `reward.py`, `kto.py`, `rloo.py`) and a `trl` command-line entry point is installed; `trl --help` lists the sub-commands (distillation, dpo, env, grpo, kto, reward, rloo, sft, vllm-serve in 1.17.1).

## 7. Launching with accelerate

```bash
accelerate config                       # interactive; writes a config file
accelerate launch train_sft.py          # uses the saved config
accelerate launch --num_processes 4 train_sft.py
```

- `accelerate launch` starts one process per GPU (DDP by default). Effective batch size scales with the process count.
- Keep the script free of hard-coded device placement. With quantized models in DDP each process loads the whole model on its own GPU.
- Log and save only on the main process (the trainer does this); do not call `push_to_hub` from every rank by hand.
- `accelerate estimate-memory` and `accelerate merge-weights` are installed commands (the first estimates model memory from a Hub id, which needs network access).

## 8. DeepSpeed and FSDP overview

- **DDP**: replicates the model on each GPU. Use it when the model, gradients and optimizer state fit on one GPU. LoRA and QLoRA of mid-sized models usually do.
- **FSDP**: shards parameters, gradients and optimizer state across GPUs through PyTorch. Configure through the accelerate config (`accelerate config`) or `fsdp` and `fsdp_config` in the training arguments. In transformers 5 the old `fsdp_min_num_params` and `fsdp_transformer_layer_cls_to_wrap` arguments were removed in favour of `fsdp_config`.
- **DeepSpeed ZeRO**: stage 1 shards optimizer state, stage 2 adds gradients, stage 3 adds parameters. Use a JSON config with `"auto"` values so batch size and precision come from the trainer arguments. Offload to CPU only when memory forces it, as it slows training a lot. TRL has special handling for ZeRO-3 (for example gathering weights for generation in GRPO).
- Mixing quantization (QLoRA) with ZeRO-3 or FSDP has version-specific limits. Check the TRL, PEFT and accelerate docs before combining them.
- Always save with the trainer's `save_model` so sharded states are gathered correctly, and test loading the result in a single process.
- Details and flag names move between accelerate and DeepSpeed releases; confirm in the current docs (DeepSpeed 0.19 is the latest on PyPI at the time of writing).

## 9. Migration notes

| Old | Current |
|---|---|
| `SFTTrainer(tokenizer=tok)` | `SFTTrainer(processing_class=tok)` |
| `SFTConfig(max_seq_length=...)` | `SFTConfig(max_length=...)` |
| `DPOConfig(max_prompt_length=...)` | removed; use `max_length` and truncate the data |
| `warmup_ratio=0.05` | `warmup_steps=0.05` |
| `evaluation_strategy="steps"` | `eval_strategy="steps"` |
| `from_pretrained(load_in_4bit=True)` | `quantization_config=BitsAndBytesConfig(load_in_4bit=True, ...)` |
| `from_pretrained(use_auth_token=...)` | `token=` (or the stored login) |
| `torch_dtype=` | `dtype=` |
| `tokenizer.apply_chat_template(msgs, tokenize=True)` returns a list | returns a `BatchEncoding`; index `["input_ids"]` or pass `return_dict=False` |
| `trainer.train(model_path=...)` | `resume_from_checkpoint=` |
| `DataCollatorForCompletionOnlyLM` for prompt masking (not exported by `trl` 1.17.1) | prompt-completion data (default completion-only loss) or `assistant_only_loss=True` |
| `save_pretrained(safe_serialization=False)` | removed; safetensors only |

- If a snippet from a blog or tutorial fails with an unexpected keyword argument, compare with `dataclasses.fields(SFTConfig)` and the migration guide shipped in the transformers repository (`MIGRATION_GUIDE_V5.md`).

## 10. Reading the logs

- `loss` (training) and `eval_loss`: compare on the same masking; packing changes the denominator per step but not the per-token meaning.
- `grad_norm`: spikes precede divergence; sustained values far above 1.0 with clipping active mean heavy clipping.
- `mean_token_accuracy` and `entropy` appear in SFT logs; an entropy collapse to near zero on a small dataset signals memorisation.
- `num_tokens`: tokens processed so far; use it to compute throughput and token budgets.
- DPO adds `rewards/chosen`, `rewards/rejected`, `rewards/margins`, `rewards/accuracies`, `logps/chosen` and `logps/rejected`.
