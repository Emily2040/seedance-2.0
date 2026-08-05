"""Focused contracts for active reference and prompt examples."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def section(text: str, heading: str, next_heading: str) -> str:
    return text.split(heading, 1)[1].split(next_heading, 1)[0]


def copyable_prompt(text: str) -> str:
    prompts = re.findall(r"`([^`\r\n]+)`", text)
    if len(prompts) != 1:
        raise AssertionError(f"expected exactly one copyable prompt, found {len(prompts)}")
    return prompts[0]


class ReferenceExampleTests(unittest.TestCase):
    def test_active_sequence_examples_use_canonical_reference_tags(self) -> None:
        for relative in (
            "references/reference-workflow.md",
            "references/examples-by-mode.md",
        ):
            text = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(relative=relative):
                self.assertNotIn("[Video 1]", text)
                self.assertNotIn("@Image 1", text)
                self.assertIn("@Video1", text)
                self.assertIn("@Image1", text)

    def test_extend_examples_bind_planned_delta_to_observed_source_state(self) -> None:
        text = (ROOT / "references/examples-by-mode.md").read_text(encoding="utf-8")
        v2v = section(text, "## V2V Extend", "## R2V Role Map")
        sequence = section(
            text,
            "## Sequence Continuation Example",
            "## Standalone Non-Overplanning Example",
        )

        for name, example in (("v2v", v2v), ("sequence", sequence)):
            with self.subTest(example=name):
                prompt = copyable_prompt(example)
                self.assertIn("@Video1", prompt)
                self.assertRegex(prompt, r"actual (?:observed )?opening state")
                self.assertIn("reviewed ending", prompt)
                self.assertNotRegex(prompt.lower(), r"\b(?:planned|unobserved)\b")
                self.assertNotIn("[Video 1]", prompt)
                self.assertNotIn("@Image 1", prompt)


class NarrativePromptExampleTests(unittest.TestCase):
    def test_hallway_drama_carries_specific_behavior_and_replacement(self) -> None:
        text = (ROOT / "references/prompt-examples.md").read_text(encoding="utf-8")
        prompt = section(text, "## T2V Character Drama", "## I2V Portrait Micro-Performance")
        for required in (
            "crooked green library-return sticker",
            "smooths the same creased corner flat twice",
            "A key enters the lock outside",
            "hold the silence instead of adding music",
        ):
            self.assertIn(required, prompt)

    def test_rooftop_action_carries_specific_behavior_and_replacement(self) -> None:
        text = (ROOT / "references/prompt-examples.md").read_text(encoding="utf-8")
        prompt = section(text, "## Action Beat", "## Safe Original Animation")
        for required in (
            "one strip of blue cloth tape",
            "starts toward the knee, then clamps the canister strap instead",
            "the jump in real time",
            "instead of cutting to an impact montage",
        ):
            self.assertIn(required, prompt)


if __name__ == "__main__":
    unittest.main()
