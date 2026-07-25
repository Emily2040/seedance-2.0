"""Freshness classification must not depend on when CI happens to run.

The source registry carries a `last_verified` date. Comparing it against the
wall clock is useful signal, but it is not a property of the commit: the same
tree flips from passing to failing as the calendar advances. These tests pin
the boundaries so per-pull-request validation stays deterministic and only
explicit enforcement can fail.
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import source_registry_check as checker  # noqa: E402

VERIFIED = date(2026, 6, 20)


def findings(age_days: int, enforce: bool) -> tuple[list[str], list[str]]:
    today = date.fromordinal(VERIFIED.toordinal() + age_days)
    return checker.freshness_findings(VERIFIED, today, enforce)


class FreshnessClassificationTests(unittest.TestCase):
    def test_fresh_registry_is_silent(self) -> None:
        for age in (0, 1, checker.STALE_WARN_DAYS):
            with self.subTest(age=age):
                for enforce in (False, True):
                    errors, warnings = findings(age, enforce)
                    self.assertEqual(errors, [])
                    self.assertEqual(warnings, [])

    def test_warn_window_never_fails_the_build(self) -> None:
        for age in (checker.STALE_WARN_DAYS + 1, checker.STALE_ERROR_DAYS):
            with self.subTest(age=age):
                for enforce in (False, True):
                    errors, warnings = findings(age, enforce)
                    self.assertEqual(errors, [])
                    self.assertEqual(len(warnings), 1)
                    self.assertIn(f"{age} days old", warnings[0])

    def test_stale_registry_only_fails_when_enforcement_is_requested(self) -> None:
        age = checker.STALE_ERROR_DAYS + 1
        errors, warnings = findings(age, False)
        self.assertEqual(errors, [], "default validation must not fail on the calendar")
        self.assertEqual(len(warnings), 1)

        errors, warnings = findings(age, True)
        self.assertEqual(len(errors), 1, "explicit enforcement must still fail")
        self.assertEqual(warnings, [])

    def test_verdict_is_stable_far_past_the_threshold(self) -> None:
        """A very old registry must still not break unrelated pull requests."""
        errors, warnings = findings(3650, False)
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1)

    def test_future_dated_registry_is_not_reported_as_stale(self) -> None:
        errors, warnings = findings(-5, True)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])


class CommandLineBehaviourTests(unittest.TestCase):
    """The default invocation is what CI runs, so it must pass on this tree."""

    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "source_registry_check.py"

    def run_checker(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.script), str(self.root), *args],
            capture_output=True,
            text=True,
        )

    def test_default_run_passes_on_this_repository(self) -> None:
        result = self.run_checker("--strict")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_enforcement_flag_is_available(self) -> None:
        result = self.run_checker("--help")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("--enforce-freshness", result.stdout)


class ReleaseChecklistTests(unittest.TestCase):
    """Relaxing per-pull-request validation only holds if release still enforces.

    Without this, dropping the gate from CI would quietly leave no enforced
    caller anywhere, and a stale registry would pass every documented check.
    """

    readme = Path(__file__).resolve().parents[1] / "README.md"

    def test_release_checklist_enforces_freshness(self) -> None:
        lines = [
            line.strip()
            for line in self.readme.read_text(encoding="utf-8").splitlines()
            if "source_registry_check.py" in line
        ]
        self.assertTrue(lines, "README must document the source-registry check")
        for line in lines:
            self.assertIn(
                "--enforce-freshness",
                line,
                "the documented release check must fail on a stale registry",
            )


if __name__ == "__main__":
    unittest.main()
