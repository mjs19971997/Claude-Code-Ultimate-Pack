# Compile Errors and Warnings

Reference for reading LaTeX logs and fixing the messages that come up most in paper and thesis work. Written against TeX Live 2025 and 2026 behavior; message wording can differ slightly between engines (`pdflatex`, `lualatex`, `xelatex`).

## Contents

1. [Reading the log](#1-reading-the-log)
2. [Errors](#2-errors)
3. [Citation and reference warnings](#3-citation-and-reference-warnings)
4. [Box warnings](#4-box-warnings)
5. [Float and layout warnings](#5-float-and-layout-warnings)
6. [Fonts, encoding and engines](#6-fonts-encoding-and-engines)
7. [Package and class problems](#7-package-and-class-problems)
8. [Bisecting a failing document](#8-bisecting-a-failing-document)

## 1. Reading the log

- Fix the first error. Later errors usually cascade from it, and one unclosed brace can generate dozens.
- Build with `latexmk -pdf -interaction=nonstopmode -file-line-error main.tex`. Errors then print as `./sections/method.tex:42: Undefined control sequence.` with the file and line.
- In the `.log`, an error starts with `!`, followed by the message, a context line (`l.42 ...`) that shows the text read so far and, on the next line, the text not yet read. The break between the two halves marks where TeX stopped.
- `-halt-on-error` stops at the first error; without it TeX continues and may print many follow-on errors.
- Errors in an `\input` file show the file name inside parentheses in the log; track the open parenthesis to know which file you are in.
- `Overfull`, `Underfull`, `Citation` and `Reference` lines are warnings, not errors; the PDF still builds.
- Overleaf: open the logs panel and use "Recompile from scratch" before concluding the code is wrong; stale cache files cause misleading messages.

## 2. Errors

| Message | Typical cause | Fix |
|---|---|---|
| `! Undefined control sequence.` | Misspelled command, missing package, command defined in a package loaded later, or a command used in the wrong engine | Check the spelling shown after `l.NN`, add the package that defines it (for example `\toprule` needs `booktabs`, `\SI` and `\qty` need `siunitx`, `\cref` needs `cleveref`), move the definition earlier |
| `! Missing $ inserted.` | A math-only symbol or `_`, `^`, `\alpha` outside math mode, or text-only construct inside math | Wrap in `$...$` or `\(...\)`; escape literal underscores as `\_`; in file names and URLs use `\detokenize` or `\url` |
| `! Extra }, or forgotten $.` | Unbalanced braces or math delimiters | Count braces around the reported line; look for a missing `$` before it |
| `! Missing } inserted.` / `! Missing { inserted.` | Unbalanced braces | Add the brace; check macro arguments |
| `! LaTeX Error: Environment xyz undefined.` | Package or class that defines the environment is not loaded, or typo | Load the package (`algorithm`, `algpseudocode`, `amsthm`), check `\begin` name |
| `! LaTeX Error: \begin{x} on input line N ended by \end{y}.` | Mismatched environments | Fix the `\end` or find the missing `\end` earlier |
| `! LaTeX Error: File 'x.sty' not found.` | Package not installed in this TeX tree | Install it (`tlmgr install x` for TeX Live, MiKTeX console), or add it to the project |
| `! LaTeX Error: File 'fig.png' not found.` | Wrong path, extension or case; file lives outside `\graphicspath` | Fix the path; match case; use `\graphicspath{{figures/}}` |
| `! LaTeX Error: Unknown graphics extension: .eps.` | EPS with `pdflatex` | Convert to PDF, or load `epstopdf` |
| `! LaTeX Error: Option clash for package x.` | Package loaded twice with different options | Pass options with `\PassOptionsToPackage{opt}{x}` before `\documentclass` |
| `! LaTeX Error: Command \xxx already defined.` | `\newcommand` for an existing name | Choose a new name, or use `\renewcommand` only if overriding is intentional; check class source for the original |
| `! Package xxx Error: ...` | Package-specific; the message states the cause | Read the message and the package manual; do not suppress |
| `! Paragraph ended before \xxx was complete.` | Blank line inside the argument of a command that does not allow paragraphs | Remove the blank line, or use the `\long` version / `\par`-safe form |
| `! Runaway argument?` / `! File ended while scanning use of \xxx.` | Missing closing brace or delimiter | Find the `{` that was never closed; bisect (section 8) |
| `! Double superscript.` / `! Double subscript.` | `x^a^b` or `x_a_b` | Group: `x^{a^b}`, `x_{a_b}` |
| `! Illegal parameter number in definition of \xxx.` | `#` inside a macro definition used in a nested definition, or in a `\newcommand` body referencing a missing argument | Double the `#` (`##`) in nested definitions or declare the argument count |
| `! Misplaced alignment tab character &.` | `&` outside tabular or align, or unescaped in text | Use `\&` in text, or fix the environment |
| `! Misplaced \noalign.` | `\hline`, `\midrule` or `\cline` in a place where a row is expected, often right after `\\` inside a macro or after a missing `\\` | Remove the stray rule and check row ends |
| `! Extra alignment tab has been changed to \cr.` | More `&` than columns | Add columns or remove `&` |
| `! Not in outer par mode.` | Float (`figure`, `table`) used inside another box, `minipage`, or `multicols` | Use `\captionof` with `capt-of` or place the float outside |
| `! Too many unprocessed floats.` | Many floats without text to place them | Use `\clearpage`, `[!ht]` sparingly, or the `placeins` package (`\FloatBarrier`) |
| `! TeX capacity exceeded, sorry [...]` | Infinite recursion in a macro, or huge figure/TikZ memory | Find the recursive macro; for pgfplots increase limits only after reducing data |
| `! Dimension too large.` | PGF/TikZ coordinates too big, or `\hsize` computations | Scale data, use `fpu` library for pgfplots |
| `! Emergency stop` / `*** (job aborted, no legal \end found)` | Missing `\end{document}` or `-interaction=nonstopmode` after an earlier fatal error | Add `\end{document}`, fix the first error |
| `! Use of \xxx doesn't match its definition.` | Wrong argument delimiters, often a fragile command in a moving argument | Use `\protect` or `\robustify`; see fragile commands in headings and captions |
| `! LaTeX Error: Something's wrong--perhaps a missing \item.` | List environment with no `\item`, or text before the first `\item` | Add `\item` |
| `! Package inputenc Error: Unicode character x (U+XXXX) not set up for use with LaTeX.` | Character without a glyph or declaration | Use a UTF-8 aware font (`T1`/`fontenc`), declare with `\DeclareUnicodeCharacter`, or use `lualatex` |
| `! LaTeX Error: \usepackage may only be used in the preamble.` or an error for `\usepackage` in a group | Package loaded in the body or inside a group, which TeX Live 2025 reports as an error | Move all `\usepackage` lines to the preamble |

## 3. Citation and reference warnings

| Message | Fix |
|---|---|
| `LaTeX Warning: Citation 'key' on page N undefined` | The key is misspelled, not in the `.bib`, or the bibliography tool was not run. Re-run `latexmk`; read the `.blg` or biber log |
| `LaTeX Warning: Reference 'x' on page N undefined` | Label typo or missing second pass. Re-run; check `\label` is after `\caption` and inside the float |
| `LaTeX Warning: There were undefined references.` | Summary of the above; fix each cited line |
| `LaTeX Warning: Label 'x' multiply defined.` | Duplicate label; rename one |
| `LaTeX Warning: Label(s) may have changed. Rerun to get cross-references right.` | Another pass is needed; `latexmk` handles it automatically |
| `Package natbib Warning: Citation 'x' undefined` | Same as above, with natbib |
| `Package biblatex Warning: Please (re)run Biber on the file` | Run `biber` or `latexmk` |
| `Package hyperref Warning: Token not allowed in a PDF string` | Math or macros in a section title; use `\texorpdfstring{TeX}{plain text}` |
| `Package hyperref Warning: Destination with the same identifier` | Duplicate page or counter identifiers; add `hypertexnames=false` or fix duplicated counters |

## 4. Box warnings

| Message | Meaning | Fix |
|---|---|---|
| `Overfull \hbox (12.3pt too wide) in paragraph at lines a--b` | A line sticks out into the margin | Reword; add hyphenation hint `\-`; use `\url{}` for URLs; set `\usepackage{microtype}`; for column stuff, shorten or use `\raggedright`; use `\sloppy` locally or `emergencystretch` for a stubborn paragraph |
| `Overfull \hbox ... in alignment` | A table is too wide | Reduce columns, use `tabularx`, `\small`, `\setlength{\tabcolsep}{4pt}`, rotate with `rotating`, or `\resizebox{\linewidth}{!}{...}` as a last resort |
| `Overfull \vbox` | A box is too tall for the page | Reduce figure height, split the table with `longtable` |
| `Underfull \hbox (badness 10000)` | Line stretched too far, often around `\\` in text | Remove manual line breaks; fix the paragraph or the `\raggedright` setting |
| `Underfull \vbox` | Page filled poorly because of float placement | Adjust float placement; add text; check `\flushbottom` |

Overfull boxes under 1 pt are usually invisible; look at ones above 3 pt. Do not hide them by raising `\hfuzz` or `\tolerance` globally. In `draft` class mode overfull lines are marked with a black bar, which helps locate them.

## 5. Float and layout warnings

| Message | Fix |
|---|---|
| `Float too large for page by 20pt` | Reduce `width` or `height` of the figure, or allow a float page (`[p]`) |
| `Float(s) lost` | Floats inside a `minipage`, or `\FloatBarrier` problems; move floats out |
| `` `h' float specifier changed to `ht' `` | Informational: LaTeX cannot place the float "here"; use `[t]`, `[tbp]` or `float` package's `[H]` only when needed |
| `Package caption Warning: Unused \captionsetup` | Unneeded setup; remove |
| `Package geometry Warning: Over-specification` | Conflicting page size options; keep one |
| `LaTeX Font Warning: Font shape ... undefined` | Requested size or style not available; substitution occurred |

## 6. Fonts, encoding and engines

- With `pdflatex`, the old `\usepackage[utf8]{inputenc}` is optional since UTF-8 is the default. Avoid `ucs` and the `utf8x` option; they are obsolete and can break other packages.
- With `xelatex` and `lualatex`, `fontspec` loads system or bundled fonts. Do not load `inputenc` or use T1 fonts as the only definition.
- `Package fontspec Error: The font "X" cannot be found` means the font name differs from the system name or the engine is `pdflatex`. Use `fc-list` (Linux) to see the exact family name.
- `pdfTeX warning: PDF inclusion: found PDF version <1.7>, but at most version <1.5> allowed` is informational; use `\pdfminorversion` only if the publisher requires a specific version.
- Mismatched `\documentclass` options and engine (for example a class that needs `lualatex`) produce odd errors from the first font command; check the template instructions.
- For Type 3 fonts in figures, which some publishers reject, export plots with embedded TrueType (Type 42) fonts from the plotting tool.
- Check embedded fonts with `pdffonts build/main.pdf`; every row should read `emb yes`.

## 7. Package and class problems

- Load-order conflicts: `hyperref` late, `cleveref` after `hyperref`, `bookmark` after `hyperref`, `caption` after the class, `subcaption` instead of `subfig` or `subfigure` (avoid mixing the three).
- `siunitx` v3 renamed or removed options and commands: `\SI` still works; `\qty`, `\unit`, `\num`, `\ang` are the preferred forms. Use `\sisetup{...}` with v3 option names, and read the log hint that prints for an unknown key.
- `array`/`tabular` redefinitions inside templates can break under newer kernels with tagging support; if a table errors only on a new TeX Live, test with the template's default table first.
- `tabu` and `tabls` are no longer supported in TeX Live 2026; replace `tabu` with `tabularx` or `tabulary`.
- `todonotes`, `soul` and `ulem` do not like fragile commands in arguments; wrap with `\protect`.
- If a class says it needs a package version newer than the installed one, update the TeX distribution; copying a newer `.sty` into the project may conflict with other packages.
- `Package xcolor Error: Undefined color` / option clash: load `xcolor` once with options via `\PassOptionsToPackage`.

## 8. Bisecting a failing document

1. Run `latexmk -C`, then build. If the error disappears, stale auxiliary files were the cause.
2. Comment out `\input` lines from the end until the build passes; the last removed section holds the first error.
3. Inside that section, comment out halves of the text with `\iffalse ... \fi` (not nested) or `%` per line.
4. Create a minimal working example: the same `\documentclass`, the failing snippet, and only the packages needed. If the minimal example works, add the other packages back one by one.
5. Try a different engine or TeX Live version to see whether the problem is version-specific.
6. Read the package manual for the failing macro rather than searching for a workaround first.
