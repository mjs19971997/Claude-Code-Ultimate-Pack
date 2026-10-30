---
name: git-expert
description: >-
  Uses Git safely and effectively for everyday work and repository maintenance: branching strategies (trunk-based, GitHub flow), merge versus non-interactive rebase, conflict resolution and rerere, bisect, reflog recovery, worktrees, sparse-checkout and partial clone, SSH commit signing, hooks, .gitattributes line endings, Git LFS, and removing leaked secrets from history with git filter-repo. Use when working with git commands, branches, merges, rebases, history rewrites, recovery from mistakes, monorepo performance, or repository hygiene. Not for GitHub rulesets, Actions or repository security settings (use cicd-expert) or code review practice (use code-review-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Git Expert

This skill covers Git itself: the object model, branching and integration workflows, history editing without an editor, recovery, large and monorepo repositories, signing, hooks, attributes, and secret removal. Commands are written to run non-interactively so they work from scripts and agent sessions. Hosting-platform features (GitHub rulesets, pull request policy, Actions) live in cicd-expert.

> Verified against Git 2.56.0 (git/git tags and Documentation/RelNotes), git-filter-repo 2.47.0 and Git LFS 3.8.0 (2026-10). Git 3.0 is announced in BreakingChanges but not released.

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

- Covered: objects, refs and the index; branching models; merge, rebase (non-interactive), cherry-pick, revert; conflicts and rerere; bisect; reflog and recovery; stash; worktrees; sparse-checkout, partial and shallow clones; `git maintenance`; commit and tag signing; hooks; `.gitattributes`; Git LFS; history rewriting with git filter-repo.
- Not covered: GitHub branch protection, rulesets, CODEOWNERS and Actions (cicd-expert), pull request review technique (code-review-expert), secret management policy beyond Git (secure-coding-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Object model | Four object types: blob (file content), tree (directory), commit (tree + parents + message), annotated tag. Objects are content-addressed; SHA-1 is the default hash, SHA-256 is available with `git init --object-format=sha256` (limited hosting support) |
| Refs | Branches are files under `refs/heads/`, tags under `refs/tags/`, remote-tracking under `refs/remotes/`; `HEAD` points at the current branch or a commit (detached) |
| Index | The staging area between working tree and next commit; `git restore --staged <path>` unstages, `git add <path>` stages |
| Switching | `git switch <branch>`, `git switch -c <new>`, `git restore <path>` replace the overloaded `git checkout` for daily use |
| Integration | `git merge --ff-only`, `git merge --no-ff`, `git rebase <base>`, `git rebase --onto <new> <old> <branch>`, `git cherry-pick -x`, `git revert -m 1 <merge>` |
| Autosquash | `git commit --fixup=<sha>` then `git rebase --autosquash <base>`; autosquash works without `-i` since Git 2.44 (not with the legacy apply backend) |
| Safety net | `git reflog` keeps local ref movements (defaults: 90 days for reachable entries, 30 days for unreachable ones) |
| Force push | `git push --force-with-lease[=<ref>:<expect>]` and `--force-if-includes` refuse to overwrite commits you have not seen |
| Signing | `gpg.format=ssh` signs with SSH keys (Git 2.34+); verify with `gpg.ssh.allowedSignersFile` and `git log --show-signature` |
| Hooks | Scripts in `core.hooksPath`; config-based hooks (`hook.<name>.event`, `hook.<name>.command`) exist since Git 2.54 |
| Large repos | Partial clone (`--filter=blob:none`), `git sparse-checkout set --cone`, `git maintenance` (geometric strategy is the default since 2.54), commit-graph |
| Experimental | `git history` (drop, fixup, reword, split, squash subcommands as of 2.56) and `git replay` are marked experimental; check `git history -h` before relying on them |

## 3. Workflow

1. Inspect before acting: `git status -sb`, `git log --oneline --graph --decorate -20`, `git diff --stat`, `git remote -v`.
2. Create a short-lived branch from the up-to-date base: `git fetch origin && git switch -c feature/short-name origin/main`.
3. Commit small, coherent changes: `git add <paths>` then `git commit -m "type: summary"`. Stage by path, not `git add -A`, when the tree has unrelated files.
4. Keep the branch current: `git fetch origin` then `git rebase origin/main` for an unpublished or single-owner branch, or `git merge origin/main` for a shared one.
5. Fold review fixes into the commit they belong to: `git commit --fixup=<sha>`, then `git rebase --autosquash origin/main`.
6. Publish: `git push -u origin HEAD`; after a rebase of an already-pushed branch, `git push --force-with-lease` only when the user asked for a force push.
7. Integrate through the hosting platform's merge method (squash, rebase or merge commit) agreed by the team; delete the branch after merge.
8. When something goes wrong, stop and read `git reflog` before running another mutating command.

## 4. Decision Rules

- Force push, deleting a remote branch (`git push origin --delete <b>`), and any `git config --global` or `--system` change happen only when the user explicitly asks. Prefer repository-local config (`git config --local`, or no flag).
- Destructive local commands (`git reset --hard`, `git clean -fd`, `git checkout -- .`, `git branch -D`, `git stash drop`) need the user's go-ahead unless the loss is trivially recoverable; run `git clean -n` first to preview.
- Rebase private, unpublished commits; merge (or revert) once commits are shared. Never rebase a branch others have based work on.
- Squash merge for a clean trunk history with one commit per change; rebase merge when each commit is meaningful and tested; merge commit when branch topology matters.
- Teaching and examples use non-interactive commands only: `git rebase <base>`, `--onto`, `--autosquash`, `--exec`. Interactive todo-list editing is not used here; `git commit --fixup` plus `--autosquash` covers reordering and folding, and `git reset --soft <base>` plus a new commit covers "squash everything".
- Trunk-based development (short branches, merges to main at least daily, feature flags) fits teams with strong CI; GitHub flow (branch, pull request, merge, deploy) fits most others; long-lived release branches only when several versions are supported.
- Use `git revert` for changes already in shared history; use reset only on local, unpushed work.
- Large binaries go to Git LFS or external storage; secrets never go in Git at all.
- A leaked secret is revoked and rotated first; history rewriting is optional cleanup after that.

## 5. Coding Standards

- Commit message: imperative summary of about 50 characters, blank line, body wrapped near 72 explaining why. Conventional Commits (`feat:`, `fix:`, `docs:`) are fine when the team uses release tooling that parses them.
- One logical change per commit; every commit builds and passes tests so `git bisect` stays usable.
- Branch names: `feature/<topic>`, `fix/<topic>`, `release/<version>`; lowercase, hyphen separated, no spaces.
- Tags: annotated and signed for releases (`git tag -s v1.2.3 -m "v1.2.3"`), semantic version names.
- `.gitignore` for build output, dependencies, local env files and editor files; commit `.env.example`, never `.env`.
- Use `git diff --check` before committing to catch trailing whitespace and conflict markers.
- Scripts call plumbing or porcelain with explicit flags and `--porcelain`/`-z` output where parsed; avoid parsing default human output.

## 6. Project Structure

```
.
├── .gitattributes        # eol normalization, binary/LFS markers, diff and merge drivers
├── .gitignore
├── .git-blame-ignore-revs  # bulk-format commits, used via blame.ignoreRevsFile
├── .githooks/            # versioned hooks, enabled with: git config core.hooksPath .githooks
│   ├── pre-commit        # fast checks only (format, secret scan on staged files)
│   └── commit-msg
├── CODEOWNERS            # at .github/CODEOWNERS or repo root; review routing (see cicd-expert)
└── .lfsconfig            # optional shared LFS endpoint settings
```

## 7. Design Patterns

- **Feature branch with rebase**: `git switch -c feature/x origin/main`, commit, `git fetch && git rebase origin/main`, push, open a pull request, squash or rebase merge.
- **Fixup and autosquash**: `git commit --fixup=<sha>` per review comment, then `git rebase --autosquash origin/main` before merge.
- **Stacked branches**: `git rebase --update-refs origin/main` moves every branch pointing into the rebased range; `git rebase --onto origin/main <old-parent> <child>` re-parents one branch after its parent was squash-merged.
- **Worktree per task**: `git worktree add ../app-hotfix -b hotfix/x origin/main` keeps a review or hotfix checkout beside the main one without stashing.
- **Release branch with backports**: `git cherry-pick -x <sha>` records the origin commit in the message.
- **Bisect with a test**: `git bisect start; git bisect bad HEAD; git bisect good v1.4.0; git bisect run ./test.sh; git bisect reset`.
- **Monorepo clone**: partial clone plus cone sparse-checkout; see [references/large-repos.md](references/large-repos.md).
- **History cleanup and recovery**: see [references/history-and-recovery.md](references/history-and-recovery.md).

## 8. Best Practices

- Fetch often; `git pull --ff-only` (or `pull.ff=only` in local config) fails instead of creating surprise merge commits.
- Set `merge.conflictStyle=zdiff3` locally to see the common ancestor in conflict markers; enable `rerere.enabled=true` when you repeatedly resolve the same conflicts.
- Keep `.git-blame-ignore-revs` for formatting-only commits and set `blame.ignoreRevsFile` so `git blame` skips them.
- Use `git log -S'text' --oneline` (pickaxe) or `git log -G'regex'` to find when text changed, `git blame -w -C -C -C` to follow moved code.
- Use `git range-diff old..new` to compare two versions of a rebased series.
- Keep repositories small: no build artifacts, no vendored binaries, no generated lockfiles you do not need.
- Write down the team's merge method and branch naming in CONTRIBUTING so history stays uniform.
- Prefer `git stash push -u -m "label"` for a quick pause, but a WIP commit on a branch is safer than a stash that can be forgotten; `git stash export` and `import` (Git 2.51+) can move stashes between clones.

## 9. Performance

- Run `git maintenance start` in large clones; it schedules prefetch, commit-graph and repack tasks. Git 2.54 made the geometric repack strategy the default for maintenance.
- `fetch.writeCommitGraph=true` and `core.untrackedCache=true` speed `log`, `status` and graph walks; `core.fsmonitor=true` helps on very large working trees where the built-in monitor is supported.
- Use `git clone --filter=blob:none --sparse` or `--filter=tree:0` for monorepos and CI; use `--depth=1` only for read-only CI builds because shallow clones limit history commands.
- `git gc` and `git repack` are rarely needed manually once maintenance runs; avoid `gc --aggressive`.
- Avoid committing large generated files; every clone downloads them forever unless history is rewritten.

## 10. Security

- Rotate before rewriting: assume a pushed secret is compromised. Revoke it, issue a new one, then optionally remove it with `git filter-repo --sensitive-data-removal` (needs git-filter-repo 2.47 or later) as described in [references/history-and-recovery.md](references/history-and-recovery.md).
- Block secrets before they land: a pre-commit hook running a secret scanner on staged changes, plus server-side push protection on the host. Local hooks are advisory because `--no-verify` skips them; enforce the same checks in CI.
- Sign commits and tags where provenance matters. SSH signing: `git config gpg.format ssh`, `git config user.signingkey ~/.ssh/id_ed25519.pub`, `git config commit.gpgsign true`, and `gpg.ssh.allowedSignersFile` listing trusted identities. Register the public key as a signing key on the host so it shows as verified.
- Treat hooks and `.gitattributes` filters in cloned repositories as code: `core.hooksPath` is local config and is not applied by clone, but filter drivers named in `.gitattributes` only run if configured locally. Do not run `git lfs install` or scripts from untrusted repositories blindly.
- Keep credentials out of remote URLs (`https://token@host/...` is stored in `.git/config`); use a credential helper or SSH keys.
- Keep global identity changes out of automation; set `user.name` and `user.email` per repository when needed.

## 11. Testing

- Hooks: run them against a scratch repository (`git init /tmp/hooktest`) and trigger each event; check the exit code semantics (non-zero aborts for `pre-commit`, `commit-msg`, `pre-push`).
- History edits: before a rebase, mark the starting point with `git branch backup/<name>`; compare after with `git range-diff backup/<name>...HEAD` and `git diff backup/<name> HEAD` (empty means the trees are identical).
- Attributes: `git check-attr -a <path>` shows which attributes apply; `git ls-files --eol` shows index and working-tree line endings.
- Ignore rules: `git check-ignore -v <path>` explains which pattern matches.
- Bisect scripts: exit 0 for good, 1 to 127 except 125 for bad, 125 to skip an untestable commit; 128 and above aborts the bisect.
- CI check that history is linear or signed when policy demands it: `git log --merges origin/main..HEAD`, `git log --show-signature`.

## 12. Review Checklist

- [ ] Commits are atomic, build, and have messages that explain why.
- [ ] No secrets, tokens, `.env` files or large binaries in the diff (`git diff --stat`, secret scan).
- [ ] Line endings are normalized by `.gitattributes`, not by individual editors.
- [ ] Branch is rebased or merged with the target; no stray merge commits from `git pull` defaults.
- [ ] Force pushes use `--force-with-lease` and were requested by the user.
- [ ] No `git config --global` changes made implicitly.
- [ ] Tags for releases are annotated (and signed when required).
- [ ] LFS patterns are tracked before the first large file is added.
- [ ] Hooks that the team depends on are versioned and also enforced in CI.

## 13. Production Notes

- Protect default branches on the host so force pushes and deletions are blocked for everyone, including admins where policy allows (see cicd-expert).
- Mirror or back up important repositories with `git clone --mirror`; restore by pushing the mirror.
- After any history rewrite, every collaborator re-clones or follows the filter-repo cleanup instructions; one stale clone pushing back reintroduces the removed data.
- Git 3.0 is planned to change defaults (default branch `main`, reftable ref storage, SHA-256); until it ships, set `init.defaultBranch` per team convention and test tooling against reftable (`git init --ref-format=reftable`) before relying on file-based refs.
- Keep the Git client current; the hosting platform and CI images may lag (GitHub-hosted Ubuntu runners install Git from the git-core PPA).
- Releases from signed tags: `git tag -s`, `git push origin v1.2.3` (push the single tag, not `--tags`).

## 14. Examples

Rebase a feature branch onto the latest main, folding fixups, without opening an editor:

```bash
git fetch origin
git branch backup/feature-x                    # cheap safety ref
git commit --fixup=3f2a9c1                     # earlier, per review comment: records "fixup! <title>"
git rebase --autosquash origin/main            # Git 2.44+: no -i needed
git range-diff backup/feature-x...HEAD         # review what changed
git push --force-with-lease                    # only when the user asked to force push
```

Re-parent a child branch after its parent was squash-merged, and rebase a stack:

```bash
git fetch origin
# child was based on feature-a; feature-a is now squashed into main
git rebase --onto origin/main feature-a feature-b
# or move all branches in a stack at once
git rebase --update-refs origin/main
```

Find the commit that introduced a bug and recover a deleted branch:

```bash
git bisect start HEAD v1.4.0 --
git bisect run sh -c 'make test >/dev/null 2>&1'
git bisect reset

git reflog --date=iso | grep 'checkout: moving from feature/x'
git branch feature/x-restored <sha-from-reflog>
```

SSH signing for one repository only (no global change):

```bash
git config --local gpg.format ssh
git config --local user.signingkey ~/.ssh/id_ed25519.pub
git config --local commit.gpgsign true
git config --local gpg.ssh.allowedSignersFile .git/allowed_signers
echo "dev@example.com $(cut -d' ' -f1,2 ~/.ssh/id_ed25519.pub)" > .git/allowed_signers
git commit -m "feat: signed change"
git log --show-signature -1
```

## 15. Common Mistakes

- **`git push --force`**: overwrites teammates' commits. Use `--force-with-lease` and only on a request from the user.
- **Rebasing a shared branch**: rewrites commits others built on. Merge or revert instead.
- **Committing a secret then deleting it in a later commit**: the secret remains in history. Rotate it, then clean history if needed.
- **`git add -A` or `git add .` in a dirty tree**: stages `.env`, build output and unrelated edits. Stage by path and review `git diff --cached`.
- **`git reset --hard` to "undo" without a backup ref**: discards uncommitted work permanently. Create a branch or stash first.
- **`git pull` with default merge behavior**: creates noisy merge commits. Use `git pull --ff-only` or fetch then rebase.
- **Mixing line endings**: editors flip CRLF and LF and produce whole-file diffs. Add `.gitattributes` with `* text=auto eol=lf` and run `git add --renormalize .` once.
- **Large binaries in plain Git**: bloat every clone. Track them with LFS from the start.
- **Relying on hooks alone**: `--no-verify` bypasses them; duplicate checks in CI.
- **`git config --global` in scripts**: silently changes the user's identity and behavior everywhere. Use `--local` or `git -c key=value`.
- **`git push --tags`**: pushes every local tag, including stale ones. Push named tags.
- **Long-lived feature branches**: conflicts compound. Merge small changes behind feature flags.
- **Using submodules for tightly coupled code**: version skew and clone friction; prefer a monorepo or a package dependency.

## 16. References

- [references/history-and-recovery.md](references/history-and-recovery.md): non-interactive rebase recipes, conflict handling, rerere, bisect, reflog and fsck recovery, undo cheat sheet, secret removal with git filter-repo, SSH signing details.
- [references/large-repos.md](references/large-repos.md): partial and shallow clones, sparse-checkout, worktrees, maintenance, `.gitattributes` and line endings, Git LFS setup and migration, hooks distribution.
- Official docs: https://git-scm.com/docs , https://git-scm.com/book , https://github.com/git/git/tree/master/Documentation/RelNotes , https://github.com/newren/git-filter-repo , https://git-lfs.com
