"""Regression tests for conservative Windows installer path preflight."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


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


def contract_with_synthetic_file(
    contract: installer.PayloadContract,
    relative: str,
) -> installer.PayloadContract:
    """Extend a frozen fixture without creating an overlong host path."""
    declared = tuple(sorted((*contract.declared, relative)))
    source_files = tuple(
        sorted(
            (
                *contract.source_files,
                installer.FileSnapshot(relative, (1, 1, 1, 1, 1, 1), 0, "0" * 64),
            ),
            key=lambda snapshot: snapshot.relative,
        )
    )
    manifest_bytes = ("\n".join(declared) + "\n").encode("utf-8")
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    files = {
        snapshot.relative: {"size": snapshot.size, "sha256": snapshot.sha256}
        for snapshot in source_files
    }
    return installer.PayloadContract(
        manifest_bytes,
        declared,
        source_files,
        manifest_sha256,
        installer._contract_sha256(manifest_sha256, declared, files),
    )


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


def existing_install_snapshot(
    relative_file: str,
) -> installer.PathSnapshot:
    parent = str(Path(relative_file).parent).replace("\\", "/")
    entries: dict[str, dict[str, object]] = {
        relative_file: {
            "type": "file",
            "size": 0,
            "sha256": "0" * 64,
            "device": 1,
            "inode": 3,
        }
    }
    if parent != ".":
        entries[parent] = {"type": "dir", "device": 1, "inode": 2}
    return installer.PathSnapshot("dir", entries, (1, 1), "0" * 64)


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

    def test_plan_projects_existing_entries_under_backup_and_quarantine(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = make_payload(root / "payload")
            relative = "runtime-cache/user-note.txt"
            snapshot = existing_install_snapshot(relative)
            labels = {
                label
                for label, _path, _is_directory in installer.planned_windows_install_paths(
                    root / "skills",
                    contract,
                    snapshot,
                )
            }

            self.assertIn(
                f"transaction backup existing install file: {relative}",
                labels,
            )
            self.assertIn(
                f"transaction quarantine existing install file: {relative}",
                labels,
            )
            self.assertFalse(any("stage existing install" in label for label in labels))

    def test_existing_entry_can_fail_only_after_projection_to_backup_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            contract = make_payload(Path(tmp) / "payload")
            skills_dir = short_lexical_base("existing-plan")
            live_prefix = installer.windows_utf16_units(
                skills_dir / installer.SKILL_NAME / "runtime-cache" / "x"
            ) - 1
            backup_prefix = installer.windows_utf16_units(
                skills_dir / installer.BACKUP_NAME / "runtime-cache" / "x"
            ) - 1
            component_length = max(
                1,
                installer.WINDOWS_PORTABLE_FILE_LIMIT + 1 - backup_prefix,
            )
            self.assertLessEqual(
                live_prefix + component_length,
                installer.WINDOWS_PORTABLE_FILE_LIMIT,
            )
            self.assertLessEqual(
                component_length,
                installer.WINDOWS_PORTABLE_COMPONENT_LIMIT,
            )
            relative = "runtime-cache/" + ("n" * component_length)
            snapshot = existing_install_snapshot(relative)

            installer.assert_windows_portable_install_path(skills_dir, contract)
            with self.assertRaises(ValueError) as raised:
                installer.assert_windows_portable_install_path(
                    skills_dir,
                    contract,
                    snapshot,
                )

            message = str(raised.exception)
            self.assertIn("existing install file", message)
            self.assertIn(relative, message)

    def test_main_rechecks_the_contract_loaded_under_the_install_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            preflight_contract = make_payload(root / "preflight")
            locked_contract = make_payload(
                root / "locked",
                ("references/added-while-waiting.md",),
            )
            skills_dir = root / "skills"
            checked: list[
                tuple[installer.PayloadContract, installer.PathSnapshot | None]
            ] = []

            def reject_locked_contract(
                _skills_dir: Path,
                contract: installer.PayloadContract,
                existing: installer.PathSnapshot | None = None,
                *,
                before_installer_writes: bool = True,
            ) -> None:
                checked.append((contract, existing))
                if contract is locked_contract:
                    self.assertFalse(before_installer_writes)
                    raise ValueError("locked contract was rechecked")

            original_argv = sys.argv
            sys.argv = ["install_codex_skill.py", "--dest", str(skills_dir)]
            try:
                with (
                    mock.patch.object(
                        installer,
                        "_load_payload_contract_once",
                        return_value=preflight_contract,
                    ),
                    mock.patch.object(
                        installer,
                        "load_payload_contract",
                        return_value=locked_contract,
                    ),
                    mock.patch.object(
                        installer,
                        "assert_platform_portable_install_path",
                        side_effect=reject_locked_contract,
                    ),
                    mock.patch.object(installer, "safe_print"),
                ):
                    result = installer.main()
            finally:
                sys.argv = original_argv

            self.assertEqual(result, 1)
            self.assertEqual(
                [contract for contract, _existing in checked],
                [preflight_contract, locked_contract],
            )
            self.assertFalse((skills_dir / installer.TRANSACTION_NAME).exists())
            self.assertEqual(list(skills_dir.glob(f"{installer.STAGE_PREFIX}*")), [])

    def test_main_checks_a_bound_existing_tree_before_staging_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            destination = skills_dir / installer.SKILL_NAME
            destination.mkdir(parents=True)
            note = destination / "runtime-cache" / "user-note.txt"
            note.parent.mkdir()
            note.write_text("preserve until path planning passes\n", encoding="utf-8")
            checked: list[installer.PathSnapshot | None] = []

            def stop_after_existing_snapshot(
                _skills_dir: Path,
                _contract: installer.PayloadContract,
                existing: installer.PathSnapshot | None = None,
                *,
                before_installer_writes: bool = True,
            ) -> None:
                checked.append(existing)
                if existing is not None:
                    self.assertFalse(before_installer_writes)
                    raise ValueError("existing install was path-checked")

            original_argv = sys.argv
            sys.argv = [
                "install_codex_skill.py",
                "--dest",
                str(skills_dir),
                "--force",
            ]
            try:
                with (
                    mock.patch.object(
                        installer,
                        "assert_platform_portable_install_path",
                        side_effect=stop_after_existing_snapshot,
                    ),
                    mock.patch.object(installer, "safe_print"),
                ):
                    result = installer.main()
            finally:
                sys.argv = original_argv

            self.assertEqual(result, 1)
            self.assertEqual(len(checked), 2)
            self.assertIsNone(checked[0])
            self.assertIsNotNone(checked[1])
            assert checked[1] is not None
            self.assertIn("runtime-cache/user-note.txt", checked[1].entries)
            self.assertEqual(
                note.read_text(encoding="utf-8"),
                "preserve until path planning passes\n",
            )
            self.assertFalse((skills_dir / installer.TRANSACTION_NAME).exists())
            self.assertEqual(list(skills_dir.glob(f"{installer.STAGE_PREFIX}*")), [])

    def test_main_restores_trusted_backup_before_rejecting_a_new_long_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skills_dir = root / "skills"
            skills_dir.mkdir()
            destination = skills_dir / installer.SKILL_NAME
            destination.mkdir()
            sentinel = destination / "rollback-proof.txt"
            sentinel.write_text("restore me\n", encoding="utf-8")

            recovery_root = root / "recovery-payload"
            recovery_contract = make_payload(recovery_root)
            stage = installer.stage_validated_install(
                recovery_root,
                skills_dir,
                recovery_contract,
                force=True,
            )
            installer._rename_directory(destination, skills_dir / installer.BACKUP_NAME)
            self.assertFalse(destination.exists())
            self.assertTrue(stage.is_dir())
            self.assertTrue((skills_dir / installer.TRANSACTION_NAME).is_file())

            long_relative = "references/" + ("x" * 240) + ".md"
            long_contract = contract_with_synthetic_file(recovery_contract, long_relative)
            with self.assertRaisesRegex(ValueError, "path limit would be exceeded"):
                installer.assert_windows_portable_install_path(skills_dir, long_contract)

            checks: list[bool] = []

            def enforce_windows_policy(
                checked_skills_dir: Path,
                contract: installer.PayloadContract,
                existing: installer.PathSnapshot | None = None,
                *,
                before_installer_writes: bool = True,
            ) -> None:
                checks.append(before_installer_writes)
                installer.assert_windows_portable_install_path(
                    checked_skills_dir,
                    contract,
                    existing,
                    before_installer_writes=before_installer_writes,
                )

            original_argv = sys.argv
            sys.argv = [
                "install_codex_skill.py",
                "--dest",
                str(skills_dir),
                "--force",
            ]
            try:
                with (
                    mock.patch.object(
                        installer,
                        "_load_payload_contract_once",
                        return_value=long_contract,
                    ),
                    mock.patch.object(
                        installer,
                        "assert_platform_portable_install_path",
                        side_effect=enforce_windows_policy,
                    ),
                    mock.patch.object(installer, "safe_print") as safe_print,
                ):
                    result = installer.main()
            finally:
                sys.argv = original_argv

            self.assertEqual(result, 1)
            self.assertEqual(checks, [True, False])
            self.assertTrue(destination.is_dir())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "restore me\n")
            self.assertFalse((skills_dir / installer.BACKUP_NAME).exists())
            self.assertFalse((skills_dir / installer.TRANSACTION_NAME).exists())
            self.assertEqual(list(skills_dir.glob(f"{installer.STAGE_PREFIX}*")), [])
            rendered = "\n".join(str(call.args[0]) for call in safe_print.call_args_list)
            self.assertIn("Recovered the previous", rendered)
            self.assertIn("Windows portable path limit", rendered)
            self.assertIn("transaction stage payload file: references/", rendered)

    def test_long_plan_preserves_an_untrusted_transaction_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skills_dir = root / "skills"
            skills_dir.mkdir()
            transaction = skills_dir / installer.TRANSACTION_NAME
            transaction.write_text('{"broken":', encoding="utf-8")
            base_contract = make_payload(root / "new-plan")
            long_relative = "references/" + ("x" * 240) + ".md"
            long_contract = contract_with_synthetic_file(base_contract, long_relative)

            checks = 0

            def enforce_windows_policy(
                checked_skills_dir: Path,
                contract: installer.PayloadContract,
                existing: installer.PathSnapshot | None = None,
                *,
                before_installer_writes: bool = True,
            ) -> None:
                nonlocal checks
                checks += 1
                installer.assert_windows_portable_install_path(
                    checked_skills_dir,
                    contract,
                    existing,
                    before_installer_writes=before_installer_writes,
                )

            original_argv = sys.argv
            sys.argv = [
                "install_codex_skill.py",
                "--dest",
                str(skills_dir),
                "--force",
            ]
            try:
                with (
                    mock.patch.object(
                        installer,
                        "_load_payload_contract_once",
                        return_value=long_contract,
                    ),
                    mock.patch.object(
                        installer,
                        "assert_platform_portable_install_path",
                        side_effect=enforce_windows_policy,
                    ),
                    mock.patch.object(installer, "safe_print") as safe_print,
                ):
                    result = installer.main()
            finally:
                sys.argv = original_argv

            self.assertEqual(result, 1)
            self.assertEqual(checks, 1, "untrusted recovery must stop before the locked plan check")
            self.assertEqual(transaction.read_text(encoding="utf-8"), '{"broken":')
            self.assertFalse((skills_dir / installer.SKILL_NAME).exists())
            rendered = "\n".join(str(call.args[0]) for call in safe_print.call_args_list)
            self.assertIn("transaction record is untrusted", rendered)

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
