---
name: linux-expert
description: >-
  Operates, hardens and troubleshoots Linux servers (Ubuntu Server LTS, Debian, RHEL family): systemd units and timers, sandboxing, OpenSSH, sudo and sudoers, nftables and ufw, netplan, apt and unattended-upgrades, Ubuntu Pro (ESM, Livepatch), cloud-init and autoinstall, AppArmor, SELinux, cgroup v2, storage and performance diagnosis. Absorbs the former ubuntu-server-expert. Use when writing or reviewing .service or .timer files, sshd_config, /etc/sudoers.d files, nftables rulesets, netplan YAML, cloud-init user-data, sysctl settings, or when debugging high load, OOM kills, full disks and boot failures. Not for container images and Compose (use docker-expert), Kubernetes (use kubernetes-expert), web server config (use nginx-expert) or cloud APIs and IaC (use aws-expert, terraform-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Linux Expert

This skill covers day-to-day administration and hardening of Linux hosts: unit files, access control, firewalling, patching, networking, storage and performance diagnosis. It leans on Ubuntu Server LTS as the reference distribution (netplan, apt, Ubuntu Pro, AppArmor, cloud-init) and notes where Debian and the RHEL family differ. It stays at the host level; containers, orchestration and cloud provisioning belong to the neighbouring skills.

> Verified against Ubuntu 26.04 LTS (standard support to May 2031, ESM to May 2036; 24.04 LTS to May 2029 and May 2034), systemd 262 (cgroup v1 removed in 258), OpenSSH 10.6p1 (hybrid post-quantum KEX default since 10.0, DSA removed), sudo-rs as Ubuntu's default sudo (2026-10).

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

- Covered: systemd services, timers, sandboxing and cgroup limits; OpenSSH, sudo and PAM; nftables, ufw and sysctl hardening; netplan and `systemd-networkd`; apt, unattended-upgrades, Ubuntu Pro, Livepatch; cloud-init and autoinstall; AppArmor and SELinux; LVM, file systems and mounts; performance and boot troubleshooting.
- Not covered: Dockerfiles, images, Compose (docker-expert); pods, manifests, cluster operations (kubernetes-expert); nginx configuration (nginx-expert); cloud resources and IaC modules (aws-expert, terraform-expert); CI pipelines (cicd-expert).
- Distribution notes: commands target Ubuntu Server unless marked. Package names, paths and the MAC system differ on RHEL family (dnf, firewalld, SELinux); check the target distribution before copying.

## 2. Core Expertise

| Area | Key tools and files |
|---|---|
| Init and services | `systemctl`, `journalctl`, `systemd-analyze`, unit files in `/etc/systemd/system/`, drop-ins, timers, `systemd-run` |
| Resource control | cgroup v2, `MemoryMax=`, `CPUWeight=`, `TasksMax=`, PSI in `/proc/pressure/`, `systemd-cgtop` |
| Access | `sshd_config.d/`, `authorized_keys`, SSH certificates, `visudo`, `/etc/sudoers.d/`, PAM, `sudo-rs` |
| Firewall | nftables (`nft`, `/etc/nftables.conf`), ufw, firewalld (RHEL family), `ss`, conntrack |
| Network | netplan, `systemd-networkd`, NetworkManager, `ip`, `resolvectl`, `networkctl` |
| Packages and patching | apt, dpkg, unattended-upgrades, needrestart, dnf, Ubuntu Pro (ESM, Livepatch), `do-release-upgrade` |
| Provisioning | cloud-init, autoinstall, cloud images, configuration management |
| Mandatory access control | AppArmor (`aa-status`, `aa-complain`, `aa-enforce`), SELinux (`getenforce`, `ausearch`, `audit2allow`) |
| Storage | LVM, ext4, XFS, `findmnt`, `lsblk`, `fio`, SMART, `fstrim.timer` |
| Observability | `vmstat`, `iostat`, `pidstat`, `perf`, `strace`, bpftrace, `dmesg`, `journalctl` |

Ubuntu facts worth knowing before touching a host:
- Ubuntu 26.04 LTS is the current LTS (released April 2026). 24.04 and 22.04 remain in standard support; ESM through Ubuntu Pro extends each by five years.
- `sudo` on current Ubuntu is `sudo-rs`; the original sudo is available as `sudo.ws`. Sudoers files remain edited with `visudo`.
- cgroup v2 is the only hierarchy in current systemd; tools and runtimes that assumed v1 paths need updating.
- nftables is the kernel firewall framework; `iptables` on Ubuntu is a compatibility front end over it. New rules should be written in nftables or through ufw.

## 3. Workflow

1. Identify the target: distribution and release (`/etc/os-release`), kernel (`uname -r`), systemd version (`systemctl --version`), virtualization, and whether the host is managed by configuration management or cloud-init.
2. Reproduce or observe before changing: `systemctl status`, `journalctl -u <unit> -b`, `dmesg -T`, `ss -tulpn`, `df -h`, `free -m`, `uptime`.
3. Form one hypothesis from the evidence (resource saturation, permission or sandbox denial, config error, dependency order) and change one thing at a time.
4. Make persistent changes in files under `/etc` (drop-ins, `sysctl.d`, `sshd_config.d`, `sudoers.d`), not by hand-run commands, so they survive reboot and can be versioned.
5. Validate syntax with the tool's own checker before reload: `sshd -t`, `visudo -c`, `nft -c -f`, `systemd-analyze verify`, `netplan generate`.
6. Apply risky remote changes with a safety net: keep an open session, use `netplan try`, schedule a revert with `systemd-run --on-active=5m`, or test on a clone first.
7. Verify from outside the host (port reachable, login works, unit healthy after `systemctl restart` and after reboot) and record the change.
8. For incidents, capture evidence first (journal excerpt, `dmesg`, `ss`, process list) before restarting anything.

## 4. Decision Rules

- Service supervision: a systemd unit, not `nohup`, screen or cron `@reboot`.
- Scheduled jobs: a systemd timer (logs in the journal, `Persistent=`, randomized delay, dependencies) over cron when the host runs systemd; cron remains fine for existing simple jobs.
- Firewall: pick one owner per host. ufw for simple host rules on Ubuntu, nftables directly for sets, rate limits and NAT, firewalld on RHEL family. Docker bypasses ufw for published ports; bind to `127.0.0.1` or manage `DOCKER-USER`.
- Network configuration: netplan on Ubuntu Server, NetworkManager on RHEL family and desktops; never mix tools for the same interface.
- Patching: security updates automatic (`unattended-upgrades`), feature and kernel updates scheduled; Livepatch or Ubuntu Pro where reboot windows are scarce.
- SSH: key-only, `PermitRootLogin no`, drop-in config, certificates once the fleet exceeds a handful of hosts.
- Privilege: dedicated service users and `DynamicUser=yes` for services; sudoers entries for specific commands with full paths, edited with `visudo -f /etc/sudoers.d/<file>`.
- MAC: keep AppArmor (Ubuntu) or SELinux (RHEL family) enforcing; debug one profile or domain at a time in complain or permissive mode.
- File system: ext4 by default, XFS for large files and parallel I/O; LVM when resizing or snapshots are needed.
- Memory limits: `MemoryHigh=` below `MemoryMax=` for services that can degrade gracefully.
- Reboot vs live patch: reboot when the kernel is updated unless Livepatch covers the CVE.

## 5. Coding Standards

- Shell scripts: `#!/usr/bin/env bash`, `set -euo pipefail`, quote every expansion, `mktemp` for temp files, `trap` for cleanup, `shellcheck` clean. Use `[[ ]]`, arrays and `printf` instead of unquoted word splitting and `echo -e`.
- Never `curl ... | sh` without verifying a pinned checksum or signature first; download to a file, verify, then run.
- Unit files: lowercase, hyphenated names (`example-api.service`); `Description=` set; `ExecStart=` with an absolute path; one concern per unit; drop-ins for local changes.
- Config under `/etc/<app>.d/NN-purpose.conf` drop-ins where supported (sshd, sysctl, sudoers, apt, cloud-init) so packaged files stay untouched.
- YAML (netplan, cloud-init): two-space indentation, no tabs, validate with the tool (`netplan generate`, `cloud-init schema`).
- File modes: secrets `0600` or `0640` with a service group; directories `0750`; never `chmod 777`.
- Idempotence: commands in provisioning scripts must be safe to rerun (`install -d`, `ln -sfn`, `grep -q || tee -a`).
- Comment intent and the reason for non-default values (why a sysctl is set, why a capability is kept).

## 6. Project Structure

Host configuration kept in version control and applied by configuration management or an image build:

```
host-config/
├── systemd/
│   ├── example-api.service
│   ├── example-api.service.d/
│   │   └── 10-limits.conf
│   ├── example-backup.service
│   └── example-backup.timer
├── ssh/
│   └── sshd_config.d/10-hardening.conf
├── sudoers.d/
│   └── 10-deploy                # validated with visudo -c
├── nftables/
│   └── nftables.conf
├── sysctl.d/
│   └── 60-network.conf
├── netplan/
│   └── 01-network.yaml
├── cloud-init/
│   └── user-data.yaml           # no secrets
├── apparmor.d/
│   └── usr.local.bin.example-api
└── tests/
    └── verify.sh                # post-deploy checks
```

## 7. Design Patterns

- **Hardened service**: dedicated user or `DynamicUser=yes`, `StateDirectory=`, `ProtectSystem=strict`, `NoNewPrivileges=yes`, empty `CapabilityBoundingSet=`, `RestrictAddressFamilies=`, `SystemCallFilter=@system-service`; score with `systemd-analyze security`.
- **Timer plus oneshot**: `Type=oneshot` service triggered by a timer with `OnCalendar=`, `Persistent=true`, `RandomizedDelaySec=`; overlapping runs prevented by the service model.
- **Drop-in layering**: packaged defaults untouched; local overrides in `*.d/NN-name.conf`; later files win (except sshd, where the first value wins).
- **Default-deny firewall**: policy `drop` on input, explicit accepts for established traffic, loopback, SSH from known sources, and required service ports.
- **Bastion plus ProxyJump**: only the bastion is reachable from outside; targets accept SSH from the bastion address; SSH certificates with short validity.
- **Golden image plus thin user-data**: patching and packages baked into the image; cloud-init sets hostname, keys and fetches secrets at boot with an instance role.
- **Immutable configuration**: edit in Git, deploy through configuration management, treat hand edits as drift.

## 8. Best Practices

- Look before acting: `systemctl cat <unit>` shows the merged unit, `sshd -T` and `sysctl -a` show effective settings, `systemctl show -p` shows properties.
- Prefer `systemctl reload` for daemons that support it; `restart` drops connections.
- Keep two terminals open for SSH, firewall and network changes; test the second login before closing the first.
- Use `journalctl -u <unit> -b -p warning` and `--since` filters rather than grepping log files; configure persistent journald (`Storage=persistent`, size limits) on hosts where post-reboot forensics matter.
- Name hosts and users meaningfully; avoid shared accounts.
- Keep clocks in sync (`timedatectl`, `systemd-timesyncd` or `chrony`), because TLS, Kerberos, logs and TOTP depend on it.
- Pin and review third-party repositories; use `Signed-By` keys under `/etc/apt/keyrings/`.
- Make mounts robust: use UUIDs in `/etc/fstab`, `nofail` for non-essential mounts, `x-systemd.automount` or timeouts for network mounts, and test with `findmnt --verify` before reboot.
- Document exceptions (accepted AppArmor complain mode, disabled hardening directive) next to the config.

## 9. Performance

- Diagnose in order: saturation of CPU, memory, disk, network (USE method), then the responsible process, then the code or setting. See [references/performance-troubleshooting.md](references/performance-troubleshooting.md).
- Load average counts runnable and uninterruptible tasks; check `vmstat` (`r`, `b`, `wa`) and `iostat -xz` before blaming CPU.
- `free` "available" is the meaningful number; page cache is not waste. Swap activity (`si`/`so`) is the symptom, not swap usage.
- PSI (`/proc/pressure/*`, per-cgroup `*.pressure`) distinguishes busy from stalled and works well as an alert signal.
- Raise `LimitNOFILE=` in the unit for services that need many descriptors; `ulimit` does not apply to units.
- `fstrim.timer` handles SSD trim on a schedule; avoid the `discard` mount option on busy volumes unless the vendor recommends it.
- Tune kernel parameters only with a measurement and put them in `/etc/sysctl.d/`; outdated blog tuning snippets often hurt on current kernels.
- Profile with `perf` or bpftrace for production; `strace` slows the target noticeably.

## 10. Security

- SSH: key-only authentication, `PermitRootLogin no`, `PasswordAuthentication no`, `AuthenticationMethods publickey`, `AllowGroups`, and a drop-in file named so it sorts before cloud images' own drop-ins. Do not pin custom cipher lists; OpenSSH 10 defaults already use a hybrid post-quantum KEX. Details in [references/ssh-access.md](references/ssh-access.md).
- sudo: least privilege. Allow specific commands by full path in `/etc/sudoers.d/<file>`, edited with `visudo -f`, preferably requiring a password. Never `NOPASSWD:ALL`. Automation gets a dedicated user limited to exact command lines. Do not allow shells, editors or interpreters through sudo.
- Services: non-root, `NoNewPrivileges=yes`, `ProtectSystem=strict`, `ProtectHome=yes`, `PrivateTmp=yes`, empty capability set, no world-writable paths. Details in [references/systemd-units.md](references/systemd-units.md).
- Secrets: `LoadCredential=` or a secret manager; never in `Environment=`, user-data, images or repositories. In cloud-init, never put passwords, tokens or private keys in user-data, because it is readable through the metadata service and logs.
- Firewall default deny inbound; expose only needed ports; keep administrative interfaces off the public internet.
- Patching: unattended security updates, `needrestart`, a reboot or Livepatch for kernel CVEs, ESM for packages past standard support.
- MAC: AppArmor or SELinux enforcing; never `setenforce 0` or `systemctl disable apparmor` as a fix.
- Kernel and network hardening via `sysctl.d`: `net.ipv4.tcp_syncookies=1`, `net.ipv4.conf.all.rp_filter=1` (or `2` with asymmetric routing), `net.ipv4.conf.all.accept_redirects=0`, `net.ipv6.conf.all.accept_ra` set deliberately, `kernel.kptr_restrict`, `kernel.dmesg_restrict=1`. Verify each applies on the target kernel with `sysctl -a`.
- Audit: `auditd` rules for privileged commands and identity files where compliance requires; `journalctl _COMM=sudo` for sudo use.
- Downloads: verify GPG signatures or checksums; no `curl | sh` without verification; no `apt-key add`.

## 11. Testing

- Syntax checkers in CI: `shellcheck`, `systemd-analyze verify`, `visudo -c -f`, `sshd -t -f`, `nft -c -f`, `netplan generate` (in a container or VM), `cloud-init schema --config-file`, `yamllint`.
- Behavior: Molecule, `testinfra` or a plain `verify.sh` against a disposable VM or LXD/multipass instance; assert listening ports (`ss`), service state (`systemctl is-active`), file modes, effective SSH settings (`sshd -T`), and sudo rules (`sudo -l -U`).
- Security scoring: `systemd-analyze security` per unit; compliance scans with `usg audit` (Ubuntu Pro) or OpenSCAP.
- Reboot test: confirm everything starts in the right order from a cold boot, not only after `systemctl restart`.
- Failure tests: kill the service and confirm `Restart=` behavior; fill a test disk; simulate network loss.
- Run risky changes (netplan, firewall, release upgrades) on a clone of the host first.

## 12. Review Checklist

- [ ] Units run as a non-root user, set sandboxing directives, and have `Restart=` and start limits
- [ ] No `chmod 777`, no world-writable paths, secrets are not in `Environment=` or user-data
- [ ] sshd: key-only, root login off, validated with `sshd -T`
- [ ] sudoers: specific commands, full paths, no `NOPASSWD:ALL`, validated with `visudo -c`
- [ ] Firewall default deny; no duplicate firewall managers
- [ ] Config in drop-ins, versioned, applied idempotently
- [ ] Syntax validators pass; change tested on a clone or with a rollback timer
- [ ] AppArmor or SELinux still enforcing
- [ ] Automatic security updates and a reboot or Livepatch plan exist
- [ ] Shell scripts use `set -euo pipefail`, quoting, and pass `shellcheck`
- [ ] No `curl | sh`, no `apt-key add`, repository keys use `Signed-By`
- [ ] Ubuntu release is within standard support or ESM is attached

## 13. Production Notes

- Check support dates at https://ubuntu.com/releaseendoflife; plan to leave a release before standard support ends, using ESM only as a bridge.
- Before upgrading a release (`do-release-upgrade`) take a snapshot or backup, rehearse on a clone, and review third-party repositories afterwards.
- Verify backups by restoring them; snapshots of the root volume do not replace application-consistent backups.
- Persist journald logs and ship them off-host if forensics matter; set `SystemMaxUse=`.
- `/var/run/reboot-required` marks pending reboots; stagger reboots across redundant nodes.
- Keep time sync and DNS (`resolvectl status`) in monitoring; many outages are expired certificates, full disks, exhausted inodes or descriptors, and clock skew.
- Document recovery access: console or serial access, rescue mode, and a break-glass key stored offline.
- Hosts that must stay up through kernel CVEs: Livepatch via Ubuntu Pro; Livepatch does not replace regular reboots for non-kernel updates.

## 14. Examples

Hardened service unit (`/etc/systemd/system/example-api.service`):

```ini
[Unit]
Description=Example API
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=60
StartLimitBurst=5

[Service]
Type=simple
DynamicUser=yes
StateDirectory=example-api
RuntimeDirectory=example-api
LoadCredential=api-key:/etc/example-api/api-key
ExecStart=/opt/example-api/bin/server --listen 127.0.0.1:8080
Restart=on-failure
RestartSec=2

NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectKernelLogs=yes
ProtectControlGroups=yes
ProtectClock=yes
ProtectHostname=yes
ProtectProc=invisible
ProcSubset=pid
CapabilityBoundingSet=
AmbientCapabilities=
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
RestrictNamespaces=yes
RestrictRealtime=yes
RestrictSUIDSGID=yes
LockPersonality=yes
SystemCallArchitectures=native
SystemCallFilter=@system-service
SystemCallErrorNumber=EPERM
UMask=0077
MemoryMax=512M
TasksMax=256

[Install]
WantedBy=multi-user.target
```

Check with `systemd-analyze verify` and `systemd-analyze security example-api.service`; add `MemoryDenyWriteExecute=yes` if the runtime does not use a JIT. The service reads the secret from `$CREDENTIALS_DIRECTORY/api-key`; the file `/etc/example-api/api-key` is `0600` root-owned.

Timer for a backup job:

```ini
# /etc/systemd/system/example-backup.timer
[Unit]
Description=Nightly backup

[Timer]
OnCalendar=*-*-* 02:30:00
Persistent=true
RandomizedDelaySec=15m

[Install]
WantedBy=timers.target
```

The paired `example-backup.service` uses `Type=oneshot` and the same hardening directives; enable with `systemctl enable --now example-backup.timer`.

Least-privilege sudoers (`sudo visudo -f /etc/sudoers.d/10-deploy`), mode `0440`:

```
Cmnd_Alias APP_CTL = /usr/bin/systemctl restart example-api.service, \
                     /usr/bin/systemctl status example-api.service
%deploy ALL=(root) APP_CTL
```

Members of `deploy` authenticate with their own password. A CI runner uses a separate dedicated user with exact command lines only, with no wildcards in the arguments.

Default-deny nftables host firewall (`/etc/nftables.conf`; check with `sudo nft -c -f /etc/nftables.conf`, do not run alongside ufw):

```
#!/usr/sbin/nft -f
flush ruleset

table inet filter {
  chain input {
    type filter hook input priority filter; policy drop;
    ct state invalid drop
    ct state established,related accept
    iif "lo" accept
    ip protocol icmp icmp type { echo-request, destination-unreachable, time-exceeded } limit rate 10/second accept
    meta l4proto ipv6-icmp accept
    tcp dport 22 ct state new limit rate 10/minute accept
    tcp dport { 80, 443 } accept
  }
  chain forward {
    type filter hook forward priority filter; policy drop;
  }
  chain output {
    type filter hook output priority filter; policy accept;
  }
}
```

Enable with `sudo systemctl enable --now nftables`. Restrict the SSH rule to a management network (`ip saddr 10.0.0.0/8 tcp dport 22 ...`) when possible.

SSH drop-in, `/etc/ssh/sshd_config.d/10-hardening.conf`: see [references/ssh-access.md](references/ssh-access.md). Validate with `sudo sshd -t`, reload, and test a new session before closing the old one.

## 15. Common Mistakes

- `chmod 777` to fix a permission error: find the actual owner or group mismatch (`namei -l <path>`, `ls -ld`, `journalctl` EACCES lines) and fix ownership or add a `StateDirectory=`.
- `setenforce 0` or disabling AppArmor to make a service run: use complain mode on that profile, fix the rules, re-enable enforcement.
- `NOPASSWD:ALL` in sudoers, or sudo access to shells, editors and interpreters: grant exact commands by full path.
- Running services as root: use a dedicated user or `DynamicUser=yes` and capabilities as needed.
- Putting the Ubuntu Pro token, passwords or private keys into cloud-init user-data: fetch them at boot from a secret manager through an instance role, or use Ubuntu Pro cloud images.
- `kill -9` as the first step: `systemctl stop` sends SIGTERM, waits `TimeoutStopSec=`, and then kills; fix a slow shutdown by handling SIGTERM.
- Editing `/etc/sysctl.conf` or packaged unit files: use `sysctl.d` and drop-ins so upgrades do not overwrite changes.
- Locking yourself out: closing the only SSH session after a firewall, sshd or netplan change. Use `netplan try`, a second session and a revert timer.
- Mixing firewall managers (ufw plus hand-written nftables, or Docker published ports assumed to be filtered by ufw).
- Forgetting `daemon-reload` after editing units, or expecting a restart to apply changes to `sshd_config` that has a drop-in later in the sort order (sshd keeps the first value).
- `apt-key add` for third-party repositories: use `Signed-By` keyrings.
- Piping remote scripts into a shell without verification.
- Relying on `ulimit` or `limits.conf` for services: set `LimitNOFILE=` in the unit.
- Ignoring `df -i` and deleted-but-open files when a disk "has space" but writes fail.
- Running a non-LTS release or an unsupported LTS without ESM on production hosts.

## 16. References

Reference files:
- [references/systemd-units.md](references/systemd-units.md): unit layout, overrides, hardening directives, resource control, timers, credentials, debugging.
- [references/ssh-access.md](references/ssh-access.md): OpenSSH defaults and hardening, keys and certificates, client config, sudo and sudoers, accounts and PAM.
- [references/performance-troubleshooting.md](references/performance-troubleshooting.md): USE-method triage, CPU, memory, disk, network, PSI, tracing, sysctl.
- [references/ubuntu-server.md](references/ubuntu-server.md): Ubuntu Server LTS support windows, netplan, apt and unattended-upgrades, Ubuntu Pro, cloud-init, autoinstall, AppArmor, ufw (absorbed from ubuntu-server-expert).

Official documentation:
- Ubuntu release and support dates: https://ubuntu.com/releaseendoflife
- Ubuntu Server documentation: https://documentation.ubuntu.com/server/
- systemd manual pages: https://www.freedesktop.org/software/systemd/man/
- OpenSSH release notes: https://www.openssh.com/releasenotes.html
- nftables wiki: https://wiki.nftables.org/
- Ubuntu Pro: https://ubuntu.com/pro
- cloud-init documentation: https://docs.cloud-init.io/
