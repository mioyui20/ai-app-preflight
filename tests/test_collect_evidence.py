"""Behavioral checks for the offline, redacted evidence collector."""

from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "skills/ai-app-preflight/scripts/collect_evidence.py"
SPEC = importlib.util.spec_from_file_location("collect_evidence", SCRIPT)
scanner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scanner)


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def scan(self, **kwargs):
        return scanner.scan_target(self.root, **kwargs)

    def run_cli(self, *arguments):
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, arguments)],
                              capture_output=True, encoding="utf-8", check=False)

    def test_cli_json_has_redacted_evidence_and_no_absolute_path(self):
        synthetic_key = "sk-proj-" + "a1b2C3d4E5f6G7h8I9j0K1l2M3n4"
        self.write("src/client.ts", "\n".join([
            "const apiKey = '" + synthetic_key + "';",
            "const client = new OpenAI({ dangerouslyAllowBrowser: true });",
            "const token = process.env.NEXT_PUBLIC_OPENAI_API_KEY;",
        ]))
        completed = self.run_cli(self.root, "--format", "json")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["root_name"], self.root.name)
        self.assertEqual({lead["rule_id"] for lead in report["leads"]},
                         {"public_env_credential", "browser_sdk_opt_in", "credential_literal"})
        key_lead = next(lead for lead in report["leads"] if lead["rule_id"] == "credential_literal")
        self.assertEqual((key_lead["file"], key_lead["line"], key_lead["symbol"]),
                         ("src/client.ts", 1, "apiKey"))
        self.assertNotIn(synthetic_key, completed.stdout)
        self.assertNotIn("const apiKey", completed.stdout)
        self.assertNotIn(str(self.root), completed.stdout)
        for lead in report["leads"]:
            self.assertEqual(lead["role"], "source")
            self.assertTrue({"category", "priority", "review_hint"} <= lead.keys())

    def test_placeholders_and_non_credential_public_variables_are_not_leads(self):
        self.write("app.js", "\n".join([
            "const apiKey = 'sk-proj-YOUR_API_KEY_PLACEHOLDER';",
            "const other = 'sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx';",
            "const url = process.env.NEXT_PUBLIC_API_URL;",
            "const name = import.meta.env.VITE_APP_TITLE;",
        ]))
        self.assertEqual(self.scan()["leads"], [])

    def test_json_parse_is_not_schema_validation(self):
        self.write("route.ts", "const body = JSON.parse(text);\nconst data = json.loads(text);\n")
        signals = self.scan()["signals"]
        self.assertEqual({item["kind"] for item in signals}, {"json_parse"})
        self.assertEqual({item["symbol"] for item in signals}, {"JSON.parse", "json.loads"})

    def test_raw_fetch_and_prompt_assembly_are_navigation_not_findings(self):
        self.write("src/provider.js", "\n".join([
            'const prompt = template.replaceAll("{{input}}", () => input);',
            'const response = await fetch(endpoint, {body: JSON.stringify({prompt})});',
        ]))
        report = self.scan()
        self.assertEqual(report["leads"], [])
        self.assertEqual({(s["kind"], s["line"]) for s in report["signals"]},
                         {("input_assembly", 1), ("network_call", 2)})
        self.assertNotIn("provider_call", {s["kind"] for s in report["signals"]})

    def test_size_measurement_does_not_claim_an_enforced_budget(self):
        self.write("src/prompt.ts", "\n".join([
            'const prompt = history.join("\\n");',
            'const measured = Buffer.byteLength(prompt, "utf8");',
            'const bytes = new TextEncoder().encode(prompt);',
        ]))
        report = self.scan()
        self.assertEqual(report["leads"], [])
        self.assertEqual({s["kind"] for s in report["signals"]},
                         {"input_assembly", "input_measurement"})
        self.assertEqual(len(report["signals"]), 3)

    def test_non_ai_fetch_and_join_remain_neutral_markers(self):
        self.write("src/weather.js", 'fetch("/weather");\n["a", "b"].join(",");')
        report = self.scan()
        self.assertEqual(report["leads"], [])
        self.assertEqual({s["kind"] for s in report["signals"]},
                         {"network_call", "input_assembly"})

    def test_observed_controls_and_provider_calls_are_recorded_separately(self):
        self.write("route.ts", "\n".join([
            "const session = await auth();",
            "const limiter = rateLimit({});",
            "const cancel = request.signal;",
            "const signal = AbortSignal.timeout(2000);",
            "const response = client.responses.create({max_output_tokens: 100, stream: true});",
            "const shape = z.object({answer: z.string()});",
            "const result = shape.safeParse(data);",
            "logger.info(result);",
        ]))
        report = self.scan()
        self.assertEqual(report["leads"], [])
        self.assertTrue({"auth", "rate_limit", "disconnect", "timeout", "provider_call",
                         "output_budget", "streaming", "schema_validation", "logging"}
                        <= {item["kind"] for item in report["signals"]})

    def test_example_and_test_roles_do_not_imply_deployed_risk(self):
        marker = "const browser = {dangerouslyAllowBrowser: true};"
        self.write("examples/demo.ts", marker)
        self.write("tests/fixtures/client.ts", marker)
        self.write("src/client.test.ts", marker)
        report = self.scan()
        roles = {item["file"]: item["role"] for item in report["leads"]}
        self.assertEqual(roles, {"examples/demo.ts": "example", "tests/fixtures/client.ts": "test",
                                 "src/client.test.ts": "test"})
        self.assertTrue(all(item["priority"] == "low" for item in report["leads"]))
        self.assertTrue(all("do not assume it is deployed" in item["review_hint"]
                            for item in report["leads"]))

    def test_auth_calls_and_authorization_header_have_distinct_evidence(self):
        self.write("route.ts", "\n".join([
            'const headers = {Authorization: "Bearer placeholder"};',
            "const first = await authenticate();",
            "const second = await getServerSession();",
        ]))
        evidence = {(item["kind"], item["symbol"], item["line"])
                    for item in self.scan()["signals"]}
        self.assertEqual(evidence, {
            ("authorization_header", "Authorization", 1),
            ("auth", "authenticate", 2),
            ("auth", "getServerSession", 3),
        })

    def test_chinese_markdown_localizes_both_table_headers(self):
        self.write("client.ts", "const options = {dangerouslyAllowBrowser: true};\nJSON.parse(text);")
        completed = self.run_cli(self.root, "--lang", "zh")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("| 规则 | 优先级 | 文件:行号 | 符号 | 来源角色 | 复核提示 |", completed.stdout)
        self.assertIn("| 标记类型 | 文件:行号 | 符号 | 来源角色 |", completed.stdout)
        self.assertNotIn("| Rule |", completed.stdout)
        self.assertNotIn("| Kind |", completed.stdout)
        self.assertIn("browser_sdk_opt_in", completed.stdout)

    def test_sensitive_dependencies_build_and_generated_sources_are_skipped(self):
        marker = "const browser = {dangerouslyAllowBrowser: true};"
        for name in (".env", ".env.local", "backup.env.ts", "secrets.py", "client.pem",
                     "node_modules/client.js", "dist/client.js", ".git/hooks/client.py",
                     "vendor/client.py", "client.min.js", "client.d.ts"):
            self.write(name, marker)
        self.write("src/app.py", "print('hello')")
        report = self.scan()
        self.assertEqual(report["leads"], [])
        self.assertEqual(report["coverage"]["files_scanned"], 1)
        skipped = report["coverage"]["skipped"]
        self.assertGreaterEqual(skipped["sensitive_file"], 5)
        self.assertGreaterEqual(skipped["excluded_directory"], 4)
        self.assertEqual(skipped["generated_file"], 2)

    def test_does_not_execute_target_code(self):
        sentinel = self.root / "executed.txt"
        self.write("app.py", "from pathlib import Path\nPath(" + repr(str(sentinel)) + ").write_text('executed')\nraise RuntimeError('never execute')")
        self.scan()
        self.assertFalse(sentinel.exists())

    def test_oversize_non_utf8_and_binary_are_visible_in_coverage(self):
        self.write("large.ts", "x" * 65)
        (self.root / "binary.py").write_bytes(b"\x00file")
        (self.root / "legacy.js").write_bytes(b"\xff\xfe")
        with patch.object(scanner, "MAX_FILE_BYTES", 64):
            report = self.scan()
        self.assertEqual(report["coverage"]["files_scanned"], 0)
        self.assertEqual({item["reason"] for item in report["coverage"]["issues"]},
                         {"oversized_file", "binary_file", "non_utf8_file"})

    def test_file_limit_marks_incomplete_coverage(self):
        for index in range(3):
            self.write(f"app{index}.py", "pass")
        with patch.object(scanner, "MAX_FILES", 2):
            report = self.scan()
        self.assertEqual(report["coverage"]["files_scanned"], 2)
        self.assertTrue(report["coverage"]["truncated"])
        self.assertIn("max_files", report["coverage"]["stop_reasons"])

    def test_total_bytes_limit_is_enforced(self):
        self.write("a.py", "a" * 20)
        self.write("b.py", "b" * 20)
        with patch.object(scanner, "MAX_TOTAL_BYTES", 30):
            report = self.scan()
        self.assertEqual(report["coverage"]["bytes_scanned"], 20)
        self.assertIn("max_total_bytes", report["coverage"]["stop_reasons"])

    def test_evidence_limit_marks_incomplete_coverage(self):
        self.write("app.ts", "\n".join("JSON.parse(value);" for _ in range(8)))
        with patch.object(scanner, "MAX_EVIDENCE", 3):
            report = self.scan()
        self.assertEqual(len(report["signals"]), 3)
        self.assertTrue(report["coverage"]["truncated"])
        self.assertIn("max_evidence", report["coverage"]["stop_reasons"])

    def test_invalid_encoding_still_consumes_the_read_budget(self):
        for index in range(3):
            (self.root / f"app{index}.py").write_bytes(b"\xff" * 20)
        with patch.object(scanner, "MAX_TOTAL_BYTES", 30):
            report = self.scan()
        self.assertEqual(report["coverage"]["bytes_scanned"], 0)
        self.assertEqual(report["coverage"]["bytes_read"], 20)
        self.assertEqual(report["coverage"]["files_read"], 1)
        self.assertIn("max_total_bytes", report["coverage"]["stop_reasons"])

    def test_entry_and_depth_limits_bound_traversal(self):
        for index in range(4):
            self.write(f"app{index}.py", "pass")
        with patch.object(scanner, "MAX_ENTRIES", 2):
            report = self.scan()
        self.assertEqual(report["coverage"]["entries_seen"], 2)
        self.assertIn("max_entries", report["coverage"]["stop_reasons"])
        self.write("nested/deep/app.py", "pass")
        with patch.object(scanner, "MAX_DEPTH", 1):
            report = self.scan()
        self.assertIn("max_depth", report["coverage"]["stop_reasons"])
        self.assertIn("depth_limit", report["coverage"]["skipped"])

    def test_symlink_is_skipped_and_link_root_is_rejected(self):
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        secret = Path(outside.name) / "client.ts"
        secret.write_text("const browser = {dangerouslyAllowBrowser: true};", encoding="utf-8")
        link = self.root / "linked.ts"
        try:
            os.symlink(secret, link)
        except (OSError, NotImplementedError):
            self.skipTest("Creating symlinks is unavailable on this host")
        report = self.scan()
        self.assertEqual(report["leads"], [])
        self.assertEqual(report["coverage"]["skipped"]["reparse_point"], 1)
        with self.assertRaises(scanner.ScanError):
            scanner.scan_target(link)

    def test_unreadable_source_is_recorded_without_os_error_details(self):
        self.write("unreadable.py", "pass")
        with patch.object(scanner.os, "open", side_effect=PermissionError("private absolute path")):
            report = self.scan()
        self.assertEqual(report["coverage"]["skipped"]["unreadable_file"], 1)
        self.assertNotIn("private absolute path", json.dumps(report))

    def test_unreadable_root_exits_two_without_absolute_path(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(scanner.os, "scandir", side_effect=PermissionError(str(self.root))):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                result = scanner.main([str(self.root)])
        self.assertEqual(result, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertNotIn(str(self.root), stderr.getvalue())

    def test_cli_default_markdown_chinese_and_invalid_root(self):
        self.write("app.py", "pass")
        completed = self.run_cli(self.root, "--lang", "zh")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(completed.stdout.startswith("# AI 应用预检"))
        self.assertIn("不构成安全性", completed.stdout)
        missing = self.run_cli(self.root / "missing", "--format", "json")
        self.assertEqual(missing.returncode, 2)
        self.assertEqual(missing.stdout, "")
        self.assertNotIn(str(self.root), missing.stderr)
        invalid = self.run_cli(self.root, "--format", "html")
        self.assertEqual(invalid.returncode, 2)

    def test_empty_project_gets_no_safety_verdict(self):
        report = self.scan()
        self.assertEqual(report["summary"]["lead_count"], 0)
        self.assertEqual(report["summary"]["signal_count"], 0)
        self.assertIn("no security", report["summary"]["interpretation"])
        self.assertTrue(any("zero leads is not a safety certification" in item
                            for item in report["limitations"]))


if __name__ == "__main__":
    unittest.main()
