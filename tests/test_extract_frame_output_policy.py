"""Fail-closed and atomic output policy for the frame-extraction CLI."""

from __future__ import annotations

import concurrent.futures
import contextlib
import io
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import extract_last_frame as extractor  # noqa: E402


class OutputPolicyTestCase(unittest.TestCase):
    def invoke(self, *arguments: str) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        argv = ["extract_last_frame.py", *arguments]
        with mock.patch.object(sys, "argv", argv):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                try:
                    result = extractor.main()
                except SystemExit as exc:
                    result = int(exc.code)
        return result, stdout.getvalue(), stderr.getvalue()

    def stage_paths(self, root: Path) -> list[Path]:
        return list(root.glob(".*.atomic-*"))


class OutputCollisionCliTests(OutputPolicyTestCase):
    def test_existing_output_is_refused_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "approved-frame.png"
            clip.write_bytes(b"clip")
            sentinel = b"approved frame that must survive"
            output.write_bytes(sentinel)

            with mock.patch.object(extractor, "run_ffmpeg", return_value=0) as run:
                result, stdout, stderr = self.invoke(
                    str(clip), "--ffmpeg", "fake-ffmpeg", "--output", str(output)
                )

            self.assertEqual(result, 1, stdout + stderr)
            run.assert_not_called()
            self.assertEqual(output.read_bytes(), sentinel)
            self.assertIn("output already exists", stdout)
            self.assertIn("--force", stdout)
            self.assertEqual(self.stage_paths(root), [])

    def test_help_states_that_refusal_is_the_default(self) -> None:
        result, stdout, stderr = self.invoke("--help")

        self.assertEqual(result, 0, stdout + stderr)
        self.assertIn("--force", stdout)
        self.assertIn("default behavior refuses", " ".join(stdout.split()))

    def test_default_output_path_is_also_protected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            clip = Path(temp_dir) / "accepted-take.mp4"
            output = clip.with_suffix(clip.suffix + ".last.png")
            clip.write_bytes(b"clip")
            output.write_bytes(b"approved frame")

            with mock.patch.object(extractor, "run_ffmpeg", return_value=0) as run:
                result, stdout, stderr = self.invoke(str(clip), "--ffmpeg", "fake-ffmpeg")

            self.assertEqual(result, 1, stdout + stderr)
            run.assert_not_called()
            self.assertEqual(output.read_bytes(), b"approved frame")

    def test_output_is_not_visible_until_complete_stage_is_published(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "new-frame.png"
            clip.write_bytes(b"clip")

            def write_stage(_ffmpeg: str, _clip: Path, stage: Path, _first: bool) -> int:
                self.assertFalse(output.exists())
                self.assertTrue(stage.exists())
                self.assertEqual(stage.read_bytes(), b"")
                self.assertEqual(stage.suffix, output.suffix)
                stage.write_bytes(b"complete frame")
                self.assertFalse(output.exists())
                return 0

            with mock.patch.object(extractor, "run_ffmpeg", side_effect=write_stage):
                result, stdout, stderr = self.invoke(
                    str(clip), "--ffmpeg", "fake-ffmpeg", "--output", str(output)
                )

            self.assertEqual(result, 0, stdout + stderr)
            self.assertEqual(output.read_bytes(), b"complete frame")
            self.assertEqual(self.stage_paths(root), [])

    def test_failed_extraction_removes_only_its_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "failed-frame.png"
            clip.write_bytes(b"clip")

            def fail_after_partial_write(
                _ffmpeg: str, _clip: Path, stage: Path, _first: bool
            ) -> int:
                stage.write_bytes(b"partial frame")
                return 1

            with mock.patch.object(extractor, "run_ffmpeg", side_effect=fail_after_partial_write):
                result, stdout, stderr = self.invoke(
                    str(clip), "--ffmpeg", "fake-ffmpeg", "--output", str(output)
                )

            self.assertEqual(result, 1, stdout + stderr)
            self.assertFalse(output.exists())
            self.assertEqual(self.stage_paths(root), [])

    def test_force_replaces_only_after_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "approved-frame.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"old frame")

            def replace_output(_ffmpeg: str, _clip: Path, stage: Path, _first: bool) -> int:
                self.assertEqual(output.read_bytes(), b"old frame")
                stage.write_bytes(b"new complete frame")
                self.assertEqual(output.read_bytes(), b"old frame")
                return 0

            with mock.patch.object(extractor, "run_ffmpeg", side_effect=replace_output):
                result, stdout, stderr = self.invoke(
                    str(clip),
                    "--ffmpeg",
                    "fake-ffmpeg",
                    "--output",
                    str(output),
                    "--force",
                )

            self.assertEqual(result, 0, stdout + stderr)
            self.assertEqual(output.read_bytes(), b"new complete frame")
            self.assertEqual(self.stage_paths(root), [])

    def test_force_failure_preserves_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "approved-frame.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"old frame")

            def fail(_ffmpeg: str, _clip: Path, stage: Path, _first: bool) -> int:
                stage.write_bytes(b"partial replacement")
                return 1

            with mock.patch.object(extractor, "run_ffmpeg", side_effect=fail):
                result, stdout, stderr = self.invoke(
                    str(clip),
                    "--ffmpeg",
                    "fake-ffmpeg",
                    "--output",
                    str(output),
                    "--force",
                )

            self.assertEqual(result, 1, stdout + stderr)
            self.assertEqual(output.read_bytes(), b"old frame")
            self.assertEqual(self.stage_paths(root), [])

    def test_force_cannot_replace_the_input_clip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            clip = Path(temp_dir) / "accepted-take.mp4"
            clip.write_bytes(b"clip")

            with mock.patch.object(extractor, "run_ffmpeg", return_value=0) as run:
                result, stdout, stderr = self.invoke(
                    str(clip),
                    "--ffmpeg",
                    "fake-ffmpeg",
                    "--output",
                    str(clip),
                    "--force",
                )

            self.assertEqual(result, 1, stdout + stderr)
            run.assert_not_called()
            self.assertEqual(clip.read_bytes(), b"clip")
            self.assertIn("must differ from the input clip", stdout)

    def test_hardlink_alias_of_input_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "input-alias.png"
            clip.write_bytes(b"clip")
            try:
                os.link(clip, output)
            except OSError as exc:
                self.skipTest(f"hard links unavailable: {exc}")

            with mock.patch.object(extractor, "run_ffmpeg", return_value=0) as run:
                result, stdout, stderr = self.invoke(
                    str(clip),
                    "--ffmpeg",
                    "fake-ffmpeg",
                    "--output",
                    str(output),
                    "--force",
                )

            self.assertEqual(result, 1, stdout + stderr)
            run.assert_not_called()
            self.assertEqual(clip.read_bytes(), b"clip")
            self.assertEqual(output.read_bytes(), b"clip")

    def test_force_refuses_directory_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "frame.png"
            clip.write_bytes(b"clip")
            output.mkdir()
            marker = output / "keep.txt"
            marker.write_bytes(b"keep")

            with mock.patch.object(extractor, "run_ffmpeg", return_value=0) as run:
                result, stdout, stderr = self.invoke(
                    str(clip),
                    "--ffmpeg",
                    "fake-ffmpeg",
                    "--output",
                    str(output),
                    "--force",
                )

            self.assertEqual(result, 1, stdout + stderr)
            run.assert_not_called()
            self.assertEqual(marker.read_bytes(), b"keep")

    def test_dangling_link_counts_as_an_existing_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "dangling.png"
            clip.write_bytes(b"clip")
            try:
                output.symlink_to(root / "missing-target.png")
            except OSError as exc:
                self.skipTest(f"symbolic links unavailable: {exc}")

            with mock.patch.object(extractor, "run_ffmpeg", return_value=0) as run:
                result, stdout, stderr = self.invoke(
                    str(clip), "--ffmpeg", "fake-ffmpeg", "--output", str(output)
                )

            self.assertEqual(result, 1, stdout + stderr)
            run.assert_not_called()
            self.assertTrue(os.path.lexists(output))

    def test_missing_output_directory_fails_before_ffmpeg(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "missing" / "frame.png"
            clip.write_bytes(b"clip")

            with mock.patch.object(extractor, "run_ffmpeg", return_value=0) as run:
                result, stdout, stderr = self.invoke(
                    str(clip), "--ffmpeg", "fake-ffmpeg", "--output", str(output)
                )

            self.assertEqual(result, 1, stdout + stderr)
            run.assert_not_called()
            self.assertIn("output directory not found", stdout)


class AdversarialPublicationTests(OutputPolicyTestCase):
    def test_late_destination_collision_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "shared-frame.png"
            clip.write_bytes(b"clip")

            def collide(_ffmpeg: str, _clip: Path, stage: Path, _first: bool) -> int:
                stage.write_bytes(b"complete generated frame")
                output.write_bytes(b"late winner")
                return 0

            with mock.patch.object(extractor, "run_ffmpeg", side_effect=collide):
                result, stdout, stderr = self.invoke(
                    str(clip), "--ffmpeg", "fake-ffmpeg", "--output", str(output)
                )

            self.assertEqual(result, 1, stdout + stderr)
            self.assertEqual(output.read_bytes(), b"late winner")
            self.assertIn("appeared during extraction", stdout)
            self.assertEqual(self.stage_paths(root), [])

    def test_two_concurrent_writers_publish_exactly_one_complete_frame(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "shared-frame.png"
            clip.write_bytes(b"clip")
            barrier = threading.Barrier(2)
            payloads: dict[int, bytes] = {}
            lock = threading.Lock()

            def render(_ffmpeg: str, _clip: Path, stage: Path, _first: bool) -> int:
                payload = f"complete-{threading.get_ident()}".encode()
                with lock:
                    payloads[threading.get_ident()] = payload
                stage.write_bytes(payload)
                barrier.wait(timeout=10)
                return 0

            def attempt() -> bool:
                try:
                    return extractor.extract_frame("fake", clip, output, False, False) == 0
                except extractor.OutputPolicyError:
                    return False

            with mock.patch.object(extractor, "run_ffmpeg", side_effect=render):
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                    results = list(pool.map(lambda _index: attempt(), range(2)))

            self.assertEqual(sorted(results), [False, True])
            self.assertIn(output.read_bytes(), payloads.values())
            self.assertEqual(self.stage_paths(root), [])

    def test_swapped_stage_hardlink_is_not_published_or_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "frame.png"
            victim = root / "victim.txt"
            clip.write_bytes(b"clip")
            victim.write_bytes(b"victim must survive")
            swapped: list[Path] = []

            def swap(_ffmpeg: str, _clip: Path, stage: Path, _first: bool) -> int:
                stage.unlink()
                try:
                    os.link(victim, stage)
                except OSError as exc:
                    self.skipTest(f"hard links unavailable: {exc}")
                swapped.append(stage)
                return 0

            with mock.patch.object(extractor, "run_ffmpeg", side_effect=swap):
                result, stdout, stderr = self.invoke(
                    str(clip), "--ffmpeg", "fake-ffmpeg", "--output", str(output)
                )

            self.assertEqual(result, 1, stdout + stderr)
            self.assertFalse(output.exists())
            self.assertEqual(victim.read_bytes(), b"victim must survive")
            self.assertTrue(swapped[0].exists())
            self.assertEqual(swapped[0].read_bytes(), b"victim must survive")
            self.assertIn("leaving unexpected path untouched", stderr)

    def test_swapped_stage_directory_is_not_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "frame.png"
            clip.write_bytes(b"clip")
            swapped: list[Path] = []

            def swap(_ffmpeg: str, _clip: Path, stage: Path, _first: bool) -> int:
                stage.unlink()
                stage.mkdir()
                (stage / "keep.txt").write_bytes(b"keep")
                swapped.append(stage)
                return 0

            with mock.patch.object(extractor, "run_ffmpeg", side_effect=swap):
                result, stdout, stderr = self.invoke(
                    str(clip), "--ffmpeg", "fake-ffmpeg", "--output", str(output)
                )

            self.assertEqual(result, 1, stdout + stderr)
            self.assertFalse(output.exists())
            self.assertEqual((swapped[0] / "keep.txt").read_bytes(), b"keep")
            self.assertIn("leaving unexpected path untouched", stderr)

    def test_force_publish_error_preserves_old_output_and_cleans_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "approved-frame.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"old frame")

            def render(_ffmpeg: str, _clip: Path, stage: Path, _first: bool) -> int:
                stage.write_bytes(b"new complete frame")
                return 0

            with mock.patch.object(extractor, "run_ffmpeg", side_effect=render):
                with mock.patch.object(extractor.os, "replace", side_effect=PermissionError("locked")):
                    result, stdout, stderr = self.invoke(
                        str(clip),
                        "--ffmpeg",
                        "fake-ffmpeg",
                        "--output",
                        str(output),
                        "--force",
                    )

            self.assertEqual(result, 1, stdout + stderr)
            self.assertEqual(output.read_bytes(), b"old frame")
            self.assertEqual(self.stage_paths(root), [])

    def test_force_rechecks_a_late_input_alias(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "approved-frame.png"
            clip.write_bytes(b"clip must survive")
            output.write_bytes(b"old frame")

            def collide(_ffmpeg: str, _clip: Path, stage: Path, _first: bool) -> int:
                stage.write_bytes(b"new complete frame")
                output.unlink()
                try:
                    os.link(clip, output)
                except OSError as exc:
                    self.skipTest(f"hard links unavailable: {exc}")
                return 0

            with mock.patch.object(extractor, "run_ffmpeg", side_effect=collide):
                result, stdout, stderr = self.invoke(
                    str(clip),
                    "--ffmpeg",
                    "fake-ffmpeg",
                    "--output",
                    str(output),
                    "--force",
                )

            self.assertEqual(result, 1, stdout + stderr)
            self.assertEqual(clip.read_bytes(), b"clip must survive")
            self.assertTrue(os.path.samefile(clip, output))
            self.assertEqual(self.stage_paths(root), [])


class OutputPolicyDocumentationTests(unittest.TestCase):
    def test_policy_and_atomic_publication_are_documented(self) -> None:
        root = Path(__file__).resolve().parents[1]
        handoff = (root / "references" / "continuation-handoff.md").read_text(encoding="utf-8")
        changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")

        self.assertIn("refuses to replace an existing output image", handoff)
        self.assertIn("`--force`", handoff)
        self.assertIn("atomically publishes the complete frame", handoff)
        self.assertIn("Late destination collisions are preserved", changelog)


if __name__ == "__main__":
    unittest.main()
