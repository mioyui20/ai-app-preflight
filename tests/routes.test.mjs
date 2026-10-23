import test from "node:test";
import assert from "node:assert/strict";
import { handleChat as before } from "../examples/before/route.mjs";
import { handleChat as after } from "../examples/after/route.mjs";

function request(body = { prompt: "Help with my invoice" }, options = {}) {
  return new Request("http://localhost/api/chat", {
    method: "POST",
    body: JSON.stringify(body),
    headers: { "Content-Type": "application/json" },
    ...options,
  });
}
function dependencies(output = '{"answer":"Check your invoice","category":"billing"}') {
  const calls = [];
  return {
    calls,
    authenticate: async () => ({ id: "fixture-user" }),
    admit: async () => true,
    client: {
      chat: { completions: { create: async (body, options) => {
        calls.push({ body, options });
        return { choices: [{ message: { content: output } }] };
      } } },
    },
  };
}

test("before fixture accepts unvalidated model data", async () => {
  const deps = dependencies('42');
  const response = await before(request(), deps);
  assert.equal(await response.json(), 42);
  assert.equal(deps.calls.length, 1);
});
test("after rejects unauthenticated requests before provider work", async () => {
  const deps = dependencies(); deps.authenticate = async () => null;
  assert.equal((await after(request(), deps)).status, 401);
  assert.equal(deps.calls.length, 0);
});
test("after rejects quota exhaustion before provider work", async () => {
  const deps = dependencies(); deps.admit = async () => false;
  assert.equal((await after(request(), deps)).status, 429);
  assert.equal(deps.calls.length, 0);
});
test("quota service errors fail closed without provider work", async () => {
  const deps = dependencies(); deps.admit = async () => { throw new Error("offline"); };
  assert.equal((await after(request(), deps)).status, 503);
  assert.equal(deps.calls.length, 0);
});
test("after rejects large streamed bodies regardless of Content-Length", async () => {
  const deps = dependencies();
  assert.equal((await after(request({ prompt: "x".repeat(9000) }), deps)).status, 413);
  assert.equal(deps.calls.length, 0);
});
test("after rejects overlong prompts and malformed bodies", async () => {
  const deps = dependencies();
  assert.equal((await after(request({ prompt: "x".repeat(2001) }), deps)).status, 400);
  assert.equal((await after(request(null), deps)).status, 400);
  assert.equal((await after(request({ prompt: " " }), deps)).status, 400);
  assert.equal(deps.calls.length, 0);
});
test("after validates and returns an allowlisted result", async () => {
  const deps = dependencies('{"answer":"Check your invoice","category":"billing","extra":"not returned"}');
  const response = await after(request(), deps);
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { answer: "Check your invoice", category: "billing" });
  assert.equal(deps.calls[0].body.max_tokens, 256);
  assert.equal(deps.calls[0].options.maxRetries, 0);
  assert.ok(deps.calls[0].options.signal instanceof AbortSignal);
});
for (const output of ['not JSON', '42', '{"answer":12,"category":"billing"}', '{"answer":"ok","category":"invalid"}']) {
  test(`after handles invalid provider output: ${output}`, async () => {
    assert.equal((await after(request(), dependencies(output))).status, 502);
  });
}
test("stalled provider is aborted by the deadline", async () => {
  const deps = dependencies();
  deps.timeoutMs = 30;
  deps.client.chat.completions.create = (body, { signal }) => new Promise((resolve, reject) => {
    const hold = setTimeout(() => resolve({}), 1000);
    signal.addEventListener("abort", () => { clearTimeout(hold); reject(signal.reason); }, { once: true });
  });
  assert.equal((await after(request(), deps)).status, 504);
});
test("caller abort propagates to an in-flight provider request", async () => {
  const controller = new AbortController();
  const deps = dependencies(); let providerAborted = false;
  deps.client.chat.completions.create = (body, { signal }) => new Promise((resolve, reject) => {
    signal.addEventListener("abort", () => { providerAborted = true; reject(signal.reason); }, { once: true });
    controller.abort();
  });
  assert.equal((await after(request(undefined, { signal: controller.signal }), deps)).status, 499);
  assert.equal(providerAborted, true);
});
test("upstream failures return a bounded error without secret details", async () => {
  const deps = dependencies();
  deps.client.chat.completions.create = async () => { throw new Error("sensitive provider details"); };
  const response = await after(request(), deps);
  assert.equal(response.status, 502);
  assert.ok(!(await response.text()).includes("sensitive provider details"));
});
