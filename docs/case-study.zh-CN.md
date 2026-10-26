# 24 KB 的输入，如何变成 16 MB 的提示词

[English](case-study.md) · [查看复现程序](../examples/prompt-expansion/demo.mjs) · [返回首页](../README.zh-CN.md)

**发现：**分别限制模板和输入长度，并没有限制最终提示词大小。AI App Preflight 的源码审查流程在 [PromptCanary](https://github.com/mioyui20/prompt-canary) 中发现了这个问题。两个项目均由同一维护者开发；这是自己的项目案例，不是外部客户评价，也没有测得真实费用节省。

## 审查了什么

固定源码版本：[`db53b8e`](https://github.com/mioyui20/prompt-canary/tree/db53b8ecf071a8a16ef70b3f7b10fe17bf53be13)。PromptCanary 通过本地单人服务比较 A/B 提示词，也提供使用预录数据的静态演示。本案例涉及真实评测模式的执行路径；静态演示不向服务商发送这些提示词。

| 环节 | 固定版本的源码依据 | 说明 |
| --- | --- | --- |
| 原始字段校验 | [core.js:37](https://github.com/mioyui20/prompt-canary/blob/db53b8ecf071a8a16ef70b3f7b10fe17bf53be13/public/core.js#L37-L44)、[core.js:59](https://github.com/mioyui20/prompt-canary/blob/db53b8ecf071a8a16ef70b3f7b10fe17bf53be13/public/core.js#L59) | 模板与输入分别最多 12,000 个 JavaScript 字符 |
| 占位符展开 | [core.js:132](https://github.com/mioyui20/prompt-canary/blob/db53b8ecf071a8a16ef70b3f7b10fe17bf53be13/public/core.js#L132-L135) | 每一个 `{{input}}` 都替换为完整输入 |
| 启动模型工作 | [core.js:275](https://github.com/mioyui20/prompt-canary/blob/db53b8ecf071a8a16ef70b3f7b10fe17bf53be13/public/core.js#L275-L278) | 展开后的文本直接交给执行器 |
| 构造服务商请求 | [provider.js:24](https://github.com/mioyui20/prompt-canary/blob/db53b8ecf071a8a16ef70b3f7b10fe17bf53be13/src/provider.js#L24-L26) | 输出 Token 上限没有约束输入膨胀 |

原始审查中，v1.0 的辅助脚本返回了 **0 条 leads**。问题来自 AI 沿源码追踪和计算长度，而非关键词规则直接命中。v1.1 新增 `replaceAll`、`join`、字节测量及原生 `fetch` 的导航标记，仍不自动证明最终预算是否有效。

## 一分钟本地复现

克隆本仓库并准备 Node.js 20.19+ 后运行：

```bash
node examples/prompt-expansion/demo.mjs --lang zh
node examples/prompt-expansion/demo.mjs
node examples/prompt-expansion/demo.mjs --json
```

无需安装依赖或配置模型密钥。程序会在未加保护的路径中实际构造一次约 16 MB 的提示词，并交给计数替身，不发送网络请求。加入预算的路径会在构造展开文本之前拒绝超限组合。

| 测量内容 | 结果 |
| --- | ---: |
| 模板：`"{{input}}".repeat(1333)` | 11,997 字符 |
| 输入：`"x".repeat(12000)` | 12,000 字符 |
| 仅包含这两个字段的最小示例 JSON | 24,023 字节 |
| 未限制的展开后提示词 | 15,996,000 字节 |
| 超限输入在修复前 / 后的替身调用次数 | 1 / 0 |
| 正常的中英文输入 | 修复后仍可通过 |
| 真实模型调用 | 0 |

24,023 字节指的是**最小示例**，不是完整的 PromptCanary HTTP 请求。维护者还对固定版本的实际 `validateSuite` 和 `runEvaluation` 做了独立本地复测：一个 24,171 字节的合法测试集，通过注入的执行器记录到两次 A/B 调用，提示词分别为 15,996,000 和 12,000 字节。没有连接真实服务商。

## 如何修复，以及修复范围

[带预算的渲染器](../examples/after/template-budget.mjs) 先计算：

```text
展开后字节数 = 模板固定部分的 UTF-8 字节数 + 占位符数量 × 输入 UTF-8 字节数
```

超限时，在拼接大字符串和启动模型工作之前拒绝。本示例选用 **32,768 字节**，方便观察边界；它是演示策略，不是通用模型上限。实际应用仍应限制原始字段，将历史消息、检索结果和系统提示词纳入最终预算，必要时结合模型的 Token 统计。

[回归测试](../tests/prompt-expansion.test.mjs) 验证超限请求的替身调用数为零、正常中英文输入可用，以及 UTF-8 字节边界；[渲染器测试](../tests/template-budget.test.mjs) 另外保证 `$&` 原文和正常重复占位符不被破坏。

**当前场景的级别：**按该项目约定的本地工具用途，这是 P2、非阻断的资源与费用预算改进。若改成公开计费接口，应重新评估。这不证明服务商会接受或收取 16 MB 提示词的费用，也不代表线上服务遭到利用。字节数不能直接换算成 Token 或金额。

**此次发布范围：**本仓库提供复现与经过测试的修复示例，不声称 PromptCanary 已集成或发布此修复。即使上游日后更新，案例仍引用固定提交。

## 在自己的项目试一次

可以向 AI 编程助手提问：

```text
请用 $ai-app-preflight 沿原始输入、模板、历史消息与检索结果，
追踪到最终模型请求，找出最终预算在哪里执行。
分别报告已确认的问题和待核实的部署信息。
如已获准复测，请使用本地替身，不调用付费模型。
```

Claude Code 中使用 `/ai-app-preflight`。[反馈一次脱敏后的结果](https://github.com/mioyui20/ai-app-preflight/issues/new?template=trial-feedback.yml)，包括“没有发现问题”或安装卡点。这些反馈会用于决定下一次改进。
