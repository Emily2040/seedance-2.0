"""Output-collision policy for the frame-extraction CLI."""

from __future__ import annotations

import contextlib
import concurrent.futures
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import extract_last_frame as extractor  # noqa: E402


class OutputCollisionCliTests(unittest.TestCase):
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

    def test_existing_output_is_refused_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "accepted-take.mp4.last.png"
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

    def test_help_states_that_refusal_is_the_default(self) -> None:
        result, stdout, stderr = self.invoke("--help")

        self.assertEqual(result, 0, stdout + stderr)
        self.assertIn("--force", stdout)
        self.assertIn("default behavior refuses", " ".join(stdout.split()))

    def test_force_allows_explicit_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "approved-frame.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"old frame")

            def replace_output(_ffmpeg: str, _clip: Path, destination: Path, _first: bool) -> int:
                destination.write_bytes(b"new frame")
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
            self.assertEqual(output.read_bytes(), b"new frame")

    def test_default_output_path_is_also_protected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            clip = Path(temp_dir) / "accepted-take.mp4"
            output = clip.with_suffix(clip.suffix + ".last.png")
            clip.write_bytes(b"clip")
            output.write_bytes(b"approved frame")

            with mock.patch.object(extractor, "run_ffmpeg", return_value=0) as run:
                result, stdout, stderr = self.invoke(
                    str(clip), "--ffmpeg", "fake-ffmpeg"
                )

            self.assertEqual(result, 1, stdout + stderr)
            run.assert_not_called()
            self.assertEqual(output.read_bytes(), b"approved frame")

    def test_new_output_is_reserved_before_ffmpeg_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "new-frame.png"
            clip.write_bytes(b"clip")

            def fill_reservation(_ffmpeg: str, _clip: Path, destination: Path, _first: bool) -> int:
                self.assertTrue(destination.exists())
                self.assertEqual(destination.read_bytes(), b"")
                destination.write_bytes(b"frame")
                return 0

            with mock.patch.object(extractor, "run_ffmpeg", side_effect=fill_reservation):
                result, stdout, stderr = self.invoke(
                    str(clip), "--ffmpeg", "fake-ffmpeg", "--output", str(output)
                )

            self.assertEqual(result, 0, stdout + stderr)
            self.assertEqual(output.read_bytes(), b"frame")

    def test_failed_extraction_removes_its_own_reservation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "failed-frame.png"
            clip.write_bytes(b"clip")

            def fail_after_partial_write(
                _ffmpeg: str, _clip: Path, destination: Path, _first: bool
            ) -> int:
                destination.write_bytes(b"partial frame")
                return 1

            with mock.patch.object(extractor, "run_ffmpeg", side_effect=fail_after_partial_write):
                result, stdout, stderr = self.invoke(
                    str(clip), "--ffmpeg", "fake-ffmpeg", "--output", str(output)
                )

            self.assertEqual(result, 1, stdout + stderr)
            self.assertFalse(output.exists())

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


class AtomicReservationTests(unittest.TestCase):
    def test_two_agents_cannot_claim_the_same_new_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "shared-frame.png"

            def claim() -> bool:
                try:
                    return extractor.reserve_output(output, force=False)
                except extractor.OutputPolicyError:
                    return False

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _index: claim(), range(2)))

            self.assertEqual(sorted(results), [False, True])
            self.assertTrue(output.exists())

    def test_force_does_not_create_a_reservation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "frame.png"

            reserved = extractor.reserve_output(output, force=True)

            self.assertFalse(reserved)
            self.assertFalse(output.exists())


class OutputPolicyDocumentationTests(unittest.TestCase):
    def test_continuation_handoff_documents_explicit_replacement(self) -> None:
        root = Path(__file__).resolve().parents[1]
        handoff = (root / "references" / "continuation-handoff.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("refuses to replace an existing output image", handoff)
        self.assertIn("`--force`", handoff)


if __name__ == "__main__":
    unittest.main()

