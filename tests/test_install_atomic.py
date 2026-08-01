"""Regression tests for transactional, shared-destination installs."""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install_codex_skill.py"
SKILL_NAME = "seedance-20"

sys.path.insert(0, str(ROOT / "scripts"))
import install_codex_skill as installer  # noqa: E402


CONCURRENT_INSTALL = textwrap.dedent(
    """
    import os
    import sys
    import time
    from pathlib import Path

    scripts_dir = Path(sys.argv[1])
    skills_dir = Path(sys.argv[2])
    barrier = Path(sys.argv[3])
    workers = int(sys.argv[4])
    force = sys.argv[5] == "force"

    sys.path.insert(0, str(scripts_dir))
    import install_codex_skill as installer

    if not force:
        destination = skills_dir / installer.SKILL_NAME
        original_path_exists = installer._path_exists
        first_destination_probe = True

        def observed_absent_at_start(path):
            global first_destination_probe
            if first_destination_probe and path == destination:
                first_destination_probe = False
                return False
            return original_path_exists(path)

        installer._path_exists = observed_absent_at_start

    (barrier / f"{os.getpid()}.ready").touch()
    deadline = time.monotonic() + 30
    while len(list(barrier.glob("*.ready"))) < workers:
        if time.monotonic() >= deadline:
            raise SystemExit("timed out waiting for install barrier")
        time.sleep(0.01)

    sys.argv = ["install_codex_skill.py", "--dest", str(skills_dir)]
    if force:
        sys.argv.append("--force")
    raise SystemExit(installer.main())
    """
)


PAUSE_DURING_COPY = textwrap.dedent(
    """
    import sys
    import time
    from pathlib import Path

    scripts_dir = Path(sys.argv[1])
    skills_dir = Path(sys.argv[2])
    ready = Path(sys.argv[3])
    force = sys.argv[4] == "force"

    sys.path.insert(0, str(scripts_dir))
    import install_codex_skill as installer

    original_copytree = installer.shutil.copytree
    copied = 0

    def paused_copy(source, destination, *args, **kwargs):
        global copied
        result = installer.shutil.copy2(source, destination, *args, **kwargs)
        copied += 1
        if copied == 2:
            ready.touch()
            time.sleep(120)
        return result

    def controlled_copytree(source, destination, *args, **kwargs):
        kwargs["copy_function"] = paused_copy
        return original_copytree(source, destination, *args, **kwargs)

    installer.shutil.copytree = controlled_copytree
    sys.argv = ["install_codex_skill.py", "--dest", str(skills_dir)]
    if force:
        sys.argv.append("--force")
    raise SystemExit(installer.main())
    """
)


PAUSE_DURING_PROMOTION = textwrap.dedent(
    """
    import sys
    import time
    from pathlib import Path

    scripts_dir = Path(sys.argv[1])
    skills_dir = Path(sys.argv[2])
    ready = Path(sys.argv[3])

    sys.path.insert(0, str(scripts_dir))
    import install_codex_skill as installer

    original_rename = installer._rename_directory

    def controlled_rename(source, destination):
        if source.name.startswith(installer.STAGE_PREFIX) and destination.name == installer.SKILL_NAME:
            ready.touch()
            time.sleep(120)
        return original_rename(source, destination)

    installer._rename_directory = controlled_rename
    sys.argv = ["install_codex_skill.py", "--dest", str(skills_dir), "--force"]
    raise SystemExit(installer.main())
    """
)


class AtomicInstallRegressionTests(unittest.TestCase):
    def run_installer(self, skills_dir: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(INSTALLER), "--dest", str(skills_dir), *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )

    def test_no_force_repairs_a_partial_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            destination = skills_dir / SKILL_NAME
            destination.mkdir(parents=True)
            shutil.copy2(ROOT / "SKILL.md", destination / "SKILL.md")

            result = self.run_installer(skills_dir)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertIn("Detected an incomplete", result.stdout)
            self.assertTrue((destination / "references" / "quick-ref.md").is_file())
            self.assertTrue((destination / "skills" / "seedance-prompt" / "SKILL.md").is_file())
            self.assert_completed(destination)

    def test_no_force_refuses_a_partial_install_with_a_truncated_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            destination = skills_dir / SKILL_NAME
            destination.mkdir(parents=True)
            (destination / "SKILL.md").write_bytes(b"truncated during copy")

            result = self.run_installer(skills_dir)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("Refusing to replace the existing path", result.stdout)
            self.assertEqual(
                (destination / "SKILL.md").read_bytes(), b"truncated during copy"
            )

    def test_empty_unmarked_directory_is_never_auto_repaired(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            destination = skills_dir / SKILL_NAME
            destination.mkdir(parents=True)

            result = self.run_installer(skills_dir)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("empty unmarked directories are never auto-repaired", result.stdout)
            self.assertEqual(list(destination.iterdir()), [])

    def test_later_no_force_call_still_reports_already_installed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            first = self.run_installer(skills_dir)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)

            later = self.run_installer(skills_dir)

            self.assertEqual(later.returncode, 1, later.stdout + later.stderr)
            self.assertIn(f"{SKILL_NAME} is already installed at", later.stdout)
            self.assertIn("Run again with --force to replace it.", later.stdout)
            self.assert_completed(skills_dir / SKILL_NAME)

    def test_complete_unmarked_legacy_install_with_extra_files_is_not_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            first = self.run_installer(skills_dir)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            destination = skills_dir / SKILL_NAME
            (destination / installer.COMPLETION_MARKER).unlink()
            extra = destination / "local-note.txt"
            extra.write_text("keep me\n", encoding="utf-8")

            later = self.run_installer(skills_dir)

            self.assertEqual(later.returncode, 1, later.stdout + later.stderr)
            self.assertIn(f"{SKILL_NAME} is already installed at", later.stdout)
            self.assertEqual(extra.read_text(encoding="utf-8"), "keep me\n")
            self.assertFalse((destination / installer.COMPLETION_MARKER).exists())

    def test_ambiguous_unmarked_install_requires_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            first = self.run_installer(skills_dir)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            destination = skills_dir / SKILL_NAME
            (destination / installer.COMPLETION_MARKER).unlink()
            skill_file = destination / "SKILL.md"
            skill_file.write_text("locally customized\n", encoding="utf-8")

            later = self.run_installer(skills_dir)

            self.assertEqual(later.returncode, 1, later.stdout + later.stderr)
            self.assertIn("Refusing to replace the existing path", later.stdout)
            self.assertIn("Run again with --force only", later.stdout)
            self.assertEqual(skill_file.read_text(encoding="utf-8"), "locally customized\n")

    def test_concurrent_force_writers_are_serialized(self) -> None:
        workers = 8
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skills_dir = root / "skills"
            barrier = root / "barrier"
            barrier.mkdir()

            initial = self.run_installer(skills_dir)
            self.assertEqual(initial.returncode, 0, initial.stdout + initial.stderr)

            commands = [
                sys.executable,
                "-c",
                CONCURRENT_INSTALL,
                str(ROOT / "scripts"),
                str(skills_dir),
                str(barrier),
                str(workers),
                "force",
            ]
            processes = [
                subprocess.Popen(
                    commands,
                    cwd=ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                for _ in range(workers)
            ]
            results = [process.communicate(timeout=120) for process in processes]

            failures = [
                (process.returncode, stdout, stderr)
                for process, (stdout, stderr) in zip(processes, results)
                if process.returncode != 0 or "Traceback" in stderr
            ]
            self.assertEqual(failures, [])
            destination = skills_dir / SKILL_NAME
            self.assertTrue((destination / "SKILL.md").is_file())
            self.assertTrue((destination / "references" / "quick-ref.md").is_file())

    def start_controlled_installer(
        self,
        code: str,
        skills_dir: Path,
        ready: Path,
        mode: str | None = None,
    ) -> subprocess.Popen[str]:
        command = [
            sys.executable,
            "-c",
            code,
            str(ROOT / "scripts"),
            str(skills_dir),
            str(ready),
        ]
        if mode is not None:
            command.append(mode)
        return subprocess.Popen(
            command,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def wait_until_ready(self, process: subprocess.Popen[str], ready: Path) -> None:
        deadline = time.monotonic() + 30
        while not ready.exists():
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                self.fail(f"controlled installer exited before pause: {stdout}{stderr}")
            if time.monotonic() >= deadline:
                process.kill()
                stdout, stderr = process.communicate()
                self.fail(f"controlled installer did not reach pause: {stdout}{stderr}")
            time.sleep(0.02)

    def terminate_at_pause(self, process: subprocess.Popen[str], ready: Path) -> None:
        self.wait_until_ready(process, ready)
        process.terminate()
        process.communicate(timeout=30)
        self.assertIsNotNone(process.returncode)

    def assert_completed(self, destination: Path) -> None:
        valid, reason = installer.validate_completed_install(destination)
        self.assertTrue(valid, reason)

    def call_main(self, skills_dir: Path, *args: str) -> tuple[int, str]:
        original_argv = sys.argv
        sys.argv = ["install_codex_skill.py", "--dest", str(skills_dir), *args]
        output = io.StringIO()
        try:
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                result = installer.main()
        finally:
            sys.argv = original_argv
        return result, output.getvalue()

    def test_valid_live_plus_untrusted_reserved_backup_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            initial = self.run_installer(skills_dir)
            self.assertEqual(initial.returncode, 0, initial.stdout + initial.stderr)
            backup = skills_dir / installer.BACKUP_NAME
            backup.mkdir()
            sentinel = backup / "user-data.txt"
            sentinel.write_text("never delete me\n", encoding="utf-8")

            retry = self.run_installer(skills_dir, "--force")

            self.assertEqual(retry.returncode, 1, retry.stdout + retry.stderr)
            self.assertIn("untrusted reserved-name backup", retry.stderr)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "never delete me\n")
            self.assert_completed(skills_dir / SKILL_NAME)

    def test_missing_live_plus_untrusted_reserved_backup_is_not_promoted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            backup = skills_dir / installer.BACKUP_NAME
            backup.mkdir(parents=True)
            sentinel = backup / "user-data.txt"
            sentinel.write_text("not an install\n", encoding="utf-8")

            retry = self.run_installer(skills_dir, "--force")

            self.assertEqual(retry.returncode, 1, retry.stdout + retry.stderr)
            self.assertIn("untrusted reserved-name backup", retry.stderr)
            self.assertFalse((skills_dir / SKILL_NAME).exists())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "not an install\n")

    def test_cleanup_stages_refuses_untrusted_reserved_prefix_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            stage = skills_dir / f"{installer.STAGE_PREFIX}user-data"
            stage.mkdir(parents=True)
            sentinel = stage / "sentinel.txt"
            sentinel.write_text("preserve\n", encoding="utf-8")
            (stage / installer.PROVENANCE_MARKER).write_text(
                '{"looks":"owned"}\n', encoding="utf-8"
            )

            with self.assertRaisesRegex(RuntimeError, "untrusted reserved-prefix stage"):
                installer._cleanup_stages(skills_dir)

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve\n")

    def test_untrusted_reserved_quarantine_is_preserved_even_with_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            quarantine = skills_dir / f"{installer.QUARANTINE_PREFIX}user-data"
            quarantine.mkdir(parents=True)
            sentinel = quarantine / "sentinel.txt"
            sentinel.write_text("preserve\n", encoding="utf-8")

            result = self.run_installer(skills_dir, "--force")

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("untrusted reserved-prefix quarantine", result.stderr)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve\n")
            self.assertFalse((skills_dir / SKILL_NAME).exists())

    def test_malformed_transaction_is_preserved_and_creates_no_live_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            transaction = skills_dir / installer.TRANSACTION_NAME
            transaction.write_text('{"broken":', encoding="utf-8")

            result = self.run_installer(skills_dir, "--force")

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("transaction record is untrusted", result.stderr)
            self.assertEqual(transaction.read_text(encoding="utf-8"), '{"broken":')
            self.assertFalse((skills_dir / SKILL_NAME).exists())

    def test_hostile_duplicate_marker_key_has_bounded_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            destination = skills_dir / SKILL_NAME
            destination.mkdir(parents=True)
            hostile_key = "x" * 5000
            marker = destination / installer.COMPLETION_MARKER
            marker.write_text(
                "{" + json.dumps(hostile_key) + ":1," + json.dumps(hostile_key) + ":2}",
                encoding="utf-8",
            )

            result = self.run_installer(skills_dir)
            combined = result.stdout + result.stderr

            self.assertEqual(result.returncode, 1, combined)
            self.assertIn("duplicate key", combined)
            self.assertNotIn("Traceback", combined)
            self.assertLess(len(combined), 1200)
            self.assertTrue(marker.is_file())

    def test_record_reader_rejects_same_length_atomic_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = root / "record.json"
            replacement = root / "replacement.json"
            record.write_bytes(b'{"a":1}')
            replacement.write_bytes(b'{"b":2}')
            original_close = installer.os.close
            swapped = False

            def close_then_swap(descriptor: int) -> None:
                nonlocal swapped
                original_close(descriptor)
                if not swapped:
                    swapped = True
                    os.replace(replacement, record)

            with mock.patch.object(installer.os, "close", close_then_swap):
                with self.assertRaisesRegex(ValueError, "record changed while it was being read"):
                    installer._read_json_record(record)

            self.assertEqual(record.read_bytes(), b'{"b":2}')

    def test_record_reader_rejects_oversize_before_opening(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            record = Path(tmp) / "oversized.json"
            with record.open("wb") as handle:
                handle.truncate(installer.MAX_RECORD_BYTES + 1)

            with mock.patch.object(
                installer.os,
                "open",
                side_effect=AssertionError("oversized record must not be opened"),
            ):
                with self.assertRaisesRegex(ValueError, "outside the safe limit"):
                    installer._read_json_record(record)

    def test_manifest_rejects_windows_ads_or_drive_like_path(self) -> None:
        hostile = {
            "SKILL.md:stream": {
                "size": 1,
                "sha256": "0" * 64,
            }
        }

        with self.assertRaisesRegex(ValueError, "unsafe path"):
            installer._validate_payload_manifest(hostile)

    def test_late_stage_extra_is_quarantined_and_never_becomes_live(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            initial = self.run_installer(skills_dir)
            self.assertEqual(initial.returncode, 0, initial.stdout + initial.stderr)
            destination = skills_dir / SKILL_NAME
            sentinel = destination / "old-live.txt"
            sentinel.write_text("old live\n", encoding="utf-8")
            original_rename = installer._rename_directory

            def inject_before_stage_promotion(source: Path, target: Path) -> None:
                if source.name.startswith(installer.STAGE_PREFIX) and target == destination:
                    (source / "late-user-data.txt").write_text("preserve me\n", encoding="utf-8")
                original_rename(source, target)

            with mock.patch.object(installer, "_rename_directory", inject_before_stage_promotion):
                result, output = self.call_main(skills_dir, "--force")

            self.assertEqual(result, 1, output)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "old live\n")
            quarantines = list(skills_dir.glob(f"{installer.QUARANTINE_PREFIX}*"))
            self.assertEqual(len(quarantines), 1)
            self.assertEqual(
                (quarantines[0] / "late-user-data.txt").read_text(encoding="utf-8"),
                "preserve me\n",
            )
            self.assertFalse((destination / "late-user-data.txt").exists())
            self.assertFalse((skills_dir / installer.BACKUP_NAME).exists())

    def test_late_backup_extra_is_preserved_after_atomic_quarantine(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            initial = self.run_installer(skills_dir)
            self.assertEqual(initial.returncode, 0, initial.stdout + initial.stderr)
            destination = skills_dir / SKILL_NAME
            old_sentinel = destination / "old-live.txt"
            old_sentinel.write_text("old live\n", encoding="utf-8")
            original_rename = installer._rename_directory

            def inject_before_backup_quarantine(source: Path, target: Path) -> None:
                if source == skills_dir / installer.BACKUP_NAME and target.name.startswith(
                    installer.QUARANTINE_PREFIX
                ):
                    (source / "late-user-data.txt").write_text("preserve me\n", encoding="utf-8")
                original_rename(source, target)

            with mock.patch.object(installer, "_rename_directory", inject_before_backup_quarantine):
                result, output = self.call_main(skills_dir, "--force")

            self.assertEqual(result, 1, output)
            self.assert_completed(destination)
            self.assertFalse((destination / "old-live.txt").exists())
            quarantines = list(skills_dir.glob(f"{installer.QUARANTINE_PREFIX}*"))
            self.assertEqual(len(quarantines), 1)
            self.assertEqual(
                (quarantines[0] / "late-user-data.txt").read_text(encoding="utf-8"),
                "preserve me\n",
            )
            self.assertEqual(
                (quarantines[0] / "old-live.txt").read_text(encoding="utf-8"),
                "old live\n",
            )

    def test_kill_window_before_quarantine_marker_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            initial = self.run_installer(skills_dir)
            self.assertEqual(initial.returncode, 0, initial.stdout + initial.stderr)
            destination = skills_dir / SKILL_NAME
            old_sentinel = destination / "old-live.txt"
            old_sentinel.write_text("old live\n", encoding="utf-8")
            original_write = installer._write_json_exclusive

            def fail_quarantine_marker(path: Path, record: object) -> bytes:
                if path.name == installer.QUARANTINE_MARKER:
                    raise OSError("injected kill before quarantine marker")
                return original_write(path, record)  # type: ignore[arg-type]

            with mock.patch.object(
                installer, "_write_json_exclusive", fail_quarantine_marker
            ):
                result, output = self.call_main(skills_dir, "--force")

            self.assertEqual(result, 1, output)
            self.assert_completed(destination)
            quarantine = next(skills_dir.glob(f"{installer.QUARANTINE_PREFIX}*"))
            self.assertEqual(
                (quarantine / "old-live.txt").read_text(encoding="utf-8"),
                "old live\n",
            )
            self.assertFalse((quarantine / installer.QUARANTINE_MARKER).exists())
            self.assertTrue((skills_dir / installer.TRANSACTION_NAME).is_file())

            retry = self.run_installer(skills_dir, "--force")
            self.assertEqual(retry.returncode, 1, retry.stdout + retry.stderr)
            self.assertIn("quarantine", retry.stderr.lower())
            self.assertEqual(
                (quarantine / "old-live.txt").read_text(encoding="utf-8"),
                "old live\n",
            )

    def test_stage_path_swap_is_quarantined_without_recursive_deletion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skills_dir = root / "skills"
            skills_dir.mkdir()
            ready = root / "copy-paused"
            process = self.start_controlled_installer(
                PAUSE_DURING_COPY, skills_dir, ready, "fresh"
            )
            self.terminate_at_pause(process, ready)
            transaction, _ = installer._load_transaction(skills_dir)
            stage = skills_dir / str(transaction["stage_name"])
            quarantine = skills_dir / str(transaction["quarantine_name"])
            stashed = skills_dir / "owned-stage-stashed-by-test"
            original_rename = installer._rename_directory

            def swap_at_quarantine(source: Path, target: Path) -> None:
                if source == stage and target == quarantine:
                    original_rename(source, stashed)
                    source.mkdir()
                    (source / "user-data.txt").write_text("preserve\n", encoding="utf-8")
                original_rename(source, target)

            with mock.patch.object(installer, "_rename_directory", swap_at_quarantine):
                with self.assertRaisesRegex(RuntimeError, "changed after transaction ownership"):
                    installer.recover_interrupted_transaction(
                        skills_dir, skills_dir / SKILL_NAME
                    )

            self.assertEqual(
                (quarantine / "user-data.txt").read_text(encoding="utf-8"),
                "preserve\n",
            )
            self.assertTrue((skills_dir / installer.TRANSACTION_NAME).is_file())

    def test_transaction_record_swap_to_directory_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            transaction = skills_dir / installer.TRANSACTION_NAME
            stashed = skills_dir / "original-transaction-stashed-by-test"
            original_rename = installer._rename_directory
            swapped = False

            def swap_record_before_quarantine(source: Path, target: Path) -> None:
                nonlocal swapped
                if source == transaction and not swapped:
                    swapped = True
                    original_rename(source, stashed)
                    source.mkdir()
                    (source / "user-data.txt").write_text("preserve\n", encoding="utf-8")
                original_rename(source, target)

            with mock.patch.object(installer, "_rename_directory", swap_record_before_quarantine):
                result, output = self.call_main(skills_dir)

            self.assertEqual(result, 1, output)
            done = list(skills_dir.glob(f"{installer.TRANSACTION_DONE_PREFIX}*"))
            self.assertEqual(len(done), 1)
            self.assertEqual(
                (done[0] / "user-data.txt").read_text(encoding="utf-8"), "preserve\n"
            )
            self.assert_completed(skills_dir / SKILL_NAME)

    def test_reparse_stage_is_refused_and_preserved_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skills_dir = root / "skills"
            outside = root / "outside"
            outside.mkdir(parents=True)
            sentinel = outside / "sentinel.txt"
            sentinel.write_text("preserve\n", encoding="utf-8")
            stage = skills_dir / f"{installer.STAGE_PREFIX}junction"
            skills_dir.mkdir()
            if os.name == "nt":
                junction = subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(stage), str(outside)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if junction.returncode != 0:
                    self.skipTest(f"directory junctions unavailable: {junction.stderr}")
            else:
                try:
                    os.symlink(outside, stage, target_is_directory=True)
                except (OSError, NotImplementedError) as exc:
                    self.skipTest(f"directory symlinks unavailable: {exc}")

            result = self.run_installer(skills_dir, "--force")

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve\n")
            self.assertTrue(os.path.lexists(stage))

    def test_concurrent_fresh_writers_finish_cleanly(self) -> None:
        workers = 6
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skills_dir = root / "skills"
            skills_dir.mkdir()
            barrier = root / "barrier"
            barrier.mkdir()
            command = [
                sys.executable,
                "-c",
                CONCURRENT_INSTALL,
                str(ROOT / "scripts"),
                str(skills_dir),
                str(barrier),
                str(workers),
                "fresh",
            ]
            processes = [
                subprocess.Popen(
                    command,
                    cwd=ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                for _ in range(workers)
            ]
            results = [process.communicate(timeout=120) for process in processes]

            self.assertEqual(sum(process.returncode == 0 for process in processes), workers)
            for process, (stdout, stderr) in zip(processes, results):
                self.assertEqual(process.returncode, 0, stdout + stderr)
                self.assertNotIn("Traceback", stderr)
                self.assertTrue(
                    "Installed seedance-20" in stdout or "another installer finished" in stdout,
                    stdout,
                )
            self.assert_completed(skills_dir / SKILL_NAME)

    def test_interrupted_fresh_stage_leaves_no_partial_live_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skills_dir = root / "skills"
            skills_dir.mkdir()
            ready = root / "copy-paused"
            process = self.start_controlled_installer(
                PAUSE_DURING_COPY, skills_dir, ready, "fresh"
            )
            self.terminate_at_pause(process, ready)

            destination = skills_dir / SKILL_NAME
            self.assertFalse(destination.exists())
            self.assertTrue(list(skills_dir.glob(f"{installer.STAGE_PREFIX}*")))

            retry = self.run_installer(skills_dir)
            self.assertEqual(retry.returncode, 0, retry.stdout + retry.stderr)
            self.assert_completed(destination)
            self.assertEqual(list(skills_dir.glob(f"{installer.STAGE_PREFIX}*")), [])

    def test_interrupted_force_stage_preserves_the_live_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skills_dir = root / "skills"
            initial = self.run_installer(skills_dir)
            self.assertEqual(initial.returncode, 0, initial.stdout + initial.stderr)
            destination = skills_dir / SKILL_NAME
            sentinel = destination / "local-sentinel.txt"
            sentinel.write_text("old install remains live\n", encoding="utf-8")
            ready = root / "copy-paused"
            process = self.start_controlled_installer(
                PAUSE_DURING_COPY, skills_dir, ready, "force"
            )
            self.terminate_at_pause(process, ready)

            self.assert_completed(destination)
            self.assertTrue(sentinel.is_file())
            retry = self.run_installer(skills_dir)
            self.assertEqual(retry.returncode, 1, retry.stdout + retry.stderr)
            self.assertIn("already installed", retry.stdout)
            self.assert_completed(destination)
            self.assertTrue(sentinel.is_file())
            self.assertEqual(list(skills_dir.glob(f"{installer.STAGE_PREFIX}*")), [])

    def test_kill_in_promotion_gap_restores_previous_install_on_retry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skills_dir = root / "skills"
            initial = self.run_installer(skills_dir)
            self.assertEqual(initial.returncode, 0, initial.stdout + initial.stderr)
            destination = skills_dir / SKILL_NAME
            sentinel = destination / "local-sentinel.txt"
            sentinel.write_text("rollback proof\n", encoding="utf-8")
            ready = root / "promotion-paused"
            process = self.start_controlled_installer(
                PAUSE_DURING_PROMOTION, skills_dir, ready
            )
            self.terminate_at_pause(process, ready)

            self.assertFalse(destination.exists())
            self.assertTrue((skills_dir / installer.BACKUP_NAME).exists())

            retry = self.run_installer(skills_dir)
            self.assertEqual(retry.returncode, 0, retry.stdout + retry.stderr)
            self.assertIn("Recovered the previous", retry.stdout)
            self.assertIn("another installer finished or recovered it", retry.stdout)
            self.assert_completed(destination)
            self.assertTrue(sentinel.is_file())
            self.assertFalse((skills_dir / installer.BACKUP_NAME).exists())
            self.assertEqual(list(skills_dir.glob(f"{installer.STAGE_PREFIX}*")), [])

    def test_promotion_error_rolls_back_before_returning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            initial = self.run_installer(skills_dir)
            self.assertEqual(initial.returncode, 0, initial.stdout + initial.stderr)
            destination = skills_dir / SKILL_NAME
            sentinel = destination / "local-sentinel.txt"
            sentinel.write_text("rollback proof\n", encoding="utf-8")
            original_rename = installer._rename_directory

            def fail_stage_promotion(source: Path, target: Path) -> None:
                if source.name.startswith(installer.STAGE_PREFIX) and target == destination:
                    raise OSError("injected promotion failure")
                original_rename(source, target)

            original_argv = sys.argv
            sys.argv = ["install_codex_skill.py", "--dest", str(skills_dir), "--force"]
            output = io.StringIO()
            try:
                with mock.patch.object(installer, "_rename_directory", fail_stage_promotion):
                    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                        result = installer.main()
            finally:
                sys.argv = original_argv

            self.assertEqual(result, 1)
            self.assertIn("injected promotion failure", output.getvalue())
            self.assert_completed(destination)
            self.assertTrue(sentinel.is_file())
            self.assertFalse((skills_dir / installer.BACKUP_NAME).exists())
            self.assertEqual(list(skills_dir.glob(f"{installer.STAGE_PREFIX}*")), [])

    def test_invalid_managed_install_is_repaired_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            initial = self.run_installer(skills_dir)
            self.assertEqual(initial.returncode, 0, initial.stdout + initial.stderr)
            destination = skills_dir / SKILL_NAME
            (destination / "references" / "quick-ref.md").unlink()

            retry = self.run_installer(skills_dir)

            self.assertEqual(retry.returncode, 0, retry.stdout + retry.stderr)
            self.assertIn("Detected an incomplete", retry.stdout)
            self.assert_completed(destination)


if __name__ == "__main__":
    unittest.main()
