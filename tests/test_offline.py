"""Offline tests for asimtool — no network access required.

Run with::

    python -m unittest discover -s tests -v
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import asimtool
from asimtool.core.helpers import extract_json_object
from asimtool.developer import code_agent
from asimtool.tools import cover_letter
from asimtool.tools.transcribe import _mime_for

# `asimtool.developer.security_scan` is re-exported as a *function*, so the
# module itself has to be pulled out of sys.modules explicitly.
security_scan = sys.modules["asimtool.developer.security_scan"]


class TestPackage(unittest.TestCase):
    def test_version_and_exports(self):
        self.assertEqual(asimtool.__version__, "0.4.0")
        for name in asimtool.__all__:
            self.assertTrue(hasattr(asimtool, name), f"missing export: {name}")

    def test_chat_accepts_custom_provider(self):
        chat = asimtool.Chat(provider=asimtool.Provider(["Yqcloud"]))
        self.assertEqual(len(chat._providers), 1)

    def test_default_providers_resolve(self):
        self.assertTrue(asimtool.Provider().providers)


class TestHelpers(unittest.TestCase):
    def test_extract_json_from_fence(self):
        raw = 'blah\n```json\n{"a": 1}\n```\n'
        self.assertEqual(extract_json_object(raw), {"a": 1})

    def test_extract_json_without_fence(self):
        raw = 'Sure! {"a": {"b": "}"}} done'
        self.assertEqual(extract_json_object(raw), {"a": {"b": "}"}})

    def test_extract_json_invalid(self):
        self.assertIsNone(extract_json_object("no json here"))


class TestSecurityScan(unittest.TestCase):
    def test_parse_findings_sorts_by_severity(self):
        raw = json.dumps({
            "summary": "ok",
            "findings": [
                {"id": "F-02", "title": "low one", "severity": "Low", "location": "a.py:1"},
                {"id": "F-01", "title": "crit", "severity": "Critical", "location": "a.py:9"},
                {"title": "no severity", "location": "a.py:4"},
            ],
        })
        parsed = security_scan._parse_findings(raw)
        self.assertEqual([f["severity"] for f in parsed["findings"]],
                         ["Critical", "Low", "Info"])
        self.assertEqual(parsed["summary"], "ok")

    def test_parse_findings_handles_garbage(self):
        parsed = security_scan._parse_findings("I could not do that")
        self.assertEqual(parsed["findings"], [])
        self.assertEqual(parsed["summary"], "")

    def test_parse_recon(self):
        raw = '```json\n{"technologies": ["Flask"], "potential_vectors": ["SQLi"]}\n```'
        recon = security_scan._parse_recon(raw)
        self.assertEqual(recon["technologies"], "Flask")
        self.assertEqual(recon["potential_vectors"], "SQLi")

    def test_sanitize_url_rejects_private_hosts(self):
        for bad in ("http://127.0.0.1", "http://localhost:5000", "http://192.168.1.1",
                    "file:///etc/passwd", ""):
            with self.assertRaises(ValueError):
                security_scan.sanitize_url(bad)

    def test_sanitize_url_adds_scheme(self):
        # example.com resolves publicly, so the SSRF guard passes.
        self.assertEqual(security_scan.sanitize_url("example.com"),
                         "https://example.com")

    def test_security_scan_uses_prompts(self):
        with mock.patch.object(security_scan, "call_ai",
                               return_value='{"summary": "s", "findings": []}') as m:
            out = security_scan.security_scan("print(1)", mode="deep",
                                              recon={"attack_surface": "flask app"})
        self.assertEqual(out["summary"], "s")
        prompt = m.call_args[0][0]
        self.assertIn("flask app", prompt)
        self.assertIn("print(1)", prompt)

    def test_security_scan_validates_input(self):
        with self.assertRaises(ValueError):
            security_scan.security_scan("   ")
        with self.assertRaises(ValueError):
            security_scan.security_recon("x" * (security_scan.MAX_TARGET_CHARS + 1))

    def test_security_recon_parses(self):
        with mock.patch.object(security_scan, "call_ai",
                               return_value='```json\n{"attack_surface": "web"}\n```'):
            self.assertEqual(security_scan.security_recon("code")["attack_surface"], "web")


class TestCodeAgent(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        (self.root / "src" / "app.py").write_text(
            "def login(user):\n    return db.connect(user)\n", encoding="utf-8"
        )
        (self.root / "node_modules").mkdir()
        (self.root / "node_modules" / "big.js").write_text("x" * 10, encoding="utf-8")
        self.addCleanup(self.tmp.cleanup)

    def test_list_dir(self):
        out = code_agent.run_tool("list_dir", {"path": "src"}, self.root)
        self.assertIn("app.py", out)

    def test_read_file_line_numbers(self):
        out = code_agent.run_tool("read_file", {"path": "src/app.py"}, self.root)
        self.assertIn("    1| def login", out)

    def test_read_file_missing(self):
        self.assertTrue(
            code_agent.run_tool("read_file", {"path": "nope.py"}, self.root).startswith("ERROR")
        )

    def test_path_escape_blocked(self):
        out = code_agent.run_tool("read_file", {"path": "../../Windows/win.ini"}, self.root)
        self.assertIn("ERROR", out)

    def test_grep_ignores_node_modules(self):
        out = code_agent.run_tool("grep", {"pattern": "x"}, self.root)
        self.assertEqual(out, "No matches for /x/")

    def test_grep_finds_matches(self):
        out = code_agent.run_tool("grep", {"pattern": "def login", "glob": "*.py"}, self.root)
        self.assertIn("src/app.py:1", out)

    def test_unknown_tool(self):
        self.assertIn("ERROR", code_agent.run_tool("rm_rf", {}, self.root))

    def test_parse_tool_call(self):
        self.assertEqual(
            code_agent._parse_tool_call('{"tool": "grep", "pattern": "x"}'),
            ("grep", {"tool": "grep", "pattern": "x"}),
        )
        self.assertIsNone(code_agent._parse_tool_call("Here is the answer."))

    def test_parse_tool_call_shorthand(self):
        self.assertEqual(
            code_agent._parse_tool_call('```json\n{"list_directory": {"path": "src"}}\n```'),
            ("list_dir", {"path": "src"}),
        )
        self.assertEqual(
            code_agent._parse_tool_call('{"tool": "read_file", "arguments": {"path": "a.py"}}'),
            ("read_file", {"path": "a.py"}),
        )
        self.assertIsNone(code_agent._parse_tool_call('{"unknown_tool": {}}'))

    def test_malformed_json_is_retried(self):
        responses = [
            '{"list_directory": {"path": "src"}}',  # shorthand → list_dir
            '{"foo": 1}',                              # unrecognised → retry
            "Final answer: it is in src/app.py.",
        ]
        with mock.patch.object(code_agent, "call_ai", side_effect=responses):
            answer = code_agent.ask_about_project("Where?", self.root)
        self.assertIn("src/app.py", answer)

        # example.com resolves publicly, so the SSRF guard passes.
        self.assertEqual(security_scan.sanitize_url("example.com"),
                         "https://example.com")

    def test_ask_about_project_loop(self):
        responses = [
            '{"tool": "grep", "pattern": "def login", "glob": "*.py"}',
            "The login helper lives in src/app.py:1.",
        ]
        seen = []
        with mock.patch.object(code_agent, "call_ai", side_effect=responses):
            answer = code_agent.ask_about_project(
                "Where is login?", self.root, on_tool_call=lambda *a: seen.append(a)
            )
        self.assertIn("src/app.py:1", answer)
        self.assertEqual(seen[0][0], "grep")

    def test_ask_about_project_max_steps(self):
        with mock.patch.object(code_agent, "call_ai",
                               return_value='{"tool": "list_dir", "path": "."}'):
            with self.assertRaises(RuntimeError):
                code_agent.ask_about_project("loop forever", self.root, max_steps=2)

    def test_ask_about_project_validates(self):
        with self.assertRaises(ValueError):
            code_agent.ask_about_project("", self.root)
        with self.assertRaises(ValueError):
            code_agent.ask_about_project("q", str(self.root / "missing"))


class TestCoverLetter(unittest.TestCase):
    def test_clean_letter(self):
        raw = "John Doe\n.\n\n,,\n\nDear Hiring Manager,\n\nI am excited."
        cleaned = cover_letter._clean_letter(raw)
        self.assertNotIn(",,", cleaned)
        self.assertTrue(cleaned.startswith("John Doe"))
        self.assertIn("Dear Hiring Manager,", cleaned)

    def test_generate_cover_letter_validation(self):
        with self.assertRaises(ValueError):
            cover_letter.generate_cover_letter("", cv_text="cv")
        with self.assertRaises(ValueError):
            cover_letter.generate_cover_letter("job", cv_text="")

    def test_generate_cover_letter_uses_tone(self):
        with mock.patch.object(cover_letter, "call_ai", return_value="Letter") as m:
            out = cover_letter.generate_cover_letter(
                "Python dev", cv_text="CV text", tone="concise"
            )
        self.assertEqual(out, "Letter")
        self.assertIn("300 words", m.call_args[0][0])


class TestTranscribeMime(unittest.TestCase):
    def test_ios_voice_memos_types(self):
        self.assertEqual(_mime_for(Path("New Recording.m4a")), "audio/mp4")
        self.assertEqual(_mime_for(Path("rec.m4r")), "audio/mp4")
        self.assertEqual(_mime_for(Path("rec.aac")), "audio/aac")
        self.assertEqual(_mime_for(Path("rec.caf")), "audio/x-caf")

    def test_common_types(self):
        self.assertEqual(_mime_for(Path("a.mp3")), "audio/mpeg")
        self.assertEqual(_mime_for(Path("a.wav")), "audio/wav")
        self.assertEqual(_mime_for(Path("a.unknown")), "application/octet-stream")


if __name__ == "__main__":
    unittest.main()
