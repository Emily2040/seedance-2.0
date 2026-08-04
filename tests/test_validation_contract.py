"""Contracts for Git-independent validation and extracted ZIP use."""

from __future__ import annotations

import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "validate_repo.py"

sys.path.insert(0, str(ROOT / "scripts"))
import validate_repo  # noqa: E402


class ValidationDocumentationContractTests(unittest.TestCase):
    def test_download_zip_path_excludes_git_hygiene(self) -> None:
        validation = (ROOT / "README.md").read_text(encoding="utf-8").split(
            "## Validation", 1
        )[1]
        archive_safe, git_and_later = validation.split(
            "### Git checkout-only hygiene", 1
        )
        git_hygiene = git_and_later.split("### Checked-in source metadata age", 1)[0]
        normalized_git_hygiene = " ".join(git_hygiene.split())

        self.assertIn("python scripts/validate_repo.py --release", archive_safe)
        self.assertNotIn("git diff --check", archive_safe)
        self.assertIn("git diff --check", git_hygiene)
        self.assertIn("requires Git metadata", normalized_git_hygiene)
        self.assertIn(
            "Do not run it in a Download ZIP extraction", normalized_git_hygiene
        )

    def test_ci_uses_runner_before_checkout_only_hygiene(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "validate-skills.yml").read_text(
            encoding="utf-8"
        )
        runner = "run: python scripts/validate_repo.py"
        git_label = "name: Check diff whitespace (Git checkout only)"
        self.assertIn(runner, workflow)
        self.assertIn(git_label, workflow)
        self.assertLess(workflow.index(runner), workflow.index(git_label))


class CanonicalPlanTests(unittest.TestCase):
    def test_plan_matches_current_strict_interfaces(self) -> None:
        commands = "\n".join(
            check.display_command()
            for check in validate_repo.validation_plan(release=False)
        )
        for strict_command in (
            "python scripts/vocab_schema_check.py --strict",
            "python scripts/project_state_check.py --strict",
            "python scripts/continuity_chain_check.py --strict",
            "python scripts/prompt_lint.py --self-test --strict",
            "python scripts/prompt_architecture_stress.py --strict",
        ):
            self.assertIn(strict_command, commands)
        for truthful_command in (
            "python scripts/validate_skills.py",
            "python scripts/content_audit.py",
            "python scripts/eval_schema_check.py",
            "python scripts/schema_check.py",
            "python scripts/design_audit.py",
            "python scripts/behavior_contract_check.py",
            "python scripts/sequence_eval_check.py",
            "python scripts/generation_run_check.py",
            "python scripts/eval_run.py --self-test",
            "python scripts/extract_last_frame.py --self-test",
        ):
            self.assertIn(truthful_command, commands)
            self.assertNotIn(f"{truthful_command} --strict", commands)

    def test_release_only_enforces_source_freshness(self) -> None:
        release = "\n".join(
            check.display_command()
            for check in validate_repo.validation_plan(release=True)
        )
        pull_request = "\n".join(
            check.display_command()
            for check in validate_repo.validation_plan(release=False)
        )
        self.assertIn("--enforce-freshness", release)
        self.assertNotIn("--enforce-freshness", pull_request)

    def test_plan_contains_no_git_command(self) -> None:
        for release in (False, True):
            commands = [
                check.display_command()
                for check in validate_repo.validation_plan(release=release)
            ]
            self.assertFalse(any("git " in f"{command} " for command in commands))


class InMemoryCompilationTests(unittest.TestCase):
    def test_compiles_sources_without_writing_bytecode(self) -> None:
        with tempfile.TemporaryDirectory(prefix="seedance compile contract ") as temp_dir:
            root = Path(temp_dir)
            (root / "scripts").mkdir()
            (root / "tests").mkdir()
            (root / "scripts" / "valid.py").write_text("value = 42\n", encoding="utf-8")
            (root / "tests" / "test_valid.py").write_text(
                "assert 6 * 7 == 42\n", encoding="utf-8"
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = validate_repo.compile_python_sources(root)

            self.assertEqual(result, 0, output.getvalue())
            self.assertIn("no bytecode written", output.getvalue())
            self.assertEqual(list(root.rglob("*.pyc")), [])
            self.assertEqual(list(root.rglob("__pycache__")), [])

    def test_compile_source_size_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory(prefix="seedance compile bound ") as temp_dir:
            root = Path(temp_dir)
            (root / "scripts").mkdir()
            (root / "tests").mkdir()
            (root / "scripts" / "oversized.py").write_text("value = 1\n", encoding="utf-8")
            errors = io.StringIO()
            with (
                mock.patch.object(validate_repo, "MAX_PYTHON_SOURCE_FILE_BYTES", 4),
                contextlib.redirect_stderr(errors),
            ):
                result = validate_repo.compile_python_sources(root)
            self.assertEqual(result, 2)
            self.assertIn("Python source exceeds 4 bytes", errors.getvalue())

    def test_syntax_failure_is_bounded_and_names_the_source(self) -> None:
        with tempfile.TemporaryDirectory(prefix="seedance compile syntax ") as temp_dir:
            root = Path(temp_dir)
            (root / "scripts").mkdir()
            (root / "tests").mkdir()
            (root / "tests" / "broken.py").write_text(
                "if True print('no')\n", encoding="utf-8"
            )
            errors = io.StringIO()
            with contextlib.redirect_stderr(errors):
                result = validate_repo.compile_python_sources(root)
            self.assertEqual(result, 1)
            self.assertIn("tests/broken.py:1", errors.getvalue())
            self.assertNotIn("Traceback", errors.getvalue())


class ArchiveSafeRunnerTests(unittest.TestCase):
    def test_orchestration_anchors_every_child_to_extracted_root(self) -> None:
        calls: list[tuple[tuple[str, ...], Path]] = []

        def successful_runner(
            command: tuple[str, ...], **kwargs: object
        ) -> subprocess.CompletedProcess[object]:
            calls.append((command, Path(kwargs["cwd"])))
            return subprocess.CompletedProcess(command, 0)

        with tempfile.TemporaryDirectory(prefix="seedance archive path ") as temp_dir:
            extracted = Path(temp_dir) / "nested parent" / "seedance extracted"
            extracted.mkdir(parents=True)
            with contextlib.redirect_stdout(io.StringIO()):
                result = validate_repo.run_validation(
                    extracted, release=True, runner=successful_runner
                )

        self.assertEqual(result, 0)
        self.assertEqual(len(calls), len(validate_repo.validation_plan(release=True)))
        self.assertTrue(all(cwd == extracted.resolve() for _, cwd in calls))
        self.assertFalse(any("git" in command for command, _ in calls))

    def test_runner_executes_from_an_extracted_zip_with_no_git(self) -> None:
        with tempfile.TemporaryDirectory(prefix="seedance zip path ") as temp_dir:
            base = Path(temp_dir)
            archive_path = base / "published head.zip"
            extracted = base / "parent folder with spaces" / "archive copy"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.write(RUNNER, "scripts/validate_repo.py")
                archive.writestr("scripts/example.py", "value = 42\n")
                archive.writestr("tests/test_example.py", "assert 6 * 7 == 42\n")
            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(extracted)

            self.assertFalse((extracted / ".git").exists())
            caller = base / "unrelated caller with spaces"
            caller.mkdir()
            listed = subprocess.run(
                [sys.executable, str(extracted / "scripts" / "validate_repo.py"), "--release", "--list"],
                cwd=caller,
                text=True,
                capture_output=True,
            )
            compiled = subprocess.run(
                [sys.executable, str(extracted / "scripts" / "validate_repo.py"), "--compile-sources"],
                cwd=caller,
                text=True,
                capture_output=True,
            )

        self.assertEqual(listed.returncode, 0, listed.stdout + listed.stderr)
        self.assertIn("--enforce-freshness", listed.stdout)
        self.assertNotIn("git diff", listed.stdout)
        self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
        self.assertIn("no bytecode written", compiled.stdout)


if __name__ == "__main__":
    unittest.main()
