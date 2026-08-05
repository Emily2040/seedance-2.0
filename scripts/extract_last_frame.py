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
opening a mutable staging pathname. A separate bounded FFmpeg invocation must decode
the retained PNG before it is written through an owned handle and published
atomically, so a failed run cannot expose a partial or undecodable final output.
"""
from __future__ import annotations

import argparse
import base64
import ctypes
import errno
import functools
import hashlib
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
from typing import BinaryIO, TextIO

if os.name == "nt":
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
    *(f"COM{digit}" for digit in "¹²³"),
    *(f"LPT{digit}" for digit in "¹²³"),
}


class OutputPolicyError(RuntimeError):
    """The requested output operation would violate the fail-closed policy."""


class FrameExtractionError(RuntimeError):
    """FFmpeg did not yield one complete frame."""


_DEFAULT_CONSOLE_STREAM = object()


def _write_console_line(
    message: object,
    *,
    stream: TextIO | None | object = _DEFAULT_CONSOLE_STREAM,
) -> None:
    """Best-effort status output that can never change publication state."""

    target = sys.stdout if stream is _DEFAULT_CONSOLE_STREAM else stream
    if target is None:
        return
    try:
        text = str(message)
        encoding = getattr(target, "encoding", None)
        if encoding:
            text = text.encode(encoding, errors="backslashreplace").decode(encoding)
        target.write(text + "\n")
    except (AttributeError, OSError, UnicodeError, ValueError):
        # ``pythonw.exe`` exposes no console streams, redirected consumers can
        # close a pipe at any time, and StringIO raises ValueError once closed.
        # Reporting is deliberately non-transactional: a completed atomic
        # publication remains success even when there is nowhere to print it.
        return


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


@dataclass(frozen=True)
class PosixReplacementSnapshot:
    """Descriptor-bound metadata that must still match at publication."""

    descriptor: int
    identity: tuple[int, int]
    uid: int
    gid: int
    mode: int
    extended_attributes: tuple[tuple[str, bytes], ...]


@dataclass
class WindowsReplacementSnapshot:
    """Handle-bound Windows policy that must still match before replacement."""

    descriptor: int
    identity: tuple[int, int]
    security_policy: str
    policy_attributes: int
    named_streams: tuple[str, ...]
    content_digest: bytes


@dataclass(frozen=True)
class WindowsArtifactState:
    """Identity, policy, and bytes for one transaction-bound Windows file."""

    identity: tuple[int, int]
    security_policy: str
    policy_attributes: int
    named_streams: tuple[str, ...]
    content_digest: bytes


def _split_win32_security_policy(policy: str) -> tuple[str, str, str, str, str]:
    """Return owner, group, DACL entries/control, and label SDDL components."""

    sections: dict[str, str] = {label: "" for label in "OGDS"}
    starts = sorted(
        (position, label)
        for label in sections
        if (position := policy.find(f"{label}:")) >= 0
    )
    for index, (position, label) in enumerate(starts):
        end = starts[index + 1][0] if index + 1 < len(starts) else len(policy)
        sections[label] = policy[position + 2 : end]

    dacl = sections["D"]
    first_ace = dacl.find("(")
    if first_ace < 0:
        dacl_control, dacl_entries = dacl, ""
    else:
        dacl_control, dacl_entries = dacl[:first_ace], dacl[first_ace:]
    return (
        sections["O"],
        sections["G"],
        dacl_entries,
        dacl_control,
        sections["S"],
    )


def _win32_artifact_differences(
    expected: WindowsArtifactState,
    observed: WindowsArtifactState,
) -> tuple[str, ...]:
    """Name mismatched postconditions without logging policy or file contents."""

    differences: list[str] = []
    if expected.content_digest != observed.content_digest:
        differences.append("bytes")
    if expected.identity != observed.identity:
        differences.append("file identity")
    if expected.security_policy != observed.security_policy:
        expected_security = _split_win32_security_policy(expected.security_policy)
        observed_security = _split_win32_security_policy(observed.security_policy)
        labels = (
            "owner",
            "group",
            "DACL entries",
            "DACL control flags",
            "mandatory label",
        )
        security_differences = [
            label
            for label, expected_value, observed_value in zip(
                labels, expected_security, observed_security
            )
            if expected_value != observed_value
        ]
        differences.extend(security_differences or ("security descriptor",))
    if expected.named_streams != observed.named_streams:
        differences.append("named streams (ADS)")
    if expected.policy_attributes != observed.policy_attributes:
        differences.append("policy attributes")
    return tuple(differences)


@dataclass
class PosixProbeArtifact:
    """One created exchange-probe inode, tracked before any fallible stat."""

    name: str
    directory_descriptor: int
    descriptor: int
    identity: tuple[int, int] | None = None


if os.name == "nt":
    _GENERIC_READ = 0x80000000
    _GENERIC_WRITE = 0x40000000
    _DELETE = 0x00010000
    _READ_CONTROL = 0x00020000
    _WRITE_DAC = 0x00040000
    _FILE_READ_ATTRIBUTES = 0x00000080
    _FILE_SHARE_READ = 0x00000001
    _FILE_SHARE_WRITE = 0x00000002
    _FILE_SHARE_DELETE = 0x00000004
    _CREATE_NEW = 1
    _OPEN_EXISTING = 3
    _FILE_ATTRIBUTE_NORMAL = 0x00000080
    _FILE_ATTRIBUTE_ARCHIVE = 0x00000020
    _FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
    _FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    _FILE_STREAM_INFO_CLASS = 7
    _FILE_RENAME_INFO_EX_CLASS = 22
    _FILE_RENAME_FLAG_REPLACE_IF_EXISTS = 0x00000001
    _FILE_RENAME_FLAG_POSIX_SEMANTICS = 0x00000002
    _FILE_DISPOSITION_INFO_CLASS = 4
    _ERROR_FILE_EXISTS = 80
    _ERROR_ALREADY_EXISTS = 183
    _ERROR_HANDLE_EOF = 38
    _ERROR_INSUFFICIENT_BUFFER = 122
    _ERROR_MORE_DATA = 234
    _ERROR_UNABLE_TO_REMOVE_REPLACED = 1175
    _ERROR_UNABLE_TO_MOVE_REPLACEMENT = 1176
    _ERROR_UNABLE_TO_MOVE_REPLACEMENT_2 = 1177
    _INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
    _OWNER_SECURITY_INFORMATION = 0x00000001
    _GROUP_SECURITY_INFORMATION = 0x00000002
    _DACL_SECURITY_INFORMATION = 0x00000004
    _SACL_SECURITY_INFORMATION = 0x00000008
    _LABEL_SECURITY_INFORMATION = 0x00000010
    _SDDL_REVISION_1 = 1
    _SE_DACL_AUTO_INHERIT_REQ = 0x0100
    _SE_DACL_AUTO_INHERITED = 0x0400
    _SE_DACL_PROTECTED = 0x1000
    _WINDOWS_POLICY_SECURITY_INFORMATION = (
        _OWNER_SECURITY_INFORMATION
        | _GROUP_SECURITY_INFORMATION
        | _DACL_SECURITY_INFORMATION
        | _LABEL_SECURITY_INFORMATION
    )
    # Archive is ordinary content state and NORMAL is meaningful only when no
    # other bit is set. Every other attribute can carry user-visible or
    # security policy (read-only, hidden, system, encryption, compression,
    # integrity, recall, sparse, and similar filesystem-specific state).
    _WINDOWS_NONPOLICY_ATTRIBUTES = _FILE_ATTRIBUTE_ARCHIVE | _FILE_ATTRIBUTE_NORMAL

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
    _GetFileInformationByHandleEx = _kernel32.GetFileInformationByHandleEx
    _GetFileInformationByHandleEx.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    )
    _GetFileInformationByHandleEx.restype = wintypes.BOOL
    _CloseHandle = _kernel32.CloseHandle
    _CloseHandle.argtypes = (wintypes.HANDLE,)
    _CloseHandle.restype = wintypes.BOOL
    _LocalFree = _kernel32.LocalFree
    _LocalFree.argtypes = (ctypes.c_void_p,)
    _LocalFree.restype = ctypes.c_void_p
    _GetFinalPathNameByHandleW = _kernel32.GetFinalPathNameByHandleW
    _GetFinalPathNameByHandleW.argtypes = (
        wintypes.HANDLE,
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
    )
    _GetFinalPathNameByHandleW.restype = wintypes.DWORD
    _ReplaceFileW = _kernel32.ReplaceFileW
    _ReplaceFileW.argtypes = (
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.DWORD,
        ctypes.c_void_p,
        ctypes.c_void_p,
    )
    _ReplaceFileW.restype = wintypes.BOOL

    _advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    _GetKernelObjectSecurity = _advapi32.GetKernelObjectSecurity
    _GetKernelObjectSecurity.argtypes = (
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    )
    _GetKernelObjectSecurity.restype = wintypes.BOOL
    _ConvertSecurityDescriptorToStringSecurityDescriptorW = (
        _advapi32.ConvertSecurityDescriptorToStringSecurityDescriptorW
    )
    _ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes = (
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.LPWSTR),
        ctypes.POINTER(wintypes.DWORD),
    )
    _ConvertSecurityDescriptorToStringSecurityDescriptorW.restype = wintypes.BOOL
    _GetSecurityDescriptorDacl = _advapi32.GetSecurityDescriptorDacl
    _GetSecurityDescriptorDacl.argtypes = (
        ctypes.c_void_p,
        ctypes.POINTER(wintypes.BOOL),
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(wintypes.BOOL),
    )
    _GetSecurityDescriptorDacl.restype = wintypes.BOOL
    _GetSecurityDescriptorControl = _advapi32.GetSecurityDescriptorControl
    _GetSecurityDescriptorControl.argtypes = (
        ctypes.c_void_p,
        ctypes.POINTER(wintypes.WORD),
        ctypes.POINTER(wintypes.DWORD),
    )
    _GetSecurityDescriptorControl.restype = wintypes.BOOL
    _SetSecurityDescriptorControl = _advapi32.SetSecurityDescriptorControl
    _SetSecurityDescriptorControl.argtypes = (
        ctypes.c_void_p,
        wintypes.WORD,
        wintypes.WORD,
    )
    _SetSecurityDescriptorControl.restype = wintypes.BOOL
    _ntdll = ctypes.WinDLL("ntdll")
    _NtSetSecurityObject = _ntdll.NtSetSecurityObject
    _NtSetSecurityObject.argtypes = (
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.c_void_p,
    )
    _NtSetSecurityObject.restype = wintypes.LONG
    _RtlNtStatusToDosError = _ntdll.RtlNtStatusToDosError
    _RtlNtStatusToDosError.argtypes = (wintypes.LONG,)
    _RtlNtStatusToDosError.restype = wintypes.ULONG

    class _FileRenameInfoEx(ctypes.Structure):
        _fields_ = (
            ("Flags", wintypes.DWORD),
            ("RootDirectory", wintypes.HANDLE),
            ("FileNameLength", wintypes.DWORD),
            ("FileName", wintypes.WCHAR * 1),
        )

    class _FileDispositionInfo(ctypes.Structure):
        _fields_ = (("DeleteFile", wintypes.BOOL),)


_RENAME_EXCHANGE = 2
_renameat2 = None
if sys.platform.startswith("linux"):
    try:
        _renameat2 = ctypes.CDLL(None, use_errno=True).renameat2
    except (AttributeError, OSError):
        _renameat2 = None
    else:
        _renameat2.argtypes = (
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        _renameat2.restype = ctypes.c_int


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


def _validate_windows_output_name(out: Path) -> None:
    """Reject every Win32 device/normalization alias at each native boundary."""

    name = out.name
    normalized = name.rstrip(" .")
    device_stem = normalized.split(".", 1)[0].upper()
    if normalized != name or ":" in name or device_stem in WINDOWS_RESERVED_STEMS:
        raise OutputPolicyError(f"unsafe Windows output filename: {name!r}")


def _validate_output_target(clip: Path, out: Path, force: bool) -> None:
    if os.name == "nt":
        _validate_windows_output_name(out)
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


def _win32_resolved_path(descriptor: int, subject: str) -> Path:
    """Resolve one retained handle without trusting its original pathname."""

    handle = wintypes.HANDLE(msvcrt.get_osfhandle(descriptor))
    required = _GetFinalPathNameByHandleW(handle, None, 0, 0)
    if not required:
        error = ctypes.get_last_error()
        raise OutputPolicyError(
            f"could not resolve {subject}: "
            f"[WinError {error}] {ctypes.FormatError(error).strip()}"
        )
    buffer = ctypes.create_unicode_buffer(required + 1)
    written = _GetFinalPathNameByHandleW(handle, buffer, len(buffer), 0)
    if not written or written >= len(buffer):
        error = ctypes.get_last_error()
        raise OutputPolicyError(
            f"could not read {subject} path: "
            f"[WinError {error}] {ctypes.FormatError(error).strip()}"
        )
    resolved = buffer.value
    if resolved.startswith("\\\\?\\UNC\\"):
        return Path("\\\\" + resolved[8:])
    if resolved.startswith("\\\\?\\"):
        return Path(resolved[4:])
    raise OutputPolicyError(f"{subject} returned an unsupported Windows path")


def _win32_directory_descriptor(path: Path) -> int:
    """Open the directory itself, never a followed junction target."""

    handle = _CreateFileW(
        _win32_extended_path(path),
        _FILE_READ_ATTRIBUTES,
        _FILE_SHARE_READ | _FILE_SHARE_WRITE | _FILE_SHARE_DELETE,
        None,
        _OPEN_EXISTING,
        _FILE_FLAG_BACKUP_SEMANTICS | _FILE_FLAG_OPEN_REPARSE_POINT,
        None,
    )
    if handle == _INVALID_HANDLE_VALUE:
        error = ctypes.get_last_error()
        raise OutputPolicyError(
            f"cannot retain the Windows output directory {path}: "
            f"[WinError {error}] {ctypes.FormatError(error).strip()}"
        )
    try:
        return msvcrt.open_osfhandle(
            int(handle), os.O_RDONLY | getattr(os, "O_BINARY", 0)
        )
    except Exception:
        _CloseHandle(handle)
        raise


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


def _win32_replacement_descriptor(path: Path) -> int:
    """Open and namespace-lock the exact target for handle-bound rechecks."""

    handle = _CreateFileW(
        _win32_extended_path(path),
        _GENERIC_READ | _READ_CONTROL | _FILE_READ_ATTRIBUTES,
        # Readers can keep using the old image during decode. Denying default-
        # stream write and delete sharing excludes conflicting existing opens,
        # protects the image bytes, and locks the destination namespace between
        # policy proof and commit. Security state and separately shared named
        # streams are still re-audited immediately before publication. The
        # handle is released only when ReplaceFileW is ready to capture the
        # actual commit-boundary target in its rollback backup.
        _FILE_SHARE_READ,
        None,
        _OPEN_EXISTING,
        _FILE_ATTRIBUTE_NORMAL | _FILE_FLAG_OPEN_REPARSE_POINT,
        None,
    )
    if handle == _INVALID_HANDLE_VALUE:
        error = ctypes.get_last_error()
        raise OutputPolicyError(
            f"cannot open existing Windows output policy for {path}: "
            f"[WinError {error}] {ctypes.FormatError(error).strip()}"
        )
    try:
        return msvcrt.open_osfhandle(
            int(handle), os.O_RDONLY | getattr(os, "O_BINARY", 0)
        )
    except Exception:
        _CloseHandle(handle)
        raise


def _win32_transaction_artifact_descriptor(
    path: Path,
    *,
    restore_dacl: bool = False,
) -> int:
    """Open an unshared transaction artifact with delete authority."""

    access = _GENERIC_READ | _DELETE | _READ_CONTROL | _FILE_READ_ATTRIBUTES
    if restore_dacl:
        access |= _WRITE_DAC
    handle = _CreateFileW(
        _win32_extended_path(path),
        access,
        _FILE_SHARE_READ,
        None,
        _OPEN_EXISTING,
        _FILE_ATTRIBUTE_NORMAL | _FILE_FLAG_OPEN_REPARSE_POINT,
        None,
    )
    if handle == _INVALID_HANDLE_VALUE:
        error = ctypes.get_last_error()
        raise OutputPolicyError(
            f"cannot open Windows transaction artifact {path}: "
            f"[WinError {error}] {ctypes.FormatError(error).strip()}"
        )
    try:
        return msvcrt.open_osfhandle(
            int(handle), os.O_RDONLY | getattr(os, "O_BINARY", 0)
        )
    except Exception:
        _CloseHandle(handle)
        raise


def _win32_security_descriptor(descriptor: int, out: Path) -> bytes:
    """Read owner, group, DACL, and mandatory label from an open file."""

    handle = wintypes.HANDLE(msvcrt.get_osfhandle(descriptor))
    needed = wintypes.DWORD(0)
    ctypes.set_last_error(0)
    first = _GetKernelObjectSecurity(
        handle,
        _WINDOWS_POLICY_SECURITY_INFORMATION,
        None,
        0,
        ctypes.byref(needed),
    )
    error = ctypes.get_last_error()
    if first or error != _ERROR_INSUFFICIENT_BUFFER or not needed.value:
        raise OutputPolicyError(
            f"cannot size the Windows security policy for {out}: "
            f"[WinError {error}] {ctypes.FormatError(error).strip()}"
        )
    if needed.value > 1024 * 1024:
        raise OutputPolicyError(
            f"Windows security policy is too large to audit safely for {out}"
        )
    buffer = ctypes.create_string_buffer(needed.value)
    if not _GetKernelObjectSecurity(
        handle,
        _WINDOWS_POLICY_SECURITY_INFORMATION,
        buffer,
        len(buffer),
        ctypes.byref(needed),
    ):
        error = ctypes.get_last_error()
        raise OutputPolicyError(
            f"cannot inspect the Windows security policy for {out}: "
            f"[WinError {error}] {ctypes.FormatError(error).strip()}"
        )
    return bytes(buffer.raw[: needed.value])


def _canonicalize_win32_security_descriptor(raw: bytes, out: Path) -> str:
    """Serialize policy components, not provider-specific relative offsets."""

    buffer = ctypes.create_string_buffer(raw)
    rendered = wintypes.LPWSTR()
    rendered_length = wintypes.DWORD(0)
    # GetKernelObjectSecurity returned only the mandatory-label portion of the
    # SACL. Asking the converter for SACL text serializes that label alongside
    # owner, group, and DACL. SDDL retains ACE order and ACL control flags while
    # discarding irrelevant self-relative offsets and padding, which may differ
    # across Windows filesystem providers after ReplaceFileW.
    requested = (
        _OWNER_SECURITY_INFORMATION
        | _GROUP_SECURITY_INFORMATION
        | _DACL_SECURITY_INFORMATION
        | _SACL_SECURITY_INFORMATION
    )
    if not _ConvertSecurityDescriptorToStringSecurityDescriptorW(
        buffer,
        _SDDL_REVISION_1,
        requested,
        ctypes.byref(rendered),
        ctypes.byref(rendered_length),
    ):
        error = ctypes.get_last_error()
        raise OutputPolicyError(
            f"cannot canonicalize the Windows security policy for {out}: "
            f"[WinError {error}] {ctypes.FormatError(error).strip()}"
        )
    try:
        if not rendered:
            raise OutputPolicyError(
                f"Windows returned an empty canonical security policy for {out}"
            )
        return ctypes.wstring_at(rendered)
    finally:
        _LocalFree(ctypes.cast(rendered, ctypes.c_void_p))


def _win32_security_policy(descriptor: int, out: Path) -> str:
    return _canonicalize_win32_security_descriptor(
        _win32_security_descriptor(descriptor, out), out
    )


def _restore_win32_dacl(
    descriptor: int,
    authorized_descriptor: bytes,
    authorized_policy: str,
    out: Path,
) -> None:
    """Reapply and prove the handle-bound destination DACL after ReplaceFileW."""

    raw = ctypes.create_string_buffer(authorized_descriptor)
    present = wintypes.BOOL()
    defaulted = wintypes.BOOL()
    dacl = ctypes.c_void_p()
    if not _GetSecurityDescriptorDacl(
        raw,
        ctypes.byref(present),
        ctypes.byref(dacl),
        ctypes.byref(defaulted),
    ):
        error = ctypes.get_last_error()
        raise OutputPolicyError(
            f"cannot read the authorized Windows DACL for {out}: "
            f"[WinError {error}] {ctypes.FormatError(error).strip()}"
        )
    if not present.value or not dacl.value:
        raise OutputPolicyError(
            f"authorized Windows output has no bounded DACL: {out}"
        )

    expected_security = _split_win32_security_policy(authorized_policy)
    # SetSecurityInfo recomputes filesystem inheritance and can rewrite ID,
    # AI, and AR history. NtSetSecurityObject applies the captured self-relative
    # descriptor through the retained WRITE_DAC handle without P/UNP propagation
    # flags. The kernel preserves SE_DACL_AUTO_INHERITED only when the matching
    # request bit accompanies it, so add that request to this temporary copy.
    control = wintypes.WORD()
    revision = wintypes.DWORD()
    ctypes.set_last_error(0)
    if not _GetSecurityDescriptorControl(
        raw, ctypes.byref(control), ctypes.byref(revision)
    ):
        error = ctypes.get_last_error()
        raise OutputPolicyError(
            f"cannot inspect authorized Windows DACL control for {out}: "
            f"[WinError {error}] {ctypes.FormatError(error).strip()}"
        )
    if control.value & _SE_DACL_PROTECTED:
        raise OutputPolicyError(
            f"authorized protected Windows DACL is outside the proven restore path: {out}"
        )
    if control.value & _SE_DACL_AUTO_INHERITED:
        ctypes.set_last_error(0)
        if not _SetSecurityDescriptorControl(
            raw,
            _SE_DACL_AUTO_INHERIT_REQ,
            _SE_DACL_AUTO_INHERIT_REQ,
        ):
            error = ctypes.get_last_error()
            raise OutputPolicyError(
                f"cannot request exact Windows DACL inheritance for {out}: "
                f"[WinError {error}] {ctypes.FormatError(error).strip()}"
            )
    status = int(
        _NtSetSecurityObject(
            wintypes.HANDLE(msvcrt.get_osfhandle(descriptor)),
            _DACL_SECURITY_INFORMATION,
            ctypes.cast(raw, ctypes.c_void_p),
        )
    )
    if status < 0:
        error = int(_RtlNtStatusToDosError(status))
        status_code = ctypes.c_ulong(status).value
        raise OutputPolicyError(
            f"cannot restore the authorized Windows DACL for {out}: "
            f"[NTSTATUS 0x{status_code:08x}; WinError {error}] "
            f"{ctypes.FormatError(error).strip()}"
        )

    observed_security = _split_win32_security_policy(
        _win32_security_policy(descriptor, out)
    )
    differences = tuple(
        label
        for label, expected, observed in (
            ("DACL entries", expected_security[2], observed_security[2]),
            ("DACL control flags", expected_security[3], observed_security[3]),
        )
        if expected != observed
    )
    if differences:
        raise OutputPolicyError(
            "authorized Windows DACL did not survive canonical reapplication "
            f"({', '.join(differences)}): {out}"
        )


def _win32_named_streams(descriptor: int, out: Path) -> tuple[str, ...]:
    """Enumerate named streams through the open target handle, not its path."""

    handle = wintypes.HANDLE(msvcrt.get_osfhandle(descriptor))
    buffer_size = 64 * 1024
    while True:
        buffer = ctypes.create_string_buffer(buffer_size)
        ctypes.set_last_error(0)
        if _GetFileInformationByHandleEx(
            handle,
            _FILE_STREAM_INFO_CLASS,
            buffer,
            len(buffer),
        ):
            break
        error = ctypes.get_last_error()
        if error == _ERROR_HANDLE_EOF:
            return ()
        if error in {_ERROR_INSUFFICIENT_BUFFER, _ERROR_MORE_DATA} and buffer_size < 1024 * 1024:
            buffer_size *= 2
            continue
        raise OutputPolicyError(
            f"cannot enumerate Windows output streams for {out}: "
            f"[WinError {error}] {ctypes.FormatError(error).strip()}"
        )

    raw = buffer.raw
    offset = 0
    named: list[str] = []
    while True:
        if offset + 24 > len(raw):
            raise OutputPolicyError(
                f"Windows returned a truncated stream-policy record for {out}"
            )
        next_offset, name_length, _size, _allocation = struct.unpack_from(
            "<IIqq", raw, offset
        )
        name_start = offset + 24
        name_end = name_start + name_length
        if name_length % 2 or name_end > len(raw):
            raise OutputPolicyError(
                f"Windows returned an invalid stream-policy record for {out}"
            )
        try:
            name = raw[name_start:name_end].decode("utf-16-le")
        except UnicodeError as exc:
            raise OutputPolicyError(
                f"Windows returned an undecodable stream name for {out}"
            ) from exc
        if name.casefold() != "::$data".casefold():
            named.append(name)
        if not next_offset:
            break
        if next_offset % 8 or next_offset < 24 or offset + next_offset <= offset:
            raise OutputPolicyError(
                f"Windows returned an invalid stream-policy offset for {out}"
            )
        offset += next_offset
    return tuple(sorted(named, key=str.casefold))


def _win32_policy_attributes(descriptor: int, out: Path) -> int:
    try:
        info = os.fstat(descriptor)
    except OSError as exc:
        raise OutputPolicyError(
            f"cannot inspect Windows output attributes for {out}: {exc}"
        ) from exc
    attributes = getattr(info, "st_file_attributes", None)
    if attributes is None:
        raise OutputPolicyError(
            f"Windows output attributes are unavailable for {out}; replacement was refused"
        )
    return int(attributes) & ~_WINDOWS_NONPOLICY_ATTRIBUTES


def _snapshot_win32_policy(
    descriptor: int,
    out: Path,
) -> tuple[str, int, tuple[str, ...]]:
    return (
        _win32_security_policy(descriptor, out),
        _win32_policy_attributes(descriptor, out),
        _win32_named_streams(descriptor, out),
    )


def _win32_content_digest(descriptor: int, out: Path) -> bytes:
    """Hash one retained regular stream without reopening its mutable name."""

    try:
        original_offset = os.lseek(descriptor, 0, os.SEEK_CUR)
        os.lseek(descriptor, 0, os.SEEK_SET)
        digest = hashlib.sha256()
        total = 0
        while True:
            block = os.read(descriptor, 1024 * 1024)
            if not block:
                break
            total += len(block)
            if total > _MAX_FRAME_BYTES:
                raise OutputPolicyError(
                    f"Windows transaction artifact exceeds the safety limit: {out}"
                )
            digest.update(block)
        return digest.digest()
    except OSError as exc:
        raise OutputPolicyError(
            f"cannot hash the retained Windows transaction artifact {out}: {exc}"
        ) from exc
    finally:
        try:
            os.lseek(descriptor, original_offset, os.SEEK_SET)
        except (OSError, UnboundLocalError):
            pass


def _snapshot_win32_artifact(descriptor: int, out: Path) -> WindowsArtifactState:
    try:
        info = os.fstat(descriptor)
    except OSError as exc:
        raise OutputPolicyError(
            f"cannot inspect the Windows transaction artifact {out}: {exc}"
        ) from exc
    if not stat.S_ISREG(info.st_mode) or _is_reparse_point(info):
        raise OutputPolicyError(
            f"Windows transaction artifact is not a regular file: {out}"
        )
    security, attributes, streams = _snapshot_win32_policy(descriptor, out)
    return WindowsArtifactState(
        identity=_identity(info),
        security_policy=security,
        policy_attributes=attributes,
        named_streams=streams,
        content_digest=_win32_content_digest(descriptor, out),
    )


def _prepare_win32_replacement_metadata(
    stage: OutputStage,
    out: Path,
) -> WindowsReplacementSnapshot:
    """Permit replacement only when the stage already carries exact policy."""

    existing_descriptor = -1
    try:
        existing_descriptor = _win32_replacement_descriptor(out)
        existing = os.fstat(existing_descriptor)
        if not stat.S_ISREG(existing.st_mode) or _is_reparse_point(existing):
            raise OutputPolicyError(
                f"--force only replaces a regular output file: {out}"
            )
        target_policy = _snapshot_win32_policy(existing_descriptor, out)
        stage_policy = _snapshot_win32_policy(stage.descriptor, stage.path)
        security_policy, policy_attributes, named_streams = target_policy
        if named_streams:
            raise OutputPolicyError(
                "existing Windows output has named data streams that cannot be "
                f"safely preserved: {named_streams!r}; replacement was refused"
            )
        if policy_attributes:
            raise OutputPolicyError(
                "existing Windows output has policy-bearing file attributes "
                f"0x{policy_attributes:x}; replacement was refused: {out}"
            )
        if stage_policy != target_policy:
            raise OutputPolicyError(
                "existing Windows output security policy differs from the protected "
                f"replacement stage; replacement was refused: {out}"
            )
        return WindowsReplacementSnapshot(
            descriptor=existing_descriptor,
            identity=_identity(existing),
            security_policy=security_policy,
            policy_attributes=policy_attributes,
            named_streams=named_streams,
            content_digest=_win32_content_digest(existing_descriptor, out),
        )
    except Exception:
        if existing_descriptor >= 0:
            try:
                os.close(existing_descriptor)
            except OSError:
                pass
        raise


def _verify_win32_replacement_metadata(
    snapshot: WindowsReplacementSnapshot,
    stage: OutputStage,
    out: Path,
) -> None:
    """Recheck both open inodes immediately before the atomic handle rename."""

    try:
        opened = os.fstat(snapshot.descriptor)
        named = os.lstat(out)
    except OSError as exc:
        raise OutputPolicyError(
            f"cannot re-verify existing Windows output policy for {out}: {exc}"
        ) from exc
    if (
        not stat.S_ISREG(opened.st_mode)
        or _is_reparse_point(opened)
        or _identity(opened) != snapshot.identity
        or _identity(named) != snapshot.identity
    ):
        raise OutputPolicyError(
            f"existing Windows output identity changed before publication: {out}"
        )
    expected = (
        snapshot.security_policy,
        snapshot.policy_attributes,
        snapshot.named_streams,
    )
    if _snapshot_win32_policy(snapshot.descriptor, out) != expected:
        raise OutputPolicyError(
            f"existing Windows output policy changed before publication: {out}"
        )
    if _snapshot_win32_policy(stage.descriptor, stage.path) != expected:
        raise OutputPolicyError(
            f"protected Windows replacement policy changed before publication: {out}"
        )


def _verify_win32_target_directory(stage: OutputStage, out: Path) -> None:
    """Prove the requested parent still names the retained staging directory."""

    if (
        stage.target_directory_descriptor is None
        or stage.target_directory_identity is None
    ):
        raise OutputPolicyError("retained Windows output directory is unavailable")
    try:
        opened = os.fstat(stage.target_directory_descriptor)
        named = os.lstat(out.parent)
        resolved_stage = _win32_resolved_path(
            stage.descriptor, "the owned staging handle"
        )
        staged_parent = os.stat(resolved_stage.parent)
    except OSError as exc:
        raise OutputPolicyError(
            f"cannot re-verify the Windows output directory for {out}: {exc}"
        ) from exc
    expected = stage.target_directory_identity
    if (
        not stat.S_ISDIR(opened.st_mode)
        or _is_reparse_point(opened)
        or not stat.S_ISDIR(named.st_mode)
        or _is_reparse_point(named)
        or _identity(opened) != expected
        or _identity(named) != expected
        or _identity(staged_parent) != expected
    ):
        raise OutputPolicyError(
            f"Windows output directory identity changed before publication: {out.parent}"
        )


def _win32_rename_by_handle(stage: OutputStage, out: Path, force: bool) -> None:
    _validate_windows_output_name(out)
    _verify_win32_target_directory(stage, out)
    _win32_rename_open_handle(stage, out.name, force)


def _win32_rename_open_handle(stage: OutputStage, target_name: str, force: bool) -> None:
    """Rename the owned file inside its handle-resolved retained directory."""

    handle = wintypes.HANDLE(msvcrt.get_osfhandle(stage.descriptor))
    if stage.target_directory_descriptor is None:
        raise OutputPolicyError("retained Windows output directory is unavailable")
    anchored = _win32_resolved_path(stage.descriptor, "the owned Windows file handle")
    dos_target = str(anchored.with_name(target_name))
    if dos_target.startswith("\\\\"):
        native_target = "\\??\\UNC\\" + dos_target[2:]
    else:
        native_target = "\\??\\" + dos_target
    encoded_name = native_target.encode("utf-16-le")
    offset = _FileRenameInfoEx.FileName.offset
    # Microsoft's FILE_RENAME_INFORMATION contract requires at least the fixed
    # structure size plus the variable filename bytes, not merely the offset of
    # FileName plus those bytes.
    buffer = ctypes.create_string_buffer(ctypes.sizeof(_FileRenameInfoEx) + len(encoded_name))
    info = ctypes.cast(buffer, ctypes.POINTER(_FileRenameInfoEx)).contents
    # FILE_RENAME_FLAG_POSIX_SEMANTICS lets the force replacement commit while
    # the audited old target is still held open with FILE_SHARE_DELETE. Keeping
    # that handle alive is what makes the final identity/policy comparison
    # descriptor-bound instead of reopening an attacker-controlled pathname.
    info.Flags = (
        _FILE_RENAME_FLAG_REPLACE_IF_EXISTS | _FILE_RENAME_FLAG_POSIX_SEMANTICS
        if force
        else 0
    )
    info.RootDirectory = None
    info.FileNameLength = len(encoded_name)
    ctypes.memmove(ctypes.addressof(buffer) + offset, encoded_name, len(encoded_name))
    if _SetFileInformationByHandle(
        handle, _FILE_RENAME_INFO_EX_CLASS, buffer, len(buffer)
    ):
        return
    error = ctypes.get_last_error()
    if not force and error in (_ERROR_FILE_EXISTS, _ERROR_ALREADY_EXISTS):
        raise OutputPolicyError(
            f"output appeared during extraction and was preserved: {target_name}"
        )
    raise OutputPolicyError(
        f"could not atomically {'replace' if force else 'publish'} output {target_name}: "
        f"[WinError {error}] {ctypes.FormatError(error).strip()}"
    )


def _win32_mark_descriptor_for_deletion(descriptor: int, path: Path) -> bool:
    handle = wintypes.HANDLE(msvcrt.get_osfhandle(descriptor))
    disposition = _FileDispositionInfo(1)
    if _SetFileInformationByHandle(
        handle,
        _FILE_DISPOSITION_INFO_CLASS,
        ctypes.byref(disposition),
        ctypes.sizeof(disposition),
    ):
        return True
    error = ctypes.get_last_error()
    _write_console_line(
        f"warning: could not delete owned Windows handle for {path}: "
        f"[WinError {error}] {ctypes.FormatError(error).strip()}",
        stream=sys.stderr,
    )
    return False


def _win32_mark_stage_for_deletion(stage: OutputStage) -> bool:
    return _win32_mark_descriptor_for_deletion(stage.descriptor, stage.path)


def _win32_auxiliary_path(parent: Path, tag: str) -> Path:
    """Allocate a bounded, currently unclaimed transaction pathname."""

    for _attempt in range(64):
        candidate = parent / f".frame-{tag}-{secrets.token_hex(20)}"
        if not _path_exists(candidate):
            return candidate
    raise OutputPolicyError(f"could not allocate a Windows {tag} transaction name")


def _call_win32_replace_file(
    replaced: Path,
    replacement: Path,
    backup: Path,
) -> int | None:
    """Run ReplaceFileW without metadata-ignore flags; return its Win32 error."""

    ctypes.set_last_error(0)
    if _ReplaceFileW(
        _win32_extended_path(replaced),
        _win32_extended_path(replacement),
        _win32_extended_path(backup),
        0,
        None,
        None,
    ):
        return None
    return ctypes.get_last_error()


def _rollback_win32_replace(
    stage: OutputStage,
    target: Path,
    backup: Path,
    expected_backup: WindowsArtifactState,
    expected_rejected: WindowsArtifactState,
) -> None:
    """Preserve the rejected inode, then atomically restore the exact backup."""

    discard = _win32_auxiliary_path(target.parent, "rejected")
    try:
        os.link(_win32_extended_path(target), _win32_extended_path(discard))
    except OSError as exc:
        raise OutputPolicyError(
            "Windows rollback could not preserve the rejected inode; both files "
            f"were left for recovery ({target}, {backup}): {exc}"
        ) from exc

    discard_descriptor = -1
    backup_descriptor = -1
    try:
        discard_descriptor = _win32_transaction_artifact_descriptor(discard)
        rejected = _snapshot_win32_artifact(discard_descriptor, discard)
        try:
            if _identity(os.lstat(target)) != rejected.identity:
                raise OutputPolicyError(
                    f"Windows rollback target changed before restoration: {target}"
                )
        except OSError as exc:
            raise OutputPolicyError(
                f"cannot inspect the Windows rollback target {target}: {exc}"
            ) from exc

        backup_descriptor = _win32_transaction_artifact_descriptor(backup)
        backup_stage = OutputStage(
            backup,
            _identity(os.fstat(backup_descriptor)),
            backup_descriptor,
            target_directory_identity=stage.target_directory_identity,
            target_directory_descriptor=stage.target_directory_descriptor,
        )
        _win32_rename_open_handle(backup_stage, target.name, True)
        restored = _snapshot_win32_artifact(backup_descriptor, target)
        if restored != expected_backup:
            raise OutputPolicyError(
                f"Windows rollback restored unexpected output state: {target}"
            )
        if rejected != expected_rejected:
            raise OutputPolicyError(
                "Windows rollback restored the prior output but preserved a late "
                f"unrelated claimant for recovery at {discard}"
            )
        if not _win32_mark_descriptor_for_deletion(discard_descriptor, discard):
            raise OutputPolicyError(
                f"Windows rollback could not delete the rejected replacement: {discard}"
            )
    finally:
        for descriptor in (backup_descriptor, discard_descriptor):
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass


def _reopen_win32_stage_for_cleanup(stage: OutputStage, path: Path) -> None:
    """Recover the generated inode after a pathname transaction did not consume it."""

    if not _path_exists(path):
        return
    descriptor = _win32_transaction_artifact_descriptor(path)
    try:
        if _identity(os.fstat(descriptor)) != stage.identity:
            raise OutputPolicyError(
                f"Windows staging identity changed; unexpected path was preserved: {path}"
            )
    except Exception:
        os.close(descriptor)
        raise
    stage.descriptor = descriptor
    stage.path = path


def _publish_win32_force_transaction(
    stage: OutputStage,
    replacement: WindowsReplacementSnapshot,
    out: Path,
) -> None:
    """Replace with an exact backup, post-verify both sides, or roll back."""

    _validate_windows_output_name(out)
    _verify_win32_target_directory(stage, out)
    _verify_win32_replacement_metadata(replacement, stage, out)
    stage_state = _snapshot_win32_artifact(stage.descriptor, stage.path)
    authorized_target_security = _win32_security_descriptor(
        replacement.descriptor, out
    )
    if (
        _canonicalize_win32_security_descriptor(authorized_target_security, out)
        != replacement.security_policy
    ):
        raise OutputPolicyError(
            f"existing Windows output security policy changed before publication: {out}"
        )
    expected_target = WindowsArtifactState(
        identity=replacement.identity,
        security_policy=replacement.security_policy,
        policy_attributes=replacement.policy_attributes,
        named_streams=replacement.named_streams,
        content_digest=replacement.content_digest,
    )
    anchored_stage = _win32_resolved_path(stage.descriptor, "the owned staging handle")
    if anchored_stage.name.casefold() != stage.path.name.casefold():
        raise OutputPolicyError("owned staging handle name changed; refusing replacement")
    target = anchored_stage.with_name(out.name)
    backup = _win32_auxiliary_path(anchored_stage.parent, "rollback")

    # ReplaceFileW deliberately opens the replacement with no sharing mode, so
    # both audited file handles must be released for the atomic operation. The
    # API's backup captures the *actual* target at the commit boundary; every
    # postcondition below is checked before that recovery copy is deleted.
    try:
        os.close(replacement.descriptor)
    except OSError as exc:
        raise OutputPolicyError(
            f"could not release the audited Windows target before replacement: {exc}"
        ) from exc
    replacement.descriptor = -1
    try:
        os.close(stage.descriptor)
    except OSError as exc:
        raise OutputPolicyError(
            f"could not release the protected Windows stage before replacement: {exc}"
        ) from exc
    stage.descriptor = -1

    error = _call_win32_replace_file(target, anchored_stage, backup)
    if error is not None:
        # The documented 1177 partial state moves the displaced target to the
        # backup. When both names exist, the same transactional rollback below
        # can restore it. Otherwise verify the old target and retain any backup
        # rather than deleting an object whose provenance is uncertain.
        if _path_exists(backup) and _path_exists(target):
            backup_descriptor = _win32_transaction_artifact_descriptor(backup)
            try:
                backup_state = _snapshot_win32_artifact(backup_descriptor, backup)
            finally:
                os.close(backup_descriptor)
            target_descriptor = _win32_replacement_descriptor(target)
            try:
                rejected_state = _snapshot_win32_artifact(target_descriptor, target)
            finally:
                os.close(target_descriptor)
            if backup_state == expected_target and rejected_state != expected_target:
                # A failed ReplaceFileW may have moved the audited target into
                # its backup before failing. Restore only that exact inode. A
                # caller that claimed our unpredictable backup name must never
                # be promoted over an intact or ambiguous destination.
                _rollback_win32_replace(
                    stage, target, backup, backup_state, rejected_state
                )
            elif rejected_state != expected_target:
                raise OutputPolicyError(
                    "Windows replacement failed with ambiguous target and backup "
                    f"state; both recovery artifacts were preserved: {target}, {backup}"
                )
        elif _path_exists(backup):
            backup_descriptor = _win32_transaction_artifact_descriptor(backup)
            try:
                backup_state = _snapshot_win32_artifact(backup_descriptor, backup)
                if backup_state != expected_target:
                    raise OutputPolicyError(
                        "Windows replacement failed with an untrusted rollback "
                        f"artifact; it was preserved without publication: {backup}"
                    )
                backup_stage = OutputStage(
                    backup,
                    backup_state.identity,
                    backup_descriptor,
                    target_directory_identity=stage.target_directory_identity,
                    target_directory_descriptor=stage.target_directory_descriptor,
                )
                _win32_rename_open_handle(backup_stage, out.name, False)
                restored = _snapshot_win32_artifact(backup_descriptor, target)
                if restored != expected_target:
                    raise OutputPolicyError(
                        "Windows partial-transaction recovery restored unexpected "
                        f"output state: {target}"
                    )
            finally:
                os.close(backup_descriptor)
        elif not _path_exists(target):
            raise OutputPolicyError(
                "Windows replacement failed after both the target and rollback backup "
                f"became unavailable: {target}, {backup}"
            )
        elif _path_exists(target):
            target_descriptor = _win32_transaction_artifact_descriptor(target)
            try:
                if _snapshot_win32_artifact(target_descriptor, target) != expected_target:
                    raise OutputPolicyError(
                        f"failed Windows transaction left an unexpected target: {target}"
                    )
            finally:
                os.close(target_descriptor)
        _reopen_win32_stage_for_cleanup(stage, anchored_stage)
        raise OutputPolicyError(
            f"could not atomically replace Windows output {out}: "
            f"[WinError {error}] {ctypes.FormatError(error).strip()}"
        )

    backup_descriptor = -1
    output_descriptor = -1
    try:
        backup_descriptor = _win32_transaction_artifact_descriptor(backup)
        backup_state = _snapshot_win32_artifact(backup_descriptor, backup)
        output_descriptor = _win32_transaction_artifact_descriptor(
            target, restore_dacl=True
        )
        output_state = _snapshot_win32_artifact(output_descriptor, target)
        violations: list[str] = []
        backup_differences = _win32_artifact_differences(
            expected_target, backup_state
        )
        if backup_differences:
            violations.append(
                "the displaced target changed at the commit boundary "
                f"({', '.join(backup_differences)})"
            )
        # ReplaceFileW intentionally merges the replaced file's DACL into the
        # replacement. Restore the exact authorized DACL state through the
        # retained output handle, then compare canonical ACEs and every DACL
        # control flag; no DACL difference is ignored.
        if output_state.identity == stage_state.identity:
            try:
                _restore_win32_dacl(
                    output_descriptor,
                    authorized_target_security,
                    replacement.security_policy,
                    target,
                )
            except OutputPolicyError:
                violations.append(
                    "the authorized destination DACL could not be restored exactly"
                )
            output_state = _snapshot_win32_artifact(output_descriptor, target)
        output_differences = _win32_artifact_differences(stage_state, output_state)
        if output_differences:
            violations.append(
                "the replacement changed after commit "
                f"({', '.join(output_differences)})"
            )
        stage.descriptor = output_descriptor
        try:
            _verify_win32_target_directory(stage, out)
        except OutputPolicyError:
            violations.append("the output directory changed at the commit boundary")
        finally:
            stage.descriptor = -1
        if violations:
            os.close(output_descriptor)
            output_descriptor = -1
            os.close(backup_descriptor)
            backup_descriptor = -1
            _rollback_win32_replace(
                stage, target, backup, backup_state, output_state
            )
            raise OutputPolicyError(
                "Windows replacement transaction was rolled back: " + "; ".join(violations)
            )

        if not _win32_mark_descriptor_for_deletion(backup_descriptor, backup):
            os.close(output_descriptor)
            output_descriptor = -1
            os.close(backup_descriptor)
            backup_descriptor = -1
            _rollback_win32_replace(
                stage, target, backup, backup_state, output_state
            )
            raise OutputPolicyError(
                "Windows replacement transaction was rolled back because the exact "
                "backup could not be committed"
            )
        os.close(backup_descriptor)
        backup_descriptor = -1
        stage.descriptor = output_descriptor
        output_descriptor = -1
        stage.path = target
        stage.published = True
    finally:
        for descriptor in (output_descriptor, backup_descriptor):
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass


def _unlink_open_posix_file(
    descriptor: int,
    name: str,
    directory_descriptor: int,
) -> bool:
    """Unlink only when the anchored name still denotes the open file."""

    try:
        opened = os.fstat(descriptor)
        named = os.stat(
            name,
            dir_fd=directory_descriptor,
            follow_symlinks=False,
        )
        if not stat.S_ISREG(opened.st_mode) or _identity(named) != _identity(opened):
            return False
        os.unlink(name, dir_fd=directory_descriptor)
        return True
    except OSError:
        return False


def _rmdir_open_posix_directory(
    descriptor: int,
    name: str,
    target_directory_descriptor: int,
) -> bool:
    """Remove only when the anchored name still denotes the open directory."""

    try:
        opened = os.fstat(descriptor)
        named = os.stat(
            name,
            dir_fd=target_directory_descriptor,
            follow_symlinks=False,
        )
        if not stat.S_ISDIR(opened.st_mode) or _identity(named) != _identity(opened):
            return False
        os.rmdir(name, dir_fd=target_directory_descriptor)
        return True
    except OSError:
        return False


def _create_output_stage(out: Path) -> OutputStage:
    suffix = out.suffix or ".img"
    if os.name == "nt":
        target_descriptor = -1
        descriptor = -1
        path: Path | None = None
        try:
            target_descriptor = _win32_directory_descriptor(out.parent)
            target_info = os.fstat(target_descriptor)
            named_parent = os.lstat(out.parent)
            if (
                not stat.S_ISDIR(target_info.st_mode)
                or _is_reparse_point(target_info)
                or not stat.S_ISDIR(named_parent.st_mode)
                or _is_reparse_point(named_parent)
                or _identity(target_info) != _identity(named_parent)
            ):
                raise OutputPolicyError(
                    f"unsafe or unstable Windows output directory: {out.parent}"
                )
            target_identity = _identity(target_info)
            target_digest = hashlib.sha256(
                out.name.encode("utf-8", errors="surrogatepass")
            ).hexdigest()[:16]
            prefix = f".frame-{target_digest}.atomic-"
            for _attempt in range(64):
                path = out.parent / f"{prefix}{secrets.token_hex(16)}{suffix}"
                try:
                    descriptor = _win32_stage_descriptor(path)
                except FileExistsError:
                    continue
                except (OSError, OutputPolicyError) as exc:
                    raise OutputPolicyError(
                        f"cannot create locked output staging file beside {out}: {exc}"
                    ) from exc
                break
            else:
                raise OutputPolicyError("could not allocate a unique output staging name")

            info = os.fstat(descriptor)
            resolved_stage = _win32_resolved_path(
                descriptor, "the newly created staging handle"
            )
            resolved_parent = os.stat(resolved_stage.parent)
            current_parent = os.lstat(out.parent)
            if (
                not stat.S_ISREG(info.st_mode)
                or _is_reparse_point(info)
                or _identity(resolved_parent) != target_identity
                or _identity(current_parent) != target_identity
                or _is_reparse_point(current_parent)
            ):
                raise OutputPolicyError(
                    "Windows output directory changed while the protected stage "
                    f"was created: {out.parent}"
                )
            return OutputStage(
                path,
                _identity(info),
                descriptor,
                target_directory_identity=target_identity,
                target_directory_descriptor=target_descriptor,
            )
        except Exception:
            if descriptor >= 0:
                cleanup_path = path if path is not None else out
                cleanup_stage = OutputStage(cleanup_path, (-1, -1), descriptor)
                _win32_mark_stage_for_deletion(cleanup_stage)
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            if target_descriptor >= 0:
                try:
                    os.close(target_descriptor)
                except OSError:
                    pass
            raise

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
    stage_name: str | None = None
    try:
        # Keep the mutable staging name inside a private directory. Directory
        # descriptors then anchor every lookup even if the parent pathname is
        # renamed concurrently. The output inode itself is created with 0666,
        # so the caller's umask produces the same permissions as an ordinary
        # newly-created image rather than mkstemp's hard-coded 0600.
        target_descriptor = os.open(out.parent, target_directory_flags)
        target_info = os.fstat(target_descriptor)
        for _attempt in range(64):
            directory_name = _posix_stage_directory_name(out, target_descriptor)
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
        # Record the created name before opening it so a replacement between
        # mkdir and open is detected. If this first stat itself fails, the
        # exception path reopens the unpredictable owner-only name and binds
        # cleanup to that descriptor before removing anything.
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
            or (
                hasattr(os, "geteuid")
                and opened_directory.st_uid != os.geteuid()
            )
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
        if descriptor >= 0 and directory_descriptor >= 0 and stage_name is not None:
            _unlink_open_posix_file(
                descriptor,
                stage_name,
                directory_descriptor,
            )
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if (
            directory_descriptor < 0
            and directory_path is not None
            and target_descriptor >= 0
        ):
            try:
                directory_descriptor = os.open(
                    directory_path.name,
                    private_directory_flags,
                    dir_fd=target_descriptor,
                )
                opened_directory = os.fstat(directory_descriptor)
                if (
                    stat.S_ISDIR(opened_directory.st_mode)
                    and (
                        not hasattr(os, "geteuid")
                        or opened_directory.st_uid == os.geteuid()
                    )
                    and stat.S_IMODE(opened_directory.st_mode) == 0o700
                ):
                    directory_identity = _identity(opened_directory)
            except OSError:
                directory_descriptor = -1
        if directory_descriptor >= 0 and directory_identity is None:
            try:
                opened_directory = os.fstat(directory_descriptor)
                if (
                    stat.S_ISDIR(opened_directory.st_mode)
                    and (
                        not hasattr(os, "geteuid")
                        or opened_directory.st_uid == os.geteuid()
                    )
                    and stat.S_IMODE(opened_directory.st_mode) == 0o700
                ):
                    directory_identity = _identity(opened_directory)
            except OSError:
                pass
        if (
            directory_descriptor >= 0
            and directory_path is not None
            and target_descriptor >= 0
            and directory_identity is not None
        ):
            try:
                opened_directory = os.fstat(directory_descriptor)
            except OSError:
                pass
            else:
                if _identity(opened_directory) == directory_identity:
                    _rmdir_open_posix_directory(
                        directory_descriptor,
                        directory_path.name,
                        target_descriptor,
                    )
        if directory_descriptor >= 0:
            try:
                os.close(directory_descriptor)
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


def _posix_name_max(directory_descriptor: int, out: Path) -> int:
    """Return the byte limit for a component in an open directory."""

    try:
        name_max = int(os.fpathconf(directory_descriptor, "PC_NAME_MAX"))
    except (OSError, ValueError) as exc:
        raise OutputPolicyError(
            f"cannot determine the output filesystem name limit for {out}: {exc}"
        ) from exc
    if name_max <= 0:
        raise OutputPolicyError(
            f"output filesystem reported an invalid component limit for {out}: {name_max}"
        )
    return name_max


def _posix_random_component_token(character_count: int) -> str:
    """Return at least six random bits per URL-safe output character."""

    byte_count = (character_count * 3 + 3) // 4
    encoded = base64.urlsafe_b64encode(secrets.token_bytes(byte_count))
    token = encoded.rstrip(b"=").decode("ascii")
    if len(token) < character_count:
        raise OutputPolicyError("could not generate a bounded POSIX staging token")
    return token[:character_count]


def _posix_auxiliary_name(
    tag: str,
    directory_descriptor: int,
    out: Path,
) -> str:
    """Return a collision-resistant probe/publication name within NAME_MAX."""

    name_max = _posix_name_max(directory_descriptor, out)
    preferred_token = _posix_random_component_token(22)
    preferred = f".frame-{tag}-{preferred_token}"
    if len(os.fsencode(preferred)) <= name_max:
        return preferred

    # POSIX permits NAME_MAX as low as 14. Reserve two ASCII bytes for a
    # recognizable hidden-file prefix and use every remaining byte for a
    # URL-safe token. At the minimum this retains 12 characters / 72 random
    # bits; O_EXCL/link collision retries provide a second line of defense.
    compact_prefix = ".x"
    available = name_max - len(os.fsencode(compact_prefix))
    if available < 12:
        raise OutputPolicyError(
            "output filesystem component limit is too small for a "
            f"collision-resistant auxiliary name: {name_max}"
        )
    return compact_prefix + _posix_random_component_token(min(available, 22))


def _posix_stage_directory_name(out: Path, target_descriptor: int) -> str:
    """Return a private staging component bounded by the target filesystem."""

    name_max = _posix_name_max(target_descriptor, out)

    token = secrets.token_hex(16)
    preferred = f".{out.stem}.atomic-{token}"
    if len(os.fsencode(preferred)) <= name_max:
        return preferred

    # A valid final basename can consume almost all of NAME_MAX. Do not copy
    # that stem into the private directory name: keep a stable target digest
    # plus independent collision entropy instead.
    target_digest = hashlib.sha256(os.fsencode(out.name)).hexdigest()[:16]
    bounded = f".frame-{target_digest}.atomic-{token}"
    if len(os.fsencode(bounded)) <= name_max:
        return bounded

    # Very small NAME_MAX filesystems still get a random digest name rather
    # than an overlong component. POSIX permits limits as small as 14 bytes.
    compact_prefix = ".f-"
    available = name_max - len(os.fsencode(compact_prefix))
    if available < 8:
        raise OutputPolicyError(
            f"output filesystem component limit is too small for safe staging: {name_max}"
        )
    compact_digest = hashlib.sha256(
        os.fsencode(out.name) + b"\0" + token.encode("ascii")
    ).hexdigest()
    return compact_prefix + compact_digest[:available]


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


def _link_unique_posix_stage_anchor(stage: OutputStage, out: Path) -> str:
    """Claim a bounded private link name, retrying collisions safely."""

    if stage.directory_descriptor is None:
        raise OutputPolicyError("output staging directory handle is unavailable")
    for _attempt in range(64):
        candidate = _posix_auxiliary_name(
            "publish",
            stage.directory_descriptor,
            out,
        )
        try:
            _posix_link_open_stage(
                stage,
                candidate,
                stage.directory_descriptor,
            )
            return candidate
        except FileExistsError:
            # Never delete the colliding object unless it is provably a link
            # to our open stage. A fresh random candidate is cheaper and keeps
            # an unrelated same-name object untouched.
            _unlink_open_posix_file(
                stage.descriptor,
                candidate,
                stage.directory_descriptor,
            )
            continue
        except BaseException:
            # A wrapper or fallback may fail after creating the link. Bind
            # cleanup to the open stage descriptor, not to the candidate name.
            _unlink_open_posix_file(
                stage.descriptor,
                candidate,
                stage.directory_descriptor,
            )
            raise
    raise OutputPolicyError(
        "could not allocate a unique bounded POSIX publication anchor"
    )


_CAP_SYS_ADMIN = 21


def _linux_has_effective_cap_sys_admin() -> bool:
    """Prove visibility of Linux's privileged extended-attribute namespace."""

    if not sys.platform.startswith("linux"):
        return False
    try:
        status = Path("/proc/self/status").read_text(encoding="ascii")
    except (OSError, UnicodeError):
        return False
    for line in status.splitlines():
        label, separator, value = line.partition(":")
        if label != "CapEff" or not separator:
            continue
        try:
            effective = int(value.strip(), 16)
        except ValueError:
            return False
        return bool(effective & (1 << _CAP_SYS_ADMIN))
    return False


def _posix_descriptor_xattr_api_supported() -> bool:
    # Python's descriptor xattr API is Linux-specific, and access ACLs on
    # macOS and other POSIX systems are not necessarily exposed as xattrs.
    # Refuse there instead of mistaking an empty xattr list for no policy.
    if not sys.platform.startswith("linux"):
        return False
    supports_fd = getattr(os, "supports_fd", set())
    return all(
        hasattr(os, name) and getattr(os, name) in supports_fd
        for name in ("listxattr", "getxattr", "setxattr", "removexattr")
    )


def _posix_atomic_exchange_supported() -> bool:
    return sys.platform.startswith("linux") and _renameat2 is not None


def _posix_descriptor_xattrs_supported() -> bool:
    return (
        _posix_descriptor_xattr_api_supported()
        and _linux_has_effective_cap_sys_admin()
        and _posix_atomic_exchange_supported()
    )


def _posix_exchange_names(
    left_name: str,
    left_directory_descriptor: int,
    right_name: str,
    right_directory_descriptor: int,
) -> None:
    """Atomically exchange two Linux directory entries."""

    if not _posix_atomic_exchange_supported():
        raise OutputPolicyError(
            "Linux renameat2(RENAME_EXCHANGE) is unavailable; replacement was refused"
        )
    ctypes.set_errno(0)
    result = _renameat2(
        left_directory_descriptor,
        os.fsencode(left_name),
        right_directory_descriptor,
        os.fsencode(right_name),
        _RENAME_EXCHANGE,
    )
    if result != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def _require_posix_replacement_metadata_contract(out: Path) -> None:
    if _posix_descriptor_xattrs_supported():
        return
    if not sys.platform.startswith("linux"):
        reason = "this non-Linux POSIX runtime does not expose a complete ACL contract"
    elif not _posix_descriptor_xattr_api_supported():
        reason = "this Linux runtime lacks descriptor-bound extended-metadata APIs"
    elif not _linux_has_effective_cap_sys_admin():
        reason = (
            "the process lacks effective CAP_SYS_ADMIN and cannot prove visibility "
            "of hidden trusted or security metadata"
        )
    elif not _posix_atomic_exchange_supported():
        reason = "Linux renameat2(RENAME_EXCHANGE) is unavailable"
    else:
        reason = "the process cannot prove complete extended-metadata visibility"
    raise OutputPolicyError(f"{reason}; refusing --force replacement of {out}")


def _read_posix_extended_attributes_once(
    descriptor: int,
    out: Path,
) -> tuple[tuple[str, bytes], ...]:
    try:
        names = tuple(sorted(os.listxattr(descriptor)))
    except OSError as exc:
        unsupported = {errno.ENOTSUP, getattr(errno, "EOPNOTSUPP", errno.ENOTSUP)}
        if exc.errno in unsupported:
            raise OutputPolicyError(
                "the output filesystem cannot enumerate extended metadata for "
                f"{out}; replacement was refused"
            ) from exc
        raise OutputPolicyError(
            f"cannot inspect existing output extended metadata for {out}: {exc}"
        ) from exc

    copyable_system_attributes = {"system.posix_acl_access"}
    for name in names:
        if (
            name.startswith(("security.", "trusted."))
            or (name.startswith("system.") and name not in copyable_system_attributes)
        ):
            raise OutputPolicyError(
                "cannot safely preserve existing output security policy attribute "
                f"{name!r} for {out}; replacement was refused"
            )

    attributes: list[tuple[str, bytes]] = []
    for name in names:
        try:
            attributes.append((name, os.getxattr(descriptor, name)))
        except OSError as exc:
            raise OutputPolicyError(
                f"cannot read existing output extended metadata {name!r} for {out}: {exc}"
            ) from exc
    return tuple(attributes)


def _snapshot_posix_extended_attributes(
    descriptor: int,
    out: Path,
) -> tuple[tuple[str, bytes], ...]:
    _require_posix_replacement_metadata_contract(out)
    first = _read_posix_extended_attributes_once(descriptor, out)
    second = _read_posix_extended_attributes_once(descriptor, out)
    if first != second:
        raise OutputPolicyError(
            f"existing output extended metadata changed while inspecting {out}; replacement was refused"
        )
    return first


def _prove_linux_privileged_xattr_visibility(descriptor: int, out: Path) -> None:
    """Verify that the target filesystem exposes the privileged namespace."""

    probe_name = f"trusted.seedance-visibility-{secrets.token_hex(8)}"
    probe_value = b"descriptor-bound"
    created = False
    failure: str | None = None
    try:
        os.setxattr(descriptor, probe_name, probe_value)
        created = True
        names = os.listxattr(descriptor)
        value = os.getxattr(descriptor, probe_name)
        if probe_name not in names or value != probe_value:
            failure = "the privileged extended-metadata namespace is not fully visible"
    except OSError as exc:
        failure = f"the privileged extended-metadata namespace cannot be audited: {exc}"
    finally:
        if created:
            try:
                os.removexattr(descriptor, probe_name)
            except OSError as exc:
                raise OutputPolicyError(
                    "cannot remove the temporary extended-metadata visibility probe "
                    f"for {out}; replacement was refused: {exc}"
                ) from exc
    if failure is not None:
        raise OutputPolicyError(f"{failure} for {out}; replacement was refused")


def _cleanup_posix_probe_artifacts(
    artifacts: list[PosixProbeArtifact],
) -> tuple[str, ...]:
    """Remove every tracked probe name by matching it to an open descriptor."""

    failures: list[str] = []
    for location in artifacts:
        removed = False
        # A one-way exchange may have swapped which descriptor owns this name.
        # Try every still-open probe descriptor rather than relying on an
        # identity capture that may itself have been the failing operation.
        for opened in artifacts:
            if _unlink_open_posix_file(
                opened.descriptor,
                location.name,
                location.directory_descriptor,
            ):
                removed = True
                break
        if removed:
            continue
        try:
            os.stat(
                location.name,
                dir_fd=location.directory_descriptor,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            continue
        except OSError as exc:
            failures.append(f"{location.name!r}: inspection failed: {exc}")
        else:
            failures.append(f"{location.name!r}: exact descriptor match failed")

    for artifact in artifacts:
        try:
            os.close(artifact.descriptor)
        except OSError as exc:
            failures.append(f"fd {artifact.descriptor}: close failed: {exc}")
    return tuple(failures)


def _probe_posix_atomic_exchange(stage: OutputStage, out: Path) -> None:
    """Prove cross-directory RENAME_EXCHANGE on the output filesystem."""

    if stage.directory_descriptor is None or stage.target_directory_descriptor is None:
        raise OutputPolicyError("POSIX publication handles are unavailable")
    locations = (
        ("exchange-private", stage.directory_descriptor),
        ("exchange-public", stage.target_directory_descriptor),
    )
    artifacts: list[PosixProbeArtifact] = []
    failure: Exception | None = None
    cleanup_failures: tuple[str, ...] = ()
    try:
        for tag, directory_descriptor in locations:
            for _attempt in range(64):
                name = _posix_auxiliary_name(tag, directory_descriptor, out)
                try:
                    descriptor = os.open(
                        name,
                        os.O_RDWR
                        | os.O_CREAT
                        | os.O_EXCL
                        | getattr(os, "O_CLOEXEC", 0),
                        0o600,
                        dir_fd=directory_descriptor,
                    )
                except FileExistsError:
                    continue
                artifact = PosixProbeArtifact(
                    name=name,
                    directory_descriptor=directory_descriptor,
                    descriptor=descriptor,
                )
                # Track the created path and descriptor before fstat. Even if
                # this very call fails, the finally block can retry the exact
                # descriptor/name comparison and remove the artifact.
                artifacts.append(artifact)
                artifact.identity = _identity(os.fstat(descriptor))
                break
            else:
                raise OutputPolicyError(
                    "could not allocate a unique bounded atomic-exchange probe name"
                )

        left, right = artifacts
        if left.identity is None or right.identity is None:
            raise OutputPolicyError(
                "atomic-exchange probe identities are incomplete"
            )
        _posix_exchange_names(
            left.name,
            left.directory_descriptor,
            right.name,
            right.directory_descriptor,
        )
        swapped = (
            _identity(
                os.stat(
                    left.name,
                    dir_fd=left.directory_descriptor,
                    follow_symlinks=False,
                )
            ),
            _identity(
                os.stat(
                    right.name,
                    dir_fd=right.directory_descriptor,
                    follow_symlinks=False,
                )
            ),
        )
        if swapped != (right.identity, left.identity):
            raise OutputPolicyError(
                "Linux atomic-exchange probe returned unexpected identities"
            )

        _posix_exchange_names(
            left.name,
            left.directory_descriptor,
            right.name,
            right.directory_descriptor,
        )
        restored = (
            _identity(
                os.stat(
                    left.name,
                    dir_fd=left.directory_descriptor,
                    follow_symlinks=False,
                )
            ),
            _identity(
                os.stat(
                    right.name,
                    dir_fd=right.directory_descriptor,
                    follow_symlinks=False,
                )
            ),
        )
        if restored != (left.identity, right.identity):
            raise OutputPolicyError(
                "Linux atomic-exchange probe could not restore its identities"
            )
    except (OSError, OutputPolicyError) as exc:
        failure = exc
    finally:
        cleanup_failures = _cleanup_posix_probe_artifacts(artifacts)

    if cleanup_failures:
        detail = "; ".join(cleanup_failures)
        cleanup_error = OutputPolicyError(
            f"could not remove exact atomic-exchange probe artifacts for {out}: {detail}"
        )
        if failure is None:
            raise cleanup_error
        raise OutputPolicyError(
            "the output filesystem atomic-exchange probe failed and exact cleanup "
            f"also failed for {out}: {detail}"
        ) from failure
    if failure is not None:
        raise OutputPolicyError(
            f"the output filesystem cannot perform an identity-safe atomic exchange for "
            f"{out}; replacement was refused: {failure}"
        ) from failure


def _verify_posix_force_directory_contract(stage: OutputStage, out: Path) -> None:
    """Require the namespace to exclude cross-account exchange interference."""

    if stage.target_directory_descriptor is None:
        raise OutputPolicyError("output directory handle is unavailable")
    try:
        target_directory = os.fstat(stage.target_directory_descriptor)
    except OSError as exc:
        raise OutputPolicyError(
            f"cannot inspect the output directory policy for {out}: {exc}"
        ) from exc
    if (
        not stat.S_ISDIR(target_directory.st_mode)
        or (
            hasattr(os, "geteuid")
            and target_directory.st_uid != os.geteuid()
        )
        or stat.S_IMODE(target_directory.st_mode) & 0o022
    ):
        raise OutputPolicyError(
            "--force requires an output directory owned by the effective user "
            f"and not writable by group or others: {out.parent}"
        )


def _prepare_posix_replacement_metadata(
    stage: OutputStage,
    out: Path,
) -> PosixReplacementSnapshot:
    """Copy auditable POSIX metadata and retain the source inode for recheck."""

    if stage.target_directory_descriptor is None:
        raise OutputPolicyError("output directory handle is unavailable")
    existing_descriptor = -1
    try:
        _verify_posix_target_directory(stage, out)
        _verify_posix_force_directory_contract(stage, out)
        existing_descriptor = os.open(
            out.name,
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0),
            dir_fd=stage.target_directory_descriptor,
        )
        existing = os.fstat(existing_descriptor)
        staged = os.fstat(stage.descriptor)
        if not stat.S_ISREG(existing.st_mode):
            raise OutputPolicyError(
                f"--force only replaces a regular output file: {out}"
            )
        extended_attributes = _snapshot_posix_extended_attributes(
            existing_descriptor,
            out,
        )
        _prove_linux_privileged_xattr_visibility(stage.descriptor, out)
        _probe_posix_atomic_exchange(stage, out)
        if (
            hasattr(os, "fchown")
            and (staged.st_uid != existing.st_uid or staged.st_gid != existing.st_gid)
        ):
            os.fchown(stage.descriptor, existing.st_uid, existing.st_gid)
        os.fchmod(stage.descriptor, stat.S_IMODE(existing.st_mode))

        for name, value in extended_attributes:
            try:
                os.setxattr(stage.descriptor, name, value)
            except OSError as exc:
                raise OutputPolicyError(
                    f"cannot preserve existing output extended metadata {name!r} for {out}: {exc}"
                ) from exc

        copied_attributes = _snapshot_posix_extended_attributes(stage.descriptor, out)
        copied = os.fstat(stage.descriptor)
        if (
            copied_attributes != extended_attributes
            or copied.st_uid != existing.st_uid
            or copied.st_gid != existing.st_gid
            or stat.S_IMODE(copied.st_mode) != stat.S_IMODE(existing.st_mode)
        ):
            raise OutputPolicyError(
                f"existing output permissions or extended metadata could not be preserved for {out}"
            )
        os.fsync(stage.descriptor)
        return PosixReplacementSnapshot(
            descriptor=existing_descriptor,
            identity=_identity(existing),
            uid=existing.st_uid,
            gid=existing.st_gid,
            mode=stat.S_IMODE(existing.st_mode),
            extended_attributes=extended_attributes,
        )
    except OutputPolicyError:
        if existing_descriptor >= 0:
            try:
                os.close(existing_descriptor)
            except OSError:
                pass
        raise
    except OSError as exc:
        if existing_descriptor >= 0:
            try:
                os.close(existing_descriptor)
            except OSError:
                pass
        raise OutputPolicyError(
            f"cannot preserve existing output permissions or extended metadata for {out}: {exc}"
        ) from exc


def _verify_posix_replacement_metadata(
    snapshot: PosixReplacementSnapshot,
    stage: OutputStage,
    out: Path,
) -> None:
    if stage.target_directory_descriptor is None:
        raise OutputPolicyError("output directory handle is unavailable")
    try:
        opened = os.fstat(snapshot.descriptor)
        named = os.stat(
            out.name,
            dir_fd=stage.target_directory_descriptor,
            follow_symlinks=False,
        )
    except OSError as exc:
        raise OutputPolicyError(
            f"cannot re-verify existing output metadata for {out}: {exc}"
        ) from exc
    if (
        not stat.S_ISREG(opened.st_mode)
        or _identity(opened) != snapshot.identity
        or _identity(named) != snapshot.identity
        or opened.st_uid != snapshot.uid
        or opened.st_gid != snapshot.gid
        or stat.S_IMODE(opened.st_mode) != snapshot.mode
        or _snapshot_posix_extended_attributes(snapshot.descriptor, out)
        != snapshot.extended_attributes
    ):
        raise OutputPolicyError(
            f"existing output permissions or extended metadata changed before publication: {out}"
        )


def _verify_posix_staged_replacement_metadata(
    snapshot: PosixReplacementSnapshot,
    stage: OutputStage,
    out: Path,
) -> None:
    """Recheck copied policy after encoding and before namespace mutation."""

    try:
        staged = os.fstat(stage.descriptor)
        attributes = _snapshot_posix_extended_attributes(stage.descriptor, out)
    except OSError as exc:
        raise OutputPolicyError(
            f"cannot re-verify staged output metadata for {out}: {exc}"
        ) from exc
    if (
        not stat.S_ISREG(staged.st_mode)
        or _identity(staged) != stage.identity
        or staged.st_uid != snapshot.uid
        or staged.st_gid != snapshot.gid
        or stat.S_IMODE(staged.st_mode) != snapshot.mode
        or attributes != snapshot.extended_attributes
    ):
        raise OutputPolicyError(
            f"staged output permissions or extended metadata changed before publication: {out}"
        )


def _verify_posix_exchanged_replacement(
    snapshot: PosixReplacementSnapshot,
    stage: OutputStage,
    publish_name: str,
    out: Path,
) -> None:
    """Verify both entries after exchange before the transaction commits."""

    if stage.directory_descriptor is None or stage.target_directory_descriptor is None:
        raise OutputPolicyError("POSIX publication handles are unavailable")
    try:
        displaced = os.stat(
            publish_name,
            dir_fd=stage.directory_descriptor,
            follow_symlinks=False,
        )
        published = os.stat(
            out.name,
            dir_fd=stage.target_directory_descriptor,
            follow_symlinks=False,
        )
    except OSError as exc:
        raise OutputPolicyError(
            f"cannot verify the atomic replacement transaction for {out}: {exc}"
        ) from exc

    _verify_posix_staged_replacement_metadata(snapshot, stage, out)
    try:
        opened = os.fstat(snapshot.descriptor)
        attributes = _snapshot_posix_extended_attributes(snapshot.descriptor, out)
    except OSError as exc:
        raise OutputPolicyError(
            f"cannot verify displaced output metadata for {out}: {exc}"
        ) from exc
    if (
        not stat.S_ISREG(displaced.st_mode)
        or _identity(displaced) != snapshot.identity
        or _identity(opened) != snapshot.identity
        or opened.st_uid != snapshot.uid
        or opened.st_gid != snapshot.gid
        or stat.S_IMODE(opened.st_mode) != snapshot.mode
        or attributes != snapshot.extended_attributes
        or not stat.S_ISREG(published.st_mode)
        or _identity(published) != stage.identity
    ):
        raise OutputPolicyError(
            "the destination changed after verification; the atomic replacement "
            f"must be rolled back: {out}"
        )


def _rollback_posix_exchange(
    stage: OutputStage,
    publish_name: str,
    out: Path,
) -> None:
    """Reverse an uncommitted exchange and preserve the displaced destination."""

    if stage.directory_descriptor is None or stage.target_directory_descriptor is None:
        raise OutputPolicyError("POSIX rollback handles are unavailable")
    try:
        displaced_before = os.stat(
            publish_name,
            dir_fd=stage.directory_descriptor,
            follow_symlinks=False,
        )
        published_before = os.stat(
            out.name,
            dir_fd=stage.target_directory_descriptor,
            follow_symlinks=False,
        )
        if _identity(published_before) != stage.identity:
            raise OutputPolicyError(
                "the destination changed during rollback; displaced output was retained "
                f"inside the protected staging directory for recovery: {out}"
            )
        displaced_identity = _identity(displaced_before)
        _posix_exchange_names(
            publish_name,
            stage.directory_descriptor,
            out.name,
            stage.target_directory_descriptor,
        )
        restored = os.stat(
            out.name,
            dir_fd=stage.target_directory_descriptor,
            follow_symlinks=False,
        )
        staged_anchor = os.stat(
            publish_name,
            dir_fd=stage.directory_descriptor,
            follow_symlinks=False,
        )
        if (
            _identity(restored) != displaced_identity
            or _identity(staged_anchor) != stage.identity
        ):
            raise OutputPolicyError(
                f"atomic replacement rollback could not be verified for {out}"
            )
        if not _unlink_open_posix_file(
            stage.descriptor,
            publish_name,
            stage.directory_descriptor,
        ):
            raise OutputPolicyError(
                f"could not remove the exact staged publication anchor after rollback: {out}"
            )
    except OutputPolicyError:
        raise
    except OSError as exc:
        raise OutputPolicyError(
            f"could not roll back the atomic replacement of {out}: {exc}"
        ) from exc


def _publish_posix_force_exchange(
    stage: OutputStage,
    replacement: PosixReplacementSnapshot,
    out: Path,
) -> None:
    """Compare, exchange, verify, and commit a Linux force replacement."""

    if stage.directory_descriptor is None or stage.target_directory_descriptor is None:
        raise OutputPolicyError("POSIX publication handles are unavailable")
    publish_name: str | None = None
    linked = False
    exchanged = False
    try:
        _verify_posix_force_directory_contract(stage, out)
        publish_name = _link_unique_posix_stage_anchor(stage, out)
        linked = True
        _verify_posix_replacement_metadata(replacement, stage, out)
        _verify_posix_staged_replacement_metadata(replacement, stage, out)
        _posix_exchange_names(
            publish_name,
            stage.directory_descriptor,
            out.name,
            stage.target_directory_descriptor,
        )
        exchanged = True
        _verify_posix_exchanged_replacement(
            replacement,
            stage,
            publish_name,
            out,
        )
        if not _unlink_open_posix_file(
            replacement.descriptor,
            publish_name,
            stage.directory_descriptor,
        ):
            raise OutputPolicyError(
                f"could not commit deletion of the exact replaced output for {out}"
            )
        linked = False
        exchanged = False
    except (OSError, OutputPolicyError) as exc:
        rollback_error: OutputPolicyError | None = None
        if exchanged and publish_name is not None:
            try:
                _rollback_posix_exchange(stage, publish_name, out)
                linked = False
                exchanged = False
            except OutputPolicyError as rollback_exc:
                rollback_error = rollback_exc
        elif linked and publish_name is not None:
            if _unlink_open_posix_file(
                stage.descriptor,
                publish_name,
                stage.directory_descriptor,
            ):
                linked = False

        if rollback_error is not None:
            raise OutputPolicyError(
                f"atomic replacement failed and rollback also failed for {out}: "
                f"{rollback_error}"
            ) from exc
        if isinstance(exc, OutputPolicyError):
            raise
        raise OutputPolicyError(
            f"could not atomically replace output {out}: {exc}"
        ) from exc
    stage.published = True


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
            if (
                not stage.published
                and stage.descriptor < 0
                and _path_exists(stage.path)
            ):
                recovered_descriptor = -1
                try:
                    recovered_descriptor = _win32_transaction_artifact_descriptor(
                        stage.path
                    )
                    if _identity(os.fstat(recovered_descriptor)) == stage.identity:
                        stage.descriptor = recovered_descriptor
                        recovered_descriptor = -1
                    else:
                        _write_console_line(
                            "warning: closed staging path identity changed; leaving "
                            f"unexpected path untouched: {stage.path}",
                            stream=sys.stderr,
                        )
                        success = False
                except (OSError, OutputPolicyError) as exc:
                    _write_console_line(
                        f"warning: could not recover closed staging handle: {exc}",
                        stream=sys.stderr,
                    )
                    success = False
                finally:
                    if recovered_descriptor >= 0:
                        try:
                            os.close(recovered_descriptor)
                        except OSError:
                            pass
            if not stage.published and stage.descriptor >= 0:
                success = _win32_mark_stage_for_deletion(stage) and success
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
                _write_console_line(
                    f"warning: could not inspect staging path {stage.path}: {exc}",
                    stream=sys.stderr,
                )
                success = False
                info = None
            if info is not None:
                if (
                    not stat.S_ISREG(info.st_mode)
                    or _is_reparse_point(info)
                    or _identity(info) != stage.identity
                ):
                    _write_console_line(
                        "warning: staging path identity changed; leaving unexpected path "
                        f"untouched: {stage.path}",
                        stream=sys.stderr,
                    )
                    success = False
                else:
                    try:
                        os.unlink(stage.path.name, dir_fd=stage.directory_descriptor)
                    except OSError as exc:
                        _write_console_line(
                            f"warning: could not remove staging file {stage.path}: {exc}",
                            stream=sys.stderr,
                        )
                        success = False
    finally:
        if stage.descriptor >= 0:
            try:
                os.close(stage.descriptor)
            except OSError as exc:
                _write_console_line(
                    f"warning: could not close staging handle: {exc}",
                    stream=sys.stderr,
                )
                success = False
        stage.descriptor = -1
        if os.name == "nt" and stage.target_directory_descriptor is not None:
            try:
                os.close(stage.target_directory_descriptor)
            except OSError as exc:
                _write_console_line(
                    f"warning: could not close output directory handle: {exc}",
                    stream=sys.stderr,
                )
                success = False
            stage.target_directory_descriptor = None
        if os.name != "nt":
            if (
                stage.directory_path is not None
                and stage.directory_identity is not None
                and stage.directory_descriptor is not None
                and stage.target_directory_descriptor is not None
            ):
                if not _rmdir_open_posix_directory(
                    stage.directory_descriptor,
                    stage.directory_path.name,
                    stage.target_directory_descriptor,
                ):
                    _write_console_line(
                        "warning: could not remove protected staging directory "
                        f"{stage.directory_path}",
                        stream=sys.stderr,
                    )
                    success = False
            if stage.directory_descriptor is not None:
                try:
                    os.close(stage.directory_descriptor)
                except OSError as exc:
                    _write_console_line(
                        f"warning: could not close staging directory handle: {exc}",
                        stream=sys.stderr,
                    )
                    success = False
                stage.directory_descriptor = None
            if stage.target_directory_descriptor is not None:
                try:
                    os.close(stage.target_directory_descriptor)
                except OSError as exc:
                    _write_console_line(
                        f"warning: could not close output directory handle: {exc}",
                        stream=sys.stderr,
                    )
                    success = False
                stage.target_directory_descriptor = None
    return success


def _publish_output(
    stage: OutputStage,
    clip: Path,
    out: Path,
    force: bool,
    replacement: PosixReplacementSnapshot | WindowsReplacementSnapshot | None = None,
) -> None:
    _verify_output_stage(stage, require_content=True)
    # Re-check immediately before publication. The locked Windows staging name
    # cannot be swapped before the atomic link/handle-rename operations below.
    _validate_output_target(clip, out, force)
    if os.name == "nt":
        if not force:
            _verify_win32_target_directory(stage, out)
            # The relative handle rename binds the destination to the retained
            # directory and atomically refuses any late claimant. Mark first so
            # an interruption immediately after the native commit cannot make
            # cleanup delete the successfully published frame.
            stage.published = True
            try:
                _win32_rename_by_handle(stage, out, False)
                try:
                    _verify_win32_target_directory(stage, out)
                except OutputPolicyError as directory_error:
                    # The relative commit landed in the retained directory. If
                    # the caller's pathname stopped naming that directory at the
                    # boundary, move the exact generated handle back to its
                    # private name before reporting the refusal.
                    _win32_rename_open_handle(stage, stage.path.name, False)
                    stage.published = False
                    raise directory_error
            except Exception:
                stage.published = False
                raise
            return
        if not isinstance(replacement, WindowsReplacementSnapshot):
            raise OutputPolicyError(
                "handle-bound Windows replacement policy snapshot is unavailable"
            )
        _publish_win32_force_transaction(stage, replacement, out)
        return

    _verify_posix_target_directory(stage, out)

    if force:
        if replacement is None:
            raise OutputPolicyError(
                "descriptor-bound replacement metadata snapshot is unavailable"
            )
        _publish_posix_force_exchange(stage, replacement, out)
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
_PNG_PROBE_TIMEOUT_SECONDS = 60
_FFMPEG_OPTION_PROBE_TIMEOUT_SECONDS = 15
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


def _probe_decodable_png(ffmpeg: str, png_frame: bytes) -> None:
    """Require a bounded independent decode before bytes become an anchor."""

    if not png_frame or len(png_frame) > _MAX_FRAME_BYTES:
        raise FrameExtractionError("retained PNG frame is outside the safety limit")
    cmd = [
        ffmpeg,
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-xerror",
        "-f",
        "image2pipe",
        "-vcodec",
        "png",
        "-i",
        "pipe:0",
        "-map",
        "0:v:0",
        "-frames:v",
        "1",
        "-an",
        "-f",
        "null",
        "-",
    ]
    with tempfile.TemporaryFile(mode="w+b") as stderr_file:
        try:
            completed = subprocess.run(
                cmd,
                input=png_frame,
                stdout=subprocess.DEVNULL,
                stderr=stderr_file,
                timeout=_PNG_PROBE_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            raise FrameExtractionError(
                "retained PNG decode probe exceeded the safety timeout"
            ) from exc
        except OSError as exc:
            raise FrameExtractionError(
                f"could not start the retained PNG decode probe: {exc}"
            ) from exc
        stderr_file.seek(0)
        detail = stderr_file.read().decode("utf-8", errors="replace")[-800:].strip()
    if completed.returncode != 0:
        raise FrameExtractionError(
            detail or "ffmpeg rejected the retained PNG frame during the decode probe"
        )


@functools.lru_cache(maxsize=16)
def _frame_sync_options(ffmpeg: str) -> tuple[str, str]:
    """Select the frame-sync spelling supported by this FFmpeg binary."""

    try:
        completed = subprocess.run(
            [ffmpeg, "-nostdin", "-hide_banner", "-h", "full"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=_FFMPEG_OPTION_PROBE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise FrameExtractionError(
            "ffmpeg option probe exceeded the safety timeout"
        ) from exc
    except OSError as exc:
        raise FrameExtractionError(f"could not probe ffmpeg options: {exc}") from exc

    help_text = completed.stdout.decode("utf-8", errors="replace")
    option_fields = {
        line.lstrip().split(maxsplit=1)[0]
        for line in help_text.splitlines()
        if line.lstrip().startswith("-")
    }
    if any(field == "-fps_mode" or field.startswith("-fps_mode[") for field in option_fields):
        return "-fps_mode", "passthrough"
    if "-vsync" in option_fields:
        return "-vsync", "0"

    detail = help_text[-800:].strip()
    if completed.returncode != 0:
        raise FrameExtractionError(detail or "ffmpeg option probe failed")
    raise FrameExtractionError(
        "ffmpeg supports neither -fps_mode nor the legacy -vsync frame-sync option"
    )


def _frame_stream_command(ffmpeg: str, clip: Path, first: bool) -> list[str]:
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
    sync_option, sync_value = _frame_sync_options(ffmpeg)
    cmd += [
        "-an",
        sync_option,
        sync_value,
        "-f",
        "image2pipe",
        "-vcodec",
        "png",
        "pipe:1",
    ]
    return cmd


def render_frame_png(ffmpeg: str, clip: Path, first: bool) -> bytes:
    """Stream every decoded frame and retain only the final complete PNG."""

    cmd = _frame_stream_command(ffmpeg, clip, first)

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
    _probe_decodable_png(ffmpeg, last_frame)
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
    stage: OutputStage | None = None
    replacement: PosixReplacementSnapshot | WindowsReplacementSnapshot | None = None
    try:
        if os.name == "posix":
            if force:
                # Common unprivileged Linux callers cannot see trusted.*
                # metadata. Refuse this known-impossible contract before even
                # allocating staging state.
                _require_posix_replacement_metadata_contract(out)
            # On POSIX, namespace support and every auditable replacement
            # policy check run before decode. Keep both the stage and the old
            # target descriptor bound across the expensive work.
            stage = _create_output_stage(out)
            if force:
                replacement = _prepare_posix_replacement_metadata(stage, out)
        elif os.name == "nt":
            # Retain the exact destination directory and create the protected
            # stage before decode in both publication modes. A parent
            # rename/recreation or junction substitution must never redirect a
            # completed frame into a different directory.
            stage = _create_output_stage(out)
            if force:
                # Bind the existing target and prove the protected stage already
                # carries the same Windows owner/group/DACL/label, has no named
                # streams, and has no policy-bearing attributes before decoding.
                replacement = _prepare_win32_replacement_metadata(stage, out)

        png_frame = render_frame_png(ffmpeg, clip, first)
        content = _encode_frame_for_output(ffmpeg, png_frame, out)
        if stage is None:
            stage = _create_output_stage(out)
        _write_output_stage(stage, content)
        _publish_output(stage, clip, out, force, replacement)
        _write_console_line(f"{'first' if first else 'last'} frame -> {out}")
        return 0
    finally:
        if replacement is not None and replacement.descriptor >= 0:
            try:
                os.close(replacement.descriptor)
            except OSError as exc:
                _write_console_line(
                    f"warning: could not close replaced output policy handle: {exc}",
                    stream=sys.stderr,
                )
        if stage is not None:
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
        _write_console_line(f"output refused: {exc}")
    except FrameExtractionError as exc:
        _write_console_line(f"extraction failed for {clip}: {exc}")
    except OSError as exc:
        _write_console_line(f"output failed safely: {exc}")
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
        _write_console_line("extract_last_frame self-test FAILED:")
        for e in errors:
            _write_console_line(f"- {e}")
        return 1
    _write_console_line(
        f"extract_last_frame self-test passed: {len(FRAME_READABLE)} frame-readable + "
        f"{len(FRAME_BLIND)} frame-blind categories, take-review fields referenced."
    )
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
        help=(
            "atomically replace an existing regular output only when its metadata policy "
            "can be preserved (Windows or capability-audited Linux; other POSIX refuses)"
        ),
    )
    parser.add_argument("--emit-record", action="store_true", help="print the observation-record skeleton")
    parser.add_argument("--self-test", action="store_true", help="offline wiring check, no ffmpeg or media")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if args.emit_record and not args.clip:
        _write_console_line(build_record())
        return 0
    if not args.clip:
        parser.error("clip path required (or use --self-test / --emit-record)")

    clip = Path(args.clip)
    if not clip.exists():
        _write_console_line(f"clip not found: {clip}")
        return 1
    ffmpeg = args.ffmpeg or shutil.which("ffmpeg")
    if not ffmpeg:
        _write_console_line(
            "ffmpeg not found on PATH; install it or pass --ffmpeg /path/to/ffmpeg"
        )
        return 2
    suffix = ".first.png" if args.first_frame else ".last.png"
    out = Path(args.output) if args.output else clip.with_suffix(clip.suffix + suffix)
    try:
        rc = extract_frame(ffmpeg, clip, out, args.first_frame, args.force)
    except OutputPolicyError as exc:
        _write_console_line(f"output refused: {exc}")
        return 1
    except FrameExtractionError as exc:
        _write_console_line(f"extraction failed for {clip}: {exc}")
        return 1
    except OSError as exc:
        _write_console_line(f"output failed safely: {exc}")
        return 1
    if rc == 0 and args.emit_record:
        _write_console_line("")
        _write_console_line(build_record())
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
