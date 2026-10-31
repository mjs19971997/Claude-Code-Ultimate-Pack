# Titles, Abstracts and Introductions

How to write the parts of a paper that are read first and decide the reviewer's frame: the title, the abstract and the introduction with its contribution list. Includes before and after rewrites. Numbers in examples are illustrative.

## Contents

1. [Titles](#1-titles)
2. [Abstract structure](#2-abstract-structure)
3. [Abstract rewrites](#3-abstract-rewrites)
4. [Introduction moves](#4-introduction-moves)
5. [Contribution lists](#5-contribution-lists)
6. [Introduction rewrite](#6-introduction-rewrite)
7. [Keywords and highlights](#7-keywords-and-highlights)
8. [Checks](#8-checks)

## 1. Titles

- Name the object and the approach or finding; 10 to 16 words is typical. The title is searchable text: put the main terms first.
- Avoid: "A Novel Approach to...", "Towards...", "On the...", "An Improved..." without a subject; pun titles; abbreviations the audience does not know.
- Include a colon subtitle only when it adds a distinct piece of information (scope, setting or method).
- Do not claim a result in the title that the paper cannot defend ("Solving", "Optimal") unless a proof exists.

Before and after:

```text
Before:  A Novel Deep Learning Approach for 5G Beam Management
After:   Confidence-Gated Beam Tracking for Mobile Millimetre-Wave Links
```

- Check the title against the abstract: every important noun in the title should appear in the abstract.
- Short titles for letters; descriptive titles for journals. Follow the venue's limit on characters or words if one exists.

## 2. Abstract structure

A single paragraph of about 150 to 250 words (follow the venue limit) with five moves, one to two sentences each:

| Move | Question answered | Test |
|---|---|---|
| Context | What field and problem, and why does it matter | Understandable to a reader outside the sub-field |
| Gap | What current approaches cannot do | Names a concrete limitation, not "has limitations" |
| Method | What this paper does | A verb and an object; the key idea, not the whole pipeline |
| Result | What was found, with a number and a comparison | Contains at least one quantity and its baseline |
| Implication | What follows for practice or research | One sentence, not hype |

Rules:

- No citations, no references to figures, no undefined acronyms (define at first use, even if defined again in the body).
- Past tense for what was done and found, present for what the paper presents or what is generally true.
- Use the terms that appear in the paper's headings and keywords.
- Theory papers: replace "result" by the theorem or bound stated in words with its conditions.
- Survey papers: state scope, taxonomy, number of works covered with the selection method, and main conclusions.
- Structured abstracts (Background, Objective, Methods, Results, Conclusions) apply where the venue requires them.
- The abstract must agree with the paper: every claim in it appears in the body with evidence.

## 3. Abstract rewrites

Theory or analysis paper:

```text
Before:
We study the performance of uplink NOMA. A closed-form expression is
derived. Numerical results verify the analysis.

After:
Non-orthogonal multiple access (NOMA) is proposed to raise spectral
efficiency in dense uplink deployments, but existing outage analyses assume
perfect successive interference cancellation (SIC). We derive a closed-form
outage probability for two-user uplink NOMA with imperfect SIC under
Rayleigh fading, parameterised by the residual-interference factor. The
expression matches Monte Carlo simulation within 2% relative error for
residual factors up to 0.2 and shows that the diversity order drops from 2
to 1 once the factor exceeds zero. This implies that SIC quality, not
transmit power, limits reliability at high signal-to-noise ratio, and gives
a direct rule for choosing the receiver precision.
```

Systems paper:

```text
Before:
We present a new scheduler for edge clusters. It is fast and scalable. We
implemented it and tested it on a testbed.

After:
Edge clusters must place latency-critical tasks within tens of milliseconds,
yet centrally computed placements take longer than that at hundreds of nodes.
We present a scheduler that decides locally from a bounded sample of
neighbour load reports and corrects drift with a periodic global pass. On a
200-node testbed with a replayed production trace, the 99th-percentile
placement latency is 12 ms versus 85 ms for a central baseline, with at most
3% more deadline misses. The design shows that sampled local decisions are
sufficient for placement when a slow global pass bounds the imbalance.
```

What changed: the first sentences state the problem with a cost; the method sentence names the mechanism; results carry baselines; the final sentence says what the result means.

## 4. Introduction moves

An introduction of one to one and a half pages usually has these moves, each a paragraph:

1. **Context and importance**: the setting and why it matters, in terms of users, cost or capability. Avoid opening with a generic claim about the whole field ("In recent years, wireless has grown rapidly").
2. **Problem and gap**: the specific problem, what existing approaches do, and why they fall short. Cite 3 to 6 key works; leave the full survey to the related-work section.
3. **Idea**: the proposed approach in plain language and why it should work.
4. **Results preview**: the main quantitative finding with its comparison.
5. **Contributions**: the list (section 5).
6. **Outline** (optional): one paragraph mapping the sections; omit in short papers.

- Keep background proportional: one paragraph, then the problem. Readers of the venue know the basics.
- Say early what is not in scope, if readers could expect it.
- Motivate with evidence: a measurement, a standard requirement, a cited figure, or a small example that shows the failure.
- Use a running example only if later sections refer to it.

## 5. Contribution lists

Each bullet is a claim a reviewer can check, with a verb, an object, and a pointer:

- Good verbs: derive, prove, design, implement, measure, show, release, characterise, compare.
- Weak verbs: propose a framework, study, investigate, explore (unless the study is the contribution).
- Each bullet maps to a section and evidence. Two to four bullets; five or more suggests the paper lacks focus or that engineering steps are listed as contributions.
- Do not list "extensive experiments" or "good performance"; list what the experiments show.
- Mark novelty precisely ("first closed-form for X under Y") only after a documented literature search.

Before and after:

```text
Before:
The main contributions of this paper are:
1. We propose a novel framework.
2. We conduct extensive simulations.
3. Our method outperforms existing methods.

After:
This paper makes three contributions.
1. Design. A scheduler that places tasks from sampled neighbour load and
   corrects drift with a periodic global pass (Section 4).
2. Analysis. A bound on the load imbalance as a function of sample size and
   pass period, used to choose both parameters (Section 4.3).
3. Evaluation. A 200-node testbed study with a replayed production trace
   showing 12 ms p99 placement latency against 85 ms for a central scheduler
   (Section 5), with code and trace-conversion scripts released.
```

## 6. Introduction rewrite

```text
Before:
Wireless networks are becoming more and more important. Many researchers have
studied scheduling. In this paper we propose a new scheduler. Our scheduler
is efficient. The paper is organised as follows...

After:
Latency-critical applications such as industrial control and AR offloading
need task placement decisions within tens of milliseconds [1], [2]. Central
schedulers that collect global state cannot meet this at hundreds of nodes
because state collection alone takes longer than the budget (Section 5.2
quantifies this on our testbed). Decentralised schedulers avoid collection
but drift into imbalance when load changes faster than their information
[3], [4].

We observe that a bounded random sample of neighbour load reports is enough
to place tasks well when a slow global pass bounds the long-term imbalance.
Based on this, we design ...
```

- The "after" version opens with the requirement and its source, names the failure of each existing family, and sets up the idea.
- Check that each citation supports the sentence it follows.

## 7. Keywords and highlights

- Keywords: 4 to 8 terms, standard vocabulary of the field (for IEEE venues, the IEEE Taxonomy or the society's keyword list if the venue asks; check the call). Include the problem, the method class and the setting. Avoid keywords that only repeat the title's rare words.
- Highlights or graphical abstract (some journals): three to five short bullets of results, not methods; each must be defensible from the paper.
- Plain-language summary (where required): no jargon, no acronyms, state what the work enables and what is not yet shown.

## 8. Checks

- Give the abstract to a colleague outside the project; ask for a one-sentence restatement of the contribution.
- Remove adjectives from the abstract; if nothing is lost, they were filler.
- Verify that the numbers in the abstract, introduction and conclusion are identical and match the tables.
- Verify that the contribution list, the abstract and the conclusion make the same claims.
- Search for "novel", "state-of-the-art", "significantly", "very", "extensive", "efficient", "robust"; keep each only with evidence.
