"""The documented validation runtime and CI matrix must agree."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PythonSupportContractTests(unittest.TestCase):
    def test_readme_declares_the_supported_python_range(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("CPython 3.11 through 3.13", readme)
        self.assertIn("Python 3.10 and 3.14 are outside this lock's supported range", readme)

    def test_ci_covers_both_supported_endpoints_on_windows_and_linux(self) -> None:
        workflow = (
            ROOT / ".github" / "workflows" / "validate-skills.yml"
        ).read_text(encoding="utf-8")
        for required in (
            "fail-fast: false",
            "os: [ubuntu-latest, windows-latest]",
            "python-version: [\"3.11\", \"3.13\"]",
            "runs-on: ${{ matrix.os }}",
            "python-version: ${{ matrix.python-version }}",
            "shell: python",
            'cache = Path(os.environ["RUNNER_TEMP"]) / "seedance-pycache"',
            'with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8")',
        ):
            with self.subTest(required=required):
                self.assertIn(required, workflow)

    def test_job_environment_does_not_use_step_only_runner_context(self) -> None:
        workflow = (
            ROOT / ".github" / "workflows" / "validate-skills.yml"
        ).read_text(encoding="utf-8")
        job_prefix, _steps = workflow.split("    steps:\n", 1)

        self.assertNotIn("${{ runner.", job_prefix)


if __name__ == "__main__":
    unittest.main()
