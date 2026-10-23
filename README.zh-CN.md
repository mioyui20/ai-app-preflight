<h1 align="center">AI App Preflight</h1>
<p align="center"><strong>AI 应用发布前，把容易出事故的请求链路查清楚。</strong><br>一个带离线证据脚本的 Agent Skill，聚焦 AI 接口四类上线问题。</p>
<p align="center"><a href="README.md">English</a> · <a href="#安装-skill">安装</a> · <a href="#无需模型密钥的演示">免密钥演示</a> · <a href="skills/ai-app-preflight/SKILL.md">查看 Skill 指令</a></p>

AI 功能在演示中能正常回答，并不意味着密钥、成本、中断处理和输出校验已经处理妥当。这个 Skill 帮助 AI 编程助手检查四条边界，并给出**文件行号 → 失败场景 → 修复建议 → 本地复测**。

| 检查方向 | 关注什么 |
| --- | --- |
| 密钥边界 | 模型密钥是否进入前端构建或接口响应 |
| 成本边界 | 调用者策略、额度、最终展开后的输入、输出限制、重试与并发 |
| 请求生命周期 | 超时、用户断开、流内错误与资源清理 |
| 输出边界 | JSON 解析、结构校验与业务语义检查的区别 |

它会根据实际用途判断：本地工具与公开计费服务需要的控制措施不同。**脚本收集线索，AI 阅读上下文后确认。** 不把关键词命中当成漏洞，也不把零命中当成安全认证；不提供虚构安全分数、不自动部署、不默认调用付费模型。

## 安装 Skill

### 使用 skills CLI

安装 Node.js **22.20+** 后，在希望使用 Skill 的项目中运行：

```bash
npx skills add mioyui20/ai-app-preflight --skill ai-app-preflight
```

按提示选择 AI 编程助手。安装工具来自 [skills CLI](https://github.com/vercel-labs/skills)，离线证据脚本不依赖它。

### 手动安装到项目

克隆仓库或[下载发布包](https://github.com/mioyui20/ai-app-preflight/releases)，将整个 `skills/ai-app-preflight` 文件夹复制到对应目录：

| 工具 | 项目内目录 |
| --- | --- |
| Codex | `<你的项目>/.agents/skills/ai-app-preflight/` |
| Claude Code | `<你的项目>/.claude/skills/ai-app-preflight/` |

请保留 `SKILL.md`、脚本、参考文件和许可证。若未立即出现，请按对应工具的发现机制操作。标准格式兼容不等于对所有工具版本的认证；已在真实仓库上独立试用 Codex 风格的工作流。

在 Codex 中可以这样提问：

```text
请用 $ai-app-preflight 检查这个项目的 AI 接口发布风险。
给出有文件行号证据的问题、还需核实的部署信息和本地复测步骤。
不要调用真实模型，不要修改项目。
```

Claude Code 可使用 `/ai-app-preflight` 后接审查请求。这是可安装到 AI 编程助手的独立 Skill，不是双击运行的桌面软件，也不是已经上架应用商店的插件。Skill 的指令要求使用用户的语言回复。

## 无需模型密钥的演示

证据脚本需要 **Python 3.10+**，无需安装 pip 依赖；命令也可根据环境改为 `python3` 或 `py -3`。

```bash
git clone https://github.com/mioyui20/ai-app-preflight.git
cd ai-app-preflight

python skills/ai-app-preflight/scripts/collect_evidence.py examples/before --lang zh
python skills/ai-app-preflight/scripts/collect_evidence.py examples/after --lang zh
python skills/ai-app-preflight/scripts/collect_evidence.py /你的项目路径 --format json
```

第一个示例会定位到 `client.mjs:4`、`client.mjs:5` 的复核线索。修复示例增加了请求边界，但**不是完整生产服务**：仍需宿主应用接入真实鉴权、共享原子额度管理和兼容的模型适配器。

[中文证据示例](docs/evidence.zh-CN.md) · [English evidence](docs/evidence.en.md) · [评审报告示例](docs/example-review.md)。

接口行为演示需要 Node.js 20.19+，无需 npm install：

```bash
node --test tests/routes.test.mjs tests/template-budget.test.mjs
python -B -m unittest discover -s tests -p 'test_*.py' -v
```

测试使用本地替身，覆盖调用模型前拒绝非法请求、额度失败、超大请求体、错误结构、超时、取消和错误脱敏。另附最终输入预算示例，阻止重复占位符把小输入展开成大请求。

## 包内结构

```text
skills/ai-app-preflight/
├── SKILL.md                     给 AI 助手的工作流指令
├── agents/openai.yaml           Codex 展示信息
├── scripts/collect_evidence.py  离线证据收集
├── references/review-guide.md   按需阅读的审查指南
└── LICENSE.txt
```

脚本支持 JSON 和中英文 Markdown，报告相对路径与行号，不输出源码行或密钥值。`leads` 是复核线索，`signals` 是相关代码位置；出站 Authorization 与调用者鉴权标记分别记录，但不能仅靠标记证明鉴权有效。JSON 解析也与 schema 标记分开；手工实现的结构校验可能没有对应关键词。

退出码 `0` 表示收集过程完成，即使存在待审线索；`2` 表示参数或根目录读取错误。部分扫描同样可能退出 `0`，必须读取覆盖范围、截断和跳过原因。它不是自动阻止发布的 CI 安全闸门。

## 边界与局限

- 不导入、执行、安装、修改目标项目，不联网；只读取源码文本。
- 跳过 `.env` 变体、常见凭据与证书文件、依赖和产物，以及检测到的符号链接、junction。不要把活跃凭据存储当作扫描目标。
- 扫描上限：1500 个候选文件、每文件 256 KiB、实际读取 8 MiB、500 条证据、20000 个目录项、24 层目录。
- 静态逐行匹配可能遗漏别名、间接调用、跨行表达式、语言与编码变体；注释和字符串可能误报。扫描时文件变化也会影响结果。它不是文件系统沙箱或针对并发恶意修改的防护。
- 网关与部署控制可能位于仓库外，应标为待核实，而不是凭缺少关键词断言漏洞。
- AI 助手仍需要自身宿主提供的模型与权限。脚本离线不等于整个 AI 助手无需模型。

欢迎带真实复现和回归测试的小改进，参见[贡献指南](CONTRIBUTING.md)。

参考：[Agent Skills 标准](https://agentskills.io/specification)、[Codex 技能说明](https://learn.chatgpt.com/docs/build-skills)、[OWASP 无边界消耗](https://genai.owasp.org/llmrisk/llm102025-unbounded-consumption/)、[AI SDK 生命周期](https://ai-sdk.dev/docs/ai-sdk-core/error-handling)。本项目独立维护，不代表这些组织的官方产品或背书。

MIT © 2026 [mioyui20](https://github.com/mioyui20)
