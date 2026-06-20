#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import os
import shutil
from pathlib import Path


SKILL_NAME = "seedance-20"
IGNORE_NAMES = {
    ".git",
    ".github",
    ".pytest_cache",
    ".seedance_backups",
    "__pycache__",
    "docs",
}
IGNORE_PATTERNS = ["*.pyc", "*.pyo", "*.tmp", "*.log", "*.png", "*.jpg", "*.jpeg", "*.psd"]


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


def assert_safe_destination(destination: Path, skills_dir: Path) -> None:
    resolved_destination = destination.resolve()
    resolved_skills_dir = skills_dir.resolve()
    if resolved_destination.name != SKILL_NAME:
        raise ValueError(f"destination must end with {SKILL_NAME}: {resolved_destination}")
    if resolved_skills_dir not in resolved_destination.parents:
        raise ValueError(f"destination must stay inside the skills directory: {resolved_skills_dir}")


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
    assert_safe_destination(destination, skills_dir)

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
    print("Restart Codex to pick up new skills.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
