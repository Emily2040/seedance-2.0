import copy
import unittest
import json
from pathlib import Path

from scripts.outcome_comparison import ARMS, assess, compare


def good():
    return {"status": "scored", "gates": {"safety": True, "state": True, "reference_fidelity": True},
            "dimensions": {"brief_fidelity": 3, "directability": 3, "specificity": 3, "user_control": 3},
            "route_matches": False, "error": None}


class OutcomeComparisonTests(unittest.TestCase):
    def test_calibration_oracle_is_excluded_from_responder_and_install(self):
        root = Path(__file__).resolve().parents[1]
        manifest = json.loads((root / "evals/source-manifest.json").read_text(encoding="utf-8"))
        entry = next(e for e in manifest["sources"] if e["path"] == "references/outcome-comparison.md")
        self.assertEqual(entry["role"], "evaluator")
        payload = (root / "validation/install-payload.txt").read_text(encoding="utf-8").splitlines()
        self.assertNotIn(entry["path"], payload)
        self.assertNotIn("scripts/outcome_comparison.py", payload)

    def test_equivalent_route_can_pass(self):
        self.assertTrue(assess(good())["passed"])

    def test_route_diagnostic_survives_without_changing_quality(self):
        rows = [{"case_id": "one", "arm": a, "judgment": good()} for a in ARMS]
        before = compare(["one"], rows)
        rows[0]["judgment"]["route_matches"] = True
        after = compare(["one"], rows)
        self.assertEqual(after["arms"]["current"]["route_matches"], 1)
        self.assertEqual(after["arms"]["current"]["route_mismatches"], 0)
        self.assertEqual(before["arms"]["current"]["route_matches"], 0)
        self.assertEqual(before["arms"]["current"]["mean_score"], after["arms"]["current"]["mean_score"])
        self.assertEqual(before["arms"]["current"]["passed"], after["arms"]["current"]["passed"])

    def test_generic_prose_and_hard_gate_fail_independently(self):
        for category, key, value in [("dimensions", "specificity", 0), ("gates", "state", False),
                                     ("gates", "safety", False), ("gates", "reference_fidelity", False)]:
            with self.subTest(key=key):
                record = good()
                record[category][key] = value
                self.assertFalse(assess(record)["passed"])

    def test_error_is_never_a_score(self):
        error = {"status": "harness_error", "gates": None, "dimensions": None, "route_matches": None, "error": "timeout"}
        self.assertEqual(assess(error), {"status": "harness_error", "score": None, "passed": None, "route_matches": None})
        rows = [{"case_id": "one", "arm": a, "judgment": good()} for a in ARMS]
        rows[0]["judgment"] = error
        report = compare(["one"], rows)
        self.assertFalse(report["complete"])
        self.assertTrue(all(a["mean_score"] is None for a in report["arms"].values()))
        self.assertEqual(report["arms"]["current"]["route_matches"], 0)
        self.assertEqual(report["arms"]["current"]["route_mismatches"], 0)

    def test_missing_rows_do_not_create_partial_average(self):
        report = compare(["one"], [{"case_id": "one", "arm": "current", "judgment": good()}])
        self.assertFalse(report["complete"])
        self.assertEqual(report["arms"]["plain"]["missing"], 1)
        self.assertIsNone(report["arms"]["current"]["mean_score"])

    def test_complete_comparison_is_still_not_release_evidence(self):
        rows = [{"case_id": "one", "arm": a, "judgment": good()} for a in ARMS]
        report = compare(["one"], rows)
        self.assertTrue(report["complete"])
        self.assertFalse(report["release_eligible"])
        self.assertEqual(report["arms"]["proposed"]["mean_score"], 3)
        with self.assertRaises(ValueError):
            compare(["one"], rows + rows[:1])
        rows[0]["case_id"] = "unexpected"
        with self.assertRaises(ValueError):
            compare(["one"], rows)

    def test_malformed_judgments_rejected(self):
        mutations = [lambda r: r.update(extra=True), lambda r: r.update(error="timeout"),
                     lambda r: r["dimensions"].update(specificity=True),
                     lambda r: r["gates"].update(state=1), lambda r: r.update(route_matches=1),
                     lambda r: r["dimensions"].pop("specificity"),
                     lambda r: r["dimensions"].update(specificity=4)]
        for mutate in mutations:
            record = copy.deepcopy(good())
            mutate(record)
            with self.assertRaises(ValueError):
                assess(record)
