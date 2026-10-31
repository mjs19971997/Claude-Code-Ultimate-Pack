# Reviewer Responses, Cover Letters and Publication Policies

Writing response letters and rebuttals, cover letters and revision packages, plus the policy topics around submission: authorship and CRediT, plagiarism and self-plagiarism, and publisher rules on AI use. Policy statements here are summaries; pages change, so read the current text of the venue and cite only what you have checked.

## Contents

1. [Reading the reviews](#1-reading-the-reviews)
2. [Response letter structure](#2-response-letter-structure)
3. [Tone and wording](#3-tone-and-wording)
4. [Response examples](#4-response-examples)
5. [Rebuttals with word limits](#5-rebuttals-with-word-limits)
6. [Tracking changes](#6-tracking-changes)
7. [Cover letters](#7-cover-letters)
8. [Authorship and CRediT](#8-authorship-and-credit)
9. [Plagiarism, self-plagiarism and overlap](#9-plagiarism-self-plagiarism-and-overlap)
10. [AI-use policies](#10-ai-use-policies)
11. [Checks](#11-checks)

## 1. Reading the reviews

- Read the editor's summary first: it states what must be done for acceptance.
- Split each review into atomic comments and number them (R1.1, R1.2, R2.1 ...). Comments with several points become several items.
- Classify each item: factual error in the review, misunderstanding (the paper was unclear), valid request for change, request for new work, request outside scope, minor edit.
- A misunderstanding is a writing problem: fix the text so the next reader does not make the same mistake.
- Group related comments across reviewers and respond consistently; cross-reference ("see our response to R1.3").
- Decide the action for each item before writing anything: change, clarify, add evidence, decline with reason.
- Prioritise: items that threaten the central claim first, then evidence gaps, then presentation.

## 2. Response letter structure

```text
Response to the Reviewers
Manuscript <ID>: <Title>

Summary of changes (editor and all reviewers): 5 to 10 bullets of the most
important changes with section references.

Reviewer 1
  R1.1  <comment quoted exactly>
  Response: <answer>
  Changes: <where the manuscript changed, with new text where useful>

  R1.2  ...

Reviewer 2
  ...

List of additional changes made by the authors (typos, updated references).
```

- Quote or reproduce every comment in full; do not paraphrase or merge so that the reviewer's concern is visible.
- Use a distinct typographic style for comments (italic, shaded or indented) and another for responses and new manuscript text.
- Give location pointers that survive editing: section and subsection numbers, figure and table numbers, and page and line numbers of the marked version when the venue's template provides them. Recheck all pointers against the final file.
- Quote the new or changed text in the letter when it is short; point to the location when it is long.
- Respond to every comment, including praise and trivial ones (a short "Thank you, corrected" suffices).
- Open with a short thanks (one or two sentences), not a paragraph for each reviewer.

## 3. Tone and wording

- Be factual, specific and courteous. The reviewer volunteered time and is the intended reader.
- Agree where the reviewer is right and say what you did. Disagree where you must, with evidence, and offer a change that addresses the underlying concern.
- Avoid: "The reviewer clearly did not read...", "As we already said...", "We respectfully disagree" without evidence, sarcasm and emotional language.
- Prefer: "We have clarified...", "We added ... (Section 5.2)", "We agree that ...; we therefore ...", "We were not able to ... because ...; instead ...".
- Blame the text, not the reader: "We see that Section 3 was unclear about X, and have rewritten it."
- Do not promise what you did not do. If a change is only in the response letter and not in the paper, say so and explain; reviewers check the manuscript.
- Keep each response as short as precision allows; add a table or a figure to the letter when it answers a point better than prose.

## 4. Response examples

Valid concern, new experiment:

```text
R2.4  "The evaluation uses a single channel model; generality is unclear."

Response: We agree that one channel model is insufficient to support the
claim of robustness. We added two further models (urban macro and indoor
hotspot, parameters in the new Table IV) and re-ran all experiments.

Changes: Section V-C and Fig. 7 present the new results. The proposed
tracker's advantage remains (misalignment below 1.2 degrees in both
models); the advantage is smaller in the indoor model, which we discuss in
Section VI.
```

Misunderstanding:

```text
R1.2  "It is unclear how the threshold is chosen."

Response: Thank you; this was not explained well. The threshold is derived
from the bound in Eq. (12) for a target misalignment probability and is not
tuned on test data. We moved the derivation from the appendix to Section IV-C
and added a worked example with the values used in the evaluation.
```

Disagreement with evidence:

```text
R3.1  "The comparison to scheme X is meaningless since X was designed for
static users."

Response: We agree that X was designed for static users, and we do not claim
it as a mobility-aware scheme. We include it because it is the scheme in
the current standard text and thus the reference a practitioner would use. To
avoid the impression of an unfair comparison, we split Table II into static
and mobile scenarios and note in Section V-A the design assumption of X.
```

## 5. Rebuttals with word limits

Rebuttals (single round, strict limit, often within days) differ from revision letters.

- Read the rules: word or character limit, whether new results, links or figures are allowed, whether the reviewers are expected to change scores, and what the meta-review will use.
- Lead with the one to three points that decide the outcome; address them first, even if a reviewer listed them last.
- Use compact numbering and a fixed pattern: "R1-Q2 (baseline tuning): ..." followed by the answer.
- Give evidence as numbers or a precise pointer to the manuscript; "we will add" is weaker than "Table 3 already shows" but acceptable when the venue allows changes in the camera-ready, and you are specific about the change.
- Do not promise experiments that cannot be done in the camera-ready time frame.
- Merge answers to the same concern raised by several reviewers.
- Be brief on minor points: "Will fix typos and update Fig. 3 labels."

## 6. Tracking changes

- Keep the submitted version as a baseline; produce the marked version by a diff tool, a change-tracking feature or a LaTeX diff process (tooling: latex-academic-expert), then a clean version.
- Check that the marked version contains all substantive edits and that pointers in the letter correspond to the numbers in the clean version, or state which version the numbers refer to.
- Highlight new text in a colour only if the venue allows; follow the venue's format for the revision package (letter, marked file, clean file, supplementary file).
- Keep a change log during revision: one line per change with the comment it answers. It becomes the "Changes" lines in the letter.
- Update the abstract, the introduction's contribution list and the conclusion when the content of the paper changes.
- Update the reference list, figure numbers and cross-references after inserting new figures or tables.
- Re-run the draft checks (notation, abbreviations, numbers) after a major revision.

## 7. Cover letters

Initial submission (journal):

```text
Dear Editor,

Please consider the enclosed manuscript, "<Title>", for publication in
<Journal> as a <regular paper / letter>.

<Sentence on the problem.> <Sentence on what the paper does and the main
result.> <Sentence on why the venue's readers care.>

A preliminary version appeared at <Conference, year> [ref]. The present
paper adds <new analysis, experiments, proofs>, about <percentage or
description> new material. A comparison of the two versions is attached.

The manuscript is original, is not under consideration elsewhere, and all
authors approved the submission. Declarations of competing interests,
funding and data availability are in the manuscript. We suggest the
following reviewers: ... We ask that ... be excluded because ...

Sincerely,
<Corresponding author, on behalf of all authors>
```

- Keep to one page. Do not repeat the abstract; explain relevance and relation to earlier work.
- Always declare related earlier publications and preprints.
- Suggest reviewers only if the system asks, give their affiliation and a reason, and avoid anyone with a conflict of interest.

Resubmission or revision cover note: reference the manuscript number, summarise the main changes in three lines, state that the full response letter is attached, and list any point on which the authors disagree and the action taken.

Resubmission after rejection elsewhere: do not mention the other venue's reviews unless the new venue asks; address the substance of the earlier reviews in the paper.

## 8. Authorship and CRediT

- Authorship criteria are set by the publisher and the community; typical elements are a substantial contribution to the work, drafting or critically revising it, approving the final version and accepting accountability. Read the criteria of the target publisher (IEEE and ACM publish theirs) and of your institution.
- Agree authorship and order early and in writing; revisit at submission. Authors who left the project still receive the draft and may approve or decline.
- No guest, gift or ghost authors. Contributors who do not meet the criteria belong in the acknowledgments, with their permission.
- Tools that generate text or code cannot be authors under IEEE and ACM policies as summarised in secondary sources; the human authors are accountable. Confirm on the current policy pages.
- The CRediT taxonomy (ANSI/NISO Z39.104-2022) has 14 roles; optional degree qualifiers (lead, equal, supporting) exist in the standard:
  1. Conceptualization
  2. Data curation
  3. Formal analysis
  4. Funding acquisition
  5. Investigation
  6. Methodology
  7. Project administration
  8. Resources
  9. Software
  10. Supervision
  11. Validation
  12. Visualization
  13. Writing - original draft
  14. Writing - review and editing
- Typical author contribution statement (use the venue's format if specified):

```text
Author contributions (CRediT): A. Author: Conceptualization, Methodology,
Software, Writing - original draft. B. Author: Formal analysis, Validation,
Writing - review and editing. C. Author: Supervision, Funding acquisition,
Project administration, Writing - review and editing.
```

- Every author appears with at least one role; every role relevant to the work is assigned to someone. The roles describe what was done, not seniority.
- Corresponding author: handles correspondence and keeps co-authors informed through review. Equal-contribution notes and ORCID iDs follow the venue's format.
- Changes in the author list after submission need the written consent of all authors and the editor's approval under most policies.

## 9. Plagiarism, self-plagiarism and overlap

- Plagiarism: using others' words, ideas, data or figures without credit. Paraphrase that follows the structure and wording of the source is still plagiarism; cite, quote or write independently from understanding.
- Self-plagiarism or text recycling: reusing your own published text, figures or results without citation or permission. Background and standard definitions may overlap lightly if cited; methods text identical to an earlier paper is a common trigger for similarity reports.
- Publishers check manuscripts with similarity software (for example iThenticate or Crossref Similarity Check at many publishers); high overlap with your own thesis or earlier paper needs explanation in the cover letter.
- Conference-to-journal extensions: add substantial new content, cite the conference paper, and list the differences. Check the target journal's guidelines for the required amount of new material; thresholds vary by publisher and journal.
- Thesis to paper: theses are usually not counted as prior publication, but check the venue and the university repository's embargo and licence.
- Preprints: allowed by most venues but check anonymity rules for double-blind review and the policy on updating the preprint after acceptance.
- Figures and tables from earlier work: obtain written permission from the copyright holder (publisher reuse tools often grant it for authors' own work), credit the source in the caption.
- Redundant publication (salami slicing the same data into several minimal papers) is an integrity problem; combine or clearly distinguish them.
- COPE's guidance describes how editors treat suspected plagiarism and duplicate publication; consult it if an editor raises a concern.

## 10. AI-use policies

Facts at the time of writing, from secondary summaries; the primary pages could not be fetched when this skill was written, so confirm each on the current publisher page:

- IEEE: AI tools cannot be authors; authors are accountable for the content. Use of AI to generate content (text, figures, images, code) is to be disclosed in the acknowledgments section, identifying the system and the affected sections and the extent of use. Language and grammar edits of human-written text are described as generally outside the disclosure requirement, with disclosure recommended. Reviewers must not upload manuscripts under review to public AI platforms.
- ACM: AI tools cannot be listed as authors; authors are responsible for the accuracy of all material. The wording on disclosure of AI used for writing assistance has varied between versions and venue pages (older text asked for disclosure in the acknowledgments; some newer venue pages state that writing assistance no longer requires disclosure, while use of AI to conduct the research still does). Read the current ACM policy and the specific venue's page.
- Other publishers and conferences have their own rules, sometimes stricter (for example for figures and for peer review). The call for papers of the specific year governs.

Practice:

- Decide a project policy at the start: what tools are used for what, and record it (tool name and version, date, purpose, sections touched).
- Never place confidential material (unpublished manuscripts from peer review, restricted data) into an external service without permission.
- Verify every statement, equation, number, reference and line of code that a tool produced or modified. Tools can invent references that look real; check each in the original source.
- Do not present tool output as your own analysis of data you did not examine.
- Draft the disclosure sentence early and adapt to the venue:

```text
Disclosure: <tool name and version> was used to <purpose, e.g. propose
rephrasing of the Introduction (Section I) and to draft the plotting scripts
for Figs. 4 and 5>. The authors reviewed and edited all output and take full
responsibility for the content.
```

- When the venue offers no rule, ask the editor or program chairs; keep the answer.

## 11. Checks

- Every reviewer comment appears in the letter and has a response with an action.
- Every location pointer matches the final clean version.
- The abstract, contribution list and conclusion reflect the revised content.
- New claims have new evidence; removed claims are removed everywhere.
- The tone is neutral; a colleague who is not an author read the draft letter.
- The author list, CRediT statement, funding, conflicts and AI-use disclosure are current.
- Overlap with earlier papers is cited and explained; reused figures have permission.
- The package matches the venue's required files and the deadline.
