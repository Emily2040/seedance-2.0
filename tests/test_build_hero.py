"""The masthead pair must stay generated, identical in geometry, and on-system.

The dark and light SVGs differ only by palette. Hand-editing them invites one
specific bug: a change landing in one theme and not the other, unnoticed
because most readers only ever see one. These tests pin that the committed
files come from the generator and that the design rules the audit cannot
express are actually held.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_hero  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RETIRED = ("viewfinder", "crosshair", "timecode", "sprocket", "REC", "21:9")


class GeneratorTests(unittest.TestCase):
    def test_committed_files_match_the_generator(self) -> None:
        for path, content in build_hero.targets().items():
            with self.subTest(asset=path.name):
                self.assertTrue(path.exists(), f"{path.name} is missing")
                self.assertEqual(
                    path.read_text(encoding="utf-8"),
                    content,
                    f"{path.name} is stale; re-run scripts/build_hero.py",
                )

    def test_themes_share_geometry_and_differ_only_in_colour(self) -> None:
        """Strip every colour: what remains must be byte-identical."""
        stripped = []
        for theme in ("dark", "light"):
            svg = build_hero.build(theme)
            stripped.append(re.sub(r"#[0-9A-Fa-f]{6}", "#", svg))
        self.assertEqual(stripped[0], stripped[1], "the two themes have drifted apart structurally")

    def test_palettes_are_actually_different(self) -> None:
        dark = set(re.findall(r"#[0-9A-Fa-f]{6}", build_hero.build("dark")))
        light = set(re.findall(r"#[0-9A-Fa-f]{6}", build_hero.build("light")))
        self.assertFalse(dark & light, "a colour is shared between themes")


class DesignRuleTests(unittest.TestCase):
    """Rules from references/frontend-design-system.md that design_audit.py
    cannot check, because they are about what must be absent."""

    def svgs(self) -> list[str]:
        return [build_hero.build(theme) for theme in ("dark", "light")]

    def test_no_retired_camera_motifs(self) -> None:
        for svg in self.svgs():
            for motif in RETIRED:
                self.assertNotIn(motif, svg, f"retired camera motif present: {motif}")

    def test_exactly_one_accent_gesture(self) -> None:
        for theme in ("dark", "light"):
            svg = build_hero.build(theme)
            accent = build_hero.THEMES[theme]["accent"]
            self.assertEqual(
                svg.count(accent), 1, "the accent hue must appear exactly once per composition"
            )

    def test_only_two_hairlines_plus_one_registration_tick(self) -> None:
        for svg in self.svgs():
            self.assertEqual(svg.count("<line"), 3)

    def test_no_gradients_blur_or_external_references(self) -> None:
        for svg in self.svgs():
            self.assertNotIn("linearGradient", svg)
            self.assertNotIn("feGaussianBlur", svg)
            self.assertNotIn("http://www.w3.org/1999/xlink", svg)
            self.assertIsNone(re.search(r"href=[\"']https?://", svg))

    def test_no_counts_or_version_numbers_are_baked_in(self) -> None:
        """The design system forbids these: they go stale in place."""
        for svg in self.svgs():
            body = svg.split("</desc>", 1)[1]
            self.assertIsNone(
                re.search(r"\bv?\d+\.\d+\.\d+\b", body), "a version number is baked into the masthead"
            )

    def test_accessible_title_and_description(self) -> None:
        for svg in self.svgs():
            self.assertIn("<title>", svg)
            self.assertIn("<desc>", svg)


if __name__ == "__main__":
    unittest.main()
