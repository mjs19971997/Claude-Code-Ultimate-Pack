---
name: bash-scripting-expert
description: >-
  Writes, reviews and hardens Bash 5.x and POSIX sh scripts: strict mode and its errexit caveats, quoting, arrays, parameter expansion, traps and cleanup, getopts, safe file iteration, locking, GNU/BSD portability, ShellCheck, shfmt and bats-core tests. Use when editing .sh, .bash or .bats files, shebangs, .shellcheckrc, install or release scripts, or fixing word-splitting, set -e, temp-file and quoting bugs. Not for system administration or systemd units (use linux-expert), CI pipeline structure (use cicd-expert), Dockerfiles (use docker-expert), or Git hook workflows (use git-expert).
license: MIT
metadata:
  version: "3.2.0"
---

# Bash Scripting Expert

This skill covers shell scripts that have to keep working: Bash 4.4 to 5.3 and POSIX sh, strict-mode behaviour and its limits, quoting and expansion, arrays, error handling with traps, argument parsing, safe handling of files and temporary data, locking, portability between GNU and BSD userlands, and the ShellCheck, shfmt and bats-core toolchain. It also states when a script should become a Python program. Host administration, CI pipeline layout, container images and Git hook policy belong to other skills.

> Verified against GNU Bash 5.3 (first public release July 2025; 5.2.21 run locally), ShellCheck 0.11.0 (run locally), shfmt 3.14.1 (run locally), bats-core 1.14.0 per its changelog (npm package bats 1.13.0 run locally) and dash 0.5.12 (2026-10).

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

- Covered: Bash scripts and functions, POSIX sh scripts, shebangs, `set -euo pipefail` and `shopt` options, quoting, parameter expansion, indexed and associative arrays, `[[ ]]` and arithmetic, traps, exit codes, `getopts` and manual long options, `read`, `mapfile`, `find -print0`, here-documents, process substitution, `flock`, `mktemp`, GNU versus BSD differences, ShellCheck, shfmt, bats-core, ShellSpec and shell security.
- Not covered: Linux administration, services and systemd units (linux-expert); CI pipeline structure and workflow files (cicd-expert); Dockerfile and image design (docker-expert); Git hook workflows and branching policy (git-expert); secrets and application-level hardening beyond the shell (secure-coding-expert); log and metric pipelines (observability-expert).
- Zsh, fish, PowerShell and Windows batch files are different languages; apply only the POSIX parts of this skill to them.

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Bash versions | Bash 5.3 is the current release (July 2025). The NEWS summary lists `${ command; }` and `${| command; }` command substitutions that run without forking, `source -p PATH`, `compgen -V VAR` and `read -E`. Check the NEWS file before depending on a 5.3-only feature. macOS still ships `/bin/bash` 3.2 (no associative arrays, no `mapfile`), and many distributions ship 5.1 or 5.2 |
| Shebangs | `#!/usr/bin/env bash` finds the first bash in PATH (needed on macOS and the BSDs, where a newer bash is in `/usr/local/bin` or `/opt/homebrew/bin`). `#!/bin/sh` promises POSIX only; on Debian and Ubuntu it is dash, on other systems it may be bash in POSIX mode or BusyBox ash |
| Strict mode | `set -e` (errexit), `set -u` (nounset), `set -o pipefail`, plus `shopt -s inherit_errexit` (4.4+) so command substitutions obey `-e`. Strict mode catches some mistakes; it is not a substitute for checking the commands that matter. Details and traps: [references/strict-mode-and-errors.md](references/strict-mode-and-errors.md) |
| errexit exceptions | `-e` is ignored in a command tested by `if`, `while`, `until`, `&&`, `\|\|` or `!`, in every function called from such a context, and for any command in a pipeline except the last (unless pipefail). `local x=$(cmd)` and `export x=$(cmd)` return the status of `local`/`export`, not of `cmd` |
| Traps | `trap cmd EXIT` runs on normal exit and after `exit`, and on termination by INT or TERM when the shell handles them. `ERR` fires where `-e` would exit; `set -E` (errtrace) makes functions, command substitutions and subshells inherit it. `trap` with a signal name keeps the shell alive unless the handler exits |
| Expansion | Quote every expansion unless splitting or globbing is wanted. `"${arr[@]}"` expands to one word per element, `"${arr[*]}"` to one word. `${v:-d}` default, `${v:?msg}` required, `${v#p}`/`${v##p}`/`${v%p}`/`${v%%p}` trim, `${v//a/b}` replace, `${v^^}` and `${v,,}` change case (4.0+), `${v@Q}` shell-quote (4.4+) |
| Arrays | Indexed arrays since 2.x; associative arrays need `declare -A` (4.0+); `mapfile -t` / `readarray` (4.0+) and `mapfile -d ''` for NUL input (4.4+); namerefs `local -n` (4.3+). An empty array under `set -u` is safe from 4.4 on |
| Conditionals | `[[ ]]` is a Bash keyword: no word splitting or globbing inside, `==` and `!=` match patterns on the right when unquoted, `=~` matches an ERE, `&&`/`\|\|` work inside. `[ ]` and `test` are commands with POSIX semantics; `-a` and `-o` inside them are obsolescent |
| Arithmetic | `$(( ))` expands to a value; `(( ))` is a command whose status is 1 when the result is 0, so `((i++))` with `i=0` fails under `set -e`. Leading zeros mean octal: use `$((10#$n))`. Integers are signed 64-bit |
| Reading input | `while IFS= read -r line` keeps whitespace and backslashes. Add `|| [[ -n $line ]]` to keep a last line without newline. Read NUL-delimited data with `read -r -d ''` or `mapfile -d ''` |
| Locking | `flock` (util-linux) on a file descriptor gives mutual exclusion that disappears when the process dies. macOS has no `flock` command by default; `mkdir lockdir` is the portable atomic primitive |
| Tooling | ShellCheck 0.11.0 (static analysis, `-s bash\|sh\|dash\|ksh`, `-x`, `-S severity`, `.shellcheckrc`); shfmt 3.14.1 (`-i N`, `-ci`, `-bn`, `-ln bash\|posix`, `-d`, `-w`, EditorConfig); bats-core 1.14.0 (`@test`, `run`, `setup`, `$status`, `$output`, `${lines[@]}`); ShellSpec (BDD, its changelog's newest release is 0.28.1 from 2021, so check project activity before adopting) |

## 3. Workflow

1. Read the existing script and its callers first: the shebang, `set` options, how it is invoked (cron, CI, `make`, interactive), the target platforms (Linux only or also macOS) and whether a `.shellcheckrc`, `.editorconfig` or `.pre-commit-config.yaml` exists.
2. Decide the dialect from the shebang and platforms: `sh` means POSIX only, `bash` means Bash 4.4+ features are fine unless macOS `/bin/bash` 3.2 must run the script. Say which bash floor you assumed.
3. Write or change the smallest unit. Quote everything, declare `local` variables, and use arrays for lists of words rather than strings.
4. Run `bash -n script.sh` (syntax), `shellcheck script.sh`, and `shfmt -d` with the project's flags. Fix every finding or add a `# shellcheck disable=SCxxxx` with a reason on the line above.
5. Run the script on hostile input: spaces, newlines and a leading dash in file names, an empty argument, no arguments, a missing file, and unset optional variables.
6. Add or update bats tests for the changed behaviour, including exit codes and stderr text.
7. Report the commands that ran, the bash version used, and any behaviour that depends on a GNU-only tool.

## 4. Decision Rules

- If the script must run on any Unix with no bash guarantee (Alpine, minimal containers, installers), write POSIX sh and test with dash and `shellcheck -s sh`; otherwise use Bash and say so in the shebang.
- If macOS `/bin/bash` 3.2 must run the script, avoid associative arrays, `mapfile`, `${v,,}`, `declare -n` and `&>>`; otherwise require Bash 4.4+ and fail early with a version check (section 14).
- If the script needs data structures, JSON or YAML parsing, HTTP with retries, date arithmetic beyond `date -d`, more than about 200 lines of logic, or unit-testable modules, write it in Python instead (see python-expert). Keep shell for gluing processes, pipelines and environment setup. Use `jq` for JSON in shell, never `grep` and `sed`.
- If a loop body calls `sed`, `awk`, `cut` or `basename` per line on a large input, use parameter expansion or one `awk` pass for the whole input (section 9).
- If a command may legitimately fail, handle it explicitly: `if cmd; then`, `cmd || rc=$?`, or `cmd || true` with a comment. Never turn `set -e` off for a whole script to avoid this.
- If a list of items is passed between functions, use an array (`"${items[@]}"`) or NUL-delimited stream; use newline-delimited text only when every item is known not to contain newlines.
- If two copies of a script must not run at once, use `flock -n` on a file descriptor; if only one machine is involved and `flock` exists, do not hand-roll PID files.
- If output goes to a person or another program, send data to stdout and diagnostics to stderr, and make exit codes meaningful.
- If you need an option that takes `--long` names, parse them by hand in a `case` loop or translate them to short options (see the reference); do not use the external `getopt` for portable scripts, because BSD and GNU versions differ.

## 5. Coding Standards

- Start with `#!/usr/bin/env bash` (or `#!/bin/sh` for POSIX) and a one-line purpose comment. Use `set -Eeuo pipefail` and `shopt -s inherit_errexit` for new Bash scripts, understanding the caveats in section 8.
- Quote variable and command substitutions: `"$var"`, `"$(cmd)"`, `"${arr[@]}"`. Use `--` before file operands (`rm -- "$f"`, `grep -e "$pat" -- "$f"`) so names starting with a dash are not options.
- Use `[[ ]]` in Bash and `[ ]` in POSIX sh. Use `(( ))` for arithmetic tests and `$(( ))` for values. Do not use `-a`/`-o` inside `[ ]`.
- Use `$(cmd)`, never backticks. Use `printf` instead of `echo` for anything that is not a fixed string, because `echo` handles `-n`, `-e` and backslashes differently between shells.
- Declare function variables with `local`; split declaration and assignment (`local x; x=$(cmd)`) so the exit status is not lost (SC2155). Use `readonly` for constants and `declare -r`/`-i`/`-A`/`-n` where they add meaning.
- Name functions `lower_snake_case`, constants and exported variables `UPPER_CASE`, local variables `lower_case`. Prefix library functions with a namespace (`lib::log` is valid in Bash; `lib_log` works everywhere).
- Format with `shfmt -i 2 -ci` (or the project's setting) and lint with ShellCheck; do not argue with the tool in review.
- Write diagnostics to stderr with a small `log`/`die` helper that includes the script name; never print secrets, even under `set -x` (see section 10).
- Use `cd -- "$dir" || exit` (or `|| return`); a failed `cd` followed by `rm` is a classic disaster. Resolve the script directory with `dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)`.
- Prefer long option names in scripts (`--recursive`, `--force`) when the tool supports them on every target, for readability.
- Keep functions short, return status with `return`, and pass data in arguments or stdout; avoid global state except for configuration set once at the top.

## 6. Project Structure

```text
tools/
|-- bin/
|   `-- backup-logs            # executable entry point, no .sh suffix needed
|-- lib/
|   |-- log.bash               # sourced helpers, no top-level side effects
|   `-- retry.bash
|-- test/
|   |-- backup-logs.bats       # bats-core tests
|   |-- test_helper.bash       # shared setup, loaded with: load test_helper
|   `-- fixtures/
|-- .shellcheckrc              # shell=bash, external-sources=true, source-path=SCRIPTDIR
|-- .editorconfig              # indent_style/indent_size read by shfmt
`-- Makefile                   # lint and test targets (or a CI job)
```

- Executables get the executable bit and a shebang; libraries are sourced, have no shebang requirement, and use a `.bash` or `.sh` suffix so tooling detects them.
- Source libraries relative to the script: `source "$(dirname -- "${BASH_SOURCE[0]}")/../lib/log.bash"`, with `# shellcheck source=../lib/log.bash` for ShellCheck.
- Keep a single `main "$@"` at the bottom of a script and guard it if the file is also sourced by tests: `if [[ ${BASH_SOURCE[0]} == "$0" ]]; then main "$@"; fi`.
- Use a Makefile target or CI step such as `shellcheck -x $(git ls-files '*.sh' '*.bash')`, `shfmt -d .` and `bats test/` so lint and tests run the same way locally and in CI. Pipeline layout itself belongs to cicd-expert.

## 7. Design Patterns

- **main function**: all logic in functions, one call to `main "$@"` at the end. This avoids global-scope surprises and makes functions testable by sourcing.
- **log and die helpers**: `log()` writes a timestamped line to stderr; `die rc msg` logs and exits. Cost: a `date` subprocess per call, so use `printf '%(%FT%T)T' -1` (Bash 4.2+) in hot paths.
- **cleanup trap**: create all temporary data under one `mktemp -d` directory and remove it in a single `EXIT` trap that preserves the original exit status.
- **atomic file replacement**: write to `mktemp` in the destination directory, then `mv` over the target; readers see the old or the new file, never half a file.
- **lock by file descriptor**: `exec 9>"$lock"; flock -n 9 || exit 75`; the lock is released when the process exits.
- **retry with backoff**: a small function taking a maximum count and a command, doubling the delay; always cap attempts and total time.
- **dispatch table**: map sub-commands to functions with an associative array or a `case`, and call `"cmd_${name}"` only after validating `name` against an allow-list.
- **dependency check**: `need() { command -v "$1" >/dev/null || die 127 "missing: $1"; }` at the start, rather than failing half way.
- **dry-run flag**: wrap mutating commands in a `run()` function that prints instead of executing when `DRY_RUN=1`; build the command as an array so printing and execution see the same words.
- **idempotent steps**: test the desired state before acting (`mkdir -p`, `ln -sfn`, `grep -qxF line file || printf '%s\n' line >>file`) so reruns are safe.

## 8. Best Practices

- Treat `set -e` as a safety net, not control flow. Check the commands whose failure matters with `if`, `||` and explicit `die`, and read the exception list in section 2 before trusting it.
- Prefer an explicit `|| exit` or `|| die` over relying on errexit inside functions that are ever called in an `if` or `||` context, because errexit is silently off there.
- Use `trap ... EXIT` for cleanup, not `ERR`. Combine with `trap 'exit 130' INT` and `trap 'exit 143' TERM` so signals run the EXIT trap. Single-quote trap strings so variables expand when the trap runs (SC2064).
- Use `mktemp` for every temporary file or directory, never a fixed name in `/tmp`. Create files with a restrictive `umask 077` when they hold sensitive data.
- Use exit codes consistently: 0 success, 1 general failure, 2 usage error, 64-78 (sysexits.h values such as 64 usage, 66 no input, 75 temporary failure) when callers care, 126/127 are reserved by the shell for not-executable and not-found, and 128+N means death by signal N.
- Read configuration from environment variables with defaults (`: "${TIMEOUT:=30}"`) and validate them early (`[[ $TIMEOUT =~ ^[0-9]+$ ]] || die 2 ...`).
- Iterate over files with globs (`for f in ./*.log`) and `shopt -s nullglob` or a test for an unmatched pattern; use `find -print0` with `read -d ''` or `xargs -0` for recursive work.
- Use `printf '%s\n' "$var"` and here-strings (`<<<"$var"`) to feed data to commands; avoid `echo "$var" | cmd`.
- Keep scripts idempotent and safe to interrupt: test state first, write atomically, and make every step restartable.
- Document required tools, environment variables, exit codes and examples in the `usage` text, and make `--help` exit 0 on stdout.
- Do not parse `ls`, `ps` or `df` output in scripts. Use globs, `find`, `stat`, `pgrep`, or tool-specific machine-readable options.
- Use `command -v tool` to test for a tool; `which` is not portable and prints nothing consistent.

## 9. Performance

- Every `$(...)`, pipe stage and external command forks a process. Inside loops, replace them with built-ins: `${f##*/}` for `basename`, `${f%/*}` for `dirname`, `${s//a/b}` for `sed s///g`, `[[ =~ ]]` for `grep -q`, `$((a+b))` for `expr`, `printf -v var` instead of `var=$(printf ...)`, `read -r a b <<<"$line"` for `cut`.
- Do not write `cat file | cmd`; use `cmd < file`. Do not call `wc`, `grep` and `awk` in series when one `awk` pass computes everything.
- Read a file once with `while IFS= read -r line; do ... done < file` or `mapfile -t lines < file`; both are fine for thousands of lines. Past a few hundred thousand lines, a loop in Bash is slow compared with `awk`, `sort`, `join` or a Python script.
- Use `xargs -0 -P N` or GNU `parallel` for independent jobs, and `wait -n` (4.3+) to limit a pool of background jobs. Always check job exit codes.
- Use `${ cmd; }` (Bash 5.3 only) or `printf -v` to avoid command-substitution forks where the target Bash allows it.
- Avoid `sort | uniq -c | sort -rn` pipelines on huge data when `awk` with an associative array does it in one pass; set `LC_ALL=C` for faster, byte-wise sorting and matching when locale rules are not needed.
- Measure with `time`, `bash -x` with `PS4='+ $EPOCHREALTIME '` (Bash 5.0+), or `hyperfine` if installed; do not guess.
- Large `for x in $(seq 1 1000000)` loops should be `for ((i = 1; i <= n; i++))`; the arithmetic for-loop uses no subprocess.

## 10. Security

- Never use `eval` on data you do not fully control. Build commands as arrays (`cmd=(tar -czf "$out" -- "${files[@]}"); "${cmd[@]}"`), use `printf %q` or `${var@Q}` when you must produce shell-safe text, and use `declare -n` rather than `eval` for indirect variables.
- Never pass untrusted input to `bash -c`, `sh -c`, `ssh host "cmd $input"`, `xargs sh -c '...'` with interpolation, or `find -exec sh -c` with the file name spliced into the command string. Pass values as positional arguments (`sh -c 'cmd "$1"' _ "$f"`).
- Validate input against an allow-list pattern before use (`[[ $name =~ ^[A-Za-z0-9._-]+$ ]]`), and reject names beginning with `-` or containing `/` or `..` when they become file names.
- Set a trusted `PATH` at the top of privileged scripts (`PATH=/usr/sbin:/usr/bin:/sbin:/bin; export PATH`) or call tools by absolute path; never include `.` or an empty element in PATH. Use `command -p` or explicit paths for security-critical tools.
- Do not `curl ... | sh` or `bash <(curl ...)`. Download to a temporary file over HTTPS (`--proto '=https' --tlsv1.2 --fail`), verify a pinned SHA-256 or a signature, then run or install it. Fetch the checksum from a separate trusted channel; a checksum served next to the file from the same host adds little.
- Treat `$IFS`, `$PATH`, `$ENV`, `$BASH_ENV`, `LD_PRELOAD` and similar inherited environment as untrusted in setuid-like or `sudo` contexts. Bash scripts should not be setuid; use `sudo` rules with fixed command paths.
- Create temp files with `mktemp`, set `umask 077` before writing secrets, and never put secrets in command-line arguments (visible in `ps` and `/proc`); pass them through a file descriptor, a mode-0600 file or the environment of a single process.
- `set -x` prints expanded commands, including secrets. Disable it around sensitive commands (`{ set +x; } 2>/dev/null`) or never enable it in production.
- Avoid world-writable directories (`/tmp`) for fixed names; check symlink and ownership assumptions with `[[ -L $f ]]` and `stat` when handling files in shared locations.
- Run ShellCheck in CI; rules such as SC2086 (unquoted expansion), SC2046 (unquoted `$(...)`), SC2115 (`rm -rf "$dir/"*` with possibly empty `dir`) and SC2064 (trap string expanded too early) flag classic injection and deletion mistakes.
- Prefer `rm -rf -- "${dir:?}/"` style guards or a validated path variable over bare `rm -rf "$dir"/*`; never run recursive deletes on a path that came from input without checking it is under the expected base.

## 11. Testing

- Use bats-core for behaviour tests (`bats test/`, `-r` for subdirectories, `--tap` or `-F junit` for CI, `-j N` for parallel runs when GNU parallel is installed). `run cmd` captures `$status`, `$output` and `${lines[@]}`; `run -N cmd` asserts exit status N and `run !` asserts non-zero (both need `bats_require_minimum_version 1.5.0`).
- Use `setup`/`teardown` per test and `$BATS_TEST_TMPDIR` for files (cleaned automatically). Use `setup_file` for expensive one-time setup.
- Make scripts testable: source them from the test with the `main` guard, call functions directly, and stub external commands by putting fake executables first in `PATH` inside the test.
- Test the unhappy paths: missing arguments, bad options, files with spaces and newlines, empty input, a failing dependency, interruption by signal, and a second concurrent instance.
- Run ShellCheck, `shfmt -d` and `bash -n` before the tests. Run the suite under the oldest bash and under `sh` (dash) when the script claims portability.
- ShellSpec is an alternative BDD framework that supports many shells. Its newest changelog entry is 0.28.1 (2021), so verify that it is maintained enough for your needs before choosing it over bats-core.
- Use `kcov` or `bashcov` only if coverage is required; line coverage of shell is approximate. More patterns: [references/testing-shellcheck-bats.md](references/testing-shellcheck-bats.md).

## 12. Review Checklist

- [ ] Shebang matches the dialect used; no bashisms in `#!/bin/sh` scripts (`shellcheck -s sh` passes).
- [ ] `set -euo pipefail` (and `inherit_errexit` for Bash) present, and no critical command sits in a context where errexit is disabled.
- [ ] Every expansion is quoted; arrays are used for word lists; `--` precedes file operands.
- [ ] `local` variables are declared, with declaration and assignment split when the substitution's status matters.
- [ ] Temporary files come from `mktemp`; one `EXIT` trap cleans up and keeps the exit status.
- [ ] Argument parsing handles `--`, `--help`, unknown options and missing operands with exit code 2.
- [ ] No `eval`, `bash -c "$input"`, `curl | sh`, `ls` parsing or unchecked `rm -rf`.
- [ ] Diagnostics go to stderr, data to stdout; exit codes are documented.
- [ ] Concurrency is handled (`flock`) where two runs would corrupt state; steps are idempotent.
- [ ] GNU-only flags (`sed -i`, `readlink -f`, `date -d`, `grep -P`) are absent or guarded when macOS or BSD is a target.
- [ ] ShellCheck and `shfmt -d` are clean, and every `disable` has a reason.
- [ ] Tests cover success, failure, odd file names and the exit status.

## 13. Production Notes

- Run unattended scripts with an explicit `PATH`, `umask`, `LC_ALL=C` (or a fixed locale) and working directory, because cron, systemd and CI provide minimal and different environments. Unit definitions and cron setup belong to linux-expert.
- Log to stderr with timestamps and a script name; let the supervisor (journald, CI, container runtime) capture it. Exit non-zero on any failure so the scheduler notices.
- Handle `SIGTERM` for long-running scripts: forward it to child processes (`kill -- "-$pgid"` or `kill "$pid"`), wait for them, then exit 143. A trap does not run while the shell waits on a foreground command; run the work in the background with `&` and `wait` so the trap fires promptly.
- Make installers and deploy scripts safe to rerun, print what they would change with `--dry-run`, and verify downloads with a pinned checksum.
- Version scripts with the code that calls them; print a version with `--version`; record the minimum Bash version in the usage text and check `BASH_VERSINFO` at the start.
- Prefer `exec` for the last command of a wrapper script so signals reach the real process and no extra shell stays resident.
- Limit blast radius: use `set -u` plus `${var:?}` guards before destructive paths, and run as the least-privileged user.
- Upgrades: when moving from Bash 5.2 to 5.3 re-run the test suite with `shopt` compatibility levels (`BASH_COMPAT`, `shopt -s compat52`) only if a regression appears; check the NEWS file for incompatible changes first.

## 14. Examples

Minimal strict-mode skeleton with usage, cleanup and a version guard (checked with ShellCheck 0.11.0 and shfmt 3.14.1; the full script with long options is in the strict-mode reference):

```bash
#!/usr/bin/env bash
set -Eeuo pipefail
shopt -s inherit_errexit nullglob

((BASH_VERSINFO[0] > 4 || (BASH_VERSINFO[0] == 4 && BASH_VERSINFO[1] >= 4))) || {
  echo "bash 4.4 or newer required" >&2
  exit 1
}

readonly PROG=${0##*/}

log() { printf '%s: %s\n' "$PROG" "$*" >&2; }
die() {
  local rc=$1
  shift
  log "error: $*"
  exit "$rc"
}

WORKDIR=
cleanup() {
  local rc=$?
  trap - EXIT
  [[ -n $WORKDIR && -d $WORKDIR ]] && rm -rf -- "$WORKDIR"
  exit "$rc"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

main() {
  (($# == 1)) || die 2 "usage: $PROG FILE"
  [[ -r $1 ]] || die 66 "cannot read: $1"
  WORKDIR=$(mktemp -d "${TMPDIR:-/tmp}/${PROG}.XXXXXX")
  sort -- "$1" >"$WORKDIR/sorted"
  wc -l <"$WORKDIR/sorted"
}

main "$@"
```

Safe iteration over names with spaces and newlines, and reading a file whose last line has no newline:

```bash
while IFS= read -r -d '' f; do
  printf 'found: %s\n' "$f"
done < <(find . -type f -name '*.log' -print0)

while IFS= read -r line || [[ -n $line ]]; do
  printf '[%s]\n' "$line"
done <input.txt
```

Download, verify, then install (never pipe into a shell):

```bash
#!/usr/bin/env bash
set -euo pipefail
shopt -s inherit_errexit

url=$1 sha256=$2 dest=$3
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT

curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
  --max-time 120 --retry 3 --output "$tmp/payload" -- "$url"
printf '%s  %s\n' "$sha256" "$tmp/payload" | sha256sum --check --status
install -m 0755 -- "$tmp/payload" "$dest"
```

On macOS replace `sha256sum --check` with `shasum -a 256 --check` (see the portability reference).

Single-instance lock with `flock`, and atomic file replacement:

```bash
exec 9>"${XDG_RUNTIME_DIR:-/tmp}/myjob-$UID.lock"
flock -n 9 || {
  echo "already running" >&2
  exit 75
}

write_atomic() {
  local dest=$1 tmp
  tmp=$(mktemp "${dest}.XXXXXX")
  cat >"$tmp"
  chmod 0644 "$tmp"
  mv -- "$tmp" "$dest"
}
```

Arrays, associative arrays and parameter expansion:

```bash
files=("report 1.txt" "report 2.txt")
printf '<%s>\n' "${files[@]}"          # one word per element

declare -A owner=([alice]=ops [bob]=dev)
for user in "${!owner[@]}"; do
  printf '%s -> %s\n' "$user" "${owner[$user]}"
done

path=/srv/app/release-1.4.2.tar.gz
base=${path##*/}                       # release-1.4.2.tar.gz
echo "${base%.tar.gz}"                 # release-1.4.2
echo "${TIMEOUT:-30}"                  # default when unset or empty
```

## 15. Common Mistakes

- **Unquoted expansions** (`rm $file`, `for f in $(ls)`): split on whitespace and expand globs. Quote them and iterate over globs or `find -print0` (SC2086, SC2045).
- **`local x=$(cmd)`**: `local` succeeds, so a failing `cmd` is hidden even under `set -e`. Write `local x; x=$(cmd)` (SC2155).
- **Trusting `set -e` inside `if f; then` or `f || ...`**: errexit is off for the whole of `f`, so `false; echo continues` runs on. Test inside the function with explicit `|| return`.
- **`((i++))` or `(( count ))` as a statement under `set -e`**: status 1 when the value is 0. Use `i=$((i + 1))` or `((i++)) || true`.
- **Pipelines without pipefail**: `cmd | tee log` hides a `cmd` failure. Use `set -o pipefail` and `${PIPESTATUS[@]}`; note that `yes | grep -q y` returns 141 under pipefail because `grep -q` exits early and the writer gets SIGPIPE.
- **`cd dir; rm -rf *`**: if `cd` fails the delete runs in the wrong place. Use `cd -- "$dir" || exit 1` (SC2164) and guard variables with `${dir:?}`.
- **Piping into `while read` and expecting variables to survive**: each pipeline stage is a subshell. Use `done < <(cmd)`, a here-string, or `shopt -s lastpipe` (non-interactive shells only).
- **`read` without `-r` or `IFS=`**: mangles backslashes and trims whitespace (SC2162). Use `IFS= read -r`.
- **`[ $a = b ]` with an empty or spaced variable**: syntax error or wrong test. Quote it, or use `[[ $a == b ]]`.
- **Quoting the right side of `=~` or `==` by habit**: quoted text matches literally, not as a regex or glob. Keep a regex in a variable (`re='^[0-9]+$'; [[ $x =~ $re ]]`) for readability.
- **`echo "$var"`** with values like `-n` or `\n`: output differs between shells. Use `printf '%s\n' "$var"`.
- **`trap "..." EXIT` with double quotes**: variables expand at definition time (SC2064). Single-quote the trap string or call a function.
- **Fixed temp names** (`/tmp/out.$$` or `/tmp/out`): predictable and racy. Use `mktemp`.
- **`sed -i` and `readlink -f` assumed portable**: BSD/macOS differ (section 2 of the portability reference).
- **`cmd | grep -q pattern` under pipefail** in a conditional: a SIGPIPE status can make a successful match look like a failure. Capture output first or use `grep` without `-q` into `/dev/null`.
- **Parsing `ls` or `ps` output**: breaks on odd names and column layout changes. Use globs, `find`, `stat`, `pgrep`.
- **A shell script that outgrew the language**: nested data, JSON handling, retries with state and 500 lines of logic belong in Python.

## 16. References

- [references/strict-mode-and-errors.md](references/strict-mode-and-errors.md): errexit rules and pitfalls, pipefail and PIPESTATUS, inherit_errexit, traps (EXIT, ERR, INT, TERM), cleanup, exit codes, logging, getopts plus long options, locking, atomic writes, retry.
- [references/quoting-expansion-arrays.md](references/quoting-expansion-arrays.md): quoting rules, parameter expansion, arrays and associative arrays, `[[ ]]`, arithmetic, `read` and `mapfile`, here-documents, process substitution, subshells versus groups, `find -print0`.
- [references/portability.md](references/portability.md): POSIX sh versus Bash, Bash version differences and macOS 3.2, GNU versus BSD tool differences (sed, date, readlink, stat, mktemp, sha256), a verified POSIX template.
- [references/testing-shellcheck-bats.md](references/testing-shellcheck-bats.md): ShellCheck options, `.shellcheckrc`, common SC codes, shfmt and EditorConfig, bats-core test patterns, stubbing, ShellSpec, CI command order.
- GNU Bash manual: https://www.gnu.org/software/bash/manual/bash.html and release notes in the NEWS file of the source tarball (https://ftp.gnu.org/gnu/bash/)
- POSIX shell command language: https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html
- ShellCheck: https://www.shellcheck.net/ and https://github.com/koalaman/shellcheck (wiki page per SC code)
- shfmt: https://github.com/mvdan/sh ; bats-core: https://bats-core.readthedocs.io/ ; ShellSpec: https://github.com/shellspec/shellspec
- Greg's Wiki (BashFAQ, BashPitfalls): https://mywiki.wooledge.org/BashGuide
