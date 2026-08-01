#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path, PurePosixPath


SKILL_NAME = "seedance-20"
PAYLOAD_MANIFEST = PurePosixPath("validation/install-payload.txt")
REPOSITORY_URL = "https://github.com/Emily2040/seedance-2.0"
# Archive material remains available for source history and comparison, but it
# must never become active retrieval material in an installed skill.
ARCHIVE_ONLY_PATHS = frozenset({"references/migrated"})
README_GALLERY_START = "<!-- installed-readme-gallery:start -->"
README_GALLERY_END = "<!-- installed-readme-gallery:end -->"

# Deliberately absent from the positive payload manifest because they are
# development-only. eval_run.py is also network-capable and credential-reading.
# tests/test_install_payload.py enforces that none of these reach an install.
DEV_ONLY_NAMES = {
    "eval_run.py",
    "eval-runs",
    "tests",
}


def default_skills_dir() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser() / "skills"
    return Path.home() / ".codex" / "skills"


def is_archive_only_path(relative_path: Path | PurePosixPath) -> bool:
    """Return whether a source-relative path belongs only to repository history."""
    normalized = relative_path.as_posix().strip("/")
    return any(
        normalized == archive or normalized.startswith(f"{archive}/")
        for archive in ARCHIVE_ONLY_PATHS
    )


def load_payload_manifest(repo_root: Path) -> frozenset[str]:
    """Load an explicit, source-relative install contract.

    Every entry is a normalized POSIX relative path to one regular file inside
    the repository. Directories are implied by their declared descendants.
    """
    root = repo_root.resolve()
    manifest_path = root.joinpath(*PAYLOAD_MANIFEST.parts)
    if not manifest_path.is_file():
        raise FileNotFoundError(f"install payload manifest not found: {manifest_path}")

    declared: set[str] = set()
    for line_number, raw_line in enumerate(manifest_path.read_text(encoding="utf-8").splitlines(), 1):
        entry = raw_line.strip()
        if not entry or entry.startswith("#"):
            continue
        relative = PurePosixPath(entry)
        invalid = (
            raw_line != entry
            or "\\" in entry
            or relative.is_absolute()
            or not relative.parts
            or any(part in {".", ".."} for part in relative.parts)
            or ":" in relative.parts[0]
            or relative.as_posix() != entry
        )
        if invalid:
            raise ValueError(
                f"{manifest_path}:{line_number}: payload path must be a normalized POSIX relative path: {entry!r}"
            )
        if is_archive_only_path(relative):
            raise ValueError(
                f"{manifest_path}:{line_number}: archive-only path cannot be installed: {entry}"
            )
        if entry in declared:
            raise ValueError(f"{manifest_path}:{line_number}: duplicate payload path: {entry}")

        source = root.joinpath(*relative.parts)
        resolved_source = source.resolve()
        if root not in resolved_source.parents:
            raise ValueError(f"{manifest_path}:{line_number}: payload path escapes repository: {entry}")
        if not source.is_file():
            raise FileNotFoundError(f"{manifest_path}:{line_number}: declared payload file missing: {entry}")
        declared.add(entry)

    required = {
        "SKILL.md",
        "scripts/install_codex_skill.py",
        PAYLOAD_MANIFEST.as_posix(),
    }
    missing_required = sorted(required - declared)
    if missing_required:
        raise ValueError(
            f"{manifest_path}: missing required payload entries: {', '.join(missing_required)}"
        )
    return frozenset(declared)


def payload_allowlist_filter(repo_root: Path, declared: frozenset[str]):
    """Return a copytree ignore callback that admits only declared files."""
    root = repo_root.resolve()
    declared_directories = {
        PurePosixPath(*path.parts[:depth]).as_posix()
        for entry in declared
        for path in [PurePosixPath(entry)]
        for depth in range(1, len(path.parts))
    }

    def ignore_undeclared(source_directory: str, names: list[str]) -> set[str]:
        relative_directory = Path(source_directory).resolve().relative_to(root)
        parent_parts = () if relative_directory == Path(".") else relative_directory.parts
        ignored: set[str] = set()
        for name in names:
            candidate = PurePosixPath(*parent_parts, name).as_posix()
            if candidate not in declared and candidate not in declared_directories:
                ignored.add(name)
        return ignored

    return ignore_undeclared


def rewrite_installed_readme(destination: Path) -> None:
    """Replace source-only gallery embeds with one usable repository link.

    The source README keeps the curated gallery. Installed payloads omit its
    large bitmaps, so retaining those embeds would knowingly create broken
    local targets. Explicit markers make this transformation deterministic and
    fail closed if the README structure changes.
    """
    readme = destination / "README.md"
    text = readme.read_text(encoding="utf-8")
    if text.count(README_GALLERY_START) != 1 or text.count(README_GALLERY_END) != 1:
        raise ValueError("README gallery install markers must each appear exactly once")

    start = text.index(README_GALLERY_START)
    end = text.index(README_GALLERY_END)
    if end <= start:
        raise ValueError("README gallery install markers are out of order")

    installed_gallery = (
        f"{README_GALLERY_START}\n\n"
        "The generated bitmap gallery is kept in the source repository rather "
        "than the installed runtime package. "
        f"[View the full visual gallery in the source repository]({REPOSITORY_URL}#visual-gallery).\n\n"
        f"{README_GALLERY_END}"
    )
    rewritten = text[:start] + installed_gallery + text[end + len(README_GALLERY_END):]
    readme.write_text(rewritten, encoding="utf-8")


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
    # Validate the source contract before creating or replacing any destination.
    declared_payload = load_payload_manifest(repo_root)

    skills_dir = args.dest.expanduser()
    destination = skills_dir / SKILL_NAME
    # Reported as a message rather than a traceback: this is the first command a
    # new user runs, and a stack trace reads as "the tool is broken".
    try:
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

    shutil.copytree(
        repo_root,
        destination,
        ignore=payload_allowlist_filter(repo_root, declared_payload),
    )
    if "README.md" in declared_payload:
        rewrite_installed_readme(destination)

    print(f"Installed {SKILL_NAME} to {destination}")
    print(f"Installed payload size: {payload_size(destination)}")
    # --dest sends this into any client's skills directory, so the closing line
    # cannot name one. Telling a Claude Code user to restart Codex is the kind
    # of instruction that makes a working install look broken.
    print("Restart your agent client to pick up new skills.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
