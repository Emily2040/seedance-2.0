from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CANONICAL = "references/directors-read.md"
ROUTES = (
    "SKILL.md",
    "skills/seedance-interview/SKILL.md",
    "skills/seedance-interview-short/SKILL.md",
    "skills/seedance-prompt/SKILL.md",
    "skills/seedance-prompt-short/SKILL.md",
    "skills/seedance-sequence/SKILL.md",
    "skills/seedance-continuation/SKILL.md",
    "references/prompt-compiler.md",
)
NO_MEMORY_ESCAPE_FILES = ROUTES + (
    "references/directing-engine.md",
    "references/progressive-disclosure.md",
)
FIELDS = (
    "dramatic function",
    "turn",
    "POV",
    "power shift",
    "hidden want/objective",
    "obstacle/tactic",
    "subtext/contradiction",
    "visible suppressed behavior",
    "non-transferable detail",
    "stock solution refused",
)


class DirectorsReadContractTests(unittest.TestCase):
    def test_one_canonical_contract_routes_every_prompt_path(self) -> None:
        for rel in ROUTES:
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("[ref:directors-read]", text, rel)

    def test_canonical_read_has_every_required_field(self) -> None:
        text = (ROOT / CANONICAL).read_text(encoding="utf-8")
        for field in FIELDS:
            self.assertIn(f"`{field}`", text, field)

    def test_contract_pins_narrative_boundary_and_compilation_boundary(self) -> None:
        text = (ROOT / CANONICAL).read_text(encoding="utf-8").lower()
        for phrase in (
            "narrative lane",
            "non-narrative lane",
            "do not fabricate",
            "internal planning only",
            "visible or audible carriers",
            "before prompt compilation",
            "does not guarantee byte-identical",
            "model-in-the-loop benchmark",
        ):
            self.assertIn(phrase, text, phrase)

    def test_fast_routes_cannot_escape_to_memory(self) -> None:
        for rel in NO_MEMORY_ESCAPE_FILES:
            text = (ROOT / rel).read_text(encoding="utf-8").lower()
            self.assertNotIn("inline from memory", text, rel)
            self.assertNotIn("apply craft from memory", text, rel)

    def test_adversarial_cases_pin_the_same_lane_for_every_agent(self) -> None:
        cases = json.loads(
            (ROOT / "validation/fixtures/directors-read-cases.json").read_text(encoding="utf-8")
        )
        expected = {
            "silent-breakup": "narrative",
            "perfume-turntable": "non_narrative",
            "product-with-performer-choice": "narrative",
            "abstract-logo-reveal": "non_narrative",
            "dancer-masks-missed-cue": "narrative",
            "hands-only-assembly-demo": "non_narrative",
        }
        self.assertEqual(len(cases), len(expected))
        self.assertEqual({case["id"]: case["expected_lane"] for case in cases}, expected)
        for case in cases:
            if case["expected_lane"] == "narrative":
                read = case["directors_read"]
                self.assertEqual(tuple(read), FIELDS, case["id"])
                self.assertTrue(all(str(value).strip() for value in read.values()), case["id"])
                self.assertTrue(case["compiled_carriers"].strip(), case["id"])
                compiled = case["compiled_carriers"].lower()
                for field in FIELDS:
                    self.assertNotIn(f"{field.lower()}:", compiled, case["id"])
            else:
                self.assertIsNone(case["directors_read"], case["id"])
                self.assertTrue(case["utility_intent"].strip(), case["id"])
                self.assertIn("no invented", case["refusal"].lower(), case["id"])


if __name__ == "__main__":
    unittest.main()
