#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import os
import shutil
import sys
from pathlib import Path
from typing import TextIO


SKILL_NAME = "seedance-20"

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


def _text_for_stream(text: str, stream: TextIO) -> str:
    """Preserve Unicode when possible and escape only unsupported characters."""
    encoding = getattr(stream, "encoding", None)
    if not isinstance(encoding, str) or not encoding:
        return text
    try:
        text.encode(encoding)
        return text
    except UnicodeEncodeError:
        return text.encode(encoding, errors="backslashreplace").decode(encoding)
    except LookupError:
        return text.encode("ascii", errors="backslashreplace").decode("ascii")


def safe_print(message: object, *, stream: TextIO | None = None) -> None:
    """Write one message without letting a narrow console encoding abort it.

    The stream is not reconfigured globally. If its advertised encoding is
    wrong, retry once with an ASCII-only escaped representation. Other write
    failures, including OSError, deliberately propagate.
    """
    output = sys.stdout if stream is None else stream
    text = f"{message}\n"
    prepared = _text_for_stream(text, output)
    try:
        output.write(prepared)
    except UnicodeEncodeError:
        escaped = text.encode("ascii", errors="backslashreplace").decode("ascii")
        output.write(escaped)


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
        assert_safe_destination(destination, skills_dir)
        assert_destination_outside_source(destination, repo_root)
    except ValueError as exc:
        safe_print(f"Refusing to install: {exc}")
        return 1

    skills_dir.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if not args.force:
            safe_print(f"{SKILL_NAME} is already installed at {destination}")
            safe_print("Run again with --force to replace it.")
            return 1
        shutil.rmtree(destination)

    shutil.copytree(repo_root, destination, ignore=ignore_runtime_noise)

    safe_print(f"Installed {SKILL_NAME} to {destination}")
    safe_print(f"Installed payload size: {payload_size(destination)}")
    # --dest sends this into any client's skills directory, so the closing line
    # cannot name one. Telling a Claude Code user to restart Codex is the kind
    # of instruction that makes a working install look broken.
    safe_print("Restart your agent client to pick up new skills.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
