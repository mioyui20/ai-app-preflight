# Changelog / 更新记录

## 1.1.0 — 2026-10-26

- Add an English/Chinese, no-key reproduction of prompt expansion found in the maintainer's PromptCanary app. The 24,023-byte minimal fixture renders a 15,996,000-byte prompt; a pre-allocation budget blocks it before the provider stub.
- Add neutral evidence markers for raw `fetch`, input assembly and byte measurement. These help navigate source; they do not classify vulnerabilities or prove budgets are enforced.
- Clarify that confirmed non-blocking findings can coexist with a bounded “no blocker found” decision for a local tool.
- Add pinned source evidence, a bilingual case study, first-review feedback, and Windows Node CI. JSON evidence schema remains version 1 with additive signal kinds.

- 增加中英文免密钥复现：维护者自己的 PromptCanary 中，24,023 字节的最小示例可展开出 15,996,000 字节的提示词；示例预算会在调用替身前拒绝超限输入。
- 新增原生 `fetch`、输入拼接和字节测量的位置标记，仅辅助追踪代码，不自动认定漏洞或预算有效。
- 明确本地工具的非阻断问题与发布结论之间的区别。
- 补充固定提交的源码证据、双语案例、试用反馈入口和 Windows Node CI。证据 JSON 仍为 schema version 1，仅新增标记类型。

## 1.0.0 — 2026-10-23

Initial Skill, offline evidence collector, guarded endpoint fixtures, and English/Chinese documentation.

首版 Skill、离线证据脚本、带边界的接口示例及中英文文档。
