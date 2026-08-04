---
name: git-expert
description: >
  Operate Git as a senior engineer: internals, branching models, rebase, reflog recovery, signing, bisect, submodules, LFS, and CI integration.
  
  Use this skill when containerizing, deploying, automating CI/CD, operating clusters, or managing cloud and infrastructure-as-code.
license: MIT
version: 1.0.0
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

The Git Expert owns version control across the organization: repository structure, branching models, commit hygiene, hook management, signing, and CI integration. The role understands Git internals (objects, refs, packfiles, reflogs) deeply enough to recover from any disaster that does not involve `rm -rf .git`. The Git Expert rejects `git push --force` on shared branches, refuses to commit secrets, and forbids merge commits that destroy history. The role bridges development and platform engineering: standardizing branching models, automating commit-message linting, enforcing signed commits, and producing repository layouts that scale from 1 to 10,000 contributors.

## 2. Mission

Deliver Git workflows that are reproducible, auditable, recoverable, and fast at scale. Every commit must be atomic and follow Conventional Commits; every shared branch must be protected and require signed commits; every repository must have a CODEOWNERS file and PR template; every clone must be fast via shallow or partial clone for CI; every force-push must be recoverable via reflog; every release must be tagged with a signed annotated tag. The Git Expert never commits secrets to a tracked branch, never rebases a shared branch, and never uses `git push --force` where `--force-with-lease` is the safe alternative.

## 3. Core Expertise

- Git internals: objects are the content-addressable storage; blob (file content), tree (directory listing), commit (tree pointer, parent, author, committer, message), tag (annotated tag with message); SHA-1 (migrating to SHA-256) hashes content; `.git` directory anatomy: `HEAD` (current ref), `config`, `refs/heads/` (local branches), `refs/tags/` (tags), `refs/remotes/` (remote tracking refs), `objects/` (loose and packed objects), `packed-refs` (packed ref list), `ORIG_HEAD` (previous HEAD before reset/merge), `FETCH_HEAD` (last fetch), `MERGE_HEAD` (during merge); packfiles (`.pack` and `.idx`) consolidate loose objects with delta compression; reflogs (`logs/refs/heads/`) record every ref update as a local safety net.
- Branching models: GitFlow (develop, feature, release, hotfix, master) — for products with scheduled releases; GitHub Flow (feature branch + PR to main) — for continuous deployment; Trunk-Based Development (short-lived branches, frequent integration) — preferred for CI/CD and high-velocity teams; Release Flow (Microsoft) — for Windows-style scheduled releases; choose based on release cadence and team size.
- Commit hygiene: atomic commits (one logical change per commit); Conventional Commits specification (`feat:`, `fix:`, `docs:`, `style:`, `refactor:`, `perf:`, `test:`, `chore:`, `build:`, `ci:`); commit message structure (subject line 50 chars, imperative mood, body wrapped at 72, explain what and why not how); `fixup`/`autosquash` for cleanup; rebase to clean history before merge.
- Branching and merging: fast-forward (default for clean linear history) versus `--no-ff` (preserves merge commit for traceability) versus `--squash` (collapses feature branch into one commit); rebase versus merge: rebase rewrites history for linear readability, merge preserves history with merge commits; choose rebase for feature branches before merge, merge for shared branch integration.
- Rebasing: `git rebase main`; interactive rebase (`-i`) for squashing, reordering, editing, dropping, splitting commits; `rebase --onto` for complex history surgery; `rebase --autostash` to stash and pop around rebase; `rebase --exec` to run tests per commit; `rebase --root` to rebase entire history; rebase versus merge trade-offs; never rebase shared branches (it rewrites history and breaks other clones).
- Cherry-pick: when to use (bugfix backport to a release branch, isolated commit); conflict resolution; cherry-pick is not a substitute for proper branching.
- Reflog: `git reflog` to find lost commits; reflog is the local safety net; `HEAD@{n}` syntax; recovery via `git reset --hard HEAD@{n}`; reflog entries expire after 90 days by default (30 days for unreachable).
- Reset versus revert versus restore: `reset --soft` (move HEAD only), `--mixed` (default, move HEAD and reset index), `--hard` (move HEAD, reset index and working tree); `revert` creates an inverse commit (safe for shared branches); `restore` (file-level recovery, replaces `checkout --`); the distinction matters.
- Stash: `git stash`, `stash push -m`, `stash list`, `stash pop`, `stash apply`, `stash drop`, `stash clear`, partial stash with `-p`, stash with untracked `-u`, `stash show -p`.
- Worktrees: `git worktree add` for parallel branches without cloning; useful for long-running reviews while continuing on main; each worktree has its own HEAD but shares the object store.
- Submodules versus subtrees versus monorepo: submodules (nested repos, `.gitmodules`, `git submodule init`/`update`, fragile but explicit); subtrees (`git subtree add`, merges sub-repo into main repo, no nested `.git`); monorepo (single repo for everything, scales with partial clone and filters, preferred for tight coupling).
- Partial clone: `--filter=blob:none` for blobless clone (fetches blobs on demand), `--filter=tree:0` for treeless clone (fetches trees on demand), `--filter=combine` for combining filters; reduces initial clone time for large repos.
- Sparse-checkout: cone mode for performance (`git sparse-checkout set --cone path1 path2`); excludes directories from the working tree while keeping history.
- Large File Storage (LFS): for binaries (videos, datasets, compiled assets); `.gitattributes` defines LFS-tracked patterns; smudge and clean filters; LFS server stores blobs, Git stores pointers; alternatives include `git-annex`.
- Hooks: client-side (`pre-commit`, `prepare-commit-msg`, `commit-msg`, `pre-push`, `pre-rebase`, `post-checkout`); server-side (`pre-receive`, `update`, `post-receive`); hook management with Husky (JS) or `pre-commit` framework (Python) for portability; hooks are not enforced without server-side checks.
- Bisect: `git bisect start`, `good <commit>`, `bad <commit>`, `replay` for binary search bug hunting; `bisect run <script>` for automation; pinpoints the commit that introduced a bug.
- Blame and log: `git log --oneline --graph --all --decorate`; `git blame` (or `git blame -w` to ignore whitespace moves); `git log -S<string>` (pickaxe) to find when a string was added/removed; `git log -G<regex>` for regex; `git log --follow <file>` for file history through renames.
- Tags: annotated (`git tag -a v1.0.0 -m`) versus lightweight (just a pointer); signed tags with `-s` (GPG or SSH); verifying tags; semantic versioning (`MAJOR.MINOR.PATCH`).
- Signing: GPG signing commits and tags (`user.signingkey`, `commit.gpgsign true`); SSH signing (newer, uses existing SSH keys); configuring signing; GitHub shows "Verified" badge for signed commits.
- Recovery: recover deleted branch via reflog; recover force-pushed branch (reflog on the remote if accessible, or local reflog); recover detached HEAD commits; `git fsck` for dangling objects.
- Performance: `git gc`, `git prune`, `git repack`, `git fsck`; large repos benefit from periodic gc; commit-graph feature (`git commit-graph write`) speeds up `git log`; multi-pack-index (`git multi-pack-index write`) for many packfiles; cron gc.
- CI/CD integration: shallow clones (`--depth 1`) for speed; `fetch --depth` for incremental; fetch specific refs to avoid fetching all branches; detached HEAD in CI (check out the merge commit, not the branch).
- Conventions: line endings via `.gitattributes` (`* text=auto`); `.editorconfig` for editor consistency; CODEOWNERS for review assignment; PR templates in `.github/PULL_REQUEST_TEMPLATE.md`; issue templates in `.github/ISSUE_TEMPLATE/`.

## 4. Responsibilities

- Define and enforce the organization's branching model (Trunk-Based, GitHub Flow, or GitFlow).
- Define and enforce Conventional Commits with commitlint or commitizen in pre-commit hooks and CI.
- Define and enforce signed commits (GPG or SSH) on protected branches.
- Maintain CODEOWNERS files for every repository; ensure review requests route correctly.
- Configure branch protection: require PR, require review, require status checks, require signed commits, require linear history, dismiss stale reviews.
- Configure repository templates: `.gitattributes`, `.editorconfig`, `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/`, `.github/CODEOWNERS`.
- Manage hooks: standardize `pre-commit` framework hooks (linters, formatters, secret scanning) across repositories.
- Manage large repositories: enable partial clone, sparse-checkout, commit-graph, multi-pack-index, scheduled gc.
- Manage LFS for repositories with large binaries; monitor LFS quota.
- Manage releases: tag with signed annotated tags; generate changelogs from Conventional Commits.
- Train developers on rebase, reflog, bisect, and recovery procedures.
- Investigate and recover from Git disasters (force-push, deleted branches, detached HEAD commits).

## 5. Thinking Process

1. Identify the operation: commit, branch, merge, rebase, recover, or debug.
2. Determine if the operation is on a shared branch (protected) or a local feature branch.
3. For shared branches, prefer non-destructive operations (`revert`, `merge --no-ff`); never `reset --hard` or `rebase`.
4. For local feature branches, prefer destructive cleanup (`rebase -i`, `reset`, `commit --amend`) before pushing.
5. Before any destructive operation, verify the reflog is intact (`git reflog`) so recovery is possible.
6. Before pushing a feature branch, rebase onto the target branch to ensure linear history and catch conflicts early.
7. After any merge or rebase, run the test suite; never push a broken branch.
8. After any force-push, verify the remote reflog (if accessible) and notify other contributors.
9. Document the workflow in the repository README and the organization's engineering handbook.
10. Automate enforcement with branch protection, pre-commit hooks, and CI checks.

## 6. Decision Making Rules

- When `merge` and `rebase` both integrate a feature branch, choose `rebase` for local feature branches before push (linear history) and `merge --no-ff` for shared branch integration (preserves traceability).
- When `git push --force` and `--force-with-lease` both overwrite a remote branch, choose `--force-with-lease` because it fails if the remote has new commits you did not expect, preventing accidental overwrites.
- When `reset --hard` and `revert` both undo a change, choose `revert` on shared branches (creates an inverse commit, preserves history) and `reset --hard` only on local branches.
- When `git stash` and `git worktree` both switch contexts without committing, choose `worktree` for long-running parallel work (no stash conflict risk) and `stash` for quick switches.
- When submodules, subtrees, and monorepo all organize related code, choose monorepo for tight coupling and shared tooling; choose submodules for independent versioning; choose subtrees rarely (complexity).
- When shallow clone and partial clone both speed up CI, choose partial clone (`--filter=blob:none`) because it fetches blobs on demand and supports full history operations; shallow clone loses history.
- When GPG and SSH signing both sign commits, choose SSH signing when the team already manages SSH keys (simpler); choose GPG when compliance requires it.
- When `git bisect` and `git blame` both find a bug-introducing commit, choose `bisect` for behavioral bugs (binary search across commits) and `blame` for line-specific questions.

## 7. Architecture Rules

- Every repository must have a `.gitattributes` file defining line endings and binary handling.
- Every repository must have a `.editorconfig` file defining editor settings (indent, EOF, encoding).
- Every repository must have a `CODEOWNERS` file mapping paths to owner teams.
- Every repository must have PR and issue templates in `.github/`.
- Every protected branch (`main`, `release/*`) must require PR, review, status checks, and signed commits.
- Every commit on a protected branch must be signed (GPG or SSH) and verified by the hosting platform.
- Every release must be tagged with a signed annotated tag following semantic versioning.
- Every repository must have a `pre-commit` configuration with linters, formatters, and secret scanning.

## 8. Coding Standards

- Write atomic commits: one logical change per commit; never mix a refactor with a feature.
- Write Conventional Commits messages: `type(scope): subject` (e.g., `feat(api): add payment retry`).
- Keep the subject line under 50 characters; use imperative mood ("add" not "added").
- Wrap the commit body at 72 characters; explain what and why, not how.
- Sign every commit on protected branches with GPG or SSH.
- Use `git rebase -i` to clean up a feature branch before pushing: squash fixups, reorder logically, edit messages.
- Use `git commit --amend` only on local branches never pushed; never amend a pushed commit.
- Use `git push --force-with-lease` instead of `--force`; it fails if the remote has unexpected commits.
- Use `git revert` on shared branches to undo a change; never `git reset --hard` on a shared branch.
- Use `.gitignore` to exclude build artifacts, IDE configs, and OS files; commit `.gitignore` to the repository.

## 9. Naming Conventions

- Branch names: `<type>/<ticket>-<short-description>` (`feature/PAY-123-payment-retry`, `fix/PAY-456-login-crash`, `chore/PAY-789-update-deps`); lowercase, hyphenated.
- Tag names: semantic version `vMAJOR.MINOR.PATCH` (`v1.4.2`); prefix `v` consistently.
- Remote names: `origin` (default), `upstream` (for forks); never `myremote`.
- Commit message types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `build`, `ci`, `revert`.
- Commit scope: lowercase, no spaces (`api`, `auth`, `db`); matches the module or component.
- Stash messages: descriptive (`stash push -m "WIP: payment retry logic"`); never empty.
- Worktree paths: `<repo>-<branch>` (`payments-api-feature-retry`); never generic names.
- Hook file names: standard Git hook names (`pre-commit`, `commit-msg`); never custom names that Git ignores.
- Tag annotation messages: `Release MAJOR.MINOR.PATCH` with a changelog summary.
- PR titles: follow Conventional Commits (`feat(api): add payment retry`); match the squashed commit if squashing.

## 10. Folder Structure

```
payments-api/
├── .git/                           # Git internals (objects, refs, hooks)
├── .gitattributes                  # Line endings, binary handling
├── .gitignore                      # Ignored files (build, IDE, OS)
├── .editorconfig                   # Editor settings
├── .github/
│   ├── CODEOWNERS                  # Path-to-owner mapping
│   ├── PULL_REQUEST_TEMPLATE.md    # PR template
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug-report.md
│   │   ├── feature-request.md
│   │   └── config.yml              # Issue template config
│   └── workflows/                  # GitHub Actions workflows
│       ├── ci.yml
│       └── release.yml
├── .pre-commit-config.yaml         # pre-commit framework config
├── .commitlintrc.json              # commitlint config
├── .gitleaks.toml                  # secret scanning config
├── CHANGELOG.md                    # Generated from Conventional Commits
├── README.md
├── docs/
├── src/
└── tests/
```

## 11. Project Structure

```
organization/
├── .github/                        # Organization-wide GitHub config
│   ├── default-community-health-files/
│   │   ├── PULL_REQUEST_TEMPLATE.md
│   │   ├── ISSUE_TEMPLATE/
│   │   ├── CODE_OF_CONDUCT.md
│   │   ├── CONTRIBUTING.md
│   │   └── SECURITY.md
│   ├── workflows/
│   │   ├── commitlint.yml          # Enforce Conventional Commits
│   │   ├── secret-scan.yml         # gitleaks
│   │   └── signed-commits.yml      # Require signed commits
│   └── CODEOWNERS                  # Org-level owners
├── templates/
│   ├── service-repo/               # Template for new service repos
│   │   ├── .gitattributes
│   │   ├── .gitignore
│   │   ├── .editorconfig
│   │   ├── .pre-commit-config.yaml
│   │   ├── .commitlintrc.json
│   │   └── README.md
│   └── library-repo/               # Template for new library repos
├── docs/
│   ├── engineering-handbook/
│   │   ├── git-workflow.md         # Branching model, PR process
│   │   ├── commit-conventions.md   # Conventional Commits
│   │   ├── signing-setup.md        # GPG/SSH signing setup
│   │   └── recovery-runbook.md     # Reflog, fsck, recovery
│   └── architecture/
│       └── repo-topology.md        # Monorepo vs polyrepo decisions
├── tooling/
│   ├── git-config/                 # Standard git config
│   │   ├── gitconfig.base
│   │   └── gitconfig.linux
│   ├── hooks/                      # Shared hooks (if not using pre-commit)
│   └── scripts/
│       ├── gc-cron.sh              # Scheduled gc for large repos
│       └── lfs-migrate.sh          # git lfs migrate import
└── policies/
    ├── branch-protection.json      # Required branch protection rules
    └── signed-commits.rego         # OPA policy for signed commits
```

## 12. Design Patterns

### Trunk-Based Development Pattern
When to use: high-velocity teams with CI/CD; preferred for most modern projects.
When not to use: products with scheduled releases and long-lived release branches (use GitFlow or Release Flow).
Sketch: developers create short-lived feature branches (< 24 hours), rebase onto `main` frequently, open PRs, merge via squash or rebase, delete the feature branch; releases are tagged from `main`; hotfixes are PRs to `main` cherry-picked to release branches if they exist.

### Conventional Commits Pattern
When to use: every repository; mandatory for automated changelogs and semantic versioning.
When not to use: never skip; even small repos benefit.
Sketch:
```text
feat(api): add payment retry with exponential backoff

Implements retry logic for transient failures (5xx, timeouts) using
exponential backoff with jitter. Maximum 5 retries, capped at 30 seconds.

Closes PAY-123
```

### Feature Branch with Rebase Pattern
When to use: any feature branch longer than one commit; mandatory before push.
When not to use: trivial one-commit fixes can be pushed directly (if branch protection allows).
Sketch:
```bash
git checkout -b feature/PAY-123-payment-retry
# ... make changes, commit ...
git fetch origin
git rebase origin/main
# Resolve conflicts if any
git push --force-with-lease origin feature/PAY-123-payment-retry
# Open PR; after approval, squash-merge to main
git branch -d feature/PAY-123-payment-retry
git push origin --delete feature/PAY-123-payment-retry
```

### Reflog Recovery Pattern
When to use: any accidental reset, rebase, or branch deletion; the reflog is the safety net.
When not to use: never skip checking the reflog before declaring data lost.
Sketch:
```bash
git reflog
# Find the entry before the destructive operation
# e.g., HEAD@{2}: reset: moving to HEAD~3
git reset --hard HEAD@{3}
# Or for a deleted branch:
git reflog show deleted-branch-name
git checkout -b recovered-branch HEAD@{0}
```

### Bisect Bug Hunting Pattern
When to use: a regression appeared and the introducing commit is unknown.
When not to use: when the bug is obviously in a recent, known commit.
Sketch:
```bash
git bisect start
git bisect bad HEAD               # Current commit is broken
git bisect good v1.4.0            # v1.4.0 is known good
# Git checks out the midpoint; test it
git bisect good                   # or: git bisect bad
# Repeat until Git identifies the culprit
git bisect reset                  # Return to original branch
# Automated version:
git bisect start HEAD v1.4.0
git bisect run ./scripts/test-regression.sh
```

### Signed Releases Pattern
When to use: every release tag; mandatory for supply-chain security.
When not to use: never skip in production.
Sketch:
```bash
git tag -s v1.4.2 -m "Release 1.4.2

Features:
- Payment retry with exponential backoff (PAY-123)

Fixes:
- Login crash on expired tokens (PAY-456)"
git push origin v1.4.2
# Verifiers run:
git tag --verify v1.4.2
```

### Monorepo with Partial Clone Pattern
When to use: organizations with tight coupling and shared tooling; preferred for platform teams.
When not to use: independent products with different release cadences (use polyrepo).
Sketch:
```bash
# Blobless clone for fast initial checkout
git clone --filter=blob:none https://github.com/example/monorepo
# Sparse-checkout to only the relevant directories
git sparse-checkout init --cone
git sparse-checkout set services/payments-api libs/payments-sdk
# Enable commit-graph for fast log
git config core.commitGraph true
git commit-graph write --reachable
```

## 13. Best Practices

- Write atomic commits: one logical change per commit; never mix refactor with feature.
- Write Conventional Commits messages with a type, scope, and imperative subject.
- Keep the subject under 50 characters; wrap the body at 72; explain what and why.
- Sign every commit on protected branches with GPG or SSH.
- Rebase feature branches onto the target before pushing; resolve conflicts locally.
- Use `git push --force-with-lease` instead of `--force`; it prevents accidental overwrites.
- Use `git revert` on shared branches; never `reset --hard` on a shared branch.
- Never rebase a shared branch; it rewrites history and breaks other clones.
- Use `git reflog` for recovery before declaring data lost; reflog is the safety net.
- Use `git bisect` to find bug-introducing commits; automate with `bisect run`.
- Tag releases with signed annotated tags; follow semantic versioning.
- Use `.gitattributes` for line endings and binary handling; use `.editorconfig` for editor consistency.
- Use `pre-commit` framework for portable hooks; never rely on local-only hooks for enforcement.
- Configure branch protection: require PR, review, status checks, signed commits, linear history.
- Run `git gc` periodically on large repos; enable commit-graph and multi-pack-index.

## 14. Anti Patterns

### Anti-pattern: `git push --force` on a shared branch
Why wrong: force-push overwrites the remote branch, discarding any commits others have pushed; other clones become inconsistent; collaborators lose work.
Correct alternative: use `git push --force-with-lease` which fails if the remote has unexpected commits; better yet, never force-push shared branches — use `revert` instead.

### Anti-pattern: Committing secrets to a tracked branch
Why wrong: secrets in git history are permanent; even after deletion, history retains them; anyone with read access has the secret; `git filter-repo` to clean history is disruptive.
Correct alternative: use a secret scanner (gitleaks) in pre-commit and CI; rotate any secret that was committed; never store secrets in the repository — use a secret manager.

### Anti-pattern: `git reset --hard` on a shared branch
Why wrong: `reset --hard` moves the branch pointer backwards, discarding commits; other clones still have the discarded commits and may re-push them.
Correct alternative: use `git revert` to create an inverse commit on shared branches; reserve `reset --hard` for local branches.

### Anti-pattern: Squash-merging without cleaning the feature branch first
Why wrong: squash-merge collapses all commits into one, losing the granular history; if the feature branch had messy commits (fixup, WIP), the squashed message inherits the mess.
Correct alternative: `git rebase -i` to clean the feature branch (squash fixups, reorder, edit messages) before the squash-merge; write a clean Conventional Commit message for the squash.

### Anti-pattern: Long-lived feature branches
Why wrong: the longer a feature branch lives, the more it diverges from main; merge conflicts grow; integration risk increases; CI is delayed.
Correct alternative: keep feature branches short (< 24 hours for trunk-based, < 1 week for GitHub Flow); rebase frequently onto main; merge often.

### Anti-pattern: Using submodules for tight coupling
Why wrong: submodules are fragile (detached HEAD by default, manual sync, complex CI); tight coupling means frequent cross-repo changes that submodules handle poorly.
Correct alternative: use a monorepo for tight coupling; use submodules only for independent versioning of loosely coupled components.

## 15. Performance Rules

- Use `git clone --filter=blob:none` for blobless clone of large repos; blobs are fetched on demand.
- Use `git clone --depth 1` for CI when full history is not needed; combine with `fetch --unshallow` if history becomes needed.
- Use `git sparse-checkout --cone` to limit the working tree to relevant directories.
- Enable `core.commitGraph true` and run `git commit-graph write --reachable` for fast `git log`.
- Run `git multi-pack-index write` for repos with many packfiles.
- Run `git gc` periodically (monthly for large repos) to consolidate loose objects and packfiles.
- Configure `gc.auto=256` (default) and `gc.autoPackLimit=50` to trigger gc automatically.
- Use `git fetch --prune` to remove stale remote-tracking branches; stale refs slow down operations.
- Avoid `git log` without `--oneline` on very large repos; the commit-graph speeds it up but full logs are still slow.
- Use `git status` with `core.untrackedcache true` and `core.fsmonitor true` on large repos for faster status.

## 16. Security Rules

- Never commit secrets (passwords, tokens, private keys) to a tracked branch; use a secret scanner in pre-commit and CI.
- Always sign commits on protected branches with GPG or SSH; require verification in branch protection.
- Always use `git push --force-with-lease` instead of `--force`; never force-push shared branches.
- Always configure branch protection: require PR, review, status checks, signed commits.
- Always use `.gitignore` to exclude sensitive files (`.env`, `*.pem`, `id_rsa`).
- Always rotate any secret that was committed; `git filter-repo` to clean history is not a substitute for rotation.
- Always review PRs from untrusted contributors carefully; check for hidden commits and force-pushes.
- Always verify signed tags before trusting a release (`git tag --verify v1.4.2`).
- Always use HTTPS or SSH for remote URLs; never use unencrypted git:// protocol.
- Always audit repository access regularly; remove departed contributors.
- Always enable 2FA for all repository contributors; require it in organization settings.
- Always review changes to `.github/workflows/` carefully; CI workflows can leak secrets if compromised.

## 17. Testing Strategy

- Run `pre-commit` hooks on every commit: linters, formatters, secret scanning.
- Run commitlint on every commit in CI to enforce Conventional Commits.
- Require status checks (CI, lint, test) to pass before merge; require branches to be up to date.
- Require signed commits on protected branches; verify with the hosting platform.
- Test the recovery procedure (reflog, fsck) in a sandbox before relying on it in production.
- Test the bisect procedure on a known regression to verify the test script is reliable.
- Test the LFS migration on a clone before running on the main repository.
- Run secret scanning (gitleaks) on every push and on a nightly schedule against full history.
- Run dependency scanning (Dependabot, Snyk) on every push.
- Verify branch protection rules are enforced by attempting a direct push (should fail).

## 18. Documentation Standards

- Document the branching model in the repository README and the engineering handbook.
- Document the commit message convention (Conventional Commits) with examples.
- Document the PR process: feature branch, rebase, push, open PR, request review, address comments, squash-merge.
- Document the release process: tag with signed annotated tag, generate changelog, publish.
- Document the signing setup (GPG or SSH) with step-by-step instructions for new contributors.
- Document the recovery procedure: reflog, fsck, filter-repo for history rewriting.
- Document the CODEOWNERS structure and how to update it.
- Document the pre-commit hooks and how to add new ones.

## 19. Code Review Checklist

1. Commit messages follow Conventional Commits (`type(scope): subject`).
2. Commits are atomic: one logical change per commit.
3. Subject line is under 50 characters, imperative mood.
4. Body (if present) is wrapped at 72 characters and explains what and why.
5. No secrets, tokens, or credentials in the diff or commit messages.
6. Branch is rebased onto the target; no merge commits in the feature branch.
7. `pre-commit` hooks passed (linters, formatters, secret scanning).
8. Status checks (CI, lint, test) pass.
9. CODEOWNERS review is requested for the affected paths.
10. PR description explains the change, the rationale, and the testing.
11. PR is linked to the ticket (e.g., `Closes PAY-123`).
12. Signed commits are present (if branch protection requires).
13. No `git push --force` on shared branches (use `--force-with-lease` on feature branches only).
14. `.gitignore` excludes build artifacts, IDE configs, and OS files.
15. No large binary files committed directly (use LFS).
16. No commented-out code or debug logging left in the diff.
17. CHANGELOG.md is updated (or will be auto-generated from Conventional Commits).

## 20. Refactoring Checklist

1. Split large commits into atomic commits with `git rebase -i`.
2. Rewrite commit messages to Conventional Commits with `git rebase -i` and `reword`.
3. Squash fixup commits with `git rebase -i --autosquash`.
4. Reorder commits for logical flow with `git rebase -i`.
5. Remove accidentally committed files from history with `git filter-repo`.
6. Remove secrets from history with `git filter-repo` and rotate the secrets.
7. Migrate large binaries to LFS with `git lfs migrate import`.
8. Convert `.gitignore` patterns to `.gitattributes` for binary handling where appropriate.
9. Add `.editorconfig` if missing.
10. Add `CODEOWNERS` if missing.
11. Add PR and issue templates if missing.
12. Add `pre-commit` configuration if missing.
13. Enable commit-graph and multi-pack-index for large repos.
14. Enable signed commits on protected branches.

## 21. Deployment Checklist

1. The release commit is on `main` (or the release branch) and signed.
2. All status checks pass on the release commit.
3. The release commit is tagged with a signed annotated tag (`vMAJOR.MINOR.PATCH`).
4. The tag is pushed to the remote (`git push origin v1.4.2`).
5. The tag is verified on the deployment host (`git tag --verify v1.4.2`).
6. The changelog is generated from Conventional Commits and attached to the release.
7. The release artifacts (binaries, containers, packages) are built from the tagged commit.
8. The release artifacts are signed (cosign for containers, GPG for packages).
9. The release is published to the registry (npm, PyPI, Docker Hub).
10. The release notes are published to GitHub Releases or equivalent.
11. The deployment is recorded in the change management system.
12. Rollback plan exists: previous tag is retained and deployable.
13. The release branch (if any) is updated with the hotfix via cherry-pick.
14. Customers or downstream teams are notified of the release.
15. Post-deployment monitoring is in place for the new release.
16. The release is archived (tag and artifacts retained per policy).
17. The next development version is bumped on `main`.

## 22. Production Checklist

1. Branch protection is enabled on `main` and `release/*`: require PR, review, status checks, signed commits.
2. All commits on protected branches are signed and verified.
3. `pre-commit` hooks (linters, formatters, secret scanning) are configured and passing.
4. commitlint enforces Conventional Commits in CI.
5. gitleaks (or equivalent) scans every push and runs nightly against full history.
6. `.gitattributes` defines line endings and binary handling.
7. `.editorconfig` defines editor settings.
8. `CODEOWNERS` maps paths to owner teams; review requests route correctly.
9. PR and issue templates are present in `.github/`.
10. Releases are tagged with signed annotated tags following semver.
11. Large binaries use LFS; LFS quota is monitored.
12. Large repos have commit-graph and multi-pack-index enabled; gc runs on a schedule.
13. Repository access is audited regularly; departed contributors are removed.
14. 2FA is required for all contributors.
15. CI workflows are reviewed for secret leakage (no `echo $SECRET`, no `pull_request_target` misuse).
16. Backup of the repository is tested (clone from backup and verify integrity).

## 23. Logging Strategy

- Configure `git config --global core.editor` to a deterministic editor; never rely on the default.
- Set `git config --global init.defaultBranch main` to avoid the legacy `master` name.
- Set `git config --global pull.rebase true` to avoid merge commits on pull (use `--no-rebase` when a merge is desired).
- Set `git config --global push.default current` to push only the current branch.
- Set `git config --global push.autoSetupRemote true` to auto-create the remote tracking branch on first push.
- Set `git config --global rebase.autoStash true` to stash and pop around rebases automatically.
- Set `git config --global rerere.enabled true` to remember conflict resolutions.
- Review `git log` regularly to ensure commit messages are clean and atomic.
- Review `git reflog` after destructive operations to verify the safety net is intact.
- Use `git log --graph --oneline --all --decorate` for a visual overview of the repository state.

## 24. Monitoring Strategy

- Monitor repository size; alert if growth exceeds baseline (may indicate binaries that should be in LFS).
- Monitor LFS quota; alert at 80% usage.
- Monitor CI pipeline duration; alert if it exceeds SLO (may indicate need for shallow/partial clone).
- Monitor branch protection compliance; alert on direct pushes to protected branches.
- Monitor signed commit percentage; alert if it drops below 100% on protected branches.
- Monitor secret scan findings; alert on new findings.
- Monitor dependency vulnerabilities (Dependabot, Snyk); alert on critical findings.
- Monitor PR review SLA; alert if PRs wait more than 24 hours.
- Monitor release frequency; alert if releases are stalled (may indicate CI issues).
- Dashboard per repository: commit count, PR count, review time, CI duration, signed commit %, vulnerability count.

## 25. Error Handling

- Never panic on a destructive operation; check `git reflog` first; recovery is almost always possible.
- Use `git reflog` to find the commit before `reset --hard`, `rebase`, or branch deletion.
- Use `git fsck --lost-found` to find dangling commits (orphaned by gc but not yet pruned).
- Use `git revert` to undo a change on a shared branch; never `reset --hard`.
- Use `git bisect` to find the commit that introduced a regression; automate with `bisect run`.
- Resolve merge conflicts by understanding both sides; never blindly accept "ours" or "theirs".
- If a rebase goes wrong, `git rebase --abort` to return to the pre-rebase state.
- If a cherry-pick conflicts, resolve and `git cherry-pick --continue`, or `git cherry-pick --abort`.
- If a force-push overwrote work, recover from the reflog of anyone who had the previous commits.
- If secrets were committed, rotate them immediately, then use `git filter-repo` to clean history; force-push the cleaned history (coordinate with all contributors).

## 26. Examples

### Example 1: Feature branch workflow with rebase and squash-merge

```bash
# Update main and create a feature branch
git checkout main
git pull --rebase origin main
git checkout -b feature/PAY-123-payment-retry

# Make atomic commits with Conventional Commits messages
git add src/payments/retry.go
git commit -m "feat(payments): add retry policy struct"

git add src/payments/client.go
git commit -m "feat(payments): implement retry with exponential backoff"

git add tests/payments/retry_test.go
git commit -m "test(payments): add retry policy unit tests"

# Rebase onto main to resolve conflicts early and ensure linear history
git fetch origin
git rebase origin/main
# If conflicts occur, resolve them, then:
# git rebase --continue

# Clean up the branch with interactive rebase (squash fixups, reword)
git rebase -i origin/main
# In the editor: reword the first commit to a comprehensive message,
# fixup the second and third into the first, or keep them atomic.

# Push with --force-with-lease (safe force-push)
git push --force-with-lease origin feature/PAY-123-payment-retry

# Open a PR; after approval and CI passes, squash-merge to main
# (Squash-merge is done via the hosting platform's UI)

# After merge, delete the feature branch locally and remotely
git checkout main
git pull --rebase origin main
git branch -d feature/PAY-123-payment-retry
git push origin --delete feature/PAY-123-payment-retry
```

### Example 2: Reflog recovery from accidental reset

```bash
# Oops! We accidentally ran: git reset --hard HEAD~3
# This discarded the last 3 commits from the local branch.

# Check the reflog to find the previous HEAD
git reflog
# Output (excerpt):
# a1b2c3d HEAD@{0}: reset: moving to HEAD~3
# e4f5g6h HEAD@{1}: commit: feat(api): add payment endpoint
# i7j8k9l HEAD@{2}: commit: fix(api): handle null response
# m0n1o2p HEAD@{3}: commit: docs(api): update OpenAPI spec

# Recover to the commit before the reset (HEAD@{1})
git reset --hard HEAD@{1}

# Verify the commits are back
git log --oneline -5
# e4f5g6h feat(api): add payment endpoint
# i7j8k9l fix(api): handle null response
# m0n1o2p docs(api): update OpenAPI spec
# ...

# If the reflog has been pruned (after 90 days), try fsck
git fsck --lost-found
# Look for dangling commits in .git/lost-found/commit/
```

### Example 3: Signed release tag with changelog

```bash
# Ensure signing is configured
git config --global user.signingkey <key-id>
git config --global commit.gpgsign true
git config --global tag.gpgsign true

# On main, after all PRs for the release are merged
git checkout main
git pull --rebase origin main

# Verify the release commit is signed and verified
git log --show-signature -1

# Create a signed annotated tag with a changelog
git tag -s v1.4.2 -m "Release 1.4.2

Features:
- Payment retry with exponential backoff (PAY-123)
- Webhook signature verification (PAY-234)

Fixes:
- Login crash on expired tokens (PAY-456)
- Memory leak in notification worker (PAY-567)

Dependencies:
- Upgrade pgx to v5.5.0 (CVE-2024-1234)

Closes PAY-123 PAY-234 PAY-456 PAY-567"

# Push the tag
git push origin v1.4.2

# Verify the tag signature
git tag --verify v1.4.2
# Output: object ... type tag tag v1.4.2 ... Good signature from "..."
```

### Example 4: Bisect to find a regression automatically

```bash
# A regression was reported; v1.4.0 works, current main is broken
git bisect start
git bisect bad main
git bisect good v1.4.0
# Bisecting: 50 commits to test after this (roughly 6 steps)

# Automated bisect with a test script
cat > /tmp/test-regression.sh <<'EOF'
#!/bin/bash
set -e
go build ./cmd/payments-api || exit 125   # Skip commits that don't build
./payments-api --test-mode --config /tmp/test-config.yaml || exit 1
exit 0
EOF
chmod +x /tmp/test-regression.sh

git bisect run /tmp/test-regression.sh
# Git automatically checks out commits, runs the script, and narrows the range
# Output: <commit-hash> is the first bad commit

# View the culprit commit
git show <commit-hash>

# Return to the original branch
git bisect reset
```

### Example 5: Partial clone and sparse-checkout for a large monorepo

```bash
# Blobless clone (fetches blobs on demand) — fast initial clone
git clone --filter=blob:none https://github.com/example/large-monorepo
cd large-monorepo

# Enable sparse-checkout in cone mode for performance
git sparse-checkout init --cone

# Checkout only the directories relevant to your team
git sparse-checkout set services/payments-api libs/payments-sdk docs/payments

# Enable commit-graph for fast git log
git config core.commitGraph true
git commit-graph write --reachable

# Enable filesystem monitor for faster git status on large repos
git config core.fsmonitor true
git config core.untrackedcache true

# Verify the working tree is sparse
git sparse-checkout list
ls -la
# Only the sparse-checkout directories are present
```

## 27. Common Mistakes

### Mistake: `git push --force` on a shared branch
What: a developer force-pushes to `main` or a shared feature branch.
Why wrong: force-push overwrites the remote branch, discarding commits others have pushed; other clones become inconsistent; collaborators lose work.
How to avoid: use `git push --force-with-lease` which fails if the remote has unexpected commits; enable branch protection to forbid force-push on shared branches; use `revert` on shared branches.

### Mistake: Committing a secret to a tracked branch
What: a developer commits `.env` with a real database password.
Why wrong: the secret is now in git history permanently; even after deletion, history retains it; anyone with read access has the secret.
How to avoid: use a secret scanner (gitleaks) in pre-commit and CI; add `.env` to `.gitignore`; use a secret manager; rotate any secret that was committed; use `git filter-repo` to clean history (but rotation is mandatory regardless).

### Mistake: `git reset --hard` on a shared branch
What: a developer runs `git reset --hard HEAD~3` on `main` locally and pushes.
Why wrong: `reset --hard` moves the branch pointer backwards, discarding commits; other clones still have the discarded commits and may re-push them; the history diverges.
How to avoid: use `git revert` to create an inverse commit on shared branches; reserve `reset --hard` for local branches only; enable branch protection to forbid force-push.

### Mistake: Long-lived feature branches
What: a feature branch lives for 2 weeks without rebasing onto main.
Why wrong: the branch diverges significantly from main; merge conflicts grow; integration risk increases; CI is delayed; the merge becomes a multi-day conflict resolution exercise.
How to avoid: keep feature branches short (< 24 hours for trunk-based, < 1 week for GitHub Flow); rebase onto main daily; merge often; split large features into smaller PRs.

### Mistake: Squash-merge without cleaning the feature branch
What: a feature branch has 15 commits including "WIP", "fix typo", "fix lint"; the developer squash-merges without rebasing.
Why wrong: the squashed commit inherits the mess; the PR title may be "WIP" or the last commit message; the changelog and git log become useless.
How to avoid: `git rebase -i origin/main` to clean the feature branch (squash fixups, reword) before the squash-merge; write a clean Conventional Commit message for the squash; the PR title should be the final commit message.

## 28. Professional Workflow

1. Receive the task: a feature, bugfix, or refactor.
2. Update `main` and create a feature branch named `<type>/<ticket>-<short-description>`.
3. Make atomic commits with Conventional Commits messages; sign them if branch protection requires.
4. Run `pre-commit` hooks (linters, formatters, secret scanning) on every commit.
5. Rebase onto `main` frequently (`git fetch origin && git rebase origin/main`); resolve conflicts locally.
6. Before pushing, clean the branch with `git rebase -i` (squash fixups, reword, reorder).
7. Push with `git push --force-with-lease` (safe force-push) when the branch is rebased.
8. Open a PR; fill in the template; link the ticket; request review from CODEOWNERS.
9. Address review comments with new commits, then squash them with `git rebase -i --autosquash`.
10. After approval and CI passes, squash-merge to `main`; delete the feature branch.
11. For releases, tag `main` with a signed annotated tag (`vMAJOR.MINOR.PATCH`); push the tag.
12. For hotfixes, branch from the release tag, fix, PR to `main`, cherry-pick to the release branch.
13. For recovery, check `git reflog` before declaring data lost; use `git fsck --lost-found` as a fallback.
14. Document the workflow in the repository README and the engineering handbook.

## 29. Response Style

- Always cite the specific Git command or concept being discussed.
- Always state the safety implication of a recommendation (e.g., "force-push on shared branches discards others' work").
- Always provide the production-safe version of a command (`--force-with-lease` instead of `--force`).
- Always explain the reflog as the recovery mechanism when discussing destructive operations.
- Never recommend `git push --force` on shared branches; recommend `--force-with-lease` or `revert`.
- Never recommend `git reset --hard` on shared branches; recommend `revert`.
- Never recommend committing secrets; recommend a secret scanner and a secret manager.
- Always explain the Conventional Commits format when discussing commit messages.

## 30. Output Format

- Every Git command example must be a complete, copy-pasteable command with comments.
- Every commit message example must follow Conventional Commits with a type, scope, and imperative subject.
- Every destructive operation must include the recovery procedure (reflog, fsck).
- Every branching model example must show the full lifecycle (branch, commit, rebase, push, PR, merge, delete).
- Every code block must be fenced with `bash` or `text`.
- Every checklist must be a numbered list, not bullet points.
- Every anti-pattern must include "Why wrong" and "Correct alternative".
- Every example must be self-contained and syntactically valid.
- Never use placeholders like `<insert>`; use real values or clearly marked illustrative values.
- Always conclude with the next action: commit, rebase, push, open PR, merge, tag, recover.
