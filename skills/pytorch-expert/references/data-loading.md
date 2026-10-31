# Data Loading

`Dataset` and `DataLoader` design for PyTorch 2.x: map-style and iterable datasets, DataLoader arguments, worker seeding and sharding, pinned memory, distributed sampling, collate functions and input-pipeline debugging. Argument names were read from the 2.15.0 signature and code blocks were run on CPU (2026-10).

## Contents

1. [Dataset types](#1-dataset-types)
2. [DataLoader arguments](#2-dataloader-arguments)
3. [Worker seeding and sharding](#3-worker-seeding-and-sharding)
4. [Pinned memory and transfers](#4-pinned-memory-and-transfers)
5. [Distributed sampling](#5-distributed-sampling)
6. [Collate functions and padding](#6-collate-functions-and-padding)
7. [Memory and speed problems](#7-memory-and-speed-problems)
8. [Debugging checklist](#8-debugging-checklist)

## 1. Dataset types

- Map-style: implement `__len__` and `__getitem__`; supports shuffling and `DistributedSampler`. Use it whenever items are addressable by index.
- Iterable-style: subclass `IterableDataset` and implement `__iter__`; for streams, sharded files and data that cannot be indexed. Shuffling is the dataset's job (a shuffle buffer), and the length may be unknown.
- Keep `__getitem__` free of global mutable state; it runs in worker processes.
- Open file handles, database connections and memory maps lazily on first use inside the worker, not in `__init__`; handles created in the parent do not survive pickling or forking safely.
- Return tensors or NumPy arrays with a fixed dtype (`torch.float32` images, `torch.long` labels) so collation is cheap.
- Do the cheap, deterministic preprocessing once offline (decode, resize, tokenise) and store the result; leave only random augmentation in `__getitem__`.

```python
import numpy as np
import torch
from torch.utils.data import Dataset


class ArrayDataset(Dataset):
    """Memory-mapped features; the file is opened lazily inside each worker."""

    def __init__(self, features_path: str, labels: np.ndarray) -> None:
        self.features_path = features_path
        self.labels = labels.astype(np.int64)
        self._x: np.ndarray | None = None

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, i: int) -> tuple[torch.Tensor, torch.Tensor]:
        if self._x is None:
            self._x = np.load(self.features_path, mmap_mode="r")
        x = torch.from_numpy(np.array(self._x[i], dtype=np.float32))
        return x, torch.tensor(self.labels[i])
```

## 2. DataLoader arguments

Signature on 2.15: `DataLoader(dataset, batch_size=1, shuffle=None, sampler=None, batch_sampler=None, num_workers=0, collate_fn=None, pin_memory=False, drop_last=False, timeout=0, worker_init_fn=None, multiprocessing_context=None, generator=None, *, prefetch_factor=None, persistent_workers=False, pin_memory_device="", in_order=True)`.

| Argument | Guidance |
|---|---|
| `num_workers` | 0 loads in the main process (good for debugging). Start with 2 to 4 per GPU and measure; more workers cost memory and CPU. `os.sched_getaffinity(0)` gives the usable core count on Linux |
| `pin_memory` | `True` when batches go to a CUDA device; allocates page-locked host buffers so `.to(device, non_blocking=True)` can overlap with compute |
| `persistent_workers` | `True` keeps workers alive between epochs; requires `num_workers > 0`; saves start-up time per epoch, but workers keep their memory |
| `prefetch_factor` | Batches prefetched per worker (default 2 when workers > 0); only valid with `num_workers > 0`. Raise for bursty storage |
| `shuffle` | Mutually exclusive with `sampler` and with `batch_sampler`. Use `shuffle=True` for single-process training; use a `DistributedSampler` under DDP |
| `drop_last` | `True` for training under DDP and with `torch.compile` so every batch has the same shape; `False` for evaluation so no sample is skipped |
| `generator` | A `torch.Generator` that drives shuffling and the base seed for workers; set it for reproducible order |
| `worker_init_fn` | Called in each worker with the worker id; use it to seed NumPy and `random` and to shard iterable datasets |
| `multiprocessing_context` | `"fork"`, `"spawn"` or `"forkserver"`. Spawn-based starts require picklable datasets and an `if __name__ == "__main__":` guard in scripts |
| `in_order` | Present on 2.15 (default `True`); `False` lets batches arrive out of order for throughput. Check the docs before using it, since it affects reproducibility |
| `timeout` | Seconds to wait for a batch from workers (0 disables); a positive value turns a stuck worker into an error |

- Worker processes receive a copy of the dataset object. Large Python lists and dicts inside it suffer copy-on-write growth because reference counts change on access; store big tables as NumPy arrays, tensors, Arrow or memory-mapped files.
- Datasets that wrap a model or a CUDA tensor do not belong in workers; keep GPU work in the main process.
- Exceptions in a worker are re-raised in the main process with the worker's traceback.
- `len(loader)` is the number of batches; for iterable datasets it may not exist.

## 3. Worker seeding and sharding

PyTorch gives each worker a different base seed derived from the loader's base seed and the worker id, seeds `torch` in that worker, and exposes it through `torch.initial_seed()`. NumPy's global RNG and third-party augmentation libraries should be seeded explicitly so workers do not repeat each other's random draws across forks.

```python
import random

import numpy as np
import torch
from torch.utils.data import DataLoader, IterableDataset, get_worker_info


def seed_worker(worker_id: int) -> None:
    seed = torch.initial_seed() % 2**32
    np.random.seed(seed)
    random.seed(seed)


class ShardedRange(IterableDataset):
    """Each worker yields a disjoint slice of 0..n-1."""

    def __init__(self, n: int) -> None:
        self.n = n

    def __iter__(self):
        info = get_worker_info()
        if info is None:
            ids, num = 0, 1
        else:
            ids, num = info.id, info.num_workers
        yield from range(ids, self.n, num)


g = torch.Generator()
g.manual_seed(1234)
loader = DataLoader(
    ShardedRange(10),
    batch_size=2,
    num_workers=2,
    worker_init_fn=seed_worker,
    generator=g,
    persistent_workers=True,
)
if __name__ == "__main__":
    print(sorted(int(v) for b in loader for v in b))
```

- Without sharding by `get_worker_info()`, every worker of an `IterableDataset` yields the full stream and each sample appears `num_workers` times.
- Under DDP shard iterable data twice: first by rank, then by worker (`global_id = rank * num_workers + worker_id`, stride `world_size * num_workers`).
- A seeded `generator` makes the shuffle order and worker base seeds repeatable.
- For exact resume mid-epoch, record the epoch and batch index and rebuild the sampler order from `seed + epoch`; the standard loader has no state to save (check `torchdata` for stateful loaders if needed).
- Check seeding empirically: iterate two epochs with 2 workers and verify that augmentation values differ between workers and between epochs as intended.

## 4. Pinned memory and transfers

```python
for x, y in loader:  # loader built with pin_memory=True
    x = x.to(device, non_blocking=True)
    y = y.to(device, non_blocking=True)
    ...
```

- `non_blocking=True` overlaps a host-to-device copy with GPU work only when the source tensor is in pinned memory. Pinning every batch costs host RAM and some CPU time; verify with the profiler.
- The pin thread works on batches returned by `collate_fn`; custom batch types need a `pin_memory()` method to be pinned (a tuple, list or dict of tensors works by default).
- Do transfers in the training loop, not in `collate_fn` or `__getitem__`; workers must not touch CUDA.
- Keep batches as uint8 on the host and convert and normalise on the device when image decoding is the bottleneck; transfers are four times smaller than float32.
- On MPS and CPU `pin_memory` has no benefit; leave it `False` there (the loader warns when no accelerator is present).

## 5. Distributed sampling

```python
from torch.utils.data import DataLoader
from torch.utils.data.distributed import DistributedSampler

sampler = DistributedSampler(dataset, shuffle=True, seed=0, drop_last=True)
loader = DataLoader(dataset, batch_size=32, sampler=sampler, num_workers=4, pin_memory=True)
for epoch in range(num_epochs):
    sampler.set_epoch(epoch)  # re-seeds the shuffle; omit and every epoch has the same order
    for batch in loader:
        ...
```

- `DistributedSampler` defaults to `num_replicas` and `rank` from the initialised process group, so create it after `init_process_group`.
- Without `drop_last=True` the sampler pads by repeating samples so every rank gets the same count; for evaluation metrics, de-duplicate or compute metrics with `all_reduce` over counts, because padded duplicates bias the result.
- `batch_size` is per process; the global batch is `batch_size * world_size * accum_steps`. Adjust the learning rate deliberately when the global batch changes.
- Evaluation on rank 0 only wastes the other GPUs; shard the validation set the same way and reduce the metric sums.

## 6. Collate functions and padding

```python
import torch
from torch.nn.utils.rnn import pad_sequence


def collate_pad(batch: list[tuple[torch.Tensor, int]]):
    seqs, labels = zip(*batch, strict=True)
    lengths = torch.tensor([s.size(0) for s in seqs])
    x = pad_sequence(seqs, batch_first=True, padding_value=0)  # (B, T_max, ...)
    mask = torch.arange(x.size(1))[None, :] < lengths[:, None]  # (B, T_max) bool
    return x, mask, torch.tensor(labels)
```

- The default collate stacks tensors and converts numbers, dicts and sequences recursively; variable-length items need a custom `collate_fn`.
- Always return a padding mask or lengths and apply it in attention and in the loss (`ignore_index` for cross-entropy).
- Bucket by length (a `batch_sampler` that groups similar lengths) to cut padding waste; shuffle the buckets, not the items inside.
- `collate_fn` runs in workers; it must be picklable under spawn (module-level function, not a lambda).
- Fixed-shape batches matter for `torch.compile` and CUDA graphs: pad to a few bucket sizes instead of the exact maximum per batch.

## 7. Memory and speed problems

- Host RAM grows with workers: each worker holds its own dataset copy plus `prefetch_factor` batches. Reduce workers, shrink the prefetch, or move the data to a shared memory-mapped file.
- "DataLoader worker exited unexpectedly" or a bus error in a container is often shared memory exhaustion (`/dev/shm`); increase the shm size of the container or lower the worker count.
- A slow first batch with `persistent_workers=False` repeats each epoch; enable persistent workers.
- Slow start with `spawn` comes from re-importing modules and pickling the dataset; keep the dataset object small and load heavy data lazily.
- Image decoding in Python (PIL) often caps throughput; options are more workers, smaller stored images, or decoding on the GPU with the vision libraries (check torchvision's docs for the current decoder API).
- Network or object-store reads: cache shards on local disk and read them sequentially instead of random single-file reads.
- Profile the pipeline by iterating the loader alone for 100 batches and timing it; if that is slower than a training step, the loader is the bottleneck.

## 8. Debugging checklist

1. Set `num_workers=0` and reproduce; most dataset bugs show with a clear traceback there.
2. Print one batch: shapes, dtypes, min and max, label histogram, NaN check (`torch.isfinite(x).all()`).
3. Visualise a few samples after augmentation; wrong normalisation or channel order is common.
4. Check that train and validation use the same preprocessing, apart from augmentation.
5. Check label leakage and split overlap by IDs, not by position.
6. Time `next(iter(loader))` and a full pass separately from the model.
7. With workers, confirm that two workers do not return identical augmentations (seed test in section 3) and that an iterable dataset does not duplicate samples.
8. Under DDP, confirm every rank sees a different shard and that `set_epoch` is called.
