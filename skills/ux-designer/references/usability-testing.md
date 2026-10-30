# Usability Testing and Inspection

Reference for planning, running and reporting usability tests, and for expert-inspection methods. Verified against NN/g guidance on heuristic evaluation and the Nielsen severity scale, Nielsen and Landauer (1993) on problem discovery by number of participants, Brooke (1996) for SUS, ISO 9241-11 and WCAG 2.2 target-size guidance (2026-10).

## 1. Test types

| Type | When | Notes |
|---|---|---|
| Moderated, in person or remote | Early prototypes, complex flows, exploring why | Moderator can probe; higher cost per session |
| Unmoderated remote | Well-defined tasks, larger samples, benchmarking | Needs clear tasks and a pilot; cannot probe in the moment |
| Guerrilla / hallway | Very early sanity checks | Convenient participants; treat as directional |
| Benchmark / summative | Compare versions or track over time | Needs consistent tasks, measures and enough participants for confidence intervals |
| Accessibility-inclusive | All major flows | Include participants who use screen readers, magnification, switch access, voice control, keyboard only |

Formative testing (find and fix problems) is the default; summative testing (measure against a target) needs stricter design.

## 2. Plan

1. Goals and decisions: what you need to learn; which flows and risks.
2. Prototype or build: realistic enough that tasks can be completed; remove dead ends unrelated to the study; use realistic data and content.
3. Participants: criteria, quotas per segment, number per round, backups for no-shows.
4. Tasks: 5 to 8 realistic scenarios for a 45 to 60 minute session; order by importance and dependency; randomize if order effects matter.
5. Measures: define success criteria per task before the first session.
6. Materials: consent, script, task cards, post-task and post-test questionnaires, observer guide.
7. Pilot with one or two people to fix tasks and the prototype.

### Sample sizes
- Nielsen and Landauer modeled problems found as N(1 - (1 - L)^n), where n is the number of participants and L the average probability that one participant exposes a given problem; their data averaged about 31 percent per participant. That supports running small, iterative qualitative rounds (NN/g's often-cited advice is around five participants per round for each distinct user group) rather than one large test.
- L varies with the product, tasks and participants; rare problems and different user groups need more people. The model is about finding problems, not estimating how many users will hit them.
- Quantitative claims (success rates, time, comparisons between designs) need larger samples; report confidence intervals and avoid presenting percentages from small samples as precise.

## 3. Writing tasks

- Use scenarios with a goal and context, not instructions: "You need to change your delivery address before Friday" instead of "Click Settings, then Addresses".
- Avoid words that appear in the interface labels; they give away the path.
- One goal per task; define a clear end state and a stop condition (time or give-up).
- Include a mix: typical frequent tasks, high-risk tasks, and recovery from an error.
- Provide needed data (account details, fictional card numbers, sample content) on a card; never ask participants to use real credentials or payment data.

## 4. Moderating

- Welcome and reassure: you are testing the design, not the participant; no wrong answers; they can stop at any time.
- Ask for think-aloud: "Please say what you are looking at, thinking and trying." Prompt neutrally ("What are you thinking?") if they go silent.
- Do not lead, explain or defend the design. Answer questions with questions ("What would you expect?"). Let participants struggle before offering help, then record any assist.
- Concurrent think-aloud can alter task time; for timing-sensitive measures use retrospective review or unmoderated timing.
- Observers stay silent and take notes (issue, evidence, severity guess) using a shared template; one moderator, one note-taker.
- End with open questions and a post-test questionnaire (SUS or similar).

## 5. Measures

| Measure | How | Notes |
|---|---|---|
| Task success | Coded per task: success, success with difficulty/assist, failure | Define "success" up front |
| Time on task | Start to end state | Compare only like with like; skip for think-aloud sessions |
| Errors | Wrong paths, slips, repeated attempts | Classify by cause |
| Single Ease Question (SEQ) | One 7-point item after each task ("Overall, how easy or difficult was this task?") | Quick per-task satisfaction |
| System Usability Scale (SUS) | 10 alternating positive and negative items on a 5-point scale after the session | Scored 0 to 100; it is not a percentage and is a relative measure, so compare across versions or against your own history |
| Qualitative issues | Observed behavior and quotes | Primary output of formative tests |

## 6. Severity ratings

A commonly used scale (Nielsen): 0 not a usability problem; 1 cosmetic only, fix if time allows; 2 minor, low priority; 3 major, high priority; 4 usability catastrophe, must fix before release. Rate by frequency (how many users meet it), impact (how hard to overcome) and persistence (does it recur once understood). Have the team rate independently, then reconcile.

## 7. Analysis and reporting

1. Consolidate issues across sessions; link each to evidence (participant IDs, quotes, clips).
2. Describe the problem, where it occurs, the cause hypothesis, severity, and a recommended direction. Fix the cause, not only the symptom.
3. Report what worked as well as what failed.
4. Summarize success per task with counts ("4 of 6 participants completed unaided") rather than percentages for small samples.
5. Share short clips for the highest-severity issues; stakeholders believe what they see.
6. Track issues in the same backlog as other work, link retest results, and close them only after verification.

## 8. Inspection methods

### Heuristic evaluation
- Several evaluators review independently against a heuristic set (Nielsen's ten or a domain-specific list), logging each violation with location, heuristic and severity; then consolidate. Independent reviews matter because different evaluators find different problems.
- Strengths: fast, cheap, good early. Limits: finds potential problems, produces false positives, misses issues that arise from real tasks. Use it alongside testing, not in place of it.

### Cognitive walkthrough
- For each step of a task: Will the user try to achieve the right effect? Will they notice the correct action is available? Will they connect the action with the effect they want? Will they see progress after acting?
- Best for learnability of infrequent or first-use tasks.

### Accessibility inspection
- Keyboard-only pass of key flows (reach, operate, visible focus, no traps), screen-reader pass of landmarks and form errors, zoom and reflow checks, target size (WCAG 2.2 requires at least 24 by 24 CSS px for pointer targets with exceptions), reduced-motion behavior. Formal conformance evaluation is the accessibility-expert's domain.

## 9. Remote testing notes

- Verify video, audio and screen sharing in advance; provide a fallback channel.
- For unmoderated tests, write task text that stands alone, include attention checks sparingly, and review a sample of recordings to remove low-quality sessions with documented criteria.
- Make sure tools and prototypes are keyboard and screen-reader accessible so you do not exclude participants.

## 10. Ethics checklist

- Consent obtained before recording; participants told how data is stored and for how long.
- No real personal data used in tasks; recordings access-restricted; names removed from reports.
- Participants can stop any time without losing compensation.
- Sensitive topics handled with care and debriefing.
