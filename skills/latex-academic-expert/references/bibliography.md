# Bibliography: BibTeX, biblatex, natbib

Reference for choosing and operating a LaTeX bibliography system in papers and theses. Versions checked (2026-10): biblatex 3.22, biber 2.21, latexmk 4.88, TeX Live 2026. Where a version pairing matters, the biblatex manual is the authority.

## Contents

1. [Choosing a system](#1-choosing-a-system)
2. [BibTeX with natbib](#2-bibtex-with-natbib)
3. [biblatex with biber](#3-biblatex-with-biber)
4. [Entry hygiene](#4-entry-hygiene)
5. [Publisher styles](#5-publisher-styles)
6. [Switching systems](#6-switching-systems)
7. [Bibliography errors](#7-bibliography-errors)

## 1. Choosing a system

| Situation | Use | Reason |
|---|---|---|
| Venue supplies a `.bst` (IEEEtran, elsarticle, ACM-Reference-Format, Springer, many others) | BibTeX | The publisher tested the style with its pipeline |
| Venue is silent, new thesis, Unicode names, many entry types | biblatex + biber | Better sorting, localisation, field coverage, customisation |
| Journal system needs a `.bbl` or rejects biblatex | BibTeX, or biblatex and upload the generated `.bbl` | Confirm the publisher's instructions first |
| Existing project already works | Keep it | Switching changes citation style and page count |

Mixing is not possible: `natbib` and `biblatex` conflict, and a `\bibliographystyle` command does not work with biblatex.

## 2. BibTeX with natbib

Minimal setup:

```latex
\usepackage[numbers,sort&compress]{natbib}   % or authoryear
% ...
\bibliographystyle{IEEEtran}                 % file IEEEtran.bst
\bibliography{refs}                          % refs.bib, no extension
```

- Run order: `latex`, `bibtex main`, `latex`, `latex`. `latexmk -pdf main.tex` does all of it.
- Citation commands: `\citet{key}` (Author (year) or Author [1]), `\citep{key}` (parenthetical), `\citep[see][p.~5]{key}`, `\citeauthor{key}`, `\citeyear{key}`. Starred forms (`\citet*`) print full author lists.
- Common options: `numbers` or `authoryear` (a citation style choice), `round`/`square`, `sort`, `sort&compress` (needs `numbers`), `super`.
- Many classes load natbib themselves (`elsarticle`, `acmart` by default). Do not load it again with different options; pass options through the class or `\PassOptionsToPackage{numbers}{natbib}` before `\documentclass`.
- `\bibliographystyle` and `\bibliography` must appear once, after the last `\cite` in the document order that matters; they write to the `.aux`.
- `bibtex` is 7-bit by design and truncates with `Warning--I'm ignoring ...`; protect accented names with braces (`{\"O}`) or use `bibtex8`/`biber` for UTF-8.
- If `bibtex` reports `I couldn't open style file xxx.bst`, the `.bst` is missing from the project folder or TeX tree.

## 3. biblatex with biber

Minimal setup:

```latex
\usepackage[backend=biber,style=numeric,sorting=nyt,giveninits=true]{biblatex}
\addbibresource{refs.bib}      % with extension; multiple allowed
% body: \cite{k}, \parencite{k}, \textcite{k}, \autocite{k}
\printbibliography             % at the point where the list should appear
```

- Build: `latexmk -pdf main.tex` detects biblatex and runs `biber`. Manual order: `pdflatex main`, `biber main`, `pdflatex main`, `pdflatex main`. Note the argument to `biber` is the job name without extension.
- Styles: `numeric`, `numeric-comp`, `alphabetic`, `authoryear`, `authortitle`, `ieee` (from the biblatex-ieee package, check availability), `apa` (biblatex-apa), `nature`, `chem-acs` and others in separate packages. Install the style package that matches the venue.
- Common options: `sorting=nty|nyt|ynt|none`, `maxbibnames`, `maxcitenames`, `url=false`, `doi=true`, `isbn=false`, `backref=true`, `natbib=true` (accept natbib-style commands such as `\citep`).
- `\addbibresource` takes a path; remote resources need explicit `location=remote` and are rarely appropriate for reproducible builds.
- Sections: `refsection` for per-chapter bibliographies; `\printbibliography[section=2,title=...]`; `\printbibliography[type=online,heading=subbibliography]` for split lists.
- `\usepackage{csquotes}` is recommended and the biblatex manual requires a supported language package (`babel` or `polyglossia`).
- Version pairing: biblatex and biber evolve together. A control-file version warning in the biber output means the two do not match; update both from the same TeX Live release rather than mixing a manual download with an older distribution.
- A stale `biblatex.sty` copied into the project directory is the usual cause of arXiv or Overleaf errors such as `Patching \MakeUppercase failed` (fixed upstream in biblatex 3.18b and later). Delete the local copy.

## 4. Entry hygiene

```bibtex
@article{doe2024fast,
  author  = {Doe, Jane and Roe, Richard},
  title   = {Fast Methods for {BERT} Inference},
  journal = {Journal of Examples},
  year    = {2024},
  volume  = {12},
  number  = {3},
  pages   = {45--67},
  doi     = {10.0000/example.2024.001},
}
```

- Keys: stable, lowercase ASCII, no spaces or commas. Do not rename keys after submission.
- Protect capitalisation of acronyms and proper nouns with braces; BibTeX styles lower-case titles. biblatex styles keep title case as written unless a style changes it.
- Separate authors with `and`; for a corporate author wrap in double braces: `author = {{World Health Organization}}`.
- Use `--` for page ranges. Provide `doi` as the bare identifier, not the URL.
- biblatex field names differ from BibTeX in places: `journaltitle` (alias `journal`), `date` (alias `year`), `location` (alias `address`), `institution` for reports, `eprint` and `eprinttype` for arXiv (`eprinttype = {arxiv}`).
- Export from a reference manager with a Better BibTeX or BibLaTeX profile, keep only cited entries in the final package, and review the output once; exporters occasionally produce wrong types.
- Validate with `biber --tool --validate-datamodel refs.bib` (biblatex) or read `main.blg` for BibTeX warnings about missing fields.
- Do not store private comments or credentials in `note` or `annote` fields; the `.bib` is often uploaded.

## 5. Publisher styles

| Publisher template | Bibliography | Notes |
|---|---|---|
| IEEEtran | `\bibliographystyle{IEEEtran}` with BibTeX | Version 1.8b class; BibTeX styles v1.14; control entries with `IEEEtranBSTCTL`. IEEE journals generally expect BibTeX, not biblatex |
| elsarticle | `elsarticle-num`, `elsarticle-num-names`, `elsarticle-harv` | natbib is loaded by the class; choose `authoryear` or `number` class option consistently with the style |
| acmart | `\bibliographystyle{ACM-Reference-Format}` | acmart loads natbib by default; check the class documentation for the `natbib=false` option before using biblatex |
| Thesis classes | Usually free | Pick biblatex unless the university says otherwise |

When the author instructions and this table disagree, follow the author instructions.

## 6. Switching systems

BibTeX to biblatex:

1. Remove `natbib`, `\bibliographystyle`, `\bibliography`.
2. Add the `biblatex` line with `backend=biber` and `\addbibresource{refs.bib}`.
3. Replace `\bibliography{...}` with `\printbibliography`. Optionally keep old commands via `natbib=true`.
4. Rebuild with `latexmk`; delete the old `.bbl`, `.blg` and `.aux` first (`latexmk -C`).

biblatex to BibTeX (publisher request): generate the `.bbl` once with biber for archive or arXiv, but for publishers that run BibTeX themselves convert the setup the other way, add `natbib` and the `.bst` from the venue, and compare the reference list visually.

## 7. Bibliography errors

| Message | Cause and fix |
|---|---|
| `Citation 'x' on page N undefined` after a full build | Key typo, entry not in `.bib`, or bibliography tool not run. Check spelling and the `.blg` file or biber log |
| `Please (re)run Biber on the file` | biblatex needs another biber pass; use `latexmk` or run `biber main` |
| `I found no \citation commands` / `no \bibdata command` | BibTeX used with no `\cite` or no `\bibliography`; or the build tool is not set to the right program |
| `Empty bibliography` | No cited keys, or `\nocite{*}` missing when a full list is wanted |
| `Datasource refs.bib not found` | `\addbibresource` path wrong or the file is in a different directory from the output directory |
| `This is a BibTeX control file, expected biblatex` style warnings | Mixed natbib and biblatex or wrong backend; remove the other system |
| `Control file version ... biber ... differ` | biblatex and biber mismatch; update both |
| `(babel) Package babel Warning: ... csquotes` | Install or load `csquotes` and set the main language in `babel` |
| Question marks `(?)` for all references on Overleaf | Wrong compiler recipe or an error in the `.bib` file; open the logs and fix the first error |
