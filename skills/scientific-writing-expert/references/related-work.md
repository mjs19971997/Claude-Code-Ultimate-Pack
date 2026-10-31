# Related Work

How to write a related-work section that positions the paper rather than listing papers: finding the grouping, writing the contrast, using a comparison table, citing responsibly and handling surveys, concurrent work and your own earlier papers.

## Contents

1. [Purpose](#1-purpose)
2. [Choosing the grouping](#2-choosing-the-grouping)
3. [Paragraph pattern](#3-paragraph-pattern)
4. [Comparison tables](#4-comparison-tables)
5. [Before and after](#5-before-and-after)
6. [Citation practice](#6-citation-practice)
7. [Special cases](#7-special-cases)
8. [Length and placement](#8-length-and-placement)
9. [Checks](#9-checks)

## 1. Purpose

- Show that the problem is real and not solved, by describing what each family of approaches does and assumes.
- Place the paper in the field so a reviewer can see what is new relative to the closest work.
- Credit prior work accurately, including the work that the paper builds on.
- Do not use the section to prove that you read many papers. Cite what a reviewer would expect and what you must contrast with.

## 2. Choosing the grouping

Group by approach, assumption or problem variant, not by year, author or venue.

| Grouping axis | Example groups |
|---|---|
| Technique | Model-based, data-driven, hybrid |
| Assumption | Perfect channel knowledge, estimated channel, blind |
| Objective | Throughput, latency, energy, fairness |
| Setting | Single cell, multi cell, mobile users, static users |
| Architecture | Centralised, distributed, hierarchical |

- Test the grouping: each paper fits in one main group, and the groups differ in a way that matters for your gap.
- Order groups from the furthest from your work to the closest, so the last paragraph leads into the contrast with your own approach. Alternatively, order by the logical development of the field.
- Two to five groups is typical for a conference paper. More groups means the grouping axis is too fine.
- Give each group a lead-in sentence that names the group and the shared idea.

## 3. Paragraph pattern

One paragraph per group, four moves:

1. **What**: the shared idea of the group, with two to five representative citations.
2. **How**: the key mechanism or assumption, in one sentence.
3. **Limit**: what the group cannot do for the problem addressed here, with a reason.
4. **Contrast**: how this paper differs. Make this sentence specific and checkable.

Template:

```text
Learning-based trackers predict the next beam from past measurements
[5]-[8]. They reduce sweeping overhead when user motion matches the
training data, but [6] and [8] report degraded accuracy under unseen
mobility patterns, and none provides a fallback. We keep the predictive
step but add a confidence test that triggers a local sweep (Section 4).
```

- Use verbs that describe the work neutrally: "assume", "propose", "report", "evaluate". Avoid "fail to", "ignore" or "naively" for others' work.
- Use the authors' own results where they exist ("[6] reports 15% drop"), not your inference, and mark inference as inference.
- Cite the closest work in detail: give the difference in assumption, method and result, with the reason your approach is not the same.

## 4. Comparison tables

A table is useful when many works are compared on a few criteria.

| Work | Mobility | Needs training data | Fallback | Overhead reduction | Open code |
|---|---|---|---|---|---|
| [5] | Low | Yes | No | 3x | No |
| [6] | High | Yes | No | 4x | Yes |
| [7] | Low | No | Not applicable | 1.5x | No |
| This paper | High | Yes | Yes | 4x | Yes |

Rules:

- Criteria are objective and checkable from the cited papers. Subjective ratings (good, poor) draw objections.
- Include criteria on which your work does not win; omission is noticed.
- Footnote or caption the source of each entry if it comes from reading, not from a reported number.
- Keep the table to 5 to 10 rows and 4 to 7 columns. Put an extended table in an appendix or supplementary file.
- Introduce the table with a sentence stating the conclusion you want the reader to draw from it.

## 5. Before and after

```text
Before:
Smith et al. [1] proposed a scheduler for edge computing. Lee et al. [2]
studied the use of reinforcement learning for resource allocation. Wang et
al. [3] designed a distributed algorithm for task offloading. Kim et al.
[4] presented a survey of edge computing. Our work is different from these
works.

After:
Edge schedulers differ mainly in where placement decisions are made.
Centralised schedulers [1], [2] compute near-optimal placements from global
state, but the state collection time grows with cluster size and exceeds
tens of milliseconds at the scale we study. Fully distributed schedulers
[3], [5] avoid collection and decide from local information, but their
imbalance grows when load changes quickly and none bounds it. Hybrid designs
[6] combine both; the closest to ours uses periodic global rebalancing, but
it samples all nodes, whereas we show that a bounded sample suffices
(Section 4.3). For a broader view of edge computing we refer to the survey
[4].
```

What changed: grouped by the decision-making axis, the weakness of each group is stated with a reason, the closest work is contrasted in terms of one design choice, and the survey is cited as a pointer rather than summarised.

## 6. Citation practice

- Cite primary sources. Cite a survey for background but not for a specific technical result.
- Prefer the archival version over the preprint when the content is identical; cite a preprint when the result is only there, and note its status.
- Read every cited work you characterise. If you could not read it, do not describe its content beyond its abstract; say what is reported.
- Self-citation is legitimate where the earlier work is relevant; excessive or irrelevant self-citation is noticed by reviewers and editors. Cite the earlier paper from which any text, figure or result is reused.
- Recent work matters: check the last two to three years of the target venue and of the main journals in the area before submission.
- For double-blind venues, cite your own work in the third person ("Smith et al. [4] show...") and not as "our previous work [4]", unless the venue says otherwise.
- Cite standards and specifications with their number, version or release and date, using the terms of the document (3GPP release naming: 5g-nr-3gpp-expert). Reference-list formatting and BibTeX mechanics: latex-academic-expert.
- Do not cite works only because a reviewer in the past asked; cite them when they help the reader.

## 7. Special cases

- **Concurrent or very recent work**: acknowledge it and state the difference or the overlap honestly. Place it in the related-work section or a footnote according to venue norms. Do not claim "first" in the face of it.
- **Surveys**: the taxonomy is the contribution. Describe the selection method (databases, years, inclusion criteria, number of works screened and included) and give a table of the surveyed works.
- **Interdisciplinary papers**: add a short orientation per field for the other field's readers, not a textbook.
- **Standards-based work**: related work includes the standard's approach as the baseline and the contributions to standards bodies where relevant; distinguish the standard's normative content from academic proposals.
- **Your own earlier paper on the same topic**: describe it as a group of one, state the new contribution and the overlap in a sentence, and mention it in the cover letter.
- **Negative or contradictory results from others**: report them fairly and explain why your setting differs.
- **Theses**: related work may be a full chapter; keep the grouping, and add a final synthesis that states the open problems that motivate the thesis.

## 8. Length and placement

- Letters: two to five sentences in the introduction or one short paragraph.
- Conference papers: 0.5 to 1 page, after the introduction or just before the conclusion.
- Journals: 1 to 2 pages; may be split into background (what the reader needs) and related work (what you contrast with).
- Place related work after the introduction when the contrast helps motivate the method; place it late when the method must be understood first. Say so in the outline sentence if you place it late.
- Move deep technical comparisons into the evaluation (as baselines) rather than the related-work section.

## 9. Checks

- Does each paragraph end with how this work differs? If the last sentence only restates the group, add the contrast.
- Could a reader name the closest prior work and the precise difference after reading the section?
- Are all baselines in the evaluation discussed here?
- Is every characterisation of another paper traceable to that paper's text?
- Are descriptions neutral enough that the cited authors would accept them?
- Is any citation present only to show off breadth? Remove it.
- Are there claims of novelty? Each needs a documented search behind it (databases, queries, dates); keep the search log.
- Have the closest recent papers (past 12 to 24 months) been checked, including preprints?
