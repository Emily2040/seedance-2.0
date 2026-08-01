"""Root routing must work without private ``[skill:]``/``[ref:]`` syntax."""

from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import install_codex_skill as installer  # noqa: E402
import validate_skills  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]


def route_errors(skill_file: Path, root: Path) -> list[str]:
    errors: list[str] = []
    validate_skills.validate_portable_routes(skill_file, root, errors)
    return errors


class PortableRouteValidationTests(unittest.TestCase):
    def fixture(self, text: str) -> tuple[tempfile.TemporaryDirectory[str], Path, Path]:
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        skill_file = root / "SKILL.md"
        skill_file.write_text(text, encoding="utf-8")
        return tmp, root, skill_file

    def test_root_routes_are_portable_and_resolvable(self) -> None:
        self.assertEqual(route_errors(ROOT / "SKILL.md", ROOT), [])

    def test_opaque_route_without_a_path_is_rejected(self) -> None:
        tmp, root, skill_file = self.fixture("Load [ref:guide].\n")
        with tmp:
            errors = route_errors(skill_file, root)
        self.assertTrue(any("opaque route" in error for error in errors), errors)

    def test_missing_target_is_rejected(self) -> None:
        tmp, root, skill_file = self.fixture("Load `references/guide.md`.\n")
        with tmp:
            errors = route_errors(skill_file, root)
        self.assertTrue(any("route target is not a file" in error for error in errors), errors)

    def test_path_traversal_is_rejected(self) -> None:
        tmp, root, skill_file = self.fixture("Load `references/../guide.md`.\n")
        with tmp:
            errors = route_errors(skill_file, root)
        self.assertTrue(any("must not traverse directories" in error for error in errors), errors)

    def test_wrong_route_type_is_rejected(self) -> None:
        tmp, root, skill_file = self.fixture("Load `skills/demo.md`.\n")
        with tmp:
            errors = route_errors(skill_file, root)
        self.assertTrue(any("skills/<skill-name>/SKILL.md" in error for error in errors), errors)

    def test_directory_target_is_rejected_as_wrong_type(self) -> None:
        tmp, root, skill_file = self.fixture("Load `skills/demo/SKILL.md`.\n")
        with tmp:
            (root / "skills/demo/SKILL.md").mkdir(parents=True)
            errors = route_errors(skill_file, root)
        self.assertTrue(any("route target is not a file" in error for error in errors), errors)

    def test_absolute_and_windows_paths_are_rejected(self) -> None:
        for target, expected in (
            ("/references/guide.md", "must be relative"),
            (r"references\guide.md", "must use forward slashes"),
        ):
            with self.subTest(target=target):
                tmp, root, skill_file = self.fixture(f"Load `{target}`.\n")
                with tmp:
                    errors = route_errors(skill_file, root)
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_canonical_skill_and_nested_reference_paths_pass(self) -> None:
        text = (
            "Load `skills/demo/SKILL.md` and `references/vocab/zh.md`.\n"
        )
        tmp, root, skill_file = self.fixture(text)
        with tmp:
            skill_target = root / "skills/demo/SKILL.md"
            ref_target = root / "references/vocab/zh.md"
            skill_target.parent.mkdir(parents=True)
            ref_target.parent.mkdir(parents=True)
            skill_target.write_text("demo\n", encoding="utf-8")
            ref_target.write_text("vocab\n", encoding="utf-8")
            self.assertEqual(route_errors(skill_file, root), [])


class PortableRoutePayloadTests(unittest.TestCase):
    def install(self, destination: Path) -> Path:
        argv = sys.argv
        sys.argv = ["install_codex_skill.py", "--dest", str(destination)]
        try:
            self.assertEqual(installer.main(), 0)
        finally:
            sys.argv = argv
        return destination / installer.SKILL_NAME

    def test_installed_payload_contains_every_root_route_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self.install(Path(tmp) / "skills")
            self.assertEqual(route_errors(payload / "SKILL.md", payload), [])

    def test_routes_survive_zip_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = self.install(root / "installed-skills")
            archive = root / "seedance-20.zip"
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
                for path in payload.rglob("*"):
                    if path.is_file():
                        bundle.write(path, Path(installer.SKILL_NAME) / path.relative_to(payload))
            extracted = root / "extracted"
            with zipfile.ZipFile(archive) as bundle:
                bundle.extractall(extracted)
            unpacked = extracted / installer.SKILL_NAME
            self.assertEqual(route_errors(unpacked / "SKILL.md", unpacked), [])


if __name__ == "__main__":
    unittest.main()
