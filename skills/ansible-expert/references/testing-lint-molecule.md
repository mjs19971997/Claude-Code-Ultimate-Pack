# Testing, Linting and Molecule

ansible-lint profiles and configuration, Molecule scenarios and the current driver story, idempotence and verification, localhost tests and a CI command order. Checked with ansible-lint 26.10.1, Molecule 26.10.0 and ansible-core 2.21.5 in a Python 3.13 virtual environment (2026-10).

## Contents

1. [Test layers](#1-test-layers)
2. [ansible-lint](#2-ansible-lint)
3. [Common lint rules](#3-common-lint-rules)
4. [Molecule scenarios](#4-molecule-scenarios)
5. [Molecule drivers](#5-molecule-drivers)
6. [Verification](#6-verification)
7. [Localhost tests and check mode](#7-localhost-tests-and-check-mode)
8. [CI order](#8-ci-order)

## 1. Test layers

| Layer | Tool | Catches |
|---|---|---|
| Syntax | `ansible-playbook --syntax-check` | YAML errors, unknown keywords, missing roles and includes |
| Lint | `ansible-lint` | style, FQCNs, risky permissions, missing `changed_when`, deprecated features |
| Dry run | `--check --diff` on a staging host | unexpected changes, templating errors |
| Role test | Molecule `converge`, `idempotence`, `verify` | real behaviour on a clean instance, second-run changes |
| Integration | playbook against staging inventory | cross-role ordering, network, secrets wiring |

- Run the cheap layers on every commit and the expensive ones on pull requests and nightly.
- Install the tools in a virtual environment (`python -m venv`, `pip install ansible-core ansible-lint molecule`) or use the same execution environment as production.

## 2. ansible-lint

```bash
ansible-lint                        # lint the current project using .ansible-lint
ansible-lint --profile production site.yml roles/
ansible-lint --offline              # do not install requirements.yml dependencies
ansible-lint --fix                  # apply automatic fixes and reformat YAML
ansible-lint -P                     # list profiles and their rules
```

Profiles are cumulative, from least to most strict: `min`, `basic`, `moderate`, `safety`, `shared`, `production`. The output ends with a line such as "Profile 'production' was required, and it passed", or reports the highest profile that passed.

```yaml
# .ansible-lint
---
profile: production
exclude_paths:
  - .cache/
  - collections/
warn_list:
  - experimental
skip_list: []
offline: false
```

- Start legacy code at `basic`, fix, then raise the profile in steps. New code starts at `production`.
- Silence a single finding with a trailing `# noqa rule-id` comment and a reason, or a `skip_list` entry for the whole project. Prefer fixing.
- `ansible-lint` installs `requirements.yml` collections unless `--offline` or `offline: true` is set. In restricted CI, preinstall collections and pass `--offline`.
- In a repository with several roles, point the linter at playbook and role paths explicitly, or run it from the root and let it discover files.
- `--fix` is available for many rules; review the diff before committing, as it also reformats YAML.
- Pre-commit: use the `ansible-lint` hook from the ansible-lint repository with a pinned `rev`; check its README for the current hook id and options.
- The linter runs `ansible-playbook --syntax-check` internally; a missing vault password file or unresolvable collection shows up as `internal-error` or `syntax-check`.

## 3. Common lint rules

Findings produced by a deliberately poor playbook on ansible-lint 26.10.1:

| Rule | Meaning and fix |
|---|---|
| `name[play]`, `name[missing]`, `name[casing]` | name every play and task, start with a capital letter |
| `fqcn[action-core]` | use `ansible.builtin.copy`, not `copy` |
| `command-instead-of-shell` | use `command` unless shell features are needed |
| `no-changed-when` | add `changed_when`, `creates` or `removes` to `command`/`shell` |
| `risky-file-permissions` | set `mode` (and owner or group) on `file`, `copy`, `template` |
| `latest[git]` | pin `version` to a tag or commit, not `HEAD`; avoid `state: latest` for packages |
| `ignore-errors` | use `failed_when` or `rescue` instead of `ignore_errors: true` |
| `key-order` | put `name` first, then the module, then `when`, `loop`, `register`, `notify` |
| `jinja` | spacing and style in Jinja expressions |
| `yaml[...]` | yamllint-based formatting (indentation, truthy values, octal values, line length) |
| `role-name`, `var-naming` | role and variable naming conventions; prefix variables with the role name |
| `no-log-password` | tasks that handle passwords should set `no_log` |
| `schema` | task or play keys that do not match the Ansible schema |

- Run `ansible-lint -L` (or check the rules docs) to list the rules for the installed version; rule IDs change between releases.
- A clean run on the localhost example project (inventory, role with templates, handlers and `argument_specs`) passed the production profile.

## 4. Molecule scenarios

Molecule 26.x scenarios live in `molecule/<name>/` of a role, or in `extensions/molecule/<name>/` of a collection. `molecule init scenario NAME` creates the playbooks (run it from an activated virtual environment so `ansible-config` is on `PATH`).

```text
molecule/default/
  molecule.yml    # scenario name, test sequence, ansible and executor options
  create.yml      # user-implemented: provision instances
  converge.yml    # apply the role under test
  verify.yml      # assertions
  destroy.yml     # user-implemented: remove instances
```

The default test sequence generated by Molecule 26.10.0 is: `dependency`, `cleanup`, `destroy`, `syntax`, `create`, `prepare`, `converge`, `idempotence`, `side_effect`, `verify`, `cleanup`, `destroy`.

A localhost-only scenario that ran successfully (`molecule test`: syntax, converge, idempotence, verify):

```yaml
# molecule/default/molecule.yml
---
ansible:
  env:
    ANSIBLE_ROLES_PATH: ${MOLECULE_PROJECT_DIRECTORY}/roles
  executor:
    args:
      ansible_playbook:
        - --inventory=inventory.yml    # resolved relative to the scenario directory
        - --diff
scenario:
  name: default
  test_sequence:
    - syntax
    - converge
    - idempotence
    - verify
```

```yaml
# molecule/default/inventory.yml
---
all:
  hosts:
    instance:
      ansible_connection: local
      hello_dir: /tmp/molecule-hello
```

- Commands: `molecule test` (whole sequence), `molecule converge`, `molecule idempotence`, `molecule verify`, `molecule login`, `molecule list`, `molecule destroy`. Use `molecule converge` repeatedly while developing a role.
- `prepare.yml` installs prerequisites that are not part of the role (a package cache update, test users). It runs once per create.
- Variables for scenarios come from the scenario inventory and the `ansible:` options in `molecule.yml`; do not put secrets in the scenario.
- `ansible.executor.backend` can be `ansible-playbook` or `ansible-navigator`; with navigator, set an execution environment image in the executor args.
- Matrix testing: define several scenarios (`molecule/debian`, `molecule/rhel`) or loop over images in `create.yml` using variables.
- A localhost scenario like the one above is useful for logic and templates but cannot test packages, services or users; use an instance for those.

## 5. Molecule drivers

- Molecule 26.10.0 contains only the delegated driver (`molecule/driver/delegated.py`); there is no `driver:` block in a newly initialised scenario. The scenario's `create.yml` and `destroy.yml` are placeholders that the author implements, and Molecule reads the instance list from the file named by `molecule_instance_config`.
- Other drivers are in the separate `molecule-plugins` package (26.10.12 at the time of checking). Its extras on PyPI include `docker`, `gce`, `openstack`, `selinux` and `vagrant`; read the project README for current driver names, configuration keys and status before choosing one.
- Container-based testing: if a driver from `molecule-plugins` is used, follow its README for the image list, privileged mode and systemd handling. Running systemd inside containers is a separate topic covered by linux-expert and docker-expert.
- Alternative: create instances with your own `create.yml` using a cloud or hypervisor collection (`community.docker`, `community.libvirt`, `amazon.aws`) and a matching `destroy.yml`; write the instance config file Molecule expects.
- Pin Molecule, molecule-plugins, ansible-core and ansible-lint together in a requirements or constraints file so CI and developer machines agree.
- Older tutorials show `driver: name: docker` and `platforms:` in `molecule.yml` with the `molecule_docker` or `molecule_podman` plugins; these layouts depend on the plugin version, so verify against the current README.

## 6. Verification

```yaml
# molecule/default/verify.yml
---
- name: Verify
  hosts: instance
  gather_facts: false
  tasks:
    - name: Read marker file
      ansible.builtin.slurp:
        src: "{{ hello_dir }}/hello.txt"
      register: hello_file

    - name: Assert content
      ansible.builtin.assert:
        that: (hello_file.content | b64decode) == "hello\n"
        fail_msg: marker file has unexpected content
```

- Verify with Ansible itself: `stat`, `slurp`, `service_facts`, `package_facts`, `uri` (health endpoints), `wait_for`, `command` with `changed_when: false`, then `assert` with a `fail_msg`.
- Testinfra (`pytest-testinfra`, 10.2.2 on PyPI) is an alternative for teams that prefer pytest; it needs its own verifier wiring, so follow its docs.
- Test the failure path too: a scenario with bad input should fail at `argument_specs` validation with the documented message.
- Idempotence: Molecule runs converge a second time and fails if any task reports `changed`. Fix by adding `creates`, `changed_when` or using a native module; do not mask with `changed_when: false` on tasks that really change state.
- Handlers that always run signal non-idempotent notify sources (a template that renders a timestamp, a command that always reports changed).

## 7. Localhost tests and check mode

```bash
export DEMO_DIR="$(mktemp -d)"
ansible-playbook local.yml
ansible-playbook local.yml --check --diff
```

- For logic that does not need a remote system (templates, filters, `block`/`rescue` flow), a playbook with `hosts: localhost`, `connection: local` and `gather_facts: false` runs fast in CI. Write files into a `mktemp` directory passed through an environment lookup (`lookup('ansible.builtin.env', 'DEMO_DIR')`).
- The second run of the localhost playbook should report `changed=0` and the check-mode run `changed=0` too; treat a difference as a bug.
- `ansible-playbook --syntax-check` does not execute tasks, so it cannot catch undefined variables or conditional type errors that appear on 2.19 and later at run time. Cover them with a localhost run or a Molecule converge.
- Use `ansible-playbook -vvv` only locally; verbose output can include secrets that are not under `no_log`.
- Avoid `ansible.builtin.pause` and interactive prompts in tests.

## 8. CI order

1. Install pinned tooling (`pip install -r requirements-dev.txt`) and collections (`ansible-galaxy collection install -r requirements.yml`).
2. `ansible-playbook --syntax-check` for each top-level playbook.
3. `ansible-lint --offline --profile production` (after step 1 has installed collections).
4. `molecule test` per role and scenario, in parallel jobs.
5. Staging: `ansible-playbook --check --diff`, then the real run, then a second run that must report no changes.
6. Production: manual approval, `serial` rollout, health checks.

- Cache the pip and collections directories keyed by the requirements files.
- Keep secrets in the CI secret store and inject the vault password as a temporary file; do not pass secrets through `-e` on the command line where process listings can expose them.
- CI pipeline structure itself (stages, caching, runners) is the territory of cicd-expert.
