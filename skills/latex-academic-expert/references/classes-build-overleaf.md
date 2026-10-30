# Classes, latexmk and Overleaf

Reference for setting up publisher classes, automating builds with latexmk, and configuring Overleaf. Versions confirmed in 2026-10: IEEEtran 1.8b, elsarticle 3.5, acmart 2.20, latexmk 4.88, TeX Live 2026. For anything specific to a journal, the author instructions win.

## Contents

1. [IEEEtran](#1-ieeetran)
2. [elsarticle](#2-elsarticle)
3. [acmart](#3-acmart)
4. [Figures, tables and cross-references](#4-figures-tables-and-cross-references)
5. [latexmk and latexmkrc](#5-latexmk-and-latexmkrc)
6. [Overleaf](#6-overleaf)
7. [Continuous integration](#7-continuous-integration)

## 1. IEEEtran

- Install: part of TeX Live, or download from CTAN; the BibTeX style package ships with it (`IEEEtran.bst`, version 1.14).
- Class options: `conference`, `journal`, `compsoc`, `comsoc`, `transmag`, `peerreview`, `draftcls`, `draftclsnofoot`, `10pt`/`11pt`/`12pt`. The `comsoc` mode needs a suitable Times math font such as `newtxmath`.
- Skeleton:

```latex
\documentclass[conference]{IEEEtran}
\usepackage{cite}               % compresses numeric ranges
\begin{document}
\title{Paper Title}
\author{\IEEEauthorblockN{First Author}
        \IEEEauthorblockA{Department, University\\ City, Country\\ email@example.org}}
\maketitle
\begin{abstract}...\end{abstract}
\begin{IEEEkeywords}keyword one, keyword two\end{IEEEkeywords}
\section{Introduction}
Text \cite{ref1}.
\bibliographystyle{IEEEtran}
\bibliography{refs}
\end{document}
```

- Do not change margins or `\baselineskip`; use `\IEEEpubid` and `\IEEEoverridecommandlockouts` only when the publisher asks.
- Column balancing on the last page: `\IEEEtriggeratref{N}` with `\IEEEtriggercmd{\enlargethispage{-5in}}` (documented in the IEEEtran manual).
- IEEE conferences usually expect PDF eXpress-compatible output (fonts embedded, no Type 3 fonts); check with `pdffonts`.

## 2. elsarticle

- Class for Elsevier journals, version 3.5 on CTAN as of 2026-01.
- Options: `preprint` (single column, no running heads; Elsevier removed the "Preprint submitted to" footer in 3.4a), `review` (double spaced), `final`, `1p`, `3p`, `5p` (journal-like formats), `authoryear` or `number`, `sort&compress`, `times`.
- Bibliography styles: `elsarticle-num`, `elsarticle-num-names`, `elsarticle-harv` for BibTeX; pick `number` with `-num`, `authoryear` with `-harv`.
- Skeleton:

```latex
\documentclass[preprint,12pt]{elsarticle}
\usepackage{amsmath}
\journal{Journal Name}
\begin{document}
\begin{frontmatter}
\title{Paper Title}
\author[inst1]{First Author\corref{cor1}}
\ead{author@example.org}
\cortext[cor1]{Corresponding author}
\affiliation[inst1]{organization={University},country={Country}}
\begin{abstract}...\end{abstract}
\begin{keyword}one \sep two\end{keyword}
\end{frontmatter}
\section{Introduction}
Text \citep{ref1}.
\bibliographystyle{elsarticle-num}
\bibliography{refs}
\end{document}
```

- `\author`, `\address` vs `\affiliation`: since elsarticle 3.x the `\affiliation` with key-value fields (`organization`, `addressline`, `city`, `postcode`, `state`, `country`) is recommended; follow the current template.
- The `Command \c@author already defined` error was fixed in 3.4c; update the class if it appears.
- Elsevier submission systems accept a PDF plus source; check whether they want the `.bbl` or the `.bib`.

## 3. acmart

- Class version 2.20 (2026-08), maintained on CTAN and GitHub; samples ship with the package (`sample-sigconf.tex`, `sample-acmsmall.tex`).
- Formats: `acmsmall`, `acmlarge`, `acmtog`, `acmcsur`, `sigconf`, `sigplan`, `manuscript`. Options: `review`, `anonymous`, `authorversion`, `nonacm`, `screen`, `natbib` (loads natbib).
- Skeleton:

```latex
\documentclass[sigconf, review, anonymous]{acmart}
\begin{document}
\title{Paper Title}
\author{First Author}
\affiliation{\institution{University}\country{Country}}
\email{author@example.org}
\begin{abstract}...\end{abstract}
\begin{CCSXML}...\end{CCSXML}   % copy from the ACM CCS tool
\keywords{keyword one, keyword two}
\maketitle
\section{Introduction}
Text \cite{ref1}.
\bibliographystyle{ACM-Reference-Format}
\bibliography{refs}
\end{document}
```

- The rights block (`\setcopyright`, `\copyrightyear`, `\acmDOI`, `\acmConference`) comes from the ACM rights management form after acceptance; leave it unset for review.
- Do not replace `ACM-Reference-Format.bst` with another style; use its official `.bst`. If you need biblatex, check the acmart documentation for the supported route.
- Use `\citestyle{acmauthoryear}` or `acmnumeric` only where the conference allows it.
- acmart 2.19 and later changed table tagging defaults and updated conference headings for `acmsmall` proceedings; use a template copy whose version matches the venue's call.

## 4. Figures, tables and cross-references

- `graphicx`: `\includegraphics[width=\columnwidth]{name}` with no extension so pdflatex picks PDF over PNG.
- `subcaption`: `\begin{subfigure}[t]{0.48\textwidth}` pairs with `\caption{...}` and `\label{...}` inside each sub-float; do not combine with `subfig` or `subfigure`.
- `booktabs` plus `siunitx` (v3): column type `S` aligns decimals, for example `S[table-format=2.2]`; wrap text headings in braces: `{Header}`.
- `\cref{a,b}` combines references; `\Cref` capitalises at the sentence start; `capitalize,noabbrev` options spell the names out.
- Load order at the end of the preamble: `hyperref`, then `cleveref`. Packages that patch captions (`caption`, `subcaption`) load before `hyperref`.
- For float placement: `[t]` for top, `[tbp]` as a fallback, `\FloatBarrier` from `placeins` at section ends if floats drift.
- Vector figures: export PDF from the plotting tool with TrueType fonts (Type 42) so the publisher's checker passes.

## 5. latexmk and latexmkrc

Version 4.88 (2026-03). Frequently used command lines:

```bash
latexmk -pdf main.tex                       # pdflatex, bibliography and reruns automatic
latexmk -lualatex main.tex                  # LuaLaTeX
latexmk -xelatex main.tex                   # XeLaTeX
latexmk -pdf -pvc main.tex                  # watch mode, rebuild on change
latexmk -pdf -outdir=build main.tex         # keep sources clean
latexmk -c                                  # remove temporary files, keep PDF
latexmk -C                                  # remove all generated files
latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error main.tex
```

`latexmkrc` examples (Perl syntax, in the project root or `~/.latexmkrc`):

```perl
# pdflatex build with biber or bibtex chosen automatically
$pdf_mode = 1;
$out_dir = 'build';
$bibtex_use = 2;
@default_files = ('main.tex');
```

```perl
# LuaLaTeX build
$pdf_mode = 4;
$lualatex = 'lualatex -interaction=nonstopmode -halt-on-error -file-line-error %O %S';
```

- `$pdf_mode`: 1 `pdflatex`, 2 `ps2pdf`, 3 `dvipdf`, 4 `lualatex`, 5 `xelatex`.
- `$bibtex_use`: 0 never run bibtex, 1 run if the `.bib` exists, 2 run and delete the `.bbl` on `-C`.
- `$out_dir` and `$aux_dir` separate generated files; biber needs the same output directory the main run used (latexmk handles this).
- `$pdflatex` can be overridden for flags; add `-shell-escape` only for projects whose source is trusted (see the security section in SKILL.md).
- `-pvc` needs a PDF viewer; the default viewer on Linux is `xdg-open` in 4.88. Set `$pdf_previewer` for your viewer.
- Overleaf reads a `latexmkrc` in the project root; keep directory settings out of it there and check the Overleaf docs for supported variables.

## 6. Overleaf

- Compiler and TeX Live version are per project: Menu (or Settings) then the Compiler section: choose `pdfLaTeX`, `LaTeX`, `XeLaTeX` or `LuaLaTeX`, and the TeX Live version. Editor-level collaborators can change them, affecting everyone.
- New and copied projects use the newest TeX Live Overleaf has installed. Existing projects are not upgraded automatically, so a project that compiled in 2025 keeps TeX Live 2025 until someone changes it. Overleaf advises not changing an existing project to TeX Live 2026 unless you need to, since kernel and package changes can add errors (for example, `tabu` and `tabls` are unsupported in 2026).
- Set the main document in the Menu (Main document), especially when the project has several `.tex` files.
- Use "Recompile from scratch" to clear the cache, and the logs button for the first error. A "Stop on first error" option halts after the first error, which suits debugging.
- Bibliography: with biblatex, Overleaf runs the right tool via latexmk. Missing citations usually mean a `.bib` error; open the biber log.
- For arXiv, set the Overleaf TeX Live version to the one you will select on arXiv, and use Overleaf's source download. Its arXiv checklist lists the steps; see [arxiv-submission.md](arxiv-submission.md).
- Overleaf compiles in a sandbox managed by the service; on your own machine `-shell-escape` carries the risk described in the security section of SKILL.md.
- Git integration and GitHub sync are premium features; check the current Overleaf plan before relying on them.

## 7. Continuous integration

A GitHub Actions job that builds with a pinned TeX Live container, with no secrets and minimal permissions:

```yaml
name: paper
on:
  pull_request:
  push:
    branches: [main]
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    container: texlive/texlive:latest-full   # pin a tag or digest for reproducibility
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false
      - name: Build
        run: latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error main.tex
      - name: Fail on undefined references
        run: "! grep -E 'undefined' main.log"
      - uses: actions/upload-artifact@v4
        with:
          name: paper
          path: main.pdf
```

- Replace `latest-full` with a year tag matching the target venue and arXiv choice, and pin by digest for supply-chain safety; check the image's registry page for current tags.
- Do not enable `-shell-escape` for pull requests from forks.
- Cache nothing that depends on untrusted input; the build is quick enough without caches for most papers.
