# Distributed Training

Launching with `torchrun`, process groups, DDP, FSDP2 (`fully_shard`) with mixed precision, distributed checkpoints, and hang debugging. Imports and signatures were read from PyTorch 2.15.0, and the FSDP2 and DDP scripts below were run with two CPU processes on the `gloo` backend (2026-10). NCCL and multi-node behaviour was not run here.

## Contents

1. [Launching with torchrun](#1-launching-with-torchrun)
2. [Process group basics](#2-process-group-basics)
3. [DDP](#3-ddp)
4. [FSDP2 fully shard](#4-fsdp2-fully-shard)
5. [Distributed checkpoints](#5-distributed-checkpoints)
6. [Debugging hangs and errors](#6-debugging-hangs-and-errors)
7. [Launch recipes](#7-launch-recipes)

## 1. Launching with torchrun

- `torchrun` starts one process per device and sets `RANK`, `LOCAL_RANK`, `WORLD_SIZE`, `MASTER_ADDR` and `MASTER_PORT` for each. Do not hand-roll `mp.spawn` for new code.
- Flags on 2.15 (from `torchrun --help`): `--nnodes`, `--nproc-per-node`, `--standalone`, `--rdzv-backend`, `--rdzv-endpoint`, `--rdzv-id`, `--rdzv-conf`, `--max-restarts`, `--node-rank`, `--master-addr`, `--master-port`, `--log-dir`, `--local-ranks-filter`.
- Single node: `torchrun --standalone --nproc_per_node=4 train.py --config configs/base.yaml`.
- Multi node with the c10d rendezvous: run the same command on every node, for example `torchrun --nnodes=2 --nproc_per_node=8 --rdzv-backend=c10d --rdzv-endpoint=HEAD_HOST:29500 --rdzv-id=job1 train.py`.
- `--max-restarts=N` restarts the worker group after a failure; combine with checkpoint resume so a restart continues instead of starting over.
- Read `LOCAL_RANK` from the environment, not from a command-line argument.
- Under `torchrun`, `OMP_NUM_THREADS` defaults to 1 per process when unset (a warning says so); tune it with the core count per rank.
- Treat the rendezvous endpoint as unauthenticated: use a private network and do not expose the port.
- For SLURM, `srun` can launch `torchrun` once per node, or processes directly with environment variables mapped from `SLURM_PROCID` and `SLURM_LOCALID`; follow your cluster's recipe.

## 2. Process group basics

```python
import os

import torch
import torch.distributed as dist


def setup() -> tuple[int, int, torch.device]:
    use_cuda = torch.cuda.is_available()
    local_rank = int(os.environ["LOCAL_RANK"])
    if use_cuda:
        torch.cuda.set_device(local_rank)
    dist.init_process_group("nccl" if use_cuda else "gloo")
    device = torch.device("cuda", local_rank) if use_cuda else torch.device("cpu")
    return dist.get_rank(), dist.get_world_size(), device


def mean_across_ranks(value: torch.Tensor) -> torch.Tensor:
    out = value.detach().clone()
    dist.all_reduce(out, op=dist.ReduceOp.SUM)
    return out / dist.get_world_size()
```

- Backends: `nccl` for CUDA, `gloo` for CPU and tests. 2.15 notes: the rewritten NCCL backend is the default, each group binds to one CUDA device, and `nccl-legacy` with `TORCH_DIST_USE_NCCL2=0` are announced for removal in the next release; do not depend on them.
- Call `torch.cuda.set_device(local_rank)` before creating the group, and call `dist.destroy_process_group()` at exit.
- `init_process_group(backend, init_method, timeout, world_size, rank, store, device_id, ...)`: `device_id` binds the rank to a device up front; `timeout` is a `datetime.timedelta`.
- Every rank must call every collective in the same order with matching shapes; a mismatch hangs or crashes.
- Rank-0-only work: logging, saving a consolidated file, evaluation printing. Wrap it in `if dist.get_rank() == 0:` but keep collectives outside the branch.
- Metrics: reduce sums and counts with `all_reduce`, then divide; averaging per-rank averages is wrong for unequal shards.
- `dist.barrier()` synchronises ranks; use sparingly and never inside the training step.
- Communicate Python objects with `all_gather_object` or `broadcast_object_list`; they pickle, so use them only between your own trusted ranks.

## 3. DDP

```python
import contextlib

import torch.nn as nn
from torch.nn.parallel import DistributedDataParallel as DDP

model = nn.Linear(10, 2).to(device)
ddp = DDP(model, device_ids=[local_rank] if device.type == "cuda" else None)

accum = 4
for i, (x, y) in enumerate(loader):
    sync = (i + 1) % accum == 0
    ctx = contextlib.nullcontext() if sync else ddp.no_sync()
    with ctx:
        loss = nn.functional.cross_entropy(ddp(x.to(device)), y.to(device)) / accum
        loss.backward()
    if sync:
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
```

- DDP replicates the model on every rank and all-reduces gradients in buckets during `backward`; wrap the model once, after moving it to its device.
- Initial weights must match across ranks: DDP broadcasts parameters and buffers from rank 0 at construction, but seed anyway for reproducibility.
- Use `model.no_sync()` (on the DDP wrapper) for the micro-batches that do not step the optimizer; the sketch above uses `contextlib.nullcontext()` on the sync step.
- `find_unused_parameters=True` is needed only when some parameters get no gradient in a step; it adds overhead, so fix the model if possible. `static_graph=True` can help when the graph does not change between steps (check the docs for its constraints).
- Access the original module through `ddp.module`; save `ddp.module.state_dict()` to avoid the `module.` key prefix.
- `DDP(..., bucket_cap_mb=...)`, `gradient_as_bucket_view=True` and `broadcast_buffers` are tuning options; change them only with a profile.
- `torch.compile(ddp_model)` is supported; compile after wrapping with DDP (check the docs for DDP-specific compile notes such as `optimize_ddp`).
- Use `SyncBatchNorm.convert_sync_batchnorm(model)` only when per-GPU batches are very small, since it adds communication.
- Per-rank data: `DistributedSampler` with `set_epoch` each epoch (data-loading.md).

## 4. FSDP2 fully shard

FSDP2 is the per-parameter sharded API in `torch.distributed.fsdp`. The older class `FullyShardedDataParallel` (FSDP1) is still importable from the same package; new code uses `fully_shard`.

Signature on 2.15: `fully_shard(module, *, mesh=None, reshard_after_forward=None, shard_placement_fn=None, mp_policy=MixedPrecisionPolicy(...), offload_policy=OffloadPolicy(), ignored_params=None, dp_mesh_dims=None)`. `MixedPrecisionPolicy(param_dtype=None, reduce_dtype=None, output_dtype=None, cast_forward_inputs=True, *, param_dtype_override_fn=None)`.

```python
import os

import torch
import torch.distributed as dist
import torch.nn as nn
from torch.distributed.device_mesh import init_device_mesh
from torch.distributed.fsdp import MixedPrecisionPolicy, fully_shard


class Block(nn.Module):
    def __init__(self, d: int) -> None:
        super().__init__()
        self.net = nn.Sequential(nn.Linear(d, d), nn.GELU(), nn.Linear(d, d))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.net(x)


def main() -> None:
    use_cuda = torch.cuda.is_available()
    device_type = "cuda" if use_cuda else "cpu"
    if use_cuda:
        torch.cuda.set_device(int(os.environ["LOCAL_RANK"]))
    dist.init_process_group("nccl" if use_cuda else "gloo")
    mesh = init_device_mesh(device_type, (dist.get_world_size(),))

    torch.manual_seed(0)
    model = nn.Sequential(*[Block(32) for _ in range(4)]).to(device_type)
    mp = MixedPrecisionPolicy(param_dtype=torch.bfloat16, reduce_dtype=torch.float32)
    for block in model:                       # shard each block first ...
        fully_shard(block, mesh=mesh, mp_policy=mp)
    fully_shard(model, mesh=mesh, mp_policy=mp)  # ... then the root

    opt = torch.optim.AdamW(model.parameters(), lr=1e-3)  # after sharding
    x = torch.randn(8, 32, device=device_type)
    for _ in range(3):
        loss = model(x).float().pow(2).mean()
        loss.backward()
        opt.step()
        opt.zero_grad(set_to_none=True)
    if dist.get_rank() == 0:
        print("loss", loss.item())
    dist.destroy_process_group()


if __name__ == "__main__":
    main()
```

Run with `torchrun --standalone --nproc_per_node=2 fsdp_demo.py` (the script ran on CPU with gloo and bf16 policy on 2.15).

- Apply `fully_shard` bottom-up: each repeated block, then the root module. Each call forms one communication group; parameters not owned by a sub-group are handled by the root.
- `fully_shard` changes the module class in place (the object becomes an `FSDPModule` subclass); parameters become `DTensor`s sharded on dim 0, so `model.parameters()` after sharding holds the sharded tensors. Build the optimizer afterwards.
- `reshard_after_forward`: `True` frees the unsharded parameters after forward (less memory, one more all-gather in backward); `False` keeps them; an integer reshards to a smaller group. The default (`None`) picks a sensible value per module, with the root not resharded after forward since backward starts there; check the docs for the exact rule.
- Mixed precision: `param_dtype=torch.bfloat16` runs compute in bf16 with fp32 sharded master parameters; set `reduce_dtype=torch.float32` for fp32 gradient reduction. Since 2.15, `reduce_dtype=None` reduces in the parameter's original dtype, so set it explicitly if you relied on the older behaviour.
- Offload: `offload_policy=CPUOffloadPolicy()` (import from `torch.distributed.fsdp`; takes `pin_memory=True`) moves sharded parameters and gradients to host memory at a speed cost.
- `FSDPModule` methods present on 2.15 include `unshard`, `reshard`, `set_requires_gradient_sync`, `set_reshard_after_backward`, `set_modules_to_forward_prefetch`, `set_modules_to_backward_prefetch` and `set_is_last_backward`. Use `set_requires_gradient_sync(False)` on micro-batches that only accumulate gradients.
- Hybrid sharding (shard within a node, replicate across nodes) uses a 2D `DeviceMesh` with named dims (`init_device_mesh(..., mesh_shape, mesh_dim_names=(...))`) passed as `mesh`; check the FSDP2 docs for the dimension order and for combining with tensor parallelism.
- Clip gradients with `torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)`; it works on `DTensor` gradients.
- Frozen parameters, tied weights and shared modules need care: shard shared modules once, at a level that contains all users, and verify with a short run.
- FSDP2 composes with `torch.compile` (compile per block) and activation checkpointing (wrap blocks before sharding).
- Do not mix FSDP1 and FSDP2 wrappers in one model.

## 5. Distributed checkpoints

```python
import torch.distributed.checkpoint as dcp
from torch.distributed.checkpoint.state_dict import (
    StateDictOptions,
    get_model_state_dict,
    get_state_dict,
    set_state_dict,
)

# every rank takes part in save and load
model_sd, opt_sd = get_state_dict(model, optimizer)
dcp.save({"model": model_sd, "optim": opt_sd}, checkpoint_id="ckpt/step_1000")

model_sd, opt_sd = get_state_dict(model, optimizer)   # fresh sharded templates
state = {"model": model_sd, "optim": opt_sd}
dcp.load(state, checkpoint_id="ckpt/step_1000")
set_state_dict(model, optimizer, model_state_dict=state["model"], optim_state_dict=state["optim"])

full = get_model_state_dict(model, options=StateDictOptions(full_state_dict=True, cpu_offload=True))
if dist.get_rank() == 0:
    torch.save(full, "model_full.pt")      # consolidated weights for inference
```

- All ranks call `dcp.save` and `dcp.load`; each writes its own shards into the directory. The format reshards on load, so a job can resume on a different world size.
- `torch.distributed.checkpoint.async_save` overlaps writing with training; the function exists on 2.15, check its current semantics and memory cost before use.
- `StateDictOptions(full_state_dict=True, cpu_offload=True)` gathers a full state dict; fields on 2.15 also include `ignore_frozen_params`, `strict` and `broadcast_from_rank0`. Full gathering needs host memory for the whole model on the ranks that receive it.
- Keep the step, epoch and sampler seed in a small rank-0 JSON or in the same dict as plain values.
- The 2.15 release notes list a compatibility break: distributed checkpoints saved with 2.15 cannot be loaded by 2.14 or earlier. Pin one version across a job's save and load sides.
- Use a shared, durable filesystem or object store path; local disks on each node hold only that node's shards.
- The final `torch.save` of the consolidated dict follows the plain state-dict rules: load it with `weights_only=True`.

## 6. Debugging hangs and errors

- Reproduce with 2 processes on `gloo` and CPU first; many ordering and shape-mismatch bugs appear there.
- A hang is usually one rank skipping a collective (an `if rank == 0:` around `dcp.save` or `all_reduce`), unequal batch counts per rank (use `drop_last=True` or equal shards), or one rank crashing while others wait. Look at the first failing rank's log.
- Set a finite `timeout` in `init_process_group` so stuck jobs fail with a trace. 2.15 notes: the rewritten NCCL backend ships a flight recorder for hang diagnosis; read the distributed docs for how to enable and dump it.
- `dist.monitored_barrier()` (gloo) reports which rank failed to arrive; useful in tests.
- `TORCH_DISTRIBUTED_DEBUG=DETAIL` adds collective consistency checks at a speed cost; `INFO` prints less. Check the docs for the current levels.
- `NCCL_DEBUG=INFO` prints NCCL setup details (network interface, transport); set `NCCL_SOCKET_IFNAME` when the wrong interface is picked on multi-NIC hosts.
- Out of memory on one rank often shows as a timeout on the others; check `nvidia-smi` per rank and the per-rank logs from `--log-dir` with `--tee 3` or `--local-ranks-filter` to reduce noise.
- Uneven last batches in evaluation: pad or compute metrics from summed counts so ranks make the same number of collective calls.
- Different results between 1 and N GPUs are expected from different batch composition and reduction order; compare with a fixed global batch and loose tolerance.

## 7. Launch recipes

```bash
# 2-process CPU smoke test (CI)
torchrun --standalone --nproc_per_node=2 train.py --max-steps 2

# one node, 8 GPUs, logs per rank in ./logs
torchrun --standalone --nproc_per_node=8 --log-dir ./logs train.py --config configs/base.yaml

# two nodes, run on each node
torchrun --nnodes=2 --nproc_per_node=8 \
  --rdzv-backend=c10d --rdzv-endpoint="${HEAD_HOST}:29500" --rdzv-id=run42 \
  --max-restarts=3 train.py --config configs/base.yaml
```

- Make `train.py` resume from the latest checkpoint if one exists, so `--max-restarts` and scheduler requeues are safe.
- Pass the same seed to all ranks and derive per-rank randomness (`seed + rank`) where it should differ.
- Keep the global batch size, learning rate and warm-up in the config and derive the per-device batch from `world_size`, so the run is comparable across cluster sizes.
