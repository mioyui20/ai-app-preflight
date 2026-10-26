import { parseArgs } from "node:util";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { renderPrompt } from "./unguarded.mjs";
import { renderBudgeted } from "../after/template-budget.mjs";

const BUDGET = 32768; // Demonstration policy, not a universal model limit.

export function simulateRequest(renderer, template, input, budget = BUDGET) {
  let providerCalls = 0;
  let submittedBytes = 0;
  // Counting stub: no SDK, credentials, fetch, sockets or external effects.
  function provider(prompt) {
    providerCalls += 1;
    submittedBytes = Buffer.byteLength(prompt, "utf8");
  }
  try {
    provider(renderer(template, input, budget));
    return { outcome: "submitted_to_stub", providerCalls, submittedBytes };
  } catch (error) {
    if (!(error instanceof RangeError)) throw error;
    return { outcome: "blocked_before_provider", providerCalls, submittedBytes };
  }
}

export function runDemo() {
  const template = "{{input}}".repeat(1333);
  const input = "x".repeat(12000);
  const before = simulateRequest(renderPrompt, template, input);
  const after = simulateRequest(renderBudgeted, template, input);
  const normal = simulateRequest(renderBudgeted, "Say {{input}} twice: {{input}}", "你好 $&");
  const verified = template.length <= 12000 && input.length <= 12000
    && before.submittedBytes === 15996000 && before.providerCalls === 1
    && after.outcome === "blocked_before_provider" && after.providerCalls === 0
    && normal.outcome === "submitted_to_stub" && normal.providerCalls === 1;
  return {
    schema_version: 1,
    fixture: "prompt-expansion",
    source_commit: "db53b8ecf071a8a16ef70b3f7b10fe17bf53be13",
    template_characters: template.length,
    input_characters: input.length,
    fixture_json_bytes: Buffer.byteLength(JSON.stringify({ template, input }), "utf8"),
    prompt_budget_bytes: BUDGET,
    before, after, normal,
    verified,
    real_provider_calls: 0,
  };
}

export function formatDemo(report, lang = "en") {
  const zh = lang === "zh";
  return [
    zh ? "AI App Preflight — 请求膨胀复现" : "AI App Preflight — prompt expansion reproduction",
    zh ? "本地计数替身；真实模型调用：0" : "Local counting stub; real model calls: 0",
    "",
    `${zh ? "模板字符数" : "Template characters"}: ${report.template_characters}`,
    `${zh ? "输入字符数" : "Input characters"}: ${report.input_characters}`,
    `${zh ? "最小示例 JSON 字节数" : "Minimal fixture JSON bytes"}: ${report.fixture_json_bytes}`,
    `${zh ? "示例提示词预算（字节）" : "Example prompt budget (bytes)"}: ${report.prompt_budget_bytes}`,
    "",
    `${zh ? "修复前：提交字节数" : "Before: submitted bytes"} = ${report.before.submittedBytes}; ${zh ? "替身调用" : "stub calls"} = ${report.before.providerCalls}`,
    `${zh ? "修复后：提交字节数" : "After: submitted bytes"} = ${report.after.submittedBytes}; ${zh ? "替身调用" : "stub calls"} = ${report.after.providerCalls}`,
    `${zh ? "正常中英文输入：替身调用" : "Normal bilingual input: stub calls"} = ${report.normal.providerCalls}`,
    "",
    `${zh ? "复现断言" : "Reproduction assertions"}: ${report.verified ? "PASS" : "FAIL"}`,
    zh ? "字节数不等于 Token 或费用。此示例不修改上游项目。" : "Bytes are not tokens or cost. This fixture does not modify the upstream project.",
    "",
  ].join("\n");
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  try {
    const { values } = parseArgs({ options: {
      lang: { type: "string", default: "en" }, json: { type: "boolean", default: false },
    } });
    if (!["en", "zh"].includes(values.lang)) throw new Error("--lang must be en or zh");
    const report = runDemo();
    process.stdout.write(values.json ? JSON.stringify(report, null, 2) + "\n" : formatDemo(report, values.lang));
    if (!report.verified) process.exitCode = 1;
  } catch (error) {
    process.stderr.write(`${error.message}\nUsage: node examples/prompt-expansion/demo.mjs [--lang en|zh] [--json]\n`);
    process.exitCode = 2;
  }
}
