"""Bytecode is a finding only when git actually tracks it.

Running the test suite imports modules, which writes __pycache__. Treating any
bytecode on disk as "committed" made the documented validation command fail for
anyone who ran the tests first, reporting gitignored files as committed ones.
CI never reproduced it because the workflow sets PYTHONDONTWRITEBYTECODE.
"""

from __future__ import annotations

import subprocess
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import validate_skills  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
GIT = shutil.which("git")


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


class TrackedFilesTests(unittest.TestCase):
    def test_returns_none_outside_a_git_checkout(self) -> None:
        """An unpacked ZIP has no index, so nothing can be committed."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(validate_skills.tracked_files(Path(tmp)))

    @unittest.skipUnless(GIT, "requires the Git executable")
    def test_lists_tracked_paths_in_a_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            git(repo, "init")
            (repo / "kept.py").write_text("x = 1\n", encoding="utf-8")
            git(repo, "add", "kept.py")
            tracked = validate_skills.tracked_files(repo)
            self.assertIsNotNone(tracked)
            self.assertIn("kept.py", tracked)

    @unittest.skipUnless(GIT, "requires the Git executable")
    def test_untracked_bytecode_is_not_listed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            git(repo, "init")
            (repo / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
            cache = repo / "scripts" / "__pycache__"
            cache.mkdir(parents=True)
            (cache / "mod.cpython-311.pyc").write_bytes(b"\x00")
            git(repo, "add", ".gitignore")
            tracked = validate_skills.tracked_files(repo)
            self.assertNotIn("scripts/__pycache__/mod.cpython-311.pyc", tracked)


class RepositoryTests(unittest.TestCase):
    def test_locally_generated_bytecode_does_not_fail_validation(self) -> None:
        """The regression itself: import a script, then validate the repo."""
        subprocess.run(
            [sys.executable, "-c", "import sys; sys.path.insert(0, 'scripts'); import prompt_lint"],
            cwd=ROOT, check=True, capture_output=True,
        )
        proc = subprocess.run(
            [sys.executable, "scripts/validate_skills.py"],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertNotIn("must not be committed", proc.stdout + proc.stderr)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
