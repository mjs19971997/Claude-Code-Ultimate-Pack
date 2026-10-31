---
name: ansible-expert
description: >-
  Writes, reviews and tests Ansible automation on ansible-core 2.19 to 2.21: inventories, playbooks, roles, collections with FQCNs, variables and Jinja2 templating, handlers, Ansible Vault, become with scoped sudoers, ansible-lint, Molecule, execution environments and performance tuning. Use when editing playbooks, roles, inventory, group_vars, ansible.cfg, requirements.yml or molecule.yml, running ansible-playbook, ansible-galaxy, ansible-vault or ansible-lint, or fixing 2.19 templating and conditional errors. Not for cloud resource provisioning (use terraform-expert), systemd and kernel tuning (use linux-expert), image builds (use docker-expert), or CI pipeline design (use cicd-expert).
license: MIT
metadata:
  version: "3.2.0"
---

# Ansible Expert

This skill covers configuration management and orchestration with Ansible: inventory design, playbooks and roles, collections, variable precedence, facts, Jinja2 templates, idempotency, privilege escalation, secrets handling, linting, role testing with Molecule, execution environments and controller performance. It targets ansible-core 2.19 through 2.21 and treats the 2.19 data tagging and templating changes as the main migration risk. Provisioning of cloud infrastructure, OS internals, container images and CI pipeline structure belong to other skills.

> Verified against ansible-core 2.21.5 (PyPI; release notes for 2.19.15rc1, 2.20.11rc1 and 2.21.6rc1 read on GitHub), the ansible community package 14.5.0 (requires ansible-core ~=2.21.5 and Python 3.12 or newer), ansible-lint 26.10.1, Molecule 26.10.0, molecule-plugins 26.10.12, ansible-navigator 26.10.0 and ansible-builder 3.2.0; examples were syntax-checked, linted with the production profile and run against localhost on Python 3.13 (2026-10).

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

- Covered: INI and YAML inventory, `group_vars` and `host_vars`, inventory plugins, playbooks, roles and `meta/argument_specs.yml`, collections and `ansible-galaxy`, `requirements.yml`, variable precedence, facts and fact caching, handlers, tags, loops, conditionals, `block`/`rescue`/`always`, `changed_when` and `failed_when`, check mode and `--diff`, Jinja2 templates, `become`, Ansible Vault and external secret lookups, `no_log`, `ansible.cfg`, ansible-lint, Molecule, ansible-navigator, ansible-builder, AWX and Automation Platform (briefly) and Windows hosts (briefly).
- Not covered: Terraform and cloud resource provisioning (terraform-expert); systemd units, kernel parameters and Linux tuning (linux-expert); Dockerfiles and image hygiene (docker-expert); pipeline syntax and runner design (cicd-expert); Kubernetes manifests and operators (kubernetes-expert); credential and key design in general (secure-coding-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Versions | ansible-core 2.21.5 is current on PyPI; maintenance releases of 2.19, 2.20 and 2.21 are still published (October 2026). The community package `ansible` 14.5.0 bundles collections and pins `ansible-core~=2.21.5`. 2.21.5 requires Python 3.12 or newer on the controller; 2.20 dropped controller Python 3.11 and target Python 3.8, and added Python 3.14 support |
| 2.19 data tagging | The variable type system was reworked: many values are subclasses of native Python types. Jinja2 3.1.0 or newer is required on the controller. Native Jinja mode is always on, so `DEFAULT_JINJA2_NATIVE` has no effect. Custom plugins that mishandle subclassed types, untagged templates or `Marker` values may need updates |
| 2.19 template trust | Jinja in a string is evaluated only when the string comes from a trusted source (playbooks, vars files, most inventory). Strings from module results and facts that contain template markers are ignored with a warning. Plugins that build templates must tag them as trusted |
| 2.19 conditionals | A `when` or `failed_when` expression that evaluates to a non-boolean is an error by default (`when: some_string` fails). A literal `None` or empty string still evaluates true. `ALLOW_BROKEN_CONDITIONALS` downgrades the error temporarily. Wrapping a conditional in `{{ }}` is deprecated; removal is announced for 2.23 |
| 2.19 other breaks | Using an undefined variable where a value is expected is always an error (`DEFAULT_UNDEFINED_VAR_BEHAVIOR` has no effect). `set_fact` no longer converts "yes", "no", "true", "false" strings to booleans; write real YAML booleans or apply `bool`. `omit` placeholders no longer leak from loop items into task templating; use `default(omit)`. Forks no longer inherit stdio. Non-`ansible.builtin` strategy plugins are deprecated |
| 2.20 | `INJECT_FACTS_AS_VARS` (default `True`) is deprecated and is planned to switch to `False` in 2.24: use `ansible_facts['os_family']`, not `ansible_os_family`. Tech preview `validate_argspec` play keyword validates play variables against `<playbook_name>.meta.yml`. `ansible-galaxy` dropped the Galaxy v2 API. `DEFAULT_TRANSPORT=smart` removed |
| 2.21 | `register` accepts a mapping of variable names to bare expressions (no `{{ }}`), and a `_task` implicit object exposes `_task.result` in `register` and `failed_when`. `ansible-galaxy` excludes collections whose `requires_ansible` does not match the running core (`COLLECTIONS_ON_ANSIBLE_VERSION_MISMATCH=ignore` restores the old behaviour). The `ansible.builtin.paramiko` connection plugin was removed. `apt_key` and `apt_repository` are deprecated in favour of `deb822_repository`. `psrp` default `negotiate_service` changed to `host` |
| Collections | Use fully qualified collection names: `ansible.builtin.copy`, `ansible.posix.firewalld`, `community.general.ufw`. Install with `ansible-galaxy collection install -r requirements.yml`. Roles can be listed in the same file under `roles:` |
| Idempotency | Native modules report `changed` only when state differs. `command`, `shell` and `raw` always report `changed` unless `changed_when`, `creates` or `removes` says otherwise |
| Privilege | `become: true` with `become_method: sudo` is the default pattern. Grant `sudoers.d` entries per command, validate with `visudo -cf %s`, never `NOPASSWD:ALL` |
| Vault | `ansible-vault encrypt_string` for single values, whole-file encryption for secrets files, `--vault-id label@source` for several passwords. A missing `vault_password_file` named in `ansible.cfg` aborts every command, including `--syntax-check` |
| ansible-lint 26.10 | Profiles in increasing strictness: `min`, `basic`, `moderate`, `safety`, `shared`, `production`. `--fix` rewrites files, `--offline` skips installing `requirements.yml` dependencies. Configured in `.ansible-lint` |
| Molecule 26.10 | Ships only the delegated (`default`) driver; the scenario's `create.yml` and `destroy.yml` are written by the user. Docker, Vagrant, cloud and similar drivers live in `molecule-plugins` (check its README for the current list). Test sequence includes `idempotence` |
| Tooling | ansible-navigator runs playbooks inside execution environments (container images). ansible-builder 3.2.0 builds them from `execution-environment.yml` (`version: 3`). AWX and Red Hat Ansible Automation Platform run playbooks in EEs on a controller |

## 3. Workflow

1. Read `ansible.cfg`, the inventory layout, `requirements.yml`, `.ansible-lint`, existing role structure and CI config. Identify the ansible-core version actually used (`ansible --version`), the target OS families and whether the project runs in an execution environment.
2. Reproduce with the project's own command and limit scope: `ansible-playbook site.yml --limit web01 --check --diff`. Use `--list-tasks`, `--list-tags` and `--start-at-task` to narrow a failing run.
3. Prefer a module over `command` or `shell`. Search with `ansible-doc -l` and read `ansible-doc ansible.builtin.<name>` for the installed version before writing parameters.
4. Make the smallest change in the right layer: defaults in the role, environment values in `group_vars`, per-host exceptions in `host_vars`.
5. Run, in order: `ansible-playbook --syntax-check`, `ansible-lint`, a check-mode run against a test host, a real run, then a second run that must report `changed=0` (idempotence).
6. After upgrading ansible-core, run the whole suite with deprecation warnings visible and fix conditionals, undefined variables and string-to-boolean assumptions before the next upgrade.
7. Report which commands were run, on which inventory limit, and any task that could not be made idempotent.

## 4. Decision Rules

- If a module exists for the task, use it. If only `command` or `shell` works, use `command` unless pipes or redirects are needed, and always set `changed_when`, `creates` or `removes`.
- If the same logic is used by more than one playbook, extract a role. If it is used once, keep it as tasks in the playbook. Do not create roles with a single task.
- If a value differs per environment, put it in `group_vars/<env>/`. If it is a safe default, put it in `roles/<name>/defaults/main.yml`. Reserve `vars/main.yml` for constants the role consumer must not override.
- If a variable should be set only for one task, use `vars:` on the task. Avoid `set_fact` for values that can be a `vars:` entry; on 2.21 and later consider a `register` projection.
- If a service must restart only when its config changed, use `notify` and a handler, not a trailing restart task.
- If hosts must be changed one at a time, use `serial` with `max_fail_percentage`. If a task runs once for a group, use `run_once` and know that it runs on the first host of the batch.
- If a secret is needed, store it vault-encrypted or fetch it with a lookup from an external manager (for example the `community.hashi_vault` or `amazon.aws` collections; check the current collection docs). Do not keep plaintext in the repository.
- If a task prints or registers a secret, add `no_log: true` to it.
- If the playbook must run on several ansible-core versions, avoid 2.21-only features (`register` mapping, `_task`) until the minimum version is 2.21.
- If a legacy playbook fails on 2.19 with a conditional or undefined-variable error, fix the expression. Use `ALLOW_BROKEN_CONDITIONALS` only as a short-lived bridge with a ticket to remove it.
- If you need per-host parallelism without waiting for the slowest host, use `strategy: free`; keep `linear` when later tasks depend on all hosts finishing earlier tasks.
- If a mitogen strategy is proposed, treat it as unsupported: external strategy plugins are deprecated in ansible-core 2.19 and compatibility with 2.19 or newer must be verified against the mitogen project before use.

## 5. Coding Standards

- YAML files start with `---`, use two-space indentation and the `.yml` extension consistently. Quote strings that could be parsed as other types ("0644", "yes", version numbers). File modes are quoted strings such as `"0644"`.
- Every play and task has a `name` starting with an uppercase letter and describing the outcome ("Install nginx", not "install"). Names in handlers match the `notify` string exactly.
- Use FQCNs for every module: `ansible.builtin.template`, not `template`. Avoid `ansible.legacy.*`.
- Set `mode`, `owner` and `group` explicitly on `file`, `copy` and `template` tasks (the `risky-file-permissions` rule).
- Use native YAML for module arguments (`key: value`), not the free-form `key=value` string.
- Prefix role variables with the role name (`webapp_http_port`) to avoid collisions across roles. Facts are read as `ansible_facts['key']`.
- Use `true` and `false` for booleans. Do not rely on `yes`/`no` string coercion.
- Keep conditionals as bare expressions: `when: webapp_enabled | bool`, `when: result.rc != 0`. Do not use `{{ }}` inside `when`.
- Prefer `loop:` over `with_*`. Use `loop_control: label:` to keep output readable and `no_log` when items hold secrets.

## 6. Project Structure

```text
ansible-repo/
  ansible.cfg
  .ansible-lint
  requirements.yml            # collections and roles, pinned or ranged
  site.yml                    # imports the other playbooks
  playbooks/
    web.yml
    db.yml
  inventory/
    production/
      hosts.yml               # or an inventory plugin config file
      group_vars/
        all/main.yml
        all/vault.yml         # encrypted
        web/main.yml
      host_vars/
        web02.example.com.yml
    staging/
      hosts.yml
      group_vars/
  roles/
    webapp/
      defaults/main.yml       # overridable defaults
      vars/main.yml           # internal constants
      tasks/main.yml
      handlers/main.yml
      templates/*.j2
      files/
      meta/main.yml
      meta/argument_specs.yml # validated inputs and docs
      molecule/default/       # scenario for the role
  collections/                # local collections (optional)
```

- One inventory directory per environment keeps `group_vars` separate and makes `-i inventory/staging` safe.
- Use a `group_vars/<group>/` directory with several files (`main.yml`, `vault.yml`) rather than one large file.
- Playbooks stay thin: host selection, `become`, role list and role variables. Logic lives in roles.

## 7. Design Patterns

- Role with argument specs: declare inputs in `meta/argument_specs.yml` (`type`, `default`, `choices`, `no_log`) so wrong input fails early with a clear message and `ansible-doc -t role` documents it.
- Handler restart on change: `template` or `copy` with `notify`, validate the file before replacing it (`validate:` on `template`, `copy` and `lineinfile`), then restart in a handler. Use `meta: flush_handlers` only when a later task needs the restarted service.
- Rolling update: `serial: 1` (or a percentage list `[1, 25%, 100%]`), `max_fail_percentage: 0`, a health check task after the change, and `any_errors_fatal` when a partial rollout is worse than a stopped one.
- Block with recovery: `block` for the change, `rescue` to restore or report, `always` for cleanup. `rescue` runs only on failure of the block and the play continues afterwards.
- Dynamic groups: `ansible.builtin.constructed` inventory plugin or `keyed_groups` on cloud inventory plugins create groups from host variables, tags or facts. Verify the output with `ansible-inventory --graph`.
- Delegation: `delegate_to` for load balancer drain or API calls from the controller; `delegate_facts` only when facts should be stored on the delegate target.
- Include versus import: `import_*` is static (parsed at load time, tags and `--list-tasks` work); `include_*` is dynamic (evaluated at run time, needed for loops over files or variable names). Choose import unless the name or condition is only known at run time.
- Check-mode friendly tasks: read-only `command` probes carry `check_mode: false` and `changed_when: false`, so later tasks can use their output during `--check`.
- Argument-validated plays on 2.20 and later: `validate_argspec` is a tech preview play keyword; treat it as unstable and check the current docs before relying on it.

## 8. Best Practices

- Keep playbooks idempotent: a second run on an unchanged host must report `changed=0`. Treat any permanent `changed` as a bug.
- Use `ansible.builtin.assert` at the top of a play or role to fail early on missing or out-of-range inputs, with a `fail_msg`.
- Prefer `ansible_facts['distribution']` and `ansible_facts['os_family']` over the injected `ansible_*` variables; use `gather_subset` or `gather_facts: false` when facts are not needed.
- Pin collection versions or ranges in `requirements.yml` and commit it; install in CI with `ansible-galaxy collection install -r requirements.yml`.
- Use tags sparingly and document them; they are for operators (`--tags config`), not for program logic. Reserved tag names (`always`, `never`, `all`, `tagged`, `untagged`) have special meaning, and 2.20 warns when selection-only tags are set in a play.
- Use `ansible-inventory --list` and `--graph` to debug groups, and `ansible -m debug -a "var=hostvars[inventory_hostname]"` for variable inspection (redact secrets first).
- Use `--check --diff` for review, knowing that tasks which depend on earlier changed state may report differently in check mode.
- Use `ansible-playbook --syntax-check` and `ansible-lint` as pre-commit hooks and in CI before any run against real hosts.
- On Debian-family targets prefer `deb822_repository` over the deprecated `apt_key` and `apt_repository`.
- Keep variables flat and named; avoid deep merging via `combine(recursive=true)` unless needed, and avoid `hash_behaviour = merge`.

## 9. Performance

- Raise `forks` (default 5) to match controller CPU and target count; start with 20 to 50 and measure. Use `throttle` on a task to limit load on a shared backend.
- Enable SSH pipelining (`[ssh_connection] pipelining = True`) when `requiretty` is not enforced on targets; it reduces SSH round trips per task. Add `ControlMaster`/`ControlPersist` in `ssh_args`.
- Gather facts only when used: `gather_facts: false`, `gather_subset: ['!all', '!min', 'network']`, or `gathering = smart` with a fact cache (`fact_caching = jsonfile` or another cache plugin, with `fact_caching_timeout`).
- `strategy: free` lets each host run ahead; `host_pinned` keeps a worker bound to a host. The default is `linear`. Strategy plugins outside `ansible.builtin` are deprecated.
- Mitogen is not recommended: it is an external strategy plugin, a deprecated category in 2.19, and its support for current ansible-core must be verified by the project before use.
- Use the `profile_tasks` and `timer` callbacks (provided by the `ansible.posix` collection in the community package; confirm with `ansible-doc -t callback -l`) to find slow tasks before tuning.
- Replace per-item loops with module-native lists where possible (`ansible.builtin.package` with `name: [a, b, c]`), and avoid `with_fileglob` over large trees.
- Use `async` with `poll: 0` and `ansible.builtin.async_status` for long tasks that can run in parallel; use `until`/`retries`/`delay` for polling instead of `pause`.

Details and `ansible.cfg` settings: [references/performance-execution-environments.md](references/performance-execution-environments.md).

## 10. Security

- Secrets: vault-encrypt with `ansible-vault`, or fetch at run time with a lookup from an external manager. Keep the vault password in a file with mode `0600` outside the repository or in a script that reads a secret store. Use `--vault-id` labels per environment.
- Put `no_log: true` on tasks that handle tokens, passwords or private keys, and on loops over secrets. Be aware that `-vvv` and `register` variables can leak data that is not under `no_log`.
- Least privilege: connect as an unprivileged user and escalate per task or play. Scoped sudoers entries per command, written through `ansible.builtin.copy` with `validate: /usr/sbin/visudo -cf %s`, mode `0440`, owner `root`. Never write `NOPASSWD:ALL`.
- Use SSH keys or a certificate authority, keep `host_key_checking` on (the default) and manage `known_hosts` instead of disabling it.
- Treat module output, facts and registered data from targets as untrusted. Since 2.19 templates in such strings are ignored, but avoid putting target-controlled strings into `command` lines; pass arguments with `argv:` or apply the `quote` filter when a shell is unavoidable.
- Do not run `ansible-galaxy` installs from unreviewed sources. Pin versions and, where policy requires, mirror collections to an internal Galaxy server. Recent maintenance releases fixed path-containment problems in `ansible-galaxy collection install` and `role install` (see the 2.19.15, 2.20.11 and 2.21.6 release notes); keep ansible-core on a current patch release.
- Never write secrets into `ansible.cfg`, inventory files or `ansible-navigator` settings committed to git.
- Restrict file modes on rendered secrets (`"0600"` or `"0640"` with a service group) and use `validate:` where the target has a config checker.
- Run production playbooks from a controlled controller or AWX with RBAC and audit logs rather than from developer laptops.

Details: [references/variables-templates-vault.md](references/variables-templates-vault.md).

## 11. Testing

- Static: `ansible-playbook --syntax-check`, `ansible-lint` (use the `production` profile for new code and `basic` or `moderate` as a first step for legacy code), and `yamllint` rules shipped with ansible-lint.
- Unit-like: `ansible-playbook` against `localhost` with `connection: local` and a temporary `dest` directory for logic that does not need a remote host.
- Role tests: Molecule scenarios under `roles/<name>/molecule/<scenario>/` or `extensions/molecule/` in a collection. The default sequence includes `syntax`, `create`, `converge`, `idempotence`, `verify` and `destroy`.
- Verification: write `verify.yml` with `ansible.builtin.assert`, `ansible.builtin.stat`, `ansible.builtin.service_facts`, `ansible.builtin.uri` or `package_facts`. Testinfra is an alternative if the team already uses pytest.
- Idempotence is part of the test: the second converge must report no changes.
- Check mode: `--check --diff` as a dry-run gate on staging before production, understanding that `command`/`shell` tasks are skipped unless `check_mode: false`.
- Matrix: test against each supported target OS image and the supported ansible-core versions.

Details: [references/testing-lint-molecule.md](references/testing-lint-molecule.md).

## 12. Review Checklist

- [ ] All modules use FQCNs, every task and play has a name, and `ansible-lint --profile production` passes (or the exceptions are listed in `.ansible-lint` with a reason).
- [ ] No `shell`/`command` where a module exists; remaining ones have `changed_when`, `creates` or `removes`.
- [ ] A second run reports `changed=0`; handlers fire only on change.
- [ ] No plaintext secrets; vaulted values are used; `no_log: true` on secret-handling tasks.
- [ ] `become` is scoped to the tasks that need it; sudoers entries are per-command and validated; no `NOPASSWD:ALL`.
- [ ] Conditionals are boolean expressions without `{{ }}`; no reliance on undefined variables or on "yes"/"no" strings turning into booleans.
- [ ] Role variables are prefixed, defaults are in `defaults/main.yml`, inputs validated by `argument_specs.yml`.
- [ ] Files and templates set `mode`, `owner`, `group`; config templates use `validate:` where possible.
- [ ] `requirements.yml` pins or bounds collection versions; the minimum ansible-core is stated.
- [ ] Rolling changes use `serial` and a health check; destructive tasks have a guard (`when`, tags with `never`, or confirmation variable).
- [ ] Facts accessed through `ansible_facts[...]`, not injected variables.
- [ ] Tests exist (Molecule scenario or a localhost playbook) and CI runs lint and syntax check.

## 13. Production Notes

- Upgrade path: move one minor version at a time (2.18 to 2.19 to 2.20 to 2.21), run the playbooks with deprecation warnings enabled and fix them each step. The 2.19 step is the largest because of templating, conditionals and undefined-variable strictness.
- Pin the toolchain in an execution environment or a constraints file (`ansible-core`, `ansible-lint`, `molecule`, collections) so local runs match CI and AWX.
- Release notes of each ansible-core minor list a porting guide; read it before bumping: https://docs.ansible.com/ansible-core/2.21/porting_guides/porting_guide_core_2.21.html (and the 2.19 and 2.20 equivalents).
- Collections declare `requires_ansible`; from 2.21 `ansible-galaxy` skips collections that do not match the running core, so a pinned old collection can silently disappear from an install. Check the install output.
- AWX and Automation Platform: store inventories, credentials (vault, SSH, cloud) and job templates as controller objects, use an EE that matches your tested toolchain, and keep the playbook repository the source of truth. Project syncs install `collections/requirements.yml`; check the AWX docs for the exact paths.
- Windows hosts: connect through `winrm` or `psrp` (or SSH), use `ansible.windows.*` and `community.windows.*` modules, `become_method: runas`. 2.21 changes the default Kerberos SPN service for `psrp` to `host` (`ansible_psrp_negotiate_service=WSMAN` restores the old value). Check the Windows guides before changing authentication settings.
- Fact caching and smart gathering can serve stale facts; set `fact_caching_timeout` deliberately and refresh facts (`setup`) before decisions that depend on them.

## 14. Examples

Inventory (`inventory/production/hosts.yml`):

```yaml
---
all:
  children:
    web:
      hosts:
        web01.example.com:
        web02.example.com:
          http_port: 8081
    db:
      hosts:
        db01.example.com:
```

Thin playbook with a rolling update (`site.yml`):

```yaml
---
- name: Configure web tier
  hosts: web
  become: true
  gather_facts: true
  serial: 1
  max_fail_percentage: 0
  roles:
    - role: webapp
      vars:
        webapp_http_port: "{{ http_port | default(8080) }}"
```

Tasks that are idempotent, secret-safe and validated (`roles/webapp/tasks/main.yml`):

```yaml
---
- name: Create config directory
  ansible.builtin.file:
    path: /etc/webapp
    state: directory
    owner: root
    group: webapp
    mode: "0750"

- name: Render configuration
  ansible.builtin.template:
    src: webapp.conf.j2
    dest: /etc/webapp/webapp.conf
    owner: root
    group: webapp
    mode: "0640"
    validate: /usr/local/bin/webapp --check-config %s
  no_log: true
  notify: Restart webapp

- name: Allow the service account to restart only this unit
  ansible.builtin.copy:
    dest: /etc/sudoers.d/webapp-restart
    content: |
      webapp ALL=(root) NOPASSWD: /usr/bin/systemctl restart webapp.service
    owner: root
    group: root
    mode: "0440"
    validate: /usr/sbin/visudo -cf %s
```

Block, rescue and always with controlled `changed_when` and `failed_when`:

```yaml
- name: Probe and recover
  block:
    - name: Probe a file
      ansible.builtin.command: cat /srv/app/state.conf
      register: app_probe
      changed_when: false
      failed_when: app_probe.rc not in [0, 1]
    - name: Assert the file exists
      ansible.builtin.assert:
        that: app_probe.rc == 0
        fail_msg: state.conf not found
  rescue:
    - name: Create the default file
      ansible.builtin.copy:
        content: "created=true\n"
        dest: /srv/app/state.conf
        mode: "0644"
  always:
    - name: Report probe result
      ansible.builtin.debug:
        msg: "rc={{ app_probe.rc | default('none') }}"
```

Conditionals that work on 2.19 and later:

```yaml
- name: Runs only when the flag is truthy
  ansible.builtin.debug:
    msg: enabled
  when: feature_flag | bool            # not: when: feature_flag (string) and not: when: "{{ ... }}"

- name: Runs when the list is not empty
  ansible.builtin.debug:
    msg: has items
  when: items_list | length > 0
```

`register` projection (2.21 and later; the mapping values are bare expressions):

```yaml
- name: Read a number
  ansible.builtin.command: echo 42
  changed_when: false
  register:
    probe_value: _task.result.stdout | int
    probe_big: probe_value > 40
```

Minimal `ansible.cfg`:

```ini
[defaults]
inventory = inventory/production/hosts.yml
roles_path = roles
collections_path = collections
forks = 20
gathering = smart
fact_caching = jsonfile
fact_caching_connection = .cache/facts
fact_caching_timeout = 7200

[ssh_connection]
pipelining = True
ssh_args = -o ControlMaster=auto -o ControlPersist=60s
```

Daily commands:

```bash
ansible-galaxy collection install -r requirements.yml
ansible-inventory -i inventory/production --graph
ansible-playbook site.yml --syntax-check
ansible-lint --profile production
ansible-playbook site.yml --limit web01.example.com --check --diff
ansible-playbook site.yml --limit web01.example.com
ansible-vault encrypt_string --vault-id prod@~/.ansible/vault-prod 'value' --name webapp_api_token
```

## 15. Common Mistakes

- `when: some_string_var` fails on 2.19 and later because the result is not boolean. Use `| bool`, a comparison or `| length > 0`.
- `when: "{{ var }}"` still works but is deprecated; remove the braces.
- Setting `vault_password_file` in `ansible.cfg` to a path that does not exist on a developer machine breaks every command, including syntax checks and ansible-lint. Use `--vault-id` or an environment variable per context, or commit a script that exists everywhere.
- Using `ansible_os_family` and other injected facts in new code; switch to `ansible_facts['os_family']` before `INJECT_FACTS_AS_VARS` changes.
- Relying on `set_fact: enabled: "yes"` becoming a boolean; since 2.19 it stays a string.
- Using `shell: apt-get install ...` instead of `ansible.builtin.package`/`apt`/`dnf`, then forgetting `changed_when`.
- Writing `NOPASSWD:ALL` into sudoers, or copying a sudoers file without `validate: visudo -cf %s`, which can lock out `sudo` on the host.
- Putting `no_log: true` on a whole play so every failure is invisible; apply it only to tasks that touch secrets.
- Using `ignore_errors: true` to hide failures; use `failed_when`, `rescue` or `ignore_unreachable` with intent.
- Using `state: latest` for packages or `git` `version: HEAD` in production, which breaks idempotence and repeatability.
- Defining the same variable in many places (role defaults, play vars, `set_fact`, extra vars) and being surprised by precedence; keep one source per value.
- Letting `ansible-lint` install `requirements.yml` in an offline CI job; pass `--offline` or provide the collections beforehand.
- Adopting an external strategy plugin such as mitogen without verifying it against the ansible-core version in use.
- Testing only the first run in Molecule; the `idempotence` step catches handlers and templates that always change.

## 16. References

- [references/playbooks-roles.md](references/playbooks-roles.md): inventory formats and plugins, playbook structure, roles and collections, requirements.yml and ansible-galaxy, handlers, tags, loops, conditionals, blocks and check mode.
- [references/variables-templates-vault.md](references/variables-templates-vault.md): variable precedence (simplified), facts, Jinja2 templates, 2.19 templating and conditional changes, Vault, no_log, become and scoped sudoers, external secret lookups.
- [references/testing-lint-molecule.md](references/testing-lint-molecule.md): ansible-lint profiles and configuration, Molecule scenarios and the driver story, idempotence and verify playbooks, localhost tests, CI order.
- [references/performance-execution-environments.md](references/performance-execution-environments.md): forks, pipelining, fact caching, strategies, async, ansible-navigator, ansible-builder, AWX and Automation Platform, Windows hosts.
- Ansible documentation: https://docs.ansible.com/ansible/latest/ and ansible-core porting guides https://docs.ansible.com/ansible-core/2.21/porting_guides/porting_guide_core_2.21.html
- ansible-core changelogs: https://github.com/ansible/ansible/tree/devel/changelogs ; PyPI: https://pypi.org/project/ansible-core/ and https://pypi.org/project/ansible/
- ansible-lint: https://docs.ansible.com/projects/lint/ ; Molecule: https://docs.ansible.com/projects/molecule/
- ansible-navigator: https://ansible.readthedocs.io/projects/navigator/ ; ansible-builder: https://ansible.readthedocs.io/projects/builder/
