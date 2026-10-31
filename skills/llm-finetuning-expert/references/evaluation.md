# Evaluation, Publishing and Serving

Measuring a fine-tuned model, publishing it responsibly and serving it: held-out loss, task metrics, lm-evaluation-harness, LLM-as-judge caveats, contamination, safety regression checks, Hub upload, model cards, licences and vLLM. Commands and flags were checked against the lm-evaluation-harness README and interface docs (lm-eval 0.4.13 on PyPI), the vLLM LoRA docs (vLLM 0.32.0 on PyPI) and the installed `hf` CLI of huggingface_hub 2.4.0 (2026-10).

## Contents

1. [Evaluation design](#1-evaluation-design)
2. [Held-out loss and perplexity](#2-held-out-loss-and-perplexity)
3. [Task metrics and generation](#3-task-metrics-and-generation)
4. [lm-evaluation-harness](#4-lm-evaluation-harness)
5. [LLM as judge](#5-llm-as-judge)
6. [Contamination](#6-contamination)
7. [Safety and regression checks](#7-safety-and-regression-checks)
8. [Publishing to the Hub](#8-publishing-to-the-hub)
9. [Model cards and licences](#9-model-cards-and-licences)
10. [Serving with vLLM](#10-serving-with-vllm)

## 1. Evaluation design

- Write the evaluation before training. It defines done. Include the base model and, if relevant, a strong prompted baseline with the same prompts and decoding settings.
- Use three layers: (a) held-out loss on the fine-tuning distribution, (b) task metrics on generated outputs, (c) regression probes for general ability and safety.
- Fix the decoding parameters (greedy or fixed temperature and seed, the same `max_new_tokens`, the same stop tokens) and the same chat template for every model compared.
- Report sample counts and uncertainty. With a few hundred examples, differences of a point or two are within noise; run bootstrap intervals or several seeds for training randomness too.
- Read outputs. Print 20 to 50 random generations per model next to the prompt and reference; most failures (missing stop token, template leaks, repeated text) show up immediately.
- Keep the test set sealed until the model and hyperparameters are final. Use the validation set for all choices.

## 2. Held-out loss and perplexity

- `eval_loss` from the trainer is the mean token negative log-likelihood on the validation set under the same masking as training. Perplexity is `exp(eval_loss)`.
- Loss compares checkpoints of one run or models with the same tokenizer and masking. It does not compare models with different tokenizers, and it does not measure task success.
- Falling training loss with rising validation loss means overfitting. Stop earlier, lower the rate or rank, or add data.
- Very low validation loss on a set with duplicated templates may mean memorisation or leakage, not skill.
- Evaluate unpacked data for per-example numbers (`eval_packing=False`), so that results do not depend on how examples were grouped into blocks.

```python
trainer = SFTTrainer(model=..., args=args, train_dataset=train, eval_dataset=valid, ...)
metrics = trainer.evaluate()
print(metrics["eval_loss"])
```

`eval_dataset` may also be a dict of named datasets in TRL 1.17.1 (the signature allows it), which reports one loss per set; use it to track the target domain and a general-ability set together.

## 3. Task metrics and generation

Pick a metric tied to the use case.

| Task | Metric | Notes |
|---|---|---|
| Structured output | Parse rate, schema validity, field accuracy | Validate with a JSON Schema library; count failures as errors, not skips |
| Classification or extraction | Accuracy, precision, recall, F1 | Report per class when imbalanced |
| Question answering with short answers | Exact match after normalisation, token F1 | Define normalisation in advance |
| Code | Unit tests passed (pass@k) | Run in a sandbox without network access and with resource limits |
| Math or reasoning with checkable answers | Final-answer accuracy | Extract the answer with a fixed rule |
| Summarisation, open-ended writing | Human rating or calibrated judge | Overlap metrics (ROUGE) correlate weakly with quality |
| Instruction following | Rule-based checkers for verifiable constraints | Lengths, formats, keywords |
| Tone and style | Human review of a sample | Plus a classifier only after validating it |

Generation loop with fixed decoding:

```python
import torch

@torch.inference_mode()
def generate(model, tok, messages, max_new_tokens=256):
    enc = tok.apply_chat_template(messages, add_generation_prompt=True,
                                  return_tensors="pt", return_dict=True).to(model.device)
    out = model.generate(**enc, do_sample=False, max_new_tokens=max_new_tokens)
    return tok.decode(out[0, enc["input_ids"].shape[1]:], skip_special_tokens=True)
```

- Use `return_dict=True` (the transformers 5 default) and unpack with `**enc`.
- Batch generation needs left padding for decoder-only models (`tok.padding_side = "left"`).
- Record the stop reason (end token or length limit). A high share of length-limited outputs means the model does not stop.
- Run evaluation in a fresh process from the saved artifact, not from the live trainer, to test the artifact that will ship.

## 4. lm-evaluation-harness

EleutherAI's harness runs standard benchmarks and custom tasks against Hugging Face models, adapters and several serving backends. Install with `pip install "lm_eval[hf]"` for the Hugging Face backend.

```bash
# base model
lm_eval --model hf \
  --model_args pretrained=org/base-model \
  --tasks <task-name> --batch_size 8 \
  --log_samples --output_path results/base

# base plus LoRA adapter
lm_eval --model hf \
  --model_args pretrained=org/base-model,peft=runs/sft/adapter \
  --tasks <task-name> --apply_chat_template \
  --batch_size 8 --log_samples --output_path results/sft
```

Flags confirmed in the README and interface docs:

- `--model hf` selects the transformers backend; `--model_args` passes comma-separated constructor arguments such as `pretrained=`, `revision=`, `dtype=` and `peft=PATH`.
- `--tasks` takes one or more task names.
- `--apply_chat_template` renders prompts with the tokenizer's chat template; `--fewshot_as_multiturn` formats few-shot examples as turns and is enabled automatically with the chat template; `--system_instruction` prepends a system message.
- `--batch_size auto` finds the largest batch size that fits.
- `--log_samples` with `--output_path` stores per-sample model responses for review.
- `--num_fewshot` and `--limit` exist; use `--limit` only for smoke tests, never for reported numbers.
- The README's PEFT example passes quantization through `model_args`; in transformers 5 the `load_in_4bit` argument was removed from `from_pretrained`, so check the harness docs for the current way to evaluate a quantized model, or evaluate the merged 16-bit model.

Practice:

- Run the same tasks on the base and the tuned model with identical settings and compare. A tuned model that wins on its target task and loses a few points on general benchmarks is normal; large drops mean forgetting.
- Chat-templated and plain prompts give different numbers. Fix the choice per comparison and report it.
- Public benchmarks measure general ability, not your task. Write a custom task (YAML task definitions are supported; see the harness docs on adding tasks) or your own script for the target behaviour.
- Pin the harness version and task versions; task definitions change and scores are not comparable across versions.
- Use `accelerate launch -m lm_eval ...` for multi-GPU data-parallel evaluation as shown in the README.

## 5. LLM as judge

A model that scores or ranks outputs is convenient for open-ended tasks and has known failure modes.

- **Position bias**: judges favour the first or the last answer. Evaluate both orders and count only consistent wins.
- **Length and style bias**: longer and more polite answers score higher. Control for length or instruct the rubric explicitly, and check the correlation between length and score.
- **Self-preference**: a judge tends to prefer outputs from its own family or its own style. Do not use the model under test, or its sibling, as the only judge.
- **Rubric drift and variance**: scores change with the prompt wording and sampling. Use a fixed rubric, temperature 0, several repeats and report the spread.
- **Calibration**: label 100 to 200 items by hand, measure judge agreement with humans (accuracy, Cohen's kappa), and report it with the results. Without it a judge score is an opinion.
- **Reference-based judging** (compare to a gold answer) is more reliable than reference-free judging.
- **Leakage**: do not put the answer key or the training data into the judge prompt.
- Use pairwise comparisons with ties against a fixed baseline, and a win rate with an interval, instead of absolute 1 to 10 scores.
- Keep judge model, version and prompt in the run record; changing the judge changes the scale.
- Use human review for decisions with real consequences (safety, release gates).

## 6. Contamination

Contamination means the test content (or near copies) was in the training data of the base model or of your fine-tuning set, so scores overstate ability.

- Check your own data first: deduplicate between train and test, exactly and by near-duplicate search, and by n-gram overlap (for example 13-gram overlap is a common choice; the length is a choice, not a standard).
- For public benchmarks, assume the base model may have seen them. Compare performance on a fresh, private, same-distribution set; a large gap suggests contamination.
- Synthetic training data generated by a model that saw the benchmark can carry the contamination to your model. Filter generated items against the benchmark text.
- Reformulated test items (paraphrase, different numbers) that cause a score drop indicate memorisation.
- Prefer a private test set for the metric that matters, kept out of any public repository and out of the data given to annotators or generators.
- Record the contamination checks that were run next to the results.

## 7. Safety and regression checks

Fine-tuning can reduce refusal and safety behaviour even when the data looks harmless.

- Keep a fixed probe set: general instructions, refusal-appropriate requests, privacy-sensitive prompts, and jailbreak-style prompts relevant to the deployment. Run it on the base and every candidate.
- Track refusal rate on harmful requests, over-refusal on benign ones, and personal data leakage (prompts that try to extract training strings).
- Test for memorisation: prompt with the beginning of rare training records and check whether the model completes them.
- Gate release on no meaningful regression against the base model, or on a documented, reviewed decision.
- Add the required safety examples to the training mix when the use case needs them, and re-run the probes.
- Document limitations, known failure modes and out-of-scope uses in the model card.
- Do not publish a model whose purpose is to remove safeguards; get an independent review before releasing models for sensitive domains.

## 8. Publishing to the Hub

```bash
hf auth login                                     # interactive; the token is stored locally
hf upload user/my-model runs/merged . --private   # create a private repo if absent and upload a folder
```

- `hf upload REPO_ID LOCAL_PATH PATH_IN_REPO` uploads a file or folder (large folders are split into several commits and an interrupted upload resumes if the command is re-run). `--private` creates a private repo when it does not exist; `--repo-type` accepts `model`, `dataset` or `space`; `--include` filters files with globs.
- In training scripts, `SFTConfig(push_to_hub=True, hub_model_id="user/my-model")` pushes checkpoints and the final model; with `hub_private_repo=True` the repo is private (check the installed `TrainingArguments` for the current names).
- Read the token from the environment (`HF_TOKEN`) in CI and use a fine-grained token limited to the repository. Never print or commit it.
- Publish privately first, load the artifact from the Hub in a clean environment, run the evaluation again, and only then change the visibility.
- Upload adapters separately from merged models, with clear names (`-lora`, `-merged`). Include the tokenizer and `chat_template.jinja`.
- Do not upload the training data to a public repo unless its licence and privacy review allow it.

## 9. Model cards and licences

A model card is the `README.md` of the repository, with YAML metadata at the top and sections below.

```markdown
---
base_model: org/base-model
license: apache-2.0
library_name: peft
datasets:
  - user/my-dataset
language:
  - en
tags:
  - lora
  - sft
---

# my-model

## Intended use and out-of-scope use
## Training data
## Training procedure (method, hyperparameters, hardware, library versions)
## Evaluation (metrics, baselines, sample counts, decoding settings)
## Limitations, biases and safety notes
## License and attribution
```

- The `license` value must be consistent with the base model licence and the data licences. The most restrictive applicable term governs.
- Check the base licence for: commercial use limits, user-count thresholds, naming requirements for derivatives, attribution text, acceptable-use policies that flow down to derivatives, and restrictions on using outputs to train other models.
- Gated models require accepting terms on the Hub before download; the tuned derivative usually must carry the same terms. Do not redistribute weights where redistribution is not allowed.
- Training on model-generated data brings the generator's terms along; record them.
- State what is not covered: languages, domains, safety evaluations not run, and the date of the evaluation.
- Mention intended users and the human oversight expected for any high-impact use.
- PEFT writes a stub `README.md` into adapter folders; replace it before publishing.

## 10. Serving with vLLM

```bash
# merged model: an ordinary model path
vllm serve runs/merged --max-model-len 8192

# base model with one or more adapters
vllm serve org/base-model \
  --enable-lora \
  --lora-modules my-task=runs/sft/adapter \
  --max-lora-rank 16
```

- `--enable-lora` and `--lora-modules name=path` expose each adapter as a model name on the OpenAI-compatible API; list names with `GET /v1/models`. The server accepts the other LoRA parameters (`max_loras`, `max_lora_rank`, `max_cpu_loras`) and `--max-lora-rank` must be at least the largest adapter rank you load.
- Runtime loading and unloading of adapters needs `VLLM_ALLOW_RUNTIME_LORA_UPDATING` and extra endpoints; leave it off unless required, because it allows loading weights through the API.
- The server reads the chat template from the tokenizer of the model path. Test a chat completion request and compare its output with your evaluation script; template differences are the usual cause of quality gaps between evaluation and serving.
- Set `--max-model-len` explicitly and match the length used in training. Use the same decoding defaults as in evaluation, or set them per request.
- Put the server behind authentication and network controls; bind to localhost or an internal interface, use an API key option if available in your version (check `vllm serve --help`), and never expose it directly to the internet.
- Pin the vLLM version together with CUDA, torch and transformers; upgrade in a staging environment and re-run the evaluation.
- Compare quality and latency of the merged model against multi-LoRA serving: merged models avoid adapter overhead, while multi-LoRA saves memory when many tasks share one base.
- Monitor request logs for prompt-injection attempts and for outputs matching personal-data patterns; log with privacy limits.
