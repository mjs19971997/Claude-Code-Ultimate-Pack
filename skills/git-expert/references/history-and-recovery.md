# History and Recovery

Reference for rewriting history without an editor, resolving conflicts, finding regressions, recovering lost work, and removing leaked secrets. Verified against Git 2.56.0 and git-filter-repo 2.47.0 (2026-10). Every command here runs non-interactively. Commands that rewrite shared history or push forcibly are run only when the user asks.

## 1. Non-interactive rebase recipes

```bash
git fetch origin
git rebase origin/main                    # replay current branch onto the latest main
git rebase --autosquash origin/main       # fold "fixup!" and "squash!" commits (Git 2.44+ without -i)
git rebase --update-refs origin/main      # also move branches that point into the rebased range
git rebase --rebase-merges origin/main    # keep merge topology instead of flattening
git rebase --onto origin/main OLD_BASE BRANCH   # transplant BRANCH, dropping commits up to OLD_BASE
git rebase --exec 'make test' origin/main       # run a command after each replayed commit
```

- Create fixups while working: `git commit --fixup=<sha>`, `git commit --fixup=amend:<sha>` (also edits the message), `git commit --fixup=reword:<sha>`, or `git commit --squash=<sha>`.
- Control flow after a conflict: `git rebase --continue`, `git rebase --skip`, `git rebase --abort`. In scripts, `GIT_EDITOR=true git rebase --continue` accepts the existing message.
- `rebase.autoStash=true` (local config) stashes and restores a dirty tree around a rebase; `git rebase --autostash` does it once.
- Squash a whole branch into one commit without a todo list: `git reset --soft $(git merge-base origin/main HEAD)` then `git commit -m "feat: summary"`. Create a `backup/` branch first.
- Move the last commit to a new branch: `git branch feature/new` then `git reset --keep HEAD~1` (refuses if it would lose local changes).
- Change the last commit: `git commit --amend` (message or content) only while it is unpublished.
- Reorder or edit older commits non-interactively: use fixup commits plus `--autosquash`, or the experimental `git history` command (subcommands drop, fixup, reword, split and squash as of Git 2.56; reword and split can open an editor or prompt). Its behavior may change, so check `git history -h` first.
- Replay without touching the working tree (server-side style): `git replay` is experimental; check `git replay -h`.

## 2. Merge strategies and revert

- `git merge --ff-only origin/main` fails rather than creating a merge commit.
- `git merge --no-ff feature` keeps an explicit merge commit; `git merge --squash feature` stages the combined change for one new commit.
- Undo a published change: `git revert <sha>` for a normal commit, `git revert -m 1 <merge-sha>` for a merge (keeps parent 1, the mainline). Reverting a merge means the branch's commits cannot be merged again until the revert is itself reverted.
- Cherry-pick across branches: `git cherry-pick -x <sha>` (adds "cherry picked from" line), `git cherry-pick A..B` for a range, `--no-commit` to combine several into one commit.
- `git merge-base A B` shows the fork point; `git log A...B --left-right --oneline` shows what each side has.

## 3. Conflict resolution

1. `git status` lists unmerged paths; `git diff --name-only --diff-filter=U` lists only those.
2. Set `git config --local merge.conflictStyle zdiff3` to show `<<<<<<<`, the base section `|||||||`, `=======` and `>>>>>>>` markers.
3. Edit the file, remove all markers, then `git add <path>`. Check nothing is left: `git diff --check` and `grep -rn '^<<<<<<<\|^>>>>>>>' .`.
4. Take one side wholesale: `git checkout --ours -- <path>` or `--theirs`. During a rebase the meaning is reversed: "ours" is the branch being rebased onto, "theirs" is your commit being replayed.
5. Finish with `git rebase --continue` or `git commit` (merge). Abort safely with `git rebase --abort` or `git merge --abort`.
6. Binary or generated files: choose a side and regenerate (`git checkout --theirs -- package-lock.json && npm install`), rather than editing by hand.
7. Re-create the conflicted merge of one file to see the original state: `git checkout --merge -- <path>`.

**rerere** (reuse recorded resolution): `git config --local rerere.enabled true`. Git records how you resolved a conflict and applies the same resolution when it recurs, which helps long-running rebases and repeated test merges. `git rerere status`, `git rerere diff` and `git rerere forget <path>` inspect and undo recordings.

## 4. Bisect

```bash
git bisect start                 # begin
git bisect bad                   # current commit is broken
git bisect good v1.4.0           # last known good
# Git checks out the midpoint; test it, then mark: git bisect good | bad | skip
git bisect run ./scripts/check.sh   # automate; script exit 0 = good, 1-127 except 125 = bad, 125 = skip
git bisect log > bisect.log      # keep the trail
git bisect reset                 # return to the original HEAD
```

- Custom terms for non-bug searches: `git bisect start --term-old=fast --term-new=slow`.
- Limit to paths with `git bisect start -- src/module/`.
- Make the test script self-contained (build, then test) and non-interactive; a script that cannot build the commit should exit 125.

## 5. Reflog and recovery

The reflog records where `HEAD` and each branch pointed locally. It is per-clone and not pushed.

```bash
git reflog                               # HEAD movements, newest first
git reflog show feature/x                # one branch
git reflog --date=iso                    # with timestamps
git branch rescue/x <sha-or-HEAD@{n}>    # make the lost state reachable again (safe)
git switch -c rescue/x HEAD@{2}          # same, and switch
```

| Situation | Recovery |
|---|---|
| Bad rebase or merge | `git reflog`, find the entry before it (`HEAD@{n}`), `git branch rescue HEAD@{n}`; if you want the branch back there, `git reset --hard rescue` after reviewing |
| Deleted local branch | find its last commit in `git reflog`, `git branch <name> <sha>` |
| Dropped stash | `git fsck --no-reflogs --unreachable \| grep commit` then `git show <sha>`; apply with `git stash apply <sha>` |
| Amended or reset-away commit | reflog entry for the old commit, `git cherry-pick <sha>` or branch from it |
| Uncommitted work lost by `reset --hard` | not in the reflog; try `git fsck --lost-found` for staged blobs, editor backups, or filesystem snapshots |
| Wrong commit on main (unpushed) | `git branch topic` (keep it), then `git reset --keep origin/main` |
| Wrong commit on main (pushed) | `git revert <sha>`, push normally |

Reflog expiry defaults are 90 days for reachable entries and 30 days for unreachable ones (`gc.reflogExpire`, `gc.reflogExpireUnreachable`). Do not run `git gc --prune=now` or `git reflog expire --expire=now --all` while you still might need to recover.

## 6. Undo cheat sheet

| Goal | Command |
|---|---|
| Unstage a file | `git restore --staged <path>` |
| Discard working-tree edits to a file | `git restore <path>` (permanent for uncommitted edits) |
| Restore a file from another commit | `git restore --source=<rev> -- <path>` |
| Undo last commit, keep changes staged | `git reset --soft HEAD~1` |
| Undo last commit, keep changes unstaged | `git reset --mixed HEAD~1` |
| Remove untracked files (preview first) | `git clean -nd` then `git clean -fd` |
| Stash including untracked | `git stash push -u -m "label"` |
| See what a branch has that main lacks | `git log --oneline origin/main..feature` |

## 7. Removing a leaked secret from history

Order matters.

1. **Revoke and rotate** the credential at its provider. This is the actual fix; everything after is cleanup. Check provider audit logs for use of the old credential.
2. **Decide whether a rewrite is worth it.** Rewriting changes commit hashes, breaks open pull requests and signatures, and requires every collaborator to re-clone. If the secret is rotated, many teams stop here.
3. **Work in a fresh clone** (filter-repo refuses to run on a non-fresh clone without `--force`, and removes the `origin` remote to prevent accidental pushes).

```bash
pip install git-filter-repo          # or your package manager; need 2.47 or later for -sdr
git clone https://git.example.com/org/repo.git repo-clean
cd repo-clean
git filter-repo --sensitive-data-removal --invert-paths --path config/secrets.yml
# or replace strings in all non-binary files, using a file of expressions:
git filter-repo --sensitive-data-removal --replace-text ../replacements.txt
```

- `replacements.txt` lines are literal strings by default (`SECRET_VALUE==>REMOVED`), `regex:` prefixed for regex.
- `--sensitive-data-removal` fetches all refs so hidden refs (such as pull request refs on GitHub) are also covered, and prints the First Changed Commit(s), the files of changed refs (`.git/filter-repo/changed-refs`), and any orphaned LFS objects. Keep that output.
- `git filter-repo --analyze` writes a report under `.git/filter-repo/analysis/` to find large or unexpected blobs before cleaning.
- Verify: `git log --all -S'SECRET_VALUE' --oneline` returns nothing; `git rev-list --all --objects | grep config/secrets.yml` returns nothing.
4. **Publish the rewrite** (only when the user asks): re-add the remote and force-push all refs, for example `git remote add origin <url>` then `git push --force --mirror origin`. Protected branches must allow it temporarily. On GitHub, `refs/pull/*` refs are read-only and fail; hidden pull request refs and cached views are removed by GitHub Support after you provide the repository name, affected pull request count and First Changed Commit(s). Forks keep the data until their owners clean them or delete the fork.
5. **Coordinate**: collaborators discard old clones (re-clone) or follow the filter-repo manual's clean-up steps, and rebase rather than merge old branches onto the new history.
6. **Prevent repeats**: push protection and secret scanning on the host, a pre-commit secret scanner, `.gitignore` for env files, and a secrets manager.

Related: GitHub's guide "Removing sensitive data from a repository".

## 8. Signing with SSH keys

```bash
git config --local gpg.format ssh
git config --local user.signingkey ~/.ssh/id_ed25519.pub     # or key::ssh-ed25519 AAAA...
git config --local commit.gpgsign true
git config --local tag.gpgsign true
git config --local gpg.ssh.allowedSignersFile ~/.config/git/allowed_signers
```

- `allowed_signers` format: `<email> <key-type> <public-key>` per line, optionally with `namespaces="git"`.
- Verify: `git log --show-signature -5`, `git verify-commit <sha>`, `git verify-tag v1.2.3`.
- Add the same public key to the hosting account as a signing key (a separate entry from an authentication key) so the host marks commits Verified.
- Hardware-backed keys (`ed25519-sk`) work as signing keys; GPG and S/MIME formats remain supported with `gpg.format=openpgp` or `x509`.
- Signatures are tied to commit hashes and are dropped or invalidated by history rewrites; re-sign after a rewrite if policy requires it.
