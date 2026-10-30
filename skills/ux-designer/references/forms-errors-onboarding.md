# Forms, Errors, Onboarding and Deceptive Design

Reference for form UX, error and empty states, destructive actions, onboarding, microcopy and the review of dark patterns. Verified against WCAG 2.2 (Recommendation, October 2023) success criteria cited below, the HTML `autocomplete` attribute tokens, the FTC staff report "Bringing Dark Patterns to Light" (2022), EU Digital Services Act Article 25, and the Eighth Circuit's July 2025 vacatur of the FTC click-to-cancel rule (2026-10). This is design guidance, not legal advice.

## 1. Form design

- Ask only for what the task needs now; every field costs completion. Remove optional fields that do not change the outcome or move them after the main action.
- One column, logical order, related fields grouped with `fieldset` and `legend` (addresses, radio groups).
- Visible, persistent labels above or beside inputs. Placeholders show format examples only. Put help text before the user needs it, not only after an error.
- Use the right control: `type="email"`, `type="tel"`, `inputmode="numeric"`, date pickers only when they help (typing a known date is often faster), radio buttons for 2 to 5 mutually exclusive options, select or combobox for long lists with search.
- Add `autocomplete` tokens (`name`, `email`, `street-address`, `postal-code`, `cc-number`, `one-time-code`, `new-password`, `current-password`) so browsers and password managers can fill; WCAG 1.3.5 Identify Input Purpose depends on them.
- Do not split single values across many boxes (phone, card, one-time code) without paste and autofill support.
- Accept input flexibly (spaces and dashes in phone and card numbers) and normalize on the server; do not make users match your format.
- Mark required and optional consistently; state the convention at the top.
- Do not clear fields on error; keep focus and scroll position meaningful.
- Redundant entry: do not ask users to re-enter information already provided in the same process unless needed for security or validity (WCAG 3.3.7).
- Long forms: save progress, show steps and allow going back; confirm what happens on submit.
- Submit buttons: a specific verb ("Create account"), enabled by default; if disabled, explain why. Prevent double submission by showing progress after click, not by silently ignoring clicks.

### Validation timing
- Prefer validating on blur (leaving the field) and on submit; show success states sparingly. Avoid errors while the user is mid-entry.
- Live checks help for password rules, character limits and username availability; show them as guidance, not as red errors.
- On submit with errors: summarize at the top (links to each field) and mark each field inline; move focus to the summary or first invalid field.
- Server errors must map to fields wherever possible; keep a generic fallback message with a retry path.

### Passwords and authentication
- Allow paste, support password managers, offer show/hide, state requirements up front, and prefer length over arbitrary complexity rules.
- Offer alternatives to cognitive tests at login (WCAG 3.3.8 Accessible Authentication (Minimum)): magic links, passkeys, authenticator apps, password managers.
- Failure messages: "Email or password is incorrect" without revealing whether an account exists; provide recovery that does not lock users out indefinitely.

## 2. Error design

Error types and treatment:

| Type | Treatment |
|---|---|
| Validation (user input) | Inline, next to the field, specific fix ("Enter a date after today"), linked from a summary |
| System / server | Say it is not the user's fault, what is affected, what to do (retry, contact), keep their data; include a reference ID for support |
| Network / offline | Detect, say the action was not completed or is queued, retry automatically when safe |
| Permission / not authorized | Explain what is missing and how to request access |
| Not found | Search, navigation back, and links to likely destinations; keep the same layout so the site feels intact |
| Timeout / session expiry | Warn before expiry when possible, preserve work, return to the same place after sign-in |

Writing: say what happened, why if known, and how to fix it. Plain language, no blame, no codes without explanation, no jokes for serious failures. WCAG 3.3.1 (Error Identification) requires identifying errors in text, 3.3.3 (Error Suggestion) requires suggestions where known, and 3.3.4 (Error Prevention for legal, financial and data submissions) requires reversibility, checking or confirmation.

## 3. Empty, loading and success states

- Empty: explain what belongs here, why it is empty, and the primary next action; offer templates or sample data. Distinguish "no data yet" from "no results for this filter" (offer to clear filters) and "failed to load".
- Loading: skeletons or placeholders keyed to the final layout; show determinate progress for long operations; keep the interface usable and allow cancel when feasible.
- Success: confirm the result and what happens next (email sent, ETA), offer the logical next step; use toasts only for low-stakes confirmation that does not require reading, and keep them long enough to read and dismissible.
- Partial: when some items fail in a batch, list which succeeded and failed with a retry for failures.

## 4. Destructive and high-impact actions

- Prefer undo: perform the action, show "Item deleted. Undo", keep it recoverable for a stated period.
- For irreversible actions, state the object and consequence in the dialog ("Delete project Atlas and its 42 files? This cannot be undone."), use a specific button label ("Delete project"), keep the cancel option equally reachable, and do not make the destructive option the default focus.
- For very high impact (account deletion, large payments), require explicit confirmation such as typing the resource name, plus a recovery window if feasible.
- Separate dangerous actions from routine ones spatially; do not place them next to frequently used buttons.

## 5. Onboarding

- Define the activation moment (the first outcome that delivers value for this product) from evidence, and measure time and steps to reach it.
- Let people try before committing: delay account creation or heavy profile setup until value is shown, if the product allows it.
- Prefer learning by doing: sample content, templates, checklists with progress, contextual hints triggered by relevant actions. Avoid long forced product tours; make any tour skippable and re-openable.
- Ask for permissions (notifications, location, contacts) at the moment of need with a short rationale, and let the product work if declined.
- Segment lightly: ask one or two questions that genuinely change the experience; do not interrogate.
- Keep help reachable (search, docs, support) and persistent through the first sessions.
- Measure with HEART: Adoption (completed first key action), Task success (errors, time), Retention (returned in week two), Happiness (post-onboarding rating). Test onboarding with first-time users who match the target, not team members.

## 6. Microcopy

- Buttons: verb plus object. Avoid "Submit", "OK", "Yes/No" where a specific label is clearer.
- Headings and links make sense out of context; avoid "Click here".
- Status and confirmation messages name the thing affected.
- Be consistent with terms; avoid internal jargon and abbreviations; define unavoidable terms inline.
- Translatable text: avoid concatenating sentence fragments; allow for text expansion.
- Tone: calm and helpful; reduce humor in error, payment and security contexts.

## 7. Dark patterns: recognizing and avoiding

Deceptive or manipulative design steers users toward choices that benefit the business at the user's expense. Brignull coined the term "dark patterns" (2010) and maintains deceptive.design with named types. Gray et al. (CHI 2018, "The Dark (Patterns) Side of UX Design") grouped them into five strategies.

| Gray et al. strategy | Examples to avoid |
|---|---|
| Nagging | Repeated interruptions to enable notifications or upgrade, with no "never ask again" |
| Obstruction | Roach motel (easy to sign up, hard to cancel), making data export or deletion difficult, requiring a call to cancel an online subscription |
| Sneaking | Hidden costs or fees revealed late (drip pricing), pre-checked add-ons, adding items to cart, hidden subscription terms, forced continuity after a trial without clear notice |
| Interface interference | Confirmshaming ("No thanks, I don't like saving money"), visually dominant "accept" with a faint "reject", misleading toggles, trick questions with double negatives, disguised ads, false urgency or scarcity timers |
| Forced action | Requiring account creation, data sharing or unrelated consent to complete a basic task |

Review test for any flow involving money, consent, data or cancellation:
1. Are the options presented with equal clarity, prominence and effort (accept and reject, subscribe and cancel)?
2. Are price, recurring charges, renewal dates and limits stated clearly before commitment?
3. Is consent unbundled, unticked by default and as easy to withdraw as to give?
4. Can users leave, cancel or delete through the same channel they used to join, with comparable effort?
5. Are urgency and scarcity claims true and verifiable?
6. Would the team be comfortable if users could see exactly why each design choice was made?

### Regulatory context
- United States: the FTC's 2022 staff report "Bringing Dark Patterns to Light" documents deceptive practices and enforcement under the FTC Act and statutes such as ROSCA (online negative-option sales). The FTC click-to-cancel rule was vacated by the Eighth Circuit in July 2025 on procedural grounds; ROSCA and many state automatic-renewal laws still apply. Rulemaking status may have moved since; check current sources.
- European Union: Article 25 of the Digital Services Act addresses online interface design on online platforms, prohibiting designs that deceive or manipulate or otherwise materially distort users' ability to make free and informed decisions; the Unfair Commercial Practices Directive and GDPR consent rules also apply to many interfaces.
- Treat regulatory exposure as one reason to avoid dark patterns; the primary reason is that they erode trust and produce users who leave, complain or churn later.

### Ethical persuasion
Legitimate nudges help users reach goals they already hold (reminders they opted into, sensible defaults that are easy to change, clear comparisons). Test: if users understood the mechanism, would they feel helped or tricked?
