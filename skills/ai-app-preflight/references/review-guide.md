# AI endpoint review guide

Use the sections relevant to the routes under review. These are evidence questions, not mandatory features for every app.

## 1. Provider credentials crossing into a client

**Inspect:** browser imports, client components, public environment prefixes, SDK client options, API responses, and logging around provider setup. Resolve whether a value is a provider secret, a publishable/anonymous key, a fixture, or a server-only setting. Public env names are a lead; actual bundling and use determine exposure. A server file can reference a badly named variable without proving that any browser bundle includes it.

**Confirm:** demonstrate the secret's path to client-accessible code or a response using source, build configuration or a redacted existing artifact. Do not build an untrusted project just to search for a key. In reports use the variable name, never the value. If an actual secret was published, recommend rotation by the owner; do not perform it during an ordinary review.

**Retest:** make the browser call a server-side endpoint. Verify the provider key is absent from client configuration and responses; preserve public keys that the service intentionally permits. Test with fake values, never live credentials.

## 2. Billable work without an enforced resource boundary

**Inspect:** caller authentication where required, anonymous/user quotas, prompt byte/token limits, bounded output generation, concurrency, retry budgets, and bounded tool/agent loops. Count all provider calls across fallbacks and retries. Identify whether quotas live in code, an API gateway, a provider budget, or another service.

Check the final model request after template substitution, retrieved context and conversation history are added. Small raw fields can multiply into a much larger prompt when a placeholder occurs repeatedly. Enforce the assembled-input budget before allocating or sending oversized expansions; an HTTP body limit alone does not establish this boundary.

**Do not infer:** an outbound `Authorization: Bearer ...` header does not authenticate an inbound user. A per-process counter does not establish a shared quota across server replicas. An output-token cap does not bound request volume or input context. Missing code keywords do not establish the absence of gateway limits.

**Retest:** missing authentication when the route requires it; over-limit body; exhausted quota; parallel requests against the same quota; provider rejection and retries. Use a counting stub and verify rejected requests do not start model work. Avoid sending concurrency tests to real providers or public endpoints.

## 3. Deadlines, cancellation and streaming cleanup

**Inspect:** the signal/deadline used by the actual provider call, SDK retry/timeouts, client disconnection propagation, in-stream errors, and resource release on success, failure, timeout and abort. Trace request IDs or reservations through cleanup.

**Do not infer:** a timer elsewhere in the repository protects this call; aborting the browser fetch necessarily stops the upstream; a `try/catch` around response creation handles later stream errors; or a finish hook runs on abort. A best-effort abort cannot undo work already processed by the provider.

**Retest:** a stub that never finishes, a disconnect before the first token, a disconnect after a chunk, a mid-stream provider error, and retry exhaustion. Assert no new queued jobs start after abort and that cleanup occurs once. Read the installed SDK version's documentation when hook semantics matter.

Primary background: [AI SDK error handling](https://ai-sdk.dev/docs/ai-sdk-core/error-handling), [timeouts and cancellation settings](https://ai-sdk.dev/docs/ai-sdk-core/settings). These are SDK-specific examples, not claims that every framework has the same hooks.

## 4. Structured outputs crossing an application boundary

**Inspect:** strict JSON parsing, object/array types, required fields, length/range limits, enums, and application-specific decisions. Determine whether validated data is actually used, or whether code validates one value and returns the raw model result. Check partial output, refusals, schema errors and exception responses.

**Do not infer:** `JSON.parse`, `json.loads`, a TypeScript cast, a prompt saying "return JSON", or schema mode alone proves that application input is trustworthy. Schema conformance does not prove factual or business correctness. A classifier returning a valid category can still be wrong.

**Retest:** invalid JSON, a valid scalar instead of an object, missing fields, wrong field types, extra fields where forbidden, extreme strings, invalid enum values, and a valid-shaped but inappropriate business action. Verify the route fails gracefully before rendering or side effects. Keep money movement and other external actions out of fixture tests.

Primary background: [AI SDK structured data](https://ai-sdk.dev/docs/ai-sdk-core/generating-structured-data), [OWASP unbounded consumption](https://genai.owasp.org/llmrisk/llm102025-unbounded-consumption/).

## Compact report shape

```text
Decision: verification needed
Scope: selected routes, deployment assumptions, files skipped

P1 · confirmed · server/chat.ts:42
Failure: an over-limit request starts provider work before the limit is checked.
Fix: enforce the existing body cap before starting that work.
Retest: submit a limit+1 fixture; expect rejection and zero stub calls.

Controls: credentials [verified], resource limits [open gateway question],
lifecycle [verified timeout, cancellation untested], output [verified shape only].
Validation: checks actually executed; tests proposed but not run.
```

Use the user's language and actual findings. The example is not a required verdict.
