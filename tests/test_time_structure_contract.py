"""Regressions for the shot-order time structure.

Seedance 2.0 keys on shot order rather than timestamps (official guidance recorded
2026-09-26). These tests keep the shipped guidance, the vocabulary skeletons, the
quickstarts, and the eval suite aligned with that rule and with the Safe /
Stretch / Ambitious ladder that replaced the old shots-times-seconds budget.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SECOND_RANGE = re.compile(r"\b0\s*[-–]\s*3\s*(?:s|秒|초)")
FENCED_BLOCK = re.compile(r"```[^\n]*\n(.*?)```", re.S)


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class TimeStructureContractTests(unittest.TestCase):
    def test_multishot_grammar_states_shot_order_and_the_ladder(self) -> None:
        text = read("references/multishot-grammar.md")
        for phrase in (
            "shot order",
            "镜头1",
            "**Safe**",
            "**Stretch**",
            "**Ambitious**",
            "authored heuristic",
            "S = D ÷ (beats + L)",
            "Do not write absolute seconds inside shot blocks on 2.0",
            "one finished prompt",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_vocabulary_skeletons_use_shot_order_not_second_ranges(self) -> None:
        for relative in (
            "references/vocab/zh.md",
            "references/vocab/ja.md",
            "references/vocab/ko.md",
        ):
            text = read(relative)
            with self.subTest(relative=relative):
                self.assertIn("## Shot Order Template", text)
                blocks = FENCED_BLOCK.findall(text)
                self.assertTrue(blocks)
                for block in blocks:
                    self.assertIsNone(SECOND_RANGE.search(block), block)

    def test_prompt_skills_carry_the_ladder_and_one_finished_prompt(self) -> None:
        full = read("skills/seedance-prompt/SKILL.md")
        short = read("skills/seedance-prompt-short/SKILL.md")
        for text in (full, short):
            self.assertIn("multishot-grammar", text)
            self.assertIn("one finished prompt", text)
            self.assertNotIn("shots-times-seconds", text)
        for rung in ("**Safe**", "**Stretch**", "**Ambitious**"):
            self.assertIn(rung, full)
        self.assertIn("Never write absolute seconds", full)

    def test_compiler_and_density_reference_the_official_rule(self) -> None:
        self.assertIn("Emit no absolute seconds inside a block", read("references/prompt-compiler.md"))
        density = read("references/event-density.md")
        self.assertIn("## Official Density Warning", density)
        self.assertIn("S = duration ÷ (beats + load)", density)

    def test_quickstarts_explain_shots_not_seconds(self) -> None:
        expected = {
            "docs/QUICKSTART.md": "Shots, not seconds",
            "docs/QUICKSTART.zh.md": "按镜头，不按秒数",
            "docs/QUICKSTART.ja.md": "秒数ではなくショットで",
            "docs/QUICKSTART.ko.md": "초가 아니라 샷으로",
            "docs/QUICKSTART.es.md": "Planos, no segundos",
            "docs/QUICKSTART.ru.md": "Кадры, а не секунды",
        }
        for relative, phrase in expected.items():
            with self.subTest(relative=relative):
                self.assertIn(phrase, read(relative))

    def test_eval_suite_covers_the_time_structure(self) -> None:
        cases = {case["id"]: case for case in json.loads(read("evals/evals.json"))["cases"]}
        for case_id in (
            "continuous_shape_gets_one_paragraph",
            "dialogue_storyboard_offers_ladder_with_split",
            "zh_storyboard_uses_shot_order_not_second_ranges",
            "newer_line_timestamp_request_stays_in_boundary",
        ):
            with self.subTest(case_id=case_id):
                self.assertIn(case_id, cases)
        continuous = cases["continuous_take_uses_phases_not_shot_labels"]
        self.assertNotIn("(for example 0-3s, 3-7s, 7-10s)", continuous["expected_output"])
        for case in cases.values():
            for assertion in case["assertions"]:
                self.assertNotIn("shots-times-seconds", assertion, case["id"])


if __name__ == "__main__":
    unittest.main()
