# Strict Mode, Errors, Traps and Script Structure

How `set -e`, `set -u`, `pipefail` and `inherit_errexit` really behave, how to clean up with traps, exit-code conventions, logging, argument parsing, locking, atomic writes and retries. All snippets were run with GNU Bash 5.2.21 and checked with ShellCheck 0.11.0 and shfmt 3.14.1 (2026-10); the dash notes use dash 0.5.12.

## Contents

1. [What strict mode does](#1-what-strict-mode-does)
2. [errexit pitfalls](#2-errexit-pitfalls)
3. [pipefail and PIPESTATUS](#3-pipefail-and-pipestatus)
4. [Traps and cleanup](#4-traps-and-cleanup)
5. [Exit codes and logging](#5-exit-codes-and-logging)
6. [Argument parsing](#6-argument-parsing)
7. [Locking, atomic writes, retries](#7-locking-atomic-writes-retries)

## 1. What strict mode does

```bash
set -Eeuo pipefail
shopt -s inherit_errexit nullglob
```

| Setting | Effect | Caveat |
|---|---|---|
| `-e` | Exit when a simple command fails | Disabled in many contexts, see section 2 |
| `-u` | Unset variable in an expansion is an error | Use `${v-}` or `${v:-}` for optional variables; `"$@"` and empty arrays are safe from Bash 4.4 |
| `-o pipefail` | Pipeline status is the last non-zero status of any stage | A writer killed by SIGPIPE reports 141 |
| `-E` | ERR trap is inherited by functions, substitutions and subshells | Only matters if you set an ERR trap |
| `inherit_errexit` | Command substitutions inherit `-e` (Bash 4.4+) | Without it, `v=$(false; echo hi)` still yields `hi` and status 0 |
| `nullglob` | An unmatched glob expands to nothing | Without it, `for f in *.log` runs once with the literal pattern |

POSIX sh has `-e`, `-u` and, since POSIX.1-2024, `-o pipefail`; the dash 0.5.12 tested here rejects `set -o pipefail`, so do not use it in `#!/bin/sh` scripts that must run on older shells.

Strict mode is a safety net. It cannot decide which failures are acceptable, so check important commands explicitly.

## 2. errexit pitfalls

Each case below was run with `bash -c` as a separate process.

```bash
# 1. Exit status of `local` hides the substitution
f() { local x=$(false); echo "still running"; }   # prints, status 0 (SC2155)
f() { local x; x=$(false); echo "not reached"; }  # exits under set -e

# 2. ((expr)) is a command; a zero result is status 1
set -e; i=0; ((i++)); echo survived   # exits: ((i++)) evaluated to 0
i=$((i + 1))                          # safe
((i++)) || true                       # safe, if you really want the post-increment

# 3. Command substitution without inherit_errexit
set -e; v=$(false; echo hi); echo "v=$v"                      # prints v=hi
set -e; shopt -s inherit_errexit; v=$(false; echo hi)         # exits with 1

# 4. Context where errexit is ignored: if, while, until, &&, ||, !
h() { false; echo "h continued"; }
h || true            # prints "h continued": -e is off for the entire function body
if h; then :; fi     # same

# 5. A failed command that is not the last in an AND-OR list
set -e; false && true; echo "after"   # prints "after": only the last command of && counts

# 6. Process substitution failures are not seen
set -e; cat <(false); echo "ignored"  # prints "ignored"
```

Rules that follow:

- Inside a function that may be called under `if` or `||`, write `cmd || return` for steps that must not be skipped.
- Use `if ! out=$(cmd); then die ...; fi` or `out=$(cmd) || die 1 "cmd failed"` when the command's failure needs a message. An assignment alone takes the status of the substitution, so `out=$(cmd)` exits under `-e`.
- Capture a status without exiting: `cmd && rc=0 || rc=$?` (do not use this form when `cmd` is a function that relies on errexit inside).
- `exit` inside `$( )` or `( )` leaves only that subshell. Propagate with `|| exit`.
- `set -e` interacts oddly with `trap ... ERR`: the ERR trap fires in the same cases where `-e` would exit, so it also stays quiet in conditionals. It reports a failing line, which is useful for debugging, but it is not a replacement for error handling.
- `[[ cond ]] && action` as the last statement of a function returns 1 when `cond` is false, which can trigger errexit in the caller. Use `if`, or end the function with `return 0`.

## 3. pipefail and PIPESTATUS

```bash
set -o pipefail
false | true; echo $?                  # 1 with pipefail, 0 without
false | true | false; echo "${PIPESTATUS[*]}"   # 1 0 1
yes | grep -q y; echo $?               # 141: grep -q exits early, yes dies of SIGPIPE
```

- `PIPESTATUS` is overwritten by the next command: copy it at once (`st=("${PIPESTATUS[@]}")`).
- Under `pipefail`, `producer | grep -q pattern` can fail although the pattern was found, because the producer was killed by SIGPIPE. Options: capture the output first (`out=$(producer) && [[ $out == *pattern* ]]`), use `grep pattern >/dev/null`, or accept 141 explicitly (`|| [[ ${PIPESTATUS[0]} -eq 141 ]]`).
- `grep` returns 1 for no match and 2 for an error. Under `-e` and `pipefail`, `grep pattern file | wc -l` aborts when there is no match; use `{ grep pattern file || true; } | wc -l`, or `grep -c`.
- Newer ShellCheck sources list SC2337 (`grep -q` in pipelines under pipefail) among unreleased additions; version 0.11.0 does not include it.

## 4. Traps and cleanup

```bash
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
trap 'log "error: line $LINENO: $BASH_COMMAND (rc=$?)"' ERR   # needs set -E to reach functions
```

- `EXIT` runs on normal end, on `exit N` (the status is visible as `$?` at the start of the handler), on a failing `set -e` and, with the INT and TERM handlers above, on those signals. It does not run on SIGKILL.
- Capture `$?` first: any command in the handler overwrites it. Call `exit "$rc"` at the end, otherwise the exit status becomes that of the last command in the handler.
- Single-quote trap strings. `trap "rm -f $tmp" EXIT` expands `$tmp` at definition time (SC2064); if `tmp` changes later, the wrong file is removed.
- `trap ... RETURN` is global once set (it is not scoped to the function unless the function is traced); avoid it in libraries and clean up explicitly.
- A trap on a signal runs only after the current foreground command finishes. For long-running children, start them with `&` and `wait "$pid"`; `wait` returns early when a trapped signal arrives, so the handler can forward the signal (`kill "$pid"`).
- Several scripts sharing one trap name overwrite each other. Chain explicitly: `old=$(trap -p EXIT)` and eval it only if you trust it, or keep a single cleanup function that calls a list of registered cleanup commands.
- Subshells reset non-ignored traps; a trap set in the parent does not run when a `( ... )` subshell exits.
- Create all temp data under one directory: `WORKDIR=$(mktemp -d "${TMPDIR:-/tmp}/${PROG}.XXXXXX")`. `mktemp` creates the item with mode 0600 or 0700.

## 5. Exit codes and logging

| Code | Use |
|---|---|
| 0 | Success |
| 1 | General failure |
| 2 | Usage error (bad option or arguments); Bash builtins also use 2 for misuse |
| 64-78 | Optional sysexits.h style codes: 64 usage, 65 data error, 66 no input, 69 unavailable, 73 cannot create, 75 temporary failure (try again), 77 permission, 78 configuration |
| 126 | Command found but not executable (set by the shell) |
| 127 | Command not found (set by the shell) |
| 128+N | Terminated by signal N (130 for INT, 143 for TERM, 141 for PIPE) |

```bash
log()   { printf '%s %s: %s\n' "$(date -u +%FT%TZ)" "$PROG" "$*" >&2; }
debug() { ((VERBOSE)) && log "debug: $*"; return 0; }
die()   { local rc=$1; shift; log "error: $*"; exit "$rc"; }
```

- Diagnostics always go to stderr; stdout carries data only, so pipelines and `$( )` capture clean output.
- `printf '%(%FT%T)T' -1` formats the current time without a subprocess (Bash 4.2+). `date -u +%FT%TZ` works on GNU and BSD.
- Stop `debug()` from failing under `-e`: `((VERBOSE)) && ...` returns 1 when `VERBOSE=0`, hence the `return 0`.
- Set `PS4='+ ${BASH_SOURCE##*/}:${LINENO}: '` before `set -x` for readable traces; remember traces print secrets.
- Wrap external failures with context: `curl ... || die 69 "download failed: $url"`.

## 6. Argument parsing

`getopts` handles short options and is portable to POSIX sh. Translate long options to short ones first (this script was run, including `--`, `--help`, paths with spaces and error cases):

```bash
parse_args() {
  local opt
  local -a args=()
  while (($#)); do
    case $1 in
      --help) args+=(-h) ;;
      --dry-run) args+=(-n) ;;
      --verbose) args+=(-v) ;;
      --) args+=("$@"); break ;;
      *) args+=("$1") ;;
    esac
    shift
  done
  set -- "${args[@]}"
  OPTIND=1
  while getopts ':nvh' opt; do
    case $opt in
      n) DRY_RUN=1 ;;
      v) VERBOSE=1 ;;
      h) usage; exit 0 ;;
      \?) usage >&2; die 2 "unknown option: -$OPTARG" ;;
      :) die 2 "option -$OPTARG needs an argument" ;;
    esac
  done
  shift $((OPTIND - 1))
  (($# == 2)) || { usage >&2; die 2 "expected SRC_DIR and DEST_DIR"; }
  SRC=$1
  DEST=$2
}
```

- A leading `:` in the option string selects silent mode: `\?` means unknown option and `:` means missing argument, with the character in `OPTARG`. An option that takes a value is written `o:`.
- `getopts` stops at the first non-option word. Operands before options (`script file -v`) are not parsed; document that or loop manually.
- Long options with values (`--output=FILE` or `--output FILE`) need a manual loop:

```bash
while (($#)); do
  case $1 in
    --output=*) OUT=${1#*=} ;;
    --output) (($# > 1)) || die 2 "--output needs a value"; OUT=$2; shift ;;
    --) shift; break ;;
    -*) die 2 "unknown option: $1" ;;
    *) break ;;
  esac
  shift
done
```

- Avoid the external `getopt` in portable code: BSD `getopt` lacks long options and GNU `getopt` from util-linux has an incompatible "enhanced" mode.
- Validate after parsing: required options present, numbers match `^[0-9]+$`, paths exist, mutually exclusive flags not both set. Exit 2 on usage errors.
- Print usage from a here-document (`cat <<USAGE`); `--help` prints to stdout and exits 0, errors print usage to stderr.

## 7. Locking, atomic writes, retries

```bash
# single instance (util-linux flock; not installed by default on macOS)
lock=${XDG_RUNTIME_DIR:-/tmp}/myjob-$UID.lock
exec 9>"$lock"
flock -n 9 || { echo "already running" >&2; exit 75; }
```

- The lock belongs to the open file description and is released when the process (and any child that inherited fd 9) exits. A child started with `9>&-` does not hold it.
- `flock -w 30 9` waits up to 30 seconds. `flock -n` fails immediately with status 1.
- Portable fallback: `mkdir "$lockdir" 2>/dev/null || die 75 "locked"` is atomic, but a crash leaves the directory behind; add a PID file check and a stale-lock policy, or prefer `flock` where it exists.
- On a shared network filesystem `flock` semantics vary; check your filesystem's documentation.

```bash
write_atomic() {
  local dest=$1 tmp
  tmp=$(mktemp "${dest}.XXXXXX")
  cat >"$tmp"
  chmod 0644 "$tmp"
  mv -- "$tmp" "$dest"
}
```

- Create the temp file in the destination directory so `mv` is a same-filesystem rename, which is atomic. `mktemp` makes it 0600, so set the final mode explicitly.
- If the script can die between `mktemp` and `mv`, remove stale `*.XXXXXX` files in a cleanup trap or a periodic job.

```bash
retry() {
  local -i max=$1 delay=1 n
  shift
  for ((n = 1; n <= max; n++)); do
    "$@" && return 0
    ((n == max)) && break
    echo "attempt $n failed, retrying in ${delay}s" >&2
    sleep "$delay"
    delay=$((delay * 2))
  done
  return 1
}
retry 3 curl --fail --silent --show-error --output "$out" -- "$url"
```

- Retry only operations that are safe to repeat, cap the attempts and the delay, and add jitter when many clients retry together.
- `"$@" && return 0` is a conditional context: errexit is off inside the retried function. That is intended here, but it means a retried shell function should return its own status explicitly.
- Idempotent helpers make reruns safe: `mkdir -p`, `ln -sfn target link`, `install -D`, `grep -qxF "$line" file || printf '%s\n' "$line" >>file`.
