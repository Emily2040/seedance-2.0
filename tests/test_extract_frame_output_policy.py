"""Fail-closed and atomic output policy for the frame-extraction CLI."""

from __future__ import annotations

import concurrent.futures
import contextlib
import io
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import unittest
import zlib
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import extract_last_frame as extractor  # noqa: E402


FFMPEG = os.environ.get("SEEDANCE_TEST_FFMPEG") or shutil.which("ffmpeg")
REPOSITORY = Path(__file__).resolve().parents[1]
WORKSPACE_TEMP_ROOT = REPOSITORY / "work"
_system_temporary_directory = tempfile.TemporaryDirectory


class _WorkspaceTempfiles:
    """Keep Win32 handle-rename tests inside the sandbox's native workspace."""

    @staticmethod
    def TemporaryDirectory(*args: object, **kwargs: object) -> tempfile.TemporaryDirectory[str]:
        WORKSPACE_TEMP_ROOT.mkdir(exist_ok=True)
        kwargs.setdefault("dir", WORKSPACE_TEMP_ROOT)
        return _system_temporary_directory(*args, **kwargs)


tempfile = _WorkspaceTempfiles()


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

            with mock.patch.object(extractor, "render_frame_png", return_value=b"new") as render:
                result, stdout, stderr = self.invoke(
                    str(clip), "--ffmpeg", "fake-ffmpeg", "--output", str(output)
                )

            self.assertEqual(result, 1, stdout + stderr)
            render.assert_not_called()
            self.assertEqual(output.read_bytes(), sentinel)
            self.assertIn("output already exists", stdout)
            self.assertIn("--force", stdout)
            self.assertEqual(self.stage_paths(root), [])

    def test_legacy_run_ffmpeg_entry_point_cannot_bypass_no_overwrite(self) -> None:
        """Imported callers receive the same default refusal as the CLI."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "approved-frame.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"approved frame")

            with mock.patch.object(extractor, "render_frame_png") as render:
                result = extractor.run_ffmpeg("fake-ffmpeg", clip, output, first=False)

            self.assertEqual(result, 1)
            render.assert_not_called()
            self.assertEqual(output.read_bytes(), b"approved frame")
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

            with mock.patch.object(extractor, "render_frame_png", return_value=b"new") as render:
                result, stdout, stderr = self.invoke(str(clip), "--ffmpeg", "fake-ffmpeg")

            self.assertEqual(result, 1, stdout + stderr)
            render.assert_not_called()
            self.assertEqual(output.read_bytes(), b"approved frame")

    def test_output_is_not_visible_during_full_decode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "new-frame.png"
            clip.write_bytes(b"clip")

            def render(_ffmpeg: str, _clip: Path, _first: bool) -> bytes:
                self.assertFalse(output.exists())
                self.assertEqual(self.stage_paths(root), [])
                return b"complete frame"

            with mock.patch.object(extractor, "render_frame_png", side_effect=render):
                result, stdout, stderr = self.invoke(
                    str(clip), "--ffmpeg", "fake-ffmpeg", "--output", str(output)
                )

            self.assertEqual(result, 0, stdout + stderr)
            self.assertEqual(output.read_bytes(), b"complete frame")
            self.assertEqual(self.stage_paths(root), [])

    def test_failed_decode_never_creates_final_or_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "failed-frame.png"
            clip.write_bytes(b"clip")

            with mock.patch.object(
                extractor,
                "render_frame_png",
                side_effect=extractor.FrameExtractionError("decoder failed"),
            ):
                result, stdout, stderr = self.invoke(
                    str(clip), "--ffmpeg", "fake-ffmpeg", "--output", str(output)
                )

            self.assertEqual(result, 1, stdout + stderr)
            self.assertIn("decoder failed", stdout)
            self.assertFalse(output.exists())
            self.assertEqual(self.stage_paths(root), [])

    def test_force_replaces_only_after_successful_decode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "approved-frame.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"old frame")

            def render(_ffmpeg: str, _clip: Path, _first: bool) -> bytes:
                self.assertEqual(output.read_bytes(), b"old frame")
                return b"new complete frame"

            with mock.patch.object(extractor, "render_frame_png", side_effect=render):
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

    def test_force_decode_failure_preserves_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "approved-frame.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"old frame")

            with mock.patch.object(
                extractor,
                "render_frame_png",
                side_effect=extractor.FrameExtractionError("decoder failed"),
            ):
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

            with mock.patch.object(extractor, "render_frame_png", return_value=b"new") as render:
                result, stdout, stderr = self.invoke(
                    str(clip),
                    "--ffmpeg",
                    "fake-ffmpeg",
                    "--output",
                    str(clip),
                    "--force",
                )

            self.assertEqual(result, 1, stdout + stderr)
            render.assert_not_called()
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

            with mock.patch.object(extractor, "render_frame_png", return_value=b"new") as render:
                result, stdout, stderr = self.invoke(
                    str(clip),
                    "--ffmpeg",
                    "fake-ffmpeg",
                    "--output",
                    str(output),
                    "--force",
                )

            self.assertEqual(result, 1, stdout + stderr)
            render.assert_not_called()
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

            with mock.patch.object(extractor, "render_frame_png", return_value=b"new") as render:
                result, stdout, stderr = self.invoke(
                    str(clip),
                    "--ffmpeg",
                    "fake-ffmpeg",
                    "--output",
                    str(output),
                    "--force",
                )

            self.assertEqual(result, 1, stdout + stderr)
            render.assert_not_called()
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

            with mock.patch.object(extractor, "render_frame_png", return_value=b"new") as render:
                result, stdout, stderr = self.invoke(
                    str(clip), "--ffmpeg", "fake-ffmpeg", "--output", str(output)
                )

            self.assertEqual(result, 1, stdout + stderr)
            render.assert_not_called()
            self.assertTrue(os.path.lexists(output))

    def test_missing_output_directory_fails_before_decode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "missing" / "frame.png"
            clip.write_bytes(b"clip")

            with mock.patch.object(extractor, "render_frame_png", return_value=b"new") as render:
                result, stdout, stderr = self.invoke(
                    str(clip), "--ffmpeg", "fake-ffmpeg", "--output", str(output)
                )

            self.assertEqual(result, 1, stdout + stderr)
            render.assert_not_called()
            self.assertIn("output directory not found", stdout)

    def test_unsupported_output_suffix_fails_before_decode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "frame.exe"
            clip.write_bytes(b"clip")

            with mock.patch.object(extractor, "render_frame_png", return_value=b"new") as render:
                result, stdout, stderr = self.invoke(
                    str(clip), "--ffmpeg", "fake-ffmpeg", "--output", str(output)
                )

            self.assertEqual(result, 1, stdout + stderr)
            render.assert_not_called()
            self.assertIn("unsupported output image suffix", stdout)

    @unittest.skipUnless(os.name == "nt", "Windows filename aliases are platform-specific")
    def test_windows_device_and_normalization_aliases_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            clip.write_bytes(b"clip")
            unsafe_names = (
                "CON.png",
                "nul.PNG",
                "AUX.txt",
                "COM1.jpg",
                "LPT9.png",
                "frame.png.",
                "frame.png ",
                "frame.png:alternate",
            )

            for name in unsafe_names:
                with self.subTest(name=name):
                    with mock.patch.object(
                        extractor, "render_frame_png", return_value=b"new"
                    ) as render:
                        result, stdout, stderr = self.invoke(
                            str(clip),
                            "--ffmpeg",
                            "fake-ffmpeg",
                            "--output",
                            str(root / name),
                        )
                    self.assertEqual(result, 1, stdout + stderr)
                    render.assert_not_called()
                    self.assertIn("unsafe Windows output filename", stdout)


class AdversarialPublicationTests(OutputPolicyTestCase):
    def test_late_destination_collision_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "shared-frame.png"
            clip.write_bytes(b"clip")

            def collide(_ffmpeg: str, _clip: Path, _first: bool) -> bytes:
                output.write_bytes(b"late winner")
                return b"complete generated frame"

            with mock.patch.object(extractor, "render_frame_png", side_effect=collide):
                result, stdout, stderr = self.invoke(
                    str(clip), "--ffmpeg", "fake-ffmpeg", "--output", str(output)
                )

            self.assertEqual(result, 1, stdout + stderr)
            self.assertEqual(output.read_bytes(), b"late winner")
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

            def render(_ffmpeg: str, _clip: Path, _first: bool) -> bytes:
                payload = f"complete-{threading.get_ident()}".encode()
                with lock:
                    payloads[threading.get_ident()] = payload
                barrier.wait(timeout=10)
                return payload

            def attempt() -> bool:
                try:
                    return extractor.extract_frame("fake", clip, output, False, False) == 0
                except extractor.OutputPolicyError:
                    return False

            with mock.patch.object(extractor, "render_frame_png", side_effect=render):
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                    results = list(pool.map(lambda _index: attempt(), range(2)))

            self.assertEqual(sorted(results), [False, True])
            self.assertIn(output.read_bytes(), payloads.values())
            self.assertEqual(self.stage_paths(root), [])

    @unittest.skipUnless(os.name == "nt", "exclusive handle attack replay is Windows-specific")
    def test_prewrite_hardlink_swap_cannot_redirect_generated_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "frame.png"
            victim = root / "victim.bin"
            clip.write_bytes(b"clip")
            victim.write_bytes(b"VICTIM")
            original_write = extractor._write_output_stage
            swap_attempted = False

            def attack(stage: extractor.OutputStage, content: bytes) -> None:
                nonlocal swap_attempted
                swap_attempted = True
                with self.assertRaises(OSError):
                    stage.path.unlink()
                self.assertEqual(victim.read_bytes(), b"VICTIM")
                original_write(stage, content)

            with mock.patch.object(extractor, "render_frame_png", return_value=b"GENERATED_FRAME"):
                with mock.patch.object(extractor, "_write_output_stage", side_effect=attack):
                    result, stdout, stderr = self.invoke(
                        str(clip), "--ffmpeg", "fake-ffmpeg", "--output", str(output)
                    )

            self.assertTrue(swap_attempted)
            self.assertEqual(result, 0, stdout + stderr)
            self.assertEqual(victim.read_bytes(), b"VICTIM")
            self.assertEqual(output.read_bytes(), b"GENERATED_FRAME")

    @unittest.skipUnless(os.name == "nt", "locked-handle link replay is Windows-specific")
    def test_verify_to_publish_swap_is_blocked_by_exclusive_handle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "frame.png"
            victim = root / "victim.bin"
            clip.write_bytes(b"clip")
            victim.write_bytes(b"VICTIM_PAYLOAD")
            original_link = extractor.os.link
            swap_attempted = False

            def attack(source: Path, target: Path) -> None:
                nonlocal swap_attempted
                swap_attempted = True
                with self.assertRaises(OSError):
                    Path(source).unlink()
                original_link(source, target)

            with mock.patch.object(extractor, "render_frame_png", return_value=b"GENERATED_FRAME"):
                with mock.patch.object(extractor.os, "link", side_effect=attack):
                    result, stdout, stderr = self.invoke(
                        str(clip), "--ffmpeg", "fake-ffmpeg", "--output", str(output)
                    )

            self.assertTrue(swap_attempted)
            self.assertEqual(result, 0, stdout + stderr)
            self.assertEqual(output.read_bytes(), b"GENERATED_FRAME")
            self.assertFalse(os.path.samefile(output, victim))
            self.assertEqual(victim.read_bytes(), b"VICTIM_PAYLOAD")

    @unittest.skipUnless(os.name == "nt", "locked-handle collision replay is Windows-specific")
    def test_collision_after_final_validation_is_atomically_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "frame.png"
            clip.write_bytes(b"clip")
            original_link = extractor.os.link

            def collide(source: Path, target: Path) -> None:
                Path(target).write_bytes(b"LATE_WINNER")
                original_link(source, target)

            with mock.patch.object(extractor, "render_frame_png", return_value=b"GENERATED_FRAME"):
                with mock.patch.object(extractor.os, "link", side_effect=collide):
                    result, stdout, stderr = self.invoke(
                        str(clip), "--ffmpeg", "fake-ffmpeg", "--output", str(output)
                    )

            self.assertEqual(result, 1, stdout + stderr)
            self.assertEqual(output.read_bytes(), b"LATE_WINNER")
            self.assertEqual(self.stage_paths(root), [])

    @unittest.skipUnless(os.name == "nt", "handle-deletion attack replay is Windows-specific")
    def test_cleanup_deletes_by_handle_not_swapped_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "frame.png"
            victim = root / "victim.bin"
            victim.write_bytes(b"VICTIM")
            stage = extractor._create_output_stage(output)
            extractor._write_output_stage(stage, b"PARTIAL")
            original_delete = extractor._win32_mark_stage_for_deletion
            swap_attempted = False

            def attack(owned: extractor.OutputStage) -> bool:
                nonlocal swap_attempted
                swap_attempted = True
                with self.assertRaises(OSError):
                    owned.path.unlink()
                return original_delete(owned)

            with mock.patch.object(extractor, "_win32_mark_stage_for_deletion", side_effect=attack):
                cleaned = extractor._cleanup_output_stage(stage)

            self.assertTrue(swap_attempted)
            self.assertTrue(cleaned)
            self.assertEqual(victim.read_bytes(), b"VICTIM")
            self.assertEqual(self.stage_paths(root), [])

    def test_force_publish_error_preserves_old_output_and_cleans_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "approved-frame.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"old frame")

            with mock.patch.object(extractor, "render_frame_png", return_value=b"new complete"):
                if os.name == "nt":
                    publish_patch = mock.patch.object(
                        extractor,
                        "_win32_rename_by_handle",
                        side_effect=extractor.OutputPolicyError("locked"),
                    )
                else:
                    publish_patch = mock.patch.object(
                        extractor.os, "replace", side_effect=PermissionError("locked")
                    )
                with publish_patch:
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

            def collide(_ffmpeg: str, _clip: Path, _first: bool) -> bytes:
                output.unlink()
                try:
                    os.link(clip, output)
                except OSError as exc:
                    self.skipTest(f"hard links unavailable: {exc}")
                return b"new complete frame"

            with mock.patch.object(extractor, "render_frame_png", side_effect=collide):
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


class PngStreamTests(unittest.TestCase):
    def chunk(self, kind: bytes, payload: bytes) -> bytes:
        checksum = zlib.crc32(payload, zlib.crc32(kind)) & 0xFFFFFFFF
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", checksum)

    def minimal_png(self, marker: bytes) -> bytes:
        return extractor._PNG_SIGNATURE + self.chunk(b"tEXt", marker) + self.chunk(b"IEND", b"")

    def test_concatenated_stream_returns_complete_frames_in_order(self) -> None:
        first = self.minimal_png(b"first")
        last = self.minimal_png(b"last")
        stream = io.BytesIO(first + last)

        self.assertEqual(extractor._read_png_frame(stream), first)
        self.assertEqual(extractor._read_png_frame(stream), last)
        self.assertIsNone(extractor._read_png_frame(stream))

    def test_truncated_stream_is_rejected(self) -> None:
        with self.assertRaises(extractor.FrameExtractionError):
            extractor._read_png_frame(io.BytesIO(extractor._PNG_SIGNATURE + b"\x00"))


@unittest.skipUnless(FFMPEG, "protected pipeline integration requires ffmpeg")
class RealProtectedPipelineTests(unittest.TestCase):
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

    def test_protected_cli_pipeline_matches_independent_final_frame_oracle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "blue-to-red.mp4"
            actual = root / "actual.png"
            jpeg = root / "actual.jpg"
            expected = root / "expected.png"
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
            self.run_ffmpeg(
                "-y", "-i", str(clip), "-vf", "reverse", "-frames:v", "1", str(expected)
            )

            self.assertEqual(extractor.extract_frame(str(FFMPEG), clip, actual, False, False), 0)
            self.assertEqual(self.raw_rgb(actual), self.raw_rgb(expected))
            self.assertEqual(extractor.extract_frame(str(FFMPEG), clip, jpeg, False, False), 0)
            self.assertTrue(jpeg.read_bytes().startswith(b"\xff\xd8"))
            self.assertEqual(len(self.raw_rgb(jpeg)), len(self.raw_rgb(expected)))
            self.assertEqual(list(root.glob(".*.atomic-*")), [])


class OutputPolicyDocumentationTests(unittest.TestCase):
    def test_policy_and_atomic_publication_are_documented(self) -> None:
        root = Path(__file__).resolve().parents[1]
        handoff = (root / "references" / "continuation-handoff.md").read_text(encoding="utf-8")
        changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")

        self.assertIn("refuses to replace an existing output image", handoff)
        self.assertIn("`--force`", handoff)
        self.assertIn("atomically publishes the complete frame", handoff)
        self.assertIn("late destination collisions are preserved", changelog)


if __name__ == "__main__":
    unittest.main()
