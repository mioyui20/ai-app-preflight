# AI App Preflight

[简体中文](README.zh-CN.md) · [Install](#install) · [Try the demo](#try-it-without-a-model-key)

A Skill for asking your AI coding assistant to review an app's AI endpoints before release. It helps trace exposed API keys, oversized model requests, requests that keep running after cancellation, and model output used without validation.

Use it when adding a chat endpoint, changing prompt assembly, or preparing a local AI prototype for other users. The result is a review with **file locations, failure scenarios, suggested fixes and retest steps**.

## What it checks

| Your question | What the review follows |
| --- | --- |
| Could my model API key reach the browser? | Where credentials are loaded and where they are sent |
| Can a small request start too much model work? | Final prompts, quotas, output limits, retries and concurrency |
| Does work stop when the user leaves? | Timeouts, cancellation and stream cleanup |
| Can an unexpected model response break the app? | JSON parsing, field validation and use of the result |

Tell the assistant whether the app is a local tool, a private service or a public demo. That context changes which controls it needs.

## Install

You need an AI coding assistant that supports Skills. For installation with the [skills CLI](https://github.com/vercel-labs/skills), use Node.js 22.20+ and run this in your app's project folder:

```bash
npx skills add mioyui20/ai-app-preflight --skill ai-app-preflight
```

Choose your assistant when prompted.

For manual installation, download and extract `ai-app-preflight-skill-*.zip` from [Releases](https://github.com/mioyui20/ai-app-preflight/releases/latest). Copy the complete `ai-app-preflight` folder to the location for your assistant.

| Assistant | Location inside your app project |
| --- | --- |
| Codex | `.agents/skills/ai-app-preflight/` |
| Claude Code | `.claude/skills/ai-app-preflight/` |

Keep the scripts and reference files with `SKILL.md`. If you downloaded the full source instead, the folder is under `skills/ai-app-preflight`. See the [Codex](https://learn.chatgpt.com/docs/build-skills) or [Claude Code](https://code.claude.com/docs/en/skills) guide if it does not appear.

## Run your first review

Open your app project in your assistant and send:

```text
Use $ai-app-preflight to review this app's AI endpoints before release.
It is a local tool for one person. Give file locations, confirmed problems,
open questions and local retest steps. Do not change files or call real models.
```

Replace the deployment description with your own. In Claude Code, use `/ai-app-preflight` instead of `$ai-app-preflight`. You can ask in English or Chinese.

Start with the confirmed findings. If a result depends on your gateway, hosting or provider settings, supply that context before treating it as a bug. You can then ask the assistant to fix a specific finding and verify it with a local stub.

[See a sample review](docs/example-review.md) · [Read a real case](docs/case-study.md)

## Try it without a model key

Run the standalone example with Node.js 20.19+.

```bash
git clone https://github.com/mioyui20/ai-app-preflight.git
cd ai-app-preflight
node examples/prompt-expansion/demo.mjs
```

It reproduces a problem found in the maintainer's PromptCanary app. Roughly 24 KB of input can expand into a 16 MB prompt. The demo uses a local substitute for the model and counts the calls.

| Oversized input | Before the guard | With the example guard |
| --- | ---: | ---: |
| Prompt bytes submitted | 15,996,000 | 0 |
| Stub calls | 1 | 0 |

Normal bilingual input still works. Add `--lang zh` for Chinese or `--json` for structured output. The demo makes no real model calls; byte counts are not token or cost estimates. [Case details](docs/case-study.md).

## Optional: collect source locations yourself

Run this from the cloned repository with Python 3.10+.

```bash
python skills/ai-app-preflight/scripts/collect_evidence.py /path/to/your/app
```

Add `--lang zh` for Chinese or `--format json` for JSON. The helper reads source text without running your app or making network requests. It skips environment and common credential files and reports locations without source snippets or key values.

Use the output to find code worth reviewing. Check the scan coverage and skipped files, then read the surrounding code before deciding whether a lead is an issue. The full Skill uses the model and tools provided by your assistant.

## Feedback

[Share your first review](https://github.com/mioyui20/ai-app-preflight/issues/new?template=trial-feedback.yml) or [report a false positive or missed issue](https://github.com/mioyui20/ai-app-preflight/issues/new?template=feedback.yml). Include your assistant, version and a small redacted example. Keep credentials and private source out of public reports.

[Updates](CHANGELOG.md) · [Contributing](CONTRIBUTING.md) · [MIT license](LICENSE)
