# systemd Units and Hardening

Reference for writing, sandboxing, scheduling and debugging systemd units. Directive names below are documented in `systemd.exec(5)`, `systemd.service(5)`, `systemd.resource-control(5)` and `systemd.timer(5)`; confirm availability against the installed version with `systemctl --version` and `man systemd.exec`, because newer directives are not present on older LTS releases.

## Contents
- [Unit layout and overrides](#unit-layout-and-overrides)
- [Hardening directives](#hardening-directives)
- [Resource control](#resource-control)
- [Timers](#timers)
- [Secrets and credentials](#secrets-and-credentials)
- [Debugging](#debugging)

## Unit layout and overrides

- Packaged units live in `/usr/lib/systemd/system/`; local units and drop-ins in `/etc/systemd/system/`. Never edit the packaged file; use `systemctl edit <unit>` (creates `/etc/systemd/system/<unit>.d/override.conf`) or `systemctl edit --full <unit>` for a full copy.
- Reset a list-type setting in a drop-in by assigning it empty first (`ExecStart=` then the new `ExecStart=`).
- After adding or changing unit files run `systemctl daemon-reload`; changing a unit does not restart the running service.
- Restart-loop protection belongs in `[Unit]`: `StartLimitIntervalSec=` and `StartLimitBurst=`. Pair `Restart=on-failure` with `RestartSec=`.
- Order on the network with `After=network-online.target` plus `Wants=network-online.target`; `network.target` alone does not mean an address is configured.
- `Type=notify` requires the program to call `sd_notify`; use `Type=simple` otherwise. Avoid `Type=forking` for new software.

## Hardening directives

Start from a restrictive set, run `systemd-analyze security <unit>` to see the exposure score and which directives are missing, then relax only what the service demonstrably needs.

| Directive | Effect |
|---|---|
| `NoNewPrivileges=yes` | Process and children cannot gain privileges via setuid or file capabilities |
| `ProtectSystem=strict` | Whole file system hierarchy read-only except `/dev`, `/proc`, `/sys`; add writable paths with `ReadWritePaths=` or better `StateDirectory=` |
| `ProtectHome=yes` | `/home`, `/root`, `/run/user` inaccessible (`read-only` and `tmpfs` are alternatives) |
| `PrivateTmp=yes` | Private `/tmp` and `/var/tmp` |
| `PrivateDevices=yes` | Minimal `/dev`, no physical devices |
| `DynamicUser=yes` | Allocates a transient unprivileged user at start; implies several restrictions and pairs with `StateDirectory=`, `CacheDirectory=`, `LogsDirectory=`, `RuntimeDirectory=` |
| `CapabilityBoundingSet=` | Empty value drops all capabilities; list only what is required, for example `CAP_NET_BIND_SERVICE` |
| `AmbientCapabilities=` | Capabilities granted to a non-root service user; keep it a subset of the bounding set |
| `ProtectKernelTunables=yes`, `ProtectKernelModules=yes`, `ProtectKernelLogs=yes`, `ProtectControlGroups=yes`, `ProtectClock=yes`, `ProtectHostname=yes` | Block writes to kernel interfaces |
| `ProtectProc=invisible`, `ProcSubset=pid` | Hide other users' processes and non-process `/proc` entries |
| `RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6` | Limit socket families |
| `RestrictNamespaces=yes` | Forbid creating namespaces |
| `RestrictSUIDSGID=yes`, `LockPersonality=yes`, `RestrictRealtime=yes` | Close common escalation paths |
| `MemoryDenyWriteExecute=yes` | Forbid W+X memory; breaks JIT runtimes (Node.js, JVM, some Python extensions), so test before enabling |
| `SystemCallFilter=@system-service` | Allow-list of syscall groups; add `SystemCallErrorNumber=EPERM` to fail instead of killing; inspect groups with `systemd-analyze syscall-filter` |
| `SystemCallArchitectures=native` | Block non-native syscall ABIs |
| `UMask=0077` | Restrictive default file mode |
| `IPAddressDeny=any` with `IPAddressAllow=` | Per-service IP allow-list via cgroup BPF |

Rules:
- Do not create world-writable paths for a service (`chmod 777`, `UMask=0000`). Give the unit a `StateDirectory=` it owns.
- Run as a dedicated user or `DynamicUser=yes`, never as root unless the job requires it, and then bound it with `CapabilityBoundingSet=`.
- Binding ports below 1024 needs `AmbientCapabilities=CAP_NET_BIND_SERVICE` (or a reverse proxy or socket activation), not root.
- `systemd-analyze security` scores are a guide; a score of 0.0 is not a goal if it breaks the service.

## Resource control

cgroup v2 is the only hierarchy supported by current systemd (cgroup v1 support was removed in systemd 258). Relevant unit settings:

- `MemoryMax=` hard limit (OOM kill inside the cgroup), `MemoryHigh=` throttling threshold, `MemorySwapMax=`.
- `CPUWeight=` relative share, `CPUQuota=` absolute cap (for example `CPUQuota=200%`).
- `TasksMax=` process and thread cap, `IOWeight=` relative block I/O share.
- `LimitNOFILE=` raises the file descriptor limit for the service; `ulimit` in a shell does not apply to units.
- Ad-hoc limits: `systemd-run --scope -p MemoryMax=512M -- <command>`. Inspect with `systemd-cgtop` and `systemctl status <unit>`.

## Timers

- A timer activates the service with the same name. Use `OnCalendar=` for wall-clock schedules, `Persistent=true` to catch up after downtime, and `RandomizedDelaySec=` to spread load across hosts.
- Check expressions with `systemd-analyze calendar "Mon..Fri 02:30"`; list schedules with `systemctl list-timers`.
- Use `OnBootSec=` and `OnUnitActiveSec=` for interval-style jobs.
- A one-shot job service uses `Type=oneshot`; keep the same hardening directives as long-running services.

## Secrets and credentials

- Prefer `LoadCredential=name:/path` (or `LoadCredentialEncrypted=` / `SetCredentialEncrypted=` with `systemd-creds`) over secrets in `Environment=`; the service reads the secret from `$CREDENTIALS_DIRECTORY`.
- `EnvironmentFile=` is acceptable for non-secret settings; if it holds secrets, the file must be `0600` and owned by root.
- Environment variables are visible to same-user processes through `/proc/<pid>/environ` and in `systemctl show`; do not put tokens in `Environment=`.

## Debugging

- `systemctl status <unit>`, `systemctl cat <unit>` (merged view with drop-ins), `systemctl show <unit> -p <Property>`, `systemctl list-dependencies <unit>`.
- `journalctl -u <unit> -b --no-pager`, `-p err`, `-f`, `--since "1 hour ago"`.
- `systemd-analyze verify /etc/systemd/system/<unit>.service` checks syntax and referenced paths.
- `systemd-analyze blame` and `systemd-analyze critical-chain` for boot time.
- A unit that fails only under hardening: relax one directive at a time with a drop-in and read `journalctl` plus `dmesg` for `EPERM` and seccomp messages.
