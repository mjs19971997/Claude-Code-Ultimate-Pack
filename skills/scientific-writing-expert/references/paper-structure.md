# Paper Structure

Section-by-section blueprint for engineering, computer science and telecom papers: how long each part is, what it must contain, and the tests that show whether it works. Lengths are typical, not rules; the venue's template and page limit decide.

## Contents

1. [Choosing a format](#1-choosing-a-format)
2. [Planning from the claim](#2-planning-from-the-claim)
3. [System model and problem formulation](#3-system-model-and-problem-formulation)
4. [Method section](#4-method-section)
5. [Evaluation](#5-evaluation)
6. [Discussion, limitations and threats to validity](#6-discussion-limitations-and-threats-to-validity)
7. [Conclusion](#7-conclusion)
8. [Thesis chapters](#8-thesis-chapters)
9. [Section length guide](#9-section-length-guide)

## 1. Choosing a format

| Format | Typical length | Structure emphasis |
|---|---|---|
| Letter or short paper | 4 to 6 pages | One idea, one main figure, compressed related work, no separate limitations section if space is tight (put one sentence in the conclusion) |
| Conference paper | 6 to 14 pages, venue dependent | Contribution list, strong evaluation, related work grouped and short |
| Journal article | 10 to 15 pages or more | Full derivations, ablations, extended related work, discussion, limitations |
| Survey or tutorial | Venue dependent | Taxonomy first, comparison tables, open problems; the organising scheme is the contribution |
| Workshop paper | 2 to 6 pages | Position or early result; state clearly what is preliminary |
| Extended version of a conference paper | Journal length | Substantial new content (new analysis, experiments, proofs); check the journal's stated threshold and cite the earlier paper |

- Read two or three accepted papers from the exact venue and match their section order and depth.
- When page limits bind, cut in this order: repeated figures, secondary sweeps, textbook derivations, then related work detail. Do not cut limitations or reproducibility details.

## 2. Planning from the claim

Write these five lines before drafting; they feed the title, abstract and introduction later.

```text
Problem:      who has what problem, and what does it cost
Gap:          why existing approaches fall short (one reason each)
Idea:         the technique in one sentence
Evidence:     the experiment or proof that supports the idea
Consequence:  what a reader can do or believe afterwards
```

- Then list sections with a one-sentence job each: "Section 4 shows the tracker and the bound that sets its threshold." If a section's job cannot be stated in one sentence, split it.
- Map figures: one figure per message. If two figures carry the same message, keep the clearer one.
- Draft the figures and tables first; the text explains them.

## 3. System model and problem formulation

- Open with a short paragraph describing the setting in words and a pointer to a diagram if the system has parts.
- State assumptions explicitly, each in its own sentence or bullet, and say which are used for analysis only and which for the simulator.
- Define notation at first use and collect symbols in a table when there are many. Keep a stable convention (for example scalars italic, vectors bold lowercase, matrices bold uppercase, sets calligraphic).
- Separate the model (what is given) from the problem (what is optimised or proved). The problem statement names the objective, the variables, the constraints and the performance metric.
- Justify the model against reality in one or two sentences: where it matches practice, where it simplifies. This pre-empts the usual reviewer objection.
- Telecom-specific: give the carrier frequency, bandwidth, antenna configuration, channel model name and version and any standard that defines a quantity, using terms as the standard does (5g-nr-3gpp-expert for 3GPP terminology; ns3-expert for simulator configuration).

## 4. Method section

- Start with an overview: a block diagram or algorithm outline and a paragraph walking through it. Then detail each block in the order of the diagram.
- Present algorithms as numbered pseudocode with inputs, outputs and a complexity statement; describe in prose the intuition behind the non-obvious lines.
- Give design rationale ("we use X because Y"), not only design description. Reviewers look for the reason behind each choice.
- State properties you can prove (convergence, bound, complexity) with the assumptions that they need; give the proof sketch in the body and the full proof in the appendix.
- State hyperparameters, defaults and how they were selected (on which data, with what budget).
- Mark what is existing work and what is new: "Step 2 follows [14]; Steps 3 and 4 are new."
- Do not mix description and evaluation in the method section; results belong in the evaluation.

## 5. Evaluation

Order of content:

1. Research questions or claims being tested, one line each.
2. Setup: platform or simulator and version, scenario parameters (table), datasets and splits, metrics with definitions, baselines with their configuration and source, number of runs or seeds, hardware.
3. Main results: one subsection per question, each with a figure or table, the observation with numbers, the explanation and the caveat.
4. Ablations: remove or replace each component to show it matters.
5. Sensitivity and robustness: parameters, distribution shift, scale.
6. Cost: runtime, memory, signalling overhead, energy, whichever the claim depends on.

Rules:

- Every figure and table is referenced in the text and interpreted in the text.
- Compare with the strongest relevant baselines, including simple ones (a naive or classical method often explains how much the new method adds).
- Report variability (error bars or intervals) and state what they represent; the statistical treatment belongs to statistics-expert.
- Say what each result means for the claim: "supports", "partly supports", "does not support".
- Report unfavourable results in the main text if they bear on the claim.

## 6. Discussion, limitations and threats to validity

- Discussion: interpret across results (why the method works here and not there), connect to the introduction's problem, and describe practical consequences.
- Limitations: write them as scope conditions, concretely. Example: "The bound assumes block fading and perfect timing; with timing offsets above X, the fallback triggers more often (Fig. 9)." Avoid vague statements such as "future work may improve generality".
- Threats to validity, in empirical and systems papers, grouped by type:
  - Internal: bugs, tuning budget differences between methods, leakage between training and test data.
  - External: how far the scenarios, datasets or hardware generalise.
  - Construct: whether the metric measures the property claimed.
  - Conclusion: sample size, run count, variance.
- For each threat, state what you did to mitigate it or why it remains.
- Put limitations in a labelled section or subsection so reviewers can find them; hiding them in a paragraph of the conclusion looks defensive.

## 7. Conclusion

- Three to five sentences of summary of what was shown, with the key number; do not repeat the abstract verbatim.
- One sentence on implications for practice or theory.
- Future work: two or three concrete items that follow from the limitations, not a wish list.
- No new results, no new citations of substance, no new claims.
- Journals sometimes allow a longer conclusion with a short discussion; follow the venue pattern.

## 8. Thesis chapters

- Thesis structure: introduction (problem, research questions, contributions, thesis outline), background, one chapter per main contribution, discussion and conclusion, appendices.
- Each content chapter: opening paragraph with motivation and what the chapter answers, the body in paper-like structure, closing summary that states the finding and the link to the next chapter.
- Papers reused as chapters need rewriting for narrative continuity; unify notation and terminology across chapters and remove repeated background.
- Declare publications included in the thesis and your contribution to each co-authored one, following the university's rules; check the copyright agreement or licence for reuse rights.
- Write a single glossary and list of symbols for the whole thesis.
- The introduction states research questions; the conclusion answers them one by one, with a pointer to the chapter and evidence.
- Keep a mapping table: research question, chapter, publication, key result.

## 9. Section length guide

Approximate share of a 10-page two-column conference paper (a planning aid only):

| Section | Share | Notes |
|---|---|---|
| Abstract | 0.2 page | 150 to 250 words |
| Introduction | 1.0 to 1.5 pages | Includes contributions |
| Related work | 0.75 to 1.0 page | Grouped |
| System model | 1.0 to 1.5 pages | Notation and assumptions |
| Method | 2.0 to 3.0 pages | Algorithm, analysis |
| Evaluation | 3.0 to 4.0 pages | Setup, results, ablations |
| Limitations and conclusion | 0.5 to 0.75 page | |
| References | 1.0 to 1.5 pages | May count toward the limit |

- Revisit the shares after the first full draft; a method section that is much longer than the evaluation usually means the evidence is thin.
