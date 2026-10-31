# Playbooks, Roles and Collections

Inventory, playbook structure, roles, collections and `ansible-galaxy`, handlers, tags, loops, conditionals and blocks on ansible-core 2.19 to 2.21. The examples were syntax-checked and linted with the ansible-lint production profile on ansible-core 2.21.5 (2026-10).

## Contents

1. [Inventory](#1-inventory)
2. [Dynamic inventory plugins](#2-dynamic-inventory-plugins)
3. [Playbook structure](#3-playbook-structure)
4. [Role layout](#4-role-layout)
5. [Collections and requirements](#5-collections-and-requirements)
6. [Handlers and tags](#6-handlers-and-tags)
7. [Loops and conditionals](#7-loops-and-conditionals)
8. [Blocks, errors and idempotency](#8-blocks-errors-and-idempotency)
9. [Check mode and diff](#9-check-mode-and-diff)

## 1. Inventory

YAML is the preferred static format; INI works for small cases.

```yaml
---
all:
  vars:
    ansible_user: deploy
  children:
    web:
      hosts:
        web01.example.com:
        web02.example.com:
          http_port: 8081
    db:
      hosts:
        db01.example.com:
    production:
      children:
        web:
        db:
    local:
      hosts:
        localhost:
          ansible_connection: local
```

- Variables live next to the inventory: `inventory/group_vars/<group>.yml` or `inventory/group_vars/<group>/*.yml`, and `inventory/host_vars/<host>.yml`. Group `all` applies to every host.
- Patterns for `--limit` and `hosts:`: `web:&production` (intersection), `web:!web02.example.com` (exclusion), `~web0[12]` (regex), `web*`.
- Connection variables: `ansible_host`, `ansible_user`, `ansible_port`, `ansible_connection` (`ssh`, `local`, `winrm`, `psrp`, `community.docker.docker`), `ansible_python_interpreter`, `ansible_become_method`.
- `ansible-inventory -i inventory/production --graph` shows groups; `--list` shows merged variables; `--host NAME` shows one host.
- Keep one inventory directory per environment so a typo in `-i` cannot mix staging and production variables.

## 2. Dynamic inventory plugins

Inventory plugins read a small YAML file and build hosts at run time. The file name usually must end with the suffix the plugin documents (for example `.aws_ec2.yml`); check `ansible-doc -t inventory <plugin>`.

```yaml
# inventory/production/constructed.yml - groups from existing host variables
---
plugin: ansible.builtin.constructed
strict: false
groups:
  prod: env == 'prod'
  staging: env == 'stg'
keyed_groups:
  - prefix: env
    key: env
```

- Run `ansible-inventory -i inventory/production/hosts.yml -i inventory/production/constructed.yml --graph` to confirm groups. The example above produced `prod`, `staging`, `env_prod` and `env_stg` from hosts with an `env` variable.
- Cloud plugins (`amazon.aws.aws_ec2`, `azure.azcollection.azure_rm`, `google.cloud.gcp_compute`, `community.vmware.vmware_vm_inventory`) live in collections. Install the collection, read its plugin doc for required options and credentials, and use `keyed_groups`, `groups` and `compose` to shape groups and variables.
- Cache plugin results (`cache: true`, `cache_plugin`, `cache_timeout`, options documented per plugin) when listing is slow.

## 3. Playbook structure

```yaml
---
- name: Configure web tier
  hosts: web
  become: true
  gather_facts: true
  serial: 1
  max_fail_percentage: 0
  vars_files:
    - vars/common.yml
  pre_tasks:
    - name: Assert supported OS
      ansible.builtin.assert:
        that: ansible_facts['os_family'] in ['Debian', 'RedHat']
        fail_msg: Unsupported OS family
  roles:
    - role: webapp
      vars:
        webapp_http_port: "{{ http_port | default(8080) }}"
  tasks:
    - name: Check the service port
      ansible.builtin.wait_for:
        port: "{{ http_port | default(8080) }}"
        timeout: 30
  post_tasks:
    - name: Report completion
      ansible.builtin.debug:
        msg: Finished {{ inventory_hostname }}
```

- Order inside a play: `pre_tasks`, handlers triggered by them, `roles`, `tasks`, handlers, `post_tasks`, handlers.
- `import_playbook: other.yml` composes playbooks (`site.yml` imports `web.yml` and `db.yml`). Imports are static.
- `serial` accepts a number, percentage or list (`[1, 25%, "100%"]`). `max_fail_percentage` and `any_errors_fatal` stop a rollout when too many hosts fail. `run_once` runs a task on the first host of the batch only.
- Tech preview on 2.20 and later: the play keyword `validate_argspec` validates play variables against `<playbook_name>.meta.yml`; check the current docs before using it.
- 2.21 `register` projections map names to bare expressions, for example `register: {probe_value: "_task.result.stdout | int"}`; wrapping the expression in `{{ }}` is a syntax error there.

## 4. Role layout

```text
roles/webapp/
  defaults/main.yml       # lowest-precedence, user-overridable variables
  vars/main.yml           # high precedence constants; avoid for tunables
  tasks/main.yml          # entry point; split into task files with import_tasks
  handlers/main.yml
  templates/webapp.conf.j2
  files/
  meta/main.yml           # galaxy_info, dependencies
  meta/argument_specs.yml # input validation and docs
  molecule/default/       # test scenario
```

`meta/argument_specs.yml` declares each option with `type`, `default`, `choices`, `description` and `no_log: true` for secrets, so bad input fails before any task runs and `ansible-doc -t role` documents the role. The argument-specs file used in this skill's examples passed the production lint profile.

- Use `roles:` for static inclusion and `ansible.builtin.include_role` or `import_role` inside tasks for conditional use. `include_role` with `tasks_from: install.yml` runs one entry point.
- Prefix all role variables and internal facts with the role name. Pass inputs through `vars:` on the role or through inventory, never by editing `defaults/`.

## 5. Collections and requirements

```yaml
# requirements.yml
---
collections:
  - name: ansible.posix
    version: ">=2.0.0"
  - name: community.general
    version: ">=10.0.0"
roles: []
```

```bash
ansible-galaxy collection install -r requirements.yml -p collections
ansible-galaxy collection list
ansible-doc ansible.posix.firewalld
```

- Always call modules by FQCN. Short names rely on `ansible.legacy` fallbacks and fail ansible-lint's `fqcn` rule.
- Core content is `ansible.builtin`. The community package `ansible` adds many collections; a bare `ansible-core` install has only `ansible.builtin`, so list every other collection in `requirements.yml`.
- Pin or bound versions and commit `requirements.yml`. From 2.21, collections whose `requires_ansible` does not match the running ansible-core are excluded from install unless `COLLECTIONS_ON_ANSIBLE_VERSION_MISMATCH` is set to `ignore`.
- Module redirects are defined in `meta/runtime.yml` of the collection; deprecated modules (for example `apt_key` and `apt_repository`, deprecated in 2.21 in favour of `deb822_repository`) still run but warn.
- Build your own collection with `ansible-galaxy collection init namespace.name`, `galaxy.yml` metadata and `ansible-galaxy collection build`.

## 6. Handlers and tags

```yaml
- name: Render configuration
  ansible.builtin.template:
    src: webapp.conf.j2
    dest: /etc/webapp/webapp.conf
    owner: root
    group: webapp
    mode: "0640"
  notify: Restart webapp
  tags: [config]

# handlers/main.yml
- name: Restart webapp
  ansible.builtin.service:
    name: webapp
    state: restarted
```

- Handlers run once per play at the end of each section, after all tasks that notified them; they run only if the notifying task reported `changed`.
- `ansible.builtin.meta: flush_handlers` runs pending handlers immediately. Use it when a later task needs the service restarted.
- A failing play skips pending handlers unless `--force-handlers` or `force_handlers: true` is set.
- Tags: `--tags config`, `--skip-tags slow`, `--list-tags`. `always` runs unless skipped; `never` runs only when asked for. `import_*` passes tags to children; `include_*` tags only the include statement unless `apply:` is used.

## 7. Loops and conditionals

```yaml
- name: Install packages
  ansible.builtin.package:
    name: "{{ web_packages }}"
    state: present

- name: Create users
  ansible.builtin.user:
    name: "{{ item.name }}"
    groups: "{{ item.groups | default([]) }}"
    shell: /bin/bash
  loop: "{{ web_users }}"
  loop_control:
    label: "{{ item.name }}"

- name: Wait for the port
  ansible.builtin.wait_for:
    port: "{{ webapp_http_port }}"
  when: webapp_start | bool
```

- Pass a list to the module (`name: [a, b]`) before reaching for `loop`; one transaction is faster and cleaner.
- `loop` replaces `with_items`, `with_dict` (`loop: "{{ d | dict2items }}"`), `with_subelements` (`subelements` filter) and `with_nested` (`product` filter). Lookup-based forms still exist but are not preferred.
- `loop_control`: `label`, `pause`, `index_var`, `loop_var` (set it in nested loops and in included files to avoid `item` clashes), `extended` for `ansible_loop` data.
- Conditionals are expressions evaluated in Jinja without delimiters. On 2.19 and later the result must be boolean: use `| bool`, comparisons, `is defined`, `| length > 0`, or `is truthy` style tests where documented. A bare string variable fails.
- Prefer tests to comparisons with literals: `result is failed`, `result is changed`, `var is defined`, `path is exists` (controller side), `version is version('2.0', '>=')`.
- Combine conditions as a list under `when:` (logical AND) or with `and`/`or` and parentheses.
- `until` with `retries` and `delay` re-runs a task until a condition is true; it needs `register`.
- `omit` removes an optional parameter: `mode: "{{ file_mode | default(omit) }}"`. Since 2.19 omit placeholders do not leak between loop items and task templating.

## 8. Blocks, errors and idempotency

```yaml
- name: Deploy with recovery
  block:
    - name: Apply the change
      ansible.builtin.command: /usr/local/bin/apply-change
      register: apply_result
      changed_when: "'APPLIED' in apply_result.stdout"
      failed_when: apply_result.rc not in [0, 2]
  rescue:
    - name: Restore the previous state
      ansible.builtin.command: /usr/local/bin/rollback
      changed_when: true
  always:
    - name: Record the outcome
      ansible.builtin.debug:
        msg: "rc={{ apply_result.rc | default('none') }}"
```

- `block` groups tasks for shared keywords (`when`, `become`, `tags`, `vars`, `environment`). `rescue` runs after a failure in the block; `always` runs in every case.
- `changed_when: false` marks read-only probes. `creates:` and `removes:` make `command` idempotent against a path.
- `failed_when` replaces the module's own failure test; keep it narrow. `ignore_errors: true` hides failures and should be rare. `ignore_unreachable: true` continues past unreachable hosts.
- Prefer modules whose `state:` is declarative (`present`, `absent`, `started`, `directory`) to scripts that act every run.
- `ansible.builtin.command` runs without a shell. Use `argv:` for argument lists, and `shell` only when pipes, globbing or redirects are required (lint rule `command-instead-of-shell`).
- Every `command` or `shell` task needs `changed_when`, `creates` or `removes` (lint rule `no-changed-when`).

## 9. Check mode and diff

```bash
ansible-playbook site.yml --check --diff --limit web01.example.com
ansible-playbook site.yml --list-tasks --list-tags
ansible-playbook site.yml --start-at-task "Render configuration" --step
```

- Check mode predicts changes without applying them. Most core modules support it; `command`, `shell` and `raw` are skipped unless the task sets `check_mode: false`.
- `--diff` prints before and after for files and templates; add `diff: false` on tasks that touch secrets.
- Tasks that depend on results of skipped tasks may fail in check mode; guard them with `when: not ansible_check_mode` or use `check_mode: false` for read-only probes.
- Run `--syntax-check` first (it also loads roles and templates for parse errors) and `ansible-lint` second.
