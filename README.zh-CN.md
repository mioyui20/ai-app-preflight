# AI App Preflight

[English](README.md) · [安装](#安装) · [免密钥演示](#先看一个免密钥演示)

让 AI 编程助手在发布前检查应用的 AI 接口：密钥会不会泄露、模型请求会不会过大、用户取消后是否还在运行，以及模型返回异常内容时会怎样。

适合新增聊天接口、修改提示词拼接逻辑，或准备把本地 AI 原型交给别人使用时运行。你会得到一份包含**文件位置、失败场景、修复建议和复测步骤**的审查结果。

## 能检查什么

| 你关心的问题 | 审查会追踪什么 |
| --- | --- |
| 模型密钥会不会进入浏览器？ | 密钥从哪里读取、发送到哪里 |
| 一个小请求会不会引发大量模型工作？ | 最终提示词、额度、输出限制、重试和并发 |
| 用户关掉页面后，请求是否停止？ | 超时、取消传递和流式请求的清理 |
| 模型返回意外内容，会不会导致应用出错？ | JSON 解析、字段校验及结果的使用方式 |

使用时告诉助手：这是本地工具、内部服务，还是公开演示。不同用途需要的控制措施不同。

## 安装

需要一个支持 Skill 的 AI 编程助手。使用 [skills CLI](https://github.com/vercel-labs/skills) 安装时，需要 Node.js 22.20+；在你的应用项目目录运行：

```bash
npx skills add mioyui20/ai-app-preflight --skill ai-app-preflight
```

按提示选择使用的助手。

也可以从[发布页](https://github.com/mioyui20/ai-app-preflight/releases/latest)下载并解压 `ai-app-preflight-skill-*.zip`，再按下表复制整个 `ai-app-preflight` 文件夹。

| 助手 | 你的应用项目内的安装位置 |
| --- | --- |
| Codex | `.agents/skills/ai-app-preflight/` |
| Claude Code | `.claude/skills/ai-app-preflight/` |

保留 `SKILL.md` 旁的脚本和参考文件。如果下载的是完整源码，对应文件夹位于 `skills/ai-app-preflight`。未显示时可查看 [Codex](https://learn.chatgpt.com/docs/build-skills) 或 [Claude Code](https://code.claude.com/docs/en/skills) 的发现说明。

## 第一次怎么用

在 AI 编程助手里打开你的应用项目，发送：

```text
请用 $ai-app-preflight 检查这个应用的 AI 接口。
这是一个本地单人使用的工具。请给出文件位置、已确认的问题、
还需核实的信息和本地复测步骤。先不要修改文件，也不要调用真实模型。
```

把“本地单人使用”换成你的实际场景。Claude Code 中将 `$ai-app-preflight` 换成 `/ai-app-preflight`。可以用中文或英文提问。

先看已确认的问题。如果结论依赖网关、部署或服务商设置，补充这些信息后再判断。之后可以让助手修复某个具体问题，并用本地替身复测。

[查看审查结果示例](docs/example-review.md) · [查看真实案例](docs/case-study.zh-CN.md)

## 先看一个免密钥演示

这个独立演示需要 Node.js 20.19+：

```bash
git clone https://github.com/mioyui20/ai-app-preflight.git
cd ai-app-preflight
node examples/prompt-expansion/demo.mjs --lang zh
```

它复现了维护者自己的 PromptCanary 项目中的问题：约 24 KB 的输入可以展开成约 16 MB 的提示词。程序使用本地计数替身：

| 超限输入 | 添加预算前 | 使用示例预算后 |
| --- | ---: | ---: |
| 提交的提示词字节数 | 15,996,000 | 0 |
| 替身调用次数 | 1 | 0 |

正常中英文输入仍可通过。省略 `--lang zh` 查看英文，使用 `--json` 输出 JSON。演示不调用真实模型，字节数也不能直接换算成 Token 或费用。[查看案例详情](docs/case-study.zh-CN.md)。

## 可选：自己收集源码位置

准备 Python 3.10+，在克隆的仓库目录运行：

```bash
python skills/ai-app-preflight/scripts/collect_evidence.py /你的应用路径 --lang zh
```

加上 `--format json` 可输出 JSON。脚本只读取源码，不运行你的应用、不联网；跳过环境文件和常见凭据文件，输出位置而不输出源码片段或密钥值。

结果是**待复核的线索**，需要结合源码确认。请阅读覆盖范围和跳过说明；没有线索不等于应用安全。完整 Skill 仍需要助手自身提供模型和工具。

## 使用反馈

[反馈首次使用结果](https://github.com/mioyui20/ai-app-preflight/issues/new?template=trial-feedback.yml)，或[报告误报和遗漏](https://github.com/mioyui20/ai-app-preflight/issues/new?template=feedback.yml)。注明助手、版本和一个脱敏的小例子，请勿公开密钥或私有源码。

[更新记录](CHANGELOG.md) · [参与贡献](CONTRIBUTING.md) · [MIT 许可](LICENSE)
