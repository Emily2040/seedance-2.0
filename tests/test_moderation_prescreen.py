"""The moderation pre-screen: cue lists, lint behaviour, and route wiring.

Two gallery prompts were refused by a platform classifier before rendering on
2026-09-26. The screen exists so a benign scene is rewritten before delivery
rather than refused after a credit is spent, and so no refusable prompt ships
as an example.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts import moderation_prescreen as screen

ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class CueMatchingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.compiled = screen.compile_cues(screen.load_cues())

    def scan(self, text: str) -> dict:
        return screen.scan_text(text, self.compiled)

    def test_latin_cues_match_words_not_substrings(self) -> None:
        self.assertEqual(self.scan("a stable bottle on a stable table"), {})
        self.assertIn("injury", self.scan("her split lip"))
        self.assertIn("weapon", self.scan("a kitchen knife held low"))
        self.assertNotIn("crime", self.scan("she has a skill for this"))

    def test_cjk_and_cyrillic_cues_match_as_written(self) -> None:
        self.assertIn("weapon", self.scan("刀光横过画面"))
        self.assertIn("minor", self.scan("少女が木刀を構える"))
        self.assertIn("injury", self.scan("кровавый след на снегу"))
        self.assertIn("institution", self.scan("이혼 서류에 서명한다"))

    def test_severity_rules(self) -> None:
        hits_minor_alone = self.scan("a boy waits at school")
        self.assertEqual(screen.effective_severity("minor", "medium", hits_minor_alone), "medium")
        stacked = self.scan("a teenage boy, a lawyer, a divorce agreement")
        self.assertEqual(screen.effective_severity("minor", "medium", stacked), "high")
        three_medium = self.scan("a hospital corridor, a cigarette, a ghost")
        self.assertEqual(screen.effective_severity("horror", "medium", three_medium), "high")

    def test_every_class_has_five_languages_and_a_reason(self) -> None:
        cues = screen.load_cues()
        for name, spec in cues["classes"].items():
            with self.subTest(cue_class=name):
                self.assertIn(spec["severity"], {"high", "medium"})
                self.assertTrue(spec["what_reacts"].strip())
                self.assertEqual(set(spec["cues"]), {"en", "zh", "ja", "ko", "ru"})
                for words in spec["cues"].values():
                    self.assertTrue(words)


class ShippedPromptTests(unittest.TestCase):
    def test_shipped_prompt_surfaces_carry_no_high_severity_cue(self) -> None:
        compiled = screen.compile_cues(screen.load_cues())
        high = []
        for relative in screen.DEFAULT_TARGETS:
            path = ROOT / relative
            if not path.exists():
                continue
            high.extend(f for f in screen.findings_for(path, compiled) if f.severity == "high")
        self.assertEqual(high, [], [f"{f.source} prompt {f.prompt_index}: {f.cue_class} {f.matches}" for f in high])

    def test_markdown_prompt_extraction_reads_fences_and_blockquotes(self) -> None:
        text = "intro\n\n```text\nfirst prompt\n```\n\n> quoted line one\n> quoted line two\n\nafter\n"
        self.assertEqual(screen.prompts_in_markdown(text), ["first prompt", "quoted line one quoted line two"])


class RouteWiringTests(unittest.TestCase):
    def test_reference_names_every_class(self) -> None:
        reference = read("references/moderation-prescreen.md")
        for phrase in ("## Boundary", "## When it runs", "## The cue classes", "## The method, in one pass", "never a verdict"):
            self.assertIn(phrase, reference)
        for label in ("Weapon", "Injury", "Crime", "Minor", "Institution", "Substance", "Horror", "Identity and symbols"):
            self.assertIn(f"| {label} |", reference)

    def test_routes_run_the_screen_before_delivery(self) -> None:
        self.assertIn("references/moderation-prescreen.md", read("SKILL.md"))
        for relative in (
            "skills/seedance-prompt/SKILL.md",
            "skills/seedance-prompt-short/SKILL.md",
            "skills/seedance-filter/SKILL.md",
            "skills/seedance-interview-short/SKILL.md",
        ):
            with self.subTest(relative=relative):
                self.assertIn("moderation-prescreen.md", read(relative))
        atlas = read("references/failure-atlas.md")
        self.assertIn("Prompt refused before rendering", atlas)
        self.assertIn("Character performs the accident on purpose", atlas)
        self.assertIn("## Stakes and Peak", read("references/directing-engine.md"))

    def test_reference_and_cues_ship_in_the_payload(self) -> None:
        payload = read("validation/install-payload.txt").splitlines()
        self.assertIn("references/moderation-prescreen.md", payload)
        self.assertIn("data/moderation-cues.json", payload)


if __name__ == "__main__":
    unittest.main()
