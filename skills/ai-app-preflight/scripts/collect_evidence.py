#!/usr/bin/env python3
"""Collect bounded, redacted source evidence for an AI application review.

This program never imports, executes, or modifies the inspected application.
Its matches are review leads, not vulnerability findings or a safety verdict.
Python 3.10+; standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any


MAX_FILES = 1500
MAX_FILE_BYTES = 256 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024
MAX_EVIDENCE = 500
MAX_ENTRIES = 20000
MAX_DEPTH = 24
MAX_ISSUES = 40

SOURCE_SUFFIXES = {
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".py", ".pyi",
    ".vue", ".svelte", ".go", ".rs", ".java", ".kt", ".kts",
    ".cs", ".rb", ".php", ".swift", ".scala", ".sh",
}
EXCLUDED_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "vendor", ".venv", "venv",
    "env", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    ".next", ".nuxt", ".svelte-kit", "dist", "build", "coverage", "target",
    ".cache", ".turbo", "site-packages", "bower_components",
}
SENSITIVE_SUFFIXES = {
    ".pem", ".key", ".p12", ".pfx", ".crt", ".cer", ".jks", ".keystore",
    ".asc", ".gpg", ".pgp",
}
SENSITIVE_NAMES = {
    "credentials", "credentials.json", "secrets", "secrets.json",
    "secrets.py", "secrets.js", "secrets.ts", "service-account.json",
    "id_rsa", "id_ed25519", "id_ecdsa", ".npmrc", ".netrc",
}

PUBLIC_ENV = re.compile(r"\b(?:NEXT_PUBLIC_|VITE_|REACT_APP_)[A-Z0-9_]+\b")
CREDENTIAL_NAME = re.compile(
    r"(?:^|_)(?:API_?KEY|ACCESS_?KEY|SECRET|TOKEN|PASSWORD|PRIVATE_?KEY)(?:_|$)",
    re.IGNORECASE,
)
BROWSER_OPTION = re.compile(r"\bdangerouslyAllowBrowser\s*:\s*true\b")
ASSIGNMENT = re.compile(
    r"\b([A-Za-z_$][A-Za-z0-9_$]*)\s*(?::\s*[A-Za-z_$][A-Za-z0-9_$<>\[\]| ]*)?"
    r"\s*[:=]\s*([\"'])([^\r\n\"']{16,512})\2"
)
KEY_VALUE = re.compile(
    r"(?:sk-(?:proj-|ant-api\d+-)?[A-Za-z0-9_-]{20,}|"
    r"AIza[A-Za-z0-9_-]{30,}|gsk_[A-Za-z0-9]{24,}|xai-[A-Za-z0-9_-]{24,})\Z"
)
PLACEHOLDER = re.compile(
    r"example|placeholder|your[_ -]|replace|dummy|fake|sample|redacted|"
    r"changeme|test[_ -]?key|insert|\.\.\.|<|>", re.IGNORECASE,
)

# Labels are fixed identifiers, never captured code or argument values.
# They describe markers that were seen, not guarantees about implementation.
SIGNAL_PATTERNS = (
    # These are navigation aids, not proof of a model call or an enforced cap.
    ("network_call", "fetch", r"\bfetch\s*\("),
    ("input_assembly", "replaceAll", r"\.\s*replaceAll\s*\("),
    ("input_assembly", "join", r"\.\s*join\s*\("),
    ("input_measurement", "Buffer.byteLength", r"\bBuffer\s*\.\s*byteLength\s*\("),
    ("input_measurement", "TextEncoder.encode", r"\bnew\s+TextEncoder\s*\(\s*\)\s*\.\s*encode\s*\("),
    ("provider_call", "responses.create", r"\bresponses\s*\.\s*create\s*\("),
    ("provider_call", "chat.completions.create", r"\bchat\s*\.\s*completions\s*\.\s*create\s*\("),
    ("provider_call", "messages.create", r"\bmessages\s*\.\s*create\s*\("),
    ("provider_call", "generateContent", r"\b(?:generateContent|generate_content)\s*\("),
    ("provider_call", "generateText", r"\b(?:generateText|streamText|generateObject|streamObject)\s*\("),
    ("streaming", "stream", r"\bstream\s*[:=]\s*(?:true|True)\b|\b(?:streamText|streamObject)\s*\(|\btext/event-stream\b"),
    ("timeout", "AbortSignal.timeout", r"\bAbortSignal\s*\.\s*timeout\s*\("),
    ("timeout", "timeout", r"\b(?:timeout|timeout_ms|timeoutMs|requestTimeout|read_timeout)\s*[:=(]"),
    ("disconnect", "abort_signal", r"\b(?:request|req)\s*\.\s*signal\b|\bsignal\s*\.\s*aborted\b"),
    ("disconnect", "abort_controller", r"\bAbortController\b|\bcontroller\s*\.\s*abort\s*\("),
    ("disconnect", "close_listener", r"\.\s*(?:on|once|addEventListener)\s*\(\s*['\"](?:close|aborted|abort)['\"]"),
    ("authorization_header", "Authorization", r"\bauthorization\b"),
    ("auth", "getServerSession", r"\bgetServerSession\s*\("),
    ("auth", "auth", r"\bauth\s*\("),
    ("auth", "authenticate", r"\bauthenticate\s*\("),
    ("auth", "requireAuth", r"\brequireAuth\s*\("),
    ("auth", "verifyToken", r"\bverifyToken\s*\("),
    ("rate_limit", "rate_limiter", r"\b(?:rateLimit|rate_limit|ratelimit|RateLimiter|limiter)\b"),
    ("output_budget", "max_tokens", r"\b(?:max_tokens|max_completion_tokens|max_output_tokens|maxOutputTokens|maxTokens)\s*[:=]"),
    ("schema_validation", "schema_parse", r"\b[A-Za-z_$][\w$]*\s*\.\s*(?:safeParse|parseAsync|safeParseAsync)\s*\("),
    ("schema_validation", "validator", r"\b(?:model_validate|model_validate_json|TypeAdapter|Draft202012Validator|jsonschema\s*\.\s*validate)\s*\("),
    ("schema_validation", "schema_builder", r"\bz\s*\.\s*(?:object|string|number|array|union)\s*\(|\b(?:ajv\s*\.\s*compile|Joi\s*\.\s*object)\s*\("),
    ("structured_output", "json_schema", r"\b(?:json_schema|response_format|text_format|with_structured_output)\b"),
    ("json_parse", "JSON.parse", r"\bJSON\s*\.\s*parse\s*\("),
    ("json_parse", "json.loads", r"\bjson\s*\.\s*loads?\s*\("),
    ("logging", "console", r"\bconsole\s*\.\s*(?:log|debug|info|warn|error)\s*\("),
    ("logging", "logger", r"\b(?:logger|logging)\s*\.\s*(?:debug|info|warning|warn|error|exception|log)\s*\("),
)
SIGNALS = tuple((kind, symbol, re.compile(pattern, re.IGNORECASE if kind == "authorization_header" else 0))
                for kind, symbol, pattern in SIGNAL_PATTERNS)

TEXT = {
    "en": {
        "title": "AI application preflight: source evidence",
        "scope": "Coverage",
        "leads": "Review leads",
        "signals": "Observed markers",
        "limitations": "Limitations",
        "lead_headers": "| Rule | Priority | File:line | Symbol | Role | Review hint |",
        "signal_headers": "| Kind | File:line | Symbol | Role |",
        "none": "None collected within the scanned scope.",
        "interpretation": "Evidence for manual review only; no security, deployment, or completeness verdict.",
        "public_env_credential": "Check whether this public environment variable reaches a browser bundle and contains a real credential. Public prefixes may expose values depending on the framework and build.",
        "browser_sdk_opt_in": "Check the actual runtime and credential source. This option permits browser SDK use but does not by itself prove a secret is exposed.",
        "credential_literal": "A credential-shaped literal is assigned here. Verify whether it is a real key; do not paste its value into a report. If real, rotate it through the provider and remove it from code/history as appropriate.",
        "non_source": "This evidence is in test/example material; do not assume it is deployed.",
        "limitations_list": [
            "Static marker matching only. Comments and strings can produce false positives; indirect calls, aliases, framework behavior, and non-UTF-8 files may be missed.",
            "No code is imported or executed, no network requests are made, and no fixes are applied. Environment files, credential/certificate files, dependencies, build outputs, and detected symlinks/junctions are skipped.",
            "Absence of a marker does not prove a missing control. Presence does not prove the control is effective or applies to a provider request.",
            "JSON parsing is recorded separately from schema-validation markers. Schema markers still require review of the actual constraints and error handling.",
            "Only names, relative locations, and fixed marker labels are reported; source lines and credential values are never included. Test/example roles describe location, not deployment status.",
            "Coverage limits and read failures restrict the review. A report with zero leads is not a safety certification. File changes during a scan can also affect coverage.",
        ],
    },
    "zh": {
        "title": "AI 应用预检：源码证据",
        "scope": "扫描覆盖范围",
        "leads": "待人工复核的线索",
        "signals": "已观察到的标记",
        "limitations": "局限性",
        "lead_headers": "| 规则 | 优先级 | 文件:行号 | 符号 | 来源角色 | 复核提示 |",
        "signal_headers": "| 标记类型 | 文件:行号 | 符号 | 来源角色 |",
        "none": "在已扫描范围内未收集到。",
        "interpretation": "这些证据仅供人工复核，不构成安全性、部署状态或完整性结论。",
        "public_env_credential": "核实此公开环境变量是否进入浏览器构建产物，以及是否包含真实凭据。公开前缀的实际行为取决于框架和构建配置。",
        "browser_sdk_opt_in": "核实运行环境和凭据来源。此选项允许浏览器使用 SDK，但单凭它不能证明存在密钥泄露。",
        "credential_literal": "此处赋值了形似凭据的字符串。请人工核实是否为真实密钥，不要把其值粘贴进报告；如属实，应在服务商处轮换并妥善清理代码及历史记录。",
        "non_source": "证据位于测试或示例材料中，不应假定它已被部署。",
        "limitations_list": [
            "仅进行静态标记匹配。注释和字符串可能造成误报；间接调用、别名、框架行为及非 UTF-8 文件可能被遗漏。",
            "不导入或执行目标代码，不联网，不自动修复。跳过环境文件、凭据和证书文件、依赖、构建产物，以及检测到的符号链接和目录联接。",
            "没有匹配标记不代表缺少控制措施；存在标记也不代表措施有效或已应用到模型请求。",
            "JSON 解析与模式校验标记单独记录。模式标记仍需人工检查约束内容及异常处理。",
            "仅报告名称、相对位置及固定标记名，不包含源码行或密钥值。测试或示例角色仅描述所在位置，不代表部署状态。",
            "扫描上限和读取失败会限制覆盖范围。零线索报告不能视为安全认证；扫描过程中的文件变更也会影响结果。",
        ],
    },
}


class ScanError(Exception):
    """A root target cannot be inspected. Messages must never include its path."""


def is_reparse(info: os.stat_result) -> bool:
    """Windows junctions are reparse points even when is_symlink() is false."""
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


def sensitive_file(name: str) -> bool:
    lower = name.lower()
    return (lower == ".env" or lower.startswith(".env.") or lower.endswith(".env")
            or ".env." in lower or lower in SENSITIVE_NAMES
            or Path(lower).suffix in SENSITIVE_SUFFIXES
            or lower.startswith(("service-account", "service_account", "credentials.", "secrets.")))


def source_role(relative: str) -> str:
    parts = Path(relative).parts
    lower_parts = {part.lower() for part in parts[:-1]}
    name = parts[-1].lower()
    if (lower_parts & {"test", "tests", "__tests__", "spec", "specs"}
            or name.startswith("test_") or name == "conftest.py"
            or ".test." in name or ".spec." in name or name.endswith("_test.go")):
        return "test"
    if lower_parts & {"example", "examples", "sample", "samples", "demo", "demos", "fixture", "fixtures"}:
        return "example"
    return "source"


def looks_like_key(value: str) -> bool:
    if not KEY_VALUE.fullmatch(value) or PLACEHOLDER.search(value):
        return False
    # Reject common all-x / all-zero / repeated placeholder payloads.
    payload = re.sub(r"^(?:sk-(?:proj-|ant-api\d+-)?|AIza|gsk_|xai-)", "", value)
    return len(set(payload.lower())) > 3


class Collector:
    def __init__(self, root: Path, lang: str):
        self.root = root
        self.lang = lang
        self.words = TEXT[lang]
        self.leads: list[dict[str, Any]] = []
        self.signals: list[dict[str, Any]] = []
        self.seen: set[tuple[Any, ...]] = set()
        self.halted = False
        self.coverage: dict[str, Any] = {
            "files_considered": 0, "files_read": 0, "files_scanned": 0,
            "bytes_read": 0, "bytes_scanned": 0, "entries_seen": 0,
            "directories_scanned": 0, "files_by_role": {"source": 0, "test": 0, "example": 0},
            "skipped": {}, "issues": [], "issues_omitted": 0, "truncated": False,
            "stop_reasons": [],
            "limits": {"max_files": MAX_FILES, "max_file_bytes": MAX_FILE_BYTES,
                       "max_total_bytes": MAX_TOTAL_BYTES, "max_evidence": MAX_EVIDENCE,
                       "max_entries": MAX_ENTRIES, "max_depth": MAX_DEPTH},
        }

    def skip(self, reason: str, relative: str | None = None, issue: bool = False) -> None:
        skipped = self.coverage["skipped"]
        skipped[reason] = skipped.get(reason, 0) + 1
        if issue:
            if len(self.coverage["issues"]) < MAX_ISSUES:
                self.coverage["issues"].append({"reason": reason, "file": relative or "."})
            else:
                self.coverage["issues_omitted"] += 1

    def stop(self, reason: str) -> None:
        self.halted = True
        self.coverage["truncated"] = True
        if reason not in self.coverage["stop_reasons"]:
            self.coverage["stop_reasons"].append(reason)

    def add(self, record: dict[str, Any], lead: bool = False) -> None:
        identity = (lead, record.get("rule_id", record.get("kind")),
                    record["file"], record["line"], record["symbol"])
        if identity in self.seen:
            return
        if len(self.leads) + len(self.signals) >= MAX_EVIDENCE:
            self.stop("max_evidence")
            return
        self.seen.add(identity)
        (self.leads if lead else self.signals).append(record)

    def add_lead(self, rule: str, symbol: str, relative: str, line: int, role: str) -> None:
        hint = self.words[rule]
        if role != "source":
            hint += " " + self.words["non_source"]
        self.add({"rule_id": rule, "category": "client_credentials", "priority":
                  "low" if role != "source" else ("medium" if rule == "browser_sdk_opt_in" else "high"),
                  "file": relative, "line": line, "symbol": symbol, "role": role,
                  "review_hint": hint}, lead=True)

    def inspect_text(self, text: str, relative: str, role: str) -> None:
        for line_number, line in enumerate(text.splitlines(), start=1):
            if self.halted:
                break
            for match in PUBLIC_ENV.finditer(line):
                symbol = match.group(0)
                if CREDENTIAL_NAME.search(symbol):
                    self.add_lead("public_env_credential", symbol, relative, line_number, role)
            if BROWSER_OPTION.search(line):
                self.add_lead("browser_sdk_opt_in", "dangerouslyAllowBrowser", relative, line_number, role)
            for match in ASSIGNMENT.finditer(line):
                if looks_like_key(match.group(3)):
                    self.add_lead("credential_literal", match.group(1), relative, line_number, role)
            for kind, symbol, pattern in SIGNALS:
                if pattern.search(line):
                    self.add({"kind": kind, "file": relative, "line": line_number,
                              "symbol": symbol, "role": role})

    def read_source(self, path: Path, relative: str, info: os.stat_result) -> None:
        if self.coverage["files_considered"] >= MAX_FILES:
            self.stop("max_files")
            return
        self.coverage["files_considered"] += 1
        if info.st_size > MAX_FILE_BYTES:
            self.skip("oversized_file", relative, issue=True)
            return
        # Invalid encodings and binary files consume the I/O budget too.
        remaining = MAX_TOTAL_BYTES - self.coverage["bytes_read"]
        if info.st_size > remaining:
            self.stop("max_total_bytes")
            return
        descriptor: int | None = None
        try:
            flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(path, flags)
            actual = os.fstat(descriptor)
            # Recheck identity before reading to avoid following a swapped link.
            if (not stat.S_ISREG(actual.st_mode) or is_reparse(actual)
                    or (actual.st_dev, actual.st_ino) != (info.st_dev, info.st_ino)):
                self.skip("changed_or_link", relative, issue=True)
                return
            if actual.st_size > MAX_FILE_BYTES:
                self.skip("oversized_file", relative, issue=True)
                return
            if actual.st_size > remaining:
                self.stop("max_total_bytes")
                return
            with os.fdopen(descriptor, "rb") as source:
                descriptor = None
                data = source.read(min(MAX_FILE_BYTES + 1, remaining))
                final_size = os.fstat(source.fileno()).st_size
        except OSError:
            self.skip("unreadable_file", relative, issue=True)
            return
        finally:
            if descriptor is not None:
                os.close(descriptor)
        self.coverage["files_read"] += 1
        self.coverage["bytes_read"] += len(data)
        if len(data) > MAX_FILE_BYTES:
            self.skip("oversized_file", relative, issue=True)
            return
        if final_size > len(data) and len(data) == remaining:
            self.stop("max_total_bytes")
            return
        if b"\x00" in data:
            self.skip("binary_file", relative, issue=True)
            return
        try:
            source_text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            self.skip("non_utf8_file", relative, issue=True)
            return
        role = source_role(relative)
        self.coverage["files_scanned"] += 1
        self.coverage["bytes_scanned"] += len(data)
        self.coverage["files_by_role"][role] += 1
        self.inspect_text(source_text, relative, role)

    def walk(self, directory: Path, depth: int = 0) -> None:
        if self.halted:
            return
        relative_dir = directory.relative_to(self.root).as_posix()
        if depth > MAX_DEPTH:
            self.skip("depth_limit", relative_dir, issue=True)
            self.coverage["truncated"] = True
            if "max_depth" not in self.coverage["stop_reasons"]:
                self.coverage["stop_reasons"].append("max_depth")
            return
        entries = []
        try:
            with os.scandir(directory) as iterator:
                self.coverage["directories_scanned"] += 1
                for entry in iterator:
                    if self.coverage["entries_seen"] >= MAX_ENTRIES:
                        self.stop("max_entries")
                        break
                    self.coverage["entries_seen"] += 1
                    entries.append(entry)
        except OSError:
            if depth == 0:
                raise ScanError("Unable to read the target directory.") from None
            self.skip("unreadable_directory", relative_dir, issue=True)
            return
        # Process already enumerated entries even if enumeration hit its bound.
        entry_bound = self.halted and self.coverage["stop_reasons"] == ["max_entries"]
        if entry_bound:
            self.halted = False
        for entry in sorted(entries, key=lambda item: item.name.lower()):
            if self.halted:
                break
            path = Path(entry.path)
            relative = path.relative_to(self.root).as_posix()
            try:
                # DirEntry.stat on Windows can return zero file identities;
                # a fresh lstat supplies an identity for the pre-read check.
                info = path.stat(follow_symlinks=False)
            except OSError:
                self.skip("unreadable_entry", relative, issue=True)
                continue
            if is_reparse(info):
                self.skip("reparse_point", relative, issue=True)
            elif stat.S_ISDIR(info.st_mode):
                if entry.name.lower() in EXCLUDED_DIRS:
                    self.skip("excluded_directory")
                elif entry_bound:
                    self.skip("entry_limit_directory", relative, issue=True)
                else:
                    self.walk(path, depth + 1)
            elif stat.S_ISREG(info.st_mode):
                if sensitive_file(entry.name):
                    self.skip("sensitive_file")
                elif path.suffix.lower() not in SOURCE_SUFFIXES:
                    self.skip("unsupported_extension")
                elif entry.name.lower().endswith((".min.js", ".min.mjs", ".bundle.js", ".d.ts")):
                    self.skip("generated_file")
                else:
                    self.read_source(path, relative, info)
            else:
                self.skip("special_file", relative, issue=True)
        if entry_bound:
            self.halted = True

    def report(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "root_name": self.root.name or "root",
            "coverage": self.coverage,
            "leads": self.leads,
            "signals": self.signals,
            "limitations": self.words["limitations_list"],
            "summary": {
                "lead_count": len(self.leads), "signal_count": len(self.signals),
                "interpretation": self.words["interpretation"],
            },
        }


def scan_target(target: str | Path, lang: str = "en") -> dict[str, Any]:
    root = Path(os.path.abspath(os.fspath(target)))
    try:
        # Refuse a root reached through a symlink/junction as well as links below it.
        for component in (root, *root.parents):
            if is_reparse(component.stat(follow_symlinks=False)):
                raise ScanError("The target path must not contain symlinks or junctions.")
        if not root.is_dir():
            raise ScanError("The target must be a readable directory.")
    except (OSError, ValueError):
        raise ScanError("The target must be a readable directory.") from None
    collector = Collector(root, lang)
    collector.walk(root)
    return collector.report()


def markdown(report: dict[str, Any], lang: str = "en") -> str:
    words = TEXT[lang]

    def cell(value: Any) -> str:
        return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("`", "\\`").replace("\n", " ").replace("\r", " ").replace("<", "&lt;").replace(">", "&gt;")

    coverage = report["coverage"]
    output = [f"# {words['title']}", "", report["summary"]["interpretation"], "",
              f"## {words['scope']}", "",
              f"- root_name: {cell(report['root_name'])}",
              f"- files_considered: {coverage['files_considered']}",
              f"- files_read: {coverage['files_read']}",
              f"- files_scanned: {coverage['files_scanned']}",
              f"- bytes_read: {coverage['bytes_read']}",
              f"- bytes_scanned: {coverage['bytes_scanned']}",
              f"- files_by_role: {cell(json.dumps(coverage['files_by_role'], ensure_ascii=False))}",
              f"- truncated: {str(coverage['truncated']).lower()}",
              f"- stop_reasons: {cell(', '.join(coverage['stop_reasons']) or 'none')}",
              f"- skipped: {cell(json.dumps(coverage['skipped'], ensure_ascii=False, sort_keys=True))}",
              f"- limits: {cell(json.dumps(coverage['limits'], sort_keys=True))}"]
    for issue in coverage["issues"]:
        output.append(f"- issue: {cell(issue['reason'])} — {cell(issue['file'])}")
    if coverage["issues_omitted"]:
        output.append(f"- issues_omitted: {coverage['issues_omitted']}")
    output.extend(["", f"## {words['leads']}", ""])
    if report["leads"]:
        output.extend([words["lead_headers"],
                       "| --- | --- | --- | --- | --- | --- |"])
        for lead in report["leads"]:
            output.append("| " + " | ".join(cell(value) for value in (
                lead["rule_id"], lead["priority"], f"{lead['file']}:{lead['line']}",
                lead["symbol"], lead["role"], lead["review_hint"])) + " |")
    else:
        output.append(words["none"])
    output.extend(["", f"## {words['signals']}", ""])
    if report["signals"]:
        output.extend([words["signal_headers"], "| --- | --- | --- | --- |"])
        for signal in report["signals"]:
            output.append("| " + " | ".join(cell(value) for value in (
                signal["kind"], f"{signal['file']}:{signal['line']}", signal["symbol"], signal["role"])) + " |")
    else:
        output.append(words["none"])
    output.extend(["", f"## {words['limitations']}", ""])
    output.extend("- " + item for item in report["limitations"])
    return "\n".join(output) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="Local source directory (read-only)")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--lang", choices=("en", "zh"), default="en")
    args = parser.parse_args(argv)
    try:
        report = scan_target(args.target, args.lang)
    except ScanError as error:
        print(f"collect_evidence: {error}", file=sys.stderr)
        return 2
    result = json.dumps(report, ensure_ascii=False, indent=2) + "\n" if args.format == "json" else markdown(report, args.lang)
    try:
        # UTF-8 is also reliable in Windows terminals with a legacy code page.
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    sys.stdout.write(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
