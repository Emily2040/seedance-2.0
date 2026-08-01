#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import os
import shutil
from pathlib import Path
from typing import Iterator


SKILL_NAME = "seedance-20"
# MAX_PATH is a 260-unit buffer including its terminating NUL. Portable
# directory creation also reserves 12 units for an appended 8.3 name.
WINDOWS_PORTABLE_DIRECTORY_LIMIT = 247
WINDOWS_PORTABLE_FILE_LIMIT = 259

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


def windows_utf16_units(path: Path) -> int:
    """Count Windows path units, where non-BMP characters consume two units."""
    return len(str(path).encode("utf-16-le", errors="surrogatepass")) // 2


def lexical_absolute_path(path: Path) -> Path:
    """Make a path absolute without resolving or touching a possibly long path."""
    candidate = path if path.is_absolute() else Path.cwd() / path
    return Path(os.path.normpath(str(candidate)))


def installed_payload_entries(repo_root: Path) -> Iterator[tuple[Path, bool]]:
    """Yield the directories and files that copytree will install."""
    for current, directory_names, file_names in os.walk(repo_root):
        ignored = ignore_runtime_noise(current, directory_names + file_names)
        directory_names[:] = sorted(name for name in directory_names if name not in ignored)
        current_path = Path(current)
        for name in directory_names:
            yield (current_path / name).relative_to(repo_root), True
        for name in sorted(file_names):
            if name not in ignored:
                yield (current_path / name).relative_to(repo_root), False


def assert_windows_portable_install_path(destination: Path, repo_root: Path) -> None:
    """Refuse paths that cannot be copied on legacy-compatible Windows hosts."""
    absolute_destination = lexical_absolute_path(destination)
    candidates: list[tuple[Path, Path, bool]] = [
        (Path("."), absolute_destination, True)
    ]
    for relative, is_directory in installed_payload_entries(repo_root):
        candidates.append((relative, absolute_destination / relative, is_directory))

    violations: list[tuple[int, int, int, Path, Path, bool]] = []
    for relative, installed_path, is_directory in candidates:
        limit = (
            WINDOWS_PORTABLE_DIRECTORY_LIMIT
            if is_directory
            else WINDOWS_PORTABLE_FILE_LIMIT
        )
        units = windows_utf16_units(installed_path)
        if units > limit:
            violations.append(
                (units - limit, units, limit, relative, installed_path, is_directory)
            )
    if not violations:
        return

    _excess, units, limit, relative, installed_path, is_directory = max(
        violations, key=lambda item: (item[0], item[1], str(item[3]))
    )
    kind = "directory" if is_directory else "file"
    payload_entry = "install destination" if relative == Path(".") else relative.as_posix()
    raise ValueError(
        "Windows portable path limit would be exceeded.\n"
        f"Predicted {kind} path uses {units} UTF-16 code units; safe limit is {limit}.\n"
        f"Payload entry: {payload_entry}\n"
        f"Predicted path: {installed_path}\n"
        "Choose a shorter --dest (for example C:\\Codex\\skills), or set "
        "CODEX_HOME closer to the drive root. No files were copied."
    )


def assert_safe_destination(destination: Path, skills_dir: Path) -> None:
    resolved_destination = destination.resolve()
    resolved_skills_dir = skills_dir.resolve()
    if resolved_destination.name != SKILL_NAME:
        raise ValueError(f"destination must end with {SKILL_NAME}: {resolved_destination}")
    if resolved_skills_dir not in resolved_destination.parents:
        raise ValueError(f"destination must stay inside the skills directory: {resolved_skills_dir}")


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
    # Reported as a message rather than a traceback: this is the first command a
    # new user runs, and a stack trace reads as "the tool is broken".
    try:
        if os.name == "nt":
            assert_windows_portable_install_path(destination, repo_root)
        assert_safe_destination(destination, skills_dir)
        assert_destination_outside_source(destination, repo_root)
    except ValueError as exc:
        print(f"Refusing to install: {exc}")
        return 1

    skills_dir.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if not args.force:
            print(f"{SKILL_NAME} is already installed at {destination}")
            print("Run again with --force to replace it.")
            return 1
        shutil.rmtree(destination)

    shutil.copytree(repo_root, destination, ignore=ignore_runtime_noise)

    print(f"Installed {SKILL_NAME} to {destination}")
    print(f"Installed payload size: {payload_size(destination)}")
    # --dest sends this into any client's skills directory, so the closing line
    # cannot name one. Telling a Claude Code user to restart Codex is the kind
    # of instruction that makes a working install look broken.
    print("Restart your agent client to pick up new skills.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
