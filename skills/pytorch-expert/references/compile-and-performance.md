# torch.compile, Profiling, Memory and Export

`torch.compile` modes, graph breaks and recompilation, regional compilation, `torch.profiler`, memory debugging, activation checkpointing, and `torch.export` and ONNX export. Signatures and mode names were read from PyTorch 2.15.0; the CPU code blocks were run (2026-10). GPU-only features are marked as unverified here and should be checked against the current docs.

## Contents

1. [Compile basics](#1-compile-basics)
2. [Graph breaks](#2-graph-breaks)
3. [Recompilation and dynamic shapes](#3-recompilation-and-dynamic-shapes)
4. [Benchmarking](#4-benchmarking)
5. [Profiler](#5-profiler)
6. [Memory debugging](#6-memory-debugging)
7. [Activation checkpointing](#7-activation-checkpointing)
8. [Export and ONNX](#8-export-and-onnx)

## 1. Compile basics

Signature on 2.15: `torch.compile(model=None, *, fullgraph=False, dynamic=None, backend=None, mode=None, options=None, name=None, disable=False, recompile_limit=None, isolate_recompiles=False, dynamic_shapes=None)`.

```python
import torch
import torch.nn as nn

model = nn.Sequential(nn.Linear(64, 64), nn.GELU(), nn.Linear(64, 8))
compiled = torch.compile(model)           # default mode, Inductor backend
x = torch.randn(32, 64)
torch.testing.assert_close(compiled(x), model(x))
```

- Compilation happens lazily on the first call (and again when guards fail); expect seconds to minutes on large models.
- Modes reported by `torch._inductor.list_mode_options()` on 2.15: `default`, `reduce-overhead` (enables CUDA graphs), `max-autotune` (kernel search plus CUDA graphs), `max-autotune-no-cudagraphs` and `lite` (a cheaper pass configuration; check the docs for its intent before relying on it). `torch._inductor.list_options()` lists the keys accepted by `options={...}`.
- Backends listed by `torch.compiler.list_backends()` on the CPU build: `cudagraphs`, `inductor`, `openxla`, `tvm`. `backend="eager"` and `"aot_eager"` are useful to separate Dynamo problems from Inductor problems.
- `Module.compile()` compiles in place and keeps the object type and `state_dict` keys. `torch.compile(model)` returns a wrapper whose `state_dict` keys carry an `_orig_mod.` prefix; save the uncompiled module's `state_dict`.
- Inductor on CPU needs a C++ compiler; on CUDA it generates Triton kernels (the Linux CUDA wheels depend on `triton`).
- Regional compilation: compile the repeated block instead of the whole model so one compiled artifact is reused across layers.

```python
for block in model.blocks:   # same class, same shapes
    block.compile()
```

- Training with `torch.compile` works with autocast, `GradScaler` and DDP; with FSDP2 apply `fully_shard` and compile in the order shown in the current FSDP2 tutorial (check the docs for ordering advice).
- `torch.compiler.disable` on a function (decorator) excludes it from tracing; `torch.compiler.set_stance(...)` switches compile behaviour at runtime (check the docs for stance names).
- `torch.compiler.precompile` became a module in 2.15 (`capture` and `load` replace the old callable); older snippets that call it directly break.
- The on-disk Inductor cache is reused across processes; CI and containers should persist it or accept cold compiles. Check the docs for `TORCHINDUCTOR_CACHE_DIR`.

## 2. Graph breaks

A graph break splits the function into several compiled graphs separated by eager Python. Each break costs speed and blocks fusion.

```python
import torch
import torch._dynamo as dynamo


def f(x):
    if x.sum() > 0:          # data-dependent branch
        return x + 1
    return x - 1


report = dynamo.explain(f)(torch.randn(3))
print(report.graph_break_count)
print(report.break_reasons[0].reason)

try:
    torch.compile(f, fullgraph=True)(torch.randn(3))   # breaks become errors
except Exception as e:
    print(type(e).__name__)
```

- `fullgraph=True` raises on the first break; use it in tests for the hot path (checked: the example raises an "Unsupported: Data-dependent branching" error).
- `TORCH_LOGS="graph_breaks"` prints each break with a user stack; `TORCH_LOGS="graph_breaks,recompiles"` adds recompilation reasons. `TORCH_LOGS="+dynamo"` is more verbose.
- Typical causes: data-dependent Python `if` on tensor values, `.item()`, `print` of tensors, unsupported third-party calls, iterating over a tensor, in-place mutation of Python globals.
- Fixes: replace branches with `torch.where` or `torch.cond`; keep scalars as Python numbers computed outside the compiled region; move logging out of the compiled function; wrap unavoidable calls with `@torch.compiler.disable` (the function then runs eagerly while the rest stays compiled).
- Compile only the model forward and loss, not the whole training loop with data loading and logging.

## 3. Recompilation and dynamic shapes

- Dynamo guards on shapes, dtypes, devices, `requires_grad`, module training flags and Python values it read. A guard failure triggers a recompile.
- Default `torch._dynamo.config.recompile_limit` is 8 on 2.15 (the `accumulated_recompile_limit` default is 256). When the limit is hit, the function falls back to eager with a warning, which silently loses the speed-up. `torch.compile(..., recompile_limit=N)` sets it per call.
- On the second distinct shape Dynamo normally marks that dimension dynamic and recompiles once; verified on 2.15 with batch sizes 2 then 3 (one recompile logged, size mismatch guard).
- Control it: `dynamic=False` pins static shapes (one graph per shape, best kernels), `dynamic=True` compiles symbolic shapes up front, `torch._dynamo.mark_dynamic(tensor, dim)` marks one dimension, and `torch._dynamo.maybe_mark_dynamic` does so without erroring on specialisation.
- Prefer a few padded bucket sizes (for example sequence lengths 128, 256, 512) to unbounded variety.
- Train/eval switches change guards; call `model.eval()` before the first compiled eval call and expect one recompile per mode.
- A changing Python scalar passed as an argument (a step counter, a float learning rate) is guarded on its value; pass such values as tensors.
- `torch._dynamo.reset()` or `torch.compiler.reset()` clears compiled state in tests and notebooks.

## 4. Benchmarking

```python
import time

import torch


def bench(fn, *args, warmup: int = 3, iters: int = 20) -> float:
    for _ in range(warmup):
        fn(*args)
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    t0 = time.perf_counter()
    for _ in range(iters):
        fn(*args)
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    return (time.perf_counter() - t0) / iters
```

- Warm up past compilation and autotuning; CUDA kernels launch asynchronously, so synchronise before reading the clock.
- Compare eager, `default` and one other mode on the real batch shapes; keep the fastest that is stable. `torch.utils.benchmark.Timer` handles warm-up and synchronisation for micro-benchmarks.
- Report time per step, samples per second and peak memory (`torch.cuda.max_memory_allocated()`), not just one number.

## 5. Profiler

```python
import torch
import torch.nn as nn
from torch.profiler import ProfilerActivity, profile, record_function, schedule

model = nn.Sequential(nn.Linear(256, 256), nn.ReLU(), nn.Linear(256, 10))
x = torch.randn(64, 256)
activities = [ProfilerActivity.CPU]
if torch.cuda.is_available():
    activities.append(ProfilerActivity.CUDA)

with profile(
    activities=activities,
    schedule=schedule(wait=1, warmup=1, active=2, repeat=1),
    record_shapes=True,
    profile_memory=True,
    on_trace_ready=torch.profiler.tensorboard_trace_handler("./prof"),
) as prof:
    for _ in range(4):
        with record_function("forward"):
            model(x).sum().backward()
        prof.step()

print(prof.key_averages().table(sort_by="cpu_time_total", row_limit=5))
```

- `schedule(wait, warmup, active, repeat, skip_first)` are keyword-only on 2.15; call `prof.step()` once per iteration.
- Open traces in TensorBoard with the profiler plugin or in Perfetto/`chrome://tracing`; `prof.export_chrome_trace("trace.json")` writes one directly.
- On CUDA, sort by `cuda_time_total` or `self_cuda_time_total`; the exact column names vary with version, so print the table once and read the header.
- Look for: gaps between kernels (CPU-bound launch or data loading), many tiny kernels (fusion opportunity, try compile), `cudaMemcpy` host-to-device in the loop, `aten::item` or `cudaStreamSynchronize` (hidden syncs), and a long `DataLoader` wait in the first lines of each step.
- `with_stack=True` adds Python stacks at some overhead; use it for a short run to find the source line of an expensive op.
- Profile steady state (after warm-up and compilation), with the real batch size, for a handful of steps.
- 2.15 deprecates `torch.autograd.profiler.load_nvprof` and related functions (removal planned for 2.17); do not build new tooling on them.

## 6. Memory debugging

- Counters: `torch.cuda.memory_allocated()`, `torch.cuda.max_memory_allocated()`, `torch.cuda.memory_reserved()` and `torch.cuda.memory_summary()`. Reset the peak with `torch.cuda.reset_peak_memory_stats()` between phases.
- "CUDA out of memory" message fields: tried to allocate, already allocated by PyTorch, reserved but unallocated. A large reserved-but-unallocated figure indicates fragmentation; try the allocator option `expandable_segments:True` through `PYTORCH_CUDA_ALLOC_CONF` (check the current docs for the variable name and options).
- Allocator history and snapshot (both functions exist in 2.15, used on a CUDA run):

```python
import torch

torch.cuda.memory._record_memory_history(max_entries=100_000)
# ... run a few training steps ...
torch.cuda.memory._dump_snapshot("snapshot.pickle")
torch.cuda.memory._record_memory_history(enabled=None)  # stop recording
```

  Load the file in the memory visualiser at https://pytorch.org/memory_viz to see which allocations dominate at the peak, with stacks. Treat snapshot files as pickles from your own job; do not open files from others in unsafe tools.
- Usual contributors, in order: activations (batch size and sequence length), optimizer state (Adam keeps two extra copies of the parameters), gradients, parameters, and the CUDA context and cache.
- Levers: smaller micro-batch with accumulation; bf16 or fp16 autocast; activation checkpointing; FSDP2 sharding; 8-bit or paged optimizers from external libraries; offloading as a last resort (`CPUOffloadPolicy` for FSDP2).
- Memory leaks in a loop come from keeping graph-attached tensors (`losses.append(loss)`), reusing a tensor across steps with history, or holding references in logs; use `.detach()` or `.item()`.
- `del` plus `torch.cuda.empty_cache()` returns cached blocks to the driver but does not lower the peak; use it between phases (train to eval), not every step.
- Inference: `torch.inference_mode()` and `model.eval()` avoid storing activations; use half precision and a KV-cache-aware design for sequence models.

## 7. Activation checkpointing

```python
import torch
from torch.utils.checkpoint import checkpoint


class CheckpointedStack(torch.nn.Module):
    def __init__(self, blocks: torch.nn.ModuleList) -> None:
        super().__init__()
        self.blocks = blocks

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        for b in self.blocks:
            x = checkpoint(b, x, use_reentrant=False)
        return x
```

- Trades compute (roughly one extra forward per checkpointed region) for activation memory.
- Always pass `use_reentrant` explicitly; `False` is the variant that supports more features (keyword arguments, nested use, `torch.autograd.grad`). The function signature on 2.15 also accepts `preserve_rng_state`, `context_fn` (selective checkpointing) and `determinism_check`.
- Checkpoint units should be large enough to matter (a transformer block) and deterministic; dropout is handled by RNG state preservation (`preserve_rng_state=True`).
- 2.15 notes: selective checkpointing now saves outputs of ordered-effect ops unless the policy returns `MUST_RECOMPUTE`; review custom policies when upgrading.
- With FSDP2 apply checkpointing to the block before `fully_shard`.

## 8. Export and ONNX

```python
import torch
import torch.nn as nn

model = nn.Sequential(nn.Linear(8, 4), nn.ReLU()).eval()
example = (torch.randn(2, 8),)
batch = torch.export.Dim("batch", min=1, max=128)

ep = torch.export.export(model, example, dynamic_shapes=({0: batch},))
print(ep.module()(torch.randn(7, 8)).shape)    # torch.Size([7, 4])

onnx_program = torch.onnx.export(model, example, dynamic_shapes=({0: batch},))
onnx_program.save("model.onnx")                # needs onnx and onnxscript installed
```

- `torch.export.export(mod, args, kwargs=None, *, dynamic_shapes=None, strict=False, ...)` returns an `ExportedProgram`; `ep.module()` gives a callable `nn.Module`, `ep.graph` the ATen graph. Export captures a full graph, so data-dependent control flow must be rewritten (`torch.cond`, `torch.where`) or constrained.
- `dynamic_shapes` takes a tuple matching the positional arguments, each a dict from dimension index to a `Dim`.
- `torch.onnx.export` defaults to `dynamo=True` on 2.15 and returns an `ONNXProgram`; pass `dynamo=False` only to reach the legacy exporter (with `dynamic_axes`, `opset_version`). Verified: export plus `onnxruntime` inference on CPU gave the expected output shape for a batch of 5 with a dynamic batch dimension (onnx 1.23.2, onnxscript 0.7.2, onnxruntime 1.31.1).
- Validate every export: run the exported model on random inputs of several batch sizes and compare with eager using `torch.testing.assert_close` or `numpy.testing.assert_allclose` with a tolerance suited to the dtype.
- Set `model.eval()` before export and export in float32 unless the target runtime supports lower precision.
- TorchScript (`torch.jit.script` and `trace`) is the older path; prefer `torch.export` for new work and check the docs for the status of TorchScript before adopting it.
- 2.15 fixes: export of `x[mask] = scalar` with data-dependent size and hardcoded LSTM or GRU output lengths under dynamic shapes in the ONNX exporter; upgrade before working around these.
