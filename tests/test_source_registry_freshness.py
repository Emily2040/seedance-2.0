"""Freshness classification must not depend on when CI happens to run.

The source registry carries a `last_verified` date. Comparing it against the
wall clock is useful signal, but it is not a property of the commit: the same
tree flips from passing to failing as the calendar advances. These tests pin
the boundaries so per-pull-request validation uses the stable HEAD date to
reject impossible future stamps, while only explicit enforcement can fail on
wall-clock age.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Callable
from contextlib import redirect_stdout
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import source_registry_check as checker  # noqa: E402

VERIFIED = date(2026, 6, 20)


def findings(age_days: int, enforce: bool) -> tuple[list[str], list[str]]:
    today = date.fromordinal(VERIFIED.toordinal() + age_days)
    return checker.freshness_findings(VERIFIED, today, enforce)


def commit_fixture(repo: Path, commit_date: date) -> None:
    """Create one deterministic commit rooted exactly at ``repo``."""
    commit_timestamp = f"{commit_date.isoformat()}T12:00:00+00:00"
    git_environment = os.environ.copy()
    git_environment.update(
        {
            "GIT_AUTHOR_DATE": commit_timestamp,
            "GIT_COMMITTER_DATE": commit_timestamp,
        }
    )
    subprocess.run(
        ["git", "init", "--quiet"], cwd=repo, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "add", "."], cwd=repo, check=True, capture_output=True
    )
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "--quiet",
            "-m",
            "fixture",
        ],
        cwd=repo,
        env=git_environment,
        check=True,
        capture_output=True,
    )


class FreshnessClassificationTests(unittest.TestCase):
    def test_checked_in_stamp_accepts_crlf_without_polluting_the_date(self) -> None:
        errors: list[str] = []

        self.assertEqual(
            checker.checked_in_last_verified(
                f"last_verified: {VERIFIED.isoformat()}\r\n",
                "source-registry.md",
                VERIFIED,
                errors,
            ),
            VERIFIED,
        )
        self.assertEqual(errors, [])

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

    def test_future_dated_registry_is_rejected(self) -> None:
        errors, warnings = findings(-5, False)
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn("future", warnings[0])

        errors, warnings = findings(-5, True)
        self.assertEqual(len(errors), 1)
        self.assertIn("future", errors[0])
        self.assertEqual(warnings, [])

    def test_future_ordering_requires_an_explicit_calendar_anchor(self) -> None:
        future = VERIFIED + timedelta(days=3650)
        text = f"last_verified: {future.isoformat()}\n"

        deterministic_errors: list[str] = []
        self.assertEqual(
            checker.checked_in_last_verified(
                text, "source-registry.md", None, deterministic_errors
            ),
            future,
        )
        self.assertEqual(deterministic_errors, [])

        enforced_errors: list[str] = []
        self.assertIsNone(
            checker.checked_in_last_verified(
                text, "source-registry.md", VERIFIED, enforced_errors
            )
        )
        self.assertEqual(len(enforced_errors), 1)
        self.assertIn("future", enforced_errors[0])


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

    def run_fixture(
        self,
        *,
        registry_verified: date | None = None,
        registry_stamp: str | None = None,
        api_status_text: str | None = None,
        reference_text: str | None = None,
        fixture_observer: Callable[[Path], None] | None = None,
        enforce_freshness: bool = True,
        commit_date: date | None = None,
    ) -> subprocess.CompletedProcess[str]:
        today = date.today()
        registry_verified = registry_verified or today
        registry_stamp = registry_stamp or registry_verified.isoformat()
        api_status_text = api_status_text or f"last_verified: {today.isoformat()}\n"
        reference_text = reference_text or f"last_verified: {today.isoformat()}\n"
        # Keep synthetic repositories outside the source tree.  The full suite
        # legitimately installs/copies this repository in parallel; an
        # in-tree temporary directory can disappear between copytree's scan
        # and open, turning an unrelated fixture cleanup into a false installer
        # failure.
        with tempfile.TemporaryDirectory(prefix="source-freshness-") as temp_dir:
            repo = Path(temp_dir)
            if fixture_observer is not None:
                fixture_observer(repo)
            references = repo / "references"
            data_dir = repo / "data"
            references.mkdir()
            data_dir.mkdir()
            (references / "source-registry.md").write_text(
                "\n".join(
                    [
                        "# Source Registry",
                        f"last_verified: {registry_stamp}",
                        "`confirmed` `volatile` `field-observed` `unverified` `internal`",
                        "seed.bytedance.com volcengine.com arxiv.org runwayml.com",
                    ]
                ),
                encoding="utf-8",
            )
            (references / "api-status.md").write_text(
                api_status_text, encoding="utf-8"
            )
            (references / "platform-surface-matrix.md").write_text(
                reference_text, encoding="utf-8"
            )
            sources = []
            for index in range(20):
                sources.append(
                    {
                        "id": f"source-{index}",
                        "title": f"Source {index}",
                        "url": f"https://example.com/{index}",
                        "language": "en",
                        "source_type": "official",
                        "retrieved_at": today.isoformat(),
                        "confidence": "high",
                        "claims": [],
                    }
                )
            (data_dir / "sources.seedance-2026-05-30.json").write_text(
                json.dumps({"sources": sources}), encoding="utf-8"
            )
            if commit_date is not None:
                commit_fixture(repo, commit_date)
            command = [sys.executable, str(self.script), str(repo)]
            if enforce_freshness:
                command.append("--enforce-freshness")
            return subprocess.run(
                command,
                capture_output=True,
                text=True,
            )

    def test_default_run_passes_on_this_repository(self) -> None:
        result = self.run_checker()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_default_pr_mode_does_not_read_the_wall_clock(self) -> None:
        class ExplodingDate(date):
            @classmethod
            def today(cls) -> date:
                raise AssertionError("ordinary PR validation read the wall clock")

        output = io.StringIO()
        with (
            mock.patch.object(checker, "date", ExplodingDate),
            mock.patch.object(
                sys,
                "argv",
                ["source_registry_check.py", str(self.root)],
            ),
            redirect_stdout(output),
        ):
            code = checker.main()

        self.assertEqual(code, 0, output.getvalue())

    def test_synthetic_repositories_stay_outside_the_source_tree(self) -> None:
        observed: list[Path] = []
        result = self.run_fixture(fixture_observer=observed.append)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(observed), 1)
        self.assertFalse(observed[0].is_relative_to(self.root))

    def test_enforcement_flag_is_available(self) -> None:
        result = self.run_checker("--help")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("--enforce-freshness", result.stdout)

    def test_unrelated_newer_date_cannot_mask_stale_reference_stamp(self) -> None:
        today = date.today()
        stale = today - timedelta(days=checker.STALE_ERROR_DAYS + 1)
        result = self.run_fixture(
            reference_text=(
                f"last_verified: {stale.isoformat()}\n"
                f"unrelated release date: {today.isoformat()}\n"
            )
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("platform-surface-matrix.md is 31 days behind", result.stdout)

    def test_future_registry_stamp_fails(self) -> None:
        result = self.run_fixture(registry_verified=date.today() + timedelta(days=1))
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("future", result.stdout.lower())

    @unittest.skipUnless(shutil.which("git"), "requires Git for a stable PR commit date")
    def test_default_pr_mode_rejects_stamps_after_the_commit_date(self) -> None:
        future = VERIFIED + timedelta(days=1)
        stamp = f"last_verified: {future.isoformat()}\n"
        result = self.run_fixture(
            registry_verified=future,
            api_status_text=stamp,
            reference_text=stamp,
            enforce_freshness=False,
            commit_date=VERIFIED,
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("future", result.stdout.lower())
        self.assertNotIn("days old", result.stdout.lower())

    @unittest.skipUnless(shutil.which("git"), "requires Git for repository containment")
    def test_nested_non_repository_does_not_inherit_parent_head_date(self) -> None:
        with tempfile.TemporaryDirectory(prefix="source-anchor-parent-") as temp_dir:
            parent = Path(temp_dir)
            (parent / "tracked.txt").write_text("parent\n", encoding="utf-8")
            commit_fixture(parent, VERIFIED)
            nested_archive = parent / "downloaded archive"
            nested_archive.mkdir()

            self.assertIsNone(checker.repository_head_date(nested_archive))

    @unittest.skipUnless(shutil.which("git"), "requires Git for a stable PR commit date")
    def test_linked_worktree_root_uses_its_own_head_date(self) -> None:
        expected = subprocess.run(
            ["git", "-C", str(self.root), "show", "-s", "--format=%cs", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

        self.assertEqual(
            checker.repository_head_date(self.root),
            date.fromisoformat(expected),
        )

    def test_green_output_refuses_live_verification_claim(self) -> None:
        result = self.run_fixture()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("offline source metadata", result.stdout.lower())
        self.assertIn("does not fetch", result.stdout.lower())

    def test_rejects_impossible_registry_date(self) -> None:
        result = self.run_fixture(registry_stamp="2026-02-30")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("invalid last_verified date", result.stdout)

    def test_rejects_missing_reference_stamp_despite_unrelated_date(self) -> None:
        result = self.run_fixture(
            reference_text=f"release date: {date.today().isoformat()}\n"
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("platform-surface-matrix.md missing last_verified", result.stdout)

    def test_rejects_malformed_reference_stamp_despite_unrelated_date(self) -> None:
        result = self.run_fixture(
            reference_text=(
                "last_verified: 2026-02-30\n"
                f"release date: {date.today().isoformat()}\n"
            )
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("platform-surface-matrix.md has invalid last_verified date", result.stdout)

    def test_rejects_duplicate_reference_stamps(self) -> None:
        today = date.today().isoformat()
        result = self.run_fixture(
            reference_text=f"last_verified: {today}\nlast_verified: {today}\n"
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("must contain exactly one last_verified field", result.stdout)

    def test_rejects_split_line_reference_stamp(self) -> None:
        today = date.today().isoformat()
        result = self.run_fixture(reference_text=f"last_verified:\n{today}\n")

        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("platform-surface-matrix.md has malformed last_verified", result.stdout)

    def test_rejects_future_reference_stamp(self) -> None:
        future = date.today() + timedelta(days=1)
        result = self.run_fixture(reference_text=f"last_verified: {future.isoformat()}\n")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("platform-surface-matrix.md last_verified", result.stdout)
        self.assertIn("future", result.stdout.lower())

    def test_rejects_future_api_anchor_stamp(self) -> None:
        future = date.today() + timedelta(days=1)
        result = self.run_fixture(api_status_text=f"last_verified: {future.isoformat()}\n")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("api-status.md last_verified", result.stdout)
        self.assertIn("future", result.stdout.lower())

    def test_explicit_current_stamp_is_not_harmed_by_historical_dates(self) -> None:
        today = date.today().isoformat()
        result = self.run_fixture(
            reference_text=(
                f"last_verified: {today}\n"
                "historical launch: 2020-01-01\n"
            )
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class ReleaseChecklistTests(unittest.TestCase):
    """Relaxing per-pull-request validation only holds if release still enforces.

    Without this, dropping the gate from CI would quietly leave no enforced
    caller anywhere, and a stale registry would pass every documented check.
    """

    root = Path(__file__).resolve().parents[1]
    readme = root / "README.md"
    workflow = root / ".github" / "workflows" / "source-freshness-review.yml"

    def test_release_checklist_enforces_freshness(self) -> None:
        readme = self.readme.read_text(encoding="utf-8")
        self.assertIn("python scripts/validate_repo.py --release", readme)

        scripts = self.root / "scripts"
        sys.path.insert(0, str(scripts))
        try:
            import validate_repo

            source_commands = [
                check.display_command()
                for check in validate_repo.validation_plan(release=True)
                if "source_registry_check.py" in check.display_command()
            ]
        finally:
            sys.path.remove(str(scripts))

        self.assertEqual(len(source_commands), 1)
        self.assertIn(
            "--enforce-freshness",
            source_commands[0],
            "the canonical release runner must fail on a stale registry",
        )

    def test_docs_define_the_offline_metadata_boundary(self) -> None:
        text = self.readme.read_text(encoding="utf-8").lower()
        self.assertIn("does not fetch urls", text)
        self.assertIn("does not prove that any upstream claim is still true", text)

    def test_scheduled_green_state_refuses_live_verification_claim(self) -> None:
        text = self.workflow.read_text(encoding="utf-8").lower()
        self.assertIn("did not fetch or re-read upstream sources", text)
        self.assertNotIn("references are within the freshness window. no action needed.", text)


if __name__ == "__main__":
    unittest.main()
