from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PromptLintTests(unittest.TestCase):
    def test_prompt_lint_self_test_and_examples(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/prompt_lint.py", "--self-test", "--strict"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
