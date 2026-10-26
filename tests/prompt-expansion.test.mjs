import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { runDemo, simulateRequest } from "../examples/prompt-expansion/demo.mjs";
import { renderBudgeted } from "../examples/after/template-budget.mjs";

const script = fileURLToPath(new URL("../examples/prompt-expansion/demo.mjs", import.meta.url));

test("real expansion shape reaches a stub before the fix and is rejected after it", () => {
  const report = runDemo();
  assert.equal(report.verified, true);
  assert.equal(report.fixture_json_bytes, 24023);
  assert.equal(report.before.submittedBytes, 15996000);
  assert.equal(report.before.providerCalls, 1);
  assert.deepEqual(report.after, { outcome: "blocked_before_provider", providerCalls: 0, submittedBytes: 0 });
  assert.equal(report.normal.providerCalls, 1);
});

test("UTF-8 boundary rejection happens before the provider stub is called", () => {
  assert.equal(simulateRequest(renderBudgeted, "{{input}}", "你好", 6).providerCalls, 1);
  assert.equal(simulateRequest(renderBudgeted, "{{input}}", "你好", 5).providerCalls, 0);
});

test("demo CLI works from another directory in both languages and as JSON", () => {
  for (const lang of ["en", "zh"]) {
    const result = spawnSync(process.execPath, [script, "--lang", lang], { encoding: "utf8", cwd: fileURLToPath(new URL("..", import.meta.url)) });
    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /15996000/);
    assert.match(result.stdout, lang === "zh" ? /真实模型调用：0/ : /real model calls: 0/);
    assert.match(result.stdout, /PASS/);
  }
  const json = spawnSync(process.execPath, [script, "--json"], { encoding: "utf8" });
  assert.equal(json.status, 0, json.stderr);
  assert.equal(JSON.parse(json.stdout).after.providerCalls, 0);
});

test("CLI rejects unsupported options rather than running a different demo", () => {
  for (const args of [["--lang", "fr"], ["--url", "https://example.invalid"]]) {
    const result = spawnSync(process.execPath, [script, ...args], { encoding: "utf8" });
    assert.equal(result.status, 2);
    assert.equal(result.stdout, "");
  }
});
