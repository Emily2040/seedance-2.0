"""Mutation coverage for the repository-wide strict JSON boundary."""
from __future__ import annotations

import ast
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from strict_json import (  # noqa: E402
    MAX_DIAGNOSTIC_CHARS,
    MAX_JSON_BYTES,
    MAX_JSON_DEPTH,
    MAX_JSONL_LINE_BYTES,
    MAX_JSONL_RECORDS,
    MAX_NUMBER_CHARS,
    StrictJSONError,
    diagnostic_path,
    load_json,
    load_jsonl,
    loads_json,
)
import strict_json as strict_json_module  # noqa: E402
import eval_run  # noqa: E402
import schema_check  # noqa: E402


class StrictLoaderTests(unittest.TestCase):
    def test_duplicate_keys_are_rejected_at_any_depth(self) -> None:
        with self.assertRaisesRegex(
            StrictJSONError,
            r"duplicate object key: 'x'.*line 1 column",
        ):
            loads_json('{"outer": {"x": 1, "x": 2}}', expected_type=dict)

    def test_every_non_finite_number_spelling_is_rejected(self) -> None:
        for token in ("NaN", "Infinity", "-Infinity", "1e400"):
            with self.subTest(token=token):
                with self.assertRaisesRegex(StrictJSONError, "non-finite number"):
                    loads_json(f'{{"value": {token}}}', expected_type=dict)

    def test_unpaired_surrogates_are_rejected_but_valid_pairs_survive(self) -> None:
        with self.assertRaisesRegex(StrictJSONError, "unpaired Unicode surrogate"):
            loads_json('{"value": "\\ud800"}', expected_type=dict)
        self.assertEqual(
            loads_json('{"value": "\\ud83d\\ude00"}', expected_type=dict)["value"],
            "😀",
        )

    def test_wrong_top_level_shape_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            StrictJSONError,
            "top-level JSON value must be object, got array",
        ):
            loads_json("[]", expected_type=dict)

    def test_malformed_utf8_reports_line_and_column(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.json"
            path.write_bytes(b'{\n  "value": "\xff"\n}')
            with self.assertRaisesRegex(
                StrictJSONError,
                r"malformed UTF-8.*line 2 column 13",
            ):
                load_json(path, expected_type=dict)

    def test_expected_types_are_exact_and_unions_are_explicit(self) -> None:
        for expected in (int, (int, float), int | float):
            with self.subTest(expected=expected):
                with self.assertRaisesRegex(StrictJSONError, "got boolean"):
                    loads_json("true", expected_type=expected)
        self.assertEqual(loads_json("1", expected_type=(int, float)), 1)
        self.assertEqual(loads_json("1.5", expected_type=int | float), 1.5)

    def test_resource_failures_are_bounded_and_located(self) -> None:
        cases = (
            (
                "[" * (MAX_JSON_DEPTH + 1) + "0" + "]" * (MAX_JSON_DEPTH + 1),
                "maximum JSON nesting depth",
            ),
            ("1" * (MAX_NUMBER_CHARS + 1), "JSON number exceeds"),
            (" " * (MAX_JSON_BYTES + 1), "JSON input exceeds"),
        )
        for text, fragment in cases:
            with self.subTest(fragment=fragment):
                with self.assertRaises(StrictJSONError) as caught:
                    loads_json(text)
                message = str(caught.exception)
                self.assertIn(fragment, message)
                self.assertRegex(message, r"line \d+(?: column \d+)?")
                self.assertLessEqual(
                    len(caught.exception.message), MAX_DIAGNOSTIC_CHARS
                )

    def test_diagnostics_are_single_line_ascii_and_bounded(self) -> None:
        key = "bad\n\r\t\x85\u2028\u2029\U0001f600"
        rendered_key = json.dumps(key, ensure_ascii=False)
        with self.assertRaises(StrictJSONError) as caught:
            loads_json(
                "{" + rendered_key + ": 1, " + rendered_key + ": 2}",
                expected_type=dict,
            )
        message = str(caught.exception)
        self.assertNotIn("\n", message)
        self.assertNotIn("\r", message)
        self.assertTrue(all(0x20 <= ord(char) <= 0x7E for char in message))
        message.encode("cp1252", errors="strict")

        huge_key = "x" * 10_000
        encoded = json.dumps(huge_key)
        with self.assertRaises(StrictJSONError) as huge:
            loads_json("{" + encoded + ": 1, " + encoded + ": 2}")
        self.assertLessEqual(len(huge.exception.message), MAX_DIAGNOSTIC_CHARS)

        path_text = diagnostic_path(
            Path("bad\n\r\x85\u2028\u2029\U0001f600.json")
        )
        self.assertNotIn("\n", path_text)
        self.assertNotIn("\r", path_text)
        self.assertTrue(all(0x20 <= ord(char) <= 0x7E for char in path_text))
        path_text.encode("cp1252", errors="strict")

    def test_surrogate_json_path_is_diagnostic_safe(self) -> None:
        key = "bad\n\u2028\x85\U0001f600"
        encoded = json.dumps(key, ensure_ascii=False)
        with self.assertRaises(StrictJSONError) as caught:
            loads_json("{" + encoded + ': "\\ud800"}')
        message = str(caught.exception)
        self.assertIn("unpaired Unicode surrogate", message)
        self.assertNotIn("\n", message)
        self.assertTrue(all(0x20 <= ord(char) <= 0x7E for char in message))
        message.encode("cp1252", errors="strict")

    def test_jsonl_accepts_only_lf_or_crlf_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "records.jsonl"
            for ending in ("\n", "\r\n"):
                with self.subTest(ending=repr(ending)):
                    path.write_bytes(
                        (f'{{"line":1}}{ending}{{"line":2}}{ending}').encode(
                            "utf-8"
                        )
                    )
                    self.assertEqual(
                        [line for line, _ in load_jsonl(path, expected_type=dict)],
                        [1, 2],
                    )

            for separator in (
                "\r",
                "\x85",
                "\x0b",
                "\x0c",
                "\u2028",
                "\u2029",
            ):
                with self.subTest(separator=repr(separator)):
                    path.write_text(
                        '{"line":1}' + separator + '{"line":2}',
                        encoding="utf-8",
                        newline="",
                    )
                    with self.assertRaises(StrictJSONError):
                        load_jsonl(path, expected_type=dict)

    def test_jsonl_rejects_blank_physical_lines_and_keeps_lf_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "records.jsonl"
            for blank in ("", " ", "\t", " \t "):
                with self.subTest(blank=repr(blank)):
                    path.write_text(
                        '{"line":1}\n' + blank + '\n{"line":3}\n',
                        encoding="utf-8",
                        newline="",
                    )
                    with self.assertRaisesRegex(
                        StrictJSONError,
                        r"blank physical lines.*line 2 column 1",
                    ):
                        load_jsonl(path, expected_type=dict)

            path.write_text(
                '{"line":1}\n{"broken": }\n',
                encoding="utf-8",
                newline="",
            )
            with self.assertRaisesRegex(StrictJSONError, r"line 2 column"):
                load_jsonl(path, expected_type=dict)

    def test_jsonl_preserves_legal_raw_and_escaped_line_separators_in_strings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "records.jsonl"
            path.write_text(
                '{"value":"raw\u2028separator"}\n'
                '{"value":"escaped\\u2028separator"}\n',
                encoding="utf-8",
                newline="",
            )
            records = load_jsonl(path, expected_type=dict)
            self.assertEqual(records[0][1]["value"], "raw\u2028separator")
            self.assertEqual(records[1][1]["value"], "escaped\u2028separator")

    def test_jsonl_resource_limits_are_strict_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "records.jsonl"
            path.write_text(
                '{"value":"' + "x" * MAX_JSONL_LINE_BYTES + '"}',
                encoding="utf-8",
                newline="",
            )
            with self.assertRaisesRegex(
                StrictJSONError,
                r"JSONL record exceeds.*line 1 column 1",
            ):
                load_jsonl(path, expected_type=dict)

            path.write_text(
                "\n".join("{}" for _ in range(MAX_JSONL_RECORDS + 1)),
                encoding="utf-8",
                newline="",
            )
            with self.assertRaisesRegex(
                StrictJSONError,
                rf"exceeds {MAX_JSONL_RECORDS} records.*line {MAX_JSONL_RECORDS + 1}",
            ):
                load_jsonl(path, expected_type=dict)

    def test_repository_root_escape_is_rejected_with_safe_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "repo"
            root.mkdir()
            outside = base / "outside\n\u2028\U0001f600.json"
            with self.assertRaises(StrictJSONError) as caught:
                load_json(outside, expected_type=dict, root=root)
            message = str(caught.exception)
            self.assertIn("escapes root", message)
            self.assertNotIn("\n", message)
            message.encode("cp1252", errors="strict")

    @unittest.skipIf(os.name == "nt", "POSIX symbolic-link semantics")
    def test_posix_file_and_directory_symlinks_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "repo"
            outside = base / "outside"
            root.mkdir()
            outside.mkdir()
            payload = outside / "payload.json"
            payload.write_text("{}", encoding="utf-8")
            try:
                (root / "file.json").symlink_to(payload)
                (root / "linked-dir").symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"symbolic links unavailable: {exc}")
            for linked in (
                root / "file.json",
                root / "linked-dir" / "payload.json",
            ):
                with self.subTest(linked=linked):
                    with self.assertRaisesRegex(
                        StrictJSONError,
                        "symbolic link, junction, or reparse point",
                    ):
                        load_json(linked, expected_type=dict, root=root)

    @unittest.skipIf(os.name == "nt" or not hasattr(os, "mkfifo"), "POSIX FIFO semantics")
    def test_posix_fifo_is_rejected_without_waiting_for_a_writer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            fifo = root / "payload.json"
            os.mkfifo(fifo)
            probe = "\n".join(
                [
                    "import sys",
                    f"sys.path.insert(0, {str(ROOT / 'scripts')!r})",
                    "from pathlib import Path",
                    "from strict_json import StrictJSONError, load_json",
                    "try:",
                    f"    load_json(Path({str(fifo)!r}), expected_type=dict, root=Path({str(root)!r}))",
                    "except StrictJSONError as exc:",
                    "    print(exc)",
                    "    raise SystemExit(0)",
                    "raise SystemExit(3)",
                ]
            )
            try:
                result = subprocess.run(
                    [sys.executable, "-B", "-c", probe],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
            except subprocess.TimeoutExpired:
                self.fail("FIFO read blocked waiting for a writer")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("not a regular file", result.stdout)

    def test_device_nodes_are_rejected_before_open(self) -> None:
        for kind in (stat.S_IFCHR, stat.S_IFBLK):
            with self.subTest(kind=kind):
                metadata = mock.Mock(
                    st_mode=kind | 0o600,
                    st_size=0,
                    st_file_attributes=0,
                )
                with (
                    mock.patch.object(
                        strict_json_module.os,
                        "stat",
                        return_value=metadata,
                    ),
                    mock.patch.object(strict_json_module.os, "open") as open_mock,
                ):
                    with self.assertRaisesRegex(
                        StrictJSONError,
                        "not a regular file",
                    ):
                        strict_json_module._read_bounded(
                            Path("device-node"),
                            "JSON input",
                        )
                open_mock.assert_not_called()

    @unittest.skipUnless(os.name == "nt", "Windows junction semantics")
    def test_windows_directory_junction_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "repo"
            outside = base / "outside"
            junction = root / "linked-dir"
            root.mkdir()
            outside.mkdir()
            (outside / "payload.json").write_text("{}", encoding="utf-8")
            created = subprocess.run(
                [
                    "cmd.exe",
                    "/d",
                    "/c",
                    "mklink",
                    "/J",
                    str(junction),
                    str(outside),
                ],
                capture_output=True,
                text=True,
            )
            if created.returncode != 0:
                self.skipTest(f"junction creation unavailable: {created.stderr}")
            try:
                with self.assertRaisesRegex(
                    StrictJSONError,
                    "symbolic link, junction, or reparse point",
                ):
                    load_json(
                        junction / "payload.json",
                        expected_type=dict,
                        root=root,
                    )
            finally:
                if os.path.lexists(junction):
                    os.rmdir(junction)

    @unittest.skipUnless(os.name == "nt", "Windows junction semantics")
    def test_junction_swap_between_validation_and_open_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "repo"
            inside = root / "slot"
            outside = base / "outside"
            saved = root / "saved-slot"
            inside.mkdir(parents=True)
            outside.mkdir()
            target = inside / "payload.json"
            target.write_text('{"origin":"inside"}', encoding="utf-8")
            (outside / "payload.json").write_text(
                '{"origin":"outside"}', encoding="utf-8"
            )

            original = strict_json_module.validate_repo_input_path
            switched = False

            def swap_after_validation(repo_root: Path, path: Path) -> Path:
                nonlocal switched
                checked = original(repo_root, path)
                if not switched:
                    inside.rename(saved)
                    created = subprocess.run(
                        [
                            "cmd.exe",
                            "/d",
                            "/c",
                            "mklink",
                            "/J",
                            str(inside),
                            str(outside),
                        ],
                        capture_output=True,
                        text=True,
                    )
                    if created.returncode != 0:
                        saved.rename(inside)
                        self.skipTest(
                            f"junction creation unavailable: {created.stderr}"
                        )
                    switched = True
                return checked

            try:
                with mock.patch.object(
                    strict_json_module,
                    "validate_repo_input_path",
                    new=swap_after_validation,
                ):
                    with self.assertRaisesRegex(
                        StrictJSONError,
                        "symbolic link, junction, or reparse point",
                    ):
                        load_json(target, expected_type=dict, root=root)
                self.assertTrue(switched)
            finally:
                if os.path.lexists(inside):
                    os.rmdir(inside)
                if saved.exists():
                    saved.rename(inside)

    def test_file_mutation_during_single_handle_read_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            target = root / "payload.json"
            target.write_text('{"origin":"before"}', encoding="utf-8")
            original_read = strict_json_module.os.read
            changed = False

            def mutate_after_first_read(descriptor: int, size: int) -> bytes:
                nonlocal changed
                chunk = original_read(descriptor, size)
                if chunk and not changed:
                    target.write_text(
                        '{"origin":"after","padding":"changed"}',
                        encoding="utf-8",
                    )
                    changed = True
                return chunk

            with mock.patch.object(
                strict_json_module.os,
                "read",
                new=mutate_after_first_read,
            ):
                with self.assertRaisesRegex(
                    StrictJSONError,
                    "changed while being read",
                ):
                    load_json(target, expected_type=dict, root=root)
            self.assertTrue(changed)


class MigratedReaderBoundaryTests(unittest.TestCase):
    MODULES = (
        "behavior_contract_check.py",
        "build_hero.py",
        "continuity_chain_check.py",
        "eval_run.py",
        "eval_schema_check.py",
        "generation_run_check.py",
        "project_state_check.py",
        "prompt_architecture_stress.py",
        "schema_check.py",
        "sequence_eval_check.py",
        "source_registry_check.py",
        "validate_skills.py",
    )
    PATH_READER_NAMES = {
        "load",
        "load_json",
        "load_jsonl",
        "strict_load_json",
        "read_repo_text",
    }

    def test_every_path_reader_call_passes_an_explicit_repository_root(self) -> None:
        unchecked: list[str] = []
        calls = 0
        for module in self.MODULES:
            source = (ROOT / "scripts" / module).read_text(encoding="utf-8")
            tree = ast.parse(source, filename=module)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                    continue
                if node.func.id not in self.PATH_READER_NAMES:
                    continue
                calls += 1
                roots = [keyword.value for keyword in node.keywords if keyword.arg == "root"]
                if node.func.id == "read_repo_text" and node.args:
                    roots.append(node.args[0])
                elif (
                    module == "project_state_check.py"
                    and node.func.id == "load_json"
                    and len(node.args) >= 2
                ):
                    roots.append(node.args[1])
                if not roots or any(
                    isinstance(value, ast.Constant) and value.value is None
                    for value in roots
                ):
                    unchecked.append(f"{module}:{node.lineno}:{node.func.id}")
        self.assertGreaterEqual(calls, 25)
        self.assertEqual(unchecked, [], "path readers without explicit root containment")

    def test_dynamic_error_prints_cross_the_final_diagnostic_gate(self) -> None:
        unsafe: list[str] = []
        dynamic_calls = 0
        tainted_names = {"error", "warning", "exc", "finding"}
        for module in self.MODULES:
            source = (ROOT / "scripts" / module).read_text(encoding="utf-8")
            tree = ast.parse(source, filename=module)
            for node in ast.walk(tree):
                if not (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "print"
                ):
                    continue
                for argument in node.args:
                    referenced = {
                        child.id
                        for child in ast.walk(argument)
                        if isinstance(child, ast.Name)
                    }
                    if not referenced & tainted_names:
                        continue
                    dynamic_calls += 1
                    has_gate = any(
                        isinstance(child, ast.Call)
                        and isinstance(child.func, ast.Name)
                        and child.func.id
                        in {"diagnostic_text", "_safe_exception_detail"}
                        for child in ast.walk(argument)
                    )
                    if not has_gate:
                        unsafe.append(f"{module}:{node.lineno}")
        self.assertGreaterEqual(dynamic_calls, 8)
        self.assertEqual(unsafe, [], "dynamic CLI output bypasses diagnostic_text")

    def _copy_repo(self, base: Path) -> Path:
        repo = base / "repo"
        shutil.copytree(
            ROOT,
            repo,
            ignore=shutil.ignore_patterns(
                ".git",
                "work",
                "__pycache__",
                "*.pyc",
            ),
        )
        return repo

    def _replace_directory_with_link(
        self,
        repo: Path,
        base: Path,
        relative: str,
    ) -> Path:
        linked = repo / relative
        outside = base / f"external-{relative}"
        linked.rename(outside)
        if os.name == "nt":
            created = subprocess.run(
                [
                    "cmd.exe",
                    "/d",
                    "/c",
                    "mklink",
                    "/J",
                    str(linked),
                    str(outside),
                ],
                capture_output=True,
                text=True,
            )
            if created.returncode != 0:
                outside.rename(linked)
                self.skipTest(f"junction creation unavailable: {created.stderr}")
        else:
            try:
                linked.symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                outside.rename(linked)
                self.skipTest(f"symbolic links unavailable: {exc}")
        return linked

    def _remove_directory_link(self, linked: Path) -> None:
        if not os.path.lexists(linked):
            return
        if os.name == "nt":
            os.rmdir(linked)
        else:
            linked.unlink()

    def _run_repo_script(
        self,
        repo: Path,
        script: str,
        *arguments: str,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(repo / "scripts" / script), *arguments],
            cwd=repo,
            capture_output=True,
            text=True,
        )

    def test_linked_repository_directories_are_rejected_by_each_reader_class(self) -> None:
        groups = {
            "evals": (
                (
                    "prompt_architecture_stress.py",
                    lambda repo: (
                        str(repo / "evals" / "prompt-architecture-stress.json"),
                        "--strict",
                    ),
                ),
                ("eval_schema_check.py", lambda repo: (str(repo),)),
                (
                    "eval_run.py",
                    lambda repo: (str(repo), "--self-test"),
                ),
                ("generation_run_check.py", lambda repo: (str(repo),)),
                ("sequence_eval_check.py", lambda repo: (str(repo),)),
                ("validate_skills.py", lambda repo: (str(repo),)),
            ),
            "data": (
                ("source_registry_check.py", lambda repo: (str(repo),)),
                ("generation_run_check.py", lambda repo: (str(repo),)),
                ("validate_skills.py", lambda repo: (str(repo),)),
            ),
            "examples": (
                ("project_state_check.py", lambda repo: (str(repo), "--strict")),
                ("continuity_chain_check.py", lambda repo: (str(repo), "--strict")),
                ("validate_skills.py", lambda repo: (str(repo),)),
            ),
            "schemas": (
                ("project_state_check.py", lambda repo: (str(repo), "--strict")),
                ("validate_skills.py", lambda repo: (str(repo),)),
            ),
            "validation": (
                ("behavior_contract_check.py", lambda repo: (str(repo),)),
            ),
            "assets": (
                ("build_hero.py", lambda _repo: ("--check",)),
                ("validate_skills.py", lambda repo: (str(repo),)),
            ),
            "skills": (
                (
                    "eval_run.py",
                    lambda repo: (str(repo), "--self-test"),
                ),
                ("validate_skills.py", lambda repo: (str(repo),)),
            ),
            "references": (
                (
                    "source_registry_check.py",
                    lambda repo: (str(repo),),
                ),
                (
                    "eval_run.py",
                    lambda repo: (str(repo), "--self-test"),
                ),
                ("validate_skills.py", lambda repo: (str(repo),)),
            ),
        }
        marker = "symbolic link, junction, or reparse point"
        for relative, scripts in groups.items():
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp)
                repo = self._copy_repo(base)
                linked = self._replace_directory_with_link(repo, base, relative)
                try:
                    for script, arguments in scripts:
                        with self.subTest(relative=relative, script=script):
                            result = self._run_repo_script(
                                repo,
                                script,
                                *arguments(repo),
                            )
                            output = result.stdout + result.stderr
                            self.assertNotEqual(result.returncode, 0, output)
                            self.assertIn(marker, output)
                    if relative in {"schemas", "validation"}:
                        errors = schema_check.check(repo)
                        self.assertTrue(any(marker in error for error in errors), errors)
                finally:
                    self._remove_directory_link(linked)


class PackageImportTests(unittest.TestCase):
    MODULES = (
        "build_hero",
        "continuity_chain_check",
        "eval_run",
        "eval_schema_check",
        "generation_run_check",
        "project_state_check",
        "prompt_architecture_stress",
        "schema_check",
        "sequence_eval_check",
        "source_registry_check",
        "validate_skills",
    )

    def _assert_package_imports(self, import_root: Path, cwd: Path) -> None:
        code = (
            "import importlib, sys\n"
            f"sys.path.insert(0, {str(import_root)!r})\n"
            f"modules = {self.MODULES!r}\n"
            "for name in modules:\n"
            "    importlib.import_module('scripts.' + name)\n"
            "print(len(modules))\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), str(len(self.MODULES)))

    def test_extracted_package_imports_from_unrelated_working_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._assert_package_imports(ROOT, Path(tmp))

    def test_zip_package_imports_without_local_fallback_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            archive = temp_root / "validators.zip"
            with zipfile.ZipFile(
                archive,
                "w",
                compression=zipfile.ZIP_DEFLATED,
            ) as bundle:
                for path in sorted((ROOT / "scripts").glob("*.py")):
                    bundle.write(path, Path("scripts") / path.name)
            self._assert_package_imports(archive, temp_root)

    def test_package_import_does_not_clobber_unrelated_top_level_module(self) -> None:
        code = (
            "import sys, types\n"
            f"sys.path.insert(0, {str(ROOT)!r})\n"
            "sentinel = types.ModuleType('strict_json')\n"
            "sentinel.marker = object()\n"
            "sys.modules['strict_json'] = sentinel\n"
            "import scripts\n"
            "import scripts.eval_run\n"
            "print(sys.modules['strict_json'] is sentinel)\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=tmp,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "True")

    def test_top_level_and_package_imports_share_exception_identity(self) -> None:
        scripts_root = ROOT / "scripts"
        programs = (
            (
                f"sys.path.insert(0, {str(scripts_root)!r})\n"
                "import strict_json as top\n"
                f"sys.path.insert(0, {str(ROOT)!r})\n"
                "import scripts.strict_json as package\n"
            ),
            (
                f"sys.path.insert(0, {str(ROOT)!r})\n"
                "import scripts.strict_json as package\n"
                f"sys.path.insert(0, {str(scripts_root)!r})\n"
                "import strict_json as top\n"
            ),
        )
        for setup in programs:
            with self.subTest(order=setup.splitlines()[1]), tempfile.TemporaryDirectory() as tmp:
                code = (
                    "import sys\n"
                    + setup
                    + "print(top is package, "
                    "top.StrictJSONError is package.StrictJSONError)\n"
                )
                result = subprocess.run(
                    [sys.executable, "-c", code],
                    cwd=tmp,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(
                    result.returncode, 0, result.stdout + result.stderr
                )
                self.assertEqual(result.stdout.strip(), "True True")


class NetworkBoundaryTests(unittest.TestCase):
    def test_api_response_read_is_bounded_before_allocation(self) -> None:
        class FakeResponse:
            def __init__(self) -> None:
                self.read_sizes: list[int] = []

            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *_args: object) -> bool:
                return False

            def read(self, size: int) -> bytes:
                self.read_sizes.append(size)
                return json.dumps(
                    {
                        "id": "msg_test",
                        "type": "message",
                        "role": "assistant",
                        "model": "model",
                        "content": [{"type": "text", "text": "ok"}],
                        "stop_reason": "end_turn",
                        "stop_sequence": None,
                        "usage": {"input_tokens": 1, "output_tokens": 0},
                    }
                ).encode("utf-8")

        response = FakeResponse()
        with mock.patch.object(
            eval_run.urllib.request,
            "urlopen",
            return_value=response,
        ):
            self.assertEqual(
                eval_run.call_api(
                    "system",
                    "user",
                    "model",
                    "key",
                    eval_run.PROVIDER_CONFIGS["anthropic"],
                    eval_run.ANTHROPIC_API_URL,
                ),
                "ok",
            )
        self.assertLess(eval_run.MAX_PROVIDER_RESPONSE_BYTES, MAX_JSON_BYTES)
        self.assertEqual(
            response.read_sizes,
            [eval_run.MAX_PROVIDER_RESPONSE_BYTES + 1],
        )


class ValidatorMutationTests(unittest.TestCase):
    MUTATED_FILES = (
        "assets/masthead-outlines.json",
        "data/sources.seedance-2026-05-30.json",
        "data/generation-runs.example.jsonl",
        "data/community-patterns.seedance-2026-05-30.json",
        "evals/generation-benchmark.json",
        "evals/prompt-architecture-stress.json",
        "evals/evals.json",
        "examples/sequence-airport-arrival/project-state.json",
        "examples/standalone-clip/project-state.json",
        "validation/fixtures/directors-read-cases.json",
    )

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.repo = Path(cls._tmp.name) / "archive"
        shutil.copytree(
            ROOT,
            cls.repo,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def setUp(self) -> None:
        for relative in self.MUTATED_FILES:
            source = ROOT / relative
            target = self.repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    def run_script(self, script: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.repo / "scripts" / script), *args],
            cwd=self.repo,
            capture_output=True,
            text=True,
        )

    def run_script_cp1252(
        self,
        script: str,
        *args: str,
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "cp1252:strict"
        environment["PYTHONUTF8"] = "0"
        return subprocess.run(
            [sys.executable, str(self.repo / "scripts" / script), *args],
            cwd=self.repo,
            capture_output=True,
            text=True,
            encoding="cp1252",
            errors="strict",
            env=environment,
        )

    def assert_cp1252_safe(
        self,
        result: subprocess.CompletedProcess[str],
        escaped_marker: str,
    ) -> str:
        output = result.stdout + result.stderr
        self.assertNotIn("UnicodeEncodeError", output)
        self.assertNotIn("\x1b", output)
        self.assertNotIn("\u2028", output)
        self.assertNotIn("\U0001f600", output)
        output.encode("ascii", errors="strict")
        self.assertIn(escaped_marker, output)
        self.assertTrue(all(len(line) <= MAX_DIAGNOSTIC_CHARS for line in output.splitlines()))
        return output

    def assert_rejected(
        self,
        result: subprocess.CompletedProcess[str],
        *fragments: str,
    ) -> None:
        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, output)
        for fragment in fragments:
            self.assertIn(fragment, output)

    def test_source_registry_rejects_duplicate_keys(self) -> None:
        target = self.repo / "data" / "sources.seedance-2026-05-30.json"
        target.write_text('{"sources": [], "sources": []}', encoding="utf-8")
        result = self.run_script("source_registry_check.py", str(self.repo))
        self.assert_rejected(
            result,
            "source data JSON parse error",
            "duplicate object key",
            "line 1",
        )

    def test_behavior_contract_cases_reject_duplicate_keys(self) -> None:
        target = self.repo / "validation" / "fixtures" / "directors-read-cases.json"
        target.write_text(
            '[{"id":"duplicate","id":"duplicate","expected_lane":"direct"}]',
            encoding="utf-8",
        )
        result = self.run_script("behavior_contract_check.py", str(self.repo))
        self.assert_rejected(
            result,
            "directors-read-cases.json: invalid JSON",
            "duplicate object key",
            "line 1",
        )

    def test_generation_run_jsonl_rejects_duplicate_keys_with_line(self) -> None:
        target = self.repo / "data" / "generation-runs.example.jsonl"
        first = target.read_text(encoding="utf-8").splitlines()[0]
        target.write_text(
            first + '\n{"run_id": "one", "run_id": "two"}\n',
            encoding="utf-8",
        )
        result = self.run_script("generation_run_check.py", str(self.repo))
        self.assert_rejected(
            result,
            "generation-runs.example.jsonl:2",
            "duplicate object key",
        )

    def test_generation_benchmark_rejects_non_finite_numbers(self) -> None:
        target = self.repo / "evals" / "generation-benchmark.json"
        target.write_text(
            '{"benchmark_version":"x","updated":"x","cases":[NaN,{},{}]}',
            encoding="utf-8",
        )
        result = self.run_script("generation_run_check.py", str(self.repo))
        self.assert_rejected(
            result,
            "evals/generation-benchmark.json invalid JSON",
            "non-finite number",
            "line 1",
        )

    def test_prompt_corpus_rejects_unpaired_surrogates(self) -> None:
        target = self.repo / "evals" / "prompt-architecture-stress.json"
        target.write_text('[{"prompt":"\\ud800"}]', encoding="utf-8")
        result = self.run_script("prompt_architecture_stress.py", str(target), "--strict")
        self.assert_rejected(
            result,
            "unpaired Unicode surrogate",
            "line 1",
        )

    def test_project_state_rejects_malformed_utf8_with_location(self) -> None:
        target = self.repo / "examples" / "standalone-clip" / "project-state.json"
        target.write_bytes(b'{\n  "project_id": "\xff"\n}')
        result = self.run_script("project_state_check.py", str(self.repo), "--strict")
        self.assert_rejected(
            result,
            "examples/standalone-clip/project-state.json",
            "malformed UTF-8",
            "line 2",
        )

    def test_evals_reject_wrong_top_level_shape(self) -> None:
        target = self.repo / "evals" / "evals.json"
        target.write_text("[]", encoding="utf-8")
        result = self.run_script("eval_schema_check.py", str(self.repo))
        self.assert_rejected(
            result,
            "Invalid JSON",
            "top-level JSON value must be object, got array",
            "line 1",
        )

    def test_validate_skills_parses_required_community_patterns(self) -> None:
        target = self.repo / "data" / "community-patterns.seedance-2026-05-30.json"
        target.write_text('{"patterns": [}', encoding="utf-8")
        result = self.run_script("validate_skills.py", str(self.repo))
        self.assert_rejected(
            result,
            "data/community-patterns.seedance-2026-05-30.json parse error",
            "line 1",
            "column",
        )

    def test_schema_reader_rejects_non_finite_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "schema.json"
            path.write_text('{"maximum": Infinity}', encoding="utf-8")
            with self.assertRaisesRegex(StrictJSONError, "non-finite number"):
                schema_check.load_json(path, root=Path(tmp))

    def test_cp1252_eval_case_id_is_escaped_at_both_cli_boundaries(self) -> None:
        malicious = "bad\n\x1b[31m\u2028\U0001f600"
        escaped = r"bad\n\u001b[31m\u2028\U0001f600"
        target = self.repo / "evals" / "evals.json"
        data = json.loads(target.read_text(encoding="utf-8"))
        data["cases"][0]["id"] = malicious
        data["cases"][0]["assertions"] = []
        target.write_text(
            json.dumps(data, ensure_ascii=False),
            encoding="utf-8",
        )

        schema_result = self.run_script_cp1252(
            "eval_schema_check.py",
            str(self.repo),
        )
        self.assertNotEqual(schema_result.returncode, 0)
        self.assert_cp1252_safe(schema_result, escaped)

        harness_result = self.run_script_cp1252(
            "eval_run.py",
            str(self.repo),
            "--self-test",
        )
        self.assertNotEqual(harness_result.returncode, 0)
        self.assert_cp1252_safe(
            harness_result,
            "source digest does not match manifest: evals/evals.json",
        )

    def test_cp1252_project_mode_is_escaped_at_cli_boundary(self) -> None:
        malicious = "bad\n\x1b[31m\u2028\U0001f600"
        escaped = r"bad\n\u001b[31m\u2028\U0001f600"
        target = self.repo / "examples" / "standalone-clip" / "project-state.json"
        data = json.loads(target.read_text(encoding="utf-8"))
        data["project_mode"] = malicious
        target.write_text(
            json.dumps(data, ensure_ascii=False),
            encoding="utf-8",
        )
        result = self.run_script_cp1252(
            "project_state_check.py",
            str(self.repo),
            "--strict",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assert_cp1252_safe(result, escaped)

    def test_cp1252_representative_reader_outputs_are_escaped(self) -> None:
        malicious = "bad\n\x1b[31m\u2028\U0001f600"
        escaped = r"bad\n\u001b[31m\u2028\U0001f600"

        continuity_target = (
            self.repo / "examples" / "sequence-airport-arrival" / "project-state.json"
        )
        continuity_data = json.loads(continuity_target.read_text(encoding="utf-8"))
        continuity_data["clips"][1]["clip_id"] = malicious
        continuity_data["clips"][1]["parent_clip_id"] = "missing-parent"
        continuity_target.write_text(
            json.dumps(continuity_data, ensure_ascii=False),
            encoding="utf-8",
        )
        continuity_result = self.run_script_cp1252(
            "continuity_chain_check.py",
            str(self.repo),
            "--strict",
        )
        self.assertNotEqual(continuity_result.returncode, 0)
        self.assert_cp1252_safe(
            continuity_result,
            r"bad\n\x1b[31m\u2028\U0001f600",
        )

        source_target = self.repo / "data" / "sources.seedance-2026-05-30.json"
        source_data = json.loads(source_target.read_text(encoding="utf-8"))
        source_data["sources"][0]["id"] = malicious
        source_data["sources"][0]["source_type"] = "community-probe"
        source_data["sources"][0]["confidence"] = "high"
        source_target.write_text(
            json.dumps(source_data, ensure_ascii=False),
            encoding="utf-8",
        )
        source_result = self.run_script_cp1252(
            "source_registry_check.py",
            str(self.repo),
        )
        self.assert_cp1252_safe(source_result, escaped)

        prompt_target = self.repo / "evals" / "prompt-architecture-stress.json"
        prompt_data = json.loads(prompt_target.read_text(encoding="utf-8"))
        prompt_data[0]["arm"] = malicious
        prompt_target.write_text(
            json.dumps(prompt_data, ensure_ascii=False),
            encoding="utf-8",
        )
        prompt_result = self.run_script_cp1252(
            "prompt_architecture_stress.py",
            str(prompt_target),
        )
        self.assertEqual(
            prompt_result.returncode,
            0,
            prompt_result.stdout + prompt_result.stderr,
        )
        self.assert_cp1252_safe(prompt_result, escaped)

    def test_duplicate_key_failures_are_contained_at_every_former_traceback_boundary(
        self,
    ) -> None:
        cases = (
            (
                "build_hero.py",
                "assets/masthead-outlines.json",
                ("--check",),
                '{"x":1,"x":2}',
            ),
            (
                "continuity_chain_check.py",
                "examples/sequence-airport-arrival/project-state.json",
                (str(self.repo), "--strict"),
                '{"x":1,"x":2}',
            ),
            (
                "eval_run.py",
                "evals/evals.json",
                (str(self.repo), "--self-test"),
                '{"cases":[],"cases":[]}',
            ),
        )
        for script, relative, arguments, payload in cases:
            with self.subTest(script=script):
                target = self.repo / relative
                shutil.copy2(ROOT / relative, target)
                target.write_text(payload, encoding="utf-8")
                result = self.run_script_cp1252(script, *arguments)
                output = result.stdout + result.stderr
                self.assertNotEqual(result.returncode, 0, output)
                self.assertNotIn("Traceback", output)
                marker = (
                    "source digest does not match manifest: evals/evals.json"
                    if script == "eval_run.py"
                    else "duplicate object key"
                )
                self.assert_cp1252_safe(result, marker)


if __name__ == "__main__":
    unittest.main()
