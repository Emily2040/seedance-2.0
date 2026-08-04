"""Active runtime routes must be explicit, resolvable Markdown links."""

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


def route_errors(
    skill_file: Path,
    root: Path,
    *,
    require_routes: bool = True,
) -> list[str]:
    errors: list[str] = []
    validate_skills.validate_portable_routes(
        skill_file,
        root,
        errors,
        require_routes=require_routes,
    )
    return errors


def runtime_route_errors(root: Path) -> list[str]:
    errors: list[str] = []
    for path in validate_skills.active_runtime_markdown_paths(root):
        is_root_skill = path == root / "SKILL.md"
        validate_skills.validate_portable_routes(
            path,
            root,
            errors,
            require_routes=is_root_skill,
        )
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

    def test_every_active_shipped_markdown_file_is_alias_free_and_resolves(self) -> None:
        runtime_paths = validate_skills.active_runtime_markdown_paths(ROOT)
        relative = {path.relative_to(ROOT).as_posix() for path in runtime_paths}

        self.assertGreaterEqual(len(runtime_paths), 90)
        self.assertIn("SKILL.md", relative)
        self.assertIn("skills/seedance-prompt/SKILL.md", relative)
        self.assertIn("references/directing-engine.md", relative)
        self.assertFalse(any(path.startswith("references/migrated/") for path in relative))
        self.assertEqual(runtime_route_errors(ROOT), [])

        opaque = []
        for path in runtime_paths:
            text = path.read_text(encoding="utf-8")
            opaque.extend(validate_skills.OPAQUE_ROUTE_RE.findall(text))
        self.assertEqual(opaque, [])

    def test_archived_markdown_remains_outside_the_active_runtime_contract(self) -> None:
        archived = ROOT / "references/migrated/seedance-audio-original.md"
        self.assertTrue(archived.is_file())
        self.assertNotIn(archived, validate_skills.active_runtime_markdown_paths(ROOT))

    def test_nested_routes_keep_readable_labels(self) -> None:
        reference = (ROOT / "references/directing-engine.md").read_text(encoding="utf-8")
        skill = (ROOT / "skills/seedance-interview/SKILL.md").read_text(encoding="utf-8")

        self.assertIn(
            "[seedance-camera](../skills/seedance-camera/SKILL.md)",
            reference,
        )
        self.assertIn(
            "[pro-filmmaking-standards](../../references/pro-filmmaking-standards.md)",
            skill,
        )
        self.assertNotIn("[../skills/", reference)
        self.assertNotIn("[../../references/", skill)

    def test_static_validation_boundary_is_honest(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Every active runtime route in this package", text)
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

    def test_nested_runtime_unlinked_route_instruction_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "skills/source/SKILL.md"
            source.parent.mkdir(parents=True)
            source.write_text(
                "For full vocabulary, load `references/vocab/en.md`.\n",
                encoding="utf-8",
            )

            errors = route_errors(source, root, require_routes=False)
            self.assertTrue(
                any("is code text, not a Markdown link" in error for error in errors),
                errors,
            )

    def test_nested_record_writeback_route_instruction_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "references/sync-budget-protocol.md"
            source.parent.mkdir(parents=True)
            source.write_text(
                "3. Record the session in `references/source-registry.md` per its methodology.\n"
                "When complete, record the result in `references/source-registry.md`.\n",
                encoding="utf-8",
            )

            errors = route_errors(source, root, require_routes=False)
            self.assertEqual(
                sum("is code text, not a Markdown link" in error for error in errors),
                2,
                errors,
            )

    def test_record_writeback_auxiliaries_are_rejected(self) -> None:
        variants = (
            "You need to record the result in `references/source-registry.md`.",
            "You are required to record the result in `references/source-registry.md`.",
            "Be sure to record the result in `references/source-registry.md`.",
            "Remember to record the result in `references/source-registry.md`.",
        )
        for prose in variants:
            with self.subTest(prose=prose), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = root / "references/source.md"
                source.parent.mkdir(parents=True)
                source.write_text(prose + "\n", encoding="utf-8")

                errors = route_errors(source, root, require_routes=False)
                self.assertEqual(
                    sum("is code text, not a Markdown link" in error for error in errors),
                    1,
                    errors,
                )

    def test_mutation_routes_cover_headings_synonyms_and_indirect_destinations(self) -> None:
        directives = (
            "### Record the result in `references/source-registry.md`",
            "Record the result in the designated registry, specifically `references/source-registry.md`",
            "Write the result to `references/source-registry.md`",
            "Append the result to `references/source-registry.md`",
            "Save the result in `references/source-registry.md`",
            "Store the result inside `references/source-registry.md`",
            "Log the result at `references/source-registry.md`",
            "Update `references/source-registry.md` after every run",
            "Edit the registry at `references/source-registry.md`",
            "When complete, add the result to `references/source-registry.md`",
            "Record the result using `references/source-registry.md`",
            "Please **record** the result in `references/source-registry.md`",
            "You need to __append__ the result to `references/source-registry.md`",
            "When complete, **save** the result in `references/source-registry.md`",
        )
        for prose in directives:
            with self.subTest(prose=prose), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = root / "references/source.md"
                source.parent.mkdir(parents=True)
                source.write_text(prose + "\n", encoding="utf-8")

                errors = route_errors(source, root, require_routes=False)
                self.assertEqual(
                    sum("is code text, not a Markdown link" in error for error in errors),
                    1,
                    errors,
                )

    def test_mutation_nouns_and_prior_sentences_do_not_impersonate_directives(self) -> None:
        descriptions = (
            "Record `references/source-registry.md` appears in this grammar example.",
            "Record labels include `references/source-registry.md` in the fixture.",
            "Write format: `references/source-registry.md`.",
            "The package writes `references/source-registry.md` in its manifest.",
            "Record the result elsewhere. The example path is `references/source-registry.md`.",
            "Record the result in another document; this example names `references/source-registry.md`.",
        )
        for prose in descriptions:
            with self.subTest(prose=prose), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = root / "references/source.md"
                source.parent.mkdir(parents=True)
                source.write_text(prose + "\n", encoding="utf-8")
                self.assertEqual(route_errors(source, root, require_routes=False), [])

    def test_multiline_record_writeback_targets_are_rejected(self) -> None:
        variants = (
            "Record the result in:\n- `references/source-registry.md`\n",
            "Remember to record the result in:\n  `references/source-registry.md`\n",
            "You need to record the result:\n  1. `references/source-registry.md`\n",
        )
        for prose in variants:
            with self.subTest(prose=prose), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = root / "references/source.md"
                source.parent.mkdir(parents=True)
                source.write_text(prose, encoding="utf-8")

                errors = route_errors(source, root, require_routes=False)
                self.assertEqual(
                    sum("is code text, not a Markdown link" in error for error in errors),
                    1,
                    errors,
                )

    def test_record_directive_and_noun_mutations_stay_distinct(self) -> None:
        cases = (
            ("> Record the result in `references/source-registry.md`.", 1),
            ("Record type: `references/source-registry.md`.", 0),
            ("- [ ] Record the result in `references/source-registry.md`.", 1),
            ("- [ ] Record field: `references/source-registry.md`.", 0),
            ("Do not record the result in `references/source-registry.md`.", 1),
            ("The do-not-record rule names `references/source-registry.md`.", 0),
            ("Carefully record the result in `references/source-registry.md`.", 1),
            ("Careful record keeping uses `references/source-registry.md`.", 0),
            ("Record the result:\n- `references/source-registry.md`\n", 1),
            ("Record type:\n- `references/source-registry.md`\n", 0),
            ("Then record the count in `references/source-registry.md`.", 1),
            ("Then record count is stored in `references/source-registry.md`.", 0),
            ("**Record** the result in `references/source-registry.md`.", 1),
            ("__Record__ the result in `references/source-registry.md`.", 1),
            ("*Please record* the result in `references/source-registry.md`.", 1),
            ("**Record type:** `references/source-registry.md`.", 0),
            ("__Record__ `references/source-registry.md` is a noun example.", 0),
            ("Record:\n- `references/source-registry.md`\n", 1),
        )
        for prose, expected in cases:
            with self.subTest(prose=prose), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = root / "references/source.md"
                source.parent.mkdir(parents=True)
                source.write_text(prose + "\n", encoding="utf-8")

                errors = route_errors(source, root, require_routes=False)
                self.assertEqual(
                    sum("is code text, not a Markdown link" in error for error in errors),
                    expected,
                    errors,
                )

    def test_record_nouns_and_descriptions_are_not_route_directives(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "references/source.md"
            source.parent.mkdir(parents=True)
            source.write_text(
                "The session record is `references/source-registry.md`. "
                "The package records `references/source-registry.md` in its manifest. "
                "A generated record named `references/source-registry.md` is test data.\n"
                "Record `references/source-registry.md` is a noun phrase in this example.\n"
                "Record keeping uses `references/source-registry.md` as test data.\n",
                encoding="utf-8",
            )

            self.assertEqual(route_errors(source, root, require_routes=False), [])

    def test_descriptive_code_paths_do_not_become_route_false_positives(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "references/source.md"
            guide = root / "references/guide.md"
            source.parent.mkdir(parents=True)
            guide.write_text("# Guide\n", encoding="utf-8")
            source.write_text(
                "The package layout includes `references/guide.md`. "
                "The client loads `SKILL.md` on demand. "
                "The generated report is named `guide.md`.\n",
                encoding="utf-8",
            )

            self.assertEqual(route_errors(source, root, require_routes=False), [])

    def test_code_form_label_inside_markdown_link_is_not_rejected(self) -> None:
        temporary, root, skill_file = self.fixture(
            "See [`guide.md`](references/guide.md).\n"
        )
        with temporary:
            target = root / "references/guide.md"
            target.parent.mkdir(parents=True)
            target.write_text("# Guide\n", encoding="utf-8")
            self.assertEqual(route_errors(skill_file, root), [])

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

    def test_routes_resolve_relative_to_nested_runtime_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "skills/source/SKILL.md"
            peer = root / "skills/peer/SKILL.md"
            reference = root / "references/guide.md"
            source.parent.mkdir(parents=True)
            peer.parent.mkdir(parents=True)
            reference.parent.mkdir(parents=True)
            source.write_text(
                "Load [guide](../../references/guide.md) and "
                "[peer](../peer/SKILL.md).\n",
                encoding="utf-8",
            )
            peer.write_text("# Peer\n", encoding="utf-8")
            reference.write_text("# Guide\n", encoding="utf-8")

            self.assertEqual(
                route_errors(
                    source,
                    root,
                    require_routes=False,
                ),
                [],
            )

    def test_nested_runtime_alias_is_rejected_without_requiring_a_route_table(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "skills/source/SKILL.md"
            source.parent.mkdir(parents=True)
            source.write_text("Load `[ref:guide]`.\n", encoding="utf-8")

            errors = route_errors(
                source,
                root,
                require_routes=False,
            )
            self.assertTrue(any("opaque route" in error for error in errors), errors)

    def test_reference_routes_resolve_without_repeating_the_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "references/source.md"
            peer = root / "references/peer.md"
            source.parent.mkdir(parents=True)
            source.write_text("Load [peer](peer.md).\n", encoding="utf-8")
            peer.write_text("# Peer\n", encoding="utf-8")

            self.assertEqual(
                route_errors(
                    source,
                    root,
                    require_routes=False,
                ),
                [],
            )

    def test_nested_routes_reject_wrong_case_escape_and_redundant_traversal(self) -> None:
        cases = (
            ("../../References/guide.md", "exact lowercase `references/`"),
            ("../../../references/guide.md", "must not traverse outside"),
            ("../source/../../references/guide.md", "must not traverse redundantly"),
        )
        for target, expected in cases:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = root / "skills/source/SKILL.md"
                reference = root / "references/guide.md"
                source.parent.mkdir(parents=True)
                reference.parent.mkdir(parents=True)
                source.write_text(f"Load [guide]({target}).\n", encoding="utf-8")
                reference.write_text("# Guide\n", encoding="utf-8")

                errors = route_errors(
                    source,
                    root,
                    require_routes=False,
                )
                self.assertTrue(any(expected in error for error in errors), errors)

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
        self.assertEqual(runtime_route_errors(payload), [])
        for path in validate_skills.active_runtime_markdown_paths(payload):
            self.assertIsNone(
                validate_skills.OPAQUE_ROUTE_RE.search(path.read_text(encoding="utf-8")),
                path,
            )
        text = (payload / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("does **not** prove that a host auto-loads", text)

    def test_installed_payload_contains_every_runtime_route_target(self) -> None:
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
