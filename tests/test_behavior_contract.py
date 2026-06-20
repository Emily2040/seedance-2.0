from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BehaviorContractTests(unittest.TestCase):
    def test_behavior_contract_is_present(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/behavior_contract_check.py", "--strict"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
