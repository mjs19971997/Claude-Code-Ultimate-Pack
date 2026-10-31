# Performance, Execution Environments and Platforms

Controller tuning, strategies, fact caching, async tasks, ansible-navigator, ansible-builder execution environments, AWX and Automation Platform, and Windows hosts. Settings were confirmed with `ansible-config` on ansible-core 2.21.5; ansible-builder 3.2.0 and ansible-navigator 26.10.0 were run in a virtual environment (2026-10).

## Contents

1. [Measure first](#1-measure-first)
2. [ansible.cfg tuning](#2-ansiblecfg-tuning)
3. [Strategies and parallelism](#3-strategies-and-parallelism)
4. [Facts and caching](#4-facts-and-caching)
5. [Async and long tasks](#5-async-and-long-tasks)
6. [Mitogen](#6-mitogen)
7. [ansible-navigator](#7-ansible-navigator)
8. [Execution environments](#8-execution-environments)
9. [AWX and Automation Platform](#9-awx-and-automation-platform)
10. [Windows hosts](#10-windows-hosts)

## 1. Measure first

- Enable a timing callback: `callbacks_enabled = ansible.posix.profile_tasks, ansible.posix.timer` in `[defaults]` (the callbacks ship in the `ansible.posix` collection; confirm with `ansible-doc -t callback -l`).
- Typical costs: fact gathering per host, many small tasks (each is an SSH round trip), loops that call a module once per item, slow `command` probes, and `serial` batches that are too small.
- Check where time goes before changing settings: run with `--limit` on one host, then on ten, and compare. If time grows linearly with host count, raise `forks`; if it is dominated by task count, reduce tasks and enable pipelining.
- `ansible-config dump --only-changed` shows the settings in effect and where each was set.

## 2. ansible.cfg tuning

```ini
[defaults]
forks = 20
gathering = smart
interpreter_python = auto_silent
result_format = yaml
fact_caching = jsonfile
fact_caching_connection = .cache/facts
fact_caching_timeout = 7200

[ssh_connection]
pipelining = True
ssh_args = -o ControlMaster=auto -o ControlPersist=60s
```

- `forks`: parallel host workers; the default is low (5). Size it to controller memory and CPU, since each fork is a process. Values of 20 to 100 are common; raise gradually.
- `pipelining = True` (default `False`, confirmed): runs modules through the SSH session without copying a file first, which cuts round trips. It conflicts with `requiretty` in sudoers on old systems; modern distributions do not set it by default.
- `ControlMaster`/`ControlPersist` reuse one SSH connection per host. Keep the `ControlPath` short on systems with long home paths (Unix socket limit).
- `interpreter_python = auto_silent` (or an explicit path per group) avoids discovery warnings. Discovery mode names `auto_legacy` were removed in 2.21; use `auto`, `auto_silent` or a path.
- `gathering = smart` gathers facts once per host and reuses cached facts; `explicit` gathers only when the play asks.
- `result_format = yaml` makes task output readable.
- `host_key_checking` stays `True` (the default). Distribute `known_hosts` entries with a task or configuration management instead of disabling it.
- `timeout` (connection timeout, default 10 seconds) can be raised for slow networks; prefer `ansible_ssh_common_args` with `ConnectTimeout` per group when only some hosts are slow.
- Keep `ansible.cfg` in the project root; ansible-core ignores a world-writable directory's cfg for safety, so check permissions in CI containers.
- Environment variables (`ANSIBLE_FORKS`, `ANSIBLE_PIPELINING`) override the file and suit CI and AWX.

## 3. Strategies and parallelism

- `linear` (default): every host finishes task N before any starts N+1. Predictable output; slowest host sets the pace.
- `free`: each host proceeds independently. Use when tasks are independent across hosts. Output order is non-deterministic and cross-host `run_once` or `delegate_to` patterns are harder to reason about.
- `host_pinned`: like `free` but a worker stays bound to a host until its play finishes.
- `debug`: interactive debugging strategy, for development only.
- Strategy plugins outside `ansible.builtin` are deprecated as of 2.19, with no backwards-compatibility promise and a stated plan to remove the ability to load external ones.
- `serial` splits a play into batches for safety; it reduces parallelism on purpose. Use `[1, 5, "100%"]` style lists for canary then fan-out.
- `throttle: N` on a task or block limits concurrent executions of that task regardless of `forks`, which protects a shared backend (package mirror, API).
- `run_once: true` with `delegate_to` runs a task one time; with `serial` it runs once per batch.
- `order: shuffle` randomises host order within a play; `inventory` (default) keeps inventory order.
- Limit blast radius with `--limit`, `max_fail_percentage` and `any_errors_fatal` rather than low `forks`.

## 4. Facts and caching

- `gather_facts: false` on plays that do not use facts is the largest single saving per host. Gather a subset otherwise: `gather_subset: ['!all', '!min', 'network']`, or call `ansible.builtin.setup` with `filter:`.
- `gathering = smart` plus a persistent cache (`jsonfile`, `redis` or another installed cache plugin; check `ansible-doc -t cache -l`) reuses facts across runs until `fact_caching_timeout` expires.
- Cached facts can be stale. Refresh with `--flush-cache` or a play with `gather_facts: true` before decisions that depend on current state (disk, network, packages).
- Do not cache secrets or large registered results with `set_fact cacheable: true`.
- Prefer `ansible_facts[...]` in new code; 2.20 deprecates the default injection of facts as top-level variables (`INJECT_FACTS_AS_VARS`), planned to change in 2.24. Setting it to `False` early removes the injection overhead and finds code that relies on it.
- Dynamic inventory plugins also support caching; enable it for slow cloud APIs and refresh on schedule.

## 5. Async and long tasks

```yaml
- name: Start a long job
  ansible.builtin.command: /usr/local/bin/long-job
  async: 1800
  poll: 0
  register: long_job
  changed_when: true

- name: Wait for the job
  ansible.builtin.async_status:
    jid: "{{ long_job.ansible_job_id }}"
  register: job_result
  until: job_result.finished
  retries: 60
  delay: 30
```

- `async` with `poll: 0` fires a task and returns immediately; poll later with `async_status`. This lets many hosts run long work in parallel under `linear` without blocking on each.
- `poll: N` (N greater than 0) holds the connection and checks every N seconds; it is simpler but occupies a fork.
- Use `until`/`retries`/`delay` for polling APIs instead of `pause`; use `wait_for` and `wait_for_connection` for ports and reboots.
- Use `ansible.builtin.reboot` rather than shell reboots; it waits for the host to return.

## 6. Mitogen

- Mitogen for Ansible is an external strategy plugin and connection layer. Since 2.19 ansible-core deprecates strategy plugins outside `ansible.builtin` and states that a future release will remove the ability to use them.
- The `mitogen` package exists on PyPI (0.3.54 at the time of checking), but whether it supports a given ansible-core version is decided by the mitogen project. Do not enable it for 2.19 or later without reading its current compatibility notes and running the full test suite.
- Default recommendation: do not use mitogen. Get most of the benefit from `pipelining`, `ControlPersist`, fewer tasks, fact caching and higher `forks`.

## 7. ansible-navigator

```yaml
# ansible-navigator.yml
---
ansible-navigator:
  mode: stdout
  execution-environment:
    enabled: true
    image: registry.example.com/ee/web-ee:1.0.0
    pull:
      policy: missing
  playbook-artifact:
    enable: false
```

```bash
ansible-navigator run site.yml --mode stdout --limit web01.example.com
ansible-navigator settings --effective
ansible-navigator images
ansible-navigator collections
```

- ansible-navigator 26.10.0 runs `ansible-playbook` and other tools inside an execution environment (EE) container with `podman` or `docker`, or on the host with `--ee false`. Use `--mode stdout` in scripts and CI, and the default interactive TUI for exploration.
- Pin the EE image by tag or digest in the project settings file; `pull.policy` accepts values such as `always`, `missing`, `never` and `tag` (confirm with `ansible-navigator settings`).
- The tool's own default image in this version is `ghcr.io/ansible/community-ansible-dev-tools:latest`; set `image:` explicitly for repeatable runs.
- Playbook artifacts (JSON run records) are written by default; disable them or store them with care, as they can include variable values.
- Mount extra paths or pass environment variables with the `volume-mounts` and `environment-variables` settings (see `ansible-navigator settings --sample`), and never mount a whole home directory.

## 8. Execution environments

An EE is a container image with ansible-core, ansible-runner, collections, Python and system dependencies. ansible-builder 3.2.0 builds it from a definition file.

```yaml
# execution-environment.yml
---
version: 3
images:
  base_image:
    name: quay.io/centos/centos:stream10
dependencies:
  ansible_core:
    package_pip: ansible-core>=2.21,<2.22
  ansible_runner:
    package_pip: ansible-runner
  galaxy: requirements.yml
  python:
    - netaddr
  system:
    - openssh-clients [platform:rpm]
    - sshpass [platform:rpm]
options:
  package_manager_path: /usr/bin/dnf
additional_build_steps:
  append_final:
    - RUN ansible --version
```

```bash
ansible-builder create                          # writes ./context with a Dockerfile (ran successfully)
ansible-builder build --tag registry.example.com/ee/web-ee:1.0.0 -v 3
```

- The definition above passed `ansible-builder create` (a `context/Dockerfile` was produced). Building needs `podman` or `docker`; choose a base image your registry policy allows, and check that its package manager path matches `package_manager_path`.
- `dependencies.galaxy` points to a `requirements.yml` for collections; `python` takes a requirements list or file; `system` takes a bindep list.
- Pin ansible-core and collection versions in the definition. Rebuild on a schedule to pick up security fixes and scan the image like any other (docker-expert covers image hygiene).
- Use `additional_build_steps` (`prepend_base`, `append_base`, `prepend_galaxy`, `append_galaxy`, `prepend_builder`, `append_builder`, `prepend_final`, `append_final`) sparingly; every step is a maintenance cost.
- Keep secrets out of build args and definition files; use the registry and controller credential stores.
- Sign or scan images and push to a private registry; reference them by tag or digest from navigator settings and AWX execution environment objects.
- Test an EE by running a smoke playbook (`ansible-navigator run smoke.yml --mode stdout`) before publishing.

## 9. AWX and Automation Platform

- AWX (upstream) and Red Hat Ansible Automation Platform provide a web UI, REST API, RBAC, credentials, job templates, workflows, inventories with sync from cloud sources, scheduling and audit logs. Jobs run in EEs on instances managed by the control plane.
- Model: Project (git repository) + Inventory + Credentials (SSH, vault, cloud, registry) + Execution Environment + Job Template. Workflows chain job templates with approvals and conditional paths.
- Keep playbooks and roles in git as the source of truth; configure the controller itself as code with the `awx.awx` collection (or `ansible.controller` on Automation Platform) after checking its module list for your version.
- Use surveys and extra variables sparingly: extra vars have the highest precedence and appear in job records.
- Store vault passwords and secrets as controller credentials; use credential plugins to read from an external secrets manager where supported.
- Check the product documentation for supported versions, installation (operator on Kubernetes or RPM bundle) and the way a project sync installs collections from `collections/requirements.yml`; these details change between releases.
- Mind Automation Platform licensing and support lifecycle separately from ansible-core versions.

## 10. Windows hosts

- Connections: WinRM (`ansible_connection: winrm`), PSRP (`psrp`) or SSH to OpenSSH on Windows. Configure TLS (HTTPS listener) and Kerberos or certificate authentication for production; avoid basic authentication over HTTP.
- Modules: `ansible.windows.*` (`win_copy`, `win_service`, `win_feature`, `win_updates` and others) and `community.windows.*`; shell options are `ansible.windows.win_shell` and `win_command`, subject to the same `changed_when` rules as Linux.
- Privilege: `become_method: runas` with `ansible_become_user` and a vaulted password; remember network-resource access and double-hop limits with WinRM.
- 2.21 changes the default `negotiate_service` for the `psrp` connection to `host`; set `ansible_psrp_negotiate_service=WSMAN` to restore the old behaviour if Kerberos SPN registration requires it.
- 2.20 removed code that stripped quotes from paths in Windows copy and fetch operations; a path that was over-quoted may now break.
- 2.21 adds support for running PowerShell-written modules on POSIX hosts with `pwsh`.
- Paths use backslashes; in YAML double-quoted strings escape them, or use single quotes or forward slashes where the module allows.
- Test Windows roles with Molecule using a delegated or custom driver; the Linux container approach does not apply.
