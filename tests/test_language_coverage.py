import copy
import unittest
import json

from scripts.language_coverage import ROOT, check
from scripts.strict_json import load_json


class LanguageCoverageTests(unittest.TestCase):
    def setUp(self):
        self.contract = load_json(ROOT / "evals/language-coverage.json")

    def test_canonical_scope_is_available_but_unreviewed(self):
        report = check(ROOT, self.contract)
        stale = {language: row for language, row in report.items() if row["status"] == "stale_review_required"}
        if stale:
            print("Language coverage review flags: " + json.dumps(stale, ensure_ascii=True))
        self.assertEqual(set(report), {"en", "zh", "ja", "ko", "es", "ru"})
        for row in report.values():
            self.assertIn(row["status"], {"unchanged_unreviewed", "stale_review_required"})
            self.assertEqual(row["native_review"], "pending")
        self.assertIsNone(self.contract["languages"]["es"]["readme"])
        self.assertIsNone(self.contract["languages"]["ru"]["readme"])

    def test_source_drift_marks_all_locales(self):
        self.contract["sources"]["SKILL.md"] = "0" * 64
        report = check(ROOT, self.contract)
        self.assertTrue(all(r["status"] == "stale_review_required" for r in report.values()))

    def test_target_drift_is_locale_scoped(self):
        baseline = check(ROOT, self.contract)
        self.contract["languages"]["es"]["snapshots"]["docs/QUICKSTART.es.md"] = "0" * 64
        report = check(ROOT, self.contract)
        self.assertEqual(report["es"]["target_changes"], ["docs/QUICKSTART.es.md"])
        self.assertEqual(report["ja"], baseline["ja"])

    def test_omissions_false_parity_and_review_claims_rejected(self):
        mutations = [lambda c: c["languages"].pop("ru"),
                     lambda c: c["sources"].pop("SKILL.md"),
                     lambda c: c["languages"]["es"].update(readme="README.md"),
                     lambda c: c["languages"]["en"].update(native_review="passed"),
                     lambda c: c["languages"]["ko"]["snapshots"].clear(),
                     lambda c: c.update(version=True)]
        for mutate in mutations:
            contract = copy.deepcopy(self.contract)
            mutate(contract)
            with self.assertRaises(ValueError):
                check(ROOT, contract)
