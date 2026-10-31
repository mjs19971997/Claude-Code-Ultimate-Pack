# Portability: POSIX sh, Bash Versions and GNU versus BSD Tools

How to decide the dialect of a script, which Bash features need which version, and which command-line differences break scripts between Linux (GNU userland), macOS and the BSDs. Bash behaviour was run on GNU Bash 5.2.21 and the POSIX template on dash 0.5.12 with ShellCheck 0.11.0 (2026-10). BSD and macOS behaviour was not run here; those rows come from the tools' documented behaviour, so confirm them on a real macOS or BSD host before relying on them.

## Contents

1. [Choosing a dialect](#1-choosing-a-dialect)
2. [GNU versus BSD commands](#2-gnu-versus-bsd-commands)
3. [Bash version features](#3-bash-version-features)
4. [A POSIX sh template](#4-a-posix-sh-template)
5. [Detecting and guarding](#5-detecting-and-guarding)
6. [Bashisms and their POSIX replacements](#6-bashisms-and-their-posix-replacements)

## 1. Choosing a dialect

| Situation | Choice |
|---|---|
| Linux servers and CI images you control, Bash installed | `#!/usr/bin/env bash`, Bash 4.4+ features allowed |
| Must run on macOS with the system bash | Bash 3.2 subset: no `declare -A`, `mapfile`, `${v,,}`, `declare -n`, `wait -n`, `${v@Q}`; or require `brew install bash` and say so |
| Installer, entry-point script in a container, Alpine, BusyBox, embedded | POSIX sh (`#!/bin/sh`), tested with dash and BusyBox ash |
| Logic needs arrays, dictionaries, JSON, or more than a few hundred lines | Python (see python-expert), with the shell script as a thin launcher |

- `#!/bin/sh` is a promise of POSIX behaviour. On Debian and Ubuntu it is dash, which has no `[[ ]]`, arrays, `local` guarantees (dash supports `local`; POSIX does not define it), `source`, `echo -e`, `read -p`, `${v//a/b}` or process substitution.
- When Bash runs as `sh` it enters POSIX mode, but it still accepts many bashisms, so a test that passes under `/bin/sh` on a Bash-based system proves little. Test with dash.
- ShellCheck selects its rules from the shebang. Use `shellcheck -s sh file` or a `# shellcheck shell=sh` directive for extensionless or sourced files.
- Different shebang forms: `#!/usr/bin/env bash` finds Bash in PATH (right for macOS and the BSDs, where Bash lives under `/usr/local/bin` or `/opt/homebrew/bin`); `#!/bin/bash` is fine for Linux-only code. Do not rely on passing options through `env` in a shebang (`#!/usr/bin/env bash -e` fails on Linux because the whole string is one argument); put `set -e` in the script.
- POSIX.1-2024 specifies `set -o pipefail`, and the ShellCheck changelog notes support for it in SC3040 after 0.11.0. Shells older than that standard may reject it: dash 0.5.12, tested here, does. Check each target shell before using it in `#!/bin/sh` scripts.

## 2. GNU versus BSD commands

| Task | GNU (Linux) | BSD / macOS | Portable approach |
|---|---|---|---|
| In-place sed | `sed -i 's/a/b/' f` | `sed -i '' 's/a/b/' f` (suffix argument required) | `sed -i.bak 's/a/b/' f && rm -f f.bak`, or write to a temp file and `mv` |
| Extended regex in sed | `sed -E` (also `-r`) | `sed -E` | Use `-E`, avoid `-r` |
| sed escapes | `\+`, `\?`, `\|`, `\n` in replacement, `\t` | Not supported in basic regex | Use `-E`, or `awk`/`perl` for complex edits |
| Resolve a path | `readlink -f p`, `realpath p` | Older macOS lacks `readlink -f`; `realpath` is available only in newer systems | `( cd -- "$(dirname -- "$p")" && printf '%s/%s\n' "$(pwd -P)" "${p##*/}" )` |
| Date arithmetic | `date -d '2 days ago' +%F` | `date -v-2d +%F`, parse with `date -j -f` | Compute in `awk` or Python; `date -u +%FT%TZ` and `date +%s` work on both; `%N` is GNU-only |
| File size, mtime | `stat -c '%s %Y' f` | `stat -f '%z %m' f` | `wc -c <f` for size; `find f -printf` is GNU-only; branch on `uname -s` when needed |
| Temp files | `mktemp`, `mktemp -d`, `mktemp /tmp/x.XXXXXX` | Same, `mktemp -t prefix` differs | Use an explicit template ending in `XXXXXX` (no suffix after the Xs) |
| SHA-256 | `sha256sum -c` | `shasum -a 256 -c` (also `sha256 -q` on some BSDs) | Detect with `command -v` (section 5) |
| Base64 | `base64 -w0`, `base64 -d` | No `-w`; decode flag spelled `-D` on older macOS (`-d` on newer) | `base64 \| tr -d '\n'` for single line |
| grep | `grep -P` (PCRE), `-o`, `-r` | `grep -P` absent in the system grep | Use `grep -E`; use `perl` or Python for PCRE |
| xargs | `-r` skips empty input, `-d`, `-P` | `-0` and `-P` exist; empty input already skipped | `find ... -print0 \| xargs -0`; accept `-r` on both |
| sort | `sort -V`, `-R`, `-h` | Some are missing on older systems | Pre-pad numbers, or sort in `awk`/Python |
| timeout | `timeout 30 cmd` | Not installed by default (`gtimeout` from coreutils) | Detect, or implement with a background job and `kill` |
| flock | `flock` (util-linux) | Not installed by default | `mkdir` lock directory, or detect `flock` |
| install | `install -D` | No `-D` | `mkdir -p` then `install` |
| CPU count | `nproc` | `sysctl -n hw.ncpu` | `getconf _NPROCESSORS_ONLN` works on both |
| echo | Flag handling differs | Differs | `printf` |
| awk | gawk extensions (`gensub`, `asort`, `strftime`) | BSD awk or mawk | Stay with POSIX awk functions |
| ls, ps, df | Flags and columns differ | Differ | Avoid parsing; use `find`, `stat`, `pgrep` |

- Prefer POSIX options only (check `man` pages for the standard marking) when the script is a public tool.
- Install GNU tools on macOS (`brew install coreutils gnu-sed grep findutils`) for CI parity and use them with their `g` prefix or via PATH; document it in the README rather than detecting silently.
- When differences cannot be avoided, branch once at the top and wrap in a function, never inline in many places:

```bash
case $(uname -s) in
  Darwin | *BSD) sed_inplace() { sed -i '' "$@"; } ;;
  *) sed_inplace() { sed -i "$@"; } ;;
esac
```

- BusyBox (Alpine) provides reduced versions of many tools: options such as `sed -i`, `find -printf`, `grep -P`, `xargs -r` and `date -d` vary. Test in an Alpine image if you target it.

## 3. Bash version features

| Feature | Bash version |
|---|---|
| Associative arrays (`declare -A`), `mapfile`/`readarray`, `${v,,}`/`${v^^}`, `\|&`, `&>>`, `globstar`, `coproc` | 4.0 |
| `{fd}` automatic file descriptor allocation | 4.1 |
| `printf '%(fmt)T'`, `[[ -v var ]]` | 4.2 |
| `declare -n` namerefs, `wait -n`, `[[ -v arr[key] ]]` | 4.3 |
| `inherit_errexit`, `${v@Q}` and other `@` transforms, `mapfile -d`, empty arrays safe under `set -u`, `local -` | 4.4 |
| `EPOCHSECONDS`, `EPOCHREALTIME`, `BASH_ARGV0` | 5.0 |
| `SRANDOM`, `wait -p` | 5.1 |
| `patsub_replacement` shopt: `&` in a `${v//p/r}` replacement stands for the matched text | 5.2 (on by default) |
| `${ cmd; }` and `${| cmd; }` forkless substitution, `source -p`, `compgen -V`, `read -E` | 5.3 (from the NEWS summary; not run here) |

- macOS ships Bash 3.2 as `/bin/bash` (check with `/bin/bash --version`), so scripts with `#!/bin/bash` there miss everything in the table.
- Bash 5.2 changed replacement semantics: `v=abc; echo "${v//b/[&]}"` prints `a[b]c` on 5.2 (default) and `a[&]c` after `shopt -u patsub_replacement`. Quote the replacement or use a variable with escaped `\&` if a literal ampersand is meant; this affects URLs and query strings.
- Check `BASH_VERSINFO` to enforce a minimum: `((BASH_VERSINFO[0] > 4 || (BASH_VERSINFO[0] == 4 && BASH_VERSINFO[1] >= 4)))`.
- Compatibility levels (`BASH_COMPAT=5.1`, `shopt -s compat51`) restore older behaviour for specific changes; they are a stop-gap for old scripts, not a design tool.
- Read the NEWS file of a release before upgrading production shells; behavioural fixes occur in patch levels.

## 4. A POSIX sh template

Run with dash and ShellCheck `-s sh`; every construct is POSIX except `mktemp`, which is near-universal but not in POSIX:

```sh
#!/bin/sh
set -eu

prog=${0##*/}
tmpdir=$(mktemp -d "${TMPDIR:-/tmp}/${prog}.XXXXXX")
trap 'rm -rf -- "$tmpdir"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

die() {
  printf '%s: %s\n' "$prog" "$*" >&2
  exit 1
}

need() {
  command -v "$1" >/dev/null 2>&1 || die "missing required command: $1"
}

sha256_check() { # file expected_hex
  if command -v sha256sum >/dev/null 2>&1; then
    actual=$(sha256sum -- "$1" | cut -d ' ' -f 1)
  elif command -v shasum >/dev/null 2>&1; then
    actual=$(shasum -a 256 -- "$1" | cut -d ' ' -f 1)
  else
    die "no sha256 tool found"
  fi
  [ "$actual" = "$2" ]
}

need cut
printf 'data\n' >"$tmpdir/f"
exp=$(printf 'data\n' | sha256sum | cut -d ' ' -f 1)
sha256_check "$tmpdir/f" "$exp" && printf 'checksum ok\n'

set -- "a b" "c"                       # positional parameters are the only array
for arg in "$@"; do printf '[%s]\n' "$arg"; done

ver=v1.2
case $ver in v[0-9]*) printf 'looks like a version\n' ;; esac

printf 'x\ny\n' | while IFS= read -r line; do printf 'line=%s\n' "$line"; done
```

- Use `case` for pattern tests, `$(( ))` for arithmetic, `${v#p}`/`${v%p}` for trimming, `[ ]` with quoted operands and `&&`/`||` between tests.
- Keep lists in positional parameters (`set -- "$@" item`) or in newline-separated text when names cannot contain newlines.
- Functions have no `local` in POSIX. dash, BusyBox ash and Bash support it, and ShellCheck warns with SC3043 under `-s sh`; either accept that knowingly, or prefix function-private names (`_fn_var`) and unset them.
- Use `command -v` (not `which`) to test for a tool, `printf` (not `echo -e`), `. file` (not `source`), `$(...)` (not backticks), and `exec` for the final command.

## 5. Detecting and guarding

```bash
# pick a checksum tool once
if command -v sha256sum >/dev/null 2>&1; then
  sha256() { sha256sum -- "$1" | cut -d ' ' -f 1; }
elif command -v shasum >/dev/null 2>&1; then
  sha256() { shasum -a 256 -- "$1" | cut -d ' ' -f 1; }
else
  echo "no sha256 tool" >&2; exit 127
fi

# fail early on a missing tool or Bash that is too old
for t in curl jq tar; do
  command -v "$t" >/dev/null 2>&1 || { echo "missing: $t" >&2; exit 127; }
done
```

- Detect capabilities rather than operating systems where possible (`command -v flock`, a trial `sed --version`), and branch on `uname -s` only for known OS differences.
- Run the test suite on every target: Linux with the oldest supported Bash, macOS, and an Alpine or dash container for POSIX scripts. A CI matrix is the only reliable portability check (pipeline layout: cicd-expert).
- Set `LC_ALL=C` for stable `sort`, `tr` and regex character classes, and `LC_ALL=en_US.UTF-8` or `C.UTF-8` only where multibyte handling is needed and the locale is installed.

## 6. Bashisms and their POSIX replacements

| Bash | POSIX sh |
|---|---|
| `[[ $a == b* ]]` | `case $a in b*) ... ;; esac` |
| `[[ $a =~ re ]]` | `printf '%s\n' "$a" \| grep -Eq 're'` |
| `arr=(a b)`, `"${arr[@]}"` | `set -- a b`, `"$@"` |
| `${v//a/b}`, `${v,,}` | `printf '%s\n' "$v" \| sed 's/a/b/g'`, `tr` |
| `source file` | `. file` |
| `echo -e "a\tb"` | `printf 'a\tb\n'` |
| `read -p prompt var` | `printf 'prompt' >&2; read -r var` |
| `<<<"$v"` | `printf '%s\n' "$v" \| cmd` |
| `<(cmd)` | A temporary file or a named pipe |
| `function f { :; }` | `f() { :; }` |
| `(( i++ ))` | `i=$((i + 1))` |
| `$RANDOM`, `$EPOCHSECONDS`, `$BASH_SOURCE` | `awk`, `date +%s`; script path from `$0` |
| `&>file`, `\|&` | `>file 2>&1`, `2>&1 \|` |

- ShellCheck codes for these under `-s sh`: SC3010 (`[[ ]]`), SC3030 (arrays), SC3043 (`local`), SC3045 (`read -p`), SC3046 (`source`), SC3037 (`echo` flags), SC3060 (`${v//}`), SC2113 (`function` keyword), all reproduced with 0.11.0.
- The Debian `checkbashisms` script (from the devscripts package) is another detector if installed; ShellCheck covers most of the same ground.
