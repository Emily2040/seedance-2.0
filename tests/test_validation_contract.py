from __future__ import annotations

import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "validate_repo.py"
ARCHIVE_REPLAY_ENV = "SEEDANCE_ARCHIVE_E2E_INNER"

sys.path.insert(0, str(ROOT / "scripts"))

import validate_repo  # noqa: E402


class ValidationDocumentationContractTests(unittest.TestCase):
    def test_download_zip_validation_does_not_require_git(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        validation = readme.split("## Validation", 1)[1]
        archive_safe = validation.split("### Git checkout-only hygiene", 1)[0]

        self.assertNotIn(
            "git diff --check",
            archive_safe,
            "Download ZIP users must not be given a Git-only command as part of "
            "the archive-safe validation path.",
        )
        self.assertIn("python scripts/validate_repo.py --release", archive_safe)

    def test_git_hygiene_is_separate_and_explicitly_checkout_only(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        validation = readme.split("## Validation", 1)[1]
        git_hygiene = validation.split("### Git checkout-only hygiene", 1)[1]
        git_hygiene = git_hygiene.split("### Source freshness", 1)[0]

        self.assertIn("git diff --check", git_hygiene)
        self.assertIn("requires Git metadata", git_hygiene)
        self.assertIn("Do not run it in a Download ZIP extraction", git_hygiene)

    def test_ci_uses_the_canonical_runner_before_git_only_hygiene(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "validate-skills.yml").read_text(
            encoding="utf-8"
        )

        runner_line = "run: python scripts/validate_repo.py"
        git_label = "name: Check diff whitespace (Git checkout only)"
        self.assertIn(runner_line, workflow)
        self.assertIn(git_label, workflow)
        self.assertLess(workflow.index(runner_line), workflow.index(git_label))
        self.assertNotIn("run: python scripts/validate_skills.py --strict", workflow)


class InMemoryCompilationTests(unittest.TestCase):
    def test_compiles_sources_without_writing_bytecode(self) -> None:
        with tempfile.TemporaryDirectory(prefix="seedance compile contract ") as temp_dir:
            root = Path(temp_dir)
            (root / "scripts").mkdir()
            (root / "tests").mkdir()
            (root / "scripts" / "valid.py").write_text(
                "def answer():\n    return 42\n",
                encoding="utf-8",
            )
            (root / "tests" / "test_valid.py").write_text(
                "assert 6 * 7 == 42\n",
                encoding="utf-8",
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

    def test_syntax_failure_names_the_source_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory(prefix="seedance compile syntax ") as temp_dir:
            root = Path(temp_dir)
            (root / "scripts").mkdir()
            (root / "tests").mkdir()
            (root / "tests" / "broken.py").write_text("if True print('no')\n", encoding="utf-8")

            errors = io.StringIO()
            with contextlib.redirect_stderr(errors):
                result = validate_repo.compile_python_sources(root)

            self.assertEqual(result, 1)
            self.assertIn("tests/broken.py:1", errors.getvalue())
            self.assertNotIn("Traceback", errors.getvalue())


class ArchiveSafeRunnerTests(unittest.TestCase):
    def test_git_specific_tests_skip_cleanly_without_git_executable(self) -> None:
        env = os.environ.copy()
        env["PATH"] = ""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "unittest",
                "-v",
                "tests.test_validate_skills_bytecode.TrackedFilesTests",
            ],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
        )

        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("skipped", output)
        self.assertNotIn("FileNotFoundError", output)

    def test_both_plans_exclude_git_commands(self) -> None:
        for release in (False, True):
            with self.subTest(release=release):
                commands = [check.display_command() for check in validate_repo.validation_plan(release=release)]
                self.assertFalse(any("git " in f"{command} " for command in commands))

    def test_release_plan_enforces_freshness_but_pull_request_plan_does_not(self) -> None:
        release = "\n".join(
            check.display_command() for check in validate_repo.validation_plan(release=True)
        )
        pull_request = "\n".join(
            check.display_command() for check in validate_repo.validation_plan(release=False)
        )

        self.assertIn("--enforce-freshness", release)
        self.assertNotIn("--enforce-freshness", pull_request)

    def test_orchestration_handles_nested_space_path_without_git(self) -> None:
        calls: list[tuple[tuple[str, ...], Path]] = []

        def successful_runner(command: tuple[str, ...], **kwargs: object) -> subprocess.CompletedProcess[object]:
            calls.append((command, Path(kwargs["cwd"])))
            return subprocess.CompletedProcess(command, 0)

        with tempfile.TemporaryDirectory(prefix="seedance archive path ") as temp_dir:
            extracted = Path(temp_dir) / "nested parent" / "seedance extracted"
            extracted.mkdir(parents=True)
            self.assertFalse((extracted / ".git").exists())

            previous = Path.cwd()
            deep_cwd = extracted / "deep" / "working folder"
            deep_cwd.mkdir(parents=True)
            try:
                os.chdir(deep_cwd)
                with contextlib.redirect_stdout(io.StringIO()):
                    result = validate_repo.run_validation(
                        extracted,
                        release=True,
                        runner=successful_runner,
                    )
            finally:
                os.chdir(previous)

        self.assertEqual(result, 0)
        self.assertEqual(len(calls), len(validate_repo.validation_plan(release=True)))
        self.assertTrue(all(cwd == extracted.resolve() for _, cwd in calls))
        self.assertFalse(any("git" in command for command, _ in calls))

    def test_copied_runner_lists_archive_plan_from_nested_no_git_tree(self) -> None:
        with tempfile.TemporaryDirectory(prefix="seedance zip path ") as temp_dir:
            extracted = Path(temp_dir) / "parent folder" / "archive copy"
            scripts = extracted / "scripts"
            nested = extracted / "nested" / "working folder"
            scripts.mkdir(parents=True)
            nested.mkdir(parents=True)
            copied_runner = scripts / RUNNER.name
            shutil.copy2(RUNNER, copied_runner)
            self.assertFalse((extracted / ".git").exists())

            result = subprocess.run(
                [sys.executable, str(copied_runner), "--release", "--list"],
                cwd=nested,
                text=True,
                capture_output=True,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("python scripts/validate_skills.py --strict", result.stdout)
        self.assertIn("--enforce-freshness", result.stdout)
        self.assertNotIn("git diff", result.stdout)


class ExtractedArchiveEndToEndTests(unittest.TestCase):
    @unittest.skipIf(
        os.environ.get(ARCHIVE_REPLAY_ENV) == "1",
        "outer test already owns the extracted-archive replay",
    )
    def test_full_suite_runs_from_deep_spaced_archive_without_git(self) -> None:
        with tempfile.TemporaryDirectory(prefix="seedance archive e2e ") as temp_dir:
            base = Path(temp_dir)
            archive_path = base / "published head.zip"
            extracted = base / "parent folder with spaces"
            while len(str(extracted)) < 140:
                extracted /= "nested folder with spaces"

            with zipfile.ZipFile(
                archive_path,
                "w",
                compression=zipfile.ZIP_DEFLATED,
            ) as archive:
                for source in sorted(ROOT.rglob("*")):
                    relative = source.relative_to(ROOT)
                    if (
                        not source.is_file()
                        or relative.parts[0] == ".git"
                        or "__pycache__" in relative.parts
                        or source.suffix == ".pyc"
                    ):
                        continue
                    archive.write(source, relative.as_posix())

            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(extracted)

            self.assertFalse((extracted / ".git").exists())
            caller = base / "unrelated caller with spaces"
            caller.mkdir()
            environment = os.environ.copy()
            environment.update(
                PATH="",
                PYTHONDONTWRITEBYTECODE="1",
                **{ARCHIVE_REPLAY_ENV: "1"},
            )
            result = subprocess.run(
                [sys.executable, str(extracted / "scripts" / "validate_repo.py")],
                cwd=caller,
                env=environment,
                text=True,
                capture_output=True,
                timeout=240,
            )

        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output[-16000:])
        self.assertIn("Mode: archive-safe pull-request; Git is not required", output)
        self.assertIn("[19/19] Compile Python sources in memory", output)
        self.assertIn("PASS: all 19 archive-safe checks completed", output)
        self.assertEqual(output.count("skipped 'requires the Git executable'"), 2)
        self.assertNotIn("FileNotFoundError", output)


if __name__ == "__main__":
    unittest.main()
