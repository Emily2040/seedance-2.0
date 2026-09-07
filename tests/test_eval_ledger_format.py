"""Compatibility and integrity checks around the extracted pure formatter."""
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType
import unittest
from unittest.mock import patch

from scripts import eval_run
from scripts import eval_ledger_format as formatting


class LedgerFormatExtractionTests(unittest.TestCase):
    def test_existing_imports_are_the_same_functions(self):
        for name in ("_is_utf8_encodable", "_ledger_row_sort_key", "_safe_ledger_text",
                     "_safe_markdown_code", "_safe_markdown_text", "_regeneration_argv",
                     "_powershell_quote", "_regeneration_command_lines"):
            self.assertIs(getattr(eval_run, name), getattr(formatting, name))

    def test_untrusted_markdown_and_line_boundaries_remain_inert(self):
        self.assertEqual(formatting._safe_ledger_text("a|b\r\nc\u2028d"), "a/b c d")
        self.assertEqual(formatting._safe_markdown_code("`test`"), "'test'")
        self.assertEqual(formatting._safe_markdown_text("<script>[x](url)"), "&lt;script&gt;\\[x\\]\\(url\\)")
        self.assertEqual(formatting._safe_ledger_text("bad\ud800"), "[invalid Unicode string]")

    def test_shell_metadata_stays_offline_and_rejects_injection(self):
        args = formatting._regeneration_argv("anthropic", "global_en", "model-1", "judge-1")
        self.assertNotIn("--live", args)
        lines = formatting._regeneration_command_lines(args)
        self.assertIn("python scripts/eval_run.py --provider anthropic --region global_en --model model-1 --judge-model judge-1 --ledger evals/eval-run-ledger.md", lines)
        self.assertIsNone(formatting._regeneration_argv("anthropic", "global_en", "$(secret)", "judge-1"))

    def test_extracted_module_remains_evaluator_only(self):
        snapshot = eval_run.freeze_repository(Path(__file__).resolve().parents[1])
        self.assertEqual(snapshot.require("scripts/eval_ledger_format.py", "evaluator").role, "evaluator")
        eval_run._verify_evaluator_modules(snapshot)
        payload = (snapshot.root / "validation/install-payload.txt").read_text(encoding="utf-8").splitlines()
        self.assertNotIn("scripts/eval_ledger_format.py", payload)

    def test_substituted_formatter_bytecode_is_rejected(self):
        snapshot = eval_run.freeze_repository(Path(__file__).resolve().parents[1])
        with patch.object(formatting, "_EXECUTED_CODE", compile("pass", "substitute", "exec")):
            with self.assertRaisesRegex(eval_run.HarnessError, "formatter code"):
                eval_run._verify_evaluator_modules(snapshot)

    def test_frozen_formatter_source_drift_is_rejected(self):
        snapshot = eval_run.freeze_repository(Path(__file__).resolve().parents[1])
        files = dict(snapshot.files)
        key = "scripts/eval_ledger_format.py"
        files[key] = replace(files[key], text=files[key].text + "\n# changed\n")
        altered = replace(snapshot, files=MappingProxyType(files))
        with self.assertRaisesRegex(eval_run.HarnessError, "formatter digest"):
            eval_run._verify_evaluator_modules(altered)
