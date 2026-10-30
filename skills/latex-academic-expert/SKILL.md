---
name: latex-academic-expert
description: >-
  Writes, builds and debugs LaTeX for journal and conference papers and theses: IEEEtran, elsarticle and acmart classes, BibTeX versus biblatex with biber, natbib, figures, booktabs and siunitx tables, cleveref and hyperref, latexmk, Overleaf settings and arXiv submission. Use when a .tex, .bib, .bbl, .cls, latexmkrc or 00README file is involved, or when a log shows Undefined control sequence, Missing $ inserted, Overfull hbox, Citation undefined or a biber error. Not for generating figures with Matplotlib (use scientific-python-expert) or Word documents.
license: MIT
metadata:
  version: "3.1.0"
---

# LaTeX Academic Expert

This skill covers preparing manuscripts in LaTeX for publishers and preprint servers: choosing and configuring a document class, managing the bibliography, placing figures and tables, cross-references, automating the build with latexmk, working in Overleaf, packaging for arXiv, and reading compile logs. It does not cover producing the figure files themselves or editing Word documents.

> Verified against TeX Live 2026 (released 2026-03), latexmk 4.88, biblatex 3.22, biber 2.21, acmart 2.20, elsarticle 3.5, IEEEtran 1.8b; arXiv offering TeX Live 2025 (default) and 2023 (2026-10).

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

- Covered: document classes `IEEEtran`, `elsarticle`, `acmart` and thesis classes; BibTeX, biblatex with biber, natbib; `graphicx`, `subcaption`, `booktabs`, `siunitx`; `cleveref` and `hyperref`; `latexmk` and `latexmkrc`; Overleaf compiler and TeX Live settings; arXiv packaging; reading `.log` files and fixing common errors.
- Not covered: creating plots and figures from data with Python (scientific-python-expert); Word `.docx` manuscripts; Markdown or HTML documentation sites; slide decks in Beamer beyond the shared build and bibliography advice.
- Publisher templates change. When a journal supplies its own class or style file, use that file as shipped and follow its author instructions over any default in this skill.

## 2. Core Expertise

| Area | Key facts |
|---|---|
| TeX Live | Annual release; 2026 came out in 2026-03. Tagged (accessible) PDF output is production-ready in 2026, and some packages were retired: `tabu` and `tabls` error out, and Overleaf lists `enumerate`, `theorem` and `verbatim` as legacy in favour of `enumitem`, `amsthm`, `fancyvrb`. Projects that built on 2025 can break on 2026, so upgrade deliberately |
| Engines | `pdflatex` is the default and the most compatible; `lualatex` and `xelatex` for system fonts and Unicode; `latex` (DVI) only for PostScript workflows. Pick one engine per project and keep it in `latexmkrc` |
| IEEEtran | Version 1.8b with BibTeX styles 1.14. Options: `conference`, `journal`, `compsoc`, `comsoc` (needs a Times math font such as `newtxmath`), `transmag`, `peerreview`. Bibliography style `IEEEtran` (BibTeX) |
| elsarticle | Version 3.5 (2026-01). Options `preprint`, `review`, `final`, `1p`, `3p`, `5p`, `authoryear`, `number`, `sort&compress`. Styles `elsarticle-num`, `elsarticle-num-names`, `elsarticle-harv`. Uses natbib; Elsevier submissions usually need BibTeX output, not biblatex |
| acmart | Version 2.20 (2026-08). Formats `acmsmall`, `acmlarge`, `acmtog`, `acmcsur`, `sigconf`, `sigplan`, `manuscript`; options `review`, `anonymous`, `nonacm`. Metadata commands (`\setcopyright`, `\acmConference`, CCS concepts) come from the publisher's rights form. Uses `ACM-Reference-Format` |
| biblatex | Version 3.22 (2026-08) with backend `biber` 2.21. biblatex and biber must be a matching pair; a version mismatch produces a control-file warning, so update both together (check the biblatex manual for the pairing) |
| BibTeX path | `natbib` or plain `\cite` with a `.bst` file; run order `latex, bibtex, latex, latex`. `bibtex8` and `upbibtex` exist for 8-bit and Japanese text |
| latexmk | Version 4.88 (2026-03). Flags `-pdf`, `-lualatex`, `-xelatex`, `-bibtex`, `-outdir=`, `-auxdir=`, `-interaction=nonstopmode`, `-halt-on-error`, `-file-line-error`, `-pvc`, `-c` and `-C` to clean. Reads `latexmkrc`, `.latexmkrc` and `~/.latexmkrc` |
| hyperref | Load near last; `cleveref` after `hyperref`; `bookmark` and `hypcap` interplay with captions; `\texorpdfstring` for math in headings |
| Figures | Vector PDF (or SVG converted to PDF) for plots; PNG for screenshots; JPEG for photographs. `pdflatex` accepts PDF, PNG, JPG; EPS needs conversion or `epstopdf` |
| Tables | `booktabs` rules (`\toprule`, `\midrule`, `\bottomrule`), no vertical rules; `siunitx` v3 for number alignment (`S` column, `\num`, `\qty`, `\unit`) |
| Overleaf | Menu or Settings, Compiler tab: set compiler (pdfLaTeX, LaTeX, XeLaTeX, LuaLaTeX) and TeX Live version per project; new and copied projects use the newest TeX Live Overleaf has installed; existing projects are never upgraded automatically; `latexmkrc` in the project root is honoured |
| arXiv | Supports TeX Live 2025 (default) and 2023; a 2026 option is planned, check the submission page. `00README.json` is generated at upload; `.bbl` is no longer mandatory when all `.bib` files are included, but a matching `.bbl` is the safest choice. See references/arxiv-submission.md |

## 3. Workflow

1. Identify the target: journal, conference or thesis, the exact template and class version the venue supplies, the page limit, the bibliography format they require, and the engine the template needs.
2. Inspect the project: main file, `\documentclass` line, loaded packages, `.bib` files, any `latexmkrc`, and the first error in the `.log` (not the last one).
3. Start from the venue's official template; copy it unmodified into the project and add content on top. Do not change margins, font sizes or `\baselineskip` to fit page limits.
4. Choose the bibliography path once (BibTeX or biblatex) and keep entries in a single maintained `.bib` file with stable citation keys.
5. Add figures as vector PDF and tables with `booktabs`; give every float a caption and a label placed after the caption.
6. Build with `latexmk` so the number of passes, bibliography runs and index runs is automatic; fix the first error, rebuild, repeat.
7. Check the output: no `Citation undefined`, no `Reference undefined`, no unexplained Overfull boxes, fonts embedded (`pdffonts main.pdf`), page count within limits.
8. Package for submission: publisher upload or arXiv (references/arxiv-submission.md). Compile the packaged copy in a clean directory before sending.

## 4. Decision Rules

- If the venue mandates a class (`IEEEtran`, `elsarticle`, `acmart`), use it and its `.bst` style; do not mix in `geometry`, `fullpage` or font-size overrides because the publisher's typesetting expects the class layout.
- If the publisher's pipeline expects BibTeX (IEEE, many Elsevier journals), use BibTeX with natbib or the supplied `.bst`; if the venue is silent and the project is new, biblatex with biber gives better Unicode, sorting and field support.
- If the paper goes to arXiv with biblatex, upload the `.bbl` generated by the same biblatex version or include all `.bib` files; see references/arxiv-submission.md.
- If the document needs system fonts, Unicode math or OpenType features, use `lualatex` (with `fontspec`); otherwise keep `pdflatex` because journal tooling is built around it.
- If a project compiled last year and fails now, first check whether the TeX Live version changed (Overleaf compiler menu or `latex --version`), then pin the older version while fixing; do not edit package files.
- If the same notation appears often, define a macro in a preamble file; if a macro would clash with a package, use `\newcommand` (errors when the name exists) rather than `\renewcommand` or `\def`.
- If a figure plot is a data-driven chart, request vector output from the plotting tool (scientific-python-expert) and include it with `\includegraphics`; use PNG at 300 dpi or more only for rasters.
- If lines overflow, fix the cause (long URL, unbreakable word, wide table) with `\url`, `\-` hints, `tabularx` or `\resizebox` as a last resort, not by loosening `\tolerance` globally.

## 5. Coding Standards

- One sentence per source line or a consistent line wrap; this makes diffs and merges readable.
- Declare the encoding and font only as the engine requires: with `pdflatex` use `\usepackage[T1]{fontenc}`; with `lualatex` or `xelatex` use `fontspec` and omit `inputenc`. Modern LaTeX defaults the input encoding to UTF-8.
- Labels use a type prefix: `fig:`, `tab:`, `sec:`, `eq:`, `alg:`, `thm:`. Keys are lowercase ASCII without spaces.
- Put the `\label` after the `\caption` (inside floats) so it refers to the float number.
- Use `~` before references and citations (`Figure~\ref{fig:x}`) or let `cleveref` insert the name; keep numbers and units together with `\,` or `siunitx`.
- Use `\emph` for emphasis, not `\it` or `\textit` for semantics; use `\text{}` inside math for words.
- Use `\input{sections/intro}` for sections; never `\include` unless `\includeonly` is used, because `\include` forces a page break.
- Avoid `\usepackage` inside body text or groups (an error in TeX Live 2025 and later); keep all packages in the preamble.
- Do not use obsolete commands: `\bf`, `\it`, `\rm`, `$$ ... $$` (use `\[ ... \]` or `equation`), `eqnarray` (use `align`), `\over`.
- Keep `.bib` fields complete (`author`, `title`, `year`, venue, `doi`), protect capitalisation with braces (`{LaTeX}`, `{BERT}`) and use `and` between authors.

## 6. Project Structure

```text
paper/
├── main.tex              # \documentclass, preamble load order, \input sections
├── preamble.tex          # packages and macros (optional split)
├── sections/             # intro.tex, method.tex, results.tex, ...
├── figures/              # PDF/PNG only; source scripts live elsewhere
├── tables/               # generated or hand-written tabular files
├── refs.bib              # single bibliography database
├── latexmkrc             # engine, bibliography tool, output directory
├── template/             # unmodified venue class and style files
└── build/                # -outdir target, not committed
```

- Commit sources, `.bib`, figures and the `latexmkrc`; ignore `build/`, `*.aux`, `*.log`, `*.bbl` (except when a submission needs a frozen `.bbl`), `*.synctex.gz`.
- Keep file names ASCII with no spaces; arXiv paths are case sensitive.

## 7. Design Patterns

- **Single preamble, many sections**: `\input` sections from `main.tex`. Cost: relative paths must be correct from the main file; use `\graphicspath{{figures/}}`.
- **Class option switch**: a `\newif\ifpreprint` or class option (`review`, `anonymous`) toggles anonymous review versus camera-ready from one source. Cost: keep both variants in CI so neither rots.
- **Generated numbers**: write result macros or `\input` snippets from the experiment pipeline (`\newcommand{\accuracy}{93.4}`) so the text never drifts from data. Cost: the build depends on the generated file existing.
- **Standalone figures**: draw TikZ or pgfplots in separate `standalone` documents, compile to PDF, include the PDF. Cost: two builds; benefit is fast main-document builds (see section 9).
- **Frozen submission folder**: copy only the used files, with the `.bbl`, to `submission/` through a script and compile there. Cost: a script to maintain; benefit is a reproducible upload.

## 8. Best Practices

- Build from the command line with `latexmk` in CI as well as in the editor, so errors found in Overleaf and locally are the same errors.
- Keep a clean bibliography: deduplicate keys, prefer DOI over free-text URLs, and check entries against the publisher page; wrong `.bib` data produces wrong references.
- Write captions that stand alone: what is plotted, units, what to notice. Reviewers read figures first.
- Make figures readable at column width: font size close to caption size, line widths of at least 0.75 pt, and colour choices that survive greyscale printing.
- Use `\cref` (cleveref) for all internal references so the word (`Figure`, `Table`, `Section`) follows the object type and changes in one place.
- Use `\autoref` only when cleveref is not allowed; avoid manual `Fig.~\ref`.
- Check accessibility when the venue asks: with TeX Live 2026 tagged PDF is production-ready; test with the venue's checker and add alt text to figures.
- Run `chktex` or `lacheck` for style hints and `latexindent` for formatting only if the team uses them; neither replaces reading the log.

## 9. Performance

- Measure first: `latexmk -pdf -time` or the Overleaf log tells which pass is slow. Typical causes are TikZ externalisation, large rasters and many `\includegraphics` of PDFs with heavy vector content.
- Draft mode: `\documentclass[draft]{...}` or `\usepackage[draft]{graphicx}` skips image loading; remember to remove before submission because draft also marks overfull boxes with black bars.
- Rasterise very dense scatter plots (millions of points) to PNG at publication resolution while keeping axes vector; the PDF viewer stays responsive.
- Cache TikZ and pgfplots with `\usetikzlibrary{external}` and `\tikzexternalize`; this needs shell-escape (see section 10), so enable it only for trusted sources, or pre-render figures instead.
- Use `-outdir`/`-auxdir` so the auxiliary files live apart from sources, and `latexmk -pvc` for incremental preview.
- On Overleaf, use "Recompile from scratch" when the cache shows stale references; use Fast or draft compile mode only while writing.
- Large biblatex bibliographies are slow: split by `refsection` only when needed, and keep `.bib` files free of unused entries by exporting only cited keys for the final submission.

## 10. Security

- `-shell-escape` (and `--enable-write18`, `\write18`) lets a document run arbitrary shell commands. The packages `minted`, `pythontex`, `svg`, `gnuplottex` and TikZ externalisation need it. Enable it only for source you wrote or fully reviewed; never for a template, thesis archive or submission received from someone else.
- Restricted shell escape is the TeX Live default (`shell_escape = p`) and only runs an allowlist of commands. Do not widen it with `shell_escape = t` in a shared `texmf.cnf` or a CI image that compiles third-party files.
- Treat `.tex` files from unknown sources as code. `\input`, `\openin` and `\write` can read or write files; TeX Live limits this by default (`openin_any`, `openout_any = p`), so keep those defaults. Compile untrusted files in a container with no network and no secrets mounted.
- Do not put tokens, passwords, internal URLs or reviewer names in `.tex` comments or `.bib` `note` fields. arXiv and many publishers distribute the source, including comments; strip comments before upload.
- Remove PDF metadata you do not want to publish (author fields in image files, `\hypersetup{pdfauthor=...}` for anonymous review) and check `pdfinfo`.
- For anonymous review, remove acknowledgements, self-identifying URLs and file names, and use the template's `anonymous` option.
- Pin tool versions in CI (TeX Live image tag, biber, latexmk) and download images from a trusted registry; do not run `curl | sh` installers.
- Do not disable TLS verification when fetching templates or packages (`tlmgr`, `curl`); use the distribution mirrors over HTTPS.

## 11. Testing

- Build check: `latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error main.tex` must exit with status 0.
- Log check: `grep -nE "Warning|Error|Overfull|Undefined" build/main.log` should show only reviewed warnings. Treat `Citation ... undefined`, `Reference ... undefined` and `There were undefined references` as failures.
- Clean-room build: `latexmk -C` then rebuild in a fresh clone or container to catch missing files and stale `.aux` content.
- PDF check: `pdffonts build/main.pdf` shows all fonts embedded (`emb yes`); `pdfinfo` shows expected page count and page size (A4 versus Letter).
- Class compliance: compile with the venue's `anonymous`, `review` or `final` options as required and compare page counts.
- Bibliography check: `biber --validate-datamodel main` (biblatex) or read the `.blg` file (BibTeX) for missing fields.
- In CI, cache the TeX Live image and fail on warnings by grepping the log for a short regex list.

## 12. Review Checklist

- [ ] Class, options and bibliography style match the venue's current template and author instructions.
- [ ] Engine and TeX Live version are pinned (`latexmkrc`, Overleaf setting, or arXiv `texlive_version`).
- [ ] `latexmk` builds from a clean state with exit status 0 and no undefined citations or references.
- [ ] Package load order is correct: `hyperref` late, `cleveref` and `bookmark` after it.
- [ ] Figures are vector or 300 dpi or higher, fonts are readable, captions are standalone, labels follow captions.
- [ ] Tables use `booktabs`, numbers are aligned with `siunitx`, units are consistent.
- [ ] Overfull and underfull boxes were reviewed, not hidden by global tolerance changes.
- [ ] No shell-escape dependency, or it is documented and limited to trusted sources.
- [ ] No secrets, comments with private notes or identifying metadata in source and PDF.
- [ ] Submission package compiles in an empty directory; arXiv package includes the `.bbl` or all `.bib` files.

## 13. Production Notes

- Reproducibility: record the TeX Live year, engine, `biblatex` and `biber` versions in the repository README; a TeX Live Docker image pinned by tag gives repeatable builds.
- Upgrades: when moving a project to a new TeX Live year, build both versions side by side, compare the logs and page counts, and fix package warnings before changing the pin. TeX Live 2026 is known to break projects relying on `tabu`, `tabls` or redefinitions of `\@array` and `\tabular`.
- Camera-ready: publishers often re-typeset. Provide source, figures, the `.bbl`, and a PDF; remove `\usepackage[draft]`, `todonotes`, `\hl` and review options before the final build.
- arXiv timing: arXiv follows TeX Live releases a few months later and keeps the last two years selectable; a paper compiled on Overleaf with a newer TeX Live than arXiv's can fail there. Match the version before uploading.
- Version control: use `git` with `latexdiff` for change-marked revision PDFs; keep the unmodified venue template in its own directory so updates are a clean replace.
- Archiving: keep the final source package (with figures and `.bbl`) alongside the PDF; many theses require PDF/A, which needs `pdfx` or `hyperref` PDF/A support and embedded fonts, so check the university's requirements.

## 14. Examples

A conference paper skeleton with `booktabs`, `siunitx`, `subcaption` and `cleveref` in a safe load order (`main.tex`):

```latex
\documentclass[conference]{IEEEtran}
\usepackage[T1]{fontenc}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{siunitx}
\usepackage{subcaption}
\usepackage[hidelinks]{hyperref}
\usepackage[capitalize,noabbrev]{cleveref} % after hyperref

\graphicspath{{figures/}}

\begin{document}
\title{A Short Study}
\author{\IEEEauthorblockN{A. Author}\IEEEauthorblockA{Example University}}
\maketitle

\begin{abstract}
One paragraph that states the result.
\end{abstract}

\section{Results}\label{sec:results}
\Cref{tab:main} lists the measurements and \cref{fig:curve} shows the trend.

\begin{table}[t]
  \caption{Latency by configuration.}\label{tab:main}
  \centering
  \begin{tabular}{l S[table-format=3.1] S[table-format=1.2]}
    \toprule
    Config & {Latency (\unit{\milli\second})} & {Error (\unit{\percent})} \\
    \midrule
    Baseline & 120.5 & 4.20 \\
    Ours     &  87.3 & 3.10 \\
    \bottomrule
  \end{tabular}
\end{table}

\begin{figure}[t]
  \centering
  \includegraphics[width=\columnwidth]{curve.pdf}
  \caption{Accuracy against training steps.}\label{fig:curve}
\end{figure}
\end{document}
```

A `latexmkrc` that builds with `pdflatex` into `build/`, runs the bibliography tool automatically and stops on errors:

```perl
$pdf_mode = 1;                  # 1 = pdflatex, 4 = lualatex, 5 = xelatex
$out_dir = 'build';
$bibtex_use = 2;                # run bibtex/biber and delete .bbl on -C
$pdflatex = 'pdflatex -interaction=nonstopmode -halt-on-error -file-line-error %O %S';
```

biblatex with biber in a paper that is not bound to a publisher `.bst`:

```latex
\usepackage[backend=biber,style=numeric,sorting=nyt,maxbibnames=10]{biblatex}
\addbibresource{refs.bib}
% ... in the text:  \parencite{knuth1984} or \textcite{lamport1994}
% ... at the end:
\printbibliography
```

Build with `latexmk -pdf main.tex`; latexmk detects biblatex and runs `biber`.

## 15. Common Mistakes

- **Wrong tool for the bibliography**: `\usepackage{biblatex}` with `bibtex` in the editor gives `Citation undefined` and empty references. Use `backend=biber` and let `latexmk` run `biber`, or switch Overleaf to the correct tool; see references/bibliography.md.
- **`hyperref` loaded too early or `cleveref` before it**: link and reference breakage, odd errors. Load `hyperref` late, `cleveref` after it.
- **Raster plots in the paper**: blurry text in figures. Export vector PDF, or PNG at 300 dpi or more.
- **Vertical lines and `\hline` in tables**: cluttered tables that venues reject. Use `booktabs` rules and `siunitx` alignment.
- **Label before caption**: `\ref` points to the section number. Put `\label` after `\caption`.
- **Changing margins or font size to hit the page limit**: desk rejection or forced reformatting. Shorten the text, tighten figures, or move material to an appendix.
- **Editing publisher class files**: breaks upgrades and may violate submission rules. Override through documented class options and macros.
- **Using `\usepackage` inside a group or environment**: compile error since TeX Live 2025. Move it to the preamble.
- **Enabling `-shell-escape` for every project**: arbitrary command execution from an untrusted file. Enable per trusted project only (section 10).
- **Case-mismatched file names**: works on Windows or macOS, fails on arXiv and Linux CI. Match the exact case of figure file names.
- **Stale `.aux`, `.bbl` or `.toc` files**: phantom errors after renaming sections or keys. Run `latexmk -C` and rebuild.
- **Fixing the last error in the log**: later errors cascade from the first. Fix the first error and rebuild.
- **Submitting with comments left in source**: private notes become public on arXiv. Strip comments (references/arxiv-submission.md).

## 16. References

- [references/bibliography.md](references/bibliography.md): BibTeX versus biblatex and biber, natbib commands and options, `.bib` entry hygiene, publisher styles, switching between systems, bibliography errors.
- [references/arxiv-submission.md](references/arxiv-submission.md): packaging a source tree for arXiv, TeX Live version choice, `.bbl` handling, `00README`, file naming, figures, ancillary files, pre-upload checks.
- [references/compile-errors.md](references/compile-errors.md): reading the log and fixing Undefined control sequence, Missing $ inserted, Overfull hbox, undefined citations or references, runaway arguments and other common messages.
- [references/classes-build-overleaf.md](references/classes-build-overleaf.md): IEEEtran, elsarticle and acmart setup and options, latexmk and `latexmkrc` recipes, Overleaf compiler and TeX Live settings, CI builds.
- Official docs: https://www.tug.org/texlive/ (TeX Live), https://ctan.org/pkg/latexmk (latexmk), https://ctan.org/pkg/biblatex (biblatex), https://ctan.org/pkg/acmart, https://ctan.org/pkg/elsarticle, https://ctan.org/pkg/ieeetran, https://docs.overleaf.com/getting-started/recompiling-your-project/selecting-a-tex-live-version-and-latex-compiler, https://info.arxiv.org/help/submit_tex.html, https://info.arxiv.org/help/00README.html, https://arxiv.org/faq/texlive.html
