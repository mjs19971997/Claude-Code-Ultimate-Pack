# ShellCheck, shfmt, bats-core and ShellSpec

Linting, formatting and testing shell code. Versions: ShellCheck 0.11.0 (released 2025-08-03; pip package shellcheck-py 0.11.0.1 installs it), shfmt 3.14.1 (changelog entry 2026-09-06), bats-core 1.14.0 (changelog entry 2026-07-21; npm package bats 1.13.0 was run for the examples). The ShellCheck, shfmt and bats snippets below were executed locally (2026-10). ShellSpec was not run.

## Contents

1. [ShellCheck](#1-shellcheck)
2. [Common ShellCheck codes](#2-common-shellcheck-codes)
3. [shfmt and EditorConfig](#3-shfmt-and-editorconfig)
4. [bats-core](#4-bats-core)
5. [Stubbing and isolation](#5-stubbing-and-isolation)
6. [ShellSpec](#6-shellspec)
7. [CI order and pre-commit](#7-ci-order-and-pre-commit)

## 1. ShellCheck

```bash
shellcheck script.sh                      # default severity: style and above
shellcheck -S warning -x bin/* lib/*.bash # warnings and errors; follow sourced files
shellcheck -s sh install.sh               # force the POSIX sh dialect
shellcheck -f gcc script.sh               # one line per finding; also json, json1, checkstyle, diff, quiet, tty
shellcheck -f diff script.sh | git apply  # apply the auto-fixable suggestions
shellcheck --list-optional                # names of optional checks
shellcheck -o all script.sh               # enable all optional checks (noisy)
```

- Install: your package manager, a release binary from github.com/koalaman/shellcheck, or `pip install shellcheck-py` in a virtual environment (the wheel bundles the binary). Pin the version in CI so new rules do not break builds unannounced.
- Dialect comes from the shebang, the `shell=` directive or `-s`. Without a shebang ShellCheck reports SC2148; add a shebang or `# shellcheck shell=bash` at the top.
- Directives go on the line above the command, or at the top of the file for the whole file:

```bash
# shellcheck disable=SC2034  # variable is read by the sourcing script
unused_but_exported=1

# shellcheck source=lib/log.bash
source "$LIB_DIR/log.bash"

# shellcheck source=/dev/null
source "$HOME/.config/tool/env"
```

- `.shellcheckrc` in the project root (or `~/.config/shellcheck/shellcheckrc`) holds options. These keys were verified with 0.11.0:

```text
shell=bash
external-sources=true
source-path=SCRIPTDIR
enable=require-double-brackets
disable=SC2034
```

- `source-path=SCRIPTDIR` lets `source ./lib.sh` resolve relative to each script. `external-sources=true` is the rc equivalent of `-x`.
- Optional checks in 0.11.0: `add-default-case`, `avoid-negated-conditions`, `avoid-nullary-conditions`, `check-extra-masked-returns`, `check-set-e-suppressed`, `check-unassigned-uppercase`, `deprecate-which`, `quote-safe-variables`, `require-double-brackets`, `require-variable-braces`, `useless-use-of-cat`. `check-set-e-suppressed` and `check-extra-masked-returns` are the useful ones for strict-mode scripts.
- Each finding links to `https://www.shellcheck.net/wiki/SCxxxx` with bad and good examples. Fix the cause; disable only with a written reason.
- The project's unreleased changelog lists SC2337 (`grep -q` in pipelines under pipefail) and SC2338; they are not in 0.11.0.

## 2. Common ShellCheck codes

Reproduced with 0.11.0 unless marked.

| Code | Meaning | Fix |
|---|---|---|
| SC2086 | Unquoted variable: splitting and globbing | Quote `"$var"` |
| SC2046 | Unquoted `$(...)` | Quote it, or use `mapfile` / `read` |
| SC2045 | Iterating over `ls` output | Use a glob |
| SC2155 | `local x=$(cmd)` masks the status | Declare, then assign |
| SC2164 | `cd` without `\|\| exit` | `cd -- "$d" \|\| exit 1` |
| SC2181 | Checking `$?` indirectly | `if cmd; then` |
| SC2162 | `read` without `-r` | `IFS= read -r` |
| SC2006 | Backticks | `$(...)` |
| SC2207 | `arr=($(cmd))` | `mapfile -t arr < <(cmd)` |
| SC2064 | Trap string expands now | Single quotes |
| SC2010 / SC2009 | `ls \| grep`, `ps \| grep` | Glob or `find`; `pgrep` |
| SC2128 | Array used without index | `"${arr[@]}"` |
| SC2166 / SC2333 | `-a` / `-o` inside `[ ]` | `[ a ] && [ b ]`, `[[ ]]` |
| SC2115 | `rm -rf "$dir/"*` with possibly empty `dir` | `"${dir:?}/"*` |
| SC2059 | Variable in printf format | `printf '%s\n' "$x"` |
| SC2034 | Variable appears unused | Remove, export or disable with a reason |
| SC2154 | Variable referenced but not assigned | Assign, or source the file with a `source=` directive |
| SC2194 | `case` on a constant word | Probably a missing `$` |
| SC2012 | `ls` parsed | `find` or glob |
| SC1091 | Sourced file not followed | `-x`, `source=` or `source-path` |
| SC2329 | Function never invoked (new in 0.11.0) | Remove it, or disable when invoked indirectly (traps, dispatch) |
| SC2331 | Unary `-a` in a test (new in 0.11.0) | `-e` |
| SC3010, SC3030, SC3043, SC3045, SC3046, SC3037, SC3060 | Bashisms under `-s sh` | See the portability reference |

- A missing code in this list is not a clean bill of health: ShellCheck is a heuristic linter and cannot see data-dependent injection. Review `eval`, `bash -c` and `ssh` string building by hand.
- Do not blanket-disable `SC2086` or `SC2155`; fix the quoting.

## 3. shfmt and EditorConfig

```bash
shfmt -i 2 -ci -bn -d .          # show a diff, exit non-zero if formatting differs
shfmt -i 2 -ci -bn -w bin lib    # rewrite files
shfmt -ln bash -i 2 -d script.sh # force the dialect: bash, posix, mksh, bats, zsh
shfmt -f .                       # list the shell files shfmt finds
```

| Flag | Meaning |
|---|---|
| `-i N` | Indent with N spaces (`0` means tabs, the default) |
| `-ci` | Indent `case` branches |
| `-bn` | Binary operators like `&&` and `\|` may start a line |
| `-sr` | Space after redirect operators |
| `-kp` | Keep column alignment padding |
| `-fn` | Function opening brace on its own line |
| `-s` | Simplify code |
| `-ln` / `-p` | Language dialect / POSIX shorthand |
| `-l` / `-d` / `-w` | List differing files / diff / write |
| `--detect` | Find shell files by executable bit or shebang while walking (added in 3.14.0) |

- shfmt also reads EditorConfig files (the `--help` text points to `man shfmt` for the keys). A project can then share one definition with editors:

```text
# .editorconfig
[*.{sh,bash,bats}]
indent_style = space
indent_size = 2
```

- Flags on the command line override EditorConfig. Check `man shfmt` for the full list of EditorConfig keys and the `shell_variant` option before relying on a key.
- shfmt parses `.bats` files with `-ln bats`. Run the formatter in CI with `-d`, locally with `-w`.
- Formatting changes whitespace and line breaks, not behaviour; commit a formatting-only change separately.

## 4. bats-core

```bash
#!/usr/bin/env bats
bats_require_minimum_version 1.5.0

setup() {
  SCRIPT=${BATS_TEST_DIRNAME}/../bin/backup-logs
  SRC=$(mktemp -d "${BATS_TEST_TMPDIR}/src.XXXXXX")
  touch "$SRC/a.log" "$SRC/b.log"
}

@test "prints usage and exits 2 without arguments" {
  run "$SCRIPT"
  [ "$status" -eq 2 ]
  [[ $output == *"Usage:"* ]]
}

@test "copies log files into a dated directory" {
  run "$SCRIPT" "$SRC" "$BATS_TEST_TMPDIR/out"
  [ "$status" -eq 0 ]
  run find "$BATS_TEST_TMPDIR/out" -name '*.log'
  [ "${#lines[@]}" -eq 2 ]
}

@test "rejects a missing source directory" {
  run -66 "$SCRIPT" "$BATS_TEST_TMPDIR/nope" "$BATS_TEST_TMPDIR/out"
  [[ $output == *"not a directory"* ]]
}
```

- Run: `bats test/`, `bats -r test/` (recurse), `bats --filter 'usage' test/`, `bats -T` (timing), `bats -x` (trace), `bats --print-output-on-failure`, `bats -F junit -o reports/` (JUnit XML; the output directory must exist), `bats --tap` for TAP output. `-j N` runs tests in parallel but requires GNU parallel (or shenwei356/rush); without it, 1.13.0 ran 0 of 3 tests in this check with a warning, so install it first or omit `-j`.
- `run cmd args` captures stdout and stderr together in `$output`, the status in `$status` and the lines in `${lines[@]}`. `run -N` asserts status N and `run !` asserts non-zero (both need `bats_require_minimum_version 1.5.0`, otherwise a BW02 warning). `run --separate-stderr` fills `$stderr`.
- Each test runs in its own subshell with `set -e`-like behaviour: a failing command in the test body fails the test, which is why `[ ... ]` assertions work. Use `[[ ]]` for patterns and regexes; on very old Bash versions a failing `[[ ]]` in the middle of a test may not fail it (see the bats documentation on `[[`), so end the test with the assertion or append `|| false`.
- `setup`/`teardown` run per test; `setup_file`/`teardown_file` once per file; `setup_suite` in `setup_suite.bash` once per run. `$BATS_TEST_TMPDIR`, `$BATS_FILE_TMPDIR`, `$BATS_SUITE_TMPDIR` are cleaned automatically; `$BATS_TEST_DIRNAME` is the test file's directory.
- `skip "reason"` marks a test as skipped; `load helper` sources `helper.bash` next to the test file.
- Test names must be unique per file; generate test cases in a loop with `bats_test_function` (see the docs) or table-driven helper functions.
- bats-support, bats-assert and bats-file are separate repositories with `assert_success`, `assert_output`, `assert_equal`, `assert_file_exist`. Install them as git submodules or packages and load them with `bats_load_library`; check each project's README for the current layout.
- Test the script as a black box with `run "$SCRIPT" ...` (real exit codes and stderr), and sources library functions with `source` for unit tests.

## 5. Stubbing and isolation

```bash
# test/helper.bash
make_stub() { # name exit_code output
  printf '#!/bin/sh\necho "%s"\nexit %s\n' "$3" "$2" >"$BATS_TEST_TMPDIR/bin/$1"
  chmod +x "$BATS_TEST_TMPDIR/bin/$1"
}
```

```bash
# test/stub.bats
bats_require_minimum_version 1.5.0
load helper

setup() {
  mkdir -p "$BATS_TEST_TMPDIR/bin"
  PATH="$BATS_TEST_TMPDIR/bin:$PATH"
  make_stub curl 22 "fake failure"
}

@test "stubbed curl is found first" {
  run --separate-stderr curl https://example.invalid
  [ "$status" -eq 22 ]
  [ "$output" = "fake failure" ]
  [ -z "$stderr" ]
}
```

- A stub earlier in `PATH` replaces `curl`, `git`, `date` or `sudo` without touching the network. This was run with bats 1.13.0.
- Tests must not touch `$HOME`, the real network or shared `/tmp` names. Set `HOME="$BATS_TEST_TMPDIR/home"` and `TMPDIR="$BATS_TEST_TMPDIR"` in `setup`.
- To unit-test functions, guard `main` (`if [[ ${BASH_SOURCE[0]} == "$0" ]]; then main "$@"; fi`) so `source script.sh` in the test defines functions without running them.
- Function-level stubs work for sourced code: redefine `date() { echo 2026-01-01; }` after sourcing, because functions take precedence over commands.
- Test for leaks of temp files by pointing `TMPDIR` into `$BATS_TEST_TMPDIR` and asserting that the directory is empty afterwards.

## 6. ShellSpec

- ShellSpec is a BDD-style framework (`Describe`, `It`, `When call`, `The output should eq ...`) that targets many shells (POSIX sh, dash, bash, zsh, ksh), supports mocks and parameterized tests, and has coverage via kcov integration.
- Its CHANGELOG on GitHub lists 0.28.1 (2021-01-11) as the newest entry at the time of this check. Confirm recent commit and release activity on the project page before adopting it for new work.
- bats-core is the simpler default for testing scripts as black boxes; ShellSpec is worth a look when the same tests must run across several shells.
- Install from the project's documented installer and verify the script's checksum or signature first; do not pipe a downloaded installer straight into a shell.

## 7. CI order and pre-commit

```bash
bash -n script.sh                 # syntax check per file
shellcheck -x -S warning $(git ls-files '*.sh' '*.bash')
shfmt -d -i 2 -ci .
bats -r test/
```

- Run syntax, lint, format and tests in that order: cheap checks fail first. `git ls-files -z | xargs -0` is safer than word-splitting `$(...)` when file names may contain spaces.
- Pin ShellCheck, shfmt and bats versions (a container image, a tools cache, or lock files for pip/npm installs) so a tool upgrade is a reviewed change.
- Run the tests on every Bash version and OS the scripts claim to support; see the portability reference. Pipeline syntax and caching belong to cicd-expert; hook mechanics belong to git-expert.
- A pre-commit hook that runs `shellcheck` and `shfmt -d` on staged files keeps style review out of pull requests; keep it fast and make CI the authority.
- Treat ShellCheck `error` and `warning` findings as failures; allow `info` and `style` through `-S warning` and fix them gradually.
