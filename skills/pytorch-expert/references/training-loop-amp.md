# Training Loop, Mixed Precision and Checkpoints

Devices and dtypes, a complete training and evaluation loop, bf16 and fp16 autocast with `torch.amp.GradScaler`, gradient accumulation and clipping, checkpoint save and resume, and reproducibility settings. Checked on PyTorch 2.15.0 (CPU runs, API signatures inspected, 2026-10).

## Contents

1. [Devices and dtypes](#1-devices-and-dtypes)
2. [Module design](#2-module-design)
3. [Autocast and GradScaler](#3-autocast-and-gradscaler)
4. [A complete loop](#4-a-complete-loop)
5. [Checkpoints and resume](#5-checkpoints-and-resume)
6. [Reproducibility](#6-reproducibility)
7. [Autograd notes](#7-autograd-notes)

## 1. Devices and dtypes

- Pick the device once: `torch.accelerator.current_accelerator(check_available=True)` returns a `torch.device` or `None`. Without `check_available=True` it reports the compiled-in accelerator even if no driver is present.
- Backend checks: `torch.cuda.is_available()`, `torch.backends.mps.is_available()`. MPS needs macOS 15 or newer for 2.15; some operators and dtypes (for example float64) are unsupported on MPS, so keep a CPU fallback path and check the MPS notes.
- Default dtype is `torch.float32`; integer labels for cross-entropy are `torch.long`. Type promotion rules apply between tensors (`int` + `float` gives float), and mixed devices raise `RuntimeError`.
- bf16 has fp32's exponent range with fewer mantissa bits, so it rarely overflows; fp16 has a narrow range and needs loss scaling.
- `torch.set_float32_matmul_precision("high")` allows TF32 or similar faster fp32 matmuls on supporting GPUs; the default is `"highest"` (checked on 2.15).
- Move data with `.to(device, non_blocking=True)`; `non_blocking` only overlaps copies when the source is pinned memory (see data-loading.md).

## 2. Module design

```python
import torch
import torch.nn as nn


class Block(nn.Module):
    def __init__(self, dim: int, hidden: int, p: float = 0.1) -> None:
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.ff = nn.Sequential(nn.Linear(dim, hidden), nn.GELU(), nn.Linear(hidden, dim))
        self.drop = nn.Dropout(p)
        self.register_buffer("scale", torch.tensor(1.0), persistent=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:  # (B, T, dim)
        return x + self.drop(self.ff(self.norm(x))) * self.scale


class Net(nn.Module):
    def __init__(self, dim: int = 64, depth: int = 4, n_classes: int = 10) -> None:
        super().__init__()
        self.blocks = nn.ModuleList(Block(dim, 4 * dim) for _ in range(depth))
        self.head = nn.Linear(dim, n_classes)
        self.apply(self._init)

    @staticmethod
    def _init(m: nn.Module) -> None:
        if isinstance(m, nn.Linear):
            nn.init.xavier_uniform_(m.weight)
            nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        for b in self.blocks:
            x = b(x)
        return self.head(x.mean(dim=1))
```

- A tensor attribute that is neither a `Parameter` nor a registered buffer is not moved by `.to()` and not saved; use `register_buffer` (`persistent=False` keeps it out of the `state_dict`).
- `load_state_dict(state, strict=True)` reports missing and unexpected keys; keep `strict=True` except for deliberate partial loads, and log the result of `strict=False`.
- `load_state_dict(state, assign=True)` is used when the module was created on the `meta` device.
- Separate weight decay groups (no decay on biases and norm weights) are passed to the optimizer as a list of dicts: `[{"params": decay, "weight_decay": 0.1}, {"params": no_decay, "weight_decay": 0.0}]`. Passing a bare `set` of parameters emits a `FutureWarning` on 2.15.

## 3. Autocast and GradScaler

Current API names (checked on 2.15): `torch.autocast(device_type, dtype=None, enabled=True, cache_enabled=None)` and `torch.amp.GradScaler(device="cuda", init_scale=65536.0, growth_factor=2.0, backoff_factor=0.5, growth_interval=2000, enabled=True)`. The old `torch.cuda.amp.GradScaler()` and `torch.cuda.amp.autocast()` still work but emit a deprecation warning.

- Wrap only the forward pass and the loss in `autocast`; run `backward` outside it.
- bf16: `torch.autocast("cuda", dtype=torch.bfloat16)`; no scaler. Also valid on `"cpu"`.
- fp16: `torch.autocast("cuda", dtype=torch.float16)` plus `torch.amp.GradScaler("cuda")`.
- The scaler order is `scaler.scale(loss).backward()`, optionally `scaler.unscale_(opt)` then clipping, `scaler.step(opt)`, `scaler.update()`.
- `scaler.step` skips the optimizer step when gradients contain inf or NaN; the scale then halves. A scale that keeps collapsing points to a real instability (learning rate, bad data, a custom op in fp16).
- `scaler.get_scale()` is a useful metric. The scaler state is saved with `scaler.state_dict()`.
- Autocast chooses per-op dtypes (matmuls and convolutions in low precision, reductions and losses in fp32). Parameters stay fp32; autocast casts on the fly and caches casts inside the context.

```python
import torch

use_amp = torch.cuda.is_available()
scaler = torch.amp.GradScaler("cuda", enabled=use_amp)  # no-op when disabled

with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=use_amp):
    out = model(x)
    loss = criterion(out, y)
scaler.scale(loss).backward()
scaler.unscale_(optimizer)
torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
scaler.step(optimizer)
scaler.update()
optimizer.zero_grad(set_to_none=True)
```

## 4. A complete loop

```python
import time
from collections.abc import Iterable

import torch
import torch.nn as nn


def train_one_epoch(
    model: nn.Module,
    loader: Iterable[tuple[torch.Tensor, torch.Tensor]],
    optimizer: torch.optim.Optimizer,
    scheduler: torch.optim.lr_scheduler.LRScheduler | None,
    scaler: torch.amp.GradScaler | None,
    device: torch.device,
    amp_dtype: torch.dtype | None,
    accum_steps: int = 1,
    max_norm: float = 1.0,
    log_every: int = 50,
) -> float:
    model.train()
    criterion = nn.CrossEntropyLoss()
    total = torch.zeros((), device=device)
    n = 0
    t0 = time.perf_counter()
    for i, (x, y) in enumerate(loader):
        x = x.to(device, non_blocking=True)
        y = y.to(device, non_blocking=True)
        with torch.autocast(device.type, dtype=amp_dtype, enabled=amp_dtype is not None):
            loss = criterion(model(x), y) / accum_steps
        if scaler is not None:
            scaler.scale(loss).backward()
        else:
            loss.backward()
        total += loss.detach() * accum_steps
        n += 1
        if (i + 1) % accum_steps == 0:
            if scaler is not None:
                scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm)
            if scaler is not None:
                scaler.step(optimizer)
                scaler.update()
            else:
                optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            if scheduler is not None:
                scheduler.step()
        if (i + 1) % log_every == 0:
            print(f"step {i + 1} loss {(total / n).item():.4f} {time.perf_counter() - t0:.1f}s")
    return (total / max(n, 1)).item()


@torch.inference_mode()
def evaluate(model: nn.Module, loader, device: torch.device) -> float:
    model.eval()
    correct = torch.zeros((), device=device)
    count = 0
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        correct += (model(x).argmax(dim=-1) == y).sum()
        count += y.numel()
    return (correct / max(count, 1)).item()
```

- `loss / accum_steps` keeps the effective gradient equal to the large-batch gradient. Under DDP, wrap the non-final micro-batches in `with model.no_sync():`; under FSDP2 use `model.set_requires_gradient_sync(False)` for those steps and `True` on the last.
- The running total stays on the device and is read with `.item()` only when logging.
- `scheduler.step()` is called once per optimizer step here; for epoch-based schedulers call it once per epoch. `OneCycleLR(optimizer, max_lr, total_steps=...)` must be stepped per optimizer step.
- For fp16 pass `scaler=torch.amp.GradScaler("cuda")` and `amp_dtype=torch.float16`; for bf16 pass `scaler=None`, `amp_dtype=torch.bfloat16`; for full fp32 pass `amp_dtype=None`.
- Stop on non-finite loss early during development: `if not torch.isfinite(loss): raise FloatingPointError(...)` checked every N steps, or `torch.autograd.set_detect_anomaly(True)` for a short debug run only (it is slow).

## 5. Checkpoints and resume

```python
import os
import random
from pathlib import Path

import numpy as np
import torch


def save_checkpoint(path: Path, model, optimizer, scheduler, scaler, epoch: int, step: int) -> None:
    state = {
        "model": model.state_dict(),
        "optimizer": optimizer.state_dict(),
        "scheduler": scheduler.state_dict() if scheduler else None,
        "scaler": scaler.state_dict() if scaler else None,
        "epoch": epoch,
        "step": step,
        "rng": {
            "python": random.getstate(),
            "numpy": np.random.get_state(),
            "torch": torch.get_rng_state(),
            "cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None,
        },
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    torch.save(state, tmp)
    os.replace(tmp, path)  # atomic on the same filesystem


def load_checkpoint(path: Path, model, optimizer, scheduler=None, scaler=None, device="cpu"):
    state = torch.load(path, map_location=device, weights_only=False)  # own file only
    model.load_state_dict(state["model"], strict=True)
    optimizer.load_state_dict(state["optimizer"])
    if scheduler and state["scheduler"]:
        scheduler.load_state_dict(state["scheduler"])
    if scaler and state["scaler"]:
        scaler.load_state_dict(state["scaler"])
    return state["epoch"], state["step"]
```

- The RNG entry holds NumPy and Python objects, so loading it needs `weights_only=False` or allow-listing every type involved. Restrict that to checkpoints your own job wrote. For model-only files shared with others, save just `model.state_dict()` and load with the default `weights_only=True`.
- To keep `weights_only=True` for resume files, store RNG states as tensors or lists and convert on load, and keep other fields to primitives and tensors.
- Saving a `DataParallel` or DDP-wrapped model gives keys prefixed `module.`; save `model.module.state_dict()` or strip the prefix on load.
- A compiled model (`torch.compile(model)`) wraps the original in `_orig_mod`; save the original module's `state_dict()` (keep a reference to the uncompiled `model`).
- Sharded and FSDP2 checkpoints use `torch.distributed.checkpoint`; see distributed.md. The 2.15 notes list a checkpoint compatibility break between 2.15 and older versions under Distributed; test cross-version loads.

## 6. Reproducibility

```python
import os
import random

import numpy as np
import torch


def seed_everything(seed: int, deterministic: bool = False) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)  # seeds CPU and all CUDA devices
    if deterministic:
        os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
        torch.use_deterministic_algorithms(True, warn_only=True)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
```

- `torch.use_deterministic_algorithms(mode, *, warn_only=False)` makes operators use deterministic algorithms or raise `RuntimeError` when none exists. `warn_only=True` turns the error into a warning so offenders can be listed.
- `CUBLAS_WORKSPACE_CONFIG=:4096:8` (or `:16:8`) must be set before the first CUDA matmul for deterministic cuBLAS; set it in the launcher environment when possible.
- `torch.backends.cudnn.benchmark=True` picks the fastest convolution algorithm per input shape and is not deterministic; leave it on for speed when shapes are fixed and exact reproducibility is not required.
- Results can differ across GPU models, PyTorch versions and CUDA versions even with every flag set; record versions with the run.
- DataLoader workers need their own seeding and a seeded generator for shuffling: see data-loading.md.
- Under DDP seed the model init identically on every rank (or broadcast from rank 0) and give data augmentation a rank-dependent seed (`seed + rank`).

## 7. Autograd notes

- `x.detach()` shares storage and stops gradients; `with torch.no_grad()` stops recording; `torch.inference_mode()` is stricter and faster, and its tensors cannot be used in later autograd.
- Gradients accumulate into `.grad` until zeroed; `zero_grad(set_to_none=True)` frees them and saves memory bandwidth.
- Custom ops: subclass `torch.autograd.Function` with `forward` and `backward`, and verify with `torch.autograd.gradcheck` in float64.
- "RuntimeError: one of the variables needed for gradient computation has been modified by an inplace operation" means an in-place op overwrote a saved value; replace it with an out-of-place op or clone.
