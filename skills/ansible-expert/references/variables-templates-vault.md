# Variables, Templates, Vault and Privilege

Variable precedence (simplified), facts, Jinja2 templating including the ansible-core 2.19 changes, Ansible Vault, secret lookups, `no_log` and `become` with scoped sudoers. Behaviour was checked on ansible-core 2.21.5 and against the 2.19, 2.20 and 2.21 release notes (2026-10).

## Contents

1. [Variable precedence](#1-variable-precedence)
2. [Facts](#2-facts)
3. [Jinja2 templates](#3-jinja2-templates)
4. [Changes since 2.19](#4-changes-since-219)
5. [Ansible Vault](#5-ansible-vault)
6. [External secrets and no_log](#6-external-secrets-and-no_log)
7. [Privilege escalation](#7-privilege-escalation)

## 1. Variable precedence

The full table in the Using Variables page has more than twenty levels. A working order, lowest to highest:

1. Role `defaults/main.yml`
2. Inventory `group_vars/all`, then parent groups, then child groups (same depth: alphabetical, or `ansible_group_priority`)
3. Inventory `host_vars/<host>`
4. Play `vars:` and `vars_files:`
5. Role `vars/main.yml`
6. Block and task `vars:`, and role parameters passed with `vars:` on a role entry
7. `set_fact` and `register` results
8. Extra vars (`-e`, `-e @file.yml`), which always win

- Put tunables in role `defaults/`, environment values in `group_vars`, per-host exceptions in `host_vars`, and use `-e` only for one-off overrides.
- Extra vars beat everything, including `set_fact`. Use them for release versions and emergency overrides, not for routine configuration.
- Avoid defining one variable at many levels; use `ansible-inventory --host NAME` and `ansible -m debug -a 'var=NAME' HOST` to find the winner.
- Variable names: letters, digits and underscores, not starting with a digit; avoid reserved names such as `environment`, `hosts`, `name`, `tags` and magic variables.
- Magic variables: `inventory_hostname`, `groups`, `group_names`, `hostvars`, `play_hosts`, `ansible_play_hosts`, `playbook_dir`, `role_path`, `ansible_check_mode`.
- Merging: dictionaries replace by default. Use `combine(recursive=true)` explicitly, and avoid the global `hash_behaviour = merge` setting.
- Prefix role variables (`webapp_http_port`) and internal ones with a double prefix (`__webapp_pkg_name`) to signal "do not override".
- OS-specific values: load `vars/{{ ansible_facts['os_family'] }}.yml` with `include_vars` and the `first_found` lookup, or keep a dictionary keyed by `os_family`.

## 2. Facts

- `gather_facts: true` runs `ansible.builtin.setup`. Read facts as `ansible_facts['distribution']`, `ansible_facts['os_family']`, `ansible_facts['default_ipv4']['address']`.
- Injected `ansible_*` variables exist while `INJECT_FACTS_AS_VARS` is `True` (the default through 2.21). 2.20 deprecates that default and plans `False` in 2.24, so new code should use the `ansible_facts` dictionary.
- `gather_subset: ['!all', '!min', 'network']` and `gather_facts: false` reduce cost. `ansible.builtin.package_facts`, `service_facts` and `setup` with `filter:` collect only what is needed.
- Custom facts: files under `/etc/ansible/facts.d/*.fact` (INI or JSON, or an executable that prints JSON) appear under `ansible_facts['ansible_local']`.
- `set_fact` creates host-scoped variables for the rest of the play; with `cacheable: true` they enter the fact cache. Keep `set_fact` for values that depend on runtime results.
- Facts and module results are untrusted data for templating (section 4): never rely on Jinja inside them being evaluated.
- Fact caching: `fact_caching = jsonfile`, `fact_caching_connection`, `fact_caching_timeout`; combine with `gathering = smart`. Clear with `--flush-cache`.

## 3. Jinja2 templates

```jinja
{{ ansible_managed | comment }}
listen_port = {{ webapp_http_port }}
log_level = {{ webapp_log_level }}
{% if webapp_api_token | length > 0 %}
api_token = {{ webapp_api_token }}
{% endif %}
```

```yaml
- name: Render configuration
  ansible.builtin.template:
    src: webapp.conf.j2
    dest: /etc/webapp/webapp.conf
    owner: root
    group: webapp
    mode: "0640"
    validate: /usr/local/bin/webapp --check-config %s
  no_log: true
```

- `template` runs on the controller and copies the result; `validate:` runs the given command on the temporary file (`%s`) before the destination is replaced.
- Common filters: `default(value, true)`, `mandatory('message')`, `bool`, `int`, `list`, `join`, `map(attribute='x')`, `select`, `reject`, `selectattr`, `regex_replace`, `to_json`, `to_nice_yaml`, `combine`, `dict2items`, `items2dict`, `unique`, `difference`, `ipaddr` (from `ansible.utils`), `password_hash`, `quote`, `b64encode`, `comment`.
- From 2.19 Jinja builtin filters and tests are addressable as `ansible.builtin.<name>`, for example `{{ x | ansible.builtin.default('fallback') }}`. The short names still work.
- `mandatory` fails with the supplied message; an undefined variable without a default fails the task on 2.19 and later (checked on 2.21.5).
- Whitespace: Ansible enables `trim_blocks` for templates; use `{%- ... -%}` or the module options `trim_blocks` and `lstrip_blocks` to control blank lines.
- Keep templates declarative: loops and conditionals over prepared variables, no data fetching or business logic. Compute lists and dictionaries in the play.
- Use `lookup('ansible.builtin.file', 'path')`, `lookup('ansible.builtin.env', 'NAME', default='x')` and `lookup('ansible.builtin.template', ...)` in tasks. Lookups run on the controller.
- `ansible.builtin.to_json`, `from_json`, `from_yaml` convert between text and data; `type_debug` shows the Python type while debugging.
- Do not template secrets into logs or `--diff` output: set `no_log: true` or `diff: false` on the task.
- File modes are strings: `"0644"`. An unquoted `0644` is parsed as an integer by YAML 1.1 loaders and linters flag it.

## 4. Changes since 2.19

Source: the 2.19.0, 2.20.0 and 2.21.0 release notes on GitHub. Behaviours marked "checked" were reproduced on 2.21.5.

- Conditionals must yield a boolean. `when: some_string` raises "Conditionals must have a boolean result" (checked). Fix with `| bool`, `| length > 0` or a comparison. A literal `None` or empty string still evaluates true for compatibility. `ALLOW_BROKEN_CONDITIONALS` downgrades the error to a deprecation warning.
- Delimiters in conditionals: `when: "{{ flag | bool }}"` runs but prints a deprecation warning (checked), with removal announced for 2.23. Write `when: flag | bool`.
- Template trust: Jinja markers in strings from untrusted sources (module results, facts, `!unsafe` values) are not evaluated and produce a warning. Strings from playbooks, vars files and most inventory sources are trusted. Custom plugins that create templates must tag them trusted.
- Undefined variables: using one where a value is needed is an error. `DEFAULT_UNDEFINED_VAR_BEHAVIOR` is deprecated and has no effect. Use `default(...)`, `is defined` or `mandatory`.
- `set_fact` and native types: Jinja native mode is always on. The strings "yes", "no", "true", "false" are no longer coerced to booleans by `set_fact`. Define real booleans in YAML (`enabled: true`) or apply `| bool`.
- `omit`: values resolving to `omit` in loop items are dropped immediately; to turn a missing value into an omit in the task, use `| default(omit)`. Serializing a variable that still holds an `omit` placeholder (with `to_json`, `to_yaml`, `ansible-inventory`) fails.
- Null handling: `DEFAULT_NULL_REPRESENTATION` has no effect; null values are no longer converted to another value in single-variable templating, and multi-node template results coerce embedded `None` to an empty string.
- Bool filter: coercing unrecognized values (including None) with `bool` is deprecated; `truthy` and `falsy` tests are the documented alternative.
- Plugin authors: variable values are subclasses of native types; libraries that reject subclasses need a conversion to the native type. Custom Jinja plugins that accept undefined arguments must opt in to receiving them.
- `INJECT_FACTS_AS_VARS` (2.20): deprecated default, planned switch in 2.24.
- 2.21: `register` accepts a mapping of names to bare expressions and a `_task` implicit object (`_task.result`, `_task.loop_result`) is available in `register` and `failed_when`. Evaluate whether it replaces `set_fact` chains, but keep it out of roles that must support 2.20 or older.
- Upgrade tip: run the test suite with `ANSIBLE_DEPRECATION_WARNINGS` at its default and fix every warning before the next core upgrade; read the porting guide of each minor.

## 5. Ansible Vault

```bash
ansible-vault create inventory/production/group_vars/all/vault.yml
ansible-vault edit inventory/production/group_vars/all/vault.yml
ansible-vault view inventory/production/group_vars/all/vault.yml
ansible-vault encrypt_string --vault-id prod@~/.ansible/vault-prod 'value' --name webapp_api_token
ansible-vault rekey --vault-id prod@~/.ansible/vault-prod --new-vault-id prod@prompt FILE
ansible-playbook site.yml --vault-id prod@~/.ansible/vault-prod
ansible-playbook site.yml --vault-id prod@prompt
```

- `encrypt_string` output is a `!vault |` YAML scalar with header `$ANSIBLE_VAULT;1.2;AES256;prod` (the label after the last semicolon is the vault id). Paste it as a variable value in any vars file.
- Whole-file encryption hides variable names and structure, so it suits files that are all secret. Inline `!vault` values keep names greppable and diffs readable.
- Common layout: `group_vars/all/main.yml` has `webapp_api_token: "{{ vault_webapp_api_token }}"` and `group_vars/all/vault.yml` (encrypted) defines `vault_webapp_api_token`.
- Vault IDs (`label@source`) let one run use several passwords (for example `dev` and `prod`). The source is `prompt`, a file path, or an executable script that prints the password on stdout.
- Keep password files outside the repository with mode `0600`. Do not set `vault_password_file` in a committed `ansible.cfg` to a path that does not exist everywhere: ansible-core aborts with "The vault password file ... was not found" even for `--syntax-check`, and ansible-lint reports an internal error.
- In CI, write the password from the secret store to a temporary file or use a script that reads an environment variable; never echo it into logs.
- `ansible-vault` can decrypt only with the right id; use `rekey` when a person leaves. Rotate the secrets themselves, not only the vault password.
- Encrypted values in `ansible-playbook -v` output are shown after decryption if a task prints them; combine with `no_log: true`.
- `!vault` values must be strings in YAML; the `yamllint` sanity test in ansible-test enforces this.

## 6. External secrets and no_log

- Prefer fetching secrets at run time for production: `community.hashi_vault.hashi_vault` lookup, `amazon.aws` Secrets Manager or SSM Parameter Store lookups, `community.general.onepassword` and similar. After installing the collection, confirm the exact plugin names and options with `ansible-doc -t lookup -l` and `ansible-doc -t lookup <name>`.
- Lookups run on the controller, so the controller needs credentials (instance profile, OIDC, AppRole token from the environment), not the managed hosts.
- Never put a lookup that returns a secret into a variable that is printed, registered without `no_log`, or written into a world-readable file.
- `no_log: true` hides task arguments and results from output and logs, including failures; to debug, temporarily run with `no_log: false` in a safe environment, never in shared CI logs.
- `no_log` applies to the task; loops over secret items also need `loop_control: label:` and `no_log`.
- `DEFAULT_NO_LOG` is a global switch; check `ansible-config list` before relying on it.
- Do not cache secrets: avoid `set_fact` with `cacheable: true` for values that came from a vault or lookup.
- Module arguments marked `no_log` in the module spec are masked automatically; module authors must set `no_log=True` for secret parameters.
- Recent releases mask credentials embedded in URLs for `uri`, `get_url` and similar modules (2.19.13, 2.20.9, 2.21.4 release notes); still avoid putting tokens in URLs.
- Rotate any secret that reached a log, a CI artifact or `-vvv` output.

## 7. Privilege escalation

```yaml
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

- Connect as a normal user (`ansible_user`) and escalate only where needed: `become: true` on the play, role or a single task. `become_user` selects the target account; `become_method` defaults to `sudo`.
- `become_password` is supplied as `ansible_become_password` from a vaulted variable or via `--ask-become-pass`; do not keep it in plain inventory.
- For sudoers, grant the specific commands (full paths, exact arguments where possible) and use `visudo -cf %s` in `validate:` so a syntax error cannot replace the file. Never write `NOPASSWD:ALL`, and do not add a user to a broad group such as `wheel` with passwordless sudo.
- Restricting sudo for Ansible's own connection is hard because modules run through the Python interpreter; use a dedicated deploy account, SSH key restrictions and audit logs instead.
- Becoming an unprivileged user (not root) may need extra settings for temporary files; see the become documentation for pipelining and `allow_world_readable_tmpfiles` trade-offs before enabling either.
- `become_flags` and `become_exe` adapt to `sudo-rs` or alternative binaries; a 2.20/2.21 fix addressed `sudo-rs` on non-English locales.
- `ansible.builtin.lineinfile` and `blockinfile` on `/etc/sudoers` are fragile; write drop-in files in `/etc/sudoers.d/` with `validate:` instead.
- For Windows targets use `become_method: runas` with `ansible_become_user` and a vaulted password; see the Windows guides before using other methods.
- Review `become` scope in code review: a play-level `become: true` should be justified when only two tasks need root.
