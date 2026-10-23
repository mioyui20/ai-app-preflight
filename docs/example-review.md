# Example review / 评审示例

This is a source review of deliberately flawed teaching fixtures, not a report about a deployed service. No real key, provider call or infrastructure check was used.

这是对教学示例的源码评审，不是对线上服务的安全报告。没有使用真实密钥、调用模型或检查基础设施。

## Before / 改进前

**Decision: verification needed for deployment; confirmed missing request boundaries in the fixture.**

**结论：部署情况待核实；示例路由中确认缺少请求边界。**

| Area / 方向 | Evidence / 依据 | Conclusion / 结论 | Local retest / 本地复测 |
| --- | --- | --- | --- |
| Credentials / 密钥 | `examples/before/client.mjs` uses a public-prefixed provider variable and browser SDK opt-in / 使用公开前缀与浏览器选项 | Needs verification: bundling and actual secret use are not established by the snippet / 待核实构建和实际密钥用途 | Use a fake key to inspect client settings, never print a real key / 用假值检查前端配置 |
| Spending / 成本 | `examples/before/route.mjs` starts provider work immediately after reading the body / 读取请求后直接调用模型 | Confirmed in this isolated handler: no caller, input/output or quota boundary. Deployment middleware remains unknown / 独立函数中确认缺少边界，外部中间件未知 | Count stub calls for rejected input or exhausted quotas / 验证拒绝路径的模型调用次数为零 |
| Lifecycle / 生命周期 | No deadline or request signal reaches the provider call / 未把期限或请求信号传入调用 | Confirmed for this function; not a claim about an unknown SDK/global timeout / 函数中确认，SDK 全局配置未知 | Stall a stub and abort a caller; observe cancellation / 用停滞替身和调用者取消验证 |
| Output / 输出 | `JSON.parse(...)` is returned directly / 解析结果直接返回 | Confirmed: valid JSON scalars and wrong-shaped objects are accepted / 可接受结构错误但语法合法的 JSON | Return `42`, wrong field types and malformed JSON / 返回标量、错误字段类型及无效 JSON |

## After / 改进后

The corrected example rejects missing authentication, limits bytes before model work, validates the prompt, consults a quota admission hook, sets an output cap, propagates deadlines/cancellation, redacts upstream errors, and returns only validated result fields. `tests/routes.test.mjs` tests observable behavior with injected stubs.

修复示例在调用模型前检查鉴权、请求字节、输入和额度；传递截止时间与取消信号，设置输出上限，隐藏上游错误细节，并只返回经过校验的字段。`tests/routes.test.mjs` 用注入的替身验证真实行为。

`examples/after/template-budget.mjs` separately budgets the assembled prompt **before** joining repeated placeholders. The corresponding test demonstrates how individually bounded template/input fields can still multiply into an excessive provider payload.

独立的最终输入预算示例会在拼接重复占位符之前检查总字节数。相应测试说明：模板和输入分别合规，也可能组合成超限请求。

**Still open:** production authentication, atomic shared quotas and reservations, SDK retry semantics, multi-replica behavior, streaming chunk failure handling, and factual/business correctness of model answers. The example is non-streaming, so its cancellation tests do not verify an SSE deployment.

**仍需核实：**生产鉴权、共享原子额度与预留、SDK 重试行为、多副本一致性、流式分块错误处理、模型回答的事实及业务正确性。此例不使用流式响应，不能用其取消测试证明 SSE 部署正确。

Use an actual Skill run to produce repository-specific file:line references. The collector's [English](evidence.en.md) and [Chinese](evidence.zh-CN.md) reports contain exact fixture locations; they remain review leads.

实际使用 Skill 时，应给出当前仓库的具体行号。[英文](evidence.en.md)和[中文](evidence.zh-CN.md)脚本报告提供示例的精确位置，但它们仍是待复核线索。
