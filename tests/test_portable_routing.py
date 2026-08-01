"""Portable root routes must be explicit, resolvable Markdown links."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

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
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        skill_file = root / "SKILL.md"
        skill_file.write_text(text, encoding="utf-8")
        return temporary, root, skill_file

    def assert_route_error(self, text: str, expected: str) -> None:
        temporary, root, skill_file = self.fixture(text)
        with temporary:
            errors = route_errors(skill_file, root)
        self.assertTrue(any(expected in error for error in errors), errors)

    def test_root_routes_are_markdown_links_and_resolve(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertEqual(route_errors(ROOT / "SKILL.md", ROOT), [])
        self.assertIsNone(validate_skills.OPAQUE_ROUTE_RE.search(text))
        self.assertIsNone(validate_skills.UNLINKED_ROUTE_RE.search(text))
        self.assertGreaterEqual(len(list(validate_skills.MARKDOWN_LINK_RE.finditer(text))), 100)

    def test_static_validation_boundary_is_honest(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("ordinary relative Markdown link", text)
        self.assertIn("does **not** prove that a host auto-loads or invokes the target", text)
        self.assertIn("clients must follow the link or provide their own native routing", text)

    def test_opaque_route_aliases_are_rejected_case_insensitively(self) -> None:
        for route in (
            "[ref:directors-read]",
            "[Skill:demo]",
            "[REF:guide with spaces]",
        ):
            with self.subTest(route=route):
                self.assert_route_error(f"Load {route}.\n", "opaque route")

    def test_code_literal_route_is_not_mistaken_for_a_link(self) -> None:
        self.assert_route_error(
            "Load `references/guide.md`.\n",
            "is code text, not a Markdown link",
        )

    def test_missing_target_is_rejected(self) -> None:
        self.assert_route_error(
            "Load [guide](references/guide.md).\n",
            "route target is not a file",
        )

    def test_dot_and_parent_traversal_are_rejected(self) -> None:
        for target in (
            "references/../guide.md",
            "references/./guide.md",
            "../references/guide.md",
            "folder/../references/guide.md",
            "references/%2e%2e/guide.md",
        ):
            with self.subTest(target=target):
                temporary, root, skill_file = self.fixture(f"Load [guide]({target}).\n")
                with temporary:
                    errors = route_errors(skill_file, root)
                self.assertTrue(
                    any(
                        phrase in error
                        for error in errors
                        for phrase in ("must not traverse", "percent encoding")
                    ),
                    errors,
                )

    def test_empty_path_segments_are_rejected(self) -> None:
        self.assert_route_error(
            "Load [guide](references//guide.md).\n",
            "must not contain empty segments",
        )

    def test_absolute_drive_and_backslash_paths_are_rejected(self) -> None:
        for target, expected in (
            ("/references/guide.md", "must be relative"),
            ("C:/references/guide.md", "must be relative"),
            (r"references\guide.md", "must use forward slashes"),
            (r"\\references\guide.md", "must use forward slashes"),
        ):
            with self.subTest(target=target):
                self.assert_route_error(f"Load [guide]({target}).\n", expected)

    def test_wrong_route_shapes_are_rejected(self) -> None:
        for target, expected in (
            ("skills/demo.md", "skills/<skill-name>/SKILL.md"),
            ("skills/demo/readme.md", "skills/<skill-name>/SKILL.md"),
            ("references/guide.txt", "references/<reference-name>.md"),
        ):
            with self.subTest(target=target):
                self.assert_route_error(f"Load [route]({target}).\n", expected)

    def test_directory_target_is_rejected_as_wrong_type(self) -> None:
        temporary, root, skill_file = self.fixture(
            "Load [demo](skills/demo/SKILL.md).\n"
        )
        with temporary:
            (root / "skills/demo/SKILL.md").mkdir(parents=True)
            errors = route_errors(skill_file, root)
        self.assertTrue(any("route target is not a file" in error for error in errors), errors)

    def test_route_prefix_and_filesystem_case_are_exact(self) -> None:
        temporary, root, skill_file = self.fixture(
            "Load [guide](References/guide.md).\n"
        )
        with temporary:
            target = root / "references/guide.md"
            target.parent.mkdir(parents=True)
            target.write_text("# Guide\n", encoding="utf-8")
            errors = route_errors(skill_file, root)
        self.assertTrue(any("exact lowercase `references/`" in error for error in errors), errors)

        temporary, root, skill_file = self.fixture(
            "Load [guide](references/guide.md).\n"
        )
        with temporary:
            target = root / "references/Guide.md"
            target.parent.mkdir(parents=True)
            target.write_text("# Guide\n", encoding="utf-8")
            errors = route_errors(skill_file, root)
        self.assertTrue(any("route path case mismatch" in error for error in errors), errors)

    def test_route_paths_with_raw_or_encoded_spaces_are_rejected(self) -> None:
        for target, expected in (
            ("<references/my guide.md>", "must not contain whitespace"),
            ("references/my%20guide.md", "percent encoding"),
        ):
            with self.subTest(target=target):
                self.assert_route_error(f"Load [guide]({target}).\n", expected)

    def test_query_and_empty_fragment_are_rejected(self) -> None:
        for target, expected in (
            ("references/guide.md?mode=raw", "must not contain a query"),
            ("references/guide.md#", "fragment must not be empty"),
        ):
            with self.subTest(target=target):
                self.assert_route_error(f"Load [guide]({target}).\n", expected)

    def test_fragment_must_be_canonical_and_resolve_to_a_heading(self) -> None:
        temporary, root, skill_file = self.fixture(
            "Load [details](references/guide.md#details-here).\n"
        )
        with temporary:
            target = root / "references/guide.md"
            target.parent.mkdir(parents=True)
            target.write_text("# Guide\n\n## Details Here\n", encoding="utf-8")
            self.assertEqual(route_errors(skill_file, root), [])

            skill_file.write_text(
                "Load [details](references/guide.md#Details-Here).\n",
                encoding="utf-8",
            )
            wrong_case = route_errors(skill_file, root)
            self.assertTrue(
                any("lowercase Markdown anchor" in error for error in wrong_case),
                wrong_case,
            )

            skill_file.write_text(
                "Load [details](references/guide.md#missing).\n",
                encoding="utf-8",
            )
            missing = route_errors(skill_file, root)
            self.assertTrue(any("fragment does not resolve" in error for error in missing), missing)

    def test_canonical_skill_and_nested_reference_links_pass(self) -> None:
        text = (
            "Load [demo](skills/demo/SKILL.md#intent) and "
            "[Chinese vocabulary](references/vocab/zh.md#dialogue).\n"
        )
        temporary, root, skill_file = self.fixture(text)
        with temporary:
            skill_target = root / "skills/demo/SKILL.md"
            reference_target = root / "references/vocab/zh.md"
            skill_target.parent.mkdir(parents=True)
            reference_target.parent.mkdir(parents=True)
            skill_target.write_text("# Demo\n\n## Intent\n", encoding="utf-8")
            reference_target.write_text("# Chinese\n\n## Dialogue\n", encoding="utf-8")
            self.assertEqual(route_errors(skill_file, root), [])

    def test_external_links_are_outside_the_static_route_contract(self) -> None:
        text = (
            "See [external docs](https://example.com/references/guide.md), then "
            "load [local guide](references/guide.md).\n"
        )
        temporary, root, skill_file = self.fixture(text)
        with temporary:
            target = root / "references/guide.md"
            target.parent.mkdir(parents=True)
            target.write_text("# Guide\n", encoding="utf-8")
            self.assertEqual(route_errors(skill_file, root), [])

    def test_resolved_target_cannot_escape_the_skill_root(self) -> None:
        temporary, root, skill_file = self.fixture(
            "Load [guide](references/guide.md).\n"
        )
        with temporary, tempfile.TemporaryDirectory() as outside_dir:
            outside = Path(outside_dir) / "guide.md"
            outside.write_text("# Outside\n", encoding="utf-8")
            with mock.patch.object(
                validate_skills,
                "_find_exact_case_path",
                return_value=(outside, None),
            ):
                errors = route_errors(skill_file, root)
        self.assertTrue(any("resolves outside the skill root" in error for error in errors), errors)


class PortableRoutePayloadTests(unittest.TestCase):
    def install(self, destination: Path) -> Path:
        original_argv = sys.argv
        sys.argv = ["install_codex_skill.py", "--dest", str(destination)]
        try:
            self.assertEqual(installer.main(), 0)
        finally:
            sys.argv = original_argv
        return destination / installer.SKILL_NAME

    def assert_payload_contract(self, payload: Path) -> None:
        self.assertEqual(route_errors(payload / "SKILL.md", payload), [])
        text = (payload / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("does **not** prove that a host auto-loads", text)

    def test_installed_payload_contains_every_root_route_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            payload = self.install(Path(temporary) / "client with spaces" / "skills")
            self.assert_payload_contract(payload)

    def test_routes_resolve_when_client_cwd_is_elsewhere(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as other:
            payload = self.install(Path(temporary) / "installed-skills")
            previous = Path.cwd()
            os.chdir(other)
            try:
                self.assert_payload_contract(payload)
            finally:
                os.chdir(previous)

    def test_routes_survive_zip_extraction_to_a_spaced_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload = self.install(root / "installed-skills")
            archive = root / "seedance-20.zip"
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
                for path in payload.rglob("*"):
                    if path.is_file():
                        bundle.write(
                            path,
                            Path(installer.SKILL_NAME) / path.relative_to(payload),
                        )
            extracted = root / "client extraction with spaces"
            with zipfile.ZipFile(archive) as bundle:
                bundle.extractall(extracted)
            self.assert_payload_contract(extracted / installer.SKILL_NAME)


if __name__ == "__main__":
    unittest.main()
