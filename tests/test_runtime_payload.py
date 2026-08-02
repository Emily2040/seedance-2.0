"""Installed-skill scope and README reachability contracts."""

from __future__ import annotations

import hashlib
import json
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

    def fixture_source(self, root: Path) -> Path:
        source = root / "source"
        declared = [
            "README.md",
            "SKILL.md",
            "scripts/install_codex_skill.py",
            installer.PAYLOAD_MANIFEST.as_posix(),
        ]
        readme = (
            "# Fixture\n\n"
            f"{installer.README_GALLERY_START}\n\n![missing](assets/missing.png)\n\n"
            f"{installer.README_GALLERY_END}\n\n"
            f"{installer.README_VALIDATION_START}\n\npython tests/missing.py\n\n"
            f"{installer.README_VALIDATION_END}\n"
        )
        files = {
            "README.md": readme,
            "SKILL.md": "fixture skill\n",
            "scripts/install_codex_skill.py": "# fixture installer\n",
            installer.PAYLOAD_MANIFEST.as_posix(): "\n".join(declared) + "\n",
        }
        for relative, content in files.items():
            path = source.joinpath(*relative.split("/"))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
        return source

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

    def test_installed_readme_does_not_advertise_omitted_maintenance_tools(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self.install(Path(tmp))
            installed_readme = (payload / "README.md").read_text(encoding="utf-8")

        self.assertIn("Run validation from a source checkout", installed_readme)
        self.assertNotIn("scripts/eval_run.py", installed_readme)
        self.assertNotIn("unittest discover", installed_readme)
        self.assertNotIn("compileall scripts tests", installed_readme)

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
        self.assertTrue(installer.is_archive_only_path(Path("REFERENCES/MIGRATED/README.md")))
        self.assertFalse(installer.is_archive_only_path(Path("examples/migrated")))
        self.assertFalse(installer.is_archive_only_path(Path("references/quick-ref.md")))

    def test_completion_marker_binds_the_transformed_readme_bytes(self) -> None:
        source_before = (ROOT / "README.md").read_bytes()
        source_contract = installer.load_payload_contract(ROOT)
        plan = installer.build_install_payload_plan(ROOT, source_contract)
        self.assertIsNotNone(plan.installed_readme_bytes)

        with tempfile.TemporaryDirectory() as tmp:
            payload = self.install(Path(tmp))
            installed_bytes = (payload / "README.md").read_bytes()
            marker = json.loads(
                (payload / installer.COMPLETION_MARKER).read_text(encoding="utf-8")
            )

        self.assertEqual((ROOT / "README.md").read_bytes(), source_before)
        self.assertNotEqual(installed_bytes, source_before)
        self.assertEqual(installed_bytes, plan.installed_readme_bytes)
        self.assertEqual(
            marker["files"]["README.md"],
            {
                "size": len(installed_bytes),
                "sha256": hashlib.sha256(installed_bytes).hexdigest(),
            },
        )
        self.assertEqual(marker["contract_sha256"], plan.installed_contract.contract_sha256)
        self.assertNotEqual(
            source_contract.file_manifest()["README.md"],
            plan.installed_contract.file_manifest()["README.md"],
        )

    def test_frozen_plan_rejects_readme_mutation_and_cleans_the_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.fixture_source(root)
            skills_dir = root / "skills"
            skills_dir.mkdir()
            source_contract = installer.load_payload_contract(source)
            plan = installer.build_install_payload_plan(source, source_contract)
            (source / "README.md").write_text(
                "changed after plan freeze\n",
                encoding="utf-8",
                newline="\n",
            )

            with self.assertRaisesRegex(RuntimeError, "source .* changed"):
                installer.stage_validated_install(
                    source,
                    skills_dir,
                    source_contract,
                    plan,
                )

            self.assertFalse((skills_dir / installer.TRANSACTION_NAME).exists())
            self.assertEqual(list(skills_dir.glob(f"{installer.STAGE_PREFIX}*")), [])

    def test_installed_readme_rewrite_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self.install(Path(tmp))
            readme = payload / "README.md"
            first = readme.read_text(encoding="utf-8")
            self.assertEqual(installer.rewrite_installed_readme_text(first), first)
            self.assertEqual(readme.read_text(encoding="utf-8"), first)

    def test_installed_readme_rewrite_fails_closed_if_markers_drift(self) -> None:
        with self.assertRaisesRegex(ValueError, "must each appear exactly once"):
            installer.rewrite_installed_readme_text(
                "## Visual Gallery\n\n![missing](assets/missing.png)\n"
            )

    def test_source_readme_has_one_ordered_marker_pair_per_rewritten_section(self) -> None:
        source_readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for start, end in (
            (installer.README_GALLERY_START, installer.README_GALLERY_END),
            (installer.README_VALIDATION_START, installer.README_VALIDATION_END),
        ):
            with self.subTest(start=start):
                self.assertEqual(source_readme.count(start), 1)
                self.assertEqual(source_readme.count(end), 1)
                self.assertLess(source_readme.index(start), source_readme.index(end))


if __name__ == "__main__":
    unittest.main()
