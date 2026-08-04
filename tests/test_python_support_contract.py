"""Keep the documented Python range aligned with both CI jobs."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PythonSupportContractTests(unittest.TestCase):
    def test_readme_declares_the_supported_python_range(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        normalized = " ".join(readme.split())
        self.assertIn("CPython 3.11 through 3.13", normalized)
        self.assertIn(
            "Python 3.10 and 3.14 are outside this lock's supported range",
            normalized,
        )

    def test_linux_and_windows_jobs_cover_both_supported_endpoints(self) -> None:
        workflow = (
            ROOT / ".github" / "workflows" / "validate-skills.yml"
        ).read_text(encoding="utf-8")
        linux_job, windows_and_later = workflow.split(
            "  windows-frame-publication:\n", 1
        )
        windows_job = "  windows-frame-publication:\n" + windows_and_later

        for name, job, runner, matrix in (
            (
                "linux",
                linux_job,
                "runs-on: ubuntu-latest",
                'python-version: ["3.11", "3.13"]',
            ),
            (
                "windows",
                windows_job,
                "runs-on: windows-latest",
                'python-version: ["3.11", "3.12", "3.13"]',
            ),
        ):
            with self.subTest(job=name):
                self.assertIn(runner, job)
                self.assertIn(matrix, job)
                self.assertIn("python-version: ${{ matrix.python-version }}", job)
                self.assertIn("fail-fast: false", job)

    def test_job_environment_does_not_use_step_only_runner_context(self) -> None:
        workflow = (
            ROOT / ".github" / "workflows" / "validate-skills.yml"
        ).read_text(encoding="utf-8")
        for job in workflow.split("    steps:\n")[:-1]:
            self.assertNotIn("${{ runner.", job)

    def test_windows_job_runs_masthead_runner_trust_regressions(self) -> None:
        workflow = (
            ROOT / ".github" / "workflows" / "validate-skills.yml"
        ).read_text(encoding="utf-8")
        _, windows_job = workflow.split("  windows-frame-publication:\n", 1)
        tests = (
            "test_windows_venv_runner_source_selects_the_exact_upstream_variant",
            "test_windows_venv_runner_source_refuses_the_wrong_variant",
            "test_windows_venv_runner_source_matches_real_envbuilder",
            "test_external_trust_rejects_runner_config_marker_and_script_tampering",
            "test_forged_runner_and_self_authored_marker_lack_external_trust",
            "test_in_venv_sitecustomize_cannot_short_circuit_a_check",
            "test_pip_bootstrap_verifies_initialized_runner_and_config_before_execution",
        )
        for test in tests:
            with self.subTest(test=test):
                self.assertIn(test, windows_job)
        self.assertLess(
            windows_job.index("Run Windows masthead runner trust regressions"),
            windows_job.index("Provision and verify FFmpeg"),
        )


if __name__ == "__main__":
    unittest.main()
