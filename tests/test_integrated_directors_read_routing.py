"""Integration proof for portable root routing plus the mandatory Director's Read."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import behavior_contract_check as behavior  # noqa: E402
import install_codex_skill as installer  # noqa: E402
import validate_skills  # noqa: E402


def assert_combined_contract(test: unittest.TestCase, root: Path) -> None:
    portable_errors: list[str] = []
    validate_skills.validate_portable_routes(root / "SKILL.md", root, portable_errors)
    test.assertEqual(portable_errors, [])

    directors_read_errors: list[str] = []
    behavior.validate_directors_read_routes(root, directors_read_errors)
    test.assertEqual(directors_read_errors, [])

    text = (root / "SKILL.md").read_text(encoding="utf-8")
    test.assertIn("## Director's Read Gate", text)
    test.assertIn("[Director's Read](references/directors-read.md)", text)
    test.assertNotIn("[ref:directors-read]", text.casefold())


class IntegratedDirectorsReadRoutingTests(unittest.TestCase):
    def install(self, destination: Path) -> Path:
        original_argv = sys.argv
        sys.argv = ["install_codex_skill.py", "--dest", str(destination)]
        try:
            self.assertEqual(installer.main(), 0)
        finally:
            sys.argv = original_argv
        return destination / installer.SKILL_NAME

    def test_checkout_combines_portable_routes_and_required_read(self) -> None:
        assert_combined_contract(self, ROOT)

    def test_route_literals_are_forward_slash_relative_paths(self) -> None:
        for rel, target in behavior.DIRECTORS_READ_ROUTES.items():
            self.assertNotIn("\\", target, rel)
            self.assertNotIn(":", target, rel)
            self.assertFalse(target.startswith("/"), rel)
            self.assertTrue(target.endswith("directors-read.md"), rel)

    def test_installed_payload_with_spaces_keeps_every_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self.install(Path(tmp) / "client with spaces" / "skills")
            assert_combined_contract(self, payload)

    def test_zip_extraction_and_foreign_cwd_keep_every_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temporary = Path(tmp)
            payload = self.install(temporary / "source client" / "skills")
            archive = temporary / "portable-skill.zip"
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
                for path in sorted(payload.rglob("*")):
                    if path.is_file():
                        bundle.write(
                            path,
                            Path(installer.SKILL_NAME) / path.relative_to(payload),
                        )

            extracted = temporary / "other client with spaces"
            with zipfile.ZipFile(archive) as bundle:
                bundle.extractall(extracted)

            foreign_cwd = temporary / "unrelated working directory"
            foreign_cwd.mkdir()
            previous = Path.cwd()
            os.chdir(foreign_cwd)
            try:
                assert_combined_contract(self, extracted / installer.SKILL_NAME)
            finally:
                os.chdir(previous)

    def test_nonportable_route_spellings_are_rejected(self) -> None:
        mutations = (
            "References/directors-read.md",
            "references\\directors-read.md",
            "C:/skills/references/directors-read.md",
            "//server/share/references/directors-read.md",
        )
        with tempfile.TemporaryDirectory() as tmp:
            payload = self.install(Path(tmp) / "skills")
            skill = payload / "SKILL.md"
            original = skill.read_text(encoding="utf-8")
            for mutation in mutations:
                with self.subTest(mutation=mutation):
                    skill.write_text(
                        original.replace("references/directors-read.md", mutation),
                        encoding="utf-8",
                    )
                    errors: list[str] = []
                    behavior.validate_directors_read_routes(payload, errors)
                    self.assertTrue(any("must link" in error for error in errors), errors)
            skill.write_text(original, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
