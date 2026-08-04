"""Fail-closed and atomic output policy for the frame-extraction CLI."""

from __future__ import annotations

import concurrent.futures
import contextlib
import ctypes
import errno
import hashlib
import io
import os
import re
import shutil
import stat
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


def _from_extended_windows_path(value: str) -> Path:
    if value.startswith("\\\\?\\UNC\\"):
        return Path("\\\\" + value[8:])
    if value.startswith("\\\\?\\"):
        return Path(value[4:])
    return Path(value)


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
        return [
            *root.glob(".*.atomic-*"),
            *root.glob(".f-*"),
            *root.glob(".frame-exchange-*"),
            *root.glob(".frame-rollback-*"),
            *root.glob(".frame-rejected-*"),
            *root.glob(".x*"),
        ]

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
                # POSIX proves staging-namespace and replacement policy support
                # before decode, but the final output remains invisible.
                expected_stage_count = 1 if os.name in {"posix", "nt"} else 0
                self.assertEqual(len(self.stage_paths(root)), expected_stage_count)
                return b"complete frame"

            with mock.patch.object(
                extractor, "render_frame_png", side_effect=render
            ):
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

            with mock.patch.object(
                extractor, "render_frame_png", side_effect=render
            ) as render_frame:
                result, stdout, stderr = self.invoke(
                    str(clip),
                    "--ffmpeg",
                    "fake-ffmpeg",
                    "--output",
                    str(output),
                    "--force",
                )

            if (
                os.name == "posix"
                and not extractor._posix_descriptor_xattrs_supported()
            ):
                self.assertEqual(result, 1, stdout + stderr)
                self.assertIn("refusing --force replacement", stdout)
                render_frame.assert_not_called()
                self.assertEqual(output.read_bytes(), b"old frame")
            else:
                self.assertEqual(result, 0, stdout + stderr)
                render_frame.assert_called_once_with("fake-ffmpeg", clip, False)
                self.assertEqual(output.read_bytes(), b"new complete frame")
            self.assertEqual(self.stage_paths(root), [])

    def test_force_decode_failure_preserves_existing_output(self) -> None:
        if os.name == "posix" and not extractor._posix_descriptor_xattrs_supported():
            self.skipTest("complete Linux extended-metadata visibility unavailable")
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

    @unittest.skipUnless(os.name == "nt", "Windows ACL policy is platform-specific")
    def test_windows_force_preserves_matching_policy_on_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "approved-frame.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"old frame")
            descriptor = extractor._win32_replacement_descriptor(output)
            try:
                before = extractor._snapshot_win32_policy(descriptor, output)
            finally:
                os.close(descriptor)

            with mock.patch.object(
                extractor, "render_frame_png", return_value=b"new complete frame"
            ) as render:
                result, stdout, stderr = self.invoke(
                    str(clip),
                    "--ffmpeg",
                    "fake-ffmpeg",
                    "--output",
                    str(output),
                    "--force",
                )

            descriptor = extractor._win32_replacement_descriptor(output)
            try:
                after = extractor._snapshot_win32_policy(descriptor, output)
            finally:
                os.close(descriptor)
            self.assertEqual(result, 0, stdout + stderr)
            render.assert_called_once_with("fake-ffmpeg", clip, False)
            self.assertEqual(output.read_bytes(), b"new complete frame")
            self.assertEqual(after, before)
            self.assertEqual(self.stage_paths(root), [])

    @unittest.skipUnless(os.name == "nt", "Windows namespace locking is platform-specific")
    def test_windows_force_locks_target_namespace_through_decode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "approved-frame.png"
            attacker = root / "late-swap.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"old frame")
            attacker.write_bytes(b"unrelated file")

            def render(_ffmpeg: str, _clip: Path, _first: bool) -> bytes:
                with self.assertRaises(PermissionError):
                    os.replace(attacker, output)
                self.assertEqual(output.read_bytes(), b"old frame")
                return b"new complete frame"

            with mock.patch.object(
                extractor, "render_frame_png", side_effect=render
            ) as render_frame:
                result, stdout, stderr = self.invoke(
                    str(clip),
                    "--ffmpeg",
                    "fake-ffmpeg",
                    "--output",
                    str(output),
                    "--force",
                )

            self.assertEqual(result, 0, stdout + stderr)
            render_frame.assert_called_once_with("fake-ffmpeg", clip, False)
            self.assertEqual(output.read_bytes(), b"new complete frame")
            self.assertEqual(attacker.read_bytes(), b"unrelated file")
            self.assertEqual(self.stage_paths(root), [])

    @unittest.skipUnless(os.name == "nt", "Windows ACL policy is platform-specific")
    def test_windows_force_refuses_an_explicit_acl_before_decode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "approved-frame.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"old frame")
            configured = subprocess.run(
                ["icacls", str(output), "/grant", "*S-1-1-0:(R)"],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(configured.returncode, 0)
            descriptor = extractor._win32_replacement_descriptor(output)
            try:
                before = extractor._win32_security_descriptor(descriptor, output)
            finally:
                os.close(descriptor)

            with mock.patch.object(
                extractor, "render_frame_png", return_value=b"new frame"
            ) as render:
                result, stdout, stderr = self.invoke(
                    str(clip),
                    "--ffmpeg",
                    "fake-ffmpeg",
                    "--output",
                    str(output),
                    "--force",
                )

            descriptor = extractor._win32_replacement_descriptor(output)
            try:
                after = extractor._win32_security_descriptor(descriptor, output)
            finally:
                os.close(descriptor)
            self.assertEqual(result, 1, stdout + stderr)
            self.assertIn("security policy differs", stdout)
            render.assert_not_called()
            self.assertEqual(output.read_bytes(), b"old frame")
            self.assertEqual(after, before)
            self.assertEqual(self.stage_paths(root), [])

    @unittest.skipUnless(os.name == "nt", "Windows named streams are platform-specific")
    def test_windows_force_refuses_named_streams_before_decode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "approved-frame.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"old frame")
            stream_path = str(output) + ":Zone.Identifier"
            marker = b"[ZoneTransfer]\r\nZoneId=3\r\n"
            with open(stream_path, "wb") as stream:
                stream.write(marker)

            with mock.patch.object(
                extractor, "render_frame_png", return_value=b"new frame"
            ) as render:
                result, stdout, stderr = self.invoke(
                    str(clip),
                    "--ffmpeg",
                    "fake-ffmpeg",
                    "--output",
                    str(output),
                    "--force",
                )

            self.assertEqual(result, 1, stdout + stderr)
            self.assertIn("named data streams", stdout)
            render.assert_not_called()
            self.assertEqual(output.read_bytes(), b"old frame")
            with open(stream_path, "rb") as stream:
                self.assertEqual(stream.read(), marker)
            self.assertEqual(self.stage_paths(root), [])

    @unittest.skipUnless(os.name == "nt", "Windows attributes are platform-specific")
    def test_windows_force_refuses_policy_attributes_before_decode(self) -> None:
        get_attributes = ctypes.windll.kernel32.GetFileAttributesW
        set_attributes = ctypes.windll.kernel32.SetFileAttributesW
        get_attributes.argtypes = (ctypes.c_wchar_p,)
        get_attributes.restype = ctypes.c_uint32
        set_attributes.argtypes = (ctypes.c_wchar_p, ctypes.c_uint32)
        set_attributes.restype = ctypes.c_int
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "approved-frame.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"old frame")
            extended = extractor._win32_extended_path(output)
            original = get_attributes(extended)
            self.assertNotEqual(original, 0xFFFFFFFF)
            self.assertTrue(set_attributes(extended, original | 0x2))
            try:
                with mock.patch.object(
                    extractor, "render_frame_png", return_value=b"new frame"
                ) as render:
                    result, stdout, stderr = self.invoke(
                        str(clip),
                        "--ffmpeg",
                        "fake-ffmpeg",
                        "--output",
                        str(output),
                        "--force",
                    )

                self.assertEqual(result, 1, stdout + stderr)
                self.assertIn("policy-bearing file attributes", stdout)
                render.assert_not_called()
                self.assertEqual(output.read_bytes(), b"old frame")
                self.assertTrue(get_attributes(extended) & 0x2)
                self.assertEqual(self.stage_paths(root), [])
            finally:
                set_attributes(extended, original)

    @unittest.skipUnless(os.name == "nt", "Windows named streams are platform-specific")
    def test_windows_force_rechecks_a_late_named_stream(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "approved-frame.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"old frame")
            stream_path = str(output) + ":late-policy"

            def render(_ffmpeg: str, _clip: Path, _first: bool) -> bytes:
                with open(stream_path, "wb") as stream:
                    stream.write(b"appeared during decode")
                return b"new frame"

            with mock.patch.object(
                extractor, "render_frame_png", side_effect=render
            ) as render_frame:
                result, stdout, stderr = self.invoke(
                    str(clip),
                    "--ffmpeg",
                    "fake-ffmpeg",
                    "--output",
                    str(output),
                    "--force",
                )

            self.assertEqual(result, 1, stdout + stderr)
            self.assertIn("policy changed before publication", stdout)
            render_frame.assert_called_once_with("fake-ffmpeg", clip, False)
            self.assertEqual(output.read_bytes(), b"old frame")
            with open(stream_path, "rb") as stream:
                self.assertEqual(stream.read(), b"appeared during decode")
            self.assertEqual(self.stage_paths(root), [])

    @unittest.skipUnless(os.name == "nt", "Windows replacement transactions are platform-specific")
    def test_windows_force_rolls_back_a_commit_boundary_winner(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "approved-frame.png"
            moved_old = root / "moved-old-frame.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"old frame")
            real_replace = extractor._ReplaceFileW
            calls = 0

            def replace_with_attack(
                replaced: str,
                replacement: str,
                backup: str,
                flags: int,
                exclude: object,
                reserved: object,
            ) -> int:
                nonlocal calls
                calls += 1
                if calls == 1:
                    target = _from_extended_windows_path(replaced)
                    os.replace(target, moved_old)
                    target.write_bytes(b"late unrelated winner")
                return int(
                    real_replace(replaced, replacement, backup, flags, exclude, reserved)
                )

            with (
                mock.patch.object(
                    extractor, "render_frame_png", return_value=b"generated frame"
                ),
                mock.patch.object(
                    extractor, "_ReplaceFileW", side_effect=replace_with_attack
                ),
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
            self.assertIn("rolled back", stdout)
            self.assertEqual(calls, 1)
            self.assertEqual(output.read_bytes(), b"late unrelated winner")
            self.assertEqual(moved_old.read_bytes(), b"old frame")
            self.assertEqual(self.stage_paths(root), [])

    @unittest.skipUnless(os.name == "nt", "Windows replacement transactions are platform-specific")
    def test_windows_force_rolls_back_commit_boundary_target_ads(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "approved-frame.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"old frame")
            real_replace = extractor._ReplaceFileW
            calls = 0
            marker = b"late policy stream"

            def replace_with_attack(
                replaced: str,
                replacement: str,
                backup: str,
                flags: int,
                exclude: object,
                reserved: object,
            ) -> int:
                nonlocal calls
                calls += 1
                if calls == 1:
                    target = _from_extended_windows_path(replaced)
                    with open(str(target) + ":late-policy", "wb") as stream:
                        stream.write(marker)
                return int(
                    real_replace(replaced, replacement, backup, flags, exclude, reserved)
                )

            with (
                mock.patch.object(
                    extractor, "render_frame_png", return_value=b"generated frame"
                ),
                mock.patch.object(
                    extractor, "_ReplaceFileW", side_effect=replace_with_attack
                ),
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
            self.assertIn("rolled back", stdout)
            self.assertEqual(calls, 1)
            self.assertEqual(output.read_bytes(), b"old frame")
            with open(str(output) + ":late-policy", "rb") as stream:
                self.assertEqual(stream.read(), marker)
            self.assertEqual(self.stage_paths(root), [])

    @unittest.skipUnless(os.name == "nt", "Windows replacement transactions are platform-specific")
    def test_windows_force_never_publishes_a_commit_boundary_stage_acl(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "approved-frame.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"old frame")
            descriptor = extractor._win32_replacement_descriptor(output)
            try:
                expected_security = extractor._win32_security_policy(
                    descriptor, output
                )
            finally:
                os.close(descriptor)
            real_replace = extractor._ReplaceFileW
            calls = 0

            def replace_with_attack(
                replaced: str,
                replacement: str,
                backup: str,
                flags: int,
                exclude: object,
                reserved: object,
            ) -> int:
                nonlocal calls
                calls += 1
                result = int(
                    real_replace(replaced, replacement, backup, flags, exclude, reserved)
                )
                if result:
                    target = _from_extended_windows_path(replaced)
                    subprocess.run(
                        ["icacls", str(target), "/grant", "*S-1-1-0:(R)"],
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                return result

            with (
                mock.patch.object(
                    extractor, "render_frame_png", return_value=b"generated frame"
                ),
                mock.patch.object(
                    extractor, "_ReplaceFileW", side_effect=replace_with_attack
                ),
                mock.patch.object(extractor, "_NtSetSecurityObject", return_value=0),
            ):
                result, stdout, stderr = self.invoke(
                    str(clip),
                    "--ffmpeg",
                    "fake-ffmpeg",
                    "--output",
                    str(output),
                    "--force",
                )

            descriptor = extractor._win32_replacement_descriptor(output)
            try:
                final_security = extractor._win32_security_policy(descriptor, output)
            finally:
                os.close(descriptor)
            self.assertEqual(result, 1, stdout + stderr)
            self.assertIn("rolled back", stdout)
            self.assertEqual(calls, 1)
            self.assertEqual(output.read_bytes(), b"old frame")
            self.assertEqual(final_security, expected_security)
            self.assertEqual(self.stage_paths(root), [])

    @unittest.skipUnless(os.name == "nt", "Windows DACL restoration is platform-specific")
    def test_windows_force_reapplies_the_authorized_destination_dacl(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            subprocess.run(
                ["icacls", str(root), "/grant", "*S-1-5-18:(OI)(CI)(F)"],
                check=True,
                capture_output=True,
                text=True,
            )
            clip = root / "accepted-take.mp4"
            output = root / "approved-frame.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"old frame")
            descriptor = extractor._win32_replacement_descriptor(output)
            try:
                expected_security = extractor._win32_security_policy(
                    descriptor, output
                )
            finally:
                os.close(descriptor)
            expected_dacl = extractor._split_win32_security_policy(
                expected_security
            )
            expected_flags = re.findall(
                r"\([^;]+;([^;]*);", expected_dacl[2]
            )
            self.assertIn("AI", expected_dacl[3])
            self.assertNotIn("P", expected_dacl[3])
            self.assertTrue(expected_flags)
            self.assertTrue(all("ID" in flags for flags in expected_flags))
            real_replace = extractor._ReplaceFileW
            calls = 0

            def replace_with_normalized_dacl(
                replaced: str,
                replacement: str,
                backup: str,
                flags: int,
                exclude: object,
                reserved: object,
            ) -> int:
                nonlocal calls
                calls += 1
                result = int(
                    real_replace(
                        replaced, replacement, backup, flags, exclude, reserved
                    )
                )
                if result:
                    target = _from_extended_windows_path(replaced)
                    subprocess.run(
                        ["icacls", str(target), "/inheritance:d"],
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    subprocess.run(
                        ["icacls", str(target), "/grant", "*S-1-1-0:(R)"],
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    changed_descriptor = extractor._win32_replacement_descriptor(
                        target
                    )
                    try:
                        changed_security = extractor._win32_security_policy(
                            changed_descriptor, target
                        )
                    finally:
                        os.close(changed_descriptor)
                    changed_dacl = extractor._split_win32_security_policy(
                        changed_security
                    )
                    changed_flags = re.findall(
                        r"\([^;]+;([^;]*);", changed_dacl[2]
                    )
                    self.assertNotEqual(
                        expected_dacl[2:4],
                        changed_dacl[2:4],
                    )
                    self.assertIn("P", changed_dacl[3])
                    self.assertTrue(any("ID" not in flags for flags in changed_flags))
                    self.assertIn("WD", changed_dacl[2])
                return result

            with (
                mock.patch.object(
                    extractor, "render_frame_png", return_value=b"generated frame"
                ),
                mock.patch.object(
                    extractor,
                    "_ReplaceFileW",
                    side_effect=replace_with_normalized_dacl,
                ),
            ):
                result, stdout, stderr = self.invoke(
                    str(clip),
                    "--ffmpeg",
                    "fake-ffmpeg",
                    "--output",
                    str(output),
                    "--force",
                )

            descriptor = extractor._win32_replacement_descriptor(output)
            try:
                final_security = extractor._win32_security_policy(descriptor, output)
            finally:
                os.close(descriptor)
            self.assertEqual(result, 0, stdout + stderr)
            self.assertEqual(calls, 1)
            self.assertEqual(output.read_bytes(), b"generated frame")
            self.assertEqual(final_security, expected_security)
            self.assertEqual(self.stage_paths(root), [])

    @unittest.skipUnless(os.name == "nt", "Windows replacement transactions are platform-specific")
    def test_windows_force_rolls_back_commit_boundary_stage_ads_and_attributes(self) -> None:
        get_attributes = ctypes.windll.kernel32.GetFileAttributesW
        set_attributes = ctypes.windll.kernel32.SetFileAttributesW
        get_attributes.argtypes = (ctypes.c_wchar_p,)
        get_attributes.restype = ctypes.c_uint32
        set_attributes.argtypes = (ctypes.c_wchar_p, ctypes.c_uint32)
        set_attributes.restype = ctypes.c_int
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "approved-frame.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"old frame")
            original_attributes = get_attributes(extractor._win32_extended_path(output))
            real_replace = extractor._ReplaceFileW
            calls = 0

            def replace_with_attack(
                replaced: str,
                replacement: str,
                backup: str,
                flags: int,
                exclude: object,
                reserved: object,
            ) -> int:
                nonlocal calls
                calls += 1
                if calls == 1:
                    stage_path = _from_extended_windows_path(replacement)
                    with open(str(stage_path) + ":late-stage-policy", "wb") as stream:
                        stream.write(b"must not publish")
                    current = get_attributes(str(stage_path))
                    self.assertNotEqual(current, 0xFFFFFFFF)
                    self.assertTrue(set_attributes(str(stage_path), current | 0x2))
                return int(
                    real_replace(replaced, replacement, backup, flags, exclude, reserved)
                )

            with (
                mock.patch.object(
                    extractor, "render_frame_png", return_value=b"generated frame"
                ),
                mock.patch.object(
                    extractor, "_ReplaceFileW", side_effect=replace_with_attack
                ),
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
            self.assertIn("rolled back", stdout)
            self.assertEqual(calls, 1)
            self.assertEqual(output.read_bytes(), b"old frame")
            self.assertEqual(
                get_attributes(extractor._win32_extended_path(output)),
                original_attributes,
            )
            with self.assertRaises(OSError):
                open(str(output) + ":late-stage-policy", "rb")
            self.assertEqual(self.stage_paths(root), [])

    @unittest.skipUnless(os.name == "nt", "Windows replacement transactions are platform-specific")
    def test_windows_force_never_promotes_a_preclaimed_rollback_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "approved-frame.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"old frame")
            calls = 0

            def fail_with_preclaimed_backup(
                replaced: str,
                replacement: str,
                backup: str,
                flags: int,
                exclude: object,
                reserved: object,
            ) -> int:
                del replaced, replacement, flags, exclude, reserved
                nonlocal calls
                calls += 1
                if calls == 1:
                    _from_extended_windows_path(backup).write_bytes(
                        b"unrelated backup claimant"
                    )
                    ctypes.set_last_error(80)
                return 0

            with (
                mock.patch.object(
                    extractor, "render_frame_png", return_value=b"generated frame"
                ),
                mock.patch.object(
                    extractor,
                    "_ReplaceFileW",
                    side_effect=fail_with_preclaimed_backup,
                ),
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
            self.assertEqual(calls, 1)
            self.assertEqual(output.read_bytes(), b"old frame")
            recovery = self.stage_paths(root)
            self.assertEqual(len(recovery), 1)
            self.assertIn(".frame-rollback-", recovery[0].name)
            self.assertEqual(recovery[0].read_bytes(), b"unrelated backup claimant")

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
    def test_windows_near_name_max_stage_is_bounded_before_decode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / ("f" * 250 + ".png")
            clip.write_bytes(b"clip")
            original_stage_descriptor = extractor._win32_stage_descriptor
            stage_names: list[str] = []

            def capture_stage(path: Path) -> int:
                stage_names.append(path.name)
                return original_stage_descriptor(path)

            with (
                mock.patch.object(
                    extractor,
                    "render_frame_png",
                    return_value=b"GENERATED_FRAME",
                ) as render,
                mock.patch.object(
                    extractor,
                    "_win32_stage_descriptor",
                    side_effect=capture_stage,
                ),
            ):
                result = extractor.extract_frame(
                    "fake-ffmpeg", clip, output, False, False
                )

            extended_output = extractor._win32_extended_path(output)
            try:
                self.assertEqual(result, 0)
                render.assert_called_once_with("fake-ffmpeg", clip, False)
                with open(extended_output, "rb") as published:
                    self.assertEqual(published.read(), b"GENERATED_FRAME")
                self.assertEqual(len(stage_names), 1)
                target_digest = hashlib.sha256(
                    output.name.encode("utf-8", errors="surrogatepass")
                ).hexdigest()[:16]
                self.assertTrue(
                    stage_names[0].startswith(f".frame-{target_digest}.atomic-"),
                    stage_names[0],
                )
                self.assertLessEqual(len(stage_names[0]), 255)
                self.assertEqual(self.stage_paths(root), [])
            finally:
                os.unlink(extended_output)

    @unittest.skipUnless(os.name == "nt", "Windows console encodings are platform-specific")
    def test_windows_long_unicode_output_publishes_with_cp1252_console(self) -> None:
        class StrictCp1252(io.StringIO):
            @property
            def encoding(self) -> str:
                return "cp1252"

            def write(self, text: str) -> int:
                text.encode(self.encoding, errors="strict")
                return super().write(text)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / ("雪" * 240 + ".png")
            clip.write_bytes(b"clip")
            console = StrictCp1252()
            self.assertGreater(len(str(output.resolve())), 260)

            with (
                mock.patch.object(
                    extractor,
                    "render_frame_png",
                    return_value=b"GENERATED_FRAME",
                ),
                mock.patch.object(extractor.sys, "stdout", console),
            ):
                result = extractor.extract_frame(
                    "fake-ffmpeg", clip, output, False, False
                )

            extended_output = extractor._win32_extended_path(output)
            try:
                self.assertEqual(result, 0)
                with open(extended_output, "rb") as published:
                    self.assertEqual(published.read(), b"GENERATED_FRAME")
                self.assertIn("\\u96ea", console.getvalue())
                self.assertEqual(self.stage_paths(root), [])
            finally:
                os.unlink(extended_output)

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
                "COM¹.png",
                "COM².jpg",
                "COM³.webp",
                "LPT¹.png",
                "LPT².jpg",
                "LPT³.webp",
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

    @unittest.skipUnless(os.name == "nt", "Windows filename aliases are platform-specific")
    def test_windows_native_publication_rejects_superscript_device_alias(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            safe_output = root / "safe-frame.png"
            unsafe_output = root / "COM¹.png"
            stage = extractor._create_output_stage(safe_output)
            try:
                extractor._write_output_stage(stage, b"complete frame")
                with self.assertRaisesRegex(
                    extractor.OutputPolicyError, "unsafe Windows output filename"
                ):
                    extractor._win32_rename_by_handle(stage, unsafe_output, False)
                self.assertFalse(extractor._path_exists(unsafe_output))
            finally:
                extractor._cleanup_output_stage(stage)
            self.assertEqual(self.stage_paths(root), [])

    @unittest.skipUnless(os.name == "nt", "Windows directory handles are platform-specific")
    def test_windows_no_force_refuses_parent_rename_and_recreation_during_decode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            original_tree = root / "original-tree"
            replacement_tree = root / "replacement-tree"
            original_parent = original_tree / "frames"
            replacement_parent = replacement_tree / "frames"
            original_parent.mkdir(parents=True)
            replacement_parent.mkdir(parents=True)
            route = root / "route"
            subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(route), str(original_tree)],
                check=True,
                capture_output=True,
                text=True,
            )
            clip = root / "accepted-take.mp4"
            output = route / "frames" / "published-frame.png"
            clip.write_bytes(b"clip")

            def render(_ffmpeg: str, _clip: Path, _first: bool) -> bytes:
                os.rmdir(route)
                subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(route), str(replacement_tree)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                return b"complete frame"

            with mock.patch.object(
                extractor, "render_frame_png", side_effect=render
            ) as render_frame:
                result, stdout, stderr = self.invoke(
                    str(clip),
                    "--ffmpeg",
                    "fake-ffmpeg",
                    "--output",
                    str(output),
                )

            self.assertEqual(result, 1, stdout + stderr)
            self.assertIn("output directory identity changed", stdout)
            render_frame.assert_called_once_with("fake-ffmpeg", clip, False)
            self.assertFalse(output.exists())
            self.assertFalse((original_parent / output.name).exists())
            self.assertFalse((replacement_parent / output.name).exists())
            self.assertEqual(self.stage_paths(original_parent), [])
            self.assertEqual(self.stage_paths(replacement_parent), [])


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
            original_rename = extractor._win32_rename_open_handle
            swap_attempted = False

            def attack(
                stage: extractor.OutputStage, target_name: str, force: bool
            ) -> None:
                nonlocal swap_attempted
                swap_attempted = True
                with self.assertRaises(OSError):
                    stage.path.unlink()
                original_rename(stage, target_name, force)

            with mock.patch.object(extractor, "render_frame_png", return_value=b"GENERATED_FRAME"):
                with mock.patch.object(
                    extractor, "_win32_rename_open_handle", side_effect=attack
                ):
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
            original_rename = extractor._win32_rename_open_handle

            def collide(
                stage: extractor.OutputStage, target_name: str, force: bool
            ) -> None:
                anchored = extractor._win32_resolved_path(
                    stage.descriptor, "the test staging handle"
                )
                anchored.with_name(target_name).write_bytes(b"LATE_WINNER")
                original_rename(stage, target_name, force)

            with mock.patch.object(extractor, "render_frame_png", return_value=b"GENERATED_FRAME"):
                with mock.patch.object(
                    extractor, "_win32_rename_open_handle", side_effect=collide
                ):
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
        if os.name == "posix" and not extractor._posix_descriptor_xattrs_supported():
            self.skipTest("complete Linux extended-metadata visibility unavailable")
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
                        "_call_win32_replace_file",
                        return_value=5,
                    )
                else:
                    original_exchange = extractor._posix_exchange_names
                    exchange_calls = 0

                    def fail_publication_exchange(*args: object) -> None:
                        nonlocal exchange_calls
                        exchange_calls += 1
                        # The pre-decode filesystem probe exchanges twice. Fail
                        # the actual publication exchange, after decode.
                        if exchange_calls == 3:
                            raise PermissionError("locked")
                        original_exchange(*args)

                    publish_patch = mock.patch.object(
                        extractor,
                        "_posix_exchange_names",
                        side_effect=fail_publication_exchange,
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
        if os.name == "posix" and not extractor._posix_descriptor_xattrs_supported():
            self.skipTest("complete Linux extended-metadata visibility unavailable")
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "approved-frame.png"
            clip.write_bytes(b"clip must survive")
            output.write_bytes(b"old frame")
            blocked = False

            def collide(_ffmpeg: str, _clip: Path, _first: bool) -> bytes:
                nonlocal blocked
                if os.name == "nt":
                    with self.assertRaises(OSError):
                        output.unlink()
                    blocked = True
                    return b"new complete frame"
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

            self.assertEqual(clip.read_bytes(), b"clip must survive")
            if os.name == "nt":
                self.assertEqual(result, 0, stdout + stderr)
                self.assertTrue(blocked)
                self.assertEqual(output.read_bytes(), b"new complete frame")
            else:
                self.assertEqual(result, 1, stdout + stderr)
                self.assertTrue(os.path.samefile(clip, output))
            self.assertEqual(self.stage_paths(root), [])


@unittest.skipUnless(os.name == "posix", "POSIX publication semantics are platform-specific")
class PosixPublicationTests(OutputPolicyTestCase):
    @unittest.skipUnless(
        sys.platform.startswith("linux"),
        "descriptor-bound /proc/self/fd publication is Linux-specific",
    )
    def test_verify_to_link_stage_rename_swap_cannot_publish_attacker_inode(self) -> None:
        force_modes = (
            (False, True)
            if extractor._posix_descriptor_xattrs_supported()
            else (False,)
        )
        for force in force_modes:
            with self.subTest(force=force), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                clip = root / "accepted-take.mp4"
                output = root / "frame.png"
                clip.write_bytes(b"clip")
                if force:
                    output.write_bytes(b"old frame")

                original_link = extractor._posix_link_open_stage
                attacked = False

                def attack(
                    stage: extractor.OutputStage,
                    destination_name: str,
                    destination_directory_descriptor: int,
                ) -> None:
                    nonlocal attacked
                    attacked = True
                    displaced = stage.path.with_name(stage.path.name + ".displaced")
                    stage.path.replace(displaced)
                    stage.path.write_bytes(b"ATTACKER_INODE")
                    try:
                        original_link(
                            stage,
                            destination_name,
                            destination_directory_descriptor,
                        )
                    finally:
                        stage.path.unlink()
                        displaced.replace(stage.path)

                with (
                    mock.patch.object(
                        extractor,
                        "render_frame_png",
                        return_value=b"VERIFIED_GENERATED_FRAME",
                    ),
                    mock.patch.object(
                        extractor,
                        "_posix_link_open_stage",
                        side_effect=attack,
                    ),
                ):
                    result = extractor.extract_frame(
                        "fake-ffmpeg", clip, output, False, force
                    )

                self.assertTrue(attacked)
                self.assertEqual(result, 0)
                self.assertEqual(output.read_bytes(), b"VERIFIED_GENERATED_FRAME")
                self.assertEqual(self.stage_paths(root), [])

    def test_private_directory_swap_between_lstat_and_open_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "frame.png"
            original_open = extractor.os.open
            swaps: list[tuple[Path, Path]] = []

            def attack(
                path: str | os.PathLike[str],
                flags: int,
                mode: int = 0o777,
                *,
                dir_fd: int | None = None,
            ) -> int:
                candidate = Path(path)
                if (
                    dir_fd is not None
                    and candidate.name.startswith(f".{output.stem}.atomic-")
                    and not swaps
                ):
                    displaced = candidate.with_name(candidate.name + ".displaced")
                    os.rename(
                        candidate.name,
                        displaced.name,
                        src_dir_fd=dir_fd,
                        dst_dir_fd=dir_fd,
                    )
                    os.mkdir(candidate.name, 0o700, dir_fd=dir_fd)
                    swaps.append((candidate, displaced))
                return original_open(path, flags, mode, dir_fd=dir_fd)

            with (
                mock.patch.object(extractor.os, "open", side_effect=attack),
                self.assertRaisesRegex(
                    extractor.OutputPolicyError,
                    "staging directory changed while opening",
                ),
            ):
                extractor._create_output_stage(output)

            self.assertEqual(len(swaps), 1)
            replacement_name, displaced_name = swaps[0]
            self.assertTrue((root / replacement_name.name).is_dir())
            self.assertTrue((root / displaced_name.name).is_dir())

    def test_mkdir_then_initial_stat_failure_cleans_exact_private_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "frame.png"
            victim = root / "keep.txt"
            victim.write_bytes(b"KEEP")
            original_stat = extractor.os.stat
            failed = False

            def fail_created_directory_stat(
                path: str | os.PathLike[str],
                *args: object,
                **kwargs: object,
            ) -> os.stat_result:
                nonlocal failed
                name = os.fspath(path)
                if (
                    not failed
                    and kwargs.get("dir_fd") is not None
                    and isinstance(name, str)
                    and ".atomic-" in name
                ):
                    failed = True
                    raise OSError(errno.EIO, "injected initial stat failure")
                return original_stat(path, *args, **kwargs)

            with (
                mock.patch.object(
                    extractor.os,
                    "stat",
                    side_effect=fail_created_directory_stat,
                ),
                self.assertRaisesRegex(
                    extractor.OutputPolicyError,
                    "injected initial stat failure",
                ),
            ):
                extractor._create_output_stage(output)

            self.assertTrue(failed)
            self.assertEqual(victim.read_bytes(), b"KEEP")
            self.assertEqual(self.stage_paths(root), [])

    def test_stage_open_then_initial_fstat_failure_cleans_exact_file_and_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "frame.png"
            victim = root / "keep.txt"
            victim.write_bytes(b"KEEP")
            original_fstat = extractor.os.fstat
            failed = False

            def fail_created_file_fstat(descriptor: int) -> os.stat_result:
                nonlocal failed
                info = original_fstat(descriptor)
                if not failed and stat.S_ISREG(info.st_mode):
                    failed = True
                    raise OSError(errno.EIO, "injected initial file fstat failure")
                return info

            with (
                mock.patch.object(
                    extractor.os,
                    "fstat",
                    side_effect=fail_created_file_fstat,
                ),
                self.assertRaisesRegex(
                    extractor.OutputPolicyError,
                    "injected initial file fstat failure",
                ),
            ):
                extractor._create_output_stage(output)

            self.assertTrue(failed)
            self.assertEqual(victim.read_bytes(), b"KEEP")
            self.assertEqual(self.stage_paths(root), [])

    def _assert_probe_fstat_failure_leaves_zero_residue(self, fault_index: int) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "frame.png"
            stage = extractor._create_output_stage(output)
            original_open = extractor.os.open
            original_fstat = extractor.os.fstat
            probe_names = ("probe-private", "probe-public")
            probe_descriptors: list[int] = []
            failed = False

            def capture_probe_open(
                path: str | os.PathLike[str],
                flags: int,
                mode: int = 0o777,
                *,
                dir_fd: int | None = None,
            ) -> int:
                descriptor = original_open(path, flags, mode, dir_fd=dir_fd)
                if os.fspath(path) in probe_names:
                    probe_descriptors.append(descriptor)
                return descriptor

            def fail_selected_probe_fstat(descriptor: int) -> os.stat_result:
                nonlocal failed
                if (
                    not failed
                    and len(probe_descriptors) > fault_index
                    and descriptor == probe_descriptors[fault_index]
                ):
                    failed = True
                    raise OSError(
                        errno.EIO,
                        f"injected probe {fault_index + 1} fstat failure",
                    )
                return original_fstat(descriptor)

            def bounded_probe_name(
                tag: str,
                _directory_descriptor: int,
                _out: Path,
            ) -> str:
                return probe_names[0] if tag == "exchange-private" else probe_names[1]

            try:
                with (
                    mock.patch.object(
                        extractor,
                        "_posix_auxiliary_name",
                        side_effect=bounded_probe_name,
                    ),
                    mock.patch.object(
                        extractor.os,
                        "open",
                        side_effect=capture_probe_open,
                    ),
                    mock.patch.object(
                        extractor.os,
                        "fstat",
                        side_effect=fail_selected_probe_fstat,
                    ),
                    self.assertRaisesRegex(
                        extractor.OutputPolicyError,
                        f"injected probe {fault_index + 1} fstat failure",
                    ),
                ):
                    extractor._probe_posix_atomic_exchange(stage, output)

                self.assertTrue(failed)
                self.assertFalse((stage.directory_path / probe_names[0]).exists())
                self.assertFalse((root / probe_names[1]).exists())
                for descriptor in probe_descriptors:
                    with self.assertRaises(OSError):
                        os.fstat(descriptor)
            finally:
                extractor._cleanup_output_stage(stage)
            self.assertEqual(self.stage_paths(root), [])

    def test_first_probe_fstat_failure_leaves_zero_residue(self) -> None:
        self._assert_probe_fstat_failure_leaves_zero_residue(0)

    def test_second_probe_fstat_failure_leaves_zero_residue(self) -> None:
        self._assert_probe_fstat_failure_leaves_zero_residue(1)

    def test_private_directory_creation_stays_bound_to_open_target_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            parent = Path(temp_dir)
            root = parent / "target"
            displaced = parent / "displaced"
            root.mkdir()
            output = root / "frame.png"
            original_mkdir = extractor.os.mkdir
            attacked = False

            def attack(
                path: str | os.PathLike[str],
                mode: int = 0o777,
                *,
                dir_fd: int | None = None,
            ) -> None:
                nonlocal attacked
                if (
                    not attacked
                    and dir_fd is not None
                    and os.fspath(path).startswith(".frame.atomic-")
                ):
                    attacked = True
                    root.rename(displaced)
                    original_mkdir(root)
                original_mkdir(path, mode, dir_fd=dir_fd)

            with (
                mock.patch.object(extractor.os, "mkdir", side_effect=attack),
                self.assertRaisesRegex(
                    extractor.OutputPolicyError,
                    "staging directory identity changed",
                ),
            ):
                extractor._create_output_stage(output)

            self.assertTrue(attacked)
            self.assertEqual(self.stage_paths(root), [])
            self.assertEqual(self.stage_paths(displaced), [])

    def test_private_staging_directory_is_verified_owner_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "frame.png"
            stage = extractor._create_output_stage(output)
            try:
                self.assertIsNotNone(stage.directory_descriptor)
                assert stage.directory_descriptor is not None
                directory = os.fstat(stage.directory_descriptor)
                self.assertEqual(stat.S_IMODE(directory.st_mode), 0o700)
                self.assertEqual(directory.st_uid, os.geteuid())
            finally:
                extractor._cleanup_output_stage(stage)

    def test_near_name_max_output_uses_bounded_stage_without_decode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            name_max = int(os.pathconf(root, "PC_NAME_MAX"))
            clip = root / "accepted-take.mp4"
            output = root / ("f" * 250 + ".png")
            if len(os.fsencode(output.name)) > name_max:
                self.skipTest(
                    f"filesystem NAME_MAX={name_max} cannot represent the 254-byte fixture"
                )
            clip.write_bytes(b"clip")
            original_stage_name = extractor._posix_stage_directory_name
            stage_names: list[str] = []

            def capture_stage_name(candidate: Path, descriptor: int) -> str:
                name = original_stage_name(candidate, descriptor)
                stage_names.append(name)
                return name

            with (
                mock.patch.object(
                    extractor,
                    "render_frame_png",
                    return_value=b"GENERATED_FRAME",
                ) as render,
                mock.patch.object(
                    extractor,
                    "_posix_stage_directory_name",
                    side_effect=capture_stage_name,
                ),
            ):
                result = extractor.extract_frame(
                    "fake-ffmpeg", clip, output, False, False
                )

            self.assertEqual(result, 0)
            render.assert_called_once_with("fake-ffmpeg", clip, False)
            self.assertEqual(output.read_bytes(), b"GENERATED_FRAME")
            self.assertEqual(len(stage_names), 1)
            directory_name = stage_names[0]
            target_digest = hashlib.sha256(os.fsencode(output.name)).hexdigest()[:16]
            self.assertTrue(
                directory_name.startswith(f".frame-{target_digest}.atomic-"),
                directory_name,
            )
            self.assertLessEqual(len(os.fsencode(directory_name)), name_max)
            self.assertEqual(self.stage_paths(root), [])

    def test_new_output_mode_honors_process_umask(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "frame.png"
            clip.write_bytes(b"clip")
            previous_umask = os.umask(0o027)
            try:
                with mock.patch.object(
                    extractor, "render_frame_png", return_value=b"GENERATED_FRAME"
                ):
                    result = extractor.extract_frame(
                        "fake-ffmpeg", clip, output, False, False
                    )
            finally:
                os.umask(previous_umask)

            self.assertEqual(result, 0)
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o640)
            self.assertEqual(self.stage_paths(root), [])

    def test_force_preserves_existing_owner_group_and_mode(self) -> None:
        if not extractor._posix_descriptor_xattrs_supported():
            self.skipTest("descriptor-bound Linux metadata APIs unavailable")
        if not hasattr(os, "geteuid") or os.geteuid() != 0:
            self.skipTest("real distinct-owner preservation requires root")
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "frame.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"old frame")
            distinct_uid = 65534
            distinct_gid = 65534
            if distinct_uid == os.geteuid():
                distinct_uid = 65533
            if distinct_gid == os.getegid():
                distinct_gid = 65533
            os.chown(output, distinct_uid, distinct_gid)
            output.chmod(0o664)
            before = output.stat()
            self.assertNotEqual(before.st_uid, os.geteuid())
            self.assertNotEqual(before.st_gid, os.getegid())
            previous_umask = os.umask(0o077)
            try:
                with mock.patch.object(
                    extractor, "render_frame_png", return_value=b"GENERATED_FRAME"
                ):
                    result = extractor.extract_frame(
                        "fake-ffmpeg", clip, output, False, True
                    )
            finally:
                os.umask(previous_umask)

            after = output.stat()
            self.assertEqual(result, 0)
            self.assertEqual(after.st_uid, distinct_uid)
            self.assertEqual(after.st_gid, distinct_gid)
            self.assertEqual(stat.S_IMODE(after.st_mode), 0o664)
            self.assertEqual(self.stage_paths(root), [])

    def test_force_holds_verified_target_descriptor_through_decode(self) -> None:
        if not extractor._posix_descriptor_xattrs_supported():
            self.skipTest("complete Linux replacement contract unavailable")
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "frame.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"old frame")
            original_prepare = extractor._prepare_posix_replacement_metadata
            snapshots: list[extractor.PosixReplacementSnapshot] = []

            def capture_snapshot(
                stage: extractor.OutputStage,
                candidate: Path,
            ) -> extractor.PosixReplacementSnapshot:
                snapshot = original_prepare(stage, candidate)
                snapshots.append(snapshot)
                return snapshot

            def render(_ffmpeg: str, _clip: Path, _first: bool) -> bytes:
                self.assertEqual(len(snapshots), 1)
                opened = os.fstat(snapshots[0].descriptor)
                self.assertEqual(extractor._identity(opened), snapshots[0].identity)
                self.assertEqual(output.read_bytes(), b"old frame")
                return b"GENERATED_FRAME"

            with (
                mock.patch.object(
                    extractor,
                    "_prepare_posix_replacement_metadata",
                    side_effect=capture_snapshot,
                ),
                mock.patch.object(extractor, "render_frame_png", side_effect=render),
            ):
                result = extractor.extract_frame(
                    "fake-ffmpeg", clip, output, False, True
                )

            self.assertEqual(result, 0)
            self.assertEqual(output.read_bytes(), b"GENERATED_FRAME")
            with self.assertRaises(OSError):
                os.fstat(snapshots[0].descriptor)
            self.assertEqual(self.stage_paths(root), [])

    def test_force_auxiliary_names_fit_name_max_14_with_unicode_output(self) -> None:
        if not extractor._posix_descriptor_xattrs_supported():
            self.skipTest("complete Linux replacement contract unavailable")
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "雪.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"old frame")
            original_exchange = extractor._posix_exchange_names
            exchange_names: list[str] = []

            def capture_exchange(
                left_name: str,
                left_directory_descriptor: int,
                right_name: str,
                right_directory_descriptor: int,
            ) -> None:
                exchange_names.extend((left_name, right_name))
                original_exchange(
                    left_name,
                    left_directory_descriptor,
                    right_name,
                    right_directory_descriptor,
                )

            with (
                mock.patch.object(extractor.os, "fpathconf", return_value=14),
                mock.patch.object(
                    extractor,
                    "_posix_exchange_names",
                    side_effect=capture_exchange,
                ),
                mock.patch.object(
                    extractor,
                    "render_frame_png",
                    return_value=b"GENERATED_FRAME",
                ),
            ):
                result = extractor.extract_frame(
                    "fake-ffmpeg", clip, output, False, True
                )

            self.assertEqual(result, 0)
            self.assertEqual(output.read_bytes(), b"GENERATED_FRAME")
            auxiliary_names = [name for name in exchange_names if name.startswith(".x")]
            self.assertGreaterEqual(len(auxiliary_names), 5)
            self.assertTrue(
                all(len(os.fsencode(name)) <= 14 for name in auxiliary_names),
                exchange_names,
            )
            self.assertEqual(self.stage_paths(root), [])

    def test_force_swap_after_final_verify_is_rolled_back_without_overwrite(self) -> None:
        if not extractor._posix_descriptor_xattrs_supported():
            self.skipTest("complete Linux replacement contract unavailable")
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "frame.png"
            old_stash = root / "verified-old-frame.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"VERIFIED_OLD_FRAME")
            original_verify = extractor._verify_posix_replacement_metadata
            attacked = False

            def swap_after_verify(
                snapshot: extractor.PosixReplacementSnapshot,
                stage: extractor.OutputStage,
                candidate: Path,
            ) -> None:
                nonlocal attacked
                original_verify(snapshot, stage, candidate)
                if not attacked:
                    attacked = True
                    candidate.replace(old_stash)
                    candidate.write_bytes(b"LATE_UNVERIFIED_TARGET")

            with (
                mock.patch.object(
                    extractor,
                    "render_frame_png",
                    return_value=b"GENERATED_FRAME",
                ),
                mock.patch.object(
                    extractor,
                    "_verify_posix_replacement_metadata",
                    side_effect=swap_after_verify,
                ),
            ):
                result, stdout, stderr = self.invoke(
                    str(clip),
                    "--ffmpeg",
                    "fake-ffmpeg",
                    "--output",
                    str(output),
                    "--force",
                )

            self.assertTrue(attacked)
            self.assertEqual(result, 1, stdout + stderr)
            self.assertIn("destination changed after verification", stdout)
            self.assertEqual(output.read_bytes(), b"LATE_UNVERIFIED_TARGET")
            self.assertEqual(old_stash.read_bytes(), b"VERIFIED_OLD_FRAME")
            self.assertEqual(self.stage_paths(root), [])

    @unittest.skipUnless(
        sys.platform.startswith("linux"),
        "descriptor-bound extended-attribute contract is Linux-specific",
    )
    def test_force_preserves_user_extended_attributes(self) -> None:
        if not extractor._posix_descriptor_xattrs_supported():
            self.skipTest("complete Linux extended-metadata visibility unavailable")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "frame.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"old frame")
            attribute = "user.seedance-publication-test"
            value = b"shared-review-policy"
            try:
                os.setxattr(output, attribute, value)
            except OSError as exc:
                unsupported = {
                    errno.EACCES,
                    errno.EPERM,
                    errno.ENOTSUP,
                    getattr(errno, "EOPNOTSUPP", errno.ENOTSUP),
                }
                if exc.errno in unsupported:
                    self.skipTest(f"filesystem user xattrs unavailable: {exc}")
                raise

            with mock.patch.object(
                extractor, "render_frame_png", return_value=b"GENERATED_FRAME"
            ):
                result = extractor.extract_frame("fake-ffmpeg", clip, output, False, True)

            self.assertEqual(result, 0)
            self.assertEqual(output.read_bytes(), b"GENERATED_FRAME")
            self.assertEqual(os.getxattr(output, attribute), value)
            self.assertEqual(self.stage_paths(root), [])

    @unittest.skipUnless(
        sys.platform.startswith("linux"),
        "Linux POSIX ACL xattr contract",
    )
    def test_force_preserves_extended_access_acl(self) -> None:
        setfacl = shutil.which("setfacl")
        if setfacl is None:
            self.skipTest("setfacl is unavailable")
        if not extractor._posix_descriptor_xattrs_supported():
            self.skipTest("complete Linux extended-metadata visibility unavailable")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "frame.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"old frame")
            numeric_uid = os.getuid() + 100000
            configured = subprocess.run(
                [setfacl, "-m", f"u:{numeric_uid}:r--", str(output)],
                capture_output=True,
                text=True,
            )
            if configured.returncode != 0:
                self.skipTest(
                    "filesystem access ACLs unavailable: "
                    + (configured.stderr.strip() or configured.stdout.strip())
                )
            try:
                before_acl = os.getxattr(output, "system.posix_acl_access")
            except OSError as exc:
                self.skipTest(f"access ACL xattr unavailable: {exc}")

            with mock.patch.object(
                extractor, "render_frame_png", return_value=b"GENERATED_FRAME"
            ):
                result = extractor.extract_frame("fake-ffmpeg", clip, output, False, True)

            self.assertEqual(result, 0)
            self.assertEqual(output.read_bytes(), b"GENERATED_FRAME")
            self.assertEqual(
                os.getxattr(output, "system.posix_acl_access"),
                before_acl,
            )
            self.assertEqual(self.stage_paths(root), [])

    def test_force_refuses_detected_security_policy_xattr(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "frame.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"old frame")

            with (
                mock.patch.object(
                    extractor, "render_frame_png", return_value=b"GENERATED_FRAME"
                ) as render,
                mock.patch.object(
                    extractor,
                    "_posix_descriptor_xattrs_supported",
                    return_value=True,
                ),
                mock.patch.object(
                    extractor,
                    "_prove_linux_privileged_xattr_visibility",
                ),
                mock.patch.object(
                    extractor.os,
                    "listxattr",
                    return_value=["security.selinux"],
                ),
                mock.patch.object(extractor.os, "getxattr") as getxattr,
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
            self.assertIn("security.selinux", stdout)
            self.assertIn("replacement was refused", stdout)
            render.assert_not_called()
            getxattr.assert_not_called()
            self.assertEqual(output.read_bytes(), b"old frame")
            self.assertEqual(self.stage_paths(root), [])

    def test_force_refuses_when_extended_policy_cannot_be_audited(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "frame.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"old frame")

            with (
                mock.patch.object(
                    extractor, "render_frame_png", return_value=b"GENERATED_FRAME"
                ) as render,
                mock.patch.object(
                    extractor,
                    "_posix_descriptor_xattrs_supported",
                    return_value=False,
                ),
                mock.patch.object(
                    extractor,
                    "_posix_descriptor_xattr_api_supported",
                    return_value=False,
                ),
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
            self.assertIn("lacks descriptor-bound extended-metadata APIs", stdout)
            render.assert_not_called()
            self.assertEqual(output.read_bytes(), b"old frame")
            self.assertEqual(self.stage_paths(root), [])

    def test_force_refuses_without_effective_cap_sys_admin(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "frame.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"old frame")

            with (
                mock.patch.object(
                    extractor, "render_frame_png", return_value=b"GENERATED_FRAME"
                ) as render,
                mock.patch.object(
                    extractor,
                    "_posix_descriptor_xattr_api_supported",
                    return_value=True,
                ),
                mock.patch.object(
                    extractor,
                    "_linux_has_effective_cap_sys_admin",
                    return_value=False,
                ),
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
            self.assertIn("effective CAP_SYS_ADMIN", stdout)
            self.assertIn("hidden trusted or security metadata", stdout)
            render.assert_not_called()
            self.assertEqual(output.read_bytes(), b"old frame")
            self.assertEqual(self.stage_paths(root), [])

    def test_force_refuses_when_xattr_enumeration_is_unsupported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "frame.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"old frame")

            with (
                mock.patch.object(
                    extractor, "render_frame_png", return_value=b"GENERATED_FRAME"
                ) as render,
                mock.patch.object(
                    extractor,
                    "_posix_descriptor_xattrs_supported",
                    return_value=True,
                ),
                mock.patch.object(
                    extractor,
                    "_prove_linux_privileged_xattr_visibility",
                ),
                mock.patch.object(
                    extractor.os,
                    "listxattr",
                    side_effect=OSError(errno.ENOTSUP, "not supported"),
                ),
                mock.patch.object(extractor.os, "getxattr") as getxattr,
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
            self.assertIn("cannot enumerate extended metadata", stdout)
            self.assertIn("replacement was refused", stdout)
            render.assert_not_called()
            getxattr.assert_not_called()
            self.assertEqual(output.read_bytes(), b"old frame")
            self.assertEqual(self.stage_paths(root), [])

    def test_force_refuses_failed_trusted_namespace_probe_before_decode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "frame.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"old frame")

            with (
                mock.patch.object(
                    extractor,
                    "_posix_descriptor_xattrs_supported",
                    return_value=True,
                ),
                mock.patch.object(extractor.os, "listxattr", return_value=[]),
                mock.patch.object(
                    extractor.os,
                    "setxattr",
                    side_effect=OSError(errno.EPERM, "trusted namespace denied"),
                ),
                mock.patch.object(
                    extractor,
                    "render_frame_png",
                    return_value=b"GENERATED_FRAME",
                ) as render,
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
            self.assertIn("privileged extended-metadata namespace", stdout)
            self.assertIn("replacement was refused", stdout)
            render.assert_not_called()
            self.assertEqual(output.read_bytes(), b"old frame")
            self.assertEqual(self.stage_paths(root), [])

    def test_force_refuses_cross_account_writable_directory_before_decode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "frame.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"old frame")
            root.chmod(0o777)
            try:
                with (
                    mock.patch.object(
                        extractor,
                        "_posix_descriptor_xattrs_supported",
                        return_value=True,
                    ),
                    mock.patch.object(
                        extractor,
                        "render_frame_png",
                        return_value=b"GENERATED_FRAME",
                    ) as render,
                ):
                    result, stdout, stderr = self.invoke(
                        str(clip),
                        "--ffmpeg",
                        "fake-ffmpeg",
                        "--output",
                        str(output),
                        "--force",
                    )
            finally:
                root.chmod(0o700)

            self.assertEqual(result, 1, stdout + stderr)
            self.assertIn("not writable by group or others", stdout)
            render.assert_not_called()
            self.assertEqual(output.read_bytes(), b"old frame")
            self.assertEqual(self.stage_paths(root), [])

    def test_force_refuses_failed_atomic_exchange_probe_before_decode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "frame.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"old frame")

            with (
                mock.patch.object(
                    extractor,
                    "_posix_descriptor_xattrs_supported",
                    return_value=True,
                ),
                mock.patch.object(extractor.os, "listxattr", return_value=[]),
                mock.patch.object(
                    extractor,
                    "_prove_linux_privileged_xattr_visibility",
                ),
                mock.patch.object(
                    extractor,
                    "_posix_exchange_names",
                    side_effect=OSError(errno.ENOTSUP, "exchange unsupported"),
                ),
                mock.patch.object(
                    extractor,
                    "render_frame_png",
                    return_value=b"GENERATED_FRAME",
                ) as render,
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
            self.assertIn("identity-safe atomic exchange", stdout)
            self.assertIn("replacement was refused", stdout)
            render.assert_not_called()
            self.assertEqual(output.read_bytes(), b"old frame")
            self.assertEqual(self.stage_paths(root), [])

    def test_non_linux_posix_force_refuses_unexposed_acl_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "frame.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"old frame")

            with (
                mock.patch.object(
                    extractor, "render_frame_png", return_value=b"GENERATED_FRAME"
                ) as render,
                mock.patch.object(extractor.sys, "platform", "darwin"),
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
            self.assertIn("non-Linux POSIX runtime", stdout)
            render.assert_not_called()
            self.assertEqual(output.read_bytes(), b"old frame")
            self.assertEqual(self.stage_paths(root), [])

    def test_force_policy_error_after_anchor_link_cleans_owned_anchor(self) -> None:
        if not extractor._posix_descriptor_xattrs_supported():
            self.skipTest("descriptor-bound Linux metadata APIs unavailable")
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clip = root / "accepted-take.mp4"
            output = root / "frame.png"
            clip.write_bytes(b"clip")
            output.write_bytes(b"old frame")
            original_link = extractor._posix_link_open_stage

            def fail_after_link(
                stage: extractor.OutputStage,
                destination_name: str,
                destination_directory_descriptor: int,
            ) -> None:
                original_link(
                    stage,
                    destination_name,
                    destination_directory_descriptor,
                )
                raise extractor.OutputPolicyError("post-link policy failure")

            with (
                mock.patch.object(
                    extractor, "render_frame_png", return_value=b"GENERATED_FRAME"
                ),
                mock.patch.object(
                    extractor,
                    "_posix_link_open_stage",
                    side_effect=fail_after_link,
                ),
                self.assertRaisesRegex(
                    extractor.OutputPolicyError, "post-link policy failure"
                ),
            ):
                extractor.extract_frame("fake-ffmpeg", clip, output, False, True)

            self.assertEqual(output.read_bytes(), b"old frame")
            self.assertEqual(self.stage_paths(root), [])


class OutputEncodingTests(unittest.TestCase):
    def test_webp_uses_ffmpegs_libwebp_encoder_name(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=b"RIFFxxxxWEBP", stderr=b""
        )
        with mock.patch.object(
            extractor.subprocess, "run", return_value=completed
        ) as run:
            encoded = extractor._encode_frame_for_output(
                "ffmpeg", b"PNG_FRAME", Path("frame.webp")
            )

        command = run.call_args.args[0]
        self.assertEqual(command[command.index("-vcodec") + 1], "libwebp")
        self.assertEqual(encoded, completed.stdout)


class ConsoleOutputTests(unittest.TestCase):
    def test_error_text_is_escaped_for_legacy_console_encoding(self) -> None:
        class StrictCp1252(io.StringIO):
            @property
            def encoding(self) -> str:
                return "cp1252"

            def write(self, text: str) -> int:
                text.encode(self.encoding, errors="strict")
                return super().write(text)

        stream = StrictCp1252()
        extractor._write_console_line(
            "output refused for C:\\frames\\雪.png",
            stream=stream,
        )

        self.assertEqual(
            stream.getvalue(),
            "output refused for C:\\frames\\\\u96ea.png\n",
        )

    def test_missing_closed_and_broken_console_streams_are_nonfatal(self) -> None:
        closed = io.StringIO()
        closed.close()

        class BrokenStream(io.StringIO):
            def write(self, text: str) -> int:
                raise BrokenPipeError("consumer closed the pipe")

        extractor._write_console_line("no console", stream=None)
        extractor._write_console_line("closed console", stream=closed)
        extractor._write_console_line("broken console", stream=BrokenStream())

    def test_missing_stdout_cannot_change_a_successful_publication(self) -> None:
        class BrokenStream(io.StringIO):
            def write(self, text: str) -> int:
                raise BrokenPipeError("consumer closed the pipe")

        closed = io.StringIO()
        closed.close()
        streams = (("missing", None), ("closed", closed), ("broken", BrokenStream()))
        for label, stream in streams:
            with self.subTest(stream=label), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                clip = root / "accepted-take.mp4"
                output = root / "published-frame.png"
                clip.write_bytes(b"clip")

                with (
                    mock.patch.object(
                        extractor, "render_frame_png", return_value=b"COMPLETE_FRAME"
                    ),
                    mock.patch.object(extractor.sys, "stdout", stream),
                ):
                    result = extractor.extract_frame(
                        "fake-ffmpeg", clip, output, False, False
                    )

                self.assertEqual(result, 0)
                self.assertEqual(output.read_bytes(), b"COMPLETE_FRAME")


class PublicationPrimitiveTests(unittest.TestCase):
    def test_windows_postverify_diagnostic_is_bounded_and_component_specific(self) -> None:
        baseline = extractor.WindowsArtifactState(
            identity=(1, 2),
            security_policy="O:SYG:BAD:PAI(A;;FA;;;SY)S:(ML;;NW;;;ME)",
            policy_attributes=0,
            named_streams=(),
            content_digest=b"digest",
        )

        def changed(**updates: object) -> extractor.WindowsArtifactState:
            values = {
                "identity": baseline.identity,
                "security_policy": baseline.security_policy,
                "policy_attributes": baseline.policy_attributes,
                "named_streams": baseline.named_streams,
                "content_digest": baseline.content_digest,
            }
            values.update(updates)
            return extractor.WindowsArtifactState(**values)

        cases = (
            ("bytes", changed(content_digest=b"other")),
            ("file identity", changed(identity=(1, 3))),
            (
                "owner",
                changed(security_policy="O:BAG:BAD:PAI(A;;FA;;;SY)S:(ML;;NW;;;ME)"),
            ),
            (
                "group",
                changed(security_policy="O:SYG:SYD:PAI(A;;FA;;;SY)S:(ML;;NW;;;ME)"),
            ),
            (
                "DACL entries",
                changed(security_policy="O:SYG:BAD:PAI(A;;FR;;;SY)S:(ML;;NW;;;ME)"),
            ),
            (
                "DACL control flags",
                changed(security_policy="O:SYG:BAD:AI(A;;FA;;;SY)S:(ML;;NW;;;ME)"),
            ),
            (
                "mandatory label",
                changed(security_policy="O:SYG:BAD:PAI(A;;FA;;;SY)S:(ML;;NW;;;HI)"),
            ),
            ("named streams (ADS)", changed(named_streams=(":audit:$DATA",))),
            ("policy attributes", changed(policy_attributes=2)),
        )
        for label, observed in cases:
            with self.subTest(label=label):
                self.assertEqual(
                    extractor._win32_artifact_differences(baseline, observed),
                    (label,),
                )

        all_differences = extractor._win32_artifact_differences(
            baseline,
            extractor.WindowsArtifactState(
                identity=(9, 9),
                security_policy="O:BAG:SYD:AI(A;;FR;;;BA)S:(ML;;NW;;;HI)",
                policy_attributes=2,
                named_streams=(":audit:$DATA",),
                content_digest=b"other",
            ),
        )
        self.assertEqual(all_differences, tuple(label for label, _ in cases))
        self.assertLessEqual(len(", ".join(all_differences)), 160)

    @unittest.skipUnless(os.name == "nt", "Windows security descriptors are platform-specific")
    def test_windows_security_policy_ignores_only_relative_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "frame.png"
            output.write_bytes(b"frame")
            descriptor = extractor._win32_replacement_descriptor(output)
            try:
                raw = extractor._win32_security_descriptor(descriptor, output)
            finally:
                os.close(descriptor)

            # A self-relative descriptor may place its components at any valid
            # offsets. Insert aligned padding and retarget every non-null
            # owner/group/SACL/DACL offset without changing one policy byte.
            shifted = bytearray(raw[:20] + b"\0\0\0\0" + raw[20:])
            for field_offset in (4, 8, 12, 16):
                component_offset = struct.unpack_from("<I", raw, field_offset)[0]
                if component_offset:
                    struct.pack_into(
                        "<I", shifted, field_offset, component_offset + 4
                    )

            self.assertNotEqual(bytes(shifted), raw)
            self.assertEqual(
                extractor._canonicalize_win32_security_descriptor(raw, output),
                extractor._canonicalize_win32_security_descriptor(
                    bytes(shifted), output
                ),
            )

    def test_linux_capability_proof_reads_the_effective_cap_sys_admin_bit(self) -> None:
        cases = (
            ("Name:\tpython\nCapEff:\t0000000000000000\n", False),
            (f"CapEff:\t{1 << extractor._CAP_SYS_ADMIN:016x}\n", True),
            ("CapEff:\tnot-hex\n", False),
            ("Name:\tpython\n", False),
        )
        for status, expected in cases:
            with (
                self.subTest(status=status),
                mock.patch.object(extractor.sys, "platform", "linux"),
                mock.patch.object(extractor.Path, "read_text", return_value=status),
            ):
                self.assertEqual(
                    extractor._linux_has_effective_cap_sys_admin(), expected
                )

    def test_linux_link_source_is_the_open_staging_descriptor(self) -> None:
        stage = extractor.OutputStage(
            Path("mutable-stage-name.png"),
            (1, 2),
            41,
            directory_descriptor=42,
        )
        with (
            mock.patch.object(extractor.sys, "platform", "linux"),
            mock.patch.object(extractor.os, "link") as link,
        ):
            extractor._posix_link_open_stage(stage, "frame.png", 43)

        link.assert_called_once_with(
            "/proc/self/fd/41",
            "frame.png",
            dst_dir_fd=43,
            follow_symlinks=True,
        )

    def test_linux_without_procfs_uses_private_directory_fallback(self) -> None:
        stage = extractor.OutputStage(
            Path("frame.png"),
            (1, 2),
            41,
            directory_descriptor=42,
        )
        linked = mock.Mock(st_dev=1, st_ino=2)
        with (
            mock.patch.object(extractor.sys, "platform", "linux"),
            mock.patch.object(extractor, "_verify_output_stage") as verify,
            mock.patch.object(
                extractor.os,
                "link",
                side_effect=[OSError(errno.ENOENT, "procfs unavailable"), None],
            ) as link,
            mock.patch.object(extractor.os, "stat", return_value=linked),
        ):
            extractor._posix_link_open_stage(stage, "target.png", 43)

        self.assertEqual(link.call_count, 2)
        self.assertEqual(link.call_args_list[0].args[:2], ("/proc/self/fd/41", "target.png"))
        self.assertEqual(link.call_args_list[1].args[:2], ("frame.png", "target.png"))
        self.assertEqual(link.call_args_list[1].kwargs["src_dir_fd"], 42)
        self.assertFalse(link.call_args_list[1].kwargs["follow_symlinks"])
        verify.assert_called_once_with(stage, require_content=True)

    def test_force_exchange_rolls_back_a_post_exchange_identity_failure(self) -> None:
        stage = extractor.OutputStage(
            Path("private/frame.png"),
            (1, 2),
            41,
            directory_descriptor=42,
            target_directory_descriptor=43,
        )
        snapshot = extractor.PosixReplacementSnapshot(
            descriptor=44,
            identity=(1, 3),
            uid=1000,
            gid=1000,
            mode=0o640,
            extended_attributes=(),
        )
        with (
            mock.patch.object(extractor, "_verify_posix_force_directory_contract"),
            mock.patch.object(
                extractor,
                "_link_unique_posix_stage_anchor",
                return_value="bounded-anchor-a",
            ),
            mock.patch.object(extractor, "_verify_posix_replacement_metadata"),
            mock.patch.object(extractor, "_verify_posix_staged_replacement_metadata"),
            mock.patch.object(extractor, "_posix_exchange_names") as exchange,
            mock.patch.object(
                extractor,
                "_verify_posix_exchanged_replacement",
                side_effect=extractor.OutputPolicyError(
                    "destination changed after verification"
                ),
            ),
            mock.patch.object(extractor, "_rollback_posix_exchange") as rollback,
            self.assertRaisesRegex(
                extractor.OutputPolicyError,
                "destination changed after verification",
            ),
        ):
            extractor._publish_posix_force_exchange(
                stage,
                snapshot,
                Path("frame.png"),
            )

        exchange.assert_called_once_with("bounded-anchor-a", 42, "frame.png", 43)
        rollback.assert_called_once_with(
            stage,
            "bounded-anchor-a",
            Path("frame.png"),
        )
        self.assertFalse(stage.published)

    def test_force_exchange_marks_published_only_after_exact_old_anchor_delete(self) -> None:
        stage = extractor.OutputStage(
            Path("private/frame.png"),
            (1, 2),
            41,
            directory_descriptor=42,
            target_directory_descriptor=43,
        )
        snapshot = extractor.PosixReplacementSnapshot(
            descriptor=44,
            identity=(1, 3),
            uid=1000,
            gid=1000,
            mode=0o640,
            extended_attributes=(),
        )
        with (
            mock.patch.object(extractor, "_verify_posix_force_directory_contract"),
            mock.patch.object(
                extractor,
                "_link_unique_posix_stage_anchor",
                return_value="bounded-anchor-b",
            ),
            mock.patch.object(extractor, "_verify_posix_replacement_metadata"),
            mock.patch.object(extractor, "_verify_posix_staged_replacement_metadata"),
            mock.patch.object(extractor, "_posix_exchange_names"),
            mock.patch.object(extractor, "_verify_posix_exchanged_replacement"),
            mock.patch.object(
                extractor,
                "_unlink_open_posix_file",
                return_value=True,
            ) as unlink,
        ):
            extractor._publish_posix_force_exchange(
                stage,
                snapshot,
                Path("frame.png"),
            )

        unlink.assert_called_once_with(
            44,
            "bounded-anchor-b",
            42,
        )
        self.assertTrue(stage.published)

    def test_auxiliary_name_fits_name_max_14_for_unicode_long_suffix(self) -> None:
        output = Path("雪." + "界" * 180)
        with (
            mock.patch.object(
                extractor.os,
                "fpathconf",
                return_value=14,
                create=True,
            ),
            mock.patch.object(extractor.secrets, "token_bytes", return_value=b"A" * 32),
        ):
            name = extractor._posix_auxiliary_name("publish", 41, output)

        self.assertEqual(len(os.fsencode(name)), 14)
        self.assertTrue(name.startswith(".x"))
        self.assertNotIn(output.suffix, name)

    def test_publication_anchor_retries_a_bounded_name_collision(self) -> None:
        stage = extractor.OutputStage(
            Path("private/frame.png"),
            (1, 2),
            41,
            directory_descriptor=42,
        )
        with (
            mock.patch.object(
                extractor,
                "_posix_auxiliary_name",
                side_effect=(".xfirsttoken12", ".xsecondtoken1"),
            ),
            mock.patch.object(
                extractor,
                "_posix_link_open_stage",
                side_effect=(FileExistsError("collision"), None),
            ) as link,
            mock.patch.object(
                extractor,
                "_unlink_open_posix_file",
                return_value=False,
            ) as unlink,
        ):
            name = extractor._link_unique_posix_stage_anchor(
                stage,
                Path("雪.png"),
            )

        self.assertEqual(name, ".xsecondtoken1")
        self.assertEqual(link.call_count, 2)
        unlink.assert_called_once_with(41, ".xfirsttoken12", 42)


class PngStreamTests(unittest.TestCase):
    def chunk(self, kind: bytes, payload: bytes) -> bytes:
        checksum = zlib.crc32(payload, zlib.crc32(kind)) & 0xFFFFFFFF
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", checksum)

    def minimal_png(self, marker: bytes) -> bytes:
        ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
        scanline = zlib.compress(b"\x00\x00\x00\x00")
        return (
            extractor._PNG_SIGNATURE
            + self.chunk(b"IHDR", ihdr)
            + self.chunk(b"tEXt", b"marker\x00" + marker)
            + self.chunk(b"IDAT", scanline)
            + self.chunk(b"IEND", b"")
        )

    def test_concatenated_stream_returns_complete_frames_in_order(self) -> None:
        first = self.minimal_png(b"first")
        last = self.minimal_png(b"last")
        stream = io.BytesIO(first + last)

        self.assertEqual(extractor._read_png_frame(stream), first)
        self.assertEqual(extractor._read_png_frame(stream), last)
        self.assertIsNone(extractor._read_png_frame(stream))

    def test_frame_stream_uses_current_passthrough_option(self) -> None:
        with mock.patch.object(
            extractor,
            "_frame_sync_options",
            return_value=("-fps_mode", "passthrough"),
        ):
            command = extractor._frame_stream_command(
                "ffmpeg",
                Path("clip.mp4"),
                first=False,
            )

        self.assertNotIn("-vsync", command)
        option = command.index("-fps_mode")
        self.assertEqual(command[option + 1], "passthrough")

    def test_frame_stream_falls_back_to_legacy_vsync_option(self) -> None:
        with mock.patch.object(
            extractor,
            "_frame_sync_options",
            return_value=("-vsync", "0"),
        ):
            command = extractor._frame_stream_command(
                "legacy-ffmpeg",
                Path("clip.mp4"),
                first=False,
            )

        self.assertNotIn("-fps_mode", command)
        option = command.index("-vsync")
        self.assertEqual(command[option + 1], "0")

    def test_frame_sync_probe_is_cached_and_prefers_current_option(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=(
                b"-vsync <> set video sync method globally\n"
                b"-fps_mode[:<stream_spec>] set framerate mode\n"
            ),
        )
        extractor._frame_sync_options.cache_clear()
        try:
            with mock.patch.object(extractor.subprocess, "run", return_value=completed) as run:
                self.assertEqual(
                    extractor._frame_sync_options("probe-ffmpeg"),
                    ("-fps_mode", "passthrough"),
                )
                self.assertEqual(
                    extractor._frame_sync_options("probe-ffmpeg"),
                    ("-fps_mode", "passthrough"),
                )
            run.assert_called_once()
        finally:
            extractor._frame_sync_options.cache_clear()

    def test_frame_sync_probe_accepts_legacy_only_help(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=b"-vsync <> set video sync method globally\n",
        )
        extractor._frame_sync_options.cache_clear()
        try:
            with mock.patch.object(extractor.subprocess, "run", return_value=completed):
                self.assertEqual(
                    extractor._frame_sync_options("legacy-probe-ffmpeg"),
                    ("-vsync", "0"),
                )
        finally:
            extractor._frame_sync_options.cache_clear()

    def test_truncated_stream_is_rejected(self) -> None:
        with self.assertRaises(extractor.FrameExtractionError):
            extractor._read_png_frame(io.BytesIO(extractor._PNG_SIGNATURE + b"\x00"))

    @unittest.skipUnless(FFMPEG, "decode-probe regression requires ffmpeg")
    def test_crc_valid_but_undecodable_png_is_rejected_by_probe(self) -> None:
        invalid = extractor._PNG_SIGNATURE + self.chunk(b"IEND", b"")

        with self.assertRaises(extractor.FrameExtractionError):
            extractor._probe_decodable_png(str(FFMPEG), invalid)

    @unittest.skipUnless(FFMPEG, "decode-probe regression requires ffmpeg")
    def test_stream_fixtures_are_genuinely_decodable_pngs(self) -> None:
        extractor._probe_decodable_png(str(FFMPEG), self.minimal_png(b"valid"))


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
            webp = root / "actual.webp"
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
            self.assertEqual(extractor.extract_frame(str(FFMPEG), clip, webp, False, False), 0)
            webp_bytes = webp.read_bytes()
            self.assertTrue(webp_bytes.startswith(b"RIFF"))
            self.assertEqual(webp_bytes[8:12], b"WEBP")
            self.assertEqual(len(self.raw_rgb(webp)), len(self.raw_rgb(expected)))
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
        security = (root / "SECURITY.md").read_text(encoding="utf-8")
        self.assertIn("same Unix account", security)
        self.assertIn("Linux access ACLs", security)
        self.assertIn("replacement is refused", security)
        self.assertIn("effective `CAP_SYS_ADMIN`", security)
        self.assertIn("creating a new output needs no capability", security)
        self.assertIn("`ReplaceFileW`", security)
        self.assertIn("non-reparse destination directory", security)
        self.assertIn("`COM¹`", security)


if __name__ == "__main__":
    unittest.main()
