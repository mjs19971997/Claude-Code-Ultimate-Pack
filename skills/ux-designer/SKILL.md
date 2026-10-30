---
name: ux-designer
description: >-
  Plans and evaluates user experience with evidence: choosing research methods, information architecture, interaction design, usability testing and heuristic evaluation (Nielsen), HEART metrics with Goals-Signals-Metrics, form UX, error, empty and loading states, onboarding, and recognizing and avoiding dark patterns. Use when scoping user research, structuring navigation, designing flows and microcopy, writing a usability test plan, defining success metrics, or reviewing a flow for friction and deceptive design. Not for visual design systems, tokens or typography (use ui-designer) or WCAG conformance detail (use accessibility-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# UX Designer

This skill covers the decisions that shape how a product works for people: who the users are and what they are trying to do, how content and features are organized, how interactions behave, how to test and measure the result, and where design crosses into manipulation. It is method-oriented and implementation-neutral; code appears only where markup carries UX meaning (forms, error messages).

> Verified against Nielsen's 10 usability heuristics (1994, wording refined 2020), the HEART framework (Rodden, Hutchinson and Fu, CHI 2010), ISO 9241-11 and ISO 9241-210, WCAG 2.2 (W3C Recommendation, October 2023), FTC staff report "Bringing Dark Patterns to Light" (2022), EU Digital Services Act Article 25 and the status of the FTC click-to-cancel rule (vacated by the Eighth Circuit in July 2025; ROSCA unaffected) (2026-10).

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

- Covered: problem framing, research planning and synthesis, personas and jobs-to-be-done, information architecture and navigation, flows and interaction patterns, forms, feedback and error states, onboarding, microcopy, usability testing, heuristic evaluation, metrics (HEART, SUS, task success), experiment design basics, dark-pattern review.
- Not covered: visual design systems, tokens, typography and component styling (ui-designer); detailed WCAG success criteria, ARIA and assistive-technology testing (accessibility-expert); component implementation (shadcn-ui-expert, senior-react-19-engineer); page speed budgets (core-web-vitals-expert); search ranking (technical-seo-expert).
- Accessibility appears here as a UX requirement (inclusive flows, target sizes, plain language); conformance auditing belongs to accessibility-expert.

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Usability definition | ISO 9241-11: the extent to which specified users can achieve specified goals with effectiveness, efficiency and satisfaction in a specified context of use. ISO 9241-210 describes human-centred design as iterating: understand context of use, specify requirements, produce design solutions, evaluate against requirements |
| Nielsen heuristics | Visibility of system status; match between system and the real world; user control and freedom; consistency and standards; error prevention; recognition rather than recall; flexibility and efficiency of use; aesthetic and minimalist design; help users recognize, diagnose and recover from errors; help and documentation |
| Research landscape | Axes: attitudinal vs behavioral, qualitative vs quantitative, generative (discover problems) vs evaluative (test solutions). Match the method to the question; see [references/research-methods.md](references/research-methods.md) |
| Information architecture | Organization schemes (topic, task, audience, chronology, alphabet), labeling, navigation systems (global, local, contextual), search; validated with card sorting, tree testing and first-click tests |
| Interaction design | Affordances and signifiers, feedback, constraints, mapping, conceptual models, gulfs of execution and evaluation (Norman); progressive disclosure; sensible defaults |
| Response-time limits | Nielsen's widely cited thresholds: about 0.1 s feels instantaneous, about 1 s keeps the user's flow of thought, about 10 s is the limit of attention; beyond 1 s show progress |
| Laws of interaction | Fitts's law (target acquisition depends on distance and size), Hick's law (decision time grows with the number and complexity of choices); use as directional guidance, not as precise predictors |
| HEART | Happiness, Engagement, Adoption, Retention, Task success, applied through Goals, Signals, Metrics so each product goal maps to observable signals and metrics |
| Usability measures | Task success, time on task, error count, Single Ease Question (SEQ), System Usability Scale (SUS: 10 items, scored 0 to 100, which is not a percentage), qualitative issues with severity ratings |
| Accessibility as UX | WCAG 2.2 adds Target Size (Minimum) 24 by 24 CSS px (2.5.8), Redundant Entry (3.3.7), Accessible Authentication (Minimum) (3.3.8), Focus Not Obscured (Minimum) (2.4.11), Consistent Help (3.2.6); design flows so these are met by default |
| Deceptive design | Taxonomies: Brignull's types (confirmshaming, roach motel, hidden costs, trick questions, ...) and Gray et al. (2018): nagging, obstruction, sneaking, interface interference, forced action |

## 3. Workflow

1. **Frame the problem**: who is affected, what they are trying to accomplish (job), what happens today, what evidence exists (analytics, support tickets, prior research), what decision the work will inform.
2. **Plan research**: write research questions, pick methods that can answer them ([references/research-methods.md](references/research-methods.md)), define participants and screener, plan consent and data handling.
3. **Synthesize**: cluster observations (affinity mapping), separate observations from interpretations, name the user needs and pain points with supporting evidence; keep the sample size visible.
4. **Structure**: define content inventory and IA, user flows (entry points, happy path, edge cases, error recovery), and states for each screen (empty, loading, partial, error, success, offline, permission denied).
5. **Design interactions**: low-fidelity wireframes or prototypes, microcopy, form behavior, validation timing, destructive-action handling. Review with the Nielsen heuristics and a dark-pattern check.
6. **Test**: moderated or unmoderated usability tests on a prototype or build ([references/usability-testing.md](references/usability-testing.md)); fix by severity; retest.
7. **Define success**: pick HEART dimensions that matter, set Goals, Signals and Metrics, baseline before the change, and plan how results will be read (including guardrail metrics).
8. **Hand off and learn**: annotated flows with states and content, acceptance criteria that cover error and empty states, and a plan to review post-launch data and feedback.

## 4. Decision Rules

- Method follows the question. "What problems exist?" needs generative methods (interviews, field studies, diary studies). "Can people use this?" needs usability testing. "How many and how often?" needs analytics or surveys. "Which labels and structure work?" needs card sorting and tree testing.
- Observe behavior for behavior questions; use interviews and surveys for motivations and attitudes, and do not treat stated intentions as predictions of behavior.
- Qualitative sample sizes are small and iterative; quantitative claims need adequately sized samples and stated uncertainty. Do not generalize percentages from a handful of sessions.
- Choose navigation depth by content and task frequency: broad-and-shallow tends to beat deep hierarchies when labels are clear, but test with tree testing rather than assuming.
- Modal vs inline vs separate page: modals for short, focused, interruptible decisions; inline editing for low-risk changes; separate pages for long tasks, anything users may bookmark, or content that needs space.
- Confirmation dialogs vs undo: for reversible actions prefer an action followed by Undo; use a confirmation naming the object and consequence for irreversible or high-impact actions.
- Required data: ask only for what the task needs now. Defer account creation until value is demonstrated when the product allows it; do not request the same information twice in a flow (WCAG 3.3.7 Redundant Entry).
- Validation timing: validate on blur or on submit, not on each keystroke, except for helpers such as password strength or character counters; keep the user's input after an error.
- A/B test only when there is a hypothesis, one primary metric, guardrail metrics, a precomputed sample size and a fixed analysis plan. Do not stop early because a result looks good.
- Persuasion is acceptable when it helps users reach their own goals and is honest; it becomes a dark pattern when it hides information, obstructs a choice or exploits a bias against the user's interest.
- Personas: use evidence-based archetypes tied to jobs and behaviors, not invented demographics. If there is no research, label them as hypotheses.

## 5. Coding Standards

Deliverable and content conventions (the equivalent of code standards for UX work):

- Name flows by user goal ("Reset password", "Invite teammate"), screens by purpose, and states explicitly (`empty`, `loading`, `error`, `success`).
- Write interface text in plain language, active voice, with the user's vocabulary; buttons start with a verb ("Save changes", "Send invoice"); avoid "OK/Cancel" for consequential choices.
- Error messages say what happened, why if known, and what to do next; never blame the user and never show raw codes or stack traces without a human sentence.
- Labels are visible and persistent; placeholders are examples, not labels. Mark optional fields as optional and be consistent about how required fields are indicated.
- Keep terminology consistent across navigation, page titles, buttons and help; keep a glossary of product terms.
- Document assumptions and open questions on every flow; link each design decision to the research evidence or heuristic behind it.
- Specify interactive behavior (focus order, keyboard operation, what happens on failure, timeouts) alongside visuals.
- Use standard patterns and platform conventions unless testing shows a better alternative (consistency and standards).

## 6. Project Structure

```
ux/
├── research/
│   ├── plan.md                  # questions, methods, participants, ethics, timeline
│   ├── screener.md
│   ├── notes/                   # session notes by participant ID (no direct identifiers)
│   └── synthesis.md             # themes, evidence, confidence, open questions
├── strategy/
│   ├── jobs-and-personas.md
│   └── metrics.md               # HEART goals, signals, metrics, baselines
├── ia/
│   ├── content-inventory.csv
│   ├── sitemap.md
│   └── tree-test-results.md
├── flows/
│   └── <flow-name>.md           # steps, decisions, states, error paths
├── tests/
│   ├── <round>-plan.md          # tasks, success criteria, scripts
│   └── <round>-findings.md      # issues with severity and recommended fixes
└── content/
    └── microcopy.md             # labels, errors, empty states, confirmations
```

## 7. Design Patterns

- **Jobs-to-be-done statement**: "When [situation], I want to [motivation], so I can [outcome]." Anchors flows to goals instead of features.
- **Journey map**: stages, user actions, thoughts, emotions, pain points and opportunities, with evidence for each claim.
- **Progressive disclosure**: show the common path first and reveal advanced options on request; keep the path back obvious.
- **State coverage**: every data-driven view specifies empty (explain and offer the next action), loading (skeleton or progress for waits over about a second), partial, error (with retry), success and permission-denied states.
- **Undo over confirm**: soft delete, toast with Undo, trash with restore.
- **Guided first run**: checklist, sample data or templates, and contextual hints rather than a forced tour; always skippable.
- **Smart defaults and autofill**: prefill from known context, use `autocomplete` tokens, let users change defaults.
- **Wizard for complex tasks**: show progress and allow going back without data loss; keep steps few and each step single-purpose.
- Detailed pattern guidance for forms, errors and onboarding: [references/forms-errors-onboarding.md](references/forms-errors-onboarding.md).

## 8. Best Practices

- Involve users early and repeatedly; a few sessions on a rough prototype beat one large study after build.
- Test the riskiest assumption first (can they find it, understand it, complete it).
- Separate problem discovery from solution evaluation; do not ask participants to design the solution.
- Make research findings actionable: each finding has evidence, impact, a severity and a proposed direction.
- Keep one source of truth for flows and copy; stale screenshots cause rework.
- Design for the whole range of users and contexts: slow networks, small screens, one-handed use, assistive technology, interruptions, non-native language.
- Reduce cognitive load: fewer choices at once, recognition over recall, chunked information, consistent placement.
- Make system status visible, especially for asynchronous work (uploads, payments, background jobs): what is happening, how long, what happens next.
- Provide help in context (hints, inline explanations) and an escape hatch (contact, undo, back).
- Treat microcopy as part of the interface; review it in context, not in a spreadsheet only.

## 9. Performance

- Perceived performance is UX: use the response-time limits (about 0.1 s, 1 s, 10 s) to decide between instant feedback, a spinner or skeleton, and a progress indicator with remaining-time or step information.
- Optimistic UI (show success immediately, reconcile in the background) suits low-risk, highly reliable actions; always handle and surface the failure case.
- Skeleton screens help layout stability for content loads; use determinate progress for long operations and allow cancel.
- Avoid layout shifts and moving targets: content that jumps under the pointer causes mis-taps (coordinate with core-web-vitals-expert for measurement).
- Reduce effort, not only time: fewer steps, fewer fields, remembered preferences, keyboard shortcuts for expert users (flexibility and efficiency of use).
- Mobile: keep primary actions within reach, ensure touch targets are comfortably large (WCAG 2.2 sets a 24 by 24 CSS px minimum; larger is better for primary actions), and avoid hover-only interactions.

## 10. Security

- Research ethics and privacy: obtain informed consent, explain recording and data use, minimize personal data, store recordings and notes securely with restricted access, set retention periods, and honor deletion requests. Follow applicable law such as GDPR where it applies.
- Never use real customer data in prototypes or shared research artifacts without permission; redact screenshots.
- Security UX: do not block paste in password fields (it prevents password managers); offer show/hide password; give generic messages on login failure that do not reveal whether an account exists; explain why MFA is requested and provide recovery options.
- Make security warnings specific, rare and actionable; alert fatigue trains users to click through. Do not use scare tactics or false urgency.
- WCAG 2.2 Accessible Authentication (Minimum) means login should not depend on a cognitive function test (memorizing or transcribing) without an alternative such as paste, password managers or a different method.
- Permission requests (location, camera, notifications): explain the benefit in context before the system prompt and keep the product usable if the user declines.
- Destructive and financial actions need clear scope, consequence and, when high-impact, additional verification.

## 11. Testing

- Usability testing: realistic task scenarios, think-aloud for qualitative insight, success criteria defined before sessions, note-takers separate from the moderator, severity ratings after. Details and templates in [references/usability-testing.md](references/usability-testing.md).
- Heuristic evaluation: several evaluators review independently against the heuristics, then consolidate; it finds likely problems but does not replace testing with users.
- Cognitive walkthrough: step through a task asking, at each step, whether the user will know what to do, notice the correct action, connect it to their goal and see progress.
- IA validation: closed card sort for labels, open card sort for grouping ideas, tree testing for findability, first-click testing for entry points.
- Quantitative: SUS for overall perceived usability, SEQ per task, task success and time, funnel analytics for drop-off, experiments for causal questions.
- Accessibility checks within usability testing: include participants who use assistive technology when possible; keyboard-only passes of key flows.
- Retest after changes; track whether fixes removed the problem rather than assuming.

## 12. Review Checklist

- [ ] The problem, target users and success measures are written down and agreed.
- [ ] Research claims cite evidence and state sample size and method limits.
- [ ] Each flow covers entry points, the happy path, errors, empty states, and recovery.
- [ ] Navigation labels use user vocabulary and were validated or are flagged as untested.
- [ ] System status is visible for waits and background work.
- [ ] Users can undo, cancel or go back; destructive actions are clear and reversible where possible.
- [ ] Forms: visible labels, correct input types and `autocomplete`, validation on blur or submit, inline errors tied to fields, input preserved after error.
- [ ] Error messages are specific, blame-free and offer a next step.
- [ ] No dark patterns: choices are symmetric, costs and renewal terms are clear before commitment, cancel is as easy as sign-up, defaults serve the user.
- [ ] Targets, focus order, keyboard operation and reduced-motion behavior are specified (details with accessibility-expert).
- [ ] Metrics have baselines, guardrails and an owner for reading them.

## 13. Production Notes

- Instrument before launch: baseline the HEART signals you plan to move, and confirm events fire correctly in staging.
- Release behind flags when possible, so qualitative feedback and metrics can inform rollout; keep a rollback path for UX regressions.
- Watch both quantitative signals (task completion, drop-off, error rates, support contacts) and qualitative ones (support tickets, session recordings where consent allows, open-text feedback).
- Experiments: run for the planned duration, do not peek and stop on a favorable blip, report effect sizes with uncertainty, and check guardrails (for example support contacts, refunds, cancellations).
- Keep a research repository so findings are searchable and reused; stale insights should be dated.
- Regulatory context for subscriptions and consent: the FTC's 2022 dark-patterns staff report and enforcement under ROSCA in the United States, and Article 25 of the EU Digital Services Act for online platforms, are relevant to cancellation flows, pricing disclosure and consent interfaces. The FTC click-to-cancel rule was vacated by the Eighth Circuit in July 2025 on procedural grounds, while ROSCA and state automatic-renewal laws remain; confirm current requirements with legal counsel for your markets.
- Localization affects UX: text expansion, date and number formats, right-to-left layouts and cultural conventions should be tested, not assumed.

## 14. Examples

HEART metrics plan for a redesigned invoice-approval flow (Goals, Signals, Metrics):

```text
Dimension     Goal                              Signal                         Metric (baseline first)
Happiness     Approvers feel in control         Post-task rating               SEQ per task, SUS each quarter
Engagement    Approvers act within the tool     Approvals made in-app          Approvals per approver per week
Adoption      New approvers complete first      First approval completed       Share of invited approvers who approve within 7 days
Retention     Approvers keep using the tool     Active in consecutive weeks    Weekly active approvers, 8-week retention
Task success  Approvals are fast and correct    Approval completed w/o error   Completion rate, median time, error and reversal rate
Guardrails    No loss in review quality         Rejected-after-approval        Reversal rate, support contacts per 100 approvals
```

Accessible form field with hint and inline error (the UX contract: visible label, input purpose, error tied to the field, input preserved):

```html
<div class="field">
  <label for="email">Work email</label>
  <input id="email" name="email" type="email" autocomplete="email"
         inputmode="email" required aria-describedby="email-hint email-error"
         aria-invalid="true" value="ana@exmaple.com">
  <p id="email-hint">We send the invoice approval link here.</p>
  <p id="email-error" role="alert">
    This address does not look right. Check for typos, for example "example.com".
  </p>
</div>
```

Usability test task scenario (neutral wording, success criteria, no instructions on where to click):

```text
Scenario: Your manager forwarded you an invoice from Northwind that needs your approval
before Friday. You do not remember how the new system works.

Task: Approve the invoice from Northwind, or tell us what stops you.

Success: Invoice status shows Approved and the participant can say what happens next.
Record: success (yes / yes with help / no), time on task, errors, path taken, verbatim
comments, SEQ rating (1-7: "Overall, how easy or difficult was this task?").
Stop condition: 5 minutes or participant gives up.
```

## 15. Common Mistakes

- **Designing without research or evidence**: opinions replace data. State assumptions and test the riskiest ones.
- **Asking participants what they would do or want**: stated preferences predict poorly. Watch tasks, ask about past behavior.
- **Leading questions and tasks** ("Click the Export button"): reveal the answer. Use goals and scenarios.
- **Treating a small test as proof of percentages**: qualitative tests find problems; they do not estimate rates.
- **Placeholder text as the only label**: it disappears on input, fails for memory and accessibility. Use visible labels.
- **Validating on every keystroke**: shows errors before the user finishes. Validate on blur or submit.
- **Clearing the form on error or disabling submit without explanation**: users lose work or do not know why they are blocked.
- **Skipping empty, loading, error and permission states**: these are the states users actually meet first and when things fail.
- **Modal overload and confirmation fatigue**: reserve modals for decisions that need them; use undo where possible.
- **Auto-advancing carousels and hidden primary content**: users miss or cannot control the content; avoid them for important information.
- **Jargon and internal terms in labels**: use the vocabulary users use; validate with tree tests.
- **Metrics without baselines or guardrails**: improvement cannot be shown and harm can go unnoticed.
- **Dark patterns for short-term conversion**: confirmshaming, hidden costs, pre-ticked consent, hard-to-find cancellation, fake urgency or scarcity, and nagging damage trust and create legal exposure.
- **Treating accessibility as a late audit**: target size, focus order, error identification and plain language are cheaper to design in.
- **Citing statistics without a source**: unsourced figures (for example for conversion lifts or user counts) mislead stakeholders; cite the study or omit the number.

## 16. References

- [references/research-methods.md](references/research-methods.md): choosing methods, interviews, surveys, diary studies, card sorting and tree testing, analytics and experiments, synthesis, personas and JTBD, ethics.
- [references/usability-testing.md](references/usability-testing.md): test planning, tasks, moderation, sample sizes, severity ratings, SUS and SEQ, heuristic evaluation and cognitive walkthrough, reporting.
- [references/forms-errors-onboarding.md](references/forms-errors-onboarding.md): form design and validation, error and empty states, destructive actions, onboarding, microcopy, dark patterns and regulation.
- Official docs: https://www.nngroup.com/articles/ten-usability-heuristics/ , https://www.w3.org/TR/WCAG22/ , https://www.iso.org/standard/63500.html , https://research.google/pubs/measuring-the-user-experience-on-a-large-scale-user-centered-metrics-for-web-applications/ , https://www.ftc.gov/reports/bringing-dark-patterns-light , https://www.deceptive.design/
