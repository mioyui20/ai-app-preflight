# Contributing / 贡献指南

Keep the Skill narrowly focused on AI endpoint release reviews. A new keyword is useful only when it helps an agent locate meaningful evidence; it must not turn absence into a vulnerability claim.

请保持 AI 接口预检的范围。新增关键词必须有助于定位有意义的证据，不能把未命中当作缺少安全措施。

- Helper / 脚本: Python 3.10+, standard library only / 仅标准库。
- Evidence / 证据: relative paths, line numbers and symbol names; no source snippets or secret values / 相对路径、行号、符号名，不输出源码或密钥值。
- Fixtures / 示例: clearly labeled, fake data, no external calls / 明确标注、假数据、不调用外部服务。
- Instructions / 指令: preserve user scope, deployment context and existing authorization / 保留用户范围、实际部署背景和已有授权。

Run / 验证：

```text
python -B -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/routes.test.mjs tests/template-budget.test.mjs tests/prompt-expansion.test.mjs
node examples/prompt-expansion/demo.mjs --lang zh
```

For a new rule, include one realistic positive case, a plausible false positive, and a regression check for the actual output or behavior. For a workflow change, independently try the Skill on a small real repository; do not supply the evaluator your intended findings. An automated test count is not a measure of security coverage.

新增规则请包括真实使用场景、合理误报场景，以及实际输出或行为的回归检查。工作流变更应在真实小仓库上独立试用，不向评估者透露预期结论。测试数量不代表安全覆盖程度。

For case studies, pin the source commit, separate source review from runtime checks, and disclose if the example comes from the maintainer's own app. Claim a deployed fix only when it was actually shipped. Keep English and Chinese entry points in sync.

案例请固定源码提交，区分静态审查与运行验证，注明是否来自维护者自己的项目。只有实际发布后才能声称上游已修复。中英文入口应同步。

First-time users: [share one review outcome](https://github.com/mioyui20/ai-app-preflight/issues/new?template=trial-feedback.yml). Useful feedback includes installation friction, one confirmed issue or a false positive, and whether you would use the Skill again. Remove secrets and private source before sharing.

首次试用可[反馈一次审查结果](https://github.com/mioyui20/ai-app-preflight/issues/new?template=trial-feedback.yml)：安装卡点、确认的问题或误报，以及是否愿意再次使用。请先移除密钥和私有源码。
