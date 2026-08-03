"""Real-FFmpeg coverage for the frame extraction helper.

The metadata-only ``--self-test`` protects the observation-record wiring.  It
cannot prove which decoded frame FFmpeg wrote, so these tests generate tiny
clips and compare the helper's output with an independent full-decode/reverse
oracle.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import extract_last_frame as extractor  # noqa: E402


FFMPEG = os.environ.get("SEEDANCE_TEST_FFMPEG") or shutil.which("ffmpeg")


class FfmpegAvailabilityTests(unittest.TestCase):
    def test_ci_does_not_silently_skip_real_ffmpeg_coverage(self) -> None:
        if os.environ.get("CI"):
            self.assertIsNotNone(
                FFMPEG,
                "CI must provide ffmpeg so frame-selection integration tests do not false-green",
            )
        if os.environ.get("GITHUB_ACTIONS"):
            configured = os.environ.get("SEEDANCE_TEST_FFMPEG")
            self.assertEqual(
                os.environ.get("SEEDANCE_CI_FFMPEG_PROVISIONED"),
                "1",
                "CI must provision and verify ffmpeg before starting the unit-test step",
            )
            self.assertTrue(
                configured,
                "CI must export the verified ffmpeg path so integration tests cannot false-green",
            )
            self.assertTrue(
                Path(str(configured)).is_file() and os.access(str(configured), os.X_OK),
                f"CI-provisioned ffmpeg is not an executable file: {configured}",
            )


@unittest.skipUnless(
    FFMPEG,
    "real-FFmpeg frame tests require ffmpeg on PATH or SEEDANCE_TEST_FFMPEG",
)
class RealFfmpegFrameTests(unittest.TestCase):
    def run_ffmpeg(self, *args: str) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [str(FFMPEG), "-hide_banner", "-loglevel", "error", *args],
            check=True,
            capture_output=True,
        )

    def raw_rgb(self, image: Path) -> bytes:
        return self.run_ffmpeg(
            "-i", str(image), "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"
        ).stdout

    def true_last_frame(self, clip: Path, output: Path) -> None:
        # ``reverse`` must decode the complete stream before emitting its first
        # frame, making that output an independent oracle for the final frame.
        self.run_ffmpeg(
            "-y", "-i", str(clip), "-vf", "reverse", "-frames:v", "1", str(output)
        )

    def assert_true_last_frame(
        self,
        clip: Path,
        actual: Path,
        expected: Path,
        *,
        force: bool = False,
    ) -> None:
        self.assertEqual(
            extractor.run_ffmpeg(
                str(FFMPEG), clip, actual, first=False, force=force
            ),
            0,
        )
        self.true_last_frame(clip, expected)
        self.assertEqual(
            self.raw_rgb(actual),
            self.raw_rgb(expected),
            "last-frame extraction must match the stream's final decoded frame",
        )

    def make_color_transition(self, clip: Path) -> None:
        self.run_ffmpeg(
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:size=48x32:rate=10:duration=0.4",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:size=48x32:rate=10:duration=0.2",
            "-filter_complex",
            "[0:v][1:v]concat=n=2:v=1:a=0,format=yuv420p",
            "-an",
            "-c:v",
            "mpeg4",
            "-q:v",
            "2",
            str(clip),
        )

    def test_one_frame_clip_returns_its_only_frame(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            clip = root / "one-frame.mp4"
            actual = root / "actual.png"
            expected = root / "expected.png"
            self.run_ffmpeg(
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=green:size=48x32:rate=25",
                "-frames:v",
                "1",
                "-an",
                "-c:v",
                "mpeg4",
                "-q:v",
                "2",
                "-pix_fmt",
                "yuv420p",
                str(clip),
            )

            self.assert_true_last_frame(clip, actual, expected)

    def test_color_transition_returns_the_final_color_frame(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            clip = root / "blue-to-red.mp4"
            actual = root / "actual.png"
            expected = root / "expected.png"
            self.make_color_transition(clip)

            self.assert_true_last_frame(clip, actual, expected)

    def test_moving_clip_returns_the_true_final_frame(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            clip = root / "moving.mp4"
            actual = root / "actual.png"
            expected = root / "expected.png"
            self.run_ffmpeg(
                "-y",
                "-f",
                "lavfi",
                "-i",
                "testsrc2=size=48x32:rate=10:duration=1",
                "-an",
                "-c:v",
                "mpeg4",
                "-q:v",
                "2",
                "-pix_fmt",
                "yuv420p",
                str(clip),
            )

            self.assert_true_last_frame(clip, actual, expected)

    def test_existing_output_is_replaced_with_the_true_final_frame(self) -> None:
        if (
            os.name == "posix"
            and not extractor._posix_descriptor_xattrs_supported()
        ):
            self.skipTest("complete Linux extended-metadata visibility unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            clip = root / "blue-to-red.mp4"
            actual = root / "actual.png"
            expected = root / "expected.png"
            self.make_color_transition(clip)
            sentinel = b"pre-existing output that must be replaced"
            actual.write_bytes(sentinel)

            self.assert_true_last_frame(clip, actual, expected, force=True)
            self.assertNotEqual(actual.read_bytes(), sentinel)


if __name__ == "__main__":
    unittest.main()
