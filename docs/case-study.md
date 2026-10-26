# A 24 KB input that became a 16 MB prompt

[简体中文](case-study.zh-CN.md) · [Run the reproduction](../examples/prompt-expansion/demo.mjs) · [Back to README](../README.md)

**Finding:** limiting a template and its input separately did not limit the final prompt. AI App Preflight's source-review workflow found this in [PromptCanary](https://github.com/mioyui20/prompt-canary), another app maintained by this repository's author. This is a maintainer case study, not an external customer testimonial or a claim of measured cost savings.

## What was reviewed

Source snapshot: [`db53b8e`](https://github.com/mioyui20/prompt-canary/tree/db53b8ecf071a8a16ef70b3f7b10fe17bf53be13). The app compares A/B prompts using a local single-user server and also publishes a static, prerecorded demo. The finding concerns its live evaluation path. The static demo does not send these prompts to a provider.

| Step | Pinned source evidence | What it establishes |
| --- | --- | --- |
| Validate raw fields | [core.js:37](https://github.com/mioyui20/prompt-canary/blob/db53b8ecf071a8a16ef70b3f7b10fe17bf53be13/public/core.js#L37-L44), [core.js:59](https://github.com/mioyui20/prompt-canary/blob/db53b8ecf071a8a16ef70b3f7b10fe17bf53be13/public/core.js#L59) | Each template and input can contain up to 12,000 JavaScript characters |
| Expand placeholders | [core.js:132](https://github.com/mioyui20/prompt-canary/blob/db53b8ecf071a8a16ef70b3f7b10fe17bf53be13/public/core.js#L132-L135) | Every `{{input}}` is replaced with the full input |
| Start model work | [core.js:275](https://github.com/mioyui20/prompt-canary/blob/db53b8ecf071a8a16ef70b3f7b10fe17bf53be13/public/core.js#L275-L278) | The rendered prompt goes directly to the executor |
| Send provider request | [provider.js:24](https://github.com/mioyui20/prompt-canary/blob/db53b8ecf071a8a16ef70b3f7b10fe17bf53be13/src/provider.js#L24-L26) | The output-token cap does not constrain input expansion |

The v1.0 evidence helper returned **zero leads** in the original review. The issue was found by following source and doing the size calculation. v1.1 adds navigation markers for `replaceAll`, `join`, byte measurements and raw `fetch`; it still does not prove semantic input bounds automatically.

## Reproduce locally in one minute

With Node.js 20.19+ and a checkout of this repository:

```bash
node examples/prompt-expansion/demo.mjs
node examples/prompt-expansion/demo.mjs --lang zh
node examples/prompt-expansion/demo.mjs --json
```

No package installation or model key is needed. The demo allocates the roughly 16 MB unguarded prompt once and passes it to a counting stub. It never sends a network request. The guarded path rejects before constructing the expanded prompt.

| Measurement | Result |
| --- | ---: |
| Template: `"{{input}}".repeat(1333)` | 11,997 characters |
| Input: `"x".repeat(12000)` | 12,000 characters |
| Minimal fixture JSON containing those two fields | 24,023 bytes |
| Unguarded rendered prompt | 15,996,000 bytes |
| Unguarded / guarded stub calls for the large input | 1 / 0 |
| Guarded normal bilingual input | Accepted |
| Real provider calls | 0 |

The 24,023-byte figure describes the **minimal fixture**, not a full PromptCanary HTTP request. A separate local check against the pinned app used a 24,171-byte valid test suite and its actual `validateSuite` + `runEvaluation` functions. With an injected executor it recorded two A/B calls of 15,996,000 and 12,000 bytes. No live provider was involved.

## The fix and its limits

The [guarded renderer](../examples/after/template-budget.mjs) calculates:

```text
rendered bytes = fixed template UTF-8 bytes + placeholder count × input UTF-8 bytes
```

It rejects over-budget combinations before joining the expanded text or starting provider work. The example chooses **32,768 bytes** to make the boundary visible. That is a demonstration policy, not a recommended universal model limit. Production callers should bound raw fields too, include history/retrieval/system context in their final budget, and use model-specific token accounting where needed.

The [regression checks](../tests/prompt-expansion.test.mjs) verify rejected requests make zero stub calls, normal bilingual requests still work, and exact UTF-8 byte boundaries are respected. The [renderer checks](../tests/template-budget.test.mjs) preserve literal `$&` and repeated placeholders.

**Severity in the reviewed context:** a P2, non-blocking resource/cost-budget improvement for the documented local tool. A public billable endpoint would need a new assessment. This is not evidence that a provider accepts the 16 MB prompt, bills for it, or that an attacker exploited a deployed service. Bytes are not tokens or currency.

**Publication scope:** this repository contains the reproduction and a tested remediation example. It does not claim that the fix has been integrated or released in PromptCanary. References remain pinned even if that repository changes later.

## Try the same review on your app

Ask your coding agent:

```text
Use $ai-app-preflight to trace raw inputs through templates, history and retrieval
to the final provider request. Find where the final budget is enforced.
Report confirmed findings separately from deployment questions.
Use local stubs for any authorized retest; do not call paid models.
```

Use `/ai-app-preflight` in Claude Code. [Share a redacted review outcome](https://github.com/mioyui20/ai-app-preflight/issues/new?template=trial-feedback.yml), including a no-findings result or installation friction. That feedback will guide the next change.
