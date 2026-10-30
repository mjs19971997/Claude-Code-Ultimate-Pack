# Prompting Reasoning Models

Reference for writing prompts for models that think before they answer, and for the vendor controls that set how much they think. Verified against Anthropic's prompting best practices, effort and Sonnet 5.5 prompting pages (platform.claude.com), the OpenAI Python SDK 3.41.0 request types, and the Google Gen AI SDK 2.34.0 types plus Google's JS codegen guide (2026-10). OpenAI's and Google's hosted prompting guides could not be fetched, so statements about those vendors are limited to what their SDK types document; read their current reasoning and thinking guides before tuning.

## 1. What changes with reasoning models

- The model plans and checks internally before replying, so the prompt's job is to define the problem well, not to dictate the steps.
- Depth is a setting (effort, thinking level or budget), not something the prompt text reliably controls.
- Thinking uses output tokens. A limit sized for a non-reasoning reply can truncate the answer.
- Behavior differs by model generation: defaults, available levels and whether thinking can be turned off all vary, so each model needs its own eval sweep.

## 2. Writing the prompt

1. **State the objective and the success test**: what the result is for, what makes it correct, which constraints are firm.
2. **Give context and the reasons for constraints**; the model can then handle cases you did not list.
3. **Prefer general instructions over prescriptive steps.** Anthropic's guide says a prompt such as "think thoroughly" often produces better reasoning than a hand-written step-by-step plan, because the model's reasoning frequently exceeds what a person would prescribe.
4. **Keep fixed procedures only when the procedure is the requirement**, for example a compliance order of checks or a mandated approval sequence. Phrase them as the policy ("check sanctions status before pricing") rather than as a reasoning script.
5. **Use worked examples as problem, method, expected answer.** Anthropic notes that multishot examples shape how the model approaches similar problems inside its own thinking.
6. **Add a verification criterion** ("before finishing, check the totals against the invoice lines") where errors are costly. Some newer models verify without being asked, and extra verification text can cause over-verification, so test with and without it.
7. **Bound exploration when the model overthinks.** A short instruction such as "choose an approach and commit to it; revisit only if new information contradicts it" reduces looping on models that explore heavily. Lower the effort setting as the primary fix.
8. **Use plain wording.** Emphatic language written for older models can cause over-triggering of tools and rules on newer ones; Anthropic recommends "use this tool when..." over "CRITICAL: you MUST use this tool when...".

Avoid on models that already reason:

- "Let's think step by step" and similar boilerplate.
- Long numbered reasoning plans that restate what the model would do anyway.
- Requests to print the full reasoning inside the answer. Anthropic documents that on its newest models a prompt asking the model to write out its reasoning, for example in thinking tags, may be declined; rely on the thinking setting, and ask for a short justification only when a user needs an explanation.
- Telling the model not to think. On models where thinking is on by default, such instructions can make internal markup appear in visible output; lower the effort setting instead.

If thinking is off or unavailable, manual chain-of-thought is a fallback: ask the model to work through the problem first and put the final answer in answer tags so code can extract it.

## 3. Provider controls

| Provider | Controls (from official docs or SDK types) | Notes |
|---|---|---|
| Anthropic | Adaptive thinking (`thinking: {"type": "adaptive"}`) with `output_config: {"effort": ...}`; levels `low`, `medium`, `high`, `xhigh`, `max`, with availability varying by model | On several current models thinking is always on or on by default; manual `budget_tokens` is deprecated on older models and rejected with a 400 on Claude 4.7 and later; Sonnet 5.5 also has `between_tools` as its lowest setting; effort is a behavioral signal, not a strict token budget |
| OpenAI | `reasoning={"effort": ...}` with `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max` (support is model-specific); `reasoning.summary`; `text.verbosity` (`low`, `medium`, `high`); `max_output_tokens` includes reasoning tokens | Lower effort gives faster responses and fewer reasoning tokens; `reasoning.context` controls which reasoning items are shown on later turns; sampling parameters can be restricted per model |
| Google | `ThinkingConfig(thinking_level=MINIMAL\|LOW\|MEDIUM\|HIGH)` or `thinking_budget` (`0` disables, `-1` automatic, model-dependent), `include_thoughts` | Google's JS codegen guide ties levels to Gemini 3 models (default `HIGH`) and budgets to Gemini 2.5 models; thought tokens count in usage totals; check the thinking page for the model in use |

Setting guidance:

- Start from the vendor's default for the model, then sweep one level up and one down on your eval set. Anthropic's pages recommend re-sweeping on each new model because level calibration changes between models.
- Low effort for routing, extraction, classification and latency-sensitive chat. Higher effort for multi-step planning, hard code, long-horizon agent work and analysis where a measured quality gain exists.
- Reserve the top levels for tasks where you measured gains; they lengthen thinking and replies sharply.
- Changing a top-level effort value between requests can invalidate prompt caches on some providers (Anthropic documents this); vary it across workloads rather than inside one cached conversation, or use a per-message mechanism where offered.

## 4. Token budgets and truncation

- Thinking counts toward the output limit: `max_tokens` on Anthropic, `max_output_tokens` on OpenAI, `max_output_tokens` with thinking on Gemini. Size the limit for thinking plus the reply.
- Treat truncated responses as failures even if partial output parses: `stop_reason == "max_tokens"` (Anthropic), `status == "incomplete"` (OpenAI), `finish_reason == MAX_TOKENS` (Gemini).
- Read content by block or item type, not by position; a response can begin with a thinking or reasoning item.
- Stream long reasoning requests; large limits on non-streaming calls risk timeouts.

## 5. Reasoning plus structured output

- Use provider-enforced schemas for the final answer. With a schema the response text holds only the JSON, so the working-out happens in thinking; if the model skips thinking, accuracy on multi-step tasks can drop.
- Anthropic's Sonnet 5.5 page reports that for reasoning tasks with JSON output, adding the line "Think the problem through before you answer." to the end of the system prompt, or raising effort, improves accuracy; at low and medium effort the model can occasionally think until the token limit, so check for truncation. Re-test such lines on your own evals before adopting them.
- If you cannot use schemas and must ask for JSON in text, expect the model to reason in the visible reply and write the JSON last; parse the last valid JSON value from text blocks only and retry once on failure.
- Avoid splitting into an answer call and a formatting call unless needed; it costs latency and money.

## 6. Prefill and format control

- Newer Claude models reject a prefilled last assistant turn. Replace prefills with structured outputs (format), direct instructions (skip preamble), or the user turn (context reminders).
- Tell the model what format to produce and match your prompt's own style to it.
- Control length with explicit statements ("answer in at most 5 sentences") and, where offered, a verbosity parameter. Effort does not reliably change visible length on every model.

## 7. Migrating prompts to a new model

1. Re-run your eval set unchanged on the new model with default settings.
2. Remove scaffolding written for older models: emphatic wording, repeated reminders, forced verification, reasoning scripts, prefills.
3. Sweep effort or thinking levels and output limits; do not carry the old level over.
4. Check instruction following: newer models can follow instructions more literally, so say explicitly when you want extra scope or thoroughness.
5. Check length and format drift; add one explicit sentence where the default style changed.
6. Re-test injection cases and tool-calling behavior.
7. Pin the snapshot you validated and record prompt version, model and settings together.

## 8. Quick before and after

Before (scripted reasoning, emphasis, negative framing):

```text
Think step by step. First list every line item. Second add them. Third compare to the total. You MUST NOT guess. NEVER output anything except the number.
```

After (goal, reason, success test, positive format):

```text
Check whether this invoice's stated total matches its line items. A mismatch holds up payment, so flag one only when the difference is certain. Reply with the computed total, the stated total, and the word "match" or "mismatch" on separate lines.

<invoice>
{{invoice_text}}
</invoice>
```

Set the effort or thinking level in the API call, not in the prompt text, and give the call enough output tokens for both the thinking and the three-line reply.
