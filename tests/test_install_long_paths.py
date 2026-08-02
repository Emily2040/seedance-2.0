"""Regression tests for conservative Windows installer path preflight."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install_codex_skill.py"

sys.path.insert(0, str(ROOT / "scripts"))
import install_codex_skill as installer  # noqa: E402


def make_payload(
    repo_root: Path,
    extra_files: tuple[str, ...] = (),
) -> installer.PayloadContract:
    declared = (
        "SKILL.md",
        "scripts/install_codex_skill.py",
        installer.PAYLOAD_MANIFEST.as_posix(),
        *extra_files,
    )
    for relative in declared:
        if relative == installer.PAYLOAD_MANIFEST.as_posix():
            continue
        path = repo_root.joinpath(*relative.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"fixture for {relative}\n", encoding="utf-8", newline="\n")
    manifest = repo_root / installer.PAYLOAD_MANIFEST.as_posix()
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        "\n".join(sorted(declared)) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return installer.load_payload_contract(repo_root)


def candidate_slack(
    skills_dir: Path,
    contract: installer.PayloadContract,
) -> list[tuple[int, str, Path, bool]]:
    result: list[tuple[int, str, Path, bool]] = []
    for label, path, is_directory in installer.planned_windows_install_paths(
        skills_dir,
        contract,
    ):
        limit = (
            installer.WINDOWS_PORTABLE_DIRECTORY_LIMIT
            if is_directory
            else installer.WINDOWS_PORTABLE_FILE_LIMIT
        )
        result.append(
            (limit - installer.windows_utf16_units(path), label, path, is_directory)
        )
    return result


def skills_dir_with_minimum_slack(
    base: Path,
    contract: installer.PayloadContract,
    target_slack: int,
) -> Path:
    seed = base / "x"
    current_slack = min(item[0] for item in candidate_slack(seed, contract))
    component_length = 1 + current_slack - target_slack
    if component_length < 1 or component_length > installer.WINDOWS_PORTABLE_COMPONENT_LIMIT:
        raise AssertionError("fixture base cannot reach the requested portable-path slack")
    candidate = base / ("x" * component_length)
    actual_slack = min(item[0] for item in candidate_slack(candidate, contract))
    if actual_slack != target_slack:
        raise AssertionError(
            f"fixture reached slack {actual_slack}, expected {target_slack}"
        )
    return candidate


def short_lexical_base(name: str) -> Path:
    return Path(f"C:/{name}") if os.name == "nt" else Path(f"/{name}")


@unittest.skipUnless(os.name == "nt", "Windows MAX_PATH subprocess regression")
class WindowsLongPathSubprocessTests(unittest.TestCase):
    def test_overlong_plan_is_refused_before_filesystem_writes(self) -> None:
        contract = installer.load_payload_contract(ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = skills_dir_with_minimum_slack(Path(tmp), contract, -20)
            environment = os.environ.copy()
            environment["PYTHONIOENCODING"] = "utf-8:strict"
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            result = subprocess.run(
                [sys.executable, "-B", str(INSTALLER), "--dest", str(skills_dir)],
                cwd=ROOT,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="strict",
                check=False,
                timeout=120,
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertEqual(result.stderr, "")
            self.assertNotIn("Traceback", result.stdout)
            self.assertIn("Refusing to install: Windows portable path limit", result.stdout)
            self.assertIn("UTF-16 code units", result.stdout)
            self.assertIn("Choose a shorter --dest", result.stdout)
            self.assertFalse(skills_dir.exists(), "preflight refusal must write nothing")
            self.assertFalse((skills_dir / installer.SKILL_NAME).exists())


class WindowsPortablePolicyTests(unittest.TestCase):
    def test_utf16_units_count_non_bmp_characters_twice(self) -> None:
        self.assertEqual(installer.windows_utf16_units(Path("A\U0001f680")), 3)

    def test_exact_overall_boundary_is_accepted_and_next_unit_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = make_payload(root / "payload")
            base = Path(tempfile.gettempdir()) / "seedance-portable-boundary"
            boundary = skills_dir_with_minimum_slack(base, contract, 0)
            over_boundary = boundary.with_name(boundary.name + "x")

            installer.assert_windows_portable_install_path(boundary, contract)
            with self.assertRaisesRegex(ValueError, "path limit would be exceeded"):
                installer.assert_windows_portable_install_path(over_boundary, contract)

    def test_transaction_path_can_fail_while_live_destination_is_still_short(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = make_payload(root / "payload")
            base = Path(tempfile.gettempdir()) / "seedance-transaction-boundary"
            skills_dir = skills_dir_with_minimum_slack(base, contract, -1)
            live_destination = skills_dir / installer.SKILL_NAME

            self.assertLessEqual(
                installer.windows_utf16_units(live_destination),
                installer.WINDOWS_PORTABLE_DIRECTORY_LIMIT,
            )
            with self.assertRaises(ValueError) as raised:
                installer.assert_windows_portable_install_path(skills_dir, contract)
            self.assertIn("transaction", str(raised.exception))
            self.assertIn("No installer files were written", str(raised.exception))

    def test_declared_file_boundary_uses_transaction_root_and_file_limit(self) -> None:
        relative = "references/" + ("f" * 150) + ".md"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = make_payload(root / "payload", (relative,))
            base = short_lexical_base("f")
            boundary = skills_dir_with_minimum_slack(base, contract, 0)
            over_boundary = boundary.with_name(boundary.name + "x")

            installer.assert_windows_portable_install_path(boundary, contract)
            with self.assertRaises(ValueError) as raised:
                installer.assert_windows_portable_install_path(over_boundary, contract)
            message = str(raised.exception)
            self.assertIn("Predicted file path uses 260 UTF-16 code units", message)
            self.assertIn("safe limit is 259", message)
            self.assertIn(f"payload file: {relative}", message)

    def test_destination_component_over_255_units_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = make_payload(root / "payload")
            skills_dir = Path(tempfile.gettempdir()) / ("x" * 256)

            with self.assertRaises(ValueError) as raised:
                installer.assert_windows_portable_install_path(skills_dir, contract)
            message = str(raised.exception)
            self.assertIn("component limit would be exceeded", message)
            self.assertIn("256 UTF-16 code units", message)
            self.assertIn("safe limit is 255", message)

    def test_undeclared_source_tree_does_not_reduce_supported_length(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_root = root / "payload"
            contract = make_payload(repo_root)
            undeclared = repo_root / "tests" / ("x" * 100)
            undeclared.parent.mkdir()
            undeclared.write_text("not installed\n", encoding="utf-8")
            base = Path(tempfile.gettempdir()) / "seedance-manifest-only-boundary"
            boundary = skills_dir_with_minimum_slack(base, contract, 0)

            installer.assert_windows_portable_install_path(boundary, contract)
            labels = {
                label
                for label, _path, _is_directory in installer.planned_windows_install_paths(
                    boundary,
                    contract,
                )
            }
            self.assertFalse(any("tests/" in label for label in labels))

    def test_plan_includes_every_reserved_transaction_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = make_payload(root / "payload")
            labels = {
                label
                for label, _path, _is_directory in installer.planned_windows_install_paths(
                    root / "skills",
                    contract,
                )
            }

            for expected in (
                "install lock",
                "transaction record",
                "completed transaction record",
                "live install root",
                "transaction stage root",
                "transaction quarantine root",
                "transaction backup root",
            ):
                self.assertIn(expected, labels)

    def test_relative_skills_directory_is_measured_lexically_from_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            contract = make_payload(Path(tmp) / "payload")
            relative = Path("short-skills")
            candidates = list(installer.planned_windows_install_paths(relative, contract))
            skills_candidate = next(
                path
                for label, path, _kind in candidates
                if label == "skills directory"
            )

            self.assertEqual(skills_candidate, installer._absolute_lexical(relative))
            installer.assert_windows_portable_install_path(relative, contract)


if __name__ == "__main__":
    unittest.main()
