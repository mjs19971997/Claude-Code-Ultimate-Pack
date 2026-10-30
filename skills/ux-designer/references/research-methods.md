# Research Methods

Reference for choosing, running and synthesizing user research. Verified against the NN/g framing of research methods (attitudinal vs behavioral, qualitative vs quantitative, context of use), the HEART framework paper (Rodden, Hutchinson and Fu, CHI 2010) and ISO 9241-11 / 9241-210 (2026-10). No percentages or sample-size guarantees are given beyond those attributed to a named source; plan sample sizes for your own decision and risk.

## 1. Choose the method from the question

| Question | Typical methods | Output |
|---|---|---|
| What problems and needs exist? (generative) | Interviews, contextual inquiry and field studies, diary studies, support-ticket and sales-call review | Needs, workflows, pain points, vocabulary |
| Do people understand and can they use this? (evaluative) | Usability tests, cognitive walkthrough, heuristic evaluation, first-click test | Issues with severity, task success, causes |
| How should content be organized and labeled? | Open and closed card sorts, tree testing, search-log analysis | Groupings, labels, findability |
| How many people, how often, where do they drop off? | Product analytics, funnels, surveys with adequate samples | Rates, trends, segments |
| Which version performs better? | A/B and multivariate experiments | Causal effect on a chosen metric |
| How do people feel overall? | SUS, SEQ, satisfaction items inside HEART | Attitudinal scores to track over time |
| Will they want this? | Concept tests, smoke tests, prototype tests, fake-door tests (disclose honestly), pre-orders | Evidence of demand and expectations |

Combine methods: qualitative work explains why, quantitative work shows how much. Triangulate important decisions across at least two sources.

## 2. Research plan

A one-page plan keeps studies honest:

1. Decision: what will be decided or changed by this research?
2. Research questions: 3 to 5, answerable by observation.
3. Method and rationale: why this method fits these questions.
4. Participants: who, how many, how recruited, screener criteria, exclusions.
5. Materials: script, prototype, tasks, consent form.
6. Logistics and ethics: consent, recording, data storage, incentives, accessibility of the session.
7. Analysis plan: how notes become findings; who reviews.
8. Output and audience: format, date, who acts.

## 3. Methods in practice

### Interviews
- Semi-structured guide with open questions; ask for specific recent episodes ("tell me about the last time you...") rather than opinions about hypothetical features.
- Probe with "why", "what happened next", "how did you decide". Stay silent after answers; avoid suggesting answers.
- Do not pitch your idea; do not ask people to design the solution.

### Contextual inquiry and field studies
- Observe people in their environment doing real work; note tools, workarounds, interruptions, collaborators.
- Findings are workflow and context models, not preferences.

### Diary and longitudinal studies
- Participants log events or feelings over days or weeks; useful for infrequent or long-running behaviors. Keep entries short and provide reminders; compensate for the effort.

### Surveys
- Use for measurement and sizing, not discovery. Write neutral, single-concept questions; avoid double-barreled items, leading wording and unbalanced scales; pilot before launch.
- Sample matters more than size: define the population, reduce non-response and self-selection bias, and report who answered.
- Use validated instruments where they exist (for example SUS).

### Card sorting
- Open sort: participants group items and name groups (generate structure ideas). Closed sort: participants place items into predefined categories (test labels). Hybrid allows new categories.
- Use 30 to 60 items that represent real content; analyze agreement patterns (similarity matrices, dendrograms) as input, not as the final IA.

### Tree testing
- Participants find items in a text-only hierarchy; measures success, directness and where people go wrong. Run it before visual design to test structure and labels, and again after changes.

### First-click and navigation tests
- Show a screen and ask where they would click to do a task; the first click strongly influences task success. Use on key entry points.

### Analytics and logs
- Define events before launch; funnels show where people leave, not why. Pair with sessions, surveys or interviews to explain.
- Search queries and zero-result searches reveal vocabulary and missing content.

### Concept and prototype tests
- Test comprehension and value: can they explain what it is, who it is for, and what they would do next? Use realistic prototypes; ask about expectations before revealing details.

### Experiments (A/B tests)
- State hypothesis, primary metric, guardrail metrics, population, minimum detectable effect and sample size before starting; use a fixed analysis plan; avoid stopping at the first favorable result.
- Randomize at the right unit (user, not session, when experiences persist); watch for novelty effects and sample-ratio mismatch.
- Experiments answer "which is better by this metric", not "why".

## 4. Recruiting and sampling

- Recruit people who match the behaviors and context you care about, not only demographics. Write a screener with behavioral criteria and a few distractor options so candidates cannot guess the "right" answer.
- Include edge users: novices, experts, people using assistive technology, people on slow connections and small screens, and non-native speakers where relevant.
- Qualitative studies run in small rounds; stop a round when new sessions stop revealing new themes for the questions asked, and recruit again for each distinct segment.
- Avoid recruiting only colleagues, friends or highly engaged power users unless they are the target.
- Pay or otherwise compensate fairly; schedule across time zones; offer remote and in-person options.

## 5. Synthesis

1. Capture raw observations as single-fact notes tagged by participant ID (not name).
2. Affinity-map notes into themes bottom-up; keep observation (what happened), interpretation (why we think) and recommendation (what to do) separate.
3. Rank by frequency, severity, and relevance to goals; note confidence and the evidence behind each theme.
4. Produce artifacts that drive decisions: problem statements, jobs-to-be-done, journey maps, opportunity lists, annotated flows.
5. Record what was not learned and the next questions.

### Jobs-to-be-done
Statement: "When [situation], I want to [motivation], so I can [expected outcome]." Describe the circumstances, forces (push, pull, anxiety, habit) and the alternatives used today. Use it to scope features by progress made, not by user demographics.

### Personas
Base them on observed behaviors, goals, constraints and context. Avoid stock photos and invented trivia; include what the persona needs from the product and where it fails them today. If a persona is not backed by research, label it a hypothesis.

### Journey maps
Stages (before, during, after), actions, touchpoints, thoughts, emotions, pain points, opportunities. Each cell should trace to evidence; mark inferred cells.

## 6. HEART and Goals-Signals-Metrics

HEART (Rodden, Hutchinson and Fu) provides five dimensions: Happiness (attitude, satisfaction), Engagement (depth of involvement), Adoption (new users or new feature uptake), Retention (continued use), Task success (efficiency, effectiveness, errors). Not every dimension applies to every product or feature.

Process:
1. Goals: what the product or feature should achieve for users and the business, per relevant dimension.
2. Signals: observable behaviors or attitudes that indicate the goal is met or not.
3. Metrics: concrete, computable measures of the signals, with baselines and targets.

Tips: choose few metrics per goal; separate leading (task success, adoption) from lagging (retention); add guardrail metrics that detect harm; revisit definitions when the product changes. Satisfaction metrics come from surveys (SUS, SEQ, custom items); behavioral metrics from instrumentation.

## 7. Ethics and data protection

- Informed consent before starting: purpose, what is recorded, who sees it, how long it is kept, right to stop at any time, how to withdraw data.
- Collect the minimum personal data; use participant IDs; store consent forms separately from notes; restrict access to recordings; set deletion dates.
- Do not deceive participants in ways that could harm them; debrief when deception is part of the method.
- Take extra care with minors, health, finance and other sensitive topics; follow your organization's review process and applicable laws (such as GDPR).
- Report findings honestly, including those that contradict stakeholder expectations; do not cherry-pick quotes.
