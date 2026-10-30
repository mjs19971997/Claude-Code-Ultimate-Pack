# Large Repositories, Attributes, LFS and Hooks

Reference for keeping big repositories fast, normalizing files, storing large binaries, and distributing hooks. Verified against Git 2.56.0 and Git LFS 3.8.0 (2026-10).

## 1. Partial and shallow clones

```bash
git clone --filter=blob:none https://git.example.com/org/big.git        # blobless: history, trees; blobs fetched on demand
git clone --filter=tree:0 https://git.example.com/org/big.git           # treeless: smallest; slower history commands
git clone --depth=1 --branch main https://git.example.com/org/big.git   # shallow: CI read-only builds
git fetch --unshallow                                                   # convert shallow to full later
```

- Blobless clones suit developers: history commands work, file contents download when checked out. Treeless clones suit CI that needs a single checkout and no history walks.
- Shallow clones break `git describe`, merge-base searches and blame; use `--depth` with `--no-tags` only for pure build jobs, or fetch more depth when needed (`git fetch --deepen=50`).
- Partial clone requires server support; the remote becomes a promisor remote. Avoid commands that touch all blobs (`git grep` on history, `git log -p` over everything) in a blobless clone, because each missing blob triggers a fetch.
- `git backfill` downloads missing blobs of a blobless clone in batches (instead of one request per blob), which speeds up later `git blame` and diffs; see `git backfill -h` for the options your version supports.

## 2. Sparse checkout

```bash
git clone --filter=blob:none --sparse https://git.example.com/org/monorepo.git
cd monorepo
git sparse-checkout set --cone services/api libs/shared    # cone mode: whole directories
git sparse-checkout add docs
git sparse-checkout list
git sparse-checkout disable
```

- Cone mode matches directories (fast, recommended). Non-cone mode uses gitignore-style patterns; the Git docs recommend against it because of its performance and correctness problems.
- In cone mode, files directly in the repository root and in the parents of included directories are always checked out.
- Combine with `core.fsmonitor` and `core.untrackedCache` on very large trees.

## 3. Worktrees

```bash
git worktree add ../app-review origin/feature-y          # detached checkout of a PR branch
git worktree add -b hotfix/x ../app-hotfix origin/main   # new branch in a new directory
git worktree list
git worktree remove ../app-hotfix                        # refuses if dirty unless --force
git worktree prune                                       # forget directories removed by hand
```

- A branch can be checked out in only one worktree at a time.
- Worktrees share the object store and refs, so fetches are shared and disk use is low.
- `git worktree lock` protects worktrees on removable media.
- Per-worktree config: `git config --worktree` (requires `extensions.worktreeConfig`).

## 4. Maintenance

```bash
git maintenance start            # registers the repo and schedules background tasks (launchd, systemd timers, cron or Task Scheduler)
git maintenance run --task=prefetch --task=commit-graph
git maintenance stop
git config --local maintenance.strategy incremental     # alternatives: gc, geometric (default since Git 2.54)
```

- Tasks: `prefetch`, `commit-graph`, `loose-objects`, `incremental-repack` / `geometric-repack`, `pack-refs`, `gc`.
- `git count-objects -vH` and the separate git-sizer tool reports growth; `git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | sort -k3 -n | tail` lists the largest objects.
- Reftable ref storage (`git init --ref-format=reftable`) improves ref-heavy repositories; it is planned to become the default in Git 3.0. Check hosting and tooling support first.

## 5. `.gitattributes` and line endings

```gitattributes
# Normalize text files in the repository to LF; checkout converts per platform settings
* text=auto eol=lf

# Windows-only scripts keep CRLF
*.bat text eol=crlf
*.cmd text eol=crlf
*.sh  text eol=lf

# Binary files: no conversion, no textual diff
*.png binary
*.jpg binary
*.pdf binary

# Lockfiles and generated code: collapse in diffs and review UIs
package-lock.json -diff linguist-generated=true
*.min.js          -diff linguist-generated=true

# Git LFS tracked patterns (written by `git lfs track`)
*.psd filter=lfs diff=lfs merge=lfs -text
```

- `text=auto` lets Git detect text; `eol=lf` forces LF in the working tree as well, which keeps shell scripts working on Windows checkouts. Without `eol`, checkout uses `core.autocrlf`/`core.eol`.
- After adding or changing the rules, renormalize once: `git add --renormalize .` and commit the result. Add that commit to `.git-blame-ignore-revs`.
- Inspect: `git check-attr -a path/to/file`; `git ls-files --eol`.
- Useful attributes: `merge=union` (append-only files such as changelogs), `export-ignore` (omit from `git archive`), `diff=<driver>` for custom textconv, `linguist-*` for GitHub language statistics.
- Do not set `core.autocrlf` globally to fix a repository problem; put the policy in `.gitattributes` so every clone behaves the same.

## 6. Git LFS

```bash
git lfs install                       # once per machine/user: installs the filter and hooks in Git config
git lfs track "*.psd" "assets/**/*.mp4"   # writes patterns to .gitattributes
git add .gitattributes
git add design/logo.psd && git commit -m "chore: add design assets via LFS"
git lfs ls-files                      # files stored as LFS pointers
git lfs status
git lfs fetch --all && git lfs checkout   # materialize objects
git lfs fsck                          # verify local LFS objects
```

- Track patterns before adding the first matching file. Files committed before tracking stay as normal blobs.
- Convert existing history (this rewrites commits and needs coordination, so only on request): `git lfs migrate import --include="*.psd" --everything`, then force-push as described in history-and-recovery.md. Preview with `git lfs migrate info`.
- Hosts limit file size and LFS storage and bandwidth; GitHub blocks regular files above 100 MiB and warns above 50 MiB (check current limits and quotas). Prefer object storage or package registries for build artifacts.
- CI: use `actions/checkout` with `lfs: true` when LFS content is needed; otherwise skip it to save bandwidth. Cache `.git/lfs` if the same objects are fetched repeatedly.
- Shared server settings live in `.lfsconfig` (committed); credentials do not.
- LFS locking (`git lfs lock`, `lfs.locksverify`) helps with unmergeable binary files.

## 7. Hooks distribution

- Client hooks are not cloned. Distribute them by committing a directory and pointing Git at it per clone: `git config --local core.hooksPath .githooks` (a bootstrap script or `make setup` can run this).
- Git 2.54 added config-based hooks, which can be defined centrally (for example in a system or global config managed by IT) without files: `hook.<friendly-name>.event=pre-commit` and `hook.<friendly-name>.command=<command>`; run one manually with `git hook run pre-commit`. The friendly name must not equal an event name.
- Hook frameworks (pre-commit, lefthook, husky) pin tool versions and run only on changed files; keep hooks fast (seconds) and move slow checks to CI.
- Common hooks: `pre-commit` (format, lint staged files, secret scan), `commit-msg` (message format), `pre-push` (quick tests), `post-merge`/`post-checkout` (dependency install hints). Server-side: `pre-receive`, `update`.
- Hooks must not require interactive input in automation and should exit non-zero with a clear message.
- Never rely on hooks alone: `git commit --no-verify` skips `pre-commit` and `commit-msg`; mirror important checks in CI and branch protection.

## 8. Submodules and subtrees

- Submodules pin another repository at an exact commit: `git submodule add <url> path`, `git clone --recurse-submodules`, `git submodule update --init --recursive`. Use them for loosely coupled, independently versioned dependencies, not for tightly coupled code.
- `git config --local submodule.recurse true` makes pull/checkout update submodules.
- Subtree (`git subtree`) merges another repository's history into a directory with no extra clone steps; useful for vendoring with occasional upstream sync.
- Often a package manager dependency or a monorepo with sparse checkout is simpler than either.
