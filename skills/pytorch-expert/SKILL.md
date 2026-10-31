---
name: pytorch-expert
description: >-
  Writes, debugs and speeds up PyTorch 2.x code: devices and dtypes, autograd, nn.Module design, DataLoader, training loops, torch.autocast with torch.amp.GradScaler, torch.compile, checkpoints, reproducibility, DDP and FSDP2 with torchrun, torch.profiler, torch.export and ONNX. Use when editing .py files that import torch, .pt or .pth checkpoints, torchrun commands, or fixing NaN loss, CUDA out-of-memory, graph breaks or hangs. Not for classical ML, experiment tracking or serving (use ml-engineering-expert), transformers, PEFT or TRL fine-tuning (use llm-finetuning-expert), NumPy or SciPy (use scientific-python-expert), or general Python tooling (use python-expert).
license: MIT
metadata:
  version: "3.2.0"
---

# PyTorch Expert

This skill covers PyTorch 2.x model code from tensor basics to multi-GPU training: devices and dtypes, autograd, module design, data loading, mixed precision, `torch.compile`, checkpoints, reproducibility, DDP and FSDP2, profiling and memory debugging, and export. It targets the current stable line and flags API names that changed. Fine-tuning large language models, experiment tracking, model serving and general Python packaging belong to other skills.

> Verified against PyTorch 2.15.0 (PyPI release 2026-10-28; installed and run locally on CPU and 2-process gloo, API signatures inspected, GitHub release notes read), onnx 1.23.2, onnxscript 0.7.2, onnxruntime 1.31.1 and pytorch-lightning 2.6.6 on PyPI (2026-10).

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

- Covered: tensors, dtypes and devices; autograd; `nn.Module`, initialisation and `state_dict`; `Dataset`, `DataLoader` and samplers; training and evaluation loops; `torch.autocast` and `torch.amp.GradScaler`; `torch.compile`; checkpointing and `torch.load`; reproducibility; DDP and FSDP2 launched with `torchrun`; `torch.profiler` and CUDA memory debugging; `torch.export` and ONNX export in brief; model tests; PyTorch Lightning in one paragraph.
- Not covered: classical ML, experiment tracking, model registries and serving stacks (ml-engineering-expert); Hugging Face transformers, PEFT, TRL and LLM fine-tuning recipes (llm-finetuning-expert); array computing with NumPy and SciPy (scientific-python-expert); `pyproject.toml`, uv, ruff and pytest configuration (python-expert); container images (docker-expert); GPU cluster scheduling on Kubernetes (kubernetes-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Version and install | Current stable is 2.15.0 (PyPI, 2026-10-28), `Requires-Python >=3.11`; wheels exist for 3.11 to 3.15 and free-threaded 3.14t. The default Linux wheel is built for CUDA 13.2 (CUDA 13 wheels need driver 580 or newer); the 2.15 notes say cu126 and cu130 wheels are no longer published. MPS needs macOS 15 or newer. Pick the exact index URL with the selector on pytorch.org |
| Devices | `torch.accelerator.current_accelerator(check_available=True)` returns the usable accelerator device or `None` and covers CUDA, MPS, XPU and others (without `check_available=True` it reports the compiled-in accelerator even when no driver is present, checked on 2.15); `torch.cuda.is_available()` and `torch.backends.mps.is_available()` are the backend-specific checks. Tensors on different devices cannot be combined; move with `.to(device)` |
| Autocast and scaler | `torch.autocast(device_type, dtype=...)` and `torch.amp.GradScaler("cuda")`. `torch.cuda.amp.GradScaler` and `torch.cuda.amp.autocast` still run but emit a deprecation warning pointing to the `torch.amp` forms (checked on 2.15). bf16 needs no scaler; fp16 does |
| `torch.compile` | `torch.compile(model, mode=..., fullgraph=..., dynamic=..., backend=...)`. Modes listed by `torch._inductor.list_mode_options()` on 2.15: `default`, `reduce-overhead`, `max-autotune`, `max-autotune-no-cudagraphs` and `lite`. Default `recompile_limit` is 8 (`torch._dynamo.config.recompile_limit`). `nn.Module.compile()` compiles in place. 2.15 notes: compile works on Python 3.15 |
| `torch.load` | `weights_only` defaults to `True` since 2.6 (a documented backward-incompatible change); a pickled custom class fails with `UnpicklingError` unless allow-listed via `torch.serialization.add_safe_globals([Cls])` or the `safe_globals([...])` context manager. 2.15 notes: nested tensors are no longer allow-listed |
| `DataLoader` | Keyword arguments checked on 2.15: `num_workers`, `pin_memory`, `persistent_workers`, `prefetch_factor`, `worker_init_fn`, `generator`, `multiprocessing_context`, `in_order`, `timeout`, `drop_last`. `prefetch_factor` and `persistent_workers` require `num_workers > 0` |
| Optimizers | `torch.optim.AdamW(params, lr, betas, eps, weight_decay=0.01, foreach=None, fused=None, ...)`. 2.15 emits a `FutureWarning` when `params` is a bare `set`; pass a list or named groups |
| FSDP2 | `from torch.distributed.fsdp import fully_shard, MixedPrecisionPolicy, CPUOffloadPolicy`. Signature on 2.15: `fully_shard(module, *, mesh, reshard_after_forward, shard_placement_fn, mp_policy, offload_policy, ignored_params, dp_mesh_dims)`. It mutates the module in place and returns it as an `FSDPModule`. 2.15 notes: with `reduce_dtype=None` gradients now reduce in the parameter dtype, so set `reduce_dtype` explicitly to keep results stable across upgrades |
| DDP and launch | `torchrun --nproc_per_node=N script.py` sets `RANK`, `LOCAL_RANK` and `WORLD_SIZE`. `DistributedDataParallel(model, device_ids=[local_rank])`. 2.15 notes: the rewritten NCCL backend is the default; `nccl-legacy` and `TORCH_DIST_USE_NCCL2=0` are announced for removal in the next release |
| Distributed checkpoint | `torch.distributed.checkpoint` (`save`, `load`, `async_save`) with `torch.distributed.checkpoint.state_dict` (`get_state_dict`, `set_state_dict`, `get_model_state_dict`, `StateDictOptions(full_state_dict, cpu_offload, ...)`). Works with FSDP2 and DDP |
| Export | `torch.export.export(mod, args, dynamic_shapes=..., strict=False)` returns an `ExportedProgram`; `.module()` gives a callable. `torch.onnx.export(model, args, dynamic_shapes=...)` uses the dynamo-based exporter by default (`dynamo=True`) and returns an `ONNXProgram` (`.save(path)`); it needs the `onnx` and `onnxscript` packages |
| Profiling | `torch.profiler.profile(activities, schedule=schedule(wait, warmup, active, repeat), on_trace_ready, record_shapes, profile_memory, with_stack)`; `torch.cuda.memory._record_memory_history()` and `_dump_snapshot()` capture allocator history for the memory viewer |

## 3. Workflow

1. Read the training entry point, the environment file (`pyproject.toml`, `requirements*.txt`) and `python -c "import torch; print(torch.__version__, torch.version.cuda)"`. Identify the PyTorch version, accelerator, launcher (`python`, `torchrun`, SLURM) and whether Lightning or another framework owns the loop.
2. Reproduce on the smallest input: a CPU run, one batch, a few steps, `torch.manual_seed` set. Confirm the failure before changing code.
3. Locate the layer of the problem before editing: data (shapes, dtypes, labels, workers), model (init, normalisation, loss), optimisation (learning rate, scaler, clipping) or system (device placement, memory, communication). Print shapes, dtypes, devices and `torch.isfinite(x).all()` at the boundaries.
4. For speed problems measure first with `torch.profiler` or a timed loop with `torch.cuda.synchronize()`; fix the input pipeline before the model, and the model before distribution.
5. Keep changes small and keep the project's loop structure. Add a test that fails without the change (a shape test, an overfit-one-batch test, a checkpoint round trip).
6. Run the code on CPU first when possible, then on the target device. Report the PyTorch version used, what ran and what could not be run (for example no GPU in the sandbox).
7. For multi-process work, test with two processes on CPU using the `gloo` backend before spending GPU time.

## 4. Decision Rules

- If the batch fits one GPU and the model fits with room for activations, use DDP; if the model, gradients or optimizer state do not fit, use FSDP2 (`fully_shard`); if only one device is available, skip distribution.
- If an FSDP1 wrapper (`FullyShardedDataParallel`) already exists and works, keep it unless a migration was requested; for new code use `fully_shard`.
- If the hardware supports bf16 (Ampere or newer on NVIDIA, CPUs with native bf16 support; check the MPS notes for your macOS version), use `torch.autocast(dtype=torch.bfloat16)` without a scaler; use fp16 with `torch.amp.GradScaler` only when bf16 is unavailable.
- If a model is called many times with stable shapes, try `torch.compile` and measure; if shapes change every step, mark dynamic dimensions or compile fixed buckets rather than accept repeated recompiles.
- If `torch.compile` shows graph breaks in a hot path, fix the cause (data-dependent Python control flow, `.item()`, prints, unsupported calls) or exclude one function with `torch.compiler.disable`; use `fullgraph=True` in tests to turn breaks into errors.
- If the loader is the bottleneck (GPU utilisation drops between steps), raise `num_workers`, set `pin_memory=True` with `non_blocking=True` copies and `persistent_workers=True`, and move decoding or augmentation out of `__getitem__` hot spots before touching the model.
- If bitwise reproducibility is required, seed everything and call `torch.use_deterministic_algorithms(True)`; if only approximate repeatability is needed, seed and accept some non-determinism for speed.
- If a checkpoint holds only tensors, save a `state_dict` and load with `weights_only=True`; if it holds custom classes, add them to the safe globals deliberately, or store plain dicts instead.
- If weights come from an untrusted source, prefer the `safetensors` format over pickle-based `.pt` files.
- If training must resume exactly, save model, optimizer, scheduler, scaler, RNG states, epoch and step in one checkpoint.
- If the target is C++, mobile or another runtime, use `torch.export` or `torch.onnx.export`; if the target is Python serving, keep the eager or compiled module.
- If the project already uses PyTorch Lightning, extend its `LightningModule` and `Trainer` instead of adding a hand-written loop beside it; for new code a plain loop is fine for most research and production work.

## 5. Coding Standards

- Subclass `nn.Module`, build layers in `__init__`, and keep `forward` free of side effects. Register tensors that are not parameters with `register_buffer`; use `nn.ModuleList` and `nn.ModuleDict` for containers so parameters are tracked.
- Call the module (`model(x)`), never `model.forward(x)`, so hooks run.
- Pass `device` and `dtype` explicitly when creating tensors inside modules (`torch.zeros(n, device=x.device, dtype=x.dtype)` or `x.new_zeros(n)`); do not hard-code `"cuda"`.
- Select the device once at the entry point and pass it down; do not call `.cuda()` in library code.
- Annotate shapes in docstrings or comments (`# (B, T, C)`); validate rank and last-dimension size at module boundaries with explicit exceptions, not `assert`.
- Use `model.train()` and `model.eval()` explicitly; wrap evaluation in `torch.no_grad()` or `torch.inference_mode()`.
- Call `optimizer.zero_grad(set_to_none=True)` (the default) before `backward`, and do not call `.item()`, `.cpu()` or `.numpy()` inside the step except to log every N steps.
- Accumulate logged losses as `loss.detach()` tensors, or as floats from `loss.item()`; calling `float(loss)` on a tensor that requires grad emits a warning on 2.15.
- Prefer `torch.nn.functional.scaled_dot_product_attention` to hand-written attention; restrict backends, if needed, with `torch.nn.attention.sdpa_kernel`.
- Use in-place operations (`add_`, `relu_`) only when autograd does not need the overwritten value; a "modified by an inplace operation" error means it does.
- Use `torch.save(model.state_dict(), path)` and `load_state_dict`, never pickle a whole module.
- Type-annotate public functions; keep the style rules of python-expert for imports, naming and formatting.

## 6. Project Structure

```text
vision-train/
|-- pyproject.toml
|-- configs/
|   `-- base.yaml            # hyperparameters; one file per experiment
|-- src/vision_train/
|   |-- data.py              # Dataset, transforms, build_loaders()
|   |-- model.py             # nn.Module definitions
|   |-- train.py             # train_one_epoch, evaluate, main()
|   |-- ckpt.py              # save/load helpers, atomic writes
|   `-- dist.py              # init/cleanup of process groups, rank helpers
|-- scripts/
|   `-- launch.sh            # torchrun invocation
`-- tests/
    |-- test_model_shapes.py
    |-- test_overfit_batch.py
    `-- test_checkpoint_roundtrip.py
```

- Keep model definitions free of data, logging and distributed code so they can be exported, compiled and tested alone.
- Keep one function that builds model, optimizer and scheduler from a config; training and resume paths both call it.
- Write checkpoints and logs outside the source tree and out of version control.

## 7. Design Patterns

- **Config-driven model factory**: a dataclass or dict of hyperparameters builds the module, so checkpoints can store the config next to the weights and rebuild the same architecture.
- **Training step as a function**: `def step(model, batch, opt, scaler) -> Tensor` isolates autocast, backward, clipping and the optimizer step; the loop, the profiler and tests all reuse it.
- **Buffers for non-trainable state**: running statistics, masks and positional tables go through `register_buffer(..., persistent=False)` when they should not enter the `state_dict`.
- **Regional compilation**: compile repeated blocks (`for b in model.blocks: b.compile()`) to cut compile time and recompiles compared with compiling a whole large model.
- **Wrap order for distributed**: build the model on the target device or `meta` device, apply activation checkpointing, then `fully_shard` each block and the root, then build the optimizer from the sharded parameters. Details: [references/distributed.md](references/distributed.md).
- **Atomic checkpoints**: write to `path.tmp`, then `os.replace(tmp, path)`, so a killed job never leaves a truncated file.
- **Rank-0 side effects**: logging, file writes and evaluation summaries run under `if rank == 0`, while every rank still takes part in collective calls (barriers, `dcp.save`, `all_reduce`).
- **Deterministic data order**: a seeded `torch.Generator` for the sampler and `DistributedSampler.set_epoch(epoch)` each epoch. Details: [references/data-loading.md](references/data-loading.md).

## 8. Best Practices

- Start every new model with the overfit-one-batch test: a correct model, loss and optimizer drive the loss on a single batch close to zero within a few hundred steps.
- Check the initial loss against theory (for `C`-class cross-entropy it is about `ln(C)`) before training.
- Normalise inputs, use sensible initialisation, and clip gradients (`torch.nn.utils.clip_grad_norm_`) for transformers and recurrent models. With a scaler, call `scaler.unscale_(optimizer)` before clipping.
- Keep the loss computation in float32; autocast already does this for common losses, but custom reductions should cast explicitly.
- Set `torch.set_float32_matmul_precision("high")` for faster fp32 matmuls on GPUs that support TF32 when full fp32 accuracy is not required (the default is `"highest"`).
- Log learning rate, gradient norm, loss scale (fp16) and throughput, not only loss.
- Use `torch.optim.lr_scheduler` objects stepped once per optimizer step or per epoch consistently, and save their state.
- Freeze parameters with `requires_grad_(False)` before building the optimizer, and pass only trainable parameters to it.
- Use `torch.utils.checkpoint.checkpoint(fn, *args, use_reentrant=False)` for activation checkpointing; always pass `use_reentrant` explicitly.
- Pin library versions; PyTorch minor releases change defaults (`weights_only`, FSDP2 reduce dtype, NCCL backend). Read the release notes' backward-incompatible section before upgrading.

## 9. Performance

- Profile before tuning. Order of checks: data loading, host-to-device copies, kernel launch overhead (many tiny ops), precision, then memory. See [references/compile-and-performance.md](references/compile-and-performance.md).
- Use bf16 autocast, fused optimizers (`fused=True` for AdamW on CUDA), `scaled_dot_product_attention`, and channels-last for convolutional nets on GPU where measured faster.
- Avoid host-device synchronisation in the loop: `.item()`, `.cpu()`, `print(tensor)`, boolean indexing with data-dependent size and `if tensor:` force a sync.
- Batch small tensors together; replace Python loops over elements with vectorised ops; preallocate outputs instead of `torch.cat` in a loop.
- `torch.compile` reduces Python and launch overhead and fuses pointwise ops; the first call compiles (seconds to minutes), so benchmark after warm-up and with `torch.cuda.synchronize()` around timers.
- `mode="reduce-overhead"` uses CUDA graphs and needs static shapes and care with tensors reused across steps; `max-autotune` raises compile time for kernel search. Measure both against `default`.
- Increase batch size or use gradient accumulation to keep the GPU busy; under DDP wrap accumulation steps (all but the last) in `model.no_sync()`.
- For memory: autocast, activation checkpointing, smaller micro-batches with accumulation, `optimizer.zero_grad(set_to_none=True)`, FSDP2 sharding, then CPU offload as a last resort. See the memory section of [references/compile-and-performance.md](references/compile-and-performance.md).
- Data loading: `num_workers` of a few per GPU, `persistent_workers=True`, `pin_memory=True`, cached or pre-decoded data, and no per-item Python work that vectorises.

## 10. Security

- `torch.load` unpickles by default unless `weights_only=True`. Since 2.6 the default is `True`, but do not pass `weights_only=False` for files you did not create, and do not widen `add_safe_globals` to arbitrary callables. The 2.15 notes list a hardening fix to the `weights_only` unpickler, so keep PyTorch current when loading external files.
- Prefer `safetensors` for weights shared across trust boundaries; it stores tensors only.
- Treat third-party checkpoints, datasets and model code as untrusted: pin the source and verify a published checksum before loading.
- Never call `torch.jit.load`, `pickle.load` or `torch.load(weights_only=False)` on user uploads in a service.
- Treat the rendezvous store behind `torchrun` and `init_process_group` as unauthenticated; run multi-node jobs on a private network and do not expose the master port.
- Do not put API keys, dataset credentials or tokens in training scripts or configs; read them from the environment or a secret manager and keep them out of logged hyperparameters.
- Do not log raw training samples that contain personal data; log shapes, IDs and aggregates.
- Pin dependencies by hash or lockfile in production images and rebuild regularly for security fixes.

## 11. Testing

- **Shape tests**: for a few batch sizes and sequence lengths assert output shapes and dtypes; include batch size 1 and a non-divisible size.
- **Overfit one batch**: 100 to 300 steps on a fixed small batch must reach a loss below a threshold; run on CPU in CI.
- **Gradient flow**: after `backward`, every trainable parameter has a finite, non-`None` `.grad`; frozen ones have `None`.
- **`gradcheck`**: for custom `autograd.Function` or custom ops use `torch.autograd.gradcheck(fn, inputs)` with `dtype=torch.double` inputs that have `requires_grad=True` (verified on 2.15).
- **Eval/train parity**: in `eval()` the output must not change between calls with the same input (dropout and batch-norm updates are off).
- **Checkpoint round trip**: save, rebuild from config, `load_state_dict(strict=True)` with `weights_only=True`, and compare outputs with `torch.testing.assert_close`.
- **Determinism**: two runs with the same seed give equal losses over a few steps on the same hardware, when determinism flags are on.
- **Device tests**: parametrise over `cpu` and, when available, `cuda` or `mps`; skip with `pytest.mark.skipif(not torch.cuda.is_available(), ...)`.
- **Distributed smoke test**: `torchrun --nproc_per_node=2` on CPU with `gloo` for one or two steps and a checkpoint save and load.
- **Compile test**: `torch.compile(model, fullgraph=True)` on a small input compared with eager via `assert_close`; catches graph breaks early.
- Use `torch.testing.assert_close(actual, expected, rtol=..., atol=...)` for tensors, not `==`.

## 12. Review Checklist

- [ ] Device and dtype are chosen once; no hard-coded `"cuda"` in modules; tensors created with `device=`.
- [ ] `model.train()` and `model.eval()` set correctly; evaluation under `no_grad` or `inference_mode`.
- [ ] Mixed precision uses `torch.autocast` and `torch.amp.GradScaler`, not the deprecated `torch.cuda.amp` forms; scaler only for fp16; `unscale_` before clipping.
- [ ] Optimizer built after freezing and device placement (and after `fully_shard` for FSDP2); scheduler stepped consistently.
- [ ] Checkpoints store state dicts plus optimizer, scheduler, scaler, RNG and step; loads use `weights_only=True`; writes are atomic.
- [ ] Seeds set; `DistributedSampler.set_epoch` called; `worker_init_fn` or generator seeds worker randomness.
- [ ] No `.item()` or `.cpu()` per step in the hot path; no accumulation of tensors that keep the graph alive (use `.detach()`).
- [ ] DataLoader settings justified (`num_workers`, `pin_memory`, `persistent_workers`); datasets do not hold large Python lists copied into every worker.
- [ ] Distributed code: every rank reaches every collective; only rank 0 writes logs and files; `destroy_process_group` called.
- [ ] Tests cover shapes, overfit-one-batch and checkpoint round trip.
- [ ] No `weights_only=False` on external files, no secrets, no pickled whole modules.

## 13. Production Notes

- Pin the PyTorch build (version and CUDA variant) in the image; match the driver to the wheel (CUDA 13 wheels need driver 580 or newer) and record `torch.__version__` and `torch.version.cuda` in the run metadata.
- Launch multi-GPU jobs with `torchrun` (single node: `--standalone --nproc_per_node=N`); for multi-node use the scheduler's rendezvous settings and a shared, durable checkpoint directory.
- Set `OMP_NUM_THREADS` explicitly per process under `torchrun` to avoid CPU oversubscription, and set the DataLoader worker count against available cores.
- Checkpoint on a time or step interval, keep the last N, and make resume the default path; test resume by killing a job mid-epoch.
- For FSDP2 and large models save with `torch.distributed.checkpoint` (sharded, resharding on load) and export a consolidated `state_dict` separately for inference.
- Set a communication timeout suitable for the slowest step (`init_process_group(timeout=...)`) so a hung rank fails the job instead of blocking forever; the rewritten NCCL backend in 2.15 includes a flight recorder for hang diagnosis (check the distributed docs for its settings).
- After a crash, check the first failing rank's log, not the last: a CUDA out-of-memory on one rank often appears as a timeout on the others.
- For inference, use `model.eval()` with `torch.inference_mode()`, export with `torch.export` or ONNX where the runtime allows, and validate exported outputs against eager within a tolerance.
- Upgrade on a branch: run the tests with warnings visible, compare a short training run's loss curve against the old version, and read the release notes' backward-incompatible and deprecation sections.
- PyTorch Lightning (pytorch-lightning 2.6.6 on PyPI) wraps this loop in `LightningModule` and `Trainer` and handles devices, precision and DDP/FSDP strategies; check its own compatibility table for the supported PyTorch versions.

## 14. Examples

A training loop that runs on CPU, CUDA or MPS with bf16 autocast, gradient accumulation and clipping (the fp16 variant is in [references/training-loop-amp.md](references/training-loop-amp.md)):

```python
import torch
import torch.nn as nn
import torch.nn.functional as F


def pick_device() -> torch.device:
    acc = torch.accelerator.current_accelerator(check_available=True)
    return acc if acc is not None else torch.device("cpu")


class Mlp(nn.Module):
    def __init__(self, d_in: int, d_hidden: int, n_classes: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d_in, d_hidden), nn.GELU(), nn.Linear(d_hidden, n_classes)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:  # (B, d_in) -> (B, C)
        return self.net(x)


def train(steps: int = 50, accum: int = 2, seed: int = 0) -> float:
    torch.manual_seed(seed)
    device = pick_device()
    model = Mlp(16, 32, 4).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-2)
    x = torch.randn(64, 16, device=device)
    y = torch.randint(0, 4, (64,), device=device)
    model.train()
    last = torch.zeros(())
    for step in range(steps):
        for xb, yb in zip(x.chunk(accum), y.chunk(accum), strict=True):
            with torch.autocast(device_type=device.type, dtype=torch.bfloat16):
                loss = F.cross_entropy(model(xb), yb) / accum
            loss.backward()
            last = loss.detach() * accum
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        opt.step()
        opt.zero_grad(set_to_none=True)
    return last.item()


if __name__ == "__main__":
    print(f"final loss {train():.4f}")
```

An overfit-one-batch test and a checkpoint round trip with the safe load default:

```python
import io

import torch
import torch.nn as nn


def test_overfit_one_batch() -> None:
    torch.manual_seed(0)
    model = nn.Sequential(nn.Linear(8, 16), nn.ReLU(), nn.Linear(16, 3))
    x = torch.randn(4, 8)
    y = torch.tensor([0, 1, 2, 1])
    opt = torch.optim.AdamW(model.parameters(), lr=1e-2)
    for _ in range(200):
        opt.zero_grad(set_to_none=True)
        loss = nn.functional.cross_entropy(model(x), y)
        loss.backward()
        opt.step()
    assert loss.item() < 0.05


def test_checkpoint_roundtrip() -> None:
    model = nn.Linear(4, 2)
    buf = io.BytesIO()
    torch.save(model.state_dict(), buf)
    buf.seek(0)
    state = torch.load(buf, weights_only=True, map_location="cpu")
    clone = nn.Linear(4, 2)
    clone.load_state_dict(state, strict=True)
    x = torch.randn(3, 4)
    torch.testing.assert_close(model(x), clone(x))
```

A DDP script launched with `torchrun --nproc_per_node=2 train_ddp.py` (uses gloo on CPU and nccl on CUDA):

```python
import os

import torch
import torch.distributed as dist
import torch.nn as nn
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader, TensorDataset
from torch.utils.data.distributed import DistributedSampler


def main() -> None:
    use_cuda = torch.cuda.is_available()
    local_rank = int(os.environ["LOCAL_RANK"])
    if use_cuda:
        torch.cuda.set_device(local_rank)
    dist.init_process_group("nccl" if use_cuda else "gloo")
    device = torch.device("cuda", local_rank) if use_cuda else torch.device("cpu")

    torch.manual_seed(0)  # same init on every rank
    model = DDP(nn.Linear(10, 2).to(device), device_ids=[local_rank] if use_cuda else None)
    data = TensorDataset(torch.randn(256, 10), torch.randint(0, 2, (256,)))
    sampler = DistributedSampler(data, shuffle=True, seed=0)
    loader = DataLoader(data, batch_size=32, sampler=sampler, drop_last=True)
    opt = torch.optim.SGD(model.parameters(), lr=0.1)

    for epoch in range(2):
        sampler.set_epoch(epoch)
        for xb, yb in loader:
            loss = nn.functional.cross_entropy(model(xb.to(device)), yb.to(device))
            loss.backward()
            opt.step()
            opt.zero_grad(set_to_none=True)
        if dist.get_rank() == 0:
            print(f"epoch {epoch} loss {loss.item():.4f}")
    dist.destroy_process_group()


if __name__ == "__main__":
    main()
```

Allow-listing a custom class for `weights_only=True` loads, only for files you created:

```python
from dataclasses import dataclass

import torch


@dataclass
class Meta:
    epoch: int


torch.save({"meta": Meta(3)}, "meta.pt")
with torch.serialization.safe_globals([Meta]):
    print(torch.load("meta.pt", weights_only=True))
```

## 15. Common Mistakes

- **Forgetting `model.eval()` or `no_grad` at evaluation**: dropout and batch norm stay in training mode and memory grows. Set the mode and wrap in `torch.no_grad()` or `torch.inference_mode()`.
- **Using the deprecated `torch.cuda.amp.GradScaler()` and `torch.cuda.amp.autocast()`**: they warn on 2.15. Use `torch.amp.GradScaler("cuda")` and `torch.autocast("cuda", ...)`.
- **Clipping gradients without `scaler.unscale_(optimizer)` under fp16**: the norm is measured on scaled gradients. Unscale first.
- **Appending `loss` (with graph) to a list**: memory grows every step. Store `loss.item()` or `loss.detach()`.
- **Calling `.item()` on every step**: forces a GPU sync and stalls the pipeline. Log every N steps.
- **Creating the optimizer before `model.to(device)` or before `fully_shard`**: it holds the wrong parameter objects. Build it last.
- **Loading old checkpoints with `torch.load(path)` and hitting `UnpicklingError`**: the default is `weights_only=True`. Re-save as a plain `state_dict`, or allow-list classes with `add_safe_globals`; use `weights_only=False` only for trusted files.
- **Saving `torch.save(model)`**: ties the file to class paths and requires unsafe unpickling. Save `state_dict()` plus a config.
- **Not calling `DistributedSampler.set_epoch(epoch)`**: every epoch sees the same order. Call it each epoch.
- **Seeding NumPy and `random` only in the main process**: DataLoader workers need their own seeds through `worker_init_fn` or a `generator`. See [references/data-loading.md](references/data-loading.md).
- **Data-dependent Python branches inside a compiled function**: each distinct value can add a graph break or a recompile; after `recompile_limit` (8) the function falls back to eager with a warning. Check with `TORCH_LOGS="graph_breaks,recompiles"`.
- **Benchmarking without `torch.cuda.synchronize()` or warm-up**: CUDA calls are asynchronous and the first compiled call includes compile time.
- **Running a DDP step with unused parameters**: raises an error unless `find_unused_parameters=True` is set; fix the model first because the flag adds overhead.
- **Only rank 0 calling a collective** (`dcp.save`, `barrier`, `all_reduce`): the other ranks wait until the timeout. All ranks must call collective operations.
- **`num_workers > 0` with a dataset that holds a large Python list or dict**: reference counts cause copy-on-write growth in every worker. Use NumPy arrays, `torch.Tensor`s or memory-mapped files.
- **Leaving `use_reentrant` unset in `torch.utils.checkpoint.checkpoint`**: it warns; pass `use_reentrant=False`.
- **Setting `reduce_dtype=None` in `MixedPrecisionPolicy` and upgrading to 2.15 without checking**: gradient reduction dtype follows the parameter dtype now. Set it explicitly (usually `torch.float32`).
- **Assuming `torch.use_deterministic_algorithms(True)` is free**: some ops raise a `RuntimeError` and some are slower; use `warn_only=True` while finding offenders. See [references/compile-and-performance.md](references/compile-and-performance.md).

## 16. References

- [references/training-loop-amp.md](references/training-loop-amp.md): device selection, dtype rules, a full training and evaluation loop, bf16 and fp16 autocast with GradScaler, gradient accumulation and clipping, checkpoint save and resume, reproducibility settings.
- [references/data-loading.md](references/data-loading.md): map-style and iterable datasets, DataLoader arguments, worker seeding and sharding, pin_memory and persistent_workers, DistributedSampler, collate functions, input-pipeline debugging.
- [references/compile-and-performance.md](references/compile-and-performance.md): torch.compile modes, graph breaks and recompilation, regional compilation, torch.profiler, memory debugging and snapshots, activation checkpointing, torch.export and ONNX export.
- [references/distributed.md](references/distributed.md): torchrun, process groups, DDP, FSDP2 fully_shard with mixed precision, distributed checkpoint, debugging hangs, launch recipes.
- PyTorch documentation: https://pytorch.org/docs/stable/ and release notes https://github.com/pytorch/pytorch/releases
- Install selector: https://pytorch.org/get-started/locally/
- Serialization notes (`weights_only`, safe globals): https://pytorch.org/docs/stable/notes/serialization.html
- Reproducibility notes: https://pytorch.org/docs/stable/notes/randomness.html
- Distributed: https://pytorch.org/docs/stable/distributed.html and FSDP2 tutorial https://pytorch.org/tutorials/intermediate/FSDP_tutorial.html
- torch.compile: https://pytorch.org/docs/stable/torch.compiler.html
- PyTorch Lightning: https://lightning.ai/docs/pytorch/stable/
