"""The stress scorer must not invent defects.

Its first draft failed the repository's own golden prompts on dimensions they
had actually satisfied - an edit prompt that preserves the source lighting was
scored as having no lighting, and a continuation that binds to accepted footage
in prose was scored as having no reference binding. A checker that cries wolf
gets ignored, so the fairness rules are pinned here.
"""

from __future__ import annotations

import re
import statistics
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import prompt_architecture_stress as stress  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "examples" / "golden-prompts"

GOLDEN_MODES = {
    "compact-i2v": "I2V",
    "continuation-observed-deviation": "EXTEND",
    "dense-2d-storyboard": "T2V",
    "first-last-frame-transition": "FLF2V",
    "phased-single-take": "T2V",
    "r2v-role-isolation": "R2V",
    "sequence-continuation": "EXTEND",
    "video-edit-one-layer": "EDIT",
}


def compiled(path: Path) -> str:
    tail = path.read_text(encoding="utf-8").split("## Compiled Natural-Language Prompt", 1)[1]
    for marker in ("\n## Lint Result", "\n## Control-Critical Sentences"):
        if marker in tail:
            tail = tail.split(marker, 1)[0]
    return re.sub(r"\s+", " ", tail.strip().strip("`")).strip()


class FairnessTests(unittest.TestCase):
    # "Keep the same lens" is a camera decision even though nothing moves, but
    # only a mode with a source to preserve gets to make that argument.
    KEPT = "Continue from the observed final frame; keep the same light and lens."

    def test_preserving_a_dimension_addresses_it_on_a_continuation(self) -> None:
        score, note = stress.score_coverage(self.KEPT, "EXTEND")
        self.assertIn("preservation: camera", note)
        self.assertNotIn("camera", note.split("(")[0])

    def test_preservation_does_not_count_for_text_to_video(self) -> None:
        t2v = stress.score_coverage(self.KEPT, "T2V")
        self.assertIn("camera", t2v[1])
        self.assertLess(t2v[0], stress.score_coverage(self.KEPT, "EXTEND")[0])

    def test_prose_binding_is_a_real_binding(self) -> None:
        prose = "Start with the accepted final frame: she is two steps from the door."
        self.assertGreaterEqual(stress.score_refs(prose, "EXTEND")[0], 3.0)

    def test_no_binding_at_all_is_still_a_finding(self) -> None:
        self.assertEqual(stress.score_refs("She walks to the door and stops.", "EXTEND")[0], 0.0)

    def test_camera_hold_and_signal_light_are_detected(self) -> None:
        self.assertTrue(stress.CAMERA.search("One continuous camera hold, no cuts."))
        self.assertTrue(stress.LIGHT.search("a red signal light reflects across the puddle"))
        self.assertTrue(stress.SOUND.search("breathing steady"))


class ShippedExampleTests(unittest.TestCase):
    def test_every_golden_prompt_clears_the_release_bar(self) -> None:
        scores = []
        for path in sorted(GOLDEN.glob("*.md")):
            mode = GOLDEN_MODES.get(path.stem)
            self.assertIsNotNone(mode, f"{path.stem} needs a mode in GOLDEN_MODES")
            result = stress.score_prompt(
                {"id": path.stem, "arm": "shipped_golden", "mode": mode,
                 "brief": path.stem, "prompt": compiled(path)}
            )
            scores.append(result["overall"])
            self.assertGreaterEqual(result["overall"], 3.0, f"{path.stem}: {result['dims']}")
        self.assertGreaterEqual(statistics.mean(scores), 3.5)


class DoctrineArmTests(unittest.TestCase):
    def test_the_doctrine_arm_still_beats_the_other_two(self) -> None:
        import json
        corpus = json.loads((ROOT / "evals" / "prompt-architecture-stress.json").read_text("utf-8"))
        by_arm: dict[str, list[float]] = {}
        for record in corpus:
            by_arm.setdefault(record["arm"], []).append(stress.score_prompt(record)["overall"])
        doctrine = statistics.mean(by_arm["skill_formula"])
        self.assertGreaterEqual(doctrine, 3.5)
        for arm in ("quickstart_style", "naive_online"):
            self.assertLess(statistics.mean(by_arm[arm]), doctrine)


if __name__ == "__main__":
    unittest.main()
