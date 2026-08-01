from __future__ import annotations

import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "validate_repo.py"

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


class ArchiveSafeRunnerTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
