"""Regression tests for transactional, shared-destination installs."""

from __future__ import annotations

import contextlib
import errno
import hashlib
import io
import json
import os
import shutil
import stat
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

    original_copy = installer._copy_payload_file_atomic
    copied = 0

    def paused_copy(source, destination, *args, **kwargs):
        global copied
        result = original_copy(source, destination, *args, **kwargs)
        copied += 1
        if copied == 2:
            ready.touch()
            time.sleep(120)
        return result

    installer._copy_payload_file_atomic = paused_copy
    sys.argv = ["install_codex_skill.py", "--dest", str(skills_dir)]
    if force:
        sys.argv.append("--force")
    raise SystemExit(installer.main())
    """
)


PAUSE_DURING_ATOMIC_WRITE = textwrap.dedent(
    """
    import os
    import sys
    import time
    from pathlib import Path

    scripts_dir = Path(sys.argv[1])
    skills_dir = Path(sys.argv[2])
    ready = Path(sys.argv[3])

    sys.path.insert(0, str(scripts_dir))
    import install_codex_skill as installer

    original_write = installer._write_payload_chunk
    paused = False

    def pause_after_partial_write(descriptor, chunk):
        global paused
        if not paused:
            paused = True
            prefix = chunk[:max(1, len(chunk) // 2)]
            written = os.write(descriptor, prefix)
            if written != len(prefix):
                raise RuntimeError("controlled partial write was itself partial")
            ready.touch()
            time.sleep(120)
        return original_write(descriptor, chunk)

    installer._write_payload_chunk = pause_after_partial_write
    sys.argv = ["install_codex_skill.py", "--dest", str(skills_dir)]
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

    def communicate_process_group(
        self, processes: list[subprocess.Popen[str]]
    ) -> list[tuple[str, str]]:
        """Collect every worker by one deadline and never leak timed-out children."""
        deadline = time.monotonic() + installer.LOCK_TIMEOUT_SECONDS + 30
        results: list[tuple[str, str]] = []
        try:
            for process in processes:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(process.args, 0)
                results.append(process.communicate(timeout=remaining))
            return results
        finally:
            running = [process for process in processes if process.poll() is None]
            for process in running:
                process.terminate()
            for process in running:
                try:
                    process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
            for process in processes:
                if process.poll() is None:
                    process.kill()
                # Close every pipe even for workers that were not reached by
                # the main collection loop. communicate() is safe to repeat.
                process.communicate()

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

    def test_nonforce_policy_snapshot_cannot_authorize_a_replacement_tree(self) -> None:
        for initial_state in ("missing", "incomplete"):
            with self.subTest(initial_state=initial_state), tempfile.TemporaryDirectory() as tmp:
                skills_dir = Path(tmp) / "skills"
                skills_dir.mkdir()
                destination = skills_dir / SKILL_NAME
                stashed = skills_dir / "classified-destination-stashed"
                if initial_state == "incomplete":
                    destination.mkdir()
                    shutil.copy2(ROOT / "SKILL.md", destination / "SKILL.md")
                original_classify = installer._classify_existing_install_bound
                swapped = False
                classify_calls = 0

                def classify_then_swap(path: Path, manifest):
                    nonlocal classify_calls, swapped
                    classification = original_classify(path, manifest)
                    self.assertEqual(classification.state, initial_state)
                    classify_calls += 1
                    if classify_calls == 2:
                        if path.exists():
                            path.rename(stashed)
                        path.mkdir()
                        (path / "user-data.txt").write_text(
                            "preserve\n", encoding="utf-8"
                        )
                        swapped = True
                    return classification

                with mock.patch.object(
                    installer,
                    "_classify_existing_install_bound",
                    classify_then_swap,
                ):
                    result, output = self.call_main(skills_dir)

                self.assertTrue(swapped)
                self.assertEqual(classify_calls, 2)
                self.assertEqual(result, 1, output)
                self.assertIn("destination changed", output)
                self.assertEqual(
                    (destination / "user-data.txt").read_text(encoding="utf-8"),
                    "preserve\n",
                )
                if initial_state == "incomplete":
                    self.assertEqual(
                        (stashed / "SKILL.md").read_bytes(),
                        (ROOT / "SKILL.md").read_bytes(),
                    )
                self.assertFalse(
                    (skills_dir / installer.TRANSACTION_NAME).exists()
                )

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

    def test_late_different_payload_winner_is_not_accepted_as_our_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            destination = skills_dir / SKILL_NAME
            alternate_source = Path(tmp) / "alternate-source"
            shutil.copytree(ROOT, alternate_source)
            (alternate_source / "SKILL.md").write_text(
                "different source revision\n", encoding="utf-8"
            )
            alternate_contract = installer.load_payload_contract(alternate_source)

            @contextlib.contextmanager
            def publish_different_payload(_skills_dir: Path):
                destination.mkdir()
                for source_file in alternate_contract.source_files:
                    relative = Path(*source_file.relative.split("/"))
                    target = destination / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(alternate_source / relative, target)
                installer.write_completion_marker(destination, alternate_contract)
                yield

            with mock.patch.object(
                installer, "exclusive_install_lock", publish_different_payload
            ):
                result, output = self.call_main(skills_dir)

            self.assertEqual(result, 1, output)
            self.assertIn("different source payload", output)
            self.assertNotIn("another installer finished", output)
            self.assertEqual(
                (destination / "SKILL.md").read_text(encoding="utf-8"),
                "different source revision\n",
            )
            self.assert_completed(destination)

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
            results = self.communicate_process_group(processes)

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

    def normalize_portable_stage_modes(self, stage: Path) -> None:
        if os.name == "nt":
            return
        directories = [stage, *(path for path in stage.rglob("*") if path.is_dir())]
        files = [path for path in stage.rglob("*") if path.is_file()]
        for directory in directories:
            directory.chmod(installer.PORTABLE_DIRECTORY_MODE)
        for file_path in files:
            file_path.chmod(installer.PORTABLE_FILE_MODE)

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

    def make_atomic_copy_fixture(
        self, root: Path, *, transaction_digit: str = "a"
    ) -> tuple[Path, Path, Path, dict[str, object], bytes, Path, Path]:
        repo_root = root / "payload-source"
        source = repo_root / "nested" / "payload.bin"
        source.parent.mkdir(parents=True)
        source.write_bytes((b"bounded atomic payload\n" * 1024) + b"end")
        relative = source.relative_to(repo_root).as_posix()
        source_metadata = installer._regular_file_metadata(source)
        manifest = {
            relative: {
                "size": source_metadata["size"],
                "sha256": source_metadata["sha256"],
            }
        }
        skills_dir = root / "skills"
        skills_dir.mkdir()
        transaction_id = transaction_digit * 32
        transaction = installer._transaction_record(
            f"{installer.STAGE_PREFIX}123-{transaction_id}",
            f"{installer.QUARANTINE_PREFIX}{transaction_id}",
            transaction_id,
            manifest,
            None,
        )
        transaction_raw = installer._write_json_exclusive(
            skills_dir / installer.TRANSACTION_NAME, transaction
        )
        stage = skills_dir / str(transaction["stage_name"])
        destination = stage.joinpath(*relative.split("/"))
        destination.parent.mkdir(parents=True)
        self.normalize_portable_stage_modes(stage)
        installer._write_json_exclusive(
            stage / installer.PROVENANCE_MARKER,
            installer._provenance_record(transaction, transaction_raw),
        )
        return (
            repo_root,
            skills_dir,
            stage,
            transaction,
            transaction_raw,
            source,
            destination,
        )

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

    def test_hard_linked_lock_never_writes_outside_user_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skills_dir = root / "skills"
            skills_dir.mkdir()
            victim = root / "outside-empty-user-file.txt"
            victim.write_bytes(b"")
            lock = skills_dir / installer.LOCK_NAME
            os.link(victim, lock)

            result = self.run_installer(skills_dir)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("installer lock is linked", result.stderr)
            self.assertEqual(victim.read_bytes(), b"")
            self.assertEqual(lock.read_bytes(), b"")
            self.assertFalse((skills_dir / SKILL_NAME).exists())

    def test_existing_lock_bytes_are_never_mutated(self) -> None:
        for original in (b"", b"x"):
            with self.subTest(original=original), tempfile.TemporaryDirectory() as tmp:
                skills_dir = Path(tmp) / "skills"
                skills_dir.mkdir()
                lock = skills_dir / installer.LOCK_NAME
                lock.write_bytes(original)

                result = self.run_installer(skills_dir)

                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(lock.read_bytes(), original)

    def test_unsupported_lock_error_fails_immediately(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()

            @contextlib.contextmanager
            def unsupported_lock(_descriptor: int):
                raise OSError(errno.ENOTSUP, "locking is unsupported")
                yield

            with mock.patch.object(
                installer, "_locked_record_descriptor", unsupported_lock
            ), mock.patch.object(installer.time, "sleep") as sleep:
                with self.assertRaisesRegex(OSError, "locking is unsupported"):
                    with installer.exclusive_install_lock(skills_dir):
                        self.fail("unsupported locking must not enter the critical section")

            sleep.assert_not_called()

    def test_snapshot_walk_error_is_not_treated_as_an_incomplete_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            destination = skills_dir / SKILL_NAME
            destination.mkdir(parents=True)
            shutil.copy2(ROOT / "SKILL.md", destination / "SKILL.md")
            original_walk = installer.os.walk

            def denied_walk(top, *args, onerror=None, **kwargs):
                if Path(top) == destination:
                    assert onerror is not None
                    onerror(PermissionError(errno.EACCES, "subtree is unreadable"))
                    return iter(())
                return original_walk(top, *args, onerror=onerror, **kwargs)

            with mock.patch.object(installer.os, "walk", denied_walk):
                result, output = self.call_main(skills_dir)

            self.assertEqual(result, 1, output)
            self.assertIn("cannot be inspected safely", output)
            self.assertTrue((destination / "SKILL.md").is_file())
            self.assertFalse((skills_dir / installer.TRANSACTION_NAME).exists())

    @unittest.skipUnless(os.name == "nt", "NTFS named stream policy")
    def test_no_force_refuses_payload_bytes_with_named_streams(self) -> None:
        for target_kind in ("file", "root"):
            with self.subTest(target_kind=target_kind), tempfile.TemporaryDirectory() as tmp:
                skills_dir = Path(tmp) / "skills"
                destination = skills_dir / SKILL_NAME
                destination.mkdir(parents=True)
                shutil.copy2(ROOT / "SKILL.md", destination / "SKILL.md")
                base = destination / "SKILL.md" if target_kind == "file" else destination
                stream = Path(f"{base}:usernote")
                stream.write_text("MUST SURVIVE\n", encoding="utf-8")

                result = self.run_installer(skills_dir)

                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("not representable", result.stdout + result.stderr)
                self.assertEqual(stream.read_text(encoding="utf-8"), "MUST SURVIVE\n")
                self.assertFalse((skills_dir / installer.TRANSACTION_NAME).exists())

    @unittest.skipUnless(os.name == "nt", "NTFS named stream policy")
    def test_stream_added_after_classification_invalidates_no_force_repair(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            destination = skills_dir / SKILL_NAME
            destination.mkdir(parents=True)
            skill_file = destination / "SKILL.md"
            shutil.copy2(ROOT / "SKILL.md", skill_file)
            stream = Path(f"{skill_file}:late-note")
            original_classify = installer._classify_existing_install_bound
            classify_calls = 0

            def classify_then_add_stream(path: Path, manifest):
                nonlocal classify_calls
                classification = original_classify(path, manifest)
                self.assertEqual(classification.state, "incomplete")
                classify_calls += 1
                if classify_calls == 2:
                    stream.write_text("MUST SURVIVE\n", encoding="utf-8")
                return classification

            with mock.patch.object(
                installer,
                "_classify_existing_install_bound",
                classify_then_add_stream,
            ):
                result, output = self.call_main(skills_dir)

            self.assertEqual(result, 1, output)
            self.assertEqual(classify_calls, 2)
            self.assertIn("not representable", output)
            self.assertEqual(stream.read_text(encoding="utf-8"), "MUST SURVIVE\n")
            self.assertFalse((skills_dir / installer.TRANSACTION_NAME).exists())

    @unittest.skipUnless(os.name == "nt", "Windows read-only deletion")
    def test_force_replacement_recovers_read_only_live_file_and_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            initial = self.run_installer(skills_dir)
            self.assertEqual(initial.returncode, 0, initial.stdout + initial.stderr)
            destination = skills_dir / SKILL_NAME
            (destination / "SKILL.md").chmod(stat.S_IREAD)
            (destination / "references").chmod(stat.S_IREAD)
            destination.chmod(stat.S_IREAD)
            try:
                replacement = self.run_installer(skills_dir, "--force")
                self.assertEqual(
                    replacement.returncode,
                    0,
                    replacement.stdout + replacement.stderr,
                )
                self.assert_completed(destination)
                self.assertFalse((skills_dir / installer.TRANSACTION_NAME).exists())
                self.assertEqual(
                    list(skills_dir.glob(f"{installer.QUARANTINE_PREFIX}*")), []
                )
            finally:
                # Keep TemporaryDirectory cleanup reliable if an assertion
                # exposes a regression and leaves a read-only quarantine.
                for candidate in sorted(
                    skills_dir.rglob("*"), key=lambda item: len(item.parts), reverse=True
                ):
                    try:
                        candidate.chmod(stat.S_IWRITE | stat.S_IREAD)
                    except OSError:
                        pass
                try:
                    destination.chmod(stat.S_IWRITE | stat.S_IREAD)
                except OSError:
                    pass

    @unittest.skipUnless(
        os.name != "nt" and hasattr(os, "setxattr"),
        "POSIX extended-attribute policy",
    )
    def test_no_force_refuses_payload_bytes_with_extended_attributes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            destination = skills_dir / SKILL_NAME
            destination.mkdir(parents=True)
            skill_file = destination / "SKILL.md"
            shutil.copy2(ROOT / "SKILL.md", skill_file)
            try:
                os.setxattr(skill_file, "user.seedance-test", b"MUST SURVIVE")
            except OSError as exc:
                self.skipTest(f"temporary filesystem does not support xattrs: {exc}")

            result = self.run_installer(skills_dir)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("not representable", result.stdout + result.stderr)
            self.assertEqual(
                os.getxattr(skill_file, "user.seedance-test"), b"MUST SURVIVE"
            )
            self.assertFalse((skills_dir / installer.TRANSACTION_NAME).exists())

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

    def test_unhashable_transaction_enums_fail_closed_through_cli(self) -> None:
        payload = {
            "SKILL.md": {
                "size": 1,
                "sha256": hashlib.sha256(b"x").hexdigest(),
            }
        }
        for field in ("old_root_type", "replacement_state"):
            for hostile in ([], {}):
                with (
                    self.subTest(field=field, hostile=type(hostile).__name__),
                    tempfile.TemporaryDirectory() as tmp,
                ):
                    skills_dir = Path(tmp) / "skills"
                    skills_dir.mkdir()
                    transaction_id = "a" * 32
                    record = installer._transaction_record(
                        f"{installer.STAGE_PREFIX}123-{transaction_id}",
                        f"{installer.QUARANTINE_PREFIX}{transaction_id}",
                        transaction_id,
                        payload,
                        None,
                    )
                    unsigned = dict(record)
                    unsigned.pop("record_sha256")
                    unsigned[field] = hostile
                    path = skills_dir / installer.TRANSACTION_NAME
                    installer._write_json_exclusive(
                        path,
                        installer._record_with_digest(unsigned),
                    )

                    result = self.run_installer(skills_dir, "--force")
                    combined = result.stdout + result.stderr

                    self.assertEqual(result.returncode, 1, combined)
                    self.assertNotIn("Traceback", combined)
                    self.assertIn("transaction record is untrusted", combined)
                    self.assertTrue(path.is_file())
                    self.assertFalse((skills_dir / SKILL_NAME).exists())

    def test_unhashable_quarantine_enums_fail_closed_through_cli(self) -> None:
        payload = {
            "SKILL.md": {
                "size": 1,
                "sha256": hashlib.sha256(b"x").hexdigest(),
            }
        }
        for field in ("purpose", "authorized_root_type"):
            for hostile in ([], {}):
                with (
                    self.subTest(field=field, hostile=type(hostile).__name__),
                    tempfile.TemporaryDirectory() as tmp,
                ):
                    skills_dir = Path(tmp) / "skills"
                    skills_dir.mkdir()
                    transaction_id = "b" * 32
                    transaction = installer._transaction_record(
                        f"{installer.STAGE_PREFIX}123-{transaction_id}",
                        f"{installer.QUARANTINE_PREFIX}{transaction_id}",
                        transaction_id,
                        payload,
                        None,
                    )
                    transaction_raw = installer._write_json_exclusive(
                        skills_dir / installer.TRANSACTION_NAME,
                        transaction,
                    )
                    quarantine = skills_dir / str(transaction["quarantine_name"])
                    quarantine.mkdir()
                    (quarantine / "owned.txt").write_bytes(b"authorized")
                    authorized = installer._capture_path_snapshot(quarantine)
                    marker = installer._quarantine_record(
                        transaction,
                        transaction_raw,
                        "stage",
                        authorized,
                    )
                    unsigned = dict(marker)
                    unsigned.pop("record_sha256")
                    unsigned[field] = hostile
                    marker_path = quarantine / installer.QUARANTINE_MARKER
                    installer._write_json_exclusive(
                        marker_path,
                        installer._record_with_digest(unsigned),
                    )

                    result = self.run_installer(skills_dir, "--force")
                    combined = result.stdout + result.stderr

                    self.assertEqual(result.returncode, 1, combined)
                    self.assertNotIn("Traceback", combined)
                    self.assertTrue(marker_path.is_file())
                    self.assertTrue((quarantine / "owned.txt").is_file())
                    self.assertFalse((skills_dir / SKILL_NAME).exists())

    def test_unhashable_private_journal_enums_fail_closed_through_cli(self) -> None:
        payload = {
            "SKILL.md": {
                "size": 1,
                "sha256": hashlib.sha256(b"x").hexdigest(),
            }
        }
        for field in ("purpose", "authorized_root_type"):
            for hostile in ([], {}):
                with (
                    self.subTest(field=field, hostile=type(hostile).__name__),
                    tempfile.TemporaryDirectory() as tmp,
                ):
                    skills_dir = Path(tmp) / "skills"
                    skills_dir.mkdir()
                    transaction_id = "c" * 32
                    transaction = installer._transaction_record(
                        f"{installer.STAGE_PREFIX}123-{transaction_id}",
                        f"{installer.QUARANTINE_PREFIX}{transaction_id}",
                        transaction_id,
                        payload,
                        None,
                    )
                    transaction_raw = installer._write_json_exclusive(
                        skills_dir / installer.TRANSACTION_NAME,
                        transaction,
                    )
                    quarantine = skills_dir / str(transaction["quarantine_name"])
                    quarantine.mkdir()
                    (quarantine / "owned.txt").write_bytes(b"authorized")
                    authorized = installer._capture_path_snapshot(quarantine)
                    workspace, journal_path = installer._private_delete_paths(
                        skills_dir,
                        transaction,
                    )
                    workspace_identity = installer._create_private_delete_workspace(
                        workspace
                    )
                    journal = installer._private_delete_record(
                        transaction,
                        transaction_raw,
                        "stage",
                        authorized,
                        workspace_identity,
                    )
                    unsigned = dict(journal)
                    unsigned.pop("record_sha256")
                    unsigned[field] = hostile
                    installer._write_json_exclusive(
                        journal_path,
                        installer._record_with_digest(unsigned),
                    )

                    result = self.run_installer(skills_dir, "--force")
                    combined = result.stdout + result.stderr

                    self.assertEqual(result.returncode, 1, combined)
                    self.assertNotIn("Traceback", combined)
                    self.assertTrue(journal_path.is_file())
                    self.assertTrue(workspace.is_dir())
                    self.assertTrue((quarantine / "owned.txt").is_file())
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

    def test_record_reader_is_a_point_in_time_snapshot_after_handle_close(self) -> None:
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
                value, raw = installer._read_json_record(record)

            self.assertEqual(value, {"a": 1})
            self.assertEqual(raw, b'{"a":1}')
            self.assertEqual(record.read_bytes(), b'{"b":2}')

    @unittest.skipUnless(os.name == "nt", "Windows share-mode exclusion")
    def test_record_handle_blocks_write_after_final_capture_and_unlock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            record = Path(tmp) / "record.json"
            record.write_bytes(b'{"a":1}')
            original_lock = installer._locked_record_descriptor
            write_was_blocked = False

            @contextlib.contextmanager
            def attempt_after_unlock(descriptor: int):
                nonlocal write_was_blocked
                with original_lock(descriptor):
                    yield
                try:
                    record.write_bytes(b'{"b":2}')
                except PermissionError:
                    write_was_blocked = True

            with mock.patch.object(
                installer, "_locked_record_descriptor", attempt_after_unlock
            ):
                value, raw = installer._read_json_record(record)

            self.assertTrue(write_was_blocked)
            self.assertEqual(value, {"a": 1})
            self.assertEqual(raw, b'{"a":1}')
            self.assertEqual(record.read_bytes(), b'{"a":1}')

    def test_record_reader_rejects_same_tick_rewrite_with_restored_mtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            record = Path(tmp) / "record.json"
            record.write_bytes(b'{"a":1}')
            original_read = installer.os.read
            reads = 0

            def rewrite_then_read(descriptor: int, count: int) -> bytes:
                nonlocal reads
                reads += 1
                # Model an in-place same-length rewrite after the first EOF
                # while all stat fields stay indistinguishable.  Supplying
                # the second descriptor capture directly keeps this portable:
                # Windows denies a real write while LockFileEx is held.
                if reads == 3:
                    return b'{"b":2}'
                if reads == 4:
                    return b""
                return original_read(descriptor, count)

            with mock.patch.object(installer.os, "read", rewrite_then_read):
                with self.assertRaisesRegex(ValueError, "record content changed"):
                    installer._read_json_record(record)

            self.assertEqual(reads, 4)

    @unittest.skipIf(os.name == "nt", "POSIX directory durability")
    def test_json_record_fsyncs_file_before_parent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = root / "authority.json"
            original_fsync = os.fsync
            observed: list[str] = []

            def observe_fsync(descriptor: int) -> None:
                info = os.fstat(descriptor)
                observed.append("directory" if stat.S_ISDIR(info.st_mode) else "file")
                original_fsync(descriptor)

            with mock.patch.object(installer.os, "fsync", observe_fsync):
                installer._write_json_exclusive(record, {"authorized": True})

            self.assertEqual(observed, ["file", "directory"])

    def test_rename_fsyncs_the_post_rename_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            destination = root / "destination"
            source.mkdir()
            observed: list[Path] = []

            with mock.patch.object(
                installer,
                "_fsync_directory",
                side_effect=lambda path: observed.append(Path(path)),
            ):
                installer._rename_directory(source, destination)

            self.assertTrue(destination.is_dir())
            self.assertEqual(observed, [root])

    @unittest.skipIf(os.name == "nt", "POSIX directory durability")
    def test_private_move_fsyncs_destination_source_and_unlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "owned.txt"
            target.write_bytes(b"authorized installer bytes")
            expected = installer._bound_regular_file_metadata(target)
            workspace_path = root / "workspace"
            workspace_identity = installer._create_private_delete_workspace(
                workspace_path
            )
            events: list[str] = []
            original_rename = os.rename
            original_unlink = os.unlink
            original_fsync_directory_descriptor = (
                installer._fsync_directory_descriptor
            )

            def observe_rename(*args, **kwargs):
                events.append("rename")
                return original_rename(*args, **kwargs)

            def observe_unlink(*args, **kwargs):
                events.append("unlink")
                return original_unlink(*args, **kwargs)

            def observe_directory_fsync(descriptor: int) -> None:
                identity = installer._object_identity(os.fstat(descriptor))
                label = (
                    "workspace"
                    if identity == workspace_identity
                    else "source-parent"
                )
                events.append(f"fsync-{label}")
                original_fsync_directory_descriptor(descriptor)

            with installer._opened_private_delete_workspace(
                workspace_path, workspace_identity
            ) as workspace:
                with (
                    mock.patch.object(installer.os, "rename", observe_rename),
                    mock.patch.object(installer.os, "unlink", observe_unlink),
                    mock.patch.object(
                        installer,
                        "_fsync_directory_descriptor",
                        observe_directory_fsync,
                    ),
                ):
                    installer._delete_regular_file_by_handle(
                        target, expected, workspace=workspace
                    )

            self.assertEqual(
                events,
                [
                    "rename",
                    "fsync-workspace",
                    "fsync-source-parent",
                    "unlink",
                    "fsync-workspace",
                ],
            )
            installer._remove_private_delete_workspace(
                workspace_path, workspace_identity
            )

    @unittest.skipIf(os.name == "nt", "POSIX directory durability")
    def test_terminal_record_unlink_fsyncs_its_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = root / "authority.json"
            record.write_bytes(b'{"authorized":true}')
            events: list[str] = []
            original_unlink = os.unlink
            original_fsync_directory_descriptor = (
                installer._fsync_directory_descriptor
            )

            def observe_unlink(*args, **kwargs):
                events.append("unlink")
                return original_unlink(*args, **kwargs)

            def observe_directory_fsync(descriptor: int) -> None:
                events.append("fsync-parent")
                original_fsync_directory_descriptor(descriptor)

            with (
                mock.patch.object(installer.os, "unlink", observe_unlink),
                mock.patch.object(
                    installer,
                    "_fsync_directory_descriptor",
                    observe_directory_fsync,
                ),
                installer._bound_json_record(record) as binding,
            ):
                installer._delete_bound_json_record(binding)

            self.assertEqual(events, ["unlink", "fsync-parent"])

    @unittest.skipIf(os.name == "nt", "POSIX directory durability")
    def test_journal_parent_fsync_failure_preserves_workspace_and_journal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            transaction_id = "7" * 32
            payload = {
                "SKILL.md": {
                    "size": 1,
                    "sha256": hashlib.sha256(b"x").hexdigest(),
                }
            }
            transaction = installer._transaction_record(
                f"{installer.STAGE_PREFIX}123-{transaction_id}",
                f"{installer.QUARANTINE_PREFIX}{transaction_id}",
                transaction_id,
                payload,
                None,
            )
            transaction_raw = installer._write_json_exclusive(
                skills_dir / installer.TRANSACTION_NAME, transaction
            )
            quarantine = skills_dir / str(transaction["quarantine_name"])
            quarantine.mkdir()
            owned = quarantine / "owned.txt"
            owned.write_bytes(b"authorized installer bytes")
            authorized = installer._capture_path_snapshot(quarantine)
            installer._write_json_exclusive(
                quarantine / installer.QUARANTINE_MARKER,
                installer._quarantine_record(
                    transaction, transaction_raw, "stage", authorized
                ),
            )
            workspace, journal = installer._private_delete_paths(
                skills_dir, transaction
            )
            original_fsync_directory = installer._fsync_directory

            def fail_after_journal_creation(path: Path) -> None:
                if Path(path) == skills_dir and journal.exists():
                    raise OSError("injected parent fsync failure")
                original_fsync_directory(path)

            with mock.patch.object(
                installer,
                "_fsync_directory",
                fail_after_journal_creation,
            ):
                with self.assertRaisesRegex(OSError, "injected parent fsync"):
                    installer._start_private_delete_journal(
                        skills_dir,
                        transaction,
                        transaction_raw,
                        "stage",
                        authorized,
                    )

            self.assertTrue(workspace.is_dir())
            self.assertTrue(journal.is_file())
            installer.recover_interrupted_transaction(
                skills_dir, skills_dir / installer.SKILL_NAME
            )
            self.assertFalse(workspace.exists())
            self.assertFalse(journal.exists())

    @unittest.skipIf(os.name == "nt", "POSIX directory mode contract")
    def test_read_only_journaled_quarantine_resumes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            transaction_id = "8" * 32
            payload = {
                "SKILL.md": {
                    "size": 1,
                    "sha256": hashlib.sha256(b"x").hexdigest(),
                }
            }
            transaction = installer._transaction_record(
                f"{installer.STAGE_PREFIX}123-{transaction_id}",
                f"{installer.QUARANTINE_PREFIX}{transaction_id}",
                transaction_id,
                payload,
                None,
            )
            transaction_raw = installer._write_json_exclusive(
                skills_dir / installer.TRANSACTION_NAME, transaction
            )
            quarantine = skills_dir / str(transaction["quarantine_name"])
            nested = quarantine / "nested"
            nested.mkdir(parents=True)
            (nested / "owned.txt").write_bytes(b"authorized installer bytes")
            authorized = installer._capture_path_snapshot(quarantine)
            installer._write_json_exclusive(
                quarantine / installer.QUARANTINE_MARKER,
                installer._quarantine_record(
                    transaction, transaction_raw, "stage", authorized
                ),
            )
            installer._start_private_delete_journal(
                skills_dir,
                transaction,
                transaction_raw,
                "stage",
                authorized,
            )
            nested.chmod(0o555)
            quarantine.chmod(0o555)
            try:
                installer.recover_interrupted_transaction(
                    skills_dir, skills_dir / installer.SKILL_NAME
                )
                self.assertFalse(quarantine.exists())
                self.assertFalse(
                    (skills_dir / installer.TRANSACTION_NAME).exists()
                )
            finally:
                for directory in [
                    skills_dir,
                    *(path for path in skills_dir.rglob("*") if path.is_dir()),
                ]:
                    directory.chmod(0o755)

    @unittest.skipIf(os.name == "nt", "POSIX directory durability")
    def test_workspace_rmdir_fsyncs_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            identity = installer._create_private_delete_workspace(workspace)
            observed: list[Path] = []
            original_fsync_directory = installer._fsync_directory

            def observe(path: Path) -> None:
                observed.append(Path(path))
                original_fsync_directory(path)

            with mock.patch.object(installer, "_fsync_directory", observe):
                installer._remove_private_delete_workspace(workspace, identity)

            self.assertEqual(observed, [root])

    def test_retry_recovers_an_authorized_private_deletion_workspace_child(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            transaction_id = "a" * 32
            payload = {
                "SKILL.md": {
                    "size": 1,
                    "sha256": hashlib.sha256(b"x").hexdigest(),
                }
            }
            transaction = installer._transaction_record(
                f"{installer.STAGE_PREFIX}123-{transaction_id}",
                f"{installer.QUARANTINE_PREFIX}{transaction_id}",
                transaction_id,
                payload,
                None,
            )
            transaction_raw = installer._write_json_exclusive(
                skills_dir / installer.TRANSACTION_NAME, transaction
            )
            quarantine = skills_dir / str(transaction["quarantine_name"])
            quarantine.mkdir()
            owned = quarantine / "owned.txt"
            owned.write_bytes(b"authorized installer bytes")
            authorized = installer._capture_path_snapshot(quarantine)
            installer._write_json_exclusive(
                quarantine / installer.QUARANTINE_MARKER,
                installer._quarantine_record(
                    transaction, transaction_raw, "stage", authorized
                ),
            )
            installer._start_private_delete_journal(
                skills_dir,
                transaction,
                transaction_raw,
                "stage",
                authorized,
            )
            workspace, _ = installer._private_delete_paths(skills_dir, transaction)
            os.replace(owned, workspace / installer.PRIVATE_DELETE_ENTRY)

            installer.recover_interrupted_transaction(
                skills_dir, skills_dir / SKILL_NAME
            )

            self.assertFalse(quarantine.exists())
            self.assertFalse((skills_dir / installer.TRANSACTION_NAME).exists())
            self.assertFalse(workspace.exists())

    def test_retry_recovers_empty_private_workspace_after_child_unlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            transaction_id = "c" * 32
            payload = {
                "SKILL.md": {
                    "size": 1,
                    "sha256": hashlib.sha256(b"x").hexdigest(),
                }
            }
            transaction = installer._transaction_record(
                f"{installer.STAGE_PREFIX}123-{transaction_id}",
                f"{installer.QUARANTINE_PREFIX}{transaction_id}",
                transaction_id,
                payload,
                None,
            )
            transaction_raw = installer._write_json_exclusive(
                skills_dir / installer.TRANSACTION_NAME, transaction
            )
            quarantine = skills_dir / str(transaction["quarantine_name"])
            quarantine.mkdir()
            owned = quarantine / "owned.txt"
            owned.write_bytes(b"authorized installer bytes")
            authorized = installer._capture_path_snapshot(quarantine)
            installer._write_json_exclusive(
                quarantine / installer.QUARANTINE_MARKER,
                installer._quarantine_record(
                    transaction, transaction_raw, "stage", authorized
                ),
            )
            installer._start_private_delete_journal(
                skills_dir,
                transaction,
                transaction_raw,
                "stage",
                authorized,
            )
            workspace, journal = installer._private_delete_paths(
                skills_dir, transaction
            )
            os.replace(owned, workspace / installer.PRIVATE_DELETE_ENTRY)
            (workspace / installer.PRIVATE_DELETE_ENTRY).unlink()

            original_delete_record = installer._delete_bound_json_record
            journal_cleanup_observed = False

            def assert_workspace_removed_first(binding, workspace_arg=None):
                nonlocal journal_cleanup_observed
                if binding.path == journal:
                    journal_cleanup_observed = True
                    self.assertFalse(workspace.exists())
                    self.assertIsNone(workspace_arg)
                return original_delete_record(binding, workspace_arg)

            with mock.patch.object(
                installer,
                "_delete_bound_json_record",
                assert_workspace_removed_first,
            ):
                installer.recover_interrupted_transaction(
                    skills_dir, skills_dir / SKILL_NAME
                )

            self.assertTrue(journal_cleanup_observed)
            self.assertFalse(quarantine.exists())
            self.assertFalse(workspace.exists())
            self.assertFalse((skills_dir / installer.TRANSACTION_NAME).exists())

    def test_retry_recovers_post_root_and_journal_only_delete_states(self) -> None:
        for remove_workspace in (False, True):
            with self.subTest(journal_only=remove_workspace), tempfile.TemporaryDirectory() as tmp:
                skills_dir = Path(tmp) / "skills"
                skills_dir.mkdir()
                transaction_id = ("9" if remove_workspace else "6") * 32
                payload = {
                    "SKILL.md": {
                        "size": 1,
                        "sha256": hashlib.sha256(b"x").hexdigest(),
                    }
                }
                transaction = installer._transaction_record(
                    f"{installer.STAGE_PREFIX}123-{transaction_id}",
                    f"{installer.QUARANTINE_PREFIX}{transaction_id}",
                    transaction_id,
                    payload,
                    None,
                )
                transaction_raw = installer._write_json_exclusive(
                    skills_dir / installer.TRANSACTION_NAME, transaction
                )
                quarantine = skills_dir / str(transaction["quarantine_name"])
                quarantine.mkdir()
                owned = quarantine / "owned.txt"
                owned.write_bytes(b"authorized installer bytes")
                authorized = installer._capture_path_snapshot(quarantine)
                installer._write_json_exclusive(
                    quarantine / installer.QUARANTINE_MARKER,
                    installer._quarantine_record(
                        transaction, transaction_raw, "stage", authorized
                    ),
                )
                installer._start_private_delete_journal(
                    skills_dir,
                    transaction,
                    transaction_raw,
                    "stage",
                    authorized,
                )
                workspace, journal = installer._private_delete_paths(
                    skills_dir, transaction
                )
                workspace_identity = installer._object_identity(workspace.lstat())
                owned.unlink()
                (quarantine / installer.QUARANTINE_MARKER).unlink()
                quarantine.rmdir()
                if remove_workspace:
                    installer._remove_private_delete_workspace(
                        workspace, workspace_identity
                    )

                with mock.patch.object(
                    installer,
                    "_create_private_delete_workspace",
                    side_effect=AssertionError(
                        "terminal record cleanup must not create an unjournaled workspace"
                    ),
                ):
                    installer.recover_interrupted_transaction(
                        skills_dir, skills_dir / SKILL_NAME
                    )

                self.assertFalse(workspace.exists())
                self.assertFalse(journal.exists())
                self.assertFalse((skills_dir / installer.TRANSACTION_NAME).exists())

    def test_unjournaled_private_workspace_is_preserved_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            transaction_id = "e" * 32
            payload = {
                "SKILL.md": {
                    "size": 1,
                    "sha256": hashlib.sha256(b"x").hexdigest(),
                }
            }
            transaction = installer._transaction_record(
                f"{installer.STAGE_PREFIX}123-{transaction_id}",
                f"{installer.QUARANTINE_PREFIX}{transaction_id}",
                transaction_id,
                payload,
                None,
            )
            installer._write_json_exclusive(
                skills_dir / installer.TRANSACTION_NAME, transaction
            )
            workspace, _ = installer._private_delete_paths(skills_dir, transaction)
            workspace.mkdir(mode=0o700)
            (workspace / "user-data.txt").write_text(
                "preserve\n", encoding="utf-8"
            )

            with self.assertRaisesRegex(RuntimeError, "no trusted journal"):
                installer.recover_interrupted_transaction(
                    skills_dir, skills_dir / SKILL_NAME
                )

            self.assertTrue(workspace.is_dir())
            self.assertEqual(
                (workspace / "user-data.txt").read_text(encoding="utf-8"),
                "preserve\n",
            )
            self.assertTrue((skills_dir / installer.TRANSACTION_NAME).is_file())

    def test_retry_recovers_journal_removed_before_empty_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            transaction_id = "f" * 32
            payload = {
                "SKILL.md": {
                    "size": 1,
                    "sha256": hashlib.sha256(b"x").hexdigest(),
                }
            }
            transaction = installer._transaction_record(
                f"{installer.STAGE_PREFIX}123-{transaction_id}",
                f"{installer.QUARANTINE_PREFIX}{transaction_id}",
                transaction_id,
                payload,
                None,
            )
            transaction_raw = installer._write_json_exclusive(
                skills_dir / installer.TRANSACTION_NAME, transaction
            )
            quarantine = skills_dir / str(transaction["quarantine_name"])
            quarantine.mkdir()
            owned = quarantine / "owned.txt"
            owned.write_bytes(b"authorized installer bytes")
            authorized = installer._capture_path_snapshot(quarantine)
            installer._write_json_exclusive(
                quarantine / installer.QUARANTINE_MARKER,
                installer._quarantine_record(
                    transaction, transaction_raw, "stage", authorized
                ),
            )
            installer._start_private_delete_journal(
                skills_dir,
                transaction,
                transaction_raw,
                "stage",
                authorized,
            )
            workspace, journal = installer._private_delete_paths(
                skills_dir, transaction
            )
            owned.unlink()
            (quarantine / installer.QUARANTINE_MARKER).unlink()
            quarantine.rmdir()
            journal.unlink()

            installer.recover_interrupted_transaction(
                skills_dir, skills_dir / installer.SKILL_NAME
            )

            self.assertFalse(workspace.exists())
            self.assertFalse(journal.exists())
            self.assertFalse((skills_dir / installer.TRANSACTION_NAME).exists())

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

    def test_record_reader_rejects_hard_linked_authority_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outside = root / "outside-user-record.json"
            outside.write_bytes(b'{"a":1}')
            record = root / "record.json"
            os.link(outside, record)

            with self.assertRaisesRegex(ValueError, "hard-linked"):
                installer._read_json_record(record)

            self.assertEqual(outside.read_bytes(), b'{"a":1}')

    def test_manifest_rejects_windows_ads_or_drive_like_path(self) -> None:
        hostile = {
            "SKILL.md:stream": {
                "size": 1,
                "sha256": "0" * 64,
            }
        }

        with self.assertRaisesRegex(ValueError, "unsafe path"):
            installer._validate_payload_manifest(hostile)

    def test_manifest_rejects_windows_reserved_and_normalized_aliases(self) -> None:
        metadata = {"size": 0, "sha256": "0" * 64}
        hostile = [
            "CON",
            "NUL",
            "aux.txt",
            "name.",
            "name ",
            "dir./file",
            "dir /file",
            "nested/COM1.log",
            "nested/LPT9",
            "nested/COM¹.txt",
            "nested/LPT².log",
        ]

        for relative in hostile:
            with self.subTest(relative=relative):
                with self.assertRaisesRegex(ValueError, "unsafe path"):
                    installer._validate_payload_manifest({relative: metadata})

    def test_manifest_rejects_control_unicode_and_case_aliases(self) -> None:
        metadata = {"size": 0, "sha256": "0" * 64}
        hostile_manifests = [
            {"bad\x01name.txt": metadata},
            {"bad\x85name.txt": metadata},
            {"bad\u202ename.txt": metadata},
            {"bad\ufe0fname.txt": metadata},
            {"A.txt": metadata, "a.txt": metadata},
            {"cafe\u0301.txt": metadata},
        ]

        for manifest in hostile_manifests:
            with self.subTest(paths=list(manifest)):
                with self.assertRaisesRegex(ValueError, "unsafe|ambiguous"):
                    installer._validate_payload_manifest(dict(sorted(manifest.items())))

    def test_tree_manifest_rejects_control_unicode_and_case_aliases(self) -> None:
        file_metadata = {
            "type": "file",
            "size": 0,
            "sha256": "0" * 64,
            "device": 1,
            "inode": 1,
        }
        hostile_manifests = [
            {"bad\x01name.txt": file_metadata},
            {"bad\x85name.txt": file_metadata},
            {"bad\u202ename.txt": file_metadata},
            {"bad\ufe0fname.txt": file_metadata},
            {"A.txt": file_metadata, "a.txt": file_metadata},
            {"cafe\u0301.txt": file_metadata},
        ]

        for manifest in hostile_manifests:
            with self.subTest(paths=list(manifest)):
                with self.assertRaisesRegex(ValueError, "unsafe|ambiguous"):
                    installer._validate_tree_entries(
                        dict(sorted(manifest.items())), "dir"
                    )

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

    def test_leaf_swap_after_metadata_validation_preserves_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            quarantine = root / "quarantine"
            quarantine.mkdir()
            target = quarantine / "owned.txt"
            target.write_bytes(b"authorized installer bytes")
            authorized = installer._capture_path_snapshot(quarantine)
            stashed = root / "authorized-stashed.txt"
            victim = root / "outside-user-data.txt"
            victim.write_bytes(b"outside user data")
            original_metadata = installer._regular_file_metadata
            target_checks = 0

            def swap_after_last_validation(path: Path, **kwargs):
                nonlocal target_checks
                metadata = original_metadata(path, **kwargs)
                if path == target:
                    target_checks += 1
                    if target_checks == 3:
                        os.replace(target, stashed)
                        os.replace(victim, target)
                return metadata

            with mock.patch.object(
                installer,
                "_regular_file_metadata",
                swap_after_last_validation,
            ):
                with self.assertRaisesRegex(
                    RuntimeError, "changed immediately|changed or late data"
                ):
                    installer._delete_bound_tree(quarantine, authorized)

            self.assertEqual(target_checks, 3)
            self.assertEqual(target.read_bytes(), b"outside user data")
            self.assertEqual(stashed.read_bytes(), b"authorized installer bytes")

    @unittest.skipIf(os.name == "nt", "POSIX private tombstone contract")
    def test_posix_file_deletion_uses_a_private_bound_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "owned.txt"
            target.write_bytes(b"authorized installer bytes")
            expected = installer._bound_regular_file_metadata(target)
            original_unlink = os.unlink
            observed = False

            def inspect_unlink(path, *args, dir_fd=None, **kwargs):
                nonlocal observed
                if path == installer.PRIVATE_DELETE_ENTRY:
                    observed = True
                    self.assertIsNotNone(dir_fd)
                    self.assertEqual(
                        stat.S_IMODE(os.fstat(dir_fd).st_mode),
                        0o700,
                    )
                return original_unlink(path, *args, dir_fd=dir_fd, **kwargs)

            with mock.patch.object(installer.os, "unlink", inspect_unlink):
                installer._delete_regular_file_by_handle(target, expected)

            self.assertTrue(observed)
            self.assertFalse(target.exists())
            self.assertEqual(list(Path(tmp).iterdir()), [])

    @unittest.skipIf(os.name == "nt", "POSIX private tombstone contract")
    def test_posix_directory_deletion_uses_a_private_bound_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "owned-directory"
            target.mkdir()
            expected_identity = installer._object_identity(target.lstat())
            original_rmdir = os.rmdir
            observed = False

            def inspect_rmdir(path, *args, dir_fd=None, **kwargs):
                nonlocal observed
                if path == installer.PRIVATE_DELETE_ENTRY:
                    observed = True
                    self.assertIsNotNone(dir_fd)
                    self.assertEqual(
                        stat.S_IMODE(os.fstat(dir_fd).st_mode),
                        0o700,
                    )
                return original_rmdir(path, *args, dir_fd=dir_fd, **kwargs)

            with mock.patch.object(installer.os, "rmdir", inspect_rmdir):
                installer._delete_empty_directory_by_handle(target, expected_identity)

            self.assertTrue(observed)
            self.assertFalse(target.exists())
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_transaction_record_cleanup_never_unlinks_a_swapped_outside_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            transaction_id = "b" * 32
            record_path = root / installer.TRANSACTION_NAME
            record_raw = installer._write_json_exclusive(record_path, {"sentinel": 1})
            done = root / f"{installer.TRANSACTION_DONE_PREFIX}{transaction_id}"
            stashed = root / "original-record-stashed"
            outside = root / "outside-user-file"
            outside.write_bytes(b"outside user bytes")
            original_unlink = Path.unlink
            swapped = False

            def swap_then_unlink(path: Path, *args, **kwargs):
                nonlocal swapped
                if path == done and not swapped:
                    swapped = True
                    path.rename(stashed)
                    outside.rename(path)
                return original_unlink(path, *args, **kwargs)

            with mock.patch.object(Path, "unlink", swap_then_unlink):
                installer._quarantine_record_and_remove(
                    record_path,
                    record_raw,
                    transaction_id,
                )

            self.assertFalse(swapped, "cleanup regressed to pathname-based unlink")
            self.assertEqual(outside.read_bytes(), b"outside user bytes")
            self.assertFalse(done.exists())

    @unittest.skipIf(os.name == "nt", "POSIX private-workspace cleanup")
    def test_bound_record_cleanup_preserves_a_namespace_swap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = root / installer.TRANSACTION_NAME
            record.write_bytes(b'{"authorized":true}')
            stashed = root / "authorized-record-stashed"
            outside = root / "outside-user-file"
            outside.write_bytes(b"outside user bytes")
            workspace_path = root / "private-workspace"
            workspace_identity = installer._create_private_delete_workspace(
                workspace_path
            )
            original_rename = os.rename
            swapped = False

            def swap_before_private_move(
                source,
                destination,
                *args,
                src_dir_fd=None,
                dst_dir_fd=None,
                **kwargs,
            ):
                nonlocal swapped
                if (
                    source == record.name
                    and destination == installer.PRIVATE_DELETE_ENTRY
                    and src_dir_fd is not None
                    and not swapped
                ):
                    swapped = True
                    original_rename(record, stashed)
                    original_rename(outside, record)
                return original_rename(
                    source,
                    destination,
                    *args,
                    src_dir_fd=src_dir_fd,
                    dst_dir_fd=dst_dir_fd,
                    **kwargs,
                )

            with installer._opened_private_delete_workspace(
                workspace_path, workspace_identity
            ) as workspace:
                with mock.patch.object(installer.os, "rename", swap_before_private_move):
                    with self.assertRaises((RuntimeError, ValueError)):
                        with installer._bound_json_record(record) as binding:
                            installer._delete_bound_json_record(binding, workspace)

            self.assertTrue(swapped)
            self.assertEqual(stashed.read_bytes(), b'{"authorized":true}')
            preserved = workspace_path / installer.PRIVATE_DELETE_ENTRY
            self.assertEqual(preserved.read_bytes(), b"outside user bytes")

    def test_directory_cleanup_never_rmdirs_a_swapped_outside_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            quarantine = root / "quarantine"
            owned = quarantine / "owned-empty-directory"
            owned.mkdir(parents=True)
            authorized = installer._capture_path_snapshot(quarantine)
            stashed = root / "authorized-directory-stashed"
            outside = root / "outside-user-directory"
            outside.mkdir()
            original_rmdir = Path.rmdir
            swapped = False

            def swap_then_rmdir(path: Path, *args, **kwargs):
                nonlocal swapped
                if path == owned and not swapped:
                    swapped = True
                    path.rename(stashed)
                    outside.rename(path)
                return original_rmdir(path, *args, **kwargs)

            with mock.patch.object(Path, "rmdir", swap_then_rmdir):
                installer._delete_bound_tree(quarantine, authorized)

            self.assertFalse(swapped, "cleanup regressed to pathname-based rmdir")
            self.assertTrue(outside.is_dir())
            self.assertFalse(owned.exists())

    def test_preopen_equal_byte_file_replacement_is_not_authorized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            quarantine = root / "quarantine"
            quarantine.mkdir()
            owned = quarantine / "owned.txt"
            owned.write_bytes(b"same bytes")
            authorized = installer._capture_path_snapshot(quarantine)
            stashed = root / "authorized-file-stashed"
            outside = root / "outside-user-file"
            outside.write_bytes(b"same bytes")
            original_delete = installer._delete_regular_file_by_handle
            swapped = False

            def swap_before_open(path: Path, expected, *, workspace=None):
                nonlocal swapped
                if path == owned and not swapped:
                    swapped = True
                    path.rename(stashed)
                    outside.rename(path)
                return original_delete(path, expected, workspace=workspace)

            with mock.patch.object(
                installer,
                "_delete_regular_file_by_handle",
                swap_before_open,
            ):
                with self.assertRaisesRegex(RuntimeError, "changed immediately"):
                    installer._delete_bound_tree(quarantine, authorized)

            self.assertTrue(swapped)
            self.assertEqual(owned.read_bytes(), b"same bytes")
            self.assertEqual(stashed.read_bytes(), b"same bytes")

    def test_preopen_empty_directory_replacement_is_not_authorized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            quarantine = root / "quarantine"
            owned = quarantine / "owned-empty-directory"
            owned.mkdir(parents=True)
            authorized = installer._capture_path_snapshot(quarantine)
            stashed = root / "authorized-directory-stashed"
            outside = root / "outside-user-directory"
            outside.mkdir()
            original_delete = installer._delete_empty_directory_by_handle
            swapped = False

            def swap_before_open(
                path: Path, expected_identity, *, workspace=None
            ):
                nonlocal swapped
                if path == owned and not swapped:
                    swapped = True
                    path.rename(stashed)
                    outside.rename(path)
                return original_delete(
                    path, expected_identity, workspace=workspace
                )

            with mock.patch.object(
                installer,
                "_delete_empty_directory_by_handle",
                swap_before_open,
            ):
                with self.assertRaisesRegex(RuntimeError, "not transaction-authorized"):
                    installer._delete_bound_tree(quarantine, authorized)

            self.assertTrue(swapped)
            self.assertTrue(owned.is_dir())
            self.assertTrue(stashed.is_dir())

    def test_bound_deletion_refuses_hard_linked_leaf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            quarantine = root / "quarantine"
            quarantine.mkdir()
            target = quarantine / "owned.txt"
            target.write_bytes(b"authorized installer bytes")
            authorized = installer._capture_path_snapshot(quarantine)
            outside = root / "outside-user-alias.txt"
            os.link(target, outside)

            with self.assertRaisesRegex(RuntimeError, "linked, reparse, or non-regular"):
                installer._delete_bound_tree(quarantine, authorized)

            self.assertEqual(target.read_bytes(), b"authorized installer bytes")
            self.assertEqual(outside.read_bytes(), b"authorized installer bytes")

    @unittest.skipUnless(os.name == "nt", "Windows share-mode exclusion")
    def test_preopened_shared_writer_blocks_bound_file_deletion(self) -> None:
        import ctypes
        from ctypes import wintypes

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "owned.txt"
            target.write_bytes(b"authorized installer bytes")
            expected = installer._bound_regular_file_metadata(target)
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            create_file = kernel32.CreateFileW
            create_file.argtypes = [
                wintypes.LPCWSTR,
                wintypes.DWORD,
                wintypes.DWORD,
                wintypes.LPVOID,
                wintypes.DWORD,
                wintypes.DWORD,
                wintypes.HANDLE,
            ]
            create_file.restype = wintypes.HANDLE
            handle = create_file(
                str(target),
                0x80000000 | 0x40000000,  # GENERIC_READ | GENERIC_WRITE
                0x00000001 | 0x00000002 | 0x00000004,
                None,
                3,
                0x08000000,
                None,
            )
            self.assertNotEqual(handle, ctypes.c_void_p(-1).value)
            close_handle = kernel32.CloseHandle
            close_handle.argtypes = [wintypes.HANDLE]
            close_handle.restype = wintypes.BOOL
            try:
                with self.assertRaises(OSError):
                    installer._delete_regular_file_by_handle(target, expected)
                self.assertEqual(target.read_bytes(), b"authorized installer bytes")
            finally:
                self.assertTrue(close_handle(handle))

            installer._delete_regular_file_by_handle(target, expected)
            self.assertFalse(target.exists())

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

    def test_transaction_record_cleanup_uses_its_bound_handle(self) -> None:
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

            self.assertEqual(result, 0, output)
            self.assertFalse(swapped)
            self.assertFalse(transaction.exists())
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
            results = self.communicate_process_group(processes)

            self.assertEqual(sum(process.returncode == 0 for process in processes), workers)
            for process, (stdout, stderr) in zip(processes, results):
                self.assertEqual(process.returncode, 0, stdout + stderr)
                self.assertNotIn("Traceback", stderr)
                self.assertTrue(
                    "Installed seedance-20" in stdout or "another installer finished" in stdout,
                    stdout,
                )
            self.assert_completed(skills_dir / SKILL_NAME)

    def test_retry_recovers_stage_created_before_provenance_publication(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            manifest = installer.payload_manifest(ROOT)
            transaction_id = "7" * 32
            transaction = installer._transaction_record(
                f"{installer.STAGE_PREFIX}123-{transaction_id}",
                f"{installer.QUARANTINE_PREFIX}{transaction_id}",
                transaction_id,
                manifest,
                None,
            )
            installer._write_json_exclusive(
                skills_dir / installer.TRANSACTION_NAME, transaction
            )
            stage = skills_dir / str(transaction["stage_name"])
            stage.mkdir(mode=0o700)

            result = self.run_installer(skills_dir)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(stage.exists())
            self.assert_completed(skills_dir / SKILL_NAME)

    def test_pre_provenance_stage_with_payload_is_preserved_fail_closed(self) -> None:
        for torn_provenance in (False, True):
            with self.subTest(torn=torn_provenance), tempfile.TemporaryDirectory() as tmp:
                skills_dir = Path(tmp) / "skills"
                skills_dir.mkdir()
                payload_bytes = b"source-identical bytes"
                manifest = {
                    "SKILL.md": {
                        "size": len(payload_bytes),
                        "sha256": hashlib.sha256(payload_bytes).hexdigest(),
                    }
                }
                transaction_id = ("4" if torn_provenance else "3") * 32
                transaction = installer._transaction_record(
                    f"{installer.STAGE_PREFIX}123-{transaction_id}",
                    f"{installer.QUARANTINE_PREFIX}{transaction_id}",
                    transaction_id,
                    manifest,
                    None,
                )
                transaction_raw = installer._write_json_exclusive(
                    skills_dir / installer.TRANSACTION_NAME, transaction
                )
                stage = skills_dir / str(transaction["stage_name"])
                stage.mkdir(mode=0o700)
                if torn_provenance:
                    expected_raw = installer._json_record_bytes(
                        installer._provenance_record(transaction, transaction_raw)
                    )
                    (stage / installer.PROVENANCE_MARKER).write_bytes(
                        expected_raw[: len(expected_raw) // 2]
                    )
                (stage / "SKILL.md").write_bytes(payload_bytes)
                self.normalize_portable_stage_modes(stage)

                with self.assertRaisesRegex(RuntimeError, "could not precede"):
                    installer.recover_interrupted_transaction(
                        skills_dir, skills_dir / SKILL_NAME
                    )

                self.assertEqual((stage / "SKILL.md").read_bytes(), payload_bytes)
                self.assertTrue((skills_dir / installer.TRANSACTION_NAME).is_file())

    def test_torn_completion_with_partial_payload_is_preserved_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            first = b"first"
            second = b"second"
            payload_manifest = (
                b"SKILL.md\n"
                b"references/second.md\n"
                b"validation/install-payload.txt\n"
            )
            manifest = {
                "SKILL.md": {
                    "size": len(first),
                    "sha256": hashlib.sha256(first).hexdigest(),
                },
                "references/second.md": {
                    "size": len(second),
                    "sha256": hashlib.sha256(second).hexdigest(),
                },
                installer.PAYLOAD_MANIFEST.as_posix(): {
                    "size": len(payload_manifest),
                    "sha256": hashlib.sha256(payload_manifest).hexdigest(),
                },
            }
            transaction_id = "5" * 32
            transaction = installer._transaction_record(
                f"{installer.STAGE_PREFIX}123-{transaction_id}",
                f"{installer.QUARANTINE_PREFIX}{transaction_id}",
                transaction_id,
                manifest,
                None,
            )
            transaction_raw = installer._write_json_exclusive(
                skills_dir / installer.TRANSACTION_NAME, transaction
            )
            stage = skills_dir / str(transaction["stage_name"])
            stage.mkdir(mode=0o700)
            installer._write_json_exclusive(
                stage / installer.PROVENANCE_MARKER,
                installer._provenance_record(transaction, transaction_raw),
            )
            (stage / "SKILL.md").write_bytes(first)
            expected_completion = installer._json_record_bytes(
                installer._completion_marker_record(manifest)
            )
            (stage / installer.COMPLETION_MARKER).write_bytes(
                expected_completion[: len(expected_completion) // 2]
            )
            self.normalize_portable_stage_modes(stage)

            with self.assertRaisesRegex(RuntimeError, "full payload"):
                installer.recover_interrupted_transaction(
                    skills_dir, skills_dir / installer.SKILL_NAME
                )

            self.assertEqual((stage / "SKILL.md").read_bytes(), first)
            self.assertTrue((skills_dir / installer.TRANSACTION_NAME).is_file())

    def test_atomic_copy_faults_never_publish_a_partial_final_path(self) -> None:
        fault_names = ("open", "write", "fsync", "rename")
        for index, fault_name in enumerate(fault_names):
            with self.subTest(fault=fault_name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (
                    repo_root,
                    skills_dir,
                    stage,
                    transaction,
                    transaction_raw,
                    source,
                    destination,
                ) = self.make_atomic_copy_fixture(
                    root, transaction_digit="abcdef0123456789"[index]
                )
                relative = source.relative_to(repo_root).as_posix()
                component_name_max = installer._copy_temp_component_budget(stage)
                temp_relative = installer._copy_temp_relative(
                    relative, transaction_raw, component_name_max
                )
                temp_path = stage.joinpath(*temp_relative.split("/"))
                expected_size = int(transaction["payload_manifest"][relative]["size"])

                if fault_name == "open":
                    original_open = installer.os.open

                    def fail_temp_open(path, flags, mode=0o777, *, dir_fd=None):
                        if Path(path) == temp_path:
                            raise OSError("injected temp open failure")
                        if dir_fd is None:
                            return original_open(path, flags, mode)
                        return original_open(path, flags, mode, dir_fd=dir_fd)

                    patcher = mock.patch.object(installer.os, "open", fail_temp_open)
                elif fault_name == "write":
                    def fail_after_partial_write(descriptor: int, chunk: bytes) -> None:
                        written = installer.os.write(descriptor, chunk[:17])
                        self.assertEqual(written, 17)
                        raise OSError("injected payload write failure")

                    patcher = mock.patch.object(
                        installer, "_write_payload_chunk", fail_after_partial_write
                    )
                elif fault_name == "fsync":
                    patcher = mock.patch.object(
                        installer.os,
                        "fsync",
                        side_effect=OSError("injected payload fsync failure"),
                    )
                else:
                    patcher = mock.patch.object(
                        installer.os,
                        "replace",
                        side_effect=OSError("injected atomic rename failure"),
                    )

                with patcher, self.assertRaises(OSError):
                    installer._copy_payload_file_atomic(
                        source,
                        destination,
                        repo_root=repo_root,
                        stage=stage,
                        transaction=transaction,
                        transaction_raw=transaction_raw,
                    )

                self.assertFalse(destination.exists())
                if fault_name == "open":
                    self.assertFalse(temp_path.exists())
                else:
                    self.assertTrue(temp_path.is_file())
                    self.assertLessEqual(temp_path.stat().st_size, expected_size)
                    if fault_name == "write":
                        self.assertGreater(temp_path.stat().st_size, 0)
                        self.assertLess(temp_path.stat().st_size, expected_size)
                snapshot = installer._inspect_owned_stage(
                    stage, transaction, transaction_raw, require_complete=False
                )
                self.assertEqual(snapshot.root_type, "dir")

                installer.recover_interrupted_transaction(
                    skills_dir, skills_dir / installer.SKILL_NAME
                )
                self.assertFalse(stage.exists())
                self.assertFalse((skills_dir / installer.TRANSACTION_NAME).exists())

    def test_copy_temp_stays_compact_across_windows_style_limit_hints(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (
                repo_root,
                _skills_dir,
                _stage,
                _transaction,
                transaction_raw,
                source,
                _destination,
            ) = self.make_atomic_copy_fixture(Path(tmp), transaction_digit="6")
            relative = source.relative_to(repo_root).as_posix()
            with mock.patch.object(installer.os, "name", "nt"):
                self.assertEqual(
                    installer._copy_temp_component_budget(_stage),
                    installer.COPY_TEMP_MAX_BASENAME_BYTES,
                )
            names = {
                limit: installer._copy_temp_relative(
                    relative, transaction_raw, limit
                )
                for limit in (36, 64, 86, 255)
            }

            self.assertEqual(len(set(names.values())), 1)
            basename = names[255].rsplit("/", 1)[-1]
            self.assertEqual(
                len(os.fsencode(basename)),
                installer.COPY_TEMP_MAX_BASENAME_BYTES,
            )
            self.assertLessEqual(
                len(os.fsencode(basename)),
                len(os.fsencode(installer.PROVENANCE_MARKER)),
            )

    def test_atomic_copy_does_not_trust_a_255_byte_windows_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (
                repo_root,
                _skills_dir,
                stage,
                transaction,
                transaction_raw,
                source,
                destination,
            ) = self.make_atomic_copy_fixture(Path(tmp), transaction_digit="7")
            simulated_backing_limit = len(
                os.fsencode(installer.PROVENANCE_MARKER)
            )
            original_open = installer.os.open
            opened_siblings: list[str] = []

            def enforce_backing_limit(path, flags, mode=0o777, *, dir_fd=None):
                candidate = Path(path)
                if candidate.parent == destination.parent:
                    opened_siblings.append(candidate.name)
                    if len(os.fsencode(candidate.name)) > simulated_backing_limit:
                        raise OSError(
                            "simulated Windows backing volume rejected component"
                        )
                if dir_fd is None:
                    return original_open(path, flags, mode)
                return original_open(path, flags, mode, dir_fd=dir_fd)

            with mock.patch.object(installer.os, "open", enforce_backing_limit):
                installer._copy_payload_file_atomic(
                    source,
                    destination,
                    repo_root=repo_root,
                    stage=stage,
                    transaction=transaction,
                    transaction_raw=transaction_raw,
                    component_name_max=255,
                )

            self.assertEqual(destination.read_bytes(), source.read_bytes())
            self.assertTrue(
                any(
                    name.startswith(installer.COPY_TEMP_COMPACT_PREFIX)
                    for name in opened_siblings
                )
            )
            self.assertTrue(
                all(
                    len(os.fsencode(name)) <= simulated_backing_limit
                    for name in opened_siblings
                )
            )

    def test_atomic_copy_fsyncs_its_parent_only_after_rename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (
                repo_root,
                _skills_dir,
                stage,
                transaction,
                transaction_raw,
                source,
                destination,
            ) = self.make_atomic_copy_fixture(Path(tmp), transaction_digit="6")
            original_replace = installer.os.replace
            events: list[str] = []

            def observed_replace(source_path, destination_path) -> None:
                self.assertEqual(Path(destination_path), destination)
                self.assertFalse(destination.exists())
                events.append("rename")
                original_replace(source_path, destination_path)

            def observed_parent_fsync(path: Path) -> None:
                self.assertEqual(Path(path), destination.parent)
                self.assertEqual(destination.read_bytes(), source.read_bytes())
                events.append("parent-fsync")

            with (
                mock.patch.object(installer.os, "replace", observed_replace),
                mock.patch.object(installer, "_fsync_directory", observed_parent_fsync),
            ):
                installer._copy_payload_file_atomic(
                    source,
                    destination,
                    repo_root=repo_root,
                    stage=stage,
                    transaction=transaction,
                    transaction_raw=transaction_raw,
                )

            self.assertEqual(events, ["rename", "parent-fsync"])

    def test_atomic_copy_parent_fsync_failure_leaves_only_complete_final_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (
                repo_root,
                skills_dir,
                stage,
                transaction,
                transaction_raw,
                source,
                destination,
            ) = self.make_atomic_copy_fixture(Path(tmp), transaction_digit="7")
            expected = source.read_bytes()

            with (
                mock.patch.object(
                    installer,
                    "_fsync_directory",
                    side_effect=OSError("injected payload parent fsync failure"),
                ),
                self.assertRaisesRegex(OSError, "parent fsync failure"),
            ):
                installer._copy_payload_file_atomic(
                    source,
                    destination,
                    repo_root=repo_root,
                    stage=stage,
                    transaction=transaction,
                    transaction_raw=transaction_raw,
                )

            self.assertEqual(destination.read_bytes(), expected)
            relative = source.relative_to(repo_root).as_posix()
            temp_relative = installer._copy_temp_relative(
                relative,
                transaction_raw,
                installer._copy_temp_component_budget(stage),
            )
            self.assertFalse(stage.joinpath(*temp_relative.split("/")).exists())
            snapshot = installer._inspect_owned_stage(
                stage, transaction, transaction_raw, require_complete=False
            )
            expected_metadata = transaction["payload_manifest"][relative]
            self.assertEqual(
                {
                    "size": snapshot.entries[relative]["size"],
                    "sha256": snapshot.entries[relative]["sha256"],
                },
                expected_metadata,
            )

            installer.recover_interrupted_transaction(
                skills_dir, skills_dir / installer.SKILL_NAME
            )
            self.assertFalse(stage.exists())
            self.assertFalse((skills_dir / installer.TRANSACTION_NAME).exists())

    @unittest.skipIf(os.name == "nt", "descriptor-relative ancestor race is POSIX-only")
    def test_permission_repair_never_traverses_a_swapped_ancestor(self) -> None:
        for replacement_kind in ("symlink", "directory"):
            with (
                self.subTest(replacement=replacement_kind),
                tempfile.TemporaryDirectory() as tmp,
            ):
                base = Path(tmp)
                managed = base / "managed"
                original_child = managed / "a" / "b"
                original_child.mkdir(parents=True)
                attacker = base / "attacker"
                attacker_child = attacker / "b"
                attacker_child.mkdir(parents=True)
                os.chmod(managed / "a", 0o500)
                os.chmod(original_child, 0o500)
                os.chmod(attacker_child, 0o500)
                snapshot = installer._capture_path_snapshot(managed)
                stashed = base / "captured-a"
                original_open = installer.os.open
                swapped = False

                def swap_before_descendant_open(
                    path, flags, mode=0o777, *, dir_fd=None
                ):
                    nonlocal swapped
                    if path == "b" and dir_fd is not None and not swapped:
                        (managed / "a").rename(stashed)
                        if replacement_kind == "symlink":
                            (managed / "a").symlink_to(
                                attacker, target_is_directory=True
                            )
                        else:
                            attacker.rename(managed / "a")
                        swapped = True
                    if dir_fd is None:
                        return original_open(path, flags, mode)
                    return original_open(path, flags, mode, dir_fd=dir_fd)

                with (
                    mock.patch.object(
                        installer.os, "open", swap_before_descendant_open
                    ),
                    self.assertRaises(RuntimeError),
                ):
                    installer._ensure_snapshot_directories_owner_writable(
                        managed, snapshot
                    )

                self.assertTrue(swapped)
                exposed_child = (
                    attacker_child
                    if replacement_kind == "symlink"
                    else managed / "a" / "b"
                )
                self.assertEqual(stat.S_IMODE(exposed_child.stat().st_mode), 0o500)

    def test_fourteen_byte_copy_temp_derivation_is_bounded_and_recoverable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (
                repo_root,
                skills_dir,
                stage,
                transaction,
                transaction_raw,
                source,
                destination,
            ) = self.make_atomic_copy_fixture(root, transaction_digit="d")
            relative = source.relative_to(repo_root).as_posix()
            temp_relative = installer._copy_temp_relative(
                relative, transaction_raw, 14
            )
            temp_path = stage.joinpath(*temp_relative.split("/"))
            self.assertEqual(len(os.fsencode(temp_path.name)), 14)
            self.assertTrue(temp_path.name.startswith(installer.COPY_TEMP_COMPACT_PREFIX))

            def fail_after_partial_write(descriptor: int, chunk: bytes) -> None:
                written = installer.os.write(descriptor, chunk[:19])
                self.assertEqual(written, 19)
                raise OSError("injected low-NAME_MAX write failure")

            with (
                mock.patch.object(
                    installer, "_copy_temp_component_budget", return_value=14
                ),
                mock.patch.object(
                    installer, "_write_payload_chunk", fail_after_partial_write
                ),
                self.assertRaises(OSError),
            ):
                installer._copy_payload_file_atomic(
                    source,
                    destination,
                    repo_root=repo_root,
                    stage=stage,
                    transaction=transaction,
                    transaction_raw=transaction_raw,
                )

            self.assertFalse(destination.exists())
            self.assertEqual(temp_path.stat().st_size, 19)
            with mock.patch.object(
                installer, "_copy_temp_component_budget", return_value=14
            ):
                snapshot = installer._inspect_owned_stage(
                    stage, transaction, transaction_raw, require_complete=False
                )
                self.assertIn(temp_relative, snapshot.entries)
                installer.recover_interrupted_transaction(
                    skills_dir, skills_dir / installer.SKILL_NAME
                )
            self.assertFalse(stage.exists())
            self.assertFalse((skills_dir / installer.TRANSACTION_NAME).exists())

    def test_copy_temp_namespace_collision_fails_before_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_root = root / "payload-source"
            (repo_root / "nested").mkdir(parents=True)
            first = repo_root / "nested" / "first.bin"
            second = repo_root / "nested" / "second.bin"
            first.write_bytes(b"first")
            second.write_bytes(b"second")
            manifest = installer.payload_manifest(repo_root)
            transaction_id = "c" * 32
            transaction = installer._transaction_record(
                f"{installer.STAGE_PREFIX}123-{transaction_id}",
                f"{installer.QUARANTINE_PREFIX}{transaction_id}",
                transaction_id,
                manifest,
                None,
            )
            raw = installer._json_record_bytes(transaction)
            with (
                mock.patch.object(
                    installer, "_canonical_sha256", return_value="a" * 64
                ),
                self.assertRaisesRegex(RuntimeError, "collides"),
            ):
                installer._expected_copy_temps(transaction, raw, 14)

    def test_recovery_refuses_multiple_bound_copy_temporaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_root = root / "payload-source"
            (repo_root / "nested").mkdir(parents=True)
            (repo_root / "nested" / "first.bin").write_bytes(b"first payload")
            (repo_root / "nested" / "second.bin").write_bytes(b"second payload")
            manifest = installer.payload_manifest(repo_root)
            skills_dir = root / "skills"
            skills_dir.mkdir()
            transaction_id = "9" * 32
            transaction = installer._transaction_record(
                f"{installer.STAGE_PREFIX}123-{transaction_id}",
                f"{installer.QUARANTINE_PREFIX}{transaction_id}",
                transaction_id,
                manifest,
                None,
            )
            transaction_raw = installer._write_json_exclusive(
                skills_dir / installer.TRANSACTION_NAME, transaction
            )
            stage = skills_dir / str(transaction["stage_name"])
            (stage / "nested").mkdir(parents=True)
            installer._write_json_exclusive(
                stage / installer.PROVENANCE_MARKER,
                installer._provenance_record(transaction, transaction_raw),
            )
            expected_temps = installer._expected_copy_temps(
                transaction, transaction_raw, 14
            )
            self.assertEqual(len(expected_temps), 2)
            for relative in expected_temps:
                stage.joinpath(*relative.split("/")).write_bytes(b"partial")
            self.normalize_portable_stage_modes(stage)

            with (
                mock.patch.object(
                    installer, "_copy_temp_component_budget", return_value=14
                ),
                self.assertRaisesRegex(RuntimeError, "more than one"),
            ):
                installer.recover_interrupted_transaction(
                    skills_dir, skills_dir / installer.SKILL_NAME
                )
            self.assertTrue(stage.exists())
            self.assertTrue((skills_dir / installer.TRANSACTION_NAME).exists())
            for relative in expected_temps:
                self.assertEqual(
                    stage.joinpath(*relative.split("/")).read_bytes(), b"partial"
                )

    def test_copy_rejects_digest_not_bound_to_transaction_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (
                repo_root,
                _skills_dir,
                stage,
                transaction,
                transaction_raw,
                source,
                destination,
            ) = self.make_atomic_copy_fixture(Path(tmp), transaction_digit="b")
            with self.assertRaisesRegex(RuntimeError, "persisted record"):
                installer._copy_payload_file_atomic(
                    source,
                    destination,
                    repo_root=repo_root,
                    stage=stage,
                    transaction=transaction,
                    transaction_raw=transaction_raw,
                    transaction_digest="0" * 64,
                    component_name_max=14,
                )
            self.assertFalse(destination.exists())
            self.assertEqual(
                list(destination.parent.glob(f"{installer.COPY_TEMP_COMPACT_PREFIX}*")),
                [],
            )

    def test_recovery_refuses_unbound_temp_or_truncated_final_payload(self) -> None:
        for artifact_kind in ("unbound-temp", "truncated-final"):
            with self.subTest(artifact=artifact_kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (
                    repo_root,
                    skills_dir,
                    stage,
                    transaction,
                    transaction_raw,
                    source,
                    destination,
                ) = self.make_atomic_copy_fixture(root, transaction_digit="e")
                del repo_root, transaction, transaction_raw, source
                if artifact_kind == "unbound-temp":
                    artifact = stage / (
                        f"{installer.COPY_TEMP_COMPACT_PREFIX}not-transaction-bound"
                    )
                    artifact.write_bytes(b"user bytes")
                else:
                    artifact = destination
                    artifact.write_bytes(b"truncated expected pathname")

                with self.assertRaises(RuntimeError):
                    installer.recover_interrupted_transaction(
                        skills_dir, skills_dir / installer.SKILL_NAME
                    )

                self.assertEqual(
                    artifact.read_bytes(),
                    b"user bytes"
                    if artifact_kind == "unbound-temp"
                    else b"truncated expected pathname",
                )
                self.assertTrue(stage.exists())
                self.assertTrue((skills_dir / installer.TRANSACTION_NAME).exists())

    def test_retry_recovers_exact_torn_completion_publication(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            contract = installer.load_payload_contract(ROOT)
            plan = installer.build_install_payload_plan(ROOT, contract)
            manifest = plan.installed_contract.file_manifest()
            transaction_id = "8" * 32
            transaction = installer._transaction_record(
                f"{installer.STAGE_PREFIX}123-{transaction_id}",
                f"{installer.QUARANTINE_PREFIX}{transaction_id}",
                transaction_id,
                manifest,
                None,
            )
            transaction_raw = installer._write_json_exclusive(
                skills_dir / installer.TRANSACTION_NAME, transaction
            )
            stage = skills_dir / str(transaction["stage_name"])
            stage.mkdir(mode=0o700)
            installer._write_json_exclusive(
                stage / installer.PROVENANCE_MARKER,
                installer._provenance_record(transaction, transaction_raw),
            )
            installer._copy_declared_payload(
                ROOT,
                stage,
                contract.declared,
                installer.payload_copy_function(ROOT, plan),
            )
            expected_raw = installer._json_record_bytes(
                installer._completion_marker_record(manifest)
            )
            (stage / installer.COMPLETION_MARKER).write_bytes(
                expected_raw[: len(expected_raw) // 2]
            )
            self.normalize_portable_stage_modes(stage)

            result = self.run_installer(skills_dir)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
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

    def test_kill_during_atomic_write_recovers_only_the_bound_temp_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skills_dir = root / "skills"
            skills_dir.mkdir()
            ready = root / "atomic-write-paused"
            process = self.start_controlled_installer(
                PAUSE_DURING_ATOMIC_WRITE, skills_dir, ready
            )
            self.terminate_at_pause(process, ready)

            transaction, transaction_raw = installer._load_transaction(skills_dir)
            stage = skills_dir / str(transaction["stage_name"])
            expected_temps = installer._expected_copy_temps(
                transaction,
                transaction_raw,
                installer._copy_temp_component_budget(stage),
            )
            snapshot = installer._inspect_owned_stage(
                stage, transaction, transaction_raw, require_complete=False
            )
            present_temps = set(snapshot.entries) & set(expected_temps)
            self.assertEqual(len(present_temps), 1)
            temp_relative = present_temps.pop()
            target_relative = expected_temps[temp_relative]
            temp_size = int(snapshot.entries[temp_relative]["size"])
            expected_size = int(transaction["payload_manifest"][target_relative]["size"])
            self.assertGreater(temp_size, 0)
            self.assertLessEqual(temp_size, expected_size)
            self.assertFalse(stage.joinpath(*target_relative.split("/")).exists())
            self.assertFalse((skills_dir / installer.SKILL_NAME).exists())

            retry = self.run_installer(skills_dir)
            self.assertEqual(retry.returncode, 0, retry.stdout + retry.stderr)
            self.assert_completed(skills_dir / installer.SKILL_NAME)
            self.assertFalse(stage.exists())

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
