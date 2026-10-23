# AI application preflight: source evidence

Evidence for manual review only; no security, deployment, or completeness verdict.

## Coverage

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

## Review leads

| Rule | Priority | File:line | Symbol | Role | Review hint |
| --- | --- | --- | --- | --- | --- |
| public_env_credential | high | client.mjs:4 | NEXT_PUBLIC_LLM_API_KEY | source | Check whether this public environment variable reaches a browser bundle and contains a real credential. Public prefixes may expose values depending on the framework and build. |
| browser_sdk_opt_in | medium | client.mjs:5 | dangerouslyAllowBrowser | source | Check the actual runtime and credential source. This option permits browser SDK use but does not by itself prove a secret is exposed. |

## Observed markers

| Kind | File:line | Symbol | Role |
| --- | --- | --- | --- |
| provider_call | route.mjs:5 | chat.completions.create | source |
| json_parse | route.mjs:10 | JSON.parse | source |

## Limitations

- Static marker matching only. Comments and strings can produce false positives; indirect calls, aliases, framework behavior, and non-UTF-8 files may be missed.
- No code is imported or executed, no network requests are made, and no fixes are applied. Environment files, credential/certificate files, dependencies, build outputs, and detected symlinks/junctions are skipped.
- Absence of a marker does not prove a missing control. Presence does not prove the control is effective or applies to a provider request.
- JSON parsing is recorded separately from schema-validation markers. Schema markers still require review of the actual constraints and error handling.
- Only names, relative locations, and fixed marker labels are reported; source lines and credential values are never included. Test/example roles describe location, not deployment status.
- Coverage limits and read failures restrict the review. A report with zero leads is not a safety certification. File changes during a scan can also affect coverage.
