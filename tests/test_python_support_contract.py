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

        for name, job, runner in (
            ("linux", linux_job, "runs-on: ubuntu-latest"),
            ("windows", windows_job, "runs-on: windows-latest"),
        ):
            with self.subTest(job=name):
                self.assertIn(runner, job)
                self.assertIn('python-version: ["3.11", "3.13"]', job)
                self.assertIn("python-version: ${{ matrix.python-version }}", job)
                self.assertIn("fail-fast: false", job)

    def test_job_environment_does_not_use_step_only_runner_context(self) -> None:
        workflow = (
            ROOT / ".github" / "workflows" / "validate-skills.yml"
        ).read_text(encoding="utf-8")
        for job in workflow.split("    steps:\n")[:-1]:
            self.assertNotIn("${{ runner.", job)


if __name__ == "__main__":
    unittest.main()
