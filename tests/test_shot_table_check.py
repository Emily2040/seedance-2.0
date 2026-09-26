"""The shot-table lint: every storyboard block states a camera side and the light."""

from __future__ import annotations

import unittest
from pathlib import Path

from scripts import shot_table_check

ROOT = Path(__file__).resolve().parents[1]


class ShotTableCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.traps = shot_table_check.load_traps()

    def test_blocks_split_on_markers_in_five_languages(self) -> None:
        for prompt, count in (
            ("Shot 1. A. Shot 2. B. Shot 3. C.", 3),
            ("镜头1：甲。镜头2：乙。", 2),
            ("ショット1：あ。ショット2：い。ショット3：う。ショット4：え。", 4),
            ("샷 1: 가. 샷 2: 나.", 2),
            ("Кадр 1. А. Кадр 2. Б.", 2),
            ("One continuous paragraph with no markers.", 0),
        ):
            with self.subTest(prompt=prompt):
                self.assertEqual(len(shot_table_check.split_blocks(prompt)), count)

    def test_a_block_without_a_camera_side_or_light_is_a_finding(self) -> None:
        prompt = ("Shot 1. Wide shot; she enters. Light: grey daylight. Camera at the back. "
                  "Shot 2. Cut to her face; she sits. Same light. "
                  "Shot 3. Cut to him; he speaks. Camera by the counter.")
        findings = shot_table_check.check_prompt(prompt, self.traps)
        self.assertEqual(findings, ["block 2: no camera side stated", "block 3: no light stated"])

    def test_a_trap_phrase_is_a_finding(self) -> None:
        prompt = "镜头1：他脸沉下来。灯光不变。机位在门口。"
        findings = shot_table_check.check_prompt(prompt, self.traps)
        self.assertIn("block 1: trap phrase '脸沉下来'", findings)

    def test_a_continuous_prompt_is_not_linted(self) -> None:
        self.assertEqual(shot_table_check.check_prompt("A single paragraph, no shots.", self.traps), [])

    def test_shipped_gallery_prompts_pass(self) -> None:
        for label, prompt in shot_table_check.prompts_in_json(ROOT / "data/front-page-clips.json"):
            with self.subTest(clip=label):
                self.assertEqual(shot_table_check.check_prompt(prompt, self.traps), [])

    def test_cli_lints_a_text_file(self) -> None:
        import contextlib, io, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prompt.txt"
            path.write_text("Shot 1. Wide. Camera at the door. Light: one lamp. Shot 2. Cut to him.", encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = shot_table_check.main(["--text", str(path)])
            self.assertEqual(code, 1)
            self.assertIn("block 2: no camera side stated", out.getvalue())


if __name__ == "__main__":
    unittest.main()
