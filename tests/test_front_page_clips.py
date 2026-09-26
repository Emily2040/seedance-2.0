"""The front-page clip gallery: data, slates, README wiring and payload.

The gallery shows Seedance 2.0 output rendered from prompts the skill wrote.
These tests keep the data file, the generated slates, the README and the
install payload in step, and keep the prompts inside the repository's own rules.
"""

from __future__ import annotations

import json
import re
import unittest
from collections import Counter
from pathlib import Path

from scripts import build_clip_posters

ROOT = Path(__file__).resolve().parents[1]
SECOND_RANGE = re.compile(r"\b\d+\s*[-–]\s*\d+\s*(?:s\b|秒|초)")
STUDIO_NAMES = ("Ghibli", "ジブリ", "Disney", "Pixar", "Marvel")
TRAPS = json.loads((ROOT / "data/direction-traps.json").read_text(encoding="utf-8"))["traps"]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class FrontPageClipTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = json.loads(read("data/front-page-clips.json"))
        self.clips = self.data["clips"]
        self.readme = read("README.md")

    def test_seven_clips_in_the_requested_language_mix(self) -> None:
        self.assertEqual(len(self.clips), 7)
        self.assertEqual(Counter(clip["language"] for clip in self.clips),
                         Counter({"en": 2, "zh": 2, "ko": 1, "ja": 1, "ru": 1}))
        self.assertEqual([clip["number"] for clip in self.clips], list(range(1, 8)))

    def test_every_clip_follows_the_prompt_rules(self) -> None:
        for clip in self.clips:
            with self.subTest(clip=clip["id"]):
                self.assertIn(clip["status"], {"unrendered", "rendered"})
                self.assertTrue(4 <= clip["duration_seconds"] <= 15)
                self.assertEqual(clip["aspect"], "16:9")
                self.assertGreaterEqual(len(clip["review"]), 2)
                self.assertTrue(clip["prompt"].strip())
                self.assertIsNone(SECOND_RANGE.search(clip["prompt"]), clip["prompt"])
                for name in STUDIO_NAMES:
                    self.assertNotIn(name, clip["prompt"])
                    self.assertNotIn(name, clip["typical_brief"])
                for language, phrases in TRAPS.items():
                    for phrase in phrases:
                        self.assertNotIn(phrase, clip["prompt"], (clip["id"], phrase))
                if clip["shape"] == "storyboard":
                    self.assertTrue(any(marker in clip["prompt"] for marker in ("Shot 1", "镜头1", "샷 1", "ショット1", "Кадр 1")))
                    self.assertTrue(any(r in clip["rung"] for r in ("Safe", "Stretch")), clip["rung"])
                    self.assertIn("premise", clip)

    def test_slates_match_the_generator_and_are_shipped(self) -> None:
        self.assertEqual(build_clip_posters.check(self.clips), [])
        payload = read("validation/install-payload.txt").splitlines()
        for clip in self.clips:
            relative = f"assets/clips/{clip['id']}.svg"
            with self.subTest(slate=relative):
                self.assertIn(relative, payload)
                self.assertIn(relative, self.readme)

    def test_readme_gallery_carries_each_clip_and_its_prompt(self) -> None:
        gallery = self.readme.split("## Seen, not told", 1)[1].split("## Start Here", 1)[0]
        for clip in self.clips:
            with self.subTest(clip=clip["id"]):
                self.assertIn(f"#### Clip {clip['number']:02d}: {clip['title']}", gallery)
                self.assertIn("".join(clip["prompt"].split()), "".join(re.sub(r"^> ?", "", gallery, flags=re.M).split()))
                self.assertIn(clip["typical_brief"], gallery)


if __name__ == "__main__":
    unittest.main()
