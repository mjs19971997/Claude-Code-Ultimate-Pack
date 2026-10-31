---
name: scientific-writing-expert
description: >-
  Writes, structures and revises engineering, computer science and telecom research papers: IMRaD and conference or journal layout, titles, abstracts, introductions with contribution lists, related work, system models, results, limitations, figures and tables, reviewer responses, rebuttals, cover letters and thesis chapters. Use when drafting or editing a manuscript, abstract, response letter or rebuttal, or checking authorship, CRediT roles, self-plagiarism and AI-use disclosure. Not for LaTeX syntax or BibTeX (use latex-academic-expert), statistics reporting details (use statistics-expert), or plotting code (use scientific-python-expert or matlab-expert).
license: MIT
metadata:
  version: "3.2.0"
---

# Scientific Writing Expert

This skill covers the prose and structure of research papers in engineering, computer science and telecommunications: how to organise a manuscript, how to write each section so that a reviewer finds the claim, the evidence and the limits quickly, and how to handle review, authorship and disclosure. It works on text and arguments, not on typesetting, statistics or plotting code, which belong to other skills.

> Verified against CRediT taxonomy (ANSI/NISO Z39.104-2022, 14 roles) and, via secondary summaries only, the IEEE Author Center AI-content policy, the ACM authorship policy and the IEEE Editorial Style Manual for Authors; the primary publisher pages were not reachable from the build environment, so every policy statement below carries a "check the current page" instruction (2026-10).

## Contents
1. [Scope](#1-scope)
2. [Core Expertise](#2-core-expertise)
3. [Workflow](#3-workflow)
4. [Decision Rules](#4-decision-rules)
5. [Writing Standards](#5-writing-standards)
6. [Document Structure](#6-document-structure)
7. [Design Patterns](#7-design-patterns)
8. [Best Practices](#8-best-practices)
9. [Reader Efficiency](#9-reader-efficiency)
10. [Integrity and Ethics](#10-integrity-and-ethics)
11. [Draft Checks](#11-draft-checks)
12. [Review Checklist](#12-review-checklist)
13. [Submission Notes](#13-submission-notes)
14. [Examples](#14-examples)
15. [Common Mistakes](#15-common-mistakes)
16. [References](#16-references)

## 1. Scope

- Covered: paper structure (IMRaD and its engineering variants), titles, abstracts, introductions and contribution lists, related work, method and system-model sections, results and discussion, limitations and threats to validity, conclusions, figures and tables as writing artefacts (captions, labels, palettes), notation consistency, reproducibility and artifact statements, response letters, rebuttals, cover letters, thesis chapters, plagiarism and self-plagiarism, publisher AI-use disclosure, authorship and CRediT.
- Not covered: LaTeX syntax, document classes, BibTeX and arXiv packaging (latex-academic-expert); choice and reporting of statistical tests, confidence intervals and effect sizes (statistics-expert); plotting code (scientific-python-expert, matlab-expert); simulator set-up for telecom results (ns3-expert); 3GPP terminology and clause references (5g-nr-3gpp-expert).
- Venue rules override this skill. Always read the call for papers or author instructions of the target venue before applying a pattern from here.

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Paper skeleton | Introduction, Related Work, System Model or Method, Evaluation (setup, results, discussion), Limitations, Conclusion. IMRaD (Introduction, Methods, Results, and Discussion) is the common name; telecom and systems papers usually split Methods into System Model, Problem Formulation and Proposed Scheme |
| Abstract | One paragraph of 150 to 250 words unless the venue sets a limit: context, gap, method, main quantitative result, implication. No citations, no undefined acronyms, no forward references |
| Contribution list | 2 to 4 bullets in the introduction, each a verifiable claim ("we derive...", "we show on X that...", "we release..."), each mapped to a section and a piece of evidence |
| Related work | Grouped by approach, each group ends with how the present work differs; a table of prior work against criteria is often clearer than a list of summaries |
| Figures and tables | One message per figure; caption that stands alone; axis labels with quantity and unit; colour-blind-safe palettes (for example the Okabe-Ito set) plus a second cue such as marker or line style, so grayscale print still works |
| Reviewer response | Point-by-point letter: quote the comment, state the action, point to the changed location (section, page or line); polite on disagreement, with evidence |
| Authorship | CRediT lists 14 roles: Conceptualization, Data curation, Formal analysis, Funding acquisition, Investigation, Methodology, Project administration, Resources, Software, Supervision, Validation, Visualization, Writing - original draft, Writing - review and editing. Roles describe contributions; the venue decides who qualifies as an author |
| AI-use disclosure | IEEE and ACM both state that AI tools cannot be listed as authors and that human authors remain accountable. IEEE (per secondary summaries) asks for disclosure of AI-generated content in the acknowledgments, naming the system and the affected sections; ACM wording on disclosure of writing assistance has changed between versions. Read the current page of the target venue before submission |
| Style guides | IEEE Editorial Style Manual for Authors (journals, transactions, letters) and the ACM publication guidelines and templates. Use the one named by the venue; check the version date on the page |
| Reproducibility | Artifact statement with a persistent link, version or commit, licence, hardware and software environment, random seeds, and what is not released and why |

## 3. Workflow

1. Identify the venue, the paper type (full paper, letter, short paper, workshop, thesis chapter), the page or word limit, the review model (single blind, double blind, open) and the template and policy pages.
2. Write the claim first: one sentence stating what the paper shows, for whom, with what evidence. Ask for it if the draft does not contain one.
3. Build the skeleton as a list of section headings with one sentence per section describing its job. Map each contribution to a section and each section to a figure or table.
4. Draft in the order that reduces rework: figures and tables, method, results, introduction, related work, abstract, title. Rewrite the abstract and title last.
5. Revise at three levels in separate passes: argument (does evidence support each claim), structure (paragraph order, topic sentences, section transitions), sentence (length, voice, terminology, notation).
6. Run the draft checks in section 11 (claim-evidence table, notation table, abbreviation list, cross-reference check, citation check).
7. For revisions, parse every reviewer comment into a numbered list, decide the action for each (change, clarify, decline with evidence), edit the manuscript first and write the response letter second, then verify that each pointer in the letter matches the final text.
8. Before submission, check the policy items in section 13 (anonymity, AI disclosure, artifact statement, ethics, conflicts, CRediT or author contribution statement, prior-publication overlap).

## 4. Decision Rules

- If the paper has a single main idea, state it in the title and abstract; if it has three equal ideas, it probably needs splitting or a clearer unifying claim.
- If a sentence needs a figure to be understood, refer to the figure in the same sentence; if a figure needs more than its caption and one paragraph, simplify the figure.
- If a result is not tied to a claim, cut it or move it to an appendix; if a claim has no result, soften it or add the evidence.
- If related work is longer than a page in a conference paper, group it harder; keep only work that a reviewer would expect to see or that you must contrast with.
- If a term has two names in the draft, pick one and use it everywhere; add a notation table when more than about 15 symbols are used.
- If a reviewer is factually wrong, show the evidence politely and still change the paper so the next reader does not make the same mistake.
- If a reviewer asks for an experiment that cannot be done, say so, explain why, and add the closest feasible evidence or a limitation statement.
- If text from your earlier paper is needed, cite it and rewrite; if more than background or definitions overlaps, contact the editor before submission.
- If a tool generated or rewrote any text, figure or code, follow the venue's disclosure rule and remain responsible for every statement and reference; verify each citation against the actual source.
- If the venue conflicts with this skill (section order, abstract length, anonymity rules), follow the venue.

## 5. Writing Standards

- One idea per paragraph. The first sentence states the point; the rest supports it. A reader skimming only first sentences should follow the argument.
- Prefer short, concrete sentences; keep subject and verb close. Use the active voice for what you did ("we measure"), the passive where the actor is irrelevant ("packets are dropped when the queue is full").
- State quantities with units and conditions: "median latency of 4.2 ms at 10 000 users per cell", not "low latency". Use SI units, a space between number and unit, and consistent significant digits.
- Define each acronym once at first use in the abstract and again in the body; do not define acronyms used only once. Use the form your venue prescribes for the plural.
- Hedge by evidence, not by habit: "suggests" for indirect evidence, "shows" for direct measurement, "proves" only for a proof. Remove "very", "novel", "state-of-the-art" and "significant" unless backed by a comparison or a test.
- Use one symbol per concept, define it at first use, keep one font convention (for example bold lowercase for vectors, bold uppercase for matrices) and never reuse a symbol with a second meaning. Put a notation table in the system-model section for symbol-heavy papers.
- Number equations that are referenced. Introduce each equation with a sentence and define every symbol right after it. Punctuate equations as part of the sentence.
- Refer to figures, tables and sections by label ("Fig. 3", "Table II", "Section V") in the form the venue style prescribes; IEEE journal style abbreviates "Fig." in running text, check the manual for sentence-start rules.
- Cite claims, not topics. A citation after a sentence must support that sentence. Prefer primary sources and archival versions over preprints when both exist.
- Keep tense consistent: present for what the paper does and for general facts, past for what was done in an experiment.
- Write for an informed reader who is not in your sub-field. Spell out the problem setting before the technique.
- Use inclusive, plain language; avoid idioms and untranslatable metaphors, because many readers and reviewers work in a second language.

## 6. Document Structure

Typical conference or journal layout for engineering and telecom work:

```text
Title
Abstract (150-250 words) and keywords
1  Introduction            context, gap, idea, contributions, paper outline (optional)
2  Related Work            grouped by approach, positioning against each group
3  System Model / Background   notation, assumptions, problem statement
4  Proposed Method         design, algorithm, analysis, complexity
5  Evaluation              setup, baselines, metrics, results, ablations, discussion
6  Limitations             scope, assumptions, threats to validity
7  Conclusion              what was shown, what follows, future work
   Acknowledgments         funding, non-author help, disclosures required by the venue
   Data and code availability / artifact statement
   References
   Appendices              proofs, extra figures, parameter tables
```

- Related work may come last in short papers and in papers where the technique must be understood first; say why in one line if you move it.
- Put the main result early. The introduction should preview it with a number, not only say that results are good.
- Theory-first papers: definitions, theorem, proof sketch in the body, full proof in the appendix. Systems papers: design goals, architecture, implementation, evaluation. Measurement papers: data collection, methodology, findings, implications.
- Thesis chapters: each chapter opens with a short motivation and chapter map, closes with a summary and the link to the next chapter. Papers reused as chapters are rewritten for the thesis narrative, and the overlap is declared in the preface or a chapter note with the publisher's reuse permission.
- Page-limited venues: references usually count unless the call says otherwise; check. Move proofs and extra plots to an appendix or a supplementary file only if the venue allows it.

Details per section: [references/paper-structure.md](references/paper-structure.md), [references/abstract-and-introduction.md](references/abstract-and-introduction.md).

## 7. Design Patterns

- **Claim-evidence table**: a private table with columns claim, section, figure or table, strength of evidence. Every contribution bullet must appear in it; use it to find unsupported claims and orphan results.
- **Gap statement**: "Existing work X does A but not B, because of C. We address B by D." Three clauses, each checkable against the related-work section.
- **Problem-solution-result paragraph** for the introduction: one paragraph names the problem and its cost, one the limitation of current approaches, one the idea, one the result in numbers.
- **Related-work grouping**: group by approach (for example "model-based", "learning-based", "hybrid"), then write one paragraph per group: what they do, what they assume, where they fall short, how this paper differs. See [references/related-work.md](references/related-work.md).
- **Figure first**: draft the figure and its caption, then write the paragraph that interprets it. The paragraph says what to look at, what the trend is, and why it happens.
- **Result paragraph**: setup reminder, observation with numbers, explanation, caveat. Never leave a plot without a stated takeaway.
- **Limitations as scope**: state assumptions and the conditions under which the claim holds, then what was not tested. Put them in the paper, not only in the response letter.
- **Response letter block**: comment quoted in a distinct style, response in prose, change described with location and, where useful, the new text quoted. See [references/reviewer-response.md](references/reviewer-response.md).
- **Reverse outline**: after drafting, write one line per paragraph summarising its point; read the lines in order to test the logic and spot repetition.

## 8. Best Practices

- Write the title and abstract so that they are complete without the paper: they are what indexing services, reviewers and readers see first.
- Choose titles that name the object and the finding or approach ("Beam Tracking for Mobile mmWave Links Using Sparse Channel Priors"), avoid puns and question marks unless the venue style allows them, and keep acronyms rare and defined by common use.
- Keep a living glossary and notation file for the project from the first draft; it prevents drift between co-authors.
- Agree on authorship order, corresponding author and CRediT roles at the start of the project and revisit at submission. Record who wrote and who checked each section.
- Separate "what we did" from "what we found" from "what we think it means"; reviewers penalise interpretations presented as results.
- Report negative and null results that bear on the claim, and compare against strong, current and tuned baselines, with the baselines' settings stated.
- Give enough detail to repeat the work: parameters, data sources and splits, software versions, hardware, seeds, run counts. Use an artifact statement and a persistent identifier for released code or data.
- Share drafts early with someone outside the project and ask them to state the contribution back in one sentence; if it differs from yours, rewrite the introduction.
- Use version control for text when the team is technical, with one sentence per line or per paragraph for readable diffs (LaTeX specifics belong to latex-academic-expert).
- Keep all co-authors informed of submissions, revisions and responses; confirm that every author has approved the final version.

## 9. Reader Efficiency

- Put the contribution in the first page and the main result in the first two pages. Many reviewers decide the tone of a review from the abstract and introduction.
- Make figures legible at column width: fonts at least about the size of body text, line widths that survive reduction, and markers that are distinguishable in grayscale. See [references/figures-and-tables.md](references/figures-and-tables.md).
- Cut material that does not serve a claim: redundant plots, textbook derivations (cite instead), exhaustive parameter sweeps (summarise and move to an appendix).
- Replace long lists of numbers in text with a table, and long tables with a figure when the message is a trend.
- Use signposting sparingly: a closing paragraph that maps sections is useful in long papers, wasteful in 4-page letters.
- Keep reviewers' effort low in a revision: highlight or mark changes as the venue allows, and give locations in the response letter.
- Prefer a response letter that is as short as precision allows; long defensive answers are read as weakness.

## 10. Integrity and Ethics

- Do not fabricate, falsify or selectively omit data or references. Do not cite works you have not read; verify every reference exists and says what you claim.
- Plagiarism covers copied sentences, close paraphrase without citation, reused figures without permission and reused ideas without credit. Quote or rewrite and cite; obtain permission and a credit line for third-party figures.
- Self-plagiarism: reusing your own published text, figures or results without citation or permission. Cite the earlier paper, state the new contribution, and check the copyright agreement and the publisher's reuse policy. Extended journal versions of conference papers normally need substantial new content; check the target journal's stated threshold, and mention the conference version in the cover letter.
- Duplicate submission is not allowed: do not submit the same work to two venues at once. Preprints are usually allowed; check the venue policy, especially for double-blind review.
- Authorship should follow substantial contribution, drafting or revising, approval and accountability, as the venue defines it (check the IEEE and ACM authorship policies). No gift or ghost authors. AI tools are not authors.
- Generative AI: follow the venue's current rule. IEEE per secondary summaries asks for disclosure in the acknowledgments of AI-generated text, figures, images or code, naming the system and the sections concerned, with grammar and editing help treated more leniently. The ACM disclosure language for writing assistance has changed between versions. Read the policy page of the target venue and the year of the call, and follow it. Never place unpublished manuscripts under review into a public AI service; IEEE reviewer guidance forbids it.
- Disclose conflicts of interest, funding, human-subject or data-ethics approvals, and licences of datasets used.
- Confidential review material (manuscripts, reviews) stays confidential. Do not reuse ideas from papers you review.
- Anonymous submissions: remove names, affiliations, acknowledgments with identifying text, self-citations written in the first person ("our previous work") and repository links that reveal identity; use anonymised artifact links if the venue allows.

## 11. Draft Checks

- Claim-evidence audit: for each sentence in the abstract and each contribution bullet, find the figure, table or proof that supports it.
- Abstract test: delete numbers and names; if the abstract could describe five other papers, add specifics.
- Reverse outline: one line per paragraph; mark paragraphs that repeat or that nobody needs.
- Notation audit: list every symbol with its first use and definition; search the text for symbols used without definition and for two symbols with one meaning.
- Abbreviation audit: list every acronym; check first-use definition and consistent capitalisation.
- Cross-reference audit: every "Fig. N", "Table N", "Section N" and "Eq. (N)" points to an existing item that says what the sentence claims.
- Citation audit: every claim citation is verified, every reference is cited in the text, no unresolved placeholders, no duplicate entries (BibTeX mechanics: latex-academic-expert).
- Number audit: every number in text matches its table or figure; units and rounding are consistent.
- Read-aloud pass or text-to-speech pass for sentence length and rhythm; a colleague pass for clarity.
- Grayscale and zoom check: print the figures in grayscale at final size.
- Venue check: page count, template, anonymity, mandatory statements, supplementary rules.

## 12. Review Checklist

- [ ] The title names the subject and the approach or finding; no unexplained acronyms.
- [ ] The abstract has context, gap, method, result with a number, and implication, within the venue limit.
- [ ] The introduction ends with a contribution list whose items are verifiable and mapped to sections.
- [ ] Related work is grouped by approach and positions the paper against each group.
- [ ] The system model states assumptions and notation; each symbol is defined once.
- [ ] Every result is tied to a claim, and every claim to a result.
- [ ] Baselines are current, fairly configured and described.
- [ ] Limitations and threats to validity are written in the paper.
- [ ] Figures have standalone captions, labelled axes with units, readable fonts and colour-blind-safe encodings.
- [ ] Tables have units in headers, consistent precision and a stated best-result convention.
- [ ] Reproducibility details or an artifact statement are present.
- [ ] Authorship, CRediT or contribution statement, funding, conflicts and AI-use disclosure follow the venue policy.
- [ ] Overlap with earlier publications is cited and explained; no duplicate submission.
- [ ] Anonymisation is complete when the review is blind.
- [ ] Response letter (if any) answers every comment, with locations that match the final text.

## 13. Submission Notes

- Read the current author instructions the day you submit; templates and policies change between years and editions. Record the version or date of the policy page in the submission notes.
- Cover letter (journals): one page; the paper's title and type, the problem in one sentence, the contribution in two, why the venue fits, relation to earlier versions (conference papers, preprints, theses), suggested or excluded reviewers if the system allows, and the declarations the editor needs (originality, no concurrent submission, conflicts). Keep it factual, without praise of the work.
- Rebuttals with word limits: lead with the points that could change a score, answer the most serious concern first, quote the reviewer's claim in a few words, give new evidence as numbers, and do not promise experiments that cannot fit into the revision. Check whether the venue allows new results or links in the rebuttal and follow that rule exactly.
- Revision: submit a clean version and a marked version when the venue asks for both; respond to the editor's summary as well as to each reviewer; keep the tone neutral and thank reviewers once, briefly.
- Camera-ready: check names, affiliations, copyright or licence form, funding text, CRediT or contribution statement, acknowledgments, AI disclosure, artifact links, and reference formatting against the style manual of the publisher.
- Preprints: check the venue's policy, especially for double-blind conferences; update the preprint with the accepted version when the publisher's rules allow.
- Thesis: follow the university's regulations on included publications, co-author declarations and permissions; keep a table that maps chapters to papers and states your contribution to each.
- Keep the final submitted source, data and code snapshot (with a tag or archive identifier) for later questions from editors and readers.

## 14. Examples

Abstract, before and after (illustrative numbers):

```text
Before:
Beam management is important in 5G. In this paper we propose a novel
beam tracking method based on deep learning. Simulations show that our method
is very effective and outperforms state-of-the-art methods significantly.

After:
Maintaining beam alignment for mobile users in millimetre-wave networks
costs up to 20% of airtime in current beam-sweeping schemes. Learning-based
trackers cut this overhead but degrade when user speed or blockage statistics
differ from the training data. We propose a tracker that predicts the angle
of arrival from a short history of received power and falls back to a narrow
local sweep when its confidence drops. In system-level simulation with
speeds from 3 to 120 km/h, it keeps the median beam misalignment below 1
degree while using 4 times fewer reference signals than exhaustive sweeping
and 1.6 times fewer than a recurrent-network baseline. The fallback rule
keeps the outage rate within 0.5 percentage points of the baseline when
tested on blockage statistics not seen in training. The results indicate that
confidence-gated sweeping is a practical way to make learned beam tracking
robust to distribution shift.
```

The "after" version follows the order context, gap, method, result, implication, and replaces adjectives with quantities. If the figures are not yet measured, mark them as placeholders in the draft and fill them from the results.

Contribution list, before and after:

```text
Before:
Our contributions are: (1) a new framework for beam tracking; (2) extensive
experiments; (3) good performance.

After:
The contributions of this paper are:
- A beam tracker that predicts angle of arrival from received-power history
  and triggers a local sweep when predictive confidence falls below a
  threshold (Section IV).
- A closed-form bound on the misalignment probability as a function of
  speed and update interval, which sets the threshold (Section IV-C).
- An evaluation against exhaustive sweeping and a recurrent baseline at
  3 to 120 km/h and under unseen blockage statistics (Section V).
- Simulation code and configuration files, available at the link in the
  artifact statement.
```

Reviewer response, before and after:

```text
Reviewer comment 2.3: "The baseline comparison is unfair. The authors do not
tune the competing method."

Before:
We respect the reviewer's opinion but we believe the comparison is fair. We
used the default parameters of the original paper.

After:
We thank the reviewer for this point. Using the published defaults alone could
disadvantage the baseline, so we tuned its learning rate, window length and
hidden size on the same validation set used for our method (grid of 36
configurations, listed in the new Table III). The tuned baseline improves by
8% in misalignment but remains 1.6 times more expensive in reference signals;
Fig. 6 and the first paragraph of Section V-B are updated accordingly.
```

The "after" response accepts the valid part of the concern, takes an action, reports the result and gives locations. Invented numbers above are for illustration only.

Declining a request politely:

```text
Reviewer comment 1.4: "Please validate on a real testbed."

Response:
We agree that a testbed would add confidence. A mmWave testbed with user
mobility up to 120 km/h is not available to us within the revision period.
We therefore added the measured-trace evaluation in Section V-D, which
replays channel recordings from [12] at the speeds in question, and we
state the absence of over-the-air validation in Section VI (Limitations).
```

## 15. Common Mistakes

- **Abstract that announces instead of reporting** ("we propose a method and evaluate it"): state the result and its size.
- **Contribution list that restates sections** ("Section 2 presents..."): list claims, not the table of contents.
- **Related work as an annotated bibliography**: group by approach and say how the paper differs; a list of paraphrased abstracts is not positioning.
- **Overclaiming** ("first", "best", "solves"): rarely checkable; replace with the precise scope ("to our knowledge, the first to evaluate X under Y", only after a documented search).
- **Weak baselines or untuned baselines**: reviewers find this quickly; tune baselines on the same budget and report settings.
- **Figures that do not stand alone**: a caption that says "Results" forces the reader to search the text; state what is plotted, the conditions and the takeaway.
- **Axes without units, or unreadable fonts after column reduction**: label quantity and unit; test at final size.
- **Colour as the only cue**: add markers or line styles and use a colour-blind-safe palette.
- **Notation drift**: the same quantity as `P`, `p` and `Pw` in different sections; keep a notation table and search for variants.
- **Undefined acronyms and symbols**: define at first use.
- **Results without interpretation**: say why the trend appears, not only that it does.
- **Limitations hidden or missing**: a reviewer will write them for you, less kindly.
- **Response letter that argues instead of acting**: change the paper, then say where.
- **Response letter pointers that are stale**: line or section references from an earlier draft; recheck against the final version.
- **Reusing earlier text without citation**: check overlap with the publisher's similarity report if it is available and rewrite.
- **Undisclosed AI assistance or unverified AI-suggested references**: follow the venue policy and check every reference against its source.
- **Author list changes at the last minute without consent**: confirm with all authors in writing.

## 16. References

- [references/paper-structure.md](references/paper-structure.md): section-by-section blueprint for conference, journal, letter and thesis formats, method and system-model writing, results and discussion, limitations, conclusion.
- [references/abstract-and-introduction.md](references/abstract-and-introduction.md): titles, abstract formula, introduction moves, contribution lists, with before and after rewrites.
- [references/related-work.md](references/related-work.md): grouping, positioning, comparison tables, citing, and avoiding unfair characterisations.
- [references/figures-and-tables.md](references/figures-and-tables.md): captions, axes, palettes, table design, notation and symbol consistency, reproducibility and artifact statements.
- [references/reviewer-response.md](references/reviewer-response.md): response letters, rebuttals with word limits, cover letters, tone, tracking changes, plus authorship, CRediT, AI-use and overlap policies.
- CRediT taxonomy: https://credit.niso.org/ (ANSI/NISO Z39.104-2022)
- IEEE Author Center, including the Editorial Style Manual and publishing-ethics policies: https://journals.ieeeauthorcenter.ieee.org/
- ACM publications policies, including authorship and generative AI: https://www.acm.org/publications/policies
- COPE guidance on authorship and publication ethics: https://publicationethics.org/
