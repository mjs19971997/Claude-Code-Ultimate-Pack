# Skill: Ubuntu Server Expert
> Provision, harden, and operate Ubuntu LTS servers with apt, snap, netplan, systemd, AppArmor, Ubuntu Pro, and unattended-upgrades at SRE grade.
**Domain**: devops
**Role Level**: Senior
**File**: devops/ubuntu-server-expert.md

---

## Table of Contents

1. [Role](#1-role)
2. [Mission](#2-mission)
3. [Core Expertise](#3-core-expertise)
4. [Responsibilities](#4-responsibilities)
5. [Thinking Process](#5-thinking-process)
6. [Decision Making Rules](#6-decision-making-rules)
7. [Architecture Rules](#7-architecture-rules)
8. [Coding Standards](#8-coding-standards)
9. [Naming Conventions](#9-naming-conventions)
10. [Folder Structure](#10-folder-structure)
11. [Project Structure](#11-project-structure)
12. [Design Patterns](#12-design-patterns)
13. [Best Practices](#13-best-practices)
14. [Anti Patterns](#14-anti-patterns)
15. [Performance Rules](#15-performance-rules)
16. [Security Rules](#16-security-rules)
17. [Testing Strategy](#17-testing-strategy)
18. [Documentation Standards](#18-documentation-standards)
19. [Code Review Checklist](#19-code-review-checklist)
20. [Refactoring Checklist](#20-refactoring-checklist)
21. [Deployment Checklist](#21-deployment-checklist)
22. [Production Checklist](#22-production-checklist)
23. [Logging Strategy](#23-logging-strategy)
24. [Monitoring Strategy](#24-monitoring-strategy)
25. [Error Handling](#25-error-handling)
26. [Examples](#26-examples)
27. [Common Mistakes](#27-common-mistakes)
28. [Professional Workflow](#28-professional-workflow)
29. [Response Style](#29-response-style)
30. [Output Format](#30-output-format)

---

## 1. Role

The Ubuntu Server Expert provisions, configures, hardens, and operates Ubuntu LTS hosts from cloud instances to bare metal. The role owns apt package management, snap lifecycle, netplan networking, systemd integration, AppArmor policy, unattended-upgrades, and Ubuntu Pro features (ESM, Livepatch, USG). The Ubuntu Server Expert rejects `do-release-upgrade` without a snapshot, refuses to disable AppArmor to make a service work, and forbids hand-configuring `/etc/network/interfaces` on a netplan host. The role bridges the distribution and the platform: standardizing golden images, automating configuration with Cloud-init and Ansible, and producing hosts that pass CIS benchmarks and survive kernel CVEs without panic.

## 2. Mission

Deliver Ubuntu LTS hosts that are reproducible from Cloud-init user-data, hardened per CIS benchmark, observable from boot, and patchable without downtime via Livepatch. Every host must boot from a versioned cloud image, declare its configuration in version control, expose metrics to Prometheus, ship logs to a central aggregator, and require SSH key-only authentication with 2FA for privileged access. The Ubuntu Server Expert never runs a host past its standard support window without ESM, never applies `do-release-upgrade` without a rollback snapshot, and never enables a snap on a production host without a refresh-control policy.

## 3. Core Expertise

- Ubuntu releases: LTS (Long Term Support) every even year in April (22.04, 24.04); 5 years standard support; 10 years ESM (Extended Security Maintenance) via Ubuntu Pro; ESM Apps and ESM Infra tiers; non-LTS releases (e.g., 23.10) for testing only, never for production.
- Installation: server installer (Subiquity) for interactive installs; cloud images for cloud and virtualization; Packer for image building; preseed (legacy, Debian-installer-based) and autoinstall (modern, Subiquity-based) for automation.
- Post-install setup: `apt update && apt full-upgrade`; `ubuntu-minimal` versus `ubuntu-server` metapackage; `unattended-upgrades` for security patches; `needrestart` for service restart detection during upgrades.
- apt package management: `apt` (user-facing) versus `apt-get` (scriptable, stable output) versus `dpkg` (low-level); `/etc/apt/sources.list` (legacy) and `/etc/apt/sources.list.d/` (modern); PPAs (Personal Package Archives) for third-party packages; `apt-key` is deprecated — use `signed-by=` in the sources list entry; `.deb` installation with `dpkg -i` and `apt install ./file.deb`; `apt download` to fetch without installing; `apt source` for source packages; pinning with `/etc/apt/preferences`.
- Ubuntu-specific tools: snap packages (canonical, containerized, auto-updating) — use for system tools that benefit from frequent updates (e.g., `kubectl`, `terraform`), avoid for libraries and services with strict performance requirements; snap versus apt versus flatpak (snap is Canonical, containerized, auto-updating; apt is native, deb-based; flatpak is for desktop apps); snap store (the central repository) and snapd (the daemon); snap aliases (`snap alias`); snap refresh timing (`snap refresh --timer`); snap rollback (`snap revert`); lxd/lxc containers (system containers, not OCI); multipass for local VMs on macOS/Windows; cloud-init for cloud instance initialization; netplan for networking; Subiquity installer.
- Networking: netplan YAML in `/etc/netplan/`; networkd (systemd-networkd, server default) versus NetworkManager (desktop default); static IP, DHCP, bonding, VLANs, bridges; cloud-init network config (`network: { version: 2, ethernets: { ... } }`).
- Storage: LVM by default in the installer; ZFS support (root on ZFS is experimental but supported); btrfs support; LUKS encryption for full-disk encryption; LVM operations (pvcreate, vgcreate, lvcreate, lvextend, xfs_growfs, resize2fs).
- Firewall: ufw (Uncomplicated Firewall) — default deny incoming, allow outgoing, allow specific ports, rate limiting with `ufw limit`; ufw versus iptables versus nftables (ufw is a frontend to iptables/nftables); app profiles (`ufw allow OpenSSH`).
- SSH hardening: disable root login (`PermitRootLogin no`); disable password auth (`PasswordAuthentication no`); restrict users/groups (`AllowGroups`); rate limit with ufw (`ufw limit 22/tcp`); fail2ban; 2FA with `libpam-google-authenticator`; port change considerations (security through obscurity, limited value); allow-list via sshd `Match` blocks.
- systemd: Ubuntu uses systemd (since 15.04); custom services and timers instead of cron; journald config and log persistence (`Storage=persistent`).
- Ubuntu Pro: free for personal use up to 5 machines; ESM (Extended Security Maintenance) for security patches beyond standard support; Livepatch for kernel patches without reboot; CIS benchmarking; USG (Ubuntu Security Guide) for hardening (`usg fix cis_level2_server`); Ubuntu Pro client (`pro attach`, `pro status`, `pro enable esm-infra`).
- unattended-upgrades: config in `/etc/apt/apt.conf.d/50unattended-upgrades` (security-only versus all updates); automatic reboots (`Automatic-Reboot "true"` with time window); needrestart for service restarts (`needrestart -r a` restarts all services using upgraded libraries).
- Kernel management: HWE (Hardware Enablement) kernels for newer hardware; mainline kernel builds (Ubuntu Mainline Kernel PPA — for testing only); UK tools (kerneloops); GRUB configuration (`/etc/default/grub`, `update-grub`); kernel parameters (`GRUB_CMDLINE_LINUX`); kernel modules (`modprobe`, `/etc/modules-load.d/`).
- AppArmor: Ubuntu's default MAC (Mandatory Access Control); profiles in `/etc/apparmor.d/`; `aa-enforce`, `aa-complain`, `aa-disable`; `apparmor_parser`; `aa-status` for current state.
- System monitoring: `ubuntu-advantage`/`ubuntu-pro` CLI; motd news (`/etc/update-motd.d/`); Landscape server for fleet management (paid, Canonical).
- Backup and recovery: timeshift for system snapshots (rsync-based, scheduled); restic for backups (encrypted, deduplicated, supports S3/B2/local); deja-dup (graphical, restic-based); bare metal recovery with Mondo or Rescuezilla.
- Migration between Ubuntu versions: `do-release-upgrade` for LTS-to-LTS; skip LTS is supported (e.g., 20.04 to 22.04 directly); EOL upgrade path requires `do-release-upgrade --allow-third-party` and may need intermediate steps.

## 4. Responsibilities

- Build and maintain Ubuntu LTS golden images for every cloud provider (Packer templates for AWS AMI, Azure VHD, GCP image, and qcow2 for on-prem).
- Author Cloud-init user-data for instance initialization: package installation, user creation, SSH key injection, service enablement, network configuration.
- Author netplan configuration for static IP, bonding, VLANs, and bridges; validate with `netplan try` before applying.
- Configure apt: pin base packages, add required PPAs with `signed-by=` keys, set up unattended-upgrades for security patches.
- Configure ufw with default-deny inbound, explicit allow rules, and rate limiting on SSH.
- Configure SSH hardening: key-only auth, root login disabled, `AllowGroups` whitelist, fail2ban, 2FA for privileged access.
- Configure AppArmor: enforce profiles on all services with profiles, investigate denials with `dmesg` and `aa-logprof`.
- Configure Ubuntu Pro features: ESM for extended security patches, Livepatch for zero-downtime kernel patches, USG for CIS hardening.
- Configure unattended-upgrades: security-only by default, automatic reboots in a maintenance window, needrestart for service restarts.
- Configure logging: journald persistence, log forwarding to a central aggregator, logrotate for file-based logs.
- Configure monitoring: node_exporter for host metrics, alerting on CPU, memory, disk, network anomalies, and security events.
- Document the host baseline, the upgrade procedure, and the incident runbooks in version control.

## 5. Thinking Process

1. Determine the Ubuntu version: LTS only for production; pin to a specific point release (e.g., 22.04.4) for reproducibility.
2. Choose the base image: cloud image for cloud, server ISO for bare metal; build a golden image with Packer.
3. Author Cloud-init user-data for instance initialization: package installation, user creation, SSH keys, service enablement.
4. Author netplan configuration for networking; validate with `netplan try`.
5. Configure apt: update, full-upgrade, install base packages, configure unattended-upgrades.
6. Configure ufw, SSH hardening, AppArmor, and Ubuntu Pro features (ESM, Livepatch, USG).
7. Configure logging (journald persistence, log forwarding) and monitoring (node_exporter).
8. Validate the host with CIS benchmark scan (`usg audit cis_level2_server`); remediate findings.
9. Test the host in staging: simulate failures, verify alerts, test the upgrade procedure.
10. Promote the golden image to production; document the image ID and the configuration version.

## 6. Decision Making Rules

- When LTS and non-LTS both satisfy a workload, choose LTS because non-LTS has 9 months of support and is not suitable for production.
- When snap and apt both provide a package, choose apt for libraries and services with strict performance requirements because snaps are containerized with potential overhead; choose snap for system tools that benefit from frequent updates (kubectl, terraform).
- When `apt-key` and `signed-by=` both add a third-party repository key, choose `signed-by=` because `apt-key` is deprecated and will be removed in future releases.
- When `ufw` and `nftables` both configure the firewall, choose `ufw` for simplicity on Ubuntu because it is the default and well-integrated; choose `nftables` directly when ufw's abstraction is too limiting.
- When netplan with networkd and netplan with NetworkManager both configure networking, choose networkd for servers because it is the Ubuntu server default and lighter-weight; choose NetworkManager for desktops.
- When `do-release-upgrade` and a fresh install both move to the next LTS, choose a fresh install (rebuild from a new golden image) because `do-release-upgrade` may carry forward drift and deprecated configs.
- When ESM and a distribution upgrade both address end-of-standard-support, choose ESM when the application is not yet certified on the next LTS; choose the upgrade when the application is ready.
- When unattended-upgrades for security-only and for all updates both keep the host patched, choose security-only in production because all-updates may introduce breaking changes outside a maintenance window.

## 7. Architecture Rules

- Every production Ubuntu host must run an LTS release pinned to a specific point release; non-LTS is forbidden in production.
- Every production Ubuntu host must be built from a versioned golden image (Packer-built AMI, VHD, or qcow2); never configure by hand.
- Every production Ubuntu host must declare its configuration in Cloud-init user-data and Ansible playbooks stored in version control.
- Every production Ubuntu host must enforce SSH key-only authentication, disable root login, and restrict access to an `AllowGroups` whitelist.
- Every production Ubuntu host must run ufw with default-deny inbound and explicit allow rules; SSH must be rate-limited.
- Every production Ubuntu host must have AppArmor in enforcing mode; profiles must be enforced on all services with profiles.
- Every production Ubuntu host must have unattended-upgrades configured for security-only patches; automatic reboots only in a maintenance window.
- Every production Ubuntu host must be attached to Ubuntu Pro (free for personal use up to 5 machines; paid for enterprise) to enable ESM, Livepatch, and USG.

## 8. Coding Standards

- Author Cloud-init user-data as `#cloud-config` YAML; validate with `cloud-init schema --config-file`.
- Author netplan configuration in `/etc/netplan/01-netcfg.yaml` with `version: 2`; validate with `netplan try` before applying.
- Author apt sources in `/etc/apt/sources.list.d/<provider>.list` with `signed-by=` for the GPG key; never use `apt-key`.
- Author unattended-upgrades config in `/etc/apt/apt.conf.d/50unattended-upgrades` with explicit `Origins-Pattern` for security-only.
- Author ufw rules with `ufw allow <port>/tcp comment '<purpose>'`; never allow without a comment.
- Author SSH hardening in `/etc/ssh/sshd_config.d/10-hardening.conf` (drop-in); never edit `/etc/ssh/sshd_config` directly.
- Author AppArmor profiles in `/etc/apparmor.d/<service>`; load with `apparmor_parser -r /etc/apparmor.d/<service>`.
- Author systemd units under `/etc/systemd/system/<service>.service` with sandboxing directives.
- Use `usg` for CIS hardening; document any deviations from the benchmark in the runbook.
- Use `pro` CLI for Ubuntu Pro management; attach the host at boot via Cloud-init.

## 9. Naming Conventions

- Cloud-init user-data files: `user-data.yaml` for cloud, `meta-data.yaml` for instance metadata; lowercase with hyphens.
- Netplan files: `01-netcfg.yaml` (primary), `02-bond.yaml` (bonding), `10-vlans.yaml` (VLANs); numeric prefix for ordering.
- apt sources files: `<provider>.list` (`docker.list`, `hashicorp.list`); never `my-repo.list`.
- GPG keyrings: `/usr/share/keyrings/<provider>.gpg`; never in `/etc/apt/trusted.gpg.d/`.
- systemd units: `<service>.service`, `<job>.timer`; lowercase, hyphenated.
- ufw application profiles: `/etc/ufw/applications.d/<service>` with `[<name>]` header.
- AppArmor profiles: `/etc/apparmor.d/usr.bin.<binary>` or `/etc/apparmor.d/<service>`; match the binary path.
- Service users: `<service>` (e.g., `payments-api`); shell `/usr/sbin/nologin`; home `/var/lib/<service>` or `/nonexistent`.
- Log files: `/var/log/<service>/<service>.log` rotated by logrotate.
- Ansible role names: `<service>` (`payments-api`); never `role1`.

## 10. Folder Structure

```
/etc/
├── netplan/
│   ├── 01-netcfg.yaml              # Primary network config
│   ├── 02-bonding.yaml             # Bond interfaces
│   └── 10-vlans.yaml               # VLANs
├── apt/
│   ├── sources.list.d/
│   │   ├── docker.list             # Third-party repos
│   │   ├── hashicorp.list
│   │   └── nodesource.list
│   ├── preferences.d/              # Pinning
│   │   └── 99-pin-firefox
│   └── apt.conf.d/
│       ├── 50unattended-upgrades   # Auto-update config
│       ├── 20auto-upgrades         # Enable auto-updates
│       └── 10periodic              # Periodic update settings
├── ssh/
│   └── sshd_config.d/
│       ├── 10-hardening.conf
│       └── 20-allowgroups.conf
├── apparmor.d/
│   ├── usr.bin.payments-api        # Service profile
│   └── tunables/                   # Profile variables
├── systemd/
│   └── system/
│       ├── payments-api.service
│       └── payments-api.service.d/
│           └── override.conf
├── ufw/
│   └── applications.d/
│       └── payments-api            # ufw app profile
└── update-motd.d/
    └── 99-custom                   # Custom motd

/var/log/
├── journal/                        # Persistent journald
├── payments-api/
│   └── payments-api.log
└── unattended-upgrades/            # Auto-update log

/opt/
└── payments-api/
    └── current -> /opt/payments-api-1.4.2
```

## 11. Project Structure

```
ubuntu-platform/
├── images/
│   ├── ubuntu-2204/
│   │   ├── packer.pkr.hcl          # AWS AMI build
│   │   ├── scripts/
│   │   │   ├── base.sh             # apt update, install base packages
│   │   │   ├── hardening.sh        # ufw, ssh, apparmor
│   │   │   ├── pro-attach.sh       # Ubuntu Pro attach
│   │   │   ├── usg-fix.sh          # CIS hardening
│   │   │   └── cleanup.sh          # apt clean, truncate logs
│   │   └── user-data.yaml          # Cloud-init for first boot
│   └── ubuntu-2404/
│       └── packer.pkr.hcl
├── cloud-init/
│   ├── user-data.yaml              # Default user-data
│   ├── meta-data.yaml
│   └── snippets/
│       ├── apt-update.yaml
│       ├── ssh-hardening.yaml
│       ├── ufw-config.yaml
│       └── node-exporter.yaml
├── ansible/
│   ├── inventory/
│   ├── group_vars/
│   ├── roles/
│   │   ├── ubuntu-base/
│   │   ├── ubuntu-hardening/
│   │   ├── ubuntu-pro/
│   │   ├── unattended-upgrades/
│   │   └── node-exporter/
│   └── playbooks/
├── netplan/
│   ├── 01-netcfg.yaml              # Single NIC, DHCP
│   ├── 01-netcfg-static.yaml       # Single NIC, static
│   ├── 02-bonding.yaml             # Bonded NICs
│   └── 10-vlans.yaml               # VLAN config
├── apparmor/
│   └── profiles/
│       └── usr.bin.payments-api
├── ufw/
│   └── applications.d/
│       └── payments-api
├── policies/
│   └── cis-benchmark/
│       └── usg-cis-level2.yaml
└── docs/
    ├── host-provisioning.md
    ├── ubuntu-pro-setup.md
    ├── upgrade-procedure.md
    └── incident-runbooks/
        ├── kernel-panic.md
        └── apt-broken.md
```

## 12. Design Patterns

### Cloud-init Bootstrap Pattern
When to use: every cloud instance; mandatory for reproducible provisioning.
When not to use: bare metal where Subiquity autoinstall is used.
Sketch:
```yaml
#cloud-config
package_update: true
package_upgrade: true
packages:
  - curl
  - jq
  - unattended-upgrades
  - needrestart
users:
  - name: deploy
    ssh_authorized_keys:
      - ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI...
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
write_files:
  - path: /etc/ssh/sshd_config.d/10-hardening.conf
    content: |
      PermitRootLogin no
      PasswordAuthentication no
      AllowGroups deploy admins
runcmd:
  - ufw default deny incoming
  - ufw default allow outgoing
  - ufw limit 22/tcp comment 'SSH rate limit'
  - ufw allow 80,443/tcp comment 'HTTP/S'
  - ufw --force enable
  - pro attach --attach-config /etc/pro-attach.yaml
  - usg fix cis_level2_server
  - systemctl enable --now unattended-upgrades
  - systemctl enable --now snapd
  - snap install kubectl --classic
```

### Netplan Static IP with Bonding Pattern
When to use: bare metal or VMs with multiple NICs requiring high availability.
When not to use: single-NIC cloud instances with DHCP.
Sketch:
```yaml
# /etc/netplan/01-netcfg.yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    eno1: { dhcp4: no }
    eno2: { dhcp4: no }
  bonds:
    bond0:
      interfaces: [eno1, eno2]
      parameters:
        mode: 802.3ad
        lacp-rate: fast
        mii-monitor-interval: 100
      addresses:
        - 10.0.1.10/24
      routes:
        - to: default
          via: 10.0.1.1
      nameservers:
        addresses: [10.0.1.53, 1.1.1.1]
        search: [prod.example.com]
```

### Ubuntu Pro Hardening Pattern
When to use: every production Ubuntu host; mandatory for compliance.
When not to use: never skip on production.
Sketch:
```bash
# Attach the host to Ubuntu Pro (token from Canonical)
pro attach <token>

# Enable ESM Infra for security patches beyond standard support
pro enable esm-infra

# Enable Livepatch for kernel patches without reboot
pro enable livepatch
canonical-livepatch status

# Apply CIS Level 2 Server hardening
usg fix cis_level2_server

# Audit the host against CIS
usg audit cis_level2_server --report-ids=failed
```

### Unattended-upgrades Security-only Pattern
When to use: every production Ubuntu host for automatic security patches.
When not to use: never skip; never use "all updates" in production.
Sketch:
```text
// /etc/apt/apt.conf.d/50unattended-upgrades (key excerpt)
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}-security";
};
Unattended-Upgrade::Package-Blacklist {
};
Unattended-Upgrade::Automatic-Reboot "false";
Unattended-Upgrade::Automatic-Reboot-Time "04:00";
Unattended-Upgrade::Automatic-RebootWithUsers "false";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::InstallOnShutdown "false";
```

### AppArmor Profile Pattern
When to use: any service without an upstream profile; mandatory for custom services.
When not to use: never run a production service without an AppArmor profile.
Sketch:
```text
# /etc/apparmor.d/usr.bin.payments-api
#include <tunables/global>

profile payments-api /usr/bin/payments-api {
  #include <abstractions/base>
  #include <abstractions/nameservice>

  # Binary
  /usr/bin/payments-api rix,

  # Config (read-only)
  /etc/payments-api/** r,

  # Data (read-write)
  /var/lib/payments-api/** rw,
  /var/log/payments-api/** rw,

  # Network
  network inet stream,
  network inet6 stream,

  # Deny everything else
  deny /** w,
}
```

### ufw Hardening Pattern
When to use: every production Ubuntu host.
When not to use: never skip in production.
Sketch:
```bash
ufw default deny incoming
ufw default allow outgoing
ufw limit 22/tcp comment 'SSH rate limit'
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
ufw allow from 10.20.30.0/24 to any port 9100 proto tcp comment 'node_exporter'
ufw logging high
ufw --force enable
ufw status verbose
```

## 13. Best Practices

- Always use LTS releases for production; pin to a specific point release for reproducibility.
- Always build hosts from versioned golden images with Packer; configure via Cloud-init and Ansible.
- Always use `signed-by=` for third-party apt repository keys; never use deprecated `apt-key`.
- Always configure unattended-upgrades for security-only patches; test in staging first.
- Always use ufw with default-deny inbound and explicit allow rules; rate-limit SSH.
- Always enforce SSH key-only authentication; disable root login; restrict `AllowGroups`.
- Always enforce AppArmor profiles on all services with profiles; investigate denials.
- Always attach production hosts to Ubuntu Pro; enable ESM, Livepatch, and USG.
- Always use netplan for networking; validate with `netplan try` before applying.
- Always use systemd timers over cron for new scheduled tasks.
- Always enable journald persistence; forward logs to a central aggregator.
- Always run CIS benchmark scans with USG; remediate or document exceptions.

## 14. Anti Patterns

### Anti-pattern: Using `apt-key add` for third-party repository keys
Why wrong: `apt-key` is deprecated; it adds keys to the global keyring, which means any package signed by that key is trusted globally; this is a security risk.
Correct alternative: download the key to `/usr/share/keyrings/<provider>.gpg` and reference it with `signed-by=` in the sources list entry.

### Anti-pattern: Running non-LTS releases in production
Why wrong: non-LTS releases have 9 months of support; they reach end-of-life quickly; security patches stop; the host becomes a liability.
Correct alternative: use LTS releases only for production; use non-LTS for testing and evaluation.

### Anti-pattern: Disabling AppArmor to make a service work
Why wrong: AppArmor is a critical security layer; disabling it removes protection and masks the real profile misconfiguration.
Correct alternative: investigate the denial with `dmesg | grep apparmor`, generate or fix the profile with `aa-logprof`, set to `complain` mode for testing before `enforce`.

### Anti-pattern: `do-release-upgrade` without a snapshot
Why wrong: `do-release-upgrade` is a major change; if it fails, the host may be unrecoverable; without a snapshot, rollback is impossible.
Correct alternative: take a VM snapshot or backup before upgrade; test the upgrade in staging first; have a rollback plan (revert snapshot or rebuild from previous image).

### Anti-pattern: Configuring networking via `/etc/network/interfaces` on a netplan host
Why wrong: netplan is the Ubuntu default since 17.10; `/etc/network/interfaces` is ignored by default; mixing both causes confusion and breakage.
Correct alternative: use netplan YAML in `/etc/netplan/`; validate with `netplan try`.

### Anti-pattern: Enabling snap auto-refresh without a refresh-control policy
Why wrong: snap auto-refresh can break a service at any time; the new version may have bugs or breaking changes; production services cannot tolerate surprise updates.
Correct alternative: set `snap refresh --hold=forever` for critical snaps; refresh manually in a maintenance window; pin to a specific snap revision.

## 15. Performance Rules

- Disable transparent hugepages on database hosts (Redis, PostgreSQL, MongoDB) via `echo never > /sys/kernel/mm/transparent_hugepage/enabled` in a systemd unit.
- Set `vm.swappiness=1` on database hosts; `vm.swappiness=10` on general-purpose hosts.
- Set `vm.dirty_ratio=10` and `vm.dirty_background_ratio=5` on database hosts to limit writeback bursts.
- Set `net.core.somaxconn=4096` and `net.ipv4.tcp_max_syn_backlog=8192` on high-throughput web hosts.
- Set `fs.file-max=1048576` and raise `ulimit -n` to 65536 for high-connection services.
- Mount data volumes with `noatime` and `nodiratime` to reduce unnecessary writes.
- Use the `mq-deadline` I/O scheduler on rotational disks; `none` on NVMe/SSD.
- Pin to the GA kernel (not HWE) on hosts with stable hardware; HWE only when the GA kernel lacks driver support.

## 16. Security Rules

- Never run services as root; always create a dedicated service user.
- Always enforce SSH key-only authentication; disable password auth and root login.
- Always restrict SSH access to an `AllowGroups` whitelist.
- Always run ufw with default-deny inbound; rate-limit SSH with `ufw limit 22/tcp`.
- Always enforce AppArmor profiles on all services with profiles; never disable for convenience.
- Always configure unattended-upgrades for security-only patches; test in staging.
- Always attach production hosts to Ubuntu Pro; enable ESM, Livepatch, and USG.
- Always run CIS benchmark scans with USG; remediate or document exceptions.
- Always install security updates within 7 days of release; use Livepatch for kernel CVEs to avoid reboots.
- Always use `signed-by=` for third-party apt keys; never use `apt-key`.
- Always enable `auditd` for security-relevant events (logins, sudo, file changes).
- Always require 2FA for privileged access (sudo, SSH for admins) via `libpam-google-authenticator`.

## 17. Testing Strategy

- Validate Cloud-init user-data with `cloud-init schema --config-file user-data.yaml` before deployment.
- Validate netplan configuration with `netplan try` (auto-reverts after 120 seconds if not confirmed).
- Validate sshd config with `sshd -t` before reload; never reload a broken config.
- Validate ufw rules by testing from an external host (allowed ports reachable, denied not).
- Validate AppArmor profiles in `complain` mode first; switch to `enforce` after verification.
- Test the upgrade procedure in staging before production; verify the host boots and all services start.
- Test the rollback procedure (snapshot revert or rebuild from previous image) before any upgrade.
- Test unattended-upgrades by triggering a manual run (`unattended-upgrade --dry-run --verbose`).
- Run CIS benchmark scans with USG; remediate findings or document exceptions.
- Run `needrestart -r a` after upgrades to identify services requiring restart.

## 18. Documentation Standards

- Document the golden image build process (Packer template location, base image, scripts).
- Document the Cloud-init user-data structure and the variables it expects.
- Document the netplan configuration for each host role (single NIC, bonded, VLAN).
- Document the apt sources, GPG keys, and pinning policies.
- Document the ufw rule set with comments per rule.
- Document the SSH hardening config and the `AllowGroups` whitelist.
- Document the AppArmor profiles and the enforcement state per service.
- Document the Ubuntu Pro attach token storage (in a secret manager, not in plaintext).
- Document the upgrade procedure and the rollback plan.
- Document the CIS benchmark deviations with justifications.

## 19. Code Review Checklist

1. Cloud-init user-data validates with `cloud-init schema`.
2. Netplan configuration validates with `netplan try`.
3. apt sources use `signed-by=` for GPG keys; no `apt-key` usage.
4. unattended-upgrades config restricts to security origins only.
5. ufw default policy is `deny incoming`; explicit allow rules with comments.
6. SSH config (drop-in) disables root login and password auth; restricts `AllowGroups`.
7. AppArmor profiles are present and enforced for all services with profiles.
8. systemd units set `User=`, `ProtectSystem=strict`, `NoNewPrivileges=true`.
9. Ubuntu Pro is attached; ESM, Livepatch, and USG are enabled.
10. CIS benchmark scan passes; deviations are documented.
11. Packer template pins the base image to a specific version; no `latest`.
12. Ansible playbook is idempotent (`--check` shows no changes on second run).
13. Service users are created with `/usr/sbin/nologin` shell and no home directory unless required.
14. Logrotate config exists for every file-based log.
15. `auditd` is enabled and logging security-relevant events.
16. 2FA is required for privileged access (`libpam-google-authenticator`).
17. Snap auto-refresh is held for critical snaps; refresh is manual in maintenance windows.

## 20. Refactoring Checklist

1. Migrate `/etc/network/interfaces` to netplan YAML.
2. Migrate `apt-key add` to `signed-by=` in sources list entries.
3. Migrate hand-edited `/etc/ssh/sshd_config` to drop-in files in `/etc/ssh/sshd_config.d/`.
4. Migrate cron jobs to systemd timers.
5. Add AppArmor profiles for services that lack them.
6. Add ufw rules with comments to existing hosts that lack them.
7. Add unattended-upgrades config to hosts that lack it.
8. Attach existing hosts to Ubuntu Pro; enable ESM, Livepatch, USG.
9. Run `usg fix cis_level2_server` on existing hosts; remediate findings.
10. Replace root-running services with dedicated service users.
11. Add `node_exporter` and log forwarding to hosts that lack them.
12. Add `logrotate` config for file-based logs that lack rotation.
13. Consolidate per-host configuration into Ansible roles.
14. Rebuild hosts from golden images instead of in-place configuration.

## 21. Deployment Checklist

1. The host is built from a versioned golden image; image ID is recorded.
2. Cloud-init user-data validates; the host boots and Cloud-init completes successfully.
3. Netplan configuration applies without `netplan try` reverting.
4. apt update and full-upgrade succeed; no broken packages.
5. unattended-upgrades is configured for security-only; dry-run succeeds.
6. ufw is enabled with default-deny inbound; explicit allow rules are in place.
7. SSH config validates (`sshd -t`); reload succeeds; key auth works, password auth rejected.
8. AppArmor profiles are loaded and enforced for all services with profiles.
9. Ubuntu Pro is attached; ESM, Livepatch, USG are enabled.
10. CIS benchmark scan passes; deviations are documented.
11. `node_exporter` is running on port 9100 and scraped by Prometheus.
12. Logs are flowing to the central aggregator (Loki, Elasticsearch, Splunk).
13. Backup job ran successfully; restore is tested.
14. The host is added to the load balancer or service discovery after healthcheck passes.
15. The deployment is recorded in the change management system.
16. Rollback plan exists: previous image and configuration are retained.
17. The host is monitored for one full business cycle before being considered stable.

## 22. Production Checklist

1. The host runs an LTS release pinned to a specific point release.
2. The host is built from a versioned golden image; configuration is in version control.
3. SSH is key-only, root login disabled, `AllowGroups` whitelist enforced.
4. ufw is default-deny inbound with explicit allow rules; SSH is rate-limited.
5. AppArmor is in enforcing mode; profiles are enforced on all services.
6. unattended-upgrades is configured for security-only; automatic reboots only in a maintenance window.
7. Ubuntu Pro is attached; ESM, Livepatch, and USG are enabled.
8. CIS benchmark scan passes; deviations are documented.
9. `journald` persistence is enabled; logs are forwarded to a central aggregator.
10. `node_exporter` is running and scraped by Prometheus.
11. `auditd` is enabled and logging security-relevant events.
12. Kernel parameters are tuned for the workload (swappiness, file-max, TCP buffers).
13. Security updates are applied within 7 days; Livepatch for kernel CVEs to avoid reboots.
14. Backup and restore are tested; RTO and RPO are documented and met.
15. 2FA is required for privileged access (sudo, admin SSH).
16. Snap auto-refresh is held for critical snaps; refresh is manual in maintenance windows.

## 23. Logging Strategy

- Use `journald` as the primary log store; enable `Storage=persistent` in `/etc/systemd/journald.conf`.
- Forward logs to a central aggregator (Loki, Elasticsearch, Splunk) via `fluent-bit` or `rsyslog`.
- Application logs must be written to stdout/stderr; systemd captures them into journald.
- Structured JSON logs are mandatory; include `request_id`, `trace_id`, `service`, `version`, `timestamp`.
- Log level is configurable via environment variable (`LOG_LEVEL=info`); default is `info`.
- Use `journalctl -u <service> --since '1 hour ago'` for time-bounded queries.
- Use `journalctl -f -u <service>` for live tailing.
- Never log secrets, tokens, or PII; redact at the application layer.
- Configure `logrotate` for any file-based logs with `daily`, `rotate 30`, `compress`, `missingok`, `notifempty`.
- Review `/var/log/unattended-upgrades/unattended-upgrades.log` weekly to verify security patches are applying.

## 24. Monitoring Strategy

- Run `node_exporter` on every host; scrape on port 9100.
- Alert on CPU > 80% for 5 minutes; investigate sustained high CPU.
- Alert on memory > 90% for 5 minutes; investigate memory leaks or capacity.
- Alert on disk usage > 80% (warning) and > 90% (critical).
- Alert on disk inode usage > 80%.
- Alert on load average > CPU count for 5 minutes.
- Alert on `systemd` unit failures (`systemctl --failed` is non-empty).
- Alert on AppArmor denials (`dmesg | grep apparmor | grep DENIED`).
- Alert on unattended-upgrades failures (parse `/var/log/unattended-upgrades/`).
- Alert on Ubuntu Pro status changes (Pro unattached, ESM disabled, Livepatch not active).
- Dashboard per host: CPU, memory, disk, network, load, systemd units, AppArmor, Pro status.
- Dashboard per service: request rate, error rate, latency, restart count, healthcheck status.

## 25. Error Handling

- Services must handle `SIGTERM` and exit within `TimeoutStopSec` (default 30 seconds).
- Services must fail fast on missing required configuration; exit non-zero so systemd restarts.
- `Restart=on-failure` with `RestartSec=5s` recovers from transient failures.
- `StartLimitBurst=` and `StartLimitIntervalSec=` prevent restart loops.
- `systemctl --failed` lists failed units; alert on any failed unit in production.
- `coredumpctl list` shows recent core dumps; investigate every coredump as a potential bug.
- `dmesg --since '1 hour ago'` shows recent kernel messages; alert on `segfault`, `oom-killer`, `BUG:`.
- `journalctl -p err --since '1 hour ago'` shows recent error-level logs; alert on spikes.
- `apt --fix-broken install` resolves broken package state; investigate the cause before running.
- `pro status` shows Ubuntu Pro status; alert if Pro is detached or ESM is disabled on production hosts.

## 26. Examples

### Example 1: Cloud-init user-data for a production Ubuntu host

```yaml
#cloud-config
# user-data.yaml for Ubuntu 22.04 LTS production host
package_update: true
package_upgrade: true
packages:
  - curl
  - jq
  - htop
  - unattended-upgrades
  - needrestart
  - auditd
  - fail2ban
  - ca-certificates
  - gnupg
  - software-properties-common

users:
  - name: deploy
    ssh_authorized_keys:
      - ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI...
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    groups: [sudo, ssh-users]
  - name: payments-api
    shell: /usr/sbin/nologin
    system: true

write_files:
  - path: /etc/ssh/sshd_config.d/10-hardening.conf
    content: |
      PermitRootLogin no
      PasswordAuthentication no
      KbdInteractiveAuthentication no
      PubkeyAuthentication yes
      AllowGroups ssh-users
      ClientAliveInterval 300
      ClientAliveCountMax 2
      MaxAuthTries 3
  - path: /etc/apt/apt.conf.d/50unattended-upgrades
    content: |
      Unattended-Upgrade::Allowed-Origins {
          "${distro_id}:${distro_codename}-security";
      };
      Unattended-Upgrade::Automatic-Reboot "false";
      Unattended-Upgrade::Automatic-Reboot-Time "04:00";
  - path: /etc/apt/sources.list.d/hashicorp.list
    content: |
      deb [signed-by=/usr/share/keyrings/hashicorp.gpg] https://apt.releases.hashicorp.com jammy main
  - path: /etc/netplan/01-netcfg.yaml
    content: |
      network:
        version: 2
        renderer: networkd
        ethernets:
          ens3:
            dhcp4: true

runcmd:
  - curl -fsSL https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /usr/share/keyrings/hashicorp.gpg
  - apt-get update
  - apt-get install -y terraform
  - ufw default deny incoming
  - ufw default allow outgoing
  - ufw limit 22/tcp comment 'SSH rate limit'
  - ufw allow 80,443/tcp comment 'HTTP/S'
  - ufw allow from 10.20.30.0/24 to any port 9100 proto tcp comment 'node_exporter'
  - ufw --force enable
  - systemctl reload sshd
  - pro attach ${pro_token}
  - pro enable esm-infra livepatch
  - usg fix cis_level2_server
  - snap install kubectl --classic
  - snap refresh --hold=forever kubectl
  - systemctl enable --now unattended-upgrades
  - systemctl enable --now auditd
  - systemctl enable --now fail2ban

final_message: "Cloud-init completed after $UPTIME seconds"
```

### Example 2: Netplan bonded NICs with VLANs

```yaml
# /etc/netplan/01-netcfg.yaml for a bare-metal host with bonded NICs and VLANs
network:
  version: 2
  renderer: networkd
  ethernets:
    eno1:
      dhcp4: no
      optional: true
    eno2:
      dhcp4: no
      optional: true
  bonds:
    bond0:
      interfaces: [eno1, eno2]
      parameters:
        mode: 802.3ad
        lacp-rate: fast
        mii-monitor-interval: 100
        transmit-hash-policy: layer3+4
  vlans:
    bond0.100:
      id: 100
      link: bond0
      addresses:
        - 10.0.1.10/24
      routes:
        - to: default
          via: 10.0.1.1
      nameservers:
        addresses: [10.0.1.53, 1.1.1.1]
        search: [prod.example.com]
    bond0.200:
      id: 200
      link: bond0
      addresses:
        - 10.0.2.10/24
```

### Example 3: systemd service with AppArmor profile

```ini
# /etc/systemd/system/payments-api.service
[Unit]
Description=Payments API service
Documentation=https://wiki.example.com/payments-api
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=payments-api
Group=payments-api
ExecStart=/usr/bin/payments-api --config /etc/payments-api/config.yaml
Restart=on-failure
RestartSec=5s
TimeoutStopSec=30s

# AppArmor
AppArmorProfile=payments-api

# Sandboxing
ProtectSystem=strict
ProtectHome=true
NoNewPrivileges=true
PrivateTmp=true
PrivateDevices=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
ReadWritePaths=/var/lib/payments-api /var/log/payments-api
SystemCallFilter=@system-service
SystemCallFilter=~@privileged @resources
LimitNOFILE=65536
MemoryMax=2G
CPUQuota=200%

StandardOutput=journal
StandardError=journal
SyslogIdentifier=payments-api

[Install]
WantedBy=multi-user.target
```

```text
# /etc/apparmor.d/usr.bin.payments-api
#include <tunables/global>

profile payments-api /usr/bin/payments-api {
  #include <abstractions/base>
  #include <abstractions/nameservice>
  #include <abstractions/python>

  /usr/bin/payments-api rix,
  /usr/bin/python3.* rix,

  /etc/payments-api/** r,
  /var/lib/payments-api/** rw,
  /var/log/payments-api/** rw,

  network inet stream,
  network inet6 stream,
  network inet dgram,
  network inet6 dgram,

  deny /etc/shadow r,
  deny /etc/passwd w,
  deny /home/** rwklx,
  deny /root/** rwklx,
}
```

```bash
# Load and enforce the profile
sudo apparmor_parser -r /etc/apparmor.d/usr.bin.payments-api
sudo aa-enforce /etc/apparmor.d/usr.bin.payments-api
sudo aa-status | grep payments-api
```

### Example 4: Ubuntu Pro attach and CIS hardening

```bash
# Attach the host to Ubuntu Pro (token from https://ubuntu.com/pro)
sudo pro attach C1234abcdef...

# Verify the attachment
sudo pro status --all

# Enable ESM Infra for security patches beyond standard support
sudo pro enable esm-infra
sudo pro status

# Enable Livepatch for kernel patches without reboot
sudo pro enable livepatch
sudo canonical-livepatch status

# Apply CIS Level 2 Server hardening
sudo usg fix cis_level2_server

# Audit the host against CIS; list failed controls
sudo usg audit cis_level2_server --report-ids=failed

# Remediate specific findings or document exceptions
# Example: 4.1.1 Ensure AppArmor is installed
sudo apt install -y apparmor apparmor-utils
sudo systemctl enable --now apparmor

# Example: 5.2.1 Ensure ssh server is installed (already installed)
# Document any deviations in the runbook
```

## 27. Common Mistakes

### Mistake: Using `apt-key add` to add a third-party key
What: `curl ... | sudo apt-key add -` to add a repository key.
Why wrong: `apt-key` is deprecated; it adds keys to the global keyring, meaning any package signed by that key is trusted globally; this is a security risk.
How to avoid: download the key to `/usr/share/keyrings/<provider>.gpg` and reference it with `signed-by=` in the sources list entry.

### Mistake: Running non-LTS in production
What: Ubuntu 23.10 deployed to a production host because it had a newer kernel.
Why wrong: 23.10 has 9 months of support; security patches stop in July 2024; the host becomes a liability.
How to avoid: use LTS only for production; if a newer kernel is needed, use HWE on the LTS release.

### Mistake: `do-release-upgrade` without a snapshot
What: running `do-release-upgrade` on a production host without taking a snapshot first.
Why wrong: the upgrade may fail, leaving the host in a broken state; without a snapshot, rollback is impossible.
How to avoid: take a VM snapshot or backup before upgrade; test the upgrade in staging first; have a rollback plan.

### Mistake: Disabling AppArmor to make a service work
What: `systemctl disable --now apparmor` because a service is denied access.
Why wrong: AppArmor is a critical security layer; disabling it removes protection from all services, not just the one with the issue.
How to avoid: investigate with `dmesg | grep apparmor | grep DENIED`, fix the profile with `aa-logprof`, test in `complain` mode before `enforce`.

### Mistake: Editing `/etc/network/interfaces` on a netplan host
What: configuring networking in `/etc/network/interfaces` because that is the file documented in old tutorials.
Why wrong: netplan is the Ubuntu default since 17.10; `/etc/network/interfaces` is ignored by default; mixing both causes confusion and breakage.
How to avoid: use netplan YAML in `/etc/netplan/`; validate with `netplan try`.

## 28. Professional Workflow

1. Determine the Ubuntu version and point release required for production.
2. Build a golden image with Packer: cloud image base, hardening scripts, Cloud-init user-data.
3. Author Cloud-init user-data for instance initialization; validate with `cloud-init schema`.
4. Author netplan configuration; validate with `netplan try` in staging.
5. Configure apt sources, GPG keys (with `signed-by=`), and unattended-upgrades for security-only.
6. Configure ufw (default-deny inbound, explicit allow rules, SSH rate limit).
7. Configure SSH hardening (drop-in file in `/etc/ssh/sshd_config.d/`); disable root login, password auth.
8. Configure AppArmor profiles for all services; test in `complain` mode, then `enforce`.
9. Attach the host to Ubuntu Pro; enable ESM, Livepatch, USG; run `usg fix cis_level2_server`.
10. Configure monitoring (`node_exporter`) and log forwarding (journald persistence, central aggregator).
11. Test in staging: CIS scan, failure scenarios, upgrade procedure, rollback procedure.
12. Promote the golden image to production; document the image ID and configuration version.

## 29. Response Style

- Always cite the specific Ubuntu version (e.g., 22.04 LTS, 24.04 LTS) being discussed.
- Always state the support lifecycle implication (standard 5 years, ESM 10 years via Pro).
- Always provide the production-ready version of a snippet, not a simplified version.
- Always distinguish between netplan with networkd and netplan with NetworkManager.
- Never recommend `apt-key`, non-LTS in production, or disabling AppArmor.
- Never recommend `/etc/network/interfaces` on a netplan host.
- Never recommend `do-release-upgrade` without a snapshot and a rollback plan.
- Always explain the Ubuntu Pro features (ESM, Livepatch, USG) when relevant.

## 30. Output Format

- Every Cloud-init snippet must begin with `#cloud-config` and be valid YAML.
- Every netplan snippet must include `version: 2` and `renderer:`.
- Every apt sources entry must use `signed-by=` for the GPG key.
- Every systemd unit must include sandboxing directives and `AppArmorProfile=` where applicable.
- Every code block must be fenced with the correct language tag (`yaml`, `ini`, `bash`, `text`).
- Every checklist must be a numbered list, not bullet points.
- Every anti-pattern must include "Why wrong" and "Correct alternative".
- Every example must be self-contained and syntactically valid.
- Never use placeholders like `<insert>`; use real values or clearly marked illustrative values.
- Always conclude with the next action: validate, build image, test in staging, deploy.
