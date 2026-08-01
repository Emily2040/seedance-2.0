"""Regression tests for Windows installer path-length preflight."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install_codex_skill.py"
LONG_PAYLOAD_ENTRY = Path(
    "examples/sequence-airport-arrival/clip-02-continuation-contract.json"
)

sys.path.insert(0, str(ROOT / "scripts"))
import install_codex_skill as installer  # noqa: E402


def windows_units(path: Path) -> int:
    return len(str(path).encode("utf-16-le")) // 2


def overlong_skills_dir(root: Path) -> Path:
    skills_dir = root
    destination = skills_dir / "seedance-20"
    index = 0
    while windows_units(destination / LONG_PAYLOAD_ENTRY) < 340:
        skills_dir /= f"installer-path-segment-{index:02d}"
        destination = skills_dir / "seedance-20"
        index += 1
    return skills_dir


def destination_with_units(root: Path, target_units: int) -> Path:
    one_character = root / "x" / "seedance-20"
    padding_length = target_units - windows_units(one_character) + 1
    if padding_length < 1 or padding_length > 255:
        raise AssertionError("test root cannot produce the requested path length")
    destination = root / ("x" * padding_length) / "seedance-20"
    if windows_units(destination) != target_units:
        raise AssertionError("destination padding did not reach the requested length")
    return destination


def make_payload(repo_root: Path) -> None:
    repo_root.mkdir()
    (repo_root / "SKILL.md").write_text("test payload\n", encoding="utf-8")


@unittest.skipUnless(os.name == "nt", "Windows MAX_PATH regression")
class WindowsLongPathSubprocessTests(unittest.TestCase):
    def test_overlong_destination_is_refused_before_filesystem_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = overlong_skills_dir(Path(tmp))
            destination = skills_dir / "seedance-20"

            result = subprocess.run(
                [sys.executable, str(INSTALLER), "--dest", str(skills_dir)],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=90,
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertEqual(result.stderr, "", result.stderr)
            self.assertNotIn("Traceback", result.stdout)
            self.assertIn("Refusing to install: Windows portable path limit", result.stdout)
            self.assertIn("UTF-16 code units", result.stdout)
            self.assertIn("Choose a shorter --dest", result.stdout)
            self.assertFalse(skills_dir.exists(), "preflight refusal must write nothing")
            self.assertFalse(destination.exists())


class WindowsPortablePolicyTests(unittest.TestCase):
    def test_utf16_units_count_non_bmp_characters_twice(self) -> None:
        self.assertEqual(installer.windows_utf16_units(Path("A🚀")), 3)

    def test_destination_directory_limit_accepts_boundary_and_refuses_next_unit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_root = root / "payload"
            make_payload(repo_root)
            path_root = Path(tempfile.gettempdir()) / "seedance-length-policy"
            boundary = destination_with_units(
                path_root, installer.WINDOWS_PORTABLE_DIRECTORY_LIMIT
            )
            over_boundary = destination_with_units(
                path_root, installer.WINDOWS_PORTABLE_DIRECTORY_LIMIT + 1
            )

            installer.assert_windows_portable_install_path(boundary, repo_root)
            with self.assertRaisesRegex(
                ValueError,
                rf"Predicted directory path uses "
                rf"{installer.WINDOWS_PORTABLE_DIRECTORY_LIMIT + 1} UTF-16 code units; "
                rf"safe limit is {installer.WINDOWS_PORTABLE_DIRECTORY_LIMIT}",
            ):
                installer.assert_windows_portable_install_path(over_boundary, repo_root)

    def test_file_limit_accepts_boundary_and_names_the_first_unsafe_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_root = root / "payload"
            make_payload(repo_root)
            destination = destination_with_units(
                Path(tempfile.gettempdir()) / "seedance-file-policy", 190
            )
            safe_name_length = (
                installer.WINDOWS_PORTABLE_FILE_LIMIT
                - installer.windows_utf16_units(destination)
                - 1
            )
            safe_name = "s" * safe_name_length
            unsafe_name = "u" * (safe_name_length + 1)
            (repo_root / safe_name).write_text("safe boundary\n", encoding="utf-8")

            installer.assert_windows_portable_install_path(destination, repo_root)
            (repo_root / unsafe_name).write_text("one unit too long\n", encoding="utf-8")

            with self.assertRaises(ValueError) as raised:
                installer.assert_windows_portable_install_path(destination, repo_root)
            message = str(raised.exception)
            self.assertIn("Predicted file path uses 260 UTF-16 code units", message)
            self.assertIn("safe limit is 259", message)
            self.assertIn(f"Payload entry: {unsafe_name}", message)
            self.assertIn("Choose a shorter --dest", message)
            self.assertIn("CODEX_HOME closer to the drive root", message)

    def test_empty_payload_directory_uses_the_directory_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_root = root / "payload"
            make_payload(repo_root)
            destination = destination_with_units(
                Path(tempfile.gettempdir()) / "seedance-directory-policy", 190
            )
            safe_name_length = (
                installer.WINDOWS_PORTABLE_DIRECTORY_LIMIT
                - installer.windows_utf16_units(destination)
                - 1
            )
            safe_name = "d" * safe_name_length
            unsafe_name = "e" * (safe_name_length + 1)
            (repo_root / safe_name).mkdir()

            installer.assert_windows_portable_install_path(destination, repo_root)
            (repo_root / unsafe_name).mkdir()

            with self.assertRaises(ValueError) as raised:
                installer.assert_windows_portable_install_path(destination, repo_root)
            message = str(raised.exception)
            self.assertIn("Predicted directory path uses 248 UTF-16 code units", message)
            self.assertIn("safe limit is 247", message)
            self.assertIn(f"Payload entry: {unsafe_name}", message)

    def test_ignored_development_tree_does_not_reduce_the_supported_length(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_root = root / "payload"
            make_payload(repo_root)
            ignored = repo_root / "tests"
            ignored.mkdir()
            (ignored / ("x" * 120)).write_text("ignored\n", encoding="utf-8")
            destination = destination_with_units(
                Path(tempfile.gettempdir()) / "seedance-ignore-policy", 190
            )

            installer.assert_windows_portable_install_path(destination, repo_root)

    def test_relative_destination_is_measured_from_current_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp) / "payload"
            make_payload(repo_root)
            relative = Path("short-skills") / "seedance-20"

            expected = installer.windows_utf16_units(Path.cwd() / relative)
            actual = installer.windows_utf16_units(
                installer.lexical_absolute_path(relative)
            )

            self.assertEqual(actual, expected)
            installer.assert_windows_portable_install_path(relative, repo_root)


if __name__ == "__main__":
    unittest.main()
