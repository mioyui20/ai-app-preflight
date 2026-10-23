import test from "node:test";
import assert from "node:assert/strict";
import { renderBudgeted } from "../examples/after/template-budget.mjs";

test("repeated placeholders cannot multiply small raw fields beyond the final budget", () => {
  const template = "{{input}}".repeat(1333);
  const input = "x".repeat(12000);
  assert.ok(template.length < 12000);
  assert.throws(() => renderBudgeted(template, input), RangeError);
});
test("budgeting uses UTF-8 bytes and preserves literal replacement text", () => {
  assert.equal(renderBudgeted("{{input}}", "你好", 6), "你好");
  assert.throws(() => renderBudgeted("{{input}}", "你好", 5), RangeError);
  assert.equal(renderBudgeted("{{input}} {{input}}", "$&"), "$& $&");
});
