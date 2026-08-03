#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import shutil
import stat
import sys
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Mapping


SKILL_NAME = "seedance-20"
COMPLETION_MARKER = ".seedance-install-complete.json"
COMPLETION_FORMAT_VERSION = 1
LOCK_NAME = f".{SKILL_NAME}.install.lock"
BACKUP_NAME = f".{SKILL_NAME}.install-backup"
STAGE_PREFIX = f".{SKILL_NAME}.install-stage-"
TRANSACTION_NAME = f".{SKILL_NAME}.install-transaction.json"
PROVENANCE_MARKER = f".{SKILL_NAME}.install-provenance.json"
QUARANTINE_MARKER = f".{SKILL_NAME}.install-quarantine.json"
QUARANTINE_PREFIX = f".{SKILL_NAME}.install-quarantine-"
TRANSACTION_DONE_PREFIX = f".{SKILL_NAME}.install-transaction-done-"
TRANSACTION_FORMAT_VERSION = 2
LOCK_TIMEOUT_SECONDS = 300.0
MAX_RECORD_BYTES = 8 * 1024 * 1024
MAX_MANIFEST_ENTRIES = 50_000
MAX_RESERVED_ARTIFACTS = 128
MAX_DIAGNOSTIC_CHARS = 480
PRIVATE_DELETE_ENTRY = "authorized-object"
PRIVATE_DELETE_PREFIX = ".seedance-delete-"

# Kept out of the installed payload because they are development-only and
# network-capable. eval_run.py contacts a model provider and reads
# ANTHROPIC_API_KEY; nothing in skills/ or references/ invokes it, so an
# install has no use for it and shipping it would put a credential-reading
# script inside every agent that loads this skill. eval-runs/ holds its output.
# tests/test_install_payload.py enforces this.
DEV_ONLY_NAMES = {
    "eval_run.py",
    "eval-runs",
    "tests",
}

IGNORE_NAMES = {
    ".git",
    ".github",
    ".pytest_cache",
    ".seedance_backups",
    COMPLETION_MARKER,
    PROVENANCE_MARKER,
    "__pycache__",
} | DEV_ONLY_NAMES
# Fonts are build inputs for scripts/build_masthead_outlines.py, which an
# installed skill never runs - the outlines it produces are already baked into
# the committed SVGs. Shipping them would add ~340 KB to every install for
# nothing.
IGNORE_PATTERNS = ["*.pyc", "*.pyo", "*.tmp", "*.log", "*.png", "*.jpg", "*.jpeg", "*.psd", "*.ttf", "*.otf"]


def default_skills_dir() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser() / "skills"
    return Path.home() / ".codex" / "skills"


def ignore_runtime_noise(_src: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        if name in IGNORE_NAMES:
            ignored.add(name)
            continue
        if any(fnmatch.fnmatch(name, pattern) for pattern in IGNORE_PATTERNS):
            ignored.add(name)
    return ignored


def payload_size(path: Path) -> str:
    total = float(sum(item.stat().st_size for item in path.rglob("*") if item.is_file()))
    for unit in ["B", "KB", "MB", "GB"]:
        if total < 1024 or unit == "GB":
            return f"{total:.1f} {unit}"
        total /= 1024
    return f"{total:.1f} GB"


def _path_exists(path: Path) -> bool:
    """Like Path.exists(), but true for dangling links as well."""
    return os.path.lexists(path)


def _file_sha256(path: Path) -> str:
    return str(_regular_file_metadata(path)["sha256"])


def _bounded_diagnostic(value: object, limit: int = MAX_DIAGNOSTIC_CHARS) -> str:
    """Keep attacker-controlled paths, JSON keys, and OS errors printable."""
    rendered = str(value).replace("\r", "\\r").replace("\n", "\\n")
    if len(rendered) <= limit:
        return rendered
    omitted = len(rendered) - limit
    return f"{rendered[:limit]}... <{omitted} chars omitted>"


def _is_reparse_stat(info: os.stat_result) -> bool:
    attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(getattr(info, "st_file_attributes", 0) & attribute)


def _stat_identity(info: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        info.st_dev,
        info.st_ino,
        stat.S_IFMT(info.st_mode),
        info.st_size,
        info.st_mtime_ns,
        info.st_nlink,
    )


def _object_identity(info: os.stat_result) -> tuple[int, int]:
    """Return the stable filesystem object coordinates used by a transaction."""

    return (int(info.st_dev), int(info.st_ino))


def _regular_file_metadata(path: Path) -> dict[str, object]:
    """Hash one stable, non-link regular file and detect a concurrent swap."""
    before = path.lstat()
    if _is_reparse_stat(before) or stat.S_ISLNK(before.st_mode):
        raise RuntimeError(f"refusing link or reparse point: {_bounded_diagnostic(path)}")
    if not stat.S_ISREG(before.st_mode):
        raise RuntimeError(f"refusing non-regular file: {_bounded_diagnostic(path)}")

    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    digest = hashlib.sha256()
    try:
        opened = os.fstat(descriptor)
        if _is_reparse_stat(opened) or not stat.S_ISREG(opened.st_mode):
            raise RuntimeError(f"file changed type while opening: {_bounded_diagnostic(path)}")
        if _stat_identity(opened) != _stat_identity(before):
            raise RuntimeError(f"file changed while opening: {_bounded_diagnostic(path)}")
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        after_open = os.fstat(descriptor)
    finally:
        os.close(descriptor)

    after_path = path.lstat()
    if (
        _stat_identity(after_open) != _stat_identity(opened)
        or _stat_identity(after_path) != _stat_identity(opened)
        or _is_reparse_stat(after_path)
    ):
        raise RuntimeError(f"file changed while hashing: {_bounded_diagnostic(path)}")
    return {"type": "file", "size": opened.st_size, "sha256": digest.hexdigest()}


def _bound_regular_file_metadata(path: Path) -> dict[str, object]:
    """Capture content plus the identity of the exact current path occupant."""

    metadata = _regular_file_metadata(path)
    info = path.lstat()
    if _is_reparse_stat(info) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise RuntimeError(
            f"bound deletion handle is linked, reparse, or non-regular: "
            f"{_bounded_diagnostic(path)}"
        )
    device, inode = _object_identity(info)
    return {**metadata, "device": device, "inode": inode}


WINDOWS_RESERVED_BASENAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "CONIN$",
    "CONOUT$",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
    *(f"COM{digit}" for digit in "¹²³"),
    *(f"LPT{digit}" for digit in "¹²³"),
}


def _safe_path_component(part: str) -> bool:
    if not part or part in {".", ".."} or ":" in part or "\x00" in part:
        return False
    # Win32 strips trailing spaces/dots and treats the prefix before the first
    # dot as a DOS device name. Reject those aliases on every platform so a
    # transaction written on one OS cannot address a different path on Windows.
    if part != part.rstrip(" ."):
        return False
    basename = part.split(".", 1)[0].upper()
    return basename not in WINDOWS_RESERVED_BASENAMES


def _safe_relative_path(relative: object, *, allow_root: bool = False) -> bool:
    if not isinstance(relative, str):
        return False
    if allow_root and relative == "":
        return True
    return (
        bool(relative)
        and "\\" not in relative
        and "\x00" not in relative
        and not relative.startswith("/")
        and all(_safe_path_component(part) for part in relative.split("/"))
    )


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class PathSnapshot:
    root_type: str
    entries: dict[str, dict[str, object]]
    root_identity: tuple[int, int]
    sha256: str


def _snapshot_sha256(
    root_type: str,
    entries: Mapping[str, Mapping[str, object]],
    root_identity: tuple[int, int],
) -> str:
    return _canonical_sha256(
        {
            "root_type": root_type,
            "root_identity": list(root_identity),
            "entries": entries,
        }
    )


def _capture_path_snapshot(path: Path) -> PathSnapshot:
    """Capture every entry without following links or silently ignoring extras."""
    root_info = path.lstat()
    if _is_reparse_stat(root_info) or stat.S_ISLNK(root_info.st_mode):
        raise RuntimeError(f"refusing link or reparse artifact: {_bounded_diagnostic(path)}")
    root_identity = _object_identity(root_info)
    if stat.S_ISREG(root_info.st_mode):
        entries = {"": _bound_regular_file_metadata(path)}
        if (
            int(entries[""]["device"]),
            int(entries[""]["inode"]),
        ) != root_identity:
            raise RuntimeError(f"file root changed during capture: {_bounded_diagnostic(path)}")
        return PathSnapshot(
            "file",
            entries,
            root_identity,
            _snapshot_sha256("file", entries, root_identity),
        )
    if not stat.S_ISDIR(root_info.st_mode):
        raise RuntimeError(f"refusing special artifact: {_bounded_diagnostic(path)}")

    entries: dict[str, dict[str, object]] = {}
    for current, directory_names, file_names in os.walk(path, topdown=True, followlinks=False):
        current_path = Path(current)
        current_info = current_path.lstat()
        if _is_reparse_stat(current_info) or not stat.S_ISDIR(current_info.st_mode):
            raise RuntimeError(
                f"directory changed or became a reparse point: {_bounded_diagnostic(current_path)}"
            )
        current_relative = current_path.relative_to(path).as_posix()
        expected_identity = (
            root_identity
            if current_path == path
            else (
                int(entries[current_relative]["device"]),
                int(entries[current_relative]["inode"]),
            )
        )
        if _object_identity(current_info) != expected_identity:
            raise RuntimeError(
                f"directory identity changed during capture: "
                f"{_bounded_diagnostic(current_path)}"
            )
        directory_names.sort()
        file_names.sort()
        if len(entries) + len(directory_names) + len(file_names) > MAX_MANIFEST_ENTRIES:
            raise RuntimeError("artifact has too many entries to inspect safely")
        for name in directory_names:
            child = current_path / name
            info = child.lstat()
            if _is_reparse_stat(info) or stat.S_ISLNK(info.st_mode):
                raise RuntimeError(f"refusing link or reparse artifact: {_bounded_diagnostic(child)}")
            if not stat.S_ISDIR(info.st_mode):
                raise RuntimeError(f"directory changed type: {_bounded_diagnostic(child)}")
            relative = child.relative_to(path).as_posix()
            device, inode = _object_identity(info)
            entries[relative] = {"type": "dir", "device": device, "inode": inode}
        for name in file_names:
            child = current_path / name
            relative = child.relative_to(path).as_posix()
            entries[relative] = _bound_regular_file_metadata(child)
    ordered = dict(sorted(entries.items()))
    final_root = path.lstat()
    if (
        _is_reparse_stat(final_root)
        or not stat.S_ISDIR(final_root.st_mode)
        or _object_identity(final_root) != root_identity
    ):
        raise RuntimeError(f"directory root changed during capture: {_bounded_diagnostic(path)}")
    return PathSnapshot(
        "dir",
        ordered,
        root_identity,
        _snapshot_sha256("dir", ordered, root_identity),
    )


def _expected_directories(manifest: Mapping[str, Mapping[str, object]]) -> list[str]:
    directories: set[str] = set()
    for relative in manifest:
        parts = relative.split("/")[:-1]
        for index in range(1, len(parts) + 1):
            directories.add("/".join(parts[:index]))
    return sorted(directories)


def _reject_duplicate_pairs(pairs: list[tuple[object, object]]) -> dict[object, object]:
    result: dict[object, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key: {_bounded_diagnostic(repr(key), 160)}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> object:
    raise ValueError(f"non-finite JSON number: {_bounded_diagnostic(value, 80)}")


@contextmanager
def _locked_record_descriptor(descriptor: int) -> Iterator[None]:
    """Hold an exclusive byte-range lock while installer authority is read."""
    if os.name == "nt":
        import ctypes
        import msvcrt
        from ctypes import wintypes

        class Overlapped(ctypes.Structure):
            _fields_ = [
                ("Internal", ctypes.c_size_t),
                ("InternalHigh", ctypes.c_size_t),
                ("Offset", wintypes.DWORD),
                ("OffsetHigh", wintypes.DWORD),
                ("hEvent", wintypes.HANDLE),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        lock_file = kernel32.LockFileEx
        lock_file.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(Overlapped),
        ]
        lock_file.restype = wintypes.BOOL
        unlock_file = kernel32.UnlockFileEx
        unlock_file.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(Overlapped),
        ]
        unlock_file.restype = wintypes.BOOL
        handle = wintypes.HANDLE(msvcrt.get_osfhandle(descriptor))
        overlapped = Overlapped()
        range_length = MAX_RECORD_BYTES + 1
        flags = 0x00000001 | 0x00000002  # FAIL_IMMEDIATELY | EXCLUSIVE_LOCK
        if not lock_file(handle, flags, 0, range_length, 0, ctypes.byref(overlapped)):
            error = ctypes.get_last_error()
            raise OSError(error, "record is being modified by another process")
        try:
            yield
        finally:
            if not unlock_file(
                handle, 0, range_length, 0, ctypes.byref(overlapped)
            ):
                error = ctypes.get_last_error()
                raise OSError(error, "could not release installer record lock")
        return

    import fcntl

    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)


def _read_json_record(path: Path) -> tuple[dict[str, object], bytes]:
    before = path.lstat()
    if _is_reparse_stat(before) or stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise ValueError("record is not a non-reparse regular file")
    if before.st_nlink != 1:
        raise ValueError("record is hard-linked and cannot grant installer authority")
    if before.st_size <= 0 or before.st_size > MAX_RECORD_BYTES:
        raise ValueError(f"record size is outside the safe limit: {before.st_size}")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        with _locked_record_descriptor(descriptor):
            opened = os.fstat(descriptor)
            if (
                _is_reparse_stat(opened)
                or not stat.S_ISREG(opened.st_mode)
                or opened.st_nlink != 1
                or _stat_identity(opened) != _stat_identity(before)
            ):
                raise ValueError("record changed while it was being opened")
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = os.read(
                    descriptor,
                    min(1024 * 1024, MAX_RECORD_BYTES + 1 - total),
                )
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                if total > MAX_RECORD_BYTES:
                    raise ValueError("record exceeds the safe size limit")
            after_open = os.fstat(descriptor)
            after_path = path.lstat()
            if (
                _stat_identity(after_open) != _stat_identity(opened)
                or _stat_identity(after_path) != _stat_identity(opened)
                or _is_reparse_stat(after_path)
                or after_path.st_nlink != 1
                or (os.name != "nt" and after_path.st_ctime_ns != before.st_ctime_ns)
            ):
                raise ValueError("record changed while it was being read")
    finally:
        os.close(descriptor)
    final_path = path.lstat()
    if (
        _stat_identity(final_path) != _stat_identity(opened)
        or _is_reparse_stat(final_path)
        or final_path.st_nlink != 1
        or (os.name != "nt" and final_path.st_ctime_ns != before.st_ctime_ns)
    ):
        raise ValueError("record changed while it was being read")
    raw = b"".join(chunks)
    if len(raw) != opened.st_size:
        raise ValueError("record size changed while it was being read")
    try:
        decoded = raw.decode("utf-8")
        value = json.loads(
            decoded,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"record is not strict JSON: {_bounded_diagnostic(exc, 240)}") from exc
    if not isinstance(value, dict):
        raise ValueError("record root must be an object")
    return value, raw


def _write_json_exclusive(path: Path, record: Mapping[str, object]) -> bytes:
    raw = (
        json.dumps(record, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")
    if not raw or len(raw) > MAX_RECORD_BYTES:
        raise RuntimeError("transaction metadata is outside the safe size limit")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        offset = 0
        while offset < len(raw):
            offset += os.write(descriptor, raw[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return raw


def payload_manifest(root: Path) -> dict[str, dict[str, object]]:
    """Return the deterministic manifest copied by this installer."""
    manifest: dict[str, dict[str, object]] = {}
    for current, directory_names, file_names in os.walk(root):
        ignored = ignore_runtime_noise(current, directory_names + file_names)
        directory_names[:] = sorted(name for name in directory_names if name not in ignored)
        for name in directory_names:
            candidate = Path(current) / name
            info = candidate.lstat()
            if _is_reparse_stat(info) or stat.S_ISLNK(info.st_mode):
                raise RuntimeError(
                    f"source payload contains a link or reparse point: "
                    f"{_bounded_diagnostic(candidate)}"
                )
        for name in sorted(file_names):
            if name in ignored:
                continue
            path = Path(current) / name
            info = path.lstat()
            if _is_reparse_stat(info) or stat.S_ISLNK(info.st_mode):
                raise RuntimeError(
                    f"source payload contains a link or reparse point: "
                    f"{_bounded_diagnostic(path)}"
                )
            if not stat.S_ISREG(info.st_mode):
                continue
            relative = path.relative_to(root).as_posix()
            metadata = _regular_file_metadata(path)
            manifest[relative] = {"size": metadata["size"], "sha256": metadata["sha256"]}
    return manifest


def _manifest_sha256(manifest: dict[str, dict[str, object]]) -> str:
    return _canonical_sha256(manifest)


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _validate_payload_manifest(value: object) -> dict[str, dict[str, object]]:
    if not isinstance(value, dict) or not value:
        raise ValueError("file manifest must be a non-empty object")
    if len(value) > MAX_MANIFEST_ENTRIES:
        raise ValueError("file manifest has too many entries")
    if any(not isinstance(relative, str) for relative in value):
        raise ValueError("file manifest paths must be strings")
    if list(value) != sorted(value):
        raise ValueError("file manifest paths must be sorted")
    validated: dict[str, dict[str, object]] = {}
    for relative, metadata in value.items():
        if not _safe_relative_path(relative):
            raise ValueError(
                f"file manifest contains an unsafe path: "
                f"{_bounded_diagnostic(repr(relative), 180)}"
            )
        if not isinstance(metadata, dict) or set(metadata) != {"sha256", "size"}:
            raise ValueError(
                f"file manifest metadata is invalid for "
                f"{_bounded_diagnostic(relative, 180)}"
            )
        size = metadata.get("size")
        digest = metadata.get("sha256")
        if type(size) is not int or size < 0 or not _is_sha256(digest):
            raise ValueError(
                f"file manifest metadata is invalid for "
                f"{_bounded_diagnostic(relative, 180)}"
            )
        validated[relative] = {"size": size, "sha256": digest}
    return validated


def _completion_record(destination: Path) -> tuple[dict[str, object], bytes]:
    record, raw = _read_json_record(destination / COMPLETION_MARKER)
    expected_keys = {
        "file_count",
        "files",
        "format_version",
        "manifest_sha256",
        "skill_name",
    }
    if set(record) != expected_keys:
        raise ValueError("completion marker has unexpected or missing fields")
    if type(record.get("format_version")) is not int or record["format_version"] != COMPLETION_FORMAT_VERSION:
        raise ValueError("completion marker format is unsupported")
    if record.get("skill_name") != SKILL_NAME:
        raise ValueError("completion marker names a different skill")
    files = _validate_payload_manifest(record.get("files"))
    if type(record.get("file_count")) is not int or record["file_count"] != len(files):
        raise ValueError("completion marker file count does not match its manifest")
    digest = record.get("manifest_sha256")
    if not _is_sha256(digest) or digest != _manifest_sha256(files):
        raise ValueError("completion marker manifest digest does not match")
    record["files"] = files
    return record, raw


def write_completion_marker(
    destination: Path, manifest: dict[str, dict[str, object]]
) -> None:
    manifest = _validate_payload_manifest(dict(sorted(manifest.items())))
    record = {
        "format_version": COMPLETION_FORMAT_VERSION,
        "skill_name": SKILL_NAME,
        "file_count": len(manifest),
        "manifest_sha256": _manifest_sha256(manifest),
        "files": manifest,
    }
    marker = destination / COMPLETION_MARKER
    _write_json_exclusive(marker, record)


def validate_completed_install(destination: Path) -> tuple[bool, str]:
    """Validate a managed install using its completion manifest.

    Extra files are deliberately allowed. The marker owns only the files the
    installer wrote, so runtime caches or user notes do not make a complete
    install look corrupt.
    """
    try:
        root_info = destination.lstat()
        if _is_reparse_stat(root_info) or not stat.S_ISDIR(root_info.st_mode):
            return False, "destination is not a non-reparse directory"
        record, _ = _completion_record(destination)
        files = record["files"]
        assert isinstance(files, dict)
        resolved_root = destination.resolve(strict=True)
        for relative, expected in files.items():
            path = destination.joinpath(*relative.split("/"))
            resolved_path = path.resolve(strict=True)
            if resolved_root not in resolved_path.parents:
                return False, (
                    "installed path escapes the destination: "
                    f"{_bounded_diagnostic(relative, 180)}"
                )
            actual = _regular_file_metadata(path)
            if actual["size"] != expected["size"]:
                return False, (
                    "installed file size does not match: "
                    f"{_bounded_diagnostic(relative, 180)}"
                )
            if actual["sha256"] != expected["sha256"]:
                return False, (
                    "installed file digest does not match: "
                    f"{_bounded_diagnostic(relative, 180)}"
                )
    except FileNotFoundError as exc:
        return False, f"completion marker or installed file is missing: {_bounded_diagnostic(exc, 240)}"
    except (OSError, RuntimeError, ValueError) as exc:
        return False, f"completion marker is untrusted: {_bounded_diagnostic(exc, 300)}"
    return True, "completion marker and managed files are valid"


def _classify_payload_subset(
    snapshot: PathSnapshot,
    expected_manifest: dict[str, dict[str, object]],
    *,
    allowed_internal_files: set[str] | None = None,
) -> tuple[str, str]:
    if snapshot.root_type != "dir":
        return "unknown", "destination exists but is not a directory"
    allowed_internal = allowed_internal_files or set()
    expected_directories = set(_expected_directories(expected_manifest))
    present_payload: set[str] = set()
    unmanaged: str | None = None
    for relative, metadata in snapshot.entries.items():
        entry_type = metadata.get("type")
        if entry_type == "dir":
            if relative not in expected_directories:
                unmanaged = unmanaged or f"unmanaged directory: {_bounded_diagnostic(relative, 180)}"
            continue
        if relative in allowed_internal:
            continue
        expected = expected_manifest.get(relative)
        if expected is None:
            unmanaged = unmanaged or f"unmanaged file: {_bounded_diagnostic(relative, 180)}"
            continue
        if metadata.get("size") != expected["size"] or metadata.get("sha256") != expected["sha256"]:
            return "unknown", (
                "unmarked install file differs from the current payload: "
                f"{_bounded_diagnostic(relative, 180)}"
            )
        present_payload.add(relative)
    if present_payload == set(expected_manifest):
        return "complete", "legacy install contains the complete current source payload"
    if not present_payload:
        return "unknown", "empty unmarked directories are never auto-repaired"
    if unmanaged:
        return "unknown", f"partial unmarked install also contains {unmanaged}"
    return "incomplete", "legacy partial contains only exact current-payload bytes"


def classify_existing_install(
    destination: Path, expected_manifest: dict[str, dict[str, object]]
) -> tuple[str, str]:
    """Classify an existing path without overwriting an ambiguous legacy copy."""
    if not _path_exists(destination):
        return "missing", "destination does not exist"
    expected_manifest = _validate_payload_manifest(dict(sorted(expected_manifest.items())))
    try:
        snapshot = _capture_path_snapshot(destination)
    except (OSError, RuntimeError) as exc:
        return "unknown", f"existing path cannot be inspected safely: {_bounded_diagnostic(exc, 280)}"
    marker = destination / COMPLETION_MARKER
    if _path_exists(marker):
        valid, reason = validate_completed_install(destination)
        if valid:
            return "complete", reason
        try:
            record, _ = _completion_record(destination)
            if record["files"] != expected_manifest:
                return "unknown", "completion marker belongs to a different source payload"
            allowed_internal = {COMPLETION_MARKER}
            provenance = destination / PROVENANCE_MARKER
            if _path_exists(provenance):
                _validate_persisted_provenance(
                    provenance, _manifest_sha256(expected_manifest)
                )
                allowed_internal.add(PROVENANCE_MARKER)
            state, subset_reason = _classify_payload_subset(
                snapshot,
                expected_manifest,
                allowed_internal_files=allowed_internal,
            )
            if state == "incomplete":
                return state, f"trusted managed install is incomplete: {subset_reason}"
            return "unknown", subset_reason
        except (OSError, RuntimeError, ValueError) as exc:
            return "unknown", (
                "completion marker is untrusted: "
                f"{_bounded_diagnostic(exc, 280)}"
            )
    return _classify_payload_subset(snapshot, expected_manifest)


def _validate_open_lock(
    lock_path: Path,
    descriptor: int,
    allowed_sizes: tuple[int, ...],
) -> None:
    opened = os.fstat(descriptor)
    current = lock_path.lstat()
    if (
        _is_reparse_stat(opened)
        or _is_reparse_stat(current)
        or stat.S_ISLNK(opened.st_mode)
        or stat.S_ISLNK(current.st_mode)
        or not stat.S_ISREG(opened.st_mode)
        or not stat.S_ISREG(current.st_mode)
        or opened.st_nlink != 1
        or current.st_nlink != 1
        or opened.st_size not in allowed_sizes
        or _stat_identity(opened) != _stat_identity(current)
    ):
        raise ValueError(
            f"installer lock is linked, replaced, or malformed: "
            f"{_bounded_diagnostic(lock_path, 220)}"
        )


def _open_install_lock(lock_path: Path):
    """Open a lock without ever writing through a user-controlled pathname."""
    flags = (
        os.O_RDWR
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        descriptor = os.open(lock_path, flags | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        descriptor = os.open(lock_path, flags)
    try:
        # New locks are empty. A one-byte file is accepted for compatibility
        # with prior installer releases, but neither form is ever mutated.
        _validate_open_lock(lock_path, descriptor, (0, 1))
        os.lseek(descriptor, 0, os.SEEK_SET)
        return os.fdopen(descriptor, "r+b", closefd=True)
    except Exception:
        os.close(descriptor)
        raise


@contextmanager
def exclusive_install_lock(skills_dir: Path) -> Iterator[None]:
    """Serialize cooperating installers and release automatically on process death."""
    lock_path = skills_dir / LOCK_NAME
    handle = _open_install_lock(lock_path)
    acquired = False
    lock_context = None
    deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
    try:
        while not acquired:
            candidate = _locked_record_descriptor(handle.fileno())
            try:
                candidate.__enter__()
                lock_context = candidate
                acquired = True
            except (BlockingIOError, OSError) as exc:
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        f"timed out waiting for installer lock {lock_path}"
                    ) from exc
                time.sleep(0.05)
        _validate_open_lock(lock_path, handle.fileno(), (0, 1))
        yield
    finally:
        try:
            if acquired and lock_context is not None:
                lock_context.__exit__(None, None, None)
        finally:
            handle.close()


def _record_with_digest(record: dict[str, object]) -> dict[str, object]:
    signed = dict(record)
    signed["record_sha256"] = _canonical_sha256(record)
    return signed


def _validate_record_digest(record: dict[str, object]) -> None:
    digest = record.get("record_sha256")
    if not _is_sha256(digest):
        raise ValueError("metadata record digest is invalid")
    unsigned = dict(record)
    del unsigned["record_sha256"]
    if digest != _canonical_sha256(unsigned):
        raise ValueError("metadata record digest does not match")


def _validate_tree_entries(
    value: object, root_type: str
) -> dict[str, dict[str, object]]:
    if not isinstance(value, dict) or len(value) > MAX_MANIFEST_ENTRIES:
        raise ValueError("tree manifest is invalid or too large")
    if any(not isinstance(relative, str) for relative in value):
        raise ValueError("tree manifest paths must be strings")
    if list(value) != sorted(value):
        raise ValueError("tree manifest paths must be sorted")
    validated: dict[str, dict[str, object]] = {}
    for relative, metadata in value.items():
        if not _safe_relative_path(relative, allow_root=root_type == "file"):
            raise ValueError(
                f"tree manifest contains an unsafe path: "
                f"{_bounded_diagnostic(repr(relative), 180)}"
            )
        if root_type == "file" and relative != "":
            raise ValueError("file-root tree manifest contains a child path")
        if not isinstance(metadata, dict):
            raise ValueError("tree manifest entry must be an object")
        entry_type = metadata.get("type")
        device = metadata.get("device")
        inode = metadata.get("inode")
        if (
            type(device) is not int
            or device < 0
            or type(inode) is not int
            or inode < 0
        ):
            raise ValueError("tree manifest filesystem identity is invalid")
        if entry_type == "dir":
            if set(metadata) != {"device", "inode", "type"} or root_type != "dir":
                raise ValueError("tree directory metadata is invalid")
            validated[relative] = {
                "type": "dir",
                "device": device,
                "inode": inode,
            }
        elif entry_type == "file":
            if set(metadata) != {"device", "inode", "sha256", "size", "type"}:
                raise ValueError("tree file metadata is invalid")
            size = metadata.get("size")
            digest = metadata.get("sha256")
            if type(size) is not int or size < 0 or not _is_sha256(digest):
                raise ValueError("tree file metadata is invalid")
            validated[relative] = {
                "type": "file",
                "size": size,
                "sha256": digest,
                "device": device,
                "inode": inode,
            }
        else:
            raise ValueError("tree manifest contains an unsupported entry type")
    if root_type == "file" and set(validated) != {""}:
        raise ValueError("file-root tree manifest is incomplete")
    return validated


def _validate_root_identity(value: object) -> tuple[int, int]:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(type(item) is not int or item < 0 for item in value)
    ):
        raise ValueError("tree root filesystem identity is invalid")
    return (value[0], value[1])


def _transaction_path(skills_dir: Path) -> Path:
    return skills_dir / TRANSACTION_NAME


def _transaction_record(
    stage_name: str,
    quarantine_name: str,
    transaction_id: str,
    expected_manifest: dict[str, dict[str, object]],
    old_snapshot: PathSnapshot | None,
) -> dict[str, object]:
    record: dict[str, object] = {
        "backup_name": BACKUP_NAME,
        "destination_name": SKILL_NAME,
        "format_version": TRANSACTION_FORMAT_VERSION,
        "had_destination": old_snapshot is not None,
        "old_entry_count": len(old_snapshot.entries) if old_snapshot else 0,
        "old_root_identity": list(old_snapshot.root_identity) if old_snapshot else None,
        "old_root_type": old_snapshot.root_type if old_snapshot else "missing",
        "old_tree_entries": old_snapshot.entries if old_snapshot else {},
        "old_tree_sha256": old_snapshot.sha256 if old_snapshot else None,
        "payload_directories": _expected_directories(expected_manifest),
        "payload_file_count": len(expected_manifest),
        "payload_manifest": expected_manifest,
        "payload_manifest_sha256": _manifest_sha256(expected_manifest),
        "quarantine_name": quarantine_name,
        "skill_name": SKILL_NAME,
        "stage_name": stage_name,
        "transaction_id": transaction_id,
    }
    return _record_with_digest(record)


def _load_transaction(skills_dir: Path) -> tuple[dict[str, object], bytes]:
    record, raw = _read_json_record(_transaction_path(skills_dir))
    expected_keys = {
        "backup_name",
        "destination_name",
        "format_version",
        "had_destination",
        "old_entry_count",
        "old_root_identity",
        "old_root_type",
        "old_tree_entries",
        "old_tree_sha256",
        "payload_directories",
        "payload_file_count",
        "payload_manifest",
        "payload_manifest_sha256",
        "quarantine_name",
        "record_sha256",
        "skill_name",
        "stage_name",
        "transaction_id",
    }
    if set(record) != expected_keys:
        raise ValueError("transaction record has unexpected or missing fields")
    _validate_record_digest(record)
    if type(record.get("format_version")) is not int or record["format_version"] != TRANSACTION_FORMAT_VERSION:
        raise ValueError("transaction record format is unsupported")
    if record.get("skill_name") != SKILL_NAME:
        raise ValueError("transaction record names a different skill")
    if record.get("destination_name") != SKILL_NAME or record.get("backup_name") != BACKUP_NAME:
        raise ValueError("transaction record names an unexpected destination or backup")
    transaction_id = record.get("transaction_id")
    if (
        not isinstance(transaction_id, str)
        or len(transaction_id) != 32
        or any(character not in "0123456789abcdef" for character in transaction_id)
    ):
        raise ValueError("transaction id is invalid")
    stage_name = record.get("stage_name")
    expected_suffix = f"-{transaction_id}"
    if (
        not isinstance(stage_name, str)
        or not stage_name.startswith(STAGE_PREFIX)
        or not stage_name.endswith(expected_suffix)
        or not stage_name[len(STAGE_PREFIX) : -len(expected_suffix)].isdigit()
    ):
        raise ValueError("transaction stage name is invalid")
    if record.get("quarantine_name") != f"{QUARANTINE_PREFIX}{transaction_id}":
        raise ValueError("transaction quarantine name is invalid")

    manifest = _validate_payload_manifest(record.get("payload_manifest"))
    if type(record.get("payload_file_count")) is not int or record["payload_file_count"] != len(manifest):
        raise ValueError("transaction payload file count does not match")
    manifest_digest = record.get("payload_manifest_sha256")
    if not _is_sha256(manifest_digest) or manifest_digest != _manifest_sha256(manifest):
        raise ValueError("transaction payload digest does not match")
    directories = record.get("payload_directories")
    if (
        not isinstance(directories, list)
        or any(not _safe_relative_path(item) for item in directories)
        or directories != sorted(set(directories))
        or directories != _expected_directories(manifest)
    ):
        raise ValueError("transaction payload directories are invalid")

    had_destination = record.get("had_destination")
    if type(had_destination) is not bool:
        raise ValueError("transaction destination flag is invalid")
    old_root_type = record.get("old_root_type")
    if old_root_type not in {"missing", "file", "dir"}:
        raise ValueError("transaction old-root type is invalid")
    old_entries = _validate_tree_entries(
        record.get("old_tree_entries"), "dir" if old_root_type == "missing" else old_root_type
    )
    old_root_identity_value = record.get("old_root_identity")
    old_root_identity = (
        _validate_root_identity(old_root_identity_value)
        if old_root_identity_value is not None
        else None
    )
    old_digest = record.get("old_tree_sha256")
    old_count = record.get("old_entry_count")
    if type(old_count) is not int or old_count != len(old_entries):
        raise ValueError("transaction old-tree entry count does not match")
    if had_destination:
        if (
            old_root_type == "missing"
            or old_root_identity is None
            or not _is_sha256(old_digest)
        ):
            raise ValueError("transaction old-tree identity is missing")
        if old_digest != _snapshot_sha256(
            old_root_type,
            old_entries,
            old_root_identity,
        ):
            raise ValueError("transaction old-tree digest does not match")
    elif (
        old_root_type != "missing"
        or old_entries
        or old_root_identity is not None
        or old_digest is not None
        or old_count != 0
    ):
        raise ValueError("fresh transaction contains an old-tree identity")
    record["payload_manifest"] = manifest
    record["old_tree_entries"] = old_entries
    record["old_root_identity"] = old_root_identity
    return record, raw


def _provenance_record(
    transaction: Mapping[str, object], transaction_raw: bytes
) -> dict[str, object]:
    record = {
        "backup_name": BACKUP_NAME,
        "destination_name": SKILL_NAME,
        "format_version": TRANSACTION_FORMAT_VERSION,
        "payload_manifest_sha256": transaction["payload_manifest_sha256"],
        "quarantine_name": transaction["quarantine_name"],
        "skill_name": SKILL_NAME,
        "stage_name": transaction["stage_name"],
        "transaction_id": transaction["transaction_id"],
        "transaction_record_sha256": hashlib.sha256(transaction_raw).hexdigest(),
    }
    return _record_with_digest(record)


def _load_provenance(path: Path) -> tuple[dict[str, object], bytes]:
    record, raw = _read_json_record(path)
    expected_keys = {
        "backup_name",
        "destination_name",
        "format_version",
        "payload_manifest_sha256",
        "quarantine_name",
        "record_sha256",
        "skill_name",
        "stage_name",
        "transaction_id",
        "transaction_record_sha256",
    }
    if set(record) != expected_keys:
        raise ValueError("provenance marker has unexpected or missing fields")
    _validate_record_digest(record)
    if type(record.get("format_version")) is not int or record["format_version"] != TRANSACTION_FORMAT_VERSION:
        raise ValueError("provenance marker format is unsupported")
    if (
        record.get("skill_name") != SKILL_NAME
        or record.get("destination_name") != SKILL_NAME
        or record.get("backup_name") != BACKUP_NAME
    ):
        raise ValueError("provenance marker names an unexpected install")
    for field in ("payload_manifest_sha256", "transaction_record_sha256"):
        if not _is_sha256(record.get(field)):
            raise ValueError(f"provenance marker {field} is invalid")
    transaction_id = record.get("transaction_id")
    if (
        not isinstance(transaction_id, str)
        or len(transaction_id) != 32
        or any(character not in "0123456789abcdef" for character in transaction_id)
    ):
        raise ValueError("provenance marker transaction id is invalid")
    if record.get("quarantine_name") != f"{QUARANTINE_PREFIX}{transaction_id}":
        raise ValueError("provenance marker quarantine name is invalid")
    stage_name = record.get("stage_name")
    suffix = f"-{transaction_id}"
    if (
        not isinstance(stage_name, str)
        or not stage_name.startswith(STAGE_PREFIX)
        or not stage_name.endswith(suffix)
        or not stage_name[len(STAGE_PREFIX) : -len(suffix)].isdigit()
    ):
        raise ValueError("provenance marker stage name is invalid")
    return record, raw


def _validate_persisted_provenance(path: Path, payload_digest: str) -> None:
    record, _ = _load_provenance(path)
    if record["payload_manifest_sha256"] != payload_digest:
        raise ValueError("provenance marker belongs to a different payload")


def _validate_transaction_provenance(
    path: Path, transaction: Mapping[str, object], transaction_raw: bytes
) -> bytes:
    record, raw = _load_provenance(path)
    expected = _provenance_record(transaction, transaction_raw)
    if record != expected:
        raise ValueError("provenance marker does not match the active transaction")
    return raw


def _metadata_for_bytes(raw: bytes) -> dict[str, object]:
    return {"type": "file", "size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _content_metadata(metadata: Mapping[str, object]) -> dict[str, object]:
    return {
        key: metadata[key]
        for key in ("type", "size", "sha256")
        if key in metadata
    }


def _bound_metadata_for_bytes(path: Path, raw: bytes) -> dict[str, object]:
    metadata = _bound_regular_file_metadata(path)
    if _content_metadata(metadata) != _metadata_for_bytes(raw):
        raise RuntimeError(
            f"bound authority file differs from verified bytes: "
            f"{_bounded_diagnostic(path, 220)}"
        )
    return metadata


def _inspect_owned_stage(
    path: Path,
    transaction: Mapping[str, object],
    transaction_raw: bytes,
    *,
    require_complete: bool,
) -> PathSnapshot:
    snapshot = _capture_path_snapshot(path)
    if snapshot.root_type != "dir":
        raise RuntimeError("owned stage is not a directory")
    provenance_path = path / PROVENANCE_MARKER
    provenance_raw = _validate_transaction_provenance(
        provenance_path, transaction, transaction_raw
    )
    expected_manifest = transaction["payload_manifest"]
    assert isinstance(expected_manifest, dict)
    expected_directories = set(transaction["payload_directories"])
    present_payload: set[str] = set()
    completion_present = False
    for relative, metadata in snapshot.entries.items():
        if metadata.get("type") == "dir":
            if relative not in expected_directories:
                raise RuntimeError(
                    f"owned stage contains an unexpected directory: "
                    f"{_bounded_diagnostic(relative, 180)}"
                )
            continue
        if relative == PROVENANCE_MARKER:
            if _content_metadata(metadata) != _metadata_for_bytes(provenance_raw):
                raise RuntimeError("owned stage provenance changed during inspection")
            continue
        if relative == COMPLETION_MARKER:
            completion, _ = _completion_record(path)
            if completion["files"] != expected_manifest:
                raise RuntimeError("owned stage completion marker names a different payload")
            completion_present = True
            continue
        expected = expected_manifest.get(relative)
        if expected is None:
            raise RuntimeError(
                f"owned stage contains an unexpected file: "
                f"{_bounded_diagnostic(relative, 180)}"
            )
        if metadata.get("size") != expected["size"] or metadata.get("sha256") != expected["sha256"]:
            raise RuntimeError(
                f"owned stage file differs from the source payload: "
                f"{_bounded_diagnostic(relative, 180)}"
            )
        present_payload.add(relative)
    if require_complete:
        if present_payload != set(expected_manifest) or not completion_present:
            raise RuntimeError("owned stage is not a complete source payload")
    return snapshot


def _snapshot_from_transaction(transaction: Mapping[str, object]) -> PathSnapshot | None:
    if not transaction["had_destination"]:
        return None
    root_type = transaction["old_root_type"]
    entries = transaction["old_tree_entries"]
    root_identity = transaction["old_root_identity"]
    digest = transaction["old_tree_sha256"]
    assert (
        isinstance(root_type, str)
        and isinstance(entries, dict)
        and isinstance(root_identity, tuple)
        and isinstance(digest, str)
    )
    return PathSnapshot(root_type, entries, root_identity, digest)


def _assert_snapshot_equal(actual: PathSnapshot, expected: PathSnapshot, label: str) -> None:
    if actual != expected:
        raise RuntimeError(f"{label} changed after transaction ownership was recorded")


def _remove_path(path: Path) -> None:
    """Remove only an empty, non-reparse directory.

    Recursive removal requires a transaction-bound snapshot and is deliberately
    kept in _delete_bound_tree. This compatibility helper cannot acquire
    authority merely from a reserved filename.
    """
    if not _path_exists(path):
        return
    info = path.lstat()
    if _is_reparse_stat(info) or not stat.S_ISDIR(info.st_mode):
        raise RuntimeError(f"refusing to remove an untrusted path: {_bounded_diagnostic(path)}")
    path.rmdir()


def _rename_directory(source: Path, destination: Path) -> None:
    """Rename within one skills directory, which is atomic for a missing target."""
    source.rename(destination)


def _reserved_stages(skills_dir: Path) -> list[Path]:
    stages = sorted(
        (Path(entry.path) for entry in os.scandir(skills_dir) if entry.name.startswith(STAGE_PREFIX)),
        key=lambda path: path.name,
    )
    if len(stages) > MAX_RESERVED_ARTIFACTS:
        raise RuntimeError("too many reserved-prefix stage artifacts; refusing recovery")
    return stages


def _reserved_quarantines(skills_dir: Path) -> list[Path]:
    quarantines = sorted(
        (
            Path(entry.path)
            for entry in os.scandir(skills_dir)
            if entry.name.startswith(QUARANTINE_PREFIX)
        ),
        key=lambda path: path.name,
    )
    if len(quarantines) > MAX_RESERVED_ARTIFACTS:
        raise RuntimeError("too many reserved-prefix quarantine artifacts; refusing recovery")
    return quarantines


def _quarantine_record_and_remove(
    record_path: Path, expected_raw: bytes, transaction_id: str
) -> None:
    if not _path_exists(record_path):
        return
    _, checked_raw = _read_json_record(record_path)
    if checked_raw != expected_raw:
        raise RuntimeError("transaction record changed before cleanup")
    done = record_path.parent / f"{TRANSACTION_DONE_PREFIX}{transaction_id}"
    if _path_exists(done):
        raise RuntimeError("transaction-record quarantine already exists")
    _rename_directory(record_path, done)
    try:
        _, quarantined_raw = _read_json_record(done)
        if quarantined_raw != expected_raw:
            raise RuntimeError("transaction record changed during quarantine")
        _delete_regular_file_by_handle(
            done,
            _bound_metadata_for_bytes(done, expected_raw),
        )
    except Exception:
        raise


def _quarantine_record(
    transaction: Mapping[str, object],
    transaction_raw: bytes,
    purpose: str,
    authorized: PathSnapshot,
) -> dict[str, object]:
    record: dict[str, object] = {
        "authorized_entries": authorized.entries,
        "authorized_root_identity": list(authorized.root_identity),
        "authorized_root_type": authorized.root_type,
        "authorized_sha256": authorized.sha256,
        "format_version": TRANSACTION_FORMAT_VERSION,
        "purpose": purpose,
        "skill_name": SKILL_NAME,
        "transaction_id": transaction["transaction_id"],
        "transaction_record_sha256": hashlib.sha256(transaction_raw).hexdigest(),
    }
    return _record_with_digest(record)


def _load_quarantine_record(
    path: Path, transaction: Mapping[str, object], transaction_raw: bytes
) -> tuple[dict[str, object], bytes, PathSnapshot]:
    record, raw = _read_json_record(path / QUARANTINE_MARKER)
    expected_keys = {
        "authorized_entries",
        "authorized_root_identity",
        "authorized_root_type",
        "authorized_sha256",
        "format_version",
        "purpose",
        "record_sha256",
        "skill_name",
        "transaction_id",
        "transaction_record_sha256",
    }
    if set(record) != expected_keys:
        raise ValueError("quarantine marker has unexpected or missing fields")
    _validate_record_digest(record)
    if (
        type(record.get("format_version")) is not int
        or record["format_version"] != TRANSACTION_FORMAT_VERSION
        or record.get("skill_name") != SKILL_NAME
        or record.get("transaction_id") != transaction["transaction_id"]
        or record.get("transaction_record_sha256")
        != hashlib.sha256(transaction_raw).hexdigest()
        or record.get("purpose") not in {"backup", "stage"}
    ):
        raise ValueError("quarantine marker does not match the active transaction")
    root_type = record.get("authorized_root_type")
    if root_type not in {"file", "dir"}:
        raise ValueError("quarantine marker root type is invalid")
    entries = _validate_tree_entries(record.get("authorized_entries"), root_type)
    root_identity = _validate_root_identity(record.get("authorized_root_identity"))
    digest = record.get("authorized_sha256")
    if not _is_sha256(digest) or digest != _snapshot_sha256(
        root_type,
        entries,
        root_identity,
    ):
        raise ValueError("quarantine marker authorized digest does not match")
    return record, raw, PathSnapshot(root_type, entries, root_identity, digest)


def _entry_matches(actual: Mapping[str, object], expected: Mapping[str, object]) -> bool:
    return dict(actual) == dict(expected)


def _validate_bound_subset(
    snapshot: PathSnapshot,
    authorized: PathSnapshot,
    extra_entries: Mapping[str, Mapping[str, object]] | None = None,
    *,
    require_exact: bool,
) -> None:
    if snapshot.root_type != authorized.root_type:
        raise RuntimeError("quarantined artifact changed root type")
    if snapshot.root_identity != authorized.root_identity:
        raise RuntimeError("quarantined artifact changed root filesystem identity")
    allowed = dict(authorized.entries)
    if extra_entries:
        allowed.update({key: dict(value) for key, value in extra_entries.items()})
    for relative, metadata in snapshot.entries.items():
        expected = allowed.get(relative)
        if expected is None or not _entry_matches(metadata, expected):
            raise RuntimeError(
                f"quarantined artifact contains changed or late data: "
                f"{_bounded_diagnostic(relative, 180)}"
            )
    if require_exact and snapshot.entries != allowed:
        raise RuntimeError("quarantined artifact changed before deletion")


def _descriptor_file_metadata(descriptor: int) -> tuple[dict[str, object], os.stat_result]:
    before = os.fstat(descriptor)
    if (
        _is_reparse_stat(before)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
    ):
        raise RuntimeError("bound deletion handle is linked, reparse, or non-regular")
    os.lseek(descriptor, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    total = 0
    while True:
        chunk = os.read(descriptor, 1024 * 1024)
        if not chunk:
            break
        digest.update(chunk)
        total += len(chunk)
    after = os.fstat(descriptor)
    if _stat_identity(after) != _stat_identity(before) or total != before.st_size:
        raise RuntimeError("bound deletion handle changed while it was verified")
    return (
        {
            "type": "file",
            "size": total,
            "sha256": digest.hexdigest(),
            "device": int(after.st_dev),
            "inode": int(after.st_ino),
        },
        after,
    )


def _delete_opened_posix_path(
    path: Path,
    opened: os.stat_result,
    *,
    is_directory: bool,
) -> None:
    """Move an opened object into a private directory before unlinking it.

    The quarantined tree can still be writable by another account. Keeping the
    final pathname inside a mode-0700 directory and addressing it relative to
    that opened directory closes the public tombstone swap window.
    """
    private_name = f"{PRIVATE_DELETE_PREFIX}{uuid.uuid4().hex}"
    parent_descriptor: int | None = None
    directory_descriptor: int | None = None
    created: os.stat_result | None = None
    moved = False
    deleted = False
    try:
        flags = (
            os.O_RDONLY
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        parent_descriptor = os.open(path.parent, flags)
        bound_parent = os.fstat(parent_descriptor)
        current_parent = path.parent.lstat()
        if (
            _is_reparse_stat(bound_parent)
            or not stat.S_ISDIR(bound_parent.st_mode)
            or _object_identity(bound_parent) != _object_identity(current_parent)
        ):
            raise RuntimeError("deletion parent changed while it was opened")
        current_object = os.stat(
            path.name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
        if _stat_identity(current_object) != _stat_identity(opened):
            raise RuntimeError("quarantined object changed before its private move")

        os.mkdir(private_name, 0o700, dir_fd=parent_descriptor)
        created = os.stat(
            private_name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
        directory_descriptor = os.open(
            private_name,
            flags,
            dir_fd=parent_descriptor,
        )
        bound_directory = os.fstat(directory_descriptor)
        if (
            _is_reparse_stat(bound_directory)
            or not stat.S_ISDIR(bound_directory.st_mode)
            or _object_identity(bound_directory) != _object_identity(created)
        ):
            raise RuntimeError("private deletion directory changed while it was opened")
        os.fchmod(directory_descriptor, 0o700)
        secured_directory = os.fstat(directory_descriptor)
        if stat.S_IMODE(secured_directory.st_mode) != 0o700:
            raise RuntimeError("private deletion directory permissions are not private")

        os.rename(
            path.name,
            PRIVATE_DELETE_ENTRY,
            src_dir_fd=parent_descriptor,
            dst_dir_fd=directory_descriptor,
        )
        moved = True
        moved_info = os.stat(
            PRIVATE_DELETE_ENTRY,
            dir_fd=directory_descriptor,
            follow_symlinks=False,
        )
        if _stat_identity(moved_info) != _stat_identity(opened):
            raise RuntimeError("quarantined object changed during private deletion move")
        if is_directory:
            os.rmdir(PRIVATE_DELETE_ENTRY, dir_fd=directory_descriptor)
        else:
            os.unlink(PRIVATE_DELETE_ENTRY, dir_fd=directory_descriptor)
        deleted = True
        if os.listdir(directory_descriptor):
            raise RuntimeError("private deletion directory gained unexpected entries")
    finally:
        if directory_descriptor is not None:
            os.close(directory_descriptor)
        try:
            # Remove the private container only while it is either still empty
            # or known to contain no object after a successful deletion. If
            # deletion failed after the move, retain the container and its
            # contents for fail-closed recovery.
            if (
                parent_descriptor is not None
                and created is not None
                and (not moved or deleted)
            ):
                current = os.stat(
                    private_name,
                    dir_fd=parent_descriptor,
                    follow_symlinks=False,
                )
                if (
                    _is_reparse_stat(current)
                    or not stat.S_ISDIR(current.st_mode)
                    or _object_identity(current) != _object_identity(created)
                ):
                    raise RuntimeError("private deletion directory changed before cleanup")
                os.rmdir(private_name, dir_fd=parent_descriptor)
        finally:
            if parent_descriptor is not None:
                os.close(parent_descriptor)


def _delete_regular_file_by_handle(
    path: Path, expected: Mapping[str, object]
) -> None:
    """Delete the verified file object, never a later occupant of its pathname."""
    if os.name == "nt":
        import ctypes
        import msvcrt
        from ctypes import wintypes

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
            str(path),
            0x80000000 | 0x00010000,  # GENERIC_READ | DELETE
            0x00000001 | 0x00000002 | 0x00000004,
            None,
            3,  # OPEN_EXISTING
            0x00200000 | 0x08000000,  # OPEN_REPARSE_POINT | SEQUENTIAL_SCAN
            None,
        )
        invalid = ctypes.c_void_p(-1).value
        if handle == invalid:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            descriptor = msvcrt.open_osfhandle(
                int(handle), os.O_RDONLY | getattr(os, "O_BINARY", 0)
            )
        except Exception:
            close_handle = kernel32.CloseHandle
            close_handle.argtypes = [wintypes.HANDLE]
            close_handle.restype = wintypes.BOOL
            close_handle(wintypes.HANDLE(handle))
            raise
        try:
            actual, opened = _descriptor_file_metadata(descriptor)
            if actual != dict(expected):
                raise RuntimeError(
                    f"quarantined file changed immediately before deletion: "
                    f"{_bounded_diagnostic(path.name, 180)}"
                )
            current = path.lstat()
            if _stat_identity(current) != _stat_identity(opened):
                raise RuntimeError(
                    f"quarantined file pathname changed before handle deletion: "
                    f"{_bounded_diagnostic(path.name, 180)}"
                )

            class FileDispositionInfo(ctypes.Structure):
                _fields_ = [("DeleteFile", wintypes.BOOL)]

            set_information = kernel32.SetFileInformationByHandle
            set_information.argtypes = [
                wintypes.HANDLE,
                wintypes.DWORD,
                wintypes.LPVOID,
                wintypes.DWORD,
            ]
            set_information.restype = wintypes.BOOL
            disposition = FileDispositionInfo(True)
            if not set_information(
                wintypes.HANDLE(msvcrt.get_osfhandle(descriptor)),
                4,  # FileDispositionInfo
                ctypes.byref(disposition),
                ctypes.sizeof(disposition),
            ):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            os.close(descriptor)
        return

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        actual, opened = _descriptor_file_metadata(descriptor)
        if actual != dict(expected):
            raise RuntimeError(
                f"quarantined file changed immediately before deletion: "
                f"{_bounded_diagnostic(path.name, 180)}"
            )
        current = path.lstat()
        if _stat_identity(current) != _stat_identity(opened):
            raise RuntimeError("quarantined file pathname changed before deletion")
        _delete_opened_posix_path(path, opened, is_directory=False)
    finally:
        os.close(descriptor)


def _delete_empty_directory_by_handle(
    path: Path,
    expected_identity: tuple[int, int],
) -> None:
    """Delete the opened empty directory object, not a later path occupant."""
    before = path.lstat()
    if _is_reparse_stat(before) or not stat.S_ISDIR(before.st_mode):
        raise RuntimeError(
            f"quarantined directory changed before deletion: "
            f"{_bounded_diagnostic(path, 200)}"
        )
    if _object_identity(before) != expected_identity:
        raise RuntimeError("quarantined directory object is not transaction-authorized")

    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

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
            str(path),
            0x00010000 | 0x00000080,  # DELETE | FILE_READ_ATTRIBUTES
            0x00000001 | 0x00000002 | 0x00000004,
            None,
            3,  # OPEN_EXISTING
            0x02000000 | 0x00200000,  # BACKUP_SEMANTICS | OPEN_REPARSE_POINT
            None,
        )
        invalid = ctypes.c_void_p(-1).value
        if handle == invalid:
            raise ctypes.WinError(ctypes.get_last_error())

        class ByHandleFileInformation(ctypes.Structure):
            _fields_ = [
                ("dwFileAttributes", wintypes.DWORD),
                ("ftCreationTime", wintypes.FILETIME),
                ("ftLastAccessTime", wintypes.FILETIME),
                ("ftLastWriteTime", wintypes.FILETIME),
                ("dwVolumeSerialNumber", wintypes.DWORD),
                ("nFileSizeHigh", wintypes.DWORD),
                ("nFileSizeLow", wintypes.DWORD),
                ("nNumberOfLinks", wintypes.DWORD),
                ("nFileIndexHigh", wintypes.DWORD),
                ("nFileIndexLow", wintypes.DWORD),
            ]

        close_handle = kernel32.CloseHandle
        close_handle.argtypes = [wintypes.HANDLE]
        close_handle.restype = wintypes.BOOL
        try:
            get_information = kernel32.GetFileInformationByHandle
            get_information.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(ByHandleFileInformation),
            ]
            get_information.restype = wintypes.BOOL
            opened = ByHandleFileInformation()
            if not get_information(handle, ctypes.byref(opened)):
                raise ctypes.WinError(ctypes.get_last_error())
            if (
                not opened.dwFileAttributes & 0x00000010
                or opened.dwFileAttributes & 0x00000400
            ):
                raise RuntimeError("bound deletion handle is not a non-reparse directory")

            current = path.lstat()
            file_index = (opened.nFileIndexHigh << 32) | opened.nFileIndexLow
            if (
                _is_reparse_stat(current)
                or not stat.S_ISDIR(current.st_mode)
                or _object_identity(current) != expected_identity
                or _stat_identity(current) != _stat_identity(before)
                or (current.st_ino and current.st_ino != file_index)
            ):
                raise RuntimeError("quarantined directory changed while it was opened")

            class FileDispositionInfo(ctypes.Structure):
                _fields_ = [("DeleteFile", wintypes.BOOL)]

            set_information = kernel32.SetFileInformationByHandle
            set_information.argtypes = [
                wintypes.HANDLE,
                wintypes.DWORD,
                wintypes.LPVOID,
                wintypes.DWORD,
            ]
            set_information.restype = wintypes.BOOL
            disposition = FileDispositionInfo(True)
            if not set_information(
                handle,
                4,  # FileDispositionInfo
                ctypes.byref(disposition),
                ctypes.sizeof(disposition),
            ):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            close_handle(handle)
        return

    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        current = path.lstat()
        if (
            _is_reparse_stat(opened)
            or not stat.S_ISDIR(opened.st_mode)
            or _object_identity(opened) != expected_identity
            or _stat_identity(opened) != _stat_identity(before)
            or _stat_identity(current) != _stat_identity(opened)
        ):
            raise RuntimeError("quarantined directory changed while it was opened")
        _delete_opened_posix_path(path, opened, is_directory=True)
    finally:
        os.close(descriptor)


def _delete_bound_tree(
    root: Path,
    authorized: PathSnapshot,
    extra_entries: Mapping[str, Mapping[str, object]] | None = None,
) -> None:
    """Delete only captured bytes; late files survive and make rmdir fail closed."""
    current = _capture_path_snapshot(root)
    _validate_bound_subset(current, authorized, extra_entries, require_exact=False)
    allowed = dict(authorized.entries)
    if extra_entries:
        allowed.update({key: dict(value) for key, value in extra_entries.items()})
    if authorized.root_type == "file":
        actual = _bound_regular_file_metadata(root)
        if actual != allowed[""]:
            raise RuntimeError("quarantined file changed immediately before deletion")
        _delete_regular_file_by_handle(root, allowed[""])
        return

    protected = [QUARANTINE_MARKER, PROVENANCE_MARKER]
    files = [
        relative
        for relative, metadata in allowed.items()
        if metadata.get("type") == "file" and relative not in protected
    ]
    files.extend(relative for relative in protected if relative in allowed)
    for relative in files:
        target = root.joinpath(*relative.split("/"))
        if not _path_exists(target):
            continue
        actual = _bound_regular_file_metadata(target)
        if actual != allowed[relative]:
            raise RuntimeError(
                f"quarantined file changed immediately before deletion: "
                f"{_bounded_diagnostic(relative, 180)}"
            )
        _delete_regular_file_by_handle(target, allowed[relative])
    directories = sorted(
        (
            relative
            for relative, metadata in allowed.items()
            if metadata.get("type") == "dir"
        ),
        key=lambda relative: (relative.count("/"), relative),
        reverse=True,
    )
    for relative in directories:
        target = root.joinpath(*relative.split("/"))
        if not _path_exists(target):
            continue
        expected_identity = (
            int(allowed[relative]["device"]),
            int(allowed[relative]["inode"]),
        )
        try:
            _delete_empty_directory_by_handle(target, expected_identity)
        except OSError as exc:
            raise RuntimeError(
                f"late data preserved in quarantine at {_bounded_diagnostic(target, 200)}: "
                f"{_bounded_diagnostic(exc, 180)}"
            ) from exc
    try:
        _delete_empty_directory_by_handle(root, authorized.root_identity)
    except OSError as exc:
        raise RuntimeError(
            f"late data preserved in quarantine at {_bounded_diagnostic(root, 220)}: "
            f"{_bounded_diagnostic(exc, 180)}"
        ) from exc


def _quarantine_and_delete(
    path: Path,
    snapshot: PathSnapshot,
    transaction: Mapping[str, object],
    transaction_raw: bytes,
    purpose: str,
) -> None:
    quarantine = path.parent / str(transaction["quarantine_name"])
    if _path_exists(quarantine):
        raise RuntimeError("transaction quarantine already exists; preserving both artifacts")
    _assert_snapshot_equal(_capture_path_snapshot(path), snapshot, purpose)
    _rename_directory(path, quarantine)
    quarantined = _capture_path_snapshot(quarantine)
    _assert_snapshot_equal(quarantined, snapshot, purpose)
    if quarantined.root_type == "file":
        _delete_bound_tree(quarantine, quarantined)
        return
    marker_record = _quarantine_record(transaction, transaction_raw, purpose, quarantined)
    marker_raw = _write_json_exclusive(quarantine / QUARANTINE_MARKER, marker_record)
    with_marker = _capture_path_snapshot(quarantine)
    marker_metadata = with_marker.entries.get(QUARANTINE_MARKER)
    if (
        marker_metadata is None
        or _content_metadata(marker_metadata) != _metadata_for_bytes(marker_raw)
    ):
        raise RuntimeError("quarantine authority marker changed after creation")
    marker_entry = {QUARANTINE_MARKER: marker_metadata}
    _validate_bound_subset(with_marker, quarantined, marker_entry, require_exact=True)
    _delete_bound_tree(quarantine, quarantined, marker_entry)


def _resume_quarantine(
    quarantine: Path,
    transaction: Mapping[str, object],
    transaction_raw: bytes,
) -> str:
    record, marker_raw, authorized = _load_quarantine_record(
        quarantine, transaction, transaction_raw
    )
    current = _capture_path_snapshot(quarantine)
    marker_metadata = current.entries.get(QUARANTINE_MARKER)
    if (
        marker_metadata is None
        or _content_metadata(marker_metadata) != _metadata_for_bytes(marker_raw)
    ):
        raise RuntimeError("quarantine authority marker changed before recovery")
    marker_entry = {QUARANTINE_MARKER: marker_metadata}
    _validate_bound_subset(current, authorized, marker_entry, require_exact=False)
    _delete_bound_tree(quarantine, authorized, marker_entry)
    purpose = record["purpose"]
    assert isinstance(purpose, str)
    return purpose


def _cleanup_stages(skills_dir: Path) -> None:
    recover_interrupted_transaction(skills_dir, skills_dir / SKILL_NAME)


def recover_interrupted_transaction(skills_dir: Path, destination: Path) -> None:
    """Recover only artifacts proven by one exact, immutable transaction."""
    backup = skills_dir / BACKUP_NAME
    transaction_path = _transaction_path(skills_dir)
    stages = _reserved_stages(skills_dir)
    quarantines = _reserved_quarantines(skills_dir)
    if not _path_exists(transaction_path):
        if _path_exists(backup):
            raise RuntimeError("untrusted reserved-name backup exists; preserving it")
        if stages:
            raise RuntimeError(
                f"untrusted reserved-prefix stage exists; preserving "
                f"{_bounded_diagnostic(stages[0].name, 180)}"
            )
        if quarantines:
            raise RuntimeError(
                f"untrusted reserved-prefix quarantine exists; preserving "
                f"{_bounded_diagnostic(quarantines[0].name, 180)}"
            )
        return
    try:
        transaction, transaction_raw = _load_transaction(skills_dir)
    except (OSError, RuntimeError, ValueError) as exc:
        raise RuntimeError(
            f"installer transaction record is untrusted; preserving all artifacts: "
            f"{_bounded_diagnostic(exc, 260)}"
        ) from exc
    expected_stage = skills_dir / str(transaction["stage_name"])
    unexpected_stages = [path for path in stages if path != expected_stage]
    if unexpected_stages:
        raise RuntimeError(
            f"untrusted reserved-prefix stage exists; preserving "
            f"{_bounded_diagnostic(unexpected_stages[0].name, 180)}"
        )
    expected_quarantine = skills_dir / str(transaction["quarantine_name"])
    unexpected_quarantines = [
        path for path in quarantines if path != expected_quarantine
    ]
    if unexpected_quarantines:
        raise RuntimeError(
            f"untrusted reserved-prefix quarantine exists; preserving "
            f"{_bounded_diagnostic(unexpected_quarantines[0].name, 180)}"
        )
    stage_snapshot = None
    if _path_exists(expected_stage):
        stage_snapshot = _inspect_owned_stage(
            expected_stage, transaction, transaction_raw, require_complete=False
        )

    old_snapshot = _snapshot_from_transaction(transaction)
    backup_snapshot = None
    if _path_exists(backup):
        if old_snapshot is None:
            raise RuntimeError("fresh transaction has an untrusted backup; preserving it")
        backup_snapshot = _capture_path_snapshot(backup)
        _assert_snapshot_equal(backup_snapshot, old_snapshot, "installer backup")

    quarantine = expected_quarantine
    if _path_exists(quarantine):
        quarantine_record, _, _ = _load_quarantine_record(
            quarantine, transaction, transaction_raw
        )
        purpose = quarantine_record["purpose"]
        live_snapshot = (
            _capture_path_snapshot(destination) if _path_exists(destination) else None
        )
        if purpose == "backup":
            if backup_snapshot is not None or stage_snapshot is not None or live_snapshot is None:
                raise RuntimeError("backup quarantine exists in an ambiguous transaction state")
            _inspect_owned_stage(
                destination, transaction, transaction_raw, require_complete=True
            )
        else:
            if backup_snapshot is not None or stage_snapshot is not None:
                raise RuntimeError("stage quarantine exists in an ambiguous transaction state")
            if old_snapshot is not None:
                if live_snapshot is None:
                    raise RuntimeError("stage quarantine exists without the bound old live install")
                _assert_snapshot_equal(live_snapshot, old_snapshot, "restored live install")
            elif live_snapshot is not None:
                raise RuntimeError("stage quarantine exists beside an unexpected fresh live path")
        _resume_quarantine(quarantine, transaction, transaction_raw)
        _quarantine_record_and_remove(
            transaction_path, transaction_raw, str(transaction["transaction_id"])
        )
        return

    live_snapshot = _capture_path_snapshot(destination) if _path_exists(destination) else None
    live_is_old = old_snapshot is not None and live_snapshot == old_snapshot
    live_is_new = False
    if live_snapshot is not None:
        try:
            _inspect_owned_stage(
                destination, transaction, transaction_raw, require_complete=True
            )
            live_is_new = True
        except (OSError, RuntimeError, ValueError):
            live_is_new = False

    if backup_snapshot is not None:
        if live_snapshot is None:
            _rename_directory(backup, destination)
            restored = _capture_path_snapshot(destination)
            assert old_snapshot is not None
            _assert_snapshot_equal(restored, old_snapshot, "restored live install")
            if stage_snapshot is not None:
                _quarantine_and_delete(
                    expected_stage,
                    stage_snapshot,
                    transaction,
                    transaction_raw,
                    "stage",
                )
            _quarantine_record_and_remove(
                transaction_path, transaction_raw, str(transaction["transaction_id"])
            )
            print(f"Recovered the previous {SKILL_NAME} install after an interrupted update.")
            return
        if live_is_new and stage_snapshot is None:
            _quarantine_and_delete(
                backup, backup_snapshot, transaction, transaction_raw, "backup"
            )
            _quarantine_record_and_remove(
                transaction_path, transaction_raw, str(transaction["transaction_id"])
            )
            return
        raise RuntimeError("transaction artifacts describe an ambiguous promotion; preserving them")

    if old_snapshot is not None:
        if live_is_old:
            if stage_snapshot is not None:
                _quarantine_and_delete(
                    expected_stage,
                    stage_snapshot,
                    transaction,
                    transaction_raw,
                    "stage",
                )
            _quarantine_record_and_remove(
                transaction_path, transaction_raw, str(transaction["transaction_id"])
            )
            return
        if live_is_new and stage_snapshot is None:
            _quarantine_record_and_remove(
                transaction_path, transaction_raw, str(transaction["transaction_id"])
            )
            return
        raise RuntimeError("transaction lost or changed its bound backup; preserving artifacts")

    if live_snapshot is None:
        if stage_snapshot is not None:
            _quarantine_and_delete(
                expected_stage, stage_snapshot, transaction, transaction_raw, "stage"
            )
        _quarantine_record_and_remove(
            transaction_path, transaction_raw, str(transaction["transaction_id"])
        )
        return
    if live_is_new and stage_snapshot is None:
        _quarantine_record_and_remove(
            transaction_path, transaction_raw, str(transaction["transaction_id"])
        )
        return
    raise RuntimeError("fresh transaction has an unexpected live path; preserving artifacts")


def promote_staged_install(stage: Path, destination: Path, skills_dir: Path) -> None:
    """Promote a validated stage and restore the old install on any failure."""
    backup = skills_dir / BACKUP_NAME
    transaction, transaction_raw = _load_transaction(skills_dir)
    if stage != skills_dir / str(transaction["stage_name"]):
        raise RuntimeError("stage path does not match the active transaction")
    if _path_exists(backup):
        raise RuntimeError("installer backup was not recovered")
    quarantine = skills_dir / str(transaction["quarantine_name"])
    if _path_exists(quarantine):
        raise RuntimeError("installer quarantine was not recovered")
    expected_stage = _inspect_owned_stage(
        stage, transaction, transaction_raw, require_complete=True
    )
    old_snapshot = _snapshot_from_transaction(transaction)
    if old_snapshot is None:
        if _path_exists(destination):
            raise RuntimeError("fresh destination appeared after transaction staging")
    else:
        current_live = _capture_path_snapshot(destination)
        _assert_snapshot_equal(current_live, old_snapshot, "live install")
        _rename_directory(destination, backup)
        _assert_snapshot_equal(
            _capture_path_snapshot(backup), old_snapshot, "installer backup"
        )
    try:
        _assert_snapshot_equal(
            _inspect_owned_stage(stage, transaction, transaction_raw, require_complete=True),
            expected_stage,
            "owned stage",
        )
        _rename_directory(stage, destination)
        _inspect_owned_stage(
            destination, transaction, transaction_raw, require_complete=True
        )
    except Exception as promotion_error:
        preserved_quarantine = False
        if _path_exists(destination):
            if _path_exists(quarantine):
                raise RuntimeError(
                    "promotion failed and a quarantine collision prevents safe rollback"
                ) from promotion_error
            _rename_directory(destination, quarantine)
            try:
                failed_snapshot = _inspect_owned_stage(
                    quarantine, transaction, transaction_raw, require_complete=True
                )
            except (OSError, RuntimeError, ValueError):
                preserved_quarantine = True
            else:
                marker_record = _quarantine_record(
                    transaction, transaction_raw, "stage", failed_snapshot
                )
                marker_raw = _write_json_exclusive(
                    quarantine / QUARANTINE_MARKER, marker_record
                )
                marker_metadata = _bound_metadata_for_bytes(
                    quarantine / QUARANTINE_MARKER,
                    marker_raw,
                )
                _delete_bound_tree(
                    quarantine,
                    failed_snapshot,
                    {QUARANTINE_MARKER: marker_metadata},
                )
        if old_snapshot is not None and _path_exists(backup):
            _assert_snapshot_equal(
                _capture_path_snapshot(backup), old_snapshot, "installer backup"
            )
            _rename_directory(backup, destination)
            _assert_snapshot_equal(
                _capture_path_snapshot(destination), old_snapshot, "restored live install"
            )
        if _path_exists(stage):
            remaining_stage = _inspect_owned_stage(
                stage, transaction, transaction_raw, require_complete=False
            )
            _quarantine_and_delete(
                stage, remaining_stage, transaction, transaction_raw, "stage"
            )
        if not preserved_quarantine:
            _quarantine_record_and_remove(
                _transaction_path(skills_dir),
                transaction_raw,
                str(transaction["transaction_id"]),
            )
        raise
    if old_snapshot is not None:
        backup_snapshot = _capture_path_snapshot(backup)
        _assert_snapshot_equal(backup_snapshot, old_snapshot, "installer backup")
        _quarantine_and_delete(
            backup, backup_snapshot, transaction, transaction_raw, "backup"
        )
    _quarantine_record_and_remove(
        _transaction_path(skills_dir),
        transaction_raw,
        str(transaction["transaction_id"]),
    )


def stage_validated_install(
    repo_root: Path,
    skills_dir: Path,
    expected_manifest: dict[str, dict[str, object]],
) -> Path:
    expected_manifest = _validate_payload_manifest(dict(sorted(expected_manifest.items())))
    destination = skills_dir / SKILL_NAME
    if _path_exists(_transaction_path(skills_dir)) or _path_exists(skills_dir / BACKUP_NAME):
        raise RuntimeError("reserved installer artifacts were not recovered before staging")
    if _reserved_stages(skills_dir):
        raise RuntimeError("reserved-prefix stage artifacts were not recovered before staging")
    if _reserved_quarantines(skills_dir):
        raise RuntimeError("reserved-prefix quarantine artifacts were not recovered before staging")
    transaction_id = uuid.uuid4().hex
    stage = skills_dir / f"{STAGE_PREFIX}{os.getpid()}-{transaction_id}"
    quarantine = skills_dir / f"{QUARANTINE_PREFIX}{transaction_id}"
    if _path_exists(stage) or _path_exists(quarantine):
        raise RuntimeError("random transaction artifact name already exists")
    old_snapshot = (
        _capture_path_snapshot(destination) if _path_exists(destination) else None
    )
    transaction = _transaction_record(
        stage.name,
        quarantine.name,
        transaction_id,
        expected_manifest,
        old_snapshot,
    )
    transaction_raw = _write_json_exclusive(
        _transaction_path(skills_dir), transaction
    )
    try:
        stage.mkdir(mode=0o700)
        _write_json_exclusive(
            stage / PROVENANCE_MARKER,
            _provenance_record(transaction, transaction_raw),
        )
        shutil.copytree(
            repo_root,
            stage,
            ignore=ignore_runtime_noise,
            dirs_exist_ok=True,
        )
        copied_manifest = payload_manifest(stage)
        source_after_copy = payload_manifest(repo_root)
        if source_after_copy != expected_manifest:
            raise RuntimeError("source payload changed while it was being copied; retry the install")
        if copied_manifest != expected_manifest:
            raise RuntimeError("staged payload does not match the source payload")
        write_completion_marker(stage, copied_manifest)
        _inspect_owned_stage(
            stage, transaction, transaction_raw, require_complete=True
        )
        return stage
    except Exception as stage_error:
        try:
            recover_interrupted_transaction(skills_dir, destination)
        except Exception as recovery_error:
            raise RuntimeError(
                f"{_bounded_diagnostic(stage_error, 220)}; staging recovery refused: "
                f"{_bounded_diagnostic(recovery_error, 220)}"
            ) from stage_error
        raise


def assert_safe_destination(destination: Path, skills_dir: Path) -> None:
    resolved_destination = destination.resolve()
    resolved_skills_dir = skills_dir.resolve()
    if resolved_destination.name != SKILL_NAME:
        raise ValueError(f"destination must end with {SKILL_NAME}: {resolved_destination}")
    if resolved_skills_dir not in resolved_destination.parents:
        raise ValueError(f"destination must stay inside the skills directory: {resolved_skills_dir}")


def assert_safe_preflight(destination: Path, skills_dir: Path, repo_root: Path) -> None:
    """Reject an obviously unsafe parent before creating the lock directory.

    This intentionally resolves only the skills directory, not its live skill
    child. Another installer may be atomically renaming that child before this
    process acquires the shared lock; resolving it here would recreate the very
    race the lock is meant to remove.
    """
    absolute_destination = Path(os.path.abspath(destination))
    absolute_skills_dir = Path(os.path.abspath(skills_dir))
    if absolute_destination.name != SKILL_NAME:
        raise ValueError(f"destination must end with {SKILL_NAME}: {absolute_destination}")
    if absolute_destination.parent != absolute_skills_dir:
        raise ValueError(f"destination must stay inside the skills directory: {absolute_skills_dir}")
    resolved_skills_dir = skills_dir.resolve()
    resolved_repo_root = repo_root.resolve()
    if resolved_skills_dir == resolved_repo_root or resolved_repo_root in resolved_skills_dir.parents:
        raise ValueError(
            f"destination is inside the source repository ({resolved_repo_root}).\n"
            f"Copying it into itself would recurse until the path length fails.\n"
            f"To install into another project, run this script from that project "
            f"by absolute path:\n"
            f"    python {resolved_repo_root / 'scripts' / 'install_codex_skill.py'} "
            f"--dest .claude/skills"
        )


def assert_destination_outside_source(destination: Path, repo_root: Path) -> None:
    """Refuse to copy the repository into a directory inside itself.

    shutil.copytree walks the source tree, and the destination is created before
    the walk reaches it, so an in-tree destination copies itself into itself:
    .claude/skills/seedance-20/.claude/skills/seedance-20/... until the path
    length fails, after hundreds of directories. `--dest .claude/skills` run
    from this repository's own root is the way into it, and installing the
    repository into itself is never what someone meant.
    """
    resolved = destination.resolve()
    root = repo_root.resolve()
    if resolved == root or root in resolved.parents:
        raise ValueError(
            f"destination is inside the source repository ({root}).\n"
            f"Copying it into itself would recurse until the path length fails.\n"
            f"To install into another project, run this script from that project "
            f"by absolute path:\n"
            f"    python {root / 'scripts' / 'install_codex_skill.py'} --dest .claude/skills"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Install this repository as a local Codex skill.")
    parser.add_argument(
        "--dest",
        type=Path,
        default=default_skills_dir(),
        help="Codex skills directory. Defaults to $CODEX_HOME/skills or ~/.codex/skills.",
    )
    parser.add_argument("--force", action="store_true", help="Replace an existing seedance-20 install.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    source_skill = repo_root / "SKILL.md"
    if not source_skill.exists():
        raise FileNotFoundError(f"SKILL.md not found at {source_skill}")

    skills_dir = args.dest.expanduser()
    destination = skills_dir / SKILL_NAME
    destination_existed_at_start = _path_exists(destination)
    # Reported as a message rather than a traceback: this is the first command a
    # new user runs, and a stack trace reads as "the tool is broken".
    try:
        assert_safe_preflight(destination, skills_dir, repo_root)
    except ValueError as exc:
        print(f"Refusing to install: {_bounded_diagnostic(exc)}")
        return 1

    try:
        skills_dir.mkdir(parents=True, exist_ok=True)
        with exclusive_install_lock(skills_dir):
            # Re-check after taking the lock. Another cooperating installer may
            # have changed the path while this process was waiting.
            assert_safe_destination(destination, skills_dir)
            assert_destination_outside_source(destination, repo_root)
            recover_interrupted_transaction(skills_dir, destination)

            expected_manifest = payload_manifest(repo_root)
            state, reason = classify_existing_install(destination, expected_manifest)
            if state == "complete" and not args.force:
                if not destination_existed_at_start:
                    print(
                        f"{SKILL_NAME} is complete at {_bounded_diagnostic(destination, 240)}; "
                        "another installer finished or recovered it while this process waited."
                    )
                    return 0
                print(
                    f"{SKILL_NAME} is already installed at "
                    f"{_bounded_diagnostic(destination, 240)}"
                )
                print("Run again with --force to replace it.")
                return 1
            if state == "unknown" and not args.force:
                print(
                    f"Refusing to replace the existing path at "
                    f"{_bounded_diagnostic(destination, 220)}: "
                    f"{_bounded_diagnostic(reason, 240)}"
                )
                print("Run again with --force only if replacing that path is intentional.")
                return 1
            if state == "incomplete" and not args.force:
                print(
                    f"Detected an incomplete {SKILL_NAME} install at "
                    f"{_bounded_diagnostic(destination, 240)}; repairing it."
                )

            stage = stage_validated_install(repo_root, skills_dir, expected_manifest)
            promote_staged_install(stage, destination, skills_dir)
    except (OSError, RuntimeError, TimeoutError, ValueError) as exc:
        print(f"Installation failed: {_bounded_diagnostic(exc)}", file=sys.stderr)
        return 1

    print(f"Installed {SKILL_NAME} to {_bounded_diagnostic(destination, 280)}")
    print(f"Installed payload size: {payload_size(destination)}")
    # --dest sends this into any client's skills directory, so the closing line
    # cannot name one. Telling a Claude Code user to restart Codex is the kind
    # of instruction that makes a working install look broken.
    print("Restart your agent client to pick up new skills.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
