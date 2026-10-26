<h1 align="center">AI App Preflight</h1>
<p align="center"><strong>Find AI request failures before users do.</strong><br>An Agent Skill that traces keys, prompt budgets, cancellation and model output to file:line evidence.</p>
<p align="center"><a href="README.zh-CN.md">简体中文</a> · <a href="#one-minute-no-key-demo">Run the demo</a> · <a href="#install-the-skill">Install</a> · <a href="docs/case-study.md">Real case study</a> · <a href="skills/ai-app-preflight/SKILL.md">Read the Skill</a></p>
<p align="center"><a href="https://github.com/mioyui20/ai-app-preflight/actions/workflows/ci.yml"><img src="https://github.com/mioyui20/ai-app-preflight/actions/workflows/ci.yml/badge.svg" alt="CI"></a> <img src="https://img.shields.io/badge/Agent_Skills-compatible-7c8e64" alt="Agent Skills format"> <img src="https://img.shields.io/badge/helper-Python_3.10%2B-3678a8" alt="Python 3.10 or newer"> <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT license"></a></p>

An AI feature can answer the happy-path demo while still leaking a provider key, accepting unlimited billable work, ignoring a disconnect, or trusting malformed model output.

**A real example:** a roughly **24 KB test suite produced a 16 MB prompt** in our own PromptCanary app. This Skill's review traced the expansion; the included fix rejects it before model work. [Read the pinned evidence and limits](docs/case-study.md).

This Skill guides an AI coding agent through **four concrete review areas**, then asks for file/line evidence, a failure scenario, a proportionate fix, and a local retest. It respects the actual deployment: a localhost utility does not automatically need the same authentication stack as a public service.

| Area | What the agent traces |
| --- | --- |
| Credential boundary | Provider secrets reaching client bundles or API responses |
| Spending boundary | Caller policy, quotas, final rendered prompts, output limits, retries and concurrency |
| Request lifecycle | Deadlines, disconnect propagation, stream errors and cleanup |
| Output boundary | JSON parsing versus schema constraints and business validation |

**The helper collects leads; the agent verifies them.** A marker is not a confirmed vulnerability. Zero matches are not a safety certificate. No numeric safety score, automatic deployment, or paid model calls are included.

## One-minute no-key demo

Node.js **20.19+**; no npm install, credentials or network calls after cloning:

```bash
git clone https://github.com/mioyui20/ai-app-preflight.git
cd ai-app-preflight
node examples/prompt-expansion/demo.mjs
```

| Same input | Before | With the example budget |
| --- | ---: | ---: |
| Bytes sent to the local model stub | 15,996,000 | 0 |
| Stub calls for the oversized prompt | 1 | 0 |
| Normal bilingual input | — | Accepted |

The demo runs the unguarded renderer and the guarded one, then checks the results. Add `--lang zh` for Chinese or `--json` for structured output. **Real model calls: zero.** The 32 KiB budget is an example policy; bytes are not tokens or measured spending. The reproduction does not update PromptCanary itself.

## Install the Skill

### With the skills CLI

With Node.js **22.20+**, run in the project where you want to use it:

```bash
npx skills add mioyui20/ai-app-preflight --skill ai-app-preflight
```

Choose your supported coding agent when prompted. The installation tooling is from the [open skills CLI](https://github.com/vercel-labs/skills); it is not a dependency of the helper.

### Manual, project-local installation

Clone or [download a release](https://github.com/mioyui20/ai-app-preflight/releases), then copy the **entire** `skills/ai-app-preflight` folder into your project's skill directory:

| Agent | Project directory |
| --- | --- |
| Codex | `<your-project>/.agents/skills/ai-app-preflight/` |
| Claude Code | `<your-project>/.claude/skills/ai-app-preflight/` |

Keep the scripts, references and license together with `SKILL.md`. Follow the host's skill discovery instructions if the new skill does not immediately appear. Format compatibility does not certify every agent/version; Codex-oriented behavior was independently tried on a real repository.

Example invocation in Codex:

```text
Use $ai-app-preflight to review this app's AI endpoints before release.
Give file:line evidence, open deployment questions, and local retests.
Do not call real models or change the app.
```

In Claude Code, use `/ai-app-preflight` followed by your review request. Chinese requests work too; the instructions tell the agent to answer in the user's language. This package is a standalone Skill, not an app-store plugin or a desktop executable.

## Review your own app

The helper needs **Python 3.10+**, with no pip packages. Use `python3` or `py -3` if that is your interpreter command.

```bash
python skills/ai-app-preflight/scripts/collect_evidence.py examples/before
python skills/ai-app-preflight/scripts/collect_evidence.py examples/after --lang zh
python skills/ai-app-preflight/scripts/collect_evidence.py /path/to/your/app --format json
```

The first fixture exposes review leads at `client.mjs:4` and `client.mjs:5`. The corrected fixture adds guarded request handling, but it is **not a complete production service**: the host must supply real authentication, atomic shared quotas and a compatible provider adapter.

[English evidence example](docs/evidence.en.md) · [中文证据示例](docs/evidence.zh-CN.md) · [Example review](docs/example-review.md).

To run the behavioral examples, Node.js 20.19+ is enough. No npm install is needed:

```bash
node --test tests/routes.test.mjs tests/template-budget.test.mjs tests/prompt-expansion.test.mjs
python -B -m unittest discover -s tests -p 'test_*.py' -v
```

The route tests use injected stubs, not commercial models. They cover rejection before model work, quota failure, oversized bodies, wrong-shaped outputs, timeout, cancellation and error redaction. The template example blocks repeated-placeholder expansion before constructing a large prompt.

For a first review, install the Skill in your app and use the request above. Read the agent's source-backed findings and open questions, then [share one redacted outcome](https://github.com/mioyui20/ai-app-preflight/issues/new?template=trial-feedback.yml). A no-findings result, missed issue or installation problem is useful too. No report is uploaded automatically.

## What you receive

```text
skills/ai-app-preflight/
├── SKILL.md                     Agent instructions and scope
├── agents/openai.yaml           Codex UI metadata
├── scripts/collect_evidence.py  Offline evidence collection
├── references/review-guide.md   Conditional review guidance
└── LICENSE.txt
```

The helper outputs JSON or English/Chinese Markdown with relative file locations and line numbers. It never includes source lines or credential values. `leads` identify review candidates; `signals` locate related code. Provider Authorization headers and caller-authentication markers are distinguished, but neither proves caller policy is correctly enforced. JSON parsing is separate from schema markers; manual validators may produce no schema marker at all.

In v1.1, `network_call`, `input_assembly` and `input_measurement` also locate raw `fetch`, joins/replacements and byte measurements. These neutral markers can occur in ordinary non-AI code. An agent must trace their connection to a model request. Existing JSON fields and schema version 1 are preserved.

Exit `0` means evidence collection completed, including reports with leads; `2` means a usage or root-reading error. Partial scans can also exit `0`: always read `coverage.truncated`, skip reasons and limitations. This is not an automatic CI security gate.

## Read-only boundaries

- No target code import, install, execution, mutation or network access. The helper reads source text only.
- Skips `.env` variants, common credential/certificate files, dependency directories, build products and detected symlinks/junctions. Do not point it at a live credential store.
- Limits: 1,500 candidate files, 256 KiB/file, 8 MiB of actual reads, 500 evidence records, 20,000 entries and 24 directory levels.
- Static line matching can miss aliases, indirect calls, split lines, unrecognized languages and encoding variants; comments and strings can create false positives. Files can change during a scan. It is not a filesystem sandbox or an adversarial concurrent-mutation defense.
- Runtime gateway controls and deployment configuration may be outside the repository. Mark those as unknown instead of inventing missing controls.
- The agent still needs its normal permissions and a model supplied by its host. An offline helper does not make the AI agent itself an offline model.

## Contribute

Add a realistic failure fixture and an observable regression test with any new rule. Keep labels cautious, output redacted, scripts dependency-free, and the Skill narrowly scoped. See [CONTRIBUTING.md](CONTRIBUTING.md).

[What changed in v1.1](CHANGELOG.md) · [Report a reproduction or false positive](https://github.com/mioyui20/ai-app-preflight/issues/new?template=feedback.yml) · [First review feedback](https://github.com/mioyui20/ai-app-preflight/issues/new?template=trial-feedback.yml)

Background: [Agent Skills format](https://agentskills.io/specification), [Codex skills](https://learn.chatgpt.com/docs/build-skills), [Claude Code skills](https://code.claude.com/docs/en/skills), [OWASP unbounded consumption](https://genai.owasp.org/llmrisk/llm102025-unbounded-consumption/), and [AI SDK lifecycle guidance](https://ai-sdk.dev/docs/ai-sdk-core/error-handling). These references inform the review; this project is independent and not endorsed by those organizations.

MIT © 2026 [mioyui20](https://github.com/mioyui20)
