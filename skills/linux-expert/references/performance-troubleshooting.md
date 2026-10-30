# Linux Performance Troubleshooting

Reference for diagnosing CPU, memory, disk and network problems on a Linux host with standard tools. Work top-down: confirm the symptom, find the saturated resource, find the process, then the cause. Change one thing at a time and record before and after numbers.

## Contents
- [First five minutes](#first-five-minutes)
- [CPU](#cpu)
- [Memory](#memory)
- [Disk and file systems](#disk-and-file-systems)
- [Network](#network)
- [Pressure stall information](#pressure-stall-information)
- [Tracing and profiling](#tracing-and-profiling)
- [Kernel parameters](#kernel-parameters)

## First five minutes

```bash
uptime                      # load averages (runnable + uninterruptible tasks), not CPU percent
dmesg -T | tail -n 50       # OOM kills, I/O errors, NIC resets, segfaults (may need root)
vmstat 1 5                  # r (runnable), b (blocked), si/so (swap), wa (iowait), cs
mpstat -P ALL 1 3           # per-CPU utilisation (sysstat package)
pidstat 1 3                 # per-process CPU
iostat -xz 1 3              # per-device utilisation, await, queue size
free -m                     # use the "available" column, not "free"
ss -s                       # socket summary
journalctl -p err -b        # errors since boot
```

Apply the USE method per resource: utilisation, saturation, errors. High load with idle CPU usually means tasks blocked on disk or locks (state `D`); high load with busy CPU means CPU saturation.

## CPU

- `top` / `htop`, `pidstat -u 1`, `ps -eo pid,ppid,stat,pcpu,pmem,comm --sort=-pcpu | head`.
- High `%sys` points at syscalls or kernel work (network, page faults); high `%usr` at application code; high `%steal` at a noisy neighbour on a virtual machine; high `%iowait` at storage.
- A container or service throttled by its cgroup shows `nr_throttled` in `cpu.stat` under `/sys/fs/cgroup/<path>/` (cgroup v2); raise `CPUQuota=` or `CPUWeight=` rather than removing limits.
- CPU frequency and power profile matter on bare metal; check the governor with `cpupower frequency-info` where available.

## Memory

- `free -m`, `/proc/meminfo` (`MemAvailable`, `Dirty`, `Slab`, `SwapCached`), `smem` or `ps_mem` for per-process proportional usage, `pmap -x <pid>`.
- Sustained swap-in and swap-out (`si`/`so` in `vmstat`) is the symptom to chase; used swap alone is not.
- OOM kills: `journalctl -k | grep -i 'out of memory'` or `dmesg -T | grep -i oom`. The report lists the victim, its `oom_score` and per-process memory. With cgroup v2 an OOM inside a service cgroup is caused by `MemoryMax=`; check `memory.events` (`oom_kill` counter) and `memory.current`.
- Prefer `MemoryHigh=` (throttle) below `MemoryMax=` (kill) for services that can slow down gracefully; use `systemd-oomd` settings (`ManagedOOMMemoryPressure=`) only where you understand the policy.
- Transparent huge pages can cause latency spikes for databases; follow the database vendor's guidance (`/sys/kernel/mm/transparent_hugepage/enabled`).
- Leaks: watch RSS over time (`pidstat -r 5`), then use the language's profiler; kernel-level leaks show in `Slab` growth and `slabtop`.

## Disk and file systems

- `iostat -xz 1`: `%util` near 100 on a single-queue device or rising `await` and `aqu-sz` indicate saturation; NVMe devices can serve many parallel requests, so `%util` alone misleads.
- `iotop -oPa` or `pidstat -d 1` for the process; `lsof +L1` finds deleted-but-open files holding space; `df -h` and `df -i` (inodes); `du -xh --max-depth=1 /var | sort -h`.
- `findmnt` shows mount options; `noatime` or the default `relatime` avoids needless writes; do not disable barriers or `fsync` semantics to gain speed on data you care about.
- Benchmark with `fio` against a test file on the same file system, never on a raw device holding data. Use direct I/O and a realistic block size and queue depth.
- File systems: ext4 is the conservative default; XFS suits large files and parallel I/O; on LVM, `lvs`/`vgs` show thin-pool usage (a full thin pool stalls I/O).
- SMART and NVMe health: `smartctl -a /dev/sdX`, `nvme smart-log /dev/nvme0` (smartmontools, nvme-cli).

## Network

- `ss -tulpn` (listeners), `ss -ti dst <ip>` (per-connection TCP info), `ss -s`, `ip -s link` (drops, errors), `nstat -az | grep -i retrans`.
- Many `TIME-WAIT` sockets are normal; exhaustion of ephemeral ports or `nf_conntrack: table full` messages in `dmesg` are not. Check `sysctl net.netfilter.nf_conntrack_count net.netfilter.nf_conntrack_max`.
- Listen queue overflows: `nstat -az TcpExtListenOverflows`; raise the application backlog and `net.core.somaxconn` together.
- Latency and path: `mtr -rwz host`, `ping`, `traceroute`; DNS: `resolvectl query host`, `resolvectl status`.
- Capture narrowly: `tcpdump -ni eth0 -c 200 'host 10.0.0.5 and tcp port 443'` and write to a file with `-w`; packet captures can contain secrets, so restrict access and delete them after use.
- NIC offload and ring sizes: `ethtool -S eth0`, `ethtool -g eth0`; change only after measuring drops.

## Pressure stall information

PSI is exposed in `/proc/pressure/{cpu,memory,io}` and per cgroup in `cpu.pressure`, `memory.pressure`, `io.pressure` (cgroup v2). `some` is the share of time at least one task stalled; `full` is the share of time all non-idle tasks stalled. Use it to tell "busy" from "stalled" and as an alerting signal.

## Tracing and profiling

- `strace -f -tt -T -p <pid>` and `strace -c -p <pid>` (syscall summary) cost a lot on busy processes; attach briefly. Prefer `perf trace` or eBPF tools for production.
- `perf top`, `perf record -g -p <pid> -- sleep 30` then `perf report`; flame graphs need symbols (`-fno-omit-frame-pointer` or DWARF) for useful stacks.
- `bpftrace` and the bcc tools (`execsnoop`, `opensnoop`, `biolatency`, `tcpretrans`) answer targeted questions with low overhead; they need root and a recent kernel with BTF. Check the one-liners against `bpftrace -l` before use.
- `lsof -p <pid>`, `ls -l /proc/<pid>/fd | wc -l`, `cat /proc/<pid>/limits` for descriptor exhaustion; `cat /proc/<pid>/stack` (root) for where a `D` state task sleeps.
- Core dumps: `coredumpctl list`, `coredumpctl info <pid>`, `coredumpctl gdb`.

## Kernel parameters

- Put settings in `/etc/sysctl.d/NN-name.conf` (never in `/etc/sysctl.conf`), apply with `sysctl --system`, inspect with `sysctl -a | grep <key>`.
- Settings that commonly matter, each to be changed only with a measured reason: `vm.swappiness`, `vm.dirty_ratio` and `vm.dirty_background_ratio`, `net.core.somaxconn`, `net.ipv4.ip_local_port_range`, `fs.file-max`, `fs.inotify.max_user_watches`, `net.ipv4.tcp_syncookies` (leave on).
- Do not copy tuning snippets between hosts or from blog posts; kernel defaults change between releases and many old recommendations are obsolete.
- Per-service limits (`LimitNOFILE=`, `TasksMax=`) go in the unit; `/etc/security/limits.conf` applies to PAM sessions only.
