# Quoting, Expansion, Arrays and Reading Data

Reference for quoting rules, parameter expansion, arrays, associative arrays, conditionals, arithmetic, reading input, here-documents, process substitution and subshells in Bash 4.4 to 5.3. The snippets were run on GNU Bash 5.2.21 (2026-10); features that need a newer Bash are marked.

## Contents

1. [Quoting rules](#1-quoting-rules)
2. [Parameter expansion](#2-parameter-expansion)
3. [Indexed arrays](#3-indexed-arrays)
4. [Associative arrays and namerefs](#4-associative-arrays-and-namerefs)
5. [Conditionals and arithmetic](#5-conditionals-and-arithmetic)
6. [Reading input safely](#6-reading-input-safely)
7. [Here-documents and process substitution](#7-here-documents-and-process-substitution)
8. [Subshells and command groups](#8-subshells-and-command-groups)
9. [Avoiding subprocesses](#9-avoiding-subprocesses)

## 1. Quoting rules

| Form | Behaviour |
|---|---|
| `"$v"` `"$(cmd)"` | Expands, no word splitting, no globbing. The default for every expansion |
| `'text'` | Literal text; no expansion at all; cannot contain a single quote |
| `$'a\tb\n'` | ANSI-C quoting: backslash escapes are interpreted |
| `\x` | Escapes one character |
| `"$@"` | One word per positional parameter, each preserved |
| `"$*"` | One word: all parameters joined by the first character of `IFS` |
| `"${arr[@]}"` | One word per element |
| `"${arr[*]}"` | One word, elements joined by the first character of `IFS` |
| `${v@Q}` | Value quoted so it can be reused as shell input (4.4+); `printf '%q'` does the same for arguments |

```bash
word="a  b"; set -- $word; echo $#    # 2 (unquoted: split, glob)
set -- "$word"; echo $#               # 1
s="it's \$x"; echo "${s@Q}"           # 'it'\''s $x'
printf '%q\n' "$s"                    # it\'s\ \$x
```

- Unquoted expansion undergoes word splitting on `IFS` and pathname expansion. This is the cause of most shell bugs (SC2086).
- Quote the right side of `==`, `!=` and `=~` when you want a literal match; leave a glob unquoted to match a pattern: `[[ abc == $p ]]` (glob), `[[ abc == "$p" ]]` (literal).
- Assignments `x=$y` and the word after `case` are not split, but quoting them costs nothing and avoids rereading the rule.
- A command stored in a variable (`cmd="ls -l"; $cmd`) splits on spaces and cannot hold quoted arguments. Use an array: `cmd=(ls -l -- "$dir"); "${cmd[@]}"`.
- Tilde does not expand inside quotes: use `"$HOME/x"`, not `"~/x"`.
- Put `--` before operands that may start with `-`, and use `./*` rather than `*` in globs: `rm -- ./*.tmp`.

## 2. Parameter expansion

```bash
path=/srv/app/release-1.4.2.tar.gz
echo "${path##*/}"        # release-1.4.2.tar.gz   (basename)
echo "${path%/*}"         # /srv/app               (dirname)
echo "${path%%.*}"        # /srv/app/release-1     (longest suffix removed)
echo "${path/release/rel}"   # replace first
echo "${path//./_}"       # replace all
v=; echo "[${v:-default}] [${v-unset only}] [${v:+alt}]"   # [default] [] []
echo "${#path}"           # length
w=hello; echo "${w^^} ${w^} ${w,,}"   # HELLO Hello hello (Bash 4.0+)
echo "${w:1:3}"           # ell  (offset:length)
echo "${w: -2}"           # lo   (note the space before the minus)
```

| Form | Meaning |
|---|---|
| `${v:-d}` / `${v-d}` | Use `d` if unset or empty / if unset |
| `${v:=d}` | Assign `d` if unset or empty, then use it |
| `${v:?msg}` | Exit with `msg` if unset or empty; use it to guard `rm -rf "${dir:?}/"` |
| `${v:+alt}` | `alt` if set and non-empty |
| `${v#p}` `${v##p}` | Remove shortest / longest prefix matching pattern `p` |
| `${v%p}` `${v%%p}` | Remove shortest / longest suffix |
| `${v/p/r}` `${v//p/r}` | Replace first / all matches; `${v/#p/r}` anchors at start, `${v/%p/r}` at end |
| `${!name}` | Indirect expansion of the variable named by `name` |
| `${!prefix@}` | Names of variables starting with `prefix` |
| `${v@U}` `${v@L}` `${v@Q}` | Transformations (check the manual for the full list per version) |

- Under `set -u`, use `${v-}` for variables that may be unset. `"$@"` is safe with no arguments in Bash 4.4+ (older Bash errors out with `set -u`).
- Patterns in `#`, `%` and `/` are globs, not regular expressions. With `shopt -s extglob`: `@(a|b)`, `*(x)`, `+(x)`, `?(x)`, `!(x)`.
- `${v:?}` and `${v:-}` take a word that is itself expanded; quote it if it contains spaces.
- Use `: "${TIMEOUT:=30}"` for defaults that later code reads as `$TIMEOUT`.
- `${ cmd; }` and `${| cmd; }` (Bash 5.3 only) run a command in the current shell without forking and substitute its output or `REPLY`. Do not use them if any target is Bash 5.2 or older.

## 3. Indexed arrays

```bash
arr=(one "two words" three four)
echo "${#arr[@]}"            # 4 elements
echo "${arr[@]:1:2}"         # two words three
echo "${!arr[@]}"            # 0 1 2 3 (indices)
arr+=(five)                  # append
unset 'arr[1]'               # leaves a gap; indices are not renumbered
printf '<%s>' "${arr[@]}"; echo
(IFS=:; echo "${arr[*]}")    # join with a separator (in a subshell to keep IFS)
```

- Build argument lists with arrays, not strings: `opts=(--recursive --exclude "*.tmp"); rsync "${opts[@]}" -- "$src" "$dst"`.
- Copy an array: `copy=("${arr[@]}")`. `copy=$arr` copies only element 0 (SC2128).
- Split a string on a delimiter: `IFS=, read -ra parts <<<"a,b,,c"` gives 4 elements, including the empty one. Never use `arr=($(cmd))` or `arr=($var)`: it splits and globs (SC2207). Use `mapfile -t arr < <(cmd)`.
- `mapfile -t lines < file` strips the newline from each line; `mapfile -d '' -t files < <(find . -print0)` reads NUL-delimited names (`-d` needs Bash 4.4+). Neither works on macOS `/bin/bash` 3.2.
- `"${arr[@]}"` on an empty array expands to nothing without error under `set -u` in Bash 4.4+ (verified); on 4.3 and older use `${arr[@]+"${arr[@]}"}`.
- Slice and reverse: `"${arr[@]: -2}"` is the last two; there is no built-in reverse, so loop with a C-style `for ((i = ${#arr[@]} - 1; i >= 0; i--))`.
- Arrays cannot be exported to the environment or passed by value to other commands; pass them as arguments, via a file, or use a nameref.

## 4. Associative arrays and namerefs

```bash
declare -A owner=([alice]=ops [bob]=dev)
owner[carol]=qa
for user in "${!owner[@]}"; do printf '%s -> %s\n' "$user" "${owner[$user]}"; done
[[ -v owner[alice] ]] && echo "alice present"      # key exists (Bash 4.3+)
unset 'owner[bob]'
echo "${#owner[@]}"
declare -p owner                                     # dump for debugging
```

- Requires Bash 4.0+. Key order is unspecified; sort the keys if output order matters: `printf '%s\n' "${!owner[@]}" | sort`.
- Without `declare -A` a name with string keys becomes an indexed array and every key evaluates as arithmetic (usually index 0). Always declare first; inside functions add `-g` for globals.
- Quote keys that contain spaces or glob characters: `"${map[$key]}"`; use single quotes when unsetting: `unset 'map[$key]'` (the subscript is expanded by `unset`).
- `declare -n` / `local -n` (Bash 4.3+) creates a reference to another variable, which replaces most `eval` use:

```bash
set_result() { local -n out=$1; out=42; }
set_result answer; echo "$answer"      # 42
```

- Use a distinct nameref name (not the caller's variable name) to avoid a circular reference.
- Expand an associative array into a command line only through loops; there is no portable flat serialization other than `declare -p`.

## 5. Conditionals and arithmetic

```bash
[[ -f $file && -r $file ]]          # no quotes needed inside [[ ]]
[[ $s == *.csv ]]                   # glob match
[[ $s =~ ^v([0-9]+)\.([0-9]+) ]] && echo "${BASH_REMATCH[1]} ${BASH_REMATCH[2]}"
[[ -z ${var-} ]]                    # empty or unset (safe under set -u)
[[ -v name ]]                       # variable is set
(( n > 3 && n % 2 == 0 ))           # arithmetic test
if [ "$a" = "$b" ]; then :; fi      # POSIX form, quote both sides
```

| Test | Meaning |
|---|---|
| `-e` `-f` `-d` `-L` | Exists, regular file, directory, symlink |
| `-r` `-w` `-x` `-s` | Readable, writable, executable, size greater than zero |
| `-z` `-n` | Empty / non-empty string |
| `-nt` `-ot` | Newer / older than (modification time) |
| `-eq` `-ne` `-lt` `-gt` | Integer comparison in `[ ]` and `[[ ]]` |
| `==` `!=` `<` `>` | String comparison in `[[ ]]` (`<` and `>` compare in collation order; escape them in `[ ]`) |

- Use `[[ ]]` in Bash. Do not use `-a`, `-o` in `[ ]` (SC2166); write `[ a ] && [ b ]`. A single `=` is POSIX; `==` in `[ ]` is a Bash extension.
- Use `-e` rather than `-a` for file existence (SC2331 in ShellCheck 0.11.0).
- A regex in a variable keeps escaping simple: `re='^[A-Za-z0-9._-]+$'; [[ $name =~ $re ]]`. Captures land in `BASH_REMATCH`.
- Arithmetic: `$((a + b))`, `((n += 2))`, `$((2**10))`, `$((0x1f))`, `$((10#08))`. Integers are signed 64-bit. Leading `0` means octal, so `$((08))` is an error; force base 10 with `10#`.
- `(( ))` returns status 1 when the result is 0; see the errexit notes. Use `$(( ))` for assignments.
- Floating point is not supported: use `awk 'BEGIN { printf "%.2f\n", 7 / 3 }'` or `bc -l`.
- `case` is the portable pattern matcher: `case $s in v[0-9]*) ... ;; *.tar.gz|*.tgz) ... ;; *) ... ;; esac`.

## 6. Reading input safely

```bash
while IFS= read -r line || [[ -n $line ]]; do   # keeps last line without newline
  printf '[%s]\n' "$line"
done <input.txt

while IFS= read -r -d '' f; do                  # NUL-delimited names
  printf 'found: %s\n' "$f"
done < <(find . -type f -name '*.log' -print0)

IFS=: read -r user _ uid _ <<<"$entry"          # split fields without cut
```

- `IFS=` stops trimming of leading and trailing whitespace; `-r` stops backslash processing. Always use both.
- `read` reading from a pipe runs in a subshell, so variables set there vanish. Use `done < <(cmd)` or `shopt -s lastpipe` (non-interactive Bash only) when the loop sets variables.
- A command inside the loop that reads stdin (`ssh`, `ffmpeg`, `cat`) eats the rest of the input. Give it `</dev/null` or read the file on another descriptor: `while read -r -u 3 line; do ... done 3<file`.
- Never use `for f in $(ls)` or `for line in $(cat file)`; both split on whitespace. Use globs and `read`.
- For recursive file work: `find ... -print0 | xargs -0 -r cmd` (`-r` stops GNU `xargs` from running the command once on empty input; BSD `xargs` already skips empty input and accepts `-r` for compatibility), or `find ... -exec cmd {} +`. `find -print0` and `xargs -0` exist on GNU and BSD.
- Globs: `for f in ./*.log` with `shopt -s nullglob`; add `dotglob` to include hidden files; `globstar` enables `**` (Bash 4.0+, off by default).
- Process a CSV with `awk` or a real parser; naive `IFS=,` splitting breaks on quoted fields.
- `read -t 5` sets a timeout; `read -s` hides input (for terminals only); `read -n 1` reads a single character.

## 7. Here-documents and process substitution

```bash
name=World
cat <<EOT              # expansions happen
hello $name
EOT

cat <<'EOT'            # quoted delimiter: no expansion
literal $name and $(not run)
EOT

if true; then
  cat <<-EOT           # <<- strips leading TABs only (not spaces)
	indented with a tab
	EOT
fi

cmp <(sort a.txt) <(sort b.txt)       # process substitution as file names
while read -r l; do :; done < <(cmd)  # loop in the current shell
tee >(gzip >out.gz) >/dev/null < data # write side
grep -c x <<<"$text"                  # here-string
```

- Quote the delimiter (`<<'EOT'`) when the body contains `$`, backticks or backslashes that must stay literal, such as embedded scripts or SQL with `$1`.
- A here-document delimiter must be alone on its line, with no trailing spaces; with `<<-` it may be preceded by tabs only.
- Here-documents and here-strings create temporary files or pipes; they work in POSIX sh (here-strings `<<<` do not).
- Process substitution (`<(...)`, `>(...)`) is Bash, ksh and zsh, not POSIX, and fails when `/dev/fd` is unavailable. Exit statuses of the substituted command are not visible to the shell, so errexit does not see them.
- To pass values to a program that reads stdin without exposing them in `ps`, use a here-string or a pipe, not arguments.

## 8. Subshells and command groups

| Form | Runs in | Use for |
|---|---|---|
| `( cmds )` | Subshell (a fork) | Isolating `cd`, `export`, `set`, `IFS` changes; changes do not leak |
| `{ cmds; }` | Current shell | Grouping for redirection: `{ a; b; } >out`; note the space after `{` and the `;` before `}` |
| `$( cmds )` | Subshell | Capturing stdout |
| `cmd1 \| cmd2` | Each stage in a subshell (the last stage too, unless `lastpipe`) | Pipelines |
| `cmd &` | Background subshell | Parallel work; collect with `wait` |

```bash
( cd -- "$dir" && make )          # cd does not affect the rest of the script
{ echo header; sort data; } > out # one redirection for a group
total=0; shopt -s lastpipe
printf '%s\n' 1 2 3 | while read -r x; do total=$((total + x)); done
echo "$total"                     # 6 with lastpipe, 0 without
```

- Variables assigned in a subshell are lost. Return values through stdout, files or the exit status.
- `exit` in a subshell leaves only the subshell; `return` is only valid in a function or a sourced file.
- `wait -n` (Bash 4.3+) waits for the next background job; `wait "$pid"` returns that job's status. Collect PIDs in an array and check each status.
- `export` makes variables visible to child processes; `declare -x` does the same. Arrays and functions are not exported by default (`export -f fn` exports a function to child Bash processes, which is rarely a good idea).

## 9. Avoiding subprocesses

| Instead of | Use |
|---|---|
| `basename "$f"` / `dirname "$f"` | `${f##*/}` / `${f%/*}` |
| `echo "$s" \| sed 's/a/b/g'` | `${s//a/b}` |
| `echo "$s" \| grep -q re` | `[[ $s =~ re ]]` |
| `expr $a + $b` / `bc` for integers | `$((a + b))` |
| `x=$(printf '%05d' "$n")` | `printf -v x '%05d' "$n"` |
| `date +%s` in a loop | `$EPOCHSECONDS` (5.0+) or `printf '%(%s)T' -1` (4.2+) |
| `echo "$s" \| tr a-z A-Z` | `${s^^}` (4.0+) |
| `cat file` | `$(<file)` for small files, or redirection `< file` |
| `seq 1 $n` | `for ((i = 1; i <= n; i++))` |
| `cut -d, -f2` per line | `IFS=, read -ra f <<<"$line"; ${f[1]}` |

- Measure before rewriting readable code. The saving matters in loops over thousands of items, not in one-off commands.
- For large inputs, one `awk` or `sort | uniq -c` invocation beats any Bash loop.
