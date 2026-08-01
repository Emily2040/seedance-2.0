"""Installed-skill scope and README reachability contracts."""

from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import install_codex_skill as installer  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_TARGET = re.compile(
    r"!?\[[^\]]*\]\(\s*<?([^\s)>]+)>?(?:\s+['\"][^'\"]*['\"])?\s*\)"
)
HTML_TARGET = re.compile(
    r"\b(?:href|src|srcset)\s*=\s*['\"]([^'\"]+)['\"]",
    re.IGNORECASE,
)


def readme_targets(text: str) -> list[str]:
    """Return Markdown and inline-HTML targets used by the README."""
    return [
        *(match.group(1) for match in MARKDOWN_TARGET.finditer(text)),
        *(match.group(1) for match in HTML_TARGET.finditer(text)),
    ]


def broken_local_targets(readme: Path, payload: Path) -> list[str]:
    """Return local README targets that do not resolve inside the install."""
    broken: list[str] = []
    payload_root = payload.resolve()
    for raw_target in readme_targets(readme.read_text(encoding="utf-8")):
        target = raw_target.strip()
        if not target or target.startswith(("#", "//")):
            continue
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        resolved = (readme.parent / unquote(parsed.path)).resolve()
        try:
            resolved.relative_to(payload_root)
        except ValueError:
            broken.append(f"{target} (escapes installed payload)")
            continue
        if not resolved.exists():
            broken.append(target)
    return sorted(set(broken))


class RuntimePayloadContractTests(unittest.TestCase):
    def install(self, destination: Path) -> Path:
        argv = sys.argv
        sys.argv = ["install_codex_skill.py", "--dest", str(destination)]
        try:
            self.assertEqual(installer.main(), 0)
        finally:
            sys.argv = argv
        return destination / installer.SKILL_NAME

    def test_quarantined_migrated_guidance_is_not_installed(self) -> None:
        archive = ROOT / "references" / "migrated"
        self.assertTrue(archive.is_dir(), "the repository must retain its history")
        self.assertIn(
            "historical comparison only",
            (archive / "README.md").read_text(encoding="utf-8"),
        )

        with tempfile.TemporaryDirectory() as tmp:
            payload = self.install(Path(tmp))
            self.assertFalse(
                (payload / "references" / "migrated").exists(),
                "explicitly quarantined legacy guidance must not enter runtime retrieval",
            )

    def test_every_installed_readme_local_target_resolves(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self.install(Path(tmp))
            readme = payload / "README.md"
            self.assertEqual(
                broken_local_targets(readme, payload),
                [],
                "an installed README must not knowingly point at omitted local files",
            )

    def test_installed_readme_routes_the_omitted_gallery_to_the_repository(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self.install(Path(tmp))
            installed_readme = (payload / "README.md").read_text(encoding="utf-8")

        self.assertIn("View the full visual gallery in the source repository", installed_readme)
        self.assertNotIn("assets/hero-command-center.png", installed_readme)
        self.assertNotIn("therefore resolve only in this repository", installed_readme)

    def test_active_guidance_and_source_gallery_remain_intact(self) -> None:
        self.assertTrue((ROOT / "assets" / "hero-command-center.png").is_file())
        self.assertIn(
            "assets/hero-command-center.png",
            (ROOT / "README.md").read_text(encoding="utf-8"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            payload = self.install(Path(tmp))
            for relative in (
                "SKILL.md",
                "skills/seedance-prompt/SKILL.md",
                "references/quick-ref.md",
                "assets/hero-dark.svg",
                "assets/skill-map.svg",
            ):
                self.assertTrue((payload / relative).is_file(), relative)

    def test_archive_policy_is_source_relative_not_name_wide(self) -> None:
        self.assertTrue(installer.is_archive_only_path(Path("references/migrated")))
        self.assertTrue(
            installer.is_archive_only_path(
                Path("references/migrated/v5.2-legacy-skill-bodies/seedance-audio.md")
            )
        )
        self.assertFalse(installer.is_archive_only_path(Path("examples/migrated")))
        self.assertFalse(installer.is_archive_only_path(Path("references/quick-ref.md")))

    def test_installed_readme_rewrite_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self.install(Path(tmp))
            readme = payload / "README.md"
            first = readme.read_text(encoding="utf-8")
            installer.rewrite_installed_readme(payload)
            self.assertEqual(readme.read_text(encoding="utf-8"), first)

    def test_installed_readme_rewrite_fails_closed_if_markers_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = Path(tmp)
            (payload / "README.md").write_text(
                "## Visual Gallery\n\n![missing](assets/missing.png)\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "must each appear exactly once"):
                installer.rewrite_installed_readme(payload)

    def test_source_readme_has_one_ordered_gallery_marker_pair(self) -> None:
        source_readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertEqual(source_readme.count(installer.README_GALLERY_START), 1)
        self.assertEqual(source_readme.count(installer.README_GALLERY_END), 1)
        self.assertLess(
            source_readme.index(installer.README_GALLERY_START),
            source_readme.index(installer.README_GALLERY_END),
        )


if __name__ == "__main__":
    unittest.main()
