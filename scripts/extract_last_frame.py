#!/usr/bin/env python3
"""Extract the last (or first) frame of an accepted clip for continuation work.

The continuation gates require the observed end state of the previous accepted
take before any successor prompt is written - but nothing paid for that
requirement: the user had to scrub the clip and describe ~10 categories by hand
for every clip of a long project. This tool removes most of that cost:

  python scripts/extract_last_frame.py takes/clip_02_take1.mp4
  python scripts/extract_last_frame.py takes/clip_02_take1.mp4 --first-frame
  python scripts/extract_last_frame.py takes/clip_02_take1.mp4 --emit-record

The extracted frame becomes (a) the continuation image reference and (b) the
agent's observation source: attach it and the AGENT fills the observation
record from what is visible, asking only about what a still can never show
(open motion, camera movement phase, audio phase). See the Observation Fast
Path in references/continuation-handoff.md and the Source-Carries-State Rule
in references/prompt-compiler.md.

Requires ffmpeg on PATH (or pass --ffmpeg /path/to/ffmpeg). The --self-test
mode is pure Python for offline CI: it verifies the observation-record template
stays aligned with the take-review schema and that no frame-readable category
is misfiled as frame-blind.

Existing output images are preserved by default. Pass --force only when replacing
one is intentional. FFmpeg streams decoded frames back to this process instead of
opening a mutable staging pathname. The retained complete frame is written through
an owned handle and published atomically, so a failed run cannot expose a partial
final output.
"""
from __future__ import annotations

import argparse
import errno
import os
import secrets
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

if os.name == "nt":
    import ctypes
    import msvcrt
    from ctypes import wintypes

# Categories the agent can read directly off the extracted still.
FRAME_READABLE = [
    ("summary", "one sentence: what is visible at the final frame"),
    ("subject_pose", "body position, hands, gaze, expression state"),
    ("screen_position", "where the subject sits in frame; travel_direction if mid-move"),
    ("wardrobe_props", "wardrobe state and prop positions vs continuity locks"),
    ("environment", "location arrangement, doors/objects state, weather"),
    ("lighting_phase", "key direction, practicals on/off, time-of-day feel"),
    ("camera_framing", "shot size and angle at the final frame"),
]
# Categories a still can NEVER show - the only things left to ask the user
# (or read from the clip itself when the full video is attached).
FRAME_BLIND = [
    ("open_motion", "what was still moving at the cut - direction and speed"),
    ("camera_move_phase", "was the camera mid-move (pan/dolly/track) and toward what"),
    ("audio_phase", "ambience bed, unfinished dialogue, music state at the cut"),
]
# Take-review fields this record feeds (schemas/take-review.schema.json).
TAKE_REVIEW_FIELDS = ["observed_end_state", "observation_confidence", "accepted_deviations"]
WINDOWS_RESERVED_STEMS = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "CLOCK$",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


class OutputPolicyError(RuntimeError):
    """The requested output operation would violate the fail-closed policy."""


class FrameExtractionError(RuntimeError):
    """FFmpeg did not yield one complete frame."""


@dataclass
class OutputStage:
    """An open staging object; its descriptor is the authority, not its name."""

    path: Path
    identity: tuple[int, int]
    descriptor: int
    directory_path: Path | None = None
    directory_identity: tuple[int, int] | None = None
    directory_descriptor: int | None = None
    target_directory_identity: tuple[int, int] | None = None
    target_directory_descriptor: int | None = None
    published: bool = False


if os.name == "nt":
    _GENERIC_READ = 0x80000000
    _GENERIC_WRITE = 0x40000000
    _DELETE = 0x00010000
    _CREATE_NEW = 1
    _FILE_ATTRIBUTE_NORMAL = 0x00000080
    _FILE_RENAME_INFO_EX_CLASS = 22
    _FILE_RENAME_FLAG_REPLACE_IF_EXISTS = 0x00000001
    _FILE_DISPOSITION_INFO_CLASS = 4
    _ERROR_FILE_EXISTS = 80
    _ERROR_ALREADY_EXISTS = 183
    _INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _CreateFileW = _kernel32.CreateFileW
    _CreateFileW.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    _CreateFileW.restype = wintypes.HANDLE
    _SetFileInformationByHandle = _kernel32.SetFileInformationByHandle
    _SetFileInformationByHandle.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    )
    _SetFileInformationByHandle.restype = wintypes.BOOL
    _CloseHandle = _kernel32.CloseHandle
    _CloseHandle.argtypes = (wintypes.HANDLE,)
    _CloseHandle.restype = wintypes.BOOL
    _GetFinalPathNameByHandleW = _kernel32.GetFinalPathNameByHandleW
    _GetFinalPathNameByHandleW.argtypes = (
        wintypes.HANDLE,
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
    )
    _GetFinalPathNameByHandleW.restype = wintypes.DWORD

    class _FileRenameInfoEx(ctypes.Structure):
        _fields_ = (
            ("Flags", wintypes.DWORD),
            ("RootDirectory", wintypes.HANDLE),
            ("FileNameLength", wintypes.DWORD),
            ("FileName", wintypes.WCHAR * 1),
        )

    class _FileDispositionInfo(ctypes.Structure):
        _fields_ = (("DeleteFile", wintypes.BOOL),)


def _identity(info: os.stat_result) -> tuple[int, int]:
    return (info.st_dev, info.st_ino)


def _is_reparse_point(info: os.stat_result) -> bool:
    flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(getattr(info, "st_file_attributes", 0) & flag)


def _path_exists(path: Path) -> bool:
    """Include dangling links: every occupied destination name is a collision."""

    return os.path.lexists(os.fspath(path))


def _paths_alias(left: Path, right: Path) -> bool:
    try:
        if left.resolve(strict=True) == right.resolve(strict=False):
            return True
    except OSError:
        pass
    if _path_exists(right):
        try:
            return os.path.samefile(left, right)
        except OSError:
            pass
    return False


def _validate_output_target(clip: Path, out: Path, force: bool) -> None:
    if os.name == "nt":
        name = out.name
        normalized = name.rstrip(" .")
        device_stem = normalized.split(".", 1)[0].upper()
        if normalized != name or ":" in name or device_stem in WINDOWS_RESERVED_STEMS:
            raise OutputPolicyError(f"unsafe Windows output filename: {name!r}")
    parent = out.parent
    if not parent.is_dir():
        raise OutputPolicyError(f"output directory not found: {parent}")
    if _paths_alias(clip, out):
        raise OutputPolicyError("output path must differ from the input clip")
    if not _path_exists(out):
        return
    if not force:
        raise OutputPolicyError(f"output already exists: {out}; choose another path or pass --force")

    # --force is deliberately narrow: it replaces a regular file, never a
    # directory, symlink, junction, device, or other special destination.
    try:
        info = os.lstat(out)
    except OSError as exc:
        raise OutputPolicyError(f"cannot inspect existing output {out}: {exc}") from exc
    if not stat.S_ISREG(info.st_mode) or _is_reparse_point(info):
        raise OutputPolicyError(f"--force only replaces a regular output file: {out}")


def _win32_extended_path(path: Path) -> str:
    absolute = str(path.resolve())
    if absolute.startswith("\\\\?\\"):
        return absolute
    if absolute.startswith("\\\\"):
        return "\\\\?\\UNC\\" + absolute[2:]
    return "\\\\?\\" + absolute


def _win32_stage_descriptor(path: Path) -> int:
    handle = _CreateFileW(
        _win32_extended_path(path),
        _GENERIC_READ | _GENERIC_WRITE | _DELETE,
        0,  # deny read/write/delete sharing while the staging name exists
        None,
        _CREATE_NEW,
        _FILE_ATTRIBUTE_NORMAL,
        None,
    )
    if handle == _INVALID_HANDLE_VALUE:
        error = ctypes.get_last_error()
        if error in (_ERROR_FILE_EXISTS, _ERROR_ALREADY_EXISTS):
            raise FileExistsError(error, "staging path already exists", str(path))
        raise OSError(error, ctypes.FormatError(error), str(path))
    try:
        return msvcrt.open_osfhandle(
            int(handle), os.O_RDWR | getattr(os, "O_BINARY", 0)
        )
    except Exception:
        _CloseHandle(handle)
        raise


def _win32_target_from_stage_handle(stage: OutputStage, out: Path) -> str:
    """Bind the destination to the staging handle's resolved parent directory."""

    handle = wintypes.HANDLE(msvcrt.get_osfhandle(stage.descriptor))
    required = _GetFinalPathNameByHandleW(handle, None, 0, 0)
    if not required:
        error = ctypes.get_last_error()
        raise OutputPolicyError(
            "could not resolve the owned staging handle: "
            f"[WinError {error}] {ctypes.FormatError(error).strip()}"
        )
    buffer = ctypes.create_unicode_buffer(required + 1)
    written = _GetFinalPathNameByHandleW(handle, buffer, len(buffer), 0)
    if not written or written >= len(buffer):
        error = ctypes.get_last_error()
        raise OutputPolicyError(
            "could not read the owned staging path: "
            f"[WinError {error}] {ctypes.FormatError(error).strip()}"
        )

    resolved = buffer.value
    if resolved.startswith("\\\\?\\UNC\\"):
        dos_stage = "\\\\" + resolved[8:]
    elif resolved.startswith("\\\\?\\"):
        dos_stage = resolved[4:]
    else:
        raise OutputPolicyError("owned staging handle returned an unsupported Windows path")
    anchored_stage = Path(dos_stage)
    if anchored_stage.name.casefold() != stage.path.name.casefold():
        raise OutputPolicyError("owned staging handle name changed; refusing publication")

    try:
        anchored_parent = os.stat(anchored_stage.parent)
        requested_parent = os.stat(out.parent)
    except OSError as exc:
        raise OutputPolicyError(f"cannot verify output directory identity: {exc}") from exc
    if _identity(anchored_parent) != _identity(requested_parent):
        raise OutputPolicyError("output directory identity changed; refusing publication")

    dos_target = str(anchored_stage.with_name(out.name))
    if dos_target.startswith("\\\\"):
        return "\\??\\UNC\\" + dos_target[2:]
    return "\\??\\" + dos_target


def _win32_rename_by_handle(stage: OutputStage, out: Path, force: bool) -> None:
    handle = wintypes.HANDLE(msvcrt.get_osfhandle(stage.descriptor))
    # SetFileInformationByHandle consumes the NT object-manager spelling here.
    # A DOS path can fail with ERROR_INVALID_NAME under the Windows sandbox,
    # while a bare filename is resolved against the process cwd. Deriving the
    # absolute target from the open staging handle also prevents a replaced
    # parent junction from redirecting publication.
    encoded_name = _win32_target_from_stage_handle(stage, out).encode("utf-16-le")
    offset = _FileRenameInfoEx.FileName.offset
    # Microsoft's FILE_RENAME_INFORMATION contract requires at least the fixed
    # structure size plus the variable filename bytes, not merely the offset of
    # FileName plus those bytes.
    buffer = ctypes.create_string_buffer(ctypes.sizeof(_FileRenameInfoEx) + len(encoded_name))
    info = ctypes.cast(buffer, ctypes.POINTER(_FileRenameInfoEx)).contents
    info.Flags = _FILE_RENAME_FLAG_REPLACE_IF_EXISTS if force else 0
    info.RootDirectory = None
    info.FileNameLength = len(encoded_name)
    ctypes.memmove(ctypes.addressof(buffer) + offset, encoded_name, len(encoded_name))
    if _SetFileInformationByHandle(
        handle, _FILE_RENAME_INFO_EX_CLASS, buffer, len(buffer)
    ):
        return
    error = ctypes.get_last_error()
    if not force and error in (_ERROR_FILE_EXISTS, _ERROR_ALREADY_EXISTS):
        raise OutputPolicyError(f"output appeared during extraction and was preserved: {out}")
    raise OutputPolicyError(
        f"could not atomically {'replace' if force else 'publish'} output {out}: "
        f"[WinError {error}] {ctypes.FormatError(error).strip()}"
    )


def _win32_mark_stage_for_deletion(stage: OutputStage) -> bool:
    handle = wintypes.HANDLE(msvcrt.get_osfhandle(stage.descriptor))
    disposition = _FileDispositionInfo(1)
    if _SetFileInformationByHandle(
        handle,
        _FILE_DISPOSITION_INFO_CLASS,
        ctypes.byref(disposition),
        ctypes.sizeof(disposition),
    ):
        return True
    error = ctypes.get_last_error()
    sys.stderr.write(
        f"warning: could not delete owned staging handle for {stage.path}: "
        f"[WinError {error}] {ctypes.FormatError(error).strip()}\n"
    )
    return False


def _create_output_stage(out: Path) -> OutputStage:
    suffix = out.suffix or ".img"
    prefix = f".{out.stem}.atomic-"
    if os.name == "nt":
        for _attempt in range(64):
            path = out.parent / f"{prefix}{secrets.token_hex(16)}{suffix}"
            try:
                descriptor = _win32_stage_descriptor(path)
            except FileExistsError:
                continue
            except OSError as exc:
                raise OutputPolicyError(
                    f"cannot create locked output staging file beside {out}: {exc}"
                ) from exc
            info = os.fstat(descriptor)
            return OutputStage(path, _identity(info), descriptor)
        raise OutputPolicyError("could not allocate a unique output staging name")

    target_directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    private_directory_flags = (
        target_directory_flags
        | getattr(os, "O_NOFOLLOW", 0)
    )
    target_descriptor = -1
    directory_descriptor = -1
    descriptor = -1
    directory_path: Path | None = None
    directory_identity: tuple[int, int] | None = None
    try:
        # Keep the mutable staging name inside a private directory. Directory
        # descriptors then anchor every lookup even if the parent pathname is
        # renamed concurrently. The output inode itself is created with 0666,
        # so the caller's umask produces the same permissions as an ordinary
        # newly-created image rather than mkstemp's hard-coded 0600.
        target_descriptor = os.open(out.parent, target_directory_flags)
        target_info = os.fstat(target_descriptor)
        for _attempt in range(64):
            directory_name = f"{prefix}{secrets.token_hex(16)}"
            try:
                os.mkdir(directory_name, 0o700, dir_fd=target_descriptor)
            except FileExistsError:
                continue
            directory_path = out.parent / directory_name
            break
        else:
            raise OutputPolicyError(
                "could not allocate a unique private output staging directory"
            )
        created_directory = os.stat(
            directory_path.name,
            dir_fd=target_descriptor,
            follow_symlinks=False,
        )
        directory_identity = _identity(created_directory)
        if (
            not stat.S_ISDIR(created_directory.st_mode)
            or (
                hasattr(os, "geteuid")
                and created_directory.st_uid != os.geteuid()
            )
        ):
            raise OutputPolicyError(
                "created output staging directory is not privately owned"
            )
        directory_descriptor = os.open(
            directory_path.name,
            private_directory_flags,
            dir_fd=target_descriptor,
        )
        opened_directory = os.fstat(directory_descriptor)
        if (
            not stat.S_ISDIR(opened_directory.st_mode)
            or _identity(opened_directory) != directory_identity
        ):
            raise OutputPolicyError(
                "output staging directory changed while opening; refusing publication"
            )
        os.fchmod(directory_descriptor, 0o700)
        directory_info = os.fstat(directory_descriptor)
        named_directory = os.stat(
            directory_path.name,
            dir_fd=target_descriptor,
            follow_symlinks=False,
        )
        if (
            not stat.S_ISDIR(directory_info.st_mode)
            or not stat.S_ISDIR(named_directory.st_mode)
            or stat.S_IMODE(directory_info.st_mode) != 0o700
            or _identity(named_directory) != directory_identity
            or _identity(directory_info) != directory_identity
            or _identity(os.stat(out.parent)) != _identity(target_info)
        ):
            raise OutputPolicyError(
                "output staging directory identity changed; refusing publication"
            )

        stage_name = f"frame{suffix}"
        descriptor = os.open(
            stage_name,
            os.O_RDWR
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_CLOEXEC", 0),
            0o666,
            dir_fd=directory_descriptor,
        )
        info = os.fstat(descriptor)
        return OutputStage(
            directory_path / stage_name,
            _identity(info),
            descriptor,
            directory_path=directory_path,
            directory_identity=directory_identity,
            directory_descriptor=directory_descriptor,
            target_directory_identity=_identity(target_info),
            target_directory_descriptor=target_descriptor,
        )
    except (OSError, OutputPolicyError) as exc:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if directory_descriptor >= 0:
            try:
                os.close(directory_descriptor)
            except OSError:
                pass
        if directory_path is not None and target_descriptor >= 0:
            try:
                named_directory = os.stat(
                    directory_path.name,
                    dir_fd=target_descriptor,
                    follow_symlinks=False,
                )
                if (
                    directory_identity is not None
                    and _identity(named_directory) == directory_identity
                ):
                    os.rmdir(directory_path.name, dir_fd=target_descriptor)
            except OSError:
                pass
        if target_descriptor >= 0:
            try:
                os.close(target_descriptor)
            except OSError:
                pass
        if isinstance(exc, OutputPolicyError):
            raise
        raise OutputPolicyError(
            f"cannot create protected output staging file beside {out}: {exc}"
        ) from exc


def _verify_output_stage(stage: OutputStage, *, require_content: bool) -> None:
    """Verify the open object; a pathname lookup is never the authority."""
    try:
        opened = os.fstat(stage.descriptor)
    except OSError as exc:
        raise OutputPolicyError(f"cannot verify output staging file: {exc}") from exc
    if (
        not stat.S_ISREG(opened.st_mode)
        or _identity(opened) != stage.identity
        or opened.st_nlink != 1
    ):
        raise OutputPolicyError("output staging handle identity changed; refusing publication")
    if require_content and opened.st_size == 0:
        raise OutputPolicyError("frame encoder produced an empty output staging file")
    os.fsync(stage.descriptor)

    if os.name != "nt":
        if stage.directory_descriptor is None:
            raise OutputPolicyError("output staging directory handle is unavailable")
        try:
            named = os.stat(
                stage.path.name,
                dir_fd=stage.directory_descriptor,
                follow_symlinks=False,
            )
        except OSError as exc:
            raise OutputPolicyError("output staging name disappeared while verifying") from exc
        if (
            not stat.S_ISREG(named.st_mode)
            or _is_reparse_point(named)
            or _identity(named) != stage.identity
            or named.st_nlink != 1
        ):
            raise OutputPolicyError("output staging name changed; refusing publication")


def _verify_posix_target_directory(stage: OutputStage, out: Path) -> None:
    if (
        stage.target_directory_descriptor is None
        or stage.target_directory_identity is None
    ):
        raise OutputPolicyError("output directory handle is unavailable")
    try:
        opened = os.fstat(stage.target_directory_descriptor)
        named = os.stat(out.parent)
    except OSError as exc:
        raise OutputPolicyError(f"cannot verify output directory identity: {exc}") from exc
    if (
        not stat.S_ISDIR(opened.st_mode)
        or _identity(opened) != stage.target_directory_identity
        or _identity(named) != stage.target_directory_identity
    ):
        raise OutputPolicyError("output directory identity changed; refusing publication")


def _posix_link_open_stage(
    stage: OutputStage,
    destination_name: str,
    destination_directory_descriptor: int,
) -> None:
    """Link the open inode, not the staging pathname, whenever POSIX exposes it."""

    if stage.directory_descriptor is None:
        raise OutputPolicyError("output staging directory handle is unavailable")

    # Linux documents /proc/self/fd + linkat(AT_SYMLINK_FOLLOW) as the
    # unprivileged descriptor-bound alternative to linkat(AT_EMPTY_PATH).
    # The magic link continues to name this open file description after an
    # attacker renames or replaces stage.path.
    if sys.platform.startswith("linux"):
        descriptor_path = f"/proc/self/fd/{stage.descriptor}"
        try:
            os.link(
                descriptor_path,
                destination_name,
                dst_dir_fd=destination_directory_descriptor,
                follow_symlinks=True,
            )
            return
        except OSError as exc:
            # Minimal/container POSIX environments may omit procfs. The
            # fallback name lives inside the verified 0700 private directory,
            # not in the attacker-writable output directory. That blocks
            # cross-account writers; a hostile process running under this same
            # Unix account shares the permission boundary and is explicitly
            # outside this fallback's guarantee.
            if exc.errno not in {
                errno.ENOENT,
                errno.EINVAL,
                getattr(errno, "ENOTSUP", errno.EOPNOTSUPP),
                errno.EPERM,
            }:
                raise

    _verify_output_stage(stage, require_content=True)
    os.link(
        stage.path.name,
        destination_name,
        src_dir_fd=stage.directory_descriptor,
        dst_dir_fd=destination_directory_descriptor,
        follow_symlinks=False,
    )
    linked = os.stat(
        destination_name,
        dir_fd=destination_directory_descriptor,
        follow_symlinks=False,
    )
    if _identity(linked) != stage.identity:
        raise OutputPolicyError(
            "published output does not match the verified staging inode"
        )


def _preserve_posix_replacement_permissions(stage: OutputStage, out: Path) -> None:
    """Carry POSIX owner, group, and mode across an intentional replacement."""

    if stage.target_directory_descriptor is None:
        raise OutputPolicyError("output directory handle is unavailable")
    try:
        existing = os.stat(
            out.name,
            dir_fd=stage.target_directory_descriptor,
            follow_symlinks=False,
        )
        staged = os.fstat(stage.descriptor)
        if not stat.S_ISREG(existing.st_mode):
            raise OutputPolicyError(
                f"--force only replaces a regular output file: {out}"
            )
        if (
            hasattr(os, "fchown")
            and (staged.st_uid != existing.st_uid or staged.st_gid != existing.st_gid)
        ):
            os.fchown(stage.descriptor, existing.st_uid, existing.st_gid)
        os.fchmod(stage.descriptor, stat.S_IMODE(existing.st_mode))
        os.fsync(stage.descriptor)
    except OutputPolicyError:
        raise
    except OSError as exc:
        raise OutputPolicyError(
            f"cannot preserve existing output permissions for {out}: {exc}"
        ) from exc


def _write_output_stage(stage: OutputStage, content: bytes) -> None:
    try:
        os.lseek(stage.descriptor, 0, os.SEEK_SET)
        os.ftruncate(stage.descriptor, 0)
        remaining = memoryview(content)
        while remaining:
            written = os.write(stage.descriptor, remaining)
            if written <= 0:
                raise OSError("short write to output staging handle")
            remaining = remaining[written:]
        _verify_output_stage(stage, require_content=True)
    except OutputPolicyError:
        raise
    except OSError as exc:
        raise OutputPolicyError(f"could not write output staging handle: {exc}") from exc


def _cleanup_output_stage(stage: OutputStage) -> bool:
    """Delete the owned handle on Windows; never unlink a re-looked-up name."""

    success = True
    try:
        if os.name == "nt":
            if not stage.published:
                success = _win32_mark_stage_for_deletion(stage)
        else:
            try:
                if stage.directory_descriptor is None:
                    raise OSError("staging directory handle is unavailable")
                info = os.stat(
                    stage.path.name,
                    dir_fd=stage.directory_descriptor,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                info = None
            except OSError as exc:
                sys.stderr.write(f"warning: could not inspect staging path {stage.path}: {exc}\n")
                success = False
                info = None
            if info is not None:
                if (
                    not stat.S_ISREG(info.st_mode)
                    or _is_reparse_point(info)
                    or _identity(info) != stage.identity
                ):
                    sys.stderr.write(
                        "warning: staging path identity changed; leaving unexpected path "
                        f"untouched: {stage.path}\n"
                    )
                    success = False
                else:
                    try:
                        os.unlink(stage.path.name, dir_fd=stage.directory_descriptor)
                    except OSError as exc:
                        sys.stderr.write(
                            f"warning: could not remove staging file {stage.path}: {exc}\n"
                        )
                        success = False
    finally:
        try:
            os.close(stage.descriptor)
        except OSError as exc:
            sys.stderr.write(f"warning: could not close staging handle: {exc}\n")
            success = False
        stage.descriptor = -1
        if os.name != "nt":
            if stage.directory_descriptor is not None:
                try:
                    os.close(stage.directory_descriptor)
                except OSError as exc:
                    sys.stderr.write(
                        f"warning: could not close staging directory handle: {exc}\n"
                    )
                    success = False
                stage.directory_descriptor = None
            if (
                stage.directory_path is not None
                and stage.directory_identity is not None
                and stage.target_directory_descriptor is not None
            ):
                try:
                    named_directory = os.stat(
                        stage.directory_path.name,
                        dir_fd=stage.target_directory_descriptor,
                        follow_symlinks=False,
                    )
                    if _identity(named_directory) != stage.directory_identity:
                        raise OSError("staging directory identity changed")
                    os.rmdir(
                        stage.directory_path.name,
                        dir_fd=stage.target_directory_descriptor,
                    )
                except FileNotFoundError:
                    pass
                except OSError as exc:
                    sys.stderr.write(
                        "warning: could not remove protected staging directory "
                        f"{stage.directory_path}: {exc}\n"
                    )
                    success = False
            if stage.target_directory_descriptor is not None:
                try:
                    os.close(stage.target_directory_descriptor)
                except OSError as exc:
                    sys.stderr.write(
                        f"warning: could not close output directory handle: {exc}\n"
                    )
                    success = False
                stage.target_directory_descriptor = None
    return success


def _publish_output(stage: OutputStage, clip: Path, out: Path, force: bool) -> None:
    _verify_output_stage(stage, require_content=True)
    # Re-check immediately before publication. The locked Windows staging name
    # cannot be swapped before the atomic link/handle-rename operations below.
    _validate_output_target(clip, out, force)
    if os.name == "nt":
        if not force:
            try:
                # The exclusive handle prevents the source name from being
                # swapped; hard-link creation is an atomic no-replace claim on
                # the destination. Cleanup then deletes only the staging link.
                os.link(stage.path, out)
            except FileExistsError as exc:
                raise OutputPolicyError(
                    f"output appeared during extraction and was preserved: {out}"
                ) from exc
            except OSError as exc:
                raise OutputPolicyError(
                    f"could not atomically publish output {out}: {exc}"
                ) from exc
            return
        # Mark first so an asynchronous interruption immediately after the
        # native rename can never make cleanup delete a successfully published
        # replacement. Ordinary failures reset the marker and delete the exact
        # still-owned staging handle.
        stage.published = True
        try:
            _win32_rename_by_handle(stage, out, force)
        except Exception:
            stage.published = False
            raise
        return

    _verify_posix_target_directory(stage, out)

    if force:
        _preserve_posix_replacement_permissions(stage, out)
        if stage.directory_descriptor is None or stage.target_directory_descriptor is None:
            raise OutputPolicyError("POSIX publication handles are unavailable")
        publish_name = f"publish-{secrets.token_hex(16)}{out.suffix or '.img'}"
        try:
            # Create the rename source from the verified descriptor inside the
            # private staging directory, then atomically replace the target by
            # directory descriptor. A swapped stage.path is never consulted.
            _posix_link_open_stage(
                stage,
                publish_name,
                stage.directory_descriptor,
            )
            os.replace(
                publish_name,
                out.name,
                src_dir_fd=stage.directory_descriptor,
                dst_dir_fd=stage.target_directory_descriptor,
            )
        except (OSError, OutputPolicyError) as exc:
            try:
                linked = os.stat(
                    publish_name,
                    dir_fd=stage.directory_descriptor,
                    follow_symlinks=False,
                )
                if _identity(linked) == stage.identity:
                    os.unlink(publish_name, dir_fd=stage.directory_descriptor)
            except OSError:
                pass
            if isinstance(exc, OutputPolicyError):
                raise
            raise OutputPolicyError(f"could not atomically replace output {out}: {exc}") from exc
        stage.published = True
        return

    if stage.target_directory_descriptor is None:
        raise OutputPolicyError("output directory handle is unavailable")
    try:
        # The descriptor-bound hard link is an atomic no-replace publication:
        # creation fails if any object claimed the destination name meanwhile.
        _posix_link_open_stage(stage, out.name, stage.target_directory_descriptor)
    except FileExistsError as exc:
        raise OutputPolicyError(f"output appeared during extraction and was preserved: {out}") from exc
    except OSError as exc:
        raise OutputPolicyError(f"could not atomically publish output {out}: {exc}") from exc
    stage.published = True


_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_MAX_PNG_CHUNK_BYTES = 256 * 1024 * 1024
_MAX_FRAME_BYTES = 512 * 1024 * 1024
_OUTPUT_CODECS = {
    ".png": "png",
    ".jpg": "mjpeg",
    ".jpeg": "mjpeg",
    ".webp": "libwebp",
    ".bmp": "bmp",
    ".tif": "tiff",
    ".tiff": "tiff",
}


def _read_exact(stream: BinaryIO, size: int, *, allow_clean_eof: bool = False) -> bytes | None:
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = stream.read(remaining)
        if not chunk:
            if allow_clean_eof and remaining == size:
                return None
            raise FrameExtractionError("truncated PNG stream from ffmpeg")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _read_png_frame(stream: BinaryIO) -> bytes | None:
    signature = _read_exact(stream, len(_PNG_SIGNATURE), allow_clean_eof=True)
    if signature is None:
        return None
    if signature != _PNG_SIGNATURE:
        raise FrameExtractionError("ffmpeg emitted a malformed PNG frame stream")
    frame = bytearray(signature)
    while True:
        header = _read_exact(stream, 8)
        assert header is not None
        length = struct.unpack(">I", header[:4])[0]
        chunk_type = header[4:]
        if length > _MAX_PNG_CHUNK_BYTES:
            raise FrameExtractionError("ffmpeg PNG chunk exceeds the safety limit")
        payload_and_crc = _read_exact(stream, length + 4)
        assert payload_and_crc is not None
        payload = payload_and_crc[:length]
        expected_crc = struct.unpack(">I", payload_and_crc[length:])[0]
        actual_crc = zlib.crc32(payload, zlib.crc32(chunk_type)) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            raise FrameExtractionError("ffmpeg emitted a PNG frame with an invalid checksum")
        frame.extend(header)
        frame.extend(payload_and_crc)
        if len(frame) > _MAX_FRAME_BYTES:
            raise FrameExtractionError("ffmpeg frame exceeds the safety limit")
        if chunk_type == b"IEND":
            if length != 0:
                raise FrameExtractionError("ffmpeg emitted an invalid PNG terminator")
            return bytes(frame)


def render_frame_png(ffmpeg: str, clip: Path, first: bool) -> bytes:
    """Stream every decoded frame and retain only the final complete PNG."""

    cmd = [
        ffmpeg,
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(clip),
    ]
    if first:
        cmd += ["-frames:v", "1"]
    cmd += ["-an", "-vsync", "0", "-f", "image2pipe", "-vcodec", "png", "pipe:1"]

    with tempfile.TemporaryFile(mode="w+b") as stderr_file:
        try:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=stderr_file,
            )
        except OSError as exc:
            raise FrameExtractionError(f"could not start ffmpeg: {exc}") from exc
        assert process.stdout is not None
        last_frame: bytes | None = None
        try:
            while True:
                frame = _read_png_frame(process.stdout)
                if frame is None:
                    break
                last_frame = frame
        except Exception:
            process.kill()
            process.wait()
            raise
        finally:
            process.stdout.close()
        returncode = process.wait()
        stderr_file.seek(0)
        stderr_text = stderr_file.read().decode("utf-8", errors="replace")[-800:].strip()
    if returncode != 0 or last_frame is None:
        detail = stderr_text or "ffmpeg returned no complete video frame"
        raise FrameExtractionError(detail)
    return last_frame


def _encode_frame_for_output(ffmpeg: str, png_frame: bytes, out: Path) -> bytes:
    codec = _OUTPUT_CODECS.get(out.suffix.lower())
    if codec is None:
        supported = ", ".join(sorted(_OUTPUT_CODECS))
        raise OutputPolicyError(f"unsupported output image suffix {out.suffix!r}; use one of: {supported}")
    if codec == "png":
        return png_frame
    cmd = [
        ffmpeg,
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        "pipe:0",
        "-frames:v",
        "1",
        "-f",
        "image2pipe",
        "-vcodec",
        codec,
        "pipe:1",
    ]
    process = subprocess.run(cmd, input=png_frame, capture_output=True)
    if process.returncode != 0 or not process.stdout:
        detail = process.stderr.decode("utf-8", errors="replace")[-800:].strip()
        raise FrameExtractionError(detail or f"ffmpeg could not encode {out.suffix}")
    return process.stdout


def extract_frame(ffmpeg: str, clip: Path, out: Path, first: bool, force: bool) -> int:
    _validate_output_target(clip, out, force)
    if out.suffix.lower() not in _OUTPUT_CODECS:
        supported = ", ".join(sorted(_OUTPUT_CODECS))
        raise OutputPolicyError(f"unsupported output image suffix {out.suffix!r}; use one of: {supported}")
    png_frame = render_frame_png(ffmpeg, clip, first)
    content = _encode_frame_for_output(ffmpeg, png_frame, out)
    stage = _create_output_stage(out)
    try:
        _write_output_stage(stage, content)
        _publish_output(stage, clip, out, force)
        print(f"{'first' if first else 'last'} frame -> {out}")
        return 0
    finally:
        _cleanup_output_stage(stage)


def build_record() -> str:
    lines = ["OBSERVATION RECORD (fills observed_end_state; agent completes from the frame)"]
    lines.append("\n# Read from the extracted frame - the agent fills these, not the user:")
    lines += [f"- {k}: ...  ({hint})" for k, hint in FRAME_READABLE]
    lines.append("\n# A still cannot show these - ask the user, or read from the attached clip:")
    lines += [f"- {k}: ...  ({hint})" for k, hint in FRAME_BLIND]
    lines.append("\n# Then set observation_confidence (high with frame attached; note any unreadable area)")
    lines.append("# and list accepted_deviations vs the planned end state before reconciling canon.")
    return "\n".join(lines)


def run_ffmpeg(
    ffmpeg: str,
    clip: Path,
    out: Path,
    first: bool,
    force: bool = False,
) -> int:
    """Compatibility entry point with the same fail-closed policy as the CLI.

    Earlier callers imported this helper directly, so leaving its historical
    unconditional ``-y`` command in place would preserve an overwrite bypass
    after the CLI was repaired. Keep the integer-returning interface, but route
    every caller through the owned-stage and atomic-publication implementation.
    """
    try:
        return extract_frame(ffmpeg, clip, out, first, force)
    except OutputPolicyError as exc:
        print(f"output refused: {exc}")
    except FrameExtractionError as exc:
        print(f"extraction failed for {clip}: {exc}")
    except OSError as exc:
        print(f"output failed safely: {exc}")
    return 1


def self_test() -> int:
    errors: list[str] = []
    record = build_record()
    for key, _ in FRAME_READABLE + FRAME_BLIND:
        if f"- {key}:" not in record:
            errors.append(f"record template missing category {key}")
    for field in TAKE_REVIEW_FIELDS:
        if field not in record:
            errors.append(f"record template must mention take-review field {field}")
    overlap = {k for k, _ in FRAME_READABLE} & {k for k, _ in FRAME_BLIND}
    if overlap:
        errors.append(f"categories filed as both frame-readable and frame-blind: {sorted(overlap)}")
    for blind in ("open_motion", "camera_move_phase", "audio_phase"):
        if blind in {k for k, _ in FRAME_READABLE}:
            errors.append(f"{blind} cannot be read from a still and must stay frame-blind")
    schema = Path(__file__).resolve().parent.parent / "schemas" / "take-review.schema.json"
    if not schema.exists():
        errors.append("schemas/take-review.schema.json missing")
    if errors:
        print("extract_last_frame self-test FAILED:")
        for e in errors:
            print(f"- {e}")
        return 1
    print(f"extract_last_frame self-test passed: {len(FRAME_READABLE)} frame-readable + "
          f"{len(FRAME_BLIND)} frame-blind categories, take-review fields referenced.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Extract the last/first frame of an accepted clip. The default behavior refuses "
            "to replace an existing output."
        )
    )
    parser.add_argument("clip", nargs="?", help="path to the accepted take (mp4/mov/webm)")
    parser.add_argument(
        "-o",
        "--output",
        help=(
            "output image path: png/jpg/jpeg/webp/bmp/tif/tiff "
            "(default: <clip>.last.png / .first.png)"
        ),
    )
    parser.add_argument("--first-frame", action="store_true", help="extract the first frame instead")
    parser.add_argument("--ffmpeg", default=None, help="path to ffmpeg if not on PATH")
    parser.add_argument(
        "--force",
        action="store_true",
        help="atomically replace an existing regular output file after extraction succeeds",
    )
    parser.add_argument("--emit-record", action="store_true", help="print the observation-record skeleton")
    parser.add_argument("--self-test", action="store_true", help="offline wiring check, no ffmpeg or media")
    parser.add_argument("--strict", action="store_true", help="accepted for parity with other validators")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if args.emit_record and not args.clip:
        print(build_record())
        return 0
    if not args.clip:
        parser.error("clip path required (or use --self-test / --emit-record)")

    clip = Path(args.clip)
    if not clip.exists():
        print(f"clip not found: {clip}")
        return 1
    ffmpeg = args.ffmpeg or shutil.which("ffmpeg")
    if not ffmpeg:
        print("ffmpeg not found on PATH; install it or pass --ffmpeg /path/to/ffmpeg")
        return 2
    suffix = ".first.png" if args.first_frame else ".last.png"
    out = Path(args.output) if args.output else clip.with_suffix(clip.suffix + suffix)
    try:
        rc = extract_frame(ffmpeg, clip, out, args.first_frame, args.force)
    except OutputPolicyError as exc:
        print(f"output refused: {exc}")
        return 1
    except FrameExtractionError as exc:
        print(f"extraction failed for {clip}: {exc}")
        return 1
    except OSError as exc:
        print(f"output failed safely: {exc}")
        return 1
    if rc == 0 and args.emit_record:
        print()
        print(build_record())
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
