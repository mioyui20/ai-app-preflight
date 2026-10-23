// Corrected teaching fixture, NOT a complete production service.
// authenticate/admit must be supplied by the application. In production,
// admit must atomically enforce shared quotas/concurrency before provider work.
const MAX_BODY_BYTES = 8192;
const MAX_PROMPT_CHARACTERS = 2000;
const categories = new Set(["billing", "other"]);

async function readSmallJson(request) {
  if (!request.body) throw new Error("body");
  const reader = request.body.getReader();
  const chunks = [];
  let length = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      length += value.byteLength;
      if (length > MAX_BODY_BYTES) {
        await reader.cancel();
        throw new RangeError("body size");
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  const bytes = new Uint8Array(length);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
  return JSON.parse(new TextDecoder().decode(bytes));
}

function validateReply(content) {
  const parsed = JSON.parse(content);
  if (!parsed || Array.isArray(parsed) || typeof parsed !== "object" ||
      typeof parsed.answer !== "string" || parsed.answer.length > 1000 ||
      !categories.has(parsed.category)) throw new Error("reply shape");
  // Return a fresh, allowlisted value rather than the unvalidated object.
  return { answer: parsed.answer, category: parsed.category };
}

export async function handleChat(request, { client, authenticate, admit, timeoutMs = 15000 }) {
  let user;
  try { user = await authenticate(request); }
  catch { return Response.json({ error: "Authentication unavailable" }, { status: 503 }); }
  if (!user || typeof user.id !== "string" || !user.id) {
    return Response.json({ error: "Authentication required" }, { status: 401 });
  }
  let body;
  try { body = await readSmallJson(request); }
  catch (error) {
    return Response.json({ error: "Invalid request body" }, { status: error instanceof RangeError ? 413 : 400 });
  }
  if (!body || typeof body.prompt !== "string" || !body.prompt.trim() ||
      [...body.prompt].length > MAX_PROMPT_CHARACTERS) {
    return Response.json({ error: "Invalid prompt" }, { status: 400 });
  }
  // A quota reservation is an application integration point, not a keyword proof.
  let allowed;
  try { allowed = await admit(user.id); }
  catch { return Response.json({ error: "Quota service unavailable" }, { status: 503 }); }
  if (allowed !== true) return Response.json({ error: "Quota exhausted" }, { status: 429 });

  const deadline = AbortSignal.timeout(timeoutMs);
  const signal = AbortSignal.any([request.signal, deadline]);
  try {
    signal.throwIfAborted();
    const result = await client.chat.completions.create({
      model: "fixture-model",
      messages: [{ role: "user", content: body.prompt }],
      max_tokens: 256,
    }, { signal, maxRetries: 0 });
    signal.throwIfAborted();
    return Response.json(validateReply(result.choices?.[0]?.message?.content));
  } catch {
    if (request.signal.aborted) return Response.json({ error: "Request canceled" }, { status: 499 });
    if (deadline.aborted) return Response.json({ error: "Provider timed out" }, { status: 504 });
    return Response.json({ error: "Invalid or failed provider response" }, { status: 502 });
  }
}
