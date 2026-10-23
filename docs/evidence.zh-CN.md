# AI 应用预检：源码证据

这些证据仅供人工复核，不构成安全性、部署状态或完整性结论。

## 扫描覆盖范围

- root_name: before
- files_considered: 2
- files_read: 2
- files_scanned: 2
- bytes_read: 733
- bytes_scanned: 733
- files_by_role: {"source": 2, "test": 0, "example": 0}
- truncated: false
- stop_reasons: none
- skipped: {}
- limits: {"max_depth": 24, "max_entries": 20000, "max_evidence": 500, "max_file_bytes": 262144, "max_files": 1500, "max_total_bytes": 8388608}

## 待人工复核的线索

| 规则 | 优先级 | 文件:行号 | 符号 | 来源角色 | 复核提示 |
| --- | --- | --- | --- | --- | --- |
| public_env_credential | high | client.mjs:4 | NEXT_PUBLIC_LLM_API_KEY | source | 核实此公开环境变量是否进入浏览器构建产物，以及是否包含真实凭据。公开前缀的实际行为取决于框架和构建配置。 |
| browser_sdk_opt_in | medium | client.mjs:5 | dangerouslyAllowBrowser | source | 核实运行环境和凭据来源。此选项允许浏览器使用 SDK，但单凭它不能证明存在密钥泄露。 |

## 已观察到的标记

| 标记类型 | 文件:行号 | 符号 | 来源角色 |
| --- | --- | --- | --- |
| provider_call | route.mjs:5 | chat.completions.create | source |
| json_parse | route.mjs:10 | JSON.parse | source |

## 局限性

- 仅进行静态标记匹配。注释和字符串可能造成误报；间接调用、别名、框架行为及非 UTF-8 文件可能被遗漏。
- 不导入或执行目标代码，不联网，不自动修复。跳过环境文件、凭据和证书文件、依赖、构建产物，以及检测到的符号链接和目录联接。
- 没有匹配标记不代表缺少控制措施；存在标记也不代表措施有效或已应用到模型请求。
- JSON 解析与模式校验标记单独记录。模式标记仍需人工检查约束内容及异常处理。
- 仅报告名称、相对位置及固定标记名，不包含源码行或密钥值。测试或示例角色仅描述所在位置，不代表部署状态。
- 扫描上限和读取失败会限制覆盖范围。零线索报告不能视为安全认证；扫描过程中的文件变更也会影响结果。
