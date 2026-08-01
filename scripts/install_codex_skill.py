#!/usr/bin/env python3
from __future__ import annotations

import argparse
import errno
import fnmatch
import hashlib
import json
import os
import shutil
import sys
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SKILL_NAME = "seedance-20"
COMPLETION_MARKER = ".seedance-install-complete.json"
COMPLETION_FORMAT_VERSION = 1
LOCK_NAME = f".{SKILL_NAME}.install.lock"
BACKUP_NAME = f".{SKILL_NAME}.install-backup"
STAGE_PREFIX = f".{SKILL_NAME}.install-stage-"
LOCK_TIMEOUT_SECONDS = 300.0

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
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def payload_manifest(root: Path) -> dict[str, dict[str, object]]:
    """Return the deterministic manifest copied by this installer."""
    manifest: dict[str, dict[str, object]] = {}
    for current, directory_names, file_names in os.walk(root):
        ignored = ignore_runtime_noise(current, directory_names + file_names)
        directory_names[:] = sorted(name for name in directory_names if name not in ignored)
        for name in sorted(file_names):
            if name in ignored:
                continue
            path = Path(current) / name
            if not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            manifest[relative] = {
                "size": path.stat().st_size,
                "sha256": _file_sha256(path),
            }
    return manifest


def _manifest_sha256(manifest: dict[str, dict[str, object]]) -> str:
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def write_completion_marker(
    destination: Path, manifest: dict[str, dict[str, object]]
) -> None:
    record = {
        "format_version": COMPLETION_FORMAT_VERSION,
        "skill_name": SKILL_NAME,
        "file_count": len(manifest),
        "manifest_sha256": _manifest_sha256(manifest),
        "files": manifest,
    }
    marker = destination / COMPLETION_MARKER
    temporary = destination / f"{COMPLETION_MARKER}.{uuid.uuid4().hex}.tmp"
    temporary.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, marker)


def validate_completed_install(destination: Path) -> tuple[bool, str]:
    """Validate a managed install using its completion manifest.

    Extra files are deliberately allowed. The marker owns only the files the
    installer wrote, so runtime caches or user notes do not make a complete
    install look corrupt.
    """
    if not destination.is_dir():
        return False, "destination is not a directory"
    marker = destination / COMPLETION_MARKER
    if not marker.is_file():
        return False, "completion marker is missing"
    try:
        record = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return False, f"completion marker cannot be read: {exc}"
    if not isinstance(record, dict):
        return False, "completion marker root must be an object"
    if record.get("format_version") != COMPLETION_FORMAT_VERSION:
        return False, "completion marker format is unsupported"
    if record.get("skill_name") != SKILL_NAME:
        return False, "completion marker names a different skill"
    files = record.get("files")
    if not isinstance(files, dict) or not files:
        return False, "completion marker has no file manifest"
    if record.get("file_count") != len(files):
        return False, "completion marker file count does not match its manifest"
    if record.get("manifest_sha256") != _manifest_sha256(files):
        return False, "completion marker manifest digest does not match"

    resolved_root = destination.resolve()
    for relative, expected in files.items():
        if (
            not isinstance(relative, str)
            or not relative
            or "\\" in relative
            or relative.startswith("/")
            or any(part in {"", ".", ".."} for part in relative.split("/"))
        ):
            return False, f"completion marker contains an unsafe path: {relative!r}"
        if not isinstance(expected, dict):
            return False, f"completion marker metadata is invalid for {relative}"
        expected_size = expected.get("size")
        expected_digest = expected.get("sha256")
        if not isinstance(expected_size, int) or not isinstance(expected_digest, str):
            return False, f"completion marker metadata is invalid for {relative}"
        path = destination.joinpath(*relative.split("/"))
        try:
            resolved_path = path.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            return False, f"installed file is missing: {relative} ({exc})"
        if resolved_root not in resolved_path.parents or not resolved_path.is_file():
            return False, f"installed path escapes the destination or is not a file: {relative}"
        try:
            if resolved_path.stat().st_size != expected_size:
                return False, f"installed file size does not match: {relative}"
            if _file_sha256(resolved_path) != expected_digest:
                return False, f"installed file digest does not match: {relative}"
        except OSError as exc:
            return False, f"installed file cannot be read: {relative} ({exc})"
    return True, "completion marker and managed files are valid"


def classify_existing_install(
    destination: Path, expected_manifest: dict[str, dict[str, object]]
) -> tuple[str, str]:
    """Classify an existing path without overwriting an ambiguous legacy copy."""
    if not _path_exists(destination):
        return "missing", "destination does not exist"
    if not destination.is_dir():
        return "unknown", "destination exists but is not a directory"

    marker = destination / COMPLETION_MARKER
    if marker.is_file():
        valid, reason = validate_completed_install(destination)
        return ("complete" if valid else "incomplete"), reason

    installed_manifest = payload_manifest(destination)
    expected_paths = set(expected_manifest)
    installed_paths = set(installed_manifest)
    if expected_paths.issubset(installed_paths) and all(
        installed_manifest[path] == expected_manifest[path] for path in expected_paths
    ):
        return "complete", "legacy install matches the current source payload"
    if installed_paths < expected_paths:
        return "incomplete", "legacy install path set is a strict subset of the current payload"
    return "unknown", "unmarked install differs from the current source payload"


@contextmanager
def exclusive_install_lock(skills_dir: Path) -> Iterator[None]:
    """Serialize cooperating installers and release automatically on process death."""
    lock_path = skills_dir / LOCK_NAME
    handle = lock_path.open("a+b")
    acquired = False
    deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
            while not acquired:
                handle.seek(0)
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    acquired = True
                except OSError as exc:
                    if exc.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                        raise
                    if time.monotonic() >= deadline:
                        raise TimeoutError(f"timed out waiting for installer lock {lock_path}") from exc
                    time.sleep(0.05)
        else:
            import fcntl

            while not acquired:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True
                except OSError as exc:
                    if exc.errno not in {errno.EACCES, errno.EAGAIN}:
                        raise
                    if time.monotonic() >= deadline:
                        raise TimeoutError(f"timed out waiting for installer lock {lock_path}") from exc
                    time.sleep(0.05)
        yield
    finally:
        if acquired:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def _remove_path(path: Path) -> None:
    if not _path_exists(path):
        return
    if path.is_symlink() or not path.is_dir():
        path.unlink()
    else:
        shutil.rmtree(path)


def _rename_directory(source: Path, destination: Path) -> None:
    """Rename within one skills directory, which is atomic for a missing target."""
    source.rename(destination)


def _cleanup_stages(skills_dir: Path) -> None:
    for path in skills_dir.glob(f"{STAGE_PREFIX}*"):
        _remove_path(path)


def recover_interrupted_transaction(skills_dir: Path, destination: Path) -> None:
    """Restore the old live tree or finish cleanup after a killed promotion."""
    backup = skills_dir / BACKUP_NAME
    if _path_exists(backup):
        if not _path_exists(destination):
            _rename_directory(backup, destination)
            print(f"Recovered the previous {SKILL_NAME} install after an interrupted update.")
        else:
            destination_valid, _ = validate_completed_install(destination)
            if destination_valid:
                _remove_path(backup)
            else:
                displaced = skills_dir / f"{STAGE_PREFIX}recovery-{uuid.uuid4().hex}"
                _rename_directory(destination, displaced)
                try:
                    _rename_directory(backup, destination)
                except Exception:
                    _rename_directory(displaced, destination)
                    raise
                _remove_path(displaced)
                print(f"Rolled back {SKILL_NAME} after an interrupted update.")
    _cleanup_stages(skills_dir)


def promote_staged_install(stage: Path, destination: Path, skills_dir: Path) -> None:
    """Promote a validated stage and restore the old install on any failure."""
    backup = skills_dir / BACKUP_NAME
    if _path_exists(backup):
        raise RuntimeError(f"installer backup was not recovered: {backup}")
    had_destination = _path_exists(destination)
    if had_destination:
        _rename_directory(destination, backup)
    try:
        _rename_directory(stage, destination)
        valid, reason = validate_completed_install(destination)
        if not valid:
            raise RuntimeError(f"promoted install failed validation: {reason}")
    except Exception:
        if _path_exists(destination):
            _remove_path(destination)
        if had_destination and _path_exists(backup):
            _rename_directory(backup, destination)
        raise
    if had_destination:
        try:
            _remove_path(backup)
        except OSError as exc:
            print(f"Warning: installed successfully but could not remove backup {backup}: {exc}")


def stage_validated_install(
    repo_root: Path,
    skills_dir: Path,
    expected_manifest: dict[str, dict[str, object]],
) -> Path:
    stage = skills_dir / f"{STAGE_PREFIX}{os.getpid()}-{uuid.uuid4().hex}"
    shutil.copytree(repo_root, stage, ignore=ignore_runtime_noise)
    copied_manifest = payload_manifest(stage)
    source_after_copy = payload_manifest(repo_root)
    if source_after_copy != expected_manifest:
        raise RuntimeError("source payload changed while it was being copied; retry the install")
    if copied_manifest != expected_manifest:
        raise RuntimeError("staged payload does not match the source payload")
    write_completion_marker(stage, copied_manifest)
    valid, reason = validate_completed_install(stage)
    if not valid:
        raise RuntimeError(f"staged payload failed completion validation: {reason}")
    return stage


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
        print(f"Refusing to install: {exc}")
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
                        f"{SKILL_NAME} is complete at {destination}; "
                        "another installer finished or recovered it while this process waited."
                    )
                    return 0
                print(f"{SKILL_NAME} is already installed at {destination}")
                print("Run again with --force to replace it.")
                return 1
            if state == "unknown" and not args.force:
                print(f"Refusing to replace the existing path at {destination}: {reason}")
                print("Run again with --force only if replacing that path is intentional.")
                return 1
            if state == "incomplete" and not args.force:
                print(f"Detected an incomplete {SKILL_NAME} install at {destination}; repairing it.")

            stage: Path | None = None
            try:
                stage = stage_validated_install(repo_root, skills_dir, expected_manifest)
                promote_staged_install(stage, destination, skills_dir)
                stage = None
            finally:
                if stage is not None and _path_exists(stage):
                    _remove_path(stage)
    except (OSError, RuntimeError, TimeoutError, ValueError) as exc:
        print(f"Installation failed: {exc}", file=sys.stderr)
        return 1

    print(f"Installed {SKILL_NAME} to {destination}")
    print(f"Installed payload size: {payload_size(destination)}")
    # --dest sends this into any client's skills directory, so the closing line
    # cannot name one. Telling a Claude Code user to restart Codex is the kind
    # of instruction that makes a working install look broken.
    print("Restart your agent client to pick up new skills.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
